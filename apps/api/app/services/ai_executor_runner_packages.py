from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from app.api.deps import api_error
from app.services.ai_executor_runner_constants import (
    AI_EXECUTOR_RUNNER_DEFAULT_INSTALL_MODE_BY_OS,
    AI_EXECUTOR_RUNNER_INSTALL_MODES_BY_OS,
    AI_EXECUTOR_RUNNER_PACKAGE_ARCHES,
    AI_EXECUTOR_RUNNER_PACKAGE_OSES,
    AI_EXECUTOR_RUNNER_PACKAGE_VERSION,
    SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
)


def _runner_endpoint(runner: dict[str, Any]) -> str:
    return str(runner.get("endpoint_url") or "runner://local")


def _runner_metadata(runner: dict[str, Any]) -> dict[str, Any]:
    metadata = runner.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _normalized_package_option(value: str | None) -> str | None:
    text = str(value or "").strip().lower()
    return text or None


def _runner_package_options(
    runner: dict[str, Any],
    *,
    target_os: str | None = None,
    arch: str | None = None,
    install_mode: str | None = None,
) -> dict[str, str]:
    metadata = _runner_metadata(runner)
    explicit_target_os = _normalized_package_option(target_os)
    explicit_arch = _normalized_package_option(arch)
    explicit_install_mode = _normalized_package_option(install_mode)

    resolved_target_os = (
        explicit_target_os
        or _normalized_package_option(str(metadata.get("target_os") or ""))
        or "linux"
    )
    if resolved_target_os not in AI_EXECUTOR_RUNNER_PACKAGE_OSES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported target_os")

    default_arch = "universal" if resolved_target_os == "manual" else "amd64"
    metadata_arch = metadata.get("package_arch") or metadata.get("arch") or ""
    resolved_arch = explicit_arch or _normalized_package_option(str(metadata_arch)) or default_arch
    if resolved_arch not in AI_EXECUTOR_RUNNER_PACKAGE_ARCHES:
        if explicit_arch:
            raise api_error(400, "VALIDATION_ERROR", "Unsupported arch")
        resolved_arch = default_arch

    allowed_modes = AI_EXECUTOR_RUNNER_INSTALL_MODES_BY_OS[resolved_target_os]
    default_install_mode = AI_EXECUTOR_RUNNER_DEFAULT_INSTALL_MODE_BY_OS[resolved_target_os]
    resolved_install_mode = (
        explicit_install_mode
        or _normalized_package_option(str(metadata.get("install_mode") or ""))
        or default_install_mode
    )
    if resolved_install_mode not in allowed_modes:
        if explicit_install_mode:
            raise api_error(400, "VALIDATION_ERROR", "Unsupported install_mode for target_os")
        resolved_install_mode = default_install_mode

    if resolved_target_os in {"docker", "manual"}:
        resolved_install_mode = default_install_mode
    if resolved_target_os == "manual" and not explicit_arch:
        resolved_arch = "universal"

    return {
        "arch": resolved_arch,
        "install_mode": resolved_install_mode,
        "target_os": resolved_target_os,
        "version": AI_EXECUTOR_RUNNER_PACKAGE_VERSION,
    }


def runner_executor_commands(runner: dict[str, Any]) -> dict[str, str]:
    metadata = _runner_metadata(runner)
    raw_commands = metadata.get("executor_commands")
    if isinstance(raw_commands, dict):
        commands = {
            str(key): str(value).strip()
            for key, value in raw_commands.items()
            if str(key).strip() and str(value).strip()
        }
    else:
        commands = {}
    defaults = {
        "claude": "claude",
        "codex": "codex",
        "hermes": "hermes",
        "openclaw": "openclaw",
    }
    for executor_type in runner.get("executor_types") or []:
        executor_key = str(executor_type)
        if executor_key == SYSTEM_DEFAULT_AI_EXECUTOR_TYPE:
            continue
        commands.setdefault(executor_key, defaults.get(executor_key, executor_key))
    return commands


def _runner_executor_commands(runner: dict[str, Any]) -> dict[str, str]:
    return runner_executor_commands(runner)


def _runner_env_text(runner: dict[str, Any], package_options: dict[str, str]) -> str:
    heartbeat_timeout_seconds = int(runner.get("heartbeat_timeout_seconds") or 120)
    max_concurrent_tasks = int(runner.get("max_concurrent_tasks") or 1)
    return "\n".join(
        [
            "# AI Brain Runner configuration",
            f"AI_BRAIN_ENDPOINT={_runner_endpoint(runner)}",
            f"AI_BRAIN_RUNNER_ID={runner.get('id')}",
            "AI_BRAIN_RUNNER_TOKEN=<runner_token>",
            "AI_BRAIN_EXECUTORS="
            + ",".join(str(item) for item in runner.get("executor_types") or []),
            "AI_BRAIN_WORKSPACE_ROOTS="
            + ",".join(str(item) for item in runner.get("workspace_roots") or ["*"]),
            f"AI_BRAIN_HEARTBEAT_TIMEOUT_SECONDS={heartbeat_timeout_seconds}",
            f"AI_BRAIN_MAX_CONCURRENT_TASKS={max_concurrent_tasks}",
            "AI_BRAIN_POLL_INTERVAL_SECONDS=5",
            "AI_BRAIN_RUNNER_CONFIG=./runner_config.json",
            "AI_BRAIN_BYPASS_PROXY=auto",
            "NO_PROXY=127.0.0.1,localhost,::1",
            "no_proxy=127.0.0.1,localhost,::1",
            f"AI_BRAIN_TARGET_OS={package_options['target_os']}",
            f"AI_BRAIN_PACKAGE_ARCH={package_options['arch']}",
            f"AI_BRAIN_INSTALL_MODE={package_options['install_mode']}",
            f"AI_BRAIN_RUNNER_PACKAGE_VERSION={package_options['version']}",
            "",
        ],
    )


def _runner_config_json(runner: dict[str, Any], package_options: dict[str, str]) -> str:
    config = {
        "executor_commands": _runner_executor_commands(runner),
        "package": dict(package_options),
        "runner": {
            "endpoint_url": _runner_endpoint(runner),
            "executor_types": runner.get("executor_types") or [],
            "heartbeat_timeout_seconds": int(runner.get("heartbeat_timeout_seconds") or 120),
            "id": runner.get("id"),
            "max_concurrent_tasks": int(runner.get("max_concurrent_tasks") or 1),
            "name": runner.get("name"),
            "protocol": runner.get("protocol"),
            "workspace_roots": runner.get("workspace_roots") or ["*"],
        },
        "safety": {
            "cancel_check_interval_seconds": 2,
            "cancel_process_tree_on_server_cancel": True,
            "command_allowlist_enforced": True,
            "command_shell_disabled": True,
            "instruction_passed_via_stdin": True,
            "log_flush_interval_seconds": 2,
            "log_flush_line_count": 5,
            "max_output_preview_chars": 4000,
            "process_group_isolation": True,
            "reject_unconfigured_executor": True,
            "require_human_review_for_git_push": True,
            "server_high_risk_approval_required": True,
            "stream_logs": True,
            "terminate_process_tree_on_timeout": True,
            "workspace_roots_enforced": True,
        },
    }
    return json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _runner_start_command_block() -> str:
    return """exec "${PYTHON:-python3}" runner_agent.py
"""


def _runner_agent_python() -> str:
    return r'''#!/usr/bin/env python3
from __future__ import annotations

import json
import ipaddress
import os
import posixpath
import queue
import re
import signal
import shlex
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


RUNNER_ID = _env("AI_BRAIN_RUNNER_ID")
RUNNER_TOKEN = _env("AI_BRAIN_RUNNER_TOKEN")
ENDPOINT = _env("AI_BRAIN_ENDPOINT").rstrip("/")
CONFIG_PATH = _env("AI_BRAIN_RUNNER_CONFIG", "./runner_config.json")
POLL_INTERVAL_SECONDS = int(_env("AI_BRAIN_POLL_INTERVAL_SECONDS", "5") or "5")
BYPASS_PROXY = _env("AI_BRAIN_BYPASS_PROXY", "auto").lower()


def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
        return json.load(config_file)


CONFIG = _load_config()
EXECUTOR_COMMANDS = dict(CONFIG.get("executor_commands") or {})
SAFETY = CONFIG.get("safety") if isinstance(CONFIG.get("safety"), dict) else {}
MAX_OUTPUT_PREVIEW_CHARS = int(SAFETY.get("max_output_preview_chars") or 4000)
LOG_FLUSH_INTERVAL_SECONDS = float(SAFETY.get("log_flush_interval_seconds") or 2)
LOG_FLUSH_LINE_COUNT = int(SAFETY.get("log_flush_line_count") or 5)
CANCEL_CHECK_INTERVAL_SECONDS = float(SAFETY.get("cancel_check_interval_seconds") or 2)
WORKSPACE_ROOTS = [
    str(item).strip()
    for item in (CONFIG.get("runner") or {}).get("workspace_roots", ["*"])
    if str(item).strip()
]
_STREAM_END = object()
SERVER_TERMINAL_STATUSES = {"cancelled", "dead_letter", "failed", "succeeded", "timed_out"}
EXECUTOR_TYPES = [
    str(item).strip()
    for item in (CONFIG.get("runner") or {}).get("executor_types", [])
    if str(item).strip()
]
HIGH_RISK_PATTERNS = (
    ("git_push_or_merge", r"\b(git\s+push|gh\s+pr\s+merge|glab\s+mr\s+merge)\b"),
    ("destructive_delete", r"\b(rm\s+-[^\n;]*[rf][^\n;]*|rmdir\s+/s|del\s+/s)\b"),
    ("force_reset", r"\b(git\s+reset\s+--hard|git\s+clean\s+-[^\n;]*[xfd])\b"),
    (
        "release_or_deploy",
        r"\b(kubectl\s+(apply|delete|rollout|scale)|helm\s+(upgrade|install|uninstall)|"
        r"terraform\s+(apply|destroy)|docker\s+push|npm\s+publish|pnpm\s+publish)\b",
    ),
)


def _api_root() -> str:
    marker = "/api/system/ai-executor-runners"
    if marker in ENDPOINT:
        return ENDPOINT.split(marker, 1)[0] + "/api/system"
    if ENDPOINT.endswith("/ai-executor-runners"):
        return ENDPOINT.rsplit("/ai-executor-runners", 1)[0]
    return ENDPOINT.rstrip("/")


API_ROOT = _api_root()


def _endpoint_is_loopback() -> bool:
    host = urllib.parse.urlparse(ENDPOINT).hostname or ""
    lowered = host.lower()
    if lowered in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(lowered).is_loopback
    except ValueError:
        return False


def _should_bypass_proxy() -> bool:
    if BYPASS_PROXY in {"1", "true", "yes", "on"}:
        return True
    if BYPASS_PROXY in {"0", "false", "no", "off"}:
        return False
    return _endpoint_is_loopback()


NO_PROXY_OPENER = (
    urllib.request.build_opener(urllib.request.ProxyHandler({}))
    if _should_bypass_proxy()
    else None
)


def _open_request(request: urllib.request.Request, *, timeout: int):
    if NO_PROXY_OPENER is not None:
        return NO_PROXY_OPENER.open(request, timeout=timeout)
    return urllib.request.urlopen(request, timeout=timeout)


def _request_json(method: str, url: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Content-Type", "application/json")
    request.add_header("X-Runner-Token", RUNNER_TOKEN)
    with _open_request(request, timeout=30) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw or "{}")


def _normalize_path(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text == "*":
        return "*"
    normalized = posixpath.normpath(text.replace("\\", "/"))
    if len(normalized) >= 2 and normalized[1] == ":":
        normalized = normalized[0].lower() + normalized[1:]
    return "" if normalized == "." else normalized


def _workspace_allowed(workspace_root: str) -> bool:
    workspace = _normalize_path(workspace_root)
    roots = [_normalize_path(root) for root in WORKSPACE_ROOTS if _normalize_path(root)]
    if not roots or "*" in roots:
        return bool(workspace)
    for root in roots:
        if workspace == root or workspace.startswith(root.rstrip("/") + "/"):
            return True
    return False


def _append_logs(task_id: str, logs: list[dict], status: str = "running") -> None:
    if not logs:
        return
    _request_json(
        "POST",
        f"{API_ROOT}/ai-executor-tasks/{task_id}/logs",
        {"logs": logs, "runner_id": RUNNER_ID, "status": status},
    )


def _flush_log_batch(task_id: str, logs: list[dict], status: str = "running") -> None:
    if not logs:
        return
    batch = list(logs)
    logs.clear()
    try:
        _append_logs(task_id, batch, status=status)
    except Exception as exc:  # noqa: BLE001 - logging should not kill local execution.
        print(f"Failed to append runner logs: {exc}", file=sys.stderr)


def _complete_task(
    task_id: str,
    *,
    status: str,
    result_json: dict,
    logs: list[dict] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    _request_json(
        "POST",
        f"{API_ROOT}/ai-executor-tasks/{task_id}/complete",
        {
            "error_code": error_code,
            "error_message": error_message,
            "logs": logs or [],
            "result_json": result_json,
            "runner_id": RUNNER_ID,
            "status": status,
        },
    )


def _task_status(task_id: str) -> dict | None:
    runner_id = urllib.parse.quote(RUNNER_ID, safe="")
    response = _request_json(
        "GET",
        f"{API_ROOT}/ai-executor-tasks/{task_id}/runner-status?runner_id={runner_id}",
    )
    task = (response.get("data") or {}).get("task")
    return task if isinstance(task, dict) else None


def _heartbeat() -> None:
    metadata = {
        "command_allowlist": sorted(EXECUTOR_COMMANDS.keys()),
        "command_allowlist_enforced": _command_allowlist_enforced(),
        "executors": EXECUTOR_TYPES,
        "instruction_passed_via_stdin": bool(
            SAFETY.get("instruction_passed_via_stdin", True)
        ),
        "package_version": _env("AI_BRAIN_RUNNER_PACKAGE_VERSION", "unknown"),
        "pid": os.getpid(),
        "process_group_isolation": bool(SAFETY.get("process_group_isolation", True)),
        "python": sys.version.split()[0],
        "safety": SAFETY,
        "server_high_risk_approval_required": bool(
            SAFETY.get("server_high_risk_approval_required", True)
        ),
        "shell_disabled": True,
        "terminate_process_tree_on_timeout": bool(
            SAFETY.get("terminate_process_tree_on_timeout", True)
        ),
        "workspace_roots": WORKSPACE_ROOTS,
        "workspace_roots_enforced": bool(SAFETY.get("workspace_roots_enforced", True)),
    }
    _request_json(
        "POST",
        f"{ENDPOINT}/{RUNNER_ID}/heartbeat",
        {"metadata": metadata},
    )


def _claim_task() -> dict | None:
    payload = {"runner_id": RUNNER_ID}
    response = _request_json("POST", f"{API_ROOT}/ai-executor-tasks/claim", payload)
    return (response.get("data") or {}).get("task")


def _enqueue_output_lines(stream, output_queue: queue.Queue) -> None:
    try:
        if stream is None:
            return
        for line in iter(stream.readline, ""):
            if line:
                output_queue.put(line)
    finally:
        output_queue.put(_STREAM_END)


def _drain_output_queue(
    output_queue: queue.Queue,
    pending_logs: list[dict],
    output_preview: str,
) -> tuple[bool, str]:
    reader_done = False
    while True:
        try:
            item = output_queue.get_nowait()
        except queue.Empty:
            break
        if item is _STREAM_END:
            reader_done = True
            continue
        if not isinstance(item, str):
            continue
        output_preview = (output_preview + item)[-MAX_OUTPUT_PREVIEW_CHARS:]
        message = item.rstrip()
        if message:
            pending_logs.append({"level": "info", "message": message})
    return reader_done, output_preview


def _process_group_popen_kwargs() -> dict:
    if os.name == "nt":
        return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    return {"start_new_session": True}


def _send_process_tree_signal(process: subprocess.Popen, sig: int) -> None:
    if os.name == "nt":
        if sig == signal.SIGTERM:
            process.terminate()
        else:
            process.kill()
        return
    os.killpg(process.pid, sig)


def _terminate_process_tree(process: subprocess.Popen) -> str:
    if process.poll() is not None:
        return "already_exited"
    try:
        _send_process_tree_signal(process, signal.SIGTERM)
    except Exception:
        try:
            process.terminate()
        except Exception:
            pass
    try:
        process.wait(timeout=5)
        return "terminated"
    except subprocess.TimeoutExpired:
        pass
    kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
    try:
        _send_process_tree_signal(process, kill_signal)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        return "kill_timeout"
    return "killed"


def _stream_process_output(
    *,
    command_args: list[str],
    instruction: str,
    task_id: str,
    timeout_seconds: int,
    workspace_root: str,
) -> tuple[int, str, bool, str | None]:
    process = subprocess.Popen(
        command_args,
        cwd=workspace_root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        **_process_group_popen_kwargs(),
    )
    if process.stdin is not None:
        process.stdin.write(instruction)
        process.stdin.close()

    output_queue: queue.Queue = queue.Queue()
    reader = threading.Thread(
        target=_enqueue_output_lines,
        args=(process.stdout, output_queue),
        daemon=True,
    )
    reader.start()

    deadline = time.monotonic() + max(timeout_seconds, 1)
    last_cancel_check_at = time.monotonic()
    last_flush_at = time.monotonic()
    output_preview = ""
    pending_logs: list[dict] = []
    reader_done = False
    server_terminal_status: str | None = None
    timed_out = False

    while True:
        try:
            item = output_queue.get(timeout=0.2)
        except queue.Empty:
            item = None
        if item is _STREAM_END:
            reader_done = True
        elif isinstance(item, str):
            output_preview = (output_preview + item)[-MAX_OUTPUT_PREVIEW_CHARS:]
            message = item.rstrip()
            if message:
                pending_logs.append({"level": "info", "message": message})

        now = time.monotonic()
        if (
            bool(SAFETY.get("cancel_process_tree_on_server_cancel", True))
            and CANCEL_CHECK_INTERVAL_SECONDS > 0
            and now - last_cancel_check_at >= CANCEL_CHECK_INTERVAL_SECONDS
        ):
            last_cancel_check_at = now
            try:
                status_payload = _task_status(task_id) or {}
                status = str(status_payload.get("status") or "")
            except Exception as exc:  # noqa: BLE001 - status polling must not kill execution.
                status = ""
                print(f"Failed to poll runner task status: {exc}", file=sys.stderr)
            if status in SERVER_TERMINAL_STATUSES:
                server_terminal_status = status
                termination_status = _terminate_process_tree(process)
                pending_logs.append(
                    {
                        "level": "warning",
                        "message": (
                            f"Task reached server terminal status {status}; "
                            f"process tree {termination_status}"
                        ),
                    }
                )
                break
        if pending_logs and (
            len(pending_logs) >= LOG_FLUSH_LINE_COUNT
            or now - last_flush_at >= LOG_FLUSH_INTERVAL_SECONDS
        ):
            _flush_log_batch(task_id, pending_logs, status="running")
            last_flush_at = now

        if process.poll() is not None and reader_done:
            break
        if now >= deadline and process.poll() is None:
            timed_out = True
            termination_status = _terminate_process_tree(process)
            pending_logs.append(
                {
                    "level": "error",
                    "message": (
                        f"Executor timed out after {timeout_seconds}s; "
                        f"process tree {termination_status}"
                    ),
                }
            )
            break

    drained_done, output_preview = _drain_output_queue(
        output_queue,
        pending_logs,
        output_preview,
    )
    reader_done = reader_done or drained_done
    if not server_terminal_status:
        _flush_log_batch(task_id, pending_logs, status="timed_out" if timed_out else "running")
    else:
        pending_logs.clear()
    reader.join(timeout=1)
    return (
        process.returncode if process.returncode is not None else -9,
        output_preview,
        timed_out,
        server_terminal_status,
    )


def _command_allowlist_enforced() -> bool:
    return bool(SAFETY.get("command_allowlist_enforced", True))


def _resolve_executor_command(executor_type: str) -> tuple[str | None, list[str], str | None]:
    configured = str(EXECUTOR_COMMANDS.get(executor_type) or "").strip()
    if _command_allowlist_enforced() and not configured:
        return None, [], f"Executor {executor_type} is not configured in runner command allowlist"
    command = configured or executor_type
    try:
        command_args = shlex.split(command)
    except ValueError as exc:
        return command, [], f"Invalid command configured for executor {executor_type}: {exc}"
    if not command_args:
        return command, [], f"No command configured for executor {executor_type}"
    return command, command_args, None


def _high_risk_operations(instruction: str) -> list[str]:
    operations: list[str] = []
    for operation, pattern in HIGH_RISK_PATTERNS:
        if re.search(pattern, instruction, flags=re.IGNORECASE):
            operations.append(operation)
    return operations


def _task_has_approval(task: dict) -> bool:
    request_config = task.get("request_config")
    if not isinstance(request_config, dict):
        return False
    safety = request_config.get("ai_executor_safety")
    if not isinstance(safety, dict):
        return False
    return safety.get("status") == "approved"


def _run_task(task: dict) -> None:
    task_id = task["id"]
    executor_type = str(task.get("executor_type") or "")
    workspace_root = str(task.get("workspace_root") or "")
    instruction = str(task.get("instruction") or "")
    timeout_seconds = int(task.get("timeout_seconds") or 1800)
    high_risk_operations = _high_risk_operations(instruction)
    if high_risk_operations and not _task_has_approval(task):
        _complete_task(
            task_id,
            status="failed",
            error_code="AI_EXECUTOR_APPROVAL_REQUIRED",
            error_message="High-risk instruction requires platform approval before execution",
            result_json={
                "blocked_operations": high_risk_operations,
                "executor_type": executor_type,
                "workspace_root": workspace_root,
            },
        )
        return
    if not _workspace_allowed(workspace_root):
        _complete_task(
            task_id,
            status="failed",
            error_code="AI_EXECUTOR_WORKSPACE_NOT_ALLOWED",
            error_message="Task workspace root is outside this runner workspace whitelist",
            result_json={"workspace_root": workspace_root, "workspace_roots": WORKSPACE_ROOTS},
        )
        return
    command, command_args, command_error = _resolve_executor_command(executor_type)
    if command_error:
        _complete_task(
            task_id,
            status="failed",
            error_code=(
                "AI_EXECUTOR_COMMAND_NOT_ALLOWED"
                if _command_allowlist_enforced()
                else "AI_EXECUTOR_COMMAND_MISSING"
            ),
            error_message=command_error,
            result_json={
                "command_allowlist_enforced": _command_allowlist_enforced(),
                "executor_type": executor_type,
            },
        )
        return
    started_at = time.time()
    _append_logs(
        task_id,
        [{"level": "info", "message": f"Starting {executor_type} in {workspace_root}"}],
        status="running",
    )
    try:
        exit_code, preview, timed_out, server_terminal_status = _stream_process_output(
            command_args=command_args,
            instruction=instruction,
            task_id=task_id,
            timeout_seconds=timeout_seconds,
            workspace_root=workspace_root,
        )
        duration_ms = int((time.time() - started_at) * 1000)
        if server_terminal_status:
            print(
                f"Task {task_id} already reached server terminal status "
                f"{server_terminal_status}; local completion skipped.",
                file=sys.stderr,
            )
            return
        if timed_out:
            _complete_task(
                task_id,
                status="timed_out",
                error_code="AI_EXECUTOR_TASK_TIMEOUT",
                error_message=f"Executor timed out after {timeout_seconds}s",
                logs=[
                    {
                        "level": "error",
                        "message": f"{executor_type} timed out after {timeout_seconds}s",
                    }
                ],
                result_json={
                    "command_shell": False,
                    "duration_ms": duration_ms,
                    "executor_type": executor_type,
                    "exit_code": exit_code,
                    "output_preview": preview,
                    "workspace_root": workspace_root,
                },
            )
            return
        status = "succeeded" if exit_code == 0 else "failed"
        logs = [
            {
                "level": "info" if exit_code == 0 else "error",
                "message": f"{executor_type} exited with {exit_code}",
            }
        ]
        _complete_task(
            task_id,
            status=status,
            error_code=None if exit_code == 0 else "AI_EXECUTOR_COMMAND_FAILED",
            error_message=None if exit_code == 0 else preview,
            logs=logs,
            result_json={
                "command_shell": False,
                "duration_ms": duration_ms,
                "executor_type": executor_type,
                "exit_code": exit_code,
                "output_preview": preview,
                "workspace_root": workspace_root,
            },
        )
    except Exception as exc:  # noqa: BLE001 - runner must report failures to AI Brain.
        _complete_task(
            task_id,
            status="failed",
            error_code=exc.__class__.__name__,
            error_message=str(exc),
            result_json={"executor_type": executor_type, "workspace_root": workspace_root},
        )


def main() -> int:
    if not RUNNER_ID or not RUNNER_TOKEN or RUNNER_TOKEN == "<runner_token>":
        print("AI_BRAIN_RUNNER_ID and AI_BRAIN_RUNNER_TOKEN are required", file=sys.stderr)
        return 2
    if not ENDPOINT.startswith("http://") and not ENDPOINT.startswith("https://"):
        print("AI_BRAIN_ENDPOINT must be an HTTP(S) API base URL", file=sys.stderr)
        return 2
    print(f"AI Brain Runner {RUNNER_ID} started; polling {API_ROOT}")
    while True:
        try:
            _heartbeat()
            task = _claim_task()
            if task:
                _run_task(task)
            else:
                time.sleep(POLL_INTERVAL_SECONDS)
        except urllib.error.HTTPError as exc:
            print(f"HTTP error: {exc.code} {exc.read().decode('utf-8')}", file=sys.stderr)
            time.sleep(POLL_INTERVAL_SECONDS)
        except Exception as exc:  # noqa: BLE001 - keep the runner alive.
            print(f"Runner loop error: {exc}", file=sys.stderr)
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _runner_shell_script(runner: dict[str, Any], package_options: dict[str, str]) -> str:
    install_mode = package_options["install_mode"]
    target_os = package_options["target_os"]
    follow_up = ""
    if target_os == "linux" and install_mode == "systemd":
        follow_up = """
cat <<'TIP'

systemd 安装提示：
1. sudo mkdir -p /opt/ai-brain-runner
2. sudo cp -R . /opt/ai-brain-runner/
3. sudo cp systemd/ai-brain-runner.service /etc/systemd/system/
4. sudo systemctl daemon-reload
5. sudo systemctl enable --now ai-brain-runner
TIP
"""
    if target_os == "macos" and install_mode == "launchd":
        follow_up = """
cat <<'TIP'

launchd 安装提示：
1. mkdir -p ~/Library/LaunchAgents ~/.ai-brain-runner
2. cp -R . ~/.ai-brain-runner/
3. cp launchd/com.ai-brain.runner.plist ~/Library/LaunchAgents/
4. launchctl load ~/Library/LaunchAgents/com.ai-brain.runner.plist
TIP
"""
    return f"""#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -f ai-brain-runner.env ]]; then
  echo "ai-brain-runner.env not found" >&2
  exit 1
fi

set -a
source ai-brain-runner.env
set +a

if [[ -z "${{AI_BRAIN_RUNNER_TOKEN:-}}" || "${{AI_BRAIN_RUNNER_TOKEN}}" == "<runner_token>" ]]; then
  echo "Please edit ai-brain-runner.env and set AI_BRAIN_RUNNER_TOKEN first." >&2
  exit 1
fi

echo "Starting AI Brain Runner {runner.get('id')}"
echo "Package: {target_os}/{package_options['arch']} ({install_mode})"
echo "Executors: ${{AI_BRAIN_EXECUTORS}}"
{follow_up}
{_runner_start_command_block()}"""


def _runner_windows_script(runner: dict[str, Any], package_options: dict[str, str]) -> str:
    return f"""$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Test-Path ".\\ai-brain-runner.env")) {{
  throw "ai-brain-runner.env not found"
}}

Get-Content ".\\ai-brain-runner.env" | ForEach-Object {{
  if ($_ -match "^\\s*#" -or $_ -notmatch "=") {{ return }}
  $parts = $_.Split("=", 2)
  [Environment]::SetEnvironmentVariable($parts[0], $parts[1], "Process")
}}

if (-not $env:AI_BRAIN_RUNNER_TOKEN -or $env:AI_BRAIN_RUNNER_TOKEN -eq "<runner_token>") {{
  throw "Please edit ai-brain-runner.env and set AI_BRAIN_RUNNER_TOKEN first."
}}

Write-Host "Starting AI Brain Runner {runner.get('id')} for windows/{package_options['arch']}"
$python = if ($env:PYTHON) {{ $env:PYTHON }} else {{ "python" }}
& $python ".\\runner_agent.py"
"""


def _runner_manual_shell_script() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"
set -a
source ai-brain-runner.env
set +a
exec "${PYTHON:-python3}" runner_agent.py
"""


def _runner_manual_powershell_script() -> str:
    return """$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location $RootDir
Get-Content ".\\ai-brain-runner.env" | ForEach-Object {
  if ($_ -match "^\\s*#" -or $_ -notmatch "=") { return }
  $parts = $_.Split("=", 2)
  [Environment]::SetEnvironmentVariable($parts[0], $parts[1], "Process")
}
$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
& $python ".\\runner_agent.py"
"""


def _runner_manifest_json(runner: dict[str, Any], package_options: dict[str, str]) -> str:
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "package": dict(package_options),
        "runner": {
            "endpoint_url": _runner_endpoint(runner),
            "executor_types": runner.get("executor_types") or [],
            "id": runner.get("id"),
            "name": runner.get("name"),
            "workspace_roots": runner.get("workspace_roots") or ["*"],
        },
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _runner_systemd_service() -> str:
    return """[Unit]
Description=AI Brain Runner
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/ai-brain-runner
ExecStart=/opt/ai-brain-runner/install.sh
Restart=always
RestartSec=5
Environment=AI_BRAIN_RUNNER_CONFIG=/opt/ai-brain-runner/runner_config.json

[Install]
WantedBy=multi-user.target
"""


def _runner_launchd_plist() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.ai-brain.runner</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>$HOME/.ai-brain-runner/install.sh</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>WorkingDirectory</key>
  <string>$HOME/.ai-brain-runner</string>
  <key>StandardOutPath</key>
  <string>/tmp/ai-brain-runner.out.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/ai-brain-runner.err.log</string>
</dict>
</plist>
"""


def _runner_windows_service_xml() -> str:
    return """<service>
  <id>ai-brain-runner</id>
  <name>AI Brain Runner</name>
  <description>Connects Codex, Claude Code, Hermes or OpenClaw to AI Brain.</description>
  <executable>powershell.exe</executable>
  <arguments>-ExecutionPolicy Bypass -File "%BASE%\\install.ps1"</arguments>
  <log mode="roll" />
</service>
"""


def _runner_dockerfile() -> str:
    return """FROM python:3.12-slim
WORKDIR /opt/ai-brain-runner
COPY . /opt/ai-brain-runner
RUN chmod +x runner_agent.py scripts/start-runner.sh || true
CMD ["bash", "scripts/start-runner.sh"]
"""


def _runner_docker_compose() -> str:
    return """services:
  ai-brain-runner:
    build: .
    restart: unless-stopped
    env_file:
      - ai-brain-runner.env
    volumes:
      - ./runner_config.json:/opt/ai-brain-runner/runner_config.json:ro
      - /var/run/docker.sock:/var/run/docker.sock
"""


def _runner_start_stop_markdown(
    runner: dict[str, Any],
    package_options: dict[str, str],
) -> str:
    target_os = package_options["target_os"]
    install_mode = package_options["install_mode"]
    common_intro = f"""# AI Brain Runner 启停说明

Runner ID: `{runner.get('id')}`

AI Brain 页面里的 `disabled` 只表示服务端不再给该 Runner 下发新任务。
如果要真正关闭本机 Runner，需要在安装机器上执行下面的停止命令。
"""
    if target_os == "linux" and install_mode == "systemd":
        commands = """## 启动 Runner

```bash
sudo systemctl start ai-brain-runner
```

## 停止 Runner

```bash
sudo systemctl stop ai-brain-runner
```

## 查看状态

```bash
sudo systemctl status ai-brain-runner
```

## 重启 Runner

```bash
sudo systemctl restart ai-brain-runner
```

## 禁用开机自启

```bash
sudo systemctl disable ai-brain-runner
```
"""
    elif target_os == "linux":
        commands = """## 启动 Runner

```bash
chmod +x install.sh
./install.sh
```

## 停止 Runner

在启动 Runner 的终端中按：

```text
Ctrl + C
```

## 查看状态

前台脚本模式没有系统服务状态，请查看当前终端输出或 AI Brain 执行器心跳状态。
"""
    elif target_os == "macos" and install_mode == "launchd":
        commands = """## 启动 Runner

```bash
launchctl load ~/Library/LaunchAgents/com.ai-brain.runner.plist
```

## 停止 Runner

```bash
launchctl unload ~/Library/LaunchAgents/com.ai-brain.runner.plist
```

## 查看状态

```bash
launchctl list | grep ai-brain
```

## 重启 Runner

```bash
launchctl unload ~/Library/LaunchAgents/com.ai-brain.runner.plist
launchctl load ~/Library/LaunchAgents/com.ai-brain.runner.plist
```
"""
    elif target_os == "macos":
        commands = """## 启动 Runner

```bash
chmod +x install.sh
./install.sh
```

## 停止 Runner

在启动 Runner 的终端中按：

```text
Ctrl + C
```

## 查看状态

前台脚本模式没有系统服务状态，请查看当前终端输出或 AI Brain 执行器心跳状态。
"""
    elif target_os == "windows" and install_mode == "service":
        commands = """## 启动 Runner

```powershell
Start-Service ai-brain-runner
```

## 停止 Runner

```powershell
Stop-Service ai-brain-runner
```

## 查看状态

```powershell
Get-Service ai-brain-runner
```

## 重启 Runner

```powershell
Restart-Service ai-brain-runner
```

## 禁用开机自启

```powershell
Set-Service ai-brain-runner -StartupType Disabled
```
"""
    elif target_os == "windows":
        commands = """## 启动 Runner

```powershell
./install.ps1
```

## 停止 Runner

在启动 Runner 的 PowerShell 窗口中按：

```text
Ctrl + C
```

## 查看状态

前台脚本模式没有系统服务状态，请查看当前 PowerShell 输出或 AI Brain 执行器心跳状态。
"""
    elif target_os == "docker":
        commands = """## 启动 Runner

```bash
docker compose -f docker-compose.runner.yml up -d --build
```

## 停止 Runner

```bash
docker compose -f docker-compose.runner.yml down
```

## 查看状态

```bash
docker compose -f docker-compose.runner.yml ps
```

## 查看日志

```bash
docker compose -f docker-compose.runner.yml logs -f
```

## 重启 Runner

```bash
docker compose -f docker-compose.runner.yml restart
```
"""
    else:
        commands = """## 启动 Runner

macOS / Linux:

```bash
./scripts/start-runner.sh
```

Windows PowerShell:

```powershell
./scripts/start-runner.ps1
```

## 停止 Runner

在启动 Runner 的终端或 PowerShell 窗口中按：

```text
Ctrl + C
```

## 查看状态

通用手动模式没有系统服务状态，请查看当前终端输出或 AI Brain 执行器心跳状态。
"""
    return (
        common_intro
        + "\n"
        + commands
        + """
## AI Brain 页面侧停用

在 `任务中心 / 插件管理 / 执行器` 中把 Runner 状态改为 `disabled` 后，
服务端不会再给该 Runner 下发新任务；但本机进程不会自动退出。
需要彻底关闭时，仍要执行本文件中的停止命令。
"""
    )


def _runner_readme(runner: dict[str, Any], package_options: dict[str, str]) -> str:
    target_os = package_options["target_os"]
    install_mode = package_options["install_mode"]
    install_hint_by_os = {
        "docker": "编辑 `ai-brain-runner.env` 后执行 `docker compose up -d --build`。",
        "linux": (
            "编辑 `ai-brain-runner.env` 后执行 `chmod +x install.sh && ./install.sh`；"
            "systemd 模式可按脚本提示安装服务。"
        ),
        "macos": (
            "编辑 `ai-brain-runner.env` 后执行 `chmod +x install.sh && ./install.sh`；"
            "launchd 模式可按脚本提示安装 LaunchAgent。"
        ),
        "manual": (
            "编辑 `ai-brain-runner.env` 后按系统选择 `scripts/start-runner.sh` "
            "或 `scripts/start-runner.ps1` 前台启动。"
        ),
        "windows": (
            "编辑 `ai-brain-runner.env` 后在 PowerShell 中执行 `./install.ps1`；"
            "service 模式可结合 `windows/ai-brain-runner-service.xml` 注册服务。"
        ),
    }
    return f"""# AI Brain Runner 安装包

本安装包用于把远程机器上的 Codex、Claude Code、Hermes 或 OpenClaw 接入 AI Brain。

## Runner

- ID: `{runner.get('id')}`
- 名称: `{runner.get('name')}`
- Endpoint: `{_runner_endpoint(runner)}`
- 执行器: `{", ".join(str(item) for item in runner.get("executor_types") or [])}`
- 工作区白名单: `{", ".join(str(item) for item in runner.get("workspace_roots") or ["*"])}`
- 目标系统: `{target_os}`
- CPU 架构: `{package_options["arch"]}`
- 安装方式: `{install_mode}`
- 安装包版本: `{package_options["version"]}`

## 安装步骤

1. 在远程机器安装需要的执行器 CLI，例如 Codex、Claude Code、Hermes 或 OpenClaw。
2. 解压本安装包。
3. 编辑 `ai-brain-runner.env`，把 `AI_BRAIN_RUNNER_TOKEN=<runner_token>`
   替换为创建或轮换 Runner 时返回的一次性 Token。
4. {install_hint_by_os[target_os]}
5. 回到 AI Brain 插件管理 / 执行器页面，确认健康状态变为 `online`。

安装包内置 `runner_agent.py`，可直接轮询 AI Brain、发送心跳、认领任务、
调用本机执行器命令并回写日志和结果；不要求目标机器预装额外 Runner CLI。
当 Endpoint 指向 `127.0.0.1`、`localhost` 或 `::1` 时，Runner 默认绕过系统
HTTP/HTTPS 代理，避免本机代理把心跳请求转发后重置连接；如需强制使用代理，
可在 `ai-brain-runner.env` 中设置 `AI_BRAIN_BYPASS_PROXY=false`。

## 启停说明

启动、停止、重启、查看状态和禁用开机自启命令见 `START_STOP.md`。

## 安全说明

Runner 主动访问 AI Brain，不需要暴露远程机器端口。
Token 只用于该 Runner，泄露后请立即在 AI Brain 中轮换。
"""


def _runner_install_assets(
    runner: dict[str, Any],
    package_options: dict[str, str],
) -> dict[str, str]:
    target_os = package_options["target_os"]
    install_mode = package_options["install_mode"]
    if target_os == "linux":
        assets = {"install.sh": _runner_shell_script(runner, package_options)}
        if install_mode == "systemd":
            assets["systemd/ai-brain-runner.service"] = _runner_systemd_service()
        return assets
    if target_os == "macos":
        assets = {"install.sh": _runner_shell_script(runner, package_options)}
        if install_mode == "launchd":
            assets["launchd/com.ai-brain.runner.plist"] = _runner_launchd_plist()
        return assets
    if target_os == "windows":
        assets = {"install.ps1": _runner_windows_script(runner, package_options)}
        if install_mode == "service":
            assets["windows/ai-brain-runner-service.xml"] = _runner_windows_service_xml()
        return assets
    if target_os == "docker":
        return {
            "Dockerfile": _runner_dockerfile(),
            "docker-compose.runner.yml": _runner_docker_compose(),
            "scripts/start-runner.sh": _runner_manual_shell_script(),
        }
    return {
        "scripts/start-runner.ps1": _runner_manual_powershell_script(),
        "scripts/start-runner.sh": _runner_manual_shell_script(),
    }


def _runner_package_filename(runner_id: str, package_options: dict[str, str]) -> str:
    return (
        f"ai-brain-runner-{runner_id}-"
        f"{package_options['target_os']}-{package_options['arch']}-"
        f"{package_options['install_mode']}.zip"
    )


def _runner_skill_markdown(runner: dict[str, Any]) -> str:
    executors = ", ".join(str(item) for item in runner.get("executor_types") or [])
    return f"""---
name: ai-brain-runner
description: Connect local Codex, Claude Code, Hermes, or OpenClaw to AI Brain.
---

# AI Brain Runner Skill

Use this skill when a task is received from AI Brain through the local Runner process.

## Runner Context

- Runner ID: `{runner.get('id')}`
- Runner name: `{runner.get('name')}`
- AI Brain endpoint: `{_runner_endpoint(runner)}`
- Supported executors: `{executors}`
- Workspace roots: `{", ".join(str(item) for item in runner.get("workspace_roots") or ["*"])}`

## Rules

- Only work inside the configured workspace roots.
- Use the requested executor type when it is available: Codex, Claude Code, Hermes, or OpenClaw.
- Stream concise logs back to AI Brain while running.
- Return structured results with status, summary, changed files, test commands,
  and failure reason when applicable.
- Do not push, merge, delete broad paths, or expose secrets unless the AI Brain
  task explicitly requires human-approved release actions.
- If credentials, workspace, or tool binaries are missing, fail the task with a
  clear remediation message.

## Result Contract

Return JSON-compatible output with:

- `status`: `succeeded` or `failed`
- `summary`: short human-readable outcome
- `executor_type`: executor used
- `workspace_root`: workspace path
- `commands`: commands run without secrets
- `changed_files`: changed file paths
- `tests`: test commands and results
- `error_message`: required when failed
"""


def build_ai_executor_runner_install_package(
    runner: dict[str, Any],
    *,
    arch: str | None = None,
    install_mode: str | None = None,
    target_os: str | None = None,
) -> tuple[bytes, str]:
    package_options = _runner_package_options(
        runner,
        arch=arch,
        install_mode=install_mode,
        target_os=target_os,
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", _runner_readme(runner, package_options))
        archive.writestr("START_STOP.md", _runner_start_stop_markdown(runner, package_options))
        archive.writestr("ai-brain-runner.env", _runner_env_text(runner, package_options))
        archive.writestr("manifest.json", _runner_manifest_json(runner, package_options))
        archive.writestr("runner_agent.py", _runner_agent_python())
        archive.writestr("runner_config.json", _runner_config_json(runner, package_options))
        archive.writestr("skills/ai-brain-runner/SKILL.md", _runner_skill_markdown(runner))
        for filename, content in _runner_install_assets(runner, package_options).items():
            archive.writestr(filename, content)
    return buffer.getvalue(), _runner_package_filename(str(runner.get("id")), package_options)
