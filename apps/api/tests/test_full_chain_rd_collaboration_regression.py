from __future__ import annotations

import importlib.util
import sys
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
