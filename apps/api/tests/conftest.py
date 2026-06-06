from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("PERSISTENCE_MODE", "memory")

import app.main as main
import app.services.model_gateway as model_gateway_service


@pytest.fixture(autouse=True)
def fake_openai_compatible_model_gateway(monkeypatch):
    original_base_url = main.settings.model_gateway_base_url
    original_api_key = main.settings.model_gateway_api_key
    original_chat_model = main.settings.model_gateway_default_chat_model
    original_embedding_model = main.settings.model_gateway_default_embedding_model
    original_code_review_executor_type = main.settings.code_review_executor_type
    original_code_review_executor_name = main.settings.code_review_executor_name
    original_code_review_executor_command = main.settings.code_review_executor_command
    original_code_review_executor_timeout = main.settings.code_review_executor_timeout_seconds
    original_code_review_executor = main.app.state.code_review_executor
    main.settings.model_gateway_base_url = "https://llm.test/v1"
    main.settings.model_gateway_api_key = "sk-test-model"
    main.settings.model_gateway_default_chat_model = "test-chat-model"
    main.settings.model_gateway_default_embedding_model = "test-embedding-model"
    main.settings.code_review_executor_type = "model_gateway"
    main.settings.code_review_executor_name = "pytest-code-review"
    main.settings.code_review_executor_command = ""
    main.settings.code_review_executor_timeout_seconds = 180
    main.app.state.code_review_executor = None

    class FakeResponse:
        def __init__(self, payload: dict):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")

    def fake_urlopen(request, timeout):
        request_body = json.loads(request.data.decode("utf-8"))
        if request.full_url.endswith("/embeddings"):
            inputs = request_body.get("input", [])
            if isinstance(inputs, str):
                inputs = [inputs]
            embeddings = []
            for index, text in enumerate(inputs):
                normalized_text = text.lower()
                vector = [0.0] * 1536
                if "retrieval marker" in normalized_text:
                    vector[0] = 1.0
                elif "new-search-token" in normalized_text:
                    vector[1] = 1.0
                elif "retry-index-token" in normalized_text:
                    vector[2] = 1.0
                elif "review" in normalized_text:
                    vector[3] = 1.0
                else:
                    vector[4] = 1.0
                embeddings.append(
                    {
                        "embedding": vector,
                        "index": index,
                    }
                )
            return FakeResponse(
                {
                    "data": embeddings,
                    "usage": {
                        "prompt_tokens": 7 * len(inputs),
                        "total_tokens": 7 * len(inputs),
                    },
                }
            )
        messages = request_body.get("messages", [])
        user_content = next(
            (message.get("content") for message in messages if message.get("role") == "user"),
            "{}",
        )
        task_payload = json.loads(user_content)
        task = task_payload.get("task") if isinstance(task_payload.get("task"), dict) else {}
        task_type = task_payload.get("task_type") or task.get("task_type")
        if task_type == "code_review":
            content = {
                "executor": {
                    "executor_name": "pytest-code-review",
                    "executor_type": "openai_compatible",
                    "retryable": False,
                },
                "findings": [
                    {
                        "category": "maintainability",
                        "confidence": 0.82,
                        "file_path": "apps/api/app/main.py",
                        "line_end": 168,
                        "line_start": 120,
                        "message": "接口编排集中，建议补充边界测试。",
                        "severity": "high",
                        "suggestion": "抽取领域服务并覆盖状态机动作。",
                    }
                ],
                "kind": "code_review_report",
                "risk_level": "medium",
                "summary": "测试模型生成的 Code Review 报告。",
            }
        elif task_type == "technical_solution":
            content = {
                "architecture": ["通过模型网关生成技术方案。"],
                "implementation_notes": ["测试环境模拟 provider 响应。"],
                "kind": "technical_solution",
                "summary": "测试模型生成的技术方案。",
            }
        elif task_type == "development_planning":
            content = {
                "code_change_suggestions": [
                    {
                        "file_path": "apps/api/app/main.py",
                        "suggestion": "补充 v1.1 任务类型创建和评审闭环。",
                    }
                ],
                "development_tasks": [
                    {
                        "estimate": "1d",
                        "owner_role": "rd_owner",
                        "title": "实现开发计划任务链路",
                    }
                ],
                "implementation_steps": ["从已确认技术方案生成开发计划。", "进入人工确认。"],
                "kind": "development_planning",
                "summary": "测试模型生成的开发计划。",
            }
        elif task_type == "automated_testing":
            content = {
                "automation_script_suggestions": [
                    {
                        "framework": "pytest",
                        "path": "apps/api/tests/test_v1_1_task_types.py",
                    }
                ],
                "bug_suggestions": [
                    {
                        "description": "自动化测试发现任务类型未接入真实创建链路。",
                        "reproduce_steps": [
                            "创建已确认技术方案任务。",
                            "创建 automated_testing 任务并启动。",
                        ],
                        "severity": "major",
                        "title": "自动化测试任务类型未落库",
                    }
                ],
                "kind": "automated_testing",
                "summary": "测试模型生成的自动化测试建议。",
                "test_cases": ["覆盖 v1.1 后续任务创建、启动、确认。"],
            }
        elif task_type == "release_readiness":
            content = {
                "checklist": [
                    {"item": "发布包构建成功", "status": "passed"},
                    {"item": "线上错误率低于阈值", "status": "warning"},
                ],
                "go_live_decision": "conditional_go",
                "kind": "release_readiness",
                "risk_assessment": [
                    {
                        "evidence": "自动化测试和线上日志仍有风险项。",
                        "risk": "上线后结算链路需重点观察。",
                        "severity": "medium",
                    }
                ],
                "risk_level": "medium",
                "rollback_plan": ["保留上一版本镜像。", "异常率超过阈值时回滚。"],
                "summary": "测试模型生成的发布评估。",
            }
        elif task_type == "post_release_analysis":
            content = {
                "anomaly_trends": [
                    {
                        "metric": "error_rate",
                        "observation": "发布后一小时错误率小幅上升。",
                        "severity": "medium",
                    }
                ],
                "bug_suggestions": [
                    {
                        "description": "上线后日志显示结算接口偶发超时。",
                        "reproduce_steps": ["发布新版本。", "连续调用结算接口。"],
                        "severity": "major",
                        "title": "上线后结算接口偶发超时",
                    }
                ],
                "health_report": {
                    "availability": "healthy",
                    "latency": "watch",
                    "overall": "degraded",
                },
                "kind": "post_release_analysis",
                "optimization_suggestions": ["优化结算接口依赖超时配置。"],
                "summary": "测试模型生成的上线后分析。",
            }
        else:
            content = {
                "acceptance_points": ["测试环境模拟 provider 响应。"],
                "kind": "product_detail_design",
                "summary": "测试模型生成的产品详细设计。",
            }
        return FakeResponse(
            {
                "choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}],
                "usage": {"completion_tokens": 22, "prompt_tokens": 11, "total_tokens": 33},
            }
        )

    monkeypatch.setattr(main, "urlopen", fake_urlopen)
    monkeypatch.setattr(model_gateway_service, "urlopen", fake_urlopen)
    try:
        yield
    finally:
        main.settings.model_gateway_base_url = original_base_url
        main.settings.model_gateway_api_key = original_api_key
        main.settings.model_gateway_default_chat_model = original_chat_model
        main.settings.model_gateway_default_embedding_model = original_embedding_model
        main.settings.code_review_executor_type = original_code_review_executor_type
        main.settings.code_review_executor_name = original_code_review_executor_name
        main.settings.code_review_executor_command = original_code_review_executor_command
        main.settings.code_review_executor_timeout_seconds = original_code_review_executor_timeout
        main.app.state.code_review_executor = original_code_review_executor
