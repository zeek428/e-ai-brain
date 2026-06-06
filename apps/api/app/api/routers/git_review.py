from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.git_review import (
    list_github_pull_requests_response,
    preview_github_pr_response,
    preview_gitlab_mr_response,
    snapshot_github_pr_response,
    snapshot_gitlab_mr_response,
)

router = APIRouter(tags=["git_review"])


class GitLabSnapshotRequest(BaseModel):
    requirement_id: str
    technical_solution_task_id: str


@router.get("/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview")
def preview_gitlab_mr(
    repository_id: str,
    mr_iid: int,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        preview_gitlab_mr_response(
            current_store=store(request),
            mr_iid=mr_iid,
            repository_id=repository_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot")
def snapshot_gitlab_mr(
    repository_id: str,
    mr_iid: int,
    request: Request,
    payload: GitLabSnapshotRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        snapshot_gitlab_mr_response(
            current_store=store(request),
            mr_iid=mr_iid,
            payload=payload,
            repository_id=repository_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/devops/github/pull-requests/{repository_id}")
def list_github_pull_requests(
    repository_id: str,
    request: Request,
    state: str = "open",
    limit: int = Query(default=20, ge=1, le=100),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_github_pull_requests_response(
            current_store=store(request),
            limit=limit,
            repository_id=repository_id,
            state=state,
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/devops/github/pull-requests/{repository_id}/{pr_number}/preview")
def preview_github_pr(
    repository_id: str,
    pr_number: int,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        preview_github_pr_response(
            current_store=store(request),
            pr_number=pr_number,
            repository_id=repository_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/devops/github/pull-requests/{repository_id}/{pr_number}/snapshot")
def snapshot_github_pr(
    repository_id: str,
    pr_number: int,
    request: Request,
    payload: GitLabSnapshotRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        snapshot_github_pr_response(
            current_store=store(request),
            payload=payload,
            pr_number=pr_number,
            repository_id=repository_id,
            user=user,
        ),
        get_trace_id(request),
    )
