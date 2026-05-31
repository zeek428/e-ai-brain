from __future__ import annotations

from copy import deepcopy
from time import sleep
from typing import Any, Protocol

from app.core.store import MemoryStore

STATE_KEY = "memory_store"
PRODUCT_CONFIG_FIELDS = [
    "products",
    "product_versions",
    "product_modules",
    "product_git_repositories",
]
REQUIREMENT_FIELDS = [
    "requirements",
]
AI_TASK_FIELDS = [
    "ai_tasks",
]
WORKFLOW_RUNTIME_FIELDS = [
    "graph_runs",
    "graph_checkpoints",
    "human_reviews",
]
COLLECTION_FIELDS = [
    "products",
    "product_versions",
    "product_modules",
    "product_git_repositories",
    "related_systems",
    "model_gateway_configs",
    "model_gateway_logs",
    "gitlab_mr_snapshots",
    "code_review_reports",
    "knowledge_documents",
    "knowledge_deposits",
    "mock_writebacks",
    "bugs",
    "requirements",
    "ai_tasks",
    "graph_runs",
    "graph_checkpoints",
    "human_reviews",
    "audit_events",
    "counters",
]


class SnapshotRepository(Protocol):
    def load(self) -> dict[str, Any] | None: ...

    def save(self, payload: dict[str, Any]) -> None: ...


class ProductConfigRepository(Protocol):
    def load_product_config(self) -> dict[str, Any] | None: ...

    def save_product_config(self, payload: dict[str, Any]) -> None: ...


class RequirementRepository(Protocol):
    def load_requirements(self) -> dict[str, Any] | None: ...

    def save_requirements(self, payload: dict[str, Any]) -> None: ...


class AiTaskRepository(Protocol):
    def load_ai_tasks(self) -> dict[str, Any] | None: ...

    def save_ai_tasks(self, payload: dict[str, Any]) -> None: ...


class WorkflowRuntimeRepository(Protocol):
    def load_workflow_runtime(self) -> dict[str, Any] | None: ...

    def save_workflow_runtime(self, payload: dict[str, Any]) -> None: ...


def _product_config_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in PRODUCT_CONFIG_FIELDS}


def _requirements_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in REQUIREMENT_FIELDS}


def _ai_tasks_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in AI_TASK_FIELDS}


def _workflow_runtime_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in WORKFLOW_RUNTIME_FIELDS}


def _ai_tasks_merge_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    merge_payload = _ai_tasks_payload(payload or {})
    for task in merge_payload.get("ai_tasks", {}).values():
        for field in ("graph_run_ids", "review_ids"):
            if task.get(field) == []:
                task.pop(field)
    return merge_payload


def _merge_collection_payload(
    payload: dict[str, Any],
    overlay: dict[str, Any],
    fields: list[str],
    *,
    merge_items: bool = False,
) -> None:
    for field in fields:
        existing_items = deepcopy(payload.get(field, {}))
        overlay_items = deepcopy(overlay.get(field, {}))
        if merge_items:
            merged_items = existing_items
            for item_id, item in overlay_items.items():
                merged_items[item_id] = {
                    **deepcopy(merged_items.get(item_id, {})),
                    **item,
                }
            payload[field] = merged_items
        else:
            payload[field] = {**existing_items, **overlay_items}


def _repository_load_product_config(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_product_config = getattr(repository, "load_product_config", None)
    if load_product_config is None:
        return None
    return load_product_config()


def _repository_save_product_config(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_product_config = getattr(repository, "save_product_config", None)
    if save_product_config is not None:
        save_product_config(_product_config_payload(payload))


def _repository_load_requirements(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_requirements = getattr(repository, "load_requirements", None)
    if load_requirements is None:
        return None
    return load_requirements()


def _repository_save_requirements(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_requirements = getattr(repository, "save_requirements", None)
    if save_requirements is not None:
        save_requirements(_requirements_payload(payload))


def _repository_load_ai_tasks(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_ai_tasks = getattr(repository, "load_ai_tasks", None)
    if load_ai_tasks is None:
        return None
    return load_ai_tasks()


def _repository_save_ai_tasks(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_ai_tasks = getattr(repository, "save_ai_tasks", None)
    if save_ai_tasks is not None:
        save_ai_tasks(_ai_tasks_payload(payload))


def _repository_load_workflow_runtime(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_workflow_runtime = getattr(repository, "load_workflow_runtime", None)
    if load_workflow_runtime is None:
        return None
    return load_workflow_runtime()


def _repository_save_workflow_runtime(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_workflow_runtime = getattr(repository, "save_workflow_runtime", None)
    if save_workflow_runtime is not None:
        save_workflow_runtime(_workflow_runtime_payload(payload))


def _has_product_config_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in PRODUCT_CONFIG_FIELDS)


def _has_requirement_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in REQUIREMENT_FIELDS)


def _has_ai_task_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in AI_TASK_FIELDS)


def _has_workflow_runtime_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in WORKFLOW_RUNTIME_FIELDS)


def _max_numeric_suffix(items: dict[str, dict[str, Any]], prefix: str) -> int:
    marker = f"{prefix}_"
    max_value = 0
    for item_id in items:
        if not item_id.startswith(marker):
            continue
        suffix = item_id.removeprefix(marker)
        if suffix.isdigit():
            max_value = max(max_value, int(suffix))
    return max_value


def _sync_product_config_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    for prefix, field in [
        ("product", "products"),
        ("version", "product_versions"),
        ("module", "product_modules"),
        ("repo", "product_git_repositories"),
    ]:
        counters[prefix] = max(
            counters.get(prefix, 0),
            _max_numeric_suffix(payload.get(field, {}), prefix),
        )
    payload["counters"] = counters


def _sync_requirement_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["requirement"] = max(
        counters.get("requirement", 0),
        _max_numeric_suffix(payload.get("requirements", {}), "requirement"),
    )
    payload["counters"] = counters


def _sync_ai_task_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["task"] = max(
        counters.get("task", 0),
        _max_numeric_suffix(payload.get("ai_tasks", {}), "task"),
    )
    payload["counters"] = counters


def _sync_workflow_runtime_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    for prefix, field in [
        ("graph_run", "graph_runs"),
        ("checkpoint", "graph_checkpoints"),
        ("review", "human_reviews"),
    ]:
        counters[prefix] = max(
            counters.get(prefix, 0),
            _max_numeric_suffix(payload.get(field, {}), prefix),
        )
    payload["counters"] = counters


def _drop_requirements_without_product_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    versions = payload.get("product_versions", {})
    requirements = payload.get("requirements", {})
    payload["requirements"] = {
        requirement_id: requirement
        for requirement_id, requirement in requirements.items()
        if requirement.get("product_id") in products
        and requirement.get("version_id") in versions
        and versions[requirement["version_id"]].get("product_id") == requirement.get("product_id")
    }


def _drop_ai_tasks_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    versions = payload.get("product_versions", {})
    requirements = payload.get("requirements", {})
    ai_tasks = payload.get("ai_tasks", {})
    payload["ai_tasks"] = {
        task_id: task
        for task_id, task in ai_tasks.items()
        if task.get("product_id") in products
        and task.get("version_id") in versions
        and task.get("requirement_id") in requirements
        and versions[task["version_id"]].get("product_id") == task.get("product_id")
        and requirements[task["requirement_id"]].get("product_id") == task.get("product_id")
        and requirements[task["requirement_id"]].get("version_id") == task.get("version_id")
    }


def _ensure_ai_task_defaults(payload: dict[str, Any]) -> None:
    for task in payload.get("ai_tasks", {}).values():
        task.setdefault("graph_run_ids", [])
        task.setdefault("input_json", {})
        task.setdefault("product_context", {})
        task.setdefault("review_ids", [])


def _drop_workflow_runtime_without_tasks(payload: dict[str, Any]) -> None:
    ai_tasks = payload.get("ai_tasks", {})
    graph_runs = payload.get("graph_runs", {})
    payload["graph_runs"] = {
        run_id: run
        for run_id, run in graph_runs.items()
        if run.get("ai_task_id") in ai_tasks
    }
    graph_runs = payload["graph_runs"]
    graph_checkpoints = payload.get("graph_checkpoints", {})
    payload["graph_checkpoints"] = {
        checkpoint_id: checkpoint
        for checkpoint_id, checkpoint in graph_checkpoints.items()
        if checkpoint.get("ai_task_id") in ai_tasks
        and checkpoint.get("graph_run_id") in graph_runs
    }
    human_reviews = payload.get("human_reviews", {})
    payload["human_reviews"] = {
        review_id: review
        for review_id, review in human_reviews.items()
        if review.get("ai_task_id") in ai_tasks
    }


def _sync_task_runtime_links(payload: dict[str, Any]) -> None:
    ai_tasks = payload.get("ai_tasks", {})
    for review_id, review in payload.get("human_reviews", {}).items():
        task = ai_tasks.get(review.get("ai_task_id"))
        if task is None:
            continue
        review_ids = task.setdefault("review_ids", [])
        if review_id not in review_ids:
            review_ids.append(review_id)
    for run_id, graph_run in payload.get("graph_runs", {}).items():
        task = ai_tasks.get(graph_run.get("ai_task_id"))
        if task is None:
            continue
        graph_run_ids = task.setdefault("graph_run_ids", [])
        if run_id not in graph_run_ids:
            graph_run_ids.append(run_id)
        if graph_run.get("checkpoint_id"):
            task["checkpoint_id"] = graph_run["checkpoint_id"]


class PersistentMemoryStore(MemoryStore):
    def __init__(self, repository: SnapshotRepository) -> None:
        super().__init__()
        self.repository = repository

    @classmethod
    def from_repository(cls, repository: SnapshotRepository) -> PersistentMemoryStore:
        store = cls(repository)
        payload = repository.load() or {}
        product_config_payload = _repository_load_product_config(repository)
        has_structured_product_config = _has_product_config_items(product_config_payload)
        if has_structured_product_config:
            _merge_collection_payload(
                payload,
                _product_config_payload(product_config_payload),
                PRODUCT_CONFIG_FIELDS,
            )
            _sync_product_config_counters(payload)
        requirements_payload = _repository_load_requirements(repository)
        if _has_requirement_items(requirements_payload):
            _merge_collection_payload(
                payload,
                _requirements_payload(requirements_payload),
                REQUIREMENT_FIELDS,
            )
            _sync_requirement_counters(payload)
        ai_tasks_payload = _repository_load_ai_tasks(repository)
        has_structured_ai_tasks = _has_ai_task_items(ai_tasks_payload)
        if has_structured_ai_tasks:
            _merge_collection_payload(
                payload,
                _ai_tasks_merge_payload(ai_tasks_payload),
                AI_TASK_FIELDS,
                merge_items=True,
            )
            _sync_ai_task_counters(payload)
        workflow_runtime_payload = _repository_load_workflow_runtime(repository)
        has_structured_workflow_runtime = _has_workflow_runtime_items(workflow_runtime_payload)
        if has_structured_workflow_runtime:
            _merge_collection_payload(
                payload,
                _workflow_runtime_payload(workflow_runtime_payload),
                WORKFLOW_RUNTIME_FIELDS,
            )
            _sync_workflow_runtime_counters(payload)
        if has_structured_product_config:
            _drop_requirements_without_product_context(payload)
        if has_structured_product_config or _has_requirement_items(requirements_payload):
            _drop_ai_tasks_without_context(payload)
        if has_structured_ai_tasks:
            _drop_workflow_runtime_without_tasks(payload)
        _ensure_ai_task_defaults(payload)
        _sync_task_runtime_links(payload)
        if payload:
            store.load_payload(payload)
        return store

    def to_payload(self) -> dict[str, Any]:
        return {field: deepcopy(getattr(self, field)) for field in COLLECTION_FIELDS}

    def load_payload(self, payload: dict[str, Any]) -> None:
        self.reset()
        for field in COLLECTION_FIELDS:
            if field in payload:
                setattr(self, field, deepcopy(payload[field]))

    def persist(self) -> None:
        payload = self.to_payload()
        self.repository.save(payload)
        _repository_save_product_config(self.repository, payload)
        _repository_save_requirements(self.repository, payload)
        _repository_save_ai_tasks(self.repository, payload)
        _repository_save_workflow_runtime(self.repository, payload)


class PostgresSnapshotRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self):
        import psycopg

        last_error: Exception | None = None
        for _ in range(20):
            try:
                return psycopg.connect(self.database_url, autocommit=True)
            except psycopg.OperationalError as exc:
                last_error = exc
                sleep(0.5)
        raise last_error or RuntimeError("PostgreSQL connection failed")

    def load(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT payload FROM app_state_snapshots WHERE key = %s",
                    (STATE_KEY,),
                )
                row = cursor.fetchone()
        return row[0] if row else None

    def save(self, payload: dict[str, Any]) -> None:
        import json

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app_state_snapshots (key, payload, updated_at)
                    VALUES (%s, %s::jsonb, now())
                    ON CONFLICT (key) DO UPDATE SET
                      payload = EXCLUDED.payload,
                      updated_at = now()
                    """,
                    (STATE_KEY, json.dumps(payload, ensure_ascii=False)),
                )

    def load_product_config(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                products = self._load_products(cursor)
                versions = self._load_product_versions(cursor)
                modules = self._load_product_modules(cursor)
                repositories = self._load_product_git_repositories(cursor)
        return {
            "product_git_repositories": repositories,
            "product_modules": modules,
            "product_versions": versions,
            "products": products,
        }

    def load_requirements(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                requirements = self._load_requirements(cursor)
        return {"requirements": requirements}

    def load_ai_tasks(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                ai_tasks = self._load_ai_tasks(cursor)
        return {"ai_tasks": ai_tasks}

    def load_workflow_runtime(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                graph_runs = self._load_graph_runs(cursor)
                graph_checkpoints = self._load_graph_checkpoints(cursor)
                human_reviews = self._load_human_reviews(cursor)
        return {
            "graph_checkpoints": graph_checkpoints,
            "graph_runs": graph_runs,
            "human_reviews": human_reviews,
        }

    def save_product_config(self, payload: dict[str, Any]) -> None:
        products = payload.get("products", {})
        versions = payload.get("product_versions", {})
        modules = payload.get("product_modules", {})
        repositories = payload.get("product_git_repositories", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "product_git_repositories", repositories)
                self._delete_missing(cursor, "product_modules", modules)
                self._delete_missing(cursor, "product_versions", versions)
                self._delete_missing(cursor, "products", products)
                self._upsert_products(cursor, products)
                self._upsert_product_versions(cursor, versions)
                self._upsert_product_modules(cursor, modules)
                self._upsert_product_git_repositories(cursor, repositories)

    def save_requirements(self, payload: dict[str, Any]) -> None:
        requirements = payload.get("requirements", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "requirements", requirements)
                self._upsert_requirements(cursor, requirements)

    def save_ai_tasks(self, payload: dict[str, Any]) -> None:
        ai_tasks = payload.get("ai_tasks", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "ai_tasks", ai_tasks)
                self._upsert_ai_tasks(cursor, ai_tasks)

    def save_workflow_runtime(self, payload: dict[str, Any]) -> None:
        graph_runs = payload.get("graph_runs", {})
        graph_checkpoints = payload.get("graph_checkpoints", {})
        human_reviews = payload.get("human_reviews", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "human_reviews", human_reviews)
                self._delete_missing(cursor, "graph_checkpoints", graph_checkpoints)
                self._delete_missing(cursor, "graph_runs", graph_runs)
                self._upsert_graph_runs(cursor, graph_runs)
                self._upsert_graph_checkpoints(cursor, graph_checkpoints)
                self._upsert_human_reviews(cursor, human_reviews)

    def _load_products(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, code, name, description, owner_team, status, display_order
            FROM products
            ORDER BY display_order, code
            """
        )
        return {
            row[0]: {
                "code": row[1],
                "description": row[3],
                "display_order": row[6],
                "id": row[0],
                "name": row[2],
                "owner_team": row[4],
                "status": row[5],
            }
            for row in cursor.fetchall()
        }

    def _load_product_versions(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, code, name, description, status, start_date, release_date
            FROM product_versions
            ORDER BY product_id, code
            """
        )
        return {
            row[0]: {
                "code": row[2],
                "description": row[4],
                "id": row[0],
                "name": row[3],
                "product_id": row[1],
                "release_date": row[7].isoformat() if row[7] else None,
                "start_date": row[6].isoformat() if row[6] else None,
                "status": row[5],
            }
            for row in cursor.fetchall()
        }

    def _load_product_modules(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, code, name, description, owner_team, status, display_order
            FROM product_modules
            ORDER BY product_id, display_order, code
            """
        )
        return {
            row[0]: {
                "code": row[2],
                "description": row[4],
                "display_order": row[7],
                "id": row[0],
                "name": row[3],
                "owner_team": row[5],
                "product_id": row[1],
                "status": row[6],
            }
            for row in cursor.fetchall()
        }

    def _load_product_git_repositories(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, repo_type, name, remote_url, git_provider, project_id,
                   project_path, credential_ref, default_branch, root_path, status
            FROM product_git_repositories
            ORDER BY product_id, name
            """
        )
        return {
            row[0]: {
                "credential_ref": row[8],
                "default_branch": row[9],
                "git_provider": row[5],
                "id": row[0],
                "name": row[3],
                "product_id": row[1],
                "project_id": row[6],
                "project_path": row[7],
                "remote_url": row[4],
                "repo_type": row[2],
                "root_path": row[10],
                "status": row[11],
            }
            for row in cursor.fetchall()
        }

    def _load_requirements(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, title, product_id, version_id, module_code, description, priority,
                   status, created_by, approval_comment, rejection_reason, task_ids,
                   created_at, updated_at
            FROM requirements
            ORDER BY created_at DESC, id
            """
        )
        requirements = {}
        for row in cursor.fetchall():
            requirement = {
                "content": row[5],
                "created_at": row[12].isoformat() if row[12] else None,
                "created_by": row[8],
                "id": row[0],
                "module_code": row[4],
                "priority": row[6],
                "product_id": row[2],
                "status": row[7],
                "task_ids": list(row[11] or []),
                "title": row[1],
                "updated_at": row[13].isoformat() if row[13] else None,
                "version_id": row[3],
            }
            if row[9] is not None:
                requirement["approval_comment"] = row[9]
            if row[10] is not None:
                requirement["rejection_reason"] = row[10]
            requirements[row[0]] = requirement
        return requirements

    def _load_ai_tasks(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, requirement_id, task_type, title, status, product_id, version_id,
                   module_code, requirement_snapshot, product_context, input_json, output_json,
                   current_step, error_code, error_message, created_by, created_at, updated_at
            FROM ai_tasks
            ORDER BY id
            """
        )
        ai_tasks = {}
        for row in cursor.fetchall():
            task = {
                "created_at": row[16].isoformat() if row[16] else None,
                "created_by": row[15],
                "current_step": row[12],
                "error_code": row[13],
                "error_message": row[14],
                "graph_run_ids": [],
                "id": row[0],
                "input_json": dict(row[10] or {}),
                "module_code": row[7],
                "output_json": row[11],
                "product_context": dict(row[9] or {}),
                "product_id": row[5],
                "requirement_id": row[1],
                "requirement_snapshot": row[8],
                "review_ids": [],
                "status": row[4],
                "task_type": row[2],
                "title": row[3],
                "updated_at": row[17].isoformat() if row[17] else None,
                "version_id": row[6],
            }
            ai_tasks[row[0]] = task
        return ai_tasks

    def _load_graph_runs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, ai_task_id, task_type, status, current_step, checkpoint_id,
                   state_snapshot, started_at, completed_at
            FROM graph_runs
            ORDER BY started_at, id
            """
        )
        return {
            row[0]: {
                "ai_task_id": row[1],
                "checkpoint_id": row[5],
                "completed_at": row[8].isoformat() if row[8] else None,
                "current_step": row[4],
                "id": row[0],
                "started_at": row[7].isoformat() if row[7] else None,
                "state_snapshot": dict(row[6] or {}),
                "status": row[3],
                "task_type": row[2],
            }
            for row in cursor.fetchall()
        }

    def _load_graph_checkpoints(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, graph_run_id, ai_task_id, current_step, state_snapshot, created_at
            FROM graph_checkpoints
            ORDER BY created_at, id
            """
        )
        return {
            row[0]: {
                "ai_task_id": row[2],
                "created_at": row[5].isoformat() if row[5] else None,
                "current_step": row[3],
                "graph_run_id": row[1],
                "id": row[0],
                "state_snapshot": dict(row[4] or {}),
            }
            for row in cursor.fetchall()
        }

    def _load_human_reviews(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, ai_task_id, stage, status, version, content, edited_content,
                   decision_reason, decided_by, questions, decided_at, created_at, updated_at
            FROM human_reviews
            ORDER BY created_at, id
            """
        )
        human_reviews = {}
        for row in cursor.fetchall():
            review = {
                "ai_task_id": row[1],
                "content": dict(row[5] or {}),
                "created_at": row[11].isoformat() if row[11] else None,
                "decided_at": row[10].isoformat() if row[10] else None,
                "decided_by": row[8],
                "decision_reason": row[7],
                "edited_content": row[6],
                "id": row[0],
                "questions": list(row[9] or []),
                "stage": row[2],
                "status": row[3],
                "updated_at": row[12].isoformat() if row[12] else None,
                "version": row[4],
            }
            if review["edited_content"] is None:
                review.pop("edited_content")
            if review["decision_reason"] is None:
                review.pop("decision_reason")
            if review["decided_by"] is None:
                review.pop("decided_by")
            if review["decided_at"] is None:
                review.pop("decided_at")
            if not review["questions"]:
                review.pop("questions")
            human_reviews[row[0]] = review
        return human_reviews

    def _delete_missing(
        self,
        cursor,
        table_name: str,
        items: dict[str, dict[str, Any]],
    ) -> None:
        if not items:
            cursor.execute(f"DELETE FROM {table_name}")  # noqa: S608
            return
        placeholders = ", ".join(["%s"] * len(items))
        cursor.execute(
            f"DELETE FROM {table_name} WHERE id NOT IN ({placeholders})",  # noqa: S608
            tuple(items.keys()),
        )

    def _upsert_products(self, cursor, products: dict[str, dict[str, Any]]) -> None:
        for product in products.values():
            cursor.execute(
                """
                INSERT INTO products (
                  id, code, name, description, owner_team, status, display_order, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                  code = EXCLUDED.code,
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  owner_team = EXCLUDED.owner_team,
                  status = EXCLUDED.status,
                  display_order = EXCLUDED.display_order,
                  updated_at = now()
                """,
                (
                    product["id"],
                    product["code"],
                    product["name"],
                    product.get("description"),
                    product.get("owner_team"),
                    product.get("status", "active"),
                    product.get("display_order", 0),
                ),
            )

    def _upsert_product_versions(self, cursor, versions: dict[str, dict[str, Any]]) -> None:
        for version in versions.values():
            cursor.execute(
                """
                INSERT INTO product_versions (
                  id, product_id, code, name, description, status, start_date, release_date,
                  updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  code = EXCLUDED.code,
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  status = EXCLUDED.status,
                  start_date = EXCLUDED.start_date,
                  release_date = EXCLUDED.release_date,
                  updated_at = now()
                """,
                (
                    version["id"],
                    version["product_id"],
                    version["code"],
                    version["name"],
                    version.get("description"),
                    version.get("status", "planning"),
                    version.get("start_date"),
                    version.get("release_date"),
                ),
            )

    def _upsert_product_modules(self, cursor, modules: dict[str, dict[str, Any]]) -> None:
        for module in modules.values():
            cursor.execute(
                """
                INSERT INTO product_modules (
                  id, product_id, code, name, description, owner_team, status, display_order,
                  updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  code = EXCLUDED.code,
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  owner_team = EXCLUDED.owner_team,
                  status = EXCLUDED.status,
                  display_order = EXCLUDED.display_order,
                  updated_at = now()
                """,
                (
                    module["id"],
                    module["product_id"],
                    module["code"],
                    module["name"],
                    module.get("description"),
                    module.get("owner_team"),
                    module.get("status", "active"),
                    module.get("display_order", 0),
                ),
            )

    def _upsert_product_git_repositories(
        self,
        cursor,
        repositories: dict[str, dict[str, Any]],
    ) -> None:
        for repository in repositories.values():
            cursor.execute(
                """
                INSERT INTO product_git_repositories (
                  id, product_id, repo_type, name, remote_url, git_provider, project_id,
                  project_path, credential_ref, default_branch, root_path, status, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  repo_type = EXCLUDED.repo_type,
                  name = EXCLUDED.name,
                  remote_url = EXCLUDED.remote_url,
                  git_provider = EXCLUDED.git_provider,
                  project_id = EXCLUDED.project_id,
                  project_path = EXCLUDED.project_path,
                  credential_ref = EXCLUDED.credential_ref,
                  default_branch = EXCLUDED.default_branch,
                  root_path = EXCLUDED.root_path,
                  status = EXCLUDED.status,
                  updated_at = now()
                """,
                (
                    repository["id"],
                    repository["product_id"],
                    repository.get("repo_type", "code"),
                    repository["name"],
                    repository.get("remote_url"),
                    repository.get("git_provider", "gitlab"),
                    repository.get("project_id"),
                    repository.get("project_path"),
                    repository.get("credential_ref"),
                    repository.get("default_branch", "main"),
                    repository.get("root_path", "/"),
                    repository.get("status", "active"),
                ),
            )

    def _upsert_requirements(self, cursor, requirements: dict[str, dict[str, Any]]) -> None:
        import json

        for requirement in requirements.values():
            created_at = requirement.get("created_at")
            updated_at = requirement.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO requirements (
                  id, title, product_id, version_id, module_code, description, priority,
                  status, created_by, approval_comment, rejection_reason, task_ids,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  title = EXCLUDED.title,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  module_code = EXCLUDED.module_code,
                  description = EXCLUDED.description,
                  priority = EXCLUDED.priority,
                  status = EXCLUDED.status,
                  created_by = EXCLUDED.created_by,
                  approval_comment = EXCLUDED.approval_comment,
                  rejection_reason = EXCLUDED.rejection_reason,
                  task_ids = EXCLUDED.task_ids,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    requirement["id"],
                    requirement["title"],
                    requirement["product_id"],
                    requirement["version_id"],
                    requirement.get("module_code"),
                    requirement["content"],
                    requirement.get("priority", "P1"),
                    requirement.get("status", "pending_approval"),
                    requirement["created_by"],
                    requirement.get("approval_comment"),
                    requirement.get("rejection_reason"),
                    json.dumps(requirement.get("task_ids", []), ensure_ascii=False),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_ai_tasks(self, cursor, ai_tasks: dict[str, dict[str, Any]]) -> None:
        import json

        for task in ai_tasks.values():
            created_at = task.get("created_at")
            updated_at = task.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO ai_tasks (
                  id, requirement_id, task_type, title, status, product_id, version_id,
                  module_code, requirement_snapshot, product_context, input_json, output_json,
                  current_step, error_code, error_message, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb,
                  %s::jsonb, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  requirement_id = EXCLUDED.requirement_id,
                  task_type = EXCLUDED.task_type,
                  title = EXCLUDED.title,
                  status = EXCLUDED.status,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
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
                """,
                (
                    task["id"],
                    task["requirement_id"],
                    task["task_type"],
                    task["title"],
                    task.get("status", "draft"),
                    task["product_id"],
                    task["version_id"],
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

    def _upsert_graph_runs(self, cursor, graph_runs: dict[str, dict[str, Any]]) -> None:
        import json

        for graph_run in graph_runs.values():
            cursor.execute(
                """
                INSERT INTO graph_runs (
                  id, ai_task_id, task_type, status, current_step, checkpoint_id,
                  state_snapshot, started_at, completed_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s::jsonb,
                  COALESCE(%s::timestamptz, now()), %s::timestamptz
                )
                ON CONFLICT (id) DO UPDATE SET
                  ai_task_id = EXCLUDED.ai_task_id,
                  task_type = EXCLUDED.task_type,
                  status = EXCLUDED.status,
                  current_step = EXCLUDED.current_step,
                  checkpoint_id = EXCLUDED.checkpoint_id,
                  state_snapshot = EXCLUDED.state_snapshot,
                  completed_at = EXCLUDED.completed_at
                """,
                (
                    graph_run["id"],
                    graph_run["ai_task_id"],
                    graph_run["task_type"],
                    graph_run["status"],
                    graph_run.get("current_step"),
                    graph_run.get("checkpoint_id"),
                    json.dumps(graph_run.get("state_snapshot", {}), ensure_ascii=False),
                    graph_run.get("started_at"),
                    graph_run.get("completed_at"),
                ),
            )

    def _upsert_graph_checkpoints(
        self,
        cursor,
        graph_checkpoints: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for checkpoint in graph_checkpoints.values():
            cursor.execute(
                """
                INSERT INTO graph_checkpoints (
                  id, graph_run_id, ai_task_id, current_step, state_snapshot, created_at
                )
                VALUES (%s, %s, %s, %s, %s::jsonb, COALESCE(%s::timestamptz, now()))
                ON CONFLICT (id) DO UPDATE SET
                  graph_run_id = EXCLUDED.graph_run_id,
                  ai_task_id = EXCLUDED.ai_task_id,
                  current_step = EXCLUDED.current_step,
                  state_snapshot = EXCLUDED.state_snapshot
                """,
                (
                    checkpoint["id"],
                    checkpoint["graph_run_id"],
                    checkpoint["ai_task_id"],
                    checkpoint["current_step"],
                    json.dumps(checkpoint.get("state_snapshot", {}), ensure_ascii=False),
                    checkpoint.get("created_at"),
                ),
            )

    def _upsert_human_reviews(self, cursor, human_reviews: dict[str, dict[str, Any]]) -> None:
        import json

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
