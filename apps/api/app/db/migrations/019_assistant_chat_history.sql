CREATE TABLE IF NOT EXISTS assistant_conversations (
  id text PRIMARY KEY,
  user_id text NOT NULL,
  product_id text,
  title text NOT NULL,
  message_count integer NOT NULL DEFAULT 0,
  last_message_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assistant_messages (
  id text PRIMARY KEY,
  conversation_id text NOT NULL REFERENCES assistant_conversations(id) ON DELETE CASCADE,
  user_id text NOT NULL,
  role text NOT NULL,
  content text NOT NULL,
  product_id text,
  model text,
  suggestions jsonb NOT NULL DEFAULT '[]'::jsonb,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_assistant_conversations_user_updated
  ON assistant_conversations (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_assistant_messages_conversation_created
  ON assistant_messages (conversation_id, created_at ASC);
