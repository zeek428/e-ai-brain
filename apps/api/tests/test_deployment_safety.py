from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.services.deployment_preflight import (
    deployment_release_identity_checks,
    validate_deployment_window,
)

client = TestClient(app)


def _auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def _release_context(headers: dict[str, str]) -> dict[str, str]:
    product = client.post(
        "/api/products",
        json={"code": "strict-release", "name": "严格发布产品"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "版本 1"},
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "content": "完成严格生产发布。",
            "product_id": product["id"],
            "title": "严格发布需求",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    app.state.store.requirements[requirement["id"]]["status"] = "ready_for_release"
    return {
        "product_id": product["id"],
        "requirement_id": requirement["id"],
        "version_id": version["id"],
    }


def test_strict_window_requires_a_complete_active_window() -> None:
    now = datetime.now(UTC)
    with pytest.raises(HTTPException) as exc_info:
        validate_deployment_window(
            {
                "deploy_window_end": None,
                "deploy_window_start": None,
                "window_enforcement": "strict",
            },
            now=now,
        )

    assert exc_info.value.detail["code"] == "DEPLOYMENT_WINDOW_REQUIRED"

    evidence = validate_deployment_window(
        {
            "deploy_window_end": (now + timedelta(minutes=10)).isoformat(),
            "deploy_window_start": (now - timedelta(minutes=10)).isoformat(),
            "window_enforcement": "strict",
        },
        now=now,
    )
    assert evidence["within_window"] is True


def test_strict_production_release_identity_requires_version_commit_and_digest() -> None:
    checks = deployment_release_identity_checks(
        {
            "artifact_digest": None,
            "artifact_version": None,
            "commit_sha": "not-a-sha",
            "environment": "prod",
            "window_enforcement": "strict",
        }
    )

    assert {item["code"] for item in checks if not item["passed"]} == {
        "artifact_digest_valid",
        "artifact_version_present",
        "commit_sha_valid",
    }

    passed = deployment_release_identity_checks(
        {
            "artifact_digest": "sha256:" + "a" * 64,
            "artifact_version": "2026.07.11-1",
            "commit_sha": "b" * 40,
            "environment": "prod",
            "window_enforcement": "strict",
        }
    )
    assert all(item["passed"] for item in passed)


def test_new_production_scheme_defaults_to_strict_and_blocks_incomplete_artifact() -> None:
    app.state.store.reset()
    headers = _auth_headers()
    context = _release_context(headers)
    scheme_response = client.post(
        "/api/devops/deployment-schemes",
        json={
            "code": "strict-manual",
            "deployment_method": "manual",
            "environment": "prod",
            "name": "严格人工发布",
            "product_id": context["product_id"],
        },
        headers=headers,
    )
    assert scheme_response.status_code == 200, scheme_response.text
    scheme = scheme_response.json()["data"]
    assert scheme["window_enforcement"] == "strict"
    now = datetime.now(UTC)
    deployment_response = client.post(
        "/api/devops/deployments",
        json={
            "deploy_window_end": (now + timedelta(minutes=10)).isoformat(),
            "deploy_window_start": (now - timedelta(minutes=10)).isoformat(),
            "deployment_scheme_id": scheme["id"],
            "environment": "prod",
            "product_id": context["product_id"],
            "requirement_ids": [context["requirement_id"]],
            "rollback_plan": "回滚到上一稳定制品",
            "title": "严格生产发布",
            "version_id": context["version_id"],
        },
        headers=headers,
    )
    assert deployment_response.status_code == 200, deployment_response.text
    deployment = deployment_response.json()["data"]
    assert deployment["gate_summary"]["quality_gate_status"] == "blocked"

    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )
    assert started.status_code == 409
    assert started.json()["detail"]["code"] == "DEPLOYMENT_RELEASE_IDENTITY_INVALID"


def test_strict_manual_release_persists_passing_pre_deploy_gate() -> None:
    app.state.store.reset()
    headers = _auth_headers()
    context = _release_context(headers)
    scheme = client.post(
        "/api/devops/deployment-schemes",
        json={
            "code": "strict-complete",
            "deployment_method": "manual",
            "environment": "prod",
            "name": "完整严格发布",
            "product_id": context["product_id"],
        },
        headers=headers,
    ).json()["data"]
    now = datetime.now(UTC)
    deployment = client.post(
        "/api/devops/deployments",
        json={
            "artifact_digest": "sha256:" + "a" * 64,
            "artifact_version": "2026.07.11-1",
            "commit_sha": "b" * 40,
            "deploy_window_end": (now + timedelta(minutes=10)).isoformat(),
            "deploy_window_start": (now - timedelta(minutes=10)).isoformat(),
            "deployment_scheme_id": scheme["id"],
            "environment": "prod",
            "product_id": context["product_id"],
            "requirement_ids": [context["requirement_id"]],
            "rollback_plan": "回滚到上一稳定制品",
            "title": "完整严格发布",
            "version_id": context["version_id"],
        },
        headers=headers,
    ).json()["data"]

    assert deployment["artifact_digest"].startswith("sha256:")
    detail = client.get(
        f"/api/devops/deployments/{deployment['id']}", headers=headers
    ).json()["data"]
    assert detail["quality_gate"]["status"] == "passed"
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )
    assert started.status_code == 200, started.text
