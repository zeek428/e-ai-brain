from types import SimpleNamespace

from fastapi.testclient import TestClient
from gitlab_fakes import install_real_gitlab_api_stub

from app.main import app
from app.services.lifecycle_risks import sync_lifecycle_context_records

client = TestClient(app)


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
    assert {bug["id"] for bug in full_chain["bugs"]} == {evidence["bug_id"]}
    assert {release["id"] for release in full_chain["jenkins_releases"]} == {
        evidence["jenkins_release_id"]
    }
    assert lifecycle["knowledge_deposit_id"] in {
        deposit["id"] for deposit in full_chain["knowledge_deposits"]
    }

    timeline = full_chain["timeline"]
    assert {item["type"] for item in timeline} >= {
        "requirement",
        "iteration_version",
        "ai_task",
        "review",
        "git_snapshot",
        "code_review_report",
        "bug",
        "jenkins_release",
        "knowledge_deposit",
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
        "code_review_reports": len(full_chain["code_review_reports"]),
        "bugs": len(full_chain["bugs"]),
        "jenkins_releases": len(full_chain["jenkins_releases"]),
        "knowledge_deposits": len(full_chain["knowledge_deposits"]),
        "timeline_events": len(timeline),
    }


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
