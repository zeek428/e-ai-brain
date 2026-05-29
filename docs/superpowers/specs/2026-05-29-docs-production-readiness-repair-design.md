# Docs Production-Readiness Repair Design

## Goal

Bring the AI Brain documentation set from a strong MVP design package to a production-ready implementation reference. The repair keeps the existing source-of-truth structure and updates only documentation: no application code, no generated migrations, and no assumptions that implementation files already exist.

## Scope

### In scope

- Fix broken links in the enterprise AI Brain PRD and technical specification.
- Complete acceptance-test traceability by adding missing detailed test cases.
- Clarify phase boundaries across MVP, v1.1, v1.2, and production-readiness validation.
- Add API error semantics for core endpoints.
- Add field-level schema details for P0 tables in the technical specification.
- Add state-machine action matrices for high-impact entities and human gates.
- Upgrade deployment, monitoring, and incident runbooks from local-demo only to staging/production-aware guidance.
- Update README, version index, and changelog to reflect the documentation repair.

### Out of scope

- Adding or modifying application source code.
- Creating actual database migrations.
- Selecting infrastructure vendors beyond the documented Docker Compose and future production constraints.
- Changing product scope or adding new user-facing capabilities beyond clarifying the existing design.

## Target files

- `docs/01-prd/enterprise-ai-brain/prd.md`
- `docs/02-specs/enterprise-ai-brain/spec.md`
- `docs/02-specs/enterprise-ai-brain/api.md`
- `docs/02-specs/enterprise-ai-brain/test-case.md`
- `docs/05-runbooks/deployment.md`
- `docs/05-runbooks/monitoring.md`
- `docs/05-runbooks/incident-response.md`
- `docs/README.md`
- `docs/VERSIONS.md`
- `docs/changelog.md`

## Design

### 1. Acceptance and test traceability

`test-case.md` will gain detailed sections for the five acceptance mappings that currently only appear in the summary table:

- `TC-AIBRAIN-AUDIT-API-006`
- `TC-AIBRAIN-DEPLOY-FUNC-007`
- `TC-AIBRAIN-CONFIG-API-008`
- `TC-AIBRAIN-CONFIG-API-009`
- `TC-AIBRAIN-AUDIT-API-013`

The test summary table will include an explicit phase column. MVP rows will distinguish mandatory closed-loop behavior from placeholder or empty-state requirements. Later-phase tests will remain documented, but their expectations will be marked as v1.1, v1.2, or production-readiness rather than implicit MVP commitments.

### 2. Link and reader-path repair

The nonexistent `solution-review-and-business-flow.html` links in PRD and spec will be replaced with an existing documentation entry or a new Markdown entry if the existing guides do not express the needed implementation path clearly enough.

A concise implementation path will be added to `docs/README.md`, covering the recommended order for P0 tables, P0 APIs, core pages, P0 tests, and runbook validation.

### 3. API error semantics

`api.md` will add a core error-semantics table for high-risk endpoints:

- AI task create/start/detail
- Review approve/edit-approve/reject/request-more-info
- GitLab MR preview and snapshot
- Code review report query
- Knowledge import/search/deposit review
- Model gateway configuration
- Audit event query

Each row will define HTTP status, error code, retryability, audit requirement, and frontend handling guidance.

### 4. P0 data schema detail

`spec.md` will add field-level schema tables for P0 entities:

- `requirements`
- `ai_tasks`
- `human_reviews`
- `gitlab_mr_snapshots`
- `code_review_reports`
- `knowledge_documents`
- `knowledge_chunks`
- `audit_events`

Each table will describe field name, logical type, requiredness, key constraints, and implementation notes. This is not a migration file, but it must be specific enough for API DTOs, migration planning, and test fixture creation.

### 5. State-machine action matrices

`spec.md` will add action matrices for:

- Requirement lifecycle
- AI task lifecycle
- Human review lifecycle
- Knowledge document indexing lifecycle
- GitLab MR snapshot and code-review report lifecycle

Each matrix will include current state, action, target state, allowed role, idempotency or conflict rule, and audit event requirement.

### 6. Production-aware runbooks

Runbooks will keep local Docker Compose commands, but clearly separate local demo, staging, and production-readiness responsibilities.

`deployment.md` will add:

- Environment matrix: local, staging, production.
- Release prerequisites and go/no-go checks.
- Database migration and rollback checks.
- Backup/restore validation gates.
- Secret and GitLab read-only credential checks.
- Code-review no-writeback verification.

`monitoring.md` will add:

- SLO targets for API availability, task execution, knowledge search latency, model gateway failures, and human-review backlog.
- Alert thresholds and severity mapping.
- Traceability expectations across request logs, graph runs, model logs, and audit events.
- Sensitive-data log restrictions.

`incident-response.md` will add:

- Incident roles and escalation path.
- RTO/RPO targets by environment.
- Database migration incident handling.
- Secret exposure handling.
- GitLab writeback boundary violation handling.
- Required post-incident doc updates.

## Validation plan

After editing, run these documentation checks:

1. Verify PRD acceptance mappings all have detailed test sections.
2. Verify Markdown relative links in non-template docs resolve.
3. Scan updated files for placeholder terms such as `TODO`, `TBD`, `待补`, `placeholder`, and unresolved template tokens.
4. Re-read touched sections for phase-boundary consistency.
5. Update changelog and version index last.

## Risks and mitigations

- Risk: production-readiness content may overpromise current implementation maturity.
  - Mitigation: explicitly label the docs as production-readiness requirements and gates, not completed implementation.
- Risk: P0 schema tables become too detailed and drift from future migrations.
  - Mitigation: describe logical schema and constraints, not physical migration syntax.
- Risk: phase boundaries become harder to read after adding a phase column.
  - Mitigation: keep MVP expectations concise and move later-phase completeness details into detailed test sections.

## Approval status

Approved direction: production-readiness repair, documentation only.
