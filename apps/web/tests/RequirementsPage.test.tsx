import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import RequirementsPage from '../src/pages/Requirements';

afterEach(() => {
  Modal.destroyAll();
  message.destroy();
  notification.destroy();
  cleanup();
  window.localStorage.clear();
  window.history.pushState({}, '', '/');
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('RequirementsPage', () => {
  it('batch schedules selected requirements from the requirements page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path.startsWith('/api/products?active_only=true')) {
        return jsonResponse({
          data: {
            items: [{ code: 'API-PRODUCT', id: 'product_api', name: '接口产品', status: 'active' }],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-06',
                id: 'version_target',
                name: '2026-06',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'planning',
              },
              {
                code: 'archived',
                id: 'version_archived',
                name: '归档版本',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'archived',
              },
            ],
            total: 2,
          },
        });
      }
      if ((path === '/api/requirements' || path.startsWith('/api/requirements?')) && method === 'GET') {
        const isVersionFiltered = path.includes('version=2026-05');
        const items = [
          {
            content: '归集需求一内容',
            created_at: '2026-06-04T08:00:00+00:00',
            created_by: 'user_admin',
            id: 'requirement_pool',
            priority: 'P1',
            product_code: 'API-PRODUCT',
            product_id: 'product_api',
            product_name: '接口产品',
            status: 'approved',
            title: '归集需求一',
          },
          {
            content: '归集需求二内容',
            created_at: '2026-06-04T08:10:00+00:00',
            created_by: 'user_admin',
            id: 'requirement_planned',
            priority: 'P1',
            product_code: 'API-PRODUCT',
            product_id: 'product_api',
            product_name: '接口产品',
            status: 'planned',
            title: '归集需求二',
            version_id: 'version_old',
            version_name: '2026-05',
          },
        ];
        return jsonResponse({
          data: {
            items: isVersionFiltered ? items.slice(1) : items,
            total: isVersionFiltered ? 1 : 2,
          },
        });
      }
      if (path === '/api/requirements/batch-schedule' && method === 'POST') {
        return jsonResponse({
          data: {
            batch_id: 'requirement_batch_001',
            product_id: 'product_api',
            skipped: [],
            skipped_count: 0,
            updated: [],
            updated_count: 2,
            version_id: 'version_target',
          },
        });
      }
      if (path === '/api/requirements/batch-assign-owner' && method === 'POST') {
        return jsonResponse({
          data: {
            assignee: 'rd_owner@example.com',
            batch_id: 'requirement_owner_batch_001',
            skipped: [],
            skipped_count: 0,
            updated: [],
            updated_count: 2,
          },
        });
      }
      if (path === '/api/requirements/batch-advance-status' && method === 'POST') {
        return jsonResponse({
          data: {
            batch_id: 'requirement_status_batch_001',
            skipped: [
              {
                code: 'REQUIREMENT_VERSION_REQUIRED',
                id: 'requirement_pool',
                message: 'Requirement must be scheduled to a version before advancing to this status',
              },
            ],
            skipped_count: 1,
            target_status: 'ready_for_dev',
            updated: [],
            updated_count: 1,
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
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<RequirementsPage />);

    await screen.findByText('归集需求一');
    expect(screen.getByRole('table')).toHaveAttribute('data-table-layout', 'fixed');
    expect(screen.getByRole('table')).toHaveAttribute('data-table-scroll-x', '1720');
    expect(screen.getByRole('columnheader', { name: '需求标题' })).toHaveAttribute(
      'data-width',
      '260',
    );
    expect(screen.getByRole('columnheader', { name: '操作' })).toHaveAttribute(
      'data-width',
      '164',
    );
    expect(screen.getByText('创建时间')).toBeInTheDocument();
    expect(screen.getByText('2026-06-04 16:00')).toBeInTheDocument();
    expect(screen.getByText('2026-06-04 16:10')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('迭代版本'), { target: { value: '2026-05' } });
    fireEvent.submit(screen.getByRole('form', { name: '查询表格' }));

    await waitFor(() => expect(screen.queryByText('归集需求一')).not.toBeInTheDocument());
    expect(screen.getByText('归集需求二')).toBeInTheDocument();

    fireEvent.reset(screen.getByRole('form', { name: '查询表格' }));
    expect(await screen.findByText('归集需求一')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('checkbox', { name: '选择 requirement_pool' }));
    fireEvent.click(screen.getByRole('checkbox', { name: '选择 requirement_planned' }));
    fireEvent.click(screen.getByRole('button', { name: '批量分配负责人' }));

    expect(await screen.findByText('已选择 2 条需求')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('负责人'), {
      target: { value: 'rd_owner@example.com' },
    });
    const assignReasonInput = screen.getByLabelText('分配原因');
    expect(assignReasonInput).toHaveAttribute('rows', '2');
    fireEvent.change(assignReasonInput, {
      target: { value: '统一交给研发负责人推进' },
    });
    fireEvent.click(screen.getByRole('button', { name: '确认分配' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/requirements/batch-assign-owner',
        'POST',
      ]),
    );
    const assignCall = fetchMock.mock.calls.find(
      ([path, init]) => path === '/api/requirements/batch-assign-owner' && init?.method === 'POST',
    );
    expect(JSON.parse(String(assignCall?.[1]?.body))).toEqual({
      assignee: 'rd_owner@example.com',
      reason: '统一交给研发负责人推进',
      requirement_ids: ['requirement_pool', 'requirement_planned'],
    });

    fireEvent.click(screen.getByRole('checkbox', { name: '选择 requirement_pool' }));
    fireEvent.click(screen.getByRole('checkbox', { name: '选择 requirement_planned' }));
    fireEvent.click(screen.getByRole('button', { name: '批量推进状态' }));

    expect(await screen.findByText('仅支持按研发流程向前推进，终态、重复或不符合路径的需求会由后端跳过。')).toBeInTheDocument();
    const advanceReasonInput = screen.getByLabelText('推进原因');
    expect(advanceReasonInput).toHaveAttribute('rows', '2');
    fireEvent.change(advanceReasonInput, {
      target: { value: '统一推进到待开发' },
    });
    fireEvent.click(screen.getByRole('button', { name: '确认推进' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/requirements/batch-advance-status',
        'POST',
      ]),
    );
    const advanceCall = fetchMock.mock.calls.find(
      ([path, init]) => path === '/api/requirements/batch-advance-status' && init?.method === 'POST',
    );
    expect(JSON.parse(String(advanceCall?.[1]?.body))).toEqual({
      reason: '统一推进到待开发',
      requirement_ids: ['requirement_pool', 'requirement_planned'],
      target_status: 'ready_for_dev',
    });
    expect(await screen.findByRole('dialog', { name: '批量推进状态结果' })).toBeInTheDocument();
    expect(screen.getByText('REQUIREMENT_VERSION_REQUIRED · Requirement must be scheduled to a version before advancing to this status')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    fireEvent.click(screen.getByRole('checkbox', { name: '选择 requirement_pool' }));
    fireEvent.click(screen.getByRole('checkbox', { name: '选择 requirement_planned' }));
    fireEvent.click(screen.getByRole('button', { name: /批量排期/ }));

    expect(await screen.findByText('已选择 2 条需求')).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByLabelText('目标版本'));
    expect(screen.queryByRole('option', { name: 'archived · 归档版本' })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole('option', { name: '2026-06 · 2026-06' }));
    const scheduleReasonInput = screen.getByLabelText('归集原因');
    expect(scheduleReasonInput).toHaveAttribute('rows', '2');
    fireEvent.change(scheduleReasonInput, {
      target: { value: '纳入 2026-06 迭代' },
    });
    fireEvent.click(screen.getByRole('button', { name: '确认归集' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/requirements/batch-schedule',
        'POST',
      ]),
    );
    const batchCall = fetchMock.mock.calls.find(
      ([path, init]) => path === '/api/requirements/batch-schedule' && init?.method === 'POST',
    );
    expect(JSON.parse(String(batchCall?.[1]?.body))).toEqual({
      product_id: 'product_api',
      reason: '纳入 2026-06 迭代',
      requirement_ids: ['requirement_pool', 'requirement_planned'],
      version_id: 'version_target',
    });
  });

  it('batch generates tasks for selected planned requirements from the requirements page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      if (path === '/api/products' || path.startsWith('/api/products?')) {
        return jsonResponse({
          data: {
            items: [{ code: 'API-PRODUCT', id: 'product_api', name: '接口产品', status: 'active' }],
            total: 1,
          },
        });
      }
      if (path === '/api/product-versions' || path.startsWith('/api/product-versions?')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-06',
                id: 'version_target',
                name: '2026-06',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'planning',
              },
            ],
            total: 1,
          },
        });
      }
      if ((path === '/api/requirements' || path.startsWith('/api/requirements?')) && method === 'GET') {
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
                  content: '补充 AI 助手引用链接。',
                  created_at: '2026-06-04T07:30:00+00:00',
                  created_by: 'user_admin',
                  id: 'requirement_083',
                  priority: 'P1',
                  product_code: 'AI-BRAIN',
                  product_id: 'product_ai_brain',
                  product_name: 'AI Brain',
                  status: 'developing',
                  title: 'AI 助手引用链接',
                  version_id: 'version_assistant_history',
                  version_name: '2026-06 AI 助手历史记录迭代',
                },
              ],
              total: 2,
            },
          });
        }
        return jsonResponse({
          data: {
            items: [
              {
                content: '批量生成任务一内容',
                created_at: '2026-06-04T08:00:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_batch_task_a',
                priority: 'P1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'planned',
                title: '批量生成任务一',
                version_id: 'version_target',
                version_name: '2026-06',
              },
              {
                content: '批量生成任务二内容',
                created_at: '2026-06-04T08:10:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_batch_task_b',
                priority: 'P1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'planned',
                title: '批量生成任务二',
                version_id: 'version_target',
                version_name: '2026-06',
              },
            ],
            total: 2,
          },
        });
      }
      if (path === '/api/requirements/batch-generate-tasks' && method === 'POST') {
        return jsonResponse({
          data: {
            batch_id: 'requirement_task_batch_001',
            generated: [
              {
                requirement_id: 'requirement_batch_task_a',
                task_id: 'task_batch_a',
                task_status: 'draft',
                task_type: 'product_detail_design',
              },
              {
                requirement_id: 'requirement_batch_task_b',
                task_id: 'task_batch_b',
                task_status: 'draft',
                task_type: 'product_detail_design',
              },
            ],
            generated_count: 2,
            product_id: 'product_api',
            skipped: [],
            skipped_count: 0,
          },
        });
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<RequirementsPage />);

    await screen.findByText('批量生成任务一');
    fireEvent.click(screen.getByRole('checkbox', { name: '选择 requirement_batch_task_a' }));
    fireEvent.click(screen.getByRole('checkbox', { name: '选择 requirement_batch_task_b' }));
    fireEvent.click(screen.getByRole('button', { name: /批量生成任务/ }));

    expect(await screen.findByText('将为 2 条已排期需求生成产品详细设计任务')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('生成原因'), {
      target: { value: '批量进入产品详细设计' },
    });
    fireEvent.click(screen.getByRole('button', { name: '确认生成' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/requirements/batch-generate-tasks',
        'POST',
      ]),
    );
    const batchCall = fetchMock.mock.calls.find(
      ([path, init]) => path === '/api/requirements/batch-generate-tasks' && init?.method === 'POST',
    );
    expect(JSON.parse(String(batchCall?.[1]?.body))).toEqual({
      product_id: 'product_api',
      reason: '批量进入产品详细设计',
      requirement_ids: ['requirement_batch_task_a', 'requirement_batch_task_b'],
    });
  });

  it('opens a requirement full-chain timeline from the requirements page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path.startsWith('/api/products?active_only=true')) {
        return jsonResponse({
          data: {
            items: [{ code: 'AI-BRAIN', id: 'product_ai_brain', name: 'AI Brain', status: 'active' }],
            total: 1,
          },
        });
      }
      if (path === '/api/product-versions' || path.startsWith('/api/product-versions?')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-06-assistant-history',
                id: 'version_assistant_history',
                name: '2026-06 AI 助手历史记录迭代',
                product_code: 'AI-BRAIN',
                product_id: 'product_ai_brain',
                product_name: 'AI Brain',
                status: 'testing',
              },
            ],
            total: 1,
          },
        });
      }
      if ((path === '/api/requirements' || path.startsWith('/api/requirements?')) && method === 'GET') {
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
                  content: '补充 AI 助手引用链接。',
                  created_at: '2026-06-04T07:30:00+00:00',
                  created_by: 'user_admin',
                  id: 'requirement_083',
                  priority: 'P1',
                  product_code: 'AI-BRAIN',
                  product_id: 'product_ai_brain',
                  product_name: 'AI Brain',
                  status: 'developing',
                  title: 'AI 助手引用链接',
                  version_id: 'version_assistant_history',
                  version_name: '2026-06 AI 助手历史记录迭代',
                },
              ],
              total: 2,
            },
          });
        }
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
            ],
            total: 1,
          },
        });
      }
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
            code_review_reports: [
              {
                archived_at: '2026-06-04T10:00:00+00:00',
                id: 'report_history',
                risk_level: 'medium',
                status: 'confirmed',
                summary: 'Review 结论：补充用户级隔离测试。',
              },
            ],
            git_snapshots: [
              {
                changed_files_summary: [
                  { additions: 6, deletions: 1, path: 'apps/api/app/main.py' },
                  { additions: 4, deletions: 0, path: 'apps/web/src/pages/Assistant/index.tsx' },
                ],
                created_at: '2026-06-04T09:30:00+00:00',
                diff_file_tree: [
                  { additions: 10, deletions: 1, file_count: 2, path: 'apps' },
                ],
                id: 'snapshot_pr_12',
                mr_iid: 12,
                review_checklist: ['确认用户级历史记录隔离测试覆盖'],
                risk_summary: {
                  file_count: 2,
                  largest_file: {
                    additions: 6,
                    deletions: 1,
                    line_count: 7,
                    path: 'apps/api/app/main.py',
                  },
                  risk_level: 'medium',
                  total_additions: 10,
                  total_changed_lines: 11,
                  total_deletions: 1,
                },
              },
            ],
            iteration_version: {
              code: '2026-06-assistant-history',
              id: 'version_assistant_history',
              name: '2026-06 AI 助手历史记录迭代',
              status: 'active',
            },
            jenkins_releases: [
              {
                build_id: 'build-084',
                created_at: '2026-06-04T12:00:00+00:00',
                id: 'jenkins_release_084',
                job_name: 'ai-brain-release',
                status: 'failed',
              },
            ],
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
            reviews: [{ ai_task_id: 'task_design', created_at: '2026-06-04T08:20:00+00:00', id: 'review_design', status: 'approved' }],
            status: 'available',
            summary: {
              ai_tasks: 1,
              bugs: 1,
              code_review_reports: 1,
              git_snapshots: 1,
              jenkins_releases: 1,
              knowledge_deposits: 1,
              reviews: 1,
              timeline_events: 8,
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
                occurred_at: '2026-06-04T10:00:00+00:00',
                metadata: { summary: 'Review 结论：补充用户级隔离测试。' },
                status: 'confirmed',
                subject_id: 'report_history',
                title: '代码评审：report_history',
                type: 'code_review_report',
              },
            ],
          },
        });
      }
      if (
        path === '/api/requirements?version_id=version_assistant_history&page=1&page_size=100&sort_by=created_at&sort_order=desc' ||
        path.includes('page_size=100')
      ) {
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
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<RequirementsPage />);

    await screen.findByText('AI 助手历史记录');
    fireEvent.click(screen.getByRole('button', { name: '全链路' }));

    expect(await screen.findByRole('dialog', { name: '需求全链路 · requirement_084' })).toBeInTheDocument();
    expect(screen.getByText('需求：AI 助手历史记录')).toBeInTheDocument();
    expect(screen.getByText('AI 任务：产品详细设计：AI 助手历史记录')).toBeInTheDocument();
    expect(screen.getByText('代码评审：report_history')).toBeInTheDocument();
    expect(screen.getByText('PR/MR 证据')).toBeInTheDocument();
    expect(screen.getAllByText(/中风险 · 2 文件 · \+10\/-1/).length).toBeGreaterThan(0);
    expect(screen.getByText(/apps · 2 文件 · \+10\/-1/)).toBeInTheDocument();
    expect(screen.getByText('确认用户级历史记录隔离测试覆盖')).toBeInTheDocument();
    expect(screen.getByText('1 个 AI 任务')).toBeInTheDocument();
    expect(screen.getByText('1 个 Bug')).toBeInTheDocument();
    expect(screen.getByText('1 个发布记录')).toBeInTheDocument();
    const stageProgress = screen.getByLabelText('全链路阶段进度');
    expect(within(stageProgress).getByText('阶段进度')).toBeInTheDocument();
    expect(within(stageProgress).getByText('需求')).toBeInTheDocument();
    expect(within(stageProgress).getByText('迭代版本')).toBeInTheDocument();
    expect(within(stageProgress).getByText('AI 任务')).toBeInTheDocument();
    expect(within(stageProgress).getByText('Review')).toBeInTheDocument();
    expect(within(stageProgress).getByText('PR/代码评审')).toBeInTheDocument();
    expect(within(stageProgress).getByText('Bug')).toBeInTheDocument();
    expect(within(stageProgress).getByText('发布')).toBeInTheDocument();
    expect(within(stageProgress).getByText('知识沉淀')).toBeInTheDocument();
    expect(within(stageProgress).getByText('测试中 · 1 项')).toBeInTheDocument();
    expect(within(stageProgress).getByText('开发中 · 2026-06-assistant-history')).toBeInTheDocument();
    expect(within(stageProgress).getByText('1 快照 / 1 报告')).toBeInTheDocument();
    expect(within(stageProgress).getByRole('list', { name: '阶段进度清单' })).toBeInTheDocument();
    const stageDetails = screen.getByLabelText('全链路阶段明细');
    expect(within(stageDetails).getByText('阶段明细')).toBeInTheDocument();
    expect(within(stageDetails).getByText('产品详细设计：AI 助手历史记录')).toBeInTheDocument();
    expect(within(stageDetails).getByText('聊天记录未按用户隔离')).toBeInTheDocument();
    expect(within(stageDetails).getByText('Review 结论：补充用户级隔离测试。')).toBeInTheDocument();
    expect(within(stageDetails).getByRole('link', { name: '查看任务 task_design' })).toHaveAttribute(
      'href',
      '/delivery/rd-tasks?task_id=task_design',
    );
    expect(within(stageDetails).getByRole('link', { name: '查看 Bug bug_history' })).toHaveAttribute(
      'href',
      '/delivery/bugs?bug_id=bug_history',
    );
    const versionComparison = await screen.findByLabelText('版本内需求对比');
    await within(versionComparison).findByText('当前版本共 2 条需求，当前需求 requirement_084');
    expect(within(versionComparison).getByText('AI 助手引用链接')).toBeInTheDocument();
    expect(within(versionComparison).getByText('测试中 1')).toBeInTheDocument();
    expect(within(versionComparison).getByText('开发中 1')).toBeInTheDocument();
    const createObjectURL = vi.fn(() => 'blob:full-chain-report');
    const revokeObjectURL = vi.fn();
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    const blobParts: BlobPart[][] = [];
    class MockBlob {
      readonly parts: BlobPart[];
      readonly type?: string;

      constructor(parts: BlobPart[], options?: BlobPropertyBag) {
        this.parts = parts;
        this.type = options?.type;
        blobParts.push(parts);
      }
    }
    const originalCreateObjectURL = URL.createObjectURL;
    const originalRevokeObjectURL = URL.revokeObjectURL;
    vi.stubGlobal('Blob', MockBlob as unknown as typeof Blob);
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL });
    fireEvent.click(screen.getByRole('button', { name: '导出链路报告' }));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(anchorClick).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:full-chain-report');
    const reportText = blobParts[0].map(String).join('');
    expect(reportText).toContain('# 需求全链路报告：AI 助手历史记录');
    expect(reportText).toContain('- Bug：1');
    expect(reportText).toContain('Review 结论：补充用户级隔离测试。');
    if (originalCreateObjectURL) {
      Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: originalCreateObjectURL });
    } else {
      Reflect.deleteProperty(URL, 'createObjectURL');
    }
    if (originalRevokeObjectURL) {
      Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: originalRevokeObjectURL });
    } else {
      Reflect.deleteProperty(URL, 'revokeObjectURL');
    }
    const timelineSection = screen.getByLabelText('全链路时间线');
    expect(within(timelineSection).getByText('3 / 3 个事件')).toBeInTheDocument();
    fireEvent.mouseDown(within(timelineSection).getByLabelText('时间线类型筛选'));
    const codeReviewOptions = await screen.findAllByText('代码评审');
    fireEvent.click(codeReviewOptions[codeReviewOptions.length - 1]);
    expect(within(timelineSection).getByText('1 / 3 个事件')).toBeInTheDocument();
    expect(within(timelineSection).getByText('代码评审：report_history')).toBeInTheDocument();
    expect(within(timelineSection).queryByText('需求：AI 助手历史记录')).not.toBeInTheDocument();
    expect(within(timelineSection).queryByText('AI 任务：产品详细设计：AI 助手历史记录')).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path]) => path)).toContain('/api/requirements/requirement_084/full-chain');
    expect(fetchMock.mock.calls.map(([path]) => path)).toContain(
      '/api/requirements?version_id=version_assistant_history&page=1&page_size=100&sort_by=created_at&sort_order=desc',
    );
  });

});
