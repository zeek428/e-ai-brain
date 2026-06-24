from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.services.execution_traces import (
    EXECUTION_TRACE_SNAPSHOT_REFRESH_STATE_ATTR,
    get_execution_trace_response,
    list_execution_traces_response,
)

client = TestClient(app)


class FakeExecutionTraceRepository:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.refresh_calls = 0
        self.snapshots: dict[str, dict[str, Any]] = {}

    def list_audit_events(self) -> list[dict[str, Any]]:
        return list(self.store.audit_events)

    def list_code_inspection_reports(self) -> list[dict[str, Any]]:
        return list(self.store.code_inspection_reports.values())

    def list_model_gateway_logs(self) -> list[dict[str, Any]]:
        return list(self.store.model_gateway_logs)

    def list_plugin_invocation_logs(self) -> list[dict[str, Any]]:
        return list(self.store.plugin_invocation_logs.values())

    def list_ai_executor_tasks(self) -> list[dict[str, Any]]:
        return list(self.store.ai_executor_tasks.values())

    def list_scheduled_job_runs(self) -> list[dict[str, Any]]:
        return list(self.store.scheduled_job_runs.values())

    def list_execution_trace_assistant_chat_runs(self) -> list[dict[str, Any]]:
        return list(self.store.assistant_chat_runs.values())

    def refresh_execution_trace_snapshots(self, traces: list[dict[str, Any]]) -> None:
        self.refresh_calls += 1
        self.snapshots = {str(trace["id"]): trace for trace in traces}

    def _filtered(
        self,
        *,
        keyword: str | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        traces = list(self.snapshots.values())
        normalized_source_id = str(source_id or "").strip()
        if normalized_source_id:
            traces = [
                trace
                for trace in traces
                if trace["id"] == normalized_source_id
                or trace["root_id"] == normalized_source_id
                or any(
                    normalized_source_id in values
                    for values in trace.get("related_ids", {}).values()
                )
                or any(
                    node.get("source_id") == normalized_source_id
                    for node in trace.get("nodes", [])
                )
            ]
        if source_type:
            traces = [
                trace
                for trace in traces
                if trace["root_type"] == source_type
                or any(node.get("source_type") == source_type for node in trace.get("nodes", []))
            ]
        if status:
            traces = [trace for trace in traces if trace["status"] == status]
        normalized_keyword = str(keyword or "").strip().lower()
        if normalized_keyword:
            traces = [
                trace
                for trace in traces
                if normalized_keyword
                in " ".join(
                    [
                        str(trace.get("id", "")),
                        str(trace.get("root_id", "")),
                        str(trace.get("root_type", "")),
                        str(trace.get("title", "")),
                        str(trace.get("summary", "")),
                        str(trace.get("related_ids", "")),
                    ]
                ).lower()
            ]
        return traces

    def count_execution_trace_snapshots(
        self,
        *,
        created_from: Any = None,
        created_to: Any = None,
        keyword: str | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> int:
        return len(
            self._filtered(
                keyword=keyword,
                source_id=source_id,
                source_type=source_type,
                status=status,
            )
        )

    def list_execution_trace_snapshots(
        self,
        *,
        created_from: Any = None,
        created_to: Any = None,
        keyword: str | None = None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        source_id: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        traces = self._filtered(
            keyword=keyword,
            source_id=source_id,
            source_type=source_type,
            status=status,
        )
        traces = sorted(
            traces,
            key=lambda trace: str(trace.get(sort_by) or ""),
            reverse=sort_order == "desc",
        )
        return traces[offset : offset + limit]

    def get_execution_trace_snapshot(self, trace_id: str) -> dict[str, Any] | None:
        for trace in self.snapshots.values():
            if trace["id"] == trace_id or trace["root_id"] == trace_id:
                return trace
            if any(trace_id in values for values in trace.get("related_ids", {}).values()):
                return trace
            if any(node.get("source_id") == trace_id for node in trace.get("nodes", [])):
                return trace
        return None


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def clear_execution_trace_refresh_state() -> None:
    if hasattr(app.state.store, EXECUTION_TRACE_SNAPSHOT_REFRESH_STATE_ATTR):
        delattr(app.state.store, EXECUTION_TRACE_SNAPSHOT_REFRESH_STATE_ATTR)


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


def seed_assistant_execution_trace_records() -> None:
    store = app.state.store
    store.assistant_chat_runs["assistant_chat_run_trace"] = {
        "assistant_message_id": "assistant_message_trace",
        "client_request_id": "client_request_trace",
        "conversation_id": "assistant_conversation_trace",
        "created_at": "2026-06-20T02:00:00+00:00",
        "error_code": "MODEL_GATEWAY_FAILED",
        "error_message": "模型网关调用失败",
        "finished_at": "2026-06-20T02:00:05+00:00",
        "id": "assistant_chat_run_trace",
        "metadata_json": {
            "context_source": "assistant-page",
            "message_excerpt": "请帮我诊断这次失败",
            "product_id": "product_trace",
            "reference_count": 1,
        },
        "started_at": "2026-06-20T02:00:00+00:00",
        "status": "failed",
        "updated_at": "2026-06-20T02:00:05+00:00",
        "user_id": "user_admin",
        "user_message_id": "assistant_user_message_trace",
    }
    store.model_gateway_logs.append(
        {
            "created_at": "2026-06-20T02:00:01+00:00",
            "error": "upstream timeout",
            "id": "model_gateway_log_assistant_trace",
            "latency_ms": 1800,
            "model": "gpt-5.5",
            "model_gateway_config_id": "model_gateway_config_trace",
            "provider": "openai_compatible",
            "purpose": "assistant_chat",
            "status": "failed",
            "tokens": {"prompt": 120, "completion": 0},
            "updated_at": "2026-06-20T02:00:03+00:00",
        }
    )
    store.audit_events.append(
        {
            "actor_id": "user_admin",
            "created_at": "2026-06-20T02:00:05+00:00",
            "event_type": "assistant.chat_failed",
            "id": "audit_assistant_trace",
            "payload": {
                "api_key": "sk-assistant-secret",
                "chat_run_id": "assistant_chat_run_trace",
                "model_log_id": "model_gateway_log_assistant_trace",
            },
            "result": "failed",
            "sequence": 2,
            "subject_id": "assistant_conversation_trace",
            "subject_type": "assistant_conversation",
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
    assert item["related_ids"]["result_write_record"] == [
        "result_write_record_scheduled_job_run_trace"
    ]
    assert item["related_ids"]["audit_event"] == ["audit_trace"]

    detail_response = client.get(
        "/api/governance/execution-traces/result_write_record_scheduled_job_run_trace",
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
        "result_write_record",
        "scheduled_job_run",
        "scheduled_job_stage",
    }.issubset(source_types)
    assert any(edge["label"] == "dispatches" for edge in detail["edges"])
    assert any(edge["label"] == "writes_report" for edge in detail["edges"])
    assert any(edge["label"] == "writes_result" for edge in detail["edges"])
    serialized_detail = str(detail)
    assert "secret-run-token" not in serialized_detail
    assert "runner-secret-token" not in serialized_detail
    assert "sk-test-secret" not in serialized_detail
    assert "<redacted>" in serialized_detail


def test_execution_trace_includes_assistant_chat_run_model_and_audit_nodes():
    app.state.store.reset()
    seed_assistant_execution_trace_records()
    headers = auth_headers()

    response = client.get(
        "/api/governance/execution-traces?source_type=assistant_chat_run&page=1&page_size=10",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == "assistant_chat_run_trace"
    assert item["root_type"] == "assistant_chat_run"
    assert item["status"] == "failed"
    assert item["related_ids"]["assistant_message"] == [
        "assistant_message_trace",
        "assistant_user_message_trace",
    ]
    assert item["related_ids"]["model_gateway_log"] == ["model_gateway_log_assistant_trace"]
    assert item["related_ids"]["audit_event"] == ["audit_assistant_trace"]

    detail_response = client.get(
        "/api/governance/execution-traces/model_gateway_log_assistant_trace",
        headers=headers,
    )

    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()["data"]
    assert detail["root_id"] == "assistant_chat_run_trace"
    source_types = {node["source_type"] for node in detail["nodes"]}
    assert {"assistant_chat_run", "assistant_message", "audit_event", "model_gateway_log"}.issubset(
        source_types
    )
    assert any(edge["label"] == "calls_model" for edge in detail["edges"])
    assert any(edge["label"] == "triggers" for edge in detail["edges"])
    assert any(edge["label"] == "writes_message" for edge in detail["edges"])
    serialized_detail = str(detail)
    assert "sk-assistant-secret" not in serialized_detail
    assert "<redacted>" in serialized_detail


def test_execution_trace_list_filters_by_any_related_source_id():
    app.state.store.reset()
    seed_assistant_execution_trace_records()
    headers = auth_headers()

    response = client.get(
        "/api/governance/execution-traces"
        "?source_id=model_gateway_log_assistant_trace&page=1&page_size=10",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["id"] == "assistant_chat_run_trace"
    assert body["items"][0]["root_type"] == "assistant_chat_run"

    message_response = client.get(
        "/api/governance/execution-traces"
        "?source_id=assistant_message_trace&page=1&page_size=10",
        headers=headers,
    )

    assert message_response.status_code == 200, message_response.text
    message_body = message_response.json()["data"]
    assert message_body["total"] == 1
    assert message_body["items"][0]["id"] == "assistant_chat_run_trace"

    message_type_response = client.get(
        "/api/governance/execution-traces"
        "?source_type=assistant_message&page=1&page_size=10",
        headers=headers,
    )

    assert message_type_response.status_code == 200, message_type_response.text
    message_type_body = message_type_response.json()["data"]
    assert message_type_body["total"] == 1
    assert message_type_body["items"][0]["id"] == "assistant_chat_run_trace"


def test_execution_trace_list_filters_by_result_write_record_source():
    app.state.store.reset()
    seed_execution_trace_records()
    headers = auth_headers()

    response = client.get(
        "/api/governance/execution-traces"
        "?source_type=result_write_record&source_id=result_write_record_scheduled_job_run_trace"
        "&page=1&page_size=10",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["id"] == "scheduled_job_run_trace"
    assert body["items"][0]["root_type"] == "scheduled_job_run"
    assert body["items"][0]["related_ids"]["result_write_record"] == [
        "result_write_record_scheduled_job_run_trace"
    ]


def test_execution_trace_list_filters_by_scheduled_job_stage_source():
    app.state.store.reset()
    seed_execution_trace_records()
    headers = auth_headers()

    response = client.get(
        "/api/governance/execution-traces"
        "?source_type=scheduled_job_stage"
        "&source_id=scheduled_job_run_trace:runner_execution"
        "&page=1&page_size=10",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["id"] == "scheduled_job_run_trace"
    assert body["items"][0]["root_type"] == "scheduled_job_run"
    assert "scheduled_job_run_trace:runner_execution" in body["items"][0]["related_ids"][
        "scheduled_job_stage"
    ]


def test_execution_trace_requires_admin_diagnostics_permission():
    app.state.store.reset()
    seed_execution_trace_records()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    response = client.get("/api/governance/execution-traces", headers=reviewer_headers)

    assert response.status_code == 403


def test_execution_trace_uses_repository_snapshots_when_available():
    app.state.store.reset()
    clear_execution_trace_refresh_state()
    seed_execution_trace_records()
    repository = FakeExecutionTraceRepository(app.state.store)
    old_repository = getattr(app.state.store, "repository", None)
    app.state.store.repository = repository
    try:
        response = list_execution_traces_response(
            created_from=None,
            created_to=None,
            current_store=app.state.store,
            keyword="质量安全",
            page=1,
            page_size=10,
            sort_by="started_at",
            sort_order="desc",
            source_id=None,
            source_type=None,
            started_at=None,
            status=None,
            trace_id="trace-test",
        )

        body = response["data"]
        assert body["total"] == 1
        assert body["items"][0]["id"] == "scheduled_job_run_trace"
        assert body["items"][0]["related_ids"]["plugin_invocation_log"] == [
            "plugin_invocation_log_trace"
        ]
        assert repository.refresh_calls == 1

        detail = get_execution_trace_response(
            current_store=app.state.store,
            trace_id="plugin_invocation_log_trace",
        )

        assert detail["root_id"] == "scheduled_job_run_trace"
        assert repository.refresh_calls == 1
    finally:
        clear_execution_trace_refresh_state()
        if old_repository is None:
            delattr(app.state.store, "repository")
        else:
            app.state.store.repository = old_repository


def test_execution_trace_reuses_fresh_repository_snapshots_for_repeated_lists():
    app.state.store.reset()
    clear_execution_trace_refresh_state()
    seed_execution_trace_records()
    repository = FakeExecutionTraceRepository(app.state.store)
    old_repository = getattr(app.state.store, "repository", None)
    app.state.store.repository = repository
    try:
        for _ in range(2):
            response = list_execution_traces_response(
                created_from=None,
                created_to=None,
                current_store=app.state.store,
                keyword=None,
                page=1,
                page_size=10,
                sort_by="started_at",
                sort_order="desc",
                source_id=None,
                source_type=None,
                started_at=None,
                status=None,
                trace_id="trace-test",
            )
            assert response["data"]["total"] == 1

        assert repository.refresh_calls == 1
    finally:
        clear_execution_trace_refresh_state()
        if old_repository is None:
            delattr(app.state.store, "repository")
        else:
            app.state.store.repository = old_repository


def test_execution_trace_detail_forces_refresh_when_fresh_snapshot_misses():
    app.state.store.reset()
    clear_execution_trace_refresh_state()
    seed_execution_trace_records()
    repository = FakeExecutionTraceRepository(app.state.store)
    old_repository = getattr(app.state.store, "repository", None)
    app.state.store.repository = repository
    try:
        response = list_execution_traces_response(
            created_from=None,
            created_to=None,
            current_store=app.state.store,
            keyword=None,
            page=1,
            page_size=10,
            sort_by="started_at",
            sort_order="desc",
            source_id=None,
            source_type=None,
            started_at=None,
            status=None,
            trace_id="trace-test",
        )
        assert response["data"]["total"] == 1
        assert repository.refresh_calls == 1

        seed_assistant_execution_trace_records()
        detail = get_execution_trace_response(
            current_store=app.state.store,
            trace_id="model_gateway_log_assistant_trace",
        )

        assert detail["root_id"] == "assistant_chat_run_trace"
        assert repository.refresh_calls == 2
    finally:
        clear_execution_trace_refresh_state()
        if old_repository is None:
            delattr(app.state.store, "repository")
        else:
            app.state.store.repository = old_repository
