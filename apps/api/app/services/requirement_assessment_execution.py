from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error

ASSESSMENT_ONLY_SIDE_EFFECT_POLICY = "no_code_git_deploy_runner_work_item"


def create_assessment_execution(
    *,
    execution_id: str,
    assessment_id: str,
    opinion_id: str,
    role_code: str,
    actor_type: str,
    actor_id: str,
    executor_profile_id: str | None,
    input_revision: int,
    strategy_snapshot_id: str,
) -> dict[str, Any]:
    """Freeze a dedicated assessment-only unit; it is never a normal R&D task."""
    if actor_type not in {"human_user", "ai_employee"}:
        raise api_error(400, "ASSESSMENT_EXECUTION_INVALID", "Unsupported assessment actor type")
    if actor_type == "ai_employee" and not executor_profile_id:
        raise api_error(
            400,
            "ASSESSMENT_EXECUTION_INVALID",
            "AI assessment execution requires a qualified executor profile",
        )
    now = datetime.now(UTC).isoformat()
    return {
        "id": execution_id,
        "assessment_id": assessment_id,
        "opinion_id": opinion_id,
        "role_code": role_code,
        "actor_type": actor_type,
        "human_user_id": actor_id if actor_type == "human_user" else None,
        "ai_employee_id": actor_id if actor_type == "ai_employee" else None,
        "executor_profile_id": executor_profile_id,
        "input_revision": input_revision,
        "strategy_snapshot_id": strategy_snapshot_id,
        "execution_kind": "assessment_only",
        "side_effect_policy": ASSESSMENT_ONLY_SIDE_EFFECT_POLICY,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }


def ensure_assessment_only_execution(execution: dict[str, Any]) -> None:
    if (
        execution.get("execution_kind") != "assessment_only"
        or execution.get("side_effect_policy") != ASSESSMENT_ONLY_SIDE_EFFECT_POLICY
    ):
        raise api_error(
            409,
            "ASSESSMENT_EXECUTION_INVALID",
            "Assessment execution cannot create code, Git, deployment, runner, or work-item "
            "effects",
        )
