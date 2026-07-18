from __future__ import annotations

from app.core.store import MemoryStore
from app.services.rd_collaboration_planning import persist_work_item_plan
from app.services.rd_command_replay_secrets import scrub_expired_command_replay_secrets
from app.services.rd_work_item_scheduler import (
    cancel_work_item,
    claim_work_item,
    complete_attempt,
    ready_work_items,
    review_work_item,
)


def test_scheduler_does_not_release_item_before_dependencies_are_approved() -> None:
    store = MemoryStore()
    store.rd_work_items.update(
        {
            "design-item": {
                "id": "design-item",
                "collaboration_run_id": "run-1",
                "status": "reviewing",
                "priority": 10,
            },
            "integration-item": {
                "id": "integration-item",
                "collaboration_run_id": "run-1",
                "status": "draft",
                "priority": 20,
            },
        }
    )
    store.rd_work_item_dependencies["dependency-1"] = {
        "id": "dependency-1",
        "collaboration_run_id": "run-1",
        "predecessor_work_item_id": "design-item",
        "successor_work_item_id": "integration-item",
        "status": "pending",
    }

    items = ready_work_items(store, collaboration_run_id="run-1")

    assert "integration-item" not in {item["id"] for item in items}


def test_persisted_plan_activates_only_root_work_items_for_claiming() -> None:
    store = MemoryStore()
    store.rd_collaboration_runs["run-plan"] = {
        "id": "run-plan",
        "status": "planning",
        "version": 1,
        "plan_version": 0,
    }
    store.rd_run_seats.update(
        {
            "seat-dev": {
                "id": "seat-dev",
                "collaboration_run_id": "run-plan",
                "role_code": "developer",
                "subject_type": "human_user",
                "human_user_id": "user-dev",
                "capacity": 1,
                "status": "active",
            },
            "seat-test": {
                "id": "seat-test",
                "collaboration_run_id": "run-plan",
                "role_code": "tester",
                "subject_type": "human_user",
                "human_user_id": "user-test",
                "capacity": 1,
                "status": "active",
            },
        }
    )

    persisted = persist_work_item_plan(
        store,
        collaboration_run_id="run-plan",
        actor={"id": "user-owner"},
        proposal={
            "work_items": [
                {
                    "id": "design",
                    "owner_role_code": "developer",
                    "reviewer_role_code": "tester",
                },
                {
                    "id": "implement",
                    "owner_role_code": "developer",
                    "reviewer_role_code": "tester",
                },
            ],
            "dependencies": [
                {
                    "predecessor_work_item_id": "design",
                    "successor_work_item_id": "implement",
                }
            ],
        },
    )

    states = {item["title"]: item["status"] for item in persisted["work_items"]}
    assert states == {"design": "ready", "implement": "blocked"}


def test_claim_replays_the_same_lease_before_expiry_without_new_attempt() -> None:
    store = MemoryStore()
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "status": "running",
        "version": 1,
    }
    store.rd_run_seats["seat-dev"] = {
        "id": "seat-dev",
        "collaboration_run_id": "run-1",
        "human_user_id": "user-dev",
        "role_code": "developer",
        "status": "active",
        "subject_type": "human_user",
    }
    store.rd_work_items["work-1"] = {
        "id": "work-1",
        "collaboration_run_id": "run-1",
        "owner_seat_id": "seat-dev",
        "priority": 1,
        "status": "ready",
        "version": 3,
    }

    first = claim_work_item(
        store,
        work_item_id="work-1",
        actor={"id": "user-dev", "roles": ["developer"]},
        expected_version=3,
        lease_seconds=60,
        idempotency_key="claim:work-1:seat-dev:1",
    )
    replay = claim_work_item(
        store,
        work_item_id="work-1",
        actor={"id": "user-dev", "roles": ["developer"]},
        expected_version=3,
        lease_seconds=60,
        idempotency_key="claim:work-1:seat-dev:1",
    )

    assert first["attempt"]["id"] == replay["attempt"]["id"]
    assert first["lease_token"] == replay["lease_token"]
    assert replay["idempotent_replay"] is True
    assert len(store.rd_work_item_attempts) == 1
    assert (
        "lease_token"
        not in next(iter(store.rd_command_idempotency_records.values()))["response_snapshot"]
    )


def test_expired_claim_secret_is_scrubbed_without_removing_command_replay_record() -> None:
    store = MemoryStore()
    store.rd_command_replay_secrets["secret-1"] = {
        "id": "secret-1",
        "command_record_id": "command-1",
        "secret_ciphertext": "ciphertext",
        "expires_at": "2000-01-01T00:00:00+00:00",
        "scrubbed_at": None,
    }

    result = scrub_expired_command_replay_secrets(store)

    assert result["scrubbed_count"] == 1
    assert store.rd_command_replay_secrets["secret-1"]["secret_ciphertext"] is None
    assert store.rd_command_replay_secrets["secret-1"]["scrubbed_at"]


def test_submit_then_request_rework_releases_item_for_a_new_attempt() -> None:
    store = MemoryStore()
    store.rd_collaboration_runs["run-1"] = {"id": "run-1", "status": "running", "version": 1}
    store.rd_run_seats.update(
        {
            "seat-dev": {
                "id": "seat-dev",
                "collaboration_run_id": "run-1",
                "human_user_id": "user-dev",
                "role_code": "developer",
                "status": "active",
                "subject_type": "human_user",
            },
            "seat-reviewer": {
                "id": "seat-reviewer",
                "collaboration_run_id": "run-1",
                "human_user_id": "user-reviewer",
                "role_code": "tester",
                "status": "active",
                "subject_type": "human_user",
            },
        }
    )
    store.rd_work_items["work-1"] = {
        "id": "work-1",
        "collaboration_run_id": "run-1",
        "owner_seat_id": "seat-dev",
        "reviewer_seat_id": "seat-reviewer",
        "status": "ready",
        "version": 1,
        "priority": 1,
    }
    claim = claim_work_item(
        store,
        work_item_id="work-1",
        actor={"id": "user-dev", "roles": ["developer"]},
        expected_version=1,
        lease_seconds=60,
        idempotency_key="claim:work-1:1",
    )

    submitted = complete_attempt(
        store,
        work_item_id="work-1",
        attempt_id=claim["attempt"]["id"],
        lease_token=claim["lease_token"],
        version=2,
        output={"summary": "done"},
        evidence={"tests": ["passed"]},
        idempotency_key="submit:work-1:1",
    )
    reviewed = review_work_item(
        store,
        work_item_id="work-1",
        decision="request_rework",
        comment="补充边界测试",
        actor={"id": "user-reviewer", "roles": ["tester"]},
        version=submitted["work_item"]["version"],
        idempotency_key="review:work-1:rework",
    )

    assert submitted["work_item"]["status"] == "reviewing"
    assert reviewed["work_item"]["status"] == "ready"
    assert reviewed["next_state"] == "rework_required"
    feedback = next(iter(store.role_feedback_records.values()))
    assert feedback["producer_subject_id"] == "user-reviewer"
    assert feedback["producer_seat_id"] == "seat-reviewer"


def test_high_risk_cancel_suspends_item_pending_human_decision() -> None:
    store = MemoryStore()
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "product_id": "product-1",
        "status": "running",
    }
    store.rd_work_items["work-1"] = {
        "id": "work-1",
        "collaboration_run_id": "run-1",
        "status": "running",
        "risk_level": "high",
        "version": 1,
    }

    result = cancel_work_item(
        store,
        work_item_id="work-1",
        reason="停止高风险变更",
        actor={"id": "user-owner", "roles": ["rd_owner"]},
        version=1,
        idempotency_key="cancel:work-1:1",
    )

    assert result["work_item"]["status"] == "waiting_human"
    assert result["decision_request"]["status"] == "pending"
