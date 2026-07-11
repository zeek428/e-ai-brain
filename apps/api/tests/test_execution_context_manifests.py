import json

import pytest
from fastapi import HTTPException

from app.core.store import MemoryStore
from app.services.execution_context_manifests import (
    build_and_save_execution_context_manifest,
    execution_context_manifest_for_task,
)


def _admin() -> dict:
    return {
        "id": "user_admin",
        "permissions": ["system.admin"],
        "roles": ["admin"],
        "scope_summary": [{"access_level": "admin", "scope_id": "*", "scope_type": "global"}],
    }


def _task() -> dict:
    return {
        "id": "task_001",
        "input_json": {
            "bug": {
                "id": "bug_001",
                "password": "must-not-leak",
                "severity": "high",
                "title": "登录失败",
            },
            "acceptance_criteria": ["登录恢复正常", "补充回归测试"],
        },
        "product_context": {
            "repository": {
                "default_branch": "main",
                "id": "repo_001",
                "remote_url": "https://oauth2:repo-secret@example.com/team/repo.git",
            }
        },
        "product_id": "product_001",
        "requirement_id": "requirement_001",
        "requirement_snapshot": {
            "acceptance_criteria": ["登录恢复正常"],
            "id": "requirement_001",
            "status": "in_development",
            "title": "修复登录流程",
            "version_id": "version_001",
        },
        "task_type": "bug_fix",
        "title": "修复登录失败",
        "version_id": "version_001",
    }


def test_context_manifest_is_versioned_deduplicated_and_redacted() -> None:
    store = MemoryStore()
    task = _task()
    knowledge_references = [
        {
            "chunk_id": "chunk_001",
            "chunk_index": 0,
            "content": "登录模块必须使用运行时凭据并补充回归测试。",
            "document_id": "document_001",
            "doc_type": "project_doc",
            "title": "登录模块研发规范",
        }
    ]

    first = build_and_save_execution_context_manifest(
        current_store=store,
        branch="main",
        knowledge_references=knowledge_references,
        repository_ref=task["product_context"]["repository"],
        task=task,
        user=_admin(),
    )
    duplicate = build_and_save_execution_context_manifest(
        current_store=store,
        branch="main",
        knowledge_references=knowledge_references,
        repository_ref=task["product_context"]["repository"],
        task=task,
        user=_admin(),
    )

    assert duplicate["id"] == first["id"]
    assert first["version"] == 1
    assert len(first["content_hash"]) == 64
    assert first["acceptance_criteria"] == ["登录恢复正常", "补充回归测试"]
    assert first["knowledge_refs"][0]["retrieval_reason"] == "产品与版本权限范围匹配"
    serialized = json.dumps(first, ensure_ascii=False)
    assert "must-not-leak" not in serialized
    assert "repo-secret" not in serialized
    assert "[REDACTED]" in serialized

    task["input_json"]["acceptance_criteria"].append("通过类型检查")
    second = build_and_save_execution_context_manifest(
        current_store=store,
        branch="main",
        knowledge_references=knowledge_references,
        repository_ref=task["product_context"]["repository"],
        task=task,
        user=_admin(),
    )

    assert second["version"] == 2
    assert second["content_hash"] != first["content_hash"]
    assert execution_context_manifest_for_task(store, task_id=task["id"]) == second


def test_context_manifest_rejects_out_of_scope_product() -> None:
    store = MemoryStore()
    user = {
        "id": "user_product_member",
        "permissions": ["task.execute"],
        "roles": ["developer"],
        "scope_summary": [
            {
                "access_level": "write",
                "scope_id": "product_other",
                "scope_type": "product",
            }
        ],
    }

    with pytest.raises(HTTPException) as error:
        build_and_save_execution_context_manifest(
            current_store=store,
            branch="main",
            knowledge_references=[],
            repository_ref={},
            task=_task(),
            user=user,
        )

    assert error.value.status_code == 403
    assert error.value.detail["code"] == "PRODUCT_SCOPE_FORBIDDEN"
