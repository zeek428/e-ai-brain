from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


class AssessmentRepository:
    """Small repository double: production services only receive repository-backed stores."""

    def __init__(self) -> None:
        self.assessments: dict[str, dict] = {}
        self.opinions: dict[str, dict] = {}
        self.requirements: dict[str, dict] = {}
        self.commands: dict[tuple[str, str, str], dict] = {}
        self.snapshots: dict[str, dict] = {}
        self.policy = {
            "id": "policy_requirement_assessment",
            "policy_version": 1,
            "created_by": "user_owner",
            "brain_app_id": "rd_brain",
            "name": "Requirement assessment policy",
            "product_id": "product_1",
            "status": "active",
            "matching_config": {"task_types": ["development_planning"]},
            "assessment_config": {},
            "iteration_config": {},
            "delivery_target": "ready_for_release",
            "team_config": {"required_role_codes": ["architect"]},
            "autonomy_config": {"mode": "single_pass"},
            "quality_gate_config": {},
            "git_config": {},
            "experience_reuse_config": {},
            "deployment_config": {},
            "role_bindings": [],
        }
        self.bindings = [
            {
                "id": "binding_architect",
                "role_code": "architect",
                "actor_mode": "ai",
                "candidate_ai_employee_ids": ["ai_architect"],
                "primary_executor_profile_id": "executor_architect",
                "fallback_executor_profile_ids": [],
                "status": "active",
            }
        ]
        self.policy["role_bindings"] = deepcopy(self.bindings)
        self.roles = {
            "architect": {
                "id": "role_architect",
                "brain_app_id": "rd_brain",
                "code": "architect",
                "status": "active",
                "assignable_subject_types": ["ai_employee"],
            }
        }
        self.employees = {
            "ai_architect": {
                "id": "ai_architect",
                "brain_app_id": "rd_brain",
                "status": "active",
            }
        }
        self.profiles = {
            "executor_architect": {
                "id": "executor_architect",
                "brain_app_id": "rd_brain",
                "status": "active",
                "health_status": "healthy",
                "supported_role_codes": ["architect"],
            }
        }

    def list_rd_collaboration_task_executor_policies(self, **_filters):
        return [deepcopy(self.policy)]

    def list_rd_policy_role_bindings(self, _policy_id: str):
        return deepcopy(self.bindings)

    def freeze_base_policy_snapshot(self, snapshot: dict):
        existing = next(
            (
                row
                for row in self.snapshots.values()
                if row["snapshot_kind"] == "base"
                and row["policy_id"] == snapshot["policy_id"]
                and row["policy_version"] == snapshot["policy_version"]
            ),
            None,
        )
        if existing:
            return deepcopy(existing)
        self.snapshots[snapshot["id"]] = deepcopy(snapshot)
        return deepcopy(snapshot)

    def get_rd_policy_snapshot(self, snapshot_id: str):
        snapshot = self.snapshots.get(snapshot_id)
        return deepcopy(snapshot) if snapshot else None

    def derive_assessment_policy_snapshot(self, *, base_snapshot_id: str, snapshot: dict):
        assert snapshot["parent_snapshot_id"] == base_snapshot_id
        self.snapshots[snapshot["id"]] = deepcopy(snapshot)
        return deepcopy(snapshot)

    def list_rd_role_definitions(self, **_filters):
        return deepcopy(list(self.roles.values()))

    def get_rd_ai_employee(self, employee_id: str):
        return deepcopy(self.employees.get(employee_id))

    def get_rd_executor_profile(self, profile_id: str):
        return deepcopy(self.profiles.get(profile_id))

    def save_assessment_bundle(
        self, *, assessment: dict, opinions: list[dict], snapshots=None, executions=None
    ):
        self.assessments[assessment["id"]] = deepcopy(assessment)
        for opinion in opinions:
            self.opinions[opinion["id"]] = deepcopy(opinion)
        return {
            "assessment": deepcopy(assessment),
            "opinions": deepcopy(opinions),
            "executions": deepcopy(executions or []),
        }

    def get_requirement_assessment(self, assessment_id: str):
        item = self.assessments.get(assessment_id)
        return deepcopy(item) if item else None

    def list_requirement_assessments(self, requirement_id: str):
        return [
            deepcopy(item)
            for item in self.assessments.values()
            if item["requirement_id"] == requirement_id
        ]

    def list_requirement_assessment_opinions(self, assessment_id: str):
        return [
            deepcopy(item)
            for item in self.opinions.values()
            if item["assessment_id"] == assessment_id
        ]

    def update_requirement_assessment(
        self, assessment: dict, *, expected_version: int, requirement=None, audit_event=None
    ):
        existing = self.assessments[assessment["id"]]
        if existing.get("version", 1) != expected_version:
            from app.core.repositories.rd_collaboration_shared import (
                RdCollaborationVersionConflictError,
            )

            raise RdCollaborationVersionConflictError(existing.get("version", 1))
        persisted = {**deepcopy(assessment), "version": expected_version + 1}
        self.assessments[assessment["id"]] = persisted
        if requirement is not None:
            self.requirements[requirement["id"]] = deepcopy(requirement)
        return deepcopy(persisted)

    def update_requirement_assessment_opinion(self, opinion: dict):
        self.opinions[opinion["id"]] = deepcopy(opinion)
        return deepcopy(opinion)

    def submit_assessment_answers(
        self, *, assessment_id: str, expected_version: int, answers: dict, actor_id: str
    ):
        assessment = self.assessments[assessment_id]
        if assessment.get("version", 1) != expected_version:
            from app.core.repositories.rd_collaboration_shared import (
                RdCollaborationVersionConflictError,
            )

            raise RdCollaborationVersionConflictError(assessment.get("version", 1))
        next_round = assessment.get("opinion_round", 1) + 1
        saved = {
            **assessment,
            "requirement_revision": assessment.get("requirement_revision", 1) + 1,
            "opinion_round": next_round,
            "status": "evaluating",
            "version": expected_version + 1,
            "structured_assessment": {"answers": deepcopy(answers), "answers_actor_id": actor_id},
        }
        self.assessments[assessment_id] = saved
        return deepcopy(saved)

    def load_requirements(self):
        return {"requirements": deepcopy(self.requirements)}

    def get_requirement_assessment_command(
        self, *, assessment_id: str, operation: str, idempotency_key: str
    ):
        command = self.commands.get((assessment_id, operation, idempotency_key))
        return deepcopy(command) if command else None

    def save_requirement_assessment_command(self, command: dict):
        key = (command["assessment_id"], command["operation"], command["idempotency_key"])
        self.commands.setdefault(key, deepcopy(command))
        return deepcopy(self.commands[key])

    def execute_requirement_assessment_command(self, command: dict, effect):
        key = (command["assessment_id"], command["operation"], command["idempotency_key"])
        existing = self.commands.get(key)
        if existing:
            if existing["request_hash"] != command["request_hash"]:
                raise AssertionError("idempotency request hash mismatch")
            return deepcopy(existing["response_snapshot"])

        repository = self

        class Transaction:
            def get_rd_policy_snapshot(self, snapshot_id: str):
                return repository.get_rd_policy_snapshot(snapshot_id)

            def derive_assessment_policy_snapshot(self, **kwargs):
                return repository.derive_assessment_policy_snapshot(**kwargs)

            def advance_assessment_policy_round(
                self, *, assessment: dict, expected_version: int, opinions: list, executions: list
            ):
                current = repository.assessments[assessment["id"]]
                assert current["version"] == expected_version
                persisted = {**deepcopy(assessment), "version": expected_version + 1}
                repository.assessments[assessment["id"]] = persisted
                for opinion in opinions:
                    repository.opinions[opinion["id"]] = deepcopy(opinion)
                return deepcopy(persisted)

        response = effect(Transaction())
        self.commands[key] = {**deepcopy(command), "response_snapshot": deepcopy(response)}
        return response


class RepositoryStore:
    def __init__(self, repository: AssessmentRepository) -> None:
        self.repository = repository
        self._next = 0

    def new_id(self, prefix: str) -> str:
        self._next += 1
        return f"{prefix}_{self._next}"


def test_assessment_resolves_initial_policy_before_ai_roles():
    from app.services.requirement_assessments import start_requirement_assessment

    store = RepositoryStore(AssessmentRepository())
    requirement = {
        "id": "requirement_1",
        "brain_app_id": "rd_brain",
        "product_id": "product_1",
        "status": "submitted",
        "revision": 1,
    }

    assessment = start_requirement_assessment(
        current_store=store,
        requirement=requirement,
        user={
            "id": "user_owner",
            "roles": ["product_owner"],
            "permissions": [],
            "scope_summary": [
                {"scope_type": "product", "scope_id": "product_1", "access_level": "write"}
            ],
        },
    )

    assert assessment["initial_policy_snapshot"]["snapshot_kind"] == "base"
    assert assessment["initial_policy_snapshot"]["resolution_revision"] == 0
    assert assessment["status"] == "evaluating"


def test_policy_re_evaluation_round_reassigns_every_new_active_qualified_role():
    from app.services.requirement_assessments import (
        _new_opinion_round,
        start_requirement_assessment,
    )

    repository = AssessmentRepository()
    repository.policy["team_config"] = {"required_role_codes": ["architect", "reviewer"]}
    repository.bindings.append(
        {
            "id": "binding_reviewer",
            "role_code": "reviewer",
            "actor_mode": "ai",
            "candidate_ai_employee_ids": ["ai_reviewer"],
            "primary_executor_profile_id": "executor_reviewer",
            "fallback_executor_profile_ids": [],
            "status": "active",
        }
    )
    repository.policy["role_bindings"] = deepcopy(repository.bindings)
    repository.roles["reviewer"] = {
        "id": "role_reviewer",
        "brain_app_id": "rd_brain",
        "code": "reviewer",
        "status": "active",
        "assignable_subject_types": ["ai_employee"],
    }
    repository.employees["ai_reviewer"] = {
        "id": "ai_reviewer",
        "brain_app_id": "rd_brain",
        "status": "active",
    }
    repository.profiles["executor_reviewer"] = {
        "id": "executor_reviewer",
        "brain_app_id": "rd_brain",
        "status": "active",
        "health_status": "healthy",
        "supported_role_codes": ["reviewer"],
    }
    store = RepositoryStore(repository)
    requirement = {
        "id": "requirement_1",
        "brain_app_id": "rd_brain",
        "product_id": "product_1",
        "status": "submitted",
    }
    owner = {
        "id": "user_owner",
        "roles": ["product_owner"],
        "permissions": [],
        "scope_summary": [
            {"scope_type": "product", "scope_id": "product_1", "access_level": "write"}
        ],
    }
    assessment = start_requirement_assessment(
        current_store=store, requirement=requirement, user=owner
    )
    round_two, executions = _new_opinion_round(
        current_store=store,
        repository=repository,
        requirement=requirement,
        assessment=assessment,
        snapshot=assessment["initial_policy_snapshot"],
        user=owner,
        opinion_round=2,
    )

    assert {item["role_code"] for item in round_two} == {"architect", "reviewer"}
    assert all(item["opinion_round"] == 2 for item in round_two)
    assert {item["role_code"] for item in executions} == {"architect", "reviewer"}


def test_policy_proposal_aggregation_fails_closed_for_incomparable_or_excess_risk():
    from app.services.requirement_assessments import _aggregate_policy_proposal

    snapshot = {"payload_json": {"quality_gate_config": {"max_risk": "medium"}}}
    try:
        _aggregate_policy_proposal(
            snapshot=snapshot,
            opinions=[
                {
                    "role_code": "architect",
                    "policy_proposal_json": {"autonomy_config": {"mode": "single_pass"}},
                    "outcome_code": "accept",
                },
                {
                    "role_code": "reviewer",
                    "policy_proposal_json": {"autonomy_config": {"mode": "supervised"}},
                    "outcome_code": "accept",
                },
            ],
        )
    except Exception as exc:
        assert getattr(exc, "detail", {}).get("code") == (
            "ASSESSMENT_INCOMPARABLE_HUMAN_DECISION_REQUIRED"
        )
    else:
        raise AssertionError("incomparable policy proposals must require a human decision")

    try:
        _aggregate_policy_proposal(
            snapshot=snapshot,
            opinions=[
                {
                    "role_code": "architect",
                    "policy_proposal_json": {},
                    "outcome_code": "accept",
                    "risk_level": "high",
                }
            ],
        )
    except Exception as exc:
        assert getattr(exc, "detail", {}).get("code") == ("ASSESSMENT_RISK_HUMAN_DECISION_REQUIRED")
    else:
        raise AssertionError("risk above the frozen policy limit must require a human decision")


def test_policy_proposal_creates_versioned_snapshot_and_requires_second_round():
    from app.services.rd_policy_resolution import resolve_initial_rd_policy
    from app.services.requirement_assessments import finalize_requirement_assessment

    repository = AssessmentRepository()
    repository.policy["quality_gate_config"] = {"max_risk": "high"}
    store = RepositoryStore(repository)
    requirement = {
        "id": "requirement_1",
        "brain_app_id": "rd_brain",
        "product_id": "product_1",
        "status": "submitted",
    }
    owner = {
        "id": "user_owner",
        "roles": ["product_owner"],
        "permissions": [],
        "scope_summary": [
            {"scope_type": "product", "scope_id": "product_1", "access_level": "write"}
        ],
    }
    base = resolve_initial_rd_policy(store, requirement=requirement)
    proposal = deepcopy(base["payload_json"])
    proposal["quality_gate_config"] = {"max_risk": "medium"}
    repository.requirements["requirement_1"] = requirement
    repository.assessments["assessment_1"] = {
        "id": "assessment_1",
        "requirement_id": "requirement_1",
        "requirement_revision": 1,
        "product_id": "product_1",
        "initial_strategy_snapshot_id": base["id"],
        "final_strategy_snapshot_id": base["id"],
        "strategy_snapshot_id": base["id"],
        "opinion_round": 1,
        "status": "waiting_human",
        "version": 1,
    }
    repository.opinions["opinion_1"] = {
        "id": "opinion_1",
        "assessment_id": "assessment_1",
        "role_code": "architect",
        "opinion_round": 1,
        "strategy_snapshot_id": base["id"],
        "conclusion_json": {"recommendation": "accept"},
        "policy_proposal_json": proposal,
        "outcome_code": "accept",
        "risk_level": "low",
    }

    result = finalize_requirement_assessment(
        current_store=store, assessment_id="assessment_1", expected_version=1, user=owner
    )

    assert result["policy_re_evaluation_required"] is True
    assert result["opinion_round"] == 2
    assert result["strategy_snapshot_id"] != base["id"]
    assert result["opinions"][0]["strategy_snapshot_id"] == result["strategy_snapshot_id"]


def test_assessment_opinion_rejects_ai_employee_bearer_identity():
    from app.services.requirement_assessments import (
        record_assessment_opinion,
        start_requirement_assessment,
    )

    store = RepositoryStore(AssessmentRepository())
    owner = {
        "id": "user_owner",
        "roles": ["product_owner"],
        "permissions": [],
        "scope_summary": [
            {"scope_type": "product", "scope_id": "product_1", "access_level": "write"}
        ],
    }
    assessment = start_requirement_assessment(
        current_store=store,
        requirement={
            "id": "requirement_1",
            "brain_app_id": "rd_brain",
            "product_id": "product_1",
            "status": "submitted",
        },
        user=owner,
    )

    try:
        record_assessment_opinion(
            current_store=store,
            assessment_id=assessment["id"],
            payload={"role_code": "architect", "conclusion_json": {"recommendation": "accept"}},
            user={**owner, "id": "unassigned"},
        )
    except Exception as exc:
        assert getattr(exc, "detail", {}).get("code") == "ASSESSMENT_OPINION_ACTOR_INVALID"
    else:
        raise AssertionError("unassigned actor must not submit an assessment opinion")

    try:
        record_assessment_opinion(
            current_store=store,
            assessment_id=assessment["id"],
            payload={"role_code": "architect", "conclusion_json": {"recommendation": "accept"}},
            user={**owner, "id": "ai_architect"},
        )
    except Exception as exc:
        assert getattr(exc, "detail", {}).get("code") == "ASSESSMENT_OPINION_ACTOR_INVALID"
    else:
        raise AssertionError("AI employee IDs must not be accepted as bearer user identities")


def test_assessment_decision_accepts_only_canonical_actions_with_optimistic_locking():
    from app.services.requirement_assessments import decide_requirement_assessment

    store = RepositoryStore(AssessmentRepository())
    assessment = {
        "id": "assessment_1",
        "requirement_id": "requirement_1",
        "requirement_revision": 1,
        "status": "waiting_human",
        "version": 1,
        "product_id": "product_1",
    }
    store.repository.assessments[assessment["id"]] = assessment
    user = {
        "id": "user_owner",
        "roles": ["product_owner"],
        "permissions": [],
        "scope_summary": [
            {"scope_type": "product", "scope_id": "product_1", "access_level": "write"}
        ],
    }

    try:
        decide_requirement_assessment(
            current_store=store,
            assessment_id="assessment_1",
            payload={"action": "approve", "expected_version": 1},
            user=user,
        )
    except Exception as exc:
        assert getattr(exc, "detail", {}).get("code") == "VALIDATION_ERROR"
    else:
        raise AssertionError("non-canonical decision action must be rejected")

    try:
        decide_requirement_assessment(
            current_store=store,
            assessment_id="assessment_1",
            payload={"action": "defer", "expected_version": 2},
            user=user,
        )
    except Exception as exc:
        assert getattr(exc, "detail", {}).get("code") == "RD_VERSION_CONFLICT"
    else:
        raise AssertionError("stale decision version must be rejected")


def test_assessment_persistence_contract_has_versioned_commands_and_requirement_revision():
    migration = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "db"
        / "migrations"
        / "111_requirement_assessment_orchestration.sql"
    )
    body = migration.read_text(encoding="utf-8").lower()

    assert "add column if not exists assessment_revision" in body
    assert "add column if not exists version bigint" in body
    assert "create table if not exists requirement_assessment_commands" in body
    assert "request_hash" in body and "response_snapshot" in body
    assert "unique (assessment_id, operation, idempotency_key)" in body

    persistence = (
        Path(__file__).resolve().parents[1] / "app" / "core" / "persistence.py"
    ).read_text(encoding="utf-8")
    assert '"111_requirement_assessment_orchestration.sql"' in persistence


def test_assessment_start_request_forbids_strategy_id():
    client = TestClient(app)
    login = client.post(
        "/api/auth/login", json={"username": "admin@example.com", "password": "admin123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    response = client.post(
        "/api/requirements/requirement_1/assessments",
        json={"strategy_id": "caller_selected_policy"},
        headers=headers,
    )

    assert response.status_code == 422


def test_answers_create_a_new_requirement_and_opinion_round():
    from app.services.requirement_assessments import submit_assessment_answers

    store = RepositoryStore(AssessmentRepository())
    store.repository.assessments["assessment_1"] = {
        "id": "assessment_1",
        "requirement_id": "requirement_1",
        "requirement_revision": 1,
        "opinion_round": 1,
        "status": "needs_info",
        "version": 1,
        "product_id": "product_1",
    }
    user = {
        "id": "user_owner",
        "roles": ["product_owner"],
        "permissions": [],
        "scope_summary": [
            {"scope_type": "product", "scope_id": "product_1", "access_level": "write"}
        ],
    }

    advanced = submit_assessment_answers(
        current_store=store,
        assessment_id="assessment_1",
        payload={"answers": {"dependency": "confirmed"}, "expected_version": 1},
        user=user,
    )

    assert advanced["requirement_revision"] == 2
    assert advanced["opinion_round"] == 2
    assert advanced["status"] == "evaluating"


def test_accept_finalization_requires_all_current_opinions_and_advances_requirement():
    from app.services.rd_policy_resolution import resolve_initial_rd_policy
    from app.services.requirement_assessments import finalize_requirement_assessment

    store = RepositoryStore(AssessmentRepository())
    base = resolve_initial_rd_policy(
        store,
        requirement={"id": "requirement_1", "product_id": "product_1", "brain_app_id": "rd_brain"},
    )
    store.repository.assessments["assessment_1"] = {
        "id": "assessment_1",
        "requirement_id": "requirement_1",
        "requirement_revision": 1,
        "initial_strategy_snapshot_id": base["id"],
        "final_strategy_snapshot_id": base["id"],
        "strategy_snapshot_id": base["id"],
        "opinion_round": 1,
        "status": "waiting_human",
        "version": 1,
        "product_id": "product_1",
    }
    store.repository.requirements["requirement_1"] = {"id": "requirement_1", "status": "submitted"}
    store.repository.opinions["opinion_1"] = {
        "id": "opinion_1",
        "assessment_id": "assessment_1",
        "role_code": "architect",
        "opinion_round": 1,
        "conclusion_json": {"recommendation": "accept"},
        "strategy_snapshot_id": base["id"],
    }
    user = {
        "id": "user_owner",
        "roles": ["product_owner"],
        "permissions": [],
        "scope_summary": [
            {"scope_type": "product", "scope_id": "product_1", "access_level": "write"}
        ],
    }

    finalized = finalize_requirement_assessment(
        current_store=store, assessment_id="assessment_1", expected_version=1, user=user
    )

    assert finalized["status"] == "accepted"
    assert finalized["final_strategy_snapshot_id"] == base["id"]
    assert store.repository.requirements["requirement_1"]["status"] == "approved"


def test_decision_idempotency_replays_the_persisted_response_snapshot():
    from app.services.requirement_assessments import decide_requirement_assessment

    store = RepositoryStore(AssessmentRepository())
    store.repository.assessments["assessment_1"] = {
        "id": "assessment_1",
        "requirement_id": "requirement_1",
        "status": "waiting_human",
        "version": 1,
        "product_id": "product_1",
    }
    user = {
        "id": "user_owner",
        "roles": ["product_owner"],
        "permissions": [],
        "scope_summary": [
            {"scope_type": "product", "scope_id": "product_1", "access_level": "write"}
        ],
    }
    payload = {"action": "defer", "expected_version": 1, "idempotency_key": "defer-once"}

    first = decide_requirement_assessment(
        current_store=store, assessment_id="assessment_1", payload=payload, user=user
    )
    replay = decide_requirement_assessment(
        current_store=store, assessment_id="assessment_1", payload=payload, user=user
    )

    assert replay == first
    assert store.repository.assessments["assessment_1"]["version"] == 2
