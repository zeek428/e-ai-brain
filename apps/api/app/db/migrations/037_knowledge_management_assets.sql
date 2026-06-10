CREATE TABLE IF NOT EXISTS knowledge_folders (
  id text PRIMARY KEY DEFAULT ('knowledge_folder_' || replace(gen_random_uuid()::text, '-', '')),
  knowledge_space_id text NOT NULL REFERENCES knowledge_spaces(id) ON DELETE CASCADE,
  parent_folder_id text REFERENCES knowledge_folders(id) ON DELETE SET NULL,
  name text NOT NULL,
  status text NOT NULL DEFAULT 'active',
  sort_order integer NOT NULL DEFAULT 0,
  created_by text REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_folders_space_parent
  ON knowledge_folders(knowledge_space_id, parent_folder_id, status);

CREATE TABLE IF NOT EXISTS knowledge_assets (
  id text PRIMARY KEY DEFAULT ('knowledge_asset_' || replace(gen_random_uuid()::text, '-', '')),
  knowledge_space_id text NOT NULL REFERENCES knowledge_spaces(id) ON DELETE CASCADE,
  document_id text,
  asset_type text NOT NULL DEFAULT 'original',
  storage_provider text NOT NULL DEFAULT 'minio',
  bucket text NOT NULL,
  object_key text NOT NULL,
  content_hash text NOT NULL,
  filename text NOT NULL DEFAULT '',
  mime_type text NOT NULL DEFAULT 'application/octet-stream',
  size_bytes bigint NOT NULL DEFAULT 0,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text NOT NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (bucket, object_key)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_assets_document
  ON knowledge_assets(document_id, asset_type);

CREATE INDEX IF NOT EXISTS idx_knowledge_assets_space
  ON knowledge_assets(knowledge_space_id, asset_type);

CREATE TABLE IF NOT EXISTS knowledge_import_jobs (
  id text PRIMARY KEY DEFAULT ('knowledge_import_job_' || replace(gen_random_uuid()::text, '-', '')),
  document_id text NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
  source_asset_id text,
  parser_engine text NOT NULL DEFAULT 'plain_text',
  chunk_strategy text NOT NULL DEFAULT 'simple_text',
  status text NOT NULL DEFAULT 'uploaded',
  progress integer NOT NULL DEFAULT 0,
  error_code text,
  error_message text,
  created_by text NOT NULL REFERENCES users(id),
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_import_jobs_document_status
  ON knowledge_import_jobs(document_id, status);

CREATE TABLE IF NOT EXISTS knowledge_chunk_sets (
  id text PRIMARY KEY DEFAULT ('knowledge_chunk_set_' || replace(gen_random_uuid()::text, '-', '')),
  document_id text NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
  source_asset_id text,
  parsed_asset_id text,
  parser_engine text NOT NULL DEFAULT 'plain_text',
  parser_version text NOT NULL DEFAULT 'v1',
  chunk_strategy text NOT NULL DEFAULT 'simple_text',
  embedding_model text,
  embedding_dimension integer,
  status text NOT NULL DEFAULT 'building',
  created_by text NOT NULL REFERENCES users(id),
  activated_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunk_sets_document_status
  ON knowledge_chunk_sets(document_id, status);

ALTER TABLE knowledge_documents
  ADD COLUMN IF NOT EXISTS knowledge_space_id text REFERENCES knowledge_spaces(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS folder_id text REFERENCES knowledge_folders(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS source_asset_id text,
  ADD COLUMN IF NOT EXISTS parsed_asset_id text,
  ADD COLUMN IF NOT EXISTS active_chunk_set_id text,
  ADD COLUMN IF NOT EXISTS parser_engine text,
  ADD COLUMN IF NOT EXISTS chunk_strategy text,
  ADD COLUMN IF NOT EXISTS document_version integer NOT NULL DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_space_folder
  ON knowledge_documents(knowledge_space_id, folder_id, index_status);

ALTER TABLE knowledge_chunks
  ADD COLUMN IF NOT EXISTS chunk_set_id text,
  ADD COLUMN IF NOT EXISTS parent_chunk_id text REFERENCES knowledge_chunks(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS content_hash text;

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_chunk_set
  ON knowledge_chunks(chunk_set_id, chunk_index);
