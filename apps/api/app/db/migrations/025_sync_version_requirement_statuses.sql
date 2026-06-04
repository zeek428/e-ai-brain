-- Backfill requirement statuses to match iteration version stages after the
-- version-driven synchronization rules were expanded.

UPDATE requirements r
SET status = 'ready_for_dev',
    updated_at = now()
FROM product_versions v
WHERE r.version_id = v.id
  AND v.status = 'active'
  AND r.status IN ('approved', 'planned');

UPDATE requirements r
SET status = 'testing',
    updated_at = now()
FROM product_versions v
WHERE r.version_id = v.id
  AND v.status = 'testing'
  AND r.status IN (
    'approved',
    'planned',
    'ready_for_dev',
    'designing',
    'developing',
    'code_reviewing',
    'task_created'
  );

UPDATE requirements r
SET status = 'released',
    updated_at = now()
FROM product_versions v
WHERE r.version_id = v.id
  AND v.status = 'released'
  AND r.status IN ('ready_for_release', 'testing');
