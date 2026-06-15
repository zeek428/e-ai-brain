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
            "url": "/delivery/rd-tasks?review_id=review_001",
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
        "url": "/delivery/rd-tasks?code_review_report_id=report_001",
    }


def test_assistant_tool_results_can_generate_scheduled_job_action_draft():
    store = SimpleNamespace(
        ai_agents={
            "agent_insight": {
                "code": "insight_agent",
                "id": "agent_insight",
                "name": "洞察 Agent",
                "status": "active",
            }
        },
        ai_skills={
            "skill_feedback": {
                "code": "weekly_feedback_analysis",
                "id": "skill_feedback",
                "name": "每周反馈分析",
                "status": "active",
            }
        },
        ai_tasks={},
        bugs={},
        code_review_reports={},
        human_reviews={},
        knowledge_documents={
            "knowledge_payment_runbook": {
                "doc_type": "runbook",
                "id": "knowledge_payment_runbook",
                "index_status": "text_indexed",
                "status": "active",
                "title": "支付页无响应排障知识",
            }
        },
        model_gateway_configs={
            "model_gateway_scheduled_job": {
                "default_chat_model": "scheduled-job-model",
                "id": "model_gateway_scheduled_job",
                "is_default": True,
                "name": "定时作业模型",
                "provider": "openai_compatible",
                "status": "active",
            }
        },
        plugin_actions={
            "plugin_action_maxcompute": {
                "code": "fetch_weekly_user_feedback",
                "id": "plugin_action_maxcompute",
                "name": "获取本周用户反馈数据",
                "plugin_id": "plugin_maxcompute",
                "status": "active",
            }
        },
        plugin_connections={
            "connection_maxcompute_prod": {
                "environment": "prod",
                "id": "connection_maxcompute_prod",
                "name": "生产 MaxCompute 项目",
                "plugin_id": "plugin_maxcompute",
                "status": "active",
            }
        },
        product_versions={},
        products={
            "product_ai_brain": {
                "code": "ai-brain",
                "id": "product_ai_brain",
                "name": "AI Brain",
                "status": "active",
            }
        },
        requirements={},
        scheduled_jobs={},
    )

    tool_results = assistant_tool_results(
        store,
        message="帮我创建每周从 MaxCompute 获取用户反馈并做 AI 洞察的定时作业",
        product_id="product_ai_brain",
    )

    assert tool_results[0]["tool"] == "assistant.action_draft"
    assert tool_results[0]["intent"] == "scheduled_job_draft"
    assert tool_results[0]["summary"] == {
        "draft_count": 1,
        "requires_confirmation": True,
        "target": "scheduled_jobs",
    }
    assert tool_results[0]["items"][0] == {
        "action": "create_scheduled_job",
        "draft_id": "assistant_draft_weekly_feedback_insight",
        "payload": {
            "agent_id": "agent_insight",
            "cron_expression": "0 9 * * MON",
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "user_feedback_insight_extract",
            "knowledge_document_ids": ["knowledge_payment_runbook"],
            "model_gateway_config_id": "model_gateway_scheduled_job",
            "name": "每周用户反馈洞察抽取",
            "plugin_action_id": "plugin_action_maxcompute",
            "plugin_connection_id": "connection_maxcompute_prod",
            "plugin_input_mapping": {
                "week_end": "{{last_full_week.end}}",
                "week_start": "{{last_full_week.start}}",
            },
            "product_id": "product_ai_brain",
            "schedule_type": "cron",
            "skill_ids": ["skill_feedback"],
            "source_system": "aliyun-maxcompute",
        },
        "requires_confirmation": True,
        "risk_level": "medium",
        "title": "每周用户反馈洞察抽取",
    }
    assert tool_results[0]["references"] == [
        {
            "id": "assistant_draft_weekly_feedback_insight",
            "title": "每周用户反馈洞察抽取",
            "type": "assistant_action_draft",
            "url": "/assistant?draft_id=assistant_draft_weekly_feedback_insight",
        }
    ]
    assert store.scheduled_jobs == {}


def test_assistant_tool_results_can_generate_code_inspection_job_action_draft():
    store = SimpleNamespace(
        ai_agents={},
        ai_skills={},
        ai_tasks={},
        bugs={},
        code_review_reports={},
        human_reviews={},
        knowledge_documents={},
        model_gateway_configs={},
        plugin_actions={
            "plugin_action_github_scan": {
                "code": "scan_github_code_inspection",
                "id": "plugin_action_github_scan",
                "name": "GitHub 代码巡检",
                "plugin_id": "plugin_github",
                "status": "active",
            }
        },
        plugin_connections={
            "connection_github_prod": {
                "environment": "prod",
                "id": "connection_github_prod",
                "name": "生产 GitHub 组织",
                "plugin_id": "plugin_github",
                "status": "active",
            }
        },
        product_versions={},
        products={
            "product_ai_brain": {
                "code": "ai-brain",
                "id": "product_ai_brain",
                "name": "AI Brain",
                "status": "active",
            }
        },
        requirements={},
        scheduled_jobs={},
    )

    tool_results = assistant_tool_results(
        store,
        message="帮我在 AI Brain 中创建每周代码巡检定时作业，扫描 GitHub 仓库质量安全规范问题",
        product_id="product_ai_brain",
    )

    assert tool_results[0]["tool"] == "assistant.action_draft"
    assert tool_results[0]["items"][0] == {
        "action": "create_scheduled_job",
        "draft_id": "assistant_draft_code_repository_inspection",
        "payload": {
            "cron_expression": "0 2 * * MON",
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "代码仓库质量安全规范巡检",
            "plugin_action_id": "plugin_action_github_scan",
            "plugin_connection_id": "connection_github_prod",
            "product_id": "product_ai_brain",
            "result_actions": [
                {"type": "write_code_inspection_report"},
                {
                    "severity_threshold": "critical",
                    "type": "create_bug_for_severe_findings",
                },
                {
                    "severity_threshold": "high",
                    "type": "create_task_for_severe_findings",
                },
                {"channels": ["email"], "recipients": [], "type": "send_notification"},
            ],
            "schedule_type": "cron",
            "skill_ids": [],
            "source_system": "code-inspection",
        },
        "requires_confirmation": True,
        "risk_level": "medium",
        "title": "代码仓库质量安全规范巡检",
    }
    assert tool_results[0]["references"] == [
        {
            "id": "assistant_draft_code_repository_inspection",
            "title": "代码仓库质量安全规范巡检",
            "type": "assistant_action_draft",
            "url": "/assistant?draft_id=assistant_draft_code_repository_inspection",
        }
    ]
    assert store.scheduled_jobs == {}


def test_assistant_tool_results_generate_code_inspection_setup_drafts_without_prereqs():
    store = SimpleNamespace(
        ai_agents={},
        ai_skills={},
        ai_tasks={},
        bugs={},
        code_review_reports={},
        human_reviews={},
        integration_plugins={
            "plugin_standard_github": {
                "code": "github",
                "id": "plugin_standard_github",
                "name": "GitHub",
                "protocol": "http",
                "status": "active",
            }
        },
        knowledge_documents={},
        model_gateway_configs={},
        plugin_actions={},
        plugin_connections={},
        product_versions={},
        products={
            "product_ai_brain": {
                "code": "ai-brain",
                "id": "product_ai_brain",
                "name": "AI Brain",
                "status": "active",
            }
        },
        requirements={},
        scheduled_jobs={},
    )

    tool_results = assistant_tool_results(
        store,
        message="帮我配置 GitHub 代码巡检定时作业，扫描仓库质量安全规范问题",
        product_id="product_ai_brain",
    )

    assert tool_results[0]["tool"] == "assistant.action_draft"
    assert tool_results[0]["intent"] == "code_inspection_setup_draft"
    assert tool_results[0]["summary"] == {
        "draft_count": 3,
        "requires_confirmation": True,
        "target": "code_inspection_setup",
    }
    assert [item["action"] for item in tool_results[0]["items"]] == [
        "create_plugin_connection",
        "create_plugin_action",
        "create_scheduled_job",
    ]
    connection_item, action_item, job_item = tool_results[0]["items"]
    assert connection_item["draft_id"] == "assistant_draft_github_plugin_connection"
    assert connection_item["payload"]["plugin_id"] == "plugin_standard_github"
    assert connection_item["payload"]["endpoint_url"] == "https://api.github.com"
    assert action_item["draft_id"] == "assistant_draft_github_plugin_action"
    assert action_item["payload"]["plugin_id"] == "plugin_standard_github"
    assert action_item["payload"]["connection_id"] is None
    assert action_item["payload"]["assistant_prerequisite_draft_ids"] == [
        "assistant_draft_github_plugin_connection",
    ]
    assert action_item["payload"]["request_config"]["path"] == (
        "/repos/{{owner}}/{{repo}}/code-scanning/alerts"
    )
    assert job_item["draft_id"] == "assistant_draft_code_repository_inspection"
    assert job_item["payload"]["plugin_action_id"] is None
    assert job_item["payload"]["plugin_connection_id"] is None
    assert job_item["payload"]["assistant_prerequisite_draft_ids"] == [
        "assistant_draft_github_plugin_connection",
        "assistant_draft_github_plugin_action",
    ]
    assert tool_results[0]["references"] == [
        {
            "id": "assistant_draft_github_plugin_connection",
            "title": "GitHub API 连接",
            "type": "assistant_action_draft",
            "url": "/assistant?draft_id=assistant_draft_github_plugin_connection",
        },
        {
            "id": "assistant_draft_github_plugin_action",
            "title": "GitHub 代码巡检动作",
            "type": "assistant_action_draft",
            "url": "/assistant?draft_id=assistant_draft_github_plugin_action",
        },
        {
            "id": "assistant_draft_code_repository_inspection",
            "title": "代码仓库质量安全规范巡检",
            "type": "assistant_action_draft",
            "url": "/assistant?draft_id=assistant_draft_code_repository_inspection",
        },
    ]
    assert store.plugin_connections == {}
    assert store.plugin_actions == {}
    assert store.scheduled_jobs == {}


def test_assistant_tool_results_can_generate_ai_code_inspection_job_action_draft():
    store = SimpleNamespace(
        ai_agents={
            "agent_code_inspection": {
                "code": "code_inspection_agent",
                "id": "agent_code_inspection",
                "name": "代码巡检 Agent",
                "status": "active",
            }
        },
        ai_skills={
            "skill_code_inspection": {
                "code": "code_inspection_analysis",
                "id": "skill_code_inspection",
                "name": "代码巡检分析",
                "status": "active",
            }
        },
        ai_tasks={},
        bugs={},
        code_review_reports={},
        human_reviews={},
        knowledge_documents={},
        model_gateway_configs={
            "model_gateway_code": {
                "default_chat_model": "code-inspection-model",
                "id": "model_gateway_code",
                "is_default": True,
                "name": "代码巡检模型",
                "provider": "openai_compatible",
                "status": "active",
            }
        },
        plugin_actions={
            "plugin_action_gitlab_scan": {
                "code": "scan_gitlab_code_inspection",
                "id": "plugin_action_gitlab_scan",
                "name": "GitLab 代码巡检",
                "plugin_id": "plugin_gitlab",
                "status": "active",
            }
        },
        plugin_connections={
            "connection_gitlab_prod": {
                "environment": "prod",
                "id": "connection_gitlab_prod",
                "name": "生产 GitLab",
                "plugin_id": "plugin_gitlab",
                "status": "active",
            }
        },
        product_versions={},
        products={
            "product_ai_brain": {
                "code": "ai-brain",
                "id": "product_ai_brain",
                "name": "AI Brain",
                "status": "active",
            }
        },
        requirements={},
        scheduled_jobs={},
    )

    tool_results = assistant_tool_results(
        store,
        message="帮我创建每周代码巡检定时作业，用大模型智能分析 GitLab 仓库质量安全规范问题",
        product_id="product_ai_brain",
    )

    assert tool_results[0]["tool"] == "assistant.action_draft"
    assert tool_results[0]["items"][0]["draft_id"] == (
        "assistant_draft_ai_code_repository_inspection"
    )
    payload = tool_results[0]["items"][0]["payload"]
    assert payload["agent_id"] == "agent_code_inspection"
    assert payload["execution_mode"] == "ai_generated"
    assert payload["job_type"] == "code_repository_inspection"
    assert payload["model_gateway_config_id"] == "model_gateway_code"
    assert payload["plugin_action_id"] == "plugin_action_gitlab_scan"
    assert payload["plugin_connection_id"] == "connection_gitlab_prod"
    assert payload["skill_ids"] == ["skill_code_inspection"]
    assert tool_results[0]["references"] == [
        {
            "id": "assistant_draft_ai_code_repository_inspection",
            "title": "AI 代码仓库质量安全规范巡检",
            "type": "assistant_action_draft",
            "url": "/assistant?draft_id=assistant_draft_ai_code_repository_inspection",
        }
    ]
    assert store.scheduled_jobs == {}


def test_assistant_tool_results_can_generate_plugin_action_draft():
    store = SimpleNamespace(
        ai_agents={},
        ai_skills={},
        ai_tasks={},
        bugs={},
        code_review_reports={},
        human_reviews={},
        integration_plugins={
            "plugin_standard_github": {
                "code": "github",
                "id": "plugin_standard_github",
                "name": "GitHub",
                "protocol": "http",
                "status": "active",
            }
        },
        knowledge_documents={},
        model_gateway_configs={},
        plugin_actions={},
        plugin_connections={
            "connection_github_prod": {
                "environment": "prod",
                "id": "connection_github_prod",
                "name": "生产 GitHub 组织",
                "plugin_id": "plugin_standard_github",
                "status": "active",
            }
        },
        product_versions={},
        products={},
        requirements={},
        scheduled_jobs={},
    )

    tool_results = assistant_tool_results(
        store,
        message="帮我新增一个 GitHub 代码巡检插件动作，用来读取安全告警",
        product_id=None,
    )

    assert tool_results[0]["tool"] == "assistant.action_draft"
    assert tool_results[0]["intent"] == "plugin_action_draft"
    assert tool_results[0]["summary"] == {
        "draft_count": 1,
        "requires_confirmation": True,
        "target": "plugin_actions",
    }
    assert tool_results[0]["items"][0] == {
        "action": "create_plugin_action",
        "draft_id": "assistant_draft_github_plugin_action",
        "payload": {
            "action_type": "http_request",
            "code": "scan_github_code_inspection",
            "connection_id": "connection_github_prod",
            "name": "GitHub 代码巡检",
            "plugin_id": "plugin_standard_github",
            "request_config": {
                "method": "GET",
                "path": "/repos/{{owner}}/{{repo}}/code-scanning/alerts",
                "query": {"per_page": 100, "state": "open"},
            },
            "requires_human_review": False,
            "result_mapping": {
                "branch_path": "$.branch",
                "commit_sha_path": "$.commit_sha",
                "findings_path": "$.findings",
                "repository_id_path": "$.repository_id",
                "risk_level_path": "$.risk_level",
                "summary_path": "$.summary",
                "write_target": "code_inspection_reports",
            },
            "status": "active",
            "template_code": "github_code_inspection",
            "template_version": "v1",
        },
        "requires_confirmation": True,
        "risk_level": "medium",
        "title": "GitHub 代码巡检动作",
    }
    assert tool_results[0]["references"] == [
        {
            "id": "assistant_draft_github_plugin_action",
            "title": "GitHub 代码巡检动作",
            "type": "assistant_action_draft",
            "url": "/assistant?draft_id=assistant_draft_github_plugin_action",
        }
    ]
    assert store.plugin_actions == {}


def test_assistant_tool_results_generate_email_action_draft_with_notification_mapping():
    store = SimpleNamespace(
        ai_agents={},
        ai_skills={},
        ai_tasks={},
        bugs={},
        code_review_reports={},
        human_reviews={},
        integration_plugins={
            "plugin_standard_email": {
                "code": "email",
                "id": "plugin_standard_email",
                "name": "邮箱",
                "protocol": "http",
                "status": "active",
            }
        },
        knowledge_documents={},
        model_gateway_configs={},
        plugin_actions={},
        plugin_connections={
            "connection_email_prod": {
                "environment": "prod",
                "id": "connection_email_prod",
                "name": "生产邮箱网关",
                "plugin_id": "plugin_standard_email",
                "status": "active",
            }
        },
        product_versions={},
        products={},
        requirements={},
        scheduled_jobs={},
    )

    tool_results = assistant_tool_results(
        store,
        message="帮我新增一个邮箱通知动作，用来发送定时作业结果",
        product_id=None,
    )

    assert tool_results[0]["tool"] == "assistant.action_draft"
    assert tool_results[0]["intent"] == "plugin_action_draft"
    payload = tool_results[0]["items"][0]["payload"]
    assert payload["code"] == "send_email_notification"
    assert payload["connection_id"] == "connection_email_prod"
    assert payload["plugin_id"] == "plugin_standard_email"
    assert payload["template_code"] == "email_notification"
    assert payload["template_version"] == "v1"
    assert payload["result_mapping"] == {
        "delivery_id_path": "$.message_id",
        "delivery_status_path": "$.status",
        "recipients_path": "$.recipients",
        "subject_path": "$.subject",
        "write_target": "email_notifications",
    }
    assert store.plugin_actions == {}


def test_assistant_tool_results_can_generate_plugin_connection_draft():
    store = SimpleNamespace(
        ai_agents={},
        ai_skills={},
        ai_tasks={},
        bugs={},
        code_review_reports={},
        human_reviews={},
        integration_plugins={
            "plugin_standard_github": {
                "code": "github",
                "id": "plugin_standard_github",
                "name": "GitHub",
                "protocol": "http",
                "status": "active",
            }
        },
        knowledge_documents={},
        model_gateway_configs={},
        plugin_actions={},
        plugin_connections={},
        product_versions={},
        products={},
        requirements={},
        scheduled_jobs={},
    )

    tool_results = assistant_tool_results(
        store,
        message="帮我新增一个 GitHub 插件连接，用于后续代码巡检",
        product_id=None,
    )

    assert tool_results[0]["tool"] == "assistant.action_draft"
    assert tool_results[0]["intent"] == "plugin_connection_draft"
    assert tool_results[0]["summary"] == {
        "draft_count": 1,
        "requires_confirmation": True,
        "target": "plugin_connections",
    }
    assert tool_results[0]["items"][0] == {
        "action": "create_plugin_connection",
        "draft_id": "assistant_draft_github_plugin_connection",
        "payload": {
            "auth_config": {},
            "auth_type": "bearer",
            "endpoint_url": "https://api.github.com",
            "environment": "prod",
            "max_retries": 1,
            "name": "生产 GitHub 连接",
            "plugin_id": "plugin_standard_github",
            "request_config": {
                "headers": {
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                "query": {
                    "owner": "",
                    "repo": "",
                },
            },
            "status": "active",
            "timeout_seconds": 30,
        },
        "requires_confirmation": True,
        "risk_level": "medium",
        "title": "GitHub API 连接",
    }
    assert tool_results[0]["references"] == [
        {
            "id": "assistant_draft_github_plugin_connection",
            "title": "GitHub API 连接",
            "type": "assistant_action_draft",
            "url": "/assistant?draft_id=assistant_draft_github_plugin_connection",
        }
    ]
    assert store.plugin_connections == {}


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
