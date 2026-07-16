from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.code_inspection_common import validate_code_inspection_result_actions
from app.services.plugin_result_mapping import (
    compact_preview_value,
    json_path_value,
    result_write_preview,
)
from app.services.product_scope import require_product_scope
from app.services.requirements import (
    REQUIREMENT_SOURCES,
    record_audit_event,
    requirement_write_store,
    save_requirement_record,
)
from app.services.result_write_targets import result_write_target_label
from app.services.scheduled_job_common import ensure_enum
from app.services.scheduled_job_config import scheduled_job_result_action_policy
from app.services.scheduled_job_runtime import exception_error_code_and_message
from app.services.system_settings import send_system_email
from app.services.user_feedback import write_ai_generated_user_feedback_insights
from app.services.version_status import validate_requirement_version

REQUIREMENT_PRIORITIES = {"P0", "P1", "P2"}
GENERIC_RESULT_ACTION_TYPES = {
    "create_requirements",
    "save_scheduled_job_result",
    "send_notification",
    "sync_dingtalk_document",
    "write_internal_user_insights",
}
GENERIC_NOTIFICATION_CHANNELS = {"dingtalk", "email"}
GENERIC_RESULT_ACTION_JOB_TYPES = {
    "online_log_ai_analysis",
    "plugin_action_invoke",
    "user_feedback_insight_extract",
}
DINGTALK_DOCUMENT_SYNC_RESULT_ACTION_JOB_TYPES = {
    "plugin_action_invoke",
    "user_feedback_insight_extract",
}
DINGTALK_WRITE_MODES = {"append", "overwrite"}


def validate_scheduled_job_result_actions(job_type: str, actions: Any) -> list[dict[str, Any]]:
    if job_type == "code_repository_inspection":
        return validate_code_inspection_result_actions(actions)
    if actions is None:
        return []
    if not isinstance(actions, list):
        raise api_error(400, "VALIDATION_ERROR", "result_actions must be a list")
    if job_type not in GENERIC_RESULT_ACTION_JOB_TYPES:
        return []
    normalized: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            raise api_error(400, "VALIDATION_ERROR", "result action must be an object")
        action_type = str(action.get("type") or "")
        ensure_enum(action_type, GENERIC_RESULT_ACTION_TYPES, "result action type")
        if action_type == "send_notification":
            normalized.append(_normalize_notification_action(action))
        elif action_type == "create_requirements":
            _ensure_plugin_invoke_result_action(job_type, action_type)
            normalized.append(_normalize_create_requirements_action(action))
        elif action_type == "write_internal_user_insights":
            _ensure_plugin_invoke_result_action(job_type, action_type)
            normalized.append(_normalize_write_internal_user_insights_action(action))
        elif action_type == "sync_dingtalk_document":
            _ensure_dingtalk_document_sync_result_action(job_type, action_type)
            normalized.append(_normalize_sync_dingtalk_document_action(action))
        else:
            normalized.append({**action, "type": action_type})
    return normalized


def default_generic_result_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return actions if actions else [{"type": "save_scheduled_job_result"}]


def execute_generic_result_actions(
    *,
    current_store: Any,
    job: dict[str, Any],
    output_json: dict[str, Any],
    output_mapping: dict[str, Any],
    result_actions: list[dict[str, Any]],
    scheduled_job_run_id: str | None = None,
    user: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    policy = scheduled_job_result_action_policy(job)
    executed: list[dict[str, Any]] = []
    result_context: dict[str, Any] = {}
    total_records = 0
    for action in default_generic_result_actions(result_actions):
        action_type = str(action.get("type") or "save_scheduled_job_result")
        try:
            result = _generic_result_action_node(
                action=action,
                action_type=action_type,
                current_store=current_store,
                job=job,
                output_json=output_json,
                output_mapping=output_mapping,
                result_context=result_context,
                scheduled_job_run_id=scheduled_job_run_id,
                user=user,
            )
            total_records += int(result.get("records_imported") or 0)
            _merge_result_action_context(result_context, result)
            executed.append(result)
        except Exception as exc:
            error_code, error_message = exception_error_code_and_message(exc)
            executed.append(
                {
                    "action_type": action_type,
                    "error_code": error_code,
                    "error_message": error_message,
                    "feedback": {"error_code": error_code, "error_message": error_message},
                    "label": "结果动作反馈内容",
                    "records_imported": 0,
                    "status": "failed",
                    "type": action_type,
                    "write_target": _write_target_for_action(action_type),
                    "write_target_label": result_write_target_label(
                        _write_target_for_action(action_type),
                    ),
                },
            )
            if policy["failure_policy"] == "fail_fast":
                raise
    return executed, total_records


def preview_generic_result_actions(
    *,
    output_mapping: dict[str, Any],
    preview_response_summary: dict[str, Any],
    result_actions: list[dict[str, Any]],
    source: str,
) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    for action in default_generic_result_actions(result_actions):
        action_type = str(action.get("type") or "save_scheduled_job_result")
        mapping = {
            **output_mapping,
            **_result_action_mapping(action, action_type),
            "write_target": _write_target_for_action(action_type),
        }
        preview = result_write_preview(preview_response_summary, mapping)
        previews.append(
            {
                "action_type": action_type,
                "channels": (
                    action.get("channels") if isinstance(action.get("channels"), list) else []
                ),
                "recipients": (
                    action.get("recipients") if isinstance(action.get("recipients"), list) else []
                ),
                "type": action_type,
                "write_preview": preview,
                "write_preview_source": source,
                "write_target": preview.get("write_target"),
                "write_target_label": preview.get("write_target_label"),
            },
        )
    return previews


def inferred_output_record_count(
    output_json: dict[str, Any],
    output_mapping: dict[str, Any],
) -> int:
    for path in (
        output_mapping.get("records_imported_path"),
        output_mapping.get("anomalies_path"),
        output_mapping.get("insights_path"),
        output_mapping.get("findings_path"),
        "$.anomalies",
        "$.insights",
        "$.findings",
        "$.rows",
        "$.items",
    ):
        value = json_path_value(output_json, str(path)) if path else None
        if isinstance(value, int) and value >= 0:
            return value
        if isinstance(value, list):
            return len(value)
    return 1 if output_json else 0


def _normalize_notification_action(action: dict[str, Any]) -> dict[str, Any]:
    channels = action.get("channels") if isinstance(action.get("channels"), list) else []
    normalized_channels = [str(channel) for channel in channels if str(channel or "").strip()]
    if not normalized_channels:
        raise api_error(400, "VALIDATION_ERROR", "send_notification requires channels")
    for channel in normalized_channels:
        ensure_enum(channel, GENERIC_NOTIFICATION_CHANNELS, "notification channel")
    recipients = action.get("recipients") if isinstance(action.get("recipients"), list) else []
    return {
        **action,
        "channels": normalized_channels,
        "recipients": [str(item) for item in recipients if str(item or "").strip()],
        "type": "send_notification",
    }


def _ensure_plugin_invoke_result_action(job_type: str, action_type: str) -> None:
    if job_type != "plugin_action_invoke":
        raise api_error(
            400,
            "VALIDATION_ERROR",
            f"{action_type} is only supported for plugin_action_invoke jobs",
        )


def _ensure_dingtalk_document_sync_result_action(job_type: str, action_type: str) -> None:
    if job_type not in DINGTALK_DOCUMENT_SYNC_RESULT_ACTION_JOB_TYPES:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            f"{action_type} is only supported for plugin_action_invoke "
            "or user_feedback_insight_extract jobs",
        )


def _normalize_create_requirements_action(action: dict[str, Any]) -> dict[str, Any]:
    source = str(action.get("source") or "user_feedback")
    ensure_enum(source, REQUIREMENT_SOURCES, "requirement source")
    priority = str(action.get("priority") or "P1")
    ensure_enum(priority, REQUIREMENT_PRIORITIES, "requirement priority")
    max_items = int(action.get("max_items") or 20)
    if max_items <= 0 or max_items > 100:
        raise api_error(400, "VALIDATION_ERROR", "create_requirements max_items must be 1-100")
    return {
        **action,
        "max_items": max_items,
        "priority": priority,
        "requirements_path": str(action.get("requirements_path") or "$.requirements"),
        "source": source,
        "type": "create_requirements",
    }


def _normalize_write_internal_user_insights_action(action: dict[str, Any]) -> dict[str, Any]:
    max_items = int(action.get("max_items") or 100)
    if max_items <= 0 or max_items > 1000:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "write_internal_user_insights max_items must be 1-1000",
        )
    return {
        **action,
        "insights_path": str(action.get("insights_path") or "$.insights"),
        "max_items": max_items,
        "source_channel": str(action.get("source_channel") or "scheduled_job_ai"),
        "type": "write_internal_user_insights",
    }


def _normalize_sync_dingtalk_document_action(action: dict[str, Any]) -> dict[str, Any]:
    plugin_action_id = str(action.get("plugin_action_id") or "").strip()
    if not plugin_action_id:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "sync_dingtalk_document requires plugin_action_id",
        )
    document_id = str(action.get("document_id") or "").strip()
    if not document_id:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "sync_dingtalk_document requires document_id",
        )
    write_mode = str(action.get("write_mode") or "append")
    ensure_enum(write_mode, DINGTALK_WRITE_MODES, "dingtalk document write mode")
    normalized = {
        **action,
        "content_template": str(action.get("content_template") or "{{dingtalk_markdown}}"),
        "document_id": document_id,
        "plugin_action_id": plugin_action_id,
        "type": "sync_dingtalk_document",
        "write_mode": write_mode,
    }
    plugin_connection_id = str(action.get("plugin_connection_id") or "").strip()
    if plugin_connection_id:
        normalized["plugin_connection_id"] = plugin_connection_id
    return normalized


def _generic_result_action_node(
    *,
    action: dict[str, Any],
    action_type: str,
    current_store: Any,
    job: dict[str, Any],
    output_json: dict[str, Any],
    output_mapping: dict[str, Any],
    result_context: dict[str, Any],
    scheduled_job_run_id: str | None,
    user: dict[str, Any] | None,
) -> dict[str, Any]:
    write_target = _write_target_for_action(action_type)
    records_imported = inferred_output_record_count(output_json, output_mapping)
    write_preview = result_write_preview(
        {"json": output_json},
        {
            **output_mapping,
            **_result_action_mapping(action, action_type),
            "write_target": write_target,
        },
    )
    feedback: dict[str, Any] = {
        "records_imported": records_imported,
        "stored_in_run_result": True,
        "write_preview": write_preview,
        "write_target": write_target,
    }
    if action_type == "send_notification":
        subject = action.get("subject") or output_json.get("summary") or "AI Brain 定时作业结果"
        recipients = action.get("recipients") or []
        channels = action.get("channels") or []
        email_delivery: dict[str, Any] | None = None
        if "email" in channels:
            email_delivery = send_system_email(
                current_store,
                body=_notification_body(output_json),
                recipients=recipients,
                subject=str(subject),
            )
        feedback.update(
            {
                "channels": channels,
                "delivery_status": (
                    email_delivery["delivery_status"] if email_delivery else "recorded"
                ),
                "message_id": email_delivery.get("message_id") if email_delivery else None,
                "recipients": email_delivery.get("recipients") if email_delivery else recipients,
                "sample_records": [compact_preview_value(output_json)],
                "subject": subject,
                "webhook_configured": bool(action.get("webhook_url")),
            },
        )
        records_imported = max(1, len(feedback["recipients"]))
        feedback["records_imported"] = records_imported
        feedback["sample_records"] = feedback["recipients"][:3] or feedback["sample_records"]
        feedback["write_preview"] = {
            **write_preview,
            "candidate_count": records_imported,
            "delivery_id": email_delivery.get("message_id") if email_delivery else None,
            "delivery_status": feedback["delivery_status"],
            "records_imported": records_imported,
            "sample_records": feedback["sample_records"],
            "subject": subject,
            "write_target": write_target,
            "write_target_label": result_write_target_label(write_target),
        }
    elif action_type == "create_requirements":
        created_requirements = _create_requirements_from_output(
            current_store=current_store,
            action=action,
            job=job,
            output_json=output_json,
            scheduled_job_run_id=scheduled_job_run_id,
            user=user,
        )
        records_imported = len(created_requirements)
        feedback.update(
            {
                "created_requirements": created_requirements,
                "created_requirement_ids": [
                    requirement["id"] for requirement in created_requirements
                ],
                "records_imported": records_imported,
                "sample_records": [
                    compact_preview_value(
                        {
                            "id": requirement["id"],
                            "priority": requirement.get("priority"),
                            "title": requirement.get("title"),
                        },
                    )
                    for requirement in created_requirements[:3]
                ],
                "write_preview": {
                    **write_preview,
                    "candidate_count": records_imported,
                    "created_requirement_ids": [
                        requirement["id"] for requirement in created_requirements
                    ],
                    "records_imported": records_imported,
                    "sample_records": [
                        compact_preview_value(requirement)
                        for requirement in created_requirements[:3]
                    ],
                    "write_target": write_target,
                    "write_target_label": result_write_target_label(write_target),
                },
            },
        )
    elif action_type == "write_internal_user_insights":
        created_insights, skipped_insights = _write_internal_user_insights_from_output(
            action=action,
            current_store=current_store,
            job=job,
            output_json=output_json,
            user=user,
        )
        records_imported = len(created_insights)
        feedback.update(
            {
                "created_insight_ids": [item["id"] for item in created_insights],
                "records_imported": records_imported,
                "sample_records": [
                    compact_preview_value(
                        {
                            "content": item.get("content"),
                            "id": item.get("id"),
                            "sentiment": item.get("sentiment"),
                        },
                    )
                    for item in created_insights[:3]
                ],
                "skipped_insights": skipped_insights,
                "write_preview": {
                    **write_preview,
                    "candidate_count": len(created_insights) + skipped_insights,
                    "created_insight_ids": [item["id"] for item in created_insights],
                    "records_imported": records_imported,
                    "sample_records": [
                        compact_preview_value(item) for item in created_insights[:3]
                    ],
                    "write_target": write_target,
                    "write_target_label": result_write_target_label(write_target),
                },
            },
        )
    elif action_type == "sync_dingtalk_document":
        dingtalk_feedback = _sync_dingtalk_document(
            action=action,
            current_store=current_store,
            output_json=output_json,
            result_context=result_context,
            scheduled_job_id=str(job.get("id") or ""),
            scheduled_job_run_id=scheduled_job_run_id,
            user=user,
        )
        records_imported = int(dingtalk_feedback.get("records_imported") or 1)
        feedback.update(dingtalk_feedback)
    else:
        feedback["result_preview"] = compact_preview_value(output_json)
    return {
        "action_type": action_type,
        "feedback": feedback,
        "label": "结果动作反馈内容",
        "records_imported": records_imported,
        "status": "succeeded",
        "type": action_type,
        "write_target": write_target,
        "write_target_label": result_write_target_label(write_target),
    }


def _write_target_for_action(action_type: str) -> str:
    if action_type == "send_notification":
        return "email_notifications"
    if action_type == "create_requirements":
        return "requirements"
    if action_type == "sync_dingtalk_document":
        return "dingtalk_document"
    if action_type == "write_internal_user_insights":
        return "user_feedback_insights"
    return "scheduled_job_result"


def _merge_result_action_context(context: dict[str, Any], result: dict[str, Any]) -> None:
    feedback = result.get("feedback") if isinstance(result.get("feedback"), dict) else {}
    if result.get("action_type") == "create_requirements":
        created = feedback.get("created_requirements")
        if isinstance(created, list):
            context["created_requirements"] = created
    if result.get("action_type") == "write_internal_user_insights":
        created_ids = feedback.get("created_insight_ids")
        if isinstance(created_ids, list):
            context["created_insight_ids"] = created_ids


def _result_action_mapping(action: dict[str, Any], action_type: str) -> dict[str, Any]:
    if action_type == "create_requirements":
        return {
            "priority": action.get("priority"),
            "requirements_path": action.get("requirements_path") or "$.requirements",
        }
    if action_type == "sync_dingtalk_document":
        return {
            "content_template": action.get("content_template") or "{{dingtalk_markdown}}",
            "document_id": action.get("document_id"),
            "write_mode": action.get("write_mode") or "append",
        }
    if action_type == "write_internal_user_insights":
        return {
            "insights_path": action.get("insights_path") or "$.insights",
            "records_imported_path": "$.row_count",
        }
    return {}


def _write_internal_user_insights_from_output(
    *,
    action: dict[str, Any],
    current_store: Any,
    job: dict[str, Any],
    output_json: dict[str, Any],
    user: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], int]:
    if user is None:
        raise api_error(403, "PERMISSION_DENIED", "User context is required")
    insights = _list_at_first_path(
        output_json,
        [str(action.get("insights_path") or "$.insights"), "$.insights", "$.items"],
    )
    return write_ai_generated_user_feedback_insights(
        current_store,
        default_product_id=str(job.get("product_id") or "").strip() or None,
        insights=insights[: int(action.get("max_items") or 100)],
        source_channel=str(action.get("source_channel") or "scheduled_job_ai"),
        user=user,
    )


def _list_at_first_path(payload: dict[str, Any], paths: list[str]) -> list[dict[str, Any]]:
    for path in paths:
        value = json_path_value(payload, path)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _candidate_text(candidate: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _candidate_priority(candidate: dict[str, Any], default_priority: str) -> str:
    value = str(candidate.get("priority") or candidate.get("priority_suggestion") or "").upper()
    return value if value in REQUIREMENT_PRIORITIES else default_priority


def _candidate_content(candidate: dict[str, Any]) -> str:
    content = _candidate_text(candidate, "content", "description", "summary", "user_problem")
    acceptance = candidate.get("acceptance_criteria")
    evidence = candidate.get("evidence")
    parts = [content] if content else []
    if isinstance(acceptance, list) and acceptance:
        parts.append("验收标准：\n" + "\n".join(f"- {item}" for item in acceptance if item))
    elif isinstance(acceptance, str) and acceptance.strip():
        parts.append(f"验收标准：\n{acceptance.strip()}")
    if isinstance(evidence, list) and evidence:
        parts.append("证据：\n" + "\n".join(f"- {item}" for item in evidence if item))
    elif isinstance(evidence, str) and evidence.strip():
        parts.append(f"证据：\n{evidence.strip()}")
    return "\n\n".join(parts).strip()


def _create_requirements_from_output(
    *,
    current_store: Any,
    action: dict[str, Any],
    job: dict[str, Any],
    output_json: dict[str, Any],
    scheduled_job_run_id: str | None,
    user: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if user is None:
        raise api_error(403, "PERMISSION_DENIED", "User context is required")
    current_store = requirement_write_store(current_store)
    requirements = _list_at_first_path(
        output_json,
        [
            str(action.get("requirements_path") or "$.requirements"),
            "$.requirement_candidates",
            "$.items",
        ],
    )
    max_items = int(action.get("max_items") or 20)
    default_priority = str(action.get("priority") or "P1")
    source = str(action.get("source") or "user_feedback")
    created: list[dict[str, Any]] = []
    products = getattr(current_store, "products", {})
    modules = getattr(current_store, "product_modules", {})
    stored_requirements = getattr(current_store, "requirements", {})
    existing_by_idempotency_key = {
        str(raw_payload.get("idempotency_key")): requirement
        for requirement in (
            stored_requirements.values() if isinstance(stored_requirements, dict) else []
        )
        if isinstance(requirement, dict)
        if isinstance((raw_payload := requirement.get("raw_payload")), dict)
        if raw_payload.get("idempotency_key")
    }
    job_product_id = str(job.get("product_id") or "").strip()
    now = datetime.now(UTC).isoformat()
    prepared: list[dict[str, Any]] = []
    for candidate in requirements[:max_items]:
        candidate_product_id = str(candidate.get("product_id") or "").strip()
        if job_product_id and candidate_product_id and candidate_product_id != job_product_id:
            raise api_error(
                409,
                "RESULT_ACTION_PRODUCT_MISMATCH",
                "Requirement candidate does not belong to the scheduled job product",
            )
        product_id = job_product_id or candidate_product_id
        if not product_id:
            raise api_error(400, "VALIDATION_ERROR", "Requirement product_id is required")
        require_product_scope(user, product_id)
        product = products.get(product_id) if isinstance(products, dict) else None
        if product is None:
            raise api_error(404, "NOT_FOUND", "Product not found")
        if product.get("status") != "active":
            raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
        version_id = str(candidate.get("version_id") or "").strip() or None
        validate_requirement_version(
            current_store,
            product_id=product_id,
            version_id=version_id,
        )
        module_code = candidate.get("module_code")
        if module_code is not None and not any(
            module.get("product_id") == product_id and module.get("code") == module_code
            for module in (modules.values() if isinstance(modules, dict) else [])
            if isinstance(module, dict)
        ):
            raise api_error(404, "NOT_FOUND", "Product module not found")
        title = _candidate_text(candidate, "title", "name")
        content = _candidate_content(candidate)
        if not title or not content:
            continue
        idempotency_key = None
        if scheduled_job_run_id:
            fingerprint_payload = {
                "candidate": candidate,
                "job_id": job.get("id"),
                "requirements_path": action.get("requirements_path") or "$.requirements",
                "scheduled_job_run_id": scheduled_job_run_id,
            }
            fingerprint = hashlib.sha256(
                json.dumps(
                    fingerprint_payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                ).encode(),
            ).hexdigest()[:24]
            idempotency_key = f"scheduled-job-requirement:{fingerprint}"
        prepared.append(
            {
                "candidate": candidate,
                "content": content,
                "idempotency_key": idempotency_key,
                "module_code": module_code,
                "product_id": product_id,
                "title": title,
                "version_id": version_id,
            }
        )

    emitted_idempotency_keys: set[str] = set()
    for item in prepared:
        idempotency_key = item["idempotency_key"]
        if idempotency_key and idempotency_key in emitted_idempotency_keys:
            continue
        if idempotency_key and idempotency_key in existing_by_idempotency_key:
            created.append(dict(existing_by_idempotency_key[idempotency_key]))
            emitted_idempotency_keys.add(idempotency_key)
            continue
        requirement_id = current_store.new_id("requirement")
        requirement = {
            "assignee": user["id"],
            "brain_app_id": DEFAULT_BRAIN_APP_ID,
            "content": item["content"],
            "created_at": now,
            "created_by": user["id"],
            "id": requirement_id,
            "module_code": item["module_code"],
            "priority": _candidate_priority(item["candidate"], default_priority),
            "product_id": item["product_id"],
            "raw_payload": {
                "idempotency_key": idempotency_key,
                "scheduled_job_id": job.get("id"),
                "scheduled_job_run_id": scheduled_job_run_id,
                "source_candidate": compact_preview_value(item["candidate"]),
            },
            "source": source,
            "status": "submitted",
            "task_ids": [],
            "title": item["title"],
            "version_id": item["version_id"],
        }
        audit_event = record_audit_event(
            current_store,
            event_type="requirement.created",
            actor_id=user["id"],
            subject_type="requirement",
            subject_id=requirement_id,
            payload={
                "scheduled_job_id": job.get("id"),
                "source": "scheduled_job_result_action",
            },
        )
        save_requirement_record(current_store, requirement, audit_event=audit_event)
        created.append(requirement)
        if idempotency_key:
            emitted_idempotency_keys.add(idempotency_key)
    return created


def _json_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _requirements_markdown(requirements: list[dict[str, Any]]) -> str:
    if not requirements:
        return ""
    lines = ["## 写入需求管理"]
    for requirement in requirements:
        lines.append(
            f"- [{requirement.get('priority') or '-'}] {requirement.get('title')}"
            f"（{requirement.get('id')}）",
        )
    return "\n".join(lines)


def _render_result_template(
    template: str,
    *,
    output_json: dict[str, Any],
    result_context: dict[str, Any],
) -> str:
    created_requirements = [
        item for item in result_context.get("created_requirements") or [] if isinstance(item, dict)
    ]
    summary = _json_text(output_json.get("summary") or compact_preview_value(output_json))
    dingtalk_markdown = _json_text(
        output_json.get("dingtalk_markdown")
        or output_json.get("markdown")
        or output_json.get("document_content")
        or summary,
    )
    replacements = {
        "created_requirement_ids": ", ".join(
            str(requirement.get("id")) for requirement in created_requirements
        ),
        "dingtalk_markdown": dingtalk_markdown,
        "requirements_markdown": _requirements_markdown(created_requirements),
        "result_json": json.dumps(output_json, ensure_ascii=False, sort_keys=True),
        "result_summary": summary,
    }
    for key, value in output_json.items():
        if isinstance(value, str | int | float | bool):
            replacements.setdefault(str(key), str(value))
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    if rendered.strip() == "{{dingtalk_markdown}}":
        return dingtalk_markdown
    return rendered.strip() or dingtalk_markdown


def _sync_dingtalk_document(
    *,
    action: dict[str, Any],
    current_store: Any,
    output_json: dict[str, Any],
    result_context: dict[str, Any],
    scheduled_job_id: str | None,
    scheduled_job_run_id: str | None,
    user: dict[str, Any] | None,
) -> dict[str, Any]:
    if user is None:
        raise api_error(403, "PERMISSION_DENIED", "User context is required")
    from app.services.plugin_invocation_runtime import dingtalk_document_id_from_url
    from app.services.plugins import invoke_plugin_action_response

    document_id = str(dingtalk_document_id_from_url(action["document_id"]))
    content = _render_result_template(
        str(action.get("content_template") or "{{dingtalk_markdown}}"),
        output_json=output_json,
        result_context=result_context,
    )
    invocation_log = invoke_plugin_action_response(
        action_id=str(action["plugin_action_id"]),
        connection_id=action.get("plugin_connection_id"),
        current_store=current_store,
        input_payload={
            "content": content,
            "document_id": document_id,
            "format": "markdown",
            "markdown": content,
            "mode": action.get("write_mode") or "append",
        },
        raise_on_failed=True,
        scheduled_job_id=scheduled_job_id,
        scheduled_job_run_id=scheduled_job_run_id,
        trigger_type="scheduled_job_result_action",
        user=user,
    )
    response_summary = invocation_log.get("response_summary") or {}
    write_preview = result_write_preview(
        response_summary if isinstance(response_summary, dict) else {},
        {
            "content_template": content,
            "document_id": document_id,
            "write_mode": action.get("write_mode") or "append",
            "write_target": "dingtalk_document",
        },
    )
    return {
        "document_id": document_id,
        "plugin_action_id": action["plugin_action_id"],
        "plugin_connection_id": action.get("plugin_connection_id"),
        "plugin_invocation_log_id": invocation_log.get("id"),
        "records_imported": 1,
        "sample_records": [compact_preview_value(content)],
        "status": invocation_log.get("status"),
        "write_mode": action.get("write_mode") or "append",
        "write_preview": write_preview,
    }


def _notification_body(output_json: dict[str, Any]) -> str:
    summary = output_json.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    return str(compact_preview_value(output_json))
