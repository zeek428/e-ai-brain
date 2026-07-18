from __future__ import annotations

from types import SimpleNamespace

import pytest
from psycopg.types.json import Jsonb

from app.api.deps import api_error
from app.core.persistence import PostgresSnapshotRepository
from app.core.store import MemoryStore
from app.services.operational_deployments import (
    complete_deployment_request_response,
    create_deployment_request_response,
    start_deployment_request_response,
)
from tests.test_rd_collaboration_repository import (
    _seed_exact_run,
    postgres_admin_url,
    repository,
)

__all__ = ["postgres_admin_url", "repository"]


_USER = {"id": "user_admin", "roles": ["admin"], "permissions": []}


def _payload(**changes: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "artifact_digest": "sha256:" + "a" * 64,
        "artifact_version": "v1",
        "assigned_ops_user": None,
        "collaboration_run_id": "run-1",
        "commit_sha": "a" * 40,
        "deploy_window_end": None,
        "deploy_window_start": None,
        "deployment_scheme_id": None,
        "environment": "prod",
        "product_id": "product-1",
        "release_branch": "release/v1",
        "release_readiness_task_id": None,
        "requirement_ids": ["requirement-1"],
        "risk_level": "medium",
        "rollback_plan": "rollback to the prior release",
        "title": "Policy-controlled deployment",
        "version_id": "version-1",
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _store(*, run_status: str = "ready_for_release") -> MemoryStore:
    store = MemoryStore()
    store.products["product-1"] = {"id": "product-1", "status": "active"}
    store.product_versions["version-1"] = {
        "id": "version-1",
        "product_id": "product-1",
        "status": "ready_for_release",
    }
    store.requirements["requirement-1"] = {
        "id": "requirement-1",
        "product_id": "product-1",
        "status": "ready_for_release",
        "version_id": "version-1",
    }
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "delivery_evidence_hash": "sha256:trusted-ready-evidence",
        "delivery_evidence_id": "ready-evidence-1",
        "delivery_target": "deployed",
        "product_id": "product-1",
        "product_version_id": "version-1",
        "status": run_status,
    }
    store.rd_collaboration_run_requirements["run-requirement-1"] = {
        "id": "run-requirement-1",
        "collaboration_run_id": "run-1",
        "requirement_id": "requirement-1",
    }
    return store


def _start_payload() -> SimpleNamespace:
    return SimpleNamespace(
        executor_type="manual",
        external_build_id="build-1",
        external_job_name="manual-release",
        log_url=None,
    )


def _complete_payload(status: str) -> SimpleNamespace:
    return SimpleNamespace(
        executor_type="manual",
        external_build_id="build-1",
        external_job_name="manual-release",
        failure_reason="health check failed" if status != "success" else None,
        finished_at=None,
        log_url=None,
        status=status,
    )


def _seed_postgres_deployed_ready_boundary(
    repository: PostgresSnapshotRepository,
    *,
    prefix: str,
) -> tuple[str, str]:
    seeded = _seed_exact_run(repository, prefix=prefix)
    run_id = str(seeded["run"]["id"])
    version_id = str(seeded["version"])
    delivery_id = f"{prefix}-delivery"
    readiness_id = f"{prefix}-readiness"
    # The hash is calculated by PostgreSQL so the immutable evidence trigger,
    # rather than a test-only Python copy, remains the source of truth.
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO rd_delivery_evidence_records (
                  id, evidence_type, product_id, collaboration_run_id,
                  product_version_id, payload_json, evidence_hash
                ) VALUES (
                  %s, 'delivery', %s, %s, %s, %s::jsonb,
                  'sha256:' || encode(
                    digest(convert_to(%s::jsonb::text, 'UTF8'), 'sha256'), 'hex'
                  )
                )
                """,
                (
                    delivery_id,
                    seeded["product"],
                    run_id,
                    version_id,
                    Jsonb({}),
                    Jsonb({}),
                ),
            )
            cursor.execute(
                """
                INSERT INTO rd_delivery_evidence_records (
                  id, evidence_type, product_id, collaboration_run_id,
                  product_version_id, delivery_id, payload_json, evidence_hash
                ) VALUES (
                  %s, 'readiness', %s, %s, %s, %s, %s::jsonb,
                  'sha256:' || encode(
                    digest(convert_to(%s::jsonb::text, 'UTF8'), 'sha256'), 'hex'
                  )
                )
                """,
                (
                    readiness_id,
                    seeded["product"],
                    run_id,
                    version_id,
                    delivery_id,
                    Jsonb({}),
                    Jsonb({}),
                ),
            )
            cursor.execute(
                "UPDATE product_versions SET status = 'ready_for_release' WHERE id = %s",
                (version_id,),
            )
            cursor.execute(
                """
                UPDATE rd_collaboration_runs
                SET status = 'ready_for_release', delivery_target = 'deployed',
                    delivery_evidence_id = %s,
                    delivery_evidence_hash = (
                      SELECT evidence_hash FROM rd_delivery_evidence_records WHERE id = %s
                    )
                WHERE id = %s
                """,
                (readiness_id, readiness_id, run_id),
            )
    return run_id, version_id


def _postgres_dispatch_bundle(
    *,
    deployment_id: str,
    product_id: str,
    version_id: str,
) -> dict[str, object]:
    run_id = f"{deployment_id}-run"
    return {
        "audit_events": [],
        "deployment": {
            "id": deployment_id,
            "product_id": product_id,
            "version_id": version_id,
            "title": "Policy-controlled deployment",
            "requirement_ids": [],
            "environment": "prod",
            "risk_level": "medium",
            "gate_summary": {},
            "status": "deploying",
            "created_by": "user_admin",
        },
        "outbox_event": {
            "id": f"{deployment_id}-outbox",
            "aggregate_type": "deployment_request",
            "aggregate_id": deployment_id,
            "event_type": "deployment_dispatch_requested",
            "idempotency_key": f"deployment:{deployment_id}:dispatch",
            "payload": {"deployment_request_id": deployment_id, "deployment_run_id": run_id},
            "status": "pending",
        },
        "requirements": [],
        "run": {
            "id": run_id,
            "deployment_request_id": deployment_id,
            "executor_type": "manual",
            "deployment_method": "manual",
            "executor_channel": "manual",
            "status": "running",
            "created_by": "user_admin",
        },
        "steps": [],
    }


def test_policy_controlled_deployment_is_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RD_COLLABORATION_DEPLOYMENT_ENABLED", raising=False)
    store = _store()

    disabled_error = type(api_error(409, "RD_COLLABORATION_DEPLOYMENT_DISABLED", "disabled"))
    with pytest.raises(disabled_error) as error:
        create_deployment_request_response(current_store=store, payload=_payload(), user=_USER)

    assert error.value.detail["code"] == "RD_COLLABORATION_DEPLOYMENT_DISABLED"
    assert store.deployment_requests == {}
    assert store.rd_collaboration_runs["run-1"]["status"] == "ready_for_release"


def test_policy_controlled_deployment_projects_success_and_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RD_COLLABORATION_DEPLOYMENT_ENABLED", "true")

    successful_store = _store()
    request = create_deployment_request_response(
        current_store=successful_store,
        payload=_payload(),
        user=_USER,
    )
    assert request["status"] == "pending_ops"
    assert request["gate_summary"]["rd_collaboration_run_id"] == "run-1"
    started = start_deployment_request_response(
        current_store=successful_store,
        deployment_request_id=request["id"],
        payload=_start_payload(),
        user=_USER,
    )
    assert started["status"] == "deploying"
    assert successful_store.rd_collaboration_runs["run-1"]["status"] == "deploying"
    assert successful_store.product_versions["version-1"]["status"] == "deploying"
    assert successful_store.ai_executor_tasks == {}
    repeated_start = start_deployment_request_response(
        current_store=successful_store,
        deployment_request_id=request["id"],
        payload=_start_payload(),
        user=_USER,
    )
    assert repeated_start["status"] == "deploying"

    complete_deployment_request_response(
        current_store=successful_store,
        deployment_request_id=request["id"],
        payload=_complete_payload("success"),
        user=_USER,
    )
    assert successful_store.rd_collaboration_runs["run-1"]["status"] == "completed"
    assert successful_store.rd_collaboration_runs["run-1"]["completion_reason"] == "deployed"
    assert successful_store.product_versions["version-1"]["status"] == "released"

    failed_store = _store()
    failed_request = create_deployment_request_response(
        current_store=failed_store,
        payload=_payload(),
        user=_USER,
    )
    start_deployment_request_response(
        current_store=failed_store,
        deployment_request_id=failed_request["id"],
        payload=_start_payload(),
        user=_USER,
    )
    complete_deployment_request_response(
        current_store=failed_store,
        deployment_request_id=failed_request["id"],
        payload=_complete_payload("failed"),
        user=_USER,
    )
    assert failed_store.rd_collaboration_runs["run-1"]["status"] == "ready_for_release"
    assert failed_store.rd_collaboration_runs["run-1"].get("completion_reason") is None
    assert failed_store.product_versions["version-1"]["status"] == "ready_for_release"


def test_policy_controlled_deployment_requires_frozen_ready_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RD_COLLABORATION_DEPLOYMENT_ENABLED", "true")
    store = _store(run_status="verifying")

    incomplete_error = type(api_error(409, "RD_DELIVERY_EVIDENCE_INCOMPLETE", "not ready"))
    with pytest.raises(incomplete_error) as error:
        create_deployment_request_response(current_store=store, payload=_payload(), user=_USER)

    assert error.value.detail["code"] == "RD_DELIVERY_EVIDENCE_INCOMPLETE"
    assert store.deployment_requests == {}


def test_postgres_projects_policy_controlled_deployment_terminal_evidence(
    repository: PostgresSnapshotRepository,
) -> None:
    run_id, version_id = _seed_postgres_deployed_ready_boundary(
        repository,
        prefix="policy-deployment",
    )
    product_id = str(repository.get_rd_collaboration_run(run_id)["product_id"])
    bundle = _postgres_dispatch_bundle(
        deployment_id="deployment-policy-1",
        product_id=product_id,
        version_id=version_id,
    )
    entered = repository.create_rd_policy_controlled_deployment_dispatch_transaction(
        collaboration_run_id=run_id,
        **bundle,
    )
    assert entered["run"]["status"] == "deploying"
    assert entered["product_version"]["status"] == "deploying"
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT rd_collaboration_run_id FROM deployment_requests WHERE id = %s",
                ("deployment-policy-1",),
            )
            assert cursor.fetchone()[0] == run_id

    completed = repository.project_rd_policy_controlled_deployment_result(
        collaboration_run_id=run_id,
        deployment_request_id="deployment-policy-1",
        result_status="success",
    )
    assert completed["run"]["status"] == "completed"
    assert completed["run"]["completion_reason"] == "deployed"
    assert completed["product_version"]["status"] == "released"


def test_postgres_dispatch_bundle_rollback_keeps_collaboration_ready(
    monkeypatch: pytest.MonkeyPatch,
    repository: PostgresSnapshotRepository,
) -> None:
    run_id, version_id = _seed_postgres_deployed_ready_boundary(
        repository,
        prefix="policy-deployment-rollback",
    )
    writes = repository._execution_governance_read_repository._write_repository

    def fail_dispatch(*_: object, **__: object) -> None:
        raise RuntimeError("simulated deployment dispatch persistence failure")

    monkeypatch.setattr(writes, "_create_deployment_dispatch_transaction_cursor", fail_dispatch)
    with pytest.raises(RuntimeError, match="simulated deployment dispatch"):
        bundle = _postgres_dispatch_bundle(
            deployment_id="deployment-policy-rollback",
            product_id=str(repository.get_rd_collaboration_run(run_id)["product_id"]),
            version_id=version_id,
        )
        repository.create_rd_policy_controlled_deployment_dispatch_transaction(
            collaboration_run_id=run_id,
            **bundle,
        )

    assert repository.get_rd_collaboration_run(run_id)["status"] == "ready_for_release"
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM product_versions WHERE id = %s", (version_id,))
            assert cursor.fetchone()[0] == "ready_for_release"
