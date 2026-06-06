import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('product service API mappings', () => {
  it('sends product subresource CRUD requests to backend APIs without exposing git credentials', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path === '/api/products/product_api/versions' && method === 'GET') {
        return jsonResponse({
          data: { items: [{ code: 'v1', id: 'version_api', name: 'v1', status: 'active' }], total: 1 },
        });
      }
      if (path === '/api/products/product_api/modules' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [{ code: 'core', id: 'module_api', name: '核心模块', owner_team: 'AI', status: 'active' }],
            total: 1,
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
                name: '代码仓库',
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
      return jsonResponse({ data: { deleted: method === 'DELETE', id: path.split('/').at(-1), status: 'active' } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    const services = (await import('../src/services/aiBrain')) as Record<string, unknown>;
    const callService = async (name: string, ...args: unknown[]) => {
      expect(services[name]).toBeTypeOf('function');
      return (services[name] as (...serviceArgs: unknown[]) => Promise<unknown>)(...args);
    };

    await callService('fetchProductVersions', 'product_api');
    await callService('createProductVersion', 'product_api', { code: 'v2', name: 'v2', status: 'active' });
    await callService('updateProductVersion', 'version_api', { name: 'v2 更新' });
    await callService('deleteProductVersion', 'version_api');
    await callService('fetchProductModules', 'product_api');
    await callService('createProductModule', 'product_api', { code: 'core', name: '核心模块', status: 'active' });
    await callService('updateProductModule', 'module_api', { owner_team: 'AI Platform' });
    await callService('deleteProductModule', 'module_api');
    const gitRepositories = await callService('fetchProductGitRepositoryRecords', 'product_api');
    await callService('createProductGitRepository', 'product_api', {
      credential_ref: 'env:GITLAB_READONLY_TOKEN',
      git_provider: 'gitlab',
      name: '代码仓库',
      project_path: 'platform/ai-brain',
      remote_url: 'https://gitlab.example.com/platform/ai-brain.git',
      status: 'active',
    });
    await callService('updateProductGitRepository', 'repo_api', { default_branch: 'develop' });
    await callService('deleteProductGitRepository', 'repo_api');
    const relatedSystems = await callService('fetchProductRelatedSystems', 'product_api');
    await callService('createProductRelatedSystem', 'product_api', {
      code: 'crm',
      name: 'CRM 系统',
      owner_team: 'Business Platform',
      status: 'active',
    });
    await callService('updateProductRelatedSystem', 'related_system_api', { owner_team: 'Business Platform' });
    await callService('deleteProductRelatedSystem', 'related_system_api');

    expect(gitRepositories).toEqual([
      expect.objectContaining({
        credentialRefConfigured: true,
        credentialStatus: '已配置',
        id: 'repo_api',
        projectPath: 'platform/ai-brain',
      }),
    ]);
    expect(JSON.stringify(gitRepositories)).not.toContain('env:GITLAB_READONLY_TOKEN');
    expect(relatedSystems).toEqual([
      expect.objectContaining({
        code: 'billing',
        id: 'related_system_api',
        name: '计费系统',
        productId: 'product_api',
      }),
    ]);
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toEqual([
      ['/api/products/product_api/versions', 'GET'],
      ['/api/products/product_api/versions', 'POST'],
      ['/api/product-versions/version_api', 'PATCH'],
      ['/api/product-versions/version_api', 'DELETE'],
      ['/api/products/product_api/modules', 'GET'],
      ['/api/products/product_api/modules', 'POST'],
      ['/api/product-modules/module_api', 'PATCH'],
      ['/api/product-modules/module_api', 'DELETE'],
      ['/api/products/product_api/git-repositories', 'GET'],
      ['/api/products/product_api/git-repositories', 'POST'],
      ['/api/product-git-repositories/repo_api', 'PATCH'],
      ['/api/product-git-repositories/repo_api', 'DELETE'],
      ['/api/system/related-systems?product_id=product_api', 'GET'],
      ['/api/system/related-systems', 'POST'],
      ['/api/system/related-systems/related_system_api', 'PATCH'],
      ['/api/system/related-systems/related_system_api', 'DELETE'],
    ]);
  });
});
