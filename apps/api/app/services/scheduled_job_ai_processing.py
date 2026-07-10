from __future__ import annotations

import json
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import HTTPException

from app.api.deps import api_error
from app.services.knowledge_documents import (
    knowledge_document_chunks,
    knowledge_query_repository,
    knowledge_repository_access_args,
)
from app.services.knowledge_search import KNOWLEDGE_SEARCHABLE_STATUSES
from app.services.model_gateway_config_context import save_model_gateway_records
from app.services.model_gateway_logging import (
    estimate_tokens,
    model_gateway_log,
    openai_usage_tokens,
)
from app.services.model_gateway_runtime import (
    model_gateway_chat_completions_url,
    read_model_gateway_json_response,
)
from app.services.operational_records import record_audit_event
from app.services.plugin_result_mapping import json_path_tokens
from app.services.scheduled_job_store import (
    read_memory_dict,
    sync_ai_skill_store,
    sync_reference_store,
)

SKILL_OUTPUT_MAPPING_PATH_KEYS = (
    "anomalies_path",
    "branch_path",
    "commit_sha_path",
    "findings_path",
    "insights_path",
    "repository_id_path",
    "risk_level_path",
    "summary_path",
)

CODE_INSPECTION_DEFAULT_OUTPUT_SCHEMA = {
    "properties": {
        "findings": {
            "items": {
                "properties": {
                    "category": {"type": "string"},
                    "committer_email": {"type": ["string", "null"]},
                    "committer_name": {"type": ["string", "null"]},
                    "description": {"type": "string"},
                    "file_path": {"type": "string"},
                    "line_number": {"type": "integer"},
                    "recommendation": {"type": "string"},
                    "risk_level": {"type": "string"},
                    "rule_id": {"type": "string"},
                    "severity": {"type": "string"},
                    "title": {"type": "string"},
                },
                "type": "object",
            },
            "type": "array",
        },
        "risk_level": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["findings", "risk_level", "summary"],
    "type": "object",
}

AI_SOURCE_DEFAULT_SAMPLE_ROW_LIMIT = 80
AI_SOURCE_DEFAULT_STRING_LIMIT = 360
AI_SOURCE_DEFAULT_SCALAR_LIST_LIMIT = 40
AI_SOURCE_ROW_PREFERRED_KEYS = (
    "content",
    "summary",
    "title",
    "description",
    "feedback_type",
    "sentiment",
    "source_channel",
    "channel",
    "msg_type",
    "ai_status",
    "role_type",
    "send_time",
    "feedback_time",
    "create_time",
    "pt",
    "product_id",
    "tags",
    "feedback_no",
    "device_name",
    "device_type",
    "os_version",
    "app_version",
    "user_network",
    "category",
    "severity",
    "risk_level",
    "file_path",
    "line_number",
    "rule_id",
    "recommendation",
)
AI_SOURCE_ROW_LOW_VALUE_KEYS = {
    "external_user_id",
    "open_kf_id",
    "user_id",
    "username",
    "media_urls",
    "bluetooth_list",
    "signal_strength",
}


def _bounded_positive_int(value: Any, *, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return min(parsed, maximum)


def _truncate_ai_source_string(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}...<truncated {len(value) - max_chars} chars>"


def _sample_ai_source_items(items: list[Any], limit: int) -> list[tuple[int, Any]]:
    if len(items) <= limit:
        return list(enumerate(items))
    if limit <= 1:
        return [(0, items[0])]
    head_count = max(1, limit // 2)
    tail_count = max(1, limit // 4)
    middle_count = max(0, limit - head_count - tail_count)
    indexes = list(range(head_count))
    if middle_count:
        start = head_count
        end = max(start, len(items) - tail_count)
        span = max(1, end - start)
        for offset in range(middle_count):
            index = start + int((offset + 1) * span / (middle_count + 1))
            indexes.append(min(index, len(items) - 1))
    indexes.extend(range(max(head_count, len(items) - tail_count), len(items)))
    unique_indexes = sorted(set(indexes))[:limit]
    return [(index, items[index]) for index in unique_indexes]


def _compact_ai_source_row(row: dict[str, Any], *, index: int, max_chars: int) -> dict[str, Any]:
    compacted: dict[str, Any] = {"_row_index": index}
    for key in AI_SOURCE_ROW_PREFERRED_KEYS:
        if key in row:
            compacted[key] = _compact_ai_source_value(
                row[key],
                max_chars=max_chars,
                max_scalar_list_items=12,
                max_rows=12,
                path=f"row.{key}",
                stats=None,
            )
    for key, value in row.items():
        if key in compacted or key in AI_SOURCE_ROW_LOW_VALUE_KEYS:
            continue
        if isinstance(value, (dict, list)):
            continue
        if value is None or value == "":
            continue
        compacted[key] = _compact_ai_source_value(
            value,
            max_chars=max_chars,
            max_scalar_list_items=12,
            max_rows=12,
            path=f"row.{key}",
            stats=None,
        )
        if len(compacted) >= 24:
            break
    return compacted


def _compact_ai_source_value(
    value: Any,
    *,
    max_chars: int,
    max_scalar_list_items: int,
    max_rows: int,
    path: str,
    stats: dict[str, Any] | None,
) -> Any:
    if isinstance(value, str):
        truncated = _truncate_ai_source_string(value, max_chars)
        if stats is not None and truncated != value:
            stats["compacted"] = True
            stats["truncated_strings"] = int(stats.get("truncated_strings") or 0) + 1
        return truncated
    if isinstance(value, dict):
        return {
            str(key): _compact_ai_source_value(
                item,
                max_chars=max_chars,
                max_scalar_list_items=max_scalar_list_items,
                max_rows=max_rows,
                path=f"{path}.{key}",
                stats=stats,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        if not value:
            return []
        if all(isinstance(item, dict) for item in value):
            if len(value) <= max_rows:
                return [
                    _compact_ai_source_value(
                        item,
                        max_chars=max_chars,
                        max_scalar_list_items=max_scalar_list_items,
                        max_rows=max_rows,
                        path=f"{path}[{index}]",
                        stats=stats,
                    )
                    for index, item in enumerate(value)
                ]
            sampled = _sample_ai_source_items(value, max_rows)
            sample_rows = [
                _compact_ai_source_row(item, index=index, max_chars=max_chars)
                for index, item in sampled
                if isinstance(item, dict)
            ]
            if stats is not None:
                stats["compacted"] = True
                stats.setdefault("sampled_lists", []).append(
                    {
                        "path": path,
                        "sample_count": len(sample_rows),
                        "total_count": len(value),
                    },
                )
            return {
                "_ai_brain_compacted_list": True,
                "omitted_count": max(0, len(value) - len(sample_rows)),
                "sample_count": len(sample_rows),
                "sample_rows": sample_rows,
                "sample_strategy": "head_middle_tail",
                "total_count": len(value),
            }
        sampled_values = value[:max_scalar_list_items]
        compacted_values = [
            _compact_ai_source_value(
                item,
                max_chars=max_chars,
                max_scalar_list_items=max_scalar_list_items,
                max_rows=max_rows,
                path=f"{path}[]",
                stats=stats,
            )
            for item in sampled_values
        ]
        if len(value) <= max_scalar_list_items:
            return compacted_values
        if stats is not None:
            stats["compacted"] = True
            stats.setdefault("sampled_lists", []).append(
                {
                    "path": path,
                    "sample_count": len(compacted_values),
                    "total_count": len(value),
                },
            )
        return {
            "_ai_brain_compacted_list": True,
            "omitted_count": max(0, len(value) - len(compacted_values)),
            "sample_count": len(compacted_values),
            "sample_values": compacted_values,
            "total_count": len(value),
        }
    return value


def ai_model_source_payload(
    *,
    job: dict[str, Any],
    source_response_json: dict[str, Any],
    source_row_count: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    job_config = job.get("config_json") if isinstance(job.get("config_json"), dict) else {}
    ai_config = (
        job_config.get("ai_processing") if isinstance(job_config.get("ai_processing"), dict) else {}
    )
    max_rows = _bounded_positive_int(
        ai_config.get("max_source_sample_rows"),
        default=AI_SOURCE_DEFAULT_SAMPLE_ROW_LIMIT,
        maximum=200,
    )
    max_chars = _bounded_positive_int(
        ai_config.get("max_source_field_chars"),
        default=AI_SOURCE_DEFAULT_STRING_LIMIT,
        maximum=1200,
    )
    stats: dict[str, Any] = {
        "compacted": False,
        "max_source_field_chars": max_chars,
        "max_source_sample_rows": max_rows,
        "source_row_count": source_row_count,
    }
    compacted = _compact_ai_source_value(
        source_response_json,
        max_chars=max_chars,
        max_scalar_list_items=AI_SOURCE_DEFAULT_SCALAR_LIST_LIMIT,
        max_rows=max_rows,
        path="$",
        stats=stats,
    )
    if not isinstance(compacted, dict):
        compacted = {"value": compacted}
    if stats["compacted"]:
        compacted = {
            "_ai_brain_compacted": True,
            "compaction": stats,
            "payload": compacted,
        }
    return compacted, stats


def normalized_knowledge_document_ids(value: Any) -> list[str]:
    if value is None:
        return []
    ids = value if isinstance(value, list) else []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in ids:
        if not isinstance(item, str):
            raise api_error(400, "VALIDATION_ERROR", "knowledge_document_ids must be strings")
        document_id = item.strip()
        if not document_id:
            continue
        if document_id in seen:
            continue
        seen.add(document_id)
        normalized.append(document_id)
    return normalized


def readable_knowledge_documents_by_id(
    current_store: Any,
    *,
    document_ids: list[str],
    user: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if not document_ids:
        return {}
    requested = set(document_ids)
    repository = knowledge_query_repository(current_store)
    if repository is not None:
        documents = repository.list_knowledge_documents(
            **knowledge_repository_access_args(user),
        )
    else:
        from app.services.knowledge_management import document_is_readable

        documents = [
            document
            for document in read_memory_dict(current_store, "knowledge_documents").values()
            if document_is_readable(current_store, user, document)
        ]
    return {
        document["id"]: dict(document) for document in documents if document.get("id") in requested
    }


def validate_knowledge_document_ids(
    current_store: Any,
    document_ids: list[str],
    *,
    user: dict[str, Any],
) -> list[str]:
    normalized = normalized_knowledge_document_ids(document_ids)
    if not normalized:
        return []
    documents_by_id = readable_knowledge_documents_by_id(
        current_store,
        document_ids=normalized,
        user=user,
    )
    missing = [document_id for document_id in normalized if document_id not in documents_by_id]
    if missing:
        raise api_error(
            404,
            "KNOWLEDGE_DOCUMENT_NOT_FOUND",
            f"Knowledge document not found or not readable: {', '.join(missing)}",
        )
    unsearchable = [
        document_id
        for document_id in normalized
        if documents_by_id[document_id].get("index_status") not in KNOWLEDGE_SEARCHABLE_STATUSES
    ]
    if unsearchable:
        raise api_error(
            400,
            "KNOWLEDGE_DOCUMENT_NOT_SEARCHABLE",
            f"Knowledge document is not searchable: {', '.join(unsearchable)}",
        )
    return normalized


def skill_codes_for_job(current_store: Any, job: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    for skill_id in job.get("skill_ids", []):
        skill = read_memory_dict(current_store, "ai_skills").get(skill_id)
        if skill is not None and skill.get("code"):
            codes.append(str(skill["code"]))
    return codes


def merged_skill_output_schema(current_store: Any, job: dict[str, Any]) -> dict[str, Any]:
    sync_ai_skill_store(current_store)
    required: list[str] = []
    properties: dict[str, Any] = {}
    if job.get("job_type") == "code_repository_inspection":
        properties.update(CODE_INSPECTION_DEFAULT_OUTPUT_SCHEMA["properties"])
        required.extend(CODE_INSPECTION_DEFAULT_OUTPUT_SCHEMA["required"])
    for skill_id in job.get("skill_ids") or []:
        skill = read_memory_dict(current_store, "ai_skills").get(skill_id)
        schema = skill.get("output_schema") if isinstance(skill, dict) else None
        if not isinstance(schema, dict) or not schema:
            continue
        schema_properties = schema.get("properties")
        if isinstance(schema_properties, dict):
            properties.update(schema_properties)
        schema_required = schema.get("required")
        if isinstance(schema_required, list):
            for item in schema_required:
                if isinstance(item, str) and item not in required:
                    required.append(item)
    if not properties and not required:
        return {}
    return {
        "properties": properties,
        "required": required,
        "type": "object",
    }


def skill_output_schema_sample(
    schema: dict[str, Any],
    *,
    source_row_count: int = 0,
) -> dict[str, Any]:
    if not schema:
        return {}
    array_size = max(1, min(int(source_row_count or 1), 3))
    sample = _schema_sample_value(
        schema,
        array_size=array_size,
        property_name="root",
        source_row_count=source_row_count,
    )
    return sample if isinstance(sample, dict) else {"value": sample}


def _schema_sample_value(
    schema: Any,
    *,
    array_size: int,
    property_name: str,
    source_row_count: int,
) -> Any:
    if not isinstance(schema, dict):
        return _sample_string(property_name)
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = next((item for item in schema_type if item != "null"), schema_type[0])
    if schema_type == "array" or "items" in schema:
        items_schema = schema.get("items") if isinstance(schema.get("items"), dict) else None
        if items_schema is None:
            items_schema = _default_array_item_schema(property_name)
        return [
            _schema_sample_value(
                items_schema,
                array_size=array_size,
                property_name=property_name.rstrip("s") or property_name,
                source_row_count=source_row_count,
            )
            for _index in range(array_size)
        ]
    properties = schema.get("properties")
    if schema_type == "object" or isinstance(properties, dict):
        if not isinstance(properties, dict):
            return {}
        return {
            key: _schema_sample_value(
                value if isinstance(value, dict) else {},
                array_size=array_size,
                property_name=key,
                source_row_count=source_row_count,
            )
            for key, value in properties.items()
        }
    if schema_type in {"integer", "number"}:
        if property_name in {"count", "row_count", "records_imported"}:
            return source_row_count
        return 1
    if schema_type == "boolean":
        return True
    if schema_type == "null":
        return None
    return _sample_string(property_name)


def _default_array_item_schema(property_name: str) -> dict[str, Any]:
    lower_name = property_name.lower()
    if lower_name in {"insights", "user_feedback_insights"}:
        return {
            "properties": {
                "confidence": {"type": "number"},
                "feedback_type": {"type": "string"},
                "sentiment": {"type": "string"},
                "source_channel": {"type": "string"},
                "summary": {"type": "string"},
                "title": {"type": "string"},
            },
            "type": "object",
        }
    if lower_name in {"findings", "issues"}:
        return {
            "properties": {
                "file_path": {"type": "string"},
                "line": {"type": "integer"},
                "risk_level": {"type": "string"},
                "rule_id": {"type": "string"},
                "summary": {"type": "string"},
            },
            "type": "object",
        }
    if lower_name in {"anomalies", "alerts"}:
        return {
            "properties": {
                "affected_service": {"type": "string"},
                "evidence": {"type": "string"},
                "recommendation": {"type": "string"},
                "severity": {"type": "string"},
                "summary": {"type": "string"},
            },
            "type": "object",
        }
    if lower_name in {"recipients", "emails", "to", "cc"}:
        return {"type": "string", "format": "email"}
    if lower_name in {"rows", "items", "records"}:
        return {
            "properties": {
                "id": {"type": "string"},
                "summary": {"type": "string"},
            },
            "type": "object",
        }
    return {}


def _sample_string(property_name: str) -> str:
    lower_name = property_name.lower()
    if lower_name in {"email", "recipient", "recipients", "to", "cc"}:
        return "dry-run@example.com"
    if lower_name in {"file_path", "path"}:
        return "src/example.py"
    if lower_name in {"rule_id"}:
        return "AI-BRAIN-DRY-RUN"
    if lower_name in {"summary", "description"}:
        return "AI Brain dry-run sample summary"
    if lower_name in {"id"}:
        return "dry-run-id"
    if lower_name in {"sentiment"}:
        return "neutral"
    if lower_name in {"feedback_type", "type"}:
        return "improvement"
    if lower_name in {"source_channel", "channel"}:
        return "dry_run"
    if lower_name in {"risk_level", "severity"}:
        return "medium"
    if lower_name in {"affected_service", "service"}:
        return "ai-brain-api"
    if lower_name in {"evidence"}:
        return "dry-run evidence"
    if lower_name in {"recommendation"}:
        return "Check recent deployment and error logs"
    if lower_name in {"branch"}:
        return "main"
    if lower_name in {"commit_sha", "sha"}:
        return "0000000"
    if lower_name in {"repository_id", "repo_id"}:
        return "repository_sample"
    if lower_name in {"status", "delivery_status"}:
        return "succeeded"
    if lower_name in {"message_id", "delivery_id"}:
        return "dry-run-message"
    if lower_name in {"subject", "title"}:
        return "AI Brain dry-run sample"
    if lower_name in {"tags"}:
        return "dry-run"
    return f"{property_name}_sample"


def schema_supports_json_path(schema: dict[str, Any], path: str | None) -> bool:
    if not schema or path in {None, "$"}:
        return True
    if not isinstance(path, str) or not path.startswith("$"):
        return True
    tokens = json_path_tokens(path)
    if tokens is None:
        return False
    return _schema_supports_json_path_tokens(schema, tokens)


def _array_item_schema(schema: Any) -> dict[str, Any] | None:
    if not isinstance(schema, dict):
        return None
    if schema.get("type") == "array" or "items" in schema:
        items = schema.get("items")
        if isinstance(items, dict):
            return items
    return None


def _object_property_schema(schema: Any, key: str) -> dict[str, Any] | None:
    if not isinstance(schema, dict):
        return None
    # Preserve compatibility with older mappings that used $.items.id for arrays.
    array_item = _array_item_schema(schema)
    if array_item is not None:
        schema = array_item
    properties = schema.get("properties") if isinstance(schema, dict) else None
    if isinstance(properties, dict) and key in properties:
        property_schema = properties[key]
        return property_schema if isinstance(property_schema, dict) else {}
    additional_properties = schema.get("additionalProperties") if isinstance(schema, dict) else None
    if isinstance(additional_properties, dict):
        return additional_properties
    return None


def _wildcard_schema_options(schema: Any) -> list[dict[str, Any]]:
    array_item = _array_item_schema(schema)
    if array_item is not None:
        return [array_item]
    if not isinstance(schema, dict):
        return []
    additional_properties = schema.get("additionalProperties")
    if isinstance(additional_properties, dict):
        return [additional_properties]
    properties = schema.get("properties")
    if isinstance(properties, dict):
        return [value if isinstance(value, dict) else {} for value in properties.values()]
    return []


def _schema_supports_json_path_tokens(
    schema: dict[str, Any],
    tokens: list[tuple[str, Any]],
) -> bool:
    if not tokens:
        return True
    kind, value = tokens[0]
    rest = tokens[1:]
    if kind == "key":
        next_schema = _object_property_schema(schema, str(value))
        return next_schema is not None and _schema_supports_json_path_tokens(next_schema, rest)
    if kind == "index":
        item_schema = _array_item_schema(schema)
        return item_schema is not None and _schema_supports_json_path_tokens(item_schema, rest)
    if kind == "wildcard":
        options = _wildcard_schema_options(schema)
        if not options:
            return False
        return any(_schema_supports_json_path_tokens(option, rest) for option in options)
    return False


def skill_output_mapping_contract(
    current_store: Any,
    *,
    job: dict[str, Any],
    output_mapping: dict[str, Any],
) -> dict[str, Any]:
    schema = merged_skill_output_schema(current_store, job)
    if not schema:
        return {
            "checked_paths": [],
            "invalid_fields": [],
            "output_schema": {},
            "status": "not_required",
        }
    checks: list[dict[str, Any]] = []
    for key in SKILL_OUTPUT_MAPPING_PATH_KEYS:
        if key not in output_mapping:
            continue
        path = output_mapping.get(key)
        supported = schema_supports_json_path(schema, path)
        checks.append(
            {
                "field": key,
                "path": path,
                "supported": supported,
            },
        )
    invalid_fields = [str(check["field"]) for check in checks if not check["supported"]]
    return {
        "checked_paths": checks,
        "invalid_fields": invalid_fields,
        "output_schema": schema,
        "status": "failed" if invalid_fields else "succeeded" if checks else "not_required",
    }


def validate_skill_output_mapping_contract(
    current_store: Any,
    *,
    job: dict[str, Any],
    output_mapping: dict[str, Any],
) -> dict[str, Any]:
    contract = skill_output_mapping_contract(
        current_store,
        job=job,
        output_mapping=output_mapping,
    )
    schema = contract["output_schema"]
    if not schema:
        return {}
    invalid = contract["invalid_fields"]
    if invalid:
        raise api_error(
            400,
            "SKILL_OUTPUT_MAPPING_INVALID",
            f"Skill output schema does not contain mapped field(s): {', '.join(invalid)}",
        )
    return schema


def validate_skill_output_json_contract(
    output_json: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    if not schema:
        return
    errors = _skill_output_schema_errors(output_json, schema, "$")
    if errors:
        raise api_error(
            400,
            "SKILL_OUTPUT_SCHEMA_INVALID",
            f"AI output does not match Skill output schema: {'; '.join(errors[:5])}",
        )


def _skill_output_schema_errors(
    value: Any,
    schema: Any,
    path: str,
) -> list[str]:
    if not isinstance(schema, dict) or not schema:
        return []
    schema_type = schema.get("type")
    allowed_types = (
        [item for item in schema_type if isinstance(item, str)]
        if isinstance(schema_type, list)
        else [schema_type]
        if isinstance(schema_type, str)
        else []
    )
    if value is None and "null" in allowed_types:
        return []
    non_null_types = [item for item in allowed_types if item != "null"]
    if not non_null_types:
        if "properties" in schema:
            non_null_types = ["object"]
        elif "items" in schema:
            non_null_types = ["array"]
    errors: list[str] = []
    matched_types = [
        item for item in non_null_types if _json_value_matches_schema_type(value, item)
    ]
    if non_null_types and not matched_types:
        expected = " or ".join(non_null_types)
        return [f"{path} expected {expected}, got {_json_value_type_name(value)}"]
    effective_type = (
        matched_types[0] if matched_types else non_null_types[0] if non_null_types else None
    )
    if "enum" in schema:
        enum = schema.get("enum")
        if isinstance(enum, list) and value not in enum:
            errors.append(f"{path} must be one of {enum}")
    if effective_type == "object" or isinstance(schema.get("properties"), dict):
        if not isinstance(value, dict):
            return errors
        required = schema.get("required")
        if isinstance(required, list):
            for item in required:
                if isinstance(item, str) and item not in value:
                    errors.append(f"{path}.{item} is required")
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for key, property_schema in properties.items():
                if key in value:
                    errors.extend(
                        _skill_output_schema_errors(
                            value[key],
                            property_schema,
                            f"{path}.{key}",
                        ),
                    )
        return errors
    if effective_type == "array" or "items" in schema:
        if not isinstance(value, list):
            return errors
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for index, item in enumerate(value):
                errors.extend(
                    _skill_output_schema_errors(item, items_schema, f"{path}[{index}]"),
                )
        return errors
    return errors


def _json_value_matches_schema_type(value: Any, schema_type: str) -> bool:
    if schema_type == "object":
        return isinstance(value, dict)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "null":
        return value is None
    return True


def _json_value_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return type(value).__name__


def selected_model_gateway_config(current_store: Any, job: dict[str, Any]) -> dict[str, Any]:
    sync_reference_store(current_store)
    config_id = job.get("model_gateway_config_id")
    config = (
        read_memory_dict(current_store, "model_gateway_configs").get(config_id)
        if config_id
        else None
    )
    if config is None:
        raise api_error(400, "MODEL_GATEWAY_CONFIG_REQUIRED", "AI model config is required")
    if config.get("status") != "active":
        raise api_error(400, "MODEL_GATEWAY_CONFIG_INACTIVE", "Model gateway config is inactive")
    if config.get("provider") != "openai_compatible":
        raise api_error(
            400,
            "MODEL_GATEWAY_PROVIDER_UNSUPPORTED",
            "Model gateway provider is not supported",
        )
    if not config.get("api_key"):
        raise api_error(
            400,
            "MODEL_GATEWAY_CONFIG_INVALID",
            "Model gateway config is missing api_key",
        )
    return config


def scheduled_job_knowledge_references(
    current_store: Any,
    *,
    job: dict[str, Any],
    user: dict[str, Any],
    max_content_chars: int = 1200,
    max_chunks: int = 8,
) -> list[dict[str, Any]]:
    document_ids = normalized_knowledge_document_ids(job.get("knowledge_document_ids") or [])
    if not document_ids:
        return []
    document_order = {document_id: index for index, document_id in enumerate(document_ids)}
    repository = knowledge_query_repository(current_store)
    candidates: list[dict[str, Any]]
    if repository is not None:
        candidates = repository.search_knowledge_chunks(
            **knowledge_repository_access_args(user),
            query=None,
        )
    else:
        documents_by_id = readable_knowledge_documents_by_id(
            current_store,
            document_ids=document_ids,
            user=user,
        )
        candidates = []
        for document_id in document_ids:
            document = documents_by_id.get(document_id)
            if document is None:
                continue
            if document.get("index_status") not in KNOWLEDGE_SEARCHABLE_STATUSES:
                continue
            for chunk in knowledge_document_chunks(current_store, document_id):
                candidates.append({"chunk": chunk, "document": document})

    references: list[dict[str, Any]] = []
    for candidate in candidates:
        document = candidate.get("document") or {}
        chunk = candidate.get("chunk") or {}
        document_id = document.get("id")
        if document_id not in document_order:
            continue
        if chunk.get("metadata", {}).get("chunk_role") == "parent":
            continue
        content = str(chunk.get("content") or "").strip()
        if not content:
            continue
        references.append(
            {
                "chunk_id": chunk.get("id"),
                "chunk_index": chunk.get("chunk_index"),
                "content": content[:max_content_chars],
                "document_id": document_id,
                "title": document.get("title"),
            }
        )
    references.sort(
        key=lambda item: (
            document_order.get(str(item.get("document_id")), 999999),
            int(item.get("chunk_index") or 0),
            str(item.get("chunk_id") or ""),
        )
    )
    return references[:max_chunks]


def model_json_content(response_payload: dict[str, Any]) -> dict[str, Any]:
    content = response_payload["choices"][0]["message"]["content"]
    if isinstance(content, dict):
        return content
    text = str(content).strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Model output must be a JSON object")
    return parsed


def model_gateway_failure_detail(exc: Exception) -> str:
    detail = str(exc).strip() or exc.__class__.__name__
    return _truncate_ai_source_string(f"{exc.__class__.__name__}: {detail}", 500)


def scheduled_job_ai_messages(
    current_store: Any,
    *,
    job: dict[str, Any],
    output_mapping: dict[str, Any],
    source_response_json: dict[str, Any],
    source_row_count: int,
    knowledge_references: list[dict[str, Any]] | None = None,
    model_source_response_json: dict[str, Any] | None = None,
    source_compaction: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    agent = (
        read_memory_dict(current_store, "ai_agents").get(job.get("agent_id"))
        if job.get("agent_id")
        else None
    )
    skill_prompts = []
    for skill_id in job.get("skill_ids", []):
        skill = read_memory_dict(current_store, "ai_skills").get(skill_id)
        if skill is not None:
            prompt = skill.get("prompt_template") or skill.get("description") or skill.get("name")
            if prompt:
                skill_prompts.append(
                    {
                        "code": skill.get("code"),
                        "prompt": prompt,
                    },
                )
    if job.get("job_type") == "code_repository_inspection":
        instructions = [
            "分析 data_connection_response 中的仓库扫描数据，提取质量、安全和规范问题。",
            "必须只返回 JSON 对象，不要返回 Markdown。",
            (
                "返回 JSON 必须包含 repository_id、branch、commit_sha、risk_level、"
                "summary 和 findings 数组。"
            ),
            (
                "findings 中每个问题至少包含 category、severity、title、description、"
                "file_path、line_number、rule_id 和 recommendation；如果源数据有提交人，"
                "保留 committer_name、committer_email 或 committer_username。"
            ),
            "如果源数据已有扫描 finding，也要校验、归一化严重级别并输出为结果动作可消费的结构。",
        ]
        output_contract = {
            "branch_path": str(output_mapping.get("branch_path") or "$.branch"),
            "commit_sha_path": str(output_mapping.get("commit_sha_path") or "$.commit_sha"),
            "findings_path": str(output_mapping.get("findings_path") or "$.findings"),
            "repository_id_path": str(
                output_mapping.get("repository_id_path") or "$.repository_id",
            ),
            "risk_level_path": str(output_mapping.get("risk_level_path") or "$.risk_level"),
            "summary_path": str(output_mapping.get("summary_path") or "$.summary"),
            "write_target": output_mapping.get("write_target") or "code_inspection_reports",
        }
    elif job.get("job_type") == "online_log_ai_analysis":
        instructions = [
            (
                "分析 data_connection_response 中的线上日志、错误率、"
                "延迟或告警数据，识别异常和处置建议。"
            ),
            "必须只返回 JSON 对象，不要返回 Markdown。",
            "返回 JSON 必须包含 summary、risk_level 和 anomalies 数组。",
            (
                "anomalies 中每个异常至少包含 severity、summary、affected_service、"
                "evidence 和 recommendation。"
            ),
            "如果没有异常，返回空 anomalies 数组，并在 summary 中说明检查窗口和结论。",
        ]
        output_contract = {
            "anomalies_path": str(output_mapping.get("anomalies_path") or "$.anomalies"),
            "records_imported_path": str(
                output_mapping.get("records_imported_path") or "$.row_count",
            ),
            "risk_level_path": str(output_mapping.get("risk_level_path") or "$.risk_level"),
            "summary_path": str(output_mapping.get("summary_path") or "$.summary"),
            "write_target": output_mapping.get("write_target") or "scheduled_job_result",
        }
    else:
        instructions = [
            "分析 data_connection_response 中的数据，提取有价值的信息。",
            "必须只返回 JSON 对象，不要返回 Markdown。",
            (
                "返回 JSON 必须包含 insights 数组；每个 insight 至少包含 "
                "content、feedback_type、sentiment、source_channel 和 tags。"
            ),
            "如果源数据已有可用洞察，也要校验、清洗并输出为结果动作可消费的结构。",
        ]
        output_contract = {
            "insights_path": str(output_mapping.get("insights_path") or "$.insights"),
            "records_imported_path": str(
                output_mapping.get("records_imported_path") or "$.row_count",
            ),
            "write_target": output_mapping.get("write_target") or "user_feedback_insights",
        }
    system_prompt = (agent or {}).get(
        "system_prompt"
    ) or "你是企业 AI 大脑的数据分析助手，负责把数据连接返回的原始数据整理为结果动作需要的 JSON。"
    job_config = job.get("config_json") or {}
    if model_source_response_json is None or source_compaction is None:
        model_source_response_json, source_compaction = ai_model_source_payload(
            job=job,
            source_response_json=source_response_json,
            source_row_count=source_row_count,
        )
    user_payload = {
        "instructions": instructions,
        "job": {
            "configured_branch": job_config.get("branch"),
            "configured_repository_id": job_config.get("repository_id"),
            "id": job.get("id"),
            "job_type": job.get("job_type"),
            "product_id": job.get("product_id"),
            "source_system": job.get("source_system"),
            "timezone": job.get("timezone"),
        },
        "output_contract": output_contract,
        "skill_prompts": skill_prompts,
        "source_row_count": source_row_count,
        "data_connection_response": model_source_response_json,
    }
    if source_compaction.get("compacted"):
        user_payload["data_connection_response_compaction"] = source_compaction
    if knowledge_references:
        user_payload["knowledge_references"] = knowledge_references
    return [
        {"role": "system", "content": str(system_prompt)},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
    ]


def run_scheduled_job_ai_processing(
    current_store: Any,
    *,
    job: dict[str, Any],
    output_mapping: dict[str, Any],
    source_response_json: dict[str, Any],
    source_row_count: int,
    user: dict[str, Any],
) -> dict[str, Any]:
    config = selected_model_gateway_config(current_store, job)
    output_schema = validate_skill_output_mapping_contract(
        current_store,
        job=job,
        output_mapping=output_mapping,
    )
    knowledge_references = scheduled_job_knowledge_references(
        current_store,
        job=job,
        user=user,
    )
    model_source_response_json, source_compaction = ai_model_source_payload(
        job=job,
        source_response_json=source_response_json,
        source_row_count=source_row_count,
    )
    messages = scheduled_job_ai_messages(
        current_store,
        job=job,
        knowledge_references=knowledge_references,
        model_source_response_json=model_source_response_json,
        output_mapping=output_mapping,
        source_compaction=source_compaction,
        source_response_json=source_response_json,
        source_row_count=source_row_count,
    )
    body = {
        "messages": messages,
        "model": config["default_chat_model"],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    request = UrlRequest(
        model_gateway_chat_completions_url(config["base_url"]),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = perf_counter()
    try:
        response_payload = read_model_gateway_json_response(
            request,
            timeout_seconds=int(config.get("timeout_seconds") or 60),
            urlopen_func=urlopen,
        )
        output_json = model_json_content(response_payload)
        latency_ms = int((perf_counter() - started) * 1000)
        model_log = model_gateway_log(
            current_store,
            provider=config["provider"],
            model=config["default_chat_model"],
            config_id=config["id"],
            tokens=openai_usage_tokens(
                response_payload.get("usage"),
                messages=messages,
                output=output_json,
            ),
            latency_ms=latency_ms,
            status="succeeded",
            purpose="scheduled_job_ai_processing",
        )
    except (
        AttributeError,
        HTTPError,
        URLError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        failure_detail = model_gateway_failure_detail(exc)
        model_log = model_gateway_log(
            current_store,
            provider=str(config.get("provider") or "openai_compatible"),
            model=str(config.get("default_chat_model") or ""),
            config_id=config.get("id"),
            tokens={
                "completion": 0,
                "prompt": estimate_tokens(messages),
                "total": estimate_tokens(messages),
            },
            latency_ms=latency_ms,
            status="failed",
            purpose="scheduled_job_ai_processing",
            error=failure_detail,
        )
        audit_event = record_audit_event(
            current_store,
            event_type="model_gateway.called",
            actor_id=user["id"],
            subject_type="model_gateway_log",
            subject_id=model_log["id"],
            payload={
                "model": model_log["model"],
                "model_log_id": model_log["id"],
                "provider": model_log["provider"],
                "purpose": model_log["purpose"],
                "scheduled_job_id": job["id"],
                "status": model_log["status"],
            },
        )
        save_model_gateway_records(current_store, audit_event=audit_event)
        raise api_error(
            502,
            "MODEL_GATEWAY_CALL_FAILED",
            "Scheduled job AI processing failed",
            {
                "failure_detail": failure_detail,
                "latency_ms": latency_ms,
                "model": model_log["model"],
                "model_gateway_config_id": config.get("id"),
                "model_log_id": model_log["id"],
                "provider": model_log["provider"],
                "source_compaction": source_compaction,
            },
        ) from exc

    audit_event = record_audit_event(
        current_store,
        event_type="model_gateway.called",
        actor_id=user["id"],
        subject_type="model_gateway_log",
        subject_id=model_log["id"],
        payload={
            "model": model_log["model"],
            "model_log_id": model_log["id"],
            "provider": model_log["provider"],
            "purpose": model_log["purpose"],
            "scheduled_job_id": job["id"],
            "status": model_log["status"],
        },
    )
    save_model_gateway_records(current_store, audit_event=audit_event)
    try:
        validate_skill_output_json_contract(output_json, output_schema)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        if detail.get("code") == "SKILL_OUTPUT_SCHEMA_INVALID":
            raise HTTPException(
                status_code=exc.status_code,
                detail={
                    **detail,
                    "latency_ms": latency_ms,
                    "model": model_log["model"],
                    "model_gateway_called": True,
                    "model_gateway_config_id": config["id"],
                    "model_log_id": model_log["id"],
                    "provider": model_log["provider"],
                },
            ) from exc
        raise
    return {
        "knowledge_references": knowledge_references,
        "model_gateway_config_id": config["id"],
        "model_log_id": model_log["id"],
        "model": config["default_chat_model"],
        "output_json": output_json,
        "provider": config["provider"],
        "source_compaction": source_compaction,
        "status": "succeeded",
        "tokens": model_log["tokens"],
    }
