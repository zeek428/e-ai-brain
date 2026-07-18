"""Frozen decision-request handling for collaboration runs and work items."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error


def _records(store: Any, name: str) -> dict[str, dict[str, Any]]:
    records = getattr(store, name, None)
    if not isinstance(records, dict):
        records = {}
        setattr(store, name, records)
    return records


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _new_id(store: Any, prefix: str) -> str:
    factory = getattr(store, "new_id", None)
    if callable(factory):
        return str(factory(prefix))
    return f"{prefix}_{hashlib.sha256(str(_now()).encode()).hexdigest()[:16]}"


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"


def _decision_command_key(decision_id: str, operation: str, idempotency_key: str) -> str:
    return f"{operation}:{decision_id}:{idempotency_key}"


def _actor_seat_ids(
    store: Any,
    actor: dict[str, Any],
    *,
    collaboration_run_id: str | None = None,
) -> set[str]:
    actor_id = str(actor.get("id") or "")
    repository = getattr(store, "repository", None)
    list_seats = getattr(repository, "list_rd_run_seats", None)
    if collaboration_run_id and callable(list_seats):
        return {
            str(seat["id"])
            for seat in list_seats(collaboration_run_id)
            if seat.get("status", "active") == "active"
            and (
                str(seat.get("human_user_id") or "") == actor_id
                or str(seat.get("ai_employee_id") or "") == actor_id
            )
        }
    return {
        str(seat["id"])
        for seat in _records(store, "rd_run_seats").values()
        if seat.get("status", "active") == "active"
        and (
            str(seat.get("human_user_id") or "") == actor_id
            or str(seat.get("ai_employee_id") or "") == actor_id
        )
    }


def _decision_collaboration_run_id(store: Any, decision: dict[str, Any]) -> str | None:
    subject_type = str(decision.get("subject_type") or "")
    subject_id = str(decision.get("subject_id") or "")
    if subject_type == "rd_collaboration_run":
        return subject_id or None
    if subject_type != "rd_work_item":
        return None
    repository = getattr(store, "repository", None)
    get_work_item = getattr(repository, "get_rd_work_item", None)
    work_item = (
        get_work_item(subject_id)
        if callable(get_work_item)
        else _records(store, "rd_work_items").get(subject_id)
    )
    return str(work_item.get("collaboration_run_id") or "") if work_item else None


def _matches_selector(store: Any, actor: dict[str, Any], selector: Any) -> bool:
    if not isinstance(selector, dict) or not selector:
        return True
    actor_id = str(actor.get("id") or "")
    roles = {str(role) for role in actor.get("roles") or []}
    seats = _actor_seat_ids(store, actor)
    return bool(
        actor_id in {str(value) for value in selector.get("user_ids", [])}
        or roles.intersection(str(value) for value in selector.get("role_codes", []))
        or seats.intersection(str(value) for value in selector.get("seat_ids", []))
    )


def _matches_schema_type(value: Any, schema_type: str) -> bool:
    checks = {
        "array": lambda item: isinstance(item, list),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "null": lambda item: item is None,
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "object": lambda item: isinstance(item, dict),
        "string": lambda item: isinstance(item, str),
    }
    return bool(checks.get(schema_type, lambda _item: False)(value))


def _validate_input(value: Any, schema: Any, *, field: str) -> None:
    effective = schema if isinstance(schema, dict) else {}
    if not effective:
        if value not in (None, {}):
            raise api_error(
                422,
                "RD_DECISION_INPUT_INVALID",
                f"{field} is not allowed for the selected option",
                {"field": field},
            )
        return
    schema_type = effective.get("type")
    if schema_type and not _matches_schema_type(value, str(schema_type)):
        raise api_error(
            422,
            "RD_DECISION_INPUT_INVALID",
            f"{field} does not match the frozen schema type",
            {"field": field, "expected_type": schema_type},
        )
    if "enum" in effective and value not in effective["enum"]:
        raise api_error(422, "RD_DECISION_INPUT_INVALID", f"{field} is not an allowed value")
    if isinstance(value, dict):
        properties = effective.get("properties") or {}
        missing = [key for key in effective.get("required", []) if key not in value]
        additional = [key for key in value if key not in properties]
        if missing or (effective.get("additionalProperties") is False and additional):
            raise api_error(
                422,
                "RD_DECISION_INPUT_INVALID",
                f"{field} does not match frozen required fields",
                {"field": field, "missing": missing, "additional": additional},
            )
        for key, child in value.items():
            if key in properties:
                _validate_input(child, properties[key], field=f"{field}.{key}")
    if isinstance(value, list) and isinstance(effective.get("items"), dict):
        for index, child in enumerate(value):
            _validate_input(child, effective["items"], field=f"{field}[{index}]")


def _decision(store: Any, decision_request_id: str) -> dict[str, Any]:
    repository = getattr(store, "repository", None)
    get_decision = getattr(repository, "get_decision_request", None)
    loaded = get_decision(decision_request_id) if callable(get_decision) else None
    decision = loaded or _records(store, "decision_requests").get(decision_request_id)
    if decision is None:
        raise api_error(404, "NOT_FOUND", "Decision request not found")
    return decision


def _subject(store: Any, decision: dict[str, Any]) -> tuple[dict[str, Any], str]:
    subject_type = str(decision.get("subject_type") or "")
    subject_id = str(decision.get("subject_id") or "")
    collection = {
        "rd_collaboration_run": "rd_collaboration_runs",
        "rd_work_item": "rd_work_items",
    }.get(subject_type)
    if collection is None:
        raise api_error(409, "RD_DECISION_REQUIRED", "Decision has an unsupported subject")
    subject = _records(store, collection).get(subject_id)
    if subject is None:
        raise api_error(409, "RD_DECISION_REQUIRED", "Decision subject is no longer available")
    return subject, subject_type


def _check_active_decision(decision: dict[str, Any], *, version: int) -> None:
    if int(decision.get("version") or 1) != version:
        raise api_error(
            409,
            "RD_VERSION_CONFLICT",
            "Decision request version is stale",
            {"current_version": decision.get("version"), "retryable": False},
        )
    expires_at = _parse_time(decision.get("expires_at"))
    if decision.get("status") not in {"pending", "waiting_more_info"} or (
        expires_at is not None and expires_at <= _now()
    ):
        raise api_error(
            409,
            "RD_DECISION_EXPIRED",
            "Decision request is no longer active",
            {"retryable": False, "next_action": "wait_for_escalation"},
        )


def _idempotent_replay(
    store: Any,
    *,
    decision_id: str,
    operation: str,
    idempotency_key: str,
    request: dict[str, Any],
) -> dict[str, Any] | None:
    commands = _records(store, "rd_command_idempotency_records")
    key = _decision_command_key(decision_id, operation, idempotency_key)
    command = commands.get(key)
    if command is None:
        return None
    request_hash = _canonical_hash(request)
    if command.get("request_hash") != request_hash:
        raise api_error(409, "RD_IDEMPOTENCY_CONFLICT", "Idempotency key has another request")
    return {**deepcopy(command["response_snapshot"]), "idempotent_replay": True}


def _save_command(
    store: Any,
    *,
    decision_id: str,
    operation: str,
    idempotency_key: str,
    request: dict[str, Any],
    response: dict[str, Any],
) -> None:
    key = _decision_command_key(decision_id, operation, idempotency_key)
    _records(store, "rd_command_idempotency_records")[key] = {
        "id": key,
        "command_type": operation,
        "aggregate_id": decision_id,
        "idempotency_key": idempotency_key,
        "request_hash": _canonical_hash(request),
        "response_hash": _canonical_hash(response),
        "response_snapshot": deepcopy(response),
    }


def apply_decision(
    store: Any,
    *,
    decision_request_id: str,
    selected_option: str,
    input_value: Any,
    comment: str | None,
    actor: dict[str, Any],
    version: int,
    idempotency_key: str,
) -> dict[str, Any]:
    """Apply a frozen option; callers cannot supply a target state."""
    request = {
        "selected_option": selected_option,
        "input": input_value,
        "comment": comment,
        "version": version,
        "actor_id": actor.get("id"),
    }
    replay = _idempotent_replay(
        store,
        decision_id=decision_request_id,
        operation="decide",
        idempotency_key=idempotency_key,
        request=request,
    )
    if replay is not None:
        return replay
    repository = getattr(store, "repository", None)
    if repository is not None:
        return _apply_decision_repository(
            store,
            repository=repository,
            decision_request_id=decision_request_id,
            selected_option=selected_option,
            input_value=input_value,
            comment=comment,
            actor=actor,
            version=version,
            idempotency_key=idempotency_key,
            request=request,
        )
    decision = _decision(store, decision_request_id)
    _check_active_decision(decision, version=version)
    if not _matches_selector(store, actor, decision.get("decision_actor_selector")):
        raise api_error(403, "FORBIDDEN", "Actor does not match the frozen decision selector")
    subject, subject_type = _subject(store, decision)
    if subject.get("suspended_decision_request_id") != decision_request_id:
        raise api_error(409, "RD_DECISION_REQUIRED", "Decision is no longer bound to the subject")
    option = next(
        (
            item
            for item in decision.get("options_json") or []
            if item.get("code") == selected_option
        ),
        None,
    )
    if option is None:
        raise api_error(422, "RD_DECISION_INPUT_INVALID", "Selected option is not frozen")
    _validate_input(input_value, option.get("input_schema"), field="input")
    if option.get("requires_comment") and not str(comment or "").strip():
        raise api_error(422, "RD_DECISION_INPUT_INVALID", "Selected option requires a comment")
    outcome = str(option.get("outcome") or "")
    if outcome not in {"approve", "reject", "request_more_info"}:
        raise api_error(422, "RD_DECISION_INPUT_INVALID", "Frozen option has an invalid outcome")
    next_state = (
        "waiting_more_info"
        if outcome == "request_more_info"
        else str(option.get("subject_transition") or "resume")
    )
    decision.update(
        {
            "status": "waiting_more_info"
            if outcome == "request_more_info"
            else "approved"
            if outcome == "approve"
            else "rejected",
            "selected_option_code": selected_option,
            "answer_json": {"input": deepcopy(input_value), "comment": comment},
            "decided_by": actor.get("id"),
            "decided_at": None if outcome == "request_more_info" else _now().isoformat(),
            "version": int(decision.get("version") or 1) + 1,
        }
    )
    if outcome != "request_more_info":
        transition = str(option.get("subject_transition") or "resume")
        if transition in {"resume", "continue", "keep_paused"}:
            target = subject.get("resume_state")
        elif transition in {"ready", "completed", "failed", "cancelled"}:
            target = transition
        else:
            target = subject.get("resume_state")
        if not target:
            raise api_error(409, "RD_DECISION_REQUIRED", "Subject has no frozen resume state")
        subject.update(
            {
                "status": target,
                "resume_state": None,
                "suspended_decision_request_id": None,
                "suspended_at": None,
                "version": int(subject.get("version") or 1) + 1,
            }
        )
        next_state = str(target)
    response = {
        "decision_request": deepcopy(decision),
        "affected_subject": {"type": subject_type, "id": subject["id"]},
        "run": deepcopy(subject) if subject_type == "rd_collaboration_run" else None,
        "work_item": deepcopy(subject) if subject_type == "rd_work_item" else None,
        "next_state": next_state,
        "idempotent_replay": False,
    }
    _save_command(
        store,
        decision_id=decision_request_id,
        operation="decide",
        idempotency_key=idempotency_key,
        request=request,
        response=response,
    )
    return response


def _apply_decision_repository(
    store: Any,
    *,
    repository: Any,
    decision_request_id: str,
    selected_option: str,
    input_value: Any,
    comment: str | None,
    actor: dict[str, Any],
    version: int,
    idempotency_key: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    execute = getattr(repository, "execute_idempotent_rd_command", None)
    if not callable(execute):
        raise api_error(503, "REPOSITORY_REQUIRED", "Decision command repository is unavailable")

    def operation(transaction: Any) -> dict[str, Any]:
        result = transaction.apply_decision_bundle(
            decision_request_id=decision_request_id,
            selected_option_code=selected_option,
            input_json=input_value,
            comment=comment,
            decided_by=str(actor["id"]),
            actor_role_codes=[str(role) for role in actor.get("roles") or []],
            expected_version=version,
        )
        decision = result["decision_request"]
        response = {
            "decision_request": decision,
            "affected_subject": {
                "type": decision["subject_type"],
                "id": decision["subject_id"],
            },
            "run": result.get("run"),
            "work_item": result.get("work_item"),
            "attempt": result.get("attempt"),
            "next_state": result.get("next_state"),
        }
        return {
            "result_type": "decision_request",
            "result_id": decision_request_id,
            "http_status": 200,
            "response_json": response,
        }

    result = execute(
        command_type="apply_decision",
        aggregate_type="decision_request",
        aggregate_id=decision_request_id,
        idempotency_key=idempotency_key,
        request_hash=_canonical_hash(request),
        operation=operation,
    )
    return {**dict(result["response_json"]), "idempotent_replay": bool(result["idempotent_replay"])}


def answer_decision_request(
    store: Any,
    *,
    decision_request_id: str,
    answer: Any,
    evidence: list[Any],
    actor: dict[str, Any],
    version: int,
    idempotency_key: str,
) -> dict[str, Any]:
    request = {
        "answer": answer,
        "evidence": evidence,
        "version": version,
        "actor_id": actor.get("id"),
    }
    replay = _idempotent_replay(
        store,
        decision_id=decision_request_id,
        operation="answer_decision",
        idempotency_key=idempotency_key,
        request=request,
    )
    if replay is not None:
        return replay
    repository = getattr(store, "repository", None)
    if repository is not None:
        return _answer_decision_repository(
            store,
            repository=repository,
            decision_request_id=decision_request_id,
            answer=answer,
            evidence=evidence,
            actor=actor,
            version=version,
            idempotency_key=idempotency_key,
            request=request,
        )
    decision = _decision(store, decision_request_id)
    _check_active_decision(decision, version=version)
    if decision.get("status") != "waiting_more_info":
        raise api_error(409, "RD_DECISION_REQUIRED", "Decision is not waiting for more information")
    if not _matches_selector(store, actor, decision.get("answer_actor_selector")):
        raise api_error(403, "FORBIDDEN", "Actor does not match the frozen answer selector")
    subject, subject_type = _subject(store, decision)
    if subject.get("suspended_decision_request_id") != decision_request_id:
        raise api_error(409, "RD_DECISION_REQUIRED", "Decision is no longer bound to the subject")
    _validate_input(answer, decision.get("answer_schema"), field="answer")
    decision.update(
        {
            "status": "pending",
            "answer_json": deepcopy(answer),
            "evidence_json": [*(decision.get("evidence_json") or []), *deepcopy(evidence)],
            "selected_option_code": None,
            "decided_by": None,
            "decided_at": None,
            "version": int(decision.get("version") or 1) + 1,
        }
    )
    response = {
        "decision_request": deepcopy(decision),
        "affected_subject": {"type": subject_type, "id": subject["id"]},
        "next_state": "pending",
        "idempotent_replay": False,
    }
    _save_command(
        store,
        decision_id=decision_request_id,
        operation="answer_decision",
        idempotency_key=idempotency_key,
        request=request,
        response=response,
    )
    return response


def _answer_decision_repository(
    store: Any,
    *,
    repository: Any,
    decision_request_id: str,
    answer: Any,
    evidence: list[Any],
    actor: dict[str, Any],
    version: int,
    idempotency_key: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    get_decision = getattr(repository, "get_decision_request", None)
    execute = getattr(repository, "execute_idempotent_rd_command", None)
    if not callable(get_decision) or not callable(execute):
        raise api_error(503, "REPOSITORY_REQUIRED", "Decision command repository is unavailable")
    current = get_decision(decision_request_id)
    if current is None:
        raise api_error(404, "NOT_FOUND", "Decision request not found")
    actor_seats = sorted(
        _actor_seat_ids(
            store,
            actor,
            collaboration_run_id=_decision_collaboration_run_id(store, current),
        )
    )

    def operation(transaction: Any) -> dict[str, Any]:
        decision = transaction.answer_decision_request(
            decision_request_id=decision_request_id,
            expected_version=version,
            actor_id=str(actor["id"]),
            actor_role_codes=[str(role) for role in actor.get("roles") or []],
            actor_seat_ids=actor_seats,
            answer_json=answer,
            evidence_json=evidence,
            options_json=current.get("options_json") or [],
            options_hash=str(current.get("options_hash") or _canonical_hash([])),
        )
        response = {
            "decision_request": decision,
            "affected_subject": {"type": decision["subject_type"], "id": decision["subject_id"]},
            "next_state": "pending",
        }
        return {
            "result_type": "decision_request",
            "result_id": decision_request_id,
            "http_status": 200,
            "response_json": response,
        }

    result = execute(
        command_type="answer_decision",
        aggregate_type="decision_request",
        aggregate_id=decision_request_id,
        idempotency_key=idempotency_key,
        request_hash=_canonical_hash(request),
        operation=operation,
    )
    return {**dict(result["response_json"]), "idempotent_replay": bool(result["idempotent_replay"])}


def expire_decision_requests(store: Any) -> dict[str, int]:
    """Expire due decisions; the worker escalates but never approves or resumes."""
    repository = getattr(store, "repository", None)
    if repository is not None:
        return _expire_decision_requests_repository(store, repository)
    expired_count = 0
    for decision in list(_records(store, "decision_requests").values()):
        expires_at = _parse_time(decision.get("expires_at"))
        if decision.get("status") not in {"pending", "waiting_more_info"} or (
            expires_at is None or expires_at > _now()
        ):
            continue
        subject, _subject_type = _subject(store, decision)
        if subject.get("suspended_decision_request_id") != decision["id"]:
            continue
        decision.update({"status": "expired", "expired_at": _now().isoformat()})
        escalation = decision.get("escalation_target_selector")
        if isinstance(escalation, dict) and escalation:
            successor_id = _new_id(store, "decision_request")
            successor = {
                **deepcopy(decision),
                "id": successor_id,
                "status": "pending",
                "selected_option_code": None,
                "decided_by": None,
                "decided_at": None,
                "expired_at": None,
                "supersedes_decision_request_id": decision["id"],
                "escalation_level": int(decision.get("escalation_level") or 0) + 1,
                "version": 1,
            }
            _records(store, "decision_requests")[successor_id] = successor
            subject["suspended_decision_request_id"] = successor_id
        expired_count += 1
    return {"expired_count": expired_count}


def _expire_decision_requests_repository(store: Any, repository: Any) -> dict[str, int]:
    """Repository scans use DB time inside the atomic expiry/escalation bundle."""
    _ = store
    list_due = getattr(repository, "list_due_decision_requests", None)
    expire = getattr(repository, "expire_and_escalate_decision_request", None)
    if not callable(list_due) or not callable(expire):
        return {"expired_count": 0}
    expired_count = 0
    for decision in list_due():
        successor_id = (
            f"decision-escalation-{decision['id']}-{int(decision.get('escalation_level') or 0) + 1}"
        )
        successor = {
            **decision,
            "id": successor_id,
            "status": "pending",
            "selected_option_code": None,
            "decided_by": None,
            "decided_at": None,
            "expired_at": None,
            "expiry_event_id": None,
            "supersedes_decision_request_id": decision["id"],
            "escalation_level": int(decision.get("escalation_level") or 0) + 1,
            "version": 1,
            "created_by": decision["created_by"],
        }
        event = {
            "id": f"decision-expiry-{decision['id']}",
            "collaboration_run_id": decision["subject_id"],
            "event_type": "decision.expired",
            "event_key": f"decision-expired:{decision['id']}",
            "subject_type": "decision_request",
            "subject_id": decision["id"],
            "payload_json": {},
        }
        if expire(
            decision_request_id=decision["id"], successor_request=successor, expiry_event=event
        ):
            expired_count += 1
    return {"expired_count": expired_count}


def suspend_collaboration_run(
    store: Any,
    *,
    collaboration_run_id: str,
    decision_request_id: str,
    expected_version: int,
) -> dict[str, Any]:
    """Persist the exact run phase that a human decision interrupted."""
    repository = getattr(store, "repository", None)
    suspend = getattr(repository, "suspend_collaboration_run", None)
    if callable(suspend):
        return suspend(
            collaboration_run_id=collaboration_run_id,
            decision_request_id=decision_request_id,
            expected_version=expected_version,
        )
    run = _records(store, "rd_collaboration_runs").get(collaboration_run_id)
    decision = _records(store, "decision_requests").get(decision_request_id)
    if run is None or decision is None or int(run.get("version") or 1) != expected_version:
        raise api_error(409, "RD_VERSION_CONFLICT", "Collaboration run version is stale")
    if run.get("status") not in {"running", "integrating", "verifying"}:
        raise api_error(409, "RD_WORK_ITEM_STATE_INVALID", "Collaboration run cannot be suspended")
    if (
        decision.get("subject_type") != "rd_collaboration_run"
        or decision.get("subject_id") != collaboration_run_id
        or decision.get("status") != "pending"
    ):
        raise api_error(
            409, "RD_DECISION_REQUIRED", "Decision is not bound to the collaboration run"
        )
    run.update(
        {
            "status": "waiting_human",
            "resume_state": run["status"],
            "suspended_decision_request_id": decision_request_id,
            "suspended_at": _now().isoformat(),
            "version": int(run.get("version") or 1) + 1,
        }
    )
    return deepcopy(run)


def resume_collaboration_run(
    store: Any,
    *,
    collaboration_run_id: str,
    decision_request_id: str,
) -> dict[str, Any]:
    """Internal-only recovery that restores the platform-frozen source phase."""
    run = _records(store, "rd_collaboration_runs").get(collaboration_run_id)
    if (
        run is None
        or run.get("status") != "waiting_human"
        or run.get("suspended_decision_request_id") != decision_request_id
    ):
        raise api_error(409, "RD_DECISION_REQUIRED", "Run is not paused by this decision")
    target = run.get("resume_state")
    if target not in {"running", "integrating", "verifying"}:
        raise api_error(409, "RD_DECISION_REQUIRED", "Run has no valid frozen resume state")
    run.update(
        {
            "status": target,
            "resume_state": None,
            "suspended_decision_request_id": None,
            "suspended_at": None,
            "version": int(run.get("version") or 1) + 1,
        }
    )
    return deepcopy(run)
