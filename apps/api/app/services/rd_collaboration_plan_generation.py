"""Generate a proposed collaboration DAG without giving the model state authority.

The model sees only frozen run inputs and returns a JSON proposal.  The
existing planning service remains the only component allowed to validate roles,
dependencies and state, then persist a runnable plan.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from typing import Any

from fastapi import HTTPException

from app.api.deps import api_error
from app.services.model_gateway import (
    ModelGatewayCallError,
    ModelGatewayConfigError,
    call_model_gateway_for_json_object,
)
from app.services.model_gateway_config_context import (
    model_gateway_write_store,
    save_model_gateway_records,
)
from app.services.rd_collaboration_planning import persist_work_item_plan

_PLANNER_PURPOSE = "rd_collaboration_work_item_planning"
_SECRET_FIELD_MARKERS = {"api_key", "credential", "password", "secret", "token"}


def _records(store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    values = getattr(store, collection_name, None)
    return values if isinstance(values, dict) else {}


def _run(store: Any, collaboration_run_id: str) -> dict[str, Any]:
    repository = getattr(store, "repository", None)
    load = getattr(repository, "get_rd_collaboration_run", None)
    loaded = load(collaboration_run_id) if callable(load) else None
    result = loaded or _records(store, "rd_collaboration_runs").get(collaboration_run_id)
    if not isinstance(result, dict):
        raise api_error(404, "NOT_FOUND", "Collaboration run not found")
    return dict(result)


def _snapshot(store: Any, snapshot_id: str) -> dict[str, Any]:
    repository = getattr(store, "repository", None)
    load = getattr(repository, "get_rd_policy_snapshot", None)
    loaded = load(snapshot_id) if callable(load) else None
    result = loaded or _records(store, "rd_task_executor_policy_snapshots").get(snapshot_id)
    if not isinstance(result, dict):
        raise api_error(
            409,
            "RD_POLICY_SNAPSHOT_INVALID",
            "Frozen strategy snapshot is unavailable",
        )
    return dict(result)


def _run_scope(store: Any, collaboration_run_id: str) -> list[dict[str, Any]]:
    repository = getattr(store, "repository", None)
    load = getattr(repository, "list_rd_collaboration_run_requirements", None)
    records = (
        load(collaboration_run_id)
        if callable(load)
        else [
            value
            for value in _records(store, "rd_collaboration_run_requirements").values()
            if value.get("collaboration_run_id") == collaboration_run_id
        ]
    )
    return sorted(
        (dict(item) for item in records if isinstance(item, dict)),
        key=lambda item: item["id"],
    )


def _requirements(store: Any, scope: list[dict[str, Any]]) -> list[dict[str, Any]]:
    repository = getattr(store, "repository", None)
    load = getattr(repository, "load_requirements", None)
    loaded = load() if callable(load) else None
    values = (
        loaded.get("requirements", {}).values()
        if isinstance(loaded, dict) and isinstance(loaded.get("requirements"), dict)
        else _records(store, "requirements").values()
    )
    by_id = {str(item.get("id")): dict(item) for item in values if isinstance(item, dict)}
    result: list[dict[str, Any]] = []
    for entry in scope:
        requirement_id = str(entry.get("requirement_id") or "")
        requirement = by_id.get(requirement_id)
        if requirement is None:
            raise api_error(
                409,
                "RD_SCOPE_CHANGE_INVALID",
                "Frozen collaboration requirement is unavailable",
                {"requirement_id": requirement_id},
            )
        result.append(
            {
                "id": requirement_id,
                "revision": int(entry.get("requirement_revision") or 1),
                "title": str(requirement.get("title") or ""),
                "description": str(requirement.get("description") or ""),
                "acceptance_criteria": deepcopy(requirement.get("acceptance_criteria") or []),
                "repository_scope": deepcopy(requirement.get("repository_scope") or {}),
            }
        )
    return result


def _seats(store: Any, collaboration_run_id: str) -> list[dict[str, Any]]:
    repository = getattr(store, "repository", None)
    load = getattr(repository, "list_rd_run_seats", None)
    records = (
        load(collaboration_run_id)
        if callable(load)
        else [
            value
            for value in _records(store, "rd_run_seats").values()
            if value.get("collaboration_run_id") == collaboration_run_id
        ]
    )
    return sorted(
        [
            {
                "id": str(item["id"]),
                "role_code": str(item.get("role_code") or ""),
                "subject_type": str(item.get("subject_type") or ""),
                "capacity": int(item.get("capacity") or 0),
            }
            for item in records
            if isinstance(item, dict) and item.get("status", "active") == "active"
        ],
        key=lambda item: (item["role_code"], item["id"]),
    )


def _redact(value: Any) -> Any:
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if not isinstance(value, dict):
        return value
    return {
        str(key): _redact(item)
        for key, item in value.items()
        if not any(marker in str(key).lower() for marker in _SECRET_FIELD_MARKERS)
    }


def frozen_planning_request(store: Any, *, collaboration_run_id: str) -> dict[str, Any]:
    """Build the bounded planner input from immutable run state only."""
    run = _run(store, collaboration_run_id)
    if run.get("status") != "planning" or int(run.get("plan_version") or 0) != 0:
        raise api_error(
            409,
            "RD_WORK_ITEM_STATE_INVALID",
            "Only an unplanned collaboration run can be generated automatically",
        )
    scope = _run_scope(store, collaboration_run_id)
    if not scope:
        raise api_error(409, "RD_SCOPE_CHANGE_INVALID", "Collaboration run has no frozen scope")
    snapshot = _snapshot(store, str(run.get("strategy_snapshot_id") or ""))
    return {
        "collaboration_run_id": collaboration_run_id,
        "scope_version": int(run.get("scope_version") or 0),
        "delivery_target": run.get("delivery_target", "ready_for_release"),
        "strategy_snapshot": {
            "id": snapshot["id"],
            "policy_id": snapshot.get("policy_id"),
            "policy_version": snapshot.get("policy_version"),
            "content_hash": snapshot.get("content_hash"),
            "payload": _redact(snapshot.get("payload_json") or {}),
        },
        "requirements": _requirements(store, scope),
        "seats": _seats(store, collaboration_run_id),
    }


def _planner_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    schema = {
        "work_items": [
            {
                "id": "stable-local-id",
                "requirement_id": "one frozen requirement id",
                "work_item_type": (
                    "product_detail_design | technical_solution | implementation | code_review | "
                    "automated_testing | release_readiness | documentation"
                ),
                "title": "string",
                "objective": "string",
                "owner_role_code": "one active role code",
                "reviewer_role_code": "a different active role code",
                "resource_claims": [
                    {
                        "repository_id": "one frozen repository id for implementation items",
                        "path": "relative path or directory",
                        "mode": "write",
                    }
                ],
                "input_contract": {},
                "output_contract": {},
                "acceptance_criteria": ["string"],
                "risk_level": "low | medium | high | critical",
                "priority": 100,
            }
        ],
        "dependencies": [
            {
                "predecessor_work_item_id": "stable-local-id",
                "successor_work_item_id": "stable-local-id",
                "dependency_type": "finish_to_start",
            }
        ],
    }
    return [
        {
            "role": "system",
            "content": (
                "You are the R&D collaboration planning assistant. Return one JSON object only, "
                "without markdown. Propose a minimal directed acyclic graph for the frozen "
                "requirements. Use only provided requirement ids and active role codes. Do not "
                "select executors, alter policies, grant permissions, or approve risk. The server "
                "will reject unsafe proposals. Every implementation item must declare at least "
                "one repository-scoped write resource_claim; use read claims for non-mutating "
                "work where relevant. Required JSON shape: "
                + json.dumps(schema, ensure_ascii=False, sort_keys=True)
            ),
        },
        {"role": "user", "content": json.dumps(request, ensure_ascii=False, sort_keys=True)},
    ]


def _default_planner(store: Any, request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    gateway_store = model_gateway_write_store(store)
    try:
        return call_model_gateway_for_json_object(
            gateway_store,
            purpose=_PLANNER_PURPOSE,
            messages=_planner_messages(request),
        )
    finally:
        # The log intentionally contains metadata only.  It remains useful if
        # deterministic validation subsequently rejects the proposal.
        save_model_gateway_records(gateway_store)


def generate_and_persist_work_item_plan(
    store: Any,
    *,
    collaboration_run_id: str,
    planner: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Ask a planner for a proposal and persist it through deterministic validation."""
    request = frozen_planning_request(store, collaboration_run_id=collaboration_run_id)
    proposal = planner(request) if planner is not None else _default_planner(store, request)[0]
    if not isinstance(proposal, dict):
        raise api_error(422, "RD_PLAN_INVALID", "Planner output must be a JSON object")
    persisted = persist_work_item_plan(
        store,
        collaboration_run_id=collaboration_run_id,
        proposal=proposal,
        actor={"id": _run(store, collaboration_run_id)["created_by"], "roles": ["rd_owner"]},
    )
    return {"status": "planned", **persisted}


def plan_pending_collaboration_runs(
    store: Any,
    *,
    limit: int = 20,
    planner: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, list[str]]:
    """Generate plans for eligible runs once their frozen start transaction commits.

    A model/configuration failure leaves the run in ``planning``.  It does not
    create a locally invented DAG, nor does it manufacture an invalid human
    pause state: the database permits run suspension only from execution
    phases.  The next worker sweep can retry after the gateway is repaired.
    """
    if limit <= 0:
        return {"planned_run_ids": [], "skipped_run_ids": []}
    repository = getattr(store, "repository", None)
    load = getattr(repository, "list_rd_collaboration_runs", None)
    runs = (
        load(status="planning")
        if callable(load)
        else [
            record
            for record in _records(store, "rd_collaboration_runs").values()
            if record.get("status") == "planning"
        ]
    )
    planned: list[str] = []
    skipped: list[str] = []
    for run in sorted(runs, key=lambda item: str(item.get("id") or "")):
        if len(planned) >= limit:
            break
        run_id = str(run.get("id") or "")
        if not run_id or int(run.get("plan_version") or 0) != 0:
            continue
        try:
            generate_and_persist_work_item_plan(
                store,
                collaboration_run_id=run_id,
                planner=planner,
            )
        except (HTTPException, ModelGatewayConfigError, ModelGatewayCallError):
            # The failed proposal is never persisted.  Gateway failures retain
            # their metadata log, while invalid plans remain safely unplanned.
            skipped.append(run_id)
            continue
        planned.append(run_id)
    return {"planned_run_ids": planned, "skipped_run_ids": skipped}
