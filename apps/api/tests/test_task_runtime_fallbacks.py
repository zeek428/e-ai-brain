from copy import deepcopy

from app.services.task_code_review_execution import create_code_review_report
from app.services.task_graph_runtime import start_graph_run, write_graph_checkpoint
from app.services.task_persistence_helpers import record_audit_event
from app.services.task_review_artifacts import create_knowledge_deposit, create_task_suggested_bugs


class MinimalTaskStore:
    def __init__(self) -> None:
        self.audit_events = []
        self.bugs = {}
        self.code_review_reports = {}
        self.counters = {}
        self.graph_checkpoints = {}
        self.graph_runs = {}
        self.knowledge_deposits = {}

    def new_id(self, prefix: str) -> str:
        next_value = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = next_value
        return f"{prefix}_{next_value:03d}"

    def snapshot(self, value):
        return deepcopy(value)


def test_task_record_audit_event_appends_minimal_store_fallback_event():
    current_store = MinimalTaskStore()

    event = record_audit_event(
        current_store,
        actor_id="user_admin",
        ai_task_id="task_001",
        event_type="task.tested",
        payload={"source": "test"},
        subject_id="task_001",
        subject_type="ai_task",
    )

    assert event["id"] == "audit_001"
    assert current_store.audit_events == [event]


def test_graph_runtime_uses_memory_fallback_collections():
    current_store = MinimalTaskStore()
    task = {"id": "task_001", "status": "running", "task_type": "technical_solution"}

    graph_run, checkpoint = start_graph_run(current_store, task=task, review_id="review_001")
    next_checkpoint = write_graph_checkpoint(
        current_store,
        current_step="complete_archive",
        graph_run=graph_run,
        state_snapshot={"task_status": "completed"},
        task=task,
    )

    assert current_store.graph_runs == {graph_run["id"]: graph_run}
    assert current_store.graph_checkpoints[checkpoint["id"]] == checkpoint
    assert current_store.graph_checkpoints[next_checkpoint["id"]] == next_checkpoint


def test_code_review_report_uses_memory_fallback_collection():
    current_store = MinimalTaskStore()
    task = {
        "id": "task_001",
        "input_json": {"gitlab_mr_snapshot_id": "snapshot_001"},
    }

    report = create_code_review_report(
        current_store,
        task=task,
        output={
            "executor": {"name": "deterministic"},
            "findings": [],
            "risk_level": "low",
            "summary": "No issues.",
        },
        uses_repository_context=lambda _store: False,
    )

    assert task["code_review_report_id"] == report["id"]
    assert current_store.code_review_reports == {report["id"]: report}


def test_task_review_artifacts_use_memory_fallback_collections_and_audit_events():
    current_store = MinimalTaskStore()
    task = {
        "id": "task_001",
        "output_json": {
            "bug_suggestions": [{"description": "Broken flow", "title": "Login fails"}],
            "summary": "Ship the accepted result.",
        },
        "product_id": "product_001",
        "requirement_id": "requirement_001",
        "task_type": "automated_testing",
        "title": "自动化测试",
        "version_id": "version_001",
    }

    bug_ids = create_task_suggested_bugs(
        current_store,
        actor_id="user_admin",
        fallback_description="Fallback description",
        fallback_steps="Fallback steps",
        source="ai_auto_test",
        task=task,
        title_prefix="自动化测试发现",
    )
    deposit = create_knowledge_deposit(current_store, task)

    assert bug_ids == ["bug_001"]
    assert current_store.bugs["bug_001"]["title"] == "Login fails"
    assert current_store.audit_events[0]["subject_id"] == "bug_001"
    assert current_store.knowledge_deposits == {deposit["id"]: deposit}
