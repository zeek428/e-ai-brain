from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.store import MemoryStore
from app.main import app

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def _github_store() -> MemoryStore:
    store = MemoryStore()
    store.integration_plugins = {
        "plugin_github": {
            "id": "plugin_github",
            "code": "github",
            "status": "active",
        }
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
    return store


def test_github_webhook_is_verified_deduplicated_and_redacted(monkeypatch):
    from app.services.external_event_inbox import receive_external_event

    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "github-webhook-secret")
    store = _github_store()
    body = json.dumps(
        {
            "action": "completed",
            "authorization": "Bearer should-not-persist",
            "repository": {"clone_url": "https://github.com/acme/project.git"},
            "workflow_run": {
                "conclusion": "success",
                "id": 42,
                "token": "should-not-persist",
            },
        }
    ).encode()
    signature = "sha256=" + hmac.new(
        b"github-webhook-secret",
        body,
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "x-github-delivery": "delivery-001",
        "x-github-event": "workflow_run",
        "x-hub-signature-256": signature,
    }

    first = receive_external_event(
        store,
        body=body,
        connection_id="connection_github",
        headers=headers,
        provider="github",
    )
    second = receive_external_event(
        store,
        body=body,
        connection_id="connection_github",
        headers=headers,
        provider="github",
    )

    assert first["id"] == second["id"]
    assert second["duplicate"] is True
    assert first["signature_status"] == "verified"
    serialized = json.dumps(first["payload"], ensure_ascii=False)
    assert "should-not-persist" not in serialized
    assert first["payload_hash"] == hashlib.sha256(body).hexdigest()


def test_duplicate_webhook_still_requires_a_valid_signature(monkeypatch):
    from app.services.external_event_inbox import receive_external_event

    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "github-webhook-secret")
    store = _github_store()
    body = b'{"action":"completed"}'
    valid_signature = "sha256=" + hmac.new(
        b"github-webhook-secret",
        body,
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "x-github-delivery": "delivery-duplicate-auth",
        "x-github-event": "workflow_run",
        "x-hub-signature-256": valid_signature,
    }
    receive_external_event(
        store,
        body=body,
        connection_id="connection_github",
        headers=headers,
        provider="github",
    )

    with pytest.raises(HTTPException) as exc_info:
        receive_external_event(
            store,
            body=body,
            connection_id="connection_github",
            headers={**headers, "x-hub-signature-256": "sha256=invalid"},
            provider="github",
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "WEBHOOK_SIGNATURE_INVALID"
    assert len(store.external_event_inbox) == 1


def test_duplicate_delivery_id_rejects_a_different_payload(monkeypatch):
    from app.services.external_event_inbox import receive_external_event

    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "github-webhook-secret")
    store = _github_store()
    first_body = b'{"action":"completed"}'
    changed_body = b'{"action":"requested"}'

    def signed_headers(body: bytes) -> dict[str, str]:
        return {
            "x-github-delivery": "delivery-payload-conflict",
            "x-github-event": "workflow_run",
            "x-hub-signature-256": "sha256="
            + hmac.new(
                b"github-webhook-secret",
                body,
                hashlib.sha256,
            ).hexdigest(),
        }

    receive_external_event(
        store,
        body=first_body,
        connection_id="connection_github",
        headers=signed_headers(first_body),
        provider="github",
    )

    with pytest.raises(HTTPException) as exc_info:
        receive_external_event(
            store,
            body=changed_body,
            connection_id="connection_github",
            headers=signed_headers(changed_body),
            provider="github",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "WEBHOOK_DELIVERY_CONFLICT"
    assert len(store.external_event_inbox) == 1


def test_invalid_webhook_signature_is_rejected_without_inbox_record(monkeypatch):
    from app.services.external_event_inbox import receive_external_event

    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "github-webhook-secret")
    store = _github_store()

    with pytest.raises(HTTPException) as exc_info:
        receive_external_event(
            store,
            body=b'{"action":"completed"}',
            connection_id="connection_github",
            headers={
                "x-github-delivery": "delivery-invalid",
                "x-github-event": "workflow_run",
                "x-hub-signature-256": "sha256=invalid",
            },
            provider="github",
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "WEBHOOK_SIGNATURE_INVALID"
    assert store.external_event_inbox == {}


def test_gitlab_token_signature_uses_constant_time_verification(monkeypatch):
    from app.services.external_event_signatures import verify_external_event_signature

    monkeypatch.setenv("GITLAB_WEBHOOK_SECRET", "gitlab-webhook-secret")

    assert verify_external_event_signature(
        provider="gitlab",
        secret_ref="env:GITLAB_WEBHOOK_SECRET",
        body=b"{}",
        headers={"x-gitlab-token": "gitlab-webhook-secret"},
    ) == "verified"
    with pytest.raises(HTTPException):
        verify_external_event_signature(
            provider="gitlab",
            secret_ref="env:GITLAB_WEBHOOK_SECRET",
            body=b"{}",
            headers={"x-gitlab-token": "wrong"},
        )


def test_observability_connection_uses_selected_event_provider(monkeypatch):
    from app.services.external_event_inbox import receive_external_event

    monkeypatch.setenv("OBSERVABILITY_WEBHOOK_SECRET", "observability-webhook-secret")
    store = MemoryStore()
    store.integration_plugins = {
        "plugin_observability": {
            "id": "plugin_observability",
            "code": "observability",
            "status": "active",
        }
    }
    store.plugin_connections = {
        "connection_observability": {
            "id": "connection_observability",
            "plugin_id": "plugin_observability",
            "status": "active",
            "auth_config": {
                "webhook_secret_ref": "env:OBSERVABILITY_WEBHOOK_SECRET",
            },
            "request_config": {
                "event_provider": "sentry",
                "environment": "prod",
                "product_id": "product_001",
            },
        }
    }
    body = b'{"event_id":"sentry-event-001","message":"boom"}'
    signature = "sha256=" + hmac.new(
        b"observability-webhook-secret",
        body,
        hashlib.sha256,
    ).hexdigest()

    event = receive_external_event(
        store,
        body=body,
        connection_id="connection_observability",
        headers={
            "x-ai-brain-delivery": "delivery-observability-001",
            "x-ai-brain-event": "error",
            "x-ai-brain-signature": signature,
        },
        provider="sentry",
    )

    assert event["provider"] == "sentry"
    assert event["payload"]["_context"] == {
        "connection_id": "connection_observability",
        "environment": "prod",
        "product_id": "product_001",
        "version_id": None,
    }


def test_external_event_webhook_route_accepts_verified_delivery(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "github-webhook-secret")
    app.state.store.reset()
    configured = _github_store()
    app.state.store.integration_plugins = configured.integration_plugins
    app.state.store.plugin_connections = configured.plugin_connections
    body = b'{"repository":{"full_name":"acme/project"}}'
    signature = "sha256=" + hmac.new(
        b"github-webhook-secret",
        body,
        hashlib.sha256,
    ).hexdigest()

    response = client.post(
        "/api/integrations/webhooks/github/connection_github",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Delivery": "delivery-route-001",
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": signature,
        },
    )

    assert response.status_code == 202, response.text
    assert response.json()["data"]["status"] == "pending"
    assert response.json()["data"]["duplicate"] is False
    assert "payload" not in response.json()["data"]


def test_external_event_admin_list_is_redacted_and_dead_letter_can_be_retried():
    app.state.store.reset()
    app.state.store.external_event_inbox["external_event_001"] = {
        "id": "external_event_001",
        "provider": "github",
        "event_type": "workflow_run",
        "delivery_id": "delivery-dead-001",
        "signature_status": "verified",
        "payload_hash": "sha256-value",
        "payload": {
            "token": "must-never-be-returned",
            "repository": {"full_name": "acme/project"},
            "_context": {
                "connection_id": "connection_github",
                "environment": "prod",
                "product_id": "product_001",
                "version_id": "version_001",
            },
        },
        "status": "dead_letter",
        "attempt_count": 5,
        "lease_owner": None,
        "lease_until": None,
        "error_message": "RuntimeError",
        "received_at": "2026-07-11T02:00:00+00:00",
        "processed_at": "2026-07-11T02:01:00+00:00",
        "updated_at": "2026-07-11T02:01:00+00:00",
    }
    headers = auth_headers()

    listed = client.get(
        "/api/system/external-events?status=dead_letter",
        headers=headers,
    )

    assert listed.status_code == 200
    item = listed.json()["data"]["items"][0]
    assert item["context"]["product_id"] == "product_001"
    assert item["context"]["connection_id"] == "connection_github"
    assert "payload" not in item
    assert "must-never-be-returned" not in listed.text

    health = client.get("/api/system/health", headers=headers)
    assert health.status_code == 200
    governance = health.json()["data"]["operations"]["execution_governance"]
    assert governance["external_event_inbox"]["dead_letter_count"] == 1
    assert governance["external_event_inbox"]["recent_dead_letters"][0]["id"] == (
        "external_event_001"
    )

    retried = client.post(
        "/api/system/external-events/external_event_001/retry",
        json={"reason": "连接已恢复"},
        headers=headers,
    )

    assert retried.status_code == 200
    assert retried.json()["data"]["status"] == "pending"
    assert retried.json()["data"]["attempt_count"] == 0
    assert app.state.store.external_event_inbox["external_event_001"]["error_message"] is None
    assert app.state.store.audit_events[-1]["event_type"] == "external_event.retry_requested"
