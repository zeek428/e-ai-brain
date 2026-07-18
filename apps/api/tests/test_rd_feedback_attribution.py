from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from app.core.store import MemoryStore
from app.services.rd_feedback_attribution import record_role_feedback


def _feedback_store() -> MemoryStore:
    store = MemoryStore()
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "strategy_snapshot_id": "snapshot-1",
        "run_generation": 2,
    }
    store.rd_run_seats.update(
        {
            "seat-reviewer": {
                "id": "seat-reviewer",
                "collaboration_run_id": "run-1",
                "role_code": "reviewer",
                "subject_type": "human_user",
                "human_user_id": "reviewer-1",
            },
            "seat-developer": {
                "id": "seat-developer",
                "collaboration_run_id": "run-1",
                "role_code": "developer",
                "subject_type": "ai_employee",
                "ai_employee_id": "employee-1",
            },
        }
    )
    return store


def test_feedback_fingerprint_uses_attributed_subject_and_preserves_separate_producer() -> None:
    store = _feedback_store()

    saved = record_role_feedback(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
        attempt_id="attempt-1",
        source_event_id="event-1",
        feedback_kind="review_approved",
        attributed={
            "subject_type": "ai_employee",
            "subject_id": "employee-1",
            "role_code": "developer",
            "seat_id": "seat-developer",
        },
        producer={
            "subject_type": "human_user",
            "subject_id": "reviewer-1",
            "role_code": "reviewer",
            "seat_id": "seat-reviewer",
        },
        executor_profile_id="executor-1",
        actor_id="reviewer-1",
        evidence_refs=[{"id": "gate-1", "kind": "quality_gate"}],
    )

    assert saved["feedback_kind"] == "review_approved"
    assert saved["ai_employee_id"] == "employee-1"
    assert saved["producer_subject_id"] == "reviewer-1"
    assert saved["producer_seat_id"] == "seat-reviewer"
    assert saved["strategy_snapshot_id"] == "snapshot-1"


def test_same_persisted_event_replays_once_while_distinct_kind_or_subject_is_distinct() -> None:
    store = _feedback_store()
    kwargs = {
        "collaboration_run_id": "run-1",
        "work_item_id": "work-1",
        "attempt_id": "attempt-1",
        "source_event_id": "event-1",
        "feedback_kind": "review_approved",
        "attributed": {
            "subject_type": "ai_employee",
            "subject_id": "employee-1",
            "role_code": "developer",
            "seat_id": "seat-developer",
        },
        "producer": {
            "subject_type": "human_user",
            "subject_id": "reviewer-1",
            "role_code": "reviewer",
            "seat_id": "seat-reviewer",
        },
        "executor_profile_id": "executor-1",
        "actor_id": "reviewer-1",
    }
    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(lambda _: record_role_feedback(store, **kwargs), range(8)))

    assert {record["id"] for record in records} == {records[0]["id"]}
    assert len(store.role_feedback_records) == 1

    record_role_feedback(store, **{**kwargs, "feedback_kind": "review_rejected"})
    record_role_feedback(
        store,
        **{
            **kwargs,
            "attributed": {
                "subject_type": "human_user",
                "subject_id": "reviewer-1",
                "role_code": "reviewer",
                "seat_id": "seat-reviewer",
            },
        },
    )
    assert len(store.role_feedback_records) == 3
