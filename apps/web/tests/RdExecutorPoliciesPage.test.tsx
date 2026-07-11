import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import RdExecutorPoliciesPage from '../src/pages/RdExecutorPolicies';

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json' },
    status: 200,
  });
}

function installFetchMock() {
  const createBodies: unknown[] = [];
  const policyItems = [
    {
      autonomy_mode: 'autonomous_loop',
      auto_merge_risk_threshold: 'low',
      code_change_review_mode: 'manual_review',
      executor_type: 'codex',
      id: 'rd_executor_policy_001',
      instruction_template: '处理 {{task_id}}',
      max_duration_seconds: 3600,
      max_iterations: 3,
      name: '开发计划走 Codex',
      output_contract: { summary: 'string' },
      priority: 10,
      product_id: 'product_001',
      product_name: '研发大脑平台',
      repository_id: 'repo_001',
      repository_name: 'e-ai-brain',
      runner_id: 'runner_codex',
      runner_name: '本地 Codex Runner',
      status: 'active',
      task_type: 'development_planning',
      timeout_seconds: 600,
      updated_at: '2026-06-20T02:00:00Z',
      workspace_root: '/Users/zeek/source/e-ai-brain',
    },
    {
      autonomy_mode: 'single_pass',
      auto_merge_risk_threshold: 'low',
      code_change_review_mode: 'manual_review',
      executor_type: 'codex',
      id: 'rd_executor_policy_002',
      instruction_template: '通用处理 {{task_id}}',
      max_duration_seconds: 3600,
      max_iterations: 1,
      name: '开发计划通用 Codex',
      output_contract: { summary: 'string' },
      priority: 20,
      product_id: null,
      product_name: null,
      runner_id: 'runner_codex',
      runner_name: '本地 Codex Runner',
      status: 'active',
      task_type: 'development_planning',
      timeout_seconds: 600,
      updated_at: '2026-06-20T03:00:00Z',
      workspace_root: '/Users/zeek/source/e-ai-brain',
    },
  ];
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    const url = new URL(String(input), 'http://localhost');
    const method = init?.method ?? 'GET';
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    if (url.pathname === '/api/delivery/rd-task-executor-policies' && method === 'GET') {
      if (!url.searchParams.has('page')) {
        return jsonResponse({
          data: {
            items: policyItems,
            total: policyItems.length,
          },
        });
      }
      expect(url.searchParams.get('page')).toBe('1');
      expect(url.searchParams.get('page_size')).toBe('10');
      expect(url.searchParams.get('sort_by')).toBe('priority');
      return jsonResponse({
        data: {
          items: policyItems,
          total: policyItems.length,
        },
      });
    }
    if (url.pathname === '/api/products' && method === 'GET') {
      return jsonResponse({
        data: {
          items: [{ code: 'rd-platform', id: 'product_001', name: '研发大脑平台', status: 'active' }],
          total: 1,
        },
      });
    }
    if (url.pathname === '/api/product-versions' && method === 'GET') {
      return jsonResponse({ data: { items: [], total: 0 } });
    }
    if (url.pathname === '/api/system/ai-executor-runners' && method === 'GET') {
      expect(url.searchParams.get('status')).toBe('active');
      return jsonResponse({
        data: {
          items: [
            {
              executor_types: ['model_gateway'],
              id: 'ai_executor_runner_system_default',
              name: '系统默认模型执行器',
              status: 'active',
            },
            {
              executor_types: ['codex'],
              id: 'runner_codex',
              name: '本地 Codex Runner',
              status: 'active',
              workspace_roots: ['/Users/zeek/source/e-ai-brain'],
            },
          ],
          total: 2,
        },
      });
    }
    if (url.pathname === '/api/products/product_001/git-repositories' && method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              default_branch: 'master',
              git_url: 'git@example.com:e-ai-brain.git',
              id: 'repo_001',
              name: 'e-ai-brain',
              product_id: 'product_001',
              status: 'active',
            },
          ],
          total: 1,
        },
      });
    }
    if (url.pathname === '/api/delivery/rd-task-executor-policies' && method === 'POST') {
      createBodies.push(JSON.parse(String(init?.body)));
      return jsonResponse({
        data: {
          code_change_review_mode: 'auto_commit',
          executor_type: 'codex',
          id: 'rd_executor_policy_002',
          name: '新增策略',
          priority: 100,
          status: 'active',
          task_type: 'development_planning',
          timeout_seconds: 1800,
          workspace_root: '/Users/zeek/source/e-ai-brain',
        },
      });
    }
    throw new Error(`Unexpected fetch ${String(input)} ${init?.method}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  return { createBodies, fetchMock };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.localStorage.clear();
});

describe('RdExecutorPoliciesPage', () => {
  it('manages delivery executor policies with explicit Agent autonomy governance', async () => {
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.spyOn(message, 'success').mockImplementation(() => null as never);
    vi.spyOn(message, 'error').mockImplementation(() => null as never);
    vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }) as never);
    vi.spyOn(notification, 'error').mockImplementation(() => null as never);
    const { createBodies } = installFetchMock();

    render(<RdExecutorPoliciesPage />);

    expect(await screen.findByText('开发计划走 Codex')).toBeInTheDocument();
    expect(screen.getByText('开发计划通用 Codex')).toBeInTheDocument();
    expect(screen.getAllByText('本地 Codex Runner').length).toBeGreaterThan(0);
    expect(screen.getAllByText('人工确认').length).toBeGreaterThan(0);
    expect(screen.getByText('Agent 自治循环')).toBeInTheDocument();
    expect(screen.getByText('最多 3 轮')).toBeInTheDocument();
    expect(screen.getAllByText('/Users/zeek/source/e-ai-brain').length).toBeGreaterThan(0);
    expect(screen.getByText('命中提示')).toBeInTheDocument();
    expect(screen.getByText('通用兜底')).toBeInTheDocument();
    expect(screen.getByText('同任务类型已有产品专用策略，产品任务会优先命中产品专用策略')).toBeInTheDocument();
    expect(screen.getAllByText('策略名称').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole('button', { name: '保存视图' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /新增策略/ }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('新增研发执行器策略')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('执行器')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Runner')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('代码提交方式')).toBeInTheDocument();
    expect(within(dialog).getByText('执行模式')).toBeInTheDocument();
    expect(within(dialog).getByText('命中预览')).toBeInTheDocument();
    expect(within(dialog).getByText('当前表单策略将作为通用兜底策略')).toBeInTheDocument();
    expect(within(dialog).queryByText('AI角色')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('Skill')).not.toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('任务类型'));
    expect((await screen.findAllByText('PRD / 原型 / 产品详细设计')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('技术方案设计').length).toBeGreaterThan(0);
    const codeImplementationOptions = screen.getAllByText('代码实现 / 开发计划');
    expect(codeImplementationOptions.length).toBeGreaterThan(0);
    expect(screen.getAllByText('Bug 修复').length).toBeGreaterThan(0);
    expect(screen.queryByText('代码巡检整改')).not.toBeInTheDocument();
    expect(screen.queryByText('代码整改')).not.toBeInTheDocument();
    expect(screen.getAllByText('发布上线评估').length).toBeGreaterThan(0);
    expect(screen.getAllByText('上线后分析').length).toBeGreaterThan(0);
    fireEvent.click(codeImplementationOptions[codeImplementationOptions.length - 1]);

    fireEvent.change(within(dialog).getByLabelText('策略名称'), { target: { value: '新增策略' } });
    fireEvent.change(within(dialog).getByLabelText('工作区'), {
      target: { value: '/Users/zeek/source/e-ai-brain' },
    });
    fireEvent.click(within(dialog).getByText('Agent 自治循环'));
    expect(await within(dialog).findByLabelText('最大循环轮次')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('自治时长上限（秒）')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Token 预算')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('费用预算（USD）')).toBeInTheDocument();
    fireEvent.mouseDown(within(dialog).getByLabelText('代码提交方式'));
    fireEvent.click(await screen.findByText('独立门禁通过后自动提交'));
    expect(await within(dialog).findByLabelText('自动合并风险')).toBeInTheDocument();
    fireEvent.mouseDown(within(dialog).getByLabelText('Runner'));
    fireEvent.click(await screen.findByText('本地 Codex Runner (Codex)'));

    fireEvent.click(within(dialog).getByRole('button', { name: 'OK' }));

    await waitFor(() => {
      expect(createBodies).toHaveLength(1);
    });
    expect(createBodies[0]).toMatchObject({
      autonomy_mode: 'autonomous_loop',
      auto_merge_risk_threshold: 'low',
      code_change_review_mode: 'auto_commit',
      executor_type: 'codex',
      name: '新增策略',
      max_duration_seconds: 3600,
      max_iterations: 3,
      runner_id: 'runner_codex',
      task_type: 'development_planning',
      workspace_root: '/Users/zeek/source/e-ai-brain',
    });
    expect(createBodies[0]).not.toHaveProperty('agent_id');
    expect(createBodies[0]).not.toHaveProperty('skill_ids');
  });
});
