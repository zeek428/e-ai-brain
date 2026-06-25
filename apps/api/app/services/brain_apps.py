from __future__ import annotations

from typing import Any


def brain_app_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    if getattr(repository, "load_brain_apps", None) is not None:
        return repository
    return None


def brain_app_rows_from_repository(repository: Any) -> dict[str, dict[str, Any]]:
    payload = repository.load_brain_apps() or {}
    return {
        str(item_id): dict(item)
        for item_id, item in payload.get("brain_apps", {}).items()
    }


def brain_app_rows_from_memory(current_store: Any) -> dict[str, dict[str, Any]]:
    rows = getattr(current_store, "brain_apps", {})
    return rows if isinstance(rows, dict) else {}


def brain_app_rows(current_store: Any) -> dict[str, dict[str, Any]]:
    repository = brain_app_query_repository(current_store)
    if repository is not None:
        return brain_app_rows_from_repository(repository)
    return brain_app_rows_from_memory(current_store)


def find_brain_app(
    brain_apps: dict[str, dict[str, Any]],
    brain_app_id: str,
) -> dict[str, Any] | None:
    brain_app = brain_apps.get(brain_app_id)
    if brain_app is not None:
        return brain_app
    return next(
        (
            item
            for item in brain_apps.values()
            if item["id"] == brain_app_id or item["code"] == brain_app_id
        ),
        None,
    )
