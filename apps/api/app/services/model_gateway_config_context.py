from __future__ import annotations

from typing import Any

from app.services.model_gateway_embeddings import embedding_connection_mode


class ModelGatewayRequestContext:
    def __init__(self, repository: Any) -> None:
        self.repository = repository
        self.model_gateway_configs: dict[str, dict[str, Any]] = {}
        self.model_gateway_logs: list[dict[str, Any]] = []
        self.audit_events: list[dict[str, Any]] = []
        self.counters: dict[str, int] = {}

    def new_id(self, prefix: str) -> str:
        next_id = getattr(self.repository, "next_id", None)
        if callable(next_id):
            allocated_id = next_id(prefix)
            suffix = allocated_id.removeprefix(f"{prefix}_")
            if suffix.isdigit():
                self.counters[prefix] = max(self.counters.get(prefix, 0), int(suffix))
            return allocated_id
        next_value = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = next_value
        return f"{prefix}_{next_value:03d}"


def runtime_repository(current_store: Any) -> Any | None:
    return getattr(current_store, "repository", None)


def model_gateway_query_repository(current_store: Any) -> Any | None:
    repository = runtime_repository(current_store)
    if repository is None:
        return None
    required_methods = [
        "list_model_gateway_configs",
        "list_model_gateway_logs",
    ]
    if all(getattr(repository, method_name, None) is not None for method_name in required_methods):
        return repository
    return None


def model_gateway_config_write_repository(current_store: Any) -> Any | None:
    repository = runtime_repository(current_store)
    if repository is None:
        return None
    required_methods = [
        "delete_model_gateway_config_record",
        "get_model_gateway_config",
        "upsert_model_gateway_config_record",
    ]
    if all(callable(getattr(repository, method_name, None)) for method_name in required_methods):
        return repository
    return None


def model_gateway_source_store(repository: Any) -> ModelGatewayRequestContext:
    source_store = ModelGatewayRequestContext(repository)
    source_store.model_gateway_configs = {
        str(item["id"]): dict(item)
        for item in repository.list_model_gateway_configs()
        if item.get("id") is not None
    }
    source_store.model_gateway_logs = [
        dict(item) for item in repository.list_model_gateway_logs()
    ]
    return source_store


def model_gateway_write_store(current_store: Any) -> Any:
    repository = model_gateway_query_repository(current_store)
    if repository is None:
        return current_store
    return model_gateway_source_store(repository)


def save_model_gateway_records(
    current_store: Any,
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    save_model_gateway_payload(
        current_store,
        configs=current_store.model_gateway_configs,
        logs=current_store.model_gateway_logs,
        audit_event=audit_event,
    )


def save_model_gateway_payload(
    current_store: Any,
    *,
    configs: dict[str, dict[str, Any]],
    logs: list[dict[str, Any]],
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = runtime_repository(current_store)
    save_records = getattr(repository, "save_model_gateway_records", None)
    if save_records is not None:
        save_records(
            {
                "model_gateway_configs": configs,
                "model_gateway_logs": logs,
            },
            audit_event=audit_event,
        )


def get_model_gateway_config_record(current_store: Any, config_id: str) -> dict[str, Any] | None:
    repository = model_gateway_config_write_repository(current_store)
    if repository is not None:
        config = repository.get_model_gateway_config(config_id)
        return dict(config) if config is not None else None
    config = current_store.model_gateway_configs.get(config_id)
    return dict(config) if config is not None else None


def replace_memory_model_gateway_configs(
    current_store: Any,
    configs: dict[str, dict[str, Any]],
) -> None:
    if runtime_repository(current_store) is None:
        current_store.model_gateway_configs = configs


def save_model_gateway_config_record(
    current_store: Any,
    config: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> bool:
    repository = model_gateway_config_write_repository(current_store)
    if repository is None:
        return False
    repository.upsert_model_gateway_config_record(config, audit_event=audit_event)
    return True


def delete_model_gateway_config_record(
    current_store: Any,
    config_id: str,
    *,
    audit_event: dict[str, Any] | None = None,
) -> bool:
    repository = model_gateway_config_write_repository(current_store)
    if repository is None:
        return False
    repository.delete_model_gateway_config_record(config_id, audit_event=audit_event)
    return True


def public_model_gateway_config(config: dict[str, Any]) -> dict[str, Any]:
    public_config = {
        key: value
        for key, value in config.items()
        if key not in {"api_key", "embedding_api_key"}
    }
    api_key = config.get("api_key")
    embedding_api_key = config.get("embedding_api_key")
    public_config["api_key_configured"] = bool(api_key)
    public_config["embedding_api_key_configured"] = bool(embedding_api_key)
    public_config["embedding_connection_mode"] = embedding_connection_mode(config)
    public_config.setdefault("default_embedding_model", None)
    return public_config


def model_gateway_configs_after_default(
    configs: dict[str, dict[str, Any]],
    *,
    config_id: str,
    is_default: bool,
) -> dict[str, dict[str, Any]]:
    if not is_default:
        return configs
    return {
        item_id: {**item, "is_default": item_id == config_id}
        for item_id, item in configs.items()
    }


def default_model_gateway_config(current_store: Any) -> dict[str, Any] | None:
    for item in current_store.model_gateway_configs.values():
        if item.get("is_default") and item.get("status") == "active":
            return item
    return None
