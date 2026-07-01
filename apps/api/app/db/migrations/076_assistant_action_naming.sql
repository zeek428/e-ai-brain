UPDATE assistant_action_reference_configs
SET
  title = '新建动作',
  summary = '生成可确认的动作草案。',
  prompt = '请帮我生成动作草案，先确认连接、请求方法、路径、参数映射和结果写入目标。',
  aliases = (
    SELECT jsonb_agg(DISTINCT alias_value)
    FROM jsonb_array_elements_text(
      aliases || '["动作"]'::jsonb
    ) AS alias_items(alias_value)
  ),
  updated_by = 'system',
  updated_at = now()
WHERE action_key = 'create_plugin_action'
  AND (
    title = '新建插件动作'
    OR summary LIKE '%插件动作%'
    OR prompt LIKE '%插件动作%'
    OR NOT aliases ? '动作'
  );
