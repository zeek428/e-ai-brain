from test_database_persistence import FakeSnapshotRepository, app, auth_headers, client

from app.core.persistence import PersistentMemoryStore, PostgresRuntimeStore
from app.core.users import MemoryUserRepository
from app.services.model_gateway_config_context import replace_memory_model_gateway_configs
from app.services.model_gateway_logging import model_gateway_log


def test_model_gateway_config_and_logs_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    current_store.model_gateway_configs["model_gateway_config_009"] = {
        "api_key": "sk-db-secret",
        "base_url": "https://llm.example.com/v1",
        "default_chat_model": "gpt-real",
        "default_embedding_model": "text-embedding-real",
        "id": "model_gateway_config_009",
        "is_default": True,
        "max_retries": 2,
        "name": "真实模型网关",
        "provider": "openai_compatible",
        "status": "active",
        "timeout_seconds": 45,
    }
    current_store.model_gateway_logs.append(
        {
            "ai_task_id": "task_002",
            "created_at": "2026-05-31T10:00:00+00:00",
            "error": None,
            "id": "model_log_007",
            "latency_ms": 321,
            "model": "gpt-real",
            "model_gateway_config_id": "model_gateway_config_009",
            "provider": "openai_compatible",
            "purpose": "product_detail_design",
            "status": "succeeded",
            "tokens": {"prompt": 10, "completion": 20, "total": 30},
        }
    )

    current_store.persist()

    assert repository.model_gateway_payload == {
        "model_gateway_configs": {
            "model_gateway_config_009": {
                "api_key": "sk-db-secret",
                "base_url": "https://llm.example.com/v1",
                "default_chat_model": "gpt-real",
                "default_embedding_model": "text-embedding-real",
                "id": "model_gateway_config_009",
                "is_default": True,
                "max_retries": 2,
                "name": "真实模型网关",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 45,
            }
        },
        "model_gateway_logs": [
            {
                "ai_task_id": "task_002",
                "created_at": "2026-05-31T10:00:00+00:00",
                "error": None,
                "id": "model_log_007",
                "latency_ms": 321,
                "model": "gpt-real",
                "model_gateway_config_id": "model_gateway_config_009",
                "provider": "openai_compatible",
                "purpose": "product_detail_design",
                "status": "succeeded",
                "tokens": {"prompt": 10, "completion": 20, "total": 30},
            }
        ],
    }


def test_model_gateway_memory_fallback_helpers_replace_configs_and_append_logs():
    current_store = app.state.store
    current_store.reset()

    replace_memory_model_gateway_configs(
        current_store,
        {
            "model_gateway_config_helper": {
                "api_key": "sk-helper",
                "base_url": "https://helper.example.com/v1",
                "default_chat_model": "helper-chat",
                "id": "model_gateway_config_helper",
                "is_default": True,
                "name": "Helper 网关",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 30,
            }
        },
    )
    log = model_gateway_log(
        current_store,
        config_id="model_gateway_config_helper",
        latency_ms=12,
        model="helper-chat",
        provider="openai_compatible",
        status="succeeded",
        tokens={"prompt": 1, "completion": 2, "total": 3},
    )

    assert list(current_store.model_gateway_configs) == ["model_gateway_config_helper"]
    assert current_store.model_gateway_configs["model_gateway_config_helper"]["api_key"] == (
        "sk-helper"
    )
    assert current_store.model_gateway_logs == [log]



def test_structured_model_gateway_restore_and_sync_counters():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "model_gateway_configs": {
            "model_gateway_config_002": {
                "api_key": "snapshot-secret",
                "base_url": "https://snapshot.example.com/v1",
                "default_chat_model": "snapshot-chat",
                "default_embedding_model": "snapshot-embedding",
                "id": "model_gateway_config_002",
                "is_default": True,
                "max_retries": 1,
                "name": "旧快照模型网关",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 60,
            }
        },
        "model_gateway_logs": [
            {
                "ai_task_id": "task_001",
                "id": "model_log_002",
                "model": "snapshot-chat",
                "provider": "openai_compatible",
                "purpose": "product_detail_design",
                "status": "succeeded",
                "tokens": {},
            }
        ],
    }
    repository.model_gateway_payload = {
        "model_gateway_configs": {
            "model_gateway_config_009": {
                "api_key": "structured-secret",
                "base_url": "https://structured.example.com/v1",
                "default_chat_model": "structured-chat",
                "default_embedding_model": "structured-embedding",
                "id": "model_gateway_config_009",
                "is_default": True,
                "max_retries": 2,
                "name": "结构表模型网关",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 30,
            }
        },
        "model_gateway_logs": [
            {
                "ai_task_id": "task_002",
                "id": "model_log_007",
                "model": "structured-chat",
                "provider": "openai_compatible",
                "purpose": "product_detail_design",
                "status": "succeeded",
                "tokens": {"total": 33},
            }
        ],
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert list(rebuilt_store.model_gateway_configs) == ["model_gateway_config_009"]
    assert rebuilt_store.model_gateway_configs["model_gateway_config_009"]["api_key"] == (
        "structured-secret"
    )
    assert [log["id"] for log in rebuilt_store.model_gateway_logs] == ["model_log_007"]
    assert rebuilt_store.new_id("model_gateway_config") == "model_gateway_config_010"
    assert rebuilt_store.new_id("model_log") == "model_log_008"



def test_model_gateway_config_api_writes_fine_grained_repository_payload():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_empty_postgres_runtime_store() -> PostgresRuntimeStore:
        runtime_store = PostgresRuntimeStore(repository)
        app.state.store = runtime_store
        return runtime_store

    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        config = client.post(
            "/api/system/model-gateway-configs",
            json={
                "api_key": "sk-api-secret",
                "base_url": "https://api.example.com/v1",
                "default_chat_model": "gpt-api",
                "default_embedding_model": "text-embedding-api",
                "is_default": True,
                "name": "API 模型网关",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 30,
            },
            headers=headers,
        ).json()["data"]

        assert config["api_key_configured"] is True
        assert "api_key" not in config
        assert repository.model_gateway_payload is not None
        persisted = repository.model_gateway_payload["model_gateway_configs"][config["id"]]
        assert persisted["api_key"] == "sk-api-secret"
        assert persisted["is_default"] is True
        assert persisted["default_chat_model"] == "gpt-api"
        assert repository.model_gateway_direct_writes == [f"upsert:{config['id']}"]

        use_empty_postgres_runtime_store()
        patched = client.patch(
            f"/api/system/model-gateway-configs/{config['id']}",
            json={
                "default_chat_model": "gpt-api-updated",
                "is_default": False,
                "status": "inactive",
            },
            headers=headers,
        ).json()["data"]
        assert patched["default_chat_model"] == "gpt-api-updated"
        assert patched["status"] == "inactive"
        updated = repository.model_gateway_payload["model_gateway_configs"][config["id"]]
        assert updated["default_chat_model"] == "gpt-api-updated"
        assert updated["status"] == "inactive"
        assert repository.model_gateway_direct_writes == [
            f"upsert:{config['id']}",
            f"upsert:{config['id']}",
        ]

        use_empty_postgres_runtime_store()
        deleted = client.delete(
            f"/api/system/model-gateway-configs/{config['id']}",
            headers=headers,
        ).json()["data"]
        assert deleted == {"deleted": True, "id": config["id"]}
        assert config["id"] not in repository.model_gateway_payload["model_gateway_configs"]
        assert repository.model_gateway_direct_writes == [
            f"upsert:{config['id']}",
            f"upsert:{config['id']}",
            f"delete:{config['id']}",
        ]
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
