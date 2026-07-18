-- EXPLICIT ONLY: this cleanup contract is deliberately excluded from the
-- additive startup migration registry.  It is run by
-- scripts/rd_collaboration_cutover.py cleanup --execute only after schema v2,
-- runtime health, and both v2 write smoke tests have been recorded.
--
-- Legacy columns remain during compatibility retention.  The destructive
-- boundary is removal of obsolete upgrade evidence, which is safe only after
-- the preceding checks and executes atomically with the cleanup marker.
DELETE FROM rd_command_idempotency_records
WHERE command_type LIKE 'legacy_rd_%';
