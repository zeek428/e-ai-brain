from __future__ import annotations

import pytest

from app.services.rd_policy_validation import (
    PolicyValidationError,
    validate_unified_policy_payload,
)


def _policy_payload(capacity: object) -> dict:
    return {
        "name": "P1 capacity policy",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "team_config": {"required_role_codes": ["developer"]},
        "role_bindings": [
            {
                "role_code": "developer",
                "actor_mode": "ai",
                "status": "active",
                "capacity": capacity,
            }
        ],
    }


def test_unified_policy_freezes_positive_role_binding_capacity() -> None:
    validated = validate_unified_policy_payload(_policy_payload(2))

    assert validated["role_bindings"] == [
        {
            "actor_mode": "ai",
            "capacity": 2,
            "fallback_executor_profile_ids": [],
            "role_code": "developer",
            "status": "active",
        }
    ]


@pytest.mark.parametrize("capacity", [0, -1, True, "2"])
def test_unified_policy_rejects_invalid_role_binding_capacity(capacity: object) -> None:
    with pytest.raises(PolicyValidationError) as exc_info:
        validate_unified_policy_payload(_policy_payload(capacity))

    assert exc_info.value.code == "RD_EXECUTION_POLICY_INVALID"
