from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error

RUNNER_SAFETY_POLICY_VERSION = "runner_safety_v1"
APPROVAL_MODES = {"manual_review_approved", "platform_human_approval"}

HIGH_RISK_OPERATION_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "git_push_or_merge",
        r"\b(git\s+push|gh\s+pr\s+merge|glab\s+mr\s+merge)\b",
        "可能修改远端代码仓库或合并分支。",
    ),
    (
        "destructive_delete",
        r"\b(rm\s+-[^\n;]*[rf][^\n;]*|rmdir\s+/s|del\s+/s)\b",
        "可能批量删除工作区文件。",
    ),
    (
        "force_reset",
        r"\b(git\s+reset\s+--hard|git\s+clean\s+-[^\n;]*[xfd])\b",
        "可能丢弃本地代码或清理未跟踪文件。",
    ),
    (
        "release_or_deploy",
        r"\b(kubectl\s+(apply|delete|rollout|scale)|helm\s+(upgrade|install|uninstall)|"
        r"terraform\s+(apply|destroy)|docker\s+push|npm\s+publish|pnpm\s+publish)\b",
        "可能发布、部署或修改线上基础设施。",
    ),
)

RUNNER_SAFETY_OPERATION_CODES = frozenset(
    operation for operation, _pattern, _reason in HIGH_RISK_OPERATION_PATTERNS
)


def safe_runner_blocked_operations(value: Any) -> list[str]:
    """Return only stable operation codes suitable for durable approval evidence."""
    if not isinstance(value, list):
        return []
    return list(
        dict.fromkeys(
            str(operation) for operation in value if str(operation) in RUNNER_SAFETY_OPERATION_CODES
        )
    )


def _high_risk_findings(instruction: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for operation, pattern, reason in HIGH_RISK_OPERATION_PATTERNS:
        match = re.search(pattern, instruction, flags=re.IGNORECASE)
        if match is None:
            continue
        findings.append(
            {
                "matched_text": match.group(0),
                "operation": operation,
                "reason": reason,
            }
        )
    return findings


def _parse_approval_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _approval_validation(
    *,
    approval: dict[str, Any],
    blocked_operations: list[str],
) -> dict[str, Any]:
    approved_operations = [
        str(item) for item in approval.get("approved_operations") or [] if str(item).strip()
    ]
    approved_operation_set = set(approved_operations)
    missing_fields = [
        field
        for field in (
            "approval_id",
            "approved_at",
            "approved_by",
            "expires_at",
            "mode",
            "policy_version",
        )
        if not approval.get(field)
    ]
    if approval.get("approved") is not True:
        missing_fields.append("approved")
    if not approved_operations:
        missing_fields.append("approved_operations")

    invalid_reasons: list[str] = []
    if (
        approval.get("policy_version")
        and approval.get("policy_version") != RUNNER_SAFETY_POLICY_VERSION
    ):
        invalid_reasons.append("policy_version_mismatch")
    if approval.get("mode") and approval.get("mode") not in APPROVAL_MODES:
        invalid_reasons.append("approval_mode_unsupported")
    approved_at = _parse_approval_datetime(approval.get("approved_at"))
    if approval.get("approved_at") and approved_at is None:
        invalid_reasons.append("approved_at_invalid")
    expires_at = _parse_approval_datetime(approval.get("expires_at"))
    if approval.get("expires_at") and expires_at is None:
        invalid_reasons.append("expires_at_invalid")
    if expires_at is not None and expires_at <= datetime.now(UTC):
        invalid_reasons.append("approval_expired")

    missing_operations = [
        operation
        for operation in blocked_operations
        if "*" not in approved_operation_set and operation not in approved_operation_set
    ]
    approved = not missing_fields and not invalid_reasons and not missing_operations
    return {
        "approved": approved,
        "approved_operations": approved_operations,
        "invalid_reasons": invalid_reasons,
        "missing_fields": sorted(set(missing_fields)),
        "missing_operations": missing_operations,
    }


def _approval_snapshot(
    *,
    existing_approval: dict[str, Any],
    blocked_operations: list[str],
) -> dict[str, Any]:
    validation = _approval_validation(
        approval=existing_approval,
        blocked_operations=blocked_operations,
    )
    return {
        "approved": validation["approved"],
        "approval_id": existing_approval.get("approval_id"),
        "approval_request_id": existing_approval.get("approval_request_id"),
        "approved_at": existing_approval.get("approved_at"),
        "approved_by": existing_approval.get("approved_by"),
        "approved_operations": validation["approved_operations"],
        "expires_at": existing_approval.get("expires_at"),
        "invalid_reasons": validation["invalid_reasons"],
        "missing_fields": validation["missing_fields"],
        "missing_operations": validation["missing_operations"],
        "mode": existing_approval.get("mode") or "platform_human_approval_required",
        "policy_version": existing_approval.get("policy_version"),
    }


def runner_task_safety_snapshot(
    *,
    instruction: str,
    request_config: dict[str, Any] | None,
) -> dict[str, Any]:
    findings = _high_risk_findings(instruction)
    risk_level = "high" if findings else "low"
    approval_required = bool(findings)
    existing_approval = (
        (request_config or {}).get("ai_executor_approval")
        if isinstance((request_config or {}).get("ai_executor_approval"), dict)
        else {}
    )
    blocked_operations = [finding["operation"] for finding in findings]
    approval_snapshot = _approval_snapshot(
        existing_approval=existing_approval,
        blocked_operations=blocked_operations,
    )
    approved = approval_required and approval_snapshot["approved"]
    snapshot = {
        "approval": approval_snapshot,
        "approval_required": approval_required,
        "blocked_operations": blocked_operations,
        "enforcement": "server_preflight_and_runner_guard",
        "execution_allowed": not approval_required or approved,
        "findings": findings,
        "policy_version": RUNNER_SAFETY_POLICY_VERSION,
        "required_action": (
            "先拆分为只读扫描指令，或接入平台人工审批后再允许 Runner 执行。"
            if approval_required and not approved
            else None
        ),
        "risk_level": risk_level,
        "status": "approved" if approved else "blocked" if approval_required else "not_required",
    }
    if approval_required and not approved:
        snapshot["approval_request"] = runner_task_approval_request_snapshot(
            approval=approval_snapshot,
            blocked_operations=blocked_operations,
            findings=findings,
        )
    return snapshot


def runner_task_approval_request_snapshot(
    *,
    approval: dict[str, Any],
    blocked_operations: list[str],
    findings: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "approval_template": {
            "approved": True,
            "approved_operations": blocked_operations,
            "mode": "platform_human_approval",
            "policy_version": RUNNER_SAFETY_POLICY_VERSION,
        },
        "blocked_operations": blocked_operations,
        "current_approval": approval,
        "findings": findings,
        "next_action": "create_platform_human_approval",
        "policy_version": RUNNER_SAFETY_POLICY_VERSION,
        "required_fields": [
            "approval_id",
            "approved",
            "approved_at",
            "approved_by",
            "approved_operations",
            "expires_at",
            "mode",
            "policy_version",
        ],
        "status": "approval_required",
        "title": "AI 执行器高风险操作审批",
    }


def ensure_runner_task_safety(
    *,
    instruction: str,
    request_config: dict[str, Any] | None,
) -> dict[str, Any]:
    snapshot = runner_task_safety_snapshot(
        instruction=instruction,
        request_config=request_config,
    )
    if snapshot["approval_required"] and not snapshot["approval"]["approved"]:
        raise api_error(
            409,
            "AI_EXECUTOR_APPROVAL_REQUIRED",
            "AI executor instruction requires human approval before Runner dispatch",
            {
                "approval_request": snapshot.get("approval_request") or {},
                "blocked_operations": snapshot["blocked_operations"],
                "approval": snapshot["approval"],
                "risk_level": snapshot["risk_level"],
                "safety": snapshot,
            },
        )
    return snapshot
