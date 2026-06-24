from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.core.repositories.product_config_lists import ProductConfigListRepository
from app.core.repositories.product_config_writes import ProductConfigWriteRepository


class ProductConfigReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._list_repository = ProductConfigListRepository(connect)
        self._write_repository = ProductConfigWriteRepository(
            connect,
            delete_missing=delete_missing,
            upsert_audit_events=upsert_audit_events,
        )

    def load_product_config(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                products = self._load_products(cursor)
                versions = self._load_product_versions(cursor)
                modules = self._load_product_modules(cursor)
                repositories = self._load_product_git_repositories(cursor)
                branch_configs = self._load_product_version_branch_configs(cursor)
                related_systems = self._load_related_systems(cursor)
        return {
            "product_git_repositories": repositories,
            "product_modules": modules,
            "product_version_branch_configs": branch_configs,
            "product_versions": versions,
            "products": products,
            "related_systems": related_systems,
        }

    def list_products(self, *, active_only: bool = False) -> list[dict[str, Any]]:
        return self._list_repository.list_product_summaries(active_only=active_only)

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, code, name, description, owner_team, status, display_order
                    FROM products
                    WHERE id = %s
                    """,
                    (product_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return {
            "code": row[1],
            "description": row[3],
            "display_order": row[6],
            "id": row[0],
            "name": row[2],
            "owner_team": row[4],
            "status": row[5],
        }

    def get_product_version(self, version_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, product_id, code, name, description, status, start_date, release_date
                    FROM product_versions
                    WHERE id = %s
                    """,
                    (version_id,),
                )
                row = cursor.fetchone()
        return _row_to_product_version(row) if row is not None else None

    def get_product_git_repository(self, repository_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, product_id, repo_type, name, remote_url, git_provider, project_id,
                           project_path, credential_ref, default_branch, root_path, status
                    FROM product_git_repositories
                    WHERE id = %s
                    """,
                    (repository_id,),
                )
                row = cursor.fetchone()
        return _row_to_product_git_repository(row) if row is not None else None

    def get_product_module(self, module_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, product_id, code, name, description, owner_team,
                           status, display_order
                    FROM product_modules
                    WHERE id = %s
                    """,
                    (module_id,),
                )
                row = cursor.fetchone()
        return _row_to_product_module(row) if row is not None else None

    def product_module_has_related_records(self, product_id: str, module_code: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                      EXISTS (
                        SELECT 1 FROM requirements
                        WHERE product_id = %s AND module_code = %s
                      )
                      OR EXISTS (
                        SELECT 1 FROM ai_tasks
                        WHERE product_id = %s AND module_code = %s
                      )
                      OR EXISTS (
                        SELECT 1 FROM bugs
                        WHERE product_id = %s AND module_code = %s
                      )
                    """,
                    (
                        product_id,
                        module_code,
                        product_id,
                        module_code,
                        product_id,
                        module_code,
                    ),
                )
                row = cursor.fetchone()
        return bool(row[0]) if row is not None else False

    def product_version_has_related_records(self, version_id: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                      EXISTS (
                        SELECT 1 FROM requirements
                        WHERE version_id = %s
                      )
                      OR EXISTS (
                        SELECT 1 FROM ai_tasks
                        WHERE version_id = %s
                      )
                      OR EXISTS (
                        SELECT 1 FROM bugs
                        WHERE version_id = %s
                      )
                      OR EXISTS (
                        SELECT 1 FROM product_version_branch_configs
                        WHERE version_id = %s
                      )
                    """,
                    (version_id, version_id, version_id, version_id),
                )
                row = cursor.fetchone()
        return bool(row[0]) if row is not None else False

    def get_related_system(self, system_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, code, name, description, owner_team, status,
                           display_order, product_id
                    FROM related_systems
                    WHERE id = %s
                    """,
                    (system_id,),
                )
                row = cursor.fetchone()
        return _row_to_related_system(row) if row is not None else None

    def get_related_system_by_code(self, code: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, code, name, description, owner_team, status,
                           display_order, product_id
                    FROM related_systems
                    WHERE code = %s
                    """,
                    (code,),
                )
                row = cursor.fetchone()
        return _row_to_related_system(row) if row is not None else None

    def get_product_version_branch_config(
        self,
        branch_config_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT b.id, b.product_id, b.version_id, b.repository_id, b.base_branch,
                           b.working_branch, b.branch_status, b.creation_source, b.description,
                           r.name, r.git_provider, r.project_path, r.default_branch
                    FROM product_version_branch_configs b
                    JOIN product_git_repositories r ON r.id = b.repository_id
                    WHERE b.id = %s
                    """,
                    (branch_config_id,),
                )
                row = cursor.fetchone()
        return _row_to_product_version_branch_config(row) if row is not None else None

    def list_product_versions(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        where_clauses = ["product_id = %s"]
        params: list[Any] = [product_id]
        if active_only:
            where_clauses.append("status = 'active'")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, product_id, code, name, description, status, start_date, release_date
                    FROM product_versions
                    WHERE {' AND '.join(where_clauses)}
                    ORDER BY code
                    """,
                    tuple(params),
                )
                return [_row_to_product_version(row) for row in cursor.fetchall()]

    def list_product_modules(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        where_clauses = ["product_id = %s"]
        params: list[Any] = [product_id]
        if active_only:
            where_clauses.append("status = 'active'")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, product_id, code, name, description, owner_team,
                           status, display_order
                    FROM product_modules
                    WHERE {' AND '.join(where_clauses)}
                    ORDER BY display_order, code
                    """,
                    tuple(params),
                )
                return [_row_to_product_module(row) for row in cursor.fetchall()]

    def list_product_git_repositories(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        where_clauses = ["product_id = %s"]
        params: list[Any] = [product_id]
        if active_only:
            where_clauses.append("status = 'active'")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, product_id, repo_type, name, remote_url, git_provider, project_id,
                           project_path, credential_ref, default_branch, root_path, status
                    FROM product_git_repositories
                    WHERE {' AND '.join(where_clauses)}
                    ORDER BY name
                    """,
                    tuple(params),
                )
                return [
                    _row_to_product_git_repository(row)
                    for row in cursor.fetchall()
                ]

    def list_product_version_branch_configs(self, version_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT b.id, b.product_id, b.version_id, b.repository_id, b.base_branch,
                           b.working_branch, b.branch_status, b.creation_source, b.description,
                           r.name, r.git_provider, r.project_path, r.default_branch
                    FROM product_version_branch_configs b
                    JOIN product_git_repositories r ON r.id = b.repository_id
                    WHERE b.version_id = %s
                    ORDER BY r.name, b.working_branch
                    """,
                    (version_id,),
                )
                return [
                    _row_to_product_version_branch_config(row)
                    for row in cursor.fetchall()
                ]

    def list_related_systems(
        self,
        *,
        active_only: bool = False,
        product_id: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if product_id is not None:
            where_clauses.append("product_id = %s")
            params.append(product_id)
        if active_only:
            where_clauses.append("status = 'active'")
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, code, name, description, owner_team, status,
                           display_order, product_id
                    FROM related_systems
                    {where_clause}
                    ORDER BY display_order, code
                    """,
                    tuple(params),
                )
                return [
                    _row_to_related_system(row)
                    for row in cursor.fetchall()
                ]

    def save_product_config(self, payload: dict[str, Any]) -> None:
        self._write_repository.save_product_config(payload)

    def save_product_config_record(
        self,
        collection_name: str,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._write_repository.save_product_config_record(
            collection_name,
            record,
            audit_event=audit_event,
        )

    def delete_product_config_record(
        self,
        collection_name: str,
        record_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._write_repository.delete_product_config_record(
            collection_name,
            record_id,
            audit_event=audit_event,
        )

    def upsert_products(self, cursor, products: dict[str, dict[str, Any]]) -> None:
        self._write_repository.upsert_products(cursor, products)

    def upsert_product_versions(self, cursor, versions: dict[str, dict[str, Any]]) -> None:
        self._write_repository.upsert_product_versions(cursor, versions)

    def upsert_product_modules(self, cursor, modules: dict[str, dict[str, Any]]) -> None:
        self._write_repository.upsert_product_modules(cursor, modules)

    def upsert_product_git_repositories(
        self,
        cursor,
        repositories: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_product_git_repositories(cursor, repositories)

    def upsert_product_version_branch_configs(
        self,
        cursor,
        branch_configs: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_product_version_branch_configs(cursor, branch_configs)

    def upsert_related_systems(
        self,
        cursor,
        related_systems: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_related_systems(cursor, related_systems)

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
            row[0]: _row_to_product_version(row)
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
            row[0]: _row_to_product_module(row)
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
            row[0]: _row_to_product_git_repository(row)
            for row in cursor.fetchall()
        }

    def _load_product_version_branch_configs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT b.id, b.product_id, b.version_id, b.repository_id, b.base_branch,
                   b.working_branch, b.branch_status, b.creation_source, b.description,
                   r.name, r.git_provider, r.project_path, r.default_branch
            FROM product_version_branch_configs b
            JOIN product_git_repositories r ON r.id = b.repository_id
            ORDER BY b.product_id, b.version_id, r.name
            """
        )
        return {
            row[0]: _row_to_product_version_branch_config(row)
            for row in cursor.fetchall()
        }

    def _load_related_systems(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, code, name, description, owner_team, status, display_order, product_id
            FROM related_systems
            ORDER BY display_order, code
            """
        )
        return {
            row[0]: _row_to_related_system(row)
            for row in cursor.fetchall()
        }

    def count_product_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        owner_team: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._list_repository.count_product_summaries(
            active_only=active_only,
            code=code,
            name=name,
            owner_team=owner_team,
            status=status,
        )

    def list_product_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        owner_team: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "display_order",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]:
        return self._list_repository.list_product_summaries(
            active_only=active_only,
            code=code,
            name=name,
            owner_team=owner_team,
            status=status,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def list_product_version_summaries(
        self,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        where_clause = "WHERE v.status = 'active'" if active_only else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT v.id, v.product_id, v.code, v.name, v.description, v.status,
                           v.start_date, v.release_date, p.code, p.name
                    FROM product_versions v
                    JOIN products p ON p.id = v.product_id
                    {where_clause}
                    ORDER BY p.code, v.code
                    """
                )
                return [
                    {
                        "code": row[2],
                        "description": row[4],
                        "id": row[0],
                        "name": row[3],
                        "product_code": row[8],
                        "product_id": row[1],
                        "product_name": row[9],
                        "release_date": row[7].isoformat() if row[7] else None,
                        "start_date": row[6].isoformat() if row[6] else None,
                        "status": row[5],
                    }
                    for row in cursor.fetchall()
                ]

    def count_product_version_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._list_repository.count_product_version_summaries(
            active_only=active_only,
            code=code,
            name=name,
            product=product,
            product_id=product_id,
            status=status,
        )

    def list_product_version_summaries_page(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "code",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]:
        return self._list_repository.list_product_version_summaries_page(
            active_only=active_only,
            code=code,
            name=name,
            product=product,
            product_id=product_id,
            status=status,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )


def _row_to_product_module(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "code": row[2],
        "description": row[4],
        "display_order": row[7],
        "id": row[0],
        "name": row[3],
        "owner_team": row[5],
        "product_id": row[1],
        "status": row[6],
    }


def _row_to_product_version(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "code": row[2],
        "description": row[4],
        "id": row[0],
        "name": row[3],
        "product_id": row[1],
        "release_date": row[7].isoformat() if row[7] else None,
        "start_date": row[6].isoformat() if row[6] else None,
        "status": row[5],
    }


def _row_to_product_version_branch_config(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "base_branch": row[4],
        "branch_status": row[6],
        "creation_source": row[7],
        "description": row[8],
        "id": row[0],
        "product_id": row[1],
        "repository_default_branch": row[12],
        "repository_id": row[3],
        "repository_name": row[9],
        "repository_path": row[11],
        "repository_provider": row[10],
        "version_id": row[2],
        "working_branch": row[5],
    }


def _row_to_product_git_repository(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
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


def _row_to_related_system(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "code": row[1],
        "description": row[3],
        "display_order": row[6],
        "id": row[0],
        "name": row[2],
        "owner_team": row[4],
        "product_id": row[7],
        "status": row[5],
    }
