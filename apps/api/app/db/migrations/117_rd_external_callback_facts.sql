-- A verified Git callback is a durable trust-boundary fact.  Worker retries
-- may change processing metadata, but never the signed payload or its mapped
-- product/repository/ref binding.

CREATE OR REPLACE FUNCTION prevent_external_event_callback_fact_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.provider IS DISTINCT FROM OLD.provider
     OR NEW.event_type IS DISTINCT FROM OLD.event_type
     OR NEW.delivery_id IS DISTINCT FROM OLD.delivery_id
     OR NEW.signature_status IS DISTINCT FROM OLD.signature_status
     OR NEW.payload_hash IS DISTINCT FROM OLD.payload_hash
     OR NEW.payload_json IS DISTINCT FROM OLD.payload_json
     OR NEW.received_at IS DISTINCT FROM OLD.received_at
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'external_event_inbox callback fact is immutable';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_external_event_callback_fact_immutable ON external_event_inbox;
CREATE TRIGGER trg_external_event_callback_fact_immutable
  BEFORE UPDATE ON external_event_inbox
  FOR EACH ROW
  EXECUTE FUNCTION prevent_external_event_callback_fact_mutation();
