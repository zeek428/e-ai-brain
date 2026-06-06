from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_roles
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.user_insights import (
    ensure_enum,
    ensure_non_blank,
    payload_updates,
    record_audit_event,
    save_single_repository_record,
    user_insight_query_repository,
    user_insight_write_store,
    uses_repository_context,
)
from app.services.version_status import validate_requirement_version

USER_FEEDBACK_TYPES = {"bug", "complaint", "improvement", "praise", "question"}
USER_FEEDBACK_SENTIMENTS = {"negative", "neutral", "positive"}
USER_FEEDBACK_STATUSES = {"archived", "linked", "open", "resolved", "triaged"}
REQUIREMENT_PRIORITIES = {"P0", "P1", "P2"}


def validate_user_feedback_enums(
    *,
    feedback_type: str | None = None,
    sentiment: str | None = None,
    status: str | None = None,
) -> None:
    ensure_enum(feedback_type, USER_FEEDBACK_TYPES, "feedback_type")
    ensure_enum(sentiment, USER_FEEDBACK_SENTIMENTS, "sentiment")
    ensure_enum(status, USER_FEEDBACK_STATUSES, "status")


def validate_satisfaction_score(score: int | None) -> None:
    if score is not None and (score < 1 or score > 5):
        raise api_error(400, "VALIDATION_ERROR", "satisfaction_score must be between 1 and 5")


def validate_user_feedback_context(
    current_store: Any,
    *,
    product_id: str,
    module_code: str | None = None,
    related_requirement_id: str | None = None,
) -> None:
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if module_code is not None and not any(
        module["product_id"] == product_id and module["code"] == module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")
    if related_requirement_id is not None:
        requirement = current_store.requirements.get(related_requirement_id)
        if requirement is None or requirement["product_id"] != product_id:
            raise api_error(404, "NOT_FOUND", "Requirement not found")


def normalized_tags(tags: list[str]) -> list[str]:
    normalized = []
    for tag in tags:
        value = tag.strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def require_user_feedback_triage_role(user: dict[str, Any]) -> None:
    require_roles(user, {"product_owner", "rd_owner"})


def list_user_feedback_response(
    *,
    created_by: str | None,
    current_store: Any,
    feature_code: str | None,
    module_code: str | None,
    product_id: str | None,
    status: str | None,
) -> dict[str, Any]:
    validate_user_feedback_enums(status=status)
    repository = user_insight_query_repository(current_store)
    if repository is not None:
        items = repository.list_user_feedback(
            product_id=product_id,
            module_code=module_code,
            feature_code=feature_code,
            status=status,
            created_by=created_by,
        )
        return {"items": items, "total": len(items)}
    items = []
    for feedback in current_store.user_feedback.values():
        if product_id is not None and feedback.get("product_id") != product_id:
            continue
        if module_code is not None and feedback.get("module_code") != module_code:
            continue
        if feature_code is not None and feedback.get("feature_code") != feature_code:
            continue
        if status is not None and feedback.get("status") != status:
            continue
        if created_by is not None and feedback.get("created_by") != created_by:
            continue
        items.append(feedback)
    items.sort(
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )
    return {"items": items, "total": len(items)}


def create_user_feedback_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    current_store = user_insight_write_store(current_store)
    validate_user_feedback_enums(
        feedback_type=payload.feedback_type,
        sentiment=payload.sentiment,
    )
    validate_satisfaction_score(payload.satisfaction_score)
    validate_user_feedback_context(
        current_store,
        product_id=payload.product_id,
        module_code=payload.module_code,
        related_requirement_id=payload.related_requirement_id,
    )
    now = datetime.now(UTC).isoformat()
    feedback = {
        "content": ensure_non_blank(payload.content, "content"),
        "created_at": now,
        "created_by": user["id"],
        "feature_code": payload.feature_code.strip() if payload.feature_code else None,
        "feedback_type": payload.feedback_type,
        "id": current_store.new_id("feedback"),
        "module_code": payload.module_code,
        "product_id": payload.product_id,
        "related_requirement_id": payload.related_requirement_id,
        "satisfaction_score": payload.satisfaction_score,
        "sentiment": payload.sentiment,
        "source_channel": ensure_non_blank(payload.source_channel, "source_channel"),
        "status": "open",
        "tags": normalized_tags(payload.tags),
        "updated_at": now,
    }
    if not uses_repository_context(current_store):
        current_store.user_feedback[feedback["id"]] = feedback
    audit_event = record_audit_event(
        current_store,
        event_type="user_feedback.created",
        actor_id=user["id"],
        subject_type="user_feedback",
        subject_id=feedback["id"],
        payload={
            "feedback_type": feedback["feedback_type"],
            "product_id": feedback["product_id"],
            "status": feedback["status"],
        },
    )
    save_single_repository_record(
        current_store,
        "save_user_feedback_record",
        feedback,
        audit_event=audit_event,
    )
    return feedback


def patch_user_feedback_response(
    *,
    current_store: Any,
    feedback_id: str,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_user_feedback_triage_role(user)
    current_store = user_insight_write_store(current_store)
    feedback = current_store.user_feedback.get(feedback_id)
    if feedback is None:
        raise api_error(404, "NOT_FOUND", "User feedback not found")
    updates = payload_updates(payload)
    validate_user_feedback_enums(
        sentiment=updates.get("sentiment"),
        status=updates.get("status"),
    )
    validate_satisfaction_score(updates.get("satisfaction_score"))
    if "content" in updates:
        updates["content"] = ensure_non_blank(updates["content"], "content")
    if "tags" in updates:
        updates["tags"] = normalized_tags(updates["tags"])
    feedback = {**feedback, **updates, "updated_at": datetime.now(UTC).isoformat()}
    if not uses_repository_context(current_store):
        current_store.user_feedback[feedback_id] = feedback
    audit_event = record_audit_event(
        current_store,
        event_type="user_feedback.updated",
        actor_id=user["id"],
        subject_type="user_feedback",
        subject_id=feedback_id,
        payload={
            "status": feedback["status"],
            "updated_fields": sorted(updates.keys()),
        },
    )
    save_single_repository_record(
        current_store,
        "save_user_feedback_record",
        feedback,
        audit_event=audit_event,
    )
    return feedback


def save_user_feedback_requirement_conversion(
    current_store: Any,
    *,
    audit_events: list[dict[str, Any]],
    feedback: dict[str, Any],
    requirement: dict[str, Any],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_conversion = getattr(repository, "save_user_feedback_requirement_conversion", None)
    if callable(save_conversion):
        save_conversion(
            audit_events=audit_events,
            feedback=feedback,
            requirement=requirement,
        )


def convert_user_feedback_to_requirement_response(
    *,
    current_store: Any,
    feedback_id: str,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_user_feedback_triage_role(user)
    current_store = user_insight_write_store(current_store)
    feedback = current_store.user_feedback.get(feedback_id)
    if feedback is None:
        raise api_error(404, "NOT_FOUND", "User feedback not found")
    if feedback.get("related_requirement_id"):
        raise api_error(409, "RESOURCE_IN_USE", "User feedback already linked to requirement")

    product_id = payload.product_id or feedback["product_id"]
    if payload.priority not in REQUIREMENT_PRIORITIES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported requirement priority")
    validate_user_feedback_context(
        current_store,
        product_id=product_id,
        module_code=payload.module_code or feedback.get("module_code"),
    )
    validate_requirement_version(
        current_store,
        product_id=product_id,
        version_id=payload.version_id,
    )
    title = ensure_non_blank(payload.title, "title")
    content = ensure_non_blank(payload.content or feedback["content"], "content")
    now = datetime.now(UTC).isoformat()
    requirement = {
        "assignee": user["id"],
        "brain_app_id": DEFAULT_BRAIN_APP_ID,
        "content": content,
        "created_at": now,
        "created_by": user["id"],
        "id": current_store.new_id("requirement"),
        "module_code": payload.module_code or feedback.get("module_code"),
        "priority": payload.priority,
        "product_id": product_id,
        "source": "user_feedback",
        "status": "submitted",
        "task_ids": [],
        "title": title,
        "updated_at": now,
        "version_id": payload.version_id,
    }
    feedback = {
        **feedback,
        "product_id": product_id,
        "related_requirement_id": requirement["id"],
        "status": "linked",
        "triage_note": payload.triage_note or feedback.get("triage_note"),
        "updated_at": now,
    }
    if not uses_repository_context(current_store):
        current_store.requirements[requirement["id"]] = requirement
        current_store.user_feedback[feedback_id] = feedback
    requirement_audit_event = record_audit_event(
        current_store,
        event_type="requirement.created",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement["id"],
        payload={"feedback_id": feedback_id, "source": "user_feedback"},
    )
    feedback_audit_event = record_audit_event(
        current_store,
        event_type="user_feedback.linked_requirement",
        actor_id=user["id"],
        subject_type="user_feedback",
        subject_id=feedback_id,
        payload={"requirement_id": requirement["id"], "status": feedback["status"]},
    )
    save_user_feedback_requirement_conversion(
        current_store,
        audit_events=[requirement_audit_event, feedback_audit_event],
        feedback=feedback,
        requirement=requirement,
    )
    return {"feedback": feedback, "requirement": requirement}
