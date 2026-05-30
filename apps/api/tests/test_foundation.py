from fastapi.testclient import TestClient

from app.main import _tcp_endpoint_from_url, app

client = TestClient(app)


def test_health_includes_dependencies_and_trace_id():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["postgres"] in {"ok", "error"}
    assert body["redis"] in {"ok", "error"}
    assert body["model_gateway"] in {"configured", "local_fallback"}
    assert body["trace_id"].startswith("trace_")


def test_health_dependency_endpoint_parsing_supports_docker_service_names():
    assert _tcp_endpoint_from_url(
        "postgresql://ai_brain:password@postgres:5432/ai_brain",
        "127.0.0.1",
        5432,
    ) == ("postgres", 5432)
    assert _tcp_endpoint_from_url("redis://redis:6379/0", "127.0.0.1", 6379) == (
        "redis",
        6379,
    )


def test_login_and_current_user_use_bearer_token():
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )

    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["trace_id"].startswith("trace_")
    assert login_body["data"]["token_type"] == "bearer"
    token = login_body["data"]["access_token"]

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["trace_id"].startswith("trace_")
    assert me_body["data"] == {
        "id": "user_admin",
        "username": "admin@example.com",
        "display_name": "AI Brain Admin",
        "roles": ["admin"],
    }


def test_api_errors_include_trace_id_and_error_code():
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    body = response.json()
    assert body["detail"]["code"] == "UNAUTHORIZED"
    assert body["detail"]["trace_id"].startswith("trace_")


def test_logout_requires_bearer_token():
    response = client.post("/api/auth/logout")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"
