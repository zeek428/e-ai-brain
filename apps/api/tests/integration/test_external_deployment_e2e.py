"""Optional isolated deployment-provider protocol regression.

Run only in the isolated compose environment described in
infra/e2e/deployment-external/README.md. It never targets production systems.
"""

from __future__ import annotations

import os
import time

import httpx
import pytest

pytestmark = pytest.mark.deployment_protocol_regression

BASE_URL = os.getenv("AI_BRAIN_E2E_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("AI_BRAIN_E2E_BEARER_TOKEN", "")


def _deployment_ids() -> dict[str, str]:
    return {
        method: value
        for method, value in {
            "ssh": os.getenv("AI_BRAIN_E2E_SSH_DEPLOYMENT_ID", ""),
            "docker": os.getenv("AI_BRAIN_E2E_DOCKER_DEPLOYMENT_ID", ""),
            "jenkins": os.getenv("AI_BRAIN_E2E_JENKINS_DEPLOYMENT_ID", ""),
        }.items()
        if value
    }


def _wait_for_deployment_status(
    client: httpx.Client,
    *,
    deployment_id: str,
    expected_status: str,
    timeout_seconds: int = 180,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    last_payload: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/api/devops/deployments/{deployment_id}")
        assert response.status_code == 200, response.text
        last_payload = response.json()["data"]
        if last_payload.get("status") == expected_status:
            return last_payload
        runs = last_payload.get("runs") or []
        if last_payload.get("deployment_method") == "jenkins" and runs:
            run_id = runs[0].get("id")
            if run_id:
                sync = client.post(f"/api/devops/deployments/{deployment_id}/runs/{run_id}/sync")
                assert sync.status_code == 200, sync.text
        time.sleep(2)
    raise AssertionError(
        f"Deployment {deployment_id} did not reach {expected_status}: {last_payload}"
    )


@pytest.fixture(scope="module")
def external_client() -> httpx.Client:
    if not BASE_URL or not TOKEN or len(_deployment_ids()) != 3:
        pytest.skip("Isolated deployment protocol regression environment is not configured")
    with httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=20,
    ) as client:
        yield client


@pytest.mark.parametrize("method", ["ssh", "docker", "jenkins"])
def test_external_deployment_probe_start_and_rollback(
    external_client: httpx.Client,
    method: str,
) -> None:
    deployment_id = _deployment_ids()[method]
    probe = external_client.post(f"/api/devops/deployments/{deployment_id}/connectivity-probe")
    assert probe.status_code == 200, probe.text

    deadline = time.monotonic() + 120
    while not probe.json()["data"].get("ready") and time.monotonic() < deadline:
        time.sleep(2)
        probe = external_client.get(f"/api/devops/deployments/{deployment_id}/connectivity-probe")
        assert probe.status_code == 200, probe.text
    assert probe.json()["data"].get("ready") is True

    started = external_client.post(f"/api/devops/deployments/{deployment_id}/start", json={})
    assert started.status_code == 200, started.text
    deployment = started.json()["data"]
    assert deployment["runs"]

    completed = _wait_for_deployment_status(
        external_client,
        deployment_id=deployment_id,
        expected_status="succeeded",
    )
    run_id = completed["runs"][0]["id"]
    logs = external_client.get(f"/api/devops/deployments/{deployment_id}/runs/{run_id}/logs")
    assert logs.status_code == 200, logs.text
    assert logs.json()["data"]["items"]

    rollback = external_client.post(
        f"/api/devops/deployments/{deployment_id}/rollback",
        json={"reason": "external e2e rollback"},
    )
    assert rollback.status_code == 200, rollback.text
    _wait_for_deployment_status(
        external_client,
        deployment_id=deployment_id,
        expected_status="rolled_back",
    )


def test_external_deployment_timeout_is_reported_when_configured(
    external_client: httpx.Client,
) -> None:
    deployment_id = os.getenv("AI_BRAIN_E2E_TIMEOUT_DEPLOYMENT_ID", "")
    if not deployment_id:
        pytest.skip("Optional timeout deployment is not configured")
    probe = external_client.post(f"/api/devops/deployments/{deployment_id}/connectivity-probe")
    assert probe.status_code == 200, probe.text
    deadline = time.monotonic() + 120
    while not probe.json()["data"].get("ready") and time.monotonic() < deadline:
        time.sleep(2)
        probe = external_client.get(f"/api/devops/deployments/{deployment_id}/connectivity-probe")
        assert probe.status_code == 200, probe.text
    assert probe.json()["data"].get("ready") is True

    started = external_client.post(f"/api/devops/deployments/{deployment_id}/start", json={})
    assert started.status_code == 200, started.text
    timed_out = _wait_for_deployment_status(
        external_client,
        deployment_id=deployment_id,
        expected_status="failed",
        timeout_seconds=120,
    )
    assert "timeout" in str(timed_out.get("failure_reason") or "").lower()
