from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_later_phase_entries_return_honest_placeholder_contracts():
    headers = auth_headers()
    endpoints = [
        "/api/dashboard/it-team",
        "/api/bugs",
        "/api/devops/gitlab/daily-code-metrics",
        "/api/devops/jenkins/releases",
        "/api/ops/online-log-metrics",
        "/api/insights/usage-metrics",
        "/api/insights/user-feedback",
        "/api/planning/iteration-suggestions",
    ]

    for endpoint in endpoints:
        body = client.get(endpoint, headers=headers).json()
        assert body["trace_id"].startswith("trace_")
        assert body["data"]["status"] == "placeholder"
        assert body["data"]["items"] == []
        assert body["data"]["available_phase"] in {"MVP 占位 / v1.1", "MVP 占位 / v1.2"}
        assert "不返回伪造统计数据" in body["data"]["message"]
