import json
from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.services.scheduled_job_ai_capabilities as scheduled_job_ai_capabilities_service
import app.services.scheduled_job_ai_processing as scheduled_job_ai_processing_service
import app.services.scheduled_job_config as scheduled_job_config
import app.services.scheduled_job_data_connections as scheduled_job_data_connections_service
import app.services.scheduled_job_result_actions as scheduled_job_result_actions_service
import app.services.scheduled_job_user_feedback as scheduled_job_user_feedback_service
import app.services.scheduled_jobs as scheduled_jobs_service
from app.core.repositories.scheduled_ai_jobs import ScheduledAiJobReadRepository
from app.core.security import hash_password
from app.core.users import MemoryUserRepository
from app.main import app
from app.services.dynamic_parameters import dynamic_time_parameters
from app.services.scheduled_job_audit import scheduled_job_run_audit_payload
from app.services.scheduled_job_execution_engine import ScheduledJobExecutionEngine
from app.services.scheduled_job_native_scan import (
    native_code_scan_repository_ids,
    queued_native_scan_result_summary,
)
from app.services.scheduled_job_refs import scheduled_job_multi_ids
from app.services.scheduled_job_run_projection import public_scheduled_job_run_projection

client = TestClient(app)
ADMIN_SERVICE_USER = {"id": "user_admin", "permissions": ["system.admin"], "roles": ["admin"]}


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_product(headers: dict[str, str]) -> dict:
    return client.post(
        "/api/products",
        json={"code": "scheduled-ai-product", "name": "定时 AI 产品"},
        headers=headers,
    ).json()["data"]


def create_model_gateway(headers: dict[str, str]) -> dict:
    return client.post(
        "/api/system/model-gateway-configs",
        json={
            "name": "定时任务模型",
            "provider": "openai_compatible",
            "base_url": "https://llm.test/v1",
            "api_key": "sk-test",
            "default_chat_model": "test-chat-model",
            "status": "active",
            "is_default": True,
        },
        headers=headers,
    ).json()["data"]


def create_feedback(headers: dict[str, str], product_id: str) -> dict:
    return client.post(
        "/api/insights/user-feedback",
        json={
            "content": "结算链路最近反馈较多，希望优先优化。",
            "feedback_type": "improvement",
            "product_id": product_id,
            "source_channel": "in_app",
            "tags": ["checkout"],
        },
        headers=headers,
    ).json()["data"]


def test_scheduled_job_ai_messages_compacts_large_connection_rows_for_model_input():
    app.state.store.reset()
    rows = [
        {
            "app_version": "3.4.0",
            "channel": "ios",
            "content": f"第 {index} 条客服反馈：蓝牙连接不上，希望优化排障指引。" * 3,
            "external_user_id": f"external-user-{index}",
            "open_kf_id": f"open-kf-{index}",
            "pt": "20260709",
            "role_type": 0,
            "send_time": "2026-07-09 10:00:00",
            "user_id": f"user-{index}",
        }
        for index in range(1000)
    ]

    messages = scheduled_job_ai_processing_service.scheduled_job_ai_messages(
        app.state.store,
        job={
            "id": "scheduled_job_large_feedback",
            "job_type": "user_feedback_insight_extract",
            "product_id": "product_feedback",
            "skill_ids": [],
            "source_system": "aliyun-maxcompute",
            "timezone": "Asia/Shanghai",
        },
        output_mapping={},
        source_response_json={
            "data": {
                "pageNum": 1,
                "pageSize": 1000,
                "rows": rows,
                "totalNum": 12709,
            },
            "errCode": 0,
            "errMsg": "success",
        },
        source_row_count=len(rows),
    )

    user_payload = json.loads(messages[1]["content"])
    compacted_rows = user_payload["data_connection_response"]["payload"]["data"]["rows"]
    assert user_payload["data_connection_response_compaction"]["compacted"] is True
    assert compacted_rows["_ai_brain_compacted_list"] is True
    assert compacted_rows["sample_count"] == 80
    assert compacted_rows["total_count"] == 1000
    assert compacted_rows["sample_rows"][0]["_row_index"] == 0
    assert compacted_rows["sample_rows"][-1]["_row_index"] == 999
    assert "external-user-999" not in messages[1]["content"]
    assert "open-kf-999" not in messages[1]["content"]
    assert len(messages[1]["content"]) < 60000


def test_scheduled_job_ai_messages_preserves_small_nested_connection_payloads():
    app.state.store.reset()

    messages = scheduled_job_ai_processing_service.scheduled_job_ai_messages(
        app.state.store,
        job={
            "id": "scheduled_job_small_payload",
            "job_type": "generic_ai_analysis",
            "product_id": "product_feedback",
            "skill_ids": [],
            "source_system": "internal",
            "timezone": "Asia/Shanghai",
        },
        output_mapping={},
        source_response_json={
            "rows": [
                {
                    "content": "需要保留嵌套字段",
                    "metadata": {"labels": ["客服", "蓝牙"], "severity": "medium"},
                },
            ],
        },
        source_row_count=1,
    )

    user_payload = json.loads(messages[1]["content"])
    assert "data_connection_response_compaction" not in user_payload
    assert user_payload["data_connection_response"]["rows"][0]["metadata"] == {
        "labels": ["客服", "蓝牙"],
        "severity": "medium",
    }


def test_user_feedback_source_row_count_falls_back_to_response_rows():
    assert (
        scheduled_job_user_feedback_service.source_row_count_from_response_summary(
            {
                "json": {
                    "data": {
                        "rows": [{"content": "连接失败"}, {"content": "充电异常"}],
                        "totalNum": 120,
                    },
                },
            },
        )
        == 2
    )


def test_scheduled_job_run_projection_adds_trace_graph_and_source_summary():
    source_run = {
        "error_code": None,
        "finished_at": "2026-06-29T01:00:00+00:00",
        "id": "scheduled_job_run_source",
        "records_imported": 3,
        "started_at": "2026-06-29T00:59:00+00:00",
        "status": "succeeded",
        "trigger_type": "manual",
    }
    projected = public_scheduled_job_run_projection(
        {
            "config_snapshot": {"max_retry_count": 2},
            "id": "scheduled_job_run_rerun",
            "result_summary": {
                "execution_nodes": {
                    "data_connection": {
                        "input_mapping": {"week_start": "2026-06-22"},
                        "label": "数据连接获取内容",
                        "records_imported": 3,
                        "status": "succeeded",
                    },
                    "result_action": {
                        "label": "结果动作反馈内容",
                        "records_imported": 3,
                        "status": "succeeded",
                        "write_target": "scheduled_job_result",
                    },
                },
            },
            "source_run_id": source_run["id"],
        },
        source_run=source_run,
    )

    assert projected["source_run_summary"] == {
        "error_code": None,
        "finished_at": "2026-06-29T01:00:00+00:00",
        "id": "scheduled_job_run_source",
        "latency_ms": None,
        "records_imported": 3,
        "started_at": "2026-06-29T00:59:00+00:00",
        "status": "succeeded",
        "trigger_type": "manual",
    }
    trace_graph = projected["result_summary"]["trace_graph"]
    assert trace_graph["edges"] == [{"from": "data_connection", "to": "result_action"}]
    assert [node["id"] for node in trace_graph["nodes"]] == [
        "data_connection",
        "result_action",
    ]
    assert {node["retry_count"] for node in trace_graph["nodes"]} == {2}
    by_node = {node["id"]: node for node in trace_graph["nodes"]}
    assert by_node["data_connection"]["stage"] == "data_connection"
    assert by_node["data_connection"]["stage_label"] == "数据连接"
    assert {"enabled": True, "label": "复制输入", "type": "copy_input"} in by_node[
        "data_connection"
    ]["debug_actions"]
    assert {"enabled": True, "label": "复制输出", "type": "copy_output"} in by_node[
        "data_connection"
    ]["debug_actions"]
    assert {"enabled": True, "label": "复制复跑计划", "type": "copy_rerun_plan"} in by_node[
        "data_connection"
    ]["debug_actions"]
    assert by_node["data_connection"]["snapshot_status"] == {
        "error": False,
        "input": True,
        "output": True,
    }
    assert by_node["data_connection"]["rerun_plan"]["control_summary"] == {
        "blocked_count": 2,
        "missing_count": 0,
        "needs_review_count": 0,
        "satisfied_count": 1,
        "status_counts": {"blocked": 2, "satisfied": 1},
        "total": 3,
    }
    assert by_node["data_connection"]["rerun_plan"]["rerun_controls"] == [
        {
            "key": "request_snapshot",
            "label": "请求快照",
            "reason": "已有可用于预检的节点快照",
            "required": True,
            "satisfied": True,
            "status": "satisfied",
        },
        {
            "key": "connection_read_idempotency",
            "label": "连接读取幂等",
            "reason": "缺少原插件调用日志，无法建立连接读取幂等键",
            "required": True,
            "satisfied": False,
            "status": "blocked",
        },
        {
            "key": "downstream_ai_and_action_invalidation",
            "label": "下游 AI/动作失效策略",
            "reason": "缺少下游 AI/动作隔离策略",
            "required": True,
            "satisfied": False,
            "status": "blocked",
        },
    ]
    assert by_node["data_connection"]["rerun_plan"]["single_node_supported"] is False
    assert (
        by_node["data_connection"]["rerun_plan"]["side_effect_policy"] == "external_read_or_fetch"
    )
    assert (
        by_node["data_connection"]["rerun_plan"]["safe_next_action"] == "rerun_full_scheduled_job"
    )
    assert by_node["result_action"]["rerun_supported"] is False
    assert by_node["result_action"]["rerun_plan"]["status"] == "blocked_by_side_effect_guard"
    assert "复跑整条作业" in by_node["result_action"]["rerun_hint"]


def test_scheduled_job_run_projection_refreshes_legacy_trace_graph_debug_fields():
    projected = public_scheduled_job_run_projection(
        {
            "config_snapshot": {"max_retry_count": 0},
            "id": "scheduled_job_run_legacy_trace",
            "result_summary": {
                "execution_nodes": {
                    "data_connection": {
                        "input_mapping": {"week_start": "2026-06-22"},
                        "label": "数据连接获取内容",
                        "records_imported": 3,
                        "status": "succeeded",
                    },
                    "skill_processing": {
                        "input": {"source_row_count": 3},
                        "label": "Skill 处理后内容",
                        "output": {"candidate_count": 1},
                        "status": "succeeded",
                    },
                },
                "trace_graph": {
                    "edges": [{"from": "data_connection", "to": "skill_processing"}],
                    "nodes": [
                        {
                            "id": "data_connection",
                            "input": {"week_start": "2026-06-22"},
                            "label": "数据连接获取内容",
                            "output": {"records_imported": 3},
                            "status": "succeeded",
                        },
                    ],
                },
            },
        },
    )

    trace_graph = projected["result_summary"]["trace_graph"]
    by_node = {node["id"]: node for node in trace_graph["nodes"]}
    assert by_node["data_connection"]["stage_label"] == "数据连接"
    assert by_node["data_connection"]["debug_actions"]
    assert by_node["data_connection"]["rerun_plan"]["blocked_by"] == [
        "connection_read_idempotency_missing",
    ]
    assert "复跑整条作业" in by_node["skill_processing"]["rerun_hint"]


def test_scheduled_job_run_projection_expands_multi_connection_and_action_trace_nodes():
    projected = public_scheduled_job_run_projection(
        {
            "config_snapshot": {"max_retry_count": 1},
            "id": "scheduled_job_run_multi_trace",
            "result_summary": {
                "execution_nodes": {
                    "data_connection": {
                        "items": [
                            {
                                "connection_id": "plugin_connection_a",
                                "input_mapping": {"week_start": "2026-06-22"},
                                "latency_ms": 120,
                                "records_imported": 2,
                                "response_status_code": 200,
                                "status": "succeeded",
                            },
                            {
                                "connection_id": "plugin_connection_b",
                                "input_mapping": {"week_start": "2026-06-22"},
                                "latency_ms": 180,
                                "records_imported": 3,
                                "response_status_code": 200,
                                "status": "succeeded",
                            },
                        ],
                        "label": "数据连接获取内容",
                        "status": "succeeded",
                    },
                    "result_action": {
                        "label": "结果动作反馈内容",
                        "records_imported": 5,
                        "status": "succeeded",
                        "write_target": "scheduled_job_result",
                    },
                    "result_actions": [
                        {
                            "action_id": "plugin_action_write_insight",
                            "feedback": {"created_ids": ["feedback_001"]},
                            "records_imported": 1,
                            "status": "succeeded",
                            "write_target": "user_feedback_insights",
                        },
                        {
                            "action_id": "plugin_action_archive",
                            "feedback": {"stored_in_run_result": True},
                            "records_imported": 0,
                            "status": "succeeded",
                            "write_target": "scheduled_job_result",
                        },
                    ],
                    "skill_processing": {
                        "input": {"source_row_count": 5},
                        "label": "Skill 处理后内容",
                        "output": {"candidate_count": 1},
                        "status": "succeeded",
                    },
                },
            },
        },
    )

    trace_graph = projected["result_summary"]["trace_graph"]
    assert [node["id"] for node in trace_graph["nodes"]] == [
        "data_connection_1",
        "data_connection_2",
        "skill_processing",
        "result_action_1",
        "result_action_2",
    ]
    assert trace_graph["edges"] == [
        {"from": "data_connection_1", "to": "skill_processing"},
        {"from": "data_connection_2", "to": "skill_processing"},
        {"from": "skill_processing", "to": "result_action_1"},
        {"from": "skill_processing", "to": "result_action_2"},
    ]
    first_connection = trace_graph["nodes"][0]
    assert first_connection["duration_ms"] == 120
    assert first_connection["input"]["connection_id"] == "plugin_connection_a"
    assert first_connection["input"]["connection_index"] == 1
    assert first_connection["output"]["records_imported"] == 2
    assert first_connection["stage_label"] == "数据连接"
    second_action = trace_graph["nodes"][-1]
    assert second_action["input"]["action_id"] == "plugin_action_archive"
    assert second_action["input"]["action_index"] == 2
    assert second_action["output"] == {"stored_in_run_result": True}
    assert second_action["stage"] == "result_action"
    assert second_action["rerun_plan"]["side_effect_policy"] == "external_or_business_write"
    assert {node["retry_count"] for node in trace_graph["nodes"]} == {1}


def test_scheduled_job_refs_merge_legacy_and_orchestration_ids():
    assert scheduled_job_multi_ids(
        {
            "config_json": {
                "orchestration": {
                    "plugin_action_ids": ["action_config", "action_legacy", ""],
                },
            },
            "plugin_action_id": "action_legacy",
            "plugin_action_ids": ["action_table", "action_config"],
        },
        "plugin_action_ids",
        "plugin_action_id",
    ) == ["action_table", "action_config", "action_legacy"]


def test_skill_output_schema_contract_supports_extended_jsonpath():
    schema = {
        "properties": {
            "payload": {
                "properties": {
                    "data.rows": {
                        "items": {
                            "properties": {
                                "items": {
                                    "items": {
                                        "properties": {
                                            "insights": {
                                                "items": {
                                                    "properties": {
                                                        "content": {"type": "string"},
                                                    },
                                                    "type": "object",
                                                },
                                                "type": "array",
                                            },
                                        },
                                        "type": "object",
                                    },
                                    "type": "array",
                                },
                            },
                            "type": "object",
                        },
                        "type": "array",
                    },
                },
                "type": "object",
            },
        },
        "type": "object",
    }

    assert scheduled_job_ai_processing_service.schema_supports_json_path(
        schema,
        "$['payload']['data.rows'][0].items[*].insights[0].content",
    )
    assert not scheduled_job_ai_processing_service.schema_supports_json_path(
        schema,
        "$['payload']['missing.rows'][0].items[*].insights",
    )
    assert scheduled_job_ai_processing_service.skill_output_mapping_contract(
        app.state.store,
        job={"skill_ids": []},
        output_mapping={"insights_path": "$.insights"},
    ) == {
        "checked_paths": [],
        "invalid_fields": [],
        "output_schema": {},
        "status": "not_required",
    }


def test_skill_output_json_contract_rejects_nested_array_item_type_mismatch():
    schema = {
        "properties": {
            "insights": {
                "items": {
                    "properties": {
                        "content": {"type": "string"},
                        "score": {"type": ["number", "null"]},
                    },
                    "required": ["content", "score"],
                    "type": "object",
                },
                "type": ["null", "array"],
            },
        },
        "required": ["insights"],
        "type": "object",
    }

    with pytest.raises(HTTPException) as exc_info:
        scheduled_job_ai_processing_service.validate_skill_output_json_contract(
            {"insights": [{"content": "响应慢", "score": "high"}]},
            schema,
        )

    assert exc_info.value.detail["code"] == "SKILL_OUTPUT_SCHEMA_INVALID"
    assert "$.insights[0].score expected number, got string" in exc_info.value.detail["message"]


def test_code_inspection_ai_processing_has_default_output_schema_without_skill_schema():
    current_store = SimpleNamespace(
        ai_skills={
            "skill_code_inspection": {
                "code": "code_inspection_analysis",
                "id": "skill_code_inspection",
                "name": "代码巡检分析",
                "status": "active",
            },
        },
        repository=None,
    )

    schema = scheduled_job_ai_processing_service.merged_skill_output_schema(
        current_store,
        {
            "job_type": "code_repository_inspection",
            "skill_ids": ["skill_code_inspection"],
        },
    )

    assert schema["type"] == "object"
    assert schema["required"] == ["findings", "risk_level", "summary"]
    assert schema["properties"]["findings"]["type"] == "array"
    finding_schema = schema["properties"]["findings"]["items"]
    assert finding_schema["properties"]["rule_id"]["type"] == "string"
    assert finding_schema["properties"]["severity"]["type"] == "string"
    assert finding_schema["properties"]["recommendation"]["type"] == "string"


def test_native_code_scan_repository_ids_merge_multi_and_single_refs():
    assert native_code_scan_repository_ids(
        {
            "config_json": {
                "repository_id": "repo_c",
                "repository_ids": ["repo_a", "repo_b", "repo_a", "", None],
            },
        },
    ) == ["repo_a", "repo_b", "repo_c"]


def test_native_code_scan_repository_ids_expand_product_active_repositories():
    current_store = SimpleNamespace(
        product_git_repositories={
            "repo_web": {
                "id": "repo_web",
                "name": "Web",
                "product_id": "product_code_scan",
                "repo_type": "code",
                "status": "active",
            },
            "repo_backend": {
                "id": "repo_backend",
                "name": "Backend",
                "product_id": "product_code_scan",
                "repo_type": "code",
                "status": "active",
            },
            "repo_inactive": {
                "id": "repo_inactive",
                "name": "Inactive",
                "product_id": "product_code_scan",
                "repo_type": "code",
                "status": "inactive",
            },
            "repo_docs": {
                "id": "repo_docs",
                "name": "Docs",
                "product_id": "product_code_scan",
                "repo_type": "document",
                "status": "active",
            },
            "repo_other_product": {
                "id": "repo_other_product",
                "name": "Other",
                "product_id": "product_other",
                "repo_type": "code",
                "status": "active",
            },
        },
        repository=None,
    )

    assert native_code_scan_repository_ids(
        {
            "config_json": {"scan_mode": "native_full_scan"},
            "product_id": "product_code_scan",
        },
        current_store=current_store,
    ) == ["repo_backend", "repo_web"]


def test_queued_native_scan_result_summary_uses_repository_default_branch():
    summary = queued_native_scan_result_summary(
        job={
            "config_json": {
                "repository_id": "repo_001",
                "scan_mode": "native_full_scan",
            },
            "skill_ids": ["skill_001"],
        },
        repository={"default_branch": "develop"},
        skill_codes=["code_scan"],
    )

    assert summary["execution_nodes"]["native_scan"]["branch"] == "develop"
    assert summary["execution_nodes"]["native_scan"]["repository_id"] == "repo_001"
    assert summary["processing"]["skill_codes"] == ["code_scan"]
    assert summary["processing"]["skill_ids"] == ["skill_001"]


def test_native_code_scan_job_preserves_github_connection_without_plugin_action():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugins = client.get("/api/system/plugins", headers=admin_headers).json()["data"]["items"]
    github_plugin = next((plugin for plugin in plugins if plugin["code"] == "github"), None)
    if github_plugin is None:
        github_plugin = client.post(
            "/api/system/plugins",
            json={
                "category": "devops",
                "code": "github",
                "name": "GitHub",
                "protocol": "http",
                "status": "active",
            },
            headers=admin_headers,
        ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {"token_ref": "env:GITHUB_READONLY_TOKEN"},
            "auth_type": "bearer",
            "endpoint_url": "https://api.github.com",
            "environment": "prod",
            "name": "GitHub 只读 Token",
            "plugin_id": github_plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {"scan_mode": "native_full_scan"},
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "本地完整代码巡检",
            "plugin_connection_id": connection["id"],
            "plugin_connection_ids": [connection["id"]],
            "schedule_type": "manual",
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    job = response.json()["data"]
    assert job["plugin_action_id"] is None
    assert job["plugin_action_ids"] == []
    assert job["plugin_connection_id"] == connection["id"]
    assert job["plugin_connection_ids"] == [connection["id"]]
    assert job["config_json"]["orchestration"]["plugin_action_ids"] == []
    assert job["config_json"]["orchestration"]["plugin_connection_ids"] == [connection["id"]]


def test_scheduled_job_run_audit_payload_preserves_execution_context():
    payload = scheduled_job_run_audit_payload(
        job={
            "agent_id": "agent_001",
            "config_json": {
                "orchestration": {
                    "plugin_action_ids": ["plugin_action_extra"],
                    "plugin_connection_ids": ["plugin_connection_extra"],
                },
            },
            "execution_mode": "ai_generated",
            "job_type": "code_repository_inspection",
            "knowledge_document_ids": ["knowledge_001"],
            "model_gateway_config_id": "model_gateway_config_001",
            "plugin_action_id": "plugin_action_001",
            "plugin_connection_id": "plugin_connection_001",
            "product_id": "product_001",
            "result_actions": [
                {"type": "write_code_inspection_report"},
                {"type": "create_bug_for_severe_findings"},
                {"severity_threshold": "low"},
            ],
            "skill_ids": ["skill_001"],
        },
        run={
            "collector_run_id": "collector_run_001",
            "error_code": "QUALITY_GATE_FAILED",
            "plugin_invocation_log_id": "plugin_invocation_log_001",
            "records_imported": 7,
            "resolved_plugin_snapshot": {
                "action": {"code": "scan_repository"},
                "connection": {"environment": "prod"},
                "plugin": {"code": "gitlab"},
            },
            "result_summary": {
                "execution_nodes": {
                    "result_action": {"write_target": "code_inspection_reports"},
                    "skill_processing": {"model_gateway_called": True},
                },
            },
            "scheduled_job_id": "scheduled_job_001",
            "source_run_id": "scheduled_job_run_previous",
            "status": "failed",
            "trigger_type": "manual_rerun",
        },
    )

    assert payload == {
        "agent_id": "agent_001",
        "collector_run_id": "collector_run_001",
        "error_code": "QUALITY_GATE_FAILED",
        "execution_mode": "ai_generated",
        "job_type": "code_repository_inspection",
        "knowledge_document_ids": ["knowledge_001"],
        "model_gateway_called": True,
        "model_gateway_config_id": "model_gateway_config_001",
        "plugin_action_code": "scan_repository",
        "plugin_action_id": "plugin_action_001",
        "plugin_action_ids": ["plugin_action_extra", "plugin_action_001"],
        "plugin_code": "gitlab",
        "plugin_connection_environment": "prod",
        "plugin_connection_id": "plugin_connection_001",
        "plugin_connection_ids": ["plugin_connection_extra", "plugin_connection_001"],
        "plugin_invocation_log_id": "plugin_invocation_log_001",
        "product_id": "product_001",
        "records_imported": 7,
        "result_action_types": [
            "write_code_inspection_report",
            "create_bug_for_severe_findings",
        ],
        "result_write_target": "code_inspection_reports",
        "scheduled_job_id": "scheduled_job_001",
        "skill_ids": ["skill_001"],
        "source_run_id": "scheduled_job_run_previous",
        "status": "failed",
        "trigger_type": "manual_rerun",
    }


def test_scheduled_job_repository_supports_paged_filtered_queries():
    class CapturingCursor:
        def __init__(self) -> None:
            self.calls: list[tuple[str, tuple | None]] = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def execute(self, query: str, params: tuple | None = None) -> None:
            self.calls.append((query, params))

        def fetchone(self):
            return (4,)

        def fetchall(self):
            return []

    class CapturingConnection:
        def __init__(self, cursor: CapturingCursor) -> None:
            self._cursor = cursor

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def cursor(self):
            return self._cursor

    cursor = CapturingCursor()
    repository = ScheduledAiJobReadRepository(lambda: CapturingConnection(cursor))

    total = repository.count_scheduled_jobs(
        enabled=True,
        job_type="code_repository_inspection",
        keyword="quality",
        name="巡检",
        product_id="product_ai_brain",
        source_system="ai-brain",
        status="active",
    )
    page_items = repository.list_scheduled_jobs_page(
        enabled=True,
        job_type="code_repository_inspection",
        keyword="quality",
        limit=10,
        name="巡检",
        offset=20,
        product_id="product_ai_brain",
        sort_by="created_at",
        sort_order="asc",
        source_system="ai-brain",
        status="active",
    )

    assert total == 4
    assert page_items == []
    count_query, count_params = cursor.calls[0]
    page_query, page_params = cursor.calls[1]
    assert "SELECT count(*) FROM scheduled_jobs" in count_query
    assert "enabled = %s" in count_query
    assert "job_type = %s" in count_query
    assert "product_id = %s" in count_query
    assert "source_system = %s" in count_query
    assert "status = %s" in count_query
    assert "lower(name) LIKE %s" in count_query
    assert "lower(id) LIKE %s" in count_query
    assert count_params == (
        True,
        "code_repository_inspection",
        "product_ai_brain",
        "ai-brain",
        "active",
        "%巡检%",
        "%quality%",
        "%quality%",
        "%quality%",
        "%quality%",
        "%quality%",
    )
    assert "ORDER BY created_at ASC NULLS FIRST, id ASC" in page_query
    assert "LIMIT %s OFFSET %s" in page_query
    assert page_params[-2:] == (10, 20)

    run_total = repository.count_scheduled_job_runs(
        product_scope_ids=["product_ai_brain"],
        run_ids=["scheduled_job_run_001", "scheduled_job_run_002"],
        scheduled_job_id="scheduled_job_001",
        status="failed",
    )
    run_page_items = repository.list_scheduled_job_runs_page(
        limit=20,
        offset=40,
        product_scope_ids=["product_ai_brain"],
        run_ids=["scheduled_job_run_001", "scheduled_job_run_002"],
        scheduled_job_id="scheduled_job_001",
        sort_by="finished_at",
        sort_order="asc",
        status="failed",
    )

    assert run_total == 4
    assert run_page_items == []
    run_count_query, run_count_params = cursor.calls[2]
    run_page_query, run_page_params = cursor.calls[3]
    assert "SELECT count(*) FROM scheduled_job_runs run" in run_count_query
    assert "JOIN scheduled_jobs job ON job.id = run.scheduled_job_id" in run_count_query
    assert "job.name AS scheduled_job_name" in run_page_query
    assert "run.scheduled_job_id = %s" in run_count_query
    assert "run.status = %s" in run_count_query
    assert "run.id = ANY(%s)" in run_count_query
    assert "job.product_id = ANY(%s)" in run_count_query
    assert run_count_params == (
        "scheduled_job_001",
        "failed",
        ["scheduled_job_run_001", "scheduled_job_run_002"],
        ["product_ai_brain"],
    )
    assert "ORDER BY run.finished_at ASC NULLS FIRST, run.id ASC" in run_page_query
    assert "LIMIT %s OFFSET %s" in run_page_query
    assert run_page_params[-2:] == (20, 40)


def test_ai_capability_repository_supports_paged_filtered_queries():
    class CapturingCursor:
        def __init__(self) -> None:
            self.calls: list[tuple[str, tuple | None]] = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def execute(self, query: str, params: tuple | None = None) -> None:
            self.calls.append((query, params))

        def fetchone(self):
            return (7,)

        def fetchall(self):
            return []

    class CapturingConnection:
        def __init__(self, cursor: CapturingCursor) -> None:
            self._cursor = cursor

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def cursor(self):
            return self._cursor

    cursor = CapturingCursor()
    repository = ScheduledAiJobReadRepository(lambda: CapturingConnection(cursor))

    skill_total = repository.count_ai_skills(
        code="code_review",
        keyword="review",
        requires_human_review=True,
        risk_level="high",
        source_type="package",
        status="active",
    )
    skill_items = repository.list_ai_skills_page(
        code="code_review",
        keyword="review",
        limit=10,
        offset=20,
        requires_human_review=True,
        risk_level="high",
        sort_by="updated_at",
        sort_order="desc",
        source_type="package",
        status="active",
    )

    assert skill_total == 7
    assert skill_items == []
    skill_count_query, skill_count_params = cursor.calls[0]
    skill_page_query, skill_page_params = cursor.calls[1]
    assert "SELECT count(*) FROM ai_skills" in skill_count_query
    assert "code = %s" in skill_count_query
    assert "requires_human_review = %s" in skill_count_query
    assert "risk_level = %s" in skill_count_query
    assert "source_type = %s" in skill_count_query
    assert "status = %s" in skill_count_query
    assert "lower(version) LIKE %s" in skill_count_query
    assert "lower(description) LIKE %s" in skill_count_query
    assert "lower(name) LIKE %s" in skill_count_query
    assert "lower(prompt_template) LIKE %s" in skill_count_query
    assert "lower(source_type) LIKE %s" in skill_count_query
    assert "lower(risk_level) LIKE %s" in skill_count_query
    assert skill_count_params == (
        "code_review",
        True,
        "high",
        "package",
        "active",
        "%review%",
        "%review%",
        "%review%",
        "%review%",
        "%review%",
        "%review%",
        "%review%",
        "%review%",
    )
    assert "ORDER BY updated_at DESC NULLS LAST, id DESC" in skill_page_query
    assert "LIMIT %s OFFSET %s" in skill_page_query
    assert skill_page_params[-2:] == (10, 20)

    agent_total = repository.count_ai_agents(
        brain_app_id="rd_brain",
        keyword="insight",
        model_gateway_config_id="model_gateway_config_001",
        status="active",
    )
    agent_items = repository.list_ai_agents_page(
        brain_app_id="rd_brain",
        keyword="insight",
        limit=5,
        model_gateway_config_id="model_gateway_config_001",
        offset=10,
        sort_by="name",
        sort_order="asc",
        status="active",
    )

    assert agent_total == 7
    assert agent_items == []
    agent_count_query, agent_count_params = cursor.calls[2]
    agent_page_query, agent_page_params = cursor.calls[3]
    assert "SELECT count(*) FROM ai_agents" in agent_count_query
    assert "brain_app_id = %s" in agent_count_query
    assert "model_gateway_config_id = %s" in agent_count_query
    assert "status = %s" in agent_count_query
    assert "lower(description) LIKE %s" in agent_count_query
    assert "lower(model_gateway_config_id) LIKE %s" in agent_count_query
    assert "lower(system_prompt) LIKE %s" in agent_count_query
    assert agent_count_params == (
        "rd_brain",
        "model_gateway_config_001",
        "active",
        "%insight%",
        "%insight%",
        "%insight%",
        "%insight%",
        "%insight%",
        "%insight%",
        "%insight%",
    )
    assert "ORDER BY lower(name) ASC NULLS FIRST, id ASC" in agent_page_query
    assert "LIMIT %s OFFSET %s" in agent_page_query
    assert agent_page_params[-2:] == (5, 10)


def test_ai_capability_lists_use_repository_pagination_when_requested():
    class PagedRepository:
        def __init__(self) -> None:
            self.skill_count_filters: dict | None = None
            self.skill_page_filters: dict | None = None
            self.agent_count_filters: dict | None = None
            self.agent_page_filters: dict | None = None

        def list_ai_agents(self, **_kwargs):
            raise AssertionError("full AI role list fallback should not be used")

        def list_ai_skills(self, **_kwargs):
            raise AssertionError("full AI skill list fallback should not be used")

        def list_scheduled_job_runs(self, **_kwargs):
            return []

        def list_scheduled_jobs(self, **_kwargs):
            return []

        def count_ai_skills(self, **kwargs):
            self.skill_count_filters = kwargs
            return 1

        def list_ai_skills_page(self, **kwargs):
            self.skill_page_filters = kwargs
            return [
                {
                    "code": "code_review",
                    "created_at": "2026-06-27T00:00:00+00:00",
                    "id": "skill_paged",
                    "name": "代码评审 Skill",
                    "prompt_template": "review code",
                    "requires_human_review": True,
                    "risk_level": "high",
                    "source_type": "package",
                    "status": "active",
                    "updated_at": "2026-06-27T01:00:00+00:00",
                    "version": "1.0.0",
                }
            ]

        def count_ai_agents(self, **kwargs):
            self.agent_count_filters = kwargs
            return 1

        def list_ai_agents_page(self, **kwargs):
            self.agent_page_filters = kwargs
            return [
                {
                    "brain_app_id": "rd_brain",
                    "code": "review_agent",
                    "default_skill_ids": ["skill_paged"],
                    "id": "agent_paged",
                    "model_gateway_config_id": "model_gateway_config_001",
                    "name": "代码评审 AI角色",
                    "status": "active",
                    "system_prompt": "review code",
                    "updated_at": "2026-06-27T01:00:00+00:00",
                }
            ]

    repository = PagedRepository()
    current_store = SimpleNamespace(repository=repository, ai_agents={}, ai_skills={})

    skills = scheduled_job_ai_capabilities_service.list_ai_skills_response(
        code="code_review",
        current_store=current_store,
        keyword="review",
        page=2,
        page_size=10,
        requires_human_review=True,
        risk_level="high",
        sort_by="updated_at",
        sort_order="desc",
        source_type="package",
        started_at=None,
        status="active",
    )
    agents = scheduled_job_ai_capabilities_service.list_ai_agents_response(
        brain_app_id="rd_brain",
        current_store=current_store,
        keyword="review",
        model_gateway_config_id="model_gateway_config_001",
        page=3,
        page_size=5,
        sort_by="name",
        sort_order="asc",
        started_at=None,
        status="active",
    )

    assert skills["items"][0]["id"] == "skill_paged"
    assert skills["page"] == 2
    assert skills["page_size"] == 10
    assert skills["query"]["name"] == "ai_skills"
    assert skills["performance"]["p95_target_ms"] == 300
    assert repository.skill_count_filters == {
        "code": "code_review",
        "keyword": "review",
        "requires_human_review": True,
        "risk_level": "high",
        "source_type": "package",
        "status": "active",
    }
    assert repository.skill_page_filters == {
        **repository.skill_count_filters,
        "limit": 10,
        "offset": 10,
        "sort_by": "updated_at",
        "sort_order": "desc",
    }
    assert agents["items"][0]["id"] == "agent_paged"
    assert agents["page"] == 3
    assert agents["page_size"] == 5
    assert agents["query"]["name"] == "ai_agents"
    assert agents["performance"]["p95_target_ms"] == 300
    assert repository.agent_count_filters == {
        "brain_app_id": "rd_brain",
        "keyword": "review",
        "model_gateway_config_id": "model_gateway_config_001",
        "status": "active",
    }
    assert repository.agent_page_filters == {
        **repository.agent_count_filters,
        "limit": 5,
        "offset": 10,
        "sort_by": "name",
        "sort_order": "asc",
    }


def test_scheduled_job_list_uses_repository_pagination_when_requested():
    class PagedRepository:
        def __init__(self) -> None:
            self.count_filters: dict | None = None
            self.page_filters: dict | None = None

        def list_ai_agents(self, **_kwargs):
            return []

        def list_ai_skills(self, **_kwargs):
            return []

        def list_scheduled_job_runs(self, **_kwargs):
            return []

        def list_scheduled_jobs(self, **_kwargs):
            raise AssertionError("full scheduled job list fallback should not be used")

        def count_scheduled_jobs(self, **kwargs):
            self.count_filters = kwargs
            return 1

        def list_scheduled_jobs_page(self, **kwargs):
            self.page_filters = kwargs
            return [
                {
                    "config_json": {},
                    "created_at": "2026-06-24T00:00:00+00:00",
                    "enabled": True,
                    "execution_mode": "deterministic",
                    "id": "scheduled_job_paged",
                    "job_type": "code_repository_inspection",
                    "name": "代码质量巡检",
                    "next_run_at": "2026-06-25T02:00:00+00:00",
                    "product_id": "product_ai_brain",
                    "schedule_type": "cron",
                    "source_system": "ai-brain",
                    "status": "active",
                    "updated_at": "2026-06-24T00:00:00+00:00",
                }
            ]

    repository = PagedRepository()
    current_store = SimpleNamespace(repository=repository, scheduled_jobs={})

    payload = scheduled_jobs_service.list_scheduled_jobs_response(
        current_store=current_store,
        enabled=True,
        job_type="code_repository_inspection",
        keyword="quality",
        name="巡检",
        page=3,
        page_size=10,
        product_id="product_ai_brain",
        sort_by="created_at",
        sort_order="asc",
        source_system="ai-brain",
        started_at=None,
        status="active",
        user=ADMIN_SERVICE_USER,
    )

    assert payload["total"] == 1
    assert payload["page"] == 3
    assert payload["page_size"] == 10
    assert payload["items"][0]["id"] == "scheduled_job_paged"
    assert payload["query"]["name"] == "scheduled_jobs"
    assert payload["performance"]["p95_target_ms"] == 400
    assert repository.count_filters == {
        "enabled": True,
        "job_type": "code_repository_inspection",
        "keyword": "quality",
        "name": "巡检",
        "product_id": "product_ai_brain",
        "product_scope_ids": None,
        "source_system": "ai-brain",
        "status": "active",
    }
    assert repository.page_filters == {
        **repository.count_filters,
        "limit": 10,
        "offset": 20,
        "sort_by": "created_at",
        "sort_order": "asc",
    }


def test_cron_scheduled_job_next_run_uses_future_occurrence_in_timezone():
    next_run = scheduled_job_config.next_run_at(
        SimpleNamespace(
            cron_expression="0 9 * * MON",
            interval_seconds=None,
            schedule_type="cron",
            timezone="Asia/Shanghai",
        ),
        now=datetime(2026, 7, 7, 2, 0, tzinfo=UTC),
    )

    assert next_run == "2026-07-13T01:00:00+00:00"


def test_scheduled_job_list_advances_stale_next_run_to_future():
    current_store = SimpleNamespace(
        scheduled_jobs={
            "scheduled_job_stale": {
                "config_json": {},
                "created_at": "2026-06-24T00:00:00+00:00",
                "cron_expression": "0 9 * * MON",
                "enabled": True,
                "execution_mode": "deterministic",
                "id": "scheduled_job_stale",
                "job_type": "code_repository_inspection",
                "name": "过期的代码巡检",
                "next_run_at": "2026-06-24T00:00:00+00:00",
                "product_id": "product_ai_brain",
                "schedule_type": "cron",
                "source_system": "ai-brain",
                "status": "active",
                "timezone": "Asia/Shanghai",
                "updated_at": "2026-06-24T00:00:00+00:00",
            },
        },
    )

    before_list = datetime.now(UTC)
    payload = scheduled_jobs_service.list_scheduled_jobs_response(
        current_store=current_store,
        enabled=True,
        job_type=None,
        page=1,
        page_size=10,
        started_at=None,
        user=ADMIN_SERVICE_USER,
    )

    refreshed_next_run = datetime.fromisoformat(payload["items"][0]["next_run_at"])
    assert refreshed_next_run > before_list
    assert (
        current_store.scheduled_jobs["scheduled_job_stale"]["next_run_at"]
        == payload["items"][0]["next_run_at"]
    )


def test_scheduled_job_runner_execution_node_keeps_system_executor_model_metadata():
    node = ScheduledJobExecutionEngine.runner_execution_node(
        {
            "response_summary": {
                "runner": {
                    "executor_type": "model_gateway",
                    "model_gateway_called": True,
                    "model_gateway_log_id": "model_gateway_log_system_executor",
                    "result_json": {"summary": "系统默认模型完成仓库分析"},
                    "runner_id": "ai_executor_runner_system_default",
                    "status": "succeeded",
                    "workspace_root": "/Users/zeek/source/e-ai-brain",
                },
            },
        },
    )

    assert node is not None
    assert node["executor_type"] == "model_gateway"
    assert node["model_gateway_called"] is True
    assert node["model_gateway_log_id"] == "model_gateway_log_system_executor"
    assert node["runner_id"] == "ai_executor_runner_system_default"
    assert node["result_json"]["summary"] == "系统默认模型完成仓库分析"


def test_scheduled_job_templates_are_admin_managed_and_versioned():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    forbidden = client.get("/api/system/scheduled-job-templates", headers=reviewer_headers)
    assert forbidden.status_code == 403

    response = client.get("/api/system/scheduled-job-templates", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 11
    by_code = {item["code"]: item for item in data["items"]}

    weekly = by_code["weekly_feedback_insight"]
    assert weekly["name"] == "每周用户反馈洞察抽取"
    assert weekly["publisher"] == "AI Brain 官方"
    assert weekly["template_version"] == "v1"
    assert weekly["payload_defaults"]["job_type"] == "user_feedback_insight_extract"
    assert weekly["payload_defaults"]["plugin_input_mapping"] == {
        "week_end": "{{last_full_week.end}}",
        "week_start": "{{last_full_week.start}}",
    }
    assert weekly["resource_selectors"]["plugin_action"]["code_candidates"] == [
        "fetch_weekly_user_feedback",
    ]

    code_inspection = by_code["code_repository_inspection"]
    assert code_inspection["payload_defaults"]["job_type"] == "code_repository_inspection"
    assert code_inspection["payload_defaults"]["execution_mode"] == "ai_assisted"
    assert code_inspection["payload_defaults"]["result_actions"][0] == {
        "type": "write_code_inspection_report",
    }
    assert code_inspection["resource_selectors"]["agent"]["code_candidates"] == [
        "code-reviewer",
    ]
    assert code_inspection["resource_selectors"]["agent"]["fallback_code_candidates"] == [
        "code_reviewer",
        "code_inspection_agent",
    ]
    assert code_inspection["resource_selectors"]["skill"]["code_candidates"] == [
        "code_analysis_skill",
    ]
    assert code_inspection["resource_selectors"]["skill"]["fallback_code_candidates"] == [
        "code_inspection_analysis",
        "code_review",
    ]
    assert code_inspection["resource_selectors"]["skill"]["text_candidates"][0] == "代码分析skill"
    assert code_inspection["resource_selectors"]["plugin_action"]["code_candidates"] == [
        "scan_github_code_inspection",
        "scan_gitlab_code_inspection",
    ]
    assert code_inspection["wizard_steps"][0]["key"] == "data_connection"
    assert code_inspection["wizard_steps"][1]["key"] == "ai_processing"

    email_digest = by_code["email_digest"]
    assert email_digest["payload_defaults"]["job_type"] == "plugin_action_invoke"
    assert email_digest["payload_defaults"]["source_system"] == "email"
    assert email_digest["resource_selectors"]["plugin_action"]["code_candidates"] == [
        "receive_email_messages",
    ]

    online_log = by_code["online_log_anomaly_analysis"]
    assert online_log["payload_defaults"]["job_type"] == "online_log_ai_analysis"
    assert online_log["payload_defaults"]["execution_mode"] == "ai_generated"
    assert online_log["payload_defaults"]["plugin_input_mapping"] == {
        "window_end": "{{now}}",
        "window_start": "{{current_date}}",
    }
    assert online_log["resource_selectors"]["plugin_action"]["code_candidates"] == [
        "query_online_log_metrics",
        "fetch_online_log_metrics",
        "collect_online_log_metrics",
    ]

    mr_review = by_code["gitlab_mr_review"]
    assert mr_review["payload_defaults"]["job_type"] == "code_repository_inspection"
    assert mr_review["payload_defaults"]["execution_mode"] == "ai_assisted"
    assert mr_review["resource_selectors"]["plugin_action"]["code_candidates"] == [
        "scan_gitlab_code_inspection",
    ]

    ai_executor = by_code["ai_executor_repository_task"]
    assert "系统默认 AI 大模型" in ai_executor["description"]
    assert ai_executor["payload_defaults"]["job_type"] == "plugin_action_invoke"
    assert ai_executor["payload_defaults"]["source_system"] == "ai_executor"
    assert ai_executor["payload_defaults"]["config_json"]["ai_executor"] == {
        "executor_type": "model_gateway",
        "runner_id": "ai_executor_runner_system_default",
        "runner_label": "系统默认执行器",
    }
    assert "系统默认执行器" in ai_executor["recommended_scenarios"]
    assert ai_executor["resource_selectors"]["plugin_action"]["code_candidates"] == [
        "run_ai_executor_instruction",
    ]

    internal_weekly = by_code["internal_business_weekly_insight"]
    assert internal_weekly["payload_defaults"]["job_type"] == "plugin_action_invoke"
    assert internal_weekly["payload_defaults"]["source_system"] == "internal_data_source"
    assert internal_weekly["payload_defaults"]["plugin_input_mapping"]["source_types"] == [
        "user_insights",
        "requirements",
        "products",
        "bugs",
    ]
    assert internal_weekly["resource_selectors"]["plugin_action"]["code_candidates"] == [
        "query_internal_business_data",
    ]
    assert by_code["requirement_bug_risk_analysis"]["payload_defaults"]["plugin_input_mapping"][
        "source_types"
    ] == ["requirements", "bugs"]
    assert by_code["user_insight_requirement_mining"]["payload_defaults"]["plugin_input_mapping"][
        "source_types"
    ] == ["user_insights", "requirements"]
    dingtalk_document_sync = by_code["dingtalk_document_sync"]
    assert dingtalk_document_sync["name"] == "同步钉钉文档"
    assert dingtalk_document_sync["payload_defaults"]["job_type"] == "plugin_action_invoke"
    assert dingtalk_document_sync["payload_defaults"]["execution_mode"] == "ai_generated"
    assert dingtalk_document_sync["payload_defaults"]["source_system"] == "internal_data_source"
    assert dingtalk_document_sync["payload_defaults"]["plugin_input_mapping"][
        "source_types"
    ] == ["user_insights", "requirements", "products", "bugs"]
    assert dingtalk_document_sync["payload_defaults"]["plugin_output_mapping"] == {
        "write_target": "dingtalk_document",
    }
    assert [
        item["type"] for item in dingtalk_document_sync["payload_defaults"]["result_actions"]
    ] == ["sync_dingtalk_document"]
    assert dingtalk_document_sync["payload_defaults"]["result_actions"][0][
        "content_template"
    ] == "{{dingtalk_markdown}}"
    assert dingtalk_document_sync["resource_selectors"]["result_plugin_action"][
        "code_candidates"
    ] == ["update_dingtalk_document_content"]
    assert by_code["product_feedback_trend_analysis"]["payload_defaults"]["plugin_input_mapping"][
        "source_types"
    ] == ["products", "user_insights", "bugs"]


def test_scheduled_job_catalog_exposes_server_owned_job_type_rules():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    forbidden = client.get("/api/system/scheduled-job-catalog", headers=reviewer_headers)
    assert forbidden.status_code == 403

    response = client.get("/api/system/scheduled-job-catalog", headers=admin_headers)
    assert response.status_code == 200
    catalog = response.json()["data"]
    by_type = {item["value"]: item for item in catalog["job_types"]}

    assert by_type["code_repository_inspection"]["label"] == "代码仓库巡检（质量 / 安全 / 规范）"
    assert by_type["code_repository_inspection"]["allow_create"] is True
    assert by_type["code_repository_inspection"]["default_execution_mode"] == "ai_assisted"
    assert by_type["code_repository_inspection"]["runnable"] is True
    assert by_type["code_repository_inspection"]["requires_product"] is True
    assert by_type["code_repository_inspection"]["requires_plugin_resource"] is True
    assert by_type["user_feedback_insight_extract"]["requires_ai_assembly"] is True
    assert by_type["online_log_ai_analysis"]["allow_create"] is True
    assert by_type["online_log_ai_analysis"]["runnable"] is True
    assert by_type["online_log_ai_analysis"]["requires_plugin_resource"] is True
    assert catalog["required_job_types"] == {
        "ai_processing": [
            "iteration_plan_suggestion_generate",
            "online_log_ai_analysis",
            "user_feedback_insight_extract",
        ],
        "plugin_resource": [
            "code_repository_inspection",
            "online_log_ai_analysis",
            "plugin_action_invoke",
            "user_feedback_insight_extract",
        ],
        "product": ["code_repository_inspection", "user_feedback_insight_extract"],
    }
    assert catalog["code_inspection"]["native_scan_mode"] == "native_full_scan"
    assert catalog["code_inspection"]["default_scan_mode"] == "sync_existing_alerts"
    assert catalog["code_inspection"]["default_result_actions"][0] == {
        "type": "write_code_inspection_report",
    }
    assert catalog["generic_result_actions"] == [
        {"label": "仅保存运行结果", "value": "save_scheduled_job_result"},
        {"label": "创建需求", "value": "create_requirements"},
        {"label": "同步钉钉文档", "value": "sync_dingtalk_document"},
        {"label": "发送通知记录", "value": "send_notification"},
    ]
    assert {item["value"] for item in catalog["execution_modes"]} == {
        "ai_assisted",
        "ai_generated",
        "deterministic",
    }


def test_generic_result_actions_are_supported_for_plugin_invoke_jobs():
    assert scheduled_job_result_actions_service.validate_scheduled_job_result_actions(
        "plugin_action_invoke",
        [
            {"type": "save_scheduled_job_result"},
            {"requirements_path": "$.requirements", "type": "create_requirements"},
            {
                "document_id": "https://alidocs.dingtalk.com/i/nodes/doc_node_001",
                "plugin_action_id": "plugin_action_dingtalk",
                "type": "sync_dingtalk_document",
            },
        ],
    ) == [
        {"type": "save_scheduled_job_result"},
        {
            "max_items": 20,
            "priority": "P1",
            "requirements_path": "$.requirements",
            "source": "user_feedback",
            "type": "create_requirements",
        },
        {
            "content_template": "{{dingtalk_markdown}}",
            "document_id": "https://alidocs.dingtalk.com/i/nodes/doc_node_001",
            "plugin_action_id": "plugin_action_dingtalk",
            "type": "sync_dingtalk_document",
            "write_mode": "append",
        },
    ]
    with pytest.raises(HTTPException) as exc_info:
        scheduled_job_result_actions_service.validate_scheduled_job_result_actions(
            "online_log_ai_analysis",
            [{"requirements_path": "$.requirements", "type": "create_requirements"}],
        )
    assert exc_info.value.status_code == 400


def test_plugin_invoke_result_actions_create_requirements_and_sync_dingtalk(monkeypatch):
    import app.services.plugins as plugin_services

    app.state.store.reset()
    product = {
        "brain_app_id": "rd_brain",
        "code": "ai-service",
        "created_at": "2026-07-10T00:00:00+00:00",
        "id": "product_ai_service",
        "name": "AI 客服",
        "owner_user_id": "user_admin",
        "status": "active",
        "updated_at": "2026-07-10T00:00:00+00:00",
    }
    app.state.store.products[product["id"]] = product
    calls: list[dict] = []

    def fake_invoke_plugin_action_response(**kwargs):
        calls.append(kwargs)
        return {
            "id": "plugin_invocation_log_dingtalk",
            "response_summary": {
                "json": {
                    "document_id": kwargs["input_payload"]["document_id"],
                    "status": "updated",
                },
            },
            "status": "succeeded",
        }

    monkeypatch.setattr(
        plugin_services,
        "invoke_plugin_action_response",
        fake_invoke_plugin_action_response,
    )

    executed, total_records = scheduled_job_result_actions_service.execute_generic_result_actions(
        current_store=app.state.store,
        job={
            "id": "scheduled_job_requirement_dingtalk",
            "product_id": product["id"],
            "result_action_policy": {"failure_policy": "fail_fast", "mode": "sequential"},
        },
        output_json={
            "dingtalk_markdown": "## 本周高价值用户洞察\n- 支付失败反馈集中。",
            "requirements": [
                {
                    "acceptance_criteria": ["失败时展示可操作错误原因"],
                    "content": (
                        "客服反馈支付失败后用户不知道下一步操作，"
                        "需要优化错误提示和恢复路径。"
                    ),
                    "evidence": ["本周 18 条反馈中有 7 条提到支付失败"],
                    "priority": "P1",
                    "title": "优化支付失败恢复指引",
                },
            ],
            "summary": "发现 1 个高价值需求机会。",
        },
        output_mapping={"requirements_path": "$.requirements", "write_target": "requirements"},
        result_actions=[
            {"requirements_path": "$.requirements", "type": "create_requirements"},
            {
                "content_template": "{{dingtalk_markdown}}\n\n{{requirements_markdown}}",
                "document_id": "https://alidocs.dingtalk.com/i/nodes/doc_node_sync_001",
                "plugin_action_id": "plugin_action_dingtalk_update",
                "type": "sync_dingtalk_document",
            },
        ],
        scheduled_job_run_id="scheduled_job_run_requirement_dingtalk",
        user=ADMIN_SERVICE_USER,
    )

    assert total_records == 2
    assert [item["type"] for item in executed] == ["create_requirements", "sync_dingtalk_document"]
    created_requirement = next(iter(app.state.store.requirements.values()))
    assert created_requirement["product_id"] == product["id"]
    assert created_requirement["source"] == "user_feedback"
    assert created_requirement["status"] == "submitted"
    assert created_requirement["title"] == "优化支付失败恢复指引"
    assert executed[0]["feedback"]["created_requirement_ids"] == [created_requirement["id"]]
    assert calls[0]["action_id"] == "plugin_action_dingtalk_update"
    assert calls[0]["input_payload"]["document_id"] == "doc_node_sync_001"
    assert calls[0]["input_payload"]["mode"] == "append"
    assert created_requirement["id"] in calls[0]["input_payload"]["markdown"]
    assert executed[1]["feedback"]["document_id"] == "doc_node_sync_001"
    assert executed[1]["feedback"]["plugin_invocation_log_id"] == "plugin_invocation_log_dingtalk"


def test_create_requirements_result_action_is_scoped_and_idempotent_per_run():
    app.state.store.reset()
    product = {
        "brain_app_id": "rd_brain",
        "code": "scoped-product",
        "created_at": "2026-07-10T00:00:00+00:00",
        "id": "product_scoped_result_action",
        "name": "作业所属产品",
        "owner_user_id": "user_admin",
        "status": "active",
        "updated_at": "2026-07-10T00:00:00+00:00",
    }
    other_product = {
        **product,
        "code": "other-product",
        "id": "product_other_result_action",
        "name": "其他产品",
    }
    app.state.store.products[product["id"]] = product
    app.state.store.products[other_product["id"]] = other_product
    job = {
        "id": "scheduled_job_scoped_requirements",
        "product_id": product["id"],
        "result_action_policy": {"failure_policy": "fail_fast", "mode": "sequential"},
    }
    output_json = {
        "requirements": [
            {
                "content": "将已确认的高频反馈转化为产品改进需求。",
                "priority": "P1",
                "title": "改进高频反馈场景",
            }
        ]
    }
    action = {"requirements_path": "$.requirements", "type": "create_requirements"}

    first, first_total = scheduled_job_result_actions_service.execute_generic_result_actions(
        current_store=app.state.store,
        job=job,
        output_json=output_json,
        output_mapping={"requirements_path": "$.requirements"},
        result_actions=[action],
        scheduled_job_run_id="scheduled_job_run_scoped_requirements",
        user=ADMIN_SERVICE_USER,
    )
    second, second_total = scheduled_job_result_actions_service.execute_generic_result_actions(
        current_store=app.state.store,
        job=job,
        output_json=output_json,
        output_mapping={"requirements_path": "$.requirements"},
        result_actions=[action],
        scheduled_job_run_id="scheduled_job_run_scoped_requirements",
        user=ADMIN_SERVICE_USER,
    )

    assert first_total == second_total == 1
    assert len(app.state.store.requirements) == 1
    assert first[0]["feedback"]["created_requirement_ids"] == second[0]["feedback"][
        "created_requirement_ids"
    ]
    created_requirement = next(iter(app.state.store.requirements.values()))
    assert created_requirement["product_id"] == product["id"]
    assert created_requirement["raw_payload"]["scheduled_job_run_id"] == (
        "scheduled_job_run_scoped_requirements"
    )

    blocked, blocked_total = scheduled_job_result_actions_service.execute_generic_result_actions(
        current_store=app.state.store,
        job=job,
        output_json={
            "requirements": [
                {
                    "content": "不应允许跨产品写入。",
                    "product_id": other_product["id"],
                    "title": "跨产品需求",
                }
            ]
        },
        output_mapping={"requirements_path": "$.requirements"},
        result_actions=[action],
        scheduled_job_run_id="scheduled_job_run_cross_product",
        user=ADMIN_SERVICE_USER,
    )

    assert blocked_total == 0
    assert blocked[0]["status"] == "failed"
    assert blocked[0]["error_code"] == "RESULT_ACTION_PRODUCT_MISMATCH"
    assert len(app.state.store.requirements) == 1


def test_unavailable_scheduled_job_types_are_not_creatable_or_runnable():
    app.state.store.reset()
    admin_headers = auth_headers()

    create_response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "dashboard_snapshot_refresh",
            "name": "看板快照刷新",
            "schedule_type": "manual",
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    )

    assert create_response.status_code == 400
    assert create_response.json()["detail"]["code"] == "SCHEDULED_JOB_TYPE_UNAVAILABLE"

    now = "2026-07-01T00:00:00+00:00"
    legacy_job_id = app.state.store.new_id("scheduled_job")
    app.state.store.scheduled_jobs[legacy_job_id] = {
        "agent_id": None,
        "config_json": {},
        "created_at": now,
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "id": legacy_job_id,
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_error_message": None,
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 300,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "name": "历史看板快照刷新",
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": now,
    }

    run_response = client.post(
        f"/api/system/scheduled-jobs/{legacy_job_id}/run",
        headers=admin_headers,
    )

    assert run_response.status_code == 400
    assert run_response.json()["detail"]["code"] == "SCHEDULED_JOB_TYPE_NOT_RUNNABLE"
    assert app.state.store.scheduled_job_runs == {}


def test_successful_scheduled_job_run_can_generate_template_and_trace_graph():
    app.state.store.reset()
    admin_headers = auth_headers()

    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "warehouse_reader",
            "name": "数据仓库读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://warehouse.example.com",
            "environment": "prod",
            "name": "生产数据仓库",
            "plugin_id": plugin["id"],
            "request_config": {"query": {"start_pt": "{{current_date-7}}"}},
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_weekly_rows",
            "connection_id": connection["id"],
            "name": "拉取每周数据",
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {"row_count": 2, "rows": [{"id": 1}, {"id": 2}]},
                "path": "/rows",
            },
            "result_mapping": {
                "records_imported_path": "$.row_count",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "cron_expression": "0 9 * * MON",
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "max_retry_count": 2,
            "name": "每周数据同步",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "plugin_input_mapping": {"week_start": "{{last_full_week.start}}"},
            "schedule_type": "cron",
            "source_system": "warehouse",
            "timezone": "Asia/Shanghai",
        },
        headers=admin_headers,
    ).json()["data"]

    run = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    ).json()["data"]
    assert run["status"] == "succeeded"
    assert run["records_imported"] == 2

    trace_graph = run["result_summary"]["trace_graph"]
    assert trace_graph["edges"] == [
        {"from": "data_connection", "to": "skill_processing"},
        {"from": "skill_processing", "to": "result_action"},
    ]
    by_node = {node["id"]: node for node in trace_graph["nodes"]}
    assert by_node["data_connection"]["duration_ms"] >= 0
    expected_week_start = dynamic_time_parameters(timezone=ZoneInfo("Asia/Shanghai"))[
        "last_full_week.start"
    ]
    assert by_node["data_connection"]["input"]["week_start"] == expected_week_start
    assert by_node["data_connection"]["output"]["records_imported"] == 2
    assert by_node["skill_processing"]["retry_count"] == 2
    assert by_node["result_action"]["error"] is None

    generated = client.post(
        f"/api/system/scheduled-job-runs/{run['id']}/template",
        headers=admin_headers,
    )
    assert generated.status_code == 200
    template = generated.json()["data"]
    assert template["code"] == f"generated_from_{run['id']}"
    assert template["source_run_id"] == run["id"]
    assert template["payload_defaults"]["name"] == "每周数据同步 模板"
    assert template["payload_defaults"]["plugin_action_id"] == action["id"]
    assert template["payload_defaults"]["plugin_connection_id"] == connection["id"]
    assert template["payload_defaults"]["cron_expression"] == "0 9 * * MON"
    assert template["payload_defaults"]["config_json"]["template_source"] == {
        "source_id": run["id"],
        "source_type": "scheduled_job_run",
        "title": "每周数据同步",
    }
    assert template["wizard_steps"][0]["key"] == "data_connection"


def test_plugin_action_invoke_ai_generated_runs_skill_before_result_action(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "generic_plugin_summary_skill",
            "input_schema": {"type": "object"},
            "name": "通用插件摘要 Skill",
            "output_schema": {
                "properties": {
                    "insights": {"type": "array"},
                    "summary": {"type": "string"},
                },
                "required": ["summary", "insights"],
                "type": "object",
            },
            "prompt_template": "把连接数据整理成 summary 和 insights。",
            "status": "active",
            "version": "1.0.0",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "generic_plugin_summary_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "通用插件摘要 AI角色",
            "status": "active",
            "system_prompt": "输出结构化摘要。",
        },
        headers=admin_headers,
    ).json()["data"]

    model_gateway_call_count = 0

    class FakeModelResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            content = {
                "insights": [
                    {
                        "content": "内部业务数据存在一条高价值洞察。",
                        "feedback_type": "opportunity",
                        "sentiment": "positive",
                        "source_channel": "internal_data_source",
                        "tags": ["internal"],
                    },
                ],
                "summary": "AI 已完成通用插件数据摘要。",
            }
            return json.dumps(
                {
                    "choices": [
                        {"message": {"content": json.dumps(content, ensure_ascii=False)}},
                    ],
                    "usage": {"completion_tokens": 18, "prompt_tokens": 36, "total_tokens": 54},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(*_args, **_kwargs):
        nonlocal model_gateway_call_count
        model_gateway_call_count += 1
        return FakeModelResponse()

    monkeypatch.setattr(scheduled_job_ai_processing_service, "urlopen", fake_urlopen)

    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "business_system",
            "code": "generic_ai_plugin",
            "name": "通用 AI 插件",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://generic-ai.example.com",
            "environment": "prod",
            "name": "通用 AI 连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_generic_ai_rows",
            "connection_id": connection["id"],
            "name": "读取通用 AI 数据",
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {
                    "row_count": 2,
                    "rows": [{"content": "反馈 A"}, {"content": "反馈 B"}],
                },
                "path": "/rows",
            },
            "result_mapping": {
                "records_imported_path": "$.row_count",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    job_payload = {
        "agent_id": agent["id"],
        "enabled": True,
        "execution_mode": "ai_generated",
        "job_type": "plugin_action_invoke",
        "model_gateway_config_id": model_gateway["id"],
        "name": "通用插件 AI 摘要",
        "plugin_action_id": action["id"],
        "plugin_connection_id": connection["id"],
        "result_actions": [{"type": "save_scheduled_job_result"}],
        "schedule_type": "manual",
        "skill_ids": [skill["id"]],
        "source_system": "generic-plugin",
    }
    dry_run = client.post(
        "/api/system/scheduled-jobs/dry-run",
        json=job_payload,
        headers=admin_headers,
    ).json()["data"]
    assert dry_run["stages"]["ai_processing"]["will_call_model_gateway"] is True
    assert dry_run["stages"]["result_actions"][0]["write_preview_source"] == ("skill_output_schema")

    job = client.post(
        "/api/system/scheduled-jobs",
        json=job_payload,
        headers=admin_headers,
    ).json()["data"]
    run = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    ).json()["data"]

    assert run["status"] == "succeeded"
    assert model_gateway_call_count == 1
    summary = run["result_summary"]
    execution_nodes = summary["execution_nodes"]
    assert execution_nodes["data_connection"]["records_imported"] == 2
    assert execution_nodes["skill_processing"]["model_gateway_called"] is True
    assert execution_nodes["skill_processing"]["processing_mode"] == (
        "model_gateway_json_transform"
    )
    assert execution_nodes["skill_processing"]["output"]["summary"] == (
        "AI 已完成通用插件数据摘要。"
    )
    assert execution_nodes["result_action"]["write_target"] == "scheduled_job_result"
    assert execution_nodes["result_actions"][0]["type"] == "save_scheduled_job_result"
    assert summary["processing"]["model_gateway_called"] is True
    assert summary["trace_graph"]["edges"] == [
        {"from": "data_connection", "to": "runner_execution"},
        {"from": "runner_execution", "to": "skill_processing"},
        {"from": "skill_processing", "to": "result_action_1"},
    ]


def test_scheduled_job_run_permission_can_trigger_without_manage_permission():
    app.state.store.reset()
    admin_headers = auth_headers()
    original_user_repository = app.state.user_repository

    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "runner_permission_warehouse",
            "name": "执行权限测试仓库",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://runner-permission.example.com",
            "environment": "prod",
            "name": "执行权限测试连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_runner_permission_rows",
            "connection_id": connection["id"],
            "name": "拉取执行权限测试数据",
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {"row_count": 1, "rows": [{"id": 1}]},
                "path": "/rows",
            },
            "result_mapping": {
                "records_imported_path": "$.row_count",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "name": "执行权限测试作业",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "schedule_type": "manual",
            "source_system": "warehouse",
        },
        headers=admin_headers,
    ).json()["data"]

    app.state.user_repository = MemoryUserRepository(
        {
            "test-owner@example.com": {
                "display_name": "测试负责人",
                "id": "user_test_owner",
                "password_hash": hash_password("test123"),
                "roles": ["test_owner"],
                "status": "active",
                "username": "test-owner@example.com",
            },
        },
    )

    try:
        runner_headers = auth_headers("test-owner@example.com", "test123")

        forbidden_create = client.post(
            "/api/system/scheduled-jobs",
            json={
                "enabled": True,
                "execution_mode": "deterministic",
                "job_type": "plugin_action_invoke",
                "name": "执行权限不应能创建作业",
                "plugin_action_id": action["id"],
                "plugin_connection_id": connection["id"],
                "schedule_type": "manual",
                "source_system": "warehouse",
            },
            headers=runner_headers,
        )
        assert forbidden_create.status_code == 403

        run_response = client.post(
            f"/api/system/scheduled-jobs/{job['id']}/run",
            headers=runner_headers,
        )
        assert run_response.status_code == 200, run_response.text
        run = run_response.json()["data"]
        assert run["trigger_type"] == "manual"
        assert run["status"] == "succeeded"
        assert run["records_imported"] == 1
    finally:
        app.state.user_repository = original_user_repository


def test_scheduled_job_preserves_multiple_plugin_connections_and_actions():
    app.state.store.reset()
    admin_headers = auth_headers()

    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "multi_warehouse_reader",
            "name": "多数据源读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    primary_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://primary-warehouse.example.com",
            "environment": "prod",
            "name": "主数据仓库",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    backup_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://backup-warehouse.example.com",
            "environment": "prod",
            "name": "备用数据仓库",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    primary_action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_primary_weekly_rows",
            "connection_id": primary_connection["id"],
            "name": "拉取主库周数据",
            "plugin_id": plugin["id"],
            "request_config": {"method": "GET", "path": "/weekly/primary"},
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    backup_action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "write_backup_weekly_rows",
            "connection_id": backup_connection["id"],
            "name": "写入备用周数据",
            "plugin_id": plugin["id"],
            "request_config": {"method": "POST", "path": "/weekly/backup"},
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "name": "多数据源每周同步",
            "plugin_action_ids": [primary_action["id"], backup_action["id"]],
            "plugin_connection_ids": [primary_connection["id"], backup_connection["id"]],
            "schedule_type": "manual",
            "source_system": "warehouse",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    job = response.json()["data"]
    assert job["plugin_action_id"] == primary_action["id"]
    assert job["plugin_action_ids"] == [primary_action["id"], backup_action["id"]]
    assert job["plugin_connection_id"] == primary_connection["id"]
    assert job["plugin_connection_ids"] == [primary_connection["id"], backup_connection["id"]]
    assert job["config_json"]["orchestration"]["plugin_action_ids"] == [
        primary_action["id"],
        backup_action["id"],
    ]
    assert job["config_json"]["orchestration"]["plugin_connection_ids"] == [
        primary_connection["id"],
        backup_connection["id"],
    ]
    assert job["config_json"]["orchestration"]["data_connections"] == {
        "failure_policy": "fail_fast",
        "merge_strategy": "append_json_arrays",
        "mode": "sequential",
    }
    assert job["config_json"]["orchestration"]["result_actions"] == {
        "failure_policy": "continue_on_error",
        "mode": "sequential",
    }

    listed = client.get("/api/system/scheduled-jobs", headers=admin_headers).json()["data"]["items"]
    listed_job = next(item for item in listed if item["id"] == job["id"])
    assert listed_job["plugin_action_ids"] == [primary_action["id"], backup_action["id"]]
    assert listed_job["plugin_connection_ids"] == [
        primary_connection["id"],
        backup_connection["id"],
    ]


def test_scheduled_job_rejects_extra_connection_from_different_plugin():
    app.state.store.reset()
    admin_headers = auth_headers()

    primary_plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "primary_warehouse_reader",
            "name": "主数据源读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    other_plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "other_warehouse_reader",
            "name": "其他数据源读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    primary_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://primary-warehouse.example.com",
            "name": "主数据源连接",
            "plugin_id": primary_plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    other_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://other-warehouse.example.com",
            "name": "其他数据源连接",
            "plugin_id": other_plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_weekly_rows",
            "connection_id": primary_connection["id"],
            "name": "拉取周数据",
            "plugin_id": primary_plugin["id"],
            "request_config": {"method": "GET", "path": "/weekly"},
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "name": "跨插件连接同步",
            "plugin_action_id": action["id"],
            "plugin_connection_id": primary_connection["id"],
            "plugin_connection_ids": [primary_connection["id"], other_connection["id"]],
            "schedule_type": "manual",
            "source_system": "warehouse",
        },
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "PLUGIN_CONNECTION_MISMATCH"


def test_scheduled_job_runs_multiple_data_connections_with_merged_dag_node():
    app.state.store.reset()
    admin_headers = auth_headers()

    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "multi_run_warehouse_reader",
            "name": "多连接运行读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    primary_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://primary-run-warehouse.example.com",
            "environment": "prod",
            "name": "主运行仓库",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    backup_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://backup-run-warehouse.example.com",
            "environment": "prod",
            "name": "备运行仓库",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_multi_connection_rows",
            "connection_id": primary_connection["id"],
            "name": "多连接取数",
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {
                    "row_count": 2,
                    "rows": [{"id": "a"}, {"id": "b"}],
                },
                "path": "/weekly",
            },
            "result_mapping": {
                "records_imported_path": "$.row_count",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "name": "多连接运行作业",
            "plugin_action_id": action["id"],
            "plugin_connection_ids": [primary_connection["id"], backup_connection["id"]],
            "schedule_type": "manual",
            "source_system": "warehouse",
        },
        headers=admin_headers,
    ).json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    assert run["records_imported"] == 4
    data_node = run["result_summary"]["execution_nodes"]["data_connection"]
    assert data_node["connection_count"] == 2
    assert data_node["successful_count"] == 2
    assert data_node["failed_count"] == 0
    assert data_node["merge_strategy"] == "append_json_arrays"
    assert data_node["failure_policy"] == "fail_fast"
    assert [item["connection_id"] for item in data_node["items"]] == [
        primary_connection["id"],
        backup_connection["id"],
    ]
    assert data_node["response_summary"]["json"]["row_count"] == 4
    assert len(data_node["response_summary"]["json"]["rows"]) == 4
    trace_nodes = run["result_summary"]["trace_graph"]["nodes"]
    trace_data_nodes = [
        node for node in trace_nodes if str(node["id"]).startswith("data_connection_")
    ]  # noqa: E501
    assert [node["id"] for node in trace_data_nodes] == ["data_connection_1", "data_connection_2"]
    assert [node["input"]["connection_id"] for node in trace_data_nodes] == [
        primary_connection["id"],
        backup_connection["id"],
    ]
    assert [node["input"]["connection_index"] for node in trace_data_nodes] == [1, 2]
    assert [node["output"]["records_imported"] for node in trace_data_nodes] == [2, 2]


def test_scheduled_job_data_connections_continue_after_failed_connection(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()

    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "multi_continue_reader",
            "name": "多连接继续读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    failed_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://failed-warehouse.example.com",
            "name": "失败仓库",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    healthy_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://healthy-warehouse.example.com",
            "name": "可用仓库",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_continue_connection_rows",
            "connection_id": failed_connection["id"],
            "name": "继续策略取数",
            "plugin_id": plugin["id"],
            "request_config": {"method": "GET", "path": "/weekly"},
            "result_mapping": {
                "records_imported_path": "$.row_count",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    calls: list[str | None] = []

    def fake_invoke_plugin_action_response(
        *,
        action_id,
        connection_id=None,
        current_store,
        **_kwargs,
    ):
        calls.append(connection_id)
        log_id = current_store.new_id("plugin_invocation_log")
        if connection_id == failed_connection["id"]:
            return {
                "action_id": action_id,
                "connection_id": connection_id,
                "error_code": "HTTPError",
                "error_message": "HTTP Error 500: Internal Server Error",
                "id": log_id,
                "latency_ms": 12,
                "request_summary": {
                    "method": "GET",
                    "request_preview": {"method": "GET", "url": "https://failed/weekly"},
                    "url": "https://failed/weekly",
                },
                "response_summary": {"json": {}, "status_code": 500},
                "status": "failed",
            }
        return {
            "action_id": action_id,
            "connection_id": connection_id,
            "error_code": None,
            "error_message": None,
            "id": log_id,
            "latency_ms": 15,
            "request_summary": {
                "method": "GET",
                "request_preview": {"method": "GET", "url": "https://healthy/weekly"},
                "url": "https://healthy/weekly",
            },
            "response_summary": {
                "json": {"row_count": 2, "rows": [{"id": "ok-1"}, {"id": "ok-2"}]},
                "status_code": 200,
            },
            "status": "succeeded",
        }

    monkeypatch.setattr(
        scheduled_job_data_connections_service,
        "invoke_plugin_action_response",
        fake_invoke_plugin_action_response,
    )
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "orchestration": {
                    "data_connections": {
                        "failure_policy": "continue_on_error",
                        "merge_strategy": "append_json_arrays",
                        "mode": "sequential",
                    },
                },
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "name": "多连接失败后继续作业",
            "plugin_action_id": action["id"],
            "plugin_connection_ids": [
                failed_connection["id"],
                healthy_connection["id"],
            ],
            "schedule_type": "manual",
            "source_system": "warehouse",
        },
        headers=admin_headers,
    ).json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert calls == [failed_connection["id"], healthy_connection["id"]]
    assert run["status"] == "succeeded"
    assert run["records_imported"] == 2
    data_node = run["result_summary"]["execution_nodes"]["data_connection"]
    assert data_node["status"] == "partial_failed"
    assert data_node["failure_policy"] == "continue_on_error"
    assert data_node["successful_count"] == 1
    assert data_node["failed_count"] == 1
    assert data_node["response_summary"]["json"]["row_count"] == 2
    assert [item["status"] for item in data_node["items"]] == ["failed", "succeeded"]
    assert data_node["items"][0]["error_code"] == "HTTPError"
    assert data_node["items"][1]["records_imported"] == 2
    trace_nodes = run["result_summary"]["trace_graph"]["nodes"]
    by_id = {node["id"]: node for node in trace_nodes}
    assert by_id["data_connection_1"]["status"] == "failed"
    assert by_id["data_connection_1"]["error"]["code"] == "HTTPError"
    assert by_id["data_connection_2"]["status"] == "succeeded"
    assert by_id["result_action"]["status"] == "partial_failed"


def test_scheduled_job_data_connection_fail_fast_keeps_failure_trace(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()

    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "multi_fail_fast_reader",
            "name": "多连接快速失败读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    failed_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://failed-fast-warehouse.example.com",
            "name": "快速失败仓库",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    skipped_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://skipped-warehouse.example.com",
            "name": "不会调用仓库",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_fail_fast_connection_rows",
            "connection_id": failed_connection["id"],
            "name": "快速失败策略取数",
            "plugin_id": plugin["id"],
            "request_config": {"method": "GET", "path": "/weekly"},
            "result_mapping": {
                "records_imported_path": "$.row_count",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    calls: list[str | None] = []

    def fake_invoke_plugin_action_response(
        *,
        action_id,
        connection_id=None,
        current_store,
        **_kwargs,
    ):
        calls.append(connection_id)
        return {
            "action_id": action_id,
            "connection_id": connection_id,
            "error_code": "HTTPError",
            "error_message": "HTTP Error 502: Bad Gateway",
            "id": current_store.new_id("plugin_invocation_log"),
            "latency_ms": 9,
            "request_summary": {
                "method": "GET",
                "request_preview": {"method": "GET", "url": "https://failed-fast/weekly"},
                "url": "https://failed-fast/weekly",
            },
            "response_summary": {"json": {}, "status_code": 502},
            "status": "failed",
        }

    monkeypatch.setattr(
        scheduled_job_data_connections_service,
        "invoke_plugin_action_response",
        fake_invoke_plugin_action_response,
    )
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "name": "多连接快速失败作业",
            "plugin_action_id": action["id"],
            "plugin_connection_ids": [
                failed_connection["id"],
                skipped_connection["id"],
            ],
            "schedule_type": "manual",
            "source_system": "warehouse",
        },
        headers=admin_headers,
    ).json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert calls == [failed_connection["id"]]
    assert run["status"] == "failed"
    assert run["error_code"] == "HTTPError"
    data_node = run["result_summary"]["execution_nodes"]["data_connection"]
    assert data_node["status"] == "failed"
    assert data_node["error_code"] == "HTTPError"
    assert data_node["response_status_code"] == 502
    result_action = run["result_summary"]["execution_nodes"]["result_action"]
    assert result_action["status"] == "failed"
    trace_nodes = run["result_summary"]["trace_graph"]["nodes"]
    by_id = {node["id"]: node for node in trace_nodes}
    assert by_id["data_connection"]["status"] == "failed"
    assert by_id["data_connection"]["error"]["code"] == "HTTPError"
    assert by_id["result_action"]["status"] == "failed"


def test_user_feedback_data_connection_failure_marks_ai_processing_not_run(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    product = create_product(admin_headers)
    model_gateway = create_model_gateway(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_not_started_skill",
            "input_schema": {"type": "object"},
            "name": "反馈未开始 Skill",
            "output_schema": {
                "properties": {"insights": {"type": "array"}},
                "required": ["insights"],
                "type": "object",
            },
            "prompt_template": "输出 insights 数组。",
            "status": "active",
            "version": "1.0.0",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "feedback_not_started_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈未开始 AI角色",
            "status": "active",
            "system_prompt": "分析反馈。",
        },
        headers=admin_headers,
    ).json()["data"]
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "feedback_data_failure_reader",
            "name": "反馈失败读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://feedback-failed.example.com",
            "name": "反馈失败连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_failed_feedback_for_ai",
            "connection_id": connection["id"],
            "name": "失败反馈取数",
            "plugin_id": plugin["id"],
            "request_config": {"method": "GET", "path": "/feedback"},
            "result_mapping": {
                "insights_path": "$.insights",
                "records_imported_path": "$.row_count",
                "write_target": "user_feedback_insights",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    def fake_invoke_plugin_action_response(
        *,
        action_id,
        connection_id=None,
        current_store,
        **_kwargs,
    ):
        return {
            "action_id": action_id,
            "connection_id": connection_id,
            "error_code": "HTTPError",
            "error_message": "HTTP Error 502: Bad Gateway",
            "id": current_store.new_id("plugin_invocation_log"),
            "latency_ms": 18,
            "request_summary": {
                "method": "GET",
                "request_preview": {"method": "GET", "url": "https://feedback-failed/feedback"},
                "url": "https://feedback-failed/feedback",
            },
            "response_summary": {"json": {}, "status_code": 502},
            "status": "failed",
        }

    model_called = False

    def fail_if_model_called(*_args, **_kwargs):
        nonlocal model_called
        model_called = True
        raise AssertionError("model gateway should not be called when data connection fails")

    monkeypatch.setattr(
        scheduled_job_data_connections_service,
        "invoke_plugin_action_response",
        fake_invoke_plugin_action_response,
    )
    monkeypatch.setattr(scheduled_job_ai_processing_service, "urlopen", fail_if_model_called)

    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "user_feedback_insight_extract",
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈取数失败不调用 AI",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
        },
        headers=admin_headers,
    ).json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    )

    assert run_response.status_code == 200
    assert model_called is False
    run = run_response.json()["data"]
    assert run["status"] == "failed"
    assert run["error_code"] == "HTTPError"
    execution_nodes = run["result_summary"]["execution_nodes"]
    assert execution_nodes["data_connection"]["status"] == "failed"
    assert execution_nodes["skill_processing"]["status"] == "not_run"
    assert execution_nodes["skill_processing"]["model_gateway_called"] is False
    assert execution_nodes["skill_processing"]["processing_mode"] == "not_started"
    assert "数据连接失败" in execution_nodes["skill_processing"]["note"]
    assert execution_nodes["result_action"]["status"] == "not_run"
    assert run["result_summary"]["processing"]["model_gateway_called"] is False


def test_scheduled_job_validates_skill_output_schema_before_ai_processing(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    product = create_product(admin_headers)
    model_gateway = create_model_gateway(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_schema_skill",
            "input_schema": {"type": "object"},
            "name": "反馈 Schema Skill",
            "output_schema": {
                "properties": {"insights": {"type": "array"}},
                "required": ["insights"],
                "type": "object",
            },
            "prompt_template": "把反馈输出为 insights 数组。",
            "status": "active",
            "version": "1.0.0",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "feedback_schema_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈 Schema AI角色",
            "status": "active",
            "system_prompt": "输出结构化反馈洞察。",
        },
        headers=admin_headers,
    ).json()["data"]
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "schema_feedback_reader",
            "name": "Schema 反馈读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://schema-feedback.example.com",
            "environment": "prod",
            "name": "Schema 反馈连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_schema_feedback",
            "connection_id": connection["id"],
            "name": "拉取 Schema 反馈",
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {"row_count": 1, "rows": [{"content": "卡顿"}]},
                "path": "/feedback",
            },
            "result_mapping": {
                "insights_path": "$.missing",
                "records_imported_path": "$.row_count",
                "write_target": "user_feedback_insights",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "user_feedback_insight_extract",
            "model_gateway_config_id": model_gateway["id"],
            "name": "Schema 映射预检作业",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
        },
        headers=admin_headers,
    ).json()["data"]
    model_called = False

    def fail_if_model_called(*_args, **_kwargs):
        nonlocal model_called
        model_called = True
        raise AssertionError("model gateway should not be called when mapping preflight fails")

    monkeypatch.setattr(scheduled_job_ai_processing_service, "urlopen", fail_if_model_called)

    run = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    ).json()["data"]

    assert model_called is False
    assert run["status"] == "failed"
    assert run["error_code"] == "SKILL_OUTPUT_MAPPING_INVALID"
    skill_node = run["result_summary"]["execution_nodes"]["skill_processing"]
    assert skill_node["status"] == "failed"
    assert "insights_path" in skill_node["error_message"]


def test_scheduled_job_rejects_model_output_type_mismatch_before_result_actions(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    product = create_product(admin_headers)
    model_gateway = create_model_gateway(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_output_type_skill",
            "input_schema": {"type": "object"},
            "name": "反馈输出类型 Skill",
            "output_schema": {
                "properties": {"insights": {"type": "array"}},
                "required": ["insights"],
                "type": "object",
            },
            "prompt_template": "输出 insights 数组。",
            "status": "active",
            "version": "1.0.0",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "feedback_output_type_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈输出类型 AI角色",
            "status": "active",
            "system_prompt": "输出结构化反馈洞察。",
        },
        headers=admin_headers,
    ).json()["data"]

    class InvalidModelResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            content = {"insights": "not-a-list", "row_count": 1}
            return json.dumps(
                {
                    "choices": [
                        {"message": {"content": json.dumps(content, ensure_ascii=False)}},
                    ],
                    "usage": {"completion_tokens": 8, "prompt_tokens": 16, "total_tokens": 24},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    monkeypatch.setattr(
        scheduled_job_ai_processing_service,
        "urlopen",
        lambda *_args, **_kwargs: InvalidModelResponse(),
    )

    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "output_type_feedback_reader",
            "name": "输出类型反馈读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://output-type-feedback.example.com",
            "environment": "prod",
            "name": "输出类型反馈连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_output_type_feedback",
            "connection_id": connection["id"],
            "name": "拉取输出类型反馈",
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {"row_count": 1, "rows": [{"content": "卡顿"}]},
                "path": "/feedback",
            },
            "result_mapping": {
                "insights_path": "$.insights",
                "records_imported_path": "$.row_count",
                "write_target": "user_feedback_insights",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "user_feedback_insight_extract",
            "model_gateway_config_id": model_gateway["id"],
            "name": "输出类型 Schema 校验作业",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
        },
        headers=admin_headers,
    ).json()["data"]

    run = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    ).json()["data"]

    assert run["status"] == "failed"
    assert run["error_code"] == "SKILL_OUTPUT_SCHEMA_INVALID"
    skill_node = run["result_summary"]["execution_nodes"]["skill_processing"]
    assert skill_node["status"] == "failed"
    assert skill_node["model_gateway_called"] is True
    assert skill_node["model_gateway_config_id"] == model_gateway["id"]
    assert skill_node["model_log_id"].startswith("model_log_")
    assert "$.insights expected array, got string" in skill_node["error_message"]
    processing = run["result_summary"]["processing"]
    assert processing["model_gateway_called"] is True
    assert processing["model_log_id"] == skill_node["model_log_id"]
    model_logs = {
        item["id"]: item
        for item in app.state.store.model_gateway_logs
        if item.get("purpose") == "scheduled_job_ai_processing"
    }
    assert model_logs[skill_node["model_log_id"]]["status"] == "succeeded"
    assert model_logs[skill_node["model_log_id"]]["tokens"]["total"] == 24
    assert run["result_summary"]["execution_nodes"]["result_action"]["status"] == "not_run"
    feedback_items = client.get(
        f"/api/insights/user-feedback?product_id={product['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert feedback_items["total"] == 0


def test_user_feedback_job_dispatches_local_ai_executor_and_completes_writeback(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    product = create_product(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_codex_skill",
            "input_schema": {"type": "object"},
            "name": "反馈 Codex Skill",
            "output_schema": {
                "properties": {
                    "insights": {
                        "items": {
                            "properties": {"content": {"type": "string"}},
                            "required": ["content"],
                            "type": "object",
                        },
                        "type": "array",
                    },
                    "summary": {"type": "string"},
                },
                "required": ["insights"],
                "type": "object",
            },
            "prompt_template": "从用户反馈中提取 insights。",
            "status": "active",
            "version": "1.0.0",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "feedback_codex_agent",
            "default_skill_ids": [skill["id"]],
            "name": "反馈 Codex AI角色",
            "status": "active",
            "system_prompt": "输出结构化用户洞察。",
        },
        headers=admin_headers,
    ).json()["data"]
    runner = client.post(
        "/api/system/ai-executor-runners",
        json={
            "executor_types": ["codex"],
            "name": "Codex 本地执行器",
            "protocol": "runner_polling",
            "runner_token": "runner-secret",
            "workspace_roots": ["/tmp/e-ai-brain"],
        },
        headers=admin_headers,
    ).json()["data"]
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "codex_feedback_reader",
            "name": "Codex 反馈读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://codex-feedback.example.com",
            "name": "Codex 反馈连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_codex_feedback",
            "connection_id": connection["id"],
            "name": "拉取 Codex 反馈",
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {
                    "row_count": 2,
                    "rows": [
                        {"content": "看板加载慢", "id": "fb-1"},
                        {"content": "希望支持周报洞察", "id": "fb-2"},
                    ],
                },
                "path": "/feedback",
            },
            "result_mapping": {
                "insights_path": "$.insights",
                "records_imported_path": "$.row_count",
                "write_target": "user_feedback_insights",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    model_called = False

    def fail_if_model_called(*_args, **_kwargs):
        nonlocal model_called
        model_called = True
        raise AssertionError("local AI executor should not call model gateway")

    monkeypatch.setattr(scheduled_job_ai_processing_service, "urlopen", fail_if_model_called)

    created_job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "config_json": {
                "ai_executor": {
                    "executor_type": "codex",
                    "instruction_timeout_seconds": 900,
                    "runner_id": runner["id"],
                    "workspace_root": "/tmp/e-ai-brain",
                },
            },
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "user_feedback_insight_extract",
            "name": "Codex 用户反馈洞察",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
        },
        headers=admin_headers,
    )
    assert created_job.status_code == 200
    job = created_job.json()["data"]
    assert job["model_gateway_config_id"] is None
    assert job["config_json"]["ai_executor"]["runner_id"] == runner["id"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    )
    assert run_response.status_code == 200
    assert model_called is False
    run = run_response.json()["data"]
    assert run["status"] == "running"
    execution_nodes = run["result_summary"]["execution_nodes"]
    assert execution_nodes["runner_execution"]["status"] == "queued"
    assert execution_nodes["runner_execution"]["executor_type"] == "codex"
    assert execution_nodes["skill_processing"]["status"] == "waiting_runner"
    assert execution_nodes["skill_processing"]["model_gateway_called"] is False
    assert execution_nodes["result_action"]["status"] == "not_run"

    task_id = execution_nodes["runner_execution"]["runner_task_id"]
    task = app.state.store.ai_executor_tasks[task_id]
    assert task["scheduled_job_run_id"] == run["id"]
    assert task["request_config"]["scheduled_job_ai_execution"]["stage"] == "ai_processing"
    execution_actor = task["request_config"]["scheduled_job_ai_execution"]["execution_actor"]
    assert execution_actor["id"] == "user_admin"
    assert "admin" in execution_actor["roles"]
    assert task["input_payload"]["source_row_count"] == 2

    completed = client.post(
        f"/api/system/ai-executor-tasks/{task_id}/complete",
        json={
            "logs": [{"level": "info", "message": "codex finished"}],
            "result_json": {
                "result": {
                    "insights": [
                        {
                            "content": "看板加载慢影响客服复盘效率，应优先优化性能。",
                            "feedback_type": "improvement",
                            "product_id": product["id"],
                            "sentiment": "negative",
                            "source_channel": "codex_runner",
                            "tags": ["feedback", "performance"],
                        },
                    ],
                    "summary": "Codex 已提取 1 条高价值洞察。",
                },
            },
            "runner_id": runner["id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert completed.status_code == 200

    listed_runs = client.get(
        f"/api/system/scheduled-job-runs?run_id={run['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    completed_run = listed_runs[0]
    assert completed_run["status"] == "succeeded"
    completed_nodes = completed_run["result_summary"]["execution_nodes"]
    assert completed_nodes["runner_execution"]["status"] == "succeeded"
    assert completed_nodes["skill_processing"]["processing_mode"] == "ai_executor_runner"
    assert completed_nodes["skill_processing"]["model_gateway_called"] is False
    assert completed_nodes["result_action"]["status"] == "succeeded"
    assert completed_nodes["result_action"]["records_imported"] == 1
    assert completed_run["records_imported"] == 1

    feedback_items = client.get(
        f"/api/insights/user-feedback?product_id={product['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert feedback_items["total"] == 1
    assert feedback_items["items"][0]["source_channel"] == "codex_runner"


def test_user_feedback_job_continues_after_result_action_mapping_failure(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    product = create_product(admin_headers)
    model_gateway = create_model_gateway(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_partial_action_skill",
            "input_schema": {"type": "object"},
            "name": "反馈部分动作失败 Skill",
            "output_schema": {
                "properties": {
                    "bad_insights": {"type": "string"},
                    "insights": {"type": "array"},
                },
                "required": ["insights"],
                "type": "object",
            },
            "prompt_template": "输出 insights 数组。",
            "status": "active",
            "version": "1.0.0",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "feedback_partial_action_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈部分动作失败 AI角色",
            "status": "active",
            "system_prompt": "分析用户反馈并输出结构化洞察。",
        },
        headers=admin_headers,
    ).json()["data"]

    class FakeModelResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            content = {
                "bad_insights": "not-a-list",
                "insights": [
                    {
                        "content": "AI 提炼的可落地改进",
                        "feedback_type": "improvement",
                        "sentiment": "neutral",
                        "source_channel": "weekly_ai",
                        "tags": ["ai"],
                    },
                ],
                "row_count": 1,
            }
            return json.dumps(
                {
                    "choices": [
                        {"message": {"content": json.dumps(content, ensure_ascii=False)}},
                    ],
                    "usage": {"completion_tokens": 16, "prompt_tokens": 32, "total_tokens": 48},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    monkeypatch.setattr(
        scheduled_job_ai_processing_service,
        "urlopen",
        lambda *_args, **_kwargs: FakeModelResponse(),
    )

    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "feedback_partial_action_reader",
            "name": "反馈部分动作失败读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://partial-action-feedback.example.com",
            "environment": "prod",
            "name": "反馈部分动作失败连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    archive_action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "archive_partial_action_feedback",
            "connection_id": connection["id"],
            "name": "归档用户反馈 AI 结果",
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {"row_count": 1, "rows": [{"content": "希望优化导出"}]},
                "path": "/feedback",
            },
            "result_mapping": {
                "insights_path": "$.insights",
                "records_imported_path": "$.row_count",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    broken_action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "broken_partial_action_feedback",
            "connection_id": connection["id"],
            "name": "错误映射用户反馈 AI 结果",
            "plugin_id": plugin["id"],
            "request_config": {"method": "POST", "path": "/broken"},
            "result_mapping": {
                "insights_path": "$.bad_insights",
                "records_imported_path": "$.row_count",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    write_action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "write_partial_action_feedback",
            "connection_id": connection["id"],
            "name": "写入用户洞察",
            "plugin_id": plugin["id"],
            "request_config": {"method": "POST", "path": "/insights"},
            "result_mapping": {
                "insights_path": "$.insights",
                "records_imported_path": "$.row_count",
                "write_target": "user_feedback_insights",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "user_feedback_insight_extract",
            "model_gateway_config_id": model_gateway["id"],
            "name": "用户反馈结果动作部分失败继续执行",
            "plugin_action_id": archive_action["id"],
            "plugin_action_ids": [
                archive_action["id"],
                broken_action["id"],
                write_action["id"],
            ],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
        },
        headers=admin_headers,
    ).json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    assert run["records_imported"] == 1
    result_actions = run["result_summary"]["execution_nodes"]["result_actions"]
    assert [action["status"] for action in result_actions] == [
        "succeeded",
        "failed",
        "succeeded",
    ]
    assert result_actions[1]["action_id"] == broken_action["id"]
    assert result_actions[1]["error_code"] == "PLUGIN_RESULT_INVALID"
    assert result_actions[2]["action_id"] == write_action["id"]
    assert result_actions[2]["records_imported"] == 1
    assert run["result_summary"]["result_action_policy"] == {
        "failure_policy": "continue_on_error",
        "mode": "sequential",
    }
    trace_nodes = run["result_summary"]["trace_graph"]["nodes"]
    by_id = {node["id"]: node for node in trace_nodes}
    assert by_id["result_action_2"]["status"] == "failed"
    assert by_id["result_action_2"]["error"]["code"] == "PLUGIN_RESULT_INVALID"
    assert by_id["result_action_3"]["status"] == "succeeded"

    result_records = client.get(
        f"/api/system/result-write-records?scheduled_job_run_id={run['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert [item["status"] for item in result_records["items"]] == [
        "succeeded",
        "failed",
        "succeeded",
    ]
    feedback_items = client.get(
        f"/api/insights/user-feedback?product_id={product['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert feedback_items["total"] == 1
    assert feedback_items["items"][0]["source_channel"] == "weekly_ai"


def test_scheduled_job_dry_run_previews_data_ai_contract_and_write_mapping():
    app.state.store.reset()
    admin_headers = auth_headers()
    product = create_product(admin_headers)
    model_gateway = create_model_gateway(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_dry_run_skill",
            "input_schema": {"type": "object"},
            "name": "反馈试运行 Skill",
            "output_schema": {
                "properties": {"insights": {"type": "array"}},
                "required": ["insights"],
                "type": "object",
            },
            "prompt_template": "输出 insights 数组。",
            "status": "active",
            "version": "1.0.0",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "feedback_dry_run_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈试运行 AI角色",
            "status": "active",
            "system_prompt": "分析反馈。",
        },
        headers=admin_headers,
    ).json()["data"]
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "dry_run_feedback_reader",
            "name": "试运行反馈读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://dry-run-feedback.example.com",
            "environment": "prod",
            "name": "试运行反馈连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_dry_run_feedback",
            "connection_id": connection["id"],
            "name": "拉取试运行反馈",
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {"row_count": 2, "rows": [{"id": 1}, {"id": 2}]},
                "path": "/feedback",
            },
            "result_mapping": {
                "insights_path": "$.insights",
                "records_imported_path": "$.row_count",
                "write_target": "user_feedback_insights",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        "/api/system/scheduled-jobs/dry-run",
        json={
            "agent_id": agent["id"],
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "user_feedback_insight_extract",
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈试运行草稿",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "succeeded"
    assert data["stages"]["data_connection"]["connection_id"] == connection["id"]
    assert data["stages"]["data_connection"]["records_imported"] == 2
    assert data["stages"]["data_connection"]["sample_source"] == "live_dry_run_response"
    assert data["stages"]["data_connection"]["sample_reuse_status"] == "ready"
    assert data["sample_reuse"]["data_connection_sample"] == {
        "records_imported": 2,
        "response_available": True,
        "source": "live_dry_run_response",
        "status": "ready",
    }
    assert data["sample_reuse"]["preferred_action_preview_source"] == "skill_output_schema"
    assert data["sample_reuse"]["action_preview_ready"] is True
    assert data["sample_reuse"]["output_preview_ready"] is True
    assert [step["status"] for step in data["sample_reuse"]["reusable_steps"]] == [
        "ready",
        "ready",
        "ready",
    ]
    assert data["sample_reuse"]["reuse_wizard"]["current_step"] == "scheduled_job_dry_run"
    assert data["sample_reuse"]["reuse_wizard"]["next_action"] == "save_scheduled_job"
    assert data["sample_reuse"]["reuse_wizard"]["primary_action_label"] == "保存为定时作业"
    assert data["sample_reuse"]["reuse_wizard"]["status"] == "ready"
    assert data["sample_reuse"]["reuse_wizard"]["can_continue"] is True
    assert data["sample_reuse"]["reuse_wizard"]["current_step_label"] == "全链路试运行"
    assert data["sample_reuse"]["reuse_wizard"]["completed_steps"] == 4
    assert data["sample_reuse"]["reuse_wizard"]["blocked_steps"] == 0
    assert data["sample_reuse"]["reuse_wizard"]["pending_steps"] == 0
    assert data["sample_reuse"]["reuse_wizard"]["progress_percent"] == 100
    assert data["sample_reuse"]["reuse_wizard"]["progress_label"] == "4/4 步已就绪"
    assert data["sample_reuse"]["reuse_wizard"]["total_steps"] == 4
    assert (
        "保存当前配置为定时作业" in data["sample_reuse"]["reuse_wizard"]["next_action_description"]
    )
    assert [
        (item["key"], item["status"])
        for item in data["sample_reuse"]["reuse_wizard"]["handoff_summary"]
    ] == [
        ("data_connection_sample", "ready"),
        ("ai_output_preview", "ready"),
        ("action_write_preview", "ready"),
        ("job_config", "ready"),
    ]
    assert data["sample_reuse"]["reuse_wizard"]["missing_requirements"] == []
    assert [step["key"] for step in data["sample_reuse"]["reuse_wizard"]["steps"]] == [
        "connection_test",
        "ai_processing_preview",
        "action_trial",
        "scheduled_job_config",
    ]
    assert [step["status"] for step in data["sample_reuse"]["reuse_wizard"]["steps"]] == [
        "succeeded",
        "succeeded",
        "succeeded",
        "ready",
    ]
    assert data["sample_reuse"]["job_config_preview"]["plugin_connection_ids"] == [
        connection["id"],
    ]
    assert data["sample_reuse"]["job_config_preview"]["plugin_action_ids"] == [action["id"]]
    assert data["stages"]["ai_processing"]["will_call_model_gateway"] is True
    assert data["stages"]["ai_processing"]["mapping_status"] == "succeeded"
    assert data["stages"]["ai_processing"]["output_schema"]["required"] == ["insights"]
    assert data["stages"]["ai_processing"]["mapping_contract"] == {
        "checked_paths": [
            {
                "field": "insights_path",
                "path": "$.insights",
                "supported": True,
            }
        ],
        "invalid_fields": [],
        "output_schema": data["stages"]["ai_processing"]["output_schema"],
        "status": "succeeded",
    }
    assert data["stages"]["ai_processing"]["output_preview_source"] == "skill_output_schema"
    assert len(data["stages"]["ai_processing"]["output_preview"]["insights"]) == 2
    assert data["stages"]["ai_processing"]["output_preview"]["insights"][0] == {
        "confidence": 1,
        "feedback_type": "improvement",
        "sentiment": "neutral",
        "source_channel": "dry_run",
        "summary": "AI Brain dry-run sample summary",
        "title": "AI Brain dry-run sample",
    }
    assert data["stages"]["result_actions"][0]["write_target"] == "user_feedback_insights"
    assert data["stages"]["result_actions"][0]["write_preview_source"] == "skill_output_schema"
    assert data["stages"]["result_actions"][0]["write_preview"]["candidate_count"] == 2
    assert data["stages"]["result_actions"][0]["write_preview"]["records_imported"] == 2
    assert data["stages"]["result_actions"][0]["write_preview"]["sample_records"][0] == {
        "confidence": 1,
        "feedback_type": "improvement",
        "sentiment": "neutral",
        "source_channel": "dry_run",
        "summary": "AI Brain dry-run sample summary",
        "title": "AI Brain dry-run sample",
    }
    invocation_log = next(
        log
        for log in app.state.store.plugin_invocation_logs.values()
        if log["action_id"] == action["id"]
    )
    assert invocation_log["trigger_type"] == "dry_run"
    assert invocation_log["scheduled_job_id"] is None
    assert invocation_log["scheduled_job_run_id"] is None

    invocation_log_count = len(app.state.store.plugin_invocation_logs)
    sample_response = client.post(
        "/api/system/scheduled-jobs/dry-run",
        json={
            "agent_id": agent["id"],
            "config_json": {
                "sample_reuse": {
                    "action_id": action["id"],
                    "connection_id": connection["id"],
                    "response_summary": {
                        "json": {
                            "row_count": 4,
                            "rows": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}],
                        },
                    },
                    "sample_source": "connection_test_response",
                },
            },
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "user_feedback_insight_extract",
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈样例复用试运行草稿",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
        },
        headers=admin_headers,
    )

    assert sample_response.status_code == 200
    sample_data = sample_response.json()["data"]
    assert sample_data["status"] == "succeeded"
    assert sample_data["stages"]["data_connection"]["records_imported"] == 4
    assert sample_data["stages"]["data_connection"]["sample_source"] == ("connection_test_response")
    assert (
        sample_data["stages"]["data_connection"]["request_summary"]["processing_mode"]
        == "sample_reuse"
    )
    assert sample_data["sample_reuse"]["data_connection_sample"] == {
        "records_imported": 4,
        "response_available": True,
        "source": "connection_test_response",
        "status": "ready",
    }
    assert sample_data["sample_reuse"]["reuse_wizard"]["sample_source"] == (
        "connection_test_response"
    )
    assert sample_data["sample_reuse"]["reuse_wizard"]["progress_label"] == ("4/4 步已就绪")
    assert sample_data["sample_reuse"]["reuse_wizard"]["progress_percent"] == 100
    assert sample_data["sample_reuse"]["reuse_wizard"]["steps"][0]["source"] == (
        "connection_test_response"
    )
    assert sample_data["stages"]["ai_processing"]["output_preview_source"] == "skill_output_schema"
    assert len(sample_data["stages"]["ai_processing"]["output_preview"]["insights"]) == 3
    assert len(app.state.store.plugin_invocation_logs) == invocation_log_count


def test_public_skill_marks_package_scripts_as_pending_sandbox():
    skill = scheduled_job_ai_capabilities_service.public_skill(
        {
            "code": "packaged_with_script",
            "name": "脚本 Skill 包",
            "package_files": [
                "SKILL.md",
                "schemas/output.json",
                "notes.py",
                "scripts/run.py",
            ],
            "source_type": "package",
        },
    )

    assert skill["runtime_capabilities"]["prompt_execution"] == "enabled"
    assert skill["runtime_capabilities"]["schema_validation"] == "enabled"
    assert skill["runtime_capabilities"]["script_execution"] == "disabled_pending_sandbox"
    assert skill["runtime_capabilities"]["script_files"] == ["scripts/run.py"]
    assert "notes.py" not in skill["runtime_capabilities"]["script_files"]
    assert "不会自动执行" in skill["runtime_capabilities"]["script_note"]


def test_public_agent_marks_package_scripts_as_pending_sandbox():
    agent = scheduled_job_ai_capabilities_service.public_agent(
        {
            "code": "packaged_agent_with_script",
            "name": "脚本 Agent 包",
            "package_files": ["AGENT.md", "agent.yaml", "tools.ts", "scripts/run.py"],
            "source_type": "package",
        },
    )

    assert agent["runtime_capabilities"]["default_skill_binding"] == "enabled"
    assert agent["runtime_capabilities"]["package_context"] == "enabled"
    assert agent["runtime_capabilities"]["script_execution"] == "disabled_pending_sandbox"
    assert agent["runtime_capabilities"]["script_files"] == ["scripts/run.py"]
    assert "tools.ts" not in agent["runtime_capabilities"]["script_files"]
    assert agent["runtime_capabilities"]["system_prompt_execution"] == "enabled"
    assert "不会自动执行" in agent["runtime_capabilities"]["script_note"]


def build_skill_package() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as package:
        package.writestr(
            "skill.yaml",
            "\n".join(
                [
                    "code: packaged_iteration_planning",
                    "name: 文件包迭代规划",
                    "version: 1.0.0",
                    "entry: SKILL.md",
                    "allowed_tools:",
                    "  - user_feedback",
                    "  - bugs",
                    "requires_human_review: true",
                    "risk_level: high",
                ],
            ),
        )
        package.writestr(
            "SKILL.md",
            "# 文件包迭代规划\n\n基于真实用户反馈、Bug 和线上日志生成迭代建议。",
        )
        package.writestr("schemas/input.json", '{"type":"object"}')
        package.writestr("schemas/output.json", '{"type":"object"}')
        package.writestr("scripts/run.py", "print('skill script placeholder')\n")
    return buffer.getvalue()


def build_agent_package(
    *,
    model_gateway_config_id: str | None = None,
    skill_id: str | None = None,
) -> bytes:
    manifest_lines = [
        "code: packaged_feedback_agent",
        "name: 文件包反馈分析角色",
        "entry: AGENT.md",
        "brain_app_id: rd_brain",
    ]
    if model_gateway_config_id:
        manifest_lines.append(f"model_gateway_config_id: {model_gateway_config_id}")
    if skill_id:
        manifest_lines.extend(["default_skill_ids:", f"  - {skill_id}"])
    buffer = BytesIO()
    with ZipFile(buffer, "w") as package:
        package.writestr("agent.yaml", "\n".join(manifest_lines))
        package.writestr(
            "AGENT.md",
            "# 文件包反馈分析角色\n\n你负责将用户反馈整理成可落地洞察。",
        )
        package.writestr("scripts/run.py", "print('agent script placeholder')\n")
    return buffer.getvalue()


def build_skill_package_with_root_script() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as package:
        package.writestr("skill.yaml", "code: invalid_script\nname: 非法脚本\nentry: SKILL.md")
        package.writestr("SKILL.md", "# 非法脚本")
        package.writestr("run.py", "print('not allowed')\n")
    return buffer.getvalue()


def build_agent_package_with_root_script() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as package:
        package.writestr("agent.yaml", "code: invalid_agent\nname: 非法 Agent\nentry: AGENT.md")
        package.writestr("AGENT.md", "# 非法 Agent")
        package.writestr("run.py", "print('not allowed')\n")
    return buffer.getvalue()


def test_ai_skill_package_upload_stores_manifest_and_local_files():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    forbidden = client.post(
        "/api/system/ai-skills/upload",
        params={"code": "packaged_iteration_planning", "name": "文件包迭代规划"},
        content=build_skill_package(),
        headers={**reviewer_headers, "Content-Type": "application/zip"},
    )
    assert forbidden.status_code == 403

    response = client.post(
        "/api/system/ai-skills/upload",
        params={"code": "packaged_iteration_planning", "name": "文件包迭代规划"},
        content=build_skill_package(),
        headers={**admin_headers, "Content-Type": "application/zip"},
    )

    assert response.status_code == 200
    skill = response.json()["data"]
    assert skill["source_type"] == "package"
    assert skill["package_checksum"]
    assert skill["package_uri"].startswith("file://")
    assert skill["manifest"]["entry"] == "SKILL.md"
    assert skill["manifest"]["code"] == "packaged_iteration_planning"
    assert skill["package_entry"] == "SKILL.md"
    assert "SKILL.md" in skill["package_files"]
    assert "scripts/run.py" in skill["package_files"]
    assert skill["prompt_template"].startswith("# 文件包迭代规划")
    assert skill["runtime_capabilities"]["script_execution"] == "disabled_pending_sandbox"
    assert skill["runtime_capabilities"]["script_files"] == ["scripts/run.py"]

    listed = client.get("/api/system/ai-skills", headers=admin_headers).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["package_checksum"] == skill["package_checksum"]


def test_ai_skill_package_rejects_executable_files_outside_scripts_dir():
    app.state.store.reset()
    admin_headers = auth_headers()

    response = client.post(
        "/api/system/ai-skills/upload",
        params={"code": "invalid_script", "name": "非法脚本"},
        content=build_skill_package_with_root_script(),
        headers={**admin_headers, "Content-Type": "application/zip"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_SKILL_PACKAGE"


def test_ai_agent_package_upload_stores_manifest_and_local_files():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    model_gateway = create_model_gateway(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_extract",
            "input_schema": {"type": "object"},
            "name": "反馈洞察抽取",
            "output_schema": {"type": "object"},
            "prompt_template": "抽取用户反馈洞察",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    package_bytes = build_agent_package(
        model_gateway_config_id=model_gateway["id"],
        skill_id=skill["id"],
    )

    forbidden = client.post(
        "/api/system/ai-agents/upload",
        params={"code": "packaged_feedback_agent", "name": "文件包反馈分析角色"},
        content=package_bytes,
        headers={**reviewer_headers, "Content-Type": "application/zip"},
    )
    assert forbidden.status_code == 403

    response = client.post(
        "/api/system/ai-agents/upload",
        params={"code": "packaged_feedback_agent", "name": "文件包反馈分析角色"},
        content=package_bytes,
        headers={**admin_headers, "Content-Type": "application/zip"},
    )

    assert response.status_code == 200
    agent = response.json()["data"]
    assert agent["source_type"] == "package"
    assert agent["package_checksum"]
    assert agent["package_uri"].startswith("file://")
    assert agent["manifest"]["entry"] == "AGENT.md"
    assert agent["manifest"]["code"] == "packaged_feedback_agent"
    assert agent["default_skill_ids"] == [skill["id"]]
    assert agent["model_gateway_config_id"] == model_gateway["id"]
    assert agent["package_entry"] == "AGENT.md"
    assert "AGENT.md" in agent["package_files"]
    assert "scripts/run.py" in agent["package_files"]
    assert agent["system_prompt"].startswith("# 文件包反馈分析角色")
    assert agent["runtime_capabilities"]["package_context"] == "enabled"
    assert agent["runtime_capabilities"]["script_execution"] == "disabled_pending_sandbox"
    assert agent["runtime_capabilities"]["script_files"] == ["scripts/run.py"]

    listed = client.get("/api/system/ai-agents", headers=admin_headers).json()["data"]
    packaged_agents = [item for item in listed["items"] if item["id"] == agent["id"]]
    assert packaged_agents
    assert packaged_agents[0]["package_checksum"] == agent["package_checksum"]


def test_ai_agent_package_rejects_executable_files_outside_scripts_dir():
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)

    response = client.post(
        "/api/system/ai-agents/upload",
        params={
            "brain_app_id": "rd_brain",
            "code": "invalid_agent",
            "model_gateway_config_id": model_gateway["id"],
            "name": "非法 Agent",
        },
        content=build_agent_package_with_root_script(),
        headers={**admin_headers, "Content-Type": "application/zip"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_AGENT_PACKAGE"


def test_ai_skills_agents_and_scheduled_jobs_are_admin_managed():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    model_gateway = create_model_gateway(admin_headers)

    forbidden = client.post(
        "/api/system/ai-skills",
        json={
            "code": "iteration_planning",
            "name": "迭代规划",
            "prompt_template": "生成迭代建议",
        },
        headers=reviewer_headers,
    )
    assert forbidden.status_code == 403

    skill = client.post(
        "/api/system/ai-skills",
        json={
            "allowed_tools": ["user_feedback", "bugs"],
            "code": "iteration_planning",
            "input_schema": {"type": "object"},
            "name": "迭代规划",
            "output_schema": {"type": "object"},
            "prompt_template": "根据真实证据生成迭代建议",
            "requires_human_review": True,
            "risk_level": "high",
            "status": "active",
            "version": "1.0.0",
        },
        headers=admin_headers,
    )
    assert skill.status_code == 200
    skill_data = skill.json()["data"]
    assert skill_data["id"].startswith("skill_")
    assert "api_key" not in skill_data

    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "iteration_planner",
            "default_skill_ids": [skill_data["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "迭代规划 Agent",
            "status": "active",
            "system_prompt": "你是产品迭代规划助手。",
        },
        headers=admin_headers,
    )
    assert agent.status_code == 200
    agent_data = agent.json()["data"]
    assert agent_data["default_skill_ids"] == [skill_data["id"]]

    product = create_product(admin_headers)
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent_data["id"],
            "config_json": {
                "include_evidence": True,
                "planning_cycle": "weekly",
            },
            "cron_expression": "0 9 * * MON",
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "iteration_plan_suggestion_generate",
            "model_gateway_config_id": model_gateway["id"],
            "name": "每周迭代建议",
            "product_id": product["id"],
            "schedule_type": "cron",
            "skill_ids": [skill_data["id"]],
            "source_system": "ai-brain",
            "timezone": "Asia/Shanghai",
        },
        headers=admin_headers,
    )
    assert job.status_code == 200
    job_data = job.json()["data"]
    assert job_data["id"].startswith("scheduled_job_")
    assert job_data["next_run_at"]

    listed = client.get("/api/system/scheduled-jobs", headers=admin_headers).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["agent_id"] == agent_data["id"]

    patched = client.patch(
        f"/api/system/scheduled-jobs/{job_data['id']}",
        json={"enabled": False, "name": "每周迭代建议 v2"},
        headers=admin_headers,
    )
    assert patched.status_code == 200
    patched_data = patched.json()["data"]
    assert patched_data["enabled"] is False
    assert patched_data["name"] == "每周迭代建议 v2"
    assert patched_data["status"] == "disabled"

    deleted = client.delete(
        f"/api/system/scheduled-jobs/{job_data['id']}",
        headers=admin_headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {"deleted": True, "id": job_data["id"]}
    listed_after_delete = client.get(
        "/api/system/scheduled-jobs",
        headers=admin_headers,
    ).json()["data"]
    assert listed_after_delete["total"] == 0


def test_scheduled_job_audit_includes_assistant_draft_source():
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    product = create_product(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_insight",
            "name": "反馈洞察",
            "prompt_template": "提取用户反馈洞察",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "feedback_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈分析 Agent",
            "status": "active",
            "system_prompt": "你负责分析用户反馈。",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "config_json": {
                "assistant_draft": {
                    "draft_id": "assistant_draft_weekly_feedback_insight",
                    "source": "assistant.action_draft",
                    "title": "每周用户反馈洞察抽取",
                },
            },
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "iteration_plan_suggestion_generate",
            "model_gateway_config_id": model_gateway["id"],
            "name": "每周用户反馈洞察抽取",
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    job = response.json()["data"]

    audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job.created&subject_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert audit_events[0]["payload"]["assistant_draft"] == {
        "draft_id": "assistant_draft_weekly_feedback_insight",
        "source": "assistant.action_draft",
        "title": "每周用户反馈洞察抽取",
    }

    update_response = client.patch(
        f"/api/system/scheduled-jobs/{job['id']}",
        json={"name": "每周用户反馈洞察抽取 v2"},
        headers=admin_headers,
    )
    assert update_response.status_code == 200

    updated_audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job.updated&subject_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert updated_audit_events[0]["payload"]["assistant_draft"] == {
        "draft_id": "assistant_draft_weekly_feedback_insight",
        "source": "assistant.action_draft",
        "title": "每周用户反馈洞察抽取",
    }


def test_scheduled_job_audit_includes_template_source():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "template_source_test",
            "name": "模板来源测试插件",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://example.com/template-source",
            "name": "模板来源测试连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "template_source_test_action",
            "connection_id": connection["id"],
            "name": "模板来源测试动作",
            "plugin_id": plugin["id"],
            "request_config": {"method": "GET", "mock_response_json": {"row_count": 0}},
            "result_mapping": {
                "records_imported_path": "$.row_count",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "template_source": {
                    "source_id": "scheduled_job_run_weekly_feedback",
                    "source_type": "scheduled_job_run",
                    "title": "每周用户反馈洞察",
                },
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "name": "每周用户反馈洞察 运行快照副本",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "schedule_type": "manual",
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    job = response.json()["data"]

    audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job.created&subject_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert audit_events[0]["payload"]["template_source"] == {
        "source_id": "scheduled_job_run_weekly_feedback",
        "source_type": "scheduled_job_run",
        "title": "每周用户反馈洞察",
    }

    update_response = client.patch(
        f"/api/system/scheduled-jobs/{job['id']}",
        json={"enabled": False},
        headers=admin_headers,
    )
    assert update_response.status_code == 200

    updated_audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job.updated&subject_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert updated_audit_events[0]["payload"]["template_source"] == {
        "source_id": "scheduled_job_run_weekly_feedback",
        "source_type": "scheduled_job_run",
        "title": "每周用户反馈洞察",
    }


def test_scheduled_job_rejects_unsearchable_knowledge_reference():
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    product = create_product(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_insight",
            "name": "反馈洞察",
            "prompt_template": "结合知识文档提取用户反馈洞察",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "feedback_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈分析 Agent",
            "status": "active",
            "system_prompt": "你负责分析用户反馈。",
        },
        headers=admin_headers,
    ).json()["data"]
    knowledge = client.post(
        "/api/knowledge/documents",
        json={
            "content": "支付页无响应时优先排查回调超时。",
            "doc_type": "runbook",
            "permission_roles": ["admin"],
            "product_id": product["id"],
            "title": "支付排障知识",
        },
        headers=admin_headers,
    ).json()["data"]
    app.state.store.knowledge_documents[knowledge["id"]]["index_status"] = "pending_index"

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "iteration_plan_suggestion_generate",
            "knowledge_document_ids": [knowledge["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "每周带知识反馈洞察",
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "KNOWLEDGE_DOCUMENT_NOT_SEARCHABLE"


def test_user_feedback_collect_with_ai_pipeline_is_normalized_to_insight_extract():
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    product = create_product(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_insight",
            "name": "反馈洞察",
            "prompt_template": "提取用户反馈洞察",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "feedback_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈分析 Agent",
            "status": "active",
            "system_prompt": "你负责分析用户反馈。",
        },
        headers=admin_headers,
    ).json()["data"]
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "maxcompute_feedback",
            "name": "MaxCompute 用户反馈",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://example.com/feedback",
            "name": "反馈数据连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_feedback",
            "connection_id": connection["id"],
            "name": "获取反馈",
            "plugin_id": plugin["id"],
            "request_config": {"method": "GET", "mock_response_json": {"row_count": 0}},
            "result_mapping": {
                "insights_path": "$.insights",
                "records_imported_path": "$.row_count",
                "write_target": "user_feedback_insights",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "user_feedback_collect",
            "model_gateway_config_id": model_gateway["id"],
            "name": "提取每周用户反馈有价值信息",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
            "source_system": "aliyun-maxcompute",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    job = response.json()["data"]
    assert job["job_type"] == "user_feedback_insight_extract"
    assert job["execution_mode"] == "ai_generated"
    assert job["agent_id"] == agent["id"]
    assert job["model_gateway_config_id"] == model_gateway["id"]
    assert job["skill_ids"] == [skill["id"]]


def test_plugin_action_scheduled_job_run_records_request_trace_summary():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "business_system",
            "code": "feedback_api",
            "name": "反馈 API",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://example.com",
            "environment": "prod",
            "name": "生产反馈 API",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_feedback",
            "connection_id": connection["id"],
            "name": "获取反馈",
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {"rows": [{"id": "feedback_001"}]},
                "path": "/feedback",
                "query": {"start_pt": "{{current_date-7}}"},
            },
            "result_mapping": {
                "records_imported_path": "$.rows",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "name": "反馈接口取数",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "schedule_type": "manual",
            "source_system": "feedback-api",
        },
        headers=admin_headers,
    ).json()["data"]

    run = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    ).json()["data"]

    assert run["result_summary"]["job_type"] == "plugin_action_invoke"
    assert run["result_summary"]["message"] == "插件执行调用完成"
    assert "No handler implemented" not in json.dumps(
        run["result_summary"],
        ensure_ascii=False,
    )
    data_node = run["result_summary"]["execution_nodes"]["data_connection"]
    assert data_node["connection_environment"] == "prod"
    assert data_node["request_method"] == "GET"
    assert data_node["request_url"].startswith("https://example.com/feedback")
    assert "start_pt=" in data_node["request_url"]
    assert isinstance(data_node["latency_ms"], int)
    assert data_node["response_summary"] == {
        "json": {"rows": [{"id": "feedback_001"}]},
        "mocked": True,
    }
    assert data_node["records_imported"] == 1

    app.state.store.model_gateway_logs.append(
        {
            "id": "model_log_scheduled_observability",
            "tokens": {"completion": 12, "prompt": 30, "total": 42},
        },
    )
    app.state.store.scheduled_job_runs["scheduled_job_run_failed_observability"] = {
        **run,
        "error_code": "MODEL_GATEWAY_FAILED",
        "error_message": "模型处理失败",
        "finished_at": "2026-06-13T09:00:05+00:00",
        "id": "scheduled_job_run_failed_observability",
        "plugin_invocation_log_id": None,
        "records_imported": 0,
        "result_summary": {
            "execution_nodes": {
                "data_connection": {"records_imported": 1, "status": "succeeded"},
                "result_action": {
                    "records_imported": 0,
                    "status": "partial_failed",
                    "write_target": "user_feedback_insights",
                },
                "result_actions": [
                    {
                        "records_imported": 1,
                        "status": "succeeded",
                        "write_target": "email_notifications",
                    },
                    {
                        "error_code": "RESULT_WRITE_FAILED",
                        "error_message": "洞察写入失败",
                        "records_imported": 0,
                        "status": "failed",
                        "write_target": "user_feedback_insights",
                    },
                ],
                "skill_processing": {
                    "model_gateway_called": True,
                    "model_log_id": "model_log_scheduled_observability",
                    "status": "failed",
                },
            },
        },
        "started_at": "2026-06-13T09:00:00+00:00",
        "status": "failed",
    }

    observability_response = client.get(
        "/api/system/scheduled-job-runs/observability",
        headers=admin_headers,
    )
    assert observability_response.status_code == 200
    observability = observability_response.json()["data"]
    assert observability["summary"]["total_runs"] == 2
    assert observability["summary"]["succeeded_runs"] == 1
    assert observability["summary"]["failed_runs"] == 1
    assert observability["summary"]["success_rate"] == 50.0
    assert observability["summary"]["failure_rate"] == 50.0
    assert observability["summary"]["model_gateway_called_runs"] == 1
    assert observability["summary"]["model_gateway_token_total"] == 42
    assert observability["summary"]["plugin_invocation_runs"] == 1
    assert observability["summary"]["action_write_runs"] == 3
    assert observability["summary"]["action_write_success_runs"] == 2
    assert observability["summary"]["action_write_success_rate"] == 66.67
    assert observability["write_target_distribution"] == [
        {"count": 1, "write_target": "email_notifications"},
        {"count": 1, "write_target": "scheduled_job_result"},
        {"count": 1, "write_target": "user_feedback_insights"},
    ]
    assert observability["error_distribution"] == [
        {"count": 1, "error": "MODEL_GATEWAY_FAILED"},
    ]
    assert observability["recent_failures"][0]["id"] == "scheduled_job_run_failed_observability"
    assert observability["slow_runs"][0]["latency_ms"] == 5000


def test_online_log_ai_analysis_requires_ai_runtime_configuration():
    app.state.store.reset()
    admin_headers = auth_headers()

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "online_log_ai_analysis",
            "name": "线上日志异常分析",
            "schedule_type": "manual",
            "source_system": "online-log-platform",
        },
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "AI_AGENT_REQUIRED"
    assert "AI job requires agent_id" in response.text


def test_online_log_ai_analysis_runs_data_ai_and_generic_result_action(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "online_log_anomaly_skill",
            "input_schema": {"type": "object"},
            "name": "线上日志异常 Skill",
            "output_schema": {
                "properties": {
                    "anomalies": {
                        "items": {
                            "properties": {
                                "affected_service": {"type": "string"},
                                "evidence": {"type": "string"},
                                "recommendation": {"type": "string"},
                                "severity": {"type": "string"},
                                "summary": {"type": "string"},
                            },
                            "type": "object",
                        },
                        "type": "array",
                    },
                    "risk_level": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["summary", "anomalies"],
                "type": "object",
            },
            "prompt_template": "分析日志异常并输出 anomalies。",
            "status": "active",
            "version": "1.0.0",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "online_log_anomaly_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "线上日志异常 AI角色",
            "status": "active",
            "system_prompt": "分析线上日志。",
        },
        headers=admin_headers,
    ).json()["data"]

    class OnlineLogModelResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            content = {
                "anomalies": [
                    {
                        "affected_service": "ai-brain-api",
                        "evidence": "5xx increased from 0.2% to 3.8%",
                        "recommendation": "Check the latest deployment and database latency.",
                        "severity": "high",
                        "summary": "API 5xx error rate increased",
                    },
                ],
                "risk_level": "high",
                "summary": "发现 1 条高风险线上日志异常。",
            }
            return json.dumps(
                {
                    "choices": [
                        {"message": {"content": json.dumps(content, ensure_ascii=False)}},
                    ],
                    "usage": {"completion_tokens": 12, "prompt_tokens": 24, "total_tokens": 36},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    model_gateway_call_count = 0

    def online_log_model_response(*_args, **_kwargs):
        nonlocal model_gateway_call_count
        model_gateway_call_count += 1
        return OnlineLogModelResponse()

    monkeypatch.setattr(
        scheduled_job_ai_processing_service,
        "urlopen",
        online_log_model_response,
    )
    sent_messages: list[dict[str, object]] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            sent_messages.append({"host": host, "port": port, "timeout": timeout})

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            sent_messages.append({"password": password, "username": username})

        def send_message(self, message: object) -> dict:
            sent_messages.append(
                {
                    "from": message["From"],
                    "subject": message["Subject"],
                    "to": message["To"],
                },
            )
            return {}

    monkeypatch.setattr("app.services.system_settings.smtplib.SMTP_SSL", FakeSMTP)
    email_settings_response = client.patch(
        "/api/system/settings",
        json={
            "high_risk_confirmation": {
                "confirmed": True,
                "reason": "测试确认变更邮件发送配置",
            },
            "email_delivery": {
                "default_from": "noreply@example.com",
                "enabled": True,
                "sender_email": "noreply@example.com",
                "smtp_host": "smtp.example.com",
                "smtp_password": "super-secret-password",
                "smtp_port": 465,
                "smtp_tls": "ssl",
                "smtp_username": "noreply@example.com",
            },
        },
        headers=admin_headers,
    )
    assert email_settings_response.status_code == 200

    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "observability",
            "code": "online_log_reader",
            "name": "线上日志读取",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://logs.example.com",
            "environment": "prod",
            "name": "线上日志连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "query_online_log_metrics",
            "connection_id": connection["id"],
            "name": "查询线上日志指标",
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {
                    "row_count": 2,
                    "rows": [
                        {"error_rate": 3.8, "service": "ai-brain-api"},
                        {"p95_latency_ms": 1800, "service": "ai-brain-api"},
                    ],
                },
                "path": "/metrics",
            },
            "result_mapping": {
                "anomalies_path": "$.anomalies",
                "summary_path": "$.summary",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    job_payload = {
        "agent_id": agent["id"],
        "enabled": True,
        "execution_mode": "ai_generated",
        "job_type": "online_log_ai_analysis",
        "model_gateway_config_id": model_gateway["id"],
        "name": "线上日志异常分析",
        "plugin_action_id": action["id"],
        "plugin_connection_id": connection["id"],
        "result_actions": [
            {
                "channels": ["email"],
                "recipients": ["ops@example.com"],
                "type": "send_notification",
            },
        ],
        "schedule_type": "manual",
        "skill_ids": [skill["id"]],
        "source_system": "online-log",
    }
    dry_run_response = client.post(
        "/api/system/scheduled-jobs/dry-run",
        json=job_payload,
        headers=admin_headers,
    )
    assert dry_run_response.status_code == 200
    dry_run = dry_run_response.json()["data"]
    dry_run_notification = next(
        item
        for item in dry_run["stages"]["result_actions"]
        if item.get("type") == "send_notification"
    )
    assert dry_run_notification["write_target"] == "email_notifications"
    assert dry_run_notification["write_preview_source"] == "skill_output_schema"

    job = client.post(
        "/api/system/scheduled-jobs",
        json=job_payload,
        headers=admin_headers,
    ).json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    assert run["records_imported"] == 1
    result_summary = run["result_summary"]
    assert result_summary["anomaly_count"] == 1
    execution_nodes = result_summary["execution_nodes"]
    assert execution_nodes["data_connection"]["records_imported"] == 2
    assert execution_nodes["skill_processing"]["model_gateway_called"] is True
    assert execution_nodes["skill_processing"]["output"]["anomaly_count"] == 1
    assert model_gateway_call_count == 1
    assert execution_nodes["result_action"]["write_target"] == "email_notifications"
    assert execution_nodes["result_action"]["feedback"]["delivery_status"] == "sent"
    assert execution_nodes["result_action"]["feedback"]["message_id"].endswith("@example.com>")
    assert execution_nodes["result_action"]["feedback"]["recipients"] == ["ops@example.com"]
    assert {"password": "super-secret-password", "username": "noreply@example.com"} in sent_messages
    sent_call = next(item for item in sent_messages if item.get("to") == "ops@example.com")
    assert sent_call["from"] == "noreply@example.com"
    assert sent_call["subject"] == "发现 1 条高风险线上日志异常。"
    assert execution_nodes["result_actions"][0]["type"] == "send_notification"
    assert result_summary["result_action_policy"] == {
        "failure_policy": "continue_on_error",
        "mode": "sequential",
    }
    assert result_summary["trace_graph"]["edges"] == [
        {"from": "data_connection", "to": "runner_execution"},
        {"from": "runner_execution", "to": "skill_processing"},
        {"from": "skill_processing", "to": "result_action_1"},
    ]
    node_preview_response = client.get(
        f"/api/system/scheduled-job-runs/{run['id']}/trace-nodes/data_connection/rerun-preview",
        headers=admin_headers,
    )
    assert node_preview_response.status_code == 200
    node_preview = node_preview_response.json()["data"]
    assert node_preview["node_id"] == "data_connection"
    assert node_preview["preflight_status"] == "ready"
    assert node_preview["rerun_supported"] is True
    assert node_preview["blocked_by"] == []
    assert node_preview["missing_controls"] == []
    assert node_preview["control_summary"] == {
        "blocked_count": 0,
        "missing_count": 0,
        "needs_review_count": 0,
        "satisfied_count": 3,
        "status_counts": {"satisfied": 3},
        "total": 3,
    }
    assert node_preview["execution_policy"] == {
        "allowed": True,
        "blocking_count": 0,
        "message": "单节点复跑控制项已满足，可以进入执行确认。",
        "missing_control_count": 0,
        "mode": "single_node_ready",
        "requires_confirmation": True,
        "side_effect_policy": "external_read_or_fetch",
    }
    assert [action["key"] for action in node_preview["next_actions"]] == [
        "inspect_node_snapshot",
        "confirm_single_node_rerun",
    ]
    assert [control["label"] for control in node_preview["rerun_controls"]] == [
        "请求快照",
        "连接读取幂等",
        "下游 AI/动作失效策略",
    ]
    assert [control["status"] for control in node_preview["rerun_controls"]] == [
        "satisfied",
        "satisfied",
        "satisfied",
    ]
    assert node_preview["safe_next_action"] == "confirm_single_node_rerun"
    assert node_preview["snapshot_status"] == {
        "error": False,
        "input": True,
        "output": True,
    }
    assert node_preview["snapshot_preview"]["input"]["available"] is True
    assert node_preview["snapshot_preview"]["input"]["truncated"] is False
    assert node_preview["snapshot_preview"]["input"]["value"]["connection_id"] == connection["id"]
    assert node_preview["snapshot_preview"]["output"]["available"] is True
    assert node_preview["snapshot_preview"]["output"]["value"]["records_imported"] == 2
    assert node_preview["snapshot_preview"]["error"]["available"] is False
    assert node_preview["full_run_request"] == {
        "scheduled_job_id": job["id"],
        "source_run_id": run["id"],
        "trigger_type": "manual_rerun",
    }
    node_rerun_response = client.post(
        f"/api/system/scheduled-job-runs/{run['id']}/trace-nodes/data_connection/rerun",
        headers=admin_headers,
    )
    assert node_rerun_response.status_code == 200
    node_rerun = node_rerun_response.json()["data"]
    assert node_rerun["source_run_id"] == run["id"]
    assert node_rerun["source_run_summary"]["id"] == run["id"]
    assert node_rerun["status"] == "succeeded"
    assert node_rerun["trigger_type"] == "manual_rerun"
    assert node_rerun["records_imported"] == 2
    assert node_rerun["plugin_invocation_log_id"] != run["plugin_invocation_log_id"]
    node_rerun_summary = node_rerun["result_summary"]
    assert node_rerun_summary["trace_node_rerun"] == {
        "completed_at": node_rerun["finished_at"],
        "downstream_strategy": "not_executed",
        "mode": "single_node_data_connection",
        "source_node_id": "data_connection",
        "source_run_id": run["id"],
        "status": "succeeded",
    }
    assert node_rerun_summary["execution_nodes"]["data_connection"]["records_imported"] == 2
    assert node_rerun_summary["execution_nodes"]["skill_processing"]["status"] == "not_run"
    assert (
        node_rerun_summary["execution_nodes"]["skill_processing"]["model_gateway_called"] is False
    )
    assert node_rerun_summary["execution_nodes"]["result_action"]["status"] == "not_run"
    assert node_rerun_summary["trace_graph"]["edges"] == [
        {"from": "data_connection", "to": "skill_processing"},
        {"from": "skill_processing", "to": "result_action"},
    ]

    result_action_preview_response = client.get(
        f"/api/system/scheduled-job-runs/{run['id']}/trace-nodes/result_action_1/rerun-preview",
        headers=admin_headers,
    )
    assert result_action_preview_response.status_code == 200
    result_action_preview = result_action_preview_response.json()["data"]
    assert result_action_preview["node_id"] == "result_action_1"
    assert result_action_preview["preflight_status"] == "ready"
    assert result_action_preview["rerun_supported"] is True
    assert result_action_preview["blocked_by"] == []
    assert result_action_preview["missing_controls"] == []
    assert result_action_preview["execution_policy"] == {
        "allowed": True,
        "blocking_count": 0,
        "message": "单节点复跑控制项已满足，可以进入执行确认。",
        "missing_control_count": 0,
        "mode": "single_node_ready",
        "requires_confirmation": True,
        "side_effect_policy": "generic_result_write_record",
    }
    assert [control["label"] for control in result_action_preview["rerun_controls"]] == [
        "动作输入快照",
        "动作输出快照",
        "写入目标幂等键",
    ]
    assert [control["status"] for control in result_action_preview["rerun_controls"]] == [
        "satisfied",
        "satisfied",
        "satisfied",
    ]
    assert result_action_preview["safe_next_action"] == "confirm_single_node_rerun"
    assert result_action_preview["snapshot_preview"]["output"]["value"]["delivery_status"] == (
        "sent"
    )

    result_action_rerun_response = client.post(
        f"/api/system/scheduled-job-runs/{run['id']}/trace-nodes/result_action_1/rerun",
        headers=admin_headers,
    )
    assert result_action_rerun_response.status_code == 200
    result_action_rerun = result_action_rerun_response.json()["data"]
    assert result_action_rerun["source_run_id"] == run["id"]
    assert result_action_rerun["source_run_summary"]["id"] == run["id"]
    assert result_action_rerun["status"] == "succeeded"
    assert result_action_rerun["trigger_type"] == "manual_rerun"
    assert result_action_rerun["records_imported"] == 1
    assert result_action_rerun["plugin_invocation_log_id"] is None
    result_action_rerun_summary = result_action_rerun["result_summary"]
    assert result_action_rerun_summary["trace_node_rerun"] == {
        "completed_at": result_action_rerun["finished_at"],
        "mode": "single_node_result_action",
        "source_node_id": "result_action_1",
        "source_run_id": run["id"],
        "status": "succeeded",
        "upstream_strategy": "source_ai_output_snapshot_reused",
    }
    assert result_action_rerun_summary["execution_nodes"]["data_connection"]["status"] == "not_run"
    assert (
        result_action_rerun_summary["execution_nodes"]["skill_processing"]["status"]
        == "reused_snapshot"
    )
    assert (
        result_action_rerun_summary["execution_nodes"]["skill_processing"]["model_gateway_called"]
        is False
    )
    assert (
        result_action_rerun_summary["execution_nodes"]["result_action"]["write_target"]
        == "email_notifications"
    )
    assert (
        result_action_rerun_summary["execution_nodes"]["result_action"]["feedback"][
            "delivery_status"
        ]
        == "sent"
    )
    result_action_records_response = client.get(
        f"/api/system/result-write-records?scheduled_job_run_id={result_action_rerun['id']}",
        headers=admin_headers,
    )
    assert result_action_records_response.status_code == 200
    result_action_records = result_action_records_response.json()["data"]
    assert result_action_records["total"] == 1
    assert result_action_records["items"][0]["write_target"] == "email_notifications"
    assert result_action_records["items"][0]["summary_fields"]["delivery_status"] == "sent"

    skill_node_preview_response = client.get(
        f"/api/system/scheduled-job-runs/{run['id']}/trace-nodes/skill_processing/rerun-preview",
        headers=admin_headers,
    )
    assert skill_node_preview_response.status_code == 200
    skill_node_preview = skill_node_preview_response.json()["data"]
    assert skill_node_preview["node_id"] == "skill_processing"
    assert skill_node_preview["preflight_status"] == "ready"
    assert skill_node_preview["rerun_supported"] is True
    assert skill_node_preview["blocked_by"] == []
    assert skill_node_preview["missing_controls"] == []
    assert skill_node_preview["execution_policy"] == {
        "allowed": True,
        "blocking_count": 0,
        "message": "单节点复跑控制项已满足，可以进入执行确认。",
        "missing_control_count": 0,
        "mode": "single_node_ready",
        "requires_confirmation": True,
        "side_effect_policy": "model_gateway_cost_and_output_drift",
    }
    assert [control["label"] for control in skill_node_preview["rerun_controls"]] == [
        "数据连接输出快照",
        "知识引用快照",
        "模型网关幂等键",
        "下游失效策略",
    ]
    assert [control["status"] for control in skill_node_preview["rerun_controls"]] == [
        "satisfied",
        "satisfied",
        "satisfied",
        "satisfied",
    ]
    assert skill_node_preview["safe_next_action"] == "confirm_single_node_rerun"
    assert skill_node_preview["snapshot_preview"]["input"]["value"]["source_row_count"] == 2
    assert skill_node_preview["snapshot_preview"]["output"]["value"]["anomaly_count"] == 1

    skill_node_rerun_response = client.post(
        f"/api/system/scheduled-job-runs/{run['id']}/trace-nodes/skill_processing/rerun",
        headers=admin_headers,
    )
    assert skill_node_rerun_response.status_code == 200
    skill_node_rerun = skill_node_rerun_response.json()["data"]
    assert skill_node_rerun["source_run_id"] == run["id"]
    assert skill_node_rerun["source_run_summary"]["id"] == run["id"]
    assert skill_node_rerun["status"] == "succeeded"
    assert skill_node_rerun["trigger_type"] == "manual_rerun"
    assert skill_node_rerun["records_imported"] == 1
    assert skill_node_rerun["plugin_invocation_log_id"] is None
    assert model_gateway_call_count == 2
    skill_node_rerun_summary = skill_node_rerun["result_summary"]
    assert skill_node_rerun_summary["trace_node_rerun"] == {
        "completed_at": skill_node_rerun["finished_at"],
        "downstream_strategy": "result_actions_not_executed",
        "mode": "single_node_skill_processing",
        "source_node_id": "skill_processing",
        "source_run_id": run["id"],
        "status": "succeeded",
        "upstream_strategy": "source_data_connection_snapshot_reused",
    }
    assert (
        skill_node_rerun_summary["execution_nodes"]["data_connection"]["status"]
        == "reused_snapshot"
    )
    assert (
        skill_node_rerun_summary["execution_nodes"]["skill_processing"]["model_gateway_called"]
        is True
    )
    assert (
        skill_node_rerun_summary["execution_nodes"]["skill_processing"]["output"]["anomaly_count"]
        == 1
    )
    assert skill_node_rerun_summary["execution_nodes"]["result_action"]["status"] == "not_run"
    skill_node_records_response = client.get(
        f"/api/system/result-write-records?scheduled_job_run_id={skill_node_rerun['id']}",
        headers=admin_headers,
    )
    assert skill_node_records_response.status_code == 200
    assert skill_node_records_response.json()["data"]["total"] == 0

    missing_node_rerun_response = client.post(
        f"/api/system/scheduled-job-runs/{run['id']}/trace-nodes/missing_node/rerun",
        headers=admin_headers,
    )
    assert missing_node_rerun_response.status_code == 404
    assert missing_node_rerun_response.json()["detail"]["code"] == "TRACE_NODE_NOT_FOUND"

    result_records_response = client.get(
        f"/api/system/result-write-records?scheduled_job_run_id={run['id']}",
        headers=admin_headers,
    )
    assert result_records_response.status_code == 200
    result_records = result_records_response.json()["data"]
    assert result_records["total"] == 1
    result_record = result_records["items"][0]
    assert result_record["write_target"] == "email_notifications"
    assert result_record["write_target_label"] == "邮件通知记录"
    assert result_record["summary_fields"]["delivery_status"] == "sent"
    assert result_record["summary_fields"]["subject"] == "发现 1 条高风险线上日志异常。"
    assert result_record["summary_fields"]["sample_records"] == ["ops@example.com"]


def test_ai_scheduled_job_requires_explicit_skill_ids_even_when_agent_has_defaults():
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "iteration_planning_default",
            "name": "默认迭代规划 Skill",
            "prompt_template": "根据真实证据生成迭代建议",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "iteration_planner_with_default_skill",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "带默认 Skill 的迭代规划 Agent",
            "status": "active",
            "system_prompt": "你是产品迭代规划助手。",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "iteration_plan_suggestion_generate",
            "model_gateway_config_id": model_gateway["id"],
            "name": "每周迭代建议",
            "schedule_type": "manual",
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "AI_SKILL_REQUIRED"
    assert "AI processing job requires skill_ids" in response.text


def test_manual_scheduled_ai_job_run_creates_snapshot_collector_run_and_suggestion():
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    product = create_product(admin_headers)
    create_feedback(admin_headers, product["id"])

    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "iteration_planning",
            "name": "迭代规划",
            "prompt_template": "根据真实证据生成迭代建议",
            "requires_human_review": True,
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "iteration_planner",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "迭代规划 Agent",
            "status": "active",
            "system_prompt": "你是产品迭代规划助手。",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "config_json": {"include_evidence": True, "planning_cycle": "weekly"},
            "enabled": True,
            "execution_mode": "ai_generated",
            "interval_seconds": 86400,
            "job_type": "iteration_plan_suggestion_generate",
            "name": "每周迭代建议",
            "product_id": product["id"],
            "schedule_type": "interval",
            "skill_ids": [skill["id"]],
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    ).json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    assert run["trigger_type"] == "manual"
    assert run["collector_run_id"].startswith("collector_run_")
    assert run["config_snapshot"]["job_type"] == "iteration_plan_suggestion_generate"
    assert run["resolved_agent_snapshot"]["id"] == agent["id"]
    assert run["resolved_skill_snapshots"][0]["id"] == skill["id"]
    assert run["tool_policy_snapshot"] == agent["tool_policy"]
    assert run["result_summary"]["suggestion_id"].startswith("suggestion_")

    suggestions = client.get(
        f"/api/planning/iteration-suggestions?product_id={product['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert suggestions["total"] == 1
    assert suggestions["items"][0]["status"] == "suggested"

    runs = client.get(
        f"/api/system/scheduled-job-runs?scheduled_job_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert runs["total"] == 1
    assert runs["items"][0]["id"] == run["id"]

    run_audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job_run.succeeded&subject_id={run['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert run_audit_events[0]["payload"] == {
        "agent_id": agent["id"],
        "collector_run_id": run["collector_run_id"],
        "execution_mode": "ai_generated",
        "job_type": "iteration_plan_suggestion_generate",
        "model_gateway_config_id": model_gateway["id"],
        "product_id": product["id"],
        "records_imported": 1,
        "scheduled_job_id": job["id"],
        "skill_ids": [skill["id"]],
        "status": "succeeded",
        "trigger_type": "manual",
    }

    invalid_trigger_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        json={"trigger_type": "rerun"},
        headers=admin_headers,
    )
    assert invalid_trigger_response.status_code == 400
    assert invalid_trigger_response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert "Unsupported scheduled job run trigger_type" in invalid_trigger_response.text

    rerun_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        json={"source_run_id": run["id"], "trigger_type": "manual_rerun"},
        headers=admin_headers,
    )
    assert rerun_response.status_code == 200
    rerun = rerun_response.json()["data"]
    assert rerun["status"] == "succeeded"
    assert rerun["source_run_id"] == run["id"]
    assert rerun["source_run_summary"] == {
        "error_code": None,
        "finished_at": run["finished_at"],
        "id": run["id"],
        "latency_ms": None,
        "records_imported": 1,
        "started_at": run["started_at"],
        "status": "succeeded",
        "trigger_type": "manual",
    }
    assert rerun["trigger_type"] == "manual_rerun"

    runs = client.get(
        f"/api/system/scheduled-job-runs?scheduled_job_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert runs["total"] == 2
    assert {item["id"] for item in runs["items"]} == {run["id"], rerun["id"]}
    listed_rerun = next(item for item in runs["items"] if item["id"] == rerun["id"])
    assert listed_rerun["source_run_summary"]["id"] == run["id"]
    assert listed_rerun["source_run_summary"]["records_imported"] == 1

    scoped_runs = client.get(
        f"/api/system/scheduled-job-runs?run_id={rerun['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert scoped_runs["total"] == 1
    assert scoped_runs["items"][0]["id"] == rerun["id"]

    rerun_audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job_run.succeeded&subject_id={rerun['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert rerun_audit_events[0]["payload"] == {
        "agent_id": agent["id"],
        "collector_run_id": rerun["collector_run_id"],
        "execution_mode": "ai_generated",
        "job_type": "iteration_plan_suggestion_generate",
        "model_gateway_config_id": model_gateway["id"],
        "product_id": product["id"],
        "records_imported": 1,
        "scheduled_job_id": job["id"],
        "skill_ids": [skill["id"]],
        "source_run_id": run["id"],
        "status": "succeeded",
        "trigger_type": "manual_rerun",
    }

    invalid_source_trigger_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        json={"source_run_id": run["id"], "trigger_type": "manual"},
        headers=admin_headers,
    )
    assert invalid_source_trigger_response.status_code == 400
    assert invalid_source_trigger_response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert (
        "source_run_id is only supported for manual_rerun" in invalid_source_trigger_response.text
    )

    missing_source_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        json={"source_run_id": "scheduled_job_run_missing", "trigger_type": "manual_rerun"},
        headers=admin_headers,
    )
    assert missing_source_response.status_code == 404
    assert missing_source_response.json()["detail"]["code"] == "NOT_FOUND"


def test_scheduled_ai_job_run_loads_packaged_skill_files_into_snapshot():
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    product = create_product(admin_headers)
    create_feedback(admin_headers, product["id"])

    skill = client.post(
        "/api/system/ai-skills/upload",
        params={"code": "packaged_iteration_planning", "name": "文件包迭代规划"},
        content=build_skill_package(),
        headers={**admin_headers, "Content-Type": "application/zip"},
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents/upload",
        params={
            "brain_app_id": "rd_brain",
            "code": "packaged_iteration_planner",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "文件包迭代规划 Agent",
        },
        content=build_agent_package(
            model_gateway_config_id=model_gateway["id"],
            skill_id=skill["id"],
        ),
        headers={**admin_headers, "Content-Type": "application/zip"},
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "config_json": {"include_evidence": True, "planning_cycle": "weekly"},
            "enabled": True,
            "execution_mode": "ai_generated",
            "interval_seconds": 86400,
            "job_type": "iteration_plan_suggestion_generate",
            "name": "每周文件包迭代建议",
            "product_id": product["id"],
            "schedule_type": "interval",
            "skill_ids": [skill["id"]],
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    ).json()["data"]

    run = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    ).json()["data"]

    agent_snapshot = run["resolved_agent_snapshot"]
    assert agent_snapshot["source_type"] == "package"
    assert agent_snapshot["package_snapshot"]["entry"] == "AGENT.md"
    assert "可落地洞察" in agent_snapshot["package_snapshot"]["entry_content"]
    assert agent_snapshot["package_snapshot"]["checksum"] == agent["package_checksum"]
    assert (
        agent_snapshot["package_snapshot"]["runtime_boundary"]["script_execution"]
        == "disabled_pending_sandbox"
    )
    assert agent_snapshot["package_snapshot"]["runtime_boundary"]["script_files"] == [
        "scripts/run.py",
    ]
    assert "不会自动执行" in agent_snapshot["package_snapshot"]["runtime_boundary"]["script_note"]
    assert run["resolved_prompt_snapshot"]["agent_system_prompt"].startswith("# 文件包反馈分析角色")
    skill_snapshot = run["resolved_skill_snapshots"][0]
    assert skill_snapshot["source_type"] == "package"
    assert skill_snapshot["package_snapshot"]["entry"] == "SKILL.md"
    assert "真实用户反馈" in skill_snapshot["package_snapshot"]["entry_content"]
    assert skill_snapshot["package_snapshot"]["checksum"] == skill["package_checksum"]
    assert (
        skill_snapshot["package_snapshot"]["runtime_boundary"]["script_execution"]
        == "disabled_pending_sandbox"
    )
    assert skill_snapshot["package_snapshot"]["runtime_boundary"]["script_files"] == [
        "scripts/run.py",
    ]
    assert "不会自动执行" in skill_snapshot["package_snapshot"]["runtime_boundary"]["script_note"]
