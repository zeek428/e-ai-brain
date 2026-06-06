from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from app.services.lifecycle_evidence import (
    lifecycle_matching_evidence,
    lifecycle_task_scope,
)


def lifecycle_risk_signals(
    current_store: Any,
    *,
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    signals = []
    task_ids = {task["id"] for task in tasks}
    for report in current_store.code_review_reports.values():
        if report["task_id"] not in task_ids or report["risk_level"] == "low":
            continue
        signals.append(
            {
                "risk_type": f"code_review_{report['risk_level']}_risk",
                "severity": report["risk_level"],
                "source_subject_type": "code_review_report",
                "source_subject_id": report["id"],
                "impact_summary": f"Review 报告提示：{report['summary']}",
                "recommendation": "优先处理高置信度 Review findings，并在关闭前补充边界测试。",
            }
        )
    matching_evidence = lifecycle_matching_evidence(current_store, tasks)
    for bug in matching_evidence["bug"]:
        if bug.get("status") == "closed" or bug.get("severity") not in {
            "blocker",
            "critical",
            "major",
        }:
            continue
        severity = "critical" if bug["severity"] in {"blocker", "critical"} else "high"
        signals.append(
            {
                "risk_type": f"{bug['severity']}_bug_open"
                if bug["severity"] != "critical"
                else "critical_bug_open",
                "severity": severity,
                "source_subject_type": "bug",
                "source_subject_id": bug["id"],
                "impact_summary": f"未关闭 Bug：{bug['title']}",
                "recommendation": "先完成修复、验证和关闭，再继续下游发布或迭代决策。",
            }
        )
    for metric in matching_evidence["gitlab_daily_code_metric"]:
        risk_count = metric.get("risk_count", 0) or 0
        quality_score = metric.get("quality_score")
        if risk_count <= 0 and (quality_score is None or quality_score >= 80):
            continue
        signals.append(
            {
                "risk_type": "gitlab_code_risk",
                "severity": "high" if risk_count >= 3 or (quality_score or 100) < 75 else "medium",
                "source_subject_type": "gitlab_daily_code_metric",
                "source_subject_id": metric["id"],
                "impact_summary": f"GitLab 代码指标存在 {risk_count} 个风险点。",
                "recommendation": "结合 MR、变更文件数和质量评分复核代码风险来源。",
            }
        )
    for release in matching_evidence["jenkins_release"]:
        if release.get("status") != "failed":
            continue
        signals.append(
            {
                "risk_type": "jenkins_release_failed",
                "severity": "high",
                "source_subject_type": "jenkins_release",
                "source_subject_id": release["id"],
                "impact_summary": f"Jenkins 发布失败：{release['job_name']}",
                "recommendation": "先定位失败原因并确认回滚或重试策略。",
            }
        )
    for metric in matching_evidence["online_log_metric"]:
        error_rate = metric.get("error_rate", 0) or 0
        error_count = metric.get("error_count", 0) or 0
        if error_rate < 0.01 and error_count < 10:
            continue
        signals.append(
            {
                "risk_type": "online_error_rate_high",
                "severity": "high" if error_rate >= 0.02 else "medium",
                "source_subject_type": "online_log_metric",
                "source_subject_id": metric["id"],
                "impact_summary": (
                    f"{metric['environment']} 错误率 {error_rate:.4f}，"
                    f"错误数 {error_count}。"
                ),
                "recommendation": "优先排查核心错误、回归范围和受影响模块。",
            }
        )
    for feedback in matching_evidence["user_feedback"]:
        satisfaction_score = feedback.get("satisfaction_score")
        is_negative = (
            feedback.get("sentiment") == "negative"
            or feedback.get("feedback_type") == "complaint"
            or (
                isinstance(satisfaction_score, int | float)
                and satisfaction_score <= 2
            )
        )
        if not is_negative:
            continue
        signals.append(
            {
                "risk_type": "negative_user_feedback",
                "severity": "medium",
                "source_subject_type": "user_feedback",
                "source_subject_id": feedback["id"],
                "impact_summary": f"负向用户反馈：{feedback['content']}",
                "recommendation": "将反馈归因到模块和需求，纳入迭代建议或 Bug 修复队列。",
            }
        )
    for suggestion in matching_evidence["iteration_plan_suggestion"]:
        if suggestion.get("confidence_level") != "low":
            continue
        signals.append(
            {
                "risk_type": "iteration_suggestion_low_confidence",
                "severity": "medium",
                "source_subject_type": "iteration_plan_suggestion",
                "source_subject_id": suggestion["id"],
                "impact_summary": f"低置信度迭代建议：{suggestion['title']}",
                "recommendation": "补充更多 Bug、反馈、使用或线上证据后再采纳。",
            }
        )
    return signals


def stable_record_id(prefix: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha1(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"{prefix}_{digest}"


def first_lifecycle_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    return min(tasks, key=lambda task: task["id"]) if tasks else None


def lifecycle_risk_context(
    current_store: Any,
    signal: dict[str, Any],
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    source_type = signal["source_subject_type"]
    source_id = signal["source_subject_id"]
    task = first_lifecycle_task(tasks)
    context = {
        "module_code": task.get("module_code") if task else None,
        "observed_at": None,
        "product_id": task.get("product_id") if task else None,
        "requirement_id": task.get("requirement_id") if task else None,
        "task_id": task.get("id") if task else None,
        "version_id": task.get("version_id") if task else None,
    }
    if source_type == "code_review_report":
        report = current_store.code_review_reports.get(source_id)
        report_task = current_store.ai_tasks.get(str(report.get("task_id"))) if report else None
        if report_task:
            context.update(
                {
                    "module_code": report_task.get("module_code"),
                    "observed_at": report.get("updated_at") or report.get("created_at"),
                    "product_id": report_task.get("product_id"),
                    "requirement_id": report_task.get("requirement_id"),
                    "task_id": report_task.get("id"),
                    "version_id": report_task.get("version_id"),
                }
            )
    elif source_type == "bug":
        bug = current_store.bugs.get(source_id)
        if bug:
            context.update(
                {
                    "module_code": bug.get("module_code"),
                    "observed_at": bug.get("updated_at") or bug.get("created_at"),
                    "product_id": bug.get("product_id"),
                    "requirement_id": bug.get("requirement_id") or context["requirement_id"],
                    "task_id": bug.get("related_task_id") or context["task_id"],
                    "version_id": bug.get("version_id") or context["version_id"],
                }
            )
    elif source_type == "gitlab_daily_code_metric":
        metric = current_store.gitlab_daily_code_metrics.get(source_id)
        if metric:
            context.update(
                {
                    "observed_at": metric.get("metric_date") or metric.get("updated_at"),
                    "product_id": metric.get("product_id"),
                }
            )
    elif source_type == "jenkins_release":
        release = current_store.jenkins_release_records.get(source_id)
        if release:
            context.update(
                {
                    "observed_at": release.get("deployed_at")
                    or release.get("updated_at")
                    or release.get("created_at"),
                    "product_id": release.get("product_id"),
                    "version_id": release.get("version_id") or context["version_id"],
                }
            )
    elif source_type == "online_log_metric":
        metric = current_store.online_log_metrics.get(source_id)
        if metric:
            context.update(
                {
                    "module_code": metric.get("module_code"),
                    "observed_at": metric.get("window_end") or metric.get("updated_at"),
                    "product_id": metric.get("product_id"),
                }
            )
    elif source_type == "user_feedback":
        feedback = current_store.user_feedback.get(source_id)
        if feedback:
            context.update(
                {
                    "module_code": feedback.get("module_code"),
                    "observed_at": feedback.get("updated_at") or feedback.get("created_at"),
                    "product_id": feedback.get("product_id"),
                    "requirement_id": feedback.get("related_requirement_id")
                    or context["requirement_id"],
                }
            )
    elif source_type == "iteration_plan_suggestion":
        suggestion = current_store.iteration_plan_suggestions.get(source_id)
        if suggestion:
            context.update(
                {
                    "module_code": ",".join(suggestion.get("module_codes", [])) or None,
                    "observed_at": suggestion.get("updated_at") or suggestion.get("created_at"),
                    "product_id": suggestion.get("product_id"),
                    "version_id": suggestion.get("version_id") or context["version_id"],
                }
            )
    if context["observed_at"] is None:
        context["observed_at"] = datetime.now(UTC).isoformat()
    return context


def sync_lifecycle_context_records(
    current_store: Any,
    *,
    subject: dict[str, Any],
    upstream: list[dict[str, Any]],
    downstream: list[dict[str, Any]],
    risk_signals: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> None:
    anchor_type = subject.get("type")
    anchor_id = subject.get("id")
    if not anchor_type or not anchor_id:
        return
    current_store.lifecycle_context_edges = {
        edge_id: edge
        for edge_id, edge in current_store.lifecycle_context_edges.items()
        if not (
            (
                edge.get("source_subject_type") == anchor_type
                and edge.get("source_subject_id") == anchor_id
            )
            or (
                edge.get("target_subject_type") == anchor_type
                and edge.get("target_subject_id") == anchor_id
            )
        )
    }
    now = datetime.now(UTC).isoformat()

    def upsert_edge(
        relation: dict[str, Any],
        *,
        source_subject_type: str,
        source_subject_id: str,
        target_subject_type: str,
        target_subject_id: str,
    ) -> None:
        edge_id = stable_record_id(
            "lifecycle_edge",
            {
                "relation_type": relation["relation_type"],
                "source_subject_id": source_subject_id,
                "source_subject_type": source_subject_type,
                "target_subject_id": target_subject_id,
                "target_subject_type": target_subject_type,
            },
        )
        current_store.lifecycle_context_edges[edge_id] = {
            "confidence": relation.get("confidence", 1.0),
            "id": edge_id,
            "metadata": current_store.snapshot(relation.get("metadata", {})),
            "module_code": relation.get("module_code"),
            "observed_at": relation.get("observed_at") or now,
            "product_id": relation.get("product_id") or subject.get("product_id"),
            "relation_type": relation["relation_type"],
            "source_module": relation.get("source_module", "lifecycle_context"),
            "source_subject_id": source_subject_id,
            "source_subject_type": source_subject_type,
            "summary": relation.get("summary"),
            "target_subject_id": target_subject_id,
            "target_subject_type": target_subject_type,
            "version_id": relation.get("version_id"),
        }

    for relation in upstream:
        upsert_edge(
            relation,
            source_subject_type=relation["subject_type"],
            source_subject_id=relation["subject_id"],
            target_subject_type=anchor_type,
            target_subject_id=anchor_id,
        )
    for relation in downstream:
        upsert_edge(
            relation,
            source_subject_type=anchor_type,
            source_subject_id=anchor_id,
            target_subject_type=relation["subject_type"],
            target_subject_id=relation["subject_id"],
        )
    task_scope = lifecycle_task_scope(tasks)
    risk_source_keys = {
        (signal["source_subject_type"], signal["source_subject_id"])
        for signal in risk_signals
    }
    current_store.lifecycle_risk_signals = {
        risk_id: risk
        for risk_id, risk in current_store.lifecycle_risk_signals.items()
        if not (
            risk.get("task_id") in task_scope["task_ids"]
            or risk.get("requirement_id") in task_scope["requirement_ids"]
            or (risk.get("source_subject_type"), risk.get("source_subject_id"))
            in risk_source_keys
        )
    }
    for signal in risk_signals:
        context = lifecycle_risk_context(current_store, signal, tasks)
        risk_id = stable_record_id(
            "lifecycle_risk",
            {
                "risk_type": signal["risk_type"],
                "source_subject_id": signal["source_subject_id"],
                "source_subject_type": signal["source_subject_type"],
                "task_id": context.get("task_id"),
            },
        )
        current_store.lifecycle_risk_signals[risk_id] = {
            **context,
            "id": risk_id,
            "impact_summary": signal["impact_summary"],
            "recommendation": signal["recommendation"],
            "risk_type": signal["risk_type"],
            "severity": signal["severity"],
            "source_subject_id": signal["source_subject_id"],
            "source_subject_type": signal["source_subject_type"],
        }
