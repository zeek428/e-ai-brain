import logging

from app.core import listing


def test_list_observability_uses_per_list_p95_target(monkeypatch, caplog):
    monkeypatch.setattr(listing, "perf_counter", lambda: 10.8)
    caplog.set_level(logging.WARNING, logger="app.core.listing")

    payload = listing.add_list_observability(
        {"items": [{"id": "requirement_001"}], "total": 3},
        filters={"status": "planned"},
        list_name="requirements",
        page=1,
        page_size=10,
        sort_by="created_at",
        sort_order="desc",
        started_at=10.0,
    )

    assert payload["performance"]["duration_ms"] == 800
    assert payload["performance"]["p95_target_ms"] == 300
    assert payload["performance"]["slow"] is True
    assert payload["performance"]["slow_threshold_ms"] == 300
    assert "p95_target_ms=300" in caplog.text
    assert '"page": 1' in caplog.text
    assert '"page_size": 10' in caplog.text
    assert '"status": "planned"' in caplog.text
    assert '"sort_by": "created_at"' in caplog.text


def test_management_list_p95_targets_are_explicit():
    expected_targets = {
        "ai_tasks": 300,
        "audit_events": 500,
        "assistant_action_drafts": 400,
        "bugs": 300,
        "code_inspections": 400,
        "devops_operational_metrics": 500,
        "execution_traces": 500,
        "knowledge_documents": 400,
        "model_gateway_configs": 300,
        "product_versions": 300,
        "products": 300,
        "requirements": 300,
        "roles": 300,
        "scheduled_jobs": 400,
        "users": 300,
        "user_insights": 400,
    }

    for list_name, target_ms in expected_targets.items():
        assert listing.list_p95_target_ms(list_name) == target_ms
