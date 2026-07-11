from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from app.api.deps import api_error
from app.services.product_scope import product_scope_filter, require_product_scope

PROCESSING_PROVIDER_TYPES = {
    "builtin",
    "gotenberg",
    "http",
    "mineru",
    "multimodal_gateway",
    "paddleocr",
}
PROCESSING_CAPABILITIES = {
    "image_embedding",
    "layout",
    "ocr",
    "table",
}
CITATION_FEEDBACK_VALUES = {
    "incorrect",
    "not_useful",
    "outdated",
    "partial",
    "useful",
}
SENSITIVE_PROVIDER_CONFIG_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat()


def _collection(current_store: Any, name: str) -> dict[str, dict[str, Any]]:
    value = getattr(current_store, name, None)
    if not isinstance(value, dict):
        raise TypeError(f"Knowledge governance collection is not available: {name}")
    return value


def _record(current_store: Any, name: str, record_id: str | None) -> dict[str, Any] | None:
    if not record_id:
        return None
    value = _collection(current_store, name).get(str(record_id))
    return dict(value) if isinstance(value, dict) else None


def _non_blank(value: Any, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return normalized


def _normalize_capabilities(values: list[str] | None) -> list[str]:
    capabilities = sorted({str(value).strip() for value in values or [] if str(value).strip()})
    unsupported = set(capabilities) - PROCESSING_CAPABILITIES
    if unsupported:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported processing capability")
    return capabilities


def _normalize_provider_config(
    provider_config: dict[str, Any],
    *,
    provider_type: str,
) -> dict[str, Any]:
    normalized = dict(provider_config or {})
    if any(str(key).lower() in SENSITIVE_PROVIDER_CONFIG_KEYS for key in normalized):
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "Provider credentials must use credential_ref",
        )
    endpoint = str(normalized.get("endpoint_url") or "").strip()
    if provider_type != "builtin":
        parsed = urlsplit(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
            raise api_error(400, "VALIDATION_ERROR", "Valid provider endpoint_url is required")
    elif endpoint:
        raise api_error(400, "VALIDATION_ERROR", "Builtin provider does not use endpoint_url")
    if endpoint:
        normalized["endpoint_url"] = endpoint
    return normalized


def _profile_response(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        **profile,
        "provider_config": dict(profile.get("provider_config") or {}),
        "capabilities": list(profile.get("capabilities") or []),
    }


def _ensure_profile_product_access(user: dict[str, Any], product_id: str | None) -> None:
    if product_id:
        require_product_scope(user, product_id)
        return
    if "admin" not in set(user.get("roles") or []) and "system.admin" not in set(
        user.get("permissions") or []
    ):
        raise api_error(403, "FORBIDDEN", "Global processing profile management denied")


def create_processing_profile_result(
    *,
    capabilities: list[str],
    credential_ref: str | None,
    current_store: Any,
    name: str,
    product_id: str | None,
    provider_config: dict[str, Any],
    provider_type: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    normalized_provider_type = str(provider_type or "").strip()
    if normalized_provider_type not in PROCESSING_PROVIDER_TYPES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported processing provider")
    _ensure_profile_product_access(user, product_id)
    timestamp = _now_iso()
    profile = {
        "id": current_store.new_id("knowledge_processing_profile"),
        "name": _non_blank(name, "name"),
        "product_id": product_id,
        "provider_type": normalized_provider_type,
        "provider_config": _normalize_provider_config(
            provider_config,
            provider_type=normalized_provider_type,
        ),
        "credential_ref": str(credential_ref or "").strip() or None,
        "capabilities": _normalize_capabilities(capabilities),
        "status": "active",
        "version": 1,
        "created_by": user["id"],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    _collection(current_store, "knowledge_processing_profiles")[profile["id"]] = profile
    from app.services.knowledge_management import persist_knowledge_payload, record_audit_event

    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_processing_profile.created",
        subject_id=profile["id"],
        subject_type="knowledge_processing_profile",
    )
    persist_knowledge_payload(current_store, audit_event=audit_event)
    return _profile_response(profile)


def list_processing_profiles_result(
    *,
    current_store: Any,
    product_id: str | None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    product_scope_ids = product_scope_filter(user)
    items = []
    for profile in _collection(current_store, "knowledge_processing_profiles").values():
        profile_product_id = profile.get("product_id")
        if product_id is not None and profile_product_id not in {None, product_id}:
            continue
        if product_scope_ids is not None and profile_product_id not in {None, *product_scope_ids}:
            continue
        if status is not None and profile.get("status") != status:
            continue
        items.append(_profile_response(profile))
    items.sort(key=lambda item: (item.get("name", ""), item["id"]))
    return {"items": items, "total": len(items)}


def update_processing_profile_result(
    *,
    capabilities: list[str] | None,
    credential_ref: str | None,
    credential_ref_set: bool,
    current_store: Any,
    name: str | None,
    profile_id: str,
    provider_config: dict[str, Any] | None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    profile = _record(current_store, "knowledge_processing_profiles", profile_id)
    if profile is None:
        raise api_error(404, "NOT_FOUND", "Knowledge processing profile not found")
    _ensure_profile_product_access(user, profile.get("product_id"))
    if status is not None and status not in {"active", "disabled"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported processing profile status")
    updated = {**profile, "updated_at": _now_iso(), "version": int(profile.get("version") or 1) + 1}
    if name is not None:
        updated["name"] = _non_blank(name, "name")
    if capabilities is not None:
        updated["capabilities"] = _normalize_capabilities(capabilities)
    if provider_config is not None:
        updated["provider_config"] = _normalize_provider_config(
            provider_config,
            provider_type=str(profile.get("provider_type") or "builtin"),
        )
    if credential_ref_set:
        updated["credential_ref"] = str(credential_ref or "").strip() or None
    if status is not None:
        updated["status"] = status
    _collection(current_store, "knowledge_processing_profiles")[profile_id] = updated
    from app.services.knowledge_management import persist_knowledge_payload, record_audit_event

    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_processing_profile.updated",
        subject_id=profile_id,
        subject_type="knowledge_processing_profile",
    )
    persist_knowledge_payload(current_store, audit_event=audit_event)
    return _profile_response(updated)


def get_processing_profile(
    current_store: Any,
    profile_id: str | None,
    *,
    user: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not profile_id:
        return None
    profile = _record(current_store, "knowledge_processing_profiles", profile_id)
    if profile is None or profile.get("status") != "active":
        raise api_error(404, "NOT_FOUND", "Knowledge processing profile not found")
    if user is not None and profile.get("product_id"):
        require_product_scope(user, profile["product_id"])
    return profile


def resolve_expiration(
    *,
    expires_in_days: int | None,
    profile: dict[str, Any] | None,
) -> str | None:
    resolved_days = expires_in_days
    if resolved_days is None and profile is not None:
        configured = dict(profile.get("provider_config") or {}).get("stale_after_days")
        try:
            resolved_days = int(configured) if configured is not None else None
        except (TypeError, ValueError):
            resolved_days = None
    if resolved_days is None:
        return None
    if resolved_days < 1 or resolved_days > 3650:
        raise api_error(400, "VALIDATION_ERROR", "expires_in_days must be between 1 and 3650")
    return (_now() + timedelta(days=resolved_days)).isoformat()


def create_document_version_record(
    *,
    content_hash: str,
    current_store: Any,
    document_id: str,
    expires_in_days: int | None,
    parser_config: dict[str, Any],
    processing_profile: dict[str, Any] | None,
    source_asset_id: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    versions = [
        item
        for item in _collection(current_store, "knowledge_document_versions").values()
        if item.get("document_id") == document_id
    ]
    version_number = max([int(item.get("version") or 0) for item in versions], default=0) + 1
    timestamp = _now_iso()
    version = {
        "id": current_store.new_id("knowledge_document_version"),
        "document_id": document_id,
        "version": version_number,
        "source_asset_id": source_asset_id,
        "processing_profile_id": (processing_profile or {}).get("id"),
        "parser_config": dict(parser_config),
        "content_hash": content_hash,
        "status": "processing",
        "activated_at": None,
        "expires_at": resolve_expiration(
            expires_in_days=expires_in_days,
            profile=processing_profile,
        ),
        "created_by": user["id"],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    _collection(current_store, "knowledge_document_versions")[version["id"]] = version
    return version


def update_document_version_source(
    current_store: Any,
    *,
    document_version_id: str,
    source_asset_id: str,
) -> dict[str, Any]:
    version = _record(current_store, "knowledge_document_versions", document_version_id)
    if version is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document version not found")
    updated = {**version, "source_asset_id": source_asset_id, "updated_at": _now_iso()}
    _collection(current_store, "knowledge_document_versions")[document_version_id] = updated
    return updated


def activate_document_version(
    current_store: Any,
    *,
    document_id: str,
    document_version_id: str,
) -> dict[str, Any]:
    versions = _collection(current_store, "knowledge_document_versions")
    version = _record(current_store, "knowledge_document_versions", document_version_id)
    if version is None or version.get("document_id") != document_id:
        raise api_error(404, "NOT_FOUND", "Knowledge document version not found")
    timestamp = _now_iso()
    for version_id, candidate in list(versions.items()):
        if candidate.get("document_id") != document_id or version_id == document_version_id:
            continue
        if candidate.get("status") in {"active", "expired"}:
            versions[version_id] = {
                **candidate,
                "status": "superseded",
                "updated_at": timestamp,
            }
    activated = {
        **version,
        "status": "active",
        "activated_at": timestamp,
        "updated_at": timestamp,
    }
    versions[document_version_id] = activated
    return activated


def fail_document_version(
    current_store: Any,
    *,
    document_version_id: str | None,
    error: str,
) -> dict[str, Any] | None:
    version = _record(current_store, "knowledge_document_versions", document_version_id)
    if version is None or version.get("status") == "active":
        return version
    failed = {
        **version,
        "parser_config": {**dict(version.get("parser_config") or {}), "error": error},
        "status": "failed",
        "updated_at": _now_iso(),
    }
    _collection(current_store, "knowledge_document_versions")[failed["id"]] = failed
    return failed


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def version_freshness_status(
    version: dict[str, Any] | None,
    *,
    outdated_feedback_count: int = 0,
) -> str:
    if version is None:
        return "unknown"
    if version.get("status") == "failed":
        return "failed"
    if version.get("status") == "superseded":
        return "superseded"
    expires_at = _parse_datetime(version.get("expires_at"))
    if version.get("status") == "expired" or (expires_at is not None and expires_at <= _now()):
        return "expired"
    if outdated_feedback_count > 0:
        return "flagged_outdated"
    if expires_at is not None and expires_at <= _now() + timedelta(days=30):
        return "expiring"
    return "fresh"


def _outdated_feedback_count(current_store: Any, document_version_id: str) -> int:
    return sum(
        1
        for feedback in _collection(current_store, "knowledge_citation_feedback").values()
        if feedback.get("document_version_id") == document_version_id
        and feedback.get("feedback_value") == "outdated"
    )


def version_response(current_store: Any, version: dict[str, Any]) -> dict[str, Any]:
    outdated_count = _outdated_feedback_count(current_store, version["id"])
    return {
        **version,
        "freshness_status": version_freshness_status(
            version,
            outdated_feedback_count=outdated_count,
        ),
        "outdated_feedback_count": outdated_count,
    }


def list_document_versions_result(
    *,
    current_store: Any,
    document_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    document = _record(current_store, "knowledge_documents", document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    from app.services.knowledge_management import document_is_readable

    if not document_is_readable(current_store, user, document):
        raise api_error(403, "FORBIDDEN", "Knowledge document permission denied")
    items = [
        version_response(current_store, version)
        for version in _collection(current_store, "knowledge_document_versions").values()
        if version.get("document_id") == document_id
    ]
    items.sort(key=lambda item: (int(item.get("version") or 0), item["id"]), reverse=True)
    return {"document_id": document_id, "items": items, "total": len(items)}


def record_citation_feedback_result(
    *,
    chunk_id: str | None,
    comment: str | None,
    current_store: Any,
    document_id: str,
    feedback_value: str,
    related_event_id: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    if feedback_value not in CITATION_FEEDBACK_VALUES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported knowledge feedback value")
    document = _record(current_store, "knowledge_documents", document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    from app.services.knowledge_management import document_is_readable, persist_knowledge_payload

    if not document_is_readable(current_store, user, document):
        raise api_error(403, "FORBIDDEN", "Knowledge document permission denied")
    chunk = _record(current_store, "knowledge_chunks", chunk_id)
    if chunk_id and (chunk is None or chunk.get("document_id") != document_id):
        raise api_error(404, "NOT_FOUND", "Knowledge chunk not found")
    document_version_id = (
        (chunk or {}).get("document_version_id")
        or document.get("active_document_version_id")
    )
    timestamp = _now_iso()
    feedback = {
        "id": current_store.new_id("knowledge_citation_feedback"),
        "product_id": document.get("product_id"),
        "document_id": document_id,
        "document_version_id": document_version_id,
        "chunk_id": chunk_id,
        "subject_type": "knowledge_quality_event" if related_event_id else None,
        "subject_id": related_event_id,
        "related_event_id": related_event_id,
        "feedback_value": feedback_value,
        "comment": str(comment or "").strip()[:1000] or None,
        "created_by": user["id"],
        "created_at": timestamp,
    }
    _collection(current_store, "knowledge_citation_feedback")[feedback["id"]] = feedback
    persist_knowledge_payload(current_store)
    return feedback


def list_citation_feedback_result(
    *,
    current_store: Any,
    document_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    document = _record(current_store, "knowledge_documents", document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    from app.services.knowledge_management import document_is_readable

    if not document_is_readable(current_store, user, document):
        raise api_error(403, "FORBIDDEN", "Knowledge document permission denied")
    items = [
        dict(item)
        for item in _collection(current_store, "knowledge_citation_feedback").values()
        if item.get("document_id") == document_id
    ]
    items.sort(key=lambda item: (item.get("created_at", ""), item["id"]), reverse=True)
    return {"document_id": document_id, "items": items, "total": len(items)}


def _staleness_items(
    *,
    current_store: Any,
    knowledge_space_id: str | None,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    from app.services.knowledge_management import document_is_readable

    items = []
    for document in _collection(current_store, "knowledge_documents").values():
        if knowledge_space_id and document.get("knowledge_space_id") != knowledge_space_id:
            continue
        if not document_is_readable(current_store, user, document):
            continue
        version = _record(
            current_store,
            "knowledge_document_versions",
            document.get("active_document_version_id"),
        )
        if version is None:
            continue
        response = version_response(current_store, version)
        items.append(
            {
                "document_id": document["id"],
                "document_title": document.get("title"),
                "knowledge_space_id": document.get("knowledge_space_id"),
                "document_version_id": version["id"],
                "version": version.get("version"),
                "status": version.get("status"),
                "expires_at": version.get("expires_at"),
                "freshness_status": response["freshness_status"],
                "outdated_feedback_count": response["outdated_feedback_count"],
            }
        )
    priority = {"expired": 0, "flagged_outdated": 1, "expiring": 2, "fresh": 3}
    items.sort(
        key=lambda item: (
            priority.get(item["freshness_status"], 9),
            item.get("expires_at") or "9999",
            item["document_id"],
        )
    )
    return items


def list_staleness_result(
    *,
    current_store: Any,
    knowledge_space_id: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    items = _staleness_items(
        current_store=current_store,
        knowledge_space_id=knowledge_space_id,
        user=user,
    )
    summary: dict[str, int] = {
        "expired": 0,
        "expiring": 0,
        "flagged_outdated": 0,
        "fresh": 0,
    }
    for item in items:
        status = item["freshness_status"]
        if status in summary:
            summary[status] += 1
    return {"items": items, "summary": summary, "total": len(items)}


def scan_staleness_result(
    *,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    if "admin" not in set(user.get("roles") or []) and "knowledge.manage" not in set(
        user.get("permissions") or []
    ):
        raise api_error(403, "FORBIDDEN", "Knowledge staleness scan denied")
    expired_ids = []
    timestamp = _now_iso()
    versions = _collection(current_store, "knowledge_document_versions")
    for version_id, version in list(versions.items()):
        expires_at = _parse_datetime(version.get("expires_at"))
        if version.get("status") != "active" or expires_at is None or expires_at > _now():
            continue
        versions[version_id] = {**version, "status": "expired", "updated_at": timestamp}
        expired_ids.append(version_id)
    from app.services.knowledge_management import persist_knowledge_payload, record_audit_event

    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="knowledge_staleness.scanned",
        subject_id=hashlib.sha256(timestamp.encode()).hexdigest()[:16],
        subject_type="knowledge_staleness_scan",
    )
    audit_event["payload"] = {"expired_count": len(expired_ids)}
    persist_knowledge_payload(current_store, audit_event=audit_event)
    return {"expired_count": len(expired_ids), "expired_version_ids": expired_ids}
