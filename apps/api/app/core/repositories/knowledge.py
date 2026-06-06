from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.core.repositories.knowledge_writes import KnowledgeWriteRepository


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
                knowledge_documents = self._load_knowledge_documents(cursor)
                knowledge_chunks = self._load_knowledge_chunks(cursor)
                knowledge_deposits = self._load_knowledge_deposits(cursor)
        return {
            "knowledge_chunks": knowledge_chunks,
            "knowledge_deposits": knowledge_deposits,
            "knowledge_documents": knowledge_documents,
        }

    def save_knowledge(self, payload: dict[str, Any]) -> None:
        self._write_repository.save_knowledge(payload)

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
        keyword: str | None = None,
        doc_type: str | None = None,
        index_status: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses = [
            """
            EXISTS (
              SELECT 1
              FROM jsonb_array_elements_text(d.permission_roles) AS role(value)
              WHERE role.value = ANY(%s::text[])
            )
            """
        ]
        params: list[Any] = [user_roles]
        if keyword is not None:
            where_clauses.append("lower(d.title || ' ' || d.content) LIKE %s")
            params.append(f"%{keyword.lower()}%")
        if doc_type is not None:
            where_clauses.append("d.doc_type = %s")
            params.append(doc_type)
        if index_status is not None:
            where_clauses.append("d.index_status = %s")
            params.append(index_status)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT d.id, d.brain_app_id, d.product_id, d.version_id, d.title,
                           d.content, d.source_type, d.doc_type, d.permission_scope,
                           d.permission_roles, d.index_status, d.index_error,
                           d.vector_index_error, d.tags, d.created_by, d.created_at,
                           d.updated_at, COUNT(c.id)
                    FROM knowledge_documents d
                    LEFT JOIN knowledge_chunks c ON c.document_id = d.id
                    WHERE {' AND '.join(where_clauses)}
                    GROUP BY d.id, d.brain_app_id, d.product_id, d.version_id, d.title,
                             d.content, d.source_type, d.doc_type, d.permission_scope,
                             d.permission_roles, d.index_status, d.index_error,
                             d.vector_index_error, d.tags, d.created_by, d.created_at,
                             d.updated_at
                    ORDER BY d.id
                    """,
                    tuple(params),
                )
                documents = []
                for row in cursor.fetchall():
                    document = {
                        "brain_app_id": row[1],
                        "chunk_count": int(row[17] or 0),
                        "content": row[5],
                        "created_at": row[15].isoformat() if row[15] else None,
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
                        "updated_at": row[16].isoformat() if row[16] else None,
                        "vector_index_error": row[12],
                        "version_id": row[3],
                    }
                    for optional_key in (
                        "brain_app_id",
                        "created_at",
                        "product_id",
                        "updated_at",
                        "version_id",
                    ):
                        if document[optional_key] is None:
                            document.pop(optional_key)
                    if not document["permission_scope"]:
                        document.pop("permission_scope")
                    documents.append(document)
                return documents

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

    def has_readable_vector_chunks(self, *, user_roles: list[str]) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1
                    FROM knowledge_chunks c
                    JOIN knowledge_documents d ON d.id = c.document_id
                    WHERE d.index_status IN ('indexed', 'text_indexed', 'vector_indexed')
                      AND c.embedding IS NOT NULL
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
                    LIMIT 1
                    """,
                    (user_roles, user_roles),
                )
                return cursor.fetchone() is not None

    def search_knowledge_chunks(
        self,
        *,
        user_roles: list[str],
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses = [
            "d.index_status IN ('indexed', 'text_indexed', 'vector_indexed')",
            """
            EXISTS (
              SELECT 1
              FROM jsonb_array_elements_text(d.permission_roles) AS role(value)
              WHERE role.value = ANY(%s::text[])
            )
            """,
            """
            (
              jsonb_array_length(COALESCE(c.permission_scope->'roles', '[]'::jsonb)) = 0
              OR EXISTS (
                SELECT 1
                FROM jsonb_array_elements_text(
                  COALESCE(c.permission_scope->'roles', '[]'::jsonb)
                ) AS role(value)
                WHERE role.value = ANY(%s::text[])
              )
            )
            """,
        ]
        params: list[Any] = [user_roles, user_roles]
        if query is not None:
            where_clauses.append("lower(d.title || ' ' || c.content) LIKE %s")
            params.append(f"%{query.lower()}%")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT d.id, d.title, d.doc_type, d.permission_roles, d.index_status,
                           c.id, c.chunk_index, c.content, c.embedding::text, c.metadata,
                           c.permission_scope
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
            "created_at": row[15].isoformat() if row[15] else None,
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
            "updated_at": row[16].isoformat() if row[16] else None,
            "vector_index_error": row[12],
            "version_id": row[3],
        }
        for optional_key in (
            "brain_app_id",
            "created_at",
            "index_error",
            "product_id",
            "updated_at",
            "vector_index_error",
            "version_id",
        ):
            if document[optional_key] is None:
                document.pop(optional_key)
        if not document["permission_scope"]:
            document.pop("permission_scope")
        return document

    @staticmethod
    def _knowledge_chunk_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        permission_scope = dict(row[6] or {})
        chunk = {
            "chunk_index": row[2],
            "content": row[3],
            "created_at": row[7].isoformat() if row[7] else None,
            "document_id": row[1],
            "embedding": _parse_vector_text(row[4]),
            "id": row[0],
            "metadata": dict(row[5] or {}),
            "permission_roles": list(permission_scope.get("roles") or []),
            "permission_scope": permission_scope,
            "updated_at": row[8].isoformat() if row[8] else None,
        }
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

    def _load_knowledge_documents(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, brain_app_id, product_id, version_id, title, content, source_type,
                   doc_type, permission_scope, permission_roles, index_status, index_error,
                   vector_index_error, tags, created_by, created_at, updated_at
            FROM knowledge_documents
            ORDER BY id
            """
        )
        return {row[0]: self._knowledge_document_from_row(row) for row in cursor.fetchall()}

    def _load_knowledge_chunks(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, document_id, chunk_index, content, embedding::text, metadata,
                   permission_scope, created_at, updated_at
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
