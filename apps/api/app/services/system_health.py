from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Request

from app.api.deps import api_error
from app.core.config import Settings
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


def _product_plugin_counts(current_store: Any) -> dict[str, int]:
    connections = _items_from_store(current_store, "list_plugin_connections", "plugin_connections")
    counts: dict[str, int] = {}
    for connection in connections:
        if str(connection.get("status") or "").lower() not in {"active", "enabled"}:
            continue
        for product_id in _connection_product_ids(connection):
            counts[product_id] = counts.get(product_id, 0) + 1
    return counts


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
    plugin_counts = _product_plugin_counts(current_store)
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
        plugin_connection_count = plugin_counts.get(product_id, 0)
        permission_scope_count = (
            permission_scope_counts.get(product_id, 0) + permission_scope_counts.get("*", 0)
        )

        score = 0
        missing_items: list[str] = []
        if product.get("name") and product.get("status") == "active":
            score += 15
        else:
            missing_items.append("产品主数据未启用或缺名称")
        if active_versions:
            score += 15
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
        if product_documents:
            score += 15
        else:
            missing_items.append("知识空间缺少产品文档")
        if active_related_systems:
            score += 10
        else:
            missing_items.append("未维护关联系统")
        if plugin_connection_count:
            score += 10
        else:
            missing_items.append("未绑定可用插件连接")
        if permission_scope_count:
            score += 10
        else:
            missing_items.append("未配置产品权限范围")

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
                "plugin_connection_count": plugin_connection_count,
                "product_id": product_id,
                "related_system_count": len(active_related_systems),
                "score": score,
                "recent_health_status": "healthy"
                if score >= 80
                else ("attention" if score >= 50 else "at_risk"),
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
        "latest_failures": [
            {
                "error_code": failure.get("error_code"),
                "error_message": _redact_error_summary(str(failure.get("error_message") or ""))
                if failure.get("error_message")
                else None,
                "id": failure.get("id"),
                "status": failure.get("status"),
                "updated_at": failure.get("updated_at") or failure.get("finished_at"),
            }
            for failure in latest_failures
        ],
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
        and str(document.get("index_status") or "").lower() not in {"archived", "deleted"}
    ]
    low_quality_documents = [
        document
        for document in documents
        if str(document.get("index_status") or "").lower()
        in {"index_failed", "pending_index", "importing"}
        or (
            str(document.get("index_status") or "").lower()
            in {"indexed", "text_indexed", "vector_indexed"}
            and int(document.get("chunk_count") or 0) == 0
        )
    ]
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
        "summary": {
            "active_space_count": sum(1 for item in spaces if item.get("status") == "active"),
            "citation_click_rate": citation_click_rate,
            "failed_import_job_count": len(failed_import_jobs),
            "index_failed_documents": failed_documents,
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
                "reason": "过期" if document in stale_documents else "低质量",
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
        corp_id = query.get("corp_id") or auth_config.get("corp_id")
        authorization_subjects.append(
            {
                "boundary": {
                    "app": "应用授权适合统一应用身份访问企业级资源。",
                    "system": "系统授权适合企业统一连接，由管理员集中维护和轮换。",
                    "user": "个人授权仅代表当前授权用户，适合个人空间或临时连接。",
                    "unknown": "未声明授权主体，建议补齐个人/系统/应用边界。",
                }.get(str(subject_type), "未声明授权主体，建议补齐个人/系统/应用边界。"),
                "connection_id": connection.get("id"),
                "connection_name": connection.get("name"),
                "corp_id": corp_id,
                "corp_name": settings.dingtalk_corp_name_map.get(str(corp_id or "")),
                "subject_type": subject_type,
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


def _help_screenshot_status() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[4]
    expected = [
        {
            "article": "系统健康",
            "doc_path": "docs/08-help/assets/screenshots/system-health-overview.png",
            "public_path": "apps/web/public/help/screenshots/system-health-overview.png",
            "route": "/system/health",
        },
        {
            "article": "产品接入向导",
            "doc_path": "docs/08-help/assets/screenshots/assets-products-onboarding.png",
            "public_path": "apps/web/public/help/screenshots/assets-products-onboarding.png",
            "route": "/assets/products",
        },
    ]
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
        "high_risk_confirmation": {
            "required": True,
            "controls": [
                "AI Runner 高风险指令要求平台审批",
                "系统告警关闭必须填写关闭原因",
                "敏感配置变更只记录字段和配置状态，不记录密钥值",
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
            "policy": "敏感配置变更需要系统管理员权限；正式接入审批流前，系统健康页持续暴露变更数量和高风险确认状态。",
            "required": True,
            "status": "monitored",
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
            return upsert([{**alert, "metadata": {"origin": "system_health"}} for alert in alerts])
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
            "owner": existing.get("owner") or alert.get("owner"),
            "status": existing.get("status") or "open",
            "updated_at": now,
        }
    return sorted(
        [dict(item) for item in incidents.values()],
        key=lambda item: (str(item.get("status") or ""), str(item.get("last_seen_at") or "")),
        reverse=True,
    )


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
    alerts = _persist_alert_incidents(current_store, alerts)
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
        "subscriptions": _list_alert_subscriptions(current_store),
        "summary": {
            "acknowledged_count": sum(1 for item in alerts if item.get("status") == "acknowledged"),
            "closed_count": sum(1 for item in alerts if item.get("status") == "closed"),
            "high_count": sum(1 for item in open_alerts if item.get("severity") == "high"),
            "low_count": sum(1 for item in open_alerts if item.get("severity") == "low"),
            "medium_count": sum(1 for item in open_alerts if item.get("severity") == "medium"),
            "open_count": len(open_alerts),
            "resolving_count": sum(1 for item in alerts if item.get("status") == "resolving"),
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


def _operations_snapshot(
    *,
    checks: list[dict[str, Any]],
    current_store: Any,
    request: Request,
    settings: Settings,
) -> dict[str, Any]:
    checks_by_key = {str(check.get("key") or ""): check for check in checks}
    operations = {
        "ai_executor_ops": _ai_executor_ops(current_store),
        "dingtalk_lifecycle": _dingtalk_lifecycle(
            current_store=current_store,
            request=request,
            settings=settings,
        ),
        "help_and_retention": {
            "retention_policies": _retention_policies(),
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

    repository = _runtime_repository(current_store)
    update_incident = getattr(repository, "update_system_alert_incident", None)
    actor_id = str(user.get("id") or user.get("username") or "")
    if callable(update_incident):
        incident = update_incident(
            alert_id,
            close_reason=normalized_close_reason,
            owner=owner.strip() if owner else None,
            postmortem=postmortem.strip() if postmortem else None,
            status=normalized_status,
            actor_id=actor_id or None,
        )
    else:
        incidents = _alert_incidents_from_memory(current_store)
        incident = incidents.get(alert_id)
        if incident is not None:
            if normalized_status:
                incident["status"] = normalized_status
            if owner:
                incident["owner"] = owner.strip()
            if normalized_close_reason:
                incident["close_reason"] = normalized_close_reason
            if postmortem:
                incident["postmortem"] = postmortem.strip()
            if normalized_status in {"acknowledged", "resolving"}:
                incident.setdefault("acknowledged_at", _now_iso())
                incident.setdefault("acknowledged_by", actor_id)
            if normalized_status in {"closed", "ignored"}:
                incident["resolved_at"] = _now_iso()
                incident["resolved_by"] = actor_id
            incident["updated_at"] = _now_iso()
    if incident is None:
        raise api_error(404, "ALERT_NOT_FOUND", "System alert incident not found")
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

    normalized_channel = channel.strip()
    if normalized_channel not in {"dingtalk", "email", "in_app", "webhook"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported alert subscription channel")
    normalized_severity = severity_min.strip() if severity_min else "medium"
    if normalized_severity not in {"high", "info", "low", "medium"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported alert severity")
    normalized_target = target.strip()
    if not normalized_target:
        raise api_error(400, "VALIDATION_ERROR", "target is required")
    repository = _runtime_repository(current_store)
    save_subscription = getattr(repository, "save_system_alert_subscription", None)
    new_id = getattr(repository, "next_id", None)
    subscription_id = (
        new_id("system_alert_subscription")
        if callable(new_id)
        else current_store.new_id("system_alert_subscription")
    )
    subscription = {
        "channel": normalized_channel,
        "created_by": user.get("id"),
        "enabled": enabled,
        "id": subscription_id,
        "scope": scope.strip() if scope else "global",
        "severity_min": normalized_severity,
        "target": normalized_target,
    }
    if callable(save_subscription):
        saved = save_subscription(subscription)
    else:
        subscriptions = getattr(current_store, "system_alert_subscriptions", None)
        if not isinstance(subscriptions, dict):
            subscriptions = {}
        saved = {**subscription, "created_at": _now_iso(), "updated_at": _now_iso()}
        subscriptions[subscription_id] = saved
    return envelope(saved, trace_id)


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
