from __future__ import annotations

import shlex
import sys

import pytest

from app.core.code_review_executor import (
    CodeReviewExecutorError,
    ExternalCommandCodeReviewExecutor,
)


def test_external_command_code_review_executor_requires_configured_command():
    executor = ExternalCommandCodeReviewExecutor(
        command="",
        executor_name="code-review",
        executor_type="claude_code_skill",
        timeout_seconds=10,
    )

    with pytest.raises(CodeReviewExecutorError) as exc_info:
        executor.execute(current_store=None, task={}, payload={})

    assert exc_info.value.executor_type == "claude_code_skill"
    assert exc_info.value.executor_name == "code-review"
    assert exc_info.value.stage == "configure"
    assert exc_info.value.retryable is False


def test_external_command_code_review_executor_reads_stdin_and_normalizes_stdout():
    script = (
        "import json, sys; "
        "payload=json.load(sys.stdin); "
        "print(json.dumps({"
        "'summary':'command generated report',"
        "'risk_level':'low',"
        "'findings':[{'file_path': payload['gitlab_mr_snapshot']['id']}]"
        "}))"
    )
    executor = ExternalCommandCodeReviewExecutor(
        command=f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}",
        executor_name="code-review",
        executor_type="claude_code_skill",
        timeout_seconds=10,
    )

    result = executor.execute(
        current_store=None,
        task={},
        payload={"gitlab_mr_snapshot": {"id": "snapshot_001"}},
    )

    assert result.output == {
        "summary": "command generated report",
        "risk_level": "low",
        "findings": [{"file_path": "snapshot_001"}],
        "executor": {
            "executor_name": "code-review",
            "executor_type": "claude_code_skill",
            "retryable": False,
        },
    }
    assert result.executor == result.output["executor"]
