from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


def estimate_tokens(value: Any) -> int:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return max(1, len(serialized) // 4)


def openai_usage_tokens(
    usage: Any,
    *,
    messages: list[dict[str, str]],
    output: dict[str, Any],
) -> dict[str, int]:
    if not isinstance(usage, dict):
        prompt = estimate_tokens(messages)
        completion = estimate_tokens(output)
        return {"prompt": prompt, "completion": completion, "total": prompt + completion}
    prompt = int(usage.get("prompt_tokens") or estimate_tokens(messages))
    completion = int(usage.get("completion_tokens") or estimate_tokens(output))
    total = int(usage.get("total_tokens") or prompt + completion)
    return {"prompt": prompt, "completion": completion, "total": total}


def openai_embedding_usage_tokens(
    usage: Any,
    *,
    inputs: list[str],
) -> dict[str, int]:
    if not isinstance(usage, dict):
        prompt = estimate_tokens(inputs)
        return {"prompt": prompt, "completion": 0, "total": prompt}
    prompt = int(usage.get("prompt_tokens") or estimate_tokens(inputs))
    total = int(usage.get("total_tokens") or prompt)
    return {"prompt": prompt, "completion": 0, "total": total}


def model_gateway_log(
    current_store: Any,
    *,
    provider: str,
    model: str,
    config_id: str | None,
    tokens: dict[str, int],
    latency_ms: int,
    status: str,
    task: dict[str, Any] | None = None,
    purpose: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    ai_task_id = task["id"] if task else None
    resolved_purpose = purpose or (task["task_type"] if task else "model_gateway")
    log = {
        "id": current_store.new_id("model_log"),
        "ai_task_id": ai_task_id,
        "provider": provider,
        "model": model,
        "purpose": resolved_purpose,
        "tokens": tokens,
        "latency_ms": latency_ms,
        "status": status,
        "error": error,
        "model_gateway_config_id": config_id,
        "created_at": datetime.now(UTC).isoformat(),
    }
    current_store.model_gateway_logs.append(log)
    return log
