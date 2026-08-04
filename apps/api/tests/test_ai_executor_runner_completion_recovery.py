from __future__ import annotations

from app.services import ai_executor_runners


def test_terminal_quality_gate_completion_is_reconciled_idempotently(monkeypatch) -> None:
    calls: list[tuple[object, dict, str]] = []

    def capture(store, *, task, runner_id) -> None:
        calls.append((store, task, runner_id))

    monkeypatch.setattr(ai_executor_runners, "_sync_runner_completion_to_ai_task", capture)
    store = object()
    task = {"id": "quality-1", "status": "succeeded", "task_kind": "quality_gate"}

    assert ai_executor_runners._reconcile_terminal_quality_gate_completion(
        store,
        task=task,
        runner_id="runner-verifier",
    )
    assert calls == [(store, task, "runner-verifier")]


def test_terminal_non_quality_gate_completion_is_not_reconciled(monkeypatch) -> None:
    monkeypatch.setattr(
        ai_executor_runners,
        "_sync_runner_completion_to_ai_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not reconcile")),
    )

    assert not ai_executor_runners._reconcile_terminal_quality_gate_completion(
        object(),
        task={"id": "coding-1", "status": "succeeded", "task_kind": "coding"},
        runner_id="runner-developer",
    )
