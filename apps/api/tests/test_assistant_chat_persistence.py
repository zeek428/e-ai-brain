import json

from test_database_persistence import FakeSnapshotRepository, app, auth_headers, client

import app.api.routers.assistant as assistant_router
import app.services.assistant_action_drafts as assistant_action_drafts_service
from app.core.persistence import PersistentMemoryStore, PostgresRuntimeStore
from app.core.users import MemoryUserRepository


class AssistantChatRepositoryStub:
    def __init__(self) -> None:
        self.payload: dict | None = None
        self.assistant_chat_payload: dict | None = None
        self.id_counters: dict[str, int] = {}

    def load(self) -> dict | None:
        return self.payload

    def save(self, payload: dict) -> None:
        self.payload = payload

    def load_assistant_chat(self) -> dict | None:
        return self.assistant_chat_payload

    def save_assistant_chat(self, payload: dict) -> None:
        self.assistant_chat_payload = payload

    def next_id(self, prefix: str) -> str:
        self.id_counters[prefix] = self._max_existing_id(prefix) + 1
        return f"{prefix}_{self.id_counters[prefix]:03d}"

    def _max_existing_id(self, prefix: str) -> int:
        max_value = self.id_counters.get(prefix, 0)
        expected_prefix = f"{prefix}_"

        def visit(value: object) -> None:
            nonlocal max_value
            if isinstance(value, dict):
                for key, item in value.items():
                    if isinstance(key, str) and key.startswith(expected_prefix):
                        suffix = key.removeprefix(expected_prefix)
                        if suffix.isdigit():
                            max_value = max(max_value, int(suffix))
                    if key == "id" and isinstance(item, str) and item.startswith(expected_prefix):
                        suffix = item.removeprefix(expected_prefix)
                        if suffix.isdigit():
                            max_value = max(max_value, int(suffix))
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(self.assistant_chat_payload)
        return max_value


class ScheduledJobAssistantRepository(FakeSnapshotRepository):
    def __init__(self) -> None:
        super().__init__()
        self.scheduled_jobs_payload = {
            "scheduled_job_runs": {},
            "scheduled_jobs": {
                "scheduled_job_feedback_insight": {
                    "agent_id": None,
                    "config_json": {},
                    "created_at": "2026-06-16T08:00:00+00:00",
                    "created_by": "user_admin",
                    "cron_expression": None,
                    "enabled": True,
                    "execution_mode": "deterministic",
                    "id": "scheduled_job_feedback_insight",
                    "interval_seconds": None,
                    "job_type": "dashboard_snapshot_refresh",
                    "knowledge_document_ids": [],
                    "last_failure_at": None,
                    "last_run_at": None,
                    "last_success_at": None,
                    "lock_ttl_seconds": 900,
                    "max_retry_count": 0,
                    "model_gateway_config_id": None,
                    "name": "提取每周用户反馈有价值信息",
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
                    "skill_ids": [],
                    "source_system": "ai-brain",
                    "status": "active",
                    "timeout_seconds": 600,
                    "timezone": "Asia/Shanghai",
                    "updated_at": "2026-06-16T08:00:00+00:00",
                },
            },
        }

    def list_ai_agents(
        self,
        *,
        brain_app_id: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        return []

    def list_ai_skills(
        self,
        *,
        code: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        return []

    def list_scheduled_jobs(
        self,
        *,
        enabled: bool | None = None,
        job_type: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        items = [
            dict(job)
            for job in self.scheduled_jobs_payload.get("scheduled_jobs", {}).values()
        ]
        if enabled is not None:
            items = [job for job in items if job.get("enabled") is enabled]
        if job_type is not None:
            items = [job for job in items if job.get("job_type") == job_type]
        if status is not None:
            items = [job for job in items if job.get("status") == status]
        return items

    def list_scheduled_job_runs(
        self,
        *,
        scheduled_job_id: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        items = [
            dict(run)
            for run in self.scheduled_jobs_payload.get("scheduled_job_runs", {}).values()
        ]
        if scheduled_job_id is not None:
            items = [
                run for run in items if run.get("scheduled_job_id") == scheduled_job_id
            ]
        if status is not None:
            items = [run for run in items if run.get("status") == status]
        return items

    def save_scheduled_job_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        self.scheduled_jobs_payload.setdefault("scheduled_jobs", {})[record["id"]] = dict(
            record
        )
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def save_scheduled_job_run_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        self.scheduled_jobs_payload.setdefault("scheduled_job_runs", {})[
            record["id"]
        ] = dict(record)
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)


class AssistantPrerequisiteRepository(FakeSnapshotRepository):
    def __init__(self) -> None:
        super().__init__()
        self.ai_skills_payload: dict[str, dict] = {}

    def list_ai_agents(
        self,
        *,
        brain_app_id: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        return []

    def list_ai_skills(
        self,
        *,
        code: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        items = [dict(skill) for skill in self.ai_skills_payload.values()]
        if code is not None:
            items = [skill for skill in items if skill.get("code") == code]
        if status is not None:
            items = [skill for skill in items if skill.get("status") == status]
        return items

    def list_scheduled_jobs(
        self,
        *,
        enabled: bool | None = None,
        job_type: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        return []

    def list_scheduled_job_runs(
        self,
        *,
        scheduled_job_id: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        return []


def test_assistant_chat_history_is_persisted_through_fine_grained_repository_payload():
    repository = AssistantChatRepositoryStub()
    current_store = PersistentMemoryStore.from_repository(repository)
    current_store.assistant_conversations["conversation_009"] = {
        "created_at": "2026-06-03T08:00:00+00:00",
        "id": "conversation_009",
        "last_message_at": "2026-06-03T08:01:00+00:00",
        "message_count": 2,
        "product_id": "product_001",
        "title": "AI Brain 进展",
        "updated_at": "2026-06-03T08:01:00+00:00",
        "user_id": "user_admin",
    }
    current_store.assistant_messages["assistant_message_011"] = {
        "content": "AI Brain 现在开发到哪里了？",
        "conversation_id": "conversation_009",
        "created_at": "2026-06-03T08:00:00+00:00",
        "id": "assistant_message_011",
        "model": None,
        "product_id": "product_001",
        "role": "user",
        "suggestions": [],
        "user_id": "user_admin",
    }
    current_store.assistant_messages["assistant_message_012"] = {
        "content": "已完成 GitHub PR Review 链路。",
        "conversation_id": "conversation_009",
        "created_at": "2026-06-03T08:01:00+00:00",
        "id": "assistant_message_012",
        "model": "gpt-review",
        "product_id": "product_001",
        "role": "assistant",
        "suggestions": ["查看任务中心"],
        "user_id": "user_admin",
    }

    current_store.persist()

    assert repository.assistant_chat_payload == {
        "assistant_action_drafts": {},
        "assistant_action_runs": {},
        "assistant_conversations": current_store.assistant_conversations,
        "assistant_messages": current_store.assistant_messages,
    }


def test_structured_assistant_chat_history_restore_and_sync_counters():
    repository = AssistantChatRepositoryStub()
    repository.payload = {
        "assistant_conversations": {
            "conversation_002": {
                "id": "conversation_002",
                "message_count": 1,
                "title": "旧快照会话",
                "user_id": "user_admin",
            }
        },
        "assistant_messages": {
            "assistant_message_002": {
                "content": "旧快照消息",
                "conversation_id": "conversation_002",
                "id": "assistant_message_002",
                "role": "user",
                "user_id": "user_admin",
            }
        },
    }
    repository.assistant_chat_payload = {
        "assistant_conversations": {
            "conversation_009": {
                "created_at": "2026-06-03T08:00:00+00:00",
                "id": "conversation_009",
                "last_message_at": "2026-06-03T08:01:00+00:00",
                "message_count": 2,
                "product_id": None,
                "title": "结构表会话",
                "updated_at": "2026-06-03T08:01:00+00:00",
                "user_id": "user_admin",
            }
        },
        "assistant_messages": {
            "assistant_message_011": {
                "content": "结构表消息",
                "conversation_id": "conversation_009",
                "created_at": "2026-06-03T08:00:00+00:00",
                "id": "assistant_message_011",
                "model": None,
                "product_id": None,
                "role": "user",
                "suggestions": [],
                "user_id": "user_admin",
            }
        },
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert list(rebuilt_store.assistant_conversations) == ["conversation_009"]
    assert list(rebuilt_store.assistant_messages) == ["assistant_message_011"]
    assert rebuilt_store.new_id("conversation") == "conversation_010"
    assert rebuilt_store.new_id("assistant_message") == "assistant_message_012"


def test_assistant_chat_writes_repository_without_request_persist(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.model_gateway_payload = {
        "model_gateway_configs": {
            "model_gateway_config_assistant": {
                "api_key": "sk-assistant-test",
                "base_url": "https://api.example.com/v1",
                "default_chat_model": "gpt-assistant",
                "default_embedding_model": "text-embedding-assistant",
                "embedding_connection_mode": "disabled",
                "id": "model_gateway_config_assistant",
                "is_default": True,
                "max_retries": 1,
                "name": "Assistant test gateway",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 30,
            }
        },
        "model_gateway_logs": [],
    }

    class FakeResponse:
        def __init__(self, answer: str):
            self.answer = answer

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": self.answer,
                                        "suggestions": ["查看需求", "查看任务"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 9, "prompt_tokens": 21, "total_tokens": 30},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def use_empty_postgres_runtime_store() -> None:
        app.state.store = PostgresRuntimeStore(repository)

    def successful_urlopen(request, timeout):
        body = json.loads(request.data.decode("utf-8"))
        user_message = body["messages"][1]["content"]
        return FakeResponse(f"已记录：{json.loads(user_message)['message']}")

    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()
    monkeypatch.setattr(assistant_router, "urlopen", successful_urlopen)

    try:
        headers = auth_headers()
        first = client.post(
            "/api/assistant/chat",
            json={"conversation_id": "conv_dbfirst", "message": "查询 AI Brain 进度"},
            headers=headers,
        ).json()["data"]
        assert first["conversation_id"] == "conv_dbfirst"

        use_empty_postgres_runtime_store()
        conversations = client.get("/api/assistant/conversations", headers=headers).json()[
            "data"
        ]["items"]
        messages = client.get(
            "/api/assistant/conversations/conv_dbfirst/messages",
            headers=headers,
        ).json()["data"]["items"]
        assert [conversation["id"] for conversation in conversations] == ["conv_dbfirst"]
        assert conversations[0]["message_count"] == 2
        assert [message["role"] for message in messages] == ["user", "assistant"]
        assert messages[1]["content"] == "已记录：查询 AI Brain 进度"

        second = client.post(
            "/api/assistant/chat",
            json={"conversation_id": "conv_dbfirst", "message": "继续记录下一步"},
            headers=headers,
        ).json()["data"]
        assert second["conversation_id"] == "conv_dbfirst"

        use_empty_postgres_runtime_store()
        updated_conversation = client.get("/api/assistant/conversations", headers=headers).json()[
            "data"
        ]["items"][0]
        updated_messages = client.get(
            "/api/assistant/conversations/conv_dbfirst/messages",
            headers=headers,
        ).json()["data"]["items"]
        assert updated_conversation["message_count"] == 4
        assert updated_messages[-1]["content"] == "已记录：继续记录下一步"

        def failing_urlopen(_request, timeout):
            raise OSError("assistant gateway unavailable")

        monkeypatch.setattr(assistant_router, "urlopen", failing_urlopen)
        failed = client.post(
            "/api/assistant/chat",
            json={"message": "触发失败日志"},
            headers=headers,
        )
        assert failed.status_code == 502
        assert failed.json()["detail"]["code"] == "ASSISTANT_CHAT_FAILED"

        use_empty_postgres_runtime_store()
        logs = client.get(
            "/api/model-gateway/logs?purpose=assistant_chat",
            headers=headers,
        ).json()["data"]["items"]
        assert [log["status"] for log in logs].count("succeeded") == 2
        assert any(log["status"] == "failed" for log in logs)
        assert any(
            event["event_type"] == "assistant.chat_completed"
            for event in repository.audit_events_payload["audit_events"]
        )
        assert any(
            event["event_type"] == "model_gateway.called"
            and event["payload"]["status"] == "failed"
            for event in repository.audit_events_payload["audit_events"]
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_assistant_prerequisite_draft_resolution_reads_repository_action_runs(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = AssistantPrerequisiteRepository()
    now = "2026-06-14T08:00:00+00:00"
    repository.ai_skills_payload = {
        "ai_skill_feedback_summary": {
            "allowed_tools": [],
            "code": "feedback_summary",
            "created_at": now,
            "created_by": "user_admin",
            "description": None,
            "id": "ai_skill_feedback_summary",
            "input_schema": {},
            "name": "反馈摘要 Skill",
            "output_schema": {},
            "prompt_template": "请总结用户反馈。",
            "required_context": [],
            "requires_human_review": False,
            "risk_level": "medium",
            "status": "active",
            "updated_at": now,
            "version": "1.0.0",
        }
    }
    repository.assistant_chat_payload = {
        "assistant_action_drafts": {
            "assistant_action_draft_repo_skill": {
                "action": "create_ai_skill",
                "confirmed_at": now,
                "confirmed_by": "user_admin",
                "created_at": now,
                "created_by": "user_admin",
                "id": "assistant_action_draft_repo_skill",
                "metadata_json": {},
                "payload": {"code": "feedback_summary", "name": "反馈摘要 Skill"},
                "result_run_id": "assistant_action_run_repo_skill",
                "risk_level": "medium",
                "status": "confirmed",
                "title": "反馈摘要 Skill",
                "updated_at": now,
            },
            "assistant_action_draft_repo_agent": {
                "action": "create_ai_agent",
                "created_at": now,
                "created_by": "user_admin",
                "id": "assistant_action_draft_repo_agent",
                "metadata_json": {},
                "payload": {
                    "assistant_prerequisite_draft_ids": [
                        "assistant_action_draft_repo_skill"
                    ],
                    "brain_app_id": "rd_brain",
                    "code": "feedback_analysis_agent",
                    "default_skill_ids": ["assistant_action_draft_repo_skill"],
                    "name": "反馈分析 AI 角色",
                    "system_prompt": "请总结用户反馈。",
                },
                "risk_level": "medium",
                "status": "pending",
                "title": "反馈分析 AI 角色",
                "updated_at": now,
            },
        },
        "assistant_action_runs": {
            "assistant_action_run_repo_skill": {
                "action": "create_ai_skill",
                "created_at": now,
                "draft_id": "assistant_action_draft_repo_skill",
                "executed_by": "user_admin",
                "finished_at": now,
                "id": "assistant_action_run_repo_skill",
                "result": {"id": "ai_skill_feedback_summary"},
                "result_id": "ai_skill_feedback_summary",
                "result_type": "ai_skill",
                "started_at": now,
                "status": "succeeded",
                "updated_at": now,
            },
        },
        "assistant_conversations": {},
        "assistant_messages": {},
    }
    stale_store = PostgresRuntimeStore(repository)
    stale_store.assistant_action_drafts = {}
    stale_store.assistant_action_runs = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    def fake_create_ai_agent_response(*, current_store, payload, user):
        assert isinstance(current_store, PostgresRuntimeStore)
        assert payload.default_skill_ids == ["ai_skill_feedback_summary"]
        assert user["id"] == "user_admin"
        return {
            "default_skill_ids": payload.default_skill_ids,
            "id": "ai_agent_feedback_analysis",
            "name": payload.name,
        }

    monkeypatch.setattr(
        assistant_action_drafts_service,
        "create_ai_agent_response",
        fake_create_ai_agent_response,
    )

    try:
        response = client.post(
            "/api/assistant/action-drafts/assistant_action_draft_repo_agent/confirm",
            headers=auth_headers(),
        )

        assert response.status_code == 200, response.text
        payload = response.json()["data"]
        assert payload["run"]["result_id"] == "ai_agent_feedback_analysis"
        assert payload["run"]["result"]["default_skill_ids"] == [
            "ai_skill_feedback_summary"
        ]
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_assistant_chat_runs_scheduled_job_from_repository_context():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = ScheduledJobAssistantRepository()

    app.state.store = PostgresRuntimeStore(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        response = client.post(
            "/api/assistant/chat",
            json={"message": "@提取每周用户反馈有价值信息 执行一次"},
            headers=auth_headers(),
        )

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["model"] == "assistant-deterministic"
        assert "已执行" in payload["message"]["content"]
        runs = repository.scheduled_jobs_payload["scheduled_job_runs"]
        assert len(runs) == 1
        run = next(iter(runs.values()))
        assert run["scheduled_job_id"] == "scheduled_job_feedback_insight"
        assert run["trigger_type"] == "manual"
        assert repository.collector_runs_payload is not None
        assert len(repository.collector_runs_payload["collector_runs"]) == 1
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_assistant_history_uses_repository_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.assistant_chat_payload = {
        "assistant_conversations": {
            "conversation_repo_admin": {
                "created_at": "2026-06-03T08:00:00+00:00",
                "id": "conversation_repo_admin",
                "last_message_at": "2026-06-03T08:01:00+00:00",
                "message_count": 2,
                "product_id": "product_119",
                "title": "Admin 会话",
                "updated_at": "2026-06-03T08:01:00+00:00",
                "user_id": "user_admin",
            },
            "conversation_repo_reviewer": {
                "created_at": "2026-06-03T09:00:00+00:00",
                "id": "conversation_repo_reviewer",
                "last_message_at": "2026-06-03T09:01:00+00:00",
                "message_count": 1,
                "product_id": None,
                "title": "Reviewer 会话",
                "updated_at": "2026-06-03T09:01:00+00:00",
                "user_id": "user_reviewer",
            },
        },
        "assistant_messages": {
            "assistant_message_repo_admin_001": {
                "content": "admin question",
                "conversation_id": "conversation_repo_admin",
                "created_at": "2026-06-03T08:00:00+00:00",
                "id": "assistant_message_repo_admin_001",
                "role": "user",
                "suggestions": [],
                "user_id": "user_admin",
            },
            "assistant_message_repo_admin_002": {
                "content": "admin answer",
                "conversation_id": "conversation_repo_admin",
                "created_at": "2026-06-03T08:01:00+00:00",
                "id": "assistant_message_repo_admin_002",
                "model": "gpt-read",
                "role": "assistant",
                "suggestions": ["查看任务"],
                "user_id": "user_admin",
            },
            "assistant_message_repo_reviewer_001": {
                "content": "reviewer question",
                "conversation_id": "conversation_repo_reviewer",
                "created_at": "2026-06-03T09:00:00+00:00",
                "id": "assistant_message_repo_reviewer_001",
                "role": "user",
                "suggestions": [],
                "user_id": "user_reviewer",
            },
        },
    }
    stale_store = PersistentMemoryStore.from_repository(repository)
    stale_store.assistant_conversations = {}
    stale_store.assistant_messages = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        admin_conversations = client.get(
            "/api/assistant/conversations",
            headers=auth_headers(),
        ).json()["data"]["items"]
        assert [item["id"] for item in admin_conversations] == ["conversation_repo_admin"]
        assert admin_conversations[0]["message_count"] == 2

        admin_messages = client.get(
            "/api/assistant/conversations/conversation_repo_admin/messages",
            headers=auth_headers(),
        ).json()["data"]["items"]
        assert [item["id"] for item in admin_messages] == [
            "assistant_message_repo_admin_001",
            "assistant_message_repo_admin_002",
        ]
        assert admin_messages[1]["model"] == "gpt-read"
        assert admin_messages[1]["suggestions"] == ["查看任务"]

        reviewer_conversations = client.get(
            "/api/assistant/conversations",
            headers=auth_headers("reviewer@example.com", "reviewer123"),
        ).json()["data"]["items"]
        assert [item["id"] for item in reviewer_conversations] == [
            "conversation_repo_reviewer"
        ]
        cross_user_messages = client.get(
            "/api/assistant/conversations/conversation_repo_admin/messages",
            headers=auth_headers("reviewer@example.com", "reviewer123"),
        )
        assert cross_user_messages.status_code == 404
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_assistant_metrics_use_repository_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    now = "2026-06-16T10:00:00+00:00"
    repository.assistant_chat_payload = {
        "assistant_action_drafts": {
            "assistant_action_draft_repo_admin": {
                "action": "create_scheduled_job",
                "created_at": now,
                "created_by": "user_admin",
                "id": "assistant_action_draft_repo_admin",
                "metadata_json": {"user_modified": True},
                "payload": {"name": "仓储草案"},
                "result_run_id": "assistant_action_run_repo_admin",
                "risk_level": "medium",
                "status": "confirmed",
                "title": "仓储草案",
                "updated_at": now,
            },
            "assistant_action_draft_repo_reviewer": {
                "action": "create_scheduled_job",
                "created_at": now,
                "created_by": "user_reviewer",
                "id": "assistant_action_draft_repo_reviewer",
                "metadata_json": {},
                "payload": {"name": "其他用户草案"},
                "risk_level": "medium",
                "status": "cancelled",
                "title": "其他用户草案",
                "updated_at": now,
            },
        },
        "assistant_action_runs": {
            "assistant_action_run_repo_admin": {
                "action": "create_scheduled_job",
                "created_at": now,
                "draft_id": "assistant_action_draft_repo_admin",
                "executed_by": "user_admin",
                "finished_at": now,
                "id": "assistant_action_run_repo_admin",
                "result": {"id": "scheduled_job_repo"},
                "started_at": now,
                "status": "succeeded",
                "updated_at": now,
            },
            "assistant_action_run_repo_reviewer": {
                "action": "create_scheduled_job",
                "created_at": now,
                "draft_id": "assistant_action_draft_repo_reviewer",
                "executed_by": "user_reviewer",
                "finished_at": now,
                "id": "assistant_action_run_repo_reviewer",
                "result": {},
                "started_at": now,
                "status": "failed",
                "updated_at": now,
            },
        },
        "assistant_conversations": {},
        "assistant_messages": {
            "assistant_message_repo_admin": {
                "content": "@知识 总结一下",
                "conversation_id": "conversation_repo_admin",
                "created_at": now,
                "id": "assistant_message_repo_admin",
                "metadata_json": {
                    "references": [
                        {"id": "knowledge_repo_doc", "type": "knowledge_document"},
                        {"id": "knowledge_repo_folder", "type": "knowledge_folder"},
                    ]
                },
                "role": "user",
                "suggestions": [],
                "user_id": "user_admin",
            },
            "assistant_message_repo_reviewer": {
                "content": "@其他 总结一下",
                "conversation_id": "conversation_repo_reviewer",
                "created_at": now,
                "id": "assistant_message_repo_reviewer",
                "metadata_json": {
                    "references": [
                        {"id": "knowledge_other_doc", "type": "knowledge_document"}
                    ]
                },
                "role": "user",
                "suggestions": [],
                "user_id": "user_reviewer",
            },
        },
    }
    stale_store = PostgresRuntimeStore(repository)
    stale_store.assistant_action_drafts = {}
    stale_store.assistant_action_runs = {}
    stale_store.assistant_messages = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        response = client.get("/api/assistant/metrics", headers=auth_headers())

        assert response.status_code == 200
        summary = response.json()["data"]["summary"]
        assert summary["draft_total"] == 1
        assert summary["draft_confirmed_count"] == 1
        assert summary["draft_user_modified_count"] == 1
        assert summary["action_run_total"] == 1
        assert summary["action_run_succeeded_count"] == 1
        assert summary["knowledge_reference_count"] == 2
        assert summary["reference_usage_rate"] == 1.0
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_assistant_action_draft_confirm_uses_runtime_store_under_postgres(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.assistant_chat_payload = {
        "assistant_action_drafts": {
            "assistant_action_draft_repo_001": {
                "action": "create_scheduled_job",
                "created_at": "2026-06-14T08:00:00+00:00",
                "created_by": "user_admin",
                "id": "assistant_action_draft_repo_001",
                "metadata_json": {},
                "payload": {
                    "job_type": "dashboard_snapshot_refresh",
                    "name": "仓储上下文确认草案",
                    "schedule_type": "manual",
                },
                "risk_level": "medium",
                "status": "pending",
                "title": "确认仓储上下文草案",
                "updated_at": "2026-06-14T08:00:00+00:00",
            }
        },
        "assistant_action_runs": {},
        "assistant_conversations": {},
        "assistant_messages": {},
    }
    app.state.store = PostgresRuntimeStore(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    def fake_create_scheduled_job_response(*, current_store, payload, user):
        assert isinstance(current_store, PostgresRuntimeStore)
        assert payload.config_json["assistant_draft"]["draft_id"] == (
            "assistant_action_draft_repo_001"
        )
        assert user["id"] == "user_admin"
        return {
            "config_json": payload.config_json,
            "id": "scheduled_job_from_assistant_draft",
            "name": payload.name,
        }

    monkeypatch.setattr(
        assistant_action_drafts_service,
        "create_scheduled_job_response",
        fake_create_scheduled_job_response,
    )
    try:
        response = client.post(
            "/api/assistant/action-drafts/assistant_action_draft_repo_001/confirm",
            headers=auth_headers(),
        )

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["draft"]["status"] == "confirmed"
        assert payload["run"]["result_id"] == "scheduled_job_from_assistant_draft"
        saved_draft = repository.assistant_chat_payload["assistant_action_drafts"][
            "assistant_action_draft_repo_001"
        ]
        assert saved_draft["status"] == "confirmed"
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
