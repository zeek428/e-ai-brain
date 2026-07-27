"""Opt-in, repository-backed R&D delivery regression through public APIs only."""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from full_chain_regression_rd_fixture import safe_report_value
from full_chain_regression_slug import regression_slug

_WORKER_HEARTBEAT_MAX_AGE_SECONDS = 180
_DEPLOYMENT_AUDIT_EVENTS = (
    "deployment_request.created",
    "deployment.run.started",
    "deployment_request.completed",
)


class RegressionError(AssertionError):
    pass


@dataclass(frozen=True)
class StepResult:
    name: str
    detail: str


@dataclass(frozen=True)
class RdDeliveryE2EConfig:
    product_id: str
    repository_id: str
    runner_id: str
    executor_profile_id: str
    ai_developer_id: str
    ai_tester_id: str
    reviewer_username: str
    reviewer_password: str = field(repr=False)
    timeout_seconds: int = 2400

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
    ) -> RdDeliveryE2EConfig:
        source = os.environ if env is None else env

        def required(name: str) -> str:
            value = str(source.get(name) or "").strip()
            if not value:
                raise RegressionError(f"{name} is required")
            return value

        raw_timeout = str(source.get("RD_E2E_TIMEOUT_SECONDS") or "2400").strip()
        try:
            timeout_seconds = int(raw_timeout)
        except ValueError as exc:
            raise RegressionError("RD_E2E_TIMEOUT_SECONDS must be a positive integer") from exc
        if timeout_seconds <= 0:
            raise RegressionError("RD_E2E_TIMEOUT_SECONDS must be positive")
        config = cls(
            ai_developer_id=required("RD_E2E_AI_DEVELOPER_ID"),
            ai_tester_id=required("RD_E2E_AI_TESTER_ID"),
            executor_profile_id=required("RD_E2E_EXECUTOR_PROFILE_ID"),
            product_id=required("RD_E2E_PRODUCT_ID"),
            repository_id=required("RD_E2E_REPOSITORY_ID"),
            reviewer_password=required("RD_E2E_REVIEWER_PASSWORD"),
            reviewer_username=required("RD_E2E_REVIEWER_USERNAME"),
            runner_id=required("RD_E2E_RUNNER_ID"),
            timeout_seconds=timeout_seconds,
        )
        if config.ai_developer_id == config.ai_tester_id:
            raise RegressionError("AI developer and tester identifiers must be distinct")
        return config


@dataclass(frozen=True)
class RdDeliveryPreflight:
    developer_role_code: str
    owner_user_id: str
    policy: dict[str, Any]
    repository: dict[str, Any]
    reviewer_role_code: str
    reviewer_user_id: str
    tester_role_code: str


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionError(message)


def _items(response: dict[str, Any]) -> list[dict[str, Any]]:
    items = response.get("items") or []
    return [dict(item) for item in items if isinstance(item, dict)]


def _find(items: list[dict[str, Any]], record_id: str, label: str) -> dict[str, Any]:
    item = next((item for item in items if str(item.get("id") or "") == record_id), None)
    _assert(item is not None, f"{label} {record_id} is unavailable")
    return dict(item or {})


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def validate_safety_boundary(
    config: RdDeliveryE2EConfig,
    *,
    owner_username: str,
    delivery_target: str,
    repository_default_branch: str,
    protected_branches: tuple[str, ...] = (),
    run_id: str | None = None,
    work_item_id: str | None = None,
    working_branch: str | None = None,
) -> None:
    _assert(
        owner_username.strip().casefold() != config.reviewer_username.casefold(),
        "R&D delivery requires an independent reviewer identity",
    )
    _assert(
        delivery_target == "ready_for_release",
        "R&D delivery E2E is restricted to ready_for_release",
    )
    if working_branch is None:
        return
    expected = f"rd/{run_id}/{work_item_id}" if run_id and work_item_id else ""
    _assert(
        bool(expected)
        and working_branch == expected
        and working_branch != repository_default_branch
        and working_branch not in set(protected_branches),
        "R&D delivery requires the exact isolated rd/<run-id>/<work-item-id> branch",
    )


def _role_binding(
    policy: dict[str, Any],
    *,
    actor_mode: str,
    subject_id: str,
    executor_profile_id: str | None = None,
) -> dict[str, Any]:
    id_field = (
        "candidate_ai_employee_ids"
        if actor_mode == "ai"
        else "candidate_human_user_ids"
    )
    matches = [
        dict(binding)
        for binding in policy.get("role_bindings") or []
        if isinstance(binding, dict)
        and binding.get("status") == "active"
        and binding.get("actor_mode") == actor_mode
        and subject_id in {str(item) for item in binding.get(id_field) or []}
        and (
            executor_profile_id is None
            or binding.get("primary_executor_profile_id") == executor_profile_id
        )
    ]
    _assert(len(matches) == 1, f"Policy must bind exactly one active role to {subject_id}")
    return matches[0]


def preflight_rd_delivery_e2e(
    client: Any,
    *,
    owner_username: str,
    owner_password: str,
    config: RdDeliveryE2EConfig,
) -> RdDeliveryPreflight:
    owner = client.login(owner_username, owner_password).get("user") or {}
    owner_user_id = str(owner.get("id") or "")
    _assert(owner_user_id, "Owner login did not return a user id")
    reviewer = client.login(config.reviewer_username, config.reviewer_password).get("user") or {}
    reviewer_user_id = str(reviewer.get("id") or "")
    _assert(reviewer_user_id, "Reviewer login did not return a user id")
    _assert(reviewer_user_id != owner_user_id, "R&D delivery requires an independent reviewer")
    client.login(owner_username, owner_password)

    product = client.get(f"/api/products/{config.product_id}")
    _assert(product.get("id") == config.product_id, "Configured product is unavailable")

    repositories = client.get(
        f"/api/products/{config.product_id}/git-repositories",
        {"active_only": True},
    )
    repository = _find(_items(repositories), config.repository_id, "Repository")
    _assert(repository.get("product_id") == config.product_id, "Repository product scope mismatch")
    _assert(repository.get("status") == "active", "Repository is not active")
    _assert(
        repository.get("git_provider") in {"gitlab", "github"},
        "Repository provider cannot produce trusted reconciliation",
    )
    default_branch = str(repository.get("default_branch") or "")
    _assert(default_branch, "Repository default branch is missing")

    runners = client.get(
        "/api/system/ai-executor-runners",
        {"executor_type": "codex", "status": "active"},
    )
    runner = _find(_items(runners), config.runner_id, "Codex Runner")
    _assert(runner.get("status") == "active", "Configured Runner is not active")
    _assert(runner.get("health_status") == "online", "Configured Runner is not online")
    _assert("codex" in set(runner.get("executor_types") or []), "Runner does not support Codex")

    profiles = client.get("/api/delivery/rd-executor-profiles", {"status": "active"})
    profile = _find(_items(profiles), config.executor_profile_id, "Executor profile")
    _assert(profile.get("status") == "active", "Executor profile is not active")
    _assert(profile.get("runner_id") == config.runner_id, "Executor profile Runner mismatch")
    _assert(profile.get("executor_type") == "codex", "Executor profile is not Codex")

    employees = client.get("/api/delivery/rd-ai-employees", {"status": "active"})
    developer = _find(_items(employees), config.ai_developer_id, "AI developer")
    tester = _find(_items(employees), config.ai_tester_id, "AI tester")
    _assert(
        developer.get("status") == tester.get("status") == "active",
        "Configured AI employees must be active",
    )

    policies = client.get(
        "/api/delivery/rd-task-executor-policies",
        {"product_id": config.product_id, "status": "active"},
    )
    matches = [
        item
        for item in _items(policies)
        if item.get("product_id") == config.product_id
        and item.get("status") == "active"
        and item.get("delivery_target") == "ready_for_release"
        and (item.get("git_config") or {}).get("repository_id") == config.repository_id
    ]
    _assert(len(matches) == 1, "Exactly one active ready_for_release policy is required")
    policy = matches[0]
    _assert(int(policy.get("policy_version") or 0) > 0, "Policy version is not immutable")
    _assert(
        {"implementation", "automated_testing"}.issubset(
            set((policy.get("matching_config") or {}).get("task_types") or [])
        ),
        "Policy does not match implementation and automated_testing",
    )
    _assert(
        str((policy.get("git_config") or {}).get("workspace_root") or "").strip(),
        "Policy Git workspace root is missing",
    )
    developer_binding = _role_binding(
        policy,
        actor_mode="ai",
        subject_id=config.ai_developer_id,
        executor_profile_id=config.executor_profile_id,
    )
    tester_binding = _role_binding(
        policy,
        actor_mode="ai",
        subject_id=config.ai_tester_id,
        executor_profile_id=config.executor_profile_id,
    )
    reviewer_binding = _role_binding(
        policy,
        actor_mode="human",
        subject_id=reviewer_user_id,
    )
    role_codes = {
        str(developer_binding.get("role_code") or ""),
        str(tester_binding.get("role_code") or ""),
        str(reviewer_binding.get("role_code") or ""),
    }
    _assert(
        len(role_codes) == 3 and "" not in role_codes,
        "Owner and reviewer roles must be distinct",
    )
    validate_safety_boundary(
        config,
        owner_username=owner_username,
        delivery_target=str(policy.get("delivery_target") or ""),
        repository_default_branch=default_branch,
    )

    operations = client.get("/api/system/execution-operations-overview")
    heartbeat_times = [
        parsed
        for worker in operations.get("workers") or []
        if isinstance(worker, dict)
        and (parsed := _parse_timestamp(worker.get("updated_at"))) is not None
    ]
    _assert(heartbeat_times, "Worker heartbeat evidence is missing")
    newest = max(heartbeat_times)
    age = (datetime.now(UTC) - newest.astimezone(UTC)).total_seconds()
    _assert(
        0 <= age <= _WORKER_HEARTBEAT_MAX_AGE_SECONDS,
        "Worker heartbeat evidence is stale",
    )
    return RdDeliveryPreflight(
        developer_role_code=str(developer_binding["role_code"]),
        owner_user_id=owner_user_id,
        policy=policy,
        repository=repository,
        reviewer_role_code=str(reviewer_binding["role_code"]),
        reviewer_user_id=reviewer_user_id,
        tester_role_code=str(tester_binding["role_code"]),
    )


def _wait_for(
    fetch: Any,
    predicate: Any,
    *,
    description: str,
    timeout_seconds: int,
    secret_values: tuple[str, ...],
) -> Any:
    deadline = time.monotonic() + timeout_seconds
    last_value = None
    while time.monotonic() < deadline:
        last_value = fetch()
        if predicate(last_value):
            return last_value
        time.sleep(min(0.5, max(0.05, deadline - time.monotonic())))
    raise RegressionError(
        f"{description} timed out; "
        f"last_value={safe_report_value(last_value, secret_values=secret_values)}"
    )


def validate_delivery_records(
    records: list[dict[str, Any]],
    *,
    expected_work_item_ids: tuple[str, ...],
    repository_id: str,
    run_id: str,
    secret_values: tuple[str, ...],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for work_item_id in expected_work_item_ids:
        matches = [
            item
            for item in records
            if str(item.get("work_item_id") or "") == work_item_id
            and str(item.get("repository_id") or "") == repository_id
        ]
        _assert(len(matches) == 1, f"Trusted delivery for {work_item_id} is missing")
        item = dict(matches[0])
        expected_branch = f"rd/{run_id}/{work_item_id}"
        _assert(item.get("working_branch") == expected_branch, "Delivery branch is not isolated")
        _assert(item.get("local_commit_sha"), "Delivery local commit SHA is missing")
        _assert(
            item.get("remote_commit_sha") == item.get("local_commit_sha"),
            "Delivery local and remote commit SHAs do not match",
        )
        _assert(
            item.get("reconciliation_status") == "reconciled",
            "Delivery is not reconciled",
        )
        _assert(
            item.get("reconciliation_id")
            and item.get("verified_at")
            and item.get("evidence_hash")
            and item.get("reconciliation_evidence_hash"),
            "Delivery reconciled evidence is incomplete",
        )
        selected.append(item)
    redacted = safe_report_value(selected, secret_values=secret_values)
    _assert(isinstance(redacted, list), "Delivery report projection is invalid")
    return redacted


def _work_items(client: Any, run_id: str) -> list[dict[str, Any]]:
    return _items(client.get(f"/api/delivery/rd-collaboration-runs/{run_id}/work-items"))


def _item_by_title(items: list[dict[str, Any]], title: str) -> dict[str, Any]:
    matches = [item for item in items if item.get("title") == title]
    _assert(len(matches) == 1, f"Work item {title} was not persisted exactly once")
    return matches[0]


def _wait_for_reviewing_item(
    client: Any,
    *,
    run_id: str,
    timeout_seconds: int,
    title: str,
    secret_values: tuple[str, ...],
) -> dict[str, Any]:
    return _wait_for(
        lambda: _item_by_title(_work_items(client, run_id), title),
        lambda item: item.get("status") == "reviewing" and bool(item.get("ai_task_id")),
        description=f"work item {title} awaiting review",
        timeout_seconds=timeout_seconds,
        secret_values=secret_values,
    )


def _runner_and_gate_evidence(
    client: Any,
    *,
    ai_task_id: str,
    expected_coding_runner_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    task = client.get(f"/api/ai-tasks/{ai_task_id}")
    gate = task.get("quality_gate")
    gate = gate if isinstance(gate, dict) else {}
    _assert(gate.get("status") == "passed" and gate.get("id"), "Independent quality gate failed")
    _assert(
        gate.get("verifier_trust_isolated") is True
        and isinstance(gate.get("verified_attestation_count"), int)
        and not isinstance(gate.get("verified_attestation_count"), bool)
        and gate["verified_attestation_count"] >= 1
        and isinstance(gate.get("independent_evidence_count"), int)
        and not isinstance(gate.get("independent_evidence_count"), bool)
        and gate["independent_evidence_count"] >= 1,
        "Independent quality gate is missing trusted isolation proof",
    )
    runner_tasks = _items(
        client.get(
            "/api/system/ai-executor-tasks",
            {"ai_task_id": ai_task_id, "status": "succeeded"},
        )
    )
    coding = [
        item for item in runner_tasks if str(item.get("task_kind") or "") == "coding"
    ]
    _assert(len(coding) == 1, "Exactly one successful native coding Runner task is required")
    coding_task = coding[0]
    _assert(
        coding_task.get("runner_id") == expected_coding_runner_id,
        "Native coding task did not run on the configured Runner",
    )
    _assert(coding_task.get("workspace_root"), "Native Runner workspace evidence is missing")
    verifier = [
        item
        for item in runner_tasks
        if str(item.get("task_kind") or "") == "quality_gate"
    ]
    _assert(
        len(verifier) == 1,
        "Exactly one successful quality-gate Runner task is required",
    )
    verifier_task = verifier[0]
    _assert(
        verifier_task.get("quality_gate_run_id") == gate.get("id"),
        "Quality-gate Runner task does not match the AI task gate",
    )
    verifier_runner_id = str(verifier_task.get("runner_id") or "")
    _assert(
        bool(verifier_runner_id) and verifier_runner_id != expected_coding_runner_id,
        "Quality-gate Runner is not independent from the configured coding Runner",
    )
    verifier_request_config = verifier_task.get("request_config")
    verifier_request_config = (
        verifier_request_config if isinstance(verifier_request_config, dict) else {}
    )
    _assert(
        verifier_request_config.get("required_trust_domain") == "verification",
        "Quality-gate Runner task is missing the verification trust boundary",
    )
    review_id = str((task.get("pending_review") or {}).get("id") or "")
    _assert(review_id, "AI task pending Review is missing")
    return coding_task, verifier_task, gate, review_id


def _approve_item(
    client: Any,
    *,
    config: RdDeliveryE2EConfig,
    item: dict[str, Any],
    marker: str,
    owner_password: str,
    owner_username: str,
) -> dict[str, Any]:
    reviewer = client.login(config.reviewer_username, config.reviewer_password).get("user") or {}
    _assert(
        str(reviewer.get("username") or "").casefold() == config.reviewer_username.casefold(),
        "Configured reviewer login mismatch",
    )
    approved = client.post(
        f"/api/delivery/rd-work-items/{item['id']}/review",
        {
            "comment": "Independent real E2E review approved",
            "decision": "approve",
            "idempotency_key": f"rd-e2e-review:{marker}:{item['id']}",
            "version": item["version"],
        },
    )
    client.login(owner_username, owner_password)
    approved_item = approved.get("work_item") or {}
    _assert(
        approved_item.get("status") in {"approved", "completed"},
        "Independent work-item review did not complete",
    )
    return approved_item


def validate_rd_delivery_e2e(
    client: Any,
    owner_username: str,
    owner_password: str,
    config: RdDeliveryE2EConfig,
) -> list[StepResult]:
    secrets = (owner_password, config.reviewer_password)
    preflight = preflight_rd_delivery_e2e(
        client,
        owner_password=owner_password,
        owner_username=owner_username,
        config=config,
    )
    marker = f"rd-delivery-{regression_slug()}"
    results = [
        StepResult(
            "rd_delivery_preflight",
            (
                f"product={config.product_id} / repository={config.repository_id} / "
                f"runner={config.runner_id} / policy={preflight.policy.get('id')}"
            ),
        )
    ]
    version = client.post(
        f"/api/products/{config.product_id}/versions",
        {
            "code": f"RD-E2E-{marker}",
            "description": "Opt-in real Runner delivery regression; no deployment.",
            "name": f"R&D delivery E2E {marker}",
            "status": "planning",
        },
    )
    version_id = str(version.get("id") or "")
    _assert(version_id, "Planning version creation did not return an id")
    default_branch = str(preflight.repository.get("default_branch") or "")
    version_branch = f"e2e/{marker}"
    _assert(
        version_branch != default_branch
        and version_branch not in set(preflight.repository.get("protected_branches") or []),
        "Version branch must not be protected or default",
    )
    client.post(
        f"/api/product-versions/{version_id}/branch-configs",
        {
            "base_branch": default_branch,
            "branch_status": "active",
            "creation_source": "manual",
            "description": "Isolated opt-in R&D delivery E2E branch",
            "repository_id": config.repository_id,
            "working_branch": version_branch,
        },
    )

    artifact_path = f"docs/e2e/rd-collaboration-{marker}.md"
    acceptance_criteria = [
        f"Only {artifact_path} is changed",
        "Independent quality gate and automated testing pass",
        "Delivery stops at ready_for_release without deployment",
    ]
    instruction = (
        f"Create only {artifact_path} containing requirement_id, run_id, trace_id, "
        f"and these acceptance criteria: {'; '.join(acceptance_criteria)}. "
        "Do not modify application code, dependencies, CI, deployment files, "
        "protected branches, or secrets."
    )
    requirement = client.post(
        "/api/requirements",
        {
            "content": instruction,
            "priority": "P2",
            "product_id": config.product_id,
            "source": "business_department",
            "title": f"Real R&D delivery E2E {marker}",
            "version_id": version_id,
        },
    )
    requirement_id = str(requirement.get("id") or "")
    _assert(requirement_id, "Requirement creation did not return an id")
    assessment = client.post(
        f"/api/requirements/{requirement_id}/assessments",
        {
            "reason": "opt-in real R&D delivery E2E",
            "request_id": f"rd-e2e-assessment:{marker}",
            "requirement_revision": int(requirement.get("revision") or 1),
        },
    )
    assessment_id = str(assessment.get("id") or "")
    _assert(
        assessment_id and assessment.get("initial_strategy_snapshot_id"),
        "Assessment did not freeze the active policy",
    )
    for role_code in preflight.policy.get("team_config", {}).get(
        "required_role_codes",
        [],
    ):
        opinion = client.post(
            f"/api/requirement-assessments/{assessment_id}/opinions",
            {
                "conclusion_json": {"recommendation": "accept", "scope": artifact_path},
                "confidence": 0.99,
                "evidence_refs": [{"artifact_path": artifact_path}],
                "idempotency_key": f"rd-e2e-opinion:{marker}:{role_code}",
                "risk_level": "low",
                "risk_summary": {"deployment": "prohibited", "risk_level": "low"},
                "role_code": role_code,
            },
        )
        _assert(opinion.get("id"), f"Assessment opinion for {role_code} was not recorded")
    latest = client.get(f"/api/requirements/{requirement_id}/assessments/latest")
    accepted = client.post(
        f"/api/requirement-assessments/{assessment_id}/decisions",
        {
            "comment": "Accept low-risk documentation-only E2E requirement",
            "decision": "accept",
            "idempotency_key": f"rd-e2e-assessment-decision:{marker}",
            "version": latest["version"],
        },
    )
    grouping = accepted.get("grouping") or {}
    _assert(
        (grouping.get("version") or {}).get("id") == version_id,
        "Assessment did not select the explicit E2E planning version",
    )
    scope_version = (grouping.get("version") or {}).get("scope_version")
    _assert(isinstance(scope_version, int), "Grouped version scope is missing")
    run = client.post(
        f"/api/product-versions/{version_id}/collaboration-runs",
        {
            "reason": "opt-in real R&D delivery E2E",
            "request_id": f"rd-e2e-run:{marker}",
            "scope_version": scope_version,
        },
    )
    run_id = str(run.get("id") or "")
    _assert(run_id and run.get("delivery_target") == "ready_for_release", "Run is unsafe")

    implementation_key = "implement_e2e_artifact"
    testing_key = "verify_e2e_artifact"
    git_delivery_output = {
        "local_commit_sha": "string",
        "working_branch": "rd/<run-id>/<work-item-id>",
    }
    plan = client.post(
        f"/api/delivery/rd-collaboration-runs/{run_id}/plan",
        {
            "dependencies": [
                {
                    "predecessor_work_item_id": implementation_key,
                    "successor_work_item_id": testing_key,
                }
            ],
            "work_items": [
                {
                    "acceptance_criteria": acceptance_criteria,
                    "description": (
                        f"{instruction} Return JSON matching output_contract; report only the "
                        "local commit SHA and the exact frozen collaboration branch "
                        "rd/<run-id>/<work-item-id>. Never report remote, callback, or "
                        "reconciliation evidence."
                    ),
                    "id": implementation_key,
                    "input_contract": {
                        "allowed_paths": [artifact_path],
                        "instruction": instruction,
                        "repository_id": config.repository_id,
                    },
                    "owner_role_code": preflight.developer_role_code,
                    "output_contract": {
                        "format": "json",
                        "git_delivery": git_delivery_output,
                        "required": ["summary", "git_delivery"],
                        "summary": "string",
                    },
                    "priority": 1,
                    "requirement_id": requirement_id,
                    "resource_claims": [
                        {
                            "mode": "write",
                            "path": artifact_path,
                            "repository_id": config.repository_id,
                        }
                    ],
                    "reviewer_role_code": preflight.reviewer_role_code,
                    "risk_level": "low",
                    "title": implementation_key,
                    "work_item_type": "implementation",
                },
                {
                    "acceptance_criteria": [
                        f"Verify only {artifact_path}",
                        "Return passed version-level test evidence",
                    ],
                    "description": (
                        f"Verify {artifact_path} content and repository state. Do not modify "
                        "application code, dependencies, CI, deployment files, protected "
                        "branches, or secrets. Return JSON matching output_contract; report "
                        "only the local commit SHA and exact frozen collaboration branch "
                        "rd/<run-id>/<work-item-id>, plus passed local test evidence. Never "
                        "report remote, callback, or reconciliation evidence."
                    ),
                    "id": testing_key,
                    "input_contract": {
                        "allowed_paths": [artifact_path],
                        "repository_id": config.repository_id,
                    },
                    "owner_role_code": preflight.tester_role_code,
                    "output_contract": {
                        "format": "json",
                        "git_delivery": git_delivery_output,
                        "required": ["summary", "git_delivery", "test_evidence"],
                        "summary": "string",
                        "test_evidence": {
                            "status": "passed",
                            "suite": "string",
                        },
                    },
                    "priority": 2,
                    "requirement_id": requirement_id,
                    "resource_claims": [
                        {
                            "mode": "read",
                            "path": artifact_path,
                            "repository_id": config.repository_id,
                        }
                    ],
                    "reviewer_role_code": preflight.reviewer_role_code,
                    "risk_level": "low",
                    "title": testing_key,
                    "work_item_type": "automated_testing",
                },
            ],
        },
    )
    planned = [
        dict(item)
        for item in plan.get("work_items") or []
        if isinstance(item, dict)
    ]
    implementation = _item_by_title(planned, implementation_key)
    testing = _item_by_title(planned, testing_key)
    implementation_id = str(implementation["id"])
    testing_id = str(testing["id"])

    implementation = _wait_for_reviewing_item(
        client,
        run_id=run_id,
        timeout_seconds=config.timeout_seconds,
        title=implementation_key,
        secret_values=secrets,
    )
    pre_review_snapshot = client.get(
        f"/api/delivery/rd-collaboration-runs/{run_id}/work-items"
    )
    pre_review_testing = _item_by_title(
        _items(pre_review_snapshot),
        testing_key,
    )
    pre_review_active_attempt_count = pre_review_testing.get("active_attempt_count")
    _assert(
        pre_review_testing.get("status") == "blocked"
        and not pre_review_testing.get("ai_task_id")
        and isinstance(pre_review_active_attempt_count, int)
        and not isinstance(pre_review_active_attempt_count, bool)
        and pre_review_active_attempt_count == 0,
        "Dependent automated-testing work item must remain blocked without an active attempt "
        "before implementation Review approval",
    )
    persisted_dependencies = [
        dependency
        for dependency in pre_review_snapshot.get("dependencies") or []
        if isinstance(dependency, dict)
        and dependency.get("predecessor_work_item_id") == implementation_id
        and dependency.get("successor_work_item_id") == testing_id
        and dependency.get("status") == "pending"
    ]
    _assert(
        len(persisted_dependencies) == 1,
        "Persisted implementation-to-testing dependency is missing before Review",
    )
    implementation_task_id = str(implementation["ai_task_id"])
    (
        implementation_runner,
        implementation_verifier,
        implementation_gate,
        implementation_review_id,
    ) = _runner_and_gate_evidence(
        client,
        ai_task_id=implementation_task_id,
        expected_coding_runner_id=config.runner_id,
    )
    _approve_item(
        client,
        config=config,
        item=implementation,
        marker=marker,
        owner_password=owner_password,
        owner_username=owner_username,
    )
    dispatched_testing = _wait_for(
        lambda: _item_by_title(_work_items(client, run_id), testing_key),
        lambda item: bool(item.get("ai_task_id"))
        and item.get("status") in {"running", "reviewing"},
        description="Worker auto-dispatching dependent automated testing",
        timeout_seconds=config.timeout_seconds,
        secret_values=secrets,
    )
    _assert(
        str(dispatched_testing.get("id")) == testing_id,
        "Worker dispatched a different dependent work item",
    )
    dispatched_active_attempt_count = dispatched_testing.get("active_attempt_count")
    _assert(
        isinstance(dispatched_active_attempt_count, int)
        and not isinstance(dispatched_active_attempt_count, bool)
        and dispatched_active_attempt_count >= 1,
        "Worker dispatch did not expose an active attempt for automated testing",
    )
    testing = _wait_for_reviewing_item(
        client,
        run_id=run_id,
        timeout_seconds=config.timeout_seconds,
        title=testing_key,
        secret_values=secrets,
    )
    testing_task_id = str(testing["ai_task_id"])
    testing_runner, testing_verifier, testing_gate, testing_review_id = (
        _runner_and_gate_evidence(
            client,
            ai_task_id=testing_task_id,
            expected_coding_runner_id=config.runner_id,
        )
    )
    _approve_item(
        client,
        config=config,
        item=testing,
        marker=marker,
        owner_password=owner_password,
        owner_username=owner_username,
    )

    final_run = _wait_for(
        lambda: client.get(f"/api/delivery/rd-collaboration-runs/{run_id}"),
        lambda value: value.get("status") == "completed"
        and value.get("completion_reason") == "ready_for_release"
        and bool(value.get("delivery_evidence_id"))
        and bool(value.get("delivery_evidence_hash")),
        description="trusted delivery reaching ready_for_release",
        timeout_seconds=config.timeout_seconds,
        secret_values=secrets,
    )
    deliveries = validate_delivery_records(
        _items(final_run.get("git_deliveries") or {}),
        expected_work_item_ids=(implementation_id, testing_id),
        repository_id=config.repository_id,
        run_id=run_id,
        secret_values=secrets,
    )
    testing_delivery = next(
        item for item in deliveries if item.get("work_item_id") == testing_id
    )
    _assert(
        (testing_delivery.get("test_evidence") or {}).get("status") == "passed"
        and (testing_delivery.get("test_evidence") or {}).get("suite"),
        "Automated-testing delivery is missing passed test evidence",
    )
    dashboard = client.get(f"/api/product-versions/{version_id}/dashboard")
    _assert(
        (dashboard.get("version") or {}).get("status") == "ready_for_release",
        "Product version did not stop at ready_for_release",
    )
    _assert((dashboard.get("deployments") or []) == [], "Deployment rows must remain empty")
    for event_type in _DEPLOYMENT_AUDIT_EVENTS:
        audit = client.get(
            "/api/audit/events",
            {"event_type": event_type, "page": 1, "page_size": 100},
        )
        related = [
            event
            for event in _items(audit)
            if event.get("subject_id") == run_id
            or (event.get("payload") or {}).get("collaboration_run_id") == run_id
        ]
        _assert(not related, f"Deployment audit event exists for run: {event_type}")

    results.extend(
        [
            StepResult(
                "rd_delivery_scope",
                (
                    f"version={version_id} / requirement={requirement_id} / "
                    f"assessment={assessment_id} / run={run_id}"
                ),
            ),
            StepResult(
                "rd_delivery_implementation",
                (
                    f"work_item={implementation_id} / task={implementation_task_id} / "
                    f"runner_task={implementation_runner.get('id')} / "
                    f"gate_runner_task={implementation_verifier.get('id')} / "
                    f"gate={implementation_gate.get('id')} / review={implementation_review_id}"
                ),
            ),
            StepResult(
                "rd_delivery_automated_testing",
                (
                    f"work_item={testing_id} / task={testing_task_id} / "
                    f"runner_task={testing_runner.get('id')} / "
                    f"gate_runner_task={testing_verifier.get('id')} / "
                    f"gate={testing_gate.get('id')} / review={testing_review_id}"
                ),
            ),
            StepResult(
                "rd_delivery_evidence",
                " / ".join(
                    f"delivery={item.get('id')}:{item.get('reconciliation_status')}"
                    for item in deliveries
                ),
            ),
            StepResult(
                "rd_delivery_ready_for_release",
                (
                    f"run={run_id}:completed(ready_for_release) / "
                    f"version={version_id}:ready_for_release / deployment=not_requested"
                ),
            ),
        ]
    )
    return results
