"""Deterministic validation for collaboration work-item plans.

The planner deliberately accepts only structured proposals.  An LLM may prepare
the JSON document, but this module is the authority that decides whether it is
safe to persist or schedule the proposed DAG.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services.rd_policy_resolution import PolicyResolutionError, merge_policy_payloads


def _invalid(message: str, *, reason: str, **details: Any) -> None:
    raise api_error(422, "RD_PLAN_INVALID", message, {"reason": reason, **details})


def _work_item_id(item: Any, *, position: int) -> str:
    if not isinstance(item, dict):
        _invalid("Work item must be an object", reason="work_item_invalid", position=position)
    value = str(item.get("id") or item.get("idempotency_key") or "").strip()
    if not value:
        _invalid("Work item id is required", reason="work_item_id_missing", position=position)
    return value


def validate_work_item_plan(
    proposal: dict[str, Any],
    *,
    available_role_codes: set[str] | None = None,
    seats: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate a proposed DAG without writing any collaboration state.

    The returned document has a canonical dependency order, which callers can
    hash before persisting.  Invalid plans fail before a seat, item, attempt or
    command record is created.
    """
    if not isinstance(proposal, dict):
        _invalid("Plan must be an object", reason="plan_invalid")
    raw_items = proposal.get("work_items")
    raw_dependencies = proposal.get("dependencies", [])
    if not isinstance(raw_items, list) or not raw_items:
        _invalid("Plan requires at least one work item", reason="work_items_missing")
    if not isinstance(raw_dependencies, list):
        _invalid("Plan dependencies must be a list", reason="dependencies_invalid")

    item_ids: set[str] = set()
    owner_roles: dict[str, str] = {}
    reviewer_roles: dict[str, str] = {}
    normalized_items: list[dict[str, Any]] = []
    for position, raw_item in enumerate(raw_items):
        item_id = _work_item_id(raw_item, position=position)
        if item_id in item_ids:
            _invalid("Work item ids must be unique", reason="work_item_duplicate", item_id=item_id)
        item_ids.add(item_id)
        item = deepcopy(raw_item)
        item["id"] = item_id
        owner_role = str(item.get("owner_role_code") or "").strip()
        reviewer_role = str(item.get("reviewer_role_code") or "").strip()
        if not owner_role:
            _invalid(
                "Work item owner role is required", reason="owner_role_missing", item_id=item_id
            )
        if not reviewer_role:
            _invalid(
                "Work item reviewer role is required",
                reason="reviewer_role_missing",
                item_id=item_id,
            )
        if owner_role == reviewer_role:
            _invalid(
                "Work item owner and reviewer must be separated",
                reason="reviewer_separation",
                item_id=item_id,
            )
        if available_role_codes is not None:
            missing = sorted({owner_role, reviewer_role}.difference(available_role_codes))
            if missing:
                _invalid(
                    "Plan references an unavailable role",
                    reason="role_unavailable",
                    item_id=item_id,
                    missing_role_codes=missing,
                )
        owner_roles[item_id] = owner_role
        reviewer_roles[item_id] = reviewer_role
        normalized_items.append(item)

    active_seats = [seat for seat in seats or [] if seat.get("status", "active") == "active"]
    if seats is not None:
        capacities = defaultdict(int)
        for seat in active_seats:
            role = str(seat.get("role_code") or "")
            capacities[role] += int(seat.get("capacity") or 0)
        required_roles = set(owner_roles.values()) | set(reviewer_roles.values())
        missing_roles = sorted(role for role in required_roles if capacities[role] <= 0)
        if missing_roles:
            _invalid(
                "Plan references a role without an active seat",
                reason="role_seat_missing",
                missing_role_codes=missing_roles,
            )

    edges: set[tuple[str, str]] = set()
    successors: dict[str, set[str]] = {item_id: set() for item_id in item_ids}
    incoming: dict[str, int] = {item_id: 0 for item_id in item_ids}
    normalized_dependencies: list[dict[str, Any]] = []
    for position, raw_dependency in enumerate(raw_dependencies):
        if not isinstance(raw_dependency, dict):
            _invalid(
                "Dependency must be an object",
                reason="dependency_invalid",
                position=position,
            )
        predecessor = str(raw_dependency.get("predecessor_work_item_id") or "").strip()
        successor = str(raw_dependency.get("successor_work_item_id") or "").strip()
        if predecessor not in item_ids or successor not in item_ids:
            _invalid(
                "Dependency references an unknown work item",
                reason="dependency_unknown_item",
                position=position,
            )
        if predecessor == successor:
            _invalid(
                "A work item cannot depend on itself",
                reason="dependency_cycle",
                item_id=predecessor,
            )
        edge = (predecessor, successor)
        if edge in edges:
            _invalid(
                "Duplicate dependency edge is not allowed",
                reason="dependency_duplicate",
                predecessor_work_item_id=predecessor,
                successor_work_item_id=successor,
            )
        edges.add(edge)
        successors[predecessor].add(successor)
        incoming[successor] += 1
        normalized = deepcopy(raw_dependency)
        normalized["predecessor_work_item_id"] = predecessor
        normalized["successor_work_item_id"] = successor
        normalized_dependencies.append(normalized)

    queue = deque(sorted(item_id for item_id, count in incoming.items() if count == 0))
    ordered: list[str] = []
    while queue:
        item_id = queue.popleft()
        ordered.append(item_id)
        for successor in sorted(successors[item_id]):
            incoming[successor] -= 1
            if incoming[successor] == 0:
                queue.append(successor)
    if len(ordered) != len(item_ids):
        _invalid("Work item dependencies contain a cycle", reason="dependency_cycle")

    return {
        **deepcopy(proposal),
        "work_items": sorted(normalized_items, key=lambda item: item["id"]),
        "dependencies": sorted(
            normalized_dependencies,
            key=lambda item: (
                item["predecessor_work_item_id"],
                item["successor_work_item_id"],
            ),
        ),
        "topological_order": ordered,
    }


_TERMINAL_RUN_STATES = {"completed", "failed", "cancelled"}


def _records(store: Any, name: str) -> dict[str, dict[str, Any]]:
    records = getattr(store, name, None)
    if not isinstance(records, dict):
        records = {}
        setattr(store, name, records)
    return records


def _new_id(store: Any, prefix: str) -> str:
    factory = getattr(store, "new_id", None)
    if callable(factory):
        return str(factory(prefix))
    digest = hashlib.sha256(f"{prefix}:{datetime.now(UTC).isoformat()}".encode()).hexdigest()
    return f"{prefix}_{digest[:16]}"


def _hash(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(serialized.encode()).hexdigest()}"


def _command_key(version_id: str, request_id: str, operation: str) -> str:
    return f"{operation}:{version_id}:{request_id}"


def _version(store: Any, version_id: str) -> dict[str, Any]:
    repository = getattr(store, "repository", None)
    get_version = getattr(repository, "get_product_version", None)
    loaded = get_version(version_id) if callable(get_version) else None
    version = loaded or _records(store, "product_versions").get(version_id)
    if version is None:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    return version


def _requirements_for_version(store: Any, version_id: str) -> list[dict[str, Any]]:
    repository = getattr(store, "repository", None)
    load = getattr(repository, "load_requirements", None)
    loaded = load() if callable(load) else None
    values = (
        loaded.values() if isinstance(loaded, dict) else _records(store, "requirements").values()
    )
    return sorted(
        [
            dict(requirement)
            for requirement in values
            if requirement.get("version_id") == version_id
        ],
        key=lambda requirement: str(requirement["id"]),
    )


def _accepted_assessment(store: Any, requirement: dict[str, Any]) -> dict[str, Any]:
    repository = getattr(store, "repository", None)
    list_assessments = getattr(repository, "list_requirement_assessments", None)
    values = (
        list_assessments(str(requirement["id"]))
        if callable(list_assessments)
        else _records(store, "requirement_assessments").values()
    )
    expected_revision = int(requirement.get("assessment_revision") or 1)
    candidates = [
        item
        for item in values
        if item.get("requirement_id") == requirement["id"]
        and item.get("status") == "accepted"
        and int(item.get("requirement_revision") or 1) == expected_revision
        and item.get("final_strategy_snapshot_id")
    ]
    if not candidates:
        raise api_error(
            409,
            "ASSESSMENT_PROVENANCE_INVALID",
            "Every scoped requirement requires an accepted current assessment",
            {"requirement_id": requirement["id"], "retryable": False},
        )
    return max(candidates, key=lambda item: str(item.get("updated_at") or item.get("id")))


def _snapshot(store: Any, snapshot_id: str) -> dict[str, Any]:
    repository = getattr(store, "repository", None)
    get_snapshot = getattr(repository, "get_rd_policy_snapshot", None)
    loaded = get_snapshot(snapshot_id) if callable(get_snapshot) else None
    snapshot = loaded or _records(store, "rd_task_executor_policy_snapshots").get(snapshot_id)
    if snapshot is None:
        raise api_error(
            409,
            "RD_POLICY_SNAPSHOT_INVALID",
            "Accepted assessment strategy snapshot is unavailable",
        )
    return dict(snapshot)


def _exact_scope(
    store: Any, version: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    requirements = _requirements_for_version(store, str(version["id"]))
    if not requirements:
        raise api_error(
            409, "RD_SCOPE_CHANGE_INVALID", "Product version has no scoped requirements"
        )
    assessments = [_accepted_assessment(store, requirement) for requirement in requirements]
    snapshots = [
        _snapshot(store, str(assessment["final_strategy_snapshot_id"]))
        for assessment in assessments
    ]
    identities = {
        (snapshot.get("policy_id"), snapshot.get("policy_version")) for snapshot in snapshots
    }
    if None in {identity[0] for identity in identities} or len(identities) != 1:
        raise api_error(
            409,
            "RD_VERSION_POLICY_MERGE_REQUIRED",
            "Scoped assessments do not share one policy identity",
            {"retryable": False, "next_action": "resolve_policy_decision"},
        )
    return requirements, assessments, snapshots


def _resolved_snapshot(
    store: Any,
    *,
    version: dict[str, Any],
    actor_id: str,
    snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    payloads = [snapshot.get("payload_json") or {} for snapshot in snapshots]
    try:
        payload = merge_policy_payloads(payloads) if len(payloads) > 1 else deepcopy(payloads[0])
    except PolicyResolutionError as exc:
        raise api_error(
            409,
            "RD_VERSION_POLICY_MERGE_REQUIRED",
            str(exc),
            {"retryable": False, "next_action": "resolve_policy_decision"},
        ) from exc
    parent = snapshots[0]
    return {
        "id": _new_id(store, "rd_policy_snapshot"),
        "policy_id": parent.get("policy_id"),
        "policy_version": parent.get("policy_version"),
        "parent_snapshot_id": parent.get("id"),
        "snapshot_kind": "version_resolved",
        "resolution_context_key": f"version:{version['id']}:scope:{version['scope_version']}",
        "resolution_revision": 1,
        "schema_version": int(parent.get("schema_version") or 1),
        "content_hash": _hash(payload),
        "payload_json": payload,
        "created_by": actor_id,
    }


def _run_response(
    run: dict[str, Any],
    *,
    snapshot: dict[str, Any],
    source_count: int,
    idempotent_replay: bool,
) -> dict[str, Any]:
    return {
        "run": {
            **deepcopy(run),
            "strategy_snapshot_kind": snapshot.get("snapshot_kind"),
            "strategy_snapshot_hash": snapshot.get("content_hash"),
        },
        "strategy_source_count": source_count,
        "idempotent_replay": idempotent_replay,
    }


def persist_work_item_plan(
    store: Any,
    *,
    collaboration_run_id: str,
    proposal: dict[str, Any],
    actor: dict[str, Any],
) -> dict[str, Any]:
    """Validate then persist one immutable plan version with frozen seat ids."""
    repository = getattr(store, "repository", None)
    get_run = getattr(repository, "get_rd_collaboration_run", None)
    run = (
        get_run(collaboration_run_id)
        if callable(get_run)
        else _records(store, "rd_collaboration_runs").get(collaboration_run_id)
    )
    if run is None:
        raise api_error(404, "NOT_FOUND", "Collaboration run not found")
    if run.get("status") not in {"draft", "planning", "running"}:
        raise api_error(409, "RD_WORK_ITEM_STATE_INVALID", "Run cannot accept a work-item plan")
    list_seats = getattr(repository, "list_rd_run_seats", None)
    seats = (
        list_seats(collaboration_run_id)
        if callable(list_seats)
        else [
            seat
            for seat in _records(store, "rd_run_seats").values()
            if seat.get("collaboration_run_id") == collaboration_run_id
        ]
    )
    active_seats = [seat for seat in seats if seat.get("status", "active") == "active"]
    plan = validate_work_item_plan(
        proposal,
        available_role_codes={str(seat.get("role_code")) for seat in active_seats},
        seats=active_seats,
    )
    seat_by_role: dict[str, dict[str, Any]] = {}
    for seat in active_seats:
        role_code = str(seat.get("role_code") or "")
        if role_code in seat_by_role:
            raise api_error(
                409,
                "RD_ROLE_ASSIGNMENT_REQUIRED",
                "A plan role must resolve to exactly one frozen seat",
                {"role_code": role_code, "retryable": False},
            )
        seat_by_role[role_code] = seat
    plan_version = int(run.get("plan_version") or 0) + 1
    persisted_items: list[dict[str, Any]] = []
    ids_by_proposal_id: dict[str, str] = {}
    for item in plan["work_items"]:
        owner = seat_by_role[str(item["owner_role_code"])]
        reviewer = seat_by_role[str(item["reviewer_role_code"])]
        persisted_id = f"{collaboration_run_id}:plan:{plan_version}:item:{item['id']}"
        ids_by_proposal_id[item["id"]] = persisted_id
        persisted_items.append(
            {
                "id": persisted_id,
                "collaboration_run_id": collaboration_run_id,
                "plan_version": plan_version,
                "work_item_type": item.get("work_item_type", "implementation"),
                "title": item.get("title", item["id"]),
                "objective": item.get("objective", item.get("title", item["id"])),
                "owner_seat_id": owner["id"],
                "reviewer_seat_id": reviewer["id"],
                "input_contract": deepcopy(item.get("input_contract") or {}),
                "output_contract": deepcopy(item.get("output_contract") or {}),
                "acceptance_criteria": deepcopy(item.get("acceptance_criteria") or []),
                "status": "draft",
                "risk_level": item.get("risk_level", "medium"),
                "priority": int(item.get("priority") or 100),
                "idempotency_key": f"plan:{plan_version}:{item['id']}",
                "version": 1,
                "created_by": actor["id"],
            }
        )
    persisted_dependencies = [
        {
            "id": f"{collaboration_run_id}:plan:{plan_version}:dependency:{position}",
            "collaboration_run_id": collaboration_run_id,
            "plan_version": plan_version,
            "predecessor_work_item_id": ids_by_proposal_id[dependency["predecessor_work_item_id"]],
            "successor_work_item_id": ids_by_proposal_id[dependency["successor_work_item_id"]],
            "dependency_type": dependency.get("dependency_type", "finish_to_start"),
            "status": "pending",
        }
        for position, dependency in enumerate(plan["dependencies"])
    ]
    save_bundle = getattr(repository, "save_rd_work_item_plan_bundle", None)
    if callable(save_bundle):
        saved = save_bundle(
            collaboration_run_id=collaboration_run_id,
            expected_run_version=int(run.get("version") or 1),
            work_items=persisted_items,
            dependencies=persisted_dependencies,
        )
        return {
            "run": saved["run"],
            "plan_version": saved["run"]["plan_version"],
            "work_items": saved["work_items"],
            "dependencies": saved["dependencies"],
        }
    for item in persisted_items:
        _records(store, "rd_work_items")[item["id"]] = item
    for dependency in persisted_dependencies:
        _records(store, "rd_work_item_dependencies")[dependency["id"]] = dependency
    run["plan_version"] = plan_version
    run["version"] = int(run.get("version") or 1) + 1
    if run.get("status") in {"draft", "planning"}:
        run["status"] = "running"
    return {
        "run": deepcopy(run),
        "plan_version": plan_version,
        "work_items": persisted_items,
        "dependencies": persisted_dependencies,
    }


def start_collaboration_run(
    store: Any,
    *,
    product_version_id: str,
    request_id: str,
    scope_version: int,
    actor: dict[str, Any],
    reason: str | None = None,
) -> dict[str, Any]:
    """Freeze version scope and strategy into one non-terminal collaboration run."""
    version = _version(store, product_version_id)
    if int(version.get("scope_version") or 1) != scope_version:
        raise api_error(
            409,
            "RD_SCOPE_VERSION_CONFLICT",
            "Product version scope is stale",
            {"current_scope_version": version.get("scope_version"), "retryable": False},
        )
    request = {"scope_version": scope_version, "reason": reason, "actor_id": actor.get("id")}
    command_id = _command_key(product_version_id, request_id, "start_collaboration_run")
    commands = _records(store, "rd_command_idempotency_records")
    existing = commands.get(command_id)
    if existing is not None:
        if existing.get("request_hash") != _hash(request):
            raise api_error(409, "RD_IDEMPOTENCY_CONFLICT", "request_id has another start payload")
        return {**deepcopy(existing["response_snapshot"]), "idempotent_replay": True}
    repository = getattr(store, "repository", None)
    list_runs = getattr(repository, "list_rd_collaboration_runs", None)
    runs = (
        list_runs(product_version_id=product_version_id)
        if callable(list_runs)
        else _records(store, "rd_collaboration_runs").values()
    )
    existing_runs = [
        run
        for run in runs
        if run.get("product_version_id") == product_version_id
        and run.get("status") not in _TERMINAL_RUN_STATES
    ]
    if existing_runs:
        raise api_error(
            409,
            "RD_ACTIVE_RUN_CONFLICT",
            "Product version already has a non-terminal collaboration run",
            {"run_id": existing_runs[0]["id"], "retryable": False},
        )
    requirements, assessments, snapshots = _exact_scope(store, version)
    resolved = _resolved_snapshot(
        store, version=version, actor_id=str(actor["id"]), snapshots=snapshots
    )
    run = {
        "id": _new_id(store, "rd_collaboration_run"),
        "brain_app_id": "rd_brain",
        "product_id": version["product_id"],
        "product_version_id": product_version_id,
        "strategy_snapshot_id": resolved["id"],
        "run_generation": 1,
        "supersedes_run_id": None,
        "scope_version": scope_version,
        "plan_version": 0,
        "status": "planning",
        "delivery_target": resolved["payload_json"].get("delivery_target", "ready_for_release"),
        "graph_definition": "rd_collaboration",
        "graph_version": "v1",
        "version": 1,
        "created_by": actor["id"],
        "reason": reason,
    }
    scope_rows = [
        {
            "id": _new_id(store, "rd_collaboration_run_requirement"),
            "collaboration_run_id": run["id"],
            "requirement_id": requirement["id"],
            "requirement_revision": int(requirement.get("assessment_revision") or 1),
            "assessment_id": assessment["id"],
            "final_strategy_snapshot_id": assessment["final_strategy_snapshot_id"],
            "acceptance_criteria_hash": _hash(requirement.get("acceptance_criteria") or []),
            "repository_scope_hash": _hash(requirement.get("repository_scope") or {}),
        }
        for requirement, assessment in zip(requirements, assessments, strict=True)
    ]
    if repository is not None:
        return _start_collaboration_run_repository(
            store,
            repository=repository,
            run=run,
            scope_rows=scope_rows,
            resolved_snapshot=resolved,
            assessments=assessments,
            request_id=request_id,
            request=request,
        )
    _records(store, "rd_task_executor_policy_snapshots")[resolved["id"]] = resolved
    _records(store, "rd_collaboration_runs")[run["id"]] = run
    for row in scope_rows:
        _records(store, "rd_collaboration_run_requirements")[row["id"]] = row
    version["status"] = "active"
    response = _run_response(
        run,
        snapshot=resolved,
        source_count=len(scope_rows),
        idempotent_replay=False,
    )
    commands[command_id] = {
        "id": command_id,
        "command_type": "start_collaboration_run",
        "aggregate_id": product_version_id,
        "idempotency_key": request_id,
        "request_hash": _hash(request),
        "response_hash": _hash(response),
        "response_snapshot": deepcopy(response),
    }
    return response


def _start_collaboration_run_repository(
    store: Any,
    *,
    repository: Any,
    run: dict[str, Any],
    scope_rows: list[dict[str, Any]],
    resolved_snapshot: dict[str, Any],
    assessments: list[dict[str, Any]],
    request_id: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    execute = getattr(repository, "execute_idempotent_rd_command", None)
    if not callable(execute):
        raise api_error(
            503, "REPOSITORY_REQUIRED", "Collaboration command repository is unavailable"
        )
    sources = [
        {
            "id": _new_id(store, "rd_policy_snapshot_source"),
            "snapshot_id": resolved_snapshot["id"],
            "source_snapshot_id": assessment["final_strategy_snapshot_id"],
            "requirement_id": scope["requirement_id"],
            "assessment_id": assessment["id"],
        }
        for scope, assessment in zip(scope_rows, assessments, strict=True)
    ]

    def operation(transaction: Any) -> dict[str, Any]:
        transaction.activate_product_version_for_collaboration(
            product_version_id=run["product_version_id"],
        )
        transaction.merge_version_policy_snapshot_with_sources(
            snapshot=resolved_snapshot,
            sources=sources,
        )
        persisted = transaction.create_collaboration_run_with_exact_scope(
            run=run,
            scope_rows=scope_rows,
        )
        response = _run_response(
            persisted["run"],
            snapshot=resolved_snapshot,
            source_count=len(scope_rows),
            idempotent_replay=False,
        )
        return {
            "result_type": "rd_collaboration_run",
            "result_id": run["id"],
            "http_status": 201,
            "response_json": response,
        }

    result = execute(
        command_type="start_collaboration_run",
        aggregate_type="product_version",
        aggregate_id=run["product_version_id"],
        idempotency_key=request_id,
        request_hash=_hash(request),
        operation=operation,
    )
    return {**dict(result["response_json"]), "idempotent_replay": bool(result["idempotent_replay"])}


def restart_terminal_collaboration_run(
    store: Any,
    *,
    product_version_id: str,
    terminal_run_id: str,
    request_id: str,
    scope_version: int,
    actor: dict[str, Any],
    reason: str | None = None,
) -> dict[str, Any]:
    """Create a new generation; terminal collaboration state is never reopened."""
    version = _version(store, product_version_id)
    repository = getattr(store, "repository", None)
    get_terminal = getattr(repository, "get_rd_collaboration_run", None)
    terminal = (
        get_terminal(terminal_run_id)
        if callable(get_terminal)
        else _records(store, "rd_collaboration_runs").get(terminal_run_id)
    )
    if (
        terminal is None
        or terminal.get("product_version_id") != product_version_id
        or terminal.get("status") not in {"failed", "cancelled"}
        or version.get("status") not in {"active", "testing"}
        or int(version.get("scope_version") or 1) != scope_version
    ):
        raise api_error(409, "RD_RUN_RESTART_NOT_ALLOWED", "Terminal run cannot be restarted")
    list_runs = getattr(repository, "list_rd_collaboration_runs", None)
    runs = (
        list_runs(product_version_id=product_version_id)
        if callable(list_runs)
        else _records(store, "rd_collaboration_runs").values()
    )
    if any(
        run.get("product_version_id") == product_version_id
        and run.get("status") not in _TERMINAL_RUN_STATES
        for run in runs
    ):
        raise api_error(409, "RD_RUN_RESTART_NOT_ALLOWED", "Product version has an active run")
    request = {
        "terminal_run_id": terminal_run_id,
        "scope_version": scope_version,
        "reason": reason,
        "actor_id": actor.get("id"),
    }
    command_id = _command_key(product_version_id, request_id, "restart_collaboration_run")
    commands = _records(store, "rd_command_idempotency_records")
    if command_id in commands:
        existing = commands[command_id]
        if existing.get("request_hash") != _hash(request):
            raise api_error(
                409, "RD_IDEMPOTENCY_CONFLICT", "request_id has another restart payload"
            )
        return {**deepcopy(existing["response_snapshot"]), "idempotent_replay": True}
    requirements, assessments, snapshots = _exact_scope(store, version)
    resolved = _resolved_snapshot(
        store, version=version, actor_id=str(actor["id"]), snapshots=snapshots
    )
    run = {
        **terminal,
        "id": _new_id(store, "rd_collaboration_run"),
        "strategy_snapshot_id": resolved["id"],
        "run_generation": int(terminal.get("run_generation") or 1) + 1,
        "supersedes_run_id": terminal_run_id,
        "scope_version": scope_version,
        "plan_version": 0,
        "status": "planning",
        "completion_reason": None,
        "resume_state": None,
        "suspended_decision_request_id": None,
        "suspended_at": None,
        "version": 1,
        "created_by": actor["id"],
        "reason": reason,
    }
    scope_rows = [
        {
            "id": _new_id(store, "rd_collaboration_run_requirement"),
            "collaboration_run_id": run["id"],
            "requirement_id": requirement["id"],
            "requirement_revision": int(requirement.get("assessment_revision") or 1),
            "assessment_id": assessment["id"],
            "final_strategy_snapshot_id": assessment["final_strategy_snapshot_id"],
            "acceptance_criteria_hash": _hash(requirement.get("acceptance_criteria") or []),
            "repository_scope_hash": _hash(requirement.get("repository_scope") or {}),
        }
        for requirement, assessment in zip(requirements, assessments, strict=True)
    ]
    if repository is not None:
        return _restart_collaboration_run_repository(
            store,
            repository=repository,
            terminal_run_id=terminal_run_id,
            run=run,
            scope_rows=scope_rows,
            resolved_snapshot=resolved,
            assessments=assessments,
            request_id=request_id,
            request=request,
        )
    _records(store, "rd_task_executor_policy_snapshots")[resolved["id"]] = resolved
    _records(store, "rd_collaboration_runs")[run["id"]] = run
    for row in scope_rows:
        _records(store, "rd_collaboration_run_requirements")[row["id"]] = row
    response = {
        **_run_response(
            run, snapshot=resolved, source_count=len(scope_rows), idempotent_replay=False
        ),
        "reused_evidence_refs": [],
    }
    commands[command_id] = {
        "id": command_id,
        "command_type": "restart_collaboration_run",
        "aggregate_id": product_version_id,
        "idempotency_key": request_id,
        "request_hash": _hash(request),
        "response_hash": _hash(response),
        "response_snapshot": deepcopy(response),
    }
    return response


def _restart_collaboration_run_repository(
    store: Any,
    *,
    repository: Any,
    terminal_run_id: str,
    run: dict[str, Any],
    scope_rows: list[dict[str, Any]],
    resolved_snapshot: dict[str, Any],
    assessments: list[dict[str, Any]],
    request_id: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    execute = getattr(repository, "execute_idempotent_rd_command", None)
    if not callable(execute):
        raise api_error(
            503, "REPOSITORY_REQUIRED", "Collaboration command repository is unavailable"
        )
    sources = [
        {
            "id": _new_id(store, "rd_policy_snapshot_source"),
            "snapshot_id": resolved_snapshot["id"],
            "source_snapshot_id": assessment["final_strategy_snapshot_id"],
            "requirement_id": scope["requirement_id"],
            "assessment_id": assessment["id"],
        }
        for scope, assessment in zip(scope_rows, assessments, strict=True)
    ]

    def operation(transaction: Any) -> dict[str, Any]:
        merged = transaction.merge_version_policy_snapshot_with_sources(
            snapshot=resolved_snapshot,
            sources=sources,
        )
        persisted = transaction.restart_terminal_collaboration_run(
            terminal_run_id=terminal_run_id,
            run={**run, "strategy_snapshot_id": merged["id"]},
            scope_rows=scope_rows,
        )
        response = {
            **_run_response(
                persisted,
                snapshot=merged,
                source_count=len(scope_rows),
                idempotent_replay=False,
            ),
            "reused_evidence_refs": [],
        }
        return {
            "result_type": "rd_collaboration_run",
            "result_id": persisted["id"],
            "http_status": 201,
            "response_json": response,
        }

    result = execute(
        command_type="restart_collaboration_run",
        aggregate_type="product_version",
        aggregate_id=run["product_version_id"],
        idempotency_key=request_id,
        request_hash=_hash(request),
        operation=operation,
    )
    return {**dict(result["response_json"]), "idempotent_replay": bool(result["idempotent_replay"])}
