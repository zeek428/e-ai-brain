from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.services.operational_records import read_memory_dict

PLAN_TYPE = "acceptance_test_plan"
CASE_TYPE = "acceptance_test_case"
RUN_TYPE = "acceptance_test_run"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json_safe(value: Any) -> Any:
    """Normalize repository rows before embedding them in JSON-backed evidence."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def acceptance_verification_fingerprint(verification: dict[str, Any]) -> str:
    """Return the stable identity of the frozen deterministic check inputs."""
    encoded = json.dumps(
        verification,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:32]


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


def _normalized_verification(verification: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(verification, dict) or not verification:
        return {}
    verification_type = str(verification.get("type") or "").strip()
    if verification_type != "file_contains":
        raise ValueError("Unsupported acceptance case verification type")
    path = str(verification.get("path") or "").strip()
    normalized_path = path.replace("\\", "/")
    if (
        not normalized_path
        or normalized_path.startswith("/")
        or (len(normalized_path) >= 2 and normalized_path[1] == ":")
        or ".." in normalized_path.split("/")
    ):
        raise ValueError("file_contains verification path must remain inside the workspace")
    required_text = verification.get("required_text")
    if not isinstance(required_text, list):
        required_text = []
    normalized_text = [str(item).strip() for item in required_text if str(item).strip()]
    if not normalized_text:
        raise ValueError("file_contains verification requires path and required_text")
    return {
        "path": path,
        "required_text": normalized_text,
        "type": verification_type,
    }


def create_acceptance_test_case(
    current_store: Any,
    *,
    case_code: str,
    criterion: str,
    created_by: str,
    plan_id: str,
    title: str,
    verification: dict[str, Any] | None = None,
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
        "verification": _normalized_verification(verification),
    }
    _save(current_store, collection="acceptance_test_cases", record=record, record_type=CASE_TYPE)
    return deepcopy(record)


def active_acceptance_case_verifications(
    current_store: Any,
    *,
    requirement_id: str,
) -> list[dict[str, Any]]:
    bundle = active_acceptance_case_verification_bundle(
        current_store,
        requirement_id=requirement_id,
    )
    return bundle["cases"]


def active_acceptance_case_verification_bundle(
    current_store: Any,
    *,
    requirement_id: str,
) -> dict[str, Any]:
    plan = next(
        (
            item
            for item in _records(current_store, "acceptance_test_plans", PLAN_TYPE)
            if item.get("requirement_id") == requirement_id and item.get("status") == "active"
        ),
        None,
    )
    if plan is None:
        return {"cases": [], "plan_id": None}
    cases = (plan.get("plan_snapshot") or {}).get("cases") or []
    verifications: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("id") or "").strip()
        verification = case.get("verification")
        if not case_id or not isinstance(verification, dict) or not verification:
            continue
        verifications.append(
            {
                "case_id": case_id,
                "verification": deepcopy(verification),
            }
        )
    return {"cases": verifications, "plan_id": str(plan.get("id") or "") or None}


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
            {
                "case_code": item["case_code"],
                "criterion": item["criterion"],
                "id": item["id"],
                "verification": deepcopy(item.get("verification") or {}),
            }
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


def _quality_gate_acceptance_run_id(
    *,
    case_id: str,
    commit_sha: str | None,
    input_fingerprint: str | None,
    quality_gate_run_id: str,
    verifier_task_id: str | None,
) -> str:
    material = {
        "case_id": case_id,
        "commit_sha": commit_sha,
        "input_fingerprint": input_fingerprint,
        "quality_gate_run_id": quality_gate_run_id,
        "verifier_task_id": verifier_task_id,
    }
    encoded = json.dumps(
        material,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "acceptance_test_run_" + hashlib.sha256(
        encoded
    ).hexdigest()[:32]


def build_acceptance_test_run(
    current_store: Any,
    *,
    artifact_ref: str | None,
    case_id: str,
    commit_sha: str | None,
    input_fingerprint: str | None,
    status: str,
    verifier_task_id: str | None,
    quality_gate_run_id: str | None = None,
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
    record_id = (
        _quality_gate_acceptance_run_id(
            case_id=case_id,
            commit_sha=commit_sha,
            input_fingerprint=input_fingerprint,
            quality_gate_run_id=quality_gate_run_id,
            verifier_task_id=verifier_task_id,
        )
        if quality_gate_run_id
        else current_store.new_id("acceptance_test_run")
    )
    existing = next(
        (
            item
            for item in _records(current_store, "acceptance_test_runs", RUN_TYPE)
            if item.get("id") == record_id
        ),
        None,
    )
    if existing is not None:
        return deepcopy(existing)
    now = _now()
    record = {
        "artifact_ref": artifact_ref,
        "case_id": case_id,
        "commit_sha": commit_sha,
        "created_at": now,
        "id": record_id,
        "input_fingerprint": input_fingerprint,
        "plan_id": case["plan_id"],
        "product_id": case["product_id"],
        "quality_gate_run_id": quality_gate_run_id,
        "status": status,
        "updated_at": now,
        "verifier_task_id": verifier_task_id,
    }
    return deepcopy(record)


def record_acceptance_test_run(
    current_store: Any,
    *,
    artifact_ref: str | None,
    case_id: str,
    commit_sha: str | None,
    input_fingerprint: str | None,
    status: str,
    verifier_task_id: str | None,
    quality_gate_run_id: str | None = None,
) -> dict[str, Any]:
    record = build_acceptance_test_run(
        current_store,
        artifact_ref=artifact_ref,
        case_id=case_id,
        commit_sha=commit_sha,
        input_fingerprint=input_fingerprint,
        quality_gate_run_id=quality_gate_run_id,
        status=status,
        verifier_task_id=verifier_task_id,
    )
    _save(current_store, collection="acceptance_test_runs", record=record, record_type=RUN_TYPE)
    return deepcopy(record)


def evaluate_acceptance_coverage(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    commit_sha: str | None = None,
    expected_case_fingerprints: dict[str, str] | None = None,
    additional_runs: list[dict[str, Any]] | None = None,
    plan_id: str | None = None,
    quality_gate_run_id: str | None = None,
) -> dict[str, Any]:
    requirement_id = str(ai_task.get("requirement_id") or "")
    plans = _records(current_store, "acceptance_test_plans", PLAN_TYPE)
    if plan_id:
        plan = next((item for item in plans if item.get("id") == plan_id), None)
    else:
        plan = next(
            (
                item
                for item in plans
                if item.get("requirement_id") == requirement_id and item.get("status") == "active"
            ),
            None,
        )
    task_criteria = list(
        (ai_task.get("input_json") or {}).get("acceptance_criteria")
        or ai_task.get("acceptance_criteria")
        or []
    )
    task_criteria = [str(item).strip() for item in task_criteria if str(item).strip()]
    snapshot_cases = (plan.get("plan_snapshot") or {}).get("cases") or [] if plan else []
    frozen_plan_criteria = [
        str(case.get("criterion") or "").strip()
        for case in snapshot_cases
        if isinstance(case, dict) and str(case.get("criterion") or "").strip()
    ]
    criteria = frozen_plan_criteria if plan_id and frozen_plan_criteria else task_criteria
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
    existing_run_ids = {str(item.get("id") or "") for item in runs}
    runs.extend(
        dict(item)
        for item in additional_runs or []
        if str(item.get("id") or "") not in existing_run_ids
    )
    flaky_case_ids: list[str] = []
    incomplete_case_ids: list[str] = []
    for case in cases:
        case_runs = [item for item in runs if item.get("case_id") == case["id"]]
        if quality_gate_run_id is not None:
            case_runs = [
                item
                for item in case_runs
                if str(item.get("quality_gate_run_id") or "") == quality_gate_run_id
            ]
        if commit_sha is not None:
            case_runs = [
                item for item in case_runs if str(item.get("commit_sha") or "") == commit_sha
            ]
        expected_fingerprint = (expected_case_fingerprints or {}).get(case["id"])
        if expected_fingerprint is not None:
            case_runs = [
                item
                for item in case_runs
                if str(item.get("input_fingerprint") or "") == expected_fingerprint
            ]
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
        "plan": _json_safe(deepcopy(plan)),
        "unmapped_criteria": unmapped,
    }
