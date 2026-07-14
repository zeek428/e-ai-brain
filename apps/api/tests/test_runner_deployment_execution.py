import json
import sys
import zipfile
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def runner_namespace(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    app.state.store.reset()
    headers = auth_headers()
    created = client.post(
        "/api/system/ai-executor-runners",
        json={
            "capabilities": ["deployment"],
            "executor_types": ["codex"],
            "name": "部署 Runner",
            "runner_token": "deployment-token",
            "trust_domain": "deployment",
        },
        headers=headers,
    ).json()["data"]
    package = client.get(
        f"/api/system/ai-executor-runners/{created['id']}/install-package"
        "?target_os=manual&arch=universal&install_mode=manual",
        headers=headers,
    )
    with zipfile.ZipFile(BytesIO(package.content)) as archive:
        config = json.loads(archive.read("runner_config.json").decode("utf-8"))
        runner_agent = archive.read("runner_agent.py").decode("utf-8")
    config["deployment_targets"] = {
        "production-ssh": {
            "name": "生产主机",
            "method": "ssh",
            "host": "app.internal",
            "port": 2222,
            "username": "deploy",
            "identity_file": "/secret/id_ed25519",
            "known_hosts_file": "/secret/known_hosts",
            "remote_command": "/opt/company/bin/deploy-from-ai-brain",
            "rollback_command": "/opt/company/bin/rollback-from-ai-brain",
        },
        "production-compose": {
            "name": "生产 Docker Compose",
            "method": "docker",
            "working_directory": "/srv/product",
            "compose_files": ["compose.yaml", "compose.prod.yaml"],
            "project_name": "product",
            "services": ["api", "web"],
            "pull": True,
            "rollback_commands": [
                {
                    "argv": ["docker", "compose", "rollback", "api", "web"],
                    "cwd": "/srv/product",
                }
            ],
            "traffic_switch_commands": [
                {
                    "argv": ["/srv/product/bin/switch-slot", "green"],
                    "cwd": "/srv/product",
                }
            ],
            "blue_green_rollback_commands": [
                {
                    "argv": ["/srv/product/bin/switch-slot", "blue"],
                    "cwd": "/srv/product",
                }
            ],
        },
    }
    config_path = tmp_path / "runner_config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("AI_BRAIN_RUNNER_ID", created["id"])
    monkeypatch.setenv("AI_BRAIN_RUNNER_TOKEN", "deployment-token")
    monkeypatch.setenv("AI_BRAIN_ENDPOINT", "http://127.0.0.1:8000/api/system")
    monkeypatch.setenv("AI_BRAIN_RUNNER_CONFIG", str(config_path))
    namespace: dict[str, object] = {"__name__": "deployment_runner_test"}
    exec(compile(runner_agent, "runner_agent.py", "exec"), namespace)
    return namespace


def test_ssh_deployment_uses_fixed_argv_and_json_stdin(tmp_path, monkeypatch):
    namespace = runner_namespace(tmp_path, monkeypatch)
    target = namespace["DEPLOYMENT_TARGETS"]["production-ssh"]  # type: ignore[index]

    command = namespace["_deployment_ssh_command"](target)

    assert command == [
        "ssh",
        "-p",
        "2222",
        "-i",
        "/secret/id_ed25519",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "UserKnownHostsFile=/secret/known_hosts",
        "deploy@app.internal",
        "/opt/company/bin/deploy-from-ai-brain",
    ]
    assert all(";" not in argument for argument in command)


def test_ssh_connectivity_probe_uses_non_mutating_fixed_argv(tmp_path, monkeypatch):
    namespace = runner_namespace(tmp_path, monkeypatch)
    target = namespace["DEPLOYMENT_TARGETS"]["production-ssh"]  # type: ignore[index]

    commands = namespace["_deployment_probe_commands"](target, "ssh")

    assert commands == [
        {
            "argv": [
                "ssh",
                "-p",
                "2222",
                "-i",
                "/secret/id_ed25519",
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=yes",
                "-o",
                "UserKnownHostsFile=/secret/known_hosts",
                "deploy@app.internal",
                "true",
            ],
            "cwd": str(tmp_path),
        }
    ]


def test_docker_deployment_uses_fixed_compose_commands(tmp_path, monkeypatch):
    namespace = runner_namespace(tmp_path, monkeypatch)
    target = namespace["DEPLOYMENT_TARGETS"]["production-compose"]  # type: ignore[index]

    commands = namespace["_deployment_docker_commands"](target)

    common = [
        "docker",
        "compose",
        "-f",
        "compose.yaml",
        "-f",
        "compose.prod.yaml",
        "--project-name",
        "product",
    ]
    assert commands == [
        {"argv": [*common, "pull", "api", "web"], "cwd": "/srv/product"},
        {
            "argv": [*common, "up", "-d", "--remove-orphans", "api", "web"],
            "cwd": "/srv/product",
        },
    ]


def test_docker_connectivity_probe_checks_engine_and_compose_config(tmp_path, monkeypatch):
    namespace = runner_namespace(tmp_path, monkeypatch)
    target = namespace["DEPLOYMENT_TARGETS"]["production-compose"]  # type: ignore[index]

    commands = namespace["_deployment_probe_commands"](target, "docker")

    assert commands == [
        {"argv": ["docker", "info", "--format", "{{.ServerVersion}}"], "cwd": "/srv/product"},
        {
            "argv": [
                "docker",
                "compose",
                "-f",
                "compose.yaml",
                "-f",
                "compose.prod.yaml",
                "--project-name",
                "product",
                "config",
                "--quiet",
            ],
            "cwd": "/srv/product",
        },
    ]


def test_runner_executes_connectivity_probe_and_returns_structured_evidence(tmp_path, monkeypatch):
    namespace = runner_namespace(tmp_path, monkeypatch)
    executions: list[dict] = []
    logs: list[dict] = []
    completions: list[dict] = []

    def fake_stream_process_output(**kwargs):  # type: ignore[no-untyped-def]
        executions.append(kwargs)
        return 0, "probe ok\n", False, None

    namespace["_append_logs"] = lambda task_id, entries, **kwargs: logs.extend(entries)
    namespace["_stream_process_output"] = fake_stream_process_output
    namespace["_complete_task"] = lambda task_id, **kwargs: completions.append(
        {"task_id": task_id, **kwargs}
    )

    namespace["_run_deployment_task"](
        {
            "executor_type": "deployment",
            "id": "runner_task_probe",
            "input_payload": {
                "deployment_method": "docker",
                "operation": "probe",
                "target_code": "production-compose",
            },
            "timeout_seconds": 60,
        }
    )

    assert [item["command_args"] for item in executions] == [
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        [
            "docker",
            "compose",
            "-f",
            "compose.yaml",
            "-f",
            "compose.prod.yaml",
            "--project-name",
            "product",
            "config",
            "--quiet",
        ],
    ]
    assert all("pull" not in item["command_args"] for item in executions)
    assert all("up" not in item["command_args"] for item in executions)
    assert all(item["suppress_output"] is True for item in executions)
    assert completions[0]["status"] == "succeeded"
    assert completions[0]["result_json"]["operation"] == "probe"
    assert completions[0]["result_json"]["health_status"] == "passed"
    assert any("Starting docker probe" in item["message"] for item in logs)
    assert "connectivity probe completed" in completions[0]["logs"][0]["message"]


def test_runner_rejects_deployment_when_target_configuration_fingerprint_changes(
    tmp_path,
    monkeypatch,
):
    namespace = runner_namespace(tmp_path, monkeypatch)
    completions: list[dict] = []
    namespace["_append_logs"] = lambda *args, **kwargs: None
    namespace["_stream_process_output"] = lambda **kwargs: (_ for _ in ()).throw(
        AssertionError("must not execute a target with a stale configuration fingerprint")
    )
    namespace["_complete_task"] = lambda task_id, **kwargs: completions.append(
        {"task_id": task_id, **kwargs}
    )

    namespace["_run_deployment_task"](
        {
            "executor_type": "deployment",
            "id": "runner_task_changed_target",
            "input_payload": {
                "deployment_method": "docker",
                "operation": "probe",
                "target_code": "production-compose",
                "target_config_fingerprint": "0" * 64,
            },
            "timeout_seconds": 60,
        }
    )

    assert completions == [
        {
            "error_code": "DEPLOYMENT_TARGET_CONFIGURATION_CHANGED",
            "error_message": (
                "Deployment target configuration changed after the platform issued this task; "
                "a new connectivity probe is required"
            ),
            "result_json": {
                "deployment_method": "docker",
                "executor_type": "deployment",
                "expected_target_config_fingerprint": "0" * 64,
                "target_code": "production-compose",
                "target_config_fingerprint": namespace["_deployment_target_config_fingerprint"](
                    namespace["DEPLOYMENT_TARGETS"]["production-compose"]
                ),
            },
            "status": "failed",
            "task_id": "runner_task_changed_target",
        }
    ]


def test_runner_connectivity_probe_timeout_is_reported_without_a_deployment(tmp_path, monkeypatch):
    namespace = runner_namespace(tmp_path, monkeypatch)
    completions: list[dict] = []
    namespace["_append_logs"] = lambda *args, **kwargs: None
    namespace["_stream_process_output"] = lambda **kwargs: (
        -9,
        "probe timed out",
        True,
        None,
    )
    namespace["_complete_task"] = lambda task_id, **kwargs: completions.append(
        {"task_id": task_id, **kwargs}
    )

    namespace["_run_deployment_task"](
        {
            "executor_type": "deployment",
            "id": "runner_task_probe_timeout",
            "input_payload": {
                "deployment_method": "ssh",
                "operation": "probe",
                "target_code": "production-ssh",
            },
            "timeout_seconds": 15,
        }
    )

    assert completions[0]["status"] == "timed_out"
    assert completions[0]["error_code"] == "AI_EXECUTOR_TASK_TIMEOUT"
    assert completions[0]["result_json"]["operation"] == "probe"


def test_connectivity_probe_output_is_not_written_to_platform_logs(tmp_path, monkeypatch):
    namespace = runner_namespace(tmp_path, monkeypatch)
    flushed_logs: list[dict] = []
    namespace["_flush_log_batch"] = lambda task_id, logs, **kwargs: flushed_logs.extend(logs)
    namespace["_print_local_log"] = lambda *args, **kwargs: None

    exit_code, output_preview, timed_out, server_status = namespace["_stream_process_output"](
        command_args=[sys.executable, "-c", "print('ssh app.internal private-output')"],
        instruction="",
        suppress_output=True,
        task_id="runner_task_redacted_probe",
        timeout_seconds=5,
        workspace_root=str(tmp_path),
    )

    assert exit_code == 0
    assert output_preview == "Deployment connectivity probe output redacted."
    assert timed_out is False
    assert server_status is None
    assert flushed_logs == []


def test_deployment_execution_reports_result_without_local_secrets(tmp_path, monkeypatch):
    namespace = runner_namespace(tmp_path, monkeypatch)
    executions: list[dict] = []
    completions: list[dict] = []
    namespace["_append_logs"] = lambda *args, **kwargs: None

    def fake_stream_process_output(**kwargs):  # type: ignore[no-untyped-def]
        executions.append(kwargs)
        return 0, "deployment completed", False, None

    def fake_complete(task_id, **kwargs):  # type: ignore[no-untyped-def]
        completions.append({"task_id": task_id, **kwargs})

    namespace["_stream_process_output"] = fake_stream_process_output
    namespace["_complete_task"] = fake_complete
    namespace["_run_deployment_task"](
        {
            "executor_type": "deployment",
            "id": "runner_task_ssh",
            "input_payload": {
                "artifact_version": "v1.2.3",
                "deployment_method": "ssh",
                "deployment_request_id": "deployment_request_001",
                "target_code": "production-ssh",
            },
            "timeout_seconds": 60,
        }
    )

    assert len(executions) == 1
    assert json.loads(executions[0]["instruction"])["artifact_version"] == "v1.2.3"
    assert completions[0]["status"] == "succeeded"
    serialized = json.dumps(completions[0], ensure_ascii=False)
    assert "app.internal" not in serialized
    assert "/secret/id_ed25519" not in serialized
    assert "/secret/known_hosts" not in serialized


def test_deployment_cancel_request_completes_as_cancelled(tmp_path, monkeypatch):
    namespace = runner_namespace(tmp_path, monkeypatch)
    completions: list[dict] = []
    namespace["_append_logs"] = lambda *args, **kwargs: None
    namespace["_stream_process_output"] = lambda **kwargs: (
        -15,
        "cancel requested",
        False,
        "cancel_requested",
    )
    namespace["_complete_task"] = lambda task_id, **kwargs: completions.append(
        {"task_id": task_id, **kwargs}
    )

    namespace["_run_deployment_task"](
        {
            "executor_type": "deployment",
            "id": "runner_task_cancel",
            "input_payload": {
                "deployment_method": "ssh",
                "target_code": "production-ssh",
            },
            "timeout_seconds": 60,
        }
    )

    assert completions[0]["status"] == "cancelled"
    assert completions[0]["error_code"] == "AI_EXECUTOR_TASK_CANCELLED"


def test_runner_executes_configured_ssh_and_docker_rollback_commands(tmp_path, monkeypatch):
    namespace = runner_namespace(tmp_path, monkeypatch)
    ssh_target = namespace["DEPLOYMENT_TARGETS"]["production-ssh"]  # type: ignore[index]
    docker_target = namespace["DEPLOYMENT_TARGETS"]["production-compose"]  # type: ignore[index]

    ssh_command = namespace["_deployment_ssh_command"](ssh_target, operation="rollback")
    docker_commands = namespace["_configured_deployment_commands"](
        docker_target,
        "rollback_commands",
    )

    assert ssh_command[-1] == "/opt/company/bin/rollback-from-ai-brain"
    assert docker_commands == [
        {
            "argv": ["docker", "compose", "rollback", "api", "web"],
            "cwd": "/srv/product",
        }
    ]


def test_failed_health_check_returns_structured_failure_for_auto_rollback(
    tmp_path,
    monkeypatch,
):
    namespace = runner_namespace(tmp_path, monkeypatch)
    completions: list[dict] = []
    namespace["_append_logs"] = lambda *args, **kwargs: None
    namespace["_stream_process_output"] = lambda **kwargs: (
        0,
        "deployment command completed",
        False,
        None,
    )
    namespace["_deployment_health_checks"] = lambda target: (
        False,
        [{"code": "api", "passed": False, "status_code": 503}],
    )
    namespace["_complete_task"] = lambda task_id, **kwargs: completions.append(
        {"task_id": task_id, **kwargs}
    )

    namespace["_run_deployment_task"](
        {
            "executor_type": "deployment",
            "id": "runner_task_health_failure",
            "input_payload": {
                "deployment_method": "docker",
                "operation": "deploy",
                "target_code": "production-compose",
            },
            "timeout_seconds": 60,
        }
    )

    assert completions[0]["status"] == "failed"
    assert completions[0]["error_code"] == "DEPLOYMENT_HEALTH_CHECK_FAILED"
    assert completions[0]["result_json"]["health_status"] == "failed"
    assert completions[0]["result_json"]["health_checks"][0]["status_code"] == 503


def test_blue_green_final_wave_executes_controlled_traffic_switch(tmp_path, monkeypatch):
    namespace = runner_namespace(tmp_path, monkeypatch)
    executions: list[list[str]] = []
    completions: list[dict] = []
    namespace["_append_logs"] = lambda *args, **kwargs: None
    namespace["_deployment_health_checks"] = lambda target: (
        True,
        [{"code": "api", "passed": True, "status_code": 200}],
    )

    def fake_stream_process_output(**kwargs):  # type: ignore[no-untyped-def]
        executions.append(kwargs["command_args"])
        return 0, "ok", False, None

    namespace["_stream_process_output"] = fake_stream_process_output
    namespace["_complete_task"] = lambda task_id, **kwargs: completions.append(
        {"task_id": task_id, **kwargs}
    )

    namespace["_run_deployment_task"](
        {
            "executor_type": "deployment",
            "id": "runner_task_blue_green",
            "input_payload": {
                "deployment_method": "docker",
                "operation": "deploy",
                "rollout_strategy": "blue_green",
                "target_code": "production-compose",
                "wave": {
                    "action": "traffic_switch",
                    "switch_action": "target.blue_green_switch",
                },
                "wave_number": 2,
                "wave_total": 2,
            },
            "timeout_seconds": 60,
        }
    )

    assert executions[-1] == ["/srv/product/bin/switch-slot", "green"]
    assert completions[0]["status"] == "succeeded"
    assert completions[0]["result_json"]["traffic_switch_attempted"] is True
    assert completions[0]["result_json"]["traffic_switch_passed"] is True
