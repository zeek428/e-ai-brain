from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from app.api.deps import api_error
from app.services.git_review_diff import enrich_code_review_preview, summarize_gitlab_change

GitLabRequestJson = Callable[[str, str, str], dict[str, Any]]
TokenResolver = Callable[[str, list[str]], str | None]


def gitlab_base_url(repository: dict[str, Any]) -> str | None:
    remote_url = str(repository.get("remote_url") or "").strip()
    if remote_url.startswith("git@") and ":" in remote_url:
        host = remote_url.split("@", 1)[1].split(":", 1)[0]
        return f"https://{host}"
    if remote_url:
        parsed = urlparse(remote_url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    configured_base_url = os.getenv("GITLAB_BASE_URL", "").strip()
    return configured_base_url.rstrip("/") if configured_base_url else None


def gitlab_access_token(
    repository: dict[str, Any],
    *,
    token_resolver: TokenResolver,
) -> str | None:
    credential_ref = str(repository.get("credential_ref") or "").strip()
    return token_resolver(credential_ref, ["GITLAB_READONLY_TOKEN"])


def gitlab_project_key(repository: dict[str, Any]) -> str:
    project_key = repository.get("project_id") or repository.get("project_path")
    if not project_key:
        raise api_error(
            400,
            "GITLAB_CONFIG_INVALID",
            "GitLab project_id or project_path is required",
        )
    return str(project_key)


def gitlab_request_json(
    base_url: str,
    token: str,
    path: str,
    *,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    request = UrlRequest(
        f"{base_url.rstrip('/')}{path}",
        headers={"Accept": "application/json", "PRIVATE-TOKEN": token},
        method="GET",
    )
    try:
        with opener(request, timeout=10) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            raise api_error(404, "GITLAB_MR_NOT_FOUND", "GitLab merge request not found") from exc
        if exc.code == 403:
            raise api_error(403, "FORBIDDEN", "GitLab merge request is not accessible") from exc
        if exc.code in {408, 429} or exc.code >= 500:
            raise api_error(
                503,
                "DEVOPS_SOURCE_UNAVAILABLE",
                "GitLab API source unavailable",
            ) from exc
        raise api_error(exc.code, "GITLAB_REQUEST_FAILED", "GitLab API request failed") from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise api_error(503, "DEVOPS_SOURCE_UNAVAILABLE", "GitLab API source unavailable") from exc


def gitlab_changes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    changes = payload.get("changes")
    if isinstance(changes, list):
        return [item for item in changes if isinstance(item, dict)]
    diffs = payload.get("diffs")
    if isinstance(diffs, list):
        return [item for item in diffs if isinstance(item, dict)]
    return []


def real_gitlab_preview(
    repository: dict[str, Any],
    mr_iid: int,
    *,
    request_json: GitLabRequestJson,
    token_resolver: TokenResolver,
) -> dict[str, Any]:
    base_url = gitlab_base_url(repository)
    if not base_url:
        raise api_error(
            400,
            "GITLAB_CONFIG_INVALID",
            "GitLab repository remote_url or GITLAB_BASE_URL is required",
        )
    token = gitlab_access_token(repository, token_resolver=token_resolver)
    if not token:
        raise api_error(
            400,
            "GITLAB_CREDENTIAL_UNAVAILABLE",
            "GitLab readonly credential is not available",
        )
    encoded_project = quote(gitlab_project_key(repository), safe="")
    mr_path = f"/api/v4/projects/{encoded_project}/merge_requests/{mr_iid}"
    changes_path = f"{mr_path}/changes"
    mr = request_json(base_url, token, mr_path)
    changes_payload = request_json(base_url, token, changes_path)
    changes_summary = [
        summarize_gitlab_change(change)
        for change in gitlab_changes(changes_payload)
    ]
    diff_refs = mr.get("diff_refs") if isinstance(mr.get("diff_refs"), dict) else {}
    base_sha = diff_refs.get("base_sha") or diff_refs.get("start_sha") or mr.get("sha")
    head_sha = diff_refs.get("head_sha") or mr.get("sha")
    project_path = repository.get("project_path") or str(repository.get("project_id") or "")
    return {
        "repository_id": repository["id"],
        "project_id": repository.get("project_id"),
        "project_path": project_path,
        "mr_iid": int(mr.get("iid") or mr_iid),
        "title": mr.get("title") or f"MR !{mr_iid}",
        "author": mr.get("author") or {},
        "source_branch": mr.get("source_branch"),
        "target_branch": mr.get("target_branch"),
        "base_sha": base_sha,
        "head_sha": head_sha,
        "diff_refs": diff_refs,
        "changed_file_count": len(changes_summary),
        "changed_files_summary": changes_summary,
        "web_url": mr.get("web_url"),
        "writeback_allowed": False,
    }


def gitlab_preview(
    repository: dict[str, Any],
    mr_iid: int,
    *,
    request_json: GitLabRequestJson,
    token_resolver: TokenResolver,
) -> dict[str, Any]:
    return enrich_code_review_preview(
        real_gitlab_preview(
            repository,
            mr_iid,
            request_json=request_json,
            token_resolver=token_resolver,
        )
    )
