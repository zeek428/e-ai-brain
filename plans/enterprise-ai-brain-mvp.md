# Plan: Enterprise AI Brain MVP

> Source PRD: docs/01-prd/enterprise-ai-brain/prd.md

## Architectural Decisions

- **Runtime shape**: React + TypeScript workbench based on Ant Design Pro conventions, FastAPI modular monolith, PostgreSQL + pgvector, Redis, optional GBrain, and OpenAI-compatible model gateway.
- **Backend modules**: auth, brain_app, product_config, requirement, ai_task, graph_runtime, review, knowledge, long_memory, model_gateway, gitlab_review, code_review_executor, integration, audit, export, dashboard, bug, devops_metrics, user_insights, iteration_planning, and lifecycle_context.
- **Core routes**: `/health`, `/api/auth/*`, `/api/products*`, `/api/requirements*`, `/api/ai-tasks*`, `/api/reviews*`, `/api/devops/gitlab/merge-requests/*`, `/api/knowledge/*`, `/api/writeback/*`, `/api/export/tasks/*/markdown`, and `/api/audit/events`.
- **Schema baseline**: use the P0 table shapes from the technical spec, especially `requirements`, `ai_tasks`, `human_reviews`, `gitlab_mr_snapshots`, `code_review_reports`, `knowledge_documents`, `knowledge_chunks`, `knowledge_deposits`, `mock_issues`, and `audit_events`.
- **State machines**: preserve documented Requirement, AI task, Human Review, Knowledge Document, and GitLab MR Snapshot / Code Review Report transitions.
- **Human gates**: product detail design, technical solution, and code review reports cannot advance or be archived without explicit human confirmation.
- **GitLab boundary**: v1 MVP reads authorized internal GitLab MR metadata and diff snapshots only. It must not write GitLab comments, approvals, request changes, merge state, or branch changes.
- **Model boundary**: business modules call AI only through `model_gateway`; model logs store metadata, not full prompts or full outputs by default.
- **Response contract**: API JSON responses include `trace_id`; `/health` includes `trace_id` directly; Markdown export returns `text/markdown`.
- **Frontend information architecture**: first-class entries are dashboard, product management, requirement management, task center, Bug management, DevOps board, insights/planning, knowledge center, and audit/runtime.

---

## Phase 1: Foundation And Health

**User stories**: platform operator can start the local stack; authenticated users can enter the workbench; every API response is traceable.

### What To Build

Create the monorepo runtime skeleton with FastAPI, React + TypeScript, Docker Compose, PostgreSQL + pgvector, Redis, environment examples, seed data, trace middleware, local auth, and a usable workbench shell.

### Acceptance Criteria

- [ ] Docker Compose configuration validates and includes web, api, postgres, and redis.
- [ ] `/health` reports API, PostgreSQL, Redis, model gateway fallback/configuration state, and `trace_id`.
- [ ] Login, current-user, and logout endpoints work with local Bearer token authentication.
- [ ] API JSON responses use `{data, trace_id}` unless explicitly documented otherwise.
- [ ] The React workbench renders the main navigation and authenticated shell.
- [ ] Backend and frontend test commands are checked in and documented.

---

## Phase 2: Product Context And System Configuration

**User stories**: admin/product owner can configure products, versions, modules, related systems, internal GitLab bindings, and model gateway settings.

### What To Build

Implement product configuration and system configuration through schema, API, UI pages, permission checks, audit events, and tests. GitLab credentials must be represented by server-side references and never returned in plaintext.

### Acceptance Criteria

- [ ] Product, version, module, Git repository, related system, and model gateway config APIs match the documented contracts.
- [ ] Archived product versions cannot be used for new requirements or tasks.
- [ ] GitLab repository bindings support project ID/path, base URL, and credential reference without exposing secrets.
- [ ] Model gateway API keys are masked in API responses.
- [ ] Product management UI supports list, create, update, and active-only filtering workflows.
- [ ] Successful writes produce audit events.

---

## Phase 3: Requirement To Product Detail Design

**User stories**: product owner submits and approves a requirement; R&D owner creates and starts a product detail design AI task; product owner confirms the AI output.

### What To Build

Implement requirement ledger, approval/rejection, task generation, AI task lifecycle, local fallback model output, graph runtime checkpoint records, human review creation, optimistic review decisions, task detail aggregation, and audit trail.

### Acceptance Criteria

- [ ] Requirements move through draft/pending, approved, rejected, task_created, and closed states only through documented actions.
- [ ] Approved requirements can generate `product_detail_design` AI tasks with immutable requirement snapshot and product context.
- [ ] Starting a task creates a graph run and moves the task to `waiting_review` with a pending human review.
- [ ] Review approve, edit-approve, reject, and request-more-info actions enforce `human_reviews.version`.
- [ ] Unconfirmed AI output cannot advance to downstream stages.
- [ ] Requirement management and task center UI expose the full path.

---

## Phase 4: Technical Solution And Markdown Export

**User stories**: R&D owner creates a technical solution from confirmed product detail design; confirmed outputs can be exported as Markdown.

### What To Build

Implement `technical_solution` task creation and execution using confirmed upstream design snapshots, human confirmation, task detail evidence display, and Markdown export.

### Acceptance Criteria

- [ ] `technical_solution` requires a confirmed product detail design input.
- [ ] Technical solution output enters human review before completion.
- [ ] Markdown export returns `text/markdown` and contains confirmed requirement, product detail design, and technical solution sections.
- [ ] Export path is traceable by header/log `trace_id`.
- [ ] UI exposes export from task details.

---

## Phase 5: GitLab MR Input Snapshot

**User stories**: reviewer selects an authorized internal GitLab MR, previews metadata, and creates an immutable diff snapshot for later code review.

### What To Build

Implement GitLab MR preview and snapshot APIs, a mockable GitLab adapter, diff size limits, immutable snapshot records, permission checks, task-context linkage, UI flow, and audit events.

### Acceptance Criteria

- [ ] MR preview reads metadata without storing full diff.
- [ ] MR snapshot stores immutable metadata, diff summary/storage reference, size, hash, requirement, and technical solution task references.
- [ ] Snapshot creation fails clearly for missing binding, forbidden MR, missing MR, GitLab outage, and diff-too-large cases.
- [ ] Snapshot creation never writes to GitLab.
- [ ] UI requires preview before snapshot creation.

---

## Phase 6: Code Review Report Loop

**User stories**: reviewer creates a `code_review` AI task from an MR snapshot, receives a structured review report, confirms or edits it, and archives it internally.

### What To Build

Implement code review task creation, code-review executor boundary, local deterministic fallback executor, structured report schema validation, human confirmation, internal report archival, failure semantics, and no-GitLab-writeback verification.

### Acceptance Criteria

- [ ] `code_review` task creation requires an existing GitLab MR snapshot and confirmed technical solution.
- [ ] Executor output validates summary, risk level, findings, severity, file path, line/range, category, suggestion, confidence, and executor metadata.
- [ ] Reports enter pending human review before they can be archived.
- [ ] Confirmed or edited-approved reports are archived only inside AI Brain.
- [ ] No endpoint or executor path writes GitLab comments, approval state, request changes, merge state, or branches.
- [ ] Audit events cover executor invocation, report generation, review decision, and archive.

---

## Phase 7: Knowledge And Governance Loop

**User stories**: knowledge maintainer imports documents, users retrieve only authorized knowledge, task outputs become reviewable deposits, and outputs/writeback are auditable.

### What To Build

Implement knowledge document import/index status, chunk storage, permission-filtered search, knowledge deposits, mock Issue idempotent writeback, lifecycle context MVP links, subject-level audit query, and MVP placeholders for later modules.

### Acceptance Criteria

- [ ] Knowledge search enforces permission filters in the query layer and returns source references.
- [ ] Knowledge deposits can be approved or rejected through documented states.
- [ ] Mock Issue generation uses unique idempotency keys and never duplicates outputs.
- [ ] Audit events can be queried by task and by subject type/id.
- [ ] Dashboard, Bug, DevOps, insights, planning, and full lifecycle views expose honest placeholder or empty states when full later-phase data is unavailable.

---

## Review And Verification Loop

After the full MVP path is implemented, run five quality loops:

- [ ] Loop 1: self-test full backend, frontend, and compose smoke suite; review failures and fix.
- [ ] Loop 2: code review for architecture, state machines, API contracts, and schema consistency; self-test and fix.
- [ ] Loop 3: code review for security, secret handling, permission filtering, audit, and GitLab read-only boundary; self-test and fix.
- [ ] Loop 4: code review for frontend workflow, accessibility, responsive behavior, and UX clarity; browser self-test and fix.
- [ ] Loop 5: final code review for maintainability, docs/changelog alignment, test coverage, and deployment readiness; final self-test.
