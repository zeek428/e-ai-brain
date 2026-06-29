from __future__ import annotations

import json
from typing import Any

from app.services.result_write_targets import (
    result_write_target_default_mapping,
    result_write_target_label,
)


def compact_preview_value(value: Any) -> Any:
    if isinstance(value, str):
        return value if len(value) <= 200 else f"{value[:200]}..."
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    try:
        encoded = json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)[:200]
    return value if len(encoded) <= 400 else f"{encoded[:400]}..."


def json_path_value(payload: Any, path: str | None) -> Any:
    if path == "$":
        return payload
    if not path or not path.startswith("$."):
        return None
    current = payload
    for part in path[2:].split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def records_imported_from_mapping(response_summary: dict[str, Any], mapping: dict[str, Any]) -> int:
    value = json_path_value(response_summary.get("json"), mapping.get("records_imported_path"))
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, list):
        return len(value)
    return 0


def result_mapping_hits(
    response_summary: dict[str, Any],
    mapping: dict[str, Any],
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for key, path in mapping.items():
        if not isinstance(path, str) or not (path == "$" or path.startswith("$.")):
            continue
        value = json_path_value(response_summary.get("json"), path)
        hits.append(
            {
                "key": key,
                "matched": value is not None,
                "path": path,
                "value_preview": compact_preview_value(value),
            },
        )
    return hits


def result_write_preview(
    response_summary: dict[str, Any],
    mapping: dict[str, Any],
) -> dict[str, Any]:
    write_target = str(mapping.get("write_target") or "scheduled_job_result")
    default_mapping = result_write_target_default_mapping(write_target)
    raw_json = response_summary.get("json")
    write_target_label = result_write_target_label(write_target)

    if write_target == "code_inspection_reports":
        findings = json_path_value(
            raw_json,
            str(mapping.get("findings_path") or default_mapping.get("findings_path")),
        )
        sample_records = findings[:3] if isinstance(findings, list) else []
        report_preview = {
            "branch": json_path_value(
                raw_json,
                str(mapping.get("branch_path") or default_mapping.get("branch_path")),
            ),
            "commit_sha": json_path_value(
                raw_json,
                str(mapping.get("commit_sha_path") or default_mapping.get("commit_sha_path")),
            ),
            "repository_id": json_path_value(
                raw_json,
                str(
                    mapping.get("repository_id_path")
                    or default_mapping.get("repository_id_path"),
                ),
            ),
            "risk_level": json_path_value(
                raw_json,
                str(mapping.get("risk_level_path") or default_mapping.get("risk_level_path")),
            ),
            "summary": json_path_value(
                raw_json,
                str(mapping.get("summary_path") or default_mapping.get("summary_path")),
            ),
        }
        return {
            "candidate_count": len(findings) if isinstance(findings, list) else 0,
            "records_imported": len(findings) if isinstance(findings, list) else 0,
            "report_preview": {
                key: compact_preview_value(value)
                for key, value in report_preview.items()
                if value is not None
            },
            "sample_records": [compact_preview_value(record) for record in sample_records],
            "write_target": write_target,
            "write_target_label": write_target_label,
        }

    if write_target == "user_feedback_insights":
        insights = json_path_value(
            raw_json,
            str(mapping.get("insights_path") or default_mapping.get("insights_path")),
        )
        rows = json_path_value(
            raw_json,
            str(mapping.get("rows_path") or default_mapping.get("rows_path")),
        )
        sample_records = insights[:3] if isinstance(insights, list) else []
        return {
            "candidate_count": len(insights) if isinstance(insights, list) else 0,
            "records_imported": records_imported_from_mapping(response_summary, mapping),
            "sample_records": [compact_preview_value(record) for record in sample_records],
            "source_row_count": len(rows) if isinstance(rows, list) else None,
            "write_target": write_target,
            "write_target_label": write_target_label,
        }

    if write_target == "email_notifications":
        recipients = json_path_value(
            raw_json,
            str(mapping.get("recipients_path") or default_mapping.get("recipients_path")),
        )
        sample_records = recipients[:3] if isinstance(recipients, list) else []
        if not sample_records and recipients is not None:
            sample_records = [recipients]
        delivery_id = json_path_value(
            raw_json,
            str(mapping.get("delivery_id_path") or default_mapping.get("delivery_id_path")),
        )
        delivery_status = json_path_value(
            raw_json,
            str(
                mapping.get("delivery_status_path")
                or default_mapping.get("delivery_status_path"),
            ),
        )
        subject = json_path_value(
            raw_json,
            str(mapping.get("subject_path") or default_mapping.get("subject_path")),
        )
        records_imported = records_imported_from_mapping(response_summary, mapping)
        if records_imported == 0 and (delivery_id is not None or delivery_status is not None):
            records_imported = 1
        candidate_count = len(recipients) if isinstance(recipients, list) else 0
        if candidate_count == 0 and recipients:
            candidate_count = 1
        return {
            "candidate_count": candidate_count,
            "delivery_id": compact_preview_value(delivery_id),
            "delivery_status": compact_preview_value(delivery_status),
            "records_imported": records_imported,
            "sample_records": [compact_preview_value(record) for record in sample_records],
            "subject": compact_preview_value(subject),
            "write_target": write_target,
            "write_target_label": write_target_label,
        }

    preview_value = json_path_value(raw_json, mapping.get("records_imported_path"))
    sample_records = preview_value[:3] if isinstance(preview_value, list) else []
    return {
        "candidate_count": len(preview_value) if isinstance(preview_value, list) else 0,
        "preview_value": compact_preview_value(preview_value),
        "records_imported": records_imported_from_mapping(response_summary, mapping),
        "sample_records": [compact_preview_value(record) for record in sample_records],
        "write_target": write_target,
        "write_target_label": write_target_label,
    }
