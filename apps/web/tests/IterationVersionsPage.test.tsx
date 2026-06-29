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
      expect(init?.headers).toMatchObject({
        Authorization: 'Bearer token-admin',
      });
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
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                status: 'active',
              },
            ],
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
      expect(init?.headers).toMatchObject({
        Authorization: 'Bearer token-admin',
      });
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
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: 'AI Brain',
                status: 'active',
              },
            ],
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
      expect(init?.headers).toMatchObject({
        Authorization: 'Bearer token-admin',
      });
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
            items: [
              {
                code: 'AI-BRAIN',
                id: 'product_api',
                name: 'AI Brain',
                status: 'active',
              },
            ],
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
    const branchText = await screen.findByText('release/2026-09');
    expect(branchText).toBeInTheDocument();
    expect(
      within(branchText.closest('tr') as HTMLElement).getByRole('link', {
        name: '全链路',
      }),
    ).toHaveAttribute(
      'href',
      '/delivery/full-chain?subject_id=version_branch_config_001&subject_type=product_version_branch_config',
    );
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
      expect(init?.headers).toMatchObject({
        Authorization: 'Bearer token-admin',
      });
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
            items: [
              {
                code: 'AI-BRAIN',
                id: 'product_api',
                name: 'AI Brain',
                status: 'active',
              },
            ],
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
      expect(init?.headers).toMatchObject({
        Authorization: 'Bearer token-admin',
      });
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
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                status: 'active',
              },
            ],
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

  it('opens the product version dashboard with delivery blockers and linked records', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({
        Authorization: 'Bearer token-admin',
      });
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-dashboard',
                id: 'version_dashboard',
                name: '驾驶舱迭代',
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
            items: [
              {
                code: 'AI-BRAIN',
                id: 'product_api',
                name: 'AI Brain',
                status: 'active',
              },
            ],
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
      if (path === '/api/product-versions/version_dashboard/dashboard' && method === 'GET') {
        return jsonResponse({
          data: {
            access_issues: [],
            blockers: [
              {
                action_label: '处理 Bug',
                action_target_id: 'bug_dashboard',
                action_target_type: 'bug',
                id: 'bug_dashboard',
                reason: 'critical Bug 仍未关闭',
                resolution_hint: '修复、验证并关闭 blocker/critical Bug 后解除发布阻塞。',
                severity: 'high',
                source_type: 'bug',
                title: '发布阻塞 Bug',
              },
              {
                action_label: '维护分支',
                action_target_id: 'version_branch_dashboard',
                action_target_type: 'product_version_branch_config',
                id: 'version_branch_dashboard',
                reason: '分支状态 not_created 不满足版本推进到 testing 的要求',
                resolution_hint: '创建或推进版本分支状态，使其满足测试/发布准入要求。',
                severity: 'medium',
                source_type: 'product_version_branch_config',
                title: 'release/2026-dashboard',
              },
              {
                action_label: '排查发布',
                action_target_id: 'version_dashboard',
                action_target_type: 'product_version',
                id: null,
                reason: '缺少成功发布记录，不能确认版本已完成发布。',
                resolution_hint: '登记或同步成功发布记录后解除发布阻塞。',
                severity: 'high',
                source_type: 'jenkins_release',
                title: '缺少成功发布记录',
              },
            ],
            branch_configs: [
              {
                base_branch: 'main',
                branch_status: 'not_created',
                creation_source: 'manual',
                id: 'version_branch_dashboard',
                product_id: 'product_api',
                repository_id: 'repo_dashboard',
                repository_name: 'Dashboard Repo',
                version_id: 'version_dashboard',
                working_branch: 'release/2026-dashboard',
              },
            ],
            bugs: [
              {
                assignee: 'qa_owner',
                created_at: '2026-06-04T09:10:00+00:00',
                id: 'bug_dashboard',
                module_code: 'delivery',
                product_id: 'product_api',
                severity: 'critical',
                source: 'code_inspection',
                status: 'open',
                title: '发布阻塞 Bug',
                version_id: 'version_dashboard',
                version_name: '驾驶舱迭代',
              },
            ],
            bug_status_counts: [{ count: 1, status: 'open' }],
            code_inspection_reports: [
              {
                branch: 'release/2026-dashboard',
                created_at: '2026-06-04T09:30:00+00:00',
                finding_count: 3,
                id: 'code_inspection_report_dashboard',
                product_id: 'product_api',
                repository_id: 'repo_dashboard',
                repository_name: 'Dashboard Repo',
                risk_level: 'high',
                severe_finding_count: 1,
                status: 'completed',
                summary: '存在高风险问题',
              },
            ],
            code_review_reports: [
              {
                executor: { name: 'codex', type: 'local' },
                finding_count: 1,
                gitlab_mr_snapshot_id: 'gitlab_mr_snapshot_dashboard',
                id: 'code_review_report_dashboard',
                review_id: 'review_dashboard',
                risk_level: 'medium',
                status: 'pending_review',
                summary: '代码评审待确认',
                task_id: 'task_dashboard',
                task_title: '实现版本驾驶舱',
              },
            ],
            knowledge_deposits: [
              {
                ai_task_id: 'task_dashboard',
                id: 'knowledge_deposit_dashboard',
                knowledge_chunk_count: 1,
                knowledge_document_id: 'knowledge_document_dashboard',
                knowledge_document_title: '版本驾驶舱知识文档',
                knowledge_embedding_chunk_count: 0,
                knowledge_index_error: 'Embedding 网关未配置，已降级为关键词检索。',
                knowledge_index_status: 'text_indexed',
                knowledge_retrieval_mode: 'keyword',
                status: 'approved',
                task_title: '实现版本驾驶舱',
                title: '版本驾驶舱知识沉淀',
                updated_at: '2026-06-04T09:40:00+00:00',
              },
            ],
            releases: [
              {
                build_id: '42',
                created_at: '2026-06-04T10:00:00+00:00',
                id: 'release_dashboard',
                job_name: 'deploy-dashboard',
                status: 'failed',
              },
            ],
            requirement_status_counts: [
              { count: 1, status: 'developing' },
              { count: 1, status: 'submitted' },
            ],
            requirements: [
              {
                content: '驾驶舱需求内容',
                created_at: '2026-06-04T08:00:00+00:00',
                created_by: 'user_admin',
                id: 'requirement_dashboard',
                priority: 'P1',
                product_code: 'AI-BRAIN',
                product_id: 'product_api',
                product_name: 'AI Brain',
                status: 'developing',
                title: '驾驶舱需求',
                updated_at: '2026-06-04T09:00:00+00:00',
                version_id: 'version_dashboard',
                version_name: '驾驶舱迭代',
              },
            ],
            status_impact: {
              blocked_requirements: [
                {
                  block_reason: '需求仍待评审，不能进入测试',
                  id: 'requirement_blocked',
                  status: 'submitted',
                  title: '待评审需求',
                },
              ],
              target_status: 'testing',
              unchanged_requirements: [
                {
                  id: 'requirement_unchanged',
                  status: 'cancelled',
                  title: '已取消需求',
                },
              ],
              updated_requirements: [
                {
                  from_status: 'developing',
                  id: 'requirement_dashboard',
                  title: '驾驶舱需求',
                  to_status: 'testing',
                },
              ],
            },
            summary: {
              blockers: 3,
              branch_configs: 1,
              bugs: 1,
              code_inspection_reports: 1,
              code_review_reports: 1,
              knowledge_deposits: 1,
              open_bugs: 1,
              pending_code_review_reports: 1,
              releases: 1,
              requirements: 1,
              searchable_knowledge_deposits: 1,
              severe_bugs: 1,
              severe_code_inspection_reports: 1,
              tasks: 1,
              vectorized_knowledge_deposits: 0,
            },
            task_status_counts: [{ count: 1, status: 'running' }],
            tasks: [
              {
                created_at: '2026-06-04T08:20:00+00:00',
                created_by: 'user_admin',
                id: 'task_dashboard',
                product_id: 'product_api',
                product_name: 'AI Brain',
                requirement_id: 'requirement_dashboard',
                status: 'running',
                task_type: 'implementation',
                title: '实现版本驾驶舱',
                version_id: 'version_dashboard',
              },
            ],
            version: {
              code: '2026-dashboard',
              id: 'version_dashboard',
              name: '驾驶舱迭代',
              product_code: 'AI-BRAIN',
              product_id: 'product_api',
              product_name: 'AI Brain',
              status: 'active',
            },
          },
        });
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<IterationVersionsPage />);

    const [versionRowText] = await screen.findAllByText('2026-dashboard');
    fireEvent.click(
      within(versionRowText.closest('tr') as HTMLElement).getByRole('button', {
        name: /总览/,
      }),
    );

    expect(await screen.findByText('版本总览 · 2026-dashboard')).toBeInTheDocument();
    expect(screen.getByText('下一步行动')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /推进到测试中/ })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /查看需求/ }).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: /维护分支/ })).toBeInTheDocument();
    expect(screen.getByText('下一阶段：测试中')).toBeInTheDocument();
    expect(screen.getByText('发布准备清单')).toBeInTheDocument();
    expect(screen.getByText('需求范围')).toBeInTheDocument();
    expect(screen.getByText('1 条需求 · 阻塞 1 条')).toBeInTheDocument();
    expect(screen.getByText('研发任务')).toBeInTheDocument();
    expect(screen.getByText('1 个任务 · 运行中 1 个')).toBeInTheDocument();
    expect(screen.getAllByText('代码分支').length).toBeGreaterThan(0);
    expect(screen.getByText('1 个分支 · 未创建 1 个')).toBeInTheDocument();
    expect(screen.getAllByText('代码巡检').length).toBeGreaterThan(0);
    expect(screen.getByText('1 份报告 · 高风险 1 份')).toBeInTheDocument();
    expect(screen.getAllByText('代码评审').length).toBeGreaterThan(0);
    expect(screen.getByText('1 份报告 · 待确认 1 份')).toBeInTheDocument();
    expect(screen.getByText('Bug 收敛')).toBeInTheDocument();
    expect(screen.getByText('1 个 Bug · 未关闭 1 个')).toBeInTheDocument();
    expect(screen.getByText('1 条知识沉淀 · 可检索 1 条 · 向量就绪 0 条')).toBeInTheDocument();
    expect(screen.getByText('发布证据')).toBeInTheDocument();
    expect(screen.getByText('1 条记录 · 发布阻塞 1 个')).toBeInTheDocument();
    expect(screen.getByText('状态推进')).toBeInTheDocument();
    expect(screen.getByText('同步 1 / 阻塞 1 / 保持 1')).toBeInTheDocument();
    expect(screen.getByText('交付健康摘要')).toBeInTheDocument();
    expect(screen.getByText('发布准入')).toBeInTheDocument();
    expect(screen.getByText('3 个阻塞项')).toBeInTheDocument();
    expect(screen.getByText('阻塞来源：Bug 1、代码分支 1、发布记录 1。')).toBeInTheDocument();
    expect(screen.getByText('质量风险')).toBeInTheDocument();
    expect(screen.getByText('2 个严重风险')).toBeInTheDocument();
    expect(screen.getByText('严重 Bug 1，严重巡检 1，未关闭 Bug 1。')).toBeInTheDocument();
    expect(screen.getByText('1 个分支未创建')).toBeInTheDocument();
    expect(screen.getByText('1 份高风险')).toBeInTheDocument();
    expect(screen.getByText('1 份待确认')).toBeInTheDocument();
    expect(screen.getAllByText('1/1 可检索').length).toBeGreaterThan(0);
    expect(screen.getByText('已有 1 条任务知识沉淀，可检索 1 条，向量就绪 0 条。')).toBeInTheDocument();
    expect(screen.getByText('1 条失败发布')).toBeInTheDocument();
    expect(screen.getByText('阻塞处理队列')).toBeInTheDocument();
    expect(screen.getByText('按严重级别、来源类型和处理入口排序，优先处理发布准入风险。')).toBeInTheDocument();
    expect(screen.getByText('优先级 1')).toBeInTheDocument();
    expect(screen.getByText('高风险 · Bug')).toBeInTheDocument();
    expect(screen.getByText('优先级 2')).toBeInTheDocument();
    expect(screen.getByText('高风险 · 发布记录')).toBeInTheDocument();
    expect(screen.getByText('优先级 3')).toBeInTheDocument();
    expect(screen.getByText('中风险 · 代码分支')).toBeInTheDocument();
    expect(screen.getByText('状态分布')).toBeInTheDocument();
    expect(screen.getByText('需求状态')).toBeInTheDocument();
    expect(screen.getByText('开发中 1')).toBeInTheDocument();
    expect(screen.getByText('待评审 1')).toBeInTheDocument();
    expect(screen.getByText('任务状态')).toBeInTheDocument();
    expect(screen.getByText('运行中 1')).toBeInTheDocument();
    expect(screen.getByText('Bug 状态')).toBeInTheDocument();
    expect(screen.getByText('打开 1')).toBeInTheDocument();
    expect(screen.getByText('推进影响明细')).toBeInTheDocument();
    expect(screen.getByText('同步推进')).toBeInTheDocument();
    expect(screen.getByText('阻塞')).toBeInTheDocument();
    expect(screen.getByText('保持不变')).toBeInTheDocument();
    expect(screen.getByText('需求仍待评审，不能进入测试')).toBeInTheDocument();
    expect(screen.getAllByText('解除条件').length).toBeGreaterThan(0);
    expect(screen.getByText('修复、验证并关闭 blocker/critical Bug 后解除发布阻塞。')).toBeInTheDocument();
    expect(screen.getByText('创建或推进版本分支状态，使其满足测试/发布准入要求。')).toBeInTheDocument();
    expect(screen.getByText('登记或同步成功发布记录后解除发布阻塞。')).toBeInTheDocument();
    expect(
      screen
        .getAllByRole('link', { name: '处理 Bug' })
        .every((link) => link.getAttribute('href') === '/delivery/bugs?bug_id=bug_dashboard'),
    ).toBe(true);
    expect(
      screen
        .getAllByRole('link', { name: '维护分支' })
        .every(
          (link) =>
            link.getAttribute('href') ===
            '/delivery/versions?branch_config_id=version_branch_dashboard&version_id=version_dashboard',
        ),
    ).toBe(true);
    expect(
      screen
        .getAllByRole('link', { name: '排查发布' })
        .every((link) => link.getAttribute('href') === '/governance/devops?version_id=version_dashboard'),
    ).toBe(true);
    expect(screen.getAllByText('发布阻塞 Bug').length).toBeGreaterThan(0);
    expect(screen.getAllByText('release/2026-dashboard').length).toBeGreaterThan(0);
    expect(screen.getAllByText('驾驶舱需求').length).toBeGreaterThan(0);
    expect(screen.getAllByText('实现版本驾驶舱').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Dashboard Repo').length).toBeGreaterThan(0);
    expect(screen.getByText('代码评审待确认')).toBeInTheDocument();
    expect(screen.getAllByText('知识沉淀').length).toBeGreaterThan(0);
    expect(screen.getByText('版本驾驶舱知识沉淀')).toBeInTheDocument();
    expect(screen.getByText('版本驾驶舱知识文档')).toBeInTheDocument();
    expect(screen.getByText('knowledge_document_dashboard')).toBeInTheDocument();
    expect(screen.getByText('关键词可检索')).toBeInTheDocument();
    expect(screen.getByText('关键词兜底')).toBeInTheDocument();
    expect(screen.getByText('分块 1 / 向量 0')).toBeInTheDocument();
    expect(screen.getByText('Embedding 网关未配置，已降级为关键词检索。')).toBeInTheDocument();
    expect(screen.getByText('codex')).toBeInTheDocument();
    expect(screen.getByText('deploy-dashboard')).toBeInTheDocument();
    const cockpitLinks = screen
      .getAllByRole('link')
      .map((link) => link.getAttribute('href'))
      .filter(Boolean);
    expect(cockpitLinks).toContain('/delivery/full-chain?subject_id=version_dashboard&subject_type=product_version');
    expect(cockpitLinks).toContain('/delivery/bugs?version_id=version_dashboard');
    expect(cockpitLinks).toContain('/governance/code-inspections?version_id=version_dashboard');
    expect(cockpitLinks).toContain('/delivery/requirements?requirement_id=requirement_dashboard');
    expect(cockpitLinks).toContain('/delivery/rd-tasks?task_id=task_dashboard');
    expect(cockpitLinks).toContain('/delivery/bugs?bug_id=bug_dashboard');
    expect(cockpitLinks).toContain('/governance/code-inspections?source_id=code_inspection_report_dashboard');
    expect(cockpitLinks).toContain('/delivery/rd-tasks?code_review_report_id=code_review_report_dashboard');
    expect(cockpitLinks).toContain(
      '/delivery/full-chain?subject_id=knowledge_deposit_dashboard&subject_type=knowledge_deposit',
    );
    expect(cockpitLinks).toContain(
      '/delivery/versions?branch_config_id=version_branch_dashboard&version_id=version_dashboard',
    );
    expect(cockpitLinks).toContain('/governance/devops?version_id=version_dashboard');
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
      '/api/product-versions/version_dashboard/dashboard',
      'GET',
    ]);
  });
});
