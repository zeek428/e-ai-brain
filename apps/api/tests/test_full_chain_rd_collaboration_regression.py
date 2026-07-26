from __future__ import annotations

import base64
import importlib.util
import json
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def _load_module(name: str, relative_path: str):
    script_path = Path(__file__).resolve().parents[3] / relative_path
    script_directory = str(script_path.parent)
    if script_directory not in sys.path:
        sys.path.insert(0, script_directory)
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fixture_module_paths_for_minimal_run() -> list[str]:
    fixture = _load_module(
        "full_chain_regression_rd_fixture_under_test",
        "scripts/full_chain_regression_rd_fixture.py",
    )

    class FixtureClient:
        def __init__(self) -> None:
            self.paths: list[str] = []

        def get(self, path: str, query=None):
            self.paths.append(path)
            assert query is None
            assert path == "/api/requirements/requirement-1/assessments/latest"
            return {"id": "assessment-1", "version": 2}

        def post(self, path: str, body=None, extra_headers=None):
            self.paths.append(path)
            assert extra_headers is None
            if path == "/api/requirements":
                return {"id": "requirement-1"}
            if path == "/api/requirements/requirement-1/assessments":
                return {
                    "id": "assessment-1",
                    "initial_strategy_snapshot_id": "strategy-1",
                }
            if path == "/api/requirement-assessments/assessment-1/opinions":
                return {"id": "opinion-1"}
            if path == "/api/requirement-assessments/assessment-1/decisions":
                return {
                    "grouping": {
                        "status": "planned",
                        "version": {"id": "version-1", "scope_version": 3},
                    }
                }
            if path == "/api/product-versions/version-1/collaboration-runs":
                return {
                    "delivery_target": "ready_for_release",
                    "id": "run-1",
                    "strategy_snapshot_kind": "version_resolved",
                }
            if path == "/api/delivery/rd-collaboration-runs/run-1/plan":
                return {
                    "work_items": [
                        {
                            "id": "implementation-1",
                            "status": "ready",
                            "work_item_type": "implementation",
                        }
                    ]
                }
            raise AssertionError(f"unexpected request: {path} {body}")

    spec = fixture.RdFixtureSpec(
        dependencies=(),
        marker="fixture-marker",
        policy_overrides={},
        product_id="product-1",
        repository_id="repository-1",
        required_role_codes=("developer",),
        role_bindings=(
            {
                "actor_mode": "human",
                "candidate_human_user_ids": ["owner-1"],
                "role_code": "developer",
                "status": "active",
            },
        ),
        work_items=(
            {
                "id": "implementation-1",
                "owner_role_code": "developer",
                "priority": 1,
                "reviewer_role_code": "developer",
                "work_item_type": "implementation",
            },
        ),
    )
    client = FixtureClient()

    result = fixture.create_rd_fixture(client, owner_user_id="owner-1", spec=spec)

    assert result == fixture.RdFixtureResult(
        assessment_id="assessment-1",
        product_id="product-1",
        requirement_id="requirement-1",
        run_id="run-1",
        scope_version=3,
        strategy_snapshot_id="strategy-1",
        version_id="version-1",
        work_items=(
            {
                "id": "implementation-1",
                "status": "ready",
                "work_item_type": "implementation",
            },
        ),
    )
    try:
        result.run_id = "mutated"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("fixture result must be immutable")
    try:
        spec.marker = "mutated"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("fixture spec must be immutable")
    return client.paths


def test_v2_fixture_uses_assessment_grouping_and_collaboration_run() -> None:
    paths = fixture_module_paths_for_minimal_run()

    assert paths == [
        "/api/requirements",
        "/api/requirements/requirement-1/assessments",
        "/api/requirement-assessments/assessment-1/opinions",
        "/api/requirements/requirement-1/assessments/latest",
        "/api/requirement-assessments/assessment-1/decisions",
        "/api/product-versions/version-1/collaboration-runs",
        "/api/delivery/rd-collaboration-runs/run-1/plan",
    ]
    assert all("/approve" not in path for path in paths)
    assert all("generate-task" not in path for path in paths)


def test_rd_collaboration_regression_is_a_declared_targeted_suite() -> None:
    suites = _load_module(
        "full_chain_regression_suites_under_test",
        "scripts/full_chain_regression_suites.py",
    )

    assert "rd_collaboration" in suites.REGRESSION_OBJECTIVE_DOMAIN_KEYS
    assert "rd-collaboration" in suites.REGRESSION_TARGETED_SUITE_NAMES
    coverage = suites.regression_suite_coverage("rd-collaboration")
    assert coverage["covered_keys"] == ["rd_collaboration"]
    assert coverage["is_complete_chain"] is False


def test_api_client_solves_the_local_login_math_challenge() -> None:
    regression = _load_module(
        "full_chain_regression_login_under_test",
        "scripts/full_chain_regression.py",
    )

    class ChallengeClient(regression.ApiClient):
        def __init__(self) -> None:
            super().__init__("http://localhost:8000")
            self.calls: list[tuple[str, str, dict | None]] = []

        def request(self, method, path, *, authenticated=True, body=None, extra_headers=None):
            self.calls.append((method, path, body))
            if path == "/api/auth/login-challenge":
                return {"challenge_id": "challenge-1", "question": "请计算：7 + 8 = ?"}
            if path == "/api/auth/login":
                assert body == {
                    "challenge_answer": "15",
                    "challenge_id": "challenge-1",
                    "password": "secret",
                    "username": "admin@example.com",
                }
                return {"access_token": "access-token", "user": {"id": "user-admin"}}
            raise AssertionError(f"unexpected request: {method} {path}")

    client = ChallengeClient()

    response = client.login("admin@example.com", "secret")

    assert response["user"]["id"] == "user-admin"
    assert client.token == "access-token"
    assert [path for _method, path, _body in client.calls] == [
        "/api/auth/login-challenge",
        "/api/auth/login",
    ]


def test_rd_collaboration_suite_dispatches_to_its_dedicated_public_api_regression(
    monkeypatch,
) -> None:
    regression = _load_module(
        "full_chain_regression_dispatch_under_test",
        "scripts/full_chain_regression.py",
    )
    called: dict[str, object] = {}

    def fake_validate(client, *, username: str, password: str):
        called.update({"client": client, "username": username, "password": password})
        return [regression.StepResult("rd_collaboration", "no deployment")]

    sentinel_client = object()
    monkeypatch.setattr(
        regression,
        "validate_rd_collaboration_quick_regression",
        fake_validate,
    )

    results = regression.run_regression_suite(
        sentinel_client,
        suite="rd-collaboration",
        task_execution_mode="deterministic",
        username="admin@example.com",
        password="secret",
    )

    assert called == {
        "client": sentinel_client,
        "username": "admin@example.com",
        "password": "secret",
    }
    assert results[-1] == regression.StepResult("rd_collaboration", "no deployment")


class _SimulatedProtocolClient:
    def __init__(self, *, requires_quality_gate: bool = False) -> None:
        self.requests: list[tuple[str, str, dict | None, dict[str, str] | None]] = []
        self.runner_tokens: dict[str, str] = {}
        self.runner_creation_count = 0
        self.runner_completed = False
        self.requires_quality_gate = requires_quality_gate
        self.quality_gate_completed = False
        self.reviewer_approved = False
        self.reviewing_reads = 0
        self.verification_public_key = ""

    def get(self, path: str, query=None, *, headers=None):
        self.requests.append(("GET", path, query, headers))
        if path == "/api/ai-tasks/task-1":
            return {
                "id": "task-1",
                "pending_review": {"id": "review-1", "version": 1},
                "status": (
                    "waiting_review"
                    if self.runner_completed
                    and (not self.requires_quality_gate or self.quality_gate_completed)
                    else "running"
                ),
            }
        if path == "/api/system/ai-executor-tasks":
            assert query == {"ai_task_id": "task-1", "status": "queued"}
            if not self.requires_quality_gate or self.quality_gate_completed:
                return {"items": []}
            return {
                "items": [
                    {
                        "ai_task_id": "task-1",
                        "executor_type": "codex",
                        "id": "runner-task-2",
                        "request_config": {"required_trust_domain": "verification"},
                        "runner_id": "verification-runner-1",
                        "status": "queued",
                        "task_kind": "quality_gate",
                    }
                ]
            }
        if path == "/api/delivery/rd-collaboration-runs/run-1/work-items":
            status = (
                "running"
                if self.requires_quality_gate and not self.quality_gate_completed
                else (
                    "completed"
                    if self.reviewer_approved
                    else (
                        "running"
                        if self.requires_quality_gate and self.reviewing_reads == 0
                        else "reviewing"
                    )
                )
            )
            if (
                self.requires_quality_gate
                and self.quality_gate_completed
                and not self.reviewer_approved
            ):
                self.reviewing_reads += 1
            return {
                "items": [
                    {
                        "ai_task_id": "task-1",
                        "id": "work-item-1",
                        "status": status,
                    }
                ]
            }
        raise AssertionError(f"unexpected GET: {path} {query}")

    def post(self, path: str, body=None, *, headers=None):
        self.requests.append(("POST", path, body, headers))
        if path == "/api/system/ai-executor-runners":
            self.runner_creation_count += 1
            if self.runner_creation_count == 1:
                assert {key: value for key, value in body.items() if key != "runner_token"} == {
                    "executor_types": ["codex"],
                    "name": "Simulated v2 Runner fixture-marker",
                    "protocol": "runner_polling",
                    "trust_boundary_id": "simulated-coding-fixture-marker",
                    "trust_domain": "coding",
                    "workspace_roots": ["/workspace/regression"],
                }
                self.runner_tokens["runner-1"] = str(body["runner_token"])
                assert self.runner_tokens["runner-1"]
                return {"id": "runner-1"}
            assert self.runner_creation_count == 2
            assert {
                key: value
                for key, value in body.items()
                if key not in {"attestation_public_key", "runner_token"}
            } == {
                "attestation_status": "active",
                "executor_types": ["codex"],
                "name": "Simulated v2 verification Runner fixture-marker",
                "protocol": "runner_polling",
                "trust_boundary_id": "simulated-verification-fixture-marker",
                "trust_domain": "verification",
                "workspace_roots": ["/workspace/regression"],
            }
            self.runner_tokens["verification-runner-1"] = str(body["runner_token"])
            assert self.runner_tokens["verification-runner-1"]
            assert self.runner_tokens["verification-runner-1"] != self.runner_tokens["runner-1"]
            self.verification_public_key = str(body["attestation_public_key"])
            assert len(base64.b64decode(self.verification_public_key, validate=True)) == 32
            return {"id": "verification-runner-1"}
        if path == "/api/delivery/rd-ai-employees":
            assert body == {
                "capability_tags": ["product_detail_design"],
                "code": "simulated-ai-fixture-marker",
                "name": "Simulated v2 AI employee fixture-marker",
                "persona_json": {"mode": "deterministic_regression"},
                "persona_version": 1,
                "work_style_json": {"mode": "single_pass"},
                "work_style_version": 1,
            }
            return {"id": "ai-employee-1"}
        if path == "/api/delivery/rd-executor-profiles":
            assert body == {
                "code": "simulated-runner-profile-fixture-marker",
                "executor_type": "codex",
                "health_status": "healthy",
                "max_concurrency": 1,
                "name": "Simulated v2 Runner profile fixture-marker",
                "runner_id": "runner-1",
                "supported_role_codes": ["designer", "reviewer"],
                "workspace_capabilities": {"workspace_root": "/workspace/regression"},
            }
            return {"id": "executor-profile-1"}
        if path == "/api/system/ai-executor-tasks/claim":
            runner_id = "verification-runner-1" if self.runner_completed else "runner-1"
            assert body == {"executor_type": "codex", "runner_id": runner_id}
            assert headers == {"X-Runner-Token": self.runner_tokens[runner_id]}
            return {
                "task": {
                    "ai_task_id": "task-1",
                    "id": "runner-task-2" if self.runner_completed else "runner-task-1",
                    "input_payload": (
                        {
                            "checks": [{"required": True, "type": "unit_test"}],
                            "rd_work_item_attempt_id": "attempt-1",
                        }
                        if self.runner_completed
                        else {"rd_work_item_attempt_id": "attempt-1"}
                    ),
                    "status": "claimed",
                    "task_kind": (
                        "quality_gate"
                        if self.runner_completed
                        else ("coding" if self.requires_quality_gate else "product_detail_design")
                    ),
                }
            }
        if path == "/api/system/ai-executor-tasks/runner-task-1/logs":
            assert body == {
                "logs": [{"level": "info", "message": "deterministic v2 regression completed"}],
                "runner_id": "runner-1",
                "status": "running",
            }
            assert headers == {"X-Runner-Token": self.runner_tokens["runner-1"]}
            return {"task": {"id": "runner-task-1", "status": "running"}}
        if path == "/api/system/ai-executor-tasks/runner-task-1/complete":
            assert body == {
                "logs": [{"level": "info", "message": "deterministic v2 regression completed"}],
                "result_json": {"summary": "deterministic v2 regression output"},
                "runner_id": "runner-1",
                "status": "succeeded",
            }
            assert headers == {"X-Runner-Token": self.runner_tokens["runner-1"]}
            self.runner_completed = True
            return {"task": {"id": "runner-task-1", "status": "succeeded"}}
        if path == "/api/system/ai-executor-tasks/runner-task-2/logs":
            assert body == {
                "logs": [{"level": "info", "message": "deterministic v2 regression completed"}],
                "runner_id": "verification-runner-1",
                "status": "running",
            }
            assert headers == {"X-Runner-Token": self.runner_tokens["verification-runner-1"]}
            return {"task": {"id": "runner-task-2", "status": "running"}}
        if path == "/api/system/ai-executor-tasks/runner-task-2/complete":
            assert body["logs"] == [
                {"level": "info", "message": "deterministic v2 regression completed"}
            ]
            assert body["runner_id"] == "verification-runner-1"
            assert body["status"] == "succeeded"
            result_json = body["result_json"]
            assert result_json["checks"] == [
                {
                    "evidence_ref": "simulated://runner-task-2/unit_test",
                    "status": "passed",
                    "type": "unit_test",
                }
            ]
            proof = result_json["execution_attestation"]
            assert proof["payload"] == {"runner_task_id": "runner-task-2"}
            Ed25519PublicKey.from_public_bytes(
                base64.b64decode(self.verification_public_key, validate=True)
            ).verify(
                base64.b64decode(proof["signature"], validate=True),
                json.dumps(
                    proof["payload"], ensure_ascii=True, separators=(",", ":"), sort_keys=True
                ).encode("utf-8"),
            )
            assert headers == {"X-Runner-Token": self.runner_tokens["verification-runner-1"]}
            self.quality_gate_completed = True
            return {"task": {"id": "runner-task-2", "status": "succeeded"}}
        raise AssertionError(f"unexpected POST: {path} {body}")


class _IndependentReviewerClient:
    def __init__(self, protocol_client: _SimulatedProtocolClient) -> None:
        self.protocol_client = protocol_client
        self.requests: list[tuple[str, str, dict | None, dict[str, str] | None]] = []

    def get(self, path: str, query=None, *, headers=None):
        self.requests.append(("GET", path, query, headers))
        assert self.protocol_client.runner_completed
        assert (
            not self.protocol_client.requires_quality_gate
            or self.protocol_client.quality_gate_completed
        )
        assert path == "/api/reviews/pending"
        assert query == {"ai_task_id": "task-1"}
        return {"items": [{"ai_task_id": "task-1", "id": "review-1", "version": 1}]}

    def post(self, path: str, body=None, *, headers=None):
        self.requests.append(("POST", path, body, headers))
        assert path == "/api/reviews/review-1/approve"
        assert body == {"version": 1}
        self.protocol_client.reviewer_approved = True
        return {"task_status": "completed"}


def simulate_protocol_fixture(*, requires_quality_gate: bool = False):
    protocol = _load_module(
        "full_chain_regression_rd_runner_protocol_under_test",
        "scripts/full_chain_regression_rd_runner_protocol.py",
    )
    client = _SimulatedProtocolClient(requires_quality_gate=requires_quality_gate)
    reviewer_client = _IndependentReviewerClient(client)
    session = protocol.create_simulated_runner_session(
        client,
        marker="fixture-marker",
        workspace_root="/workspace/regression",
        role_codes=("designer", "reviewer"),
    )
    result = protocol.complete_ai_work_item_via_runner_protocol(
        client,
        session,
        run_id="run-1",
        work_item_id="work-item-1",
        reviewer_client=reviewer_client,
        timeout_seconds=1.0 if requires_quality_gate else 0.1,
    )
    return client, reviewer_client, result


def test_simulated_runner_completes_v2_task_without_git_side_effects() -> None:
    client, reviewer_client, result = simulate_protocol_fixture()

    assert result.work_item["status"] == "completed"
    assert result.ai_task_id == "task-1"
    assert result.runner_task_ids == ("runner-task-1",)
    assert result.review_id == "review-1"
    assert "git_delivery" not in result.runner_result
    assert [path for method, path, _body, _headers in client.requests if method == "POST"] == [
        "/api/system/ai-executor-runners",
        "/api/system/ai-executor-runners",
        "/api/delivery/rd-ai-employees",
        "/api/delivery/rd-executor-profiles",
        "/api/system/ai-executor-tasks/claim",
        "/api/system/ai-executor-tasks/runner-task-1/logs",
        "/api/system/ai-executor-tasks/runner-task-1/complete",
    ]
    reviewer_post_paths = [
        path for method, path, _body, _headers in reviewer_client.requests if method == "POST"
    ]
    assert reviewer_post_paths == ["/api/reviews/review-1/approve"]


def test_simulated_runner_token_is_excluded_from_step_detail_and_json_report() -> None:
    client, _reviewer_client, result = simulate_protocol_fixture()
    collaboration = _load_module(
        "full_chain_regression_rd_collaboration_under_test",
        "scripts/full_chain_regression_rd_collaboration.py",
    )

    detail = collaboration.StepResult(
        "simulated_runner", result.step_detail
    ).detail
    report_content = json.dumps(result.report, sort_keys=True)
    token = client.runner_tokens["runner-1"]

    assert token not in detail
    assert token not in report_content
    assert all(
        headers == {"X-Runner-Token": client.runner_tokens["runner-1"]}
        for _method, path, _body, headers in client.requests
        if path.endswith(("/claim", "/logs", "/complete"))
        and "runner-task-1" in path
    )


def test_simulated_runner_completes_quality_gate_before_reviewing_work_item() -> None:
    client, _reviewer_client, result = simulate_protocol_fixture(requires_quality_gate=True)

    assert result.runner_task_ids == ("runner-task-1", "runner-task-2")
    assert result.work_item["status"] == "completed"
    assert client.reviewing_reads == 2


def test_simulated_runner_redacts_tokens_embedded_in_error_and_report_strings() -> None:
    fixture = _load_module(
        "full_chain_regression_rd_fixture_redaction_under_test",
        "scripts/full_chain_regression_rd_fixture.py",
    )
    client, _reviewer_client, result = simulate_protocol_fixture()
    coding_token = client.runner_tokens["runner-1"]
    verifier_token = client.runner_tokens.get("verification-runner-1", "injected-verifier-token")

    redacted_error = fixture.safe_report_value(
        {"message": f"Runner authentication failed: {coding_token}"},
        secret_values=(coding_token, verifier_token),
    )
    redacted_result = replace(
        result,
        runner_result={"error": f"verification token rejected: {verifier_token}"},
    )
    try:
        fixture.wait_for_value(
            lambda: {"message": f"Runner authentication failed: {coding_token}"},
            lambda _value: False,
            timeout_seconds=0.01,
            description="redaction timeout",
            secret_values=(coding_token,),
        )
    except AssertionError as exc:
        timeout_message = str(exc)
    else:
        raise AssertionError("Redaction timeout should fail")

    assert coding_token not in redacted_error["message"]
    assert verifier_token not in json.dumps(redacted_result.report, sort_keys=True)
    assert coding_token not in timeout_message


def test_simulated_runner_freezes_distinct_ai_and_human_role_bindings() -> None:
    protocol = _load_module(
        "full_chain_regression_rd_runner_protocol_bindings_under_test",
        "scripts/full_chain_regression_rd_runner_protocol.py",
    )
    session = protocol.SimulatedRunnerSession(
        ai_employee_id="ai-employee-1",
        executor_profile_id="executor-profile-1",
        runner_headers={"X-Runner-Token": "token"},
        runner_id="runner-1",
    )

    bindings = protocol.simulated_runner_role_bindings(
        session,
        role_code="designer",
        reviewer_user_id="reviewer-1",
    )

    assert bindings == (
        {
            "actor_mode": "ai",
            "candidate_ai_employee_ids": ["ai-employee-1"],
            "primary_executor_profile_id": "executor-profile-1",
            "role_code": "designer",
            "status": "active",
        },
        {
            "actor_mode": "human",
            "candidate_human_user_ids": ["reviewer-1"],
            "role_code": "designer",
            "status": "active",
        },
    )
