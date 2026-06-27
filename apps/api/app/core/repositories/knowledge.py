from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.core.repositories.knowledge_writes import KnowledgeWriteRepository

READ_SPACE_ROLES = ["admin", "contributor", "maintainer", "reader"]
KNOWLEDGE_DOCUMENT_SELECT = """
d.id, d.brain_app_id, d.product_id, d.version_id, d.title,
d.content, d.source_type, d.doc_type, d.permission_scope,
d.permission_roles, d.index_status, d.index_error,
d.vector_index_error, d.tags, d.created_by, d.created_at,
d.updated_at, d.knowledge_space_id, d.folder_id,
d.source_asset_id, d.parsed_asset_id, d.active_chunk_set_id,
d.parser_engine, d.chunk_strategy, d.document_version,
f.name AS folder_path, COUNT(c.id)
"""
KNOWLEDGE_DOCUMENT_GROUP_BY = """
d.id, d.brain_app_id, d.product_id, d.version_id, d.title,
d.content, d.source_type, d.doc_type, d.permission_scope,
d.permission_roles, d.index_status, d.index_error,
d.vector_index_error, d.tags, d.created_by, d.created_at,
d.updated_at, d.knowledge_space_id, d.folder_id,
d.source_asset_id, d.parsed_asset_id, d.active_chunk_set_id,
d.parser_engine, d.chunk_strategy, d.document_version,
f.name
"""
KNOWLEDGE_DOCUMENT_SORT_COLUMNS = {
    "created_at": "d.created_at",
    "doc_type": "d.doc_type",
    "folder_id": "d.folder_id",
    "id": "d.id",
    "index_status": "d.index_status",
    "knowledge_space_id": "d.knowledge_space_id",
    "permission_roles": "d.permission_roles::text",
    "title": "lower(d.title)",
    "updated_at": "d.updated_at",
}


def _parse_vector_text(value: Any) -> list[float] | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    try:
        return [float(part.strip()) for part in text.split(",") if part.strip()]
    except ValueError:
        return None


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None


class KnowledgeReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
        upsert_model_gateway_logs: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._write_repository = KnowledgeWriteRepository(
            connect,
            delete_missing=delete_missing,
            upsert_audit_events=upsert_audit_events,
            upsert_model_gateway_logs=upsert_model_gateway_logs,
        )

    def load_knowledge(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                knowledge_spaces = self._load_knowledge_spaces(cursor)
                knowledge_space_members = self._load_knowledge_space_members(cursor)
                knowledge_folders = self._load_knowledge_folders(cursor)
                knowledge_assets = self._load_knowledge_assets(cursor)
                knowledge_import_jobs = self._load_knowledge_import_jobs(cursor)
                knowledge_chunk_sets = self._load_knowledge_chunk_sets(cursor)
                knowledge_documents = self._load_knowledge_documents(cursor)
                knowledge_chunks = self._load_knowledge_chunks(cursor)
                knowledge_deposits = self._load_knowledge_deposits(cursor)
        return {
            "knowledge_assets": knowledge_assets,
            "knowledge_chunk_sets": knowledge_chunk_sets,
            "knowledge_chunks": knowledge_chunks,
            "knowledge_deposits": knowledge_deposits,
            "knowledge_documents": knowledge_documents,
            "knowledge_folders": knowledge_folders,
            "knowledge_import_jobs": knowledge_import_jobs,
            "knowledge_space_members": knowledge_space_members,
            "knowledge_spaces": knowledge_spaces,
        }

    def save_knowledge(self, payload: dict[str, Any]) -> None:
        self._write_repository.save_knowledge(payload)

    def claim_knowledge_import_job(
        self,
        *,
        job_id: str,
        worker_id: str,
        lock_ttl_seconds: float,
    ) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE knowledge_import_jobs
                    SET locked_by = %s,
                        locked_until = now() + (%s * interval '1 second'),
                        attempt_count = COALESCE(attempt_count, 0) + 1,
                        updated_at = now()
                    WHERE id = %s
                      AND status = 'queued'
                      AND (
                        locked_until IS NULL
                        OR locked_until < now()
                        OR locked_by = %s
                      )
                    RETURNING id
                    """,
                    (worker_id, lock_ttl_seconds, job_id, worker_id),
                )
                return cursor.fetchone() is not None

    def save_knowledge_document_records(
        self,
        *,
        document: dict[str, Any],
        chunks: list[dict[str, Any]],
        audit_event: dict[str, Any] | None = None,
        model_logs: list[dict[str, Any]] | None = None,
    ) -> None:
        self._write_repository.save_knowledge_document_records(
            document=document,
            chunks=chunks,
            audit_event=audit_event,
            model_logs=model_logs,
        )

    def delete_knowledge_document_records(
        self,
        *,
        document_id: str,
        deposits: list[dict[str, Any]],
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._write_repository.delete_knowledge_document_records(
            document_id=document_id,
            deposits=deposits,
            audit_event=audit_event,
        )

    def save_knowledge_deposit_records(
        self,
        *,
        deposit: dict[str, Any],
        audit_event: dict[str, Any] | None = None,
        document: dict[str, Any] | None = None,
        chunks: list[dict[str, Any]] | None = None,
        model_logs: list[dict[str, Any]] | None = None,
    ) -> None:
        self._write_repository.save_knowledge_deposit_records(
            deposit=deposit,
            audit_event=audit_event,
            document=document,
            chunks=chunks,
            model_logs=model_logs,
        )

    def clean_knowledge_deposit_references(
        self,
        documents: dict[str, dict[str, Any]],
        deposits: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        return self._write_repository.clean_knowledge_deposit_references(documents, deposits)

    def clean_knowledge_chunk_references(
        self,
        documents: dict[str, dict[str, Any]],
        chunks: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        return self._write_repository.clean_knowledge_chunk_references(documents, chunks)

    def clear_dangling_knowledge_chunk_documents(
        self,
        cursor,
        documents: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.clear_dangling_knowledge_chunk_documents(cursor, documents)

    def clear_dangling_knowledge_deposit_documents(
        self,
        cursor,
        documents: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.clear_dangling_knowledge_deposit_documents(cursor, documents)

    def upsert_knowledge_documents(
        self,
        cursor,
        documents: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_knowledge_documents(cursor, documents)

    def upsert_knowledge_chunks(
        self,
        cursor,
        chunks: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_knowledge_chunks(cursor, chunks)

    def upsert_knowledge_deposits(
        self,
        cursor,
        deposits: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_knowledge_deposits(cursor, deposits)

    def list_knowledge_documents(
        self,
        *,
        user_roles: list[str],
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_scope_ids: list[str] | None = None,
        keyword: str | None = None,
        doc_type: str | None = None,
        folder_id: str | None = None,
        index_status: str | None = None,
        knowledge_space_id: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clause, params = self._knowledge_document_where(
            doc_type=doc_type,
            folder_id=folder_id,
            global_knowledge_access=global_knowledge_access,
            index_status=index_status,
            keyword=keyword,
            knowledge_space_id=knowledge_space_id,
            knowledge_space_scope_ids=knowledge_space_scope_ids,
            permission_role=None,
            user_id=user_id,
            user_roles=user_roles,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT {KNOWLEDGE_DOCUMENT_SELECT}
                    FROM knowledge_documents d
                    LEFT JOIN knowledge_folders f ON f.id = d.folder_id
                    LEFT JOIN knowledge_chunks c
                      ON c.document_id = d.id
                     AND (d.active_chunk_set_id IS NULL OR c.chunk_set_id = d.active_chunk_set_id)
                    WHERE {where_clause}
                    GROUP BY {KNOWLEDGE_DOCUMENT_GROUP_BY}
                    ORDER BY d.id
                    """,
                    tuple(params),
                )
                return [self._knowledge_document_summary_from_row(row) for row in cursor.fetchall()]

    def count_knowledge_document_summaries(
        self,
        *,
        user_roles: list[str],
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_scope_ids: list[str] | None = None,
        keyword: str | None = None,
        doc_type: str | None = None,
        folder_id: str | None = None,
        index_status: str | None = None,
        knowledge_space_id: str | None = None,
        permission_role: str | None = None,
    ) -> int:
        where_clause, params = self._knowledge_document_where(
            doc_type=doc_type,
            folder_id=folder_id,
            global_knowledge_access=global_knowledge_access,
            index_status=index_status,
            keyword=keyword,
            knowledge_space_id=knowledge_space_id,
            knowledge_space_scope_ids=knowledge_space_scope_ids,
            permission_role=permission_role,
            user_id=user_id,
            user_roles=user_roles,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT count(*) FROM knowledge_documents d WHERE {where_clause}",
                    tuple(params),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_knowledge_document_summaries_page(
        self,
        *,
        user_roles: list[str],
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_scope_ids: list[str] | None = None,
        keyword: str | None = None,
        doc_type: str | None = None,
        folder_id: str | None = None,
        index_status: str | None = None,
        knowledge_space_id: str | None = None,
        permission_role: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clause, params = self._knowledge_document_where(
            doc_type=doc_type,
            folder_id=folder_id,
            global_knowledge_access=global_knowledge_access,
            index_status=index_status,
            keyword=keyword,
            knowledge_space_id=knowledge_space_id,
            knowledge_space_scope_ids=knowledge_space_scope_ids,
            permission_role=permission_role,
            user_id=user_id,
            user_roles=user_roles,
        )
        sort_column = KNOWLEDGE_DOCUMENT_SORT_COLUMNS.get(sort_by, "d.id")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT {KNOWLEDGE_DOCUMENT_SELECT}
                    FROM knowledge_documents d
                    LEFT JOIN knowledge_folders f ON f.id = d.folder_id
                    LEFT JOIN knowledge_chunks c
                      ON c.document_id = d.id
                     AND (d.active_chunk_set_id IS NULL OR c.chunk_set_id = d.active_chunk_set_id)
                    WHERE {where_clause}
                    GROUP BY {KNOWLEDGE_DOCUMENT_GROUP_BY}
                    ORDER BY {sort_column} {direction} {nulls}, d.id {direction}
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params),
                )
                return [self._knowledge_document_summary_from_row(row) for row in cursor.fetchall()]

    def list_knowledge_deposits(
        self,
        *,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clause = "WHERE status = %s" if status is not None else ""
        params: tuple[Any, ...] = (status,) if status is not None else ()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, ai_task_id, deposit_type, title, content, content_hash, status,
                           knowledge_document_id, rejection_reason, created_at, updated_at
                    FROM knowledge_deposits
                    {where_clause}
                    ORDER BY created_at, id
                    """,
                    params,
                )
                return [self.knowledge_deposit_from_row(row) for row in cursor.fetchall()]

    def get_knowledge_deposit(self, deposit_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, ai_task_id, deposit_type, title, content, content_hash, status,
                           knowledge_document_id, rejection_reason, created_at, updated_at
                    FROM knowledge_deposits
                    WHERE id = %s
                    """,
                    (deposit_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return self.knowledge_deposit_from_row(row)

    def has_readable_vector_chunks(
        self,
        *,
        user_roles: list[str],
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_id: str | None = None,
        knowledge_space_scope_ids: list[str] | None = None,
    ) -> bool:
        where_clauses = [
            "d.index_status IN ('indexed', 'text_indexed', 'vector_indexed')",
            "c.embedding IS NOT NULL",
            "(d.active_chunk_set_id IS NULL OR c.chunk_set_id = d.active_chunk_set_id)",
            """
            (
              %s IS TRUE
              OR (
                d.knowledge_space_id IS NULL
                AND EXISTS (
                  SELECT 1
                  FROM jsonb_array_elements_text(d.permission_roles) AS role(value)
                  WHERE role.value = ANY(%s::text[])
                )
                AND (
                  jsonb_array_length(COALESCE(c.permission_scope->'roles', '[]'::jsonb)) = 0
                  OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements_text(
                      COALESCE(c.permission_scope->'roles', '[]'::jsonb)
                    ) AS role(value)
                    WHERE role.value = ANY(%s::text[])
                  )
                )
              )
              OR (
                d.knowledge_space_id IS NOT NULL
                AND (
                  d.knowledge_space_id = ANY(%s::text[])
                  OR EXISTS (
                    SELECT 1
                    FROM knowledge_spaces ks
                    WHERE ks.id = d.knowledge_space_id
                      AND ks.status = 'active'
                      AND ks.owner_user_id = %s
                  )
                  OR EXISTS (
                    SELECT 1
                    FROM knowledge_space_members ksm
                    WHERE ksm.knowledge_space_id = d.knowledge_space_id
                      AND ksm.user_id = %s
                      AND ksm.status = 'active'
                      AND ksm.space_role = ANY(%s::text[])
                  )
                )
              )
            )
            """,
        ]
        params: list[Any] = [
            global_knowledge_access,
            user_roles,
            user_roles,
            knowledge_space_scope_ids or [],
            user_id,
            user_id,
            READ_SPACE_ROLES,
        ]
        if knowledge_space_id is not None:
            where_clauses.append("d.knowledge_space_id = %s")
            params.append(knowledge_space_id)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT 1
                    FROM knowledge_chunks c
                    JOIN knowledge_documents d ON d.id = c.document_id
                    WHERE {' AND '.join(where_clauses)}
                    LIMIT 1
                    """,
                    tuple(params),
                )
                return cursor.fetchone() is not None

    def search_knowledge_chunks(
        self,
        *,
        user_roles: list[str],
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_id: str | None = None,
        knowledge_space_scope_ids: list[str] | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses = [
            "d.index_status IN ('indexed', 'text_indexed', 'vector_indexed')",
            "(d.active_chunk_set_id IS NULL OR c.chunk_set_id = d.active_chunk_set_id)",
            """
            (
              %s IS TRUE
              OR (
                d.knowledge_space_id IS NULL
                AND EXISTS (
                  SELECT 1
                  FROM jsonb_array_elements_text(d.permission_roles) AS role(value)
                  WHERE role.value = ANY(%s::text[])
                )
                AND (
                  jsonb_array_length(COALESCE(c.permission_scope->'roles', '[]'::jsonb)) = 0
                  OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements_text(
                      COALESCE(c.permission_scope->'roles', '[]'::jsonb)
                    ) AS role(value)
                    WHERE role.value = ANY(%s::text[])
                  )
                )
              )
              OR (
                d.knowledge_space_id IS NOT NULL
                AND (
                  d.knowledge_space_id = ANY(%s::text[])
                  OR EXISTS (
                    SELECT 1
                    FROM knowledge_spaces ks
                    WHERE ks.id = d.knowledge_space_id
                      AND ks.status = 'active'
                      AND ks.owner_user_id = %s
                  )
                  OR EXISTS (
                    SELECT 1
                    FROM knowledge_space_members ksm
                    WHERE ksm.knowledge_space_id = d.knowledge_space_id
                      AND ksm.user_id = %s
                      AND ksm.status = 'active'
                      AND ksm.space_role = ANY(%s::text[])
                  )
                )
              )
            )
            """,
        ]
        params: list[Any] = [
            global_knowledge_access,
            user_roles,
            user_roles,
            knowledge_space_scope_ids or [],
            user_id,
            user_id,
            READ_SPACE_ROLES,
        ]
        if query is not None:
            where_clauses.append("lower(d.title || ' ' || c.content) LIKE %s")
            params.append(f"%{query.lower()}%")
        if knowledge_space_id is not None:
            where_clauses.append("d.knowledge_space_id = %s")
            params.append(knowledge_space_id)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT d.id, d.title, d.doc_type, d.permission_roles, d.index_status,
                           c.id, c.chunk_index, c.content, c.embedding::text, c.metadata,
                           c.permission_scope, d.knowledge_space_id, d.folder_id,
                           d.source_asset_id, d.active_chunk_set_id, c.chunk_set_id,
                           c.parent_chunk_id, c.content_hash
                    FROM knowledge_chunks c
                    JOIN knowledge_documents d ON d.id = c.document_id
                    WHERE {' AND '.join(where_clauses)}
                    ORDER BY d.id, c.chunk_index, c.id
                    """,
                    tuple(params),
                )
                candidates = []
                for row in cursor.fetchall():
                    permission_scope = dict(row[10] or {})
                    chunk = {
                        "chunk_index": row[6],
                        "content": row[7],
                        "document_id": row[0],
                        "embedding": _parse_vector_text(row[8]),
                        "id": row[5],
                        "metadata": dict(row[9] or {}),
                        "permission_roles": list(permission_scope.get("roles") or []),
                        "permission_scope": permission_scope,
                    }
                    for optional_key, value in (
                        ("chunk_set_id", row[15]),
                        ("parent_chunk_id", row[16]),
                        ("content_hash", row[17]),
                    ):
                        if value is not None:
                            chunk[optional_key] = value
                    if chunk["embedding"] is None:
                        chunk.pop("embedding")
                    if not chunk["permission_roles"]:
                        chunk.pop("permission_roles")
                    if not chunk["permission_scope"]:
                        chunk.pop("permission_scope")
                    candidates.append(
                        {
                            "chunk": chunk,
                            "document": {
                                "doc_type": row[2],
                                "id": row[0],
                                "index_status": row[4],
                                "permission_roles": list(row[3] or []),
                                "knowledge_space_id": row[11],
                                "folder_id": row[12],
                                "source_asset_id": row[13],
                                "active_chunk_set_id": row[14],
                                "title": row[1],
                            },
                        }
                    )
                return candidates

    @staticmethod
    def knowledge_deposit_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        deposit = {
            "ai_task_id": row[1],
            "content": row[4],
            "content_hash": row[5],
            "created_at": row[9].isoformat() if row[9] else None,
            "deposit_type": row[2],
            "id": row[0],
            "knowledge_document_id": row[7],
            "rejection_reason": row[8],
            "status": row[6],
            "title": row[3],
            "updated_at": row[10].isoformat() if row[10] else None,
        }
        for optional_key in (
            "created_at",
            "knowledge_document_id",
            "rejection_reason",
            "updated_at",
        ):
            if deposit[optional_key] is None:
                deposit.pop(optional_key)
        return deposit

    @staticmethod
    def _knowledge_document_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        document = {
            "brain_app_id": row[1],
            "content": row[5],
            "created_at": _iso(row[15]),
            "created_by": row[14],
            "doc_type": row[7],
            "id": row[0],
            "index_error": row[11],
            "index_status": row[10],
            "permission_roles": list(row[9] or []),
            "permission_scope": dict(row[8] or {}),
            "product_id": row[2],
            "source_type": row[6],
            "tags": list(row[13] or []),
            "title": row[4],
            "updated_at": _iso(row[16]),
            "vector_index_error": row[12],
            "version_id": row[3],
        }
        optional_row_fields = (
            ("knowledge_space_id", 17),
            ("folder_id", 18),
            ("source_asset_id", 19),
            ("parsed_asset_id", 20),
            ("active_chunk_set_id", 21),
            ("parser_engine", 22),
            ("chunk_strategy", 23),
            ("document_version", 24),
        )
        for key, index in optional_row_fields:
            if len(row) > index and row[index] is not None:
                document[key] = row[index]
        for optional_key in (
            "active_chunk_set_id",
            "brain_app_id",
            "chunk_strategy",
            "created_at",
            "folder_id",
            "index_error",
            "knowledge_space_id",
            "parsed_asset_id",
            "parser_engine",
            "product_id",
            "source_asset_id",
            "updated_at",
            "vector_index_error",
            "version_id",
        ):
            if optional_key in document and document[optional_key] is None:
                document.pop(optional_key)
        if not document["permission_scope"]:
            document.pop("permission_scope")
        return document

    def _knowledge_document_summary_from_row(self, row: tuple[Any, ...]) -> dict[str, Any]:
        document = self._knowledge_document_from_row(row[:25])
        if len(row) > 26:
            document["chunk_count"] = int(row[26] or 0)
        if len(row) > 25 and row[25]:
            document["folder_path"] = row[25]
        return document

    def _knowledge_document_where(
        self,
        *,
        user_roles: list[str],
        user_id: str | None,
        global_knowledge_access: bool,
        knowledge_space_scope_ids: list[str] | None,
        keyword: str | None,
        doc_type: str | None,
        folder_id: str | None,
        index_status: str | None,
        knowledge_space_id: str | None,
        permission_role: str | None,
    ) -> tuple[str, list[Any]]:
        where_clauses = [
            """
            (
              %s IS TRUE
              OR (
                d.knowledge_space_id IS NULL
                AND EXISTS (
                  SELECT 1
                  FROM jsonb_array_elements_text(d.permission_roles) AS role(value)
                  WHERE role.value = ANY(%s::text[])
                )
              )
              OR (
                d.knowledge_space_id IS NOT NULL
                AND (
                  d.knowledge_space_id = ANY(%s::text[])
                  OR EXISTS (
                    SELECT 1
                    FROM knowledge_spaces ks
                    WHERE ks.id = d.knowledge_space_id
                      AND ks.status = 'active'
                      AND ks.owner_user_id = %s
                  )
                  OR EXISTS (
                    SELECT 1
                    FROM knowledge_space_members ksm
                    WHERE ksm.knowledge_space_id = d.knowledge_space_id
                      AND ksm.user_id = %s
                      AND ksm.status = 'active'
                      AND ksm.space_role = ANY(%s::text[])
                  )
                )
              )
            )
            """
        ]
        params: list[Any] = [
            global_knowledge_access,
            user_roles,
            knowledge_space_scope_ids or [],
            user_id,
            user_id,
            READ_SPACE_ROLES,
        ]
        if keyword is not None:
            where_clauses.append("lower(d.title || ' ' || d.content) LIKE %s")
            params.append(f"%{keyword.lower()}%")
        if doc_type is not None:
            where_clauses.append("d.doc_type = %s")
            params.append(doc_type)
        if folder_id is not None:
            where_clauses.append("d.folder_id = %s")
            params.append(folder_id)
        if index_status is not None:
            where_clauses.append("d.index_status = %s")
            params.append(index_status)
        if knowledge_space_id is not None:
            where_clauses.append("d.knowledge_space_id = %s")
            params.append(knowledge_space_id)
        if permission_role is not None:
            where_clauses.append(
                """
                EXISTS (
                  SELECT 1
                  FROM jsonb_array_elements_text(d.permission_roles) AS filter_role(value)
                  WHERE filter_role.value = %s
                )
                """
            )
            params.append(permission_role)
        return " AND ".join(where_clauses), params

    @staticmethod
    def _knowledge_chunk_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        permission_scope = dict(row[6] or {})
        chunk = {
            "chunk_index": row[2],
            "content": row[3],
            "created_at": _iso(row[7]),
            "document_id": row[1],
            "embedding": _parse_vector_text(row[4]),
            "id": row[0],
            "metadata": dict(row[5] or {}),
            "permission_roles": list(permission_scope.get("roles") or []),
            "permission_scope": permission_scope,
            "updated_at": _iso(row[8]),
        }
        optional_row_fields = (
            ("chunk_set_id", 9),
            ("parent_chunk_id", 10),
            ("content_hash", 11),
        )
        for key, index in optional_row_fields:
            if len(row) > index and row[index] is not None:
                chunk[key] = row[index]
        if chunk["embedding"] is None:
            chunk.pop("embedding")
        if not chunk["permission_roles"]:
            chunk.pop("permission_roles")
        if not chunk["permission_scope"]:
            chunk.pop("permission_scope")
        if chunk["created_at"] is None:
            chunk.pop("created_at")
        if chunk["updated_at"] is None:
            chunk.pop("updated_at")
        return chunk

    @staticmethod
    def _knowledge_deposit_restore_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        deposit = {
            "ai_task_id": row[1],
            "content": row[4],
            "content_hash": row[5],
            "created_at": _iso(row[9]),
            "deposit_type": row[2],
            "id": row[0],
            "knowledge_document_id": row[7],
            "rejection_reason": row[8],
            "status": row[6],
            "title": row[3],
            "updated_at": _iso(row[10]),
        }
        for optional_key in (
            "content_hash",
            "created_at",
            "deposit_type",
            "knowledge_document_id",
            "rejection_reason",
            "updated_at",
        ):
            if deposit[optional_key] is None:
                deposit.pop(optional_key)
        return deposit

    @staticmethod
    def _knowledge_space_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        space = {
            "id": row[0],
            "code": row[1],
            "name": row[2],
            "description": row[3],
            "owner_user_id": row[4],
            "department_id": row[5],
            "status": row[6],
            "created_at": _iso(row[7]),
            "updated_at": _iso(row[8]),
        }
        for optional_key in ("department_id", "owner_user_id", "created_at", "updated_at"):
            if space[optional_key] is None:
                space.pop(optional_key)
        return space

    @staticmethod
    def _knowledge_space_member_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        member = {
            "knowledge_space_id": row[0],
            "user_id": row[1],
            "space_role": row[2],
            "status": row[3],
            "granted_by": row[4],
            "created_at": _iso(row[5]),
            "updated_at": _iso(row[6]),
        }
        for optional_key in ("granted_by", "created_at", "updated_at"):
            if member[optional_key] is None:
                member.pop(optional_key)
        return member

    @staticmethod
    def _knowledge_folder_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        folder = {
            "id": row[0],
            "knowledge_space_id": row[1],
            "parent_folder_id": row[2],
            "name": row[3],
            "status": row[4],
            "sort_order": row[5],
            "created_by": row[6],
            "created_at": _iso(row[7]),
            "updated_at": _iso(row[8]),
        }
        for optional_key in ("parent_folder_id", "created_by", "created_at", "updated_at"):
            if folder[optional_key] is None:
                folder.pop(optional_key)
        return folder

    @staticmethod
    def _knowledge_asset_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        asset = {
            "id": row[0],
            "knowledge_space_id": row[1],
            "document_id": row[2],
            "asset_type": row[3],
            "storage_provider": row[4],
            "bucket": row[5],
            "object_key": row[6],
            "content_hash": row[7],
            "filename": row[8],
            "mime_type": row[9],
            "size_bytes": int(row[10] or 0),
            "metadata": dict(row[11] or {}),
            "created_by": row[12],
            "created_at": _iso(row[13]),
            "updated_at": _iso(row[14]),
        }
        for optional_key in ("document_id", "created_at", "updated_at"):
            if asset[optional_key] is None:
                asset.pop(optional_key)
        return asset

    @staticmethod
    def _knowledge_import_job_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        import_job = {
            "id": row[0],
            "document_id": row[1],
            "source_asset_id": row[2],
            "parser_engine": row[3],
            "chunk_strategy": row[4],
            "status": row[5],
            "progress": row[6],
            "error_code": row[7],
            "error_message": row[8],
            "created_by": row[9],
            "started_at": _iso(row[10]),
            "finished_at": _iso(row[11]),
            "created_at": _iso(row[12]),
            "updated_at": _iso(row[13]),
            "locked_by": row[14],
            "locked_until": _iso(row[15]),
            "attempt_count": row[16] or 0,
        }
        for optional_key in (
            "error_code",
            "error_message",
            "finished_at",
            "locked_by",
            "locked_until",
            "source_asset_id",
            "started_at",
            "created_at",
            "updated_at",
        ):
            if import_job[optional_key] is None:
                import_job.pop(optional_key)
        return import_job

    @staticmethod
    def _knowledge_chunk_set_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        chunk_set = {
            "id": row[0],
            "document_id": row[1],
            "source_asset_id": row[2],
            "parsed_asset_id": row[3],
            "parser_engine": row[4],
            "parser_version": row[5],
            "chunk_strategy": row[6],
            "embedding_model": row[7],
            "embedding_dimension": row[8],
            "status": row[9],
            "created_by": row[10],
            "activated_at": _iso(row[11]),
            "created_at": _iso(row[12]),
            "updated_at": _iso(row[13]),
            "index_status": row[14],
            "vector_index_error": row[15],
        }
        for optional_key in (
            "activated_at",
            "embedding_dimension",
            "embedding_model",
            "index_status",
            "parsed_asset_id",
            "source_asset_id",
            "created_at",
            "updated_at",
            "vector_index_error",
        ):
            if chunk_set[optional_key] is None:
                chunk_set.pop(optional_key)
        return chunk_set

    def _load_knowledge_spaces(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, code, name, description, owner_user_id, department_id, status,
                   created_at, updated_at
            FROM knowledge_spaces
            ORDER BY code, id
            """
        )
        return {row[0]: self._knowledge_space_from_row(row) for row in cursor.fetchall()}

    def _load_knowledge_space_members(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT knowledge_space_id, user_id, space_role, status, granted_by,
                   created_at, updated_at
            FROM knowledge_space_members
            ORDER BY knowledge_space_id, user_id, space_role
            """
        )
        members = {}
        for row in cursor.fetchall():
            member = self._knowledge_space_member_from_row(row)
            key = (
                f"{member['knowledge_space_id']}:{member['user_id']}:"
                f"{member.get('space_role', 'reader')}"
            )
            members[key] = member
        return members

    def _load_knowledge_folders(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, knowledge_space_id, parent_folder_id, name, status, sort_order,
                   created_by, created_at, updated_at
            FROM knowledge_folders
            ORDER BY knowledge_space_id, sort_order, name, id
            """
        )
        return {row[0]: self._knowledge_folder_from_row(row) for row in cursor.fetchall()}

    def _load_knowledge_assets(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, knowledge_space_id, document_id, asset_type, storage_provider,
                   bucket, object_key, content_hash, filename, mime_type, size_bytes,
                   metadata, created_by, created_at, updated_at
            FROM knowledge_assets
            ORDER BY knowledge_space_id, document_id, asset_type, id
            """
        )
        return {row[0]: self._knowledge_asset_from_row(row) for row in cursor.fetchall()}

    def _load_knowledge_import_jobs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, document_id, source_asset_id, parser_engine, chunk_strategy,
                   status, progress, error_code, error_message, created_by, started_at,
                   finished_at, created_at, updated_at, locked_by, locked_until,
                   attempt_count
            FROM knowledge_import_jobs
            ORDER BY created_at, id
            """
        )
        return {
            row[0]: self._knowledge_import_job_from_row(row)
            for row in cursor.fetchall()
        }

    def _load_knowledge_chunk_sets(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, document_id, source_asset_id, parsed_asset_id, parser_engine,
                   parser_version, chunk_strategy, embedding_model, embedding_dimension,
                   status, created_by, activated_at, created_at, updated_at,
                   index_status, vector_index_error
            FROM knowledge_chunk_sets
            ORDER BY document_id, created_at, id
            """
        )
        return {
            row[0]: self._knowledge_chunk_set_from_row(row)
            for row in cursor.fetchall()
        }

    def _load_knowledge_documents(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, brain_app_id, product_id, version_id, title, content, source_type,
                   doc_type, permission_scope, permission_roles, index_status, index_error,
                   vector_index_error, tags, created_by, created_at, updated_at,
                   knowledge_space_id, folder_id, source_asset_id, parsed_asset_id,
                   active_chunk_set_id, parser_engine, chunk_strategy, document_version
            FROM knowledge_documents
            ORDER BY id
            """
        )
        return {row[0]: self._knowledge_document_from_row(row) for row in cursor.fetchall()}

    def _load_knowledge_chunks(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, document_id, chunk_index, content, embedding::text, metadata,
                   permission_scope, created_at, updated_at, chunk_set_id, parent_chunk_id,
                   content_hash
            FROM knowledge_chunks
            ORDER BY document_id, chunk_index, id
            """
        )
        return {row[0]: self._knowledge_chunk_from_row(row) for row in cursor.fetchall()}

    def _load_knowledge_deposits(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, ai_task_id, deposit_type, title, content, content_hash, status,
                   knowledge_document_id, rejection_reason, created_at, updated_at
            FROM knowledge_deposits
            ORDER BY created_at, id
            """
        )
        return {
            row[0]: self._knowledge_deposit_restore_from_row(row)
            for row in cursor.fetchall()
        }
