from __future__ import annotations

import hashlib
import json
import secrets
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from time import perf_counter
from typing import Any

from fastapi import Request

from app.api.deps import api_error, require_permissions
from app.core.listing import add_list_observability, sort_list_items
from app.services.operational_records import record_audit_event, save_single_repository_record
from app.services.product_scope import product_scope_filter, user_can_read_product

SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID = "ai_executor_runner_system_default"
SYSTEM_DEFAULT_AI_EXECUTOR_TYPE = "model_gateway"
AI_EXECUTOR_TYPES = {
    SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
    "claude",
    "codex",
    "hermes",
    "openclaw",
}
AI_EXECUTOR_LOCAL_RUNNER_TYPES = AI_EXECUTOR_TYPES - {SYSTEM_DEFAULT_AI_EXECUTOR_TYPE}
AI_EXECUTOR_RUNNER_PROTOCOLS = {"mcp_http", "mcp_stdio", "runner_polling", "runner_websocket"}
AI_EXECUTOR_RUNNER_STATUSES = {"active", "disabled", "offline"}
AI_EXECUTOR_RUNNER_PACKAGE_OSES = {"docker", "linux", "macos", "manual", "windows"}
AI_EXECUTOR_RUNNER_PACKAGE_ARCHES = {"amd64", "arm64", "universal"}
AI_EXECUTOR_RUNNER_INSTALL_MODES_BY_OS = {
    "docker": {"docker"},
    "linux": {"shell", "systemd"},
    "macos": {"launchd", "shell"},
    "manual": {"manual"},
    "windows": {"powershell", "service"},
}
AI_EXECUTOR_RUNNER_DEFAULT_INSTALL_MODE_BY_OS = {
    "docker": "docker",
    "linux": "systemd",
    "macos": "launchd",
    "manual": "manual",
    "windows": "service",
}
AI_EXECUTOR_TASK_STATUSES = {
    "cancelled",
    "claimed",
    "failed",
    "queued",
    "running",
    "succeeded",
    "timed_out",
}
AI_EXECUTOR_TASK_TERMINAL_STATUSES = {"cancelled", "failed", "succeeded", "timed_out"}
AI_EXECUTOR_TASK_SORT_FIELDS = {
    "claimed_at",
    "created_at",
    "executor_type",
    "finished_at",
    "id",
    "runner_id",
    "scheduled_job_run_id",
    "status",
    "updated_at",
}
AI_EXECUTOR_RUNNER_SORT_FIELDS = {
    "created_at",
    "endpoint_url",
    "id",
    "last_heartbeat_at",
    "name",
    "protocol",
    "status",
    "updated_at",
}


def _ensure_admin(user: dict[str, Any]) -> None:
    require_permissions(user, {"system.plugins.manage"})


def _ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def _ensure_enum(value: str | None, allowed_values: set[str], field: str) -> str:
    normalized = _ensure_non_blank(value, field).lower()
    if normalized not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")
    return normalized


def _normalized_string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise api_error(400, "VALIDATION_ERROR", f"{field} must be an array")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _normalized_executor_types(value: Any) -> list[str]:
    executor_types = _normalized_string_list(value, "executor_types")
    if not executor_types:
        executor_types = ["codex"]
    for executor_type in executor_types:
        _ensure_enum(executor_type, AI_EXECUTOR_LOCAL_RUNNER_TYPES, "executor_type")
    return executor_types


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _is_system_default_runner_id(runner_id: str | None) -> bool:
    return runner_id == SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID


def _is_system_default_runner(runner: dict[str, Any]) -> bool:
    metadata = runner.get("metadata") if isinstance(runner.get("metadata"), dict) else {}
    return (
        runner.get("id") == SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID
        or runner.get("protocol") == SYSTEM_DEFAULT_AI_EXECUTOR_TYPE
        or metadata.get("is_system") is True
    )


def system_default_ai_executor_runner() -> dict[str, Any]:
    return {
        "created_at": "1970-01-01T00:00:00+00:00",
        "created_by": "system",
        "endpoint_url": "model-gateway://default",
        "executor_types": [SYSTEM_DEFAULT_AI_EXECUTOR_TYPE],
        "heartbeat_timeout_seconds": 0,
        "id": SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
        "last_heartbeat_at": None,
        "max_concurrent_tasks": 0,
        "metadata": {
            "description": "使用系统默认 AI 大模型执行指令，无需本地 Runner。",
            "is_system": True,
            "managed_by": "ai_brain",
        },
        "name": "系统默认执行器",
        "protocol": SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
        "status": "active",
        "token_hash": "",
        "token_rotated_at": None,
        "token_version": 0,
        "updated_at": "9999-12-31T00:00:00+00:00",
        "workspace_roots": ["*"],
    }


def _runner_public(runner: dict[str, Any]) -> dict[str, Any]:
    public = dict(runner)
    public.pop("token_hash", None)
    public["token_configured"] = (
        False if _is_system_default_runner(runner) else bool(runner.get("token_hash"))
    )
    heartbeat_age = _heartbeat_age_seconds(runner.get("last_heartbeat_at"))
    public["heartbeat_age_seconds"] = heartbeat_age
    public["health_status"] = _runner_health_status(runner, heartbeat_age)
    public["setup_command"] = _runner_setup_command(runner)
    public["token_rotated_at"] = runner.get("token_rotated_at")
    public["token_version"] = int(runner.get("token_version") or 1)
    return public


def _task_public(task: dict[str, Any]) -> dict[str, Any]:
    return dict(task)


def _heartbeat_age_seconds(value: Any) -> int | None:
    if not value:
        return None
    try:
        heartbeat_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if heartbeat_at.tzinfo is None:
        heartbeat_at = heartbeat_at.replace(tzinfo=UTC)
    return max(0, int((datetime.now(UTC) - heartbeat_at.astimezone(UTC)).total_seconds()))


def _runner_health_status(runner: dict[str, Any], heartbeat_age: int | None) -> str:
    if _is_system_default_runner(runner):
        return "managed"
    if runner.get("status") == "disabled":
        return "disabled"
    if runner.get("status") == "offline":
        return "offline"
    if heartbeat_age is None:
        return "never_connected"
    timeout_seconds = int(runner.get("heartbeat_timeout_seconds") or 120)
    return "online" if heartbeat_age <= timeout_seconds else "offline"


def _runner_setup_command(runner: dict[str, Any]) -> str:
    if _is_system_default_runner(runner):
        return "使用系统默认 AI 大模型执行，无需启动本地 Runner"
    executor_types = ",".join(str(item) for item in runner.get("executor_types") or ["codex"])
    workspace_roots = ",".join(str(item) for item in runner.get("workspace_roots") or ["*"])
    return (
        "ai-brain-runner start "
        f"--runner-id {runner.get('id')} "
        "--token <runner_token> "
        f"--endpoint {runner.get('endpoint_url') or 'runner://local'} "
        f"--executors {executor_types} "
        f"--workspace-roots {workspace_roots}"
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
    }


def _runner_executor_commands(runner: dict[str, Any]) -> dict[str, str]:
    metadata = runner.get("metadata") if isinstance(runner.get("metadata"), dict) else {}
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
            "AI_BRAIN_RUNNER_CONFIG=./runner_config.json",
            f"AI_BRAIN_TARGET_OS={package_options['target_os']}",
            f"AI_BRAIN_PACKAGE_ARCH={package_options['arch']}",
            f"AI_BRAIN_INSTALL_MODE={package_options['install_mode']}",
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
            "require_human_review_for_git_push": True,
            "workspace_roots_enforced": True,
        },
    }
    return json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _runner_start_command_block() -> str:
    return """exec ai-brain-runner start \\
  --runner-id "${AI_BRAIN_RUNNER_ID}" \\
  --token "${AI_BRAIN_RUNNER_TOKEN}" \\
  --endpoint "${AI_BRAIN_ENDPOINT}" \\
  --executors "${AI_BRAIN_EXECUTORS}" \\
  --workspace-roots "${AI_BRAIN_WORKSPACE_ROOTS}"
"""


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
& ai-brain-runner start `
  --runner-id "$env:AI_BRAIN_RUNNER_ID" `
  --token "$env:AI_BRAIN_RUNNER_TOKEN" `
  --endpoint "$env:AI_BRAIN_ENDPOINT" `
  --executors "$env:AI_BRAIN_EXECUTORS" `
  --workspace-roots "$env:AI_BRAIN_WORKSPACE_ROOTS"
"""


def _runner_manual_shell_script() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"
set -a
source ai-brain-runner.env
set +a
exec ai-brain-runner start \\
  --runner-id "${AI_BRAIN_RUNNER_ID}" \\
  --token "${AI_BRAIN_RUNNER_TOKEN}" \\
  --endpoint "${AI_BRAIN_ENDPOINT}" \\
  --executors "${AI_BRAIN_EXECUTORS}" \\
  --workspace-roots "${AI_BRAIN_WORKSPACE_ROOTS}"
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
& ai-brain-runner start `
  --runner-id "$env:AI_BRAIN_RUNNER_ID" `
  --token "$env:AI_BRAIN_RUNNER_TOKEN" `
  --endpoint "$env:AI_BRAIN_ENDPOINT" `
  --executors "$env:AI_BRAIN_EXECUTORS" `
  --workspace-roots "$env:AI_BRAIN_WORKSPACE_ROOTS"
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
RUN chmod +x scripts/start-runner.sh || true
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

## 安装步骤

1. 在远程机器安装需要的执行器 CLI，例如 Codex、Claude Code、Hermes 或 OpenClaw。
2. 解压本安装包。
3. 编辑 `ai-brain-runner.env`，把 `AI_BRAIN_RUNNER_TOKEN=<runner_token>`
   替换为创建或轮换 Runner 时返回的一次性 Token。
4. {install_hint_by_os[target_os]}
5. 回到 AI Brain 插件管理 / 执行器页面，确认健康状态变为 `online`。

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
def create_ai_executor_runner_install_package_response(
    *,
    arch: str | None = None,
    current_store: Any,
    install_mode: str | None = None,
    runner_id: str,
    target_os: str | None = None,
    user: dict[str, Any],
) -> tuple[bytes, str]:
    _ensure_admin(user)
    if _is_system_default_runner_id(runner_id):
        raise api_error(
            409,
            "AI_EXECUTOR_SYSTEM_RUNNER_LOCKED",
            "系统默认执行器由平台托管，不需要 Runner 安装包",
        )
    sync_ai_executor_runner_store(current_store)
    runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")

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
        archive.writestr("runner_config.json", _runner_config_json(runner, package_options))
        archive.writestr("skills/ai-brain-runner/SKILL.md", _runner_skill_markdown(runner))
        for filename, content in _runner_install_assets(runner, package_options).items():
            archive.writestr(filename, content)
    return buffer.getvalue(), _runner_package_filename(runner_id, package_options)


def _repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    required = (
        "list_ai_executor_runners",
        "list_ai_executor_tasks",
        "save_ai_executor_runner_record",
        "save_ai_executor_task_record",
    )
    if repository is not None and all(
        callable(getattr(repository, name, None)) for name in required
    ):
        return repository
    return None


RUNNER_RECORD_METHOD_COLLECTIONS = {
    "save_ai_executor_runner_record": "ai_executor_runners",
    "save_ai_executor_task_record": "ai_executor_tasks",
    "save_collector_run_record": "collector_runs",
    "save_plugin_invocation_log_record": "plugin_invocation_logs",
    "save_scheduled_job_record": "scheduled_jobs",
    "save_scheduled_job_run_record": "scheduled_job_runs",
}


def _read_collection(
    current_store: Any,
    collection_name: str,
) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, {})
    return collection if isinstance(collection, dict) else {}


def _read_record(
    current_store: Any,
    collection_name: str,
    record_id: str | None,
) -> dict[str, Any] | None:
    if record_id is None:
        return None
    item = _read_collection(current_store, collection_name).get(str(record_id))
    return item if isinstance(item, dict) else None


def _memory_collection(
    current_store: Any,
    collection_name: str,
) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name)
    if not isinstance(collection, dict):
        raise TypeError(f"Runner record collection is not mutable: {collection_name}")
    return collection


def _memory_collection_for_method(
    current_store: Any,
    method_name: str,
) -> dict[str, dict[str, Any]]:
    collection_name = RUNNER_RECORD_METHOD_COLLECTIONS.get(method_name)
    if collection_name is None:
        raise ValueError(f"Unsupported runner record save method: {method_name}")
    return _memory_collection(current_store, collection_name)


def _replace_collection(
    current_store: Any,
    collection_name: str,
    items: list[dict[str, Any]],
) -> None:
    setattr(
        current_store,
        collection_name,
        {str(item["id"]): dict(item) for item in items if item.get("id") is not None},
    )


def sync_ai_executor_runner_store(current_store: Any, *, status: str | None = None) -> None:
    repository = _repository(current_store)
    if repository is None:
        return
    _replace_collection(
        current_store,
        "ai_executor_runners",
        repository.list_ai_executor_runners(status=status),
    )


def _runner_matches_filters(
    runner: dict[str, Any],
    *,
    executor_type: str | None = None,
    keyword: str | None = None,
    protocol: str | None = None,
    status: str | None = None,
) -> bool:
    if status is not None and runner.get("status") != status:
        return False
    if protocol is not None and runner.get("protocol") != protocol:
        return False
    if executor_type is not None and executor_type not in (runner.get("executor_types") or []):
        return False
    normalized_keyword = str(keyword or "").strip().lower()
    if normalized_keyword:
        searchable = " ".join(
            str(runner.get(field) or "").lower()
            for field in ("id", "name", "endpoint_url", "protocol")
        )
        if normalized_keyword not in searchable:
            return False
    return True


def _latest_task_for_runner(current_store: Any, runner_id: str | None) -> dict[str, Any] | None:
    if runner_id is None:
        return None
    return max(
        (
            task
            for task in _read_collection(current_store, "ai_executor_tasks").values()
            if task.get("runner_id") == runner_id
        ),
        key=lambda task: (
            task.get("updated_at") or task.get("created_at") or "",
            task.get("id") or "",
        ),
        default=None,
    )


def _runner_public_with_latest_task(
    current_store: Any,
    runner: dict[str, Any],
) -> dict[str, Any]:
    item = _runner_public(runner)
    latest_task = _latest_task_for_runner(current_store, runner.get("id"))
    if latest_task is not None:
        item["latest_task_id"] = latest_task.get("id")
        item["latest_task_status"] = latest_task.get("status")
    return item


def sync_ai_executor_task_store(
    current_store: Any,
    *,
    ai_task_id: str | None = None,
    product_scope_ids: list[str] | None = None,
    runner_id: str | None = None,
    scheduled_job_run_id: str | None = None,
    status: str | None = None,
) -> None:
    repository = _repository(current_store)
    if repository is None:
        return
    _replace_collection(
        current_store,
        "ai_executor_tasks",
        repository.list_ai_executor_tasks(
            ai_task_id=ai_task_id,
            product_scope_ids=product_scope_ids,
            runner_id=runner_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        ),
    )


def _persist_record(
    current_store: Any,
    method_name: str,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, method_name, None)
    if callable(save_record):
        save_single_repository_record(current_store, method_name, record, audit_event=audit_event)
        return
    if repository is None:
        _memory_collection_for_method(current_store, method_name)[record["id"]] = record


def _delete_runner_record(
    current_store: Any,
    *,
    audit_event: dict[str, Any] | None = None,
    collection_name: str,
    method_name: str,
    record_id: str,
) -> None:
    repository = getattr(current_store, "repository", None)
    delete_record = getattr(repository, method_name, None)
    if callable(delete_record):
        delete_record(record_id, audit_event=audit_event)
        return
    if repository is None:
        collection = getattr(current_store, collection_name)
        if isinstance(collection, dict):
            collection.pop(record_id, None)


def _load_scheduled_job_run(current_store: Any, task: dict[str, Any]) -> dict[str, Any] | None:
    run_id = task.get("scheduled_job_run_id")
    if not run_id:
        return None
    run = _read_record(current_store, "scheduled_job_runs", run_id)
    if run is not None:
        return run
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_scheduled_job_runs", None)
    if callable(list_runs):
        for candidate in list_runs(scheduled_job_id=task.get("scheduled_job_id")):
            if candidate.get("id") == run_id:
                return candidate
    return None


def _load_plugin_invocation_log(current_store: Any, task: dict[str, Any]) -> dict[str, Any] | None:
    log_id = task.get("plugin_invocation_log_id")
    if not log_id:
        return None
    log = _read_record(current_store, "plugin_invocation_logs", log_id)
    if log is not None:
        return log
    repository = getattr(current_store, "repository", None)
    list_logs = getattr(repository, "list_plugin_invocation_logs", None)
    if callable(list_logs):
        for candidate in list_logs(scheduled_job_run_id=task.get("scheduled_job_run_id")):
            if candidate.get("id") == log_id:
                return candidate
    return None


def _load_collector_run(current_store: Any, collector_run_id: str | None) -> dict[str, Any] | None:
    if not collector_run_id:
        return None
    collector_run = _read_record(current_store, "collector_runs", collector_run_id)
    if collector_run is not None:
        return collector_run
    repository = getattr(current_store, "repository", None)
    list_collector_runs = getattr(repository, "list_collector_runs", None)
    if callable(list_collector_runs):
        for candidate in list_collector_runs():
            if candidate.get("id") == collector_run_id:
                return candidate
    return None


def _load_scheduled_job(current_store: Any, scheduled_job_id: str | None) -> dict[str, Any] | None:
    if not scheduled_job_id:
        return None
    job = _read_record(current_store, "scheduled_jobs", scheduled_job_id)
    if job is not None:
        return job
    repository = getattr(current_store, "repository", None)
    list_jobs = getattr(repository, "list_scheduled_jobs", None)
    if callable(list_jobs):
        for candidate in list_jobs():
            if candidate.get("id") == scheduled_job_id:
                return candidate
    return None


def _load_ai_task(current_store: Any, ai_task_id: str | None) -> dict[str, Any] | None:
    if not ai_task_id:
        return None
    task = _read_record(current_store, "ai_tasks", ai_task_id)
    if task is not None:
        return task
    repository = getattr(current_store, "repository", None)
    load_ai_tasks = getattr(repository, "load_ai_tasks", None)
    if callable(load_ai_tasks):
        payload = load_ai_tasks()
        for candidate in payload.get("ai_tasks", {}).values():
            if candidate.get("id") == ai_task_id:
                return candidate
        return _read_record(current_store, "ai_tasks", ai_task_id)
    return None


def _ai_executor_task_product_id(current_store: Any, task: dict[str, Any]) -> Any:
    if task.get("product_id") is not None:
        return task.get("product_id")
    job = _load_scheduled_job(current_store, task.get("scheduled_job_id"))
    if job is not None and job.get("product_id") is not None:
        return job.get("product_id")
    run = _load_scheduled_job_run(current_store, task)
    if run is not None:
        config_snapshot = run.get("config_snapshot")
        if isinstance(config_snapshot, dict) and config_snapshot.get("product_id") is not None:
            return config_snapshot.get("product_id")
        run_job = _load_scheduled_job(current_store, run.get("scheduled_job_id"))
        if run_job is not None and run_job.get("product_id") is not None:
            return run_job.get("product_id")
    ai_task = _load_ai_task(current_store, task.get("ai_task_id"))
    if ai_task is not None:
        return ai_task.get("product_id")
    return None


def _ai_executor_task_visible_to_user(
    current_store: Any,
    *,
    task: dict[str, Any],
    user: dict[str, Any],
) -> bool:
    return user_can_read_product(user, _ai_executor_task_product_id(current_store, task))


def _runner_node_from_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "error_code": task.get("error_code"),
        "error_message": task.get("error_message"),
        "executor_type": task.get("executor_type"),
        "finished_at": task.get("finished_at"),
        "label": "AI 执行器执行内容",
        "logs": task.get("logs") or [],
        "result_json": task.get("result_json") or {},
        "runner_id": task.get("runner_id"),
        "runner_task_id": task.get("id"),
        "status": task.get("status"),
        "workspace_root": task.get("workspace_root"),
    }


def _persist_task_state_records(
    current_store: Any,
    *,
    audit_events: list[dict[str, Any]],
    reviews: list[dict[str, Any]] | None,
    task: dict[str, Any],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_task_state_records", None)
    if callable(save_records):
        save_records(task=task, audit_events=audit_events, reviews=reviews)
        return
    if repository is None:
        _memory_collection(current_store, "ai_tasks")[task["id"]] = task
        for review in reviews or []:
            _memory_collection(current_store, "human_reviews")[review["id"]] = review


def _existing_pending_review(
    current_store: Any,
    ai_task_id: str,
    stage: str,
) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    load_workflow_runtime = getattr(repository, "load_workflow_runtime", None)
    if callable(load_workflow_runtime):
        payload = load_workflow_runtime()
        for review in payload.get("human_reviews", {}).values():
            if (
                review.get("ai_task_id") == ai_task_id
                and review.get("stage") == stage
                and review.get("status") == "pending"
            ):
                return review
    for review in _read_collection(current_store, "human_reviews").values():
        if (
            review.get("ai_task_id") == ai_task_id
            and review.get("stage") == stage
            and review.get("status") == "pending"
        ):
            return review
    return None


def _sync_runner_completion_to_ai_task(
    current_store: Any,
    *,
    task: dict[str, Any],
    runner_id: str,
) -> None:
    ai_task = _load_ai_task(current_store, task.get("ai_task_id"))
    if ai_task is None:
        return
    runner_status = str(task.get("status") or "running")
    now = datetime.now(UTC).isoformat()
    executor_snapshot = {
        "executor_type": task.get("executor_type"),
        "runner_id": task.get("runner_id"),
        "runner_task_id": task.get("id"),
        "status": runner_status,
        "workspace_root": task.get("workspace_root"),
    }
    if runner_status in {"queued", "claimed", "running"}:
        updated_task = {
            **ai_task,
            "current_step": "waiting_ai_executor",
            "input_json": {
                **dict(ai_task.get("input_json") or {}),
                "executor": executor_snapshot,
            },
            "status": "running",
            "updated_at": now,
        }
        audit_event = record_audit_event(
            current_store,
            event_type="ai_task.executor_waiting",
            actor_id=runner_id,
            subject_type="ai_task",
            subject_id=updated_task["id"],
            payload={"ai_task_id": updated_task["id"], **executor_snapshot},
        )
        _persist_task_state_records(
            current_store,
            audit_events=[audit_event],
            reviews=None,
            task=updated_task,
        )
        return

    if runner_status == "succeeded":
        output_json = {
            "executor": {
                **executor_snapshot,
                "finished_at": task.get("finished_at"),
            },
            "result": task.get("result_json") or {},
        }
        updated_task = {
            **ai_task,
            "current_step": "executor_completed",
            "output_json": output_json,
            "status": "waiting_review",
            "updated_at": now,
        }
        reviews: list[dict[str, Any]] = []
        existing_review = _existing_pending_review(
            current_store,
            updated_task["id"],
            str(updated_task.get("task_type") or "executor_result"),
        )
        if existing_review is None:
            review_id = current_store.new_id("review")
            review = {
                "ai_task_id": updated_task["id"],
                "content": output_json,
                "created_at": now,
                "decided_at": None,
                "decided_by": None,
                "decision_reason": None,
                "id": review_id,
                "questions": [],
                "stage": updated_task.get("task_type") or "executor_result",
                "status": "pending",
                "updated_at": now,
                "version": 1,
            }
            reviews.append(review)
        review_ids = list(updated_task.get("review_ids") or [])
        for review in reviews or ([existing_review] if existing_review else []):
            if review and review["id"] not in review_ids:
                review_ids.append(review["id"])
        updated_task = {
            **updated_task,
            "review_ids": review_ids,
        }
        audit_event = record_audit_event(
            current_store,
            event_type="ai_task.executor_completed",
            actor_id=runner_id,
            subject_type="ai_task",
            subject_id=updated_task["id"],
            payload={"ai_task_id": updated_task["id"], **executor_snapshot},
        )
        _persist_task_state_records(
            current_store,
            audit_events=[audit_event],
            reviews=reviews or None,
            task=updated_task,
        )
        return

    next_status = "cancelled" if runner_status == "cancelled" else "failed"
    updated_task = {
        **ai_task,
        "current_step": "executor_failed",
        "error_code": task.get("error_code") or "AI_EXECUTOR_TASK_FAILED",
        "error_message": task.get("error_message") or "AI executor task failed",
        "output_json": {
            "executor": executor_snapshot,
            "result": task.get("result_json") or {},
        },
        "status": next_status,
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="ai_task.executor_failed",
        actor_id=runner_id,
        subject_type="ai_task",
        subject_id=updated_task["id"],
        payload={
            "ai_task_id": updated_task["id"],
            **executor_snapshot,
            "error_code": updated_task.get("error_code"),
            "error_message": updated_task.get("error_message"),
        },
    )
    _persist_task_state_records(
        current_store,
        audit_events=[audit_event],
        reviews=None,
        task=updated_task,
    )


def _status_for_runner_task(task_status: str) -> str:
    if task_status == "succeeded":
        return "succeeded"
    if task_status == "cancelled":
        return "cancelled"
    if task_status in {"failed", "timed_out"}:
        return "failed"
    return "running"


def _records_imported_from_runner_result(task: dict[str, Any], fallback: int = 0) -> int:
    result_json = task.get("result_json")
    if isinstance(result_json, dict):
        for key in ("records_imported", "finding_count", "row_count", "count"):
            value = result_json.get(key)
            if isinstance(value, int) and value >= 0:
                return value
    return fallback


def _sync_runner_completion_to_scheduled_run(
    current_store: Any,
    *,
    task: dict[str, Any],
    runner_id: str,
) -> None:
    run = _load_scheduled_job_run(current_store, task)
    if run is None:
        return
    now = datetime.now(UTC).isoformat()
    runner_node = _runner_node_from_task(task)
    result_summary = dict(run.get("result_summary") or {})
    execution_nodes = dict(result_summary.get("execution_nodes") or {})
    execution_nodes["runner_execution"] = runner_node
    result_action = dict(execution_nodes.get("result_action") or {})
    if result_action:
        feedback = dict(result_action.get("feedback") or {})
        feedback["runner_result"] = task.get("result_json") or {}
        result_action["feedback"] = feedback
        result_action["status"] = _status_for_runner_task(str(task.get("status") or "running"))
        execution_nodes["result_action"] = result_action
    result_summary["execution_nodes"] = execution_nodes

    log = _load_plugin_invocation_log(current_store, task)
    if log is not None:
        response_summary = dict(log.get("response_summary") or {})
        response_summary["runner"] = runner_node
        json_payload = dict(response_summary.get("json") or {})
        json_payload.update(
            {
                "executor_type": task.get("executor_type"),
                "result_json": task.get("result_json") or {},
                "runner_id": task.get("runner_id"),
                "runner_task_id": task.get("id"),
                "status": task.get("status"),
                "workspace_root": task.get("workspace_root"),
            },
        )
        response_summary["json"] = json_payload
        log_status = log.get("status") or "succeeded"
        if task.get("status") in {"failed", "cancelled", "timed_out"}:
            log_status = "failed"
        updated_log = {
            **log,
            "error_code": task.get("error_code"),
            "error_message": task.get("error_message"),
            "response_summary": response_summary,
            "status": log_status,
            "updated_at": now,
        }
        _persist_record(current_store, "save_plugin_invocation_log_record", updated_log)
        plugin_summary = dict(result_summary.get("plugin") or {})
        if plugin_summary:
            plugin_summary.update(
                {
                    "error_code": updated_log.get("error_code"),
                    "error_message": updated_log.get("error_message"),
                    "response_summary": response_summary,
                    "status": log_status,
                },
            )
            result_summary["plugin"] = plugin_summary

    run_status = _status_for_runner_task(str(task.get("status") or "running"))
    records_imported = _records_imported_from_runner_result(
        task,
        fallback=int(run.get("records_imported") or 0),
    )
    updated_run = {
        **run,
        "error_code": task.get("error_code") if run_status == "failed" else None,
        "error_message": task.get("error_message") if run_status == "failed" else None,
        "finished_at": now if run_status in {"cancelled", "failed", "succeeded"} else None,
        "records_imported": records_imported,
        "result_summary": result_summary,
        "status": run_status,
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type=f"scheduled_job_run.{run_status}",
        actor_id=runner_id,
        subject_type="scheduled_job_run",
        subject_id=updated_run["id"],
        payload={
            "ai_executor_task_id": task["id"],
            "records_imported": records_imported,
            "runner_id": runner_id,
            "scheduled_job_id": task.get("scheduled_job_id"),
            "status": run_status,
        },
    )
    _persist_record(
        current_store,
        "save_scheduled_job_run_record",
        updated_run,
        audit_event=audit_event,
    )

    if run_status not in {"cancelled", "failed", "succeeded"}:
        return
    collector_run = _load_collector_run(current_store, updated_run.get("collector_run_id"))
    if collector_run is not None:
        collector_status = "succeeded" if run_status == "succeeded" else "failed"
        updated_collector = {
            **collector_run,
            "error_message": updated_run.get("error_message"),
            "finished_at": now,
            "records_imported": records_imported,
            "status": collector_status,
            "updated_at": now,
        }
        _persist_record(current_store, "save_collector_run_record", updated_collector)
    job = _load_scheduled_job(current_store, task.get("scheduled_job_id"))
    if job is not None:
        updated_job = {
            **job,
            "last_error_message": updated_run.get("error_message"),
            "last_failure_at": now if run_status == "failed" else job.get("last_failure_at"),
            "last_run_at": now,
            "last_success_at": now if run_status == "succeeded" else job.get("last_success_at"),
            "updated_at": now,
        }
        _persist_record(current_store, "save_scheduled_job_record", updated_job)


def create_ai_executor_runner_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    runner_token = str(getattr(payload, "runner_token", None) or secrets.token_urlsafe(32))
    now = datetime.now(UTC).isoformat()
    runner_id = current_store.new_id("ai_executor_runner")
    runner = {
        "created_at": now,
        "created_by": user["id"],
        "endpoint_url": _ensure_non_blank(
            getattr(payload, "endpoint_url", None) or "runner://local",
            "endpoint_url",
        ),
        "executor_types": _normalized_executor_types(getattr(payload, "executor_types", None)),
        "heartbeat_timeout_seconds": int(
            getattr(payload, "heartbeat_timeout_seconds", None) or 120,
        ),
        "id": runner_id,
        "last_heartbeat_at": None,
        "max_concurrent_tasks": int(getattr(payload, "max_concurrent_tasks", None) or 1),
        "metadata": dict(getattr(payload, "metadata", None) or {}),
        "name": _ensure_non_blank(getattr(payload, "name", None), "name"),
        "protocol": _ensure_enum(
            getattr(payload, "protocol", None) or "runner_polling",
            AI_EXECUTOR_RUNNER_PROTOCOLS,
            "protocol",
        ),
        "status": _ensure_enum(
            getattr(payload, "status", None) or "active",
            AI_EXECUTOR_RUNNER_STATUSES,
            "status",
        ),
        "token_hash": _token_hash(runner_token),
        "token_rotated_at": None,
        "token_version": 1,
        "updated_at": now,
        "workspace_roots": _normalized_string_list(
            getattr(payload, "workspace_roots", None),
            "workspace_roots",
        ),
    }
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_runner.created",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={
            "executor_types": runner["executor_types"],
            "protocol": runner["protocol"],
            "status": runner["status"],
        },
    )
    _persist_record(
        current_store,
        "save_ai_executor_runner_record",
        runner,
        audit_event=audit_event,
    )
    return {**_runner_public(runner), "runner_token": runner_token}


def list_ai_executor_runners_response(
    *,
    current_store: Any,
    executor_type: str | None = None,
    keyword: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    protocol: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    started_at: float | None = None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    if status is not None:
        _ensure_enum(status, AI_EXECUTOR_RUNNER_STATUSES, "status")
    if protocol is not None:
        _ensure_enum(protocol, AI_EXECUTOR_RUNNER_PROTOCOLS | {SYSTEM_DEFAULT_AI_EXECUTOR_TYPE}, "protocol")
    if executor_type is not None:
        _ensure_enum(executor_type, AI_EXECUTOR_TYPES, "executor_type")
    sort_order = _ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        _ensure_enum(sort_by, AI_EXECUTOR_RUNNER_SORT_FIELDS, "sort_by")
    resolved_sort_by = sort_by or "updated_at"
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    with_pagination = page is not None or page_size is not None
    repository = getattr(current_store, "repository", None)
    count_page = getattr(repository, "count_ai_executor_runners", None)
    list_page = getattr(repository, "list_ai_executor_runners_page", None)
    filters = {
        "executor_type": executor_type,
        "keyword": keyword,
        "protocol": protocol,
        "status": status,
    }
    sync_ai_executor_task_store(current_store)
    system_runner = system_default_ai_executor_runner()
    system_matches = _runner_matches_filters(system_runner, **filters)
    if with_pagination and callable(count_page) and callable(list_page):
        repository_total = count_page(**filters)
        system_count = 1 if system_matches else 0
        total = repository_total + system_count
        offset = (resolved_page - 1) * resolved_page_size
        items: list[dict[str, Any]] = []
        repository_limit = resolved_page_size
        repository_offset = offset
        if system_count:
            if offset == 0:
                items.append(_runner_public_with_latest_task(current_store, system_runner))
                repository_limit = max(0, resolved_page_size - 1)
                repository_offset = 0
            else:
                repository_offset = max(0, offset - 1)
        if repository_limit > 0 and repository_offset < repository_total:
            items.extend(
                _runner_public_with_latest_task(current_store, runner)
                for runner in list_page(
                    **filters,
                    limit=repository_limit,
                    offset=repository_offset,
                    sort_by=resolved_sort_by,
                    sort_order=sort_order,
                )
            )
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="ai_executor_runners",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    sync_ai_executor_runner_store(
        current_store,
        status=status,
    )
    runners = [
        system_runner,
        *[
            runner
            for runner in _read_collection(current_store, "ai_executor_runners").values()
            if runner.get("id") != SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID
        ],
    ]
    items = [
        _runner_public_with_latest_task(current_store, runner)
        for runner in runners
        if _runner_matches_filters(runner, **filters)
    ]
    items = sort_list_items(
        items,
        allowed_fields=AI_EXECUTOR_RUNNER_SORT_FIELDS,
        default_sort_by=resolved_sort_by,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    if system_matches:
        items = sorted(
            items,
            key=lambda item: 0 if item.get("id") == SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID else 1,
        )
    total = len(items)
    if with_pagination:
        start_index = (resolved_page - 1) * resolved_page_size
        items = items[start_index : start_index + resolved_page_size]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="ai_executor_runners",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    return {"items": items, "total": total}


def list_ai_executor_tasks_response(
    *,
    ai_task_id: str | None,
    current_store: Any,
    page: int | None = None,
    page_size: int | None = None,
    runner_id: str | None,
    scheduled_job_run_id: str | None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    started_at: float | None = None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    if status is not None:
        _ensure_enum(status, AI_EXECUTOR_TASK_STATUSES, "status")
    sort_order = _ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        _ensure_enum(sort_by, AI_EXECUTOR_TASK_SORT_FIELDS, "sort_by")
    resolved_sort_by = sort_by or "updated_at"
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    with_pagination = page is not None or page_size is not None
    repository = getattr(current_store, "repository", None)
    count_page = getattr(repository, "count_ai_executor_tasks", None)
    list_page = getattr(repository, "list_ai_executor_tasks_page", None)
    filters = {
        "ai_task_id": ai_task_id,
        "product_scope_ids": product_scope_filter(user),
        "runner_id": runner_id,
        "scheduled_job_run_id": scheduled_job_run_id,
        "status": status,
    }
    if with_pagination and callable(count_page) and callable(list_page):
        total = count_page(**filters)
        items = [
            _task_public(task)
            for task in list_page(
                **filters,
                limit=resolved_page_size,
                offset=(resolved_page - 1) * resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
            )
        ]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="ai_executor_tasks",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    sync_ai_executor_task_store(
        current_store,
        ai_task_id=ai_task_id,
        product_scope_ids=filters["product_scope_ids"],
        runner_id=runner_id,
        scheduled_job_run_id=scheduled_job_run_id,
        status=status,
    )
    items = [
        _task_public(task)
        for task in _read_collection(current_store, "ai_executor_tasks").values()
        if (ai_task_id is None or task.get("ai_task_id") == ai_task_id)
        and (
            filters["product_scope_ids"] is None
            or _ai_executor_task_visible_to_user(current_store, task=task, user=user)
        )
        and (runner_id is None or task.get("runner_id") == runner_id)
        and (
            scheduled_job_run_id is None
            or task.get("scheduled_job_run_id") == scheduled_job_run_id
        )
        and (status is None or task.get("status") == status)
    ]
    items = sort_list_items(
        items,
        allowed_fields=AI_EXECUTOR_TASK_SORT_FIELDS,
        default_sort_by=resolved_sort_by,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total = len(items)
    if with_pagination:
        start_index = (resolved_page - 1) * resolved_page_size
        items = items[start_index : start_index + resolved_page_size]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="ai_executor_tasks",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    return {"items": items, "total": total}


def _runner_test_diagnostic(
    *,
    detail: str,
    name: str,
    status: str,
    latency_ms: int | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "detail": detail,
        "name": name,
        "status": status,
    }
    if latency_ms is not None:
        item["latency_ms"] = latency_ms
    return item


def test_ai_executor_runner_response(
    *,
    current_store: Any,
    runner_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    started_at = perf_counter()
    sync_ai_executor_runner_store(current_store)
    if _is_system_default_runner_id(runner_id):
        runner = system_default_ai_executor_runner()
    else:
        runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")

    public_runner = _runner_public(runner)
    diagnostics: list[dict[str, Any]] = []
    if _is_system_default_runner(runner):
        diagnostics.extend(
            [
                _runner_test_diagnostic(
                    detail="系统默认执行器由 AI Brain 模型网关托管，无需 Runner Token 或心跳。",
                    name="system_managed",
                    status="succeeded",
                ),
                _runner_test_diagnostic(
                    detail="支持 model_gateway 执行器类型，可用于系统内置 AI 执行。",
                    name="executor_types",
                    status="succeeded",
                ),
            ],
        )
    else:
        runner_status = str(runner.get("status") or "unknown")
        diagnostics.append(
            _runner_test_diagnostic(
                detail=f"Runner 注册状态 {runner_status}。",
                name="runner_registration",
                status="succeeded" if runner_status == "active" else "failed",
            ),
        )
        token_configured = bool(public_runner.get("token_configured"))
        diagnostics.append(
            _runner_test_diagnostic(
                detail=(
                    "Runner Token 已配置。"
                    if token_configured
                    else "Runner Token 未配置，无法安全领取任务。"
                ),
                name="runner_token",
                status="succeeded" if token_configured else "failed",
            ),
        )
        executor_types = [str(item) for item in runner.get("executor_types") or []]
        diagnostics.append(
            _runner_test_diagnostic(
                detail=(
                    "已配置执行器类型：" + "、".join(executor_types)
                    if executor_types
                    else "未配置执行器类型，无法匹配任务。"
                ),
                name="executor_types",
                status="succeeded" if executor_types else "failed",
            ),
        )
        endpoint_url = _runner_endpoint(runner)
        diagnostics.append(
            _runner_test_diagnostic(
                detail=f"执行器端点 {endpoint_url}。",
                name="runner_endpoint",
                status="succeeded" if endpoint_url else "failed",
            ),
        )
        health_status = str(public_runner.get("health_status") or "unknown")
        heartbeat_age = public_runner.get("heartbeat_age_seconds")
        heartbeat_timeout = int(runner.get("heartbeat_timeout_seconds") or 120)
        if health_status == "online":
            heartbeat_detail = f"Runner 心跳正常，{heartbeat_age} 秒前上报。"
            heartbeat_status = "succeeded"
        elif health_status == "never_connected":
            heartbeat_detail = "Runner 尚未上报心跳，请启动本地 Runner 或检查安装包配置。"
            heartbeat_status = "failed"
        elif health_status == "offline":
            heartbeat_detail = (
                f"Runner 心跳超时，最近心跳 {heartbeat_age} 秒前，"
                f"超时时间 {heartbeat_timeout} 秒。"
            )
            heartbeat_status = "failed"
        else:
            heartbeat_detail = f"Runner 当前健康状态为 {health_status}。"
            heartbeat_status = "failed"
        diagnostics.append(
            _runner_test_diagnostic(
                detail=heartbeat_detail,
                name="runner_heartbeat",
                status=heartbeat_status,
            ),
        )

    overall_status = (
        "failed"
        if any(item["status"] == "failed" for item in diagnostics)
        else "succeeded"
    )
    latency_ms = int((perf_counter() - started_at) * 1000)
    result = {
        "checked_at": datetime.now(UTC).isoformat(),
        "diagnostics": diagnostics,
        "health_status": public_runner.get("health_status"),
        "heartbeat_age_seconds": public_runner.get("heartbeat_age_seconds"),
        "latency_ms": latency_ms,
        "runner": public_runner,
        "runner_id": runner_id,
        "status": overall_status,
    }
    record_audit_event(
        current_store,
        event_type="ai_executor_runner.tested",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={
            "health_status": result["health_status"],
            "latency_ms": latency_ms,
            "status": overall_status,
        },
    )
    return result


def patch_ai_executor_runner_response(
    *,
    current_store: Any,
    payload: Any,
    runner_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    if _is_system_default_runner_id(runner_id):
        raise api_error(
            409,
            "AI_EXECUTOR_SYSTEM_RUNNER_LOCKED",
            "系统默认执行器由平台托管，不能修改",
        )
    sync_ai_executor_runner_store(current_store)
    runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        updates["name"] = _ensure_non_blank(updates["name"], "name")
    if "endpoint_url" in updates:
        updates["endpoint_url"] = _ensure_non_blank(updates["endpoint_url"], "endpoint_url")
    if "protocol" in updates:
        updates["protocol"] = _ensure_enum(
            updates["protocol"],
            AI_EXECUTOR_RUNNER_PROTOCOLS,
            "protocol",
        )
    if "status" in updates:
        updates["status"] = _ensure_enum(
            updates["status"],
            AI_EXECUTOR_RUNNER_STATUSES,
            "status",
        )
    if "executor_types" in updates:
        updates["executor_types"] = _normalized_executor_types(updates["executor_types"])
    if "workspace_roots" in updates:
        updates["workspace_roots"] = _normalized_string_list(
            updates["workspace_roots"],
            "workspace_roots",
        )
    if "runner_token" in updates:
        updates["token_hash"] = _token_hash(
            _ensure_non_blank(updates.pop("runner_token"), "runner_token"),
        )
        updates["token_rotated_at"] = datetime.now(UTC).isoformat()
        updates["token_version"] = int(runner.get("token_version") or 1) + 1
    for int_key in ("heartbeat_timeout_seconds", "max_concurrent_tasks"):
        if int_key in updates:
            updates[int_key] = int(updates[int_key])
    if "metadata" in updates:
        updates["metadata"] = dict(updates["metadata"] or {})
    runner = {**runner, **updates, "updated_at": datetime.now(UTC).isoformat()}
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_runner.updated",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={
            "executor_types": runner["executor_types"],
            "protocol": runner["protocol"],
            "status": runner["status"],
        },
    )
    _persist_record(
        current_store,
        "save_ai_executor_runner_record",
        runner,
        audit_event=audit_event,
    )
    return _runner_public(runner)


def rotate_ai_executor_runner_token_response(
    *,
    current_store: Any,
    payload: Any,
    runner_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    if _is_system_default_runner_id(runner_id):
        raise api_error(
            409,
            "AI_EXECUTOR_SYSTEM_RUNNER_LOCKED",
            "系统默认执行器由平台托管，不需要 Runner Token",
        )
    sync_ai_executor_runner_store(current_store)
    runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")
    runner_token = str(getattr(payload, "runner_token", None) or secrets.token_urlsafe(32))
    now = datetime.now(UTC).isoformat()
    runner = {
        **runner,
        "token_hash": _token_hash(_ensure_non_blank(runner_token, "runner_token")),
        "token_rotated_at": now,
        "token_version": int(runner.get("token_version") or 1) + 1,
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_runner.token_rotated",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={"token_version": runner["token_version"]},
    )
    _persist_record(
        current_store,
        "save_ai_executor_runner_record",
        runner,
        audit_event=audit_event,
    )
    return {**_runner_public(runner), "runner_token": runner_token}


def delete_ai_executor_runner_response(
    *,
    current_store: Any,
    runner_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    if _is_system_default_runner_id(runner_id):
        raise api_error(
            409,
            "AI_EXECUTOR_SYSTEM_RUNNER_LOCKED",
            "系统默认执行器由平台托管，不能删除",
        )
    sync_ai_executor_runner_store(current_store)
    sync_ai_executor_task_store(current_store, runner_id=runner_id)
    runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")
    active_tasks = [
        task["id"]
        for task in _read_collection(current_store, "ai_executor_tasks").values()
        if task.get("runner_id") == runner_id
        and task.get("status") not in AI_EXECUTOR_TASK_TERMINAL_STATUSES
    ]
    if active_tasks:
        raise api_error(
            409,
            "AI_EXECUTOR_RUNNER_IN_USE",
            "AI executor runner has active tasks: " + ", ".join(active_tasks),
        )
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_runner.deleted",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={"name": runner["name"], "protocol": runner["protocol"]},
    )
    _delete_runner_record(
        current_store,
        collection_name="ai_executor_runners",
        method_name="delete_ai_executor_runner_record",
        record_id=runner_id,
        audit_event=audit_event,
    )
    return {"deleted": True, "id": runner_id}


def _runner_token_from_request(request: Request) -> str:
    explicit = request.headers.get("X-Runner-Token")
    if explicit:
        return explicit.strip()
    authorization = request.headers.get("Authorization") or ""
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    raise api_error(401, "AI_EXECUTOR_RUNNER_TOKEN_REQUIRED", "Runner token is required")


def _authenticated_runner(
    current_store: Any,
    *,
    request: Request,
    runner_id: str,
) -> dict[str, Any]:
    if _is_system_default_runner_id(runner_id):
        raise api_error(
            409,
            "AI_EXECUTOR_SYSTEM_RUNNER_LOCKED",
            "系统默认执行器由平台托管，不接收 Runner 心跳或任务领取",
        )
    sync_ai_executor_runner_store(current_store)
    runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")
    token = _runner_token_from_request(request)
    if not secrets.compare_digest(_token_hash(token), str(runner.get("token_hash") or "")):
        raise api_error(401, "AI_EXECUTOR_RUNNER_TOKEN_INVALID", "Runner token is invalid")
    if runner.get("status") == "disabled":
        raise api_error(409, "AI_EXECUTOR_RUNNER_DISABLED", "AI executor runner is disabled")
    return runner


def runner_heartbeat_response(
    *,
    current_store: Any,
    metadata: dict[str, Any] | None,
    request: Request,
    runner_id: str,
) -> dict[str, Any]:
    runner = _authenticated_runner(current_store, request=request, runner_id=runner_id)
    now = datetime.now(UTC).isoformat()
    merged_metadata = {**dict(runner.get("metadata") or {}), **dict(metadata or {})}
    runner = {
        **runner,
        "last_heartbeat_at": now,
        "metadata": merged_metadata,
        "status": "active" if runner.get("status") != "disabled" else "disabled",
        "updated_at": now,
    }
    _persist_record(current_store, "save_ai_executor_runner_record", runner)
    return _runner_public(runner)


def _workspace_allowed(runner: dict[str, Any], workspace_root: str) -> bool:
    roots = [str(root) for root in runner.get("workspace_roots") or []]
    if not roots or "*" in roots:
        return True
    return workspace_root in roots


def find_available_runner(
    current_store: Any,
    *,
    executor_type: str,
    runner_id: str | None,
    workspace_root: str,
) -> dict[str, Any]:
    if executor_type == SYSTEM_DEFAULT_AI_EXECUTOR_TYPE:
        if runner_id and not _is_system_default_runner_id(runner_id):
            raise api_error(
                409,
                "AI_EXECUTOR_RUNNER_UNAVAILABLE",
                "System default executor must use the system default runner",
            )
        return system_default_ai_executor_runner()
    if _is_system_default_runner_id(runner_id):
        raise api_error(
            409,
            "AI_EXECUTOR_RUNNER_UNAVAILABLE",
            "System default runner only supports the model_gateway executor type",
        )
    sync_ai_executor_runner_store(current_store)
    candidates = list(_read_collection(current_store, "ai_executor_runners").values())
    if runner_id:
        candidates = [runner for runner in candidates if runner.get("id") == runner_id]
    for runner in candidates:
        if runner.get("status") != "active":
            continue
        if executor_type not in (runner.get("executor_types") or []):
            continue
        if not _workspace_allowed(runner, workspace_root):
            continue
        return runner
    raise api_error(
        409,
        "AI_EXECUTOR_RUNNER_UNAVAILABLE",
        "No active AI executor runner supports the requested executor and workspace",
    )


def create_ai_executor_task(
    current_store: Any,
    *,
    action_id: str | None,
    connection_id: str | None,
    created_by: str,
    executor_type: str,
    input_payload: dict[str, Any],
    instruction: str,
    plugin_invocation_log_id: str | None,
    request_config: dict[str, Any],
    runner_id: str,
    scheduled_job_id: str | None,
    scheduled_job_run_id: str | None,
    timeout_seconds: int,
    workspace_root: str,
    ai_task_id: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    task_id = current_store.new_id("ai_executor_task")
    task = {
        "action_id": action_id,
        "ai_task_id": ai_task_id,
        "claimed_at": None,
        "connection_id": connection_id,
        "created_at": now,
        "created_by": created_by,
        "error_code": None,
        "error_message": None,
        "executor_type": executor_type,
        "finished_at": None,
        "id": task_id,
        "input_payload": input_payload,
        "instruction": instruction,
        "logs": [],
        "plugin_invocation_log_id": plugin_invocation_log_id,
        "request_config": request_config,
        "result_json": {},
        "runner_id": runner_id,
        "scheduled_job_id": scheduled_job_id,
        "scheduled_job_run_id": scheduled_job_run_id,
        "status": "queued",
        "timeout_seconds": timeout_seconds,
        "updated_at": now,
        "workspace_root": workspace_root,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.queued",
        actor_id=created_by,
        subject_type="ai_executor_task",
        subject_id=task_id,
        payload={
            "executor_type": executor_type,
            "runner_id": runner_id,
            "scheduled_job_id": scheduled_job_id,
            "scheduled_job_run_id": scheduled_job_run_id,
            "ai_task_id": ai_task_id,
            "workspace_root": workspace_root,
        },
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    return task


def claim_ai_executor_task_response(
    *,
    current_store: Any,
    executor_type: str | None,
    request: Request,
    runner_id: str,
) -> dict[str, Any]:
    runner = _authenticated_runner(current_store, request=request, runner_id=runner_id)
    requested_executor = executor_type.lower() if isinstance(executor_type, str) else None
    if requested_executor is not None:
        _ensure_enum(requested_executor, AI_EXECUTOR_TYPES, "executor_type")
    sync_ai_executor_task_store(current_store, runner_id=runner_id, status="queued")
    queued = [
        task
        for task in _read_collection(current_store, "ai_executor_tasks").values()
        if task.get("runner_id") == runner_id
        and task.get("status") == "queued"
        and (requested_executor is None or task.get("executor_type") == requested_executor)
    ]
    queued.sort(key=lambda task: (task.get("created_at") or "", task["id"]))
    if not queued:
        return {"task": None}
    task = queued[0]
    if task.get("executor_type") not in (runner.get("executor_types") or []):
        raise api_error(
            409,
            "AI_EXECUTOR_TASK_UNSUPPORTED",
            "Runner does not support task executor",
        )
    now = datetime.now(UTC).isoformat()
    task = {**task, "claimed_at": now, "status": "claimed", "updated_at": now}
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.claimed",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=task["id"],
        payload={"executor_type": task["executor_type"], "runner_id": runner_id},
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    _sync_runner_completion_to_scheduled_run(
        current_store,
        task=task,
        runner_id=runner_id,
    )
    _sync_runner_completion_to_ai_task(
        current_store,
        task=task,
        runner_id=runner_id,
    )
    return {"task": _task_public(task)}


def _sync_ai_executor_task_by_id(current_store: Any, task_id: str) -> dict[str, Any]:
    sync_ai_executor_task_store(current_store)
    task = _read_record(current_store, "ai_executor_tasks", task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    return task


def _sync_visible_ai_executor_task_by_id(
    current_store: Any,
    *,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    task = _sync_ai_executor_task_by_id(current_store, task_id)
    if not _ai_executor_task_visible_to_user(current_store, task=task, user=user):
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    return task


def _log_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _append_task_logs(task: dict[str, Any], logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = [dict(item) for item in task.get("logs") or [] if isinstance(item, dict)]
    next_sequence = int(existing[-1].get("sequence") or len(existing)) + 1 if existing else 1
    normalized: list[dict[str, Any]] = []
    for item in logs:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "level": str(item.get("level") or "info"),
                "message": str(item.get("message") or ""),
                "sequence": int(item.get("sequence") or next_sequence),
                "timestamp": item.get("timestamp") or _log_timestamp(),
            }
        )
        next_sequence += 1
    return [*existing, *normalized]


def list_ai_executor_task_logs_response(
    *,
    current_store: Any,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    task = _sync_visible_ai_executor_task_by_id(current_store, task_id=task_id, user=user)
    return {"logs": list(task.get("logs") or []), "task": _task_public(task)}


def append_ai_executor_task_logs_response(
    *,
    current_store: Any,
    payload: Any,
    request: Request,
    task_id: str,
) -> dict[str, Any]:
    runner_id = _ensure_non_blank(getattr(payload, "runner_id", None), "runner_id")
    _authenticated_runner(current_store, request=request, runner_id=runner_id)
    sync_ai_executor_task_store(current_store, runner_id=runner_id)
    task = _read_record(current_store, "ai_executor_tasks", task_id)
    if task is None or task.get("runner_id") != runner_id:
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    if task.get("status") in AI_EXECUTOR_TASK_TERMINAL_STATUSES:
        raise api_error(409, "AI_EXECUTOR_TASK_TERMINAL", "Terminal task cannot append logs")
    status = str(getattr(payload, "status", None) or task.get("status") or "running")
    if status not in {"claimed", "running"}:
        raise api_error(400, "VALIDATION_ERROR", "Log append status is invalid")
    now = datetime.now(UTC).isoformat()
    task = {
        **task,
        "logs": _append_task_logs(task, list(getattr(payload, "logs", None) or [])),
        "status": status,
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.logs_appended",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=task_id,
        payload={"log_count": len(getattr(payload, "logs", None) or []), "runner_id": runner_id},
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    _sync_runner_completion_to_scheduled_run(current_store, task=task, runner_id=runner_id)
    _sync_runner_completion_to_ai_task(current_store, task=task, runner_id=runner_id)
    return {"logs": list(task.get("logs") or []), "task": _task_public(task)}


def cancel_ai_executor_task_response(
    *,
    current_store: Any,
    payload: Any,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    task = _sync_visible_ai_executor_task_by_id(current_store, task_id=task_id, user=user)
    if task.get("status") in AI_EXECUTOR_TASK_TERMINAL_STATUSES:
        raise api_error(409, "AI_EXECUTOR_TASK_TERMINAL", "Terminal task cannot be cancelled")
    now = datetime.now(UTC).isoformat()
    reason = str(getattr(payload, "reason", None) or "cancelled by user")
    task = {
        **task,
        "error_code": "AI_EXECUTOR_TASK_CANCELLED",
        "error_message": reason,
        "finished_at": now,
        "logs": _append_task_logs(
            task,
            [{"level": "warning", "message": f"Task cancelled: {reason}", "timestamp": now}],
        ),
        "status": "cancelled",
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.cancelled",
        actor_id=user["id"],
        subject_type="ai_executor_task",
        subject_id=task_id,
        payload={"reason": reason, "runner_id": task.get("runner_id")},
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    _sync_runner_completion_to_scheduled_run(
        current_store,
        task=task,
        runner_id=str(task.get("runner_id") or user["id"]),
    )
    _sync_runner_completion_to_ai_task(
        current_store,
        task=task,
        runner_id=str(task.get("runner_id") or user["id"]),
    )
    return {"task": _task_public(task)}


def _datetime_value(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def timeout_ai_executor_tasks_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    now = _datetime_value(getattr(payload, "now", None)) or datetime.now(UTC)
    task_product_scope_ids = product_scope_filter(user)
    sync_ai_executor_task_store(current_store, product_scope_ids=task_product_scope_ids)
    timed_out: list[dict[str, Any]] = []
    for task in list(_read_collection(current_store, "ai_executor_tasks").values()):
        if task_product_scope_ids is not None and not _ai_executor_task_visible_to_user(
            current_store,
            task=task,
            user=user,
        ):
            continue
        if task.get("status") in AI_EXECUTOR_TASK_TERMINAL_STATUSES:
            continue
        reference_at = (
            _datetime_value(task.get("claimed_at"))
            or _datetime_value(task.get("updated_at"))
            or _datetime_value(task.get("created_at"))
            or now
        )
        timeout_seconds = int(task.get("timeout_seconds") or 1800)
        if (now - reference_at).total_seconds() < timeout_seconds:
            continue
        now_iso = now.isoformat()
        updated_task = {
            **task,
            "error_code": "AI_EXECUTOR_TASK_TIMEOUT",
            "error_message": f"AI executor task timed out after {timeout_seconds}s",
            "finished_at": now_iso,
            "logs": _append_task_logs(
                task,
                [
                    {
                        "level": "error",
                        "message": f"Task timed out after {timeout_seconds}s",
                        "timestamp": now_iso,
                    }
                ],
            ),
            "status": "timed_out",
            "updated_at": now_iso,
        }
        audit_event = record_audit_event(
            current_store,
            event_type="ai_executor_task.timed_out",
            actor_id=user["id"],
            subject_type="ai_executor_task",
            subject_id=updated_task["id"],
            payload={
                "runner_id": updated_task.get("runner_id"),
                "timeout_seconds": timeout_seconds,
            },
        )
        _persist_record(
            current_store,
            "save_ai_executor_task_record",
            updated_task,
            audit_event=audit_event,
        )
        _sync_runner_completion_to_scheduled_run(
            current_store,
            task=updated_task,
            runner_id=str(updated_task.get("runner_id") or user["id"]),
        )
        _sync_runner_completion_to_ai_task(
            current_store,
            task=updated_task,
            runner_id=str(updated_task.get("runner_id") or user["id"]),
        )
        timed_out.append(updated_task)
    return {
        "timed_out_task_ids": [task["id"] for task in timed_out],
        "tasks": [_task_public(task) for task in timed_out],
    }


def complete_ai_executor_task_response(
    *,
    current_store: Any,
    payload: Any,
    request: Request,
    task_id: str,
) -> dict[str, Any]:
    runner_id = _ensure_non_blank(getattr(payload, "runner_id", None), "runner_id")
    _authenticated_runner(current_store, request=request, runner_id=runner_id)
    sync_ai_executor_task_store(current_store, runner_id=runner_id)
    task = _read_record(current_store, "ai_executor_tasks", task_id)
    if task is None or task.get("runner_id") != runner_id:
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    status = _ensure_enum(getattr(payload, "status", None), AI_EXECUTOR_TASK_STATUSES, "status")
    if status not in AI_EXECUTOR_TASK_TERMINAL_STATUSES and status != "running":
        raise api_error(400, "VALIDATION_ERROR", "Task completion status is invalid")
    now = datetime.now(UTC).isoformat()
    task = {
        **task,
        "error_code": getattr(payload, "error_code", None),
        "error_message": getattr(payload, "error_message", None),
        "finished_at": now if status in AI_EXECUTOR_TASK_TERMINAL_STATUSES else None,
        "logs": list(getattr(payload, "logs", None) or []),
        "result_json": dict(getattr(payload, "result_json", None) or {}),
        "status": status,
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type=f"ai_executor_task.{status}",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=task_id,
        payload={
            "executor_type": task["executor_type"],
            "runner_id": runner_id,
            "scheduled_job_id": task.get("scheduled_job_id"),
            "scheduled_job_run_id": task.get("scheduled_job_run_id"),
            "status": status,
        },
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    _sync_runner_completion_to_scheduled_run(
        current_store,
        task=task,
        runner_id=runner_id,
    )
    _sync_runner_completion_to_ai_task(
        current_store,
        task=task,
        runner_id=runner_id,
    )
    return {"task": _task_public(task)}
