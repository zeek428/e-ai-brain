from __future__ import annotations

import os
import re
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any

from app.api.deps import api_error

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SMTP_TLS_OPTIONS = {"none", "ssl", "starttls"}
SMTP_TEST_TIMEOUT_SECONDS = 15


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
    settings = getattr(current_store, "_system_settings", None)
    if not isinstance(settings, dict):
        settings = getattr(current_store, "system_settings", None)
    if not isinstance(settings, dict):
        settings = {}
        vars(current_store)["_system_settings"] = settings
    return settings


def _memory_audit_events(current_store: Any) -> list[dict[str, Any]]:
    audit_events = getattr(current_store, "_system_settings_audit_events", None)
    if not isinstance(audit_events, list):
        audit_events = getattr(current_store, "audit_events", None)
    if not isinstance(audit_events, list):
        audit_events = []
        vars(current_store)["_system_settings_audit_events"] = audit_events
    return audit_events


def _normalize_admin_email(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if not EMAIL_RE.match(text):
        raise api_error(400, "VALIDATION_ERROR", "admin_email must be a valid email address")
    return text


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_optional_email(value: Any, field_name: str) -> str | None:
    text = _normalize_optional_text(value)
    if text is None:
        return None
    if not EMAIL_RE.match(text):
        raise api_error(400, "VALIDATION_ERROR", f"{field_name} must be a valid email address")
    return text


def _normalize_smtp_port(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise api_error(400, "VALIDATION_ERROR", "smtp_port must be a valid port") from exc
    if port < 1 or port > 65535:
        raise api_error(400, "VALIDATION_ERROR", "smtp_port must be between 1 and 65535")
    return port


def _normalize_email_delivery(
    value: dict[str, Any] | None,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    normalized = {
        "default_from": _normalize_optional_email(
            raw.get("default_from", previous.get("default_from")),
            "default_from",
        ),
        "enabled": bool(raw.get("enabled", previous.get("enabled", False))),
        "reply_to": _normalize_optional_email(
            raw.get("reply_to", previous.get("reply_to")),
            "reply_to",
        ),
        "sender_email": _normalize_optional_email(
            raw.get("sender_email", previous.get("sender_email")),
            "sender_email",
        ),
        "smtp_host": _normalize_optional_text(raw.get("smtp_host", previous.get("smtp_host"))),
        "smtp_password": _normalize_optional_text(
            raw.get("smtp_password", previous.get("smtp_password")),
        ),
        "smtp_port": _normalize_smtp_port(raw.get("smtp_port", previous.get("smtp_port"))),
        "smtp_secret_ref": _normalize_optional_text(
            raw.get("smtp_secret_ref", previous.get("smtp_secret_ref")),
        ),
        "smtp_tls": str(raw.get("smtp_tls", previous.get("smtp_tls") or "starttls")).strip(),
        "smtp_username": _normalize_optional_text(
            raw.get("smtp_username", previous.get("smtp_username")),
        ),
    }
    if normalized["default_from"] is None and normalized["sender_email"]:
        normalized["default_from"] = normalized["sender_email"]
    if normalized["smtp_tls"] not in SMTP_TLS_OPTIONS:
        raise api_error(400, "VALIDATION_ERROR", "smtp_tls must be one of none, ssl, starttls")
    if normalized["enabled"]:
        required_fields = {
            "default_from": normalized["default_from"],
            "sender_email": normalized["sender_email"],
            "smtp_host": normalized["smtp_host"],
            "smtp_port": normalized["smtp_port"],
            "smtp_tls": normalized["smtp_tls"],
            "smtp_username": normalized["smtp_username"],
        }
        missing = [key for key, field_value in required_fields.items() if field_value in (None, "")]
        if missing:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                f"email_delivery missing required fields: {', '.join(missing)}",
            )
        if not normalized["smtp_password"] and not normalized["smtp_secret_ref"]:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                "email_delivery requires smtp_password or smtp_secret_ref",
            )
    return normalized


def _public_email_delivery(settings: dict[str, Any]) -> dict[str, Any] | None:
    delivery = settings.get("email_delivery")
    if not isinstance(delivery, dict):
        return None
    return {
        "default_from": delivery.get("default_from"),
        "enabled": bool(delivery.get("enabled")),
        "reply_to": delivery.get("reply_to"),
        "sender_email": delivery.get("sender_email"),
        "smtp_host": delivery.get("smtp_host"),
        "smtp_password_configured": bool(delivery.get("smtp_password")),
        "smtp_port": delivery.get("smtp_port"),
        "smtp_secret_ref": delivery.get("smtp_secret_ref"),
        "smtp_secret_ref_configured": bool(delivery.get("smtp_secret_ref")),
        "smtp_tls": delivery.get("smtp_tls") or "starttls",
        "smtp_username": delivery.get("smtp_username"),
    }


def _email_delivery_configured(settings: dict[str, Any]) -> bool:
    delivery = settings.get("email_delivery")
    if not isinstance(delivery, dict) or not delivery.get("enabled"):
        return False
    return bool(
        delivery.get("default_from")
        and delivery.get("sender_email")
        and delivery.get("smtp_host")
        and delivery.get("smtp_port")
        and delivery.get("smtp_tls")
        and delivery.get("smtp_username")
        and (delivery.get("smtp_password") or delivery.get("smtp_secret_ref"))
    )


def _public_settings(settings: dict[str, Any]) -> dict[str, Any]:
    admin_email = settings.get("admin_email")
    return {
        "admin_email": admin_email,
        "admin_email_configured": bool(admin_email),
        "email_delivery": _public_email_delivery(settings),
        "email_delivery_configured": _email_delivery_configured(settings),
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
    admin_email_provided: bool = True,
    email_delivery: dict[str, Any] | None = None,
    email_delivery_provided: bool = False,
    trace_id: str,
) -> dict[str, Any]:
    repository = _settings_repository(current_store)
    existing_settings = (
        repository.get_system_settings()
        if repository is not None
        else dict(_memory_settings(current_store))
    )
    normalized_email = (
        _normalize_admin_email(admin_email)
        if admin_email_provided
        else existing_settings.get("admin_email")
    )
    normalized_delivery = (
        _normalize_email_delivery(
            email_delivery,
            existing=existing_settings.get("email_delivery"),
        )
        if email_delivery_provided
        else existing_settings.get("email_delivery")
    )
    next_settings = {
        "admin_email": normalized_email,
        "email_delivery": normalized_delivery,
    }
    changed_fields = []
    if admin_email_provided:
        changed_fields.append("admin_email")
    if email_delivery_provided:
        changed_fields.append("email_delivery")
    audit_payload = {
        "admin_email_configured": bool(normalized_email),
        "changed_fields": changed_fields,
    }
    if email_delivery_provided:
        audit_payload.update(
            {
                "email_delivery_configured": _email_delivery_configured(next_settings),
                "smtp_password_configured": bool((normalized_delivery or {}).get("smtp_password")),
                "smtp_secret_ref_configured": bool(
                    (normalized_delivery or {}).get("smtp_secret_ref"),
                ),
            }
        )
    audit_event = {
        "id": current_store.new_id("audit"),
        "event_type": "system.settings.updated",
        "actor_id": actor_id,
        "ai_task_id": None,
        "subject_type": "system_settings",
        "subject_id": "global",
        "payload": audit_payload,
        "sequence": len(_memory_audit_events(current_store)) + 1,
        "trace_id": trace_id,
        "created_at": _now_iso(),
    }
    if repository is not None:
        return _public_settings(
            repository.upsert_system_settings(
                next_settings,
                actor_id=actor_id,
                audit_event=audit_event,
            )
        )
    now = _now_iso()
    settings = _memory_settings(current_store)
    settings.update(
        {
            "admin_email": normalized_email,
            "email_delivery": normalized_delivery,
            "updated_at": now,
            "updated_by": actor_id,
        }
    )
    _memory_audit_events(current_store).append(audit_event)
    return _public_settings(settings)


def _smtp_password_from_delivery(delivery: dict[str, Any]) -> str:
    direct_password = _normalize_optional_text(delivery.get("smtp_password"))
    if direct_password:
        return direct_password
    secret_ref = _normalize_optional_text(delivery.get("smtp_secret_ref"))
    if secret_ref and secret_ref.startswith("env:"):
        env_name = secret_ref.removeprefix("env:").strip()
        env_value = os.getenv(env_name)
        if env_value:
            return env_value
    raise api_error(
        400,
        "VALIDATION_ERROR",
        "Configured smtp_secret_ref cannot be resolved by this runtime",
    )


def test_email_delivery_response(
    current_store: Any,
    *,
    actor_id: str,
    recipient_email: str | None,
) -> dict[str, Any]:
    repository = _settings_repository(current_store)
    settings = (
        repository.get_system_settings()
        if repository is not None
        else dict(_memory_settings(current_store))
    )
    delivery = settings.get("email_delivery")
    if not isinstance(delivery, dict) or not _email_delivery_configured(settings):
        raise api_error(400, "VALIDATION_ERROR", "Email delivery is not fully configured")
    recipient = _normalize_optional_email(
        recipient_email or settings.get("admin_email"),
        "recipient_email",
    )
    if not recipient:
        raise api_error(400, "VALIDATION_ERROR", "recipient_email is required")

    message = EmailMessage()
    message["From"] = str(delivery["default_from"])
    message["To"] = recipient
    if delivery.get("reply_to"):
        message["Reply-To"] = str(delivery["reply_to"])
    message["Subject"] = "[AI Brain] 邮件发送配置测试"
    message.set_content(
        "这是一封 AI Brain 系统设置测试邮件，用于验证 SMTP 发信配置。",
    )

    host = str(delivery["smtp_host"])
    port = int(delivery["smtp_port"])
    password = _smtp_password_from_delivery(delivery)
    smtp_tls = str(delivery.get("smtp_tls") or "starttls")
    username = str(delivery["smtp_username"])
    try:
        if smtp_tls == "ssl":
            with smtplib.SMTP_SSL(host, port, timeout=SMTP_TEST_TIMEOUT_SECONDS) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=SMTP_TEST_TIMEOUT_SECONDS) as smtp:
                if smtp_tls == "starttls":
                    smtp.starttls()
                smtp.login(username, password)
                smtp.send_message(message)
    except smtplib.SMTPException as exc:
        raise api_error(
            502,
            "EMAIL_DELIVERY_TEST_FAILED",
            "Email delivery test failed",
            {"error": str(exc)},
        ) from exc

    return {
        "delivery_status": "sent",
        "recipient_email": recipient,
        "smtp_host": host,
        "smtp_port": port,
        "smtp_tls": smtp_tls,
    }
