from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from full_chain_regression_version_dashboard import (
    validate_version_dashboard_blocker_actions,
    validate_version_dashboard_delivery_stage_overview,
    validate_version_dashboard_evidence_coverage,
    validate_version_dashboard_governance_conclusion,
    validate_version_dashboard_next_actions,
    validate_version_dashboard_release_readiness,
    validate_version_dashboard_status_impact,
    validate_version_dashboard_status_impact_projection,
)


@dataclass
class StepResult:
    name: str
    detail: str


def _slug() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"full-chain-{timestamp}"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_assistant_qa_quick_regression(
    client: Any,
    *,
    username: str,
    password: str,
) -> list[StepResult]:
    slug = _slug()
    results: list[StepResult] = []

    user = client.login(username, password).get("user", {})
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    product = client.post(
        "/api/products",
        {
            "code": f"assistant-qa-{slug}",
            "description": "自动 AI 助手问答快速回归脚本创建的产品数据。",
            "name": f"AI 助手问答快速回归产品 {slug}",
            "status": "active",
        },
    )
    version = client.post(
        f"/api/products/{product['id']}/versions",
        {
            "code": f"assistant-qa-{slug}",
            "description": "自动 AI 助手问答快速回归版本。",
            "name": f"AI 助手问答快速回归版本 {slug}",
            "status": "active",
        },
    )
    requirement = client.post(
        "/api/requirements",
        {
            "content": "AI 助手需要能回答迭代版本阻塞项、版本总览和下一步行动。",
            "priority": "P1",
            "product_id": product["id"],
            "source": "product_planning",
            "title": f"AI 助手问答快速回归需求 {slug}",
            "version_id": version["id"],
        },
    )
    approved = client.post(
        f"/api/requirements/{requirement['id']}/approve",
        {"comment": "AI 助手问答快速回归审批通过"},
    )
    _assert(
        approved.get("status") in {"approved", "planned"},
        f"Assistant QA requirement was not approved: {approved}",
    )
    task = client.post(f"/api/requirements/{requirement['id']}/generate-task")
    task_id = str(task["task_id"])
    started = client.post(
        f"/api/ai-tasks/{task_id}/start",
        {
            "execution_mode": "deterministic",
            "reason": "assistant QA quick regression prepares progress context",
        },
    )
    _assert(
        started.get("status") == "waiting_review",
        f"Assistant QA task did not enter waiting_review: {started}",
    )
    approved_review = client.post(
        f"/api/reviews/{started['review_id']}/approve",
        {"version": 1},
    )
    _assert(
        approved_review.get("task_status") == "completed",
        f"Assistant QA review did not complete task: {approved_review}",
    )

    bug = client.post(
        "/api/bugs",
        {
            "description": "AI 助手问答快速回归制造一个版本阻塞缺陷。",
            "product_id": product["id"],
            "related_task_id": task_id,
            "requirement_id": requirement["id"],
            "severity": "critical",
            "source": "manual_test",
            "title": f"AI 助手问答阻塞 Bug {slug}",
            "version_id": version["id"],
        },
    )
    version_testing = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        {
            "force": True,
            "reason": "assistant QA quick regression checks iteration governance answer",
            "target_status": "testing",
        },
    )
    _assert(
        version_testing.get("version", {}).get("status") == "testing",
        f"Assistant QA version did not advance to testing: {version_testing}",
    )

    dashboard = client.get(f"/api/product-versions/{version['id']}/dashboard")
    dashboard_blockers = dashboard.get("blockers", [])
    _assert(
        int((dashboard.get("summary") or {}).get("blockers") or 0) >= 1,
        f"Assistant QA fixture did not expose version blockers: {dashboard}",
    )
    validate_version_dashboard_blocker_actions(dashboard_blockers)
    validate_version_dashboard_next_actions(dashboard, dashboard_blockers)
    validate_version_dashboard_governance_conclusion(dashboard, dashboard_blockers)
    validate_version_dashboard_delivery_stage_overview(dashboard)
    validate_version_dashboard_evidence_coverage(dashboard, require_blockers=True)
    validate_version_dashboard_release_readiness(dashboard, require_blockers=True)
    dashboard_status_impact = validate_version_dashboard_status_impact(dashboard)

    assistant = client.post(
        "/api/assistant/chat",
        {
            "client_request_id": f"assistant-qa-regression-{slug}",
            "message": "请总结当前迭代版本阻塞项、版本总览和下一步行动",
            "product_id": product["id"],
            "references": [{"id": version["id"], "type": "product_version"}],
        },
    )
    _assert(
        assistant.get("model") == "assistant-deterministic",
        f"Assistant QA quick check should use deterministic iteration governance: {assistant}",
    )
    assistant_message = assistant.get("message") or {}
    assistant_message_id = str(assistant_message.get("id") or "")
    _assert(assistant_message_id, f"Assistant QA response missed message id: {assistant}")
    assistant_reference_keys = {
        (reference.get("type"), reference.get("id"))
        for reference in assistant_message.get("references", [])
    }
    _assert(
        ("product_version", version["id"]) in assistant_reference_keys,
        f"Assistant QA response missed product version reference: {assistant_message.get('references')}",
    )
    iteration_tools = [
        item
        for item in assistant_message.get("tool_results", [])
        if item.get("tool") == "assistant.iteration"
    ]
    _assert(iteration_tools, f"Assistant QA response missed iteration tool result: {assistant_message}")
    version_items = [
        item
        for item in iteration_tools[0].get("items", [])
        if str(item.get("id")) == version["id"]
    ]
    _assert(version_items, f"Assistant QA iteration tool missed version {version['id']}: {iteration_tools}")
    version_item = version_items[0]
    _assert(
        int(version_item.get("blocker_count") or 0)
        == int((dashboard.get("summary") or {}).get("blockers") or 0),
        f"Assistant QA blocker count drifted from version dashboard: {version_item}",
    )
    dashboard_next_action_sources = [
        str(item.get("source_type") or "") for item in dashboard.get("next_actions", [])
    ]
    assistant_next_action_sources = [
        str(item.get("source_type") or "")
        for item in version_item.get("next_actions", [])
    ]
    _assert(
        assistant_next_action_sources == dashboard_next_action_sources[:3],
        (
            "Assistant QA next_actions drifted from version dashboard: "
            f"assistant={version_item.get('next_actions')}, dashboard={dashboard.get('next_actions')}"
        ),
    )
    dashboard_stage_keys = [
        str(item.get("key") or "")
        for item in dashboard.get("delivery_stage_overview", [])
    ]
    assistant_stage_keys = [
        str(item.get("key") or "") for item in version_item.get("delivery_stage_overview", [])
    ]
    _assert(
        assistant_stage_keys == dashboard_stage_keys[:9],
        (
            "Assistant QA delivery_stage_overview drifted from version dashboard: "
            f"assistant={version_item.get('delivery_stage_overview')}, "
            f"dashboard={dashboard.get('delivery_stage_overview')}"
        ),
    )
    dashboard_conclusion = dashboard.get("governance_conclusion") or {}
    assistant_conclusion = version_item.get("governance_conclusion") or {}
    for field in ("level", "value"):
        _assert(
            assistant_conclusion.get(field) == dashboard_conclusion.get(field),
            (
                "Assistant QA governance_conclusion drifted from version dashboard: "
                f"field={field}, assistant={assistant_conclusion}, dashboard={dashboard_conclusion}"
            ),
        )
    validate_version_dashboard_status_impact_projection(
        dashboard_status_impact,
        version_item.get("status_impact"),
        label="Assistant QA",
    )
    conversation_id = assistant.get("conversation_id") or assistant.get("run", {}).get("conversation_id")
    _assert(conversation_id, f"Assistant QA response missing conversation id: {assistant}")
    conversation_messages = client.get(f"/api/assistant/conversations/{conversation_id}/messages")
    persisted_messages = conversation_messages.get("items", [])
    _assert(
        len(persisted_messages) >= 2,
        f"Assistant QA conversation history was not persisted: {conversation_messages}",
    )
    persisted_assistant = [
        item for item in persisted_messages if item.get("id") == assistant_message_id
    ]
    _assert(persisted_assistant, f"Assistant QA message not found in history: {conversation_messages}")
    persisted_iteration_tools = [
        item
        for item in persisted_assistant[0].get("tool_results", [])
        if item.get("tool") == "assistant.iteration"
    ]
    _assert(
        persisted_iteration_tools,
        f"Assistant QA history missed iteration tool result: {persisted_assistant[0]}",
    )
    persisted_version_items = [
        item
        for item in persisted_iteration_tools[0].get("items", [])
        if str(item.get("id")) == version["id"]
    ]
    _assert(
        persisted_version_items and persisted_version_items[0].get("next_actions"),
        f"Assistant QA history missed version next_actions: {persisted_iteration_tools}",
    )
    _assert(
        persisted_version_items[0].get("delivery_stage_overview"),
        f"Assistant QA history missed version delivery_stage_overview: {persisted_version_items[0]}",
    )
    validate_version_dashboard_status_impact_projection(
        dashboard_status_impact,
        persisted_version_items[0].get("status_impact"),
        label="Assistant QA history",
    )
    results.append(
        StepResult(
            "assistant_qa_quick",
            (
                f"{assistant_message_id} / version={version['id']} / "
                f"bug={bug['id']} / blockers={version_item.get('blocker_count')}"
            ),
        )
    )
    return results
