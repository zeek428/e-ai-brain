from fastapi.testclient import TestClient

from app.main import app
from app.services.product_version_dashboard import product_version_dashboard_response

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
    assert {item["id"]: item["to_status"] for item in released_data["updated_requirements"]} == {
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
        "code_review_report_id": "code_review_report_dashboard",
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
    app.state.store.knowledge_deposits["deposit_version_dashboard"] = {
        "ai_task_id": "task_version_dashboard",
        "content": "版本驾驶舱知识沉淀内容",
        "created_at": "2026-06-04T09:05:00+00:00",
        "id": "deposit_version_dashboard",
        "knowledge_document_id": "knowledge_version_dashboard",
        "status": "approved",
        "title": "版本驾驶舱知识沉淀",
        "updated_at": "2026-06-04T09:06:00+00:00",
    }
    app.state.store.knowledge_documents["knowledge_version_dashboard"] = {
        "active_chunk_set_id": "chunk_set_version_dashboard",
        "created_at": "2026-06-04T09:05:30+00:00",
        "doc_type": "markdown",
        "id": "knowledge_version_dashboard",
        "index_status": "text_indexed",
        "permission_roles": ["admin"],
        "title": "版本驾驶舱知识文档",
        "updated_at": "2026-06-04T09:05:40+00:00",
        "vector_index_error": "Embedding 网关未配置，已降级为关键词检索。",
    }
    app.state.store.knowledge_chunks["chunk_version_dashboard"] = {
        "chunk_index": 0,
        "chunk_set_id": "chunk_set_version_dashboard",
        "content": "版本驾驶舱知识沉淀内容",
        "created_at": "2026-06-04T09:05:35+00:00",
        "document_id": "knowledge_version_dashboard",
        "id": "chunk_version_dashboard",
        "updated_at": "2026-06-04T09:05:35+00:00",
    }
    app.state.store.code_review_reports["code_review_report_dashboard"] = {
        "archived_at": None,
        "executor": {"name": "codex", "type": "local"},
        "findings": [{"severity": "medium", "summary": "需要补充边界测试"}],
        "gitlab_mr_snapshot_id": "gitlab_mr_snapshot_dashboard",
        "gitlab_writeback_performed": False,
        "id": "code_review_report_dashboard",
        "review_id": "review_dashboard",
        "risk_level": "medium",
        "status": "pending_review",
        "summary": "代码评审待确认",
        "task_id": "task_version_dashboard",
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
        "created_task_ids": [],
        "finding_count": 4,
        "id": "code_inspection_report_dashboard",
        "product_id": product["id"],
        "quality_gate": {
            "status": "failed",
            "violations": [{"metric": "critical_findings", "severity": "high"}],
        },
        "repository_id": "repo_dashboard",
        "repository_name": "Dashboard Repo",
        "risk_level": "high",
        "severe_finding_count": 3,
        "status": "completed",
        "suppressed_finding_count": 2,
        "suppression_summary": {"accepted_risk": 1, "false_positive": 1},
        "summary": "存在高风险问题",
    }
    app.state.store.code_inspection_findings["finding_dashboard_active"] = {
        "created_bug_id": "bug_version_dashboard_from_inspection",
        "created_task_id": None,
        "id": "finding_dashboard_active",
        "report_id": "code_inspection_report_dashboard",
        "severity": "critical",
        "suppression_status": "none",
    }
    app.state.store.code_inspection_findings["finding_dashboard_expired_risk"] = {
        "created_bug_id": None,
        "created_task_id": None,
        "id": "finding_dashboard_expired_risk",
        "report_id": "code_inspection_report_dashboard",
        "severity": "high",
        "suppression_expires_at": "2000-01-01T00:00:00+00:00",
        "suppression_reason": "accepted_risk",
        "suppression_status": "approved",
    }
    app.state.store.code_inspection_findings["finding_dashboard_false_positive"] = {
        "created_bug_id": None,
        "created_task_id": None,
        "id": "finding_dashboard_false_positive",
        "report_id": "code_inspection_report_dashboard",
        "severity": "high",
        "suppression_reason": "false_positive",
        "suppression_status": "approved",
    }
    app.state.store.code_inspection_findings["finding_dashboard_pending_suppression"] = {
        "created_bug_id": None,
        "created_task_id": None,
        "id": "finding_dashboard_pending_suppression",
        "report_id": "code_inspection_report_dashboard",
        "severity": "medium",
        "suppression_reason": "accepted_risk",
        "suppression_status": "pending",
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
        "blockers": 6,
        "branch_configs": 1,
        "branch_quality_action_required": 1,
        "branch_quality_accepted_risks": 1,
        "branch_quality_active_severe_findings": 2,
        "branch_quality_expired_accepted_risks": 1,
        "branch_quality_false_positives": 1,
        "branch_quality_pending_scan": 0,
        "branch_quality_pending_suppressions": 1,
        "bugs": 2,
        "code_review_reports": 1,
        "code_inspection_reports": 1,
        "knowledge_deposits": 1,
        "open_bugs": 2,
        "pending_code_review_reports": 1,
        "failed_releases": 1,
        "releases": 1,
        "requirements": 1,
        "searchable_knowledge_deposits": 1,
        "severe_bugs": 2,
        "severe_code_inspection_reports": 1,
        "successful_releases": 0,
        "tasks": 1,
        "vectorized_knowledge_deposits": 0,
    }
    assert data["governance_conclusion"] == {
        "detail": (
            "当前版本有 6 个发布阻塞项，未关闭 Bug 2 个，"
            "门禁失败 1 份，状态推进阻塞需求 0 条。"
        ),
        "level": "error",
        "next_action": "先处理阻塞队列中的 Bug、发布记录和分支问题，再重新查看推进影响。",
        "risks": [
            "发布阻塞 6",
            "未关闭 Bug 2",
            "严重质量风险 5",
            "门禁失败 1",
            "待治理分支 1",
            "待审批忽略 1",
            "到期接受风险 1",
            "待确认评审 1",
        ],
        "title": "版本治理结论",
        "value": "版本暂不建议推进",
    }
    assert data["release_readiness_checklist"]["title"] == "发布准备清单"
    assert data["release_readiness_checklist"]["level"] == "error"
    assert data["release_readiness_checklist"]["value"] == "发布准备未通过"
    assert data["release_readiness_checklist"]["blocked_items"] == 5
    assert data["release_readiness_checklist"]["missing_items"] == 0
    assert data["release_readiness_checklist"]["ready_items"] == 4
    assert data["release_readiness_checklist"]["risk_items"] == 0
    readiness_by_key = {
        item["key"]: item for item in data["release_readiness_checklist"]["items"]
    }
    assert list(readiness_by_key) == [
        "requirements",
        "tasks",
        "branches",
        "inspections",
        "code-reviews",
        "bugs",
        "knowledge-deposits",
        "releases",
        "status-impact",
    ]
    assert readiness_by_key["branches"]["status"] == "blocked"
    assert readiness_by_key["branches"]["value"] == "分支待治理"
    assert readiness_by_key["inspections"]["value"] == "质量门禁未通过"
    assert readiness_by_key["code-reviews"]["status"] == "blocked"
    assert readiness_by_key["bugs"]["value"] == "严重 Bug 未关闭"
    assert readiness_by_key["knowledge-deposits"]["status"] == "ready"
    assert readiness_by_key["releases"] == {
        "action_label": "排查发布",
        "action_target_id": version["id"],
        "action_target_type": "releases",
        "detail": "成功 0 条，失败 1 条，发布阻塞 1 个。",
        "key": "releases",
        "level": "error",
        "status": "blocked",
        "title": "发布证据",
        "value": "发布待治理",
    }
    assert [item["key"] for item in data["delivery_stage_overview"]] == [
        "requirements",
        "tasks",
        "branches",
        "inspections",
        "code-reviews",
        "bugs",
        "knowledge-deposits",
        "releases",
        "status-impact",
    ]
    delivery_stage_by_key = {item["key"]: item for item in data["delivery_stage_overview"]}
    assert delivery_stage_by_key["requirements"] == {
        "action_label": "查看需求",
        "action_target_id": version["id"],
        "action_target_type": "requirements",
        "detail": "1 条需求 · 可推进",
        "full_chain_subject_id": None,
        "full_chain_subject_type": None,
        "key": "requirements",
        "level": "success",
        "title": "需求范围",
        "value": "范围可推进",
    }
    assert delivery_stage_by_key["tasks"] == {
        "action_label": "查看任务",
        "action_target_id": "task_version_dashboard",
        "action_target_type": "ai_task",
        "detail": "1 个任务 · 运行中 1 个",
        "full_chain_subject_id": requirement["id"],
        "full_chain_subject_type": "requirement",
        "key": "tasks",
        "level": "info",
        "title": "研发任务",
        "value": "任务进行中",
    }
    assert (
        delivery_stage_by_key["branches"]["action_target_id"]
        == "version_branch_dashboard"
    )
    assert (
        delivery_stage_by_key["branches"]["action_target_type"]
        == "product_version_branch_config"
    )
    assert delivery_stage_by_key["branches"]["detail"] == "1 个分支 · 未创建 1 个"
    assert delivery_stage_by_key["branches"]["level"] == "warning"
    assert delivery_stage_by_key["inspections"]["detail"] == "1 份报告 · 高风险 1 份"
    assert delivery_stage_by_key["inspections"]["level"] == "warning"
    assert (
        delivery_stage_by_key["code-reviews"]["action_target_id"]
        == "code_review_report_dashboard"
    )
    assert delivery_stage_by_key["code-reviews"]["detail"] == "1 份报告 · 待确认 1 份"
    assert delivery_stage_by_key["bugs"]["detail"] == "2 个 Bug · 未关闭 2 个"
    assert delivery_stage_by_key["bugs"]["level"] == "error"
    assert (
        delivery_stage_by_key["knowledge-deposits"]["action_target_id"]
        == "deposit_version_dashboard"
    )
    assert (
        delivery_stage_by_key["knowledge-deposits"]["detail"]
        == "1 条知识沉淀 · 可检索 1 条 · 向量就绪 0 条"
    )
    assert (
        delivery_stage_by_key["releases"]["detail"]
        == "1 条记录 · 发布阻塞 1 个 · 成功 0 条 · 失败 1 条 · "
        "最近 failed deploy-dashboard · 2026-06-04 18:00"
    )
    assert delivery_stage_by_key["releases"]["level"] == "error"
    assert delivery_stage_by_key["status-impact"]["action_target_type"] == "product_version_advance"
    assert delivery_stage_by_key["status-impact"]["detail"] == "同步 1 / 阻塞 0 / 保持 0"
    assert data["evidence_coverage"] == {
        "blocking_domains": 5,
        "covered_domains": 4,
        "domains": [
            {
                "action_label": "查看需求",
                "action_target_id": version["id"],
                "action_target_type": "requirements",
                "detail": "1 条需求 · 状态推进阻塞 0 条",
                "key": "requirements",
                "level": "success",
                "status": "covered",
                "title": "需求范围",
                "value": "1 条",
            },
            {
                "action_label": "查看任务",
                "action_target_id": version["id"],
                "action_target_type": "tasks_by_version",
                "detail": "1 个研发任务",
                "key": "tasks",
                "level": "success",
                "status": "covered",
                "title": "研发任务",
                "value": "1 个",
            },
            {
                "action_label": "维护分支",
                "action_target_id": version["id"],
                "action_target_type": "product_version",
                "detail": "1 个版本分支 · 待治理 1 个",
                "key": "branches",
                "level": "error",
                "status": "blocked",
                "title": "代码分支",
                "value": "1 个",
            },
            {
                "action_label": "查看巡检",
                "action_target_id": version["id"],
                "action_target_type": "code_inspection_dashboard",
                "detail": "1 份报告 · 严重风险 1 份",
                "key": "inspections",
                "level": "error",
                "status": "blocked",
                "title": "代码巡检",
                "value": "1 份",
            },
            {
                "action_label": "查看评审",
                "action_target_id": version["id"],
                "action_target_type": "code_review_reports_by_version",
                "detail": "1 份评审 · 待确认 1 份",
                "key": "code-reviews",
                "level": "error",
                "status": "blocked",
                "title": "代码评审",
                "value": "1 份",
            },
            {
                "action_label": "查看 Bug",
                "action_target_id": version["id"],
                "action_target_type": "bugs",
                "detail": "2 个 Bug · 未关闭 2 个 · 严重 2 个",
                "key": "bugs",
                "level": "error",
                "status": "blocked",
                "title": "Bug 收敛",
                "value": "2 未关闭",
            },
            {
                "action_label": "查看沉淀",
                "action_target_id": version["id"],
                "action_target_type": "knowledge_deposits_by_version",
                "detail": "1 条沉淀 · 可检索 1 条 · 向量就绪 0 条",
                "key": "knowledge-deposits",
                "level": "success",
                "status": "covered",
                "title": "知识沉淀",
                "value": "1/1 可检索",
            },
            {
                "action_label": "查看发布",
                "action_target_id": version["id"],
                "action_target_type": "releases",
                "detail": "1 条发布记录 · 成功 0 条 · 失败 1 条",
                "key": "releases",
                "level": "error",
                "status": "blocked",
                "title": "发布证据",
                "value": "发布待补证",
            },
            {
                "action_label": "推进状态",
                "action_target_id": version["id"],
                "action_target_type": "product_version_advance",
                "detail": "目标 testing · 同步 1 · 阻塞 0",
                "key": "status-impact",
                "level": "success",
                "status": "covered",
                "title": "状态推进",
                "value": "影响已预览",
            },
        ],
        "gap_domains": 0,
        "level": "error",
        "score": 44,
        "summary": "5 个交付域存在阻断，需先处理阻塞队列。",
        "total_domains": 9,
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
        "code_review_report",
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
    assert (
        blocker_by_source["code_inspection_report"]["action_target_id"]
        == "code_inspection_report_dashboard"
    )
    assert "重新扫描" in blocker_by_source["code_inspection_report"]["resolution_hint"]
    assert blocker_by_source["code_review_report"]["action_label"] == "处理评审"
    assert (
        blocker_by_source["code_review_report"]["action_target_id"]
        == "code_review_report_dashboard"
    )
    assert blocker_by_source["code_review_report"]["action_target_type"] == "code_review_report"
    assert "代码评审仍待确认" in blocker_by_source["code_review_report"]["reason"]
    assert "关闭待确认项" in blocker_by_source["code_review_report"]["resolution_hint"]
    assert blocker_by_source["product_version_branch_config"]["action_label"] == "维护分支"
    assert blocker_by_source["jenkins_release"]["action_label"] == "排查发布"
    assert [item["priority"] for item in data["next_actions"]] == [1, 2, 3]
    assert [item["source_type"] for item in data["next_actions"]] == [
        "bug",
        "bug",
        "jenkins_release",
    ]
    assert data["next_actions"][0]["source_label"] == "Bug"
    assert data["next_actions"][0]["full_chain_subject_type"] == "bug"
    assert data["next_actions"][0]["full_chain_subject_id"] in {
        "bug_version_dashboard",
        "bug_version_dashboard_from_inspection",
    }
    assert data["next_actions"][2]["source_label"] == "发布记录"
    assert data["next_actions"][2]["full_chain_subject_type"] == "jenkins_release"
    assert data["next_actions"][2]["full_chain_subject_id"] == "release_dashboard"
    assert data["branch_configs"][0]["repository_name"] == "Dashboard Repo"
    assert data["branch_quality_governance"] == [
        {
            "branch": "release/2026-dashboard",
            "branch_config_id": "version_branch_dashboard",
            "accepted_risk_count": 1,
            "active_severe_finding_count": 2,
            "created_bug_count": 1,
            "created_task_count": 0,
            "expired_accepted_risk_count": 1,
            "false_positive_count": 1,
            "finding_count": 4,
            "id": "version_branch_dashboard",
            "latest_report_id": "code_inspection_report_dashboard",
            "latest_report_summary": "存在高风险问题",
            "latest_report_time": "2026-06-04T09:30:00+00:00",
            "quality_gate_failed_report_count": 1,
            "quality_gate_violation_count": 1,
            "report_count": 1,
            "repository_id": "repo_dashboard",
            "repository_name": "Dashboard Repo",
            "severe_finding_count": 3,
            "status": "action_required",
            "suppressed_finding_count": 2,
            "pending_suppression_count": 1,
            "uncovered_severe_bug_count": 1,
            "uncovered_severe_task_count": 2,
        }
    ]
    assert data["code_review_reports"] == [
        {
            "archived_at": None,
            "executor": {"name": "codex", "type": "local"},
            "finding_count": 1,
            "gitlab_mr_snapshot_id": "gitlab_mr_snapshot_dashboard",
            "gitlab_writeback_performed": False,
            "id": "code_review_report_dashboard",
            "review_id": "review_dashboard",
            "risk_level": "medium",
            "status": "pending_review",
            "summary": "代码评审待确认",
            "task_id": "task_version_dashboard",
            "task_title": "实现版本驾驶舱",
        }
    ]
    assert data["code_inspection_reports"][0]["id"] == "code_inspection_report_dashboard"
    assert data["knowledge_deposits"] == [
        {
            "ai_task_id": "task_version_dashboard",
            "id": "deposit_version_dashboard",
            "knowledge_chunk_count": 1,
            "knowledge_document_id": "knowledge_version_dashboard",
            "knowledge_document_title": "版本驾驶舱知识文档",
            "knowledge_embedding_chunk_count": 0,
            "knowledge_index_error": "Embedding 网关未配置，已降级为关键词检索。",
            "knowledge_index_status": "text_indexed",
            "knowledge_retrieval_mode": "keyword",
            "status": "approved",
            "title": "版本驾驶舱知识沉淀",
            "task_title": "实现版本驾驶舱",
            "updated_at": "2026-06-04T09:06:00+00:00",
        }
    ]
    assert {bug["id"] for bug in data["bugs"]} == {
        "bug_version_dashboard",
        "bug_version_dashboard_from_inspection",
    }
    assert data["bug_status_counts"] == [{"count": 2, "status": "open"}]
    limited_dashboard = product_version_dashboard_response(
        current_store=app.state.store,
        user={
            "id": "limited_user",
            "permissions": ["bug.read", "knowledge.read", "product.read"],
            "roles": [],
        },
        version_id=version["id"],
    )
    assert limited_dashboard is not None
    assert limited_dashboard["code_inspection_reports"] == []
    assert limited_dashboard["branch_quality_governance"] == []
    assert limited_dashboard["summary"]["branch_quality_action_required"] == 0
    assert limited_dashboard["summary"]["branch_quality_pending_scan"] == 0
    assert limited_dashboard["access_issues"] == [
        {
            "code": "code_inspection.read",
            "message": "缺少代码巡检读取权限，版本驾驶舱已隐藏代码巡检明细。",
            "section": "code_inspections",
        }
    ]
    limited_evidence_by_key = {
        item["key"]: item for item in limited_dashboard["evidence_coverage"]["domains"]
    }
    assert limited_evidence_by_key["inspections"]["status"] == "inaccessible"
    assert limited_evidence_by_key["inspections"]["value"] == "权限不足"
    assert limited_dashboard["evidence_coverage"]["gap_domains"] >= 1


def test_product_version_dashboard_loads_knowledge_index_health_from_repository_projection():
    class FakeRepository:
        def get_task_workflow_source_rows(self) -> dict[str, list[dict[str, object]]]:
            return {
                "audit_events": [],
                "bugs": [],
                "code_inspection_reports": [],
                "code_review_reports": [],
                "gitlab_daily_code_metrics": [],
                "gitlab_mr_snapshots": [],
                "graph_checkpoints": [],
                "graph_runs": [],
                "human_reviews": [],
                "jenkins_release_records": [],
                "knowledge_chunks": [
                    {
                        "chunk_index": 1,
                        "content": "repository projection knowledge chunk",
                        "document_id": "knowledge_repository_projection",
                        "id": "chunk_repository_projection",
                    }
                ],
                "knowledge_deposits": [
                    {
                        "ai_task_id": "task_repository_projection",
                        "created_at": "2026-06-04T09:05:00+00:00",
                        "id": "deposit_repository_projection",
                        "knowledge_document_id": "knowledge_repository_projection",
                        "status": "approved",
                        "title": "Repository 投影知识沉淀",
                        "updated_at": "2026-06-04T09:06:00+00:00",
                    }
                ],
                "knowledge_documents": [
                    {
                        "created_at": "2026-06-04T09:05:30+00:00",
                        "doc_type": "task_deposit",
                        "id": "knowledge_repository_projection",
                        "index_status": "text_indexed",
                        "permission_roles": ["admin"],
                        "title": "Repository 投影知识文档",
                        "updated_at": "2026-06-04T09:05:40+00:00",
                        "vector_index_error": "Embedding 网关未配置，已降级为关键词检索。",
                    }
                ],
                "model_gateway_configs": [],
                "model_gateway_logs": [],
                "mock_writebacks": [],
                "online_log_metrics": [],
                "product_git_repositories": [],
                "product_modules": [],
                "product_version_branch_configs": [],
                "product_versions": [
                    {
                        "code": "repository-dashboard",
                        "id": "version_repository_projection",
                        "name": "Repository 投影驾驶舱",
                        "product_id": "product_repository_projection",
                        "status": "active",
                    }
                ],
                "products": [
                    {
                        "code": "repository-dashboard-product",
                        "id": "product_repository_projection",
                        "name": "Repository 投影产品",
                        "status": "active",
                    }
                ],
                "related_systems": [],
                "requirements": [
                    {
                        "created_at": "2026-06-04T08:00:00+00:00",
                        "id": "requirement_repository_projection",
                        "priority": "P1",
                        "product_id": "product_repository_projection",
                        "status": "developing",
                        "title": "Repository 投影需求",
                        "updated_at": "2026-06-04T08:30:00+00:00",
                        "version_id": "version_repository_projection",
                    }
                ],
                "tasks": [
                    {
                        "created_at": "2026-06-04T08:40:00+00:00",
                        "created_by": "user_admin",
                        "id": "task_repository_projection",
                        "product_id": "product_repository_projection",
                        "requirement_id": "requirement_repository_projection",
                        "status": "completed",
                        "task_type": "implementation",
                        "title": "Repository 投影任务",
                        "updated_at": "2026-06-04T09:00:00+00:00",
                        "version_id": "version_repository_projection",
                    }
                ],
            }

    current_store = type("RepositoryBackedStore", (), {"repository": FakeRepository()})()

    dashboard = product_version_dashboard_response(
        current_store=current_store,
        user={"id": "user_admin", "permissions": [], "roles": ["admin"]},
        version_id="version_repository_projection",
    )

    assert dashboard is not None
    assert dashboard["summary"]["knowledge_deposits"] == 1
    assert dashboard["summary"]["searchable_knowledge_deposits"] == 1
    assert dashboard["summary"]["vectorized_knowledge_deposits"] == 0
    assert dashboard["knowledge_deposits"] == [
        {
            "ai_task_id": "task_repository_projection",
            "id": "deposit_repository_projection",
            "knowledge_chunk_count": 1,
            "knowledge_document_id": "knowledge_repository_projection",
            "knowledge_document_title": "Repository 投影知识文档",
            "knowledge_embedding_chunk_count": 0,
            "knowledge_index_error": "Embedding 网关未配置，已降级为关键词检索。",
            "knowledge_index_status": "text_indexed",
            "knowledge_retrieval_mode": "keyword",
            "status": "approved",
            "task_title": "Repository 投影任务",
            "title": "Repository 投影知识沉淀",
            "updated_at": "2026-06-04T09:06:00+00:00",
        }
    ]


def test_product_version_dashboard_prefers_version_scoped_repository_projection():
    class FakeRepository:
        def __init__(self) -> None:
            self.requested_version_id: str | None = None

        def get_task_workflow_source_rows(self) -> dict[str, list[dict[str, object]]]:
            raise AssertionError("version dashboard should not load full workflow source rows")

        def get_product_version_dashboard_source_rows(
            self,
            version_id: str,
        ) -> dict[str, list[dict[str, object]]]:
            self.requested_version_id = version_id
            return {
                "product_versions": [
                    {
                        "code": "scoped-dashboard",
                        "id": "version_scoped_projection",
                        "name": "版本专用投影",
                        "product_id": "product_scoped_projection",
                        "status": "active",
                    }
                ],
                "products": [
                    {
                        "code": "scoped-dashboard-product",
                        "id": "product_scoped_projection",
                        "name": "版本专用投影产品",
                        "status": "active",
                    }
                ],
                "requirements": [
                    {
                        "created_at": "2026-06-04T08:00:00+00:00",
                        "id": "requirement_scoped_projection",
                        "priority": "P1",
                        "product_id": "product_scoped_projection",
                        "status": "developing",
                        "title": "版本专用投影需求",
                        "updated_at": "2026-06-04T08:30:00+00:00",
                        "version_id": "version_scoped_projection",
                    }
                ],
                "tasks": [],
            }

    repository = FakeRepository()
    current_store = type("RepositoryBackedStore", (), {"repository": repository})()

    dashboard = product_version_dashboard_response(
        current_store=current_store,
        user={"id": "user_admin", "permissions": [], "roles": ["admin"]},
        version_id="version_scoped_projection",
    )

    assert repository.requested_version_id == "version_scoped_projection"
    assert dashboard is not None
    assert dashboard["version"]["product_name"] == "版本专用投影产品"
    assert dashboard["summary"]["requirements"] == 1
    assert dashboard["summary"]["tasks"] == 0
    assert dashboard["status_impact"]["updated_requirements"] == [
        {
            "from_status": "developing",
            "id": "requirement_scoped_projection",
            "title": "版本专用投影需求",
            "to_status": "testing",
        }
    ]


def test_product_version_dashboard_blocks_release_without_successful_release_record():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "version-dashboard-release-evidence")
    version = create_version(headers, product["id"], "2026-release", status="active")
    requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "发布证据需求", version["id"])["id"],
    )
    set_requirement_status(requirement["id"], "ready_for_release")
    set_version_status(version["id"], "testing")

    response = client.get(f"/api/product-versions/{version['id']}/dashboard", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status_impact"]["target_status"] == "released"
    assert data["summary"]["blockers"] == 1
    assert data["governance_conclusion"]["value"] == "版本暂不建议推进"
    assert data["governance_conclusion"]["risks"] == ["发布阻塞 1"]
    assert data["blockers"] == [
        {
            "action_label": "排查发布",
            "action_target_id": version["id"],
            "action_target_type": "product_version",
            "id": None,
            "reason": "缺少成功发布记录，不能确认版本已完成发布。",
            "resolution_hint": "登记或同步成功发布记录后解除发布阻塞。",
            "severity": "high",
            "source_type": "jenkins_release",
            "title": "缺少成功发布记录",
        }
    ]
    assert data["next_actions"] == [
        {
            "action_label": "排查发布",
            "action_target_id": version["id"],
            "action_target_type": "product_version",
            "full_chain_subject_id": version["id"],
            "full_chain_subject_type": "product_version",
            "id": None,
            "priority": 1,
            "reason": "缺少成功发布记录，不能确认版本已完成发布。",
            "resolution_hint": "登记或同步成功发布记录后解除发布阻塞。",
            "severity": "high",
            "source_label": "发布记录",
            "source_type": "jenkins_release",
            "title": "缺少成功发布记录",
        }
    ]

    app.state.store.jenkins_release_records["release_success"] = {
        "build_id": "99",
        "created_at": "2026-06-04T10:00:00+00:00",
        "id": "release_success",
        "job_name": "deploy-release",
        "product_id": product["id"],
        "status": "success",
        "version_id": version["id"],
    }

    response_with_release = client.get(
        f"/api/product-versions/{version['id']}/dashboard",
        headers=headers,
    )

    assert response_with_release.status_code == 200
    data_with_release = response_with_release.json()["data"]
    assert data_with_release["summary"]["blockers"] == 0
    assert data_with_release["summary"]["successful_releases"] == 1
    assert data_with_release["summary"]["failed_releases"] == 0
    release_stage = next(
        item
        for item in data_with_release["delivery_stage_overview"]
        if item["key"] == "releases"
    )
    assert (
        release_stage["detail"]
        == "1 条记录 · 暂无发布阻塞 · 成功 1 条 · 失败 0 条 · "
        "最近 success deploy-release · 2026-06-04 18:00"
    )
    assert data_with_release["governance_conclusion"] == {
        "detail": (
            "待确认评审 0 份，状态推进阻塞需求 0 条，"
            "交付证据覆盖：分支 0、巡检 0、评审 0、知识 0。"
        ),
        "level": "warning",
        "next_action": "补齐待确认评审、知识索引或交付证据后，再执行版本推进。",
        "risks": ["交付证据待补齐"],
        "title": "版本治理结论",
        "value": "版本证据待补齐",
    }
    assert data_with_release["blockers"] == []
    assert data_with_release["next_actions"] == []
