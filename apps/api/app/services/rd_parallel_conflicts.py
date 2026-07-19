"""Deterministic resource-conflict analysis for collaboration work-item plans."""

from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from typing import Any

from app.api.deps import api_error

_WRITE_MODE = "write"
_ALLOWED_MODES = {"read", _WRITE_MODE}


def _invalid(message: str, *, reason: str, **details: Any) -> None:
    raise api_error(422, "RD_PLAN_INVALID", message, {"reason": reason, **details})


def _item_id(item: Any, *, position: int) -> str:
    if not isinstance(item, dict):
        _invalid("Work item must be an object", reason="work_item_invalid", position=position)
    item_id = str(item.get("id") or item.get("idempotency_key") or "").strip()
    if not item_id:
        _invalid("Work item id is required", reason="work_item_id_missing", position=position)
    return item_id


def _normalise_path(value: Any, *, item_id: str, position: int) -> str:
    path = str(value or "").strip().replace("\\", "/")
    segments = path.split("/")
    if (
        not path
        or path.startswith("/")
        or any(segment in {"", ".", ".."} for segment in segments)
        or ":" in segments[0]
    ):
        _invalid(
            "Resource claim path must be a relative repository path",
            reason="resource_claim_path_invalid",
            item_id=item_id,
            position=position,
        )
    return "/".join(segments)


def _normalise_claims(item: dict[str, Any], *, item_id: str) -> list[dict[str, str]]:
    raw_claims = item.get("resource_claims", [])
    if raw_claims is None:
        raw_claims = []
    if not isinstance(raw_claims, list):
        _invalid(
            "resource_claims must be a list",
            reason="resource_claims_invalid",
            item_id=item_id,
        )
    claims: set[tuple[str, str, str]] = set()
    for position, raw_claim in enumerate(raw_claims):
        if not isinstance(raw_claim, dict):
            _invalid(
                "Resource claim must be an object",
                reason="resource_claim_invalid",
                item_id=item_id,
                position=position,
            )
        repository_id = str(raw_claim.get("repository_id") or "").strip()
        if not repository_id:
            _invalid(
                "Resource claim repository_id is required",
                reason="resource_claim_repository_missing",
                item_id=item_id,
                position=position,
            )
        mode = str(raw_claim.get("mode") or "").strip().lower()
        if not mode:
            _invalid(
                "Resource claim mode is required",
                reason="resource_claim_mode_missing",
                item_id=item_id,
                position=position,
            )
        if mode not in _ALLOWED_MODES:
            _invalid(
                "Resource claim mode must be read or write",
                reason="resource_claim_mode_invalid",
                item_id=item_id,
                position=position,
            )
        claims.add(
            (
                repository_id,
                _normalise_path(raw_claim.get("path"), item_id=item_id, position=position),
                mode,
            )
        )
    return [
        {"repository_id": repository_id, "path": path, "mode": mode}
        for repository_id, path, mode in sorted(claims)
    ]


def _dependency_pairs(raw_dependencies: Any, item_ids: set[str]) -> list[dict[str, Any]]:
    if raw_dependencies is None:
        return []
    if not isinstance(raw_dependencies, list):
        _invalid("Plan dependencies must be a list", reason="dependencies_invalid")
    result: list[dict[str, Any]] = []
    for position, raw_dependency in enumerate(raw_dependencies):
        if not isinstance(raw_dependency, dict):
            _invalid(
                "Dependency must be an object",
                reason="dependency_invalid",
                position=position,
            )
        predecessor = str(raw_dependency.get("predecessor_work_item_id") or "").strip()
        successor = str(raw_dependency.get("successor_work_item_id") or "").strip()
        if predecessor not in item_ids or successor not in item_ids or predecessor == successor:
            # The regular plan validator provides the precise DAG error after
            # this component has normalised the remaining data.
            result.append(deepcopy(raw_dependency))
            continue
        result.append(
            {
                **deepcopy(raw_dependency),
                "predecessor_work_item_id": predecessor,
                "successor_work_item_id": successor,
                "dependency_type": str(
                    raw_dependency.get("dependency_type") or "finish_to_start"
                ),
            }
        )
    return result


def _reachable(
    item_ids: set[str],
    dependencies: list[dict[str, Any]],
) -> dict[str, set[str]]:
    successors: dict[str, set[str]] = defaultdict(set)
    for dependency in dependencies:
        predecessor = str(dependency.get("predecessor_work_item_id") or "")
        successor = str(dependency.get("successor_work_item_id") or "")
        if predecessor in item_ids and successor in item_ids and predecessor != successor:
            successors[predecessor].add(successor)
    reachability: dict[str, set[str]] = {}
    for item_id in item_ids:
        seen: set[str] = set()
        queue = deque(successors[item_id])
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            queue.extend(successors[current].difference(seen))
        reachability[item_id] = seen
    return reachability


def _paths_overlap(first: str, second: str) -> bool:
    return first == second or first.startswith(f"{second}/") or second.startswith(f"{first}/")


def _priority(item: dict[str, Any]) -> int:
    value = item.get("priority", 100)
    return value if isinstance(value, int) and not isinstance(value, bool) else 100


def analyze_parallel_resource_conflicts(proposal: dict[str, Any]) -> dict[str, Any]:
    """Serialize unordered repository write collisions from explicit claims.

    The function is deliberately pure: it cannot write state, perform model
    calls, choose a seat, or grant access.  It only makes unsafe parallelism
    impossible by adding an ordinary DAG dependency and retaining the evidence
    used to derive it.
    """
    if not isinstance(proposal, dict):
        _invalid("Plan must be an object", reason="plan_invalid")
    raw_items = proposal.get("work_items")
    if not isinstance(raw_items, list):
        _invalid("Plan requires work_items", reason="work_items_missing")

    work_items: list[dict[str, Any]] = []
    items_by_id: dict[str, dict[str, Any]] = {}
    claims_by_id: dict[str, list[dict[str, str]]] = {}
    for position, raw_item in enumerate(raw_items):
        item_id = _item_id(raw_item, position=position)
        if item_id in items_by_id:
            _invalid("Work item ids must be unique", reason="work_item_duplicate", item_id=item_id)
        item = deepcopy(raw_item)
        item["id"] = item_id
        claims = _normalise_claims(item, item_id=item_id)
        if (
            str(item.get("work_item_type") or "").strip().lower() == "implementation"
            and not any(claim["mode"] == _WRITE_MODE for claim in claims)
        ):
            _invalid(
                "Implementation work items require at least one repository write claim",
                reason="implementation_resource_claim_missing",
                item_id=item_id,
            )
        item["resource_claims"] = claims
        work_items.append(item)
        items_by_id[item_id] = item
        claims_by_id[item_id] = claims

    item_ids = set(items_by_id)
    dependencies = _dependency_pairs(proposal.get("dependencies", []), item_ids)
    generated_dependencies: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []

    candidates: list[
        tuple[tuple[int, str], tuple[int, str], str, str, dict[str, str], dict[str, str]]
    ] = []
    ordered_ids = sorted(item_ids)
    for first_index, first_id in enumerate(ordered_ids):
        for second_id in ordered_ids[first_index + 1 :]:
            for first_claim in claims_by_id[first_id]:
                for second_claim in claims_by_id[second_id]:
                    if (
                        first_claim["mode"] != _WRITE_MODE
                        or second_claim["mode"] != _WRITE_MODE
                        or first_claim["repository_id"] != second_claim["repository_id"]
                        or not _paths_overlap(first_claim["path"], second_claim["path"])
                    ):
                        continue
                    first_order = (_priority(items_by_id[first_id]), first_id)
                    second_order = (_priority(items_by_id[second_id]), second_id)
                    predecessor_id, successor_id = (
                        (first_id, second_id)
                        if first_order <= second_order
                        else (second_id, first_id)
                    )
                    predecessor_claim, successor_claim = (
                        (first_claim, second_claim)
                        if predecessor_id == first_id
                        else (second_claim, first_claim)
                    )
                    candidates.append(
                        (
                            (_priority(items_by_id[predecessor_id]), predecessor_id),
                            (_priority(items_by_id[successor_id]), successor_id),
                            predecessor_id,
                            successor_id,
                            predecessor_claim,
                            successor_claim,
                        )
                    )

    seen_pairs: set[tuple[str, str, str, str, str]] = set()
    for (
        _,
        _,
        predecessor_id,
        successor_id,
        predecessor_claim,
        successor_claim,
    ) in sorted(candidates):
        claim_key = (
            predecessor_id,
            successor_id,
            predecessor_claim["repository_id"],
            predecessor_claim["path"],
            successor_claim["path"],
        )
        if claim_key in seen_pairs:
            continue
        seen_pairs.add(claim_key)
        reachability = _reachable(item_ids, [*dependencies, *generated_dependencies])
        if (
            successor_id in reachability[predecessor_id]
            or predecessor_id in reachability[successor_id]
        ):
            continue
        generated = {
            "predecessor_work_item_id": predecessor_id,
            "successor_work_item_id": successor_id,
            "dependency_type": "finish_to_start",
            "source": "parallel_resource_conflict",
        }
        dependencies.append(generated)
        generated_dependencies.append(generated)
        conflicts.append(
            {
                "repository_id": predecessor_claim["repository_id"],
                "path": predecessor_claim["path"],
                "other_path": successor_claim["path"],
                "predecessor_work_item_id": predecessor_id,
                "successor_work_item_id": successor_id,
            }
        )

    return {
        **deepcopy(proposal),
        "work_items": sorted(work_items, key=lambda item: item["id"]),
        "dependencies": sorted(
            dependencies,
            key=lambda item: (
                str(item.get("predecessor_work_item_id") or ""),
                str(item.get("successor_work_item_id") or ""),
                str(item.get("dependency_type") or ""),
                str(item.get("source") or ""),
            ),
        ),
        "parallel_resource_conflicts": sorted(
            conflicts,
            key=lambda item: (
                item["predecessor_work_item_id"],
                item["successor_work_item_id"],
                item["repository_id"],
                item["path"],
                item["other_path"],
            ),
        ),
    }
