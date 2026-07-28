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
import full_chain_regression_rd_delivery_e2e as rd_delivery_e2e  # noqa: E402
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
    assert config.review_channel == "api"
    assert config.timeout_seconds == 2400
    assert "reviewer-secret" not in repr(config)

    for name in ENV:
        missing = dict(ENV)
        missing.pop(name)
        with pytest.raises(RegressionError, match=name):
            RdDeliveryE2EConfig.from_env(missing)

    with pytest.raises(RegressionError, match="positive"):
        RdDeliveryE2EConfig.from_env({**ENV, "RD_E2E_TIMEOUT_SECONDS": "0"})


def test_browser_review_channel_is_validated_and_uses_an_external_artifact_dir() -> None:
    config = RdDeliveryE2EConfig.from_env(
        {
            **ENV,
            "RD_E2E_ARTIFACT_DIR": "/private/tmp/rd-e2e-browser",
            "RD_E2E_REVIEW_CHANNEL": "browser",
        }
    )

    assert config.review_channel == "browser"
    assert config.artifact_dir == "/private/tmp/rd-e2e-browser"

    with pytest.raises(RegressionError, match="api or browser"):
        RdDeliveryE2EConfig.from_env({**ENV, "RD_E2E_REVIEW_CHANNEL": "manual"})
    with pytest.raises(RegressionError, match="outside the repository"):
        RdDeliveryE2EConfig.from_env(
            {
                **ENV,
                "RD_E2E_ARTIFACT_DIR": str(Path(__file__).resolve().parents[3] / "artifacts"),
                "RD_E2E_REVIEW_CHANNEL": "browser",
            }
        )


def test_browser_review_adapter_uses_checked_in_command_and_non_secret_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def run_process(argv, **kwargs):
        captured["argv"] = list(argv)
        captured.update(kwargs)
        return type(
            "Completed",
            (),
            {"returncode": 0, "stderr": "", "stdout": "browser smoke passed"},
        )()

    monkeypatch.setattr(rd_delivery_e2e.subprocess, "run", run_process)
    monkeypatch.setenv("RD_E2E_REVIEWER_USERNAME", "inherited-reviewer@example.com")
    monkeypatch.setenv("RD_E2E_REVIEWER_PASSWORD", "inherited-reviewer-secret")
    config = valid_config(
        artifact_dir="/private/tmp/rd-e2e-browser",
        review_channel="browser",
        reviewer_password="inherited-reviewer-secret",
        reviewer_username="inherited-reviewer@example.com",
    )

    rd_delivery_e2e.run_browser_review(
        config,
        decision_request_id="decision-1",
        run_id="run-1",
        task_id="task-1",
        version_id="version-1",
    )

    assert captured["argv"] == ["npm", "run", "test:e2e:rd-collaboration"]
    assert captured["cwd"] == Path(__file__).resolve().parents[3] / "apps" / "web"
    child_env = captured["env"]
    assert isinstance(child_env, dict)
    assert child_env["RD_E2E_VERSION_ID"] == "version-1"
    assert child_env["RD_E2E_RUN_ID"] == "run-1"
    assert child_env["RD_E2E_TASK_ID"] == "task-1"
    assert child_env["RD_E2E_DECISION_REQUEST_ID"] == "decision-1"
    assert child_env["RD_E2E_ARTIFACT_DIR"] == "/private/tmp/rd-e2e-browser"
    assert child_env["RD_E2E_REVIEWER_USERNAME"] == "inherited-reviewer@example.com"
    assert child_env["RD_E2E_REVIEWER_PASSWORD"] == "inherited-reviewer-secret"
    assert "reviewer-secret" not in repr(captured["argv"])


def test_browser_review_adapter_requires_matching_inherited_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process_calls: list[list[str]] = []

    def run_process(argv, **kwargs):
        del kwargs
        process_calls.append(list(argv))
        return type(
            "Completed",
            (),
            {"returncode": 0, "stderr": "", "stdout": "browser smoke passed"},
        )()

    monkeypatch.setattr(rd_delivery_e2e.subprocess, "run", run_process)
    monkeypatch.setenv("RD_E2E_REVIEWER_USERNAME", "different-reviewer@example.com")
    monkeypatch.setenv("RD_E2E_REVIEWER_PASSWORD", "different-reviewer-secret")
    config = valid_config(
        artifact_dir="/private/tmp/rd-e2e-browser",
        review_channel="browser",
    )

    with pytest.raises(RegressionError, match="inherited reviewer credentials"):
        rd_delivery_e2e.run_browser_review(
            config,
            decision_request_id="decision-1",
            run_id="run-1",
            task_id="task-1",
            version_id="version-1",
        )
    assert process_calls == []


def test_browser_review_adapter_fails_closed_without_leaking_child_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run_process(argv, **kwargs):
        del argv, kwargs
        return type(
            "Completed",
            (),
            {
                "returncode": 7,
                "stderr": "Authorization: Bearer reviewer-secret",
                "stdout": "reviewer@example.com",
            },
        )()

    monkeypatch.setattr(rd_delivery_e2e.subprocess, "run", run_process)
    monkeypatch.setenv("RD_E2E_REVIEWER_USERNAME", "reviewer@example.com")
    monkeypatch.setenv("RD_E2E_REVIEWER_PASSWORD", "reviewer-secret")
    config = valid_config(
        artifact_dir="/private/tmp/rd-e2e-browser",
        review_channel="browser",
    )

    with pytest.raises(RegressionError, match="browser review failed") as exc_info:
        rd_delivery_e2e.run_browser_review(
            config,
            run_id="run-1",
            task_id="task-1",
            version_id="version-1",
        )

    assert "reviewer-secret" not in str(exc_info.value)
    assert "reviewer@example.com" not in str(exc_info.value)


def test_browser_review_adapter_rejects_secret_bearing_success_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run_process(argv, **kwargs):
        del argv, kwargs
        return type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stderr": "",
                "stdout": "browser smoke passed for reviewer@example.com",
            },
        )()

    monkeypatch.setattr(rd_delivery_e2e.subprocess, "run", run_process)
    monkeypatch.setenv("RD_E2E_REVIEWER_USERNAME", "reviewer@example.com")
    monkeypatch.setenv("RD_E2E_REVIEWER_PASSWORD", "reviewer-secret")
    config = valid_config(
        artifact_dir="/private/tmp/rd-e2e-browser",
        review_channel="browser",
    )

    with pytest.raises(RegressionError, match="browser review failed") as exc_info:
        rd_delivery_e2e.run_browser_review(
            config,
            run_id="run-1",
            task_id="task-1",
            version_id="version-1",
        )

    assert "reviewer@example.com" not in str(exc_info.value)


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
        self.testing_dispatch_observed = False

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
            testing_running = self.phase == 1 and not self.testing_dispatch_observed
            implementation_attempt = {
                "ai_task_id": "ai-task-implementation",
                "attempt_no": 1,
                "completed_at": "2026-07-26T00:00:00+00:00",
                "failure_code": None,
                "fence_event_id": None,
                "late_result_fenced": False,
                "rework_evidence_count": 0,
                "runner_status": "succeeded",
                "runner_task_id": "runner-task-implementation",
                "started_at": "2026-07-25T23:59:00+00:00",
                "status": "completed",
                "workspace_fingerprint": "sha256:" + ("a" * 64),
            }
            implementation = {
                "active_attempt_count": 0,
                "ai_task_id": "ai-task-implementation",
                "attempt_history": {
                    "items": [implementation_attempt],
                    "total": 1,
                    "truncated": False,
                },
                "id": "work-implementation",
                "status": "reviewing" if self.phase == 0 else "completed",
                "title": "implement_e2e_artifact",
                "version": 2,
            }
            testing_attempt = {
                "ai_task_id": "ai-task-testing",
                "attempt_no": 1,
                "completed_at": (
                    None if testing_running else "2026-07-26T00:02:00+00:00"
                ),
                "failure_code": None,
                "fence_event_id": None,
                "late_result_fenced": False,
                "rework_evidence_count": 0,
                "runner_status": "running" if testing_running else "succeeded",
                "runner_task_id": "runner-task-testing",
                "started_at": "2026-07-26T00:01:00+00:00",
                "status": "running" if testing_running else "completed",
                "workspace_fingerprint": "sha256:" + ("b" * 64),
            }
            testing = {
                "active_attempt_count": 1 if testing_running else 0,
                "ai_task_id": "ai-task-testing" if self.phase >= 1 else None,
                "attempt_history": {
                    "items": [testing_attempt] if self.phase >= 1 else [],
                    "total": 1 if self.phase >= 1 else 0,
                    "truncated": False,
                },
                "id": "work-testing",
                "status": "running" if testing_running else (
                    "reviewing" if self.phase == 1 else (
                    "completed" if self.phase >= 2 else "blocked"
                    )
                ),
                "title": "verify_e2e_artifact",
                "version": 2,
            }
            if testing_running:
                self.testing_dispatch_observed = True
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


class BrowserApprovalClient:
    def __init__(self, *, final_work_item_version: int = 3) -> None:
        self.browser_completed = False
        self.calls: list[tuple[str, str]] = []
        self.final_work_item_version = final_work_item_version

    def get(self, path: str, query=None, *, headers=None) -> dict[str, object]:
        del query, headers
        self.calls.append(("GET", path))
        if path == "/api/reviews/review-browser":
            return {
                "ai_task_id": "ai-task-browser",
                "id": "review-browser",
                "status": "approved" if self.browser_completed else "pending",
                "version": 5 if self.browser_completed else 4,
            }
        if path == "/api/delivery/rd-collaboration-runs/run-browser/work-items":
            return {
                "dependencies": [],
                "items": [
                    {
                        "id": "work-browser",
                        "status": "completed" if self.browser_completed else "reviewing",
                        "version": (
                            self.final_work_item_version
                            if self.browser_completed
                            else 2
                        ),
                    }
                ],
            }
        raise AssertionError(f"unexpected GET {path}")

    def login(self, username: str, password: str) -> dict[str, object]:
        del password
        self.calls.append(("LOGIN", username))
        return {"user": {"id": "owner-user", "username": username}}

    def post(self, path: str, body=None, *, headers=None) -> dict[str, object]:
        del body, headers
        raise AssertionError(f"browser review must not POST through Python: {path}")


def test_browser_review_waits_for_durable_review_and_work_item_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = BrowserApprovalClient()
    browser_calls: list[dict[str, object]] = []

    def complete_browser_review(config, **identifiers):
        browser_calls.append({"config": config, **identifiers})
        client.browser_completed = True

    monkeypatch.setattr(rd_delivery_e2e, "run_browser_review", complete_browser_review)
    config = valid_config(
        artifact_dir="/private/tmp/rd-e2e-browser",
        review_channel="browser",
        timeout_seconds=2,
    )

    approved = rd_delivery_e2e._approve_item(
        client,
        config=config,
        item={"ai_task_id": "ai-task-browser", "id": "work-browser", "version": 2},
        marker="browser-marker",
        owner_password="owner-secret",
        owner_username="owner@example.com",
        review_id="review-browser",
        run_id="run-browser",
        task_id="ai-task-browser",
        version_id="version-browser",
    )

    assert approved == {"id": "work-browser", "status": "completed", "version": 3}
    assert browser_calls == [
        {
            "config": config,
            "decision_request_id": None,
            "run_id": "run-browser",
            "task_id": "ai-task-browser",
            "version_id": "version-browser",
        }
    ]
    assert ("GET", "/api/reviews/review-browser") in client.calls
    assert (
        "GET",
        "/api/delivery/rd-collaboration-runs/run-browser/work-items",
    ) in client.calls
    assert not any(method == "POST" for method, _ in client.calls)
    assert client.calls[-1] == ("LOGIN", "owner@example.com")


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
    assert results[-1].evidence == {
        "attempt_chain": {
            "automated_testing": [
                {
                    "ai_task_id": "ai-task-testing",
                    "attempt_no": 1,
                    "completed_at": "2026-07-26T00:02:00+00:00",
                    "failure_code": None,
                    "fence_event_id": None,
                    "late_result_fenced": False,
                    "rework_evidence_count": 0,
                    "runner_status": "succeeded",
                    "runner_task_id": "runner-task-testing",
                    "started_at": "2026-07-26T00:01:00+00:00",
                    "status": "completed",
                    "workspace_fingerprint": "sha256:" + ("b" * 64),
                }
            ],
            "implementation": [
                {
                    "ai_task_id": "ai-task-implementation",
                    "attempt_no": 1,
                    "completed_at": "2026-07-26T00:00:00+00:00",
                    "failure_code": None,
                    "fence_event_id": None,
                    "late_result_fenced": False,
                    "rework_evidence_count": 0,
                    "runner_status": "succeeded",
                    "runner_task_id": "runner-task-implementation",
                    "started_at": "2026-07-25T23:59:00+00:00",
                    "status": "completed",
                    "workspace_fingerprint": "sha256:" + ("a" * 64),
                }
            ],
        },
        "scenario": "happy-path",
    }
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
                    "active_attempt_count": 1,
                    "ai_task_id": "ai-task-premature",
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


class HiddenActiveAttemptClient(HappyPathClient):
    def get(self, path: str, query=None, *, headers=None) -> dict[str, object]:
        response = super().get(path, query, headers=headers)
        if (
            path == "/api/delivery/rd-collaboration-runs/run-e2e/work-items"
            and self.phase == 0
        ):
            items = [dict(item) for item in response["items"]]
            testing = next(item for item in items if item["id"] == "work-testing")
            testing["active_attempt_count"] = 1
            return {**response, "items": items}
        return response


class MissingActiveDispatchClient(HappyPathClient):
    def get(self, path: str, query=None, *, headers=None) -> dict[str, object]:
        response = super().get(path, query, headers=headers)
        if path == "/api/delivery/rd-collaboration-runs/run-e2e/work-items":
            items = [dict(item) for item in response["items"]]
            testing = next(item for item in items if item["id"] == "work-testing")
            if testing.get("status") == "running":
                testing["active_attempt_count"] = 0
            return {**response, "items": items}
        return response


@pytest.mark.parametrize(
    "client_type",
    [HiddenActiveAttemptClient, MissingActiveDispatchClient],
)
def test_real_e2e_requires_public_attempt_counts_across_dependency_dispatch(
    client_type: type[HappyPathClient],
) -> None:
    with pytest.raises(RegressionError, match="active attempt"):
        validate_rd_delivery_e2e(
            client_type(),
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


SCENARIOS = (
    "happy-path",
    "quality-rework",
    "cancel-resume",
    "timeout-recovery",
    "high-risk-dispatch",
)


def test_rd_e2e_cli_exposes_exact_scenario_choices() -> None:
    parser = regression_cli.build_argument_parser()
    action = next(
        action
        for action in parser._actions
        if action.dest == "rd_e2e_scenario"
    )

    assert tuple(action.choices or ()) == SCENARIOS
    assert action.default == "happy-path"


def test_regression_report_keeps_attempt_chain_machine_readable() -> None:
    report = regression_cli.build_regression_report(
        api_base_url="http://localhost:8000",
        duration_ms=1,
        error=None,
        finished_at="2026-07-27T03:00:01+00:00",
        started_at="2026-07-27T03:00:00+00:00",
        status="passed",
        steps=[
            regression_cli.StepResult(
                "rd_delivery_ready_for_release",
                "scenario=timeout-recovery",
                evidence={
                    "attempt_chain": [
                        {
                            "attempt_no": 1,
                            "runner_task_id": "runner-attempt-1",
                            "status": "failed",
                        }
                    ]
                },
            )
        ],
        suite="rd-delivery-e2e",
        task_execution_mode="simulated_runner",
    )

    assert report["steps"][0]["evidence"]["attempt_chain"] == [
        {
            "attempt_no": 1,
            "runner_task_id": "runner-attempt-1",
            "status": "failed",
        }
    ]


def test_rd_e2e_scenario_is_ignored_outside_explicit_suite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    configured = valid_config()

    monkeypatch.setattr(
        regression_cli,
        "validate_permission_visibility_quick_regression",
        lambda client, *, username, password: [],
    )
    monkeypatch.setattr(
        regression_cli.RdDeliveryE2EConfig,
        "from_env",
        classmethod(lambda cls: calls.append("config") or configured),
    )
    monkeypatch.setattr(
        regression_cli,
        "validate_rd_delivery_e2e",
        lambda client, username, password, config, *, scenario: (
            calls.append(scenario) or []
        ),
    )

    regression_cli.run_regression_suite(
        object(),
        suite="permission-visibility",
        username="owner@example.com",
        password="owner-secret",
        rd_e2e_scenario="timeout-recovery",
    )
    assert calls == []

    regression_cli.run_regression_suite(
        object(),
        suite="rd-delivery-e2e",
        username="owner@example.com",
        password="owner-secret",
        rd_e2e_scenario="timeout-recovery",
    )
    assert calls == ["config", "timeout-recovery"]


class TimeoutPolicyLifecycleClient:
    def __init__(self, *, fail_restore: bool = False) -> None:
        self.calls: list[tuple[str, str, dict[str, object]]] = []
        self.fail_restore = fail_restore

    def patch(self, path: str, body=None, *, headers=None) -> dict[str, object]:
        del headers
        payload = dict(body or {})
        self.calls.append(("PATCH", path, payload))
        patch_count = len([call for call in self.calls if call[0] == "PATCH"])
        if patch_count == 1:
            assert payload["expected_policy_version"] == 7
            assert payload["changes"]["autonomy_config"] == {
                "max_iterations": 1,
                "mode": "single_pass",
                "timeout_seconds": 3,
            }
            return {
                "policy": {
                    "id": "policy-1",
                    "policy_version": 8,
                    **payload["changes"],
                }
            }
        if self.fail_restore and patch_count == 2:
            raise RegressionError("restore conflict")
        assert payload["expected_policy_version"] == 8
        assert payload["changes"]["status"] == "active"
        assert payload["changes"]["autonomy_config"] == {
            "max_iterations": 5,
            "mode": "autonomous_loop",
            "timeout_seconds": 600,
        }
        return {
            "policy": {
                "id": "policy-1",
                "policy_version": 9,
                **payload["changes"],
            }
        }

    def post(self, path: str, body=None, *, headers=None) -> dict[str, object]:
        del headers
        payload = dict(body or {})
        self.calls.append(("POST", path, payload))
        return {
            "id": "assessment-timeout",
            "initial_strategy_snapshot_id": "snapshot-timeout",
        }


def _policy_for_timeout_lifecycle() -> dict[str, object]:
    return {
        "assessment_config": {},
        "autonomy_config": {
            "max_iterations": 5,
            "mode": "autonomous_loop",
            "timeout_seconds": 600,
        },
        "brain_app_id": "rd_brain",
        "delivery_target": "ready_for_release",
        "deployment_config": {},
        "experience_reuse_config": {},
        "git_config": {"repository_id": "repository-1", "workspace_root": "/workspace"},
        "id": "policy-1",
        "iteration_config": {},
        "matching_config": {"task_types": ["implementation", "automated_testing"]},
        "name": "Policy",
        "policy_version": 7,
        "product_id": "product-1",
        "quality_gate_config": {},
        "role_bindings": [],
        "status": "active",
        "team_config": {"required_role_codes": []},
    }


def test_timeout_fault_policy_is_versioned_frozen_and_immediately_restored() -> None:
    client = TimeoutPolicyLifecycleClient()

    assessment, versions = rd_delivery_e2e.create_scenario_assessment(
        client,
        scenario="timeout-recovery",
        policy=_policy_for_timeout_lifecycle(),
        requirement_id="requirement-1",
        request_payload={
            "reason": "timeout scenario",
            "request_id": "assessment-request",
            "requirement_revision": 1,
        },
    )

    assert assessment["initial_strategy_snapshot_id"] == "snapshot-timeout"
    assert versions == {
        "fault_policy_version": 8,
        "original_policy_version": 7,
        "restored_policy_version": 9,
    }
    assert [method for method, _path, _body in client.calls] == [
        "PATCH",
        "POST",
        "PATCH",
    ]


def test_timeout_fault_policy_restore_failure_stops_before_following_writes() -> None:
    client = TimeoutPolicyLifecycleClient(fail_restore=True)

    with pytest.raises(RegressionError, match="restore conflict"):
        rd_delivery_e2e.create_scenario_assessment(
            client,
            scenario="timeout-recovery",
            policy=_policy_for_timeout_lifecycle(),
            requirement_id="requirement-1",
            request_payload={
                "reason": "timeout scenario",
                "request_id": "assessment-request",
                "requirement_revision": 1,
            },
        )

    assert [method for method, _path, _body in client.calls] == [
        "PATCH",
        "POST",
        "PATCH",
        "PATCH",
    ]


def test_quality_rework_contract_starts_pre_fault_and_requires_real_gate_repair() -> None:
    criteria, instruction = rd_delivery_e2e.build_scenario_task_contract(
        artifact_path="docs/e2e/quality.md",
        scenario="quality-rework",
    )

    assert any("quality_rework_complete=true" in item for item in criteria)
    assert "first real Runner attempt" in instruction
    assert "omit quality_rework_complete=true" in instruction
    assert "independent quality gate" in instruction
    assert "rework evidence" in instruction
    assert "callback" not in instruction


class GovernanceScenarioClient:
    def __init__(self, scenario: str) -> None:
        self.scenario = scenario
        self.phase = 0
        self.calls: list[tuple[str, str]] = []
        self.decision_posts = 0

    @staticmethod
    def _attempt(
        attempt_no: int,
        *,
        ai_task_id: str,
        failure_code: str | None = None,
        fenced: bool = False,
        rework_evidence_count: int = 0,
        runner_status: str,
        runner_task_id: str,
        status: str,
        workspace_fingerprint: str = "sha256:" + ("a" * 64),
    ) -> dict[str, object]:
        return {
            "ai_task_id": ai_task_id,
            "attempt_no": attempt_no,
            "completed_at": (
                "2026-07-27T02:01:00+00:00"
                if status in {"cancelled", "completed", "failed"}
                else None
            ),
            "failure_code": failure_code,
            "fence_event_id": "fence-event-1" if fenced else None,
            "late_result_fenced": fenced,
            "rework_evidence_count": rework_evidence_count,
            "runner_status": runner_status,
            "runner_task_id": runner_task_id,
            "started_at": "2026-07-27T02:00:00+00:00",
            "status": status,
            "workspace_fingerprint": workspace_fingerprint,
        }

    @staticmethod
    def _history(items: list[dict[str, object]]) -> dict[str, object]:
        return {"items": items, "total": len(items), "truncated": False}

    def login(self, username: str, password: str) -> dict[str, object]:
        del password
        self.calls.append(("LOGIN", username))
        return {
            "user": {
                "id": "reviewer-user" if username.startswith("reviewer") else "owner-user",
                "username": username,
            }
        }

    def _item_response(self) -> dict[str, object]:
        quality_failed = self.scenario == "quality-rework" and self.phase >= 1
        first = self._attempt(
            1,
            ai_task_id="ai-task-attempt-1",
            failure_code=(
                "AI_EXECUTOR_TASK_TIMEOUT"
                if self.scenario == "timeout-recovery"
                else None
            ),
            fenced=self.scenario == "cancel-resume" and self.phase >= 1,
            rework_evidence_count=0,
            runner_status=(
                "succeeded"
                if quality_failed
                else (
                    "cancelled"
                    if self.scenario == "cancel-resume" and self.phase >= 1
                    else (
                        "timed_out"
                        if self.scenario == "timeout-recovery"
                        else "running"
                    )
                )
            ),
            runner_task_id="runner-attempt-1",
            status=(
                "failed"
                if quality_failed or self.scenario == "timeout-recovery"
                else (
                    "cancelled"
                    if self.scenario == "cancel-resume" and self.phase >= 1
                    else "running"
                )
            ),
        )
        second = self._attempt(
            2,
            ai_task_id="ai-task-attempt-2",
            runner_status="succeeded",
            runner_task_id="runner-attempt-2",
            status="completed",
        )
        status = "running"
        active_attempt_count = 1
        ai_task_id: str | None = "ai-task-attempt-1"
        history = [first]
        version = 3
        decision_id: str | None = None
        if self.scenario == "quality-rework":
            if self.phase == 0:
                status = "running"
                active_attempt_count = 1
                self.phase = 1
            elif self.phase == 1:
                status = "rework_required"
                active_attempt_count = 0
                self.phase = 2
            else:
                status = "reviewing"
                active_attempt_count = 0
                ai_task_id = "ai-task-attempt-2"
                history.append(second)
                version = 5
        elif self.scenario == "cancel-resume":
            if self.phase == 1:
                status = "cancelled"
                active_attempt_count = 0
                version = 4
            elif self.phase >= 2:
                status = "reviewing"
                active_attempt_count = 0
                ai_task_id = "ai-task-attempt-2"
                history.append(second)
                version = 6
        elif self.scenario == "timeout-recovery":
            if self.phase == 0:
                status = "waiting_human"
                active_attempt_count = 0
                decision_id = "decision-timeout"
                version = 4
            else:
                status = "reviewing"
                active_attempt_count = 0
                ai_task_id = "ai-task-attempt-2"
                history.append(second)
                version = 6
        elif self.scenario == "high-risk-dispatch":
            if self.phase == 0:
                status = "waiting_human"
                active_attempt_count = 0
                ai_task_id = None
                history = []
                decision_id = "decision-high-risk"
                version = 2
            elif self.phase == 1:
                status = "running"
                active_attempt_count = 1
                self.phase = 2
            else:
                first = {**first, "runner_status": "succeeded", "status": "completed"}
                status = "reviewing"
                active_attempt_count = 0
                history = [first]
                version = 4
        return {
            "active_attempt_count": active_attempt_count,
            "ai_task_id": ai_task_id,
            "attempt_history": self._history(history),
            "id": "work-scenario",
            "resume_state": (
                "ready"
                if self.scenario == "timeout-recovery" and self.phase == 0
                else None
            ),
            "status": status,
            "suspended_decision_request_id": decision_id,
            "title": "scenario_work_item",
            "version": version,
        }

    def get(self, path: str, query=None, *, headers=None) -> dict[str, object]:
        del headers
        self.calls.append(("GET", path))
        if path == "/api/delivery/rd-collaboration-runs/run-scenario/work-items":
            return {"dependencies": [], "items": [self._item_response()]}
        if path == "/api/delivery/decision-requests/decision-timeout":
            return {
                "decision_type": "runner_timeout_recovery",
                "evidence_json": [
                    {
                        "error_code": "AI_EXECUTOR_TASK_TIMEOUT",
                        "max_iterations": 1,
                        "timed_out_attempt_count": 1,
                        "timeout_seconds": 3,
                    }
                ],
                "id": "decision-timeout",
                "options_json": [
                    {"code": "retry_after_human_confirmation"},
                    {"code": "cancel_work_item"},
                ],
                "status": "pending",
                "version": 1,
            }
        if path == "/api/delivery/decision-requests/decision-high-risk":
            return {
                "decision_type": "high_risk_ai_dispatch",
                "id": "decision-high-risk",
                "options_json": [
                    {"code": "approve_dispatch"},
                    {"code": "cancel_work_item"},
                ],
                "status": "pending",
                "version": 1,
            }
        if path.startswith("/api/ai-tasks/"):
            task_id = path.rsplit("/", 1)[-1]
            first_quality_failure = (
                self.scenario == "quality-rework" and task_id == "ai-task-attempt-1"
            )
            return {
                "id": task_id,
                "pending_review": (
                    None if first_quality_failure else {"id": f"review-{task_id}"}
                ),
                "quality_gate": {
                    "id": f"gate-{task_id}",
                    "independent_evidence_count": 1,
                    "status": "failed" if first_quality_failure else "passed",
                    "verified_attestation_count": 1,
                    "verifier_trust_isolated": True,
                },
                "status": "failed" if first_quality_failure else "waiting_review",
            }
        if path == "/api/system/ai-executor-tasks":
            ai_task_id = str((query or {}).get("ai_task_id") or "")
            attempt_no = 1 if ai_task_id.endswith("-1") else 2
            coding_status = (
                "cancelled"
                if self.scenario == "cancel-resume" and attempt_no == 1
                else (
                    "timed_out"
                    if self.scenario == "timeout-recovery" and attempt_no == 1
                    else "succeeded"
                )
            )
            items: list[dict[str, object]] = [
                {
                    "ai_task_id": ai_task_id,
                    "id": f"runner-attempt-{attempt_no}",
                    "runner_id": "runner-codex",
                    "status": coding_status,
                    "task_kind": "coding",
                    "workspace_root": f"/not-reported/by-attempt-{attempt_no}",
                }
            ]
            if coding_status == "succeeded":
                items.append(
                    {
                        "ai_task_id": ai_task_id,
                        "id": f"verifier-attempt-{attempt_no}",
                        "quality_gate_run_id": f"gate-{ai_task_id}",
                        "request_config": {
                            "required_trust_domain": "verification",
                        },
                        "runner_id": "runner-verifier",
                        "status": "succeeded",
                        "task_kind": "quality_gate",
                    }
                )
            return {"items": items}
        raise AssertionError(f"unexpected GET {path} {query}")

    def post(self, path: str, body=None, *, headers=None) -> dict[str, object]:
        del headers
        payload = dict(body or {})
        self.calls.append(("POST", path))
        if path == "/api/delivery/rd-work-items/work-scenario/cancel":
            assert self.scenario == "cancel-resume"
            assert payload["version"] == 3
            self.phase = 1
            return {
                "idempotent_replay": False,
                "next_state": "cancelled",
                "work_item": {"id": "work-scenario", "status": "cancelled", "version": 4},
            }
        if path == "/api/delivery/rd-work-items/work-scenario/resume":
            assert self.scenario == "cancel-resume"
            assert self.phase == 1
            assert payload["version"] == 4
            self.phase = 2
            return {
                "idempotent_replay": False,
                "next_state": "rework_required",
                "work_item": {
                    "id": "work-scenario",
                    "status": "rework_required",
                    "version": 5,
                },
            }
        if path in {
            "/api/delivery/decision-requests/decision-timeout/decide",
            "/api/delivery/decision-requests/decision-high-risk/decide",
        }:
            expected = (
                "retry_after_human_confirmation"
                if self.scenario == "timeout-recovery"
                else "approve_dispatch"
            )
            assert payload["selected_option"] == expected
            self.decision_posts += 1
            self.phase = 1
            return {
                "decision_request": {
                    "id": path.split("/")[-2],
                    "selected_option": expected,
                    "status": "approved",
                },
                "idempotent_replay": self.decision_posts > 1,
                "next_state": "ready",
            }
        raise AssertionError(f"unexpected POST {path}")


class BrowserHighRiskScenarioClient(GovernanceScenarioClient):
    def __init__(self) -> None:
        super().__init__("high-risk-dispatch")
        self.browser_completed = False

    def get(self, path: str, query=None, *, headers=None) -> dict[str, object]:
        if path == "/api/delivery/decision-requests/decision-high-risk":
            self.calls.append(("GET", path))
            return {
                "decision_type": "high_risk_ai_dispatch",
                "id": "decision-high-risk",
                "options_json": [
                    {"code": "approve_dispatch"},
                    {"code": "cancel_work_item"},
                ],
                "selected_option_code": (
                    "approve_dispatch" if self.browser_completed else None
                ),
                "status": "approved" if self.browser_completed else "pending",
                "version": 2 if self.browser_completed else 1,
            }
        return super().get(path, query, headers=headers)


def test_browser_high_risk_decision_uses_only_safe_option_and_polls_durable_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = BrowserHighRiskScenarioClient()
    browser_calls: list[dict[str, object]] = []

    def complete_browser_decision(config, **identifiers):
        browser_calls.append({"config": config, **identifiers})
        client.browser_completed = True
        client.phase = 1

    monkeypatch.setattr(rd_delivery_e2e, "run_browser_review", complete_browser_decision)
    config = valid_config(
        artifact_dir="/private/tmp/rd-e2e-browser",
        review_channel="browser",
        timeout_seconds=2,
    )

    outcome = rd_delivery_e2e.validate_governance_scenario(
        client,
        scenario="high-risk-dispatch",
        config=config,
        marker="high-risk-browser",
        owner_password="owner-secret",
        owner_username="owner@example.com",
        run_id="run-scenario",
        version_id="version-scenario",
        work_item_id="work-scenario",
    )

    assert outcome.observed_states == ("waiting_human", "running", "reviewing")
    assert browser_calls == [
        {
            "config": config,
            "decision_request_id": "decision-high-risk",
            "run_id": "run-scenario",
            "task_id": None,
            "version_id": "version-scenario",
        }
    ]
    assert not any(
        method == "POST" and path.endswith("/decision-high-risk/decide")
        for method, path in client.calls
    )


@pytest.mark.parametrize(
    ("scenario", "attempt_numbers", "first_status"),
    [
        ("quality-rework", [1, 2], "failed"),
        ("cancel-resume", [1, 2], "cancelled"),
        ("timeout-recovery", [1, 2], "failed"),
        ("high-risk-dispatch", [1], "completed"),
    ],
)
def test_governance_scenarios_produce_immutable_attempt_chains(
    scenario: str,
    attempt_numbers: list[int],
    first_status: str,
) -> None:
    client = GovernanceScenarioClient(scenario)

    outcome = rd_delivery_e2e.validate_governance_scenario(
        client,
        scenario=scenario,
        config=valid_config(timeout_seconds=2),
        marker="scenario-marker",
        owner_password="owner-secret",
        owner_username="owner@example.com",
        run_id="run-scenario",
        work_item_id="work-scenario",
    )

    assert [item["attempt_no"] for item in outcome.attempt_chain] == attempt_numbers
    assert outcome.attempt_chain[0]["status"] == first_status
    assert [item["runner_task_id"] for item in outcome.attempt_chain] == [
        f"runner-attempt-{attempt_no}" for attempt_no in attempt_numbers
    ]
    assert "owner-secret" not in repr(outcome)
    assert "reviewer-secret" not in repr(outcome)
    assert all(
        set(item).issubset(
            {
                "ai_task_id",
                "attempt_no",
                "completed_at",
                "failure_code",
                "fence_event_id",
                "late_result_fenced",
                "rework_evidence_count",
                "runner_status",
                "runner_task_id",
                "started_at",
                "status",
                "workspace_fingerprint",
            }
        )
        for item in outcome.attempt_chain
    )

    posted_paths = [path for method, path in client.calls if method == "POST"]
    assert not any(
        path == "/api/ai-tasks"
        or path.startswith("/api/ai-tasks/")
        or path.endswith("/retry")
        or path.endswith("/start")
        or path.endswith("/complete")
        or "/webhooks/" in path
        or path.startswith("/api/devops/deployments")
        for path in posted_paths
    )


def test_quality_rework_requires_failed_gate_before_attempt_two() -> None:
    client = GovernanceScenarioClient("quality-rework")

    outcome = rd_delivery_e2e.validate_governance_scenario(
        client,
        scenario="quality-rework",
        config=valid_config(timeout_seconds=2),
        marker="quality-marker",
        owner_password="owner-secret",
        owner_username="owner@example.com",
        run_id="run-scenario",
        work_item_id="work-scenario",
    )

    assert outcome.observed_states == ("rework_required", "reviewing")
    assert outcome.attempt_chain[0]["failure_code"] is None
    assert outcome.attempt_chain[0]["rework_evidence_count"] == 0
    assert outcome.transition_evidence == (
        {
            "attempt_no": 1,
            "quality_gate_id": "gate-ai-task-attempt-1",
            "quality_gate_status": "failed",
            "verifier_runner_task_id": "verifier-attempt-1",
        },
    )


def test_cancel_resume_uses_only_work_item_commands_and_requires_fenced_late_result() -> None:
    client = GovernanceScenarioClient("cancel-resume")

    outcome = rd_delivery_e2e.validate_governance_scenario(
        client,
        scenario="cancel-resume",
        config=valid_config(timeout_seconds=2),
        marker="cancel-marker",
        owner_password="owner-secret",
        owner_username="owner@example.com",
        run_id="run-scenario",
        work_item_id="work-scenario",
    )

    assert outcome.observed_states == (
        "running",
        "cancelled",
        "rework_required",
        "reviewing",
    )
    assert outcome.attempt_chain[0]["runner_status"] == "cancelled"
    assert outcome.attempt_chain[0]["late_result_fenced"] is True
    assert [path for method, path in client.calls if method == "POST"] == [
        "/api/delivery/rd-work-items/work-scenario/cancel",
        "/api/delivery/rd-work-items/work-scenario/resume",
    ]


def test_cancel_resume_waits_for_runner_terminal_and_durable_fence() -> None:
    class DelayedFenceClient(GovernanceScenarioClient):
        def __init__(self) -> None:
            super().__init__("cancel-resume")
            self.cancelled_reads = 0

        def _item_response(self) -> dict[str, object]:
            item = super()._item_response()
            if item["status"] == "cancelled":
                self.cancelled_reads += 1
                if self.cancelled_reads == 1:
                    history = dict(item["attempt_history"])
                    attempt = dict(history["items"][0])
                    attempt.update(
                        {
                            "fence_event_id": None,
                            "late_result_fenced": False,
                            "runner_status": "cancel_requested",
                        }
                    )
                    item["attempt_history"] = {**history, "items": [attempt]}
            return item

    client = DelayedFenceClient()

    rd_delivery_e2e.validate_governance_scenario(
        client,
        scenario="cancel-resume",
        config=valid_config(timeout_seconds=2),
        marker="cancel-wait-marker",
        owner_password="owner-secret",
        owner_username="owner@example.com",
        run_id="run-scenario",
        work_item_id="work-scenario",
    )

    assert client.cancelled_reads >= 2


def test_timeout_recovery_uses_only_frozen_human_retry_and_retains_workspace() -> None:
    client = GovernanceScenarioClient("timeout-recovery")

    outcome = rd_delivery_e2e.validate_governance_scenario(
        client,
        scenario="timeout-recovery",
        config=valid_config(timeout_seconds=2),
        marker="timeout-marker",
        owner_password="owner-secret",
        owner_username="owner@example.com",
        run_id="run-scenario",
        work_item_id="work-scenario",
    )

    assert outcome.observed_states == ("waiting_human", "ready", "reviewing")
    assert outcome.attempt_chain[0]["runner_status"] == "timed_out"
    assert (
        outcome.attempt_chain[0]["workspace_fingerprint"]
        == outcome.attempt_chain[1]["workspace_fingerprint"]
    )
    decision_posts = [
        path for method, path in client.calls if method == "POST" and "/decision-requests/" in path
    ]
    assert decision_posts == [
        "/api/delivery/decision-requests/decision-timeout/decide"
    ]


def test_high_risk_dispatch_replay_creates_exactly_one_attempt() -> None:
    client = GovernanceScenarioClient("high-risk-dispatch")

    outcome = rd_delivery_e2e.validate_governance_scenario(
        client,
        scenario="high-risk-dispatch",
        config=valid_config(timeout_seconds=2),
        marker="high-risk-marker",
        owner_password="owner-secret",
        owner_username="owner@example.com",
        run_id="run-scenario",
        work_item_id="work-scenario",
    )

    assert outcome.observed_states == ("waiting_human", "running", "reviewing")
    assert len(outcome.attempt_chain) == 1
    assert client.decision_posts == 2
