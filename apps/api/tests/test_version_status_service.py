from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.version_status import (
    build_version_advance_impact,
    canonical_requirement_status,
    validate_version_status_transition,
)


def test_version_advance_impact_normalizes_legacy_requirement_statuses():
    store = SimpleNamespace(
        requirements={
            "requirement_a": {
                "created_at": "2026-06-01T00:00:00+00:00",
                "id": "requirement_a",
                "status": "task_created",
                "title": "设计中需求",
                "version_id": "version_001",
            },
            "requirement_b": {
                "created_at": "2026-06-02T00:00:00+00:00",
                "id": "requirement_b",
                "status": "submitted",
                "title": "未审批需求",
                "version_id": "version_001",
            },
        },
    )

    impact = build_version_advance_impact(
        store,
        target_status="testing",
        version_id="version_001",
    )

    assert canonical_requirement_status("task_created") == "designing"
    assert impact["updated_requirements"] == [
        {
            "from_status": "designing",
            "id": "requirement_a",
            "title": "设计中需求",
            "to_status": "testing",
        }
    ]
    assert impact["blocked_requirements"] == [
        {
            "block_reason": "需求尚未进入可交付状态，进入测试会形成版本风险",
            "id": "requirement_b",
            "status": "submitted",
            "title": "未审批需求",
        }
    ]


def test_version_status_transition_rejects_skipped_delivery_stage():
    with pytest.raises(HTTPException) as exc_info:
        validate_version_status_transition("planning", "released")

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "PRODUCT_VERSION_STATUS_INVALID"
