from __future__ import annotations

import importlib.util
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path


def _load_module(name: str, relative_path: str):
    script_path = Path(__file__).resolve().parents[3] / relative_path
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
