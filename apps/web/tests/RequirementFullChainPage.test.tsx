import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { cleanup, render, screen, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import RequirementFullChainPage from '../src/pages/RequirementFullChain';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.history.pushState({}, '', '/');
  window.localStorage.clear();
  void message.destroy();
  notification.destroy();
  Modal.destroyAll();
});

describe('RequirementFullChainPage', () => {
  it('opens a requirement full-chain detail page directly from the route', async () => {
    const routes = readFileSync(join(__dirname, '..', 'config', 'routes.ts'), 'utf8');
    expect(routes).toContain("path: '/delivery/requirements/:requirementId/full-chain'");
    expect(routes).toContain("path: '/delivery/full-chain'");
    expect(routes).toContain("component: './RequirementFullChain'");

    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path === '/api/requirements/requirement_084/full-chain') {
        return jsonResponse({
          data: {
            ai_tasks: [
              {
                created_at: '2026-06-04T08:00:00+00:00',
                id: 'task_design',
                requirement_id: 'requirement_084',
                status: 'completed',
                task_type: 'product_detail_design',
                title: '产品详细设计：AI 助手历史记录',
              },
            ],
            bugs: [
              {
                created_at: '2026-06-04T11:00:00+00:00',
                id: 'bug_history',
                severity: 'critical',
                status: 'open',
                title: '聊天记录未按用户隔离',
              },
            ],
            audit_events: [
              {
                actor_id: 'user_admin',
                created_at: '2026-06-04T08:21:00+00:00',
                event_type: 'review.submitted',
                id: 'audit_review_submitted',
                subject_id: 'review_design',
                subject_type: 'human_review',
              },
            ],
            branch_configs: [
              {
                base_branch: 'main',
                branch_status: 'active',
                creation_source: 'manual',
                id: 'version_branch_history',
                product_id: 'product_ai_brain',
                repository_id: 'repo_ai_brain_web',
                repository_name: 'AI Brain Web',
                repository_path: 'zeek428/e-ai-brain',
                repository_provider: 'github',
                version_id: 'version_assistant_history',
                working_branch: 'feature/assistant-history',
              },
            ],
            code_review_reports: [
              {
                archived_at: '2026-06-04T10:00:00+00:00',
                id: 'report_history',
                risk_level: 'medium',
                status: 'confirmed',
                summary: 'Review 结论：补充用户级隔离测试。',
              },
            ],
            code_inspection_reports: [
              {
                branch: 'main',
                created_at: '2026-06-04T10:10:00+00:00',
                finding_count: 2,
                id: 'code_inspection_history',
                risk_level: 'high',
                severe_finding_count: 1,
                status: 'completed',
                summary: '代码巡检发现历史记录隔离风险。',
              },
            ],
            execution_traces: [
              {
                duration_ms: 6300,
                failed_node_count: 1,
                id: 'scheduled_job_run_history_trace',
                node_count: 5,
                root_id: 'scheduled_job_run_history_trace',
                root_type: 'scheduled_job_run',
                running_node_count: 0,
                started_at: '2026-06-04T10:15:00+00:00',
                status: 'failed',
                summary: '代码巡检运行失败',
                title: '定时作业运行 scheduled_job_run_history_trace',
                updated_at: '2026-06-04T10:16:00+00:00',
              },
            ],
            git_snapshots: [
              {
                changed_files_summary: [{ additions: 6, deletions: 1, path: 'apps/api/app/main.py' }],
                created_at: '2026-06-04T09:30:00+00:00',
                diff_file_tree: [{ additions: 6, deletions: 1, file_count: 1, path: 'apps/api' }],
                id: 'snapshot_pr_12',
                mr_iid: 12,
                review_checklist: ['确认用户级历史记录隔离测试覆盖'],
                risk_summary: {
                  file_count: 1,
                  largest_file: {
                    additions: 6,
                    deletions: 1,
                    line_count: 7,
                    path: 'apps/api/app/main.py',
                  },
                  risk_level: 'medium',
                  total_additions: 6,
                  total_changed_lines: 7,
                  total_deletions: 1,
                },
              },
            ],
            iteration_version: {
              code: '2026-06-assistant-history',
              id: 'version_assistant_history',
              name: '2026-06 AI 助手历史记录迭代',
              status: 'testing',
            },
            jenkins_releases: [],
            knowledge_deposits: [
              {
                created_at: '2026-06-04T10:30:00+00:00',
                id: 'deposit_history',
                status: 'pending',
                title: 'AI 助手历史记录 知识沉淀',
              },
            ],
            product: { code: 'AI-BRAIN', id: 'product_ai_brain', name: 'AI Brain' },
            requirement: {
              created_at: '2026-06-04T07:41:00+00:00',
              id: 'requirement_084',
              product_id: 'product_ai_brain',
              status: 'testing',
              title: 'AI 助手历史记录',
              version_id: 'version_assistant_history',
            },
            reviews: [
              {
                ai_task_id: 'task_design',
                created_at: '2026-06-04T08:20:00+00:00',
                id: 'review_design',
                status: 'approved',
              },
            ],
            status: 'available',
            summary: {
              ai_tasks: 1,
              audit_events: 1,
              branch_configs: 1,
              bugs: 1,
              code_inspection_reports: 1,
              code_review_reports: 1,
              execution_traces: 1,
              git_snapshots: 1,
              jenkins_releases: 0,
              knowledge_deposits: 1,
              reviews: 1,
              timeline_events: 6,
            },
            timeline: [
              {
                occurred_at: '2026-06-04T07:41:00+00:00',
                status: 'testing',
                subject_id: 'requirement_084',
                title: '需求：AI 助手历史记录',
                type: 'requirement',
              },
              {
                occurred_at: '2026-06-04T08:00:00+00:00',
                status: 'completed',
                subject_id: 'task_design',
                title: 'AI 任务：产品详细设计：AI 助手历史记录',
                type: 'ai_task',
              },
              {
                occurred_at: '2026-06-04T08:21:00+00:00',
                status: 'review.submitted',
                subject_id: 'audit_review_submitted',
                title: '审计：review.submitted · user_admin',
                type: 'audit_event',
              },
              {
                occurred_at: '2026-06-04T09:00:00+00:00',
                status: 'active',
                subject_id: 'version_branch_history',
                title: '代码分支：feature/assistant-history',
                type: 'branch_config',
              },
              {
                occurred_at: '2026-06-04T10:10:00+00:00',
                status: 'completed',
                subject_id: 'code_inspection_history',
                title: '代码巡检：代码巡检发现历史记录隔离风险。',
                type: 'code_inspection_report',
              },
              {
                occurred_at: '2026-06-04T10:15:00+00:00',
                status: 'failed',
                subject_id: 'scheduled_job_run_history_trace',
                title: '执行诊断：定时作业运行 scheduled_job_run_history_trace',
                type: 'execution_trace',
              },
            ],
          },
        });
      }
      if (path.includes('version_id=version_assistant_history') || path.includes('page_size=100')) {
        return jsonResponse({
          data: {
            items: [
              {
                content: '按用户级别保存 AI 助手会话。',
                created_at: '2026-06-04T07:41:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_084',
                priority: 'P0',
                product_code: 'AI-BRAIN',
                product_id: 'product_ai_brain',
                product_name: 'AI Brain',
                status: 'testing',
                title: 'AI 助手历史记录',
                version_id: 'version_assistant_history',
                version_name: '2026-06 AI 助手历史记录迭代',
              },
              {
                content: '补充消息引用。',
                created_at: '2026-06-04T07:20:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_082',
                priority: 'P1',
                product_code: 'AI-BRAIN',
                product_id: 'product_ai_brain',
                product_name: 'AI Brain',
                status: 'ready_for_release',
                title: 'AI 助手消息引用',
                version_id: 'version_assistant_history',
                version_name: '2026-06 AI 助手历史记录迭代',
              },
            ],
            total: 2,
          },
        });
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.history.pushState({}, '', '/delivery/requirements/requirement_084/full-chain');
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<RequirementFullChainPage />);

    expect(await screen.findByRole('heading', { name: '需求全链路详情' })).toBeInTheDocument();
    expect(await screen.findByText('需求：AI 助手历史记录')).toBeInTheDocument();
    const stageProgress = screen.getByLabelText('全链路阶段进度');
    expect(stageProgress).toBeInTheDocument();
    expect(within(stageProgress).getByRole('list', { name: '阶段进度清单' })).toBeInTheDocument();
    const stageDetails = screen.getByLabelText('全链路阶段明细');
    expect(within(stageDetails).getByText('阶段明细')).toBeInTheDocument();
    expect(within(stageDetails).getByRole('link', { name: '查看代码评审 report_history' })).toHaveAttribute(
      'href',
      '/delivery/rd-tasks?code_review_report_id=report_history',
    );
    expect(within(stageDetails).getByRole('link', { name: '查看代码巡检 code_inspection_history' })).toHaveAttribute(
      'href',
      '/governance/code-inspections?source_id=code_inspection_history',
    );
    expect(
      within(stageDetails).getByRole('link', { name: '查看执行诊断 scheduled_job_run_history_trace' }),
    ).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=scheduled_job_run_history_trace&source_type=scheduled_job_run',
    );
    expect(within(stageDetails).getByRole('link', { name: '查看分支 version_branch_history' })).toHaveAttribute(
      'href',
      '/delivery/versions?branch_config_id=version_branch_history&version_id=version_assistant_history',
    );
    expect(within(stageDetails).getByRole('link', { name: '查看审计 audit_review_submitted' })).toHaveAttribute(
      'href',
      '/governance/audit?audit_id=audit_review_submitted',
    );
    const versionComparison = await screen.findByLabelText('版本内需求对比');
    await within(versionComparison).findByText('当前版本共 2 条需求，当前需求 requirement_084');
    expect(within(versionComparison).getByText('AI 助手消息引用')).toBeInTheDocument();
    expect(screen.getByText('PR/MR 证据')).toBeInTheDocument();
    expect(screen.getByText('确认用户级历史记录隔离测试覆盖')).toBeInTheDocument();
    expect(screen.getAllByText('代码分支').length).toBeGreaterThan(0);
    expect(screen.getAllByText('执行诊断').length).toBeGreaterThan(0);
    expect(screen.getAllByText('审计事件').length).toBeGreaterThan(0);
    expect(screen.getByRole('link', { name: '返回需求管理' })).toHaveAttribute('href', '/delivery/requirements');
    expect(fetchMock.mock.calls.map(([path]) => path)).toContain('/api/requirements/requirement_084/full-chain');
    expect(fetchMock.mock.calls.map(([path]) => path)).toContain(
      '/api/requirements?version_id=version_assistant_history&page=1&page_size=100&sort_by=created_at&sort_order=desc',
    );
  });

  it('opens a requirement full-chain detail page from a lifecycle subject route', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (
        path ===
        '/api/lifecycle/full-chain?subject_id=bug_history&subject_type=bug'
      ) {
        return jsonResponse({
          data: {
            ai_tasks: [],
            anchor: {
              resolved_requirement_id: 'requirement_084',
              subject_id: 'bug_history',
              subject_type: 'bug',
            },
            bugs: [
              {
                created_at: '2026-06-04T11:00:00+00:00',
                id: 'bug_history',
                severity: 'critical',
                status: 'open',
                title: '聊天记录未按用户隔离',
              },
            ],
            audit_events: [],
            branch_configs: [],
            code_inspection_reports: [],
            code_review_reports: [],
            git_snapshots: [],
            iteration_version: null,
            jenkins_releases: [],
            knowledge_deposits: [],
            product: { code: 'AI-BRAIN', id: 'product_ai_brain', name: 'AI Brain' },
            requirement: {
              created_at: '2026-06-04T07:41:00+00:00',
              id: 'requirement_084',
              product_id: 'product_ai_brain',
              status: 'testing',
              title: 'AI 助手历史记录',
            },
            reviews: [],
            status: 'available',
            summary: {
              ai_tasks: 0,
              audit_events: 0,
              branch_configs: 0,
              bugs: 1,
              code_inspection_reports: 0,
              code_review_reports: 0,
              git_snapshots: 0,
              jenkins_releases: 0,
              knowledge_deposits: 0,
              reviews: 0,
              timeline_events: 2,
            },
            timeline: [
              {
                occurred_at: '2026-06-04T07:41:00+00:00',
                status: 'testing',
                subject_id: 'requirement_084',
                title: '需求：AI 助手历史记录',
                type: 'requirement',
              },
              {
                occurred_at: '2026-06-04T11:00:00+00:00',
                status: 'open',
                subject_id: 'bug_history',
                title: 'Bug：聊天记录未按用户隔离',
                type: 'bug',
              },
            ],
          },
        });
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.history.pushState(
      {},
      '',
      '/delivery/full-chain?subject_type=bug&subject_id=bug_history',
    );
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<RequirementFullChainPage />);

    expect(await screen.findByRole('heading', { name: '需求全链路详情' })).toBeInTheDocument();
    expect(await screen.findByText('需求：AI 助手历史记录')).toBeInTheDocument();
    expect(await screen.findByText('入口主体：Bug · bug_history')).toBeInTheDocument();
    expect(screen.getByText('已解析需求 requirement_084')).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path]) => path)).toContain(
      '/api/lifecycle/full-chain?subject_id=bug_history&subject_type=bug',
    );
  });
});
