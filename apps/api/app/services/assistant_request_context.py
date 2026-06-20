from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.store import MemoryStore, default_brain_apps
from app.services.assistant_history import assistant_query_repository


class AssistantRepositoryRequestContext:
    def __init__(self, repository: Any) -> None:
        self.repository = repository
        self.brain_apps: dict[str, dict[str, Any]] = default_brain_apps()
        self.products: dict[str, dict[str, Any]] = {}
        self.product_versions: dict[str, dict[str, Any]] = {}
        self.product_modules: dict[str, dict[str, Any]] = {}
        self.product_git_repositories: dict[str, dict[str, Any]] = {}
        self.related_systems: dict[str, dict[str, Any]] = {}
        self.model_gateway_configs: dict[str, dict[str, Any]] = {}
        self.model_gateway_logs: list[dict[str, Any]] = []
        self.ai_skills: dict[str, dict[str, Any]] = {}
        self.ai_agents: dict[str, dict[str, Any]] = {}
        self.integration_plugins: dict[str, dict[str, Any]] = {}
        self.plugin_connections: dict[str, dict[str, Any]] = {}
        self.plugin_actions: dict[str, dict[str, Any]] = {}
        self.plugin_invocation_logs: dict[str, dict[str, Any]] = {}
        self.collector_runs: dict[str, dict[str, Any]] = {}
        self.scheduled_jobs: dict[str, dict[str, Any]] = {}
        self.scheduled_job_runs: dict[str, dict[str, Any]] = {}
        self.assistant_chat_runs: dict[str, dict[str, Any]] = {}
        self.assistant_conversations: dict[str, dict[str, Any]] = {}
        self.assistant_messages: dict[str, dict[str, Any]] = {}
        self.assistant_action_drafts: dict[str, dict[str, Any]] = {}
        self.assistant_action_runs: dict[str, dict[str, Any]] = {}
        self.gitlab_mr_snapshots: dict[str, dict[str, Any]] = {}
        self.code_review_reports: dict[str, dict[str, Any]] = {}
        self.knowledge_deposits: dict[str, dict[str, Any]] = {}
        self.mock_writebacks: dict[str, dict[str, Any]] = {}
        self.bugs: dict[str, dict[str, Any]] = {}
        self.requirements: dict[str, dict[str, Any]] = {}
        self.ai_tasks: dict[str, dict[str, Any]] = {}
        self.graph_runs: dict[str, dict[str, Any]] = {}
        self.graph_checkpoints: dict[str, dict[str, Any]] = {}
        self.human_reviews: dict[str, dict[str, Any]] = {}
        self.audit_events: list[dict[str, Any]] = []
        self.counters: dict[str, int] = {}

    def new_id(self, prefix: str) -> str:
        next_id = getattr(self.repository, "next_id", None)
        if not callable(next_id):
            next_value = self.counters.get(prefix, 0) + 1
            self.counters[prefix] = next_value
            return f"{prefix}_{next_value:03d}"
        allocated_id = next_id(prefix)
        suffix = allocated_id.removeprefix(f"{prefix}_")
        if suffix.isdigit():
            self.counters[prefix] = max(self.counters.get(prefix, 0), int(suffix))
        return allocated_id

    def audit(
        self,
        *,
        event_type: str,
        actor_id: str,
        ai_task_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": self.new_id("audit"),
            "event_type": event_type,
            "actor_id": actor_id,
            "ai_task_id": ai_task_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "payload": payload or {},
            "sequence": len(self.audit_events) + 1,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.audit_events.append(event)
        return event


def assistant_request_store(current_store: MemoryStore, *, user_id: str) -> Any:
    repository = assistant_query_repository(current_store)
    if repository is None:
        return current_store
    return assistant_source_store(repository, user_id=user_id)


def assistant_source_store(repository: Any, *, user_id: str) -> Any:
    load_task_rows = getattr(repository, "get_task_workflow_source_rows", None)
    source_store = (
        assistant_task_source_store(load_task_rows(), repository=repository)
        if callable(load_task_rows)
        else AssistantRepositoryRequestContext(repository)
    )
    _hydrate_assistant_operational_store(source_store, repository)
    conversations = repository.list_assistant_conversations(user_id=user_id)
    list_chat_runs = getattr(repository, "list_assistant_chat_runs", None)
    if callable(list_chat_runs):
        source_store.assistant_chat_runs = {
            str(run["id"]): dict(run)
            for run in list_chat_runs(user_id=user_id)
            if run.get("id") is not None
        }
    source_store.assistant_conversations = {
        str(conversation["id"]): dict(conversation)
        for conversation in conversations
        if conversation.get("id") is not None
    }
    messages: dict[str, dict[str, Any]] = {}
    for conversation in conversations:
        conversation_id = conversation.get("id")
        if conversation_id is None:
            continue
        conversation_messages = repository.list_assistant_conversation_messages(
            conversation_id=str(conversation_id),
            user_id=user_id,
        )
        for message in conversation_messages or []:
            if message.get("id") is not None:
                messages[str(message["id"])] = dict(message)
    source_store.assistant_messages = messages
    return source_store


def _hydrate_assistant_operational_store(source_store: Any, repository: Any) -> None:
    collection_loaders = {
        "ai_agents": ("list_ai_agents", {"brain_app_id": None, "status": None}),
        "ai_skills": ("list_ai_skills", {"code": None, "status": None}),
        "integration_plugins": ("list_plugins", {"protocol": None, "status": None}),
        "plugin_actions": ("list_plugin_actions", {"plugin_id": None, "status": None}),
        "plugin_connections": (
            "list_plugin_connections",
            {"environment": None, "plugin_id": None, "status": None},
        ),
        "plugin_invocation_logs": (
            "list_plugin_invocation_logs",
            {
                "action_id": None,
                "scheduled_job_id": None,
                "scheduled_job_run_id": None,
                "status": None,
            },
        ),
        "collector_runs": (
            "list_collector_runs",
            {
                "collector_type": None,
                "product_id": None,
                "source_system": None,
                "status": None,
            },
        ),
        "scheduled_jobs": (
            "list_scheduled_jobs",
            {"enabled": None, "job_type": None, "status": None},
        ),
        "scheduled_job_runs": (
            "list_scheduled_job_runs",
            {"scheduled_job_id": None, "status": None},
        ),
    }
    for collection_name, (method_name, kwargs) in collection_loaders.items():
        list_items = getattr(repository, method_name, None)
        if not callable(list_items):
            continue
        try:
            items = list_items(**kwargs)
        except TypeError:
            items = list_items()
        setattr(
            source_store,
            collection_name,
            {
                str(item["id"]): dict(item)
                for item in items
                if isinstance(item, dict) and item.get("id") is not None
            },
        )
    list_model_gateway_logs = getattr(repository, "list_model_gateway_logs", None)
    if callable(list_model_gateway_logs):
        try:
            source_store.model_gateway_logs = list_model_gateway_logs(
                ai_task_id=None,
                purpose=None,
                status=None,
            )
        except TypeError:
            source_store.model_gateway_logs = list_model_gateway_logs()


def assistant_task_source_store(rows: dict[str, Any], *, repository: Any) -> Any:
    source_store = AssistantRepositoryRequestContext(repository)
    source_store.audit_events = list(rows.get("audit_events", []))
    source_store.model_gateway_logs = list(rows.get("model_gateway_logs", []))
    collection_keys = {
        "ai_tasks": "tasks",
        "bugs": "bugs",
        "code_review_reports": "code_review_reports",
        "gitlab_mr_snapshots": "gitlab_mr_snapshots",
        "graph_checkpoints": "graph_checkpoints",
        "graph_runs": "graph_runs",
        "human_reviews": "human_reviews",
        "knowledge_deposits": "knowledge_deposits",
        "model_gateway_configs": "model_gateway_configs",
        "mock_writebacks": "mock_writebacks",
        "product_git_repositories": "product_git_repositories",
        "product_modules": "product_modules",
        "product_versions": "product_versions",
        "products": "products",
        "related_systems": "related_systems",
        "requirements": "requirements",
    }
    for store_key, row_key in collection_keys.items():
        setattr(
            source_store,
            store_key,
            {
                str(item["id"]): dict(item)
                for item in rows.get(row_key, [])
                if item.get("id") is not None
            },
        )
    for result in rows.get("mock_writebacks", []):
        idempotency_key = result.get("idempotency_key") or result.get("task_id") or result.get("id")
        if idempotency_key is not None:
            source_store.mock_writebacks[str(idempotency_key)] = dict(result)
    return source_store


def save_assistant_chat_records(
    current_store: MemoryStore,
    *,
    chat_run: dict[str, Any] | None = None,
    conversation: dict[str, Any] | None,
    messages: list[dict[str, Any]],
    audit_events: list[dict[str, Any]],
    model_log: dict[str, Any] | None = None,
) -> None:
    repository = runtime_repository(current_store)
    save_records = getattr(repository, "save_assistant_chat_records", None)
    if save_records is not None:
        save_records(
            chat_run=chat_run,
            conversation=conversation,
            messages=messages,
            model_log=model_log,
            audit_events=audit_events,
        )


def runtime_repository(current_store: Any) -> Any | None:
    return getattr(current_store, "repository", None)
