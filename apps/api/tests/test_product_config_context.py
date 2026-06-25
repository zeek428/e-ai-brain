from app.services.product_config_context import record_audit_event, save_requirement_record


class MinimalProductConfigStore:
    def __init__(self) -> None:
        self.audit_events = []
        self.counters = {}

    def new_id(self, prefix: str) -> str:
        next_value = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = next_value
        return f"{prefix}_{next_value:03d}"


def test_save_requirement_record_uses_memory_fallback_collection():
    current_store = MinimalProductConfigStore()
    requirement = {"id": "requirement_001", "title": "Fallback requirement"}

    saved = save_requirement_record(current_store, requirement)

    assert saved is False
    assert current_store.requirements == {"requirement_001": requirement}


def test_record_audit_event_appends_minimal_store_fallback_event():
    current_store = MinimalProductConfigStore()

    event = record_audit_event(
        current_store,
        actor_id="user_admin",
        event_type="product_config.tested",
        payload={"source": "test"},
        subject_id="model_gateway_config_001",
        subject_type="model_gateway_config",
    )

    assert event["id"] == "audit_001"
    assert event["payload"] == {"source": "test"}
    assert current_store.audit_events == [event]
