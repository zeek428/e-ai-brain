from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.services.operational_records import read_memory_dict

PLAN_TYPE = "acceptance_test_plan"
CASE_TYPE = "acceptance_test_case"
RUN_TYPE = "acceptance_test_run"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _records(current_store: Any, collection: str, record_type: str) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_trusted_delivery_records", None)
    if callable(list_records):
        return [dict(record) for record in list_records(record_type=record_type)]
    return [dict(record) for record in read_memory_dict(current_store, collection).values()]


def _save(
    current_store: Any,
    *,
    collection: str,
    record: dict[str, Any],
    record_type: str,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_trusted_delivery_record", None)
    if callable(save_record):
        save_record(record=record, record_type=record_type)
    read_memory_dict(current_store, collection)[record["id"]] = deepcopy(record)


def create_acceptance_test_plan(
    current_store: Any,
    *,
    created_by: str,
    product_id: str,
    requirement_id: str,
    title: str,
) -> dict[str, Any]:
    now = _now()
    record = {
        "created_at": now,
        "created_by": created_by,
        "id": current_store.new_id("acceptance_test_plan"),
        "plan_snapshot": {},
        "product_id": product_id,
        "requirement_id": requirement_id,
        "status": "draft",
        "title": title.strip(),
        "updated_at": now,
        "version": 1,
    }
    _save(current_store, collection="acceptance_test_plans", record=record, record_type=PLAN_TYPE)
    return deepcopy(record)


def list_acceptance_test_plans(
    current_store: Any,
    *,
    product_scope_ids: list[str] | None,
    requirement_id: str | None = None,
) -> list[dict[str, Any]]:
    plans = _records(current_store, "acceptance_test_plans", PLAN_TYPE)
    if product_scope_ids is not None:
        allowed = set(product_scope_ids)
        plans = [plan for plan in plans if str(plan.get("product_id")) in allowed]
    if requirement_id is not None:
        plans = [plan for plan in plans if plan.get("requirement_id") == requirement_id]
    return [deepcopy(plan) for plan in plans]


def get_acceptance_test_plan(current_store: Any, *, plan_id: str) -> dict[str, Any] | None:
    return next(
        (
            deepcopy(plan)
            for plan in _records(current_store, "acceptance_test_plans", PLAN_TYPE)
            if plan.get("id") == plan_id
        ),
        None,
    )


def get_acceptance_test_case(current_store: Any, *, case_id: str) -> dict[str, Any] | None:
    return next(
        (
            deepcopy(case)
            for case in _records(current_store, "acceptance_test_cases", CASE_TYPE)
            if case.get("id") == case_id
        ),
        None,
    )


def create_acceptance_test_case(
    current_store: Any,
    *,
    case_code: str,
    criterion: str,
    created_by: str,
    plan_id: str,
    title: str,
) -> dict[str, Any]:
    plan = next(
        (
            item
            for item in _records(current_store, "acceptance_test_plans", PLAN_TYPE)
            if item["id"] == plan_id
        ),
        None,
    )
    if plan is None:
        raise ValueError("Acceptance test plan not found")
    if plan.get("status") == "active":
        raise ValueError("Active acceptance test plan is immutable")
    now = _now()
    record = {
        "case_code": case_code.strip(),
        "created_at": now,
        "created_by": created_by,
        "criterion": criterion.strip(),
        "id": current_store.new_id("acceptance_test_case"),
        "plan_id": plan_id,
        "product_id": plan["product_id"],
        "status": "active",
        "title": title.strip(),
        "updated_at": now,
    }
    _save(current_store, collection="acceptance_test_cases", record=record, record_type=CASE_TYPE)
    return deepcopy(record)


def activate_acceptance_test_plan(
    current_store: Any,
    *,
    plan_id: str,
    user_id: str,
) -> dict[str, Any]:
    plans = _records(current_store, "acceptance_test_plans", PLAN_TYPE)
    plan = next((item for item in plans if item["id"] == plan_id), None)
    if plan is None:
        raise ValueError("Acceptance test plan not found")
    cases = [
        item
        for item in _records(current_store, "acceptance_test_cases", CASE_TYPE)
        if item["plan_id"] == plan_id
    ]
    snapshot = {
        "activated_by": user_id,
        "activated_at": _now(),
        "cases": [
            {"case_code": item["case_code"], "criterion": item["criterion"], "id": item["id"]}
            for item in cases
        ],
    }
    for item in plans:
        if item["requirement_id"] == plan["requirement_id"] and item.get("status") == "active":
            item.update({"status": "superseded", "updated_at": _now()})
            _save(
                current_store,
                collection="acceptance_test_plans",
                record=item,
                record_type=PLAN_TYPE,
            )
    plan.update(
        {
            "plan_snapshot": snapshot,
            "status": "active",
            "updated_at": _now(),
            "version": int(plan.get("version") or 1) + 1,
        }
    )
    _save(current_store, collection="acceptance_test_plans", record=plan, record_type=PLAN_TYPE)
    return deepcopy(plan)


def record_acceptance_test_run(
    current_store: Any,
    *,
    artifact_ref: str | None,
    case_id: str,
    commit_sha: str | None,
    input_fingerprint: str | None,
    status: str,
    verifier_task_id: str | None,
) -> dict[str, Any]:
    case = next(
        (
            item
            for item in _records(current_store, "acceptance_test_cases", CASE_TYPE)
            if item["id"] == case_id
        ),
        None,
    )
    if case is None:
        raise ValueError("Acceptance test case not found")
    now = _now()
    record = {
        "artifact_ref": artifact_ref,
        "case_id": case_id,
        "commit_sha": commit_sha,
        "created_at": now,
        "id": current_store.new_id("acceptance_test_run"),
        "input_fingerprint": input_fingerprint,
        "plan_id": case["plan_id"],
        "product_id": case["product_id"],
        "status": status,
        "updated_at": now,
        "verifier_task_id": verifier_task_id,
    }
    _save(current_store, collection="acceptance_test_runs", record=record, record_type=RUN_TYPE)
    return deepcopy(record)


def evaluate_acceptance_coverage(current_store: Any, *, ai_task: dict[str, Any]) -> dict[str, Any]:
    requirement_id = str(ai_task.get("requirement_id") or "")
    plans = _records(current_store, "acceptance_test_plans", PLAN_TYPE)
    plan = next(
        (
            item
            for item in plans
            if item.get("requirement_id") == requirement_id and item.get("status") == "active"
        ),
        None,
    )
    criteria = list(
        (ai_task.get("input_json") or {}).get("acceptance_criteria")
        or ai_task.get("acceptance_criteria")
        or []
    )
    criteria = [str(item).strip() for item in criteria if str(item).strip()]
    if not criteria:
        return {
            "blocked_reasons": [],
            "flaky_case_ids": [],
            "incomplete_case_ids": [],
            "plan": None,
            "unmapped_criteria": [],
        }
    if plan is None:
        return {
            "blocked_reasons": ["ACCEPTANCE_GATE_BLOCKED"],
            "flaky_case_ids": [],
            "plan": None,
            "unmapped_criteria": criteria,
        }
    snapshot_cases = (plan.get("plan_snapshot") or {}).get("cases") or []
    case_ids = {
        str(case.get("id") or "")
        for case in snapshot_cases
        if isinstance(case, dict) and str(case.get("id") or "")
    }
    cases = [
        item
        for item in _records(current_store, "acceptance_test_cases", CASE_TYPE)
        if item.get("id") in case_ids
    ]
    mapped = {str(item.get("criterion") or "") for item in snapshot_cases if isinstance(item, dict)}
    unmapped = [criterion for criterion in criteria if criterion not in mapped]
    runs = _records(current_store, "acceptance_test_runs", RUN_TYPE)
    flaky_case_ids: list[str] = []
    incomplete_case_ids: list[str] = []
    for case in cases:
        case_runs = [item for item in runs if item.get("case_id") == case["id"]]
        outcomes: dict[tuple[str, str], set[str]] = {}
        for item in case_runs:
            key = (str(item.get("commit_sha") or ""), str(item.get("input_fingerprint") or ""))
            outcomes.setdefault(key, set()).add(str(item.get("status") or ""))
        if any({"passed", "failed"}.issubset(values) for values in outcomes.values()):
            flaky_case_ids.append(case["id"])
        elif not any(item.get("status") == "passed" for item in case_runs):
            incomplete_case_ids.append(case["id"])
    reasons: list[str] = []
    if unmapped or incomplete_case_ids:
        reasons.append("ACCEPTANCE_GATE_BLOCKED")
    if flaky_case_ids:
        reasons.append("ACCEPTANCE_FLAKY")
    return {
        "blocked_reasons": reasons,
        "flaky_case_ids": sorted(flaky_case_ids),
        "incomplete_case_ids": sorted(incomplete_case_ids),
        "plan": deepcopy(plan),
        "unmapped_criteria": unmapped,
    }
