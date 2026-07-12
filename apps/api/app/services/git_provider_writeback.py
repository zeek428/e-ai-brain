from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, urlopen

from app.api.deps import api_error, require_any_permission_or_roles
from app.services.external_event_signatures import resolve_webhook_secret
from app.services.operational_records import (
    read_memory_dict,
    read_memory_records,
    record_audit_event,
)
from app.services.product_scope import require_product_scope

GIT_WRITEBACK_ACTIONS = {"approve", "comment", "merge", "request_changes"}


def _required_write_permission(action: str) -> str:
    return "review" if action in {"approve", "request_changes"} else action


def _repository(current_store: Any, repository_id: str) -> dict[str, Any]:
    record = read_memory_dict(current_store, "product_git_repositories").get(repository_id)
    repository = getattr(current_store, "repository", None)
    get_record = getattr(repository, "get_product_git_repository", None)
    if record is None and callable(get_record):
        record = get_record(repository_id)
    if record is None or record.get("status", "active") != "active":
        raise api_error(404, "NOT_FOUND", "Product Git repository not found")
    return dict(record)


def _connection(current_store: Any, connection_id: str) -> dict[str, Any]:
    record = read_memory_dict(current_store, "plugin_connections").get(connection_id)
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_plugin_connections", None)
    if record is None and callable(list_records):
        record = next(
            (
                item
                for item in list_records(status="active")
                if str(item.get("id")) == connection_id
            ),
            None,
        )
    if record is None or record.get("status") != "active":
        raise api_error(404, "NOT_FOUND", "Git provider connection not found")
    return dict(record)


def _connection_provider(current_store: Any, connection: dict[str, Any]) -> str:
    code = str(connection.get("plugin_code") or "").strip()
    if code:
        return code
    plugin = read_memory_dict(current_store, "integration_plugins").get(
        str(connection.get("plugin_id") or "")
    )
    return str((plugin or {}).get("code") or "").strip()


def _quality_gate(current_store: Any, run_id: str) -> dict[str, Any] | None:
    run = read_memory_dict(current_store, "quality_gate_runs").get(run_id)
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_quality_gate_runs", None)
    if run is None and callable(list_runs):
        run = next(
            (
                item
                for item in list_runs(subject_id=None, subject_type=None)
                if item.get("id") == run_id
            ),
            None,
        )
    return dict(run) if run else None


def _require_merge_gate(
    current_store: Any,
    *,
    product_id: str,
    quality_gate_run_id: str | None,
) -> dict[str, Any]:
    run_id = str(quality_gate_run_id or "").strip()
    gate = _quality_gate(current_store, run_id) if run_id else None
    if (
        gate is None
        or str(gate.get("product_id") or "") != product_id
        or gate.get("status") != "passed"
        or gate.get("blocked_reasons")
        or int(gate.get("independent_evidence_count") or 0) < 1
        or int(gate.get("verified_attestation_count") or 0) < 1
        or not gate.get("verifier_trust_isolated")
    ):
        raise api_error(
            409,
            "GIT_WRITEBACK_GATE_BLOCKED",
            "Git merge requires a passed independent quality gate",
        )
    return gate


def _outbox_events(current_store: Any) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_events = getattr(repository, "list_execution_outbox_events", None)
    if callable(list_events):
        return list(list_events(aggregate_id=None, aggregate_type=None, status=None))
    return read_memory_records(current_store, "execution_outbox_events")


def _save_outbox_event(
    current_store: Any,
    event: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_execution_outbox_event_record", None)
    if callable(save_record):
        save_record(event, audit_event=audit_event)
    read_memory_dict(current_store, "execution_outbox_events")[event["id"]] = event


def queue_git_writeback(
    current_store: Any,
    *,
    action: str,
    connection_id: str,
    message: str,
    product_id: str,
    quality_gate_run_id: str | None,
    repository_id: str,
    subject_id: str,
    subject_type: str,
    target_number: int,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"gitlab.review"}, {"admin", "reviewer"})
    require_product_scope(user, product_id)
    if action not in GIT_WRITEBACK_ACTIONS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported Git writeback action")
    repository = _repository(current_store, repository_id)
    if str(repository.get("product_id") or "") != product_id:
        raise api_error(404, "NOT_FOUND", "Product Git repository not found")
    connection = _connection(current_store, connection_id)
    provider = _connection_provider(current_store, connection)
    if provider not in {"github", "gitlab"} or provider != repository.get("git_provider"):
        raise api_error(409, "GIT_WRITEBACK_CONNECTION_INVALID", "Git connection is invalid")
    request_config = (
        connection.get("request_config")
        if isinstance(connection.get("request_config"), dict)
        else {}
    )
    write_permissions = set(request_config.get("write_permissions") or [])
    required_permission = _required_write_permission(action)
    if required_permission not in write_permissions:
        raise api_error(
            403,
            "GIT_WRITEBACK_PERMISSION_DENIED",
            "Git connection does not allow this writeback action",
        )
    gate = (
        _require_merge_gate(
            current_store,
            product_id=product_id,
            quality_gate_run_id=quality_gate_run_id,
        )
        if action == "merge"
        else _quality_gate(current_store, str(quality_gate_run_id or ""))
    )
    idempotency_material = json.dumps(
        {
            "action": action,
            "connection_id": connection_id,
            "message": message,
            "product_id": product_id,
            "quality_gate_run_id": quality_gate_run_id,
            "repository_id": repository_id,
            "subject_id": subject_id,
            "subject_type": subject_type,
            "target_number": target_number,
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    idempotency_key = "git-writeback:" + hashlib.sha256(
        idempotency_material.encode()
    ).hexdigest()
    existing = next(
        (
            item
            for item in _outbox_events(current_store)
            if item.get("idempotency_key") == idempotency_key
        ),
        None,
    )
    if existing is not None:
        return dict(existing)
    now = datetime.now(UTC).isoformat()
    event = {
        "id": current_store.new_id("execution_outbox_event"),
        "aggregate_type": subject_type,
        "aggregate_id": subject_id,
        "event_type": "git_writeback_requested",
        "idempotency_key": idempotency_key,
        "payload": {
            "action": action,
            "connection_id": connection_id,
            "gate_snapshot": {
                "blocked_reasons": list((gate or {}).get("blocked_reasons") or []),
                "id": (gate or {}).get("id"),
                "independent_evidence_count": int(
                    (gate or {}).get("independent_evidence_count") or 0
                ),
                "status": (gate or {}).get("status"),
            },
            "message": str(message or "")[:10000],
            "permission_snapshot": {
                "actor_id": user["id"],
                "connection_write_permissions": sorted(write_permissions),
            },
            "product_id": product_id,
            "provider": provider,
            "quality_gate_run_id": quality_gate_run_id,
            "repository_id": repository_id,
            "target_number": int(target_number),
        },
        "status": "pending",
        "attempt_count": 0,
        "available_at": now,
        "lease_owner": None,
        "lease_until": None,
        "last_error": None,
        "created_at": now,
        "updated_at": now,
        "processed_at": None,
    }
    audit = record_audit_event(
        current_store,
        event_type="git.writeback_queued",
        actor_id=user["id"],
        subject_type=subject_type,
        subject_id=subject_id,
        payload={
            "action": action,
            "outbox_event_id": event["id"],
            "product_id": product_id,
            "repository_id": repository_id,
        },
    )
    _save_outbox_event(current_store, event, audit_event=audit)
    return dict(event)


def _validated_endpoint(connection: dict[str, Any], provider: str) -> str:
    endpoint = str(connection.get("endpoint_url") or "").strip()
    if not endpoint:
        endpoint = "https://api.github.com" if provider == "github" else "https://gitlab.com"
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
        raise api_error(409, "GIT_WRITEBACK_ENDPOINT_INVALID", "Git endpoint is invalid")
    return endpoint.rstrip("/") + "/"


def _provider_request(
    current_store: Any,
    *,
    event: dict[str, Any],
) -> Request:
    payload = dict(event.get("payload") or {})
    repository = _repository(current_store, str(payload.get("repository_id") or ""))
    if str(repository.get("product_id") or "") != str(payload.get("product_id") or ""):
        raise api_error(404, "NOT_FOUND", "Product Git repository not found")
    connection = _connection(current_store, str(payload.get("connection_id") or ""))
    provider = _connection_provider(current_store, connection)
    if provider != payload.get("provider") or provider != repository.get("git_provider"):
        raise api_error(409, "GIT_WRITEBACK_CONNECTION_INVALID", "Git connection is invalid")
    action = str(payload.get("action") or "")
    request_config = (
        connection.get("request_config")
        if isinstance(connection.get("request_config"), dict)
        else {}
    )
    if _required_write_permission(action) not in set(
        request_config.get("write_permissions") or []
    ):
        raise api_error(
            403,
            "GIT_WRITEBACK_PERMISSION_DENIED",
            "Git connection no longer allows this writeback action",
        )
    if action == "merge":
        _require_merge_gate(
            current_store,
            product_id=str(payload["product_id"]),
            quality_gate_run_id=str(payload.get("quality_gate_run_id") or ""),
        )
    auth_config = (
        connection.get("auth_config")
        if isinstance(connection.get("auth_config"), dict)
        else {}
    )
    token_ref = str(auth_config.get("token_ref") or auth_config.get("secret_ref") or "")
    token = resolve_webhook_secret(token_ref).decode()
    target_number = int(payload.get("target_number") or 0)
    project_path = str(repository.get("project_path") or "").strip().strip("/")
    endpoint = _validated_endpoint(connection, provider)
    message = str(payload.get("message") or "")
    if provider == "github":
        base = urljoin(endpoint, f"repos/{quote(project_path, safe='/')}/")
        if action == "comment":
            url = urljoin(base, f"issues/{target_number}/comments")
            method = "POST"
            body = {"body": message}
        elif action in {"approve", "request_changes"}:
            url = urljoin(base, f"pulls/{target_number}/reviews")
            method = "POST"
            body = {
                "body": message,
                "event": "APPROVE" if action == "approve" else "REQUEST_CHANGES",
            }
        else:
            url = urljoin(base, f"pulls/{target_number}/merge")
            method = "PUT"
            body = {"commit_title": message or "AI Brain governed merge"}
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    else:
        project = quote(str(repository.get("project_id") or project_path), safe="")
        base = urljoin(endpoint, f"api/v4/projects/{project}/merge_requests/{target_number}/")
        if action in {"comment", "request_changes"}:
            url = urljoin(base, "notes")
            method = "POST"
            body = {"body": message}
        elif action == "approve":
            url = urljoin(base, "approve")
            method = "POST"
            body = {}
        else:
            url = urljoin(base, "merge")
            method = "PUT"
            body = {"merge_commit_message": message}
        headers = {"Content-Type": "application/json", "PRIVATE-TOKEN": token}
    return Request(
        url,
        data=json.dumps(body).encode(),
        headers=headers,
        method=method,
    )


def dispatch_git_writeback_event(
    current_store: Any,
    *,
    event: dict[str, Any],
) -> dict[str, Any]:
    request = _provider_request(current_store, event=event)
    with urlopen(request, timeout=30) as response:
        status_code = int(getattr(response, "status", 200))
    if status_code >= 400:
        raise RuntimeError(f"Git writeback returned HTTP {status_code}")
    return {
        "action": (event.get("payload") or {}).get("action"),
        "provider": (event.get("payload") or {}).get("provider"),
        "status_code": status_code,
    }
