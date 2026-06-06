from __future__ import annotations

from dataclasses import replace

from app.core.production_readiness import ReadinessOptions, run_production_readiness_checks


def _successful_runner(commands: list[list[str]]):
    def run(command: list[str], cwd: str | None = None):
        commands.append(command)
        joined = " ".join(command)
        if "ps --services" in joined:
            return 0, "api\nweb\npostgres\nredis\n", ""
        if "redis-cli ping" in joined:
            return 0, "PONG\n", ""
        if "pg_extension" in joined:
            return 0, "pgcrypto\nvector\n", ""
        return 0, "", ""

    return run


def _successful_http_requests(requests: list[dict]):
    def request(method: str, url: str, *, headers=None, json_body=None):
        requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers or {},
                "json_body": json_body,
            }
        )
        if url.endswith("/health"):
            return 200, {
                "status": "ok",
                "postgres": "ok",
                "redis": "ok",
                "model_gateway": "not_configured",
                "trace_id": "trace_readiness",
            }
        if url.endswith("/api/auth/login"):
            return 200, {"data": {"access_token": "readiness-token"}}
        if url.endswith("/api/system/model-gateway-configs"):
            return 200, {
                "data": {
                    "items": [
                        {
                            "id": "model_gateway_config_001",
                            "api_key_configured": True,
                            "is_default": True,
                            "status": "active",
                        }
                    ]
                }
            }
        if (
            url == "http://web.test"
            or url.startswith("http://web.test/")
            or url == "http://localhost:5173"
            or url.startswith("http://localhost:5173/")
        ):
            return 200, {
                "raw": "<html><body><div id=\"root\">Enterprise AI Brain</div></body></html>"
            }
        if url.endswith("/api/requirements?page=1&page_size=1"):
            return 200, {
                "data": {
                    "items": [],
                    "page": 1,
                    "page_size": 1,
                    "performance": {"duration_ms": 3, "result_count": 0, "total": 0},
                    "query": {"filters": {}, "name": "requirements"},
                    "total": 0,
                },
                "trace_id": "trace_requirements",
            }
        if url.endswith("/api/ai-tasks?page=1&page_size=1"):
            return 200, {
                "data": {
                    "items": [],
                    "page": 1,
                    "page_size": 1,
                    "performance": {"duration_ms": 4, "result_count": 0, "total": 0},
                    "query": {"filters": {}, "name": "ai_tasks"},
                    "total": 0,
                },
                "trace_id": "trace_tasks",
            }
        if url.endswith("/api/bugs?page=1&page_size=1"):
            return 200, {
                "data": {
                    "items": [],
                    "page": 1,
                    "page_size": 1,
                    "performance": {"duration_ms": 5, "result_count": 0, "total": 0},
                    "query": {"filters": {}, "name": "bugs"},
                    "total": 0,
                },
                "trace_id": "trace_bugs",
            }
        if url.endswith("/api/insights/items?page=1&page_size=1"):
            return 200, {
                "data": {
                    "items": [],
                    "page": 1,
                    "page_size": 1,
                    "performance": {"duration_ms": 6, "result_count": 0, "total": 0},
                    "query": {"filters": {}, "name": "user_insights"},
                    "total": 0,
                },
                "trace_id": "trace_insights",
            }
        if url.endswith("/api/devops/operational-metrics?page=1&page_size=1"):
            return 200, {
                "data": {
                    "items": [],
                    "page": 1,
                    "page_size": 1,
                    "performance": {"duration_ms": 7, "result_count": 0, "total": 0},
                    "query": {"filters": {}, "name": "devops_operational_metrics"},
                    "total": 0,
                },
                "trace_id": "trace_devops",
            }
        if url.endswith("/preview"):
            return 200, {"data": {"mr_iid": 42, "writeback_allowed": False}}
        if url.endswith("/snapshot"):
            return 200, {
                "data": {
                    "id": "snapshot_001",
                    "diff_size_bytes": 128,
                    "writeback_allowed": False,
                }
            }
        raise AssertionError(f"unexpected request: {method} {url}")

    return request


def _strict_options() -> ReadinessOptions:
    return ReadinessOptions(
        api_base_url="http://api.test",
        gitlab_mr_iid="42",
        gitlab_repository_id="repository_001",
        gitlab_requirement_id="requirement_001",
        gitlab_technical_solution_task_id="task_001",
        password="admin123",
        project_root="/repo",
        web_base_url="http://web.test",
        username="admin@example.com",
    )


def test_production_readiness_checks_cover_compose_health_database_gateway_and_gitlab():
    commands: list[list[str]] = []
    requests: list[dict] = []

    report = run_production_readiness_checks(
        _strict_options(),
        run_command=_successful_runner(commands),
        http_request=_successful_http_requests(requests),
    )

    assert report.ok is True
    assert [item.name for item in report.results] == [
        "compose_config",
        "compose_services",
        "api_health",
        "redis_ping",
        "postgres_extensions",
        "web_shell",
        "auth_token",
        "model_gateway_config",
        "core_list_requirements",
        "core_list_tasks",
        "core_list_bugs",
        "core_list_insights",
        "core_list_devops",
        "gitlab_mr_preview",
        "gitlab_mr_snapshot",
    ]
    assert ["docker", "compose", "config", "--quiet"] in commands
    assert any("pg_extension" in " ".join(command) for command in commands)
    assert any(item["url"] == "http://web.test" for item in requests)
    assert any(item["url"].endswith("/api/system/model-gateway-configs") for item in requests)
    assert requests[-1]["json_body"] == {
        "requirement_id": "requirement_001",
        "technical_solution_task_id": "task_001",
    }


def test_production_readiness_can_rebuild_compose_stack_before_checks():
    commands: list[list[str]] = []

    report = run_production_readiness_checks(
        replace(_strict_options(), rebuild=True),
        run_command=_successful_runner(commands),
        http_request=_successful_http_requests([]),
    )

    assert report.ok is True
    assert report.results[0].name == "compose_rebuild"
    assert commands[0] == ["docker", "compose", "up", "-d", "--build"]


def test_production_readiness_can_run_web_page_smoke_gate():
    commands: list[list[str]] = []

    report = run_production_readiness_checks(
        replace(_strict_options(), web_smoke=True),
        run_command=_successful_runner(commands),
        http_request=_successful_http_requests([]),
    )

    assert report.ok is True
    assert [item.name for item in report.results][-3:] == [
        "web_page_smoke",
        "gitlab_mr_preview",
        "gitlab_mr_snapshot",
    ]
    smoke_command = next(command for command in commands if "web_page_smoke.mjs" in command[1])
    assert smoke_command[:2] == ["node", "/repo/scripts/web_page_smoke.mjs"]
    assert "--api-base-url" in smoke_command
    assert "--web-base-url" in smoke_command
    assert "--username" in smoke_command
    assert "--password" in smoke_command
    assert "--expect-text" in smoke_command
    expect_index = smoke_command.index("--expect-text")
    assert smoke_command[expect_index + 1] == "/system/roles=系统管理员"


def test_production_readiness_fails_when_model_gateway_response_exposes_secret_fields():
    def leaking_http_request(method: str, url: str, *, headers=None, json_body=None):
        if url.endswith("/api/system/model-gateway-configs"):
            return 200, {
                "data": {
                    "items": [
                        {
                            "api_key": "sk-leaked",
                            "api_key_configured": True,
                            "id": "model_gateway_config_001",
                            "is_default": True,
                            "status": "active",
                        }
                    ]
                }
            }
        return _successful_http_requests([])(method, url, headers=headers, json_body=json_body)

    report = run_production_readiness_checks(
        _strict_options(),
        run_command=_successful_runner([]),
        http_request=leaking_http_request,
    )

    failed = [item for item in report.results if item.name == "model_gateway_config"][0]
    assert report.ok is False
    assert failed.ok is False
    assert "secret field" in failed.detail


def test_production_readiness_requires_gitlab_inputs_for_strict_gate():
    options = ReadinessOptions(
        api_base_url="http://api.test",
        password="admin123",
        project_root="/repo",
        username="admin@example.com",
    )

    report = run_production_readiness_checks(
        options,
        run_command=_successful_runner([]),
        http_request=_successful_http_requests([]),
    )

    failed = [item for item in report.results if item.name == "gitlab_mr_preview"][0]
    assert report.ok is False
    assert failed.ok is False
    assert "READINESS_GITLAB_REPOSITORY_ID" in failed.detail
