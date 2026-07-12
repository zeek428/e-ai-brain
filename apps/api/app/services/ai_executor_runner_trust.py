from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any


def runner_trust_fields(
    payload: Any,
    *,
    ensure_enum: Callable[[str | None, set[str], str], str],
) -> dict[str, str | None]:
    public_key = str(getattr(payload, "attestation_public_key", None) or "").strip() or None
    return {
        "attestation_key_fingerprint": (
            hashlib.sha256(public_key.encode("utf-8")).hexdigest() if public_key else None
        ),
        "attestation_public_key": public_key,
        "attestation_status": ensure_enum(
            getattr(payload, "attestation_status", None) or "pending",
            {"pending", "active", "revoked"},
            "attestation_status",
        ),
        "trust_boundary_id": str(getattr(payload, "trust_boundary_id", None) or "").strip() or None,
        "trust_domain": ensure_enum(
            getattr(payload, "trust_domain", None) or "coding",
            {"coding", "verification", "deployment"},
            "trust_domain",
        ),
    }
