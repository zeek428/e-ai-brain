ALTER TABLE requirements
  ADD COLUMN IF NOT EXISTS assignee text;

CREATE INDEX IF NOT EXISTS idx_requirements_assignee ON requirements (assignee);
