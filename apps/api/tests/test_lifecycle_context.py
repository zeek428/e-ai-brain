from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from gitlab_fakes import install_real_gitlab_api_stub

from app.main import app
from app.services.lifecycle_risks import sync_lifecycle_context_records
from app.services.requirement_full_chain import (
    get_requirement_full_chain_by_subject_response,
    get_requirement_full_chain_response,
)
from app.services.task_workflow_context import TaskWorkflowSourceStore

client = TestClient(app)


def build_minimal_full_chain_store() -> TaskWorkflowSourceStore:
    store = TaskWorkflowSourceStore()
    store.products["product_alpha"] = {
        "code": "ALPHA",
        "id": "product_alpha",
        "name": "Alpha Product",
    }
    store.product_versions["version_alpha"] = {
        "code": "v1",
        "id": "version_alpha",
        "name": "Alpha v1",
        "product_id": "product_alpha",
        "status": "active",
    }
    store.product_version_branch_configs["branch_config_alpha"] = {
        "base_branch": "main",
        "branch_status": "active",
        "creation_source": "manual",
        "id": "branch_config_alpha",
        "product_id": "product_alpha",
        "repository_id": "repo_alpha",
        "version_id": "version_alpha",
        "working_branch": "feature/alpha",
    }
    store.requirements["requirement_alpha"] = {
        "content": "Alpha full-chain access check.",
        "created_at": "2026-06-27T01:00:00+00:00",
        "created_by": "user_admin",
        "id": "requirement_alpha",
        "priority": "P1",
        "product_id": "product_alpha",
        "source": "product_planning",
        "status": "approved",
        "title": "Alpha 全链路访问控制",
        "updated_at": "2026-06-27T01:10:00+00:00",
        "version_id": "version_alpha",
    }
    store.ai_tasks["task_alpha"] = {
        "created_at": "2026-06-27T01:15:00+00:00",
        "created_by": "user_admin",
        "id": "task_alpha",
        "product_id": "product_alpha",
        "requirement_id": "requirement_alpha",
        "status": "completed",
        "task_type": "technical_solution",
        "title": "Alpha 技术方案",
        "updated_at": "2026-06-27T01:20:00+00:00",
        "version_id": "version_alpha",
    }
    return store


def scoped_reader(product_id: str) -> dict[str, object]:
    return {
        "id": "user_scoped_reader",
        "permissions": ["requirement.read"],
        "roles": ["product_owner"],
        "scope_summary": [
            {
                "access_level": "read",
                "scope_id": product_id,
                "scope_type": "product",
            }
        ],
    }


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def build_mvp_lifecycle(headers: dict[str, str]) -> dict[str, str]:
    app.state.store.reset()
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
    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "name": "AI Brain API",
            "remote_url": "https://gitlab.example.com/platform/ai-brain.git",
            "git_provider": "gitlab",
            "project_path": "platform/ai-brain",
            "credential_ref": "env:GITLAB_READONLY_TOKEN",
        },
        headers=headers,
    ).json()["data"]
    branch_config = client.post(
        f"/api/product-versions/{version['id']}/branch-configs",
        json={
            "base_branch": "main",
            "branch_status": "active",
            "creation_source": "manual",
            "repository_id": repository["id"],
            "working_branch": "feature/full-chain-mvp",
        },
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "title": "全流程感知 MVP",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "从需求追踪到设计、方案、Review、回写、知识沉淀和审计。",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)

    design_task = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    design_started = client.post(
        f"/api/ai-tasks/{design_task['task_id']}/start",
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/reviews/{design_started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    writeback = client.post(
        f"/api/writeback/results/{design_task['task_id']}",
        headers=headers,
    ).json()["data"]

    solution_task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "technical_solution",
            "title": "技术方案：全流程感知 MVP",
            "requirement_id": requirement["id"],
            "input": {"product_detail_design_task_id": design_task["task_id"]},
        },
        headers=headers,
    ).json()["data"]
    solution_started = client.post(
        f"/api/ai-tasks/{solution_task['id']}/start",
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/reviews/{solution_started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )

    snapshot = client.post(
        f"/api/devops/gitlab/merge-requests/{repository['id']}/42/snapshot",
        json={
            "requirement_id": requirement["id"],
            "technical_solution_task_id": solution_task["id"],
        },
        headers=headers,
    ).json()["data"]
    review_task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "code_review",
            "title": "Review MR !42",
            "requirement_id": requirement["id"],
            "input": {"gitlab_mr_snapshot_id": snapshot["id"]},
        },
        headers=headers,
    ).json()["data"]
    review_started = client.post(
        f"/api/ai-tasks/{review_task['id']}/start",
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/reviews/{review_started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    code_review_report_id = app.state.store.ai_tasks[review_task["id"]]["code_review_report_id"]
    design_deposit = next(
        deposit
        for deposit in app.state.store.knowledge_deposits.values()
        if deposit["ai_task_id"] == design_task["task_id"]
    )
    review_audit_event = next(
        event
        for event in app.state.store.audit_events
        if event.get("subject_type") == "human_review"
        and event.get("subject_id") == design_started["review_id"]
        and event["event_type"] == "review.submitted"
    )
    return {
        "requirement_id": requirement["id"],
        "product_id": product["id"],
        "version_id": version["id"],
        "branch_config_id": branch_config["id"],
        "design_task_id": design_task["task_id"],
        "design_review_id": design_started["review_id"],
        "solution_task_id": solution_task["id"],
        "snapshot_id": snapshot["id"],
        "review_task_id": review_task["id"],
        "review_id": review_started["review_id"],
        "code_review_report_id": code_review_report_id,
        "mock_issue_id": writeback["issues"][0]["id"],
        "knowledge_deposit_id": design_deposit["id"],
        "audit_event_id": review_audit_event["id"],
    }


def add_v1_2_lifecycle_evidence(
    headers: dict[str, str],
    lifecycle: dict[str, str],
) -> dict[str, str]:
    module = client.post(
        f"/api/products/{lifecycle['product_id']}/modules",
        json={"code": "knowledge", "name": "知识中心"},
        headers=headers,
    ).json()["data"]
    repository = client.post(
        f"/api/products/{lifecycle['product_id']}/git-repositories",
        json={
            "default_branch": "main",
            "git_provider": "gitlab",
            "name": "Lifecycle API",
            "project_path": "rd/lifecycle-api",
            "remote_url": "https://gitlab.internal/rd/lifecycle-api.git",
            "repo_type": "code",
            "root_path": "/",
        },
        headers=headers,
    ).json()["data"]
    bug = client.post(
        "/api/bugs",
        json={
            "description": "严重缺陷仍未关闭。",
            "module_code": module["code"],
            "product_id": lifecycle["product_id"],
            "related_task_id": lifecycle["review_task_id"],
            "requirement_id": lifecycle["requirement_id"],
            "severity": "critical",
            "source": "manual_test",
            "title": "Lifecycle 严重 Bug",
            "version_id": lifecycle["version_id"],
        },
        headers=headers,
    ).json()["data"]
    gitlab_metric = client.post(
        "/api/devops/gitlab/daily-code-metrics",
        json={
            "changed_files": 18,
            "commit_count": 7,
            "merge_request_count": 2,
            "metric_date": "2026-06-01",
            "product_id": lifecycle["product_id"],
            "quality_score": 72.5,
            "repository_id": repository["id"],
            "risk_count": 3,
        },
        headers=headers,
    ).json()["data"]
    jenkins_release = client.post(
        "/api/devops/jenkins/releases",
        json={
            "build_id": "lifecycle-build-1",
            "failure_reason": "smoke test failed",
            "job_name": "lifecycle-deploy",
            "product_id": lifecycle["product_id"],
            "status": "failed",
            "version_id": lifecycle["version_id"],
        },
        headers=headers,
    ).json()["data"]
    online_log_metric = client.post(
        "/api/ops/online-log-metrics",
        json={
            "environment": "prod",
            "error_count": 25,
            "module_code": module["code"],
            "p95_latency_ms": 480.0,
            "product_id": lifecycle["product_id"],
            "request_count": 1000,
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=headers,
    ).json()["data"]
    usage_metric = client.post(
        "/api/insights/usage-metrics",
        json={
            "active_users": 12,
            "event_count": 40,
            "feature_code": "knowledge-search",
            "module_code": module["code"],
            "product_id": lifecycle["product_id"],
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=headers,
    ).json()["data"]
    feedback = client.post(
        "/api/insights/user-feedback",
        json={
            "content": "知识检索上线后体验变差。",
            "feedback_type": "complaint",
            "module_code": module["code"],
            "product_id": lifecycle["product_id"],
            "satisfaction_score": 1,
            "sentiment": "negative",
        },
        headers=headers,
    ).json()["data"]
    suggestion = client.post(
        "/api/planning/iteration-suggestions",
        json={
            "module_codes": [module["code"]],
            "planning_cycle": "2026Q3",
            "product_id": lifecycle["product_id"],
            "version_id": lifecycle["version_id"],
        },
        headers=headers,
    ).json()["data"]["items"][0]
    app.state.store.iteration_plan_suggestions[suggestion["id"]][
        "confidence_level"
    ] = "low"
    return {
        "bug_id": bug["id"],
        "feedback_id": feedback["id"],
        "gitlab_metric_id": gitlab_metric["id"],
        "iteration_suggestion_id": suggestion["id"],
        "jenkins_release_id": jenkins_release["id"],
        "module_code": module["code"],
        "online_log_metric_id": online_log_metric["id"],
        "usage_metric_id": usage_metric["id"],
    }


def test_lifecycle_context_links_mvp_requirement_downstream_subjects_and_risks(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    lifecycle = build_mvp_lifecycle(headers)
    requirement_id = lifecycle["requirement_id"]
    product_id = lifecycle["product_id"]

    context = client.get(
        f"/api/lifecycle/context?subject_type=requirement&subject_id={requirement_id}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]

    assert context["status"] == "available"
    assert context["subject"] == {
        "type": "requirement",
        "id": requirement_id,
        "product_id": product_id,
    }

    downstream = context["downstream"]
    relation_types = {item["relation_type"] for item in downstream}
    assert {
        "generates_product_detail_design",
        "generates_technical_solution",
        "generates_code_review",
        "creates_human_review",
        "creates_mock_issue",
        "creates_knowledge_deposit",
        "creates_audit_event",
    }.issubset(relation_types)

    task_types = {
        item["metadata"].get("task_type")
        for item in downstream
        if item["subject_type"] == "ai_task"
    }
    assert {"product_detail_design", "technical_solution", "code_review"}.issubset(task_types)

    assert any(item["subject_type"] == "code_review_report" for item in downstream)
    assert any(item["subject_type"] == "knowledge_deposit" for item in downstream)
    assert any(item["subject_type"] == "mock_issue" for item in downstream)
    assert any(item["subject_type"] == "audit_event" for item in downstream)

    risk = context["risk_signals"][0]
    assert risk["risk_type"] == "code_review_medium_risk"
    assert risk["source_subject_type"] == "code_review_report"
    assert risk["severity"] == "medium"
    assert "Review" in risk["impact_summary"]
    assert risk["recommendation"]

    assert "automated_testing" in context["missing_context"]
    assert context["summary"]["downstream_count"] == len(downstream)


def test_lifecycle_context_and_dashboard_queries_materialize_persistent_records(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    lifecycle = build_mvp_lifecycle(headers)
    add_v1_2_lifecycle_evidence(headers, lifecycle)

    context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=requirement&subject_id={lifecycle['requirement_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]
    dashboard = client.get(
        f"/api/dashboard/it-team?product_id={lifecycle['product_id']}&time_range=7d",
        headers=headers,
    ).json()["data"]

    persisted_edges = app.state.store.lifecycle_context_edges
    persisted_risks = app.state.store.lifecycle_risk_signals
    persisted_snapshots = app.state.store.dashboard_metric_snapshots

    assert persisted_edges
    assert {
        (edge["source_subject_type"], edge["source_subject_id"])
        for edge in persisted_edges.values()
    } == {("requirement", lifecycle["requirement_id"])}
    assert {
        (edge["target_subject_type"], edge["target_subject_id"])
        for edge in persisted_edges.values()
    } == {
        (item["subject_type"], item["subject_id"])
        for item in context["upstream"] + context["downstream"]
    }

    assert persisted_risks
    assert {
        (risk["source_subject_type"], risk["source_subject_id"])
        for risk in persisted_risks.values()
    } == {
        (item["source_subject_type"], item["source_subject_id"])
        for item in context["risk_signals"]
    }

    snapshot = next(iter(persisted_snapshots.values()))
    assert snapshot["product_id"] == lifecycle["product_id"]
    assert snapshot["time_range"] == "7d"
    assert snapshot["metrics"]["summary"] == dashboard["summary"]
    assert snapshot["metrics"]["online_log_summary"] == dashboard["online_log_summary"]


def test_sync_lifecycle_context_records_replaces_stale_anchor_edges_and_risks():
    store = SimpleNamespace(
        lifecycle_context_edges={
            "stale_edge": {
                "id": "stale_edge",
                "source_subject_id": "requirement_001",
                "source_subject_type": "requirement",
                "target_subject_id": "old_task",
                "target_subject_type": "ai_task",
            },
            "unrelated_edge": {
                "id": "unrelated_edge",
                "source_subject_id": "requirement_other",
                "source_subject_type": "requirement",
                "target_subject_id": "task_other",
                "target_subject_type": "ai_task",
            },
        },
        lifecycle_risk_signals={
            "stale_risk": {
                "id": "stale_risk",
                "requirement_id": "requirement_001",
                "source_subject_id": "bug_old",
                "source_subject_type": "bug",
                "task_id": "task_001",
            },
            "unrelated_risk": {
                "id": "unrelated_risk",
                "requirement_id": "requirement_other",
                "source_subject_id": "bug_other",
                "source_subject_type": "bug",
                "task_id": "task_other",
            },
        },
        ai_tasks={},
        bugs={},
        code_review_reports={},
        gitlab_daily_code_metrics={},
        iteration_plan_suggestions={},
        jenkins_release_records={},
        online_log_metrics={},
        user_feedback={},
    )
    store.snapshot = lambda value: dict(value)

    sync_lifecycle_context_records(
        store,
        subject={
            "id": "requirement_001",
            "product_id": "product_001",
            "type": "requirement",
        },
        upstream=[],
        downstream=[
            {
                "metadata": {"task_type": "technical_solution"},
                "relation_type": "generates_technical_solution",
                "subject_id": "task_002",
                "subject_type": "ai_task",
                "summary": "技术方案",
            }
        ],
        risk_signals=[
            {
                "impact_summary": "Review 高风险",
                "recommendation": "补充测试",
                "risk_type": "code_review_high_risk",
                "severity": "high",
                "source_subject_id": "report_001",
                "source_subject_type": "code_review_report",
            }
        ],
        tasks=[
            {
                "id": "task_001",
                "module_code": "core",
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "version_id": "version_001",
            }
        ],
    )

    assert "stale_edge" not in store.lifecycle_context_edges
    assert "unrelated_edge" in store.lifecycle_context_edges
    assert any(
        edge["target_subject_id"] == "task_002"
        for edge in store.lifecycle_context_edges.values()
    )
    assert "stale_risk" not in store.lifecycle_risk_signals
    assert "unrelated_risk" in store.lifecycle_risk_signals
    assert any(
        risk["source_subject_id"] == "report_001"
        for risk in store.lifecycle_risk_signals.values()
    )


def test_requirement_full_chain_returns_requirement_timeline_and_related_subjects(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    lifecycle = build_mvp_lifecycle(headers)
    evidence = add_v1_2_lifecycle_evidence(headers, lifecycle)

    response = client.get(
        f"/api/requirements/{lifecycle['requirement_id']}/full-chain",
        headers=headers,
    )

    assert response.status_code == 200
    full_chain = response.json()["data"]
    assert full_chain["requirement"]["id"] == lifecycle["requirement_id"]
    assert full_chain["product"]["id"] == lifecycle["product_id"]
    assert full_chain["iteration_version"]["id"] == lifecycle["version_id"]

    assert {task["id"] for task in full_chain["ai_tasks"]} >= {
        lifecycle["design_task_id"],
        lifecycle["solution_task_id"],
        lifecycle["review_task_id"],
    }
    assert {review["id"] for review in full_chain["reviews"]} >= {
        lifecycle["design_review_id"],
        lifecycle["review_id"],
    }
    assert {report["id"] for report in full_chain["code_review_reports"]} == {
        lifecycle["code_review_report_id"]
    }
    assert {snapshot["id"] for snapshot in full_chain["git_snapshots"]} == {
        lifecycle["snapshot_id"]
    }
    assert {branch["id"] for branch in full_chain["branch_configs"]} == {
        lifecycle["branch_config_id"]
    }
    assert {bug["id"] for bug in full_chain["bugs"]} == {evidence["bug_id"]}
    assert {release["id"] for release in full_chain["jenkins_releases"]} == {
        evidence["jenkins_release_id"]
    }
    assert lifecycle["knowledge_deposit_id"] in {
        deposit["id"] for deposit in full_chain["knowledge_deposits"]
    }
    assert lifecycle["audit_event_id"] in {
        audit_event["id"] for audit_event in full_chain["audit_events"]
    }

    timeline = full_chain["timeline"]
    assert {item["type"] for item in timeline} >= {
        "requirement",
        "iteration_version",
        "branch_config",
        "ai_task",
        "review",
        "git_snapshot",
        "code_review_report",
        "bug",
        "jenkins_release",
        "knowledge_deposit",
        "audit_event",
    }
    assert [item["occurred_at"] for item in timeline] == sorted(
        item["occurred_at"] for item in timeline
    )
    code_review_event = next(
        item
        for item in timeline
        if item["type"] == "code_review_report"
        and item["subject_id"] == lifecycle["code_review_report_id"]
    )
    assert code_review_event["title"] == f"代码评审：{lifecycle['code_review_report_id']}"
    assert code_review_event["metadata"]["summary"]
    assert full_chain["summary"] == {
        "ai_tasks": len(full_chain["ai_tasks"]),
        "reviews": len(full_chain["reviews"]),
        "git_snapshots": len(full_chain["git_snapshots"]),
        "branch_configs": len(full_chain["branch_configs"]),
        "code_review_reports": len(full_chain["code_review_reports"]),
        "code_inspection_reports": len(full_chain["code_inspection_reports"]),
        "bugs": len(full_chain["bugs"]),
        "deployment_requests": len(full_chain["deployment_requests"]),
        "jenkins_releases": len(full_chain["jenkins_releases"]),
        "knowledge_deposits": len(full_chain["knowledge_deposits"]),
        "execution_traces": len(full_chain["execution_traces"]),
        "audit_events": len(full_chain["audit_events"]),
        "timeline_events": len(timeline),
    }


def test_lifecycle_full_chain_resolves_subjects_to_requirement_chain(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    lifecycle = build_mvp_lifecycle(headers)
    evidence = add_v1_2_lifecycle_evidence(headers, lifecycle)
    report_id = "code_inspection_report_lifecycle"
    branch_config = app.state.store.product_version_branch_configs[lifecycle["branch_config_id"]]
    version_branch_report_id = "code_inspection_report_version_branch"
    app.state.store.code_inspection_reports[report_id] = {
        "branch": "main",
        "created_at": "2026-06-01T03:00:00+00:00",
        "created_bug_ids": [evidence["bug_id"]],
        "created_task_ids": [],
        "finding_count": 3,
        "id": report_id,
        "product_id": lifecycle["product_id"],
        "repository_id": "repo_lifecycle",
        "risk_level": "high",
        "scan_finished_at": "2026-06-01T03:05:00+00:00",
        "severe_finding_count": 1,
        "scheduled_job_run_id": "scheduled_job_run_full_chain",
        "status": "completed",
        "summary": "生命周期链路代码巡检",
    }
    app.state.store.code_inspection_reports[version_branch_report_id] = {
        "branch": branch_config["working_branch"],
        "created_at": "2026-06-01T03:10:00+00:00",
        "created_bug_ids": [],
        "created_task_ids": [],
        "finding_count": 1,
        "id": version_branch_report_id,
        "product_id": lifecycle["product_id"],
        "repository_id": branch_config["repository_id"],
        "risk_level": "medium",
        "scan_finished_at": "2026-06-01T03:12:00+00:00",
        "severe_finding_count": 0,
        "status": "completed",
        "summary": "版本分支代码巡检",
    }
    app.state.store.scheduled_job_runs["scheduled_job_run_full_chain"] = {
        "created_at": "2026-06-01T02:58:00+00:00",
        "finished_at": "2026-06-01T03:06:00+00:00",
        "id": "scheduled_job_run_full_chain",
        "result_summary": {"summary": "代码巡检全链路运行"},
        "scheduled_job_id": "scheduled_job_full_chain",
        "started_at": "2026-06-01T02:58:00+00:00",
        "status": "succeeded",
        "updated_at": "2026-06-01T03:06:00+00:00",
    }
    app.state.store.ai_executor_tasks["ai_executor_task_full_chain"] = {
        "ai_task_id": lifecycle["review_task_id"],
        "created_at": "2026-06-01T03:01:00+00:00",
        "executor_type": "codex",
        "id": "ai_executor_task_full_chain",
        "runner_id": "runner_full_chain",
        "scheduled_job_run_id": "scheduled_job_run_full_chain",
        "status": "completed",
        "updated_at": "2026-06-01T03:05:00+00:00",
    }
    app.state.store.model_gateway_logs.append(
        {
            "ai_task_id": lifecycle["review_task_id"],
            "created_at": "2026-06-01T03:02:00+00:00",
            "id": "model_gateway_log_full_chain",
            "model": "gpt-test",
            "provider": "openai",
            "purpose": "execution_trace_full_chain",
            "status": "succeeded",
            "updated_at": "2026-06-01T03:03:00+00:00",
        }
    )

    response = client.get(
        f"/api/lifecycle/full-chain?subject_type=code_inspection_report&subject_id={report_id}",
        headers=headers,
    )

    assert response.status_code == 200
    full_chain = response.json()["data"]
    assert full_chain["anchor"] == {
        "resolved_requirement_id": lifecycle["requirement_id"],
        "subject_id": report_id,
        "subject_type": "code_inspection_report",
    }
    assert full_chain["requirement"]["id"] == lifecycle["requirement_id"]
    assert {report["id"] for report in full_chain["code_inspection_reports"]} == {
        report_id,
        version_branch_report_id,
    }
    execution_trace_ids = {trace["id"] for trace in full_chain["execution_traces"]}
    execution_trace_root_types = {trace["root_type"] for trace in full_chain["execution_traces"]}
    assert "scheduled_job_run_full_chain" in execution_trace_ids
    assert "audit_event" not in execution_trace_root_types
    assert any(
        item["type"] == "code_inspection_report" and item["subject_id"] == report_id
        for item in full_chain["timeline"]
    )
    assert any(
        item["type"] == "execution_trace"
        and item["subject_id"] == "scheduled_job_run_full_chain"
        for item in full_chain["timeline"]
    )

    version_branch_report_response = client.get(
        "/api/lifecycle/full-chain"
        f"?subject_type=code_inspection_report&subject_id={version_branch_report_id}",
        headers=headers,
    )
    assert version_branch_report_response.status_code == 200
    version_branch_report_full_chain = version_branch_report_response.json()["data"]
    assert version_branch_report_full_chain["anchor"] == {
        "resolved_requirement_id": lifecycle["requirement_id"],
        "subject_id": version_branch_report_id,
        "subject_type": "code_inspection_report",
    }
    assert version_branch_report_full_chain["requirement"]["id"] == lifecycle[
        "requirement_id"
    ]

    bug_response = client.get(
        f"/api/lifecycle/full-chain?subject_type=bug&subject_id={evidence['bug_id']}",
        headers=headers,
    )
    assert bug_response.status_code == 200
    assert bug_response.json()["data"]["requirement"]["id"] == lifecycle["requirement_id"]

    version_response = client.get(
        f"/api/lifecycle/full-chain?subject_type=product_version&subject_id={lifecycle['version_id']}",
        headers=headers,
    )
    assert version_response.status_code == 200
    assert version_response.json()["data"]["requirement"]["id"] == lifecycle["requirement_id"]

    branch_config_response = client.get(
        "/api/lifecycle/full-chain"
        f"?subject_type=product_version_branch_config&subject_id={lifecycle['branch_config_id']}",
        headers=headers,
    )
    assert branch_config_response.status_code == 200
    branch_config_full_chain = branch_config_response.json()["data"]
    assert branch_config_full_chain["requirement"]["id"] == lifecycle["requirement_id"]
    assert branch_config_full_chain["anchor"] == {
        "resolved_requirement_id": lifecycle["requirement_id"],
        "subject_id": lifecycle["branch_config_id"],
        "subject_type": "product_version_branch_config",
    }

    branch_alias_response = client.get(
        "/api/lifecycle/full-chain"
        f"?subject_type=branch_config&subject_id={lifecycle['branch_config_id']}",
        headers=headers,
    )
    assert branch_alias_response.status_code == 200
    assert branch_alias_response.json()["data"]["requirement"]["id"] == lifecycle[
        "requirement_id"
    ]

    assistant_alias_response = client.get(
        f"/api/lifecycle/full-chain?subject_type=iteration_version&subject_id={lifecycle['version_id']}",
        headers=headers,
    )
    assert assistant_alias_response.status_code == 200
    assistant_alias_full_chain = assistant_alias_response.json()["data"]
    assert assistant_alias_full_chain["requirement"]["id"] == lifecycle["requirement_id"]
    assert assistant_alias_full_chain["anchor"] == {
        "resolved_requirement_id": lifecycle["requirement_id"],
        "subject_id": lifecycle["version_id"],
        "subject_type": "iteration_version",
    }

    scheduled_run_response = client.get(
        "/api/lifecycle/full-chain"
        "?subject_type=scheduled_job_run&subject_id=scheduled_job_run_full_chain",
        headers=headers,
    )
    assert scheduled_run_response.status_code == 200
    scheduled_run_full_chain = scheduled_run_response.json()["data"]
    assert scheduled_run_full_chain["requirement"]["id"] == lifecycle["requirement_id"]
    assert scheduled_run_full_chain["anchor"] == {
        "resolved_requirement_id": lifecycle["requirement_id"],
        "subject_id": "scheduled_job_run_full_chain",
        "subject_type": "scheduled_job_run",
    }

    execution_trace_response = client.get(
        "/api/lifecycle/full-chain"
        "?subject_type=execution_trace&subject_id=scheduled_job_run_full_chain",
        headers=headers,
    )
    assert execution_trace_response.status_code == 200
    assert execution_trace_response.json()["data"]["requirement"]["id"] == lifecycle[
        "requirement_id"
    ]

    executor_task_response = client.get(
        "/api/lifecycle/full-chain"
        "?subject_type=ai_executor_task&subject_id=ai_executor_task_full_chain",
        headers=headers,
    )
    assert executor_task_response.status_code == 200
    assert executor_task_response.json()["data"]["requirement"]["id"] == lifecycle[
        "requirement_id"
    ]

    model_log_response = client.get(
        "/api/lifecycle/full-chain"
        "?subject_type=model_gateway_log&subject_id=model_gateway_log_full_chain",
        headers=headers,
    )
    assert model_log_response.status_code == 200
    assert model_log_response.json()["data"]["requirement"]["id"] == lifecycle[
        "requirement_id"
    ]


def test_requirement_full_chain_enforces_product_scope():
    store = build_minimal_full_chain_store()

    with pytest.raises(HTTPException) as blocked:
        get_requirement_full_chain_response(
            current_store=store,
            requirement_id="requirement_alpha",
            user=scoped_reader("product_beta"),
        )

    assert blocked.value.status_code == 404
    assert blocked.value.detail["code"] == "NOT_FOUND"

    allowed = get_requirement_full_chain_response(
        current_store=store,
        requirement_id="requirement_alpha",
        user=scoped_reader("product_alpha"),
    )

    assert allowed["requirement"]["id"] == "requirement_alpha"
    assert allowed["product"]["id"] == "product_alpha"
    assert {task["id"] for task in allowed["ai_tasks"]} == {"task_alpha"}


def test_lifecycle_full_chain_subject_anchor_enforces_product_scope():
    store = build_minimal_full_chain_store()
    store.ai_executor_tasks["ai_executor_task_alpha"] = {
        "ai_task_id": "task_alpha",
        "created_at": "2026-06-27T01:16:00+00:00",
        "executor_type": "codex",
        "id": "ai_executor_task_alpha",
        "runner_id": "runner_alpha",
        "status": "completed",
        "updated_at": "2026-06-27T01:18:00+00:00",
    }

    with pytest.raises(HTTPException) as blocked:
        get_requirement_full_chain_by_subject_response(
            current_store=store,
            subject_id="version_alpha",
            subject_type="product_version",
            user=scoped_reader("product_beta"),
        )

    assert blocked.value.status_code == 404
    assert blocked.value.detail["code"] == "NOT_FOUND"

    allowed = get_requirement_full_chain_by_subject_response(
        current_store=store,
        subject_id="version_alpha",
        subject_type="product_version",
        user=scoped_reader("product_alpha"),
    )

    assert allowed["anchor"] == {
        "resolved_requirement_id": "requirement_alpha",
        "subject_id": "version_alpha",
        "subject_type": "product_version",
    }
    assert allowed["requirement"]["id"] == "requirement_alpha"

    with pytest.raises(HTTPException) as blocked_branch_config:
        get_requirement_full_chain_by_subject_response(
            current_store=store,
            subject_id="branch_config_alpha",
            subject_type="product_version_branch_config",
            user=scoped_reader("product_beta"),
        )

    assert blocked_branch_config.value.status_code == 404
    assert blocked_branch_config.value.detail["code"] == "NOT_FOUND"

    allowed_branch_config = get_requirement_full_chain_by_subject_response(
        current_store=store,
        subject_id="branch_config_alpha",
        subject_type="product_version_branch_config",
        user=scoped_reader("product_alpha"),
    )

    assert allowed_branch_config["anchor"] == {
        "resolved_requirement_id": "requirement_alpha",
        "subject_id": "branch_config_alpha",
        "subject_type": "product_version_branch_config",
    }
    assert allowed_branch_config["requirement"]["id"] == "requirement_alpha"

    with pytest.raises(HTTPException) as blocked_executor_task:
        get_requirement_full_chain_by_subject_response(
            current_store=store,
            subject_id="ai_executor_task_alpha",
            subject_type="ai_executor_task",
            user=scoped_reader("product_beta"),
        )

    assert blocked_executor_task.value.status_code == 404
    assert blocked_executor_task.value.detail["code"] == "NOT_FOUND"

    allowed_executor_task = get_requirement_full_chain_by_subject_response(
        current_store=store,
        subject_id="ai_executor_task_alpha",
        subject_type="ai_executor_task",
        user=scoped_reader("product_alpha"),
    )

    assert allowed_executor_task["anchor"] == {
        "resolved_requirement_id": "requirement_alpha",
        "subject_id": "ai_executor_task_alpha",
        "subject_type": "ai_executor_task",
    }
    assert allowed_executor_task["requirement"]["id"] == "requirement_alpha"


def test_lifecycle_full_chain_returns_empty_version_payload_without_requirements():
    store = build_minimal_full_chain_store()
    store.requirements.clear()
    store.ai_tasks.clear()
    store.code_inspection_reports["inspection_alpha"] = {
        "branch": "feature/alpha",
        "created_at": "2026-06-27T02:00:00+00:00",
        "created_bug_ids": [],
        "created_task_ids": [],
        "finding_count": 1,
        "id": "inspection_alpha",
        "product_id": "product_alpha",
        "repository_id": "repo_alpha",
        "risk_level": "medium",
        "scan_finished_at": "2026-06-27T02:05:00+00:00",
        "severe_finding_count": 0,
        "status": "completed",
        "summary": "空版本分支巡检",
    }
    store.jenkins_release_records["release_alpha"] = {
        "build_id": "42",
        "created_at": "2026-06-27T03:00:00+00:00",
        "id": "release_alpha",
        "job_name": "alpha-release",
        "product_id": "product_alpha",
        "status": "succeeded",
        "version_id": "version_alpha",
    }

    payload = get_requirement_full_chain_by_subject_response(
        current_store=store,
        subject_id="version_alpha",
        subject_type="product_version",
        user=scoped_reader("product_alpha"),
    )

    assert payload["status"] == "empty"
    assert payload["empty_reason"] == "iteration_version_has_no_requirements"
    assert payload["requirement"] is None
    assert payload["product"]["id"] == "product_alpha"
    assert payload["iteration_version"]["id"] == "version_alpha"
    assert payload["anchor"] == {
        "subject_id": "version_alpha",
        "subject_type": "product_version",
    }
    assert {branch["id"] for branch in payload["branch_configs"]} == {"branch_config_alpha"}
    assert {report["id"] for report in payload["code_inspection_reports"]} == {
        "inspection_alpha"
    }
    assert {release["id"] for release in payload["jenkins_releases"]} == {"release_alpha"}
    assert payload["summary"]["branch_configs"] == 1
    assert payload["summary"]["code_inspection_reports"] == 1
    assert payload["summary"]["jenkins_releases"] == 1
    assert payload["summary"]["timeline_events"] == len(payload["timeline"])
    assert {item["type"] for item in payload["timeline"]} >= {
        "branch_config",
        "code_inspection_report",
        "iteration_version",
        "jenkins_release",
    }

    branch_payload = get_requirement_full_chain_by_subject_response(
        current_store=store,
        subject_id="branch_config_alpha",
        subject_type="product_version_branch_config",
        user=scoped_reader("product_alpha"),
    )

    assert branch_payload["status"] == "empty"
    assert branch_payload["anchor"] == {
        "subject_id": "branch_config_alpha",
        "subject_type": "product_version_branch_config",
    }
    assert branch_payload["requirement"] is None


def test_lifecycle_context_requires_query_anchor():
    headers = auth_headers()

    response = client.get("/api/lifecycle/context", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "LIFECYCLE_SUBJECT_REQUIRED"


def test_lifecycle_context_traces_from_review_and_report_subjects(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    lifecycle = build_mvp_lifecycle(headers)

    review_context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=human_review&subject_id={lifecycle['design_review_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]

    assert review_context["subject"] == {
        "type": "human_review",
        "id": lifecycle["design_review_id"],
        "product_id": lifecycle["product_id"],
    }
    assert [item["subject_id"] for item in review_context["upstream"]] == [
        lifecycle["requirement_id"]
    ]
    review_downstream = review_context["downstream"]
    assert {
        item["subject_id"]
        for item in review_downstream
        if item["subject_type"] == "ai_task"
    } == {lifecycle["design_task_id"]}
    assert any(
        item["subject_type"] == "human_review"
        and item["subject_id"] == lifecycle["design_review_id"]
        for item in review_downstream
    )
    assert not any(
        item["subject_type"] == "ai_task"
        and item["subject_id"] == lifecycle["solution_task_id"]
        for item in review_downstream
    )

    report_context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=code_review_report&subject_id={lifecycle['code_review_report_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]

    assert report_context["subject"] == {
        "type": "code_review_report",
        "id": lifecycle["code_review_report_id"],
        "product_id": lifecycle["product_id"],
    }
    assert {
        item["subject_id"]
        for item in report_context["downstream"]
        if item["subject_type"] == "ai_task"
    } == {lifecycle["review_task_id"]}
    assert report_context["risk_signals"][0]["source_subject_id"] == lifecycle[
        "code_review_report_id"
    ]


def test_lifecycle_context_traces_from_writeback_deposit_and_audit_subjects(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    lifecycle = build_mvp_lifecycle(headers)

    writeback_context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=mock_issue&subject_id={lifecycle['mock_issue_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]
    assert writeback_context["subject"] == {
        "type": "mock_issue",
        "id": lifecycle["mock_issue_id"],
        "product_id": lifecycle["product_id"],
    }
    assert {
        item["subject_id"]
        for item in writeback_context["downstream"]
        if item["subject_type"] == "ai_task"
    } == {lifecycle["design_task_id"]}

    deposit_context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=knowledge_deposit&subject_id={lifecycle['knowledge_deposit_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]
    assert deposit_context["subject"] == {
        "type": "knowledge_deposit",
        "id": lifecycle["knowledge_deposit_id"],
        "product_id": lifecycle["product_id"],
    }
    assert {
        item["subject_id"]
        for item in deposit_context["downstream"]
        if item["subject_type"] == "ai_task"
    } == {lifecycle["design_task_id"]}

    audit_context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=audit_event&subject_id={lifecycle['audit_event_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]
    assert audit_context["subject"] == {
        "type": "audit_event",
        "id": lifecycle["audit_event_id"],
        "product_id": lifecycle["product_id"],
    }
    assert {
        item["subject_id"]
        for item in audit_context["downstream"]
        if item["subject_type"] == "ai_task"
    } == {lifecycle["design_task_id"]}


def test_lifecycle_context_rejects_unknown_subject_type():
    headers = auth_headers()

    response = client.get(
        "/api/lifecycle/context?subject_type=unknown_subject&subject_id=subject_1",
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_lifecycle_context_links_v1_2_evidence_and_dynamic_missing_context(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    lifecycle = build_mvp_lifecycle(headers)
    evidence = add_v1_2_lifecycle_evidence(headers, lifecycle)

    context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=requirement&subject_id={lifecycle['requirement_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]

    downstream_subjects = {
        (item["subject_type"], item["subject_id"])
        for item in context["downstream"]
    }
    assert ("bug", evidence["bug_id"]) in downstream_subjects
    assert ("gitlab_daily_code_metric", evidence["gitlab_metric_id"]) in downstream_subjects
    assert ("jenkins_release", evidence["jenkins_release_id"]) in downstream_subjects
    assert ("online_log_metric", evidence["online_log_metric_id"]) in downstream_subjects
    assert ("user_usage_metric", evidence["usage_metric_id"]) in downstream_subjects
    assert ("user_feedback", evidence["feedback_id"]) in downstream_subjects
    assert ("iteration_plan_suggestion", evidence["iteration_suggestion_id"]) in downstream_subjects

    risk_types = {signal["risk_type"] for signal in context["risk_signals"]}
    assert {
        "critical_bug_open",
        "gitlab_code_risk",
        "jenkins_release_failed",
        "online_error_rate_high",
        "negative_user_feedback",
        "iteration_suggestion_low_confidence",
    }.issubset(risk_types)
    assert "bug" not in context["missing_context"]
    assert "gitlab_daily_code_metric" not in context["missing_context"]
    assert "jenkins_release" not in context["missing_context"]
    assert "online_log_metric" not in context["missing_context"]
    assert "user_usage_metric" not in context["missing_context"]
    assert "user_feedback" not in context["missing_context"]
    assert "iteration_plan_suggestion" not in context["missing_context"]

    metric_context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=gitlab_daily_code_metric&subject_id={evidence['gitlab_metric_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]
    assert metric_context["subject"] == {
        "type": "gitlab_daily_code_metric",
        "id": evidence["gitlab_metric_id"],
        "product_id": lifecycle["product_id"],
    }
    assert {
        item["subject_id"]
        for item in metric_context["downstream"]
        if item["subject_type"] == "ai_task"
    } == {
        lifecycle["design_task_id"],
        lifecycle["solution_task_id"],
        lifecycle["review_task_id"],
    }


def test_lifecycle_context_reports_missing_v1_2_context_dynamically(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    lifecycle = build_mvp_lifecycle(headers)

    context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=requirement&subject_id={lifecycle['requirement_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]

    assert {
        "bug",
        "gitlab_daily_code_metric",
        "jenkins_release",
        "online_log_metric",
        "user_usage_metric",
        "user_feedback",
        "iteration_plan_suggestion",
    }.issubset(set(context["missing_context"]))
