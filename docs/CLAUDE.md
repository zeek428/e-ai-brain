# CLAUDE.md

This file guides Claude Code and other AI coding agents when reading documentation for the AI Brain repository.

## Project Overview

AI Brain is an enterprise AI brain platform. The v1 sample application is the R&D brain (`rd_brain`), which turns a business requirement into full-lifecycle AI-assisted R&D tasks: product detail design, technical solution, internal GitLab MR preview and diff snapshot, code review, automated testing, release readiness, post-release analysis, Bug management, knowledge deposits, and product-level engineering operations dashboards.

## Documentation Source of Truth

Project-level documents are the source of truth for ongoing implementation and version iteration. Maintain PRD, spec, API, and test-case documents directly.

## Reading Order

1. [01-prd/enterprise-ai-brain/prd.md](01-prd/enterprise-ai-brain/prd.md) — product scope, users, stories, acceptance criteria.
2. [02-specs/enterprise-ai-brain/spec.md](02-specs/enterprise-ai-brain/spec.md) — technical design, modules, data flow, state and risks.
3. [02-specs/enterprise-ai-brain/api.md](02-specs/enterprise-ai-brain/api.md) — API contract and error handling.
4. [02-specs/enterprise-ai-brain/test-case.md](02-specs/enterprise-ai-brain/test-case.md) — test cases mapped to acceptance criteria.
5. [02-specs/architecture/system-overview.md](02-specs/architecture/system-overview.md) and [02-specs/architecture/tech-stack.md](02-specs/architecture/tech-stack.md) — concise architecture summaries.

## Current Technical Direction

| Area | Direction |
|------|-----------|
| Frontend | React + TypeScript workbench based on Ant Design Pro; UI components from Ant Design; routes for IT team dashboard, product management, requirements, task center, Bug management, engineering operations, user insights/iteration planning, knowledge center, and audit/runtime |
| Backend | FastAPI + Python modular monolith with product_config, requirement, ai_task, graph_runtime, review, knowledge, long_memory, model_gateway, devops_metrics, user_insights, iteration_planning, lifecycle_context, bug, dashboard, integration, audit, and export modules |
| AI orchestration | LangGraph with checkpoints and human interrupts |
| Database | PostgreSQL + pgvector |
| Long-term memory | GBrain hybrid retrieval + knowledge graph |
| Cache/queue | Redis |
| Model access | OpenAI-compatible API through a model gateway |
| v1 deployment | Docker Compose |

## Documentation Rules

- If implementation and docs diverge, update docs first, then code.
- New modules must update API, data model, permission, and audit design.
- PRD acceptance criteria must map to test cases.
- High-impact AI actions must include explicit human confirmation points.
- Frontend implementation defaults to an Ant Design Pro based React + TypeScript workbench, using `https://github.com/ant-design/ant-design-pro` as the project template and Ant Design components from the project `antd` dependency. The local `/Users/zeek/source/ant-design` checkout may be used for reference only; `ai-brain` must remain independently installable, buildable, and deployable.
- Long-term memory defaults to GBrain (`https://github.com/garrytan/gbrain`) as a supplementary brain layer for hybrid retrieval, answer synthesis, and knowledge graph traversal. It does not replace the project PostgreSQL business database or permission model.
- Keep templates under `_template/`; create project documents in feature folders such as `enterprise-ai-brain/`.

## Useful Commands

```bash
# Inspect project-level docs
find docs/01-prd docs/02-specs docs/03-guides docs/05-runbooks docs/06-standards -maxdepth 2 -type f | sort

# Validate Docker Compose configuration
docker compose config

# Start local development stack
docker compose up -d --build

# Backend tests
cd apps/api
uv run pytest
```

---
Status: Approved
Owner: Project Maintainers
Created: 2026-05-27
Updated: 2026-05-29
