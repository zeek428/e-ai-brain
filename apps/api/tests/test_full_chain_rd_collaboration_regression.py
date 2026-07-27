from __future__ import annotations

import base64
import importlib.util
import json
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from types import SimpleNamespace

import pytest
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


def test_v2_setup_separates_human_assessment_from_ai_delivery_and_approves_workspace(
    monkeypatch,
) -> None:
    suites = _load_module(
        "full_chain_regression_suites_workspace_under_test",
        "scripts/full_chain_regression_suites.py",
    )
    session = SimpleNamespace(
        ai_employee_id="ai-employee-1",
        executor_profile_id="executor-profile-1",
    )
    fixture = SimpleNamespace(run_id="run-1")
    captured_fixture_kwargs: dict[str, object] = {}
    monkeypatch.setattr(
        suites,
        "create_simulated_runner_session",
        lambda *_args, **_kwargs: session,
    )
    monkeypatch.setattr(
        suites,
        "simulated_runner_role_bindings",
        lambda *_args, **kwargs: (
            {
                "actor_mode": "ai",
                "primary_executor_profile_id": session.executor_profile_id,
                "role_code": kwargs["role_code"],
                "status": "active",
            },
            {
                "actor_mode": "human",
                "candidate_human_user_ids": [kwargs["reviewer_user_id"]],
                "role_code": kwargs["role_code"],
                "status": "active",
            },
        ),
    )
    def create_fixture(fixture_client, **kwargs):
        captured_fixture_kwargs.update(kwargs)
        requirement = fixture_client.post(
            "/api/requirements",
            {"title": "workspace fixture requirement"},
        )
        fixture_client.post(
            "/api/delivery/rd-collaboration-runs/run-1/plan",
            {
                "dependencies": list(kwargs["spec"].dependencies),
                "work_items": list(kwargs["spec"].work_items),
            },
        )
        assert requirement["id"] == "requirement-1"
        return fixture

    monkeypatch.setattr(suites, "create_rd_fixture", create_fixture)

    class SetupClient:
        def __init__(self) -> None:
            self.requests: list[tuple[str, str, dict | None]] = []

        def post(self, path: str, body=None, *, headers=None):
            assert headers is None
            self.requests.append(("POST", path, body))
            if path == "/api/delivery/rd-roles":
                return {"id": f"role-{body['code']}"}
            if path == "/api/delivery/rd-task-executor-policies":
                return {"policy": {"id": "policy-1"}}
            if path == "/api/requirements":
                return {"id": "requirement-1"}
            if path == "/api/delivery/rd-collaboration-runs/run-1/plan":
                return {"work_items": body["work_items"]}
            raise AssertionError(f"unexpected POST {path} {body}")

        def request(self, method: str, path: str, *, body=None):
            self.requests.append((method, path, body))
            return {"id": session.executor_profile_id, **(body or {})}

    client = SetupClient()
    setup = suites.create_v2_collaboration_setup(
        client,
        dependencies=(),
        marker="workspace-fixture",
        owner_user_id="user-admin",
        product_id="product-1",
        repository_id="repository-1",
        requirement=None,
        work_items=(
            {
                "id": "design",
                "owner_role_code": "simulated-ai-workspace-fixture",
                "reviewer_role_code": "simulated-reviewer-workspace-fixture",
                "work_item_type": "product_detail_design",
            },
        ),
        workspace_root="/workspace/regression",
    )

    assert setup.fixture is fixture
    assert (
        "PATCH",
        "/api/delivery/rd-executor-profiles/executor-profile-1",
        {
            "workspace_capabilities": {
                "assessment_workspace_root": "/workspace/regression",
                "workspace_root": "/workspace/regression",
            }
        },
    ) in client.requests
    policy_body = next(
        body
        for method, path, body in client.requests
        if method == "POST" and path == "/api/delivery/rd-task-executor-policies"
    )
    assert policy_body["team_config"]["required_role_codes"] == [
        "simulated-assessor-workspace-fixture"
    ]
    assert policy_body["git_config"] == {
        "repository_id": "repository-1",
        "workspace_root": "/workspace/regression",
    }
    bindings_by_role = {
        binding["role_code"]: binding
        for binding in policy_body["role_bindings"]
    }
    assert bindings_by_role["simulated-ai-workspace-fixture"]["actor_mode"] == "ai"
    assert (
        bindings_by_role["simulated-reviewer-workspace-fixture"]["actor_mode"]
        == "human"
    )
    assert (
        bindings_by_role["simulated-assessor-workspace-fixture"]["actor_mode"]
        == "human"
    )
    fixture_spec = captured_fixture_kwargs["spec"]
    assert fixture_spec.required_role_codes == (
        "simulated-assessor-workspace-fixture",
    )
    plan_body = next(
        body
        for method, path, body in client.requests
        if method == "POST"
        and path == "/api/delivery/rd-collaboration-runs/run-1/plan"
    )
    assert {
        item["requirement_id"] for item in plan_body["work_items"]
    } == {"requirement-1"}


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


class _TraceBoundaryReached(RuntimeError):
    pass


class _RegressionEntrypointTraceClient:
    def __init__(self, *, trace_knowledge_deposit: bool = False) -> None:
        self.requests: list[tuple[str, str, dict | None]] = []
        self.deposit_ai_task_id = ""
        self.trace_knowledge_deposit = trace_knowledge_deposit

    def login(self, username: str, password: str) -> dict:
        assert username == "admin@example.com"
        assert password == "secret"
        return {"user": {"id": "user-admin", "username": username}}

    def get(self, path: str, query=None, *, headers=None):
        assert headers is None
        self.requests.append(("GET", path, query))
        if path == "/api/knowledge/deposits":
            if self.trace_knowledge_deposit:
                return {
                    "items": [
                        {
                            "ai_task_id": self.deposit_ai_task_id,
                            "id": "deposit-1",
                            "status": "pending",
                        }
                    ]
                }
            raise _TraceBoundaryReached
        if path == "/api/knowledge/spaces":
            assert self.trace_knowledge_deposit
            return {
                "items": [
                    {
                        "id": "knowledge-space-1",
                        "status": "active",
                    }
                ],
                "total": 1,
            }
        if path == "/api/knowledge/index-health":
            raise _TraceBoundaryReached
        if path.endswith("/code-review-report"):
            return {"id": "code-review-report-1"}
        if path == "/api/delivery/rd-collaboration-runs/run-1/work-items":
            return {
                "items": [
                    {
                        "id": "review",
                        "status": "waiting_human",
                        "suspended_decision_request_id": "decision-review",
                        "work_item_type": "code_review",
                    }
                ]
            }
        if path == "/api/delivery/decision-requests/decision-review":
            return {"id": "decision-review", "status": "pending", "version": 1}
        raise AssertionError(f"unexpected GET {path} {query}")

    def post(self, path: str, body=None, *, headers=None):
        assert headers is None
        self.requests.append(("POST", path, body))
        if path == "/api/products":
            return {"code": body["code"], "id": "product-1"}
        if path == "/api/products/product-1/modules":
            return {"code": "core", "id": "module-1"}
        if path == "/api/products/product-1/versions":
            return {"code": body["code"], "id": "version-1"}
        if path == "/api/insights/user-feedback":
            return {"id": "feedback-1"}
        if path == "/api/insights/user-feedback/feedback-1/convert-requirement":
            return {
                "feedback": {"status": "linked"},
                "requirement": {"id": "requirement-1"},
            }
        if path == "/api/requirements":
            return {"id": "requirement-1"}
        if path == "/api/requirements/requirement-1/approve":
            return {"status": "approved"}
        if path == "/api/requirements/batch-schedule":
            return {"updated_count": 1}
        if path == "/api/requirements/requirement-1/generate-task":
            return {"task_id": "design-task"}
        if path == "/api/ai-tasks":
            task_type = str((body or {}).get("task_type") or "")
            return {"id": f"{task_type}-task"}
        if path.endswith("/start") and path.startswith("/api/ai-tasks/"):
            return {"review_id": f"review-{path.split('/')[-2]}", "status": "waiting_review"}
        if path.startswith("/api/reviews/") and path.endswith("/approve"):
            return {"task_status": "completed"}
        if path == "/api/products/product-1/git-repositories":
            return {"id": "repository-1"}
        if path == "/api/product-versions/version-1/branch-configs":
            return {"id": "branch-config-1"}
        if path == "/api/product-versions/version-1/collaboration-runs":
            return {"id": "run-1"}
        if path == "/api/devops/gitlab/merge-requests/repository-1/7/snapshot":
            return {"id": "snapshot-1"}
        if path == "/api/delivery/rd-collaboration-runs/run-1/plan":
            plan = {
                "plan_version": 1,
                "work_items": [
                    {
                        **item,
                        "id": f"plan-1:{item['id']}",
                        "status": "ready" if index == 0 else "blocked",
                        "version": 1,
                    }
                    for index, item in enumerate(body["work_items"])
                ],
            }
            if self.trace_knowledge_deposit:
                self.deposit_ai_task_id = f"{plan['work_items'][0]['id']}-task"
            return plan
        if path == "/api/delivery/rd-collaboration-runs/run-1/replan":
            item = body["work_items"][0]
            return {
                "plan_version": 2,
                "work_items": [
                    {
                        **item,
                        "id": f"plan-2:{item['id']}",
                        "status": "ready",
                        "version": 1,
                    }
                ],
            }
        if path.endswith("/claim") and path.startswith("/api/delivery/rd-work-items/"):
            work_item_id = path.removesuffix("/claim").rsplit("/", 1)[-1]
            return {
                "attempt": {"id": "snapshot-binding-attempt"},
                "lease_token": "snapshot-binding-lease",
                "work_item": {
                    "id": work_item_id,
                    "status": "running",
                    "version": 2,
                },
            }
        if path.endswith("/submit") and path.startswith("/api/delivery/rd-work-items/"):
            work_item_id = path.removesuffix("/submit").rsplit("/", 1)[-1]
            return {
                "work_item": {
                    "id": work_item_id,
                    "status": "reviewing",
                    "version": 3,
                }
            }
        if path.endswith("/review") and path.startswith("/api/delivery/rd-work-items/"):
            work_item_id = path.removesuffix("/review").rsplit("/", 1)[-1]
            return {"work_item": {"id": work_item_id, "status": "completed"}}
        if path == "/api/delivery/decision-requests/decision-review/decide":
            return {"decision_request": {"status": "approved"}}
        if path == "/api/knowledge/deposits/deposit-1/approve":
            assert self.trace_knowledge_deposit
            return {
                "id": "deposit-1",
                "knowledge_document_id": "knowledge-document-1",
                "status": "approved",
            }
        if path == "/api/bugs":
            raise _TraceBoundaryReached
        if path == "/api/product-versions/version-1/advance-status":
            raise _TraceBoundaryReached
        raise AssertionError(f"unexpected POST {path} {body}")


def _install_v2_orchestration_fakes(monkeypatch, module) -> None:
    def create_setup(client, **kwargs):
        client.post(
            "/api/product-versions/version-1/collaboration-runs",
            {"repository_id": kwargs["repository_id"]},
        )
        plan = client.post(
            "/api/delivery/rd-collaboration-runs/run-1/plan",
            {
                "dependencies": list(kwargs["dependencies"]),
                "work_items": list(kwargs["work_items"]),
            },
        )
        fixture = SimpleNamespace(
            assessment_id="assessment-1",
            product_id="product-1",
            requirement_id="requirement-1",
            run_id="run-1",
            scope_version=1,
            strategy_snapshot_id="strategy-1",
            version_id="version-1",
            work_items=tuple(plan["work_items"]),
        )
        return SimpleNamespace(fixture=fixture, session=SimpleNamespace())

    monkeypatch.setattr(
        module,
        "create_v2_collaboration_setup",
        create_setup,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "create_simulated_runner_session",
        lambda *args, **kwargs: SimpleNamespace(),
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "simulated_runner_role_bindings",
        lambda *args, **kwargs: (
            {"actor_mode": "ai", "role_code": kwargs["role_code"], "status": "active"},
            {
                "actor_mode": "human",
                "candidate_human_user_ids": [kwargs["reviewer_user_id"]],
                "role_code": kwargs["role_code"],
                "status": "active",
            },
        ),
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "complete_ai_work_item_via_runner_protocol",
        lambda _client, _session, _run_id, work_item_id, _reviewer_client, _timeout: (
            SimpleNamespace(
                ai_task_id=f"{work_item_id}-task",
                review_id=f"{work_item_id}-review",
                step_detail=f"ai_task={work_item_id}-task",
            )
        ),
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "wait_for_ai_work_item",
        lambda *_args, **kwargs: {
            "id": kwargs["work_item_id"],
            "status": kwargs["status"],
            "version": 1,
        },
        raising=False,
    )

    def approve_dispatch(client, **_kwargs):
        decision = client.get("/api/delivery/decision-requests/decision-review")
        return client.post(
            "/api/delivery/decision-requests/decision-review/decide",
            {
                "idempotency_key": "trace",
                "input": {},
                "selected_option": "approve_dispatch",
                "version": decision["version"],
            },
        )

    monkeypatch.setattr(
        module,
        "approve_high_risk_dispatch",
        approve_dispatch,
        raising=False,
    )


@pytest.mark.parametrize("suite", ["full", "version-dashboard", "assistant-qa"])
def test_v2_regression_suites_never_call_legacy_task_entrypoints(
    monkeypatch,
    tmp_path: Path,
    suite: str,
) -> None:
    regression = _load_module(
        f"full_chain_regression_trace_under_test_{suite}",
        "scripts/full_chain_regression.py",
    )
    assistant = sys.modules["full_chain_regression_assistant_qa"]
    _install_v2_orchestration_fakes(monkeypatch, regression)
    _install_v2_orchestration_fakes(monkeypatch, assistant)
    monkeypatch.setattr(regression, "create_fixture_repository", lambda *_args: tmp_path)
    client = _RegressionEntrypointTraceClient()

    with pytest.raises(_TraceBoundaryReached):
        regression.run_regression_suite(
            client,
            suite=suite,
            task_execution_mode="deterministic",
            username="admin@example.com",
            password="secret",
        )

    forbidden = [
        (method, path)
        for method, path, _body in client.requests
        if (
            path.startswith("/api/requirements/")
            and (path.endswith("/approve") or path.endswith("/generate-task"))
        )
        or (method == "POST" and path == "/api/ai-tasks")
        or (
            method == "POST"
            and path.startswith("/api/ai-tasks/")
            and path.endswith("/start")
        )
    ]
    assert forbidden == []
    if suite in {"full", "version-dashboard"}:
        request_paths = [path for _method, path, _body in client.requests]
        assert request_paths.index(
            "/api/products/product-1/git-repositories"
        ) < request_paths.index(
            "/api/product-versions/version-1/branch-configs"
        ) < request_paths.index(
            "/api/product-versions/version-1/collaboration-runs"
        ) < request_paths.index(
            "/api/delivery/rd-collaboration-runs/run-1/plan"
        )
        run_request = next(
            body
            for method, path, body in client.requests
            if method == "POST"
            and path == "/api/product-versions/version-1/collaboration-runs"
        )
        assert run_request["repository_id"] == "repository-1"
    if suite == "version-dashboard":
        plan_requests = [
            (path, body)
            for method, path, body in client.requests
            if method == "POST"
            and path
            in {
                "/api/delivery/rd-collaboration-runs/run-1/plan",
                "/api/delivery/rd-collaboration-runs/run-1/replan",
            }
        ]
        assert [path for path, _body in plan_requests] == [
            "/api/delivery/rd-collaboration-runs/run-1/plan",
            "/api/delivery/rd-collaboration-runs/run-1/replan",
        ]
        assert [
            item["work_item_type"] for item in plan_requests[0][1]["work_items"]
        ] == ["product_detail_design", "technical_solution", "documentation"]
        assert all(
            item["owner_role_code"] != item["reviewer_role_code"]
            for item in plan_requests[0][1]["work_items"]
        )
        second_plan_item = plan_requests[1][1]["work_items"][0]
        assert second_plan_item["work_item_type"] == "code_review"
        assert second_plan_item["risk_level"] == "high"
        assert (
            second_plan_item["owner_role_code"]
            != second_plan_item["reviewer_role_code"]
        )
        assert second_plan_item["requirement_id"] == "requirement-1"
        assert second_plan_item["input_contract"] == {
            "gitlab_mr_snapshot_id": "snapshot-1"
        }
        binding_paths = [
            path
            for method, path, _body in client.requests
            if method == "POST" and "snapshot-binding" in path
        ]
        assert [path.rsplit("/", 1)[-1] for path in binding_paths] == [
            "claim",
            "submit",
            "review",
        ]
        assert any(
            method == "GET"
            and path.startswith("/api/ai-tasks/plan-2:review-")
            and path.endswith("-task/code-review-report")
            for method, path, _body in client.requests
        )


def test_full_suite_selects_real_knowledge_space_for_deposit_approval(
    monkeypatch,
    tmp_path: Path,
) -> None:
    regression = _load_module(
        "full_chain_regression_knowledge_space_under_test",
        "scripts/full_chain_regression.py",
    )
    _install_v2_orchestration_fakes(monkeypatch, regression)
    monkeypatch.setattr(regression, "create_fixture_repository", lambda *_args: tmp_path)
    client = _RegressionEntrypointTraceClient(trace_knowledge_deposit=True)

    with pytest.raises(_TraceBoundaryReached):
        regression.run_regression_suite(
            client,
            suite="full",
            task_execution_mode="deterministic",
            username="admin@example.com",
            password="secret",
        )

    spaces_index = next(
        index
        for index, (method, path, _body) in enumerate(client.requests)
        if method == "GET" and path == "/api/knowledge/spaces"
    )
    approval_index, approval_body = next(
        (index, body)
        for index, (method, path, body) in enumerate(client.requests)
        if method == "POST" and path == "/api/knowledge/deposits/deposit-1/approve"
    )
    assert spaces_index < approval_index
    assert approval_body["knowledge_space_id"] == "knowledge-space-1"
    assert approval_body["permission_roles"] == ["admin", "product_owner", "rd_owner"]
    assert approval_body["title"].startswith("全链路回归知识沉淀 ")


def test_full_code_inspection_contract_tracks_requirements_not_direct_tasks() -> None:
    regression = _load_module(
        "full_chain_regression_requirement_coverage_under_test",
        "scripts/full_chain_regression.py",
    )

    class RequirementCoverageClient:
        def __init__(self) -> None:
            self.requests: list[tuple[str, dict | None]] = []

        def get(self, path: str, query=None):
            self.requests.append((path, query))
            assert path == "/api/requirements"
            assert query == {
                "page": 1,
                "page_size": 100,
                "product_id": "product-1",
            }
            return {
                "items": [
                    {
                        "id": "requirement-1",
                        "source_object_type": "code_inspection_finding",
                    }
                ]
            }

    client = RequirementCoverageClient()
    requirement_ids = regression.validate_code_inspection_requirement_coverage(
        client,
        committer_governance={
            "covered_by_requirement_count": 1,
            "historical_covered_by_task_count": 0,
        },
        governance_summary={
            "covered_by_requirement_count": 1,
            "historical_covered_by_task_count": 0,
            "requirement_coverage_rate": 1.0,
        },
        product_id="product-1",
        report={
            "created_requirement_ids": ["requirement-1"],
            "created_task_ids": [],
            "id": "report-1",
        },
    )

    assert requirement_ids == {"requirement-1"}
    assert regression.validate_code_inspection_report_full_chain_requirement(
        {"requirement": {"id": "requirement-1"}},
        requirement_ids,
    ) == "requirement-1"
    regression.validate_full_team_dashboard_collaboration_task(
        {
            "latest_tasks": [{"id": "task-1"}],
            "summary": {"ai_tasks": 1},
        },
        "task-1",
    )
    assert client.requests == [
        (
            "/api/requirements",
            {"page": 1, "page_size": 100, "product_id": "product-1"},
        )
    ]


def test_assistant_draft_governance_uses_disabled_mock_plugin_jobs() -> None:
    drafts = _load_module(
        "full_chain_regression_assistant_drafts_under_test",
        "scripts/full_chain_regression_assistant_drafts.py",
    )

    class DraftApiError(RuntimeError):
        def __init__(self, status: int, body: str) -> None:
            super().__init__(body)
            self.body = body
            self.status = status

    class DraftGovernanceClient:
        def __init__(self) -> None:
            self.requests: list[tuple[str, str, dict | None]] = []
            self.draft_bodies: list[dict] = []

        def login(self, username: str, password: str):
            assert username == "admin@example.com"
            assert password == "secret"
            return {"user": {"username": username}}

        def get(self, path: str, query=None):
            self.requests.append(("GET", path, query))
            if path == "/api/system/scheduled-job-catalog":
                return {
                    "job_types": [
                        {
                            "allow_create": False,
                            "runnable": False,
                            "value": "dashboard_snapshot_refresh",
                        },
                        {
                            "allow_create": True,
                            "runnable": True,
                            "value": "plugin_action_invoke",
                        },
                    ]
                }
            if path == "/api/assistant/action-drafts/draft-1":
                return {
                    "governance": {
                        "audit": {
                            "event_types": ["assistant_action_draft.confirmed"],
                            "latest_event_type": "assistant_action_draft.confirmed",
                        }
                    }
                }
            if path == "/api/assistant/action-drafts":
                return {
                    "items": [
                        {
                            "id": "draft-1",
                            "impact_changed_field_count": 7,
                            "latest_audit_event_type": "assistant_action_draft.confirmed",
                            "permission_status": "passed",
                        }
                    ]
                }
            if path == "/api/audit/events":
                subject_id = query["subject_id"]
                event_types = (
                    [
                        "assistant_action_draft.created",
                        "assistant_action_draft.viewed",
                        "assistant_action_draft.modified",
                        "assistant_action_draft.updated",
                        "assistant_action_draft.confirmed",
                    ]
                    if subject_id == "draft-1"
                    else [
                        "assistant_action_draft.created",
                        "assistant_action_draft.failed",
                        "assistant_action_draft.retry_requested",
                        "assistant_action_draft.updated",
                        "assistant_action_draft.confirmed",
                    ]
                )
                return {"items": [{"event_type": event_type} for event_type in event_types]}
            if path == "/api/assistant/action-drafts/draft-2":
                return {
                    "governance": {"retries": {"can_retry": True}},
                    "metadata_json": {
                        "failure": {"code": "DRAFT_PRECHECK_FAILED"},
                    },
                    "status": "failed",
                }
            raise AssertionError(f"unexpected GET {path} {query}")

        def post(self, path: str, body=None, *, headers=None):
            assert headers is None
            self.requests.append(("POST", path, body))
            if path == "/api/system/plugins":
                if body["category"] not in {"general"}:
                    raise DraftApiError(
                        400,
                        f"Unsupported category: {body['category']}",
                    )
                return {"id": "plugin-1", "status": "active"}
            if path == "/api/system/plugin-connections":
                return {"id": "connection-1", "status": "active"}
            if path == "/api/system/plugin-actions":
                return {"id": "action-1", "status": "active"}
            if path == "/api/assistant/action-drafts":
                self.draft_bodies.append(body)
                if len(self.draft_bodies) == 1:
                    return {
                        "governance": {
                            "audit": {"latest_event_type": "assistant_action_draft.created"},
                            "diff": {"count": 7},
                            "impact": {
                                "changed_field_count": 7,
                                "resource_type": "scheduled_job",
                            },
                            "permissions": {"status": "passed"},
                        },
                        "id": "draft-1",
                        "payload": body["payload"],
                        "risk_level": "medium",
                        "status": "pending",
                    }
                return {
                    "governance": {"decision": {"status": "blocked"}},
                    "id": "draft-2",
                    "payload": body["payload"],
                    "status": "pending",
                }
            if path == "/api/assistant/action-drafts/draft-1/view":
                return {"metadata_json": {"view_count": 1}}
            if path == "/api/assistant/action-drafts/draft-1/modification":
                return {"metadata_json": {"user_modified": True}}
            if path == "/api/assistant/action-drafts/draft-1/confirm":
                return {
                    "draft": {"status": "confirmed"},
                    "run": {
                        "result": {"enabled": False},
                        "result_id": "scheduled-job-1",
                        "result_type": "scheduled_job",
                        "status": "succeeded",
                    },
                }
            if path == "/api/assistant/action-drafts/draft-2/confirm":
                if not any(
                    method == "PATCH" and request_path.endswith("/draft-2")
                    for method, request_path, _body in self.requests
                ):
                    raise DraftApiError(409, "DRAFT_PRECHECK_FAILED")
                return {
                    "draft": {"status": "confirmed"},
                    "run": {
                        "result": {"enabled": False},
                        "result_id": "scheduled-job-2",
                        "result_type": "scheduled_job",
                        "status": "succeeded",
                    },
                }
            if path == "/api/assistant/action-drafts/draft-2/retry":
                return {
                    "governance": {
                        "retries": {
                            "failure_count": 1,
                            "last_failure_code": "DRAFT_PRECHECK_FAILED",
                        }
                    },
                    "metadata_json": {
                        "failure_history": [{"code": "DRAFT_PRECHECK_FAILED"}],
                        "retry_count": 1,
                        "retry_reason": body["reason"],
                    },
                    "status": "pending",
                }
            raise AssertionError(f"unexpected POST {path} {body}")

        def request(self, method: str, path: str, *, body=None, **_kwargs):
            assert method == "PATCH"
            self.requests.append((method, path, body))
            if path == "/api/assistant/action-drafts/draft-1":
                return {
                    "metadata_json": {
                        "modified_fields": ["name"],
                        "user_modified": True,
                    }
                }
            if path == "/api/assistant/action-drafts/draft-2":
                return {"governance": {"decision": {"can_confirm": True}}}
            raise AssertionError(f"unexpected {method} {path} {body}")

    client = DraftGovernanceClient()
    results = drafts.validate_assistant_draft_governance(
        client,
        username="admin@example.com",
        password="secret",
    )

    assert results[-1].name == "assistant_draft_governance"
    assert len(client.draft_bodies) == 2
    for draft_body in client.draft_bodies:
        assert draft_body["payload"]["enabled"] is False
        assert draft_body["payload"]["execution_mode"] == "deterministic"
        assert draft_body["payload"]["job_type"] == "plugin_action_invoke"
        assert draft_body["payload"]["plugin_action_id"] == "action-1"
        assert draft_body["payload"]["plugin_connection_id"] == "connection-1"
    action_body = next(
        body
        for method, path, body in client.requests
        if method == "POST" and path == "/api/system/plugin-actions"
    )
    plugin_body = next(
        body
        for method, path, body in client.requests
        if method == "POST" and path == "/api/system/plugins"
    )
    assert plugin_body["category"] == "general"
    assert plugin_body["code"].startswith("assistant_draft_mock_")
    assert plugin_body["name"].startswith("Assistant draft mock fixture ")
    assert action_body["request_config"]["mock_response_json"] == {
        "records": [{"status": "ok"}]
    }
    assert not any(
        path.endswith("/run") or path.endswith("/invoke")
        for _method, path, _body in client.requests
    )


class _SimulatedProtocolClient:
    def __init__(
        self,
        *,
        code_review: bool = False,
        coding_without_quality_gate: bool = False,
        requires_quality_gate: bool = False,
    ) -> None:
        self.requests: list[tuple[str, str, dict | None, dict[str, str] | None]] = []
        self.code_review = code_review
        self.coding_without_quality_gate = coding_without_quality_gate
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
            waiting_review = self.runner_completed and (
                not self.requires_quality_gate or self.quality_gate_completed
            )
            return {
                "current_step": (
                    "waiting_review"
                    if waiting_review
                    else (
                        "quality_gate_running"
                        if self.runner_completed and self.requires_quality_gate
                        else "waiting_ai_executor"
                    )
                ),
                "id": "task-1",
                "pending_review": {"id": "review-1", "version": 1},
                "status": "waiting_review" if waiting_review else "running",
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
                        else {
                            "rd_work_item_attempt_id": "attempt-1",
                            **(
                                {"task": {"task_type": "code_review"}}
                                if self.code_review
                                else {}
                            ),
                        }
                    ),
                    "status": "claimed",
                    "task_kind": (
                        "quality_gate"
                        if self.runner_completed
                        else (
                            "coding"
                            if self.requires_quality_gate
                            or self.coding_without_quality_gate
                            else "product_detail_design"
                        )
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
                "result_json": (
                    {
                        "findings": [],
                        "risk_level": "low",
                        "summary": "deterministic v2 regression output",
                    }
                    if self.code_review
                    else {"summary": "deterministic v2 regression output"}
                ),
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


def simulate_protocol_fixture(
    *,
    code_review: bool = False,
    coding_without_quality_gate: bool = False,
    requires_quality_gate: bool = False,
):
    protocol = _load_module(
        "full_chain_regression_rd_runner_protocol_under_test",
        "scripts/full_chain_regression_rd_runner_protocol.py",
    )
    client = _SimulatedProtocolClient(
        code_review=code_review,
        coding_without_quality_gate=coding_without_quality_gate,
        requires_quality_gate=requires_quality_gate,
    )
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


def test_coding_runner_task_skips_unrequested_quality_gate() -> None:
    client, _reviewer_client, result = simulate_protocol_fixture(
        coding_without_quality_gate=True,
    )

    assert result.work_item["status"] == "completed"
    assert result.runner_task_ids == ("runner-task-1",)
    assert not any(
        method == "GET" and path == "/api/system/ai-executor-tasks"
        for method, path, _body, _headers in client.requests
    )


def test_code_review_runner_submits_normalized_report_result() -> None:
    client, _reviewer_client, result = simulate_protocol_fixture(
        code_review=True,
        coding_without_quality_gate=True,
    )

    completion = next(
        body
        for method, path, body, _headers in client.requests
        if method == "POST" and path.endswith("/runner-task-1/complete")
    )
    assert completion["result_json"] == {
        "findings": [],
        "risk_level": "low",
        "summary": "deterministic v2 regression output",
    }
    assert result.runner_result["result_json"] == completion["result_json"]


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
