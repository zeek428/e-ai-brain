from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Request

from app.api.deps import api_error
from app.core.config import Settings
from app.services.ai_executor_runner_constants import (
    AI_EXECUTOR_TASK_RETRYABLE_STATUSES,
    AI_EXECUTOR_TASK_STATUSES,
    AI_EXECUTOR_TASK_TERMINAL_STATUSES,
)
from app.services.ai_executor_task_reliability import (
    DEFAULT_LEASE_TIMEOUT_SECONDS,
    DEFAULT_MAX_RECLAIM_COUNT,
    LEASE_ACTIVE_STATUSES,
    lease_timeout_seconds,
    max_reclaim_count,
)
from app.services.knowledge_index_health import knowledge_index_health_response
from app.services.knowledge_quality import knowledge_quality_summary
from app.services.platform_status import health_payload
from app.services.product_config_context import (
    list_product_git_repository_records,
    list_product_module_records,
    list_product_records,
    list_product_version_records,
    list_related_system_records,
)
from app.services.rbac_matrix import build_rbac_policy_matrix
from app.services.system_settings import system_settings_response


HEALTH_STATUS_RANK = {
    "ok": 0,
    "configured": 0,
    "managed": 0,
    "enabled": 0,
    "info": 1,
    "disabled": 1,
    "not_configured": 1,
    "warning": 1,
    "degraded": 2,
    "error": 3,
    "failed": 3,
}
ALERT_SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3}

SENSITIVE_ERROR_PATTERNS = (
    re.compile(r"(?i)(key=)[^&\s]+"),
    re.compile(r"(?i)(token=)[^&\s]+"),
    re.compile(r"(?i)(secret=)[^&\s]+"),
    re.compile(r"(?i)(password=)[^&\s]+"),
    re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s]+"),
)


def _runtime_repository(current_store: Any) -> Any | None:
    return getattr(current_store, "repository", None)


def _items_from_store(current_store: Any, repository_method: str, memory_attr: str) -> list[dict[str, Any]]:
    repository = _runtime_repository(current_store)
    list_items = getattr(repository, repository_method, None)
    if callable(list_items):
        try:
            items = list_items()
        except TypeError:
            items = []
    else:
        items = getattr(current_store, memory_attr, [])
    if isinstance(items, dict):
        iterable = items.values()
    else:
        iterable = items or []
    return [dict(item) for item in iterable if isinstance(item, dict)]


def _items_from_repository_payload(
    current_store: Any,
    *,
    memory_attr: str,
    payload_key: str,
    repository_method: str,
) -> list[dict[str, Any]]:
    repository = _runtime_repository(current_store)
    load_items = getattr(repository, repository_method, None)
    if callable(load_items):
        try:
            payload = load_items()
        except Exception:  # pragma: no cover - defensive around partial repositories
            payload = {}
        items = payload.get(payload_key, {}) if isinstance(payload, dict) else {}
    else:
        items = getattr(current_store, memory_attr, {})
    if isinstance(items, dict):
        iterable = items.values()
    else:
        iterable = items or []
    return [dict(item) for item in iterable if isinstance(item, dict)]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _status_rank(status: str) -> int:
    return HEALTH_STATUS_RANK.get(status, 2)


def _count_by_status(items: list[dict[str, Any]], *, field: str = "status") -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get(field) or "unknown").lower()
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _percent(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return round((numerator / denominator) * 100)


def _overall_status(checks: list[dict[str, Any]]) -> str:
    if any(_status_rank(str(check.get("status"))) >= 3 for check in checks):
        return "error"
    if any(_status_rank(str(check.get("status"))) == 2 for check in checks):
        return "degraded"
    if any(_status_rank(str(check.get("status"))) == 1 for check in checks):
        return "warning"
    return "ok"


def _check(
    *,
    action_href: str | None = None,
    category: str,
    component: str,
    description: str,
    fix_suggestion: str,
    key: str,
    last_error: str | None = None,
    metrics: dict[str, Any] | None = None,
    status: str,
    title: str,
) -> dict[str, Any]:
    return {
        "action_href": action_href,
        "category": category,
        "component": component,
        "description": description,
        "fix_suggestion": fix_suggestion,
        "key": key,
        "last_error": last_error,
        "metrics": metrics or {},
        "status": status,
        "title": title,
    }


def _latest_error(items: list[dict[str, Any]], *fields: str) -> str | None:
    for item in items:
        for field in fields:
            value = item.get(field)
            if value:
                return _redact_error_summary(str(value))
    return None


def _redact_error_summary(value: str) -> str:
    redacted = value.strip()
    for pattern in SENSITIVE_ERROR_PATTERNS:
        redacted = pattern.sub(r"\1***", redacted)
    return redacted[:500]


def _pgvector_check(current_store: Any, settings: Settings) -> dict[str, Any]:
    if settings.persistence_mode == "memory":
        return _check(
            category="基础设施",
            component="pgvector",
            description="测试环境使用内存模式，跳过 PostgreSQL 扩展检查。",
            fix_suggestion="生产环境应使用 PostgreSQL 并启用 vector 与 pgcrypto 扩展。",
            key="pgvector",
            status="info",
            title="PostgreSQL 向量扩展",
        )
    repository = _runtime_repository(current_store)
    connect = getattr(repository, "_connect", None)
    if not callable(connect):
        return _check(
            category="基础设施",
            component="pgvector",
            description="当前运行时没有暴露数据库连接，无法确认 pgvector 扩展。",
            fix_suggestion="检查 PostgreSQL runtime repository 初始化状态。",
            key="pgvector",
            status="warning",
            title="PostgreSQL 向量扩展",
        )
    try:
        with connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "select extname from pg_extension where extname in ('vector', 'pgcrypto')",
                )
                extensions = {str(row[0]) for row in cursor.fetchall()}
    except Exception as exc:  # pragma: no cover - exercised by integration environments
        return _check(
            category="基础设施",
            component="pgvector",
            description="无法查询 PostgreSQL 扩展状态。",
            fix_suggestion="确认数据库连接、迁移权限和扩展安装权限。",
            key="pgvector",
            last_error=exc.__class__.__name__,
            status="error",
            title="PostgreSQL 向量扩展",
        )
    missing = sorted({"vector", "pgcrypto"} - extensions)
    return _check(
        category="基础设施",
        component="pgvector",
        description="用于知识中心向量检索和安全随机值生成的 PostgreSQL 扩展。",
        fix_suggestion="在数据库执行 create extension if not exists vector; create extension if not exists pgcrypto;",
        key="pgvector",
        metrics={"enabled_extensions": sorted(extensions), "missing_extensions": missing},
        status="ok" if not missing else "error",
        title="PostgreSQL 向量扩展",
    )


def _smtp_check(current_store: Any) -> dict[str, Any]:
    settings_payload = system_settings_response(current_store)
    delivery = settings_payload.get("email_delivery") or {}
    enabled = bool(delivery.get("enabled"))
    configured = bool(settings_payload.get("email_delivery_configured"))
    if configured:
        status = "configured"
        description = "邮件发送配置完整，可用于系统通知和测试发送。"
        fix = "建议定期使用系统设置中的发送测试邮件验证 SMTP 授权码仍有效。"
    elif enabled:
        status = "error"
        description = "邮件发送已启用，但 SMTP 配置不完整。"
        fix = "到系统设置补齐发件邮箱、SMTP Host、端口、加密方式、用户名和密码/授权码。"
    else:
        status = "not_configured"
        description = "邮件发送未启用，系统通知邮件不会发出。"
        fix = "如需要邮件通知，请到系统设置启用发信并完成 SMTP 配置。"
    return _check(
        action_href="/system/settings",
        category="外部通知",
        component="smtp",
        description=description,
        fix_suggestion=fix,
        key="smtp",
        metrics={
            "enabled": enabled,
            "smtp_host": delivery.get("smtp_host"),
            "smtp_port": delivery.get("smtp_port"),
            "smtp_tls": delivery.get("smtp_tls"),
            "test_recipient_configured": bool(settings_payload.get("test_recipient_email_configured")),
        },
        status=status,
        title="SMTP 邮件发送",
    )


def _dingtalk_login_check(settings: Settings) -> dict[str, Any]:
    if not settings.dingtalk_login_enabled:
        return _check(
            action_href="/system/settings",
            category="身份集成",
            component="dingtalk_login",
            description="钉钉登录未启用，用户只能使用本地账号密码登录。",
            fix_suggestion="如需企业 SSO，请配置 DINGTALK_LOGIN_ENABLED、Client ID、Client Secret 和回调地址。",
            key="dingtalk_login",
            status="disabled",
            title="钉钉登录",
        )
    missing = [
        label
        for label, value in (
            ("Client ID", settings.dingtalk_client_id),
            ("Client Secret", settings.dingtalk_client_secret_value),
            ("Redirect URI", settings.dingtalk_redirect_uri),
        )
        if not value
    ]
    return _check(
        action_href="/account/profile",
        category="身份集成",
        component="dingtalk_login",
        description="钉钉登录用于企业用户免密码登录和账号绑定。",
        fix_suggestion="补齐缺失配置，并确认钉钉开放平台回调地址与公网域名一致。",
        key="dingtalk_login",
        metrics={
            "allowed_corp_count": len(settings.dingtalk_allowed_corp_id_set),
            "auto_provision": settings.dingtalk_auto_provision,
            "corp_name_count": len(settings.dingtalk_corp_name_map),
            "pending_approval": settings.dingtalk_pending_approval,
        },
        status="configured" if not missing else "error",
        last_error=f"缺失配置：{', '.join(missing)}" if missing else None,
        title="钉钉登录",
    )


def _dingtalk_mcp_check(current_store: Any) -> dict[str, Any]:
    plugins = _items_from_store(current_store, "list_plugins", "integration_plugins")
    connections = _items_from_store(
        current_store,
        "list_plugin_connections",
        "plugin_connections",
    )
    dingtalk_plugins = [
        item
        for item in plugins
        if "dingtalk" in str(item.get("code") or "").lower()
        or "钉钉" in str(item.get("name") or "")
    ]
    dingtalk_connections = [
        item
        for item in connections
        if "dingtalk" in str(item.get("plugin_code") or item.get("plugin_id") or "").lower()
        or "钉钉" in str(item.get("plugin_name") or item.get("name") or "")
    ]
    failed_connections = [
        item
        for item in dingtalk_connections
        if str(item.get("status") or "").lower() not in {"active", "enabled"}
        or str((item.get("last_test_summary") or {}).get("status") or "").lower() in {"failed", "error"}
    ]
    if dingtalk_plugins and dingtalk_connections and not failed_connections:
        status = "configured"
        description = "已安装钉钉 MCP 插件并存在可用连接。"
        fix = "建议定期执行连接测试，并关注授权 key 的有效期。"
    elif dingtalk_plugins:
        status = "warning"
        description = "已安装钉钉 MCP 插件，但缺少可用连接或最近测试失败。"
        fix = "到插件管理补齐钉钉知识库连接，使用连接测试确认授权可用。"
    else:
        status = "not_configured"
        description = "未检测到钉钉 MCP 插件，知识库等钉钉能力不可用。"
        fix = "到插件管理从插件市场安装钉钉知识库或相关 MCP 插件。"
    return _check(
        action_href="/tasks/plugins",
        category="插件集成",
        component="dingtalk_mcp",
        description=description,
        fix_suggestion=fix,
        key="dingtalk_mcp",
        last_error=_latest_error(failed_connections, "error_message"),
        metrics={
            "connection_count": len(dingtalk_connections),
            "failed_connection_count": len(failed_connections),
            "plugin_count": len(dingtalk_plugins),
        },
        status=status,
        title="钉钉 MCP 连接",
    )


def _object_storage_check(settings: Settings) -> dict[str, Any]:
    provider = settings.object_storage_provider
    if provider == "minio":
        missing = [
            label
            for label, value in (
                ("endpoint", settings.object_storage_endpoint),
                ("access_key", settings.object_storage_access_key),
                ("secret_key", settings.object_storage_secret_key),
                ("bucket", settings.object_storage_bucket),
            )
            if not value
        ]
        return _check(
            action_href="/assets/knowledge",
            category="对象存储",
            component="object_storage",
            description="知识文件和 Bug 图片证据使用 MinIO/S3-compatible 对象存储。",
            fix_suggestion="补齐 OBJECT_STORAGE_ENDPOINT、ACCESS_KEY、SECRET_KEY、BUCKET，并确认 bucket 私有。",
            key="object_storage",
            last_error=f"缺失配置：{', '.join(missing)}" if missing else None,
            metrics={"bucket": settings.object_storage_bucket, "provider": provider},
            status="configured" if not missing else "error",
            title="MinIO / S3 对象存储",
        )
    return _check(
        action_href="/assets/knowledge",
        category="对象存储",
        component="object_storage",
        description="当前使用本地文件存储，仅适合开发或测试。",
        fix_suggestion="生产环境建议切换 OBJECT_STORAGE_PROVIDER=minio，并配置私有 bucket。",
        key="object_storage",
        metrics={"local_dir": settings.object_storage_local_dir, "provider": provider},
        status="info" if settings.is_local_or_test_env else "warning",
        title="MinIO / S3 对象存储",
    )


def _model_gateway_check(current_store: Any, settings: Settings, platform_health: dict[str, str]) -> dict[str, Any]:
    logs = _items_from_store(current_store, "list_model_gateway_logs", "model_gateway_logs")
    failed_logs = [item for item in logs if item.get("status") == "failed"]
    status = platform_health.get("model_gateway") or "not_configured"
    return _check(
        action_href="/system/model-gateway",
        category="模型能力",
        component="model_gateway",
        description="模型网关统一承载聊天、embedding、RAG 和 AI 任务模型调用。",
        fix_suggestion="到模型网关配置默认模型、API Key、embedding 模型，并执行连接测试。",
        key="model_gateway",
        last_error=_latest_error(failed_logs, "error"),
        metrics={
            "failed_log_count": len(failed_logs),
            "recent_log_count": len(logs),
            "embedding_gateway": platform_health.get("embedding_gateway"),
        },
        status=status,
        title="模型网关",
    )


def _knowledge_quality_check(
    current_store: Any,
    *,
    request: Request,
    user: dict[str, Any],
) -> dict[str, Any]:
    try:
        health_envelope = knowledge_index_health_response(
            current_store=current_store,
            doc_type=None,
            folder_id=None,
            index_status=None,
            issue_limit=5,
            knowledge_space_id=None,
            keyword=None,
            permission_role=None,
            request=request,
            user=user,
        )
        health = health_envelope.get("data", health_envelope)
    except Exception as exc:  # pragma: no cover - defensive for partially migrated runtimes
        return _check(
            action_href="/assets/knowledge",
            category="知识质量",
            component="knowledge_quality",
            description="无法读取知识索引健康状态。",
            fix_suggestion="检查知识库表结构、权限范围和索引迁移是否完成。",
            key="knowledge_quality",
            last_error=exc.__class__.__name__,
            status="warning",
            title="知识中心质量",
        )
    summary = health.get("summary") or {}
    total_documents = int(summary.get("totalDocuments") or summary.get("total_documents") or 0)
    searchable_documents = int(
        summary.get("searchableDocuments") or summary.get("searchable_documents") or 0,
    )
    failed_documents = int(
        summary.get("indexFailedDocuments") or summary.get("index_failed_documents") or 0,
    )
    issues = health.get("issues") or []
    if failed_documents > 0:
        status = "degraded"
    elif total_documents == 0:
        status = "not_configured"
    else:
        status = "configured"
    return _check(
        action_href="/assets/knowledge",
        category="知识质量",
        component="knowledge_quality",
        description="展示知识文档、分块、向量索引和 Hybrid Search 可用性。",
        fix_suggestion="关注索引失败和仅关键词可检索文档，补建 embedding 并使用 RAG 反馈评估引用准确性。",
        key="knowledge_quality",
        last_error=_latest_error(issues, "description"),
        metrics={
            "issue_count": len(issues),
            "searchable_documents": searchable_documents,
            "total_documents": total_documents,
            "index_failed_documents": failed_documents,
        },
        status=status,
        title="知识中心质量",
    )


def _ai_executor_check(current_store: Any) -> dict[str, Any]:
    runners = _items_from_store(current_store, "list_ai_executor_runners", "ai_executor_runners")
    tasks = _items_from_store(current_store, "list_ai_executor_tasks", "ai_executor_tasks")
    failing_tasks = [
        item
        for item in tasks
        if str(item.get("status") or "").lower() in {"failed", "dead_letter", "timed_out"}
    ]
    queued_tasks = [item for item in tasks if str(item.get("status") or "").lower() == "queued"]
    offline_runners = [
        item
        for item in runners
        if str(item.get("status") or "").lower() in {"offline", "disabled"}
        or str(item.get("health_status") or "").lower() in {"offline", "never_connected"}
    ]
    status = "configured"
    if failing_tasks or offline_runners:
        status = "degraded"
    elif not runners:
        status = "not_configured"
    return _check(
        action_href="/tasks/plugins",
        category="AI 执行运维",
        component="ai_executor",
        description="本地 Runner、队列和高风险执行审批承载代码变更与插件动作执行。",
        fix_suggestion="关注离线 Runner、失败队列、超时任务，必要时执行重试、取消或超时扫描。",
        key="ai_executor",
        last_error=_latest_error(failing_tasks, "error_message", "error_code"),
        metrics={
            "failed_task_count": len(failing_tasks),
            "offline_runner_count": len(offline_runners),
            "queued_task_count": len(queued_tasks),
            "runner_count": len(runners),
        },
        status=status,
        title="AI 执行器与队列",
    )


def _scheduled_jobs_check(current_store: Any) -> dict[str, Any]:
    runs = _items_from_store(current_store, "list_scheduled_job_runs", "scheduled_job_runs")
    failed_runs = [item for item in runs if str(item.get("status") or "").lower() == "failed"]
    return _check(
        action_href="/tasks/scheduled-jobs",
        category="作业观测",
        component="scheduled_jobs",
        description="定时作业负责外部数据采集、插件编排和治理自动化。",
        fix_suggestion="对失败作业查看 trace 节点、重跑失败节点，并检查插件连接和模型网关状态。",
        key="scheduled_jobs",
        last_error=_latest_error(failed_runs, "error_message", "failure_reason"),
        metrics={"failed_run_count": len(failed_runs), "recent_run_count": len(runs)},
        status="degraded" if failed_runs else "configured",
        title="定时作业运行",
    )


def _product_onboarding_check(current_store: Any) -> dict[str, Any]:
    products = list_product_records(current_store, active_only=False)
    active_products = [item for item in products if item.get("status") != "archived"]
    return _check(
        action_href="/assets/products",
        category="产品接入",
        component="product_onboarding",
        description="产品、版本、模块、仓库、知识空间和插件连接是平台数据归属的基础。",
        fix_suggestion="建议为每个活跃产品补齐版本、模块、代码仓库、知识空间和插件连接，后续可通过产品接入向导集中维护。",
        key="product_onboarding",
        metrics={
            "active_product_count": len(active_products),
            "total_product_count": len(products),
        },
        status="configured" if active_products else "not_configured",
        title="产品初始化",
    )


def _knowledge_documents_for_health(current_store: Any) -> list[dict[str, Any]]:
    repository = _runtime_repository(current_store)
    list_documents = getattr(repository, "list_knowledge_documents", None)
    if callable(list_documents):
        try:
            return [
                dict(document)
                for document in list_documents(
                    user_roles=["admin"],
                    user_id=None,
                    global_knowledge_access=True,
                    knowledge_space_scope_ids=["*"],
                )
                if isinstance(document, dict)
            ]
        except Exception:  # pragma: no cover - defensive around partially migrated stores
            return []
    documents = getattr(current_store, "knowledge_documents", {})
    if isinstance(documents, dict):
        iterable = documents.values()
    else:
        iterable = documents or []
    return [dict(document) for document in iterable if isinstance(document, dict)]


def _knowledge_spaces_for_health(current_store: Any) -> list[dict[str, Any]]:
    repository = _runtime_repository(current_store)
    list_spaces = getattr(repository, "list_knowledge_spaces", None)
    if callable(list_spaces):
        try:
            return [
                dict(space)
                for space in list_spaces(active_only=False)
                if isinstance(space, dict)
            ]
        except Exception:  # pragma: no cover - defensive around partially migrated stores
            return []
    spaces = getattr(current_store, "knowledge_spaces", {})
    if isinstance(spaces, dict):
        iterable = spaces.values()
    else:
        iterable = spaces or []
    return [dict(space) for space in iterable if isinstance(space, dict)]


def _connection_product_ids(connection: dict[str, Any]) -> set[str]:
    request_config = connection.get("request_config")
    if not isinstance(request_config, dict):
        return set()
    candidates: list[Any] = [
        request_config.get("product_id"),
        (request_config.get("query") or {}).get("product_id")
        if isinstance(request_config.get("query"), dict)
        else None,
    ]
    source_filters = request_config.get("source_filters")
    if isinstance(source_filters, dict):
        for value in source_filters.values():
            if isinstance(value, dict):
                candidates.append(value.get("product_id"))
    product_ids: set[str] = set()
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            product_ids.add(candidate.strip())
        elif isinstance(candidate, list):
            product_ids.update(str(item).strip() for item in candidate if str(item).strip())
    return product_ids


def _plugin_connection_test_status(connection: dict[str, Any]) -> str:
    last_test = connection.get("last_test_summary")
    if not isinstance(last_test, dict):
        return "unknown"
    status = str(last_test.get("status") or "").strip().lower()
    if status in {"ok", "pass", "passed", "success", "succeeded", "healthy"}:
        return "passed"
    if status in {"blocked", "error", "failed", "fail", "timeout", "timed_out"}:
        return "failed"
    return status or "unknown"


def _plugin_connection_checked_at(connection: dict[str, Any]) -> str | None:
    last_test = connection.get("last_test_summary")
    if not isinstance(last_test, dict):
        return None
    for field in ("checked_at", "tested_at", "finished_at", "updated_at", "created_at"):
        value = last_test.get(field)
        if value:
            return str(value)
    return None


def _product_plugin_health(current_store: Any) -> dict[str, dict[str, Any]]:
    connections = _items_from_store(current_store, "list_plugin_connections", "plugin_connections")
    health_by_product: dict[str, dict[str, Any]] = {}
    for connection in connections:
        connection_status = str(connection.get("status") or "").strip().lower()
        enabled = connection_status in {"active", "enabled"}
        test_status = _plugin_connection_test_status(connection)
        checked_at = _plugin_connection_checked_at(connection)
        for product_id in _connection_product_ids(connection):
            entry = health_by_product.setdefault(
                product_id,
                {
                    "active_count": 0,
                    "checked_count": 0,
                    "failed_count": 0,
                    "latest_checked_at": None,
                    "total_count": 0,
                },
            )
            entry["total_count"] += 1
            if enabled:
                entry["active_count"] += 1
            if test_status != "unknown":
                entry["checked_count"] += 1
            if not enabled or test_status == "failed":
                entry["failed_count"] += 1
            if checked_at and (entry["latest_checked_at"] is None or checked_at > entry["latest_checked_at"]):
                entry["latest_checked_at"] = checked_at
    return health_by_product


def _product_permission_scope_counts(
    *,
    current_store: Any,
    request: Request | None,
) -> dict[str, int]:
    repository = None
    if request is not None:
        repository = getattr(request.app.state, "authorization_repository", None)
    repository = repository or _runtime_repository(current_store)
    if repository is None:
        return {}
    try:
        matrix = build_rbac_policy_matrix(repository)
    except Exception:  # pragma: no cover - defensive around partial repositories
        return {}
    counts: dict[str, int] = {}
    for row in matrix.get("rows") or []:
        for scope in row.get("scopes") or []:
            if not isinstance(scope, dict):
                continue
            if str(scope.get("scope_type") or "") not in {"product", "global"}:
                continue
            scope_id = str(scope.get("scope_id") or "")
            if not scope_id:
                continue
            counts[scope_id] = counts.get(scope_id, 0) + 1
    return counts


def _product_onboarding_scores(
    current_store: Any,
    *,
    request: Request | None = None,
) -> dict[str, Any]:
    products = list_product_records(current_store, active_only=False)
    active_products = [product for product in products if product.get("status") != "archived"]
    documents = _knowledge_documents_for_health(current_store)
    plugin_health_by_product = _product_plugin_health(current_store)
    permission_scope_counts = _product_permission_scope_counts(
        current_store=current_store,
        request=request,
    )
    products_payload: list[dict[str, Any]] = []
    for product in active_products:
        product_id = str(product.get("id") or "")
        versions = list_product_version_records(current_store, product_id, active_only=False)
        active_versions = [item for item in versions if item.get("status") != "archived"]
        modules = list_product_module_records(current_store, product_id, active_only=False)
        active_modules = [item for item in modules if item.get("status") != "archived"]
        git_repositories = list_product_git_repository_records(
            current_store,
            product_id,
            active_only=False,
        )
        active_git_repositories = [
            item for item in git_repositories if item.get("status") != "archived"
        ]
        related_systems = list_related_system_records(
            current_store,
            active_only=False,
            product_id=product_id,
        )
        active_related_systems = [
            item for item in related_systems if item.get("status") != "archived"
        ]
        product_documents = [
            document
            for document in documents
            if str(document.get("product_id") or "") == product_id
            and document.get("index_status") != "archived"
        ]
        searchable_product_documents = [
            document
            for document in product_documents
            if str(document.get("index_status") or "") in {"indexed", "text_indexed", "vector_indexed"}
        ]
        failed_product_documents = [
            document
            for document in product_documents
            if str(document.get("index_status") or "") == "index_failed"
        ]
        plugin_health = plugin_health_by_product.get(
            product_id,
            {
                "active_count": 0,
                "checked_count": 0,
                "failed_count": 0,
                "latest_checked_at": None,
                "total_count": 0,
            },
        )
        plugin_connection_count = int(plugin_health.get("active_count") or 0)
        failed_plugin_connection_count = int(plugin_health.get("failed_count") or 0)
        permission_scope_count = (
            permission_scope_counts.get(product_id, 0) + permission_scope_counts.get("*", 0)
        )
        health_issues: list[str] = []
        if not active_git_repositories:
            health_issues.append("缺少可用代码仓库")
        if not plugin_connection_count:
            health_issues.append("缺少可用插件连接")
        if failed_plugin_connection_count:
            health_issues.append("插件连接健康检查失败")
        if not permission_scope_count:
            health_issues.append("缺少产品权限范围")
        if failed_product_documents:
            health_issues.append("存在知识索引失败文档")
        if health_issues:
            recent_health_status = "degraded" if failed_plugin_connection_count or failed_product_documents else "attention"
        else:
            recent_health_status = "healthy"

        score = 0
        missing_items: list[str] = []
        if product.get("name") and product.get("status") == "active":
            score += 10
        else:
            missing_items.append("产品主数据未启用或缺名称")
        if active_versions:
            score += 10
        else:
            missing_items.append("未维护可用迭代版本")
        if active_modules:
            score += 10
        else:
            missing_items.append("未维护产品模块")
        if active_git_repositories:
            score += 15
        else:
            missing_items.append("未绑定代码仓库")
        if searchable_product_documents:
            score += 15
        else:
            missing_items.append("知识空间缺少可检索产品文档")
        if failed_product_documents:
            missing_items.append("存在知识索引失败文档")
        if active_related_systems:
            score += 10
        else:
            missing_items.append("未维护关联系统")
        if plugin_connection_count and not failed_plugin_connection_count:
            score += 10
        elif plugin_connection_count:
            score += 5
            missing_items.append("插件连接健康检查失败")
        else:
            missing_items.append("未绑定可用插件连接")
        if permission_scope_count:
            score += 10
        else:
            missing_items.append("未配置产品权限范围")
        if recent_health_status == "healthy":
            score += 10
        elif recent_health_status == "attention":
            score += 5
        score = min(score, 100)

        if score >= 80:
            status = "ready"
        elif score >= 50:
            status = "partial"
        else:
            status = "at_risk"
        products_payload.append(
            {
                "git_repository_count": len(active_git_repositories),
                "knowledge_document_count": len(product_documents),
                "missing_items": missing_items,
                "module_count": len(active_modules),
                "name": product.get("name") or product_id,
                "permission_scope_count": permission_scope_count,
                "permission_scope_status": "configured" if permission_scope_count else "missing",
                "plugin_connection_count": plugin_connection_count,
                "plugin_failed_connection_count": failed_plugin_connection_count,
                "plugin_total_connection_count": int(plugin_health.get("total_count") or 0),
                "product_id": product_id,
                "recent_health_check": {
                    "checked_at": plugin_health.get("latest_checked_at") or _now_iso(),
                    "failed_knowledge_document_count": len(failed_product_documents),
                    "failed_plugin_connection_count": failed_plugin_connection_count,
                    "issues": health_issues,
                    "status": recent_health_status,
                    "summary": "健康检查正常" if not health_issues else "；".join(health_issues[:4]),
                },
                "related_system_count": len(active_related_systems),
                "score": score,
                "recent_health_status": recent_health_status,
                "searchable_knowledge_document_count": len(searchable_product_documents),
                "status": status,
                "version_count": len(active_versions),
            },
        )
    products_payload.sort(key=lambda item: (int(item["score"]), str(item["name"])))
    average_score = (
        round(sum(int(item["score"]) for item in products_payload) / len(products_payload))
        if products_payload
        else 0
    )
    return {
        "products": products_payload,
        "summary": {
            "active_product_count": len(active_products),
            "average_score": average_score,
            "at_risk_count": sum(1 for item in products_payload if item["status"] == "at_risk"),
            "partial_count": sum(1 for item in products_payload if item["status"] == "partial"),
            "ready_count": sum(1 for item in products_payload if item["status"] == "ready"),
        },
    }


def _observability_check(current_store: Any) -> dict[str, Any]:
    audit_events = _items_from_store(current_store, "list_audit_events", "audit_events")
    traces = _items_from_store(current_store, "list_execution_traces", "execution_traces")
    otel_enabled = os.getenv("OBSERVABILITY_OTEL_ENABLED", "").lower() in {"1", "true", "yes"}
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    sentry_dsn = os.getenv("SENTRY_DSN", "").strip()
    prometheus_enabled = os.getenv("PROMETHEUS_ENABLED", "").lower() in {"1", "true", "yes"}
    configured = otel_enabled and bool(otlp_endpoint)
    partial = configured or prometheus_enabled or bool(sentry_dsn)
    return _check(
        action_href="/governance/execution-traces",
        category="观测告警",
        component="observability",
        description="平台已有 trace、审计和执行记录；外部指标、错误上报和告警接入可进一步闭环。",
        fix_suggestion="生产环境建议开启 OpenTelemetry OTLP、Prometheus 指标和 Sentry 错误上报，并配置 API/任务/插件失败告警。",
        key="observability",
        metrics={
            "audit_event_count": len(audit_events),
            "execution_trace_count": len(traces),
            "otel_enabled": otel_enabled,
            "prometheus_enabled": prometheus_enabled,
            "sentry_configured": bool(sentry_dsn),
        },
        status="configured" if configured else ("warning" if partial else "not_configured"),
        title="观测与告警",
    )


def _int_range(values: list[int], *, default: int | None = None) -> dict[str, Any]:
    if not values:
        return {
            "avg": default,
            "max": default,
            "min": default,
        }
    return {
        "avg": round(sum(values) / len(values)),
        "max": max(values),
        "min": min(values),
    }


def _task_configured_count(tasks: list[dict[str, Any]], config_key: str) -> int:
    count = 0
    for task in tasks:
        request_config = task.get("request_config") if isinstance(task.get("request_config"), dict) else {}
        reliability = request_config.get("reliability") if isinstance(request_config.get("reliability"), dict) else {}
        query = request_config.get("query") if isinstance(request_config.get("query"), dict) else {}
        if config_key in reliability or config_key in request_config or config_key in query:
            count += 1
    return count


def _ai_executor_strategy_config(
    *,
    lease_expired_tasks: list[dict[str, Any]],
    runners: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    task_timeout_values = [
        int(task.get("timeout_seconds") or 1800)
        for task in tasks
        if str(task.get("status") or "").lower() not in AI_EXECUTOR_TASK_TERMINAL_STATUSES
    ]
    lease_timeout_values = [lease_timeout_seconds(task) for task in tasks]
    reclaim_values = [max_reclaim_count(task) for task in tasks]
    heartbeat_values = [
        int(runner.get("heartbeat_timeout_seconds") or 120)
        for runner in runners
        if str(runner.get("status") or "").lower() == "active"
    ]
    cancellable_statuses = sorted(AI_EXECUTOR_TASK_STATUSES - AI_EXECUTOR_TASK_TERMINAL_STATUSES)
    retryable_statuses = sorted(AI_EXECUTOR_TASK_RETRYABLE_STATUSES)
    configuration_issues: list[dict[str, Any]] = []
    if not tasks:
        configuration_issues.append(
            {
                "level": "info",
                "message": "暂无执行任务样本，策略配置仅展示默认值。",
                "target": "ai_executor_tasks",
            }
        )
    if lease_expired_tasks:
        configuration_issues.append(
            {
                "level": "warning",
                "message": "存在租约已过期任务，应执行超时扫描释放 Runner 槽位。",
                "target": "lease_timeout",
            }
        )
    if task_timeout_values and max(task_timeout_values) > 24 * 60 * 60:
        configuration_issues.append(
            {
                "level": "warning",
                "message": "存在超过 24 小时的任务执行超时配置，建议复核是否会掩盖卡死任务。",
                "target": "task_timeout",
            }
        )
    if runners and not heartbeat_values:
        configuration_issues.append(
            {
                "level": "warning",
                "message": "没有 active Runner 心跳阈值样本，队列容量和超时判断可能不稳定。",
                "target": "runner_heartbeat",
            }
        )
    strategy_matrix = [
        {
            "action": "运行中的任务超过任务 timeout_seconds 后标记 timed_out，可从运维台重试。",
            "key": "timeout",
            "label": "超时策略",
            "source": "ai_executor_tasks.timeout_seconds",
            "status": "attention" if lease_expired_tasks else "configured",
            "threshold": _int_range(task_timeout_values, default=1800),
            "unit": "seconds",
        },
        {
            "action": "claimed/running 任务租约过期后先重排，超过回收次数进入 dead_letter。",
            "key": "lease_reclaim",
            "label": "租约回收",
            "source": "request_config.reliability.lease_timeout_seconds",
            "status": "attention" if lease_expired_tasks else "configured",
            "threshold": _int_range(lease_timeout_values, default=DEFAULT_LEASE_TIMEOUT_SECONDS),
            "unit": "seconds",
        },
        {
            "action": "租约回收次数达到阈值后转入 dead_letter，由管理员复核后重跑。",
            "key": "dead_letter",
            "label": "死信阈值",
            "source": "request_config.reliability.max_reclaim_count",
            "status": "configured",
            "threshold": _int_range(reclaim_values, default=DEFAULT_MAX_RECLAIM_COUNT),
            "unit": "times",
        },
        {
            "action": "failed/timed_out/dead_letter/cancelled 可一键重新入队，保留 retry_history。",
            "key": "manual_retry",
            "label": "重试策略",
            "retryable_statuses": retryable_statuses,
            "source": "AI_EXECUTOR_TASK_RETRYABLE_STATUSES",
            "status": "configured",
        },
        {
            "action": "queued/claimed/running 等非终态任务可取消并记录审计。",
            "cancellable_statuses": cancellable_statuses,
            "key": "manual_cancel",
            "label": "取消策略",
            "source": "AI_EXECUTOR_TASK_TERMINAL_STATUSES",
            "status": "configured",
        },
        {
            "action": "active Runner 超过心跳阈值未上报时会在健康诊断中视为离线。",
            "key": "runner_heartbeat",
            "label": "Runner 心跳",
            "source": "ai_executor_runners.heartbeat_timeout_seconds",
            "status": "configured" if heartbeat_values else "attention",
            "threshold": _int_range(heartbeat_values, default=120),
            "unit": "seconds",
        },
    ]
    return {
        "active_lease_statuses": sorted(LEASE_ACTIVE_STATUSES),
        "cancellable_statuses": cancellable_statuses,
        "configuration_issues": configuration_issues,
        "configured_task_count": {
            "lease_timeout_seconds": _task_configured_count(tasks, "lease_timeout_seconds"),
            "max_reclaim_count": _task_configured_count(tasks, "max_reclaim_count"),
            "timeout_seconds": sum(1 for task in tasks if task.get("timeout_seconds")),
        },
        "dead_letter_after_reclaim_count": _int_range(reclaim_values, default=DEFAULT_MAX_RECLAIM_COUNT),
        "lease_timeout_seconds": _int_range(lease_timeout_values, default=DEFAULT_LEASE_TIMEOUT_SECONDS),
        "recommendation": (
            "存在租约过期或策略异常，建议先执行超时扫描，再复核任务 timeout、租约和 Runner 心跳阈值。"
            if configuration_issues
            else "重试、取消、超时和死信策略已具备可操作闭环，建议按失败分布定期复盘阈值。"
        ),
        "retryable_statuses": retryable_statuses,
        "runner_heartbeat_timeout_seconds": _int_range(heartbeat_values, default=120),
        "status": "attention" if configuration_issues else "configured",
        "strategy_matrix": strategy_matrix,
        "task_timeout_seconds": _int_range(task_timeout_values, default=1800),
    }


def _ai_executor_ops(current_store: Any) -> dict[str, Any]:
    runners = _items_from_store(current_store, "list_ai_executor_runners", "ai_executor_runners")
    tasks = _items_from_store(current_store, "list_ai_executor_tasks", "ai_executor_tasks")
    approvals = _items_from_store(
        current_store,
        "list_ai_executor_approval_requests",
        "ai_executor_approval_requests",
    )
    status_counts = _count_by_status(tasks)
    runner_status_counts = _count_by_status(runners)
    now = datetime.now(UTC)
    lease_expired_tasks = [
        task
        for task in tasks
        if str(task.get("status") or "").lower() in {"claimed", "running"}
        and (lease_expires_at := _parse_datetime(task.get("lease_expires_at"))) is not None
        and lease_expires_at <= now
    ]
    latest_active_tasks = sorted(
        [
            task
            for task in tasks
            if str(task.get("status") or "").lower() in {"queued", "claimed", "running"}
        ],
        key=lambda task: (
            task.get("updated_at") or task.get("claimed_at") or task.get("created_at") or "",
            task.get("id") or "",
        ),
        reverse=True,
    )[:5]
    latest_failures = sorted(
        [
            task
            for task in tasks
            if str(task.get("status") or "").lower()
            in {"dead_letter", "failed", "timed_out"}
        ],
        key=lambda task: (
            task.get("finished_at") or task.get("updated_at") or task.get("created_at") or "",
            task.get("id") or "",
        ),
        reverse=True,
    )[:5]
    failure_reason_counts: dict[str, int] = {}
    for task in tasks:
        if str(task.get("status") or "").lower() not in {"cancelled", "dead_letter", "failed", "timed_out"}:
            continue
        reason = (
            task.get("failure_reason")
            or task.get("error_code")
            or task.get("dead_letter_reason")
            or task.get("status")
            or "unknown"
        )
        normalized_reason = _redact_error_summary(str(reason)) or "unknown"
        failure_reason_counts[normalized_reason] = failure_reason_counts.get(normalized_reason, 0) + 1
    total_capacity = sum(max(0, int(runner.get("max_concurrent_tasks") or 0)) for runner in runners)
    running_total = status_counts.get("claimed", 0) + status_counts.get("running", 0)
    queued_count = status_counts.get("queued", 0)
    failed_total = (
        status_counts.get("dead_letter", 0)
        + status_counts.get("failed", 0)
        + status_counts.get("timed_out", 0)
    )
    pending_approvals = [
        item for item in approvals if str(item.get("status") or "").lower() == "pending"
    ]
    strategy_config = _ai_executor_strategy_config(
        lease_expired_tasks=lease_expired_tasks,
        runners=runners,
        tasks=tasks,
    )

    def task_brief(task: dict[str, Any]) -> dict[str, Any]:
        return {
            "ai_task_id": task.get("ai_task_id"),
            "created_at": task.get("created_at"),
            "error_code": task.get("error_code"),
            "error_message": _redact_error_summary(str(task.get("error_message") or ""))
            if task.get("error_message")
            else None,
            "executor_type": task.get("executor_type"),
            "id": task.get("id"),
            "runner_id": task.get("runner_id"),
            "scheduled_job_run_id": task.get("scheduled_job_run_id"),
            "status": task.get("status"),
            "updated_at": task.get("updated_at")
            or task.get("finished_at")
            or task.get("claimed_at")
            or task.get("created_at"),
        }

    return {
        "controls": [
            {
                "description": "将 failed、timed_out 或 dead_letter 任务重新放回队列。",
                "label": "重试失败任务",
                "target": "/tasks/plugins",
            },
            {
                "description": "取消长期排队或不再需要的 Runner 任务，并保留审计。",
                "label": "取消积压任务",
                "target": "/tasks/plugins",
            },
            {
                "description": "扫描租约过期任务，释放卡住的 Runner 槽位。",
                "label": "超时扫描",
                "target": "/tasks/plugins",
            },
        ],
        "latest_active_tasks": [task_brief(task) for task in latest_active_tasks],
        "latest_failures": [task_brief(failure) for failure in latest_failures],
        "operation_targets": {
            "cancellable_count": queued_count + running_total,
            "retryable_count": failed_total + status_counts.get("cancelled", 0),
            "timeout_scan_count": len(lease_expired_tasks),
        },
        "runner_health": {
            "active_runner_count": runner_status_counts.get("active", 0),
            "offline_runner_count": runner_status_counts.get("offline", 0)
            + runner_status_counts.get("disabled", 0),
            "runner_status_counts": runner_status_counts,
            "total_runner_count": len(runners),
        },
        "failure_reason_distribution": [
            {"count": count, "reason": reason}
            for reason, count in sorted(
                failure_reason_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:8]
        ],
        "policies": {
            "cancel_strategy": "支持取消 queued/claimed/running 等任务并保留审计事件。",
            "dead_letter_strategy": "租约多次失效或超过重试上限后进入 dead_letter，需人工确认。",
            "retry_strategy": "failed、timed_out、dead_letter、cancelled 可重新入队。",
            "timeout_strategy": "超时扫描会释放过期租约，并按可靠性策略重排或转死信。",
        },
        "strategy_config": strategy_config,
        "summary": {
            "dead_letter_count": status_counts.get("dead_letter", 0),
            "failed_total": failed_total,
            "lease_expired_count": len(lease_expired_tasks),
            "pending_approval_count": len(pending_approvals),
            "queue_pressure": _ratio(queued_count, max(total_capacity, 1))
            if runners
            else None,
            "queued_count": queued_count,
            "running_count": running_total,
            "timed_out_count": status_counts.get("timed_out", 0),
            "total_capacity": total_capacity,
            "total_task_count": len(tasks),
        },
        "task_status_counts": status_counts,
    }


def _knowledge_quality_loop(
    current_store: Any,
    knowledge_check: dict[str, Any],
) -> dict[str, Any]:
    documents = _knowledge_documents_for_health(current_store)
    spaces = _knowledge_spaces_for_health(current_store)
    import_jobs = _items_from_repository_payload(
        current_store,
        memory_attr="knowledge_import_jobs",
        payload_key="knowledge_import_jobs",
        repository_method="load_knowledge",
    )
    deposits = _items_from_store(current_store, "list_knowledge_deposits", "knowledge_deposits")
    metrics = knowledge_check.get("metrics") or {}
    total_documents = int(metrics.get("total_documents") or len(documents) or 0)
    searchable_documents = int(metrics.get("searchable_documents") or 0)
    failed_documents = int(metrics.get("index_failed_documents") or 0)
    status_counts = _count_by_status(documents, field="index_status")
    failed_import_jobs = [
        item for item in import_jobs if str(item.get("status") or "").lower() == "failed"
    ]
    pending_deposits = [
        item for item in deposits if str(item.get("status") or "").lower() == "pending"
    ]
    quality_metrics = knowledge_quality_summary(current_store, since_days=30)
    stale_days = int(os.getenv("KNOWLEDGE_DOC_STALE_DAYS", "180") or "180")
    now = datetime.now(UTC)
    active_document_statuses = {"archived", "deleted"}
    spaces_by_id = {str(space.get("id")): space for space in spaces if space.get("id")}
    stale_documents = [
        document
        for document in documents
        if (
            (
                _updated_at := _parse_datetime(
                    document.get("updated_at") or document.get("created_at"),
                )
            )
            is not None
        )
        and (now - _updated_at).days >= stale_days
        and str(document.get("index_status") or "").lower() not in active_document_statuses
    ]
    index_failed_documents = [
        document
        for document in documents
        if str(document.get("index_status") or "").lower()
        in {"failed", "index_failed", "pending_index", "importing"}
    ]
    keyword_only_documents = [
        document
        for document in documents
        if str(document.get("index_status") or "").lower() in {"keyword_only", "text_indexed"}
    ]
    zero_chunk_documents = [
        document
        for document in documents
        if str(document.get("index_status") or "").lower()
        in {"indexed", "text_indexed", "vector_indexed"}
        and int(document.get("chunk_count") or 0) == 0
    ]
    low_quality_documents = [
        document
        for document in documents
        if document in index_failed_documents
        or document in keyword_only_documents
        or document in zero_chunk_documents
    ]
    stale_document_ids = {str(document.get("id")) for document in stale_documents if document.get("id")}
    low_quality_document_ids = {
        str(document.get("id")) for document in low_quality_documents if document.get("id")
    }

    def _governance_candidate(document: dict[str, Any]) -> dict[str, Any]:
        document_id = str(document.get("id") or "")
        index_status = str(document.get("index_status") or "unknown").lower()
        updated_at = _parse_datetime(document.get("updated_at") or document.get("created_at"))
        age_days = (now - updated_at).days if updated_at else None
        reasons: list[str] = []
        suggested_actions: list[str] = []
        severity = "low"
        if index_status in {"failed", "index_failed", "pending_index", "importing"}:
            reasons.append("索引未完成或失败")
            suggested_actions.append("重新索引并查看导入/解析日志")
            severity = "high" if index_status in {"failed", "index_failed"} else "medium"
        if index_status in {"keyword_only", "text_indexed"}:
            reasons.append("仅关键词索引，缺少向量召回")
            suggested_actions.append("补齐 Embedding 配置并重建向量索引")
            severity = "medium" if severity == "low" else severity
        if document in zero_chunk_documents:
            reasons.append("没有可检索分片")
            suggested_actions.append("重新解析文档或检查文件内容")
            severity = "high"
        if document_id in stale_document_ids:
            reasons.append(f"{stale_days} 天未更新")
            suggested_actions.append("确认内容是否过期，更新文档或归档")
            severity = "medium" if severity == "low" else severity
        knowledge_space_id = (
            document.get("knowledge_space_id")
            or document.get("space_id")
            or document.get("target_space_id")
        )
        space = spaces_by_id.get(str(knowledge_space_id)) if knowledge_space_id else None
        return {
            "age_days": age_days,
            "document_id": document.get("id"),
            "index_status": document.get("index_status"),
            "knowledge_space_id": knowledge_space_id,
            "knowledge_space_name": (space or {}).get("name") or (space or {}).get("title"),
            "product_id": document.get("product_id"),
            "reason": "、".join(reasons) if reasons else "待复核",
            "reasons": reasons,
            "severity": severity,
            "suggested_action": "；".join(dict.fromkeys(suggested_actions)) or "复核文档质量",
            "title": document.get("title") or document.get("file_name") or document.get("id"),
            "updated_at": document.get("updated_at") or document.get("created_at"),
        }

    governance_candidates = [
        _governance_candidate(document)
        for document in documents
        if str(document.get("id") or "") in low_quality_document_ids
        or str(document.get("id") or "") in stale_document_ids
    ]
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    governance_candidates.sort(
        key=lambda item: (
            severity_rank.get(str(item.get("severity") or "low"), 3),
            -(int(item.get("age_days") or 0)),
            str(item.get("title") or ""),
        )
    )
    no_result_rate = quality_metrics.get("no_result_rate")
    citation_click_rate = quality_metrics.get("citation_click_rate")
    citation_accuracy = quality_metrics.get("rag_citation_accuracy_proxy")
    query_count = int(quality_metrics.get("query_count") or 0)
    return {
        "feedback_loop": {
            "citation_accuracy_status": "observed" if citation_accuracy is not None else "waiting_feedback",
            "citation_click_rate": citation_click_rate,
            "citation_click_status": "observed" if citation_click_rate is not None else "waiting_clicks",
            "metrics_window_days": quality_metrics.get("since_days"),
            "no_result_rate": no_result_rate,
            "no_result_rate_status": "observed" if query_count else "waiting_queries",
            "rag_citation_accuracy_proxy": citation_accuracy,
            "rag_feedback_status": "observed"
            if int(quality_metrics.get("feedback_count") or 0)
            else "waiting_feedback",
            "recommendation": (
                "继续引导用户点击引用和提交有用/无用反馈，优先治理无结果查询和过期文档。"
                if query_count
                else "检索日志已接入，等待真实搜索和 RAG 问答产生质量样本。"
            ),
            "summary": quality_metrics,
        },
        "quality_gates": [
            {
                "metric": "searchable_ratio",
                "passed": total_documents == 0 or searchable_documents >= total_documents - failed_documents,
                "target": "可检索文档应覆盖全部非失败文档",
                "value": _ratio(searchable_documents, total_documents),
            },
            {
                "metric": "index_failed_documents",
                "passed": failed_documents == 0,
                "target": "索引失败文档为 0",
                "value": failed_documents,
            },
            {
                "metric": "pending_deposits",
                "passed": len(pending_deposits) == 0,
                "target": "沉淀候选及时审核",
                "value": len(pending_deposits),
            },
            {
                "metric": "no_result_rate",
                "passed": no_result_rate is None or no_result_rate <= 0.3,
                "target": "近 30 天检索/RAG 无结果率不超过 30%",
                "value": no_result_rate,
            },
            {
                "metric": "outdated_documents",
                "passed": len(stale_documents) == 0,
                "target": f"{stale_days} 天未更新文档需要复核",
                "value": len(stale_documents),
            },
        ],
        "governance_candidates": governance_candidates[:8],
        "governance_summary": {
            "failed_import_job_count": len(failed_import_jobs),
            "governance_candidate_count": len(governance_candidates),
            "index_failed_document_count": len(index_failed_documents),
            "keyword_only_document_count": len(keyword_only_documents),
            "low_quality_document_count": len(low_quality_documents),
            "stale_days": stale_days,
            "stale_document_count": len(stale_documents),
            "zero_chunk_document_count": len(zero_chunk_documents),
        },
        "summary": {
            "active_space_count": sum(1 for item in spaces if item.get("status") == "active"),
            "citation_click_rate": citation_click_rate,
            "failed_import_job_count": len(failed_import_jobs),
            "index_failed_documents": failed_documents,
            "keyword_only_document_count": len(keyword_only_documents),
            "low_quality_document_count": len(low_quality_documents),
            "no_result_rate": no_result_rate,
            "outdated_document_count": len(stale_documents),
            "pending_deposit_count": len(pending_deposits),
            "quality_event_count": query_count,
            "rag_citation_accuracy_proxy": citation_accuracy,
            "searchable_documents": searchable_documents,
            "searchable_ratio": _ratio(searchable_documents, total_documents),
            "status_counts": status_counts,
            "total_documents": total_documents,
            "total_space_count": len(spaces),
        },
        "watch_documents": [
            {
                "document_id": document.get("id"),
                "index_status": document.get("index_status"),
                "reason": "过期" if str(document.get("id") or "") in stale_document_ids else "低质量",
                "title": document.get("title"),
                "updated_at": document.get("updated_at"),
            }
            for document in [*low_quality_documents[:3], *stale_documents[:3]]
        ][:5],
    }


def _permission_diagnostics(*, current_store: Any, request: Request) -> dict[str, Any]:
    repository = getattr(request.app.state, "authorization_repository", None) or _runtime_repository(
        current_store
    )
    if repository is None:
        return {
            "diagnostics": [
                {
                    "level": "warning",
                    "message": "当前运行时未暴露 RBAC repository，无法生成权限矩阵摘要。",
                },
            ],
            "summary": {
                "active_role_count": 0,
                "roles_with_high_risk_permissions": 0,
                "roles_with_menu_permission_gaps": 0,
                "roles_without_scope": 0,
            },
        }
    try:
        matrix = build_rbac_policy_matrix(repository)
    except Exception as exc:  # pragma: no cover - defensive around partial repositories
        return {
            "diagnostics": [
                {
                    "level": "warning",
                    "message": f"权限矩阵生成失败：{exc.__class__.__name__}",
                },
            ],
            "summary": {
                "active_role_count": 0,
                "roles_with_high_risk_permissions": 0,
                "roles_with_menu_permission_gaps": 0,
                "roles_without_scope": 0,
            },
        }
    rows = matrix.get("rows") or []
    active_rows = [row for row in rows if row.get("status") == "active"]
    rows_without_scope = [row for row in active_rows if not row.get("scope_count")]
    high_risk_rows = [row for row in rows if int(row.get("high_risk_permission_count") or 0) > 0]
    menu_gap_rows = [row for row in rows if row.get("missing_menu_permission_codes")]
    scope_comparison: dict[str, dict[str, int]] = {}
    for row in active_rows:
        role_code = str(row.get("role_code") or "")
        access_levels = {"admin": 0, "read": 0, "viewer": 0, "write": 0}
        for scope in row.get("scopes") or []:
            if not isinstance(scope, dict):
                continue
            access_level = str(scope.get("access_level") or "read")
            if access_level in access_levels:
                access_levels[access_level] += 1
        scope_comparison[role_code] = access_levels
    diagnostics: list[dict[str, Any]] = []
    if menu_gap_rows:
        diagnostics.append(
            {
                "level": "warning",
                "message": "存在菜单授权与权限点不一致的角色",
                "role_codes": [row.get("role_code") for row in menu_gap_rows[:6]],
            },
        )
    if high_risk_rows:
        diagnostics.append(
            {
                "level": "risk",
                "message": "存在包含高风险权限点的角色",
                "role_codes": [row.get("role_code") for row in high_risk_rows[:6]],
            },
        )
    if rows_without_scope:
        diagnostics.append(
            {
                "level": "warning",
                "message": "存在未配置数据范围的启用角色",
                "role_codes": [row.get("role_code") for row in rows_without_scope[:6]],
            },
        )
    auto_fix_suggestions = [
        {
            "action": "sync_menu_required_permissions",
            "description": "保存角色前自动补齐菜单必需权限，避免菜单可见但接口 Forbidden。",
            "role_codes": [row.get("role_code") for row in menu_gap_rows[:6]],
        }
    ] if menu_gap_rows else []
    risk_precheck = {
        "blocking_issue_count": len(menu_gap_rows) + len(rows_without_scope),
        "high_risk_permission_role_count": len(high_risk_rows),
        "status": "attention"
        if menu_gap_rows or rows_without_scope or high_risk_rows
        else "pass",
    }
    return {
        "auto_fix_suggestions": auto_fix_suggestions,
        "diagnostics": diagnostics,
        "risk_precheck": risk_precheck,
        "scope_comparison": scope_comparison,
        "summary": {
            "active_role_count": len(active_rows),
            "permission_count": (matrix.get("summary") or {}).get("permission_count", 0),
            "roles_with_high_risk_permissions": len(high_risk_rows),
            "roles_with_menu_permission_gaps": len(menu_gap_rows),
            "roles_without_scope": len(rows_without_scope),
            "scope_grant_count": (matrix.get("summary") or {}).get("scope_grant_count", 0),
        },
        "user_menu_preview": {
            "available": True,
            "description": "可基于用户有效角色和菜单授权预览该用户实际可见菜单，排查菜单和接口权限不一致。",
            "target": "/system/roles",
        },
    }


def _dingtalk_connections(current_store: Any) -> list[dict[str, Any]]:
    connections = _items_from_store(
        current_store,
        "list_plugin_connections",
        "plugin_connections",
    )
    return [
        item
        for item in connections
        if "dingtalk" in str(item.get("plugin_code") or item.get("plugin_id") or "").lower()
        or "钉钉" in str(item.get("plugin_name") or item.get("name") or "")
    ]


def _dingtalk_key_expiry_alerts(connections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    alerts: list[dict[str, Any]] = []
    for connection in connections:
        auth_config = connection.get("auth_config") if isinstance(connection.get("auth_config"), dict) else {}
        expires_at = _parse_datetime(auth_config.get("key_expires_at"))
        if expires_at is None:
            continue
        days_left = (expires_at - now).days
        severity = "expired" if days_left < 0 else ("warning" if days_left <= 14 else "info")
        alerts.append(
            {
                "connection_id": connection.get("id"),
                "connection_name": connection.get("name") or connection.get("plugin_name"),
                "days_left": days_left,
                "expires_at": expires_at.isoformat(),
                "severity": severity,
            },
        )
    alerts.sort(key=lambda item: int(item.get("days_left") or 9999))
    return alerts


def _dingtalk_lifecycle(
    *,
    current_store: Any,
    request: Request,
    settings: Settings,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    connections = _dingtalk_connections(current_store)
    failed_connections = [
        connection
        for connection in connections
        if str(connection.get("status") or "").lower() not in {"active", "enabled"}
        or str((connection.get("last_test_summary") or {}).get("status") or "").lower()
        in {"failed", "error"}
    ]
    identity_repository = getattr(request.app.state, "external_identity_repository", None)
    list_identities = getattr(identity_repository, "list_identities", None)
    identities = (
        list_identities(provider="dingtalk", status=None, user_id=None)
        if callable(list_identities)
        else []
    )
    status_counts = _count_by_status(identities)
    expiry_alerts = _dingtalk_key_expiry_alerts(connections)
    corp_names = sorted(
        {
            str(identity.get("corp_name") or settings.dingtalk_corp_name_map.get(str(identity.get("corp_id") or "")) or "")
            for identity in identities
            if identity.get("corp_name") or settings.dingtalk_corp_name_map.get(str(identity.get("corp_id") or ""))
        }
    )
    authorization_subjects: list[dict[str, Any]] = []
    subject_type_counts: dict[str, int] = {}
    for connection in connections:
        auth_config = connection.get("auth_config") if isinstance(connection.get("auth_config"), dict) else {}
        request_config = (
            connection.get("request_config") if isinstance(connection.get("request_config"), dict) else {}
        )
        query = request_config.get("query") if isinstance(request_config.get("query"), dict) else {}
        subject_type = (
            query.get("auth_subject_type")
            or auth_config.get("auth_subject_type")
            or auth_config.get("subject_type")
            or "unknown"
        )
        normalized_subject_type = str(subject_type or "unknown")
        subject_type_counts[normalized_subject_type] = (
            subject_type_counts.get(normalized_subject_type, 0) + 1
        )
        corp_id = query.get("corp_id") or auth_config.get("corp_id")
        expires_at = _parse_datetime(auth_config.get("key_expires_at"))
        days_left = (expires_at - now).days if expires_at else None
        expiry_status = (
            "expired"
            if days_left is not None and days_left < 0
            else "warning"
            if days_left is not None and days_left <= 14
            else "healthy"
            if days_left is not None
            else "unknown"
        )
        last_test_summary = (
            connection.get("last_test_summary")
            if isinstance(connection.get("last_test_summary"), dict)
            else {}
        )
        subject_type_label = {
            "app": "应用授权",
            "system": "系统授权",
            "user": "个人授权",
            "unknown": "未声明",
        }.get(normalized_subject_type, normalized_subject_type)
        authorization_subjects.append(
            {
                "boundary": {
                    "app": "应用授权适合统一应用身份访问企业级资源。",
                    "system": "系统授权适合企业统一连接，由管理员集中维护和轮换。",
                    "user": "个人授权仅代表当前授权用户，适合个人空间或临时连接。",
                    "unknown": "未声明授权主体，建议补齐个人/系统/应用边界。",
                }.get(normalized_subject_type, "未声明授权主体，建议补齐个人/系统/应用边界。"),
                "connection_id": connection.get("id"),
                "connection_name": connection.get("name"),
                "corp_id": corp_id,
                "corp_name": settings.dingtalk_corp_name_map.get(str(corp_id or "")),
                "days_left": days_left,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "expiry_status": expiry_status,
                "last_test_status": last_test_summary.get("status"),
                "plugin_code": connection.get("plugin_code") or connection.get("plugin_id"),
                "secret_ref_configured": bool(auth_config.get("secret_ref")),
                "status": connection.get("status"),
                "subject_label": f"{connection.get('name') or connection.get('id') or '钉钉连接'} · {subject_type_label}",
                "subject_type": normalized_subject_type,
                "subject_type_label": subject_type_label,
            },
        )
    return {
        "authorization_boundaries": [
            {
                "description": "个人授权代表具体用户，授权失效或人员离职会影响连接。",
                "subject_type": "user",
                "title": "个人授权",
            },
            {
                "description": "系统授权代表企业统一连接，适合知识库等共享能力。",
                "subject_type": "system",
                "title": "系统授权",
            },
            {
                "description": "应用授权代表钉钉应用身份，适合稳定的企业级自动化。",
                "subject_type": "app",
                "title": "应用授权",
            },
        ],
        "authorization_subject_summary": {
            "app": subject_type_counts.get("app", 0),
            "system": subject_type_counts.get("system", 0),
            "unknown": subject_type_counts.get("unknown", 0),
            "user": subject_type_counts.get("user", 0),
        },
        "authorization_subjects": authorization_subjects,
        "login": {
            "allowed_corp_count": len(settings.dingtalk_allowed_corp_id_set),
            "auto_provision": settings.dingtalk_auto_provision,
            "configured": settings.dingtalk_login_enabled
            and bool(settings.dingtalk_client_id)
            and bool(settings.dingtalk_client_secret_value)
            and bool(settings.dingtalk_redirect_uri),
            "corp_names": corp_names or sorted(settings.dingtalk_corp_name_map.values()),
            "enabled": settings.dingtalk_login_enabled,
            "pending_approval": settings.dingtalk_pending_approval,
        },
        "mcp": {
            "connection_count": len(connections),
            "failed_connection_count": len(failed_connections),
            "key_expiry_alerts": expiry_alerts,
            "soon_expiring_count": sum(
                1 for alert in expiry_alerts if alert.get("severity") in {"expired", "warning"}
            ),
        },
        "user_bindings": {
            "active_identity_count": status_counts.get("active", 0),
            "identity_status_counts": status_counts,
            "total_identity_count": len(identities),
        },
    }


def _retention_policies() -> list[dict[str, Any]]:
    definitions = [
        ("audit_events", "审计事件", "AUDIT_RETENTION_DAYS", 365, "合规审计建议至少保留一年。"),
        ("execution_traces", "执行诊断链路", "EXECUTION_TRACE_RETENTION_DAYS", 90, "链路详情用于排障，建议按季度归档。"),
        ("model_gateway_logs", "模型调用元数据", "MODEL_LOG_RETENTION_DAYS", 90, "只保留调用元数据，不保存完整提示词。"),
        ("scheduled_job_runs", "定时作业运行记录", "JOB_RUN_RETENTION_DAYS", 180, "作业结果建议保留到下一个审计周期。"),
        ("knowledge_import_jobs", "知识导入任务", "KNOWLEDGE_IMPORT_RETENTION_DAYS", 180, "导入失败证据保留到问题闭环。"),
        ("help_screenshots", "帮助截图", "HELP_SCREENSHOT_REFRESH_DAYS", 30, "界面明显变更后应刷新截图。"),
    ]
    policies: list[dict[str, Any]] = []
    for key, title, env_name, default_days, note in definitions:
        raw_value = os.getenv(env_name)
        try:
            days = int(raw_value) if raw_value else default_days
        except ValueError:
            days = default_days
        policies.append(
            {
                "configured": raw_value is not None,
                "days": days,
                "env": env_name,
                "key": key,
                "note": note,
                "title": title,
            },
        )
    return policies


def _record_timestamp(item: dict[str, Any]) -> datetime | None:
    for field in (
        "created_at",
        "updated_at",
        "finished_at",
        "completed_at",
        "ended_at",
        "started_at",
        "last_seen_at",
    ):
        parsed = _parse_datetime(item.get(field))
        if parsed is not None:
            return parsed
    return None


def _retention_items_for_policy(current_store: Any, policy_key: str) -> list[dict[str, Any]]:
    if policy_key == "audit_events":
        return _items_from_store(current_store, "list_audit_events", "audit_events")
    if policy_key == "execution_traces":
        return _items_from_store(current_store, "list_execution_traces", "execution_traces")
    if policy_key == "model_gateway_logs":
        return _items_from_store(current_store, "list_model_gateway_logs", "model_gateway_logs")
    if policy_key == "scheduled_job_runs":
        return _items_from_store(current_store, "list_scheduled_job_runs", "scheduled_job_runs")
    if policy_key == "knowledge_import_jobs":
        return _items_from_repository_payload(
            current_store,
            memory_attr="knowledge_import_jobs",
            payload_key="knowledge_import_jobs",
            repository_method="load_knowledge",
        )
    return []


def _retention_cleanup_status(
    current_store: Any,
    policies: list[dict[str, Any]],
) -> dict[str, Any]:
    now = datetime.now(UTC)
    policy_statuses: list[dict[str, Any]] = []
    expired_records: list[dict[str, Any]] = []
    for policy in policies:
        policy_key = str(policy.get("key") or "")
        if policy_key == "help_screenshots":
            continue
        items = _retention_items_for_policy(current_store, policy_key)
        days = int(policy.get("days") or 0)
        expired_items: list[tuple[dict[str, Any], int]] = []
        for item in items:
            timestamp = _record_timestamp(item)
            if timestamp is None:
                continue
            age_days = (now - timestamp).days
            if age_days >= days:
                expired_items.append((item, age_days))
        expired_items.sort(key=lambda pair: pair[1], reverse=True)
        policy_statuses.append(
            {
                "expired_count": len(expired_items),
                "key": policy_key,
                "retention_days": days,
                "status": "attention" if expired_items else "pass",
                "title": policy.get("title"),
                "total_count": len(items),
            }
        )
        for item, age_days in expired_items[:3]:
            expired_records.append(
                {
                    "age_days": age_days,
                    "id": item.get("id") or item.get("trace_id") or item.get("event_type"),
                    "policy_key": policy_key,
                    "status": item.get("status") or item.get("result"),
                    "title": item.get("title")
                    or item.get("name")
                    or item.get("event_type")
                    or item.get("purpose")
                    or item.get("job_id")
                    or item.get("id"),
                }
            )
    expired_records.sort(key=lambda item: int(item.get("age_days") or 0), reverse=True)
    total_expired = sum(int(item.get("expired_count") or 0) for item in policy_statuses)
    return {
        "cleanup_mode": "manual_review",
        "expired_records": expired_records[:8],
        "policies": policy_statuses,
        "recommendation": (
            "存在超过保留期的数据，建议先导出审计证据，再由管理员按策略归档或清理。"
            if total_expired
            else "暂无超过保留期的数据，继续按当前策略观察。"
        ),
        "status": "attention" if total_expired else "pass",
        "total_expired_count": total_expired,
    }


def _object_storage_cleanup_status(current_store: Any) -> dict[str, Any]:
    candidates = _object_storage_cleanup_candidates(current_store)
    orphan_assets = candidates["orphan_assets"]
    incomplete_assets = candidates["incomplete_assets"]
    cleanup_failed_assets = candidates["cleanup_failed_assets"]
    cleanup_ready_assets = candidates["cleanup_ready_assets"]
    metadata_only_assets = candidates["metadata_only_assets"]
    blocked_assets = candidates["blocked_assets"]
    status = "attention" if orphan_assets or incomplete_assets or cleanup_failed_assets else "pass"
    return {
        "blocked_asset_count": len(blocked_assets),
        "cleanup_failed_count": len(cleanup_failed_assets),
        "cleanup_ready_count": len(cleanup_ready_assets),
        "incomplete_asset_count": len(incomplete_assets),
        "metadata_only_cleanup_count": len(metadata_only_assets),
        "orphan_asset_count": len(orphan_assets),
        "recommendation": (
            "发现文档已删除但对象引用仍存在或对象信息不完整，建议复核知识文档删除结果并补偿清理对象存储。"
            if status == "attention"
            else "知识文档删除会同步尝试清理对象存储，当前未发现孤儿对象引用。"
        ),
        "sample_assets": [
            {
                "asset_id": asset.get("id"),
                "bucket": asset.get("bucket"),
                "document_id": asset.get("document_id"),
                "object_key": asset.get("object_key"),
            }
            for asset in [*orphan_assets[:3], *incomplete_assets[:3], *cleanup_failed_assets[:3]]
        ][:6],
        "status": status,
        "tracked_asset_count": len(candidates["assets"]),
    }


def _object_storage_cleanup_candidates(current_store: Any) -> dict[str, list[dict[str, Any]]]:
    assets = _items_from_repository_payload(
        current_store,
        memory_attr="knowledge_assets",
        payload_key="knowledge_assets",
        repository_method="load_knowledge",
    )
    documents = _knowledge_documents_for_health(current_store)
    document_ids = {str(document.get("id")) for document in documents if document.get("id")}
    orphan_assets = [
        asset
        for asset in assets
        if asset.get("document_id") and str(asset.get("document_id")) not in document_ids
    ]
    incomplete_assets = [
        asset
        for asset in assets
        if not asset.get("bucket") or not asset.get("object_key")
    ]
    cleanup_failed_assets = [
        asset
        for asset in assets
        if (asset.get("metadata") or {}).get("object_cleanup_error")
        or asset.get("object_cleanup_error")
    ]
    cleanup_ready_assets = [
        asset for asset in orphan_assets if asset.get("bucket") and asset.get("object_key")
    ]
    metadata_only_assets = [
        asset for asset in orphan_assets if not asset.get("bucket") or not asset.get("object_key")
    ]
    blocked_assets = [
        asset for asset in [*incomplete_assets, *cleanup_failed_assets] if asset not in orphan_assets
    ]
    return {
        "assets": assets,
        "blocked_assets": blocked_assets,
        "cleanup_failed_assets": cleanup_failed_assets,
        "cleanup_ready_assets": cleanup_ready_assets,
        "incomplete_assets": incomplete_assets,
        "metadata_only_assets": metadata_only_assets,
        "orphan_assets": orphan_assets,
    }


def _persist_object_storage_asset_cleanup(
    current_store: Any,
    *,
    audit_event: dict[str, Any],
    cleaned_asset_ids: set[str],
) -> None:
    repository = _runtime_repository(current_store)
    load_knowledge = getattr(repository, "load_knowledge", None)
    save_knowledge = getattr(repository, "save_knowledge", None)
    if callable(load_knowledge) and callable(save_knowledge):
        payload = load_knowledge()
        if not isinstance(payload, dict):
            payload = {}
        assets = payload.get("knowledge_assets", {})
        if isinstance(assets, dict):
            payload["knowledge_assets"] = {
                asset_id: asset
                for asset_id, asset in assets.items()
                if str(asset_id) not in cleaned_asset_ids
                and str((asset or {}).get("id") or "") not in cleaned_asset_ids
            }
        payload["audit_events"] = [audit_event]
        save_knowledge(payload)
        return
    memory_assets = getattr(current_store, "knowledge_assets", None)
    if isinstance(memory_assets, dict):
        for asset_id in cleaned_asset_ids:
            memory_assets.pop(asset_id, None)


def object_storage_cleanup_response(
    *,
    confirmed: bool,
    current_store: Any,
    reason: str | None,
    trace_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    from app.core.trace import envelope
    from app.services.knowledge_deposits import record_audit_event
    from app.services.object_storage import object_storage

    candidates = _object_storage_cleanup_candidates(current_store)
    cleanup_ready_assets = candidates["cleanup_ready_assets"]
    metadata_only_assets = candidates["metadata_only_assets"]
    blocked_assets = candidates["blocked_assets"]
    cleaned_asset_ids: set[str] = set()
    deleted_objects: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    storage = object_storage()
    if confirmed:
        for asset in cleanup_ready_assets:
            asset_id = str(asset.get("id") or "")
            bucket = str(asset.get("bucket") or "")
            object_key = str(asset.get("object_key") or "")
            try:
                storage.delete_object(bucket=bucket, object_key=object_key)
            except Exception as exc:  # pragma: no cover - depends on external object storage
                errors.append(
                    {
                        "asset_id": asset_id,
                        "error": exc.__class__.__name__,
                        "object_key": object_key,
                    }
                )
                continue
            if asset_id:
                cleaned_asset_ids.add(asset_id)
            deleted_objects.append(
                {
                    "asset_id": asset_id,
                    "bucket": bucket,
                    "object_key": object_key,
                }
            )
        for asset in metadata_only_assets:
            asset_id = str(asset.get("id") or "")
            if asset_id:
                cleaned_asset_ids.add(asset_id)
        if cleaned_asset_ids:
            audit_event = record_audit_event(
                current_store,
                event_type="system.object_storage.cleanup",
                actor_id=user["id"],
                subject_type="system_object_storage",
                subject_id="knowledge_assets",
            )
            audit_event["payload"] = {
                "blocked_asset_count": len(blocked_assets),
                "cleaned_asset_count": len(cleaned_asset_ids),
                "deleted_object_count": len(deleted_objects),
                "dry_run": False,
                "error_count": len(errors),
                "reason_configured": bool(reason and reason.strip()),
            }
            _persist_object_storage_asset_cleanup(
                current_store,
                audit_event=audit_event,
                cleaned_asset_ids=cleaned_asset_ids,
            )
    status = "dry_run"
    if confirmed:
        if errors and cleaned_asset_ids:
            status = "partial"
        elif errors:
            status = "failed"
        else:
            status = "completed"
    return envelope(
        {
            "blocked_asset_count": len(blocked_assets),
            "cleaned_asset_ids": sorted(cleaned_asset_ids),
            "confirmed": confirmed,
            "deleted_objects": deleted_objects,
            "dry_run": not confirmed,
            "errors": errors,
            "metadata_only_cleanup_count": len(metadata_only_assets),
            "object_delete_count": len(deleted_objects),
            "planned_asset_cleanup_count": len(cleanup_ready_assets) + len(metadata_only_assets),
            "planned_object_delete_count": len(cleanup_ready_assets),
            "reason_configured": bool(reason and reason.strip()),
            "sample_blocked_assets": [
                {
                    "asset_id": asset.get("id"),
                    "bucket": asset.get("bucket"),
                    "document_id": asset.get("document_id"),
                    "object_key": asset.get("object_key"),
                }
                for asset in blocked_assets[:6]
            ],
            "status": status,
            "trace_id": trace_id,
        },
        trace_id,
    )


def _fallback_help_screenshot_targets() -> list[dict[str, Any]]:
    return [
        {
            "article": "系统健康",
            "doc_path": "docs/08-help/assets/screenshots/system-health-overview.png",
            "public_path": "apps/web/public/help/screenshots/system-health-overview.png",
            "route": "/system/health",
            "source": "fallback",
        },
        {
            "article": "产品接入向导",
            "doc_path": "docs/08-help/assets/screenshots/assets-products-onboarding.png",
            "public_path": "apps/web/public/help/screenshots/assets-products-onboarding.png",
            "route": "/assets/products",
            "source": "fallback",
        },
    ]


def _help_screenshot_article_label(alt: str, route: str, filename: str) -> str:
    label = alt.strip()
    for suffix in ("页面总览截图", "页面截图", "总览截图", "截图"):
        if label.endswith(suffix):
            label = label[: -len(suffix)].strip()
            break
    return label or route or filename.removesuffix(".png")


def _help_screenshot_targets_from_content(root: Path) -> list[dict[str, Any]]:
    help_content_path = root / "apps/web/src/pages/Help/helpContent.ts"
    if not help_content_path.exists():
        return []
    try:
        help_content = help_content_path.read_text(encoding="utf-8")
    except OSError:
        return []

    current_route = ""
    current_alt = ""
    targets: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for line in help_content.splitlines():
        route_match = re.search(r"route:\s*'([^']+)'", line)
        if route_match:
            current_route = route_match.group(1)
        alt_match = re.search(r"alt:\s*'([^']+)'", line)
        if alt_match:
            current_alt = alt_match.group(1)
        src_match = re.search(r"src:\s*'/help/screenshots/([^']+\.png)'", line)
        if not src_match:
            continue

        filename = src_match.group(1)
        key = (current_route, filename)
        if key in seen:
            continue
        seen.add(key)
        targets.append(
            {
                "article": _help_screenshot_article_label(current_alt, current_route, filename),
                "doc_path": f"docs/08-help/assets/screenshots/{filename}",
                "public_path": f"apps/web/public/help/screenshots/{filename}",
                "route": current_route,
                "source": "help_content",
            }
        )
        current_alt = ""
    return targets


def _help_screenshot_status() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[4]
    expected = _help_screenshot_targets_from_content(root) or _fallback_help_screenshot_targets()
    screenshots: list[dict[str, Any]] = []
    for item in expected:
        doc_file = root / item["doc_path"]
        public_file = root / item["public_path"]
        latest_mtime = max(
            [path.stat().st_mtime for path in (doc_file, public_file) if path.exists()],
            default=None,
        )
        screenshots.append(
            {
                **item,
                "exists": doc_file.exists() and public_file.exists(),
                "updated_at": datetime.fromtimestamp(latest_mtime, UTC).isoformat()
                if latest_mtime
                else None,
            },
        )
    return {
        "coverage": {
            "expected_count": len(expected),
            "ready_count": sum(1 for item in screenshots if item["exists"]),
        },
        "screenshots": screenshots,
    }


def _secret_ref_validity(secret_ref: str) -> tuple[str, str | None]:
    if secret_ref.startswith("env:"):
        env_name = secret_ref.removeprefix("env:").strip()
        if not env_name:
            return "invalid", "env 引用缺少变量名"
        if os.getenv(env_name):
            return "valid", None
        return "unresolved", "当前运行时未解析到对应环境变量"
    if secret_ref.startswith("vault/"):
        return "valid", None
    return "warning", "建议统一使用 env:NAME 或 vault/path 形式"


def _collect_secret_refs(
    value: Any,
    *,
    prefix: str,
    refs: list[dict[str, Any]],
    direct_secret_paths: list[str],
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            normalized_key = str(key).lower()
            if normalized_key in {"secret_ref", "token_ref", "api_key_ref"} or normalized_key.endswith("_secret_ref"):
                if isinstance(child, str) and child.strip():
                    status, issue = _secret_ref_validity(child.strip())
                    refs.append(
                        {
                            "issue": issue,
                            "path": path,
                            "status": status,
                            "type": child.split(":", 1)[0] if ":" in child else child.split("/", 1)[0],
                        }
                    )
                else:
                    refs.append(
                        {
                            "issue": "密钥引用为空",
                            "path": path,
                            "status": "missing",
                            "type": "unknown",
                        }
                    )
                continue
            if normalized_key in {"api_key", "client_secret", "password", "secret", "smtp_password", "token"}:
                if child:
                    direct_secret_paths.append(path)
                continue
            _collect_secret_refs(
                child,
                prefix=path,
                refs=refs,
                direct_secret_paths=direct_secret_paths,
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _collect_secret_refs(
                child,
                prefix=f"{prefix}[{index}]",
                refs=refs,
                direct_secret_paths=direct_secret_paths,
            )


def _security_audit_governance(current_store: Any) -> dict[str, Any]:
    settings_payload = system_settings_response(current_store)
    plugin_connections = _items_from_store(
        current_store,
        "list_plugin_connections",
        "plugin_connections",
    )
    model_gateway_configs = _items_from_store(
        current_store,
        "list_model_gateway_configs",
        "model_gateway_configs",
    )
    audit_events = _items_from_store(current_store, "list_audit_events", "audit_events")
    secret_refs: list[dict[str, Any]] = []
    direct_secret_paths: list[str] = []
    _collect_secret_refs(
        settings_payload.get("email_delivery") or {},
        prefix="system_settings.email_delivery",
        refs=secret_refs,
        direct_secret_paths=direct_secret_paths,
    )
    for connection in plugin_connections:
        connection_id = connection.get("id") or connection.get("code") or "unknown"
        _collect_secret_refs(
            connection.get("auth_config") or {},
            prefix=f"plugin_connection.{connection_id}.auth_config",
            refs=secret_refs,
            direct_secret_paths=direct_secret_paths,
        )
    for config in model_gateway_configs:
        config_id = config.get("id") or config.get("name") or "unknown"
        _collect_secret_refs(
            config,
            prefix=f"model_gateway_config.{config_id}",
            refs=secret_refs,
            direct_secret_paths=direct_secret_paths,
        )

    now = datetime.now(UTC)
    recent_audit_events = [
        event
        for event in audit_events
        if (
            event_at := _parse_datetime(event.get("created_at"))
        ) is not None
        and (now - event_at).days <= 7
    ]
    sensitive_event_keywords = (
        "auth",
        "config",
        "gateway",
        "permission",
        "role",
        "secret",
        "settings",
        "user",
    )
    sensitive_config_events = [
        event
        for event in recent_audit_events
        if any(keyword in str(event.get("event_type") or "").lower() for keyword in sensitive_event_keywords)
    ]
    high_risk_operation_events = [
        event
        for event in recent_audit_events
        if str(event.get("result") or "").lower() in {"blocked", "failed"}
        or "delete" in str(event.get("event_type") or "").lower()
        or "admin" in str(event.get("event_type") or "").lower()
    ]
    invalid_refs = [
        ref
        for ref in secret_refs
        if ref.get("status") in {"invalid", "missing", "unresolved", "warning"}
    ]
    governance_actions: list[dict[str, Any]] = []
    if invalid_refs:
        governance_actions.append(
            {
                "detail": f"发现 {len(invalid_refs)} 个异常密钥引用，建议补齐 env/vault 配置后重新体检。",
                "key": "fix_invalid_secret_refs",
                "metric": len(invalid_refs),
                "severity": "high",
                "target": "/system/settings",
                "title": "修复异常密钥引用",
            }
        )
    if direct_secret_paths:
        governance_actions.append(
            {
                "detail": f"发现 {len(direct_secret_paths)} 个直接密钥配置，建议迁移为 env:NAME 或 vault/path 引用。",
                "key": "migrate_direct_secrets",
                "metric": len(direct_secret_paths),
                "severity": "medium",
                "target": "/system/settings",
                "title": "迁移直接密钥配置",
            }
        )
    if sensitive_config_events:
        governance_actions.append(
            {
                "detail": f"近 7 天有 {len(sensitive_config_events)} 次敏感配置或权限变更，建议复核确认原因和审计摘要。",
                "key": "review_sensitive_changes",
                "metric": len(sensitive_config_events),
                "severity": "medium",
                "target": "/governance/audit",
                "title": "复核敏感配置变更",
            }
        )
    if high_risk_operation_events:
        governance_actions.append(
            {
                "detail": f"近 7 天有 {len(high_risk_operation_events)} 次高风险或失败操作，建议进入审计与运行复盘。",
                "key": "review_high_risk_operations",
                "metric": len(high_risk_operation_events),
                "severity": "high",
                "target": "/governance/audit",
                "title": "复盘高风险操作",
            }
        )
    governance_actions.extend(
        [
            {
                "detail": "按当前筛选导出最近 1000 条脱敏审计摘要，用于问题复盘和合规留档。",
                "key": "export_audit_evidence",
                "metric": len(recent_audit_events),
                "severity": "low",
                "target": "/governance/audit",
                "title": "导出审计证据",
            },
            {
                "detail": "生成近 7 天管理员周报，覆盖告警、审计、权限、知识质量和 AI 执行失败。",
                "key": "generate_admin_weekly_report",
                "metric": len(recent_audit_events),
                "severity": "low",
                "target": "/system/health",
                "title": "生成管理员周报",
            },
        ]
    )
    return {
        "admin_weekly_report": {
            "available": True,
            "high_risk_operation_count": len(high_risk_operation_events),
            "recommendation": "每周汇总审计、告警、权限和敏感配置变更，发送给管理员复盘。",
            "sensitive_config_change_count": len(sensitive_config_events),
            "total_audit_events": len(recent_audit_events),
            "window_days": 7,
        },
        "audit_export": {
            "endpoint": "/api/audit/events/export",
            "supported": True,
        },
        "governance_actions": governance_actions[:8],
        "high_risk_confirmation": {
            "required": True,
            "controls": [
                "AI Runner 高风险指令要求平台审批",
                "系统告警关闭必须填写关闭原因",
                "系统邮件发送等敏感配置变更要求后端二次确认",
                "敏感配置审计只记录字段和配置状态，不记录密钥值",
            ],
            "status": "configured",
        },
        "secret_ref_validation": {
            "direct_secret_count": len(direct_secret_paths),
            "invalid_ref_count": len(invalid_refs),
            "issues": invalid_refs[:6],
            "ref_count": len(secret_refs),
            "status": "attention" if invalid_refs else "pass",
            "supported_formats": ["env:NAME", "vault/path"],
        },
        "sensitive_config_approval": {
            "policy": "敏感配置变更需要系统管理员权限；系统邮件发送配置写入必须携带二次确认和确认原因，审计仅记录字段、配置状态和确认状态。",
            "required": True,
            "status": "configured",
            "tracked_event_count_7d": len(sensitive_config_events),
        },
    }


def _alert_severity_for_check(check: dict[str, Any]) -> str:
    status = str(check.get("status") or "")
    rank = _status_rank(status)
    if rank >= 3:
        return "high"
    if rank >= 2:
        return "medium"
    if status in {"warning", "not_configured"}:
        return "low"
    return "low"


def _alert_rule_matches(rule: dict[str, Any], alert: dict[str, Any]) -> bool:
    if not bool(rule.get("enabled", True)):
        return False
    rule_source = str(rule.get("source") or "").strip()
    if rule_source and rule_source != str(alert.get("source") or ""):
        return False
    rule_component = str(rule.get("component") or "").strip()
    if rule_component and rule_component != str(alert.get("component") or ""):
        return False
    severity_min = str(rule.get("severity_min") or "medium")
    alert_severity = str(alert.get("severity") or "low")
    return ALERT_SEVERITY_RANK.get(alert_severity, 0) >= ALERT_SEVERITY_RANK.get(severity_min, 2)


def _apply_alert_rules(alerts: list[dict[str, Any]], rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rules:
        return alerts
    for alert in alerts:
        matched_rules = [
            rule
            for rule in rules
            if _alert_rule_matches(rule, alert)
        ]
        if not matched_rules:
            continue
        metadata = alert.get("metadata") if isinstance(alert.get("metadata"), dict) else {}
        alert["metadata"] = {
            **metadata,
            "matched_rule_ids": [rule.get("id") for rule in matched_rules if rule.get("id")],
        }
        if not alert.get("owner"):
            alert["owner"] = matched_rules[0].get("owner")
    return alerts


def _alert_incidents_from_memory(current_store: Any) -> dict[str, dict[str, Any]]:
    incidents = getattr(current_store, "system_alert_incidents", None)
    if not isinstance(incidents, dict):
        return {}
    return incidents


def _persist_alert_incidents(
    current_store: Any,
    alerts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    repository = _runtime_repository(current_store)
    upsert = getattr(repository, "upsert_system_alert_incidents", None)
    list_incidents = getattr(repository, "list_system_alert_incidents", None)
    if callable(upsert) and callable(list_incidents):
        try:
            return upsert(
                [
                    {
                        **alert,
                        "metadata": {
                            **(alert.get("metadata") if isinstance(alert.get("metadata"), dict) else {}),
                            "origin": "system_health",
                        },
                    }
                    for alert in alerts
                ]
            )
        except Exception:  # pragma: no cover - defensive around partially migrated runtimes
            return alerts
    incidents = _alert_incidents_from_memory(current_store)
    now = _now_iso()
    for alert in alerts:
        existing = incidents.get(str(alert["id"])) or {}
        incidents[str(alert["id"])] = {
            **alert,
            "created_at": existing.get("created_at") or now,
            "first_seen_at": existing.get("first_seen_at") or now,
            "last_seen_at": now,
            "metadata": existing.get("metadata") or alert.get("metadata") or {},
            "owner": existing.get("owner") or alert.get("owner"),
            "status": existing.get("status") or "open",
            "status_history": existing.get("status_history") or [],
            "updated_at": now,
        }
    return sorted(
        [dict(item) for item in incidents.values()],
        key=lambda item: (str(item.get("status") or ""), str(item.get("last_seen_at") or "")),
        reverse=True,
    )


def _alert_subscription_scope_matches(subscription: dict[str, Any], alert: dict[str, Any]) -> bool:
    scope = str(subscription.get("scope") or "global").strip()
    if scope in {"*", "all", "global"}:
        return True
    if ":" in scope:
        scope_type, scope_value = scope.split(":", 1)
        scope_value = scope_value.strip()
        if scope_type == "source":
            return scope_value == str(alert.get("source") or "")
        if scope_type == "component":
            return scope_value == str(alert.get("component") or "")
        if scope_type == "owner":
            return scope_value == str(alert.get("owner") or "")
        if scope_type == "severity":
            return scope_value == str(alert.get("severity") or "")
        return False
    return scope in {
        str(alert.get("source") or ""),
        str(alert.get("component") or ""),
        str(alert.get("owner") or ""),
    }


def _alert_subscription_matches(subscription: dict[str, Any], alert: dict[str, Any]) -> bool:
    if not bool(subscription.get("enabled", True)):
        return False
    if alert.get("status") in {"closed", "ignored"}:
        return False
    severity_min = str(subscription.get("severity_min") or "medium")
    alert_severity = str(alert.get("severity") or "low")
    if ALERT_SEVERITY_RANK.get(alert_severity, 0) < ALERT_SEVERITY_RANK.get(severity_min, 2):
        return False
    return _alert_subscription_scope_matches(subscription, alert)


def _alert_notification_id(alert_id: str, subscription_id: str) -> str:
    normalized_alert_id = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", alert_id.strip())
    normalized_subscription_id = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", subscription_id.strip())
    return f"alert_notification:{normalized_alert_id}:{normalized_subscription_id}"[:220]


def _build_alert_notifications(
    *,
    alerts: list[dict[str, Any]],
    subscriptions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    notifications: list[dict[str, Any]] = []
    for alert in alerts:
        alert_id = str(alert.get("id") or "").strip()
        if not alert_id:
            continue
        for subscription in subscriptions:
            subscription_id = str(subscription.get("id") or "").strip()
            if not subscription_id or not _alert_subscription_matches(subscription, alert):
                continue
            notifications.append(
                {
                    "alert_id": alert_id,
                    "channel": subscription.get("channel"),
                    "id": _alert_notification_id(alert_id, subscription_id),
                    "payload_json": {
                        "action_href": alert.get("action_href"),
                        "alert_status": alert.get("status"),
                        "component": alert.get("component"),
                        "last_seen_at": alert.get("last_seen_at"),
                        "matched_rule_ids": (
                            alert.get("metadata", {}).get("matched_rule_ids")
                            if isinstance(alert.get("metadata"), dict)
                            else []
                        ),
                        "message": alert.get("message"),
                        "owner": alert.get("owner"),
                        "source": alert.get("source"),
                        "title": alert.get("title"),
                    },
                    "severity": alert.get("severity") or "low",
                    "subscription_id": subscription_id,
                    "target": subscription.get("target"),
                }
            )
    return notifications


def _persist_alert_notifications(
    current_store: Any,
    notifications: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    repository = _runtime_repository(current_store)
    upsert = getattr(repository, "upsert_system_alert_notifications", None)
    if callable(upsert):
        try:
            return upsert(notifications)
        except Exception:  # pragma: no cover - defensive around partially migrated runtimes
            return []
    stored = getattr(current_store, "system_alert_notifications", None)
    if not isinstance(stored, dict):
        stored = {}
        vars(current_store)["system_alert_notifications"] = stored
    now = _now_iso()
    for notification in notifications:
        notification_id = str(notification["id"])
        existing = stored.get(notification_id) or {}
        if existing.get("status") in {"sent", "skipped"}:
            continue
        stored[notification_id] = {
            **existing,
            **notification,
            "attempts": int(existing.get("attempts") or 0),
            "created_at": existing.get("created_at") or now,
            "payload_json": {
                **(
                    existing.get("payload_json")
                    if isinstance(existing.get("payload_json"), dict)
                    else {}
                ),
                **(
                    notification.get("payload_json")
                    if isinstance(notification.get("payload_json"), dict)
                    else {}
                ),
            },
            "status": existing.get("status") or "pending",
            "updated_at": now,
        }
    return _list_alert_notifications(current_store)


def _list_alert_notifications(
    current_store: Any,
    *,
    limit: int = 100,
    status: str | None = None,
) -> list[dict[str, Any]]:
    repository = _runtime_repository(current_store)
    list_notifications = getattr(repository, "list_system_alert_notifications", None)
    if callable(list_notifications):
        try:
            return list_notifications(limit=limit, status=status)
        except Exception:  # pragma: no cover - defensive around partially migrated runtimes
            return []
    notifications = getattr(current_store, "system_alert_notifications", {})
    if not isinstance(notifications, dict):
        return []
    items = [
        dict(item)
        for item in notifications.values()
        if status is None or str(item.get("status") or "") == status
    ]
    status_order = {"pending": 0, "failed": 1, "sent": 2, "skipped": 3}
    items.sort(
        key=lambda item: (
            status_order.get(str(item.get("status") or ""), 9),
            -(int(_parse_datetime(item.get("created_at")).timestamp()) if _parse_datetime(item.get("created_at")) else 0),
            str(item.get("id") or ""),
        )
    )
    return items[:limit]


def _alert_notification_summary(notifications: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = _count_by_status(notifications)
    channel_counts = _count_by_status(notifications, field="channel")
    return {
        "channel_counts": channel_counts,
        "failed_notification_count": status_counts.get("failed", 0),
        "pending_notification_count": status_counts.get("pending", 0),
        "sent_notification_count": status_counts.get("sent", 0),
        "skipped_notification_count": status_counts.get("skipped", 0),
        "total_notification_count": len(notifications),
    }


def _alert_history_trend(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trend: dict[str, dict[str, Any]] = {}
    for alert in alerts:
        seen_at = _parse_datetime(alert.get("last_seen_at") or alert.get("created_at"))
        if seen_at is None:
            continue
        day = seen_at.date().isoformat()
        entry = trend.setdefault(
            day,
            {"closed": 0, "date": day, "high": 0, "opened": 0, "total": 0},
        )
        entry["total"] += 1
        if alert.get("severity") == "high":
            entry["high"] += 1
        if alert.get("status") in {"closed", "ignored"}:
            entry["closed"] += 1
        else:
            entry["opened"] += 1
    return [trend[day] for day in sorted(trend.keys())[-14:]]


def _alert_center(
    current_store: Any,
    checks: list[dict[str, Any]],
    operations: dict[str, Any],
) -> dict[str, Any]:
    alerts: list[dict[str, Any]] = []
    rules = _list_alert_rules(current_store)
    owner_by_category = {
        "AI 执行运维": "平台运维",
        "产品接入": "产品负责人",
        "作业观测": "平台运维",
        "基础设施": "平台运维",
        "外部通知": "系统管理员",
        "插件集成": "平台运维",
        "模型能力": "AI 平台管理员",
        "知识质量": "知识管理员",
        "观测告警": "平台运维",
        "身份集成": "系统管理员",
    }
    for check in checks:
        status = str(check.get("status") or "")
        if _status_rank(status) == 0:
            continue
        severity = _alert_severity_for_check(check)
        alerts.append(
            {
                "action_href": check.get("action_href"),
                "component": check.get("component"),
                "id": f"check:{check.get('key')}",
                "message": check.get("fix_suggestion"),
                "owner": owner_by_category.get(str(check.get("category") or ""), "平台管理员"),
                "severity": severity,
                "source": "system_check",
                "status": "open",
                "title": check.get("title"),
            },
        )
    for product in (operations.get("product_onboarding_scores") or {}).get("products", [])[:8]:
        if int(product.get("score") or 0) >= 80:
            continue
        alerts.append(
            {
                "action_href": "/assets/products",
                "component": "product_onboarding",
                "id": f"product:{product.get('product_id')}",
                "message": "、".join(product.get("missing_items") or []) or "产品接入信息待补齐",
                "owner": "产品负责人",
                "severity": "medium" if int(product.get("score") or 0) < 50 else "low",
                "source": "product_score",
                "status": "open",
                "title": f"{product.get('name')} 接入完整度 {product.get('score')} 分",
            },
        )
    for alert in (operations.get("dingtalk_lifecycle") or {}).get("mcp", {}).get(
        "key_expiry_alerts",
        [],
    ):
        if alert.get("severity") not in {"expired", "warning"}:
            continue
        alerts.append(
            {
                "action_href": "/tasks/plugins",
                "component": "dingtalk_mcp",
                "id": f"dingtalk_key:{alert.get('connection_id')}",
                "message": f"授权 key 剩余 {alert.get('days_left')} 天，请及时轮换。",
                "owner": "平台运维",
                "severity": "high" if alert.get("severity") == "expired" else "medium",
                "source": "dingtalk_lifecycle",
                "status": "open",
                "title": f"{alert.get('connection_name') or '钉钉连接'} 授权即将到期",
            },
        )
    alerts = _persist_alert_incidents(current_store, _apply_alert_rules(alerts, rules))
    subscriptions = _list_alert_subscriptions(current_store)
    notifications = _persist_alert_notifications(
        current_store,
        _build_alert_notifications(alerts=alerts, subscriptions=subscriptions),
    )
    severity_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    status_order = {"open": 0, "acknowledged": 1, "resolving": 2, "ignored": 3, "closed": 4}
    alerts.sort(
        key=lambda item: (
            status_order.get(str(item.get("status")), 9),
            severity_order.get(str(item.get("severity")), 9),
            str(item.get("title")),
        )
    )
    open_alerts = [item for item in alerts if item.get("status") not in {"closed", "ignored"}]
    return {
        "alerts": alerts[:12],
        "notifications": notifications[:8],
        "rules": rules,
        "subscriptions": subscriptions,
        "summary": {
            "acknowledged_count": sum(1 for item in alerts if item.get("status") == "acknowledged"),
            "closed_count": sum(1 for item in alerts if item.get("status") == "closed"),
            "enabled_subscription_count": sum(1 for item in subscriptions if item.get("enabled")),
            "high_count": sum(1 for item in open_alerts if item.get("severity") == "high"),
            "low_count": sum(1 for item in open_alerts if item.get("severity") == "low"),
            "medium_count": sum(1 for item in open_alerts if item.get("severity") == "medium"),
            **_alert_notification_summary(notifications),
            "open_count": len(open_alerts),
            "resolving_count": sum(1 for item in alerts if item.get("status") == "resolving"),
            "rule_count": len(rules),
            "enabled_rule_count": sum(1 for item in rules if item.get("enabled")),
        },
        "trend": _alert_history_trend(alerts),
    }


def _list_alert_subscriptions(current_store: Any) -> list[dict[str, Any]]:
    repository = _runtime_repository(current_store)
    list_subscriptions = getattr(repository, "list_system_alert_subscriptions", None)
    if callable(list_subscriptions):
        try:
            return list_subscriptions()
        except Exception:  # pragma: no cover - defensive around partially migrated runtimes
            return []
    subscriptions = getattr(current_store, "system_alert_subscriptions", {})
    if isinstance(subscriptions, dict):
        return [dict(item) for item in subscriptions.values()]
    return []


def _find_alert_incident(current_store: Any, alert_id: str) -> dict[str, Any] | None:
    repository = _runtime_repository(current_store)
    list_incidents = getattr(repository, "list_system_alert_incidents", None)
    if callable(list_incidents):
        try:
            return next(
                (
                    dict(incident)
                    for incident in list_incidents()
                    if incident.get("id") == alert_id
                ),
                None,
            )
        except Exception:  # pragma: no cover - defensive around partially migrated runtimes
            return None
    incident = _alert_incidents_from_memory(current_store).get(alert_id)
    return dict(incident) if isinstance(incident, dict) else None


def _alert_incident_status_history(incident: dict[str, Any]) -> list[dict[str, Any]]:
    history = incident.get("status_history")
    if isinstance(history, list):
        return [dict(item) for item in history if isinstance(item, dict)]
    metadata = incident.get("metadata")
    if isinstance(metadata, dict) and isinstance(metadata.get("status_history"), list):
        return [dict(item) for item in metadata["status_history"] if isinstance(item, dict)]
    return []


def _alert_history_event(
    *,
    actor_id: str,
    close_reason: str | None,
    existing: dict[str, Any] | None,
    owner: str | None,
    postmortem: str | None,
    status: str | None,
) -> dict[str, Any]:
    existing = existing or {}
    from_status = str(existing.get("status") or "open")
    to_status = status or from_status
    changed_fields: list[str] = []
    if status is not None and status != existing.get("status"):
        changed_fields.append("status")
    if owner is not None and owner != existing.get("owner"):
        changed_fields.append("owner")
    if close_reason is not None and close_reason != existing.get("close_reason"):
        changed_fields.append("close_reason")
    if postmortem is not None and postmortem != existing.get("postmortem"):
        changed_fields.append("postmortem")
    return {
        "actor_id": actor_id,
        "at": _now_iso(),
        "changed_fields": changed_fields or ["touched"],
        "close_reason": close_reason
        if close_reason is not None
        else existing.get("close_reason"),
        "from_status": from_status,
        "owner": owner if owner is not None else existing.get("owner"),
        "postmortem_configured": bool(
            postmortem if postmortem is not None else existing.get("postmortem")
        ),
        "to_status": to_status,
    }


def _list_alert_rules(current_store: Any) -> list[dict[str, Any]]:
    repository = _runtime_repository(current_store)
    list_rules = getattr(repository, "list_system_alert_rules", None)
    if callable(list_rules):
        try:
            return list_rules()
        except Exception:  # pragma: no cover - defensive around partially migrated runtimes
            return []
    rules = getattr(current_store, "system_alert_rules", {})
    if isinstance(rules, dict):
        return [dict(item) for item in rules.values()]
    return []


def _operations_snapshot(
    *,
    checks: list[dict[str, Any]],
    current_store: Any,
    request: Request,
    settings: Settings,
) -> dict[str, Any]:
    checks_by_key = {str(check.get("key") or ""): check for check in checks}
    retention_policies = _retention_policies()
    operations = {
        "ai_executor_ops": _ai_executor_ops(current_store),
        "dingtalk_lifecycle": _dingtalk_lifecycle(
            current_store=current_store,
            request=request,
            settings=settings,
        ),
        "help_and_retention": {
            "cleanup_status": _retention_cleanup_status(current_store, retention_policies),
            "object_storage_cleanup": _object_storage_cleanup_status(current_store),
            "retention_policies": retention_policies,
            "screenshots": _help_screenshot_status(),
        },
        "knowledge_quality_loop": _knowledge_quality_loop(
            current_store,
            checks_by_key.get("knowledge_quality", {}),
        ),
        "permission_diagnostics": _permission_diagnostics(
            current_store=current_store,
            request=request,
        ),
        "product_onboarding_scores": _product_onboarding_scores(
            current_store,
            request=request,
        ),
        "security_audit_governance": _security_audit_governance(current_store),
    }
    operations["alert_center"] = _alert_center(current_store, checks, operations)
    return operations


def update_system_alert_incident_response(
    *,
    alert_id: str,
    close_reason: str | None,
    current_store: Any,
    owner: str | None,
    postmortem: str | None,
    status: str | None,
    trace_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    from app.core.trace import envelope

    normalized_status = status.strip() if isinstance(status, str) and status.strip() else None
    if normalized_status is not None and normalized_status not in {
        "acknowledged",
        "closed",
        "ignored",
        "open",
        "resolving",
    }:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported alert status")
    normalized_close_reason = close_reason.strip() if close_reason else None
    if normalized_status in {"closed", "ignored"} and not normalized_close_reason:
        raise api_error(400, "VALIDATION_ERROR", "close_reason is required when closing alert")
    normalized_owner = owner.strip() if owner else None
    normalized_postmortem = postmortem.strip() if postmortem else None

    repository = _runtime_repository(current_store)
    update_incident = getattr(repository, "update_system_alert_incident", None)
    actor_id = str(user.get("id") or user.get("username") or "")
    existing_incident = _find_alert_incident(current_store, alert_id)
    history_event = _alert_history_event(
        actor_id=actor_id,
        close_reason=normalized_close_reason,
        existing=existing_incident,
        owner=normalized_owner,
        postmortem=normalized_postmortem,
        status=normalized_status,
    )
    if callable(update_incident):
        incident = update_incident(
            alert_id,
            close_reason=normalized_close_reason,
            history_event=history_event,
            owner=normalized_owner,
            postmortem=normalized_postmortem,
            status=normalized_status,
            actor_id=actor_id or None,
        )
    else:
        incidents = _alert_incidents_from_memory(current_store)
        incident = incidents.get(alert_id)
        if incident is not None:
            if normalized_status:
                incident["status"] = normalized_status
            if normalized_owner:
                incident["owner"] = normalized_owner
            if normalized_close_reason:
                incident["close_reason"] = normalized_close_reason
            if normalized_postmortem:
                incident["postmortem"] = normalized_postmortem
            if normalized_status in {"acknowledged", "resolving"}:
                incident.setdefault("acknowledged_at", _now_iso())
                incident.setdefault("acknowledged_by", actor_id)
            if normalized_status in {"closed", "ignored"}:
                incident["resolved_at"] = _now_iso()
                incident["resolved_by"] = actor_id
            history = _alert_incident_status_history(incident)
            history.append(history_event)
            metadata = incident.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            metadata["status_history"] = history
            incident["metadata"] = metadata
            incident["status_history"] = history
            incident["updated_at"] = _now_iso()
    if incident is None:
        raise api_error(404, "ALERT_NOT_FOUND", "System alert incident not found")
    incident = {
        **incident,
        "status_history": _alert_incident_status_history(incident),
    }
    return envelope(incident, trace_id)


def save_system_alert_subscription_response(
    *,
    channel: str,
    current_store: Any,
    enabled: bool,
    scope: str | None,
    severity_min: str,
    target: str,
    trace_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    from app.core.trace import envelope

    repository = _runtime_repository(current_store)
    new_id = getattr(repository, "next_id", None)
    subscription_id = (
        new_id("system_alert_subscription")
        if callable(new_id)
        else current_store.new_id("system_alert_subscription")
    )
    subscription = _normalize_alert_subscription(
        channel=channel,
        created_by=str(user.get("id") or ""),
        enabled=enabled,
        existing=None,
        scope=scope,
        severity_min=severity_min,
        subscription_id=subscription_id,
        target=target,
    )
    return envelope(_save_alert_subscription(current_store, subscription), trace_id)


def _normalize_alert_subscription(
    *,
    channel: str | None,
    created_by: str | None,
    enabled: bool | None,
    existing: dict[str, Any] | None,
    scope: str | None,
    severity_min: str | None,
    subscription_id: str,
    target: str | None,
) -> dict[str, Any]:
    normalized_channel = str(
        channel if channel is not None else (existing or {}).get("channel") or "",
    ).strip()
    if normalized_channel not in {"dingtalk", "email", "in_app", "webhook"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported alert subscription channel")
    normalized_severity = str(
        severity_min if severity_min is not None else (existing or {}).get("severity_min") or "medium",
    ).strip()
    if normalized_severity not in {"high", "info", "low", "medium"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported alert severity")
    normalized_target = str(
        target if target is not None else (existing or {}).get("target") or "",
    ).strip()
    if not normalized_target:
        raise api_error(400, "VALIDATION_ERROR", "target is required")
    normalized_scope = str(
        scope if scope is not None else (existing or {}).get("scope") or "global",
    ).strip() or "global"
    return {
        "channel": normalized_channel,
        "created_by": (existing or {}).get("created_by") or created_by,
        "enabled": bool(enabled if enabled is not None else (existing or {}).get("enabled", True)),
        "id": subscription_id,
        "scope": normalized_scope,
        "severity_min": normalized_severity,
        "target": normalized_target,
    }


def _save_alert_subscription(current_store: Any, subscription: dict[str, Any]) -> dict[str, Any]:
    repository = _runtime_repository(current_store)
    save_subscription = getattr(repository, "save_system_alert_subscription", None)
    if callable(save_subscription):
        return save_subscription(subscription)
    subscriptions = getattr(current_store, "system_alert_subscriptions", None)
    if not isinstance(subscriptions, dict):
        subscriptions = {}
        vars(current_store)["system_alert_subscriptions"] = subscriptions
    now = _now_iso()
    existing = subscriptions.get(str(subscription["id"])) or {}
    saved = {
        **existing,
        **subscription,
        "created_at": existing.get("created_at") or now,
        "updated_at": now,
    }
    subscriptions[str(subscription["id"])] = saved
    return dict(saved)


def update_system_alert_subscription_response(
    *,
    channel: str | None,
    current_store: Any,
    enabled: bool | None,
    scope: str | None,
    severity_min: str | None,
    subscription_id: str,
    target: str | None,
    trace_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    from app.core.trace import envelope

    existing = next(
        (
            subscription
            for subscription in _list_alert_subscriptions(current_store)
            if subscription.get("id") == subscription_id
        ),
        None,
    )
    if existing is None:
        raise api_error(
            404,
            "ALERT_SUBSCRIPTION_NOT_FOUND",
            "System alert subscription not found",
        )
    subscription = _normalize_alert_subscription(
        channel=channel,
        created_by=str(user.get("id") or ""),
        enabled=enabled,
        existing=existing,
        scope=scope,
        severity_min=severity_min,
        subscription_id=subscription_id,
        target=target,
    )
    return envelope(_save_alert_subscription(current_store, subscription), trace_id)


def _normalize_alert_rule(
    *,
    actor_id: str,
    current_store: Any,
    existing: dict[str, Any] | None,
    payload: dict[str, Any],
    rule_id: str | None = None,
) -> dict[str, Any]:
    normalized_name = str(payload.get("name", existing.get("name") if existing else "") or "").strip()
    if not normalized_name:
        raise api_error(400, "VALIDATION_ERROR", "name is required")
    normalized_source = str(
        payload.get("source", existing.get("source") if existing else "system_check") or "system_check"
    ).strip()
    normalized_severity = str(
        payload.get("severity_min", existing.get("severity_min") if existing else "medium") or "medium"
    ).strip()
    if normalized_severity not in ALERT_SEVERITY_RANK:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported alert severity")
    condition_json = payload.get(
        "condition_json",
        existing.get("condition_json") if existing else {},
    )
    if condition_json is None:
        condition_json = {}
    if not isinstance(condition_json, dict):
        raise api_error(400, "VALIDATION_ERROR", "condition_json must be an object")
    repository = _runtime_repository(current_store)
    new_id = getattr(repository, "next_id", None)
    allocated_id = (
        rule_id
        or (new_id("system_alert_rule") if callable(new_id) else current_store.new_id("system_alert_rule"))
    )
    return {
        "component": _normalize_optional_rule_text(
            payload.get("component", existing.get("component") if existing else None),
        ),
        "condition_json": condition_json,
        "created_by": existing.get("created_by") if existing else actor_id,
        "enabled": bool(payload.get("enabled", existing.get("enabled") if existing else True)),
        "id": allocated_id,
        "name": normalized_name,
        "notification_scope": _normalize_optional_rule_text(
            payload.get(
                "notification_scope",
                existing.get("notification_scope") if existing else "global",
            ),
        )
        or "global",
        "owner": _normalize_optional_rule_text(
            payload.get("owner", existing.get("owner") if existing else None),
        ),
        "severity_min": normalized_severity,
        "source": normalized_source,
        "updated_by": actor_id,
    }


def _normalize_optional_rule_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _save_alert_rule(current_store: Any, rule: dict[str, Any]) -> dict[str, Any]:
    repository = _runtime_repository(current_store)
    save_rule = getattr(repository, "save_system_alert_rule", None)
    if callable(save_rule):
        return save_rule(rule)
    rules = getattr(current_store, "system_alert_rules", None)
    if not isinstance(rules, dict):
        rules = {}
        vars(current_store)["system_alert_rules"] = rules
    now = _now_iso()
    existing = rules.get(str(rule["id"])) or {}
    saved = {
        **existing,
        **rule,
        "created_at": existing.get("created_at") or now,
        "updated_at": now,
    }
    rules[str(rule["id"])] = saved
    return dict(saved)


def save_system_alert_rule_response(
    *,
    condition_json: dict[str, Any] | None,
    component: str | None,
    current_store: Any,
    enabled: bool,
    name: str | None,
    notification_scope: str | None,
    owner: str | None,
    severity_min: str,
    source: str | None,
    trace_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    from app.core.trace import envelope

    actor_id = str(user.get("id") or user.get("username") or "")
    rule = _normalize_alert_rule(
        actor_id=actor_id,
        current_store=current_store,
        existing=None,
        payload={
            "component": component,
            "condition_json": condition_json or {},
            "enabled": enabled,
            "name": name,
            "notification_scope": notification_scope,
            "owner": owner,
            "severity_min": severity_min,
            "source": source,
        },
    )
    return envelope(_save_alert_rule(current_store, rule), trace_id)


def list_system_alert_rules_response(
    *,
    current_store: Any,
    trace_id: str,
) -> dict[str, Any]:
    from app.core.trace import envelope

    rules = _list_alert_rules(current_store)
    return envelope(
        {
            "items": rules,
            "summary": {
                "enabled_count": sum(1 for rule in rules if rule.get("enabled")),
                "total": len(rules),
            },
        },
        trace_id,
    )


def update_system_alert_rule_response(
    *,
    condition_json: dict[str, Any] | None,
    component: str | None,
    current_store: Any,
    enabled: bool | None,
    name: str | None,
    notification_scope: str | None,
    owner: str | None,
    rule_id: str,
    severity_min: str | None,
    source: str | None,
    trace_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    from app.core.trace import envelope

    existing = next((rule for rule in _list_alert_rules(current_store) if rule.get("id") == rule_id), None)
    if existing is None:
        raise api_error(404, "ALERT_RULE_NOT_FOUND", "System alert rule not found")
    actor_id = str(user.get("id") or user.get("username") or "")
    payload = {
        key: value
        for key, value in {
            "component": component,
            "condition_json": condition_json,
            "enabled": enabled,
            "name": name,
            "notification_scope": notification_scope,
            "owner": owner,
            "severity_min": severity_min,
            "source": source,
        }.items()
        if value is not None
    }
    rule = _normalize_alert_rule(
        actor_id=actor_id,
        current_store=current_store,
        existing=existing,
        payload=payload,
        rule_id=rule_id,
    )
    return envelope(_save_alert_rule(current_store, rule), trace_id)


def admin_weekly_report_response(
    *,
    current_store: Any,
    days: int,
    request: Request,
    settings: Settings,
    trace_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    from app.core.trace import envelope

    window_days = max(1, min(int(days or 7), 31))
    health = system_health_report(
        current_store=current_store,
        request=request,
        settings=settings,
        trace_id=trace_id,
        user=user,
    )
    operations = health.get("operations") or {}
    alerts = (operations.get("alert_center") or {}).get("alerts") or []
    audit_events = _items_from_store(current_store, "list_audit_events", "audit_events")
    now = datetime.now(UTC)
    recent_audit_events = [
        event
        for event in audit_events
        if (
            created_at := _parse_datetime(event.get("created_at"))
        ) is not None
        and (now - created_at).days <= window_days
    ]
    sensitive_keywords = {"auth", "config", "gateway", "permission", "role", "secret", "settings", "user"}
    sensitive_events = [
        event
        for event in recent_audit_events
        if any(keyword in str(event.get("event_type") or "").lower() for keyword in sensitive_keywords)
    ]
    high_risk_events = [
        event
        for event in recent_audit_events
        if str(event.get("result") or "").lower() in {"blocked", "failed"}
        or "delete" in str(event.get("event_type") or "").lower()
        or "admin" in str(event.get("event_type") or "").lower()
    ]
    knowledge_summary = (operations.get("knowledge_quality_loop") or {}).get("summary") or {}
    ai_summary = (operations.get("ai_executor_ops") or {}).get("summary") or {}
    alert_summary = (operations.get("alert_center") or {}).get("summary") or {}
    report_summary = {
        "alert_open_count": alert_summary.get("open_count", 0),
        "alert_closed_count": alert_summary.get("closed_count", 0),
        "audit_event_count": len(recent_audit_events),
        "high_risk_operation_count": len(high_risk_events),
        "knowledge_no_result_rate": knowledge_summary.get("no_result_rate"),
        "runner_failed_total": ai_summary.get("failed_total", 0),
        "sensitive_change_count": len(sensitive_events),
        "window_days": window_days,
    }
    markdown_lines = [
        f"# AI Brain 管理员周报（近 {window_days} 天）",
        "",
        f"- 打开告警：{report_summary['alert_open_count']}，已关闭：{report_summary['alert_closed_count']}",
        f"- 审计事件：{report_summary['audit_event_count']}，敏感配置/权限相关变更：{report_summary['sensitive_change_count']}",
        f"- 高风险或失败操作：{report_summary['high_risk_operation_count']}",
        f"- AI 执行失败/死信/超时：{report_summary['runner_failed_total']}",
        f"- 知识检索无结果率：{report_summary['knowledge_no_result_rate'] if report_summary['knowledge_no_result_rate'] is not None else '-'}",
        "",
        "## 待处理告警",
    ]
    for alert in alerts[:5]:
        markdown_lines.append(
            f"- [{alert.get('severity')}] {alert.get('title')}，负责人：{alert.get('owner') or '未分配'}，状态：{alert.get('status')}"
        )
    if not alerts:
        markdown_lines.append("- 暂无告警。")
    markdown_lines.extend(
        [
            "",
            "## 建议动作",
            "- 优先关闭 high/medium 告警，并补齐关闭原因和复盘记录。",
            "- 对敏感配置、权限和密钥引用变更进行抽查。",
            "- 关注知识无结果查询和 AI 执行失败原因分布。",
        ]
    )
    return envelope(
        {
            "generated_at": _now_iso(),
            "markdown": "\n".join(markdown_lines),
            "sections": {
                "alerts": alerts[:10],
                "high_risk_events": [
                    {
                        "created_at": event.get("created_at"),
                        "event_type": event.get("event_type"),
                        "id": event.get("id"),
                        "result": event.get("result"),
                        "subject_id": event.get("subject_id"),
                        "subject_type": event.get("subject_type"),
                    }
                    for event in high_risk_events[:10]
                ],
                "sensitive_events": [
                    {
                        "created_at": event.get("created_at"),
                        "event_type": event.get("event_type"),
                        "id": event.get("id"),
                        "subject_id": event.get("subject_id"),
                        "subject_type": event.get("subject_type"),
                    }
                    for event in sensitive_events[:10]
                ],
            },
            "summary": report_summary,
            "trace_id": trace_id,
        },
        trace_id,
    )


def system_health_report(
    *,
    current_store: Any,
    request: Request,
    settings: Settings,
    trace_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    platform_health = health_payload(
        current_store=current_store,
        settings=settings,
        trace_id=trace_id,
    )
    checks = [
        _check(
            category="基础设施",
            component="postgres",
            description="PostgreSQL 是业务事实源和 pgvector 检索基础。",
            fix_suggestion="检查 DATABASE_URL、数据库进程、网络和迁移状态。",
            key="postgres",
            status=platform_health.get("postgres", "error"),
            title="PostgreSQL",
        ),
        _check(
            category="基础设施",
            component="redis",
            description="Redis 用于缓存、队列或运行时协调能力。",
            fix_suggestion="检查 REDIS_URL、Redis 进程和网络访问。",
            key="redis",
            status=platform_health.get("redis", "error"),
            title="Redis",
        ),
        _pgvector_check(current_store, settings),
        _object_storage_check(settings),
        _smtp_check(current_store),
        _dingtalk_login_check(settings),
        _dingtalk_mcp_check(current_store),
        _model_gateway_check(current_store, settings, platform_health),
        _knowledge_quality_check(current_store, request=request, user=user),
        _ai_executor_check(current_store),
        _scheduled_jobs_check(current_store),
        _observability_check(current_store),
        _product_onboarding_check(current_store),
    ]
    status_counts: dict[str, int] = {}
    category_counts: dict[str, dict[str, int]] = {}
    for check in checks:
        status = str(check.get("status") or "unknown")
        category = str(check.get("category") or "未分类")
        status_counts[status] = status_counts.get(status, 0) + 1
        category_counts.setdefault(category, {})
        category_counts[category][status] = category_counts[category].get(status, 0) + 1
    critical_checks = [
        check for check in checks if _status_rank(str(check.get("status"))) >= 2
    ]
    operations = _operations_snapshot(
        checks=checks,
        current_store=current_store,
        request=request,
        settings=settings,
    )
    return {
        "checked_at": _now_iso(),
        "checks": checks,
        "operations": operations,
        "overall_status": _overall_status(checks),
        "platform": platform_health,
        "recommendations": [
            {
                "action_href": check.get("action_href"),
                "component": check["component"],
                "message": check["fix_suggestion"],
                "severity": "high" if _status_rank(str(check.get("status"))) >= 3 else "medium",
                "title": check["title"],
            }
            for check in critical_checks[:6]
        ],
        "summary": {
            "category_counts": category_counts,
            "critical_count": sum(
                1 for check in checks if _status_rank(str(check.get("status"))) >= 3
            ),
            "needs_attention_count": len(critical_checks),
            "ok_count": sum(1 for check in checks if _status_rank(str(check.get("status"))) == 0),
            "status_counts": status_counts,
            "total": len(checks),
        },
        "trace_id": trace_id,
    }
