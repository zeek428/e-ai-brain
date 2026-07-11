from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error

_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{7,64}$")
_ARTIFACT_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


def _parse_utc_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def validate_deployment_window(
    deployment: dict[str, Any],
    *,
    now: datetime,
) -> dict[str, Any]:
    enforcement = str(deployment.get("window_enforcement") or "warn")
    start = _parse_utc_datetime(deployment.get("deploy_window_start"))
    end = _parse_utc_datetime(deployment.get("deploy_window_end"))
    within_window = (start is None or now >= start) and (end is None or now <= end)
    if enforcement == "strict" and (start is None or end is None):
        raise api_error(
            409,
            "DEPLOYMENT_WINDOW_REQUIRED",
            "Strict deployment window requires both start and end time",
        )
    if enforcement == "strict" and not within_window:
        raise api_error(
            409,
            "DEPLOYMENT_WINDOW_CLOSED",
            "Current time is outside the configured deployment window",
            {
                "deploy_window_end": deployment.get("deploy_window_end"),
                "deploy_window_start": deployment.get("deploy_window_start"),
                "evaluated_at": now.isoformat(),
            },
        )
    return {
        "enforcement": enforcement,
        "evaluated_at": now.isoformat(),
        "within_window": within_window,
        "warning": enforcement == "warn" and not within_window,
    }


def deployment_release_identity_checks(
    deployment: dict[str, Any],
) -> list[dict[str, Any]]:
    artifact_version = str(deployment.get("artifact_version") or "").strip()
    commit_sha = str(deployment.get("commit_sha") or "").strip()
    artifact_digest = str(deployment.get("artifact_digest") or "").strip()
    return [
        {
            "code": "artifact_version_present",
            "passed": bool(artifact_version),
        },
        {
            "code": "commit_sha_valid",
            "passed": bool(_COMMIT_SHA_PATTERN.fullmatch(commit_sha)),
        },
        {
            "code": "artifact_digest_valid",
            "passed": bool(_ARTIFACT_DIGEST_PATTERN.fullmatch(artifact_digest)),
        },
    ]


def require_deployment_release_identity(deployment: dict[str, Any]) -> list[dict[str, Any]]:
    checks = deployment_release_identity_checks(deployment)
    failed = [check["code"] for check in checks if not check["passed"]]
    if failed:
        raise api_error(
            409,
            "DEPLOYMENT_RELEASE_IDENTITY_INVALID",
            "Strict production deployment requires artifact version, commit SHA and SHA-256 digest",
            {"failed_checks": failed},
        )
    return checks
