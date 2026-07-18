from __future__ import annotations

from copy import deepcopy
from typing import Any

RD_POLICY_SCHEMA_VERSION = 1

_CONFIG_FIELDS = (
    "matching_config",
    "assessment_config",
    "iteration_config",
    "team_config",
    "autonomy_config",
    "quality_gate_config",
    "git_config",
    "experience_reuse_config",
    "deployment_config",
)


class PolicyValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _non_blank(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise PolicyValidationError("RD_EXECUTION_POLICY_INVALID", f"{field} is required")
    return result


def _config(value: Any, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PolicyValidationError("RD_EXECUTION_POLICY_INVALID", f"{field} must be an object")
    return deepcopy(value)


def _string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not str(item or "").strip() for item in value):
        raise PolicyValidationError("RD_EXECUTION_POLICY_INVALID", f"{field} must be a string list")
    return sorted(set(str(item).strip() for item in value))


def _validate_experience_reuse_config(value: dict[str, Any]) -> dict[str, Any]:
    """Normalize the frozen experience-reuse contract used by planning.

    Capacity is deliberately two-dimensional: item count and context tokens.
    The old ambiguous ``max_capacity`` field is rejected instead of silently
    weakening one of those limits.
    """
    config = deepcopy(value)
    if "max_capacity" in config:
        raise PolicyValidationError(
            "RD_EXECUTION_POLICY_INVALID",
            "experience_reuse_config.max_capacity is unsupported; "
            "use max_items and max_context_tokens",
        )
    if "enabled" in config and not isinstance(config["enabled"], bool):
        raise PolicyValidationError(
            "RD_EXECUTION_POLICY_INVALID", "experience_reuse_config.enabled must be boolean"
        )
    if "min_confidence" in config and (
        isinstance(config["min_confidence"], bool)
        or not isinstance(config["min_confidence"], (int, float))
        or not 0 <= float(config["min_confidence"]) <= 1
    ):
        raise PolicyValidationError(
            "RD_EXECUTION_POLICY_INVALID", "experience_reuse_config.min_confidence must be 0..1"
        )
    for field, allow_zero in (
        ("max_age_days", True),
        ("max_items", False),
        ("max_context_tokens", False),
    ):
        if field not in config:
            continue
        value = config[field]
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < (0 if allow_zero else 1)
        ):
            raise PolicyValidationError(
                "RD_EXECUTION_POLICY_INVALID", f"experience_reuse_config.{field} is invalid"
            )
    for field in ("repository_trust_domains", "tool_trust_domains"):
        if field in config:
            config[field] = _string_list(config[field], f"experience_reuse_config.{field}")
    if "policy_compatibility" in config and config["policy_compatibility"] not in {
        "same_policy_version",
        "same_policy_schema",
    }:
        raise PolicyValidationError(
            "RD_EXECUTION_POLICY_INVALID",
            "experience_reuse_config.policy_compatibility is invalid",
        )
    if "require_independent_reviewer" in config and not isinstance(
        config["require_independent_reviewer"], bool
    ):
        raise PolicyValidationError(
            "RD_EXECUTION_POLICY_INVALID",
            "experience_reuse_config.require_independent_reviewer must be boolean",
        )
    if config.get("enabled") and (
        "max_items" not in config or "max_context_tokens" not in config
    ):
        raise PolicyValidationError(
            "RD_EXECUTION_POLICY_INVALID",
            "enabled experience reuse requires max_items and max_context_tokens",
        )
    return config


def validate_unified_policy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the one-policy strategy contract before persistence or resolution."""
    normalized = {
        "name": _non_blank(payload.get("name"), "name"),
        "brain_app_id": _non_blank(payload.get("brain_app_id", "rd_brain"), "brain_app_id"),
        "product_id": str(payload["product_id"]).strip() if payload.get("product_id") else None,
        "status": str(payload.get("status", "active")).strip().lower(),
        "delivery_target": _non_blank(
            payload.get("delivery_target", "ready_for_release"), "delivery_target"
        ),
    }
    if normalized["status"] not in {"active", "disabled"}:
        raise PolicyValidationError(
            "RD_EXECUTION_POLICY_INVALID", "status must be active or disabled"
        )
    if normalized["delivery_target"] not in {"deployed", "ready_for_release"}:
        raise PolicyValidationError(
            "RD_EXECUTION_POLICY_INVALID",
            "delivery_target must be deployed or ready_for_release",
        )
    for field in _CONFIG_FIELDS:
        normalized[field] = _config(payload.get(field), field)
    normalized["experience_reuse_config"] = _validate_experience_reuse_config(
        normalized["experience_reuse_config"]
    )

    bindings_value = payload.get("role_bindings")
    if not isinstance(bindings_value, list):
        raise PolicyValidationError("RD_EXECUTION_POLICY_INVALID", "role_bindings must be a list")
    bindings: list[dict[str, Any]] = []
    active_roles: set[str] = set()
    for binding_value in bindings_value:
        if not isinstance(binding_value, dict):
            raise PolicyValidationError(
                "RD_EXECUTION_POLICY_INVALID", "each role binding must be an object"
            )
        binding = deepcopy(binding_value)
        role_code = _non_blank(binding.get("role_code"), "role_bindings.role_code")
        status = str(binding.get("status", "active")).strip().lower()
        actor_mode = str(binding.get("actor_mode", "")).strip().lower()
        if status not in {"active", "disabled"} or actor_mode not in {"human", "ai", "hybrid"}:
            raise PolicyValidationError(
                "RD_EXECUTION_POLICY_INVALID", "invalid role binding status or mode"
            )
        fallbacks = binding.get("fallback_executor_profile_ids", [])
        if fallbacks:
            raise PolicyValidationError(
                "RD_POLICY_FALLBACK_FORBIDDEN",
                "role bindings cannot declare fallback executors",
            )
        if status == "active":
            if role_code in active_roles:
                raise PolicyValidationError(
                    "RD_POLICY_ROLE_BINDING_INVALID",
                    "each role may have exactly one active binding",
                )
            active_roles.add(role_code)
        bindings.append(
            {
                **binding,
                "actor_mode": actor_mode,
                "role_code": role_code,
                "status": status,
                "fallback_executor_profile_ids": [],
            }
        )
    required_roles = _string_list(
        normalized["team_config"].get("required_role_codes"),
        "team_config.required_role_codes",
    )
    normalized["team_config"]["required_role_codes"] = required_roles
    missing = sorted(set(required_roles) - active_roles)
    if missing:
        raise PolicyValidationError(
            "RD_POLICY_REQUIRED_ROLE_MISSING",
            f"required role bindings are missing: {', '.join(missing)}",
        )
    normalized["role_bindings"] = sorted(bindings, key=lambda item: item["role_code"])
    return normalized


def unified_policy_from_record(
    record: dict[str, Any],
    *,
    role_bindings: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    strategy_config = record.get("strategy_config")
    if isinstance(strategy_config, dict) and strategy_config:
        if role_bindings is None:
            return None
        return validate_unified_policy_payload({**strategy_config, "role_bindings": role_bindings})
    return None


def unified_policy_contract(policy: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(policy)
