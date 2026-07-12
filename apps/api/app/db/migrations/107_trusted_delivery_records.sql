CREATE TABLE IF NOT EXISTS trusted_delivery_records (
  record_type text NOT NULL,
  id text NOT NULL,
  product_id text REFERENCES products(id) ON DELETE CASCADE,
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (record_type, id)
);

CREATE INDEX IF NOT EXISTS idx_trusted_delivery_records_type_product_updated
  ON trusted_delivery_records (record_type, product_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_trusted_delivery_records_type_updated
  ON trusted_delivery_records (record_type, updated_at DESC);
