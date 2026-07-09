from __future__ import annotations

from urllib.parse import quote

from fastapi.testclient import TestClient

from app.main import app, settings
from app.services.object_storage import object_storage

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_system_alert_incident_can_be_acknowledged_closed_and_subscribed():
    app.state.store.reset()
    headers = auth_headers()

    health = client.get("/api/system/health", headers=headers)
    assert health.status_code == 200
    alerts = health.json()["data"]["operations"]["alert_center"]["alerts"]
    assert alerts
    alert_id = alerts[0]["id"]

    acknowledged = client.patch(
        f"/api/system/alerts/{quote(alert_id, safe='')}",
        headers=headers,
        json={"owner": "值班负责人", "status": "acknowledged"},
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["data"]["status"] == "acknowledged"
    assert acknowledged.json()["data"]["owner"] == "值班负责人"
    acknowledged_history = acknowledged.json()["data"]["status_history"]
    assert acknowledged_history[-1]["from_status"] == "open"
    assert acknowledged_history[-1]["to_status"] == "acknowledged"
    assert "status" in acknowledged_history[-1]["changed_fields"]
    assert "owner" in acknowledged_history[-1]["changed_fields"]

    missing_reason = client.patch(
        f"/api/system/alerts/{quote(alert_id, safe='')}",
        headers=headers,
        json={"status": "closed"},
    )
    assert missing_reason.status_code == 400
    assert missing_reason.json()["detail"]["code"] == "VALIDATION_ERROR"

    closed = client.patch(
        f"/api/system/alerts/{quote(alert_id, safe='')}",
        headers=headers,
        json={"close_reason": "测试环境确认可忽略", "status": "closed"},
    )
    assert closed.status_code == 200
    assert closed.json()["data"]["close_reason"] == "测试环境确认可忽略"
    assert closed.json()["data"]["status"] == "closed"
    closed_history = closed.json()["data"]["status_history"]
    assert len(closed_history) == 2
    assert closed_history[-1]["from_status"] == "acknowledged"
    assert closed_history[-1]["to_status"] == "closed"
    assert closed_history[-1]["close_reason"] == "测试环境确认可忽略"

    subscription = client.post(
        "/api/system/alerts/subscriptions",
        headers=headers,
        json={
            "channel": "email",
            "severity_min": "high",
            "target": "ops@example.com",
        },
    )
    assert subscription.status_code == 200
    assert subscription.json()["data"]["channel"] == "email"
    assert subscription.json()["data"]["severity_min"] == "high"

    patched_subscription = client.patch(
        f"/api/system/alerts/subscriptions/{subscription.json()['data']['id']}",
        headers=headers,
        json={"enabled": False},
    )
    assert patched_subscription.status_code == 200
    patched_data = patched_subscription.json()["data"]
    assert patched_data["enabled"] is False
    assert patched_data["channel"] == "email"
    assert patched_data["severity_min"] == "high"
    assert patched_data["target"] == "ops@example.com"

    health_after_subscription_update = client.get("/api/system/health", headers=headers)
    assert health_after_subscription_update.status_code == 200
    subscriptions = health_after_subscription_update.json()["data"]["operations"]["alert_center"]["subscriptions"]
    assert subscriptions[0]["enabled"] is False


def test_system_alert_rules_and_admin_weekly_report_are_operable():
    app.state.store.reset()
    headers = auth_headers()

    created = client.post(
        "/api/system/alerts/rules",
        headers=headers,
        json={
            "condition_json": {"score_lt": 80},
            "component": "product_onboarding",
            "name": "产品接入评分低于 80",
            "owner": "产品负责人",
            "severity_min": "medium",
            "source": "product_score",
        },
    )
    assert created.status_code == 200
    rule = created.json()["data"]
    assert rule["enabled"] is True
    assert rule["condition_json"]["score_lt"] == 80
    assert rule["source"] == "product_score"

    listed = client.get("/api/system/alerts/rules", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["data"]["summary"]["total"] == 1

    patched = client.patch(
        f"/api/system/alerts/rules/{rule['id']}",
        headers=headers,
        json={"enabled": False, "severity_min": "high"},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["enabled"] is False
    assert patched.json()["data"]["severity_min"] == "high"

    health = client.get("/api/system/health", headers=headers)
    assert health.status_code == 200
    alert_center = health.json()["data"]["operations"]["alert_center"]
    assert alert_center["summary"]["rule_count"] == 1
    assert alert_center["summary"]["enabled_rule_count"] == 0

    report = client.get("/api/system/admin-weekly-report?days=7", headers=headers)
    assert report.status_code == 200
    payload = report.json()["data"]
    assert payload["summary"]["window_days"] == 7
    assert "AI Brain 管理员周报" in payload["markdown"]
    assert "sections" in payload


def test_system_alert_subscriptions_create_deduplicated_notification_outbox():
    app.state.store.reset()
    headers = auth_headers()

    subscription = client.post(
        "/api/system/alerts/subscriptions",
        headers=headers,
        json={
            "channel": "in_app",
            "scope": "source:system_check",
            "severity_min": "low",
            "target": "ops-duty",
        },
    )
    assert subscription.status_code == 200
    subscription_id = subscription.json()["data"]["id"]

    health = client.get("/api/system/health", headers=headers)
    assert health.status_code == 200
    alert_center = health.json()["data"]["operations"]["alert_center"]
    notifications = alert_center["notifications"]
    assert notifications
    notification = notifications[0]
    assert notification["subscription_id"] == subscription_id
    assert notification["channel"] == "in_app"
    assert notification["target"] == "ops-duty"
    assert notification["status"] == "pending"
    assert notification["payload_json"]["source"] == "system_check"
    assert alert_center["summary"]["pending_notification_count"] >= 1
    first_notification_count = len(app.state.store.system_alert_notifications)

    refreshed = client.get("/api/system/health", headers=headers)
    assert refreshed.status_code == 200
    assert len(app.state.store.system_alert_notifications) == first_notification_count


def test_system_alert_notification_dispatch_marks_in_app_sent():
    app.state.store.reset()
    headers = auth_headers()

    subscription = client.post(
        "/api/system/alerts/subscriptions",
        headers=headers,
        json={
            "channel": "in_app",
            "scope": "source:system_check",
            "severity_min": "low",
            "target": "ops-duty",
        },
    )
    assert subscription.status_code == 200

    health = client.get("/api/system/health", headers=headers)
    assert health.status_code == 200
    assert health.json()["data"]["operations"]["alert_center"]["summary"]["pending_notification_count"] >= 1

    dispatched = client.post(
        "/api/system/alerts/notifications/dispatch",
        headers=headers,
        json={"limit": 200},
    )
    assert dispatched.status_code == 200
    payload = dispatched.json()["data"]
    assert payload["summary"]["processed_count"] >= 1
    assert payload["summary"]["sent_count"] >= 1
    assert payload["remaining_pending_count"] == 0
    assert all(item["status"] == "sent" for item in payload["notifications"])
    assert all(item["attempts"] == 1 for item in payload["notifications"])
    assert all(item["sent_at"] for item in payload["notifications"])
    assert all(
        item["payload_json"]["delivery_result"]["provider"] == "in_app"
        for item in payload["notifications"]
    )
    assert app.state.store.audit_events[-1]["event_type"] == "system_alert_notifications.dispatched"


def test_system_alert_notification_dispatch_can_retry_failed_webhook_targets():
    app.state.store.reset()
    headers = auth_headers()

    subscription = client.post(
        "/api/system/alerts/subscriptions",
        headers=headers,
        json={
            "channel": "dingtalk",
            "scope": "source:system_check",
            "severity_min": "low",
            "target": "ding-not-a-webhook-url",
        },
    )
    assert subscription.status_code == 200

    health = client.get("/api/system/health", headers=headers)
    assert health.status_code == 200

    dispatched = client.post(
        "/api/system/alerts/notifications/dispatch",
        headers=headers,
        json={"limit": 1},
    )
    assert dispatched.status_code == 200
    failed_notification = dispatched.json()["data"]["notifications"][0]
    assert failed_notification["status"] == "failed"
    assert failed_notification["attempts"] == 1
    assert failed_notification["last_error"] == "DINGTALK_TARGET_URL_REQUIRED"

    retried = client.post(
        "/api/system/alerts/notifications/dispatch",
        headers=headers,
        json={"include_failed": True, "limit": 1},
    )
    assert retried.status_code == 200
    retried_notification = retried.json()["data"]["notifications"][0]
    assert retried_notification["id"] == failed_notification["id"]
    assert retried_notification["status"] == "failed"
    assert retried_notification["attempts"] == 2
    assert retried_notification["last_error"] == "DINGTALK_TARGET_URL_REQUIRED"


def test_product_onboarding_score_uses_real_health_signals():
    app.state.store.reset()
    headers = auth_headers()
    store = app.state.store
    product_id = "product_health_001"
    store.products[product_id] = {
        "code": "health-product",
        "id": product_id,
        "name": "健康评分产品",
        "status": "active",
    }
    store.product_versions["version_health_001"] = {
        "code": "v1",
        "id": "version_health_001",
        "name": "v1",
        "product_id": product_id,
        "status": "active",
    }
    store.product_modules["module_health_001"] = {
        "code": "core",
        "id": "module_health_001",
        "name": "核心模块",
        "product_id": product_id,
        "status": "active",
    }
    store.product_git_repositories["git_health_001"] = {
        "id": "git_health_001",
        "name": "主仓库",
        "product_id": product_id,
        "remote_url": "https://example.com/health/product.git",
        "status": "active",
    }
    store.related_systems["related_health_001"] = {
        "id": "related_health_001",
        "name": "关联系统",
        "product_id": product_id,
        "status": "active",
    }
    store.knowledge_documents["knowledge_health_001"] = {
        "id": "knowledge_health_001",
        "index_status": "vector_indexed",
        "name": "产品知识",
        "product_id": product_id,
    }
    store.plugin_connections["plugin_connection_health_001"] = {
        "id": "plugin_connection_health_001",
        "last_test_summary": {
            "checked_at": "2026-07-09T10:00:00+00:00",
            "status": "failed",
        },
        "name": "失败插件连接",
        "plugin_code": "dingtalk",
        "request_config": {"product_id": product_id},
        "status": "active",
    }

    response = client.get("/api/system/health", headers=headers)
    assert response.status_code == 200
    products = response.json()["data"]["operations"]["product_onboarding_scores"]["products"]
    product = next(item for item in products if item["product_id"] == product_id)
    assert product["plugin_connection_count"] == 1
    assert product["plugin_failed_connection_count"] == 1
    assert product["permission_scope_count"] >= 1
    assert product["permission_scope_status"] == "configured"
    assert product["recent_health_status"] == "degraded"
    assert product["recent_health_check"]["checked_at"] == "2026-07-09T10:00:00+00:00"
    assert product["recent_health_check"]["failed_plugin_connection_count"] == 1
    assert "插件连接健康检查失败" in product["recent_health_check"]["summary"]
    assert "未配置产品权限范围" not in product["missing_items"]


def test_object_storage_cleanup_dry_run_and_confirm(monkeypatch, tmp_path):
    app.state.store.reset()
    monkeypatch.setattr(settings, "object_storage_provider", "local")
    monkeypatch.setattr(settings, "object_storage_local_dir", str(tmp_path))
    monkeypatch.setattr(settings, "object_storage_bucket", "ai-brain-knowledge")
    headers = auth_headers()
    store = app.state.store
    storage = object_storage()
    storage.put_bytes(
        bucket=settings.object_storage_bucket,
        content=b"orphan pdf",
        mime_type="application/pdf",
        object_key="knowledge/deleted.pdf",
    )
    store.knowledge_documents["knowledge_document_active"] = {
        "id": "knowledge_document_active",
        "index_status": "vector_indexed",
        "title": "保留文档",
    }
    store.knowledge_assets["knowledge_asset_orphan"] = {
        "bucket": settings.object_storage_bucket,
        "document_id": "knowledge_document_deleted",
        "filename": "deleted.pdf",
        "id": "knowledge_asset_orphan",
        "object_key": "knowledge/deleted.pdf",
    }
    store.knowledge_assets["knowledge_asset_incomplete"] = {
        "bucket": settings.object_storage_bucket,
        "document_id": "knowledge_document_active",
        "filename": "broken.pdf",
        "id": "knowledge_asset_incomplete",
        "object_key": "",
    }

    dry_run = client.post(
        "/api/system/object-storage/cleanup",
        headers=headers,
        json={"confirmed": False},
    )
    assert dry_run.status_code == 200
    plan = dry_run.json()["data"]
    assert plan["dry_run"] is True
    assert plan["planned_asset_cleanup_count"] == 1
    assert plan["planned_object_delete_count"] == 1
    assert plan["blocked_asset_count"] == 1
    assert "knowledge_asset_orphan" in store.knowledge_assets
    assert storage.get_bytes(
        bucket=settings.object_storage_bucket,
        object_key="knowledge/deleted.pdf",
    ) == b"orphan pdf"

    confirmed = client.post(
        "/api/system/object-storage/cleanup",
        headers=headers,
        json={"confirmed": True, "reason": "测试同步清理"},
    )
    assert confirmed.status_code == 200
    result = confirmed.json()["data"]
    assert result["dry_run"] is False
    assert result["cleaned_asset_ids"] == ["knowledge_asset_orphan"]
    assert result["object_delete_count"] == 1
    assert "knowledge_asset_orphan" not in store.knowledge_assets
    assert "knowledge_asset_incomplete" in store.knowledge_assets
    try:
        storage.get_bytes(
            bucket=settings.object_storage_bucket,
            object_key="knowledge/deleted.pdf",
        )
    except FileNotFoundError:
        pass
    else:  # pragma: no cover - defensive assertion clarity
        raise AssertionError("orphan object was not deleted")
    assert any(
        event["event_type"] == "system.object_storage.cleanup"
        and event["payload"]["cleaned_asset_count"] == 1
        for event in store.audit_events
    )
