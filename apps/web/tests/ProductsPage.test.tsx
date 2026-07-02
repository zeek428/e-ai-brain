import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import ProductsPage from '../src/pages/Products';

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

describe('ProductsPage', () => {
  it('renders product management filters without local example rows', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path === '/api/products' || path.startsWith('/api/products?')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/product-versions' || path.startsWith('/api/product-versions?')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      throw new Error(`Unexpected fetch call: ${path}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<ProductsPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('产品资产');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('工作台');
    expect(screen.queryByRole('heading', { level: 1, name: '产品管理' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('产品列表')).toBeInTheDocument();
    expect(screen.getAllByText('产品编码')).not.toHaveLength(0);
    expect(screen.queryByText('AI-BRAIN')).not.toBeInTheDocument();
  });

  it('filters product table rows from query conditions', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path.includes('/versions') || path.startsWith('/api/product-versions')) {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      const productItems = [
        {
          code: 'AI-BRAIN',
          id: 'product_ai_brain',
          name: '企业 AI 大脑平台',
          owner_team: 'AI Platform',
          status: 'active',
        },
        {
          code: 'RD-BRAIN',
          id: 'product_rd_brain',
          name: '研发大脑',
          owner_team: 'R&D Enablement',
          status: 'active',
        },
      ].filter((item) => {
        if (!path.includes('code=RD-BRAIN')) {
          return true;
        }
        return item.code === 'RD-BRAIN';
      });
      return new Response(
        JSON.stringify({
          data: {
            items: productItems,
            total: productItems.length,
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      );
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<ProductsPage />);

    expect(await screen.findByText('AI-BRAIN')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('产品编码'), { target: { value: 'RD-BRAIN' } });
    fireEvent.submit(screen.getByRole('form', { name: '查询表格' }));

    expect(await screen.findByText('RD-BRAIN')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('AI-BRAIN')).not.toBeInTheDocument());

    fireEvent.reset(screen.getByRole('form', { name: '查询表格' }));

    expect(await screen.findByText('AI-BRAIN')).toBeInTheDocument();
  });

  it('shows backend load failures without local product example rows', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      return new Response(
        JSON.stringify({
          detail: {
            code: 'FORBIDDEN',
            message: 'Role permission denied',
            trace_id: 'trace_denied',
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 403,
        },
      );
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<ProductsPage />);

    expect(screen.queryByText('AI-BRAIN')).not.toBeInTheDocument();
    expect(await screen.findByText(/接口异常，未加载到数据/)).toBeInTheDocument();
    expect(screen.getByText(/FORBIDDEN/)).toBeInTheDocument();
    expect(screen.getByText(/trace_denied/)).toBeInTheDocument();
  });

  it('shows related record counts when product deletion is blocked', async () => {
    const errorSpy = vi.spyOn(message, 'error').mockImplementation(() => null as never);
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path === '/api/products' || path.startsWith('/api/products?')) {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  code: 'AI-BRAIN',
                  id: 'product_ai_brain',
                  name: 'AI Brain',
                  owner_team: 'AI Platform',
                  status: 'active',
                },
              ],
              total: 1,
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (path === '/api/products/product_ai_brain' && method === 'DELETE') {
        return new Response(
          JSON.stringify({
            detail: {
              code: 'RESOURCE_IN_USE',
              message: 'Product still has related records',
              related_counts: { ai_tasks: 2, bugs: 1, requirements: 3 },
              related_total: 6,
              trace_id: 'trace_product_delete',
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 409,
          },
        );
      }
      if (path === '/api/product-versions' || path.startsWith('/api/product-versions?')) {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      throw new Error(`Unexpected fetch call: ${path} ${method}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<ProductsPage />);

    expect(await screen.findByText('AI Brain')).toBeInTheDocument();
    const productRow = screen.getByText('AI Brain').closest('tr');
    expect(productRow).not.toBeNull();
    fireEvent.click(within(productRow as HTMLElement).getByRole('button', { name: /删除/ }));
    await screen.findByText('删除产品 AI-BRAIN？');
    fireEvent.click(screen.getAllByRole('button', { name: /删\s*除/ }).at(-1)!);

    await waitFor(() =>
      expect(errorSpy).toHaveBeenCalledWith(
        '无法删除产品，仍关联 3 条需求、2 个AI任务、1 个Bug。请先迁移或删除关联业务记录，也可以将产品状态改为停用。',
      ),
    );
  });

  it('manages product versions modules and git resources from the product page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });

      if (path === '/api/products' || path.startsWith('/api/products?')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'AI-BRAIN',
                id: 'product_api',
                module_count: 1,
                name: 'AI Brain',
                owner_team: 'AI Platform',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products/product_api/versions' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1 MVP',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/product-versions' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1 MVP',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products/product_api/versions' && method === 'POST') {
        expect(JSON.parse(String(init?.body))).toMatchObject({
          code: 'v2',
          name: 'v2 版本',
          status: 'active',
        });
        return jsonResponse({
          data: {
            code: 'v2',
            id: 'version_new',
            name: 'v2 版本',
            product_id: 'product_api',
            status: 'active',
          },
        });
      }
      if (path === '/api/products/product_api/modules' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'knowledge',
                id: 'module_api',
                name: '知识模块',
                owner_team: 'AI Platform',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products/product_api/modules' && method === 'POST') {
        expect(JSON.parse(String(init?.body))).toMatchObject({
          code: 'planning',
          name: '规划模块',
          owner_team: 'AI Platform',
          status: 'active',
        });
        return jsonResponse({
          data: {
            code: 'planning',
            id: 'module_new',
            name: '规划模块',
            owner_team: 'AI Platform',
            product_id: 'product_api',
            status: 'active',
          },
        });
      }
      if (path === '/api/products/product_api/git-repositories' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                credential_ref_configured: true,
                default_branch: 'main',
                git_provider: 'gitlab',
                id: 'repo_api',
                name: 'AI Brain 仓库',
                project_path: 'platform/ai-brain',
                remote_url: 'https://gitlab.example.com/platform/ai-brain.git',
                repo_type: 'code',
                root_path: '/',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/system/related-systems?product_id=product_api' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'billing',
                id: 'related_system_api',
                name: '计费系统',
                owner_team: 'Business Platform',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/system/related-systems' && method === 'POST') {
        expect(JSON.parse(String(init?.body))).toMatchObject({
          code: 'crm',
          name: 'CRM 系统',
          owner_team: 'Business Platform',
          product_id: 'product_api',
          status: 'active',
        });
        return jsonResponse({
          data: {
            code: 'crm',
            id: 'related_system_new',
            name: 'CRM 系统',
            owner_team: 'Business Platform',
            product_id: 'product_api',
            status: 'active',
          },
        });
      }
      if (path === '/api/products/product_api/git-repositories' && method === 'POST') {
        expect(JSON.parse(String(init?.body))).toMatchObject({
          credential_ref: 'env:GITLAB_READONLY_TOKEN',
          git_provider: 'gitlab',
          name: '测试仓库',
          project_path: 'platform/test',
          remote_url: 'https://gitlab.example.com/platform/test.git',
          status: 'active',
        });
        return jsonResponse({
          data: {
            credential_ref_configured: true,
            default_branch: 'main',
            git_provider: 'gitlab',
            id: 'repo_new',
            name: '测试仓库',
            project_path: 'platform/test',
            remote_url: 'https://gitlab.example.com/platform/test.git',
            repo_type: 'code',
            root_path: '/',
            status: 'active',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${path} ${method}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<ProductsPage />);

    expect(await screen.findByText('AI Brain')).toBeInTheDocument();
    const productRow = screen.getByText('AI Brain').closest('tr');
    expect(productRow).not.toBeNull();
    fireEvent.click(within(productRow as HTMLElement).getByRole('button', { name: '配置' }));

    expect(await screen.findByText(/产品配置：AI Brain/)).toBeInTheDocument();
    expect(screen.getByText('版本管理')).toBeInTheDocument();
    expect(screen.getByText('模块管理')).toBeInTheDocument();
    expect(screen.getByText('Git 资源')).toBeInTheDocument();
    expect(screen.getByText('相关系统')).toBeInTheDocument();
    expect(screen.getAllByText('v1 MVP').length).toBeGreaterThan(0);
    expect(screen.getByText('知识模块')).toBeInTheDocument();
    expect(screen.getByText('platform/ai-brain')).toBeInTheDocument();
    expect(screen.getByText('已配置')).toBeInTheDocument();
    expect(screen.getByText('计费系统')).toBeInTheDocument();
    expect(screen.queryByText('env:GITLAB_READONLY_TOKEN')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '新增版本' }));
    fireEvent.change(screen.getByLabelText('版本编码'), { target: { value: 'v2' } });
    fireEvent.change(screen.getByLabelText('版本名称'), { target: { value: 'v2 版本' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/products/product_api/versions',
        'POST',
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增模块' }));
    fireEvent.change(screen.getByLabelText('模块编码'), { target: { value: 'planning' } });
    fireEvent.change(screen.getByLabelText('模块名称'), { target: { value: '规划模块' } });
    fireEvent.change(screen.getByLabelText('模块负责团队'), { target: { value: 'AI Platform' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/products/product_api/modules',
        'POST',
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增 Git 资源' }));
    fireEvent.change(screen.getByLabelText('资源名称'), { target: { value: '测试仓库' } });
    fireEvent.change(screen.getByLabelText('Remote URL'), {
      target: { value: 'https://gitlab.example.com/platform/test.git' },
    });
    fireEvent.change(screen.getByLabelText('Project Path'), { target: { value: 'platform/test' } });
    fireEvent.change(screen.getByLabelText('凭据引用'), {
      target: { value: 'env:GITLAB_READONLY_TOKEN' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/products/product_api/git-repositories',
        'POST',
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增相关系统' }));
    fireEvent.change(screen.getByLabelText('系统编码'), { target: { value: 'crm' } });
    fireEvent.change(screen.getByLabelText('系统名称'), { target: { value: 'CRM 系统' } });
    fireEvent.change(screen.getByLabelText('系统负责团队'), {
      target: { value: 'Business Platform' },
    });
    expect(screen.getByLabelText('描述')).toHaveAttribute('rows', '3');
    fireEvent.click(screen.getByRole('button', { name: '保存' }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/system/related-systems',
        'POST',
      ]),
    );
  }, 10_000);

  it('saves GitHub provider when editing product Git resources', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if ((path === '/api/products' || path.startsWith('/api/products?')) && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'AI-BRAIN',
                id: 'product_api',
                module_count: 1,
                name: 'AI Brain',
                owner_team: 'AI Platform',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products/product_api/versions' && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/product-versions' && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/products/product_api/modules' && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/system/related-systems?product_id=product_api' && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/products/product_api/git-repositories' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                credential_ref_configured: true,
                default_branch: 'main',
                git_provider: 'gitlab',
                id: 'repo_api',
                name: 'AI Brain 仓库',
                project_path: 'platform/ai-brain',
                remote_url: 'https://gitlab.example.com/platform/ai-brain.git',
                repo_type: 'code',
                root_path: '/',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/product-git-repositories/repo_api' && method === 'PATCH') {
        expect(JSON.parse(String(init?.body))).toMatchObject({
          git_provider: 'github',
          name: 'AI Brain 仓库',
          project_path: 'zeek428/e-ai-brain',
          remote_url: 'git@github.com:zeek428/e-ai-brain.git',
        });
        return jsonResponse({
          data: {
            credential_ref_configured: true,
            default_branch: 'main',
            git_provider: 'github',
            id: 'repo_api',
            name: 'AI Brain 仓库',
            project_path: 'zeek428/e-ai-brain',
            remote_url: 'git@github.com:zeek428/e-ai-brain.git',
            repo_type: 'code',
            root_path: '/',
            status: 'active',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${path} ${method}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<ProductsPage />);

    expect(await screen.findByText('AI Brain')).toBeInTheDocument();
    const productRow = screen.getByText('AI Brain').closest('tr');
    expect(productRow).not.toBeNull();
    fireEvent.click(within(productRow as HTMLElement).getByRole('button', { name: '配置' }));
    const repositoryRow = await screen.findByText('AI Brain 仓库');
    fireEvent.click(
      within(repositoryRow.closest('tr') as HTMLElement).getByRole('button', { name: /编辑/ }),
    );

    fireEvent.mouseDown(screen.getByLabelText('代码平台'));
    fireEvent.click(await screen.findByRole('option', { name: 'GitHub' }));
    fireEvent.change(screen.getByLabelText('Remote URL'), {
      target: { value: 'git@github.com:zeek428/e-ai-brain.git' },
    });
    fireEvent.change(screen.getByLabelText('Project Path'), {
      target: { value: 'zeek428/e-ai-brain' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/product-git-repositories/repo_api',
        'PATCH',
      ]),
    );
  });
});
