from __future__ import annotations

from typing import Any

from fastapi import HTTPException

VERSION_STATUSES = {"active", "archived", "planning", "released", "testing"}
VERSION_MAIN_STATUSES = {"active", "planning", "released", "testing"}
VERSION_STATUS_TRANSITIONS = {
    "active": {"testing"},
    "planning": {"active"},
    "released": {"archived"},
    "testing": {"released"},
}
VERSION_REQUIREMENT_AUTO_ADVANCE = {
    "active": {
        "approved": "ready_for_dev",
        "planned": "ready_for_dev",
    },
    "released": {},
    "testing": {
        "approved": "testing",
        "code_reviewing": "testing",
        "designing": "testing",
        "developing": "testing",
        "planned": "testing",
        "ready_for_dev": "testing",
    },
}
VERSION_REQUIREMENT_ALLOWED_UNCHANGED = {
    "active": {
        "accepted",
        "cancelled",
        "closed",
        "code_reviewing",
        "deferred",
        "developing",
        "deploying",
        "ready_for_dev",
        "ready_for_release",
        "rejected",
        "released",
        "testing",
    },
    "released": {
        "accepted",
        "cancelled",
        "closed",
        "deferred",
        "deploying",
        "rejected",
        "released",
    },
    "archived": {
        "accepted",
        "cancelled",
        "closed",
        "deferred",
        "rejected",
        "released",
    },
    "testing": {
        "accepted",
        "cancelled",
        "closed",
        "deferred",
        "deploying",
        "ready_for_release",
        "rejected",
        "released",
        "testing",
    },
}
VERSION_REQUIREMENT_BLOCK_REASONS = {
    "active": "需求尚未进入可开发状态，版本进入开发会形成范围风险",
    "archived": "需求尚未达到发布或终止状态，归档会形成历史数据风险",
    "released": "需求尚未达到发布或终止状态，不能发布版本",
    "testing": "需求尚未进入可交付状态，进入测试会形成版本风险",
}
REQUIREMENT_SCHEDULABLE_VERSION_STATUSES = {"active", "planning"}
REQUIREMENT_BATCH_ADVANCE_TRANSITIONS = {
    "approved": {"cancelled", "closed", "deferred", "planned", "ready_for_dev"},
    "planned": {"cancelled", "closed", "deferred", "ready_for_dev"},
    "ready_for_dev": {"cancelled", "closed", "deferred", "developing"},
    "designing": {"cancelled", "closed", "deferred", "ready_for_dev"},
    "developing": {"cancelled", "closed", "code_reviewing", "deferred", "testing"},
    "code_reviewing": {"cancelled", "closed", "deferred", "testing"},
    "testing": {"cancelled", "closed", "deferred", "ready_for_release"},
    "ready_for_release": {"cancelled", "closed", "deferred", "deploying"},
    "deploying": {"cancelled", "closed", "deferred", "ready_for_release"},
    "released": {"accepted", "closed"},
}
REQUIREMENT_BATCH_ADVANCE_TARGET_STATUSES = {
    target
    for allowed_targets in REQUIREMENT_BATCH_ADVANCE_TRANSITIONS.values()
    for target in allowed_targets
}
REQUIREMENT_BATCH_ADVANCE_VERSION_REQUIRED_STATUSES = {
    "planned",
    "ready_for_dev",
    "developing",
    "code_reviewing",
    "testing",
    "ready_for_release",
    "deploying",
    "released",
    "accepted",
}

LEGACY_REQUIREMENT_STATUS_ALIASES = {
    "pending_approval": "submitted",
    "task_created": "designing",
}


def _domain_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def ensure_enum(value: str | None, allowed_values: set[str], field: str) -> None:
    if value is not None and value not in allowed_values:
        raise _domain_error(400, "VALIDATION_ERROR", f"Unsupported {field}")


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _memory_records(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    return list(_memory_dict(current_store, collection_name).values())


def canonical_requirement_status(status: str | None) -> str:
    if status is None:
        return "draft"
    return LEGACY_REQUIREMENT_STATUS_ALIASES.get(status, status)


def validate_requirement_batch_advance_target(target_status: str) -> None:
    ensure_enum(
        target_status,
        REQUIREMENT_BATCH_ADVANCE_TARGET_STATUSES,
        "requirement target status",
    )


def can_batch_advance_requirement_status(from_status: str, target_status: str) -> bool:
    if from_status == target_status:
        return False
    return target_status in REQUIREMENT_BATCH_ADVANCE_TRANSITIONS.get(from_status, set())


def requires_requirement_version_for_batch_advance(target_status: str) -> bool:
    return target_status in REQUIREMENT_BATCH_ADVANCE_VERSION_REQUIRED_STATUSES


def validate_requirement_version(
    current_store: Any,
    *,
    product_id: str,
    version_id: str | None,
) -> dict[str, Any] | None:
    if version_id is None:
        return None
    version = _memory_dict(current_store, "product_versions").get(version_id)
    if version is None or version["product_id"] != product_id:
        raise _domain_error(404, "NOT_FOUND", "Product version not found")
    if version["status"] == "archived":
        raise _domain_error(400, "PRODUCT_VERSION_ARCHIVED", "Archived version cannot be used")
    if version["status"] not in REQUIREMENT_SCHEDULABLE_VERSION_STATUSES:
        raise _domain_error(
            400,
            "PRODUCT_VERSION_NOT_SCHEDULABLE",
            "Only planning or active versions can be used for requirement scheduling",
        )
    return version


def requirement_advance_item(
    requirement: dict[str, Any],
    *,
    from_status: str,
    to_status: str,
) -> dict[str, str]:
    return {
        "from_status": from_status,
        "id": requirement["id"],
        "title": requirement["title"],
        "to_status": to_status,
    }


def requirement_block_item(
    requirement: dict[str, Any],
    *,
    block_reason: str,
    status: str,
) -> dict[str, str]:
    return {
        "block_reason": block_reason,
        "id": requirement["id"],
        "status": status,
        "title": requirement["title"],
    }


def requirements_for_version(
    current_store: Any,
    version_id: str,
) -> list[dict[str, Any]]:
    requirements = [
        requirement
        for requirement in _memory_records(current_store, "requirements")
        if requirement.get("version_id") == version_id
    ]
    requirements.sort(key=lambda item: (item.get("created_at") or "", item.get("id") or ""))
    return requirements


def build_version_advance_impact(
    current_store: Any,
    *,
    target_status: str,
    version_id: str,
) -> dict[str, list[dict[str, str]]]:
    auto_advance = VERSION_REQUIREMENT_AUTO_ADVANCE.get(target_status, {})
    allowed_unchanged = VERSION_REQUIREMENT_ALLOWED_UNCHANGED.get(target_status, set())
    block_reason = VERSION_REQUIREMENT_BLOCK_REASONS.get(
        target_status,
        "需求状态不满足版本推进条件",
    )
    updated: list[dict[str, str]] = []
    blocked: list[dict[str, str]] = []
    unchanged: list[dict[str, str]] = []
    for requirement in requirements_for_version(current_store, version_id):
        status = canonical_requirement_status(requirement.get("status"))
        next_status = auto_advance.get(status)
        if next_status is not None:
            updated.append(
                requirement_advance_item(
                    requirement,
                    from_status=status,
                    to_status=next_status,
                )
            )
            continue
        if status in allowed_unchanged:
            unchanged.append(
                {
                    "id": requirement["id"],
                    "status": status,
                    "title": requirement["title"],
                }
            )
            continue
        blocked.append(
            requirement_block_item(
                requirement,
                block_reason=block_reason,
                status=status,
            )
        )
    return {
        "blocked_requirements": blocked,
        "unchanged_requirements": unchanged,
        "updated_requirements": updated,
    }


def validate_version_status_transition(from_status: str, target_status: str) -> None:
    ensure_enum(target_status, VERSION_STATUSES, "product version target status")
    if target_status == "archived":
        if from_status != "released":
            raise _domain_error(
                409,
                "PRODUCT_VERSION_STATUS_INVALID",
                "Only released versions can be archived",
            )
        return
    if target_status not in VERSION_MAIN_STATUSES:
        raise _domain_error(
            400,
            "PRODUCT_VERSION_STATUS_INVALID",
            "Target status is not a version delivery stage",
        )
    if target_status == from_status:
        raise _domain_error(
            400,
            "PRODUCT_VERSION_STATUS_UNCHANGED",
            "Target status must be different from current status",
        )
    if target_status not in VERSION_STATUS_TRANSITIONS.get(from_status, set()):
        raise _domain_error(
            409,
            "PRODUCT_VERSION_STATUS_INVALID",
            "Version status must be advanced through the configured delivery flow",
        )
