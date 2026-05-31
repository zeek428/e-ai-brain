# Model Gateway Config UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the MVP AC9 frontend management surface for platform model gateway configs under System Management.

**Architecture:** The backend already owns `/api/system/model-gateway-configs` and masks API keys. Add typed web service methods, a `ModelGateway` management list page matching existing CRUD pages, and a route under `/system/model-gateway`. Keep the UI read/write path on real APIs only and never render API key plaintext from responses.

**Tech Stack:** React 19, Umi Max routes, Ant Design / ProTable, Vitest + Testing Library.

---

### Task 1: Failing Frontend Tests

**Files:**
- Modify: `apps/web/tests/App.test.tsx`

- [x] **Step 1: Add route, page, and service expectations**

Add tests that assert:
- routes include `模型网关` under system management.
- rendering the new page shows model gateway configs from `/api/system/model-gateway-configs`.
- the table shows `api_key_configured=true` as `已配置` and does not show plaintext API keys.
- create and edit modals POST/PATCH real API payloads.
- service helpers call GET/POST/PATCH/DELETE `/api/system/model-gateway-configs`.

- [x] **Step 2: Run test to verify it fails**

Run: `npm run test -- App.test.tsx`
Expected: fails because the page and service exports do not exist yet.

### Task 2: Service Layer

**Files:**
- Modify: `apps/web/src/services/aiBrain.ts`

- [x] **Step 1: Add model gateway config types and CRUD helpers**

Add `ModelGatewayConfigRecord`, payload types, and functions:
- `fetchModelGatewayConfigs`
- `createModelGatewayConfig`
- `updateModelGatewayConfig`
- `deleteModelGatewayConfig`

- [x] **Step 2: Run targeted service tests**

Run: `npm run test -- App.test.tsx`
Expected: route/page test may still fail, service test passes.

### Task 3: Management Page And Route

**Files:**
- Create: `apps/web/src/pages/ModelGateway/index.tsx`
- Modify: `apps/web/config/routes.ts`

- [x] **Step 1: Implement page following existing management page style**

Use `ManagementListPage`, `Modal`, `Form`, `Input`, `InputNumber`, `Select`, `Switch`, `Popconfirm`, and `StatusTag`.

Fields:
- name, provider, base_url, default_chat_model, default_embedding_model
- timeout_seconds, max_retries, status, is_default
- api_key only in create/edit form; leave blank on edit to keep existing key.

Table:
- name, provider, base_url, chat model, embedding model, status, default, key configured, operations.

- [x] **Step 2: Run targeted tests**

Run: `npm run test -- App.test.tsx`
Expected: all App tests pass.

### Task 4: Docs And Verification

**Files:**
- Modify: `docs/02-specs/enterprise-ai-brain/api.md`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md`
- Modify: `docs/changelog.md`

- [x] **Step 1: Document AC9 page behavior**

State that System Management includes Model Gateway Config and that the page only displays `api_key_configured`, never plaintext.

- [x] **Step 2: Run verification**

Commands:
- `npm run test`
- `npm run lint`
- `npm run typecheck`
- `npm run build`
- `uv run ruff check .`
- `uv run pytest`
- Docker sync/restart web and browser QA on `http://127.0.0.1:5173/system/model-gateway`.
