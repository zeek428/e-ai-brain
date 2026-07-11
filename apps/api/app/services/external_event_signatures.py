from __future__ import annotations

import hashlib
import hmac
import os
from collections.abc import Mapping

from app.api.deps import api_error


def resolve_webhook_secret(secret_ref: str) -> bytes:
    normalized = str(secret_ref or "").strip()
    if not normalized.startswith("env:"):
        raise api_error(
            409,
            "WEBHOOK_SECRET_UNAVAILABLE",
            "Webhook secret must use an env: reference",
        )
    env_name = normalized.removeprefix("env:").strip()
    value = os.getenv(env_name, "")
    if not env_name or not value:
        raise api_error(
            409,
            "WEBHOOK_SECRET_UNAVAILABLE",
            "Webhook secret reference cannot be resolved",
        )
    return value.encode()


def _normalized_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items()}


def verify_external_event_signature(
    *,
    provider: str,
    secret_ref: str,
    body: bytes,
    headers: Mapping[str, str],
) -> str:
    normalized_headers = _normalized_headers(headers)
    secret = resolve_webhook_secret(secret_ref)
    if provider == "gitlab":
        supplied = normalized_headers.get("x-gitlab-token", "").encode()
        verified = hmac.compare_digest(supplied, secret)
    else:
        header_name = (
            "x-hub-signature-256"
            if provider == "github"
            else "x-ai-brain-signature"
        )
        supplied = normalized_headers.get(header_name, "")
        expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
        verified = hmac.compare_digest(supplied, expected)
    if not verified:
        raise api_error(401, "WEBHOOK_SIGNATURE_INVALID", "Webhook signature is invalid")
    return "verified"
