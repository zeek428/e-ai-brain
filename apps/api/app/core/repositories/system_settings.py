from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

SYSTEM_ADMIN_EMAIL_KEY = "system_admin_email"


class SystemSettingsRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._upsert_audit_events = upsert_audit_events

    def get_system_settings(self) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT setting_value, updated_by, updated_at
                    FROM system_settings
                    WHERE setting_key = %s
                    """,
                    (SYSTEM_ADMIN_EMAIL_KEY,),
                )
                row = cursor.fetchone()
        if row is None:
            return {}
        value = row[0] if isinstance(row[0], dict) else {}
        admin_email = value.get("admin_email", value.get("email"))
        return {
            "admin_email": admin_email,
            "email_delivery": value.get("email_delivery"),
            "updated_at": row[2].isoformat() if row[2] else None,
            "updated_by": row[1],
        }

    def upsert_system_settings(
        self,
        settings: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        admin_email = settings.get("admin_email")
        setting_value = {
            "admin_email": admin_email,
            "email": admin_email,
            "email_delivery": settings.get("email_delivery"),
        }
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO system_settings (
                      setting_key,
                      setting_value,
                      description,
                      updated_by
                    )
                    VALUES (%s, %s::jsonb, %s, %s)
                    ON CONFLICT (setting_key) DO UPDATE SET
                      setting_value = EXCLUDED.setting_value,
                      description = EXCLUDED.description,
                      updated_by = EXCLUDED.updated_by,
                      updated_at = now()
                    RETURNING setting_value, updated_by, updated_at
                    """,
                    (
                        SYSTEM_ADMIN_EMAIL_KEY,
                        json.dumps(setting_value, ensure_ascii=False),
                        "系统管理员邮箱，用于发送 AI Brain 相关系统邮件。",
                        actor_id,
                    ),
                )
                row = cursor.fetchone()
                if audit_event is not None:
                    if self._upsert_audit_events is None:
                        raise RuntimeError("Audit upsert callback is not configured")
                    self._upsert_audit_events(cursor, [audit_event])
        value = row[0] if row and isinstance(row[0], dict) else {}
        admin_email = value.get("admin_email", value.get("email"))
        return {
            "admin_email": admin_email,
            "email_delivery": value.get("email_delivery"),
            "updated_at": row[2].isoformat() if row and row[2] else None,
            "updated_by": row[1] if row else actor_id,
        }
