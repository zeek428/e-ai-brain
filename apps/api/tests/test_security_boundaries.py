from fastapi.testclient import TestClient
from gitlab_fakes import install_real_gitlab_api_stub

from app.main import app, settings

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_draft_product_detail_design_task(headers: dict[str, str]) -> str:
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
    requirement = client.post(
        "/api/requirements",
        json={
            "title": "权限边界验证",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "任务读写必须遵守任务类型角色边界。",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    task = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    return task["task_id"]


def create_product_detail_design_task_context(headers: dict[str, str]) -> dict[str, str]:
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
    requirement = client.post(
        "/api/requirements",
        json={
            "title": "权限过滤生命周期",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "生命周期和仪表盘不能泄露无权任务。",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    task = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    started = client.post(
        f"/api/ai-tasks/{task['task_id']}/start",
        headers=headers,
    ).json()["data"]
    return {
        "product_id": product["id"],
        "requirement_id": requirement["id"],
        "review_id": started["review_id"],
        "task_id": task["task_id"],
    }


def create_scoped_test_owner(headers: dict[str, str], *, product_id: str) -> dict[str, str]:
    suffix = len(getattr(app.state.user_repository, "users", {})) + 1
    username = f"scheduled-scope-{suffix}@example.com"
    created = client.post(
        "/api/users",
        json={
            "display_name": f"Scheduled Scope {suffix}",
            "password": "password123",
            "roles": ["test_owner"],
            "status": "active",
            "username": username,
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    user = created.json()["data"]
    scoped = client.put(
        f"/api/users/{user['id']}/scopes",
        json={
            "scopes": [
                {
                    "access_level": "read",
                    "scope_id": product_id,
                    "scope_type": "product",
                }
            ]
        },
        headers=headers,
    )
    assert scoped.status_code == 200, scoped.text
    return auth_headers(username, "password123")


def create_scoped_role_user(
    headers: dict[str, str],
    *,
    product_id: str,
    role_code: str,
) -> dict[str, str]:
    suffix = len(getattr(app.state.user_repository, "users", {})) + 1
    username = f"{role_code}-scope-{suffix}@example.com"
    created = client.post(
        "/api/users",
        json={
            "display_name": f"{role_code} Scope {suffix}",
            "password": "password123",
            "roles": [role_code],
            "status": "active",
            "username": username,
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    user = created.json()["data"]
    scoped = client.put(
        f"/api/users/{user['id']}/scopes",
        json={
            "scopes": [
                {
                    "access_level": "read",
                    "scope_id": product_id,
                    "scope_type": "product",
                }
            ]
        },
        headers=headers,
    )
    assert scoped.status_code == 200, scoped.text
    return auth_headers(username, "password123")


def create_manual_scheduled_job(
    headers: dict[str, str],
    *,
    name: str,
    product_id: str,
) -> dict:
    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "dashboard_snapshot_refresh",
            "name": name,
            "product_id": product_id,
            "schedule_type": "manual",
            "source_system": "ai-brain",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def add_scheduled_job_run(job: dict, *, run_id: str) -> None:
    app.state.store.scheduled_job_runs[run_id] = {
        "collector_run_id": None,
        "config_snapshot": dict(job),
        "created_at": "2026-06-27T10:00:00+00:00",
        "error_code": None,
        "error_message": None,
        "finished_at": "2026-06-27T10:01:00+00:00",
        "id": run_id,
        "records_imported": 0,
        "resolved_agent_snapshot": {},
        "resolved_plugin_snapshot": {},
        "resolved_prompt_snapshot": {},
        "resolved_skill_snapshots": [],
        "result_summary": {},
        "scheduled_for": "2026-06-27T10:00:00+00:00",
        "scheduled_job_id": job["id"],
        "source_run_id": None,
        "started_at": "2026-06-27T10:00:00+00:00",
        "status": "succeeded",
        "tool_policy_snapshot": {},
        "trigger_type": "manual",
        "updated_at": "2026-06-27T10:01:00+00:00",
    }


def create_product(headers: dict[str, str], *, code: str, name: str) -> dict:
    response = client.post(
        "/api/products",
        json={"code": code, "name": name},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create_requirement(headers: dict[str, str], *, product_id: str, title: str) -> dict:
    response = client.post(
        "/api/requirements",
        json={
            "content": f"{title} content",
            "product_id": product_id,
            "title": title,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create_bug(headers: dict[str, str], *, product_id: str, title: str) -> dict:
    response = client.post(
        "/api/bugs",
        json={
            "description": f"{title} description",
            "product_id": product_id,
            "severity": "major",
            "source": "manual_test",
            "title": title,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def add_code_inspection_report(*, report_id: str, product_id: str, title: str) -> None:
    app.state.store.code_inspection_reports[report_id] = {
        "branch": "main",
        "commit_sha": "abc123",
        "committer_summary": [{"email": "alice@example.com"}],
        "created_at": "2026-06-27T10:00:00+00:00",
        "created_by": "user_admin",
        "finding_count": 1,
        "id": report_id,
        "product_id": product_id,
        "repository": {"name": title, "project_path": f"example/{report_id}"},
        "repository_id": f"repo_{report_id}",
        "risk_level": "medium",
        "scan_mode": "native_full_scan",
        "severe_finding_count": 0,
        "source_system": "native-code-scanner",
        "status": "completed",
        "summary": title,
        "updated_at": "2026-06-27T10:00:00+00:00",
    }


def test_gitlab_review_api_surface_has_no_writeback_routes():
    paths = client.get("/openapi.json").json()["paths"]
    gitlab_paths = {
        path: methods
        for path, methods in paths.items()
        if path.startswith("/api/devops/gitlab/merge-requests")
    }

    assert set(gitlab_paths) == {
        "/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview",
        "/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot",
    }
    for path in gitlab_paths:
        assert "/comments" not in path
        assert "/approvals" not in path
        assert "/request-changes" not in path
        assert not path.endswith("/merge")


def test_core_management_lists_require_menu_declared_read_permissions():
    app.state.store.reset()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    forbidden_paths = [
        "/api/requirements",
        "/api/bugs",
        "/api/knowledge/documents",
        "/api/governance/code-inspections",
    ]
    for path in forbidden_paths:
        response = client.get(path, headers=reviewer_headers)
        assert response.status_code == 403, path
        assert response.json()["detail"]["code"] == "FORBIDDEN"


def test_product_scoped_management_lists_filter_business_records():
    app.state.store.reset()
    admin_headers = auth_headers()
    product_a = create_product(
        admin_headers,
        code="scope-contract-a",
        name="Scope Contract A",
    )
    product_b = create_product(
        admin_headers,
        code="scope-contract-b",
        name="Scope Contract B",
    )
    requirement_a = create_requirement(
        admin_headers,
        product_id=product_a["id"],
        title="A 产品需求",
    )
    requirement_b = create_requirement(
        admin_headers,
        product_id=product_b["id"],
        title="B 产品需求",
    )
    bug_a = create_bug(admin_headers, product_id=product_a["id"], title="A 产品 Bug")
    bug_b = create_bug(admin_headers, product_id=product_b["id"], title="B 产品 Bug")
    add_code_inspection_report(
        report_id="code_inspection_scope_a",
        product_id=product_a["id"],
        title="A 产品巡检",
    )
    add_code_inspection_report(
        report_id="code_inspection_scope_b",
        product_id=product_b["id"],
        title="B 产品巡检",
    )

    scoped_headers = create_scoped_role_user(
        admin_headers,
        product_id=product_a["id"],
        role_code="product_owner",
    )

    scoped_requirements = client.get(
        "/api/requirements?page=1&page_size=20",
        headers=scoped_headers,
    )
    assert scoped_requirements.status_code == 200, scoped_requirements.text
    requirement_ids = {item["id"] for item in scoped_requirements.json()["data"]["items"]}
    assert requirement_a["id"] in requirement_ids
    assert requirement_b["id"] not in requirement_ids

    scoped_bugs = client.get("/api/bugs?page=1&page_size=20", headers=scoped_headers)
    assert scoped_bugs.status_code == 200, scoped_bugs.text
    bug_ids = {item["id"] for item in scoped_bugs.json()["data"]["items"]}
    assert bug_a["id"] in bug_ids
    assert bug_b["id"] not in bug_ids

    scoped_code_inspections = client.get(
        "/api/governance/code-inspections?page=1&page_size=20",
        headers=scoped_headers,
    )
    assert scoped_code_inspections.status_code == 200, scoped_code_inspections.text
    report_ids = {item["id"] for item in scoped_code_inspections.json()["data"]["items"]}
    assert "code_inspection_scope_a" in report_ids
    assert "code_inspection_scope_b" not in report_ids


def test_role_boundaries_for_product_audit_and_gitlab_preview(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    forbidden_product = client.post(
        "/api/products",
        json={"code": "forbidden", "name": "Reviewer Cannot Maintain Products"},
        headers=reviewer_headers,
    )
    assert forbidden_product.status_code == 403
    assert forbidden_product.json()["detail"]["code"] == "FORBIDDEN"

    product = client.post(
        "/api/products",
        json={"code": "rd-platform", "name": "研发大脑平台"},
        headers=admin_headers,
    ).json()["data"]
    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "name": "AI Brain API",
            "remote_url": "https://gitlab.example.com/platform/ai-brain.git",
            "git_provider": "gitlab",
            "project_path": "platform/ai-brain",
            "credential_ref": "env:GITLAB_READONLY_TOKEN",
        },
        headers=admin_headers,
    ).json()["data"]

    preview = client.get(
        f"/api/devops/gitlab/merge-requests/{repository['id']}/42/preview",
        headers=reviewer_headers,
    )
    assert preview.status_code == 200
    assert preview.json()["data"]["writeback_allowed"] is False

    audit = client.get("/api/audit/events", headers=reviewer_headers)
    assert audit.status_code == 403
    assert audit.json()["detail"]["code"] == "FORBIDDEN"

    filtered_audit = client.get(
        "/api/audit/events?event_type=product.created",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert len(filtered_audit) == 1
    assert filtered_audit[0]["event_type"] == "product.created"
    assert filtered_audit[0]["created_at"].startswith("20")


def test_operational_config_lists_require_permissions_and_scheduled_jobs_filter_product_scope():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    forbidden_paths = [
        "/api/system/scheduled-jobs",
        "/api/system/scheduled-job-runs",
        "/api/system/scheduled-job-runs/observability",
        "/api/system/plugins",
        "/api/system/plugin-connections",
        "/api/system/plugin-actions",
        "/api/system/plugin-invocation-logs",
        "/api/system/ai-executor-runners",
    ]
    for path in forbidden_paths:
        response = client.get(path, headers=reviewer_headers)
        assert response.status_code == 403, path
        assert response.json()["detail"]["code"] == "FORBIDDEN"

    product_a = client.post(
        "/api/products",
        json={"code": "scheduled-scope-a", "name": "定时作业范围 A"},
        headers=admin_headers,
    ).json()["data"]
    product_b = client.post(
        "/api/products",
        json={"code": "scheduled-scope-b", "name": "定时作业范围 B"},
        headers=admin_headers,
    ).json()["data"]
    job_a = create_manual_scheduled_job(
        admin_headers,
        name="A 产品作业",
        product_id=product_a["id"],
    )
    job_b = create_manual_scheduled_job(
        admin_headers,
        name="B 产品作业",
        product_id=product_b["id"],
    )
    add_scheduled_job_run(job_a, run_id="scheduled_run_scope_a")
    add_scheduled_job_run(job_b, run_id="scheduled_run_scope_b")

    scoped_headers = create_scoped_test_owner(admin_headers, product_id=product_a["id"])
    scoped_jobs = client.get("/api/system/scheduled-jobs", headers=scoped_headers)
    assert scoped_jobs.status_code == 200, scoped_jobs.text
    scoped_job_ids = {item["id"] for item in scoped_jobs.json()["data"]["items"]}
    assert job_a["id"] in scoped_job_ids
    assert job_b["id"] not in scoped_job_ids

    scoped_runs = client.get("/api/system/scheduled-job-runs", headers=scoped_headers)
    assert scoped_runs.status_code == 200, scoped_runs.text
    scoped_run_ids = {item["id"] for item in scoped_runs.json()["data"]["items"]}
    assert scoped_run_ids == {"scheduled_run_scope_a"}

    hidden_runs = client.get(
        f"/api/system/scheduled-job-runs?scheduled_job_id={job_b['id']}",
        headers=scoped_headers,
    )
    assert hidden_runs.status_code == 200
    assert hidden_runs.json()["data"]["items"] == []

    hidden_run = client.post(
        f"/api/system/scheduled-jobs/{job_b['id']}/run",
        headers=scoped_headers,
    )
    assert hidden_run.status_code == 404
    assert hidden_run.json()["detail"]["code"] == "NOT_FOUND"


def test_audit_events_filter_by_actor_and_time_range():
    app.state.store.reset()
    admin_headers = auth_headers()
    store = app.state.store
    outside = store.audit(
        event_type="requirement.created",
        actor_id="user_admin",
        subject_type="requirement",
        subject_id="requirement_old",
    )
    outside["created_at"] = "2026-05-30T08:00:00+00:00"
    included = store.audit(
        event_type="requirement.approved",
        actor_id="user_admin",
        subject_type="requirement",
        subject_id="requirement_new",
    )
    included["created_at"] = "2026-05-31T08:00:00+00:00"
    other_actor = store.audit(
        event_type="requirement.approved",
        actor_id="user_reviewer",
        subject_type="requirement",
        subject_id="requirement_new",
    )
    other_actor["created_at"] = "2026-05-31T09:00:00+00:00"

    filtered = client.get(
        "/api/audit/events"
        "?actor_id=user_admin"
        "&subject_type=requirement"
        "&created_from=2026-05-31T00:00:00+00:00"
        "&created_to=2026-05-31T23:59:59+00:00",
        headers=admin_headers,
    ).json()["data"]

    assert filtered["total"] == 1
    assert filtered["items"][0]["id"] == included["id"]
    assert outside["id"] not in [item["id"] for item in filtered["items"]]
    assert other_actor["id"] not in [item["id"] for item in filtered["items"]]


def test_seeded_default_users_are_disabled_outside_local_env():
    original_env = settings.app_env
    original_persistence_mode = settings.persistence_mode
    settings.app_env = "production"
    try:
        response = client.post(
            "/api/auth/login",
            json={"username": "admin@example.com", "password": "admin123"},
        )
        settings.persistence_mode = "postgres"
        postgres_response = client.post(
            "/api/auth/login",
            json={"username": "admin@example.com", "password": "admin123"},
        )
    finally:
        settings.app_env = original_env
        settings.persistence_mode = original_persistence_mode

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "DEFAULT_CREDENTIALS_DISABLED"
    assert postgres_response.status_code == 403
    assert postgres_response.json()["detail"]["code"] == "DEFAULT_CREDENTIALS_DISABLED"


def test_reviewer_cannot_start_or_read_product_design_tasks_and_reviews():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    task_id = create_draft_product_detail_design_task(admin_headers)

    forbidden_start = client.post(f"/api/ai-tasks/{task_id}/start", headers=reviewer_headers)
    assert forbidden_start.status_code == 403
    assert forbidden_start.json()["detail"]["code"] == "FORBIDDEN"

    reviewer_tasks = client.get("/api/ai-tasks", headers=reviewer_headers).json()["data"]
    assert reviewer_tasks["items"] == []

    forbidden_detail = client.get(f"/api/ai-tasks/{task_id}", headers=reviewer_headers)
    assert forbidden_detail.status_code == 403
    assert forbidden_detail.json()["detail"]["code"] == "FORBIDDEN"

    started = client.post(f"/api/ai-tasks/{task_id}/start", headers=admin_headers).json()["data"]
    pending_reviews = client.get("/api/reviews/pending", headers=reviewer_headers).json()["data"]
    assert pending_reviews["items"] == []

    forbidden_review = client.get(
        f"/api/reviews/{started['review_id']}",
        headers=reviewer_headers,
    )
    assert forbidden_review.status_code == 403
    assert forbidden_review.json()["detail"]["code"] == "FORBIDDEN"


def test_reviewer_cannot_see_unreadable_product_design_tasks_in_aggregates():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    context = create_product_detail_design_task_context(admin_headers)

    lifecycle = client.get(
        "/api/lifecycle/context"
        f"?subject_type=requirement&subject_id={context['requirement_id']}"
        "&direction=both&include_risks=true",
        headers=reviewer_headers,
    ).json()["data"]
    assert lifecycle["downstream"] == []
    assert lifecycle["summary"]["downstream_count"] == 0
    assert lifecycle["risk_signals"] == []

    dashboard = client.get(
        f"/api/dashboard/it-team?product_id={context['product_id']}",
        headers=reviewer_headers,
    ).json()["data"]
    assert dashboard["summary"]["ai_tasks"] == 0
    assert dashboard["summary"]["pending_reviews"] == 0
    assert dashboard["latest_tasks"] == []
    assert dashboard["pending_reviews"] == []
