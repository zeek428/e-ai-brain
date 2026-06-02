from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CodeReviewExecutorResult:
    output: dict[str, Any]
    executor: dict[str, Any] = field(default_factory=dict)
    model_log: dict[str, Any] | None = None


class CodeReviewExecutorError(Exception):
    def __init__(
        self,
        message: str,
        *,
        executor_type: str,
        executor_name: str,
        stage: str = "execute",
        retryable: bool = True,
        model_log: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.executor_type = executor_type
        self.executor_name = executor_name
        self.stage = stage
        self.retryable = retryable
        self.model_log = model_log


def normalize_code_review_output(
    output: dict[str, Any],
    *,
    executor_type: str,
    executor_name: str,
    retryable: bool = False,
) -> dict[str, Any]:
    if not isinstance(output, dict):
        raise ValueError("Code review executor output must be a JSON object")
    summary = output.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("Code review executor output is missing summary")
    risk_level = output.get("risk_level")
    if not isinstance(risk_level, str) or not risk_level.strip():
        raise ValueError("Code review executor output is missing risk_level")
    findings = output.get("findings")
    if not isinstance(findings, list):
        raise ValueError("Code review executor output is missing findings")

    executor = output.get("executor") if isinstance(output.get("executor"), dict) else {}
    normalized_executor = {
        **executor,
        "executor_name": executor_name,
        "executor_type": executor_type,
        "retryable": bool(executor.get("retryable", retryable)),
    }
    normalized = dict(output)
    normalized["summary"] = summary.strip()
    normalized["risk_level"] = risk_level.strip()
    normalized["findings"] = findings
    normalized["executor"] = normalized_executor
    return normalized


class ExternalCommandCodeReviewExecutor:
    def __init__(
        self,
        *,
        command: str,
        executor_type: str,
        executor_name: str,
        timeout_seconds: int,
    ) -> None:
        self.command = command
        self.executor_type = executor_type
        self.executor_name = executor_name
        self.timeout_seconds = timeout_seconds

    def execute(
        self,
        *,
        current_store: Any,
        task: dict[str, Any],
        payload: dict[str, Any],
    ) -> CodeReviewExecutorResult:
        del current_store, task
        if not self.command.strip():
            raise CodeReviewExecutorError(
                "Code review executor command is not configured",
                executor_type=self.executor_type,
                executor_name=self.executor_name,
                stage="configure",
                retryable=False,
            )
        args = shlex.split(self.command)
        if not args:
            raise CodeReviewExecutorError(
                "Code review executor command is not configured",
                executor_type=self.executor_type,
                executor_name=self.executor_name,
                stage="configure",
                retryable=False,
            )
        try:
            completed = subprocess.run(
                args,
                input=json.dumps(payload, ensure_ascii=False),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CodeReviewExecutorError(
                "Code review executor timed out",
                executor_type=self.executor_type,
                executor_name=self.executor_name,
                stage="execute",
                retryable=True,
            ) from exc
        except OSError as exc:
            raise CodeReviewExecutorError(
                "Code review executor process failed",
                executor_type=self.executor_type,
                executor_name=self.executor_name,
                stage="execute",
                retryable=True,
            ) from exc
        if completed.returncode != 0:
            raise CodeReviewExecutorError(
                "Code review executor returned a non-zero exit code",
                executor_type=self.executor_type,
                executor_name=self.executor_name,
                stage="execute",
                retryable=True,
            )
        try:
            output = json.loads(completed.stdout)
            normalized = normalize_code_review_output(
                output,
                executor_type=self.executor_type,
                executor_name=self.executor_name,
            )
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise CodeReviewExecutorError(
                "Code review executor returned invalid output",
                executor_type=self.executor_type,
                executor_name=self.executor_name,
                stage="parse_output",
                retryable=True,
            ) from exc
        return CodeReviewExecutorResult(
            output=normalized,
            executor=normalized["executor"],
        )
