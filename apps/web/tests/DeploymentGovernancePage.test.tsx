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

it('re-probes an automatic deployment before starting it', async () => {
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    const path = String(input);
    if (path.startsWith('/api/devops/deployments?')) {
      return jsonResponse({
        data: {
          items: [{
            current_wave: 0,
            deployment_method: 'docker',
            environment: 'prod',
            executor_channel: 'runner',
            id: 'deployment_002',
            product_id: 'product_001',
            requirement_ids: ['requirement_001'],
            risk_level: 'medium',
            status: 'approved',
            title: '待启动 Docker 部署',
            total_waves: 1,
            updated_at: '2026-07-14T01:00:00Z',
            version_id: 'version_001',
          }],
          page: 1,
          page_size: 10,
          total: 1,
        },
      });
    }
    if (path === '/api/devops/deployments/deployment_002/connectivity-probe' && init?.method === 'POST') {
      return jsonResponse({
        data: {
          deployment_id: 'deployment_002',
          kind: 'runner',
          max_age_seconds: 600,
          probe: { ready: true, status: 'succeeded' },
          ready: true,
          status: 'succeeded',
        },
      });
    }
    if (path === '/api/devops/deployments/deployment_002/start' && init?.method === 'POST') {
      return jsonResponse({
        data: {
          deployment_method: 'docker',
          environment: 'prod',
          executor_channel: 'runner',
          id: 'deployment_002',
          product_id: 'product_001',
          requirement_ids: ['requirement_001'],
          risk_level: 'medium',
          status: 'deploying',
          title: '待启动 Docker 部署',
          version_id: 'version_001',
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
    if (path.startsWith('/api/product-versions?active_only=true')) {
      return jsonResponse({ data: { items: [], total: 0 } });
    }
    return jsonResponse({ data: { items: [], page: 1, page_size: 10, total: 0 } });
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  saveCurrentUser({
    display_name: 'AI Brain Admin',
    id: 'user_admin',
    permissions: ['deployment.execute', 'deployment.read'],
    roles: ['admin'],
    username: 'admin@example.com',
  });
  vi.stubGlobal('fetch', fetchMock);

  render(<DeploymentsPage />);

  fireEvent.click(await screen.findByRole('button', { name: '探测并启动' }));
  const dialog = await screen.findByRole('dialog', { name: '重新探测并启动部署' });
  fireEvent.click(within(dialog).getByRole('button', { name: '确认部署操作' }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/devops/deployments/deployment_002/connectivity-probe',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/devops/deployments/deployment_002/start',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});

it('keeps failed connectivity probe details actionable with scoped Runner logs and a safe retry', async () => {
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    const path = String(input);
    if (path.startsWith('/api/devops/deployments?')) {
      return jsonResponse({
        data: {
          items: [{
            current_wave: 0,
            deployment_method: 'docker',
            environment: 'prod',
            executor_channel: 'runner',
            id: 'deployment_003',
            product_id: 'product_001',
            requirement_ids: ['requirement_001'],
            risk_level: 'medium',
            status: 'approved',
            title: '探测超时 Docker 部署',
            total_waves: 1,
            updated_at: '2026-07-14T01:00:00Z',
            version_id: 'version_001',
          }],
          page: 1,
          page_size: 10,
          total: 1,
        },
      });
    }
    if (path === '/api/devops/deployments/deployment_003/connectivity-probe' && init?.method === 'POST') {
      return jsonResponse({
        data: {
          deployment_id: 'deployment_003',
          failure: {
            category: 'timeout',
            message: 'Runner 连通性探测超时，请查看日志后重新探测。',
          },
          kind: 'runner',
          log_url: '/api/devops/deployments/deployment_003/connectivity-probe/logs',
          max_age_seconds: 600,
          next_poll_after_seconds: null,
          probe: { error_code: 'AI_EXECUTOR_TASK_TIMEOUT', ready: false, status: 'timed_out' },
          ready: false,
          retry: { allowed: true, after_seconds: 0 },
          status: 'timed_out',
          task: { id: 'runner_task_probe_timeout', status: 'timed_out', timeout_seconds: 60 },
        },
      });
    }
    if (path === '/api/devops/deployments/deployment_003/connectivity-probe/logs') {
      return jsonResponse({
        data: {
          logs: [{ level: 'error', message: 'Docker engine probe timed out', timestamp: '2026-07-14T01:00:00Z' }],
          task: { id: 'runner_task_probe_timeout', status: 'timed_out' },
        },
      });
    }
    if (path.startsWith('/api/products?active_only=true')) {
      return jsonResponse({ data: { items: [{ code: 'p1', id: 'product_001', name: '研发平台', status: 'active' }], total: 1 } });
    }
    if (path.startsWith('/api/product-versions?active_only=true')) {
      return jsonResponse({ data: { items: [], total: 0 } });
    }
    return jsonResponse({ data: { items: [], page: 1, page_size: 10, total: 0 } });
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  saveCurrentUser({
    display_name: 'AI Brain Admin',
    id: 'user_admin',
    permissions: ['deployment.execute', 'deployment.read'],
    roles: ['admin'],
    username: 'admin@example.com',
  });
  vi.stubGlobal('fetch', fetchMock);

  render(<DeploymentsPage />);
  fireEvent.click(await screen.findByRole('button', { name: '探测并启动' }));
  const dialog = await screen.findByRole('dialog', { name: '重新探测并启动部署' });
  fireEvent.click(within(dialog).getByRole('button', { name: '确认部署操作' }));

  expect(await within(dialog).findByText('Runner 连通性探测超时，请查看日志后重新探测。')).toBeInTheDocument();
  expect(within(dialog).getByText('可立即重新探测')).toBeInTheDocument();
  fireEvent.click(within(dialog).getByRole('button', { name: '查看 Runner 日志' }));
  expect(await screen.findByText('Docker engine probe timed out')).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    '/api/devops/deployments/deployment_003/connectivity-probe/logs',
    expect.any(Object),
  );
});
