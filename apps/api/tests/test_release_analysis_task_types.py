from fastapi.testclient import TestClient

from app.main import app
from tests.test_technical_solution_export import auth_headers
from tests.test_v1_1_task_types import create_confirmed_technical_solution_task

client = TestClient(app)


def _create_release_context_records(headers: dict[str, str], requirement: dict[str, str]) -> None:
    repository = client.post(
        f"/api/products/{requirement['product_id']}/git-repositories",
        json={
            "default_branch": "main",
            "git_provider": "gitlab",
            "name": "release-api",
            "project_path": "rd/release-api",
            "remote_url": "https://gitlab.internal/rd/release-api.git",
            "repo_type": "code",
            "root_path": "/",
        },
        headers=headers,
    ).json()["data"]
    client.post(
        "/api/devops/gitlab/daily-code-metrics",
        json={
            "active_author_count": 3,
            "changed_files": 14,
            "commit_count": 6,
            "metric_date": "2026-06-01",
            "product_id": requirement["product_id"],
            "quality_score": 86,
            "repository_id": repository["id"],
            "risk_count": 1,
        },
        headers=headers,
    )
    client.post(
        "/api/devops/jenkins/releases",
        json={
            "build_id": "build-20260601-42",
            "build_number": 42,
            "environment": "prod",
            "job_name": "rd-platform-deploy",
            "product_id": requirement["product_id"],
            "started_at": "2026-06-01T10:00:00Z",
            "status": "success",
            "version_id": requirement["version_id"],
        },
        headers=headers,
    )
    client.post(
        "/api/ops/online-log-metrics",
        json={
            "anomaly_summary": "checkout timeout rose after candidate release",
            "environment": "prod",
            "error_count": 8,
            "product_id": requirement["product_id"],
            "request_count": 1600,
            "top_errors": [{"count": 8, "message": "CheckoutTimeout"}],
            "window_end": "2026-06-01T11:00:00Z",
            "window_start": "2026-06-01T10:00:00Z",
        },
        headers=headers,
    )
    client.post(
        "/api/bugs",
        json={
            "description": "发布候选版本仍有偶发超时。",
            "product_id": requirement["product_id"],
            "requirement_id": requirement["id"],
            "severity": "major",
            "source": "manual_test",
            "title": "发布前结算偶发超时",
            "version_id": requirement["version_id"],
        },
        headers=headers,
    )


def _create_confirmed_release_readiness_task(
    headers: dict[str, str],
    requirement: dict[str, str],
    technical_solution_task_id: str,
) -> str:
    created = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "release_readiness",
            "title": "发布评估：上线候选版本",
            "requirement_id": requirement["id"],
            "input": {"technical_solution_task_id": technical_solution_task_id},
        },
        headers=headers,
    ).json()["data"]
    started = client.post(f"/api/ai-tasks/{created['id']}/start", headers=headers).json()["data"]
    client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    return created["id"]


def test_release_readiness_runs_to_review_with_real_context_payload():
    headers = auth_headers()
    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)
    _create_release_context_records(headers, requirement)

    created = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "release_readiness",
            "title": "发布评估：上线候选版本",
            "requirement_id": requirement["id"],
            "input": {"technical_solution_task_id": technical_solution_task_id},
        },
        headers=headers,
    ).json()["data"]
    assert created["status"] == "draft"

    detail = client.get(f"/api/ai-tasks/{created['id']}", headers=headers).json()["data"]
    assert detail["input"]["source_technical_solution"]["id"] == technical_solution_task_id
    assert detail["input"]["bugs"]["total"] == 1
    assert detail["input"]["jenkins_releases"]["total"] == 1
    assert detail["input"]["online_log_metrics"]["total"] == 1
    assert detail["input"]["gitlab_daily_code_metrics"]["total"] == 1

    started = client.post(f"/api/ai-tasks/{created['id']}/start", headers=headers).json()["data"]
    assert started["status"] == "waiting_review"

    reviewed = client.get(f"/api/ai-tasks/{created['id']}", headers=headers).json()["data"]
    assert reviewed["output"]["kind"] == "release_readiness"
    assert reviewed["output"]["go_live_decision"] == "conditional_go"
    assert reviewed["output"]["risk_assessment"]
    assert reviewed["output"]["rollback_plan"]


def test_release_readiness_keeps_product_level_online_metrics_for_module_scope():
    headers = auth_headers()
    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)
    client.post(
        f"/api/products/{requirement['product_id']}/modules",
        json={"code": "checkout", "name": "Checkout"},
        headers=headers,
    )
    _create_release_context_records(headers, requirement)
    app.state.store.requirements[requirement["id"]]["module_code"] = "checkout"

    created = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "release_readiness",
            "title": "发布评估：模块上线候选版本",
            "requirement_id": requirement["id"],
            "input": {"technical_solution_task_id": technical_solution_task_id},
        },
        headers=headers,
    ).json()["data"]

    detail = client.get(f"/api/ai-tasks/{created['id']}", headers=headers).json()["data"]
    assert detail["input"]["online_log_metrics"]["total"] == 1
    assert detail["input"]["online_log_metrics"]["items"][0].get("module_code") is None


def test_post_release_analysis_approval_creates_ai_post_release_bugs():
    headers = auth_headers()
    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)
    _create_release_context_records(headers, requirement)
    release_readiness_task_id = _create_confirmed_release_readiness_task(
        headers,
        requirement,
        technical_solution_task_id,
    )

    created = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "post_release_analysis",
            "title": "上线后分析：生产观测",
            "requirement_id": requirement["id"],
            "input": {"release_readiness_task_id": release_readiness_task_id},
        },
        headers=headers,
    ).json()["data"]
    assert created["status"] == "draft"

    detail = client.get(f"/api/ai-tasks/{created['id']}", headers=headers).json()["data"]
    assert detail["input"]["source_release_readiness"]["id"] == release_readiness_task_id
    assert detail["input"]["bugs"]["total"] == 1
    assert detail["input"]["jenkins_releases"]["total"] == 1
    assert detail["input"]["online_log_metrics"]["total"] == 1

    started = client.post(f"/api/ai-tasks/{created['id']}/start", headers=headers).json()["data"]
    assert started["status"] == "waiting_review"
    reviewed = client.get(f"/api/ai-tasks/{created['id']}", headers=headers).json()["data"]
    assert reviewed["output"]["kind"] == "post_release_analysis"
    assert reviewed["output"]["bug_suggestions"]

    confirmed = client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    ).json()["data"]
    assert confirmed["task_status"] == "completed"

    bugs = client.get("/api/bugs?source=ai_post_release", headers=headers).json()["data"]["items"]
    assert len(bugs) == len(reviewed["output"]["bug_suggestions"])
    assert bugs[0]["related_task_id"] == created["id"]
    assert bugs[0]["requirement_id"] == requirement["id"]
    assert bugs[0]["source"] == "ai_post_release"
    assert bugs[0]["status"] == "open"
    assert bugs[0]["evidence"]["generated_by_task_type"] == "post_release_analysis"


def test_release_analysis_tasks_require_confirmed_source_tasks():
    headers = auth_headers()
    requirement, _technical_solution_task_id = create_confirmed_technical_solution_task(headers)

    release_response = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "release_readiness",
            "title": "发布评估：缺少技术方案",
            "requirement_id": requirement["id"],
            "input": {"technical_solution_task_id": "task_missing"},
        },
        headers=headers,
    )
    assert release_response.status_code == 400
    assert release_response.json()["detail"]["code"] == "TECHNICAL_SOLUTION_NOT_CONFIRMED"

    post_release_response = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "post_release_analysis",
            "title": "上线后分析：缺少发布评估",
            "requirement_id": requirement["id"],
            "input": {"release_readiness_task_id": "task_missing"},
        },
        headers=headers,
    )
    assert post_release_response.status_code == 400
    assert post_release_response.json()["detail"]["code"] == "RELEASE_READINESS_NOT_CONFIRMED"
