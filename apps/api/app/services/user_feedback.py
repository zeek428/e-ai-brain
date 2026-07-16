from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.core.listing import add_list_observability, paginated_list_payload
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.product_config_context import product_config_source_store
from app.services.product_scope import require_product_scope
from app.services.user_insights import (
    ensure_enum,
    ensure_non_blank,
    payload_updates,
    record_audit_event,
    user_insight_query_repository,
)
from app.services.version_status import validate_requirement_version

USER_FEEDBACK_TYPES = {"bug", "complaint", "improvement", "praise", "question"}
USER_FEEDBACK_SENTIMENTS = {"negative", "neutral", "positive"}
USER_FEEDBACK_STATUSES = {"archived", "linked", "open", "resolved", "triaged"}
REQUIREMENT_PRIORITIES = {"P0", "P1", "P2"}


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _user_feedback_collection(current_store: Any) -> dict[str, dict[str, Any]]:
    return _memory_dict(current_store, "user_feedback")


def _requirements_collection(current_store: Any) -> dict[str, dict[str, Any]]:
    return _memory_dict(current_store, "requirements")


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
    products = _memory_dict(current_store, "products")
    product_modules = _memory_dict(current_store, "product_modules")
    requirements = _memory_dict(current_store, "requirements")
    if product_id not in products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if module_code is not None and not any(
        module["product_id"] == product_id and module["code"] == module_code
        for module in product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")
    if related_requirement_id is not None:
        requirement = requirements.get(related_requirement_id)
        if requirement is None or requirement["product_id"] != product_id:
            raise api_error(404, "NOT_FOUND", "Requirement not found")


def user_feedback_write_store(current_store: Any, *, feedback_id: str | None = None) -> Any:
    repository = user_insight_query_repository(current_store)
    if repository is None:
        return current_store
    source_store = product_config_source_store(repository)
    source_store.user_feedback = {}
    if feedback_id is None:
        return source_store
    get_feedback = getattr(repository, "get_user_feedback", None)
    if callable(get_feedback):
        feedback = get_feedback(feedback_id)
        if feedback is not None:
            source_store.user_feedback[str(feedback["id"])] = dict(feedback)
        return source_store
    source_store.user_feedback = {
        str(item["id"]): dict(item)
        for item in repository.list_user_feedback()
        if item.get("id") is not None
    }
    return source_store


def user_feedback_by_id(current_store: Any, feedback_id: str) -> dict[str, Any] | None:
    feedback = getattr(current_store, "user_feedback", {}).get(feedback_id)
    if feedback is not None:
        return dict(feedback)
    repository = getattr(current_store, "repository", None)
    get_feedback = getattr(repository, "get_user_feedback", None)
    if callable(get_feedback):
        feedback = get_feedback(feedback_id)
        return dict(feedback) if feedback is not None else None
    return None


def save_user_feedback_record(
    current_store: Any,
    feedback: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_user_feedback_record", None)
    if callable(save_record):
        save_record(feedback, audit_event=audit_event)
        return
    _user_feedback_collection(current_store)[str(feedback["id"])] = dict(feedback)


def normalized_tags(tags: list[str]) -> list[str]:
    normalized = []
    for tag in tags:
        value = tag.strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def require_user_feedback_triage_role(user: dict[str, Any]) -> None:
    require_any_permission_or_roles(user, {"insight.read"}, {"product_owner", "rd_owner"})


def list_user_feedback_response(
    *,
    created_by: str | None,
    current_store: Any,
    feature_code: str | None,
    module_code: str | None,
    page: int | None = None,
    page_size: int | None = None,
    product_id: str | None,
    started_at: float | None = None,
    status: str | None,
    summary_only: bool = False,
    trace_id: str = "",
) -> dict[str, Any]:
    validate_user_feedback_enums(status=status)
    filters = {
        "created_by": created_by,
        "feature_code": feature_code,
        "module_code": module_code,
        "product_id": product_id,
        "status": status,
        "summary_only": summary_only or None,
    }
    repository = user_insight_query_repository(current_store)
    if repository is not None:
        use_pagination = page is not None or page_size is not None
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        list_filters = {
            "product_id": product_id,
            "module_code": module_code,
            "feature_code": feature_code,
            "status": status,
            "created_by": created_by,
        }
        count_feedback = getattr(repository, "count_user_feedback", None)
        if use_pagination and callable(count_feedback):
            total = count_feedback(
                **list_filters,
            )
            items = repository.list_user_feedback(
                **list_filters,
                limit=resolved_page_size,
                offset=(resolved_page - 1) * resolved_page_size,
                summary_only=summary_only,
            )
            return add_list_observability(
                {
                    "items": items,
                    "page": resolved_page,
                    "page_size": resolved_page_size,
                    "total": total,
                },
                filters=filters,
                list_name="user_feedback",
                page=resolved_page,
                page_size=resolved_page_size,
                sort_by="updated_at",
                sort_order="desc",
                started_at=started_at,
            )
        if summary_only:
            items = repository.list_user_feedback(**list_filters, summary_only=True)
        else:
            items = repository.list_user_feedback(**list_filters)
        if not use_pagination:
            payload = {"items": items, "total": len(items)}
            if started_at is not None:
                payload = add_list_observability(
                    payload,
                    filters=filters,
                    list_name="user_feedback",
                    sort_by="updated_at",
                    sort_order="desc",
                    started_at=started_at,
                )
            return payload
        return paginated_list_payload(
            items,
            filters=filters,
            list_name="user_feedback",
            observed=True,
            page=page,
            page_size=page_size,
            sort_by="updated_at",
            sort_order="desc",
            started_at=started_at,
            trace_id=trace_id,
        )["data"]
    items = []
    for feedback in _user_feedback_collection(current_store).values():
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
    if summary_only:
        items = [
            {
                **item,
                "content": (
                    f"{str(item.get('content') or '')[:240]}..."
                    if len(str(item.get("content") or "")) > 240
                    else item.get("content")
                ),
            }
            for item in items
        ]
    return paginated_list_payload(
        items,
        filters=filters,
        list_name="user_feedback",
        observed=started_at is not None,
        page=page,
        page_size=page_size,
        sort_by="updated_at",
        sort_order="desc",
        started_at=started_at,
        trace_id=trace_id,
    )["data"]


def create_user_feedback_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    current_store = user_feedback_write_store(current_store)
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
    save_user_feedback_record(
        current_store,
        feedback,
        audit_event=audit_event,
    )
    return feedback


def write_ai_generated_user_feedback_insights(
    current_store: Any,
    *,
    default_product_id: str | None,
    insights: list[Any],
    source_channel: str,
    user: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    """Persist structured AI insight candidates through the user-feedback write boundary."""
    created: list[dict[str, Any]] = []
    skipped = 0
    for insight in insights:
        if not isinstance(insight, dict) or not str(insight.get("content") or "").strip():
            skipped += 1
            continue
        candidate_product_id = str(insight.get("product_id") or "").strip()
        if (
            default_product_id
            and candidate_product_id
            and candidate_product_id != default_product_id
        ):
            raise api_error(
                409,
                "RESULT_ACTION_PRODUCT_MISMATCH",
                "User insight candidate does not belong to the scheduled job product",
            )
        product_id = default_product_id or candidate_product_id
        if not product_id:
            raise api_error(400, "VALIDATION_ERROR", "User insight product_id is required")
        require_product_scope(user, product_id)
        feature_code = insight.get("feature_code")
        module_code = insight.get("module_code")
        related_requirement_id = insight.get("related_requirement_id")
        payload = SimpleNamespace(
            content=str(insight["content"]),
            feature_code=feature_code if isinstance(feature_code, str) else None,
            feedback_type=(
                str(insight.get("feedback_type"))
                if str(insight.get("feedback_type") or "") in USER_FEEDBACK_TYPES
                else "improvement"
            ),
            module_code=module_code if isinstance(module_code, str) else None,
            product_id=product_id,
            related_requirement_id=(
                related_requirement_id if isinstance(related_requirement_id, str) else None
            ),
            satisfaction_score=(
                insight.get("satisfaction_score")
                if isinstance(insight.get("satisfaction_score"), int)
                else None
            ),
            sentiment=(
                str(insight.get("sentiment"))
                if str(insight.get("sentiment") or "") in USER_FEEDBACK_SENTIMENTS
                else "neutral"
            ),
            source_channel=str(insight.get("source_channel") or source_channel),
            tags=insight.get("tags") if isinstance(insight.get("tags"), list) else [],
        )
        created.append(
            create_user_feedback_response(
                current_store=current_store,
                payload=payload,
                user=user,
            ),
        )
    return created, skipped


def patch_user_feedback_response(
    *,
    current_store: Any,
    feedback_id: str,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_user_feedback_triage_role(user)
    current_store = user_feedback_write_store(current_store, feedback_id=feedback_id)
    feedback = user_feedback_by_id(current_store, feedback_id)
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
    save_user_feedback_record(
        current_store,
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
        return
    _requirements_collection(current_store)[str(requirement["id"])] = dict(requirement)
    _user_feedback_collection(current_store)[str(feedback["id"])] = dict(feedback)


def convert_user_feedback_to_requirement_response(
    *,
    current_store: Any,
    feedback_id: str,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_user_feedback_triage_role(user)
    current_store = user_feedback_write_store(current_store, feedback_id=feedback_id)
    feedback = user_feedback_by_id(current_store, feedback_id)
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
