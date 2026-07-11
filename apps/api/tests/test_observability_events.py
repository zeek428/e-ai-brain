from __future__ import annotations

import hashlib
import hmac
import json

from app.core.store import MemoryStore

PROVIDERS = ("prometheus", "opentelemetry", "sentry", "user_behavior")


def _store() -> MemoryStore:
    store = MemoryStore()
    store.products = {
        "product_001": {"id": "product_001", "name": "观测产品", "status": "active"}
    }
    store.product_versions = {
        "version_001": {
            "id": "version_001",
            "product_id": "product_001",
            "name": "版本 1",
            "status": "active",
        }
    }
    for provider in PROVIDERS:
        plugin_id = f"plugin_{provider}"
        connection_id = f"connection_{provider}"
        store.integration_plugins[plugin_id] = {
            "id": plugin_id,
            "code": provider,
            "status": "active",
        }
        store.plugin_connections[connection_id] = {
            "id": connection_id,
            "plugin_id": plugin_id,
            "status": "active",
            "auth_config": {"webhook_secret_ref": "env:OBSERVABILITY_WEBHOOK_SECRET"},
            "request_config": {
                "environment": "prod",
                "product_id": "product_001",
                "version_id": "version_001",
            },
        }
    return store


def _receive(store: MemoryStore, provider: str, payload: dict, delivery: str):
    from app.services.external_event_inbox import receive_external_event

    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(
        b"observability-webhook-secret",
        body,
        hashlib.sha256,
    ).hexdigest()
    return receive_external_event(
        store,
        body=body,
        connection_id=f"connection_{provider}",
        headers={
            "x-ai-brain-delivery": delivery,
            "x-ai-brain-event": "metric_batch",
            "x-ai-brain-signature": signature,
        },
        provider=provider,
    )


def test_prometheus_and_opentelemetry_events_create_operational_metrics(monkeypatch):
    from app.services.external_event_inbox import process_external_event_inbox_events

    monkeypatch.setenv("OBSERVABILITY_WEBHOOK_SECRET", "observability-webhook-secret")
    store = _store()
    common = {
        "window_start": "2026-07-11T00:00:00Z",
        "window_end": "2026-07-11T00:05:00Z",
        "request_count": 100,
        "error_count": 2,
        "p95_latency_ms": 85.5,
    }
    _receive(store, "prometheus", common, "prometheus-001")
    _receive(store, "opentelemetry", {**common, "request_count": 120}, "otel-001")

    assert process_external_event_inbox_events(
        store,
        worker_id="event-worker",
    ) == 2
    metrics = list(store.online_log_metrics.values())
    assert len(metrics) == 2
    assert {item["source_channel"] for item in metrics} == {
        "opentelemetry_webhook",
        "prometheus_webhook",
    }
    assert all(item["product_id"] == "product_001" for item in metrics)


def test_sentry_event_creates_product_scoped_bug(monkeypatch):
    from app.services.external_event_inbox import process_external_event_inbox_events

    monkeypatch.setenv("OBSERVABILITY_WEBHOOK_SECRET", "observability-webhook-secret")
    store = _store()
    _receive(
        store,
        "sentry",
        {
            "issue": {
                "culprit": "api.checkout",
                "level": "error",
                "title": "Checkout failed",
            }
        },
        "sentry-001",
    )

    assert process_external_event_inbox_events(
        store,
        worker_id="event-worker",
    ) == 1
    bug = next(iter(store.bugs.values()))
    assert bug["product_id"] == "product_001"
    assert bug["version_id"] == "version_001"
    assert bug["source"] == "sentry"
    assert bug["title"] == "Sentry：Checkout failed"


def test_user_behavior_event_creates_usage_metric(monkeypatch):
    from app.services.external_event_inbox import process_external_event_inbox_events

    monkeypatch.setenv("OBSERVABILITY_WEBHOOK_SECRET", "observability-webhook-secret")
    store = _store()
    _receive(
        store,
        "user_behavior",
        {
            "active_users": 12,
            "conversion_count": 4,
            "error_count": 1,
            "event_count": 30,
            "feature_code": "deployment.detail",
            "user_segment": "release_owner",
            "window_end": "2026-07-11T00:05:00Z",
            "window_start": "2026-07-11T00:00:00Z",
        },
        "behavior-001",
    )

    assert process_external_event_inbox_events(
        store,
        worker_id="event-worker",
    ) == 1
    metric = next(iter(store.user_usage_metrics.values()))
    assert metric["product_id"] == "product_001"
    assert metric["feature_code"] == "deployment.detail"
    assert metric["source_channel"] == "user_behavior_webhook"


def test_observability_payload_cannot_override_connection_product(monkeypatch):
    from app.services.external_event_inbox import process_external_event_inbox_events

    monkeypatch.setenv("OBSERVABILITY_WEBHOOK_SECRET", "observability-webhook-secret")
    store = _store()
    event = _receive(
        store,
        "prometheus",
        {
            "product_id": "product_other",
            "window_start": "2026-07-11T00:00:00Z",
            "window_end": "2026-07-11T00:05:00Z",
            "request_count": 1,
            "error_count": 0,
        },
        "prometheus-override",
    )

    assert process_external_event_inbox_events(
        store,
        worker_id="event-worker",
    ) == 1
    assert next(iter(store.online_log_metrics.values()))["product_id"] == "product_001"
    assert store.external_event_inbox[event["id"]]["status"] == "completed"
