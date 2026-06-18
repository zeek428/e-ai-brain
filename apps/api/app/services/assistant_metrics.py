from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

ASSISTANT_DRAFT_STATUSES = ("pending", "confirmed", "cancelled", "expired", "failed")
KNOWLEDGE_REFERENCE_TYPES = {
    "knowledge_chunk",
    "knowledge_document",
    "knowledge_folder",
    "knowledge_space",
}


def assistant_metrics_response(current_store: Any, *, user: dict[str, Any]) -> dict[str, Any]:
    user_id = str(user["id"])
    drafts, runs, messages, scheduled_job_runs = _assistant_metric_rows(
        current_store,
        user_id=user_id,
    )
    user_draft_ids = {str(draft["id"]) for draft in drafts if draft.get("id") is not None}
    runs = [run for run in runs if str(run.get("draft_id")) in user_draft_ids]
    messages = [message for message in messages if str(message.get("user_id")) == user_id]
    scheduled_job_runs = _filter_scheduled_job_runs_for_assistant_scope(
        scheduled_job_runs,
        action_runs=runs,
        messages=messages,
    )

    draft_status_counts = _status_counts(drafts, ASSISTANT_DRAFT_STATUSES)
    run_succeeded_count = sum(1 for run in runs if run.get("status") == "succeeded")
    run_failed_count = sum(1 for run in runs if run.get("status") == "failed")
    scheduled_job_run_succeeded_count = sum(
        1 for run in scheduled_job_runs if run.get("status") == "succeeded"
    )
    scheduled_job_run_failed_count = sum(
        1 for run in scheduled_job_runs if run.get("status") == "failed"
    )
    repaired_failed_run_count = _repaired_failed_run_count(scheduled_job_runs)
    draft_total = len(drafts)
    action_run_total = len(runs)
    scheduled_job_run_total = len(scheduled_job_runs)
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
    knowledge_request_count, knowledge_hit_count = _knowledge_reference_hit_stats(messages)

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
            "draft_expired_count": draft_status_counts["expired"],
            "draft_failed_count": draft_status_counts["failed"],
            "draft_pending_count": draft_status_counts["pending"],
            "draft_resolution_rate": _rate(
                draft_status_counts["confirmed"]
                + draft_status_counts["cancelled"]
                + draft_status_counts["expired"]
                + draft_status_counts["failed"],
                draft_total,
            ),
            "draft_total": draft_total,
            "draft_user_modified_count": draft_user_modified_count,
            "draft_user_modified_rate": _rate(draft_user_modified_count, draft_total),
            "failed_run_repair_rate": _rate(
                repaired_failed_run_count,
                scheduled_job_run_failed_count,
            ),
            "failed_run_repaired_count": repaired_failed_run_count,
            "failed_run_total": scheduled_job_run_failed_count,
            "knowledge_reference_count": sum(
                1
                for reference in references
                if reference.get("type") in KNOWLEDGE_REFERENCE_TYPES
            ),
            "knowledge_reference_hit_count": knowledge_hit_count,
            "knowledge_reference_hit_rate": _rate(knowledge_hit_count, knowledge_request_count),
            "knowledge_reference_request_count": knowledge_request_count,
            "message_total": len(messages),
            "reference_total": len(references),
            "reference_usage_rate": _rate(referenced_user_message_count, len(user_messages)),
            "referenced_user_message_count": referenced_user_message_count,
            "scheduled_job_run_failed_count": scheduled_job_run_failed_count,
            "scheduled_job_run_succeeded_count": scheduled_job_run_succeeded_count,
            "scheduled_job_run_success_rate": _rate(
                scheduled_job_run_succeeded_count,
                scheduled_job_run_total,
            ),
            "scheduled_job_run_total": scheduled_job_run_total,
            "user_message_total": len(user_messages),
        },
    }


def _assistant_metric_rows(
    current_store: Any,
    *,
    user_id: str,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    repository = getattr(current_store, "repository", None)
    if repository is not None:
        drafts = _repository_user_drafts(repository, user_id=user_id)
        payload = _repository_assistant_chat(repository)
        runs = _dict_values(payload.get("assistant_action_runs", {}))
        messages = _dict_values(payload.get("assistant_messages", {}))
        if not messages:
            messages = _dict_values(getattr(current_store, "assistant_messages", {}))
        scheduled_job_runs = _repository_scheduled_job_runs(repository)
        if not scheduled_job_runs:
            scheduled_job_runs = _dict_values(getattr(current_store, "scheduled_job_runs", {}))
        return drafts, runs, messages, scheduled_job_runs
    drafts = [
        dict(draft)
        for draft in _dict_values(getattr(current_store, "assistant_action_drafts", {}))
        if _record_user_id(draft) == user_id
    ]
    runs = _dict_values(getattr(current_store, "assistant_action_runs", {}))
    messages = _dict_values(getattr(current_store, "assistant_messages", {}))
    scheduled_job_runs = _dict_values(getattr(current_store, "scheduled_job_runs", {}))
    return drafts, runs, messages, scheduled_job_runs


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


def _repository_scheduled_job_runs(repository: Any) -> list[dict[str, Any]]:
    list_runs = getattr(repository, "list_scheduled_job_runs", None)
    if not callable(list_runs):
        return []
    return [dict(run) for run in list_runs() if isinstance(run, dict)]


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
        status = _effective_draft_status(record)
        if status in counts:
            counts[status] += 1
    return counts


def _drafts_by_action(drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    action_counts: dict[str, dict[str, int | str]] = defaultdict(
        lambda: {
            "cancelled_count": 0,
            "confirmed_count": 0,
            "expired_count": 0,
            "failed_count": 0,
            "pending_count": 0,
            "total": 0,
        }
    )
    for draft in drafts:
        action = str(draft.get("action") or "unknown")
        row = action_counts[action]
        row["total"] = int(row["total"]) + 1
        status = _effective_draft_status(draft)
        status_key = f"{status}_count"
        if status_key in row:
            row[status_key] = int(row[status_key]) + 1
    return [
        {"action": action, **dict(counts)}
        for action, counts in sorted(action_counts.items(), key=lambda item: item[0])
    ]


def _filter_scheduled_job_runs_for_assistant_scope(
    scheduled_job_runs: list[dict[str, Any]],
    *,
    action_runs: list[dict[str, Any]],
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    scheduled_job_ids = {
        str(run.get("result_id") or (run.get("result") or {}).get("id"))
        for run in action_runs
        if run.get("result_type") == "scheduled_job"
        and (run.get("result_id") or (run.get("result") or {}).get("id"))
    }
    referenced_run_ids: set[str] = set()
    for message in messages:
        for reference in _message_references(message):
            reference_id = str(reference.get("id") or "").strip()
            if not reference_id:
                continue
            if reference.get("type") == "scheduled_job":
                scheduled_job_ids.add(reference_id)
            elif reference.get("type") == "scheduled_job_run":
                referenced_run_ids.add(reference_id)
    if not scheduled_job_ids and not referenced_run_ids:
        return []
    scoped_runs = []
    for run in scheduled_job_runs:
        run_id = str(run.get("id") or "")
        source_run_id = str(run.get("source_run_id") or "")
        scheduled_job_id = str(run.get("scheduled_job_id") or "")
        if (
            scheduled_job_id in scheduled_job_ids
            or run_id in referenced_run_ids
            or source_run_id in referenced_run_ids
        ):
            scoped_runs.append(run)
    return scoped_runs


def _repaired_failed_run_count(scheduled_job_runs: list[dict[str, Any]]) -> int:
    successful_rerun_source_ids = {
        str(run.get("source_run_id"))
        for run in scheduled_job_runs
        if run.get("status") == "succeeded" and run.get("source_run_id")
    }
    return sum(
        1
        for run in scheduled_job_runs
        if run.get("status") == "failed" and str(run.get("id")) in successful_rerun_source_ids
    )


def _knowledge_reference_hit_stats(messages: list[dict[str, Any]]) -> tuple[int, int]:
    requested_by_conversation: dict[str, set[str]] = defaultdict(set)
    answered_by_conversation: dict[str, set[str]] = defaultdict(set)
    for message in messages:
        conversation_id = str(message.get("conversation_id") or "")
        knowledge_keys = {
            _reference_key(reference)
            for reference in _message_references(message)
            if reference.get("type") in KNOWLEDGE_REFERENCE_TYPES
        }
        knowledge_keys.discard("")
        if not knowledge_keys:
            continue
        if message.get("role") == "user":
            requested_by_conversation[conversation_id].update(knowledge_keys)
        elif message.get("role") == "assistant":
            answered_by_conversation[conversation_id].update(knowledge_keys)
    requested_count = sum(len(items) for items in requested_by_conversation.values())
    hit_count = sum(
        len(items & answered_by_conversation.get(conversation_id, set()))
        for conversation_id, items in requested_by_conversation.items()
    )
    return requested_count, hit_count


def _reference_key(reference: dict[str, Any]) -> str:
    reference_type = str(reference.get("type") or "").strip()
    reference_id = str(reference.get("id") or "").strip()
    if not reference_type or not reference_id:
        return ""
    return f"{reference_type}:{reference_id}"


def _message_references(message: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = message.get("metadata_json") or {}
    references = message.get("references") or metadata.get("references") or []
    if not isinstance(references, list):
        return []
    return [dict(reference) for reference in references if isinstance(reference, dict)]


def _draft_was_user_modified(draft: dict[str, Any]) -> bool:
    metadata = draft.get("metadata_json") or {}
    return metadata.get("user_modified") is True or bool(metadata.get("modified_fields"))


def _effective_draft_status(draft: dict[str, Any]) -> str:
    status = str(draft.get("status") or "").strip()
    if status == "pending" and _draft_expires_at(draft) <= datetime.now(UTC):
        return "expired"
    return status


def _draft_expires_at(draft: dict[str, Any]) -> datetime:
    metadata = draft.get("metadata_json") if isinstance(draft.get("metadata_json"), dict) else {}
    value = draft.get("expires_at") or metadata.get("expires_at")
    if not value:
        return datetime.max.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.max.replace(tzinfo=UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 3)
