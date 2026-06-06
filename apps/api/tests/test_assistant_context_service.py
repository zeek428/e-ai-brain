from __future__ import annotations

import json
from types import SimpleNamespace

from app.services.assistant_context import (
    assistant_chat_messages,
    assistant_conversation_title,
    assistant_reference_candidates,
    assistant_response_content,
    build_assistant_system_context,
    public_assistant_message,
)
from app.services.assistant_tools import assistant_tool_results


def test_assistant_system_context_is_product_scoped_and_includes_delivery_signals():
    store = SimpleNamespace(
        ai_tasks={
            "task_001": {
                "created_at": "2026-06-05T08:20:00+00:00",
                "id": "task_001",
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "status": "waiting_review",
                "task_type": "code_review",
                "title": "AI 助手代码评审",
                "version_id": "version_001",
            },
            "task_other": {
                "created_at": "2026-06-05T08:10:00+00:00",
                "id": "task_other",
                "product_id": "product_002",
                "status": "completed",
                "task_type": "technical_solution",
                "title": "其他产品任务",
            },
        },
        bugs={
            "bug_001": {
                "created_at": "2026-06-05T09:00:00+00:00",
                "id": "bug_001",
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "severity": "critical",
                "status": "open",
                "title": "助手阻塞缺陷",
                "updated_at": "2026-06-05T09:05:00+00:00",
                "version_id": "version_001",
            },
            "bug_other": {
                "id": "bug_other",
                "product_id": "product_002",
                "severity": "major",
                "status": "open",
                "title": "其他产品缺陷",
            },
        },
        code_review_reports={
            "report_001": {
                "archived_at": "2026-06-05T09:10:00+00:00",
                "findings": [{"severity": "low"}],
                "id": "report_001",
                "risk_level": "low",
                "status": "confirmed",
                "summary": "助手 Review 低风险",
                "task_id": "task_001",
            }
        },
        human_reviews={
            "review_001": {
                "ai_task_id": "task_001",
                "created_at": "2026-06-05T09:01:00+00:00",
                "id": "review_001",
                "review_type": "code_review",
                "status": "pending",
            }
        },
        knowledge_deposits={
            "deposit_001": {
                "ai_task_id": "task_001",
                "created_at": "2026-06-05T09:02:00+00:00",
                "id": "deposit_001",
                "status": "pending",
                "title": "助手知识沉淀",
            }
        },
        product_git_repositories={
            "repo_001": {
                "default_branch": "main",
                "git_provider": "github",
                "id": "repo_001",
                "name": "AI Brain",
                "product_id": "product_001",
                "status": "active",
            }
        },
        product_versions={
            "version_001": {
                "code": "2026-06",
                "created_at": "2026-06-01T00:00:00+00:00",
                "id": "version_001",
                "name": "AI 助手迭代",
                "product_id": "product_001",
                "status": "testing",
            }
        },
        products={
            "product_001": {
                "code": "AI-BRAIN",
                "id": "product_001",
                "name": "Enterprise AI Brain",
                "status": "active",
            },
            "product_002": {
                "code": "OTHER",
                "id": "product_002",
                "name": "Other",
                "status": "active",
            },
        },
        requirements={
            "requirement_001": {
                "created_at": "2026-06-05T08:00:00+00:00",
                "id": "requirement_001",
                "priority": "P0",
                "product_id": "product_001",
                "status": "testing",
                "title": "AI 助手工具化查询",
                "version_id": "version_001",
            },
            "requirement_other": {
                "id": "requirement_other",
                "product_id": "product_002",
                "status": "approved",
                "title": "其他产品需求",
            },
        },
    )

    context = build_assistant_system_context(
        store,
        default_gateway={
            "api_key": "sk-test",
            "default_chat_model": "gpt-test",
            "provider": "openai_compatible",
        },
        model_gateway_status="not_configured",
        product_id="product_001",
    )

    assert context["products"] == [
        {
            "code": "AI-BRAIN",
            "id": "product_001",
            "name": "Enterprise AI Brain",
            "status": "active",
        }
    ]
    assert context["requirements_total"] == 1
    assert context["ai_tasks_total"] == 1
    assert context["bug_distribution"]["high_severity_open"] == 1
    assert context["blocked_requirements"][0]["id"] == "requirement_001"
    assert context["iteration_progress"][0]["pending_review_count"] == 1
    assert context["pending_reviews"][0]["task_title"] == "AI 助手代码评审"
    assert context["recent_code_review_reports"][0]["summary"] == "助手 Review 低风险"
    assert context["recent_knowledge_deposits"][0]["title"] == "助手知识沉淀"
    assert context["git_repositories"][0]["provider"] == "github"
    assert context["model_gateway"]["chat_model"] == "gpt-test"

    references = assistant_reference_candidates(
        store,
        message="当前有哪些阻塞需求和待确认 Review？",
        product_id="product_001",
    )
    assert references[:3] == [
        {
            "id": "requirement_001",
            "title": "AI 助手工具化查询",
            "type": "requirement",
            "url": "/delivery/requirements?requirement_id=requirement_001",
        },
        {
            "id": "bug_001",
            "title": "助手阻塞缺陷",
            "type": "bug",
            "url": "/delivery/bugs?bug_id=bug_001",
        },
        {
            "id": "review_001",
            "title": "review_001",
            "type": "human_review",
            "url": "/tasks/management?review_id=review_001",
        },
    ]

    tool_results = assistant_tool_results(
        store,
        message="当前迭代进展、待确认 Review 和代码评审结论是什么？",
        product_id="product_001",
    )
    assert [item["tool"] for item in tool_results] == [
        "assistant.delivery_progress",
        "assistant.pending_reviews",
        "assistant.code_review",
        "assistant.iteration",
    ]
    assert tool_results[0]["summary"]["requirements_total"] == 1
    assert tool_results[1]["items"][0]["id"] == "review_001"
    assert tool_results[2]["references"][0] == {
        "id": "report_001",
        "title": "助手 Review 低风险",
        "type": "code_review_report",
        "url": "/tasks/management?code_review_report_id=report_001",
    }


def test_assistant_message_helpers_normalize_payloads_and_public_projection():
    system_context = {"requirements_total": 1}
    messages = assistant_chat_messages(
        context={"view": "dashboard"},
        conversation_id="conversation_001",
        message="当前进展？",
        product_id="product_001",
        system_context=system_context,
    )
    user_payload = json.loads(messages[1]["content"])

    assert messages[0]["role"] == "system"
    assert user_payload["system_context"] == system_context
    assistant_payload = '{"answer":" 好的 ","suggestions":["A","","B","C","D","E"]}'
    assert assistant_response_content(assistant_payload) == {
        "answer": "好的",
        "references": [],
        "suggestions": ["A", "B", "C", "D"],
    }
    assert assistant_response_content("纯文本回答") == {
        "answer": "纯文本回答",
        "references": [],
        "suggestions": [],
    }
    assert assistant_conversation_title("x" * 70) == f"{'x' * 57}..."
    assert public_assistant_message(
        {
            "content": "回答",
            "conversation_id": "conversation_001",
            "created_at": "2026-06-05T09:00:00+00:00",
            "id": "assistant_message_001",
            "model": "gpt-test",
            "metadata_json": {
                "references": [
                    {
                        "id": "requirement_001",
                        "title": "AI 助手工具化查询",
                        "type": "requirement",
                        "url": "/delivery/requirements?requirement_id=requirement_001",
                    }
                ],
                "tool_results": [
                    {
                        "intent": "delivery_progress",
                        "items": [],
                        "summary": {"requirements_total": 1},
                        "tool": "assistant.delivery_progress",
                    }
                ],
            },
            "role": "assistant",
            "suggestions": ["查看需求"],
        }
    ) == {
        "content": "回答",
        "conversation_id": "conversation_001",
        "created_at": "2026-06-05T09:00:00+00:00",
        "id": "assistant_message_001",
        "model": "gpt-test",
        "references": [
            {
                "id": "requirement_001",
                "title": "AI 助手工具化查询",
                "type": "requirement",
                "url": "/delivery/requirements?requirement_id=requirement_001",
            }
        ],
        "role": "assistant",
        "suggestions": ["查看需求"],
        "tool_results": [
            {
                "intent": "delivery_progress",
                "items": [],
                "summary": {"requirements_total": 1},
                "tool": "assistant.delivery_progress",
            }
        ],
    }
