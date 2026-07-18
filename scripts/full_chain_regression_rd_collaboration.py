"""Public-API smoke regression for the requirement-driven R&D control plane.

This suite intentionally stops after independent approval of the version-level
integration work item.  Trusted Git delivery, remote reconciliation, and the
``ready_for_release`` transition are covered by the repository-backed delivery
suite because no public API accepts user-supplied remote commit evidence.  It
does not create a deployment request or call a deployment endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from full_chain_regression_slug import regression_slug


@dataclass
class StepResult:
    name: str
    detail: str


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _role_payload(*, code: str, name: str) -> dict[str, Any]:
    return {
        "assignable_subject_types": ["human_user"],
        "capabilities": ["delivery"],
        "code": code,
        "maximum_risk_level": "high",
        "name": name,
        "responsibilities": ["delivery"],
        "status": "active",
    }


def _human_binding(*, role_code: str, user_id: str) -> dict[str, Any]:
    return {
        "actor_mode": "human",
        "candidate_human_user_ids": [user_id],
        "role_code": role_code,
        "status": "active",
    }


def _work_item(
    *,
    item_id: str,
    owner_role_code: str,
    reviewer_role_code: str,
    work_item_type: str,
    priority: int,
) -> dict[str, Any]:
    return {
        "acceptance_criteria": ["Regression evidence is recorded"],
        "description": f"Full-chain regression work item: {item_id}",
        "id": item_id,
        "owner_role_code": owner_role_code,
        "priority": priority,
        "reviewer_role_code": reviewer_role_code,
        "title": item_id,
        "work_item_type": work_item_type,
    }


def _complete_and_approve_work_item(
    client: Any,
    *,
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
    _assert(lease_token, f"Work-item claim missed lease token: {claimed}")
    _assert(attempt.get("id"), f"Work-item claim missed attempt: {claimed}")
    _assert(
        claimed_item.get("status") == "running",
        f"Work item was not running after claim: {claimed}",
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
    _assert(
        submitted_item.get("status") == "reviewing",
        f"Work item was not awaiting independent review: {submitted}",
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
    _assert(
        reviewed_item.get("status") == "completed",
        f"Work item was not completed after independent review: {reviewed}",
    )
    _assert(
        (reviewed.get("feedback") or {}).get("id"),
        f"Independent review did not create immutable feedback attribution: {reviewed}",
    )
    return reviewed_item


def validate_rd_collaboration_quick_regression(
    client: Any,
    *,
    username: str,
    password: str,
) -> list[StepResult]:
    """Exercise the public P0 control-plane lifecycle without deployment."""
    slug = regression_slug()
    marker = f"rd-collaboration-{slug}"
    developer_role = f"developer-{slug}"
    tester_role = f"tester-{slug}"
    results: list[StepResult] = []

    user = client.login(username, password).get("user") or {}
    user_id = str(user.get("id") or "")
    _assert(user_id, f"Login response missed the user identity: {user}")
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    product = client.post(
        "/api/products",
        {"code": marker, "name": f"R&D collaboration regression {slug}"},
    )
    product_id = str(product.get("id") or "")
    _assert(product_id, f"Product creation did not return id: {product}")
    version = client.post(
        f"/api/products/{product_id}/versions",
        {"code": f"RD-{slug}", "name": f"R&D collaboration {slug}", "status": "planning"},
    )
    version_id = str(version.get("id") or "")
    _assert(version_id, f"Planning version creation did not return id: {version}")

    developer = client.post(
        "/api/delivery/rd-roles",
        _role_payload(code=developer_role, name="R&D regression developer"),
    )
    tester = client.post(
        "/api/delivery/rd-roles",
        _role_payload(code=tester_role, name="R&D regression tester"),
    )
    _assert(developer.get("id"), f"Developer role was not created: {developer}")
    _assert(tester.get("id"), f"Tester role was not created: {tester}")

    policy_response = client.post(
        "/api/delivery/rd-task-executor-policies",
        {
            "assessment_config": {},
            "autonomy_config": {"mode": "single_pass"},
            "brain_app_id": "rd_brain",
            "delivery_target": "ready_for_release",
            "deployment_config": {},
            "experience_reuse_config": {},
            "git_config": {},
            "iteration_config": {"max_requirements": 5},
            "matching_config": {"task_types": ["implementation", "integration"]},
            "name": f"R&D collaboration regression policy {slug}",
            "product_id": product_id,
            "quality_gate_config": {},
            "role_bindings": [
                _human_binding(role_code=developer_role, user_id=user_id),
                _human_binding(role_code=tester_role, user_id=user_id),
            ],
            "status": "active",
            "team_config": {"required_role_codes": [developer_role, tester_role]},
        },
    )
    policy = policy_response.get("policy") or {}
    _assert(policy.get("id"), f"Unified policy was not created: {policy_response}")
    _assert(
        policy.get("delivery_target") == "ready_for_release",
        f"P0 policy delivery target drifted: {policy}",
    )

    requirement = client.post(
        "/api/requirements",
        {
            "content": f"{marker}: validate requirement-driven R&D collaboration",
            "priority": "P1",
            "product_id": product_id,
            "source": "business_department",
            "title": f"R&D collaboration regression {slug}",
        },
    )
    requirement_id = str(requirement.get("id") or "")
    _assert(requirement_id, f"Requirement creation did not return id: {requirement}")

    assessment = client.post(
        f"/api/requirements/{requirement_id}/assessments",
        {
            "reason": "full-chain regression",
            "request_id": f"assessment:{marker}",
            "requirement_revision": 1,
        },
    )
    assessment_id = str(assessment.get("id") or "")
    _assert(assessment_id, f"Assessment creation did not return id: {assessment}")
    _assert(
        assessment.get("initial_strategy_snapshot_id"),
        f"Assessment did not freeze a policy snapshot: {assessment}",
    )

    for role_code in (developer_role, tester_role):
        opinion = client.post(
            f"/api/requirement-assessments/{assessment_id}/opinions",
            {
                "conclusion_json": {"marker": marker, "recommendation": "accept"},
                "confidence": 0.9,
                "evidence_refs": [{"marker": marker, "role_code": role_code}],
                "idempotency_key": f"opinion:{marker}:{role_code}",
                "risk_level": "low",
                "risk_summary": {"risk_level": "low"},
                "role_code": role_code,
            },
        )
        _assert(opinion.get("id"), f"Assessment opinion was not recorded: {opinion}")

    latest_assessment = client.get(f"/api/requirements/{requirement_id}/assessments/latest")
    _assert(
        latest_assessment.get("id") == assessment_id and latest_assessment.get("version"),
        f"Assessment opinion writes did not return a versioned assessment: {latest_assessment}",
    )
    accepted = client.post(
        f"/api/requirement-assessments/{assessment_id}/decisions",
        {
            "comment": "Full-chain regression accepts the complete assessment",
            "decision": "accept",
            "idempotency_key": f"assessment-decision:{marker}",
            "version": latest_assessment["version"],
        },
    )
    grouping = accepted.get("grouping") or {}
    grouped_version = grouping.get("version") or {}
    _assert(
        grouping.get("status") == "planned" and grouped_version.get("id") == version_id,
        f"Accepted assessment did not deterministically select the compatible version: {accepted}",
    )
    _assert(
        grouped_version.get("scope_version"),
        f"Grouping response missed updated version scope: {grouping}",
    )
    results.append(
        StepResult(
            "requirement_assessment_and_grouping",
            f"requirement={requirement_id} / version={version_id}",
        )
    )

    run = client.post(
        f"/api/product-versions/{version_id}/collaboration-runs",
        {
            "reason": "full-chain regression",
            "request_id": f"collaboration-run:{marker}",
            "scope_version": grouped_version["scope_version"],
        },
    )
    run_id = str(run.get("id") or "")
    _assert(run_id, f"Collaboration run was not created: {run}")
    _assert(
        run.get("strategy_snapshot_kind") == "version_resolved",
        f"Collaboration run did not freeze a version-resolved policy: {run}",
    )

    implementation_id = f"implementation-{slug}"
    integration_id = f"integration-{slug}"
    plan = client.post(
        f"/api/delivery/rd-collaboration-runs/{run_id}/plan",
        {
            "dependencies": [
                {
                    "predecessor_work_item_id": implementation_id,
                    "successor_work_item_id": integration_id,
                }
            ],
            "work_items": [
                _work_item(
                    item_id=implementation_id,
                    owner_role_code=developer_role,
                    priority=1,
                    reviewer_role_code=tester_role,
                    work_item_type="implementation",
                ),
                _work_item(
                    item_id=integration_id,
                    owner_role_code=tester_role,
                    priority=2,
                    reviewer_role_code=developer_role,
                    work_item_type="integration",
                ),
            ],
        },
    )
    planned_items = plan.get("work_items") or []
    implementation = next(
        (
            item
            for item in planned_items
            if item.get("work_item_type") == "implementation"
            and item.get("title") == implementation_id
        ),
        {},
    )
    integration = next(
        (
            item
            for item in planned_items
            if item.get("work_item_type") == "integration" and item.get("title") == integration_id
        ),
        {},
    )
    _assert(
        implementation.get("status") == "ready" and integration.get("status") == "blocked",
        f"DAG plan did not preserve the dependency gate: {plan}",
    )
    _complete_and_approve_work_item(client, marker=marker, work_item=implementation)

    after_implementation = client.get(f"/api/delivery/rd-collaboration-runs/{run_id}/work-items")
    integration = next(
        (
            item
            for item in after_implementation.get("items") or []
            if item.get("work_item_type") == "integration" and item.get("title") == integration_id
        ),
        {},
    )
    _assert(
        integration.get("status") == "ready",
        f"Integration item was not released after prerequisite review: {after_implementation}",
    )
    _complete_and_approve_work_item(client, marker=marker, work_item=integration)

    final_run = client.get(f"/api/delivery/rd-collaboration-runs/{run_id}")
    _assert(
        final_run.get("status") == "verifying",
        f"Approved version-level integration did not advance the run to verifying: {final_run}",
    )
    _assert(
        final_run.get("delivery_target") == "ready_for_release",
        f"Run delivery target drifted from the frozen P0 policy: {final_run}",
    )
    results.append(
        StepResult(
            "collaboration_dag_and_independent_review",
            f"run={run_id} / status={final_run.get('status')} / deployment=not_requested",
        )
    )
    return results
