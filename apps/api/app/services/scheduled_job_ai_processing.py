from __future__ import annotations

import json
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

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
from app.services.model_gateway_runtime import model_gateway_chat_completions_url
from app.services.operational_records import record_audit_event
from app.services.scheduled_job_store import (
    read_memory_dict,
    sync_ai_skill_store,
    sync_reference_store,
)


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
        document["id"]: dict(document)
        for document in documents
        if document.get("id") in requested
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


def schema_supports_json_path(schema: dict[str, Any], path: str | None) -> bool:
    if not schema or path in {None, "$"}:
        return True
    if not isinstance(path, str) or not path.startswith("$."):
        return True
    current_schema: Any = schema
    for part in path[2:].split("."):
        if not isinstance(current_schema, dict):
            return False
        properties = current_schema.get("properties")
        if not isinstance(properties, dict) or part not in properties:
            return False
        current_schema = properties[part]
        if isinstance(current_schema, dict) and current_schema.get("type") == "array":
            items = current_schema.get("items")
            if isinstance(items, dict):
                current_schema = items
    return True


def validate_skill_output_mapping_contract(
    current_store: Any,
    *,
    job: dict[str, Any],
    output_mapping: dict[str, Any],
) -> dict[str, Any]:
    schema = merged_skill_output_schema(current_store, job)
    if not schema:
        return {}
    path_keys = (
        "branch_path",
        "commit_sha_path",
        "findings_path",
        "insights_path",
        "repository_id_path",
        "risk_level_path",
        "summary_path",
    )
    invalid = [
        key
        for key in path_keys
        if key in output_mapping and not schema_supports_json_path(schema, output_mapping.get(key))
    ]
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
    required = schema.get("required")
    if not isinstance(required, list):
        return
    missing = [
        item
        for item in required
        if isinstance(item, str) and item not in output_json
    ]
    if missing:
        raise api_error(
            400,
            "SKILL_OUTPUT_SCHEMA_INVALID",
            f"AI output is missing required field(s): {', '.join(missing)}",
        )


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


def scheduled_job_ai_messages(
    current_store: Any,
    *,
    job: dict[str, Any],
    output_mapping: dict[str, Any],
    source_response_json: dict[str, Any],
    source_row_count: int,
    knowledge_references: list[dict[str, Any]] | None = None,
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
    system_prompt = (
        (agent or {}).get("system_prompt")
        or "你是企业 AI 大脑的数据分析助手，负责把数据连接返回的原始数据整理为结果动作需要的 JSON。"
    )
    job_config = job.get("config_json") or {}
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
        "data_connection_response": source_response_json,
    }
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
    messages = scheduled_job_ai_messages(
        current_store,
        job=job,
        knowledge_references=knowledge_references,
        output_mapping=output_mapping,
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
        with urlopen(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        output_json = model_json_content(response_payload)
        validate_skill_output_json_contract(output_json, output_schema)
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
            error="Scheduled job AI processing failed",
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
    return {
        "knowledge_references": knowledge_references,
        "model_gateway_config_id": config["id"],
        "model_log_id": model_log["id"],
        "model": config["default_chat_model"],
        "output_json": output_json,
        "provider": config["provider"],
        "status": "succeeded",
        "tokens": model_log["tokens"],
    }
