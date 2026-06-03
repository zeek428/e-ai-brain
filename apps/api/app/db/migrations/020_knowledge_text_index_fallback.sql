ALTER TABLE knowledge_documents
  ADD COLUMN IF NOT EXISTS vector_index_error text;

UPDATE knowledge_documents
SET index_status = 'vector_indexed'
WHERE index_status = 'indexed';
