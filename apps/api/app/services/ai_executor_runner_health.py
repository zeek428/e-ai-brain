from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.services.ai_executor_runner_constants import (
    SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
    SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
)


def is_system_default_runner_id(runner_id: str | None) -> bool:
    return runner_id == SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID


def is_system_default_runner(runner: dict[str, Any]) -> bool:
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
        "capabilities": [],
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


def runner_public(runner: dict[str, Any]) -> dict[str, Any]:
    public = dict(runner)
    public.pop("token_hash", None)
    public["token_configured"] = (
        False if is_system_default_runner(runner) else bool(runner.get("token_hash"))
    )
    heartbeat_age = heartbeat_age_seconds(runner.get("last_heartbeat_at"))
    public["heartbeat_age_seconds"] = heartbeat_age
    health_status = runner_health_status(runner, heartbeat_age)
    public["health_status"] = health_status
    public["health_alert"] = runner_health_alert(runner, health_status, heartbeat_age)
    public["setup_command"] = runner_setup_command(runner)
    public["token_rotated_at"] = runner.get("token_rotated_at")
    public["token_version"] = int(runner.get("token_version") or 1)
    return public


def heartbeat_age_seconds(value: Any) -> int | None:
    if not value:
        return None
    try:
        heartbeat_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if heartbeat_at.tzinfo is None:
        heartbeat_at = heartbeat_at.replace(tzinfo=UTC)
    return max(0, int((datetime.now(UTC) - heartbeat_at.astimezone(UTC)).total_seconds()))


def runner_health_status(runner: dict[str, Any], heartbeat_age: int | None) -> str:
    if is_system_default_runner(runner):
        return "managed"
    if runner.get("status") == "disabled":
        return "disabled"
    if runner.get("status") == "offline":
        return "offline"
    if heartbeat_age is None:
        return "never_connected"
    timeout_seconds = int(runner.get("heartbeat_timeout_seconds") or 120)
    return "online" if heartbeat_age <= timeout_seconds else "offline"


def runner_is_online(runner: dict[str, Any]) -> bool:
    heartbeat_age = heartbeat_age_seconds(runner.get("last_heartbeat_at"))
    return runner_health_status(runner, heartbeat_age) == "online"


def runner_health_alert(
    runner: dict[str, Any],
    health_status: str,
    heartbeat_age: int | None,
) -> dict[str, Any] | None:
    if health_status in {"managed", "online"}:
        return None

    if health_status == "disabled":
        return {
            "action_label": "启用 Runner",
            "code": "runner_disabled",
            "message": "Runner 已停用，不会接收新任务。",
            "severity": "info",
        }

    if health_status == "never_connected":
        return {
            "action_label": "启动 Runner",
            "code": "runner_never_connected",
            "heartbeat_age_seconds": None,
            "heartbeat_timeout_seconds": int(runner.get("heartbeat_timeout_seconds") or 120),
            "message": "Runner 尚未上报心跳，请启动本地 Runner 或检查安装包配置。",
            "severity": "warning",
        }

    if health_status == "offline":
        timeout_seconds = int(runner.get("heartbeat_timeout_seconds") or 120)
        if heartbeat_age is None:
            return {
                "action_label": "检查 Runner",
                "code": "runner_offline",
                "heartbeat_age_seconds": None,
                "heartbeat_timeout_seconds": timeout_seconds,
                "message": "Runner 当前离线，请检查进程、网络连接和 endpoint 配置。",
                "severity": "warning",
            }
        return {
            "action_label": "检查 Runner",
            "code": "runner_heartbeat_timeout",
            "heartbeat_age_seconds": heartbeat_age,
            "heartbeat_timeout_seconds": timeout_seconds,
            "message": (
                f"Runner 心跳超时，最近心跳 {heartbeat_age} 秒前，"
                f"超时时间 {timeout_seconds} 秒。"
            ),
            "severity": "critical",
        }

    return {
        "action_label": "查看诊断",
        "code": f"runner_{health_status}",
        "heartbeat_age_seconds": heartbeat_age,
        "heartbeat_timeout_seconds": int(runner.get("heartbeat_timeout_seconds") or 120),
        "message": f"Runner 当前健康状态为 {health_status}，请查看诊断结果。",
        "severity": "warning",
    }


def runner_setup_command(runner: dict[str, Any]) -> str:
    if is_system_default_runner(runner):
        return "使用系统默认 AI 大模型执行，无需启动本地 Runner"
    executor_types = ",".join(str(item) for item in runner.get("executor_types") or ["codex"])
    workspace_roots = ",".join(str(item) for item in runner.get("workspace_roots") or ["*"])
    return (
        "ai-brain-runner start "
        f"--runner-id {runner.get('id')} "
        "--token <runner_token> "
        f"--endpoint {runner_endpoint(runner)} "
        f"--executors {executor_types} "
        f"--workspace-roots {workspace_roots}"
    )


def runner_endpoint(runner: dict[str, Any]) -> str:
    return str(runner.get("endpoint_url") or "runner://local")
