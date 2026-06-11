import inspect
from pathlib import Path

from app.main import app


def _route_for(path: str, method: str):
    routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set())
    ]

    assert len(routes) == 1
    return routes[0]


def test_dashboard_endpoint_is_owned_by_dashboard_router():
    route = _route_for("/api/dashboard/it-team", "GET")
    assert route.endpoint.__module__ == "app.api.routers.dashboard"


def test_auth_endpoints_are_owned_by_auth_router():
    expected_module = "app.api.routers.auth"

    assert _route_for("/api/auth/login", "POST").endpoint.__module__ == expected_module
    assert _route_for("/api/auth/me", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/auth/logout", "POST").endpoint.__module__ == expected_module
    assert _route_for("/api/auth/roles", "GET").endpoint.__module__ == expected_module


def test_platform_status_endpoints_are_owned_by_platform_router():
    expected_module = "app.api.routers.platform"

    assert _route_for("/health", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/long-memory/status", "GET").endpoint.__module__ == expected_module


def test_user_management_endpoints_are_owned_by_users_router():
    expected_module = "app.api.routers.users"

    assert _route_for("/api/users", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/users", "POST").endpoint.__module__ == expected_module
    assert _route_for("/api/users/{user_id}", "PATCH").endpoint.__module__ == expected_module
    assert _route_for("/api/users/{user_id}", "DELETE").endpoint.__module__ == expected_module


def test_system_rbac_endpoints_are_owned_by_system_rbac_router():
    expected_module = "app.api.routers.system_rbac"

    for path, method in [
        ("/api/system/permissions", "GET"),
        ("/api/system/menus", "GET"),
        ("/api/system/roles", "GET"),
        ("/api/system/roles", "POST"),
        ("/api/system/roles/{role_id}", "GET"),
        ("/api/system/roles/{role_id}", "PATCH"),
        ("/api/system/roles/{role_id}/copy", "POST"),
        ("/api/system/roles/{role_id}/disable", "POST"),
        ("/api/system/roles/{role_id}/enable", "POST"),
        ("/api/system/roles/{role_id}/permissions", "PUT"),
        ("/api/system/roles/{role_id}/menus", "PUT"),
        ("/api/system/roles/{role_id}/scopes", "PUT"),
        ("/api/users/{user_id}/permissions", "GET"),
        ("/api/users/{user_id}/roles", "PUT"),
        ("/api/users/{user_id}/scopes", "PUT"),
    ]:
        assert _route_for(path, method).endpoint.__module__ == expected_module


def test_scheduled_ai_job_endpoints_are_owned_by_scheduled_jobs_router():
    expected_module = "app.api.routers.scheduled_jobs"

    for path, method in [
        ("/api/system/ai-skills", "GET"),
        ("/api/system/ai-skills", "POST"),
        ("/api/system/ai-skills/upload", "POST"),
        ("/api/system/ai-skills/{skill_id}", "PATCH"),
        ("/api/system/ai-agents", "GET"),
        ("/api/system/ai-agents", "POST"),
        ("/api/system/ai-agents/{agent_id}", "PATCH"),
        ("/api/system/scheduled-jobs", "GET"),
        ("/api/system/scheduled-jobs", "POST"),
        ("/api/system/scheduled-jobs/{job_id}", "PATCH"),
        ("/api/system/scheduled-jobs/{job_id}/run", "POST"),
        ("/api/system/scheduled-job-runs", "GET"),
        ("/api/system/scheduled-job-runs/{run_id}/cancel", "POST"),
    ]:
        assert _route_for(path, method).endpoint.__module__ == expected_module


def test_code_inspection_endpoints_are_owned_by_code_inspections_router():
    expected_module = "app.api.routers.code_inspections"

    assert _route_for("/api/governance/code-inspections", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for(
        "/api/governance/code-inspections/{report_id}",
        "GET",
    ).endpoint.__module__ == expected_module


def test_product_core_endpoints_are_owned_by_products_router():
    expected_module = "app.api.routers.products"

    assert _route_for("/api/products", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/products", "POST").endpoint.__module__ == expected_module
    assert _route_for("/api/products/{product_id}", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/products/{product_id}", "PATCH").endpoint.__module__ == expected_module
    assert _route_for("/api/products/{product_id}", "DELETE").endpoint.__module__ == expected_module


def test_product_version_endpoints_are_owned_by_product_versions_router():
    expected_module = "app.api.routers.product_versions"

    assert _route_for("/api/product-versions", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/products/{product_id}/versions", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/products/{product_id}/versions", "POST").endpoint.__module__ == (
        expected_module
    )
    advance_status_route = _route_for(
        "/api/product-versions/{version_id}/advance-status",
        "POST",
    )
    assert advance_status_route.endpoint.__module__ == expected_module
    assert _route_for(
        "/api/product-versions/{version_id}/branch-configs",
        "GET",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/product-versions/{version_id}/branch-configs",
        "POST",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/product-version-branch-configs/{branch_config_id}",
        "PATCH",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/product-version-branch-configs/{branch_config_id}",
        "DELETE",
    ).endpoint.__module__ == expected_module
    assert _route_for("/api/product-versions/{version_id}", "PATCH").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/product-versions/{version_id}", "DELETE").endpoint.__module__ == (
        expected_module
    )


def test_product_module_endpoints_are_owned_by_product_modules_router():
    expected_module = "app.api.routers.product_modules"

    assert _route_for("/api/products/{product_id}/modules", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/products/{product_id}/modules", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/product-modules/{module_id}", "PATCH").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/product-modules/{module_id}", "DELETE").endpoint.__module__ == (
        expected_module
    )


def test_product_git_repository_endpoints_are_owned_by_product_git_repositories_router():
    expected_module = "app.api.routers.product_git_repositories"

    assert _route_for(
        "/api/products/{product_id}/git-repositories",
        "GET",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/products/{product_id}/git-repositories",
        "POST",
    ).endpoint.__module__ == expected_module
    assert _route_for("/api/product-git-repositories/{repo_id}", "PATCH").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/product-git-repositories/{repo_id}", "DELETE").endpoint.__module__ == (
        expected_module
    )


def test_related_system_endpoints_are_owned_by_related_systems_router():
    expected_module = "app.api.routers.related_systems"

    assert _route_for("/api/system/related-systems", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/system/related-systems", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/system/related-systems/{system_id}", "PATCH").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/system/related-systems/{system_id}", "DELETE").endpoint.__module__ == (
        expected_module
    )


def test_model_gateway_endpoints_are_owned_by_model_gateway_router():
    expected_module = "app.api.routers.model_gateway"

    assert _route_for("/api/system/model-gateway-configs", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/system/model-gateway-configs", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/system/model-gateway-configs/test", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for(
        "/api/system/model-gateway-configs/{config_id}",
        "PATCH",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/system/model-gateway-configs/{config_id}",
        "DELETE",
    ).endpoint.__module__ == expected_module
    assert _route_for("/api/model-gateway/logs", "GET").endpoint.__module__ == expected_module


def test_brain_app_endpoints_are_owned_by_brain_apps_router():
    expected_module = "app.api.routers.brain_apps"

    assert _route_for("/api/brain-apps", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/brain-apps/{brain_app_id}", "GET").endpoint.__module__ == (
        expected_module
    )


def test_git_review_endpoints_are_owned_by_git_review_router():
    expected_module = "app.api.routers.git_review"

    assert _route_for(
        "/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview",
        "GET",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot",
        "POST",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/devops/github/pull-requests/{repository_id}",
        "GET",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/devops/github/pull-requests/{repository_id}/{pr_number}/preview",
        "GET",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/devops/github/pull-requests/{repository_id}/{pr_number}/snapshot",
        "POST",
    ).endpoint.__module__ == expected_module


def test_bug_management_endpoints_are_owned_by_bugs_router():
    expected_module = "app.api.routers.bugs"

    assert _route_for("/api/bugs", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/bugs", "POST").endpoint.__module__ == expected_module
    assert _route_for("/api/bugs/batch-update", "POST").endpoint.__module__ == expected_module
    assert _route_for("/api/bugs/{bug_id}", "PATCH").endpoint.__module__ == expected_module
    assert _route_for("/api/bugs/{bug_id}", "DELETE").endpoint.__module__ == expected_module


def test_bug_router_does_not_call_legacy_main():
    import app.api.routers.bugs as bugs_router

    router_source = inspect.getsource(bugs_router)
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source
    assert "legacy." not in router_source


def test_requirement_delivery_endpoints_are_owned_by_requirements_router():
    expected_module = "app.api.routers.requirements"

    assert _route_for("/api/requirements", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/requirements", "POST").endpoint.__module__ == expected_module
    assert _route_for("/api/requirements/batch-schedule", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for(
        "/api/requirements/batch-assign-owner",
        "POST",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/requirements/batch-advance-status",
        "POST",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/requirements/batch-generate-tasks",
        "POST",
    ).endpoint.__module__ == expected_module
    assert _route_for("/api/requirements/{requirement_id}", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/requirements/{requirement_id}", "PATCH").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/requirements/{requirement_id}", "DELETE").endpoint.__module__ == (
        expected_module
    )
    assert _route_for(
        "/api/requirements/{requirement_id}/full-chain",
        "GET",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/requirements/{requirement_id}/approve",
        "POST",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/requirements/{requirement_id}/reject",
        "POST",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/requirements/{requirement_id}/close",
        "POST",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/requirements/{requirement_id}/generate-task",
        "POST",
    ).endpoint.__module__ == expected_module


def test_requirement_list_handler_does_not_call_legacy_main():
    route = _route_for("/api/requirements", "GET")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_requirement_create_handler_does_not_call_legacy_main():
    route = _route_for("/api/requirements", "POST")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_requirement_read_handlers_do_not_call_legacy_main():
    for path, method in [
        ("/api/requirements/{requirement_id}", "GET"),
        ("/api/requirements/{requirement_id}/full-chain", "GET"),
    ]:
        route = _route_for(path, method)
        handler_source = inspect.getsource(route.endpoint)
        assert "_legacy_main" not in handler_source
        assert "from app import main" not in handler_source
        assert "legacy." not in handler_source


def test_requirement_update_delete_handlers_do_not_call_legacy_main():
    for path, method in [
        ("/api/requirements/{requirement_id}", "PATCH"),
        ("/api/requirements/{requirement_id}", "DELETE"),
    ]:
        route = _route_for(path, method)
        handler_source = inspect.getsource(route.endpoint)
        assert "_legacy_main" not in handler_source
        assert "from app import main" not in handler_source
        assert "legacy." not in handler_source


def test_requirement_decision_handlers_do_not_call_legacy_main():
    for path in [
        "/api/requirements/{requirement_id}/approve",
        "/api/requirements/{requirement_id}/reject",
        "/api/requirements/{requirement_id}/close",
    ]:
        route = _route_for(path, "POST")
        handler_source = inspect.getsource(route.endpoint)
        assert "_legacy_main" not in handler_source
        assert "from app import main" not in handler_source
        assert "legacy." not in handler_source


def test_requirement_generate_task_handler_does_not_call_legacy_main():
    route = _route_for("/api/requirements/{requirement_id}/generate-task", "POST")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_requirement_batch_generate_tasks_handler_does_not_call_legacy_main():
    route = _route_for("/api/requirements/batch-generate-tasks", "POST")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_requirement_batch_assign_owner_handler_does_not_call_legacy_main():
    route = _route_for("/api/requirements/batch-assign-owner", "POST")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_requirement_batch_schedule_handler_does_not_call_legacy_main():
    route = _route_for("/api/requirements/batch-schedule", "POST")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_requirement_batch_advance_status_handler_does_not_call_legacy_main():
    route = _route_for("/api/requirements/batch-advance-status", "POST")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_requirements_router_does_not_call_legacy_main():
    import app.api.routers.requirements as requirements_router

    router_source = inspect.getsource(requirements_router)
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source
    assert "legacy." not in router_source


def test_ai_task_and_review_endpoints_are_owned_by_tasks_router():
    expected_module = "app.api.routers.tasks"

    assert _route_for("/api/ai-tasks", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/ai-tasks", "POST").endpoint.__module__ == expected_module
    assert _route_for("/api/ai-tasks/{task_id}", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/ai-tasks/{task_id}/start", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/ai-tasks/{task_id}/cancel", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/ai-tasks/{task_id}/more-info", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/graph-runs", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/reviews/pending", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/reviews/{review_id}", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/reviews/{review_id}/approve", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/reviews/{review_id}/edit-approve", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/reviews/{review_id}/reject", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for(
        "/api/reviews/{review_id}/request-more-info",
        "POST",
    ).endpoint.__module__ == expected_module


def test_ai_task_list_and_create_handlers_are_not_legacy_main_handlers():
    import app.main as legacy_main

    assert not hasattr(legacy_main, "list_ai_tasks")
    assert not hasattr(legacy_main, "create_ai_task")


def test_tasks_router_does_not_call_legacy_main():
    import app.api.routers.tasks as tasks_router

    router_source = inspect.getsource(tasks_router)
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source
    assert "legacy." not in router_source


def test_ai_task_list_handler_does_not_call_legacy_main():
    route = _route_for("/api/ai-tasks", "GET")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_ai_task_detail_handler_does_not_call_legacy_main():
    route = _route_for("/api/ai-tasks/{task_id}", "GET")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_task_workflow_read_handlers_do_not_call_legacy_main():
    for path, method in [
        ("/api/graph-runs", "GET"),
        ("/api/reviews/pending", "GET"),
        ("/api/reviews/{review_id}", "GET"),
    ]:
        route = _route_for(path, method)
        handler_source = inspect.getsource(route.endpoint)
        assert "_legacy_main" not in handler_source
        assert "from app import main" not in handler_source
        assert "legacy." not in handler_source


def test_task_state_write_handlers_do_not_call_legacy_main():
    for path, method in [
        ("/api/ai-tasks/{task_id}/cancel", "POST"),
        ("/api/ai-tasks/{task_id}/more-info", "POST"),
    ]:
        route = _route_for(path, method)
        handler_source = inspect.getsource(route.endpoint)
        assert "_legacy_main" not in handler_source
        assert "from app import main" not in handler_source
        assert "legacy." not in handler_source


def test_ai_task_batch_cancel_handler_does_not_call_legacy_main():
    route = _route_for("/api/ai-tasks/batch-cancel", "POST")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_ai_task_batch_retry_handler_does_not_call_legacy_main():
    route = _route_for("/api/ai-tasks/batch-retry", "POST")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_ai_task_start_handler_does_not_call_legacy_main():
    route = _route_for("/api/ai-tasks/{task_id}/start", "POST")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_review_decision_handlers_do_not_call_legacy_main():
    for path in [
        "/api/reviews/{review_id}/approve",
        "/api/reviews/{review_id}/edit-approve",
        "/api/reviews/{review_id}/reject",
        "/api/reviews/{review_id}/request-more-info",
    ]:
        route = _route_for(path, "POST")
        handler_source = inspect.getsource(route.endpoint)
        assert "_legacy_main" not in handler_source
        assert "from app import main" not in handler_source
        assert "legacy." not in handler_source


def test_knowledge_endpoints_are_owned_by_knowledge_router():
    expected_module = "app.api.routers.knowledge"

    assert _route_for("/api/knowledge/documents", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/knowledge/documents", "POST").endpoint.__module__ == expected_module
    assert _route_for("/api/knowledge/documents/{document_id}", "PATCH").endpoint.__module__ == (
        expected_module
    )
    assert _route_for(
        "/api/knowledge/documents/{document_id}/retry-index",
        "POST",
    ).endpoint.__module__ == expected_module
    assert _route_for("/api/knowledge/documents/{document_id}", "DELETE").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/knowledge/search", "POST").endpoint.__module__ == expected_module
    assert _route_for("/api/knowledge/deposits", "GET").endpoint.__module__ == expected_module
    assert _route_for(
        "/api/knowledge/deposits/{deposit_id}/approve",
        "POST",
    ).endpoint.__module__ == expected_module
    assert _route_for(
        "/api/knowledge/deposits/{deposit_id}/reject",
        "POST",
    ).endpoint.__module__ == expected_module


def test_knowledge_document_list_handler_does_not_call_legacy_main():
    route = _route_for("/api/knowledge/documents", "GET")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_knowledge_document_create_handler_does_not_call_legacy_main():
    route = _route_for("/api/knowledge/documents", "POST")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_knowledge_document_write_handlers_do_not_call_legacy_main():
    for path, method in [
        ("/api/knowledge/documents/{document_id}", "PATCH"),
        ("/api/knowledge/documents/{document_id}/retry-index", "POST"),
        ("/api/knowledge/documents/{document_id}", "DELETE"),
    ]:
        route = _route_for(path, method)
        handler_source = inspect.getsource(route.endpoint)
        assert "_legacy_main" not in handler_source
        assert "from app import main" not in handler_source
        assert "legacy." not in handler_source


def test_knowledge_deposit_list_handler_does_not_call_legacy_main():
    route = _route_for("/api/knowledge/deposits", "GET")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_knowledge_search_handler_does_not_call_legacy_main():
    route = _route_for("/api/knowledge/search", "POST")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_knowledge_deposit_decision_handlers_do_not_call_legacy_main():
    for path in [
        "/api/knowledge/deposits/{deposit_id}/approve",
        "/api/knowledge/deposits/{deposit_id}/reject",
    ]:
        route = _route_for(path, "POST")
        handler_source = inspect.getsource(route.endpoint)
        assert "_legacy_main" not in handler_source
        assert "from app import main" not in handler_source
        assert "legacy." not in handler_source


def test_operational_metric_endpoints_are_owned_by_devops_metrics_router():
    expected_module = "app.api.routers.devops_metrics"

    assert _route_for("/api/devops/operational-metrics", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/devops/gitlab/daily-code-metrics", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/devops/gitlab/daily-code-metrics", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/devops/jenkins/releases", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/devops/jenkins/releases", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/ops/online-log-metrics", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/ops/online-log-metrics", "POST").endpoint.__module__ == (
        expected_module
    )


def test_operational_metrics_handler_does_not_call_legacy_main():
    route = _route_for("/api/devops/operational-metrics", "GET")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_devops_metrics_router_does_not_call_legacy_main():
    router_source = Path("app/api/routers/devops_metrics.py").read_text()
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source
    assert "legacy." not in router_source


def test_user_insight_endpoints_are_owned_by_user_insights_router():
    expected_module = "app.api.routers.user_insights"

    assert _route_for("/api/insights/items", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/insights/usage-metrics", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/insights/usage-metrics", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/insights/user-feedback", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/insights/user-feedback", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/insights/user-feedback/{feedback_id}", "PATCH").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/planning/iteration-suggestions", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/planning/iteration-suggestions", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for(
        "/api/planning/iteration-suggestions/{suggestion_id}/decide",
        "POST",
    ).endpoint.__module__ == expected_module


def test_user_insight_items_handler_does_not_call_legacy_main():
    route = _route_for("/api/insights/items", "GET")
    handler_source = inspect.getsource(route.endpoint)
    assert "_legacy_main" not in handler_source
    assert "from app import main" not in handler_source
    assert "legacy." not in handler_source


def test_user_insights_router_does_not_call_legacy_main():
    router_source = Path("app/api/routers/user_insights.py").read_text()
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source
    assert "legacy." not in router_source


def test_git_review_router_does_not_call_legacy_main():
    router_source = Path("app/api/routers/git_review.py").read_text()
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source
    assert "legacy." not in router_source


def test_writeback_endpoints_are_owned_by_writeback_router():
    expected_module = "app.api.routers.writeback"

    assert _route_for("/api/writeback/results/{task_id}", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/writeback/results/{task_id}", "POST").endpoint.__module__ == (
        expected_module
    )


def test_writeback_router_does_not_call_legacy_main():
    router_source = Path("app/api/routers/writeback.py").read_text()
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source


def test_code_review_report_endpoint_is_owned_by_code_review_reports_router():
    route = _route_for("/api/ai-tasks/{task_id}/code-review-report", "GET")
    assert route.endpoint.__module__ == "app.api.routers.code_review_reports"


def test_code_review_report_router_does_not_call_legacy_main():
    router_source = Path("app/api/routers/code_review_reports.py").read_text()
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source


def test_audit_event_endpoint_is_owned_by_audit_router():
    route = _route_for("/api/audit/events", "GET")
    assert route.endpoint.__module__ == "app.api.routers.audit"


def test_audit_router_does_not_call_legacy_main():
    router_source = Path("app/api/routers/audit.py").read_text()
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source


def test_export_endpoint_is_owned_by_export_router():
    route = _route_for("/api/export/tasks/{task_id}/markdown", "GET")
    assert route.endpoint.__module__ == "app.api.routers.export"


def test_export_router_does_not_call_legacy_main():
    router_source = Path("app/api/routers/export.py").read_text()
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source


def test_collector_run_endpoints_are_owned_by_collectors_router():
    expected_module = "app.api.routers.collectors"

    assert _route_for("/api/collectors/runs", "GET").endpoint.__module__ == expected_module
    assert _route_for("/api/collectors/runs", "POST").endpoint.__module__ == expected_module
    assert _route_for("/api/collectors/runs/{run_id}", "PATCH").endpoint.__module__ == (
        expected_module
    )


def test_collectors_router_does_not_call_legacy_main():
    router_source = Path("app/api/routers/collectors.py").read_text()
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source
    assert "legacy." not in router_source


def test_pending_attribution_endpoints_are_owned_by_attribution_router():
    expected_module = "app.api.routers.attribution"

    assert _route_for("/api/attribution/pending-items", "GET").endpoint.__module__ == (
        expected_module
    )
    assert _route_for("/api/attribution/pending-items", "POST").endpoint.__module__ == (
        expected_module
    )
    assert _route_for(
        "/api/attribution/pending-items/{item_id}/resolve",
        "POST",
    ).endpoint.__module__ == expected_module


def test_attribution_router_does_not_call_legacy_main():
    router_source = Path("app/api/routers/attribution.py").read_text()
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source
    assert "legacy." not in router_source


def test_lifecycle_context_endpoint_is_owned_by_lifecycle_router():
    route = _route_for("/api/lifecycle/context", "GET")
    assert route.endpoint.__module__ == "app.api.routers.lifecycle"


def test_lifecycle_router_does_not_call_legacy_main():
    router_source = Path("app/api/routers/lifecycle.py").read_text()
    assert "_legacy_main" not in router_source
    assert "from app import main" not in router_source
    assert "legacy." not in router_source
