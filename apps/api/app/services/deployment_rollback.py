from __future__ import annotations

from typing import Any

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def auto_rollback_allowed(
    *,
    risk_level: str,
    rollback_config: dict[str, Any],
) -> bool:
    enabled = bool(
        rollback_config.get("auto_on_failure")
        or rollback_config.get("auto_rollback")
    )
    if not enabled:
        return False
    threshold = str(rollback_config.get("auto_risk_threshold") or "medium")
    return RISK_ORDER.get(risk_level, RISK_ORDER["critical"]) <= RISK_ORDER.get(
        threshold,
        RISK_ORDER["medium"],
    )
