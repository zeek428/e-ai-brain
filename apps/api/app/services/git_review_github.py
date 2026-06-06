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
from app.services.git_review_diff import enrich_code_review_preview, summarize_github_file

GitHubRequestJson = Callable[[str, str, str], dict[str, Any] | list[Any]]
TokenResolver = Callable[[str, list[str]], str | None]


def github_base_url(repository: dict[str, Any]) -> str | None:
    configured_base_url = os.getenv("GITHUB_BASE_URL", "").strip()
    if configured_base_url:
        return configured_base_url.rstrip("/")
    remote_url = str(repository.get("remote_url") or "").strip()
    host = ""
    if remote_url.startswith("git@") and ":" in remote_url:
        host = remote_url.split("@", 1)[1].split(":", 1)[0]
    elif remote_url:
        parsed = urlparse(remote_url)
        host = parsed.netloc
    if host in {"github.com", "www.github.com"}:
        return "https://api.github.com"
    if host:
        return f"https://{host}/api/v3"
    return "https://api.github.com"


def github_access_token(
    repository: dict[str, Any],
    *,
    token_resolver: TokenResolver,
) -> str | None:
    credential_ref = str(repository.get("credential_ref") or "").strip()
    return token_resolver(
        credential_ref,
        ["GITHUB_READONLY_TOKEN", "GITHUB_TOKEN"],
    )


def clean_repository_path(value: str) -> str:
    cleaned = value.strip().strip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    return cleaned


def github_repository_path(repository: dict[str, Any]) -> str:
    project_path = clean_repository_path(str(repository.get("project_path") or ""))
    if project_path and not project_path.startswith("Users/") and len(project_path.split("/")) == 2:
        return project_path
    remote_url = str(repository.get("remote_url") or "").strip()
    candidate = ""
    if remote_url.startswith("git@") and ":" in remote_url:
        candidate = remote_url.split(":", 1)[1]
    elif remote_url:
        parsed = urlparse(remote_url)
        candidate = parsed.path
    candidate = clean_repository_path(candidate)
    if len(candidate.split("/")) == 2:
        return candidate
    raise api_error(
        400,
        "GITHUB_CONFIG_INVALID",
        "GitHub repository owner/repo path is required",
    )


def github_request_json(base_url: str, token: str, path: str) -> dict[str, Any] | list[Any]:
    request = UrlRequest(
        f"{base_url.rstrip('/')}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            raise api_error(404, "GITHUB_PR_NOT_FOUND", "GitHub pull request not found") from exc
        if exc.code == 403:
            raise api_error(403, "FORBIDDEN", "GitHub pull request is not accessible") from exc
        if exc.code in {408, 429} or exc.code >= 500:
            raise api_error(
                503,
                "DEVOPS_SOURCE_UNAVAILABLE",
                "GitHub API source unavailable",
            ) from exc
        raise api_error(exc.code, "GITHUB_REQUEST_FAILED", "GitHub API request failed") from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise api_error(503, "DEVOPS_SOURCE_UNAVAILABLE", "GitHub API source unavailable") from exc


def github_pull_request_summary(
    repository: dict[str, Any],
    *,
    owner_repo: str,
    pull_request: dict[str, Any],
) -> dict[str, Any]:
    user = pull_request.get("user") if isinstance(pull_request.get("user"), dict) else {}
    head = pull_request.get("head") if isinstance(pull_request.get("head"), dict) else {}
    base = pull_request.get("base") if isinstance(pull_request.get("base"), dict) else {}
    return {
        "author": {
            "username": user.get("login") or "-",
            "name": user.get("name") or user.get("login") or "-",
        },
        "base_sha": base.get("sha") or pull_request.get("base_sha"),
        "created_at": pull_request.get("created_at"),
        "head_sha": head.get("sha") or pull_request.get("head_sha"),
        "number": int(pull_request.get("number") or 0),
        "project_path": owner_repo,
        "repository_id": repository["id"],
        "source_branch": head.get("ref"),
        "state": pull_request.get("state"),
        "target_branch": base.get("ref"),
        "title": pull_request.get("title") or f"PR #{pull_request.get('number')}",
        "updated_at": pull_request.get("updated_at"),
        "web_url": pull_request.get("html_url"),
        "writeback_allowed": False,
    }


def github_pull_requests(
    repository: dict[str, Any],
    *,
    request_json: GitHubRequestJson,
    state: str,
    limit: int,
    token_resolver: TokenResolver,
) -> list[dict[str, Any]]:
    base_url = github_base_url(repository)
    if not base_url:
        raise api_error(
            400,
            "GITHUB_CONFIG_INVALID",
            "GitHub repository remote_url or GITHUB_BASE_URL is required",
        )
    token = github_access_token(repository, token_resolver=token_resolver)
    if not token:
        raise api_error(
            400,
            "GITHUB_CREDENTIAL_UNAVAILABLE",
            "GitHub readonly credential is not available",
        )
    owner_repo = github_repository_path(repository)
    encoded_owner_repo = quote(owner_repo, safe="/")
    pull_requests = request_json(
        base_url,
        token,
        f"/repos/{encoded_owner_repo}/pulls?state={state}&per_page={limit}",
    )
    if not isinstance(pull_requests, list):
        raise api_error(503, "DEVOPS_SOURCE_UNAVAILABLE", "GitHub API source unavailable")
    return [
        github_pull_request_summary(repository, owner_repo=owner_repo, pull_request=item)
        for item in pull_requests
        if isinstance(item, dict)
    ]


def github_preview(
    repository: dict[str, Any],
    pr_number: int,
    *,
    request_json: GitHubRequestJson,
    token_resolver: TokenResolver,
) -> dict[str, Any]:
    base_url = github_base_url(repository)
    if not base_url:
        raise api_error(
            400,
            "GITHUB_CONFIG_INVALID",
            "GitHub repository remote_url or GITHUB_BASE_URL is required",
        )
    token = github_access_token(repository, token_resolver=token_resolver)
    if not token:
        raise api_error(
            400,
            "GITHUB_CREDENTIAL_UNAVAILABLE",
            "GitHub readonly credential is not available",
        )
    owner_repo = github_repository_path(repository)
    encoded_owner_repo = quote(owner_repo, safe="/")
    pr_path = f"/repos/{encoded_owner_repo}/pulls/{pr_number}"
    files_path = f"{pr_path}/files?per_page=100"
    pr = request_json(base_url, token, pr_path)
    files_payload = request_json(base_url, token, files_path)
    if not isinstance(pr, dict) or not isinstance(files_payload, list):
        raise api_error(503, "DEVOPS_SOURCE_UNAVAILABLE", "GitHub API source unavailable")
    user = pr.get("user") if isinstance(pr.get("user"), dict) else {}
    head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
    base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
    base_sha = base.get("sha") or pr.get("base_sha")
    head_sha = head.get("sha") or pr.get("head_sha")
    return enrich_code_review_preview(
        {
            "repository_id": repository["id"],
            "project_id": repository.get("project_id"),
            "project_path": owner_repo,
            "mr_iid": int(pr.get("number") or pr_number),
            "title": pr.get("title") or f"PR #{pr_number}",
            "author": {
                "username": user.get("login") or "-",
                "name": user.get("name") or user.get("login") or "-",
            },
            "source_branch": head.get("ref"),
            "target_branch": base.get("ref"),
            "base_sha": base_sha,
            "head_sha": head_sha,
            "diff_refs": {"base_sha": base_sha, "head_sha": head_sha},
            "changed_file_count": len(files_payload),
            "changed_files_summary": [
                summarize_github_file(file_item)
                for file_item in files_payload
                if isinstance(file_item, dict)
            ],
            "web_url": pr.get("html_url"),
            "writeback_allowed": False,
        }
    )
