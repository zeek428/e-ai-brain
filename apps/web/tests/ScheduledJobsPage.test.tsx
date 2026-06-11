import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import ScheduledJobsPage from '../src/pages/ScheduledJobs';

function installScheduledJobsFetchMock() {
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    if (input === '/api/system/scheduled-jobs' && init?.method === 'GET') {
      return jsonResponse({ data: { items: [], total: 0 } });
    }
    if (input === '/api/system/scheduled-job-runs' && init?.method === 'GET') {
      return jsonResponse({ data: { items: [], total: 0 } });
    }
    if (input === '/api/system/plugin-actions' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              action_type: 'mcp_tool',
              code: 'fetch_weekly_user_feedback',
              id: 'plugin_action_maxcompute',
              name: '获取本周用户反馈数据',
              plugin_id: 'plugin_maxcompute',
              status: 'active',
            },
          ],
          total: 1,
        },
      });
    }
    if (input === '/api/system/plugin-connections' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              environment: 'prod',
              id: 'connection_maxcompute_prod',
              name: '生产 MaxCompute 项目',
              plugin_id: 'plugin_maxcompute',
              status: 'active',
            },
          ],
          total: 1,
        },
      });
    }
    if (input === '/api/products?active_only=true&page_size=100' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [{ code: 'ai-brain', id: 'product_ai_brain', name: 'AI Brain', status: 'active' }],
          total: 1,
        },
      });
    }
    if (input === '/api/system/ai-agents' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [{ code: 'insight_agent', id: 'agent_insight', name: '洞察 Agent', status: 'active' }],
          total: 1,
        },
      });
    }
    if (input === '/api/system/ai-skills' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [{ code: 'weekly_feedback_analysis', id: 'skill_feedback', name: '每周反馈分析', status: 'active' }],
          total: 1,
        },
      });
    }
    throw new Error(`Unexpected fetch call: ${String(input)}`);
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  vi.stubGlobal('fetch', fetchMock);
}

describe('ScheduledJobsPage', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    notification.destroy();
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('uses selectable references instead of requiring raw ids in the create dialog', async () => {
    installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(dialog).getByLabelText('所属产品')).toBeInTheDocument());

    expect(within(dialog).queryByLabelText('产品 ID')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('Agent ID')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('Skill IDs')).not.toBeInTheDocument();
    expect(within(dialog).getByLabelText('Agent')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Skills')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('插件连接')).toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('时间参数'));
    fireEvent.click(await screen.findByText('当前日期 - 7 天'));
    expect(within(dialog).getByDisplayValue('start_pt')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('{{current_date-7}}')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('end_pt')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('{{current_date}}')).toBeInTheDocument();
    expect(within(dialog).queryByLabelText('插件输入映射 JSON')).not.toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: '高级输入映射 JSON 修改' }));
    expect(within(dialog).getByLabelText('插件输入映射 JSON')).toHaveValue(
      JSON.stringify(
        {
          end_pt: '{{current_date}}',
          start_pt: '{{current_date-7}}',
        },
        null,
        2,
      ),
    );
    fireEvent.click(within(dialog).getByRole('button', { name: '从 JSON 应用到表格' }));

    fireEvent.mouseDown(within(dialog).getByLabelText('时间参数'));
    fireEvent.click(await screen.findByText('上一个完整自然周'));
    expect(within(dialog).getByLabelText('插件输入映射 JSON')).toHaveValue(
      JSON.stringify(
        {
          week_end: '{{last_full_week.end}}',
          week_start: '{{last_full_week.start}}',
        },
        null,
        2,
      ),
    );
  });
});
