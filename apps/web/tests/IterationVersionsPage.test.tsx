import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import IterationVersionsPage from '../src/pages/IterationVersions';

afterEach(() => {
  Modal.destroyAll();
  message.destroy();
  notification.destroy();
  cleanup();
  window.localStorage.clear();
  window.history.pushState({}, '', '/');
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('IterationVersionsPage', () => {
  it('collects demand pool requirements from the iteration version page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-06',
                id: 'version_target',
                name: '2026-06',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'planning',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products?active_only=true' || path === '/api/products?active_only=true&page_size=100') {
        return jsonResponse({
          data: {
            items: [{ code: 'API-PRODUCT', id: 'product_api', name: '接口产品', status: 'active' }],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions?active_only=true' ||
        path === '/api/product-versions?active_only=true&page_size=100'
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-06',
                id: 'version_target',
                name: '2026-06',
                product_id: 'product_api',
                status: 'planning',
              },
            ],
            total: 1,
          },
        });
      }
      if ((path === '/api/requirements' || path.startsWith('/api/requirements?')) && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                content: '需求池内容',
                created_at: '2026-06-04T08:00:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_pool',
                priority: 'P1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'approved',
                title: '需求池待归集',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/requirements/batch-schedule' && method === 'POST') {
        return jsonResponse({
          data: {
            batch_id: 'requirement_batch_002',
            product_id: 'product_api',
            skipped: [],
            skipped_count: 0,
            updated: [],
            updated_count: 1,
            version_id: 'version_target',
          },
        });
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<IterationVersionsPage />);

    const [versionRowText] = await screen.findAllByText('2026-06');
    fireEvent.click(
      within(versionRowText.closest('tr') as HTMLElement).getByRole('button', {
        name: /归集需求/,
      }),
    );
    fireEvent.click(await screen.findByRole('checkbox', { name: /需求池待归集/ }));
    fireEvent.change(screen.getByLabelText('归集原因'), {
      target: { value: '归入版本入口' },
    });
    fireEvent.click(screen.getByRole('button', { name: '确认归集' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/requirements/batch-schedule',
        'POST',
      ]),
    );
    const batchCall = fetchMock.mock.calls.find(
      ([path, init]) => path === '/api/requirements/batch-schedule' && init?.method === 'POST',
    );
    expect(JSON.parse(String(batchCall?.[1]?.body))).toEqual({
      product_id: 'product_api',
      reason: '归入版本入口',
      requirement_ids: ['requirement_pool'],
      version_id: 'version_target',
    });
  });

  it('shows requirements for a testing iteration version without enabling collection', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-08',
                id: 'version_testing',
                name: '2026-08 测试迭代',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: 'AI Brain',
                status: 'testing',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products?active_only=true' || path === '/api/products?active_only=true&page_size=100') {
        return jsonResponse({
          data: {
            items: [{ code: 'API-PRODUCT', id: 'product_api', name: 'AI Brain', status: 'active' }],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions?active_only=true' ||
        path === '/api/product-versions?active_only=true&page_size=100'
      ) {
        return jsonResponse({
          data: {
            items: [],
            total: 0,
          },
        });
      }
      if ((path === '/api/requirements' || path.startsWith('/api/requirements?')) && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                content: '测试中需求内容',
                created_at: '2026-06-04T08:00:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_testing',
                priority: 'P0',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: 'AI Brain',
                status: 'testing',
                title: '测试中版本需求',
                updated_at: '2026-06-04T09:00:00+00:00',
                version_id: 'version_testing',
                version_name: '2026-08 测试迭代',
              },
              {
                content: '其他版本需求内容',
                created_at: '2026-06-04T08:10:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_other',
                priority: 'P1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: 'AI Brain',
                status: 'code_reviewing',
                title: '其他版本需求',
                updated_at: '2026-06-04T08:30:00+00:00',
                version_id: 'version_other',
                version_name: '2026-07',
              },
            ],
            total: 2,
          },
        });
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<IterationVersionsPage />);

    const [versionRowText] = await screen.findAllByText('2026-08');
    const versionRow = versionRowText.closest('tr') as HTMLElement;
    expect(within(versionRow).getByRole('button', { name: /归集需求/ })).toBeDisabled();
    fireEvent.click(within(versionRow).getByRole('button', { name: /查看需求/ }));

    expect(await screen.findByText('查看需求 · 2026-08')).toBeInTheDocument();
    expect(screen.getByText('AI Brain · 2026-08 测试迭代 · 测试中 · 1 条需求')).toBeInTheDocument();
    expect(screen.getByText('测试中版本需求')).toBeInTheDocument();
    expect(screen.getByText('requirement_testing')).toBeInTheDocument();
    expect(screen.queryByText('其他版本需求')).not.toBeInTheDocument();
  });

  it('opens version branch configs from a full-chain branch deep link', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-09',
                id: 'version_branch',
                name: '分支配置迭代',
                product_code: 'AI-BRAIN',
                product_id: 'product_api',
                product_name: 'AI Brain',
                status: 'active',
              },
            ],
            page: 1,
            page_size: 100,
            total: 1,
          },
        });
      }
      if (path === '/api/products?active_only=true' || path === '/api/products?active_only=true&page_size=100') {
        return jsonResponse({
          data: {
            items: [{ code: 'AI-BRAIN', id: 'product_api', name: 'AI Brain', status: 'active' }],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions?active_only=true' ||
        path === '/api/product-versions?active_only=true&page_size=100'
      ) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if ((path === '/api/requirements' || path.startsWith('/api/requirements?')) && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/products/product_api/git-repositories' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                default_branch: 'main',
                git_provider: 'github',
                id: 'repo_web',
                name: 'AI Brain Web',
                project_path: 'zeek428/e-ai-brain',
                remote_url: 'git@github.com:zeek428/e-ai-brain.git',
                repo_type: 'code',
                root_path: '/',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/product-versions/version_branch/branch-configs' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                base_branch: 'main',
                branch_status: 'active',
                creation_source: 'manual',
                id: 'version_branch_config_001',
                product_id: 'product_api',
                repository_id: 'repo_web',
                repository_name: 'AI Brain Web',
                version_id: 'version_branch',
                working_branch: 'release/2026-09',
              },
            ],
            total: 1,
          },
        });
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.history.pushState(
      {},
      '',
      '/delivery/versions?branch_config_id=version_branch_config_001&version_id=version_branch',
    );
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<IterationVersionsPage />);

    expect(await screen.findByText('代码分支 · 2026-09')).toBeInTheDocument();
    expect(await screen.findByText('release/2026-09')).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path]) => path)).toContain(
      '/api/product-versions?page=1&page_size=100&sort_by=code&sort_order=asc',
    );
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
      '/api/product-versions/version_branch/branch-configs',
      'GET',
    ]);
  });

  it('manages version branch configs from the iteration version row', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-09',
                id: 'version_branch',
                name: '分支配置迭代',
                product_code: 'AI-BRAIN',
                product_id: 'product_api',
                product_name: 'AI Brain',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products?active_only=true' || path === '/api/products?active_only=true&page_size=100') {
        return jsonResponse({
          data: {
            items: [{ code: 'AI-BRAIN', id: 'product_api', name: 'AI Brain', status: 'active' }],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions?active_only=true' ||
        path === '/api/product-versions?active_only=true&page_size=100'
      ) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if ((path === '/api/requirements' || path.startsWith('/api/requirements?')) && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/products/product_api/git-repositories' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                default_branch: 'main',
                git_provider: 'github',
                id: 'repo_web',
                name: 'AI Brain Web',
                project_path: 'zeek428/e-ai-brain',
                remote_url: 'git@github.com:zeek428/e-ai-brain.git',
                repo_type: 'code',
                root_path: '/',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/product-versions/version_branch/branch-configs' && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/product-versions/version_branch/branch-configs' && method === 'POST') {
        return jsonResponse({
          data: {
            base_branch: 'main',
            branch_status: 'active',
            creation_source: 'manual',
            id: 'version_branch_config_001',
            product_id: 'product_api',
            repository_id: 'repo_web',
            repository_name: 'AI Brain Web',
            version_id: 'version_branch',
            working_branch: 'release/2026-09',
          },
        });
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<IterationVersionsPage />);

    const [versionRowText] = await screen.findAllByText('2026-09');
    fireEvent.click(
      within(versionRowText.closest('tr') as HTMLElement).getByRole('button', {
        name: /代码分支/,
      }),
    );

    expect(await screen.findByText('代码分支 · 2026-09')).toBeInTheDocument();
    expect(await screen.findByDisplayValue('main')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('开发分支'), {
      target: { value: 'release/2026-09' },
    });
    fireEvent.click(screen.getByRole('button', { name: '新增分支' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/product-versions/version_branch/branch-configs',
        'POST',
      ]),
    );
    const createCall = fetchMock.mock.calls.find(
      ([path, init]) => path === '/api/product-versions/version_branch/branch-configs' && init?.method === 'POST',
    );
    expect(JSON.parse(String(createCall?.[1]?.body))).toEqual({
      base_branch: 'main',
      branch_status: 'not_created',
      creation_source: 'manual',
      repository_id: 'repo_web',
      working_branch: 'release/2026-09',
    });
  });

  it('advances iteration version status with synchronized requirement impact preview', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-07',
                id: 'version_active',
                name: '2026-07',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products?active_only=true' || path === '/api/products?active_only=true&page_size=100') {
        return jsonResponse({
          data: {
            items: [{ code: 'API-PRODUCT', id: 'product_api', name: '接口产品', status: 'active' }],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions?active_only=true' ||
        path === '/api/product-versions?active_only=true&page_size=100'
      ) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if ((path === '/api/requirements' || path.startsWith('/api/requirements?')) && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                content: '开发尚未完成',
                created_at: '2026-06-04T08:00:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_planned',
                priority: 'P1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'planned',
                title: '同步到测试需求',
                version_id: 'version_active',
                version_name: '2026-07',
              },
              {
                content: '已经完成代码评审',
                created_at: '2026-06-04T08:10:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_reviewed',
                priority: 'P1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'code_reviewing',
                title: '可进入测试需求',
                version_id: 'version_active',
                version_name: '2026-07',
              },
            ],
            total: 2,
          },
        });
      }
      if (path === '/api/product-versions/version_active/advance-status' && method === 'POST') {
        const body = JSON.parse(String(init?.body));
        return jsonResponse({
          data: {
            blocked_requirements: [],
            force: Boolean(body.force),
            from_status: 'active',
            preview_only: Boolean(body.preview_only),
            target_status: 'testing',
            unchanged_requirements: [],
            updated_requirements: [
              {
                from_status: 'planned',
                id: 'requirement_planned',
                title: '同步到测试需求',
                to_status: 'testing',
              },
              {
                from_status: 'code_reviewing',
                id: 'requirement_reviewed',
                title: '可进入测试需求',
                to_status: 'testing',
              },
            ],
            version: {
              code: '2026-07',
              id: 'version_active',
              name: '2026-07',
              product_code: 'API-PRODUCT',
              product_id: 'product_api',
              product_name: '接口产品',
              status: body.preview_only ? 'active' : 'testing',
            },
          },
        });
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<IterationVersionsPage />);

    const [versionRowText] = await screen.findAllByText('2026-07');
    const versionRow = versionRowText.closest('tr') as HTMLElement;
    fireEvent.click(within(versionRow).getByRole('button', { name: /推进状态/ }));

    expect(await screen.findByText('推进版本状态')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '生成影响预览' }));

    expect(await screen.findByText('将推进 2 条需求')).toBeInTheDocument();
    expect(screen.getByText('阻塞 0 条需求')).toBeInTheDocument();
    expect(screen.getByText(/同步到测试需求/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('推进原因'), {
      target: { value: '进入系统测试' },
    });
    fireEvent.click(screen.getByRole('button', { name: '确认推进' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/product-versions/version_active/advance-status',
        'POST',
      ]),
    );
    const advanceCalls = fetchMock.mock.calls.filter(
      ([path, init]) => path === '/api/product-versions/version_active/advance-status' && init?.method === 'POST',
    );
    expect(advanceCalls).toHaveLength(2);
    expect(JSON.parse(String(advanceCalls[0]?.[1]?.body))).toEqual({
      force: false,
      preview_only: true,
      reason: undefined,
      target_status: 'testing',
    });
    expect(JSON.parse(String(advanceCalls[1]?.[1]?.body))).toEqual({
      force: false,
      preview_only: false,
      reason: '进入系统测试',
      target_status: 'testing',
    });
  });

});
