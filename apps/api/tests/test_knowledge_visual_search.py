from app.core.store import MemoryStore
from app.services.knowledge_visual_search import (
    visual_search_response,
    visual_search_with_image_response,
)


def test_visual_search_never_returns_hidden_product_asset() -> None:
    store = MemoryStore()
    store.knowledge_visual_embeddings = {
        "visible": {
            "asset_id": "asset_visible",
            "document_id": "doc_visible",
            "embedding": [1.0, 0.0],
            "product_id": "product_001",
        },
        "hidden": {
            "asset_id": "asset_hidden",
            "document_id": "doc_hidden",
            "embedding": [1.0, 0.0],
            "product_id": "product_002",
        },
    }
    store.knowledge_documents = {
        "doc_visible": {
            "id": "doc_visible",
            "index_status": "indexed",
            "permission_roles": ["developer"],
            "product_id": "product_001",
        },
        "doc_hidden": {
            "id": "doc_hidden",
            "index_status": "indexed",
            "permission_roles": ["developer"],
            "product_id": "product_002",
        },
    }
    user = {
        "permissions": [],
        "roles": ["developer"],
        "scope_summary": [
            {"access_level": "read", "scope_id": "product_001", "scope_type": "product"}
        ],
    }

    result = visual_search_response(current_store=store, query_embedding=[1.0, 0.0], user=user)

    assert result["items"] == [
        {
            "asset_id": "asset_visible",
            "bounding_box": None,
            "document_id": "doc_visible",
            "page_number": None,
            "score": 1.0,
        }
    ]


def test_visual_search_generates_query_embedding_from_image_profile(monkeypatch) -> None:
    store = MemoryStore()
    store.knowledge_processing_profiles = {
        "profile_001": {
            "id": "profile_001",
            "capabilities": ["image_embedding"],
            "provider_type": "multimodal_gateway",
            "status": "active",
        }
    }
    store.knowledge_visual_embeddings = {
        "visible": {
            "asset_id": "asset_visible",
            "document_id": "doc_visible",
            "embedding": [1.0, 0.0],
        }
    }
    store.knowledge_documents = {
        "doc_visible": {
            "id": "doc_visible",
            "index_status": "indexed",
            "permission_roles": ["developer"],
        }
    }

    class FakeProvider:
        def process(self, **_kwargs):
            return {"embedding": [1.0, 0.0]}

    monkeypatch.setattr(
        "app.services.knowledge_visual_search.resolve_knowledge_processing_provider",
        lambda _profile: FakeProvider(),
    )

    result = visual_search_with_image_response(
        current_store=store,
        content=b"image-bytes",
        filename="query.png",
        mime_type="image/png",
        processing_profile_id="profile_001",
        user={"permissions": [], "roles": ["admin"], "scope_summary": []},
    )

    assert result["query_profile_id"] == "profile_001"
    assert result["items"][0]["asset_id"] == "asset_visible"
