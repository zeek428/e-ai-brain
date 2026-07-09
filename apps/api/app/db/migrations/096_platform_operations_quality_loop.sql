CREATE TABLE IF NOT EXISTS system_alert_incidents (
  id text PRIMARY KEY,
  source text NOT NULL,
  component text,
  title text NOT NULL,
  severity text NOT NULL CHECK (severity IN ('info', 'low', 'medium', 'high')),
  status text NOT NULL DEFAULT 'open' CHECK (
    status IN ('open', 'acknowledged', 'resolving', 'closed', 'ignored')
  ),
  owner text,
  message text,
  action_href text,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  acknowledged_at timestamptz,
  acknowledged_by text,
  resolved_at timestamptz,
  resolved_by text,
  close_reason text,
  postmortem text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_system_alert_incidents_status_last_seen
  ON system_alert_incidents(status, last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_system_alert_incidents_source_component
  ON system_alert_incidents(source, component);

CREATE TABLE IF NOT EXISTS system_alert_subscriptions (
  id text PRIMARY KEY,
  scope text NOT NULL DEFAULT 'global',
  channel text NOT NULL CHECK (channel IN ('email', 'dingtalk', 'webhook', 'in_app')),
  target text NOT NULL,
  severity_min text NOT NULL DEFAULT 'medium' CHECK (
    severity_min IN ('info', 'low', 'medium', 'high')
  ),
  enabled boolean NOT NULL DEFAULT true,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_system_alert_subscriptions_enabled
  ON system_alert_subscriptions(enabled, severity_min);

CREATE TABLE IF NOT EXISTS knowledge_quality_events (
  id text PRIMARY KEY,
  event_type text NOT NULL CHECK (
    event_type IN ('search', 'rag', 'feedback', 'citation_click')
  ),
  query text,
  knowledge_space_id text,
  user_id text,
  hit_count integer NOT NULL DEFAULT 0,
  no_result boolean NOT NULL DEFAULT false,
  citation_count integer NOT NULL DEFAULT 0,
  latency_ms numeric(12, 2),
  retrieval_modes jsonb NOT NULL DEFAULT '{}'::jsonb,
  feedback_value text,
  feedback_comment text,
  citation_chunk_id text,
  citation_document_id text,
  related_event_id text REFERENCES knowledge_quality_events(id) ON DELETE SET NULL,
  trace_id text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_quality_events_type_created
  ON knowledge_quality_events(event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_quality_events_space_created
  ON knowledge_quality_events(knowledge_space_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_quality_events_related
  ON knowledge_quality_events(related_event_id);

INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  (
    'system.alerts.manage',
    '管理系统告警',
    'system',
    '处理系统健康告警、维护负责人、关闭原因和复盘记录。',
    'high',
    true,
    'active'
  ),
  (
    'knowledge.quality.read',
    '查看知识质量',
    'knowledge',
    '查看知识检索日志、无结果率、引用点击率和 RAG 反馈指标。',
    'normal',
    true,
    'active'
  )
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  category = EXCLUDED.category,
  description = EXCLUDED.description,
  risk_level = EXCLUDED.risk_level,
  is_system = EXCLUDED.is_system,
  status = EXCLUDED.status,
  updated_at = now();

WITH admin_role AS (
  SELECT id FROM roles WHERE code = 'admin'
)
INSERT INTO role_permissions (role_id, permission_code, granted_by)
SELECT admin_role.id, permission_code, 'user_admin'
FROM admin_role
CROSS JOIN (
  VALUES ('system.alerts.manage'), ('knowledge.quality.read')
) AS permission_values(permission_code)
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();

UPDATE role_definitions
SET
  permissions = (
    SELECT jsonb_agg(permission_code ORDER BY permission_code)
    FROM (
      SELECT DISTINCT permission_code
      FROM jsonb_array_elements_text(
        COALESCE(role_definitions.permissions, '[]'::jsonb)
        || '["system.alerts.manage","knowledge.quality.read"]'::jsonb
      ) AS permission_values(permission_code)
    ) AS merged_permissions
  ),
  updated_at = now()
WHERE code = 'admin';
