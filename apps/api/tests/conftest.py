from __future__ import annotations

import json

import pytest

import app.main as main


@pytest.fixture(autouse=True)
def fake_openai_compatible_model_gateway(monkeypatch):
    original_base_url = main.settings.model_gateway_base_url
    original_api_key = main.settings.model_gateway_api_key
    original_chat_model = main.settings.model_gateway_default_chat_model
    original_embedding_model = main.settings.model_gateway_default_embedding_model
    main.settings.model_gateway_base_url = "https://llm.test/v1"
    main.settings.model_gateway_api_key = "sk-test-model"
    main.settings.model_gateway_default_chat_model = "test-chat-model"
    main.settings.model_gateway_default_embedding_model = "test-embedding-model"

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
        task_type = task_payload.get("task_type")
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
    try:
        yield
    finally:
        main.settings.model_gateway_base_url = original_base_url
        main.settings.model_gateway_api_key = original_api_key
        main.settings.model_gateway_default_chat_model = original_chat_model
        main.settings.model_gateway_default_embedding_model = original_embedding_model
