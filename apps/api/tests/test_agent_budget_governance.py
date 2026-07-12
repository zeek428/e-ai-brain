from app.core.store import MemoryStore
from app.services.agent_budget_governance import (
    evaluate_agent_circuit_breaker,
    reserve_agent_budget,
    settle_agent_budget,
)


def test_budget_is_reserved_then_settled_without_overrun() -> None:
    store = MemoryStore()
    ledger = reserve_agent_budget(store, ai_task_id="task_001", cost_budget=2.5, token_budget=100)

    settled = settle_agent_budget(
        store,
        ledger_id=ledger["id"],
        cost_used=4.0,
        token_used=120,
    )

    assert settled["cost_settled"] == 2.5
    assert settled["token_settled"] == 100


def test_repeated_failure_fingerprint_opens_circuit() -> None:
    assert (
        evaluate_agent_circuit_breaker(
            [{"failure_fingerprint": "test_failed"}, {"failure_fingerprint": "test_failed"}]
        )
        == "AGENT_LOOP_CIRCUIT_OPEN"
    )
