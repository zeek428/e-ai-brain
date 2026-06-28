import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import AssistantRoleQuickTasksPage from '../src/pages/AssistantRoleQuickTasks';

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json' },
    status: 200,
  });
}

describe('AssistantRoleQuickTasksPage', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    notification.destroy();
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it('lists, toggles, and updates rollout for assistant quick task configs', async () => {
    const listRequests: string[] = [];
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (
        typeof input === 'string'
        && input.startsWith('/api/assistant/role-quick-task-configs?')
        && init?.method === 'GET'
      ) {
        listRequests.push(input);
        return jsonResponse({
          data: {
            items: [
              {
                analytics_key: 'admin.scheduled_jobs',
                enabled: true,
                enterprise_id: 'enterprise_a',
                group_enabled: true,
                group_key: 'admin',
                group_label: '管理员快捷任务',
                group_roles: ['admin'],
                group_sort_order: 50,
                id: 'assistant_role_quick_task_admin_jobs',
                permissions: ['system.scheduled_jobs.manage'],
                prompt: '请汇总定时作业配置',
                rollout_json: { percentage: 50 },
                sort_order: 30,
                target_draft_type: 'create_scheduled_job',
                task_key: 'scheduled_jobs',
                template_version: '2026.06',
                title: '定时作业',
              },
            ],
            page: 1,
            page_size: 10,
            performance: {
              duration_ms: 13,
              p95_target_ms: 400,
              result_count: 1,
              slow: false,
              slow_threshold_ms: 400,
              total: 1,
            },
            total: 1,
          },
        });
      }
      if (
        input === '/api/assistant/role-quick-task-configs/assistant_role_quick_task_admin_jobs/status'
        && init?.method === 'POST'
      ) {
        expect(JSON.parse(String(init.body))).toMatchObject({ enabled: false });
        return jsonResponse({
          data: {
            enabled: false,
            group_enabled: true,
            group_key: 'admin',
            group_label: '管理员快捷任务',
            group_roles: ['admin'],
            id: 'assistant_role_quick_task_admin_jobs',
            permissions: ['system.scheduled_jobs.manage'],
            prompt: '请汇总定时作业配置',
            rollout_json: { percentage: 50 },
            task_key: 'scheduled_jobs',
            title: '定时作业',
          },
        });
      }
      if (
        input === '/api/assistant/role-quick-task-configs/assistant_role_quick_task_admin_jobs/rollout'
        && init?.method === 'PUT'
      ) {
        expect(JSON.parse(String(init.body))).toEqual({
          enterprise_id: 'enterprise_b',
          rollout_json: { percentage: 25 },
          template_version: '2026.07',
        });
        return jsonResponse({
          data: {
            enabled: false,
            enterprise_id: 'enterprise_b',
            group_enabled: true,
            group_key: 'admin',
            group_label: '管理员快捷任务',
            group_roles: ['admin'],
            id: 'assistant_role_quick_task_admin_jobs',
            permissions: ['system.scheduled_jobs.manage'],
            prompt: '请汇总定时作业配置',
            rollout_json: { percentage: 25 },
            task_key: 'scheduled_jobs',
            template_version: '2026.07',
            title: '定时作业',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantRoleQuickTasksPage />);

    expect(await screen.findByRole('heading', { name: 'AI助手快捷任务配置' })).toBeInTheDocument();
    expect(listRequests.length).toBeGreaterThan(0);
    expect(listRequests[0] ?? '').toContain('page=1');
    expect(listRequests[0] ?? '').toContain('page_size=10');
    expect(listRequests[0] ?? '').toContain('sort_by=group_sort_order');
    expect(listRequests[0] ?? '').toContain('sort_order=asc');
    expect(screen.getByText('查询 13ms')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '保存视图' })).toBeInTheDocument();
    expect(screen.getByText('管理员快捷任务')).toBeInTheDocument();
    expect(screen.getByText('定时作业')).toBeInTheDocument();
    expect(screen.getByText('enterprise_a')).toBeInTheDocument();
    expect(screen.getByText('2026.06')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '停用 定时作业' }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/assistant/role-quick-task-configs/assistant_role_quick_task_admin_jobs/status',
        expect.objectContaining({ method: 'POST' }),
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: '配置灰度 定时作业' }));
    const dialog = await screen.findByRole('dialog', { name: '快捷任务灰度 · 定时作业' });
    fireEvent.change(within(dialog).getByLabelText('企业 ID'), {
      target: { value: 'enterprise_b' },
    });
    fireEvent.change(within(dialog).getByLabelText('模板版本'), {
      target: { value: '2026.07' },
    });
    fireEvent.change(within(dialog).getByLabelText('灰度比例'), {
      target: { value: '25' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/assistant/role-quick-task-configs/assistant_role_quick_task_admin_jobs/rollout',
        expect.objectContaining({ method: 'PUT' }),
      ),
    );
  });
});
