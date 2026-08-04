import base64
import json
from datetime import UTC, datetime
from types import SimpleNamespace

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.store import MemoryStore
from app.services.acceptance_test_plans import (
    acceptance_verification_fingerprint,
    activate_acceptance_test_plan,
    create_acceptance_test_case,
    create_acceptance_test_plan,
    record_acceptance_test_run,
)
from app.services.quality_gates import (
    _gate_run_and_checks,
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
            "git_delivery": {"local_commit_sha": "e2e-local-commit"},
            "workspace_isolation": {
                "base_workspace_root": "/workspace",
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


def test_repository_quality_gate_rows_are_json_safe_before_task_projection() -> None:
    class Repository:
        def list_quality_gate_runs(self, **_kwargs):
            return [
                {
                    "id": "gate-1",
                    "created_at": datetime(2026, 8, 4, tzinfo=UTC),
                    "policy_snapshot": {},
                }
            ]

        def list_quality_gate_checks(self, _run_id):
            return [{"id": "check-1", "updated_at": datetime(2026, 8, 4, tzinfo=UTC)}]

    run, checks = _gate_run_and_checks(SimpleNamespace(repository=Repository()), "gate-1")

    assert run is not None
    assert run["created_at"] == "2026-08-04 00:00:00+00:00"
    assert checks[0]["updated_at"] == "2026-08-04 00:00:00+00:00"
    json.dumps({"run": run, "checks": checks})


def _configure_isolated_verifier(store: MemoryStore) -> Ed25519PrivateKey:
    signing_key = Ed25519PrivateKey.generate()
    public_key = signing_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    store.ai_executor_runners.update(
        {
            "runner_001": {
                "attestation_status": "active",
                "executor_types": ["codex"],
                "id": "runner_001",
                "status": "active",
                "trust_boundary_id": "coding-pool-a",
                "trust_domain": "coding",
            },
            "runner_verifier_001": {
                "attestation_public_key": base64.b64encode(public_key).decode("ascii"),
                "attestation_status": "active",
                "executor_types": ["codex"],
                "id": "runner_verifier_001",
                "status": "active",
                "trust_boundary_id": "verification-pool-a",
                "trust_domain": "verification",
            },
        }
    )
    return signing_key


def _signed_attestation(
    signing_key: Ed25519PrivateKey,
    *,
    result_json: dict,
    runner_task_id: str,
) -> dict:
    signed_result = {
        key: value for key, value in result_json.items() if key != "execution_attestation"
    }
    result_sha256 = __import__("hashlib").sha256(
        json.dumps(
            signed_result,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    payload = {
        "result_sha256": result_sha256,
        "runner_task_id": runner_task_id,
        "status": "succeeded",
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "payload": payload,
        "signature": base64.b64encode(signing_key.sign(serialized)).decode("ascii"),
    }


def test_quality_gate_reconstructs_commit_from_durable_base_workspace() -> None:
    store = MemoryStore()

    _, verifier = start_pre_merge_quality_gate(
        store,
        ai_task=_ai_task(),
        coding_runner_task=_coding_task(),
        executor_policy={"code_change_review_mode": "auto_commit"},
    )

    assert verifier["workspace_root"] == "/workspace"
    assert verifier["input_payload"]["base_branch"] == "e2e-local-commit^"
    assert verifier["input_payload"]["expected_commit_sha"] == "e2e-local-commit"


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
        "REQUIRED_CHECK_FAILED",
        "VERIFIER_ATTESTATION_REQUIRED",
    }
    unit_check = next(
        check
        for check in store.quality_gate_checks.values()
        if check["quality_gate_run_id"] == run["id"] and check["check_type"] == "unit_test"
    )
    assert unit_check["source"] == "platform_verifier"


def test_quality_gate_never_reuses_coding_runner_when_verifier_is_unavailable() -> None:
    store = MemoryStore()
    coding_task = _coding_task()
    store.ai_executor_runners["runner_001"] = {
        "attestation_status": "active",
        "executor_types": ["codex"],
        "id": "runner_001",
        "status": "active",
        "trust_boundary_id": "coding-pool-a",
        "trust_domain": "coding",
    }

    _, verifier = start_pre_merge_quality_gate(
        store,
        ai_task=_ai_task(),
        coding_runner_task=coding_task,
        executor_policy={"code_change_review_mode": "auto_commit"},
    )

    assert verifier["runner_id"] == ""
    assert verifier["status"] == "blocked"
    assert verifier["request_config"]["trust_isolation_required"] is True


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
    assert {check["source"] for check in checks if check["check_type"] != "secret_scan"} == {
        "platform_verifier"
    }


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
                "changed_files": ["apps/api/app/db/migrations/103_sensitive_change.sql"],
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


def test_auto_merge_requires_verified_attestation_from_an_isolated_verifier() -> None:
    passed_without_proof = {
        "blocked_reasons": [],
        "status": "passed",
        "verified_attestation_count": 0,
        "verifier_trust_isolated": False,
    }
    passed_with_proof = {
        **passed_without_proof,
        "verified_attestation_count": 1,
        "verifier_trust_isolated": True,
    }

    assert not quality_gate_allows_auto_merge(passed_without_proof)
    assert quality_gate_allows_auto_merge(passed_with_proof)


def test_isolated_verifier_attestation_allows_auto_merge() -> None:
    store = MemoryStore()
    signing_key = _configure_isolated_verifier(store)
    coding_task = _coding_task()
    store.ai_executor_tasks[coding_task["id"]] = coding_task
    _, verifier = start_pre_merge_quality_gate(
        store,
        ai_task=_ai_task(),
        coding_runner_task=coding_task,
        executor_policy={"code_change_review_mode": "auto_commit"},
    )

    assert verifier["runner_id"] == "runner_verifier_001"
    result_json = {
        "changed_files": ["apps/api/app/services/example.py"],
        "changed_lines": 2,
        "checks": _reported_checks(),
        "risk_findings": [],
    }
    result_json["execution_attestation"] = _signed_attestation(
        signing_key,
        result_json=result_json,
        runner_task_id=verifier["id"],
    )
    verifier.update({"result_json": result_json, "status": "succeeded"})

    completed = complete_pre_merge_quality_gate(store, verifier_runner_task=verifier)

    assert completed is not None
    assert completed["status"] == "passed"
    assert completed["blocked_reasons"] == []
    assert completed["verified_attestation_count"] == 1
    assert completed["verifier_trust_isolated"] is True
    assert quality_gate_allows_auto_merge(completed)


def test_tampered_verifier_result_cannot_reuse_an_attestation() -> None:
    store = MemoryStore()
    signing_key = _configure_isolated_verifier(store)
    coding_task = _coding_task()
    store.ai_executor_tasks[coding_task["id"]] = coding_task
    _, verifier = start_pre_merge_quality_gate(
        store,
        ai_task=_ai_task(),
        coding_runner_task=coding_task,
        executor_policy={"code_change_review_mode": "auto_commit"},
    )

    result_json = {
        "changed_files": ["apps/api/app/services/example.py"],
        "changed_lines": 2,
        "checks": _reported_checks(),
        "risk_findings": [],
        "summary": "verified source result",
    }
    result_json["execution_attestation"] = _signed_attestation(
        signing_key,
        result_json=result_json,
        runner_task_id=verifier["id"],
    )
    result_json["summary"] = "tampered after signing"
    verifier.update({"result_json": result_json, "status": "succeeded"})

    completed = complete_pre_merge_quality_gate(store, verifier_runner_task=verifier)

    assert completed is not None
    assert not quality_gate_allows_auto_merge(completed)
    assert "VERIFIER_ATTESTATION_REQUIRED" in {
        reason["code"] for reason in completed["blocked_reasons"]
    }


def test_verified_acceptance_case_results_complete_the_pre_merge_acceptance_gate() -> None:
    store = MemoryStore()

    class CompletionBundleRepository:
        def __init__(self) -> None:
            self.bundles: list[dict] = []

        def save_quality_gate_completion_bundle_record(self, **payload) -> None:
            self.bundles.append(payload)

    completion_repository = CompletionBundleRepository()
    store.repository = completion_repository
    signing_key = _configure_isolated_verifier(store)
    task = {
        **_ai_task(),
        "input_json": {"acceptance_criteria": ["交付说明包含验收标记"]},
        "requirement_id": "requirement_001",
    }
    coding_task = _coding_task()
    store.ai_tasks[task["id"]] = task
    store.ai_executor_tasks[coding_task["id"]] = coding_task
    plan = create_acceptance_test_plan(
        store,
        created_by="user_admin",
        product_id=task["product_id"],
        requirement_id=task["requirement_id"],
        title="E2E 交付验收",
    )
    case = create_acceptance_test_case(
        store,
        case_code="acceptance.delivery_marker",
        criterion="交付说明包含验收标记",
        created_by="user_admin",
        plan_id=plan["id"],
        title="验收标记存在",
        verification={
            "path": "docs/e2e/delivery.md",
            "required_text": ["ACCEPTANCE-MARKER"],
            "type": "file_contains",
        },
    )
    activate_acceptance_test_plan(store, plan_id=plan["id"], user_id="user_admin")

    run, verifier = start_pre_merge_quality_gate(
        store,
        ai_task=task,
        coding_runner_task=coding_task,
        executor_policy={"code_change_review_mode": "auto_commit"},
    )

    assert run["policy_snapshot"]["acceptance_plan_id"] == plan["id"]
    assert verifier["input_payload"]["acceptance_cases"] == [
        {
            "case_id": case["id"],
            "verification": {
                "path": "docs/e2e/delivery.md",
                "required_text": ["ACCEPTANCE-MARKER"],
                "type": "file_contains",
            },
        }
    ]
    replacement_plan = create_acceptance_test_plan(
        store,
        created_by="user_admin",
        product_id=task["product_id"],
        requirement_id=task["requirement_id"],
        title="Replacement acceptance plan",
    )
    create_acceptance_test_case(
        store,
        case_code="acceptance.replacement",
        criterion="交付说明包含验收标记",
        created_by="user_admin",
        plan_id=replacement_plan["id"],
        title="Replacement acceptance case",
    )
    activate_acceptance_test_plan(store, plan_id=replacement_plan["id"], user_id="user_admin")
    result_json = {
        "acceptance_results": [
            {
                "artifact_ref": "runner://runner_verifier_001/gate/acceptance-marker",
                "case_id": case["id"],
                "commit_sha": "e2e-local-commit",
                "input_fingerprint": acceptance_verification_fingerprint(
                    {
                        "path": "docs/e2e/delivery.md",
                        "required_text": ["ACCEPTANCE-MARKER"],
                        "type": "file_contains",
                    }
                ),
                "status": "passed",
            }
        ],
        "changed_files": ["docs/e2e/delivery.md"],
        "changed_lines": 3,
        "checks": _reported_checks(),
        "risk_findings": [],
    }
    result_json["execution_attestation"] = _signed_attestation(
        signing_key,
        result_json=result_json,
        runner_task_id=verifier["id"],
    )
    verifier.update({"result_json": result_json, "status": "succeeded"})

    completed = complete_pre_merge_quality_gate(store, verifier_runner_task=verifier)

    assert completed is not None
    assert completed["status"] == "passed"
    assert completed["blocked_reasons"] == []
    assert completed["policy_snapshot"]["acceptance_coverage"]["unmapped_criteria"] == []
    acceptance_runs = list(store.acceptance_test_runs.values())
    assert acceptance_runs == [
        {
            "artifact_ref": "runner://runner_verifier_001/gate/acceptance-marker",
            "case_id": case["id"],
            "commit_sha": "e2e-local-commit",
            "input_fingerprint": acceptance_verification_fingerprint(
                {
                    "path": "docs/e2e/delivery.md",
                    "required_text": ["ACCEPTANCE-MARKER"],
                    "type": "file_contains",
                }
            ),
            "plan_id": plan["id"],
            "product_id": task["product_id"],
            "quality_gate_run_id": run["id"],
            "status": "passed",
            "verifier_task_id": verifier["id"],
            "id": acceptance_runs[0]["id"],
            "created_at": acceptance_runs[0]["created_at"],
            "updated_at": acceptance_runs[0]["updated_at"],
        }
    ]
    assert len(completion_repository.bundles) == 1
    completion_bundle = completion_repository.bundles[0]
    assert completion_bundle["acceptance_runs"] == acceptance_runs
    assert completion_bundle["run"] == completed
    assert completion_bundle["checks"] == [
        check
        for check in store.quality_gate_checks.values()
        if check["quality_gate_run_id"] == run["id"]
    ]
    assert completion_bundle["audit_events"]


def test_historic_acceptance_result_cannot_complete_a_new_quality_gate() -> None:
    store = MemoryStore()
    signing_key = _configure_isolated_verifier(store)
    task = {
        **_ai_task(),
        "input_json": {"acceptance_criteria": ["交付说明包含验收标记"]},
        "requirement_id": "requirement_001",
    }
    coding_task = _coding_task()
    store.ai_tasks[task["id"]] = task
    store.ai_executor_tasks[coding_task["id"]] = coding_task
    plan = create_acceptance_test_plan(
        store,
        created_by="user_admin",
        product_id=task["product_id"],
        requirement_id=task["requirement_id"],
        title="范围隔离验收计划",
    )
    case = create_acceptance_test_case(
        store,
        case_code="acceptance.delivery_marker",
        criterion="交付说明包含验收标记",
        created_by="user_admin",
        plan_id=plan["id"],
        title="验收标记存在",
        verification={
            "path": "docs/e2e/delivery.md",
            "required_text": ["ACCEPTANCE-MARKER"],
            "type": "file_contains",
        },
    )
    activate_acceptance_test_plan(store, plan_id=plan["id"], user_id="user_admin")
    historical_fingerprint = acceptance_verification_fingerprint(
        {
            "path": "docs/e2e/delivery.md",
            "required_text": ["ACCEPTANCE-MARKER"],
            "type": "file_contains",
        }
    )
    record_acceptance_test_run(
        store,
        artifact_ref="runner://historic/acceptance-marker",
        case_id=case["id"],
        commit_sha="e2e-local-commit",
        input_fingerprint=historical_fingerprint,
        status="passed",
        verifier_task_id="historic_verifier_task",
    )
    _, verifier = start_pre_merge_quality_gate(
        store,
        ai_task=task,
        coding_runner_task=coding_task,
        executor_policy={"code_change_review_mode": "auto_commit"},
    )
    result_json = {
        "acceptance_results": [],
        "changed_files": ["docs/e2e/delivery.md"],
        "changed_lines": 3,
        "checks": _reported_checks(),
        "risk_findings": [],
    }
    result_json["execution_attestation"] = _signed_attestation(
        signing_key,
        result_json=result_json,
        runner_task_id=verifier["id"],
    )
    verifier.update({"result_json": result_json, "status": "succeeded"})

    completed = complete_pre_merge_quality_gate(store, verifier_runner_task=verifier)

    assert completed is not None
    assert not quality_gate_allows_auto_merge(completed)
    assert "ACCEPTANCE_GATE_BLOCKED" in {
        reason["code"] for reason in completed["blocked_reasons"]
    }


def test_untrusted_verifier_cannot_write_acceptance_results() -> None:
    store = MemoryStore()
    _configure_isolated_verifier(store)
    task = {
        **_ai_task(),
        "input_json": {"acceptance_criteria": ["验证受信任来源"]},
        "requirement_id": "requirement_001",
    }
    coding_task = _coding_task()
    store.ai_tasks[task["id"]] = task
    store.ai_executor_tasks[coding_task["id"]] = coding_task
    plan = create_acceptance_test_plan(
        store,
        created_by="user_admin",
        product_id=task["product_id"],
        requirement_id=task["requirement_id"],
        title="受信任验收计划",
    )
    case = create_acceptance_test_case(
        store,
        case_code="acceptance.trusted_verifier",
        criterion="验证受信任来源",
        created_by="user_admin",
        plan_id=plan["id"],
        title="受信任验证",
        verification={
            "path": "docs/e2e/delivery.md",
            "required_text": ["TRUSTED"],
            "type": "file_contains",
        },
    )
    activate_acceptance_test_plan(store, plan_id=plan["id"], user_id="user_admin")
    _, verifier = start_pre_merge_quality_gate(
        store,
        ai_task=task,
        coding_runner_task=coding_task,
        executor_policy={"code_change_review_mode": "auto_commit"},
    )
    verifier.update(
        {
            "result_json": {
                "acceptance_results": [
                    {
                        "artifact_ref": "runner://untrusted/acceptance",
                        "case_id": case["id"],
                        "status": "passed",
                    }
                ],
                "changed_files": ["docs/e2e/delivery.md"],
                "changed_lines": 1,
                "checks": _reported_checks(),
                "risk_findings": [],
            },
            "status": "succeeded",
        }
    )

    completed = complete_pre_merge_quality_gate(store, verifier_runner_task=verifier)

    assert completed is not None
    assert store.acceptance_test_runs == {}
    assert "ACCEPTANCE_GATE_BLOCKED" in {
        reason["code"] for reason in completed["blocked_reasons"]
    }
