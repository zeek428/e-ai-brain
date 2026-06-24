from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.core.config import get_settings
from app.services.knowledge_deposits import (
    apply_knowledge_document_to_memory,
    get_knowledge_chunk_set_from_memory,
    put_knowledge_asset_to_memory,
    put_knowledge_chunk_set_to_memory,
    put_knowledge_chunk_to_memory,
    put_knowledge_document_to_memory,
    record_audit_event,
    uses_repository_context,
)
from app.services.knowledge_documents import knowledge_document_response
from app.services.knowledge_indexing import replace_knowledge_chunks_result
from app.services.object_storage import object_storage

WRITE_SPACE_ROLES = {"admin", "contributor", "maintainer"}
READ_SPACE_ROLES = WRITE_SPACE_ROLES | {"reader"}
IMPORT_JOB_RUNNABLE_STATUSES = {"queued", "uploaded", "failed"}
IMPORT_JOB_RETRYABLE_STATUSES = {"failed", "cancelled"}
SUPPORTED_PARSER_ENGINES = {"plain_text", "markdown", "pdf_text", "ocr_json", "table_json"}
SUPPORTED_CHUNK_STRATEGIES = {"simple_text", "parent_child", "regex_section"}


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


def _memory_collection(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def get_knowledge_import_job_from_memory(
    current_store: Any,
    job_id: str | None,
) -> dict[str, Any] | None:
    if not job_id:
        return None
    return _memory_collection(current_store, "knowledge_import_jobs").get(str(job_id))


def put_knowledge_import_job_to_memory(
    current_store: Any,
    import_job: dict[str, Any],
) -> None:
    job_id = import_job.get("id")
    if job_id is None:
        return
    _memory_collection(current_store, "knowledge_import_jobs")[str(job_id)] = import_job


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
        if not folder_is_effectively_active(current_store, parent_folder_id):
            raise api_error(409, "KNOWLEDGE_FOLDER_ARCHIVED", "Parent folder is archived")
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


def folder_descendant_ids(current_store: Any, folder_id: str) -> set[str]:
    descendants: set[str] = set()
    changed = True
    while changed:
        changed = False
        for folder in current_store.knowledge_folders.values():
            parent_id = folder.get("parent_folder_id")
            if parent_id == folder_id or parent_id in descendants:
                if folder["id"] not in descendants:
                    descendants.add(folder["id"])
                    changed = True
    return descendants


def folder_is_effectively_active(current_store: Any, folder_id: str | None) -> bool:
    if folder_id is None:
        return True
    visited: set[str] = set()
    current_id = folder_id
    while current_id:
        if current_id in visited:
            return False
        visited.add(current_id)
        folder = current_store.knowledge_folders.get(current_id)
        if folder is None or folder.get("status", "active") == "archived":
            return False
        current_id = folder.get("parent_folder_id")
    return True


def patch_knowledge_folder_result(
    *,
    current_store: Any,
    folder_id: str,
    name: str | None,
    parent_folder_id: str | None,
    parent_folder_id_set: bool,
    sort_order: int | None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    folder = current_store.knowledge_folders.get(folder_id)
    if folder is None:
        raise api_error(404, "NOT_FOUND", "Knowledge folder not found")
    space_id = folder["knowledge_space_id"]
    ensure_space_access(current_store, user, space_id=space_id, required="write")
    if status is not None and status not in {"active", "archived"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported folder status")
    if parent_folder_id_set and parent_folder_id is not None:
        parent = current_store.knowledge_folders.get(parent_folder_id)
        if parent is None or parent.get("knowledge_space_id") != space_id:
            raise api_error(404, "NOT_FOUND", "Parent folder not found")
        if not folder_is_effectively_active(current_store, parent_folder_id):
            raise api_error(409, "KNOWLEDGE_FOLDER_ARCHIVED", "Parent folder is archived")
        if parent_folder_id == folder_id or parent_folder_id in folder_descendant_ids(
            current_store,
            folder_id,
        ):
            raise api_error(409, "KNOWLEDGE_FOLDER_CYCLE", "Folder cannot be moved under itself")
    updated = {
        **folder,
        "updated_at": now_iso(),
    }
    if name is not None:
        updated["name"] = non_blank(name, "name")
    if parent_folder_id_set:
        updated["parent_folder_id"] = parent_folder_id
    if sort_order is not None:
        updated["sort_order"] = sort_order
    if status is not None:
        updated["status"] = status
    updated["path"] = folder_path(current_store, updated)
    current_store.knowledge_folders[folder_id] = updated
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_folder.updated",
        subject_id=folder_id,
        subject_type="knowledge_folder",
    )
    persist_knowledge_payload(current_store, audit_event=audit_event)
    return dict(updated)


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
        if folder.get("knowledge_space_id") == space_id
        and folder_is_effectively_active(current_store, folder["id"])
    ]
    items.sort(key=lambda item: (item.get("sort_order", 0), item["name"], item["id"]))
    return {"items": items, "total": len(items)}


def list_knowledge_document_assets_result(
    *,
    current_store: Any,
    document_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    document = current_store.knowledge_documents.get(document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    if not document_is_readable(current_store, user, document):
        raise api_error(403, "FORBIDDEN", "Knowledge document permission denied")
    items = [
        dict(asset)
        for asset in current_store.knowledge_assets.values()
        if asset.get("document_id") == document_id
    ]
    items.sort(
        key=lambda item: (item.get("asset_type", ""), item.get("created_at", ""), item["id"])
    )
    return {"document_id": document_id, "items": items, "total": len(items)}


def _import_job_space_id(
    *,
    current_store: Any,
    import_job: dict[str, Any],
) -> str | None:
    document_id = import_job.get("document_id")
    if document_id:
        document = current_store.knowledge_documents.get(document_id)
        if document is not None:
            document_space_id = document.get("knowledge_space_id")
            if document_space_id:
                return document_space_id
    source_asset_id = import_job.get("source_asset_id")
    if source_asset_id:
        asset = current_store.knowledge_assets.get(source_asset_id)
        if asset is not None:
            return asset.get("knowledge_space_id")
    return None


def import_job_response(current_store: Any, import_job: dict[str, Any]) -> dict[str, Any]:
    response = dict(import_job)
    document = current_store.knowledge_documents.get(import_job.get("document_id"))
    if document is not None:
        response["document_title"] = document.get("title")
        document_space_id = document.get("knowledge_space_id")
        if document_space_id:
            response["knowledge_space_id"] = document_space_id
        folder_id = document.get("folder_id")
        if folder_id:
            folder = current_store.knowledge_folders.get(folder_id)
            if folder is not None:
                response["folder_id"] = folder_id
                response["folder_path"] = folder.get("path") or folder_path(current_store, folder)
    source_asset_id = import_job.get("source_asset_id")
    if source_asset_id:
        asset = current_store.knowledge_assets.get(source_asset_id)
        if asset is not None:
            response["asset_filename"] = asset.get("filename")
            response["asset_mime_type"] = asset.get("mime_type")
            response["asset_size_bytes"] = asset.get("size_bytes")
            response.setdefault("knowledge_space_id", asset.get("knowledge_space_id"))
    return response


def list_knowledge_import_jobs_result(
    *,
    current_store: Any,
    document_id: str | None,
    knowledge_space_id: str | None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    if knowledge_space_id is not None:
        ensure_space_access(current_store, user, space_id=knowledge_space_id, required="read")

    items: list[dict[str, Any]] = []
    for import_job in current_store.knowledge_import_jobs.values():
        if document_id is not None and import_job.get("document_id") != document_id:
            continue
        if status is not None and import_job.get("status") != status:
            continue
        space_id = _import_job_space_id(current_store=current_store, import_job=import_job)
        if knowledge_space_id is not None and space_id != knowledge_space_id:
            continue
        if space_id is not None and not user_can_access_space(
            current_store,
            user,
            space_id=space_id,
            required="read",
        ):
            continue
        if space_id is None:
            document = current_store.knowledge_documents.get(import_job.get("document_id"))
            if document is not None and not document_is_readable(current_store, user, document):
                continue
        items.append(import_job_response(current_store, import_job))

    items.sort(key=lambda item: (item.get("created_at", ""), item["id"]), reverse=True)
    return {
        "filters": {
            "document_id": document_id,
            "knowledge_space_id": knowledge_space_id,
            "status": status,
        },
        "items": items,
        "total": len(items),
    }


def decode_upload_content(content_base64: str) -> bytes:
    try:
        return base64.b64decode(content_base64.encode("ascii"), validate=True)
    except Exception as exc:  # noqa: BLE001
        raise api_error(400, "VALIDATION_ERROR", "content_base64 is invalid") from exc


def create_asset_record(
    *,
    asset_type: str = "original",
    content: bytes,
    current_store: Any,
    document_id: str,
    filename: str,
    metadata: dict[str, Any] | None = None,
    mime_type: str,
    space_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    settings = get_settings()
    digest = hashlib.sha256(content).hexdigest()
    object_key = f"knowledge/{space_id}/{document_id}/v1/{asset_type}/{digest}/{filename}"
    bucket = settings.object_storage_bucket
    for existing_asset in current_store.knowledge_assets.values():
        if existing_asset.get("bucket") != bucket or existing_asset.get("object_key") != object_key:
            continue
        if metadata:
            updated_asset = {
                **existing_asset,
                "metadata": {
                    **dict(existing_asset.get("metadata") or {}),
                    **dict(metadata),
                },
                "updated_at": now_iso(),
            }
            put_knowledge_asset_to_memory(current_store, updated_asset)
            return dict(updated_asset)
        return dict(existing_asset)
    asset_id = current_store.new_id("knowledge_asset")
    storage = object_storage()
    stored = storage.put_bytes(
        bucket=bucket,
        content=content,
        mime_type=mime_type,
        object_key=object_key,
    )
    timestamp = now_iso()
    asset = {
        "id": asset_id,
        "knowledge_space_id": space_id,
        "document_id": document_id,
        "asset_type": asset_type,
        "storage_provider": storage.provider,
        "bucket": stored.bucket,
        "object_key": stored.object_key,
        "content_hash": digest,
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": stored.size_bytes,
        "metadata": dict(metadata or {}),
        "created_by": user["id"],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    put_knowledge_asset_to_memory(current_store, asset)
    return asset


def normalize_parser_engine(parser_engine: str | None, mime_type: str | None) -> str:
    if parser_engine:
        normalized = parser_engine.strip()
    elif mime_type in {"text/markdown", "text/x-markdown"}:
        normalized = "markdown"
    elif mime_type == "application/pdf":
        normalized = "pdf_text"
    else:
        normalized = "plain_text"
    if normalized not in SUPPORTED_PARSER_ENGINES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported parser_engine")
    return normalized


def normalize_chunk_strategy(chunk_strategy: str | None) -> str:
    normalized = (chunk_strategy or "simple_text").strip()
    if normalized not in SUPPORTED_CHUNK_STRATEGIES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported chunk_strategy")
    return normalized


def _json_asset_content(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


def _normalized_number(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _source_metadata_for_content(
    source_map: list[dict[str, Any]],
    content: str,
) -> dict[str, Any]:
    for source in source_map:
        match_text = str(source.get("match_text") or "").strip()
        if not match_text:
            continue
        if match_text in content or content in match_text:
            return dict(source.get("metadata") or {})
    return {}


def _parse_ocr_json_payload(payload: Any, *, filename: str, parser_engine: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("OCR_JSON_INVALID")
    pages = payload.get("pages")
    normalized_pages: list[dict[str, Any]] = []
    markdown_sections: list[str] = []
    source_map: list[dict[str, Any]] = []
    image_count = 0
    if isinstance(pages, list):
        for index, page in enumerate(pages, start=1):
            if not isinstance(page, dict):
                continue
            page_text = str(page.get("text", "")).strip()
            if not page_text:
                continue
            page_number = _normalized_number(
                page.get("page_number", page.get("page")),
                index,
            )
            images = page.get("images") if isinstance(page.get("images"), list) else []
            tables = page.get("tables") if isinstance(page.get("tables"), list) else []
            image_refs = [
                str(
                    image.get("id")
                    or image.get("image_id")
                    or image.get("name")
                    or image.get("filename")
                    or index
                )
                for image in images
                if isinstance(image, dict)
            ]
            image_count += len(images)
            normalized_pages.append(
                {
                    "page_number": page_number,
                    "text": page_text,
                    "image_count": len(images),
                    "image_refs": image_refs,
                    "table_count": len(tables),
                }
            )
            markdown_sections.append(f"## Page {page_number}\n\n{page_text}")
            source_map.append(
                {
                    "match_text": page_text,
                    "metadata": {
                        "image_count": len(images),
                        "image_refs": image_refs,
                        "page_number": page_number,
                        "source_asset_type": "ocr_json",
                        "source_kind": "ocr_page",
                        "table_count": len(tables),
                    },
                }
            )
    else:
        page_text = str(payload.get("text", "")).strip()
        if page_text:
            normalized_pages.append(
                {
                    "page_number": 1,
                    "text": page_text,
                    "image_count": 0,
                    "table_count": 0,
                }
            )
            markdown_sections.append(page_text)
            source_map.append(
                {
                    "match_text": page_text,
                    "metadata": {
                        "page_number": 1,
                        "source_asset_type": "ocr_json",
                        "source_kind": "ocr_page",
                    },
                }
            )
    if not markdown_sections:
        raise ValueError("OCR_TEXT_EMPTY")
    normalized_payload = {
        "parser_engine": parser_engine,
        "pages": normalized_pages,
    }
    return {
        "asset_type": "parsed_markdown",
        "content": "\n\n".join(markdown_sections),
        "filename": f"{filename}.ocr.md",
        "mime_type": "text/markdown",
        "metadata": {
            "image_count": image_count,
            "page_count": len(normalized_pages),
            "parser_engine": parser_engine,
            "source_asset_type": "ocr_json",
        },
        "sidecar_assets": [
            {
                "asset_type": "ocr_json",
                "content": _json_asset_content(normalized_payload),
                "filename": f"{filename}.ocr.json",
                "mime_type": "application/json",
                "metadata": {
                    "image_count": image_count,
                    "page_count": len(normalized_pages),
                    "parser_engine": parser_engine,
                },
            }
        ],
        "source_map": source_map,
    }


def _normalized_table_specs(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [{"name": "Table 1", "rows": payload}]
    if not isinstance(payload, dict):
        raise ValueError("TABLE_JSON_INVALID")
    tables = payload.get("tables")
    if isinstance(tables, list):
        return [
            {
                "name": str(table.get("name") or f"Table {index}").strip(),
                "rows": table.get("rows", []),
            }
            for index, table in enumerate(tables, start=1)
            if isinstance(table, dict)
        ]
    return [
        {
            "name": str(payload.get("name") or "Table 1").strip(),
            "rows": payload.get("rows", []),
        }
    ]


def _parse_table_json_payload(payload: Any, *, filename: str, parser_engine: str) -> dict[str, Any]:
    markdown_sections: list[str] = []
    normalized_tables: list[dict[str, Any]] = []
    source_map: list[dict[str, Any]] = []
    all_columns: set[str] = set()
    for table_index, table_spec in enumerate(_normalized_table_specs(payload), start=1):
        rows = table_spec.get("rows")
        if not isinstance(rows, list) or not rows:
            continue
        row_dicts = [row for row in rows if isinstance(row, dict)]
        if not row_dicts:
            continue
        columns = sorted({key for row in row_dicts for key in row})
        if not columns:
            continue
        all_columns.update(columns)
        header = "| " + " | ".join(columns) + " |"
        divider = "| " + " | ".join(["---"] * len(columns)) + " |"
        body = [
            "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |"
            for row in row_dicts
        ]
        table_name = str(table_spec.get("name") or f"Table {table_index}").strip()
        table_markdown = "\n".join([header, divider, *body])
        markdown_sections.append(f"## Table {table_index}: {table_name}\n\n{table_markdown}")
        normalized_tables.append(
            {
                "columns": columns,
                "name": table_name,
                "rows": row_dicts,
                "table_index": table_index,
            }
        )
        source_map.append(
            {
                "match_text": table_markdown,
                "metadata": {
                    "columns": columns,
                    "source_asset_type": "table_json",
                    "source_kind": "table",
                    "table_index": table_index,
                    "table_name": table_name,
                },
            }
        )
    if not markdown_sections:
        raise ValueError("TABLE_EMPTY")
    normalized_payload = {
        "parser_engine": parser_engine,
        "tables": normalized_tables,
    }
    columns = sorted(all_columns)
    return {
        "asset_type": "parsed_markdown",
        "content": "\n\n".join(markdown_sections),
        "filename": f"{filename}.table.md",
        "mime_type": "text/markdown",
        "metadata": {
            "columns": columns,
            "parser_engine": parser_engine,
            "source_asset_type": "table_json",
            "table_count": len(normalized_tables),
        },
        "sidecar_assets": [
            {
                "asset_type": "table_json",
                "content": _json_asset_content(normalized_payload),
                "filename": f"{filename}.table.json",
                "mime_type": "application/json",
                "metadata": {
                    "columns": columns,
                    "parser_engine": parser_engine,
                    "table_count": len(normalized_tables),
                },
            }
        ],
        "source_map": source_map,
    }


def parse_asset_content(
    *,
    content: bytes,
    filename: str,
    mime_type: str,
    parser_engine: str,
) -> dict[str, Any]:
    text = content.decode("utf-8", errors="replace").strip()
    if parser_engine == "plain_text":
        if not text:
            raise ValueError("NO_INDEXABLE_CONTENT")
        return {
            "asset_type": "parsed_markdown",
            "content": text,
            "filename": f"{filename}.parsed.md",
            "mime_type": "text/markdown",
            "metadata": {"parser_engine": parser_engine},
        }
    if parser_engine == "markdown":
        if not text:
            raise ValueError("NO_INDEXABLE_CONTENT")
        return {
            "asset_type": "parsed_markdown",
            "content": text,
            "filename": f"{filename}.parsed.md",
            "mime_type": "text/markdown",
            "metadata": {"parser_engine": parser_engine, "structure": "markdown"},
        }
    if parser_engine == "pdf_text":
        printable = "".join(char if char.isprintable() or char.isspace() else " " for char in text)
        page_texts = [
            "\n".join(line.strip() for line in page.splitlines() if line.strip())
            for page in printable.split("\f")
        ]
        page_texts = [page for page in page_texts if page]
        normalized = "\n\n".join(
            f"## Page {index}\n\n{page}" if len(page_texts) > 1 else page
            for index, page in enumerate(page_texts, start=1)
        )
        if not normalized:
            raise ValueError("PDF_TEXT_EMPTY")
        return {
            "asset_type": "parsed_markdown",
            "content": normalized,
            "filename": f"{filename}.parsed.md",
            "mime_type": "text/markdown",
            "metadata": {
                "page_count": len(page_texts),
                "parser_engine": parser_engine,
                "source_mime_type": mime_type,
            },
            "source_map": [
                {
                    "match_text": page,
                    "metadata": {"page_number": index, "source_kind": "pdf_page"},
                }
                for index, page in enumerate(page_texts, start=1)
            ],
        }
    if parser_engine == "ocr_json":
        return _parse_ocr_json_payload(
            json.loads(text),
            filename=filename,
            parser_engine=parser_engine,
        )
    if parser_engine == "table_json":
        return _parse_table_json_payload(
            json.loads(text),
            filename=filename,
            parser_engine=parser_engine,
        )
    raise ValueError("UNSUPPORTED_PARSER")


def upload_knowledge_document_result(
    *,
    content_base64: str,
    current_store: Any,
    doc_type: str,
    filename: str,
    folder_id: str | None,
    knowledge_space_id: str,
    mime_type: str,
    parser_engine: str | None = None,
    chunk_strategy: str | None = None,
    tags: list[str],
    title: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_space_access(current_store, user, space_id=knowledge_space_id, required="write")
    if folder_id is not None:
        folder = current_store.knowledge_folders.get(folder_id)
        if (
            folder is None
            or folder.get("knowledge_space_id") != knowledge_space_id
            or not folder_is_effectively_active(current_store, folder_id)
        ):
            raise api_error(404, "NOT_FOUND", "Knowledge folder not found")
    content = decode_upload_content(content_base64)
    if not content:
        raise api_error(400, "VALIDATION_ERROR", "uploaded content is empty")
    normalized_parser = normalize_parser_engine(parser_engine, mime_type)
    normalized_chunk_strategy = normalize_chunk_strategy(chunk_strategy)
    preview_content = content.decode("utf-8", errors="replace").strip()

    timestamp = now_iso()
    document_id = current_store.new_id("knowledge")
    document = {
        "id": document_id,
        "title": non_blank(title, "title"),
        "content": preview_content,
        "source_type": "upload",
        "doc_type": doc_type or "manual",
        "product_id": None,
        "knowledge_space_id": knowledge_space_id,
        "folder_id": folder_id,
        "permission_roles": ["admin"],
        "permission_scope": {"knowledge_space_id": knowledge_space_id},
        "tags": tags,
        "index_status": "importing",
        "index_error": None,
        "vector_index_error": None,
        "created_by": user["id"],
        "created_at": timestamp,
        "updated_at": timestamp,
        "document_version": 1,
        "active_chunk_set_id": None,
        "parser_engine": normalized_parser,
        "chunk_strategy": normalized_chunk_strategy,
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
    import_job = {
        "id": current_store.new_id("knowledge_import_job"),
        "document_id": document_id,
        "source_asset_id": asset["id"],
        "parser_engine": normalized_parser,
        "chunk_strategy": normalized_chunk_strategy,
        "status": "queued",
        "progress": 0,
        "error_code": None,
        "error_message": None,
        "created_by": user["id"],
        "locked_by": None,
        "locked_until": None,
        "attempt_count": 0,
        "started_at": None,
        "finished_at": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    put_knowledge_import_job_to_memory(current_store, import_job)

    if not uses_repository_context(current_store):
        put_knowledge_document_to_memory(current_store, document)
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_document.uploaded",
        subject_id=document_id,
        subject_type="knowledge_document",
    )
    put_knowledge_document_to_memory(current_store, document)
    persist_knowledge_payload(current_store, audit_event=audit_event)
    return {
        "asset": dict(asset),
        "document": knowledge_document_response(current_store, document, []),
        "import_job": dict(import_job),
    }


def _space_id_for_document_or_asset(
    current_store: Any,
    *,
    document: dict[str, Any],
    source_asset: dict[str, Any] | None,
) -> str | None:
    return document.get("knowledge_space_id") or (
        source_asset.get("knowledge_space_id") if source_asset is not None else None
    )


def _save_import_processing_state(
    current_store: Any,
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    persist_knowledge_payload(current_store, audit_event=audit_event)


def _mark_import_job_failed(
    *,
    current_store: Any,
    document: dict[str, Any],
    import_job: dict[str, Any],
    error_code: str,
    error_message: str,
) -> dict[str, Any]:
    timestamp = now_iso()
    failed_job = {
        **import_job,
        "status": "failed",
        "progress": 80,
        "error_code": error_code,
        "error_message": error_message,
        "locked_by": None,
        "locked_until": None,
        "finished_at": timestamp,
        "updated_at": timestamp,
    }
    put_knowledge_import_job_to_memory(current_store, failed_job)
    failed_document = {
        **document,
        "index_status": "index_failed",
        "index_error": error_message,
        "updated_at": timestamp,
    }
    put_knowledge_document_to_memory(current_store, failed_document)
    return failed_job


def run_knowledge_import_job_result(
    *,
    current_store: Any,
    job_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    import_job = get_knowledge_import_job_from_memory(current_store, job_id)
    if import_job is None:
        raise api_error(404, "NOT_FOUND", "Knowledge import job not found")
    document = current_store.knowledge_documents.get(import_job.get("document_id"))
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    source_asset = current_store.knowledge_assets.get(import_job.get("source_asset_id"))
    space_id = _space_id_for_document_or_asset(
        current_store,
        document=document,
        source_asset=source_asset,
    )
    if space_id:
        ensure_space_access(current_store, user, space_id=space_id, required="write")
    if import_job.get("status") not in IMPORT_JOB_RUNNABLE_STATUSES:
        raise api_error(409, "IMPORT_JOB_STATE_INVALID", "Import job cannot be run")
    if source_asset is None:
        raise api_error(404, "NOT_FOUND", "Knowledge source asset not found")

    timestamp = now_iso()
    running_job = {
        **import_job,
        "status": "parsing",
        "progress": 20,
        "started_at": import_job.get("started_at") or timestamp,
        "finished_at": None,
        "error_code": None,
        "error_message": None,
        "updated_at": timestamp,
    }
    put_knowledge_import_job_to_memory(current_store, running_job)
    document = {
        **document,
        "index_status": "importing",
        "index_error": None,
        "vector_index_error": None,
        "updated_at": timestamp,
    }
    put_knowledge_document_to_memory(current_store, document)

    try:
        source_content = object_storage().get_bytes(
            bucket=source_asset["bucket"],
            object_key=source_asset["object_key"],
        )
        parsed = parse_asset_content(
            content=source_content,
            filename=source_asset.get("filename", document["id"]),
            mime_type=source_asset.get("mime_type", "application/octet-stream"),
            parser_engine=running_job.get("parser_engine", "plain_text"),
        )
        structured_assets: list[dict[str, Any]] = []
        structured_asset_by_type: dict[str, dict[str, Any]] = {}
        for sidecar in parsed.get("sidecar_assets") or []:
            structured_asset = create_asset_record(
                asset_type=sidecar["asset_type"],
                content=str(sidecar["content"]).encode(),
                current_store=current_store,
                document_id=document["id"],
                filename=sidecar["filename"],
                metadata=sidecar.get("metadata", {}),
                mime_type=sidecar["mime_type"],
                space_id=space_id or source_asset["knowledge_space_id"],
                user=user,
            )
            put_knowledge_asset_to_memory(current_store, structured_asset)
            structured_assets.append(structured_asset)
            structured_asset_by_type[structured_asset["asset_type"]] = structured_asset
        parsed_metadata = dict(parsed.get("metadata") or {})
        if structured_assets:
            parsed_metadata["structured_asset_ids"] = [
                asset["id"] for asset in structured_assets
            ]
        parsed_asset = create_asset_record(
            asset_type=parsed["asset_type"],
            content=parsed["content"].encode(),
            current_store=current_store,
            document_id=document["id"],
            filename=parsed["filename"],
            metadata=parsed_metadata,
            mime_type=parsed["mime_type"],
            space_id=space_id or source_asset["knowledge_space_id"],
            user=user,
        )
        put_knowledge_asset_to_memory(current_store, parsed_asset)
        chunk_set_id = current_store.new_id("knowledge_chunk_set")
        chunk_set = {
            "id": chunk_set_id,
            "document_id": document["id"],
            "source_asset_id": source_asset["id"],
            "parsed_asset_id": parsed_asset["id"],
            "parser_engine": running_job.get("parser_engine", "plain_text"),
            "parser_version": "v1",
            "chunk_strategy": running_job.get("chunk_strategy", "simple_text"),
            "embedding_model": None,
            "embedding_dimension": None,
            "status": "building",
            "created_by": user["id"],
            "created_at": timestamp,
            "index_status": None,
            "vector_index_error": None,
            "updated_at": timestamp,
            "activated_at": None,
        }
        put_knowledge_chunk_set_to_memory(current_store, chunk_set_id, chunk_set)
        indexing_document = {
            **document,
            "content": parsed["content"],
            "parsed_asset_id": parsed_asset["id"],
            "parser_engine": running_job.get("parser_engine", "plain_text"),
            "chunk_strategy": running_job.get("chunk_strategy", "simple_text"),
        }
        _model_log_start_index = len(current_store.model_gateway_logs)
        indexed_document, chunks = replace_knowledge_chunks_result(
            current_store,
            indexing_document,
        )
        chunk_id_map = {
            chunk["id"]: f"{chunk_set_id}_chunk_{chunk['chunk_index']:03d}"
            for chunk in chunks
        }
        for chunk in chunks:
            old_parent_chunk_id = chunk.get("parent_chunk_id")
            chunk["id"] = chunk_id_map[chunk["id"]]
            if old_parent_chunk_id:
                chunk["parent_chunk_id"] = chunk_id_map.get(
                    old_parent_chunk_id,
                    old_parent_chunk_id,
                )
            chunk["chunk_set_id"] = chunk_set_id
            source_metadata = _source_metadata_for_content(
                parsed.get("source_map") or [],
                chunk.get("content", ""),
            )
            source_asset_type = source_metadata.get("source_asset_type")
            if source_asset_type in structured_asset_by_type:
                source_metadata["structured_asset_id"] = structured_asset_by_type[
                    source_asset_type
                ]["id"]
            chunk.setdefault("metadata", {})["knowledge_space_id"] = document.get(
                "knowledge_space_id",
            )
            chunk["metadata"].update(source_metadata)
            chunk["metadata"]["folder_id"] = document.get("folder_id")
            chunk["metadata"]["source_asset_id"] = source_asset["id"]
            chunk["metadata"]["parsed_asset_id"] = parsed_asset["id"]
            chunk["metadata"]["chunk_set_id"] = chunk_set_id
        previous_active_id = document.get("active_chunk_set_id")
        next_index_status = indexed_document["index_status"]
        if (
            next_index_status != "index_failed"
            and previous_active_id
            and get_knowledge_chunk_set_from_memory(current_store, previous_active_id)
            is not None
        ):
            previous_active = get_knowledge_chunk_set_from_memory(
                current_store,
                previous_active_id,
            )
            put_knowledge_chunk_set_to_memory(current_store, previous_active_id, {
                **previous_active,
                "status": "archived",
                "updated_at": now_iso(),
            })
        chunk_set = {
            **chunk_set,
            "status": "active" if next_index_status != "index_failed" else "failed",
            "embedding_model": (
                chunks[0].get("metadata", {}).get("embedding_model") if chunks else None
            ),
            "embedding_dimension": (
                chunks[0].get("metadata", {}).get("embedding_dimension") if chunks else None
            ),
            "index_status": next_index_status,
            "vector_index_error": indexed_document.get("vector_index_error"),
            "activated_at": now_iso()
            if next_index_status != "index_failed"
            else None,
            "updated_at": now_iso(),
        }
        put_knowledge_chunk_set_to_memory(current_store, chunk_set_id, chunk_set)
        indexed_document = {
            **indexed_document,
            "active_chunk_set_id": chunk_set_id
            if indexed_document["index_status"] != "index_failed"
            else previous_active_id,
            "source_asset_id": source_asset["id"],
            "parsed_asset_id": parsed_asset["id"],
            "updated_at": now_iso(),
        }
        put_knowledge_document_to_memory(current_store, indexed_document)
        for chunk in chunks:
            put_knowledge_chunk_to_memory(current_store, chunk)
        completed_job = {
            **running_job,
            "status": "completed"
            if next_index_status != "index_failed"
            else "failed",
            "progress": 100 if next_index_status != "index_failed" else 80,
            "error_code": indexed_document.get("index_error"),
            "error_message": indexed_document.get("index_error"),
            "locked_by": None,
            "locked_until": None,
            "finished_at": now_iso(),
            "updated_at": now_iso(),
        }
        put_knowledge_import_job_to_memory(current_store, completed_job)
        if not uses_repository_context(current_store):
            apply_knowledge_document_to_memory(current_store, indexed_document, chunks)
        audit_event = record_audit_event(
            current_store,
            actor_id=user["id"],
            event_type="knowledge_import_job.completed"
            if completed_job["status"] == "completed"
            else "knowledge_import_job.failed",
            subject_id=job_id,
            subject_type="knowledge_import_job",
        )
        _save_import_processing_state(current_store, audit_event=audit_event)
        return {
            "document": knowledge_document_response(current_store, indexed_document, chunks),
            "import_job": import_job_response(current_store, completed_job),
            "chunk_set": dict(chunk_set),
            "parsed_asset": dict(parsed_asset),
            "parsed_assets": [dict(asset) for asset in [*structured_assets, parsed_asset]],
        }
    except Exception as exc:  # noqa: BLE001
        failed_job = _mark_import_job_failed(
            current_store=current_store,
            document=document,
            import_job=running_job,
            error_code=exc.__class__.__name__,
            error_message=str(exc) or "Knowledge import failed",
        )
        audit_event = record_audit_event(
            current_store,
            actor_id=user["id"],
            event_type="knowledge_import_job.failed",
            subject_id=job_id,
            subject_type="knowledge_import_job",
        )
        _save_import_processing_state(current_store, audit_event=audit_event)
        failed_document = current_store.knowledge_documents[document["id"]]
        return {
            "document": knowledge_document_response(current_store, failed_document, []),
            "import_job": import_job_response(current_store, failed_job),
        }


def retry_knowledge_import_job_result(
    *,
    current_store: Any,
    job_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    import_job = get_knowledge_import_job_from_memory(current_store, job_id)
    if import_job is None:
        raise api_error(404, "NOT_FOUND", "Knowledge import job not found")
    document = current_store.knowledge_documents.get(import_job.get("document_id"))
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    space_id = document.get("knowledge_space_id") or _import_job_space_id(
        current_store=current_store,
        import_job=import_job,
    )
    if space_id:
        ensure_space_access(current_store, user, space_id=space_id, required="write")
    if import_job.get("status") not in IMPORT_JOB_RETRYABLE_STATUSES:
        raise api_error(409, "IMPORT_JOB_STATE_INVALID", "Import job cannot be retried")
    retried_job = {
        **import_job,
        "status": "queued",
        "progress": 0,
        "error_code": None,
        "error_message": None,
        "locked_by": None,
        "locked_until": None,
        "started_at": None,
        "finished_at": None,
        "updated_at": now_iso(),
    }
    put_knowledge_import_job_to_memory(current_store, retried_job)
    document = {
        **document,
        "index_status": "importing",
        "index_error": None,
        "vector_index_error": None,
        "updated_at": now_iso(),
    }
    put_knowledge_document_to_memory(current_store, document)
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_import_job.retried",
        subject_id=job_id,
        subject_type="knowledge_import_job",
    )
    _save_import_processing_state(current_store, audit_event=audit_event)
    return {
        "document": knowledge_document_response(current_store, document, []),
        "import_job": import_job_response(current_store, retried_job),
    }


def cancel_knowledge_import_job_result(
    *,
    current_store: Any,
    job_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    import_job = get_knowledge_import_job_from_memory(current_store, job_id)
    if import_job is None:
        raise api_error(404, "NOT_FOUND", "Knowledge import job not found")
    document = current_store.knowledge_documents.get(import_job.get("document_id"))
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    space_id = document.get("knowledge_space_id")
    if space_id:
        ensure_space_access(current_store, user, space_id=space_id, required="write")
    if import_job.get("status") not in {"queued", "uploaded", "failed"}:
        raise api_error(409, "IMPORT_JOB_STATE_INVALID", "Import job cannot be cancelled")
    cancelled_job = {
        **import_job,
        "status": "cancelled",
        "progress": import_job.get("progress", 0),
        "locked_by": None,
        "locked_until": None,
        "finished_at": now_iso(),
        "updated_at": now_iso(),
    }
    put_knowledge_import_job_to_memory(current_store, cancelled_job)
    document = {
        **document,
        "index_status": (
            "archived" if not document.get("active_chunk_set_id") else document["index_status"]
        ),
        "updated_at": now_iso(),
    }
    put_knowledge_document_to_memory(current_store, document)
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_import_job.cancelled",
        subject_id=job_id,
        subject_type="knowledge_import_job",
    )
    _save_import_processing_state(current_store, audit_event=audit_event)
    return {
        "document": knowledge_document_response(current_store, document, []),
        "import_job": import_job_response(current_store, cancelled_job),
    }


def list_knowledge_chunk_sets_result(
    *,
    current_store: Any,
    document_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    document = current_store.knowledge_documents.get(document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    if not document_is_readable(current_store, user, document):
        raise api_error(403, "FORBIDDEN", "Knowledge document permission denied")
    items = [
        dict(chunk_set)
        for chunk_set in current_store.knowledge_chunk_sets.values()
        if chunk_set.get("document_id") == document_id
    ]
    active_id = document.get("active_chunk_set_id")
    for item in items:
        item["is_active"] = item["id"] == active_id
        item["chunk_count"] = len(
            [
                chunk
                for chunk in current_store.knowledge_chunks.values()
                if chunk.get("chunk_set_id") == item["id"]
            ]
        )
    items.sort(
        key=lambda item: (
            0 if item.get("is_active") else 1,
            item.get("created_at", ""),
            item["id"],
        )
    )
    return {"document_id": document_id, "items": items, "total": len(items)}


def list_knowledge_chunks_result(
    *,
    current_store: Any,
    document_id: str,
    chunk_set_id: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    document = current_store.knowledge_documents.get(document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    if not document_is_readable(current_store, user, document):
        raise api_error(403, "FORBIDDEN", "Knowledge document permission denied")
    target_chunk_set_id = chunk_set_id or document.get("active_chunk_set_id")
    items = [
        dict(chunk)
        for chunk in current_store.knowledge_chunks.values()
        if chunk.get("document_id") == document_id
        and (target_chunk_set_id is None or chunk.get("chunk_set_id") == target_chunk_set_id)
    ]
    items.sort(key=lambda item: (item.get("chunk_index", 0), item["id"]))
    parent_content_by_id = {item["id"]: item["content"] for item in items}
    for item in items:
        parent_id = item.get("parent_chunk_id")
        if parent_id:
            item["parent_content"] = parent_content_by_id.get(parent_id) or item.get(
                "metadata",
                {},
            ).get("parent_content")
    return {
        "chunk_set_id": target_chunk_set_id,
        "document_id": document_id,
        "items": items,
        "total": len(items),
    }


def activate_knowledge_chunk_set_result(
    *,
    current_store: Any,
    document_id: str,
    chunk_set_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    document = current_store.knowledge_documents.get(document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    space_id = document.get("knowledge_space_id")
    if space_id:
        ensure_space_access(current_store, user, space_id=space_id, required="write")
    chunk_set = current_store.knowledge_chunk_sets.get(chunk_set_id)
    if chunk_set is None or chunk_set.get("document_id") != document_id:
        raise api_error(404, "NOT_FOUND", "Knowledge chunk set not found")
    if chunk_set.get("status") not in {"active", "archived"}:
        raise api_error(409, "CHUNK_SET_STATE_INVALID", "Knowledge chunk set cannot be activated")
    for existing_id, existing in list(current_store.knowledge_chunk_sets.items()):
        if existing.get("document_id") != document_id:
            continue
        put_knowledge_chunk_set_to_memory(current_store, existing_id, {
            **existing,
            "status": "active" if existing_id == chunk_set_id else "archived",
            "activated_at": (
                now_iso() if existing_id == chunk_set_id else existing.get("activated_at")
            ),
            "updated_at": now_iso(),
        })
    restored_index_status = chunk_set.get("index_status") or (
        "vector_indexed" if chunk_set.get("embedding_model") else "text_indexed"
    )
    updated_document = {
        **document,
        "active_chunk_set_id": chunk_set_id,
        "parsed_asset_id": chunk_set.get("parsed_asset_id") or document.get("parsed_asset_id"),
        "parser_engine": chunk_set.get("parser_engine"),
        "chunk_strategy": chunk_set.get("chunk_strategy"),
        "index_status": restored_index_status,
        "index_error": None,
        "vector_index_error": chunk_set.get("vector_index_error"),
        "updated_at": now_iso(),
    }
    put_knowledge_document_to_memory(current_store, updated_document)
    chunks = [
        chunk
        for chunk in current_store.knowledge_chunks.values()
        if chunk.get("document_id") == document_id and chunk.get("chunk_set_id") == chunk_set_id
    ]
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_chunk_set.activated",
        subject_id=chunk_set_id,
        subject_type="knowledge_chunk_set",
    )
    _save_import_processing_state(current_store, audit_event=audit_event)
    return {
        "chunk_set": dict(current_store.knowledge_chunk_sets[chunk_set_id]),
        "document": knowledge_document_response(current_store, updated_document, chunks),
    }


def reparse_knowledge_document_result(
    *,
    current_store: Any,
    document_id: str,
    parser_engine: str | None,
    chunk_strategy: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    document = current_store.knowledge_documents.get(document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    space_id = document.get("knowledge_space_id")
    if space_id:
        ensure_space_access(current_store, user, space_id=space_id, required="write")
    source_asset_id = document.get("source_asset_id")
    if not source_asset_id or source_asset_id not in current_store.knowledge_assets:
        raise api_error(404, "NOT_FOUND", "Knowledge source asset not found")
    source_asset = current_store.knowledge_assets[source_asset_id]
    normalized_parser = normalize_parser_engine(
        parser_engine or document.get("parser_engine"),
        source_asset.get("mime_type"),
    )
    normalized_strategy = normalize_chunk_strategy(chunk_strategy or document.get("chunk_strategy"))
    timestamp = now_iso()
    import_job = {
        "id": current_store.new_id("knowledge_import_job"),
        "document_id": document_id,
        "source_asset_id": source_asset_id,
        "parser_engine": normalized_parser,
        "chunk_strategy": normalized_strategy,
        "status": "queued",
        "progress": 0,
        "error_code": None,
        "error_message": None,
        "created_by": user["id"],
        "locked_by": None,
        "locked_until": None,
        "attempt_count": 0,
        "started_at": None,
        "finished_at": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    put_knowledge_import_job_to_memory(current_store, import_job)
    updated_document = {
        **document,
        "index_status": "importing",
        "parser_engine": normalized_parser,
        "chunk_strategy": normalized_strategy,
        "updated_at": timestamp,
    }
    put_knowledge_document_to_memory(current_store, updated_document)
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_document.reparse_requested",
        subject_id=document_id,
        subject_type="knowledge_document",
    )
    _save_import_processing_state(current_store, audit_event=audit_event)
    return {
        "document": knowledge_document_response(
            current_store,
            updated_document,
            [],
        ),
        "import_job": import_job_response(current_store, import_job),
    }


def batch_move_knowledge_documents_result(
    *,
    current_store: Any,
    document_ids: list[str],
    folder_id: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    if not document_ids:
        raise api_error(400, "VALIDATION_ERROR", "document_ids is required")
    target_folder = None
    if folder_id is not None:
        target_folder = current_store.knowledge_folders.get(folder_id)
        if target_folder is None or not folder_is_effectively_active(current_store, folder_id):
            raise api_error(404, "NOT_FOUND", "Knowledge folder not found")
        ensure_space_access(
            current_store,
            user,
            space_id=target_folder["knowledge_space_id"],
            required="write",
        )
    updated: list[str] = []
    skipped: list[dict[str, str]] = []
    for document_id in document_ids:
        document = current_store.knowledge_documents.get(document_id)
        if document is None:
            skipped.append({"id": document_id, "reason": "not_found"})
            continue
        space_id = document.get("knowledge_space_id")
        if not space_id:
            skipped.append({"id": document_id, "reason": "missing_space"})
            continue
        if target_folder is not None and target_folder.get("knowledge_space_id") != space_id:
            skipped.append({"id": document_id, "reason": "folder_space_mismatch"})
            continue
        ensure_space_access(current_store, user, space_id=space_id, required="write")
        moved_document = {
            **document,
            "folder_id": folder_id,
            "updated_at": now_iso(),
        }
        put_knowledge_document_to_memory(current_store, moved_document)
        updated.append(document_id)
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_document.batch_moved",
        subject_id=",".join(updated) if updated else "none",
        subject_type="knowledge_document",
    )
    _save_import_processing_state(current_store, audit_event=audit_event)
    return {"folder_id": folder_id, "skipped": skipped, "updated": updated}


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
