from __future__ import annotations

import json
import os
import shlex
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


def _normalize_runner_executor_command(executor_type: str, command: str) -> str:
    text = str(command or "").strip()
    if executor_type != "codex" or not text:
        return text
    try:
        command_args = shlex.split(text)
    except ValueError:
        return text
    if len(command_args) == 1 and os.path.basename(command_args[0]).lower() in {
        "codex",
        "codex.exe",
    }:
        command_args.append("exec")
        return shlex.join(command_args)
    return text


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
            str(key): _normalize_runner_executor_command(str(key), str(value))
            for key, value in raw_commands.items()
            if str(key).strip() and str(value).strip()
        }
    else:
        commands = {}
    defaults = {
        "claude": "claude",
        "codex": "codex exec",
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
            "AI_BRAIN_CAPABILITIES="
            + ",".join(str(item) for item in runner.get("capabilities") or []),
            "AI_BRAIN_WORKSPACE_ROOTS="
            + ",".join(str(item) for item in runner.get("workspace_roots") or ["*"]),
            f"AI_BRAIN_HEARTBEAT_TIMEOUT_SECONDS={heartbeat_timeout_seconds}",
            f"AI_BRAIN_MAX_CONCURRENT_TASKS={max_concurrent_tasks}",
            "AI_BRAIN_POLL_INTERVAL_SECONDS=5",
            "AI_BRAIN_RUNNER_CONFIG=./runner_config.json",
            "AI_BRAIN_RUNNER_PRINT_BACKGROUND_LOGS=false",
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
        "deployment_targets": {},
        "executor_commands": _runner_executor_commands(runner),
        "package": dict(package_options),
        "runner": {
            "capabilities": runner.get("capabilities") or [],
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
            "extra_path_entries": [
                "$HOME/.local/bin",
                "$HOME/.npm-global/bin",
                "$HOME/.bun/bin",
                "$HOME/.cargo/bin",
                "/Applications/Codex.app/Contents/Resources",
                "/opt/homebrew/bin",
                "/usr/local/bin",
            ],
            "instruction_passed_via_stdin": True,
            "local_console_logs": False,
            "log_flush_interval_seconds": 2,
            "log_flush_line_count": 5,
            "max_output_preview_chars": 4000,
            "print_background_logs": False,
            "process_group_isolation": True,
            "reject_unconfigured_executor": True,
            "require_human_review_for_git_push": True,
            "server_high_risk_approval_required": True,
            "stream_logs": True,
            "terminate_process_tree_on_timeout": True,
            "workspace_worktree_isolation_enabled": True,
            "workspace_worktree_parent_dir_name": ".ai-brain-worktrees",
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
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_bool(name: str, default: bool) -> bool:
    raw_value = _env(name)
    if not raw_value:
        return bool(default)
    return raw_value.lower() in {"1", "true", "yes", "on"}


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
DEPLOYMENT_TARGETS = dict(CONFIG.get("deployment_targets") or {})
EXECUTOR_COMMANDS = dict(CONFIG.get("executor_commands") or {})
SAFETY = CONFIG.get("safety") if isinstance(CONFIG.get("safety"), dict) else {}
PRINT_BACKGROUND_LOGS = bool(
    SAFETY.get("print_background_logs", SAFETY.get("local_console_logs", False))
)
LOCAL_CONSOLE_LOGS = _env_bool("AI_BRAIN_RUNNER_PRINT_BACKGROUND_LOGS", PRINT_BACKGROUND_LOGS)
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
SERVER_CANCEL_REQUEST_STATUSES = {"cancel_requested"}
WORKTREE_ISOLATION_ENABLED = bool(SAFETY.get("workspace_worktree_isolation_enabled", True))
WORKTREE_PARENT_DIR_NAME = str(
    SAFETY.get("workspace_worktree_parent_dir_name") or ".ai-brain-worktrees"
)
WORKSPACE_ISOLATIONS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(CONFIG_PATH)),
    "workspace_isolations.json",
)
EXECUTOR_TYPES = [
    str(item).strip()
    for item in (CONFIG.get("runner") or {}).get("executor_types", [])
    if str(item).strip()
]
RUNNER_CAPABILITIES = [
    str(item).strip()
    for item in (CONFIG.get("runner") or {}).get("capabilities", [])
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


def _string_list(value) -> list[str]:
    if isinstance(value, str):
        values = value.split(os.pathsep)
    elif isinstance(value, list):
        values = value
    else:
        values = []
    return [str(item).strip() for item in values if str(item).strip()]


def _default_executor_path_entries() -> list[str]:
    home = os.path.expanduser("~")
    entries: list[str] = []
    if home and home != "~":
        entries.extend(
            [
                os.path.join(home, ".local", "bin"),
                os.path.join(home, ".npm-global", "bin"),
                os.path.join(home, ".bun", "bin"),
                os.path.join(home, ".cargo", "bin"),
            ]
        )
    entries.extend(
        [
            "/Applications/Codex.app/Contents/Resources",
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin",
        ]
    )
    return entries


def _configured_extra_path_entries() -> list[str]:
    entries = _string_list(SAFETY.get("extra_path_entries"))
    return [os.path.expandvars(os.path.expanduser(item)) for item in entries]


def _runner_search_path() -> str:
    existing_path = os.environ.get("PATH") or ""
    entries = [
        *_configured_extra_path_entries(),
        *_default_executor_path_entries(),
        *existing_path.split(os.pathsep),
    ]
    unique_entries: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        normalized = str(entry or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_entries.append(normalized)
    return os.pathsep.join(unique_entries)


def _augment_process_path() -> None:
    os.environ["PATH"] = _runner_search_path()


_augment_process_path()


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


def _print_local_log(task_id: str, log: dict) -> None:
    if not LOCAL_CONSOLE_LOGS:
        return
    level = str(log.get("level") or "info").upper()
    timestamp = str(log.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    message = str(log.get("message") or "")
    stream = sys.stderr if level in {"ERROR", "WARNING"} else sys.stdout
    print(f"[{timestamp}] [{task_id}] [{level}] {message}", file=stream, flush=True)


def _print_local_logs(task_id: str, logs: list[dict]) -> None:
    for log in logs:
        if isinstance(log, dict):
            _print_local_log(task_id, log)


def _append_logs(
    task_id: str,
    logs: list[dict],
    status: str = "running",
    *,
    local_echo: bool = True,
) -> None:
    if not logs:
        return
    if local_echo:
        _print_local_logs(task_id, logs)
    _request_json(
        "POST",
        f"{API_ROOT}/ai-executor-tasks/{task_id}/logs",
        {"logs": logs, "runner_id": RUNNER_ID, "status": status},
    )


def _flush_log_batch(
    task_id: str,
    logs: list[dict],
    status: str = "running",
    *,
    local_echo: bool = True,
) -> None:
    if not logs:
        return
    batch = list(logs)
    logs.clear()
    try:
        _append_logs(task_id, batch, status=status, local_echo=local_echo)
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
    if logs:
        _print_local_logs(task_id, logs)
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


def _complete_workspace_decision(
    task_id: str,
    *,
    action: str,
    message: str,
    status: str,
) -> None:
    _request_json(
        "POST",
        f"{API_ROOT}/ai-executor-tasks/{task_id}/workspace-decision",
        {
            "action": action,
            "message": message,
            "runner_id": RUNNER_ID,
            "status": status,
        },
    )


def _load_pending_workspace_isolations() -> dict:
    try:
        with open(WORKSPACE_ISOLATIONS_PATH, "r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001 - local state should not stop task execution.
        print(f"Failed to load workspace isolation state: {exc}", file=sys.stderr)
        return {}
    return value if isinstance(value, dict) else {}


def _save_pending_workspace_isolations(value: dict) -> None:
    try:
        os.makedirs(os.path.dirname(WORKSPACE_ISOLATIONS_PATH), exist_ok=True)
        with open(WORKSPACE_ISOLATIONS_PATH, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception as exc:  # noqa: BLE001 - local state should not stop task execution.
        print(f"Failed to save workspace isolation state: {exc}", file=sys.stderr)


def _remember_pending_workspace(task_id: str, isolation: dict | None) -> None:
    if not isolation or isolation.get("mode") != "git_worktree":
        return
    pending = _load_pending_workspace_isolations()
    pending[task_id] = isolation
    _save_pending_workspace_isolations(pending)


def _forget_pending_workspace(task_id: str) -> None:
    pending = _load_pending_workspace_isolations()
    if task_id in pending:
        pending.pop(task_id, None)
        _save_pending_workspace_isolations(pending)


def _command_output(
    command_args: list[str],
    *,
    cwd: str,
    timeout_seconds: int = 60,
) -> tuple[int, str]:
    process = subprocess.Popen(
        command_args,
        cwd=cwd,
        env={**os.environ, "PATH": _runner_search_path()},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        **_process_group_popen_kwargs(),
    )
    try:
        output, _ = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        output, _ = process.communicate(timeout=2)
        return -9, output or ""
    return int(process.returncode or 0), output or ""


def _git(cwd: str, *args: str, timeout_seconds: int = 60) -> tuple[int, str]:
    return _command_output(["git", *args], cwd=cwd, timeout_seconds=timeout_seconds)


def _safe_path_part(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip()).strip(".-")
    return sanitized or "task"


def _prepare_isolated_workspace(task: dict, workspace_root: str) -> tuple[str, dict | None]:
    if not WORKTREE_ISOLATION_ENABLED:
        return workspace_root, None
    task_id = str(task.get("id") or "task")
    code, git_root = _git(workspace_root, "rev-parse", "--show-toplevel")
    if code != 0 or not git_root.strip():
        return workspace_root, {
            "base_workspace_root": workspace_root,
            "mode": "none",
            "reason": "not_git_repository",
            "status": "not_isolated",
            "worktree_path": workspace_root,
        }
    base_root = os.path.abspath(git_root.strip())
    repo_name = _safe_path_part(os.path.basename(base_root))
    worktree_path = os.path.join(
        os.path.dirname(base_root),
        WORKTREE_PARENT_DIR_NAME,
        repo_name,
        _safe_path_part(task_id),
    )
    branch_name = f"ai-brain/{_safe_path_part(task_id)}"
    if os.path.exists(worktree_path):
        _discard_isolated_workspace(
            {
                "base_workspace_root": base_root,
                "branch_name": branch_name,
                "worktree_path": worktree_path,
            }
        )
    os.makedirs(os.path.dirname(worktree_path), exist_ok=True)
    # git worktree add keeps AI changes outside the primary workspace until review approval.
    code, output = _git(base_root, "worktree", "add", "-b", branch_name, worktree_path, "HEAD")
    if code != 0:
        raise RuntimeError(f"git worktree add failed: {output}")
    return worktree_path, {
        "base_workspace_root": base_root,
        "branch_name": branch_name,
        "mode": "git_worktree",
        "patch_path": None,
        "status": "active",
        "worktree_path": worktree_path,
    }


def _capture_workspace_patch(isolation: dict | None) -> dict | None:
    if not isolation or isolation.get("mode") != "git_worktree":
        return isolation
    worktree_path = str(isolation.get("worktree_path") or "")
    if not worktree_path or not os.path.isdir(worktree_path):
        return {**isolation, "status": "missing_worktree"}
    _git(worktree_path, "add", "-N", ".")
    code, patch = _git(worktree_path, "diff", "--binary", "HEAD", timeout_seconds=120)
    patch_path = os.path.join(worktree_path, ".ai-brain-task.patch")
    with open(patch_path, "w", encoding="utf-8") as handle:
        handle.write(patch if code == 0 else "")
    return {
        **isolation,
        "changed": bool(patch.strip()) if code == 0 else False,
        "patch_path": patch_path,
        "status": "pending_review",
    }


def _base_workspace_has_local_changes(base_workspace_root: str) -> bool:
    code, output = _git(base_workspace_root, "status", "--porcelain", timeout_seconds=30)
    return code != 0 or bool(output.strip())


def _merge_isolated_workspace(isolation: dict) -> str:
    base_workspace_root = str(isolation.get("base_workspace_root") or "")
    patch_path = str(isolation.get("patch_path") or "")
    if not base_workspace_root or not os.path.isdir(base_workspace_root):
        raise RuntimeError("Base workspace is missing")
    if _base_workspace_has_local_changes(base_workspace_root):
        raise RuntimeError("Base workspace has local changes; refusing to apply isolated patch")
    if patch_path and os.path.exists(patch_path):
        code, output = _git(
            base_workspace_root,
            "apply",
            "--whitespace=nowarn",
            patch_path,
            timeout_seconds=120,
        )
        if code != 0:
            raise RuntimeError(f"git apply failed: {output}")
    _discard_isolated_workspace(isolation)
    return "merged isolated patch into base workspace"


def _discard_isolated_workspace(isolation: dict) -> str:
    base_workspace_root = str(isolation.get("base_workspace_root") or "")
    worktree_path = str(isolation.get("worktree_path") or "")
    branch_name = str(isolation.get("branch_name") or "")
    if base_workspace_root and os.path.isdir(base_workspace_root) and worktree_path:
        _git(
            base_workspace_root,
            "worktree",
            "remove",
            "--force",
            worktree_path,
            timeout_seconds=120,
        )
    if worktree_path and os.path.exists(worktree_path):
        shutil.rmtree(worktree_path, ignore_errors=True)
    if base_workspace_root and os.path.isdir(base_workspace_root) and branch_name:
        _git(base_workspace_root, "branch", "-D", branch_name, timeout_seconds=60)
    return "discarded isolated worktree"


def _finalize_workspace_decisions() -> None:
    pending = _load_pending_workspace_isolations()
    if not pending:
        return
    for task_id, pending_isolation in list(pending.items()):
        try:
            task_status = _task_status(task_id) or {}
            isolation = task_status.get("workspace_isolation")
            if not isinstance(isolation, dict):
                isolation = pending_isolation if isinstance(pending_isolation, dict) else {}
            decision = isolation.get("decision") if isinstance(isolation, dict) else {}
            if not isinstance(decision, dict) or decision.get("status") != "requested":
                continue
            action = str(decision.get("action") or "")
            if action == "merge":
                message = _merge_isolated_workspace(isolation)
            elif action == "discard":
                message = _discard_isolated_workspace(isolation)
            else:
                continue
            _complete_workspace_decision(
                task_id,
                action=action,
                message=message,
                status="completed",
            )
            _forget_pending_workspace(task_id)
        except Exception as exc:  # noqa: BLE001 - keep the runner alive and report the failure.
            action = str(((isolation or {}).get("decision") or {}).get("action") or "unknown")
            try:
                _complete_workspace_decision(
                    task_id,
                    action=action,
                    message=str(exc),
                    status="failed",
                )
            except Exception as report_exc:  # noqa: BLE001
                print(f"Failed to report workspace decision failure: {report_exc}", file=sys.stderr)


def _deployment_target_summaries() -> list[dict]:
    summaries: list[dict] = []
    for code, target in DEPLOYMENT_TARGETS.items():
        if not isinstance(target, dict):
            continue
        method = str(target.get("method") or "").strip().lower()
        name = str(target.get("name") or code).strip()
        if not str(code).strip() or not name or method not in {"ssh", "docker"}:
            continue
        summaries.append(
            {
                "code": str(code).strip(),
                "method": method,
                "name": name,
                "ready": bool(target.get("ready", True)),
            }
        )
    return sorted(summaries, key=lambda item: (item["method"], item["code"]))


def _heartbeat() -> None:
    metadata = {
        "capabilities": RUNNER_CAPABILITIES,
        "command_allowlist": sorted(EXECUTOR_COMMANDS.keys()),
        "command_allowlist_enforced": _command_allowlist_enforced(),
        "executors": EXECUTOR_TYPES,
        "deployment_targets": _deployment_target_summaries(),
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


def _parsed_json_output(output_preview: str):
    text = str(output_preview or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    candidates = [text]
    object_start = text.find("{")
    object_end = text.rfind("}")
    if object_start >= 0 and object_end > object_start:
        candidates.append(text[object_start:object_end + 1])
    array_start = text.find("[")
    array_end = text.rfind("]")
    if array_start >= 0 and array_end > array_start:
        candidates.append(text[array_start:array_end + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _executor_result_json(
    *,
    duration_ms: int,
    execution_workspace_root: str | None = None,
    executor_type: str,
    exit_code: int,
    output_preview: str,
    workspace_isolation: dict | None = None,
    workspace_root: str,
) -> dict:
    result_json = {
        "command_shell": False,
        "duration_ms": duration_ms,
        "executor_type": executor_type,
        "exit_code": exit_code,
        "output_preview": output_preview,
        "workspace_root": workspace_root,
    }
    if execution_workspace_root:
        result_json["execution_workspace_root"] = execution_workspace_root
    if workspace_isolation:
        result_json["workspace_isolation"] = workspace_isolation
    parsed_output = _parsed_json_output(output_preview)
    if parsed_output is not None:
        result_json["parsed_output"] = parsed_output
        result_json["result"] = (
            parsed_output if isinstance(parsed_output, dict) else {"result": parsed_output}
        )
    return result_json


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
        env={**os.environ, "PATH": _runner_search_path()},
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
                log = {"level": "info", "message": message}
                _print_local_log(task_id, log)
                pending_logs.append(log)

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
            if status in SERVER_TERMINAL_STATUSES | SERVER_CANCEL_REQUEST_STATUSES:
                server_terminal_status = status
                termination_status = _terminate_process_tree(process)
                log = {
                    "level": "warning",
                    "message": (
                        f"Task reached server terminal status {status}; "
                        f"process tree {termination_status}"
                    ),
                }
                _print_local_log(task_id, log)
                pending_logs.append(
                    log
                )
                break
        if pending_logs and (
            len(pending_logs) >= LOG_FLUSH_LINE_COUNT
            or now - last_flush_at >= LOG_FLUSH_INTERVAL_SECONDS
        ):
            _flush_log_batch(task_id, pending_logs, status="running", local_echo=False)
            last_flush_at = now

        if process.poll() is not None and reader_done:
            break
        if now >= deadline and process.poll() is None:
            timed_out = True
            termination_status = _terminate_process_tree(process)
            log = {
                "level": "error",
                "message": (
                    f"Executor timed out after {timeout_seconds}s; "
                    f"process tree {termination_status}"
                ),
            }
            _print_local_log(task_id, log)
            pending_logs.append(log)
            break

    drained_done, output_preview = _drain_output_queue(
        output_queue,
        pending_logs,
        output_preview,
    )
    reader_done = reader_done or drained_done
    if not server_terminal_status:
        _flush_log_batch(
            task_id,
            pending_logs,
            status="timed_out" if timed_out else "running",
            local_echo=False,
        )
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


def _command_basename(command_path: str) -> str:
    normalized = str(command_path or "").replace("\\", "/").rstrip("/")
    return normalized.rsplit("/", 1)[-1].lower()


def _ensure_noninteractive_codex_command(
    executor_type: str,
    command_args: list[str],
) -> list[str]:
    if executor_type != "codex" or len(command_args) != 1:
        return command_args
    if _command_basename(command_args[0]) not in {"codex", "codex.exe"}:
        return command_args
    return [command_args[0], "exec"]


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
    executable = command_args[0]
    if not os.path.dirname(executable):
        resolved = shutil.which(executable, path=_runner_search_path())
        if not resolved:
            return (
                command,
                command_args,
                (
                    f"Executable {executable!r} was not found. "
                    f"Search PATH: {_runner_search_path()}"
                ),
            )
        command_args[0] = resolved
    command_args = _ensure_noninteractive_codex_command(executor_type, command_args)
    return command, command_args, None


def _required_deployment_target_text(target: dict, field: str) -> str:
    value = str(target.get(field) or "").strip()
    if not value:
        raise ValueError(f"Deployment target field {field} is required")
    if "\x00" in value or "\n" in value or "\r" in value:
        raise ValueError(f"Deployment target field {field} is invalid")
    return value


def _deployment_ssh_command(target: dict) -> list[str]:
    host = _required_deployment_target_text(target, "host")
    username = _required_deployment_target_text(target, "username")
    identity_file = _required_deployment_target_text(target, "identity_file")
    known_hosts_file = _required_deployment_target_text(target, "known_hosts_file")
    remote_command = _required_deployment_target_text(target, "remote_command")
    port = int(target.get("port") or 22)
    if port < 1 or port > 65535:
        raise ValueError("Deployment target port is invalid")
    return [
        "ssh",
        "-p",
        str(port),
        "-i",
        identity_file,
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={known_hosts_file}",
        f"{username}@{host}",
        remote_command,
    ]


def _deployment_docker_commands(target: dict) -> list[dict]:
    working_directory = _required_deployment_target_text(target, "working_directory")
    compose_files = _string_list(target.get("compose_files"))
    if not compose_files:
        raise ValueError("Deployment target compose_files is required")
    project_name = _required_deployment_target_text(target, "project_name")
    services = _string_list(target.get("services"))
    common = ["docker", "compose"]
    for compose_file in compose_files:
        common.extend(["-f", compose_file])
    common.extend(["--project-name", project_name])
    commands: list[dict] = []
    if bool(target.get("pull", False)):
        commands.append(
            {"argv": [*common, "pull", *services], "cwd": working_directory}
        )
    commands.append(
        {
            "argv": [*common, "up", "-d", "--remove-orphans", *services],
            "cwd": working_directory,
        }
    )
    return commands


def _deployment_result_json(
    *,
    deployment_method: str,
    duration_ms: int,
    exit_code: int,
    output_preview: str,
    target_code: str,
) -> dict:
    return {
        "command_shell": False,
        "deployment_method": deployment_method,
        "duration_ms": duration_ms,
        "executor_type": "deployment",
        "exit_code": exit_code,
        "output_preview": output_preview,
        "target_code": target_code,
    }


def _run_deployment_task(task: dict) -> None:
    task_id = str(task["id"])
    input_payload = task.get("input_payload")
    if not isinstance(input_payload, dict):
        input_payload = {}
    target_code = str(input_payload.get("target_code") or "").strip()
    deployment_method = str(input_payload.get("deployment_method") or "").strip().lower()
    timeout_seconds = int(task.get("timeout_seconds") or 1800)
    target = DEPLOYMENT_TARGETS.get(target_code)
    if (
        not target_code
        or not isinstance(target, dict)
        or deployment_method not in {"ssh", "docker"}
        or str(target.get("method") or "").strip().lower() != deployment_method
        or not bool(target.get("ready", True))
    ):
        _complete_task(
            task_id,
            status="failed",
            error_code="DEPLOYMENT_TARGET_UNAVAILABLE",
            error_message="Configured deployment target is unavailable",
            result_json={
                "deployment_method": deployment_method,
                "executor_type": "deployment",
                "target_code": target_code,
            },
        )
        return
    started_at = time.time()
    output_preview = ""
    try:
        if deployment_method == "ssh":
            commands = [
                {
                    "argv": _deployment_ssh_command(target),
                    "cwd": os.path.dirname(os.path.abspath(CONFIG_PATH)),
                }
            ]
        else:
            commands = _deployment_docker_commands(target)
        _append_logs(
            task_id,
            [
                {
                    "level": "info",
                    "message": f"Starting {deployment_method} deployment target {target_code}",
                }
            ],
            status="running",
        )
        exit_code = 0
        for command in commands:
            exit_code, preview, timed_out, server_status = _stream_process_output(
                command_args=list(command["argv"]),
                instruction=json.dumps(input_payload, ensure_ascii=False),
                task_id=task_id,
                timeout_seconds=timeout_seconds,
                workspace_root=str(command["cwd"]),
            )
            output_preview = (output_preview + preview)[-MAX_OUTPUT_PREVIEW_CHARS:]
            duration_ms = int((time.time() - started_at) * 1000)
            if server_status == "cancel_requested":
                _complete_task(
                    task_id,
                    status="cancelled",
                    error_code="AI_EXECUTOR_TASK_CANCELLED",
                    error_message="Deployment cancelled by platform request",
                    result_json=_deployment_result_json(
                        deployment_method=deployment_method,
                        duration_ms=duration_ms,
                        exit_code=exit_code,
                        output_preview=output_preview,
                        target_code=target_code,
                    ),
                )
                return
            if server_status:
                return
            if timed_out:
                _complete_task(
                    task_id,
                    status="timed_out",
                    error_code="AI_EXECUTOR_TASK_TIMEOUT",
                    error_message=f"Deployment timed out after {timeout_seconds}s",
                    result_json=_deployment_result_json(
                        deployment_method=deployment_method,
                        duration_ms=duration_ms,
                        exit_code=exit_code,
                        output_preview=output_preview,
                        target_code=target_code,
                    ),
                )
                return
            if exit_code != 0:
                _complete_task(
                    task_id,
                    status="failed",
                    error_code="DEPLOYMENT_COMMAND_FAILED",
                    error_message=output_preview or "Deployment command failed",
                    result_json=_deployment_result_json(
                        deployment_method=deployment_method,
                        duration_ms=duration_ms,
                        exit_code=exit_code,
                        output_preview=output_preview,
                        target_code=target_code,
                    ),
                )
                return
        duration_ms = int((time.time() - started_at) * 1000)
        _complete_task(
            task_id,
            status="succeeded",
            error_code=None,
            error_message=None,
            logs=[
                {
                    "level": "info",
                    "message": f"Deployment target {target_code} completed",
                }
            ],
            result_json=_deployment_result_json(
                deployment_method=deployment_method,
                duration_ms=duration_ms,
                exit_code=exit_code,
                output_preview=output_preview,
                target_code=target_code,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - report bounded local execution errors.
        _complete_task(
            task_id,
            status="failed",
            error_code="DEPLOYMENT_EXECUTION_FAILED",
            error_message=f"Deployment execution failed: {type(exc).__name__}",
            result_json={
                "deployment_method": deployment_method,
                "executor_type": "deployment",
                "target_code": target_code,
            },
        )


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
    if executor_type == "deployment":
        _run_deployment_task(task)
        return
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
                "command": command,
                "command_args": command_args,
                "command_allowlist_enforced": _command_allowlist_enforced(),
                "executor_type": executor_type,
                "search_path": _runner_search_path(),
            },
        )
        return
    started_at = time.time()
    execution_workspace_root = workspace_root
    workspace_isolation: dict | None = None
    try:
        execution_workspace_root, workspace_isolation = _prepare_isolated_workspace(
            task,
            workspace_root,
        )
        _append_logs(
            task_id,
            [
                {
                    "level": "info",
                    "message": f"Starting {executor_type} in {execution_workspace_root}",
                }
            ],
            status="running",
        )
        exit_code, preview, timed_out, server_terminal_status = _stream_process_output(
            command_args=command_args,
            instruction=instruction,
            task_id=task_id,
            timeout_seconds=timeout_seconds,
            workspace_root=execution_workspace_root,
        )
        duration_ms = int((time.time() - started_at) * 1000)
        if server_terminal_status == "cancel_requested":
            if workspace_isolation and workspace_isolation.get("mode") == "git_worktree":
                _discard_isolated_workspace(workspace_isolation)
                workspace_isolation = {
                    **workspace_isolation,
                    "status": "discarded_after_cancel",
                }
            _complete_task(
                task_id,
                status="cancelled",
                error_code="AI_EXECUTOR_TASK_CANCELLED",
                error_message="Task cancelled by platform request",
                result_json=_executor_result_json(
                    duration_ms=duration_ms,
                    execution_workspace_root=execution_workspace_root,
                    executor_type=executor_type,
                    exit_code=exit_code,
                    output_preview=preview,
                    workspace_isolation=workspace_isolation,
                    workspace_root=workspace_root,
                ),
            )
            return
        if server_terminal_status:
            print(
                f"Task {task_id} already reached server terminal status "
                f"{server_terminal_status}; local completion skipped.",
                file=sys.stderr,
            )
            if workspace_isolation and workspace_isolation.get("mode") == "git_worktree":
                _discard_isolated_workspace(workspace_isolation)
            return
        workspace_isolation = _capture_workspace_patch(workspace_isolation)
        if timed_out:
            if workspace_isolation and workspace_isolation.get("mode") == "git_worktree":
                _discard_isolated_workspace(workspace_isolation)
                workspace_isolation = {
                    **workspace_isolation,
                    "status": "discarded_after_timeout",
                }
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
                result_json=_executor_result_json(
                    duration_ms=duration_ms,
                    execution_workspace_root=execution_workspace_root,
                    executor_type=executor_type,
                    exit_code=exit_code,
                    output_preview=preview,
                    workspace_isolation=workspace_isolation,
                    workspace_root=workspace_root,
                ),
            )
            return
        status = "succeeded" if exit_code == 0 else "failed"
        if status == "succeeded":
            _remember_pending_workspace(task_id, workspace_isolation)
        elif workspace_isolation and workspace_isolation.get("mode") == "git_worktree":
            _discard_isolated_workspace(workspace_isolation)
            workspace_isolation = {
                **workspace_isolation,
                "status": "discarded_after_failure",
            }
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
            result_json=_executor_result_json(
                duration_ms=duration_ms,
                execution_workspace_root=execution_workspace_root,
                executor_type=executor_type,
                exit_code=exit_code,
                output_preview=preview,
                workspace_isolation=workspace_isolation,
                workspace_root=workspace_root,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - runner must report failures to AI Brain.
        if workspace_isolation and workspace_isolation.get("mode") == "git_worktree":
            try:
                _discard_isolated_workspace(workspace_isolation)
                workspace_isolation = {
                    **workspace_isolation,
                    "status": "discarded_after_exception",
                }
            except Exception as cleanup_exc:  # noqa: BLE001
                print(f"Failed to discard isolated workspace: {cleanup_exc}", file=sys.stderr)
        _complete_task(
            task_id,
            status="failed",
            error_code=exc.__class__.__name__,
            error_message=str(exc),
            result_json={
                "execution_workspace_root": execution_workspace_root,
                "executor_type": executor_type,
                "workspace_isolation": workspace_isolation,
                "workspace_root": workspace_root,
            },
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
            _finalize_workspace_decisions()
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
Runner 默认仍会把任务日志同步到 AI Brain，但不在本机后台控制台打印执行日志；
如需排查本地执行过程，可在 `ai-brain-runner.env` 中设置
`AI_BRAIN_RUNNER_PRINT_BACKGROUND_LOGS=true` 后重启 Runner。

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
