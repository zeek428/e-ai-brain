from __future__ import annotations

from typing import Any


def lifecycle_task_scope(tasks: list[dict[str, Any]]) -> dict[str, set[str]]:
    return {
        "module_codes": {str(task["module_code"]) for task in tasks if task.get("module_code")},
        "product_ids": {str(task["product_id"]) for task in tasks if task.get("product_id")},
        "requirement_ids": {
            str(task["requirement_id"]) for task in tasks if task.get("requirement_id")
        },
        "task_ids": {str(task["id"]) for task in tasks if task.get("id")},
        "version_ids": {str(task["version_id"]) for task in tasks if task.get("version_id")},
    }


def lifecycle_matches_scope(item: dict[str, Any], scope: dict[str, set[str]]) -> bool:
    if item.get("related_task_id") and str(item["related_task_id"]) in scope["task_ids"]:
        return True
    if item.get("requirement_id") and str(item["requirement_id"]) in scope["requirement_ids"]:
        return True
    product_id = item.get("product_id")
    if product_id and str(product_id) not in scope["product_ids"]:
        return False
    version_id = item.get("version_id")
    if version_id and scope["version_ids"] and str(version_id) not in scope["version_ids"]:
        return False
    module_code = item.get("module_code")
    if module_code and scope["module_codes"] and str(module_code) not in scope["module_codes"]:
        return False
    return bool(product_id and str(product_id) in scope["product_ids"])


def lifecycle_matching_evidence(
    current_store: Any,
    tasks: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    scope = lifecycle_task_scope(tasks)
    return {
        "bug": [
            item
            for item in current_store.bugs.values()
            if lifecycle_matches_scope(item, scope)
        ],
        "gitlab_daily_code_metric": [
            item
            for item in current_store.gitlab_daily_code_metrics.values()
            if lifecycle_matches_scope(item, scope)
        ],
        "jenkins_release": [
            item
            for item in current_store.jenkins_release_records.values()
            if lifecycle_matches_scope(item, scope)
        ],
        "online_log_metric": [
            item
            for item in current_store.online_log_metrics.values()
            if lifecycle_matches_scope(item, scope)
        ],
        "user_usage_metric": [
            item
            for item in current_store.user_usage_metrics.values()
            if lifecycle_matches_scope(item, scope)
        ],
        "user_feedback": [
            item
            for item in current_store.user_feedback.values()
            if lifecycle_matches_scope(item, scope)
        ],
        "iteration_plan_suggestion": [
            item
            for item in current_store.iteration_plan_suggestions.values()
            if lifecycle_matches_scope(item, scope)
        ],
    }


def lifecycle_missing_context(current_store: Any, *, tasks: list[dict[str, Any]]) -> list[str]:
    missing = []
    if not any(task["task_type"] == "automated_testing" for task in tasks):
        missing.append("automated_testing")
    matching_evidence = lifecycle_matching_evidence(current_store, tasks)
    missing.extend(subject_type for subject_type, items in matching_evidence.items() if not items)
    return missing
