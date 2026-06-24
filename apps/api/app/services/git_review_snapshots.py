from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services.git_review_diff import compare_changed_file_snapshots, diff_payload


def save_git_review_snapshot_record(
    current_store: Any,
    *,
    snapshot: dict[str, Any] | None,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_gitlab_review_snapshot_record", None)
    if callable(save_record):
        save_record(snapshot=snapshot, audit_event=audit_event)
        return
    if snapshot is not None:
        _memory_collection(current_store, "gitlab_mr_snapshots")[str(snapshot["id"])] = snapshot
    if audit_event is not None:
        _memory_list(current_store, "audit_events").append(audit_event)


def _memory_collection(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _memory_list(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, list):
        collection = []
        setattr(current_store, collection_name, collection)
    return collection


def record_audit_event(
    current_store: Any,
    *,
    actor_id: str,
    event_type: str,
    payload: dict[str, Any],
    subject_id: str,
    subject_type: str,
) -> dict[str, Any]:
    audit_events = getattr(current_store, "audit_events", None)
    sequence = len(audit_events) + 1 if isinstance(audit_events, list) else 1
    event = {
        "id": current_store.new_id("audit_event"),
        "event_type": event_type,
        "actor_id": actor_id,
        "ai_task_id": None,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": payload,
        "sequence": sequence,
        "created_at": datetime.now(UTC).isoformat(),
    }
    return event


def raise_git_context_mismatch(message: str) -> None:
    raise api_error(400, "GITLAB_CONTEXT_MISMATCH", message)


def ensure_snapshot_context(
    *,
    repository: dict[str, Any],
    requirement: dict[str, Any],
    technical_solution: dict[str, Any],
) -> None:
    if repository["product_id"] != requirement["product_id"]:
        raise_git_context_mismatch(
            "GitLab repository binding and requirement must belong to the same product"
        )
    if technical_solution["requirement_id"] != requirement["id"]:
        raise_git_context_mismatch(
            "Technical solution task must be derived from the snapshot requirement"
        )
    if technical_solution["product_id"] != requirement["product_id"]:
        raise_git_context_mismatch(
            "Technical solution task and requirement must belong to the same product"
        )
    if technical_solution["version_id"] != requirement["version_id"]:
        raise_git_context_mismatch(
            "Technical solution task and requirement must belong to the same version"
        )


def create_code_review_source_snapshot(
    current_store: Any,
    *,
    repository: dict[str, Any],
    requirement: dict[str, Any],
    mr_iid: int,
    preview: dict[str, Any],
    payload: Any,
    user: dict[str, Any],
    event_prefix: str,
    diff_storage_prefix: str,
) -> dict[str, Any]:
    diff_content = diff_payload(preview)
    diff_size_bytes = len(diff_content.encode())
    diff_limit_bytes = 204_800
    changed_file_count = len(preview["changed_files_summary"])
    changed_file_limit = 50
    file_diff_line_limit = 2_000

    def fail_snapshot(reason: str, extra_payload: dict[str, Any]) -> None:
        audit_event = record_audit_event(
            current_store,
            event_type=f"{event_prefix}.snapshot_failed",
            actor_id=user["id"],
            subject_type="product_git_repository",
            subject_id=repository["id"],
            payload={
                "diff_limit_bytes": diff_limit_bytes,
                "diff_size_bytes": diff_size_bytes,
                "mr_iid": mr_iid,
                "reason": reason,
                "requirement_id": payload.requirement_id,
                "technical_solution_task_id": payload.technical_solution_task_id,
                **extra_payload,
            },
        )
        save_git_review_snapshot_record(current_store, snapshot=None, audit_event=audit_event)

    if changed_file_count > changed_file_limit:
        fail_snapshot(
            "changed_file_count_too_large",
            {"changed_file_count": changed_file_count, "changed_file_limit": changed_file_limit},
        )
        raise api_error(413, "GITLAB_MR_DIFF_TOO_LARGE", "MR diff exceeds configured limit")
    oversized_file = next(
        (
            item
            for item in preview["changed_files_summary"]
            if int(item.get("additions") or 0) + int(item.get("deletions") or 0)
            > file_diff_line_limit
        ),
        None,
    )
    if oversized_file:
        file_diff_line_count = int(oversized_file.get("additions") or 0) + int(
            oversized_file.get("deletions") or 0
        )
        fail_snapshot(
            "single_file_diff_too_large",
            {
                "file_diff_line_count": file_diff_line_count,
                "file_diff_line_limit": file_diff_line_limit,
                "file_path": oversized_file.get("path") or "-",
            },
        )
        raise api_error(413, "GITLAB_MR_DIFF_TOO_LARGE", "MR diff exceeds configured limit")
    if diff_size_bytes > diff_limit_bytes:
        fail_snapshot("diff_too_large", {})
        raise api_error(413, "GITLAB_MR_DIFF_TOO_LARGE", "MR diff exceeds configured limit")

    snapshot_hash = hashlib.sha256(diff_content.encode()).hexdigest()
    related_snapshots = [
        snapshot
        for snapshot in current_store.gitlab_mr_snapshots.values()
        if snapshot.get("repository_id") == repository["id"]
        and int(snapshot.get("mr_iid") or 0) == int(mr_iid)
    ]
    related_snapshots.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    previous_snapshot = related_snapshots[0] if related_snapshots else None
    diff_change_summary = compare_changed_file_snapshots(
        previous_snapshot.get("changed_files_summary") if previous_snapshot else None,
        preview.get("changed_files_summary"),
    )

    existing_snapshot = next(
        (
            snapshot
            for snapshot in current_store.gitlab_mr_snapshots.values()
            if snapshot.get("repository_id") == repository["id"]
            and snapshot.get("snapshot_hash") == snapshot_hash
        ),
        None,
    )
    if existing_snapshot is not None:
        audit_event = record_audit_event(
            current_store,
            event_type=f"{event_prefix}.snapshot_reused",
            actor_id=user["id"],
            subject_type="gitlab_mr_snapshot",
            subject_id=existing_snapshot["id"],
            payload={
                "repository_id": repository["id"],
                "mr_iid": mr_iid,
                "requirement_id": payload.requirement_id,
                "technical_solution_task_id": payload.technical_solution_task_id,
            },
        )
        save_git_review_snapshot_record(current_store, snapshot=None, audit_event=audit_event)
        return {
            **existing_snapshot,
            "diff_change_summary": diff_change_summary,
            "previous_snapshot": _snapshot_comparison_ref(previous_snapshot),
            "snapshot_reused": True,
        }

    snapshot_id = current_store.new_id("snapshot")
    snapshot = {
        "id": snapshot_id,
        "repository_id": repository["id"],
        "product_id": requirement["product_id"],
        "version_id": requirement["version_id"],
        "project_id": preview["project_id"],
        "project_path": preview["project_path"],
        "mr_iid": mr_iid,
        "title": preview["title"],
        "author": preview["author"],
        "source_branch": preview["source_branch"],
        "target_branch": preview["target_branch"],
        "base_sha": preview["base_sha"],
        "head_sha": preview["head_sha"],
        "diff_refs": preview["diff_refs"],
        "changed_files_summary": preview["changed_files_summary"],
        "diff_file_tree": preview.get("diff_file_tree", []),
        "review_checklist": preview.get("review_checklist", []),
        "risk_summary": preview.get("risk_summary", {}),
        "diff_storage_ref": f"memory://{diff_storage_prefix}/{snapshot_id}",
        "diff_size_bytes": diff_size_bytes,
        "diff_limit_bytes": diff_limit_bytes,
        "snapshot_hash": snapshot_hash,
        "requirement_id": payload.requirement_id,
        "technical_solution_task_id": payload.technical_solution_task_id,
        "created_by": user["id"],
        "created_at": datetime.now(UTC).isoformat(),
        "source_provider": repository.get("git_provider", "gitlab"),
        "writeback_allowed": False,
    }
    audit_event = record_audit_event(
        current_store,
        event_type=f"{event_prefix}.snapshotted",
        actor_id=user["id"],
        subject_type="gitlab_mr_snapshot",
        subject_id=snapshot_id,
        payload={"repository_id": repository["id"], "mr_iid": mr_iid},
    )
    save_git_review_snapshot_record(current_store, snapshot=snapshot, audit_event=audit_event)
    return {
        **snapshot,
        "diff_change_summary": diff_change_summary,
        "previous_snapshot": _snapshot_comparison_ref(previous_snapshot),
        "snapshot_reused": False,
    }


def _snapshot_comparison_ref(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return {
        "created_at": snapshot.get("created_at"),
        "head_sha": snapshot.get("head_sha"),
        "id": snapshot.get("id"),
        "snapshot_hash": snapshot.get("snapshot_hash"),
    }
