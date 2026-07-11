from app.core.store import MemoryStore
from app.services.quality_gates import (
    complete_pre_merge_quality_gate,
    quality_gate_allows_auto_merge,
    start_pre_merge_quality_gate,
)


def _ai_task() -> dict:
    return {
        "created_by": "user_admin",
        "id": "task_quality_001",
        "input_json": {},
        "product_id": "product_001",
        "task_type": "development_planning",
    }


def _coding_task() -> dict:
    return {
        "context_manifest_id": "execution_context_manifest_001",
        "executor_type": "codex",
        "id": "ai_executor_task_coding_001",
        "request_config": {"branch": "main"},
        "result_json": {
            "workspace_isolation": {
                "worktree_path": "/workspace/.ai-brain-worktrees/task_quality_001"
            }
        },
        "runner_id": "runner_001",
        "timeout_seconds": 600,
        "workspace_root": "/workspace",
    }


def _reported_checks(*, failed_type: str | None = None) -> list[dict]:
    return [
        {
            "evidence_ref": f"runner://runner_001/gate/{check_type}",
            "source": "runner_coding",
            "status": "failed" if check_type == failed_type else "passed",
            "summary": f"{check_type} result",
            "type": check_type,
        }
        for check_type in ("unit_test", "type_check", "secret_scan")
    ]


def test_failed_required_check_blocks_auto_merge() -> None:
    store = MemoryStore()
    run, verifier = start_pre_merge_quality_gate(
        store,
        ai_task=_ai_task(),
        coding_runner_task=_coding_task(),
        executor_policy={"code_change_review_mode": "auto_commit"},
    )
    verifier.update(
        {
            "result_json": {
                "changed_file_count": 1,
                "changed_files": ["apps/web/src/pages/Login/index.tsx"],
                "changed_lines": 8,
                "checks": _reported_checks(failed_type="unit_test"),
                "risk_findings": [],
            },
            "status": "succeeded",
        }
    )

    completed = complete_pre_merge_quality_gate(store, verifier_runner_task=verifier)

    assert completed is not None
    assert completed["status"] == "failed"
    assert not quality_gate_allows_auto_merge(completed)
    assert {reason["code"] for reason in completed["blocked_reasons"]} == {
        "REQUIRED_CHECK_FAILED"
    }
    unit_check = next(
        check
        for check in store.quality_gate_checks.values()
        if check["quality_gate_run_id"] == run["id"]
        and check["check_type"] == "unit_test"
    )
    assert unit_check["source"] == "platform_verifier"


def test_verifier_cannot_override_platform_evidence_source() -> None:
    store = MemoryStore()
    run, verifier = start_pre_merge_quality_gate(
        store,
        ai_task=_ai_task(),
        coding_runner_task=_coding_task(),
        executor_policy={"code_change_review_mode": "auto_commit"},
    )
    verifier.update(
        {
            "result_json": {
                "changed_files": ["apps/api/app/services/example.py"],
                "changed_lines": 2,
                "checks": [
                    {
                        **item,
                        "source": "human_approval",
                    }
                    for item in _reported_checks()
                ],
                "risk_findings": [],
            },
            "status": "succeeded",
        }
    )

    completed = complete_pre_merge_quality_gate(store, verifier_runner_task=verifier)

    assert completed is not None
    checks = [
        check
        for check in store.quality_gate_checks.values()
        if check["quality_gate_run_id"] == run["id"]
    ]
    assert {check["source"] for check in checks if check["check_type"] == "secret_scan"} == {
        "platform_scan"
    }
    assert {
        check["source"] for check in checks if check["check_type"] != "secret_scan"
    } == {"platform_verifier"}


def test_migration_and_protected_path_force_manual_review_after_checks_pass() -> None:
    store = MemoryStore()
    run, verifier = start_pre_merge_quality_gate(
        store,
        ai_task=_ai_task(),
        coding_runner_task=_coding_task(),
        executor_policy={"code_change_review_mode": "auto_commit"},
    )
    verifier.update(
        {
            "result_json": {
                "changed_file_count": 1,
                "changed_files": [
                    "apps/api/app/db/migrations/103_sensitive_change.sql"
                ],
                "changed_lines": 12,
                "checks": _reported_checks(),
                "risk_findings": [],
            },
            "status": "succeeded",
        }
    )

    completed = complete_pre_merge_quality_gate(store, verifier_runner_task=verifier)

    assert completed is not None
    assert completed["status"] == "passed"
    assert not quality_gate_allows_auto_merge(completed)
    reason_codes = {reason["code"] for reason in completed["blocked_reasons"]}
    assert "DATABASE_MIGRATION_REQUIRES_MANUAL_REVIEW" in reason_codes
    assert "PROTECTED_PATH_REQUIRES_MANUAL_REVIEW" in reason_codes


def test_high_risk_security_finding_blocks_auto_merge() -> None:
    store = MemoryStore()
    task = _ai_task()
    task["input_json"] = {"risk_level": "critical"}
    _, verifier = start_pre_merge_quality_gate(
        store,
        ai_task=task,
        coding_runner_task=_coding_task(),
        executor_policy={"code_change_review_mode": "auto_commit"},
    )
    verifier.update(
        {
            "result_json": {
                "changed_files": ["apps/api/app/services/auth/session.py"],
                "changed_lines": 4,
                "checks": _reported_checks(),
                "risk_findings": [
                    {
                        "code": "hardcoded_secret",
                        "severity": "critical",
                        "summary": "Potential credential detected",
                    }
                ],
            },
            "status": "succeeded",
        }
    )

    completed = complete_pre_merge_quality_gate(store, verifier_runner_task=verifier)

    assert completed is not None
    assert completed["status"] == "failed"
    reason_codes = {reason["code"] for reason in completed["blocked_reasons"]}
    assert "SECURITY_FINDING" in reason_codes
    assert "HIGH_RISK_TASK_REQUIRES_MANUAL_REVIEW" in reason_codes
