"""One-way maintenance fence for the R&D-collaboration cutover.

The fence deliberately governs only R&D collaboration writes.  Scheduled-job
configuration and execution are a separate product capability and must remain
available while R&D work drains.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.core.repositories.rd_collaboration import RdCollaborationVersionConflictError

UPGRADE_STATE_ID = "rd_collaboration"
_VALID_MODES = {"disabled", "draining", "cutover_locked"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _default_state() -> dict[str, Any]:
    now = _now()
    return {
        "id": UPGRADE_STATE_ID,
        "fence_mode": "disabled",
        "version": 1,
        "schema_version": 1,
        "advisory_preflight_json": {},
        "locked_preflight_json": {},
        "active_counts_json": {},
        "smoke_test_json": {},
        "fence_release_evidence": {},
        "created_at": now,
        "updated_at": now,
    }


def _repository(current_store: Any) -> Any | None:
    return getattr(current_store, "repository", None)


def _memory_states(current_store: Any) -> dict[str, dict[str, Any]]:
    states = getattr(current_store, "rd_collaboration_upgrade_state", None)
    if not isinstance(states, dict):
        states = {}
        current_store.rd_collaboration_upgrade_state = states
    return states


def get_rd_maintenance_state(current_store: Any) -> dict[str, Any]:
    repository = _repository(current_store)
    getter = getattr(repository, "get_rd_collaboration_upgrade_state", None)
    if callable(getter):
        state = getter(UPGRADE_STATE_ID)
        if state is not None:
            return deepcopy(state)
    states = _memory_states(current_store)
    if UPGRADE_STATE_ID not in states:
        states[UPGRADE_STATE_ID] = _default_state()
    return deepcopy(states[UPGRADE_STATE_ID])


def _append_audit_event(
    current_store: Any,
    *,
    actor_id: str,
    state: dict[str, Any],
    reason: str,
) -> None:
    events = getattr(current_store, "audit_events", None)
    if not isinstance(events, list):
        return
    events.append(
        {
            "id": (
                current_store.new_id("audit")
                if hasattr(current_store, "new_id")
                else f"audit:{_now()}"
            ),
            "event_type": "rd_collaboration.maintenance_fence_changed",
            "actor_id": actor_id,
            "subject_type": "rd_collaboration_upgrade",
            "subject_id": UPGRADE_STATE_ID,
            "payload": {
                "fence_mode": state["fence_mode"],
                "schema_version": state["schema_version"],
                "version": state["version"],
                "reason": reason,
            },
            "created_at": _now(),
        }
    )


def save_rd_maintenance_state(
    current_store: Any,
    *,
    expected_version: int,
    changes: dict[str, Any],
    actor_id: str,
    reason: str,
) -> dict[str, Any]:
    current = get_rd_maintenance_state(current_store)
    if int(current["version"]) != int(expected_version):
        raise api_error(
            409,
            "RD_VERSION_CONFLICT",
            "R&D collaboration upgrade state version conflict",
            {"current_version": current["version"]},
        )
    next_state = {
        **current,
        **deepcopy(changes),
        "id": UPGRADE_STATE_ID,
        "version": int(current["version"]) + 1,
        "updated_at": _now(),
    }
    repository = _repository(current_store)
    updater = getattr(repository, "update_rd_collaboration_upgrade_state", None)
    if callable(updater):
        try:
            saved = updater(
                expected_version=int(expected_version),
                changes=next_state,
            )
        except RdCollaborationVersionConflictError as exc:
            raise api_error(
                409,
                exc.code,
                str(exc),
                exc.details,
            ) from exc
        _append_audit_event(current_store, actor_id=actor_id, state=saved, reason=reason)
        return deepcopy(saved)
    _memory_states(current_store)[UPGRADE_STATE_ID] = deepcopy(next_state)
    _append_audit_event(current_store, actor_id=actor_id, state=next_state, reason=reason)
    return next_state


def _release_ready(state: dict[str, Any], expected_schema_version: int | None) -> bool:
    smoke = state.get("smoke_test_json")
    expected_schema = expected_schema_version or 2
    return (
        int(state.get("schema_version") or 0) == expected_schema
        and bool(state.get("health_marker"))
        and bool(state.get("cleanup_completed_at"))
        and isinstance(smoke, dict)
        and smoke.get("assessment") == "passed"
        and smoke.get("collaboration") == "passed"
    )


def set_rd_maintenance_fence(
    current_store: Any,
    *,
    mode: str,
    actor_id: str,
    expected_version: int,
    reason: str,
    expected_schema_version: int | None = None,
) -> dict[str, Any]:
    if mode not in _VALID_MODES:
        raise api_error(422, "VALIDATION_ERROR", "Unsupported maintenance-fence mode")
    if not reason.strip():
        raise api_error(422, "VALIDATION_ERROR", "Maintenance-fence reason is required")
    state = get_rd_maintenance_state(current_store)
    if int(state["version"]) != int(expected_version):
        raise api_error(
            409,
            "RD_VERSION_CONFLICT",
            "R&D collaboration upgrade state version conflict",
        )
    current_mode = str(state["fence_mode"])
    if mode == "draining":
        if current_mode != "disabled":
            raise api_error(409, "RD_UPGRADE_STATE_INVALID", "Fence can drain only from disabled")
        from app.services.rd_collaboration_migration import build_upgrade_preflight

        report = build_upgrade_preflight(current_store)
        return save_rd_maintenance_state(
            current_store,
            expected_version=expected_version,
            actor_id=actor_id,
            reason=reason,
            changes={
                "fence_mode": "draining",
                "fence_reason": reason,
                "advisory_preflight_json": report,
                "active_counts_json": report["active_counts"],
            },
        )
    if mode == "disabled":
        if current_mode == "disabled":
            return deepcopy(state)
        if current_mode == "draining" and not state.get("cutover_started_at"):
            return save_rd_maintenance_state(
                current_store,
                expected_version=expected_version,
                actor_id=actor_id,
                reason=reason,
                changes={
                    "abort_actor_id": actor_id,
                    "abort_reason": reason,
                    "aborted_at": _now(),
                    "fence_mode": "disabled",
                    "fence_reason": reason,
                },
            )
        if current_mode == "cutover_locked" and _release_ready(state, expected_schema_version):
            return save_rd_maintenance_state(
                current_store,
                expected_version=expected_version,
                actor_id=actor_id,
                reason=reason,
                changes={
                    "fence_mode": "disabled",
                    "fence_reason": reason,
                    "fence_released_at": _now(),
                    "fence_release_evidence": {
                        "health_marker": state["health_marker"],
                        "schema_version": state["schema_version"],
                        "smoke_test": state["smoke_test_json"],
                    },
                },
            )
        raise api_error(
            409,
            "RD_UPGRADE_ABORT_NOT_ALLOWED",
            "A cutover-locked fence can only open after v2 health and smoke evidence",
        )
    raise api_error(
        409,
        "RD_UPGRADE_STATE_INVALID",
        "Cutover lock must be entered through the validated cutover command",
    )


def lock_rd_maintenance_fence(
    current_store: Any,
    *,
    actor_id: str,
    expected_version: int,
    backup_marker: str,
    locked_preflight: dict[str, Any],
    versions: dict[str, str],
) -> dict[str, Any]:
    state = get_rd_maintenance_state(current_store)
    if state["fence_mode"] != "draining":
        raise api_error(409, "RD_UPGRADE_STATE_INVALID", "Cutover requires draining fence")
    if not backup_marker.strip():
        raise api_error(422, "VALIDATION_ERROR", "Backup marker is required")
    if not locked_preflight.get("ready"):
        raise api_error(
            409,
            "RD_UPGRADE_STATE_INVALID",
            "Cutover preflight is blocked",
            locked_preflight,
        )
    return save_rd_maintenance_state(
        current_store,
        expected_version=expected_version,
        actor_id=actor_id,
        reason="validated cutover lock",
        changes={
            "active_counts_json": locked_preflight["active_counts"],
            "backup_marker": backup_marker,
            "cutover_started_at": _now(),
            "fence_mode": "cutover_locked",
            "locked_preflight_json": locked_preflight,
            "schema_version": 2,
            "v2_api_version": versions["v2_api_version"],
            "v2_graph_version": versions["v2_graph_version"],
            "v2_worker_version": versions["v2_worker_version"],
        },
    )


def require_rd_write_allowed(
    current_store: Any,
    *,
    operation: str,
    allow_inflight_completion: bool = False,
) -> None:
    state = get_rd_maintenance_state(current_store)
    if state["fence_mode"] == "disabled" or allow_inflight_completion:
        return
    raise api_error(
        423,
        "RD_UPGRADE_MAINTENANCE",
        "R&D collaboration write is blocked while maintenance fence is active",
        {
            "fence_mode": state["fence_mode"],
            "fence_version": state["version"],
            "operation": operation,
        },
    )
