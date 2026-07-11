from __future__ import annotations

from typing import Any


def health_evidence_present(result_json: dict[str, Any]) -> bool:
    health_checks = result_json.get("health_checks")
    smoke_tests = result_json.get("smoke_tests")
    return bool(
        (isinstance(health_checks, list) and health_checks)
        or (isinstance(smoke_tests, list) and smoke_tests)
    )


def health_evidence_passed(result_json: dict[str, Any]) -> bool:
    if str(result_json.get("health_status") or "") != "passed":
        return False
    checks = [
        item
        for collection in (
            result_json.get("health_checks"),
            result_json.get("smoke_tests"),
        )
        if isinstance(collection, list)
        for item in collection
        if isinstance(item, dict)
    ]
    return bool(checks) and all(bool(item.get("passed")) for item in checks)
