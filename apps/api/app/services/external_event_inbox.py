from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.services.external_event_projectors import project_external_event
from app.services.external_event_signatures import verify_external_event_signature
from app.services.operational_records import (
    read_memory_dict,
    read_memory_records,
    record_audit_event,
)

EXTERNAL_EVENT_MAX_BODY_BYTES = 2 * 1024 * 1024
EXTERNAL_EVENT_MAX_ATTEMPTS = 5
SUPPORTED_EXTERNAL_EVENT_PROVIDERS = {
    "github",
    "gitlab",
    "jenkins",
    "opentelemetry",
    "prometheus",
    "sentry",
    "user_behavior",
}
EXTERNAL_EVENT_STATUSES = {
    "dead_letter",
    "failed",
    "ignored",
    "pending",
    "processed",
    "processing",
}
SENSITIVE_PAYLOAD_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "cookie",
    "credentials",
    "password",
    "private_key",
    "secret",
    "token",
}


def _headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items()}


def _connection(current_store: Any, connection_id: str) -> dict[str, Any]:
    connection = read_memory_dict(current_store, "plugin_connections").get(connection_id)
    repository = getattr(current_store, "repository", None)
    list_connections = getattr(repository, "list_plugin_connections", None)
    if connection is None and callable(list_connections):
        connection = next(
            (
                item
                for item in list_connections(status="active")
                if str(item.get("id")) == connection_id
            ),
            None,
        )
    if connection is None or connection.get("status") != "active":
        raise api_error(404, "NOT_FOUND", "Webhook connection not found")
    return dict(connection)


def _connection_provider(current_store: Any, connection: dict[str, Any]) -> str:
    code = str(connection.get("plugin_code") or "").strip()
    if not code:
        plugin = read_memory_dict(current_store, "integration_plugins").get(
            str(connection.get("plugin_id") or "")
        )
        code = str((plugin or {}).get("code") or "").strip()
    if code == "observability":
        request_config = (
            connection.get("request_config")
            if isinstance(connection.get("request_config"), dict)
            else {}
        )
        event_provider = str(request_config.get("event_provider") or "").strip()
        if event_provider in {"opentelemetry", "prometheus", "sentry"}:
            return event_provider
    return code


def _event_headers(provider: str, headers: Mapping[str, str]) -> tuple[str, str]:
    normalized = _headers(headers)
    if provider == "github":
        return (
            normalized.get("x-github-delivery", ""),
            normalized.get("x-github-event", ""),
        )
    if provider == "gitlab":
        return (
            normalized.get("x-gitlab-event-uuid") or normalized.get("x-request-id", ""),
            normalized.get("x-gitlab-event", ""),
        )
    return (
        normalized.get("x-ai-brain-delivery", ""),
        normalized.get("x-ai-brain-event", ""),
    )


def _sanitize_payload(value: Any, *, key: str = "") -> Any:
    normalized_key = key.lower().replace("-", "_")
    if normalized_key in SENSITIVE_PAYLOAD_KEYS or any(
        normalized_key.endswith(f"_{suffix}") for suffix in ("password", "secret", "token")
    ):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {
            str(child_key): _sanitize_payload(child, key=str(child_key))
            for child_key, child in list(value.items())[:500]
        }
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value[:500]]
    if isinstance(value, str):
        return value[:10000]
    return value


def _callback_repository_ref(provider: str, payload: dict[str, Any]) -> str | None:
    """Return the Git ref carried by a provider callback in a stable form."""
    if provider not in {"github", "gitlab"}:
        return None
    push = payload.get("push") if isinstance(payload.get("push"), dict) else {}
    value = str(payload.get("ref") or push.get("ref") or "").strip()
    return value.removeprefix("refs/heads/") or None


def _persisted_callback_context(
    current_store: Any,
    *,
    connection_id: str,
    provider: str,
    payload: dict[str, Any],
    request_config: dict[str, Any],
) -> dict[str, Any]:
    """Bind a newly verified callback to configured product/repository facts.

    This context is written once with the signed Inbox payload.  Projectors may
    update event processing state, but must not create or alter this binding.
    """
    context: dict[str, Any] = {
        "connection_id": connection_id,
        "environment": request_config.get("environment"),
        "product_id": request_config.get("product_id"),
        "version_id": request_config.get("version_id"),
    }
    if provider in {"github", "gitlab"}:
        from app.services.external_event_projectors import map_external_event_product

        mapped_product_id, repository_id = map_external_event_product(
            current_store,
            payload=payload,
            provider=provider,
        )
        context.update(
            {
                "product_id": mapped_product_id or context.get("product_id"),
                "repository_id": repository_id,
                "repository_provider": provider if repository_id else None,
                "repository_ref": _callback_repository_ref(provider, payload),
            }
        )
    return context


def _list_events(
    current_store: Any,
    *,
    delivery_id: str | None = None,
    provider: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_external_event_inbox", None)
    if callable(list_records):
        return list(
            list_records(
                delivery_id=delivery_id,
                provider=provider,
                status=status,
            )
        )
    items = read_memory_records(current_store, "external_event_inbox")
    for field, value in (
        ("delivery_id", delivery_id),
        ("provider", provider),
        ("status", status),
    ):
        if value is not None:
            items = [item for item in items if item.get(field) == value]
    return [dict(item) for item in items]


def _save_event(
    current_store: Any,
    event: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_external_event_inbox_record", None)
    if callable(save_record):
        save_record(event, audit_event=audit_event)
    read_memory_dict(current_store, "external_event_inbox")[event["id"]] = event


def receive_external_event(
    current_store: Any,
    *,
    body: bytes,
    connection_id: str,
    headers: Mapping[str, str],
    provider: str,
) -> dict[str, Any]:
    if len(body) > EXTERNAL_EVENT_MAX_BODY_BYTES:
        raise api_error(413, "WEBHOOK_PAYLOAD_TOO_LARGE", "Webhook payload is too large")
    connection = _connection(current_store, connection_id)
    if _connection_provider(current_store, connection) != provider:
        raise api_error(404, "NOT_FOUND", "Webhook connection not found")
    delivery_id, event_type = _event_headers(provider, headers)
    if not delivery_id or not event_type:
        raise api_error(
            400,
            "WEBHOOK_HEADERS_INVALID",
            "Webhook delivery and event headers are required",
        )
    auth_config = (
        connection.get("auth_config") if isinstance(connection.get("auth_config"), dict) else {}
    )
    secret_ref = str(auth_config.get("webhook_secret_ref") or "").strip()
    signature_status = verify_external_event_signature(
        provider=provider,
        secret_ref=secret_ref,
        body=body,
        headers=headers,
    )
    payload_hash = hashlib.sha256(body).hexdigest()
    duplicate = next(
        iter(_list_events(current_store, delivery_id=delivery_id, provider=provider)),
        None,
    )
    if duplicate is not None:
        duplicate_payload = (
            duplicate.get("payload") if isinstance(duplicate.get("payload"), dict) else {}
        )
        duplicate_context = (
            duplicate_payload.get("_context")
            if isinstance(duplicate_payload.get("_context"), dict)
            else {}
        )
        if (
            duplicate.get("payload_hash") != payload_hash
            or duplicate.get("event_type") != event_type
            or duplicate_context.get("connection_id") != connection_id
        ):
            audit = record_audit_event(
                current_store,
                event_type="external_event.delivery_conflict",
                actor_id=f"webhook:{provider}",
                subject_type="external_event",
                subject_id=str(duplicate["id"]),
                payload={
                    "connection_id": connection_id,
                    "delivery_id": delivery_id,
                    "event_type": event_type,
                    "provider": provider,
                },
            )
            _save_event(current_store, duplicate, audit_event=audit)
            raise api_error(
                409,
                "WEBHOOK_DELIVERY_CONFLICT",
                "Webhook delivery id was already used for another payload",
            )
        return {**duplicate, "duplicate": True}
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise api_error(400, "WEBHOOK_PAYLOAD_INVALID", "Webhook payload must be JSON") from exc
    if not isinstance(decoded, dict):
        raise api_error(400, "WEBHOOK_PAYLOAD_INVALID", "Webhook payload must be an object")
    now = datetime.now(UTC).isoformat()
    request_config = (
        connection.get("request_config")
        if isinstance(connection.get("request_config"), dict)
        else {}
    )
    sanitized_payload = _sanitize_payload(decoded)
    event = {
        "id": current_store.new_id("external_event"),
        "provider": provider,
        "event_type": event_type,
        "delivery_id": delivery_id,
        "signature_status": signature_status,
        "payload_hash": payload_hash,
        "payload": {
            **sanitized_payload,
            "_context": _persisted_callback_context(
                current_store,
                connection_id=connection_id,
                provider=provider,
                payload=sanitized_payload,
                request_config=request_config,
            ),
        },
        "status": "pending",
        "attempt_count": 0,
        "lease_owner": None,
        "lease_until": None,
        "error_message": None,
        "received_at": now,
        "processed_at": None,
        "updated_at": now,
        "duplicate": False,
    }
    audit = record_audit_event(
        current_store,
        event_type="external_event.received",
        actor_id=f"webhook:{provider}",
        subject_type="external_event",
        subject_id=event["id"],
        payload={
            "connection_id": connection_id,
            "delivery_id": delivery_id,
            "event_type": event_type,
            "provider": provider,
        },
    )
    _save_event(current_store, event, audit_event=audit)
    return dict(event)


def _claim_events(
    current_store: Any,
    *,
    lease_seconds: int,
    limit: int,
    worker_id: str,
) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    claim = getattr(repository, "claim_external_event_inbox", None)
    if callable(claim):
        return list(claim(lease_seconds=lease_seconds, limit=limit, worker_id=worker_id))
    now = datetime.now(UTC)
    claimed: list[dict[str, Any]] = []
    for event in sorted(
        read_memory_records(current_store, "external_event_inbox"),
        key=lambda item: str(item.get("received_at") or ""),
    ):
        if event.get("status") not in {"pending", "failed", "processing"}:
            continue
        lease_until = event.get("lease_until")
        if lease_until:
            try:
                if datetime.fromisoformat(str(lease_until)) > now:
                    continue
            except ValueError:
                pass
        event.update(
            {
                "attempt_count": int(event.get("attempt_count") or 0) + 1,
                "lease_owner": worker_id,
                "lease_until": (now + timedelta(seconds=lease_seconds)).isoformat(),
                "status": "processing",
                "updated_at": now.isoformat(),
            }
        )
        claimed.append(dict(event))
        if len(claimed) >= limit:
            break
    return claimed


def process_external_event_inbox_events(
    current_store: Any,
    *,
    lease_seconds: int = 30,
    limit: int = 20,
    worker_id: str,
) -> int:
    processed = 0
    for event in _claim_events(
        current_store,
        lease_seconds=lease_seconds,
        limit=limit,
        worker_id=worker_id,
    ):
        try:
            status, error_message = project_external_event(
                current_store,
                event=event,
            )
            now = datetime.now(UTC).isoformat()
            event.update(
                {
                    "error_message": error_message,
                    "lease_owner": None,
                    "lease_until": None,
                    "processed_at": now,
                    "status": status,
                    "updated_at": now,
                }
            )
            audit = record_audit_event(
                current_store,
                event_type=f"external_event.{status}",
                actor_id=worker_id,
                subject_type="external_event",
                subject_id=event["id"],
                payload={"error_code": error_message},
            )
            _save_event(current_store, event, audit_event=audit)
            processed += 1
        except Exception as exc:  # noqa: BLE001 - Inbox retries isolate projector failures.
            now = datetime.now(UTC).isoformat()
            attempts = int(event.get("attempt_count") or 1)
            event.update(
                {
                    "error_message": type(exc).__name__,
                    "lease_owner": None,
                    "lease_until": None,
                    "processed_at": now if attempts >= EXTERNAL_EVENT_MAX_ATTEMPTS else None,
                    "status": "dead_letter"
                    if attempts >= EXTERNAL_EVENT_MAX_ATTEMPTS
                    else "failed",
                    "updated_at": now,
                }
            )
            _save_event(current_store, event)
    return processed


def _require_external_event_operations_access(user: dict[str, Any]) -> None:
    require_any_permission_or_roles(
        user,
        {"audit.read", "system.health.read", "system.plugins.manage"},
        {"admin"},
    )


def _public_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    context = payload.get("_context") if isinstance(payload.get("_context"), dict) else {}
    return {key: value for key, value in event.items() if key not in {"payload", "lease_owner"}} | {
        "context": dict(context)
    }


def list_external_events_response(
    *,
    current_store: Any,
    event_type: str | None,
    page: int,
    page_size: int,
    provider: str | None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    _require_external_event_operations_access(user)
    if provider is not None and provider not in SUPPORTED_EXTERNAL_EVENT_PROVIDERS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported external event provider")
    if status is not None and status not in EXTERNAL_EVENT_STATUSES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported external event status")
    items = _list_events(current_store, provider=provider, status=status)
    if event_type:
        items = [item for item in items if item.get("event_type") == event_type]
    items.sort(
        key=lambda item: (
            str(item.get("received_at") or ""),
            str(item.get("id") or ""),
        ),
        reverse=True,
    )
    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": [_public_event(item) for item in items[start : start + page_size]],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def retry_external_event_response(
    *,
    current_store: Any,
    event_id: str,
    reason: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    _require_external_event_operations_access(user)
    event = next(
        (item for item in _list_events(current_store) if item.get("id") == event_id),
        None,
    )
    if event is None:
        raise api_error(404, "NOT_FOUND", "External event not found")
    if event.get("status") not in {"dead_letter", "failed"}:
        raise api_error(
            409,
            "EXTERNAL_EVENT_RETRY_INVALID",
            "Only failed or dead-letter events can be retried",
        )
    previous_status = str(event.get("status") or "")
    previous_attempt_count = int(event.get("attempt_count") or 0)
    now = datetime.now(UTC).isoformat()
    event.update(
        {
            "attempt_count": 0,
            "error_message": None,
            "lease_owner": None,
            "lease_until": None,
            "processed_at": None,
            "status": "pending",
            "updated_at": now,
        }
    )
    audit = record_audit_event(
        current_store,
        event_type="external_event.retry_requested",
        actor_id=user["id"],
        subject_type="external_event",
        subject_id=event_id,
        payload={
            "previous_attempt_count": previous_attempt_count,
            "previous_status": previous_status,
            "reason": str(reason or "").strip() or None,
        },
    )
    _save_event(current_store, event, audit_event=audit)
    return _public_event(event)
