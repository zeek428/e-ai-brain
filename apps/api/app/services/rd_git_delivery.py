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
_INTEGRATION_WORK_ITEM_TYPES = {
    "automated_testing",
    "integration",
    "integration_test",
    "version_integration",
}


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
) -> dict[str, Any]:
    repository = _repository(store)
    save_record = getattr(repository, "save_rd_delivery_evidence_record", None)
    if not callable(save_record):
        save_record = getattr(repository, "save_trusted_delivery_record", None)
    persisted = dict(record)
    if callable(save_record):
        result = save_record(record=record, record_type=record_type)
        if isinstance(result, dict):
            persisted = dict(result)
    else:
        payload = {
            key: value
            for key, value in persisted.items()
            if key not in {"created_at", "evidence_hash"}
        }
        persisted.setdefault("evidence_hash", _canonical_hash(payload))
    records = read_memory_dict(store, collection)
    existing = records.get(record["id"])
    if existing is not None and existing != persisted:
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_MISMATCH",
            "Delivery evidence is immutable and cannot be overwritten",
        )
    records[record["id"]] = deepcopy(persisted)
    return persisted


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


def _save_delivery_bundle(
    store: Any,
    *,
    delivery: dict[str, Any],
    outbox: dict[str, Any],
) -> dict[str, Any]:
    """Store the immutable local fact and its push command in one transaction."""
    repository = _repository(store)
    save_bundle = getattr(repository, "save_rd_git_delivery_bundle", None)
    persisted = dict(delivery)
    if callable(save_bundle):
        result = save_bundle(delivery=delivery, outbox_event=outbox)
        if isinstance(result, dict):
            persisted = dict(result)
    else:
        persisted = _save_record(
            store,
            record=delivery,
            record_type=DELIVERY_RECORD_TYPE,
            collection="rd_git_deliveries",
        )
        _save_outbox(store, outbox)
        return persisted
    records = read_memory_dict(store, "rd_git_deliveries")
    existing = records.get(persisted["id"])
    if existing is not None and existing != persisted:
        raise api_error(409, "RD_DELIVERY_EVIDENCE_MISMATCH", "Delivery evidence is immutable")
    records[persisted["id"]] = deepcopy(persisted)
    read_memory_dict(store, "execution_outbox_events")[outbox["id"]] = deepcopy(outbox)
    return persisted


def _save_reconciliation_bundle(
    store: Any,
    *,
    reconciliation: dict[str, Any],
    outbox: dict[str, Any] | None,
) -> dict[str, Any]:
    repository = _repository(store)
    save_bundle = getattr(repository, "save_rd_git_reconciliation_bundle", None)
    persisted = dict(reconciliation)
    if callable(save_bundle):
        result = save_bundle(reconciliation=reconciliation, outbox_event=outbox)
        if isinstance(result, dict):
            persisted = dict(result)
    else:
        persisted = _save_record(
            store,
            record=reconciliation,
            record_type=RECONCILIATION_RECORD_TYPE,
            collection="rd_git_delivery_reconciliations",
        )
        if outbox is not None:
            _save_outbox(store, outbox)
        return persisted
    records = read_memory_dict(store, "rd_git_delivery_reconciliations")
    existing = records.get(persisted["id"])
    if existing is not None and existing != persisted:
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_MISMATCH",
            "Reconciliation evidence is immutable",
        )
    records[persisted["id"]] = deepcopy(persisted)
    if outbox is not None:
        read_memory_dict(store, "execution_outbox_events")[outbox["id"]] = deepcopy(outbox)
    return persisted


def _outbox_event(store: Any, event_id: str) -> dict[str, Any] | None:
    repository = _repository(store)
    list_events = getattr(repository, "list_execution_outbox_events", None)
    if callable(list_events):
        for event in list_events(aggregate_id=None, aggregate_type=None, status=None):
            if event.get("id") == event_id:
                return dict(event)
    event = read_memory_dict(store, "execution_outbox_events").get(event_id)
    return dict(event) if event is not None else None


def _persisted_verified_inbox_callback(
    store: Any,
    *,
    inbox_event_id: str,
    inbox_event_payload_hash: str,
) -> dict[str, Any]:
    """Load the provider callback from its durable Inbox fact, never caller input.

    PostgreSQL is the source of truth whenever a repository-backed runtime is
    present.  MemoryStore is deliberately supported only for isolated unit
    tests, where its Inbox dictionary represents the persisted fact.
    """
    repository = _repository(store)
    event: dict[str, Any] | None = None
    if repository is not None:
        get_event = getattr(repository, "get_external_event_inbox", None)
        if not callable(get_event):
            raise api_error(
                403,
                "RD_GIT_DELIVERY_CALLBACK_UNTRUSTED",
                "The delivery callback cannot be loaded from the durable Inbox",
            )
        loaded = get_event(inbox_event_id)
        event = dict(loaded) if isinstance(loaded, dict) else None
    else:
        candidate = read_memory_dict(store, "external_event_inbox").get(inbox_event_id)
        event = dict(candidate) if isinstance(candidate, dict) else None
    if (
        event is None
        or event.get("signature_status") != "verified"
        or str(event.get("payload_hash") or "") != inbox_event_payload_hash
    ):
        raise api_error(
            403,
            "RD_GIT_DELIVERY_CALLBACK_UNTRUSTED",
            "Remote Git reconciliation requires a persisted verified callback",
        )
    return event


def _callback_ref(payload: dict[str, Any]) -> str:
    context = payload.get("_context") if isinstance(payload.get("_context"), dict) else {}
    return (
        str(
            context.get("repository_ref")
            or payload.get("ref")
            or (payload.get("push") or {}).get("ref")
            or ""
        )
        .strip()
        .removeprefix("refs/heads/")
    )


def _callback_delivery_control(event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    control = payload.get("ai_brain") if isinstance(payload.get("ai_brain"), dict) else {}
    return dict(payload), dict(control)


def require_rd_delivery_finalization_for_version_transition(
    store: Any,
    *,
    from_status: str,
    target_status: str,
    version_id: str,
) -> None:
    """Fence the legacy version endpoint from advancing a v2 delivery run.

    The collaboration delivery service is the only owner of the
    testing -> ready_for_release transition when a version has a v2 run.  Its
    evidence bundle and finalization command execute against locked records;
    a generic product-version request cannot supply equivalent proof.
    """
    if from_status != "testing" or target_status != "ready_for_release":
        return
    repository = _repository(store)
    list_runs = getattr(repository, "list_rd_collaboration_runs", None)
    if callable(list_runs):
        runs = [dict(run) for run in list_runs(product_version_id=version_id)]
    else:
        runs = [
            dict(run)
            for run in read_memory_dict(store, "rd_collaboration_runs").values()
            if str(run.get("product_version_id") or "") == version_id
        ]
    if not runs:
        return
    raise api_error(
        409,
        "RD_DELIVERY_FINALIZATION_REQUIRED",
        "R&D collaboration versions enter ready-for-release only through trusted delivery "
        "finalization",
    )


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
            "source_runner_id": delivery.get("source_runner_id"),
            "source_runner_task_id": delivery.get("source_runner_task_id"),
            "target_branch": delivery["target_branch"],
            "version_branch": delivery["version_branch"],
            "working_branch": delivery["working_branch"],
            "workspace_root": (delivery.get("workspace_isolation") or {}).get("worktree_path"),
        },
        "status": "pending",
        "attempt_count": 0,
        # Let PostgreSQL assign availability within the same transaction as the
        # immutable delivery fact.  An app/DB clock skew must not make a new
        # push intent invisible to the first worker claim; MemoryStore treats
        # None as immediately available as well.
        "available_at": None,
        "lease_owner": None,
        "lease_until": None,
        "last_error": None,
        "created_at": now,
        "updated_at": now,
        "processed_at": None,
    }
    return event


def _reconciliation_for_delivery(
    store: Any,
    *,
    delivery_id: str,
) -> dict[str, Any] | None:
    records = _records(
        store,
        record_type=RECONCILIATION_RECORD_TYPE,
        collection="rd_git_delivery_reconciliations",
    )
    matching = [
        record
        for record in records
        if str(record.get("delivery_id") or "") == delivery_id
        and record.get("status") == "reconciled"
    ]
    if not matching:
        return None
    return max(matching, key=lambda record: str(record.get("created_at") or ""))


def _materialize_delivery(store: Any, delivery: dict[str, Any]) -> dict[str, Any]:
    """Derive reconciliation fields without mutating the local delivery fact."""
    reconciliation = _reconciliation_for_delivery(store, delivery_id=str(delivery["id"]))
    result = dict(delivery)
    result.update(
        {
            "reconciliation_id": reconciliation.get("id") if reconciliation else None,
            "reconciliation_evidence_hash": (
                reconciliation.get("evidence_hash") if reconciliation else None
            ),
            "reconciliation_status": (
                reconciliation.get("status") if reconciliation else "pending"
            ),
            "remote_commit_sha": (
                reconciliation.get("remote_commit_sha") if reconciliation else None
            ),
            "verified_at": reconciliation.get("created_at") if reconciliation else None,
        }
    )
    if reconciliation is not None:
        result["merge_request_id"] = reconciliation.get(
            "merge_request_id", result.get("merge_request_id")
        )
        result["pull_request_id"] = reconciliation.get(
            "pull_request_id", result.get("pull_request_id")
        )
    return result


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
    source_runner_id: str | None = None,
    source_runner_task_id: str | None = None,
    push_approval: dict[str, Any] | None = None,
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
        return {
            "delivery": _materialize_delivery(store, existing),
            "outbox": dict(outbox or {}),
            "idempotent_replay": True,
        }
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
        "merge_request_id": merge_request_id,
        "pull_request_id": pull_request_id,
        "test_evidence": deepcopy(test_evidence or {}),
        "source_runner_id": source_runner_id,
        "source_runner_task_id": source_runner_task_id,
        "push_approval": deepcopy(push_approval or {}),
        "created_at": now,
    }
    outbox = _delivery_outbox(store, delivery=delivery)
    delivery["outbox_event_id"] = outbox["id"]
    persisted_delivery = _save_delivery_bundle(store, delivery=delivery, outbox=outbox)
    return {
        "delivery": deepcopy(_materialize_delivery(store, persisted_delivery)),
        "outbox": deepcopy(outbox),
        "idempotent_replay": False,
    }


def record_version_git_delivery_from_runner(
    store: Any,
    *,
    ai_task: dict[str, Any],
    runner_task: dict[str, Any],
) -> dict[str, Any] | None:
    """Create push intent from frozen Runner/branch facts, never API input.

    The terminal Runner result can attest only to the local commit it produced.
    Repository, version branch, target branch and workspace root are loaded
    from the immutable execution policy and product-version branch config.
    Remote truth is intentionally absent here and can only arrive later via a
    verified provider Inbox callback.
    """
    result = runner_task.get("result_json")
    result = result if isinstance(result, dict) else {}
    reported = result.get("git_delivery") if isinstance(result.get("git_delivery"), dict) else {}
    if not reported:
        return None
    input_payload = (
        runner_task.get("input_payload")
        if isinstance(runner_task.get("input_payload"), dict)
        else {}
    )
    frozen = input_payload.get("rd_execution_policy_snapshot")
    frozen = frozen if isinstance(frozen, dict) else {}
    git_config = frozen.get("git_config") if isinstance(frozen.get("git_config"), dict) else {}
    run_id = str(ai_task.get("collaboration_run_id") or "").strip()
    work_item_id = str(ai_task.get("work_item_id") or "").strip()
    if (
        not run_id
        or not work_item_id
        or runner_task.get("ai_task_id") != ai_task.get("id")
        or runner_task.get("status") != "succeeded"
        or input_payload.get("rd_collaboration_run_id") != run_id
        or input_payload.get("rd_work_item_id") != work_item_id
    ):
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_MISMATCH",
            "Runner delivery is missing frozen collaboration provenance",
        )
    repository_id = str(git_config.get("repository_id") or "").strip()
    workspace_root = str(git_config.get("workspace_root") or "").strip()
    if (
        not repository_id
        or not workspace_root
        or runner_task.get("workspace_root") != workspace_root
    ):
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_MISMATCH",
            "Runner delivery is not bound to its frozen repository/workspace",
        )
    run = _run(store, run_id)
    branch_configs: list[dict[str, Any]] = []
    repository = _repository(store)
    list_configs = getattr(repository, "list_product_version_branch_configs", None)
    if callable(list_configs):
        branch_configs = [
            dict(item)
            for item in list_configs(str(run["product_version_id"]))
            if isinstance(item, dict)
        ]
    else:
        branch_configs = [
            dict(item)
            for item in read_memory_dict(store, "product_version_branch_configs").values()
            if item.get("version_id") == run["product_version_id"]
        ]
    branch_config = next(
        (item for item in branch_configs if str(item.get("repository_id") or "") == repository_id),
        None,
    )
    if branch_config is None:
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_MISMATCH",
            "Frozen delivery repository is not configured for the product version",
        )
    working_branch = f"rd/{run_id}/{work_item_id}"
    if str(reported.get("working_branch") or "") != working_branch:
        raise api_error(
            409,
            "RD_GIT_DELIVERY_ISOLATION_REQUIRED",
            "Runner delivery branch does not match the isolated work-item branch",
        )
    local_commit_sha = str(reported.get("local_commit_sha") or "").strip()
    if not local_commit_sha:
        raise api_error(422, "VALIDATION_ERROR", "Runner delivery is missing local_commit_sha")
    isolation = {
        "branch": working_branch,
        "status": "isolated",
        "worktree_path": workspace_root,
    }
    return record_version_git_delivery(
        store,
        collaboration_run_id=run_id,
        work_item_id=work_item_id,
        repository_id=repository_id,
        provider=str(branch_config.get("repository_provider") or git_config.get("provider") or ""),
        working_branch=working_branch,
        version_branch=str(branch_config.get("working_branch") or ""),
        target_branch=str(
            branch_config.get("base_branch") or branch_config.get("repository_default_branch") or ""
        ),
        local_commit_sha=local_commit_sha,
        workspace_isolation=isolation,
        test_evidence=(
            result.get("test_evidence") if isinstance(result.get("test_evidence"), dict) else None
        ),
        source_runner_id=str(runner_task.get("runner_id") or ""),
        source_runner_task_id=str(runner_task.get("id") or ""),
        push_approval=(
            git_config.get("push_approval")
            if isinstance(git_config.get("push_approval"), dict)
            else None
        ),
    )


def verify_version_git_delivery(
    store: Any,
    *,
    inbox_event_id: str,
    inbox_event_payload_hash: str,
) -> dict[str, Any]:
    """Append reconciliation using only a durable signature-verified Inbox fact."""
    callback = _persisted_verified_inbox_callback(
        store,
        inbox_event_id=inbox_event_id,
        inbox_event_payload_hash=inbox_event_payload_hash,
    )
    callback_payload, control = _callback_delivery_control(callback)
    delivery_id = str(control.get("rd_delivery_id") or "").strip()
    remote_commit_sha = str(
        control.get("remote_commit_sha")
        or callback_payload.get("after")
        or callback_payload.get("commit_sha")
        or ""
    ).strip()
    if not delivery_id or not remote_commit_sha:
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_MISMATCH",
            "Persisted Git callback is missing its delivery id or remote commit",
        )
    deliveries = _records(store, record_type=DELIVERY_RECORD_TYPE, collection="rd_git_deliveries")
    delivery = next((record for record in deliveries if record.get("id") == delivery_id), None)
    if delivery is None:
        raise api_error(404, "NOT_FOUND", "Git delivery record not found")
    context = (
        callback_payload.get("_context")
        if isinstance(callback_payload.get("_context"), dict)
        else {}
    )
    callback_ref = _callback_ref(callback_payload)
    if str(callback.get("provider") or "") != str(delivery.get("provider") or ""):
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_MISMATCH",
            "Verified callback provider does not match the frozen delivery repository",
        )
    if (
        str(context.get("product_id") or "") != str(delivery.get("product_id") or "")
        or str(context.get("repository_id") or "") != str(delivery.get("repository_id") or "")
        or str(context.get("repository_provider") or callback.get("provider") or "")
        != str(delivery.get("provider") or "")
        or callback_ref != str(delivery.get("working_branch") or "")
    ):
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_MISMATCH",
            "Verified callback is not bound to the frozen repository and work-item branch",
        )
    if remote_commit_sha != delivery.get("local_commit_sha"):
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
        "product_version_id": delivery["product_version_id"],
        "repository_id": delivery["repository_id"],
        "local_commit_sha": delivery["local_commit_sha"],
        "remote_commit_sha": remote_commit_sha,
        "status": "reconciled",
        "created_at": now,
        "predecessor_evidence_ids": [delivery_id],
        "delivery_evidence_hash": delivery.get("evidence_hash"),
        "merge_request_id": (control.get("merge_request_id") or delivery.get("merge_request_id")),
        "pull_request_id": (control.get("pull_request_id") or delivery.get("pull_request_id")),
        "provider_callback_event_id": callback["id"],
        "provider_callback_payload_hash": callback.get("payload_hash"),
        "provider_callback_signature_status": callback.get("signature_status"),
        "provider_callback_product_id": context.get("product_id"),
        "provider_callback_repository_id": context.get("repository_id"),
        "provider_callback_ref": callback_ref,
    }
    outbox_id = delivery.get("outbox_event_id")
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
    else:
        completed_outbox = None
    persisted_reconciliation = _save_reconciliation_bundle(
        store,
        reconciliation=reconciliation,
        outbox=completed_outbox,
    )
    verified = _materialize_delivery(store, delivery)
    readiness: dict[str, Any] | None = None
    readiness_pending = False
    try:
        readiness = record_ready_for_release_evidence(
            store,
            collaboration_run_id=str(delivery["collaboration_run_id"]),
            finalize_ready_target=True,
        )
    except Exception as exc:  # noqa: BLE001 - incomplete chains await later callbacks.
        detail = getattr(exc, "detail", None)
        code = detail.get("code") if isinstance(detail, dict) else None
        if code != "RD_DELIVERY_EVIDENCE_INCOMPLETE":
            raise
        # The local/remote Git fact is immutable and may arrive before the
        # approved integration item has advanced the durable run to verifying.
        # Keep that reconciliation, but make the Inbox projector defer rather
        # than falsely acknowledge the callback as fully completed.
        readiness_pending = True
    return {
        "delivery": deepcopy(verified),
        "reconciliation": deepcopy(persisted_reconciliation),
        "readiness": deepcopy(readiness) if readiness is not None else None,
        "readiness_pending": readiness_pending,
    }


def reconcile_version_git_delivery_from_provider_callback(
    store: Any,
    *,
    inbox_event: dict[str, Any],
) -> dict[str, Any] | None:
    """Project only an authenticated Inbox callback into delivery evidence.

    Git providers may attach their own event schema, so the configured callback
    requires a namespaced AI Brain block.  No endpoint accepts a delivery id or
    remote SHA directly; both originate from the signed, immutable Inbox row.
    """
    payload = inbox_event.get("payload") if isinstance(inbox_event.get("payload"), dict) else {}
    control = payload.get("ai_brain") if isinstance(payload.get("ai_brain"), dict) else {}
    if not str(control.get("rd_delivery_id") or "").strip():
        return None
    reconciled = verify_version_git_delivery(
        store,
        inbox_event_id=str(inbox_event.get("id") or ""),
        inbox_event_payload_hash=str(inbox_event.get("payload_hash") or ""),
    )
    if reconciled.get("readiness_pending"):
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_INCOMPLETE",
            "Remote Git callback is reconciled but the collaboration delivery phase is incomplete",
        )
    return reconciled


def dispatch_rd_git_delivery_push_from_outbox(
    store: Any,
    *,
    event: dict[str, Any],
) -> dict[str, Any]:
    """Queue the physical Git push on the Runner that owns the frozen worktree.

    The durable outbox payload is validated against the immutable local fact
    before a Runner task is created.  It never carries an arbitrary repository,
    branch, worktree or commit supplied by a user request.
    """
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    delivery_id = str(payload.get("delivery_id") or "")
    deliveries = _records(store, record_type=DELIVERY_RECORD_TYPE, collection="rd_git_deliveries")
    delivery = next((item for item in deliveries if item.get("id") == delivery_id), None)
    if delivery is None:
        raise api_error(404, "NOT_FOUND", "Git delivery record not found")
    for field in (
        "local_commit_sha",
        "product_id",
        "provider",
        "repository_id",
        "target_branch",
        "version_branch",
        "working_branch",
        "source_runner_id",
        "source_runner_task_id",
    ):
        if payload.get(field) != delivery.get(field):
            raise api_error(
                409,
                "RD_DELIVERY_EVIDENCE_MISMATCH",
                "Push outbox payload does not match its immutable delivery fact",
            )
    workspace_root = str((delivery.get("workspace_isolation") or {}).get("worktree_path") or "")
    if not workspace_root or payload.get("workspace_root") != workspace_root:
        raise api_error(
            409,
            "RD_GIT_DELIVERY_ISOLATION_REQUIRED",
            "Push outbox is not bound to the frozen Runner worktree",
        )
    source_runner_task_id = str(delivery.get("source_runner_task_id") or "")
    source_runner_id = str(delivery.get("source_runner_id") or "")
    repository = _repository(store)
    list_runner_tasks = getattr(repository, "list_ai_executor_tasks", None)
    runner_tasks = (
        [dict(item) for item in list_runner_tasks()]
        if callable(list_runner_tasks)
        else [dict(item) for item in read_memory_dict(store, "ai_executor_tasks").values()]
    )
    source = next((item for item in runner_tasks if item.get("id") == source_runner_task_id), None)
    if (
        source is None
        or source.get("status") != "succeeded"
        or source.get("runner_id") != source_runner_id
        or source.get("workspace_root") != workspace_root
    ):
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_INCOMPLETE",
            "Frozen source Runner task is unavailable for the Git push",
        )
    idempotency_key = f"rd-git-push:{delivery_id}"
    existing = next(
        (
            item
            for item in runner_tasks
            if (item.get("request_config") or {}).get("outbox_idempotency_key") == idempotency_key
        ),
        None,
    )
    if existing is not None:
        return {"delivery": _materialize_delivery(store, delivery), "runner_task": existing}
    from app.services.ai_executor_task_creation import create_ai_executor_task

    push_task = create_ai_executor_task(
        store,
        action_id=None,
        ai_task_id=source.get("ai_task_id"),
        connection_id=None,
        created_by=str(source.get("created_by") or "system"),
        executor_type=str(source.get("executor_type") or ""),
        input_payload={
            "rd_git_delivery_id": delivery_id,
            "local_commit_sha": delivery["local_commit_sha"],
            "repository_id": delivery["repository_id"],
            "target_branch": delivery["target_branch"],
            "version_branch": delivery["version_branch"],
            "working_branch": delivery["working_branch"],
            "workspace_root": workspace_root,
        },
        instruction=(
            "Run git push for the already-created frozen local commit to the configured "
            "remote repository. Do not amend, reset, rebase, merge, deploy, or report a "
            "remote SHA as trusted evidence. "
            f"Commit: {delivery['local_commit_sha']}; branch: {delivery['working_branch']}."
        ),
        plugin_invocation_log_id=None,
        request_config={
            "ai_executor_approval": delivery.get("push_approval") or {},
            "outbox_idempotency_key": idempotency_key,
            "rd_git_delivery_id": delivery_id,
            "source_runner_task_id": source_runner_task_id,
        },
        runner_id=source_runner_id,
        scheduled_job_id=None,
        scheduled_job_run_id=None,
        task_kind="git_push",
        timeout_seconds=int(source.get("timeout_seconds") or 1800),
        workspace_root=workspace_root,
    )
    return {"delivery": _materialize_delivery(store, delivery), "runner_task": push_task}


def _evidence_is_fresh(run: dict[str, Any], delivery: dict[str, Any]) -> bool:
    if delivery.get("evidence_stale"):
        return False
    raw_verified_at = delivery.get("verified_at")
    if not raw_verified_at:
        return False
    if isinstance(raw_verified_at, datetime):
        verified_at = raw_verified_at
    else:
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
        _materialize_delivery(store, record)
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
            or not delivery.get("evidence_hash")
            or not delivery.get("reconciliation_evidence_hash")
            or not _evidence_is_fresh(run, delivery)
        ):
            raise api_error(
                409,
                "RD_DELIVERY_EVIDENCE_INCOMPLETE",
                "Remote delivery evidence is missing, stale or mismatched",
            )
        reconciliation = _reconciliation_for_delivery(store, delivery_id=str(delivery["id"]))
        if (
            reconciliation is None
            or reconciliation.get("delivery_evidence_hash") != delivery.get("evidence_hash")
            or str(delivery["id"])
            not in {str(item) for item in reconciliation.get("predecessor_evidence_ids") or []}
        ):
            raise api_error(
                409,
                "RD_DELIVERY_EVIDENCE_MISMATCH",
                "Reconciliation is not bound to the immutable local delivery fact",
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


def _delivery_evidence_chain(deliveries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "delivery_id": record["id"],
            "delivery_evidence_hash": record["evidence_hash"],
            "reconciliation_id": record["reconciliation_id"],
            "reconciliation_evidence_hash": record["reconciliation_evidence_hash"],
            "remote_commit_sha": record["remote_commit_sha"],
            "test_evidence": record.get("test_evidence") or {},
        }
        for record in sorted(deliveries, key=lambda record: str(record["id"]))
    ]


def _assert_frozen_readiness_chain(
    store: Any,
    *,
    run: dict[str, Any],
) -> dict[str, Any]:
    records = [
        record
        for record in _records(
            store,
            record_type=READINESS_RECORD_TYPE,
            collection="rd_ready_for_release_evidence",
        )
        if record.get("collaboration_run_id") == run["id"]
    ]
    if not records:
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_INCOMPLETE",
            "Ready-for-release evidence must be recorded before finalization",
        )
    evidence = max(records, key=lambda record: str(record.get("created_at") or ""))
    deliveries = _assert_trusted_delivery_evidence(store, run=run)
    chain = _delivery_evidence_chain(deliveries)
    material = {
        "run_id": run["id"],
        "delivery_ids": sorted(str(record["id"]) for record in deliveries),
        "evidence_chain": chain,
    }
    if (
        evidence.get("evidence_chain_hash") != _canonical_hash(material)
        or evidence.get("evidence_chain") != chain
        or set(str(item) for item in evidence.get("delivery_ids") or [])
        != set(material["delivery_ids"])
    ):
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_MISMATCH",
            "Finalization evidence no longer matches the frozen delivery chain",
        )
    if run.get("delivery_evidence_id") is not None and (
        run.get("delivery_evidence_id") != evidence["id"]
        or run.get("delivery_evidence_hash") != evidence.get("evidence_hash")
    ):
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_MISMATCH",
            "Collaboration run is not linked to the frozen readiness evidence",
        )
    return evidence


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
    if run.get("status") not in {"verifying", "ready_for_release"}:
        raise api_error(
            409,
            "RD_DELIVERY_EVIDENCE_INCOMPLETE",
            "Collaboration run must complete the verified delivery phase",
        )
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


def record_ready_for_release_evidence(
    store: Any,
    *,
    collaboration_run_id: str,
    finalize_ready_target: bool = False,
) -> dict[str, Any]:
    """Verify immutable remote/test evidence and enter, but do not finish, ready state."""
    run = _run(store, collaboration_run_id)
    version = _version(store, str(run["product_version_id"]))
    deliveries = _assert_trusted_delivery_evidence(store, run=run)
    delivery_ids = sorted(str(record["id"]) for record in deliveries)
    evidence_chain = _delivery_evidence_chain(deliveries)
    material = {
        "run_id": run["id"],
        "delivery_ids": delivery_ids,
        "evidence_chain": evidence_chain,
    }
    evidence = {
        "id": _new_id(store, "rd-ready-evidence", material),
        "product_id": run["product_id"],
        "collaboration_run_id": run["id"],
        "product_version_id": version["id"],
        # A readiness fact references the first delivery directly and the full
        # set through predecessor_evidence_ids / payload.  The latter is the
        # frozen chain used again at finalization.
        "delivery_id": delivery_ids[0],
        "predecessor_evidence_ids": [
            *delivery_ids,
            *sorted(str(record["reconciliation_id"]) for record in deliveries),
        ],
        "delivery_ids": delivery_ids,
        "evidence_chain": evidence_chain,
        "evidence_chain_hash": _canonical_hash(material),
        "verified_only": True,
        "created_at": _now(),
    }
    existing_evidence = next(
        (
            record
            for record in _records(
                store,
                record_type=READINESS_RECORD_TYPE,
                collection="rd_ready_for_release_evidence",
            )
            if record.get("id") == evidence["id"]
        ),
        None,
    )
    if existing_evidence is not None:
        if finalize_ready_target and run.get("status") != "completed":
            run, version = _persist_ready_status(
                store,
                collaboration_run_id=collaboration_run_id,
                finalize=True,
            )
        return {
            "evidence": deepcopy(existing_evidence),
            "run": deepcopy(run),
            "product_version": deepcopy(version),
        }
    # In PostgreSQL mode the collaboration repository owns this state
    # transition and evidence insert as one database transaction.
    repository = _repository(store)
    save_bundle = getattr(repository, "record_rd_ready_for_release_evidence_bundle", None)
    if callable(save_bundle):
        persisted = save_bundle(
            collaboration_run_id=collaboration_run_id,
            evidence=evidence,
            finalize_ready_target=finalize_ready_target,
        )
        evidence = dict(persisted["evidence"])
        run = dict(persisted["run"])
        version = dict(persisted["product_version"])
        read_memory_dict(store, "rd_ready_for_release_evidence")[evidence["id"]] = deepcopy(
            evidence
        )
    else:
        run, version = _persist_ready_status(
            store, collaboration_run_id=collaboration_run_id, finalize=False
        )
        evidence = _save_record(
            store,
            record=evidence,
            record_type=READINESS_RECORD_TYPE,
            collection="rd_ready_for_release_evidence",
        )
        if finalize_ready_target:
            run, version = _persist_ready_status(
                store,
                collaboration_run_id=collaboration_run_id,
                finalize=True,
            )
    return {
        "evidence": deepcopy(evidence),
        "run": deepcopy(run),
        "product_version": deepcopy(version),
    }


def finalize_ready_for_release_target(store: Any, *, collaboration_run_id: str) -> dict[str, Any]:
    """Finalize only the frozen ready-for-release target; deployment stays non-terminal."""
    run = _run(store, collaboration_run_id)
    version = _version(store, str(run["product_version_id"]))
    if run.get("status") == "completed":
        return {"run": deepcopy(run), "product_version": deepcopy(version)}
    _assert_frozen_readiness_chain(store, run=run)
    run, version = _persist_ready_status(
        store, collaboration_run_id=collaboration_run_id, finalize=True
    )
    return {"run": deepcopy(run), "product_version": deepcopy(version)}
