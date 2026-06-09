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


def test_later_phase_entries_return_empty_lists_without_fake_data():
    headers = auth_headers()
    endpoints = [
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
        assert body["data"]["items"] == []
        assert body["data"]["total"] == 0
        assert "placeholder" not in body["data"]
        assert "available_phase" not in body["data"]


def test_dashboard_it_team_returns_real_mvp_aggregate_without_fake_rows():
    app.state.store.reset()
    headers = auth_headers()
    product = client.post(
        "/api/products",
        json={"code": "rd-platform", "name": "研发大脑平台"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1 MVP"},
        headers=headers,
    ).json()["data"]
    pending_requirement = client.post(
        "/api/requirements",
        json={
            "content": "进入首页看板待审批需求统计。",
            "product_id": product["id"],
            "title": "首页看板待审批需求",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    approved_requirement = client.post(
        "/api/requirements",
        json={
            "content": "进入首页看板 AI 任务统计。",
            "product_id": product["id"],
            "title": "首页看板任务需求",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/requirements/{approved_requirement['id']}/approve",
        json={},
        headers=headers,
    )
    generated = client.post(
        f"/api/requirements/{approved_requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    started = client.post(
        f"/api/ai-tasks/{generated['task_id']}/start",
        headers=headers,
    ).json()["data"]
    knowledge = client.post(
        "/api/knowledge/documents",
        json={
            "content": "dashboard knowledge source",
            "permission_roles": ["admin"],
            "product_id": product["id"],
            "title": "首页看板知识",
        },
        headers=headers,
    ).json()["data"]
    module = client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": "knowledge", "name": "知识中心"},
        headers=headers,
    ).json()["data"]
    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "default_branch": "main",
            "git_provider": "gitlab",
            "name": "dashboard-api",
            "project_path": "rd/dashboard-api",
            "remote_url": "https://gitlab.internal/rd/dashboard-api.git",
            "repo_type": "code",
            "root_path": "/",
        },
        headers=headers,
    ).json()["data"]
    bug = client.post(
        "/api/bugs",
        json={
            "description": "首页看板需要统计高严重级别 Bug。",
            "module_code": module["code"],
            "product_id": product["id"],
            "severity": "critical",
            "source": "manual_test",
            "title": "首页看板严重 Bug",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    client.post(
        "/api/devops/gitlab/daily-code-metrics",
        json={
            "changed_files": 8,
            "commit_count": 7,
            "merge_request_count": 2,
            "metric_date": "2026-06-01",
            "product_id": product["id"],
            "quality_score": 88.5,
            "repository_id": repository["id"],
            "risk_count": 1,
        },
        headers=headers,
    )
    client.post(
        "/api/devops/jenkins/releases",
        json={
            "build_id": "dashboard-build-1",
            "job_name": "dashboard-deploy",
            "product_id": product["id"],
            "status": "failed",
            "version_id": version["id"],
        },
        headers=headers,
    )
    client.post(
        "/api/ops/online-log-metrics",
        json={
            "environment": "prod",
            "error_count": 12,
            "module_code": module["code"],
            "p95_latency_ms": 318.5,
            "p99_latency_ms": 640.25,
            "product_id": product["id"],
            "request_count": 2400,
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=headers,
    )
    client.post(
        "/api/insights/usage-metrics",
        json={
            "active_users": 42,
            "event_count": 120,
            "feature_code": "dashboard",
            "module_code": module["code"],
            "product_id": product["id"],
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=headers,
    )
    feedback = client.post(
        "/api/insights/user-feedback",
        json={
            "content": "首页看板需要看到真实运营数据。",
            "feedback_type": "improvement",
            "module_code": module["code"],
            "product_id": product["id"],
            "sentiment": "negative",
        },
        headers=headers,
    ).json()["data"]
    suggestions = client.post(
        "/api/planning/iteration-suggestions",
        json={
            "module_codes": [module["code"]],
            "planning_cycle": "2026Q3",
            "product_id": product["id"],
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]["items"]
    other_product = client.post(
        "/api/products",
        json={"code": "unrelated", "name": "无关产品"},
        headers=headers,
    ).json()["data"]
    unrelated_knowledge = client.post(
        "/api/knowledge/documents",
        json={
            "content": "unrelated dashboard knowledge source",
            "permission_roles": ["admin"],
            "product_id": other_product["id"],
            "title": "无关产品知识",
        },
        headers=headers,
    ).json()["data"]

    dashboard = client.get(
        f"/api/dashboard/it-team?product_id={product['id']}&time_range=all",
        headers=headers,
    ).json()["data"]

    assert dashboard["summary"]["active_products"] == 1
    assert dashboard["summary"]["ai_tasks"] == 1
    assert dashboard["summary"]["audit_events"] < len(app.state.store.audit_events)
    assert dashboard["summary"]["knowledge_deposits"] == 0
    assert dashboard["summary"]["knowledge_documents"] == 1
    assert dashboard["summary"]["pending_reviews"] == 1
    assert dashboard["summary"]["requirements"] == 2
    assert dashboard["summary"]["bugs"] == 1
    assert dashboard["summary"]["open_bugs"] == 1
    assert dashboard["summary"]["high_severity_bugs"] == 1
    assert dashboard["summary"]["gitlab_commits"] == 7
    assert dashboard["summary"]["jenkins_releases"] == 1
    assert dashboard["summary"]["online_errors"] == 12
    assert dashboard["summary"]["usage_events"] == 120
    assert dashboard["summary"]["user_feedback"] == 1
    assert dashboard["summary"]["iteration_suggestions"] == 1
    assert dashboard["bug_status_counts"] == [{"status": "open", "count": 1}]
    assert dashboard["latest_high_severity_bugs"][0]["id"] == bug["id"]
    assert dashboard["gitlab_daily_summary"] == {
        "average_quality_score": 88.5,
        "changed_files": 8,
        "commit_count": 7,
        "merge_request_count": 2,
        "metric_count": 1,
        "risk_count": 1,
    }
    assert dashboard["jenkins_release_status_counts"] == [{"status": "failed", "count": 1}]
    assert dashboard["online_log_summary"] == {
        "error_count": 12,
        "error_rate": 0.005,
        "max_p95_latency_ms": 318.5,
        "max_p99_latency_ms": 640.25,
        "metric_count": 1,
        "request_count": 2400,
    }
    assert dashboard["usage_metric_summary"]["active_users"] == 42
    assert dashboard["usage_metric_summary"]["event_count"] == 120
    assert dashboard["user_feedback_status_counts"] == [{"status": "open", "count": 1}]
    assert dashboard["iteration_suggestion_status_counts"] == [
        {"status": "suggested", "count": 1}
    ]
    assert suggestions[0]["evidence"][0]["subject_id"] == feedback["id"]
    assert {"status": "submitted", "count": 1} in dashboard["requirement_status_counts"]
    assert {"status": "designing", "count": 1} in dashboard["requirement_status_counts"]
    assert dashboard["task_status_counts"] == [{"status": "waiting_review", "count": 1}]
    assert dashboard["latest_tasks"][0]["id"] == generated["task_id"]
    assert dashboard["pending_reviews"][0]["id"] == started["review_id"]
    assert dashboard["recent_knowledge_documents"][0]["id"] == knowledge["id"]
    assert all(
        event["subject_id"] != unrelated_knowledge["id"]
        for event in dashboard["recent_audit_events"]
    )
    assert "items" not in dashboard
    assert pending_requirement["title"] in dashboard["requirement_titles"]
