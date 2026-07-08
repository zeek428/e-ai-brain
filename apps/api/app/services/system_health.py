from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from app.core.config import Settings
from app.services.knowledge_index_health import knowledge_index_health_response
from app.services.platform_status import health_payload
from app.services.product_config_context import list_product_records
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


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _status_rank(status: str) -> int:
    return HEALTH_STATUS_RANK.get(status, 2)


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
    return {
        "checked_at": _now_iso(),
        "checks": checks,
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
