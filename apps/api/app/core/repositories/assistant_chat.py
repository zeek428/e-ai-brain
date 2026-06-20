from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class AssistantChatReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
        upsert_model_gateway_logs: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._delete_missing = delete_missing
        self._upsert_audit_events = upsert_audit_events
        self._upsert_model_gateway_logs = upsert_model_gateway_logs

    def load_assistant_chat(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                action_drafts = self._load_assistant_action_drafts(cursor)
                action_runs = self._load_assistant_action_runs(cursor)
                chat_runs = self._load_assistant_chat_runs(cursor)
                conversations = self._load_assistant_conversations(cursor)
                messages = self._load_assistant_messages(cursor)
        return {
            "assistant_action_drafts": action_drafts,
            "assistant_action_runs": action_runs,
            "assistant_chat_runs": chat_runs,
            "assistant_conversations": conversations,
            "assistant_messages": messages,
        }

    def list_assistant_chat_runs(self, *, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, conversation_id, user_message_id,
                           assistant_message_id, client_request_id, status,
                           cancel_reason, cancelled_by, cancelled_at, error_code,
                           error_message, metadata_json, started_at, finished_at,
                           created_at, updated_at
                    FROM assistant_chat_runs
                    WHERE user_id = %s
                    ORDER BY updated_at DESC, id
                    """,
                    (user_id,),
                )
                return [self._assistant_chat_run_from_row(row) for row in cursor.fetchall()]

    def get_assistant_chat_run(self, *, run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, conversation_id, user_message_id,
                           assistant_message_id, client_request_id, status,
                           cancel_reason, cancelled_by, cancelled_at, error_code,
                           error_message, metadata_json, started_at, finished_at,
                           created_at, updated_at
                    FROM assistant_chat_runs
                    WHERE id = %s
                    """,
                    (run_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return self._assistant_chat_run_from_row(row)

    def list_assistant_conversations(self, *, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, product_id, title, message_count, last_message_at,
                           created_at, updated_at, command_signature,
                           source_message_hash, context_scope
                    FROM assistant_conversations
                    WHERE user_id = %s
                    ORDER BY COALESCE(last_message_at, updated_at) DESC, id
                    """,
                    (user_id,),
                )
                conversations = []
                for row in cursor.fetchall():
                    conversations.append(self._assistant_conversation_from_row(row))
                return conversations

    def find_reusable_assistant_conversation(
        self,
        *,
        command_signature: str,
        context_scope: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, product_id, title, message_count, last_message_at,
                           created_at, updated_at, command_signature,
                           source_message_hash, context_scope
                    FROM assistant_conversations
                    WHERE user_id = %s
                      AND command_signature = %s
                      AND COALESCE(context_scope, 'global') = %s
                    ORDER BY COALESCE(last_message_at, updated_at, created_at) DESC, id DESC
                    LIMIT 1
                    """,
                    (user_id, command_signature, context_scope),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return self._assistant_conversation_from_row(row)

    def list_assistant_conversation_messages(
        self,
        *,
        conversation_id: str,
        user_id: str,
    ) -> list[dict[str, Any]] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1
                    FROM assistant_conversations
                    WHERE id = %s AND user_id = %s
                    """,
                    (conversation_id, user_id),
                )
                if cursor.fetchone() is None:
                    return None
                cursor.execute(
                    """
                    SELECT id, conversation_id, user_id, role, content, product_id, model,
                           suggestions, metadata_json, status, client_request_id, run_id,
                           cancelled_at, completed_at, failed_at, error_code,
                           created_at, updated_at
                    FROM assistant_messages
                    WHERE conversation_id = %s AND user_id = %s
                    ORDER BY created_at, id
                    """,
                    (conversation_id, user_id),
                )
                messages = []
                for row in cursor.fetchall():
                    messages.append(self._assistant_message_from_row(row))
                return messages

    def list_assistant_action_drafts(self, *, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, source_message_id, client_draft_id, title, action,
                           risk_level, status, payload, metadata_json, result_run_id,
                           cancel_reason, cancelled_by, cancelled_at, confirmed_by,
                           confirmed_at, created_at, updated_at, expires_at
                    FROM assistant_action_drafts
                    WHERE user_id = %s
                    ORDER BY updated_at DESC, id
                    """,
                    (user_id,),
                )
                return [self._assistant_action_draft_from_row(row) for row in cursor.fetchall()]

    def get_assistant_action_draft(self, *, draft_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, source_message_id, client_draft_id, title, action,
                           risk_level, status, payload, metadata_json, result_run_id,
                           cancel_reason, cancelled_by, cancelled_at, confirmed_by,
                           confirmed_at, created_at, updated_at, expires_at
                    FROM assistant_action_drafts
                    WHERE id = %s
                    """,
                    (draft_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return self._assistant_action_draft_from_row(row)

    def list_assistant_role_quick_tasks(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, enterprise_id, group_key, group_label, group_roles, group_enabled,
                           group_sort_order, task_key, title, prompt, permissions,
                           analytics_key, target_draft_type, enabled, sort_order,
                           template_version, rollout_json, metadata_json, created_by,
                           updated_by, created_at, updated_at
                    FROM assistant_role_quick_tasks
                    ORDER BY group_sort_order, group_key, sort_order, task_key
                    """
                )
                return [
                    {
                        "analytics_key": row[11],
                        "created_at": row[20].isoformat() if row[20] else None,
                        "created_by": row[18],
                        "enabled": row[13],
                        "enterprise_id": row[1],
                        "group_enabled": row[5],
                        "group_key": row[2],
                        "group_label": row[3],
                        "group_roles": list(row[4] or []),
                        "group_sort_order": row[6],
                        "id": row[0],
                        "metadata_json": dict(row[17] or {}),
                        "permissions": list(row[10] or []),
                        "prompt": row[9],
                        "rollout_json": dict(row[16] or {}),
                        "sort_order": row[14],
                        "target_draft_type": row[12],
                        "task_key": row[7],
                        "template_version": row[15],
                        "title": row[8],
                        "updated_at": row[21].isoformat() if row[21] else None,
                        "updated_by": row[19],
                    }
                    for row in cursor.fetchall()
                ]

    def get_assistant_role_quick_task(self, *, config_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, enterprise_id, group_key, group_label, group_roles, group_enabled,
                           group_sort_order, task_key, title, prompt, permissions,
                           analytics_key, target_draft_type, enabled, sort_order,
                           template_version, rollout_json, metadata_json, created_by,
                           updated_by, created_at, updated_at
                    FROM assistant_role_quick_tasks
                    WHERE id = %s
                    """,
                    (config_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return {
            "analytics_key": row[11],
            "created_at": row[20].isoformat() if row[20] else None,
            "created_by": row[18],
            "enabled": row[13],
            "enterprise_id": row[1],
            "group_enabled": row[5],
            "group_key": row[2],
            "group_label": row[3],
            "group_roles": list(row[4] or []),
            "group_sort_order": row[6],
            "id": row[0],
            "metadata_json": dict(row[17] or {}),
            "permissions": list(row[10] or []),
            "prompt": row[9],
            "rollout_json": dict(row[16] or {}),
            "sort_order": row[14],
            "target_draft_type": row[12],
            "task_key": row[7],
            "template_version": row[15],
            "title": row[8],
            "updated_at": row[21].isoformat() if row[21] else None,
            "updated_by": row[19],
        }

    def list_assistant_action_reference_configs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, enterprise_id, action_key, title, summary, prompt, url,
                           aliases, roles, permissions, enabled, sort_order,
                           template_version, rollout_json, metadata_json, created_by,
                           updated_by, created_at, updated_at
                    FROM assistant_action_reference_configs
                    ORDER BY sort_order, action_key, COALESCE(template_version, ''), id
                    """
                )
                return [
                    self._assistant_action_reference_config_from_row(row)
                    for row in cursor.fetchall()
                ]

    def get_assistant_action_reference_config(
        self,
        *,
        config_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, enterprise_id, action_key, title, summary, prompt, url,
                           aliases, roles, permissions, enabled, sort_order,
                           template_version, rollout_json, metadata_json, created_by,
                           updated_by, created_at, updated_at
                    FROM assistant_action_reference_configs
                    WHERE id = %s
                    """,
                    (config_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return self._assistant_action_reference_config_from_row(row)

    def save_assistant_action_reference_config_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO assistant_action_reference_configs (
                      id, enterprise_id, action_key, title, summary, prompt, url,
                      aliases, roles, permissions, enabled, sort_order,
                      template_version, rollout_json, metadata_json, created_by,
                      updated_by, created_at, updated_at
                    )
                    VALUES (
                      %s, %s, %s, %s, %s, %s, %s,
                      %s::jsonb, %s::jsonb, %s::jsonb, %s, %s,
                      %s, %s::jsonb, %s::jsonb, %s,
                      %s, COALESCE(%s::timestamptz, now()), now()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                      enterprise_id = EXCLUDED.enterprise_id,
                      action_key = EXCLUDED.action_key,
                      title = EXCLUDED.title,
                      summary = EXCLUDED.summary,
                      prompt = EXCLUDED.prompt,
                      url = EXCLUDED.url,
                      aliases = EXCLUDED.aliases,
                      roles = EXCLUDED.roles,
                      permissions = EXCLUDED.permissions,
                      enabled = EXCLUDED.enabled,
                      sort_order = EXCLUDED.sort_order,
                      template_version = EXCLUDED.template_version,
                      rollout_json = EXCLUDED.rollout_json,
                      metadata_json = EXCLUDED.metadata_json,
                      updated_by = EXCLUDED.updated_by,
                      updated_at = now()
                    """,
                    (
                        record["id"],
                        record.get("enterprise_id"),
                        record["action_key"],
                        record["title"],
                        record["summary"],
                        record["prompt"],
                        record["url"],
                        json.dumps(record.get("aliases") or [], ensure_ascii=False),
                        json.dumps(record.get("roles") or [], ensure_ascii=False),
                        json.dumps(record.get("permissions") or [], ensure_ascii=False),
                        bool(record.get("enabled", True)),
                        int(record.get("sort_order") or 0),
                        record.get("template_version"),
                        json.dumps(record.get("rollout_json") or {}, ensure_ascii=False),
                        json.dumps(record.get("metadata_json") or {}, ensure_ascii=False),
                        record.get("created_by"),
                        record.get("updated_by"),
                        record.get("created_at"),
                    ),
                )
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def delete_assistant_action_reference_config_record(
        self,
        config_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM assistant_action_reference_configs WHERE id = %s",
                    (config_id,),
                )
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def save_assistant_role_quick_task_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO assistant_role_quick_tasks (
                      id, enterprise_id, group_key, group_label, group_roles,
                      group_enabled, group_sort_order, task_key, title, prompt,
                      permissions, analytics_key, target_draft_type, enabled,
                      sort_order, template_version, rollout_json, metadata_json,
                      created_by, updated_by, created_at, updated_at
                    )
                    VALUES (
                      %s, %s, %s, %s, %s::jsonb,
                      %s, %s, %s, %s, %s,
                      %s::jsonb, %s, %s, %s,
                      %s, %s, %s::jsonb, %s::jsonb,
                      %s, %s, COALESCE(%s::timestamptz, now()), now()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                      enterprise_id = EXCLUDED.enterprise_id,
                      group_key = EXCLUDED.group_key,
                      group_label = EXCLUDED.group_label,
                      group_roles = EXCLUDED.group_roles,
                      group_enabled = EXCLUDED.group_enabled,
                      group_sort_order = EXCLUDED.group_sort_order,
                      task_key = EXCLUDED.task_key,
                      title = EXCLUDED.title,
                      prompt = EXCLUDED.prompt,
                      permissions = EXCLUDED.permissions,
                      analytics_key = EXCLUDED.analytics_key,
                      target_draft_type = EXCLUDED.target_draft_type,
                      enabled = EXCLUDED.enabled,
                      sort_order = EXCLUDED.sort_order,
                      template_version = EXCLUDED.template_version,
                      rollout_json = EXCLUDED.rollout_json,
                      metadata_json = EXCLUDED.metadata_json,
                      updated_by = EXCLUDED.updated_by,
                      updated_at = now()
                    """,
                    (
                        record["id"],
                        record.get("enterprise_id"),
                        record["group_key"],
                        record["group_label"],
                        json.dumps(record.get("group_roles") or [], ensure_ascii=False),
                        bool(record.get("group_enabled", True)),
                        int(record.get("group_sort_order") or 0),
                        record["task_key"],
                        record["title"],
                        record["prompt"],
                        json.dumps(record.get("permissions") or [], ensure_ascii=False),
                        record.get("analytics_key"),
                        record.get("target_draft_type"),
                        bool(record.get("enabled", True)),
                        int(record.get("sort_order") or 0),
                        record.get("template_version"),
                        json.dumps(record.get("rollout_json") or {}, ensure_ascii=False),
                        json.dumps(record.get("metadata_json") or {}, ensure_ascii=False),
                        record.get("created_by"),
                        record.get("updated_by"),
                        record.get("created_at"),
                    ),
                )
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def delete_assistant_role_quick_task_record(
        self,
        config_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM assistant_role_quick_tasks WHERE id = %s", (config_id,))
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def save_assistant_chat(self, payload: dict[str, Any]) -> None:
        action_drafts = payload.get("assistant_action_drafts", {})
        action_runs = payload.get("assistant_action_runs", {})
        chat_runs = payload.get("assistant_chat_runs", {})
        conversations = payload.get("assistant_conversations", {})
        messages = payload.get("assistant_messages", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing_assistant_rows(
                    cursor,
                    action_drafts=action_drafts,
                    action_runs=action_runs,
                    chat_runs=chat_runs,
                    conversations=conversations,
                    messages=messages,
                )
                self.upsert_assistant_action_drafts(cursor, action_drafts)
                self.upsert_assistant_action_runs(cursor, action_runs)
                self.upsert_assistant_chat_runs(cursor, chat_runs)
                self.upsert_assistant_conversations(cursor, conversations)
                self.upsert_assistant_messages(cursor, messages)

    def save_assistant_chat_records(
        self,
        *,
        chat_run: dict[str, Any] | None = None,
        conversation: dict[str, Any] | None,
        messages: list[dict[str, Any]],
        audit_events: list[dict[str, Any]],
        model_log: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if chat_run is not None:
                    self.upsert_assistant_chat_runs(cursor, {chat_run["id"]: chat_run})
                if conversation is not None:
                    self.upsert_assistant_conversations(
                        cursor,
                        {conversation["id"]: conversation},
                    )
                if messages:
                    self.upsert_assistant_messages(
                        cursor,
                        {message["id"]: message for message in messages},
                    )
                if model_log is not None:
                    if self._upsert_model_gateway_logs is None:
                        raise RuntimeError("Model gateway log upsert callback is not configured")
                    self._upsert_model_gateway_logs(cursor, [model_log])
                if self._upsert_audit_events is None:
                    raise RuntimeError("Audit upsert callback is not configured")
                self._upsert_audit_events(cursor, audit_events)

    def save_assistant_action_records(
        self,
        *,
        draft: dict[str, Any],
        audit_events: list[dict[str, Any]],
        run: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_assistant_action_drafts(cursor, {draft["id"]: draft})
                if run is not None:
                    self.upsert_assistant_action_runs(cursor, {run["id"]: run})
                if self._upsert_audit_events is None:
                    raise RuntimeError("Audit upsert callback is not configured")
                self._upsert_audit_events(cursor, audit_events)

    def _load_assistant_action_drafts(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, user_id, source_message_id, client_draft_id, title, action,
                   risk_level, status, payload, metadata_json, result_run_id,
                   cancel_reason, cancelled_by, cancelled_at, confirmed_by,
                   confirmed_at, created_at, updated_at, expires_at
            FROM assistant_action_drafts
            ORDER BY updated_at, id
            """
        )
        return {
            row[0]: self._assistant_action_draft_from_row(row)
            for row in cursor.fetchall()
        }

    def _load_assistant_action_runs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, draft_id, action, status, executed_by, result_type, result_id,
                   result, error_code, error_message, started_at, finished_at,
                   created_at, updated_at
            FROM assistant_action_runs
            ORDER BY created_at, id
            """
        )
        return {row[0]: self._assistant_action_run_from_row(row) for row in cursor.fetchall()}

    def _load_assistant_chat_runs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, user_id, conversation_id, user_message_id,
                   assistant_message_id, client_request_id, status,
                   cancel_reason, cancelled_by, cancelled_at, error_code,
                   error_message, metadata_json, started_at, finished_at,
                   created_at, updated_at
            FROM assistant_chat_runs
            ORDER BY created_at, id
            """
        )
        return {row[0]: self._assistant_chat_run_from_row(row) for row in cursor.fetchall()}

    def _load_assistant_conversations(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, user_id, product_id, title, message_count, last_message_at,
                   created_at, updated_at, command_signature,
                   source_message_hash, context_scope
            FROM assistant_conversations
            ORDER BY updated_at, id
            """
        )
        return {row[0]: self._assistant_conversation_from_row(row) for row in cursor.fetchall()}

    def _load_assistant_messages(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, conversation_id, user_id, role, content, product_id, model,
                   suggestions, metadata_json, status, client_request_id, run_id,
                   cancelled_at, completed_at, failed_at, error_code,
                   created_at, updated_at
            FROM assistant_messages
            ORDER BY created_at, id
            """
        )
        return {row[0]: self._assistant_message_from_row(row) for row in cursor.fetchall()}

    def _delete_missing_assistant_rows(
        self,
        cursor,
        *,
        action_drafts: dict[str, dict[str, Any]],
        action_runs: dict[str, dict[str, Any]],
        chat_runs: dict[str, dict[str, Any]],
        conversations: dict[str, dict[str, Any]],
        messages: dict[str, dict[str, Any]],
    ) -> None:
        if self._delete_missing is None:
            raise RuntimeError("Assistant chat delete callback is not configured")
        self._delete_missing(cursor, "assistant_messages", messages)
        self._delete_missing(cursor, "assistant_conversations", conversations)
        self._delete_missing(cursor, "assistant_chat_runs", chat_runs)
        self._delete_missing(cursor, "assistant_action_runs", action_runs)
        self._delete_missing(cursor, "assistant_action_drafts", action_drafts)

    def upsert_assistant_conversations(
        self,
        cursor,
        conversations: dict[str, dict[str, Any]],
    ) -> None:
        for conversation in conversations.values():
            created_at = conversation.get("created_at")
            updated_at = conversation.get("updated_at") or conversation.get("last_message_at")
            updated_at = updated_at or created_at
            cursor.execute(
                """
                INSERT INTO assistant_conversations (
                  id, user_id, product_id, title, message_count, last_message_at,
                  created_at, updated_at, command_signature, source_message_hash,
                  context_scope
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s::timestamptz,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()),
                  %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                  user_id = EXCLUDED.user_id,
                  product_id = EXCLUDED.product_id,
                  title = EXCLUDED.title,
                  message_count = EXCLUDED.message_count,
                  last_message_at = EXCLUDED.last_message_at,
                  updated_at = EXCLUDED.updated_at,
                  command_signature = EXCLUDED.command_signature,
                  source_message_hash = EXCLUDED.source_message_hash,
                  context_scope = EXCLUDED.context_scope
                """,
                (
                    conversation["id"],
                    conversation["user_id"],
                    conversation.get("product_id"),
                    conversation.get("title", "新对话"),
                    conversation.get("message_count", 0),
                    conversation.get("last_message_at"),
                    created_at,
                    updated_at,
                    conversation.get("command_signature"),
                    conversation.get("source_message_hash"),
                    conversation.get("context_scope"),
                ),
            )

    def upsert_assistant_messages(
        self,
        cursor,
        messages: dict[str, dict[str, Any]],
    ) -> None:
        for message in messages.values():
            created_at = message.get("created_at")
            updated_at = message.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO assistant_messages (
                  id, conversation_id, user_id, role, content, product_id, model,
                  suggestions, metadata_json, status, client_request_id, run_id,
                  cancelled_at, completed_at, failed_at, error_code, created_at,
                  updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb,
                  %s, %s, %s, %s::timestamptz, %s::timestamptz,
                  %s::timestamptz, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  conversation_id = EXCLUDED.conversation_id,
                  user_id = EXCLUDED.user_id,
                  role = EXCLUDED.role,
                  content = EXCLUDED.content,
                  product_id = EXCLUDED.product_id,
                  model = EXCLUDED.model,
                  suggestions = EXCLUDED.suggestions,
                  metadata_json = EXCLUDED.metadata_json,
                  status = EXCLUDED.status,
                  client_request_id = EXCLUDED.client_request_id,
                  run_id = EXCLUDED.run_id,
                  cancelled_at = EXCLUDED.cancelled_at,
                  completed_at = EXCLUDED.completed_at,
                  failed_at = EXCLUDED.failed_at,
                  error_code = EXCLUDED.error_code,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    message["id"],
                    message["conversation_id"],
                    message["user_id"],
                    message["role"],
                    message["content"],
                    message.get("product_id"),
                    message.get("model"),
                    json.dumps(message.get("suggestions", []), ensure_ascii=False),
                    json.dumps(
                        message.get("metadata_json")
                        or {"references": message.get("references", [])},
                        ensure_ascii=False,
                    ),
                    message.get("status", "completed"),
                    message.get("client_request_id"),
                    message.get("run_id"),
                    message.get("cancelled_at"),
                    message.get("completed_at"),
                    message.get("failed_at"),
                    message.get("error_code"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_assistant_chat_runs(
        self,
        cursor,
        runs: dict[str, dict[str, Any]],
    ) -> None:
        for run in runs.values():
            created_at = run.get("created_at")
            updated_at = run.get("updated_at") or run.get("finished_at") or created_at
            cursor.execute(
                """
                INSERT INTO assistant_chat_runs (
                  id, user_id, conversation_id, user_message_id,
                  assistant_message_id, client_request_id, status,
                  cancel_reason, cancelled_by, cancelled_at, error_code,
                  error_message, metadata_json, started_at, finished_at,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s,
                  %s, %s, %s,
                  %s, %s, %s::timestamptz, %s,
                  %s, %s::jsonb, %s::timestamptz, %s::timestamptz,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  user_id = EXCLUDED.user_id,
                  conversation_id = EXCLUDED.conversation_id,
                  user_message_id = EXCLUDED.user_message_id,
                  assistant_message_id = EXCLUDED.assistant_message_id,
                  client_request_id = EXCLUDED.client_request_id,
                  status = EXCLUDED.status,
                  cancel_reason = EXCLUDED.cancel_reason,
                  cancelled_by = EXCLUDED.cancelled_by,
                  cancelled_at = EXCLUDED.cancelled_at,
                  error_code = EXCLUDED.error_code,
                  error_message = EXCLUDED.error_message,
                  metadata_json = EXCLUDED.metadata_json,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    run["id"],
                    run["user_id"],
                    run.get("conversation_id"),
                    run.get("user_message_id"),
                    run.get("assistant_message_id"),
                    run.get("client_request_id"),
                    run.get("status", "running"),
                    run.get("cancel_reason"),
                    run.get("cancelled_by"),
                    run.get("cancelled_at"),
                    run.get("error_code"),
                    run.get("error_message"),
                    json.dumps(run.get("metadata_json") or {}, ensure_ascii=False),
                    run.get("started_at"),
                    run.get("finished_at"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_assistant_action_drafts(
        self,
        cursor,
        drafts: dict[str, dict[str, Any]],
    ) -> None:
        for draft in drafts.values():
            created_at = draft.get("created_at")
            updated_at = draft.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO assistant_action_drafts (
                  id, user_id, source_message_id, client_draft_id, title, action,
                  risk_level, status, payload, metadata_json, result_run_id,
                  cancel_reason, cancelled_by, cancelled_at, confirmed_by,
                  confirmed_at, expires_at, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s,
                  %s, %s, %s::jsonb, %s::jsonb, %s,
                  %s, %s, %s::timestamptz, %s,
                  %s::timestamptz, %s::timestamptz, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  user_id = EXCLUDED.user_id,
                  source_message_id = EXCLUDED.source_message_id,
                  client_draft_id = EXCLUDED.client_draft_id,
                  title = EXCLUDED.title,
                  action = EXCLUDED.action,
                  risk_level = EXCLUDED.risk_level,
                  status = EXCLUDED.status,
                  payload = EXCLUDED.payload,
                  metadata_json = EXCLUDED.metadata_json,
                  result_run_id = EXCLUDED.result_run_id,
                  cancel_reason = EXCLUDED.cancel_reason,
                  cancelled_by = EXCLUDED.cancelled_by,
                  cancelled_at = EXCLUDED.cancelled_at,
                  confirmed_by = EXCLUDED.confirmed_by,
                  confirmed_at = EXCLUDED.confirmed_at,
                  expires_at = EXCLUDED.expires_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    draft["id"],
                    draft.get("created_by") or draft.get("user_id"),
                    draft.get("source_message_id"),
                    draft.get("client_draft_id"),
                    draft["title"],
                    draft["action"],
                    draft.get("risk_level", "medium"),
                    draft.get("status", "pending"),
                    json.dumps(draft.get("payload", {}), ensure_ascii=False),
                    json.dumps(draft.get("metadata_json", {}), ensure_ascii=False),
                    draft.get("result_run_id"),
                    draft.get("cancel_reason"),
                    draft.get("cancelled_by"),
                    draft.get("cancelled_at"),
                    draft.get("confirmed_by"),
                    draft.get("confirmed_at"),
                    draft.get("expires_at"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_assistant_action_runs(
        self,
        cursor,
        runs: dict[str, dict[str, Any]],
    ) -> None:
        for run in runs.values():
            created_at = run.get("created_at")
            updated_at = run.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO assistant_action_runs (
                  id, draft_id, action, status, executed_by, result_type, result_id,
                  result, error_code, error_message, started_at, finished_at,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s,
                  %s::jsonb, %s, %s, %s::timestamptz, %s::timestamptz,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  draft_id = EXCLUDED.draft_id,
                  action = EXCLUDED.action,
                  status = EXCLUDED.status,
                  executed_by = EXCLUDED.executed_by,
                  result_type = EXCLUDED.result_type,
                  result_id = EXCLUDED.result_id,
                  result = EXCLUDED.result,
                  error_code = EXCLUDED.error_code,
                  error_message = EXCLUDED.error_message,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    run["id"],
                    run["draft_id"],
                    run["action"],
                    run["status"],
                    run.get("executed_by"),
                    run.get("result_type"),
                    run.get("result_id"),
                    json.dumps(run.get("result", {}), ensure_ascii=False),
                    run.get("error_code"),
                    run.get("error_message"),
                    run.get("started_at"),
                    run.get("finished_at"),
                    created_at,
                    updated_at,
                ),
            )

    def _assistant_action_draft_from_row(self, row) -> dict[str, Any]:
        draft = {
            "action": row[5],
            "cancel_reason": row[11],
            "cancelled_at": row[13].isoformat() if row[13] else None,
            "cancelled_by": row[12],
            "client_draft_id": row[3],
            "confirmed_at": row[15].isoformat() if row[15] else None,
            "confirmed_by": row[14],
            "created_at": row[16].isoformat() if row[16] else None,
            "created_by": row[1],
            "expires_at": row[18].isoformat() if len(row) > 18 and row[18] else None,
            "id": row[0],
            "metadata_json": dict(row[9] or {}),
            "payload": dict(row[8] or {}),
            "result_run_id": row[10],
            "risk_level": row[6],
            "source_message_id": row[2],
            "status": row[7],
            "title": row[4],
            "updated_at": row[17].isoformat() if row[17] else None,
            "user_id": row[1],
        }
        for optional_key in (
            "cancel_reason",
            "cancelled_at",
            "cancelled_by",
            "client_draft_id",
            "confirmed_at",
            "confirmed_by",
            "created_at",
            "expires_at",
            "result_run_id",
            "source_message_id",
            "updated_at",
        ):
            if draft[optional_key] is None:
                draft.pop(optional_key)
        return draft

    def _assistant_action_run_from_row(self, row) -> dict[str, Any]:
        run = {
            "action": row[2],
            "created_at": row[12].isoformat() if row[12] else None,
            "draft_id": row[1],
            "error_code": row[8],
            "error_message": row[9],
            "executed_by": row[4],
            "finished_at": row[11].isoformat() if row[11] else None,
            "id": row[0],
            "result": dict(row[7] or {}),
            "result_id": row[6],
            "result_type": row[5],
            "started_at": row[10].isoformat() if row[10] else None,
            "status": row[3],
            "updated_at": row[13].isoformat() if row[13] else None,
        }
        for optional_key in (
            "created_at",
            "error_code",
            "error_message",
            "finished_at",
            "result_id",
            "result_type",
            "started_at",
            "updated_at",
        ):
            if run[optional_key] is None:
                run.pop(optional_key)
        return run

    def _assistant_action_reference_config_from_row(self, row) -> dict[str, Any]:
        config = {
            "action_key": row[2],
            "aliases": list(row[7] or []),
            "created_at": row[17].isoformat() if row[17] else None,
            "created_by": row[15],
            "enabled": row[10],
            "enterprise_id": row[1],
            "id": row[0],
            "metadata_json": dict(row[14] or {}),
            "permissions": list(row[9] or []),
            "prompt": row[5],
            "roles": list(row[8] or []),
            "rollout_json": dict(row[13] or {}),
            "sort_order": row[11],
            "summary": row[4],
            "template_version": row[12],
            "title": row[3],
            "updated_at": row[18].isoformat() if row[18] else None,
            "updated_by": row[16],
            "url": row[6],
        }
        for optional_key in (
            "created_at",
            "created_by",
            "enterprise_id",
            "template_version",
            "updated_at",
            "updated_by",
        ):
            if config[optional_key] is None:
                config.pop(optional_key)
        return config

    def _assistant_chat_run_from_row(self, row) -> dict[str, Any]:
        run = {
            "assistant_message_id": row[4],
            "cancel_reason": row[7],
            "cancelled_at": row[9].isoformat() if row[9] else None,
            "cancelled_by": row[8],
            "client_request_id": row[5],
            "conversation_id": row[2],
            "created_at": row[15].isoformat() if row[15] else None,
            "error_code": row[10],
            "error_message": row[11],
            "finished_at": row[14].isoformat() if row[14] else None,
            "id": row[0],
            "metadata_json": dict(row[12] or {}),
            "started_at": row[13].isoformat() if row[13] else None,
            "status": row[6],
            "updated_at": row[16].isoformat() if row[16] else None,
            "user_id": row[1],
            "user_message_id": row[3],
        }
        for optional_key in (
            "assistant_message_id",
            "cancel_reason",
            "cancelled_at",
            "cancelled_by",
            "client_request_id",
            "conversation_id",
            "created_at",
            "error_code",
            "error_message",
            "finished_at",
            "started_at",
            "updated_at",
            "user_message_id",
        ):
            if run[optional_key] is None:
                run.pop(optional_key)
        return run

    def _assistant_conversation_from_row(self, row) -> dict[str, Any]:
        conversation = {
            "created_at": row[6].isoformat() if row[6] else None,
            "command_signature": row[8],
            "context_scope": row[10],
            "id": row[0],
            "last_message_at": row[5].isoformat() if row[5] else None,
            "message_count": row[4],
            "product_id": row[2],
            "source_message_hash": row[9],
            "title": row[3],
            "updated_at": row[7].isoformat() if row[7] else None,
            "user_id": row[1],
        }
        for optional_key in (
            "created_at",
            "command_signature",
            "context_scope",
            "last_message_at",
            "product_id",
            "source_message_hash",
            "updated_at",
        ):
            if conversation[optional_key] is None:
                conversation.pop(optional_key)
        return conversation

    def _assistant_message_from_row(self, row) -> dict[str, Any]:
        message = {
            "content": row[4],
            "conversation_id": row[1],
            "cancelled_at": row[12].isoformat() if row[12] else None,
            "client_request_id": row[10],
            "completed_at": row[13].isoformat() if row[13] else None,
            "created_at": row[16].isoformat() if row[16] else None,
            "error_code": row[15],
            "failed_at": row[14].isoformat() if row[14] else None,
            "id": row[0],
            "metadata_json": dict(row[8] or {}),
            "model": row[6],
            "product_id": row[5],
            "references": list((row[8] or {}).get("references") or []),
            "role": row[3],
            "run_id": row[11],
            "status": row[9] or "completed",
            "suggestions": list(row[7] or []),
            "updated_at": row[17].isoformat() if row[17] else None,
            "user_id": row[2],
        }
        for optional_key in (
            "cancelled_at",
            "client_request_id",
            "completed_at",
            "created_at",
            "error_code",
            "failed_at",
            "model",
            "product_id",
            "run_id",
            "updated_at",
        ):
            if message[optional_key] is None:
                message.pop(optional_key)
        return message
