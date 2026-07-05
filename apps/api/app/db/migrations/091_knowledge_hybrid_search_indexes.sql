CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_title_trgm
  ON knowledge_documents
  USING gin (lower(title) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_content_trgm
  ON knowledge_chunks
  USING gin (lower(content) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_search_scope
  ON knowledge_chunks(document_id, chunk_set_id, chunk_index)
  INCLUDE (content_hash);
