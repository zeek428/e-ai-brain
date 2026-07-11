from __future__ import annotations

import ast
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
    tokens = json_path_tokens(path)
    if tokens is None:
        return None
    return _json_path_apply(payload, tokens)


def json_path_tokens(path: str | None) -> list[tuple[str, Any]] | None:
    return _json_path_tokens(path)


def _json_path_tokens(path: str | None) -> list[tuple[str, Any]] | None:
    if path == "$":
        return []
    if not path or not path.startswith("$"):
        return None
    tokens: list[tuple[str, Any]] = []
    index = 1
    while index < len(path):
        char = path[index]
        if char == ".":
            index += 1
            start = index
            while index < len(path) and path[index] not in ".[":
                index += 1
            key = path[start:index]
            if not key:
                return None
            if key == "*":
                tokens.append(("wildcard", None))
            else:
                tokens.append(("key", key))
            continue
        if char == "[":
            end = _json_path_bracket_end(path, index)
            if end is None:
                return None
            token = _json_path_bracket_token(path[index + 1 : end])
            if token is None:
                return None
            tokens.append(token)
            index = end + 1
            continue
        return None
    return tokens


def _json_path_bracket_end(path: str, start: int) -> int | None:
    quote: str | None = None
    escaped = False
    for index in range(start + 1, len(path)):
        char = path[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "]":
            return index
    return None


def _json_path_bracket_token(content: str) -> tuple[str, Any] | None:
    stripped = content.strip()
    if stripped == "*":
        return ("wildcard", None)
    if stripped.isdigit():
        return ("index", int(stripped))
    if len(stripped) >= 2 and stripped[0] in {"'", '"'} and stripped[-1] == stripped[0]:
        try:
            value = ast.literal_eval(stripped)
        except (SyntaxError, ValueError):
            return None
        if isinstance(value, str):
            return ("key", value)
    return None


def _json_path_apply(payload: Any, tokens: list[tuple[str, Any]]) -> Any:
    if not tokens:
        return payload
    kind, value = tokens[0]
    rest = tokens[1:]
    if kind == "key":
        if not isinstance(payload, dict) or value not in payload:
            return None
        return _json_path_apply(payload[value], rest)
    if kind == "index":
        if not isinstance(payload, list) or value >= len(payload):
            return None
        return _json_path_apply(payload[value], rest)
    if kind == "wildcard":
        if isinstance(payload, dict):
            items = payload.values()
        elif isinstance(payload, list):
            items = payload
        else:
            return None
        results: list[Any] = []
        for item in items:
            resolved = _json_path_apply(item, rest)
            if resolved is None:
                continue
            if isinstance(resolved, list):
                results.extend(resolved)
            else:
                results.append(resolved)
        return results
    return None


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
        if not isinstance(path, str) or json_path_tokens(path) is None:
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
        records_imported = records_imported_from_mapping(response_summary, mapping)
        if records_imported == 0 and isinstance(insights, list):
            records_imported = len(insights)
        return {
            "candidate_count": len(insights) if isinstance(insights, list) else 0,
            "records_imported": records_imported,
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

    if write_target == "dingtalk_document":
        document_id = str(mapping.get("document_id") or "").strip() or json_path_value(
            raw_json,
            str(mapping.get("document_id_path") or default_mapping.get("document_id_path")),
        )
        status = json_path_value(
            raw_json,
            str(mapping.get("status_path") or default_mapping.get("status_path")),
        )
        content_template = str(
            mapping.get("content_template")
            or default_mapping.get("content_template")
            or "",
        )
        write_mode = str(mapping.get("write_mode") or default_mapping.get("write_mode") or "")
        records_imported = 1 if raw_json is not None else 0
        candidate_count = 1 if document_id or status or raw_json is not None else 0
        return {
            "candidate_count": candidate_count,
            "document_id": compact_preview_value(document_id),
            "records_imported": records_imported,
            "sample_records": [compact_preview_value(content_template)] if content_template else [],
            "status": compact_preview_value(status),
            "write_mode": write_mode,
            "write_target": write_target,
            "write_target_label": write_target_label,
        }

    if write_target == "requirements":
        requirements = json_path_value(
            raw_json,
            str(mapping.get("requirements_path") or default_mapping.get("requirements_path")),
        )
        sample_records = requirements[:3] if isinstance(requirements, list) else []
        return {
            "candidate_count": len(requirements) if isinstance(requirements, list) else 0,
            "records_imported": len(requirements) if isinstance(requirements, list) else 0,
            "sample_records": [compact_preview_value(record) for record in sample_records],
            "write_target": write_target,
            "write_target_label": write_target_label,
        }

    preview_value = json_path_value(raw_json, mapping.get("records_imported_path"))
    if preview_value is None:
        for path in (
            mapping.get("anomalies_path"),
            mapping.get("insights_path"),
            mapping.get("findings_path"),
            "$.anomalies",
            "$.insights",
            "$.findings",
        ):
            preview_value = json_path_value(raw_json, str(path))
            if preview_value is not None:
                break
    sample_records = preview_value[:3] if isinstance(preview_value, list) else []
    records_imported = records_imported_from_mapping(response_summary, mapping)
    if records_imported == 0 and isinstance(preview_value, list):
        records_imported = len(preview_value)
    return {
        "candidate_count": len(preview_value) if isinstance(preview_value, list) else 0,
        "preview_value": compact_preview_value(preview_value),
        "records_imported": records_imported,
        "sample_records": [compact_preview_value(record) for record in sample_records],
        "write_target": write_target,
        "write_target_label": write_target_label,
    }
