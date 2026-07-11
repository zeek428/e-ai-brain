from __future__ import annotations

import hashlib
import hmac
import json

from app.core.store import MemoryStore


def _store() -> MemoryStore:
    store = MemoryStore()
    store.products = {
        "product_001": {"id": "product_001", "name": "CI 产品", "status": "active"}
    }
    store.product_git_repositories = {
        "repo_001": {
            "id": "repo_001",
            "product_id": "product_001",
            "git_provider": "github",
            "remote_url": "https://github.com/acme/project.git",
            "project_path": "acme/project",
            "status": "active",
        }
    }
    store.integration_plugins = {
        "plugin_github": {"id": "plugin_github", "code": "github", "status": "active"}
    }
    store.plugin_connections = {
        "connection_github": {
            "id": "connection_github",
            "plugin_id": "plugin_github",
            "status": "active",
            "auth_config": {"webhook_secret_ref": "env:GITHUB_WEBHOOK_SECRET"},
            "request_config": {},
        }
    }
    store.quality_gate_runs = {
        "quality_gate_run_001": {
            "id": "quality_gate_run_001",
            "product_id": "product_001",
            "status": "running",
            "phase": "pre_merge",
            "subject_type": "ai_task",
            "subject_id": "task_001",
            "policy_snapshot": {},
            "risk_level": "low",
            "independent_evidence_count": 0,
        }
    }
    store.quality_gate_checks = {
        "quality_gate_check_ci": {
            "id": "quality_gate_check_ci",
            "quality_gate_run_id": "quality_gate_run_001",
            "check_type": "ci_status",
            "source": "ci_webhook",
            "status": "pending",
            "required": True,
            "independent": True,
            "details": {},
        }
    }
    return store


def _headers(body: bytes, delivery_id: str) -> dict[str, str]:
    return {
        "x-github-delivery": delivery_id,
        "x-github-event": "workflow_run",
        "x-hub-signature-256": "sha256="
        + hmac.new(b"github-webhook-secret", body, hashlib.sha256).hexdigest(),
    }


def test_github_ci_event_projects_independent_quality_gate_evidence(monkeypatch):
    from app.services.external_event_inbox import (
        process_external_event_inbox_events,
        receive_external_event,
    )

    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "github-webhook-secret")
    store = _store()
    body = json.dumps(
        {
            "repository": {"clone_url": "https://github.com/acme/project.git"},
            "workflow_run": {
                "conclusion": "success",
                "head_sha": "abc123",
                "html_url": "https://github.com/acme/project/actions/runs/42",
                "id": 42,
            },
            "quality_gate_run_id": "quality_gate_run_001",
        }
    ).encode()
    event = receive_external_event(
        store,
        body=body,
        connection_id="connection_github",
        headers=_headers(body, "delivery-ci-001"),
        provider="github",
    )

    assert process_external_event_inbox_events(
        store,
        worker_id="event-worker",
    ) == 1
    assert store.external_event_inbox[event["id"]]["status"] == "completed"
    check = store.quality_gate_checks["quality_gate_check_ci"]
    assert check["status"] == "passed"
    assert check["source"] == "ci_webhook"
    assert check["evidence_ref"].endswith("delivery-ci-001")
    assert check["details"]["commit_sha"] == "abc123"


def test_unmapped_repository_event_is_ignored_with_diagnostic(monkeypatch):
    from app.services.external_event_inbox import (
        process_external_event_inbox_events,
        receive_external_event,
    )

    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "github-webhook-secret")
    store = _store()
    body = json.dumps(
        {
            "repository": {"clone_url": "https://github.com/other/unknown.git"},
            "workflow_run": {"conclusion": "failure", "id": 99},
        }
    ).encode()
    event = receive_external_event(
        store,
        body=body,
        connection_id="connection_github",
        headers=_headers(body, "delivery-unmapped"),
        provider="github",
    )

    assert process_external_event_inbox_events(
        store,
        worker_id="event-worker",
    ) == 1
    persisted = store.external_event_inbox[event["id"]]
    assert persisted["status"] == "ignored"
    assert persisted["error_message"] == "PRODUCT_REPOSITORY_NOT_MAPPED"


def test_jenkins_callback_converges_deployment_and_requirement(monkeypatch):
    from app.services.external_event_inbox import (
        process_external_event_inbox_events,
        receive_external_event,
    )

    monkeypatch.setenv("JENKINS_WEBHOOK_SECRET", "jenkins-webhook-secret")
    store = MemoryStore()
    store.integration_plugins = {
        "plugin_jenkins": {
            "id": "plugin_jenkins",
            "code": "jenkins",
            "status": "active",
        }
    }
    store.plugin_connections = {
        "connection_jenkins": {
            "id": "connection_jenkins",
            "plugin_id": "plugin_jenkins",
            "status": "active",
            "auth_config": {"webhook_secret_ref": "env:JENKINS_WEBHOOK_SECRET"},
            "request_config": {"product_id": "product_001"},
        }
    }
    store.deployment_requests = {
        "deployment_001": {
            "id": "deployment_001",
            "product_id": "product_001",
            "version_id": "version_001",
            "requirement_ids": ["requirement_001"],
            "environment": "prod",
            "executor_channel": "integration",
            "deployment_method": "jenkins",
            "status": "deploying",
            "scheme_snapshot": {},
        }
    }
    store.deployment_runs = {
        "deployment_run_001": {
            "id": "deployment_run_001",
            "deployment_request_id": "deployment_001",
            "operation": "deploy",
            "status": "running",
        }
    }
    store.requirements = {
        "requirement_001": {
            "id": "requirement_001",
            "product_id": "product_001",
            "version_id": "version_001",
            "title": "发布需求",
            "content": "发布",
            "status": "deploying",
            "created_by": "user_admin",
        }
    }
    body = json.dumps(
        {
            "deployment_request_id": "deployment_001",
            "deployment_run_id": "deployment_run_001",
            "status": "SUCCESS",
            "build_url": "https://jenkins.example.com/job/deploy/42/",
        }
    ).encode()
    event = receive_external_event(
        store,
        body=body,
        connection_id="connection_jenkins",
        headers={
            "x-ai-brain-delivery": "jenkins-callback-001",
            "x-ai-brain-event": "build_completed",
            "x-ai-brain-signature": "sha256="
            + hmac.new(
                b"jenkins-webhook-secret",
                body,
                hashlib.sha256,
            ).hexdigest(),
        },
        provider="jenkins",
    )

    assert process_external_event_inbox_events(
        store,
        worker_id="event-worker",
    ) == 1
    assert store.external_event_inbox[event["id"]]["status"] == "completed"
    assert store.deployment_requests["deployment_001"]["status"] == "succeeded"
    assert store.deployment_runs["deployment_run_001"]["status"] == "success"
    assert store.requirements["requirement_001"]["status"] == "released"
