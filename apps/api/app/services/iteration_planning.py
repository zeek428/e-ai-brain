from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_roles
from app.services.user_insights import (
    ensure_enum,
    ensure_non_blank,
    user_insight_query_repository,
    user_insight_write_store,
    uses_repository_context,
)

ITERATION_SUGGESTION_STATUSES = {
    "accepted",
    "converted_to_requirement",
    "edited_accepted",
    "rejected",
    "suggested",
}
ITERATION_DECISIONS = {"accepted", "edited_accepted", "rejected"}


def require_iteration_planning_role(user: dict[str, Any]) -> None:
    require_roles(user, {"product_owner", "rd_owner"})


def validate_iteration_enums(
    *,
    decision: str | None = None,
    status: str | None = None,
) -> None:
    ensure_enum(decision, ITERATION_DECISIONS, "decision")
    ensure_enum(status, ITERATION_SUGGESTION_STATUSES, "status")


def normalized_module_codes(module_codes: list[str]) -> list[str]:
    normalized = []
    for module_code in module_codes:
        value = module_code.strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def validate_iteration_context(
    current_store: Any,
    *,
    product_id: str,
    version_id: str | None = None,
    module_codes: list[str] | None = None,
) -> None:
    product = current_store.products.get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    if version_id is not None:
        version = current_store.product_versions.get(version_id)
        if version is None or version["product_id"] != product_id:
            raise api_error(404, "NOT_FOUND", "Product version not found")
        if version["status"] == "archived":
            raise api_error(400, "PRODUCT_VERSION_ARCHIVED", "Archived version cannot be used")
    for module_code in module_codes or []:
        if not any(
            module["product_id"] == product_id and module["code"] == module_code
            for module in current_store.product_modules.values()
        ):
            raise api_error(404, "NOT_FOUND", "Product module not found")


def record_audit_event(
    current_store: Any,
    *,
    event_type: str,
    actor_id: str,
    subject_type: str,
    subject_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    audit_events = (
        getattr(current_store, "audit_events", None)
        if uses_repository_context(current_store)
        else _memory_list(current_store, "audit_events")
    )
    sequence = len(audit_events) + 1 if isinstance(audit_events, list) else 1
    event = {
        "id": current_store.new_id("audit"),
        "event_type": event_type,
        "actor_id": actor_id,
        "ai_task_id": None,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": payload or {},
        "sequence": sequence,
        "created_at": datetime.now(UTC).isoformat(),
    }
    if not uses_repository_context(current_store):
        audit_events.append(event)
    return event


def _memory_collection(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _memory_list(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, list):
        collection = []
        setattr(current_store, collection_name, collection)
    return collection


def _append_memory_audit_event(current_store: Any, audit_event: dict[str, Any]) -> None:
    audit_events = _memory_list(current_store, "audit_events")
    if not any(event.get("id") == audit_event.get("id") for event in audit_events):
        audit_events.append(audit_event)


def persist_iteration_suggestion_record(
    current_store: Any,
    *,
    audit_event: dict[str, Any],
    suggestion: dict[str, Any],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_iteration_suggestion_record", None)
    if callable(save_record):
        save_record(suggestion, audit_event=audit_event)
        return
    _memory_collection(current_store, "iteration_plan_suggestions")[str(suggestion["id"])] = (
        suggestion
    )
    _append_memory_audit_event(current_store, audit_event)


def persist_iteration_decision_records(
    current_store: Any,
    *,
    audit_events: list[dict[str, Any]],
    decision: dict[str, Any],
    requirement: dict[str, Any] | None,
    suggestion: dict[str, Any],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_iteration_decision_records", None)
    if callable(save_records):
        save_records(
            suggestion=suggestion,
            decision=decision,
            audit_events=audit_events,
            requirement=requirement,
        )
        return
    if requirement is not None:
        _memory_collection(current_store, "requirements")[str(requirement["id"])] = requirement
    _memory_collection(current_store, "iteration_plan_suggestions")[str(suggestion["id"])] = (
        suggestion
    )
    _memory_collection(current_store, "iteration_plan_decisions")[str(decision["id"])] = decision
    for audit_event in audit_events:
        _append_memory_audit_event(current_store, audit_event)


def iteration_evidence_matches_modules(item: dict[str, Any], module_codes: list[str]) -> bool:
    return not module_codes or item.get("module_code") in module_codes


def collect_iteration_evidence(
    current_store: Any,
    *,
    product_id: str,
    module_codes: list[str],
    include_evidence: bool,
) -> list[dict[str, Any]]:
    if not include_evidence:
        return []
    feedback_evidence = [
        {
            "subject_id": feedback["id"],
            "subject_type": "user_feedback",
            "summary": feedback["content"],
        }
        for feedback in sorted(
            current_store.user_feedback.values(),
            key=lambda item: (item.get("created_at") or "", item["id"]),
        )
        if feedback["product_id"] == product_id
        and feedback.get("status") not in {"archived", "resolved"}
        and iteration_evidence_matches_modules(feedback, module_codes)
    ]
    bug_evidence = [
        {
            "subject_id": bug["id"],
            "subject_type": "bug",
            "summary": bug["title"],
        }
        for bug in sorted(
            current_store.bugs.values(),
            key=lambda item: (item.get("created_at") or "", item["id"]),
        )
        if bug["product_id"] == product_id
        and bug.get("status") not in {"closed", "verified"}
        and iteration_evidence_matches_modules(bug, module_codes)
    ]
    return (feedback_evidence + bug_evidence)[:12]


def build_iteration_suggestion(
    current_store: Any,
    *,
    evidence: list[dict[str, Any]],
    module_codes: list[str],
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    product_name = current_store.products[payload.product_id]["name"]
    module_scope = "、".join(module_codes) if module_codes else product_name
    evidence_types = {item["subject_type"] for item in evidence}
    if len(evidence) >= 4:
        confidence_level = "high"
        priority_score = 88
    elif len(evidence) >= 2:
        confidence_level = "medium"
        priority_score = 76
    else:
        confidence_level = "low"
        priority_score = 52
    risk_signals = []
    if "user_feedback" in evidence_types:
        risk_signals.append("user_feedback_signal")
    if "bug" in evidence_types:
        risk_signals.append("bug_quality_signal")
    return {
        "business_value": f"提升 {module_scope} 的用户体验和交付质量。",
        "confidence_level": confidence_level,
        "created_at": now,
        "created_by": user["id"],
        "dependencies": ["产品负责人确认范围", "研发负责人评估投入"],
        "estimated_effort": "medium",
        "evidence": evidence,
        "evidence_insufficient": confidence_level == "low",
        "id": current_store.new_id("suggestion"),
        "module_codes": module_codes,
        "planning_cycle": ensure_non_blank(payload.planning_cycle, "planning_cycle"),
        "priority": "P1",
        "priority_score": priority_score,
        "product_id": payload.product_id,
        "recommendation_reason": (
            f"{module_scope} 已出现 {len(evidence)} 条真实反馈或缺陷证据，"
            "建议进入下一阶段迭代评估。"
        ),
        "risk_signals": risk_signals,
        "status": "suggested",
        "title": f"优化{module_scope}反馈与缺陷集中问题",
        "updated_at": now,
        "version_id": payload.version_id,
    }


def create_iteration_requirement(
    current_store: Any,
    *,
    payload: Any,
    suggestion: dict[str, Any],
    user: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    version_id = suggestion.get("version_id")
    if not version_id:
        raise api_error(
            400,
            "ITERATION_PLAN_VERSION_REQUIRED",
            "version_id is required to convert suggestion to requirement",
        )
    title = ensure_non_blank(payload.edited_title or suggestion["title"], "edited_title")
    scope = payload.edited_scope or suggestion["recommendation_reason"]
    now = datetime.now(UTC).isoformat()
    requirement_id = current_store.new_id("requirement")
    requirement = {
        "content": "\n".join(
            [
                scope,
                "",
                f"业务价值：{suggestion['business_value']}",
                f"推荐理由：{suggestion['recommendation_reason']}",
            ]
        ),
        "created_at": now,
        "created_by": user["id"],
        "id": requirement_id,
        "module_code": suggestion["module_codes"][0] if suggestion["module_codes"] else None,
        "priority": suggestion["priority"],
        "product_id": suggestion["product_id"],
        "source": "product_planning",
        "status": "submitted",
        "task_ids": [],
        "title": title,
        "version_id": version_id,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="requirement.created",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
        payload={"source": "iteration_plan_suggestion", "suggestion_id": suggestion["id"]},
    )
    return requirement, audit_event


def list_iteration_suggestions_response(
    *,
    current_store: Any,
    planning_cycle: str | None,
    product_id: str | None,
    status: str | None,
) -> dict[str, Any]:
    validate_iteration_enums(status=status)
    repository = user_insight_query_repository(current_store)
    if repository is not None:
        items = repository.list_iteration_plan_suggestions(
            product_id=product_id,
            planning_cycle=planning_cycle,
            status=status,
        )
        return {"items": items, "total": len(items)}
    items = []
    for suggestion in current_store.iteration_plan_suggestions.values():
        if product_id is not None and suggestion.get("product_id") != product_id:
            continue
        if planning_cycle is not None and suggestion.get("planning_cycle") != planning_cycle:
            continue
        if status is not None and suggestion.get("status") != status:
            continue
        items.append(suggestion)
    items.sort(
        key=lambda item: (
            item.get("priority_score", 0),
            item.get("updated_at") or item.get("created_at") or "",
        ),
        reverse=True,
    )
    return {"items": items, "total": len(items)}


def create_iteration_suggestions_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_iteration_planning_role(user)
    current_store = user_insight_write_store(current_store)
    module_codes = normalized_module_codes(payload.module_codes)
    validate_iteration_context(
        current_store,
        product_id=payload.product_id,
        version_id=payload.version_id,
        module_codes=module_codes,
    )
    evidence = collect_iteration_evidence(
        current_store,
        product_id=payload.product_id,
        module_codes=module_codes,
        include_evidence=payload.include_evidence,
    )
    if not evidence:
        return {"items": [], "total": 0}
    suggestion = build_iteration_suggestion(
        current_store,
        evidence=evidence,
        module_codes=module_codes,
        payload=payload,
        user=user,
    )
    audit_event = record_audit_event(
        current_store,
        event_type="iteration_suggestion.generated",
        actor_id=user["id"],
        subject_type="iteration_plan_suggestion",
        subject_id=suggestion["id"],
        payload={
            "evidence_count": len(evidence),
            "planning_cycle": suggestion["planning_cycle"],
            "product_id": suggestion["product_id"],
            "status": suggestion["status"],
        },
    )
    persist_iteration_suggestion_record(
        current_store,
        suggestion=suggestion,
        audit_event=audit_event,
    )
    return {"items": [suggestion], "total": 1}


def decide_iteration_suggestion_response(
    *,
    current_store: Any,
    payload: Any,
    suggestion_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_iteration_planning_role(user)
    validate_iteration_enums(decision=payload.decision)
    current_store = user_insight_write_store(current_store)
    suggestion = current_store.iteration_plan_suggestions.get(suggestion_id)
    if suggestion is None:
        raise api_error(404, "NOT_FOUND", "Iteration suggestion not found")
    if suggestion["status"] not in {"suggested", "accepted", "edited_accepted"}:
        raise api_error(
            409,
            "ITERATION_PLAN_STATE_INVALID",
            "Suggestion cannot be decided from current status",
        )
    if payload.convert_to_requirement and payload.decision == "rejected":
        raise api_error(
            400,
            "ITERATION_PLAN_DECISION_INVALID",
            "Rejected suggestion cannot convert to requirement",
        )
    requirement = None
    requirement_audit_event = None
    if payload.convert_to_requirement:
        requirement, requirement_audit_event = create_iteration_requirement(
            current_store,
            payload=payload,
            suggestion=suggestion,
            user=user,
        )
    now = datetime.now(UTC).isoformat()
    suggestion = {
        **suggestion,
        "status": "converted_to_requirement" if requirement is not None else payload.decision,
        "decision": payload.decision,
        "updated_at": now,
    }
    if payload.edited_title:
        suggestion["title"] = ensure_non_blank(payload.edited_title, "edited_title")
    if requirement is not None:
        suggestion["converted_requirement_id"] = requirement["id"]
    decision = {
        "comment": payload.comment,
        "convert_to_requirement": payload.convert_to_requirement,
        "created_requirement_id": requirement["id"] if requirement is not None else None,
        "decided_at": now,
        "decided_by": user["id"],
        "decision": payload.decision,
        "edited_scope": payload.edited_scope,
        "edited_title": payload.edited_title,
        "id": current_store.new_id("iteration_decision"),
        "suggestion_id": suggestion_id,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="iteration_suggestion.decided",
        actor_id=user["id"],
        subject_type="iteration_plan_suggestion",
        subject_id=suggestion_id,
        payload={
            "converted_requirement_id": suggestion.get("converted_requirement_id"),
            "decision": payload.decision,
            "status": suggestion["status"],
        },
    )
    audit_events = [
        *([] if requirement_audit_event is None else [requirement_audit_event]),
        audit_event,
    ]
    persist_iteration_decision_records(
        current_store,
        suggestion=suggestion,
        decision=decision,
        requirement=requirement,
        audit_events=audit_events,
    )
    return {
        **suggestion,
        "converted_requirement_id": suggestion.get("converted_requirement_id"),
        "decision": payload.decision,
    }
