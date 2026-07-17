from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.core.store import DEFAULT_BRAIN_APP_ID

OPEN_REQUIREMENT_STATUSES = {
    "draft",
    "submitted",
    "approved",
    "planned",
    "designing",
    "ready_for_dev",
    "developing",
    "code_reviewing",
    "testing",
    "ready_for_release",
    "deploying",
}

SOURCE_TO_REQUIREMENT_SOURCE = {
    "assistant_action_draft": "product_planning",
    "bug": "other",
    "code_inspection_finding": "other",
}

V2_POLICY_SNAPSHOT_KINDS = {
    "base",
    "assessment_resolved",
    "version_resolved",
}


def adapter_idempotency_key(*, source_id: str, source_type: str) -> str:
    return f"{source_type}:{source_id}"


def _read_records(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    records = getattr(current_store, collection_name, None)
    return records if isinstance(records, dict) else {}


def _non_blank(value: Any, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return normalized


def _open_requirement_for_source(
    current_store: Any,
    *,
    source_id: str,
    source_type: str,
) -> dict[str, Any] | None:
    key = adapter_idempotency_key(source_id=source_id, source_type=source_type)
    for requirement in _read_records(current_store, "requirements").values():
        if requirement.get("source_adapter_key") != key:
            continue
        if str(requirement.get("status") or "submitted") in OPEN_REQUIREMENT_STATUSES:
            return requirement
    return None


def _requirement_record(current_store: Any, requirement_id: str) -> dict[str, Any] | None:
    requirement = _read_records(current_store, "requirements").get(requirement_id)
    if requirement is not None:
        return requirement
    repository = getattr(current_store, "repository", None)
    load_requirements = getattr(repository, "load_requirements", None)
    if not callable(load_requirements):
        return None
    payload = load_requirements()
    requirements = payload.get("requirements", {}) if isinstance(payload, dict) else {}
    candidate = requirements.get(requirement_id) if isinstance(requirements, dict) else None
    return candidate if isinstance(candidate, dict) else None


def _accepted_assessments(current_store: Any, requirement_id: str) -> list[dict[str, Any]]:
    assessments = [
        item
        for item in _read_records(current_store, "requirement_assessments").values()
        if item.get("requirement_id") == requirement_id
    ]
    if not assessments:
        repository = getattr(current_store, "repository", None)
        list_assessments = getattr(repository, "list_requirement_assessments", None)
        if callable(list_assessments):
            loaded = list_assessments(requirement_id)
            assessments = [item for item in loaded if isinstance(item, dict)]
    return [item for item in assessments if item.get("status") == "accepted"]


def _v2_snapshot(current_store: Any, snapshot_id: Any) -> dict[str, Any] | None:
    if not snapshot_id:
        return None
    snapshot = _read_records(current_store, "rd_task_executor_policy_snapshots").get(
        str(snapshot_id)
    )
    if snapshot is not None:
        return snapshot
    repository = getattr(current_store, "repository", None)
    get_snapshot = getattr(repository, "get_rd_policy_snapshot", None)
    if not callable(get_snapshot):
        return None
    loaded = get_snapshot(str(snapshot_id))
    return loaded if isinstance(loaded, dict) else None


def is_v2_collaboration_requirement(current_store: Any, requirement_id: str) -> bool:
    """Return true only for requirements owned by the v2 collaboration flow.

    Legacy requirements may have an accepted compatibility assessment record but
    no v2 snapshot kind.  Keeping those paths writable is required while the
    v2 assessment/collaboration contract is rolled out incrementally.
    """
    requirement = _requirement_record(current_store, requirement_id)
    if requirement is None:
        return False
    if requirement.get("source_adapter_key") or requirement.get("source_collaboration_run_id"):
        return True
    return any(
        (snapshot := _v2_snapshot(current_store, assessment.get("final_strategy_snapshot_id")))
        is not None
        and snapshot.get("snapshot_kind") in V2_POLICY_SNAPSHOT_KINDS
        for assessment in _accepted_assessments(current_store, requirement_id)
    )


def _source_title(source_type: str, source_id: str, evidence: dict[str, Any]) -> str:
    evidence_title = str(evidence.get("title") or "").strip()
    if evidence_title:
        return evidence_title
    if source_type == "bug":
        return f"Bug 修复：{source_id}"
    if source_type == "code_inspection_finding":
        return f"代码巡检整改：{source_id}"
    return f"研发需求：{source_id}"


def _source_content(source_type: str, source_id: str, evidence: dict[str, Any]) -> str:
    for key in ("content", "description", "recommendation", "summary"):
        value = str(evidence.get(key) or "").strip()
        if value:
            return value
    return f"由 {source_type}:{source_id} 创建的正式研发需求。"


def create_or_link_rd_requirement(
    current_store: Any,
    *,
    source_type: str,
    source_id: str,
    product_id: str,
    evidence: dict[str, Any],
    actor_id: str,
) -> dict[str, Any]:
    """Create one open formal requirement for a legacy R&D source.

    The source-object key is persisted on the requirement itself, so retries
    across Bug, inspection and assistant entry points reuse the same open
    requirement instead of creating another task or another requirement.
    """
    normalized_source_type = _non_blank(source_type, "source_type")
    normalized_source_id = _non_blank(source_id, "source_id")
    normalized_product_id = _non_blank(product_id, "product_id")
    if normalized_source_type not in SOURCE_TO_REQUIREMENT_SOURCE:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported R&D requirement adapter source")
    if not isinstance(evidence, dict):
        raise api_error(400, "VALIDATION_ERROR", "evidence must be an object")

    existing = _open_requirement_for_source(
        current_store,
        source_id=normalized_source_id,
        source_type=normalized_source_type,
    )
    key = adapter_idempotency_key(
        source_id=normalized_source_id,
        source_type=normalized_source_type,
    )
    if existing is not None:
        return {
            "created": False,
            "idempotency_key": key,
            "requirement": current_store.snapshot(existing),
            "requirement_id": existing["id"],
        }

    product = _read_records(current_store, "products").get(normalized_product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product.get("status") != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")

    now = datetime.now(UTC).isoformat()
    requirement_id = current_store.new_id("requirement")
    requirement = {
        "assignee": actor_id,
        "brain_app_id": DEFAULT_BRAIN_APP_ID,
        "content": _source_content(normalized_source_type, normalized_source_id, evidence),
        "created_at": now,
        "created_by": actor_id,
        "id": requirement_id,
        "module_code": evidence.get("module_code"),
        "priority": str(evidence.get("priority") or "P1"),
        "product_id": normalized_product_id,
        "source": SOURCE_TO_REQUIREMENT_SOURCE[normalized_source_type],
        "source_adapter_key": key,
        "source_evidence": current_store.snapshot(evidence),
        "source_object_id": normalized_source_id,
        "source_object_type": normalized_source_type,
        "source_collaboration_run_id": None,
        "status": "submitted",
        "supersedes_requirement_id": None,
        "task_ids": [],
        "title": _source_title(normalized_source_type, normalized_source_id, evidence),
        "updated_at": now,
        "version_id": None,
    }
    # Import lazily: the canonical requirement service also imports the
    # compatibility error helper from this module.
    from app.services.requirements import record_audit_event, save_requirement_record

    audit_event = record_audit_event(
        current_store,
        event_type="requirement.created_from_legacy_entry",
        actor_id=actor_id,
        subject_type="requirement",
        subject_id=requirement_id,
        payload={
            "idempotency_key": key,
            "source_object_id": normalized_source_id,
            "source_object_type": normalized_source_type,
        },
    )
    save_requirement_record(current_store, requirement, audit_event=audit_event)
    return {
        "created": True,
        "idempotency_key": key,
        "requirement": current_store.snapshot(requirement),
        "requirement_id": requirement_id,
    }


def rd_collaboration_required_details(
    *,
    entrypoint: str,
    task: dict[str, Any] | None = None,
    requirement_id: str | None = None,
) -> dict[str, Any]:
    task = task or {}
    resolved_requirement_id = requirement_id or task.get("requirement_id")
    collaboration_run_id = task.get("collaboration_run_id")
    work_item_id = task.get("work_item_id")
    next_action = "create_requirement_assessment"
    if resolved_requirement_id:
        next_action = "start_version_collaboration"
    if collaboration_run_id and work_item_id:
        next_action = "use_work_item_command"
    return {
        "details": {
            "assessment_url": (
                f"/api/requirements/{resolved_requirement_id}/assessments"
                if resolved_requirement_id
                else None
            ),
            "collaboration_run_id": collaboration_run_id,
            "entrypoint": entrypoint,
            "next_action": next_action,
            "requirement_id": resolved_requirement_id,
            "retryable": False,
            "version_id": task.get("version_id"),
            "work_item_id": work_item_id,
        }
    }


def require_v2_task_work_item_entrypoint(task: dict[str, Any], *, entrypoint: str) -> None:
    if task.get("collaboration_run_id") or task.get("work_item_id"):
        raise api_error(
            409,
            "RD_COLLABORATION_REQUIRED",
            "V2 collaboration tasks must be operated through their work item",
            rd_collaboration_required_details(entrypoint=entrypoint, task=task),
        )


def require_v2_requirement_entrypoint(
    *,
    current_store: Any,
    entrypoint: str,
    requirement_id: str,
) -> None:
    if not is_v2_collaboration_requirement(current_store, requirement_id):
        return
    raise api_error(
        409,
        "RD_COLLABORATION_REQUIRED",
        "Legacy R&D task entry points are retired; use requirement assessment and collaboration",
        rd_collaboration_required_details(
            entrypoint=entrypoint,
            requirement_id=requirement_id,
        ),
    )


def raise_legacy_rd_entrypoint_required(
    *,
    current_store: Any,
    entrypoint: str,
    requirement_id: str | None = None,
) -> None:
    if requirement_id is None:
        return
    require_v2_requirement_entrypoint(
        current_store=current_store,
        entrypoint=entrypoint,
        requirement_id=requirement_id,
    )
