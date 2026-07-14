from __future__ import annotations

import re
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from app.api.deps import api_error, require_permissions
from app.services.ai_executor_runner_constants import DEPLOYMENT_EXECUTOR_TYPE
from app.services.ai_executor_runner_health import (
    is_system_default_runner,
    is_system_default_runner_id,
    runner_endpoint,
    runner_is_online,
    runner_public,
    system_default_ai_executor_runner,
)
from app.services.ai_executor_runner_persistence import (
    _read_collection,
    _read_record,
    sync_ai_executor_runner_store,
    sync_ai_executor_task_store,
)
from app.services.ai_executor_task_creation import create_ai_executor_task
from app.services.operational_records import record_audit_event

DEPLOYMENT_PROBE_MAX_AGE_SECONDS = 600
DEPLOYMENT_PROBE_TASK_KIND = "deployment_connectivity_probe"
_PROBE_TERMINAL_STATUSES = {"cancelled", "dead_letter", "failed", "succeeded", "timed_out"}
_CONFIG_FINGERPRINT_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_PROBE_MAX_AGE_BY_ENVIRONMENT = {
    "dev": 3600,
    "sandbox": 3600,
    "test": 1800,
    "staging": 900,
    "prod": DEPLOYMENT_PROBE_MAX_AGE_SECONDS,
}
_PROBE_MAX_AGE_BY_RISK = {
    "critical": 120,
    "high": 300,
    "low": 1800,
    "medium": 900,
}


def deployment_probe_max_age_seconds(
    *,
    environment: str | None = None,
    risk_level: str | None = None,
    scheme: dict[str, Any] | None = None,
) -> int:
    """Return the stricter configured connectivity-proof lifetime for a deployment."""
    environment_limit = _PROBE_MAX_AGE_BY_ENVIRONMENT.get(
        str(environment or "prod").strip().lower(),
        DEPLOYMENT_PROBE_MAX_AGE_SECONDS,
    )
    risk_limit = _PROBE_MAX_AGE_BY_RISK.get(
        str(risk_level or "medium").strip().lower(),
        _PROBE_MAX_AGE_BY_RISK["medium"],
    )
    policy_limit = min(environment_limit, risk_limit)
    preflight_config = (
        scheme.get("preflight_config") if isinstance(scheme, dict) else None
    )
    configured = (
        preflight_config.get("connectivity_probe_max_age_seconds")
        if isinstance(preflight_config, dict)
        else None
    )
    try:
        configured_limit = int(configured)
    except (TypeError, ValueError):
        configured_limit = 0
    if configured_limit:
        if not 60 <= configured_limit <= 3600:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                "connectivity_probe_max_age_seconds must be between 60 and 3600",
            )
        policy_limit = min(policy_limit, configured_limit)
    return policy_limit


def normalized_deployment_target_metadata(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    targets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        name = str(item.get("name") or "").strip()
        method = str(item.get("method") or "").strip().lower()
        if not code or not name or method not in {"ssh", "docker"} or code in seen:
            continue
        seen.add(code)
        target: dict[str, Any] = {
            "code": code,
            "method": method,
            "name": name,
            "ready": bool(item.get("ready", True)),
        }
        config_fingerprint = str(item.get("config_fingerprint") or "").strip().lower()
        if _CONFIG_FINGERPRINT_PATTERN.fullmatch(config_fingerprint):
            target["config_fingerprint"] = config_fingerprint
        for capability in (
            "health_check_configured",
            "rollback_configured",
            "supports_blue_green",
        ):
            if bool(item.get(capability)):
                target[capability] = True
        targets.append(target)
    return targets


def _parse_utc_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def deployment_target_probe_state(
    target: dict[str, Any],
    *,
    max_age_seconds: int = DEPLOYMENT_PROBE_MAX_AGE_SECONDS,
    now: datetime | None = None,
) -> dict[str, Any]:
    config_fingerprint = str(target.get("config_fingerprint") or "").strip().lower()
    if not _CONFIG_FINGERPRINT_PATTERN.fullmatch(config_fingerprint):
        return {"ready": False, "status": "config_fingerprint_missing"}
    probe = target.get("connectivity_probe")
    if not isinstance(probe, dict):
        return {"ready": False, "status": "not_probed"}
    checked_at = _parse_utc_datetime(probe.get("checked_at"))
    status = str(probe.get("status") or "failed")
    result: dict[str, Any] = {
        "checked_at": probe.get("checked_at"),
        "duration_ms": probe.get("duration_ms"),
        "error_code": probe.get("error_code"),
        "ready": False,
        "status": status,
        "task_id": probe.get("task_id"),
    }
    if str(probe.get("target_config_fingerprint") or "").strip().lower() != config_fingerprint:
        return {**result, "status": "configuration_changed"}
    if status != "succeeded":
        return result
    if checked_at is None:
        return {**result, "status": "invalid"}
    age_seconds = max(0, int(((now or datetime.now(UTC)) - checked_at).total_seconds()))
    result["age_seconds"] = age_seconds
    if age_seconds > max_age_seconds:
        return {**result, "status": "stale"}
    return {**result, "ready": bool(target.get("ready", True))}


def find_available_deployment_runner(
    current_store: Any,
    *,
    deployment_method: str,
    require_connectivity_probe: bool = False,
    runner_id: str,
    target_code: str,
    max_probe_age_seconds: int = DEPLOYMENT_PROBE_MAX_AGE_SECONDS,
) -> dict[str, Any]:
    sync_ai_executor_runner_store(current_store)
    runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if (
        runner is None
        or runner.get("status") != "active"
        or DEPLOYMENT_EXECUTOR_TYPE not in (runner.get("capabilities") or [])
        or runner.get("trust_domain") != "deployment"
        or not runner_is_online(runner)
    ):
        raise api_error(
            409,
            "DEPLOYMENT_RUNNER_UNAVAILABLE",
            "Configured deployment runner must be available and in the deployment trust domain",
        )
    matching_target = deployment_runner_target_metadata(
        runner,
        deployment_method=deployment_method,
        target_code=target_code,
    )
    if matching_target is None:
        raise api_error(
            409,
            "DEPLOYMENT_TARGET_UNAVAILABLE",
            "Configured deployment target is unavailable on the runner",
        )
    probe = deployment_target_probe_state(
        matching_target,
        max_age_seconds=max_probe_age_seconds,
    )
    if require_connectivity_probe and not probe["ready"]:
        raise api_error(
            409,
            "DEPLOYMENT_TARGET_CONNECTIVITY_UNVERIFIED",
            "Configured deployment target requires a successful recent connectivity probe",
            {
                "max_age_seconds": max_probe_age_seconds,
                "probe": probe,
                "target_code": target_code,
            },
        )
    return runner


def deployment_runner_target_metadata(
    runner: dict[str, Any],
    *,
    deployment_method: str,
    target_code: str,
) -> dict[str, Any] | None:
    metadata = runner.get("metadata") if isinstance(runner.get("metadata"), dict) else {}
    targets = metadata.get("deployment_targets")
    matching_target = next(
        (
            dict(target)
            for target in targets or []
            if isinstance(target, dict)
            and target.get("code") == target_code
            and target.get("method") == deployment_method
            and bool(target.get("ready", True))
        ),
        None,
    )
    return matching_target


def preserve_deployment_target_probe_metadata(
    targets: list[dict[str, Any]],
    existing_targets: Any,
) -> list[dict[str, Any]]:
    existing_by_key = {
        (str(item.get("code") or ""), str(item.get("method") or "")): item
        for item in existing_targets or []
        if isinstance(item, dict)
    }
    merged: list[dict[str, Any]] = []
    for target in targets:
        existing = existing_by_key.get(
            (str(target.get("code") or ""), str(target.get("method") or "")),
        )
        probe = (existing or {}).get("connectivity_probe")
        target_fingerprint = str(target.get("config_fingerprint") or "").lower()
        existing_fingerprint = str((existing or {}).get("config_fingerprint") or "").lower()
        merged.append(
            {**target, "connectivity_probe": dict(probe)}
            if (
                isinstance(probe, dict)
                and _CONFIG_FINGERPRINT_PATTERN.fullmatch(target_fingerprint)
                and target_fingerprint == existing_fingerprint
                and str(probe.get("target_config_fingerprint") or "").lower()
                == target_fingerprint
            )
            else dict(target)
        )
    return merged


def runner_with_deployment_probe_result(
    runner: dict[str, Any],
    *,
    task: dict[str, Any],
) -> dict[str, Any] | None:
    if (
        task.get("task_kind") != DEPLOYMENT_PROBE_TASK_KIND
        or task.get("status") not in _PROBE_TERMINAL_STATUSES
    ):
        return None
    input_payload = (
        task.get("input_payload") if isinstance(task.get("input_payload"), dict) else {}
    )
    target_code = str(input_payload.get("target_code") or "").strip()
    deployment_method = str(input_payload.get("deployment_method") or "").strip().lower()
    expected_fingerprint = str(input_payload.get("target_config_fingerprint") or "").strip().lower()
    if not target_code or deployment_method not in {"docker", "ssh"}:
        return None
    metadata = runner.get("metadata") if isinstance(runner.get("metadata"), dict) else {}
    targets = (
        metadata.get("deployment_targets")
        if isinstance(metadata.get("deployment_targets"), list)
        else []
    )
    changed = False
    updated_targets: list[dict[str, Any]] = []
    result_json = task.get("result_json") if isinstance(task.get("result_json"), dict) else {}
    probe = {
        "checked_at": (
            task.get("finished_at") or task.get("updated_at") or datetime.now(UTC).isoformat()
        ),
        "duration_ms": result_json.get("duration_ms"),
        "error_code": task.get("error_code"),
        "status": task.get("status"),
        "task_id": task.get("id"),
        "target_config_fingerprint": expected_fingerprint,
    }
    for target in targets:
        if not isinstance(target, dict):
            continue
        if target.get("code") == target_code and target.get("method") == deployment_method:
            current_fingerprint = str(target.get("config_fingerprint") or "").strip().lower()
            if (
                _CONFIG_FINGERPRINT_PATTERN.fullmatch(expected_fingerprint)
                and current_fingerprint == expected_fingerprint
            ):
                updated_targets.append({**target, "connectivity_probe": probe})
            else:
                updated_targets.append(dict(target))
            changed = True
        else:
            updated_targets.append(dict(target))
    if not changed:
        return None
    return {
        **runner,
        "metadata": {**metadata, "deployment_targets": updated_targets},
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _runner_test_diagnostic(
    *,
    detail: str,
    name: str,
    status: str,
    latency_ms: int | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {"detail": detail, "name": name, "status": status}
    if latency_ms is not None:
        item["latency_ms"] = latency_ms
    return item


def _probe_targets(runner: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = runner.get("metadata") if isinstance(runner.get("metadata"), dict) else {}
    return [
        dict(target)
        for target in metadata.get("deployment_targets") or []
        if isinstance(target, dict)
        and str(target.get("code") or "").strip()
        and str(target.get("method") or "").strip() in {"docker", "ssh"}
        and bool(target.get("ready", True))
    ]


def _existing_probe_task(
    current_store: Any,
    *,
    deployment_method: str,
    runner_id: str,
    target_code: str,
    target_config_fingerprint: str,
) -> dict[str, Any] | None:
    for task in _read_collection(current_store, "ai_executor_tasks").values():
        payload = task.get("input_payload") if isinstance(task.get("input_payload"), dict) else {}
        if (
            task.get("runner_id") == runner_id
            and task.get("task_kind") == DEPLOYMENT_PROBE_TASK_KIND
            and task.get("status") not in _PROBE_TERMINAL_STATUSES
            and payload.get("target_code") == target_code
            and payload.get("deployment_method") == deployment_method
            and payload.get("target_config_fingerprint") == target_config_fingerprint
        ):
            return dict(task)
    return None


def queue_deployment_target_probe_task(
    *,
    current_store: Any,
    runner: dict[str, Any],
    requested_by: str,
    target_code: str,
    deployment_method: str,
) -> dict[str, Any] | None:
    target = next(
        (
            item
            for item in _probe_targets(runner)
            if item.get("code") == target_code and item.get("method") == deployment_method
        ),
        None,
    )
    if target is None:
        return None
    target_config_fingerprint = str(target.get("config_fingerprint") or "").strip().lower()
    if not _CONFIG_FINGERPRINT_PATTERN.fullmatch(target_config_fingerprint):
        return None
    sync_ai_executor_task_store(current_store, runner_id=str(runner["id"]))
    task = _existing_probe_task(
        current_store,
        deployment_method=deployment_method,
        runner_id=str(runner["id"]),
        target_code=target_code,
        target_config_fingerprint=target_config_fingerprint,
    )
    if task is not None:
        return task
    return create_ai_executor_task(
        current_store,
        action_id=None,
        connection_id=None,
        created_by=requested_by,
        executor_type="deployment",
        input_payload={
            "deployment_method": deployment_method,
            "operation": "probe",
            "target_code": target_code,
            "target_config_fingerprint": target_config_fingerprint,
        },
        instruction=(
            "Run the configured non-mutating deployment connectivity probe and report "
            "structured evidence."
        ),
        plugin_invocation_log_id=None,
        request_config={"operation": "probe"},
        runner_id=str(runner["id"]),
        scheduled_job_id=None,
        scheduled_job_run_id=None,
        task_kind=DEPLOYMENT_PROBE_TASK_KIND,
        timeout_seconds=60,
        workspace_root="",
    )


def queue_deployment_target_probe_tasks(
    *,
    current_store: Any,
    runner: dict[str, Any],
    requested_by: str,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for target in _probe_targets(runner):
        task = queue_deployment_target_probe_task(
            current_store=current_store,
            deployment_method=str(target["method"]),
            requested_by=requested_by,
            runner=runner,
            target_code=str(target["code"]),
        )
        if task is not None:
            tasks.append(task)
    return tasks


def test_ai_executor_runner_response(
    *,
    current_store: Any,
    runner_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_permissions(user, {"system.plugins.manage"})
    started_at = perf_counter()
    sync_ai_executor_runner_store(current_store)
    if is_system_default_runner_id(runner_id):
        runner = system_default_ai_executor_runner()
    else:
        runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")

    public_runner = runner_public(runner)
    diagnostics: list[dict[str, Any]] = []
    probe_tasks: list[dict[str, Any]] = []
    if is_system_default_runner(runner):
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
        endpoint_url = runner_endpoint(runner)
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
                f"Runner 心跳超时，最近心跳 {heartbeat_age} 秒前，超时时间 {heartbeat_timeout} 秒。"
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
        if "deployment" in (runner.get("capabilities") or []):
            targets = _probe_targets(runner)
            if runner.get("trust_domain") != "deployment":
                diagnostics.append(
                    _runner_test_diagnostic(
                        detail="部署能力必须使用部署信任域 Runner，当前不能下发真实探测。",
                        name="deployment_trust_domain",
                        status="failed",
                    ),
                )
            elif not runner_is_online(runner):
                diagnostics.append(
                    _runner_test_diagnostic(
                        detail="Runner 未在线，待心跳恢复后再执行真实连通性探测。",
                        name="deployment_connectivity",
                        status="failed",
                    ),
                )
            elif not targets:
                diagnostics.append(
                    _runner_test_diagnostic(
                        detail="未上报可探测的 SSH 或 Docker 部署目标。",
                        name="deployment_connectivity",
                        status="failed",
                    ),
                )
            else:
                probe_tasks = queue_deployment_target_probe_tasks(
                    current_store=current_store,
                    requested_by=user["id"],
                    runner=runner,
                )
                diagnostics.append(
                    _runner_test_diagnostic(
                        detail=(
                            f"已下发 {len(probe_tasks)} 个真实部署目标连通性探测，"
                            "等待 Runner 回写结果。"
                        ),
                        name="deployment_connectivity",
                        status="queued",
                    ),
                )

    overall_status = (
        "failed" if any(item["status"] == "failed" for item in diagnostics) else "succeeded"
    )
    latency_ms = int((perf_counter() - started_at) * 1000)
    result = {
        "checked_at": datetime.now(UTC).isoformat(),
        "diagnostics": diagnostics,
        "health_status": public_runner.get("health_status"),
        "heartbeat_age_seconds": public_runner.get("heartbeat_age_seconds"),
        "latency_ms": latency_ms,
        "probe_tasks": [
            {
                "id": task["id"],
                "status": task["status"],
                "target_code": task["input_payload"]["target_code"],
            }
            for task in probe_tasks
        ],
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
