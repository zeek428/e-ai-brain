-- Task 11: a failed independent quality gate is a first-class rework state.
-- Existing installations created the original constraint in migration 109, so
-- CREATE TABLE IF NOT EXISTS alone cannot extend its permitted state set.

ALTER TABLE IF EXISTS rd_work_items
  DROP CONSTRAINT IF EXISTS ck_rd_work_item_status;

ALTER TABLE IF EXISTS rd_work_items
  ADD CONSTRAINT ck_rd_work_item_status CHECK (
    status IN (
      'draft', 'ready', 'claimed', 'running', 'waiting_human', 'blocked',
      'rework_required', 'reviewing', 'completed', 'failed', 'cancelled'
    )
  );

-- Work items are planned at version scope, which may contain more than one
-- requirement.  The internal AI-task bridge therefore needs an explicit,
-- durable requirement attribution instead of selecting an arbitrary scoped
-- requirement at dispatch time.
ALTER TABLE IF EXISTS rd_work_items
  ADD COLUMN IF NOT EXISTS requirement_id text REFERENCES requirements(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_rd_work_items_run_requirement
  ON rd_work_items (collaboration_run_id, requirement_id);
