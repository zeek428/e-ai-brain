from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services.rd_policy_resolution import PolicyResolutionError, merge_policy_payloads

_TERMINAL_RUN_STATUSES = {"completed", "failed", "cancelled"}
_RISK_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def _records(store: Any, name: str) -> dict[str, dict[str, Any]]:
    records = getattr(store, name, None)
    if not isinstance(records, dict):
        records = {}
        setattr(store, name, records)
    return records


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _idempotency_key(requirement_id: str, assessment_id: str) -> str:
    return f"requirement:{requirement_id}:assessment:{assessment_id}"


def _accepted_assessment_for_requirement(
    store: Any,
    *,
    assessment_id: str,
    requirement: dict[str, Any],
) -> dict[str, Any]:
    assessment = _records(store, "requirement_assessments").get(assessment_id)
    if assessment is None or assessment.get("requirement_id") != requirement["id"]:
        raise api_error(404, "NOT_FOUND", "Accepted requirement assessment not found")
    if assessment.get("status") != "accepted":
        raise api_error(
            409,
            "ASSESSMENT_STATE_INVALID",
            "Only accepted assessments can be grouped into an iteration",
        )
    requirement_revision = int(requirement.get("assessment_revision") or 1)
    if int(assessment.get("requirement_revision") or 1) != requirement_revision:
        raise api_error(
            409,
            "ASSESSMENT_PROVENANCE_INVALID",
            "Accepted assessment does not match the current requirement revision",
        )
    if not assessment.get("final_strategy_snapshot_id"):
        raise api_error(
            409,
            "ASSESSMENT_PROVENANCE_INVALID",
            "Accepted assessment has no final strategy snapshot",
        )
    return assessment


def _snapshot(store: Any, snapshot_id: str) -> dict[str, Any]:
    snapshot = _records(store, "rd_task_executor_policy_snapshots").get(snapshot_id)
    if snapshot is None:
        repository = getattr(store, "repository", None)
        get_snapshot = getattr(repository, "get_rd_policy_snapshot", None)
        loaded = get_snapshot(snapshot_id) if callable(get_snapshot) else None
        snapshot = loaded if isinstance(loaded, dict) else None
    if snapshot is None:
        raise api_error(
            409,
            "ASSESSMENT_PROVENANCE_INVALID",
            "Final strategy snapshot is unavailable",
        )
    if not snapshot.get("policy_id") or not snapshot.get("policy_version"):
        raise api_error(
            409,
            "ASSESSMENT_PROVENANCE_INVALID",
            "Final strategy snapshot has no policy identity",
        )
    return snapshot


def _accepted_member_assessment(
    store: Any,
    requirement: dict[str, Any],
) -> dict[str, Any] | None:
    required_revision = int(requirement.get("assessment_revision") or 1)
    matching = [
        item
        for item in _records(store, "requirement_assessments").values()
        if item.get("requirement_id") == requirement.get("id")
        and item.get("status") == "accepted"
        and int(item.get("requirement_revision") or 1) == required_revision
        and item.get("final_strategy_snapshot_id")
    ]
    if not matching:
        repository = getattr(store, "repository", None)
        list_assessments = getattr(repository, "list_requirement_assessments", None)
        loaded = list_assessments(str(requirement["id"])) if callable(list_assessments) else []
        matching = [
            item
            for item in loaded
            if isinstance(item, dict)
            and item.get("status") == "accepted"
            and int(item.get("requirement_revision") or 1) == required_revision
            and item.get("final_strategy_snapshot_id")
        ]
    if not matching:
        return None
    return max(matching, key=lambda item: str(item.get("updated_at") or item.get("id")))


def _version_members(store: Any, version_id: str) -> list[dict[str, Any]]:
    return sorted(
        [
            item
            for item in _records(store, "requirements").values()
            if item.get("version_id") == version_id
        ],
        key=lambda item: str(item.get("id")),
    )


def _version_has_active_run(store: Any, version_id: str) -> bool:
    memory_runs = _records(store, "rd_collaboration_runs").values()
    if any(
        item.get("product_version_id") == version_id
        and item.get("status") not in _TERMINAL_RUN_STATUSES
        for item in memory_runs
    ):
        return True
    repository = getattr(store, "repository", None)
    list_runs = getattr(repository, "list_rd_collaboration_runs", None)
    runs = list_runs(product_version_id=version_id) if callable(list_runs) else []
    return any(
        isinstance(item, dict) and item.get("status") not in _TERMINAL_RUN_STATUSES for item in runs
    )


def _capacity_limit(snapshot: dict[str, Any]) -> int | None:
    payload = snapshot.get("payload_json")
    if not isinstance(payload, dict):
        return None
    iteration_config = payload.get("iteration_config")
    if not isinstance(iteration_config, dict):
        return None
    capacity = iteration_config.get("capacity")
    raw_limit = (
        capacity.get("max_requirements")
        if isinstance(capacity, dict)
        else iteration_config.get("max_requirements")
    )
    return raw_limit if isinstance(raw_limit, int) and raw_limit > 0 else None


def _candidate_score(
    store: Any,
    *,
    candidate: dict[str, Any],
    source_snapshot: dict[str, Any],
    source_assessment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    members = _version_members(store, str(candidate["id"]))
    reasons: list[str] = []
    if candidate.get("status") != "planning":
        reasons.append("version_not_planning")
    if _version_has_active_run(store, str(candidate["id"])):
        reasons.append("active_run")

    limit = _capacity_limit(source_snapshot)
    if limit is not None and len(members) >= limit:
        reasons.append("capacity_exhausted")

    payload = source_snapshot.get("payload_json")
    if not isinstance(payload, dict):
        # Historical read-only snapshots did not retain the unified payload.
        # They have no declared repository/dependency/delivery constraint, so
        # remain compatible while current frozen snapshots are fully checked.
        payload = {}
    git_config = payload.get("git_config")
    requested_repository_ids: set[str] = set()
    if isinstance(git_config, dict):
        raw_ids = git_config.get("repository_ids")
        if isinstance(raw_ids, list):
            requested_repository_ids.update(str(item) for item in raw_ids if item)
        if git_config.get("repository_id"):
            requested_repository_ids.add(str(git_config["repository_id"]))
    if requested_repository_ids:
        configured_repository_ids = {
            str(config.get("repository_id"))
            for config in _records(store, "product_version_branch_configs").values()
            if config.get("version_id") == candidate["id"] and config.get("repository_id")
        }
        if not requested_repository_ids & configured_repository_ids:
            reasons.append("repository_incompatible")
    if payload.get("delivery_target", "ready_for_release") not in {
        "ready_for_release",
        "deployed",
    }:
        reasons.append("delivery_target_incompatible")
    if source_assessment is not None:
        dependencies = source_assessment.get("dependency_summary")
        member_ids = {str(item.get("id")) for item in members}
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if not isinstance(dependency, dict):
                    continue
                is_hard = dependency.get("hard") is True or dependency.get("type") == "hard"
                dependency_id = dependency.get("requirement_id") or dependency.get(
                    "dependency_requirement_id"
                )
                if is_hard and dependency_id and str(dependency_id) not in member_ids:
                    reasons.append("hard_dependency_unsatisfied")
                    break

    merge_payloads: list[dict[str, Any]] = []
    for member in members:
        assessment = _accepted_member_assessment(store, member)
        if assessment is None:
            reasons.append("member_assessment_unaccepted")
            break
        member_snapshot = _snapshot(store, str(assessment["final_strategy_snapshot_id"]))
        if (
            member_snapshot["policy_id"] != source_snapshot["policy_id"]
            or member_snapshot["policy_version"] != source_snapshot["policy_version"]
        ):
            reasons.append("policy_identity_mismatch")
            break
        if member_snapshot["id"] != source_snapshot["id"]:
            source_payload = source_snapshot.get("payload_json")
            member_payload = member_snapshot.get("payload_json")
            if not isinstance(source_payload, dict) or not isinstance(member_payload, dict):
                reasons.append("policy_merge_required")
                break
            if not merge_payloads:
                merge_payloads.append(source_payload)
            merge_payloads.append(member_payload)

    if not reasons and merge_payloads:
        try:
            merge_policy_payloads(merge_payloads)
        except PolicyResolutionError:
            reasons.append("policy_merge_required")

    hard_eligible = not reasons
    # Fewer existing members preserves capacity and is a deterministic, explainable score.
    score = 1_000 - len(members) if hard_eligible else None
    return {
        "capacity_limit": limit,
        "current_requirement_count": len(members),
        "hard_eligible": hard_eligible,
        "reasons": reasons,
        "score": score,
        "version_id": candidate["id"],
    }


def validate_manual_iteration_assignment(
    store: Any,
    *,
    requirement_id: str,
    version_id: str,
) -> dict[str, Any]:
    """Recheck the non-negotiable grouping constraints for manual scheduling.

    The batch endpoint may choose a version, but it may not circumvent the
    assessment provenance, policy merge, capacity, repository, or dependency
    checks used by automated grouping.
    """
    requirement = _records(store, "requirements").get(requirement_id)
    candidate = _records(store, "product_versions").get(version_id)
    if requirement is None or candidate is None:
        return {
            "hard_eligible": False,
            "reasons": ["missing_requirement_or_version"],
            "version_id": version_id,
        }
    assessment = _accepted_member_assessment(store, requirement)
    if assessment is None:
        return {
            "hard_eligible": False,
            "reasons": ["assessment_unaccepted"],
            "version_id": version_id,
        }
    source_snapshot = _snapshot(store, str(assessment["final_strategy_snapshot_id"]))
    result = _candidate_score(
        store,
        candidate=candidate,
        source_snapshot=source_snapshot,
        source_assessment=assessment,
    )
    result["score"] = (
        1_000 - int(result["current_requirement_count"]) if result["hard_eligible"] else None
    )
    return result


def _decision_request(
    store: Any,
    *,
    assessment_id: str,
    candidate_ids: list[str],
    reason: str,
    requirement: dict[str, Any],
    actor_id: str,
) -> dict[str, Any]:
    decision = {
        "id": store.new_id("plan_version_decision"),
        "assessment_id": assessment_id,
        "brain_app_id": requirement.get("brain_app_id", "rd_brain"),
        "created_at": _now(),
        "created_by": actor_id,
        "decision_type": "iteration_grouping",
        "evidence_json": [{"candidate_version_ids": candidate_ids, "reason": reason}],
        "plan_version": 0,
        "product_id": requirement["product_id"],
        "status": "pending",
        "subject_id": requirement["id"],
        "subject_type": "requirement_iteration_grouping",
        "version": 1,
    }
    _records(store, "decision_requests")[decision["id"]] = decision
    return decision


def _new_planning_version(store: Any, requirement: dict[str, Any]) -> dict[str, Any]:
    product_versions = _records(store, "product_versions")
    existing_codes = {
        str(item.get("code"))
        for item in product_versions.values()
        if item.get("product_id") == requirement["product_id"]
    }
    ordinal = 1
    code = f"RD-{requirement['product_id']}-PLAN-{ordinal:03d}"
    while code in existing_codes:
        ordinal += 1
        code = f"RD-{requirement['product_id']}-PLAN-{ordinal:03d}"
    version = {
        "code": code,
        "created_at": _now(),
        "id": store.new_id("product_version"),
        "name": f"{code} 规划版本",
        "product_id": requirement["product_id"],
        "scope_version": 1,
        "status": "planning",
        "updated_at": _now(),
    }
    product_versions[version["id"]] = version
    return version


def _assign_to_version(
    store: Any,
    *,
    requirement: dict[str, Any],
    version: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if requirement.get("version_id") == version["id"] and requirement.get("status") == "planned":
        return requirement, version
    updated_requirement = {
        **requirement,
        "status": "planned",
        "updated_at": _now(),
        "version_id": version["id"],
    }
    updated_version = {
        **version,
        "scope_version": int(version.get("scope_version") or 1) + 1,
        "updated_at": _now(),
    }
    _records(store, "requirements")[updated_requirement["id"]] = updated_requirement
    _records(store, "product_versions")[updated_version["id"]] = updated_version
    return updated_requirement, updated_version


def plan_accepted_requirement(
    store: Any,
    *,
    requirement_id: str,
    assessment_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """Group one accepted requirement into a compatible planning version.

    This deterministic service owns grouping selection.  It deliberately leaves
    ties and high-risk new-version creation pending for a human decision rather
    than silently selecting an arbitrary iteration.
    """
    requirement = _records(store, "requirements").get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if requirement.get("status") == "planned" and requirement.get("version_id"):
        return {
            "created_version": False,
            "idempotency_key": _idempotency_key(requirement_id, assessment_id),
            "idempotent_replay": True,
            "requirement": deepcopy(requirement),
            "version": deepcopy(_records(store, "product_versions")[requirement["version_id"]]),
            "version_id": requirement["version_id"],
        }
    if requirement.get("status") != "approved":
        raise api_error(
            409,
            "REQUIREMENT_STATE_INVALID",
            "Only approved requirements can be grouped into an iteration",
        )
    assessment = _accepted_assessment_for_requirement(
        store,
        assessment_id=assessment_id,
        requirement=requirement,
    )
    source_snapshot = _snapshot(store, str(assessment["final_strategy_snapshot_id"]))
    key = _idempotency_key(requirement_id, assessment_id)
    plans = _records(store, "requirement_iteration_plans")
    existing = plans.get(key)
    if existing is not None:
        return {**deepcopy(existing), "idempotent_replay": True}

    candidates = [
        item
        for item in _records(store, "product_versions").values()
        if item.get("product_id") == requirement["product_id"] and item.get("status") == "planning"
    ]
    score_breakdowns = [
        _candidate_score(
            store,
            candidate=candidate,
            source_snapshot=source_snapshot,
            source_assessment=assessment,
        )
        for candidate in sorted(candidates, key=lambda item: str(item["id"]))
    ]
    eligible = [item for item in score_breakdowns if item["hard_eligible"]]
    if eligible:
        top_score = max(int(item["score"] or 0) for item in eligible)
        top = [item for item in eligible if item["score"] == top_score]
        if len(top) > 1:
            decision = _decision_request(
                store,
                assessment_id=assessment_id,
                candidate_ids=[str(item["version_id"]) for item in top],
                reason="candidate_score_tie",
                requirement=requirement,
                actor_id=actor_id,
            )
            result = {
                "candidate_scores": score_breakdowns,
                "created_version": False,
                "decision_request": decision,
                "idempotency_key": key,
                "status": "waiting_human",
            }
            plans[key] = deepcopy(result)
            return result
        selected = _records(store, "product_versions")[str(top[0]["version_id"])]
        updated_requirement, updated_version = _assign_to_version(
            store,
            requirement=requirement,
            version=selected,
        )
        result = {
            "candidate_scores": score_breakdowns,
            "created_version": False,
            "idempotency_key": key,
            "idempotent_replay": False,
            "requirement": deepcopy(updated_requirement),
            "score_breakdown": top[0],
            "status": "planned",
            "version": deepcopy(updated_version),
            "version_id": updated_version["id"],
        }
        plans[key] = deepcopy(result)
        return result

    risk_summary = assessment.get("risk_summary")
    risk_level = (
        risk_summary.get("risk_level") if isinstance(risk_summary, dict) else "none"
    ) or "none"
    if _RISK_RANK.get(str(risk_level), 99) >= _RISK_RANK["high"]:
        decision = _decision_request(
            store,
            assessment_id=assessment_id,
            candidate_ids=[],
            reason="high_risk_new_version",
            requirement=requirement,
            actor_id=actor_id,
        )
        result = {
            "candidate_scores": score_breakdowns,
            "created_version": False,
            "decision_request": decision,
            "idempotency_key": key,
            "status": "waiting_human",
        }
        plans[key] = deepcopy(result)
        return result

    created_version = _new_planning_version(store, requirement)
    updated_requirement, updated_version = _assign_to_version(
        store,
        requirement=requirement,
        version=created_version,
    )
    result = {
        "candidate_scores": score_breakdowns,
        "created_version": True,
        "idempotency_key": key,
        "idempotent_replay": False,
        "requirement": deepcopy(updated_requirement),
        "score_breakdown": {
            "hard_eligible": True,
            "reasons": ["no_compatible_planning_version"],
            "score": None,
            "version_id": updated_version["id"],
        },
        "status": "planned",
        "version": deepcopy(updated_version),
        "version_id": updated_version["id"],
    }
    plans[key] = deepcopy(result)
    return result
