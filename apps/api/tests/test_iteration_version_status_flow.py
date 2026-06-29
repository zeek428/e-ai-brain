from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_product(headers: dict[str, str], code: str) -> dict[str, str]:
    return client.post(
        "/api/products",
        json={"code": code, "name": code},
        headers=headers,
    ).json()["data"]


def create_version(
    headers: dict[str, str],
    product_id: str,
    code: str,
    status: str = "planning",
) -> dict[str, str]:
    response = client.post(
        f"/api/products/{product_id}/versions",
        json={"code": code, "name": code, "status": status},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["data"]


def create_requirement(
    headers: dict[str, str],
    product_id: str,
    title: str,
    version_id: str,
) -> dict[str, str]:
    return client.post(
        "/api/requirements",
        json={
            "content": f"{title} 内容",
            "priority": "P1",
            "product_id": product_id,
            "title": title,
            "version_id": version_id,
        },
        headers=headers,
    ).json()["data"]


def approve_requirement(headers: dict[str, str], requirement_id: str) -> dict[str, str]:
    return client.post(
        f"/api/requirements/{requirement_id}/approve",
        json={"comment": "进入版本范围"},
        headers=headers,
    ).json()["data"]


def set_requirement_status(requirement_id: str, status: str) -> None:
    app.state.store.requirements[requirement_id]["status"] = status


def set_version_status(version_id: str, status: str) -> None:
    app.state.store.product_versions[version_id]["status"] = status


def get_requirement(headers: dict[str, str], requirement_id: str) -> dict[str, str]:
    return client.get(f"/api/requirements/{requirement_id}", headers=headers).json()["data"]


def test_advancing_planning_version_to_active_moves_planned_requirements_to_ready_for_dev():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "version-flow-active")
    version = create_version(headers, product["id"], "2026-07", status="planning")
    requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "启动开发需求", version["id"])["id"],
    )

    response = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"reason": "版本进入开发", "target_status": "active"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["from_status"] == "planning"
    assert data["target_status"] == "active"
    assert data["version"]["status"] == "active"
    assert data["blocked_requirements"] == []
    assert data["updated_requirements"] == [
        {
            "from_status": "planned",
            "id": requirement["id"],
            "title": "启动开发需求",
            "to_status": "ready_for_dev",
        }
    ]
    assert get_requirement(headers, requirement["id"])["status"] == "ready_for_dev"

    audits = client.get(
        f"/api/audit/events?subject_type=product_version&subject_id={version['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert "product_version.status_advanced" in [event["event_type"] for event in audits]


def test_advancing_active_version_to_testing_syncs_included_requirements_to_testing():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "version-flow-testing")
    version = create_version(headers, product["id"], "2026-08", status="active")
    planned_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "仍未开发需求", version["id"])["id"],
    )
    ready_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "待开发需求", version["id"])["id"],
    )
    designing_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "设计中需求", version["id"])["id"],
    )
    developing_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "开发中需求", version["id"])["id"],
    )
    review_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "已评审需求", version["id"])["id"],
    )
    set_requirement_status(ready_requirement["id"], "ready_for_dev")
    set_requirement_status(designing_requirement["id"], "task_created")
    set_requirement_status(developing_requirement["id"], "developing")
    set_requirement_status(review_requirement["id"], "code_reviewing")

    preview = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"preview_only": True, "target_status": "testing"},
        headers=headers,
    )

    assert preview.status_code == 200
    preview_data = preview.json()["data"]
    assert preview_data["preview_only"] is True
    assert preview_data["version"]["status"] == "active"
    assert {
        item["id"]: (item["from_status"], item["to_status"])
        for item in preview_data["updated_requirements"]
    } == {
        planned_requirement["id"]: ("planned", "testing"),
        ready_requirement["id"]: ("ready_for_dev", "testing"),
        designing_requirement["id"]: ("designing", "testing"),
        developing_requirement["id"]: ("developing", "testing"),
        review_requirement["id"]: ("code_reviewing", "testing"),
    }
    assert preview_data["blocked_requirements"] == []
    assert get_requirement(headers, review_requirement["id"])["status"] == "code_reviewing"

    advanced = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"reason": "进入系统测试", "target_status": "testing"},
        headers=headers,
    )

    assert advanced.status_code == 200
    advanced_data = advanced.json()["data"]
    assert advanced_data["version"]["status"] == "testing"
    assert advanced_data["blocked_requirements"] == []
    assert get_requirement(headers, planned_requirement["id"])["status"] == "testing"
    assert get_requirement(headers, ready_requirement["id"])["status"] == "testing"
    assert get_requirement(headers, designing_requirement["id"])["status"] == "testing"
    assert get_requirement(headers, developing_requirement["id"])["status"] == "testing"
    assert get_requirement(headers, review_requirement["id"])["status"] == "testing"


def test_advancing_testing_version_to_released_blocks_unfinished_requirements():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "version-flow-release")
    version = create_version(headers, product["id"], "2026-09", status="active")
    testing_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "测试完成需求", version["id"])["id"],
    )
    ready_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "待发布需求", version["id"])["id"],
    )
    unfinished_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "开发中需求", version["id"])["id"],
    )
    set_requirement_status(testing_requirement["id"], "testing")
    set_requirement_status(ready_requirement["id"], "ready_for_release")
    set_requirement_status(unfinished_requirement["id"], "developing")
    set_version_status(version["id"], "testing")

    blocked = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"force": True, "target_status": "released"},
        headers=headers,
    )

    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "PRODUCT_VERSION_STATUS_BLOCKED"
    assert get_requirement(headers, testing_requirement["id"])["status"] == "testing"

    set_requirement_status(unfinished_requirement["id"], "deferred")
    released = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"reason": "版本发布", "target_status": "released"},
        headers=headers,
    )

    assert released.status_code == 200
    released_data = released.json()["data"]
    assert released_data["version"]["status"] == "released"
    assert {
        item["id"]: item["to_status"]
        for item in released_data["updated_requirements"]
    } == {
        testing_requirement["id"]: "released",
        ready_requirement["id"]: "released",
    }
    assert get_requirement(headers, testing_requirement["id"])["status"] == "released"
    assert get_requirement(headers, ready_requirement["id"])["status"] == "released"
    assert get_requirement(headers, unfinished_requirement["id"])["status"] == "deferred"

    archived = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"reason": "版本历史归档", "target_status": "archived"},
        headers=headers,
    )

    assert archived.status_code == 200
    archived_data = archived.json()["data"]
    assert archived_data["version"]["status"] == "archived"
    assert archived_data["blocked_requirements"] == []
    assert {item["id"] for item in archived_data["unchanged_requirements"]} == {
        testing_requirement["id"],
        ready_requirement["id"],
        unfinished_requirement["id"],
    }


def test_direct_version_status_patch_requires_advance_endpoint():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "version-flow-direct-patch")
    version = create_version(headers, product["id"], "2026-10", status="planning")

    response = client.patch(
        f"/api/product-versions/{version['id']}",
        json={"status": "active"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED"


def test_product_version_dashboard_aggregates_delivery_health_and_blockers():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "version-dashboard-product")
    version = create_version(headers, product["id"], "2026-dashboard", status="active")
    requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "驾驶舱需求", version["id"])["id"],
    )
    set_requirement_status(requirement["id"], "developing")
    app.state.store.product_git_repositories["repo_dashboard"] = {
        "default_branch": "main",
        "git_provider": "github",
        "id": "repo_dashboard",
        "name": "Dashboard Repo",
        "product_id": product["id"],
        "project_path": "zeek428/e-ai-brain",
        "remote_url": "git@github.com:zeek428/e-ai-brain.git",
        "repo_type": "code",
        "root_path": "/",
        "status": "active",
    }
    app.state.store.product_version_branch_configs["version_branch_dashboard"] = {
        "base_branch": "main",
        "branch_status": "not_created",
        "creation_source": "manual",
        "id": "version_branch_dashboard",
        "product_id": product["id"],
        "repository_id": "repo_dashboard",
        "version_id": version["id"],
        "working_branch": "release/2026-dashboard",
    }
    app.state.store.ai_tasks["task_version_dashboard"] = {
        "created_at": "2026-06-04T08:00:00+00:00",
        "created_by": "user_admin",
        "id": "task_version_dashboard",
        "product_id": product["id"],
        "requirement_id": requirement["id"],
        "status": "running",
        "task_type": "implementation",
        "title": "实现版本驾驶舱",
        "updated_at": "2026-06-04T09:00:00+00:00",
        "version_id": version["id"],
    }
    app.state.store.bugs["bug_version_dashboard"] = {
        "assignee": "qa_owner",
        "created_at": "2026-06-04T09:10:00+00:00",
        "description": "严重缺陷",
        "id": "bug_version_dashboard",
        "module_code": "delivery",
        "product_id": product["id"],
        "related_task_id": "task_version_dashboard",
        "requirement_id": requirement["id"],
        "severity": "critical",
        "source": "manual_test",
        "status": "open",
        "title": "发布阻塞 Bug",
        "updated_at": "2026-06-04T09:20:00+00:00",
        "version_id": version["id"],
    }
    app.state.store.bugs["bug_version_dashboard_from_inspection"] = {
        "created_at": "2026-06-04T09:35:00+00:00",
        "description": "巡检派生缺陷",
        "evidence": {
            "code_inspection_report_id": "code_inspection_report_dashboard",
            "rule_id": "secrets.hardcoded_credential",
        },
        "id": "bug_version_dashboard_from_inspection",
        "product_id": product["id"],
        "severity": "critical",
        "source": "code_inspection",
        "status": "open",
        "title": "巡检派生阻塞 Bug",
        "updated_at": "2026-06-04T09:40:00+00:00",
    }
    app.state.store.code_inspection_reports["code_inspection_report_dashboard"] = {
        "branch": "release/2026-dashboard",
        "created_at": "2026-06-04T09:30:00+00:00",
        "created_bug_ids": ["bug_version_dashboard_from_inspection"],
        "finding_count": 3,
        "id": "code_inspection_report_dashboard",
        "product_id": product["id"],
        "quality_gate": {"status": "failed"},
        "repository_id": "repo_dashboard",
        "repository_name": "Dashboard Repo",
        "risk_level": "high",
        "severe_finding_count": 1,
        "status": "completed",
        "summary": "存在高风险问题",
    }
    app.state.store.jenkins_release_records["release_dashboard"] = {
        "build_id": "42",
        "created_at": "2026-06-04T10:00:00+00:00",
        "id": "release_dashboard",
        "job_name": "deploy-dashboard",
        "product_id": product["id"],
        "status": "failed",
        "version_id": version["id"],
    }

    response = client.get(f"/api/product-versions/{version['id']}/dashboard", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["version"]["id"] == version["id"]
    assert data["summary"] == {
        "blockers": 5,
        "branch_configs": 1,
        "bugs": 2,
        "code_inspection_reports": 1,
        "open_bugs": 2,
        "releases": 1,
        "requirements": 1,
        "severe_bugs": 2,
        "severe_code_inspection_reports": 1,
        "tasks": 1,
    }
    assert data["status_impact"]["target_status"] == "testing"
    assert data["status_impact"]["updated_requirements"] == [
        {
            "from_status": "developing",
            "id": requirement["id"],
            "title": "驾驶舱需求",
            "to_status": "testing",
        }
    ]
    assert {item["source_type"] for item in data["blockers"]} == {
        "bug",
        "code_inspection_report",
        "jenkins_release",
        "product_version_branch_config",
    }
    blocker_by_source = {item["source_type"]: item for item in data["blockers"]}
    assert blocker_by_source["bug"]["action_label"] == "处理 Bug"
    assert blocker_by_source["bug"]["action_target_id"] in {
        "bug_version_dashboard",
        "bug_version_dashboard_from_inspection",
    }
    assert blocker_by_source["bug"]["action_target_type"] == "bug"
    assert "关闭 blocker/critical Bug" in blocker_by_source["bug"]["resolution_hint"]
    assert blocker_by_source["code_inspection_report"]["action_label"] == "治理巡检"
    assert blocker_by_source["code_inspection_report"]["action_target_id"] == "code_inspection_report_dashboard"
    assert "重新扫描" in blocker_by_source["code_inspection_report"]["resolution_hint"]
    assert blocker_by_source["product_version_branch_config"]["action_label"] == "维护分支"
    assert blocker_by_source["jenkins_release"]["action_label"] == "排查发布"
    assert data["branch_configs"][0]["repository_name"] == "Dashboard Repo"
    assert data["code_inspection_reports"][0]["id"] == "code_inspection_report_dashboard"
    assert {bug["id"] for bug in data["bugs"]} == {
        "bug_version_dashboard",
        "bug_version_dashboard_from_inspection",
    }
    assert data["bug_status_counts"] == [{"count": 2, "status": "open"}]
