UPDATE menu_resources
SET
  path = '/tasks/ai-capabilities',
  parent_code = 'task',
  sort_order = 22,
  updated_at = now()
WHERE code = 'system.ai_capabilities';

UPDATE menu_resources
SET
  path = '/tasks/scheduled-jobs',
  parent_code = 'task',
  sort_order = 23,
  updated_at = now()
WHERE code = 'system.scheduled_jobs';

UPDATE menu_resources
SET
  path = '/tasks/plugins',
  parent_code = 'task',
  sort_order = 24,
  updated_at = now()
WHERE code = 'system.plugins';
