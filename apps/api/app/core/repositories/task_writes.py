from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.core.store import DEFAULT_BRAIN_APP_ID


class TaskWriteRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._delete_missing = delete_missing

    def save_ai_tasks(self, payload: dict[str, Any]) -> None:
        ai_tasks = payload.get("ai_tasks", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "ai_tasks", ai_tasks)
                self.upsert_ai_tasks(cursor, ai_tasks)

    def upsert_ai_tasks(self, cursor, ai_tasks: dict[str, dict[str, Any]]) -> None:
        for task in ai_tasks.values():
            created_at = task.get("created_at")
            updated_at = task.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO ai_tasks (
                  id, brain_app_id, requirement_id, task_type, title, status,
                  product_id, version_id, collaboration_run_id, work_item_id,
                  module_code, requirement_snapshot, product_context, input_json, output_json,
                  current_step, error_code, error_message, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb,
                  %s::jsonb, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  brain_app_id = EXCLUDED.brain_app_id,
                  requirement_id = EXCLUDED.requirement_id,
                  task_type = EXCLUDED.task_type,
                  title = EXCLUDED.title,
                  status = EXCLUDED.status,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  collaboration_run_id = EXCLUDED.collaboration_run_id,
                  work_item_id = EXCLUDED.work_item_id,
                  module_code = EXCLUDED.module_code,
                  requirement_snapshot = EXCLUDED.requirement_snapshot,
                  product_context = EXCLUDED.product_context,
                  input_json = EXCLUDED.input_json,
                  output_json = EXCLUDED.output_json,
                  current_step = EXCLUDED.current_step,
                  error_code = EXCLUDED.error_code,
                  error_message = EXCLUDED.error_message,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                WHERE NOT (
                  ai_tasks.work_item_id IS NOT NULL
                  AND ai_tasks.status = 'cancelled'
                  AND EXCLUDED.status <> 'cancelled'
                )
                """,
                (
                    task["id"],
                    task.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
                    task["requirement_id"],
                    task["task_type"],
                    task["title"],
                    task.get("status", "draft"),
                    task["product_id"],
                    task["version_id"],
                    task.get("collaboration_run_id"),
                    task.get("work_item_id"),
                    task.get("module_code"),
                    json.dumps(task.get("requirement_snapshot"), ensure_ascii=False),
                    json.dumps(task.get("product_context", {}), ensure_ascii=False),
                    json.dumps(task.get("input_json", {}), ensure_ascii=False),
                    json.dumps(task.get("output_json"), ensure_ascii=False),
                    task.get("current_step"),
                    task.get("error_code"),
                    task.get("error_message"),
                    task["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def save_workflow_runtime(self, payload: dict[str, Any]) -> None:
        graph_runs = payload.get("graph_runs", {})
        graph_checkpoints = payload.get("graph_checkpoints", {})
        human_reviews = payload.get("human_reviews", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "human_reviews", human_reviews)
                    self._delete_missing(cursor, "graph_checkpoints", graph_checkpoints)
                    self._delete_missing(cursor, "graph_runs", graph_runs)
                self.upsert_graph_runs(cursor, graph_runs)
                self.upsert_graph_checkpoints(cursor, graph_checkpoints)
                self.upsert_human_reviews(cursor, human_reviews)

    def upsert_graph_runs(self, cursor, graph_runs: dict[str, dict[str, Any]]) -> None:
        for graph_run in graph_runs.values():
            created_at = graph_run.get("created_at") or graph_run.get("started_at")
            updated_at = graph_run.get("updated_at") or graph_run.get("completed_at") or created_at
            cursor.execute(
                """
                INSERT INTO graph_runs (
                  id, ai_task_id, task_type, status, current_step, checkpoint_id,
                  runtime, node_path, state_snapshot, subject_type, subject_id,
                  thread_id, graph_definition, graph_version, started_at, completed_at,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb,
                  %s, %s, %s, %s, %s, COALESCE(%s::timestamptz, now()), %s::timestamptz,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  ai_task_id = EXCLUDED.ai_task_id,
                  task_type = EXCLUDED.task_type,
                  status = EXCLUDED.status,
                  current_step = EXCLUDED.current_step,
                  checkpoint_id = EXCLUDED.checkpoint_id,
                  runtime = EXCLUDED.runtime,
                  node_path = EXCLUDED.node_path,
                  state_snapshot = EXCLUDED.state_snapshot,
                  subject_type = EXCLUDED.subject_type,
                  subject_id = EXCLUDED.subject_id,
                  thread_id = EXCLUDED.thread_id,
                  graph_definition = EXCLUDED.graph_definition,
                  graph_version = EXCLUDED.graph_version,
                  completed_at = EXCLUDED.completed_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    graph_run["id"],
                    graph_run.get("ai_task_id"),
                    graph_run["task_type"],
                    graph_run["status"],
                    graph_run.get("current_step"),
                    graph_run.get("checkpoint_id"),
                    graph_run.get("runtime"),
                    json.dumps(graph_run.get("node_path", []), ensure_ascii=False),
                    json.dumps(graph_run.get("state_snapshot", {}), ensure_ascii=False),
                    graph_run.get("subject_type"),
                    graph_run.get("subject_id"),
                    graph_run.get("thread_id"),
                    graph_run.get("graph_definition"),
                    graph_run.get("graph_version"),
                    graph_run.get("started_at"),
                    graph_run.get("completed_at"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_graph_checkpoints(
        self,
        cursor,
        graph_checkpoints: dict[str, dict[str, Any]],
    ) -> None:
        for checkpoint in graph_checkpoints.values():
            created_at = checkpoint.get("created_at")
            updated_at = checkpoint.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO graph_checkpoints (
                  id, graph_run_id, ai_task_id, current_step, state_snapshot, subject_type,
                  subject_id, thread_id, graph_definition, graph_version, created_at,
                  updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  graph_run_id = EXCLUDED.graph_run_id,
                  ai_task_id = EXCLUDED.ai_task_id,
                  current_step = EXCLUDED.current_step,
                  state_snapshot = EXCLUDED.state_snapshot,
                  subject_type = EXCLUDED.subject_type,
                  subject_id = EXCLUDED.subject_id,
                  thread_id = EXCLUDED.thread_id,
                  graph_definition = EXCLUDED.graph_definition,
                  graph_version = EXCLUDED.graph_version,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    checkpoint["id"],
                    checkpoint["graph_run_id"],
                    checkpoint.get("ai_task_id"),
                    checkpoint["current_step"],
                    json.dumps(checkpoint.get("state_snapshot", {}), ensure_ascii=False),
                    checkpoint.get("subject_type"),
                    checkpoint.get("subject_id"),
                    checkpoint.get("thread_id"),
                    checkpoint.get("graph_definition"),
                    checkpoint.get("graph_version"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_human_reviews(self, cursor, human_reviews: dict[str, dict[str, Any]]) -> None:
        for review in human_reviews.values():
            created_at = review.get("created_at")
            updated_at = review.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO human_reviews (
                  id, ai_task_id, stage, status, version, content, edited_content,
                  decision_reason, decided_by, questions, decided_at, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb,
                  %s::timestamptz, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  ai_task_id = EXCLUDED.ai_task_id,
                  stage = EXCLUDED.stage,
                  status = EXCLUDED.status,
                  version = EXCLUDED.version,
                  content = EXCLUDED.content,
                  edited_content = EXCLUDED.edited_content,
                  decision_reason = EXCLUDED.decision_reason,
                  decided_by = EXCLUDED.decided_by,
                  questions = EXCLUDED.questions,
                  decided_at = EXCLUDED.decided_at,
                  updated_at = EXCLUDED.updated_at
                WHERE NOT (
                  human_reviews.status = 'cancelled'
                  AND EXCLUDED.status <> 'cancelled'
                  AND EXISTS (
                    SELECT 1
                    FROM ai_tasks AS linked_task
                    WHERE linked_task.id = human_reviews.ai_task_id
                      AND linked_task.work_item_id IS NOT NULL
                  )
                )
                """,
                (
                    review["id"],
                    review["ai_task_id"],
                    review["stage"],
                    review.get("status", "pending"),
                    review.get("version", 1),
                    json.dumps(review.get("content", {}), ensure_ascii=False),
                    json.dumps(review.get("edited_content"), ensure_ascii=False),
                    review.get("decision_reason"),
                    review.get("decided_by"),
                    json.dumps(review.get("questions", []), ensure_ascii=False),
                    review.get("decided_at"),
                    created_at,
                    updated_at,
                ),
            )
