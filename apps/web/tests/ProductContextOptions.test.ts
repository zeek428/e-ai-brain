import { afterEach, describe, expect, it, vi } from 'vitest';

import { fetchProductContextOptions } from '../src/services/aiBrain';

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('product context option services', () => {
  it('loads all paginated products and versions for shared selectors', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path === '/api/products?active_only=true&page_size=100') {
        return jsonResponse({
          data: {
            items: [{ code: 'PRODUCT-A', id: 'product_a', name: '产品 A' }],
            page: 1,
            page_size: 100,
            total: 2,
          },
        });
      }
      if (path === '/api/products?active_only=true&page_size=100&page=2') {
        return jsonResponse({
          data: {
            items: [{ code: 'AI-BRAIN', id: 'product_ai_brain', name: 'AI Brain' }],
            page: 2,
            page_size: 100,
            total: 2,
          },
        });
      }
      if (path === '/api/product-versions?active_only=true&page_size=100') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v-a',
                id: 'version_a',
                name: '版本 A',
                product_id: 'product_a',
                status: 'active',
              },
            ],
            page: 1,
            page_size: 100,
            total: 2,
          },
        });
      }
      if (path === '/api/product-versions?active_only=true&page_size=100&page=2') {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-ai-brain',
                id: 'version_ai_brain',
                name: 'AI Brain 2026',
                product_id: 'product_ai_brain',
                status: 'active',
              },
            ],
            page: 2,
            page_size: 100,
            total: 2,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${path}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchProductContextOptions()).resolves.toEqual([
      {
        code: 'PRODUCT-A',
        id: 'product_a',
        name: '产品 A',
        versions: [{ code: 'v-a', id: 'version_a', name: '版本 A', status: 'active' }],
      },
      {
        code: 'AI-BRAIN',
        id: 'product_ai_brain',
        name: 'AI Brain',
        versions: [
          {
            code: '2026-ai-brain',
            id: 'version_ai_brain',
            name: 'AI Brain 2026',
            status: 'active',
          },
        ],
      },
    ]);
    expect(fetchMock.mock.calls.map(([path]) => String(path))).toEqual(expect.arrayContaining([
      '/api/products?active_only=true&page_size=100&page=2',
      '/api/product-versions?active_only=true&page_size=100&page=2',
    ]));
  });
});
