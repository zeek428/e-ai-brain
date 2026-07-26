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

from full_chain_regression_rd_fixture import (
    RdFixtureSpec,
    complete_and_review_human_work_item,
    create_rd_fixture,
)
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
    resource_claims: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    item = {
        "acceptance_criteria": ["Regression evidence is recorded"],
        "description": f"Full-chain regression work item: {item_id}",
        "id": item_id,
        "owner_role_code": owner_role_code,
        "priority": priority,
        "reviewer_role_code": reviewer_role_code,
        "title": item_id,
        "work_item_type": work_item_type,
    }
    if resource_claims:
        item["resource_claims"] = resource_claims
    return item


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

    implementation_id = f"implementation-{slug}"
    integration_id = f"integration-{slug}"
    repository_id = f"regression-repository-{slug}"
    fixture = create_rd_fixture(
        client,
        owner_user_id=user_id,
        spec=RdFixtureSpec(
            dependencies=(
                {
                    "predecessor_work_item_id": implementation_id,
                    "successor_work_item_id": integration_id,
                },
            ),
            marker=marker,
            policy_overrides={},
            product_id=product_id,
            repository_id=repository_id,
            required_role_codes=(developer_role, tester_role),
            role_bindings=(
                _human_binding(role_code=developer_role, user_id=user_id),
                _human_binding(role_code=tester_role, user_id=user_id),
            ),
            work_items=(
                _work_item(
                    item_id=implementation_id,
                    owner_role_code=developer_role,
                    priority=1,
                    resource_claims=[
                        {
                            "repository_id": repository_id,
                            "path": "docs/full-chain-regression.md",
                            "mode": "write",
                        }
                    ],
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
            ),
        ),
    )
    _assert(
        fixture.version_id == version_id,
        "Accepted assessment did not deterministically select the compatible version: "
        f"expected={version_id} actual={fixture.version_id}",
    )
    results.append(
        StepResult(
            "requirement_assessment_and_grouping",
            f"requirement={fixture.requirement_id} / version={fixture.version_id}",
        )
    )

    planned_items = fixture.work_items
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
        f"DAG plan did not preserve the dependency gate: {planned_items}",
    )
    complete_and_review_human_work_item(client, marker, implementation)

    after_implementation = client.get(
        f"/api/delivery/rd-collaboration-runs/{fixture.run_id}/work-items"
    )
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
    complete_and_review_human_work_item(client, marker, integration)

    final_run = client.get(f"/api/delivery/rd-collaboration-runs/{fixture.run_id}")
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
            f"run={fixture.run_id} / status={final_run.get('status')} / deployment=not_requested",
        )
    )
    return results
