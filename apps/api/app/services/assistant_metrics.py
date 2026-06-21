from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

ASSISTANT_DRAFT_STATUSES = ("pending", "confirmed", "cancelled", "expired", "failed")
ASSISTANT_CHAT_RUN_STATUSES = ("running", "succeeded", "cancelled", "failed")
ASSISTANT_CHAT_RUN_MODEL_FAILURE_ERROR_CODES = {
    "ASSISTANT_CHAT_FAILED",
    "MODEL_GATEWAY_CONFIG_INVALID",
    "MODEL_GATEWAY_FAILED",
}
KNOWLEDGE_REFERENCE_TYPES = {
    "knowledge_chunk",
    "knowledge_document",
    "knowledge_folder",
    "knowledge_space",
}
ASSISTANT_METRIC_DETAIL_LABELS = {
    "action_run_failed_count": "动作执行失败",
    "action_run_succeeded_count": "动作执行成功",
    "action_run_total": "动作执行",
    "chat_run_cancelled_count": "AI 生成已取消",
    "chat_run_failed_count": "AI 生成失败",
    "chat_run_model_failed_count": "模型网关失败",
    "chat_run_running_count": "AI 生成中",
    "chat_run_succeeded_count": "AI 生成成功",
    "chat_run_total": "AI 生成",
    "draft_cancelled_count": "已取消草案",
    "draft_confirmed_count": "已应用草案",
    "draft_deeplink_viewed_count": "深链打开草案",
    "draft_detail_viewed_count": "查看详情草案",
    "draft_expired_count": "已过期草案",
    "draft_failed_count": "失败草案",
    "draft_inferred_viewed_count": "历史推断查看草案",
    "draft_pending_count": "待确认草案",
    "draft_total": "草案生成",
    "draft_tracked_viewed_count": "埋点查看草案",
    "draft_user_modified_count": "用户修改草案",
    "draft_viewed_count": "查看草案",
    "failed_run_repaired_count": "已修复失败运行",
    "failed_run_total": "失败运行",
    "knowledge_reference_count": "知识引用",
    "knowledge_reference_hit_count": "知识引用命中",
    "knowledge_reference_request_count": "知识引用请求",
    "message_total": "助手消息",
    "reference_total": "显式引用",
    "referenced_user_message_count": "带引用用户消息",
    "scheduled_job_run_failed_count": "定时作业运行失败",
    "scheduled_job_run_succeeded_count": "定时作业运行成功",
    "scheduled_job_run_total": "定时作业运行",
    "user_message_total": "用户消息",
}


def assistant_metrics_response(
    current_store: Any,
    *,
    user: dict[str, Any],
    window_days: int | None = None,
) -> dict[str, Any]:
    scoped_rows = _assistant_scoped_metric_rows(
        current_store,
        user=user,
        window_days=window_days,
    )
    drafts = scoped_rows["drafts"]
    runs = scoped_rows["runs"]
    messages = scoped_rows["messages"]
    scheduled_job_runs = scoped_rows["scheduled_job_runs"]
    chat_runs = scoped_rows["chat_runs"]
    scheduled_job_run_attribution = scoped_rows["scheduled_job_run_attribution"]

    draft_status_counts = _status_counts(drafts, ASSISTANT_DRAFT_STATUSES)
    chat_run_status_counts = _field_status_counts(chat_runs, ASSISTANT_CHAT_RUN_STATUSES)
    run_succeeded_count = sum(1 for run in runs if run.get("status") == "succeeded")
    run_failed_count = sum(1 for run in runs if run.get("status") == "failed")
    chat_run_total = len(chat_runs)
    chat_run_model_failed_count = sum(1 for run in chat_runs if _chat_run_model_failed(run))
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
    draft_tracked_viewed_count = sum(1 for draft in drafts if _draft_was_viewed_by_tracking(draft))
    draft_viewed_count = sum(1 for draft in drafts if _draft_was_effectively_viewed(draft))
    draft_inferred_viewed_count = max(draft_viewed_count - draft_tracked_viewed_count, 0)
    draft_detail_viewed_count = sum(1 for draft in drafts if _draft_was_detail_viewed(draft))
    draft_deeplink_viewed_count = sum(1 for draft in drafts if _draft_was_deeplink_viewed(draft))
    knowledge_request_count, knowledge_hit_count = _knowledge_reference_hit_stats(messages)
    continued_followup_or_repair_count = _continued_followup_or_repair_count(user_messages)

    return {
        "drafts_by_action": _drafts_by_action(drafts),
        "funnel": {
            "stages": _assistant_effectiveness_funnel_stages(
                draft_confirmed_count=draft_status_counts["confirmed"],
                draft_generated_count=draft_total,
                draft_deeplink_viewed_count=draft_deeplink_viewed_count,
                draft_detail_viewed_count=draft_detail_viewed_count,
                draft_modified_count=draft_user_modified_count,
                draft_viewed_count=draft_viewed_count,
                intent_triggered_count=len(user_messages),
                run_succeeded_count=scheduled_job_run_succeeded_count,
                continued_followup_or_repair_count=continued_followup_or_repair_count,
            )
        },
        "summary": {
            "action_run_failed_count": run_failed_count,
            "action_run_succeeded_count": run_succeeded_count,
            "action_run_success_rate": _rate(run_succeeded_count, action_run_total),
            "action_run_total": action_run_total,
            "chat_run_average_duration_ms": _chat_run_average_duration_ms(chat_runs),
            "chat_run_cancel_rate": _rate(chat_run_status_counts["cancelled"], chat_run_total),
            "chat_run_cancelled_count": chat_run_status_counts["cancelled"],
            "chat_run_failed_count": chat_run_status_counts["failed"],
            "chat_run_failure_rate": _rate(chat_run_status_counts["failed"], chat_run_total),
            "chat_run_model_failed_count": chat_run_model_failed_count,
            "chat_run_model_failure_rate": _rate(chat_run_model_failed_count, chat_run_total),
            "chat_run_running_count": chat_run_status_counts["running"],
            "chat_run_succeeded_count": chat_run_status_counts["succeeded"],
            "chat_run_success_rate": _rate(chat_run_status_counts["succeeded"], chat_run_total),
            "chat_run_total": chat_run_total,
            "draft_adoption_rate": _rate(draft_status_counts["confirmed"], draft_total),
            "draft_cancelled_count": draft_status_counts["cancelled"],
            "draft_confirmed_count": draft_status_counts["confirmed"],
            "draft_expired_count": draft_status_counts["expired"],
            "draft_failed_count": draft_status_counts["failed"],
            "draft_inferred_viewed_count": draft_inferred_viewed_count,
            "draft_pending_count": draft_status_counts["pending"],
            "draft_resolution_rate": _rate(
                draft_status_counts["confirmed"]
                + draft_status_counts["cancelled"]
                + draft_status_counts["expired"]
                + draft_status_counts["failed"],
                draft_total,
            ),
            "draft_total": draft_total,
            "draft_deeplink_viewed_count": draft_deeplink_viewed_count,
            "draft_detail_viewed_count": draft_detail_viewed_count,
            "draft_user_modified_count": draft_user_modified_count,
            "draft_user_modified_rate": _rate(draft_user_modified_count, draft_total),
            "draft_tracked_viewed_count": draft_tracked_viewed_count,
            "draft_viewed_count": draft_viewed_count,
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
        "window": {
            "days": window_days,
            "label": f"最近 {window_days} 天" if window_days else "全部时间",
        },
        "instrumentation": _assistant_metrics_instrumentation(
            draft_inferred_viewed_count=draft_inferred_viewed_count,
            draft_tracked_viewed_count=draft_tracked_viewed_count,
        ),
        "scheduled_job_run_attribution": {
            "items": [
                {
                    "count": int(scheduled_job_run_attribution.get("assistant_triggered", 0)),
                    "key": "assistant_triggered",
                    "label": "助手触发",
                },
                {
                    "count": int(scheduled_job_run_attribution.get("explicit_reference", 0)),
                    "key": "explicit_reference",
                    "label": "显式引用",
                },
                {
                    "count": int(scheduled_job_run_attribution.get("rerun_chain", 0)),
                    "key": "rerun_chain",
                    "label": "复跑链",
                },
            ],
            "total": scheduled_job_run_total,
        },
    }


def assistant_metric_details_response(
    current_store: Any,
    *,
    limit: int = 50,
    metric: str,
    user: dict[str, Any],
    window_days: int | None = None,
) -> dict[str, Any]:
    normalized_metric = str(metric or "").strip()
    if not normalized_metric:
        normalized_metric = "draft_total"
    scoped_rows = _assistant_scoped_metric_rows(
        current_store,
        user=user,
        window_days=window_days,
    )
    normalized_limit = min(max(int(limit or 50), 1), 100)
    items, total = _assistant_metric_detail_records(
        scoped_rows,
        limit=normalized_limit,
        metric=normalized_metric,
    )
    return {
        "items": [
            _assistant_metric_detail_item(item)
            for item in items
        ],
        "metric": normalized_metric,
        "title": ASSISTANT_METRIC_DETAIL_LABELS.get(normalized_metric, normalized_metric),
        "total": total,
        "window": {
            "days": window_days,
            "label": f"最近 {window_days} 天" if window_days else "全部时间",
        },
    }


def _assistant_scoped_metric_rows(
    current_store: Any,
    *,
    user: dict[str, Any],
    window_days: int | None,
) -> dict[str, Any]:
    user_id = str(user["id"])
    drafts, runs, messages, scheduled_job_runs, chat_runs = _assistant_metric_rows(
        current_store,
        user_id=user_id,
    )
    cutoff = _metrics_cutoff(window_days)
    user_draft_ids = {str(draft["id"]) for draft in drafts if draft.get("id") is not None}
    runs = [run for run in runs if str(run.get("draft_id")) in user_draft_ids]
    messages = [message for message in messages if str(message.get("user_id")) == user_id]
    chat_runs = [run for run in chat_runs if str(run.get("user_id")) == user_id]
    if cutoff is not None:
        drafts = _filter_records_since(drafts, cutoff, ("created_at", "updated_at"))
        runs = _filter_records_since(runs, cutoff, ("started_at", "created_at", "updated_at"))
        messages = _filter_records_since(messages, cutoff, ("created_at", "updated_at"))
        chat_runs = _filter_records_since(
            chat_runs,
            cutoff,
            ("started_at", "created_at", "updated_at"),
        )
    repository_scoped_runs = _repository_assistant_scoped_scheduled_job_runs(
        getattr(current_store, "repository", None),
        action_runs=runs,
        cutoff=cutoff,
        messages=messages,
    )
    if repository_scoped_runs is not None:
        scheduled_job_runs = repository_scoped_runs
    elif cutoff is not None:
        scheduled_job_runs = _filter_records_since(
            scheduled_job_runs,
            cutoff,
            ("started_at", "created_at", "updated_at"),
        )
    (
        scheduled_job_runs,
        scheduled_job_run_attribution,
    ) = _filter_scheduled_job_runs_for_assistant_scope(
        scheduled_job_runs,
        action_runs=runs,
        messages=messages,
    )
    return {
        "chat_runs": _sort_metric_records(chat_runs),
        "drafts": _sort_metric_records(drafts),
        "messages": _sort_metric_records(messages),
        "runs": _sort_metric_records(runs),
        "scheduled_job_run_attribution": scheduled_job_run_attribution,
        "scheduled_job_runs": _sort_metric_records(scheduled_job_runs),
    }


def _assistant_metric_detail_records(
    scoped_rows: dict[str, Any],
    *,
    limit: int,
    metric: str,
) -> tuple[list[dict[str, Any]], int]:
    drafts = scoped_rows["drafts"]
    runs = scoped_rows["runs"]
    messages = scoped_rows["messages"]
    scheduled_job_runs = scoped_rows["scheduled_job_runs"]
    chat_runs = scoped_rows["chat_runs"]
    if metric in {"draft_total", "draft_adoption_rate", "draft_resolution_rate"}:
        return _limited_metric_records(drafts, kind="draft", limit=limit)
    if metric.startswith("draft_") and metric.endswith("_count"):
        if metric == "draft_user_modified_count":
            return _limited_metric_records(
                drafts,
                kind="draft",
                limit=limit,
                predicate=_draft_was_user_modified,
            )
        if metric == "draft_viewed_count":
            return _limited_metric_records(
                drafts,
                kind="draft",
                limit=limit,
                predicate=_draft_was_effectively_viewed,
            )
        if metric == "draft_tracked_viewed_count":
            return _limited_metric_records(
                drafts,
                kind="draft",
                limit=limit,
                predicate=_draft_was_viewed_by_tracking,
            )
        if metric == "draft_inferred_viewed_count":
            return _limited_metric_records(
                drafts,
                kind="draft",
                limit=limit,
                predicate=lambda draft: (
                    _draft_was_effectively_viewed(draft)
                    and not _draft_was_viewed_by_tracking(draft)
                ),
            )
        if metric == "draft_detail_viewed_count":
            return _limited_metric_records(
                drafts,
                kind="draft",
                limit=limit,
                predicate=_draft_was_detail_viewed,
            )
        if metric == "draft_deeplink_viewed_count":
            return _limited_metric_records(
                drafts,
                kind="draft",
                limit=limit,
                predicate=_draft_was_deeplink_viewed,
            )
        status = metric.removeprefix("draft_").removesuffix("_count")
        return _limited_metric_records(
            drafts,
            kind="draft",
            limit=limit,
            predicate=lambda draft: _effective_draft_status(draft) == status,
        )
    if metric in {"action_run_total", "action_run_success_rate"}:
        return _limited_metric_records(runs, kind="action_run", limit=limit)
    if metric == "action_run_succeeded_count":
        return _limited_metric_records(
            runs,
            kind="action_run",
            limit=limit,
            predicate=lambda run: run.get("status") == "succeeded",
        )
    if metric == "action_run_failed_count":
        return _limited_metric_records(
            runs,
            kind="action_run",
            limit=limit,
            predicate=lambda run: run.get("status") == "failed",
        )
    if metric in {
        "chat_run_total",
        "chat_run_success_rate",
        "chat_run_failure_rate",
        "chat_run_cancel_rate",
        "chat_run_model_failure_rate",
    }:
        return _limited_metric_records(chat_runs, kind="chat_run", limit=limit)
    if metric == "chat_run_model_failed_count":
        return _limited_metric_records(
            chat_runs,
            kind="chat_run",
            limit=limit,
            predicate=_chat_run_model_failed,
        )
    if metric.startswith("chat_run_") and metric.endswith("_count"):
        status = metric.removeprefix("chat_run_").removesuffix("_count")
        return _limited_metric_records(
            chat_runs,
            kind="chat_run",
            limit=limit,
            predicate=lambda run: str(run.get("status") or "") == status,
        )
    if metric in {
        "scheduled_job_run_total",
        "scheduled_job_run_success_rate",
        "failed_run_repair_rate",
    }:
        return _limited_metric_records(
            scheduled_job_runs,
            kind="scheduled_job_run",
            limit=limit,
        )
    if metric == "scheduled_job_run_succeeded_count":
        return _limited_metric_records(
            scheduled_job_runs,
            kind="scheduled_job_run",
            limit=limit,
            predicate=lambda run: run.get("status") == "succeeded",
        )
    if metric in {"scheduled_job_run_failed_count", "failed_run_total"}:
        return _limited_metric_records(
            scheduled_job_runs,
            kind="scheduled_job_run",
            limit=limit,
            predicate=lambda run: run.get("status") == "failed",
        )
    if metric == "failed_run_repaired_count":
        repaired_ids = _repaired_failed_run_ids(scheduled_job_runs)
        return _limited_metric_records(
            scheduled_job_runs,
            kind="scheduled_job_run",
            limit=limit,
            predicate=lambda run: str(run.get("id")) in repaired_ids,
        )
    if metric in {"message_total", "user_message_total"}:
        return _limited_metric_records(
            messages,
            kind="message",
            limit=limit,
            predicate=lambda message: metric == "message_total" or message.get("role") == "user",
        )
    if metric in {"reference_total", "reference_usage_rate", "referenced_user_message_count"}:
        return _limited_metric_records(
            messages,
            kind="message",
            limit=limit,
            predicate=lambda message: message.get("role") == "user" and bool(_message_references(message)),
        )
    if metric in {
        "knowledge_reference_count",
        "knowledge_reference_hit_count",
        "knowledge_reference_hit_rate",
        "knowledge_reference_request_count",
    }:
        return _limited_knowledge_reference_detail_records(
            messages,
            limit=limit,
            metric=metric,
        )
    return [], 0


def _limited_metric_records(
    records: list[dict[str, Any]],
    *,
    kind: str,
    limit: int,
    predicate: Any | None = None,
) -> tuple[list[dict[str, Any]], int]:
    items: list[dict[str, Any]] = []
    total = 0
    for record in records:
        if predicate is not None and not predicate(record):
            continue
        total += 1
        if len(items) < limit:
            items.append(_with_metric_kind(record, kind))
    return items, total


def _limited_knowledge_reference_detail_records(
    messages: list[dict[str, Any]],
    *,
    limit: int,
    metric: str,
) -> tuple[list[dict[str, Any]], int]:
    items: list[dict[str, Any]] = []
    total = 0
    answered_by_conversation: dict[str, set[str]] = defaultdict(set)
    for message in messages:
        if message.get("role") != "assistant":
            continue
        conversation_id = str(message.get("conversation_id") or "")
        answered_by_conversation[conversation_id].update(
            _reference_key(reference)
            for reference in _message_references(message)
            if reference.get("type") in KNOWLEDGE_REFERENCE_TYPES
        )
    for message in _sort_metric_records(messages):
        conversation_id = str(message.get("conversation_id") or "")
        message_records: list[dict[str, Any]] = []
        for reference in _message_references(message):
            if reference.get("type") not in KNOWLEDGE_REFERENCE_TYPES:
                continue
            if (
                metric in {
                    "knowledge_reference_hit_count",
                    "knowledge_reference_hit_rate",
                    "knowledge_reference_request_count",
                }
                and message.get("role") != "user"
            ):
                continue
            reference_key = _reference_key(reference)
            is_hit = reference_key in answered_by_conversation.get(conversation_id, set())
            if (
                metric in {"knowledge_reference_hit_count", "knowledge_reference_hit_rate"}
                and not is_hit
            ):
                continue
            message_records.append(
                {
                    **message,
                    "id": f"{message.get('id') or 'message'}:{reference_key}",
                    "reference": dict(reference),
                    "status": "hit" if is_hit else "requested",
                }
            )
        message_records.sort(key=lambda item: str(item.get("id") or ""), reverse=True)
        for record in message_records:
            total += 1
            if len(items) < limit:
                items.append(_with_metric_kind(record, "knowledge_reference"))
    return items, total


def _assistant_metric_detail_item(record: dict[str, Any]) -> dict[str, Any]:
    kind = str(record.get("_metric_kind") or "record")
    record_id = str(record.get("id") or "")
    status = str(record.get("status") or _effective_draft_status(record) or "")
    title = _metric_record_title(record, kind=kind)
    item = {
        "action": record.get("action"),
        "created_at": record.get("created_at") or record.get("started_at"),
        "description": _metric_record_description(record, kind=kind),
        "id": record_id,
        "status": status,
        "title": title,
        "type": kind,
        "updated_at": record.get("updated_at") or record.get("finished_at"),
        "url": _metric_record_url(record, kind=kind),
    }
    return {key: value for key, value in item.items() if value not in (None, "")}


def _metric_record_title(record: dict[str, Any], *, kind: str) -> str:
    if kind == "draft":
        return str(record.get("title") or record.get("action") or record.get("id") or "草案")
    if kind == "action_run":
        return str(
            record.get("result_type")
            or record.get("action")
            or record.get("id")
            or "动作运行"
        )
    if kind == "chat_run":
        return str(record.get("client_request_id") or record.get("id") or "AI 生成运行")
    if kind == "scheduled_job_run":
        return str(
            record.get("name")
            or record.get("scheduled_job_id")
            or record.get("id")
            or "定时作业运行"
        )
    if kind == "knowledge_reference":
        reference = record.get("reference") or {}
        if isinstance(reference, dict):
            return str(reference.get("title") or reference.get("id") or "知识引用")
        return "知识引用"
    if kind == "message":
        content = str(record.get("content") or "")
        return content[:48] if content else str(record.get("id") or "消息")
    return str(record.get("title") or record.get("id") or "记录")


def _metric_record_description(record: dict[str, Any], *, kind: str) -> str:
    if kind == "draft":
        return f"{record.get('action') or 'draft'} · {_effective_draft_status(record)}"
    if kind == "action_run":
        return f"{record.get('action') or 'action'} · {record.get('status') or '-'}"
    if kind == "chat_run":
        error = str(record.get("error_code") or record.get("error_message") or "").strip()
        return f"{record.get('status') or '-'}{f' · {error}' if error else ''}"
    if kind == "scheduled_job_run":
        error = str(record.get("error_message") or "").strip()
        return f"{record.get('status') or '-'}{f' · {error}' if error else ''}"
    if kind == "knowledge_reference":
        reference = record.get("reference") or {}
        reference_type = reference.get("type") if isinstance(reference, dict) else None
        return f"{reference_type or 'knowledge'} · {record.get('status') or '-'}"
    if kind == "message":
        return f"{record.get('role') or 'message'} · {len(_message_references(record))} 个引用"
    return str(record.get("status") or "")


def _metric_record_url(record: dict[str, Any], *, kind: str) -> str | None:
    if kind == "draft" and record.get("id"):
        return f"/assistant?draft_id={record['id']}"
    if kind == "chat_run" and record.get("conversation_id"):
        return f"/assistant?conversation_id={record['conversation_id']}"
    if kind == "action_run" and record.get("draft_id"):
        return f"/assistant?draft_id={record['draft_id']}"
    if kind == "scheduled_job_run" and record.get("id"):
        job_id = str(record.get("scheduled_job_id") or "")
        if job_id:
            return f"/tasks/scheduled-jobs?job_id={job_id}&run_id={record['id']}"
        return f"/tasks/scheduled-jobs?run_id={record['id']}"
    if kind in {"knowledge_reference", "message"} and record.get("conversation_id"):
        return f"/assistant?conversation_id={record['conversation_id']}"
    return None


def _with_metric_kind(record: dict[str, Any], kind: str) -> dict[str, Any]:
    return {**record, "_metric_kind": kind}


def _sort_metric_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda item: (
            _parse_datetime(
                item.get("updated_at")
                or item.get("finished_at")
                or item.get("started_at")
                or item.get("created_at")
            )
            or datetime.min.replace(tzinfo=UTC),
            str(item.get("id") or ""),
        ),
        reverse=True,
    )


def _metrics_cutoff(window_days: int | None) -> datetime | None:
    if window_days is None:
        return None
    try:
        days = int(window_days)
    except (TypeError, ValueError):
        return None
    if days <= 0:
        return None
    return datetime.now(UTC) - timedelta(days=days)


def _filter_records_since(
    records: list[dict[str, Any]],
    cutoff: datetime,
    time_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for record in records:
        record_times = [
            parsed
            for parsed in (_parse_datetime(record.get(field)) for field in time_fields)
            if parsed is not None
        ]
        if record_times and max(record_times) >= cutoff:
            filtered.append(record)
    return filtered


def _assistant_metric_rows(
    current_store: Any,
    *,
    user_id: str,
) -> tuple[
    list[dict[str, Any]],
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
        chat_runs = _dict_values(payload.get("assistant_chat_runs", {}))
        messages = _dict_values(payload.get("assistant_messages", {}))
        if not messages:
            messages = _dict_values(getattr(current_store, "assistant_messages", {}))
        scheduled_job_runs: list[dict[str, Any]] = []
        if not callable(getattr(repository, "list_assistant_scoped_scheduled_job_runs", None)):
            scheduled_job_runs = _repository_scheduled_job_runs(repository)
            if not scheduled_job_runs:
                scheduled_job_runs = _dict_values(getattr(current_store, "scheduled_job_runs", {}))
        return drafts, runs, messages, scheduled_job_runs, chat_runs
    drafts = [
        dict(draft)
        for draft in _dict_values(getattr(current_store, "assistant_action_drafts", {}))
        if _record_user_id(draft) == user_id
    ]
    runs = _dict_values(getattr(current_store, "assistant_action_runs", {}))
    messages = _dict_values(getattr(current_store, "assistant_messages", {}))
    scheduled_job_runs = _dict_values(getattr(current_store, "scheduled_job_runs", {}))
    chat_runs = _dict_values(getattr(current_store, "assistant_chat_runs", {}))
    return drafts, runs, messages, scheduled_job_runs, chat_runs


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


def _repository_assistant_scoped_scheduled_job_runs(
    repository: Any,
    *,
    action_runs: list[dict[str, Any]],
    cutoff: datetime | None,
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    list_runs = getattr(repository, "list_assistant_scoped_scheduled_job_runs", None)
    if not callable(list_runs):
        return None
    action_run_ids = [
        str(run.get("id"))
        for run in action_runs
        if run.get("id")
    ]
    action_draft_ids = [
        str(run.get("draft_id"))
        for run in action_runs
        if run.get("draft_id")
    ]
    message_ids = [
        str(message.get("id"))
        for message in messages
        if message.get("id")
    ]
    referenced_run_ids = [
        str(reference.get("id"))
        for message in messages
        for reference in _message_references(message)
        if reference.get("type") == "scheduled_job_run" and reference.get("id")
    ]
    return [
        dict(run)
        for run in list_runs(
            action_draft_ids=action_draft_ids,
            action_run_ids=action_run_ids,
            message_ids=message_ids,
            referenced_run_ids=referenced_run_ids,
            since=cutoff.isoformat() if cutoff is not None else None,
        )
        if isinstance(run, dict)
    ]


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


def _field_status_counts(
    records: list[dict[str, Any]],
    statuses: tuple[str, ...],
) -> dict[str, int]:
    counts = {status: 0 for status in statuses}
    for record in records:
        status = str(record.get("status") or "")
        if status in counts:
            counts[status] += 1
    return counts


def _chat_run_model_failed(run: dict[str, Any]) -> bool:
    if run.get("status") != "failed":
        return False
    error_code = str(run.get("error_code") or "").strip()
    error_message = str(run.get("error_message") or "").lower()
    return (
        error_code in ASSISTANT_CHAT_RUN_MODEL_FAILURE_ERROR_CODES
        or error_code.startswith("MODEL_GATEWAY")
        or "model gateway" in error_message
    )


def _chat_run_average_duration_ms(chat_runs: list[dict[str, Any]]) -> int | None:
    durations: list[int] = []
    for run in chat_runs:
        started_at = _parse_datetime(run.get("started_at") or run.get("created_at"))
        finished_at = _parse_datetime(run.get("finished_at") or run.get("cancelled_at"))
        if started_at is None or finished_at is None:
            continue
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        if duration_ms >= 0:
            durations.append(duration_ms)
    if not durations:
        return None
    return round(sum(durations) / len(durations))


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


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
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    action_run_ids = {
        str(run.get("id"))
        for run in action_runs
        if run.get("id")
    }
    action_draft_ids = {
        str(run.get("draft_id"))
        for run in action_runs
        if run.get("draft_id")
    }
    message_ids = {
        str(message.get("id"))
        for message in messages
        if message.get("id")
    }
    referenced_run_ids: set[str] = set()
    for message in messages:
        for reference in _message_references(message):
            reference_id = str(reference.get("id") or "").strip()
            if not reference_id:
                continue
            if reference.get("type") == "scheduled_job_run":
                referenced_run_ids.add(reference_id)
    if not action_run_ids and not action_draft_ids and not message_ids and not referenced_run_ids:
        return [], {}
    runs_by_id = {
        str(run.get("id") or ""): run
        for run in scheduled_job_runs
        if run.get("id")
    }
    scoped_run_ids: set[str] = set()
    attribution_reasons: dict[str, set[str]] = defaultdict(set)
    for run in scheduled_job_runs:
        run_id = str(run.get("id") or "")
        source_run_id = str(run.get("source_run_id") or "")
        assistant_action_run_id = str(run.get("assistant_action_run_id") or "")
        assistant_action_draft_id = str(run.get("assistant_action_draft_id") or "")
        assistant_source_message_id = str(run.get("assistant_source_message_id") or "")
        if run_id in referenced_run_ids:
            attribution_reasons[run_id].add("explicit_reference")
        if source_run_id in referenced_run_ids:
            attribution_reasons[run_id].add("rerun_chain")
        if (
            assistant_action_run_id in action_run_ids
            or assistant_action_draft_id in action_draft_ids
            or (
                run.get("triggered_by_assistant") is True
                and assistant_source_message_id in message_ids
            )
        ):
            attribution_reasons[run_id].add("assistant_triggered")
        if attribution_reasons.get(run_id):
            scoped_run_ids.add(run_id)
            if source_run_id:
                scoped_run_ids.add(source_run_id)
                attribution_reasons[source_run_id].add("rerun_chain")
    changed = True
    while changed:
        changed = False
        for run in scheduled_job_runs:
            run_id = str(run.get("id") or "")
            source_run_id = str(run.get("source_run_id") or "")
            if run_id in scoped_run_ids:
                continue
            if (
                run.get("trigger_type") == "manual_rerun"
                and source_run_id
                and source_run_id in scoped_run_ids
            ):
                scoped_run_ids.add(run_id)
                attribution_reasons[run_id].add("rerun_chain")
                changed = True
    scoped_runs = [
        runs_by_id[run_id]
        for run_id in scoped_run_ids
        if run_id in runs_by_id
    ]
    return scoped_runs, _scheduled_job_run_attribution_counts(scoped_runs, attribution_reasons)


def _scheduled_job_run_attribution_counts(
    scheduled_job_runs: list[dict[str, Any]],
    attribution_reasons: dict[str, set[str]],
) -> dict[str, int]:
    counts = {
        "assistant_triggered": 0,
        "explicit_reference": 0,
        "rerun_chain": 0,
    }
    for run in scheduled_job_runs:
        reasons = attribution_reasons.get(str(run.get("id") or ""), set())
        if "assistant_triggered" in reasons:
            counts["assistant_triggered"] += 1
        elif "explicit_reference" in reasons:
            counts["explicit_reference"] += 1
        elif "rerun_chain" in reasons:
            counts["rerun_chain"] += 1
    return counts


def _repaired_failed_run_count(scheduled_job_runs: list[dict[str, Any]]) -> int:
    successful_rerun_source_ids = _repaired_failed_run_ids(scheduled_job_runs)
    return sum(
        1
        for run in scheduled_job_runs
        if run.get("status") == "failed" and str(run.get("id")) in successful_rerun_source_ids
    )


def _repaired_failed_run_ids(scheduled_job_runs: list[dict[str, Any]]) -> set[str]:
    successful_rerun_source_ids = {
        str(run.get("source_run_id"))
        for run in scheduled_job_runs
        if run.get("status") == "succeeded"
        and run.get("trigger_type") == "manual_rerun"
        and run.get("source_run_id")
    }
    return {
        str(run.get("id"))
        for run in scheduled_job_runs
        if run.get("status") == "failed" and str(run.get("id")) in successful_rerun_source_ids
    }


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


def _draft_was_viewed_by_tracking(draft: dict[str, Any]) -> bool:
    metadata = draft.get("metadata_json") or {}
    return bool(
        metadata.get("viewed_at")
        or metadata.get("detail_viewed_at")
        or metadata.get("last_viewed_at")
    )


def _draft_was_effectively_viewed(draft: dict[str, Any]) -> bool:
    if _draft_was_viewed_by_tracking(draft):
        return True
    status = _effective_draft_status(draft)
    if status in {"confirmed", "cancelled", "failed"}:
        return True
    return _draft_was_user_modified(draft) or bool(draft.get("result_run_id"))


def _draft_was_detail_viewed(draft: dict[str, Any]) -> bool:
    metadata = draft.get("metadata_json") or {}
    return bool(metadata.get("detail_viewed_at"))


def _draft_was_deeplink_viewed(draft: dict[str, Any]) -> bool:
    metadata = draft.get("metadata_json") or {}
    return bool(metadata.get("deeplink_viewed_at"))


def _continued_followup_or_repair_count(messages: list[dict[str, Any]]) -> int:
    count = 0
    for message in messages:
        content = str(message.get("content") or "")
        references = _message_references(message)
        has_run_reference = any(
            reference.get("type") == "scheduled_job_run" for reference in references
        )
        asks_repair = any(
            keyword in content
            for keyword in (
                "继续追问",
                "为什么这次任务失败",
                "为什么失败",
                "修复草案",
                "重新执行",
                "重跑",
            )
        )
        if has_run_reference or asks_repair:
            count += 1
    return count


def _assistant_metrics_instrumentation(
    *,
    draft_inferred_viewed_count: int,
    draft_tracked_viewed_count: int,
) -> dict[str, Any]:
    return {
        "notes": [
            {
                "code": "DRAFT_VIEW_TRACKING_ROLLOUT",
                "level": "info" if draft_tracked_viewed_count else "warning",
                "message": (
                    "草案查看埋点只统计上线后的显式查看；历史已确认、已取消、失败、已修改或已产生执行结果的草案"
                    "会计入有效查看，并在历史推断查看中单独列示。"
                ),
            }
        ],
        "view_metrics": {
            "effective_viewed_count": draft_tracked_viewed_count + draft_inferred_viewed_count,
            "inferred_legacy_count": draft_inferred_viewed_count,
            "tracked_count": draft_tracked_viewed_count,
        },
    }


def _assistant_effectiveness_funnel_stages(
    *,
    intent_triggered_count: int,
    draft_generated_count: int,
    draft_viewed_count: int,
    draft_detail_viewed_count: int,
    draft_deeplink_viewed_count: int,
    draft_modified_count: int,
    draft_confirmed_count: int,
    run_succeeded_count: int,
    continued_followup_or_repair_count: int,
) -> list[dict[str, Any]]:
    return [
        {
            "count": intent_triggered_count,
            "key": "intent_triggered",
            "label": "触发意图",
            "sort_order": 10,
        },
        {
            "count": draft_generated_count,
            "key": "draft_generated",
            "label": "生成草案",
            "sort_order": 20,
        },
        {
            "count": draft_viewed_count,
            "key": "draft_viewed",
            "label": "查看草案",
            "sort_order": 30,
        },
        {
            "count": draft_detail_viewed_count,
            "key": "draft_detail_viewed",
            "label": "查看详情",
            "sort_order": 31,
        },
        {
            "count": draft_deeplink_viewed_count,
            "key": "draft_deeplink_viewed",
            "label": "深链打开",
            "sort_order": 32,
        },
        {
            "count": draft_modified_count,
            "key": "draft_modified",
            "label": "修改字段",
            "sort_order": 40,
        },
        {
            "count": draft_confirmed_count,
            "key": "draft_confirmed",
            "label": "确认草案",
            "sort_order": 50,
        },
        {
            "count": run_succeeded_count,
            "key": "run_succeeded",
            "label": "运行成功",
            "sort_order": 60,
        },
        {
            "count": continued_followup_or_repair_count,
            "key": "continued_followup_or_repair",
            "label": "继续追问/修复",
            "sort_order": 70,
        },
    ]


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
