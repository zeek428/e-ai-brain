from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_permissions
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.rd_role_definitions import (
    _non_blank,
    _string_list,
    active_brain_app_id,
    ensure_safe_metadata,
    redact_metadata,
    reject_explicit_nulls,
)

RD_AI_EMPLOYEE_MANAGE_PERMISSION = "delivery.rd_ai_employees.manage"
RD_AI_EMPLOYEE_STATUSES = {"active", "disabled", "retired"}


def _repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    required = (
        "get_rd_ai_employee",
        "list_rd_ai_employees",
        "save_rd_ai_employee_record",
    )
    if repository is not None and all(
        callable(getattr(repository, name, None)) for name in required
    ):
        return repository
    return None


def _collection(current_store: Any) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, "rd_ai_employees", None)
    if not isinstance(collection, dict):
        raise RuntimeError("R&D AI employee store is unavailable")
    return collection


def _status(value: Any) -> str:
    status = str(value if value is not None else "").strip().lower()
    if status not in RD_AI_EMPLOYEE_STATUSES:
        raise api_error(400, "VALIDATION_ERROR", "status is invalid")
    return status


def _positive_version(value: Any, field: str) -> int:
    try:
        version = int(value)
    except (TypeError, ValueError) as exc:
        raise api_error(400, "VALIDATION_ERROR", f"{field} must be a positive integer") from exc
    if version < 1:
        raise api_error(400, "VALIDATION_ERROR", f"{field} must be a positive integer")
    return version


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise api_error(400, "VALIDATION_ERROR", f"{field} must be an object")
    ensure_safe_metadata(value, field)
    return dict(value)


def _public_employee(record: dict[str, Any]) -> dict[str, Any]:
    public = {
        key: value
        for key, value in record.items()
        if key not in {"credential_ref", "permissions", "granted_permissions", "system_role_id"}
    }
    for field in ("capability_tags", "persona_json", "work_style_json"):
        if field in public:
            public[field] = redact_metadata(public[field])
    return public


def _employee_from_payload(
    *,
    current_store: Any,
    payload: dict[str, Any],
    user: dict[str, Any],
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    if existing is not None:
        reject_explicit_nulls(
            payload,
            {
                "brain_app_id",
                "code",
                "name",
                "capability_tags",
                "persona_version",
                "persona_json",
                "work_style_version",
                "work_style_json",
                "status",
            },
        )
    source = {**(existing or {}), **payload}
    now = datetime.now(UTC).isoformat()
    return {
        "id": existing["id"] if existing else current_store.new_id("rd_ai_employee"),
        "brain_app_id": active_brain_app_id(
            current_store, source.get("brain_app_id", DEFAULT_BRAIN_APP_ID)
        ),
        "code": _non_blank(source.get("code"), "code"),
        "name": _non_blank(source.get("name"), "name"),
        "capability_tags": _string_list(source.get("capability_tags", []), "capability_tags"),
        "persona_version": _positive_version(source.get("persona_version", 1), "persona_version"),
        "persona_json": _object(source.get("persona_json", {}), "persona_json"),
        "work_style_version": _positive_version(
            source.get("work_style_version", 1), "work_style_version"
        ),
        "work_style_json": _object(source.get("work_style_json", {}), "work_style_json"),
        "status": _status(source.get("status")),
        "created_by": existing.get("created_by") if existing else user["id"],
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
    }


def _ensure_manager(user: dict[str, Any]) -> None:
    require_permissions(user, {RD_AI_EMPLOYEE_MANAGE_PERMISSION})


def _save(current_store: Any, record: dict[str, Any]) -> dict[str, Any]:
    repository = _repository(current_store)
    if repository is not None:
        return repository.save_rd_ai_employee_record(record)
    _collection(current_store)[record["id"]] = dict(record)
    return record


def _get(current_store: Any, record_id: str) -> dict[str, Any] | None:
    repository = _repository(current_store)
    if repository is not None:
        return repository.get_rd_ai_employee(record_id)
    return _collection(current_store).get(record_id)


def list_rd_ai_employees_response(
    *, current_store: Any, user: dict[str, Any], brain_app_id: str | None, status: str | None
) -> dict[str, Any]:
    _ensure_manager(user)
    if status is not None and status not in RD_AI_EMPLOYEE_STATUSES:
        raise api_error(400, "VALIDATION_ERROR", "status is invalid")
    repository = _repository(current_store)
    records = (
        repository.list_rd_ai_employees(brain_app_id=brain_app_id, status=status)
        if repository is not None
        else list(_collection(current_store).values())
    )
    return {
        "items": [
            _public_employee(record)
            for record in sorted(records, key=lambda item: (item.get("code", ""), item["id"]))
            if (brain_app_id is None or record.get("brain_app_id") == brain_app_id)
            and (status is None or record.get("status") == status)
        ]
    }


def create_rd_ai_employee_response(
    *, current_store: Any, payload: dict[str, Any], user: dict[str, Any]
) -> dict[str, Any]:
    _ensure_manager(user)
    return _public_employee(
        _save(
            current_store,
            _employee_from_payload(
                current_store=current_store, payload=payload, user=user, existing=None
            ),
        )
    )


def patch_rd_ai_employee_response(
    *, current_store: Any, employee_id: str, payload: dict[str, Any], user: dict[str, Any]
) -> dict[str, Any]:
    _ensure_manager(user)
    existing = _get(current_store, employee_id)
    if existing is None:
        raise api_error(404, "NOT_FOUND", "R&D AI employee not found")
    return _public_employee(
        _save(
            current_store,
            _employee_from_payload(
                current_store=current_store, payload=payload, user=user, existing=existing
            ),
        )
    )


def validate_ai_actor_selector(selector: Any) -> list[str]:
    if not isinstance(selector, dict) or set(selector) != {"ai_employee_ids"}:
        raise api_error(
            400,
            "RD_AI_SELECTOR_INVALID",
            "AI actor selector must contain only explicit ai_employee_ids",
        )
    employee_ids = selector.get("ai_employee_ids")
    if (
        not isinstance(employee_ids, list)
        or not employee_ids
        or any(not str(item or "").strip() for item in employee_ids)
    ):
        raise api_error(
            400,
            "RD_AI_SELECTOR_INVALID",
            "AI actor selector requires non-empty ai_employee_ids",
        )
    return sorted({str(item).strip() for item in employee_ids})


def qualify_ai_actor(
    employee: dict[str, Any],
    profile: dict[str, Any],
    *,
    role_definition: dict[str, Any],
    policy_binding: dict[str, Any],
) -> bool:
    """Validate that an AI identity and a separate execution profile are bound together."""
    employee_id = str(employee.get("id") or "").strip()
    profile_id = str(profile.get("id") or "").strip()
    return bool(
        employee_id
        and profile_id
        and employee.get("status") == "active"
        and profile.get("status") == "active"
        and profile.get("health_status") == "healthy"
        and employee.get("brain_app_id", DEFAULT_BRAIN_APP_ID)
        == profile.get("brain_app_id", DEFAULT_BRAIN_APP_ID)
        == role_definition.get("brain_app_id", DEFAULT_BRAIN_APP_ID)
        and role_definition.get("status") == "active"
        and "ai_employee" in set(role_definition.get("assignable_subject_types") or [])
        and role_definition.get("code") in set(profile.get("supported_role_codes") or [])
        and policy_binding.get("status") == "active"
        and policy_binding.get("actor_mode") in {"ai", "hybrid"}
        and employee_id in set(policy_binding.get("candidate_ai_employee_ids") or [])
        and profile_id == policy_binding.get("primary_executor_profile_id")
    )
