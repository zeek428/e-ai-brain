from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from full_chain_regression_slug import regression_slug


@dataclass
class StepResult:
    name: str
    detail: str


def _slug() -> str:
    return regression_slug()


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expect_api_error(callable_request: Any, *, status: int, message: str) -> Any:
    try:
        callable_request()
    except Exception as exc:
        _assert(
            getattr(exc, "status", None) == status,
            f"{message}: expected HTTP {status}, got {getattr(exc, 'status', None)}",
        )
        return exc
    raise AssertionError(message)


def validate_assistant_draft_governance(
    client: Any,
    *,
    username: str,
    password: str,
) -> list[StepResult]:
    slug = _slug()
    results: list[StepResult] = []
    user = client.login(username, password).get("user", {})
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    draft = client.post(
        "/api/assistant/action-drafts",
        {
            "action": "create_scheduled_job",
            "client_draft_id": f"full_chain_assistant_draft_{slug}",
            "metadata_json": {
                "risk_reason": "full-chain regression validates action governance",
                "wizard_steps": [{"key": "basic"}, {"key": "governance"}],
            },
            "payload": {
                "enabled": False,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": f"全链路草案治理回归 {slug}",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "risk_level": "medium",
            "title": f"全链路草案治理回归 {slug}",
        },
    )
    _assert(draft.get("status") == "pending", f"Assistant draft was not pending: {draft}")
    _assert(draft.get("risk_level") == "medium", f"Assistant draft risk was not persisted: {draft}")
    governance = draft.get("governance") or {}
    impact = governance.get("impact") or {}
    permissions = governance.get("permissions") or {}
    diff = governance.get("diff") or {}
    audit = governance.get("audit") or {}
    _assert(
        permissions.get("status") == "passed",
        f"Assistant draft permission_status was not passed: {governance}",
    )
    _assert(
        impact.get("resource_type") == "scheduled_job",
        f"Assistant draft impact resource type was unexpected: {governance}",
    )
    _assert(
        int(impact.get("changed_field_count") or 0) >= 5,
        f"Assistant draft impact_changed_field_count was too small: {governance}",
    )
    _assert(
        int(diff.get("count") or 0) == int(impact.get("changed_field_count") or 0),
        f"Assistant draft diff count and impact count diverged: {governance}",
    )
    _assert(
        audit.get("latest_event_type") == "assistant_action_draft.created",
        f"Assistant draft latest_audit_event_type did not track creation: {governance}",
    )

    viewed = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/view",
        {"surface": "full_chain_regression"},
    )
    _assert(
        int((viewed.get("metadata_json") or {}).get("view_count") or 0) >= 1,
        f"Assistant draft view was not tracked: {viewed}",
    )

    modified = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/modification",
        {"modified_fields": ["name"], "user_modified": True},
    )
    modified_metadata = modified.get("metadata_json") or {}
    _assert(
        modified_metadata.get("user_modified") is True,
        f"Assistant draft modification marker was not tracked: {modified}",
    )

    patched_payload = dict(draft.get("payload") or {})
    patched_payload["name"] = f"{patched_payload['name']} patched"
    patched = client.request(
        "PATCH",
        f"/api/assistant/action-drafts/{draft['id']}",
        body={
            "modified_fields": ["name"],
            "payload": patched_payload,
            "user_modified": True,
        },
    )
    metadata = patched.get("metadata_json") or {}
    _assert(metadata.get("user_modified") is True, f"Assistant draft modification was not tracked: {patched}")
    _assert("name" in set(metadata.get("modified_fields") or []), f"Assistant draft modified field missing: {patched}")

    confirmed = client.post(f"/api/assistant/action-drafts/{draft['id']}/confirm")
    confirmed_draft = confirmed.get("draft") or {}
    run = confirmed.get("run") or {}
    _assert(
        confirmed_draft.get("status") == "confirmed",
        f"Assistant draft was not confirmed: {confirmed}",
    )
    _assert(run.get("status") == "succeeded", f"Assistant draft run failed: {confirmed}")
    _assert(
        run.get("result_type") == "scheduled_job",
        f"Assistant draft did not create scheduled job: {confirmed}",
    )
    result = run.get("result") or {}
    _assert(result.get("enabled") is False, f"Assistant draft created an enabled job unexpectedly: {result}")

    detail = client.get(f"/api/assistant/action-drafts/{draft['id']}")
    detail_governance = detail.get("governance") or {}
    detail_audit = detail_governance.get("audit") or {}
    _assert(
        detail_audit.get("latest_event_type") == "assistant_action_draft.confirmed",
        f"Assistant draft latest audit did not track confirmation: {detail_governance}",
    )
    _assert(
        "assistant_action_draft.confirmed" in set(detail_audit.get("event_types") or []),
        f"Assistant draft audit event types missed confirmation: {detail_governance}",
    )

    draft_list = client.get(
        "/api/assistant/action-drafts",
        {"page": 1, "page_size": 10, "status": "confirmed", "sort_by": "updated_at", "sort_order": "desc"},
    )
    matching_items = [
        item
        for item in draft_list.get("items", [])
        if item.get("id") == draft["id"]
    ]
    _assert(matching_items, f"Assistant draft list missed confirmed draft: {draft_list}")
    list_item = matching_items[0]
    _assert(
        list_item.get("permission_status") == "passed",
        f"Assistant draft list missed permission_status: {list_item}",
    )
    _assert(
        int(list_item.get("impact_changed_field_count") or 0) >= 5,
        f"Assistant draft list missed impact_changed_field_count: {list_item}",
    )
    _assert(
        list_item.get("latest_audit_event_type") == "assistant_action_draft.confirmed",
        f"Assistant draft list missed latest_audit_event_type: {list_item}",
    )

    audit_events = client.get(
        "/api/audit/events",
        {
            "page": 1,
            "page_size": 20,
            "subject_id": draft["id"],
            "subject_type": "assistant_action_draft",
        },
    )
    audit_event_types = {item.get("event_type") for item in audit_events.get("items", [])}
    for expected_event in [
        "assistant_action_draft.created",
        "assistant_action_draft.viewed",
        "assistant_action_draft.modified",
        "assistant_action_draft.updated",
        "assistant_action_draft.confirmed",
    ]:
        _assert(
            expected_event in audit_event_types,
            f"Assistant draft audit trail missed {expected_event}: {audit_events}",
        )

    retry_draft = client.post(
        "/api/assistant/action-drafts",
        {
            "action": "create_scheduled_job",
            "client_draft_id": f"full_chain_assistant_retry_draft_{slug}",
            "metadata_json": {
                "risk_reason": "full-chain regression validates failed draft retry",
                "wizard_steps": [{"key": "schedule"}, {"key": "governance"}],
            },
            "payload": {
                "enabled": False,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": f"全链路草案失败重试回归 {slug}",
                "schedule_type": "cron",
                "source_system": "ai-assistant",
            },
            "risk_level": "medium",
            "title": f"全链路草案失败重试回归 {slug}",
        },
    )
    retry_governance = retry_draft.get("governance") or {}
    _assert(
        (retry_governance.get("decision") or {}).get("status") == "blocked",
        f"Assistant retry draft should start with blocked precheck: {retry_governance}",
    )
    retry_error = expect_api_error(
        lambda: client.post(f"/api/assistant/action-drafts/{retry_draft['id']}/confirm"),
        status=409,
        message="Assistant retry draft confirm should fail precheck",
    )
    _assert(
        "DRAFT_PRECHECK_FAILED" in retry_error.body,
        f"Assistant retry draft failed with unexpected error body: {retry_error.body}",
    )
    failed_retry_draft = client.get(f"/api/assistant/action-drafts/{retry_draft['id']}")
    failed_metadata = failed_retry_draft.get("metadata_json") or {}
    failed_retries = (failed_retry_draft.get("governance") or {}).get("retries") or {}
    _assert(
        failed_retry_draft.get("status") == "failed",
        f"Assistant retry draft was not marked failed after precheck: {failed_retry_draft}",
    )
    _assert(
        (failed_metadata.get("failure") or {}).get("code") == "DRAFT_PRECHECK_FAILED",
        f"Assistant retry draft failure was not persisted: {failed_retry_draft}",
    )
    _assert(
        failed_retries.get("can_retry") is True,
        f"Assistant retry draft did not expose can_retry after failure: {failed_retry_draft}",
    )

    reopened = client.post(
        f"/api/assistant/action-drafts/{retry_draft['id']}/retry",
        {"reason": "补齐 Cron 表达式后重试"},
    )
    reopened_metadata = reopened.get("metadata_json") or {}
    reopened_retries = (reopened.get("governance") or {}).get("retries") or {}
    _assert(reopened.get("status") == "pending", f"Assistant retry draft was not reopened: {reopened}")
    _assert(
        reopened_metadata.get("retry_count") == 1,
        f"Assistant retry draft did not persist retry_count: {reopened}",
    )
    _assert(
        reopened_metadata.get("retry_reason") == "补齐 Cron 表达式后重试",
        f"Assistant retry draft did not persist retry_reason: {reopened}",
    )
    _assert(
        len(reopened_metadata.get("failure_history") or []) == 1,
        f"Assistant retry draft did not keep failure_history: {reopened}",
    )
    _assert(
        reopened_retries.get("failure_count") == 1
        and reopened_retries.get("last_failure_code") == "DRAFT_PRECHECK_FAILED",
        f"Assistant retry draft governance missed historical failure: {reopened}",
    )

    retry_payload = dict(retry_draft.get("payload") or {})
    retry_payload["cron_expression"] = "0 9 * * MON"
    patched_retry = client.request(
        "PATCH",
        f"/api/assistant/action-drafts/{retry_draft['id']}",
        body={
            "modified_fields": ["cron_expression"],
            "payload": retry_payload,
            "user_modified": True,
        },
    )
    patched_decision = (patched_retry.get("governance") or {}).get("decision") or {}
    _assert(
        patched_decision.get("can_confirm") is True,
        f"Assistant retry draft was not confirmable after cron fix: {patched_retry}",
    )
    retry_confirmed = client.post(f"/api/assistant/action-drafts/{retry_draft['id']}/confirm")
    retry_confirmed_draft = retry_confirmed.get("draft") or {}
    retry_run = retry_confirmed.get("run") or {}
    _assert(
        retry_confirmed_draft.get("status") == "confirmed",
        f"Assistant retry draft was not confirmed after retry: {retry_confirmed}",
    )
    _assert(retry_run.get("status") == "succeeded", f"Assistant retry draft run failed: {retry_confirmed}")

    retry_audit_events = client.get(
        "/api/audit/events",
        {
            "page": 1,
            "page_size": 20,
            "subject_id": retry_draft["id"],
            "subject_type": "assistant_action_draft",
        },
    )
    retry_audit_event_types = {item.get("event_type") for item in retry_audit_events.get("items", [])}
    for expected_event in [
        "assistant_action_draft.created",
        "assistant_action_draft.failed",
        "assistant_action_draft.retry_requested",
        "assistant_action_draft.updated",
        "assistant_action_draft.confirmed",
    ]:
        _assert(
            expected_event in retry_audit_event_types,
            f"Assistant retry draft audit trail missed {expected_event}: {retry_audit_events}",
        )

    results.append(
        StepResult(
            "assistant_draft_governance",
            (
                f"{draft['id']} / {run.get('result_type')}={run.get('result_id')} / "
                f"retry={retry_draft['id']}"
            ),
        )
    )
    return results
