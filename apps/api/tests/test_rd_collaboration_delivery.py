from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.api.deps import api_error
from app.core.store import MemoryStore
from app.services.rd_git_delivery import (
    finalize_ready_for_release_target,
    list_run_git_deliveries,
    record_ready_for_release_evidence,
    record_version_git_delivery,
    record_version_git_delivery_from_runner,
    verify_version_git_delivery,
)


def _delivery_store(*, delivery_target: str = "ready_for_release") -> MemoryStore:
    store = MemoryStore()
    store.products["product-1"] = {"id": "product-1", "name": "交付产品"}
    store.product_versions["version-1"] = {
        "id": "version-1",
        "product_id": "product-1",
        "status": "testing",
    }
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "product_version_id": "version-1",
        "status": "verifying",
        "strategy_snapshot_id": "snapshot-1",
        "delivery_target": delivery_target,
    }
    store.rd_work_items.update(
        {
            "coding-1": {
                "id": "coding-1",
                "collaboration_run_id": "run-1",
                "work_item_type": "coding",
                "status": "completed",
            },
            "integration-1": {
                "id": "integration-1",
                "collaboration_run_id": "run-1",
                "work_item_type": "integration",
                "status": "completed",
            },
        }
    )
    return store


def _persist_verified_callback(
    store: MemoryStore,
    *,
    delivery_id: str,
    remote_commit_sha: str,
    working_branch: str,
    repository_id: str = "repo-1",
    product_id: str = "product-1",
) -> dict[str, object]:
    callback = {
        "id": f"webhook:{delivery_id}:{remote_commit_sha}:{working_branch}",
        "provider": "gitlab",
        "signature_status": "verified",
        "payload_hash": "sha256:verified-webhook",
        "payload": {
            "after": remote_commit_sha,
            "ref": f"refs/heads/{working_branch}",
            "ai_brain": {"rd_delivery_id": delivery_id},
            "_context": {
                "product_id": product_id,
                "repository_id": repository_id,
                "repository_provider": "gitlab",
                "repository_ref": working_branch,
            },
        },
    }
    store.external_event_inbox[str(callback["id"])] = callback
    return callback


def _record_verified_delivery(store: MemoryStore) -> dict[str, object]:
    delivery = record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="coding-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="rd/run-1/coding-1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        merge_request_id="42",
        workspace_isolation={
            "worktree_path": "/tmp/rd/run-1/coding-1",
            "branch": "rd/run-1/coding-1",
            "status": "isolated",
        },
    )
    assert delivery["outbox"]["event_type"] == "rd.git_delivery.push_requested"
    callback = _persist_verified_callback(
        store,
        delivery_id=str(delivery["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        working_branch="rd/run-1/coding-1",
    )
    return verify_version_git_delivery(
        store,
        inbox_event_id=str(callback["id"]),
        inbox_event_payload_hash=str(callback["payload_hash"]),
    )


def _runner_delivery_fixture(
    *,
    envelope: str | None,
    work_item_id: str = "integration-1",
) -> tuple[MemoryStore, dict[str, object], dict[str, object]]:
    store = _delivery_store()
    store.product_git_repositories["repo-1"] = {
        "id": "repo-1",
        "product_id": "product-1",
        "git_provider": "gitlab",
        "default_branch": "main",
        "status": "active",
    }
    store.product_version_branch_configs["branch-1"] = {
        "id": "branch-1",
        "product_id": "product-1",
        "version_id": "version-1",
        "repository_id": "repo-1",
        "base_branch": "main",
        "working_branch": "release/v1",
        "repository_provider": "gitlab",
        "repository_default_branch": "main",
    }
    ai_task = {
        "id": f"ai-task-{work_item_id}",
        "collaboration_run_id": "run-1",
        "work_item_id": work_item_id,
    }
    local_result = {
        "callback": {"signature_status": "verified"},
        "git_delivery": {
            "local_commit_sha": f"local-{work_item_id}",
            "remote_commit_sha": "forged-remote-sha",
            "reconciliation_id": "forged-reconciliation",
            "working_branch": f"rd/run-1/{work_item_id}",
        },
        "reconciliation": {"remote_commit_sha": "forged-reconciled-sha"},
        "summary": "native Runner result",
        "test_evidence": {
            "callback": "forged-test-callback",
            "status": "passed",
            "suite": "rd-delivery-e2e",
        },
    }
    result_json = local_result if envelope is None else {envelope: local_result}
    runner_task = {
        "id": f"runner-task-{work_item_id}",
        "ai_task_id": ai_task["id"],
        "status": "succeeded",
        "runner_id": "runner-1",
        "workspace_root": "/workspace",
        "input_payload": {
            "rd_collaboration_run_id": "run-1",
            "rd_work_item_id": work_item_id,
            "rd_execution_policy_snapshot": {
                "git_config": {
                    "provider": "gitlab",
                    "repository_id": "repo-1",
                    "workspace_root": "/workspace",
                }
            },
        },
        "result_json": result_json,
    }
    return store, ai_task, runner_task


@pytest.mark.parametrize("envelope", [None, "result", "parsed_output"])
def test_runner_delivery_accepts_native_local_result_shapes_and_ignores_remote_claims(
    envelope: str | None,
) -> None:
    store, ai_task, runner_task = _runner_delivery_fixture(envelope=envelope)

    recorded = record_version_git_delivery_from_runner(
        store,
        ai_task=ai_task,
        runner_task=runner_task,
    )

    assert recorded is not None
    delivery = recorded["delivery"]
    assert delivery["local_commit_sha"] == "local-integration-1"
    assert delivery["working_branch"] == "rd/run-1/integration-1"
    assert delivery["remote_commit_sha"] is None
    assert delivery["reconciliation_status"] == "pending"
    assert delivery["test_evidence"] == {
        "status": "passed",
        "suite": "rd-delivery-e2e",
    }
    persisted = repr(
        {
            "delivery": store.rd_git_deliveries,
            "outbox": store.execution_outbox_events,
            "reconciliations": store.rd_git_delivery_reconciliations,
        }
    )
    for forged in (
        "forged-remote-sha",
        "forged-reconciliation",
        "forged-reconciled-sha",
        "forged-test-callback",
        "signature_status",
    ):
        assert forged not in persisted


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        ("branch", "RD_GIT_DELIVERY_ISOLATION_REQUIRED"),
        ("repository", "RD_DELIVERY_EVIDENCE_MISMATCH"),
        ("workspace", "RD_DELIVERY_EVIDENCE_MISMATCH"),
    ],
)
def test_nested_runner_delivery_still_enforces_frozen_execution_bindings(
    mutate: str,
    expected_code: str,
) -> None:
    store, ai_task, runner_task = _runner_delivery_fixture(
        envelope="result",
        work_item_id="coding-1",
    )
    if mutate == "branch":
        runner_task["result_json"]["result"]["git_delivery"]["working_branch"] = "main"
    elif mutate == "repository":
        runner_task["input_payload"]["rd_execution_policy_snapshot"]["git_config"][
            "repository_id"
        ] = "repo-other"
    else:
        runner_task["workspace_root"] = "/workspace-other"

    with pytest.raises(type(api_error(409, expected_code, "mismatch"))) as rejected:
        record_version_git_delivery_from_runner(
            store,
            ai_task=ai_task,
            runner_task=runner_task,
        )

    assert rejected.value.detail["code"] == expected_code


def test_run_delivery_projection_keeps_pending_remote_evidence_empty_and_redacted() -> None:
    store = _delivery_store()
    created = record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="coding-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="rd/run-1/coding-1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        workspace_isolation={
            "worktree_path": "/tmp/private-worktree",
            "branch": "rd/run-1/coding-1",
            "status": "isolated",
        },
        source_runner_id="secret-runner",
        source_runner_task_id="secret-runner-task",
        push_approval={"token": "secret-approval"},
    )

    projection = list_run_git_deliveries(store, collaboration_run_id="run-1")

    assert projection["total"] == 1
    item = projection["items"][0]
    assert item == {
        "evidence_hash": created["delivery"]["evidence_hash"],
        "id": created["delivery"]["id"],
        "local_commit_sha": "local-sha-1",
        "provider": "gitlab",
        "reconciliation_evidence_hash": None,
        "reconciliation_id": None,
        "reconciliation_status": "pending",
        "remote_commit_sha": None,
        "repository_id": "repo-1",
        "test_evidence": {},
        "verified_at": None,
        "work_item_id": "coding-1",
        "work_item_type": "coding",
        "working_branch": "rd/run-1/coding-1",
    }
    serialized = repr(projection)
    for secret in (
        "/tmp/private-worktree",
        "secret-approval",
        "secret-runner",
        "secret-runner-task",
    ):
        assert secret not in serialized
    assert "outbox_event_id" not in item
    assert "workspace_isolation" not in item
    assert "push_approval" not in item


def test_run_delivery_projection_materializes_complete_reconciled_chain() -> None:
    store = _delivery_store()
    verified = _record_verified_delivery(store)

    projection = list_run_git_deliveries(store, collaboration_run_id="run-1")

    assert projection["total"] == 1
    item = projection["items"][0]
    assert item["id"] == verified["delivery"]["id"]
    assert item["local_commit_sha"] == "local-sha-1"
    assert item["remote_commit_sha"] == item["local_commit_sha"]
    assert item["reconciliation_id"] == verified["reconciliation"]["id"]
    assert item["reconciliation_status"] == "reconciled"
    assert item["verified_at"]
    assert item["evidence_hash"]
    assert item["reconciliation_evidence_hash"]


def test_run_delivery_projection_filters_other_collaboration_runs() -> None:
    store = _delivery_store()
    _record_verified_delivery(store)
    other = dict(next(iter(store.rd_git_deliveries.values())))
    other["id"] = "other-delivery"
    other["collaboration_run_id"] = "other-run"
    store.rd_git_deliveries[other["id"]] = other

    projection = list_run_git_deliveries(store, collaboration_run_id="run-1")

    assert projection["total"] == 1
    assert [item["id"] for item in projection["items"]] != ["other-delivery"]


def test_coding_delivery_requires_an_isolated_worktree_and_creates_push_outbox() -> None:
    store = _delivery_store()

    with pytest.raises(
        type(api_error(422, "RD_GIT_DELIVERY_ISOLATION_REQUIRED", "missing"))
    ) as missing_isolation:
        record_version_git_delivery(
            store,
            collaboration_run_id="run-1",
            work_item_id="coding-1",
            repository_id="repo-1",
            provider="gitlab",
            working_branch="shared-main",
            version_branch="release/v1",
            target_branch="main",
            local_commit_sha="local-sha-1",
        )

    assert missing_isolation.value.detail["code"] == "RD_GIT_DELIVERY_ISOLATION_REQUIRED"

    result = record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="coding-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="rd/run-1/coding-1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        pull_request_id="9",
        workspace_isolation={
            "worktree_path": "/tmp/rd/run-1/coding-1",
            "branch": "rd/run-1/coding-1",
            "status": "isolated",
        },
    )

    delivery = result["delivery"]
    assert delivery["repository_id"] == "repo-1"
    assert delivery["local_commit_sha"] == "local-sha-1"
    assert delivery["remote_commit_sha"] is None
    assert delivery["pull_request_id"] == "9"
    assert result["outbox"]["id"] in store.execution_outbox_events


def test_reconciliation_rejects_caller_supplied_remote_sha_without_verified_callback() -> None:
    store = _delivery_store()
    record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="coding-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="rd/run-1/coding-1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        workspace_isolation={
            "worktree_path": "/tmp/rd/run-1/coding-1",
            "branch": "rd/run-1/coding-1",
            "status": "isolated",
        },
    )

    error_type = type(api_error(403, "RD_GIT_DELIVERY_CALLBACK_UNTRUSTED", "missing"))
    with pytest.raises(error_type) as exc:
        verify_version_git_delivery(
            store,
            inbox_event_id="missing-persisted-callback",
            inbox_event_payload_hash="sha256:missing-persisted-callback",
        )

    assert exc.value.detail["code"] == "RD_GIT_DELIVERY_CALLBACK_UNTRUSTED"


def test_reconciliation_rejects_a_forged_verified_callback_dict() -> None:
    """Only a persisted Inbox fact may attest to a remote Git callback."""
    store = _delivery_store()
    record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="coding-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="rd/run-1/coding-1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        workspace_isolation={
            "worktree_path": "/tmp/rd/run-1/coding-1",
            "branch": "rd/run-1/coding-1",
            "status": "isolated",
        },
    )

    with pytest.raises(
        type(api_error(403, "RD_GIT_DELIVERY_CALLBACK_UNTRUSTED", "missing"))
    ) as rejected:
        verify_version_git_delivery(
            store,
            inbox_event_id="forged-verified-callback",
            inbox_event_payload_hash="sha256:verified-webhook",
        )

    assert rejected.value.detail["code"] == "RD_GIT_DELIVERY_CALLBACK_UNTRUSTED"


def test_reconciliation_rejects_persisted_callback_from_another_repository_or_branch() -> None:
    store = _delivery_store()
    delivery = record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="coding-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="rd/run-1/coding-1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        workspace_isolation={
            "worktree_path": "/tmp/rd/run-1/coding-1",
            "branch": "rd/run-1/coding-1",
            "status": "isolated",
        },
    )
    wrong_binding = _persist_verified_callback(
        store,
        delivery_id=str(delivery["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        repository_id="repo-other",
        working_branch="rd/run-1/another-work-item",
    )

    with pytest.raises(
        type(api_error(409, "RD_DELIVERY_EVIDENCE_MISMATCH", "missing"))
    ) as rejected:
        verify_version_git_delivery(
            store,
            inbox_event_id=str(wrong_binding["id"]),
            inbox_event_payload_hash=str(wrong_binding["payload_hash"]),
        )

    assert rejected.value.detail["code"] == "RD_DELIVERY_EVIDENCE_MISMATCH"


def test_runner_delivery_outbox_and_signed_provider_callback_form_the_only_remote_path() -> None:
    from app.services.external_event_projectors import project_external_event
    from app.services.operational_deployments import process_execution_outbox_events

    store = _delivery_store()
    store.product_git_repositories["repo-1"] = {
        "id": "repo-1",
        "product_id": "product-1",
        "git_provider": "gitlab",
        "remote_url": "https://git.example.test/group/delivery.git",
        "project_path": "group/delivery",
        "status": "active",
    }
    now = datetime.now(UTC)
    store.ai_executor_runners["runner-1"] = {
        "id": "runner-1",
        "executor_types": ["codex"],
        "status": "active",
        "workspace_roots": ["/tmp/rd"],
    }
    store.ai_executor_tasks["runner-source-1"] = {
        "id": "runner-source-1",
        "ai_task_id": "task-1",
        "created_by": "user_admin",
        "executor_type": "codex",
        "runner_id": "runner-1",
        "status": "succeeded",
        "timeout_seconds": 600,
        "workspace_root": "/tmp/rd/run-1/coding-1",
    }
    approval = {
        "approval_id": "approval-git-push-1",
        "approved": True,
        "approved_at": now.isoformat(),
        "approved_by": "user_admin",
        "approved_operations": ["git_push_or_merge"],
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "mode": "platform_human_approval",
        "policy_version": "runner_safety_v1",
    }
    created = record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="coding-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="rd/run-1/coding-1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        workspace_isolation={
            "worktree_path": "/tmp/rd/run-1/coding-1",
            "branch": "rd/run-1/coding-1",
            "status": "isolated",
        },
        source_runner_id="runner-1",
        source_runner_task_id="runner-source-1",
        push_approval=approval,
    )

    assert process_execution_outbox_events(store, worker_id="worker-1") == 1
    push_task_id = store.execution_outbox_events[created["outbox"]["id"]]["payload"][
        "push_runner_task_id"
    ]
    push_task = store.ai_executor_tasks[push_task_id]
    assert push_task["task_kind"] == "git_push"
    assert push_task["input_payload"]["local_commit_sha"] == "local-sha-1"
    assert "remote_commit_sha" not in push_task["input_payload"]

    callback = _persist_verified_callback(
        store,
        delivery_id=str(created["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        working_branch="rd/run-1/coding-1",
    )
    callback["payload"]["project"] = {"path_with_namespace": "group/delivery"}
    with pytest.raises(
        type(api_error(409, "RD_DELIVERY_EVIDENCE_INCOMPLETE", "missing"))
    ) as incomplete:
        project_external_event(store, event=callback)

    assert incomplete.value.detail["code"] == "RD_DELIVERY_EVIDENCE_INCOMPLETE"
    reconciled = _materialized_delivery(store, str(created["delivery"]["id"]))
    assert reconciled["remote_commit_sha"] == "local-sha-1"


def test_incomplete_callback_is_retryable_instead_of_being_marked_completed() -> None:
    """A remote push may arrive before the durable integration phase is ready."""
    from app.services.external_event_projectors import project_external_event

    store = _delivery_store()
    store.product_git_repositories["repo-1"] = {
        "id": "repo-1",
        "product_id": "product-1",
        "git_provider": "gitlab",
        "remote_url": "https://git.example.test/group/delivery.git",
        "project_path": "group/delivery",
        "status": "active",
    }
    delivery = record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="coding-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="rd/run-1/coding-1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        workspace_isolation={
            "worktree_path": "/tmp/rd/run-1/coding-1",
            "branch": "rd/run-1/coding-1",
            "status": "isolated",
        },
    )
    callback = _persist_verified_callback(
        store,
        delivery_id=str(delivery["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        working_branch="rd/run-1/coding-1",
    )
    callback["payload"]["project"] = {"path_with_namespace": "group/delivery"}

    with pytest.raises(
        type(api_error(409, "RD_DELIVERY_EVIDENCE_INCOMPLETE", "missing"))
    ) as incomplete:
        project_external_event(store, event=callback)

    assert incomplete.value.detail["code"] == "RD_DELIVERY_EVIDENCE_INCOMPLETE"


def test_inbox_defers_incomplete_delivery_callback_without_consuming_retry_budget() -> None:
    from app.services.external_event_inbox import process_external_event_inbox_events

    store = _delivery_store()
    store.product_git_repositories["repo-1"] = {
        "id": "repo-1",
        "product_id": "product-1",
        "git_provider": "gitlab",
        "remote_url": "https://git.example.test/group/delivery.git",
        "project_path": "group/delivery",
        "status": "active",
    }
    delivery = record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="coding-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="rd/run-1/coding-1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        workspace_isolation={
            "worktree_path": "/tmp/rd/run-1/coding-1",
            "branch": "rd/run-1/coding-1",
            "status": "isolated",
        },
    )
    callback = _persist_verified_callback(
        store,
        delivery_id=str(delivery["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        working_branch="rd/run-1/coding-1",
    )
    callback.update(
        {
            "attempt_count": 0,
            "error_message": None,
            "lease_owner": None,
            "lease_until": None,
            "received_at": datetime.now(UTC).isoformat(),
            "processed_at": None,
            "status": "pending",
            "updated_at": datetime.now(UTC).isoformat(),
        }
    )
    callback["payload"]["project"] = {"path_with_namespace": "group/delivery"}

    assert process_external_event_inbox_events(store, worker_id="delivery-worker") == 0
    deferred = store.external_event_inbox[str(callback["id"])]
    assert deferred["status"] == "pending"
    assert deferred["attempt_count"] == 0
    assert deferred["lease_until"] is not None
    assert deferred["error_message"] == "RD_DELIVERY_EVIDENCE_INCOMPLETE"


def _materialized_delivery(store: MemoryStore, delivery_id: str) -> dict[str, object]:
    delivery = next(
        item for item in store.rd_git_deliveries.values() if item.get("id") == delivery_id
    )
    reconciliation = next(
        item
        for item in store.rd_git_delivery_reconciliations.values()
        if item.get("delivery_id") == delivery_id
    )
    return {**delivery, "remote_commit_sha": reconciliation["remote_commit_sha"]}


def test_ready_evidence_requires_reconciled_remote_and_version_integration_tests() -> None:
    store = _delivery_store()
    verified = _record_verified_delivery(store)

    with pytest.raises(
        type(api_error(409, "RD_DELIVERY_EVIDENCE_INCOMPLETE", "missing"))
    ) as missing_integration:
        record_ready_for_release_evidence(store, collaboration_run_id="run-1")
    assert missing_integration.value.detail["code"] == "RD_DELIVERY_EVIDENCE_INCOMPLETE"

    integration = record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="integration-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="release/v1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        test_evidence={"suite": "version-integration", "status": "passed", "run_id": "ci-1"},
    )
    integration_callback = _persist_verified_callback(
        store,
        delivery_id=str(integration["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        working_branch="release/v1",
    )
    verify_version_git_delivery(
        store,
        inbox_event_id=str(integration_callback["id"]),
        inbox_event_payload_hash=str(integration_callback["payload_hash"]),
    )

    evidence = record_ready_for_release_evidence(store, collaboration_run_id="run-1")

    assert verified["delivery"]["reconciliation_status"] == "reconciled"
    assert evidence["product_version"]["status"] == "ready_for_release"
    assert not any(
        "deploy" in event["event_type"] for event in store.execution_outbox_events.values()
    )


def test_ready_evidence_requires_the_verified_run_phase() -> None:
    store = _delivery_store()
    _record_verified_delivery(store)
    integration = record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="integration-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="release/v1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        test_evidence={"suite": "version-integration", "status": "passed"},
    )
    integration_callback = _persist_verified_callback(
        store,
        delivery_id=str(integration["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        working_branch="release/v1",
    )
    store.rd_collaboration_runs["run-1"]["status"] = "integrating"
    verify_version_git_delivery(
        store,
        inbox_event_id=str(integration_callback["id"]),
        inbox_event_payload_hash=str(integration_callback["payload_hash"]),
    )

    with pytest.raises(
        type(api_error(409, "RD_DELIVERY_EVIDENCE_INCOMPLETE", "missing"))
    ) as incomplete:
        record_ready_for_release_evidence(store, collaboration_run_id="run-1")

    assert incomplete.value.detail["code"] == "RD_DELIVERY_EVIDENCE_INCOMPLETE"


def test_remote_sha_mismatch_and_stale_evidence_cannot_enter_ready_for_release() -> None:
    store = _delivery_store()
    delivery = record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="coding-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="rd/run-1/coding-1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        workspace_isolation={
            "worktree_path": "/tmp/rd/run-1/coding-1",
            "branch": "rd/run-1/coding-1",
            "status": "isolated",
        },
    )

    mismatched_callback = _persist_verified_callback(
        store,
        delivery_id=str(delivery["delivery"]["id"]),
        remote_commit_sha="another-sha",
        working_branch="rd/run-1/coding-1",
    )
    with pytest.raises(
        type(api_error(409, "RD_DELIVERY_EVIDENCE_MISMATCH", "mismatch"))
    ) as mismatch:
        verify_version_git_delivery(
            store,
            inbox_event_id=str(mismatched_callback["id"]),
            inbox_event_payload_hash=str(mismatched_callback["payload_hash"]),
        )
    assert mismatch.value.detail["code"] == "RD_DELIVERY_EVIDENCE_MISMATCH"

    verified = _record_verified_delivery(store)
    integration = record_version_git_delivery(
        store,
        collaboration_run_id="run-1",
        work_item_id="integration-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="release/v1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        test_evidence={"suite": "version-integration", "status": "passed"},
    )
    integration_callback = _persist_verified_callback(
        store,
        delivery_id=str(integration["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        working_branch="release/v1",
    )
    store.rd_git_deliveries[str(verified["delivery"]["id"])]["evidence_stale"] = True
    integration_verified = verify_version_git_delivery(
        store,
        inbox_event_id=str(integration_callback["id"]),
        inbox_event_payload_hash=str(integration_callback["payload_hash"]),
    )

    with pytest.raises(type(api_error(409, "RD_DELIVERY_EVIDENCE_INCOMPLETE", "stale"))) as stale:
        record_ready_for_release_evidence(store, collaboration_run_id="run-1")
    assert stale.value.detail["code"] == "RD_DELIVERY_EVIDENCE_INCOMPLETE"
    assert integration_verified["delivery"]["reconciliation_status"] == "reconciled"
    assert store.product_versions["version-1"]["status"] == "testing"


def test_ready_target_finalizes_without_deployment_but_deployed_target_remains_nonterminal() -> (
    None
):
    ready_store = _delivery_store()
    _record_verified_delivery(ready_store)
    integration = record_version_git_delivery(
        ready_store,
        collaboration_run_id="run-1",
        work_item_id="integration-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="release/v1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        test_evidence={"suite": "version-integration", "status": "passed"},
    )
    ready_callback = _persist_verified_callback(
        ready_store,
        delivery_id=str(integration["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        working_branch="release/v1",
    )
    verify_version_git_delivery(
        ready_store,
        inbox_event_id=str(ready_callback["id"]),
        inbox_event_payload_hash=str(ready_callback["payload_hash"]),
    )
    record_ready_for_release_evidence(ready_store, collaboration_run_id="run-1")

    finalized = finalize_ready_for_release_target(ready_store, collaboration_run_id="run-1")
    assert finalized["run"]["status"] == "completed"
    assert finalized["run"]["completion_reason"] == "ready_for_release"
    assert not any(
        "deploy" in event["event_type"] for event in ready_store.execution_outbox_events.values()
    )

    deployed_store = _delivery_store(delivery_target="deployed")
    _record_verified_delivery(deployed_store)
    deployed_integration = record_version_git_delivery(
        deployed_store,
        collaboration_run_id="run-1",
        work_item_id="integration-1",
        repository_id="repo-1",
        provider="gitlab",
        working_branch="release/v1",
        version_branch="release/v1",
        target_branch="main",
        local_commit_sha="local-sha-1",
        test_evidence={"suite": "version-integration", "status": "passed"},
    )
    deployed_callback = _persist_verified_callback(
        deployed_store,
        delivery_id=str(deployed_integration["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        working_branch="release/v1",
    )
    verify_version_git_delivery(
        deployed_store,
        inbox_event_id=str(deployed_callback["id"]),
        inbox_event_payload_hash=str(deployed_callback["payload_hash"]),
    )
    record_ready_for_release_evidence(deployed_store, collaboration_run_id="run-1")
    pending = finalize_ready_for_release_target(deployed_store, collaboration_run_id="run-1")
    assert pending["run"]["status"] == "ready_for_release"
    assert pending["run"].get("completion_reason") is None
    assert not any(
        "deploy" in event["event_type"] for event in deployed_store.execution_outbox_events.values()
    )
