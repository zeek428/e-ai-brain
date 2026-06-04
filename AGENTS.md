# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Repository Status

This checkout contains the AI Brain documentation set under [docs/](docs/) plus the current MVP implementation under [apps/api](apps/api) and [apps/web](apps/web). The backend is a FastAPI app in DB-first migration mode: `PERSISTENCE_MODE` defaults to `postgres`, non-test `memory` mode fails fast, and PostgreSQL startup uses a lightweight `PostgresRuntimeStore` repository container instead of `PersistentMemoryStore.from_repository(...)`. Plain `MemoryStore` remains a test helper only; PostgreSQL request contexts use repository-backed source rows/read models that do not inherit `MemoryStore`. Read-only caches are allowed for performance when they are derived from PostgreSQL, rebuildable, and never treated as a write source of truth. Users are managed through the `users` table, business brain read-only configuration is loaded from `brain_apps`, product configuration is written into `products`, `product_versions`, `product_modules`, `product_git_repositories`, and `related_systems`, requirement ledger data is written into `requirements` with default `rd_brain` attribution, AI task core fields are written into `ai_tasks` with inherited business brain attribution, workflow review/checkpoint state is written into `human_reviews`, `graph_runs`, and `graph_checkpoints`, GitLab MR / GitHub PR compatible review artifacts are written into `gitlab_mr_snapshots` and `code_review_reports`, knowledge operations are written into `knowledge_documents`, `knowledge_chunks`, and `knowledge_deposits`, audit events are written into `audit_events`, Bug records are written into `bugs`, GitLab daily metrics are written into `gitlab_daily_code_metrics`, Jenkins release records are written into `jenkins_release_records`, online log metrics are written into `online_log_metrics`, lifecycle context is written into `lifecycle_context_edges` and `lifecycle_risk_signals`, dashboard snapshots are written into `dashboard_metric_snapshots`, mock Issue writebacks are written into `mock_issues`, model gateway configuration and metadata logs are written into `model_gateway_configs` and `model_gateway_logs`, and AI assistant chat history is written into `assistant_conversations` and `assistant_messages`. `app_state_snapshots` is retained only as a historical migration table and is no longer a production business-state restore source or request-end write target; API middleware no longer performs global request-end `persist()` synchronization. `development_planning`, `automated_testing`, and `release_readiness` can now be created from a confirmed `technical_solution`; `post_release_analysis` can be created from a confirmed `release_readiness`. Confirmed automated-testing outputs create `ai_auto_test` Bug records from `bug_suggestions`, and confirmed post-release analysis outputs create `ai_post_release` Bug records. Always verify implementation files before assuming a module is complete.

## Source of Truth

Use the project-level documents as the active source of truth:

1. [docs/01-prd/enterprise-ai-brain/prd.md](docs/01-prd/enterprise-ai-brain/prd.md) — product scope, user stories, acceptance criteria, and rollout phases.
2. [docs/02-specs/enterprise-ai-brain/spec.md](docs/02-specs/enterprise-ai-brain/spec.md) — technical design, module boundaries, data model, state machine, cache strategy, security, and testing strategy.
3. [docs/02-specs/enterprise-ai-brain/api.md](docs/02-specs/enterprise-ai-brain/api.md) — API contracts and error semantics.
4. [docs/02-specs/enterprise-ai-brain/test-case.md](docs/02-specs/enterprise-ai-brain/test-case.md) — acceptance-test mapping and P0/P1 test cases.
5. [docs/02-specs/architecture/system-overview.md](docs/02-specs/architecture/system-overview.md) and [docs/02-specs/architecture/tech-stack.md](docs/02-specs/architecture/tech-stack.md) — concise architecture and technology summaries.

The [docs/07-deprecated/](docs/07-deprecated/) directory is a historical archive only. Do not use it as the implementation authority for new work; migrate any still-valid historical details into the project-level PRD/spec/API/test documents instead.

## Common Commands

The docs define these commands for the intended local development stack:

```bash
# Prepare local environment
cp .env.example .env

# Validate Docker Compose configuration
docker compose config
docker compose config --quiet

# Build and start the full local stack
docker compose up -d --build

# Inspect running services and logs
docker compose ps
docker compose logs api
docker compose logs postgres
docker compose logs redis

# Health checks
curl http://localhost:8000/health
docker compose exec redis redis-cli ping
docker compose exec postgres psql -U ai_brain -d ai_brain -c "select extname from pg_extension where extname in ('vector', 'pgcrypto');"

# Backend tests, once apps/api exists
cd apps/api
uv run pytest

# Run a single backend test, once tests exist
cd apps/api
uv run pytest path/to/test_file.py::test_name
```

If package scripts or app directories are added later, prefer the checked-in scripts over inferred commands and update this file.

## Testing and Commit Gate

For any change that affects frontend routes, menus, visible copy, page components, frontend service mappings, or backend API behavior that changes a rendered page, run actual web UI validation before committing. Start or restart the real web service, use the PostgreSQL-backed API runtime, open the target page in a browser, log in with the relevant role, and verify the URL/title, non-blank render, expected menu/text/table/modal/interaction, absence of stale UI, and no relevant console/runtime errors. If Umi/MFSU cache, old ports, or stale bundles prevent the page from reflecting the change, fix the running environment and repeat the browser check. Do not commit until both automated tests and the real webpage validation pass, and include the URL, role, checked page/flow, commands, and result in the final summary.

## Intended Architecture

AI Brain v1 is an enterprise AI brain platform. The initial sample application is the R&D brain (`rd_brain`), which runs the loop from requirement submission through AI-assisted analysis, human confirmation, task writeback, export, and knowledge deposit.

The planned runtime architecture is:

```text
React + TypeScript workbench based on Ant Design Pro
  -> FastAPI modular monolith
     -> PostgreSQL + pgvector
     -> Redis
     -> GBrain long-term memory / knowledge graph
     -> OpenAI-compatible model gateway
```

The backend is specified as a modular monolith with these domain boundaries:

- `auth`: local accounts, Bearer Token authentication, roles, permissions.
- `brain_app`: business brain configuration, including default `rd_brain`.
- `product_config`: products, versions, modules, and Git resource context.
- `requirement`: requirement ledger, approval, rejection, and task generation.
- `ai_task`: task lifecycle, status transitions, task detail aggregation.
- `graph_runtime`: LangGraph execution, checkpoints, interrupts, and resume.
- `review`: human confirmation, edited approval, rejection, and requests for more information.
- `knowledge`: document import, chunking, embeddings, hybrid search, permission filtering, and knowledge deposits.
- `long_memory`: GBrain-backed long-term memory, hybrid retrieval, answer synthesis, and knowledge graph traversal.
- `model_gateway`: chat and embedding calls through an OpenAI-compatible provider boundary.
- `devops_metrics`: GitLab, Jenkins, and online log metric collection by product ownership.
- `user_insights`: usage metrics and user feedback collection, attribution, aggregation, and pending-attribution handling.
- `iteration_planning`: AI iteration suggestions, evidence-chain aggregation, human decisions, and adoption tracking.
- `lifecycle_context`: full R&D lifecycle context graph, upstream/downstream tracing, and risk signals.
- `bug`: AI automated-test and manual-test bug lifecycle management.
- `dashboard`: IT team dashboard and engineering operations metric aggregation.
- `integration`: v1 mock Issue writeback with idempotency controls.
- `audit`: write-operation and high-impact AI-action audit events.
- `export`: Markdown task-solution export.

## Key Product Flow

The core flow is:

```text
create requirement
-> approve requirement
-> generate ai_task
-> start graph_run
-> retrieve knowledge context
-> optionally query GBrain long-term memory
-> call model_gateway
-> create human review checkpoints
-> resume graph after decisions
-> write mock issues, Bug records, release/readiness results, and Markdown output
-> create knowledge deposit candidates
-> update lifecycle_context edges and risk signals
-> aggregate DevOps metrics, user insights, and iteration planning suggestions
-> record audit events throughout
```

Important states from the active spec:

```text
Requirement: draft | pending_approval | approved | rejected | task_created | closed
AI task: draft | running | waiting_more_info | waiting_review | writing_back | completed | failed | cancelled
Review: pending | approved | edited_approved | rejected | requested_more_info | cancelled
```

High-impact AI steps must stop at explicit human confirmation points before continuing.

## Implementation Constraints from the Docs

- Frontend work defaults to a React + TypeScript workbench based on the Ant Design Pro template (`https://github.com/ant-design/ant-design-pro`) and Ant Design components from the project `antd` dependency. A local Ant Design checkout may be used only as reference; this project must remain independently installable and deployable.
- Long-term memory defaults to GBrain (`https://github.com/garrytan/gbrain`) as a supplementary brain layer for hybrid retrieval, answer synthesis, and knowledge graph traversal. It does not replace PostgreSQL-owned product, requirement, task, review, knowledge, or audit data.
- Backend work defaults to FastAPI + Python 3.11 and should keep the documented module boundaries rather than prematurely splitting microservices.
- LangGraph should own long-running AI workflow state, checkpointing, interruption, and resume behavior.
- Knowledge retrieval must enforce permissions in the database query layer before returning chunks.
- Model calls must go through `model_gateway`; business modules should not call provider SDKs directly.
- Model logs should record metadata such as provider, model, purpose, tokens, latency, status, and error, but not full prompts or full outputs by default.
- Mock Issue writeback must use idempotency keys to avoid duplicate outputs.
- `human_reviews.version` is specified for optimistic locking around concurrent review decisions.
- Every API response is expected to include a `trace_id`; audit event persistence is documented separately in `audit_events`.

## Documentation Maintenance

When implementation and docs diverge, update the project-level docs first, then code, then [docs/changelog.md](docs/changelog.md). New modules must update the API, data model, permission, and audit documentation. PRD acceptance criteria must remain mapped to test cases.
