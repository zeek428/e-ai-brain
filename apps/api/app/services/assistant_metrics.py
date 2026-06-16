from __future__ import annotations

from collections import defaultdict
from typing import Any

ASSISTANT_DRAFT_STATUSES = ("pending", "confirmed", "cancelled", "failed")


def assistant_metrics_response(current_store: Any, *, user: dict[str, Any]) -> dict[str, Any]:
    user_id = str(user["id"])
    drafts, runs, messages = _assistant_metric_rows(current_store, user_id=user_id)
    user_draft_ids = {str(draft["id"]) for draft in drafts if draft.get("id") is not None}
    runs = [run for run in runs if str(run.get("draft_id")) in user_draft_ids]
    messages = [message for message in messages if str(message.get("user_id")) == user_id]

    draft_status_counts = _status_counts(drafts, ASSISTANT_DRAFT_STATUSES)
    run_succeeded_count = sum(1 for run in runs if run.get("status") == "succeeded")
    run_failed_count = sum(1 for run in runs if run.get("status") == "failed")
    draft_total = len(drafts)
    action_run_total = len(runs)
    user_messages = [message for message in messages if message.get("role") == "user"]
    referenced_user_message_count = sum(
        1 for message in user_messages if _message_references(message)
    )
    references = [
        reference
        for message in messages
        for reference in _message_references(message)
    ]
    draft_user_modified_count = sum(1 for draft in drafts if _draft_was_user_modified(draft))

    return {
        "drafts_by_action": _drafts_by_action(drafts),
        "summary": {
            "action_run_failed_count": run_failed_count,
            "action_run_succeeded_count": run_succeeded_count,
            "action_run_success_rate": _rate(run_succeeded_count, action_run_total),
            "action_run_total": action_run_total,
            "draft_adoption_rate": _rate(draft_status_counts["confirmed"], draft_total),
            "draft_cancelled_count": draft_status_counts["cancelled"],
            "draft_confirmed_count": draft_status_counts["confirmed"],
            "draft_failed_count": draft_status_counts["failed"],
            "draft_pending_count": draft_status_counts["pending"],
            "draft_resolution_rate": _rate(
                draft_status_counts["confirmed"]
                + draft_status_counts["cancelled"]
                + draft_status_counts["failed"],
                draft_total,
            ),
            "draft_total": draft_total,
            "draft_user_modified_count": draft_user_modified_count,
            "draft_user_modified_rate": _rate(draft_user_modified_count, draft_total),
            "knowledge_reference_count": sum(
                1
                for reference in references
                if reference.get("type")
                in {"knowledge_chunk", "knowledge_document", "knowledge_space"}
            ),
            "message_total": len(messages),
            "reference_total": len(references),
            "reference_usage_rate": _rate(referenced_user_message_count, len(user_messages)),
            "referenced_user_message_count": referenced_user_message_count,
            "user_message_total": len(user_messages),
        },
    }


def _assistant_metric_rows(
    current_store: Any,
    *,
    user_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    repository = getattr(current_store, "repository", None)
    if repository is not None:
        drafts = _repository_user_drafts(repository, user_id=user_id)
        payload = _repository_assistant_chat(repository)
        runs = _dict_values(payload.get("assistant_action_runs", {}))
        messages = _dict_values(payload.get("assistant_messages", {}))
        if not messages:
            messages = _dict_values(getattr(current_store, "assistant_messages", {}))
        return drafts, runs, messages
    drafts = [
        dict(draft)
        for draft in _dict_values(getattr(current_store, "assistant_action_drafts", {}))
        if _record_user_id(draft) == user_id
    ]
    runs = _dict_values(getattr(current_store, "assistant_action_runs", {}))
    messages = _dict_values(getattr(current_store, "assistant_messages", {}))
    return drafts, runs, messages


def _repository_user_drafts(repository: Any, *, user_id: str) -> list[dict[str, Any]]:
    list_drafts = getattr(repository, "list_assistant_action_drafts", None)
    if callable(list_drafts):
        return [dict(draft) for draft in list_drafts(user_id=user_id)]
    assistant_chat_payload = _repository_assistant_chat(repository)
    return [
        dict(draft)
        for draft in _dict_values(assistant_chat_payload.get("assistant_action_drafts", {}))
        if _record_user_id(draft) == user_id
    ]


def _repository_assistant_chat(repository: Any) -> dict[str, Any]:
    load_chat = getattr(repository, "load_assistant_chat", None)
    if not callable(load_chat):
        return {}
    return load_chat() or {}


def _dict_values(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [dict(item) for item in value.values() if isinstance(item, dict)]
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    return []


def _record_user_id(record: dict[str, Any]) -> str | None:
    user_id = record.get("user_id") or record.get("created_by")
    return str(user_id) if user_id is not None else None


def _status_counts(records: list[dict[str, Any]], statuses: tuple[str, ...]) -> dict[str, int]:
    counts = {status: 0 for status in statuses}
    for record in records:
        status = str(record.get("status") or "").strip()
        if status in counts:
            counts[status] += 1
    return counts


def _drafts_by_action(drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    action_counts: dict[str, dict[str, int | str]] = defaultdict(
        lambda: {
            "cancelled_count": 0,
            "confirmed_count": 0,
            "failed_count": 0,
            "pending_count": 0,
            "total": 0,
        }
    )
    for draft in drafts:
        action = str(draft.get("action") or "unknown")
        row = action_counts[action]
        row["total"] = int(row["total"]) + 1
        status = str(draft.get("status") or "").strip()
        status_key = f"{status}_count"
        if status_key in row:
            row[status_key] = int(row[status_key]) + 1
    return [
        {"action": action, **dict(counts)}
        for action, counts in sorted(action_counts.items(), key=lambda item: item[0])
    ]


def _message_references(message: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = message.get("metadata_json") or {}
    references = message.get("references") or metadata.get("references") or []
    if not isinstance(references, list):
        return []
    return [dict(reference) for reference in references if isinstance(reference, dict)]


def _draft_was_user_modified(draft: dict[str, Any]) -> bool:
    metadata = draft.get("metadata_json") or {}
    return metadata.get("user_modified") is True or bool(metadata.get("modified_fields"))


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 3)
