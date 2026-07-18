"""Trusted remote-Git delivery evidence for R&D collaboration runs.

This boundary deliberately *does not* perform a synchronous Git push or a
deployment.  Coding work records its isolated checkout and creates an Outbox
intent.  A provider/worker callback later reconciles the immutable commit
evidence.  Only then can the separate readiness service advance the version.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from app.api.deps import api_error
from app.services.operational_records import read_memory_dict

DELIVERY_RECORD_TYPE = "rd_git_delivery"
RECONCILIATION_RECORD_TYPE = "rd_git_delivery_reconciliation"
READINESS_RECORD_TYPE = "rd_ready_for_release_evidence"
_CODING_WORK_ITEM_TYPES = {"coding", "development", "implementation"}
_INTEGRATION_WORK_ITEM_TYPES = {"integration", "integration_test", "version_integration"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"


def _new_id(store: Any, prefix: str, material: dict[str, Any]) -> str:
    # The deterministic id is also the replay/unique identity in the generic
    # trusted-record store.  A worker may repeat a delivery command safely.
    return f"{prefix}:{_canonical_hash(material).removeprefix('sha256:')[:32]}"


def _repository(store: Any) -> Any | None:
    return getattr(store, "repository", None)


def _records(store: Any, *, record_type: str, collection: str) -> list[dict[str, Any]]:
    repository = _repository(store)
    list_records = getattr(repository, "list_rd_delivery_evidence_records", None)
    if not callable(list_records):
        list_records = getattr(repository, "list_trusted_delivery_records", None)
    if callable(list_records):
        return [dict(record) for record in list_records(record_type=record_type)]
    return [dict(record) for record in read_memory_dict(store, collection).values()]


def _save_record(
    store: Any,
    *,
    record: dict[str, Any],
    record_type: str,
    collection: str,
) -> None:
    repository = _repository(store)
    save_record = getattr(repository, "save_rd_delivery_evidence_record", None)
    if not callable(save_record):
        save_record = getattr(repository, "save_trusted_delivery_record", None)
    if callable(save_record):
        save_record(record=record, record_type=record_type)
    read_memory_dict(store, collection)[record["id"]] = deepcopy(record)


def _run(store: Any, collaboration_run_id: str) -> dict[str, Any]:
    repository = _repository(store)
    get_run = getattr(repository, "get_rd_collaboration_run", None)
    run = get_run(collaboration_run_id) if callable(get_run) else None
    if run is None:
        run = read_memory_dict(store, "rd_collaboration_runs").get(collaboration_run_id)
    if run is None:
        raise api_error(404, "NOT_FOUND", "Collaboration run not found")
    return dict(run)


def _version(store: Any, version_id: str) -> dict[str, Any]:
    repository = _repository(store)
    get_version = getattr(repository, "get_product_version", None)
    version = get_version(version_id) if callable(get_version) else None
    if version is None:
        version = read_memory_dict(store, "product_versions").get(version_id)
    if version is None:
        raise api_error(409, "RD_DELIVERY_EVIDENCE_INCOMPLETE", "Product version is unavailable")
    return dict(version)


def _work_item(store: Any, work_item_id: str) -> dict[str, Any]:
    repository = _repository(store)
    get_item = getattr(repository, "get_rd_work_item", None)
    item = get_item(work_item_id) if callable(get_item) else None
    if item is None:
        item = read_memory_dict(store, "rd_work_items").get(work_item_id)
    if item is None:
        raise api_error(404, "NOT_FOUND", "Collaboration work item not found")
    return dict(item)


def _work_item_type(item: dict[str, Any]) -> str:
    return str(item.get("work_item_type") or "").strip().lower()


def _is_coding(item: dict[str, Any]) -> bool:
    return _work_item_type(item) in _CODING_WORK_ITEM_TYPES


def _is_integration(item: dict[str, Any]) -> bool:
    return _work_item_type(item) in _INTEGRATION_WORK_ITEM_TYPES


def _validate_isolation(
    *,
    target_branch: str,
    version_branch: str,
    working_branch: str,
    workspace_isolation: dict[str, Any] | None,
) -> dict[str, Any]:
    isolation = dict(workspace_isolation or {})
    if (
        isolation.get("status") != "isolated"
        or not str(isolation.get("worktree_path") or "").strip()
        or str(isolation.get("branch") or "") != working_branch
        or working_branch in {target_branch, version_branch}
    ):
        raise api_error(
            422,
            "RD_GIT_DELIVERY_ISOLATION_REQUIRED",
            "Coding delivery requires a dedicated worktree and branch",
        )
    return isolation


def _save_outbox(store: Any, event: dict[str, Any]) -> None:
    repository = _repository(store)
    save_event = getattr(repository, "save_execution_outbox_event_record", None)
    if callable(save_event):
        save_event(event)
    read_memory_dict(store, "execution_outbox_events")[event["id"]] = deepcopy(event)


def _outbox_event(store: Any, event_id: str) -> dict[str, Any] | None:
    repository = _repository(store)
    list_events = getattr(repository, "list_execution_outbox_events", None)
    if callable(list_events):
        for event in list_events(aggregate_id=None, aggregate_type=None, status=None):
            if event.get("id") == event_id:
                return dict(event)
    event = read_memory_dict(store, "execution_outbox_events").get(event_id)
    return dict(event) if event is not None else None


def _delivery_outbox(store: Any, *, delivery: dict[str, Any]) -> dict[str, Any]:
    material = {
        "delivery_id": delivery["id"],
        "local_commit_sha": delivery["local_commit_sha"],
        "repository_id": delivery["repository_id"],
    }
    event_id = _new_id(store, "rd-git-outbox", material)
    existing = _outbox_event(store, event_id)
    if existing is not None:
        return dict(existing)
    now = _now()
    event = {
        "id": event_id,
        "aggregate_type": "rd_git_delivery",
        "aggregate_id": delivery["id"],
        "event_type": "rd.git_delivery.push_requested",
        "idempotency_key": event_id,
        "payload": {
            "collaboration_run_id": delivery["collaboration_run_id"],
            "delivery_id": delivery["id"],
            "local_commit_sha": delivery["local_commit_sha"],
            "merge_request_id": delivery.get("merge_request_id"),
            "product_id": delivery["product_id"],
            "provider": delivery["provider"],
            "pull_request_id": delivery.get("pull_request_id"),
            "repository_id": delivery["repository_id"],
            "target_branch": delivery["target_branch"],
            "version_branch": delivery["version_branch"],
            "working_branch": delivery["working_branch"],
        },
        "status": "pending",
        "attempt_count": 0,
        "available_at": now,
        "lease_owner": None,
        "lease_until": None,
        "last_error": None,
        "created_at": now,
        "updated_at": now,
        "processed_at": None,
    }
    _save_outbox(store, event)
    return event


def record_version_git_delivery(
    store: Any,
    *,
    collaboration_run_id: str,
    work_item_id: str,
    repository_id: str,
    provider: str,
    working_branch: str,
    version_branch: str,
    target_branch: str,
    local_commit_sha: str,
    workspace_isolation: dict[str, Any] | None = None,
    merge_request_id: str | None = None,
    pull_request_id: str | None = None,
    test_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record local delivery facts and queue, but never synchronously push."""
    run = _run(store, collaboration_run_id)
    item = _work_item(store, work_item_id)
    if item.get("collaboration_run_id") != collaboration_run_id:
        raise api_error(409, "RD_DELIVERY_EVIDENCE_INCOMPLETE", "Work item belongs to another run")
    if not repository_id or not provider or not local_commit_sha:
        raise api_error(
            422, "VALIDATION_ERROR", "Repository, provider and local commit are required"
        )
    if _is_coding(item):
        isolation = _validate_isolation(
            target_branch=target_branch,
            version_branch=version_branch,
            working_branch=working_branch,
            workspace_isolation=workspace_isolation,
        )
    else:
        isolation = dict(workspace_isolation or {})
    if _is_integration(item):
        evidence = dict(test_evidence or {})
        if evidence.get("status") != "passed" or not evidence.get("suite"):
            raise api_error(
                422,
                "RD_INTEGRATION_TEST_EVIDENCE_REQUIRED",
                "Integration work must record a passed version-level test suite",
            )
    material = {
        "collaboration_run_id": collaboration_run_id,
        "work_item_id": work_item_id,
        "repository_id": repository_id,
        "working_branch": working_branch,
        "local_commit_sha": local_commit_sha,
        "test_evidence": test_evidence or {},
    }
    delivery_id = _new_id(store, "rd-git-delivery", material)
    existing = next(
        (
            record
            for record in _records(
                store, record_type=DELIVERY_RECORD_TYPE, collection="rd_git_deliveries"
            )
            if record.get("id") == delivery_id
        ),
        None,
    )
    if existing is not None:
        outbox_id = str(existing.get("outbox_event_id") or "")
        outbox = _outbox_event(store, outbox_id)
        return {"delivery": existing, "outbox": dict(outbox or {}), "idempotent_replay": True}
    now = _now()
    delivery = {
        "id": delivery_id,
        "product_id": run["product_id"],
        "collaboration_run_id": collaboration_run_id,
        "product_version_id": run["product_version_id"],
        "work_item_id": work_item_id,
        "work_item_type": _work_item_type(item),
        "repository_id": repository_id,
        "provider": provider,
        "working_branch": working_branch,
        "version_branch": version_branch,
        "target_branch": target_branch,
        "workspace_isolation": isolation,
        "local_commit_sha": local_commit_sha,
        "remote_commit_sha": None,
        "merge_request_id": merge_request_id,
        "pull_request_id": pull_request_id,
        "test_evidence": deepcopy(test_evidence or {}),
        "reconciliation_status": "pending",
        "reconciliation_id": None,
        "verified_at": None,
        "created_at": now,
        "updated_at": now,
    }
    outbox = _delivery_outbox(store, delivery=delivery)
    delivery["outbox_event_id"] = outbox["id"]
    _save_record(
        store,
        record=delivery,
        record_type=DELIVERY_RECORD_TYPE,
        collection="rd_git_deliveries",
    )
    return {"delivery": deepcopy(delivery), "outbox": deepcopy(outbox), "idempotent_replay": False}


def verify_version_git_delivery(
    store: Any,
    *,
    delivery_id: str,
    remote_commit_sha: str,
    reconciliation_status: str,
    merge_request_id: str | None = None,
    pull_request_id: str | None = None,
) -> dict[str, Any]:
    """Record provider reconciliation; a remote mismatch is never trusted."""
    deliveries = _records(store, record_type=DELIVERY_RECORD_TYPE, collection="rd_git_deliveries")
    delivery = next((record for record in deliveries if record.get("id") == delivery_id), None)
    if delivery is None:
        raise api_error(404, "NOT_FOUND", "Git delivery record not found")
    if reconciliation_status != "reconciled" or remote_commit_sha != delivery.get(
        "local_commit_sha"
    ):
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_MISMATCH",
            "Remote Git evidence does not match the recorded local commit",
        )
    now = _now()
    reconciliation = {
        "id": _new_id(
            store,
            "rd-git-reconciliation",
            {"delivery_id": delivery_id, "remote_commit_sha": remote_commit_sha},
        ),
        "product_id": delivery["product_id"],
        "delivery_id": delivery_id,
        "collaboration_run_id": delivery["collaboration_run_id"],
        "repository_id": delivery["repository_id"],
        "local_commit_sha": delivery["local_commit_sha"],
        "remote_commit_sha": remote_commit_sha,
        "status": "reconciled",
        "created_at": now,
        "updated_at": now,
    }
    _save_record(
        store,
        record=reconciliation,
        record_type=RECONCILIATION_RECORD_TYPE,
        collection="rd_git_delivery_reconciliations",
    )
    verified = {
        **delivery,
        "remote_commit_sha": remote_commit_sha,
        "merge_request_id": merge_request_id or delivery.get("merge_request_id"),
        "pull_request_id": pull_request_id or delivery.get("pull_request_id"),
        "reconciliation_id": reconciliation["id"],
        "reconciliation_status": "reconciled",
        "verified_at": now,
        "updated_at": now,
    }
    _save_record(
        store,
        record=verified,
        record_type=DELIVERY_RECORD_TYPE,
        collection="rd_git_deliveries",
    )
    outbox_id = verified.get("outbox_event_id")
    outbox = _outbox_event(store, str(outbox_id))
    if outbox is not None:
        completed_outbox = {
            **outbox,
            "status": "completed",
            "processed_at": now,
            "updated_at": now,
            "payload": {
                **dict(outbox.get("payload") or {}),
                "reconciliation_id": reconciliation["id"],
            },
        }
        _save_outbox(store, completed_outbox)
    return {
        "delivery": deepcopy(verified),
        "reconciliation": deepcopy(reconciliation),
    }


def _evidence_is_fresh(run: dict[str, Any], delivery: dict[str, Any]) -> bool:
    if delivery.get("evidence_stale"):
        return False
    raw_verified_at = delivery.get("verified_at")
    if not raw_verified_at:
        return False
    try:
        verified_at = datetime.fromisoformat(str(raw_verified_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=UTC)
    max_age = int(run.get("delivery_evidence_max_age_seconds") or 86400)
    return verified_at >= datetime.now(UTC) - timedelta(seconds=max_age)


def _assert_trusted_delivery_evidence(store: Any, *, run: dict[str, Any]) -> list[dict[str, Any]]:
    deliveries = [
        record
        for record in _records(
            store, record_type=DELIVERY_RECORD_TYPE, collection="rd_git_deliveries"
        )
        if record.get("collaboration_run_id") == run["id"]
    ]
    coding = [
        record for record in deliveries if record.get("work_item_type") in _CODING_WORK_ITEM_TYPES
    ]
    integration = [
        record
        for record in deliveries
        if record.get("work_item_type") in _INTEGRATION_WORK_ITEM_TYPES
    ]
    if not coding or not integration:
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_INCOMPLETE",
            "Trusted remote delivery and version integration evidence are required",
        )
    for delivery in coding + integration:
        if (
            delivery.get("reconciliation_status") != "reconciled"
            or delivery.get("remote_commit_sha") != delivery.get("local_commit_sha")
            or not delivery.get("reconciliation_id")
            or not _evidence_is_fresh(run, delivery)
        ):
            raise api_error(
                409,
                "RD_DELIVERY_EVIDENCE_INCOMPLETE",
                "Remote delivery evidence is missing, stale or mismatched",
            )
    if not any(
        isinstance(record.get("test_evidence"), dict)
        and record["test_evidence"].get("status") == "passed"
        and record["test_evidence"].get("suite")
        for record in integration
    ):
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_INCOMPLETE",
            "A passed version-level integration test is required",
        )
    return deliveries


def _persist_ready_status(
    store: Any,
    *,
    collaboration_run_id: str,
    finalize: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    repository = _repository(store)
    method_name = (
        "finalize_rd_ready_for_release_target" if finalize else "mark_rd_ready_for_release"
    )
    operation = getattr(repository, method_name, None)
    if callable(operation):
        result = operation(collaboration_run_id=collaboration_run_id)
        return dict(result["run"]), dict(result["product_version"])
    run = _run(store, collaboration_run_id)
    version = _version(store, str(run["product_version_id"]))
    if version.get("status") not in {"testing", "active", "ready_for_release"}:
        raise api_error(
            409, "RD_DELIVERY_EVIDENCE_INCOMPLETE", "Version cannot enter ready for release"
        )
    version["status"] = "ready_for_release"
    version["updated_at"] = _now()
    run["status"] = "ready_for_release"
    run["updated_at"] = _now()
    if finalize and str(run.get("delivery_target") or "ready_for_release") == "ready_for_release":
        run["status"] = "completed"
        run["completion_reason"] = "ready_for_release"
        run["completed_at"] = _now()
    read_memory_dict(store, "product_versions")[version["id"]] = deepcopy(version)
    read_memory_dict(store, "rd_collaboration_runs")[run["id"]] = deepcopy(run)
    return run, version


def record_ready_for_release_evidence(store: Any, *, collaboration_run_id: str) -> dict[str, Any]:
    """Verify immutable remote/test evidence and enter, but do not finish, ready state."""
    run = _run(store, collaboration_run_id)
    deliveries = _assert_trusted_delivery_evidence(store, run=run)
    run, version = _persist_ready_status(
        store, collaboration_run_id=collaboration_run_id, finalize=False
    )
    material = {"run_id": run["id"], "delivery_ids": sorted(record["id"] for record in deliveries)}
    evidence = {
        "id": _new_id(store, "rd-ready-evidence", material),
        "product_id": run["product_id"],
        "collaboration_run_id": run["id"],
        "product_version_id": version["id"],
        "delivery_ids": sorted(record["id"] for record in deliveries),
        "verified_only": True,
        "created_at": _now(),
        "updated_at": _now(),
    }
    _save_record(
        store,
        record=evidence,
        record_type=READINESS_RECORD_TYPE,
        collection="rd_ready_for_release_evidence",
    )
    return {
        "evidence": deepcopy(evidence),
        "run": deepcopy(run),
        "product_version": deepcopy(version),
    }


def finalize_ready_for_release_target(store: Any, *, collaboration_run_id: str) -> dict[str, Any]:
    """Finalize only the frozen ready-for-release target; deployment stays non-terminal."""
    run = _run(store, collaboration_run_id)
    _version(store, str(run["product_version_id"]))
    evidence = [
        record
        for record in _records(
            store, record_type=READINESS_RECORD_TYPE, collection="rd_ready_for_release_evidence"
        )
        if record.get("collaboration_run_id") == collaboration_run_id
    ]
    if not evidence:
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_INCOMPLETE",
            "Ready-for-release evidence must be recorded before finalization",
        )
    run, version = _persist_ready_status(
        store, collaboration_run_id=collaboration_run_id, finalize=True
    )
    return {"run": deepcopy(run), "product_version": deepcopy(version)}
