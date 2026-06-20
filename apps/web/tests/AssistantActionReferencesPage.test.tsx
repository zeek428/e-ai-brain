import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
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
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    if (input === '/api/assistant/action-reference-configs' && init?.method === 'GET') {
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
          ],
          total: 1,
        },
      });
    }
    if (
      input === '/api/assistant/action-reference-configs/assistant_action_reference_config_create_requirement/status'
      && init?.method === 'POST'
    ) {
      bodies.push(JSON.parse(String(init.body)));
      return jsonResponse({
        data: {
          action_key: 'create_requirement',
          aliases: ['新建', '需求'],
          enabled: false,
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
  return { bodies, fetchMock };
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
    const { bodies, fetchMock } = installFetchMock();

    render(<AssistantActionReferencesPage />);

    await screen.findByText('新建需求');
    expect(screen.getByText('create_requirement')).toBeInTheDocument();
    expect(screen.getByText('product_owner')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('停用 新建需求'));
    await waitFor(() => {
      expect(bodies).toContainEqual({ enabled: false });
    });
    expect(await screen.findByText('停用')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('配置灰度 新建需求'));
    fireEvent.change(screen.getByLabelText('企业 ID'), { target: { value: 'enterprise_a' } });
    fireEvent.change(screen.getByLabelText('模板版本'), { target: { value: '2026.07' } });
    fireEvent.change(screen.getByLabelText('灰度比例'), { target: { value: '30' } });
    fireEvent.click(screen.getByText('OK'));

    await waitFor(() => {
      expect(bodies).toContainEqual({
        enterprise_id: 'enterprise_a',
        rollout_json: { percentage: 30 },
        template_version: '2026.07',
      });
    });
    expect(fetchMock).toHaveBeenCalledWith('/api/assistant/action-reference-configs', expect.anything());
  });
});
