"""Reusable v2 R&D collaboration fixture helpers for public-API regressions."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RdFixtureSpec:
    marker: str
    product_id: str
    repository_id: str | None
    role_bindings: tuple[dict[str, Any], ...]
    required_role_codes: tuple[str, ...]
    work_items: tuple[dict[str, Any], ...]
    dependencies: tuple[dict[str, Any], ...]
    policy_overrides: dict[str, Any]


@dataclass(frozen=True)
class RdFixtureResult:
    assessment_id: str
    product_id: str
    requirement_id: str
    run_id: str
    scope_version: int
    strategy_snapshot_id: str
    version_id: str
    work_items: tuple[dict[str, Any], ...]


def _safe_summary(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _safe_summary(item)
            for key, item in value.items()
            if not any(
                sensitive in key.lower()
                for sensitive in (
                    "token",
                    "secret",
                    "credential",
                    "authorization",
                    "cookie",
                )
            )
        }
    if isinstance(value, list):
        return [_safe_summary(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_safe_summary(item) for item in value)
    return value


def safe_report_value(value: Any) -> Any:
    """Return a recursively redacted value suitable for regression reports."""
    return _safe_summary(value)


def frozen_ai_and_human_role_bindings(
    *,
    ai_employee_id: str,
    executor_profile_id: str,
    role_code: str,
    reviewer_user_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the immutable AI owner and independent human reviewer bindings."""
    assert ai_employee_id and executor_profile_id and role_code and reviewer_user_id
    assert ai_employee_id != reviewer_user_id, "AI owner and human reviewer must be distinct"
    return (
        {
            "actor_mode": "ai",
            "candidate_ai_employee_ids": [ai_employee_id],
            "primary_executor_profile_id": executor_profile_id,
            "role_code": role_code,
            "status": "active",
        },
        {
            "actor_mode": "human",
            "candidate_human_user_ids": [reviewer_user_id],
            "role_code": role_code,
            "status": "active",
        },
    )


def wait_for_value(
    fetch: Callable[[], Any],
    predicate: Callable[[Any], bool],
    *,
    timeout_seconds: float,
    description: str,
) -> Any:
    deadline = time.monotonic() + timeout_seconds
    last_value = None
    while time.monotonic() < deadline:
        last_value = fetch()
        if predicate(last_value):
            return last_value
        time.sleep(min(0.5, max(0.05, deadline - time.monotonic())))
    raise AssertionError(f"{description} timed out; last_value={_safe_summary(last_value)}")


def complete_and_review_human_work_item(
    client: Any,
    marker: str,
    work_item: dict[str, Any],
) -> dict[str, Any]:
    claimed = client.post(
        f"/api/delivery/rd-work-items/{work_item['id']}/claim",
        {
            "expected_version": work_item["version"],
            "idempotency_key": f"claim:{marker}:{work_item['id']}",
            "lease_seconds": 60,
        },
    )
    attempt = claimed.get("attempt") or {}
    claimed_item = claimed.get("work_item") or {}
    lease_token = str(claimed.get("lease_token") or "")
    assert lease_token, f"Work-item claim missed lease token: {_safe_summary(claimed)}"
    assert attempt.get("id"), f"Work-item claim missed attempt: {_safe_summary(claimed)}"
    assert claimed_item.get("status") == "running", (
        f"Work item was not running after claim: {_safe_summary(claimed)}"
    )

    submitted = client.post(
        f"/api/delivery/rd-work-items/{work_item['id']}/submit",
        {
            "attempt_id": attempt["id"],
            "evidence": {
                "marker": marker,
                "status": "passed",
                "work_item_type": work_item.get("work_item_type"),
            },
            "idempotency_key": f"submit:{marker}:{work_item['id']}",
            "lease_token": lease_token,
            "output": {"marker": marker, "summary": "R&D regression work completed"},
            "version": claimed_item["version"],
        },
    )
    submitted_item = submitted.get("work_item") or {}
    assert submitted_item.get("status") == "reviewing", (
        f"Work item was not awaiting independent review: {_safe_summary(submitted)}"
    )

    reviewed = client.post(
        f"/api/delivery/rd-work-items/{work_item['id']}/review",
        {
            "comment": "Full-chain regression independent review approved",
            "decision": "approve",
            "idempotency_key": f"review:{marker}:{work_item['id']}",
            "version": submitted_item["version"],
        },
    )
    reviewed_item = reviewed.get("work_item") or {}
    assert reviewed_item.get("status") == "completed", (
        f"Work item was not completed after independent review: {_safe_summary(reviewed)}"
    )
    assert (reviewed.get("feedback") or {}).get("id"), (
        "Independent review did not create immutable feedback attribution: "
        f"{_safe_summary(reviewed)}"
    )
    return reviewed_item


def create_rd_fixture(
    client: Any,
    *,
    owner_user_id: str,
    spec: RdFixtureSpec,
) -> RdFixtureResult:
    """Create a requirement-scoped v2 collaboration run and its planned DAG."""
    del owner_user_id

    requirement = client.post(
        "/api/requirements",
        {
            "content": f"{spec.marker}: validate requirement-driven R&D collaboration",
            "priority": "P1",
            "product_id": spec.product_id,
            "source": "business_department",
            "title": f"R&D collaboration regression {spec.marker}",
        },
    )
    requirement_id = str(requirement.get("id") or "")
    assert requirement_id, f"Requirement creation did not return id: {_safe_summary(requirement)}"

    assessment = client.post(
        f"/api/requirements/{requirement_id}/assessments",
        {
            "reason": "full-chain regression",
            "request_id": f"assessment:{spec.marker}",
            "requirement_revision": 1,
        },
    )
    assessment_id = str(assessment.get("id") or "")
    assert assessment_id, f"Assessment creation did not return id: {_safe_summary(assessment)}"
    assert assessment["initial_strategy_snapshot_id"]
    strategy_snapshot_id = str(assessment["initial_strategy_snapshot_id"])

    for role_code in spec.required_role_codes:
        opinion = client.post(
            f"/api/requirement-assessments/{assessment_id}/opinions",
            {
                "conclusion_json": {"marker": spec.marker, "recommendation": "accept"},
                "confidence": 0.9,
                "evidence_refs": [{"marker": spec.marker, "role_code": role_code}],
                "idempotency_key": f"opinion:{spec.marker}:{role_code}",
                "risk_level": "low",
                "risk_summary": {"risk_level": "low"},
                "role_code": role_code,
            },
        )
        assert opinion.get("id"), f"Assessment opinion was not recorded: {_safe_summary(opinion)}"

    latest_assessment = client.get(f"/api/requirements/{requirement_id}/assessments/latest")
    assert latest_assessment.get("id") == assessment_id and latest_assessment.get("version"), (
        "Assessment opinion writes did not return a versioned assessment: "
        f"{_safe_summary(latest_assessment)}"
    )
    accepted = client.post(
        f"/api/requirement-assessments/{assessment_id}/decisions",
        {
            "comment": "Full-chain regression accepts the complete assessment",
            "decision": "accept",
            "idempotency_key": f"assessment-decision:{spec.marker}",
            "version": latest_assessment["version"],
        },
    )
    grouping = accepted.get("grouping") or {}
    version = grouping.get("version") or {}
    version_id = str(version.get("id") or "")
    assert grouping["status"] == "planned"
    assert grouping["version"]["id"] == version_id
    scope_version = version.get("scope_version")
    assert isinstance(scope_version, int), (
        f"Grouping response missed updated version scope: {_safe_summary(grouping)}"
    )

    run = client.post(
        f"/api/product-versions/{version_id}/collaboration-runs",
        {
            "reason": "full-chain regression",
            "request_id": f"collaboration-run:{spec.marker}",
            "scope_version": scope_version,
        },
    )
    run_id = str(run.get("id") or "")
    assert run_id, f"Collaboration run was not created: {_safe_summary(run)}"
    assert run["strategy_snapshot_kind"] == "version_resolved"
    assert run["delivery_target"] == "ready_for_release"

    plan = client.post(
        f"/api/delivery/rd-collaboration-runs/{run_id}/plan",
        {
            "dependencies": list(spec.dependencies),
            "work_items": list(spec.work_items),
        },
    )
    work_items = tuple(plan.get("work_items") or [])
    assert work_items, f"Collaboration plan did not return work items: {_safe_summary(plan)}"
    return RdFixtureResult(
        assessment_id=assessment_id,
        product_id=spec.product_id,
        requirement_id=requirement_id,
        run_id=run_id,
        scope_version=scope_version,
        strategy_snapshot_id=strategy_snapshot_id,
        version_id=version_id,
        work_items=work_items,
    )
