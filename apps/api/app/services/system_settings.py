from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _runtime_repository(current_store: Any) -> Any | None:
    return getattr(current_store, "repository", None)


def _settings_repository(current_store: Any) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    if all(
        callable(getattr(repository, method_name, None))
        for method_name in ("get_system_settings", "upsert_system_settings")
    ):
        return repository
    return None


def _memory_settings(current_store: Any) -> dict[str, Any]:
    settings = getattr(current_store, "system_settings", None)
    if not isinstance(settings, dict):
        settings = {}
        current_store.system_settings = settings
    return settings


def _memory_audit_events(current_store: Any) -> list[dict[str, Any]]:
    audit_events = getattr(current_store, "audit_events", None)
    if not isinstance(audit_events, list):
        audit_events = []
        current_store.audit_events = audit_events
    return audit_events


def _normalize_admin_email(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if not EMAIL_RE.match(text):
        raise api_error(400, "VALIDATION_ERROR", "admin_email must be a valid email address")
    return text


def _public_settings(settings: dict[str, Any]) -> dict[str, Any]:
    admin_email = settings.get("admin_email")
    return {
        "admin_email": admin_email,
        "admin_email_configured": bool(admin_email),
        "updated_at": settings.get("updated_at"),
        "updated_by": settings.get("updated_by"),
    }


def system_settings_response(current_store: Any) -> dict[str, Any]:
    repository = _settings_repository(current_store)
    if repository is not None:
        return _public_settings(repository.get_system_settings())
    return _public_settings(_memory_settings(current_store))


def update_system_settings_response(
    current_store: Any,
    *,
    actor_id: str,
    admin_email: str | None,
    trace_id: str,
) -> dict[str, Any]:
    normalized_email = _normalize_admin_email(admin_email)
    audit_event = {
        "id": current_store.new_id("audit"),
        "event_type": "system.settings.updated",
        "actor_id": actor_id,
        "ai_task_id": None,
        "subject_type": "system_settings",
        "subject_id": "global",
        "payload": {
            "admin_email_configured": bool(normalized_email),
            "changed_fields": ["admin_email"],
        },
        "sequence": len(_memory_audit_events(current_store)) + 1,
        "trace_id": trace_id,
        "created_at": _now_iso(),
    }
    repository = _settings_repository(current_store)
    if repository is not None:
        return _public_settings(
            repository.upsert_system_settings(
                {"admin_email": normalized_email},
                actor_id=actor_id,
                audit_event=audit_event,
            )
        )
    now = _now_iso()
    settings = _memory_settings(current_store)
    settings.update(
        {
            "admin_email": normalized_email,
            "updated_at": now,
            "updated_by": actor_id,
        }
    )
    _memory_audit_events(current_store).append(audit_event)
    return _public_settings(settings)
