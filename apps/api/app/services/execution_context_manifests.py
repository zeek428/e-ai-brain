from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.services.operational_records import read_memory_dict, record_audit_event
from app.services.product_scope import require_product_scope

SENSITIVE_KEY_FRAGMENTS = (
    "access_key",
    "api_key",
    "authorization",
    "credential",
    "password",
    "private_key",
    "secret",
    "session",
    "token",
)
MAX_KNOWLEDGE_SUMMARY_CHARS = 500
URL_CREDENTIAL_PATTERN = re.compile(r"(?P<scheme>https?://)[^/@\s]+@", re.IGNORECASE)
BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]+")


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().lower().replace("-", "_")
    return any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS)


def _redact_string(value: str) -> str:
    if "-----BEGIN" in value and "PRIVATE KEY-----" in value:
        return "[REDACTED]"
    sanitized = URL_CREDENTIAL_PATTERN.sub(r"\g<scheme>[REDACTED]@", value)
    return BEARER_PATTERN.sub("Bearer [REDACTED]", sanitized)


def redact_execution_context(value: Any, *, key: str | None = None) -> Any:
    if key is not None and _is_sensitive_key(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {
            str(item_key): redact_execution_context(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [redact_execution_context(item) for item in value]
    if isinstance(value, tuple):
        return [redact_execution_context(item) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _canonical_hash(content: dict[str, Any]) -> str:
    canonical = json.dumps(
        content,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _unique_text_values(*values: Any) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidates = value if isinstance(value, list) else [value]
        for candidate in candidates:
            text = str(candidate or "").strip()
            if text and text not in seen:
                seen.add(text)
                items.append(text)
    return items


def _knowledge_manifest_reference(reference: dict[str, Any]) -> dict[str, Any]:
    content = str(reference.get("content") or "").strip()
    summary = content[:MAX_KNOWLEDGE_SUMMARY_CHARS].rstrip()
    if len(content) > MAX_KNOWLEDGE_SUMMARY_CHARS:
        summary = f"{summary}..."
    return redact_execution_context(
        {
            "chunk_id": reference.get("chunk_id"),
            "chunk_index": reference.get("chunk_index"),
            "content_chars": len(content),
            "content_summary": summary,
            "content_truncated": len(content) > MAX_KNOWLEDGE_SUMMARY_CHARS,
            "document_id": reference.get("document_id"),
            "document_version": reference.get("document_version")
            or reference.get("version"),
            "doc_type": reference.get("doc_type"),
            "folder_id": reference.get("folder_id"),
            "knowledge_space_id": reference.get("knowledge_space_id"),
            "retrieval_reason": reference.get("retrieval_reason")
            or "产品与版本权限范围匹配",
            "title": reference.get("title"),
        }
    )


def _manifest_records(
    current_store: Any,
    *,
    product_id: str,
    subject_id: str,
) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_execution_context_manifests", None)
    if callable(list_records):
        return list(
            list_records(
                product_scope_ids=[product_id],
                subject_id=subject_id,
                subject_type="ai_task",
            )
        )
    return [
        record
        for record in read_memory_dict(current_store, "execution_context_manifests").values()
        if record.get("subject_type") == "ai_task"
        and record.get("subject_id") == subject_id
        and record.get("product_id") == product_id
    ]


def build_execution_context_manifest(
    *,
    branch: str | None,
    current_store: Any,
    knowledge_references: list[dict[str, Any]],
    repository_ref: dict[str, Any],
    task: dict[str, Any],
    user: dict[str, Any],
    iteration_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Build a manifest and audit record without writing durable state."""
    product_id = str(task.get("product_id") or "").strip()
    require_product_scope(
        user,
        product_id,
        code="PRODUCT_SCOPE_FORBIDDEN",
        message="AI task product is outside the current user scope",
        status_code=403,
    )
    task_id = str(task["id"])
    requirement = (
        task.get("requirement_snapshot")
        if isinstance(task.get("requirement_snapshot"), dict)
        else {}
    )
    input_json = task.get("input_json") if isinstance(task.get("input_json"), dict) else {}
    bug = input_json.get("bug") if isinstance(input_json.get("bug"), dict) else {}
    acceptance_criteria = _unique_text_values(
        requirement.get("acceptance_criteria"),
        input_json.get("acceptance_criteria"),
        input_json.get("definition_of_done"),
    )
    knowledge_refs = [
        _knowledge_manifest_reference(reference)
        for reference in knowledge_references
        if isinstance(reference, dict)
    ]
    manifest_content = redact_execution_context(
        {
            "acceptance_criteria": acceptance_criteria,
            "branch": str(branch or "").strip() or None,
            "bug_refs": [bug] if bug else [],
            "knowledge_refs": knowledge_refs,
            "iteration_context": iteration_context or {},
            "permission_snapshot": {
                "permissions": sorted(str(item) for item in user.get("permissions") or []),
                "roles": sorted(str(item) for item in user.get("roles") or []),
                "scopes": user.get("scope_summary") or [],
                "user_id": user.get("id"),
            },
            "repository_ref": repository_ref or {},
            "requirement_refs": [requirement] if requirement else [],
            "retrieval_summary": {
                "product_id": product_id,
                "selected_knowledge_count": len(knowledge_refs),
                "source": "permission_filtered_product_knowledge",
                "version_id": task.get("version_id") or requirement.get("version_id"),
            },
            "truncation_summary": {
                "knowledge_reference_limit": len(knowledge_references),
                "knowledge_summary_max_chars": MAX_KNOWLEDGE_SUMMARY_CHARS,
                "truncated_knowledge_count": sum(
                    1 for reference in knowledge_refs if reference.get("content_truncated")
                ),
            },
        }
    )
    content_hash = _canonical_hash(manifest_content)
    existing = _manifest_records(
        current_store,
        product_id=product_id,
        subject_id=task_id,
    )
    duplicate = next(
        (record for record in existing if record.get("content_hash") == content_hash),
        None,
    )
    if duplicate is not None:
        return deepcopy(duplicate), None

    now = datetime.now(UTC).isoformat()
    record = {
        "id": current_store.new_id("execution_context_manifest"),
        "subject_type": "ai_task",
        "subject_id": task_id,
        "product_id": product_id,
        "version": max((int(item.get("version") or 0) for item in existing), default=0) + 1,
        "content_hash": content_hash,
        "created_by": user["id"],
        "created_at": now,
        **manifest_content,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="execution_context_manifest.created",
        actor_id=user["id"],
        subject_type="execution_context_manifest",
        subject_id=record["id"],
        payload={
            "ai_task_id": task_id,
            "content_hash": content_hash,
            "product_id": product_id,
            "version": record["version"],
        },
    )
    return deepcopy(record), audit_event


def save_execution_context_manifest(
    current_store: Any,
    *,
    audit_event: dict[str, Any] | None,
    record: dict[str, Any],
) -> dict[str, Any]:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_execution_context_manifest_record", None)
    if callable(save_record):
        persisted = save_record(record, audit_event=audit_event)
        return deepcopy(persisted or record)
    read_memory_dict(current_store, "execution_context_manifests")[record["id"]] = record
    return deepcopy(record)


def build_and_save_execution_context_manifest(
    *,
    branch: str | None,
    current_store: Any,
    knowledge_references: list[dict[str, Any]],
    repository_ref: dict[str, Any],
    task: dict[str, Any],
    user: dict[str, Any],
    iteration_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record, audit_event = build_execution_context_manifest(
        branch=branch,
        current_store=current_store,
        iteration_context=iteration_context,
        knowledge_references=knowledge_references,
        repository_ref=repository_ref,
        task=task,
        user=user,
    )
    if audit_event is None:
        return record
    return save_execution_context_manifest(
        current_store,
        audit_event=audit_event,
        record=record,
    )


def execution_context_manifest_for_task(
    current_store: Any,
    *,
    task_id: str,
    product_scope_ids: list[str] | None = None,
) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_execution_context_manifests", None)
    if callable(list_records):
        records = list(
            list_records(
                product_scope_ids=product_scope_ids,
                subject_id=task_id,
                subject_type="ai_task",
            )
        )
    else:
        allowed_products = set(product_scope_ids or [])
        records = [
            record
            for record in read_memory_dict(current_store, "execution_context_manifests").values()
            if record.get("subject_type") == "ai_task"
            and record.get("subject_id") == task_id
            and (product_scope_ids is None or record.get("product_id") in allowed_products)
        ]
    if not records:
        return None
    latest = max(
        records,
        key=lambda record: (int(record.get("version") or 0), str(record.get("created_at") or "")),
    )
    return deepcopy(latest)
