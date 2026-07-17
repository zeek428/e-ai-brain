from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from app.services.rd_policy_validation import (
    RD_POLICY_SCHEMA_VERSION,
    PolicyValidationError,
    unified_policy_from_record,
    validate_unified_policy_payload,
)


class PolicyResolutionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _hash(payload: Any) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(serialized.encode()).hexdigest()}"


def _repository(store: Any) -> Any | None:
    return getattr(store, "repository", None)


def _new_id(store: Any, prefix: str) -> str:
    factory = getattr(store, "new_id", None)
    return factory(prefix) if callable(factory) else f"{prefix}_{_hash(prefix)[:12]}"


def _policy_payload(policy: dict[str, Any]) -> dict[str, Any]:
    embedded = unified_policy_from_record(policy)
    return embedded if embedded is not None else validate_unified_policy_payload(policy)


def _validate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    payload = snapshot.get("payload_json")
    if (
        not isinstance(payload, dict)
        or int(snapshot.get("schema_version") or RD_POLICY_SCHEMA_VERSION)
        != RD_POLICY_SCHEMA_VERSION
    ):
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "policy snapshot schema is invalid"
        )
    if snapshot.get("content_hash") not in {None, "sha256:ignored", _hash(payload)}:
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
        or not str(context_key or "").startswith("assessment:")
        or revision not in {1, 2}
    ):
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "assessment snapshot identity is invalid"
        )
    if kind == "version_resolved" and (
        not snapshot.get("parent_snapshot_id")
        or not str(context_key or "").startswith("version:")
        or revision != 1
    ):
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "version snapshot identity is invalid"
        )
    try:
        return validate_unified_policy_payload(payload)
    except PolicyValidationError as exc:
        raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", str(exc)) from exc


def freeze_base_rd_policy_snapshot(
    store: Any,
    *,
    policy: dict[str, Any],
    role_bindings: list[dict[str, Any]] | None = None,
    schema_version: int = RD_POLICY_SCHEMA_VERSION,
) -> dict[str, Any]:
    payload = _policy_payload(policy)
    if role_bindings is not None:
        payload = {**payload, "role_bindings": deepcopy(role_bindings)}
        payload = validate_unified_policy_payload(payload)
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
) -> dict[str, Any]:
    if resolution_revision not in {1, 2}:
        raise PolicyResolutionError(
            "RD_POLICY_RESOLUTION_LIMIT", "at most two strengthening rounds"
        )
    repository = _repository(store)
    get_snapshot = getattr(repository, "get_rd_policy_snapshot", None)
    parent = get_snapshot(parent_snapshot_id) if callable(get_snapshot) else None
    if parent is None:
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID", "assessment parent snapshot is missing"
        )
    base_payload = _validate_snapshot(parent)
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
    derive = getattr(repository, "derive_assessment_policy_snapshot", None)
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
    source_snapshot_ids: list[str],
) -> dict[str, Any]:
    repository = _repository(store)
    get_snapshot = getattr(repository, "get_rd_policy_snapshot", None)
    if not callable(get_snapshot) or not source_snapshot_ids:
        raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", "version sources are required")
    sources = [get_snapshot(snapshot_id) for snapshot_id in source_snapshot_ids]
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
    payload = merge_policy_payloads([_validate_snapshot(source) for source in typed_sources])
    first = typed_sources[0]
    snapshot = {
        "id": _new_id(store, "rd_policy_snapshot"),
        "policy_id": first["policy_id"],
        "policy_version": first["policy_version"],
        "parent_snapshot_id": first["id"],
        "snapshot_kind": "version_resolved",
        "resolution_context_key": f"version:{version_id}:scope:{scope_version}",
        "resolution_revision": 1,
        "schema_version": first["schema_version"],
        "content_hash": _hash(payload),
        "payload_json": payload,
        "created_by": first.get("created_by") or "system",
    }
    get_assessment = getattr(repository, "get_requirement_assessment", None)
    sources_payload = [
        _source_edge_for_snapshot(
            store,
            source=source,
            get_assessment=get_assessment,
        )
        for source in typed_sources
    ]
    merge = getattr(repository, "merge_version_policy_snapshot_with_sources", None)
    return merge(snapshot=snapshot, sources=sources_payload) if callable(merge) else snapshot


def _source_edge_for_snapshot(
    store: Any,
    *,
    source: dict[str, Any],
    get_assessment: Any,
) -> dict[str, Any]:
    context_key = str(source.get("resolution_context_key") or "")
    if source.get("snapshot_kind") != "assessment_resolved" or not context_key.startswith(
        "assessment:"
    ):
        raise PolicyResolutionError(
            "RD_POLICY_SNAPSHOT_INVALID",
            "version sources must be assessment-resolved snapshots",
        )
    assessment_id = context_key.removeprefix("assessment:")
    assessment = get_assessment(assessment_id) if callable(get_assessment) else None
    requirement_id = str((assessment or {}).get("requirement_id") or "").strip()
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
        candidates = list_policies(brain_app_id=brain_app_id, product_id=None, status="active")
    if len(candidates) != 1:
        raise PolicyResolutionError(
            "RD_EXECUTION_POLICY_NOT_FOUND", "exactly one active policy is required"
        )
    return freeze_base_rd_policy_snapshot(store, policy=candidates[0])


def resolve_final_rd_policy(
    store: Any,
    *,
    requirement: dict[str, Any],
    assessment: dict[str, Any],
) -> dict[str, Any]:
    base_id = assessment.get("initial_strategy_snapshot_id")
    if not base_id:
        return resolve_initial_rd_policy(store, requirement=requirement)
    delta = assessment.get("tightened_policy") or assessment.get("policy_delta")
    if not delta:
        repository = _repository(store)
        get_snapshot = getattr(repository, "get_rd_policy_snapshot", None)
        base = get_snapshot(base_id) if callable(get_snapshot) else None
        if base is None:
            raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", "base snapshot is missing")
        _validate_snapshot(base)
        return base
    repository = _repository(store)
    get_snapshot = getattr(repository, "get_rd_policy_snapshot", None)
    base = get_snapshot(base_id) if callable(get_snapshot) else None
    if base is None:
        raise PolicyResolutionError("RD_POLICY_SNAPSHOT_INVALID", "base snapshot is missing")
    payload = {**_validate_snapshot(base), **delta}
    return derive_assessment_rd_policy_snapshot(
        store,
        assessment_id=str(assessment["id"]),
        parent_snapshot_id=base_id,
        resolution_revision=int(assessment.get("resolution_revision") or 1),
        tightened_payload=payload,
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
                union_keys={"gates", "human_points", "reviewer_role_codes"},
                risk_keys={"max_risk"},
            )
        elif key == "git_config":
            merged[key] = _merge_config(
                a,
                b,
                intersect_keys={"allowlist", "repository_allowlist", "trust_domains"},
                union_keys={"denylist", "repository_denylist"},
            )
        elif key == "experience_reuse_config":
            merged[key] = _merge_experience(a, b)
        elif key in {"team_config", "role_bindings"}:
            merged[key] = _union_value(a, b)
        else:
            raise PolicyResolutionError(
                "RD_VERSION_POLICY_MERGE_REQUIRED", f"{key} is incomparable"
            )
    return merged


def _merge_config(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    intersect_keys: set[str] | None = None,
    union_keys: set[str] | None = None,
    risk_keys: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise PolicyResolutionError(
            "RD_VERSION_POLICY_MERGE_REQUIRED", "configuration must be objects"
        )
    intersect_keys, union_keys, risk_keys = (
        intersect_keys or set(),
        union_keys or set(),
        risk_keys or set(),
    )
    merged: dict[str, Any] = {}
    for key in set(left) | set(right):
        a, b = left.get(key), right.get(key)
        if a == b or a is None or b is None:
            merged[key] = deepcopy(b if a is None else a)
        elif key in intersect_keys and isinstance(a, list) and isinstance(b, list):
            merged[key] = sorted(set(a) & set(b))
        elif key in union_keys and isinstance(a, list) and isinstance(b, list):
            merged[key] = sorted(set(a) | set(b))
        elif key in risk_keys:
            merged[key] = a if _risk_rank(a) <= _risk_rank(b) else b
        elif (
            key.startswith(("max_", "budget_", "timeout_", "capacity_"))
            and isinstance(a, (int, float))
            and isinstance(b, (int, float))
        ):
            merged[key] = min(a, b)
        else:
            raise PolicyResolutionError(
                "RD_VERSION_POLICY_MERGE_REQUIRED", f"{key} is incomparable"
            )
    return merged


def _merge_experience(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    mergeable_left = {
        key: value for key, value in left.items() if key not in {"enabled", "confidence"}
    }
    mergeable_right = {
        key: value for key, value in right.items() if key not in {"enabled", "confidence"}
    }
    merged = _merge_config(
        mergeable_left,
        mergeable_right,
        intersect_keys={"trust_domains", "compatibility"},
    )
    if "enabled" in left and "enabled" in right:
        merged["enabled"] = bool(left["enabled"]) and bool(right["enabled"])
    if "confidence" in left and "confidence" in right:
        merged["confidence"] = max(float(left["confidence"]), float(right["confidence"]))
    return merged


def _union_value(left: Any, right: Any) -> Any:
    if isinstance(left, list) and isinstance(right, list):
        unique = {
            json.dumps(value, ensure_ascii=False, sort_keys=True): deepcopy(value)
            for value in left + right
        }
        return [unique[key] for key in sorted(unique)]
    if isinstance(left, dict) and isinstance(right, dict):
        return _merge_config(left, right, union_keys=set(left) | set(right))
    raise PolicyResolutionError("RD_VERSION_POLICY_MERGE_REQUIRED", "values cannot be merged")
