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


def patch_runner_trust_fields(
    updates: dict[str, Any],
    *,
    runner: dict[str, Any],
    ensure_enum: Callable[[str | None, set[str], str], str],
) -> dict[str, Any]:
    patched = dict(updates)
    if "trust_domain" in patched:
        patched["trust_domain"] = ensure_enum(
            patched["trust_domain"],
            {"coding", "verification", "deployment"},
            "trust_domain",
        )
    if "attestation_status" in patched:
        patched["attestation_status"] = ensure_enum(
            patched["attestation_status"],
            {"pending", "active", "revoked"},
            "attestation_status",
        )
    if "trust_boundary_id" in patched:
        patched["trust_boundary_id"] = str(patched["trust_boundary_id"] or "").strip() or None
    if "attestation_public_key" in patched:
        trust_payload = type(
            "RunnerTrustPayload",
            (),
            {
                "attestation_public_key": patched["attestation_public_key"],
                "attestation_status": patched.get(
                    "attestation_status", runner.get("attestation_status")
                ),
                "trust_boundary_id": patched.get(
                    "trust_boundary_id", runner.get("trust_boundary_id")
                ),
                "trust_domain": patched.get("trust_domain", runner.get("trust_domain")),
            },
        )()
        patched.update(runner_trust_fields(trust_payload, ensure_enum=ensure_enum))
    return patched
