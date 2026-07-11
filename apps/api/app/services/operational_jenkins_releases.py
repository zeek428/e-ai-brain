from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.services.operational_records import (
    JENKINS_RELEASE_STATUSES,
    ensure_enum,
    ensure_non_blank,
    operational_query_repository,
    operational_write_store,
    parse_optional_time,
    read_memory_dict,
    read_memory_records,
    record_audit_event,
    save_single_repository_record,
    uses_repository_context,
)


def validate_jenkins_release_payload(payload: Any) -> tuple[str | None, str | None]:
    ensure_non_blank(payload.job_name, "job_name")
    ensure_non_blank(payload.build_id, "build_id")
    ensure_non_blank(payload.environment, "environment")
    ensure_enum(payload.status, JENKINS_RELEASE_STATUSES, "status")
    if payload.build_number is not None and payload.build_number < 0:
        raise api_error(400, "VALIDATION_ERROR", "build_number must be greater than or equal to 0")
    if payload.duration_seconds is not None and payload.duration_seconds < 0:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "duration_seconds must be greater than or equal to 0",
        )
    started_at = parse_optional_time(payload.started_at, "started_at")
    deployed_at = parse_optional_time(payload.deployed_at, "deployed_at")
    if started_at is not None and deployed_at is not None and deployed_at < started_at:
        raise api_error(400, "VALIDATION_ERROR", "deployed_at must be after started_at")
    return started_at, deployed_at


def validate_jenkins_release_context(
    current_store: Any,
    *,
    deployment_request_id: str | None = None,
    product_id: str,
    version_id: str,
) -> None:
    product = read_memory_dict(current_store, "products").get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    version = read_memory_dict(current_store, "product_versions").get(version_id)
    if version is None or version["product_id"] != product_id:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    if version["status"] == "archived":
        raise api_error(400, "PRODUCT_VERSION_ARCHIVED", "Archived version cannot be used")
    if deployment_request_id is not None:
        deployment = read_memory_dict(current_store, "deployment_requests").get(
            deployment_request_id
        )
        if (
            deployment is None
            or deployment.get("product_id") != product_id
            or deployment.get("version_id") != version_id
        ):
            raise api_error(404, "NOT_FOUND", "Deployment request not found")


def list_jenkins_releases_response(
    *,
    current_store: Any,
    environment: str | None,
    product_id: str | None,
    status: str | None,
    version_id: str | None,
) -> dict[str, Any]:
    ensure_enum(status, JENKINS_RELEASE_STATUSES, "status")
    repository = operational_query_repository(current_store)
    list_releases = getattr(repository, "list_jenkins_release_records", None)
    if callable(list_releases):
        items = list_releases(
            product_id=product_id,
            version_id=version_id,
            status=status,
            environment=environment,
        )
        return {"items": items, "total": len(items)}
    items = []
    for release in read_memory_records(current_store, "jenkins_release_records"):
        if product_id is not None and release.get("product_id") != product_id:
            continue
        if version_id is not None and release.get("version_id") != version_id:
            continue
        if status is not None and release.get("status") != status:
            continue
        if environment is not None and release.get("environment") != environment:
            continue
        items.append(release)
    items.sort(
        key=lambda item: (
            item.get("deployed_at") or item.get("created_at") or "",
            item.get("updated_at") or "",
        ),
        reverse=True,
    )
    return {"items": items, "total": len(items)}


def create_jenkins_release_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"devops.read"}, {"product_owner", "rd_owner"})
    write_store = operational_write_store(current_store)
    validate_jenkins_release_context(
        write_store,
        deployment_request_id=payload.deployment_request_id,
        product_id=payload.product_id,
        version_id=payload.version_id,
    )
    started_at, deployed_at = validate_jenkins_release_payload(payload)
    now = datetime.now(UTC).isoformat()
    release_id = write_store.new_id("jenkins_release")
    release = {
        "build_id": ensure_non_blank(payload.build_id, "build_id"),
        "build_number": payload.build_number,
        "commit_sha": payload.commit_sha,
        "created_at": now,
        "created_by": user["id"],
        "deployed_at": deployed_at,
        "deployment_request_id": payload.deployment_request_id,
        "duration_seconds": payload.duration_seconds,
        "environment": ensure_non_blank(payload.environment, "environment"),
        "failure_reason": payload.failure_reason,
        "id": release_id,
        "job_name": ensure_non_blank(payload.job_name, "job_name"),
        "product_id": payload.product_id,
        "source_channel": payload.source_channel,
        "started_at": started_at,
        "status": payload.status,
        "trigger_actor": payload.trigger_actor,
        "updated_at": now,
        "version_id": payload.version_id,
    }
    for optional_key in (
        "build_number",
        "commit_sha",
        "deployed_at",
        "deployment_request_id",
        "duration_seconds",
        "failure_reason",
        "source_channel",
        "started_at",
        "trigger_actor",
    ):
        if release[optional_key] is None:
            release.pop(optional_key)
    if not uses_repository_context(write_store):
        write_store.jenkins_release_records[release_id] = release
    audit_event = record_audit_event(
        write_store,
        event_type="jenkins_release.created",
        actor_id=user["id"],
        subject_type="jenkins_release",
        subject_id=release_id,
        payload={
            "build_id": release["build_id"],
            "job_name": release["job_name"],
            "product_id": release["product_id"],
            "version_id": release["version_id"],
        },
    )
    save_single_repository_record(
        write_store,
        "save_jenkins_release_record",
        release,
        audit_event=audit_event,
    )
    return release
