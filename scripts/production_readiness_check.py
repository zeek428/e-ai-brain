#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.core.production_readiness import (  # noqa: E402
    GateResult,
    ReadinessOptions,
    default_docker_bin,
    run_production_readiness_checks,
)


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _options_from_args(args: argparse.Namespace) -> ReadinessOptions:
    return ReadinessOptions(
        api_base_url=args.api_base_url,
        bearer_token=_env("READINESS_BEARER_TOKEN"),
        docker_bin=args.docker_bin,
        gitlab_mr_iid=_env("READINESS_GITLAB_MR_IID"),
        gitlab_repository_id=_env("READINESS_GITLAB_REPOSITORY_ID"),
        gitlab_requirement_id=_env("READINESS_REQUIREMENT_ID"),
        gitlab_technical_solution_task_id=_env("READINESS_TECHNICAL_SOLUTION_TASK_ID"),
        password=_env("READINESS_PASSWORD"),
        postgres_db=args.postgres_db,
        postgres_user=args.postgres_user,
        project_root=str(REPO_ROOT),
        username=_env("READINESS_USERNAME"),
    )


def _format_result(result: GateResult) -> str:
    prefix = "OK" if result.ok else "FAIL"
    return f"[{prefix}] {result.name}: {result.detail}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run AI Brain production-readiness gates against the local Docker stack.",
    )
    parser.add_argument(
        "--api-base-url",
        default=_env("READINESS_API_BASE_URL", "http://localhost:8000"),
        help="API base URL, defaults to READINESS_API_BASE_URL or http://localhost:8000.",
    )
    parser.add_argument(
        "--docker-bin",
        default=_env("READINESS_DOCKER_BIN", default_docker_bin()),
        help="Docker executable, defaults to READINESS_DOCKER_BIN, PATH docker, or Docker Desktop.",
    )
    parser.add_argument(
        "--postgres-db",
        default=_env("POSTGRES_DB", "ai_brain"),
        help="PostgreSQL database name used inside the compose postgres service.",
    )
    parser.add_argument(
        "--postgres-user",
        default=_env("POSTGRES_USER", "ai_brain"),
        help="PostgreSQL user used inside the compose postgres service.",
    )
    args = parser.parse_args()

    report = run_production_readiness_checks(_options_from_args(args))
    for result in report.results:
        print(_format_result(result))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
