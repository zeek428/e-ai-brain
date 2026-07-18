import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message } from 'antd';
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
      return jsonResponse({
        data: {
          items: [
            {
              assessment_config: {},
              autonomy_config: {},
              brain_app_id: 'rd_brain',
              delivery_target: 'ready_for_release',
              experience_reuse_config: {},
              git_config: {},
              id: 'policy_001',
              iteration_config: {},
              matching_config: { task_types: ['requirement_assessment', 'development_planning'] },
              name: '团队协同交付',
              policy_version: 2,
              quality_gate_config: {},
              role_bindings: [{ actor_mode: 'ai', role_code: 'developer', status: 'active' }],
              status: 'active',
              team_config: { required_role_codes: ['developer'] },
            },
          ],
          total: 1,
        },
      });
    }
    if (url.pathname === '/api/delivery/rd-roles' && method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              assignable_subject_types: ['human_user', 'ai_employee'],
              capabilities: ['code'],
              code: 'developer',
              id: 'role_developer',
              maximum_risk_level: 'medium',
              name: '开发',
              responsibilities: ['实现'],
              status: 'active',
            },
          ],
        },
      });
    }
    if (url.pathname === '/api/delivery/rd-ai-employees' && method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              capability_tags: ['开发'],
              code: 'ai_developer',
              id: 'employee_001',
              name: '开发数字员工',
              persona_version: 1,
              status: 'active',
              work_style_version: 1,
            },
          ],
        },
      });
    }
    if (url.pathname === '/api/delivery/rd-executor-profiles' && method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              code: 'codex_developer',
              executor_type: 'codex',
              health_status: 'healthy',
              id: 'profile_001',
              name: '受控 Codex 开发配置',
              runner_id: 'runner_001',
              status: 'active',
              supported_role_codes: ['developer'],
            },
          ],
        },
      });
    }
    if (url.pathname === '/api/delivery/rd-task-executor-policies' && method === 'POST') {
      const body = JSON.parse(String(init?.body));
      createBodies.push(body);
      return jsonResponse({ data: { policy: { ...body, id: 'policy_002', policy_version: 1 } } });
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
  it('keeps legacy policies readable when they do not yet contain team role bindings', async () => {
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    const { fetchMock } = installFetchMock();
    fetchMock.mockImplementationOnce(async () => jsonResponse({
      data: {
        items: [
          {
            assessment_config: {},
            autonomy_config: {},
            brain_app_id: 'rd_brain',
            delivery_target: 'ready_for_release',
            experience_reuse_config: {},
            git_config: {},
            id: 'policy_legacy',
            iteration_config: {},
            matching_config: { task_types: ['development_planning'] },
            name: '历史策略（待转换）',
            policy_version: 1,
            quality_gate_config: {},
            status: 'disabled',
            team_config: {},
          },
        ],
        total: 1,
      },
    }));

    render(<RdExecutorPoliciesPage />);

    expect(await screen.findByText('历史策略（待转换）')).toBeInTheDocument();
    expect(screen.getByText('统一研发执行策略')).toBeInTheDocument();
    expect(screen.queryByText('Something went wrong.')).not.toBeInTheDocument();
  });

  it('presents one policy-controlled R&D team without exposing deployment', async () => {
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    installFetchMock();

    render(<RdExecutorPoliciesPage />);

    expect(await screen.findByText('统一研发执行策略')).toBeInTheDocument();
    expect(screen.getByText('团队协同交付')).toBeInTheDocument();
    expect(screen.getByText('推送远程仓库并待发布')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'AI 数字员工（1）' })).toBeInTheDocument();
    expect(screen.queryByText('执行器')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '启用部署' })).not.toBeInTheDocument();
  });

  it('creates a governed policy with roles, not legacy task executor fields', async () => {
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.spyOn(message, 'success').mockImplementation(() => null as never);
    const { createBodies } = installFetchMock();

    render(<RdExecutorPoliciesPage />);
    await screen.findByText('团队协同交付');
    fireEvent.click(screen.getByRole('button', { name: '新增研发执行策略' }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('策略名称'), { target: { value: '新团队策略' } });

    fireEvent.mouseDown(within(dialog).getByLabelText('参与岗位'));
    fireEvent.click(await screen.findByText('开发（developer）'));
    fireEvent.mouseDown(within(dialog).getByLabelText('developer AI数字员工'));
    fireEvent.click(await screen.findByText('开发数字员工（ai_developer）'));
    fireEvent.mouseDown(within(dialog).getByLabelText('developer 执行配置'));
    const profileOptions = await screen.findAllByText('受控 Codex 开发配置（codex）');
    fireEvent.click(profileOptions[profileOptions.length - 1]);
    fireEvent.click(within(dialog).getByRole('button', { name: 'OK' }));

    await waitFor(() => expect(createBodies).toHaveLength(1));
    expect(createBodies[0]).toMatchObject({
      delivery_target: 'ready_for_release',
      git_config: { prohibit_deployment: true, push_remote: true },
      team_config: { required_role_codes: ['developer'] },
    });
    expect(createBodies[0]).not.toHaveProperty('executor_type');
    expect(createBodies[0]).not.toHaveProperty('task_type');
  });
});
