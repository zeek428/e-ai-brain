from __future__ import annotations

from hashlib import sha256
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
    collapse_duplicates: bool = True,
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
    if collapse_duplicates:
        items = _collapse_duplicate_conversations(items)
    return {
        "items": items,
        "total": len(items),
    }


def _conversation_collapse_key(conversation: dict[str, Any]) -> tuple[str, str]:
    command_signature = str(conversation.get("command_signature") or "").strip()
    if command_signature:
        context_scope = conversation.get("context_scope") or _conversation_context_scope(
            conversation.get("product_id")
        )
        return f"command:{command_signature}", str(
            context_scope
        )
    title = " ".join(str(conversation.get("title") or "").strip().split()).casefold()
    if not title:
        return "", _conversation_context_scope(conversation.get("product_id"))
    return f"title:{title}", _conversation_context_scope(conversation.get("product_id"))


def _collapse_duplicate_conversations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collapsed: dict[tuple[str, str], dict[str, Any]] = {}
    ordered_keys: list[tuple[str, str]] = []
    for item in items:
        key = _conversation_collapse_key(item)
        if not key[0]:
            key = (str(item["id"]), key[1])
        existing = collapsed.get(key)
        if existing is None:
            collapsed[key] = {
                **item,
                "collapsed_conversation_ids": [item["id"]],
                "collapsed_message_count": int(item.get("message_count") or 0),
                "duplicate_conversation_ids": [],
                "duplicate_count": 1,
            }
            ordered_keys.append(key)
            continue
        existing["duplicate_count"] = int(existing.get("duplicate_count") or 1) + 1
        existing["duplicate_conversation_ids"] = [
            *list(existing.get("duplicate_conversation_ids") or []),
            item["id"],
        ]
        existing["collapsed_conversation_ids"] = [
            *list(existing.get("collapsed_conversation_ids") or [existing["id"]]),
            item["id"],
        ]
        existing["collapsed_message_count"] = (
            int(existing.get("collapsed_message_count") or 0)
            + int(item.get("message_count") or 0)
        )
    result: list[dict[str, Any]] = []
    duplicate_metadata_keys = {
        "collapsed_conversation_ids",
        "collapsed_message_count",
        "duplicate_conversation_ids",
        "duplicate_count",
    }
    for key in ordered_keys:
        item = collapsed[key]
        if int(item.get("duplicate_count") or 1) <= 1:
            item = {
                field: value
                for field, value in item.items()
                if field not in duplicate_metadata_keys
            }
        result.append(item)
    return result


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
    items = [
        public_assistant_message(message, include_tool_details=False)
        for message in messages
    ]
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
    signature_fields = _conversation_signature_fields(message, product_id=product_id)
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
            for key, value in signature_fields.items():
                conversation.setdefault(key, value)
            conversation["updated_at"] = now
            if not assistant_uses_repository_context(current_store):
                current_store.assistant_conversations[conversation_id] = conversation
            return conversation
        resolved_id = conversation_id
    else:
        reusable_conversation = _find_reusable_command_conversation(
            current_store,
            message=message,
            product_id=product_id,
            user_id=user_id,
        )
        if reusable_conversation is not None:
            conversation = dict(reusable_conversation)
            conversation["updated_at"] = now
            if product_id and not conversation.get("product_id"):
                conversation["product_id"] = product_id
            for key, value in signature_fields.items():
                conversation.setdefault(key, value)
            if not assistant_uses_repository_context(current_store):
                current_store.assistant_conversations[conversation["id"]] = conversation
            return conversation
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
        **signature_fields,
    }
    if not assistant_uses_repository_context(current_store):
        current_store.assistant_conversations[resolved_id] = conversation
    return conversation


def _find_reusable_command_conversation(
    current_store: MemoryStore,
    *,
    message: str,
    product_id: str | None,
    user_id: str,
) -> dict[str, Any] | None:
    if not _message_should_reuse_conversation(message):
        return None
    target_title = assistant_conversation_title(message)
    command_signature = _command_signature_for_message(message)
    context_scope = _conversation_context_scope(product_id)
    if command_signature:
        repository = assistant_query_repository(current_store)
        find_reusable = (
            getattr(repository, "find_reusable_assistant_conversation", None)
            if repository is not None
            else None
        )
        if callable(find_reusable):
            conversation = find_reusable(
                command_signature=command_signature,
                context_scope=context_scope,
                user_id=user_id,
            )
            if conversation is not None:
                return conversation
    normalized_title = " ".join(target_title.strip().split()).casefold()
    target_key = (
        f"command:{command_signature}" if command_signature else f"title:{normalized_title}",
        context_scope,
    )
    candidates = [
        conversation
        for conversation in current_store.assistant_conversations.values()
        if conversation.get("user_id") == user_id
        and _conversation_collapse_key(conversation) == target_key
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            item.get("last_message_at")
            or item.get("updated_at")
            or item.get("created_at")
            or ""
        ),
        reverse=True,
    )[0]


def _message_should_reuse_conversation(message: str) -> bool:
    normalized = " ".join(message.strip().split()).casefold()
    if not normalized:
        return False
    if normalized.startswith("@") or normalized.startswith("＠"):
        return True
    command_keywords = (
        "新建需求",
        "新增需求",
        "创建需求",
        "新建 bug",
        "新建bug",
        "新增 bug",
        "新增bug",
        "新建插件",
        "新增插件",
        "新建定时",
        "新增定时",
        "创建定时",
        "执行一次",
        "运行一次",
        "跑一次",
        "运行诊断",
        "指标解释",
    )
    return any(keyword.casefold() in normalized for keyword in command_keywords)


def _conversation_context_scope(product_id: str | None) -> str:
    return f"product:{product_id}" if product_id else "global"


def _normalized_command_message(message: str) -> str:
    return " ".join(message.strip().split()).casefold()


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _conversation_signature_fields(message: str, *, product_id: str | None) -> dict[str, str]:
    normalized = _normalized_command_message(message)
    fields = {
        "context_scope": _conversation_context_scope(product_id),
        "source_message_hash": _hash_text(f"assistant-message:v1:{normalized}"),
    }
    command_signature = _command_signature_for_message(message)
    if command_signature:
        fields["command_signature"] = command_signature
    return fields


def _command_signature_for_message(message: str) -> str | None:
    normalized = _normalized_command_message(message)
    if not normalized or not _message_should_reuse_conversation(normalized):
        return None
    return _hash_text(f"assistant-command:v1:{normalized}")


def append_assistant_message(
    current_store: MemoryStore,
    *,
    client_request_id: str | None = None,
    content: str,
    conversation: dict[str, Any],
    cancelled_at: str | None = None,
    completed_at: str | None = None,
    error_code: str | None = None,
    failed_at: str | None = None,
    intent: dict[str, Any] | None = None,
    now: str,
    role: str,
    run_id: str | None = None,
    status: str = "completed",
    user_id: str,
    model: str | None = None,
    references: list[dict[str, str]] | None = None,
    suggestions: list[str] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    metadata_json = {"references": references or []}
    if intent is not None:
        metadata_json["intent"] = intent
    if tool_results is not None:
        metadata_json["tool_results"] = tool_results
    message = {
        "content": content,
        "conversation_id": conversation["id"],
        "client_request_id": client_request_id,
        "cancelled_at": cancelled_at,
        "completed_at": completed_at,
        "created_at": now,
        "error_code": error_code,
        "failed_at": failed_at,
        "id": current_store.new_id("assistant_message"),
        "metadata_json": metadata_json,
        "model": model,
        "product_id": conversation.get("product_id"),
        "references": references or [],
        "role": role,
        "run_id": run_id,
        "status": status,
        "suggestions": suggestions or [],
        "user_id": user_id,
    }
    for optional_key in (
        "client_request_id",
        "cancelled_at",
        "completed_at",
        "error_code",
        "failed_at",
        "run_id",
    ):
        if message[optional_key] is None:
            message.pop(optional_key)
    if not assistant_uses_repository_context(current_store):
        current_store.assistant_messages[message["id"]] = message
    conversation["last_message_at"] = now
    conversation["message_count"] = int(conversation.get("message_count") or 0) + 1
    conversation["updated_at"] = now
    return message
