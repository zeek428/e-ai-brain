from __future__ import annotations

from types import SimpleNamespace

from app.services.dashboard_cache import (
    dashboard_cache_entry_metadata,
    dashboard_cache_key,
    dashboard_cache_store,
    get_dashboard_cache_entry,
    set_dashboard_cache_entry,
)


def test_dashboard_cache_store_initializes_missing_state_cache():
    state = SimpleNamespace()

    cache = dashboard_cache_store(state)

    assert cache == {}
    assert state.dashboard_cache is cache


def test_dashboard_cache_entry_round_trips_and_exposes_metadata():
    cache = {}
    repository = object()
    user = {"roles": ["viewer", "admin"]}
    key = dashboard_cache_key(
        product_id="product_001",
        repository=repository,
        time_range="7d",
        user=user,
    )

    entry = set_dashboard_cache_entry(
        cache,
        key,
        {"summary": {"requirements": 2}},
        ttl_seconds=30,
    )
    cached = get_dashboard_cache_entry(cache, key, ttl_seconds=30)
    metadata = dashboard_cache_entry_metadata(
        cache_hit=True,
        default_ttl_seconds=30,
        duration_ms=12,
        entry=entry,
        slow_threshold_ms=500,
    )

    assert cached is entry
    assert key[3] == ("admin", "viewer")
    assert metadata["dashboard_cache"]["cache_hit"] is True
    assert metadata["dashboard_cache"]["cache_enabled"] is True
    assert metadata["dashboard_cache"]["duration_ms"] == 12
    assert metadata["dashboard_cache"]["slow"] is False


def test_dashboard_cache_entry_expires_and_is_removed():
    cache = {}
    key = ("repo", "product", "all", ("admin",))
    entry = set_dashboard_cache_entry(cache, key, {"summary": {}}, ttl_seconds=30)
    entry["expires_at"] = 0

    assert get_dashboard_cache_entry(cache, key, ttl_seconds=30) is None
    assert key not in cache
