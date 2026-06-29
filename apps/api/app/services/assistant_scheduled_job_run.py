from __future__ import annotations

import re
from time import perf_counter
from typing import Any

from app.core.store import MemoryStore
from app.services.assistant_chat_intents import (
    SCHEDULED_JOB_RUN_ONCE_KEYWORDS,
    merge_assistant_references,
)
from app.services.assistant_references import assistant_reference_matches_query
from app.services.assistant_tools import assistant_tool_results

SCHEDULED_JOB_MANAGE_PERMISSION = "system.scheduled_jobs.manage"
SCHEDULED_JOB_RUN_PERMISSION = "system.scheduled_jobs.run"


def scheduled_job_run_once_missing_job_draft_output(
    *,
    current_store: MemoryStore,
    message: str,
    product_id: str | None,
    queries: list[str],
    selected_references: list[dict[str, str]],
    user: dict[str, Any],
) -> dict[str, Any] | None:
    if not user_can_run_scheduled_job_from_assistant(user):
        return None
    if not weekly_feedback_run_once_draft_requested(message, queries):
        return None
    started = perf_counter()
    tool_results = assistant_tool_results(
        current_store,
        message="请帮我生成每周用户反馈洞察定时作业草案",
        product_id=product_id,
        references=selected_references,
    )
    draft_results = [
        result
        for result in tool_results
        if result.get("tool") == "assistant.action_draft"
        and result.get("intent") == "scheduled_job_draft"
    ]
    if not draft_results:
        return None
    for result in draft_results:
        summary = dict(result.get("summary") or {})
        summary["run_once_requested"] = True
        summary["status"] = "draft_required"
        result["summary"] = summary
        for item in result.get("items") or []:
            if not isinstance(item, dict):
                continue
            payload = dict(item.get("payload") or {})
            config_json = dict(payload.get("config_json") or {})
            config_json["assistant_run_once_request"] = {
                "requested": True,
                "source_message": message,
            }
            payload["config_json"] = config_json
            item["payload"] = payload
            item["run_once_requested"] = True
    draft_references = [
        reference
        for result in draft_results
        for reference in result.get("references", [])
        if isinstance(reference, dict)
    ]
    query_text = "、".join(queries) if queries else "这个 @ 引用"
    return {
        "answer": (
            f"还没有找到可执行的定时作业：{query_text}。"
            "当前尚未执行；我先生成周反馈洞察定时作业草案，"
            "确认并补齐校验项后再执行一次。"
        ),
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": "assistant-deterministic",
        "references": merge_assistant_references(selected_references, draft_references),
        "selected_references": selected_references,
        "suggestions": ["查看并确认草案", "补齐数据连接和结果动作"],
        "tool_results": draft_results,
    }


def weekly_feedback_run_once_draft_requested(message: str, queries: list[str]) -> bool:
    normalized = f"{message} {' '.join(queries)}".lower()
    has_feedback_context = any(
        keyword in normalized
        for keyword in ("用户反馈", "周反馈", "每周", "feedback", "user feedback")
    )
    has_insight_context = any(
        keyword in normalized
        for keyword in ("洞察", "提取", "抽取", "有价值", "价值", "信息", "insight", "extract")
    )
    return has_feedback_context and has_insight_context


def scheduled_job_references_from_explicit_mentions(
    current_store: MemoryStore,
    *,
    message: str,
    product_id: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    queries = explicit_mention_queries_for_run_once(message)
    if not queries:
        return {"attempted": False, "queries": [], "references": []}
    if not user_can_run_scheduled_job_from_assistant(user):
        return {
            "attempted": True,
            "blocked_reason": "permission_denied",
            "queries": queries,
            "references": [],
        }
    jobs = list(getattr(current_store, "scheduled_jobs", {}).values())
    if product_id:
        jobs = [job for job in jobs if job.get("product_id") == product_id]
    references: list[dict[str, str]] = []
    for query in queries:
        matches = [job for job in jobs if scheduled_job_matches_mention(job, query)]
        preferred_matches = scheduled_job_preferred_run_once_mention_matches(
            matches,
            query,
            require_official_insight=True,
        )
        if len(preferred_matches) == 1:
            matches = preferred_matches
        if len(matches) != 1:
            exact_matches = [
                job for job in matches if scheduled_job_exactly_matches_mention(job, query)
            ]
            if len(exact_matches) == 1:
                matches = exact_matches
        if len(matches) != 1:
            preferred_matches = scheduled_job_preferred_run_once_mention_matches(
                matches,
                query,
                require_official_insight=False,
            )
            if len(preferred_matches) == 1:
                matches = preferred_matches
        if len(matches) != 1:
            runnable_matches = [
                job for job in matches if scheduled_job_is_runnable_mention_match(job)
            ]
            if len(runnable_matches) == 1:
                matches = runnable_matches
        if len(matches) != 1:
            return {"attempted": True, "queries": queries, "references": []}
        job = matches[0]
        job_id = str(job["id"])
        references.append(
            {
                "id": job_id,
                "title": scheduled_job_title(job, job_id),
                "type": "scheduled_job",
                "url": f"/tasks/scheduled-jobs?job_id={job_id}",
            }
        )
    return {
        "attempted": True,
        "queries": queries,
        "references": merge_assistant_references(references),
    }


def explicit_mention_queries_for_run_once(message: str) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"[@＠]([^@＠\n]+)", message):
        raw_tail = match.group(1).strip()
        if not raw_tail:
            continue
        end_index = len(raw_tail)
        normalized_tail = raw_tail.lower()
        for keyword in SCHEDULED_JOB_RUN_ONCE_KEYWORDS:
            keyword_index = normalized_tail.find(keyword)
            if keyword_index >= 0:
                end_index = min(end_index, keyword_index)
        query = raw_tail[:end_index].strip(" \t，,。；;：:")
        query = re.sub(r"(请|麻烦|帮我|帮忙)$", "", query).strip()
        if not query:
            continue
        normalized_query = query.lower()
        if normalized_query in seen:
            continue
        seen.add(normalized_query)
        queries.append(query)
    return queries


def scheduled_job_run_once_permission_denied_output(
    *,
    attempted_queries: list[str],
    selected_references: list[dict[str, str]],
) -> dict[str, Any]:
    query_text = "、".join(attempted_queries) if attempted_queries else "这个 @ 引用"
    return {
        "answer": (
            f"我识别到你想执行定时作业：{query_text}，"
            "但当前账号没有执行定时作业的权限。请使用管理员账号，"
            "或让管理员授予定时作业执行权限后再执行。"
        ),
        "latency_ms": 0,
        "model": "assistant-deterministic",
        "references": selected_references,
        "selected_references": selected_references,
        "suggestions": ["联系管理员授权", "生成可确认的配置草案"],
        "tool_results": [
            {
                "intent": "scheduled_job_run_once",
                "items": [],
                "summary": {
                    "queries": attempted_queries,
                    "required_permission": SCHEDULED_JOB_RUN_PERMISSION,
                    "status": "permission_denied",
                },
                "tool": "assistant.scheduled_job_run",
            }
        ],
    }


def scheduled_job_matches_mention(job: dict[str, Any], query: str) -> bool:
    normalized_query = query.lower().strip()
    haystack = " ".join(
        str(value or "")
        for value in (
            job.get("id"),
            job.get("name"),
            job.get("title"),
            job.get("code"),
            job.get("job_type"),
        )
    ).lower()
    if normalized_query in haystack:
        return True
    return assistant_reference_matches_query(
        "scheduled_job",
        job,
        query,
        current_store=None,
    )


def scheduled_job_exactly_matches_mention(job: dict[str, Any], query: str) -> bool:
    normalized_query = normalized_mention_token(query)
    if not normalized_query:
        return False
    return any(
        normalized_mention_token(value) == normalized_query
        for value in (
            job.get("id"),
            job.get("name"),
            job.get("title"),
            job.get("code"),
        )
    )


def scheduled_job_preferred_run_once_mention_matches(
    jobs: list[dict[str, Any]],
    query: str,
    *,
    require_official_insight: bool = False,
) -> list[dict[str, Any]]:
    if not weekly_feedback_run_once_draft_requested(query, [query]):
        return []
    scored_matches = [(scheduled_job_weekly_feedback_insight_score(job), job) for job in jobs]
    preferred_matches = [(score, job) for score, job in scored_matches if score > 0]
    if not preferred_matches:
        return []
    runnable_matches = [
        (score, job)
        for score, job in preferred_matches
        if scheduled_job_is_runnable_mention_match(job)
    ]
    candidates = runnable_matches or preferred_matches
    if require_official_insight:
        candidates = [
            (score, job)
            for score, job in candidates
            if scheduled_job_is_official_weekly_feedback_insight(job)
        ]
        if not candidates:
            return []
    ranked = sorted(
        candidates,
        key=lambda item: (
            item[0],
            str(item[1].get("updated_at") or item[1].get("created_at") or ""),
            str(item[1].get("id") or ""),
        ),
        reverse=True,
    )
    if len(ranked) == 1 or ranked[0][0] > ranked[1][0]:
        return [ranked[0][1]]
    return [job for _, job in ranked]


def scheduled_job_is_official_weekly_feedback_insight(job: dict[str, Any]) -> bool:
    config_json = job.get("config_json")
    assistant_template = (
        config_json.get("assistant_template") if isinstance(config_json, dict) else None
    )
    template_code = (
        assistant_template.get("code") if isinstance(assistant_template, dict) else None
    )
    return (
        template_code == "weekly_feedback_insight"
        or str(job.get("job_type") or "").strip() == "user_feedback_insight_extract"
    )


def scheduled_job_weekly_feedback_insight_score(job: dict[str, Any]) -> int:
    config_json = job.get("config_json")
    assistant_template = (
        config_json.get("assistant_template") if isinstance(config_json, dict) else None
    )
    template_code = (
        assistant_template.get("code") if isinstance(assistant_template, dict) else None
    )
    code = str(job.get("code") or "").strip()
    job_type = str(job.get("job_type") or "").strip()
    title = normalized_mention_token(
        " ".join(
            str(value or "")
            for value in (
                job.get("name"),
                job.get("title"),
                job.get("description"),
                job.get("summary"),
            )
        )
    )
    source_system = str(job.get("source_system") or "").strip()
    score = 0
    if code == "weekly_feedback_insight":
        score += 70
    if template_code == "weekly_feedback_insight":
        score += 65
    if job_type == "user_feedback_insight_extract":
        score += 60
    if "用户反馈" in title or "feedback" in title:
        score += 20
    if any(
        keyword in title
        for keyword in ("洞察", "提取", "抽取", "有价值", "价值", "insight", "extract")
    ):
        score += 20
    if "每周" in title or "weekly" in title:
        score += 10
    if source_system == "aliyun-maxcompute":
        score += 5
    if scheduled_job_is_runnable_mention_match(job):
        score += 5
    return score


def scheduled_job_is_runnable_mention_match(job: dict[str, Any]) -> bool:
    return bool(job.get("enabled")) and str(job.get("status") or "active") == "active"


def user_can_run_scheduled_job_from_assistant(user: dict[str, Any]) -> bool:
    roles = set(user.get("roles") or [])
    permissions = set(user.get("permissions") or [])
    return (
        "admin" in roles
        or "system.admin" in permissions
        or SCHEDULED_JOB_MANAGE_PERMISSION in permissions
        or SCHEDULED_JOB_RUN_PERMISSION in permissions
    )


def normalized_mention_token(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def scheduled_job_title(job: dict[str, Any], job_id: str) -> str:
    return str(job.get("name") or job.get("title") or job.get("code") or job_id)


def scheduled_job_run_reference(
    *,
    job: dict[str, Any],
    job_id: str,
    run: dict[str, Any],
) -> dict[str, str]:
    run_id = str(run["id"])
    return {
        "id": run_id,
        "title": f"{scheduled_job_title(job, job_id)} / {run.get('status') or 'unknown'}",
        "type": "scheduled_job_run",
        "url": f"/tasks/scheduled-jobs?run_id={run_id}",
    }


def scheduled_job_run_tool_result(
    *,
    error_code: str | None,
    error_message: str | None,
    job: dict[str, Any],
    job_id: str,
    run: dict[str, Any] | None,
) -> dict[str, Any]:
    job_name = scheduled_job_title(job, job_id)
    if run is None:
        return {
            "intent": "scheduled_job_run_once",
            "items": [],
            "references": [],
            "summary": {
                "error_code": error_code,
                "error_message": error_message,
                "scheduled_job_id": job_id,
                "scheduled_job_name": job_name,
                "status": "failed",
                "trigger_type": "manual",
            },
            "tool": "assistant.scheduled_job_run",
        }
    run_reference = scheduled_job_run_reference(job=job, job_id=job_id, run=run)
    progress_text = scheduled_job_run_progress_text(run)
    item = {
        "id": run_reference["id"],
        "records_imported": int(run.get("records_imported") or 0),
        "scheduled_job_id": job_id,
        "status": str(run.get("status") or "unknown"),
        "title": run_reference["title"],
        "trigger_type": str(run.get("trigger_type") or "manual"),
        "type": "scheduled_job_run",
        "url": run_reference["url"],
    }
    if progress_text:
        item["progress_text"] = progress_text
    summary = {
        "error_code": error_code,
        "error_message": error_message,
        "records_imported": int(run.get("records_imported") or 0),
        "run_id": run_reference["id"],
        "scheduled_job_id": job_id,
        "scheduled_job_name": job_name,
        "status": str(run.get("status") or "unknown"),
        "trigger_type": str(run.get("trigger_type") or "manual"),
    }
    if progress_text:
        summary["progress_text"] = progress_text
    return {
        "intent": "scheduled_job_run_once",
        "items": [item],
        "references": [run_reference],
        "summary": summary,
        "tool": "assistant.scheduled_job_run",
    }


def scheduled_job_run_progress_text(run: dict[str, Any]) -> str | None:
    result_summary = run.get("result_summary")
    if not isinstance(result_summary, dict):
        return None
    execution_nodes = result_summary.get("execution_nodes")
    if not isinstance(execution_nodes, dict):
        return None
    runner_node = execution_nodes.get("runner_execution")
    if not isinstance(runner_node, dict):
        return None
    runner_status = str(runner_node.get("status") or "").strip()
    if runner_status not in {"claimed", "queued", "running"}:
        return None
    executor_type = str(runner_node.get("executor_type") or "AI 执行器").strip()
    runner_task_id = str(runner_node.get("runner_task_id") or "").strip()
    status_labels = {
        "claimed": "等待 AI 执行器开始执行",
        "queued": "等待 AI 执行器接单",
        "running": "AI 执行器执行中",
    }
    suffix = f"{executor_type} / {runner_task_id}" if runner_task_id else executor_type
    return f"{status_labels[runner_status]}：{suffix}"
