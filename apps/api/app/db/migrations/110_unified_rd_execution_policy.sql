ALTER TABLE rd_task_executor_policies
  ADD COLUMN IF NOT EXISTS strategy_config jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN rd_task_executor_policies.strategy_config IS
  'Canonical unified R&D execution policy configuration; role bindings are normalized separately.';
