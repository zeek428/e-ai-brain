import json
from datetime import UTC, datetime

import pytest

from app.core.store import MemoryStore
from app.services.acceptance_test_plans import (
    activate_acceptance_test_plan,
    create_acceptance_test_case,
    create_acceptance_test_plan,
    evaluate_acceptance_coverage,
    record_acceptance_test_run,
)


def _task() -> dict:
    return {
        "id": "task_001",
        "input_json": {"acceptance_criteria": ["可导出审批结果"]},
        "product_id": "product_001",
        "requirement_id": "requirement_001",
    }


def test_unmapped_criterion_blocks_acceptance_gate() -> None:
    store = MemoryStore()

    result = evaluate_acceptance_coverage(store, ai_task=_task())

    assert result["blocked_reasons"] == ["ACCEPTANCE_GATE_BLOCKED"]
    assert result["unmapped_criteria"] == ["可导出审批结果"]


def test_conflicting_case_results_for_same_commit_are_flaky_and_blocked() -> None:
    store = MemoryStore()
    plan = create_acceptance_test_plan(
        store,
        created_by="user_admin",
        product_id="product_001",
        requirement_id="requirement_001",
        title="审批导出验收",
    )
    case = create_acceptance_test_case(
        store,
        case_code="acceptance.export_approval",
        criterion="可导出审批结果",
        created_by="user_admin",
        plan_id=plan["id"],
        title="审批结果导出",
    )
    activate_acceptance_test_plan(store, plan_id=plan["id"], user_id="user_admin")
    record_acceptance_test_run(
        store,
        artifact_ref="artifact://build/001",
        case_id=case["id"],
        commit_sha="abc123",
        input_fingerprint="inputs-v1",
        status="passed",
        verifier_task_id="verify_001",
    )
    record_acceptance_test_run(
        store,
        artifact_ref="artifact://build/001",
        case_id=case["id"],
        commit_sha="abc123",
        input_fingerprint="inputs-v1",
        status="failed",
        verifier_task_id="verify_002",
    )

    result = evaluate_acceptance_coverage(store, ai_task=_task())

    assert result["blocked_reasons"] == ["ACCEPTANCE_FLAKY"]
    assert result["flaky_case_ids"] == [case["id"]]


def test_frozen_plan_scope_is_not_replaced_by_internal_work_item_criteria() -> None:
    store = MemoryStore()
    plan = create_acceptance_test_plan(
        store,
        created_by="user_admin",
        product_id="product_001",
        requirement_id="requirement_001",
        title="需求验收计划",
    )
    case = create_acceptance_test_case(
        store,
        case_code="acceptance.requirement_scope",
        criterion="需求交付标准",
        created_by="user_admin",
        plan_id=plan["id"],
        title="需求交付标准验收",
    )
    activate_acceptance_test_plan(store, plan_id=plan["id"], user_id="user_admin")
    record_acceptance_test_run(
        store,
        artifact_ref="artifact://build/requirement-scope",
        case_id=case["id"],
        commit_sha="abc123",
        input_fingerprint="inputs-v1",
        status="passed",
        verifier_task_id="verify_001",
    )
    task = _task()
    task["input_json"]["acceptance_criteria"] = ["返回测试岗位内部证据"]

    result = evaluate_acceptance_coverage(store, ai_task=task, plan_id=plan["id"])

    assert result["blocked_reasons"] == []
    assert result["unmapped_criteria"] == []


def test_acceptance_coverage_plan_is_json_safe_for_postgres_timestamp_rows() -> None:
    store = MemoryStore()
    plan = create_acceptance_test_plan(
        store,
        created_by="user_admin",
        product_id="product_001",
        requirement_id="requirement_001",
        title="审批导出验收",
    )
    store.acceptance_test_plans[plan["id"]]["created_at"] = datetime(2026, 8, 4, tzinfo=UTC)

    result = evaluate_acceptance_coverage(store, ai_task=_task(), plan_id=plan["id"])

    assert result["plan"]["created_at"] == "2026-08-04T00:00:00+00:00"
    json.dumps(result)


def test_active_acceptance_plan_cannot_be_mutated_after_snapshot() -> None:
    store = MemoryStore()
    plan = create_acceptance_test_plan(
        store,
        created_by="user_admin",
        product_id="product_001",
        requirement_id="requirement_001",
        title="冻结验收范围",
    )
    activate_acceptance_test_plan(store, plan_id=plan["id"], user_id="user_admin")

    with pytest.raises(ValueError, match="immutable"):
        create_acceptance_test_case(
            store,
            case_code="acceptance.late_case",
            criterion="不得在激活后插入",
            created_by="user_admin",
            plan_id=plan["id"],
            title="后加用例",
        )


def test_file_contains_verification_rejects_paths_outside_the_workspace() -> None:
    store = MemoryStore()
    plan = create_acceptance_test_plan(
        store,
        created_by="user_admin",
        product_id="product_001",
        requirement_id="requirement_001",
        title="安全验收计划",
    )

    with pytest.raises(ValueError, match="path"):
        create_acceptance_test_case(
            store,
            case_code="acceptance.outside_workspace",
            criterion="不得读取工作区外文件",
            created_by="user_admin",
            plan_id=plan["id"],
            title="工作区边界",
            verification={
                "path": "../outside.txt",
                "required_text": ["not allowed"],
                "type": "file_contains",
            },
        )
