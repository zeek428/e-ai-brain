from __future__ import annotations

import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import full_chain_regression as regression_cli  # noqa: E402
from full_chain_regression_rd_delivery_e2e import (  # noqa: E402
    RdDeliveryE2EConfig,
    RegressionError,
    preflight_rd_delivery_e2e,
    validate_delivery_records,
    validate_rd_delivery_e2e,
    validate_safety_boundary,
)
from full_chain_regression_suites import (  # noqa: E402
    REGRESSION_SUITE_DOMAINS,
    REGRESSION_TARGETED_SUITE_NAMES,
)

ENV = {
    "RD_E2E_AI_DEVELOPER_ID": "ai-developer",
    "RD_E2E_AI_TESTER_ID": "ai-tester",
    "RD_E2E_EXECUTOR_PROFILE_ID": "profile-codex",
    "RD_E2E_PRODUCT_ID": "product-1",
    "RD_E2E_REPOSITORY_ID": "repository-1",
    "RD_E2E_REVIEWER_PASSWORD": "reviewer-secret",
    "RD_E2E_REVIEWER_USERNAME": "reviewer@example.com",
    "RD_E2E_RUNNER_ID": "runner-codex",
}


def valid_config(**changes: object) -> RdDeliveryE2EConfig:
    return replace(RdDeliveryE2EConfig.from_env(ENV), **changes)


def test_real_e2e_requires_every_identifier_and_only_timeout_has_a_default() -> None:
    config = RdDeliveryE2EConfig.from_env(ENV)
    assert config.timeout_seconds == 2400
    assert "reviewer-secret" not in repr(config)

    for name in ENV:
        missing = dict(ENV)
        missing.pop(name)
        with pytest.raises(RegressionError, match=name):
            RdDeliveryE2EConfig.from_env(missing)

    with pytest.raises(RegressionError, match="positive"):
        RdDeliveryE2EConfig.from_env({**ENV, "RD_E2E_TIMEOUT_SECONDS": "0"})


def test_real_e2e_rejects_unsafe_identity_target_and_branch_boundaries() -> None:
    config = valid_config()
    with pytest.raises(RegressionError, match="independent"):
        validate_safety_boundary(
            config,
            owner_username="reviewer@example.com",
            delivery_target="ready_for_release",
            repository_default_branch="main",
        )
    with pytest.raises(RegressionError, match="ready_for_release"):
        validate_safety_boundary(
            config,
            owner_username="owner@example.com",
            delivery_target="deployed",
            repository_default_branch="main",
        )
    for branch in ("main", "release/v2", "rd/wrong-shape"):
        with pytest.raises(RegressionError, match="isolated"):
            validate_safety_boundary(
                config,
                owner_username="owner@example.com",
                delivery_target="ready_for_release",
                protected_branches=("release/v2",),
                repository_default_branch="main",
                run_id="run-1",
                work_item_id="work-1",
                working_branch=branch,
            )

    validate_safety_boundary(
        config,
        owner_username="owner@example.com",
        delivery_target="ready_for_release",
        protected_branches=("release/v2",),
        repository_default_branch="main",
        run_id="run-1",
        work_item_id="work-1",
        working_branch="rd/run-1/work-1",
    )


class PreflightClient:
    def __init__(self, *, worker_updated_at: str | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self.requirement_created = False
        self.worker_updated_at = worker_updated_at or datetime.now(UTC).isoformat()

    def login(self, username: str, password: str) -> dict[str, object]:
        self.calls.append(("LOGIN", username))
        user_id = "reviewer-user" if username.startswith("reviewer") else "owner-user"
        return {"user": {"id": user_id, "username": username}}

    def get(self, path: str, query=None, *, headers=None) -> dict[str, object]:
        del headers
        self.calls.append(("GET", path))
        if path == "/api/products/product-1":
            return {"id": "product-1", "status": "active"}
        if path == "/api/products/product-1/git-repositories":
            return {
                "items": [
                    {
                        "default_branch": "main",
                        "git_provider": "gitlab",
                        "id": "repository-1",
                        "product_id": "product-1",
                        "status": "active",
                    }
                ]
            }
        if path == "/api/system/ai-executor-runners":
            return {
                "items": [
                    {
                        "executor_types": ["codex"],
                        "health_status": "online",
                        "id": "runner-codex",
                        "status": "active",
                    }
                ]
            }
        if path == "/api/delivery/rd-executor-profiles":
            return {
                "items": [
                    {
                        "executor_type": "codex",
                        "id": "profile-codex",
                        "runner_id": "runner-codex",
                        "status": "active",
                    }
                ]
            }
        if path == "/api/delivery/rd-ai-employees":
            return {
                "items": [
                    {
                        "id": "ai-developer",
                        "role_codes": ["developer"],
                        "status": "active",
                    },
                    {
                        "id": "ai-tester",
                        "role_codes": ["tester"],
                        "status": "active",
                    },
                ]
            }
        if path == "/api/delivery/rd-task-executor-policies":
            return {
                "items": [
                    {
                        "delivery_target": "ready_for_release",
                        "git_config": {
                            "repository_id": "repository-1",
                            "workspace_root": "/workspace",
                        },
                        "id": "policy-1",
                        "matching_config": {
                            "task_types": ["implementation", "automated_testing"]
                        },
                        "policy_version": 3,
                        "product_id": "product-1",
                        "role_bindings": [
                            {
                                "actor_mode": "ai",
                                "candidate_ai_employee_ids": ["ai-developer"],
                                "primary_executor_profile_id": "profile-codex",
                                "role_code": "developer",
                                "status": "active",
                            },
                            {
                                "actor_mode": "ai",
                                "candidate_ai_employee_ids": ["ai-tester"],
                                "primary_executor_profile_id": "profile-codex",
                                "role_code": "tester",
                                "status": "active",
                            },
                            {
                                "actor_mode": "human",
                                "candidate_human_user_ids": ["reviewer-user"],
                                "role_code": "reviewer",
                                "status": "active",
                            },
                        ],
                        "status": "active",
                        "team_config": {
                            "required_role_codes": ["developer", "tester", "reviewer"]
                        },
                    }
                ]
            }
        if path == "/api/system/execution-operations-overview":
            return {
                "workers": [
                    {"updated_at": self.worker_updated_at, "worker_id": "worker-1"}
                ]
            }
        raise AssertionError(f"unexpected GET {path} {query}")

    def post(self, path: str, body=None, *, headers=None) -> dict[str, object]:
        del body, headers
        if path == "/api/requirements":
            self.requirement_created = True
        raise AssertionError(f"preflight must not POST {path}")


def test_preflight_uses_public_apis_and_finishes_before_requirement_creation() -> None:
    client = PreflightClient()

    context = preflight_rd_delivery_e2e(
        client,
        owner_password="owner-secret",
        owner_username="owner@example.com",
        config=valid_config(),
    )

    assert context.owner_user_id == "owner-user"
    assert context.reviewer_user_id == "reviewer-user"
    assert context.developer_role_code == "developer"
    assert context.tester_role_code == "tester"
    assert context.reviewer_role_code == "reviewer"
    assert client.requirement_created is False
    assert client.calls[-1] == ("GET", "/api/system/execution-operations-overview")
    assert [path for method, path in client.calls if method == "GET"] == [
        "/api/products/product-1",
        "/api/products/product-1/git-repositories",
        "/api/system/ai-executor-runners",
        "/api/delivery/rd-executor-profiles",
        "/api/delivery/rd-ai-employees",
        "/api/delivery/rd-task-executor-policies",
        "/api/system/execution-operations-overview",
    ]


def test_preflight_rejects_stale_worker_before_requirement_creation() -> None:
    client = PreflightClient(worker_updated_at="2000-01-01T00:00:00+00:00")

    with pytest.raises(RegressionError, match="Worker heartbeat"):
        preflight_rd_delivery_e2e(
            client,
            owner_password="owner-secret",
            owner_username="owner@example.com",
            config=valid_config(),
        )

    assert client.requirement_created is False


def test_delivery_projection_requires_both_reconciled_records_and_redacts_secrets() -> None:
    records = [
        {
            "evidence_hash": "sha256:delivery-1",
            "id": "delivery-1",
            "local_commit_sha": "commit-1",
            "reconciliation_evidence_hash": "sha256:reconciliation-1",
            "reconciliation_id": "reconciliation-1",
            "reconciliation_status": "reconciled",
            "remote_commit_sha": "commit-1",
            "repository_id": "repository-1",
            "verified_at": "2026-07-26T00:00:00+00:00",
            "work_item_id": "implementation-1",
            "working_branch": "rd/run-1/implementation-1",
        },
        {
            "evidence_hash": "sha256:delivery-2",
            "id": "delivery-2",
            "local_commit_sha": "commit-2",
            "reconciliation_evidence_hash": "sha256:reconciliation-2",
            "reconciliation_id": "reconciliation-2",
            "reconciliation_status": "reconciled",
            "remote_commit_sha": "commit-2",
            "repository_id": "repository-1",
            "test_evidence": {"status": "passed", "suite": "rd-e2e"},
            "verified_at": "2026-07-26T00:01:00+00:00",
            "work_item_id": "testing-1",
            "working_branch": "rd/run-1/testing-1",
        },
    ]

    result = validate_delivery_records(
        records,
        expected_work_item_ids=("implementation-1", "testing-1"),
        repository_id="repository-1",
        run_id="run-1",
        secret_values=("reviewer-secret",),
    )

    assert [item["id"] for item in result] == ["delivery-1", "delivery-2"]
    assert "reviewer-secret" not in repr(result)
    with pytest.raises(RegressionError, match="reconciled"):
        validate_delivery_records(
            [{**records[0], "reconciliation_status": "pending"}, records[1]],
            expected_work_item_ids=("implementation-1", "testing-1"),
            repository_id="repository-1",
            run_id="run-1",
            secret_values=(),
        )


class ForbiddenSideEffectClient(PreflightClient):
    def post(self, path: str, body=None, *, headers=None) -> dict[str, object]:
        del body, headers
        forbidden = (
            path == "/api/ai-tasks"
            or path.endswith("/start")
            or path.endswith("/complete")
            or "/webhooks/" in path
            or path.startswith("/api/devops/deployments")
        )
        if forbidden:
            raise AssertionError(f"forbidden external side effect: {path}")
        raise AssertionError(f"fixture intentionally stops at first allowed write: {path}")


def test_validator_never_uses_legacy_or_fabricated_side_effect_endpoints() -> None:
    client = ForbiddenSideEffectClient()

    with pytest.raises(
        AssertionError,
        match="first allowed write: /api/products/product-1/versions",
    ):
        validate_rd_delivery_e2e(
            client,
            "owner@example.com",
            "owner-secret",
            valid_config(),
        )

    assert all(
        not (
            path == "/api/ai-tasks"
            or path.endswith("/start")
            or path.endswith("/complete")
            or "/webhooks/" in path
            or path.startswith("/api/devops/deployments")
        )
        for method, path in client.calls
        if method == "POST"
    )


class HappyPathClient(PreflightClient):
    def __init__(self) -> None:
        super().__init__()
        self.phase = 0
        self.posts: list[tuple[str, dict[str, object]]] = []

    @staticmethod
    def _delivery(work_item_id: str, commit: str, *, testing: bool) -> dict[str, object]:
        item: dict[str, object] = {
            "evidence_hash": f"sha256:{work_item_id}",
            "id": f"delivery-{work_item_id}",
            "local_commit_sha": commit,
            "provider": "gitlab",
            "reconciliation_evidence_hash": f"sha256:reconciliation-{work_item_id}",
            "reconciliation_id": f"reconciliation-{work_item_id}",
            "reconciliation_status": "reconciled",
            "remote_commit_sha": commit,
            "repository_id": "repository-1",
            "verified_at": "2026-07-26T00:00:00+00:00",
            "work_item_id": work_item_id,
            "working_branch": f"rd/run-e2e/{work_item_id}",
        }
        if testing:
            item["test_evidence"] = {"status": "passed", "suite": "rd-e2e"}
        return item

    def get(self, path: str, query=None, *, headers=None) -> dict[str, object]:
        if path in {
            "/api/products/product-1",
            "/api/products/product-1/git-repositories",
            "/api/system/ai-executor-runners",
            "/api/delivery/rd-executor-profiles",
            "/api/delivery/rd-ai-employees",
            "/api/delivery/rd-task-executor-policies",
            "/api/system/execution-operations-overview",
        }:
            return super().get(path, query, headers=headers)
        self.calls.append(("GET", path))
        if path == "/api/requirements/requirement-e2e/assessments/latest":
            return {"id": "assessment-e2e", "version": 4}
        if path == "/api/delivery/rd-collaboration-runs/run-e2e/work-items":
            implementation = {
                "ai_task_id": "ai-task-implementation",
                "id": "work-implementation",
                "status": "reviewing" if self.phase == 0 else "completed",
                "title": "implement_e2e_artifact",
                "version": 2,
            }
            testing = {
                "attempt_id": None,
                "ai_task_id": "ai-task-testing" if self.phase >= 1 else None,
                "id": "work-testing",
                "status": "reviewing" if self.phase == 1 else (
                    "completed" if self.phase >= 2 else "blocked"
                ),
                "title": "verify_e2e_artifact",
                "version": 2,
            }
            return {
                "dependencies": [
                    {
                        "predecessor_work_item_id": "work-implementation",
                        "status": "pending" if self.phase == 0 else "satisfied",
                        "successor_work_item_id": "work-testing",
                    }
                ],
                "items": [implementation, testing],
            }
        if path in {
            "/api/ai-tasks/ai-task-implementation",
            "/api/ai-tasks/ai-task-testing",
        }:
            suffix = "implementation" if path.endswith("implementation") else "testing"
            return {
                "id": f"ai-task-{suffix}",
                "pending_review": {"id": f"review-{suffix}"},
                "quality_gate": {
                    "id": f"gate-{suffix}",
                    "independent_evidence_count": 1,
                    "status": "passed",
                    "verified_attestation_count": 1,
                    "verifier_trust_isolated": True,
                },
                "status": "waiting_review",
            }
        if path == "/api/system/ai-executor-tasks":
            ai_task_id = str((query or {}).get("ai_task_id") or "")
            suffix = "implementation" if ai_task_id.endswith("implementation") else "testing"
            return {
                "items": [
                    {
                        "ai_task_id": ai_task_id,
                        "id": f"runner-task-{suffix}",
                        "runner_id": "runner-codex",
                        "status": "succeeded",
                        "task_kind": "coding",
                        "workspace_root": f"/workspace/{suffix}",
                    },
                    {
                        "ai_task_id": ai_task_id,
                        "id": f"verifier-task-{suffix}",
                        "quality_gate_run_id": f"gate-{suffix}",
                        "request_config": {
                            "required_trust_domain": "verification",
                        },
                        "runner_id": "runner-verifier",
                        "status": "succeeded",
                        "task_kind": "quality_gate",
                        "workspace_root": f"/workspace/{suffix}",
                    },
                ]
            }
        if path == "/api/delivery/rd-collaboration-runs/run-e2e":
            assert self.phase == 2
            return {
                "completion_reason": "ready_for_release",
                "delivery_evidence_hash": "sha256:ready",
                "delivery_evidence_id": "ready-evidence",
                "git_deliveries": {
                    "items": [
                        self._delivery(
                            "work-implementation",
                            "commit-implementation",
                            testing=False,
                        ),
                        self._delivery("work-testing", "commit-testing", testing=True),
                    ],
                    "total": 2,
                },
                "id": "run-e2e",
                "status": "completed",
            }
        if path == "/api/product-versions/version-e2e/dashboard":
            return {
                "deployments": [],
                "version": {"id": "version-e2e", "status": "ready_for_release"},
            }
        if path == "/api/audit/events":
            assert (query or {}).get("event_type") in {
                "deployment_request.created",
                "deployment.run.started",
                "deployment_request.completed",
            }
            return {"items": [], "total": 0}
        raise AssertionError(f"unexpected GET {path} {query}")

    def post(self, path: str, body=None, *, headers=None) -> dict[str, object]:
        del headers
        payload = dict(body or {})
        self.calls.append(("POST", path))
        self.posts.append((path, payload))
        forbidden = (
            path == "/api/ai-tasks"
            or path.endswith("/start")
            or path.endswith("/complete")
            or "/webhooks/" in path
            or path.startswith("/api/devops/deployments")
        )
        if forbidden:
            raise AssertionError(f"forbidden external side effect: {path}")
        if path == "/api/products/product-1/versions":
            return {"id": "version-e2e", **payload}
        if path == "/api/product-versions/version-e2e/branch-configs":
            return {"id": "branch-config-e2e", **payload}
        if path == "/api/requirements":
            return {
                "id": "requirement-e2e",
                "revision": 1,
                **payload,
            }
        if path == "/api/requirements/requirement-e2e/assessments":
            return {
                "id": "assessment-e2e",
                "initial_strategy_snapshot_id": "snapshot-e2e",
            }
        if path.startswith("/api/requirement-assessments/assessment-e2e/opinions"):
            return {"id": f"opinion-{payload['role_code']}"}
        if path == "/api/requirement-assessments/assessment-e2e/decisions":
            return {
                "grouping": {
                    "status": "planned",
                    "version": {"id": "version-e2e", "scope_version": 2},
                }
            }
        if path == "/api/product-versions/version-e2e/collaboration-runs":
            return {
                "delivery_target": "ready_for_release",
                "id": "run-e2e",
                "strategy_snapshot_kind": "version_resolved",
            }
        if path == "/api/delivery/rd-collaboration-runs/run-e2e/plan":
            assert [item["work_item_type"] for item in payload["work_items"]] == [
                "implementation",
                "automated_testing",
            ]
            implementation_contract = payload["work_items"][0]["output_contract"]
            testing_contract = payload["work_items"][1]["output_contract"]
            assert implementation_contract["format"] == "json"
            assert implementation_contract["required"] == ["summary", "git_delivery"]
            assert implementation_contract["git_delivery"] == {
                "local_commit_sha": "string",
                "working_branch": "rd/<run-id>/<work-item-id>",
            }
            assert testing_contract["format"] == "json"
            assert testing_contract["required"] == [
                "summary",
                "git_delivery",
                "test_evidence",
            ]
            assert testing_contract["test_evidence"] == {
                "status": "passed",
                "suite": "string",
            }
            for item in payload["work_items"]:
                assert "rd/<run-id>/<work-item-id>" in item["description"]
            assert payload["dependencies"] == [
                {
                    "predecessor_work_item_id": "implement_e2e_artifact",
                    "successor_work_item_id": "verify_e2e_artifact",
                }
            ]
            return {
                "work_items": [
                    {
                        **payload["work_items"][0],
                        "id": "work-implementation",
                        "status": "ready",
                        "version": 1,
                    },
                    {
                        **payload["work_items"][1],
                        "id": "work-testing",
                        "status": "blocked",
                        "version": 1,
                    },
                ]
            }
        if path == "/api/delivery/rd-work-items/work-implementation/review":
            assert self.phase == 0
            self.phase = 1
            return {"work_item": {"id": "work-implementation", "status": "completed"}}
        if path == "/api/delivery/rd-work-items/work-testing/review":
            assert self.phase == 1
            self.phase = 2
            return {"work_item": {"id": "work-testing", "status": "completed"}}
        raise AssertionError(f"unexpected POST {path}")


def test_real_e2e_happy_path_projects_native_runner_gate_delivery_and_no_deployment() -> None:
    client = HappyPathClient()

    results = validate_rd_delivery_e2e(
        client,
        "owner@example.com",
        "owner-secret",
        valid_config(timeout_seconds=2),
    )

    assert [result.name for result in results] == [
        "rd_delivery_preflight",
        "rd_delivery_scope",
        "rd_delivery_implementation",
        "rd_delivery_automated_testing",
        "rd_delivery_evidence",
        "rd_delivery_ready_for_release",
    ]
    report = repr(results)
    assert "owner-secret" not in report
    assert "reviewer-secret" not in report
    requirement_payload = next(
        payload for path, payload in client.posts if path == "/api/requirements"
    )
    instruction = str(requirement_payload["content"])
    for prohibited in (
        "application code",
        "dependencies",
        "CI",
        "deployment files",
        "protected branches",
        "secrets",
    ):
        assert prohibited in instruction
    assert not any(
        path == "/api/ai-tasks"
        or path.endswith("/start")
        or path.endswith("/complete")
        or "/webhooks/" in path
        or path.startswith("/api/devops/deployments")
        for method, path in client.calls
        if method == "POST"
    )


class InvalidRunnerEvidenceClient(HappyPathClient):
    def __init__(self, fault: str) -> None:
        super().__init__()
        self.fault = fault

    def get(self, path: str, query=None, *, headers=None) -> dict[str, object]:
        response = super().get(path, query, headers=headers)
        if path == "/api/system/ai-executor-tasks":
            items = [dict(item) for item in response["items"]]
            coding = next(item for item in items if item.get("task_kind") == "coding")
            if self.fault == "missing_coding_kind":
                coding.pop("task_kind")
            elif self.fault == "wrong_coding_runner":
                coding["runner_id"] = "runner-other"
            elif self.fault == "missing_quality_gate_task":
                items = [item for item in items if item.get("task_kind") != "quality_gate"]
            else:
                verifier = next(
                    item for item in items if item.get("task_kind") == "quality_gate"
                )
                if self.fault == "mismatched_quality_gate":
                    verifier["quality_gate_run_id"] = "gate-other"
                elif self.fault == "shared_verifier_runner":
                    verifier["runner_id"] = "runner-codex"
                elif self.fault == "wrong_verifier_trust":
                    verifier["request_config"] = {
                        "required_trust_domain": "coding",
                    }
            return {"items": items}
        if path.startswith("/api/ai-tasks/") and self.fault == "untrusted_gate":
            gate = dict(response["quality_gate"])
            gate.update(
                {
                    "independent_evidence_count": 0,
                    "verified_attestation_count": 0,
                    "verifier_trust_isolated": False,
                }
            )
            return {**response, "quality_gate": gate}
        return response


@pytest.mark.parametrize(
    ("fault", "message"),
    [
        ("missing_coding_kind", "coding Runner task"),
        ("wrong_coding_runner", "configured Runner"),
        ("missing_quality_gate_task", "quality-gate Runner task"),
        ("mismatched_quality_gate", "does not match"),
        ("shared_verifier_runner", "not independent"),
        ("wrong_verifier_trust", "verification trust"),
        ("untrusted_gate", "trusted isolation"),
    ],
)
def test_real_e2e_rejects_untrusted_or_ambiguous_runner_evidence(
    fault: str,
    message: str,
) -> None:
    with pytest.raises(RegressionError, match=message):
        validate_rd_delivery_e2e(
            InvalidRunnerEvidenceClient(fault),
            "owner@example.com",
            "owner-secret",
            valid_config(timeout_seconds=2),
        )


class PrematureDependentDispatchClient(HappyPathClient):
    def get(self, path: str, query=None, *, headers=None) -> dict[str, object]:
        response = super().get(path, query, headers=headers)
        if (
            path == "/api/delivery/rd-collaboration-runs/run-e2e/work-items"
            and self.phase == 0
        ):
            items = [dict(item) for item in response["items"]]
            testing = next(item for item in items if item["id"] == "work-testing")
            testing.update(
                {
                    "ai_task_id": "ai-task-premature",
                    "attempt_id": "attempt-premature",
                    "status": "running",
                }
            )
            return {"items": items}
        return response


def test_real_e2e_proves_dependency_is_blocked_before_implementation_review() -> None:
    with pytest.raises(RegressionError, match="blocked"):
        validate_rd_delivery_e2e(
            PrematureDependentDispatchClient(),
            "owner@example.com",
            "owner-secret",
            valid_config(timeout_seconds=2),
        )


def test_real_suite_is_explicit_and_never_part_of_fast_targeted_runs() -> None:
    assert "rd-delivery-e2e" in REGRESSION_SUITE_DOMAINS
    assert "rd-delivery-e2e" not in REGRESSION_TARGETED_SUITE_NAMES


def test_e2e_config_is_accessed_only_when_explicit_suite_is_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accesses: list[str] = []
    configured = valid_config()

    def read_config(cls) -> RdDeliveryE2EConfig:
        del cls
        accesses.append("rd-delivery-e2e")
        return configured

    monkeypatch.setattr(
        regression_cli.RdDeliveryE2EConfig,
        "from_env",
        classmethod(read_config),
    )
    monkeypatch.setattr(
        regression_cli,
        "validate_permission_visibility_quick_regression",
        lambda client, *, username, password: [],
    )
    monkeypatch.setattr(
        regression_cli,
        "validate_rd_delivery_e2e",
        lambda client, username, password, config: [],
    )

    regression_cli.run_regression_suite(
        object(),
        suite="permission-visibility",
        username="owner@example.com",
        password="owner-secret",
    )
    assert accesses == []

    regression_cli.run_regression_suite(
        object(),
        suite="rd-delivery-e2e",
        username="owner@example.com",
        password="owner-secret",
    )
    assert accesses == ["rd-delivery-e2e"]
