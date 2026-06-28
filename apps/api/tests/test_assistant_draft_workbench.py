from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services.assistant_action_drafts import list_assistant_action_drafts_response

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _draft(
    draft_id: str,
    *,
    action: str = "create_scheduled_job",
    created_by: str = "user_admin",
    metadata_json: dict | None = None,
    payload: dict | None = None,
    result_run_id: str | None = None,
    risk_level: str = "medium",
    status: str = "pending",
    title: str = "草案",
    updated_at: str = "2026-06-20T10:00:00+00:00",
) -> dict:
    default_payload = {
        "execution_mode": "deterministic",
        "job_type": "dashboard_snapshot_refresh",
        "name": title,
        "schedule_type": "manual",
    }
    return {
        "action": action,
        "created_at": updated_at,
        "created_by": created_by,
        "id": draft_id,
        "metadata_json": metadata_json or {},
        "payload": payload or default_payload,
        "result_run_id": result_run_id,
        "risk_level": risk_level,
        "status": status,
        "title": title,
        "updated_at": updated_at,
    }


def _empty_draft_summary(total: int = 0) -> dict:
    return {
        "adoption_rate": 0.0,
        "draft_total": total,
        "resolution_rate": 0.0,
        "status_counts": {
            "cancelled": 0,
            "confirmed": 0,
            "expired": 0,
            "failed": 0,
            "pending": total,
        },
        "user_modified_count": 0,
        "user_modified_rate": 0.0,
        "validation_counts": {
            "blocked": 0,
            "passed": total,
            "unknown": 0,
            "warning": 0,
        },
    }


class FakeAssistantDraftPagingRepository:
    def __init__(self) -> None:
        self.page_calls: list[dict] = []

    def list_assistant_action_draft_workbench_page(self, **kwargs) -> dict:
        self.page_calls.append(kwargs)
        return {
            "items": [
                _draft(
                    "assistant_action_draft_repo_page",
                    action="create_analysis_draft",
                    payload={"analysis_type": "diagnosis", "title": "仓储分页草案"},
                    title="仓储分页草案",
                )
            ],
            "summary": _empty_draft_summary(total=7),
            "total": 7,
        }

    def list_assistant_action_drafts(self, **_kwargs) -> list[dict]:
        raise AssertionError("草案任务台列表应使用分页 read model，不能退回全量草案读取")


def test_assistant_action_draft_workbench_uses_repository_pagination_when_available():
    repository = FakeAssistantDraftPagingRepository()
    current_store = SimpleNamespace(
        ai_agents={},
        ai_skills={},
        assistant_action_drafts={},
        assistant_action_runs={},
        audit_events=[],
        model_gateway_configs={},
        plugin_actions={},
        plugin_connections={},
        product_versions={},
        products={},
        repository=repository,
        scheduled_job_runs={},
        scheduled_jobs={},
        new_id=lambda prefix: f"{prefix}_001",
    )

    response = list_assistant_action_drafts_response(
        action="create_analysis_draft",
        created_from="2026-06-01T00:00:00+00:00",
        created_to="2026-06-30T23:59:59+00:00",
        current_store=current_store,
        keyword="仓储",
        page=2,
        page_size=1,
        sort_by="updated_at",
        sort_order="desc",
        started_at=None,
        status="pending",
        trace_id="trace_draft_repo_page",
        user={"id": "user_admin", "permissions": ["system.admin"], "roles": ["admin"]},
        validation_status="passed",
    )

    assert response["trace_id"] == "trace_draft_repo_page"
    payload = response["data"]
    assert payload["total"] == 7
    assert payload["page"] == 2
    assert payload["page_size"] == 1
    assert payload["summary"]["draft_total"] == 7
    assert payload["items"][0]["id"] == "assistant_action_draft_repo_page"
    assert repository.page_calls == [
        {
            "action": "create_analysis_draft",
            "created_from": "2026-06-01T00:00:00+00:00",
            "created_to": "2026-06-30T23:59:59+00:00",
            "keyword": "仓储",
            "limit": 1,
            "offset": 1,
            "sort_by": "updated_at",
            "sort_order": "desc",
            "status": "pending",
            "user_id": "user_admin",
            "validation_status": "passed",
        }
    ]


def test_assistant_action_draft_workbench_lists_current_user_drafts_with_summary():
    app.state.store.reset()
    app.state.store.assistant_action_drafts = {
        "assistant_action_draft_pending": _draft(
            "assistant_action_draft_pending",
            metadata_json={
                "modified_fields": ["cron_expression"],
                "user_modified": True,
                "view_count": 3,
                "wizard_steps": [{"key": "source"}],
            },
            title="待确认定时作业草案",
        ),
        "assistant_action_draft_confirmed": _draft(
            "assistant_action_draft_confirmed",
            result_run_id="assistant_action_run_confirmed",
            status="confirmed",
            title="已采纳插件动作草案",
            updated_at="2026-06-20T11:00:00+00:00",
        ),
        "assistant_action_draft_blocked": _draft(
            "assistant_action_draft_blocked",
            action="create_plugin_connection",
            payload={"name": "缺少插件和 Endpoint"},
            risk_level="high",
            title="阻塞草案",
            updated_at="2026-06-20T12:00:00+00:00",
        ),
        "assistant_action_draft_other_user": _draft(
            "assistant_action_draft_other_user",
            created_by="user_reviewer",
            title="其他用户草案",
            updated_at="2026-06-20T13:00:00+00:00",
        ),
    }
    app.state.store.audit_events = [
        {
            "actor_id": "user_admin",
            "created_at": "2026-06-20T10:00:00+00:00",
            "event_type": "assistant_action_draft.created",
            "id": "audit_assistant_action_draft_pending_created",
            "payload": {"action": "create_scheduled_job"},
            "sequence": 1,
            "subject_id": "assistant_action_draft_pending",
            "subject_type": "assistant_action_draft",
        }
    ]
    app.state.store.assistant_action_runs = {
        "assistant_action_run_confirmed": {
            "action": "create_scheduled_job",
            "created_at": "2026-06-20T11:00:00+00:00",
            "draft_id": "assistant_action_draft_confirmed",
            "executed_by": "user_admin",
            "finished_at": "2026-06-20T11:00:00+00:00",
            "id": "assistant_action_run_confirmed",
            "result": {"id": "plugin_action_001"},
            "result_id": "plugin_action_001",
            "result_type": "plugin_action",
            "started_at": "2026-06-20T11:00:00+00:00",
            "status": "succeeded",
            "updated_at": "2026-06-20T11:00:00+00:00",
        }
    }

    response = client.get(
        "/api/assistant/action-drafts?page=1&page_size=10&sort_by=updated_at&sort_order=desc",
        headers=auth_headers(),
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["total"] == 3
    assert [item["id"] for item in payload["items"]] == [
        "assistant_action_draft_blocked",
        "assistant_action_draft_confirmed",
        "assistant_action_draft_pending",
    ]
    assert payload["summary"]["draft_total"] == 3
    assert payload["summary"]["status_counts"]["pending"] == 2
    assert payload["summary"]["status_counts"]["confirmed"] == 1
    assert payload["summary"]["validation_counts"]["blocked"] == 1
    assert payload["summary"]["adoption_rate"] == 0.3333
    assert payload["summary"]["user_modified_rate"] == 0.3333
    pending = next(
        item for item in payload["items"] if item["id"] == "assistant_action_draft_pending"
    )
    assert pending["modified_field_count"] == 1
    assert pending["audit_event_count"] == 1
    assert pending["failure_count"] == 0
    assert pending["impact_changed_field_count"] == 5
    assert pending["impact_operation"] == "create"
    assert pending["impact_resource_type"] == "scheduled_job"
    assert pending["latest_audit_event_type"] == "assistant_action_draft.created"
    assert pending["view_count"] == 3
    assert pending["permission_status"] == "passed"
    assert pending["retry_count"] == 0
    assert pending["wizard_step_count"] == 1
    assert pending["source_link"] == "/assistant?draft_id=assistant_action_draft_pending"
    confirmed = next(
        item for item in payload["items"] if item["id"] == "assistant_action_draft_confirmed"
    )
    assert confirmed["result_status"] == "succeeded"
    assert confirmed["result_type"] == "plugin_action"
    assert confirmed["result_id"] == "plugin_action_001"


def test_assistant_action_draft_workbench_filters_and_scopes_to_current_user():
    app.state.store.reset()
    app.state.store.assistant_action_drafts = {
        "assistant_action_draft_admin_pending": _draft(
            "assistant_action_draft_admin_pending",
            status="pending",
            title="管理员待确认草案",
        ),
        "assistant_action_draft_reviewer_confirmed": _draft(
            "assistant_action_draft_reviewer_confirmed",
            created_by="user_reviewer",
            status="confirmed",
            title="评审已采纳草案",
        ),
    }

    admin_response = client.get(
        "/api/assistant/action-drafts?status=confirmed",
        headers=auth_headers(),
    )
    reviewer_response = client.get(
        "/api/assistant/action-drafts?status=confirmed",
        headers=auth_headers("reviewer@example.com", "reviewer123"),
    )

    assert admin_response.status_code == 200, admin_response.text
    assert admin_response.json()["data"]["total"] == 0
    assert reviewer_response.status_code == 200, reviewer_response.text
    reviewer_payload = reviewer_response.json()["data"]
    assert reviewer_payload["total"] == 1
    assert reviewer_payload["items"][0]["id"] == "assistant_action_draft_reviewer_confirmed"


def test_assistant_action_draft_workbench_refreshes_expired_drafts():
    app.state.store.reset()
    app.state.store.assistant_action_drafts = {
        "assistant_action_draft_expired": {
            **_draft("assistant_action_draft_expired", title="过期草案"),
            "expires_at": "2026-01-01T00:00:00+00:00",
        }
    }

    response = client.get(
        "/api/assistant/action-drafts?status=expired",
        headers=auth_headers(),
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["total"] == 1
    assert payload["items"][0]["status"] == "expired"
    assert app.state.store.assistant_action_drafts["assistant_action_draft_expired"]["status"] == (
        "expired"
    )


def test_assistant_action_draft_retry_reopens_failed_draft_with_audit():
    app.state.store.reset()
    app.state.store.assistant_action_drafts = {
        "assistant_action_draft_failed": _draft(
            "assistant_action_draft_failed",
            metadata_json={
                "failed_at": "2026-06-20T12:00:00+00:00",
                "failed_by": "user_admin",
                "failure": {
                    "code": "DRAFT_CONFIRM_FAILED",
                    "message": "模拟确认失败",
                },
            },
            result_run_id="assistant_action_run_failed",
            status="failed",
            title="失败草案",
        )
    }
    app.state.store.assistant_action_runs = {
        "assistant_action_run_failed": {
            "action": "create_scheduled_job",
            "created_at": "2026-06-20T12:00:00+00:00",
            "draft_id": "assistant_action_draft_failed",
            "error_code": "DRAFT_CONFIRM_FAILED",
            "error_message": "模拟确认失败",
            "executed_by": "user_admin",
            "finished_at": "2026-06-20T12:00:00+00:00",
            "id": "assistant_action_run_failed",
            "result": None,
            "result_id": None,
            "result_type": None,
            "started_at": "2026-06-20T12:00:00+00:00",
            "status": "failed",
            "updated_at": "2026-06-20T12:00:00+00:00",
        }
    }

    response = client.post(
        "/api/assistant/action-drafts/assistant_action_draft_failed/retry",
        headers=auth_headers(),
        json={"reason": "修正字段后重试"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["status"] == "pending"
    assert payload.get("result_run_id") is None
    metadata_json = payload["metadata_json"]
    assert metadata_json["retry_count"] == 1
    assert metadata_json["retry_reason"] == "修正字段后重试"
    assert metadata_json["retry_requested_by"] == "user_admin"
    assert "failure" not in metadata_json
    assert metadata_json["failure_history"] == [
        {
            "failed_at": "2026-06-20T12:00:00+00:00",
            "failed_by": "user_admin",
            "failure": {
                "code": "DRAFT_CONFIRM_FAILED",
                "message": "模拟确认失败",
            },
            "run_id": "assistant_action_run_failed",
        }
    ]
    assert payload["governance"]["retries"] == {
        "can_retry": False,
        "failure_count": 1,
        "last_failure_code": "DRAFT_CONFIRM_FAILED",
        "last_failure_message": "模拟确认失败",
        "retry_count": 1,
        "retry_reason": "修正字段后重试",
    }
    assert payload["governance"]["audit"]["event_count"] == 1
    assert payload["governance"]["audit"]["latest_event_type"] == (
        "assistant_action_draft.retry_requested"
    )
    stored_draft = app.state.store.assistant_action_drafts["assistant_action_draft_failed"]
    assert stored_draft["status"] == "pending"
    assert stored_draft["result_run_id"] is None

    audit_event = app.state.store.audit_events[-1]
    assert audit_event["event_type"] == "assistant_action_draft.retry_requested"
    assert audit_event["subject_id"] == "assistant_action_draft_failed"
    assert audit_event["payload"] == {
        "action": "create_scheduled_job",
        "previous_run_id": "assistant_action_run_failed",
        "reason": "修正字段后重试",
        "retry_count": 1,
    }

    conflict = client.post(
        "/api/assistant/action-drafts/assistant_action_draft_failed/retry",
        headers=auth_headers(),
        json={"reason": "再次重试"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "DRAFT_NOT_FAILED"
