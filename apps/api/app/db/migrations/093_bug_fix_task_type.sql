UPDATE brain_apps
SET config = jsonb_set(
      COALESCE(config, '{}'::jsonb),
      '{default_task_types}',
      CASE
        WHEN COALESCE(config->'default_task_types', '[]'::jsonb) ? 'bug_fix'
          THEN COALESCE(config->'default_task_types', '[]'::jsonb)
        ELSE COALESCE(config->'default_task_types', '[]'::jsonb) || '["bug_fix"]'::jsonb
      END,
      true
    ),
    updated_at = now()
WHERE id = 'rd_brain';
