from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse

from app.services.operational_records import (
    read_memory_dict,
    read_memory_records,
    record_audit_event,
)

EXTERNAL_EVENT_ACTOR = {
    "id": "external_event_worker",
    "roles": ["admin"],
    "permissions": ["bug.manage", "devops.read", "insight.read", "system.admin"],
}


def _repository_identity(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("git@") and ":" in text:
        host, path = text.removeprefix("git@").split(":", 1)
        normalized = f"{host}/{path}"
    else:
        parsed = urlparse(text)
        normalized = f"{parsed.netloc}{parsed.path}" if parsed.netloc else parsed.path
    return normalized.lower().strip().strip("/").removesuffix(".git")


def _event_repository_identities(payload: dict[str, Any]) -> set[str]:
    repository = payload.get("repository") if isinstance(payload.get("repository"), dict) else {}
    project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
    values = {
        repository.get("clone_url"),
        repository.get("git_url"),
        repository.get("html_url"),
        repository.get("full_name"),
        project.get("git_http_url"),
        project.get("git_ssh_url"),
        project.get("path_with_namespace"),
        project.get("web_url"),
    }
    return {identity for value in values if (identity := _repository_identity(value))}


def _product_repositories(current_store: Any) -> list[dict[str, Any]]:
    items = read_memory_records(current_store, "product_git_repositories")
    if items:
        return items
    repository = getattr(current_store, "repository", None)
    list_products = getattr(repository, "list_products", None)
    list_repositories = getattr(repository, "list_product_git_repositories", None)
    if not callable(list_products) or not callable(list_repositories):
        return []
    results: list[dict[str, Any]] = []
    for product in list_products(active_only=True):
        results.extend(list_repositories(str(product["id"]), active_only=True))
    return results


def map_external_event_product(
    current_store: Any,
    *,
    payload: dict[str, Any],
    provider: str,
) -> tuple[str | None, str | None]:
    identities = _event_repository_identities(payload)
    if not identities:
        explicit_product_id = str(payload.get("product_id") or "").strip()
        return (explicit_product_id or None, None)
    for repository in _product_repositories(current_store):
        if repository.get("status", "active") != "active":
            continue
        if str(repository.get("git_provider") or "") != provider:
            continue
        configured = {
            _repository_identity(repository.get("remote_url")),
            _repository_identity(repository.get("project_path")),
        }
        if identities.intersection(configured - {""}):
            return str(repository.get("product_id") or "") or None, str(repository["id"])
    return None, None


def _quality_gate_bundle(
    current_store: Any,
    run_id: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    run = read_memory_dict(current_store, "quality_gate_runs").get(run_id)
    checks = [
        item
        for item in read_memory_records(current_store, "quality_gate_checks")
        if item.get("quality_gate_run_id") == run_id
    ]
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_quality_gate_runs", None)
    list_checks = getattr(repository, "list_quality_gate_checks", None)
    if run is None and callable(list_runs):
        run = next(
            (
                item
                for item in list_runs(subject_id=None, subject_type=None)
                if item.get("id") == run_id
            ),
            None,
        )
    if not checks and run is not None and callable(list_checks):
        checks = list(list_checks(run_id))
    return dict(run) if run else None, [dict(item) for item in checks]


def _save_quality_gate_bundle(
    current_store: Any,
    *,
    audit_event: dict[str, Any],
    checks: list[dict[str, Any]],
    run: dict[str, Any],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_bundle = getattr(repository, "save_quality_gate_bundle_record", None)
    if callable(save_bundle):
        save_bundle(audit_events=[audit_event], checks=checks, run=run)
    read_memory_dict(current_store, "quality_gate_runs")[run["id"]] = run
    check_store = read_memory_dict(current_store, "quality_gate_checks")
    for check in checks:
        check_store[check["id"]] = check


def _ci_payload(payload: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    workflow = payload.get("workflow_run") if isinstance(payload.get("workflow_run"), dict) else {}
    pipeline = (
        payload.get("object_attributes")
        if isinstance(payload.get("object_attributes"), dict)
        else {}
    )
    conclusion = str(
        workflow.get("conclusion")
        or pipeline.get("status")
        or payload.get("status")
        or ""
    ).lower()
    commit_sha = str(
        workflow.get("head_sha")
        or pipeline.get("sha")
        or payload.get("commit_sha")
        or ""
    ).strip()
    evidence_url = str(
        workflow.get("html_url")
        or pipeline.get("url")
        or payload.get("details_url")
        or ""
    ).strip()
    return conclusion or None, commit_sha or None, evidence_url or None


def project_git_ci_event(
    current_store: Any,
    *,
    event: dict[str, Any],
    product_id: str,
) -> tuple[str, str | None]:
    payload = dict(event.get("payload") or {})
    run_id = str(
        payload.get("quality_gate_run_id")
        or (payload.get("ai_brain") or {}).get("quality_gate_run_id")
        or ""
    ).strip()
    if not run_id:
        return "completed", None
    run, checks = _quality_gate_bundle(current_store, run_id)
    if run is None or str(run.get("product_id") or "") != product_id:
        return "ignored", "QUALITY_GATE_NOT_MAPPED"
    conclusion, commit_sha, evidence_url = _ci_payload(payload)
    passed = conclusion in {"passed", "success", "succeeded"}
    failed = conclusion in {"cancelled", "canceled", "error", "failed", "failure", "timed_out"}
    status = "passed" if passed else "failed" if failed else "pending"
    now = datetime.now(UTC).isoformat()
    check = next((item for item in checks if item.get("check_type") == "ci_status"), None)
    if check is None:
        check = {
            "id": current_store.new_id("quality_gate_check"),
            "quality_gate_run_id": run_id,
            "check_type": "ci_status",
            "source": "ci_webhook",
            "required": True,
            "independent": True,
            "created_at": now,
        }
        checks.append(check)
    check.update(
        {
            "details": {
                "commit_sha": commit_sha,
                "conclusion": conclusion,
                "evidence_url": evidence_url,
                "repository_id": (payload.get("_context") or {}).get("repository_id"),
            },
            "evidence_ref": f"{event['provider']}:{event['delivery_id']}",
            "finished_at": now if status != "pending" else None,
            "source": "ci_webhook",
            "status": status,
            "summary": f"CI status: {conclusion or 'pending'}",
            "updated_at": now,
        }
    )
    required = [item for item in checks if bool(item.get("required", True))]
    required_statuses = {str(item.get("status") or "pending") for item in required}
    run_status = (
        "failed"
        if "failed" in required_statuses
        else "passed" if required and required_statuses == {"passed"} else "running"
    )
    run.update(
        {
            "finished_at": now if run_status in {"failed", "passed"} else None,
            "independent_evidence_count": sum(
                1
                for item in checks
                if item.get("independent") and item.get("status") == "passed"
            ),
            "status": run_status,
            "summary": f"CI webhook evidence: {conclusion or 'pending'}",
            "updated_at": now,
        }
    )
    audit = record_audit_event(
        current_store,
        event_type="quality_gate.ci_evidence_recorded",
        actor_id="external-event-worker",
        subject_type="quality_gate_run",
        subject_id=run_id,
        payload={
            "delivery_id": event["delivery_id"],
            "provider": event["provider"],
            "status": status,
        },
    )
    _save_quality_gate_bundle(
        current_store,
        audit_event=audit,
        checks=checks,
        run=run,
    )
    return "completed", None


def _trusted_event_context(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    context = payload.get("_context") if isinstance(payload.get("_context"), dict) else {}
    return dict(context)


def _project_operational_metric(
    current_store: Any,
    *,
    event: dict[str, Any],
) -> tuple[str, str | None]:
    from app.services.operational_online_logs import create_online_log_metric_response

    payload = dict(event.get("payload") or {})
    context = _trusted_event_context(event)
    product_id = str(context.get("product_id") or "").strip()
    if not product_id:
        return "ignored", "CONNECTION_PRODUCT_NOT_CONFIGURED"
    request_count = max(0, int(payload.get("request_count") or 0))
    error_count = max(0, min(request_count, int(payload.get("error_count") or 0)))
    create_online_log_metric_response(
        current_store=current_store,
        payload=SimpleNamespace(
            anomaly_summary=payload.get("anomaly_summary"),
            core_event_count=max(0, int(payload.get("core_event_count") or 0)),
            environment=str(context.get("environment") or "prod"),
            error_count=error_count,
            module_code=payload.get("module_code"),
            p95_latency_ms=payload.get("p95_latency_ms"),
            p99_latency_ms=payload.get("p99_latency_ms"),
            product_id=product_id,
            request_count=request_count,
            source_channel=f"{event['provider']}_webhook",
            status="collected",
            top_errors=payload.get("top_errors") or [],
            window_end=payload.get("window_end"),
            window_start=payload.get("window_start"),
        ),
        user=EXTERNAL_EVENT_ACTOR,
    )
    return "completed", None


def _project_user_behavior(
    current_store: Any,
    *,
    event: dict[str, Any],
) -> tuple[str, str | None]:
    from app.services.user_usage_metrics import create_usage_metric_response

    payload = dict(event.get("payload") or {})
    context = _trusted_event_context(event)
    product_id = str(context.get("product_id") or "").strip()
    if not product_id:
        return "ignored", "CONNECTION_PRODUCT_NOT_CONFIGURED"
    event_count = max(0, int(payload.get("event_count") or 0))
    conversion_count = max(0, int(payload.get("conversion_count") or 0))
    conversion_rate = (
        conversion_count / event_count if event_count else None
    )
    create_usage_metric_response(
        current_store=current_store,
        payload=SimpleNamespace(
            active_users=max(0, int(payload.get("active_users") or 0)),
            avg_duration_seconds=payload.get("avg_duration_seconds"),
            bounce_rate=payload.get("bounce_rate"),
            conversion_count=conversion_count,
            conversion_rate=payload.get("conversion_rate", conversion_rate),
            error_count=max(0, int(payload.get("error_count") or 0)),
            event_count=event_count,
            feature_code=str(payload.get("feature_code") or "external_event"),
            module_code=payload.get("module_code"),
            product_id=product_id,
            source_channel="user_behavior_webhook",
            user_segment=str(payload.get("user_segment") or "all"),
            window_end=payload.get("window_end"),
            window_start=payload.get("window_start"),
        ),
        user=EXTERNAL_EVENT_ACTOR,
    )
    return "completed", None


def _project_sentry_issue(
    current_store: Any,
    *,
    event: dict[str, Any],
) -> tuple[str, str | None]:
    from app.services.bugs import save_bug_record

    payload = dict(event.get("payload") or {})
    context = _trusted_event_context(event)
    product_id = str(context.get("product_id") or "").strip()
    version_id = str(context.get("version_id") or "").strip()
    if not product_id or not version_id:
        return "ignored", "CONNECTION_PRODUCT_VERSION_NOT_CONFIGURED"
    issue = payload.get("issue") if isinstance(payload.get("issue"), dict) else payload
    title = str(issue.get("title") or "未命名异常").strip()
    level = str(issue.get("level") or "error").lower()
    severity = "critical" if level in {"fatal", "critical"} else "major"
    now = datetime.now(UTC).isoformat()
    bug = {
        "id": current_store.new_id("bug"),
        "title": f"Sentry：{title}",
        "description": str(issue.get("culprit") or title),
        "product_id": product_id,
        "version_id": version_id,
        "module_code": issue.get("module_code"),
        "severity": severity,
        "status": "open",
        "source": "sentry",
        "reproduce_steps": ["查看 Sentry 事件证据", "按堆栈和发布版本复现"],
        "evidence": {
            "delivery_id": event["delivery_id"],
            "event_id": issue.get("id"),
            "level": level,
            "provider": "sentry",
            "url": issue.get("web_url") or issue.get("permalink"),
        },
        "created_by": EXTERNAL_EVENT_ACTOR["id"],
        "created_at": now,
        "updated_at": now,
    }
    if bug["module_code"] is None:
        bug.pop("module_code")
    audit = record_audit_event(
        current_store,
        event_type="bug.created",
        actor_id=EXTERNAL_EVENT_ACTOR["id"],
        subject_type="bug",
        subject_id=bug["id"],
        payload={"delivery_id": event["delivery_id"], "source": "sentry"},
    )
    save_bug_record(current_store, bug, audit_event=audit)
    return "completed", None


def _project_jenkins_callback(
    current_store: Any,
    *,
    event: dict[str, Any],
) -> tuple[str, str | None]:
    from app.services.operational_deployments import sync_deployment_runner_task

    payload = dict(event.get("payload") or {})
    context = _trusted_event_context(event)
    deployment_request_id = str(payload.get("deployment_request_id") or "").strip()
    deployment_run_id = str(payload.get("deployment_run_id") or "").strip()
    deployment = read_memory_dict(current_store, "deployment_requests").get(
        deployment_request_id
    )
    run = read_memory_dict(current_store, "deployment_runs").get(deployment_run_id)
    if deployment is None or run is None:
        return "ignored", "DEPLOYMENT_RUN_NOT_MAPPED"
    configured_product_id = str(context.get("product_id") or "").strip()
    if configured_product_id and configured_product_id != str(deployment.get("product_id")):
        return "ignored", "CONNECTION_PRODUCT_SCOPE_MISMATCH"
    reported_status = str(payload.get("status") or "").upper()
    task_status = {
        "ABORTED": "cancelled",
        "CANCELED": "cancelled",
        "CANCELLED": "cancelled",
        "FAILURE": "failed",
        "FAILED": "failed",
        "RUNNING": "running",
        "STARTED": "running",
        "SUCCESS": "succeeded",
        "SUCCEEDED": "succeeded",
        "UNSTABLE": "failed",
    }.get(reported_status)
    if task_status is None:
        return "ignored", "JENKINS_STATUS_UNSUPPORTED"
    now = datetime.now(UTC).isoformat()
    sync_deployment_runner_task(
        current_store=current_store,
        runner_id=f"webhook:{event['provider']}",
        task={
            "id": f"external:{event['id']}",
            "deployment_run_id": deployment_run_id,
            "status": task_status,
            "error_message": None
            if task_status == "succeeded"
            else str(payload.get("failure_reason") or reported_status),
            "finished_at": now
            if task_status in {"cancelled", "failed", "succeeded"}
            else None,
            "logs": [
                {
                    "level": "info" if task_status == "succeeded" else "error",
                    "message": f"Jenkins callback status: {reported_status}",
                    "timestamp": now,
                }
            ],
            "preserve_runner_task_id": True,
            "result_json": {
                "build_url": payload.get("build_url"),
                "health_status": "passed"
                if task_status == "succeeded"
                else "failed"
                if task_status in {"cancelled", "failed"}
                else "pending",
                "operation": run.get("operation") or "deploy",
            },
        },
    )
    return "completed", None


def project_external_event(
    current_store: Any,
    *,
    event: dict[str, Any],
) -> tuple[str, str | None]:
    provider = str(event.get("provider") or "")
    payload = dict(event.get("payload") or {})
    if provider in {"github", "gitlab"}:
        product_id, repository_id = map_external_event_product(
            current_store,
            payload=payload,
            provider=provider,
        )
        if not product_id:
            return "ignored", "PRODUCT_REPOSITORY_NOT_MAPPED"
        payload["_context"] = {
            **dict(payload.get("_context") or {}),
            "product_id": product_id,
            "repository_id": repository_id,
        }
        event["payload"] = payload
        ai_brain = payload.get("ai_brain") if isinstance(payload.get("ai_brain"), dict) else {}
        if str(ai_brain.get("rd_delivery_id") or "").strip():
            from app.services.rd_git_delivery import (
                reconcile_version_git_delivery_from_provider_callback,
            )

            reconcile_version_git_delivery_from_provider_callback(
                current_store,
                inbox_event=event,
            )
            return "completed", None
        return project_git_ci_event(
            current_store,
            event=event,
            product_id=product_id,
        )
    if provider in {"opentelemetry", "prometheus"}:
        return _project_operational_metric(current_store, event=event)
    if provider == "sentry":
        return _project_sentry_issue(current_store, event=event)
    if provider == "user_behavior":
        return _project_user_behavior(current_store, event=event)
    if provider == "jenkins":
        return _project_jenkins_callback(current_store, event=event)
    return "ignored", "EVENT_PROVIDER_NOT_SUPPORTED"
