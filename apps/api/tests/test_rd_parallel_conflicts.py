from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.rd_parallel_conflicts import analyze_parallel_resource_conflicts


def test_parallel_write_claims_are_serialized_deterministically() -> None:
    result = analyze_parallel_resource_conflicts(
        {
            "work_items": [
                {
                    "id": "api-user",
                    "priority": 20,
                    "resource_claims": [
                        {
                            "repository_id": "repository-1",
                            "path": "apps/api/app/users.py",
                            "mode": "write",
                        }
                    ],
                },
                {
                    "id": "api-package",
                    "priority": 10,
                    "resource_claims": [
                        {
                            "repository_id": "repository-1",
                            "path": "apps/api/app",
                            "mode": "write",
                        }
                    ],
                },
            ],
            "dependencies": [],
        }
    )

    assert result["dependencies"] == [
        {
            "predecessor_work_item_id": "api-package",
            "successor_work_item_id": "api-user",
            "dependency_type": "finish_to_start",
            "source": "parallel_resource_conflict",
        }
    ]
    assert result["parallel_resource_conflicts"] == [
        {
            "repository_id": "repository-1",
            "path": "apps/api/app",
            "other_path": "apps/api/app/users.py",
            "predecessor_work_item_id": "api-package",
            "successor_work_item_id": "api-user",
        }
    ]


def test_ordered_or_read_only_claims_do_not_add_a_serialization_edge() -> None:
    result = analyze_parallel_resource_conflicts(
        {
            "work_items": [
                {
                    "id": "read",
                    "resource_claims": [
                        {
                            "repository_id": "repository-1",
                            "path": "apps/api/app/users.py",
                            "mode": "read",
                        }
                    ],
                },
                {
                    "id": "write",
                    "resource_claims": [
                        {
                            "repository_id": "repository-1",
                            "path": "apps/api/app/users.py",
                            "mode": "write",
                        }
                    ],
                },
                {
                    "id": "ordered",
                    "resource_claims": [
                        {
                            "repository_id": "repository-1",
                            "path": "apps/api/app/users.py",
                            "mode": "write",
                        }
                    ],
                },
            ],
            "dependencies": [
                {
                    "predecessor_work_item_id": "write",
                    "successor_work_item_id": "ordered",
                    "dependency_type": "finish_to_start",
                }
            ],
        }
    )

    assert result["dependencies"] == [
        {
            "predecessor_work_item_id": "write",
            "successor_work_item_id": "ordered",
            "dependency_type": "finish_to_start",
        }
    ]
    assert result["parallel_resource_conflicts"] == []


@pytest.mark.parametrize(
    "claim",
    [
        {"repository_id": "repository-1", "path": "/absolute.py", "mode": "write"},
        {"repository_id": "repository-1", "path": "../escape.py", "mode": "write"},
        {"repository_id": "", "path": "src/main.py", "mode": "write"},
        {"repository_id": "repository-1", "path": "src/main.py"},
    ],
)
def test_invalid_resource_claim_is_rejected(claim: dict[str, str]) -> None:
    with pytest.raises(HTTPException) as exc_info:
        analyze_parallel_resource_conflicts(
            {
                "work_items": [{"id": "implementation", "resource_claims": [claim]}],
                "dependencies": [],
            }
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "RD_PLAN_INVALID"
