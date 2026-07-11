import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, expect, it, vi } from 'vitest';

import './proComponentsMock';

import DeploymentsPage from '../src/pages/Deployments';
import { saveCurrentUser } from '../src/services/aiBrain';

afterEach(() => {
  Modal.destroyAll();
  message.destroy();
  notification.destroy();
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it('uses paged deployment data and renders structured execution detail in a drawer', async () => {
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input) => {
    const path = String(input);
    if (path.startsWith('/api/devops/deployments?')) {
      return jsonResponse({
        data: {
          items: [
            {
              current_wave: 1,
              deployment_method: 'docker',
              environment: 'prod',
              executor_channel: 'runner',
              id: 'deployment_001',
              product_id: 'product_001',
              requirement_ids: ['requirement_001'],
              risk_level: 'medium',
              status: 'deploying',
              title: '生产部署',
              total_waves: 2,
              updated_at: '2026-07-11T01:00:00Z',
              version_id: 'version_001',
            },
          ],
          page: 1,
          page_size: 10,
          total: 1,
        },
      });
    }
    if (path === '/api/devops/deployments/deployment_001') {
      return jsonResponse({
        data: {
          audit_events: [
            {
              actor_id: 'execution-worker',
              created_at: '2026-07-11T01:00:05Z',
              event_type: 'deployment.run.dispatched',
              id: 'audit_001',
            },
          ],
          current_wave: 1,
          deployment_method: 'docker',
          dispatch_events: [
            {
              attempt_count: 1,
              event_type: 'deployment_dispatch_requested',
              id: 'outbox_001',
              status: 'completed',
            },
          ],
          environment: 'prod',
          executor_channel: 'runner',
          id: 'deployment_001',
          product_id: 'product_001',
          requirement_ids: ['requirement_001'],
          risk_level: 'medium',
          runs: [
            {
              health_status: 'healthy',
              id: 'run_001',
              operation: 'deploy',
              status: 'running',
              steps: [
                {
                  evidence: { checks: [{ code: 'api', passed: true }] },
                  id: 'step_001',
                  sequence: 3,
                  status: 'passed',
                  step_type: 'health_check',
                  summary: '健康检查通过',
                },
              ],
              wave_number: 1,
              wave_total: 2,
            },
          ],
          status: 'deploying',
          title: '生产部署',
          total_waves: 2,
          version_id: 'version_001',
        },
      });
    }
    if (path.startsWith('/api/devops/deployment-schemes')) {
      return jsonResponse({ data: { items: [], total: 0 } });
    }
    if (path.startsWith('/api/products?active_only=true')) {
      return jsonResponse({
        data: {
          items: [{ code: 'p1', id: 'product_001', name: '研发平台', status: 'active' }],
          total: 1,
        },
      });
    }
    if (path.startsWith('/api/product-versions?active_only=true')) {
      return jsonResponse({
        data: {
          items: [
            {
              code: 'v1',
              id: 'version_001',
              name: '版本 1',
              product_id: 'product_001',
              status: 'active',
            },
          ],
          total: 1,
        },
      });
    }
    return jsonResponse({ data: { items: [], page: 1, page_size: 10, total: 0 } });
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  saveCurrentUser({
    display_name: 'AI Brain Admin',
    id: 'user_admin',
    permissions: ['deployment.read'],
    roles: ['admin'],
    username: 'admin@example.com',
  });
  vi.stubGlobal('fetch', fetchMock);

  render(<DeploymentsPage />);

  expect(await screen.findByText('生产部署')).toBeInTheDocument();
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.some(([path]) =>
        String(path).startsWith('/api/devops/deployments?page=1&page_size=10'),
      ),
    ).toBe(true),
  );
  fireEvent.click(screen.getByRole('button', { name: '详情' }));

  const detailDialog = await screen.findByRole('dialog', { name: '部署详情 · 生产部署' });
  expect(within(detailDialog).getAllByText('第 1 / 2 波')).not.toHaveLength(0);
  expect(within(detailDialog).getByText('健康检查通过')).toBeInTheDocument();
  fireEvent.click(within(detailDialog).getByRole('tab', { name: '派发与审计' }));
  expect(within(detailDialog).getByText('派发记录')).toBeInTheDocument();
  expect(within(detailDialog).getByText('审计记录')).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    '/api/devops/deployments/deployment_001',
    expect.any(Object),
  );
});

it('loads deployment schemes through the paged server read model', async () => {
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input) => {
    const path = String(input);
    if (path.startsWith('/api/devops/deployment-schemes')) {
      return jsonResponse({
        data: {
          items: [
            {
              code: 'prod-manual',
              deployment_method: 'manual',
              environment: 'prod',
              executor_channel: 'manual',
              id: 'scheme_001',
              is_default: true,
              name: '生产人工部署',
              product_id: 'product_001',
              status: 'active',
              timeout_seconds: 1800,
              updated_at: '2026-07-11T01:00:00Z',
              version: 1,
            },
          ],
          page: 1,
          page_size: 10,
          total: 21,
        },
      });
    }
    if (path.startsWith('/api/products?active_only=true')) {
      return jsonResponse({
        data: {
          items: [{ code: 'p1', id: 'product_001', name: '研发平台', status: 'active' }],
          total: 1,
        },
      });
    }
    return jsonResponse({ data: { items: [], page: 1, page_size: 10, total: 0 } });
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  saveCurrentUser({
    display_name: 'AI Brain Admin',
    id: 'user_admin',
    permissions: ['deployment.read', 'deployment.scheme.manage'],
    roles: ['admin'],
    username: 'admin@example.com',
  });
  vi.stubGlobal('fetch', fetchMock);

  render(<DeploymentsPage />);
  fireEvent.click(await screen.findByRole('tab', { name: '部署方案' }));

  expect(await screen.findByText('生产人工部署')).toBeInTheDocument();
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.some(([path]) =>
        String(path).startsWith('/api/devops/deployment-schemes?page=1&page_size=10'),
      ),
    ).toBe(true),
  );
});
