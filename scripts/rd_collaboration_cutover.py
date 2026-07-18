#!/usr/bin/env python3
"""Operate the explicit, non-deploying R&D-collaboration cleanup contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "lock", "record-health", "cleanup"))
    parser.add_argument("--database-url", help="Required only with cleanup --execute")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the explicit cleanup SQL after verified cutover health",
    )
    args = parser.parse_args()
    if args.action != "cleanup" or not args.execute:
        print(json.dumps({"action": args.action, "executed": False, "mutates_state": False}))
        return 0
    if not args.database_url:
        parser.error("--database-url is required with cleanup --execute")
    import psycopg

    sql_path = (
        Path(__file__).resolve().parents[1]
        / "apps"
        / "api"
        / "app"
        / "db"
        / "migrations"
        / "121_requirement_driven_rd_cutover.sql"
    )
    with psycopg.connect(args.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_version, health_marker, smoke_test_json FROM rd_collaboration_upgrade_state WHERE id = %s FOR UPDATE",
                ("rd_collaboration",),
            )
            state = cursor.fetchone()
            if (
                state is None
                or int(state[0]) != 2
                or not state[1]
                or not isinstance(state[2], dict)
                or state[2].get("assessment") != "passed"
                or state[2].get("collaboration") != "passed"
            ):
                raise SystemExit(
                    "refusing cleanup: v2 schema, health marker, and both write-smoke results are required"
                )
            cursor.execute(sql_path.read_text(encoding="utf-8"))
            cursor.execute(
                "UPDATE rd_collaboration_upgrade_state SET cleanup_started_at = COALESCE(cleanup_started_at, now()), cleanup_completed_at = now(), updated_at = now() WHERE id = %s",
                ("rd_collaboration",),
            )
        connection.commit()
    print(json.dumps({"action": "cleanup", "executed": True, "deploys": False}))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))
    raise SystemExit(main())
