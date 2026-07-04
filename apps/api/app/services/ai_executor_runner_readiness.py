from __future__ import annotations

from typing import Any

from app.services.ai_executor_runner_constants import SYSTEM_DEFAULT_AI_EXECUTOR_TYPE
from app.services.ai_executor_runner_health import is_system_default_runner
from app.services.ai_executor_runner_packages import runner_executor_commands


def _readiness_control(
    key: str,
    label: str,
    status: str,
    reason: str,
    *,
    required: bool = True,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "reason": reason,
        "required": required,
        "satisfied": status == "satisfied",
        "status": status,
    }


def _metadata_bool(metadata: dict[str, Any], *keys: str) -> bool | None:
    safety = metadata.get("safety") if isinstance(metadata.get("safety"), dict) else {}
    for key in keys:
        for container in (metadata, safety):
            value = container.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in {"true", "1", "yes", "on"}:
                    return True
                if normalized in {"false", "0", "no", "off"}:
                    return False
    return None


def _sandbox_boundary_control(runner: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(runner.get("metadata") or {})
    required_guards = {
        "command_allowlist_enforced": (
            "命令白名单强制",
            _metadata_bool(metadata, "command_allowlist_enforced"),
        ),
        "command_shell_disabled": (
            "禁用 shell 执行",
            _metadata_bool(metadata, "command_shell_disabled", "shell_disabled"),
        ),
        "instruction_passed_via_stdin": (
            "指令 stdin 传入",
            _metadata_bool(metadata, "instruction_passed_via_stdin"),
        ),
        "process_group_isolation": (
            "进程组隔离",
            _metadata_bool(metadata, "process_group_isolation"),
        ),
        "terminate_process_tree_on_timeout": (
            "超时清理进程树",
            _metadata_bool(metadata, "terminate_process_tree_on_timeout"),
        ),
        "workspace_roots_enforced": (
            "工作区白名单强制",
            _metadata_bool(metadata, "workspace_roots_enforced"),
        ),
        "server_high_risk_approval_required": (
            "服务端高风险审批",
            _metadata_bool(metadata, "server_high_risk_approval_required"),
        ),
    }
    missing = [label for label, value in required_guards.values() if value is None]
    disabled = [label for label, value in required_guards.values() if value is False]
    if disabled:
        return _readiness_control(
            "sandbox_permission_boundary",
            "沙箱权限边界",
            "blocked",
            "Runner 上报的安全边界未满足：" + "、".join(disabled),
        )
    if missing:
        return _readiness_control(
            "sandbox_permission_boundary",
            "沙箱权限边界",
            "needs_review",
            "Runner 尚未上报完整沙箱安全元数据，缺少：" + "、".join(missing),
            required=False,
        )
    return _readiness_control(
        "sandbox_permission_boundary",
        "沙箱权限边界",
        "satisfied",
        (
            "已启用命令白名单、禁用 shell、stdin 指令传递、进程组隔离、"
            "超时进程树清理、工作区白名单和高风险审批。"
        ),
    )


def _protocol_adapter_control(runner: dict[str, Any]) -> dict[str, Any]:
    protocol = str(runner.get("protocol") or "").strip()
    if protocol == "runner_polling":
        return _readiness_control(
            "protocol_adapter",
            "协议适配",
            "satisfied",
            "当前 Runner 安装包和任务队列使用 polling 协议完成心跳、认领、日志和结果回写。",
        )
    if protocol in {"runner_websocket", "mcp_http", "mcp_stdio"}:
        protocol_label = {
            "mcp_http": "MCP HTTP",
            "mcp_stdio": "MCP Stdio",
            "runner_websocket": "Runner WebSocket",
        }.get(protocol, protocol)
        return _readiness_control(
            "protocol_adapter",
            "协议适配",
            "blocked",
            (
                f"{protocol_label} 目前仅作为协议预留；当前本地 Runner 安装包和"
                "任务队列闭环请使用 runner_polling。"
            ),
        )
    return _readiness_control(
        "protocol_adapter",
        "协议适配",
        "missing",
        "未配置受支持的 Runner 协议。",
    )


def runner_readiness_summary(
    *,
    public_runner: dict[str, Any],
    queue_summary: dict[str, Any],
    runner: dict[str, Any],
) -> dict[str, Any]:
    if is_system_default_runner(runner):
        return _summary_from_controls(
            [
                _readiness_control(
                    "managed_model_gateway",
                    "系统默认模型托管",
                    "satisfied",
                    "由平台模型网关托管执行，无需本地 Runner 心跳或 Token。",
                ),
                _readiness_control(
                    "completion_callback",
                    "结果回写",
                    "satisfied",
                    "系统默认执行器直接写回运行结果和模型日志。",
                ),
            ],
        )

    health_status = str(public_runner.get("health_status") or "unknown")
    heartbeat_age = public_runner.get("heartbeat_age_seconds")
    heartbeat_timeout = int(runner.get("heartbeat_timeout_seconds") or 0)
    workspace_roots = [str(item) for item in runner.get("workspace_roots") or []]
    max_concurrent_tasks = int(runner.get("max_concurrent_tasks") or 0)
    available_slots = int(queue_summary.get("available_slots") or 0)
    queued_count = int(queue_summary.get("queued") or 0)
    token_configured = bool(public_runner.get("token_configured"))
    executor_types = [
        str(item)
        for item in runner.get("executor_types") or []
        if str(item) != SYSTEM_DEFAULT_AI_EXECUTOR_TYPE
    ]
    command_allowlist = runner_executor_commands(runner)
    missing_commands = [
        executor_type
        for executor_type in executor_types
        if not command_allowlist.get(executor_type)
    ]
    command_status = "satisfied" if executor_types and not missing_commands else "missing"
    if not executor_types:
        command_reason = "未配置本地执行器类型，无法生成命令白名单。"
    elif missing_commands:
        command_reason = "以下执行器缺少命令白名单：" + "、".join(missing_commands)
    else:
        command_reason = (
            "已为执行器配置命令白名单："
            + "、".join(key for key in command_allowlist if key in executor_types)
        )

    heartbeat_status = "satisfied" if health_status == "online" else "missing"
    heartbeat_reason = (
        f"最近心跳 {heartbeat_age} 秒前，未超过 {heartbeat_timeout} 秒超时阈值。"
        if health_status == "online"
        else "Runner 未在线，需启动本地 Runner 或检查网络与 endpoint。"
    )
    if health_status in {"disabled", "offline"}:
        heartbeat_status = "blocked"

    workspace_status = "satisfied"
    workspace_reason = "已配置工作区白名单。"
    if not workspace_roots:
        workspace_status = "missing"
        workspace_reason = "未配置工作区白名单。"
    elif "*" in workspace_roots:
        workspace_status = "warning"
        workspace_reason = "当前允许全部工作区，建议收敛为明确目录。"

    queue_status = "satisfied"
    queue_reason = f"并发上限 {max_concurrent_tasks}，可用槽位 {available_slots}。"
    if max_concurrent_tasks <= 0:
        queue_status = "missing"
        queue_reason = "未配置可用并发槽位。"
    elif queued_count > 0 and available_slots <= 0:
        queue_status = "warning"
        queue_reason = f"当前排队 {queued_count} 个任务且无可用槽位。"

    return _summary_from_controls(
        [
            _readiness_control(
                "runner_registration",
                "Runner 注册状态",
                "satisfied" if runner.get("status") == "active" else "blocked",
                "Runner 已启用。" if runner.get("status") == "active" else "Runner 未启用。",
            ),
            _protocol_adapter_control(runner),
            _readiness_control(
                "heartbeat",
                "心跳在线",
                heartbeat_status,
                heartbeat_reason,
            ),
            _readiness_control(
                "runner_token",
                "Runner Token",
                "satisfied" if token_configured else "missing",
                "Token 已配置，可用于 Runner 心跳、认领和回写。"
                if token_configured
                else "未配置 Runner Token。",
            ),
            _readiness_control(
                "workspace_whitelist",
                "工作区白名单",
                workspace_status,
                workspace_reason,
            ),
            _readiness_control(
                "command_allowlist",
                "命令白名单",
                command_status,
                command_reason,
            ),
            _readiness_control(
                "command_shell_disabled",
                "禁用 shell 执行",
                "satisfied",
                "安装包 Runner 使用参数数组启动命令，并通过 stdin 传递指令。",
            ),
            _sandbox_boundary_control(runner),
            _readiness_control(
                "queue_capacity",
                "队列容量",
                queue_status,
                queue_reason,
            ),
            _readiness_control(
                "timeout_guard",
                "超时重派",
                "satisfied" if heartbeat_timeout > 0 else "missing",
                f"心跳超时阈值 {heartbeat_timeout} 秒，超时扫描可重派或进入死信。"
                if heartbeat_timeout > 0
                else "未配置心跳超时阈值。",
            ),
            _readiness_control(
                "log_streaming",
                "日志流",
                "satisfied",
                "Runner 可追加 stdout/stderr 日志，页面可按任务查看。",
                required=False,
            ),
            _readiness_control(
                "completion_callback",
                "结果回写",
                "satisfied",
                "Runner 完成回写会同步任务、插件日志和定时作业运行。",
            ),
            _readiness_control(
                "approval_gate",
                "高风险操作审批",
                "needs_review",
                (
                    "服务端和 Runner 会拦截 push、发布、删除等高风险指令；"
                    "动作试运行支持审批写回，定时作业需携带有效审批快照后才会入队。"
                ),
                required=False,
            ),
        ],
    )


def _summary_from_controls(controls: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for control in controls:
        status = str(control.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    blocking_statuses = {"blocked", "missing"}
    attention_statuses = {"needs_review", "warning"}
    readiness_status = "ready"
    if any(
        control.get("required") is not False and control.get("status") in blocking_statuses
        for control in controls
    ):
        readiness_status = "blocked"
    elif any(control.get("status") in attention_statuses for control in controls):
        readiness_status = "attention"

    return {
        "attention_count": sum(status_counts.get(status, 0) for status in attention_statuses),
        "blocked_count": status_counts.get("blocked", 0),
        "controls": controls,
        "missing_count": status_counts.get("missing", 0),
        "readiness_status": readiness_status,
        "satisfied_count": status_counts.get("satisfied", 0),
        "status_counts": status_counts,
        "total": len(controls),
    }
