from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from copy import deepcopy
from typing import Any


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


def _vector_sql_literal(value: Any) -> str | None:
    vector = _parse_vector_text(value)
    if vector is None:
        return None
    return "[" + ",".join(f"{item:.12g}" for item in vector) + "]"


class KnowledgeWriteRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
        upsert_model_gateway_logs: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._delete_missing = delete_missing
        self._upsert_audit_events = upsert_audit_events
        self._upsert_model_gateway_logs = upsert_model_gateway_logs

    def save_knowledge(self, payload: dict[str, Any]) -> None:
        documents = payload.get("knowledge_documents", {})
        chunks = self.clean_knowledge_chunk_references(
            documents,
            payload.get("knowledge_chunks", {}),
        )
        deposits = self.clean_knowledge_deposit_references(
            documents,
            payload.get("knowledge_deposits", {}),
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.clear_dangling_knowledge_deposit_documents(cursor, documents)
                self.clear_dangling_knowledge_chunk_documents(cursor, documents)
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "knowledge_deposits", deposits)
                    self._delete_missing(cursor, "knowledge_chunks", chunks)
                    self._delete_missing(cursor, "knowledge_documents", documents)
                self.upsert_knowledge_documents(cursor, documents)
                self.upsert_knowledge_chunks(cursor, chunks)
                self.upsert_knowledge_deposits(cursor, deposits)

    def save_knowledge_document_records(
        self,
        *,
        document: dict[str, Any],
        chunks: list[dict[str, Any]],
        audit_event: dict[str, Any] | None = None,
        model_logs: list[dict[str, Any]] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM knowledge_chunks WHERE document_id = %s",
                    (document["id"],),
                )
                self.upsert_knowledge_documents(cursor, {document["id"]: document})
                self.upsert_knowledge_chunks(
                    cursor,
                    {chunk["id"]: chunk for chunk in chunks},
                )
                if model_logs and self._upsert_model_gateway_logs is not None:
                    self._upsert_model_gateway_logs(cursor, model_logs)
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def delete_knowledge_document_records(
        self,
        *,
        document_id: str,
        deposits: list[dict[str, Any]],
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM knowledge_chunks WHERE document_id = %s",
                    (document_id,),
                )
                if deposits:
                    self.upsert_knowledge_deposits(
                        cursor,
                        {deposit["id"]: deposit for deposit in deposits},
                    )
                cursor.execute("DELETE FROM knowledge_documents WHERE id = %s", (document_id,))
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def save_knowledge_deposit_records(
        self,
        *,
        deposit: dict[str, Any],
        audit_event: dict[str, Any] | None = None,
        document: dict[str, Any] | None = None,
        chunks: list[dict[str, Any]] | None = None,
        model_logs: list[dict[str, Any]] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if document is not None:
                    cursor.execute(
                        "DELETE FROM knowledge_chunks WHERE document_id = %s",
                        (document["id"],),
                    )
                    self.upsert_knowledge_documents(cursor, {document["id"]: document})
                    self.upsert_knowledge_chunks(
                        cursor,
                        {chunk["id"]: chunk for chunk in chunks or []},
                    )
                self.upsert_knowledge_deposits(cursor, {deposit["id"]: deposit})
                if model_logs and self._upsert_model_gateway_logs is not None:
                    self._upsert_model_gateway_logs(cursor, model_logs)
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def clean_knowledge_deposit_references(
        self,
        documents: dict[str, dict[str, Any]],
        deposits: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        cleaned = deepcopy(deposits)
        for deposit in cleaned.values():
            if deposit.get("knowledge_document_id") not in documents:
                deposit["knowledge_document_id"] = None
        return cleaned

    def clean_knowledge_chunk_references(
        self,
        documents: dict[str, dict[str, Any]],
        chunks: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        return {
            chunk_id: chunk
            for chunk_id, chunk in deepcopy(chunks).items()
            if chunk.get("document_id") in documents
        }

    def clear_dangling_knowledge_chunk_documents(
        self,
        cursor,
        documents: dict[str, dict[str, Any]],
    ) -> None:
        if not documents:
            cursor.execute("DELETE FROM knowledge_chunks")
            return
        placeholders = ", ".join(["%s"] * len(documents))
        cursor.execute(
            f"""
            DELETE FROM knowledge_chunks
            WHERE document_id NOT IN ({placeholders})
            """,  # noqa: S608
            tuple(documents.keys()),
        )

    def clear_dangling_knowledge_deposit_documents(
        self,
        cursor,
        documents: dict[str, dict[str, Any]],
    ) -> None:
        if not documents:
            cursor.execute("UPDATE knowledge_deposits SET knowledge_document_id = NULL")
            return
        placeholders = ", ".join(["%s"] * len(documents))
        cursor.execute(
            f"""
            UPDATE knowledge_deposits
            SET knowledge_document_id = NULL
            WHERE knowledge_document_id IS NOT NULL
              AND knowledge_document_id NOT IN ({placeholders})
            """,  # noqa: S608
            tuple(documents.keys()),
        )

    def upsert_knowledge_documents(
        self,
        cursor,
        documents: dict[str, dict[str, Any]],
    ) -> None:
        for document in documents.values():
            created_at = document.get("created_at")
            updated_at = document.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO knowledge_documents (
                  id, brain_app_id, product_id, version_id, title, content, source_type,
                  doc_type, permission_scope, permission_roles, index_status, index_error,
                  vector_index_error, tags, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s,
                  %s, %s::jsonb, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  brain_app_id = EXCLUDED.brain_app_id,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  title = EXCLUDED.title,
                  content = EXCLUDED.content,
                  source_type = EXCLUDED.source_type,
                  doc_type = EXCLUDED.doc_type,
                  permission_scope = EXCLUDED.permission_scope,
                  permission_roles = EXCLUDED.permission_roles,
                  index_status = EXCLUDED.index_status,
                  index_error = EXCLUDED.index_error,
                  vector_index_error = EXCLUDED.vector_index_error,
                  tags = EXCLUDED.tags,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    document["id"],
                    document.get("brain_app_id", "rd_brain"),
                    document.get("product_id"),
                    document.get("version_id"),
                    document["title"],
                    document["content"],
                    document.get("source_type", "manual"),
                    document.get("doc_type", "manual"),
                    json.dumps(document.get("permission_scope", {}), ensure_ascii=False),
                    json.dumps(document.get("permission_roles", ["admin"]), ensure_ascii=False),
                    document.get("index_status", "pending_index"),
                    document.get("index_error"),
                    document.get("vector_index_error"),
                    json.dumps(document.get("tags", []), ensure_ascii=False),
                    document["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def upsert_knowledge_chunks(
        self,
        cursor,
        chunks: dict[str, dict[str, Any]],
    ) -> None:
        for chunk in chunks.values():
            created_at = chunk.get("created_at")
            updated_at = chunk.get("updated_at") or created_at
            permission_scope = deepcopy(chunk.get("permission_scope", {}))
            if chunk.get("permission_roles"):
                permission_scope["roles"] = list(chunk["permission_roles"])
            cursor.execute(
                """
                INSERT INTO knowledge_chunks (
                  id, document_id, chunk_index, content, embedding, metadata,
                  permission_scope, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s::vector, %s::jsonb, %s::jsonb,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  document_id = EXCLUDED.document_id,
                  chunk_index = EXCLUDED.chunk_index,
                  content = EXCLUDED.content,
                  embedding = EXCLUDED.embedding,
                  metadata = EXCLUDED.metadata,
                  permission_scope = EXCLUDED.permission_scope,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    chunk["id"],
                    chunk["document_id"],
                    chunk["chunk_index"],
                    chunk["content"],
                    _vector_sql_literal(chunk.get("embedding")),
                    json.dumps(chunk.get("metadata", {}), ensure_ascii=False),
                    json.dumps(permission_scope, ensure_ascii=False),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_knowledge_deposits(
        self,
        cursor,
        deposits: dict[str, dict[str, Any]],
    ) -> None:
        for deposit in deposits.values():
            created_at = deposit.get("created_at")
            updated_at = deposit.get("updated_at") or created_at
            content_hash = deposit.get("content_hash") or deposit["id"]
            cursor.execute(
                """
                INSERT INTO knowledge_deposits (
                  id, ai_task_id, deposit_type, title, content, content_hash, status,
                  knowledge_document_id, rejection_reason, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  ai_task_id = EXCLUDED.ai_task_id,
                  deposit_type = EXCLUDED.deposit_type,
                  title = EXCLUDED.title,
                  content = EXCLUDED.content,
                  content_hash = EXCLUDED.content_hash,
                  status = EXCLUDED.status,
                  knowledge_document_id = EXCLUDED.knowledge_document_id,
                  rejection_reason = EXCLUDED.rejection_reason,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    deposit["id"],
                    deposit["ai_task_id"],
                    deposit.get("deposit_type", "task_output"),
                    deposit["title"],
                    deposit["content"],
                    content_hash,
                    deposit.get("status", "pending"),
                    deposit.get("knowledge_document_id"),
                    deposit.get("rejection_reason"),
                    created_at,
                    updated_at,
                ),
            )
