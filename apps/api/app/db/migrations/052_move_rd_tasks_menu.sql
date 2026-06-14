UPDATE menu_resources
SET
  name = '研发任务',
  path = '/delivery/rd-tasks',
  parent_code = 'delivery',
  sort_order = 35,
  updated_at = now()
WHERE code = 'task.center';

UPDATE role_definitions
SET
  menu_scope = (
    SELECT jsonb_agg(
      CASE
        WHEN item.value = '"任务管理"'::jsonb THEN '"研发任务"'::jsonb
        ELSE item.value
      END
    )
    FROM jsonb_array_elements(role_definitions.menu_scope) AS item(value)
  ),
  updated_at = now()
WHERE menu_scope ? '任务管理';
