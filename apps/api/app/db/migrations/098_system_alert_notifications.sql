CREATE TABLE IF NOT EXISTS system_alert_notifications (
  id text PRIMARY KEY,
  alert_id text NOT NULL REFERENCES system_alert_incidents(id) ON DELETE CASCADE,
  subscription_id text NOT NULL REFERENCES system_alert_subscriptions(id) ON DELETE CASCADE,
  channel text NOT NULL CHECK (channel IN ('email', 'dingtalk', 'webhook', 'in_app')),
  target text NOT NULL,
  severity text NOT NULL CHECK (severity IN ('info', 'low', 'medium', 'high')),
  status text NOT NULL DEFAULT 'pending' CHECK (
    status IN ('pending', 'sent', 'failed', 'skipped')
  ),
  attempts integer NOT NULL DEFAULT 0,
  last_error text,
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  sent_at timestamptz,
  UNIQUE (alert_id, subscription_id)
);

CREATE INDEX IF NOT EXISTS idx_system_alert_notifications_status_created
  ON system_alert_notifications(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_system_alert_notifications_alert
  ON system_alert_notifications(alert_id);
