from __future__ import annotations

import hashlib
import inspect
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.core.persistence import PostgresSnapshotRepository
from app.core.persistence_contracts import RdCollaborationRepository
from app.core.repositories.rd_collaboration import RdCollaborationRepositoryError
from tests.test_rd_collaboration_repository import (
    _decision_record,
    _seed_exact_run,
    postgres_admin_url,
    repository,
)

__all__ = ["postgres_admin_url", "repository"]


def _hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _scope_decision(
    seeded: dict[str, object],
    *,
    request_id: str,
    expires_at: datetime | None = None,
    product_id: str | None = None,
    subject_id: str | None = None,
) -> dict[str, object]:
    decision = _decision_record(
        seeded,
        decision_id=f"{request_id}-decision",
        subject_type="rd_scope_change_request",
        subject_id=subject_id or request_id,
        expires_at=expires_at,
    )
    decision.update(
        {
            "product_id": product_id or seeded["product"],
            "decision_type": "scope_change",
            "options_json": [
                {
                    "code": "approve_apply_and_restart",
                    "label": "Approve",
                    "outcome": "approve",
                    "subject_transition": "cancel_and_restart",
                    "requires_comment": False,
                    "input_schema": {},
                    "effect_preview": {},
                },
                {
                    "code": "reject_keep_current_scope",
                    "label": "Reject",
                    "outcome": "reject",
                    "subject_transition": "resume",
                    "requires_comment": False,
                    "input_schema": {},
                    "effect_preview": {},
                },
            ],
        }
    )
    decision["options_hash"] = "caller-must-not-control-options-hash"
    return decision


def _remove_scope_command(
    seeded: dict[str, object],
    *,
    request_id: str,
    decision: dict[str, object] | None = None,
) -> dict[str, object]:
    typed_operation = {
        "id": f"{request_id}-operation",
        "op": "remove_requirement",
        "requirement_id": seeded["requirement"],
        "destination": "approved_pool",
    }
    return {
        "request": {
            "id": request_id,
            "product_version_id": seeded["version"],
            "request_id": f"{request_id}-idempotency",
            "source_run_id": seeded["run"]["id"],
            "expected_scope_version": 1,
            "expected_run_generation": 1,
            "operations_json": [{"op": "attacker-controlled"}],
            "operations_hash": "attacker-controlled",
            "reason": "remove requirement",
            "decision_request_id": f"{request_id}-decision",
            "requested_by": "user_admin",
        },
        "operations": [typed_operation],
        "decision_request": decision or _scope_decision(seeded, request_id=request_id),
    }


def _work_item(run_id: str, *, work_item_id: str, status: str = "ready") -> dict[str, Any]:
    return {
        "id": work_item_id,
        "collaboration_run_id": run_id,
        "plan_version": 1,
        "work_item_type": "implementation",
        "title": work_item_id,
        "objective": work_item_id,
        "status": status,
        "idempotency_key": work_item_id,
    }


def _attempt(work_item_id: str, *, attempt_id: str) -> dict[str, Any]:
    return {
        "id": attempt_id,
        "work_item_id": work_item_id,
        "attempt_no": 1,
        "idempotency_key": attempt_id,
        "status": "claimed",
    }


def test_command_transaction_owns_domain_audit_outbox_response_and_secret(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="command-atomic")
    run_id = str(seeded["run"]["id"])
    repository.save_rd_work_item_record(_work_item(run_id, work_item_id="command-atomic-work"))

    def operation(transaction: Any) -> dict[str, Any]:
        claimed = transaction.claim_ready_work_item(
            "command-atomic-work",
            lease_owner="worker-a",
            attempt=_attempt("command-atomic-work", attempt_id="command-atomic-attempt"),
        )
        transaction.save_collaboration_event(
            {
                "id": "command-atomic-event",
                "collaboration_run_id": run_id,
                "event_type": "work.claimed",
                "event_key": "work.claimed:command-atomic-work",
                "subject_type": "rd_work_item",
                "subject_id": "command-atomic-work",
                "payload_json": {},
            }
        )
        transaction.save_outbox_event(
            {
                "id": "command-atomic-outbox",
                "aggregate_type": "rd_work_item",
                "aggregate_id": "command-atomic-work",
                "event_type": "work.dispatch",
                "idempotency_key": "work.dispatch:command-atomic-work",
                "payload_json": {},
            }
        )
        transaction.save_audit_event(
            {
                "id": "command-atomic-audit",
                "event_type": "rd_work_item.claimed",
                "actor_id": "worker-a",
                "subject_type": "rd_work_item",
                "subject_id": "command-atomic-work",
                "payload": {},
            }
        )
        return {
            "result_type": "rd_work_item_attempt",
            "result_id": "command-atomic-attempt",
            "http_status": 200,
            "response_hash": "caller-controlled-response-hash",
            "response_json": {"data": {"attempt_id": claimed["attempt"]["id"]}},
            "claim_replay_secret": {
                "id": "command-atomic-secret",
                "secret_ciphertext": "ciphertext",
                "key_id": "test-key",
                "expires_at": datetime.now(UTC) + timedelta(minutes=5),
            },
        }

    result = repository.execute_idempotent_rd_command(
        command_type="claim",
        aggregate_type="rd_work_item",
        aggregate_id="command-atomic-work",
        idempotency_key="command-atomic-key",
        request_hash="command-atomic-request",
        operation=operation,
        command_record_id="command-atomic-record",
    )

    assert result["command_record"]["response_hash"] == _hash(result["response_json"])
    assert repository.get_rd_work_item("command-atomic-work")["status"] == "claimed"
    assert (
        repository.get_valid_claim_replay_secret("command-atomic-record")["secret_ciphertext"]
        == "ciphertext"
    )
    with repository._connect() as connection:
        assert connection.execute(
            "SELECT status FROM execution_outbox_events WHERE id = 'command-atomic-outbox'"
        ).fetchone() == ("pending",)
        assert connection.execute(
            "SELECT event_type FROM audit_events WHERE id = 'command-atomic-audit'"
        ).fetchone() == ("rd_work_item.claimed",)


def test_command_failure_after_secret_rolls_back_every_write(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="command-rollback")
    run_id = str(seeded["run"]["id"])
    repository.save_rd_work_item_record(_work_item(run_id, work_item_id="command-rollback-work"))

    def operation(transaction: Any) -> dict[str, Any]:
        transaction.claim_ready_work_item(
            "command-rollback-work",
            lease_owner="worker-a",
            attempt=_attempt("command-rollback-work", attempt_id="command-rollback-attempt"),
        )
        transaction.save_collaboration_event(
            {
                "id": "command-rollback-event",
                "collaboration_run_id": run_id,
                "event_type": "work.claimed",
                "event_key": "work.claimed:command-rollback-work",
                "subject_type": "rd_work_item",
                "subject_id": "command-rollback-work",
            }
        )
        return {
            "result_type": "rd_work_item_attempt",
            "result_id": "command-rollback-attempt",
            "http_status": 200,
            "response_json": {"data": {"attempt_id": "command-rollback-attempt"}},
            "claim_replay_secret": {
                "id": "command-rollback-secret",
                "secret_ciphertext": "ciphertext",
                "key_id": "test-key",
                "expires_at": datetime.now(UTC) + timedelta(minutes=5),
            },
        }

    def fail(stage: str) -> None:
        if stage == "after_secret":
            raise RuntimeError("injected after secret")

    with pytest.raises(RuntimeError, match="injected after secret"):
        repository.execute_idempotent_rd_command(
            command_type="claim",
            aggregate_type="rd_work_item",
            aggregate_id="command-rollback-work",
            idempotency_key="command-rollback-key",
            request_hash="command-rollback-request",
            operation=operation,
            command_record_id="command-rollback-record",
            failure_injection=fail,
        )

    assert repository.get_rd_work_item("command-rollback-work")["status"] == "ready"
    assert repository.get_rd_work_item_attempt("command-rollback-attempt") is None
    assert repository.get_rd_command_idempotency_record("command-rollback-record") is None
    assert repository.get_valid_claim_replay_secret("command-rollback-record") is None
    assert repository.list_rd_collaboration_events(run_id) == []


def test_scope_request_freezes_canonical_typed_operations_and_server_hash(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="scope-canonical")
    command = _remove_scope_command(seeded, request_id="scope-canonical-request")
    persisted = repository.create_scope_change_request(**command)
    expected = [
        {
            "position": 0,
            "op": "remove_requirement",
            "requirement_id": seeded["requirement"],
            "destination": "approved_pool",
        }
    ]
    assert persisted["operations_json"] == expected
    assert persisted["operations_hash"] == _hash(expected)
    decision = repository.get_decision_request("scope-canonical-request-decision")
    assert decision["options_hash"] == _hash(decision["options_json"])


@pytest.mark.parametrize("mismatch", ["subject", "product", "expired"])
def test_scope_request_rejects_unbound_or_expired_decision(
    repository: PostgresSnapshotRepository,
    mismatch: str,
) -> None:
    seeded = _seed_exact_run(repository, prefix=f"scope-decision-{mismatch}")
    request_id = f"scope-decision-{mismatch}-request"
    decision = _scope_decision(
        seeded,
        request_id=request_id,
        subject_id="other-request" if mismatch == "subject" else None,
        product_id="product_default" if mismatch == "product" else None,
        expires_at=(datetime.now(UTC) - timedelta(seconds=1) if mismatch == "expired" else None),
    )
    command = _remove_scope_command(seeded, request_id=request_id, decision=decision)
    with pytest.raises(RdCollaborationRepositoryError) as error:
        repository.create_scope_change_request(**command)
    assert error.value.code == "RD_DECISION_REQUIRED"
    assert repository.get_rd_scope_change_request(request_id) is None


def test_scope_apply_recomputes_frozen_operation_hash_and_uses_option_mapping(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="scope-apply-provenance")
    request_id = "scope-apply-provenance-request"
    repository.create_scope_change_request(**_remove_scope_command(seeded, request_id=request_id))
    with repository._connect(autocommit=False) as connection:
        connection.execute("ALTER TABLE rd_scope_change_requests DISABLE TRIGGER USER")
        connection.execute(
            "UPDATE rd_scope_change_requests SET operations_hash = 'corrupted' WHERE id = %s",
            (request_id,),
        )
        connection.execute("ALTER TABLE rd_scope_change_requests ENABLE TRIGGER USER")

    with pytest.raises(RdCollaborationRepositoryError) as error:
        repository.apply_scope_change_bundle(
            scope_change_request_id=request_id,
            decision="approve_apply_and_restart",
            decided_by="user_admin",
            expected_decision_version=1,
        )
    assert error.value.code == "RD_IDEMPOTENCY_CONFLICT"
    assert repository.get_rd_collaboration_run(str(seeded["run"]["id"]))["status"] == (
        "waiting_human"
    )


def test_paused_run_wins_race_against_claim_and_claim_terminates(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="pause-claim")
    run_id = str(seeded["run"]["id"])
    work_item_id = "pause-claim-work"
    decision = _decision_record(seeded, decision_id="pause-claim-decision")
    repository.save_decision_request_record(decision)
    repository.save_rd_work_item_record(_work_item(run_id, work_item_id=work_item_id))

    with repository._connect(autocommit=False) as connection:
        connection.execute(
            "SELECT id FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
            (run_id,),
        )
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                repository.claim_ready_work_item,
                work_item_id,
                lease_owner="worker-racing",
            )
            connection.execute(
                """
                UPDATE rd_collaboration_runs
                SET status = 'waiting_human', resume_state = 'running',
                    suspended_decision_request_id = %s, suspended_at = now(),
                    version = version + 1, updated_at = now()
                WHERE id = %s
                """,
                (decision["id"], run_id),
            )
            connection.commit()
            claimed = future.result(timeout=5)

    assert claimed is None
    assert repository.get_rd_work_item(work_item_id)["status"] == "ready"


def test_work_creation_is_insert_only_and_attempt_cannot_cross_items(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="attempt-identity")
    run_id = str(seeded["run"]["id"])
    first = _work_item(run_id, work_item_id="attempt-work-a", status="claimed")
    second = _work_item(run_id, work_item_id="attempt-work-b", status="claimed")
    repository.save_rd_work_item_record(first)
    repository.save_rd_work_item_record(second)

    with pytest.raises(RdCollaborationRepositoryError) as work_conflict:
        repository.save_rd_work_item_record({**first, "title": "divergent replay"})
    assert work_conflict.value.code == "RD_IDEMPOTENCY_CONFLICT"

    with pytest.raises(RdCollaborationRepositoryError) as attempt_conflict:
        repository.save_work_item_attempt_bundle(
            work_item_id="attempt-work-a",
            expected_statuses=["claimed"],
            next_status="running",
            attempt=_attempt("attempt-work-b", attempt_id="attempt-cross-item"),
        )
    assert attempt_conflict.value.code == "RD_IDEMPOTENCY_CONFLICT"
    assert repository.get_rd_work_item_attempt("attempt-cross-item") is None


def _seed_generation_side_effects(
    repository: PostgresSnapshotRepository,
    seeded: dict[str, object],
    *,
    prefix: str,
) -> dict[str, str]:
    run_id = str(seeded["run"]["id"])
    ids = {
        "run": run_id,
        "work": f"{prefix}-work",
        "attempt": f"{prefix}-attempt",
        "task": f"{prefix}-task",
        "review": f"{prefix}-review",
    }
    repository.save_rd_work_item_record(
        _work_item(run_id, work_item_id=ids["work"], status="claimed")
    )
    repository.save_work_item_attempt_bundle(
        work_item_id=ids["work"],
        expected_statuses=["claimed"],
        next_status="running",
        attempt={**_attempt(ids["work"], attempt_id=ids["attempt"]), "status": "running"},
    )
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            """
            INSERT INTO ai_tasks (
              id, brain_app_id, requirement_id, task_type, title, status,
              product_id, version_id, created_by, collaboration_run_id, work_item_id
            )
            VALUES (%s, 'rd_brain', %s, 'technical_solution', %s, 'running',
                    %s, %s, 'user_admin', %s, %s)
            """,
            (
                ids["task"],
                seeded["requirement"],
                ids["task"],
                seeded["product"],
                seeded["version"],
                run_id,
                ids["work"],
            ),
        )
        connection.execute(
            "INSERT INTO human_reviews (id, ai_task_id, stage, status) "
            "VALUES (%s, %s, 'technical_solution', 'pending')",
            (ids["review"], ids["task"]),
        )
    for aggregate_type, aggregate_id in (
        ("rd_collaboration_run", ids["run"]),
        ("rd_work_item", ids["work"]),
        ("rd_work_item_attempt", ids["attempt"]),
        ("ai_task", ids["task"]),
    ):
        command_id = f"{prefix}-command-{aggregate_type}"

        def operation(
            _transaction: Any,
            result_id: str = aggregate_id,
            secret_id: str = f"{command_id}-secret",
        ) -> dict[str, Any]:
            return {
                "result_type": "generation-work",
                "result_id": result_id,
                "http_status": 200,
                "response_json": {"data": {"id": result_id}},
                "claim_replay_secret": {
                    "id": secret_id,
                    "secret_ciphertext": "ciphertext",
                    "key_id": "test-key",
                    "expires_at": datetime.now(UTC) + timedelta(minutes=5),
                },
            }

        repository.execute_idempotent_rd_command(
            command_type="generation-work",
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            idempotency_key=command_id,
            request_hash=command_id,
            command_record_id=command_id,
            operation=operation,
        )
    with repository._connect(autocommit=False) as connection:
        for position, (aggregate_type, aggregate_id, status) in enumerate(
            (
                ("rd_collaboration_run", ids["run"], "pending"),
                ("rd_work_item", ids["work"], "processing"),
                ("rd_work_item_attempt", ids["attempt"], "completed"),
                ("ai_task", ids["task"], "failed"),
            )
        ):
            connection.execute(
                """
                INSERT INTO execution_outbox_events (
                  id, aggregate_type, aggregate_id, event_type,
                  idempotency_key, status
                )
                VALUES (%s, %s, %s, 'generation.dispatch', %s, %s)
                """,
                (
                    f"{prefix}-source-outbox-{position}",
                    aggregate_type,
                    aggregate_id,
                    f"{prefix}-source-outbox-{position}",
                    status,
                ),
            )
    return ids


def test_scope_apply_fences_generation_and_mandates_outbox_audit_and_event(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="scope-fence")
    ids = _seed_generation_side_effects(repository, seeded, prefix="scope-fence")
    request_id = "scope-fence-request"
    repository.create_scope_change_request(**_remove_scope_command(seeded, request_id=request_id))

    result = repository.apply_scope_change_bundle(
        scope_change_request_id=request_id,
        decision="approve_apply_and_restart",
        decided_by="user_admin",
        expected_decision_version=1,
    )

    assert result["run"]["status"] == "cancelled"
    assert repository.get_rd_work_item(ids["work"])["status"] == "cancelled"
    assert repository.get_rd_work_item_attempt(ids["attempt"])["status"] == "cancelled"
    with repository._connect() as connection:
        assert connection.execute(
            "SELECT status FROM ai_tasks WHERE id = %s", (ids["task"],)
        ).fetchone() == ("cancelled",)
        assert connection.execute(
            "SELECT status FROM human_reviews WHERE id = %s", (ids["review"],)
        ).fetchone() == ("cancelled",)
        secrets = connection.execute(
            """
            SELECT secret_ciphertext, scrubbed_at IS NOT NULL
            FROM rd_command_replay_secrets
            ORDER BY id
            """
        ).fetchall()
        assert secrets == [(None, True)] * 4
        source_outboxes = dict(
            connection.execute(
                """
                SELECT id, status FROM execution_outbox_events
                WHERE event_type = 'generation.dispatch'
                """
            ).fetchall()
        )
        assert source_outboxes["scope-fence-source-outbox-0"] == "cancelled"
        assert source_outboxes["scope-fence-source-outbox-3"] == "cancelled"
        assert source_outboxes["scope-fence-source-outbox-1"] == "processing"
        assert source_outboxes["scope-fence-source-outbox-2"] == "completed"
        reconciliation = connection.execute(
            """
            SELECT payload_json->>'source_outbox_id'
            FROM execution_outbox_events
            WHERE event_type = 'rd.scope_change.reconcile_cancellation'
            ORDER BY payload_json->>'source_outbox_id'
            """
        ).fetchall()
        assert reconciliation == [
            ("scope-fence-source-outbox-1",),
            ("scope-fence-source-outbox-2",),
        ]
        assert connection.execute(
            "SELECT event_type FROM audit_events WHERE id = %s",
            (f"audit:scope-change:{request_id}:applied",),
        ).fetchone() == ("rd_scope_change.applied",)
        assert connection.execute(
            "SELECT event_type FROM rd_collaboration_events WHERE id = %s",
            (f"event:scope-change:{request_id}:applied",),
        ).fetchone() == ("scope_change.applied",)
        assert connection.execute(
            "SELECT status FROM execution_outbox_events WHERE idempotency_key = %s",
            (f"scope-change:{request_id}:cancel-generation",),
        ).fetchone() == ("pending",)


def test_scope_apply_failure_after_mandatory_effects_rolls_back_all_fencing(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="scope-fence-rollback")
    ids = _seed_generation_side_effects(
        repository,
        seeded,
        prefix="scope-fence-rollback",
    )
    request_id = "scope-fence-rollback-request"
    repository.create_scope_change_request(**_remove_scope_command(seeded, request_id=request_id))

    def fail(stage: str) -> None:
        if stage == "after_mandatory_effects":
            raise RuntimeError("scope failure injection")

    with pytest.raises(RuntimeError, match="scope failure injection"):
        repository.apply_scope_change_bundle(
            scope_change_request_id=request_id,
            decision="approve_apply_and_restart",
            decided_by="user_admin",
            expected_decision_version=1,
            failure_injection=fail,
        )

    assert repository.get_rd_scope_change_request(request_id)["status"] == "pending_decision"
    assert repository.get_rd_collaboration_run(ids["run"])["status"] == "waiting_human"
    assert repository.get_rd_work_item(ids["work"])["status"] == "running"
    assert repository.get_rd_work_item_attempt(ids["attempt"])["status"] == "running"
    with repository._connect() as connection:
        assert connection.execute(
            "SELECT status FROM ai_tasks WHERE id = %s", (ids["task"],)
        ).fetchone() == ("running",)
        assert connection.execute(
            "SELECT status FROM human_reviews WHERE id = %s", (ids["review"],)
        ).fetchone() == ("pending",)
        assert connection.execute(
            "SELECT count(*) FROM rd_command_replay_secrets WHERE secret_ciphertext IS NULL"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT count(*) FROM audit_events WHERE id = %s",
            (f"audit:scope-change:{request_id}:applied",),
        ).fetchone() == (0,)


def test_run_decision_requires_matching_subject_and_product(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="decision-binding")
    decision = _decision_record(
        seeded,
        decision_id="decision-binding-request",
        subject_id="different-run",
    )
    repository.save_decision_request_record(decision)
    with pytest.raises(RdCollaborationRepositoryError) as error:
        repository.suspend_collaboration_run(
            collaboration_run_id=str(seeded["run"]["id"]),
            decision_request_id="decision-binding-request",
            expected_version=1,
        )
    assert error.value.code == "RD_DECISION_REQUIRED"
    assert repository.get_rd_collaboration_run(str(seeded["run"]["id"]))["status"] == "running"


def test_expiry_successor_must_preserve_subject_product_and_provenance(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="expiry-provenance")
    old = _decision_record(
        seeded,
        decision_id="expiry-provenance-old",
        expires_at=datetime.now(UTC) + timedelta(milliseconds=50),
    )
    repository.save_decision_request_record(old)
    repository.suspend_collaboration_run(
        collaboration_run_id=str(seeded["run"]["id"]),
        decision_request_id="expiry-provenance-old",
        expected_version=1,
    )
    with repository._connect() as connection:
        connection.execute("SELECT pg_sleep(0.08)")
    successor = _decision_record(
        seeded,
        decision_id="expiry-provenance-new",
        subject_id="different-run",
    )
    successor["supersedes_decision_request_id"] = "different-request"
    successor["escalation_level"] = 1
    event = {
        "id": "expiry-provenance-event",
        "collaboration_run_id": seeded["run"]["id"],
        "event_type": "decision.expired",
        "event_key": "decision.expired:expiry-provenance-old",
        "subject_type": "decision_request",
        "subject_id": "expiry-provenance-old",
    }
    with pytest.raises(RdCollaborationRepositoryError) as error:
        repository.expire_and_escalate_decision_request(
            decision_request_id="expiry-provenance-old",
            successor_request=successor,
            expiry_event=event,
        )
    assert error.value.code == "RD_DECISION_REQUIRED"
    assert repository.get_decision_request("expiry-provenance-old")["status"] == "pending"
    assert repository.get_decision_request("expiry-provenance-new") is None


def test_immutable_run_scope_feedback_and_experience_replays_conflict(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="immutable-replay")
    with pytest.raises(RdCollaborationRepositoryError) as scope_error:
        repository.create_collaboration_run_with_exact_scope(
            run=seeded["run"],
            scope_rows=[
                {
                    **seeded["scope"],
                    "acceptance_criteria_hash": "divergent-acceptance",
                }
            ],
        )
    assert scope_error.value.code == "RD_IDEMPOTENCY_CONFLICT"

    run_id = str(seeded["run"]["id"])
    repository.save_rd_collaboration_event_record(
        {
            "id": "immutable-feedback-event",
            "collaboration_run_id": run_id,
            "event_type": "feedback.created",
            "event_key": "immutable-feedback-event",
            "subject_type": "rd_collaboration_run",
            "subject_id": run_id,
        }
    )
    feedback = {
        "id": "immutable-feedback",
        "brain_app_id": "rd_brain",
        "product_id": seeded["product"],
        "collaboration_run_id": run_id,
        "feedback_kind": "review",
        "source_event_id": "immutable-feedback-event",
        "feedback_fingerprint": "immutable-fingerprint",
        "role_code": "developer",
        "human_user_id": "user_admin",
        "strategy_snapshot_id": seeded["version_snapshot"]["id"],
        "producer_subject_type": "service",
        "producer_subject_id": "quality_gate",
    }
    repository.save_role_feedback_once(feedback)
    with pytest.raises(RdCollaborationRepositoryError) as feedback_error:
        repository.save_role_feedback_once({**feedback, "role_code": "reviewer"})
    assert feedback_error.value.code == "RD_IDEMPOTENCY_CONFLICT"

    experience = {
        "id": "immutable-experience",
        "experience_key": "developer:immutable",
        "brain_app_id": "rd_brain",
        "product_scope": [seeded["product"]],
        "role_code": "developer",
        "work_item_type": "implementation",
        "scenario": "immutable",
        "risk_scope": {"maximum": "high"},
        "content": {"guidance": "original"},
        "strategy_snapshot_id": seeded["version_snapshot"]["id"],
        "confidence": 0.9,
        "status": "pending",
    }
    sources = [
        {
            "id": "immutable-experience-source",
            "experience_id": experience["id"],
            "role_feedback_record_id": feedback["id"],
            "strategy_snapshot_id": seeded["version_snapshot"]["id"],
        }
    ]
    repository.save_rd_role_experience_record(experience, sources=sources)
    with pytest.raises(RdCollaborationRepositoryError) as experience_error:
        repository.save_rd_role_experience_record(
            {**experience, "content": {"guidance": "divergent"}},
            sources=sources,
        )
    assert experience_error.value.code == "RD_IDEMPOTENCY_CONFLICT"


def test_experience_requires_nonempty_relational_sources(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="experience-sources")
    with pytest.raises(RdCollaborationRepositoryError) as error:
        repository.save_rd_role_experience_record(
            {
                "id": "experience-without-source",
                "experience_key": "developer:no-source",
                "brain_app_id": "rd_brain",
                "product_scope": [seeded["product"]],
                "role_code": "developer",
                "work_item_type": "implementation",
                "scenario": "no-source",
                "risk_scope": {},
                "content": {"guidance": "invalid"},
                "strategy_snapshot_id": seeded["version_snapshot"]["id"],
                "confidence": 0.5,
                "status": "pending",
            },
            sources=[],
        )
    assert error.value.code == "RD_EXPERIENCE_INVALID"
    assert repository.get_rd_role_experience_record("experience-without-source") is None


def test_legacy_policy_round_trip_preserves_fields_and_collaboration_list_is_explicit(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="legacy-policy-base")
    policy_id = str(seeded["policy"]["id"])
    audit_id = "legacy-policy-audit"
    updated = repository.save_rd_task_executor_policy_record(
        {
            **repository.get_rd_task_executor_policy(policy_id),
            "autonomy_mode": "autonomous_loop",
            "max_iterations": 7,
            "max_duration_seconds": 7200,
            "token_budget": 12345,
            "cost_budget": 42.5,
            "quality_gate_policy_id": None,
            "auto_merge_risk_threshold": "medium",
        },
        expected_policy_version=1,
        audit_event={
            "id": audit_id,
            "event_type": "rd_task_executor_policy.updated",
            "actor_id": "user_admin",
            "subject_type": "rd_task_executor_policy",
            "subject_id": policy_id,
            "payload": {},
        },
    )
    assert updated["policy_version"] == 2
    legacy = next(
        item
        for item in repository.list_rd_task_executor_policies(product_id=str(seeded["product"]))
        if item["id"] == policy_id
    )
    assert legacy["autonomy_mode"] == "autonomous_loop"
    assert legacy["max_iterations"] == 7
    assert legacy["max_duration_seconds"] == 7200
    assert legacy["token_budget"] == 12345
    assert legacy["cost_budget"] == 42.5
    assert legacy["auto_merge_risk_threshold"] == "medium"
    collaboration = repository.list_rd_collaboration_task_executor_policies(
        brain_app_id="rd_brain",
        product_id=str(seeded["product"]),
        status="active",
    )
    assert [(item["id"], item["policy_version"]) for item in collaboration] == [(policy_id, 2)]
    with repository._connect() as connection:
        assert connection.execute(
            "SELECT event_type FROM audit_events WHERE id = %s", (audit_id,)
        ).fetchone() == ("rd_task_executor_policy.updated",)


def test_protocol_has_explicit_task3_signatures() -> None:
    required = {
        "list_rd_scope_change_requests",
        "restart_terminal_collaboration_run",
        "save_assessment_bundle",
        "save_work_item_attempt_bundle",
        "dispatch_work_item_execution_bundle",
        "cancel_work_item_bundle",
        "suspend_collaboration_run",
        "answer_decision_request",
        "expire_and_escalate_decision_request",
        "decide_role_experience",
    }
    assert required.issubset(RdCollaborationRepository.__dict__)
    critical = {
        "create_scope_change_request",
        "apply_scope_change_bundle",
        "dispatch_work_item_execution_bundle",
        "claim_ready_work_item",
        "execute_idempotent_rd_command",
        "apply_decision_bundle",
    }
    for method_name in critical:
        signature = inspect.signature(getattr(RdCollaborationRepository, method_name))
        assert all(
            parameter.kind is not inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        ), method_name


def test_high_risk_cancel_requires_decision_bound_to_same_work_and_product(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="cancel-binding")
    run_id = str(seeded["run"]["id"])
    repository.save_rd_work_item_record(
        _work_item(run_id, work_item_id="cancel-binding-work", status="running")
    )
    decision = _decision_record(
        seeded,
        decision_id="cancel-binding-decision",
        subject_type="rd_work_item",
        subject_id="different-work",
    )
    with pytest.raises(RdCollaborationRepositoryError) as error:
        repository.cancel_work_item_bundle(
            work_item_id="cancel-binding-work",
            expected_version=1,
            high_risk=True,
            decision_request=decision,
        )
    assert error.value.code == "RD_DECISION_REQUIRED"
    assert repository.get_rd_work_item("cancel-binding-work")["status"] == "running"
    assert repository.get_decision_request("cancel-binding-decision") is None


def test_answer_requires_decision_bound_to_existing_subject_and_product(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="answer-binding")
    decision = _decision_record(
        seeded,
        decision_id="answer-binding-decision",
        subject_id="different-run",
        status="waiting_more_info",
    )
    repository.save_decision_request_record(decision)
    with pytest.raises(RdCollaborationRepositoryError) as error:
        repository.answer_decision_request(
            decision_request_id="answer-binding-decision",
            expected_version=1,
            actor_id="user_admin",
            actor_role_codes=[],
            actor_seat_ids=[],
            answer_json={"detail": "complete"},
            evidence_json=[],
            options_json=decision["options_json"],
            options_hash="answer-binding-options-v2",
        )
    assert error.value.code == "RD_DECISION_REQUIRED"
    assert repository.get_decision_request("answer-binding-decision")["status"] == (
        "waiting_more_info"
    )


def test_concurrent_restart_has_one_generation_winner_and_terminates(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(
        repository,
        prefix="restart-race",
        run_status="failed",
        version_status="active",
    )
    terminal_run_id = str(seeded["run"]["id"])

    def restart(suffix: str) -> dict[str, Any] | str:
        run = {
            **seeded["run"],
            "id": f"restart-race-run-g2-{suffix}",
            "run_generation": 2,
            "supersedes_run_id": terminal_run_id,
            "status": "draft",
        }
        scope = {
            **seeded["scope"],
            "id": f"restart-race-scope-g2-{suffix}",
            "collaboration_run_id": run["id"],
        }
        try:
            return repository.restart_terminal_collaboration_run(
                terminal_run_id=terminal_run_id,
                run=run,
                scope_rows=[scope],
            )
        except RdCollaborationRepositoryError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(restart, suffix) for suffix in ("a", "b")]
        results = [future.result(timeout=5) for future in futures]
    assert sum(isinstance(result, dict) for result in results) == 1
    assert results.count("RD_RUN_RESTART_NOT_ALLOWED") == 1
    assert (
        len(repository.list_rd_collaboration_runs(product_version_id=str(seeded["version"]))) == 2
    )


def test_scope_reject_mandates_atomic_audit_and_collaboration_event(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="scope-reject-effects")
    request_id = "scope-reject-effects-request"
    repository.create_scope_change_request(**_remove_scope_command(seeded, request_id=request_id))
    repository.apply_scope_change_bundle(
        scope_change_request_id=request_id,
        decision="reject_keep_current_scope",
        decided_by="user_admin",
        expected_decision_version=1,
    )
    with repository._connect() as connection:
        assert connection.execute(
            "SELECT event_type FROM audit_events WHERE id = %s",
            (f"audit:scope-change:{request_id}:rejected",),
        ).fetchone() == ("rd_scope_change.rejected",)
        assert connection.execute(
            "SELECT event_type FROM rd_collaboration_events WHERE id = %s",
            (f"event:scope-change:{request_id}:rejected",),
        ).fetchone() == ("scope_change.rejected",)
