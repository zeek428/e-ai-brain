from __future__ import annotations

from urllib.parse import quote

from fastapi.testclient import TestClient

from app.main import app

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
        json={"owner": "平台运维", "status": "acknowledged"},
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["data"]["status"] == "acknowledged"
    assert acknowledged.json()["data"]["owner"] == "平台运维"

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
