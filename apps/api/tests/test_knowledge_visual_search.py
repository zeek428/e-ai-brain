from app.core.store import MemoryStore
from app.services.knowledge_visual_search import visual_search_response


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
