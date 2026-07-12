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
