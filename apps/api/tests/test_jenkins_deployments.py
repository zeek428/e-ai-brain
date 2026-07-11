import base64

from fastapi.testclient import TestClient

from app.main import app
from app.services.operational_deployments import process_execution_outbox_events

client = TestClient(app)


class FakeResponse:
    def __init__(self, payload: str = "", *, location: str | None = None, status: int = 200):
        self._payload = payload.encode("utf-8")
        self.headers = {"Location": location} if location else {}
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._payload


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def create_context(headers: dict[str, str]) -> dict[str, str]:
    product = client.post(
        "/api/products",
        json={"code": "jenkins-deploy", "name": "Jenkins 部署产品"},
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
            "content": "通过 Jenkins 发布。",
            "product_id": product["id"],
            "title": "Jenkins 发布需求",
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


def create_jenkins_scheme(
    headers: dict[str, str],
    context: dict[str, str],
    *,
    health_check_config: dict | None = None,
    rollback_config: dict | None = None,
) -> dict:
    marketplace = client.get("/api/system/plugin-marketplace", headers=headers)
    assert marketplace.status_code == 200
    jenkins = next(
        item
        for item in marketplace.json()["data"]["items"]
        if item["code"] == "jenkins"
    )
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {
                "password_ref": "env:JENKINS_API_TOKEN",
                "username": "jenkins-bot",
            },
            "auth_type": "basic",
            "endpoint_url": "https://jenkins.example.com",
            "environment": "prod",
            "name": "生产 Jenkins",
            "plugin_id": jenkins["plugin_id"],
            "request_config": {},
            "status": "active",
        },
        headers=headers,
    )
    assert connection.status_code == 200, connection.text
    scheme = client.post(
        "/api/devops/deployment-schemes",
        json={
            "code": "jenkins-production",
            "config": {"parameters": {"DEPLOY_ENV": "prod"}},
            "deployment_method": "jenkins",
            "environment": "prod",
            "jenkins_connection_id": connection.json()["data"]["id"],
            "jenkins_job_name": "folder/deploy-product",
            "name": "Jenkins 生产部署",
            "product_id": context["product_id"],
            "health_check_config": health_check_config or {},
            "rollback_config": rollback_config or {},
            "window_enforcement": "warn",
        },
        headers=headers,
    )
    assert scheme.status_code == 200, scheme.text
    return scheme.json()["data"]


def create_deployment(headers: dict[str, str], context: dict[str, str], scheme: dict) -> dict:
    response = client.post(
        "/api/devops/deployments",
        json={
            "deployment_scheme_id": scheme["id"],
            "environment": "prod",
            "product_id": context["product_id"],
            "requirement_ids": [context["requirement_id"]],
            "rollback_plan": "回滚上一构建。",
            "title": "Jenkins 生产部署",
            "version_id": context["version_id"],
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_jenkins_trigger_and_sync_release_requirement(monkeypatch):
    app.state.store.reset()
    monkeypatch.setenv("JENKINS_API_TOKEN", "jenkins-secret-token")
    headers = auth_headers()
    context = create_context(headers)
    scheme = create_jenkins_scheme(headers, context)
    deployment = create_deployment(headers, context, scheme)
    requests: list[dict] = []
    build_checks = 0

    def fake_urlopen(request, timeout=30):  # type: ignore[no-untyped-def]
        nonlocal build_checks
        requests.append(
            {
                "authorization": request.get_header("Authorization"),
                "data": request.data,
                "method": request.get_method(),
                "url": request.full_url,
            }
        )
        if request.full_url.endswith("/buildWithParameters"):
            return FakeResponse(location="https://jenkins.example.com/queue/item/42/")
        if request.full_url.endswith("/queue/item/42/api/json"):
            return FakeResponse(
                '{"cancelled": false, "executable": {'
                '"number": 77, "url": "https://jenkins.example.com/job/folder/job/deploy-product/77/"}}'
            )
        if request.full_url.endswith("/77/api/json"):
            build_checks += 1
            if build_checks == 1:
                return FakeResponse('{"building": true, "result": null}')
            return FakeResponse('{"building": false, "result": "SUCCESS"}')
        raise AssertionError(request.full_url)

    monkeypatch.setattr("app.services.jenkins_deployments.urlopen", fake_urlopen)
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )
    assert started.status_code == 200, started.text
    run = started.json()["data"]["runs"][0]
    assert run["status"] == "queued"
    assert run["external_queue_url"] == "https://jenkins.example.com/queue/item/42/"
    assert run["plugin_invocation_log_id"]
    assert started.json()["data"]["dispatch_events"][0]["status"] == "completed"
    expected_auth = "Basic " + base64.b64encode(
        b"jenkins-bot:jenkins-secret-token"
    ).decode("ascii")
    assert requests[0]["authorization"] == expected_auth
    assert b"jenkins-secret-token" not in (requests[0]["data"] or b"")

    first_sync = client.post(
        f"/api/devops/deployments/{deployment['id']}/runs/{run['id']}/sync",
        headers=headers,
    )
    assert first_sync.status_code == 200, first_sync.text
    assert first_sync.json()["data"]["run"]["status"] == "running"
    assert first_sync.json()["data"]["run"]["external_build_id"] == "77"

    running_sync = client.post(
        f"/api/devops/deployments/{deployment['id']}/runs/{run['id']}/sync",
        headers=headers,
    )
    assert running_sync.status_code == 200, running_sync.text
    assert running_sync.json()["data"]["run"]["status"] == "running"
    assert running_sync.json()["data"]["run"]["sync_attempts"] == 2
    assert running_sync.json()["data"]["run"]["next_sync_at"]
    assert running_sync.json()["data"]["run"]["sync_lease_owner"] is None

    completed_sync = client.post(
        f"/api/devops/deployments/{deployment['id']}/runs/{run['id']}/sync",
        headers=headers,
    )
    assert completed_sync.status_code == 200, completed_sync.text
    assert completed_sync.json()["data"]["deployment"]["status"] == "succeeded"
    assert completed_sync.json()["data"]["run"]["status"] == "success"
    assert app.state.store.requirements[context["requirement_id"]]["status"] == "released"


def test_jenkins_cancel_waits_for_aborted_confirmation(monkeypatch):
    app.state.store.reset()
    monkeypatch.setenv("JENKINS_API_TOKEN", "jenkins-secret-token")
    headers = auth_headers()
    context = create_context(headers)
    scheme = create_jenkins_scheme(headers, context)
    deployment = create_deployment(headers, context, scheme)
    build_aborted = False

    def fake_urlopen(request, timeout=30):  # type: ignore[no-untyped-def]
        nonlocal build_aborted
        if request.full_url.endswith("/buildWithParameters"):
            return FakeResponse(location="https://jenkins.example.com/queue/item/43/")
        if request.full_url.endswith("/queue/cancelItem?id=43"):
            build_aborted = True
            return FakeResponse()
        if request.full_url.endswith("/queue/item/43/api/json"):
            return FakeResponse(
                '{"cancelled": true, "why": "Cancelled by AI Brain"}'
                if build_aborted
                else '{"cancelled": false}'
            )
        raise AssertionError(request.full_url)

    monkeypatch.setattr("app.services.jenkins_deployments.urlopen", fake_urlopen)
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    ).json()["data"]
    run = started["runs"][0]
    cancelled = client.post(
        f"/api/devops/deployments/{deployment['id']}/cancel",
        json={"reason": "停止 Jenkins 发布"},
        headers=headers,
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["data"]["status"] == "cancelling"

    synced = client.post(
        f"/api/devops/deployments/{deployment['id']}/runs/{run['id']}/sync",
        headers=headers,
    )
    assert synced.status_code == 200, synced.text
    assert synced.json()["data"]["deployment"]["status"] == "cancelled"
    assert synced.json()["data"]["run"]["status"] == "cancelled"


def test_jenkins_trigger_failure_records_retryable_failed_run(monkeypatch):
    app.state.store.reset()
    monkeypatch.setenv("JENKINS_API_TOKEN", "jenkins-secret-token")
    headers = auth_headers()
    context = create_context(headers)
    scheme = create_jenkins_scheme(headers, context)
    deployment = create_deployment(headers, context, scheme)

    def failing_urlopen(request, timeout=30):  # type: ignore[no-untyped-def]
        raise OSError("jenkins is unavailable")

    monkeypatch.setattr("app.services.jenkins_deployments.urlopen", failing_urlopen)
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )

    assert started.status_code == 200
    persisted = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert persisted["status"] == "deploying"
    assert persisted["runs"][0]["status"] == "queued"
    assert persisted["dispatch_events"][0]["status"] == "failed"
    assert "jenkins-secret-token" not in persisted["dispatch_events"][0]["last_error"]
    assert app.state.store.requirements[context["requirement_id"]]["status"] == "deploying"

    monkeypatch.setattr(
        "app.services.jenkins_deployments.urlopen",
        lambda request, timeout=30: FakeResponse(
            location="https://jenkins.example.com/queue/item/44/"
        ),
    )
    event = next(iter(app.state.store.execution_outbox_events.values()))
    event["available_at"] = "2000-01-01T00:00:00+00:00"
    processed = process_execution_outbox_events(
        app.state.store,
        limit=1,
        worker_id="test-worker",
    )
    assert processed == 1
    retried = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert retried["status"] == "deploying"
    assert retried["runs"][0]["status"] == "queued"
    assert retried["runs"][0]["external_queue_url"].endswith("/queue/item/44/")
    assert retried["dispatch_events"][0]["status"] == "completed"


def test_jenkins_dispatch_moves_to_dead_letter_after_retry_limit(monkeypatch):
    app.state.store.reset()
    monkeypatch.setenv("JENKINS_API_TOKEN", "jenkins-secret-token")
    monkeypatch.setattr(
        "app.services.operational_deployments.EXECUTION_OUTBOX_MAX_ATTEMPTS",
        2,
    )
    headers = auth_headers()
    context = create_context(headers)
    scheme = create_jenkins_scheme(headers, context)
    deployment = create_deployment(headers, context, scheme)

    def failing_urlopen(request, timeout=30):  # type: ignore[no-untyped-def]
        raise OSError("jenkins is unavailable")

    monkeypatch.setattr("app.services.jenkins_deployments.urlopen", failing_urlopen)
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )
    assert started.status_code == 200

    event = next(iter(app.state.store.execution_outbox_events.values()))
    event["available_at"] = "2000-01-01T00:00:00+00:00"
    assert process_execution_outbox_events(
        app.state.store,
        limit=1,
        worker_id="test-worker",
    ) == 0

    persisted = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert persisted["status"] == "failed"
    assert persisted["runs"][0]["status"] == "failed"
    assert persisted["dispatch_events"][0]["status"] == "dead_letter"
    assert app.state.store.requirements[context["requirement_id"]]["status"] == (
        "ready_for_release"
    )


def test_jenkins_missing_queue_location_records_failed_run(monkeypatch):
    app.state.store.reset()
    monkeypatch.setenv("JENKINS_API_TOKEN", "jenkins-secret-token")
    headers = auth_headers()
    context = create_context(headers)
    scheme = create_jenkins_scheme(headers, context)
    deployment = create_deployment(headers, context, scheme)
    monkeypatch.setattr(
        "app.services.jenkins_deployments.urlopen",
        lambda request, timeout=30: FakeResponse(),
    )

    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )

    assert started.status_code == 200
    persisted = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert persisted["status"] == "failed"
    assert persisted["runs"][0]["status"] == "failed"
    assert persisted["dispatch_events"][0]["status"] == "dead_letter"


def test_jenkins_rejects_cross_origin_queue_url_without_forwarding_credentials(monkeypatch):
    app.state.store.reset()
    monkeypatch.setenv("JENKINS_API_TOKEN", "jenkins-secret-token")
    headers = auth_headers()
    context = create_context(headers)
    scheme = create_jenkins_scheme(headers, context)
    deployment = create_deployment(headers, context, scheme)
    requested_urls: list[str] = []

    def fake_urlopen(request, timeout=30):  # type: ignore[no-untyped-def]
        requested_urls.append(request.full_url)
        return FakeResponse(location="https://credential-sink.example.com/queue/item/46/")

    monkeypatch.setattr("app.services.jenkins_deployments.urlopen", fake_urlopen)
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )

    assert started.status_code == 200
    assert requested_urls == [
        "https://jenkins.example.com/job/folder/job/deploy-product/buildWithParameters"
    ]
    persisted = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert persisted["status"] == "failed"
    assert persisted["runs"][0]["status"] == "failed"
    assert persisted["dispatch_events"][0]["status"] == "dead_letter"


def test_disabled_jenkins_connection_blocks_start_without_changing_deployment():
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers)
    scheme = create_jenkins_scheme(headers, context)
    deployment = create_deployment(headers, context, scheme)
    connection = app.state.store.plugin_connections[scheme["jenkins_connection_id"]]
    connection["status"] = "disabled"

    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )

    assert started.status_code == 409
    assert started.json()["detail"]["code"] == "DEPLOYMENT_JENKINS_UNAVAILABLE"
    persisted = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert persisted["status"] == "pending_ops"
    assert persisted["runs"] == []


def test_jenkins_cancel_failure_restores_deploying_state(monkeypatch):
    app.state.store.reset()
    monkeypatch.setenv("JENKINS_API_TOKEN", "jenkins-secret-token")
    headers = auth_headers()
    context = create_context(headers)
    scheme = create_jenkins_scheme(headers, context)
    deployment = create_deployment(headers, context, scheme)

    monkeypatch.setattr(
        "app.services.jenkins_deployments.urlopen",
        lambda request, timeout=30: FakeResponse(
            location="https://jenkins.example.com/queue/item/45/"
        ),
    )
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )
    assert started.status_code == 200, started.text

    def failing_cancel(request, timeout=30):  # type: ignore[no-untyped-def]
        raise OSError("jenkins cancel unavailable")

    monkeypatch.setattr("app.services.jenkins_deployments.urlopen", failing_cancel)
    cancelled = client.post(
        f"/api/devops/deployments/{deployment['id']}/cancel",
        json={"reason": "取消发布"},
        headers=headers,
    )

    assert cancelled.status_code == 502
    assert cancelled.json()["detail"]["code"] == "JENKINS_CANCEL_FAILED"
    persisted = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert persisted["status"] == "deploying"
    assert persisted["runs"][0]["status"] == "queued"
    assert persisted["runs"][0]["logs"][-1]["message"] == (
        "Jenkins cancel failed: OSError"
    )
    assert app.state.store.requirements[context["requirement_id"]]["status"] == "deploying"


def test_background_sync_claims_due_runs_with_repository_lease(monkeypatch):
    from app.services.deployment_sync_worker import sync_due_jenkins_deployments

    calls: list[dict] = []

    class Repository:
        def claim_due_deployment_runs(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append(kwargs)
            return [
                {
                    "id": "deployment_run_lease",
                    "deployment_request_id": "deployment_request_lease",
                }
            ]

    class Store:
        repository = Repository()

    monkeypatch.setattr(
        "app.services.deployment_sync_worker.sync_jenkins_deployment",
        lambda **kwargs: calls.append(kwargs),
    )

    processed = sync_due_jenkins_deployments(
        Store(),
        lease_seconds=45,
        limit=5,
        worker_id="deployment-sync-test",
    )

    assert processed == 1
    assert calls[0] == {
        "lease_seconds": 45,
        "limit": 5,
        "worker_id": "deployment-sync-test",
    }
    assert calls[1]["deployment_request_id"] == "deployment_request_lease"
    assert calls[1]["deployment_run_id"] == "deployment_run_lease"


def test_jenkins_success_runs_health_job_before_release(monkeypatch):
    app.state.store.reset()
    monkeypatch.setenv("JENKINS_API_TOKEN", "jenkins-secret-token")
    headers = auth_headers()
    context = create_context(headers)
    scheme = create_jenkins_scheme(
        headers,
        context,
        health_check_config={"job_name": "folder/verify-product"},
    )
    deployment = create_deployment(headers, context, scheme)
    triggered_jobs: list[str] = []

    def fake_urlopen(request, timeout=30):  # type: ignore[no-untyped-def]
        url = request.full_url
        if url.endswith("/job/folder/job/deploy-product/buildWithParameters"):
            triggered_jobs.append("deploy")
            return FakeResponse(location="https://jenkins.example.com/queue/item/50/")
        if url.endswith("/queue/item/50/api/json"):
            return FakeResponse(
                '{"cancelled": false, "executable": {'
                '"number": 50, "url": "https://jenkins.example.com/job/deploy/50/"}}'
            )
        if url.endswith("/job/deploy/50/api/json"):
            return FakeResponse('{"building": false, "result": "SUCCESS"}')
        if url.endswith("/job/folder/job/verify-product/buildWithParameters"):
            triggered_jobs.append("verify")
            return FakeResponse(location="https://jenkins.example.com/queue/item/51/")
        if url.endswith("/queue/item/51/api/json"):
            return FakeResponse(
                '{"cancelled": false, "executable": {'
                '"number": 51, "url": "https://jenkins.example.com/job/verify/51/"}}'
            )
        if url.endswith("/job/verify/51/api/json"):
            return FakeResponse('{"building": false, "result": "SUCCESS"}')
        raise AssertionError(url)

    monkeypatch.setattr("app.services.jenkins_deployments.urlopen", fake_urlopen)
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    ).json()["data"]
    deploy_run = started["runs"][0]
    client.post(
        f"/api/devops/deployments/{deployment['id']}/runs/{deploy_run['id']}/sync",
        headers=headers,
    )
    after_deploy = client.post(
        f"/api/devops/deployments/{deployment['id']}/runs/{deploy_run['id']}/sync",
        headers=headers,
    ).json()["data"]["deployment"]

    assert after_deploy["status"] == "verifying"
    verify_run = client.get(
        f"/api/devops/deployments/{deployment['id']}", headers=headers
    ).json()["data"]["runs"][0]
    assert verify_run["operation"] == "verify"
    client.post(
        f"/api/devops/deployments/{deployment['id']}/runs/{verify_run['id']}/sync",
        headers=headers,
    )
    completed = client.post(
        f"/api/devops/deployments/{deployment['id']}/runs/{verify_run['id']}/sync",
        headers=headers,
    ).json()["data"]["deployment"]

    assert triggered_jobs == ["deploy", "verify"]
    assert completed["status"] == "succeeded"
    assert app.state.store.requirements[context["requirement_id"]]["status"] == "released"


def test_jenkins_failure_dispatches_configured_rollback_job(monkeypatch):
    app.state.store.reset()
    monkeypatch.setenv("JENKINS_API_TOKEN", "jenkins-secret-token")
    headers = auth_headers()
    context = create_context(headers)
    scheme = create_jenkins_scheme(
        headers,
        context,
        rollback_config={
            "auto_on_failure": True,
            "enabled": True,
            "job_name": "folder/rollback-product",
        },
    )
    deployment = create_deployment(headers, context, scheme)
    triggered_jobs: list[str] = []

    def fake_urlopen(request, timeout=30):  # type: ignore[no-untyped-def]
        url = request.full_url
        if url.endswith("/job/folder/job/deploy-product/buildWithParameters"):
            triggered_jobs.append("deploy")
            return FakeResponse(location="https://jenkins.example.com/queue/item/60/")
        if url.endswith("/queue/item/60/api/json"):
            return FakeResponse(
                '{"cancelled": false, "executable": {'
                '"number": 60, "url": "https://jenkins.example.com/job/deploy/60/"}}'
            )
        if url.endswith("/job/deploy/60/api/json"):
            return FakeResponse('{"building": false, "result": "FAILURE"}')
        if url.endswith("/job/folder/job/rollback-product/buildWithParameters"):
            triggered_jobs.append("rollback")
            return FakeResponse(location="https://jenkins.example.com/queue/item/61/")
        raise AssertionError(url)

    monkeypatch.setattr("app.services.jenkins_deployments.urlopen", fake_urlopen)
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    ).json()["data"]
    deploy_run = started["runs"][0]
    client.post(
        f"/api/devops/deployments/{deployment['id']}/runs/{deploy_run['id']}/sync",
        headers=headers,
    )
    failed = client.post(
        f"/api/devops/deployments/{deployment['id']}/runs/{deploy_run['id']}/sync",
        headers=headers,
    ).json()["data"]["deployment"]

    assert triggered_jobs == ["deploy", "rollback"]
    assert failed["status"] == "rolling_back"
    rollback_run = client.get(
        f"/api/devops/deployments/{deployment['id']}", headers=headers
    ).json()["data"]["runs"][0]
    assert rollback_run["operation"] == "rollback"
