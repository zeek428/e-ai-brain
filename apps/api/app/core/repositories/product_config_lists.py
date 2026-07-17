from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class ProductConfigListRepository:
    def __init__(self, connect: Callable[..., AbstractContextManager[Any]]) -> None:
        self._connect = connect

    def _product_summary_where(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        owner_team: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
    ) -> tuple[str, list[Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if active_only:
            where_clauses.append("p.status = 'active'")
        if code is not None:
            code_pattern = f"%{code}%"
            where_clauses.append("(p.code ILIKE %s OR p.id ILIKE %s)")
            params.extend([code_pattern, code_pattern])
        if name is not None:
            where_clauses.append("p.name ILIKE %s")
            params.append(f"%{name}%")
        if owner_team is not None:
            where_clauses.append("p.owner_team ILIKE %s")
            params.append(f"%{owner_team}%")
        if product_scope_ids is not None:
            if product_scope_ids:
                where_clauses.append("p.id = ANY(%s)")
                params.append(product_scope_ids)
            else:
                where_clauses.append("FALSE")
        if status is not None:
            where_clauses.append("p.status = %s")
            params.append(status)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        return where_clause, params

    def count_product_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        owner_team: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
    ) -> int:
        where_clause, params = self._product_summary_where(
            active_only=active_only,
            code=code,
            name=name,
            owner_team=owner_team,
            product_scope_ids=product_scope_ids,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM products p
                    {where_clause}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
        return int(row[0] if row else 0)

    def list_product_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        owner_team: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "display_order",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]:
        where_clause, params = self._product_summary_where(
            active_only=active_only,
            code=code,
            name=name,
            owner_team=owner_team,
            product_scope_ids=product_scope_ids,
            status=status,
        )
        sort_columns = {
            "code": "p.code",
            "current_version_name": "current_version.name",
            "display_order": "p.display_order",
            "id": "p.id",
            "module_count": "COALESCE(module_counts.module_count, 0)",
            "name": "p.name",
            "owner_team": "p.owner_team",
            "status": "p.status",
        }
        order_column = sort_columns.get(sort_by, sort_columns["display_order"])
        order_direction = "ASC" if sort_order == "asc" else "DESC"
        paging_clause = ""
        if limit is not None:
            paging_clause += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            paging_clause += " OFFSET %s"
            params.append(offset)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT p.id, p.code, p.name, p.description, p.owner_team,
                           p.status, p.display_order, current_version.code,
                           current_version.name, COALESCE(module_counts.module_count, 0)
                    FROM products p
                    LEFT JOIN LATERAL (
                        SELECT code, name
                        FROM product_versions v
                        WHERE v.product_id = p.id
                        ORDER BY CASE v.status
                            WHEN 'active' THEN 0
                            WHEN 'testing' THEN 1
                            WHEN 'ready_for_release' THEN 2
                            WHEN 'deploying' THEN 3
                            WHEN 'released' THEN 4
                            WHEN 'planning' THEN 5
                            ELSE 6
                        END,
                        COALESCE(v.updated_at, v.created_at) DESC,
                        v.code ASC
                        LIMIT 1
                    ) current_version ON TRUE
                    LEFT JOIN (
                        SELECT product_id, COUNT(*) AS module_count
                        FROM product_modules
                        WHERE status = 'active'
                        GROUP BY product_id
                    ) module_counts ON module_counts.product_id = p.id
                    {where_clause}
                    ORDER BY {order_column} {order_direction}, p.id ASC
                    {paging_clause}
                    """,
                    tuple(params),
                )
                return [_product_summary(row) for row in cursor.fetchall()]

    def _product_version_summary_where(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
    ) -> tuple[str, list[Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if active_only:
            where_clauses.append("v.status = 'active'")
        if code is not None:
            where_clauses.append("v.code ILIKE %s")
            params.append(f"%{code}%")
        if name is not None:
            where_clauses.append("v.name ILIKE %s")
            params.append(f"%{name}%")
        if product is not None:
            product_pattern = f"%{product}%"
            where_clauses.append("(p.code ILIKE %s OR p.name ILIKE %s OR v.product_id ILIKE %s)")
            params.extend([product_pattern, product_pattern, product_pattern])
        if product_id is not None:
            where_clauses.append("v.product_id = %s")
            params.append(product_id)
        if product_scope_ids is not None:
            if product_scope_ids:
                where_clauses.append("v.product_id = ANY(%s)")
                params.append(product_scope_ids)
            else:
                where_clauses.append("FALSE")
        if status is not None:
            where_clauses.append("v.status = %s")
            params.append(status)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        return where_clause, params

    def count_product_version_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
    ) -> int:
        where_clause, params = self._product_version_summary_where(
            active_only=active_only,
            code=code,
            name=name,
            product=product,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM product_versions v
                    JOIN products p ON p.id = v.product_id
                    {where_clause}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
        return int(row[0] if row else 0)

    def list_product_version_summaries_page(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "code",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]:
        where_clause, params = self._product_version_summary_where(
            active_only=active_only,
            code=code,
            name=name,
            product=product,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            status=status,
        )
        sort_columns = {
            "code": "v.code",
            "created_at": "v.created_at",
            "name": "v.name",
            "product_code": "p.code",
            "product_name": "p.name",
            "release_date": "v.release_date",
            "start_date": "v.start_date",
            "status": "v.status",
            "updated_at": "COALESCE(v.updated_at, v.created_at)",
        }
        order_column = sort_columns.get(sort_by, sort_columns["code"])
        order_direction = "ASC" if sort_order == "asc" else "DESC"
        paging_clause = ""
        if limit is not None:
            paging_clause += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            paging_clause += " OFFSET %s"
            params.append(offset)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT v.id, v.product_id, v.code, v.name, v.description, v.status,
                           v.start_date, v.release_date, v.scope_version, p.code, p.name,
                           v.created_at, v.updated_at
                    FROM product_versions v
                    JOIN products p ON p.id = v.product_id
                    {where_clause}
                    ORDER BY {order_column} {order_direction}, v.id ASC
                    {paging_clause}
                    """,
                    tuple(params),
                )
                return [
                    {
                        "code": row[2],
                        "created_at": row[10].isoformat() if row[10] else None,
                        "description": row[4],
                        "id": row[0],
                        "name": row[3],
                        "product_code": row[9],
                        "product_id": row[1],
                        "product_name": row[10],
                        "release_date": row[7].isoformat() if row[7] else None,
                        "scope_version": row[8],
                        "start_date": row[6].isoformat() if row[6] else None,
                        "status": row[5],
                        "updated_at": row[12].isoformat() if row[12] else None,
                    }
                    for row in cursor.fetchall()
                ]


def _product_summary(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "code": row[1],
        "current_version_code": row[7],
        "current_version_name": row[8],
        "description": row[3],
        "display_order": row[6],
        "id": row[0],
        "module_count": row[9],
        "name": row[2],
        "owner_team": row[4],
        "status": row[5],
    }
