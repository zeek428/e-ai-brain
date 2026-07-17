from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_permissions
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.brain_apps import brain_app_rows, find_brain_app
from app.services.product_scope import user_can_read_product

RD_ROLE_MANAGE_PERMISSION = "delivery.rd_roles.manage"
RD_ROLE_STATUSES = {"active", "disabled"}
RD_ROLE_RISK_LEVELS = {"low", "medium", "high", "critical"}
RD_ASSIGNABLE_SUBJECT_TYPES = {"human_user", "ai_employee"}
_SENSITIVE_METADATA_KEY_PREFIXES = (
    "apikey",
    "password",
    "passwd",
    "credential",
    "secret",
    "privatekey",
    "authorization",
    "accesskey",
)
_SENSITIVE_METADATA_KEY_SUFFIXES = (
    "apikey",
    "secret",
    "privatekey",
    "accesskey",
    "credential",
    "authorization",
    "token",
    "password",
    "passwd",
)
_SENSITIVE_VALUE_PREFIXES = (
    "secret://",
    "secret/",
    "env:",
    "bearer ",
    "sk-",
    "sk_",
    "ghp_",
    "glpat-",
    "akia",
)


def _repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    required = (
        "get_rd_role_definition",
        "list_rd_role_definitions",
        "save_rd_role_definition_record",
    )
    if repository is not None and all(
        callable(getattr(repository, name, None)) for name in required
    ):
        return repository
    return None


def _collection(current_store: Any) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, "rd_role_definitions", None)
    if not isinstance(collection, dict):
        raise RuntimeError("R&D role definition store is unavailable")
    return collection


def _non_blank(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return text


def reject_explicit_nulls(payload: dict[str, Any], fields: set[str]) -> None:
    for field in fields:
        if field in payload and payload[field] is None:
            raise api_error(400, "VALIDATION_ERROR", f"{field} cannot be null")


def _is_sensitive_metadata_key(key: str) -> bool:
    normalized = "".join(character for character in key.lower() if character.isalnum())
    return normalized.startswith(_SENSITIVE_METADATA_KEY_PREFIXES) or normalized.endswith(
        _SENSITIVE_METADATA_KEY_SUFFIXES
    )


def _is_sensitive_metadata_value(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized.startswith(_SENSITIVE_VALUE_PREFIXES)


def ensure_safe_metadata(value: Any, field: str) -> None:
    """Reject credential-shaped data without including its value in an error response."""
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if _is_sensitive_metadata_key(str(key)):
                raise api_error(
                    400,
                    "RD_CATALOG_SECRET_FORBIDDEN",
                    f"{field} cannot contain credential metadata",
                )
            ensure_safe_metadata(nested_value, field)
    elif isinstance(value, list):
        for nested_value in value:
            ensure_safe_metadata(nested_value, field)
    elif isinstance(value, str) and _is_sensitive_metadata_value(value):
        raise api_error(
            400,
            "RD_CATALOG_SECRET_FORBIDDEN",
            f"{field} cannot contain credential metadata",
        )


def redact_metadata(value: Any) -> Any:
    """Redact legacy or corrupt metadata without leaking key names or values."""
    if isinstance(value, dict):
        return {
            key: redact_metadata(nested_value)
            for key, nested_value in value.items()
            if not _is_sensitive_metadata_key(str(key))
        }
    if isinstance(value, list):
        return [redact_metadata(nested_value) for nested_value in value]
    if isinstance(value, str) and _is_sensitive_metadata_value(value):
        return "[REDACTED]"
    return value


def _string_list(value: Any, field: str, *, allowed: set[str] | None = None) -> list[str]:
    if not isinstance(value, list) or not value:
        raise api_error(400, "VALIDATION_ERROR", f"{field} must be a non-empty string list")
    values = sorted({_non_blank(item, field) for item in value})
    ensure_safe_metadata(values, field)
    if allowed is not None and not set(values).issubset(allowed):
        raise api_error(400, "VALIDATION_ERROR", f"{field} contains an unsupported value")
    return values


def _status(value: Any) -> str:
    status = str(value if value is not None else "").strip().lower()
    if status not in RD_ROLE_STATUSES:
        raise api_error(400, "VALIDATION_ERROR", "status must be active or disabled")
    return status


def active_brain_app_id(current_store: Any, value: Any) -> str:
    brain_app_id = _non_blank(value, "brain_app_id")
    brain_app = find_brain_app(brain_app_rows(current_store), brain_app_id)
    if brain_app is None or brain_app.get("status") != "active":
        raise api_error(404, "RD_BRAIN_APP_NOT_FOUND", "R&D brain app not found or inactive")
    return str(brain_app["id"])


def _public_role(record: dict[str, Any]) -> dict[str, Any]:
    public = {
        key: value
        for key, value in record.items()
        if key not in {"permissions", "granted_permissions", "system_role_id"}
    }
    # R&D role definitions are business catalog entries, not system RBAC roles.
    for field in ("capabilities", "responsibilities"):
        if field in public:
            public[field] = redact_metadata(public[field])
    public["system_role_id"] = None
    return public


def _role_from_payload(
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
                "capabilities",
                "responsibilities",
                "maximum_risk_level",
                "assignable_subject_types",
                "status",
            },
        )
    source = {**(existing or {}), **payload}
    risk = (
        str(source.get("maximum_risk_level") if "maximum_risk_level" in source else "")
        .strip()
        .lower()
    )
    if risk not in RD_ROLE_RISK_LEVELS:
        raise api_error(400, "VALIDATION_ERROR", "maximum_risk_level is invalid")
    now = datetime.now(UTC).isoformat()
    return {
        "id": existing["id"] if existing else current_store.new_id("rd_role"),
        "brain_app_id": active_brain_app_id(
            current_store, source.get("brain_app_id", DEFAULT_BRAIN_APP_ID)
        ),
        "code": _non_blank(source.get("code"), "code"),
        "name": _non_blank(source.get("name"), "name"),
        "capabilities": _string_list(source.get("capabilities", []), "capabilities"),
        "responsibilities": _string_list(source.get("responsibilities", []), "responsibilities"),
        "maximum_risk_level": risk,
        "assignable_subject_types": _string_list(
            source.get("assignable_subject_types", []),
            "assignable_subject_types",
            allowed=RD_ASSIGNABLE_SUBJECT_TYPES,
        ),
        "status": _status(source.get("status")),
        "created_by": existing.get("created_by") if existing else user["id"],
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
    }


def _save_role(current_store: Any, record: dict[str, Any]) -> dict[str, Any]:
    repository = _repository(current_store)
    if repository is not None:
        return repository.save_rd_role_definition_record(record)
    _collection(current_store)[record["id"]] = dict(record)
    return record


def _get_role(current_store: Any, role_id: str) -> dict[str, Any] | None:
    repository = _repository(current_store)
    if repository is not None:
        return repository.get_rd_role_definition(role_id)
    return _collection(current_store).get(role_id)


def _ensure_manager(user: dict[str, Any]) -> None:
    require_permissions(user, {RD_ROLE_MANAGE_PERMISSION})


def list_rd_roles_response(
    *, current_store: Any, user: dict[str, Any], brain_app_id: str | None, status: str | None
) -> dict[str, Any]:
    _ensure_manager(user)
    if status is not None and status not in RD_ROLE_STATUSES:
        raise api_error(400, "VALIDATION_ERROR", "status must be active or disabled")
    repository = _repository(current_store)
    records = (
        repository.list_rd_role_definitions(brain_app_id=brain_app_id, status=status)
        if repository is not None
        else list(_collection(current_store).values())
    )
    return {
        "items": [
            _public_role(record)
            for record in sorted(records, key=lambda item: (item.get("code", ""), item["id"]))
            if (brain_app_id is None or record.get("brain_app_id") == brain_app_id)
            and (status is None or record.get("status") == status)
        ]
    }


def create_rd_role_response(
    *, current_store: Any, payload: dict[str, Any], user: dict[str, Any]
) -> dict[str, Any]:
    _ensure_manager(user)
    return _public_role(
        _save_role(
            current_store,
            _role_from_payload(
                current_store=current_store, payload=payload, user=user, existing=None
            ),
        )
    )


def patch_rd_role_response(
    *, current_store: Any, role_id: str, payload: dict[str, Any], user: dict[str, Any]
) -> dict[str, Any]:
    _ensure_manager(user)
    existing = _get_role(current_store, role_id)
    if existing is None:
        raise api_error(404, "NOT_FOUND", "R&D role definition not found")
    return _public_role(
        _save_role(
            current_store,
            _role_from_payload(
                current_store=current_store, payload=payload, user=user, existing=existing
            ),
        )
    )


def validate_human_actor_selector(selector: Any) -> list[str]:
    """P0 human seats use only a non-empty explicit user_ids selector."""
    if not isinstance(selector, dict) or set(selector) != {"user_ids"}:
        raise api_error(
            400,
            "RD_HUMAN_SELECTOR_INVALID",
            "human actor selector must contain only explicit user_ids",
        )
    user_ids = selector.get("user_ids")
    if (
        not isinstance(user_ids, list)
        or not user_ids
        or any(not str(item or "").strip() for item in user_ids)
    ):
        raise api_error(
            400,
            "RD_HUMAN_SELECTOR_INVALID",
            "human actor selector requires non-empty user_ids",
        )
    return sorted({str(item).strip() for item in user_ids})


def qualify_human_actor(
    user: dict[str, Any], *, role_definition: dict[str, Any], product_id: str
) -> bool:
    """Check the identity, business role, collaboration permission, and product scope."""
    permissions = set(user.get("permissions") or [])
    roles = set(user.get("roles") or [])
    can_work = bool(
        "delivery.rd_collaboration.work" in permissions
        or "system.admin" in permissions
        or "admin" in roles
    )
    return bool(
        str(user.get("id") or "").strip()
        and role_definition.get("status") == "active"
        and "human_user" in set(role_definition.get("assignable_subject_types") or [])
        and can_work
        and user_can_read_product(user, product_id)
    )
