CREATE TABLE IF NOT EXISTS id_counters (
  prefix text PRIMARY KEY,
  next_value integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
