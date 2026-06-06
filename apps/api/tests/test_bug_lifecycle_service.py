from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.bug_lifecycle import (
    ensure_bug_status_transition,
    initial_bug_status,
    validate_bug_context,
    validate_bug_enums,
)


def test_bug_lifecycle_initial_status_handles_ai_and_duplicate_sources():
    assert (
        initial_bug_status(
            SimpleNamespace(
                duplicate_of_bug_id=None,
                reproduce_steps=[],
                source="ai_auto_test",
            ),
        )
        == "needs_info"
    )
    assert (
        initial_bug_status(
            SimpleNamespace(
                duplicate_of_bug_id="bug_001",
                reproduce_steps=["复现步骤"],
                source="manual_test",
            ),
        )
        == "closed"
    )
    assert (
        initial_bug_status(
            SimpleNamespace(
                duplicate_of_bug_id=None,
                reproduce_steps=["复现步骤"],
                source="manual_test",
            ),
        )
        == "open"
    )


def test_bug_lifecycle_rejects_invalid_status_transition():
    with pytest.raises(HTTPException) as exc_info:
        ensure_bug_status_transition("closed", "triaged")

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "BUG_STATE_INVALID"


def test_bug_lifecycle_validates_context_and_enums():
    validate_bug_enums(source="manual_test", severity="major", status="open")
    store = SimpleNamespace(
        ai_tasks={"task_001": {"id": "task_001", "product_id": "product_001"}},
        bugs={"bug_001": {"id": "bug_001", "product_id": "product_001"}},
        product_modules={"module_001": {"code": "core", "product_id": "product_001"}},
        product_versions={"version_001": {"id": "version_001", "product_id": "product_001"}},
        products={"product_001": {"id": "product_001"}},
        requirements={"requirement_001": {"id": "requirement_001", "product_id": "product_001"}},
    )

    validate_bug_context(
        store,
        duplicate_of_bug_id="bug_001",
        module_code="core",
        product_id="product_001",
        related_task_id="task_001",
        requirement_id="requirement_001",
        version_id="version_001",
    )

    with pytest.raises(HTTPException) as exc_info:
        validate_bug_context(
            store,
            bug_id="bug_001",
            duplicate_of_bug_id="bug_001",
            product_id="product_001",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "VALIDATION_ERROR"
