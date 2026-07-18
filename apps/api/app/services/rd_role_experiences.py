"""Governed, read-only reuse of reviewed R&D role experience.

Experience is deliberately not a policy input.  It is evidence with a narrow
review lifecycle, and retrieval returns cited context only after the current
frozen policy has accepted every scope and trust-domain constraint.
"""

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from app.api.deps import api_error, require_permissions
from app.core.repositories.rd_collaboration import (
    RdCollaborationRepositoryError,
    RdCollaborationVersionConflictError,
)
from app.services.product_scope import (
    brain_app_scope_filter,
    product_scope_filter,
    require_brain_app_scope,
    require_product_scope,
    user_can_read_brain_app,
    user_can_read_product,
)

READ_PERMISSION = "delivery.rd_role_experiences.read"
DECIDE_PERMISSION = "delivery.rd_role_experiences.decide"
_STATUSES = {"pending", "approved", "rejected", "retired"}
_DECISIONS = {"approve", "reject", "retire"}


def role_experience_enabled() -> bool:
    """Read the independent P1 flag without changing P0 startup behavior."""
    return os.getenv("RD_ROLE_EXPERIENCE_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


def require_role_experience_enabled() -> None:
    if not role_experience_enabled():
        raise api_error(404, "RD_ROLE_EXPERIENCE_DISABLED", "Role experience is not enabled")


def _records(store: Any, name: str) -> dict[str, dict[str, Any]]:
    values = getattr(store, name, None)
    if not isinstance(values, dict):
        values = {}
        setattr(store, name, values)
    return values


def _repository(store: Any) -> Any | None:
    return getattr(store, "repository", None)


def _get(store: Any, collection: str, record_id: str, method: str) -> dict[str, Any] | None:
    repository = _repository(store)
    getter = getattr(repository, method, None)
    if callable(getter):
        row = getter(record_id)
        return dict(row) if row is not None else None
    value = _records(store, collection).get(record_id)
    return deepcopy(value) if value is not None else None


def _new_id(store: Any, prefix: str, content: Any | None = None) -> str:
    if content is not None:
        encoded = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return f"{prefix}_{hashlib.sha256(encoded.encode()).hexdigest()[:24]}"
    new_id = getattr(store, "new_id", None)
    return (
        str(new_id(prefix)) if callable(new_id) else f"{prefix}_{datetime.now(UTC).timestamp():.6f}"
    )


def _hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"


def _snapshot(store: Any, snapshot_id: str) -> dict[str, Any]:
    snapshot = _get(
        store, "rd_task_executor_policy_snapshots", snapshot_id, "get_rd_policy_snapshot"
    )
    if snapshot is None or not isinstance(snapshot.get("payload_json"), dict):
        raise api_error(
            409, "RD_POLICY_SNAPSHOT_INVALID", "Experience policy snapshot is unavailable"
        )
    return snapshot


def _reuse_config(snapshot: dict[str, Any]) -> dict[str, Any]:
    payload = snapshot.get("payload_json") or {}
    value = payload.get("experience_reuse_config") if isinstance(payload, dict) else None
    return deepcopy(value) if isinstance(value, dict) else {}


def _source_rows(store: Any, experience_id: str) -> list[dict[str, Any]]:
    repository = _repository(store)
    list_sources = getattr(repository, "list_rd_role_experience_sources", None)
    if callable(list_sources):
        return [dict(row) for row in list_sources(experience_id)]
    return sorted(
        [
            deepcopy(row)
            for row in _records(store, "rd_role_experience_sources").values()
            if row.get("experience_id") == experience_id
        ],
        key=lambda row: (str(row.get("role_feedback_record_id")), str(row.get("id"))),
    )


def _feedback(store: Any, feedback_id: str) -> dict[str, Any] | None:
    return _get(store, "role_feedback_records", feedback_id, "get_role_feedback_record")


def _candidate_public(
    store: Any, record: dict[str, Any], *, include_sources: bool = False
) -> dict[str, Any]:
    public = deepcopy(record)
    public.pop("reviewed_by", None)
    if include_sources:
        sources = _source_rows(store, str(record["id"]))
        public["sources"] = [
            {
                "feedback_record_id": source["role_feedback_record_id"],
                "strategy_snapshot_id": source["strategy_snapshot_id"],
            }
            for source in sources
        ]
    return public


def generate_role_experience_candidates(
    store: Any, *, candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Append candidates only from immutable feedback provenance.

    This is intentionally a service call, not an LLM side effect.  Any model
    may propose the structured candidate, but it cannot bypass the frozen
    feedback/source/snapshot validation in this function and the repository.
    """
    if not role_experience_enabled():
        return []
    saved: list[dict[str, Any]] = []
    for raw in candidates:
        source_ids = sorted({str(item) for item in raw.get("source_feedback_ids", []) if str(item)})
        if not source_ids:
            raise api_error(422, "RD_EXPERIENCE_INVALID", "Experience requires feedback sources")
        sources = [_feedback(store, source_id) for source_id in source_ids]
        if any(source is None for source in sources):
            raise api_error(
                422, "RD_EXPERIENCE_INVALID", "Experience feedback source is unavailable"
            )
        typed_sources = [source for source in sources if source is not None]
        source_products = {str(source.get("product_id") or "") for source in typed_sources}
        source_roles = {str(source.get("role_code") or "") for source in typed_sources}
        source_brains = {str(source.get("brain_app_id") or "") for source in typed_sources}
        snapshot_id = str(raw.get("strategy_snapshot_id") or "")
        if (
            not snapshot_id
            or len(source_products) != 1
            or len(source_roles) != 1
            or len(source_brains) != 1
            or any(source.get("strategy_snapshot_id") != snapshot_id for source in typed_sources)
        ):
            raise api_error(
                422, "RD_EXPERIENCE_INVALID", "Experience source provenance is inconsistent"
            )
        product_scope = sorted({str(item) for item in raw.get("product_scope", []) if str(item)})
        if set(source_products) - set(product_scope):
            raise api_error(
                422, "RD_EXPERIENCE_INVALID", "Experience product scope must contain every source"
            )
        if str(raw.get("role_code") or "") != next(iter(source_roles)):
            raise api_error(422, "RD_EXPERIENCE_INVALID", "Experience role must match every source")
        if str(raw.get("brain_app_id") or "rd_brain") != next(iter(source_brains)):
            raise api_error(
                422, "RD_EXPERIENCE_INVALID", "Experience brain must match every source"
            )
        candidate = {
            key: deepcopy(value)
            for key, value in raw.items()
            if key
            not in {
                "source_feedback_ids",
                "version",
                "review_version",
                "status",
                "reviewed_by",
                "reviewed_at",
            }
        }
        candidate["id"] = str(candidate.get("id") or _new_id(store, "rd_role_experience", raw))
        candidate["brain_app_id"] = next(iter(source_brains))
        candidate["product_scope"] = product_scope
        candidate["status"] = "pending"
        candidate["review_version"] = 1
        candidate["created_at"] = datetime.now(UTC).isoformat()
        candidate["updated_at"] = candidate["created_at"]
        relational_sources = [
            {
                "id": _new_id(
                    store,
                    "rd_role_experience_source",
                    {"experience": candidate["id"], "feedback": source["id"]},
                ),
                "experience_id": candidate["id"],
                "role_feedback_record_id": source["id"],
                "strategy_snapshot_id": snapshot_id,
            }
            for source in typed_sources
        ]
        repository = _repository(store)
        save = getattr(repository, "save_rd_role_experience_record", None)
        if callable(save):
            try:
                saved.append(save(candidate, sources=relational_sources))
            except RdCollaborationRepositoryError as exc:
                raise api_error(409, exc.code, str(exc), exc.details) from exc
            continue
        values = _records(store, "rd_role_experience_records")
        existing = values.get(candidate["id"])
        if existing is not None:
            saved.append(deepcopy(existing))
            continue
        candidate["version"] = 1 + max(
            (
                int(item.get("version") or 0)
                for item in values.values()
                if item.get("experience_key") == candidate.get("experience_key")
            ),
            default=0,
        )
        values[candidate["id"]] = candidate
        for source in relational_sources:
            _records(store, "rd_role_experience_sources")[source["id"]] = source
        saved.append(deepcopy(candidate))
    return saved


def generate_role_experience_candidate_from_feedback(
    store: Any, *, feedback: dict[str, Any]
) -> list[dict[str, Any]]:
    """Project one persisted feedback fact into a pending governed candidate.

    This closes the production feedback-to-review loop without treating a
    candidate as an approved rule.  The feedback id is part of the immutable
    candidate identity, so worker replay is safe.
    """
    if not role_experience_enabled() or not feedback.get("strategy_snapshot_id"):
        return []
    role_code = str(feedback.get("role_code") or "").strip()
    product_id = str(feedback.get("product_id") or "").strip()
    if not role_code or role_code == "system" or not product_id:
        return []
    work_item_id = str(feedback.get("work_item_id") or "")
    work_item = (
        _get(store, "rd_work_items", work_item_id, "get_rd_work_item") if work_item_id else None
    )
    work_item = work_item or {}
    work_item_type = str(work_item.get("work_item_type") or "feedback").strip()
    scenario = str(
        work_item.get("scenario")
        or work_item.get("objective")
        or feedback.get("feedback_kind")
        or "feedback"
    ).strip()
    snapshot = _snapshot(store, str(feedback["strategy_snapshot_id"]))
    reuse = _reuse_config(snapshot)
    raw = {
        "brain_app_id": str(feedback.get("brain_app_id") or "rd_brain"),
        "content": {
            "kind": "feedback_candidate",
            "feedback_kind": str(feedback.get("feedback_kind") or "feedback"),
            "guidance": "Pending review: inspect cited feedback before reuse.",
        },
        "confidence": 0.5,
        "evidence_refs": deepcopy(feedback.get("evidence_refs") or []),
        "experience_key": f"{role_code}:{work_item_type}:{scenario}",
        "product_scope": [product_id],
        "repository_trust_domains": deepcopy(reuse.get("repository_trust_domains") or []),
        "risk_scope": {"maximum": str(work_item.get("risk_level") or "medium")},
        "role_code": role_code,
        "scenario": scenario,
        "source_feedback_ids": [str(feedback["id"])],
        "strategy_snapshot_id": str(feedback["strategy_snapshot_id"]),
        "tool_trust_domains": deepcopy(reuse.get("tool_trust_domains") or []),
        "work_item_type": work_item_type,
    }
    raw["id"] = _new_id(
        store,
        "rd_role_experience",
        {"feedback_id": feedback["id"], "snapshot_id": raw["strategy_snapshot_id"]},
    )
    return generate_role_experience_candidates(store, candidates=[raw])


def _require_candidate_scope(user: dict[str, Any], record: dict[str, Any]) -> None:
    require_brain_app_scope(
        user,
        record.get("brain_app_id"),
        code="FORBIDDEN",
        message="Experience is outside business brain scope",
        status_code=403,
    )
    for product_id in record.get("product_scope") or []:
        require_product_scope(
            user,
            product_id,
            code="FORBIDDEN",
            message="Experience is outside product scope",
            status_code=403,
        )


def _get_scoped_candidate(
    store: Any, *, experience_id: str, user: dict[str, Any]
) -> dict[str, Any] | None:
    repository = _repository(store)
    getter = getattr(repository, "get_rd_role_experience_record_scoped", None)
    if callable(getter):
        return getter(
            experience_id,
            product_scope_ids=product_scope_filter(user),
            brain_app_ids=brain_app_scope_filter(user),
        )
    record = _get(
        store,
        "rd_role_experience_records",
        experience_id,
        "get_rd_role_experience_record",
    )
    if record is not None:
        _require_candidate_scope(user, record)
    return record


def _require_decide_permission(user: dict[str, Any]) -> None:
    require_permissions(user, {DECIDE_PERMISSION})


def _reviewer_identity(
    store: Any, *, user: dict[str, Any], experience_id: str
) -> tuple[list[str], list[str]]:
    """Resolve review separation from authenticated roles and frozen seats.

    Request bodies never carry these values.  A user may hold several role
    codes, so any overlap with a feedback producer rejects the review.
    """
    role_codes = {
        str(value).strip()
        for value in [*(user.get("rd_role_codes") or []), *(user.get("roles") or [])]
        if str(value).strip()
    }
    source_runs: set[str] = set()
    for source in _source_rows(store, experience_id):
        feedback = _feedback(store, str(source.get("role_feedback_record_id") or ""))
        if feedback and feedback.get("collaboration_run_id"):
            source_runs.add(str(feedback["collaboration_run_id"]))
    repository = _repository(store)
    list_seats = getattr(repository, "list_rd_run_seats", None)
    seats: list[dict[str, Any]] = []
    for run_id in sorted(source_runs):
        if callable(list_seats):
            seats.extend(dict(item) for item in list_seats(run_id))
        else:
            seats.extend(
                item
                for item in _records(store, "rd_run_seats").values()
                if item.get("collaboration_run_id") == run_id
            )
    reviewer_seat_ids = {
        str(seat["id"])
        for seat in seats
        if seat.get("subject_type") == "human_user" and seat.get("human_user_id") == user.get("id")
    }
    role_codes.update(
        str(seat.get("role_code"))
        for seat in seats
        if str(seat.get("id")) in reviewer_seat_ids and seat.get("role_code")
    )
    return sorted(role_codes), sorted(reviewer_seat_ids)


def decide_role_experience(
    store: Any,
    *,
    experience_id: str,
    decision: str,
    comment: str | None,
    expected_version: int,
    idempotency_key: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    from app.services.rd_maintenance_fence import require_rd_write_allowed

    require_rd_write_allowed(store, operation="rd_role_experience.decide")
    require_role_experience_enabled()
    _require_decide_permission(user)
    if decision not in _DECISIONS or not idempotency_key.strip():
        raise api_error(422, "RD_EXPERIENCE_INVALID", "Experience decision is invalid")
    record = _get_scoped_candidate(store, experience_id=experience_id, user=user)
    if record is None:
        raise api_error(404, "NOT_FOUND", "Role experience not found")
    _require_candidate_scope(user, record)
    snapshot = _snapshot(store, str(record["strategy_snapshot_id"]))
    independent = bool(_reuse_config(snapshot).get("require_independent_reviewer"))
    reviewer_role_codes, reviewer_seat_ids = _reviewer_identity(
        store, user=user, experience_id=experience_id
    )
    request_hash = _hash(
        {
            "decision": decision,
            "comment": comment,
            "expected_version": expected_version,
            "reviewer": user["id"],
            "reviewer_role_codes": reviewer_role_codes,
            "reviewer_seat_ids": reviewer_seat_ids,
        }
    )
    event_status = {"approve": "approved", "reject": "rejected", "retire": "retired"}[decision]
    audit_event = {
        "id": _new_id(
            store, "audit_event", {"experience": experience_id, "idempotency_key": idempotency_key}
        ),
        "event_type": f"rd_role_experience.{event_status}",
        "actor_id": str(user["id"]),
        "subject_type": "rd_role_experience",
        "subject_id": experience_id,
        "payload": {
            "comment": comment,
            "idempotency_key": idempotency_key,
            "expected_version": expected_version,
        },
        "created_at": datetime.now(UTC).isoformat(),
    }
    repository = _repository(store)
    command = getattr(repository, "decide_role_experience_command", None)
    try:
        if callable(command):
            return command(
                experience_id=experience_id,
                decision=decision,
                comment=comment,
                expected_review_version=expected_version,
                reviewer_subject_id=str(user["id"]),
                reviewer_role_code=None,
                reviewer_seat_id=None,
                reviewer_role_codes=reviewer_role_codes,
                reviewer_seat_ids=reviewer_seat_ids,
                require_independent_reviewer=independent,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                audit_event=audit_event,
            )
    except RdCollaborationVersionConflictError as exc:
        raise api_error(409, exc.code, str(exc), exc.details) from exc
    except RdCollaborationRepositoryError as exc:
        raise api_error(
            409 if exc.code != "PERMISSION_DENIED" else 403, exc.code, str(exc), exc.details
        ) from exc
    decisions = _records(store, "rd_role_experience_decisions")
    existing = next(
        (
            item
            for item in decisions.values()
            if item["experience_id"] == experience_id and item["idempotency_key"] == idempotency_key
        ),
        None,
    )
    if existing is not None:
        if existing["request_hash"] != request_hash:
            raise api_error(
                409, "RD_IDEMPOTENCY_CONFLICT", "Experience decision idempotency key conflicts"
            )
        return deepcopy(existing["response_json"])
    if int(record.get("review_version") or 1) != expected_version:
        raise api_error(
            409,
            "RD_VERSION_CONFLICT",
            "R&D collaboration record version conflict",
            {"current_version": record.get("review_version")},
        )
    transitions = {
        "approve": ("pending", "approved"),
        "reject": ("pending", "rejected"),
        "retire": ("approved", "retired"),
    }
    expected_status, next_status = transitions[decision]
    if record.get("status") != expected_status:
        raise api_error(
            409,
            "RD_EXPERIENCE_STATE_INVALID",
            "Experience decision is not valid for current status",
        )
    for source in _source_rows(store, experience_id):
        feedback = _feedback(store, str(source["role_feedback_record_id"]))
        if feedback is None:
            raise api_error(409, "RD_EXPERIENCE_INVALID", "Experience source is unavailable")
        if (
            feedback.get("producer_subject_type") == "human_user"
            and feedback.get("producer_subject_id") == user["id"]
        ):
            raise api_error(
                403, "PERMISSION_DENIED", "Feedback producer cannot review its derived experience"
            )
        if independent and (
            (feedback.get("producer_role_code") in reviewer_role_codes)
            or (feedback.get("producer_seat_id") in reviewer_seat_ids)
        ):
            raise api_error(
                403,
                "PERMISSION_DENIED",
                "Feedback producer role or seat cannot review its derived experience",
            )
    persisted = {
        **record,
        "status": next_status,
        "reviewed_by": user["id"],
        "reviewed_at": datetime.now(UTC).isoformat(),
        "review_version": expected_version + 1,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _records(store, "rd_role_experience_records")[experience_id] = persisted
    decisions[_new_id(store, "rd_role_experience_decision")] = {
        "experience_id": experience_id,
        "idempotency_key": idempotency_key,
        "request_hash": request_hash,
        "response_json": deepcopy(persisted),
        "comment": comment,
    }
    audit_events = getattr(store, "audit_events", None)
    if isinstance(audit_events, list):
        audit_events.append(audit_event)
    return deepcopy(persisted)


def _matches_scope(record: dict[str, Any], filters: dict[str, Any]) -> bool:
    for field in ("brain_app_id", "role_code", "work_item_type", "scenario", "status"):
        if filters.get(field) is not None and record.get(field) != filters[field]:
            return False
    if filters.get("product_id") and filters["product_id"] not in set(
        record.get("product_scope") or []
    ):
        return False
    if (
        filters.get("risk_level")
        and record.get("risk_scope", {}).get("maximum") != filters["risk_level"]
    ):
        return False
    if filters.get("repository_trust_domain") and filters["repository_trust_domain"] not in set(
        record.get("repository_trust_domains") or []
    ):
        return False
    if filters.get("tool_trust_domain") and filters["tool_trust_domain"] not in set(
        record.get("tool_trust_domains") or []
    ):
        return False
    return float(record.get("confidence") or 0) >= float(filters.get("minimum_confidence") or 0)


def list_role_experiences_response(
    *, current_store: Any, user: dict[str, Any], filters: dict[str, Any], page: int, page_size: int
) -> dict[str, Any]:
    require_role_experience_enabled()
    require_permissions(user, {READ_PERMISSION})
    if filters.get("status") is not None and filters["status"] not in _STATUSES:
        raise api_error(422, "VALIDATION_ERROR", "Unsupported experience status")
    repository = _repository(current_store)
    list_page = getattr(repository, "list_rd_role_experience_records_page", None)
    if callable(list_page):
        rows, total = list_page(
            filters=filters,
            product_scope_ids=product_scope_filter(user),
            brain_app_ids=brain_app_scope_filter(user),
            page=page,
            page_size=page_size,
        )
        return {
            "items": [_candidate_public(current_store, row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
        }
    rows = [
        row
        for row in _records(current_store, "rd_role_experience_records").values()
        if _matches_scope(row, filters)
        and user_can_read_brain_app(user, row.get("brain_app_id"))
        and all(
            user_can_read_product(user, product_id) for product_id in row.get("product_scope") or []
        )
    ]
    evidence_subject = filters.get("evidence_subject_id")
    if evidence_subject:
        rows = [
            row
            for row in rows
            if any(
                (_feedback(current_store, str(source["role_feedback_record_id"])) or {}).get(
                    "producer_subject_id"
                )
                == evidence_subject
                for source in _source_rows(current_store, str(row["id"]))
            )
        ]
    rows.sort(key=lambda item: (-float(item.get("confidence") or 0), str(item.get("id"))))
    start = (page - 1) * page_size
    return {
        "items": [_candidate_public(current_store, row) for row in rows[start : start + page_size]],
        "page": page,
        "page_size": page_size,
        "total": len(rows),
    }


def get_role_experience_response(
    *, current_store: Any, user: dict[str, Any], experience_id: str
) -> dict[str, Any]:
    require_role_experience_enabled()
    require_permissions(user, {READ_PERMISSION})
    record = _get_scoped_candidate(current_store, experience_id=experience_id, user=user)
    if record is None:
        raise api_error(404, "NOT_FOUND", "Role experience not found")
    _require_candidate_scope(user, record)
    return _candidate_public(current_store, record, include_sources=True)


def retrieve_approved_role_experiences(
    store: Any, *, current_policy_snapshot_id: str, scope: dict[str, Any], user: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return deterministic cited context; callers must never treat it as policy."""
    if not role_experience_enabled():
        return []
    current = _snapshot(store, current_policy_snapshot_id)
    config = _reuse_config(current)
    if not config.get("enabled"):
        return []
    repository_domains = set(config.get("repository_trust_domains") or [])
    tool_domains = set(config.get("tool_trust_domains") or [])
    if not repository_domains or not tool_domains:
        return []
    if (
        scope.get("repository_trust_domain") not in repository_domains
        or scope.get("tool_trust_domain") not in tool_domains
    ):
        return []
    filters = {**scope, "status": "approved", "minimum_confidence": config.get("min_confidence", 1)}
    records = list_role_experiences_response(
        current_store=store,
        user=user,
        filters=filters,
        page=1,
        page_size=max(1, int(config.get("max_items", 1)) * 4),
    )["items"]
    max_age = datetime.now(UTC) - timedelta(days=max(0, int(config.get("max_age_days", 0))))
    compatibility = str(config.get("policy_compatibility") or "same_policy_version")
    chosen: list[dict[str, Any]] = []
    used_tokens = 0
    for record in records:
        created_at = record.get("created_at")
        try:
            created = (
                datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                if created_at
                else datetime.now(UTC)
            )
        except ValueError:
            continue
        if (
            created < max_age
            or not set(record.get("repository_trust_domains") or []).issubset(repository_domains)
            or not set(record.get("tool_trust_domains") or []).issubset(tool_domains)
        ):
            continue
        source_snapshot = _snapshot(store, str(record["strategy_snapshot_id"]))
        same_policy = source_snapshot.get("policy_id") == current.get(
            "policy_id"
        ) and source_snapshot.get("policy_version") == current.get("policy_version")
        same_schema = (
            source_snapshot.get("schema_version") == current.get("schema_version")
            and record.get("brain_app_id") == scope.get("brain_app_id")
            and scope.get("product_id") in set(record.get("product_scope") or [])
        )
        if (compatibility == "same_policy_version" and not same_policy) or (
            compatibility == "same_policy_schema" and not same_schema
        ):
            continue
        text = json.dumps(record.get("content") or {}, ensure_ascii=False, sort_keys=True)
        token_cost = max(1, (len(text) + 3) // 4)
        if len(chosen) >= int(config.get("max_items", 1)) or used_tokens + token_cost > int(
            config.get("max_context_tokens", 0)
        ):
            continue
        chosen.append(
            {
                "experience_id": record["id"],
                "version": record["version"],
                "content": deepcopy(record["content"]),
                "evidence_refs": deepcopy(record.get("evidence_refs") or []),
            }
        )
        used_tokens += token_cost
    return chosen
