#!/usr/bin/env python3
"""Run an advisory R&D-collaboration cutover preflight without changing state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


_ACTIVE_STATUSES = {
    "active_ai_tasks": (
        "ai_tasks",
        ("draft", "running", "waiting_more_info", "waiting_review", "writing_back"),
    ),
    "active_agent_loops": (
        "agent_loop_runs",
        ("planning", "executing", "verifying", "reflecting", "waiting_review"),
    ),
    "active_runner_tasks": ("ai_executor_tasks", ("queued", "claimed", "running")),
    "active_collaboration_runs": (
        "rd_collaboration_runs",
        (
            "running",
            "integrating",
            "verifying",
            "waiting_human",
            "ready_for_release",
            "deploying",
        ),
    ),
}


def _live_report(database_url: str) -> dict[str, object]:
    """Read the same durable activity indicators as the API preflight endpoint."""
    import psycopg

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            active_counts: dict[str, int] = {}
            for count_key, (table, statuses) in _ACTIVE_STATUSES.items():
                cursor.execute(
                    f"SELECT count(*) FROM {table} WHERE status = ANY(%s)",
                    (list(statuses),),
                )
                active_counts[count_key] = int(cursor.fetchone()[0])
            cursor.execute(
                """
                SELECT id
                FROM rd_task_executor_policies
                WHERE status = 'active'
                  AND (strategy_config IS NULL OR jsonb_typeof(strategy_config) <> 'object')
                ORDER BY id
                """
            )
            legacy_policy_ids = [str(row[0]) for row in cursor.fetchall()]
            cursor.execute(
                """
                SELECT fence_mode, version, schema_version, cleanup_started_at, cleanup_completed_at
                FROM rd_collaboration_upgrade_state
                WHERE id = %s
                """,
                ("rd_collaboration",),
            )
            state = cursor.fetchone()
    blockers = [
        {"code": code, "count": active_counts[count_key]}
        for count_key, code in (
            ("active_ai_tasks", "RD_UPGRADE_ACTIVE_TASKS"),
            ("active_agent_loops", "RD_UPGRADE_ACTIVE_AGENT_LOOPS"),
            ("active_runner_tasks", "RD_UPGRADE_ACTIVE_RUNNER_TASKS"),
            ("active_collaboration_runs", "RD_UPGRADE_ACTIVE_COLLABORATION_RUNS"),
        )
        if active_counts[count_key]
    ]
    if legacy_policy_ids:
        blockers.append(
            {"code": "RD_UPGRADE_POLICY_CONVERSION_REQUIRED", "policy_ids": legacy_policy_ids}
        )
    return {
        "active_counts": active_counts,
        "blockers": blockers,
        "ready": not blockers,
        "state": (
            {
                "fence_mode": state[0],
                "version": state[1],
                "schema_version": state[2],
                "cleanup_started_at": state[3].isoformat() if state[3] else None,
                "cleanup_completed_at": state[4].isoformat() if state[4] else None,
            }
            if state
            else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", help="PostgreSQL URL used only for a live advisory query")
    parser.add_argument("--json", action="store_true", help="Print machine-readable guidance")
    args = parser.parse_args()
    payload = {
        "action": "advisory_preflight",
        "mutates_state": False,
        "next_action": "Use the authenticated upgrade preflight endpoint or the cutover command after review.",
    }
    if args.database_url:
        payload["database_url_supplied"] = True
        payload["report"] = _live_report(args.database_url)
    else:
        payload["database_url_supplied"] = False
    print(json.dumps(payload, ensure_ascii=False) if args.json else payload["next_action"])
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))
    raise SystemExit(main())
