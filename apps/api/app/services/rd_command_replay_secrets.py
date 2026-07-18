"""Lifecycle helpers for the short-lived claim replay secret store."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


def scrub_expired_command_replay_secrets(store: Any) -> dict[str, int]:
    """Irreversibly remove expired replay ciphertext while retaining audit identity."""
    repository = getattr(store, "repository", None)
    scrub = getattr(repository, "save_and_scrub_claim_replay_secret", None)
    if callable(scrub):
        result = scrub()
        return {"scrubbed_count": int(result.get("scrubbed_count") or 0)}

    now = datetime.now(UTC)
    secrets = getattr(store, "rd_command_replay_secrets", {})
    scrubbed_count = 0
    if not isinstance(secrets, dict):
        return {"scrubbed_count": 0}
    for secret in secrets.values():
        expires_at = _parse_time(secret.get("expires_at"))
        if (
            secret.get("secret_ciphertext") is not None
            and expires_at is not None
            and expires_at <= now
        ):
            secret["secret_ciphertext"] = None
            secret["scrubbed_at"] = now.isoformat()
            scrubbed_count += 1
    return {"scrubbed_count": scrubbed_count}
