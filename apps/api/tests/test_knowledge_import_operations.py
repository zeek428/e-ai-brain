from __future__ import annotations

import base64
import json
import time
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def current_user(headers: dict[str, str]) -> dict:
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    return response.json()["data"]


def create_space(headers: dict[str, str]) -> dict[str, str]:
    response = client.post(
        "/api/knowledge/spaces",
        headers=headers,
        json={"code": "import-ops", "name": "导入运营", "description": "导入运营测试"},
    )
    assert response.status_code == 200
    return response.json()["data"]


def create_folder(headers: dict[str, str], space_id: str, name: str) -> dict[str, str]:
    response = client.post(
        f"/api/knowledge/spaces/{space_id}/folders",
        headers=headers,
        json={"name": name},
    )
    assert response.status_code == 200
    return response.json()["data"]


def upload_markdown(
    headers: dict[str, str],
    *,
    space_id: str,
    folder_id: str | None = None,
    title: str = "支付手册",
    content: str = "# 支付接入\n\n## 失败排查\n\nspace-token 需要检查网关。",
) -> dict:
    response = client.post(
        "/api/knowledge/documents/upload",
        headers=headers,
        json={
            "knowledge_space_id": space_id,
            "folder_id": folder_id,
            "title": title,
            "filename": f"{title}.md",
            "mime_type": "text/markdown",
            "content_base64": base64.b64encode(content.encode()).decode("ascii"),
            "doc_type": "runbook",
            "tags": ["payment"],
            "parser_engine": "markdown",
            "chunk_strategy": "parent_child",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]


def wait_for_import_job(
    headers: dict[str, str],
    *,
    job_id: str,
    terminal_statuses: set[str] | None = None,
    timeout_seconds: float = 2.0,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    terminal_statuses = terminal_statuses or {"completed", "failed", "cancelled"}
    while time.monotonic() < deadline:
        response = client.get("/api/knowledge/import-jobs", headers=headers)
        assert response.status_code == 200
        jobs = response.json()["data"]["items"]
        job = next((item for item in jobs if item["id"] == job_id), None)
        if job is not None and job["status"] in terminal_statuses:
            return job
        time.sleep(0.02)
    raise AssertionError(f"Import job {job_id} did not reach {sorted(terminal_statuses)}")


class RecordingImportWorker:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, str]] = []

    def enqueue(self, *, job_id: str, user: dict) -> None:
        self.enqueued.append((job_id, user["id"]))


def test_upload_reparse_and_retry_enqueue_jobs_when_worker_is_available():
    app.state.store.reset()
    previous_worker = getattr(app.state, "knowledge_import_worker", None)
    worker = RecordingImportWorker()
    app.state.knowledge_import_worker = worker
    try:
        headers = auth_headers()
        user = current_user(headers)
        space = create_space(headers)

        uploaded = upload_markdown(headers, space_id=space["id"])
        upload_job_id = uploaded["import_job"]["id"]
        assert worker.enqueued == [(upload_job_id, user["id"])]

        reparse_response = client.post(
            f"/api/knowledge/documents/{uploaded['document']['id']}/reparse",
            headers=headers,
            json={"parser_engine": "markdown", "chunk_strategy": "simple_text"},
        )
        assert reparse_response.status_code == 200
        reparse_job_id = reparse_response.json()["data"]["import_job"]["id"]
        assert worker.enqueued[-1] == (reparse_job_id, user["id"])

        cancel_response = client.post(
            f"/api/knowledge/import-jobs/{upload_job_id}/cancel",
            headers=headers,
        )
        assert cancel_response.status_code == 200
        retry_response = client.post(
            f"/api/knowledge/import-jobs/{upload_job_id}/retry",
            headers=headers,
        )
        assert retry_response.status_code == 200
        assert worker.enqueued[-1] == (upload_job_id, user["id"])
    finally:
        if previous_worker is None:
            delattr(app.state, "knowledge_import_worker")
        else:
            app.state.knowledge_import_worker = previous_worker


def test_import_worker_status_requires_authorized_knowledge_role():
    app.state.store.reset()

    missing_auth_response = client.get("/api/knowledge/import-worker/status")
    assert missing_auth_response.status_code == 401

    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    forbidden_response = client.get(
        "/api/knowledge/import-worker/status",
        headers=reviewer_headers,
    )
    assert forbidden_response.status_code == 403

    admin_headers = auth_headers()
    ok_response = client.get("/api/knowledge/import-worker/status", headers=admin_headers)
    assert ok_response.status_code == 200
    assert ok_response.json()["data"]["running"] is False


def test_background_import_worker_processes_queued_upload_to_completion():
    from app.services.knowledge_import_worker import KnowledgeImportWorker

    app.state.store.reset()
    headers = auth_headers()
    user = current_user(headers)
    space = create_space(headers)
    uploaded = upload_markdown(
        headers,
        space_id=space["id"],
        content="# 后台导入\n\nbackground-worker-token 自动生成 chunk。",
    )
    document_id = uploaded["document"]["id"]
    job_id = uploaded["import_job"]["id"]

    worker = KnowledgeImportWorker(app=app, poll_interval_seconds=0.01)
    worker.start()
    try:
        worker.enqueue(job_id=job_id, user=user)
        completed_job = wait_for_import_job(headers, job_id=job_id)
    finally:
        worker.stop(timeout_seconds=1)

    assert completed_job["status"] == "completed"
    stored_job = app.state.store.knowledge_import_jobs[job_id]
    assert stored_job["attempt_count"] == 1
    assert stored_job["locked_by"] is None
    assert stored_job["locked_until"] is None
    chunks_response = client.get(
        f"/api/knowledge/documents/{document_id}/chunks",
        headers=headers,
    )
    assert chunks_response.status_code == 200
    chunks = chunks_response.json()["data"]["items"]
    assert any("background-worker-token" in chunk["content"] for chunk in chunks)


def test_background_import_worker_claims_repository_job_before_running():
    from app.services.knowledge_import_worker import (
        KnowledgeImportWorker,
        KnowledgeImportWorkItem,
    )

    class ClaimRepository:
        def __init__(self, claimed: bool) -> None:
            self.claimed = claimed
            self.calls: list[dict] = []

        def claim_knowledge_import_job(
            self,
            *,
            job_id: str,
            worker_id: str,
            lock_ttl_seconds: float,
        ) -> bool:
            self.calls.append(
                {
                    "job_id": job_id,
                    "worker_id": worker_id,
                    "lock_ttl_seconds": lock_ttl_seconds,
                },
            )
            return self.claimed

    repository = ClaimRepository(claimed=False)
    worker = KnowledgeImportWorker(
        app=SimpleNamespace(state=SimpleNamespace(store=SimpleNamespace(repository=repository))),
        lock_ttl_seconds=42,
    )

    claimed = worker._claim_item(
        KnowledgeImportWorkItem(job_id="knowledge_import_job_001", user={"id": "user_admin"}),
    )

    assert claimed is False
    assert repository.calls == [
        {
            "job_id": "knowledge_import_job_001",
            "worker_id": worker.worker_id,
            "lock_ttl_seconds": 42,
        },
    ]


def test_background_import_worker_claims_memory_job_through_helper():
    from app.core.store import MemoryStore
    from app.services.knowledge_import_worker import (
        KnowledgeImportWorker,
        KnowledgeImportWorkItem,
    )

    store = MemoryStore()
    store.knowledge_import_jobs["knowledge_import_job_001"] = {
        "id": "knowledge_import_job_001",
        "status": "queued",
        "attempt_count": 0,
    }
    worker = KnowledgeImportWorker(
        app=SimpleNamespace(state=SimpleNamespace(store=store)),
        lock_ttl_seconds=42,
    )

    claimed = worker._claim_item(
        KnowledgeImportWorkItem(job_id="knowledge_import_job_001", user={"id": "user_admin"}),
    )

    assert claimed is True
    stored_job = store.knowledge_import_jobs["knowledge_import_job_001"]
    assert stored_job["attempt_count"] == 1
    assert stored_job["locked_by"] == worker.worker_id
    assert stored_job["locked_until"]


def test_background_import_worker_sweeps_queued_jobs_without_explicit_enqueue():
    from app.services.knowledge_import_worker import KnowledgeImportWorker

    app.state.store.reset()
    headers = auth_headers()
    space = create_space(headers)
    uploaded = upload_markdown(
        headers,
        space_id=space["id"],
        content="# 队列补偿\n\nworker-sweep-token 应被补偿消费。",
    )
    document_id = uploaded["document"]["id"]
    job_id = uploaded["import_job"]["id"]

    worker = KnowledgeImportWorker(app=app, poll_interval_seconds=0.01)
    worker.start()
    try:
        completed_job = wait_for_import_job(headers, job_id=job_id)
    finally:
        worker.stop(timeout_seconds=1)

    assert completed_job["status"] == "completed"
    chunk_sets = client.get(
        f"/api/knowledge/documents/{document_id}/chunk-sets",
        headers=headers,
    ).json()["data"]["items"]
    assert chunk_sets[0]["created_by"] == "user_admin"
    chunks = client.get(
        f"/api/knowledge/documents/{document_id}/chunks",
        headers=headers,
    ).json()["data"]["items"]
    assert any("worker-sweep-token" in chunk["content"] for chunk in chunks)


def test_import_job_is_queued_then_processed_with_parsed_asset_and_parent_child_chunks():
    app.state.store.reset()
    headers = auth_headers()
    space = create_space(headers)
    folder = create_folder(headers, space["id"], "支付资料")

    uploaded = upload_markdown(
        headers,
        space_id=space["id"],
        folder_id=folder["id"],
        content="# 失败排查\n\nspace-token 需要检查网关。",
    )
    document = uploaded["document"]
    job = uploaded["import_job"]

    assert document["index_status"] == "importing"
    assert document["chunk_count"] == 0
    assert document["active_chunk_set_id"] is None
    assert job["status"] == "queued"
    assert job["progress"] == 0

    run_response = client.post(f"/api/knowledge/import-jobs/{job['id']}/run", headers=headers)
    assert run_response.status_code == 200
    run_payload = run_response.json()["data"]
    assert run_payload["import_job"]["status"] == "completed"
    assert run_payload["document"]["index_status"] in {"text_indexed", "vector_indexed"}
    assert run_payload["document"]["active_chunk_set_id"].startswith("knowledge_chunk_set_")

    assets = client.get(
        f"/api/knowledge/documents/{document['id']}/assets",
        headers=headers,
    ).json()["data"]["items"]
    assert [asset["asset_type"] for asset in assets] == ["original", "parsed_markdown"]
    assert assets[1]["filename"].endswith(".parsed.md")

    chunk_sets = client.get(
        f"/api/knowledge/documents/{document['id']}/chunk-sets",
        headers=headers,
    ).json()["data"]["items"]
    assert len(chunk_sets) == 1
    assert chunk_sets[0]["status"] == "active"
    assert chunk_sets[0]["chunk_strategy"] == "parent_child"

    chunks = client.get(
        f"/api/knowledge/documents/{document['id']}/chunks",
        headers=headers,
    ).json()["data"]["items"]
    parent_chunks = [chunk for chunk in chunks if chunk["metadata"]["chunk_role"] == "parent"]
    child_chunks = [chunk for chunk in chunks if chunk["metadata"]["chunk_role"] == "child"]
    assert parent_chunks
    assert child_chunks
    assert child_chunks[0]["parent_chunk_id"] in {chunk["id"] for chunk in parent_chunks}

    search_response = client.post(
        "/api/knowledge/search",
        headers=headers,
        json={"query": "space-token", "knowledge_space_id": space["id"], "top_k": 5},
    )
    assert search_response.status_code == 200
    result = search_response.json()["data"]["items"][0]
    matched_child = next(chunk for chunk in child_chunks if "space-token" in chunk["content"])
    assert result["source"]["parent_chunk_id"] == matched_child["parent_chunk_id"]
    assert "失败排查" in result["source"]["parent_content"]


def test_regex_section_chunk_strategy_splits_by_structural_markers():
    app.state.store.reset()
    headers = auth_headers()
    space = create_space(headers)
    response = client.post(
        "/api/knowledge/documents/upload",
        headers=headers,
        json={
            "knowledge_space_id": space["id"],
            "title": "正则分块手册",
            "filename": "regex-runbook.md",
            "mime_type": "text/markdown",
            "content_base64": base64.b64encode(
                (
                    "# 接入流程\n"
                    "setup-regex-token 保留在第一段。\n\n"
                    "---\n"
                    "第2章 风险排查\n"
                    "risk-regex-token 保留在第二段。"
                ).encode()
            ).decode("ascii"),
            "doc_type": "runbook",
            "parser_engine": "markdown",
            "chunk_strategy": "regex_section",
        },
    )
    assert response.status_code == 200
    uploaded = response.json()["data"]
    run_response = client.post(
        f"/api/knowledge/import-jobs/{uploaded['import_job']['id']}/run",
        headers=headers,
    )
    assert run_response.status_code == 200

    chunk_sets = client.get(
        f"/api/knowledge/documents/{uploaded['document']['id']}/chunk-sets",
        headers=headers,
    ).json()["data"]["items"]
    assert chunk_sets[0]["chunk_strategy"] == "regex_section"

    chunks = client.get(
        f"/api/knowledge/documents/{uploaded['document']['id']}/chunks",
        headers=headers,
    ).json()["data"]["items"]
    regex_chunks = [
        chunk for chunk in chunks if chunk["metadata"]["chunk_role"] == "regex_section"
    ]
    assert len(regex_chunks) >= 2
    first_chunk = next(chunk for chunk in regex_chunks if "setup-regex-token" in chunk["content"])
    second_chunk = next(chunk for chunk in regex_chunks if "risk-regex-token" in chunk["content"])
    assert first_chunk["metadata"]["section_title"] == "# 接入流程"
    assert first_chunk["metadata"]["split_pattern"] == "regex_separator"
    assert second_chunk["metadata"]["section_title"] == "第2章 风险排查"


def test_ocr_json_import_writes_structured_asset_and_page_chunk_metadata():
    app.state.store.reset()
    headers = auth_headers()
    space = create_space(headers)
    ocr_payload = {
        "pages": [
            {
                "page_number": 2,
                "text": "ocr-page-token 需要查看第二页截图。",
                "images": [{"id": "image-2-a"}],
                "tables": [{"id": "table-2-a"}],
            },
            {"page_number": 3, "text": "第三页是补充说明。"},
        ],
    }
    response = client.post(
        "/api/knowledge/documents/upload",
        headers=headers,
        json={
            "knowledge_space_id": space["id"],
            "title": "OCR 解析资产",
            "filename": "ocr-result.json",
            "mime_type": "application/json",
            "content_base64": base64.b64encode(
                json.dumps(ocr_payload, ensure_ascii=False).encode(),
            ).decode("ascii"),
            "doc_type": "ocr",
            "parser_engine": "ocr_json",
            "chunk_strategy": "parent_child",
        },
    )
    assert response.status_code == 200
    uploaded = response.json()["data"]
    run_response = client.post(
        f"/api/knowledge/import-jobs/{uploaded['import_job']['id']}/run",
        headers=headers,
    )
    assert run_response.status_code == 200

    assets = client.get(
        f"/api/knowledge/documents/{uploaded['document']['id']}/assets",
        headers=headers,
    ).json()["data"]["items"]
    asset_types = [asset["asset_type"] for asset in assets]
    assert asset_types == ["ocr_json", "original", "parsed_markdown"]
    ocr_asset = next(asset for asset in assets if asset["asset_type"] == "ocr_json")
    assert ocr_asset["metadata"]["page_count"] == 2
    assert ocr_asset["metadata"]["image_count"] == 1

    chunks = client.get(
        f"/api/knowledge/documents/{uploaded['document']['id']}/chunks",
        headers=headers,
    ).json()["data"]["items"]
    matched_chunk = next(chunk for chunk in chunks if "ocr-page-token" in chunk["content"])
    assert matched_chunk["metadata"]["source_kind"] == "ocr_page"
    assert matched_chunk["metadata"]["source_asset_type"] == "ocr_json"
    assert matched_chunk["metadata"]["page_number"] == 2
    assert matched_chunk["metadata"]["image_count"] == 1
    assert matched_chunk["metadata"]["image_refs"] == ["image-2-a"]
    assert matched_chunk["metadata"]["table_count"] == 1


def test_import_rerun_reuses_existing_parsed_assets_by_object_key():
    app.state.store.reset()
    headers = auth_headers()
    space = create_space(headers)
    ocr_payload = {"pages": [{"page_number": 4, "text": "rerun-token 保持资产幂等。"}]}
    response = client.post(
        "/api/knowledge/documents/upload",
        headers=headers,
        json={
            "knowledge_space_id": space["id"],
            "title": "OCR 幂等导入",
            "filename": "ocr-idempotent.json",
            "mime_type": "application/json",
            "content_base64": base64.b64encode(
                json.dumps(ocr_payload, ensure_ascii=False).encode(),
            ).decode("ascii"),
            "doc_type": "ocr",
            "parser_engine": "ocr_json",
            "chunk_strategy": "parent_child",
        },
    )
    assert response.status_code == 200
    uploaded = response.json()["data"]
    job_id = uploaded["import_job"]["id"]
    first_run = client.post(f"/api/knowledge/import-jobs/{job_id}/run", headers=headers)
    assert first_run.status_code == 200

    # Simulate a repository recovery after a partial worker failure where the same
    # import job is made runnable again while parsed assets already exist.
    app.state.store.knowledge_import_jobs[job_id]["status"] = "queued"
    second_run = client.post(f"/api/knowledge/import-jobs/{job_id}/run", headers=headers)
    assert second_run.status_code == 200

    assets = client.get(
        f"/api/knowledge/documents/{uploaded['document']['id']}/assets",
        headers=headers,
    ).json()["data"]["items"]
    asset_types = [asset["asset_type"] for asset in assets]
    assert asset_types.count("ocr_json") == 1
    assert asset_types.count("parsed_markdown") == 1
    assert asset_types.count("original") == 1


def test_table_json_import_writes_table_asset_and_table_chunk_metadata():
    app.state.store.reset()
    headers = auth_headers()
    space = create_space(headers)
    table_payload = {
        "tables": [
            {
                "name": "风险表",
                "rows": [
                    {"risk": "timeout", "owner": "SRE"},
                    {"risk": "capacity", "owner": "RD"},
                ],
            }
        ]
    }
    response = client.post(
        "/api/knowledge/documents/upload",
        headers=headers,
        json={
            "knowledge_space_id": space["id"],
            "title": "表格解析资产",
            "filename": "tables.json",
            "mime_type": "application/json",
            "content_base64": base64.b64encode(
                json.dumps(table_payload, ensure_ascii=False).encode(),
            ).decode("ascii"),
            "doc_type": "table",
            "parser_engine": "table_json",
            "chunk_strategy": "simple_text",
        },
    )
    assert response.status_code == 200
    uploaded = response.json()["data"]
    run_response = client.post(
        f"/api/knowledge/import-jobs/{uploaded['import_job']['id']}/run",
        headers=headers,
    )
    assert run_response.status_code == 200

    assets = client.get(
        f"/api/knowledge/documents/{uploaded['document']['id']}/assets",
        headers=headers,
    ).json()["data"]["items"]
    asset_types = [asset["asset_type"] for asset in assets]
    assert asset_types == ["original", "parsed_markdown", "table_json"]
    table_asset = next(asset for asset in assets if asset["asset_type"] == "table_json")
    assert table_asset["metadata"]["table_count"] == 1
    assert table_asset["metadata"]["columns"] == ["owner", "risk"]

    chunks = client.get(
        f"/api/knowledge/documents/{uploaded['document']['id']}/chunks",
        headers=headers,
    ).json()["data"]["items"]
    matched_chunk = next(chunk for chunk in chunks if "timeout" in chunk["content"])
    assert matched_chunk["metadata"]["source_kind"] == "table"
    assert matched_chunk["metadata"]["source_asset_type"] == "table_json"
    assert matched_chunk["metadata"]["table_index"] == 1
    assert matched_chunk["metadata"]["columns"] == ["owner", "risk"]


def test_import_job_retry_and_cancel_do_not_duplicate_documents():
    app.state.store.reset()
    headers = auth_headers()
    space = create_space(headers)

    bad_upload = client.post(
        "/api/knowledge/documents/upload",
        headers=headers,
        json={
            "knowledge_space_id": space["id"],
            "title": "坏 OCR",
            "filename": "bad-ocr.json",
            "mime_type": "application/json",
            "content_base64": base64.b64encode(b"{bad json").decode("ascii"),
            "doc_type": "ocr",
            "parser_engine": "ocr_json",
            "chunk_strategy": "simple_text",
        },
    )
    assert bad_upload.status_code == 200
    bad_payload = bad_upload.json()["data"]
    job_id = bad_payload["import_job"]["id"]
    document_id = bad_payload["document"]["id"]

    first_run = client.post(f"/api/knowledge/import-jobs/{job_id}/run", headers=headers)
    assert first_run.status_code == 200
    assert first_run.json()["data"]["import_job"]["status"] == "failed"

    retry_response = client.post(f"/api/knowledge/import-jobs/{job_id}/retry", headers=headers)
    assert retry_response.status_code == 200
    retry_payload = retry_response.json()["data"]
    assert retry_payload["import_job"]["status"] == "queued"
    assert retry_payload["import_job"]["progress"] == 0
    assert retry_payload["document"]["id"] == document_id

    documents = client.get(
        f"/api/knowledge/documents?knowledge_space_id={space['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert [item["id"] for item in documents] == [document_id]

    cancel_upload = upload_markdown(
        headers,
        space_id=space["id"],
        title="待取消导入",
        content="# 待取消\n\n取消前不应生成 chunk。",
    )
    cancel_job_id = cancel_upload["import_job"]["id"]
    cancel_response = client.post(
        f"/api/knowledge/import-jobs/{cancel_job_id}/cancel",
        headers=headers,
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["data"]["import_job"]["status"] == "cancelled"

    cancelled_run = client.post(f"/api/knowledge/import-jobs/{cancel_job_id}/run", headers=headers)
    assert cancelled_run.status_code == 409
    assert cancelled_run.json()["detail"]["code"] == "IMPORT_JOB_STATE_INVALID"


def test_chunk_set_reparse_and_activation_rolls_back_active_version():
    app.state.store.reset()
    headers = auth_headers()
    space = create_space(headers)
    uploaded = upload_markdown(headers, space_id=space["id"])
    document_id = uploaded["document"]["id"]
    job_id = uploaded["import_job"]["id"]

    first_run = client.post(f"/api/knowledge/import-jobs/{job_id}/run", headers=headers)
    assert first_run.status_code == 200
    first_chunk_set_id = first_run.json()["data"]["document"]["active_chunk_set_id"]
    app.state.store.knowledge_chunk_sets[first_chunk_set_id] = {
        **app.state.store.knowledge_chunk_sets[first_chunk_set_id],
        "index_status": "vector_indexed",
        "vector_index_error": None,
        "embedding_model": "text-embedding-3-small",
        "embedding_dimension": 1536,
    }

    reparse_response = client.post(
        f"/api/knowledge/documents/{document_id}/reparse",
        headers=headers,
        json={"parser_engine": "markdown", "chunk_strategy": "simple_text"},
    )
    assert reparse_response.status_code == 200
    reparse_job_id = reparse_response.json()["data"]["import_job"]["id"]
    second_run = client.post(f"/api/knowledge/import-jobs/{reparse_job_id}/run", headers=headers)
    assert second_run.status_code == 200
    second_chunk_set_id = second_run.json()["data"]["document"]["active_chunk_set_id"]
    assert second_chunk_set_id != first_chunk_set_id

    chunk_sets = client.get(
        f"/api/knowledge/documents/{document_id}/chunk-sets",
        headers=headers,
    ).json()["data"]["items"]
    assert [item["status"] for item in chunk_sets] == ["active", "archived"]

    activate_response = client.post(
        f"/api/knowledge/documents/{document_id}/chunk-sets/{first_chunk_set_id}/activate",
        headers=headers,
    )
    assert activate_response.status_code == 200
    activated_document = activate_response.json()["data"]["document"]
    assert activated_document["active_chunk_set_id"] == first_chunk_set_id
    assert activated_document["index_status"] == "vector_indexed"


def test_failed_reparse_keeps_previous_active_chunk_set(monkeypatch):
    app.state.store.reset()
    headers = auth_headers()
    space = create_space(headers)
    uploaded = upload_markdown(headers, space_id=space["id"])
    document_id = uploaded["document"]["id"]
    job_id = uploaded["import_job"]["id"]

    first_run = client.post(f"/api/knowledge/import-jobs/{job_id}/run", headers=headers)
    assert first_run.status_code == 200
    first_chunk_set_id = first_run.json()["data"]["document"]["active_chunk_set_id"]

    def fail_indexing(current_store, document):  # type: ignore[no-untyped-def]
        return (
            {
                **document,
                "index_status": "index_failed",
                "index_error": "模拟索引失败",
                "vector_index_error": None,
            },
            [],
        )

    monkeypatch.setattr(
        "app.services.knowledge_management.replace_knowledge_chunks_result",
        fail_indexing,
    )
    reparse_response = client.post(
        f"/api/knowledge/documents/{document_id}/reparse",
        headers=headers,
        json={"parser_engine": "markdown", "chunk_strategy": "simple_text"},
    )
    assert reparse_response.status_code == 200
    reparse_job_id = reparse_response.json()["data"]["import_job"]["id"]

    failed_run = client.post(f"/api/knowledge/import-jobs/{reparse_job_id}/run", headers=headers)

    assert failed_run.status_code == 200
    failed_payload = failed_run.json()["data"]
    assert failed_payload["import_job"]["status"] == "failed"
    assert failed_payload["document"]["active_chunk_set_id"] == first_chunk_set_id
    assert app.state.store.knowledge_chunk_sets[first_chunk_set_id]["status"] == "active"
    failed_chunk_sets = [
        chunk_set
        for chunk_set in app.state.store.knowledge_chunk_sets.values()
        if chunk_set["document_id"] == document_id and chunk_set["status"] == "failed"
    ]
    assert len(failed_chunk_sets) == 1
    assert failed_chunk_sets[0]["index_status"] == "index_failed"


def test_folder_move_archive_and_document_batch_move_are_permission_checked():
    app.state.store.reset()
    headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    space = create_space(headers)
    source_folder = create_folder(headers, space["id"], "待整理")
    target_folder = create_folder(headers, space["id"], "已整理")
    uploaded = upload_markdown(headers, space_id=space["id"], folder_id=source_folder["id"])
    document_id = uploaded["document"]["id"]

    patch_response = client.patch(
        f"/api/knowledge/folders/{target_folder['id']}",
        headers=headers,
        json={"name": "已整理资料", "parent_folder_id": source_folder["id"], "sort_order": 1},
    )
    assert patch_response.status_code == 200
    moved_folder = patch_response.json()["data"]
    assert moved_folder["path"] == "待整理/已整理资料"
    assert moved_folder["sort_order"] == 1

    batch_response = client.post(
        "/api/knowledge/documents/batch-move",
        headers=headers,
        json={"document_ids": [document_id], "folder_id": target_folder["id"]},
    )
    assert batch_response.status_code == 200
    assert batch_response.json()["data"]["updated"] == [document_id]

    updated_document = client.get(
        f"/api/knowledge/documents?knowledge_space_id={space['id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert updated_document["folder_id"] == target_folder["id"]
    assert updated_document["folder_path"] == "待整理/已整理资料"

    archive_response = client.patch(
        f"/api/knowledge/folders/{source_folder['id']}",
        headers=headers,
        json={"status": "archived"},
    )
    assert archive_response.status_code == 200
    folders = client.get(
        f"/api/knowledge/spaces/{space['id']}/folders",
        headers=headers,
    ).json()["data"]["items"]
    folder_ids = [folder["id"] for folder in folders]
    assert source_folder["id"] not in folder_ids
    assert target_folder["id"] not in folder_ids

    create_under_archived = client.post(
        f"/api/knowledge/spaces/{space['id']}/folders",
        headers=headers,
        json={"name": "归档子目录", "parent_folder_id": target_folder["id"]},
    )
    assert create_under_archived.status_code == 409
    assert create_under_archived.json()["detail"]["code"] == "KNOWLEDGE_FOLDER_ARCHIVED"

    move_to_archived_child = client.post(
        "/api/knowledge/documents/batch-move",
        headers=headers,
        json={"document_ids": [document_id], "folder_id": target_folder["id"]},
    )
    assert move_to_archived_child.status_code == 404

    forbidden_batch = client.post(
        "/api/knowledge/documents/batch-move",
        headers=reviewer_headers,
        json={"document_ids": [document_id], "folder_id": None},
    )
    assert forbidden_batch.status_code == 403
