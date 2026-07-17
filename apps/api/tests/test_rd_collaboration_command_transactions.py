from __future__ import annotations

import inspect
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.core.persistence import PostgresSnapshotRepository
from app.core.persistence_contracts import RdCollaborationRepository
from app.core.repositories.rd_collaboration import (
    RdCollaborationReadRepository,
    RdCollaborationRepositoryError,
    RdCollaborationVersionConflictError,
)
from app.core.repositories.rd_collaboration_shared import RdCollaborationTransaction
from tests.test_rd_collaboration_repository import (
    _accepted_assessment,
    _base_snapshot,
    _decision_record,
    _insert_product_version,
    _insert_requirement,
    _policy_record,
    _run_record,
    _run_scope,
    _seed_exact_run,
    _version_snapshot,
    postgres_admin_url,
    repository,
)
from tests.test_rd_collaboration_repository_hardening import (
    _hash,
    _remove_scope_command,
    _work_item,
)

__all__ = ["postgres_admin_url", "repository"]


TRANSACTION_METHODS = {
    "save_rd_role_definition_record",
    "save_rd_ai_employee_record",
    "save_rd_executor_profile_record",
    "save_rd_policy_role_binding_record",
    "save_rd_task_executor_policy_role_binding_record",
    "save_rd_task_executor_policy_record",
    "freeze_base_policy_snapshot",
    "derive_assessment_policy_snapshot",
    "merge_version_policy_snapshot_with_sources",
    "save_assessment_bundle",
    "create_collaboration_run_with_exact_scope",
    "restart_terminal_collaboration_run",
    "assign_requirement_to_version_and_increment_scope",
    "create_scope_change_request",
    "apply_scope_change_bundle",
    "save_rd_run_seat_record",
    "save_rd_role_session_record",
    "save_rd_work_item_record",
    "save_rd_work_item_dependency_record",
    "save_rd_collaboration_event_record",
    "save_decision_request_record",
    "save_work_item_attempt_bundle",
    "cancel_work_item_bundle",
    "suspend_collaboration_run",
    "apply_decision_bundle",
    "answer_decision_request",
    "expire_and_escalate_decision_request",
    "save_role_feedback_once",
    "save_rd_role_experience_record",
    "decide_role_experience",
}


def _assert_command_rolls_back(
    repository: PostgresSnapshotRepository,
    *,
    prefix: str,
    run_id: str,
    domain_operation: Callable[[RdCollaborationTransaction], str],
) -> None:
    command_record_id = f"{prefix}-command"

    def operation(transaction: RdCollaborationTransaction) -> dict[str, Any]:
        result_id = domain_operation(transaction)
        transaction.save_collaboration_event(
            {
                "id": f"{prefix}-event",
                "collaboration_run_id": run_id,
                "event_type": "command.tested",
                "event_key": f"{prefix}-event",
                "subject_type": "rd_collaboration_run",
                "subject_id": run_id,
                "payload_json": {},
            }
        )
        transaction.save_outbox_event(
            {
                "id": f"{prefix}-outbox",
                "aggregate_type": "rd_collaboration_run",
                "aggregate_id": run_id,
                "event_type": "command.tested",
                "idempotency_key": f"{prefix}-outbox",
                "payload_json": {},
            }
        )
        transaction.save_audit_event(
            {
                "id": f"{prefix}-audit",
                "event_type": "rd.command.tested",
                "actor_id": "user_admin",
                "subject_type": "rd_collaboration_run",
                "subject_id": run_id,
                "payload": {},
            }
        )
        return {
            "result_type": "rd_collaboration",
            "result_id": result_id,
            "http_status": 200,
            "response_json": {"data": {"id": result_id}},
            "claim_replay_secret": {
                "id": f"{prefix}-secret",
                "secret_ciphertext": "ciphertext",
                "key_id": "test-key",
                "expires_at": datetime.now(UTC) + timedelta(minutes=5),
            },
        }

    def fail(stage: str) -> None:
        if stage == "after_secret":
            raise RuntimeError(f"{prefix} injected rollback")

    with pytest.raises(RuntimeError, match=f"{prefix} injected rollback"):
        repository.execute_idempotent_rd_command(
            command_type="atomic-test",
            aggregate_type="rd_collaboration_run",
            aggregate_id=run_id,
            idempotency_key=f"{prefix}-key",
            request_hash=f"{prefix}-request",
            command_record_id=command_record_id,
            operation=operation,
            failure_injection=fail,
        )

    assert repository.get_rd_command_idempotency_record(command_record_id) is None
    assert repository.get_valid_claim_replay_secret(command_record_id) is None
    with repository._connect() as connection:
        assert (
            connection.execute(
                "SELECT id FROM rd_collaboration_events WHERE id = %s", (f"{prefix}-event",)
            ).fetchone()
            is None
        )
        assert (
            connection.execute(
                "SELECT id FROM execution_outbox_events WHERE id = %s", (f"{prefix}-outbox",)
            ).fetchone()
            is None
        )
        assert (
            connection.execute(
                "SELECT id FROM audit_events WHERE id = %s", (f"{prefix}-audit",)
            ).fetchone()
            is None
        )


def test_transaction_exposes_every_task3_command_bundle() -> None:
    assert TRANSACTION_METHODS.issubset(RdCollaborationTransaction.__dict__)


def test_assessment_snapshot_and_start_roll_back_with_command(
    repository: PostgresSnapshotRepository,
) -> None:
    prefix = "command-assessment-start"
    ids = _insert_product_version(repository, prefix=prefix, status="active")
    policy = _policy_record(ids, prefix=prefix)
    base = _base_snapshot(policy, prefix=prefix)
    requirement_id = f"{prefix}-requirement"
    assessment_id = f"{prefix}-assessment"
    _insert_requirement(
        repository,
        ids,
        requirement_id=requirement_id,
        status="planned",
        version_id=ids["version"],
    )
    assessment = _accepted_assessment(
        assessment_id=assessment_id,
        requirement_id=requirement_id,
        snapshot_id=str(base["id"]),
    )
    version_snapshot = _version_snapshot(
        base_snapshot_id=str(base["id"]),
        ids=ids,
        policy_id=str(policy["id"]),
        prefix=prefix,
    )
    run = _run_record(
        ids=ids,
        snapshot_id=str(version_snapshot["id"]),
        prefix=prefix,
    )
    scope = _run_scope(
        assessment_id=assessment_id,
        final_snapshot_id=str(base["id"]),
        requirement_id=requirement_id,
        run_id=str(run["id"]),
        prefix=prefix,
    )

    def domain(transaction: RdCollaborationTransaction) -> str:
        transaction.save_rd_task_executor_policy_record(policy)
        transaction.freeze_base_policy_snapshot(base)
        transaction.save_assessment_bundle(assessment=assessment, opinions=[])
        transaction.merge_version_policy_snapshot_with_sources(
            snapshot=version_snapshot,
            sources=[
                {
                    "id": f"{prefix}-source",
                    "snapshot_id": version_snapshot["id"],
                    "source_snapshot_id": base["id"],
                    "requirement_id": requirement_id,
                    "assessment_id": assessment_id,
                }
            ],
        )
        transaction.create_collaboration_run_with_exact_scope(run=run, scope_rows=[scope])
        return str(run["id"])

    _assert_command_rolls_back(
        repository,
        prefix=prefix,
        run_id=str(run["id"]),
        domain_operation=domain,
    )
    assert repository.get_rd_task_executor_policy(str(policy["id"])) is None
    assert repository.get_rd_policy_snapshot(str(base["id"])) is None
    assert repository.get_requirement_assessment(assessment_id) is None
    assert repository.get_rd_policy_snapshot(str(version_snapshot["id"])) is None
    assert repository.get_rd_collaboration_run(str(run["id"])) is None


def test_terminal_restart_rolls_back_with_command(
    repository: PostgresSnapshotRepository,
) -> None:
    prefix = "command-restart"
    seeded = _seed_exact_run(repository, prefix=prefix, run_status="failed")
    terminal_run_id = str(seeded["run"]["id"])
    run = {
        **seeded["run"],
        "id": f"{prefix}-run-g2",
        "run_generation": 2,
        "supersedes_run_id": terminal_run_id,
        "status": "draft",
    }
    scope = {
        **seeded["scope"],
        "id": f"{prefix}-scope-g2",
        "collaboration_run_id": run["id"],
    }

    def domain(transaction: RdCollaborationTransaction) -> str:
        transaction.restart_terminal_collaboration_run(
            terminal_run_id=terminal_run_id,
            run=run,
            scope_rows=[scope],
        )
        return str(run["id"])

    _assert_command_rolls_back(
        repository,
        prefix=prefix,
        run_id=str(run["id"]),
        domain_operation=domain,
    )
    assert repository.get_rd_collaboration_run(str(run["id"])) is None
    assert repository.get_rd_collaboration_run(terminal_run_id)["status"] == "failed"


def test_scope_proposal_and_apply_roll_back_with_command(
    repository: PostgresSnapshotRepository,
) -> None:
    prefix = "command-scope"
    seeded = _seed_exact_run(repository, prefix=prefix)
    run_id = str(seeded["run"]["id"])
    request_id = f"{prefix}-request"
    command = _remove_scope_command(seeded, request_id=request_id)

    def domain(transaction: RdCollaborationTransaction) -> str:
        transaction.create_scope_change_request(**command)
        transaction.apply_scope_change_bundle(
            scope_change_request_id=request_id,
            decision="approve_apply_and_restart",
            decided_by="user_admin",
            expected_decision_version=1,
        )
        return request_id

    _assert_command_rolls_back(
        repository,
        prefix=prefix,
        run_id=run_id,
        domain_operation=domain,
    )
    assert repository.get_rd_scope_change_request(request_id) is None
    assert repository.get_decision_request(f"{request_id}-decision") is None
    assert repository.get_rd_collaboration_run(run_id)["status"] == "running"
    assert repository.get_rd_collaboration_run(run_id)["run_generation"] == 1


def test_cancel_and_decision_roll_back_with_command(
    repository: PostgresSnapshotRepository,
) -> None:
    prefix = "command-cancel-decision"
    seeded = _seed_exact_run(repository, prefix=prefix)
    run_id = str(seeded["run"]["id"])
    work_item_id = f"{prefix}-work"
    repository.save_rd_work_item_record(
        _work_item(run_id, work_item_id=work_item_id, status="running")
    )
    decision = _decision_record(
        seeded,
        decision_id=f"{prefix}-decision",
        subject_type="rd_work_item",
        subject_id=work_item_id,
    )

    def domain(transaction: RdCollaborationTransaction) -> str:
        transaction.cancel_work_item_bundle(
            work_item_id=work_item_id,
            expected_version=1,
            high_risk=True,
            decision_request=decision,
        )
        transaction.apply_decision_bundle(
            decision_request_id=str(decision["id"]),
            selected_option_code="continue",
            input_json={"modules": []},
            comment=None,
            decided_by="user_admin",
            expected_version=1,
        )
        return work_item_id

    _assert_command_rolls_back(
        repository,
        prefix=prefix,
        run_id=run_id,
        domain_operation=domain,
    )
    assert repository.get_rd_work_item(work_item_id)["status"] == "running"
    assert repository.get_rd_work_item(work_item_id)["version"] == 1
    assert repository.get_decision_request(str(decision["id"])) is None


def test_feedback_experience_and_decision_roll_back_with_command(
    repository: PostgresSnapshotRepository,
) -> None:
    prefix = "command-experience"
    seeded = _seed_exact_run(repository, prefix=prefix)
    run_id = str(seeded["run"]["id"])
    repository.save_rd_collaboration_event_record(
        {
            "id": f"{prefix}-source-event",
            "collaboration_run_id": run_id,
            "event_type": "feedback.source",
            "event_key": f"{prefix}-source-event",
            "subject_type": "rd_collaboration_run",
            "subject_id": run_id,
        }
    )
    feedback = {
        "id": f"{prefix}-feedback",
        "brain_app_id": "rd_brain",
        "product_id": seeded["product"],
        "collaboration_run_id": run_id,
        "feedback_kind": "review",
        "source_event_id": f"{prefix}-source-event",
        "feedback_fingerprint": f"{prefix}-fingerprint",
        "role_code": "developer",
        "human_user_id": "user_admin",
        "strategy_snapshot_id": seeded["version_snapshot"]["id"],
        "producer_subject_type": "human_user",
        "producer_subject_id": "user_admin",
    }
    experience = {
        "id": f"{prefix}-experience",
        "experience_key": f"developer:{prefix}",
        "brain_app_id": "rd_brain",
        "product_scope": [seeded["product"]],
        "role_code": "developer",
        "work_item_type": "implementation",
        "scenario": prefix,
        "risk_scope": {"maximum": "high"},
        "content": {"guidance": "atomic"},
        "strategy_snapshot_id": seeded["version_snapshot"]["id"],
        "confidence": 0.9,
        "status": "pending",
    }
    sources = [
        {
            "id": f"{prefix}-source",
            "experience_id": experience["id"],
            "role_feedback_record_id": feedback["id"],
            "strategy_snapshot_id": seeded["version_snapshot"]["id"],
        }
    ]

    def domain(transaction: RdCollaborationTransaction) -> str:
        transaction.save_role_feedback_once(feedback)
        transaction.save_rd_role_experience_record(experience, sources=sources)
        transaction.decide_role_experience(
            experience_id=str(experience["id"]),
            decision="approve",
            expected_review_version=1,
            reviewer_subject_type="human_user",
            reviewer_subject_id="user_reviewer",
            reviewer_role_code="rd_owner",
            reviewer_seat_id=None,
            require_independent_reviewer=True,
        )
        return str(experience["id"])

    _assert_command_rolls_back(
        repository,
        prefix=prefix,
        run_id=run_id,
        domain_operation=domain,
    )
    assert repository.get_role_feedback_record(str(feedback["id"])) is None
    assert repository.get_rd_role_experience_record(str(experience["id"])) is None


def test_decision_and_scope_request_replays_reject_divergent_provenance(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="replay-provenance")
    decision = _decision_record(seeded, decision_id="replay-provenance-decision")
    repository.save_decision_request_record(decision)
    for mutation in (
        {"subject_id": "different-run"},
        {"product_id": "product_default"},
        {"brain_app_id": "other_brain"},
        {"plan_version": 99},
    ):
        with pytest.raises(RdCollaborationRepositoryError) as decision_error:
            repository.save_decision_request_record({**decision, **mutation})
        assert decision_error.value.code == "RD_IDEMPOTENCY_CONFLICT"

    request_id = "replay-provenance-request"
    command = _remove_scope_command(seeded, request_id=request_id)
    repository.create_scope_change_request(**command)
    with pytest.raises(RdCollaborationRepositoryError) as request_error:
        repository.create_scope_change_request(
            request={**command["request"], "reason": "different reason"},
            operations=command["operations"],
            decision_request=command["decision_request"],
        )
    assert request_error.value.code == "RD_IDEMPOTENCY_CONFLICT"


def test_scope_request_replay_rejects_a_different_decision(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="request-decision-replay")
    request_id = "request-decision-replay-request"
    command = _remove_scope_command(seeded, request_id=request_id)
    repository.create_scope_change_request(**command)
    replacement_decision = {
        **command["decision_request"],
        "id": "request-decision-replay-other-decision",
        "subject_id": request_id,
    }
    with pytest.raises(RdCollaborationRepositoryError) as error:
        repository.create_scope_change_request(
            request={
                **command["request"],
                "decision_request_id": replacement_decision["id"],
            },
            operations=command["operations"],
            decision_request=replacement_decision,
        )
    assert error.value.code == "RD_IDEMPOTENCY_CONFLICT"


def test_scope_creation_rejects_a_poisoned_decision_identity(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="poisoned-decision")
    request_id = "poisoned-decision-request"
    command = _remove_scope_command(seeded, request_id=request_id)
    repository.save_decision_request_record(
        {**command["decision_request"], "subject_id": "other-scope-request"}
    )
    with pytest.raises(RdCollaborationRepositoryError) as error:
        repository.create_scope_change_request(**command)
    assert error.value.code == "RD_IDEMPOTENCY_CONFLICT"
    assert repository.get_rd_scope_change_request(request_id) is None
    assert repository.get_rd_collaboration_run(str(seeded["run"]["id"]))["status"] == "running"


@pytest.mark.parametrize("poison", ["swapped_outcomes", "initial_evidence"])
def test_scope_creation_rejects_poisoned_frozen_decision_provenance(
    repository: PostgresSnapshotRepository,
    poison: str,
) -> None:
    prefix = f"poisoned-frozen-{poison}"
    seeded = _seed_exact_run(repository, prefix=prefix)
    request_id = f"{prefix}-request"
    command = _remove_scope_command(seeded, request_id=request_id)
    incoming_decision = command["decision_request"]
    poisoned_decision = dict(incoming_decision)
    if poison == "swapped_outcomes":
        poisoned_options = [
            {
                **option,
                "outcome": ("reject" if option["outcome"] == "approve" else "approve"),
            }
            for option in incoming_decision["options_json"]
        ]
        poisoned_decision["options_json"] = poisoned_options
        poisoned_decision["options_hash"] = _hash(poisoned_options)
    else:
        poisoned_decision["options_hash"] = _hash(poisoned_decision["options_json"])
        poisoned_decision["evidence_json"] = [{"ref": "poisoned-evidence"}]
    repository.save_decision_request_record(poisoned_decision)

    with pytest.raises(RdCollaborationRepositoryError) as error:
        repository.create_scope_change_request(**command)

    assert error.value.code == "RD_IDEMPOTENCY_CONFLICT"
    assert repository.get_rd_scope_change_request(request_id) is None
    assert repository.get_rd_collaboration_run(str(seeded["run"]["id"]))["status"] == "running"


@pytest.mark.parametrize(
    "selected",
    ["approve_apply_and_restart", "reject_keep_current_scope"],
)
def test_scope_create_exact_replay_survives_terminal_decision_lifecycle(
    repository: PostgresSnapshotRepository,
    selected: str,
) -> None:
    prefix = f"create-after-{selected.split('_', 1)[0]}"
    seeded = _seed_exact_run(repository, prefix=prefix)
    request_id = f"{prefix}-request"
    command = _remove_scope_command(seeded, request_id=request_id)
    repository.create_scope_change_request(**command)
    terminal = repository.apply_scope_change_bundle(
        scope_change_request_id=request_id,
        decision=selected,
        decided_by="user_admin",
        expected_decision_version=1,
    )

    replay = repository.create_scope_change_request(**command)

    assert replay["id"] == request_id
    assert replay["status"] == terminal["scope_change_request"]["status"]
    assert repository.get_decision_request(f"{request_id}-decision")["version"] == 2


def test_decision_exact_creation_replay_survives_answer_refresh(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="decision-after-answer")
    decision = _decision_record(
        seeded,
        decision_id="decision-after-answer-request",
        answer_actor_selector={"user_ids": ["user_admin"]},
    )
    repository.save_decision_request_record(decision)
    repository.suspend_collaboration_run(
        collaboration_run_id=str(seeded["run"]["id"]),
        decision_request_id=str(decision["id"]),
        expected_version=1,
    )
    repository.apply_decision_bundle(
        decision_request_id=str(decision["id"]),
        selected_option_code="more_info",
        input_json=None,
        comment="need details",
        decided_by="user_admin",
        expected_version=1,
    )
    refreshed_options = [
        *decision["options_json"],
        {
            "code": "defer",
            "label": "Defer",
            "outcome": "reject",
            "subject_transition": "cancelled",
            "requires_comment": True,
            "input_schema": {},
            "effect_preview": {},
        },
    ]
    repository.answer_decision_request(
        decision_request_id=str(decision["id"]),
        expected_version=2,
        actor_id="user_admin",
        actor_role_codes=[],
        actor_seat_ids=[],
        answer_json={"detail": "complete"},
        evidence_json=[{"ref": "document-1"}],
        options_json=refreshed_options,
        options_hash="caller-hash-is-ignored",
    )

    replay = repository.save_decision_request_record(decision)

    assert replay["id"] == decision["id"]
    assert replay["status"] == "pending"
    assert replay["version"] == 3
    assert replay["options_json"] == refreshed_options
    assert replay["evidence_json"] == [{"ref": "document-1"}]


@pytest.mark.parametrize(
    ("selected", "opposite"),
    [
        ("approve_apply_and_restart", "reject_keep_current_scope"),
        ("reject_keep_current_scope", "approve_apply_and_restart"),
    ],
)
def test_terminal_scope_replay_requires_same_option_actor_and_version(
    repository: PostgresSnapshotRepository,
    selected: str,
    opposite: str,
) -> None:
    prefix = f"terminal-replay-{selected.split('_', 1)[0]}"
    seeded = _seed_exact_run(repository, prefix=prefix)
    request_id = f"{prefix}-request"
    repository.create_scope_change_request(**_remove_scope_command(seeded, request_id=request_id))
    first = repository.apply_scope_change_bundle(
        scope_change_request_id=request_id,
        decision=selected,
        decided_by="user_admin",
        expected_decision_version=1,
    )
    replay = repository.apply_scope_change_bundle(
        scope_change_request_id=request_id,
        decision=selected,
        decided_by="user_admin",
        expected_decision_version=1,
    )
    assert replay["scope_change_request"]["status"] == first["scope_change_request"]["status"]

    for decision, actor in ((opposite, "user_admin"), (selected, "different-user")):
        with pytest.raises(RdCollaborationRepositoryError) as divergent:
            repository.apply_scope_change_bundle(
                scope_change_request_id=request_id,
                decision=decision,
                decided_by=actor,
                expected_decision_version=1,
            )
        assert divergent.value.code == "RD_IDEMPOTENCY_CONFLICT"

    with pytest.raises(RdCollaborationVersionConflictError):
        repository.apply_scope_change_bundle(
            scope_change_request_id=request_id,
            decision=selected,
            decided_by="user_admin",
            expected_decision_version=999,
        )


@pytest.mark.parametrize(
    ("selected", "opposite"),
    [
        ("approve_apply_and_restart", "reject_keep_current_scope"),
        ("reject_keep_current_scope", "approve_apply_and_restart"),
    ],
)
def test_terminal_scope_replay_checks_option_matches_terminal_outcome(
    repository: PostgresSnapshotRepository,
    selected: str,
    opposite: str,
) -> None:
    prefix = f"terminal-outcome-{selected.split('_', 1)[0]}"
    seeded = _seed_exact_run(repository, prefix=prefix)
    request_id = f"{prefix}-request"
    repository.create_scope_change_request(**_remove_scope_command(seeded, request_id=request_id))
    repository.apply_scope_change_bundle(
        scope_change_request_id=request_id,
        decision=selected,
        decided_by="user_admin",
        expected_decision_version=1,
    )
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            "UPDATE decision_requests SET selected_option_code = %s WHERE id = %s",
            (opposite, f"{request_id}-decision"),
        )

    with pytest.raises(RdCollaborationRepositoryError) as error:
        repository.apply_scope_change_bundle(
            scope_change_request_id=request_id,
            decision=opposite,
            decided_by="user_admin",
            expected_decision_version=1,
        )
    assert error.value.code == "RD_IDEMPOTENCY_CONFLICT"


def test_production_repository_concretely_exposes_protocol_and_legacy_signature(
    repository: PostgresSnapshotRepository,
) -> None:
    protocol_methods = {
        name
        for name, value in RdCollaborationRepository.__dict__.items()
        if not name.startswith("_") and inspect.isfunction(value)
    }
    assert protocol_methods.issubset(dir(PostgresSnapshotRepository))
    assert isinstance(repository, RdCollaborationReadRepository)
    for method_name in protocol_methods:
        protocol_signature = inspect.signature(getattr(RdCollaborationRepository, method_name))
        concrete_signature = inspect.signature(getattr(PostgresSnapshotRepository, method_name))
        assert tuple(protocol_signature.parameters) == tuple(concrete_signature.parameters), (
            method_name
        )
        assert [parameter.kind for parameter in protocol_signature.parameters.values()] == [
            parameter.kind for parameter in concrete_signature.parameters.values()
        ], method_name

    legacy_parameters = inspect.signature(
        PostgresSnapshotRepository.list_rd_task_executor_policies
    ).parameters
    protocol_parameters = inspect.signature(
        RdCollaborationRepository.list_rd_task_executor_policies
    ).parameters
    assert tuple(protocol_parameters) == tuple(legacy_parameters)
    assert tuple(protocol_parameters) == ("self", "product_id", "status", "task_type")

    collaboration_parameters = inspect.signature(
        PostgresSnapshotRepository.list_rd_collaboration_task_executor_policies
    ).parameters
    assert tuple(collaboration_parameters) == (
        "self",
        "brain_app_id",
        "product_id",
        "status",
    )
