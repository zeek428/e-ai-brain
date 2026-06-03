ALTER TABLE model_gateway_configs
  ALTER COLUMN default_embedding_model DROP NOT NULL,
  ADD COLUMN IF NOT EXISTS embedding_connection_mode text NOT NULL DEFAULT 'reuse_chat',
  ADD COLUMN IF NOT EXISTS embedding_base_url text,
  ADD COLUMN IF NOT EXISTS embedding_api_key_ref text,
  ADD COLUMN IF NOT EXISTS embedding_dimension integer;

UPDATE model_gateway_configs
SET embedding_connection_mode = 'disabled'
WHERE COALESCE(default_embedding_model, '') = '';

UPDATE model_gateway_configs
SET embedding_dimension = 1536
WHERE default_embedding_model IS NOT NULL
  AND default_embedding_model <> ''
  AND embedding_dimension IS NULL;
