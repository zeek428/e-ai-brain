import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import AssistantActionReferencesPage from '../src/pages/AssistantActionReferences';

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json' },
    status: 200,
  });
}

function installFetchMock() {
  const bodies: unknown[] = [];
  const listRequests: string[] = [];
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    if (
      typeof input === 'string'
      && input.startsWith('/api/assistant/action-reference-configs?')
      && init?.method === 'GET'
    ) {
      listRequests.push(input);
      return jsonResponse({
        data: {
          items: [
            {
              action_key: 'create_requirement',
              aliases: ['新建', '需求'],
              enabled: true,
              enterprise_id: null,
              id: 'assistant_action_reference_config_create_requirement',
              metadata_json: { source: 'standard' },
              permissions: [],
              prompt: '我要新建需求',
              roles: ['admin', 'product_owner'],
              rollout_json: {},
              sort_order: 10,
              summary: '进入需求流程',
              template_version: null,
              title: '新建需求',
              url: '/delivery/requirements',
            },
            {
              action_key: 'create_bug',
              aliases: ['新建', 'Bug'],
              enabled: false,
              enterprise_id: null,
              id: 'assistant_action_reference_config_create_bug',
              metadata_json: { source: 'standard' },
              permissions: ['bug.write'],
              prompt: '我要新建 Bug',
              roles: ['tester'],
              rollout_json: {},
              sort_order: 20,
              summary: '进入 Bug 登记流程',
              template_version: null,
              title: '新建 Bug',
              url: '/delivery/bugs',
            },
          ],
          page: 1,
          page_size: 10,
          performance: {
            duration_ms: 12,
            p95_target_ms: 400,
            result_count: 2,
            slow: false,
            slow_threshold_ms: 400,
            total: 2,
          },
          total: 2,
        },
      });
    }
    if (
      typeof input === 'string'
      && input.startsWith('/api/assistant/action-reference-configs/')
      && input.endsWith('/status')
      && init?.method === 'POST'
    ) {
      const requestBody = JSON.parse(String(init.body));
      bodies.push(requestBody);
      const isBug = input.includes('assistant_action_reference_config_create_bug');
      return jsonResponse({
        data: {
          action_key: isBug ? 'create_bug' : 'create_requirement',
          aliases: isBug ? ['新建', 'Bug'] : ['新建', '需求'],
          enabled: requestBody.enabled,
          enterprise_id: null,
          id: isBug
            ? 'assistant_action_reference_config_create_bug'
            : 'assistant_action_reference_config_create_requirement',
          metadata_json: { source: 'standard' },
          permissions: isBug ? ['bug.write'] : [],
          prompt: isBug ? '我要新建 Bug' : '我要新建需求',
          roles: isBug ? ['tester'] : ['admin', 'product_owner'],
          rollout_json: {},
          sort_order: isBug ? 20 : 10,
          summary: isBug ? '进入 Bug 登记流程' : '进入需求流程',
          template_version: null,
          title: isBug ? '新建 Bug' : '新建需求',
          url: isBug ? '/delivery/bugs' : '/delivery/requirements',
        },
      });
    }
    if (
      input === '/api/assistant/action-reference-configs/assistant_action_reference_config_create_requirement/rollout'
      && init?.method === 'PUT'
    ) {
      bodies.push(JSON.parse(String(init.body)));
      return jsonResponse({
        data: {
          action_key: 'create_requirement',
          aliases: ['新建', '需求'],
          enabled: false,
          enterprise_id: 'enterprise_a',
          id: 'assistant_action_reference_config_create_requirement',
          metadata_json: { source: 'standard' },
          permissions: [],
          prompt: '我要新建需求',
          roles: ['admin', 'product_owner'],
          rollout_json: { percentage: 30 },
          sort_order: 10,
          summary: '进入需求流程',
          template_version: '2026.07',
          title: '新建需求',
          url: '/delivery/requirements',
        },
      });
    }
    throw new Error(`Unexpected fetch call: ${String(input)}`);
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  vi.stubGlobal('fetch', fetchMock);
  return { bodies, fetchMock, listRequests };
}

describe('Assistant action references page', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
    void message.destroy();
    notification.destroy();
    Modal.destroyAll();
  });

  it('loads action reference configs and supports status and rollout operations', async () => {
    const { bodies, listRequests } = installFetchMock();

    render(<AssistantActionReferencesPage />);

    await screen.findByText('新建需求');
    expect(listRequests[0]).toContain('page=1');
    expect(listRequests[0]).toContain('page_size=10');
    expect(listRequests[0]).toContain('sort_by=sort_order');
    expect(listRequests[0]).toContain('sort_order=asc');
    expect(screen.getByText('查询 12ms')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '保存视图' })).toBeInTheDocument();
    expect(screen.getByText('create_requirement')).toBeInTheDocument();
    expect(screen.getByText('product_owner')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('停用 新建需求'));
    await waitFor(() => {
      expect(bodies).toContainEqual({ enabled: false });
    });
    expect((await screen.findAllByText('停用')).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByLabelText('配置灰度 新建需求'));
    const rolloutDialog = screen.getByRole('dialog', { name: /@ 能力灰度/ });
    fireEvent.change(within(rolloutDialog).getByLabelText('企业 ID'), {
      target: { value: 'enterprise_a' },
    });
    fireEvent.change(within(rolloutDialog).getByLabelText('模板版本'), {
      target: { value: '2026.07' },
    });
    fireEvent.change(within(rolloutDialog).getByLabelText('灰度比例'), { target: { value: '30' } });
    fireEvent.click(screen.getByText('OK'));

    await waitFor(() => {
      expect(bodies).toContainEqual({
        enterprise_id: 'enterprise_a',
        rollout_json: { percentage: 30 },
        template_version: '2026.07',
      });
    });
  });

  it('supports search filtering and batch status operations', async () => {
    const { bodies, listRequests } = installFetchMock();

    render(<AssistantActionReferencesPage />);

    await screen.findByText('新建需求');
    expect(screen.getByText('新建 Bug')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '保存视图' })).toBeInTheDocument();

    const searchInput = screen.getByLabelText('搜索');
    fireEvent.change(searchInput, {
      target: { value: 'Bug' },
    });
    fireEvent.click(screen.getByRole('button', { name: '查询' }));

    await waitFor(() => {
      expect(listRequests.some((url) => url.includes('keyword=Bug'))).toBe(true);
    });
    expect(screen.getByText('新建 Bug')).toBeInTheDocument();

    fireEvent.change(searchInput, {
      target: { value: '' },
    });
    fireEvent.click(screen.getByRole('button', { name: '查询' }));
    await screen.findByText('新建需求');

    fireEvent.click(screen.getByLabelText('选择 assistant_action_reference_config_create_bug'));
    fireEvent.click(screen.getByRole('button', { name: '批量启用' }));

    await waitFor(() => {
      expect(bodies).toContainEqual({ enabled: true });
    });
  });
});
