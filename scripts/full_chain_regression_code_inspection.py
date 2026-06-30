from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from full_chain_regression_version_dashboard import (
    validate_version_dashboard_blocker_actions,
    validate_version_dashboard_branch_quality,
    validate_version_dashboard_delivery_stage_overview,
    validate_version_dashboard_governance_conclusion,
    validate_version_dashboard_next_actions,
    validate_version_dashboard_status_impact,
)

FIXTURE_ROOT = Path(os.getenv("AI_BRAIN_FULL_CHAIN_FIXTURE_ROOT", "/tmp/e-ai-brain-full-chain-fixtures"))


@dataclass
class StepResult:
    name: str
    detail: str


def _slug() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"full-chain-{timestamp}"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _ids(items: list[dict[str, Any]]) -> set[str]:
    return {str(item["id"]) for item in items if item.get("id")}


def _assert_contains(container: set[str], expected: str, message: str) -> None:
    _assert(expected in container, f"{message}: expected {expected}, got {sorted(container)}")


def _git(args: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> None:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=merged_env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def create_fixture_repository(slug: str, branch: str) -> Path:
    repo_path = FIXTURE_ROOT / slug / "source-repo"
    if repo_path.exists():
        raise AssertionError(f"Fixture repository already exists: {repo_path}")
    repo_path.mkdir(parents=True)
    _git(["init", "-b", "main"], repo_path)
    _git(["config", "user.email", "full-chain@example.com"], repo_path)
    _git(["config", "user.name", "AI Brain Full Chain"], repo_path)
    (repo_path / "README.md").write_text("# AI Brain full-chain regression fixture\n", encoding="utf-8")
    _git(["add", "README.md"], repo_path)
    _git(["commit", "-m", "Initial full-chain fixture"], repo_path)
    _git(["checkout", "-b", branch], repo_path)
    source_dir = repo_path / "src"
    source_dir.mkdir()
    (source_dir / "settings.py").write_text(
        'API_KEY = "sk-full-chain-regression-secret"\n'
        'ADMIN_URL = "http://127.0.0.1:8080/admin"\n',
        encoding="utf-8",
    )
    _git(["add", "src/settings.py"], repo_path)
    _git(
        ["commit", "-m", "Add scan findings"],
        repo_path,
        env={
            "GIT_AUTHOR_EMAIL": "full-chain@example.com",
            "GIT_AUTHOR_NAME": "Full Chain Tester",
            "GIT_COMMITTER_EMAIL": "full-chain@example.com",
            "GIT_COMMITTER_NAME": "Full Chain Tester",
        },
    )
    return repo_path


def validate_code_inspection_governance_quick_regression(
    client: Any,
    *,
    username: str,
    password: str,
) -> list[StepResult]:
    slug = _slug()
    version_branch = f"inspection/{slug}"
    repo_path = create_fixture_repository(slug, version_branch)
    results: list[StepResult] = []

    user = client.login(username, password).get("user", {})
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    product = client.post(
        "/api/products",
        {
            "code": f"inspection-{slug}",
            "description": "自动代码巡检治理快速回归脚本创建的产品数据。",
            "name": f"代码巡检治理快速回归产品 {slug}",
            "status": "active",
        },
    )
    version = client.post(
        f"/api/products/{product['id']}/versions",
        {
            "code": f"inspection-{slug}",
            "description": "自动代码巡检治理快速回归版本。",
            "name": f"代码巡检治理快速回归版本 {slug}",
            "status": "active",
        },
    )
    results.append(StepResult("code_inspection_product", f"{product['id']} / {version['id']}"))

    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        {
            "default_branch": "main",
            "git_provider": "github",
            "name": f"代码巡检治理快速回归仓库 {slug}",
            "project_path": f"inspection/{slug}",
            "remote_url": str(repo_path),
            "repo_type": "code",
            "root_path": "/",
            "status": "active",
        },
    )
    branch_config = client.post(
        f"/api/product-versions/{version['id']}/branch-configs",
        {
            "base_branch": "main",
            "branch_status": "active",
            "creation_source": "manual",
            "description": "代码巡检治理快速回归分支。",
            "repository_id": repository["id"],
            "working_branch": version_branch,
        },
    )
    results.append(StepResult("code_inspection_branch", f"{branch_config['id']} / {version_branch}"))

    scan_config = {
        "async_execution": False,
        "branch": version_branch,
        "quality_gate": {
            "critical_max": 0,
            "enabled": True,
            "high_max": 0,
            "medium_max": 0,
        },
        "repository_id": repository["id"],
        "scan_mode": "native_full_scan",
        "scan_rules": ["secrets", "internal_addresses"],
    }
    scan_job = client.post(
        "/api/system/scheduled-jobs",
        {
            "config_json": scan_config,
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": f"代码巡检治理快速回归 {slug}",
            "product_id": product["id"],
            "result_actions": [
                {"type": "write_code_inspection_report"},
                {"severity_threshold": "critical", "type": "create_bug_for_severe_findings"},
                {"severity_threshold": "high", "type": "create_task_for_severe_findings"},
            ],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
    )
    scan_run = client.post(f"/api/system/scheduled-jobs/{scan_job['id']}/run")
    _assert(scan_run.get("status") == "succeeded", f"Code inspection run failed: {scan_run}")
    scan_run_summary = scan_run.get("result_summary") or {}
    native_scan_node = (scan_run_summary.get("execution_nodes") or {}).get("native_scan") or {}
    native_quality_gate = native_scan_node.get("quality_gate") or {}
    _assert(
        native_quality_gate.get("status") == "failed",
        f"Native scan did not fail the configured quality gate: {native_quality_gate}",
    )
    _assert(
        native_quality_gate.get("violations"),
        f"Native scan quality gate did not include violation details: {native_quality_gate}",
    )
    report_id = str(scan_run_summary.get("report_id") or "")
    _assert(report_id, f"Code inspection run did not return report_id: {scan_run}")

    report_detail = client.get(f"/api/governance/code-inspections/{report_id}")
    report = report_detail["report"]
    findings = report_detail.get("findings", [])
    scan_summary = report_detail.get("scan_summary") or {}
    governance_summary = report_detail.get("governance_summary") or {}
    report_quality_gate = report.get("quality_gate") or {}
    scan_summary_quality_gate = scan_summary.get("quality_gate") or {}
    _assert(report["scan_mode"] == "native_full_scan", "Report is not native_full_scan.")
    _assert(report["branch"] == version_branch, "Report branch does not match version branch.")
    _assert(report["repository_id"] == repository["id"], "Report repository does not match version repository.")
    _assert(
        report_quality_gate.get("status") == "failed",
        f"Report did not persist failed quality gate status: {report_quality_gate}",
    )
    _assert(
        scan_summary_quality_gate.get("status") == "failed",
        f"Detail scan summary did not expose failed quality gate status: {scan_summary_quality_gate}",
    )
    _assert(len(findings) >= 2, f"Native scan did not return expected findings: {findings}")
    for expected_rule in {"secrets.hardcoded_credential", "metadata.internal_address_exposure"}:
        _assert(
            any(finding.get("rule_id") == expected_rule for finding in findings),
            f"Native scan did not detect {expected_rule}: {findings}",
        )
    coverage = scan_summary.get("coverage") or {}
    _assert(int(coverage.get("files_scanned") or 0) >= 2, f"Scan coverage is incomplete: {coverage}")
    _assert(
        any(
            item.get("email") == "full-chain@example.com"
            for item in scan_summary.get("committer_distribution", [])
        ),
        f"Scan did not preserve committer attribution: {scan_summary.get('committer_distribution')}",
    )
    _assert(
        int(governance_summary.get("covered_by_bug_count") or 0) >= 1,
        f"Governance summary did not count Bug coverage: {governance_summary}",
    )
    _assert(
        int(governance_summary.get("covered_by_task_count") or 0) >= 1,
        f"Governance summary did not count remediation task coverage: {governance_summary}",
    )

    inspection_dashboard = client.get(
        "/api/governance/code-inspections/dashboard",
        {"product_id": product["id"], "repository_id": repository["id"]},
    )
    _assert(
        any(
            int(item.get("quality_gate_failed_count") or 0) >= 1
            for item in inspection_dashboard.get("trend", [])
        ),
        f"Code inspection dashboard trend missed quality gate failure: {inspection_dashboard.get('trend')}",
    )
    _assert(
        inspection_dashboard.get("quality_gate_violations"),
        f"Code inspection dashboard missed quality gate violation aggregation: {inspection_dashboard}",
    )
    governance_pressure = inspection_dashboard.get("governance_pressure") or {}
    _assert(
        governance_pressure.get("status") == "action_required",
        f"Code inspection governance pressure did not expose quality gate pressure: {governance_pressure}",
    )
    _assert(
        int(governance_pressure.get("quality_gate_failed_report_count") or 0) >= 1,
        f"Code inspection governance pressure missed failed report count: {governance_pressure}",
    )
    _assert(
        int(governance_pressure.get("quality_gate_violation_count") or 0) >= 1,
        f"Code inspection governance pressure missed violation count: {governance_pressure}",
    )
    _assert(
        int(governance_pressure.get("active_severe_finding_count") or 0) >= 1,
        f"Code inspection governance pressure missed active severe findings: {governance_pressure}",
    )
    _assert(
        int(governance_pressure.get("uncovered_bug_finding_count") or 0) == 0,
        f"Code inspection governance pressure did not close Bug coverage: {governance_pressure}",
    )
    _assert(
        int(governance_pressure.get("uncovered_task_finding_count") or 0) == 0,
        f"Code inspection governance pressure did not close remediation coverage: {governance_pressure}",
    )

    committer_governance = [
        item
        for item in inspection_dashboard.get("committer_governance", [])
        if item.get("email") == "full-chain@example.com"
    ]
    _assert(
        committer_governance,
        f"Code inspection dashboard missed committer governance queue: {inspection_dashboard}",
    )
    committer_governance_item = committer_governance[0]
    _assert(
        committer_governance_item.get("status") == "healthy",
        f"Code inspection committer governance did not close the loop: {committer_governance_item}",
    )
    _assert(
        int(committer_governance_item.get("active_severe_finding_count") or 0) >= 1,
        f"Code inspection committer governance missed active severe findings: {committer_governance_item}",
    )
    _assert(
        int(committer_governance_item.get("covered_by_bug_count") or 0) >= 1,
        f"Code inspection committer governance missed Bug coverage: {committer_governance_item}",
    )
    _assert(
        int(committer_governance_item.get("covered_by_task_count") or 0) >= 1,
        f"Code inspection committer governance missed remediation task coverage: {committer_governance_item}",
    )

    report_bug_ids = {str(item) for item in report.get("created_bug_ids") or []}
    report_task_ids = {str(item) for item in report.get("created_task_ids") or []}
    _assert(report_bug_ids, f"Code inspection report did not record created Bug ids: {report}")
    _assert(report_task_ids, f"Code inspection report did not record created remediation task ids: {report}")
    bugs = client.get("/api/bugs", {"product_id": product["id"], "source": "code_inspection"})
    bug_items = bugs.get("items", [])
    bug_ids = _ids(bug_items)
    for bug_id in report_bug_ids:
        _assert_contains(bug_ids, bug_id, "Code inspection Bug writeback missing from Bug list")
    _assert(
        all(
            item.get("evidence", {}).get("code_inspection_report_id") == report_id
            for item in bug_items
            if item["id"] in report_bug_ids
        ),
        "Code inspection Bug evidence did not point back to the report.",
    )
    remediation_tasks = client.get(
        "/api/ai-tasks",
        {"product_id": product["id"], "task_type": "code_inspection_remediation"},
    )
    remediation_task_ids = _ids(remediation_tasks.get("items", []))
    for remediation_task_id in report_task_ids:
        _assert_contains(
            remediation_task_ids,
            remediation_task_id,
            "Code inspection remediation task writeback missing from AI task list",
        )

    results.append(StepResult("code_inspection", f"{report_id} / findings={len(findings)} / {scan_run['id']}"))
    results.append(
        StepResult(
            "code_inspection_governance_pressure",
            (
                f"status={governance_pressure.get('status')}, "
                f"gate_failures={governance_pressure.get('quality_gate_failed_report_count')}, "
                f"uncovered_bug={governance_pressure.get('uncovered_bug_finding_count')}, "
                f"uncovered_task={governance_pressure.get('uncovered_task_finding_count')}"
            ),
        )
    )
    results.append(
        StepResult(
            "inspection_writeback",
            f"bugs={len(report_bug_ids)}, tasks={len(report_task_ids)}",
        )
    )

    comparison_scan_job = client.post(
        "/api/system/scheduled-jobs",
        {
            "config_json": scan_config,
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": f"代码巡检治理趋势对比 {slug}",
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
    )
    comparison_scan_run = client.post(f"/api/system/scheduled-jobs/{comparison_scan_job['id']}/run")
    _assert(
        comparison_scan_run.get("status") == "succeeded",
        f"Code inspection comparison run failed: {comparison_scan_run}",
    )
    comparison_report_id = str((comparison_scan_run.get("result_summary") or {}).get("report_id") or "")
    _assert(
        comparison_report_id,
        f"Code inspection comparison run did not return report_id: {comparison_scan_run}",
    )
    comparison_report_detail = client.get(f"/api/governance/code-inspections/{comparison_report_id}")
    comparison_report = comparison_report_detail["report"]
    comparison_previous = (
        (comparison_report_detail.get("scan_summary") or {}).get("previous_comparison")
        or comparison_report.get("previous_comparison")
        or {}
    )
    _assert(
        comparison_report.get("previous_report_id") == report_id,
        f"Comparison report did not persist previous_report_id={report_id}: {comparison_report}",
    )
    _assert(
        comparison_previous.get("previous_report_id") == report_id,
        f"Comparison report missed previous comparison report id: {comparison_previous}",
    )
    _assert(
        int(comparison_previous.get("previous_finding_count") or -1)
        == int(report.get("finding_count") or 0),
        f"Comparison report previous finding count mismatch: {comparison_previous}",
    )
    _assert(
        int(comparison_previous.get("finding_delta") or 0) == 0,
        f"Comparison report should have stable finding_delta for unchanged fixture: {comparison_previous}",
    )
    _assert(
        int(comparison_previous.get("severe_finding_delta") or 0) == 0,
        f"Comparison report should have stable severe_finding_delta: {comparison_previous}",
    )
    results.append(
        StepResult(
            "code_inspection_trend_comparison",
            f"{comparison_report_id} / previous={comparison_previous.get('previous_report_id')}",
        )
    )

    dashboard = client.get(f"/api/product-versions/{version['id']}/dashboard")
    _assert_contains(
        _ids(dashboard.get("branch_configs", [])),
        branch_config["id"],
        "Version dashboard missed code inspection branch config",
    )
    _assert_contains(
        _ids(dashboard.get("code_inspection_reports", [])),
        report_id,
        "Version dashboard missed code inspection report row",
    )
    branch_quality = validate_version_dashboard_branch_quality(
        dashboard,
        branch_config_id=branch_config["id"],
        branch_name=version_branch,
        expected_status="action_required",
        report_id=comparison_report_id,
    )
    dashboard_blockers = dashboard.get("blockers", [])
    validate_version_dashboard_blocker_actions(dashboard_blockers)
    validate_version_dashboard_next_actions(dashboard, dashboard_blockers)
    validate_version_dashboard_governance_conclusion(dashboard, dashboard_blockers)
    validate_version_dashboard_delivery_stage_overview(dashboard)
    validate_version_dashboard_status_impact(dashboard)
    inspection_blockers = [
        blocker
        for blocker in dashboard_blockers
        if blocker.get("source_type") == "code_inspection_report"
        and str(blocker.get("action_target_id")) == report_id
    ]
    _assert(inspection_blockers, "Version dashboard missed actionable code inspection blocker.")
    bug_blockers = [
        blocker
        for blocker in dashboard_blockers
        if blocker.get("source_type") == "bug" and str(blocker.get("action_target_id")) in report_bug_ids
    ]
    _assert(bug_blockers, "Version dashboard missed actionable Bug blocker.")
    results.append(
        StepResult(
            "version_dashboard_code_inspection_governance",
            f"blockers={dashboard['summary']['blockers']} / branch_quality={branch_quality['status']}",
        )
    )
    results.append(StepResult("fixture_repository", str(repo_path)))
    return results
