from __future__ import annotations

import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.store import MemoryStore
from app.services.execution_attestations import verify_execution_attestation


def _signed_verifier_task(
    *,
    boundary_id: str,
    private_key: Ed25519PrivateKey,
) -> tuple[dict, dict]:
    payload = {
        "base_commit": "abc123",
        "result_commit": "def456",
        "runner_task_id": "ai_executor_task_verify_001",
        "test_summary": {"passed": 3},
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    signature = private_key.sign(serialized)
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    runner = {
        "id": "runner_verify_001",
        "attestation_public_key": base64.b64encode(public_key).decode("ascii"),
        "attestation_status": "active",
        "status": "active",
        "trust_boundary_id": boundary_id,
        "trust_domain": "verification",
    }
    task = {
        "id": "ai_executor_task_verify_001",
        "runner_id": runner["id"],
        "result_json": {
            "execution_attestation": {
                "payload": payload,
                "signature": base64.b64encode(signature).decode("ascii"),
            }
        },
    }
    return runner, task


def _coding_task(*, boundary_id: str) -> dict:
    return {
        "id": "ai_executor_task_code_001",
        "runner_id": "runner_code_001",
        "runner_trust_boundary_id": boundary_id,
    }


def test_valid_verifier_attestation_is_verified_and_recorded() -> None:
    store = MemoryStore()
    private_key = Ed25519PrivateKey.generate()
    runner, verifier_task = _signed_verifier_task(
        boundary_id="boundary-verify",
        private_key=private_key,
    )
    store.ai_executor_runners[runner["id"]] = runner

    result = verify_execution_attestation(
        store,
        runner_task=verifier_task,
        required_trust_domain="verification",
        coding_runner_task=_coding_task(boundary_id="boundary-code"),
    )

    assert result["status"] == "verified"
    assert result["payload_sha256"]
    assert store.execution_attestations[result["id"]]["verification_status"] == "verified"


def test_verifier_sharing_coding_trust_boundary_is_blocked() -> None:
    store = MemoryStore()
    private_key = Ed25519PrivateKey.generate()
    runner, verifier_task = _signed_verifier_task(
        boundary_id="boundary-shared",
        private_key=private_key,
    )
    store.ai_executor_runners[runner["id"]] = runner

    result = verify_execution_attestation(
        store,
        runner_task=verifier_task,
        required_trust_domain="verification",
        coding_runner_task=_coding_task(boundary_id="boundary-shared"),
    )

    assert result["status"] == "blocked"
    assert result["error_code"] == "VERIFIER_TRUST_DOMAIN_UNAVAILABLE"


def test_repeated_runner_task_proof_reuses_the_same_attestation_id() -> None:
    store = MemoryStore()
    private_key = Ed25519PrivateKey.generate()
    runner, verifier_task = _signed_verifier_task(
        boundary_id="boundary-verify",
        private_key=private_key,
    )
    store.ai_executor_runners[runner["id"]] = runner

    first = verify_execution_attestation(
        store,
        runner_task=verifier_task,
        required_trust_domain="verification",
        coding_runner_task=_coding_task(boundary_id="boundary-code"),
    )
    repeated = verify_execution_attestation(
        store,
        runner_task=verifier_task,
        required_trust_domain="verification",
        coding_runner_task=_coding_task(boundary_id="boundary-code"),
    )

    assert repeated["id"] == first["id"]
    assert len(store.execution_attestations) == 1


def test_verifier_reusing_the_coding_runner_id_is_blocked() -> None:
    store = MemoryStore()
    private_key = Ed25519PrivateKey.generate()
    runner, verifier_task = _signed_verifier_task(
        boundary_id="boundary-verify",
        private_key=private_key,
    )
    store.ai_executor_runners[runner["id"]] = runner

    result = verify_execution_attestation(
        store,
        runner_task=verifier_task,
        required_trust_domain="verification",
        coding_runner_task={
            **_coding_task(boundary_id="boundary-code"),
            "runner_id": runner["id"],
        },
    )

    assert result["status"] == "blocked"
    assert result["error_code"] == "VERIFIER_TRUST_DOMAIN_UNAVAILABLE"


def test_attestation_payload_must_reference_the_current_runner_task() -> None:
    store = MemoryStore()
    private_key = Ed25519PrivateKey.generate()
    runner, verifier_task = _signed_verifier_task(
        boundary_id="boundary-verify",
        private_key=private_key,
    )
    verifier_task["result_json"]["execution_attestation"]["payload"]["runner_task_id"] = "other"
    serialized = json.dumps(
        verifier_task["result_json"]["execution_attestation"]["payload"],
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    verifier_task["result_json"]["execution_attestation"]["signature"] = base64.b64encode(
        private_key.sign(serialized),
    ).decode("ascii")
    store.ai_executor_runners[runner["id"]] = runner

    result = verify_execution_attestation(
        store,
        runner_task=verifier_task,
        required_trust_domain="verification",
        coding_runner_task=_coding_task(boundary_id="boundary-code"),
    )

    assert result["status"] == "invalid"
    assert result["error_code"] == "EXECUTION_ATTESTATION_INVALID"
