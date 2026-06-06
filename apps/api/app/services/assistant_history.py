from __future__ import annotations

from typing import Any

from app.core.store import MemoryStore
from app.services.assistant_context import (
    assistant_conversation_messages,
    assistant_conversation_title,
    public_assistant_conversation,
    public_assistant_message,
)
from app.services.assistant_errors import AssistantServiceError


def assistant_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    required_methods = [
        "list_assistant_conversation_messages",
        "list_assistant_conversations",
    ]
    if all(getattr(repository, method_name, None) is not None for method_name in required_methods):
        return repository
    return None


def assistant_uses_repository_context(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is not None


def assistant_conversations_response(
    current_store: MemoryStore,
    *,
    user_id: str,
) -> dict[str, Any]:
    repository = assistant_query_repository(current_store)
    if repository is not None:
        conversations = repository.list_assistant_conversations(user_id=user_id)
    else:
        conversations = [
            conversation
            for conversation in current_store.assistant_conversations.values()
            if conversation.get("user_id") == user_id
        ]
    items = [public_assistant_conversation(conversation) for conversation in conversations]
    items.sort(key=lambda item: item.get("last_message_at") or item["updated_at"], reverse=True)
    return {"items": items, "total": len(items)}


def assistant_conversation_messages_response(
    current_store: MemoryStore,
    *,
    conversation_id: str,
    user_id: str,
) -> dict[str, Any]:
    repository = assistant_query_repository(current_store)
    if repository is not None:
        messages = repository.list_assistant_conversation_messages(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        if messages is None:
            raise AssistantServiceError(404, "NOT_FOUND", "Assistant conversation not found")
    else:
        assistant_conversation_for_user(
            current_store,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        messages = assistant_conversation_messages(
            current_store,
            conversation_id=conversation_id,
        )
    items = [public_assistant_message(message) for message in messages]
    return {"items": items, "total": len(items)}


def assistant_conversation_for_user(
    current_store: MemoryStore,
    *,
    conversation_id: str,
    user_id: str,
) -> dict[str, Any]:
    conversation = current_store.assistant_conversations.get(conversation_id)
    if conversation is None or conversation.get("user_id") != user_id:
        raise AssistantServiceError(404, "NOT_FOUND", "Assistant conversation not found")
    return conversation


def ensure_assistant_conversation(
    current_store: MemoryStore,
    *,
    conversation_id: str | None,
    message: str,
    product_id: str | None,
    user: dict[str, Any],
    now: str,
) -> dict[str, Any]:
    user_id = user["id"]
    if conversation_id:
        existing = current_store.assistant_conversations.get(conversation_id)
        if existing is not None:
            if existing.get("user_id") != user_id:
                raise AssistantServiceError(404, "NOT_FOUND", "Assistant conversation not found")
            if (
                product_id
                and existing.get("product_id")
                and existing.get("product_id") != product_id
            ):
                raise AssistantServiceError(
                    400,
                    "VALIDATION_ERROR",
                    "Conversation product_id does not match",
                )
            conversation = dict(existing)
            if product_id and not conversation.get("product_id"):
                conversation["product_id"] = product_id
            conversation["updated_at"] = now
            if not assistant_uses_repository_context(current_store):
                current_store.assistant_conversations[conversation_id] = conversation
            return conversation
        resolved_id = conversation_id
    else:
        resolved_id = current_store.new_id("conversation")
    conversation = {
        "created_at": now,
        "id": resolved_id,
        "last_message_at": now,
        "message_count": 0,
        "product_id": product_id,
        "title": assistant_conversation_title(message),
        "updated_at": now,
        "user_id": user_id,
    }
    if not assistant_uses_repository_context(current_store):
        current_store.assistant_conversations[resolved_id] = conversation
    return conversation


def append_assistant_message(
    current_store: MemoryStore,
    *,
    content: str,
    conversation: dict[str, Any],
    now: str,
    role: str,
    user_id: str,
    model: str | None = None,
    references: list[dict[str, str]] | None = None,
    suggestions: list[str] | None = None,
) -> dict[str, Any]:
    metadata_json = {"references": references or []}
    message = {
        "content": content,
        "conversation_id": conversation["id"],
        "created_at": now,
        "id": current_store.new_id("assistant_message"),
        "metadata_json": metadata_json,
        "model": model,
        "product_id": conversation.get("product_id"),
        "references": references or [],
        "role": role,
        "suggestions": suggestions or [],
        "user_id": user_id,
    }
    if not assistant_uses_repository_context(current_store):
        current_store.assistant_messages[message["id"]] = message
    conversation["last_message_at"] = now
    conversation["message_count"] = int(conversation.get("message_count") or 0) + 1
    conversation["updated_at"] = now
    return message
