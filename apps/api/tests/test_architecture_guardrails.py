from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MAX_DOMAIN_FILE_LINES = 2800
MAX_PLUGIN_SERVICE_LINES = 2600
MAX_SCHEDULED_JOB_SERVICE_LINES = 2600
MAX_FRONTEND_SERVICE_BARREL_LINES = 2400

DOMAIN_FILE_LINE_BUDGETS = {
    "apps/api/app/services/ai_executor_runners.py": MAX_DOMAIN_FILE_LINES,
    "apps/api/app/core/repositories/authorization.py": MAX_DOMAIN_FILE_LINES,
    "apps/api/app/services/assistant_chat.py": MAX_DOMAIN_FILE_LINES,
    "apps/api/app/services/assistant_references.py": MAX_DOMAIN_FILE_LINES,
    "apps/api/app/services/plugins.py": MAX_PLUGIN_SERVICE_LINES,
    "apps/api/app/services/scheduled_jobs.py": MAX_SCHEDULED_JOB_SERVICE_LINES,
    "apps/web/src/services/aiBrain.ts": MAX_FRONTEND_SERVICE_BARREL_LINES,
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


def test_assistant_references_uses_split_action_defaults_module():
    defaults_path = REPO_ROOT / "apps/api/app/services/assistant_action_reference_defaults.py"
    entrypoint_path = REPO_ROOT / "apps/api/app/services/assistant_references.py"

    assert defaults_path.exists(), (
        "Move assistant action reference default candidates to a split module."
    )
    entrypoint_source = entrypoint_path.read_text(encoding="utf-8")
    assert "from app.services.assistant_action_reference_defaults import" in entrypoint_source
    assert "ASSISTANT_ACTION_CANDIDATES = (" not in entrypoint_source
