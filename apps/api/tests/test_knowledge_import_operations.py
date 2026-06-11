from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


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
    assert activate_response.json()["data"]["document"]["active_chunk_set_id"] == first_chunk_set_id


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
    assert source_folder["id"] not in [folder["id"] for folder in folders]

    forbidden_batch = client.post(
        "/api/knowledge/documents/batch-move",
        headers=reviewer_headers,
        json={"document_ids": [document_id], "folder_id": None},
    )
    assert forbidden_batch.status_code == 403
