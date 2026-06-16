from __future__ import annotations

from typing import Any

from app.services.assistant_references import normalize_assistant_references
from app.services.plugin_templates import (
    STANDARD_PLUGIN_IDS_BY_CODE,
    plugin_action_payload_from_template,
    plugin_action_template_for_plugin_code,
    plugin_connection_payload_from_template,
)
from app.services.scheduled_job_templates import scheduled_job_template_by_code


class AssistantDraftBuilder:
    """Build assistant-confirmed configuration drafts for task orchestration."""

    def __init__(self, context: dict[str, Any]) -> None:
        self.context = context

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
        action = _find_by_code(self.context["plugin_actions"], "receive_email_messages")
        connection = _connection_for_action(self.context["plugin_connections"], action)
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
        item = {
            "action": "create_scheduled_job",
            "draft_id": "assistant_draft_email_digest",
            "payload": payload,
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": template.get("name") or "邮件摘要收取",
        }
        return {
            "intent": "email_digest_job_draft",
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
    def _plugin_connection_draft_item(scenario: str, *, plugin_id: str) -> dict[str, Any]:
        payload = _plugin_connection_payload(scenario, plugin_id=plugin_id)
        title = {
            "email": "邮箱通知连接",
            "github": "GitHub API 连接",
            "gitlab": "GitLab API 连接",
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
        connection_id: str | None,
        plugin_id: str,
        prerequisite_draft_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = _plugin_action_payload(
            scenario,
            connection_id=connection_id,
            plugin_id=plugin_id,
        )
        title = {
            "email": "邮箱通知发送动作",
            "github": "GitHub 代码巡检动作",
            "gitlab": "GitLab 代码巡检动作",
        }[scenario]
        if payload is None:
            return {
                "action": "missing_plugin_action_template",
                "draft_id": f"assistant_draft_{scenario}_plugin_action_template_missing",
                "payload": {"plugin_code": scenario},
                "requires_confirmation": False,
                "risk_level": "low",
                "title": f"{title}模板缺失",
            }
        if prerequisite_draft_ids:
            payload["assistant_prerequisite_draft_ids"] = prerequisite_draft_ids
        return {
            "action": "create_plugin_action",
            "draft_id": f"assistant_draft_{scenario}_plugin_action",
            "payload": payload,
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": title,
        }


def _plugin_connection_payload(scenario: str, *, plugin_id: str) -> dict[str, Any]:
    return plugin_connection_payload_from_template(scenario, plugin_id=plugin_id)


def _template_payload_defaults(template: dict[str, Any]) -> dict[str, Any]:
    payload_defaults = template.get("payload_defaults")
    return payload_defaults if isinstance(payload_defaults, dict) else {}


def _plugin_action_payload(
    scenario: str,
    *,
    connection_id: str | None,
    plugin_id: str,
) -> dict[str, Any] | None:
    template = plugin_action_template_for_plugin_code(scenario)
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
