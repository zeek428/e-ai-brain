from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

PRODUCT_CONFIG_TABLES = {
    "product_git_repositories": "product_git_repositories",
    "product_modules": "product_modules",
    "product_version_branch_configs": "product_version_branch_configs",
    "product_versions": "product_versions",
    "products": "products",
    "related_systems": "related_systems",
}


class ProductConfigWriteRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._delete_missing = delete_missing
        self._upsert_audit_events = upsert_audit_events

    def save_product_config(self, payload: dict[str, Any]) -> None:
        products = payload.get("products", {})
        versions = payload.get("product_versions", {})
        branch_configs = payload.get("product_version_branch_configs", {})
        modules = payload.get("product_modules", {})
        repositories = payload.get("product_git_repositories", {})
        related_systems = payload.get("related_systems", {})
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "related_systems", related_systems)
                    self._delete_missing(
                        cursor,
                        "product_version_branch_configs",
                        branch_configs,
                    )
                    self._delete_missing(cursor, "product_git_repositories", repositories)
                    self._delete_missing(cursor, "product_modules", modules)
                    self._delete_missing(cursor, "product_versions", versions)
                    self._delete_missing(cursor, "products", products)
                self.upsert_products(cursor, products)
                self.upsert_product_versions(cursor, versions)
                self.upsert_product_modules(cursor, modules)
                self.upsert_product_git_repositories(cursor, repositories)
                self.upsert_product_version_branch_configs(cursor, branch_configs)
                self.upsert_related_systems(cursor, related_systems)

    def save_product_config_record(
        self,
        collection_name: str,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        upsert_by_collection = {
            "product_git_repositories": self.upsert_product_git_repositories,
            "product_modules": self.upsert_product_modules,
            "product_version_branch_configs": self.upsert_product_version_branch_configs,
            "product_versions": self.upsert_product_versions,
            "products": self.upsert_products,
            "related_systems": self.upsert_related_systems,
        }
        upsert = upsert_by_collection.get(collection_name)
        if upsert is None:
            raise ValueError(f"Unsupported product config collection: {collection_name}")
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                upsert(cursor, {record["id"]: record})
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def delete_product_config_record(
        self,
        collection_name: str,
        record_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        table_name = PRODUCT_CONFIG_TABLES.get(collection_name)
        if table_name is None:
            raise ValueError(f"Unsupported product config collection: {collection_name}")
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {table_name} WHERE id = %s",  # noqa: S608
                    (record_id,),
                )
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def upsert_products(self, cursor, products: dict[str, dict[str, Any]]) -> None:
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

    def upsert_product_versions(self, cursor, versions: dict[str, dict[str, Any]]) -> None:
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

    def upsert_product_modules(self, cursor, modules: dict[str, dict[str, Any]]) -> None:
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

    def upsert_product_git_repositories(
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

    def upsert_product_version_branch_configs(
        self,
        cursor,
        branch_configs: dict[str, dict[str, Any]],
    ) -> None:
        for branch_config in branch_configs.values():
            cursor.execute(
                """
                INSERT INTO product_version_branch_configs (
                  id, product_id, version_id, repository_id, base_branch, working_branch,
                  branch_status, creation_source, description, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  repository_id = EXCLUDED.repository_id,
                  base_branch = EXCLUDED.base_branch,
                  working_branch = EXCLUDED.working_branch,
                  branch_status = EXCLUDED.branch_status,
                  creation_source = EXCLUDED.creation_source,
                  description = EXCLUDED.description,
                  updated_at = now()
                """,
                (
                    branch_config["id"],
                    branch_config["product_id"],
                    branch_config["version_id"],
                    branch_config["repository_id"],
                    branch_config.get("base_branch", "main"),
                    branch_config["working_branch"],
                    branch_config.get("branch_status", "not_created"),
                    branch_config.get("creation_source", "manual"),
                    branch_config.get("description"),
                ),
            )

    def upsert_related_systems(
        self,
        cursor,
        related_systems: dict[str, dict[str, Any]],
    ) -> None:
        for related_system in related_systems.values():
            cursor.execute(
                """
                INSERT INTO related_systems (
                  id, product_id, code, name, description, owner_team, status,
                  display_order, updated_at
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
                    related_system["id"],
                    related_system.get("product_id"),
                    related_system["code"],
                    related_system["name"],
                    related_system.get("description"),
                    related_system.get("owner_team"),
                    related_system.get("status", "active"),
                    related_system.get("display_order", 0),
                ),
            )
