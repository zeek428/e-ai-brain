-- Harden the P1 experience lifecycle against direct runtime-table writes.
-- Candidate creation is pending-only; a decision transaction must set the
-- transaction-local guard before advancing its lifecycle.

CREATE OR REPLACE FUNCTION protect_rd_role_experience_record() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NEW.status <> 'pending' OR NEW.review_version <> 1
       OR NEW.reviewed_by IS NOT NULL OR NEW.reviewed_at IS NOT NULL THEN
      RAISE EXCEPTION 'rd role experience candidates must be inserted pending and unreviewed';
    END IF;
    RETURN NEW;
  END IF;

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
  IF NEW.review_version <> OLD.review_version + 1
     OR NEW.reviewed_by IS NULL OR NEW.reviewed_at IS NULL THEN
    RAISE EXCEPTION 'rd role experience lifecycle must carry one reviewer and version increment';
  END IF;
  IF current_setting('app.rd_role_experience_governed_decision', true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'rd role experience lifecycle requires governed decision transaction';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_rd_role_experience_record_governance ON rd_role_experience_records;
CREATE TRIGGER trg_rd_role_experience_record_governance
BEFORE INSERT OR UPDATE ON rd_role_experience_records
FOR EACH ROW EXECUTE FUNCTION protect_rd_role_experience_record();

CREATE OR REPLACE FUNCTION protect_rd_role_experience_source() RETURNS trigger AS $$
DECLARE
  parent_status text;
  parent_snapshot_id text;
  feedback_snapshot_id text;
BEGIN
  IF TG_OP <> 'INSERT' THEN
    RAISE EXCEPTION 'rd_role_experience_sources are immutable';
  END IF;
  SELECT status, strategy_snapshot_id
    INTO parent_status, parent_snapshot_id
    FROM rd_role_experience_records
    WHERE id = NEW.experience_id
    FOR KEY SHARE;
  SELECT strategy_snapshot_id
    INTO feedback_snapshot_id
    FROM role_feedback_records
    WHERE id = NEW.role_feedback_record_id
    FOR KEY SHARE;
  IF parent_status IS DISTINCT FROM 'pending'
     OR parent_snapshot_id IS DISTINCT FROM NEW.strategy_snapshot_id
     OR feedback_snapshot_id IS DISTINCT FROM NEW.strategy_snapshot_id THEN
    RAISE EXCEPTION 'experience source must be added while candidate is pending with matching snapshot';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_rd_role_experience_sources_immutable ON rd_role_experience_sources;
CREATE TRIGGER trg_rd_role_experience_sources_immutable
BEFORE INSERT OR UPDATE OR DELETE ON rd_role_experience_sources
FOR EACH ROW EXECUTE FUNCTION protect_rd_role_experience_source();
