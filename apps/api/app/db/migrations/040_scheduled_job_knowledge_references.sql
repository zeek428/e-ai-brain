ALTER TABLE IF EXISTS scheduled_jobs
  ADD COLUMN IF NOT EXISTS knowledge_document_ids jsonb NOT NULL DEFAULT '[]'::jsonb;
