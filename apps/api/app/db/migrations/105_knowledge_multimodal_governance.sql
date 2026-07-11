ALTER TABLE knowledge_documents
  ADD COLUMN IF NOT EXISTS active_document_version_id text
    REFERENCES knowledge_document_versions(id)
    ON DELETE SET NULL
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE knowledge_import_jobs
  ADD COLUMN IF NOT EXISTS processing_profile_id text
    REFERENCES knowledge_processing_profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS document_version_id text
    REFERENCES knowledge_document_versions(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS parser_config jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE knowledge_chunk_sets
  ADD COLUMN IF NOT EXISTS document_version_id text
    REFERENCES knowledge_document_versions(id) ON DELETE SET NULL;

ALTER TABLE knowledge_citation_feedback
  ADD COLUMN IF NOT EXISTS related_event_id text;

ALTER TABLE knowledge_citation_feedback
  DROP CONSTRAINT IF EXISTS ck_knowledge_citation_feedback_value;

ALTER TABLE knowledge_citation_feedback
  ADD CONSTRAINT ck_knowledge_citation_feedback_value CHECK (
    feedback_value IN ('useful', 'partial', 'not_useful', 'outdated', 'incorrect')
  );

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_active_version
  ON knowledge_documents (active_document_version_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_import_jobs_document_version
  ON knowledge_import_jobs (document_version_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunk_sets_document_version
  ON knowledge_chunk_sets (document_version_id, status, created_at DESC);
