import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, expect, it, vi } from 'vitest';

import './proComponentsMock';

import ExecutionResourcesPage from '../src/pages/ExecutionResources';

afterEach(() => {
  Modal.destroyAll();
  message.destroy();
  notification.destroy();
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it('manages product and environment scoped Runner targets with optimistic status updates', async () => {
  const updateBodies: unknown[] = [];
  const response = (body: unknown) => new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json' },
    status: 200,
  });
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    const url = new URL(String(input), 'http://localhost');
    const method = init?.method ?? 'GET';
    if (url.pathname === '/api/system/execution-resources' && method === 'GET') {
      return response({
        data: {
          items: [{
            environment: 'prod',
            id: 'execution_resource_grant_001',
            product_id: 'product_001',
            resource_id: 'runner_001',
            resource_type: 'runner_target',
            status: 'active',
            target_code: 'prod-docker',
            updated_at: '2026-07-11T02:00:00Z',
            version: 2,
          }],
          total: 1,
        },
      });
    }
    if (url.pathname === '/api/products') {
      return response({ data: { items: [{ id: 'product_001', name: '研发大脑平台', status: 'active' }], total: 1 } });
    }
    if (url.pathname === '/api/system/ai-executor-runners') {
      return response({
        data: {
          items: [{
            capabilities: ['deployment'],
            executor_types: ['deployment'],
            id: 'runner_001',
            health_status: 'online',
            metadata: {
              deployment_targets: [{ code: 'prod-docker', method: 'docker', name: '生产 Docker', ready: true }],
            },
            name: '本地部署 Runner',
            status: 'active',
            trust_domain: 'deployment',
          }],
          total: 1,
        },
      });
    }
    if (url.pathname === '/api/system/plugin-connections') {
      return response({ data: { items: [], total: 0 } });
    }
    if (url.pathname === '/api/system/execution-resources/execution_resource_grant_001' && method === 'PUT') {
      updateBodies.push(JSON.parse(String(init?.body)));
      return response({
        data: {
          environment: 'prod',
          id: 'execution_resource_grant_001',
          product_id: 'product_001',
          resource_id: 'runner_001',
          resource_type: 'runner_target',
          status: 'disabled',
          target_code: 'prod-docker',
          version: 3,
        },
      });
    }
    throw new Error(`Unexpected request: ${method} ${url.pathname}${url.search}`);
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  vi.stubGlobal('fetch', fetchMock);

  render(<ExecutionResourcesPage />);

  expect(await screen.findByText('研发大脑平台')).toBeInTheDocument();
  expect(screen.getByText('生产 Docker')).toBeInTheDocument();
  expect(screen.getByText('已就绪')).toBeInTheDocument();
  expect(screen.getAllByText('生产环境').length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole('switch', { name: '停用生产 Docker授权' }));
  await waitFor(() => expect(updateBodies).toEqual([{ status: 'disabled', version: 2 }]));

  fireEvent.click(screen.getByRole('button', { name: /新增授权/ }));
  const dialog = await screen.findByRole('dialog');
  expect(dialog).toHaveTextContent('新增执行资源授权');
  expect(within(dialog).getByLabelText('产品')).toBeInTheDocument();
  expect(within(dialog).getByText('Runner 目标')).toBeInTheDocument();
  expect(within(dialog).getByLabelText('执行资源')).toBeInTheDocument();
});
