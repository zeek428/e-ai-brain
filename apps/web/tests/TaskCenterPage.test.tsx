import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import TaskCenterPage from '../src/pages/TaskCenter';

beforeEach(() => {
  window.localStorage.setItem(
    'ai_brain_current_user',
    JSON.stringify({
      display_name: 'Admin',
      id: 'user_admin',
      roles: ['admin'],
      username: 'admin@example.com',
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  void message.destroy();
  notification.destroy();
  Modal.destroyAll();
});

describe('TaskCenterPage', () => {
  it('cancels a cancellable task from the row operation dialog', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path.startsWith('/api/reviews/pending')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (
        path === '/api/products?active_only=true' ||
        path === '/api/products?active_only=true&page_size=100'
      ) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (
        path === '/api/product-versions?active_only=true' ||
        path === '/api/product-versions?active_only=true&page_size=100'
      ) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/ai-tasks/task_cancel/cancel' && init?.method === 'POST') {
        expect(init.body).toBeUndefined();
        return jsonResponse({ data: { id: 'task_cancel', status: 'cancelled' } });
      }
      if (path.startsWith('/api/ai-tasks')) {
        return jsonResponse({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_cancel',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'waiting_review',
                task_type: 'technical_solution',
                title: '可取消任务',
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${path}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    const taskRow = (await screen.findByText('可取消任务')).closest('tr');
    expect(taskRow).not.toBeNull();
    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));
    const operationDialog = await screen.findByTestId('task-operation-dialog');
    fireEvent.click(within(operationDialog).getByRole('button', { name: '取消任务' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/ai-tasks/task_cancel/cancel',
        'POST',
      ]),
    );
  });

  it('hides task mutation actions for viewer users', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-viewer' });
      const path = String(input);
      if (path.startsWith('/api/reviews/pending')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (
        path === '/api/products?active_only=true' ||
        path === '/api/products?active_only=true&page_size=100'
      ) {
        return jsonResponse({
          data: {
            items: [{ code: 'AI-BRAIN', id: 'product_api', name: 'AI Brain 产品' }],
            total: 1,
          },
        });
      }
      if (path.startsWith('/api/ai-tasks?page=1&page_size=10')) {
        return jsonResponse({
          data: {
            items: [
              {
                created_at: '2026-06-04T09:00:00+00:00',
                current_step: 'completed',
                id: 'task_viewer',
                product_id: 'product_api',
                product_name: 'AI Brain 产品',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'technical_solution',
                title: 'Viewer 只读任务',
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-viewer');
    window.localStorage.setItem(
      'ai_brain_current_user',
      JSON.stringify({
        display_name: 'Viewer',
        id: 'user_viewer',
        roles: ['viewer'],
        username: 'viewer@example.com',
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    const taskRow = (await screen.findByText('Viewer 只读任务')).closest('tr');
    expect(taskRow).not.toBeNull();
    expect(screen.queryByRole('button', { name: '批量重试' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '批量取消' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '待确认' })).not.toBeInTheDocument();

    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));
    const operationDialog = await screen.findByTestId('task-operation-dialog');
    expect(within(operationDialog).getByRole('button', { name: '查看详情' })).toBeInTheDocument();
    expect(within(operationDialog).queryByRole('button', { name: '模拟 Issue' })).not.toBeInTheDocument();
    expect(within(operationDialog).queryByRole('button', { name: '生成开发计划' })).not.toBeInTheDocument();
  });

  it('opens a Code Review report with a requirement full-chain link', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path.startsWith('/api/reviews/pending')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (
        path === '/api/products?active_only=true' ||
        path === '/api/products?active_only=true&page_size=100'
      ) {
        return jsonResponse({
          data: {
            items: [{ code: 'AI-BRAIN', id: 'product_api', name: 'AI Brain 产品' }],
            total: 1,
          },
        });
      }
      if (input === '/api/product-versions?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (typeof input === 'string' && input.startsWith('/api/ai-tasks?page=1&page_size=10')) {
        return jsonResponse({
          data: {
            items: [
              {
                created_at: '2026-06-04T09:00:00+00:00',
                id: 'task_code_review',
                owner: 'user_admin',
                product_id: 'product_api',
                product_name: 'AI Brain 产品',
                requirement_id: 'requirement_api',
                status: 'waiting_review',
                task_type: 'code_review',
                title: 'Code Review：接口任务',
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      if (input === '/api/ai-tasks/task_code_review/code-review-report') {
        return jsonResponse({
          data: {
            findings: [
              {
                file_path: 'apps/api/app/main.py',
                line_number: 42,
                severity: 'high',
                summary: '缺少边界测试',
              },
            ],
            gitlab_writeback_performed: false,
            id: 'report_api',
            risk_level: 'medium',
            status: 'pending_review',
            summary: '发现 1 个高风险问题',
            writeback_template: {
              body: '## AI Brain Code Review 结论\n\n- 风险等级：medium\n- 远端回写：未自动回写',
              format: 'markdown',
              title: 'AI Brain Code Review: medium risk',
              writeback_allowed: false,
              writeback_reason: 'read_only_review_flow',
            },
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    const codeReviewTaskRow = (await screen.findByText('Code Review：接口任务')).closest('tr');
    expect(codeReviewTaskRow).not.toBeNull();
    fireEvent.click(within(codeReviewTaskRow as HTMLElement).getByRole('button', { name: '操作' }));
    const operationDialog = await screen.findByTestId('task-operation-dialog');
    fireEvent.click(within(operationDialog).getByRole('button', { name: '查看报告' }));

    expect(await screen.findByText('发现 1 个高风险问题')).toBeInTheDocument();
    expect(screen.getByText('Review 结论回写模板')).toBeInTheDocument();
    expect(screen.getByDisplayValue(/AI Brain Code Review 结论/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看需求全链路' })).toHaveAttribute(
      'href',
      '/delivery/requirements/requirement_api/full-chain',
    );
  });
  it('renders the task center from backend tasks without a demo workflow', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input).startsWith('/api/reviews/pending')) {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  ai_task_id: 'task_api',
                  content: { summary: '接口任务输出摘要' },
                  id: 'review_api',
                  stage: 'product_detail_design',
                  status: 'pending',
                  version: 1,
                },
              ],
              total: 1,
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (
        input === '/api/products?active_only=true' ||
        input === '/api/products?active_only=true&page_size=100'
      ) {
        return new Response(
          JSON.stringify({
            data: {
              items: [{ code: 'aibrain', id: 'product_api', name: 'AI Brain 产品' }],
              total: 1,
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (
        input === '/api/product-versions?active_only=true' ||
        input === '/api/product-versions?active_only=true&page_size=100'
      ) {
        return new Response(
          JSON.stringify({ data: { items: [], total: 0 } }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (input === '/api/ai-tasks/batch-cancel' && init?.method === 'POST') {
        return new Response(
          JSON.stringify({
            data: {
              batch_id: 'ai_task_cancel_batch_001',
              skipped: [
                {
                  code: 'TASK_STATE_INVALID',
                  id: 'task_done',
                  message: 'Task cannot be cancelled from current status',
                },
              ],
              skipped_count: 1,
              updated: [{ id: 'task_api', status: 'cancelled' }],
              updated_count: 1,
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (input === '/api/ai-tasks/batch-retry' && init?.method === 'POST') {
        return new Response(
          JSON.stringify({
            data: {
              batch_id: 'ai_task_retry_batch_001',
              retried: [
                {
                  current_step: 'interrupt_for_human_review',
                  id: 'task_retry',
                  review_id: 'review_retry',
                  status: 'waiting_review',
                },
                {
                  current_step: 'model_gateway_failed',
                  error_code: 'MODEL_GATEWAY_FAILED',
                  error_message: 'temporary upstream error',
                  id: 'task_retry_still_failed',
                  status: 'failed',
                },
              ],
              retried_count: 2,
              skipped: [
                {
                  code: 'TASK_NOT_RETRYABLE',
                  id: 'task_completed',
                  message: 'Task is not retryable',
                },
              ],
              skipped_count: 1,
              updated: [
                {
                  current_step: 'interrupt_for_human_review',
                  id: 'task_retry',
                  review_id: 'review_retry',
                  status: 'waiting_review',
                },
              ],
              updated_count: 1,
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (input === '/api/ai-tasks/task_code_review/code-review-report') {
        return new Response(
          JSON.stringify({
            data: {
              findings: [{ severity: 'high', summary: '缺少边界测试' }],
              gitlab_writeback_performed: false,
              id: 'report_api',
              risk_level: 'medium',
              status: 'pending_review',
              summary: '发现 1 个高风险问题',
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      expect(String(input).startsWith('/api/ai-tasks')).toBe(true);
      expect(String(input).startsWith('/api/ai-tasks/')).toBe(false);
      return new Response(
        JSON.stringify({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_api',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'waiting_review',
                task_type: 'product_detail_design',
                title: '接口任务',
              },
              {
                created_by: 'user_admin',
                current_step: 'model_gateway_failed',
                id: 'task_retry',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'failed',
                task_type: 'technical_solution',
                title: '模型网关失败任务',
              },
              {
                created_by: 'user_admin',
                id: 'task_design_done',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'product_detail_design',
                title: '已确认详细设计',
              },
              {
                created_by: 'user_admin',
                id: 'task_solution_done',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'technical_solution',
                title: '技术方案：接口任务',
              },
              {
                created_by: 'user_admin',
                id: 'task_code_review',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'waiting_review',
                task_type: 'code_review',
                title: 'Code Review：接口任务',
              },
              {
                created_by: 'user_admin',
                id: 'task_code_inspection',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'waiting_review',
                task_type: 'code_inspection_remediation',
                title: '代码巡检整改：硬编码敏感凭据',
              },
              {
                created_by: 'user_admin',
                id: 'task_bug_fix',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'draft',
                task_type: 'bug_fix',
                title: 'Bug 修复：登录失败',
              },
            ],
            total: 1,
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      );
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '任务管理' })).not.toBeInTheDocument();
    expect(
      screen.queryByText('研发大脑 v1 MVP：从需求审批到方案确认、GitLab 输入快照、内部 Review 和知识沉淀。'),
    ).not.toBeInTheDocument();
    expect(screen.getByText('任务列表')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('需求交付');
    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('研发任务');
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.queryByText('MVP-A 基础 + GitLab 输入闭环')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '运行 MVP 演示流程' })).not.toBeInTheDocument();
    expect(await screen.findByText('接口任务')).toBeInTheDocument();
    expect(screen.getByText('模型网关失败任务')).toBeInTheDocument();
    expect(screen.getAllByText('产品详细设计')).not.toHaveLength(0);
    expect(screen.getAllByText('代码巡检整改').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Bug 修复').length).toBeGreaterThan(0);
    expect(screen.queryByText('code_inspection_remediation')).not.toBeInTheDocument();
    expect(screen.queryByText('bug_fix')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '批量取消' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '批量重试' })).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox', { name: '选择 task_api' }));
    expect(screen.getByRole('button', { name: '批量取消' })).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: '批量取消' }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/ai-tasks/batch-cancel',
        'POST',
      ]),
    );
    const batchCancelCall = fetchMock.mock.calls.find(
      ([path, init]) => path === '/api/ai-tasks/batch-cancel' && init?.method === 'POST',
    );
    expect(JSON.parse(String(batchCancelCall?.[1]?.body))).toEqual({
      reason: '研发任务批量取消',
      task_ids: ['task_api'],
    });
    expect(await screen.findByRole('dialog', { name: '批量取消结果' })).toBeInTheDocument();
    expect(screen.getByText('ai_task_cancel_batch_001')).toBeInTheDocument();
    expect(screen.getByText('TASK_STATE_INVALID · Task cannot be cancelled from current status')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    fireEvent.click(screen.getByRole('checkbox', { name: '选择 task_retry' }));
    expect(screen.getByRole('button', { name: '批量重试' })).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: '批量重试' }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/ai-tasks/batch-retry',
        'POST',
      ]),
    );
    const batchRetryCall = fetchMock.mock.calls.find(
      ([path, init]) => path === '/api/ai-tasks/batch-retry' && init?.method === 'POST',
    );
    expect(JSON.parse(String(batchRetryCall?.[1]?.body))).toEqual({
      reason: '研发任务批量重试',
      task_ids: ['task_retry'],
    });
    expect(await screen.findByRole('dialog', { name: '批量重试结果' })).toBeInTheDocument();
    expect(screen.getByText('ai_task_retry_batch_001')).toBeInTheDocument();
    expect(screen.getByText('failed · model_gateway_failed · MODEL_GATEWAY_FAILED · temporary upstream error')).toBeInTheDocument();
    expect(screen.getByText('TASK_NOT_RETRYABLE · Task is not retryable')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: '批量重试结果' })).not.toBeInTheDocument());

    expect(screen.getByRole('button', { name: '待确认' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '操作' })).toHaveLength(7);
    expect(screen.queryByRole('button', { name: '确认输出' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '生成技术方案' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '导出 Markdown' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '模拟 Issue' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '创建 Code Review' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '生成开发计划' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '生成自动化测试' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '生成发布评估' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '查看报告' })).not.toBeInTheDocument();
    expect(screen.queryByText('确认台')).not.toBeInTheDocument();
    expect(screen.queryByText('确认编号')).not.toBeInTheDocument();
    const completedTaskRow = screen.getByText('技术方案：接口任务').closest('tr');
    expect(completedTaskRow).not.toBeNull();
    fireEvent.click(within(completedTaskRow as HTMLElement).getByRole('button', { name: '操作' }));
    const operationDialog = await screen.findByTestId('task-operation-dialog');
    const summarySection = screen.getByTestId('task-operation-summary');
    const actionSection = screen.getByTestId('task-operation-actions');
    expect(screen.getByText('任务操作')).toBeInTheDocument();
    expect(summarySection).toHaveTextContent('技术方案：接口任务');
    expect(operationDialog).toContainElement(summarySection);
    expect(operationDialog).toContainElement(actionSection);
    expect(summarySection.compareDocumentPosition(actionSection)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(actionSection).toHaveClass('task-operation-actions');
    expect(screen.getByRole('button', { name: '生成开发计划' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成自动化测试' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成发布评估' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '创建 Code Review' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '待确认' }));
    expect(await screen.findByText('接口任务输出摘要')).toBeInTheDocument();
    expect(screen.getByText('确认通过后由 Runner 合入主工作区，拒绝后由 Runner 丢弃隔离结果。')).toBeInTheDocument();
    const pendingReviewTable = screen
      .getAllByRole('table')
      .find((table) => table.getAttribute('data-table-scroll-x') === '1160');
    expect(pendingReviewTable).toBeDefined();
    expect(pendingReviewTable).toHaveAttribute('data-table-layout', 'fixed');
    expect(pendingReviewTable).toHaveAttribute('data-table-scroll-x', '1160');
    expect(screen.getAllByText('确认编号')).not.toHaveLength(0);
    expect(within(pendingReviewTable as HTMLElement).getByRole('columnheader', { name: '操作' })).toHaveAttribute(
      'data-fixed',
      'right',
    );
    expect(screen.getByRole('button', { name: '确认通过' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '拒绝并丢弃' })).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
      expect.stringMatching(/^\/api\/reviews\/pending\?.*page=1.*page_size=20/),
      'GET',
    ]);
  });

  it('loads task-scoped pending reviews from row operations without local filtering', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path.startsWith('/api/reviews/pending')) {
        return jsonResponse({
          data: path.includes('ai_task_id=task_scoped')
            ? {
                items: [
                  {
                    ai_task_id: 'task_scoped',
                    content: {
                      result: {
                        output_preview:
                          '@@ -1,3 +1,3 @@\n- raw diff\n+ fixed diff\n\n' +
                          'tokens used\n1,024\n**整改状态：已修复** - 任务级输出摘要 - `npm test`：通过',
                      },
                    },
                    id: 'review_scoped',
                    stage: 'technical_solution',
                    status: 'pending',
                    version: 1,
                  },
                ],
                page: 1,
                page_size: 20,
                total: 1,
              }
            : {
                items: [],
                page: 1,
                page_size: 20,
                total: 0,
              },
        });
      }
      if (
        path === '/api/products?active_only=true' ||
        path === '/api/products?active_only=true&page_size=100'
      ) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (
        path === '/api/product-versions?active_only=true' ||
        path === '/api/product-versions?active_only=true&page_size=100'
      ) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path.startsWith('/api/ai-tasks')) {
        return jsonResponse({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_scoped',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'waiting_review',
                task_type: 'technical_solution',
                title: '任务级确认任务',
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${path}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('任务级确认任务')).toBeInTheDocument();
    const taskRow = screen.getByText('任务级确认任务').closest('tr');
    expect(taskRow).not.toBeNull();
    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));
    const operationDialog = await screen.findByTestId('task-operation-dialog');
    fireEvent.click(within(operationDialog).getByRole('button', { name: '确认输出' }));

    expect(await screen.findByText('确认输出：任务级确认任务')).toBeInTheDocument();
    const reviewSummary = await screen.findByTestId('task-output-summary-preview');
    expect(within(reviewSummary).getByText('整改状态')).toBeInTheDocument();
    expect(within(reviewSummary).getByText('已修复')).toBeInTheDocument();
    expect(within(reviewSummary).getByText('任务级输出摘要')).toBeInTheDocument();
    expect(within(reviewSummary).getByText('npm test')).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
      expect.stringMatching(/^\/api\/reviews\/pending\?.*ai_task_id=task_scoped/),
      'GET',
    ]);
  });

  it('filters task center tasks by product and time range', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path.startsWith('/api/reviews/pending')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (
        path === '/api/products?active_only=true' ||
        path === '/api/products?active_only=true&page_size=100'
      ) {
        return jsonResponse({
          data: {
            items: [{ code: 'aibrain', id: 'product_api', name: 'AI Brain 产品' }],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions?active_only=true' ||
        path === '/api/product-versions?active_only=true&page_size=100'
      ) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (
        path === '/api/ai-tasks' ||
        (
          path.startsWith('/api/ai-tasks?') &&
          !path.includes('product_id=')
        )
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                created_at: '2026-06-02T09:30:00+00:00',
                created_by: 'user_admin',
                id: 'task_target',
                product_id: 'product_api',
                product_name: 'AI Brain 产品',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'technical_solution',
                title: '目标技术方案任务',
              },
              {
                created_at: '2026-06-02T10:00:00+00:00',
                created_by: 'user_admin',
                id: 'task_other_product',
                product_id: 'product_other',
                product_name: '其他产品',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'technical_solution',
                title: '其他产品任务',
              },
              {
                created_at: '2026-05-20T10:00:00+00:00',
                created_by: 'user_admin',
                id: 'task_old',
                product_id: 'product_api',
                product_name: 'AI Brain 产品',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'technical_solution',
                title: '过期技术方案任务',
              },
            ],
            total: 3,
          },
        });
      }
      if (
        path.startsWith('/api/ai-tasks?') &&
        path.includes('product_id=product_api')
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                created_at: '2026-06-02T09:30:00+00:00',
                created_by: 'user_admin',
                id: 'task_target',
                product_id: 'product_api',
                product_name: 'AI Brain 产品',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'technical_solution',
                title: '目标技术方案任务',
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${path}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('目标技术方案任务')).toBeInTheDocument();
    expect(screen.getByText('其他产品任务')).toBeInTheDocument();
    expect(screen.getByText('过期技术方案任务')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('所属产品'), {
      target: { value: 'product_api' },
    });
    fireEvent.change(screen.getByLabelText('时间段 开始'), {
      target: { value: '2026-06-01' },
    });
    fireEvent.change(screen.getByLabelText('时间段 结束'), {
      target: { value: '2026-06-03' },
    });
    fireEvent.click(screen.getByRole('button', { name: '查询' }));

    expect(await screen.findByText('目标技术方案任务')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('其他产品任务')).not.toBeInTheDocument());
    expect(screen.queryByText('过期技术方案任务')).not.toBeInTheDocument();
  });

  it('opens real task details from task row operations', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input).startsWith('/api/reviews/pending')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (
        input === '/api/products?active_only=true' ||
        input === '/api/products?active_only=true&page_size=100'
      ) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (
        input === '/api/product-versions?active_only=true' ||
        input === '/api/product-versions?active_only=true&page_size=100'
      ) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ai-tasks' || (typeof input === 'string' && input.startsWith('/api/ai-tasks?'))) {
        return jsonResponse({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_detail_api',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'code_inspection_remediation',
                title: '代码巡检整改：详情入口',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/ai-tasks/task_detail_api') {
        return jsonResponse({
          data: {
            current_step: 'completed',
            graph_runs: [{ id: 'graph_run_api', status: 'completed' }],
            id: 'task_detail_api',
            input: {
              code_inspection_finding_id: 'code_inspection_finding_api',
              code_inspection_report_id: 'code_inspection_report_api',
              description: 'Access key is committed in source code.',
              file_path: 'src/config.py',
              line_number: 12,
              product_context: {
                module: { code: 'core', name: '工作台模块' },
                product: { id: 'product_api', name: 'AI Brain 产品' },
                version: { id: 'version_api', name: 'v1 MVP' },
              },
              recommendation: 'Move the key to a secret manager.',
              rule_id: 'SEC001',
              severity: 'critical',
              requirement_snapshot: {
                id: 'requirement_api',
                title: '真实需求快照',
              },
            },
            output: {
              result: {
                output_preview:
                  "@@ -150,7 +202,7 @@\n- username: 'admin@example.com'\n+ username: TEST_LOGIN_USERNAME",
              },
            },
            output_summary:
              '**整改状态：已修复**\n' +
              '- 已删除登录页硬编码凭据\n' +
              '**验证方式**\n' +
              '- `npm test`：通过\n' +
              '**结构化结论**\n' +
              '```json\n' +
              '{"verdict":"fixed"}\n' +
              '```',
            pending_review: null,
            product_id: 'product_api',
            requirement_id: 'requirement_api',
            status: 'completed',
            task_type: 'code_inspection_remediation',
            title: '代码巡检整改：详情入口',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('代码巡检整改：详情入口')).toBeInTheDocument();
    const taskRow = screen.getByText('代码巡检整改：详情入口').closest('tr');
    expect(taskRow).not.toBeNull();
    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));

    expect(await screen.findByText('任务操作')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '查看详情' }));

    expect(await screen.findByText(/任务详情：代码巡检整改：详情入口/)).toBeInTheDocument();
    expect(screen.getAllByText('代码巡检整改').length).toBeGreaterThan(0);
    expect(screen.queryByText('code_inspection_remediation')).not.toBeInTheDocument();
    expect(screen.getByText('AI Brain 产品')).toBeInTheDocument();
    expect(screen.getByText('v1 MVP')).toBeInTheDocument();
    expect(screen.getByText('工作台模块')).toBeInTheDocument();
    expect(screen.getByText('真实需求快照')).toBeInTheDocument();
    expect(screen.getByText('graph_run_api')).toBeInTheDocument();
    expect(screen.getByText('代码巡检定位')).toBeInTheDocument();
    expect(screen.getByText('src/config.py:12')).toBeInTheDocument();
    expect(screen.getByText('SEC001')).toBeInTheDocument();
    expect(screen.getByText('critical')).toBeInTheDocument();
    expect(screen.getByText('code_inspection_finding_api')).toBeInTheDocument();
    expect(screen.getByText('Access key is committed in source code.')).toBeInTheDocument();
    expect(screen.getByText('Move the key to a secret manager.')).toBeInTheDocument();
    const outputSummaryReport = screen.getByTestId('task-output-summary-report');
    expect(within(outputSummaryReport).getByText('整改状态')).toBeInTheDocument();
    expect(within(outputSummaryReport).getByText('已修复')).toBeInTheDocument();
    expect(within(outputSummaryReport).getByText('已删除登录页硬编码凭据')).toBeInTheDocument();
    expect(within(outputSummaryReport).getByText('验证方式')).toBeInTheDocument();
    expect(within(outputSummaryReport).getByText('npm test')).toBeInTheDocument();
    expect(within(outputSummaryReport).getByText('{"verdict":"fixed"}')).toBeInTheDocument();
    expect(screen.getByDisplayValue(/output_preview/)).toBeInTheDocument();
    await waitFor(() => {
      const relevantCalls = fetchMock.mock.calls
        .map(([path, init]) => [
          String(path).startsWith('/api/ai-tasks?')
            ? '/api/ai-tasks'
            : String(path).startsWith('/api/reviews/pending')
              ? '/api/reviews/pending'
              : path,
          init?.method ?? 'GET',
        ])
        .filter(([path]) => !String(path).startsWith('/api/products'))
        .filter(([path]) => !String(path).startsWith('/api/product-versions'));
      expect(relevantCalls).toHaveLength(3);
      expect(relevantCalls).toContainEqual(['/api/ai-tasks', 'GET']);
      expect(relevantCalls).toContainEqual(['/api/reviews/pending', 'GET']);
      expect(relevantCalls).toContainEqual(['/api/ai-tasks/task_detail_api', 'GET']);
    });
  });

  it('submits edit-approved review decisions from the task center dialog', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input).startsWith('/api/reviews/pending')) {
        return jsonResponse({
          data: {
            items: [
              {
                ai_task_id: 'task_api',
                content: { summary: 'AI 原始技术方案摘要' },
                id: 'review_api',
                stage: 'technical_solution',
                status: 'pending',
                version: 1,
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/ai-tasks' || (typeof input === 'string' && input.startsWith('/api/ai-tasks?'))) {
        return jsonResponse({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_api',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'waiting_review',
                task_type: 'technical_solution',
                title: '技术方案确认任务',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/reviews/review_api/edit-approve') {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBe(
          JSON.stringify({
            edited_content: { summary: '人工修订后的技术方案摘要' },
            version: 1,
          }),
        );
        return jsonResponse({
          data: { review_status: 'edited_approved', task_status: 'completed' },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('技术方案确认任务')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '待确认' }));
    expect(await screen.findByText('AI 原始技术方案摘要')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '修改后通过' }));
    const editApproveModalTitle = await screen.findByText('修改后通过：review_api');
    const editApproveModal = editApproveModalTitle.closest('.ant-modal') as HTMLElement;
    fireEvent.change(screen.getByRole('textbox', { name: '修订摘要' }), {
      target: { value: '人工修订后的技术方案摘要' },
    });
    fireEvent.click(within(editApproveModal).getByRole('button', { name: '修改后通过' }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([path]) => path === '/api/reviews/review_api/edit-approve')).toBe(true),
    );
  });

  it('submits rejected review decisions from the task center dialog', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input).startsWith('/api/reviews/pending')) {
        return jsonResponse({
          data: {
            items: [
              {
                ai_task_id: 'task_api',
                content: { summary: 'AI 原始技术方案摘要' },
                id: 'review_api',
                stage: 'technical_solution',
                status: 'pending',
                version: 1,
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/ai-tasks' || (typeof input === 'string' && input.startsWith('/api/ai-tasks?'))) {
        return jsonResponse({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_api',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'waiting_review',
                task_type: 'technical_solution',
                title: '技术方案确认任务',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/reviews/review_api/reject') {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBe(
          JSON.stringify({
            decision_reason: '风险过高，需要重新生成',
            version: 1,
          }),
        );
        return jsonResponse({
          data: { review_status: 'rejected', task_status: 'failed' },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('技术方案确认任务')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '待确认' }));
    expect(await screen.findByText('AI 原始技术方案摘要')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '拒绝并丢弃' }));
    const rejectModalTitle = await screen.findByText('拒绝确认：review_api');
    const rejectModal = rejectModalTitle.closest('.ant-modal') as HTMLElement;
    expect(rejectModal).toHaveTextContent('拒绝后 Runner 会丢弃隔离工作区的代码修改；历史未隔离任务不会自动回滚主工作区。');
    fireEvent.change(screen.getByRole('textbox', { name: '拒绝原因' }), {
      target: { value: '风险过高，需要重新生成' },
    });
    fireEvent.click(within(rejectModal).getByRole('button', { name: '拒绝并丢弃' }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([path]) => path === '/api/reviews/review_api/reject')).toBe(true),
    );
  });

  it('opens task row operations in vertical dialogs aligned with management pages', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input).startsWith('/api/reviews/pending')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (
        input === '/api/products?active_only=true' ||
        input === '/api/products?active_only=true&page_size=100'
      ) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (
        input === '/api/product-versions?active_only=true' ||
        input === '/api/product-versions?active_only=true&page_size=100'
      ) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ai-tasks' || (typeof input === 'string' && input.startsWith('/api/ai-tasks?'))) {
        return jsonResponse({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_solution_done',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'technical_solution',
                title: '技术方案：弹窗操作',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/products/product_api/git-repositories?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              {
                default_branch: 'main',
                git_provider: 'gitlab',
                id: 'repo_api',
                name: 'AI Brain 仓库',
                project_path: 'platform/ai-brain',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/devops/gitlab/merge-requests/repo_api/1/preview') {
        return jsonResponse({
          data: {
            author: { name: 'Alice', username: 'alice' },
            changed_file_count: 2,
            changed_files_summary: [
              { additions: 4, deletions: 1, path: 'apps/api/app/main.py' },
              { additions: 2, deletions: 0, path: 'apps/web/src/pages/TaskCenter/index.tsx' },
            ],
            diff_file_tree: [
              { additions: 6, deletions: 1, file_count: 2, path: 'apps' },
            ],
            mr_iid: 1,
            repository_id: 'repo_api',
            review_checklist: ['确认变更文件归属目标需求和技术方案范围'],
            risk_summary: {
              file_count: 2,
              largest_file: {
                additions: 4,
                deletions: 1,
                line_count: 5,
                path: 'apps/api/app/main.py',
              },
              risk_level: 'low',
              total_additions: 6,
              total_changed_lines: 7,
              total_deletions: 1,
            },
            source_branch: 'feature/review-preview',
            target_branch: 'main',
            title: '任务中心预览 MR',
            writeback_allowed: false,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('技术方案：弹窗操作')).toBeInTheDocument();
    const taskRow = screen.getByText('技术方案：弹窗操作').closest('tr');
    expect(taskRow).not.toBeNull();
    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));

    expect(await screen.findByText('任务操作')).toBeInTheDocument();
    expect(screen.getByTestId('task-operation-summary')).toHaveTextContent('技术方案：弹窗操作');
    expect(screen.queryByText('确认台')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '创建 Code Review' }));

    expect(await screen.findByText(/创建 Code Review：技术方案：弹窗操作/)).toBeInTheDocument();
    const codeReviewForm = screen.getByRole('form', { name: '创建 Code Review 参数' });
    expect(codeReviewForm).toHaveClass('ant-form-vertical');
    expect(codeReviewForm).not.toHaveClass('ant-form-inline');
    expect(screen.getByText('GitLab · AI Brain 仓库 (platform/ai-brain)')).toBeInTheDocument();
    await waitFor(() => {
      const previewButton = screen.getByRole('button', { name: /预览 GitLab MR/ });
      expect(previewButton).toBeEnabled();
      expect(previewButton).not.toHaveClass('ant-btn-loading');
    });
    const previewButton = screen.getByRole('button', { name: /预览 GitLab MR/ });
    fireEvent.click(previewButton);
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([path]) => path === '/api/devops/gitlab/merge-requests/repo_api/1/preview',
        ),
      ).toBe(true),
    );
    expect(await screen.findByText('任务中心预览 MR')).toBeInTheDocument();
    expect(screen.getByText(/低风险 · 2 文件 · \+6\/-1/)).toBeInTheDocument();
    expect(screen.getByText('变更文件树')).toBeInTheDocument();
    expect(screen.getByText(/apps · 2 文件 · \+6\/-1/)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/apps\/api\/app\/main.py · \+4\/-1/)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/确认变更文件归属目标需求和技术方案范围/)).toBeInTheDocument();
  });

  it('offers post-release analysis from completed release readiness rows', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input).startsWith('/api/reviews/pending')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      expect(String(input).startsWith('/api/ai-tasks')).toBe(true);
      expect(String(input).startsWith('/api/ai-tasks/')).toBe(false);
      return jsonResponse({
        data: {
          items: [
            {
              created_by: 'user_admin',
              id: 'task_release_done',
              product_id: 'product_api',
              requirement_id: 'requirement_api',
              status: 'completed',
              task_type: 'release_readiness',
              title: '发布评估：弹窗操作',
            },
          ],
          total: 1,
        },
      });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('发布评估：弹窗操作')).toBeInTheDocument();
    const taskRow = screen.getByText('发布评估：弹窗操作').closest('tr');
    expect(taskRow).not.toBeNull();
    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));

    expect(await screen.findByText('任务操作')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成上线后分析' })).toBeInTheDocument();
  });

  it('opens mock issue writeback from completed task rows', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input).startsWith('/api/reviews/pending')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ai-tasks' || (typeof input === 'string' && input.startsWith('/api/ai-tasks?'))) {
        return jsonResponse({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_solution_done',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'technical_solution',
                title: '技术方案：写回需求',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/writeback/results/task_solution_done' && init?.method !== 'POST') {
        return jsonResponse({
          data: {
            idempotency_key: 'mock_issue:task_solution_done',
            issues: [],
            status: 'not_written',
            task_id: 'task_solution_done',
          },
        });
      }
      if (input === '/api/writeback/results/task_solution_done' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            idempotency_key: 'mock_issue:task_solution_done',
            issues: [
              {
                id: 'mock_issue_api',
                source_task_id: 'task_solution_done',
                status: 'open',
                title: '技术方案：写回需求',
              },
            ],
            status: 'completed',
            task_id: 'task_solution_done',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('技术方案：写回需求')).toBeInTheDocument();
    const taskRow = screen.getByText('技术方案：写回需求').closest('tr');
    expect(taskRow).not.toBeNull();
    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));

    expect(await screen.findByText('任务操作')).toBeInTheDocument();
    expect(screen.getByTestId('task-operation-summary')).toHaveTextContent('技术方案：写回需求');
    expect(screen.getByRole('button', { name: '创建 Code Review' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '模拟 Issue' }));

    expect(await screen.findByText(/模拟 Issue 写回/)).toBeInTheDocument();
    expect(screen.getByText('未写回')).toBeInTheDocument();
    expect(screen.getByText('mock_issue:task_solution_done')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '生成模拟 Issue' }));

    expect(await screen.findByText('已生成')).toBeInTheDocument();
    expect(screen.getByText('mock_issue_api')).toBeInTheDocument();
    const relevantWritebackCalls = fetchMock.mock.calls
      .map(([path, init]) => [
        String(path).startsWith('/api/ai-tasks?')
          ? '/api/ai-tasks'
          : String(path).startsWith('/api/reviews/pending')
            ? '/api/reviews/pending'
            : path,
        init?.method,
      ])
      .filter(([path]) => !String(path).startsWith('/api/products'))
      .filter(([path]) => !String(path).startsWith('/api/product-versions'));
    expect(relevantWritebackCalls).toHaveLength(4);
    expect(relevantWritebackCalls).toContainEqual(['/api/ai-tasks', 'GET']);
    expect(relevantWritebackCalls).toContainEqual(['/api/reviews/pending', 'GET']);
    expect(relevantWritebackCalls).toContainEqual([
      '/api/writeback/results/task_solution_done',
      'GET',
    ]);
    expect(relevantWritebackCalls).toContainEqual([
      '/api/writeback/results/task_solution_done',
      'POST',
    ]);
  });

  it('requests and submits more information from task management dialogs', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/ai-tasks' || (typeof input === 'string' && input.startsWith('/api/ai-tasks?'))) {
        return jsonResponse({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_more_info',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'waiting_more_info',
                task_type: 'product_detail_design',
                title: '待补充详细设计',
              },
            ],
            total: 1,
          },
        });
      }
      if (String(input).startsWith('/api/reviews/pending')) {
        return jsonResponse({
          data: {
            items: [
              {
                ai_task_id: 'task_review',
                content: { summary: '需要人工确认的输出' },
                id: 'review_more_info',
                stage: 'product_detail_design',
                status: 'pending',
                version: 1,
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/reviews/review_more_info/request-more-info') {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toEqual({
          questions: ['请补充验收边界'],
          version: 1,
        });
        return jsonResponse({
          data: {
            review_status: 'requested_more_info',
            task_status: 'waiting_more_info',
          },
        });
      }
      if (input === '/api/ai-tasks/task_more_info/more-info') {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toEqual({
          answers: [{ answer: '补充 P0 验收边界', question: '补充说明' }],
        });
        return jsonResponse({ data: { id: 'task_more_info', status: 'draft' } });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('待补充详细设计')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '待确认' }));
    expect(await screen.findByText('需要人工确认的输出')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '要求补充' }));
    fireEvent.change(screen.getByLabelText('补充问题'), {
      target: { value: '请补充验收边界' },
    });
    fireEvent.click(screen.getByRole('button', { name: '提交补充问题' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/reviews/review_more_info/request-more-info',
        'POST',
      ]),
    );

    const taskRow = screen.getByText('待补充详细设计').closest('tr');
    expect(taskRow).not.toBeNull();
    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));
    expect(await screen.findByText('任务操作')).toBeInTheDocument();
    expect(screen.getByTestId('task-operation-summary')).toHaveTextContent('待补充详细设计');
    fireEvent.click(screen.getByRole('button', { name: '提交补充信息' }));
    fireEvent.change(screen.getByLabelText('补充说明'), {
      target: { value: '补充 P0 验收边界' },
    });
    fireEvent.click(screen.getByRole('button', { name: '提交补充内容' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/ai-tasks/task_more_info/more-info',
        'POST',
      ]),
    );
  });

});
