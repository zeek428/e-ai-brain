# Plugin Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build plugin management for third-party HTTP/MCP integrations and allow scheduled jobs to invoke configured plugin actions with auditable run snapshots.

**Architecture:** Add a new `integration_plugin` backend boundary alongside scheduled jobs. Plugins define protocol and lifecycle, connections hold endpoint/auth references, actions define executable HTTP/MCP calls and schemas, invocation logs record each run; scheduled jobs reference plugin actions for orchestration while AI Skills only consume returned data semantically.

**Tech Stack:** FastAPI, Pydantic, PostgreSQL JSONB migrations, repository-backed `PostgresRuntimeStore`, React + TypeScript + Ant Design Pro, pytest, Vitest.

---

## File Structure

- Create `apps/api/app/db/migrations/036_integration_plugins.sql`: plugin tables, scheduled job extension columns, RBAC/menu seed.
- Create `apps/api/app/core/repositories/plugins.py`: SQL read/write repository for plugins, connections, actions, invocation logs.
- Create `apps/api/app/services/plugins.py`: validation, public response shaping, secret masking, action invocation and audit.
- Create `apps/api/app/api/routers/plugins.py`: `/api/system/plugins`, `/api/system/plugin-connections`, `/api/system/plugin-actions`, `/api/system/plugin-invocation-logs`.
- Modify `apps/api/app/core/store.py`: add in-memory dictionaries for plugin entities.
- Modify `apps/api/app/core/persistence_repositories.py` and `apps/api/app/core/persistence.py`: install and expose plugin repository methods.
- Modify `apps/api/app/services/scheduled_jobs.py`: validate plugin references, snapshot plugin config, invoke plugin action during runs, link invocation logs.
- Modify `apps/api/app/api/routers/scheduled_jobs.py`: add scheduled job plugin fields to request models.
- Modify `apps/api/app/core/repositories/scheduled_ai_jobs.py`: persist/read scheduled job plugin fields and run plugin snapshots.
- Modify `apps/api/app/main.py`: include plugin router.
- Modify `apps/api/app/core/roles.py` and `apps/api/app/core/repositories/authorization.py`: add admin permission/menu fallback.
- Create `apps/api/tests/test_plugin_management.py`: backend contract tests for CRUD, masking, invocation, scheduled job integration.
- Modify `apps/web/src/services/aiBrain.ts`: add plugin types and API clients; extend scheduled job types.
- Create `apps/web/src/pages/Plugins/index.tsx`: plugin management UI.
- Modify `apps/web/src/pages/ScheduledJobs/index.tsx`: allow plugin action selection and show invocation log link/summary.
- Modify `apps/web/config/routes.ts`: add `/system/plugins`.
- Modify `docs/01-prd/enterprise-ai-brain/prd.md`, `docs/02-specs/enterprise-ai-brain/spec.md`, `docs/02-specs/enterprise-ai-brain/api.md`, `docs/02-specs/enterprise-ai-brain/test-case.md`, `docs/changelog.md`: document the design and test scope.

## Data Contract

`integration_plugins`:
- `id`, `code`, `name`, `description`, `protocol`, `category`, `risk_level`, `status`, `created_by`, `created_at`, `updated_at`.
- `protocol` values: `http`, `mcp_http`, `mcp_stdio`.
- Phase 1 allows `http` and `mcp_http` invocation. `mcp_stdio` can be configured but returns `PLUGIN_PROTOCOL_UNSUPPORTED` when invoked.

`plugin_connections`:
- `id`, `plugin_id`, `name`, `environment`, `endpoint_url`, `auth_type`, `auth_config`, `timeout_seconds`, `max_retries`, `status`, timestamps.
- `auth_config` is returned masked. No plaintext secret fields are exposed.

`plugin_actions`:
- `id`, `plugin_id`, `connection_id`, `code`, `name`, `description`, `action_type`, `input_schema`, `output_schema`, `request_config`, `result_mapping`, `requires_human_review`, `status`, timestamps.
- `action_type` values: `http_request`, `mcp_tool`.

`plugin_invocation_logs`:
- `id`, `plugin_id`, `connection_id`, `action_id`, `scheduled_job_id`, `scheduled_job_run_id`, `trigger_type`, `status`, `request_summary`, `response_summary`, `latency_ms`, `error_code`, `error_message`, `trace_id`, `created_by`, timestamps.

Scheduled jobs:
- Add `plugin_action_id`, `plugin_connection_id`, `plugin_input_mapping`, `plugin_output_mapping`.
- Scheduled job runs add `resolved_plugin_snapshot`, `plugin_invocation_log_id`.

## Tasks

### Task 1: Backend Contract Tests

**Files:**
- Create: `apps/api/tests/test_plugin_management.py`

- [ ] **Step 1: Write failing tests for plugin CRUD and masking**

Add tests that:
- reviewer cannot create plugin.
- admin creates plugin, connection and action.
- connection response masks `auth_config.secret_ref`.
- audit events include `plugin.created`, `plugin_connection.created`, `plugin_action.created`.

- [ ] **Step 2: Write failing test for scheduled job plugin invocation**

Add a test that:
- creates HTTP plugin action with `request_config.mock_response_json`.
- creates deterministic scheduled job with `plugin_action_id`.
- runs the job.
- asserts `resolved_plugin_snapshot`, `plugin_invocation_log_id`, `result_summary.plugin.status == "succeeded"` and one invocation log exists.

- [ ] **Step 3: Run focused tests to verify RED**

Run:

```bash
cd apps/api
uv run pytest tests/test_plugin_management.py -q
```

Expected: fails because plugin routes and scheduled job fields do not exist.

### Task 2: Database and Repository

**Files:**
- Create: `apps/api/app/db/migrations/036_integration_plugins.sql`
- Create: `apps/api/app/core/repositories/plugins.py`
- Modify: `apps/api/app/core/persistence_repositories.py`
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/core/store.py`

- [ ] **Step 1: Add migration**

Create tables and indexes listed in the Data Contract. Add RBAC seed:
- permission `system.plugins.manage`
- menu `system.plugins` at `/system/plugins`
- admin role permission/menu grant.

- [ ] **Step 2: Add repository**

Implement repository methods:
- `list_plugins(status=None, protocol=None)`
- `save_plugin_record(plugin, audit_event=None)`
- `list_plugin_connections(plugin_id=None, status=None)`
- `save_plugin_connection_record(connection, audit_event=None)`
- `list_plugin_actions(plugin_id=None, status=None)`
- `save_plugin_action_record(action, audit_event=None)`
- `list_plugin_invocation_logs(action_id=None, scheduled_job_id=None, scheduled_job_run_id=None, status=None)`
- `save_plugin_invocation_log_record(log, audit_event=None)`

- [ ] **Step 3: Wire repository into runtime**

Expose those methods through `PostgresSnapshotRepository`, install the repository in `install_snapshot_repositories`, and add in-memory collections to `MemoryStore.reset`.

### Task 3: Plugin Service and Router

**Files:**
- Create: `apps/api/app/services/plugins.py`
- Create: `apps/api/app/api/routers/plugins.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/core/roles.py`
- Modify: `apps/api/app/core/repositories/authorization.py`

- [ ] **Step 1: Implement validation and public masking**

Validate enum values, active references and non-blank fields. Return `auth_config` with secret-like values replaced by `"***"`.

- [ ] **Step 2: Implement CRUD endpoints**

Add admin-managed endpoints for plugins, connections and actions. Each create/update writes an audit event and persists through the repository method.

- [ ] **Step 3: Implement action invocation**

`POST /api/system/plugin-actions/{action_id}/invoke` resolves plugin, connection and action. For Phase 1:
- if `request_config.mock_response_json` exists, return it without network.
- if `protocol=http`, build an HTTP request from method/path/query/body and call endpoint.
- if `protocol=mcp_http`, send a JSON-RPC style tools call using `request_config.tool_name`.
- if `protocol=mcp_stdio`, fail with `PLUGIN_PROTOCOL_UNSUPPORTED`.

Always write a `plugin_invocation_logs` row and audit event.

### Task 4: Scheduled Job Integration

**Files:**
- Modify: `apps/api/app/api/routers/scheduled_jobs.py`
- Modify: `apps/api/app/services/scheduled_jobs.py`
- Modify: `apps/api/app/core/repositories/scheduled_ai_jobs.py`
- Modify: `apps/api/app/db/migrations/036_integration_plugins.sql`

- [ ] **Step 1: Add scheduled job request fields**

Add optional `plugin_action_id`, `plugin_connection_id`, `plugin_input_mapping`, `plugin_output_mapping` to create/patch request models.

- [ ] **Step 2: Validate active plugin action references**

During create/patch, if `plugin_action_id` is present, require an active action, plugin and connection. `plugin_connection_id` overrides the action default connection when active.

- [ ] **Step 3: Invoke plugin during run**

During `run_scheduled_job_response`, resolve plugin snapshot and invoke action before AI-specific handlers. Include invocation log id and plugin result in `result_summary`.

- [ ] **Step 4: Persist new scheduled job/run fields**

Update SQL select/upsert and row mapping for scheduled jobs and runs.

### Task 5: Frontend UI

**Files:**
- Modify: `apps/web/src/services/aiBrain.ts`
- Create: `apps/web/src/pages/Plugins/index.tsx`
- Modify: `apps/web/src/pages/ScheduledJobs/index.tsx`
- Modify: `apps/web/config/routes.ts`

- [ ] **Step 1: Add service clients**

Add plugin record types and clients for list/create/update/invoke/logs. Extend scheduled job types with plugin fields.

- [ ] **Step 2: Build plugin management page**

Create tabs for Plugins, Connections, Actions and Invocation Logs. Provide create modals for first-stage configuration and a run button on actions.

- [ ] **Step 3: Extend scheduled jobs page**

Load plugin actions, allow selecting `plugin_action_id`, show plugin action column and run records' `plugin_invocation_log_id`.

### Task 6: Documentation and Verification

**Files:**
- Modify active docs listed above.

- [ ] **Step 1: Update active source-of-truth docs**

Document plugin boundaries, protocol support, data model, APIs, permission/audit requirements and scheduled job integration.

- [ ] **Step 2: Run backend verification**

Run:

```bash
cd apps/api
uv run pytest tests/test_plugin_management.py tests/test_scheduled_ai_jobs.py -q
```

Expected: all selected tests pass.

- [ ] **Step 3: Run frontend verification**

Run:

```bash
cd apps/web
npm test -- --run
npm run build
```

Expected: tests and build pass.

- [ ] **Step 4: Browser smoke**

Start the API and web app with PostgreSQL-backed runtime, log in as admin, open `/system/plugins` and `/system/scheduled-jobs`, verify non-blank render and no relevant console errors.

## Self-Review

- Spec coverage: covers plugin config, connection config, HTTP/MCP protocol modeling, scheduled task invocation, snapshots, logs, RBAC and audit.
- Deliberate Phase 1 boundary: `mcp_stdio` is configurable but not executable until command isolation is designed.
- Type consistency: API fields use snake_case to match existing backend/frontend service patterns.
- Security: secrets are stored as references/config metadata and masked in responses; invocation logs keep summaries only.
