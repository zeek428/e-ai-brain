from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CommandRunner = Callable[..., tuple[int, str, str]]
HttpRequest = Callable[..., tuple[int, dict[str, Any]]]


@dataclass(frozen=True)
class ReadinessOptions:
    api_base_url: str = "http://localhost:8000"
    bearer_token: str | None = None
    docker_bin: str = "docker"
    gitlab_mr_iid: str | None = None
    gitlab_repository_id: str | None = None
    gitlab_requirement_id: str | None = None
    gitlab_technical_solution_task_id: str | None = None
    password: str | None = None
    postgres_db: str = "ai_brain"
    postgres_user: str = "ai_brain"
    project_root: str | None = None
    rebuild: bool = False
    web_base_url: str = "http://localhost:5173"
    web_smoke: bool = False
    web_smoke_command: tuple[str, ...] | None = None
    username: str | None = None


@dataclass(frozen=True)
class GateResult:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class ReadinessReport:
    results: list[GateResult]

    @property
    def ok(self) -> bool:
        return all(item.ok for item in self.results)


def _default_run_command(command: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def default_docker_bin() -> str:
    docker = shutil.which("docker")
    if docker:
        return docker
    docker_desktop = Path("/Applications/Docker.app/Contents/Resources/bin/docker")
    if docker_desktop.exists():
        return str(docker_desktop)
    return "docker"


def _docker_command(options: ReadinessOptions, *args: str) -> list[str]:
    return [options.docker_bin, *args]


def _default_http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    data = None
    request_headers = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            response_text = response.read().decode("utf-8")
            try:
                payload = json.loads(response_text)
            except json.JSONDecodeError:
                payload = {"raw": response_text}
            return int(response.status), payload
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {"detail": str(exc)}
        return int(exc.code), payload
    except (OSError, URLError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return 0, {"detail": str(exc)}


def _command_gate(
    name: str,
    command: list[str],
    *,
    run_command: CommandRunner,
    project_root: str | None,
    expected_text: str | None = None,
) -> GateResult:
    code, stdout, stderr = run_command(command, project_root)
    if code != 0:
        detail = (stderr or stdout or f"exit_code={code}").strip()
        return GateResult(name, False, detail)
    if expected_text is not None and expected_text not in stdout:
        return GateResult(name, False, f"expected {expected_text!r}, got {stdout.strip()!r}")
    return GateResult(name, True, "ok")


def _compose_services_gate(
    options: ReadinessOptions,
    *,
    run_command: CommandRunner,
    project_root: str | None,
) -> GateResult:
    code, stdout, stderr = run_command(
        _docker_command(options, "compose", "ps", "--services", "--filter", "status=running"),
        project_root,
    )
    if code != 0:
        return GateResult("compose_services", False, (stderr or stdout).strip())
    running = {line.strip() for line in stdout.splitlines() if line.strip()}
    missing = sorted({"api", "web", "postgres", "redis"} - running)
    if missing:
        return GateResult(
            "compose_services",
            False,
            f"missing running services: {', '.join(missing)}",
        )
    return GateResult("compose_services", True, "api, web, postgres and redis are running")


def _compose_rebuild_gate(
    options: ReadinessOptions,
    *,
    run_command: CommandRunner,
    project_root: str | None,
) -> GateResult:
    code, stdout, stderr = run_command(
        _docker_command(options, "compose", "up", "-d", "--build"),
        project_root,
    )
    if code != 0:
        return GateResult("compose_rebuild", False, (stderr or stdout).strip())
    return GateResult("compose_rebuild", True, "docker compose stack rebuilt and started")


def _api_url(options: ReadinessOptions, path: str) -> str:
    return f"{options.api_base_url.rstrip('/')}{path}"


def _web_url(options: ReadinessOptions, path: str = "") -> str:
    return f"{options.web_base_url.rstrip('/')}{path}"


def _api_health_gate(
    options: ReadinessOptions,
    *,
    http_request: Callable[..., tuple[int, dict[str, Any]]],
) -> GateResult:
    status, payload = http_request("GET", _api_url(options, "/health"))
    if status != 200:
        return GateResult("api_health", False, f"status={status}, payload={payload}")
    if payload.get("status") != "ok":
        return GateResult("api_health", False, f"api status is {payload.get('status')!r}")
    if payload.get("postgres") != "ok" or payload.get("redis") != "ok":
        return GateResult("api_health", False, "postgres or redis health is not ok")
    if not payload.get("trace_id"):
        return GateResult("api_health", False, "missing trace_id")
    return GateResult("api_health", True, "ok")


def _web_shell_gate(
    options: ReadinessOptions,
    *,
    http_request: Callable[..., tuple[int, dict[str, Any]]],
) -> GateResult:
    status, payload = http_request("GET", _web_url(options))
    raw = payload.get("raw") if isinstance(payload, dict) else None
    if status != 200:
        return GateResult("web_shell", False, f"status={status}, payload={payload}")
    if not isinstance(raw, str) or "<html" not in raw.lower():
        return GateResult("web_shell", False, "web shell did not return HTML")
    if "id=\"root\"" not in raw and "id='root'" not in raw and "Enterprise AI Brain" not in raw:
        return GateResult("web_shell", False, "web shell is missing root mount or product title")
    return GateResult("web_shell", True, "web shell returned HTML")


def _web_smoke_command(options: ReadinessOptions) -> list[str]:
    if options.web_smoke_command is not None:
        return list(options.web_smoke_command)
    project_root = Path(options.project_root or ".")
    command = [
        "node",
        str(project_root / "scripts" / "web_page_smoke.mjs"),
        "--api-base-url",
        options.api_base_url,
        "--web-base-url",
        options.web_base_url,
        "--expect-text",
        "/system/roles=系统管理员",
    ]
    if options.bearer_token:
        command.extend(["--bearer-token", options.bearer_token])
    elif options.username and options.password:
        command.extend(["--username", options.username, "--password", options.password])
    return command


def _web_page_smoke_gate(
    options: ReadinessOptions,
    *,
    run_command: CommandRunner,
    project_root: str | None,
) -> GateResult:
    command = _web_smoke_command(options)
    code, stdout, stderr = run_command(command, project_root)
    detail = (stderr or stdout or f"exit_code={code}").strip()
    if code != 0:
        return GateResult("web_page_smoke", False, detail)
    return GateResult("web_page_smoke", True, detail or "ok")


def _postgres_extensions_gate(
    options: ReadinessOptions,
    *,
    run_command: CommandRunner,
    project_root: str | None,
) -> GateResult:
    sql = (
        "select extname from pg_extension "
        "where extname in ('vector','pgcrypto') order by extname;"
    )
    code, stdout, stderr = run_command(
        [
            *_docker_command(options, "compose", "exec", "-T", "postgres"),
            "psql",
            "-U",
            options.postgres_user,
            "-d",
            options.postgres_db,
            "-Atc",
            sql,
        ],
        project_root,
    )
    if code != 0:
        return GateResult("postgres_extensions", False, (stderr or stdout).strip())
    extensions = {line.strip() for line in stdout.splitlines() if line.strip()}
    missing = sorted({"pgcrypto", "vector"} - extensions)
    if missing:
        return GateResult(
            "postgres_extensions",
            False,
            f"missing extensions: {', '.join(missing)}",
        )
    return GateResult("postgres_extensions", True, "pgcrypto and vector are installed")


def _auth_headers(
    options: ReadinessOptions,
    *,
    http_request: Callable[..., tuple[int, dict[str, Any]]],
) -> tuple[GateResult, dict[str, str] | None]:
    if options.bearer_token:
        return GateResult("auth_token", True, "using provided bearer token"), {
            "Authorization": f"Bearer {options.bearer_token}",
        }
    if not options.username or not options.password:
        return GateResult(
            "auth_token",
            False,
            "provide READINESS_BEARER_TOKEN or READINESS_USERNAME/READINESS_PASSWORD",
        ), None
    status, payload = http_request(
        "POST",
        _api_url(options, "/api/auth/login"),
        json_body={"username": options.username, "password": options.password},
    )
    token = payload.get("data", {}).get("access_token") if isinstance(payload, dict) else None
    if status != 200 or not token:
        return GateResult("auth_token", False, f"status={status}, payload={payload}"), None
    return GateResult("auth_token", True, "ok"), {"Authorization": f"Bearer {token}"}


def _model_gateway_config_gate(
    options: ReadinessOptions,
    *,
    headers: dict[str, str],
    http_request: Callable[..., tuple[int, dict[str, Any]]],
) -> GateResult:
    status, payload = http_request(
        "GET",
        _api_url(options, "/api/system/model-gateway-configs"),
        headers=headers,
    )
    if status != 200:
        return GateResult("model_gateway_config", False, f"status={status}, payload={payload}")
    items = payload.get("data", {}).get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return GateResult("model_gateway_config", False, "response is missing data.items")
    secret_fields = {"api_key", "api_key_prefix", "api_key_suffix", "secret", "token"}
    for item in items:
        if not isinstance(item, dict):
            continue
        leaked = sorted(secret_fields & set(item))
        if leaked:
            return GateResult(
                "model_gateway_config",
                False,
                f"response exposes secret field(s): {', '.join(leaked)}",
            )
    configured_default = any(
        item.get("api_key_configured") is True
        and item.get("is_default") is True
        and item.get("status") == "active"
        for item in items
        if isinstance(item, dict)
    )
    if not configured_default:
        return GateResult(
            "model_gateway_config",
            False,
            "missing active default model gateway with api_key_configured=true",
        )
    return GateResult("model_gateway_config", True, "active default gateway is configured")


def _core_list_gate(
    name: str,
    path: str,
    options: ReadinessOptions,
    *,
    headers: dict[str, str],
    http_request: Callable[..., tuple[int, dict[str, Any]]],
) -> GateResult:
    status, payload = http_request("GET", _api_url(options, path), headers=headers)
    if status != 200:
        return GateResult(name, False, f"status={status}, payload={payload}")
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    if not isinstance(data.get("items"), list):
        return GateResult(name, False, "response is missing data.items")
    if "total" not in data:
        return GateResult(name, False, "response is missing data.total")
    if not payload.get("trace_id"):
        return GateResult(name, False, "response is missing trace_id")
    query = data.get("query")
    if not isinstance(query, dict) or "filters" not in query:
        return GateResult(name, False, "response is missing query.filters")
    performance = data.get("performance")
    if not isinstance(performance, dict) or "duration_ms" not in performance:
        return GateResult(name, False, "response is missing performance.duration_ms")
    if "result_count" not in performance or "total" not in performance:
        return GateResult(name, False, "response is missing performance row counts")
    return GateResult(name, True, "ok")


def _missing_gitlab_options(options: ReadinessOptions) -> list[str]:
    missing = []
    if not options.gitlab_repository_id:
        missing.append("READINESS_GITLAB_REPOSITORY_ID")
    if not options.gitlab_mr_iid:
        missing.append("READINESS_GITLAB_MR_IID")
    if not options.gitlab_requirement_id:
        missing.append("READINESS_REQUIREMENT_ID")
    if not options.gitlab_technical_solution_task_id:
        missing.append("READINESS_TECHNICAL_SOLUTION_TASK_ID")
    return missing


def _gitlab_preview_gate(
    options: ReadinessOptions,
    *,
    headers: dict[str, str],
    http_request: Callable[..., tuple[int, dict[str, Any]]],
) -> GateResult:
    missing = _missing_gitlab_options(options)
    if missing:
        return GateResult(
            "gitlab_mr_preview",
            False,
            f"missing required env: {', '.join(missing)}",
        )
    path = (
        "/api/devops/gitlab/merge-requests/"
        f"{options.gitlab_repository_id}/{options.gitlab_mr_iid}/preview"
    )
    status, payload = http_request("GET", _api_url(options, path), headers=headers)
    if status != 200:
        return GateResult("gitlab_mr_preview", False, f"status={status}, payload={payload}")
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    if data.get("writeback_allowed") is not False:
        return GateResult("gitlab_mr_preview", False, "preview is not explicitly read-only")
    return GateResult("gitlab_mr_preview", True, "read-only preview returned")


def _gitlab_snapshot_gate(
    options: ReadinessOptions,
    *,
    headers: dict[str, str],
    http_request: Callable[..., tuple[int, dict[str, Any]]],
) -> GateResult:
    path = (
        "/api/devops/gitlab/merge-requests/"
        f"{options.gitlab_repository_id}/{options.gitlab_mr_iid}/snapshot"
    )
    status, payload = http_request(
        "POST",
        _api_url(options, path),
        headers=headers,
        json_body={
            "requirement_id": options.gitlab_requirement_id,
            "technical_solution_task_id": options.gitlab_technical_solution_task_id,
        },
    )
    if status != 200:
        return GateResult("gitlab_mr_snapshot", False, f"status={status}, payload={payload}")
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    if not data.get("id"):
        return GateResult("gitlab_mr_snapshot", False, "snapshot response is missing id")
    if data.get("writeback_allowed") is not False:
        return GateResult("gitlab_mr_snapshot", False, "snapshot is not explicitly read-only")
    return GateResult("gitlab_mr_snapshot", True, "read-only snapshot returned")


def run_production_readiness_checks(
    options: ReadinessOptions,
    *,
    run_command: CommandRunner = _default_run_command,
    http_request: Callable[..., tuple[int, dict[str, Any]]] = _default_http_request,
) -> ReadinessReport:
    results = []
    if options.rebuild:
        results.append(
            _compose_rebuild_gate(
                options,
                run_command=run_command,
                project_root=options.project_root,
            )
        )
        if not results[-1].ok:
            return ReadinessReport(results)
    results.extend(
        [
            _command_gate(
                "compose_config",
                _docker_command(options, "compose", "config", "--quiet"),
                run_command=run_command,
                project_root=options.project_root,
            ),
            _compose_services_gate(
                options,
                run_command=run_command,
                project_root=options.project_root,
            ),
            _api_health_gate(options, http_request=http_request),
            _command_gate(
                "redis_ping",
                _docker_command(options, "compose", "exec", "-T", "redis", "redis-cli", "ping"),
                run_command=run_command,
                project_root=options.project_root,
                expected_text="PONG",
            ),
            _postgres_extensions_gate(
                options,
                run_command=run_command,
                project_root=options.project_root,
            ),
            _web_shell_gate(options, http_request=http_request),
        ]
    )
    auth_result, headers = _auth_headers(options, http_request=http_request)
    results.append(auth_result)
    if headers is None:
        return ReadinessReport(results)
    results.append(
        _model_gateway_config_gate(options, headers=headers, http_request=http_request)
    )
    results.extend(
        [
            _core_list_gate(
                "core_list_requirements",
                "/api/requirements?page=1&page_size=1",
                options,
                headers=headers,
                http_request=http_request,
            ),
            _core_list_gate(
                "core_list_tasks",
                "/api/ai-tasks?page=1&page_size=1",
                options,
                headers=headers,
                http_request=http_request,
            ),
            _core_list_gate(
                "core_list_bugs",
                "/api/bugs?page=1&page_size=1",
                options,
                headers=headers,
                http_request=http_request,
            ),
            _core_list_gate(
                "core_list_insights",
                "/api/insights/items?page=1&page_size=1",
                options,
                headers=headers,
                http_request=http_request,
            ),
            _core_list_gate(
                "core_list_devops",
                "/api/devops/operational-metrics?page=1&page_size=1",
                options,
                headers=headers,
                http_request=http_request,
            ),
        ]
    )
    if options.web_smoke:
        results.append(
            _web_page_smoke_gate(
                options,
                run_command=run_command,
                project_root=options.project_root,
            )
        )
    results.append(_gitlab_preview_gate(options, headers=headers, http_request=http_request))
    if results[-1].ok:
        results.append(_gitlab_snapshot_gate(options, headers=headers, http_request=http_request))
    return ReadinessReport(results)
