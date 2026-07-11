import pytest
from fastapi import HTTPException

from app.services.deployment_rollouts import build_rollout_wave_plan


def test_batch_rollout_builds_bounded_ordered_waves() -> None:
    waves = build_rollout_wave_plan(
        {
            "rollout_strategy": "batch",
            "wave_config": {
                "waves": [
                    {"name": "第一批", "traffic_percent": 25},
                    {"name": "第二批", "traffic_percent": 60},
                    {"name": "全量", "traffic_percent": 100},
                ]
            },
        }
    )

    assert [wave["number"] for wave in waves] == [1, 2, 3]
    assert [wave["traffic_percent"] for wave in waves] == [25, 60, 100]


def test_blue_green_requires_controlled_slot_actions() -> None:
    with pytest.raises(HTTPException) as exc_info:
        build_rollout_wave_plan(
            {"rollout_strategy": "blue_green", "wave_config": {}}
        )

    assert exc_info.value.detail["code"] == "DEPLOYMENT_BLUE_GREEN_CONFIG_INVALID"

    waves = build_rollout_wave_plan(
        {
            "rollout_strategy": "blue_green",
            "wave_config": {
                "active_slot": "blue",
                "rollback_action": "target.blue_green_rollback",
                "switch_action": "target.blue_green_switch",
                "target_slot": "green",
            },
        }
    )
    assert waves[0]["target_slot"] == "green"
    assert waves[1]["action"] == "traffic_switch"
