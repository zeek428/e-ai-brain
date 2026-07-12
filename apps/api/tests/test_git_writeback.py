from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from app.core.store import MemoryStore

ADMIN = {
    "id": "user_admin",
    "roles": ["admin"],
    "permissions": ["gitlab.review", "system.admin"],
    "scope_summary": [
        {"access_level": "admin", "scope_id": "*", "scope_type": "global"}
    ],
}


class FakeResponse:
    status = 201
    headers: dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"id": 42}'


def _store() -> MemoryStore:
    store = MemoryStore()
    store.products = {
        "product_001": {"id": "product_001", "name": "Git 产品", "status": "active"},
        "product_002": {"id": "product_002", "name": "其他产品", "status": "active"},
    }
    store.product_git_repositories = {
        "repo_001": {
            "id": "repo_001",
            "product_id": "product_001",
            "git_provider": "github",
            "remote_url": "https://github.com/acme/project.git",
            "project_path": "acme/project",
            "status": "active",
        }
    }
    store.integration_plugins = {
        "plugin_github": {"id": "plugin_github", "code": "github", "status": "active"}
    }
    store.plugin_connections = {
        "connection_github": {
            "id": "connection_github",
            "plugin_id": "plugin_github",
            "endpoint_url": "https://api.github.com",
            "status": "active",
            "auth_config": {"token_ref": "env:GITHUB_WRITEBACK_TOKEN"},
            "request_config": {"write_permissions": ["comment", "review", "merge"]},
        }
    }
    store.quality_gate_runs = {
        "quality_gate_passed": {
            "id": "quality_gate_passed",
            "product_id": "product_001",
            "status": "passed",
            "blocked_reasons": [],
            "independent_evidence_count": 2,
            "verified_attestation_count": 1,
            "verifier_trust_isolated": True,
        },
        "quality_gate_failed": {
            "id": "quality_gate_failed",
            "product_id": "product_001",
            "status": "failed",
            "blocked_reasons": ["CI_FAILED"],
            "independent_evidence_count": 1,
        },
    }
    return store


def test_git_merge_writeback_requires_passed_independent_gate():
    from app.services.git_provider_writeback import queue_git_writeback

    store = _store()

    with pytest.raises(HTTPException) as exc_info:
        queue_git_writeback(
            store,
            action="merge",
            connection_id="connection_github",
            message="Merge after checks",
            product_id="product_001",
            quality_gate_run_id="quality_gate_failed",
            repository_id="repo_001",
            subject_id="task_001",
            subject_type="ai_task",
            target_number=17,
            user=ADMIN,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "GIT_WRITEBACK_GATE_BLOCKED"


def test_git_writeback_is_idempotent_and_never_persists_token(monkeypatch):
    from app.services.git_provider_writeback import queue_git_writeback

    monkeypatch.setenv("GITHUB_WRITEBACK_TOKEN", "github-writeback-secret")
    store = _store()
    first = queue_git_writeback(
        store,
        action="merge",
        connection_id="connection_github",
        message="Merge after checks",
        product_id="product_001",
        quality_gate_run_id="quality_gate_passed",
        repository_id="repo_001",
        subject_id="task_001",
        subject_type="ai_task",
        target_number=17,
        user=ADMIN,
    )
    second = queue_git_writeback(
        store,
        action="merge",
        connection_id="connection_github",
        message="Merge after checks",
        product_id="product_001",
        quality_gate_run_id="quality_gate_passed",
        repository_id="repo_001",
        subject_id="task_001",
        subject_type="ai_task",
        target_number=17,
        user=ADMIN,
    )

    assert first["id"] == second["id"]
    assert len(store.execution_outbox_events) == 1
    assert "github-writeback-secret" not in json.dumps(first)


def test_git_writeback_worker_calls_github_and_completes_outbox(monkeypatch):
    from app.services.git_provider_writeback import queue_git_writeback
    from app.services.operational_deployments import process_execution_outbox_events

    monkeypatch.setenv("GITHUB_WRITEBACK_TOKEN", "github-writeback-secret")
    store = _store()
    event = queue_git_writeback(
        store,
        action="merge",
        connection_id="connection_github",
        message="Merge after checks",
        product_id="product_001",
        quality_gate_run_id="quality_gate_passed",
        repository_id="repo_001",
        subject_id="task_001",
        subject_type="ai_task",
        target_number=17,
        user=ADMIN,
    )
    requests: list[dict[str, str]] = []

    def fake_urlopen(request, timeout=30):  # type: ignore[no-untyped-def]
        requests.append(
            {
                "authorization": request.get_header("Authorization"),
                "method": request.get_method(),
                "url": request.full_url,
            }
        )
        return FakeResponse()

    monkeypatch.setattr("app.services.git_provider_writeback.urlopen", fake_urlopen)

    assert process_execution_outbox_events(
        store,
        worker_id="execution-worker",
    ) == 1
    assert requests == [
        {
            "authorization": "Bearer github-writeback-secret",
            "method": "PUT",
            "url": "https://api.github.com/repos/acme/project/pulls/17/merge",
        }
    ]
    persisted = store.execution_outbox_events[event["id"]]
    assert persisted["status"] == "completed"
    assert "github-writeback-secret" not in json.dumps(persisted)


def test_git_writeback_dispatch_rechecks_revoked_connection_permission(monkeypatch):
    from app.services.git_provider_writeback import (
        dispatch_git_writeback_event,
        queue_git_writeback,
    )

    monkeypatch.setenv("GITHUB_WRITEBACK_TOKEN", "github-writeback-secret")
    store = _store()
    event = queue_git_writeback(
        store,
        action="merge",
        connection_id="connection_github",
        message="Merge after checks",
        product_id="product_001",
        quality_gate_run_id="quality_gate_passed",
        repository_id="repo_001",
        subject_id="task_001",
        subject_type="ai_task",
        target_number=17,
        user=ADMIN,
    )
    store.plugin_connections["connection_github"]["request_config"] = {
        "write_permissions": ["comment"]
    }

    with pytest.raises(HTTPException) as exc_info:
        dispatch_git_writeback_event(store, event=event)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "GIT_WRITEBACK_PERMISSION_DENIED"


def test_git_writeback_rejects_repository_from_another_product():
    from app.services.git_provider_writeback import queue_git_writeback

    store = _store()

    with pytest.raises(HTTPException) as exc_info:
        queue_git_writeback(
            store,
            action="comment",
            connection_id="connection_github",
            message="Review result",
            product_id="product_002",
            quality_gate_run_id=None,
            repository_id="repo_001",
            subject_id="task_001",
            subject_type="ai_task",
            target_number=17,
            user=ADMIN,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == "NOT_FOUND"
