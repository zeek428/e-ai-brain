# Final R&D collaboration documentation sync report

## Scope

Documentation was synchronized against source through `4623ddc13` without
changing code, tests, infrastructure, or `docs/changelog.md`.

The final contract now states:

- Ordinary API container startup executes normal additive migrations while
  explicitly excluding destructive cleanup migration 121 and large dispatch
  index migrations 125-128.
- Migration 121 remains an explicit maintenance-fenced cleanup. Migrations
  125-128 are delegated to non-test API repository schema compatibility on an
  autocommit connection, with one non-blocking advisory lock, index
  validity/readiness checks, and concurrent drop/create behavior.
- Final work-item dispatch performs a non-locking work-item identity lookup,
  then acquires row locks in canonical
  `rd_collaboration_runs FOR UPDATE -> rd_work_items FOR UPDATE` order.
- After both locks, dispatch revalidates parent ownership, parent/item status,
  reservation version and due time before seat, Runner-safety, or durable
  bundle writes. Concurrent cancel or parent suspension cannot produce
  SQLSTATE `40P01` or leave task, Runner, attempt, event, or audit artifacts.

## Documents updated

- `docs/02-specs/enterprise-ai-brain/spec.md`
- `docs/02-specs/enterprise-ai-brain/api/delivery-and-tasks.md`
- `docs/02-specs/enterprise-ai-brain/api/audit-and-errors.md`
- `docs/02-specs/enterprise-ai-brain/test-cases/requirements-and-tasks.md`
- `docs/02-specs/architecture/system-overview.md`
- `docs/05-runbooks/deployment.md`
- `docs/README.md`
- `docs/superpowers/plans/2026-07-16-requirement-driven-rd-collaboration.md`
- `docs/superpowers/specs/2026-07-16-requirement-driven-rd-collaboration-design.md`
- `docs/superpowers/plans/2026-07-19-rd-collaboration-review-remediation.md`
- `docs/superpowers/specs/2026-07-19-rd-collaboration-review-remediation-design.md`

No help-center update or screenshot was required because these changes affect
backend startup, database index installation, and internal dispatch
concurrency; they do not change a route, visible label, form, permission, or
user operation flow.

## Verification

- `git diff --check` — passed.
- Consistency searches found no remaining authoritative reference to a
  `110_requirement_driven_rd_cutover.sql` cleanup or work-item-first final
  dispatch lock order.
- Focused verification passed: `6 passed in 1.13s` for the API entrypoint,
  advisory-lock index compatibility, pre-suspended parent fence, concurrent
  dispatch/cancel lock order, and concurrent dispatch/suspend no-artifact
  regressions.
- The source lock-order commit also completed the fresh backend suite with
  `1640 passed, 4 skipped, 1 deselected`.

## Exact changelog proposal for the controller

Add the following bullet under `## [Unreleased]` / `### Changed`:

```markdown
- 加固研发协同启动迁移与最终派发锁序：普通 API 启动明确排除显式 cleanup 迁移 121 和派发大索引 125-128，四个大索引改由 autocommit repository compatibility 路径通过非阻塞 advisory lock 与 concurrent DDL 校验/创建；最终派发先无锁读取工作项父运行标识，再按 `rd_collaboration_runs -> rd_work_items` 加锁并重验归属、状态、版本和到期边界，与取消/暂停并发时不会产生 `40P01`，也不会向暂停运行写入陈旧任务、Runner、attempt、事件或审计。
```

## Delivery boundary

- Documentation-only commit: yes.
- `docs/changelog.md` modified: no.
- Push performed: no.
