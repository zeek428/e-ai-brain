from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MAX_DOMAIN_FILE_LINES = 2800
MAX_AI_EXECUTOR_RUNNER_LINES = 2200
MAX_CODE_INSPECTION_SERVICE_LINES = 1600
MAX_PLUGIN_MAIN_SERVICE_LINES = 1800
MAX_PRODUCT_VERSION_DASHBOARD_LINES = 1300
MAX_SCHEDULED_JOB_SERVICE_LINES = 1900
MAX_ASSISTANT_ACTION_DRAFT_LINES = 2000
MAX_FRONTEND_SERVICE_BARREL_LINES = 2450
FRONTEND_PAGE_CONTAINER_REVIEW_THRESHOLD_LINES = 900

DOMAIN_FILE_LINE_BUDGETS = {
    "apps/api/app/services/ai_executor_runners.py": MAX_AI_EXECUTOR_RUNNER_LINES,
    "apps/api/app/services/assistant_action_drafts.py": MAX_ASSISTANT_ACTION_DRAFT_LINES,
    "apps/api/app/core/repositories/authorization.py": MAX_DOMAIN_FILE_LINES,
    "apps/api/app/services/assistant_chat.py": MAX_DOMAIN_FILE_LINES,
    "apps/api/app/services/assistant_references.py": MAX_DOMAIN_FILE_LINES,
    "apps/api/app/services/code_inspections.py": MAX_CODE_INSPECTION_SERVICE_LINES,
    "apps/api/app/services/plugins.py": MAX_PLUGIN_MAIN_SERVICE_LINES,
    "apps/api/app/services/product_version_dashboard.py": MAX_PRODUCT_VERSION_DASHBOARD_LINES,
    "apps/api/app/services/scheduled_jobs.py": MAX_SCHEDULED_JOB_SERVICE_LINES,
    "apps/web/src/services/aiBrain.ts": MAX_FRONTEND_SERVICE_BARREL_LINES,
}

FRONTEND_PAGE_CONTAINER_LINE_BUDGETS = {
    "apps/web/src/pages/AiCapabilities/index.tsx": 1000,
    "apps/web/src/pages/Bugs/index.tsx": 1100,
    "apps/web/src/pages/CodeInspections/index.tsx": 1100,
    "apps/web/src/pages/Devops/index.tsx": 1200,
    "apps/web/src/pages/IterationVersions/index.tsx": 1500,
    "apps/web/src/pages/Knowledge/index.tsx": 1800,
    "apps/web/src/pages/Plugins/index.tsx": 1600,
    "apps/web/src/pages/Products/index.tsx": 1550,
    "apps/web/src/pages/Requirements/index.tsx": 1250,
    "apps/web/src/pages/Roles/index.tsx": 1900,
    "apps/web/src/pages/ScheduledJobs/index.tsx": 1450,
    "apps/web/src/pages/SystemHealth/index.tsx": 2000,
    "apps/web/src/pages/TaskCenter/index.tsx": 1800,
}


def test_split_domain_entrypoints_stay_under_line_budget():
    oversized_files: list[str] = []
    for relative_path, max_lines in DOMAIN_FILE_LINE_BUDGETS.items():
        file_path = REPO_ROOT / relative_path
        assert file_path.exists(), f"Guarded architecture file is missing: {relative_path}"
        line_count = len(file_path.read_text(encoding="utf-8").splitlines())
        if line_count > max_lines:
            oversized_files.append(f"{relative_path}: {line_count} lines > {max_lines}")

    assert not oversized_files, "Split large domain files before merging:\n" + "\n".join(
        oversized_files
    )


def test_frontend_page_containers_stay_under_line_budget():
    oversized_files: list[str] = []
    unguarded_large_pages: list[str] = []
    pages_root = REPO_ROOT / "apps/web/src/pages"

    for page_path in sorted(pages_root.glob("*/index.tsx")):
        relative_path = str(page_path.relative_to(REPO_ROOT))
        line_count = len(page_path.read_text(encoding="utf-8").splitlines())
        max_lines = FRONTEND_PAGE_CONTAINER_LINE_BUDGETS.get(relative_path)

        if max_lines is None:
            if line_count > FRONTEND_PAGE_CONTAINER_REVIEW_THRESHOLD_LINES:
                unguarded_large_pages.append(
                    f"{relative_path}: {line_count} lines needs an explicit split budget"
                )
            continue

        if line_count > max_lines:
            oversized_files.append(f"{relative_path}: {line_count} lines > {max_lines}")

    assert not unguarded_large_pages, (
        "Add an explicit page-container budget or split these frontend pages:\n"
        + "\n".join(unguarded_large_pages)
    )
    assert not oversized_files, "Split frontend page containers before merging:\n" + "\n".join(
        oversized_files
    )


def test_task_center_detail_modal_is_split_from_page_container():
    component_path = REPO_ROOT / "apps/web/src/pages/TaskCenter/components/TaskDetailModal.tsx"
    entrypoint_path = REPO_ROOT / "apps/web/src/pages/TaskCenter/index.tsx"

    assert component_path.exists(), "Keep TaskCenter task-detail display in a split component."
    component_source = component_path.read_text(encoding="utf-8")
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")

    assert "TaskDetailModal" in entrypoint_source
    assert "任务详情加载中" not in entrypoint_source
    assert "Graph Runs" in component_source
    assert "formatJsonPreview" in component_source


def test_scheduled_job_entrypoint_uses_split_constants_module():
    constants_path = REPO_ROOT / "apps/api/app/services/scheduled_job_constants.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/scheduled_jobs.py"

    assert constants_path.exists(), (
        "Move scheduled job status/sort/policy constants to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    assert "from app.services.scheduled_job_constants import" in entrypoint_source


def test_scheduled_job_entrypoint_uses_split_config_module():
    config_path = REPO_ROOT / "apps/api/app/services/scheduled_job_config.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/scheduled_jobs.py"

    assert config_path.exists(), (
        "Move scheduled job config normalization and effective type helpers to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    assert "from app.services.scheduled_job_config import" in entrypoint_source
    assert "def scheduled_job_config_with_multi_refs(" not in entrypoint_source
    assert "def scheduled_job_data_connection_policy(" not in entrypoint_source
    assert "def effective_scheduled_job_type(" not in entrypoint_source


def test_scheduled_job_entrypoint_uses_split_user_feedback_module():
    user_feedback_path = REPO_ROOT / "apps/api/app/services/scheduled_job_user_feedback.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/scheduled_jobs.py"

    assert user_feedback_path.exists(), (
        "Move scheduled job user feedback insight extraction to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    user_feedback_source = user_feedback_path.read_text(encoding="utf-8")
    assert "from app.services.scheduled_job_user_feedback import" in entrypoint_source
    assert "def run_user_feedback_insight_extract_job(" not in entrypoint_source
    assert "def normalized_insight_enum(" not in entrypoint_source
    assert "USER_FEEDBACK_TYPES" not in entrypoint_source
    assert "def run_user_feedback_insight_extract_job(" in user_feedback_source
    assert "def resolve_job_plugin_output_mapping(" in user_feedback_source


def test_scheduled_job_entrypoint_uses_split_read_model_module():
    read_model_path = REPO_ROOT / "apps/api/app/services/scheduled_job_read_models.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/scheduled_jobs.py"

    assert read_model_path.exists(), (
        "Move scheduled job list and run list read models to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    read_model_source = read_model_path.read_text(encoding="utf-8")
    assert "from app.services.scheduled_job_read_models import" in entrypoint_source
    assert "def list_scheduled_jobs_response(" in read_model_source
    assert "def list_scheduled_job_runs_response(" in read_model_source
    assert "def public_scheduled_job_run(" in read_model_source
    assert "def list_scheduled_jobs_response(" not in entrypoint_source
    assert "def list_scheduled_job_runs_response(" not in entrypoint_source
    assert "def public_scheduled_job_run(" not in entrypoint_source


def test_scheduled_job_entrypoint_uses_split_ref_validation_module():
    validation_path = REPO_ROOT / "apps/api/app/services/scheduled_job_ref_validation.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/scheduled_jobs.py"

    assert validation_path.exists(), (
        "Move scheduled job AI, product and plugin reference validation "
        "to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    validation_source = validation_path.read_text(encoding="utf-8")
    assert "from app.services.scheduled_job_ref_validation import" in entrypoint_source
    assert "def validate_job_refs(" in validation_source
    assert "def validate_plugin_refs(" in validation_source
    assert "ensure_active_model_gateway(" in validation_source
    assert "ensure_active_plugin_action(" in validation_source
    assert "def validate_job_refs(" not in entrypoint_source
    assert "def validate_plugin_refs(" not in entrypoint_source


def test_plugin_entrypoint_uses_split_constants_module():
    constants_path = REPO_ROOT / "apps/api/app/services/plugin_constants.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/plugins.py"

    assert constants_path.exists(), (
        "Move plugin protocol/status/sort constants to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    assert "from app.services.plugin_constants import" in entrypoint_source
    assert "PLUGIN_PROTOCOLS = " not in entrypoint_source
    assert "PLUGIN_CONNECTION_SORT_FIELDS = " not in entrypoint_source


def test_plugin_entrypoint_uses_split_projection_module():
    projection_path = REPO_ROOT / "apps/api/app/services/plugin_projection.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/plugins.py"

    assert projection_path.exists(), (
        "Move plugin public projections and request redaction to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    assert "from app.services.plugin_projection import" in entrypoint_source
    assert "def public_plugin(" not in entrypoint_source
    assert "def public_invocation_log(" not in entrypoint_source
    assert "def redact_plugin_request_summary(" not in entrypoint_source


def test_plugin_entrypoint_uses_split_store_helpers_module():
    helper_path = REPO_ROOT / "apps/api/app/services/plugin_store_helpers.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/plugins.py"

    assert helper_path.exists(), (
        "Move plugin MemoryStore compatibility, repository sync and generic validators "
        "to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "from app.services.plugin_store_helpers import" in entrypoint_source
    assert "def ensure_standard_plugins(" in helper_source
    assert "def sync_plugin_dependency_store(" in helper_source
    assert "def merge_masked_config(" in helper_source
    assert "def ensure_standard_plugins(" not in entrypoint_source
    assert "def sync_plugin_dependency_store(" not in entrypoint_source
    assert "def merge_masked_config(" not in entrypoint_source


def test_plugin_entrypoint_uses_split_invocation_runtime_module():
    runtime_path = REPO_ROOT / "apps/api/app/services/plugin_invocation_runtime.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/plugins.py"

    assert runtime_path.exists(), (
        "Move plugin dynamic request config, preview and invocation runtime helpers "
        "to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    runtime_source = runtime_path.read_text(encoding="utf-8")
    assert "from app.services.plugin_invocation_runtime import" in entrypoint_source
    assert "def resolve_plugin_request_config(" in runtime_source
    assert "def plugin_action_request_preview(" in runtime_source
    assert "def _invoke_ai_executor_runner(" in runtime_source
    assert "def resolve_plugin_request_config(" not in entrypoint_source
    assert "def plugin_action_request_preview(" not in entrypoint_source
    assert "def _invoke_ai_executor_runner(" not in entrypoint_source
    assert "call_model_gateway_for_task(" not in entrypoint_source


def test_ai_executor_runners_use_split_health_module():
    helper_path = REPO_ROOT / "apps/api/app/services/ai_executor_runner_health.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/ai_executor_runners.py"

    assert helper_path.exists(), (
        "Move AI executor runner health, system runner and public projection helpers "
        "to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "from app.services.ai_executor_runner_health import" in entrypoint_source
    assert "def runner_public(" in helper_source
    assert "def runner_health_alert(" in helper_source
    assert "def system_default_ai_executor_runner(" in helper_source
    assert "def _runner_public(" not in entrypoint_source
    assert "def _runner_health_alert(" not in entrypoint_source
    assert "def system_default_ai_executor_runner(" not in entrypoint_source


def test_ai_executor_runners_use_split_task_context_module():
    helper_path = REPO_ROOT / "apps/api/app/services/ai_executor_runner_task_context.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/ai_executor_runners.py"

    assert helper_path.exists(), (
        "Move AI executor task product-scope, upstream context and runner node helpers "
        "to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "from app.services.ai_executor_runner_task_context import" in entrypoint_source
    assert "def _ai_executor_task_visible_to_user(" in helper_source
    assert "def _runner_node_from_task(" in helper_source
    assert "def _datetime_value(" in helper_source
    assert "def _load_scheduled_job_run(" not in entrypoint_source
    assert "def _ai_executor_task_visible_to_user(" not in entrypoint_source
    assert "def _runner_node_from_task(" not in entrypoint_source
    assert "def _datetime_value(" not in entrypoint_source


def test_assistant_references_uses_split_action_defaults_module():
    defaults_path = REPO_ROOT / "apps/api/app/services/assistant_action_reference_defaults.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/assistant_references.py"

    assert defaults_path.exists(), (
        "Move assistant action reference default candidates to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    assert "from app.services.assistant_action_reference_defaults import" in entrypoint_source
    assert "ASSISTANT_ACTION_CANDIDATES = (" not in entrypoint_source


def test_assistant_references_uses_split_knowledge_reference_module():
    helper_path = REPO_ROOT / "apps/api/app/services/assistant_knowledge_references.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/assistant_references.py"

    assert helper_path.exists(), (
        "Move assistant knowledge reference candidates and context helpers to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "assistant_knowledge_references as knowledge_reference_helpers" in entrypoint_source
    assert "def knowledge_document_reference_candidates(" in helper_source
    assert "def knowledge_context_for_document(" in helper_source
    assert "def _knowledge_document_reference_candidates(" not in entrypoint_source
    assert "def _knowledge_context_for_document(" not in entrypoint_source


def test_assistant_chat_uses_split_scheduled_job_run_module():
    helper_path = REPO_ROOT / "apps/api/app/services/assistant_scheduled_job_run.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/assistant_chat.py"

    assert helper_path.exists(), (
        "Move assistant scheduled job run-once mention and projection helpers to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "assistant_scheduled_job_run as scheduled_job_run_helpers" in entrypoint_source
    assert "def scheduled_job_references_from_explicit_mentions(" in helper_source
    assert "def scheduled_job_run_tool_result(" in helper_source
    assert "def _scheduled_job_references_from_explicit_mentions(" not in entrypoint_source
    assert "def _scheduled_job_run_tool_result(" not in entrypoint_source


def test_assistant_chat_uses_split_model_gateway_module():
    helper_path = REPO_ROOT / "apps/api/app/services/assistant_chat_gateway.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/assistant_chat.py"

    assert helper_path.exists(), (
        "Move assistant model gateway request assembly, cancellation and logging to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "call_model_gateway_for_assistant_chat as _call_model_gateway_for_assistant_chat" in (
        entrypoint_source
    )
    assert "def call_model_gateway_for_assistant_chat(" in helper_source
    assert "def interrupt_assistant_chat_gateway_run(" in helper_source
    assert "def _read_model_gateway_response_payload(" not in entrypoint_source
    assert "def _model_gateway_chat_completions_url(" not in entrypoint_source
    assert "httpx.Client(" not in entrypoint_source


def test_assistant_action_drafts_uses_split_common_module():
    helper_path = REPO_ROOT / "apps/api/app/services/assistant_action_draft_common.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/assistant_action_drafts.py"

    assert helper_path.exists(), (
        "Move assistant action draft constants, payload defaults and base validators "
        "to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "from app.services.assistant_action_draft_common import" in entrypoint_source
    assert "def ensure_draft_action(" in helper_source
    assert "def valid_cron_expression(" in helper_source
    assert "ASSISTANT_DRAFT_ACTIONS = " not in entrypoint_source
    assert "SCHEDULED_JOB_DEFAULTS = " not in entrypoint_source
    assert "def _valid_cron_expression(" not in entrypoint_source


def test_assistant_action_drafts_uses_split_workbench_module():
    helper_path = REPO_ROOT / "apps/api/app/services/assistant_action_draft_workbench.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/assistant_action_drafts.py"

    assert helper_path.exists(), (
        "Move assistant action draft workbench projections and summary to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "from app.services.assistant_action_draft_workbench import" in entrypoint_source
    assert "def assistant_action_draft_workbench_item(" in helper_source
    assert "def assistant_action_draft_workbench_summary(" in helper_source
    assert "def _assistant_action_draft_workbench_item(" not in entrypoint_source
    assert "def _assistant_action_draft_workbench_summary(" not in entrypoint_source
    assert "governance_counts" in helper_source


def test_assistant_action_drafts_uses_split_governance_module():
    helper_path = REPO_ROOT / "apps/api/app/services/assistant_action_draft_governance.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/assistant_action_drafts.py"

    assert helper_path.exists(), (
        "Move assistant action draft risk, impact, permission, retry and audit governance "
        "projection to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "from app.services.assistant_action_draft_governance import" in entrypoint_source
    assert "def assistant_action_draft_governance(" in helper_source
    assert "def assistant_action_required_permissions(" in helper_source
    assert "def _assistant_action_draft_governance(" not in entrypoint_source
    assert "def _assistant_action_required_permissions(" not in entrypoint_source
    assert "assistant_action_draft_decision" in helper_source


def test_assistant_action_drafts_uses_split_preview_helpers_module():
    helper_path = REPO_ROOT / "apps/api/app/services/assistant_action_draft_preview_helpers.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/assistant_action_drafts.py"

    assert helper_path.exists(), (
        "Move assistant action draft preview, validation and permission helper "
        "logic to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "from app.services.assistant_action_draft_preview_helpers import" in entrypoint_source
    assert "def generic_create_draft_preview(" in helper_source
    assert "def validate_plugin_connection_ref(" in helper_source
    assert "def with_action_permission_preview(" in helper_source
    assert "def _generic_create_draft_preview(" not in entrypoint_source
    assert "def _validate_plugin_connection_ref(" not in entrypoint_source
    assert "def _with_action_permission_preview(" not in entrypoint_source


def test_product_version_dashboard_uses_split_evidence_coverage_module():
    helper_path = REPO_ROOT / "apps/api/app/services/product_version_evidence_coverage.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/product_version_dashboard.py"

    assert helper_path.exists(), (
        "Move product version dashboard evidence coverage scoring to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "from app.services.product_version_evidence_coverage import" in entrypoint_source
    assert "def version_evidence_coverage(" in helper_source
    assert "def _version_evidence_coverage(" not in entrypoint_source
    assert "def _evidence_domain(" not in entrypoint_source


def test_product_version_dashboard_uses_split_delivery_overview_module():
    helper_path = REPO_ROOT / "apps/api/app/services/product_version_delivery_overview.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/product_version_dashboard.py"

    assert helper_path.exists(), (
        "Move product version dashboard delivery stage and governance conclusion "
        "projection to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "from app.services.product_version_delivery_overview import" in entrypoint_source
    assert "def version_governance_conclusion(" in helper_source
    assert "def version_delivery_stage_overview(" in helper_source
    assert "def successful_release(" in helper_source
    assert "def _version_governance_conclusion(" not in entrypoint_source
    assert "def _delivery_stage_overview(" not in entrypoint_source
    assert "def _delivery_stage(" not in entrypoint_source


def test_code_inspections_uses_split_common_module():
    helper_path = REPO_ROOT / "apps/api/app/services/code_inspection_common.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/code_inspections.py"

    assert helper_path.exists(), (
        "Move code inspection constants, severity helpers and result-action validation "
        "to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "from app.services.code_inspection_common import" in entrypoint_source
    assert "def validate_code_inspection_result_actions(" in helper_source
    assert "def committer_summary(" in helper_source
    assert "CODE_INSPECTION_ACTION_TYPES = " not in entrypoint_source
    assert "def normalize_severity(" not in entrypoint_source
    assert "def report_matches_committer(" not in entrypoint_source


def test_code_inspections_uses_split_detail_projection_module():
    helper_path = REPO_ROOT / "apps/api/app/services/code_inspection_detail_projection.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/code_inspections.py"

    assert helper_path.exists(), (
        "Move code inspection detail scan and governance projections to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "from app.services.code_inspection_detail_projection import" in entrypoint_source
    assert "def code_inspection_scan_summary(" in helper_source
    assert "def code_inspection_governance_summary(" in helper_source
    assert "def code_inspection_scan_summary(" not in entrypoint_source
    assert "def code_inspection_governance_summary(" not in entrypoint_source
    assert "finding_accepted_risk_is_expired" in helper_source


def test_code_inspections_uses_split_read_model_module():
    helper_path = REPO_ROOT / "apps/api/app/services/code_inspection_read_models.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/code_inspections.py"

    assert helper_path.exists(), (
        "Move code inspection dashboard, list pagination and read model helpers "
        "to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    helper_source = helper_path.read_text(encoding="utf-8")
    assert "from app.services.code_inspection_read_models import" in entrypoint_source
    assert "def code_inspection_dashboard_response(" in helper_source
    assert "def list_code_inspection_reports_response(" in helper_source
    assert "def scoped_code_inspection_reports(" in helper_source
    assert "def code_inspection_dashboard_response(" not in entrypoint_source
    assert "def list_code_inspection_reports_response(" not in entrypoint_source
    assert "def scoped_code_inspection_reports(" not in entrypoint_source
