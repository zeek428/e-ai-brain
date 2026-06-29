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
