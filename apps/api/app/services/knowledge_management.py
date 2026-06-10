from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.core.config import get_settings
from app.services.knowledge_deposits import (
    apply_knowledge_document_to_memory,
    record_audit_event,
    save_knowledge_document_records,
    uses_repository_context,
)
from app.services.knowledge_documents import knowledge_document_response
from app.services.knowledge_indexing import replace_knowledge_chunks_result
from app.services.object_storage import object_storage

WRITE_SPACE_ROLES = {"admin", "contributor", "maintainer"}
READ_SPACE_ROLES = WRITE_SPACE_ROLES | {"reader"}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def persist_knowledge_payload(
    current_store: Any,
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_knowledge = getattr(repository, "save_knowledge", None)
    if not callable(save_knowledge):
        return
    save_knowledge(
        {
            "knowledge_assets": current_store.knowledge_assets,
            "knowledge_chunk_sets": current_store.knowledge_chunk_sets,
            "knowledge_chunks": current_store.knowledge_chunks,
            "knowledge_deposits": current_store.knowledge_deposits,
            "knowledge_documents": current_store.knowledge_documents,
            "knowledge_folders": current_store.knowledge_folders,
            "knowledge_import_jobs": current_store.knowledge_import_jobs,
            "knowledge_space_members": current_store.knowledge_space_members,
            "knowledge_spaces": current_store.knowledge_spaces,
            "audit_events": [audit_event] if audit_event is not None else [],
        }
    )


def non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def user_has_global_knowledge_access(user: dict[str, Any]) -> bool:
    return "admin" in set(user.get("roles") or [])


def user_has_space_scope(
    user: dict[str, Any],
    *,
    space_id: str,
    required: str,
) -> bool:
    if user_has_global_knowledge_access(user):
        return True
    allowed_levels = {"read"} if required == "read" else {"write", "admin"}
    if required == "read":
        allowed_levels = {"read", "write", "admin"}
    for scope in user.get("scope_summary") or []:
        if scope.get("scope_type") not in {"global", "knowledge_space"}:
            continue
        if scope.get("scope_id") not in {"*", space_id}:
            continue
        if scope.get("access_level") in allowed_levels:
            return True
    return False


def user_has_space_membership(
    current_store: Any,
    user: dict[str, Any],
    *,
    space_id: str,
    required: str,
) -> bool:
    user_id = str(user["id"])
    for member in current_store.knowledge_space_members.values():
        if member.get("knowledge_space_id") != space_id:
            continue
        if member.get("user_id") != user_id or member.get("status", "active") != "active":
            continue
        role = member.get("space_role", "reader")
        if required == "read" and role in READ_SPACE_ROLES:
            return True
        if required == "write" and role in WRITE_SPACE_ROLES:
            return True
    return False


def user_can_access_space(
    current_store: Any,
    user: dict[str, Any],
    *,
    space_id: str,
    required: str = "read",
) -> bool:
    space = current_store.knowledge_spaces.get(space_id)
    if space is None or space.get("status", "active") != "active":
        return False
    if space.get("owner_user_id") == user.get("id"):
        return True
    return user_has_space_scope(user, space_id=space_id, required=required) or (
        user_has_space_membership(current_store, user, space_id=space_id, required=required)
    )


def ensure_space_access(
    current_store: Any,
    user: dict[str, Any],
    *,
    space_id: str,
    required: str = "read",
) -> None:
    if space_id not in current_store.knowledge_spaces:
        raise api_error(404, "NOT_FOUND", "Knowledge space not found")
    if not user_can_access_space(current_store, user, space_id=space_id, required=required):
        raise api_error(403, "FORBIDDEN", "Knowledge space permission denied")


def document_is_readable(
    current_store: Any,
    user: dict[str, Any],
    document: dict[str, Any],
) -> bool:
    space_id = document.get("knowledge_space_id")
    if space_id:
        return user_can_access_space(current_store, user, space_id=space_id, required="read")
    from app.services.knowledge_documents import user_can_read_roles

    return user_can_read_roles(user, document.get("permission_roles") or [])


def create_knowledge_space_result(
    *,
    current_store: Any,
    code: str,
    name: str,
    description: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    if not user_has_global_knowledge_access(user) and "knowledge_owner" not in set(user["roles"]):
        raise api_error(403, "FORBIDDEN", "Knowledge space management denied")
    normalized_code = non_blank(code, "code")
    if any(
        space.get("code") == normalized_code
        for space in current_store.knowledge_spaces.values()
    ):
        raise api_error(409, "KNOWLEDGE_SPACE_CODE_EXISTS", "Knowledge space code already exists")
    timestamp = now_iso()
    space = {
        "id": current_store.new_id("knowledge_space"),
        "code": normalized_code,
        "name": non_blank(name, "name"),
        "description": description.strip(),
        "owner_user_id": user["id"],
        "department_id": None,
        "status": "active",
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    current_store.knowledge_spaces[space["id"]] = space
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_space.created",
        subject_id=space["id"],
        subject_type="knowledge_space",
    )
    persist_knowledge_payload(current_store, audit_event=audit_event)
    return dict(space)


def list_knowledge_spaces_result(*, current_store: Any, user: dict[str, Any]) -> dict[str, Any]:
    items = [
        dict(space)
        for space in current_store.knowledge_spaces.values()
        if user_can_access_space(current_store, user, space_id=space["id"], required="read")
    ]
    items.sort(key=lambda item: (item.get("code", ""), item["id"]))
    return {"items": items, "total": len(items)}


def update_knowledge_space_members_result(
    *,
    current_store: Any,
    members: list[dict[str, Any]],
    space_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_space_access(current_store, user, space_id=space_id, required="write")
    normalized_members: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for member in members:
        user_id = non_blank(member.get("user_id"), "user_id")
        role = member.get("space_role", "reader")
        if role not in READ_SPACE_ROLES:
            raise api_error(400, "VALIDATION_ERROR", "Unsupported space_role")
        key = (user_id, role)
        if key in seen:
            raise api_error(400, "VALIDATION_ERROR", "members must be unique")
        seen.add(key)
        normalized_members.append(
            {
                "knowledge_space_id": space_id,
                "user_id": user_id,
                "space_role": role,
                "status": "active",
                "granted_by": user["id"],
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        )
    current_store.knowledge_space_members = {
        key: value
        for key, value in current_store.knowledge_space_members.items()
        if value.get("knowledge_space_id") != space_id
    }
    for member in normalized_members:
        member_key = f"{space_id}:{member['user_id']}:{member['space_role']}"
        current_store.knowledge_space_members[member_key] = member
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_space.members_updated",
        subject_id=space_id,
        subject_type="knowledge_space",
    )
    persist_knowledge_payload(current_store, audit_event=audit_event)
    return {"knowledge_space_id": space_id, "members": normalized_members}


def folder_path(current_store: Any, folder: dict[str, Any]) -> str:
    names = [folder["name"]]
    parent_id = folder.get("parent_folder_id")
    while parent_id:
        parent = current_store.knowledge_folders.get(parent_id)
        if parent is None:
            break
        names.append(parent["name"])
        parent_id = parent.get("parent_folder_id")
    return "/".join(reversed(names))


def create_knowledge_folder_result(
    *,
    current_store: Any,
    name: str,
    parent_folder_id: str | None,
    space_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_space_access(current_store, user, space_id=space_id, required="write")
    if parent_folder_id is not None:
        parent = current_store.knowledge_folders.get(parent_folder_id)
        if parent is None or parent.get("knowledge_space_id") != space_id:
            raise api_error(404, "NOT_FOUND", "Parent folder not found")
    timestamp = now_iso()
    folder = {
        "id": current_store.new_id("knowledge_folder"),
        "knowledge_space_id": space_id,
        "parent_folder_id": parent_folder_id,
        "name": non_blank(name, "name"),
        "status": "active",
        "sort_order": len(current_store.knowledge_folders) + 1,
        "created_by": user["id"],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    folder["path"] = folder_path(current_store, folder)
    current_store.knowledge_folders[folder["id"]] = folder
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_folder.created",
        subject_id=folder["id"],
        subject_type="knowledge_folder",
    )
    persist_knowledge_payload(current_store, audit_event=audit_event)
    return dict(folder)


def list_knowledge_folders_result(
    *,
    current_store: Any,
    space_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_space_access(current_store, user, space_id=space_id, required="read")
    items = [
        {**folder, "path": folder_path(current_store, folder)}
        for folder in current_store.knowledge_folders.values()
        if folder.get("knowledge_space_id") == space_id and folder.get("status") != "archived"
    ]
    items.sort(key=lambda item: (item.get("sort_order", 0), item["name"], item["id"]))
    return {"items": items, "total": len(items)}


def decode_upload_content(content_base64: str) -> bytes:
    try:
        return base64.b64decode(content_base64.encode("ascii"), validate=True)
    except Exception as exc:  # noqa: BLE001
        raise api_error(400, "VALIDATION_ERROR", "content_base64 is invalid") from exc


def create_asset_record(
    *,
    content: bytes,
    current_store: Any,
    document_id: str,
    filename: str,
    mime_type: str,
    space_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    settings = get_settings()
    digest = hashlib.sha256(content).hexdigest()
    asset_id = current_store.new_id("knowledge_asset")
    object_key = f"knowledge/{space_id}/{document_id}/v1/original/{digest}/{filename}"
    storage = object_storage()
    stored = storage.put_bytes(
        bucket=settings.object_storage_bucket,
        content=content,
        mime_type=mime_type,
        object_key=object_key,
    )
    timestamp = now_iso()
    asset = {
        "id": asset_id,
        "knowledge_space_id": space_id,
        "document_id": document_id,
        "asset_type": "original",
        "storage_provider": storage.provider,
        "bucket": stored.bucket,
        "object_key": stored.object_key,
        "content_hash": digest,
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": stored.size_bytes,
        "metadata": {},
        "created_by": user["id"],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    current_store.knowledge_assets[asset_id] = asset
    return asset


def upload_knowledge_document_result(
    *,
    content_base64: str,
    current_store: Any,
    doc_type: str,
    filename: str,
    folder_id: str | None,
    knowledge_space_id: str,
    mime_type: str,
    tags: list[str],
    title: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_space_access(current_store, user, space_id=knowledge_space_id, required="write")
    if folder_id is not None:
        folder = current_store.knowledge_folders.get(folder_id)
        if folder is None or folder.get("knowledge_space_id") != knowledge_space_id:
            raise api_error(404, "NOT_FOUND", "Knowledge folder not found")
    content = decode_upload_content(content_base64)
    text_content = content.decode("utf-8", errors="replace").strip()
    if not text_content:
        raise api_error(400, "VALIDATION_ERROR", "uploaded content is empty")

    timestamp = now_iso()
    document_id = current_store.new_id("knowledge")
    chunk_set_id = current_store.new_id("knowledge_chunk_set")
    document = {
        "id": document_id,
        "title": non_blank(title, "title"),
        "content": text_content,
        "source_type": "upload",
        "doc_type": doc_type or "manual",
        "product_id": None,
        "knowledge_space_id": knowledge_space_id,
        "folder_id": folder_id,
        "permission_roles": ["admin"],
        "permission_scope": {"knowledge_space_id": knowledge_space_id},
        "tags": tags,
        "index_status": "pending_index",
        "index_error": None,
        "vector_index_error": None,
        "created_by": user["id"],
        "created_at": timestamp,
        "updated_at": timestamp,
        "document_version": 1,
        "active_chunk_set_id": chunk_set_id,
    }
    asset = create_asset_record(
        content=content,
        current_store=current_store,
        document_id=document_id,
        filename=non_blank(filename, "filename"),
        mime_type=mime_type or "application/octet-stream",
        space_id=knowledge_space_id,
        user=user,
    )
    document["source_asset_id"] = asset["id"]
    document["parsed_asset_id"] = asset["id"]
    chunk_set = {
        "id": chunk_set_id,
        "document_id": document_id,
        "source_asset_id": asset["id"],
        "parsed_asset_id": asset["id"],
        "parser_engine": "plain_text",
        "parser_version": "v1",
        "chunk_strategy": "simple_text",
        "embedding_model": None,
        "embedding_dimension": None,
        "status": "building",
        "created_by": user["id"],
        "created_at": timestamp,
        "updated_at": timestamp,
        "activated_at": None,
    }
    current_store.knowledge_chunk_sets[chunk_set_id] = chunk_set
    import_job = {
        "id": current_store.new_id("knowledge_import_job"),
        "document_id": document_id,
        "source_asset_id": asset["id"],
        "parser_engine": "plain_text",
        "chunk_strategy": "simple_text",
        "status": "parsing",
        "progress": 40,
        "error_code": None,
        "error_message": None,
        "created_by": user["id"],
        "started_at": timestamp,
        "finished_at": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    current_store.knowledge_import_jobs[import_job["id"]] = import_job

    model_log_start_index = len(current_store.model_gateway_logs)
    document, chunks = replace_knowledge_chunks_result(current_store, document)
    for chunk in chunks:
        chunk["chunk_set_id"] = chunk_set_id
        chunk.setdefault("metadata", {})["knowledge_space_id"] = knowledge_space_id
        chunk["metadata"]["folder_id"] = folder_id
        chunk["metadata"]["source_asset_id"] = asset["id"]
        chunk["metadata"]["chunk_set_id"] = chunk_set_id
    chunk_set = {
        **chunk_set,
        "status": "active",
        "embedding_model": (
            chunks[0].get("metadata", {}).get("embedding_model") if chunks else None
        ),
        "embedding_dimension": (
            chunks[0].get("metadata", {}).get("embedding_dimension") if chunks else None
        ),
        "activated_at": now_iso(),
        "updated_at": now_iso(),
    }
    current_store.knowledge_chunk_sets[chunk_set_id] = chunk_set
    import_job = {
        **import_job,
        "status": "completed" if document["index_status"] != "index_failed" else "failed",
        "progress": 100 if document["index_status"] != "index_failed" else 80,
        "error_code": document.get("index_error"),
        "error_message": document.get("index_error"),
        "finished_at": now_iso(),
        "updated_at": now_iso(),
    }
    current_store.knowledge_import_jobs[import_job["id"]] = import_job

    if not uses_repository_context(current_store):
        apply_knowledge_document_to_memory(current_store, document, chunks)
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_document.uploaded",
        subject_id=document_id,
        subject_type="knowledge_document",
    )
    save_knowledge_document_records(
        current_store,
        audit_event=audit_event,
        chunks=chunks,
        document=document,
        model_logs=current_store.model_gateway_logs[model_log_start_index:],
    )
    persist_knowledge_payload(current_store)
    return {
        "asset": dict(asset),
        "document": knowledge_document_response(current_store, document, chunks),
        "import_job": dict(import_job),
    }


def asset_preview_result(
    *,
    asset_id: str,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    asset = current_store.knowledge_assets.get(asset_id)
    if asset is None:
        raise api_error(404, "NOT_FOUND", "Knowledge asset not found")
    ensure_space_access(
        current_store,
        user,
        space_id=asset["knowledge_space_id"],
        required="read",
    )
    content = object_storage().get_bytes(bucket=asset["bucket"], object_key=asset["object_key"])
    text_content = content.decode("utf-8", errors="replace")
    return {
        "asset": dict(asset),
        "content": text_content,
        "preview_type": "text",
    }
