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

RD_EXECUTOR_PROFILE_MANAGE_PERMISSION = "delivery.rd_executor_profiles.manage"
RD_EXECUTOR_PROFILE_STATUSES = {"active", "disabled", "retired"}
RD_EXECUTOR_TYPES = {"model_gateway", "codex", "claude", "hermes", "openclaw", "human"}
RD_EXECUTOR_HEALTH = {"unknown", "healthy", "degraded", "unavailable"}


def _repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    required = (
        "get_rd_executor_profile",
        "list_rd_executor_profiles",
        "save_rd_executor_profile_record",
    )
    if repository is not None and all(
        callable(getattr(repository, name, None)) for name in required
    ):
        return repository
    return None


def _collection(current_store: Any) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, "rd_executor_profiles", None)
    if not isinstance(collection, dict):
        raise RuntimeError("R&D executor profile store is unavailable")
    return collection


def _enum(value: Any, field: str, allowed: set[str], default: str) -> str:
    result = str(value if value is not None else "").strip().lower()
    if result not in allowed:
        raise api_error(400, "VALIDATION_ERROR", f"{field} is invalid")
    return result


def _positive_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise api_error(400, "VALIDATION_ERROR", f"{field} must be a positive integer") from exc
    if number < 1:
        raise api_error(400, "VALIDATION_ERROR", f"{field} must be a positive integer")
    return number


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise api_error(400, "VALIDATION_ERROR", f"{field} must be an object")
    ensure_safe_metadata(value, field)
    return dict(value)


def _reject_credential_reference(payload: dict[str, Any]) -> None:
    if str(payload.get("credential_ref") or "").strip():
        raise api_error(
            400,
            "RD_EXECUTOR_PROFILE_SECRET_FORBIDDEN",
            "credential_ref is not accepted for R&D executor profiles",
        )


def _public_profile(record: dict[str, Any]) -> dict[str, Any]:
    public = {key: value for key, value in record.items() if key != "credential_ref"}
    for field in ("workspace_capabilities", "supported_role_codes"):
        if field in public:
            public[field] = redact_metadata(public[field])
    return public


def _profile_from_payload(
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
                "executor_type",
                "credential_ref",
                "workspace_capabilities",
                "max_concurrency",
                "supported_role_codes",
                "health_status",
                "status",
            },
        )
    _reject_credential_reference(payload)
    source = {**(existing or {}), **payload}
    now = datetime.now(UTC).isoformat()
    return {
        "id": existing["id"] if existing else current_store.new_id("rd_executor_profile"),
        "brain_app_id": active_brain_app_id(
            current_store, source.get("brain_app_id", DEFAULT_BRAIN_APP_ID)
        ),
        "code": _non_blank(source.get("code"), "code"),
        "name": _non_blank(source.get("name"), "name"),
        "executor_type": _enum(source.get("executor_type"), "executor_type", RD_EXECUTOR_TYPES, ""),
        "runner_id": str(source.get("runner_id") or "").strip() or None,
        "model_gateway_config_id": str(source.get("model_gateway_config_id") or "").strip() or None,
        "credential_ref": None,
        "workspace_capabilities": _object(
            source.get("workspace_capabilities", {}), "workspace_capabilities"
        ),
        "max_concurrency": _positive_int(source.get("max_concurrency", 1), "max_concurrency"),
        "supported_role_codes": _string_list(
            source.get("supported_role_codes", []), "supported_role_codes"
        ),
        "health_status": _enum(
            source.get("health_status"), "health_status", RD_EXECUTOR_HEALTH, "unknown"
        ),
        "status": _enum(source.get("status"), "status", RD_EXECUTOR_PROFILE_STATUSES, "active"),
        "created_by": existing.get("created_by") if existing else user["id"],
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
    }


def _ensure_manager(user: dict[str, Any]) -> None:
    require_permissions(user, {RD_EXECUTOR_PROFILE_MANAGE_PERMISSION})


def _save(current_store: Any, record: dict[str, Any]) -> dict[str, Any]:
    repository = _repository(current_store)
    if repository is not None:
        return repository.save_rd_executor_profile_record(record)
    _collection(current_store)[record["id"]] = dict(record)
    return record


def _get(current_store: Any, record_id: str) -> dict[str, Any] | None:
    repository = _repository(current_store)
    if repository is not None:
        return repository.get_rd_executor_profile(record_id)
    return _collection(current_store).get(record_id)


def list_rd_executor_profiles_response(
    *, current_store: Any, user: dict[str, Any], brain_app_id: str | None, status: str | None
) -> dict[str, Any]:
    _ensure_manager(user)
    if status is not None and status not in RD_EXECUTOR_PROFILE_STATUSES:
        raise api_error(400, "VALIDATION_ERROR", "status is invalid")
    repository = _repository(current_store)
    records = (
        repository.list_rd_executor_profiles(brain_app_id=brain_app_id, status=status)
        if repository is not None
        else list(_collection(current_store).values())
    )
    return {
        "items": [
            _public_profile(record)
            for record in sorted(records, key=lambda item: (item.get("code", ""), item["id"]))
            if (brain_app_id is None or record.get("brain_app_id") == brain_app_id)
            and (status is None or record.get("status") == status)
        ]
    }


def create_rd_executor_profile_response(
    *, current_store: Any, payload: dict[str, Any], user: dict[str, Any]
) -> dict[str, Any]:
    _ensure_manager(user)
    return _public_profile(
        _save(
            current_store,
            _profile_from_payload(
                current_store=current_store, payload=payload, user=user, existing=None
            ),
        )
    )


def patch_rd_executor_profile_response(
    *, current_store: Any, profile_id: str, payload: dict[str, Any], user: dict[str, Any]
) -> dict[str, Any]:
    _ensure_manager(user)
    existing = _get(current_store, profile_id)
    if existing is None:
        raise api_error(404, "NOT_FOUND", "R&D executor profile not found")
    return _public_profile(
        _save(
            current_store,
            _profile_from_payload(
                current_store=current_store, payload=payload, user=user, existing=existing
            ),
        )
    )
