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
        spaces = payload.get("knowledge_spaces", {})
        space_members = payload.get("knowledge_space_members", {})
        folders = payload.get("knowledge_folders", {})
        assets = payload.get("knowledge_assets", {})
        import_jobs = payload.get("knowledge_import_jobs", {})
        chunk_sets = payload.get("knowledge_chunk_sets", {})
        documents = payload.get("knowledge_documents", {})
        chunks = self.clean_knowledge_chunk_references(
            documents,
            payload.get("knowledge_chunks", {}),
        )
        deposits = self.clean_knowledge_deposit_references(
            documents,
            payload.get("knowledge_deposits", {}),
        )
        audit_events = payload.get("audit_events") or []
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.clear_dangling_knowledge_deposit_documents(cursor, documents)
                self.clear_dangling_knowledge_chunk_documents(cursor, documents)
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "knowledge_deposits", deposits)
                    self._delete_missing(cursor, "knowledge_chunks", chunks)
                    self._delete_missing(cursor, "knowledge_import_jobs", import_jobs)
                    self._delete_missing(cursor, "knowledge_chunk_sets", chunk_sets)
                    self._delete_missing(cursor, "knowledge_assets", assets)
                    self._delete_missing(cursor, "knowledge_documents", documents)
                    self._delete_missing(cursor, "knowledge_folders", folders)
                    self.delete_missing_knowledge_space_members(cursor, space_members)
                    self._delete_missing(cursor, "knowledge_spaces", spaces)
                self.upsert_knowledge_spaces(cursor, spaces)
                self.upsert_knowledge_space_members(cursor, space_members)
                self.upsert_knowledge_folders(cursor, folders)
                self.upsert_knowledge_documents(cursor, documents)
                self.upsert_knowledge_assets(cursor, assets)
                self.upsert_knowledge_chunk_sets(cursor, chunk_sets)
                self.upsert_knowledge_chunks(cursor, chunks)
                self.upsert_knowledge_import_jobs(cursor, import_jobs)
                self.upsert_knowledge_deposits(cursor, deposits)
                if audit_events and self._upsert_audit_events is not None:
                    self._upsert_audit_events(
                        cursor,
                        list(audit_events.values())
                        if isinstance(audit_events, dict)
                        else list(audit_events),
                    )

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
                  vector_index_error, tags, created_by, created_at, updated_at,
                  knowledge_space_id, folder_id, source_asset_id, parsed_asset_id,
                  active_chunk_set_id, parser_engine, chunk_strategy, document_version
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s,
                  %s, %s::jsonb, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now()), %s, %s, %s, %s, %s, %s, %s, %s
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
                  knowledge_space_id = EXCLUDED.knowledge_space_id,
                  folder_id = EXCLUDED.folder_id,
                  source_asset_id = EXCLUDED.source_asset_id,
                  parsed_asset_id = EXCLUDED.parsed_asset_id,
                  active_chunk_set_id = EXCLUDED.active_chunk_set_id,
                  parser_engine = EXCLUDED.parser_engine,
                  chunk_strategy = EXCLUDED.chunk_strategy,
                  document_version = EXCLUDED.document_version,
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
                    document.get("knowledge_space_id"),
                    document.get("folder_id"),
                    document.get("source_asset_id"),
                    document.get("parsed_asset_id"),
                    document.get("active_chunk_set_id"),
                    document.get("parser_engine"),
                    document.get("chunk_strategy"),
                    document.get("document_version", 1),
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
                  permission_scope, created_at, updated_at, chunk_set_id,
                  parent_chunk_id, content_hash
                )
                VALUES (
                  %s, %s, %s, %s, %s::vector, %s::jsonb, %s::jsonb,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()),
                  %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                  document_id = EXCLUDED.document_id,
                  chunk_index = EXCLUDED.chunk_index,
                  content = EXCLUDED.content,
                  embedding = EXCLUDED.embedding,
                  metadata = EXCLUDED.metadata,
                  permission_scope = EXCLUDED.permission_scope,
                  chunk_set_id = EXCLUDED.chunk_set_id,
                  parent_chunk_id = EXCLUDED.parent_chunk_id,
                  content_hash = EXCLUDED.content_hash,
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
                    chunk.get("chunk_set_id"),
                    chunk.get("parent_chunk_id"),
                    chunk.get("content_hash"),
                ),
            )

    def delete_missing_knowledge_space_members(
        self,
        cursor,
        members: dict[str, dict[str, Any]],
    ) -> None:
        if not members:
            cursor.execute("DELETE FROM knowledge_space_members")
            return
        keys = [
            (
                member["knowledge_space_id"],
                member["user_id"],
                member.get("space_role", "reader"),
            )
            for member in members.values()
        ]
        placeholders = ", ".join(["(%s, %s, %s)"] * len(keys))
        params = [value for key in keys for value in key]
        cursor.execute(
            f"""
            DELETE FROM knowledge_space_members
            WHERE (knowledge_space_id, user_id, space_role) NOT IN ({placeholders})
            """,  # noqa: S608
            tuple(params),
        )

    def upsert_knowledge_spaces(
        self,
        cursor,
        spaces: dict[str, dict[str, Any]],
    ) -> None:
        for space in spaces.values():
            created_at = space.get("created_at")
            updated_at = space.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO knowledge_spaces (
                  id, code, name, description, owner_user_id, department_id, status,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  code = EXCLUDED.code,
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  owner_user_id = EXCLUDED.owner_user_id,
                  department_id = EXCLUDED.department_id,
                  status = EXCLUDED.status,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    space["id"],
                    space["code"],
                    space["name"],
                    space.get("description", ""),
                    space.get("owner_user_id"),
                    space.get("department_id"),
                    space.get("status", "active"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_knowledge_space_members(
        self,
        cursor,
        members: dict[str, dict[str, Any]],
    ) -> None:
        for member in members.values():
            created_at = member.get("created_at")
            updated_at = member.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO knowledge_space_members (
                  knowledge_space_id, user_id, space_role, status, granted_by,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (knowledge_space_id, user_id, space_role) DO UPDATE SET
                  status = EXCLUDED.status,
                  granted_by = EXCLUDED.granted_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    member["knowledge_space_id"],
                    member["user_id"],
                    member.get("space_role", "reader"),
                    member.get("status", "active"),
                    member.get("granted_by"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_knowledge_folders(
        self,
        cursor,
        folders: dict[str, dict[str, Any]],
    ) -> None:
        for folder in folders.values():
            created_at = folder.get("created_at")
            updated_at = folder.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO knowledge_folders (
                  id, knowledge_space_id, parent_folder_id, name, status, sort_order,
                  created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  knowledge_space_id = EXCLUDED.knowledge_space_id,
                  parent_folder_id = EXCLUDED.parent_folder_id,
                  name = EXCLUDED.name,
                  status = EXCLUDED.status,
                  sort_order = EXCLUDED.sort_order,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    folder["id"],
                    folder["knowledge_space_id"],
                    folder.get("parent_folder_id"),
                    folder["name"],
                    folder.get("status", "active"),
                    folder.get("sort_order", 0),
                    folder.get("created_by"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_knowledge_assets(
        self,
        cursor,
        assets: dict[str, dict[str, Any]],
    ) -> None:
        for asset in assets.values():
            created_at = asset.get("created_at")
            updated_at = asset.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO knowledge_assets (
                  id, knowledge_space_id, document_id, asset_type, storage_provider,
                  bucket, object_key, content_hash, filename, mime_type, size_bytes,
                  metadata, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s::jsonb, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (bucket, object_key) DO UPDATE SET
                  knowledge_space_id = EXCLUDED.knowledge_space_id,
                  document_id = EXCLUDED.document_id,
                  asset_type = EXCLUDED.asset_type,
                  storage_provider = EXCLUDED.storage_provider,
                  content_hash = EXCLUDED.content_hash,
                  filename = EXCLUDED.filename,
                  mime_type = EXCLUDED.mime_type,
                  size_bytes = EXCLUDED.size_bytes,
                  metadata = knowledge_assets.metadata || EXCLUDED.metadata,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    asset["id"],
                    asset["knowledge_space_id"],
                    asset.get("document_id"),
                    asset.get("asset_type", "original"),
                    asset.get("storage_provider", "minio"),
                    asset["bucket"],
                    asset["object_key"],
                    asset["content_hash"],
                    asset.get("filename", ""),
                    asset.get("mime_type", "application/octet-stream"),
                    asset.get("size_bytes", 0),
                    json.dumps(asset.get("metadata", {}), ensure_ascii=False),
                    asset["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def upsert_knowledge_chunk_sets(
        self,
        cursor,
        chunk_sets: dict[str, dict[str, Any]],
    ) -> None:
        for chunk_set in chunk_sets.values():
            created_at = chunk_set.get("created_at")
            updated_at = chunk_set.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO knowledge_chunk_sets (
                  id, document_id, source_asset_id, parsed_asset_id, parser_engine,
                  parser_version, chunk_strategy, embedding_model, embedding_dimension,
                  status, created_by, activated_at, created_at, updated_at,
                  index_status, vector_index_error
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s::timestamptz, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now()), %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                  document_id = EXCLUDED.document_id,
                  source_asset_id = EXCLUDED.source_asset_id,
                  parsed_asset_id = EXCLUDED.parsed_asset_id,
                  parser_engine = EXCLUDED.parser_engine,
                  parser_version = EXCLUDED.parser_version,
                  chunk_strategy = EXCLUDED.chunk_strategy,
                  embedding_model = EXCLUDED.embedding_model,
                  embedding_dimension = EXCLUDED.embedding_dimension,
                  status = EXCLUDED.status,
                  created_by = EXCLUDED.created_by,
                  activated_at = EXCLUDED.activated_at,
                  index_status = EXCLUDED.index_status,
                  vector_index_error = EXCLUDED.vector_index_error,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    chunk_set["id"],
                    chunk_set["document_id"],
                    chunk_set.get("source_asset_id"),
                    chunk_set.get("parsed_asset_id"),
                    chunk_set.get("parser_engine", "plain_text"),
                    chunk_set.get("parser_version", "v1"),
                    chunk_set.get("chunk_strategy", "simple_text"),
                    chunk_set.get("embedding_model"),
                    chunk_set.get("embedding_dimension"),
                    chunk_set.get("status", "building"),
                    chunk_set["created_by"],
                    chunk_set.get("activated_at"),
                    created_at,
                    updated_at,
                    chunk_set.get("index_status"),
                    chunk_set.get("vector_index_error"),
                ),
            )

    def upsert_knowledge_import_jobs(
        self,
        cursor,
        import_jobs: dict[str, dict[str, Any]],
    ) -> None:
        for import_job in import_jobs.values():
            created_at = import_job.get("created_at")
            updated_at = import_job.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO knowledge_import_jobs (
                  id, document_id, source_asset_id, parser_engine, chunk_strategy,
                  status, progress, error_code, error_message, created_by, started_at,
                  finished_at, created_at, updated_at, locked_by, locked_until,
                  attempt_count
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s::timestamptz, %s::timestamptz,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()),
                  %s, %s::timestamptz, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                  document_id = EXCLUDED.document_id,
                  source_asset_id = EXCLUDED.source_asset_id,
                  parser_engine = EXCLUDED.parser_engine,
                  chunk_strategy = EXCLUDED.chunk_strategy,
                  status = EXCLUDED.status,
                  progress = EXCLUDED.progress,
                  error_code = EXCLUDED.error_code,
                  error_message = EXCLUDED.error_message,
                  created_by = EXCLUDED.created_by,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  locked_by = EXCLUDED.locked_by,
                  locked_until = EXCLUDED.locked_until,
                  attempt_count = EXCLUDED.attempt_count,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    import_job["id"],
                    import_job["document_id"],
                    import_job.get("source_asset_id"),
                    import_job.get("parser_engine", "plain_text"),
                    import_job.get("chunk_strategy", "simple_text"),
                    import_job.get("status", "uploaded"),
                    import_job.get("progress", 0),
                    import_job.get("error_code"),
                    import_job.get("error_message"),
                    import_job["created_by"],
                    import_job.get("started_at"),
                    import_job.get("finished_at"),
                    created_at,
                    updated_at,
                    import_job.get("locked_by"),
                    import_job.get("locked_until"),
                    import_job.get("attempt_count", 0),
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
