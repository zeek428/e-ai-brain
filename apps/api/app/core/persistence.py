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


def _product_config_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in PRODUCT_CONFIG_FIELDS}


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


def _has_product_config_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in PRODUCT_CONFIG_FIELDS)


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


class PersistentMemoryStore(MemoryStore):
    def __init__(self, repository: SnapshotRepository) -> None:
        super().__init__()
        self.repository = repository

    @classmethod
    def from_repository(cls, repository: SnapshotRepository) -> PersistentMemoryStore:
        store = cls(repository)
        payload = repository.load() or {}
        product_config_payload = _repository_load_product_config(repository)
        if _has_product_config_items(product_config_payload):
            payload.update(_product_config_payload(product_config_payload))
            _sync_product_config_counters(payload)
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
