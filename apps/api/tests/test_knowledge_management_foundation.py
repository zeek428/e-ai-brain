from __future__ import annotations

from pathlib import Path

MIGRATION = Path("app/db/migrations/037_knowledge_management_assets.sql")
COMPOSE = Path("../../docker-compose.yml")


def test_knowledge_management_migration_declares_assets_folders_jobs_and_chunk_sets():
    sql = MIGRATION.read_text(encoding="utf-8")

    for table in [
        "knowledge_folders",
        "knowledge_assets",
        "knowledge_import_jobs",
        "knowledge_chunk_sets",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
        create_table = sql.split(f"CREATE TABLE IF NOT EXISTS {table}", maxsplit=1)[1]
        create_table = create_table.split(");", maxsplit=1)[0]
        assert "created_at timestamptz NOT NULL DEFAULT now()" in create_table
        assert "updated_at timestamptz NOT NULL DEFAULT now()" in create_table

    for column in [
        "ADD COLUMN IF NOT EXISTS knowledge_space_id text",
        "ADD COLUMN IF NOT EXISTS folder_id text",
        "ADD COLUMN IF NOT EXISTS source_asset_id text",
        "ADD COLUMN IF NOT EXISTS parsed_asset_id text",
        "ADD COLUMN IF NOT EXISTS active_chunk_set_id text",
        "ADD COLUMN IF NOT EXISTS document_version integer",
        "ADD COLUMN IF NOT EXISTS chunk_set_id text",
    ]:
        assert column in sql

    for index in [
        "idx_knowledge_documents_space_folder",
        "idx_knowledge_assets_document",
        "idx_knowledge_import_jobs_document_status",
        "idx_knowledge_chunks_chunk_set",
    ]:
        assert index in sql


def test_docker_compose_declares_private_minio_service_for_knowledge_assets():
    compose = COMPOSE.read_text(encoding="utf-8")

    assert "minio:" in compose
    assert "minio/minio" in compose
    assert "MINIO_ROOT_USER" in compose
    assert "MINIO_ROOT_PASSWORD" in compose
    assert "9000:9000" in compose
    assert "minio_data:" in compose
    assert "OBJECT_STORAGE_PROVIDER: minio" in compose
