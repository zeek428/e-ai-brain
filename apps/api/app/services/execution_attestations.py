from __future__ import annotations

import base64
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def _canonical_payload_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _runner_record(current_store: Any, runner_id: str) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_runners = getattr(repository, "list_ai_executor_runners", None)
    if callable(list_runners):
        return next(
            (record for record in list_runners() if record.get("id") == runner_id),
            None,
        )
    runners = getattr(current_store, "ai_executor_runners", {})
    return deepcopy(runners.get(runner_id)) if isinstance(runners, dict) else None


def _coding_boundary(current_store: Any, coding_runner_task: dict[str, Any] | None) -> str:
    if not coding_runner_task:
        return ""
    direct = str(coding_runner_task.get("runner_trust_boundary_id") or "").strip()
    if direct:
        return direct
    runner = _runner_record(current_store, str(coding_runner_task.get("runner_id") or ""))
    return str((runner or {}).get("trust_boundary_id") or "").strip()


def _save_attestation(current_store: Any, record: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_execution_attestation_record", None)
    if callable(save_record):
        save_record(record)
    records = getattr(current_store, "execution_attestations", None)
    if isinstance(records, dict):
        records[record["id"]] = deepcopy(record)


def _existing_attestation(current_store: Any, runner_task_id: str) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_execution_attestations", None)
    if callable(list_records):
        records = list_records(runner_task_id=runner_task_id)
        return deepcopy(records[0]) if records else None
    records = getattr(current_store, "execution_attestations", {})
    if not isinstance(records, dict):
        return None
    return next(
        (
            deepcopy(record)
            for record in records.values()
            if record.get("runner_task_id") == runner_task_id
        ),
        None,
    )


def _record(
    current_store: Any,
    *,
    runner: dict[str, Any] | None,
    runner_task: dict[str, Any],
    payload: dict[str, Any],
    signature: str | None,
    status: str,
    error_code: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    payload_sha256 = hashlib.sha256(_canonical_payload_bytes(payload)).hexdigest()
    runner_task_id = str(runner_task.get("id") or "")
    existing = _existing_attestation(current_store, runner_task_id)
    record = {
        "id": str((existing or {}).get("id") or current_store.new_id("execution_attestation")),
        "subject_type": "ai_executor_task",
        "subject_id": runner_task_id,
        "runner_task_id": runner_task_id,
        "runner_id": str(runner_task.get("runner_id") or ""),
        "trust_domain": str((runner or {}).get("trust_domain") or ""),
        "trust_boundary_id": str((runner or {}).get("trust_boundary_id") or "") or None,
        "payload": deepcopy(payload),
        "payload_sha256": payload_sha256,
        "signature": signature,
        "public_key_fingerprint": (runner or {}).get("attestation_key_fingerprint"),
        "verification_status": status,
        "verification_error_code": error_code,
        "verified_at": now if status == "verified" else None,
        "created_at": now,
        "updated_at": now,
    }
    _save_attestation(current_store, record)
    return record


def verify_execution_attestation(
    current_store: Any,
    *,
    runner_task: dict[str, Any],
    required_trust_domain: str,
    coding_runner_task: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runner = _runner_record(current_store, str(runner_task.get("runner_id") or ""))
    result_json = runner_task.get("result_json")
    result_json = result_json if isinstance(result_json, dict) else {}
    proof = result_json.get("execution_attestation")
    proof = proof if isinstance(proof, dict) else {}
    payload = proof.get("payload") if isinstance(proof.get("payload"), dict) else {}
    signature = str(proof.get("signature") or "").strip() or None
    boundary = str((runner or {}).get("trust_boundary_id") or "").strip()
    coding_boundary = _coding_boundary(current_store, coding_runner_task)
    coding_runner_id = str((coding_runner_task or {}).get("runner_id") or "").strip()
    verifier_runner_id = str(runner_task.get("runner_id") or "").strip()
    if (
        runner is None
        or runner.get("status") != "active"
        or runner.get("attestation_status") != "active"
        or runner.get("trust_domain") != required_trust_domain
        or not boundary
        or boundary == coding_boundary
        or (coding_runner_id and coding_runner_id == verifier_runner_id)
    ):
        record = _record(
            current_store,
            runner=runner,
            runner_task=runner_task,
            payload=payload,
            signature=signature,
            status="blocked",
            error_code="VERIFIER_TRUST_DOMAIN_UNAVAILABLE",
        )
        return {
            "id": record["id"],
            "status": "blocked",
            "error_code": "VERIFIER_TRUST_DOMAIN_UNAVAILABLE",
            "payload_sha256": record["payload_sha256"],
        }
    if str(payload.get("runner_task_id") or "") != str(runner_task.get("id") or ""):
        record = _record(
            current_store,
            runner=runner,
            runner_task=runner_task,
            payload=payload,
            signature=signature,
            status="invalid",
            error_code="EXECUTION_ATTESTATION_INVALID",
        )
        return {
            "id": record["id"],
            "status": "invalid",
            "error_code": "EXECUTION_ATTESTATION_INVALID",
            "payload_sha256": record["payload_sha256"],
        }
    try:
        public_key = base64.b64decode(
            str(runner.get("attestation_public_key") or ""),
            validate=True,
        )
        signed_value = base64.b64decode(signature or "", validate=True)
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signed_value,
            _canonical_payload_bytes(payload),
        )
    except (InvalidSignature, ValueError, TypeError):
        record = _record(
            current_store,
            runner=runner,
            runner_task=runner_task,
            payload=payload,
            signature=signature,
            status="invalid",
            error_code="EXECUTION_ATTESTATION_INVALID",
        )
        return {
            "id": record["id"],
            "status": "invalid",
            "error_code": "EXECUTION_ATTESTATION_INVALID",
            "payload_sha256": record["payload_sha256"],
        }
    record = _record(
        current_store,
        runner=runner,
        runner_task=runner_task,
        payload=payload,
        signature=signature,
        status="verified",
    )
    return {
        "id": record["id"],
        "status": "verified",
        "payload_sha256": record["payload_sha256"],
    }
