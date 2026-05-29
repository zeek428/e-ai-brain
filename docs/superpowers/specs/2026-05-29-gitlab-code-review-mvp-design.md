# GitLab Code Review MVP Design

## Context

AI Brain v1 currently defines the MVP as a core loop from requirement approval to product detail design, technical solution, human confirmation, mock issue output, Markdown export, knowledge deposit, and audit. Code review and automated testing are currently documented as later v1.1研发任务扩展 capabilities.

The updated first-phase goal is to bring GitLab-based code review into v1 MVP while keeping automated testing in a later phase. The product should support an auditable AI review loop for internal GitLab Merge Requests without writing comments or state changes back to GitLab in the first phase.

## Scope

### In Scope for v1 MVP

- Internal GitLab Merge Request code review as a `code_review` AI task.
- Pulling MR metadata and diff through the internal GitLab API.
- Creating an immutable review input snapshot for each run.
- Invoking a pluggable code-review executor.
- Default executor: Claude Code `code-review` skill.
- Generating a structured review report.
- Sending the report through human confirmation.
- Archiving the confirmed report, confirmation decision, and audit events inside AI Brain.

### Out of Scope for v1 MVP

- Automated testing tasks.
- AI automated-test Bug suggestions.
- Full Bug assignment, fixing, verification, and closure lifecycle.
- Writing comments, approvals, or request-changes decisions back to GitLab.
- Automatic merge, branch mutation, or CI/CD actions.
- Branch-to-branch diff review outside a Merge Request.
- Manual diff upload as the primary path.

## Product Boundary

The v1 MVP becomes a minimum研发闭环:

```text
Requirement approval
→ product detail design
→ technical solution
→ GitLab MR code review
→ human confirmation
→ internal report archive
→ audit trail
```

The business value is that a研发负责人 can connect a confirmed requirement and technical solution to a real internal GitLab MR diff, receive an AI-generated review report, and make an explicit human decision before the report becomes part of the task record.

## User Flow

1. A product owner or研发负责人 completes requirement approval, product detail design confirmation, and technical solution confirmation.
2. A研发负责人 creates a `code_review` task in the task center.
3. The user selects product, version, module, internal GitLab project, and Merge Request.
4. The system reads MR metadata and diff through the internal GitLab API.
5. The system stores an immutable MR review snapshot.
6. `graph_runtime` starts the code review node.
7. The pluggable code-review executor receives MR diff, requirement snapshot, technical solution, product context, and relevant project standards.
8. The default executor calls Claude Code `code-review` skill and returns a structured report.
9. The report enters a `human_reviews` confirmation point.
10. The reviewer can approve, edit-approve, reject for rerun, or request more information.
11. After confirmation, AI Brain archives the report and decision and writes audit events.
12. The first phase does not write back to GitLab.

## Module Boundaries

| Module / capability | Responsibility |
|---------------------|----------------|
| `product_config` | Maintain internal GitLab project/repository binding and credential reference. |
| GitLab integration capability | Pull MR metadata and diff from internal GitLab and produce a stable snapshot. The implementation may live in `devops_metrics` or a later dedicated module. |
| `ai_task` | Manage `code_review` task creation, state, task type, input snapshot, and result visibility. |
| `graph_runtime` | Orchestrate the code review node, executor invocation, failure state, and human interrupt. |
| `code_review_executor` | Pluggable executor abstraction. v1 MVP default adapter invokes Claude Code `code-review` skill. |
| `review` | Reuse human review confirmation, edited approval, rejection, more-info, and optimistic locking. |
| `audit` | Record GitLab pull, executor invocation, report generation, human decision, and report archive. |

## Data Design

Product Git resource metadata should support internal GitLab binding:

- GitLab base URL.
- Project ID or project path.
- Default branch.
- Credential reference.
- Enabled/archived status.

The code review task input snapshot should include:

- Product, version, module, and requirement references.
- Technical solution reference or snapshot.
- GitLab project ID/path.
- MR IID.
- MR title, author, source branch, target branch.
- Commit SHA or diff refs used for the review.
- Changed files summary.
- Diff content or diff storage reference.
- GitLab web URL.
- Snapshot creation time.

The review report should include:

- Summary.
- Overall risk level.
- Findings list.
- Finding severity.
- Finding category.
- File path and line/range when available.
- Explanation.
- Suggested fix.
- Confidence.
- Executor metadata: executor type, skill name/version when available, model, trace ID, token/latency metadata when available.

## API Impact

- Product Git resource APIs need GitLab binding fields and must never return credentials in plaintext.
- AI task creation must allow `task_type = code_review` in v1 MVP when a valid GitLab MR reference is provided.
- A MR preview endpoint is optional but recommended: given a product Git resource and MR IID, return title, author, branches, changed file count, and target commit/diff refs for user confirmation.
- AI task detail must return the MR snapshot, executor metadata, structured review report, and pending human review state.
- No GitLab comment/writeback API is exposed in v1 MVP.

## State and Confirmation

`code_review` follows the existing AI task lifecycle:

```text
draft → running → waiting_review → running/writing_back → completed
running → failed
waiting_review → waiting_more_info → draft → running
```

For v1 MVP, `writing_back` means internal AI Brain report archive only. It does not write comments, approvals, or state changes to GitLab.

## Error Handling

- Missing GitLab project binding: fail fast with a clear configuration error.
- MR not found: task remains failed or waiting for corrected input.
- Permission denied: fail with a permission-specific error and audit event.
- GitLab API timeout or rate limit: mark retryable when safe.
- Diff too large: fail with guidance to split the MR or reduce scope; do not silently truncate.
- Executor failure: record executor type, error code, trace ID, failed stage, and retryability.
- Review rejection: allow rerun with the same snapshot or a newly pulled snapshot, explicitly recorded.

## Security

- GitLab tokens/API keys are stored as credential references or encrypted secrets.
- API responses show only masked credential metadata.
- Users can only review MRs from product Git resources they are authorized to access.
- Executor input includes only MR diff, requirement/solution summary, product context, and relevant standards.
- Executor input must not include GitLab credentials, unrelated repository content, or unnecessary user-private data.
- GitLab pull, executor invocation, report generation, report confirmation, and archive are audited.

## Acceptance Criteria Changes

- v1 MVP scope includes internal GitLab MR Code Review.
- `code_review` moves from v1.1 first-delivery scope into v1 MVP.
- Automated testing stays in v1.1.
- AC3a should include product detail design, technical solution, and code review report human confirmation.
- AC3b should no longer be the first delivery point for code review; it should cover automated testing and any remaining later研发扩展 tasks.
- Task center acceptance should include creating, running, viewing, confirming, and archiving code review tasks.
- New MVP test coverage should verify:
  - product GitLab binding;
  - MR preview or pull;
  - MR diff snapshot creation;
  - pluggable executor invocation using the default code-review skill adapter;
  - structured report generation;
  - human confirmation;
  - internal report archive;
  - audit event traceability.

## Testing Strategy

Unit tests:

- GitLab MR input validation.
- Diff size and file count limits.
- Review report schema validation.
- `code_review` task state transitions.
- Credential masking.
- Permission checks.

Integration tests:

- Product GitLab binding.
- MR preview/pull through GitLab adapter.
- `code_review` AI task creation.
- Executor adapter invocation.
- Report persistence.
- Human confirmation.
- Audit events.

E2E/P0 path:

```text
Configure GitLab project
→ select MR
→ pull diff snapshot
→ create/run code_review task
→ generate report
→ human approve or edit-approve
→ complete task
→ view archived report
→ verify audit trail
```

Exception tests:

- GitLab API failure.
- Permission denied.
- MR not found.
- Diff too large.
- Executor failure.
- Human review version conflict.

## Documentation Update Targets

After this design is approved for implementation planning, update:

- `docs/01-prd/enterprise-ai-brain/prd.md`
- `docs/02-specs/enterprise-ai-brain/spec.md`
- `docs/02-specs/enterprise-ai-brain/api.md`
- `docs/02-specs/enterprise-ai-brain/test-case.md`
- `docs/02-specs/architecture/system-overview.md`
- `docs/02-specs/architecture/tech-stack.md`
- `docs/changelog.md`
