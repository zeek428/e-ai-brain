UPDATE menu_resources
SET
  path = '/tasks/scheduled-jobs',
  parent_code = 'task',
  sort_order = CASE WHEN sort_order IN (22, 23) THEN 21 ELSE sort_order END,
  updated_at = now()
WHERE code = 'system.scheduled_jobs';

UPDATE menu_resources
SET
  path = '/tasks/ai-capabilities',
  parent_code = 'task',
  sort_order = CASE WHEN sort_order IN (21, 23) THEN 22 ELSE sort_order END,
  updated_at = now()
WHERE code = 'system.ai_capabilities';

UPDATE menu_resources
SET
  path = '/tasks/plugins',
  parent_code = 'task',
  sort_order = CASE WHEN sort_order IN (22, 23) THEN 24 ELSE sort_order END,
  updated_at = now()
WHERE code = 'system.plugins';
