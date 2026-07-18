from __future__ import annotations

import pytest

from app.api.deps import api_error
from app.core.store import MemoryStore
from app.services.rd_git_delivery import (
    finalize_ready_for_release_target,
    record_ready_for_release_evidence,
    record_version_git_delivery,
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
        "status": "integrating",
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
    return verify_version_git_delivery(
        store,
        delivery_id=str(delivery["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        merge_request_id="42",
        reconciliation_status="reconciled",
    )


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
    verify_version_git_delivery(
        store,
        delivery_id=str(integration["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        reconciliation_status="reconciled",
    )

    evidence = record_ready_for_release_evidence(store, collaboration_run_id="run-1")

    assert verified["delivery"]["reconciliation_status"] == "reconciled"
    assert evidence["product_version"]["status"] == "ready_for_release"
    assert not any(
        "deploy" in event["event_type"] for event in store.execution_outbox_events.values()
    )


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

    with pytest.raises(
        type(api_error(409, "RD_DELIVERY_EVIDENCE_MISMATCH", "mismatch"))
    ) as mismatch:
        verify_version_git_delivery(
            store,
            delivery_id=str(delivery["delivery"]["id"]),
            remote_commit_sha="another-sha",
            reconciliation_status="reconciled",
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
    integration_verified = verify_version_git_delivery(
        store,
        delivery_id=str(integration["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        reconciliation_status="reconciled",
    )
    store.rd_git_deliveries[str(verified["delivery"]["id"])]["evidence_stale"] = True

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
    verify_version_git_delivery(
        ready_store,
        delivery_id=str(integration["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        reconciliation_status="reconciled",
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
    verify_version_git_delivery(
        deployed_store,
        delivery_id=str(deployed_integration["delivery"]["id"]),
        remote_commit_sha="local-sha-1",
        reconciliation_status="reconciled",
    )
    record_ready_for_release_evidence(deployed_store, collaboration_run_id="run-1")
    pending = finalize_ready_for_release_target(deployed_store, collaboration_run_id="run-1")
    assert pending["run"]["status"] == "ready_for_release"
    assert pending["run"].get("completion_reason") is None
    assert not any(
        "deploy" in event["event_type"] for event in deployed_store.execution_outbox_events.values()
    )
