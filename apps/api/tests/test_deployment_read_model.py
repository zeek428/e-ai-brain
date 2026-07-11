from __future__ import annotations

from contextlib import contextmanager

import pytest

from app.core.repositories.devops import DevopsReadRepository
from app.core.store import MemoryStore
from app.services.operational_deployments import (
    get_deployment_request_detail_response,
    list_deployment_requests_response,
    list_deployment_schemes_response,
)

ADMIN = {
    "id": "user_admin",
    "roles": ["admin"],
    "permissions": ["deployment.read", "system.admin"],
    "scope_summary": [
        {"access_level": "admin", "scope_id": "*", "scope_type": "global"}
    ],
}


class _Cursor:
    def __init__(self):
        self.executed: list[tuple[str, tuple]] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=()):  # type: ignore[no-untyped-def]
        self.executed.append((" ".join(str(sql).split()), tuple(params)))

    def fetchall(self):
        return []


class _Connection:
    def __init__(self, cursor: _Cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self._cursor


class _Connect:
    def __init__(self, cursor: _Cursor):
        self.cursor = cursor

    @contextmanager
    def __call__(self, *, autocommit: bool = True):
        del autocommit
        yield _Connection(self.cursor)


def _store() -> MemoryStore:
    store = MemoryStore()
    for index in range(1, 4):
        scheme_id = f"scheme_{index:03d}"
        store.deployment_schemes[scheme_id] = {
            "id": scheme_id,
            "product_id": "product_001",
            "code": f"prod-{index}",
            "name": f"部署方案 {index}",
            "environment": "prod",
            "deployment_method": "manual",
            "executor_channel": "manual",
            "is_default": index == 1,
            "status": "active",
            "version": 1,
            "created_at": f"2026-07-11T00:0{index}:00+00:00",
            "updated_at": f"2026-07-11T00:0{index}:00+00:00",
        }
    for index in range(1, 4):
        deployment_id = f"deployment_{index:03d}"
        store.deployment_requests[deployment_id] = {
            "id": deployment_id,
            "product_id": "product_001",
            "version_id": "version_001",
            "title": f"部署 {index}",
            "environment": "prod",
            "status": "succeeded" if index == 1 else "pending_ops",
            "risk_level": "medium",
            "gate_summary": {},
            "requirement_ids": ["requirement_001"],
            "created_by": "user_admin",
            "created_at": f"2026-07-11T00:0{index}:00+00:00",
            "updated_at": f"2026-07-11T00:0{index}:00+00:00",
        }
    store.deployment_runs = {
        "run_001": {
            "id": "run_001",
            "deployment_request_id": "deployment_001",
            "operation": "deploy",
            "status": "success",
            "health_status": "healthy",
            "wave_number": 1,
            "wave_total": 1,
            "created_at": "2026-07-11T00:01:00+00:00",
        }
    }
    store.deployment_run_steps = {
        "step_001": {
            "id": "step_001",
            "deployment_run_id": "run_001",
            "step_type": "health_check",
            "status": "passed",
            "sequence": 3,
            "evidence": {"checks": [{"code": "api", "passed": True}]},
        }
    }
    store.execution_outbox_events = {
        "outbox_001": {
            "id": "outbox_001",
            "aggregate_type": "deployment_request",
            "aggregate_id": "deployment_001",
            "event_type": "deployment_dispatch_requested",
            "status": "completed",
        }
    }
    store.audit_events = [
        {
            "id": "audit_001",
            "event_type": "deployment.request.completed",
            "actor_id": "user_admin",
            "subject_type": "deployment_request",
            "subject_id": "deployment_001",
            "payload": {},
            "created_at": "2026-07-11T00:02:00+00:00",
        }
    ]
    return store


def test_repository_deployment_page_uses_sql_limit_offset_and_whitelisted_sort():
    cursor = _Cursor()
    repository = DevopsReadRepository(_Connect(cursor))

    result = repository.page_deployment_requests(
        environment="prod",
        page=2,
        page_size=20,
        product_id="product_001",
        product_scope_ids=["product_001"],
        sort_by="title",
        sort_order="asc",
        status=None,
        title="发布",
        version_id=None,
    )

    assert result == {"items": [], "total": 0}
    sql, params = cursor.executed[0]
    assert "COUNT(*) OVER()" in sql
    assert "ORDER BY lower(d.title) ASC, d.id ASC" in sql
    assert "LIMIT %s OFFSET %s" in sql
    assert params[-2:] == (20, 20)

    with pytest.raises(ValueError, match="sort"):
        repository.page_deployment_requests(
            environment=None,
            page=1,
            page_size=20,
            product_id=None,
            product_scope_ids=None,
            sort_by="updated_at; DROP TABLE deployment_requests",
            sort_order="desc",
            status=None,
            title=None,
            version_id=None,
        )


def test_repository_deployment_scheme_page_uses_sql_limit_offset_and_whitelisted_sort():
    cursor = _Cursor()
    repository = DevopsReadRepository(_Connect(cursor))

    result = repository.page_deployment_schemes(
        deployment_method="manual",
        environment="prod",
        name="生产",
        page=2,
        page_size=20,
        product_id="product_001",
        product_scope_ids=["product_001"],
        sort_by="name",
        sort_order="asc",
        status="active",
    )

    assert result == {"items": [], "total": 0}
    sql, params = cursor.executed[0]
    assert "COUNT(*) OVER()" in sql
    assert "ORDER BY lower(name) ASC, id ASC" in sql
    assert "LIMIT %s OFFSET %s" in sql
    assert params[-2:] == (20, 20)

    with pytest.raises(ValueError, match="sort"):
        repository.page_deployment_schemes(
            deployment_method=None,
            environment=None,
            name=None,
            page=1,
            page_size=20,
            product_id=None,
            product_scope_ids=None,
            sort_by="updated_at; DROP TABLE deployment_schemes",
            sort_order="desc",
            status=None,
        )


def test_deployment_list_has_stable_server_pagination():
    result = list_deployment_requests_response(
        current_store=_store(),
        environment=None,
        page=2,
        page_size=2,
        product_id="product_001",
        sort_by="updated_at",
        sort_order="desc",
        status=None,
        title=None,
        user=ADMIN,
        version_id=None,
    )

    assert result["total"] == 3
    assert [item["id"] for item in result["items"]] == ["deployment_001"]
    assert result["page"] == 2
    assert result["page_size"] == 2


def test_deployment_scheme_list_has_stable_server_pagination():
    result = list_deployment_schemes_response(
        current_store=_store(),
        deployment_method=None,
        environment=None,
        name=None,
        page=2,
        page_size=2,
        product_id="product_001",
        sort_by="updated_at",
        sort_order="desc",
        status=None,
        user=ADMIN,
    )

    assert result["total"] == 3
    assert [item["id"] for item in result["items"]] == ["scheme_001"]
    assert result["page"] == 2
    assert result["page_size"] == 2
    assert isinstance(result["query_time_ms"], float)


def test_deployment_detail_aggregates_runs_steps_dispatch_and_audit():
    detail = get_deployment_request_detail_response(
        current_store=_store(),
        deployment_request_id="deployment_001",
        user=ADMIN,
    )

    assert detail["id"] == "deployment_001"
    assert detail["runs"][0]["steps"][0]["step_type"] == "health_check"
    assert detail["dispatch_events"][0]["status"] == "completed"
    assert detail["audit_events"][0]["event_type"] == "deployment.request.completed"
