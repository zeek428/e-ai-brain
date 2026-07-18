from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.rd_policy_validation import (
    RD_POLICY_SCHEMA_VERSION,
    PolicyValidationError,
    unified_policy_from_record,
    validate_unified_policy_payload,
)


class PolicyResolutionError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


# The registry is deliberately public: assessment strengthening and version merge
# share these operators, and any absent/different field is a human-decision case.
STRATEGY_MERGE_OPERATOR_REGISTRY = {
    "delivery_target": "ready_for_release_dominates",
    "quality_gate_config.gates": "union",
    "quality_gate_config.human_points": "union",
    "quality_gate_config.reviewer_role_codes": "union",
    "quality_gate_config.max_risk": "minimum_risk",
    "git_config.allowlist": "intersection",
    "git_config.denylist": "union",
    "git_config.repository_trust_domains": "intersection",
    "git_config.tool_trust_domains": "intersection",
    "iteration_config.budget.base_run_cap": "minimum",
    "iteration_config.budget.per_requirement_allocations": "minimum_per_requirement",
    "autonomy_config.mode": "less_automation",
    "autonomy_config.timeout_seconds": "minimum",
    "autonomy_config.max_iterations": "minimum",
    "autonomy_config.max_duration_seconds": "minimum",
    "autonomy_config.token_budget": "minimum",
    "autonomy_config.cost_budget": "minimum",
    "team_config.required_role_codes": "union",
    "experience_reuse_config.enabled": "and",
    "experience_reuse_config.min_confidence": "maximum",
    "experience_reuse_config.max_items": "minimum",
    "experience_reuse_config.max_context_tokens": "minimum",
    "experience_reuse_config.max_age_days": "minimum",
    "experience_reuse_config.repository_trust_domains": "intersection",
    "experience_reuse_config.tool_trust_domains": "intersection",
    "experience_reuse_config.policy_compatibility": "strictest_compatibility",
    "experience_reuse_config.require_independent_reviewer": "or",
}


def _hash(payload: Any) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(serialized.encode()).hexdigest()}"


def _repository(store: Any) -> Any | None:
    return getattr(store, "repository", None)


def _new_id(store: Any, prefix: str) -> str:
    factory = getattr(store, "new_id", None)
    return factory(prefix) if callable(factory) else f"{prefix}_{_hash(prefix)[:12]}"


def _policy_payload(
    policy: dict[str, Any], *, role_bindings: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    embedded = unified_policy_from_record(policy, role_bindings=role_bindings)
    return embedded if embedded is not None else validate_unified_policy_payload(policy)


def _validate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    if any(
        not snapshot.get(field)
        for field in ("id", "policy_id", "policy_version", "created_by", "content_hash")
    ):
        raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", "snapshot identity is incomplete")
    payload = snapshot.get("payload_json")
    if not isinstance(payload, dict) or snapshot.get("schema_version") != RD_POLICY_SCHEMA_VERSION:
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "policy snapshot schema is invalid"
        )
    if snapshot.get("content_hash") != _hash(payload):
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "policy snapshot hash does not match"
        )
    kind = snapshot.get("snapshot_kind")
    policy_id = snapshot.get("policy_id")
    policy_version = snapshot.get("policy_version")
    context_key = snapshot.get("resolution_context_key")
    revision = snapshot.get("resolution_revision")
    if kind not in {"base", "assessment_resolved", "version_resolved"}:
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "policy snapshot kind is unsupported"
        )
    if kind == "base" and (
        snapshot.get("parent_snapshot_id") is not None
        or context_key != f"policy:{policy_id}:version:{policy_version}"
        or revision != 0
    ):
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "base snapshot identity is invalid"
        )
    if kind == "assessment_resolved" and (
        not snapshot.get("parent_snapshot_id")
        or not re.fullmatch(r"assessment:[^:]+", str(context_key or ""))
        or revision not in {1, 2}
    ):
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "assessment snapshot identity is invalid"
        )
    if kind == "version_resolved" and (
        not snapshot.get("parent_snapshot_id")
        or not re.fullmatch(r"version:[^:]+:scope:[0-9]+", str(context_key or ""))
        or revision != 1
    ):
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "version snapshot identity is invalid"
        )
    try:
        return validate_unified_policy_payload(payload)
    except PolicyValidationError as exc:
        raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", str(exc)) from exc


def validate_snapshot_chain(repository: Any, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Validate immutable snapshot content and every parent without reading policy rows."""
    payload = _validate_snapshot(snapshot)
    current = snapshot
    seen: set[str] = set()
    while current["snapshot_kind"] != "base":
        if current["id"] in seen:
            raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", "snapshot parent cycle")
        seen.add(current["id"])
        get_snapshot = getattr(repository, "get_rd_policy_snapshot", None)
        parent_id = current.get("parent_snapshot_id")
        parent = get_snapshot(parent_id) if callable(get_snapshot) else None
        if parent is None:
            raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", "snapshot parent is missing")
        _validate_snapshot(parent)
        if (
            parent["policy_id"] != current["policy_id"]
            or parent["policy_version"] != current["policy_version"]
        ):
            raise PolicyResolutionError(
                "RD_POLICY_SNAPSHOT_INVALID", "snapshot parent policy differs"
            )
        if current["snapshot_kind"] == "version_resolved" and parent["snapshot_kind"] != "base":
            raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", "version parent must be base")
        if current["snapshot_kind"] == "assessment_resolved":
            assessment_context = str(current["resolution_context_key"])
            revision = int(current["resolution_revision"])
            if revision == 1 and parent["snapshot_kind"] != "base":
                raise PolicyResolutionError(
                    "RD_POLICY_SNAPSHOT_INVALID", "assessment revision one must parent base"
                )
            if revision == 2 and (
                parent["snapshot_kind"] != "assessment_resolved"
                or parent.get("resolution_context_key") != assessment_context
                or parent.get("resolution_revision") != 1
            ):
                raise PolicyResolutionError(
                    "RD_POLICY_SNAPSHOT_INVALID",
                    "assessment revision two must parent its revision one",
                )
        current = parent
    return payload


def freeze_base_rd_policy_snapshot(
    store: Any,
    *,
    policy: dict[str, Any],
    role_bindings: list[dict[str, Any]] | None = None,
    schema_version: int = RD_POLICY_SCHEMA_VERSION,
) -> dict[str, Any]:
    payload = _policy_payload(policy, role_bindings=role_bindings)
    policy_id = str(policy.get("id") or "")
    policy_version = int(policy.get("policy_version") or 1)
    snapshot = {
        "id": _new_id(store, "rd_policy_snapshot"),
        "policy_id": policy_id,
        "policy_version": policy_version,
        "parent_snapshot_id": None,
        "snapshot_kind": "base",
        "resolution_context_key": f"policy:{policy_id}:version:{policy_version}",
        "resolution_revision": 0,
        "schema_version": schema_version,
        "content_hash": _hash(payload),
        "payload_json": payload,
        "created_by": policy.get("created_by") or "system",
    }
    repository = _repository(store)
    freeze = getattr(repository, "freeze_base_policy_snapshot", None)
    return freeze(snapshot) if callable(freeze) else snapshot


def derive_assessment_rd_policy_snapshot(
    store: Any,
    *,
    assessment_id: str,
    parent_snapshot_id: str,
    resolution_revision: int,
    tightened_payload: dict[str, Any],
    repository: Any | None = None,
) -> dict[str, Any]:
    if resolution_revision not in {1, 2}:
        raise PolicyResolutionError(
            "RD_POLICY_RESOLUTION_LIMIT", "at most two strengthening rounds"
        )
    policy_repository = repository or _repository(store)
    get_snapshot = getattr(policy_repository, "get_rd_policy_snapshot", None)
    parent = get_snapshot(parent_snapshot_id) if callable(get_snapshot) else None
    if parent is None:
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "assessment parent snapshot is missing"
        )
    _validate_snapshot(parent)
    expected_context = f"assessment:{assessment_id}"
    if resolution_revision == 1 and parent.get("snapshot_kind") != "base":
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "assessment revision one must parent base"
        )
    if resolution_revision == 2 and (
        parent.get("snapshot_kind") != "assessment_resolved"
        or parent.get("resolution_context_key") != expected_context
        or parent.get("resolution_revision") != 1
    ):
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "assessment revision two must parent its revision one"
        )
    base_payload = validate_snapshot_chain(policy_repository, parent)
    candidate = validate_unified_policy_payload(tightened_payload)
    if candidate == base_payload:
        return parent
    if not is_monotonic_strengthening(base_payload, candidate):
        raise PolicyResolutionError(
            "RD_POLICY_HUMAN_DECISION_REQUIRED",
            "assessment policy is not a monotonic strengthening",
        )
    snapshot = {
        "id": _new_id(store, "rd_policy_snapshot"),
        "policy_id": parent["policy_id"],
        "policy_version": parent["policy_version"],
        "parent_snapshot_id": parent_snapshot_id,
        "snapshot_kind": "assessment_resolved",
        "resolution_context_key": f"assessment:{assessment_id}",
        "resolution_revision": resolution_revision,
        "schema_version": parent["schema_version"],
        "content_hash": _hash(candidate),
        "payload_json": candidate,
        "created_by": parent.get("created_by") or "system",
    }
    derive = getattr(policy_repository, "derive_assessment_policy_snapshot", None)
    return (
        derive(base_snapshot_id=parent_snapshot_id, snapshot=snapshot)
        if callable(derive)
        else snapshot
    )


def merge_version_rd_policy_snapshot(
    store: Any,
    *,
    version_id: str,
    scope_version: int,
    source_snapshot_ids: list[str] | None = None,
    source_provenance: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    repository = _repository(store)
    get_snapshot = getattr(repository, "get_rd_policy_snapshot", None)
    if not callable(get_snapshot) or not (source_snapshot_ids or source_provenance):
        raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", "version sources are required")
    provenance = source_provenance or [
        {"final_snapshot_id": snapshot_id} for snapshot_id in (source_snapshot_ids or [])
    ]
    sources = [get_snapshot(item.get("final_snapshot_id")) for item in provenance]
    if any(source is None for source in sources):
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "version source snapshot is missing"
        )
    typed_sources = [source for source in sources if source is not None]
    policy_ids = {source["policy_id"] for source in typed_sources}
    policy_versions = {source["policy_version"] for source in typed_sources}
    if len(policy_ids) != 1 or len(policy_versions) != 1:
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "sources must share one policy version"
        )
    base_parents = [_base_snapshot_for_source(source, get_snapshot) for source in typed_sources]
    if len({parent["id"] for parent in base_parents}) != 1:
        raise PolicyResolutionError(
            "RD_VERSION_POLICY_MERGE_REQUIRED",
            "sources do not share one base policy snapshot",
        )
    try:
        payload = merge_policy_payloads(
            [validate_snapshot_chain(repository, source) for source in typed_sources]
        )
    except PolicyResolutionError as exc:
        decision = _persist_merge_decision_request(
            store,
            version_id=version_id,
            scope_version=scope_version,
            sources=typed_sources,
            reason=str(exc),
        )
        raise PolicyResolutionError(
            exc.code,
            str(exc),
            details={"decision_request_id": decision.get("id")} if decision else {},
        ) from exc
    first = typed_sources[0]
    snapshot = {
        "id": _new_id(store, "rd_policy_snapshot"),
        "policy_id": first["policy_id"],
        "policy_version": first["policy_version"],
        "parent_snapshot_id": base_parents[0]["id"],
        "snapshot_kind": "version_resolved",
        "resolution_context_key": f"version:{version_id}:scope:{scope_version}",
        "resolution_revision": 1,
        "schema_version": first["schema_version"],
        "content_hash": _hash(payload),
        "payload_json": payload,
        "created_by": first.get("created_by") or "system",
    }
    get_assessment = getattr(repository, "get_requirement_assessment", None)
    list_by_final = getattr(repository, "list_requirement_assessments_for_final_snapshot", None)
    sources_payload = [
        _source_edge_for_snapshot(
            store,
            source=source,
            get_assessment=get_assessment,
            list_by_final=list_by_final,
            provenance=item,
        )
        for source, item in zip(typed_sources, provenance, strict=True)
    ]
    if len({source["requirement_id"] for source in sources_payload}) != len(sources_payload):
        raise PolicyResolutionError(
            "RD_VERSION_POLICY_MERGE_REQUIRED", "each requirement may appear only once"
        )
    merge = getattr(repository, "merge_version_policy_snapshot_with_sources", None)
    return merge(snapshot=snapshot, sources=sources_payload) if callable(merge) else snapshot


def _persist_merge_decision_request(
    store: Any,
    *,
    version_id: str,
    scope_version: int,
    sources: list[dict[str, Any]],
    reason: str,
) -> dict[str, Any] | None:
    """Persist the only allowed resolution choices; never invent a merged payload."""
    repository = _repository(store)
    save = getattr(repository, "save_decision_request_record", None)
    payload = sources[0].get("payload_json") if sources else {}
    product_id = str((payload or {}).get("product_id") or "").strip()
    if not callable(save) or not product_id:
        return None
    now = datetime.now(UTC)
    options = [
        {"code": "split_requirements", "label": "Split requirements"},
        {"code": "remove_requirement", "label": "Remove requirement"},
        {"code": "reassess_with_updated_policy", "label": "Update policy and reassess"},
        {"code": "cancel_start", "label": "Cancel start"},
    ]
    record = {
        "id": _new_id(store, "rd_policy_merge_decision"),
        "brain_app_id": str((payload or {}).get("brain_app_id") or "rd_brain"),
        "product_id": product_id,
        "subject_type": "product_version_policy_merge",
        "subject_id": version_id,
        "decision_type": "policy_merge",
        "plan_version": scope_version,
        "options_json": options,
        "options_hash": _hash(options),
        "evidence_json": [{"reason": reason, "source_snapshot_ids": [s["id"] for s in sources]}],
        "recommendation_json": {"action": "reassess_with_updated_policy"},
        "decision_actor_selector": {"role_codes": ["rd_owner"]},
        "answer_actor_selector": {"role_codes": ["rd_owner"]},
        "answer_schema": {"type": "object", "additionalProperties": False},
        "status": "pending",
        "expires_at": now + timedelta(hours=24),
        "timeout_policy": "escalate_keep_paused",
        "escalation_target_selector": {"role_codes": ["rd_owner"]},
        "version": 1,
        "created_by": sources[0].get("created_by") or "system",
    }
    return save(record)


def _base_snapshot_for_source(source: dict[str, Any], get_snapshot: Any) -> dict[str, Any]:
    _validate_snapshot(source)
    current = source
    seen: set[str] = set()
    while current["snapshot_kind"] != "base":
        if current["id"] in seen:
            raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", "snapshot parent cycle")
        seen.add(current["id"])
        parent = get_snapshot(current.get("parent_snapshot_id")) if callable(get_snapshot) else None
        if parent is None:
            raise PolicyResolutionError(
                "RD_POLICY_SNAPSHOT_INVALID", "source base parent is invalid"
            )
        _validate_snapshot(parent)
        if (
            parent["policy_id"] != source["policy_id"]
            or parent["policy_version"] != source["policy_version"]
        ):
            raise PolicyResolutionError(
                "RD_POLICY_SNAPSHOT_INVALID", "source parent policy differs"
            )
        current = parent
    return current


def _source_edge_for_snapshot(
    store: Any,
    *,
    source: dict[str, Any],
    get_assessment: Any,
    list_by_final: Any,
    provenance: dict[str, str],
) -> dict[str, Any]:
    context_key = str(source.get("resolution_context_key") or "")
    requested_assessment_id = str(provenance.get("assessment_id") or "")
    requested_requirement_id = str(provenance.get("requirement_id") or "")
    if source.get("snapshot_kind") == "assessment_resolved" and context_key.startswith(
        "assessment:"
    ):
        assessment_id = context_key.removeprefix("assessment:")
        if requested_assessment_id and requested_assessment_id != assessment_id:
            raise PolicyResolutionError("RD_VERSION_POLICY_MERGE_REQUIRED", "assessment differs")
        assessment = get_assessment(assessment_id) if callable(get_assessment) else None
    elif source.get("snapshot_kind") == "base" and callable(list_by_final):
        assessments = list_by_final(source["id"])
        assessment = next(
            (item for item in assessments if item.get("id") == requested_assessment_id), None
        )
        if assessment is None:
            raise PolicyResolutionError(
                "RD_VERSION_POLICY_MERGE_REQUIRED",
                "base source requires explicit assessment provenance",
            )
        assessment_id = str(assessment["id"])
    else:
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID",
            "version source is missing assessment provenance",
        )
    requirement_id = str((assessment or {}).get("requirement_id") or "").strip()
    if requested_requirement_id and requested_requirement_id != requirement_id:
        raise PolicyResolutionError("RD_VERSION_POLICY_MERGE_REQUIRED", "requirement differs")
    if not requirement_id:
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID",
            "version source assessment is missing its requirement provenance",
        )
    return {
        "id": _new_id(store, "rd_policy_snapshot_source"),
        "source_snapshot_id": source["id"],
        "requirement_id": requirement_id,
        "assessment_id": assessment_id,
    }


def resolve_initial_rd_policy(store: Any, *, requirement: dict[str, Any]) -> dict[str, Any]:
    repository = _repository(store)
    list_policies = getattr(repository, "list_rd_collaboration_task_executor_policies", None)
    if not callable(list_policies):
        raise PolicyResolutionError(
            "RD_EXECUTION_POLICY_NOT_FOUND", "policy repository is unavailable"
        )
    product_id = requirement.get("product_id")
    brain_app_id = requirement.get("brain_app_id") or "rd_brain"
    candidates = list_policies(brain_app_id=brain_app_id, product_id=product_id, status="active")
    if not candidates and product_id:
        list_default = getattr(
            repository, "list_rd_collaboration_default_task_executor_policies", None
        )
        candidates = list_default(brain_app_id=brain_app_id) if callable(list_default) else []
    if not candidates:
        raise PolicyResolutionError("RD_EXECUTION_POLICY_REQUIRED", "an active policy is required")
    if len(candidates) != 1:
        raise PolicyResolutionError("RD_EXECUTION_POLICY_INVALID", "multiple active policies match")
    bindings = getattr(repository, "list_rd_policy_role_bindings", lambda _id: [])(
        candidates[0]["id"]
    )
    return freeze_base_rd_policy_snapshot(
        store,
        policy=candidates[0],
        role_bindings=bindings,
    )


def resolve_final_rd_policy(
    store: Any,
    *,
    requirement: dict[str, Any],
    assessment: dict[str, Any],
    repository: Any | None = None,
) -> dict[str, Any]:
    # A second strengthening round extends the first frozen assessment result,
    # never jumps back to the base snapshot.
    base_id = assessment.get("final_strategy_snapshot_id") or assessment.get(
        "initial_strategy_snapshot_id"
    )
    if not base_id:
        return resolve_initial_rd_policy(store, requirement=requirement)
    delta = assessment.get("tightened_policy") or assessment.get("policy_delta")
    if not delta:
        policy_repository = repository or _repository(store)
        get_snapshot = getattr(policy_repository, "get_rd_policy_snapshot", None)
        base = get_snapshot(base_id) if callable(get_snapshot) else None
        if base is None:
            raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", "base snapshot is missing")
        validate_snapshot_chain(policy_repository, base)
        return base
    policy_repository = repository or _repository(store)
    get_snapshot = getattr(policy_repository, "get_rd_policy_snapshot", None)
    base = get_snapshot(base_id) if callable(get_snapshot) else None
    if base is None:
        raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", "base snapshot is missing")
    payload = {**validate_snapshot_chain(policy_repository, base), **delta}
    return derive_assessment_rd_policy_snapshot(
        store,
        assessment_id=str(assessment["id"]),
        parent_snapshot_id=base_id,
        resolution_revision=int(assessment.get("resolution_revision") or 1),
        tightened_payload=payload,
        repository=repository,
    )


def resolve_work_item_binding(
    policy_snapshot: dict[str, Any],
    *,
    role_code: str,
    task_type: str,
) -> dict[str, Any]:
    payload = _validate_snapshot(policy_snapshot)
    task_types = payload["matching_config"].get("task_types", [])
    if task_types and task_type not in task_types:
        raise PolicyResolutionError(
            "RD_POLICY_ROLE_BINDING_INVALID", "task type is outside policy scope"
        )
    bindings = [
        binding
        for binding in payload["role_bindings"]
        if binding.get("role_code") == role_code and binding.get("status") == "active"
    ]
    if len(bindings) != 1 or bindings[0].get("fallback_executor_profile_ids"):
        raise PolicyResolutionError(
            "RD_POLICY_ROLE_BINDING_INVALID",
            "exactly one active role binding without fallback is required",
        )
    return deepcopy(bindings[0])


def _risk_rank(value: Any) -> int:
    return {"none": 0, "low": 1, "medium": 2, "high": 3}.get(str(value), 99)


def is_monotonic_strengthening(base: dict[str, Any], candidate: dict[str, Any]) -> bool:
    try:
        merged = merge_policy_payloads([base, candidate])
    except PolicyResolutionError:
        return False
    return merged == candidate


def merge_policy_payloads(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    if not payloads:
        raise PolicyResolutionError(
            "RD_VERSION_POLICY_MERGE_REQUIRED", "at least one policy is required"
        )
    result = deepcopy(payloads[0])
    for candidate in payloads[1:]:
        result = _merge_pair(result, candidate)
    return result


def _merge_pair(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    allowed_top = {
        "delivery_target",
        "quality_gate_config",
        "experience_reuse_config",
        "git_config",
        "autonomy_config",
        "team_config",
        "assessment_config",
        "iteration_config",
        "matching_config",
        "deployment_config",
        "role_bindings",
        "name",
        "brain_app_id",
        "product_id",
        "status",
    }
    if set(left) - allowed_top or set(right) - allowed_top:
        raise PolicyResolutionError("RD_VERSION_POLICY_MERGE_REQUIRED", "undeclared policy field")
    merged: dict[str, Any] = {}
    for key in sorted(set(left) | set(right)):
        a, b = left.get(key), right.get(key)
        if a == b or a is None:
            merged[key] = deepcopy(b)
        elif b is None:
            merged[key] = deepcopy(a)
        elif key == "delivery_target":
            values = {a, b}
            if not values <= {"deployed", "ready_for_release"}:
                raise PolicyResolutionError(
                    "RD_VERSION_POLICY_MERGE_REQUIRED", "delivery target is invalid"
                )
            merged[key] = "ready_for_release" if "ready_for_release" in values else "deployed"
        elif key == "quality_gate_config":
            merged[key] = _merge_config(
                a,
                b,
                path="quality_gate_config",
            )
        elif key == "git_config":
            merged[key] = _merge_config(
                a,
                b,
                path="git_config",
            )
        elif key == "experience_reuse_config":
            merged[key] = _merge_experience(a, b)
        elif key == "autonomy_config":
            merged[key] = _merge_autonomy(a, b)
        elif key == "team_config":
            merged[key] = _merge_config(a, b, path="team_config")
        elif key == "role_bindings":
            merged[key] = _union_value(a, b)
        elif key == "iteration_config":
            merged[key] = _merge_iteration(a, b)
        else:
            raise PolicyResolutionError(
                "RD_VERSION_POLICY_MERGE_REQUIRED", f"{key} is incomparable"
            )
    return merged


def _merge_config(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    path: str,
) -> dict[str, Any]:
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise PolicyResolutionError(
            "RD_VERSION_POLICY_MERGE_REQUIRED", "configuration must be objects"
        )
    merged: dict[str, Any] = {}
    for key in set(left) | set(right):
        field_path = f"{path}.{key}"
        operator = STRATEGY_MERGE_OPERATOR_REGISTRY.get(field_path)
        left_missing, right_missing = key not in left, key not in right
        if left_missing or right_missing:
            if operator is None:
                raise PolicyResolutionError(
                    "RD_VERSION_POLICY_MERGE_REQUIRED", f"{field_path} is incomparable"
                )
            default = _merge_default(operator, field_path)
            if default is _NO_DEFAULT:
                raise PolicyResolutionError(
                    "RD_VERSION_POLICY_MERGE_REQUIRED", f"{field_path} is incomparable"
                )
            a = deepcopy(default) if left_missing else left[key]
            b = deepcopy(default) if right_missing else right[key]
        else:
            a, b = left[key], right[key]
        if a == b:
            merged[key] = deepcopy(a)
        else:
            if operator is None:
                raise PolicyResolutionError(
                    "RD_VERSION_POLICY_MERGE_REQUIRED", f"{field_path} is incomparable"
                )
            if operator == "intersection" and isinstance(a, list) and isinstance(b, list):
                merged[key] = sorted(set(a) & set(b))
            elif operator == "union" and isinstance(a, list) and isinstance(b, list):
                merged[key] = sorted(set(a) | set(b))
            elif operator == "minimum_risk":
                merged[key] = a if _risk_rank(a) <= _risk_rank(b) else b
            elif (
                operator == "minimum"
                and isinstance(a, (int, float))
                and isinstance(b, (int, float))
            ):
                merged[key] = min(a, b)
            elif (
                operator == "maximum"
                and isinstance(a, (int, float))
                and isinstance(b, (int, float))
            ):
                merged[key] = max(a, b)
            elif operator == "and":
                merged[key] = bool(a) and bool(b)
            elif operator == "or":
                merged[key] = bool(a) or bool(b)
            elif operator == "strictest_compatibility":
                order = {"any": 0, "same_policy_schema": 1, "same_policy_version": 2}
                if str(a) not in order or str(b) not in order:
                    raise PolicyResolutionError(
                        "RD_VERSION_POLICY_MERGE_REQUIRED", "policy compatibility is invalid"
                    )
                merged[key] = max((str(a), str(b)), key=order.__getitem__)
            else:
                raise PolicyResolutionError(
                    "RD_VERSION_POLICY_MERGE_REQUIRED", f"{path}.{key} is incomparable"
                )
    return merged


_NO_DEFAULT = object()


def _merge_default(operator: str, field_path: str) -> Any:
    if field_path == "experience_reuse_config.policy_compatibility":
        return "same_policy_version"
    if operator in {"union", "intersection"}:
        return []
    if operator == "and":
        return True
    if operator == "or":
        return False
    return _NO_DEFAULT


def _merge_experience(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return _merge_config(left, right, path="experience_reuse_config")


def _merge_autonomy(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = _merge_config(
        {key: value for key, value in left.items() if key != "mode"},
        {key: value for key, value in right.items() if key != "mode"},
        path="autonomy_config",
    )
    modes = {left.get("mode", "single_pass"), right.get("mode", "single_pass")}
    if not modes <= {"single_pass", "autonomous_loop"}:
        raise PolicyResolutionError("RD_VERSION_POLICY_MERGE_REQUIRED", "autonomy mode invalid")
    merged["mode"] = "single_pass" if "single_pass" in modes else "autonomous_loop"
    return merged


def _merge_iteration(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = _merge_config(
        {key: value for key, value in left.items() if key != "budget"},
        {key: value for key, value in right.items() if key != "budget"},
        path="iteration_config",
    )
    if "budget" not in left or "budget" not in right:
        return merged
    first, second = left["budget"], right["budget"]
    if not isinstance(first, dict) or not isinstance(second, dict):
        raise PolicyResolutionError("RD_VERSION_POLICY_MERGE_REQUIRED", "budget is invalid")
    base_cap = min(first.get("base_run_cap"), second.get("base_run_cap"))
    allocations = {
        key: min(
            first.get("per_requirement_allocations", {}).get(key, value),
            second.get("per_requirement_allocations", {}).get(key, value),
        )
        for key, value in {
            **first.get("per_requirement_allocations", {}),
            **second.get("per_requirement_allocations", {}),
        }.items()
    }
    merged["budget"] = {
        "base_run_cap": base_cap,
        "per_requirement_allocations": allocations,
    }
    return merged


def _union_value(left: Any, right: Any) -> Any:
    if isinstance(left, list) and isinstance(right, list):
        unique = {
            json.dumps(value, ensure_ascii=False, sort_keys=True): deepcopy(value)
            for value in left + right
        }
        return [unique[key] for key in sorted(unique)]
    if isinstance(left, dict) and isinstance(right, dict):
        if left == right:
            return deepcopy(left)
    raise PolicyResolutionError("RD_VERSION_POLICY_MERGE_REQUIRED", "values cannot be merged")
