from __future__ import annotations

import json
from typing import Any

from app.api.deps import api_error


def public_git_repository(repository: dict[str, Any] | None) -> dict[str, Any] | None:
    if not repository:
        return None
    public = dict(repository)
    credentials_ref = public.pop("credentials_ref", None)
    if credentials_ref:
        public["credentials_configured"] = True
    return public


def public_product_context(product_context: Any) -> Any:
    if not isinstance(product_context, dict):
        return {}
    public_context = json.loads(json.dumps(product_context, ensure_ascii=False))
    repositories = public_context.get("repositories")
    if isinstance(repositories, dict):
        items = repositories.get("items")
        if isinstance(items, list):
            repositories["items"] = [
                public_git_repository(item) if isinstance(item, dict) else item
                for item in items
            ]
            repositories["total"] = len(repositories["items"])
    return public_context


def raise_git_context_mismatch(message: str) -> None:
    raise api_error(400, "GITLAB_CONTEXT_MISMATCH", message)


def raise_task_context_mismatch(message: str) -> None:
    raise api_error(400, "TASK_CONTEXT_MISMATCH", message)


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def _read_memory_record(
    current_store: Any,
    collection_name: str,
    record_id: Any,
) -> dict[str, Any] | None:
    if record_id is None:
        return None
    record = _read_memory_dict(current_store, collection_name).get(str(record_id))
    return record if isinstance(record, dict) else None


def ensure_task_matches_requirement(
    task: dict[str, Any],
    requirement: dict[str, Any],
    *,
    source_label: str,
) -> None:
    if task["requirement_id"] != requirement["id"]:
        raise_task_context_mismatch(f"{source_label} task must belong to the same requirement")
    if task["product_id"] != requirement["product_id"]:
        raise_task_context_mismatch(f"{source_label} task must belong to the same product")
    if task["version_id"] != requirement["version_id"]:
        raise_task_context_mismatch(f"{source_label} task must belong to the same version")


def product_context(current_store: Any, requirement: dict[str, Any]) -> dict[str, Any]:
    product = _read_memory_record(current_store, "products", requirement["product_id"])
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    version = (
        _read_memory_record(current_store, "product_versions", requirement["version_id"])
        if requirement.get("version_id")
        else None
    )
    module = next(
        (
            item
            for item in _read_memory_dict(current_store, "product_modules").values()
            if item["product_id"] == product["id"]
            and item["code"] == requirement.get("module_code")
        ),
        None,
    )
    repositories = [
        public_git_repository(repository)
        for repository in _read_memory_dict(
            current_store,
            "product_git_repositories",
        ).values()
        if repository["product_id"] == product["id"] and repository.get("status") == "active"
    ]
    related_systems = [
        related_system
        for related_system in _read_memory_dict(current_store, "related_systems").values()
        if related_system.get("product_id") == product["id"]
        and related_system.get("status") == "active"
    ]
    return {
        "product": current_store.snapshot(product),
        "version": current_store.snapshot(version) if version else None,
        "module": current_store.snapshot(module) if module else None,
        "repositories": current_store.snapshot({"items": repositories, "total": len(repositories)}),
        "related_systems": current_store.snapshot(
            {"items": related_systems, "total": len(related_systems)}
        ),
    }


def ensure_confirmed_technical_solution_task(
    current_store: Any,
    *,
    requirement: dict[str, Any],
    technical_solution_task_id: Any,
) -> dict[str, Any]:
    technical_solution = _read_memory_record(
        current_store,
        "ai_tasks",
        technical_solution_task_id,
    )
    if (
        technical_solution is None
        or technical_solution["task_type"] != "technical_solution"
        or technical_solution["status"] != "completed"
    ):
        raise api_error(
            400,
            "TECHNICAL_SOLUTION_NOT_CONFIRMED",
            "Task requires a confirmed technical solution",
        )
    ensure_task_matches_requirement(
        technical_solution,
        requirement,
        source_label="Technical solution",
    )
    return technical_solution


def ensure_confirmed_release_readiness_task(
    current_store: Any,
    *,
    requirement: dict[str, Any],
    release_readiness_task_id: Any,
) -> dict[str, Any]:
    release_readiness = _read_memory_record(
        current_store,
        "ai_tasks",
        release_readiness_task_id,
    )
    if (
        release_readiness is None
        or release_readiness["task_type"] != "release_readiness"
        or release_readiness["status"] != "completed"
    ):
        raise api_error(
            400,
            "RELEASE_READINESS_NOT_CONFIRMED",
            "Task requires a confirmed release readiness task",
        )
    ensure_task_matches_requirement(
        release_readiness,
        requirement,
        source_label="Release readiness",
    )
    return release_readiness


def ensure_git_snapshot_context(
    *,
    repository: dict[str, Any],
    requirement: dict[str, Any],
    technical_solution: dict[str, Any],
) -> None:
    if repository["product_id"] != requirement["product_id"]:
        raise_git_context_mismatch(
            "GitLab repository binding and requirement must belong to the same product"
        )
    if technical_solution["requirement_id"] != requirement["id"]:
        raise_git_context_mismatch(
            "Technical solution task must be derived from the snapshot requirement"
        )
    if technical_solution["product_id"] != requirement["product_id"]:
        raise_git_context_mismatch(
            "Technical solution task and requirement must belong to the same product"
        )
    if technical_solution["version_id"] != requirement["version_id"]:
        raise_git_context_mismatch(
            "Technical solution task and requirement must belong to the same version"
        )


def collection_snapshot(current_store: Any, items: list[dict[str, Any]]) -> dict[str, Any]:
    return current_store.snapshot({"items": items, "total": len(items)})


def source_task_context(current_store: Any, task: dict[str, Any]) -> dict[str, Any]:
    return current_store.snapshot(
        {
            "id": task["id"],
            "task_type": task["task_type"],
            "title": task["title"],
            "status": task["status"],
            "summary": (task.get("output_json") or {}).get("summary"),
            "output": task.get("output_json"),
        }
    )


def matching_bugs_for_task_context(
    current_store: Any,
    task: dict[str, Any],
    *,
    include_closed: bool = False,
) -> list[dict[str, Any]]:
    bugs = []
    for bug in _read_memory_dict(current_store, "bugs").values():
        if bug["product_id"] != task["product_id"]:
            continue
        if bug.get("version_id") not in {None, task["version_id"]}:
            continue
        if bug.get("requirement_id") not in {None, task["requirement_id"]}:
            continue
        if not include_closed and bug["status"] == "closed":
            continue
        bugs.append(bug)
    bugs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return bugs


def matching_jenkins_releases(current_store: Any, task: dict[str, Any]) -> list[dict[str, Any]]:
    releases = [
        release
        for release in _read_memory_dict(current_store, "jenkins_release_records").values()
        if release.get("product_id") == task["product_id"]
        and release.get("version_id") == task["version_id"]
    ]
    releases.sort(
        key=lambda item: (
            item.get("deployed_at") or item.get("created_at") or "",
            item.get("updated_at") or "",
        ),
        reverse=True,
    )
    return releases


def matching_online_log_metrics(current_store: Any, task: dict[str, Any]) -> list[dict[str, Any]]:
    module_code = task.get("module_code")
    metrics = []
    for metric in _read_memory_dict(current_store, "online_log_metrics").values():
        if metric.get("product_id") != task["product_id"]:
            continue
        if module_code is not None and metric.get("module_code") not in {None, module_code}:
            continue
        metrics.append(metric)
    metrics.sort(
        key=lambda item: (
            item.get("window_start") or "",
            item.get("updated_at") or item.get("created_at") or "",
        ),
        reverse=True,
    )
    return metrics


def matching_gitlab_daily_code_metrics(
    current_store: Any,
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    product_repository_ids = {
        repository["id"]
        for repository in _read_memory_dict(
            current_store,
            "product_git_repositories",
        ).values()
        if repository["product_id"] == task["product_id"]
    }
    metrics = [
        metric
        for metric in _read_memory_dict(current_store, "gitlab_daily_code_metrics").values()
        if metric.get("product_id") == task["product_id"]
        and metric.get("repository_id") in product_repository_ids
    ]
    metrics.sort(
        key=lambda item: (
            item.get("metric_date") or "",
            item.get("updated_at") or item.get("created_at") or "",
        ),
        reverse=True,
    )
    return metrics


def release_readiness_context(
    current_store: Any,
    *,
    requirement: dict[str, Any],
    technical_solution: dict[str, Any],
) -> dict[str, Any]:
    task_context = {
        "product_id": requirement["product_id"],
        "version_id": requirement["version_id"],
        "module_code": requirement.get("module_code"),
        "requirement_id": requirement["id"],
    }
    return {
        "source_technical_solution": source_task_context(current_store, technical_solution),
        "bugs": collection_snapshot(
            current_store,
            matching_bugs_for_task_context(current_store, task_context),
        ),
        "jenkins_releases": collection_snapshot(
            current_store,
            matching_jenkins_releases(current_store, task_context),
        ),
        "online_log_metrics": collection_snapshot(
            current_store,
            matching_online_log_metrics(current_store, task_context),
        ),
        "gitlab_daily_code_metrics": collection_snapshot(
            current_store,
            matching_gitlab_daily_code_metrics(current_store, task_context),
        ),
    }


def post_release_analysis_context(
    current_store: Any,
    *,
    requirement: dict[str, Any],
    release_readiness: dict[str, Any],
) -> dict[str, Any]:
    task_context = {
        "product_id": requirement["product_id"],
        "version_id": requirement["version_id"],
        "module_code": requirement.get("module_code"),
        "requirement_id": requirement["id"],
    }
    return {
        "source_release_readiness": source_task_context(current_store, release_readiness),
        "bugs": collection_snapshot(
            current_store,
            matching_bugs_for_task_context(current_store, task_context, include_closed=True),
        ),
        "jenkins_releases": collection_snapshot(
            current_store,
            matching_jenkins_releases(current_store, task_context),
        ),
        "online_log_metrics": collection_snapshot(
            current_store,
            matching_online_log_metrics(current_store, task_context),
        ),
    }
