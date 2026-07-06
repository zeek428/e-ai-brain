import re

from fastapi.testclient import TestClient
from gitlab_fakes import install_real_gitlab_api_stub

from app.core.login_challenges import MemoryLoginChallengeRepository
from app.core.security import hash_password
from app.core.users import MemoryUserRepository
from app.main import app, settings

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _challenge_answer(question: str) -> str:
    left, right = [int(item) for item in re.findall(r"\d+", question)[:2]]
    return str(left + right)


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


def create_scoped_permission_user_for_scope(
    headers: dict[str, str],
    *,
    access_level: str = "write",
    permissions: list[str],
    role_prefix: str,
    scope_id: str,
    scope_type: str,
) -> dict[str, str]:
    suffix = len(getattr(app.state.user_repository, "users", {})) + 1
    role_code = f"{role_prefix}_{suffix}"
    role = client.post(
        "/api/system/roles",
        json={"code": role_code, "name": role_prefix.replace("_", " ").title()},
        headers=headers,
    )
    assert role.status_code == 200, role.text
    granted = client.put(
        f"/api/system/roles/{role.json()['data']['id']}/permissions",
        json={"permission_codes": permissions},
        headers=headers,
    )
    assert granted.status_code == 200, granted.text
    username = f"{role_code}@example.com"
    created = client.post(
        "/api/users",
        json={
            "display_name": role_prefix.replace("_", " ").title(),
            "password": "password123",
            "roles": ["viewer"],
            "status": "active",
            "username": username,
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    user = created.json()["data"]
    assigned = client.put(
        f"/api/users/{user['id']}/roles",
        json={"role_codes": [role_code]},
        headers=headers,
    )
    assert assigned.status_code == 200, assigned.text
    scoped = client.put(
        f"/api/users/{user['id']}/scopes",
        json={
            "scopes": [
                {
                    "access_level": access_level,
                    "scope_id": scope_id,
                    "scope_type": scope_type,
                }
            ]
        },
        headers=headers,
    )
    assert scoped.status_code == 200, scoped.text
    return auth_headers(username, "password123")


def create_scoped_permission_user(
    headers: dict[str, str],
    *,
    access_level: str = "write",
    permissions: list[str],
    product_id: str,
    role_prefix: str,
) -> dict[str, str]:
    return create_scoped_permission_user_for_scope(
        headers,
        access_level=access_level,
        permissions=permissions,
        role_prefix=role_prefix,
        scope_id=product_id,
        scope_type="product",
    )


def create_manual_scheduled_job(
    headers: dict[str, str],
    *,
    name: str,
    product_id: str,
) -> dict:
    suffix = f"{product_id}_{len(app.state.store.plugin_actions) + 1}"
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "business_system",
            "code": f"scheduled_scope_plugin_{suffix}",
            "name": f"{name} 插件",
            "protocol": "http",
            "status": "active",
        },
        headers=headers,
    )
    assert plugin.status_code == 200, plugin.text
    plugin_data = plugin.json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://scheduled-scope.example.com",
            "name": f"{name} 连接",
            "plugin_id": plugin_data["id"],
            "status": "active",
        },
        headers=headers,
    )
    assert connection.status_code == 200, connection.text
    connection_data = connection.json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": f"scheduled_scope_action_{suffix}",
            "connection_id": connection_data["id"],
            "name": f"{name} 动作",
            "plugin_id": plugin_data["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {"records_imported": 0},
                "path": "/scope",
            },
            "result_mapping": {
                "records_imported_path": "$.records_imported",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=headers,
    )
    assert action.status_code == 200, action.text
    action_data = action.json()["data"]
    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "name": name,
            "plugin_action_id": action_data["id"],
            "plugin_action_ids": [action_data["id"]],
            "plugin_connection_id": connection_data["id"],
            "plugin_connection_ids": [connection_data["id"]],
            "plugin_output_mapping": {
                "records_imported_path": "$.records_imported",
                "write_target": "scheduled_job_result",
            },
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
        "result_summary": {
            "execution_nodes": {
                "result_action": {
                    "feedback": {
                        "records_imported": 1,
                        "write_preview": {
                            "records_imported": 1,
                            "write_target": "scheduled_job_result",
                        },
                    },
                    "records_imported": 1,
                    "status": "succeeded",
                    "write_target": "scheduled_job_result",
                }
            }
        },
        "scheduled_for": "2026-06-27T10:00:00+00:00",
        "scheduled_job_id": job["id"],
        "source_run_id": None,
        "started_at": "2026-06-27T10:00:00+00:00",
        "status": "succeeded",
        "tool_policy_snapshot": {},
        "trigger_type": "manual",
        "updated_at": "2026-06-27T10:01:00+00:00",
    }


def add_plugin_invocation_log(job: dict, *, log_id: str, run_id: str) -> None:
    action = app.state.store.plugin_actions.get(str(job.get("plugin_action_id") or ""))
    app.state.store.plugin_invocation_logs[log_id] = {
        "action_id": job.get("plugin_action_id"),
        "connection_id": job.get("plugin_connection_id"),
        "created_at": "2026-06-27T10:00:30+00:00",
        "created_by": "user_admin",
        "error_code": None,
        "error_message": None,
        "id": log_id,
        "latency_ms": 42,
        "plugin_id": action.get("plugin_id") if isinstance(action, dict) else None,
        "request_summary": {},
        "response_summary": {},
        "scheduled_job_id": job["id"],
        "scheduled_job_run_id": run_id,
        "status": "succeeded",
        "trace_id": f"trace_{log_id}",
        "trigger_type": "scheduled_job",
        "updated_at": "2026-06-27T10:00:31+00:00",
    }


def add_failed_scheduled_job_run(job: dict, *, run_id: str) -> None:
    add_scheduled_job_run(job, run_id=run_id)
    app.state.store.scheduled_job_runs[run_id].update(
        {
            "error_code": "HIDDEN_PRODUCT_FAILURE",
            "error_message": "隐藏产品作业失败",
            "finished_at": "2026-06-27T10:03:00+00:00",
            "status": "failed",
            "updated_at": "2026-06-27T10:03:00+00:00",
        },
    )


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


def create_product_git_repository(
    headers: dict[str, str],
    *,
    product_id: str,
    name: str,
    project_path: str,
) -> dict:
    response = client.post(
        f"/api/products/{product_id}/git-repositories",
        json={
            "git_provider": "github",
            "name": name,
            "project_path": project_path,
            "remote_url": f"https://github.com/{project_path}.git",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create_product_version(
    headers: dict[str, str],
    *,
    code: str,
    name: str,
    product_id: str,
) -> dict:
    response = client.post(
        f"/api/products/{product_id}/versions",
        json={"code": code, "name": name},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create_product_version_branch_config(
    headers: dict[str, str],
    *,
    repository_id: str,
    version_id: str,
    working_branch: str,
) -> dict:
    response = client.post(
        f"/api/product-versions/{version_id}/branch-configs",
        json={
            "repository_id": repository_id,
            "working_branch": working_branch,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create_related_system(
    headers: dict[str, str],
    *,
    code: str,
    name: str,
    product_id: str,
) -> dict:
    response = client.post(
        "/api/system/related-systems",
        json={
            "code": code,
            "name": name,
            "product_id": product_id,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create_product_module(
    headers: dict[str, str],
    *,
    code: str,
    name: str,
    product_id: str,
) -> dict:
    response = client.post(
        f"/api/products/{product_id}/modules",
        json={
            "code": code,
            "name": name,
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


def add_ai_executor_task(job: dict, *, run_id: str, task_id: str) -> None:
    app.state.store.ai_executor_tasks[task_id] = {
        "ai_task_id": None,
        "claimed_at": None,
        "created_at": "2026-06-27T10:00:00+00:00",
        "created_by": "user_admin",
        "error_code": None,
        "error_message": None,
        "executor_type": "codex",
        "finished_at": None,
        "id": task_id,
        "input_payload": {},
        "instruction": f"Run {job['name']}",
        "logs": [{"level": "info", "message": job["name"], "sequence": 1}],
        "plugin_invocation_log_id": None,
        "request_config": {},
        "result_json": {},
        "runner_id": "runner_scope_contract",
        "scheduled_job_id": job["id"],
        "scheduled_job_run_id": run_id,
        "status": "queued",
        "timeout_seconds": 300,
        "updated_at": "2026-06-27T10:00:00+00:00",
        "workspace_root": "/workspace",
    }


def test_system_admin_pages_use_permission_points_instead_of_admin_role():
    admin_headers = auth_headers()
    suffix = len(getattr(app.state.store, "products", {})) + 1
    product = client.post(
        "/api/products",
        json={"code": f"system-permission-scope-{suffix}", "name": "系统权限点验证产品"},
        headers=admin_headers,
    )
    assert product.status_code == 200, product.text
    permission_headers = create_scoped_permission_user(
        admin_headers,
        permissions=["audit.read", "system.model_gateway.manage", "system.users.manage"],
        product_id=product.json()["data"]["id"],
        role_prefix="system_permission",
    )
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    users_response = client.get(
        "/api/users?page=1&page_size=10",
        headers=permission_headers,
    )
    assert users_response.status_code == 200, users_response.text

    model_gateway_list = client.get(
        "/api/system/model-gateway-configs?page=1&page_size=10",
        headers=permission_headers,
    )
    assert model_gateway_list.status_code == 200, model_gateway_list.text
    model_gateway_create = client.post(
        "/api/system/model-gateway-configs",
        json={
            "base_url": "http://127.0.0.1:8080/v1",
            "default_chat_model": "gpt-5.5",
            "embedding_connection_mode": "disabled",
            "name": "权限点模型网关",
            "provider": "openai_compatible",
            "status": "active",
        },
        headers=permission_headers,
    )
    assert model_gateway_create.status_code == 200, model_gateway_create.text

    audit_response = client.get(
        "/api/audit/events?page=1&page_size=10",
        headers=permission_headers,
    )
    assert audit_response.status_code == 200, audit_response.text

    assert client.get("/api/users", headers=reviewer_headers).status_code == 403
    reviewer_model_gateway = client.get(
        "/api/system/model-gateway-configs",
        headers=reviewer_headers,
    )
    assert reviewer_model_gateway.status_code == 403
    assert client.get("/api/audit/events", headers=reviewer_headers).status_code == 403


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


def test_knowledge_deposit_review_uses_permission_point_not_role_name():
    app.state.store.reset()
    admin_headers = auth_headers()
    suffix = len(getattr(app.state.user_repository, "users", {})) + 1
    role_code = f"knowledge_deposit_decider_{suffix}"
    viewer_username = f"knowledge-deposit-viewer-{suffix}@example.com"
    username = f"knowledge-deposit-decider-{suffix}@example.com"

    role = client.post(
        "/api/system/roles",
        json={"code": role_code, "name": "Knowledge Deposit Decider"},
        headers=admin_headers,
    )
    assert role.status_code == 200, role.text
    role_id = role.json()["data"]["id"]
    granted = client.put(
        f"/api/system/roles/{role_id}/permissions",
        json={"permission_codes": ["knowledge.deposit.decide"]},
        headers=admin_headers,
    )
    assert granted.status_code == 200, granted.text
    created_user = client.post(
        "/api/users",
        json={
            "display_name": "Knowledge Deposit Decider",
            "password": "password123",
            "roles": ["viewer"],
            "status": "active",
            "username": username,
        },
        headers=admin_headers,
    )
    assert created_user.status_code == 200, created_user.text
    user_id = created_user.json()["data"]["id"]
    assigned = client.put(
        f"/api/users/{user_id}/roles",
        json={"role_codes": [role_code]},
        headers=admin_headers,
    )
    assert assigned.status_code == 200, assigned.text
    viewer_user = client.post(
        "/api/users",
        json={
            "display_name": "Knowledge Deposit Viewer",
            "password": "password123",
            "roles": ["viewer"],
            "status": "active",
            "username": viewer_username,
        },
        headers=admin_headers,
    )
    assert viewer_user.status_code == 200, viewer_user.text

    viewer_response = client.get(
        "/api/knowledge/deposits?page=1&page_size=10",
        headers=auth_headers(viewer_username, "password123"),
    )
    assert viewer_response.status_code == 403
    assert viewer_response.json()["detail"]["code"] == "FORBIDDEN"

    decider_response = client.get(
        "/api/knowledge/deposits?page=1&page_size=10",
        headers=auth_headers(username, "password123"),
    )
    assert decider_response.status_code == 200, decider_response.text
    assert "items" in decider_response.json()["data"]


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


def test_p0_management_routes_have_permission_and_scope_contract_matrix():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    openapi_paths = client.get("/openapi.json").json()["paths"]

    product_a = create_product(
        admin_headers,
        code="p0-route-scope-a",
        name="P0 Route Scope A",
    )
    product_b = create_product(
        admin_headers,
        code="p0-route-scope-b",
        name="P0 Route Scope B",
    )
    requirement_a = create_requirement(
        admin_headers,
        product_id=product_a["id"],
        title="P0 A 产品需求",
    )
    requirement_b = create_requirement(
        admin_headers,
        product_id=product_b["id"],
        title="P0 B 产品需求",
    )
    bug_a = create_bug(admin_headers, product_id=product_a["id"], title="P0 A 产品 Bug")
    bug_b = create_bug(admin_headers, product_id=product_b["id"], title="P0 B 产品 Bug")
    add_code_inspection_report(
        report_id="p0_code_inspection_scope_a",
        product_id=product_a["id"],
        title="P0 A 产品巡检",
    )
    add_code_inspection_report(
        report_id="p0_code_inspection_scope_b",
        product_id=product_b["id"],
        title="P0 B 产品巡检",
    )

    knowledge_space_a = "p0_knowledge_space_scope_a"
    knowledge_space_b = "p0_knowledge_space_scope_b"
    app.state.store.knowledge_spaces[knowledge_space_a] = {
        "code": "p0-knowledge-a",
        "created_at": "2026-06-27T10:00:00+00:00",
        "description": "A 知识空间",
        "id": knowledge_space_a,
        "name": "P0 A 知识空间",
        "owner_user_id": "user_admin",
        "status": "active",
        "updated_at": "2026-06-27T10:00:00+00:00",
    }
    app.state.store.knowledge_spaces[knowledge_space_b] = {
        "code": "p0-knowledge-b",
        "created_at": "2026-06-27T10:00:00+00:00",
        "description": "B 知识空间",
        "id": knowledge_space_b,
        "name": "P0 B 知识空间",
        "owner_user_id": "user_admin",
        "status": "active",
        "updated_at": "2026-06-27T10:00:00+00:00",
    }
    app.state.store.knowledge_documents["p0_knowledge_document_scope_a"] = {
        "content": "A 知识空间文档",
        "created_at": "2026-06-27T10:00:00+00:00",
        "doc_type": "manual",
        "folder_id": None,
        "id": "p0_knowledge_document_scope_a",
        "index_error": None,
        "index_status": "indexed",
        "knowledge_space_id": knowledge_space_a,
        "permission_roles": [],
        "permission_scope": {"knowledge_space_id": knowledge_space_a},
        "product_id": product_a["id"],
        "source_type": "manual",
        "title": "P0 A 知识文档",
        "updated_at": "2026-06-27T10:00:00+00:00",
    }
    app.state.store.knowledge_documents["p0_knowledge_document_scope_b"] = {
        "content": "B 知识空间文档",
        "created_at": "2026-06-27T10:00:00+00:00",
        "doc_type": "manual",
        "folder_id": None,
        "id": "p0_knowledge_document_scope_b",
        "index_error": None,
        "index_status": "indexed",
        "knowledge_space_id": knowledge_space_b,
        "permission_roles": [],
        "permission_scope": {"knowledge_space_id": knowledge_space_b},
        "product_id": product_b["id"],
        "source_type": "manual",
        "title": "P0 B 知识文档",
        "updated_at": "2026-06-27T10:00:00+00:00",
    }

    job_a = create_manual_scheduled_job(
        admin_headers,
        name="P0 A 产品作业",
        product_id=product_a["id"],
    )
    job_b = create_manual_scheduled_job(
        admin_headers,
        name="P0 B 产品作业",
        product_id=product_b["id"],
    )
    add_scheduled_job_run(job_a, run_id="p0_scheduled_run_scope_a")
    add_scheduled_job_run(job_b, run_id="p0_scheduled_run_scope_b")
    add_plugin_invocation_log(
        job_a,
        log_id="p0_plugin_invocation_scope_a",
        run_id="p0_scheduled_run_scope_a",
    )
    add_plugin_invocation_log(
        job_b,
        log_id="p0_plugin_invocation_scope_b",
        run_id="p0_scheduled_run_scope_b",
    )
    add_ai_executor_task(
        job_a,
        run_id="p0_scheduled_run_scope_a",
        task_id="p0_ai_executor_task_scope_a",
    )
    add_ai_executor_task(
        job_b,
        run_id="p0_scheduled_run_scope_b",
        task_id="p0_ai_executor_task_scope_b",
    )

    delivery_headers = create_scoped_role_user(
        admin_headers,
        product_id=product_a["id"],
        role_code="product_owner",
    )
    knowledge_headers = create_scoped_permission_user_for_scope(
        admin_headers,
        access_level="read",
        permissions=["knowledge.read"],
        role_prefix="p0_knowledge_reader",
        scope_id=knowledge_space_a,
        scope_type="knowledge_space",
    )
    scheduled_headers = create_scoped_test_owner(admin_headers, product_id=product_a["id"])
    plugin_headers = create_scoped_permission_user(
        admin_headers,
        access_level="read",
        permissions=["system.plugins.manage"],
        product_id=product_a["id"],
        role_prefix="p0_plugin_operator",
    )

    permission_contracts = [
        ("requirements", "/api/requirements", "requirement.read"),
        ("bugs", "/api/bugs", "bug.read"),
        ("knowledge_documents", "/api/knowledge/documents", "knowledge.read"),
        ("code_inspections", "/api/governance/code-inspections", "code_inspection.read"),
        ("scheduled_jobs", "/api/system/scheduled-jobs", "system.scheduled_jobs.manage"),
        ("plugins", "/api/system/plugins", "system.plugins.manage"),
        ("plugin_connections", "/api/system/plugin-connections", "system.plugins.manage"),
        ("plugin_actions", "/api/system/plugin-actions", "system.plugins.manage"),
        (
            "plugin_invocation_logs",
            "/api/system/plugin-invocation-logs",
            "system.plugins.manage",
        ),
        ("ai_executor_runners", "/api/system/ai-executor-runners", "system.plugins.manage"),
        ("ai_executor_tasks", "/api/system/ai-executor-tasks", "system.plugins.manage"),
    ]
    for domain, path, permission in permission_contracts:
        assert path in openapi_paths, domain
        response = client.get(f"{path}?page=1&page_size=1", headers=reviewer_headers)
        assert response.status_code == 403, f"{domain} should require {permission}"
        assert response.json()["detail"]["code"] == "FORBIDDEN"

    scope_contracts = [
        (
            "requirements",
            "/api/requirements?page=1&page_size=20",
            delivery_headers,
            requirement_a["id"],
            requirement_b["id"],
            "product",
        ),
        (
            "bugs",
            "/api/bugs?page=1&page_size=20",
            delivery_headers,
            bug_a["id"],
            bug_b["id"],
            "product",
        ),
        (
            "code_inspections",
            "/api/governance/code-inspections?page=1&page_size=20",
            delivery_headers,
            "p0_code_inspection_scope_a",
            "p0_code_inspection_scope_b",
            "product",
        ),
        (
            "knowledge_documents",
            "/api/knowledge/documents?page=1&page_size=20",
            knowledge_headers,
            "p0_knowledge_document_scope_a",
            "p0_knowledge_document_scope_b",
            "knowledge_space",
        ),
        (
            "scheduled_jobs",
            "/api/system/scheduled-jobs?page=1&page_size=20",
            scheduled_headers,
            job_a["id"],
            job_b["id"],
            "product",
        ),
        (
            "plugin_invocation_logs",
            "/api/system/plugin-invocation-logs?page=1&page_size=20",
            plugin_headers,
            "p0_plugin_invocation_scope_a",
            "p0_plugin_invocation_scope_b",
            "product",
        ),
        (
            "ai_executor_tasks",
            "/api/system/ai-executor-tasks?page=1&page_size=20",
            plugin_headers,
            "p0_ai_executor_task_scope_a",
            "p0_ai_executor_task_scope_b",
            "product",
        ),
    ]
    for domain, path, headers, visible_id, hidden_id, scope_kind in scope_contracts:
        response = client.get(path, headers=headers)
        assert response.status_code == 200, f"{domain} {scope_kind}: {response.text}"
        item_ids = {item["id"] for item in response.json()["data"]["items"]}
        assert visible_id in item_ids, f"{domain} should expose scope-visible record"
        assert hidden_id not in item_ids, f"{domain} should hide out-of-scope record"


def test_product_git_repository_routes_use_permissions_and_product_scope():
    app.state.store.reset()
    admin_headers = auth_headers()
    product_a = create_product(
        admin_headers,
        code="repo-scope-contract-a",
        name="Repo Scope Contract A",
    )
    product_b = create_product(
        admin_headers,
        code="repo-scope-contract-b",
        name="Repo Scope Contract B",
    )
    repo_a = create_product_git_repository(
        admin_headers,
        product_id=product_a["id"],
        name="A 产品代码库",
        project_path="scope-contract/a",
    )
    repo_b = create_product_git_repository(
        admin_headers,
        product_id=product_b["id"],
        name="B 产品代码库",
        project_path="scope-contract/b",
    )

    suffix = len(getattr(app.state.user_repository, "users", {})) + 1
    role_code = f"product_repo_operator_{suffix}"
    role = client.post(
        "/api/system/roles",
        json={"code": role_code, "name": "Product Repo Operator"},
        headers=admin_headers,
    )
    assert role.status_code == 200, role.text
    granted = client.put(
        f"/api/system/roles/{role.json()['data']['id']}/permissions",
        json={"permission_codes": ["product.read", "product.manage"]},
        headers=admin_headers,
    )
    assert granted.status_code == 200, granted.text
    username = f"{role_code}@example.com"
    created_user = client.post(
        "/api/users",
        json={
            "display_name": "Product Repo Operator",
            "password": "password123",
            "roles": ["viewer"],
            "status": "active",
            "username": username,
        },
        headers=admin_headers,
    )
    assert created_user.status_code == 200, created_user.text
    user_id = created_user.json()["data"]["id"]
    assigned = client.put(
        f"/api/users/{user_id}/roles",
        json={"role_codes": [role_code]},
        headers=admin_headers,
    )
    assert assigned.status_code == 200, assigned.text
    scoped = client.put(
        f"/api/users/{user_id}/scopes",
        json={
            "scopes": [
                {
                    "access_level": "write",
                    "scope_id": product_a["id"],
                    "scope_type": "product",
                }
            ]
        },
        headers=admin_headers,
    )
    assert scoped.status_code == 200, scoped.text
    scoped_headers = auth_headers(username, "password123")

    visible_repositories = client.get(
        f"/api/products/{product_a['id']}/git-repositories",
        headers=scoped_headers,
    )
    assert visible_repositories.status_code == 200, visible_repositories.text
    assert [item["id"] for item in visible_repositories.json()["data"]["items"]] == [
        repo_a["id"]
    ]

    hidden_repositories = client.get(
        f"/api/products/{product_b['id']}/git-repositories",
        headers=scoped_headers,
    )
    assert hidden_repositories.status_code == 404
    assert hidden_repositories.json()["detail"]["code"] == "NOT_FOUND"

    created_visible_repository = client.post(
        f"/api/products/{product_a['id']}/git-repositories",
        json={
            "git_provider": "github",
            "name": "A 产品新增代码库",
            "project_path": "scope-contract/a-extra",
            "remote_url": "https://github.com/scope-contract/a-extra.git",
        },
        headers=scoped_headers,
    )
    assert created_visible_repository.status_code == 200, created_visible_repository.text

    hidden_create = client.post(
        f"/api/products/{product_b['id']}/git-repositories",
        json={
            "git_provider": "github",
            "name": "B 产品新增代码库",
            "project_path": "scope-contract/b-extra",
            "remote_url": "https://github.com/scope-contract/b-extra.git",
        },
        headers=scoped_headers,
    )
    assert hidden_create.status_code == 404
    assert hidden_create.json()["detail"]["code"] == "NOT_FOUND"

    visible_patch = client.patch(
        f"/api/product-git-repositories/{repo_a['id']}",
        json={"default_branch": "develop"},
        headers=scoped_headers,
    )
    assert visible_patch.status_code == 200, visible_patch.text
    assert visible_patch.json()["data"]["default_branch"] == "develop"

    hidden_patch = client.patch(
        f"/api/product-git-repositories/{repo_b['id']}",
        json={"default_branch": "develop"},
        headers=scoped_headers,
    )
    assert hidden_patch.status_code == 404
    assert hidden_patch.json()["detail"]["code"] == "NOT_FOUND"

    hidden_delete = client.delete(
        f"/api/product-git-repositories/{repo_b['id']}",
        headers=scoped_headers,
    )
    assert hidden_delete.status_code == 404
    assert hidden_delete.json()["detail"]["code"] == "NOT_FOUND"


def test_related_system_routes_use_permissions_and_product_scope():
    app.state.store.reset()
    admin_headers = auth_headers()
    product_a = create_product(
        admin_headers,
        code="system-scope-contract-a",
        name="System Scope Contract A",
    )
    product_b = create_product(
        admin_headers,
        code="system-scope-contract-b",
        name="System Scope Contract B",
    )
    system_a = create_related_system(
        admin_headers,
        code="scope-system-a",
        name="A 产品相关系统",
        product_id=product_a["id"],
    )
    system_b = create_related_system(
        admin_headers,
        code="scope-system-b",
        name="B 产品相关系统",
        product_id=product_b["id"],
    )

    suffix = len(getattr(app.state.user_repository, "users", {})) + 1
    role_code = f"related_system_operator_{suffix}"
    role = client.post(
        "/api/system/roles",
        json={"code": role_code, "name": "Related System Operator"},
        headers=admin_headers,
    )
    assert role.status_code == 200, role.text
    granted = client.put(
        f"/api/system/roles/{role.json()['data']['id']}/permissions",
        json={"permission_codes": ["product.read", "product.manage"]},
        headers=admin_headers,
    )
    assert granted.status_code == 200, granted.text
    username = f"{role_code}@example.com"
    created_user = client.post(
        "/api/users",
        json={
            "display_name": "Related System Operator",
            "password": "password123",
            "roles": ["viewer"],
            "status": "active",
            "username": username,
        },
        headers=admin_headers,
    )
    assert created_user.status_code == 200, created_user.text
    user_id = created_user.json()["data"]["id"]
    assigned = client.put(
        f"/api/users/{user_id}/roles",
        json={"role_codes": [role_code]},
        headers=admin_headers,
    )
    assert assigned.status_code == 200, assigned.text
    scoped = client.put(
        f"/api/users/{user_id}/scopes",
        json={
            "scopes": [
                {
                    "access_level": "write",
                    "scope_id": product_a["id"],
                    "scope_type": "product",
                }
            ]
        },
        headers=admin_headers,
    )
    assert scoped.status_code == 200, scoped.text
    scoped_headers = auth_headers(username, "password123")

    visible_systems = client.get(
        f"/api/system/related-systems?product_id={product_a['id']}",
        headers=scoped_headers,
    )
    assert visible_systems.status_code == 200, visible_systems.text
    assert [item["id"] for item in visible_systems.json()["data"]["items"]] == [system_a["id"]]

    hidden_product_systems = client.get(
        f"/api/system/related-systems?product_id={product_b['id']}",
        headers=scoped_headers,
    )
    assert hidden_product_systems.status_code == 404
    assert hidden_product_systems.json()["detail"]["code"] == "NOT_FOUND"

    visible_all_systems = client.get("/api/system/related-systems", headers=scoped_headers)
    assert visible_all_systems.status_code == 200, visible_all_systems.text
    visible_ids = {item["id"] for item in visible_all_systems.json()["data"]["items"]}
    assert system_a["id"] in visible_ids
    assert system_b["id"] not in visible_ids

    created_visible_system = client.post(
        "/api/system/related-systems",
        json={
            "code": "scope-system-a-extra",
            "name": "A 产品新增相关系统",
            "product_id": product_a["id"],
        },
        headers=scoped_headers,
    )
    assert created_visible_system.status_code == 200, created_visible_system.text

    hidden_create = client.post(
        "/api/system/related-systems",
        json={
            "code": "scope-system-b-extra",
            "name": "B 产品新增相关系统",
            "product_id": product_b["id"],
        },
        headers=scoped_headers,
    )
    assert hidden_create.status_code == 404
    assert hidden_create.json()["detail"]["code"] == "NOT_FOUND"

    visible_patch = client.patch(
        f"/api/system/related-systems/{system_a['id']}",
        json={"owner_team": "A 产品团队"},
        headers=scoped_headers,
    )
    assert visible_patch.status_code == 200, visible_patch.text
    assert visible_patch.json()["data"]["owner_team"] == "A 产品团队"

    hidden_rebind = client.patch(
        f"/api/system/related-systems/{system_a['id']}",
        json={"product_id": product_b["id"]},
        headers=scoped_headers,
    )
    assert hidden_rebind.status_code == 404
    assert hidden_rebind.json()["detail"]["code"] == "NOT_FOUND"

    hidden_patch = client.patch(
        f"/api/system/related-systems/{system_b['id']}",
        json={"owner_team": "B 产品团队"},
        headers=scoped_headers,
    )
    assert hidden_patch.status_code == 404
    assert hidden_patch.json()["detail"]["code"] == "NOT_FOUND"

    hidden_delete = client.delete(
        f"/api/system/related-systems/{system_b['id']}",
        headers=scoped_headers,
    )
    assert hidden_delete.status_code == 404
    assert hidden_delete.json()["detail"]["code"] == "NOT_FOUND"


def test_product_module_routes_use_permissions_and_product_scope():
    app.state.store.reset()
    admin_headers = auth_headers()
    product_a = create_product(
        admin_headers,
        code="module-scope-contract-a",
        name="Module Scope Contract A",
    )
    product_b = create_product(
        admin_headers,
        code="module-scope-contract-b",
        name="Module Scope Contract B",
    )
    module_a = create_product_module(
        admin_headers,
        code="scope-module-a",
        name="A 产品模块",
        product_id=product_a["id"],
    )
    module_b = create_product_module(
        admin_headers,
        code="scope-module-b",
        name="B 产品模块",
        product_id=product_b["id"],
    )

    suffix = len(getattr(app.state.user_repository, "users", {})) + 1
    role_code = f"product_module_operator_{suffix}"
    role = client.post(
        "/api/system/roles",
        json={"code": role_code, "name": "Product Module Operator"},
        headers=admin_headers,
    )
    assert role.status_code == 200, role.text
    granted = client.put(
        f"/api/system/roles/{role.json()['data']['id']}/permissions",
        json={"permission_codes": ["product.read", "product.manage"]},
        headers=admin_headers,
    )
    assert granted.status_code == 200, granted.text
    username = f"{role_code}@example.com"
    created_user = client.post(
        "/api/users",
        json={
            "display_name": "Product Module Operator",
            "password": "password123",
            "roles": ["viewer"],
            "status": "active",
            "username": username,
        },
        headers=admin_headers,
    )
    assert created_user.status_code == 200, created_user.text
    user_id = created_user.json()["data"]["id"]
    assigned = client.put(
        f"/api/users/{user_id}/roles",
        json={"role_codes": [role_code]},
        headers=admin_headers,
    )
    assert assigned.status_code == 200, assigned.text
    scoped = client.put(
        f"/api/users/{user_id}/scopes",
        json={
            "scopes": [
                {
                    "access_level": "write",
                    "scope_id": product_a["id"],
                    "scope_type": "product",
                }
            ]
        },
        headers=admin_headers,
    )
    assert scoped.status_code == 200, scoped.text
    scoped_headers = auth_headers(username, "password123")

    visible_modules = client.get(
        f"/api/products/{product_a['id']}/modules",
        headers=scoped_headers,
    )
    assert visible_modules.status_code == 200, visible_modules.text
    assert [item["id"] for item in visible_modules.json()["data"]["items"]] == [
        module_a["id"]
    ]

    hidden_modules = client.get(
        f"/api/products/{product_b['id']}/modules",
        headers=scoped_headers,
    )
    assert hidden_modules.status_code == 404
    assert hidden_modules.json()["detail"]["code"] == "NOT_FOUND"

    created_visible_module = client.post(
        f"/api/products/{product_a['id']}/modules",
        json={"code": "scope-module-a-extra", "name": "A 产品新增模块"},
        headers=scoped_headers,
    )
    assert created_visible_module.status_code == 200, created_visible_module.text

    hidden_create = client.post(
        f"/api/products/{product_b['id']}/modules",
        json={"code": "scope-module-b-extra", "name": "B 产品新增模块"},
        headers=scoped_headers,
    )
    assert hidden_create.status_code == 404
    assert hidden_create.json()["detail"]["code"] == "NOT_FOUND"

    visible_patch = client.patch(
        f"/api/product-modules/{module_a['id']}",
        json={"owner_team": "A 产品团队"},
        headers=scoped_headers,
    )
    assert visible_patch.status_code == 200, visible_patch.text
    assert visible_patch.json()["data"]["owner_team"] == "A 产品团队"

    hidden_patch = client.patch(
        f"/api/product-modules/{module_b['id']}",
        json={"owner_team": "B 产品团队"},
        headers=scoped_headers,
    )
    assert hidden_patch.status_code == 404
    assert hidden_patch.json()["detail"]["code"] == "NOT_FOUND"

    hidden_delete = client.delete(
        f"/api/product-modules/{module_b['id']}",
        headers=scoped_headers,
    )
    assert hidden_delete.status_code == 404
    assert hidden_delete.json()["detail"]["code"] == "NOT_FOUND"


def test_product_and_version_routes_use_permissions_and_product_scope():
    app.state.store.reset()
    admin_headers = auth_headers()
    product_a = create_product(
        admin_headers,
        code="product-version-scope-a",
        name="Product Version Scope A",
    )
    product_b = create_product(
        admin_headers,
        code="product-version-scope-b",
        name="Product Version Scope B",
    )
    version_a = create_product_version(
        admin_headers,
        code="version-scope-a",
        name="A 产品迭代",
        product_id=product_a["id"],
    )
    version_b = create_product_version(
        admin_headers,
        code="version-scope-b",
        name="B 产品迭代",
        product_id=product_b["id"],
    )
    scoped_headers = create_scoped_permission_user(
        admin_headers,
        permissions=["product.read", "product.manage"],
        product_id=product_a["id"],
        role_prefix="product_version_operator",
    )

    scoped_products = client.get(
        "/api/products?page=1&page_size=20",
        headers=scoped_headers,
    )
    assert scoped_products.status_code == 200, scoped_products.text
    assert [item["id"] for item in scoped_products.json()["data"]["items"]] == [
        product_a["id"]
    ]

    visible_product = client.get(f"/api/products/{product_a['id']}", headers=scoped_headers)
    assert visible_product.status_code == 200, visible_product.text
    hidden_product = client.get(f"/api/products/{product_b['id']}", headers=scoped_headers)
    assert hidden_product.status_code == 404
    assert hidden_product.json()["detail"]["code"] == "NOT_FOUND"

    visible_product_patch = client.patch(
        f"/api/products/{product_a['id']}",
        json={"owner_team": "A 产品团队"},
        headers=scoped_headers,
    )
    assert visible_product_patch.status_code == 200, visible_product_patch.text
    hidden_product_patch = client.patch(
        f"/api/products/{product_b['id']}",
        json={"owner_team": "B 产品团队"},
        headers=scoped_headers,
    )
    assert hidden_product_patch.status_code == 404
    assert hidden_product_patch.json()["detail"]["code"] == "NOT_FOUND"

    scoped_product_create = client.post(
        "/api/products",
        json={"code": "product-version-scope-c", "name": "Scoped User Product Create"},
        headers=scoped_headers,
    )
    assert scoped_product_create.status_code == 403
    assert scoped_product_create.json()["detail"]["code"] == "FORBIDDEN"

    scoped_versions = client.get(
        "/api/product-versions?page=1&page_size=20",
        headers=scoped_headers,
    )
    assert scoped_versions.status_code == 200, scoped_versions.text
    assert [item["id"] for item in scoped_versions.json()["data"]["items"]] == [
        version_a["id"]
    ]

    visible_versions = client.get(
        f"/api/products/{product_a['id']}/versions",
        headers=scoped_headers,
    )
    assert visible_versions.status_code == 200, visible_versions.text
    assert [item["id"] for item in visible_versions.json()["data"]["items"]] == [
        version_a["id"]
    ]
    hidden_versions = client.get(
        f"/api/products/{product_b['id']}/versions",
        headers=scoped_headers,
    )
    assert hidden_versions.status_code == 404
    assert hidden_versions.json()["detail"]["code"] == "NOT_FOUND"

    visible_create = client.post(
        f"/api/products/{product_a['id']}/versions",
        json={"code": "version-scope-a-extra", "name": "A 产品新增迭代"},
        headers=scoped_headers,
    )
    assert visible_create.status_code == 200, visible_create.text
    hidden_create = client.post(
        f"/api/products/{product_b['id']}/versions",
        json={"code": "version-scope-b-extra", "name": "B 产品新增迭代"},
        headers=scoped_headers,
    )
    assert hidden_create.status_code == 404
    assert hidden_create.json()["detail"]["code"] == "NOT_FOUND"

    visible_version_patch = client.patch(
        f"/api/product-versions/{version_a['id']}",
        json={"description": "A 产品迭代说明"},
        headers=scoped_headers,
    )
    assert visible_version_patch.status_code == 200, visible_version_patch.text
    hidden_version_patch = client.patch(
        f"/api/product-versions/{version_b['id']}",
        json={"description": "B 产品迭代说明"},
        headers=scoped_headers,
    )
    assert hidden_version_patch.status_code == 404
    assert hidden_version_patch.json()["detail"]["code"] == "NOT_FOUND"

    hidden_advance = client.post(
        f"/api/product-versions/{version_b['id']}/advance-status",
        json={"preview_only": True, "target_status": "active"},
        headers=scoped_headers,
    )
    assert hidden_advance.status_code == 404
    assert hidden_advance.json()["detail"]["code"] == "NOT_FOUND"

    hidden_delete = client.delete(
        f"/api/product-versions/{version_b['id']}",
        headers=scoped_headers,
    )
    assert hidden_delete.status_code == 404
    assert hidden_delete.json()["detail"]["code"] == "NOT_FOUND"


def test_product_version_branch_routes_use_permissions_and_product_scope():
    app.state.store.reset()
    admin_headers = auth_headers()
    product_a = create_product(
        admin_headers,
        code="branch-scope-contract-a",
        name="Branch Scope Contract A",
    )
    product_b = create_product(
        admin_headers,
        code="branch-scope-contract-b",
        name="Branch Scope Contract B",
    )
    version_a = create_product_version(
        admin_headers,
        code="branch-version-a",
        name="A 产品分支迭代",
        product_id=product_a["id"],
    )
    version_b = create_product_version(
        admin_headers,
        code="branch-version-b",
        name="B 产品分支迭代",
        product_id=product_b["id"],
    )
    repo_a = create_product_git_repository(
        admin_headers,
        product_id=product_a["id"],
        name="A 产品代码库",
        project_path="branch-scope/a",
    )
    repo_b = create_product_git_repository(
        admin_headers,
        product_id=product_b["id"],
        name="B 产品代码库",
        project_path="branch-scope/b",
    )
    branch_b = create_product_version_branch_config(
        admin_headers,
        repository_id=repo_b["id"],
        version_id=version_b["id"],
        working_branch="feature/b-scope",
    )
    scoped_headers = create_scoped_permission_user(
        admin_headers,
        permissions=["product.read", "product.manage"],
        product_id=product_a["id"],
        role_prefix="product_branch_operator",
    )

    visible_branch_list = client.get(
        f"/api/product-versions/{version_a['id']}/branch-configs",
        headers=scoped_headers,
    )
    assert visible_branch_list.status_code == 200, visible_branch_list.text
    assert visible_branch_list.json()["data"]["items"] == []

    hidden_branch_list = client.get(
        f"/api/product-versions/{version_b['id']}/branch-configs",
        headers=scoped_headers,
    )
    assert hidden_branch_list.status_code == 404
    assert hidden_branch_list.json()["detail"]["code"] == "NOT_FOUND"

    branch_a = client.post(
        f"/api/product-versions/{version_a['id']}/branch-configs",
        json={"repository_id": repo_a["id"], "working_branch": "feature/a-scope"},
        headers=scoped_headers,
    )
    assert branch_a.status_code == 200, branch_a.text

    hidden_repository = client.post(
        f"/api/product-versions/{version_a['id']}/branch-configs",
        json={"repository_id": repo_b["id"], "working_branch": "feature/leak"},
        headers=scoped_headers,
    )
    assert hidden_repository.status_code == 404
    assert hidden_repository.json()["detail"]["code"] == "NOT_FOUND"

    hidden_version = client.post(
        f"/api/product-versions/{version_b['id']}/branch-configs",
        json={"repository_id": repo_b["id"], "working_branch": "feature/hidden"},
        headers=scoped_headers,
    )
    assert hidden_version.status_code == 404
    assert hidden_version.json()["detail"]["code"] == "NOT_FOUND"

    visible_patch = client.patch(
        f"/api/product-version-branch-configs/{branch_a.json()['data']['id']}",
        json={"branch_status": "active"},
        headers=scoped_headers,
    )
    assert visible_patch.status_code == 200, visible_patch.text
    assert visible_patch.json()["data"]["branch_status"] == "active"

    hidden_patch = client.patch(
        f"/api/product-version-branch-configs/{branch_b['id']}",
        json={"branch_status": "active"},
        headers=scoped_headers,
    )
    assert hidden_patch.status_code == 404
    assert hidden_patch.json()["detail"]["code"] == "NOT_FOUND"

    hidden_delete = client.delete(
        f"/api/product-version-branch-configs/{branch_b['id']}",
        headers=scoped_headers,
    )
    assert hidden_delete.status_code == 404
    assert hidden_delete.json()["detail"]["code"] == "NOT_FOUND"


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
        "/api/system/result-write-records",
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
    add_failed_scheduled_job_run(job_b, run_id="scheduled_run_scope_b")
    add_plugin_invocation_log(
        job_a,
        log_id="plugin_invocation_scope_a",
        run_id="scheduled_run_scope_a",
    )
    add_plugin_invocation_log(
        job_b,
        log_id="plugin_invocation_scope_b",
        run_id="scheduled_run_scope_b",
    )
    add_ai_executor_task(
        job_a,
        run_id="scheduled_run_scope_a",
        task_id="ai_executor_task_scope_a",
    )
    add_ai_executor_task(
        job_b,
        run_id="scheduled_run_scope_b",
        task_id="ai_executor_task_scope_b",
    )

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

    scoped_observability = client.get(
        "/api/system/scheduled-job-runs/observability",
        headers=scoped_headers,
    )
    assert scoped_observability.status_code == 200, scoped_observability.text
    scoped_observability_data = scoped_observability.json()["data"]
    assert scoped_observability_data["summary"]["total_runs"] == 1
    assert scoped_observability_data["summary"]["succeeded_runs"] == 1
    assert scoped_observability_data["summary"]["failed_runs"] == 0
    assert scoped_observability_data["error_distribution"] == []
    assert scoped_observability_data["recent_failures"] == []
    assert [item["id"] for item in scoped_observability_data["slow_runs"]] == [
        "scheduled_run_scope_a",
    ]

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

    suffix = len(getattr(app.state.user_repository, "users", {})) + 1
    role_code = f"runner_task_scope_operator_{suffix}"
    role = client.post(
        "/api/system/roles",
        json={"code": role_code, "name": "Runner Task Scope Operator"},
        headers=admin_headers,
    )
    assert role.status_code == 200, role.text
    granted = client.put(
        f"/api/system/roles/{role.json()['data']['id']}/permissions",
        json={"permission_codes": ["system.plugins.manage"]},
        headers=admin_headers,
    )
    assert granted.status_code == 200, granted.text
    username = f"{role_code}-scope@example.com"
    created_user = client.post(
        "/api/users",
        json={
            "display_name": "Runner Task Scope Operator",
            "password": "password123",
            "roles": ["viewer"],
            "status": "active",
            "username": username,
        },
        headers=admin_headers,
    )
    assert created_user.status_code == 200, created_user.text
    user_id = created_user.json()["data"]["id"]
    assigned = client.put(
        f"/api/users/{user_id}/roles",
        json={"role_codes": [role_code]},
        headers=admin_headers,
    )
    assert assigned.status_code == 200, assigned.text
    scoped = client.put(
        f"/api/users/{user_id}/scopes",
        json={
            "scopes": [
                {
                    "access_level": "read",
                    "scope_id": product_a["id"],
                    "scope_type": "product",
                }
            ]
        },
        headers=admin_headers,
    )
    assert scoped.status_code == 200, scoped.text
    scoped_plugin_headers = auth_headers(username, "password123")
    scoped_tasks = client.get(
        "/api/system/ai-executor-tasks?page=1&page_size=20",
        headers=scoped_plugin_headers,
    )
    assert scoped_tasks.status_code == 200, scoped_tasks.text
    task_ids = {item["id"] for item in scoped_tasks.json()["data"]["items"]}
    assert "ai_executor_task_scope_a" in task_ids
    assert "ai_executor_task_scope_b" not in task_ids

    scoped_invocation_logs = client.get(
        "/api/system/plugin-invocation-logs?page=1&page_size=20",
        headers=scoped_plugin_headers,
    )
    assert scoped_invocation_logs.status_code == 200, scoped_invocation_logs.text
    invocation_log_ids = {
        item["id"] for item in scoped_invocation_logs.json()["data"]["items"]
    }
    assert "plugin_invocation_scope_a" in invocation_log_ids
    assert "plugin_invocation_scope_b" not in invocation_log_ids

    hidden_invocation_logs = client.get(
        f"/api/system/plugin-invocation-logs?scheduled_job_id={job_b['id']}",
        headers=scoped_plugin_headers,
    )
    assert hidden_invocation_logs.status_code == 200, hidden_invocation_logs.text
    assert hidden_invocation_logs.json()["data"]["items"] == []

    scoped_result_write_records = client.get(
        "/api/system/result-write-records?write_target=scheduled_job_result",
        headers=scoped_plugin_headers,
    )
    assert scoped_result_write_records.status_code == 200, scoped_result_write_records.text
    result_write_record_ids = {
        item["id"] for item in scoped_result_write_records.json()["data"]["items"]
    }
    assert "result_write_record_scheduled_run_scope_a" in result_write_record_ids
    assert "result_write_record_scheduled_run_scope_b" not in result_write_record_ids

    hidden_result_write_records = client.get(
        "/api/system/result-write-records?scheduled_job_run_id=scheduled_run_scope_b",
        headers=scoped_plugin_headers,
    )
    assert hidden_result_write_records.status_code == 200, hidden_result_write_records.text
    assert hidden_result_write_records.json()["data"]["items"] == []

    hidden_task_logs = client.get(
        "/api/system/ai-executor-tasks/ai_executor_task_scope_b/logs",
        headers=scoped_plugin_headers,
    )
    assert hidden_task_logs.status_code == 404
    assert hidden_task_logs.json()["detail"]["code"] == "NOT_FOUND"


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
    original_allow_seeded_users = settings.allow_seeded_users
    settings.app_env = "production"
    settings.allow_seeded_users = False
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
        settings.allow_seeded_users = original_allow_seeded_users

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "DEFAULT_CREDENTIALS_DISABLED"
    assert postgres_response.status_code == 403
    assert postgres_response.json()["detail"]["code"] == "DEFAULT_CREDENTIALS_DISABLED"


def test_seeded_default_users_require_explicit_opt_in_outside_tests():
    original_env = settings.app_env
    original_allow_seeded_users = settings.allow_seeded_users
    settings.app_env = "local"
    settings.allow_seeded_users = False
    try:
        disabled = client.post(
            "/api/auth/login",
            json={"username": "admin@example.com", "password": "admin123"},
        )
        settings.allow_seeded_users = True
        enabled = client.post(
            "/api/auth/login",
            json={"username": "admin@example.com", "password": "admin123"},
        )
    finally:
        settings.app_env = original_env
        settings.allow_seeded_users = original_allow_seeded_users

    assert disabled.status_code == 403
    assert disabled.json()["detail"]["code"] == "DEFAULT_CREDENTIALS_DISABLED"
    assert enabled.status_code == 200


def test_password_login_requires_one_time_numeric_challenge_when_enabled():
    original_enabled = settings.login_challenge_enabled
    original_repository = app.state.login_challenge_repository
    settings.login_challenge_enabled = True
    app.state.login_challenge_repository = MemoryLoginChallengeRepository(
        secret_key=settings.app_secret_key,
    )
    try:
        missing_challenge = client.post(
            "/api/auth/login",
            json={"username": "admin@example.com", "password": "admin123"},
        )
        challenge_response = client.post("/api/auth/login-challenge", json={})
        challenge = challenge_response.json()["data"]
        wrong_answer = client.post(
            "/api/auth/login",
            json={
                "challenge_answer": "999",
                "challenge_id": challenge["challenge_id"],
                "password": "admin123",
                "username": "admin@example.com",
            },
        )
        reused_challenge = client.post(
            "/api/auth/login",
            json={
                "challenge_answer": _challenge_answer(challenge["question"]),
                "challenge_id": challenge["challenge_id"],
                "password": "admin123",
                "username": "admin@example.com",
            },
        )
        next_challenge = client.post("/api/auth/login-challenge", json={}).json()["data"]
        successful_login = client.post(
            "/api/auth/login",
            json={
                "challenge_answer": _challenge_answer(next_challenge["question"]),
                "challenge_id": next_challenge["challenge_id"],
                "password": "admin123",
                "username": "admin@example.com",
            },
        )
    finally:
        settings.login_challenge_enabled = original_enabled
        app.state.login_challenge_repository = original_repository

    assert missing_challenge.status_code == 400
    assert missing_challenge.json()["detail"]["code"] == "LOGIN_CHALLENGE_REQUIRED"
    assert challenge_response.status_code == 200
    assert challenge["challenge_id"]
    assert challenge["question"].startswith("请计算：")
    assert wrong_answer.status_code == 401
    assert wrong_answer.json()["detail"]["code"] == "LOGIN_CHALLENGE_INVALID"
    assert reused_challenge.status_code == 401
    assert reused_challenge.json()["detail"]["code"] == "LOGIN_CHALLENGE_INVALID"
    assert successful_login.status_code == 200
    assert successful_login.json()["data"]["access_token"]


def test_seeded_username_can_login_with_real_non_default_password():
    original_env = settings.app_env
    original_allow_seeded_users = settings.allow_seeded_users
    original_users = app.state.user_repository
    settings.app_env = "local"
    settings.allow_seeded_users = False
    app.state.user_repository = MemoryUserRepository(
        {
            "admin@example.com": {
                "display_name": "Real Admin",
                "id": "user_admin",
                "password_hash": hash_password("real-admin-secret", salt="real-admin-salt"),
                "password_login_enabled": True,
                "roles": ["admin"],
                "status": "active",
                "username": "admin@example.com",
            }
        }
    )
    try:
        default_password = client.post(
            "/api/auth/login",
            json={"username": "admin@example.com", "password": "admin123"},
        )
        real_password = client.post(
            "/api/auth/login",
            json={"username": "admin@example.com", "password": "real-admin-secret"},
        )
    finally:
        settings.app_env = original_env
        settings.allow_seeded_users = original_allow_seeded_users
        app.state.user_repository = original_users

    assert default_password.status_code == 401
    assert default_password.json()["detail"]["code"] == "INVALID_CREDENTIALS"
    assert real_password.status_code == 200


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
