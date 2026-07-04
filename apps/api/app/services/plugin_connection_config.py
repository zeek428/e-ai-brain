from __future__ import annotations

from typing import Any
from urllib.parse import quote, unquote, urlparse

from app.api.deps import api_error


def ensure_plugin_connection_auth_requirements(
    *,
    auth_config: dict[str, Any] | None,
    auth_type: str,
    plugin: dict[str, Any],
) -> None:
    plugin_code = plugin.get("code")
    if auth_type == "url_key":
        secret_ref = (auth_config or {}).get("secret_ref")
        if not isinstance(secret_ref, str) or not secret_ref.strip():
            raise api_error(400, "VALIDATION_ERROR", "URL key secret_ref is required")
    if str(plugin_code or "").startswith("dingtalk_"):
        if auth_type != "url_key":
            raise api_error(
                400,
                "VALIDATION_ERROR",
                "DingTalk MCP connection requires url_key auth_type",
            )
        query_key = (auth_config or {}).get("query_key") or "key"
        if not isinstance(query_key, str) or not query_key.strip():
            raise api_error(400, "VALIDATION_ERROR", "DingTalk URL key query_key is required")
        return
    if plugin_code == "github":
        if auth_type != "bearer":
            raise api_error(400, "VALIDATION_ERROR", "GitHub connection requires bearer auth_type")
        token_ref = (auth_config or {}).get("token_ref")
        if not isinstance(token_ref, str) or not token_ref.strip():
            raise api_error(400, "VALIDATION_ERROR", "GitHub token_ref is required")
        return
    if plugin_code != "gitlab":
        return
    if auth_type != "api_key_header":
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "GitLab connection requires api_key_header auth_type",
        )
    header_name = (auth_config or {}).get("header_name")
    if not isinstance(header_name, str) or not header_name.strip():
        raise api_error(400, "VALIDATION_ERROR", "GitLab header_name is required")
    secret_ref = (auth_config or {}).get("secret_ref")
    if not isinstance(secret_ref, str) or not secret_ref.strip():
        raise api_error(400, "VALIDATION_ERROR", "GitLab secret_ref is required")


def parse_git_repository_address(value: Any) -> dict[str, str] | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw_value = value.strip()
    path = raw_value
    if "@" in raw_value and ":" in raw_value and "://" not in raw_value:
        path = raw_value.split(":", 1)[1]
    else:
        first_segment = raw_value.split("/", 1)[0]
        looks_like_url = "://" in raw_value or "." in first_segment
        if looks_like_url:
            parsed = urlparse(raw_value if "://" in raw_value else f"https://{raw_value}")
            path = parsed.path or raw_value
    segments = [segment for segment in path.strip("/").split("/") if segment]
    if segments and segments[0] == "repos":
        segments = segments[1:]
    if len(segments) < 2:
        return None
    owner = segments[0].strip()
    repo = segments[1].removesuffix(".git").strip()
    if not owner or not repo:
        return None
    return {"owner": owner, "repo": repo}


def normalize_github_connection_request_config(
    request_config: dict[str, Any],
    plugin: dict[str, Any],
) -> dict[str, Any]:
    if plugin.get("code") != "github":
        return request_config
    query = request_config.get("query")
    if not isinstance(query, dict):
        return request_config
    parsed = parse_git_repository_address(query.get("repository_url"))
    if not parsed:
        return request_config
    query_without_repository_url = {
        key: value for key, value in query.items() if key != "repository_url"
    }
    return {
        **request_config,
        "query": {
            **query_without_repository_url,
            "owner": parsed["owner"],
            "repo": parsed["repo"],
        },
    }


def parse_gitlab_project_address(value: Any) -> dict[str, str] | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw_value = value.strip()
    endpoint_url = ""
    path = raw_value
    if "@" in raw_value and ":" in raw_value and "://" not in raw_value:
        host_part, path = raw_value.split(":", 1)
        host = host_part.rsplit("@", 1)[-1].strip()
        endpoint_url = f"https://{host}" if host else ""
    else:
        first_segment = raw_value.split("/", 1)[0]
        looks_like_url = (
            "://" in raw_value
            or "." in first_segment
            or ":" in first_segment
            or first_segment == "localhost"
        )
        if looks_like_url:
            parsed = urlparse(raw_value if "://" in raw_value else f"http://{raw_value}")
            path = parsed.path or raw_value
            if parsed.scheme and parsed.netloc:
                endpoint_url = f"{parsed.scheme}://{parsed.netloc}"
    path = path.split("/-/", 1)[0]
    segments = [segment for segment in path.strip("/").split("/") if segment]
    if len(segments) >= 4 and segments[0] == "api" and segments[2] == "projects":
        segments = [unquote(segments[3])]
    if not segments:
        return None
    project_path = unquote("/".join(segments)).removesuffix(".git").strip("/")
    if not project_path or "/" not in project_path:
        return None
    return {
        "endpoint_url": endpoint_url,
        "project_id": quote(project_path, safe=""),
        "project_path": project_path,
    }


def normalize_gitlab_connection_config(
    *,
    endpoint_url: str,
    request_config: dict[str, Any],
    plugin: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    if plugin.get("code") != "gitlab":
        return endpoint_url, request_config
    query = request_config.get("query")
    if not isinstance(query, dict):
        return endpoint_url, request_config
    parsed = parse_gitlab_project_address(
        query.get("gitlab_project_url") or query.get("repository_url")
    )
    if not parsed:
        return endpoint_url, request_config
    query_without_project_url = {
        key: value
        for key, value in query.items()
        if key not in {"gitlab_project_url", "repository_url"}
    }
    project_path = parsed["project_path"]
    return (
        parsed["endpoint_url"] or endpoint_url,
        {
            **request_config,
            "query": {
                **query_without_project_url,
                "api_version": str(query_without_project_url.get("api_version") or "v4"),
                "group_id": project_path.split("/", 1)[0],
                "project_id": parsed["project_id"],
                "project_path": project_path,
            },
        },
    )
