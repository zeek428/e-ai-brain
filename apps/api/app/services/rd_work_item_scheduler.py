"""Deterministic DAG scheduling primitives for R&D collaboration runs."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.api.deps import api_error
from app.core.config import get_settings
from app.services.rd_feedback_attribution import record_role_feedback
from app.services.rd_role_experiences import generate_role_experience_candidate_from_feedback

_SATISFIED_PREDECESSOR_STATES = {"completed", "approved"}
_TERMINAL_WORK_ITEM_STATES = {"completed", "approved", "failed", "cancelled"}
_INTEGRATION_WORK_ITEM_TYPES = {
    "automated_testing",
    "integration",
    "integration_test",
    "version_integration",
}


def _records(store: Any, name: str) -> dict[str, dict[str, Any]]:
    values = getattr(store, name, None)
    if not isinstance(values, dict):
        values = {}
        setattr(store, name, values)
    return values


def _repository(store: Any) -> Any | None:
    return getattr(store, "repository", None)


def _work_items(store: Any, collaboration_run_id: str) -> list[dict[str, Any]]:
    repository = _repository(store)
    list_items = getattr(repository, "list_rd_work_items", None)
    if callable(list_items):
        return [dict(item) for item in list_items(collaboration_run_id)]
    return [
        item
        for item in _records(store, "rd_work_items").values()
        if item.get("collaboration_run_id") == collaboration_run_id
    ]


def _dependencies(store: Any, collaboration_run_id: str) -> list[dict[str, Any]]:
    repository = _repository(store)
    list_dependencies = getattr(repository, "list_rd_work_item_dependencies", None)
    if callable(list_dependencies):
        return [dict(item) for item in list_dependencies(collaboration_run_id)]
    return [
        dependency
        for dependency in _records(store, "rd_work_item_dependencies").values()
        if dependency.get("collaboration_run_id") == collaboration_run_id
    ]


def ready_work_items(
    store: Any,
    *,
    collaboration_run_id: str,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Return only items whose full predecessor set is satisfied.

    This is intentionally a read-side scheduler primitive.  State transitions
    are performed by a command service with optimistic locking, so a stale
    listing can never grant a lease by itself.
    """
    observed_at = now or _now()
    items = {str(item["id"]): item for item in _work_items(store, collaboration_run_id)}
    dependencies = _dependencies(store, collaboration_run_id)
    ready: list[dict[str, Any]] = []
    for item_id, item in items.items():
        if item.get("status") not in {"ready", "draft", "rework_required", "blocked"}:
            continue
        next_dispatch_at = _parse_time(item.get("next_dispatch_at"))
        if next_dispatch_at is not None and next_dispatch_at > observed_at:
            continue
        predecessor_ids = [
            str(edge.get("predecessor_work_item_id"))
            for edge in dependencies
            if edge.get("successor_work_item_id") == item_id
        ]
        if all(
            items.get(predecessor_id, {}).get("status") in _SATISFIED_PREDECESSOR_STATES
            for predecessor_id in predecessor_ids
        ):
            ready.append(deepcopy(item))
    return sorted(ready, key=lambda item: (int(item.get("priority") or 100), str(item["id"])))


def is_terminal_work_item_status(status: str | None) -> bool:
    return status in _TERMINAL_WORK_ITEM_STATES


def advance_delivery_phase_after_work_item_completion(
    store: Any,
    *,
    collaboration_run_id: str,
) -> dict[str, Any] | None:
    """Advance only the two delivery phases proved by approved work items.

    This is the MemoryStore counterpart of the repository transaction.  A
    completion signal is accepted only after the work-item review command has
    persisted ``status=completed``.  The explicit integration item is the
    safety boundary: a run cannot leave ``running`` without one, and cannot
    reach ``verifying`` until every integration item has been independently
    accepted.
    """
    run = _records(store, "rd_collaboration_runs").get(collaboration_run_id)
    if run is None or run.get("status") not in {"running", "integrating"}:
        return None
    work_items = _work_items(store, collaboration_run_id)
    integration_items = [
        item
        for item in work_items
        if str(item.get("work_item_type") or "").strip().lower() in _INTEGRATION_WORK_ITEM_TYPES
    ]
    if not integration_items:
        return None
    current_status = str(run["status"])
    if current_status == "running":
        predecessor_items = [item for item in work_items if item not in integration_items]
        next_status = (
            "integrating"
            if predecessor_items
            and all(item.get("status") == "completed" for item in predecessor_items)
            else None
        )
    else:
        next_status = (
            "verifying" if all(item.get("status") == "completed" for item in work_items) else None
        )
    if next_status is None:
        return None
    event_key = f"delivery-phase:{collaboration_run_id}:{current_status}:{next_status}"
    events = _records(store, "rd_collaboration_events")
    existing = next(
        (
            event
            for event in events.values()
            if event.get("collaboration_run_id") == collaboration_run_id
            and event.get("event_key") == event_key
        ),
        None,
    )
    if existing is not None:
        return dict(run)
    run.update(
        {
            "status": next_status,
            "version": int(run.get("version") or 1) + 1,
            "updated_at": _now().isoformat(),
        }
    )
    event = {
        "id": _new_id(store, "rd_collaboration_event"),
        "collaboration_run_id": collaboration_run_id,
        "event_type": "run.delivery_phase_advanced",
        "event_key": event_key,
        "subject_type": "rd_collaboration_run",
        "subject_id": collaboration_run_id,
        "payload_json": {
            "from_status": current_status,
            "to_status": next_status,
            "evidence": "approved_work_items",
        },
        "occurred_at": _now().isoformat(),
    }
    events[event["id"]] = event
    return dict(run)


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id(store: Any, prefix: str) -> str:
    factory = getattr(store, "new_id", None)
    if callable(factory):
        return str(factory(prefix))
    return f"{prefix}_{secrets.token_hex(8)}"


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().app_secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encode_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def _decode_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise api_error(
            409,
            "RD_WORK_ITEM_LEASE_EXPIRED",
            "The claim replay lease is no longer available",
            {"retryable": False, "next_action": "wait_for_scheduler_requeue"},
        ) from exc


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


def _command_key(*, command_type: str, aggregate_id: str, idempotency_key: str) -> str:
    return f"{command_type}:{aggregate_id}:{idempotency_key}"


def _actor_matches_seat(actor: dict[str, Any], seat: dict[str, Any]) -> bool:
    if "admin" in set(actor.get("roles") or []):
        return True
    actor_id = str(actor.get("id") or "")
    if seat.get("subject_type") == "human_user":
        return actor_id == str(seat.get("human_user_id") or "")
    return actor_id == str(seat.get("ai_employee_id") or "")


def _claim_response(
    *,
    work_item: dict[str, Any],
    attempt: dict[str, Any],
    run: dict[str, Any],
    seat: dict[str, Any],
) -> dict[str, Any]:
    return {
        "work_item": deepcopy(work_item),
        "attempt": deepcopy(attempt),
        "lease_expires_at": work_item.get("lease_expires_at"),
        "lease_holder": {
            "seat_id": seat["id"],
            "subject_type": seat.get("subject_type"),
            "subject_id": seat.get("human_user_id")
            if seat.get("subject_type") == "human_user"
            else seat.get("ai_employee_id"),
        },
        "run": deepcopy(run),
        "next_state": "running",
    }


def claim_work_item(
    store: Any,
    *,
    work_item_id: str,
    actor: dict[str, Any],
    expected_version: int,
    lease_seconds: int,
    idempotency_key: str,
) -> dict[str, Any]:
    """Grant one lease after rechecking the complete DAG and frozen seat.

    The in-memory branch is used only by test fixtures.  PostgreSQL callers
    use the same immutable command vocabulary through the repository in later
    command adapters; no caller is allowed to manufacture a replacement lease.
    """
    from app.services.rd_maintenance_fence import require_rd_write_allowed

    require_rd_write_allowed(store, operation="work_item.claim")
    if not 60 <= lease_seconds <= 1800:
        raise api_error(422, "VALIDATION_ERROR", "lease_seconds must be between 60 and 1800")
    request = {
        "expected_version": expected_version,
        "lease_seconds": lease_seconds,
        "actor_id": actor.get("id"),
    }
    request_hash = _canonical_hash(request)
    command_id = _command_key(
        command_type="claim_work_item", aggregate_id=work_item_id, idempotency_key=idempotency_key
    )
    commands = _records(store, "rd_command_idempotency_records")
    existing = commands.get(command_id)
    if existing is not None:
        if existing.get("request_hash") != request_hash:
            raise api_error(
                409,
                "RD_IDEMPOTENCY_CONFLICT",
                "Idempotency key is already bound to a different request",
            )
        secret = _records(store, "rd_command_replay_secrets").get(command_id)
        expires_at = _parse_time((secret or {}).get("expires_at"))
        if (
            not secret
            or not secret.get("secret_ciphertext")
            or expires_at is None
            or expires_at <= _now()
        ):
            if secret is not None:
                secret["secret_ciphertext"] = None
                secret["scrubbed_at"] = _now().isoformat()
            raise api_error(
                409,
                "RD_WORK_ITEM_LEASE_EXPIRED",
                "The claim replay lease has expired",
                {"retryable": False, "next_action": "wait_for_scheduler_requeue"},
            )
        return {
            **deepcopy(existing["response_snapshot"]),
            "lease_token": _decode_secret(str(secret["secret_ciphertext"])),
            "idempotent_replay": True,
        }

    repository = _repository(store)
    if repository is not None:
        return _claim_work_item_repository(
            repository,
            store=store,
            work_item_id=work_item_id,
            actor=actor,
            expected_version=expected_version,
            lease_seconds=lease_seconds,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )

    work_items = _records(store, "rd_work_items")
    item = work_items.get(work_item_id)
    if item is None:
        raise api_error(404, "NOT_FOUND", "Work item not found")
    if item.get("status") != "ready" or int(item.get("version") or 1) != expected_version:
        raise api_error(
            409,
            "RD_VERSION_CONFLICT",
            "Work item is not ready at the requested version",
            {"current_version": item.get("version"), "retryable": False},
        )
    run = _records(store, "rd_collaboration_runs").get(str(item.get("collaboration_run_id")))
    if run is None or run.get("status") not in {"running", "integrating", "verifying"}:
        raise api_error(
            409,
            "RD_WORK_ITEM_NOT_READY",
            "Collaboration run is not dispatchable",
        )
    if work_item_id not in {
        entry["id"] for entry in ready_work_items(store, collaboration_run_id=run["id"])
    }:
        raise api_error(409, "RD_WORK_ITEM_NOT_READY", "Work item dependencies are not satisfied")
    seat = _records(store, "rd_run_seats").get(str(item.get("owner_seat_id")))
    if seat is None or seat.get("status") != "active" or not _actor_matches_seat(actor, seat):
        raise api_error(
            409,
            "RD_ROLE_ASSIGNMENT_REQUIRED",
            "Caller does not match an active frozen owner seat",
            {"retryable": False, "next_action": "assign_role_seat"},
        )

    lease_token = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(seconds=lease_seconds)
    attempt_no = 1 + max(
        (
            int(candidate.get("attempt_no") or 0)
            for candidate in _records(store, "rd_work_item_attempts").values()
            if candidate.get("work_item_id") == work_item_id
        ),
        default=0,
    )
    attempt = {
        "id": _new_id(store, "rd_work_item_attempt"),
        "work_item_id": work_item_id,
        "attempt_no": attempt_no,
        "idempotency_key": idempotency_key,
        "lease_id": _new_id(store, "rd_lease"),
        "lease_token_hash": hashlib.sha256(lease_token.encode()).hexdigest(),
        "status": "running",
        "executor_profile_id": seat.get("executor_profile_id"),
        "claimed_at": _now().isoformat(),
    }
    item.update(
        {
            "status": "running",
            "lease_owner": seat["id"],
            "lease_expires_at": expires_at.isoformat(),
            "version": int(item.get("version") or 1) + 1,
        }
    )
    _records(store, "rd_work_item_attempts")[attempt["id"]] = attempt
    snapshot = _claim_response(work_item=item, attempt=attempt, run=run, seat=seat)
    commands[command_id] = {
        "id": command_id,
        "command_type": "claim_work_item",
        "aggregate_id": work_item_id,
        "idempotency_key": idempotency_key,
        "request_hash": request_hash,
        "response_snapshot": deepcopy(snapshot),
        "response_hash": _canonical_hash(snapshot),
    }
    _records(store, "rd_command_replay_secrets")[command_id] = {
        "id": _new_id(store, "rd_command_replay_secret"),
        "command_record_id": command_id,
        "secret_ciphertext": _encode_secret(lease_token),
        "key_id": "app-secret-v1",
        "expires_at": expires_at.isoformat(),
        "scrubbed_at": None,
    }
    return {**snapshot, "lease_token": lease_token, "idempotent_replay": False}


def _claim_work_item_repository(
    repository: Any,
    *,
    store: Any,
    work_item_id: str,
    actor: dict[str, Any],
    expected_version: int,
    lease_seconds: int,
    idempotency_key: str,
    request_hash: str,
) -> dict[str, Any]:
    """Use the repository's single transaction/idempotency primitive in production."""
    execute = getattr(repository, "execute_idempotent_rd_command", None)
    get_item = getattr(repository, "get_rd_work_item", None)
    get_run = getattr(repository, "get_rd_collaboration_run", None)
    get_seat = getattr(repository, "get_rd_run_seat", None)
    if not all(callable(method) for method in (execute, get_item, get_run, get_seat)):
        raise api_error(
            503, "REPOSITORY_REQUIRED", "Collaboration command repository is unavailable"
        )
    item = get_item(work_item_id)
    if item is None:
        raise api_error(404, "NOT_FOUND", "Work item not found")
    run = get_run(str(item["collaboration_run_id"]))
    seat = get_seat(str(item["owner_seat_id"])) if item.get("owner_seat_id") else None
    if run is None or seat is None or not _actor_matches_seat(actor, seat):
        raise api_error(409, "RD_ROLE_ASSIGNMENT_REQUIRED", "Frozen owner seat is unavailable")
    lease_token = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(seconds=lease_seconds)
    attempt = {
        "id": _new_id(store, "rd_work_item_attempt"),
        "work_item_id": work_item_id,
        "attempt_no": len(repository.list_rd_work_item_attempts(work_item_id)) + 1,
        "idempotency_key": idempotency_key,
        "lease_id": _new_id(store, "rd_lease"),
        "lease_token_hash": hashlib.sha256(lease_token.encode()).hexdigest(),
        "status": "running",
        "executor_profile_id": seat.get("executor_profile_id"),
        "claimed_at": _now(),
    }

    def operation(transaction: Any) -> dict[str, Any]:
        claimed = transaction.claim_ready_work_item(
            work_item_id,
            lease_owner=str(seat["id"]),
            lease_seconds=lease_seconds,
            expected_version=expected_version,
            attempt=attempt,
        )
        if claimed is None:
            raise api_error(409, "RD_WORK_ITEM_NOT_READY", "Work item is not ready for claim")
        persisted = transaction.save_work_item_attempt_bundle(
            work_item_id=work_item_id,
            expected_statuses=["claimed"],
            next_status="running",
            attempt=attempt,
            expected_version=int(claimed["work_item"]["version"]),
        )
        response = _claim_response(
            work_item=persisted["work_item"],
            attempt=persisted["attempt"],
            run=run,
            seat=seat,
        )
        return {
            "result_type": "rd_work_item_attempt",
            "result_id": persisted["attempt"]["id"],
            "http_status": 200,
            "response_json": response,
            "claim_replay_secret": {
                "id": _new_id(store, "rd_command_replay_secret"),
                "secret_ciphertext": _encode_secret(lease_token),
                "key_id": "app-secret-v1",
                "expires_at": expires_at,
            },
        }

    result = execute(
        command_type="claim_work_item",
        aggregate_type="rd_work_item",
        aggregate_id=work_item_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        operation=operation,
    )
    response = dict(result["response_json"])
    if result["idempotent_replay"]:
        secret = repository.get_valid_claim_replay_secret(result["command_record"]["id"])
        if secret is None:
            raise api_error(409, "RD_WORK_ITEM_LEASE_EXPIRED", "The claim replay lease has expired")
        response["lease_token"] = _decode_secret(str(secret["secret_ciphertext"]))
    else:
        response["lease_token"] = lease_token
    response["idempotent_replay"] = bool(result["idempotent_replay"])
    return response


def _active_attempt(store: Any, *, work_item_id: str, attempt_id: str) -> dict[str, Any]:
    attempt = _records(store, "rd_work_item_attempts").get(attempt_id)
    if attempt is None or attempt.get("work_item_id") != work_item_id:
        raise api_error(
            409, "RD_WORK_ITEM_STATE_INVALID", "Attempt does not belong to the work item"
        )
    return attempt


def _fence_linked_delivery_memory(
    store: Any,
    *,
    attempt: dict[str, Any] | None,
    item: dict[str, Any],
    reason: str,
) -> None:
    """Cancel local delivery state and enqueue the asynchronous Runner stop.

    The external process may already be executing, so the outbox is not a
    substitute for local fencing: task/review/attempt state changes happen
    first and make every late Runner callback audit-only.
    """
    now = _now().isoformat()
    work_item_id = str(item["id"])
    task_store = _records(store, "ai_tasks")
    task_ids = [
        task_id for task_id, task in task_store.items() if task.get("work_item_id") == work_item_id
    ]
    for task_id in task_ids:
        task = task_store[task_id]
        if task.get("status") not in {"completed", "failed", "cancelled"}:
            task.update(
                {
                    "status": "cancelled",
                    "current_step": "rd_work_item_cancelled",
                    "error_code": "RD_WORK_ITEM_CANCELLED",
                    "error_message": reason,
                    "updated_at": now,
                }
            )
    for review in _records(store, "human_reviews").values():
        if review.get("ai_task_id") in task_ids and review.get("status") == "pending":
            review.update(
                {
                    "status": "cancelled",
                    "decision_reason": reason,
                    "decided_at": now,
                    "updated_at": now,
                    "version": int(review.get("version") or 1) + 1,
                }
            )
    runner_tasks = _records(store, "ai_executor_tasks")
    runner_task_ids = [
        runner_task_id
        for runner_task_id, runner_task in runner_tasks.items()
        if runner_task.get("ai_task_id") in task_ids
    ]
    for runner_task_id in runner_task_ids:
        runner_task = runner_tasks[runner_task_id]
        if runner_task.get("status") in {"succeeded", "failed", "cancelled", "timed_out"}:
            continue
        runner_task.update(
            {
                "status": (
                    "cancelled" if runner_task.get("status") == "queued" else "cancel_requested"
                ),
                "error_code": "RD_WORK_ITEM_CANCELLED",
                "error_message": reason,
                "finished_at": now if runner_task.get("status") == "queued" else None,
                "updated_at": now,
            }
        )
    aggregate_ids = {work_item_id, *task_ids}
    if attempt is not None:
        aggregate_ids.add(str(attempt["id"]))
    for outbox in _records(store, "execution_outbox_events").values():
        if outbox.get("aggregate_id") in aggregate_ids and outbox.get("status") in {
            "pending",
            "failed",
        }:
            outbox.update({"status": "cancelled", "lease_owner": None, "lease_until": None})
    outbox_id = f"outbox:work-item:{work_item_id}:cancel"
    _records(store, "execution_outbox_events").setdefault(
        outbox_id,
        {
            "id": outbox_id,
            "aggregate_type": "rd_work_item",
            "aggregate_id": work_item_id,
            "event_type": "rd.work_item.cancel_runner",
            "idempotency_key": f"work-item:{work_item_id}:cancel",
            "payload_json": {
                "attempt_id": attempt.get("id") if attempt else None,
                "ai_task_ids": task_ids,
                "reason": reason,
                "runner_task_ids": runner_task_ids,
            },
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        },
    )


def complete_attempt(
    store: Any,
    *,
    work_item_id: str,
    attempt_id: str,
    lease_token: str,
    version: int,
    output: dict[str, Any],
    evidence: dict[str, Any],
    idempotency_key: str,
) -> dict[str, Any]:
    """Submit a leased attempt and deterministically route it to review."""
    # A leased worker must be able to return an already-started result while
    # the cutover fence drains.  It cannot claim or start further work there.
    from app.services.rd_maintenance_fence import require_rd_write_allowed

    require_rd_write_allowed(
        store,
        operation="work_item.inflight_completion",
        allow_inflight_completion=True,
    )
    request = {
        "attempt_id": attempt_id,
        "lease_token_hash": hashlib.sha256(lease_token.encode()).hexdigest(),
        "version": version,
        "output": output,
        "evidence": evidence,
    }
    command_id = _command_key(
        command_type="submit_work_item", aggregate_id=work_item_id, idempotency_key=idempotency_key
    )
    commands = _records(store, "rd_command_idempotency_records")
    existing = commands.get(command_id)
    if existing is not None:
        if existing.get("request_hash") != _canonical_hash(request):
            raise api_error(409, "RD_IDEMPOTENCY_CONFLICT", "Submission key has another payload")
        return {**deepcopy(existing["response_snapshot"]), "idempotent_replay": True}
    repository = _repository(store)
    if repository is not None:
        return _complete_attempt_repository(
            store,
            repository=repository,
            work_item_id=work_item_id,
            attempt_id=attempt_id,
            lease_token=lease_token,
            version=version,
            output=output,
            evidence=evidence,
            idempotency_key=idempotency_key,
            request=request,
        )
    item = _records(store, "rd_work_items").get(work_item_id)
    if item is None or item.get("status") != "running" or int(item.get("version") or 1) != version:
        raise api_error(
            409, "RD_VERSION_CONFLICT", "Work item is not running at the requested version"
        )
    attempt = _active_attempt(store, work_item_id=work_item_id, attempt_id=attempt_id)
    if (
        attempt.get("status") != "running"
        or attempt.get("lease_token_hash") != request["lease_token_hash"]
    ):
        raise api_error(409, "RD_WORK_ITEM_LEASE_EXPIRED", "Attempt lease is invalid")
    lease_expires_at = _parse_time(item.get("lease_expires_at"))
    if lease_expires_at is None or lease_expires_at <= _now():
        raise api_error(409, "RD_WORK_ITEM_LEASE_EXPIRED", "Attempt lease has expired")
    attempt.update(
        {
            "status": "completed",
            "result_json": {"output": deepcopy(output), "evidence": deepcopy(evidence)},
            "completed_at": _now().isoformat(),
        }
    )
    item.update(
        {
            "status": "reviewing",
            "lease_owner": None,
            "lease_expires_at": None,
            "version": int(item.get("version") or 1) + 1,
        }
    )
    run = _records(store, "rd_collaboration_runs").get(str(item["collaboration_run_id"]))
    response = {
        "work_item": deepcopy(item),
        "attempt": deepcopy(attempt),
        "run": deepcopy(run) if run else None,
        "next_state": "reviewing",
        "idempotent_replay": False,
    }
    commands[command_id] = {
        "id": command_id,
        "command_type": "submit_work_item",
        "aggregate_id": work_item_id,
        "idempotency_key": idempotency_key,
        "request_hash": _canonical_hash(request),
        "response_hash": _canonical_hash(response),
        "response_snapshot": deepcopy(response),
    }
    return response


def _complete_attempt_repository(
    store: Any,
    *,
    repository: Any,
    work_item_id: str,
    attempt_id: str,
    lease_token: str,
    version: int,
    output: dict[str, Any],
    evidence: dict[str, Any],
    idempotency_key: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    get_item = getattr(repository, "get_rd_work_item", None)
    get_attempt = getattr(repository, "get_rd_work_item_attempt", None)
    get_run = getattr(repository, "get_rd_collaboration_run", None)
    execute = getattr(repository, "execute_idempotent_rd_command", None)
    if not all(callable(method) for method in (get_item, get_attempt, get_run, execute)):
        raise api_error(503, "REPOSITORY_REQUIRED", "Work item command repository is unavailable")
    item = get_item(work_item_id)
    attempt = get_attempt(attempt_id)
    if item is None or attempt is None or attempt.get("work_item_id") != work_item_id:
        raise api_error(404, "NOT_FOUND", "Work item attempt not found")
    if attempt.get("lease_token_hash") != request["lease_token_hash"]:
        raise api_error(409, "RD_WORK_ITEM_LEASE_EXPIRED", "Attempt lease is invalid")

    def operation(transaction: Any) -> dict[str, Any]:
        persisted = transaction.save_work_item_attempt_bundle(
            work_item_id=work_item_id,
            expected_statuses=["running"],
            next_status="reviewing",
            expected_version=version,
            attempt={
                **attempt,
                "status": "completed",
                "result_json": {"output": output, "evidence": evidence},
                "completed_at": _now(),
            },
        )
        run = get_run(str(persisted["work_item"]["collaboration_run_id"]))
        response = {
            "work_item": persisted["work_item"],
            "attempt": persisted["attempt"],
            "run": run,
            "next_state": "reviewing",
        }
        return {
            "result_type": "rd_work_item_attempt",
            "result_id": attempt_id,
            "http_status": 200,
            "response_json": response,
        }

    result = execute(
        command_type="submit_work_item",
        aggregate_type="rd_work_item",
        aggregate_id=work_item_id,
        idempotency_key=idempotency_key,
        request_hash=_canonical_hash(request),
        operation=operation,
    )
    return {**dict(result["response_json"]), "idempotent_replay": bool(result["idempotent_replay"])}


def review_work_item(
    store: Any,
    *,
    work_item_id: str,
    decision: str,
    comment: str | None,
    actor: dict[str, Any],
    version: int,
    idempotency_key: str,
) -> dict[str, Any]:
    """Apply the fixed approve/rework/reject review mapping."""
    from app.services.rd_maintenance_fence import require_rd_write_allowed

    if decision not in {"approve", "request_rework", "reject"}:
        raise api_error(422, "VALIDATION_ERROR", "Review decision is invalid")
    if decision == "request_rework" and not str(comment or "").strip():
        raise api_error(422, "VALIDATION_ERROR", "Rework decision requires a comment")
    # Approval/rejection finish an existing review.  Rework creates another
    # executable unit, so it remains blocked until the fence is released.
    require_rd_write_allowed(
        store,
        operation="work_item.review",
        allow_inflight_completion=decision in {"approve", "reject"},
    )
    request = {
        "decision": decision,
        "comment": comment,
        "version": version,
        "actor_id": actor.get("id"),
    }
    command_id = _command_key(
        command_type="review_work_item", aggregate_id=work_item_id, idempotency_key=idempotency_key
    )
    commands = _records(store, "rd_command_idempotency_records")
    existing = commands.get(command_id)
    if existing is not None:
        if existing.get("request_hash") != _canonical_hash(request):
            raise api_error(409, "RD_IDEMPOTENCY_CONFLICT", "Review key has another payload")
        return {**deepcopy(existing["response_snapshot"]), "idempotent_replay": True}
    repository = _repository(store)
    if repository is not None:
        return _review_work_item_repository(
            store,
            repository,
            work_item_id=work_item_id,
            decision=decision,
            comment=comment,
            actor=actor,
            version=version,
            idempotency_key=idempotency_key,
            request=request,
        )
    item = _records(store, "rd_work_items").get(work_item_id)
    if (
        item is None
        or item.get("status") != "reviewing"
        or int(item.get("version") or 1) != version
    ):
        raise api_error(
            409, "RD_VERSION_CONFLICT", "Work item is not awaiting review at this version"
        )
    reviewer = _records(store, "rd_run_seats").get(str(item.get("reviewer_seat_id")))
    owner = _records(store, "rd_run_seats").get(str(item.get("owner_seat_id")))
    if (
        reviewer is None
        or owner is None
        or reviewer["id"] == owner["id"]
        or not _actor_matches_seat(actor, reviewer)
    ):
        raise api_error(
            403, "FORBIDDEN", "Reviewer must match the independent frozen reviewer seat"
        )
    attempts = [
        candidate
        for candidate in _records(store, "rd_work_item_attempts").values()
        if candidate.get("work_item_id") == work_item_id
    ]
    attempt = max(
        attempts, key=lambda candidate: int(candidate.get("attempt_no") or 0), default=None
    )
    status_map = {"approve": "completed", "request_rework": "ready", "reject": "failed"}
    item.update({"status": status_map[decision], "version": int(item.get("version") or 1) + 1})
    if decision == "approve":
        ready_successors = ready_work_items(
            store,
            collaboration_run_id=str(item["collaboration_run_id"]),
        )
        for successor in ready_successors:
            if successor.get("status") == "blocked":
                promoted = _records(store, "rd_work_items")[str(successor["id"])]
                promoted.update(
                    {
                        "status": "ready",
                        "version": int(promoted.get("version") or 1) + 1,
                    }
                )
        advance_delivery_phase_after_work_item_completion(
            store,
            collaboration_run_id=str(item["collaboration_run_id"]),
        )
    review = {
        "id": _new_id(store, "rd_work_item_review"),
        "decision": decision,
        "comment": comment,
        "reviewer_seat_id": reviewer["id"],
        "version": 1,
    }
    if attempt is not None and decision == "request_rework":
        attempt["rework_evidence"] = [{"comment": comment, "review_id": review["id"]}]
    event = {
        "id": _new_id(store, "rd_collaboration_event"),
        "collaboration_run_id": item["collaboration_run_id"],
        "event_type": "work_item.reviewed",
        "event_key": f"review:{work_item_id}:{idempotency_key}",
        "subject_type": "rd_work_item",
        "subject_id": work_item_id,
        "payload_json": {"decision": decision, "comment": comment},
    }
    _records(store, "rd_collaboration_events")[event["id"]] = event
    feedback = record_role_feedback(
        store,
        collaboration_run_id=item["collaboration_run_id"],
        work_item_id=work_item_id,
        source_event_id=event["id"],
        outcome=f"review_{decision}",
        producer={
            "subject_type": reviewer["subject_type"],
            "subject_id": reviewer.get("human_user_id")
            if reviewer["subject_type"] == "human_user"
            else reviewer.get("ai_employee_id"),
            "role_code": reviewer["role_code"],
            "seat_id": reviewer["id"],
        },
        executor_profile_id=attempt.get("executor_profile_id") if attempt else None,
        actor_id=str(actor["id"]),
        attempt_id=attempt.get("id") if attempt else None,
    )
    response = {
        "work_item": deepcopy(item),
        "attempt": deepcopy(attempt) if attempt else None,
        "review": review,
        "feedback": feedback,
        "next_state": "rework_required" if decision == "request_rework" else status_map[decision],
        "idempotent_replay": False,
    }
    commands[command_id] = {
        "id": command_id,
        "command_type": "review_work_item",
        "aggregate_id": work_item_id,
        "idempotency_key": idempotency_key,
        "request_hash": _canonical_hash(request),
        "response_hash": _canonical_hash(response),
        "response_snapshot": deepcopy(response),
    }
    return response


def _review_work_item_repository(
    store: Any,
    repository: Any,
    *,
    work_item_id: str,
    decision: str,
    comment: str | None,
    actor: dict[str, Any],
    version: int,
    idempotency_key: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    get_item = getattr(repository, "get_rd_work_item", None)
    get_seat = getattr(repository, "get_rd_run_seat", None)
    get_run = getattr(repository, "get_rd_collaboration_run", None)
    list_attempts = getattr(repository, "list_rd_work_item_attempts", None)
    execute = getattr(repository, "execute_idempotent_rd_command", None)
    if not all(
        callable(method) for method in (get_item, get_seat, get_run, list_attempts, execute)
    ):
        raise api_error(503, "REPOSITORY_REQUIRED", "Review command repository is unavailable")
    item = get_item(work_item_id)
    if item is None:
        raise api_error(404, "NOT_FOUND", "Work item not found")
    reviewer = get_seat(str(item.get("reviewer_seat_id") or ""))
    owner = get_seat(str(item.get("owner_seat_id") or ""))
    if (
        reviewer is None
        or owner is None
        or reviewer["id"] == owner["id"]
        or not _actor_matches_seat(actor, reviewer)
    ):
        raise api_error(
            403, "FORBIDDEN", "Reviewer must match the independent frozen reviewer seat"
        )
    attempts = list_attempts(work_item_id)
    attempt = max(
        attempts, key=lambda candidate: int(candidate.get("attempt_no") or 0), default=None
    )
    if attempt is None:
        raise api_error(409, "RD_WORK_ITEM_STATE_INVALID", "Work item has no reviewable attempt")
    run = get_run(str(item["collaboration_run_id"]))
    if run is None:
        raise api_error(409, "RD_WORK_ITEM_STATE_INVALID", "Collaboration run is unavailable")
    next_status = {"approve": "completed", "request_rework": "ready", "reject": "failed"}[decision]

    def operation(transaction: Any) -> dict[str, Any]:
        persisted = transaction.save_work_item_attempt_bundle(
            work_item_id=work_item_id,
            expected_statuses=["reviewing"],
            next_status=next_status,
            expected_version=version,
            attempt={
                **attempt,
                "rework_evidence": [{"comment": comment}] if decision == "request_rework" else [],
            },
        )
        event = transaction.save_rd_collaboration_event_record(
            {
                "id": f"review-event:{work_item_id}:{idempotency_key}",
                "collaboration_run_id": item["collaboration_run_id"],
                "event_type": "work_item.reviewed",
                "event_key": f"review:{work_item_id}:{idempotency_key}",
                "subject_type": "rd_work_item",
                "subject_id": work_item_id,
                "payload_json": {"decision": decision, "comment": comment},
            }
        )
        producer_subject_type = reviewer["subject_type"]
        producer_subject_id = (
            reviewer.get("human_user_id")
            if producer_subject_type == "human_user"
            else reviewer.get("ai_employee_id")
        )
        feedback = transaction.save_role_feedback_once(
            {
                "id": f"review-feedback:{work_item_id}:{idempotency_key}",
                "brain_app_id": run["brain_app_id"],
                "product_id": run["product_id"],
                "collaboration_run_id": item["collaboration_run_id"],
                "feedback_kind": f"review_{decision}",
                "source_event_id": event["id"],
                "feedback_fingerprint": _canonical_hash(
                    {
                        "attempt_id": attempt["id"],
                        "attributed_role_code": reviewer["role_code"],
                        "attributed_seat_id": reviewer["id"],
                        "attributed_subject_id": producer_subject_id,
                        "attributed_subject_type": producer_subject_type,
                        "feedback_kind": f"review_{decision}",
                        "run_generation": int(run.get("run_generation") or 1),
                        "source_event_id": event["id"],
                        "strategy_snapshot_id": run["strategy_snapshot_id"],
                        "work_item_id": work_item_id,
                    }
                ),
                "role_code": reviewer["role_code"],
                "seat_id": reviewer["id"],
                "human_user_id": reviewer.get("human_user_id"),
                "ai_employee_id": reviewer.get("ai_employee_id"),
                "executor_profile_id": attempt.get("executor_profile_id"),
                "work_item_id": work_item_id,
                "attempt_id": attempt["id"],
                "strategy_snapshot_id": run["strategy_snapshot_id"],
                "evidence_refs": [],
                "producer_subject_type": producer_subject_type,
                "producer_subject_id": producer_subject_id,
                "producer_role_code": reviewer["role_code"],
                "producer_seat_id": reviewer["id"],
            }
        )
        response = {
            "work_item": persisted["work_item"],
            "attempt": persisted["attempt"],
            "review": {
                "decision": decision,
                "comment": comment,
                "reviewer_seat_id": reviewer["id"],
                "version": 1,
            },
            "feedback": feedback,
            "next_state": "rework_required" if decision == "request_rework" else next_status,
        }
        return {
            "result_type": "rd_work_item",
            "result_id": work_item_id,
            "http_status": 200,
            "response_json": response,
        }

    result = execute(
        command_type="review_work_item",
        aggregate_type="rd_work_item",
        aggregate_id=work_item_id,
        idempotency_key=idempotency_key,
        request_hash=_canonical_hash(request),
        operation=operation,
    )
    response = dict(result["response_json"])
    feedback = response.get("feedback")
    if isinstance(feedback, dict):
        generate_role_experience_candidate_from_feedback(store, feedback=feedback)
    return {**response, "idempotent_replay": bool(result["idempotent_replay"])}


def cancel_work_item(
    store: Any,
    *,
    work_item_id: str,
    reason: str,
    actor: dict[str, Any],
    version: int,
    idempotency_key: str,
    maintenance_drain_cancel: bool = False,
) -> dict[str, Any]:
    """Cancel low-risk work atomically, or pause high-risk work for a decision."""
    from app.services.rd_maintenance_fence import get_rd_maintenance_state, require_rd_write_allowed

    if maintenance_drain_cancel:
        fence_state = get_rd_maintenance_state(store)
        if fence_state["fence_mode"] != "draining":
            raise api_error(
                409,
                "RD_UPGRADE_STATE_INVALID",
                "Controlled drain cancellation requires a draining maintenance fence",
            )
    else:
        require_rd_write_allowed(store, operation="work_item.cancel")
    request = {
        "reason": reason,
        "version": version,
        "actor_id": actor.get("id"),
        "maintenance_drain_cancel": maintenance_drain_cancel,
    }
    command_id = _command_key(
        command_type="cancel_work_item", aggregate_id=work_item_id, idempotency_key=idempotency_key
    )
    commands = _records(store, "rd_command_idempotency_records")
    existing = commands.get(command_id)
    if existing is not None:
        if existing.get("request_hash") != _canonical_hash(request):
            raise api_error(409, "RD_IDEMPOTENCY_CONFLICT", "Cancellation key has another payload")
        return {**deepcopy(existing["response_snapshot"]), "idempotent_replay": True}
    repository = _repository(store)
    if repository is not None:
        return _cancel_work_item_repository(
            store,
            repository=repository,
            work_item_id=work_item_id,
            reason=reason,
            actor=actor,
            version=version,
            idempotency_key=idempotency_key,
            request=request,
        )
    item = _records(store, "rd_work_items").get(work_item_id)
    if item is None:
        raise api_error(404, "NOT_FOUND", "Work item not found")
    if item.get("status") in _TERMINAL_WORK_ITEM_STATES or int(item.get("version") or 1) != version:
        raise api_error(409, "RD_VERSION_CONFLICT", "Work item cannot be cancelled at this version")
    run = _records(store, "rd_collaboration_runs").get(str(item["collaboration_run_id"]))
    attempts = [
        value
        for value in _records(store, "rd_work_item_attempts").values()
        if value.get("work_item_id") == work_item_id
        and value.get("status") not in {"completed", "failed", "cancelled", "expired"}
    ]
    attempt = max(attempts, key=lambda value: int(value.get("attempt_no") or 0), default=None)
    high_risk = item.get("risk_level") in {"high", "critical"} or bool(item.get("required"))
    decision_request = None
    if high_risk:
        decision_request = {
            "id": _new_id(store, "decision_request"),
            "brain_app_id": (run or {}).get("brain_app_id", "rd_brain"),
            "product_id": (run or {}).get("product_id"),
            "subject_type": "rd_work_item",
            "subject_id": work_item_id,
            "decision_type": "cancel_work_item",
            "plan_version": int((run or {}).get("plan_version") or 0),
            "options_json": [
                {
                    "code": "approve_cancel",
                    "outcome": "approve",
                    "subject_transition": "cancelled",
                    "input_schema": {},
                },
                {
                    "code": "continue_with_new_attempt",
                    "outcome": "reject",
                    "subject_transition": "ready",
                    "input_schema": {},
                },
            ],
            "status": "pending",
            "expires_at": (_now() + timedelta(hours=24)).isoformat(),
            "version": 1,
            "created_by": actor["id"],
        }
        _records(store, "decision_requests")[decision_request["id"]] = decision_request
        if attempt is not None:
            attempt["status"] = "waiting_human"
        item.update(
            {
                "status": "waiting_human",
                "resume_state": "ready",
                "suspended_attempt_id": attempt.get("id") if attempt else None,
                "suspended_decision_request_id": decision_request["id"],
                "suspended_at": _now().isoformat(),
                "lease_owner": None,
                "lease_expires_at": None,
                "version": int(item.get("version") or 1) + 1,
            }
        )
        next_state = "waiting_human"
    else:
        if attempt is not None:
            attempt["status"] = "cancelled"
            attempt["completed_at"] = _now().isoformat()
        item.update(
            {
                "status": "cancelled",
                "lease_owner": None,
                "lease_expires_at": None,
                "version": int(item.get("version") or 1) + 1,
            }
        )
        next_state = "cancelled"
    _fence_linked_delivery_memory(store, attempt=attempt, item=item, reason=reason)
    event = {
        "id": _new_id(store, "rd_collaboration_event"),
        "collaboration_run_id": item["collaboration_run_id"],
        "event_type": "work_item.cancel_requested",
        "event_key": f"cancel:{work_item_id}:{idempotency_key}",
        "subject_type": "rd_work_item",
        "subject_id": work_item_id,
        "payload_json": {"reason": reason, "high_risk": high_risk},
    }
    _records(store, "rd_collaboration_events")[event["id"]] = event
    response = {
        "work_item": deepcopy(item),
        "attempt": deepcopy(attempt) if attempt else None,
        "decision_request": deepcopy(decision_request) if decision_request else None,
        "run": deepcopy(run) if run else None,
        "next_state": next_state,
        "idempotent_replay": False,
    }
    commands[command_id] = {
        "id": command_id,
        "command_type": "cancel_work_item",
        "aggregate_id": work_item_id,
        "idempotency_key": idempotency_key,
        "request_hash": _canonical_hash(request),
        "response_hash": _canonical_hash(response),
        "response_snapshot": deepcopy(response),
    }
    return response


def _cancel_work_item_repository(
    store: Any,
    *,
    repository: Any,
    work_item_id: str,
    reason: str,
    actor: dict[str, Any],
    version: int,
    idempotency_key: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    get_item = getattr(repository, "get_rd_work_item", None)
    get_run = getattr(repository, "get_rd_collaboration_run", None)
    execute = getattr(repository, "execute_idempotent_rd_command", None)
    if not all(callable(method) for method in (get_item, get_run, execute)):
        raise api_error(503, "REPOSITORY_REQUIRED", "Cancellation repository is unavailable")
    item = get_item(work_item_id)
    if item is None:
        raise api_error(404, "NOT_FOUND", "Work item not found")
    run = get_run(str(item["collaboration_run_id"]))
    high_risk = item.get("risk_level") in {"high", "critical"} or bool(item.get("required"))
    decision_request = None
    if high_risk:
        decision_request = {
            "id": _new_id(store, "decision_request"),
            "brain_app_id": run["brain_app_id"],
            "product_id": run["product_id"],
            "subject_type": "rd_work_item",
            "subject_id": work_item_id,
            "decision_type": "cancel_work_item",
            "plan_version": int(run.get("plan_version") or 0),
            "options_json": [
                {"code": "approve_cancel", "outcome": "approve", "input_schema": {}},
                {"code": "continue_with_new_attempt", "outcome": "reject", "input_schema": {}},
            ],
            "options_hash": _canonical_hash(["approve_cancel", "continue_with_new_attempt"]),
            "decision_actor_selector": {"role_codes": ["rd_owner"]},
            "answer_actor_selector": {},
            "answer_schema": {},
            "status": "pending",
            "expires_at": _now() + timedelta(hours=24),
            "timeout_policy": "escalate_keep_paused",
            "escalation_target_selector": {"role_codes": ["rd_owner"]},
            "escalation_level": 0,
            "version": 1,
            "created_by": actor["id"],
        }

    def operation(transaction: Any) -> dict[str, Any]:
        result = transaction.cancel_work_item_bundle(
            work_item_id=work_item_id,
            expected_version=version,
            high_risk=high_risk,
            decision_request=decision_request,
            event={
                "id": _new_id(store, "rd_collaboration_event"),
                "collaboration_run_id": item["collaboration_run_id"],
                "event_type": "work_item.cancel_requested",
                "event_key": f"cancel:{work_item_id}:{idempotency_key}",
                "subject_type": "rd_work_item",
                "subject_id": work_item_id,
                "payload_json": {"reason": reason},
            },
        )
        response = {
            **result,
            "run": get_run(str(item["collaboration_run_id"])),
            "next_state": "waiting_human" if high_risk else "cancelled",
        }
        return {
            "result_type": "rd_work_item",
            "result_id": work_item_id,
            "http_status": 202 if high_risk else 200,
            "response_json": response,
        }

    result = execute(
        command_type="cancel_work_item",
        aggregate_type="rd_work_item",
        aggregate_id=work_item_id,
        idempotency_key=idempotency_key,
        request_hash=_canonical_hash(request),
        operation=operation,
    )
    return {**dict(result["response_json"]), "idempotent_replay": bool(result["idempotent_replay"])}


def suspend_work_item(
    store: Any,
    *,
    work_item_id: str,
    decision_request_id: str,
    expected_version: int,
) -> dict[str, Any]:
    """Platform-only pause helper; callers cannot provide a recovery state."""
    item = _records(store, "rd_work_items").get(work_item_id)
    if item is None or int(item.get("version") or 1) != expected_version:
        raise api_error(409, "RD_VERSION_CONFLICT", "Work item version is stale")
    if item.get("status") not in {"ready", "claimed", "running", "reviewing"}:
        raise api_error(409, "RD_WORK_ITEM_STATE_INVALID", "Work item cannot be suspended")
    item.update(
        {
            "resume_state": item["status"],
            "status": "waiting_human",
            "suspended_decision_request_id": decision_request_id,
            "suspended_at": _now().isoformat(),
            "lease_owner": None,
            "lease_expires_at": None,
            "version": int(item.get("version") or 1) + 1,
        }
    )
    return deepcopy(item)


def resume_work_item(store: Any, *, work_item_id: str, decision_request_id: str) -> dict[str, Any]:
    item = _records(store, "rd_work_items").get(work_item_id)
    if (
        item is None
        or item.get("status") != "waiting_human"
        or item.get("suspended_decision_request_id") != decision_request_id
    ):
        raise api_error(409, "RD_DECISION_REQUIRED", "Work item is not paused by this decision")
    target = item.get("resume_state")
    if target not in {"ready", "claimed", "running", "reviewing"}:
        raise api_error(409, "RD_DECISION_REQUIRED", "Work item has no valid frozen resume state")
    item.update(
        {
            "status": target,
            "resume_state": None,
            "suspended_decision_request_id": None,
            "suspended_at": None,
            "version": int(item.get("version") or 1) + 1,
        }
    )
    return deepcopy(item)
