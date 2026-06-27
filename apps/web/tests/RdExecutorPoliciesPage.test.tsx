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
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    const url = new URL(String(input), 'http://localhost');
    const method = init?.method ?? 'GET';
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    if (url.pathname === '/api/delivery/rd-task-executor-policies' && method === 'GET') {
      expect(url.searchParams.get('page')).toBe('1');
      expect(url.searchParams.get('page_size')).toBe('10');
      expect(url.searchParams.get('sort_by')).toBe('priority');
      return jsonResponse({
        data: {
          items: [
            {
              executor_type: 'codex',
              id: 'rd_executor_policy_001',
              instruction_template: '处理 {{task_id}}',
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
          ],
          total: 1,
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
  it('manages delivery executor policies without agent or skill fields', async () => {
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.spyOn(message, 'success').mockImplementation(() => null as never);
    vi.spyOn(message, 'error').mockImplementation(() => null as never);
    vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }) as never);
    vi.spyOn(notification, 'error').mockImplementation(() => null as never);
    const { createBodies } = installFetchMock();

    render(<RdExecutorPoliciesPage />);

    expect(await screen.findByText('开发计划走 Codex')).toBeInTheDocument();
    expect(screen.getByText('本地 Codex Runner')).toBeInTheDocument();
    expect(screen.getByText('/Users/zeek/source/e-ai-brain')).toBeInTheDocument();
    expect(screen.getAllByText('策略名称').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole('button', { name: '保存视图' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /新增策略/ }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('新增研发执行器策略')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('执行器')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Runner')).toBeInTheDocument();
    expect(within(dialog).queryByText('AI角色')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('Skill')).not.toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('任务类型'));
    expect((await screen.findAllByText('PRD / 原型 / 产品详细设计')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('技术方案设计').length).toBeGreaterThan(0);
    const codeImplementationOptions = screen.getAllByText('代码实现 / 开发计划');
    expect(codeImplementationOptions.length).toBeGreaterThan(0);
    expect(screen.getAllByText('发布上线评估').length).toBeGreaterThan(0);
    expect(screen.getAllByText('上线后分析').length).toBeGreaterThan(0);
    fireEvent.click(codeImplementationOptions[codeImplementationOptions.length - 1]);

    fireEvent.change(within(dialog).getByLabelText('策略名称'), { target: { value: '新增策略' } });
    fireEvent.change(within(dialog).getByLabelText('工作区'), {
      target: { value: '/Users/zeek/source/e-ai-brain' },
    });
    fireEvent.mouseDown(within(dialog).getByLabelText('Runner'));
    fireEvent.click(await screen.findByText('本地 Codex Runner (Codex)'));

    fireEvent.click(within(dialog).getByRole('button', { name: 'OK' }));

    await waitFor(() => {
      expect(createBodies).toHaveLength(1);
    });
    expect(createBodies[0]).toMatchObject({
      executor_type: 'codex',
      name: '新增策略',
      runner_id: 'runner_codex',
      task_type: 'development_planning',
      workspace_root: '/Users/zeek/source/e-ai-brain',
    });
    expect(createBodies[0]).not.toHaveProperty('agent_id');
    expect(createBodies[0]).not.toHaveProperty('skill_ids');
  });
});
