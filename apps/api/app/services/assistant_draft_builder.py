from __future__ import annotations

from typing import Any

from app.services.assistant_references import normalize_assistant_references
from app.services.plugin_templates import (
    STANDARD_PLUGIN_IDS_BY_CODE,
    plugin_action_payload_from_template,
    plugin_action_template_by_code,
    plugin_action_template_for_plugin_code,
    plugin_connection_payload_from_template,
)
from app.services.scheduled_job_templates import scheduled_job_template_by_code


class AssistantDraftBuilder:
    """Build assistant-confirmed configuration drafts for task orchestration."""

    def __init__(self, context: dict[str, Any]) -> None:
        self.context = context

    def rd_task_draft(
        self,
        *,
        message: str,
        references: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        requirement = _referenced_requirement(
            self.context["requirements"],
            references or [],
        ) or _single_planned_requirement(self.context["requirements"])
        product = _find_by_id(
            self.context["products"],
            str(requirement.get("product_id") or "") if requirement else "",
        )
        version = _find_by_id(
            self.context["versions"],
            str(requirement.get("version_id") or "") if requirement else "",
        )
        requirement_id = requirement.get("id") if requirement else None
        requirement_title = requirement.get("title") if requirement else None
        product_version_summary = _rd_task_product_version_summary(product, version)
        payload = {
            "input": {
                "acceptance_criteria": [],
                "owner_role": "rd_owner",
                "source": "ai_assistant",
            },
            "requirement_id": requirement_id,
            "task_type": "product_detail_design",
            "title": (
                f"产品详细设计：{requirement_title}"
                if requirement_title
                else "产品详细设计任务"
            ),
        }
        item = {
            "action": "create_rd_task",
            "draft_id": (
                f"assistant_draft_rd_task_{requirement_id}"
                if requirement_id
                else "assistant_draft_rd_task"
            ),
            "payload": payload,
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": payload["title"],
            "wizard_steps": [
                {
                    "depends_on": [],
                    "key": "data_source",
                    "status": "ready" if requirement_id and product and version else "blocked",
                    "summary": (
                        f"{requirement_title} · {product_version_summary}"
                        if requirement_title
                        else "请先 @ 一个已规划需求"
                    ),
                    "title": "数据来源",
                },
                {
                    "depends_on": ["data_source"],
                    "key": "ai_processing",
                    "status": "ready" if requirement_id and product and version else "blocked",
                    "summary": "生成产品详细设计 AI 研发任务草案",
                    "title": "AI处理",
                },
                {
                    "depends_on": ["ai_processing"],
                    "key": "result_action",
                    "status": "ready" if requirement_id and product and version else "blocked",
                    "summary": "创建 AI 研发任务并推进需求状态",
                    "title": "结果动作",
                },
                {
                    "depends_on": [],
                    "key": "schedule",
                    "status": "skipped",
                    "summary": "研发任务创建为一次性确认动作，不创建定时调度",
                    "title": "调度策略",
                },
                {
                    "depends_on": ["data_source", "ai_processing", "result_action"],
                    "key": "confirmation",
                    "status": "pending",
                    "summary": "确认后创建 AI 研发任务并更新需求状态",
                    "title": "确认执行",
                },
            ],
        }
        return {
            "intent": "rd_task_draft",
            "items": [item],
            "references": _references(
                "assistant_action_draft",
                [
                    {
                        "id": item["draft_id"],
                        "title": item["title"],
                        "url": f"/assistant?draft_id={item['draft_id']}",
                    }
                ],
            ),
            "summary": {
                "draft_count": 1,
                "requires_confirmation": True,
                "target": "ai_tasks",
            },
            "tool": "assistant.action_draft",
        }

    def plugin_connection_draft(self, *, message: str) -> dict[str, Any]:
        scenario = self._plugin_connection_scenario(message.lower())
        plugin = _find_plugin_by_code(self.context["integration_plugins"], scenario)
        plugin_id = _plugin_id_for_code(plugin, scenario)
        item = self._plugin_connection_draft_item(scenario, plugin_id=plugin_id)
        return {
            "intent": "plugin_connection_draft",
            "items": [item],
            "references": _references(
                "assistant_action_draft",
                [
                    {
                        "id": item["draft_id"],
                        "title": item["title"],
                        "url": f"/assistant?draft_id={item['draft_id']}",
                    }
                ],
            ),
            "summary": {
                "draft_count": 1,
                "requires_confirmation": True,
                "target": "plugin_connections",
            },
            "tool": "assistant.action_draft",
        }

    def plugin_action_draft(self, *, message: str) -> dict[str, Any]:
        scenario = self._plugin_action_scenario(message.lower())
        plugin = _find_plugin_by_code(self.context["integration_plugins"], scenario)
        plugin_id = _plugin_id_for_code(plugin, scenario)
        connection = _first_active(
            self.context["plugin_connections"],
            predicate=lambda item: item.get("plugin_id") == plugin_id,
        )
        item = self._plugin_action_draft_item(
            scenario,
            connection_id=connection.get("id") if connection else None,
            plugin_id=plugin_id,
        )
        return {
            "intent": "plugin_action_draft",
            "items": [item],
            "references": _references(
                "assistant_action_draft",
                [
                    {
                        "id": item["draft_id"],
                        "title": item["title"],
                        "url": f"/assistant?draft_id={item['draft_id']}",
                    }
                ],
            ),
            "summary": {
                "draft_count": 1,
                "requires_confirmation": True,
                "target": "plugin_actions",
            },
            "tool": "assistant.action_draft",
        }

    def ai_capability_draft(self, *, message: str) -> dict[str, Any]:
        scenario = self._ai_capability_scenario(message.lower())
        model_gateway = _first_active(
            self.context["model_gateway_configs"],
            predicate=lambda item: item.get("is_default") is True,
        ) or _first_active(self.context["model_gateway_configs"])
        skill_item = self._ai_skill_draft_item(scenario)
        agent_item = self._ai_agent_draft_item(
            scenario,
            default_skill_ids=[],
            model_gateway_config_id=model_gateway.get("id") if model_gateway else None,
            prerequisite_draft_ids=[skill_item["draft_id"]],
        )
        items = [skill_item, agent_item]
        return {
            "intent": "ai_capability_draft",
            "items": items,
            "references": _references(
                "assistant_action_draft",
                [
                    {
                        "id": draft_item["draft_id"],
                        "title": draft_item["title"],
                        "url": f"/assistant?draft_id={draft_item['draft_id']}",
                    }
                    for draft_item in items
                ],
            ),
            "summary": {
                "draft_count": len(items),
                "scenario": scenario,
                "target": "ai_capabilities",
            },
            "tool": "assistant.action_draft",
        }

    def scheduled_job_draft(self) -> dict[str, Any]:
        template = scheduled_job_template_by_code("weekly_feedback_insight") or {}
        defaults = _template_payload_defaults(template)
        product = _first_active(self.context["products"])
        action = _find_by_code(self.context["plugin_actions"], "fetch_weekly_user_feedback")
        connection = _connection_for_action(self.context["plugin_connections"], action)
        model_gateway = _first_active(
            self.context["model_gateway_configs"],
            predicate=lambda item: item.get("is_default") is True,
        ) or _first_active(self.context["model_gateway_configs"])
        agent = _first_active(self.context["ai_agents"])
        skill = _first_active(self.context["ai_skills"])
        knowledge_document = _first_indexed_knowledge_document(
            self.context["knowledge_documents"],
        )

        payload = {
            "agent_id": agent.get("id") if agent else None,
            "cron_expression": defaults.get("cron_expression") or "0 9 * * MON",
            "enabled": defaults.get("enabled", True),
            "execution_mode": defaults.get("execution_mode") or "ai_generated",
            "job_type": defaults.get("job_type") or "user_feedback_insight_extract",
            "knowledge_document_ids": [knowledge_document["id"]] if knowledge_document else [],
            "model_gateway_config_id": model_gateway.get("id") if model_gateway else None,
            "name": defaults.get("name") or template.get("name") or "每周用户反馈洞察抽取",
            "plugin_action_id": action.get("id") if action else None,
            "plugin_connection_id": connection.get("id") if connection else None,
            "plugin_input_mapping": defaults.get("plugin_input_mapping")
            or {
                "week_end": "{{last_full_week.end}}",
                "week_start": "{{last_full_week.start}}",
            },
            "product_id": product.get("id") if product else None,
            "schedule_type": defaults.get("schedule_type") or "cron",
            "skill_ids": [skill["id"]] if skill else [],
            "source_system": defaults.get("source_system") or "aliyun-maxcompute",
        }
        item = {
            "action": "create_scheduled_job",
            "draft_id": "assistant_draft_weekly_feedback_insight",
            "payload": payload,
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": template.get("name") or "每周用户反馈洞察抽取",
            "wizard_steps": _scheduled_job_wizard_steps(
                action=action,
                agent=agent,
                connection=connection,
                payload=payload,
                result_action_summary="写入用户反馈洞察",
                skill=skill,
            ),
        }
        return {
            "intent": "scheduled_job_draft",
            "items": [item],
            "references": _references(
                "assistant_action_draft",
                [
                    {
                        "id": item["draft_id"],
                        "title": item["title"],
                        "url": f"/assistant?draft_id={item['draft_id']}",
                    }
                ],
            ),
            "summary": {
                "draft_count": 1,
                "requires_confirmation": True,
                "target": "scheduled_jobs",
            },
            "tool": "assistant.action_draft",
        }

    def email_digest_job_draft(self) -> dict[str, Any]:
        template = scheduled_job_template_by_code("email_digest") or {}
        defaults = _template_payload_defaults(template)
        plugin = _find_plugin_by_code(self.context["integration_plugins"], "email")
        plugin_id = _plugin_id_for_code(plugin, "email")
        action = _find_by_code(self.context["plugin_actions"], "receive_email_messages")
        connection = _connection_for_action(self.context["plugin_connections"], action)
        prerequisite_items: list[dict[str, Any]] = []
        if connection is None:
            connection = _first_active(
                self.context["plugin_connections"],
                predicate=lambda item: item.get("plugin_id") == plugin_id,
            )
        if connection is None:
            prerequisite_items.append(
                self._plugin_connection_draft_item("email", plugin_id=plugin_id),
            )
        if action is None:
            action_prerequisite_draft_ids = [
                item["draft_id"]
                for item in prerequisite_items
                if item.get("action") == "create_plugin_connection"
            ]
            prerequisite_items.append(
                self._plugin_action_draft_item(
                    "email",
                    action_template_code="email_receive",
                    connection_id=connection.get("id") if connection else None,
                    draft_id="assistant_draft_email_receive_action",
                    plugin_id=plugin_id,
                    prerequisite_draft_ids=action_prerequisite_draft_ids,
                    title="邮件收取动作",
                ),
            )
        payload = {
            "cron_expression": defaults.get("cron_expression") or "0 8 * * MON-FRI",
            "enabled": defaults.get("enabled", True),
            "execution_mode": defaults.get("execution_mode") or "deterministic",
            "job_type": defaults.get("job_type") or "plugin_action_invoke",
            "name": defaults.get("name") or template.get("name") or "每日邮件摘要收取",
            "plugin_action_id": action.get("id") if action else None,
            "plugin_connection_id": connection.get("id") if connection else None,
            "plugin_input_mapping": defaults.get("plugin_input_mapping")
            or {"poll_since": "{{current_date-1}}"},
            "schedule_type": defaults.get("schedule_type") or "cron",
            "source_system": defaults.get("source_system") or "email",
        }
        if prerequisite_items:
            payload["assistant_prerequisite_draft_ids"] = [
                item["draft_id"] for item in prerequisite_items
            ]
        item = {
            "action": "create_scheduled_job",
            "draft_id": "assistant_draft_email_digest",
            "payload": payload,
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": template.get("name") or "邮件摘要收取",
            "wizard_steps": _scheduled_job_wizard_steps(
                action=action,
                agent=None,
                connection=connection,
                payload=payload,
                prerequisite_items=prerequisite_items,
                prerequisite_summary="需先确认邮箱连接和邮件收取动作",
                skill=None,
            ),
        }
        items = [*prerequisite_items, item]
        return {
            "intent": "email_digest_setup_draft"
            if prerequisite_items
            else "email_digest_job_draft",
            "items": items,
            "references": _references(
                "assistant_action_draft",
                [
                    {
                        "id": draft_item["draft_id"],
                        "title": draft_item["title"],
                        "url": f"/assistant?draft_id={draft_item['draft_id']}",
                    }
                    for draft_item in items
                ],
            ),
            "summary": {
                "draft_count": len(items),
                "requires_confirmation": True,
                "target": "email_digest_setup" if prerequisite_items else "scheduled_jobs",
            },
            "tool": "assistant.action_draft",
        }

    def online_log_anomaly_job_draft(self) -> dict[str, Any]:
        template = scheduled_job_template_by_code("online_log_anomaly_analysis") or {}
        defaults = _template_payload_defaults(template)
        product = _first_active(self.context["products"])
        plugin = _find_plugin_by_code(self.context["integration_plugins"], "observability")
        plugin_id = _plugin_id_for_code(plugin, "observability")
        action = _find_online_log_action(self.context["plugin_actions"])
        connection = _connection_for_action(self.context["plugin_connections"], action)
        prerequisite_items: list[dict[str, Any]] = []
        if connection is None:
            connection = _first_active(
                self.context["plugin_connections"],
                predicate=lambda item: item.get("plugin_id") == plugin_id,
            )
        if connection is None:
            prerequisite_items.append(
                self._plugin_connection_draft_item("observability", plugin_id=plugin_id),
            )
        if action is None:
            action_prerequisite_draft_ids = [
                item["draft_id"]
                for item in prerequisite_items
                if item.get("action") == "create_plugin_connection"
            ]
            prerequisite_items.append(
                self._plugin_action_draft_item(
                    "observability",
                    action_template_code="observability_online_log_metrics",
                    connection_id=connection.get("id") if connection else None,
                    draft_id="assistant_draft_observability_online_log_action",
                    plugin_id=plugin_id,
                    prerequisite_draft_ids=action_prerequisite_draft_ids,
                    title="线上日志查询动作",
                ),
            )
        model_gateway = _first_active(
            self.context["model_gateway_configs"],
            predicate=lambda item: item.get("is_default") is True,
        ) or _first_active(self.context["model_gateway_configs"])
        agent = _first_active(self.context["ai_agents"])
        skill = _first_active(
            self.context["ai_skills"],
            predicate=_is_online_log_skill,
        ) or _first_active(self.context["ai_skills"])
        if skill is None:
            prerequisite_items.append(self._ai_skill_draft_item("online_log_anomaly"))
        if agent is None:
            agent_prerequisite_draft_ids = [
                item["draft_id"]
                for item in prerequisite_items
                if item.get("action") == "create_ai_skill"
            ]
            prerequisite_items.append(
                self._ai_agent_draft_item(
                    "online_log_anomaly",
                    default_skill_ids=[skill["id"]] if skill else [],
                    model_gateway_config_id=(
                        model_gateway.get("id") if model_gateway else None
                    ),
                    prerequisite_draft_ids=agent_prerequisite_draft_ids,
                ),
            )
        knowledge_document = _first_indexed_knowledge_document(
            self.context["knowledge_documents"],
        )

        payload = {
            "agent_id": agent.get("id") if agent else None,
            "cron_expression": defaults.get("cron_expression") or "*/30 * * * *",
            "enabled": defaults.get("enabled", True),
            "execution_mode": defaults.get("execution_mode") or "ai_generated",
            "job_type": defaults.get("job_type") or "online_log_ai_analysis",
            "knowledge_document_ids": [knowledge_document["id"]] if knowledge_document else [],
            "model_gateway_config_id": model_gateway.get("id") if model_gateway else None,
            "name": defaults.get("name") or template.get("name") or "线上日志异常分析",
            "plugin_action_id": action.get("id") if action else None,
            "plugin_connection_id": connection.get("id") if connection else None,
            "plugin_input_mapping": defaults.get("plugin_input_mapping")
            or {
                "window_end": "{{now}}",
                "window_start": "{{current_date}}",
            },
            "product_id": product.get("id") if product else None,
            "result_actions": defaults.get("result_actions")
            or [{"channels": ["email"], "recipients": [], "type": "send_notification"}],
            "schedule_type": defaults.get("schedule_type") or "cron",
            "skill_ids": [skill["id"]] if skill else [],
            "source_system": defaults.get("source_system") or "online-log",
        }
        if prerequisite_items:
            payload["assistant_prerequisite_draft_ids"] = [
                item["draft_id"] for item in prerequisite_items
            ]
        data_source_prerequisites = [
            item["draft_id"]
            for item in prerequisite_items
            if item.get("action") in {"create_plugin_connection", "create_plugin_action"}
        ]
        ai_prerequisites = [
            item["draft_id"]
            for item in prerequisite_items
            if item.get("action") in {"create_ai_skill", "create_ai_agent"}
        ]
        item = {
            "action": "create_scheduled_job",
            "draft_id": "assistant_draft_online_log_anomaly_analysis",
            "payload": payload,
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": template.get("name") or "线上日志异常分析",
            "wizard_steps": _scheduled_job_wizard_steps(
                action=action,
                agent=agent,
                connection=connection,
                payload=payload,
                data_source_prerequisite_ids=data_source_prerequisites,
                ai_prerequisite_ids=ai_prerequisites,
                ai_prerequisite_summary=(
                    f"需先确认{_draft_titles(ai_prerequisites, prerequisite_items)}"
                    if ai_prerequisites
                    else None
                ),
                confirm_prerequisite_ids=[
                    item["draft_id"] for item in prerequisite_items
                ],
                prerequisite_items=prerequisite_items,
                prerequisite_summary="需先确认可观测平台连接和线上日志查询动作"
                if data_source_prerequisites
                else None,
                skill=skill,
            ),
        }
        items = [*prerequisite_items, item]
        return {
            "intent": "online_log_anomaly_setup_draft"
            if prerequisite_items
            else "online_log_anomaly_job_draft",
            "items": items,
            "references": _references(
                "assistant_action_draft",
                [
                    {
                        "id": draft_item["draft_id"],
                        "title": draft_item["title"],
                        "url": f"/assistant?draft_id={draft_item['draft_id']}",
                    }
                    for draft_item in items
                ],
            ),
            "summary": {
                "draft_count": len(items),
                "requires_confirmation": True,
                "target": "online_log_anomaly_setup"
                if prerequisite_items
                else "scheduled_jobs",
            },
            "tool": "assistant.action_draft",
        }

    def knowledge_base_inspection_draft(self) -> dict[str, Any]:
        documents = self.context["knowledge_documents"]
        deposits = self.context["knowledge_deposits"]
        indexed_documents = [
            document
            for document in documents
            if document.get("index_status") in {"indexed", "vector_indexed"}
        ]
        failed_documents = [
            document
            for document in documents
            if "failed" in str(document.get("index_status") or "").lower()
        ]
        pending_deposits = [
            deposit for deposit in deposits if deposit.get("status") == "pending"
        ]
        findings = [
            {
                "document_id": document.get("id"),
                "message": document.get("vector_index_error")
                or "知识文档索引失败，需要重试或检查 Embedding 网关。",
                "severity": "high",
                "title": document.get("title"),
                "type": "index_failed",
            }
            for document in failed_documents
        ]
        findings.extend(
            {
                "deposit_id": deposit.get("id"),
                "message": "知识沉淀候选仍待处理，需要人工采纳或拒绝。",
                "severity": "medium",
                "title": deposit.get("title"),
                "type": "pending_deposit",
            }
            for deposit in pending_deposits
        )
        payload = {
            "analysis_type": "knowledge_base_inspection",
            "findings": findings,
            "source_module": "knowledge",
            "summary": {
                "indexed_document_count": len(indexed_documents),
                "index_failed_document_count": len(failed_documents),
                "knowledge_document_count": len(documents),
                "pending_deposit_count": len(pending_deposits),
            },
            "title": "知识库巡检",
        }
        item = {
            "action": "create_analysis_draft",
            "draft_id": "assistant_draft_knowledge_base_inspection",
            "payload": payload,
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": "知识库巡检",
            "wizard_steps": _analysis_draft_wizard_steps(
                ai_summary="生成索引失败、权限异常、过期知识和沉淀候选巡检结论",
                data_dependencies=["知识文档索引", "知识沉淀候选"],
                data_summary=(
                    f"读取 {len(documents)} 篇知识文档和 "
                    f"{len(pending_deposits)} 条待处理知识沉淀"
                ),
            ),
        }
        return {
            "intent": "knowledge_base_inspection_draft",
            "items": [item],
            "references": _references(
                "assistant_action_draft",
                [
                    {
                        "id": item["draft_id"],
                        "title": item["title"],
                        "url": f"/assistant?draft_id={item['draft_id']}",
                    }
                ],
            ),
            "summary": {
                "draft_count": 1,
                "requires_confirmation": True,
                "target": "assistant_analysis",
            },
            "tool": "assistant.action_draft",
        }

    def release_risk_analysis_draft(self) -> dict[str, Any]:
        versions = self.context["versions"]
        requirements = self.context["requirements"]
        bugs = self.context["bugs"]
        active_release_versions = [
            version
            for version in versions
            if version.get("status") in {"active", "testing", "ready_for_release"}
        ]
        unclosed_requirements = [
            requirement
            for requirement in requirements
            if requirement.get("status")
            not in {"accepted", "cancelled", "closed", "deferred", "rejected", "released"}
        ]
        open_bugs = [
            bug
            for bug in bugs
            if bug.get("status") not in {"cancelled", "closed", "done", "resolved"}
        ]
        critical_open_bugs = [
            bug for bug in open_bugs if bug.get("severity") == "critical"
        ]
        findings = [
            {
                "bug_id": bug.get("id"),
                "message": "存在未关闭严重缺陷，发布前需要明确修复或风险接受结论。",
                "severity": "critical",
                "title": bug.get("title"),
                "type": "critical_open_bug",
            }
            for bug in critical_open_bugs
        ]
        findings.extend(
            {
                "message": "存在未关闭交付需求，发布前需要确认是否阻塞。",
                "requirement_id": requirement.get("id"),
                "severity": "medium",
                "title": requirement.get("title"),
                "type": "unclosed_requirement",
            }
            for requirement in unclosed_requirements
        )
        payload = {
            "analysis_type": "release_risk_analysis",
            "findings": findings,
            "source_module": "release_governance",
            "summary": {
                "active_release_version_count": len(active_release_versions),
                "critical_open_bug_count": len(critical_open_bugs),
                "open_bug_count": len(open_bugs),
                "unclosed_requirement_count": len(unclosed_requirements),
            },
            "title": "发布风险分析",
        }
        item = {
            "action": "create_analysis_draft",
            "draft_id": "assistant_draft_release_risk_analysis",
            "payload": payload,
            "requires_confirmation": True,
            "risk_level": "high" if critical_open_bugs else "medium",
            "title": "发布风险分析",
            "wizard_steps": _analysis_draft_wizard_steps(
                ai_summary="生成发布风险、阻塞项和需人工确认的风险结论",
                data_dependencies=["发布记录", "缺陷列表", "需求状态"],
                data_summary=(
                    f"读取 {len(active_release_versions)} 个发布版本、"
                    f"{len(unclosed_requirements)} 条未关闭需求和 {len(open_bugs)} 个未关闭缺陷"
                ),
            ),
        }
        return {
            "intent": "release_risk_analysis_draft",
            "items": [item],
            "references": _references(
                "assistant_action_draft",
                [
                    {
                        "id": item["draft_id"],
                        "title": item["title"],
                        "url": f"/assistant?draft_id={item['draft_id']}",
                    }
                ],
            ),
            "summary": {
                "draft_count": 1,
                "requires_confirmation": True,
                "target": "assistant_analysis",
            },
            "tool": "assistant.action_draft",
        }

    def code_inspection_job_draft(self, *, message: str) -> dict[str, Any]:
        template = scheduled_job_template_by_code("code_repository_inspection") or {}
        defaults = _template_payload_defaults(template)
        product = _first_active(self.context["products"])
        action = _find_code_inspection_action(self.context["plugin_actions"])
        connection = _connection_for_action(self.context["plugin_connections"], action)
        scenario = self._code_inspection_plugin_scenario(message.lower(), action=action)
        plugin_id = (
            str(action["plugin_id"])
            if action and action.get("plugin_id")
            else _plugin_id_for_code(
                _find_plugin_by_code(self.context["integration_plugins"], scenario),
                scenario,
            )
        )
        prerequisite_items: list[dict[str, Any]] = []
        if connection is None:
            connection = _first_active(
                self.context["plugin_connections"],
                predicate=lambda item: item.get("plugin_id") == plugin_id,
            )
        if connection is None:
            prerequisite_items.append(
                self._plugin_connection_draft_item(scenario, plugin_id=plugin_id),
            )
        if action is None:
            action_prerequisite_draft_ids = [
                item["draft_id"]
                for item in prerequisite_items
                if item.get("action") == "create_plugin_connection"
            ]
            prerequisite_items.append(
                self._plugin_action_draft_item(
                    scenario,
                    connection_id=connection.get("id") if connection else None,
                    plugin_id=plugin_id,
                    prerequisite_draft_ids=action_prerequisite_draft_ids,
                ),
            )
        ai_requested = _ai_processing_draft_requested(message.lower())
        model_gateway = _first_active(
            self.context["model_gateway_configs"],
            predicate=lambda item: item.get("is_default") is True,
        ) or _first_active(self.context["model_gateway_configs"])
        agent = _first_active(self.context["ai_agents"])
        skill = _first_active(
            self.context["ai_skills"],
            predicate=lambda item: "inspection" in str(item.get("code") or "").lower()
            or "巡检" in str(item.get("name") or ""),
        ) or _first_active(self.context["ai_skills"])
        if ai_requested and skill is None:
            prerequisite_items.append(self._ai_skill_draft_item("code_inspection"))
        if ai_requested and agent is None:
            agent_prerequisite_draft_ids = [
                item["draft_id"]
                for item in prerequisite_items
                if item.get("action") == "create_ai_skill"
            ]
            prerequisite_items.append(
                self._ai_agent_draft_item(
                    "code_inspection",
                    default_skill_ids=[skill["id"]] if skill else [],
                    model_gateway_config_id=(
                        model_gateway.get("id") if model_gateway else None
                    ),
                    prerequisite_draft_ids=agent_prerequisite_draft_ids,
                )
            )
        payload = {
            "agent_id": agent.get("id") if ai_requested and agent else None,
            "cron_expression": defaults.get("cron_expression") or "0 2 * * MON",
            "enabled": defaults.get("enabled", True),
            "execution_mode": "ai_generated" if ai_requested else "deterministic",
            "job_type": defaults.get("job_type") or "code_repository_inspection",
            "model_gateway_config_id": (
                model_gateway.get("id") if ai_requested and model_gateway else None
            ),
            "name": defaults.get("name") or "代码仓库质量安全规范巡检",
            "plugin_action_id": action.get("id") if action else None,
            "plugin_connection_id": connection.get("id") if connection else None,
            "product_id": product.get("id") if product else None,
            "result_actions": defaults.get("result_actions")
            or [
                {"type": "write_code_inspection_report"},
                {
                    "severity_threshold": "critical",
                    "type": "create_bug_for_severe_findings",
                },
                {"channels": ["email"], "recipients": [], "type": "send_notification"},
            ],
            "schedule_type": defaults.get("schedule_type") or "cron",
            "skill_ids": [skill["id"]] if ai_requested and skill else [],
            "source_system": defaults.get("source_system") or "code-inspection",
        }
        if prerequisite_items:
            payload["assistant_prerequisite_draft_ids"] = [
                item["draft_id"] for item in prerequisite_items
            ]
        if not ai_requested:
            payload.pop("agent_id")
            payload.pop("model_gateway_config_id")
        item = {
            "action": "create_scheduled_job",
            "draft_id": (
                "assistant_draft_ai_code_repository_inspection"
                if ai_requested
                else "assistant_draft_code_repository_inspection"
            ),
            "payload": payload,
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": (
                "AI 代码仓库质量安全规范巡检"
                if ai_requested
                else "代码仓库质量安全规范巡检"
            ),
            "wizard_steps": _code_inspection_wizard_steps(
                action=action,
                ai_requested=ai_requested,
                agent=agent,
                connection=connection,
                payload=payload,
                prerequisite_items=prerequisite_items,
                skill=skill,
            ),
        }
        items = [*prerequisite_items, item]
        intent = "code_inspection_setup_draft" if prerequisite_items else "scheduled_job_draft"
        return {
            "intent": intent,
            "items": items,
            "references": _references(
                "assistant_action_draft",
                [
                    {
                        "id": draft_item["draft_id"],
                        "title": draft_item["title"],
                        "url": f"/assistant?draft_id={draft_item['draft_id']}",
                    }
                    for draft_item in items
                ],
            ),
            "summary": {
                "draft_count": len(items),
                "requires_confirmation": True,
                "target": "code_inspection_setup" if prerequisite_items else "scheduled_jobs",
            },
            "tool": "assistant.action_draft",
        }

    def _plugin_connection_scenario(self, normalized_message: str) -> str:
        if any(keyword in normalized_message for keyword in ("邮箱", "邮件", "email")):
            return "email"
        if "gitlab" in normalized_message:
            return "gitlab"
        if "github" in normalized_message:
            return "github"
        if _find_plugin_by_code(self.context["integration_plugins"], "github"):
            return "github"
        return "gitlab"

    def _plugin_action_scenario(self, normalized_message: str) -> str:
        if any(keyword in normalized_message for keyword in ("邮箱", "邮件", "email", "通知")):
            return "email"
        if "gitlab" in normalized_message:
            return "gitlab"
        if "github" in normalized_message:
            return "github"
        if _find_plugin_by_code(self.context["integration_plugins"], "github"):
            return "github"
        return "gitlab"

    def _code_inspection_plugin_scenario(
        self,
        normalized_message: str,
        *,
        action: dict[str, Any] | None,
    ) -> str:
        if "gitlab" in normalized_message:
            return "gitlab"
        if "github" in normalized_message:
            return "github"
        action_text = (
            f"{action.get('code') or ''} {action.get('name') or ''}".lower()
            if action
            else ""
        )
        if "gitlab" in action_text:
            return "gitlab"
        if "github" in action_text:
            return "github"
        if _find_plugin_by_code(self.context["integration_plugins"], "github"):
            return "github"
        return "gitlab"

    @staticmethod
    def _ai_capability_scenario(normalized_message: str) -> str:
        if any(
            keyword in normalized_message
            for keyword in (
                "online_log",
                "online log",
                "log anomaly",
                "线上日志",
                "日志异常",
                "日志分析",
            )
        ):
            return "online_log_anomaly"
        return "code_inspection"

    @staticmethod
    def _plugin_connection_draft_item(scenario: str, *, plugin_id: str) -> dict[str, Any]:
        payload = _plugin_connection_payload(scenario, plugin_id=plugin_id)
        title = {
            "email": "邮箱通知连接",
            "github": "GitHub API 连接",
            "gitlab": "GitLab API 连接",
            "observability": "可观测平台连接",
        }[scenario]
        return {
            "action": "create_plugin_connection",
            "draft_id": f"assistant_draft_{scenario}_plugin_connection",
            "payload": payload,
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": title,
        }

    @staticmethod
    def _plugin_action_draft_item(
        scenario: str,
        *,
        action_template_code: str | None = None,
        connection_id: str | None,
        draft_id: str | None = None,
        plugin_id: str,
        prerequisite_draft_ids: list[str] | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        payload = _plugin_action_payload(
            scenario,
            action_template_code=action_template_code,
            connection_id=connection_id,
            plugin_id=plugin_id,
        )
        default_title = {
            "email": "邮箱通知发送动作",
            "github": "GitHub 代码巡检动作",
            "gitlab": "GitLab 代码巡检动作",
            "observability": "线上日志查询动作",
        }[scenario]
        if payload is None:
            return {
                "action": "missing_plugin_action_template",
                "draft_id": draft_id
                or f"assistant_draft_{scenario}_plugin_action_template_missing",
                "payload": {"plugin_code": scenario},
                "requires_confirmation": False,
                "risk_level": "low",
                "title": f"{title or default_title}模板缺失",
            }
        if prerequisite_draft_ids:
            payload["assistant_prerequisite_draft_ids"] = prerequisite_draft_ids
        return {
            "action": "create_plugin_action",
            "draft_id": draft_id or f"assistant_draft_{scenario}_plugin_action",
            "payload": payload,
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": title or default_title,
        }

    @staticmethod
    def _ai_skill_draft_item(scenario: str) -> dict[str, Any]:
        if scenario == "online_log_anomaly":
            return {
                "action": "create_ai_skill",
                "draft_id": "assistant_draft_online_log_anomaly_ai_skill",
                "payload": {
                    "code": "online_log_anomaly_detection",
                    "name": "线上日志异常检测 Skill",
                    "prompt_template": (
                        "请基于线上日志指标、错误样本和延迟分布识别异常模式，"
                        "输出影响范围、根因假设、处置建议和需追踪的证据。"
                    ),
                    "required_context": ["online_log_metrics"],
                    "risk_level": "medium",
                    "status": "active",
                    "version": "1.0.0",
                },
                "requires_confirmation": True,
                "risk_level": "medium",
                "title": "线上日志异常检测 Skill",
            }
        if scenario != "code_inspection":
            raise ValueError(f"Unsupported AI skill draft scenario: {scenario}")
        return {
            "action": "create_ai_skill",
            "draft_id": "assistant_draft_code_inspection_ai_skill",
            "payload": {
                "code": "code_inspection_analysis",
                "name": "代码巡检分析 Skill",
                "prompt_template": (
                    "请基于代码扫描结果归一化仓库、分支、提交、风险等级、摘要和"
                    "finding 列表，并保留可追踪的证据字段。"
                ),
                "required_context": ["code_repository_inspection"],
                "risk_level": "medium",
                "status": "active",
                "version": "1.0.0",
            },
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": "代码巡检分析 Skill",
        }

    @staticmethod
    def _ai_agent_draft_item(
        scenario: str,
        *,
        default_skill_ids: list[str],
        model_gateway_config_id: str | None,
        prerequisite_draft_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        if scenario == "online_log_anomaly":
            payload = {
                "brain_app_id": "rd_brain",
                "code": "online_log_anomaly_agent",
                "default_skill_ids": default_skill_ids,
                "description": "用于线上日志异常检测、影响分析和处置建议的 AI角色。",
                "model_gateway_config_id": model_gateway_config_id,
                "name": "线上日志分析 AI角色",
                "status": "active",
                "system_prompt": (
                    "你负责分析线上日志、错误率和延迟指标，输出异常归因、"
                    "修复建议和结果动作摘要。"
                ),
            }
            if prerequisite_draft_ids:
                payload["assistant_prerequisite_draft_ids"] = prerequisite_draft_ids
            return {
                "action": "create_ai_agent",
                "draft_id": "assistant_draft_online_log_anomaly_ai_agent",
                "payload": payload,
                "requires_confirmation": True,
                "risk_level": "medium",
                "title": "线上日志分析 AI角色",
            }
        if scenario != "code_inspection":
            raise ValueError(f"Unsupported AI role draft scenario: {scenario}")
        payload: dict[str, Any] = {
            "brain_app_id": "rd_brain",
            "code": "code_inspection_agent",
            "default_skill_ids": default_skill_ids,
            "description": "用于代码仓库质量、安全和规范巡检的 AI角色。",
            "model_gateway_config_id": model_gateway_config_id,
            "name": "代码巡检 AI角色",
            "status": "active",
            "system_prompt": "你负责分析代码仓库扫描结果，输出风险摘要和结构化整改建议。",
        }
        if prerequisite_draft_ids:
            payload["assistant_prerequisite_draft_ids"] = prerequisite_draft_ids
        return {
            "action": "create_ai_agent",
            "draft_id": "assistant_draft_code_inspection_ai_agent",
            "payload": payload,
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": "代码巡检 AI角色",
        }


def _plugin_connection_payload(scenario: str, *, plugin_id: str) -> dict[str, Any]:
    return plugin_connection_payload_from_template(scenario, plugin_id=plugin_id)


def _template_payload_defaults(template: dict[str, Any]) -> dict[str, Any]:
    payload_defaults = template.get("payload_defaults")
    return payload_defaults if isinstance(payload_defaults, dict) else {}


def _plugin_action_payload(
    scenario: str,
    *,
    action_template_code: str | None = None,
    connection_id: str | None,
    plugin_id: str,
) -> dict[str, Any] | None:
    template = (
        plugin_action_template_by_code(action_template_code)
        if action_template_code
        else plugin_action_template_for_plugin_code(scenario)
    )
    if template is None:
        return None
    return plugin_action_payload_from_template(
        template,
        connection_id=connection_id,
        plugin_id=plugin_id,
    )


def _first_active(
    items: list[dict[str, Any]],
    *,
    predicate: Any | None = None,
) -> dict[str, Any] | None:
    for item in items:
        if item.get("status") != "active":
            continue
        if predicate is not None and not predicate(item):
            continue
        return item
    return None


def _find_by_code(items: list[dict[str, Any]], code: str) -> dict[str, Any] | None:
    return _first_active(items, predicate=lambda item: item.get("code") == code) or next(
        (item for item in items if item.get("code") == code),
        None,
    )


def _find_by_id(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    if not item_id:
        return None
    return next((item for item in items if str(item.get("id") or "") == item_id), None)


def _referenced_requirement(
    requirements: list[dict[str, Any]],
    references: list[dict[str, Any]],
) -> dict[str, Any] | None:
    requirement_ids = [
        str(reference.get("id") or "")
        for reference in references
        if reference.get("type") == "requirement"
    ]
    for requirement_id in requirement_ids:
        if requirement := _find_by_id(requirements, requirement_id):
            return requirement
    return None


def _single_planned_requirement(
    requirements: list[dict[str, Any]],
) -> dict[str, Any] | None:
    planned = [
        requirement
        for requirement in requirements
        if str(requirement.get("status") or "") == "planned"
    ]
    return planned[0] if len(planned) == 1 else None


def _rd_task_product_version_summary(
    product: dict[str, Any] | None,
    version: dict[str, Any] | None,
) -> str:
    product_name = str(product.get("name") or product.get("code") or "").strip() if product else ""
    version_name = str(version.get("name") or version.get("code") or "").strip() if version else ""
    if product_name and version_name:
        return f"{product_name} / {version_name}"
    if product_name:
        return f"{product_name} / 请补齐版本"
    return "请先选择已规划需求"


def _find_plugin_by_code(items: list[dict[str, Any]], code: str) -> dict[str, Any] | None:
    return _first_active(items, predicate=lambda item: item.get("code") == code) or next(
        (item for item in items if item.get("code") == code),
        None,
    )


def _plugin_id_for_code(plugin: dict[str, Any] | None, code: str) -> str:
    if plugin and plugin.get("id"):
        return str(plugin["id"])
    return STANDARD_PLUGIN_IDS_BY_CODE[code]


def _find_code_inspection_action(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    for code in ("scan_github_code_inspection", "scan_gitlab_code_inspection"):
        if action := _find_by_code(items, code):
            return action
    return _first_active(items, predicate=_is_code_inspection_action) or next(
        (item for item in items if _is_code_inspection_action(item)),
        None,
    )


def _is_code_inspection_action(item: dict[str, Any]) -> bool:
    text = f"{item.get('code') or ''} {item.get('name') or ''}".lower()
    return "code_inspection" in text or "代码巡检" in text


def _find_online_log_action(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    for code in (
        "query_online_log_metrics",
        "fetch_online_log_metrics",
        "collect_online_log_metrics",
    ):
        if action := _find_by_code(items, code):
            return action
    return _first_active(items, predicate=_is_online_log_action) or next(
        (item for item in items if _is_online_log_action(item)),
        None,
    )


def _is_online_log_action(item: dict[str, Any]) -> bool:
    text = f"{item.get('code') or ''} {item.get('name') or ''}".lower()
    return any(
        keyword in text
        for keyword in ("online_log", "log_anomaly", "logs", "线上日志", "日志异常")
    )


def _is_online_log_skill(item: dict[str, Any]) -> bool:
    text = f"{item.get('code') or ''} {item.get('name') or ''}".lower()
    return any(
        keyword in text
        for keyword in ("online_log", "log_anomaly", "anomaly", "线上日志", "日志异常", "异常")
    )


def _ai_processing_draft_requested(normalized_message: str) -> bool:
    return any(
        keyword in normalized_message
        for keyword in (
            "ai 分析",
            "ai 生成",
            "ai 辅助",
            "ai分析",
            "ai生成",
            "ai辅助",
            "大模型",
            "模型",
            "智能分析",
            "智能巡检",
            "自动分析",
            "归一化",
            "llm",
        )
    )


def _connection_for_action(
    connections: list[dict[str, Any]],
    action: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not action:
        return None
    return _first_active(
        connections,
        predicate=lambda item: item.get("plugin_id") == action.get("plugin_id"),
    ) or next(
        (item for item in connections if item.get("plugin_id") == action.get("plugin_id")),
        None,
    )


def _first_indexed_knowledge_document(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in items:
        status = item.get("index_status") or item.get("status")
        if status in {"indexed", "text_indexed", "vector_indexed"}:
            return item
    return None


def _scheduled_job_wizard_steps(
    *,
    action: dict[str, Any] | None,
    agent: dict[str, Any] | None,
    ai_prerequisite_ids: list[str] | None = None,
    ai_prerequisite_summary: str | None = None,
    connection: dict[str, Any] | None,
    confirm_prerequisite_ids: list[str] | None = None,
    data_source_prerequisite_ids: list[str] | None = None,
    payload: dict[str, Any],
    prerequisite_items: list[dict[str, Any]] | None = None,
    prerequisite_summary: str | None = None,
    skill: dict[str, Any] | None,
    result_action_summary: str | None = None,
) -> list[dict[str, Any]]:
    prerequisite_ids = [
        str(item["draft_id"])
        for item in prerequisite_items or []
        if item.get("requires_confirmation") is not False
    ]
    data_source_dependency_ids = (
        data_source_prerequisite_ids
        if data_source_prerequisite_ids is not None
        else prerequisite_ids
    )
    confirm_dependency_ids = (
        confirm_prerequisite_ids
        if confirm_prerequisite_ids is not None
        else prerequisite_ids
    )
    action_name = str(action.get("name") or action.get("code")) if action else ""
    data_source_ready = action is not None and connection is not None
    if data_source_ready:
        data_source_summary = f"已选择 {action_name}" if action_name else "已选择数据来源"
    elif data_source_dependency_ids and prerequisite_summary:
        data_source_summary = prerequisite_summary
    elif action is None:
        data_source_summary = "需补齐插件动作"
    else:
        data_source_summary = "需补齐插件连接"

    execution_mode = str(payload.get("execution_mode") or "")
    if execution_mode == "deterministic":
        ai_status = "skipped"
        ai_summary = "不调用 AI"
    elif ai_prerequisite_ids:
        ai_status = "needs_prerequisite"
        ai_summary = ai_prerequisite_summary or "需补齐 AI角色和 Skill"
    elif (
        bool(payload.get("agent_id") or agent)
        and bool(payload.get("model_gateway_config_id"))
        and bool(payload.get("skill_ids") or skill)
    ):
        ai_status = "ready"
        ai_summary = "已选择 AI角色和 Skill"
    else:
        ai_status = "needs_prerequisite"
        ai_summary = "需补齐 AI角色和 Skill"

    schedule_type = str(payload.get("schedule_type") or "manual")
    cron_expression = payload.get("cron_expression")
    schedule_summary = (
        f"cron: {cron_expression}" if schedule_type == "cron" and cron_expression else schedule_type
    )
    return [
        {
            "depends_on": [] if data_source_ready else data_source_dependency_ids,
            "key": "data_source",
            "status": "ready" if data_source_ready else "needs_prerequisite",
            "summary": data_source_summary,
            "title": "数据来源",
        },
        {
            "depends_on": ai_prerequisite_ids or [],
            "key": "ai_processing",
            "status": ai_status,
            "summary": ai_summary,
            "title": "AI处理",
        },
        {
            "depends_on": [],
            "key": "result_action",
            "status": "ready",
            "summary": result_action_summary
            or _result_actions_summary(payload.get("result_actions")),
            "title": "结果动作",
        },
        {
            "depends_on": [],
            "key": "schedule",
            "status": "ready",
            "summary": schedule_summary,
            "title": "调度策略",
        },
        {
            "depends_on": confirm_dependency_ids,
            "key": "confirm",
            "status": "pending",
            "summary": "确认前置草案后创建定时作业"
            if confirm_dependency_ids
            else "确认后创建定时作业",
            "title": "确认执行",
        },
    ]


def _analysis_draft_wizard_steps(
    *,
    ai_summary: str,
    data_dependencies: list[str],
    data_summary: str,
) -> list[dict[str, Any]]:
    return [
        {
            "depends_on": data_dependencies,
            "key": "data_source",
            "status": "ready",
            "summary": data_summary,
            "title": "数据来源",
        },
        {
            "depends_on": [],
            "key": "ai_processing",
            "status": "ready",
            "summary": ai_summary,
            "title": "AI处理",
        },
        {
            "depends_on": [],
            "key": "result_action",
            "status": "ready",
            "summary": "确认后写入助手分析结果并提供追踪入口",
            "title": "结果动作",
        },
        {
            "depends_on": [],
            "key": "schedule",
            "status": "skipped",
            "summary": "一次性分析草案，不创建定时调度",
            "title": "调度策略",
        },
        {
            "depends_on": [],
            "key": "confirm",
            "status": "pending",
            "summary": "等待人工确认后归档分析结果",
            "title": "确认执行",
        },
    ]


def _code_inspection_wizard_steps(
    *,
    action: dict[str, Any] | None,
    ai_requested: bool,
    agent: dict[str, Any] | None,
    connection: dict[str, Any] | None,
    payload: dict[str, Any],
    prerequisite_items: list[dict[str, Any]],
    skill: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    prerequisite_ids = [str(item["draft_id"]) for item in prerequisite_items]
    data_source_prerequisites = [
        str(item["draft_id"])
        for item in prerequisite_items
        if item.get("action") in {"create_plugin_connection", "create_plugin_action"}
    ]
    ai_prerequisites = [
        str(item["draft_id"])
        for item in prerequisite_items
        if item.get("action") in {"create_ai_skill", "create_ai_agent"}
    ]
    action_name = str(action.get("name") or action.get("code")) if action else ""
    data_source_ready = action is not None and connection is not None
    if data_source_ready:
        data_source_summary = f"已选择 {action_name}" if action_name else "已选择代码巡检动作"
    elif data_source_prerequisites:
        data_source_summary = "需先确认插件连接和代码巡检动作"
    else:
        data_source_summary = "需补齐代码仓库数据来源"

    if not ai_requested:
        ai_status = "skipped"
        ai_summary = "不调用 AI"
    elif ai_prerequisites:
        ai_status = "needs_prerequisite"
        ai_summary = f"需先确认{_draft_titles(ai_prerequisites, prerequisite_items)}"
    elif agent is not None and skill is not None:
        ai_status = "ready"
        ai_summary = "已选择代码巡检 AI角色和 Skill"
    else:
        ai_status = "needs_prerequisite"
        ai_summary = "需补齐代码巡检 AI角色和 Skill"

    schedule_type = str(payload.get("schedule_type") or "manual")
    cron_expression = payload.get("cron_expression")
    schedule_summary = (
        f"cron: {cron_expression}" if schedule_type == "cron" and cron_expression else schedule_type
    )
    return [
        {
            "depends_on": data_source_prerequisites,
            "key": "data_source",
            "status": "ready" if data_source_ready else "needs_prerequisite",
            "summary": data_source_summary,
            "title": "数据来源",
        },
        {
            "depends_on": ai_prerequisites,
            "key": "ai_processing",
            "status": ai_status,
            "summary": ai_summary,
            "title": "AI处理",
        },
        {
            "depends_on": [],
            "key": "result_action",
            "status": "ready",
            "summary": _result_actions_summary(payload.get("result_actions")),
            "title": "结果动作",
        },
        {
            "depends_on": [],
            "key": "schedule",
            "status": "ready",
            "summary": schedule_summary,
            "title": "调度策略",
        },
        {
            "depends_on": prerequisite_ids,
            "key": "confirm",
            "status": "pending",
            "summary": "确认前置草案后创建定时作业"
            if prerequisite_ids
            else "确认后创建定时作业",
            "title": "确认执行",
        },
    ]


def _draft_titles(draft_ids: list[str], items: list[dict[str, Any]]) -> str:
    titles = [
        str(item.get("title") or item.get("draft_id"))
        for item in items
        if str(item.get("draft_id")) in draft_ids
    ]
    return "、".join(title for title in titles if title)


def _result_actions_summary(result_actions: Any) -> str:
    labels = []
    for action in result_actions or []:
        if not isinstance(action, dict):
            continue
        action_type = action.get("type")
        if action_type == "write_code_inspection_report":
            labels.append("写代码巡检报告")
        elif action_type == "create_bug_for_severe_findings":
            labels.append("严重问题建 Bug")
        elif action_type == "send_notification":
            labels.append("发送通知")
    return "、".join(labels) if labels else "记录运行结果"


def _references(entity_type: str, items: list[dict[str, Any]]) -> list[dict[str, str]]:
    return normalize_assistant_references(
        [
            {
                "id": item.get("id"),
                "title": item.get("title") or item.get("summary") or item.get("id"),
                "type": entity_type,
                "url": item.get("url"),
            }
            for item in items
        ]
    )
