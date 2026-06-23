from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def seed_execution_trace_records() -> None:
    store = app.state.store
    store.scheduled_job_runs["scheduled_job_run_trace"] = {
        "created_at": "2026-06-20T01:00:00+00:00",
        "error_message": None,
        "finished_at": "2026-06-20T01:00:08+00:00",
        "id": "scheduled_job_run_trace",
        "latency_ms": 8000,
        "records_imported": 1,
        "result_summary": {
            "execution_nodes": {
                "data_connection": {
                    "duration_ms": 1200,
                    "id": "data_connection",
                    "label": "数据连接",
                    "plugin_invocation_log_id": "plugin_invocation_log_trace",
                    "status": "succeeded",
                    "summary": "插件采集完成。",
                },
                "runner_execution": {
                    "duration_ms": 4600,
                    "id": "runner_execution",
                    "label": "Runner 执行",
                    "model_gateway_log_id": "model_gateway_log_trace",
                    "status": "succeeded",
                    "summary": "本地执行器完成扫描。",
                },
                "result_action": {
                    "duration_ms": 600,
                    "id": "result_action",
                    "label": "结果写入",
                    "status": "succeeded",
                    "summary": "已写入代码巡检报告。",
                },
            },
            "summary": "代码仓库质量安全规范巡检完成。",
        },
        "scheduled_job_id": "scheduled_job_trace",
        "started_at": "2026-06-20T01:00:00+00:00",
        "status": "succeeded",
        "trigger_type": "manual",
        "updated_at": "2026-06-20T01:00:08+00:00",
    }
    store.plugin_invocation_logs["plugin_invocation_log_trace"] = {
        "action_id": "plugin_action_trace",
        "connection_id": "plugin_connection_trace",
        "created_at": "2026-06-20T01:00:01+00:00",
        "error_code": None,
        "error_message": None,
        "id": "plugin_invocation_log_trace",
        "latency_ms": 1200,
        "plugin_id": "plugin_trace",
        "request_summary": {
            "headers": {
                "Authorization": "Bearer secret-run-token",
            },
        },
        "response_summary": {"records": 1},
        "scheduled_job_id": "scheduled_job_trace",
        "scheduled_job_run_id": "scheduled_job_run_trace",
        "status": "succeeded",
        "trace_id": "trace-001",
        "updated_at": "2026-06-20T01:00:02+00:00",
    }
    store.ai_executor_tasks["ai_executor_task_trace"] = {
        "ai_task_id": "ai_task_trace",
        "claimed_at": "2026-06-20T01:00:02+00:00",
        "created_at": "2026-06-20T01:00:01+00:00",
        "error_message": None,
        "executor_type": "codex",
        "finished_at": "2026-06-20T01:00:07+00:00",
        "id": "ai_executor_task_trace",
        "plugin_invocation_log_id": "plugin_invocation_log_trace",
        "request_config": {"token": "runner-secret-token"},
        "result_json": {"summary": "扫描完成"},
        "runner_id": "ai_executor_runner_001",
        "scheduled_job_id": "scheduled_job_trace",
        "scheduled_job_run_id": "scheduled_job_run_trace",
        "status": "succeeded",
        "workspace_root": "/Users/zeek/source/e-ai-brain",
    }
    store.model_gateway_logs.append(
        {
            "ai_task_id": "ai_task_trace",
            "created_at": "2026-06-20T01:00:03+00:00",
            "error": None,
            "id": "model_gateway_log_trace",
            "latency_ms": 900,
            "model": "gpt-5.5",
            "model_gateway_config_id": "model_gateway_config_trace",
            "provider": "openai_compatible",
            "purpose": "code_inspection",
            "status": "success",
            "tokens": {"prompt": 100, "completion": 20},
            "updated_at": "2026-06-20T01:00:04+00:00",
        }
    )
    store.code_inspection_reports["code_inspection_report_trace"] = {
        "branch": "main",
        "commit_sha": "abc1234",
        "created_at": "2026-06-20T01:00:07+00:00",
        "finding_count": 1,
        "id": "code_inspection_report_trace",
        "plugin_invocation_log_id": "plugin_invocation_log_trace",
        "product_id": "product_trace",
        "quality_gate": {"status": "passed"},
        "repository_id": "repo_trace",
        "risk_level": "medium",
        "scan_finished_at": "2026-06-20T01:00:08+00:00",
        "scan_started_at": "2026-06-20T01:00:02+00:00",
        "scheduled_job_id": "scheduled_job_trace",
        "scheduled_job_run_id": "scheduled_job_run_trace",
        "severe_finding_count": 0,
        "status": "completed",
        "summary": "发现 1 个 medium 问题。",
        "updated_at": "2026-06-20T01:00:08+00:00",
    }
    store.audit_events.append(
        {
            "actor_id": "user_admin",
            "created_at": "2026-06-20T01:00:09+00:00",
            "event_type": "scheduled_job.run.completed",
            "id": "audit_trace",
            "payload": {"api_key": "sk-test-secret", "message": "done"},
            "result": "success",
            "sequence": 1,
            "subject_id": "scheduled_job_run_trace",
            "subject_type": "scheduled_job_run",
        }
    )


def test_execution_trace_lists_related_runtime_nodes_and_redacts_secrets():
    app.state.store.reset()
    seed_execution_trace_records()
    headers = auth_headers()

    response = client.get(
        "/api/governance/execution-traces?page=1&page_size=10&sort_by=started_at&sort_order=desc",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == "scheduled_job_run_trace"
    assert item["root_type"] == "scheduled_job_run"
    assert item["status"] == "succeeded"
    assert item["node_count"] >= 8
    assert item["related_ids"]["plugin_invocation_log"] == ["plugin_invocation_log_trace"]
    assert item["related_ids"]["ai_executor_task"] == ["ai_executor_task_trace"]
    assert item["related_ids"]["model_gateway_log"] == ["model_gateway_log_trace"]
    assert item["related_ids"]["code_inspection_report"] == ["code_inspection_report_trace"]
    assert item["related_ids"]["audit_event"] == ["audit_trace"]

    detail_response = client.get(
        "/api/governance/execution-traces/plugin_invocation_log_trace",
        headers=headers,
    )

    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()["data"]
    assert detail["root_id"] == "scheduled_job_run_trace"
    source_types = {node["source_type"] for node in detail["nodes"]}
    assert {
        "ai_executor_task",
        "audit_event",
        "code_inspection_report",
        "model_gateway_log",
        "plugin_invocation_log",
        "scheduled_job_run",
        "scheduled_job_stage",
    }.issubset(source_types)
    assert any(edge["label"] == "dispatches" for edge in detail["edges"])
    assert any(edge["label"] == "writes_report" for edge in detail["edges"])
    serialized_detail = str(detail)
    assert "secret-run-token" not in serialized_detail
    assert "runner-secret-token" not in serialized_detail
    assert "sk-test-secret" not in serialized_detail
    assert "<redacted>" in serialized_detail


def test_execution_trace_requires_admin_diagnostics_permission():
    app.state.store.reset()
    seed_execution_trace_records()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    response = client.get("/api/governance/execution-traces", headers=reviewer_headers)

    assert response.status_code == 403
