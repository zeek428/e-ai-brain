from __future__ import annotations

import fnmatch
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.services.ai_executor_task_creation import create_ai_executor_task
from app.services.operational_records import read_memory_dict, record_audit_event

DEFAULT_PRE_MERGE_POLICY = {
    "id": "quality_gate_policy_system_pre_merge",
    "name": "系统默认研发合并门禁",
    "phase": "pre_merge",
    "product_id": None,
    "task_type": None,
    "risk_levels": ["low", "medium", "high", "critical"],
    "required_checks": [
        {
            "catalog_code": "project.unit_test",
            "independent": True,
            "required": True,
            "type": "unit_test",
        },
        {
            "catalog_code": "project.type_check",
            "independent": True,
            "required": True,
            "type": "type_check",
        },
        {
            "catalog_code": "platform.secret_scan",
            "independent": True,
            "required": True,
            "type": "secret_scan",
        },
    ],
    "protected_paths": [
        "**/migrations/**",
        "**/auth/**",
        "**/permissions/**",
        "**/*secret*",
        "docker-compose*.yml",
    ],
    "max_changed_files": 60,
    "max_changed_lines": 2000,
    "required_ci_contexts": [],
    "minimum_independent_evidence": 1,
    "manual_review_on_migration": True,
    "status": "active",
    "version": 1,
}
RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
AUTO_MERGE_RISK_ORDER = {"none": -1, "low": 0, "medium": 1}
ALLOWED_EVIDENCE_SOURCES = {
    "ci_webhook",
    "human_approval",
    "platform_scan",
    "platform_verifier",
}
MANUAL_REVIEW_REASON_CODES = {
    "DATABASE_MIGRATION_REQUIRES_MANUAL_REVIEW",
    "HIGH_RISK_TASK_REQUIRES_MANUAL_REVIEW",
    "PROTECTED_PATH_REQUIRES_MANUAL_REVIEW",
}


def _policy_candidates(current_store: Any) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_policies = getattr(repository, "list_quality_gate_policies", None)
    if callable(list_policies):
        return list(list_policies(phase="pre_merge", status="active"))
    return [
        dict(policy)
        for policy in read_memory_dict(current_store, "quality_gate_policies").values()
        if policy.get("phase") == "pre_merge" and policy.get("status") == "active"
    ]


def resolve_pre_merge_quality_gate_policy(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    executor_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    explicit_id = str((executor_policy or {}).get("quality_gate_policy_id") or "").strip()
    candidates = _policy_candidates(current_store)
    if explicit_id:
        explicit = next((item for item in candidates if item.get("id") == explicit_id), None)
        if explicit is not None:
            return explicit
    product_id = str(ai_task.get("product_id") or "").strip()
    task_type = str(ai_task.get("task_type") or "").strip()
    matching = [
        policy
        for policy in candidates
        if policy.get("product_id") in {None, "", product_id}
        and policy.get("task_type") in {None, "", task_type}
    ]
    if not matching:
        return deepcopy(DEFAULT_PRE_MERGE_POLICY)
    matching.sort(
        key=lambda policy: (
            int(bool(policy.get("product_id"))),
            int(bool(policy.get("task_type"))),
            int(policy.get("version") or 1),
        ),
        reverse=True,
    )
    return deepcopy(matching[0])


def _task_risk_level(ai_task: dict[str, Any]) -> str:
    input_json = ai_task.get("input_json") if isinstance(ai_task.get("input_json"), dict) else {}
    bug = input_json.get("bug") if isinstance(input_json.get("bug"), dict) else {}
    for value in (
        input_json.get("risk_level"),
        input_json.get("severity"),
        bug.get("severity"),
    ):
        normalized = str(value or "").strip().lower()
        if normalized in RISK_ORDER:
            return normalized
        if normalized in {"fatal", "blocker"}:
            return "critical"
    return "low"


def _required_check_records(
    current_store: Any,
    *,
    now: str,
    policy: dict[str, Any],
    run_id: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for definition in policy.get("required_checks") or []:
        if not isinstance(definition, dict):
            continue
        check_type = str(definition.get("type") or "").strip()
        if not check_type:
            continue
        checks.append(
            {
                "id": current_store.new_id("quality_gate_check"),
                "quality_gate_run_id": run_id,
                "check_type": check_type,
                "status": "pending",
                "source": "platform_scan"
                if check_type in {"dangerous_command_scan", "dependency_scan", "secret_scan"}
                else "platform_verifier",
                "required": bool(definition.get("required", True)),
                "independent": bool(definition.get("independent", True)),
                "evidence_ref": None,
                "command_catalog_code": definition.get("catalog_code"),
                "exit_code": None,
                "duration_ms": None,
                "summary": None,
                "details": {},
                "started_at": None,
                "finished_at": None,
                "created_at": now,
                "updated_at": now,
            }
        )
    return checks


def _save_gate_bundle(
    current_store: Any,
    *,
    audit_events: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    run: dict[str, Any],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_bundle = getattr(repository, "save_quality_gate_bundle_record", None)
    if callable(save_bundle):
        save_bundle(audit_events=audit_events, checks=checks, run=run)
        return
    read_memory_dict(current_store, "quality_gate_runs")[run["id"]] = deepcopy(run)
    check_store = read_memory_dict(current_store, "quality_gate_checks")
    for check in checks:
        check_store[check["id"]] = deepcopy(check)


def start_pre_merge_quality_gate(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    coding_runner_task: dict[str, Any],
    executor_policy: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    now = datetime.now(UTC).isoformat()
    policy = resolve_pre_merge_quality_gate_policy(
        current_store,
        ai_task=ai_task,
        executor_policy=executor_policy,
    )
    run_id = current_store.new_id("quality_gate_run")
    run = {
        "id": run_id,
        "policy_id": policy.get("id"),
        "policy_snapshot": deepcopy(policy),
        "phase": "pre_merge",
        "subject_type": "ai_task",
        "subject_id": ai_task["id"],
        "product_id": ai_task.get("product_id"),
        "context_manifest_id": coding_runner_task.get("context_manifest_id"),
        "status": "running",
        "risk_level": _task_risk_level(ai_task),
        "independent_evidence_count": 0,
        "summary": "正在执行独立合并前质量门禁",
        "blocked_reasons": [],
        "started_at": now,
        "finished_at": None,
        "created_by": ai_task.get("created_by"),
        "created_at": now,
        "updated_at": now,
    }
    checks = _required_check_records(
        current_store,
        now=now,
        policy=policy,
        run_id=run_id,
    )
    created_audit = record_audit_event(
        current_store,
        event_type="quality_gate.started",
        actor_id=str(ai_task.get("created_by") or "system"),
        subject_type="quality_gate_run",
        subject_id=run_id,
        payload={
            "ai_task_id": ai_task["id"],
            "context_manifest_id": run.get("context_manifest_id"),
            "policy_id": policy.get("id"),
            "risk_level": run["risk_level"],
        },
    )
    _save_gate_bundle(
        current_store,
        audit_events=[created_audit],
        checks=checks,
        run=run,
    )
    coding_result = (
        coding_runner_task.get("result_json")
        if isinstance(coding_runner_task.get("result_json"), dict)
        else {}
    )
    workspace_isolation = (
        coding_result.get("workspace_isolation")
        if isinstance(coding_result.get("workspace_isolation"), dict)
        else {}
    )
    workspace_root = str(
        workspace_isolation.get("worktree_path")
        or coding_runner_task.get("workspace_root")
        or ""
    )
    verifier_task = create_ai_executor_task(
        current_store,
        action_id=None,
        agent_loop_iteration_id=coding_runner_task.get("agent_loop_iteration_id"),
        agent_loop_run_id=coding_runner_task.get("agent_loop_run_id"),
        ai_task_id=ai_task["id"],
        connection_id=None,
        context_manifest_id=run.get("context_manifest_id"),
        created_by=str(ai_task.get("created_by") or "system"),
        executor_type=str(coding_runner_task.get("executor_type") or "codex"),
        input_payload={
            "base_branch": (coding_runner_task.get("request_config") or {}).get("branch"),
            "checks": [
                {
                    "catalog_code": check.get("command_catalog_code"),
                    "required": check.get("required"),
                    "type": check["check_type"],
                }
                for check in checks
            ],
            "coding_runner_task_id": coding_runner_task["id"],
            "max_changed_files": policy.get("max_changed_files"),
            "max_changed_lines": policy.get("max_changed_lines"),
            "protected_paths": policy.get("protected_paths") or [],
            "quality_gate_run_id": run_id,
        },
        instruction=(
            "Execute the platform-defined deterministic quality gate catalog. "
            "Do not modify repository files. Return structured evidence for every check."
        ),
        plugin_invocation_log_id=None,
        quality_gate_run_id=run_id,
        request_config={
            "coding_runner_task_id": coding_runner_task["id"],
            "context_manifest_id": run.get("context_manifest_id"),
            "source": "platform_quality_gate",
        },
        runner_id=str(coding_runner_task.get("runner_id") or ""),
        scheduled_job_id=None,
        scheduled_job_run_id=None,
        task_kind="quality_gate",
        timeout_seconds=int(coding_runner_task.get("timeout_seconds") or 1800),
        workspace_root=workspace_root,
    )
    run["policy_snapshot"] = {
        **run["policy_snapshot"],
        "coding_runner_task_id": coding_runner_task["id"],
        "verifier_runner_task_id": verifier_task["id"],
    }
    _save_gate_bundle(current_store, audit_events=[], checks=checks, run=run)
    return deepcopy(run), verifier_task


def _gate_run_and_checks(
    current_store: Any,
    quality_gate_run_id: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_quality_gate_runs", None)
    list_checks = getattr(repository, "list_quality_gate_checks", None)
    if callable(list_runs) and callable(list_checks):
        runs = list(list_runs(subject_id=None, subject_type=None))
        run = next((item for item in runs if item.get("id") == quality_gate_run_id), None)
        return run, list(list_checks(quality_gate_run_id)) if run else []
    run = read_memory_dict(current_store, "quality_gate_runs").get(quality_gate_run_id)
    checks = [
        check
        for check in read_memory_dict(current_store, "quality_gate_checks").values()
        if check.get("quality_gate_run_id") == quality_gate_run_id
    ]
    return deepcopy(run) if run else None, [deepcopy(check) for check in checks]


def _matches_protected_path(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def complete_pre_merge_quality_gate(
    current_store: Any,
    *,
    verifier_runner_task: dict[str, Any],
) -> dict[str, Any] | None:
    run_id = str(verifier_runner_task.get("quality_gate_run_id") or "").strip()
    if not run_id:
        return None
    run, checks = _gate_run_and_checks(current_store, run_id)
    if run is None:
        return None
    now = datetime.now(UTC).isoformat()
    result = (
        verifier_runner_task.get("result_json")
        if isinstance(verifier_runner_task.get("result_json"), dict)
        else {}
    )
    reported_checks = {
        str(item.get("type") or ""): item
        for item in result.get("checks") or []
        if isinstance(item, dict) and str(item.get("type") or "").strip()
    }
    verifier_succeeded = verifier_runner_task.get("status") == "succeeded"
    for check in checks:
        reported = reported_checks.get(check["check_type"], {})
        reported_status = str(reported.get("status") or "failed")
        evidence_ref = str(reported.get("evidence_ref") or "").strip() or None
        source = str(check.get("source") or "platform_verifier")
        if source not in ALLOWED_EVIDENCE_SOURCES:
            source = "platform_verifier"
        passed = verifier_succeeded and reported_status in {"passed", "skipped"}
        if check.get("required") and not evidence_ref:
            passed = False
        check.update(
            {
                "status": reported_status if passed else "failed",
                "source": source,
                "independent": bool(check.get("independent"))
                and source in ALLOWED_EVIDENCE_SOURCES,
                "evidence_ref": evidence_ref,
                "exit_code": reported.get("exit_code"),
                "duration_ms": reported.get("duration_ms"),
                "summary": reported.get("summary")
                or ("验证通过" if passed else "验证失败或缺少证据"),
                "details": reported.get("details") or {},
                "started_at": reported.get("started_at") or run.get("started_at"),
                "finished_at": reported.get("finished_at") or now,
                "updated_at": now,
            }
        )

    reasons: list[dict[str, Any]] = []
    failed_required = [
        check["check_type"]
        for check in checks
        if check.get("required") and check.get("status") != "passed"
    ]
    if failed_required:
        reasons.append(
            {
                "code": "REQUIRED_CHECK_FAILED",
                "details": {"checks": failed_required},
                "message": "必需的独立质量检查未全部通过",
            }
        )
    independent_evidence = {
        (str(check.get("source")), str(check.get("evidence_ref")))
        for check in checks
        if check.get("status") == "passed"
        and check.get("independent")
        and check.get("evidence_ref")
    }
    minimum_evidence = int(
        (run.get("policy_snapshot") or {}).get("minimum_independent_evidence") or 1
    )
    if len(independent_evidence) < minimum_evidence:
        reasons.append(
            {
                "code": "INDEPENDENT_EVIDENCE_MISSING",
                "details": {
                    "actual": len(independent_evidence),
                    "required": minimum_evidence,
                },
                "message": "独立验证证据数量不足",
            }
        )

    changed_files = [str(item) for item in result.get("changed_files") or []]
    changed_file_count = int(result.get("changed_file_count") or len(changed_files))
    changed_lines = int(result.get("changed_lines") or 0)
    policy = run.get("policy_snapshot") or {}
    max_files = policy.get("max_changed_files")
    max_lines = policy.get("max_changed_lines")
    if max_files is not None and changed_file_count > int(max_files):
        reasons.append(
            {
                "code": "CHANGE_FILE_LIMIT_EXCEEDED",
                "details": {"actual": changed_file_count, "maximum": int(max_files)},
                "message": "变更文件数量超过自动合并上限",
            }
        )
    if max_lines is not None and changed_lines > int(max_lines):
        reasons.append(
            {
                "code": "CHANGE_LINE_LIMIT_EXCEEDED",
                "details": {"actual": changed_lines, "maximum": int(max_lines)},
                "message": "代码变更行数超过自动合并上限",
            }
        )
    protected_files = [
        path
        for path in changed_files
        if _matches_protected_path(path, list(policy.get("protected_paths") or []))
    ]
    if protected_files:
        reasons.append(
            {
                "code": "PROTECTED_PATH_REQUIRES_MANUAL_REVIEW",
                "details": {"files": protected_files},
                "message": "变更包含受保护目录，必须人工确认",
            }
        )
    migration_files = [path for path in changed_files if "/migrations/" in f"/{path}"]
    if migration_files and bool(policy.get("manual_review_on_migration", True)):
        reasons.append(
            {
                "code": "DATABASE_MIGRATION_REQUIRES_MANUAL_REVIEW",
                "details": {"files": migration_files},
                "message": "数据库迁移变更必须人工确认",
            }
        )
    risk_threshold = str(policy.get("auto_merge_risk_threshold") or "low")
    if RISK_ORDER.get(str(run.get("risk_level")), 3) > AUTO_MERGE_RISK_ORDER.get(
        risk_threshold,
        0,
    ):
        reasons.append(
            {
                "code": "HIGH_RISK_TASK_REQUIRES_MANUAL_REVIEW",
                "details": {
                    "risk_level": run.get("risk_level"),
                    "threshold": risk_threshold,
                },
                "message": "任务风险等级超过自动合并阈值",
            }
        )
    risk_findings = [
        item
        for item in result.get("risk_findings") or []
        if isinstance(item, dict)
        and str(item.get("severity") or "high").lower() in {"high", "critical"}
    ]
    if risk_findings:
        reasons.append(
            {
                "code": "SECURITY_FINDING",
                "details": {"findings": risk_findings},
                "message": "独立安全扫描发现高风险问题",
            }
        )

    failure_reasons = [
        reason
        for reason in reasons
        if reason["code"] not in MANUAL_REVIEW_REASON_CODES
    ]
    run.update(
        {
            "status": "failed" if failure_reasons else "passed",
            "independent_evidence_count": len(independent_evidence),
            "summary": result.get("summary")
            or ("独立质量门禁通过" if not failure_reasons else "独立质量门禁未通过"),
            "blocked_reasons": reasons,
            "finished_at": now,
            "updated_at": now,
            "policy_snapshot": {
                **policy,
                "change_summary": {
                    "changed_file_count": changed_file_count,
                    "changed_files": changed_files,
                    "changed_lines": changed_lines,
                },
            },
        }
    )
    audit_event = record_audit_event(
        current_store,
        event_type=f"quality_gate.{run['status']}",
        actor_id=str(verifier_runner_task.get("runner_id") or "system"),
        subject_type="quality_gate_run",
        subject_id=run["id"],
        payload={
            "ai_task_id": run["subject_id"],
            "blocked_reasons": reasons,
            "independent_evidence_count": len(independent_evidence),
            "status": run["status"],
            "verifier_runner_task_id": verifier_runner_task.get("id"),
        },
    )
    _save_gate_bundle(
        current_store,
        audit_events=[audit_event],
        checks=checks,
        run=run,
    )
    return deepcopy(run)


def quality_gate_allows_auto_merge(run: dict[str, Any]) -> bool:
    return run.get("status") == "passed" and not run.get("blocked_reasons")


def latest_quality_gate_for_task(
    current_store: Any,
    *,
    product_scope_ids: list[str] | None,
    task_id: str,
) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_quality_gate_runs", None)
    list_checks = getattr(repository, "list_quality_gate_checks", None)
    if callable(list_runs) and callable(list_checks):
        runs = list(
            list_runs(
                phase="pre_merge",
                product_scope_ids=product_scope_ids,
                subject_id=task_id,
                subject_type="ai_task",
            )
        )
        if not runs:
            return None
        run = runs[0]
        return {**run, "checks": list(list_checks(run["id"]))}
    allowed_products = set(product_scope_ids or [])
    runs = [
        run
        for run in read_memory_dict(current_store, "quality_gate_runs").values()
        if run.get("subject_type") == "ai_task"
        and run.get("subject_id") == task_id
        and (product_scope_ids is None or run.get("product_id") in allowed_products)
    ]
    if not runs:
        return None
    run = max(runs, key=lambda item: str(item.get("created_at") or ""))
    checks = [
        deepcopy(check)
        for check in read_memory_dict(current_store, "quality_gate_checks").values()
        if check.get("quality_gate_run_id") == run["id"]
    ]
    return {**deepcopy(run), "checks": checks}


def create_pre_deploy_quality_gate(
    current_store: Any,
    *,
    deployment: dict[str, Any],
    checks: list[dict[str, Any]],
    actor_id: str,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    run_id = current_store.new_id("quality_gate_run")
    normalized_checks: list[dict[str, Any]] = []
    blocked_reasons: list[dict[str, Any]] = []
    for item in checks:
        passed = bool(item.get("passed"))
        required = bool(item.get("required", True))
        code = str(item.get("code") or "deployment_preflight")
        if required and not passed:
            blocked_reasons.append(
                {
                    "code": code.upper(),
                    "message": str(item.get("message") or f"{code} failed"),
                }
            )
        normalized_checks.append(
            {
                "id": current_store.new_id("quality_gate_check"),
                "quality_gate_run_id": run_id,
                "check_type": code,
                "status": "passed" if passed else "failed" if required else "skipped",
                "source": "platform_scan",
                "required": required,
                "independent": True,
                "evidence_ref": f"deployment:{deployment['id']}:{code}",
                "command_catalog_code": None,
                "exit_code": 0 if passed else None,
                "duration_ms": 0,
                "summary": str(
                    item.get("summary")
                    or ("检查通过" if passed else "检查未通过")
                ),
                "details": deepcopy(item.get("details") or {}),
                "started_at": now,
                "finished_at": now,
                "created_at": now,
                "updated_at": now,
            }
        )
    status = "passed" if not blocked_reasons else "blocked"
    run = {
        "id": run_id,
        "policy_id": "quality_gate_policy_system_pre_deploy",
        "policy_snapshot": {
            "id": "quality_gate_policy_system_pre_deploy",
            "name": "系统默认生产部署前门禁",
            "phase": "pre_deploy",
            "required_checks": [item["check_type"] for item in normalized_checks],
            "version": 1,
        },
        "phase": "pre_deploy",
        "subject_type": "deployment_request",
        "subject_id": deployment["id"],
        "product_id": deployment.get("product_id"),
        "context_manifest_id": None,
        "status": status,
        "risk_level": deployment.get("risk_level") or "medium",
        "independent_evidence_count": sum(
            1 for item in normalized_checks if item["status"] == "passed"
        ),
        "summary": "部署前质量门禁通过" if status == "passed" else "部署前质量门禁阻断",
        "blocked_reasons": blocked_reasons,
        "started_at": now,
        "finished_at": now,
        "created_by": actor_id,
        "created_at": now,
        "updated_at": now,
    }
    audit = record_audit_event(
        current_store,
        event_type=f"quality_gate.{status}",
        actor_id=actor_id,
        subject_type="quality_gate_run",
        subject_id=run_id,
        payload={
            "deployment_request_id": deployment["id"],
            "phase": "pre_deploy",
            "status": status,
        },
    )
    _save_gate_bundle(
        current_store,
        audit_events=[audit],
        checks=normalized_checks,
        run=run,
    )
    return deepcopy(run)
