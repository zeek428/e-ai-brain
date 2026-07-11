from __future__ import annotations

from typing import Any

from app.api.deps import api_error

BLUE_GREEN_ACTIONS = {
    "target.blue_green_rollback",
    "target.blue_green_switch",
}


def _bounded_percent(value: Any, *, field: str) -> int:
    try:
        percent = int(value)
    except (TypeError, ValueError) as exc:
        raise api_error(
            400,
            "DEPLOYMENT_WAVE_CONFIG_INVALID",
            f"{field} must be an integer percentage",
        ) from exc
    if percent < 1 or percent > 100:
        raise api_error(
            400,
            "DEPLOYMENT_WAVE_CONFIG_INVALID",
            f"{field} must be between 1 and 100",
        )
    return percent


def _batch_waves(config: dict[str, Any]) -> list[dict[str, Any]]:
    raw_waves = config.get("waves")
    if not isinstance(raw_waves, list) or not raw_waves:
        count = max(2, min(20, int(config.get("wave_count") or 2)))
        raw_waves = [
            {
                "name": f"Batch {index}",
                "traffic_percent": round(index * 100 / count),
            }
            for index in range(1, count + 1)
        ]
    waves: list[dict[str, Any]] = []
    previous = 0
    for index, raw in enumerate(raw_waves[:20], start=1):
        item = raw if isinstance(raw, dict) else {}
        percent = _bounded_percent(
            item.get("traffic_percent"),
            field=f"waves[{index - 1}].traffic_percent",
        )
        if percent <= previous:
            raise api_error(
                400,
                "DEPLOYMENT_WAVE_CONFIG_INVALID",
                "Batch traffic percentages must increase strictly",
            )
        waves.append(
            {
                "action": "deploy",
                "name": str(item.get("name") or f"Batch {index}").strip(),
                "number": index,
                "traffic_percent": percent,
            }
        )
        previous = percent
    if not waves or waves[-1]["traffic_percent"] != 100:
        raise api_error(
            400,
            "DEPLOYMENT_WAVE_CONFIG_INVALID",
            "The final batch wave must reach 100 percent",
        )
    return waves


def _blue_green_waves(config: dict[str, Any]) -> list[dict[str, Any]]:
    active_slot = str(config.get("active_slot") or "").strip()
    target_slot = str(config.get("target_slot") or "").strip()
    switch_action = str(config.get("switch_action") or "").strip()
    rollback_action = str(config.get("rollback_action") or "").strip()
    if (
        not active_slot
        or not target_slot
        or active_slot == target_slot
        or switch_action != "target.blue_green_switch"
        or rollback_action != "target.blue_green_rollback"
    ):
        raise api_error(
            400,
            "DEPLOYMENT_BLUE_GREEN_CONFIG_INVALID",
            "Blue-green rollout requires distinct slots and controlled switch/rollback actions",
        )
    return [
        {
            "action": "deploy",
            "active_slot": active_slot,
            "name": f"Deploy {target_slot}",
            "number": 1,
            "target_slot": target_slot,
            "traffic_percent": 0,
        },
        {
            "action": "traffic_switch",
            "active_slot": active_slot,
            "name": f"Switch to {target_slot}",
            "number": 2,
            "rollback_action": rollback_action,
            "switch_action": switch_action,
            "target_slot": target_slot,
            "traffic_percent": 100,
        },
    ]


def build_rollout_wave_plan(scheme_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    strategy = str(scheme_snapshot.get("rollout_strategy") or "all_at_once")
    config = (
        scheme_snapshot.get("wave_config")
        if isinstance(scheme_snapshot.get("wave_config"), dict)
        else {}
    )
    if strategy == "all_at_once":
        return [
            {
                "action": "deploy",
                "name": "All at once",
                "number": 1,
                "traffic_percent": 100,
            }
        ]
    if strategy == "canary":
        canary_percent = _bounded_percent(
            config.get("canary_percent") or 10,
            field="canary_percent",
        )
        if canary_percent >= 100:
            raise api_error(
                400,
                "DEPLOYMENT_WAVE_CONFIG_INVALID",
                "Canary percentage must be below 100",
            )
        return [
            {
                "action": "deploy",
                "name": "Canary",
                "number": 1,
                "traffic_percent": canary_percent,
            },
            {
                "action": "deploy",
                "name": "Full rollout",
                "number": 2,
                "traffic_percent": 100,
            },
        ]
    if strategy == "batch":
        return _batch_waves(config)
    if strategy == "blue_green":
        return _blue_green_waves(config)
    raise api_error(
        400,
        "VALIDATION_ERROR",
        "Unsupported deployment rollout strategy",
    )
