-- P1 governed role-experience decisions.  Candidate content/provenance is append-only;
-- only its review lifecycle may change, and every change has an immutable decision fact.

CREATE TABLE IF NOT EXISTS rd_role_experience_decisions (
  id text PRIMARY KEY,
  experience_id text NOT NULL REFERENCES rd_role_experience_records(id) ON DELETE RESTRICT,
  decision text NOT NULL,
  comment text,
  reviewer_user_id text NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  expected_review_version bigint NOT NULL,
  resulting_review_version bigint NOT NULL,
  idempotency_key text NOT NULL,
  request_hash text NOT NULL,
  response_json jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (experience_id, idempotency_key),
  CONSTRAINT ck_rd_role_experience_decision_kind CHECK (decision IN ('approve', 'reject', 'retire')),
  CONSTRAINT ck_rd_role_experience_decision_versions CHECK (
    expected_review_version > 0 AND resulting_review_version = expected_review_version + 1
  )
);

CREATE INDEX IF NOT EXISTS idx_rd_role_experience_scope
  ON rd_role_experience_records (brain_app_id, role_code, work_item_type, scenario, status, confidence DESC, created_at DESC, id);
CREATE INDEX IF NOT EXISTS idx_rd_role_experience_product_scope
  ON rd_role_experience_records USING gin (product_scope);
CREATE INDEX IF NOT EXISTS idx_rd_role_experience_sources_feedback
  ON rd_role_experience_sources (role_feedback_record_id, experience_id);

CREATE OR REPLACE FUNCTION protect_rd_role_experience_record() RETURNS trigger AS $$
BEGIN
  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.experience_key IS DISTINCT FROM OLD.experience_key
     OR NEW.version IS DISTINCT FROM OLD.version
     OR NEW.brain_app_id IS DISTINCT FROM OLD.brain_app_id
     OR NEW.product_scope IS DISTINCT FROM OLD.product_scope
     OR NEW.role_code IS DISTINCT FROM OLD.role_code
     OR NEW.work_item_type IS DISTINCT FROM OLD.work_item_type
     OR NEW.scenario IS DISTINCT FROM OLD.scenario
     OR NEW.risk_scope IS DISTINCT FROM OLD.risk_scope
     OR NEW.repository_trust_domains IS DISTINCT FROM OLD.repository_trust_domains
     OR NEW.tool_trust_domains IS DISTINCT FROM OLD.tool_trust_domains
     OR NEW.content IS DISTINCT FROM OLD.content
     OR NEW.evidence_refs IS DISTINCT FROM OLD.evidence_refs
     OR NEW.strategy_snapshot_id IS DISTINCT FROM OLD.strategy_snapshot_id
     OR NEW.confidence IS DISTINCT FROM OLD.confidence
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'rd_role_experience_records content is immutable';
  END IF;
  IF NOT ((OLD.status = 'pending' AND NEW.status IN ('approved', 'rejected'))
       OR (OLD.status = 'approved' AND NEW.status = 'retired')) THEN
    RAISE EXCEPTION 'invalid rd role experience lifecycle transition';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_rd_role_experience_record_governance ON rd_role_experience_records;
CREATE TRIGGER trg_rd_role_experience_record_governance
BEFORE UPDATE ON rd_role_experience_records
FOR EACH ROW EXECUTE FUNCTION protect_rd_role_experience_record();

CREATE OR REPLACE FUNCTION protect_rd_role_experience_source() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'rd_role_experience_sources are immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_rd_role_experience_sources_immutable ON rd_role_experience_sources;
CREATE TRIGGER trg_rd_role_experience_sources_immutable
BEFORE UPDATE OR DELETE ON rd_role_experience_sources
FOR EACH ROW EXECUTE FUNCTION protect_rd_role_experience_source();

CREATE OR REPLACE FUNCTION protect_rd_role_experience_decision() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'rd_role_experience_decisions are immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_rd_role_experience_decisions_immutable ON rd_role_experience_decisions;
CREATE TRIGGER trg_rd_role_experience_decisions_immutable
BEFORE UPDATE OR DELETE ON rd_role_experience_decisions
FOR EACH ROW EXECUTE FUNCTION protect_rd_role_experience_decision();

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_brain_app_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON rd_role_experience_records TO ai_brain_app_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON rd_role_experience_sources TO ai_brain_app_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON rd_role_experience_decisions TO ai_brain_app_runtime';
  END IF;
END;
$$;
