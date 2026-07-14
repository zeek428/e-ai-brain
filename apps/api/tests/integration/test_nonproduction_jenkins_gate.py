"""Mandatory release-candidate acceptance against an existing non-production Jenkins job.

The test creates only an AI Brain deployment record. The Jenkins server, acceptance
job, credentials, agents and deployment target are pre-provisioned and must be
non-mutating. Missing CI configuration is a gate failure, never a skipped check.
"""

from __future__ import annotations

import os
import time

import httpx
import pytest

pytestmark = pytest.mark.nonproduction_jenkins_gate


def _required_environment() -> dict[str, str]:
    names = {
        "base_url": "AI_BRAIN_JENKINS_GATE_BASE_URL",
        "bearer_token": "AI_BRAIN_JENKINS_GATE_BEARER_TOKEN",
        "environment": "AI_BRAIN_JENKINS_GATE_ENVIRONMENT",
        "expected_job_name": "AI_BRAIN_JENKINS_GATE_JOB_NAME",
        "product_id": "AI_BRAIN_JENKINS_GATE_PRODUCT_ID",
        "scheme_id": "AI_BRAIN_JENKINS_GATE_SCHEME_ID",
        "version_id": "AI_BRAIN_JENKINS_GATE_VERSION_ID",
    }
    values = {key: os.getenv(name, "").strip() for key, name in names.items()}
    missing = [name for key, name in names.items() if not values[key]]
    if missing:
        pytest.fail(
            "Non-production Jenkins acceptance gate is not configured: " + ", ".join(missing),
            pytrace=False,
        )
    values["base_url"] = values["base_url"].rstrip("/")
    return values


def _wait_for_completion(
    client: httpx.Client,
    *,
    deployment_id: str,
    timeout_seconds: int = 300,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/api/devops/deployments/{deployment_id}")
        assert response.status_code == 200, response.text
        latest = response.json()["data"]
        if latest.get("status") in {"failed", "succeeded"}:
            return latest
        runs = latest.get("runs") or []
        if runs and runs[0].get("id"):
            sync = client.post(f"/api/devops/deployments/{deployment_id}/runs/{runs[0]['id']}/sync")
            assert sync.status_code == 200, sync.text
        time.sleep(2)
    raise AssertionError(f"Jenkins acceptance deployment did not complete: {latest}")


def test_nonproduction_jenkins_acceptance_job_is_triggered_and_returns_evidence() -> None:
    config = _required_environment()
    run_label = os.getenv("GITHUB_RUN_ID") or str(int(time.time()))
    with httpx.Client(
        base_url=config["base_url"],
        headers={"Authorization": f"Bearer {config['bearer_token']}"},
        timeout=30,
    ) as client:
        created = client.post(
            "/api/devops/deployments",
            json={
                "deployment_scheme_id": config["scheme_id"],
                "environment": config["environment"],
                "product_id": config["product_id"],
                "requirement_ids": [],
                "risk_level": "low",
                "title": f"CI 非生产 Jenkins 验收 {run_label}",
                "version_id": config["version_id"],
            },
        )
        assert created.status_code == 200, created.text
        deployment = created.json()["data"]

        probe = client.post(f"/api/devops/deployments/{deployment['id']}/connectivity-probe")
        assert probe.status_code == 200, probe.text
        assert probe.json()["data"]["kind"] == "jenkins"
        assert probe.json()["data"]["ready"] is True

        started = client.post(f"/api/devops/deployments/{deployment['id']}/start", json={})
        assert started.status_code == 200, started.text
        completed = _wait_for_completion(client, deployment_id=deployment["id"])
        assert completed["status"] == "succeeded", completed
        run = completed["runs"][0]
        assert run["external_job_name"] == config["expected_job_name"]
        logs = client.get(f"/api/devops/deployments/{deployment['id']}/runs/{run['id']}/logs")
        assert logs.status_code == 200, logs.text
        assert logs.json()["data"]["items"]
