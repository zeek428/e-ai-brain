from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


class FakeMultimodalProvider:
    def process(self, *, content, filename, mime_type, profile):
        assert content.startswith(b"\x89PNG")
        assert filename == "architecture.png"
        assert mime_type == "image/png"
        assert profile["provider_type"] == "multimodal_gateway"
        return {
            "pages": [
                {
                    "page_number": 1,
                    "text": "发布架构说明",
                    "blocks": [
                        {
                            "bounding_box": [20, 30, 600, 420],
                            "confidence": 0.97,
                            "modality": "image",
                            "text": "architecture topology shows gateway, api and postgres",
                        },
                        {
                            "bounding_box": [20, 450, 700, 700],
                            "modality": "table",
                            "table": {
                                "columns": ["service", "owner"],
                                "rows": [
                                    {"owner": "platform", "service": "api"},
                                    {"owner": "dba", "service": "postgres"},
                                ],
                            },
                        },
                    ],
                }
            ],
            "provider_metadata": {
                "model": "fake-vision-v1",
                "request_id": "provider-request-001",
            },
        }


def test_multimodal_processing_versions_search_feedback_and_staleness(monkeypatch):
    monkeypatch.setattr(
        "app.services.knowledge_multimodal.resolve_knowledge_processing_provider",
        lambda profile: FakeMultimodalProvider(),
    )
    app.state.store.reset()
    headers = auth_headers()
    space = client.post(
        "/api/knowledge/spaces",
        headers=headers,
        json={"code": "multimodal", "name": "多模态知识"},
    ).json()["data"]

    profile_response = client.post(
        "/api/knowledge/processing-profiles",
        headers=headers,
        json={
            "capabilities": ["ocr", "layout", "table", "image_embedding"],
            "credential_ref": "env:MULTIMODAL_GATEWAY_TOKEN",
            "name": "企业视觉解析",
            "provider_config": {
                "endpoint_url": "https://vision.example.com/process",
                "stale_after_days": 90,
            },
            "provider_type": "multimodal_gateway",
        },
    )
    assert profile_response.status_code == 200, profile_response.text
    profile = profile_response.json()["data"]
    assert profile["version"] == 1

    upload_response = client.post(
        "/api/knowledge/documents/upload",
        headers=headers,
        json={
            "chunk_strategy": "simple_text",
            "content_base64": base64.b64encode(b"\x89PNG\r\n\x1a\nimage-bytes").decode(),
            "doc_type": "architecture",
            "filename": "architecture.png",
            "knowledge_space_id": space["id"],
            "mime_type": "image/png",
            "parser_engine": "multimodal",
            "processing_profile_id": profile["id"],
            "title": "发布架构图",
        },
    )
    assert upload_response.status_code == 200, upload_response.text
    uploaded = upload_response.json()["data"]
    document_id = uploaded["document"]["id"]
    version_id = uploaded["document_version"]["id"]
    assert uploaded["document_version"]["status"] == "processing"
    assert uploaded["asset"]["document_version_id"] == version_id
    assert uploaded["import_job"]["document_version_id"] == version_id

    run_response = client.post(
        f"/api/knowledge/import-jobs/{uploaded['import_job']['id']}/run",
        headers=headers,
    )
    assert run_response.status_code == 200, run_response.text
    processed = run_response.json()["data"]
    assert processed["document"]["active_document_version_id"] == version_id
    assert processed["document_version"]["status"] == "active"
    assert processed["document_version"]["processing_profile_id"] == profile["id"]

    assets = client.get(
        f"/api/knowledge/documents/{document_id}/assets",
        headers=headers,
    ).json()["data"]["items"]
    assert {asset["asset_type"] for asset in assets} >= {
        "layout_json",
        "ocr_json",
        "original",
        "parsed_markdown",
        "table_json",
    }
    assert all(asset["document_version_id"] == version_id for asset in assets)
    layout_asset = next(asset for asset in assets if asset["asset_type"] == "layout_json")
    assert layout_asset["page_number"] == 1
    assert layout_asset["provider_metadata"]["model"] == "fake-vision-v1"

    chunks = client.get(
        f"/api/knowledge/documents/{document_id}/chunks",
        headers=headers,
    ).json()["data"]["items"]
    assert {chunk["modality"] for chunk in chunks} >= {"image", "table", "text"}
    assert {chunk["document_version_id"] for chunk in chunks} == {version_id}

    search_response = client.post(
        "/api/knowledge/search",
        headers=headers,
        json={
            "knowledge_space_id": space["id"],
            "query": "architecture topology",
            "top_k": 5,
        },
    )
    assert search_response.status_code == 200
    search_data = search_response.json()["data"]
    hit = search_data["items"][0]
    assert hit["source"]["document_version_id"] == version_id
    assert hit["source"]["modality"] == "image"
    assert hit["source"]["page_number"] == 1
    assert hit["source"]["freshness_status"] == "fresh"

    feedback_response = client.post(
        "/api/knowledge/quality/feedback",
        headers=headers,
        json={
            "citation_chunk_id": hit["chunk_id"],
            "citation_document_id": document_id,
            "feedback_comment": "该架构图已经过期",
            "feedback_value": "outdated",
            "related_event_id": search_data["metrics"]["quality_event_id"],
        },
    )
    assert feedback_response.status_code == 200, feedback_response.text
    feedback = feedback_response.json()["data"]
    assert feedback["citation_feedback_id"].startswith("knowledge_citation_feedback_")
    assert feedback["document_version_id"] == version_id

    feedback_items = client.get(
        f"/api/knowledge/documents/{document_id}/citation-feedback",
        headers=headers,
    ).json()["data"]["items"]
    assert feedback_items[0]["feedback_value"] == "outdated"
    assert feedback_items[0]["document_version_id"] == version_id

    reparse_response = client.post(
        f"/api/knowledge/documents/{document_id}/reparse",
        headers=headers,
        json={
            "expires_in_days": 1,
            "parser_engine": "multimodal",
            "processing_profile_id": profile["id"],
        },
    )
    assert reparse_response.status_code == 200, reparse_response.text
    reparse = reparse_response.json()["data"]
    second_version_id = reparse["document_version"]["id"]
    assert reparse["document_version"]["version"] == 2

    second_run = client.post(
        f"/api/knowledge/import-jobs/{reparse['import_job']['id']}/run",
        headers=headers,
    )
    assert second_run.status_code == 200
    assert second_run.json()["data"]["document_version"]["id"] == second_version_id

    versions = client.get(
        f"/api/knowledge/documents/{document_id}/versions",
        headers=headers,
    ).json()["data"]["items"]
    assert [(item["version"], item["status"]) for item in versions] == [
        (2, "active"),
        (1, "superseded"),
    ]

    app.state.store.knowledge_document_versions[second_version_id]["expires_at"] = (
        datetime.now(UTC) - timedelta(minutes=1)
    ).isoformat()
    stale_scan = client.post("/api/knowledge/staleness/scan", headers=headers)
    assert stale_scan.status_code == 200
    assert stale_scan.json()["data"]["expired_count"] == 1
    stale_items = client.get(
        f"/api/knowledge/staleness?knowledge_space_id={space['id']}",
        headers=headers,
    ).json()["data"]
    assert stale_items["summary"]["expired"] == 1
    assert stale_items["items"][0]["freshness_status"] == "expired"


def test_processing_profile_list_never_resolves_or_exposes_credentials(monkeypatch):
    app.state.store.reset()
    headers = auth_headers()
    monkeypatch.setenv("VISION_PROFILE_SECRET", "must-not-be-returned")

    created = client.post(
        "/api/knowledge/processing-profiles",
        headers=headers,
        json={
            "capabilities": ["ocr"],
            "credential_ref": "env:VISION_PROFILE_SECRET",
            "name": "OCR",
            "provider_config": {"endpoint_url": "https://vision.example.com/process"},
            "provider_type": "http",
        },
    )
    assert created.status_code == 200

    listed = client.get("/api/knowledge/processing-profiles", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["data"]["items"][0]["credential_ref"] == "env:VISION_PROFILE_SECRET"
    assert "must-not-be-returned" not in listed.text

    rejected = client.post(
        "/api/knowledge/processing-profiles",
        headers=headers,
        json={
            "capabilities": ["ocr"],
            "name": "Bad OCR",
            "provider_config": {
                "endpoint_url": "https://vision.example.com/process",
                "token": "must-not-be-persisted",
            },
            "provider_type": "http",
        },
    )
    assert rejected.status_code == 400
    assert "must-not-be-persisted" not in str(app.state.store.knowledge_processing_profiles)
