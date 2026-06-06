import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import KnowledgePage from '../src/pages/Knowledge';

const roleCatalogEnvelope = {
  data: {
    items: [
      {
        business_roles: ['平台管理员'],
        code: 'admin',
        data_scope: '全平台。',
        decision_scope: '系统治理。',
        description: '负责用户、角色、模型网关、审计与系统级配置管理。',
        is_assignable: true,
        limitations: ['不能代替业务负责人做最终产品决策。'],
        menu_scope: ['系统管理', '审计与运行'],
        name: '系统管理员',
        permissions: ['system.users.manage'],
        responsibilities: ['维护用户和角色。'],
        sort_order: 10,
        status: 'active',
      },
    ],
  },
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  void message.destroy();
  notification.destroy();
  Modal.destroyAll();
});

describe('KnowledgePage', () => {
  it('opens knowledge deposit review and approves a pending deposit', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input) === '/api/knowledge/documents' || String(input).startsWith('/api/knowledge/documents?')) {
        return jsonResponse({
          data: {
            items: [
              {
                doc_type: 'Spec',
                id: 'knowledge_api',
                index_status: 'indexed',
                permission_roles: ['admin'],
                title: '接口知识',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/knowledge/deposits?status=pending') {
        return jsonResponse({
          data: {
            items: [
              {
                ai_task_id: 'task_solution_done',
                content: '沉淀内容摘要',
                id: 'deposit_api',
                knowledge_document_id: null,
                status: 'pending',
                title: '技术方案知识沉淀',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/knowledge/deposits/deposit_api/approve') {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toEqual({
          permission_roles: ['admin'],
          title: '技术方案知识沉淀',
        });
        return jsonResponse({
          data: {
            ai_task_id: 'task_solution_done',
            id: 'deposit_api',
            knowledge_document_id: 'knowledge_deposit_api',
            status: 'approved',
            title: '技术方案知识沉淀',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<KnowledgePage />);

    expect(await screen.findByText('接口知识')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '沉淀审核' }));

    expect(await screen.findByText('技术方案知识沉淀')).toBeInTheDocument();
    expect(screen.getByText('沉淀内容摘要')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '批准入库' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/knowledge/deposits/deposit_api/approve',
        'POST',
      ]),
    );
  });

  it('opens knowledge search and shows permission-filtered sources', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input) === '/api/knowledge/documents' || String(input).startsWith('/api/knowledge/documents?')) {
        return jsonResponse({
          data: {
            items: [
              {
                content: '需求评估规则内容',
                doc_type: 'manual',
                id: 'knowledge_api',
                index_status: 'indexed',
                permission_roles: ['admin'],
                title: '需求评估规则',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/auth/roles') {
        return jsonResponse(roleCatalogEnvelope);
      }
      if (input === '/api/knowledge/search') {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toEqual({
          query: '需求评估',
          top_k: 5,
        });
        return jsonResponse({
          data: {
            items: [
              {
                content: '需求评估规则内容',
                document_id: 'knowledge_api',
                source: { doc_type: 'manual', title: '需求评估规则' },
                title: '需求评估规则',
              },
            ],
            total: 1,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<KnowledgePage />);

    expect(await screen.findByText('需求评估规则')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '知识检索' }));
    fireEvent.change(screen.getByLabelText('检索关键词'), { target: { value: '需求评估' } });
    fireEvent.click(screen.getByRole('button', { name: '检索' }));

    expect(await screen.findByText('需求评估规则内容')).toBeInTheDocument();
    expect(screen.getByText('manual · 需求评估规则')).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path, init]) => [String(path).split('?')[0], init?.method ?? 'GET'])).toEqual([
      ['/api/auth/roles', 'GET'],
      ['/api/knowledge/documents', 'GET'],
      ['/api/knowledge/search', 'POST'],
    ]);
  });

  it('shows knowledge index errors and retries failed indexing', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    let retryCalled = false;
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input) === '/api/knowledge/documents' || String(input).startsWith('/api/knowledge/documents?')) {
        return jsonResponse({
          data: {
            items: [
              {
                content: '索引失败内容',
                doc_type: 'manual',
                id: 'knowledge_failed',
                index_error: retryCalled ? null : 'embedding provider timeout',
                index_status: retryCalled ? 'indexed' : 'index_failed',
                permission_roles: ['admin'],
                title: '失败知识',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/auth/roles') {
        return jsonResponse(roleCatalogEnvelope);
      }
      if (input === '/api/knowledge/documents/knowledge_failed/retry-index') {
        expect(init?.method).toBe('POST');
        retryCalled = true;
        return jsonResponse({
          data: {
            id: 'knowledge_failed',
            index_error: null,
            index_status: 'indexed',
            title: '失败知识',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<KnowledgePage />);

    expect(await screen.findByText('失败知识')).toBeInTheDocument();
    expect(screen.getByText('embedding provider timeout')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /重试索引/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/knowledge/documents/knowledge_failed/retry-index',
        'POST',
      ]),
    );
    await waitFor(() => expect(screen.getAllByText('已索引').length).toBeGreaterThan(1));
  });
});
