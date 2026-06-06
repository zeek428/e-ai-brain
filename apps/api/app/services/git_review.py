from __future__ import annotations

import os
import re
from typing import Any
from urllib.request import urlopen

from app.api.deps import api_error, require_roles
from app.services import git_review_github, git_review_gitlab
from app.services.git_review_snapshots import (
    create_code_review_source_snapshot,
    ensure_snapshot_context,
    record_audit_event,
    save_git_review_snapshot_record,
)
from app.services.product_config_context import ensure_enum, product_config_source_store
from app.services.task_workflow_context import task_workflow_write_store


def product_config_write_store(current_store: Any) -> Any:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return current_store
    required_methods = (
        "list_product_git_repositories",
        "list_product_modules",
        "list_product_versions",
        "list_products",
        "list_related_systems",
    )
    if not all(
        callable(getattr(repository, method_name, None))
        for method_name in required_methods
    ):
        return current_store
    return product_config_source_store(repository)


def credential_ref_env_candidates(credential_ref: str) -> list[str]:
    if credential_ref.startswith("env:"):
        return [credential_ref.removeprefix("env:").strip()]
    normalized = credential_ref.removeprefix("secret://").removeprefix("secret/")
    env_name = re.sub(r"[^A-Za-z0-9]+", "_", normalized).strip("_").upper()
    if not env_name:
        return []
    candidates = [env_name]
    if not env_name.endswith("_TOKEN"):
        candidates.append(f"{env_name}_TOKEN")
    if "GITLAB" in env_name and "READONLY" in env_name:
        candidates.append("GITLAB_READONLY_TOKEN")
    return candidates


def credential_ref_token(credential_ref: str, *, fallback_env_names: list[str]) -> str | None:
    credential_ref = credential_ref.strip()
    if credential_ref and not credential_ref.startswith(("env:", "secret://", "secret/")):
        return credential_ref
    for env_name in credential_ref_env_candidates(credential_ref):
        token = os.getenv(env_name, "").strip()
        if token:
            return token
    for env_name in fallback_env_names:
        token = os.getenv(env_name, "").strip()
        if token:
            return token
    return None


def gitlab_base_url(repository: dict[str, Any]) -> str | None:
    return git_review_gitlab.gitlab_base_url(repository)


def gitlab_access_token(repository: dict[str, Any]) -> str | None:
    return git_review_gitlab.gitlab_access_token(
        repository,
        token_resolver=lambda credential_ref, fallback_env_names: credential_ref_token(
            credential_ref,
            fallback_env_names=fallback_env_names,
        ),
    )


def gitlab_project_key(repository: dict[str, Any]) -> str:
    return git_review_gitlab.gitlab_project_key(repository)


def gitlab_request_json(base_url: str, token: str, path: str) -> dict[str, Any]:
    return git_review_gitlab.gitlab_request_json(base_url, token, path, opener=urlopen)


def gitlab_changes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return git_review_gitlab.gitlab_changes(payload)


def real_gitlab_preview(repository: dict[str, Any], mr_iid: int) -> dict[str, Any]:
    return git_review_gitlab.real_gitlab_preview(
        repository,
        mr_iid,
        request_json=gitlab_request_json,
        token_resolver=lambda credential_ref, fallback_env_names: credential_ref_token(
            credential_ref,
            fallback_env_names=fallback_env_names,
        ),
    )


def gitlab_preview(repository: dict[str, Any], mr_iid: int) -> dict[str, Any]:
    return git_review_gitlab.gitlab_preview(
        repository,
        mr_iid,
        request_json=gitlab_request_json,
        token_resolver=lambda credential_ref, fallback_env_names: credential_ref_token(
            credential_ref,
            fallback_env_names=fallback_env_names,
        ),
    )


def github_base_url(repository: dict[str, Any]) -> str | None:
    return git_review_github.github_base_url(repository)


def github_access_token(repository: dict[str, Any]) -> str | None:
    return git_review_github.github_access_token(
        repository,
        token_resolver=lambda credential_ref, fallback_env_names: credential_ref_token(
            credential_ref,
            fallback_env_names=fallback_env_names,
        ),
    )


def clean_repository_path(value: str) -> str:
    return git_review_github.clean_repository_path(value)


def github_repository_path(repository: dict[str, Any]) -> str:
    return git_review_github.github_repository_path(repository)


def github_request_json(base_url: str, token: str, path: str) -> dict[str, Any] | list[Any]:
    return git_review_github.github_request_json(base_url, token, path)


def github_pull_request_summary(
    repository: dict[str, Any],
    *,
    owner_repo: str,
    pull_request: dict[str, Any],
) -> dict[str, Any]:
    return git_review_github.github_pull_request_summary(
        repository,
        owner_repo=owner_repo,
        pull_request=pull_request,
    )


def github_pull_requests(
    repository: dict[str, Any],
    *,
    state: str,
    limit: int,
) -> list[dict[str, Any]]:
    return git_review_github.github_pull_requests(
        repository,
        request_json=github_request_json,
        state=state,
        limit=limit,
        token_resolver=lambda credential_ref, fallback_env_names: credential_ref_token(
            credential_ref,
            fallback_env_names=fallback_env_names,
        ),
    )


def github_preview(repository: dict[str, Any], pr_number: int) -> dict[str, Any]:
    return git_review_github.github_preview(
        repository,
        pr_number,
        request_json=github_request_json,
        token_resolver=lambda credential_ref, fallback_env_names: credential_ref_token(
            credential_ref,
            fallback_env_names=fallback_env_names,
        ),
    )


def preview_gitlab_mr_response(
    *,
    current_store: Any,
    mr_iid: int,
    repository_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"reviewer", "rd_owner"})
    current_store = product_config_write_store(current_store)
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "GitLab repository binding not found")
    if repository["git_provider"] != "gitlab":
        raise api_error(400, "VALIDATION_ERROR", "Repository is not a GitLab binding")
    preview = gitlab_preview(repository, mr_iid)
    audit_event = record_audit_event(
        current_store,
        event_type="gitlab_mr.previewed",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repository_id,
        payload={"mr_iid": mr_iid},
    )
    save_git_review_snapshot_record(current_store, snapshot=None, audit_event=audit_event)
    return preview


def snapshot_gitlab_mr_response(
    *,
    current_store: Any,
    mr_iid: int,
    payload: Any,
    repository_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"reviewer", "rd_owner"})
    current_store = task_workflow_write_store(current_store)
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "GitLab repository binding not found")
    requirement = current_store.requirements.get(payload.requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    technical_solution = current_store.ai_tasks.get(payload.technical_solution_task_id)
    if (
        technical_solution is None
        or technical_solution["task_type"] != "technical_solution"
        or technical_solution["status"] != "completed"
    ):
        raise api_error(
            400,
            "TECHNICAL_SOLUTION_NOT_CONFIRMED",
            "MR snapshot requires a confirmed technical solution task",
        )
    ensure_snapshot_context(
        repository=repository,
        requirement=requirement,
        technical_solution=technical_solution,
    )
    return create_code_review_source_snapshot(
        current_store,
        repository=repository,
        requirement=requirement,
        mr_iid=mr_iid,
        preview=gitlab_preview(repository, mr_iid),
        payload=payload,
        user=user,
        event_prefix="gitlab_mr",
        diff_storage_prefix="gitlab-mr-diff",
    )


def list_github_pull_requests_response(
    *,
    current_store: Any,
    limit: int,
    repository_id: str,
    state: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"reviewer", "rd_owner"})
    ensure_enum(state, {"open", "closed", "all"}, "GitHub pull request state")
    current_store = product_config_write_store(current_store)
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "GitHub repository binding not found")
    if repository["git_provider"] != "github":
        raise api_error(400, "VALIDATION_ERROR", "Repository is not a GitHub binding")
    items = github_pull_requests(repository, state=state, limit=limit)
    audit_event = record_audit_event(
        current_store,
        event_type="github_pr.listed",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repository_id,
        payload={"limit": limit, "state": state},
    )
    save_git_review_snapshot_record(current_store, snapshot=None, audit_event=audit_event)
    return {"items": items, "total": len(items)}


def preview_github_pr_response(
    *,
    current_store: Any,
    pr_number: int,
    repository_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"reviewer", "rd_owner"})
    current_store = product_config_write_store(current_store)
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "GitHub repository binding not found")
    if repository["git_provider"] != "github":
        raise api_error(400, "VALIDATION_ERROR", "Repository is not a GitHub binding")
    preview = github_preview(repository, pr_number)
    audit_event = record_audit_event(
        current_store,
        event_type="github_pr.previewed",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repository_id,
        payload={"pr_number": pr_number},
    )
    save_git_review_snapshot_record(current_store, snapshot=None, audit_event=audit_event)
    return preview


def snapshot_github_pr_response(
    *,
    current_store: Any,
    payload: Any,
    pr_number: int,
    repository_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"reviewer", "rd_owner"})
    current_store = task_workflow_write_store(current_store)
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "GitHub repository binding not found")
    if repository["git_provider"] != "github":
        raise api_error(400, "VALIDATION_ERROR", "Repository is not a GitHub binding")
    requirement = current_store.requirements.get(payload.requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    technical_solution = current_store.ai_tasks.get(payload.technical_solution_task_id)
    if (
        technical_solution is None
        or technical_solution["task_type"] != "technical_solution"
        or technical_solution["status"] != "completed"
    ):
        raise api_error(
            400,
            "TECHNICAL_SOLUTION_NOT_CONFIRMED",
            "PR snapshot requires a confirmed technical solution task",
        )
    ensure_snapshot_context(
        repository=repository,
        requirement=requirement,
        technical_solution=technical_solution,
    )
    return create_code_review_source_snapshot(
        current_store,
        repository=repository,
        requirement=requirement,
        mr_iid=pr_number,
        preview=github_preview(repository, pr_number),
        payload=payload,
        user=user,
        event_prefix="github_pr",
        diff_storage_prefix="github-pr-diff",
    )
