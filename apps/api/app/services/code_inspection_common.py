from __future__ import annotations

from typing import Any

from app.api.deps import api_error

CODE_INSPECTION_ACTION_TYPES = {
    "create_bug_for_severe_findings",
    "create_task_for_severe_findings",
    "send_notification",
    "write_code_inspection_report",
}
CODE_INSPECTION_SEVERITIES = {"info", "low", "medium", "high", "critical"}
CODE_INSPECTION_RISK_LEVELS = {"low", "medium", "high", "critical"}
CODE_INSPECTION_NOTIFICATION_CHANNELS = {"dingtalk", "email", "webhook"}
CODE_INSPECTION_SUPPRESSION_REASONS = {
    "accepted_risk",
    "baseline",
    "false_positive",
    "ignored",
    "other",
}
CODE_INSPECTION_SORT_FIELDS = {
    "created_at",
    "committer_count",
    "finding_count",
    "id",
    "risk_level",
    "severe_finding_count",
    "status",
    "updated_at",
}
SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
SEVERE_FINDING_THRESHOLD = "high"
DEFAULT_DASHBOARD_TREND_DAYS = 14
DEFAULT_SEVERITY_MAPPING = {
    "blocker": "critical",
    "major": "high",
    "minor": "low",
}
OPEN_BUG_STATUSES = {"assigned", "fixed", "needs_info", "open", "reopened", "triaged"}


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def ensure_enum(value: str | None, allowed_values: set[str], field: str) -> None:
    if value is None or value not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")


def severity_rank(value: str | None) -> int:
    return SEVERITY_ORDER.get(str(value or "").lower(), SEVERITY_ORDER["medium"])


def normalized_severity_mapping(*mappings: Any) -> dict[str, str]:
    normalized = dict(DEFAULT_SEVERITY_MAPPING)
    for mapping in mappings:
        if not isinstance(mapping, dict):
            continue
        for source, target in mapping.items():
            source_key = str(source or "").strip().lower()
            target_value = str(target or "").strip().lower()
            if source_key and target_value in CODE_INSPECTION_SEVERITIES:
                normalized[source_key] = target_value
    return normalized


def normalize_severity(
    value: Any,
    *,
    fallback: str = "medium",
    severity_mapping: dict[str, str] | None = None,
) -> str:
    normalized = str(value or fallback).lower()
    if severity_mapping and normalized in severity_mapping:
        normalized = severity_mapping[normalized]
    return normalized if normalized in CODE_INSPECTION_SEVERITIES else fallback


def normalize_risk_level(
    value: Any,
    findings: list[dict[str, Any]],
    *,
    severity_mapping: dict[str, str] | None = None,
) -> str:
    normalized = str(value or "").lower()
    if severity_mapping and normalized in severity_mapping:
        normalized = severity_mapping[normalized]
    if normalized in CODE_INSPECTION_RISK_LEVELS:
        return normalized
    if not findings:
        return "low"
    highest = max(findings, key=lambda item: severity_rank(item.get("severity")))
    highest_severity = str(highest.get("severity") or "medium")
    return highest_severity if highest_severity in CODE_INSPECTION_RISK_LEVELS else "medium"


def validate_code_inspection_result_actions(actions: Any) -> list[dict[str, Any]]:
    if actions is None:
        return []
    if not isinstance(actions, list):
        raise api_error(400, "VALIDATION_ERROR", "result_actions must be a list")
    normalized: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            raise api_error(400, "VALIDATION_ERROR", "result action must be an object")
        action_type = str(action.get("type") or "")
        ensure_enum(action_type, CODE_INSPECTION_ACTION_TYPES, "result action type")
        if action_type in {"create_bug_for_severe_findings", "create_task_for_severe_findings"}:
            threshold = normalize_severity(action.get("severity_threshold"), fallback="critical")
            normalized.append({**action, "severity_threshold": threshold, "type": action_type})
        elif action_type == "send_notification":
            channels = action.get("channels") if isinstance(action.get("channels"), list) else []
            channels = [str(channel) for channel in channels if str(channel or "").strip()]
            if not channels:
                raise api_error(400, "VALIDATION_ERROR", "send_notification requires channels")
            for channel in channels:
                ensure_enum(channel, CODE_INSPECTION_NOTIFICATION_CHANNELS, "notification channel")
            recipients = (
                action.get("recipients")
                if isinstance(action.get("recipients"), list)
                else []
            )
            normalized.append(
                {
                    **action,
                    "channels": channels,
                    "recipients": [
                        str(recipient)
                        for recipient in recipients
                        if str(recipient or "").strip()
                    ],
                    "type": action_type,
                }
            )
        else:
            normalized.append({**action, "type": action_type})
    return normalized


def default_code_inspection_result_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if actions:
        return actions
    return [{"type": "write_code_inspection_report"}]


def nested_value(raw: dict[str, Any], section: str, key: str) -> Any:
    nested = raw.get(section)
    return nested.get(key) if isinstance(nested, dict) else None


def committer_field(raw: dict[str, Any], field: str) -> str | None:
    value = (
        raw.get(f"committer_{field}")
        or nested_value(raw, "committer", field)
        or raw.get(f"author_{field}")
        or nested_value(raw, "author", field)
    )
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def committer_key(finding: dict[str, Any]) -> str | None:
    value = (
        finding.get("committer_email")
        or finding.get("committer_username")
        or finding.get("committer_name")
    )
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def committer_summary(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for finding in findings:
        key = committer_key(finding)
        if key is None:
            continue
        entry = grouped.setdefault(
            key,
            {
                "bug_count": 0,
                "email": finding.get("committer_email"),
                "finding_count": 0,
                "name": finding.get("committer_name"),
                "severe_finding_count": 0,
                "username": finding.get("committer_username"),
            },
        )
        entry["finding_count"] += 1
        if severity_rank(finding.get("severity")) >= severity_rank(SEVERE_FINDING_THRESHOLD):
            entry["severe_finding_count"] += 1
        if finding.get("created_bug_id"):
            entry["bug_count"] += 1
    return sorted(
        grouped.values(),
        key=lambda item: (
            -int(item["severe_finding_count"]),
            -int(item["finding_count"]),
            str(item.get("email") or item.get("username") or item.get("name") or ""),
        ),
    )


def committer_count(findings: list[dict[str, Any]]) -> int:
    return len({key for finding in findings if (key := committer_key(finding))})


def report_matches_committer(report: dict[str, Any], committer: str | None) -> bool:
    if not committer:
        return True
    needle = committer.lower()
    for item in report.get("committer_summary") or []:
        haystack = " ".join(
            str(item.get(field) or "")
            for field in ("email", "name", "username")
        ).lower()
        if needle in haystack:
            return True
    return False
