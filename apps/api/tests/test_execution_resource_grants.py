from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.store import MemoryStore

ADMIN = {
    "id": "user_admin",
    "roles": ["admin"],
    "permissions": ["system.admin"],
    "scope_summary": [
        {"access_level": "admin", "scope_id": "*", "scope_type": "global"}
    ],
}
PRODUCT_A_RELEASE_OWNER = {
    "id": "user_release_a",
    "roles": ["release_owner"],
    "permissions": ["deployment.scheme.manage"],
    "scope_summary": [
        {"access_level": "write", "scope_id": "product_a", "scope_type": "product"}
    ],
}


def _store() -> MemoryStore:
    store = MemoryStore()
    store.products = {
        "product_a": {"id": "product_a", "name": "产品 A", "status": "active"},
        "product_b": {"id": "product_b", "name": "产品 B", "status": "active"},
    }
    store.ai_executor_runners = {
        "runner_001": {
            "id": "runner_001",
            "capabilities": ["deployment"],
            "last_heartbeat_at": "2999-01-01T00:00:00+00:00",
            "metadata": {
                "deployment_targets": [
                    {"code": "prod-a", "method": "ssh", "name": "生产 A"},
                    {"code": "prod-b", "method": "docker", "name": "生产 B"},
                ]
            },
            "status": "active",
            "trust_domain": "deployment",
        }
    }
    return store


def test_product_user_sees_only_granted_runner_targets():
    from app.services.execution_resource_grants import (
        create_execution_resource_grant_response,
    )
    from app.services.operational_deployments import (
        list_deployment_runner_targets_response,
    )

    store = _store()
    create_execution_resource_grant_response(
        current_store=store,
        payload=SimpleNamespace(
            environment="prod",
            product_id="product_a",
            resource_id="runner_001",
            resource_type="runner_target",
            target_code="prod-a",
        ),
        user=ADMIN,
    )
    create_execution_resource_grant_response(
        current_store=store,
        payload=SimpleNamespace(
            environment="prod",
            product_id="product_b",
            resource_id="runner_001",
            resource_type="runner_target",
            target_code="prod-b",
        ),
        user=ADMIN,
    )

    result = list_deployment_runner_targets_response(
        current_store=store,
        environment="prod",
        method=None,
        product_id="product_a",
        runner_id=None,
        user=PRODUCT_A_RELEASE_OWNER,
    )

    assert [(item["runner_id"], item["code"]) for item in result["items"]] == [
        ("runner_001", "prod-a")
    ]


def test_cross_product_or_ungranted_resource_binding_is_rejected():
    from app.services.execution_resource_grants import (
        create_execution_resource_grant_response,
        require_execution_resource_grant,
    )

    store = _store()
    create_execution_resource_grant_response(
        current_store=store,
        payload=SimpleNamespace(
            environment="prod",
            product_id="product_b",
            resource_id="runner_001",
            resource_type="runner_target",
            target_code="prod-b",
        ),
        user=ADMIN,
    )

    with pytest.raises(HTTPException) as exc_info:
        require_execution_resource_grant(
            store,
            environment="prod",
            product_id="product_a",
            resource_id="runner_001",
            resource_type="runner_target",
            target_code="prod-b",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "EXECUTION_RESOURCE_NOT_GRANTED"


def test_resource_grant_update_uses_optimistic_version():
    from app.services.execution_resource_grants import (
        create_execution_resource_grant_response,
        update_execution_resource_grant_response,
    )

    store = _store()
    grant = create_execution_resource_grant_response(
        current_store=store,
        payload=SimpleNamespace(
            environment="prod",
            product_id="product_a",
            resource_id="runner_001",
            resource_type="runner_target",
            target_code="prod-a",
        ),
        user=ADMIN,
    )
    updated = update_execution_resource_grant_response(
        current_store=store,
        grant_id=grant["id"],
        payload=SimpleNamespace(status="disabled", version=1),
        user=ADMIN,
    )
    assert updated["status"] == "disabled"
    assert updated["version"] == 2

    with pytest.raises(HTTPException) as exc_info:
        update_execution_resource_grant_response(
            current_store=store,
            grant_id=grant["id"],
            payload=SimpleNamespace(status="active", version=1),
            user=ADMIN,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "RESOURCE_VERSION_CONFLICT"
