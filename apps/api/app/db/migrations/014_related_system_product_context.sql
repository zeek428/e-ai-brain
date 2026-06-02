ALTER TABLE related_systems
  ADD COLUMN IF NOT EXISTS product_id text REFERENCES products(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_related_systems_product_status
  ON related_systems (product_id, status);
