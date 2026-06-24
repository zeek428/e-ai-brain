from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, api_error, require_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.product_config_context import (
    delete_product_config_record,
    ensure_enum,
    ensure_non_blank,
    get_product_git_repository_record,
    payload_updates,
    product_config_record_write_store,
    product_config_write_store,
    record_audit_event,
    save_product_config_record,
    uses_repository_context,
)
from app.services.product_git_repository_listing import (
    list_product_git_repositories_response,
    public_git_repository,
)

router = APIRouter(tags=["product_git_repositories"])

GIT_REPO_STATUSES = {"active", "inactive"}
GIT_REPO_PROVIDERS = {"gitlab", "github"}


class ProductGitRepositoryRequest(BaseModel):
    repo_type: str = "code"
    name: str
    remote_url: str | None = None
    git_provider: str = "gitlab"
    project_id: str | None = None
    project_path: str | None = None
    credential_ref: str | None = None
    default_branch: str = "main"
    root_path: str = "/"
    status: str = "active"


class ProductGitRepositoryPatchRequest(BaseModel):
    repo_type: str | None = None
    name: str | None = None
    remote_url: str | None = None
    git_provider: str | None = None
    project_id: str | None = None
    project_path: str | None = None
    credential_ref: str | None = None
    default_branch: str | None = None
    root_path: str | None = None
    status: str | None = None


def _validate_git_repository_binding(
    provider: str,
    *,
    project_id: str | None,
    project_path: str | None,
    remote_url: str | None,
) -> None:
    ensure_enum(provider, GIT_REPO_PROVIDERS, "git provider")
    if provider == "gitlab" and not project_id and not project_path:
        raise api_error(400, "VALIDATION_ERROR", "GitLab project_id or project_path is required")
    if provider == "github" and not project_path and not remote_url:
        raise api_error(400, "VALIDATION_ERROR", "GitHub project_path or remote_url is required")


@router.get("/api/products/{product_id}/git-repositories")
def list_product_git_repositories(
    product_id: str,
    request: Request,
    active_only: bool = False,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    return list_product_git_repositories_response(
        active_only=active_only,
        current_store=store(request),
        product_id=product_id,
        trace_id=get_trace_id(request),
    )


@router.post("/api/products/{product_id}/git-repositories")
def create_product_git_repository(
    product_id: str,
    request: Request,
    payload: ProductGitRepositoryRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_write_store(store(request))
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    name = ensure_non_blank(payload.name, "name")
    ensure_enum(payload.status, GIT_REPO_STATUSES, "product Git repository status")
    _validate_git_repository_binding(
        payload.git_provider,
        project_id=payload.project_id,
        project_path=payload.project_path,
        remote_url=payload.remote_url,
    )

    repository_id = current_store.new_id("repo")
    repository = {
        "id": repository_id,
        "product_id": product_id,
        "repo_type": payload.repo_type,
        "name": name,
        "remote_url": payload.remote_url,
        "git_provider": payload.git_provider,
        "project_id": payload.project_id,
        "project_path": payload.project_path,
        "credential_ref": payload.credential_ref,
        "default_branch": payload.default_branch,
        "root_path": payload.root_path,
        "status": payload.status,
    }
    if not uses_repository_context(current_store):
        current_store.product_git_repositories[repository_id] = repository
    audit_event = record_audit_event(
        current_store,
        event_type="product_git_repository.created",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repository_id,
    )
    save_product_config_record(
        current_store,
        "product_git_repositories",
        repository,
        audit_event=audit_event,
    )
    return envelope(public_git_repository(repository), get_trace_id(request))


@router.patch("/api/product-git-repositories/{repo_id}")
def patch_product_git_repository(
    repo_id: str,
    request: Request,
    payload: ProductGitRepositoryPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_record_write_store(store(request))
    repository = get_product_git_repository_record(current_store, repo_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "Product Git repository not found")
    updates = payload_updates(payload)
    if "name" in updates:
        updates["name"] = ensure_non_blank(updates["name"], "name")
    if "status" in updates:
        ensure_enum(updates["status"], GIT_REPO_STATUSES, "product Git repository status")
    next_provider = updates.get("git_provider", repository["git_provider"])
    next_project_id = updates.get("project_id", repository.get("project_id"))
    next_project_path = updates.get("project_path", repository.get("project_path"))
    next_remote_url = updates.get("remote_url", repository.get("remote_url"))
    _validate_git_repository_binding(
        next_provider,
        project_id=next_project_id,
        project_path=next_project_path,
        remote_url=next_remote_url,
    )
    repository = {**repository, **updates}
    if not uses_repository_context(current_store):
        current_store.product_git_repositories[repo_id] = repository
    audit_event = record_audit_event(
        current_store,
        event_type="product_git_repository.updated",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repo_id,
    )
    save_product_config_record(
        current_store,
        "product_git_repositories",
        repository,
        audit_event=audit_event,
    )
    return envelope(public_git_repository(repository), get_trace_id(request))


@router.delete("/api/product-git-repositories/{repo_id}")
def delete_product_git_repository(
    repo_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_record_write_store(store(request))
    if get_product_git_repository_record(current_store, repo_id) is None:
        raise api_error(404, "NOT_FOUND", "Product Git repository not found")
    if not uses_repository_context(current_store):
        del current_store.product_git_repositories[repo_id]
    audit_event = record_audit_event(
        current_store,
        event_type="product_git_repository.deleted",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repo_id,
    )
    delete_product_config_record(
        current_store,
        "product_git_repositories",
        repo_id,
        audit_event=audit_event,
    )
    return envelope({"deleted": True, "id": repo_id}, get_trace_id(request))
