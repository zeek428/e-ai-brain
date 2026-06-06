import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import BugsPage from '../src/pages/Bugs';
import AuditPage from '../src/pages/Audit';
import DashboardPage from '../src/pages/Dashboard';
import DevopsPage from '../src/pages/Devops';
import InsightsPage from '../src/pages/Insights';
import IterationVersionsPage from '../src/pages/IterationVersions';
import KnowledgePage from '../src/pages/Knowledge';
import ProductsPage from '../src/pages/Products';
import RequirementsPage from '../src/pages/Requirements';
import UsersPage from '../src/pages/Users';
import {
  apiRequest,
  fetchItTeamDashboard,
  generateRequirementTask,
} from '../src/services/aiBrain';
import TaskCenterPage from '../src/pages/TaskCenter';

const roleCatalogEnvelope = {
  data: {
    items: [
      {
        business_roles: ['平台管理员'],
        code: 'admin',
        data_scope: '全平台。',
        decision_scope: '系统治理。',
        description: '负责用户、角色、模型网关、审计与系统级配置管理。',
        is_assignable: true,
        limitations: ['不能代替业务负责人做最终产品决策。'],
        menu_scope: ['系统管理', '审计与运行'],
        name: '系统管理员',
        permissions: ['system.users.manage'],
        responsibilities: ['维护用户和角色。'],
        sort_order: 10,
        status: 'active',
      },
      {
        business_roles: ['只读参与者'],
        code: 'viewer',
        data_scope: '授权范围内的数据。',
        decision_scope: '无写入或审批决策权限。',
        description: '只能查看有权限访问的工作台数据、任务结果、知识和看板摘要。',
        is_assignable: true,
        limitations: ['不能执行写操作、审批或配置变更。'],
        menu_scope: ['首页 IT 团队看板', '授权业务列表'],
        name: '查看者',
        permissions: ['workspace.read'],
        responsibilities: ['查看授权范围内的业务数据。'],
        sort_order: 60,
        status: 'active',
      },
    ],
    total: 2,
  },
};

describe('AI Brain Ant Design Pro workbench', () => {
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

  it('renders the task center from backend tasks without a demo workflow', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/reviews/pending') {
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
      if (input === '/api/products?active_only=true') {
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
      if (input === '/api/product-versions?active_only=true') {
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
    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('任务中心');
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.queryByText('MVP-A 基础 + GitLab 输入闭环')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '运行 MVP 演示流程' })).not.toBeInTheDocument();
    expect(await screen.findByText('接口任务')).toBeInTheDocument();
    expect(screen.getByText('模型网关失败任务')).toBeInTheDocument();
    expect(screen.getAllByText('产品详细设计')).not.toHaveLength(0);
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
      reason: '任务管理批量取消',
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
      reason: '任务管理批量重试',
      task_ids: ['task_retry'],
    });
    expect(await screen.findByRole('dialog', { name: '批量重试结果' })).toBeInTheDocument();
    expect(screen.getByText('ai_task_retry_batch_001')).toBeInTheDocument();
    expect(screen.getByText('failed · model_gateway_failed · MODEL_GATEWAY_FAILED · temporary upstream error')).toBeInTheDocument();
    expect(screen.getByText('TASK_NOT_RETRYABLE · Task is not retryable')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: '批量重试结果' })).not.toBeInTheDocument());

    expect(screen.getByRole('button', { name: '待确认' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '操作' })).toHaveLength(5);
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
    const pendingReviewTable = screen
      .getAllByRole('table')
      .find((table) => table.getAttribute('data-table-scroll-x') === '1040');
    expect(pendingReviewTable).toBeDefined();
    expect(pendingReviewTable).toHaveAttribute('data-table-layout', 'fixed');
    expect(pendingReviewTable).toHaveAttribute('data-table-scroll-x', '1040');
    expect(screen.getAllByText('确认编号')).not.toHaveLength(0);
    expect(within(pendingReviewTable as HTMLElement).getByRole('columnheader', { name: '操作' })).toHaveAttribute(
      'data-fixed',
      'right',
    );
    expect(screen.getByRole('button', { name: '确认通过' })).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
      '/api/reviews/pending',
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
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/reviews/pending') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: 'aibrain', id: 'product_api', name: 'AI Brain 产品' }],
            total: 1,
          },
        });
      }
      if (input === '/api/product-versions?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (
        input === '/api/ai-tasks' ||
        (
          typeof input === 'string' &&
          input.startsWith('/api/ai-tasks?') &&
          !input.includes('product_id=')
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
        typeof input === 'string' &&
        input.startsWith('/api/ai-tasks?') &&
        input.includes('product_id=product_api')
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
      throw new Error(`Unexpected fetch call: ${String(input)}`);
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
      if (input === '/api/reviews/pending') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/products?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/product-versions?active_only=true') {
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
                task_type: 'technical_solution',
                title: '技术方案：详情入口',
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
              product_context: {
                module: { code: 'core', name: '工作台模块' },
                product: { id: 'product_api', name: 'AI Brain 产品' },
                version: { id: 'version_api', name: 'v1 MVP' },
              },
              requirement_snapshot: {
                id: 'requirement_api',
                title: '真实需求快照',
              },
            },
            output: {
              summary: '任务详情输出摘要',
            },
            pending_review: null,
            product_id: 'product_api',
            requirement_id: 'requirement_api',
            status: 'completed',
            task_type: 'technical_solution',
            title: '技术方案：详情入口',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('技术方案：详情入口')).toBeInTheDocument();
    const taskRow = screen.getByText('技术方案：详情入口').closest('tr');
    expect(taskRow).not.toBeNull();
    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));

    expect(await screen.findByText('任务操作')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '查看详情' }));

    expect(await screen.findByText(/任务详情：技术方案：详情入口/)).toBeInTheDocument();
    expect(screen.getByText('AI Brain 产品')).toBeInTheDocument();
    expect(screen.getByText('v1 MVP')).toBeInTheDocument();
    expect(screen.getByText('工作台模块')).toBeInTheDocument();
    expect(screen.getByText('真实需求快照')).toBeInTheDocument();
    expect(screen.getByText('graph_run_api')).toBeInTheDocument();
    expect(screen.getByDisplayValue(/任务详情输出摘要/)).toBeInTheDocument();
    await waitFor(() => {
      const relevantCalls = fetchMock.mock.calls
          .map(([path, init]) => [
            String(path).startsWith('/api/ai-tasks?') ? '/api/ai-tasks' : path,
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
      if (input === '/api/reviews/pending') {
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
      if (input === '/api/reviews/pending') {
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
    fireEvent.click(screen.getByRole('button', { name: '拒绝' }));
    const rejectModalTitle = await screen.findByText('拒绝确认：review_api');
    const rejectModal = rejectModalTitle.closest('.ant-modal') as HTMLElement;
    fireEvent.change(screen.getByRole('textbox', { name: '拒绝原因' }), {
      target: { value: '风险过高，需要重新生成' },
    });
    fireEvent.click(within(rejectModal).getByRole('button', { name: /拒\s*绝/ }));
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
      if (input === '/api/reviews/pending') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/products?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/product-versions?active_only=true') {
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
      if (input === '/api/reviews/pending') {
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
      if (input === '/api/reviews/pending') {
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
          String(path).startsWith('/api/ai-tasks?') ? '/api/ai-tasks' : path,
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
      if (input === '/api/reviews/pending') {
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

  it('renders dashboard and operation pages without placeholder data', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const path = String(input);
      if (input === '/api/dashboard/it-team') {
        return jsonResponse({
          data: {
            latest_tasks: [
              {
                id: 'task_dashboard',
                status: 'waiting_review',
                task_type: 'product_detail_design',
                title: '首页看板任务',
              },
            ],
            pending_reviews: [{ id: 'review_dashboard', stage: 'product_detail_design' }],
            recent_audit_events: [
              { event_type: 'ai_task.started', id: 'audit_dashboard' },
            ],
            recent_knowledge_documents: [{ id: 'knowledge_dashboard', title: '首页知识' }],
            bug_status_counts: [{ count: 2, status: 'open' }],
            gitlab_daily_summary: {
              average_quality_score: 88.5,
              changed_files: 12,
              commit_count: 9,
              merge_request_count: 2,
              metric_count: 1,
              risk_count: 1,
            },
            iteration_suggestion_status_counts: [{ count: 1, status: 'suggested' }],
            jenkins_release_status_counts: [{ count: 1, status: 'failed' }],
            latest_high_severity_bugs: [
              {
                id: 'bug_dashboard',
                severity: 'critical',
                status: 'open',
                title: '首页严重 Bug',
              },
            ],
            online_log_summary: {
              error_count: 4,
              error_rate: 0.02,
              max_p95_latency_ms: 318.5,
              max_p99_latency_ms: 640.25,
              metric_count: 1,
              request_count: 200,
            },
            requirement_status_counts: [
              { count: 1, status: 'submitted' },
              { count: 1, status: 'designing' },
            ],
            summary: {
              active_products: 1,
              ai_tasks: 3,
              audit_events: 8,
              bugs: 2,
              gitlab_commits: 9,
              high_severity_bugs: 1,
              iteration_suggestions: 1,
              jenkins_releases: 1,
              knowledge_deposits: 2,
              knowledge_documents: 4,
              online_errors: 4,
              open_bugs: 2,
              pending_reviews: 1,
              requirements: 5,
              usage_events: 120,
              user_feedback: 3,
            },
            task_status_counts: [{ count: 1, status: 'waiting_review' }],
            time_range: '7d',
            usage_metric_summary: {
              active_users: 42,
              conversion_count: 15,
              error_count: 2,
              event_count: 120,
              metric_count: 1,
            },
            user_feedback_status_counts: [{ count: 3, status: 'open' }],
          },
        });
      }
      if (path.startsWith('/api/devops/operational-metrics')) {
        return jsonResponse({
          data: {
            items: [
              {
                category: 'GitLab 指标',
                id: 'gitlab_metric_dashboard',
                name: '首页仓库指标',
                status: 'collected',
                updated_at: '2026-06-04T08:00:00Z',
                value: 9,
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      if (path.startsWith('/api/insights/items')) {
        return jsonResponse({
          data: {
            items: [
              {
                category: '使用趋势',
                id: 'usage_dashboard',
                status: 'active',
                summary: '首页使用趋势',
                updated_at: '2026-06-04T08:00:00Z',
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    const { rerender } = render(<DashboardPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '欢迎' })).not.toBeInTheDocument();
    expect(screen.queryByText('欢迎使用 AI Brain')).not.toBeInTheDocument();
    expect(screen.queryByText('从左侧菜单进入任务中心、需求交付、产品资产和运营治理。')).not.toBeInTheDocument();
    expect(await screen.findByText('IT 团队看板')).toBeInTheDocument();
    expect(screen.getByText('需求总数')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('首页看板任务')).toBeInTheDocument();
    expect(screen.getByText('首页知识')).toBeInTheDocument();
    expect(screen.getByText('ai_task.started')).toBeInTheDocument();
    expect(screen.getByText('开放 Bug')).toBeInTheDocument();
    expect(screen.getByText('严重 Bug')).toBeInTheDocument();
    expect(screen.getByText('GitLab 提交')).toBeInTheDocument();
    expect(screen.getByText('发布记录')).toBeInTheDocument();
    expect(screen.getByText('用户反馈')).toBeInTheDocument();
    expect(screen.getByText('使用事件')).toBeInTheDocument();
    expect(screen.getAllByText('迭代建议').length).toBeGreaterThan(0);
    expect(screen.getByText('首页严重 Bug')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Bug 明细/ })).toHaveAttribute(
      'href',
      '/delivery/bugs',
    );
    expect(screen.getByRole('link', { name: /运营明细/ })).toHaveAttribute(
      'href',
      '/governance/devops',
    );

    rerender(<DevopsPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '研发运营看板' })).not.toBeInTheDocument();
    expect(screen.queryByText('后续阶段')).not.toBeInTheDocument();
    expect(screen.queryByText('GitLab/Jenkins/线上日志真实运营采集属于后续增强。')).not.toBeInTheDocument();
    expect(screen.queryByText('待接入')).not.toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('运营治理');
    expect(screen.getByText('研发运营指标')).toBeInTheDocument();
    expect(screen.getByText('GitLab 指标')).toBeInTheDocument();
    await waitFor(() => {
      const paths = fetchMock.mock.calls.map(([path]) => String(path));
      expect(paths.some((path) => path.startsWith('/api/devops/operational-metrics'))).toBe(true);
      expect(paths).toEqual(expect.arrayContaining(['/api/products?active_only=true']));
    });

    rerender(<InsightsPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '用户洞察/迭代规划' })).not.toBeInTheDocument();
    expect(screen.getAllByText('用户洞察').length).toBeGreaterThan(0);
    expect(screen.queryByText('后续阶段')).not.toBeInTheDocument();
    expect(screen.queryByText('当前预留入口，后续接入用户使用、反馈和 AI 迭代建议。')).not.toBeInTheDocument();
    expect(screen.queryByText('待接入')).not.toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('运营治理');
    expect(screen.getByText('使用趋势')).toBeInTheDocument();
    await waitFor(() => {
      const paths = fetchMock.mock.calls.map(([path]) => String(path));
      expect(paths.some((path) => path.startsWith('/api/insights/items'))).toBe(true);
    });
  });

  it('reloads the dashboard with a selected product filter', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      if (input === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              { code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' },
              { code: 'ops-platform', id: 'product_ops', name: '运营平台', status: 'active' },
            ],
            total: 2,
          },
        });
      }
      if (input === '/api/dashboard/it-team?product_id=product_api') {
        return jsonResponse({
          data: {
            latest_tasks: [
              {
                id: 'task_product_dashboard',
                status: 'waiting_review',
                task_type: 'technical_solution',
                title: '研发平台筛选任务',
              },
            ],
            pending_reviews: [],
            recent_audit_events: [],
            recent_knowledge_documents: [],
            requirement_status_counts: [{ count: 2, status: 'approved' }],
            summary: {
              active_products: 1,
              ai_tasks: 1,
              audit_events: 0,
              knowledge_deposits: 0,
              knowledge_documents: 0,
              pending_reviews: 0,
              requirements: 2,
            },
            task_status_counts: [{ count: 1, status: 'waiting_review' }],
            time_range: 'all',
          },
        });
      }
      if (input === '/api/dashboard/it-team?product_id=product_api&time_range=7d') {
        return jsonResponse({
          data: {
            latest_tasks: [
              {
                id: 'task_product_dashboard',
                status: 'waiting_review',
                task_type: 'technical_solution',
                title: '研发平台筛选任务',
              },
            ],
            pending_reviews: [],
            recent_audit_events: [],
            recent_knowledge_documents: [],
            requirement_status_counts: [{ count: 2, status: 'approved' }],
            summary: {
              active_products: 1,
              ai_tasks: 1,
              audit_events: 0,
              bugs: 1,
              gitlab_commits: 3,
              high_severity_bugs: 1,
              iteration_suggestions: 1,
              jenkins_releases: 1,
              knowledge_deposits: 0,
              knowledge_documents: 0,
              online_errors: 2,
              open_bugs: 1,
              pending_reviews: 0,
              requirements: 2,
              usage_events: 20,
              user_feedback: 1,
            },
            task_status_counts: [{ count: 1, status: 'waiting_review' }],
            time_range: '7d',
          },
        });
      }
      if (input === '/api/dashboard/it-team') {
        return jsonResponse({
          data: {
            latest_tasks: [],
            pending_reviews: [],
            recent_audit_events: [],
            recent_knowledge_documents: [],
            requirement_status_counts: [],
            summary: {
              active_products: 2,
              ai_tasks: 0,
              audit_events: 0,
              knowledge_deposits: 0,
              knowledge_documents: 0,
              pending_reviews: 0,
              requirements: 0,
            },
            task_status_counts: [],
            time_range: 'all',
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DashboardPage />);

    expect(await screen.findByText('IT 团队看板')).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toContain('/api/products?active_only=true'),
    );
    fireEvent.change(await screen.findByLabelText('产品筛选'), {
      target: { value: 'product_api' },
    });

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toContain(
        '/api/dashboard/it-team?product_id=product_api',
      ),
    );
    fireEvent.change(screen.getByLabelText('时间范围'), {
      target: { value: '7d' },
    });
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toContain(
        '/api/dashboard/it-team?product_id=product_api&time_range=7d',
      ),
    );
    expect(await screen.findByText('研发平台筛选任务')).toBeInTheDocument();
    expect(screen.getAllByText('2')).not.toHaveLength(0);
    expect(screen.getByRole('link', { name: /运营明细/ })).toHaveAttribute(
      'href',
      '/governance/devops?product_id=product_api&time_range=7d',
    );
    expect(screen.getByRole('link', { name: /洞察明细/ })).toHaveAttribute(
      'href',
      '/governance/insights?product_id=product_api&time_range=7d',
    );
    expect(
      fetchMock.mock.calls
        .map(([path]) => String(path))
        .some((path) => path.includes('/versions?active_only=true')),
    ).toBe(false);
  });

  it('renders management modules as query filters with table lists', async () => {
    const { rerender } = render(<ProductsPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('产品资产');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('工作台');
    expect(screen.queryByRole('heading', { level: 1, name: '产品管理' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('产品列表')).toBeInTheDocument();
    expect(screen.getAllByText('产品编码')).not.toHaveLength(0);
    expect(screen.queryByText('AI-BRAIN')).not.toBeInTheDocument();

    rerender(<RequirementsPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('需求交付');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.queryByRole('heading', { level: 1, name: '需求管理' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(
      screen.queryByText('按产品、标题、状态和优先级查询需求台账，并从列表进入审批、关闭和生成 AI 任务操作。'),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('需求列表')).toBeInTheDocument();
    expect(screen.getAllByText('需求标题')).not.toHaveLength(0);
    expect(screen.getByText('创建时间')).toBeInTheDocument();
    expect(screen.queryByText('更新时间')).not.toBeInTheDocument();
    expect(screen.queryByText('产品详细设计辅助')).not.toBeInTheDocument();

    rerender(<BugsPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('需求交付');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.queryByRole('heading', { level: 1, name: 'Bug 管理' })).not.toBeInTheDocument();
    expect(screen.queryByText('MVP 占位数据')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('Bug 列表')).toBeInTheDocument();
    expect(screen.getAllByText('严重级别')).not.toHaveLength(0);
    expect(screen.queryByText('登录态过期提示异常')).not.toBeInTheDocument();

    rerender(<KnowledgePage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('产品资产');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.queryByRole('heading', { level: 1, name: '知识中心' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('知识列表')).toBeInTheDocument();
    expect(screen.getAllByText('知识标题')).not.toHaveLength(0);
    expect(screen.queryByText('AI Brain v1 产品需求文档')).not.toBeInTheDocument();

    rerender(<AuditPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('运营治理');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.queryByRole('heading', { level: 1, name: '审计与运行' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('审计列表')).toBeInTheDocument();
    expect(screen.getAllByText('事件类型')).not.toHaveLength(0);
    expect(screen.queryByText('requirement.approved')).not.toBeInTheDocument();
  });

  it('opens real audit detail and lifecycle trace actions from audit rows', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input) === '/api/audit/events' || String(input).startsWith('/api/audit/events?')) {
        return jsonResponse({
          data: {
            items: [
              {
                actor_id: 'user_admin',
                ai_task_id: 'task_audit',
                created_at: '2026-05-31T08:00:00+00:00',
                event_type: 'requirement.approved',
                id: 'audit_api',
                payload: { comment: '进入设计评审' },
                subject_id: 'requirement_api',
                subject_type: 'requirement',
              },
              {
                actor_id: 'user_admin',
                created_at: '2026-06-01T08:00:00+00:00',
                event_type: 'user_feedback.created',
                id: 'audit_feedback',
                payload: { sentiment: 'negative' },
                subject_id: 'feedback_api',
                subject_type: 'user_feedback',
              },
            ],
            total: 2,
          },
        });
      }
      if (input === '/api/lifecycle/context?subject_type=requirement&subject_id=requirement_api') {
        return jsonResponse({
          data: {
            downstream: [
              {
                relation_type: 'generates_product_detail_design',
                subject_id: 'task_audit',
                subject_type: 'ai_task',
                summary: '产品详细设计：审计链路',
              },
            ],
            missing_context: ['automated_testing'],
            risk_signals: [
              {
                impact_summary: 'Review 中风险',
                recommendation: '补充边界测试',
                risk_type: 'code_review_medium_risk',
                severity: 'medium',
                source_subject_id: 'report_api',
                source_subject_type: 'code_review_report',
              },
            ],
            status: 'available',
            summary: { downstream_count: 1, risk_count: 1 },
            upstream: [],
          },
        });
      }
      if (input === '/api/lifecycle/context?subject_type=user_feedback&subject_id=feedback_api') {
        return jsonResponse({
          data: {
            downstream: [
              {
                relation_type: 'observes_user_feedback',
                subject_id: 'feedback_api',
                subject_type: 'user_feedback',
                summary: '知识检索上线后体验变差。',
              },
              {
                relation_type: 'observes_iteration_suggestion',
                subject_id: 'suggestion_api',
                subject_type: 'iteration_plan_suggestion',
                summary: '优化知识检索体验',
              },
            ],
            missing_context: [],
            risk_signals: [
              {
                impact_summary: '负向用户反馈：知识检索上线后体验变差。',
                recommendation: '纳入迭代建议或 Bug 修复队列。',
                risk_type: 'negative_user_feedback',
                severity: 'medium',
                source_subject_id: 'feedback_api',
                source_subject_type: 'user_feedback',
              },
            ],
            status: 'available',
            summary: { downstream_count: 2, risk_count: 1 },
            upstream: [],
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AuditPage />);

    expect(await screen.findByText('requirement.approved')).toBeInTheDocument();
    const auditRow = screen.getByText('requirement.approved').closest('tr');
    expect(auditRow).not.toBeNull();
    fireEvent.click(within(auditRow as HTMLElement).getByRole('button', { name: '详情' }));
    expect(await screen.findByText('审计详情')).toBeInTheDocument();
    expect(screen.getAllByText('requirement: requirement_api')).not.toHaveLength(0);
    expect(screen.getByText(/进入设计评审/)).toBeInTheDocument();

    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /close/i }));
    fireEvent.click(within(auditRow as HTMLElement).getByRole('button', { name: '链路追踪' }));
    expect(await screen.findByText('generates_product_detail_design')).toBeInTheDocument();
    expect(screen.getByText('code_review_medium_risk')).toBeInTheDocument();
    expect(screen.getByText('code_review_report: report_api')).toBeInTheDocument();
    expect(screen.getByText('automated_testing')).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /close/i }));

    expect(await screen.findByText('user_feedback.created')).toBeInTheDocument();
    const feedbackRow = screen.getByText('user_feedback.created').closest('tr');
    expect(feedbackRow).not.toBeNull();
    fireEvent.click(within(feedbackRow as HTMLElement).getByRole('button', { name: '链路追踪' }));
    expect(await screen.findByText('observes_user_feedback')).toBeInTheDocument();
    expect(screen.getByText('negative_user_feedback')).toBeInTheDocument();
    expect(screen.getAllByText('user_feedback: feedback_api').length).toBeGreaterThanOrEqual(1);
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toContain(
        '/api/lifecycle/context?subject_type=user_feedback&subject_id=feedback_api',
      ),
    );
  });

  it('filters management table rows from query conditions', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const path = String(input);
      if (path.includes('/versions') || path.startsWith('/api/product-versions')) {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      const productItems = [
        {
          code: 'AI-BRAIN',
          id: 'product_ai_brain',
          name: '企业 AI 大脑平台',
          owner_team: 'AI Platform',
          status: 'active',
        },
        {
          code: 'RD-BRAIN',
          id: 'product_rd_brain',
          name: '研发大脑',
          owner_team: 'R&D Enablement',
          status: 'active',
        },
      ].filter((item) => {
        if (!path.includes('code=RD-BRAIN')) {
          return true;
        }
        return item.code === 'RD-BRAIN';
      });
      return new Response(
        JSON.stringify({
          data: {
            items: productItems,
            total: productItems.length,
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

    render(<ProductsPage />);

    expect(await screen.findByText('AI-BRAIN')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('产品编码'), { target: { value: 'RD-BRAIN' } });
    fireEvent.submit(screen.getByRole('form', { name: '查询表格' }));

    expect(await screen.findByText('RD-BRAIN')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('AI-BRAIN')).not.toBeInTheDocument());

    fireEvent.reset(screen.getByRole('form', { name: '查询表格' }));

    expect(await screen.findByText('AI-BRAIN')).toBeInTheDocument();
  });

  it('manages product versions modules and git resources from the product page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });

      if (path === '/api/products' || path.startsWith('/api/products?')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'AI-BRAIN',
                id: 'product_api',
                module_count: 1,
                name: 'AI Brain',
                owner_team: 'AI Platform',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products/product_api/versions' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1 MVP',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/product-versions' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1 MVP',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products/product_api/versions' && method === 'POST') {
        expect(JSON.parse(String(init?.body))).toMatchObject({
          code: 'v2',
          name: 'v2 版本',
          status: 'active',
        });
        return jsonResponse({
          data: {
            code: 'v2',
            id: 'version_new',
            name: 'v2 版本',
            product_id: 'product_api',
            status: 'active',
          },
        });
      }
      if (path === '/api/products/product_api/modules' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'knowledge',
                id: 'module_api',
                name: '知识模块',
                owner_team: 'AI Platform',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products/product_api/modules' && method === 'POST') {
        expect(JSON.parse(String(init?.body))).toMatchObject({
          code: 'planning',
          name: '规划模块',
          owner_team: 'AI Platform',
          status: 'active',
        });
        return jsonResponse({
          data: {
            code: 'planning',
            id: 'module_new',
            name: '规划模块',
            owner_team: 'AI Platform',
            product_id: 'product_api',
            status: 'active',
          },
        });
      }
      if (path === '/api/products/product_api/git-repositories' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                credential_ref_configured: true,
                default_branch: 'main',
                git_provider: 'gitlab',
                id: 'repo_api',
                name: 'AI Brain 仓库',
                project_path: 'platform/ai-brain',
                remote_url: 'https://gitlab.example.com/platform/ai-brain.git',
                repo_type: 'code',
                root_path: '/',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/system/related-systems?product_id=product_api' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'billing',
                id: 'related_system_api',
                name: '计费系统',
                owner_team: 'Business Platform',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/system/related-systems' && method === 'POST') {
        expect(JSON.parse(String(init?.body))).toMatchObject({
          code: 'crm',
          name: 'CRM 系统',
          owner_team: 'Business Platform',
          product_id: 'product_api',
          status: 'active',
        });
        return jsonResponse({
          data: {
            code: 'crm',
            id: 'related_system_new',
            name: 'CRM 系统',
            owner_team: 'Business Platform',
            product_id: 'product_api',
            status: 'active',
          },
        });
      }
      if (path === '/api/products/product_api/git-repositories' && method === 'POST') {
        expect(JSON.parse(String(init?.body))).toMatchObject({
          credential_ref: 'env:GITLAB_READONLY_TOKEN',
          git_provider: 'gitlab',
          name: '测试仓库',
          project_path: 'platform/test',
          remote_url: 'https://gitlab.example.com/platform/test.git',
          status: 'active',
        });
        return jsonResponse({
          data: {
            credential_ref_configured: true,
            default_branch: 'main',
            git_provider: 'gitlab',
            id: 'repo_new',
            name: '测试仓库',
            project_path: 'platform/test',
            remote_url: 'https://gitlab.example.com/platform/test.git',
            repo_type: 'code',
            root_path: '/',
            status: 'active',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${path} ${method}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<ProductsPage />);

    expect(await screen.findByText('AI Brain')).toBeInTheDocument();
    const productRow = screen.getByText('AI Brain').closest('tr');
    expect(productRow).not.toBeNull();
    fireEvent.click(within(productRow as HTMLElement).getByRole('button', { name: '配置' }));

    expect(await screen.findByText(/产品配置：AI Brain/)).toBeInTheDocument();
    expect(screen.getByText('版本管理')).toBeInTheDocument();
    expect(screen.getByText('模块管理')).toBeInTheDocument();
    expect(screen.getByText('Git 资源')).toBeInTheDocument();
    expect(screen.getByText('相关系统')).toBeInTheDocument();
    expect(screen.getAllByText('v1 MVP').length).toBeGreaterThan(0);
    expect(screen.getByText('知识模块')).toBeInTheDocument();
    expect(screen.getByText('platform/ai-brain')).toBeInTheDocument();
    expect(screen.getByText('已配置')).toBeInTheDocument();
    expect(screen.getByText('计费系统')).toBeInTheDocument();
    expect(screen.queryByText('env:GITLAB_READONLY_TOKEN')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '新增版本' }));
    fireEvent.change(screen.getByLabelText('版本编码'), { target: { value: 'v2' } });
    fireEvent.change(screen.getByLabelText('版本名称'), { target: { value: 'v2 版本' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/products/product_api/versions',
        'POST',
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增模块' }));
    fireEvent.change(screen.getByLabelText('模块编码'), { target: { value: 'planning' } });
    fireEvent.change(screen.getByLabelText('模块名称'), { target: { value: '规划模块' } });
    fireEvent.change(screen.getByLabelText('模块负责团队'), { target: { value: 'AI Platform' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/products/product_api/modules',
        'POST',
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增 Git 资源' }));
    fireEvent.change(screen.getByLabelText('资源名称'), { target: { value: '测试仓库' } });
    fireEvent.change(screen.getByLabelText('Remote URL'), {
      target: { value: 'https://gitlab.example.com/platform/test.git' },
    });
    fireEvent.change(screen.getByLabelText('Project Path'), { target: { value: 'platform/test' } });
    fireEvent.change(screen.getByLabelText('凭据引用'), {
      target: { value: 'env:GITLAB_READONLY_TOKEN' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/products/product_api/git-repositories',
        'POST',
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增相关系统' }));
    fireEvent.change(screen.getByLabelText('系统编码'), { target: { value: 'crm' } });
    fireEvent.change(screen.getByLabelText('系统名称'), { target: { value: 'CRM 系统' } });
    fireEvent.change(screen.getByLabelText('系统负责团队'), {
      target: { value: 'Business Platform' },
    });
    expect(screen.getByLabelText('描述')).toHaveAttribute('rows', '3');
    fireEvent.click(screen.getByRole('button', { name: '保存' }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/system/related-systems',
        'POST',
      ]),
    );
  });

  it('saves GitHub provider when editing product Git resources', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if ((path === '/api/products' || path.startsWith('/api/products?')) && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'AI-BRAIN',
                id: 'product_api',
                module_count: 1,
                name: 'AI Brain',
                owner_team: 'AI Platform',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products/product_api/versions' && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/product-versions' && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/products/product_api/modules' && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/system/related-systems?product_id=product_api' && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/products/product_api/git-repositories' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                credential_ref_configured: true,
                default_branch: 'main',
                git_provider: 'gitlab',
                id: 'repo_api',
                name: 'AI Brain 仓库',
                project_path: 'platform/ai-brain',
                remote_url: 'https://gitlab.example.com/platform/ai-brain.git',
                repo_type: 'code',
                root_path: '/',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/product-git-repositories/repo_api' && method === 'PATCH') {
        expect(JSON.parse(String(init?.body))).toMatchObject({
          git_provider: 'github',
          name: 'AI Brain 仓库',
          project_path: 'zeek428/e-ai-brain',
          remote_url: 'git@github.com:zeek428/e-ai-brain.git',
        });
        return jsonResponse({
          data: {
            credential_ref_configured: true,
            default_branch: 'main',
            git_provider: 'github',
            id: 'repo_api',
            name: 'AI Brain 仓库',
            project_path: 'zeek428/e-ai-brain',
            remote_url: 'git@github.com:zeek428/e-ai-brain.git',
            repo_type: 'code',
            root_path: '/',
            status: 'active',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${path} ${method}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<ProductsPage />);

    expect(await screen.findByText('AI Brain')).toBeInTheDocument();
    const productRow = screen.getByText('AI Brain').closest('tr');
    expect(productRow).not.toBeNull();
    fireEvent.click(within(productRow as HTMLElement).getByRole('button', { name: '配置' }));
    const repositoryRow = await screen.findByText('AI Brain 仓库');
    fireEvent.click(
      within(repositoryRow.closest('tr') as HTMLElement).getByRole('button', { name: /编辑/ }),
    );

    fireEvent.mouseDown(screen.getByLabelText('代码平台'));
    fireEvent.click(await screen.findByRole('option', { name: 'GitHub' }));
    fireEvent.change(screen.getByLabelText('Remote URL'), {
      target: { value: 'git@github.com:zeek428/e-ai-brain.git' },
    });
    fireEvent.change(screen.getByLabelText('Project Path'), {
      target: { value: 'zeek428/e-ai-brain' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/product-git-repositories/repo_api',
        'PATCH',
      ]),
    );
  });

  it('does not flash local requirement examples while authenticated data is loading', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    let resolveActiveProducts: (response: Response) => void = () => {};
    let resolveRequirements: (response: Response) => void = () => {};
    let resolveRequirementVersions: (response: Response) => void = () => {};
    const activeProductsPromise = new Promise<Response>((resolve) => {
      resolveActiveProducts = resolve;
    });
    const requirementVersionsPromise = new Promise<Response>((resolve) => {
      resolveRequirementVersions = resolve;
    });
    const requirementsPromise = new Promise<Response>((resolve) => {
      resolveRequirements = resolve;
    });
    const fetchMock = vi.fn<typeof fetch>((input) => {
      const path = String(input);
      if (path === '/api/products?active_only=true') {
        return activeProductsPromise;
      }
      if (path === '/api/product-versions' || path.startsWith('/api/product-versions?')) {
        return requirementVersionsPromise;
      }
      if (path === '/api/requirements' || path.startsWith('/api/requirements?')) {
        return requirementsPromise;
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<RequirementsPage />);

    expect(screen.queryByText('产品详细设计辅助')).not.toBeInTheDocument();

    resolveActiveProducts(jsonResponse({ data: { items: [], total: 0 } }));
    resolveRequirementVersions(jsonResponse({ data: { items: [], total: 0 } }));
    resolveRequirements(jsonResponse({ data: { items: [], total: 0 } }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(screen.queryByText('产品详细设计辅助')).not.toBeInTheDocument();
    expect(screen.queryByText(/接口异常/)).not.toBeInTheDocument();
  });

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
      if (path === '/api/products?active_only=true') {
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
    expect(screen.getByRole('table')).toHaveAttribute('data-table-scroll-x', '1600');
    expect(screen.getByRole('columnheader', { name: '需求标题' })).toHaveAttribute(
      'data-width',
      '260',
    );
    expect(screen.getByRole('columnheader', { name: '操作' })).toHaveAttribute(
      'data-width',
      '164',
    );
    expect(screen.getByText('创建时间')).toBeInTheDocument();
    expect(screen.getByText('2026-06-04 08:00')).toBeInTheDocument();
    expect(screen.getByText('2026-06-04 08:10')).toBeInTheDocument();

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
      if (path === '/api/products?active_only=true') {
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
      '/tasks/management?task_id=task_design',
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

  it('collects demand pool requirements from the iteration version page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
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
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: 'API-PRODUCT', id: 'product_api', name: '接口产品', status: 'active' }],
            total: 1,
          },
        });
      }
      if (path === '/api/product-versions?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-06',
                id: 'version_target',
                name: '2026-06',
                product_id: 'product_api',
                status: 'planning',
              },
            ],
            total: 1,
          },
        });
      }
      if ((path === '/api/requirements' || path.startsWith('/api/requirements?')) && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                content: '需求池内容',
                created_at: '2026-06-04T08:00:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_pool',
                priority: 'P1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'approved',
                title: '需求池待归集',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/requirements/batch-schedule' && method === 'POST') {
        return jsonResponse({
          data: {
            batch_id: 'requirement_batch_002',
            product_id: 'product_api',
            skipped: [],
            skipped_count: 0,
            updated: [],
            updated_count: 1,
            version_id: 'version_target',
          },
        });
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<IterationVersionsPage />);

    const [versionRowText] = await screen.findAllByText('2026-06');
    fireEvent.click(
      within(versionRowText.closest('tr') as HTMLElement).getByRole('button', {
        name: /归集需求/,
      }),
    );
    fireEvent.click(await screen.findByRole('checkbox', { name: /需求池待归集/ }));
    fireEvent.change(screen.getByLabelText('归集原因'), {
      target: { value: '归入版本入口' },
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
      reason: '归入版本入口',
      requirement_ids: ['requirement_pool'],
      version_id: 'version_target',
    });
  });

  it('shows requirements for a testing iteration version without enabling collection', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-08',
                id: 'version_testing',
                name: '2026-08 测试迭代',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: 'AI Brain',
                status: 'testing',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: 'API-PRODUCT', id: 'product_api', name: 'AI Brain', status: 'active' }],
            total: 1,
          },
        });
      }
      if (path === '/api/product-versions?active_only=true') {
        return jsonResponse({
          data: {
            items: [],
            total: 0,
          },
        });
      }
      if ((path === '/api/requirements' || path.startsWith('/api/requirements?')) && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                content: '测试中需求内容',
                created_at: '2026-06-04T08:00:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_testing',
                priority: 'P0',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: 'AI Brain',
                status: 'testing',
                title: '测试中版本需求',
                updated_at: '2026-06-04T09:00:00+00:00',
                version_id: 'version_testing',
                version_name: '2026-08 测试迭代',
              },
              {
                content: '其他版本需求内容',
                created_at: '2026-06-04T08:10:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_other',
                priority: 'P1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: 'AI Brain',
                status: 'code_reviewing',
                title: '其他版本需求',
                updated_at: '2026-06-04T08:30:00+00:00',
                version_id: 'version_other',
                version_name: '2026-07',
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

    render(<IterationVersionsPage />);

    const [versionRowText] = await screen.findAllByText('2026-08');
    const versionRow = versionRowText.closest('tr') as HTMLElement;
    expect(within(versionRow).getByRole('button', { name: /归集需求/ })).toBeDisabled();
    fireEvent.click(within(versionRow).getByRole('button', { name: /查看需求/ }));

    expect(await screen.findByText('查看需求 · 2026-08')).toBeInTheDocument();
    expect(screen.getByText('AI Brain · 2026-08 测试迭代 · 测试中 · 1 条需求')).toBeInTheDocument();
    expect(screen.getByText('测试中版本需求')).toBeInTheDocument();
    expect(screen.getByText('requirement_testing')).toBeInTheDocument();
    expect(screen.queryByText('其他版本需求')).not.toBeInTheDocument();
  });

  it('advances iteration version status with synchronized requirement impact preview', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-07',
                id: 'version_active',
                name: '2026-07',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: 'API-PRODUCT', id: 'product_api', name: '接口产品', status: 'active' }],
            total: 1,
          },
        });
      }
      if (path === '/api/product-versions?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if ((path === '/api/requirements' || path.startsWith('/api/requirements?')) && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                content: '开发尚未完成',
                created_at: '2026-06-04T08:00:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_planned',
                priority: 'P1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'planned',
                title: '同步到测试需求',
                version_id: 'version_active',
                version_name: '2026-07',
              },
              {
                content: '已经完成代码评审',
                created_at: '2026-06-04T08:10:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_reviewed',
                priority: 'P1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'code_reviewing',
                title: '可进入测试需求',
                version_id: 'version_active',
                version_name: '2026-07',
              },
            ],
            total: 2,
          },
        });
      }
      if (path === '/api/product-versions/version_active/advance-status' && method === 'POST') {
        const body = JSON.parse(String(init?.body));
        return jsonResponse({
          data: {
            blocked_requirements: [],
            force: Boolean(body.force),
            from_status: 'active',
            preview_only: Boolean(body.preview_only),
            target_status: 'testing',
            unchanged_requirements: [],
            updated_requirements: [
              {
                from_status: 'planned',
                id: 'requirement_planned',
                title: '同步到测试需求',
                to_status: 'testing',
              },
              {
                from_status: 'code_reviewing',
                id: 'requirement_reviewed',
                title: '可进入测试需求',
                to_status: 'testing',
              },
            ],
            version: {
              code: '2026-07',
              id: 'version_active',
              name: '2026-07',
              product_code: 'API-PRODUCT',
              product_id: 'product_api',
              product_name: '接口产品',
              status: body.preview_only ? 'active' : 'testing',
            },
          },
        });
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<IterationVersionsPage />);

    const [versionRowText] = await screen.findAllByText('2026-07');
    const versionRow = versionRowText.closest('tr') as HTMLElement;
    fireEvent.click(within(versionRow).getByRole('button', { name: /推进状态/ }));

    expect(await screen.findByText('推进版本状态')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '生成影响预览' }));

    expect(await screen.findByText('将推进 2 条需求')).toBeInTheDocument();
    expect(screen.getByText('阻塞 0 条需求')).toBeInTheDocument();
    expect(screen.getByText(/同步到测试需求/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('推进原因'), {
      target: { value: '进入系统测试' },
    });
    fireEvent.click(screen.getByRole('button', { name: '确认推进' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/product-versions/version_active/advance-status',
        'POST',
      ]),
    );
    const advanceCalls = fetchMock.mock.calls.filter(
      ([path, init]) => path === '/api/product-versions/version_active/advance-status' && init?.method === 'POST',
    );
    expect(advanceCalls).toHaveLength(2);
    expect(JSON.parse(String(advanceCalls[0]?.[1]?.body))).toEqual({
      force: false,
      preview_only: true,
      reason: undefined,
      target_status: 'testing',
    });
    expect(JSON.parse(String(advanceCalls[1]?.[1]?.body))).toEqual({
      force: false,
      preview_only: false,
      reason: '进入系统测试',
      target_status: 'testing',
    });
  });

  it('renders executable CRUD buttons on management pages', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const path = String(input);
      if (path === '/api/products' || path.startsWith('/api/products?')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                owner_team: 'API Team',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                owner_team: 'API Team',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions?active_only=true' ||
        path === '/api/product-versions' ||
        path.startsWith('/api/product-versions?')
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/requirements' || path.startsWith('/api/requirements?')) {
        return jsonResponse({
          data: {
            items: [
              {
                id: 'requirement_api',
                priority: 'P1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'submitted',
                title: '接口需求',
                version_id: 'version_api',
                version_name: 'v1',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/bugs' || path.startsWith('/api/bugs?')) {
        return jsonResponse({
          data: {
            items: [
              {
                id: 'bug_api',
                product_id: 'product_api',
                severity: 'major',
                source: 'manual_test',
                status: 'open',
                title: '接口 Bug',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/knowledge/documents' || path.startsWith('/api/knowledge/documents?')) {
        return jsonResponse({
          data: {
            items: [
              {
                id: 'knowledge_api',
                index_status: 'indexed',
                permission_roles: ['admin'],
                title: '接口知识',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/auth/roles') {
        return jsonResponse(roleCatalogEnvelope);
      }
      if (path === '/api/users' || path.startsWith('/api/users?')) {
        return jsonResponse({
          data: {
            items: [
              {
                display_name: '接口用户',
                id: 'user_api',
                roles: ['viewer'],
                status: 'active',
                username: 'viewer@example.com',
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

    const { rerender } = render(<ProductsPage />);

    expect(screen.getByRole('button', { name: /新增产品/ })).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: /编辑/ })).not.toHaveLength(0);
    expect(screen.getAllByRole('button', { name: /删除/ })).not.toHaveLength(0);

    rerender(<RequirementsPage />);
    expect(screen.getByRole('button', { name: /新增需求/ })).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: /全链路/ })).not.toHaveLength(0);
    expect(screen.getAllByRole('button', { name: /更多/ })).not.toHaveLength(0);
    expect(screen.queryByRole('link', { name: /详情页/ })).not.toBeInTheDocument();
    expect(screen.getByRole('table')).toHaveAttribute('data-table-scroll-x', '1600');
    expect(screen.getByRole('columnheader', { name: '需求标题' })).toHaveAttribute(
      'data-width',
      '260',
    );
    expect(screen.getByRole('columnheader', { name: '迭代版本' })).toHaveAttribute(
      'data-width',
      '240',
    );
    expect(screen.getByRole('columnheader', { name: '操作' })).toHaveAttribute(
      'data-width',
      '164',
    );

    rerender(<BugsPage />);
    expect(screen.getByRole('button', { name: /登记 Bug/ })).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: /编辑/ })).not.toHaveLength(0);
    expect(screen.getAllByRole('button', { name: /删除/ })).not.toHaveLength(0);

    rerender(<KnowledgePage />);
    expect(screen.getByRole('button', { name: /导入文档/ })).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: /编辑/ })).not.toHaveLength(0);
    expect(screen.getAllByRole('button', { name: /删除/ })).not.toHaveLength(0);

    rerender(<UsersPage />);
    expect(screen.getByRole('button', { name: /新增用户/ })).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: /编辑/ })).not.toHaveLength(0);
    expect(screen.getAllByRole('button', { name: /删除/ })).not.toHaveLength(0);
  });



  it('hydrates management tables from backend API list endpoints when available', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);

      if (path === '/api/products' || path.startsWith('/api/products?')) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                owner_team: 'API Team',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products?active_only=true') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                owner_team: 'API Team',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions?active_only=true' ||
        path === '/api/product-versions' ||
        path.startsWith('/api/product-versions?')
      ) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/requirements' || path.startsWith('/api/requirements?')) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                created_at: '2026-05-30T08:30:00+00:00',
                id: 'requirement_api',
                priority: 'P0',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'approved',
                title: '接口需求',
                version_id: 'version_api',
                version_name: 'v1',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/knowledge/documents' || path.startsWith('/api/knowledge/documents?')) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                doc_type: 'Spec',
                id: 'knowledge_api',
                index_status: 'indexed',
                permission_roles: ['admin', 'rd_owner'],
                title: '接口知识文档',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/auth/roles') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse(roleCatalogEnvelope);
      }
      if (path === '/api/bugs' || path.startsWith('/api/bugs?')) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                assignee: 'rd_owner@example.com',
                id: 'bug_api',
                module_code: 'knowledge',
                severity: 'critical',
                source: 'ai_post_release',
                status: 'needs_info',
                title: '接口 Bug',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/audit/events' || path.startsWith('/api/audit/events?')) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                actor_id: 'user_admin',
                created_at: '2026-05-30T08:40:00+00:00',
                event_type: 'product.created',
                id: 'audit_api',
                subject_id: 'product_api',
                subject_type: 'product',
              },
            ],
            total: 1,
          },
        });
      }

      throw new Error(`Unexpected fetch call: ${path}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    const { rerender } = render(<ProductsPage />);

    expect(await screen.findByText('API-PRODUCT')).toBeInTheDocument();
    expect(screen.queryByText('AI-BRAIN')).not.toBeInTheDocument();

    rerender(<RequirementsPage />);

    expect(await screen.findByText('接口需求')).toBeInTheDocument();
    expect(screen.getByText('API-PRODUCT')).toBeInTheDocument();

    rerender(<BugsPage />);

    expect(await screen.findByText('接口 Bug')).toBeInTheDocument();
    expect(screen.getAllByText('致命')).not.toHaveLength(0);
    expect(screen.getAllByText('待补充')).not.toHaveLength(0);
    expect(screen.getByText('AI 上线后分析')).toBeInTheDocument();

    rerender(<KnowledgePage />);

    expect(await screen.findByText('接口知识文档')).toBeInTheDocument();
    expect(screen.getByText('admin, rd_owner')).toBeInTheDocument();

    rerender(<AuditPage />);

    expect(await screen.findByText('product.created')).toBeInTheDocument();
    expect(screen.getByText('product: product_api')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith('/api/auth/login', expect.anything());
  });

  it('shows backend load failures without local example rows', async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      new Response(
        JSON.stringify({
          detail: {
            code: 'FORBIDDEN',
            message: 'Role permission denied',
            trace_id: 'trace_denied',
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 403,
        },
      ),
    );
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<ProductsPage />);

    expect(screen.queryByText('AI-BRAIN')).not.toBeInTheDocument();
    expect(await screen.findByText(/接口异常，未加载到数据/)).toBeInTheDocument();
    expect(screen.getByText(/FORBIDDEN/)).toBeInTheDocument();
    expect(screen.getByText(/trace_denied/)).toBeInTheDocument();
  });

  it('preserves backend error code, message and trace id in API failures', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(async () =>
        new Response(
          JSON.stringify({
            detail: {
              code: 'TASK_STATE_INVALID',
              message: 'Task cannot be started from current status',
              trace_id: 'trace_task',
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 409,
          },
        ),
      ),
    );

    await expect(apiRequest('/api/ai-tasks/task_001/start')).rejects.toMatchObject({
      code: 'TASK_STATE_INVALID',
      message: 'Task cannot be started from current status',
      status: 409,
      traceId: 'trace_task',
    });
  });

  it('clears stale login state and redirects to login when an API token expires', async () => {
    window.history.pushState({}, '', '/delivery/requirements?priority=P0');
    window.localStorage.setItem('ai_brain_access_token', 'expired-token');
    window.localStorage.setItem('ai_brain_current_user', JSON.stringify({ username: 'old@example.com' }));
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(async () =>
        new Response(
          JSON.stringify({
            detail: {
              code: 'TOKEN_EXPIRED',
              message: 'Invalid bearer token',
              trace_id: 'trace_expired',
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 401,
          },
        ),
      ),
    );

    await expect(apiRequest('/api/requirements', { token: 'expired-token' })).rejects.toMatchObject({
      code: 'TOKEN_EXPIRED',
      message: 'Invalid bearer token',
      status: 401,
      traceId: 'trace_expired',
    });
    expect(window.localStorage.getItem('ai_brain_access_token')).toBeNull();
    expect(window.localStorage.getItem('ai_brain_current_user')).toBeNull();
    expect(window.location.pathname).toBe('/login');
    expect(window.location.search).toBe(
      '?redirect=%2Fdelivery%2Frequirements%3Fpriority%3DP0',
    );
  });

});
