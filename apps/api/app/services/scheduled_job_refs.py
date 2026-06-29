from __future__ import annotations

from typing import Any


def payload_field(payload: Any, name: str, default: Any = None) -> Any:
    if isinstance(payload, dict):
        return payload.get(name, default)
    return getattr(payload, name, default)


def normalized_string_ids(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        if item is None:
            continue
        item_id = str(item).strip()
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        result.append(item_id)
    return result


def scheduled_job_orchestration_config(config_json: Any) -> dict[str, Any]:
    if not isinstance(config_json, dict):
        return {}
    orchestration = config_json.get("orchestration")
    return dict(orchestration) if isinstance(orchestration, dict) else {}


def scheduled_job_multi_ids_from_config(config_json: Any, key: str) -> list[str]:
    return normalized_string_ids(scheduled_job_orchestration_config(config_json).get(key))


def scheduled_job_multi_ids(payload: Any, plural_key: str, singular_key: str) -> list[str]:
    return normalized_string_ids(
        [
            *normalized_string_ids(payload_field(payload, plural_key, [])),
            *scheduled_job_multi_ids_from_config(
                payload_field(payload, "config_json", {}),
                plural_key,
            ),
            payload_field(payload, singular_key),
        ]
    )
