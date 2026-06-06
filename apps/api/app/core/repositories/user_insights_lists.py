from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class UserInsightListRepository:
    def __init__(self, connect: Callable[..., AbstractContextManager[Any]]) -> None:
        self._connect = connect

    def list_user_insight_items(
        self,
        *,
        category: str | None = None,
        summary: str | None = None,
        status: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]:
        sort_expressions = {
            "category": "LOWER(category)",
            "id": "LOWER(id)",
            "owner": "LOWER(owner)",
            "status": "LOWER(status)",
            "summary": "LOWER(summary)",
            "updated_at": "updated_at",
        }
        sort_expression = sort_expressions[sort_by]
        sort_direction = "ASC" if sort_order == "asc" else "DESC"
        base_query = """
            WITH insight_rows AS (
                SELECT '使用趋势'::text AS category,
                       id,
                       created_by AS owner,
                       '-'::text AS status,
                       COALESCE(feature_code, '-') AS summary,
                       COALESCE(updated_at, created_at, window_start) AS updated_at,
                       product_id,
                       '-'::text AS version_id,
                       COALESCE(module_code, '-') AS module_code,
                       COALESCE(feature_code, '-') AS feature_code,
                       '-'::text AS feedback_type,
                       '-'::text AS confidence_level,
                       '-'::text AS planning_cycle,
                       '-'::text AS priority,
                       '-'::text AS converted_requirement_id
                FROM user_usage_metrics
                UNION ALL
                SELECT '用户反馈'::text AS category,
                       id,
                       created_by AS owner,
                       status,
                       content AS summary,
                       COALESCE(updated_at, created_at) AS updated_at,
                       product_id,
                       '-'::text AS version_id,
                       COALESCE(module_code, '-') AS module_code,
                       COALESCE(feature_code, '-') AS feature_code,
                       feedback_type,
                       '-'::text AS confidence_level,
                       '-'::text AS planning_cycle,
                       '-'::text AS priority,
                       '-'::text AS converted_requirement_id
                FROM user_feedback
                UNION ALL
                SELECT '迭代建议'::text AS category,
                       id,
                       created_by AS owner,
                       status,
                       title AS summary,
                       COALESCE(updated_at, created_at) AS updated_at,
                       product_id,
                       COALESCE(version_id, '-') AS version_id,
                       CASE
                           WHEN jsonb_typeof(module_codes) = 'array'
                                AND jsonb_array_length(module_codes) > 0
                           THEN module_codes ->> 0
                           ELSE '-'
                       END AS module_code,
                       '-'::text AS feature_code,
                       '-'::text AS feedback_type,
                       confidence_level,
                       planning_cycle,
                       priority,
                       COALESCE(converted_requirement_id, '-') AS converted_requirement_id
                FROM iteration_plan_suggestions
            )
        """
        where_clauses: list[str] = []
        params: list[Any] = []
        if category is not None:
            where_clauses.append("category = %s")
            params.append(category)
        if status is not None:
            where_clauses.append("status = %s")
            params.append(status)
        if summary is not None and summary.strip():
            where_clauses.append(
                """
                CONCAT_WS(
                    ' ',
                    summary,
                    id,
                    product_id,
                    version_id,
                    module_code,
                    feature_code
                ) ILIKE %s
                """
            )
            params.append(f"%{summary.strip()}%")
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        use_pagination = page is not None or page_size is not None
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        limit_clause = ""
        query_params = list(params)
        if use_pagination:
            limit_clause = "LIMIT %s OFFSET %s"
            query_params.extend([resolved_page_size, (resolved_page - 1) * resolved_page_size])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    {base_query}
                    SELECT COUNT(*)
                    FROM insight_rows
                    {where_clause}
                    """,
                    tuple(params),
                )
                total = int(cursor.fetchone()[0])
                cursor.execute(
                    f"""
                    {base_query}
                    SELECT category, id, owner, status, summary, updated_at,
                           product_id, version_id, module_code, feature_code,
                           feedback_type, confidence_level, planning_cycle, priority,
                           converted_requirement_id
                    FROM insight_rows
                    {where_clause}
                    ORDER BY {sort_expression} {sort_direction}, id {sort_direction}
                    {limit_clause}
                    """,
                    tuple(query_params),
                )
                items = [
                    {
                        "category": row[0],
                        "confidence_level": row[11],
                        "converted_requirement_id": row[14],
                        "feature_code": row[9],
                        "feedback_type": row[10],
                        "id": row[1],
                        "module_code": row[8],
                        "owner": row[2],
                        "planning_cycle": row[12],
                        "priority": row[13],
                        "product_id": row[6],
                        "status": row[3],
                        "summary": row[4],
                        "updated_at": row[5].isoformat() if row[5] else "",
                        "version_id": row[7],
                    }
                    for row in cursor.fetchall()
                ]
        payload: dict[str, Any] = {"items": items, "total": total}
        if use_pagination:
            payload["page"] = resolved_page
            payload["page_size"] = resolved_page_size
        return payload
