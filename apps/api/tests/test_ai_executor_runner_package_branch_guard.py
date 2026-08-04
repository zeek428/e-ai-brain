from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.services.acceptance_test_plans import acceptance_verification_fingerprint
from app.services.ai_executor_runner_packages import _runner_agent_python


def _git(path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_generated_runner_detects_frozen_work_item_branch_drift(tmp_path, monkeypatch) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.email", "runner-test@example.com")
    _git(repository, "config", "user.name", "Runner Test")
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "fixture")

    config_path = tmp_path / "runner_config.json"
    config_path.write_text(
        json.dumps(
            {
                "runner": {
                    "executor_types": ["codex"],
                    "id": "runner-branch-guard",
                    "workspace_roots": [str(repository)],
                },
                "safety": {"workspace_worktree_isolation_enabled": True},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_BRAIN_ENDPOINT", "http://127.0.0.1:8000/api/system")
    monkeypatch.setenv("AI_BRAIN_RUNNER_CONFIG", str(config_path))
    monkeypatch.setenv("AI_BRAIN_RUNNER_ID", "runner-branch-guard")
    monkeypatch.setenv("AI_BRAIN_RUNNER_TOKEN", "runner-token")
    namespace: dict[str, object] = {"__name__": "runner_branch_guard_test"}
    exec(compile(_runner_agent_python(), "runner_agent.py", "exec"), namespace)

    execution_workspace, isolation = namespace["_prepare_isolated_workspace"](  # type: ignore[index,operator]
        {
            "id": "runner_task_branch_guard",
            "request_config": {
                "rd_collaboration_run_id": "run-1",
                "rd_work_item_id": "run-1:plan:1:item:implementation",
            },
        },
        str(repository),
    )
    _git(execution_workspace, "switch", "-c", "unexpected-branch")

    drift = namespace["_frozen_workspace_branch_drift"](isolation)  # type: ignore[index,operator]

    assert drift == {
        "actual_branch_name": "unexpected-branch",
        "expected_branch_name": isolation["branch_name"],
    }

    rework_workspace, rework_isolation = namespace["_prepare_isolated_workspace"](  # type: ignore[index,operator]
        {
            "id": "runner_task_branch_guard_rework",
            "request_config": {
                "rd_collaboration_run_id": "run-1",
                "rd_work_item_id": "run-1:plan:1:item:implementation",
            },
        },
        str(repository),
    )

    assert _git(rework_workspace, "branch", "--show-current") == isolation["branch_name"]
    assert rework_isolation["branch_name"] == isolation["branch_name"]


def test_generated_runner_seeds_dependent_worktree_from_upstream_commit(
    tmp_path,
    monkeypatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.email", "runner-test@example.com")
    _git(repository, "config", "user.name", "Runner Test")
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "fixture")
    base_sha = _git(repository, "rev-parse", "HEAD")
    (repository / "artifact.md").write_text("upstream delivery\n", encoding="utf-8")
    _git(repository, "add", "artifact.md")
    _git(repository, "commit", "-m", "upstream delivery")
    upstream_sha = _git(repository, "rev-parse", "HEAD")
    _git(repository, "reset", "--hard", base_sha)

    config_path = tmp_path / "runner_config.json"
    config_path.write_text(
        json.dumps(
            {
                "runner": {
                    "executor_types": ["codex"],
                    "id": "runner-upstream-seed",
                    "workspace_roots": [str(repository)],
                },
                "safety": {"workspace_worktree_isolation_enabled": True},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_BRAIN_ENDPOINT", "http://127.0.0.1:8000/api/system")
    monkeypatch.setenv("AI_BRAIN_RUNNER_CONFIG", str(config_path))
    monkeypatch.setenv("AI_BRAIN_RUNNER_ID", "runner-upstream-seed")
    monkeypatch.setenv("AI_BRAIN_RUNNER_TOKEN", "runner-token")
    namespace: dict[str, object] = {"__name__": "runner_upstream_seed_test"}
    exec(compile(_runner_agent_python(), "runner_agent.py", "exec"), namespace)

    retained_workspace, _ = namespace["_prepare_isolated_workspace"](  # type: ignore[index,operator]
        {
            "id": "runner_task_old_test_workspace",
            "request_config": {
                "rd_collaboration_run_id": "run-1",
                "rd_work_item_id": "run-1:plan:1:item:test",
            },
        },
        str(repository),
    )
    execution_workspace, isolation = namespace["_prepare_isolated_workspace"](  # type: ignore[index,operator]
        {
            "id": "runner_task_upstream_seed",
            "request_config": {
                "rd_collaboration_run_id": "run-1",
                "rd_work_item_id": "run-1:plan:1:item:test",
                "upstream_delivery_commit_shas": [upstream_sha],
            },
        },
        str(repository),
    )

    assert _git(execution_workspace, "rev-parse", "HEAD") == upstream_sha
    assert (Path(execution_workspace) / "artifact.md").read_text(encoding="utf-8") == (
        "upstream delivery\n"
    )
    assert isolation["upstream_delivery_commit_shas"] == [upstream_sha]
    assert not Path(retained_workspace).exists()


def test_generated_runner_reuses_retained_worktree_from_allowed_base_workspace(
    tmp_path,
    monkeypatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.email", "runner-test@example.com")
    _git(repository, "config", "user.name", "Runner Test")
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "fixture")

    config_path = tmp_path / "runner_config.json"
    config_path.write_text(
        json.dumps(
            {
                "runner": {
                    "executor_types": ["codex"],
                    "id": "runner-worktree-reuse",
                    "workspace_roots": [str(repository)],
                },
                "safety": {"workspace_worktree_isolation_enabled": True},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_BRAIN_ENDPOINT", "http://127.0.0.1:8000/api/system")
    monkeypatch.setenv("AI_BRAIN_RUNNER_CONFIG", str(config_path))
    monkeypatch.setenv("AI_BRAIN_RUNNER_ID", "runner-worktree-reuse")
    monkeypatch.setenv("AI_BRAIN_RUNNER_TOKEN", "runner-token")
    namespace: dict[str, object] = {"__name__": "runner_worktree_reuse_test"}
    exec(compile(_runner_agent_python(), "runner_agent.py", "exec"), namespace)

    retained_workspace, retained_isolation = namespace["_prepare_isolated_workspace"](  # type: ignore[index,operator]
        {
            "id": "runner_task_retained",
            "request_config": {
                "rd_collaboration_run_id": "run-1",
                "rd_work_item_id": "work-1",
            },
        },
        str(repository),
    )
    completed: list[dict] = []
    namespace["_append_logs"] = lambda *args, **kwargs: None  # type: ignore[index]
    namespace["_complete_task"] = lambda task_id, **kwargs: completed.append(  # type: ignore[index]
        {"task_id": task_id, **kwargs}
    )
    namespace["_resolve_executor_command"] = lambda _executor_type: (  # type: ignore[index]
        "codex",
        ["codex", "exec"],
        None,
    )
    namespace["_stream_process_output"] = lambda **_kwargs: (0, '{"summary":"ok"}', False, None)  # type: ignore[index]

    namespace["_run_task"](  # type: ignore[index,operator]
        {
            "executor_type": "codex",
            "id": "runner_task_rework",
            "instruction": "complete the retained worktree task",
            "request_config": {
                "reuse_workspace": True,
                "workspace_isolation": retained_isolation,
            },
            "timeout_seconds": 5,
            "workspace_root": str(repository),
        }
    )

    assert completed[0]["status"] == "succeeded"
    assert completed[0]["result_json"]["execution_workspace_root"] == retained_workspace


def test_generated_runner_rebuilds_missing_retained_workspace_from_upstream_commit(
    tmp_path,
    monkeypatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.email", "runner-test@example.com")
    _git(repository, "config", "user.name", "Runner Test")
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "fixture")
    base_sha = _git(repository, "rev-parse", "HEAD")
    (repository / "artifact.md").write_text("upstream delivery\n", encoding="utf-8")
    _git(repository, "add", "artifact.md")
    _git(repository, "commit", "-m", "upstream delivery")
    upstream_sha = _git(repository, "rev-parse", "HEAD")
    _git(repository, "reset", "--hard", base_sha)

    config_path = tmp_path / "runner_config.json"
    config_path.write_text(
        json.dumps(
            {
                "runner": {
                    "executor_types": ["codex"],
                    "id": "runner-missing-retained-worktree",
                    "workspace_roots": [str(repository)],
                },
                "safety": {"workspace_worktree_isolation_enabled": True},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_BRAIN_ENDPOINT", "http://127.0.0.1:8000/api/system")
    monkeypatch.setenv("AI_BRAIN_RUNNER_CONFIG", str(config_path))
    monkeypatch.setenv("AI_BRAIN_RUNNER_ID", "runner-missing-retained-worktree")
    monkeypatch.setenv("AI_BRAIN_RUNNER_TOKEN", "runner-token")
    namespace: dict[str, object] = {"__name__": "runner_missing_retained_test"}
    exec(compile(_runner_agent_python(), "runner_agent.py", "exec"), namespace)
    completed: list[dict] = []
    namespace["_append_logs"] = lambda *args, **kwargs: None  # type: ignore[index]
    namespace["_complete_task"] = lambda task_id, **kwargs: completed.append(  # type: ignore[index]
        {"task_id": task_id, **kwargs}
    )
    namespace["_resolve_executor_command"] = lambda _executor_type: (  # type: ignore[index]
        "codex",
        ["codex", "exec"],
        None,
    )
    namespace["_stream_process_output"] = lambda **_kwargs: (  # type: ignore[index]
        0,
        json.dumps(
            {
                "git_delivery": {
                    "local_commit_sha": upstream_sha,
                    "working_branch": "rd/run-1/work-1",
                },
                "summary": "verified",
            }
        ),
        False,
        None,
    )
    missing_path = tmp_path / ".ai-brain-worktrees" / "repository" / "missing"

    namespace["_run_task"](  # type: ignore[index,operator]
        {
            "executor_type": "codex",
            "id": "runner_task_rebuild_missing_retained",
            "instruction": "verify upstream delivery",
            "request_config": {
                "rd_collaboration_run_id": "run-1",
                "rd_work_item_id": "work-1",
                "reuse_workspace": True,
                "upstream_delivery_commit_shas": [upstream_sha],
                "workspace_isolation": {
                    "base_workspace_root": str(repository),
                    "branch_name": "rd/run-1/work-1",
                    "mode": "git_worktree",
                    "worktree_path": str(missing_path),
                },
            },
            "timeout_seconds": 5,
            "workspace_root": str(repository),
        }
    )

    assert completed[0]["status"] == "succeeded"
    rebuilt_path = completed[0]["result_json"]["execution_workspace_root"]
    assert _git(rebuilt_path, "rev-parse", "HEAD") == upstream_sha


def test_generated_ai_reviewer_executes_read_only_without_creating_a_worktree(
    tmp_path,
    monkeypatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.email", "runner-test@example.com")
    _git(repository, "config", "user.name", "Runner Test")
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "fixture")

    config_path = tmp_path / "runner_config.json"
    config_path.write_text(
        json.dumps(
            {
                "runner": {
                    "executor_types": ["codex"],
                    "id": "runner-ai-reviewer",
                    "workspace_roots": [str(repository)],
                },
                "safety": {"workspace_worktree_isolation_enabled": True},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_BRAIN_ENDPOINT", "http://127.0.0.1:8000/api/system")
    monkeypatch.setenv("AI_BRAIN_RUNNER_CONFIG", str(config_path))
    monkeypatch.setenv("AI_BRAIN_RUNNER_ID", "runner-ai-reviewer")
    monkeypatch.setenv("AI_BRAIN_RUNNER_TOKEN", "runner-token")
    namespace: dict[str, object] = {"__name__": "runner_ai_reviewer_test"}
    exec(compile(_runner_agent_python(), "runner_agent.py", "exec"), namespace)

    completed: list[dict] = []
    namespace["_append_logs"] = lambda *args, **kwargs: None  # type: ignore[index]
    namespace["_complete_task"] = lambda task_id, **kwargs: completed.append(  # type: ignore[index]
        {"task_id": task_id, **kwargs}
    )
    namespace["_prepare_isolated_workspace"] = lambda *_args, **_kwargs: (_ for _ in ()).throw(  # type: ignore[index]
        AssertionError("AI reviewer must not create another worktree")
    )
    namespace["_resolve_executor_command"] = lambda _executor_type: (  # type: ignore[index]
        "codex",
        ["codex", "exec"],
        None,
    )
    namespace["_stream_process_output"] = lambda **_kwargs: (  # type: ignore[index]
        0,
        json.dumps(
            {
                "comment": "review passed",
                "decision": "approve",
                "findings": [],
                "reviewed_commit_sha": _git(repository, "rev-parse", "HEAD"),
                "summary": "independent review passed",
            }
        ),
        False,
        None,
    )

    namespace["_run_task"](  # type: ignore[index,operator]
        {
            "executor_type": "codex",
            "id": "runner_task_ai_review",
            "instruction": "review the frozen commit without changing files",
            "request_config": {"read_only": True},
            "task_kind": "work_item_review",
            "timeout_seconds": 5,
            "workspace_root": str(repository),
        }
    )

    assert completed[0]["status"] == "succeeded"
    assert completed[0]["result_json"]["parsed_output"]["decision"] == "approve"
    assert _git(repository, "status", "--porcelain") == ""


def test_generated_ai_reviewer_reconstructs_frozen_commit_in_detached_worktree(
    tmp_path,
    monkeypatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.email", "runner-test@example.com")
    _git(repository, "config", "user.name", "Runner Test")
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "fixture")
    base_sha = _git(repository, "rev-parse", "HEAD")
    (repository / "artifact.md").write_text("frozen delivery\n", encoding="utf-8")
    _git(repository, "add", "artifact.md")
    _git(repository, "commit", "-m", "delivery")
    delivery_sha = _git(repository, "rev-parse", "HEAD")
    _git(repository, "reset", "--hard", base_sha)

    config_path = tmp_path / "runner_config.json"
    config_path.write_text(
        json.dumps(
            {
                "runner": {
                    "executor_types": ["codex"],
                    "id": "runner-detached-ai-reviewer",
                    "workspace_roots": [str(repository)],
                },
                "safety": {"workspace_worktree_isolation_enabled": True},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_BRAIN_ENDPOINT", "http://127.0.0.1:8000/api/system")
    monkeypatch.setenv("AI_BRAIN_RUNNER_CONFIG", str(config_path))
    monkeypatch.setenv("AI_BRAIN_RUNNER_ID", "runner-detached-ai-reviewer")
    monkeypatch.setenv("AI_BRAIN_RUNNER_TOKEN", "runner-token")
    namespace: dict[str, object] = {"__name__": "runner_detached_ai_reviewer_test"}
    exec(compile(_runner_agent_python(), "runner_agent.py", "exec"), namespace)

    completed: list[dict] = []
    observed_workspaces: list[str] = []
    namespace["_append_logs"] = lambda *args, **kwargs: None  # type: ignore[index]
    namespace["_complete_task"] = lambda task_id, **kwargs: completed.append(  # type: ignore[index]
        {"task_id": task_id, **kwargs}
    )
    namespace["_resolve_executor_command"] = lambda _executor_type: (  # type: ignore[index]
        "codex",
        ["codex", "exec"],
        None,
    )

    def execute_review(**kwargs):
        workspace_root = kwargs["workspace_root"]
        observed_workspaces.append(workspace_root)
        assert _git(workspace_root, "rev-parse", "HEAD") == delivery_sha
        assert (Path(workspace_root) / "artifact.md").read_text(encoding="utf-8") == (
            "frozen delivery\n"
        )
        return (
            0,
            json.dumps(
                {
                    "comment": "review passed",
                    "decision": "approve",
                    "findings": [],
                    "reviewed_commit_sha": delivery_sha,
                    "summary": "independent review passed",
                }
            ),
            False,
            None,
        )

    namespace["_stream_process_output"] = execute_review  # type: ignore[index]
    namespace["_run_work_item_review_task"](  # type: ignore[index,operator]
        {
            "executor_type": "codex",
            "id": "runner_task_detached_ai_review",
            "input_payload": {"expected_commit_sha": delivery_sha},
            "instruction": "review the frozen commit without changing files",
            "request_config": {"read_only": True},
            "task_kind": "work_item_review",
            "timeout_seconds": 5,
            "workspace_root": str(repository),
        }
    )

    assert completed[0]["status"] == "succeeded"
    assert completed[0]["result_json"]["parsed_output"]["decision"] == "approve"
    assert observed_workspaces[0] != str(repository)
    assert _git(repository, "rev-parse", "HEAD") == base_sha
    assert "runner_task_detached_ai_review" not in _git(repository, "worktree", "list")


def test_generated_quality_gate_reports_a_missing_workspace_as_failed_evidence(
    tmp_path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "runner_config.json"
    config_path.write_text(
        json.dumps(
            {
                "runner": {
                    "executor_types": ["codex"],
                    "id": "runner-quality-gate",
                    "workspace_roots": [str(tmp_path)],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_BRAIN_ENDPOINT", "http://127.0.0.1:8000/api/system")
    monkeypatch.setenv("AI_BRAIN_RUNNER_CONFIG", str(config_path))
    monkeypatch.setenv("AI_BRAIN_RUNNER_ID", "runner-quality-gate")
    monkeypatch.setenv("AI_BRAIN_RUNNER_TOKEN", "runner-token")
    namespace: dict[str, object] = {"__name__": "runner_quality_gate_test"}
    exec(compile(_runner_agent_python(), "runner_agent.py", "exec"), namespace)
    completed: list[dict] = []
    namespace["_complete_task"] = lambda task_id, **kwargs: completed.append(  # type: ignore[index]
        {"task_id": task_id, **kwargs}
    )
    missing_workspace = tmp_path / "missing-worktree"

    namespace["_run_quality_gate_task"](  # type: ignore[index,operator]
        {
            "id": "quality-gate-missing-workspace",
            "input_payload": {
                "acceptance_cases": [
                    {
                        "case_id": "case-1",
                        "verification": {
                            "path": "artifact.md",
                            "required_text": ["expected"],
                            "type": "file_contains",
                        },
                    }
                ],
                "checks": [],
            },
            "timeout_seconds": 5,
            "workspace_root": str(missing_workspace),
        }
    )

    assert completed[0]["status"] == "succeeded"
    assert completed[0]["result_json"]["acceptance_results"][0]["status"] == "failed"
    assert "unavailable" in completed[0]["result_json"]["acceptance_results"][0]["summary"]


def test_generated_quality_gate_reconstructs_the_frozen_commit_in_a_detached_worktree(
    tmp_path,
    monkeypatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.email", "runner-test@example.com")
    _git(repository, "config", "user.name", "Runner Test")
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "fixture")
    base_sha = _git(repository, "rev-parse", "HEAD")
    (repository / "artifact.md").write_text("expected marker\n", encoding="utf-8")
    _git(repository, "add", "artifact.md")
    _git(repository, "commit", "-m", "delivery")
    delivery_sha = _git(repository, "rev-parse", "HEAD")
    _git(repository, "reset", "--hard", base_sha)

    config_path = tmp_path / "runner_config.json"
    config_path.write_text(
        json.dumps(
            {
                "runner": {
                    "executor_types": ["codex"],
                    "id": "runner-detached-quality-gate",
                    "workspace_roots": [str(repository)],
                },
                "safety": {"workspace_worktree_isolation_enabled": True},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_BRAIN_ENDPOINT", "http://127.0.0.1:8000/api/system")
    monkeypatch.setenv("AI_BRAIN_RUNNER_CONFIG", str(config_path))
    monkeypatch.setenv("AI_BRAIN_RUNNER_ID", "runner-detached-quality-gate")
    monkeypatch.setenv("AI_BRAIN_RUNNER_TOKEN", "runner-token")
    namespace: dict[str, object] = {"__name__": "runner_detached_quality_gate_test"}
    exec(compile(_runner_agent_python(), "runner_agent.py", "exec"), namespace)
    completed: list[dict] = []
    namespace["_complete_task"] = lambda task_id, **kwargs: completed.append(  # type: ignore[index]
        {"task_id": task_id, **kwargs}
    )

    namespace["_run_quality_gate_task"](  # type: ignore[index,operator]
        {
            "id": "quality-gate-detached-commit",
            "input_payload": {
                "acceptance_cases": [
                    {
                        "case_id": "case-1",
                        "verification": {
                            "path": "artifact.md",
                            "required_text": ["expected marker"],
                            "type": "file_contains",
                        },
                    }
                ],
                "base_branch": f"{delivery_sha}^",
                "checks": [],
                "expected_commit_sha": delivery_sha,
            },
            "timeout_seconds": 5,
            "workspace_root": str(repository),
        }
    )

    acceptance = completed[0]["result_json"]["acceptance_results"][0]
    assert completed[0]["status"] == "succeeded"
    assert acceptance["commit_sha"] == delivery_sha
    assert acceptance["status"] == "passed"
    assert _git(repository, "rev-parse", "HEAD") == base_sha
    assert "quality-gate-detached-commit" not in _git(repository, "worktree", "list")


def test_generated_runner_extracts_final_delivery_json_from_executor_transcript(
    tmp_path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "runner_config.json"
    config_path.write_text(
        json.dumps(
            {
                "runner": {
                    "executor_types": ["codex"],
                    "id": "runner-json-parser",
                    "workspace_roots": [str(tmp_path)],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_BRAIN_ENDPOINT", "http://127.0.0.1:8000/api/system")
    monkeypatch.setenv("AI_BRAIN_RUNNER_CONFIG", str(config_path))
    monkeypatch.setenv("AI_BRAIN_RUNNER_ID", "runner-json-parser")
    monkeypatch.setenv("AI_BRAIN_RUNNER_TOKEN", "runner-token")
    namespace: dict[str, object] = {"__name__": "runner_json_parser_test"}
    exec(compile(_runner_agent_python(), "runner_agent.py", "exec"), namespace)

    parsed = namespace["_parsed_json_output"](  # type: ignore[index,operator]
        """Codex completed its work.
command arguments: {"path":"docs/e2e/artifact.md"}
{
  "summary": "artifact committed",
  "git_delivery": {
    "local_commit_sha": "7e741ccfbf1e951f14ea7f35453b3f5ea5fb1f15",
    "working_branch": "rd/run-1/work-1"
  }
}
"""
    )

    assert parsed == {
        "summary": "artifact committed",
        "git_delivery": {
            "local_commit_sha": "7e741ccfbf1e951f14ea7f35453b3f5ea5fb1f15",
            "working_branch": "rd/run-1/work-1",
        },
    }


def test_generated_quality_gate_ignores_runner_workspace_patch_artifact(
    tmp_path,
    monkeypatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.email", "runner-test@example.com")
    _git(repository, "config", "user.name", "Runner Test")
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "fixture")
    artifact = repository / "docs" / "e2e" / "delivery.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("delivered\n", encoding="utf-8")
    _git(repository, "add", "docs/e2e/delivery.md")
    _git(repository, "commit", "-m", "delivery")
    (repository / ".ai-brain-task.patch").write_text("runner evidence\n", encoding="utf-8")

    config_path = tmp_path / "runner_config.json"
    config_path.write_text(
        json.dumps(
            {
                "runner": {
                    "executor_types": ["codex"],
                    "id": "runner-quality-gate",
                    "workspace_roots": [str(repository)],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_BRAIN_ENDPOINT", "http://127.0.0.1:8000/api/system")
    monkeypatch.setenv("AI_BRAIN_RUNNER_CONFIG", str(config_path))
    monkeypatch.setenv("AI_BRAIN_RUNNER_ID", "runner-quality-gate")
    monkeypatch.setenv("AI_BRAIN_RUNNER_TOKEN", "runner-token")
    namespace: dict[str, object] = {"__name__": "runner_quality_gate_test"}
    exec(compile(_runner_agent_python(), "runner_agent.py", "exec"), namespace)

    summary = namespace["_quality_gate_change_summary"](  # type: ignore[index,operator]
        str(repository),
        "HEAD^",
    )

    assert summary["changed_files"] == ["docs/e2e/delivery.md"]
    assert summary["changed_file_count"] == 1


def test_generated_acceptance_check_ignores_runner_workspace_patch_artifact(
    tmp_path,
    monkeypatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.email", "runner-test@example.com")
    _git(repository, "config", "user.name", "Runner Test")
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "fixture")
    artifact = repository / "docs" / "e2e" / "delivery.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("delivered\n", encoding="utf-8")
    _git(repository, "add", "docs/e2e/delivery.md")
    _git(repository, "commit", "-m", "delivery")
    (repository / ".ai-brain-task.patch").write_text("runner evidence\n", encoding="utf-8")

    config_path = tmp_path / "runner_config.json"
    config_path.write_text(
        json.dumps(
            {
                "runner": {
                    "executor_types": ["codex"],
                    "id": "runner-acceptance-check",
                    "workspace_roots": [str(repository)],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_BRAIN_ENDPOINT", "http://127.0.0.1:8000/api/system")
    monkeypatch.setenv("AI_BRAIN_RUNNER_CONFIG", str(config_path))
    monkeypatch.setenv("AI_BRAIN_RUNNER_ID", "runner-acceptance-check")
    monkeypatch.setenv("AI_BRAIN_RUNNER_TOKEN", "runner-token")
    namespace: dict[str, object] = {"__name__": "runner_acceptance_check_test"}
    exec(compile(_runner_agent_python(), "runner_agent.py", "exec"), namespace)

    verification = {
        "type": "file_contains",
        "path": "docs/e2e/delivery.md",
        "required_text": ["delivered"],
    }
    results = namespace["_verify_acceptance_cases"](  # type: ignore[index,operator]
        acceptance_cases=[{"case_id": "case-delivery", "verification": verification}],
        task_id="runner_task_acceptance",
        workspace_root=str(repository),
    )

    assert results[0]["status"] == "passed"
    assert results[0]["input_fingerprint"] == acceptance_verification_fingerprint(verification)
