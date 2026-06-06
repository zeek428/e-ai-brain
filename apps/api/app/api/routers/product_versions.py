from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, api_error, require_roles, store
from app.core.listing import list_payload
from app.core.trace import envelope, get_trace_id
from app.services.product_config_context import (
    delete_product_config_record,
    ensure_enum,
    ensure_non_blank,
    ensure_unique_value,
    payload_updates,
    product_config_query_repository,
    product_config_write_store,
    product_version_summary_projection,
    record_audit_event,
    save_product_config_record,
    save_requirement_record,
    uses_repository_context,
)
from app.services.product_version_listing import list_all_product_versions_response
from app.services.version_status import (
    VERSION_STATUSES,
    build_version_advance_impact,
    validate_version_status_transition,
)

router = APIRouter(tags=["product_versions"])


class ProductVersionRequest(BaseModel):
    code: str | None = None
    name: str
    description: str | None = None
    status: str = "planning"
    start_date: str | None = None
    release_date: str | None = None


class ProductVersionPatchRequest(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    status: str | None = None
    start_date: str | None = None
    release_date: str | None = None


class ProductVersionAdvanceStatusRequest(BaseModel):
    target_status: str
    reason: str | None = None
    force: bool = False
    preview_only: bool = False


@router.get("/api/product-versions")
def list_all_product_versions(
    request: Request,
    active_only: bool = False,
    code: str | None = None,
    name: str | None = None,
    product: str | None = None,
    product_id: str | None = None,
    status: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "asc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return list_all_product_versions_response(
        active_only=active_only,
        code=code,
        current_store=store(request),
        name=name,
        page=page,
        page_size=page_size,
        product=product,
        product_id=product_id,
        request=request,
        sort_by=sort_by,
        sort_order=sort_order,
        status=status,
    )


@router.get("/api/products/{product_id}/versions")
def list_product_versions(
    product_id: str,
    request: Request,
    active_only: bool = False,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    repository = product_config_query_repository(current_store)
    if repository is not None:
        if repository.get_product(product_id) is None:
            raise api_error(404, "NOT_FOUND", "Product not found")
        items = repository.list_product_versions(product_id, active_only=active_only)
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    items = [
        item
        for item in current_store.product_versions.values()
        if item["product_id"] == product_id
    ]
    items.sort(key=lambda item: item["code"])
    return list_payload(items, trace_id=get_trace_id(request), active_only=active_only)


@router.post("/api/products/{product_id}/versions")
def create_product_version(
    product_id: str,
    request: Request,
    payload: ProductVersionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_write_store(store(request))
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    name = ensure_non_blank(payload.name, "name")
    ensure_enum(payload.status, VERSION_STATUSES, "product version status")
    version_id = current_store.new_id("version")
    code = ensure_non_blank(payload.code or version_id, "code")
    ensure_unique_value(
        current_store.product_versions,
        field="code",
        value=code,
        conflict_code="PRODUCT_VERSION_CODE_EXISTS",
        message="Product version code already exists",
        scope={"product_id": product_id},
    )
    version = {
        "id": version_id,
        "product_id": product_id,
        "code": code,
        "name": name,
        "description": payload.description,
        "status": payload.status,
        "start_date": payload.start_date,
        "release_date": payload.release_date,
    }
    if not uses_repository_context(current_store):
        current_store.product_versions[version_id] = version
    audit_event = record_audit_event(
        current_store,
        event_type="product_version.created",
        actor_id=user["id"],
        subject_type="product_version",
        subject_id=version_id,
    )
    save_product_config_record(
        current_store,
        "product_versions",
        version,
        audit_event=audit_event,
    )
    return envelope(version, get_trace_id(request))


@router.post("/api/product-versions/{version_id}/advance-status")
def advance_product_version_status(
    version_id: str,
    request: Request,
    payload: ProductVersionAdvanceStatusRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    current_store = product_config_write_store(store(request))
    version = current_store.product_versions.get(version_id)
    if version is None:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    from_status = version.get("status", "planning")
    target_status = payload.target_status
    validate_version_status_transition(from_status, target_status)
    impact = build_version_advance_impact(
        current_store,
        target_status=target_status,
        version_id=version_id,
    )
    blocked_requirements = impact["blocked_requirements"]
    if (
        not payload.preview_only
        and blocked_requirements
        and (target_status == "released" or not payload.force)
    ):
        raise api_error(
            409,
            "PRODUCT_VERSION_STATUS_BLOCKED",
            "Version has requirements that block this status transition",
        )

    response_version = version
    if not payload.preview_only:
        now = datetime.now(UTC).isoformat()
        response_version = {
            **version,
            "status": target_status,
            "updated_at": now,
        }
        if not uses_repository_context(current_store):
            current_store.product_versions[version_id] = response_version
        for item in impact["updated_requirements"]:
            requirement = current_store.requirements[item["id"]]
            updated_requirement = {
                **requirement,
                "status": item["to_status"],
                "updated_at": now,
            }
            if not uses_repository_context(current_store):
                current_store.requirements[item["id"]] = updated_requirement
            requirement_audit_event = record_audit_event(
                current_store,
                event_type="requirement.updated",
                actor_id=user["id"],
                subject_type="requirement",
                subject_id=item["id"],
                payload={
                    "from_status": item["from_status"],
                    "operation": "version_status_advance",
                    "product_id": version["product_id"],
                    "reason": payload.reason,
                    "to_status": item["to_status"],
                    "version_id": version_id,
                    "version_status_from": from_status,
                    "version_status_to": target_status,
                },
            )
            save_requirement_record(
                current_store,
                updated_requirement,
                audit_event=requirement_audit_event,
            )
        version_audit_event = record_audit_event(
            current_store,
            event_type="product_version.status_advanced",
            actor_id=user["id"],
            subject_type="product_version",
            subject_id=version_id,
            payload={
                "blocked_requirements": blocked_requirements,
                "force": payload.force,
                "from_status": from_status,
                "reason": payload.reason,
                "target_status": target_status,
                "unchanged_requirements": impact["unchanged_requirements"],
                "updated_requirements": impact["updated_requirements"],
            },
        )
        save_product_config_record(
            current_store,
            "product_versions",
            response_version,
            audit_event=version_audit_event,
        )

    return envelope(
        {
            **impact,
            "force": payload.force,
            "from_status": from_status,
            "preview_only": payload.preview_only,
            "target_status": target_status,
            "version": product_version_summary_projection(response_version, current_store),
        },
        get_trace_id(request),
    )


@router.patch("/api/product-versions/{version_id}")
def patch_product_version(
    version_id: str,
    request: Request,
    payload: ProductVersionPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_write_store(store(request))
    version = current_store.product_versions.get(version_id)
    if version is None:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    updates = payload_updates(payload)
    if "name" in updates:
        updates["name"] = ensure_non_blank(updates["name"], "name")
    if "code" in updates:
        updates["code"] = ensure_non_blank(updates["code"], "code")
        ensure_unique_value(
            current_store.product_versions,
            field="code",
            value=updates["code"],
            conflict_code="PRODUCT_VERSION_CODE_EXISTS",
            message="Product version code already exists",
            exclude_id=version_id,
            scope={"product_id": version["product_id"]},
        )
    if "status" in updates:
        ensure_enum(updates["status"], VERSION_STATUSES, "product version status")
        if updates["status"] != version.get("status"):
            raise api_error(
                409,
                "PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED",
                "Use the version status advance endpoint to change delivery status",
            )
    version = {**version, **updates}
    if not uses_repository_context(current_store):
        current_store.product_versions[version_id] = version
    audit_event = record_audit_event(
        current_store,
        event_type="product_version.updated",
        actor_id=user["id"],
        subject_type="product_version",
        subject_id=version_id,
    )
    save_product_config_record(
        current_store,
        "product_versions",
        version,
        audit_event=audit_event,
    )
    return envelope(version, get_trace_id(request))


@router.delete("/api/product-versions/{version_id}")
def delete_product_version(
    version_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_write_store(store(request))
    version = current_store.product_versions.get(version_id)
    if version is None:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    if (
        any(item["version_id"] == version_id for item in current_store.requirements.values())
        or any(item.get("version_id") == version_id for item in current_store.ai_tasks.values())
        or any(item.get("version_id") == version_id for item in current_store.bugs.values())
    ):
        raise api_error(409, "RESOURCE_IN_USE", "Product version still has related records")
    if not uses_repository_context(current_store):
        del current_store.product_versions[version_id]
    audit_event = record_audit_event(
        current_store,
        event_type="product_version.deleted",
        actor_id=user["id"],
        subject_type="product_version",
        subject_id=version_id,
    )
    delete_product_config_record(
        current_store,
        "product_versions",
        version_id,
        audit_event=audit_event,
    )
    return envelope({"deleted": True, "id": version_id}, get_trace_id(request))
