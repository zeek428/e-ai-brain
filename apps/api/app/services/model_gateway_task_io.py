from __future__ import annotations

import json
from typing import Any


def public_git_repository(repository: dict[str, Any]) -> dict[str, Any]:
    public_repository = {
        key: value
        for key, value in repository.items()
        if key != "credential_ref"
    }
    public_repository["credential_ref_configured"] = bool(
        repository.get("credential_ref") or repository.get("credential_ref_configured")
    )
    return public_repository


def public_product_context(product_context: Any) -> dict[str, Any]:
    if not isinstance(product_context, dict):
        return {}
    public_context = json.loads(json.dumps(product_context, ensure_ascii=False))
    repositories = public_context.get("repositories")
    if isinstance(repositories, dict):
        items = repositories.get("items")
        if isinstance(items, list):
            repositories["items"] = [
                public_git_repository(item) if isinstance(item, dict) else item
                for item in items
            ]
            repositories["total"] = len(repositories["items"])
    return public_context


def derive_code_review_risk_level(output: dict[str, Any]) -> str:
    risk_level = output.get("risk_level")
    if isinstance(risk_level, str) and risk_level.strip():
        return risk_level.strip()
    overall = str(output.get("overall") or output.get("decision") or "").lower()
    if any(marker in overall for marker in ("block", "request_changes", "high", "reject")):
        return "high"
    if any(marker in overall for marker in ("warn", "medium", "conditional", "review")):
        return "medium"
    if any(marker in overall for marker in ("approve", "low", "pass")):
        return "low"
    score = output.get("score")
    if isinstance(score, int | float):
        if score < 60:
            return "high"
        if score < 80:
            return "medium"
        return "low"
    findings = output.get("findings")
    if isinstance(findings, list):
        severities = {
            str(item.get("severity") or "").lower()
            for item in findings
            if isinstance(item, dict)
        }
        if severities & {"critical", "blocker", "high"}:
            return "high"
        if severities & {"major", "medium"}:
            return "medium"
        return "low"
    return "medium"


def normalize_model_gateway_code_review_output(output: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(output)
    normalized["risk_level"] = derive_code_review_risk_level(normalized)
    if not isinstance(normalized.get("executor"), dict):
        normalized["executor"] = {}
    return normalized


def parse_model_gateway_task_output(
    response_payload: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Model gateway response is missing choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise ValueError("Model gateway response is missing message")
    content = message.get("content")
    if isinstance(content, str):
        parsed = json.loads(content)
    elif isinstance(content, dict):
        parsed = content
    else:
        raise ValueError("Model gateway response content must be a JSON object")
    if not isinstance(parsed, dict):
        raise ValueError("Model gateway response content must be a JSON object")

    output = parsed
    if task["task_type"] == "code_review":
        output = normalize_model_gateway_code_review_output(output)
    if not isinstance(output.get("summary"), str) or not output["summary"].strip():
        raise ValueError("Model gateway response content is missing summary")
    if task["task_type"] == "code_review":
        if not isinstance(output.get("risk_level"), str):
            raise ValueError("Code review response is missing risk_level")
        if not isinstance(output.get("findings"), list):
            raise ValueError("Code review response is missing findings")
        if not isinstance(output.get("executor"), dict):
            raise ValueError("Code review response is missing executor")
    return output


def model_gateway_messages(
    *,
    code_review_payload: dict[str, Any] | None,
    task: dict[str, Any],
) -> list[dict[str, str]]:
    if task["task_type"] == "code_review":
        payload = dict(code_review_payload or {})
        payload["expected_output_schema"] = {
            "summary": "string",
            "risk_level": "low | medium | high",
            "findings": [
                {
                    "severity": "low | medium | high",
                    "file_path": "string",
                    "line_start": "integer or null",
                    "line_end": "integer or null",
                    "category": "string",
                    "message": "string",
                    "suggestion": "string",
                    "confidence": "number from 0 to 1",
                }
            ],
        }
        system_content = (
            "You are the AI Brain code-review executor. Review only the provided MR/PR "
            "snapshot, requirement, technical solution, and product context. Return one "
            "JSON object only with summary, risk_level, and findings. Do not invent file "
            "paths that are absent from changed_files_summary."
        )
    else:
        payload = {
            "input_json": task.get("input_json", {}),
            "product_context": public_product_context(task.get("product_context")),
            "requirement_snapshot": task.get("requirement_snapshot", {}),
            "task_type": task["task_type"],
            "title": task["title"],
        }
        system_content = (
            "You are the AI Brain model gateway. Return one JSON object only, "
            "without markdown, comments, or explanatory text."
        )
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]
