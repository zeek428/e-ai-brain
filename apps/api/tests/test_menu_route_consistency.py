from __future__ import annotations

import re
from pathlib import Path

from app.core.repositories.authorization import CompatibilityAuthorizationRepository

ROUTE_PATH_PATTERN = re.compile(r"path:\s*'([^']+)'")

CRITICAL_MENU_PATHS = {
    "assistant.drafts": "/assistant/drafts",
    "code_inspection.reports": "/governance/code-inspections",
    "delivery.rd_executor_policies": "/delivery/rd-executor-policies",
    "diagnostics.execution_traces": "/governance/execution-traces",
    "system.ai_capabilities": "/tasks/ai-capabilities",
    "system.menus": "/system/menus",
    "system.plugins": "/tasks/plugins",
    "system.scheduled_jobs": "/tasks/scheduled-jobs",
    "task.center": "/delivery/rd-tasks",
}


def _frontend_route_paths() -> set[str]:
    route_config = Path(__file__).resolve().parents[2] / "web" / "config" / "routes.ts"
    source = route_config.read_text(encoding="utf-8")
    return {
        match.group(1)
        for match in ROUTE_PATH_PATTERN.finditer(source)
        if match.group(1) != "/*"
    }


def _active_navigable_menus() -> list[dict]:
    repository = CompatibilityAuthorizationRepository()
    return [
        menu
        for menu in repository.menu_resources()
        if menu.get("status") == "active"
        and menu.get("menu_type") in {"group", "page"}
        and menu.get("path")
    ]


def test_active_menu_paths_are_registered_frontend_routes():
    route_paths = _frontend_route_paths()
    missing = [
        f"{menu['code']} -> {menu['path']}"
        for menu in _active_navigable_menus()
        if menu["path"] not in route_paths
    ]

    assert missing == []


def test_critical_menu_paths_do_not_drift_from_current_navigation():
    menus_by_code = {menu["code"]: menu for menu in _active_navigable_menus()}

    for code, expected_path in CRITICAL_MENU_PATHS.items():
        assert menus_by_code[code]["path"] == expected_path
