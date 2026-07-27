from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from full_chain_regression_rd_fixture import (
    RdFixtureResult,
    RdFixtureSpec,
    create_rd_fixture,
    wait_for_value,
)
from full_chain_regression_rd_runner_protocol import (
    SimulatedRunnerSession,
    create_simulated_runner_session,
    simulated_runner_role_bindings,
)

REGRESSION_OBJECTIVE_DOMAINS: tuple[tuple[str, str], ...] = (
    ("user_feedback_to_requirement", "用户反馈转需求"),
    ("requirement_version_scheduling", "需求归入迭代版本"),
    ("ai_task_review", "AI 任务与 Review"),
    ("knowledge_deposit", "知识沉淀"),
    ("knowledge_index_health", "知识索引健康"),
    ("version_branch", "迭代版本代码分支"),
    ("code_inspection_governance", "代码巡检治理闭环"),
    ("bug_remediation", "Bug 和整改任务写回"),
    ("runner_reliability", "Runner 运行可靠性"),
    ("assistant_draft_governance", "AI 动作确认中心"),
    ("version_dashboard", "版本总览"),
    ("release_blockers", "发布阻塞项"),
    ("full_chain_trace", "需求全链路聚合"),
    ("team_dashboard", "IT 团队看板"),
    ("assistant_qa", "AI 助手问答"),
    ("permission_visibility", "权限可视化"),
    ("rd_collaboration", "需求驱动研发协作"),
)
REGRESSION_OBJECTIVE_DOMAIN_KEYS = tuple(key for key, _label in REGRESSION_OBJECTIVE_DOMAINS)
REGRESSION_OBJECTIVE_DOMAIN_LABELS = {
    key: label for key, label in REGRESSION_OBJECTIVE_DOMAINS
}
REGRESSION_TARGETED_SUITE_NAMES = (
    "runner-reliability",
    "version-dashboard",
    "assistant-qa",
    "assistant-draft-governance",
    "code-inspection-governance",
    "knowledge-index-health",
    "permission-visibility",
    "rd-collaboration",
)
REGRESSION_TARGETED_DOMAIN_KEYS = tuple(
    key
    for key in REGRESSION_OBJECTIVE_DOMAIN_KEYS
    if key
    in {
        "ai_task_review",
        "assistant_qa",
        "assistant_draft_governance",
        "bug_remediation",
        "code_inspection_governance",
        "knowledge_index_health",
        "permission_visibility",
        "release_blockers",
        "requirement_version_scheduling",
        "runner_reliability",
        "rd_collaboration",
        "version_branch",
        "version_dashboard",
    }
)
REGRESSION_SUITE_DOMAINS: dict[str, tuple[str, ...]] = {
    "full": REGRESSION_OBJECTIVE_DOMAIN_KEYS,
    "all-targeted": REGRESSION_TARGETED_DOMAIN_KEYS,
    "runner-reliability": ("runner_reliability",),
    "version-dashboard": (
        "requirement_version_scheduling",
        "ai_task_review",
        "version_branch",
        "bug_remediation",
        "version_dashboard",
        "release_blockers",
    ),
    "assistant-draft-governance": ("assistant_draft_governance",),
    "assistant-qa": (
        "requirement_version_scheduling",
        "ai_task_review",
        "version_dashboard",
        "release_blockers",
        "assistant_qa",
    ),
    "code-inspection-governance": (
        "version_branch",
        "code_inspection_governance",
        "bug_remediation",
        "version_dashboard",
    ),
    "knowledge-index-health": ("knowledge_index_health",),
    "permission-visibility": ("permission_visibility",),
    "rd-collaboration": ("rd_collaboration",),
    "rd-delivery-e2e": ("rd_collaboration",),
}


@dataclass(frozen=True)
class V2CollaborationSetup:
    fixture: RdFixtureResult
    session: SimulatedRunnerSession


class _RequirementScopedFixtureClient:
    def __init__(
        self,
        client: Any,
        requirement: dict[str, Any] | None,
    ) -> None:
        self._client = client
        self._requirement = requirement

    def get(self, path: str, query=None, *, headers=None):
        return self._client.get(path, query, headers=headers)

    def post(self, path: str, body=None, *, headers=None):
        if path == "/api/requirements":
            if self._requirement is None:
                self._requirement = self._client.post(path, body, headers=headers)
            return self._requirement
        if (
            path.startswith("/api/delivery/rd-collaboration-runs/")
            and path.endswith("/plan")
        ):
            requirement_id = str((self._requirement or {}).get("id") or "")
            assert requirement_id, "Collaboration plan requires its frozen requirement"
            plan_body = dict(body or {})
            plan_body["work_items"] = [
                {**item, "requirement_id": requirement_id}
                for item in plan_body.get("work_items") or []
            ]
            return self._client.post(path, plan_body, headers=headers)
        return self._client.post(path, body, headers=headers)


def create_v2_collaboration_setup(
    client: Any,
    *,
    dependencies: tuple[dict[str, Any], ...],
    marker: str,
    matching_task_types: tuple[str, ...] = (),
    owner_user_id: str,
    product_id: str,
    repository_id: str | None,
    requirement: dict[str, Any] | None,
    work_items: tuple[dict[str, Any], ...],
    workspace_root: str,
) -> V2CollaborationSetup:
    ai_role_code = f"simulated-ai-{marker}"
    assessment_role_code = f"simulated-assessor-{marker}"
    human_role_code = f"simulated-reviewer-{marker}"
    session = create_simulated_runner_session(
        client,
        marker=marker,
        workspace_root=workspace_root,
        role_codes=(ai_role_code,),
    )
    client.request(
        "PATCH",
        f"/api/delivery/rd-executor-profiles/{session.executor_profile_id}",
        body={
            "workspace_capabilities": {
                "assessment_workspace_root": workspace_root,
                "workspace_root": workspace_root,
            }
        },
    )
    for role_code, name, assignable_subject_types in (
        (ai_role_code, f"Simulated AI role {marker}", ["ai_employee"]),
        (
            assessment_role_code,
            f"Simulated assessor role {marker}",
            ["human_user"],
        ),
        (
            human_role_code,
            f"Simulated reviewer role {marker}",
            ["human_user"],
        ),
    ):
        client.post(
            "/api/delivery/rd-roles",
            {
                "assignable_subject_types": assignable_subject_types,
                "capabilities": ["delivery"],
                "code": role_code,
                "maximum_risk_level": "high",
                "name": name,
                "responsibilities": ["delivery"],
                "status": "active",
            },
        )
    ai_binding, human_binding = simulated_runner_role_bindings(
        session,
        role_code=ai_role_code,
        reviewer_user_id=owner_user_id,
    )
    role_bindings = (
        ai_binding,
        {**human_binding, "role_code": assessment_role_code},
        {**human_binding, "role_code": human_role_code},
    )
    git_config = {"workspace_root": workspace_root}
    if repository_id:
        git_config["repository_id"] = repository_id
    policy_response = client.post(
        "/api/delivery/rd-task-executor-policies",
        {
            "assessment_config": {},
            "autonomy_config": {"mode": "single_pass"},
            "brain_app_id": "rd_brain",
            "delivery_target": "ready_for_release",
            "deployment_config": {},
            "experience_reuse_config": {},
            "git_config": git_config,
            "iteration_config": {"max_requirements": 5},
            "matching_config": {
                "task_types": sorted(
                    {
                        str(item.get("work_item_type") or "")
                        for item in work_items
                        if item.get("work_item_type")
                    }.union(matching_task_types)
                )
            },
            "name": f"Simulated v2 policy {marker}",
            "product_id": product_id,
            "quality_gate_config": {},
            "role_bindings": list(role_bindings),
            "status": "active",
            "team_config": {
                "required_role_codes": [assessment_role_code]
            },
        },
    )
    assert (policy_response.get("policy") or {}).get("id"), (
        f"Simulated v2 policy was not created: {policy_response}"
    )
    fixture_client = _RequirementScopedFixtureClient(client, requirement)
    fixture = create_rd_fixture(
        fixture_client,
        owner_user_id=owner_user_id,
        spec=RdFixtureSpec(
            dependencies=dependencies,
            marker=marker,
            policy_overrides={},
            product_id=product_id,
            repository_id=repository_id,
            required_role_codes=(assessment_role_code,),
            role_bindings=role_bindings,
            work_items=work_items,
        ),
    )
    return V2CollaborationSetup(fixture=fixture, session=session)


def wait_for_ai_work_item(
    client: Any,
    *,
    run_id: str,
    status: str,
    timeout_seconds: float,
    work_item_id: str,
) -> dict[str, Any]:
    def fetch() -> dict[str, Any]:
        response = client.get(
            f"/api/delivery/rd-collaboration-runs/{run_id}/work-items"
        )
        return next(
            (
                item
                for item in response.get("items") or []
                if item.get("id") == work_item_id
            ),
            {},
        )

    return wait_for_value(
        fetch,
        lambda item: item.get("status") == status,
        timeout_seconds=timeout_seconds,
        description=f"v2 collaboration work item {work_item_id} entering {status}",
    )


def approve_high_risk_dispatch(
    client: Any,
    *,
    marker: str,
    run_id: str,
    timeout_seconds: float,
    work_item_id: str,
) -> dict[str, Any]:
    paused = wait_for_ai_work_item(
        client,
        run_id=run_id,
        status="waiting_human",
        timeout_seconds=timeout_seconds,
        work_item_id=work_item_id,
    )
    assert not paused.get("ai_task_id"), (
        f"High-risk work item dispatched before approval: {paused}"
    )
    decision_id = str(paused.get("suspended_decision_request_id") or "")
    assert decision_id, f"High-risk work item missed dispatch decision: {paused}"
    decision = client.get(f"/api/delivery/decision-requests/{decision_id}")
    assert decision.get("status") == "pending", (
        f"High-risk dispatch decision was not pending: {decision}"
    )
    approved = client.post(
        f"/api/delivery/decision-requests/{decision_id}/decide",
        {
            "comment": "Regression approves high-risk code-review dispatch",
            "idempotency_key": f"approve-dispatch:{marker}:{work_item_id}",
            "input": {},
            "selected_option": "approve_dispatch",
            "version": decision["version"],
        },
    )
    assert (approved.get("decision_request") or approved).get("status") == "approved", (
        f"High-risk dispatch decision was not approved: {approved}"
    )
    return approved


def regression_suite_coverage(suite: str) -> dict[str, Any]:
    covered_keys = list(REGRESSION_SUITE_DOMAINS.get(suite, ()))
    covered_key_set = set(covered_keys)
    skipped_keys = [
        key for key in REGRESSION_OBJECTIVE_DOMAIN_KEYS if key not in covered_key_set
    ]
    return {
        "covered": [
            {"key": key, "label": REGRESSION_OBJECTIVE_DOMAIN_LABELS[key]}
            for key in covered_keys
        ],
        "covered_domain_count": len(covered_keys),
        "covered_keys": covered_keys,
        "is_complete_chain": not skipped_keys,
        "objective_domain_count": len(REGRESSION_OBJECTIVE_DOMAIN_KEYS),
        "skipped": [
            {"key": key, "label": REGRESSION_OBJECTIVE_DOMAIN_LABELS[key]}
            for key in skipped_keys
        ],
        "skipped_keys": skipped_keys,
        "suite": suite,
    }
