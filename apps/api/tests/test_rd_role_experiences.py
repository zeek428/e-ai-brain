from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.core.store import MemoryStore
from app.main import app
from app.services.rd_feedback_attribution import record_role_feedback
from app.services.rd_policy_resolution import merge_policy_payloads
from app.services.rd_policy_validation import PolicyValidationError, validate_unified_policy_payload
from app.services.rd_role_experiences import (
    decide_role_experience,
    generate_role_experience_candidates,
    list_role_experiences_response,
    retrieve_approved_role_experiences,
)


def _policy_snapshot(*, reuse: dict | None = None) -> dict:
    return {
        "id": "snapshot-current",
        "policy_id": "policy-current",
        "policy_version": 7,
        "schema_version": 1,
        "payload_json": {
            "experience_reuse_config": {
                "enabled": True,
                "min_confidence": 0.8,
                "max_age_days": 30,
                "max_items": 1,
                "max_context_tokens": 100,
                "policy_compatibility": "same_policy_version",
                "repository_trust_domains": ["repo:payments"],
                "tool_trust_domains": ["tool:ci"],
                "require_independent_reviewer": True,
                **(reuse or {}),
            }
        },
    }


def _store() -> MemoryStore:
    current_store = MemoryStore()
    current_store.rd_task_executor_policy_snapshots["snapshot-current"] = _policy_snapshot()
    current_store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-a",
        "strategy_snapshot_id": "snapshot-current",
    }
    current_store.rd_work_items["work-1"] = {
        "id": "work-1",
        "collaboration_run_id": "run-1",
        "work_item_type": "implementation",
        "risk_level": "high",
        "objective": "payments",
    }
    current_store.role_feedback_records["feedback-1"] = {
        "id": "feedback-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-a",
        "collaboration_run_id": "run-1",
        "role_code": "developer",
        "work_item_id": "work-1",
        "strategy_snapshot_id": "snapshot-current",
        "evidence_refs": [{"id": "gate-1", "kind": "quality_gate"}],
        "producer_subject_type": "human_user",
        "producer_subject_id": "producer-1",
        "producer_role_code": "tester",
        "producer_seat_id": "seat-tester",
    }
    return current_store


def _candidate(*, candidate_id: str = "experience-1", confidence: float = 0.9) -> dict:
    return {
        "id": candidate_id,
        "experience_key": "developer:payments:implementation",
        "brain_app_id": "rd_brain",
        "product_scope": ["product-a"],
        "role_code": "developer",
        "work_item_type": "implementation",
        "scenario": "payments",
        "risk_scope": {"maximum": "high"},
        "repository_trust_domains": ["repo:payments"],
        "tool_trust_domains": ["tool:ci"],
        "content": {"guidance": "Keep the response idempotent."},
        "evidence_refs": [{"id": "gate-1", "kind": "quality_gate"}],
        "strategy_snapshot_id": "snapshot-current",
        "confidence": confidence,
        "source_feedback_ids": ["feedback-1"],
    }


def _reviewer() -> dict:
    return {
        "id": "reviewer-1",
        "roles": ["rd_owner"],
        "permissions": [
            "delivery.rd_role_experiences.read",
            "delivery.rd_role_experiences.decide",
        ],
        "scope_summary": [
            {"scope_type": "product", "scope_id": "product-a", "access_level": "write"}
        ],
    }


def test_feature_flag_disabled_leaves_feedback_derived_generation_and_routes_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RD_ROLE_EXPERIENCE_ENABLED", "false")
    current_store = _store()

    assert generate_role_experience_candidates(current_store, candidates=[_candidate()]) == []
    assert current_store.rd_role_experience_records == {}

    client = TestClient(app)
    login = client.post(
        "/api/auth/login", json={"username": "admin@example.com", "password": "admin123"}
    )
    response = client.get(
        "/api/delivery/rd-role-experiences",
        headers={"Authorization": f"Bearer {login.json()['data']['access_token']}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RD_ROLE_EXPERIENCE_DISABLED"


def test_candidate_decision_is_versioned_idempotent_and_separated_from_all_producers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RD_ROLE_EXPERIENCE_ENABLED", "true")
    current_store = _store()
    [candidate] = generate_role_experience_candidates(current_store, candidates=[_candidate()])
    assert candidate["status"] == "pending"
    assert candidate["version"] == 1

    with pytest.raises(Exception) as self_review:
        decide_role_experience(
            current_store,
            experience_id=candidate["id"],
            decision="approve",
            comment="self review is forbidden",
            expected_version=1,
            idempotency_key="self-review",
            user={**_reviewer(), "id": "producer-1"},
        )
    assert getattr(self_review.value, "detail", {}).get("code") == "PERMISSION_DENIED"

    approved = decide_role_experience(
        current_store,
        experience_id=candidate["id"],
        decision="approve",
        comment="evidence is sufficient",
        expected_version=1,
        idempotency_key="approve-1",
        user=_reviewer(),
    )
    replay = decide_role_experience(
        current_store,
        experience_id=candidate["id"],
        decision="approve",
        comment="evidence is sufficient",
        expected_version=1,
        idempotency_key="approve-1",
        user=_reviewer(),
    )
    assert (approved["status"], approved["review_version"]) == ("approved", 2)
    assert replay == approved
    assert len(current_store.rd_role_experience_decisions) == 1
    assert current_store.audit_events[-1]["event_type"] == "rd_role_experience.approved"

    retired = decide_role_experience(
        current_store,
        experience_id=candidate["id"],
        decision="retire",
        comment="superseded by newer evidence",
        expected_version=2,
        idempotency_key="retire-1",
        user=_reviewer(),
    )
    assert (retired["status"], retired["review_version"]) == ("retired", 3)


def test_brain_scope_is_server_enforced_for_list_detail_and_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RD_ROLE_EXPERIENCE_ENABLED", "true")
    current_store = _store()
    [allowed] = generate_role_experience_candidates(current_store, candidates=[_candidate()])
    current_store.role_feedback_records["feedback-other"] = {
        **current_store.role_feedback_records["feedback-1"],
        "id": "feedback-other",
        "brain_app_id": "other_brain",
    }
    other = _candidate(candidate_id="experience-other")
    other.update({"brain_app_id": "other_brain", "source_feedback_ids": ["feedback-other"]})
    [hidden] = generate_role_experience_candidates(current_store, candidates=[other])
    scoped_user = {
        **_reviewer(),
        "scope_summary": [
            {"scope_type": "product", "scope_id": "product-a", "access_level": "write"},
            {"scope_type": "brain_app", "scope_id": "rd_brain", "access_level": "read"},
        ],
    }

    listed = list_role_experiences_response(
        current_store=current_store,
        user=scoped_user,
        filters={},
        page=1,
        page_size=10,
    )
    assert [item["id"] for item in listed["items"]] == [allowed["id"]]
    with pytest.raises(Exception) as detail:
        from app.services.rd_role_experiences import get_role_experience_response

        get_role_experience_response(
            current_store=current_store,
            user=scoped_user,
            experience_id=hidden["id"],
        )
    assert getattr(detail.value, "detail", {}).get("code") == "FORBIDDEN"
    with pytest.raises(Exception) as decide:
        decide_role_experience(
            current_store,
            experience_id=hidden["id"],
            decision="approve",
            comment="out of brain scope",
            expected_version=1,
            idempotency_key="other-brain",
            user=scoped_user,
        )
    assert getattr(decide.value, "detail", {}).get("code") == "FORBIDDEN"


def test_independent_reviewer_uses_server_identity_roles_not_optional_client_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RD_ROLE_EXPERIENCE_ENABLED", "true")
    current_store = _store()
    [candidate] = generate_role_experience_candidates(current_store, candidates=[_candidate()])

    with pytest.raises(Exception) as same_producer_role:
        decide_role_experience(
            current_store,
            experience_id=candidate["id"],
            decision="approve",
            comment="same role cannot review",
            expected_version=1,
            idempotency_key="same-producer-role",
            user={**_reviewer(), "roles": ["tester"]},
        )
    assert getattr(same_producer_role.value, "detail", {}).get("code") == "PERMISSION_DENIED"


def test_experience_reuse_capacity_uses_items_and_tokens_with_strict_policy_validation() -> None:
    with pytest.raises(PolicyValidationError):
        validate_unified_policy_payload(
            {
                "name": "legacy capacity",
                "role_bindings": [],
                "experience_reuse_config": {"enabled": True, "max_capacity": 4},
            }
        )
    with pytest.raises(PolicyValidationError):
        validate_unified_policy_payload(
            {
                "name": "bad token capacity",
                "role_bindings": [],
                "experience_reuse_config": {
                    "enabled": True,
                    "max_items": 2,
                    "max_context_tokens": "100",
                },
            }
        )
    merged = merge_policy_payloads(
        [
            {"experience_reuse_config": {"max_items": 5, "max_context_tokens": 600}},
            {"experience_reuse_config": {"max_items": 2, "max_context_tokens": 150}},
        ]
    )
    assert merged["experience_reuse_config"] == {"max_items": 2, "max_context_tokens": 150}


def test_persisted_feedback_generates_one_pending_governed_candidate_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RD_ROLE_EXPERIENCE_ENABLED", "true")
    current_store = _store()
    current_store.rd_run_seats.update(
        {
            "seat-tester": {
                "id": "seat-tester",
                "collaboration_run_id": "run-1",
                "role_code": "tester",
                "subject_type": "human_user",
                "human_user_id": "tester-1",
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
    feedback = record_role_feedback(
        current_store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
        source_event_id="review-event-1",
        feedback_kind="review_approved",
        producer={
            "subject_type": "human_user",
            "subject_id": "tester-1",
            "role_code": "tester",
            "seat_id": "seat-tester",
        },
        attributed={
            "subject_type": "ai_employee",
            "subject_id": "employee-1",
            "role_code": "developer",
            "seat_id": "seat-developer",
        },
        executor_profile_id="executor-1",
        actor_id="tester-1",
        evidence_refs=[{"id": "review-event-1", "kind": "review"}],
    )
    assert feedback["id"]
    assert len(current_store.rd_role_experience_records) == 1
    candidate = next(iter(current_store.rd_role_experience_records.values()))
    assert candidate["status"] == "pending"
    assert next(iter(current_store.rd_role_experience_sources.values()))[
        "role_feedback_record_id"
    ] == feedback["id"]


def test_list_and_reuse_filter_scope_including_policy_trust_and_token_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RD_ROLE_EXPERIENCE_ENABLED", "true")
    current_store = _store()
    approved_ids = []
    for candidate_id, confidence, guidance in (
        ("experience-a", 0.95, "idempotency evidence"),
        ("experience-b", 0.90, "short guidance"),
        ("experience-c", 0.99, "wrong trust domain"),
    ):
        proposal = _candidate(candidate_id=candidate_id, confidence=confidence)
        proposal["content"] = {"guidance": guidance}
        if candidate_id == "experience-c":
            proposal["repository_trust_domains"] = ["repo:other"]
        [created] = generate_role_experience_candidates(current_store, candidates=[proposal])
        approved = decide_role_experience(
            current_store,
            experience_id=created["id"],
            decision="approve",
            comment="approved",
            expected_version=1,
            idempotency_key=f"approve-{candidate_id}",
            user=_reviewer(),
        )
        approved_ids.append(approved["id"])

    page = list_role_experiences_response(
        current_store=current_store,
        user=_reviewer(),
        filters={
            "brain_app_id": "rd_brain",
            "product_id": "product-a",
            "role_code": "developer",
            "work_item_type": "implementation",
            "scenario": "payments",
            "risk_level": "high",
            "repository_trust_domain": "repo:payments",
            "tool_trust_domain": "tool:ci",
            "minimum_confidence": 0.8,
            "status": "approved",
            "evidence_subject_id": "producer-1",
        },
        page=1,
        page_size=10,
    )
    assert {item["id"] for item in page["items"]} == set(approved_ids[:2])

    context = retrieve_approved_role_experiences(
        current_store,
        current_policy_snapshot_id="snapshot-current",
        scope={
            "brain_app_id": "rd_brain",
            "product_id": "product-a",
            "role_code": "developer",
            "work_item_type": "implementation",
            "scenario": "payments",
            "risk_level": "high",
            "repository_trust_domain": "repo:payments",
            "tool_trust_domain": "tool:ci",
        },
        user=_reviewer(),
    )
    assert [item["experience_id"] for item in context] == ["experience-a"]
    assert context[0]["version"] == 1
    assert context[0]["evidence_refs"] == [{"id": "gate-1", "kind": "quality_gate"}]
    assert "policy" not in current_store.rd_task_executor_policy_snapshots["snapshot-current"]

    incompatible = deepcopy(current_store.rd_task_executor_policy_snapshots["snapshot-current"])
    incompatible["id"] = "snapshot-incompatible"
    incompatible["policy_version"] = 8
    current_store.rd_task_executor_policy_snapshots[incompatible["id"]] = incompatible
    assert (
        retrieve_approved_role_experiences(
            current_store,
            current_policy_snapshot_id=incompatible["id"],
            scope={
                "brain_app_id": "rd_brain",
                "product_id": "product-a",
                "role_code": "developer",
                "work_item_type": "implementation",
                "scenario": "payments",
                "risk_level": "high",
                "repository_trust_domain": "repo:payments",
                "tool_trust_domain": "tool:ci",
            },
            user=_reviewer(),
        )
        == []
    )


def test_governed_api_lists_detail_and_decides_with_version_and_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RD_ROLE_EXPERIENCE_ENABLED", "true")
    original_store = app.state.store
    current_store = _store()
    app.state.store = current_store
    try:
        [candidate] = generate_role_experience_candidates(current_store, candidates=[_candidate()])
        client = TestClient(app)
        login = client.post(
            "/api/auth/login", json={"username": "admin@example.com", "password": "admin123"}
        )
        headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
        listed = client.get(
            "/api/delivery/rd-role-experiences?product_id=product-a&role_code=developer",
            headers=headers,
        )
        assert listed.status_code == 200, listed.text
        assert listed.json()["data"]["total"] == 1
        detail = client.get(f"/api/delivery/rd-role-experiences/{candidate['id']}", headers=headers)
        assert detail.status_code == 200, detail.text
        assert detail.json()["data"]["sources"][0]["feedback_record_id"] == "feedback-1"
        decided = client.post(
            f"/api/delivery/rd-role-experiences/{candidate['id']}/decide",
            headers=headers,
            json={
                "decision": "approve",
                "comment": "approved",
                "version": 1,
                "idempotency_key": "api-approve",
            },
        )
        assert decided.status_code == 200, decided.text
        assert decided.json()["data"]["status"] == "approved"
        stale = client.post(
            f"/api/delivery/rd-role-experiences/{candidate['id']}/decide",
            headers=headers,
            json={
                "decision": "retire",
                "comment": "stale",
                "version": 1,
                "idempotency_key": "api-retire",
            },
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "RD_VERSION_CONFLICT"
    finally:
        app.state.store = original_store
