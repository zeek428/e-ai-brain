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
                conversations = self._load_assistant_conversations(cursor)
                messages = self._load_assistant_messages(cursor)
        return {
            "assistant_conversations": conversations,
            "assistant_messages": messages,
        }

    def list_assistant_conversations(self, *, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, product_id, title, message_count, last_message_at,
                           created_at, updated_at
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
                           suggestions, metadata_json, created_at, updated_at
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

    def save_assistant_chat(self, payload: dict[str, Any]) -> None:
        conversations = payload.get("assistant_conversations", {})
        messages = payload.get("assistant_messages", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing_assistant_rows(
                    cursor,
                    conversations=conversations,
                    messages=messages,
                )
                self.upsert_assistant_conversations(cursor, conversations)
                self.upsert_assistant_messages(cursor, messages)

    def save_assistant_chat_records(
        self,
        *,
        conversation: dict[str, Any] | None,
        messages: list[dict[str, Any]],
        audit_events: list[dict[str, Any]],
        model_log: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
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

    def _load_assistant_conversations(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, user_id, product_id, title, message_count, last_message_at,
                   created_at, updated_at
            FROM assistant_conversations
            ORDER BY updated_at, id
            """
        )
        return {row[0]: self._assistant_conversation_from_row(row) for row in cursor.fetchall()}

    def _load_assistant_messages(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, conversation_id, user_id, role, content, product_id, model,
                   suggestions, metadata_json, created_at, updated_at
            FROM assistant_messages
            ORDER BY created_at, id
            """
        )
        return {row[0]: self._assistant_message_from_row(row) for row in cursor.fetchall()}

    def _delete_missing_assistant_rows(
        self,
        cursor,
        *,
        conversations: dict[str, dict[str, Any]],
        messages: dict[str, dict[str, Any]],
    ) -> None:
        if self._delete_missing is None:
            raise RuntimeError("Assistant chat delete callback is not configured")
        self._delete_missing(cursor, "assistant_messages", messages)
        self._delete_missing(cursor, "assistant_conversations", conversations)

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
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s::timestamptz,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  user_id = EXCLUDED.user_id,
                  product_id = EXCLUDED.product_id,
                  title = EXCLUDED.title,
                  message_count = EXCLUDED.message_count,
                  last_message_at = EXCLUDED.last_message_at,
                  updated_at = EXCLUDED.updated_at
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
                  suggestions, metadata_json, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
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
                    created_at,
                    updated_at,
                ),
            )

    def _assistant_conversation_from_row(self, row) -> dict[str, Any]:
        conversation = {
            "created_at": row[6].isoformat() if row[6] else None,
            "id": row[0],
            "last_message_at": row[5].isoformat() if row[5] else None,
            "message_count": row[4],
            "product_id": row[2],
            "title": row[3],
            "updated_at": row[7].isoformat() if row[7] else None,
            "user_id": row[1],
        }
        for optional_key in (
            "created_at",
            "last_message_at",
            "product_id",
            "updated_at",
        ):
            if conversation[optional_key] is None:
                conversation.pop(optional_key)
        return conversation

    def _assistant_message_from_row(self, row) -> dict[str, Any]:
        message = {
            "content": row[4],
            "conversation_id": row[1],
            "created_at": row[9].isoformat() if row[9] else None,
            "id": row[0],
            "metadata_json": dict(row[8] or {}),
            "model": row[6],
            "product_id": row[5],
            "references": list((row[8] or {}).get("references") or []),
            "role": row[3],
            "suggestions": list(row[7] or []),
            "updated_at": row[10].isoformat() if row[10] else None,
            "user_id": row[2],
        }
        for optional_key in ("created_at", "model", "product_id", "updated_at"):
            if message[optional_key] is None:
                message.pop(optional_key)
        return message
