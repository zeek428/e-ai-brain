from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
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
from app.services.knowledge_multimodal_governance import (
    activate_document_version,
    create_document_version_record,
    fail_document_version,
    get_processing_profile,
    update_document_version_source,
    version_response,
)
from app.services.object_storage import object_storage
from app.services.product_scope import require_product_scope

WRITE_SPACE_ROLES = {"admin", "contributor", "maintainer"}
READ_SPACE_ROLES = WRITE_SPACE_ROLES | {"reader"}
IMPORT_JOB_RUNNABLE_STATUSES = {"queued", "uploaded", "failed"}
IMPORT_JOB_RETRYABLE_STATUSES = {"failed", "cancelled"}
SUPPORTED_PARSER_ENGINES = {
    "markdown",
    "multimodal",
    "ocr_json",
    "pdf_text",
    "plain_text",
    "table_json",
}
SUPPORTED_CHUNK_STRATEGIES = {"simple_text", "parent_child", "regex_section"}
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


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
            "knowledge_assets": _memory_collection(current_store, "knowledge_assets"),
            "knowledge_chunk_sets": _memory_collection(current_store, "knowledge_chunk_sets"),
            "knowledge_chunks": _memory_collection(current_store, "knowledge_chunks"),
            "knowledge_citation_feedback": _memory_collection(
                current_store,
                "knowledge_citation_feedback",
            ),
            "knowledge_deposits": _memory_collection(current_store, "knowledge_deposits"),
            "knowledge_document_versions": _memory_collection(
                current_store,
                "knowledge_document_versions",
            ),
            "knowledge_documents": _memory_collection(current_store, "knowledge_documents"),
            "knowledge_folders": _memory_collection(current_store, "knowledge_folders"),
            "knowledge_import_jobs": _memory_collection(current_store, "knowledge_import_jobs"),
            "knowledge_processing_profiles": _memory_collection(
                current_store,
                "knowledge_processing_profiles",
            ),
            "knowledge_space_members": _memory_collection(
                current_store,
                "knowledge_space_members",
            ),
            "knowledge_spaces": _memory_collection(current_store, "knowledge_spaces"),
            "audit_events": [audit_event] if audit_event is not None else [],
        }
    )


def _memory_collection(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _read_memory_collection(
    current_store: Any,
    collection_name: str,
) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def _read_memory_record(
    current_store: Any,
    collection_name: str,
    record_id: Any,
) -> dict[str, Any] | None:
    if record_id is None:
        return None
    record = _read_memory_collection(current_store, collection_name).get(str(record_id))
    return record if isinstance(record, dict) else None


def get_knowledge_import_job_from_memory(
    current_store: Any,
    job_id: str | None,
) -> dict[str, Any] | None:
    if not job_id:
        return None
    return _read_memory_record(current_store, "knowledge_import_jobs", job_id)


def put_knowledge_import_job_to_memory(
    current_store: Any,
    import_job: dict[str, Any],
) -> None:
    job_id = import_job.get("id")
    if job_id is None:
        return
    _memory_collection(current_store, "knowledge_import_jobs")[str(job_id)] = import_job


def put_knowledge_space_to_memory(current_store: Any, space: dict[str, Any]) -> None:
    space_id = space.get("id")
    if space_id is None:
        return
    _memory_collection(current_store, "knowledge_spaces")[str(space_id)] = space


def replace_knowledge_space_members_to_memory(
    current_store: Any,
    *,
    members: list[dict[str, Any]],
    space_id: str,
) -> None:
    collection = _memory_collection(current_store, "knowledge_space_members")
    for member_key in [
        key
        for key, value in collection.items()
        if value.get("knowledge_space_id") == space_id
    ]:
        collection.pop(member_key, None)
    for member in members:
        member_key = f"{space_id}:{member['user_id']}:{member['space_role']}"
        collection[member_key] = member


def put_knowledge_folder_to_memory(current_store: Any, folder: dict[str, Any]) -> None:
    folder_id = folder.get("id")
    if folder_id is None:
        return
    _memory_collection(current_store, "knowledge_folders")[str(folder_id)] = folder


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
    for member in _read_memory_collection(current_store, "knowledge_space_members").values():
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
    space = _read_memory_record(current_store, "knowledge_spaces", space_id)
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
    if _read_memory_record(current_store, "knowledge_spaces", space_id) is None:
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
        for space in _read_memory_collection(current_store, "knowledge_spaces").values()
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
    put_knowledge_space_to_memory(current_store, space)
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
        for space in _read_memory_collection(current_store, "knowledge_spaces").values()
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
    replace_knowledge_space_members_to_memory(
        current_store,
        members=normalized_members,
        space_id=space_id,
    )
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
        parent = _read_memory_record(current_store, "knowledge_folders", parent_id)
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
        parent = _read_memory_record(current_store, "knowledge_folders", parent_folder_id)
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
        "sort_order": len(_read_memory_collection(current_store, "knowledge_folders")) + 1,
        "created_by": user["id"],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    folder["path"] = folder_path(current_store, folder)
    put_knowledge_folder_to_memory(current_store, folder)
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
        for folder in _read_memory_collection(current_store, "knowledge_folders").values():
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
        folder = _read_memory_record(current_store, "knowledge_folders", current_id)
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
    folder = _read_memory_record(current_store, "knowledge_folders", folder_id)
    if folder is None:
        raise api_error(404, "NOT_FOUND", "Knowledge folder not found")
    space_id = folder["knowledge_space_id"]
    ensure_space_access(current_store, user, space_id=space_id, required="write")
    if status is not None and status not in {"active", "archived"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported folder status")
    if parent_folder_id_set and parent_folder_id is not None:
        parent = _read_memory_record(current_store, "knowledge_folders", parent_folder_id)
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
    put_knowledge_folder_to_memory(current_store, updated)
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
        for folder in _read_memory_collection(current_store, "knowledge_folders").values()
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
    document = _read_memory_record(current_store, "knowledge_documents", document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    if not document_is_readable(current_store, user, document):
        raise api_error(403, "FORBIDDEN", "Knowledge document permission denied")
    items = [
        dict(asset)
        for asset in _read_memory_collection(current_store, "knowledge_assets").values()
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
        document = _read_memory_record(current_store, "knowledge_documents", document_id)
        if document is not None:
            document_space_id = document.get("knowledge_space_id")
            if document_space_id:
                return document_space_id
    source_asset_id = import_job.get("source_asset_id")
    if source_asset_id:
        asset = _read_memory_record(current_store, "knowledge_assets", source_asset_id)
        if asset is not None:
            return asset.get("knowledge_space_id")
    return None


def import_job_response(current_store: Any, import_job: dict[str, Any]) -> dict[str, Any]:
    response = dict(import_job)
    document = _read_memory_record(
        current_store,
        "knowledge_documents",
        import_job.get("document_id"),
    )
    if document is not None:
        response["document_title"] = document.get("title")
        document_space_id = document.get("knowledge_space_id")
        if document_space_id:
            response["knowledge_space_id"] = document_space_id
        folder_id = document.get("folder_id")
        if folder_id:
            folder = _read_memory_record(current_store, "knowledge_folders", folder_id)
            if folder is not None:
                response["folder_id"] = folder_id
                response["folder_path"] = folder.get("path") or folder_path(current_store, folder)
    source_asset_id = import_job.get("source_asset_id")
    if source_asset_id:
        asset = _read_memory_record(current_store, "knowledge_assets", source_asset_id)
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
    for import_job in _read_memory_collection(current_store, "knowledge_import_jobs").values():
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
            document = _read_memory_record(
                current_store,
                "knowledge_documents",
                import_job.get("document_id"),
            )
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


def normalize_upload_filename(filename: str) -> str:
    original_name = Path(non_blank(filename, "filename")).name.strip()
    if original_name in {"", ".", ".."}:
        raise api_error(400, "VALIDATION_ERROR", "filename is invalid")
    normalized = SAFE_FILENAME_PATTERN.sub("_", original_name)
    return normalized[:180] or "upload.bin"


def _upload_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_upload_content(
    *,
    content: bytes,
    filename: str,
    mime_type: str,
) -> None:
    settings = get_settings()
    if not content:
        raise api_error(400, "VALIDATION_ERROR", "uploaded content is empty")
    if len(content) > settings.knowledge_upload_max_bytes:
        raise api_error(
            413,
            "KNOWLEDGE_UPLOAD_TOO_LARGE",
            "uploaded file exceeds configured size limit",
        )
    extension = _upload_extension(filename)
    if extension not in settings.knowledge_upload_allowed_extensions:
        raise api_error(400, "KNOWLEDGE_UPLOAD_TYPE_UNSUPPORTED", "file extension is not allowed")
    normalized_mime_type = (mime_type or "application/octet-stream").lower()
    if normalized_mime_type not in settings.knowledge_upload_allowed_mime_types:
        raise api_error(400, "KNOWLEDGE_UPLOAD_TYPE_UNSUPPORTED", "file mime type is not allowed")
    if extension == ".pdf" and not content.startswith(b"%PDF"):
        raise api_error(400, "KNOWLEDGE_PDF_INVALID", "PDF signature is invalid")
    if extension == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise api_error(400, "KNOWLEDGE_IMAGE_INVALID", "PNG signature is invalid")
    if extension in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise api_error(400, "KNOWLEDGE_IMAGE_INVALID", "JPEG signature is invalid")


def create_asset_record(
    *,
    asset_type: str = "original",
    bounding_boxes: list[Any] | None = None,
    content: bytes,
    current_store: Any,
    document_id: str,
    document_version_id: str | None = None,
    filename: str,
    metadata: dict[str, Any] | None = None,
    mime_type: str,
    page_number: int | None = None,
    provider_metadata: dict[str, Any] | None = None,
    space_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    settings = get_settings()
    digest = hashlib.sha256(content).hexdigest()
    version_segment = document_version_id or "legacy-v1"
    object_key = (
        f"knowledge/{space_id}/{document_id}/{version_segment}/"
        f"{asset_type}/{digest}/{filename}"
    )
    bucket = settings.object_storage_bucket
    for existing_asset in _read_memory_collection(current_store, "knowledge_assets").values():
        if existing_asset.get("bucket") != bucket or existing_asset.get("object_key") != object_key:
            continue
        if metadata:
            updated_asset = {
                **existing_asset,
                "metadata": {
                    **dict(existing_asset.get("metadata") or {}),
                    **dict(metadata),
                },
                "document_version_id": document_version_id
                or existing_asset.get("document_version_id"),
                "page_number": page_number
                if page_number is not None
                else existing_asset.get("page_number"),
                "bounding_boxes": list(
                    bounding_boxes or existing_asset.get("bounding_boxes") or []
                ),
                "provider_metadata": {
                    **dict(existing_asset.get("provider_metadata") or {}),
                    **dict(provider_metadata or {}),
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
        "document_version_id": document_version_id,
        "asset_type": asset_type,
        "storage_provider": storage.provider,
        "bucket": stored.bucket,
        "object_key": stored.object_key,
        "content_hash": digest,
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": stored.size_bytes,
        "metadata": dict(metadata or {}),
        "page_number": page_number,
        "bounding_boxes": list(bounding_boxes or []),
        "provider_metadata": dict(provider_metadata or {}),
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
    elif str(mime_type or "").startswith("image/"):
        normalized = "multimodal"
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
                        "modality": "multimodal" if images or tables else "text",
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
                        "modality": "text",
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
                    "modality": "table",
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


def _extract_pdf_pages(content: bytes) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is part of runtime install
        raise ValueError("PDF_PARSER_UNAVAILABLE") from exc
    try:
        reader = PdfReader(BytesIO(content))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
            if normalized:
                pages.append(normalized)
        return pages
    except Exception as exc:  # noqa: BLE001
        raise ValueError("PDF_PARSE_FAILED") from exc


def parse_asset_content(
    *,
    content: bytes,
    filename: str,
    mime_type: str,
    parser_engine: str,
) -> dict[str, Any]:
    if parser_engine == "plain_text":
        text = content.decode("utf-8", errors="replace").strip()
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
        text = content.decode("utf-8", errors="replace").strip()
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
        page_texts = _extract_pdf_pages(content)
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
        text = content.decode("utf-8", errors="replace").strip()
        return _parse_ocr_json_payload(
            json.loads(text),
            filename=filename,
            parser_engine=parser_engine,
        )
    if parser_engine == "table_json":
        text = content.decode("utf-8", errors="replace").strip()
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
    processing_profile_id: str | None = None,
    product_id: str | None = None,
    expires_in_days: int | None = None,
    tags: list[str],
    title: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    content = decode_upload_content(content_base64)
    return upload_knowledge_document_bytes_result(
        content=content,
        current_store=current_store,
        doc_type=doc_type,
        filename=filename,
        folder_id=folder_id,
        knowledge_space_id=knowledge_space_id,
        mime_type=mime_type,
        parser_engine=parser_engine,
        chunk_strategy=chunk_strategy,
        processing_profile_id=processing_profile_id,
        product_id=product_id,
        expires_in_days=expires_in_days,
        tags=tags,
        title=title,
        user=user,
    )


def upload_knowledge_document_bytes_result(
    *,
    content: bytes,
    current_store: Any,
    doc_type: str,
    filename: str,
    folder_id: str | None,
    knowledge_space_id: str,
    mime_type: str,
    parser_engine: str | None = None,
    chunk_strategy: str | None = None,
    processing_profile_id: str | None = None,
    product_id: str | None = None,
    expires_in_days: int | None = None,
    tags: list[str],
    title: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_space_access(current_store, user, space_id=knowledge_space_id, required="write")
    if folder_id is not None:
        folder = _read_memory_record(current_store, "knowledge_folders", folder_id)
        if (
            folder is None
            or folder.get("knowledge_space_id") != knowledge_space_id
            or not folder_is_effectively_active(current_store, folder_id)
        ):
            raise api_error(404, "NOT_FOUND", "Knowledge folder not found")
    normalized_filename = normalize_upload_filename(filename)
    normalized_mime_type = (mime_type or "application/octet-stream").lower()
    validate_upload_content(
        content=content,
        filename=normalized_filename,
        mime_type=normalized_mime_type,
    )
    normalized_parser = normalize_parser_engine(parser_engine, normalized_mime_type)
    normalized_chunk_strategy = normalize_chunk_strategy(chunk_strategy)
    processing_profile = get_processing_profile(
        current_store,
        processing_profile_id,
        user=user,
    )
    if normalized_parser == "multimodal" and processing_profile is None:
        raise api_error(
            400,
            "KNOWLEDGE_PROCESSING_PROFILE_REQUIRED",
            "Multimodal parser requires a processing profile",
        )
    if processing_profile is not None:
        profile_product_id = processing_profile.get("product_id")
        if product_id is not None and profile_product_id not in {None, product_id}:
            raise api_error(
                409,
                "KNOWLEDGE_PROCESSING_PROFILE_SCOPE_MISMATCH",
                "Processing profile does not belong to the selected product",
            )
        product_id = product_id or profile_product_id
    if product_id is not None:
        require_product_scope(user, product_id)
    settings = get_settings()
    if normalized_parser in {"multimodal", "pdf_text"}:
        preview_content = f"{normalized_filename} 已上传，等待内容解析。"
    else:
        preview_content = content.decode("utf-8", errors="replace").strip()
    preview_content = preview_content[: settings.knowledge_preview_max_chars]

    timestamp = now_iso()
    document_id = current_store.new_id("knowledge")
    document = {
        "id": document_id,
        "title": non_blank(title, "title"),
        "content": preview_content,
        "source_type": "upload",
        "doc_type": doc_type or "manual",
        "product_id": product_id,
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
        "active_document_version_id": None,
        "active_chunk_set_id": None,
        "parser_engine": normalized_parser,
        "chunk_strategy": normalized_chunk_strategy,
    }
    document_version = create_document_version_record(
        content_hash=hashlib.sha256(content).hexdigest(),
        current_store=current_store,
        document_id=document_id,
        expires_in_days=expires_in_days,
        parser_config={
            "chunk_strategy": normalized_chunk_strategy,
            "parser_engine": normalized_parser,
        },
        processing_profile=processing_profile,
        source_asset_id=None,
        user=user,
    )
    asset = create_asset_record(
        content=content,
        current_store=current_store,
        document_id=document_id,
        document_version_id=document_version["id"],
        filename=normalized_filename,
        mime_type=normalized_mime_type,
        space_id=knowledge_space_id,
        user=user,
    )
    document_version = update_document_version_source(
        current_store,
        document_version_id=document_version["id"],
        source_asset_id=asset["id"],
    )
    document["source_asset_id"] = asset["id"]
    import_job = {
        "id": current_store.new_id("knowledge_import_job"),
        "document_id": document_id,
        "source_asset_id": asset["id"],
        "parser_engine": normalized_parser,
        "chunk_strategy": normalized_chunk_strategy,
        "processing_profile_id": processing_profile_id,
        "document_version_id": document_version["id"],
        "parser_config": {
            "chunk_strategy": normalized_chunk_strategy,
            "parser_engine": normalized_parser,
        },
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
        "document_version": version_response(current_store, document_version),
    }


def create_knowledge_upload_presign_result(
    *,
    content_length: int | None,
    current_store: Any,
    filename: str,
    knowledge_space_id: str,
    mime_type: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_space_access(current_store, user, space_id=knowledge_space_id, required="write")
    normalized_filename = normalize_upload_filename(filename)
    normalized_mime_type = (mime_type or "application/octet-stream").lower()
    settings = get_settings()
    extension = _upload_extension(normalized_filename)
    if extension not in settings.knowledge_upload_allowed_extensions:
        raise api_error(400, "KNOWLEDGE_UPLOAD_TYPE_UNSUPPORTED", "file extension is not allowed")
    if normalized_mime_type not in settings.knowledge_upload_allowed_mime_types:
        raise api_error(400, "KNOWLEDGE_UPLOAD_TYPE_UNSUPPORTED", "file mime type is not allowed")
    if content_length is not None and content_length > settings.knowledge_upload_max_bytes:
        raise api_error(
            413,
            "KNOWLEDGE_UPLOAD_TOO_LARGE",
            "uploaded file exceeds configured size limit",
        )
    upload_session_id = current_store.new_id("knowledge_upload")
    object_key = f"knowledge/{knowledge_space_id}/pending/{upload_session_id}/{normalized_filename}"
    storage = object_storage()
    upload_url = storage.presigned_put_url(
        bucket=settings.object_storage_bucket,
        expires_seconds=settings.knowledge_upload_presign_expires_seconds,
        object_key=object_key,
    )
    return {
        "allowed_extensions": sorted(settings.knowledge_upload_allowed_extensions),
        "allowed_mime_types": sorted(settings.knowledge_upload_allowed_mime_types),
        "bucket": settings.object_storage_bucket,
        "expires_seconds": settings.knowledge_upload_presign_expires_seconds,
        "filename": normalized_filename,
        "max_bytes": settings.knowledge_upload_max_bytes,
        "mime_type": normalized_mime_type,
        "object_key": object_key,
        "provider": storage.provider,
        "supports_presigned": bool(upload_url),
        "upload_session_id": upload_session_id,
        "upload_url": upload_url,
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
    document = _read_memory_record(
        current_store,
        "knowledge_documents",
        import_job.get("document_id"),
    )
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    source_asset = _read_memory_record(
        current_store,
        "knowledge_assets",
        import_job.get("source_asset_id"),
    )
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
    document_version = _read_memory_record(
        current_store,
        "knowledge_document_versions",
        import_job.get("document_version_id"),
    )
    if import_job.get("document_version_id") and document_version is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document version not found")
    processing_profile = get_processing_profile(
        current_store,
        import_job.get("processing_profile_id"),
        user=user,
    )

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
        if running_job.get("parser_engine") == "multimodal":
            if processing_profile is None:
                raise ValueError("KNOWLEDGE_PROCESSING_PROFILE_REQUIRED")
            from app.services import knowledge_multimodal

            parsed = knowledge_multimodal.process_multimodal_asset(
                content=source_content,
                filename=source_asset.get("filename", document["id"]),
                mime_type=source_asset.get("mime_type", "application/octet-stream"),
                profile=processing_profile,
            )
        else:
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
                document_version_id=running_job.get("document_version_id"),
                filename=sidecar["filename"],
                metadata=sidecar.get("metadata", {}),
                mime_type=sidecar["mime_type"],
                page_number=sidecar.get("page_number"),
                bounding_boxes=sidecar.get("bounding_boxes", []),
                provider_metadata=sidecar.get("provider_metadata", {}),
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
            document_version_id=running_job.get("document_version_id"),
            filename=parsed["filename"],
            metadata=parsed_metadata,
            mime_type=parsed["mime_type"],
            provider_metadata=parsed.get("provider_metadata", {}),
            space_id=space_id or source_asset["knowledge_space_id"],
            user=user,
        )
        put_knowledge_asset_to_memory(current_store, parsed_asset)
        chunk_set_id = current_store.new_id("knowledge_chunk_set")
        chunk_set = {
            "id": chunk_set_id,
            "document_id": document["id"],
            "document_version_id": running_job.get("document_version_id"),
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
            chunk["document_version_id"] = running_job.get("document_version_id")
            chunk["modality"] = source_metadata.get("modality", "text")
            chunk["embedding_model"] = chunk.get("metadata", {}).get("embedding_model")
            chunk["metadata"]["document_version_id"] = running_job.get(
                "document_version_id"
            )
            if document_version is not None:
                chunk["metadata"]["document_version"] = document_version.get("version")
                chunk["metadata"]["expires_at"] = document_version.get("expires_at")
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
        activated_version = (
            activate_document_version(
                current_store,
                document_id=document["id"],
                document_version_id=running_job["document_version_id"],
            )
            if next_index_status != "index_failed" and running_job.get("document_version_id")
            else document_version
        )
        indexed_document = {
            **indexed_document,
            "active_chunk_set_id": chunk_set_id
            if indexed_document["index_status"] != "index_failed"
            else previous_active_id,
            "source_asset_id": source_asset["id"],
            "parsed_asset_id": parsed_asset["id"],
            "active_document_version_id": (
                running_job.get("document_version_id")
                if next_index_status != "index_failed"
                else document.get("active_document_version_id")
            ),
            "document_version": (
                activated_version.get("version")
                if activated_version is not None
                else document.get("document_version", 1)
            ),
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
            "document_version": (
                version_response(current_store, activated_version)
                if activated_version is not None
                else None
            ),
        }
    except Exception as exc:  # noqa: BLE001
        failed_version = fail_document_version(
            current_store,
            document_version_id=running_job.get("document_version_id"),
            error=str(exc) or "Knowledge import failed",
        )
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
        failed_document = _read_memory_record(
            current_store,
            "knowledge_documents",
            document["id"],
        ) or document
        return {
            "document": knowledge_document_response(current_store, failed_document, []),
            "import_job": import_job_response(current_store, failed_job),
            "document_version": (
                version_response(current_store, failed_version)
                if failed_version is not None
                else None
            ),
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
    document = _read_memory_record(
        current_store,
        "knowledge_documents",
        import_job.get("document_id"),
    )
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
    document = _read_memory_record(
        current_store,
        "knowledge_documents",
        import_job.get("document_id"),
    )
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
    document = _read_memory_record(current_store, "knowledge_documents", document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    if not document_is_readable(current_store, user, document):
        raise api_error(403, "FORBIDDEN", "Knowledge document permission denied")
    items = [
        dict(chunk_set)
        for chunk_set in _read_memory_collection(current_store, "knowledge_chunk_sets").values()
        if chunk_set.get("document_id") == document_id
    ]
    active_id = document.get("active_chunk_set_id")
    for item in items:
        item["is_active"] = item["id"] == active_id
        item["chunk_count"] = len(
            [
                chunk
                for chunk in _read_memory_collection(current_store, "knowledge_chunks").values()
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
    document = _read_memory_record(current_store, "knowledge_documents", document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    if not document_is_readable(current_store, user, document):
        raise api_error(403, "FORBIDDEN", "Knowledge document permission denied")
    target_chunk_set_id = chunk_set_id or document.get("active_chunk_set_id")
    items = [
        dict(chunk)
        for chunk in _read_memory_collection(current_store, "knowledge_chunks").values()
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
    document = _read_memory_record(current_store, "knowledge_documents", document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    space_id = document.get("knowledge_space_id")
    if space_id:
        ensure_space_access(current_store, user, space_id=space_id, required="write")
    chunk_set = _read_memory_record(current_store, "knowledge_chunk_sets", chunk_set_id)
    if chunk_set is None or chunk_set.get("document_id") != document_id:
        raise api_error(404, "NOT_FOUND", "Knowledge chunk set not found")
    if chunk_set.get("status") not in {"active", "archived"}:
        raise api_error(409, "CHUNK_SET_STATE_INVALID", "Knowledge chunk set cannot be activated")
    for existing_id, existing in list(
        _read_memory_collection(current_store, "knowledge_chunk_sets").items()
    ):
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
    activated_version = None
    if chunk_set.get("document_version_id"):
        activated_version = activate_document_version(
            current_store,
            document_id=document_id,
            document_version_id=chunk_set["document_version_id"],
        )
    updated_document = {
        **document,
        "active_chunk_set_id": chunk_set_id,
        "active_document_version_id": chunk_set.get("document_version_id")
        or document.get("active_document_version_id"),
        "document_version": (
            activated_version.get("version")
            if activated_version is not None
            else document.get("document_version", 1)
        ),
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
        for chunk in _read_memory_collection(current_store, "knowledge_chunks").values()
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
    active_chunk_set = _read_memory_record(
        current_store,
        "knowledge_chunk_sets",
        chunk_set_id,
    ) or chunk_set
    return {
        "chunk_set": dict(active_chunk_set),
        "document": knowledge_document_response(current_store, updated_document, chunks),
    }


def reparse_knowledge_document_result(
    *,
    current_store: Any,
    document_id: str,
    parser_engine: str | None,
    chunk_strategy: str | None,
    processing_profile_id: str | None = None,
    expires_in_days: int | None = None,
    user: dict[str, Any],
) -> dict[str, Any]:
    document = _read_memory_record(current_store, "knowledge_documents", document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    space_id = document.get("knowledge_space_id")
    if space_id:
        ensure_space_access(current_store, user, space_id=space_id, required="write")
    source_asset_id = document.get("source_asset_id")
    source_asset = _read_memory_record(current_store, "knowledge_assets", source_asset_id)
    if source_asset is None:
        raise api_error(404, "NOT_FOUND", "Knowledge source asset not found")
    normalized_parser = normalize_parser_engine(
        parser_engine or document.get("parser_engine"),
        source_asset.get("mime_type"),
    )
    normalized_strategy = normalize_chunk_strategy(chunk_strategy or document.get("chunk_strategy"))
    active_version = _read_memory_record(
        current_store,
        "knowledge_document_versions",
        document.get("active_document_version_id"),
    )
    resolved_profile_id = processing_profile_id or (active_version or {}).get(
        "processing_profile_id"
    )
    processing_profile = get_processing_profile(
        current_store,
        resolved_profile_id,
        user=user,
    )
    if normalized_parser == "multimodal" and processing_profile is None:
        raise api_error(
            400,
            "KNOWLEDGE_PROCESSING_PROFILE_REQUIRED",
            "Multimodal parser requires a processing profile",
        )
    if (
        processing_profile is not None
        and processing_profile.get("product_id")
        and processing_profile.get("product_id") != document.get("product_id")
    ):
        raise api_error(
            409,
            "KNOWLEDGE_PROCESSING_PROFILE_SCOPE_MISMATCH",
            "Processing profile does not belong to the document product",
        )
    timestamp = now_iso()
    document_version = create_document_version_record(
        content_hash=str(source_asset.get("content_hash") or ""),
        current_store=current_store,
        document_id=document_id,
        expires_in_days=expires_in_days,
        parser_config={
            "chunk_strategy": normalized_strategy,
            "parser_engine": normalized_parser,
        },
        processing_profile=processing_profile,
        source_asset_id=source_asset_id,
        user=user,
    )
    import_job = {
        "id": current_store.new_id("knowledge_import_job"),
        "document_id": document_id,
        "source_asset_id": source_asset_id,
        "parser_engine": normalized_parser,
        "chunk_strategy": normalized_strategy,
        "processing_profile_id": resolved_profile_id,
        "document_version_id": document_version["id"],
        "parser_config": {
            "chunk_strategy": normalized_strategy,
            "parser_engine": normalized_parser,
        },
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
        "document_version": version_response(current_store, document_version),
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
        target_folder = _read_memory_record(current_store, "knowledge_folders", folder_id)
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
        document = _read_memory_record(current_store, "knowledge_documents", document_id)
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
    asset = _read_memory_record(current_store, "knowledge_assets", asset_id)
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
