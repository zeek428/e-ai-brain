# R&D Collaboration Review Remediation Design

## Goal

Close the P1/P2 findings from the implementation review without
changing the product-version entry point, the frozen-policy model, or the P0
`ready_for_release` delivery boundary.

## Chosen approach

The dispatch service will build an in-memory delivery bundle first and persist
all durable records in the same PostgreSQL transaction that changes a work
item from `ready`/`rework_required` to `running`.  The bundle includes the AI
task, Runner task, attempt, execution context manifest, optional Agent Loop
run and iteration, and optional budget ledger.  A failed compare-and-set or
Runner insert rolls back all of them.  This is preferred over compensating
deletes because it leaves no interval in which a retry can observe or charge
an uncommitted task.

The automatic dispatcher will classify domain errors.  Capacity exhaustion,
concurrent state changes, and explicitly retryable executor failures remain
deferred.  Configuration, frozen-snapshot, role-assignment, and Runner safety
approval failures pause the affected work item, persist the diagnostic event
and audit record, and create a frozen human decision whose options are
`repair_configuration` and `cancel_work_item`.  The version overview can then
surface the normal waiting-human state instead of an indefinitely ready item.

The deterministic plan analyser will require each `implementation` work item
to carry at least one repository-scoped `write` claim.  Finally, the dispatcher
will count every processed work item, including high-risk decision creation,
against its sweep limit.  This prevents a single polling iteration from
creating an unbounded number of human decisions.

## Review supplement: dispatch audit, Runner approval, and retry control

The preparation path must be entirely referentially transparent for production
state: manifest, Agent Loop, Runner-task, and work-item audit builders return
their records explicitly. The caller constructs one `audit_events` bundle and
the PostgreSQL dispatch transaction persists it with the task, Runner, attempt,
work-item transition, event, and execution-governance records. No production
dispatch code may inspect or use `PostgresRuntimeStore.audit_events` as an
inter-stage transport.

`AI_EXECUTOR_APPROVAL_REQUIRED` is a human-gated outcome, not a retryable
fault. Its first preflight creates, in the same idempotent command as the
work-item pause, a durable runner-safety approval request and a frozen
`runner_safety_approval` decision. The decision contains only safe diagnostic
evidence and the approval-request identity. Approval writes an immutable
approval snapshot covering the frozen blocked operations; the next dispatch
looks up that approved snapshot by its deterministic
`work-item + attempt-number` identity and passes it to the existing Runner
safety contract. Rejecting the decision cancels the work item. Changing a
strategy snapshot or silently weakening a safety check is never a resolution.

Retryable faults are recorded on the ready work item as a small operational
state: safe error code, failure count, and `next_dispatch_at`. Backoff is
bounded exponential (5 seconds, 10 seconds, 20 seconds) and a fourth
consecutive retryable failure is escalated through the existing frozen human
decision mechanism. A successful dispatch clears this retry state. The Worker
and version overview expose only safe aggregate/count information.

The production scanner selects only due `ready`/`rework_required` candidates
from PostgreSQL. It uses a bounded candidate page and batched predecessor
lookup; it does not hydrate an unbounded run or issue one dependency query per
item. A locked global sweep cursor rotates active runs and a per-run cursor
continues the due/priority/ID page after restart. Candidate reservation carries
the work-item optimistic-lock version and the observed due time into the final
dispatch transaction; that transaction rechecks both values before creating
any execution artifact, so a concurrent backoff update makes the reservation a
safe no-op.

Candidate reservation is not authority to dispatch after the parent aggregate
changes. The final PostgreSQL bundle transaction first obtains the parent ID
with a non-locking lookup, then follows the canonical
`rd_collaboration_runs FOR UPDATE -> rd_work_items FOR UPDATE` lock order used
by cancel and suspension. After both locks it revalidates parent ownership,
run/item status, reservation version and due time. If a decision or another
transaction has moved the run to `waiting_human` (or any terminal/non-active
state), or cancelled the item after reservation, dispatch fails closed before
any task, Runner, attempt, event, or audit artifact is committed. The shared
lock order prevents the cancel/suspend race from producing SQLSTATE `40P01`.

Large dispatch indexes and destructive cleanup have different startup
lifecycles. The ordinary API entrypoint excludes cleanup migration 121 and
index migrations 125-128. Cleanup 121 remains explicit and maintenance-fenced.
For 125-128, non-test API repository initialization uses an autocommit
compatibility connection, one non-blocking advisory lock, catalog
validity/readiness checks, and concurrent index drop/create. Only one startup
instance performs this work; other instances skip without waiting and a later
startup rechecks the indexes.

## Completed implementation notes

- **Task 4** — The implementation and source-spec verification scope is
  complete. It has no user-facing route, page, copy, form, permission or help
  screenshot change; final changelog aggregation and release delivery remain
  controller-owned.
- **Task 5** — `af8616938` moves all dispatch audit records into an explicit
  durable bundle. Together with the existing atomic bundle command, a failed
  Runner write, compare-and-set or later bundle write rolls back task, Runner,
  attempt, manifest, Agent Loop, budget, event and audit facts.
- **Task 6** — `6f2465d9c` through `171c687ee` implement the collaboration
  `runner_safety_approval` decision. Identity is deterministic by work item,
  attempt and, after expiry, renewal; generic Runner/plugin approval mutations
  are fenced from collaboration requests. Approval produces an immutable,
  bounded operation snapshot, and final PostgreSQL dispatch locks and
  revalidates the canonical instruction/safety/approval proof before writing a
  Runner task.
- **Task 7** — `6f8db6d33` through `698a86c47` persist the safe retry state,
  5/10/20-second backoff and fourth-failure decision, then add indexed due
  pages, batch dependency hydration, durable fair continuation and stale
  reservation protection.
- **Task 8** — `e775507e9` and `48e82eda2` separate ordinary startup migrations
  from explicit cleanup/concurrent large-index work and add the parent-run
  fence; `4623ddc13` canonicalizes final dispatch to run-then-item row locking
  with post-lock provenance/status/version/due revalidation.

Representative regression evidence is
`test_postgres_autonomous_dispatch_persists_explicit_audit_bundle_without_reading_store_audits`,
`test_postgres_runner_safety_approval_is_atomic_replay_safe_and_dispatchable`,
`test_postgres_expired_runner_safety_approval_renews_without_dispatch_artifacts`,
`test_postgres_stale_reserved_worker_cannot_bypass_new_retry_backoff` and
`test_repository_reserves_fair_dispatch_pages_across_restart_and_workers`, plus
`test_api_entrypoint_runs_only_ordinary_additive_migrations`,
`test_concurrent_index_compatibility_path_serializes_and_skips_valid_index` and
`test_postgres_final_dispatch_and_cancel_use_run_then_work_item_lock_order` and
`test_postgres_final_dispatch_waits_for_parent_suspension_without_artifacts`.

## Compatibility and safety

- No public API gains a direct AI-task start path; all state remains owned by
  collaboration work-item commands.
- The frozen strategy snapshot remains the sole source for executor, budget,
  and autonomy choices.
- Only the affected work item pauses for a permanent dispatch fault; unrelated
  ready work can continue when dependencies permit.
- Retryable failures never auto-approve a decision or widen access.
- Runner approval identities are deterministic per work item and attempt, so a
  Worker restart or repeated sweep cannot create a second approval request.
- Retry schedules never contain exception text, paths, prompts, tokens, or
  credentials; the persisted state carries only a stable safe error code.
- Existing MemoryStore tests retain the same observable state transitions;
  PostgreSQL remains the production source of truth.

## Verification

Regression tests will prove that concurrent or failed autonomous dispatches
leave exactly one task bundle and no orphan manifests, loop rows, or budget
ledgers; permanent dispatch faults create a pause and decision while temporary
capacity faults remain deferred; read-only implementation claims are rejected;
and the decision sweep limit caps all processed outcomes.  The full backend
suite, frontend checks, production-mode API/page smoke check, and help-center
validation remain commit gates.
