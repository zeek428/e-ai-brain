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


def test_knowledge_space_folder_asset_upload_and_search_are_permission_filtered():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    viewer_response = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "display_name": "Knowledge Space Reader",
            "password": "reader123",
            "roles": ["viewer"],
            "status": "active",
            "username": "space-reader@example.com",
        },
    )
    assert viewer_response.status_code == 200
    viewer = viewer_response.json()["data"]
    viewer_headers = auth_headers("space-reader@example.com", "reader123")

    space_response = client.post(
        "/api/knowledge/spaces",
        headers=admin_headers,
        json={
            "code": "payments",
            "name": "支付知识空间",
            "description": "支付产品研发资料",
        },
    )
    assert space_response.status_code == 200
    space = space_response.json()["data"]

    member_response = client.put(
        f"/api/knowledge/spaces/{space['id']}/members",
        headers=admin_headers,
        json={"members": [{"user_id": viewer["id"], "space_role": "reader"}]},
    )
    assert member_response.status_code == 200
    assert member_response.json()["data"]["members"][0]["user_id"] == viewer["id"]

    folder_response = client.post(
        f"/api/knowledge/spaces/{space['id']}/folders",
        headers=admin_headers,
        json={"name": "故障手册"},
    )
    assert folder_response.status_code == 200
    folder = folder_response.json()["data"]
    assert folder["knowledge_space_id"] == space["id"]
    assert folder["path"] == "故障手册"

    upload_response = client.post(
        "/api/knowledge/documents/upload",
        headers=admin_headers,
        json={
            "knowledge_space_id": space["id"],
            "folder_id": folder["id"],
            "title": "支付失败排查",
            "filename": "payment-runbook.md",
            "mime_type": "text/markdown",
            "content_base64": base64.b64encode(
                "支付失败排查步骤。space-secret-token".encode()
            ).decode("ascii"),
            "doc_type": "runbook",
            "tags": ["payment", "runbook"],
        },
    )
    assert upload_response.status_code == 200
    document = upload_response.json()["data"]["document"]
    assert document["knowledge_space_id"] == space["id"]
    assert document["folder_id"] == folder["id"]
    assert document["source_asset_id"].startswith("knowledge_asset_")
    assert document["active_chunk_set_id"].startswith("knowledge_chunk_set_")
    assert document["index_status"] in {"text_indexed", "vector_indexed"}
    assert upload_response.json()["data"]["asset"]["asset_type"] == "original"
    assert upload_response.json()["data"]["import_job"]["status"] == "completed"

    viewer_documents = client.get(
        f"/api/knowledge/documents?knowledge_space_id={space['id']}",
        headers=viewer_headers,
    ).json()["data"]["items"]
    assert [item["id"] for item in viewer_documents] == [document["id"]]
    assert viewer_documents[0]["folder_path"] == "故障手册"

    reviewer_documents = client.get(
        f"/api/knowledge/documents?knowledge_space_id={space['id']}",
        headers=reviewer_headers,
    ).json()["data"]["items"]
    assert reviewer_documents == []

    viewer_results = client.post(
        "/api/knowledge/search",
        headers=viewer_headers,
        json={"query": "space-secret-token", "knowledge_space_id": space["id"], "top_k": 5},
    ).json()["data"]["items"]
    assert [item["document_id"] for item in viewer_results] == [document["id"]]
    assert viewer_results[0]["source"]["knowledge_space_id"] == space["id"]
    assert viewer_results[0]["source"]["folder_id"] == folder["id"]
    assert viewer_results[0]["source"]["asset_id"] == document["source_asset_id"]

    reviewer_results = client.post(
        "/api/knowledge/search",
        headers=reviewer_headers,
        json={"query": "space-secret-token", "knowledge_space_id": space["id"], "top_k": 5},
    ).json()["data"]["items"]
    assert reviewer_results == []

    asset_preview = client.get(
        f"/api/knowledge/assets/{document['source_asset_id']}/preview",
        headers=viewer_headers,
    )
    assert asset_preview.status_code == 200
    assert asset_preview.json()["data"]["content"] == "支付失败排查步骤。space-secret-token"

    forbidden_preview = client.get(
        f"/api/knowledge/assets/{document['source_asset_id']}/preview",
        headers=reviewer_headers,
    )
    assert forbidden_preview.status_code == 403
    assert forbidden_preview.json()["detail"]["code"] == "FORBIDDEN"
