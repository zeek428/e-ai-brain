from __future__ import annotations

from typing import Any


def seed_accepted_assessment_provenance(store: Any, requirement: dict[str, Any] | str) -> None:
    """Test-only provenance fixture for legacy flows which start after assessment."""
    if isinstance(requirement, str):
        requirement = store.requirements[requirement]
    assessment = {
        "id": f"fixture-assessment-{requirement['id']}",
        "requirement_id": requirement["id"],
        "product_id": requirement["product_id"],
        "status": "accepted",
        "final_strategy_snapshot_id": "fixture-policy-snapshot",
    }
    store.requirement_assessments[assessment["id"]] = assessment
    repository = getattr(store, "repository", None)
    if repository is not None:
        records = getattr(repository, "_test_requirement_assessments", {})
        records[assessment["id"]] = assessment
        repository._test_requirement_assessments = records
        if not callable(getattr(repository, "list_requirement_assessments", None)):
            repository.list_requirement_assessments = lambda requirement_id: [
                dict(item)
                for item in repository._test_requirement_assessments.values()
                if item["requirement_id"] == requirement_id
            ]
