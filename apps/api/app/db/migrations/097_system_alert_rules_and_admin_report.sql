CREATE TABLE IF NOT EXISTS system_alert_rules (
  id text PRIMARY KEY,
  name text NOT NULL,
  source text NOT NULL DEFAULT 'system_check',
  component text,
  severity_min text NOT NULL DEFAULT 'medium' CHECK (
    severity_min IN ('info', 'low', 'medium', 'high')
  ),
  owner text,
  notification_scope text NOT NULL DEFAULT 'global',
  condition_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  enabled boolean NOT NULL DEFAULT true,
  created_by text REFERENCES users(id),
  updated_by text REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_system_alert_rules_enabled_source
  ON system_alert_rules(enabled, source, severity_min);

INSERT INTO system_alert_rules (
  id, name, source, component, severity_min, owner, notification_scope,
  condition_json, enabled, created_by, updated_by
)
VALUES
  (
    'alert_rule_system_high',
    '系统检查高优先级告警',
    'system_check',
    NULL,
    'high',
    '平台运维',
    'global',
    '{"description":"任一系统检查达到 high severity 时生成告警。"}'::jsonb,
    true,
    'user_admin',
    'user_admin'
  ),
  (
    'alert_rule_product_score_medium',
    '产品接入低分告警',
    'product_score',
    'product_onboarding',
    'medium',
    '产品负责人',
    'global',
    '{"score_lt":80,"description":"产品接入评分低于 80 分时提示补齐接入项。"}'::jsonb,
    true,
    'user_admin',
    'user_admin'
  ),
  (
    'alert_rule_dingtalk_key_medium',
    '钉钉授权即将过期告警',
    'dingtalk_lifecycle',
    'dingtalk_mcp',
    'medium',
    '平台运维',
    'global',
    '{"days_left_lte":14,"description":"钉钉 MCP 授权 key 距过期小于等于 14 天时提醒轮换。"}'::jsonb,
    true,
    'user_admin',
    'user_admin'
  )
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  source = EXCLUDED.source,
  component = EXCLUDED.component,
  severity_min = EXCLUDED.severity_min,
  owner = EXCLUDED.owner,
  notification_scope = EXCLUDED.notification_scope,
  condition_json = EXCLUDED.condition_json,
  enabled = EXCLUDED.enabled,
  updated_by = EXCLUDED.updated_by,
  updated_at = now();
