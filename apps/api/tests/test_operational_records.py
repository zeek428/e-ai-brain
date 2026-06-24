from app.services.operational_records import record_audit_event


class MinimalAuditStore:
    def __init__(self) -> None:
        self.audit_events = []
        self.counters = {}

    def new_id(self, prefix: str) -> str:
        next_value = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = next_value
        return f"{prefix}_{next_value:03d}"


def test_record_audit_event_appends_minimal_store_fallback_event():
    current_store = MinimalAuditStore()

    event = record_audit_event(
        current_store,
        actor_id="user_admin",
        event_type="operational.created",
        payload={"source": "test"},
        subject_id="operational_001",
        subject_type="operational",
    )

    assert event["id"] == "audit_event_001"
    assert event["payload"] == {"source": "test"}
    assert current_store.audit_events == [event]
