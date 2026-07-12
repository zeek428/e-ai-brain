from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.services.operational_records import read_memory_dict


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _records(current_store: Any, collection: str, record_type: str) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_trusted_delivery_records", None)
    if callable(list_records):
        return [dict(item) for item in list_records(record_type=record_type)]
    return [dict(item) for item in read_memory_dict(current_store, collection).values()]


def _save(current_store: Any, *, collection: str, record: dict[str, Any], record_type: str) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_trusted_delivery_record", None)
    if callable(save_record):
        save_record(record=record, record_type=record_type)
    read_memory_dict(current_store, collection)[record["id"]] = deepcopy(record)


def create_production_change_control(
    current_store: Any,
    *,
    created_by: str,
    deployment_id: str,
    product_id: str,
    required_roles: list[str],
) -> dict[str, Any]:
    now = _now()
    control = {
        "created_at": now,
        "created_by": created_by,
        "deployment_id": deployment_id,
        "environment": "prod",
        "id": current_store.new_id("production_change_control"),
        "product_id": product_id,
        "required_roles": sorted(set(required_roles)),
        "status": "pending_approval",
        "updated_at": now,
    }
    _save(
        current_store,
        collection="production_change_controls",
        record=control,
        record_type="production_change_control",
    )
    return deepcopy(control)


def set_release_freeze(
    current_store: Any,
    *,
    created_by: str,
    product_id: str,
    status: str,
) -> dict[str, Any]:
    now = _now()
    existing = next(
        (
            item
            for item in _records(current_store, "release_freezes", "release_freeze")
            if item.get("product_id") == product_id
        ),
        None,
    )
    freeze = {
        **(existing or {}),
        "created_at": (existing or {}).get("created_at") or now,
        "created_by": (existing or {}).get("created_by") or created_by,
        "id": (existing or {}).get("id") or current_store.new_id("release_freeze"),
        "product_id": product_id,
        "status": status,
        "updated_at": now,
    }
    _save(
        current_store,
        collection="release_freezes",
        record=freeze,
        record_type="release_freeze",
    )
    return deepcopy(freeze)


def approve_production_change(
    current_store: Any,
    *,
    control_id: str,
    decision: str,
    role_code: str,
    user_id: str,
) -> dict[str, Any]:
    control = next(
        (
            item
            for item in _records(
                current_store,
                "production_change_controls",
                "production_change_control",
            )
            if item.get("id") == control_id
        ),
        None,
    )
    if control is None:
        raise ValueError("Production change control not found")
    status = (
        "approved" if decision == "approved" and user_id != control["created_by"] else "rejected"
    )
    now = _now()
    approval = {
        "control_id": control_id,
        "created_at": now,
        "decision": decision,
        "id": current_store.new_id("production_change_approval"),
        "product_id": control["product_id"],
        "role_code": role_code,
        "status": status,
        "updated_at": now,
        "user_id": user_id,
    }
    _save(
        current_store,
        collection="production_change_approvals",
        record=approval,
        record_type="production_change_approval",
    )
    return deepcopy(approval)


def deployment_can_start(
    control: dict[str, Any], approvals: list[dict[str, Any]], *, frozen: bool = False
) -> bool:
    if frozen:
        return False
    people = {
        item.get("user_id")
        for item in approvals
        if item.get("status") == "approved" and item.get("decision") == "approved"
    }
    roles = {
        item.get("role_code")
        for item in approvals
        if item.get("status") == "approved" and item.get("decision") == "approved"
    }
    return set(control.get("required_roles") or []) <= roles and (
        not control.get("required_roles") or len(people) >= 2
    )


def production_deployment_can_start(
    current_store: Any, *, deployment_id: str, product_id: str
) -> bool:
    frozen = any(
        item.get("product_id") == product_id and item.get("status") == "active"
        for item in _records(current_store, "release_freezes", "release_freeze")
    )
    controls = [
        item
        for item in _records(
            current_store,
            "production_change_controls",
            "production_change_control",
        )
        if item.get("deployment_id") == deployment_id
    ]
    if not controls:
        return False
    control = controls[-1]
    approvals = [
        item
        for item in _records(
            current_store,
            "production_change_approvals",
            "production_change_approval",
        )
        if item.get("control_id") == control["id"]
    ]
    return deployment_can_start(control, approvals, frozen=frozen)
