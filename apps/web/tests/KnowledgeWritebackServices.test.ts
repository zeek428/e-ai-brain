import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  approveKnowledgeDeposit,
  createTaskWritebackResult,
  fetchKnowledgeDeposits,
  fetchKnowledgeSearchResults,
  fetchTaskWritebackResult,
  rejectKnowledgeDeposit,
} from '../src/services/aiBrain';

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('knowledge writeback service API mappings', () => {
  it('sends MVP-C writeback and knowledge deposit mutations to backend APIs', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/writeback/results/task_solution') {
        return jsonResponse({
          data: {
            idempotency_key: 'mock_issue:task_solution',
            issues: [
              {
                id: 'mock_issue_api',
                source_task_id: 'task_solution',
                status: 'open',
                title: '技术方案：CRUD 需求',
              },
            ],
            status: init?.method === 'POST' ? 'completed' : 'not_written',
            task_id: 'task_solution',
          },
        });
      }
      if (input === '/api/knowledge/deposits?status=pending') {
        return jsonResponse({
          data: {
            items: [
              {
                ai_task_id: 'task_solution',
                content: '沉淀内容',
                id: 'deposit_api',
                status: 'pending',
                title: '技术方案知识沉淀',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/knowledge/deposits/deposit_api/approve') {
        return jsonResponse({
          data: {
            id: 'deposit_api',
            knowledge_document_id: 'knowledge_api',
            status: 'approved',
          },
        });
      }
      if (input === '/api/knowledge/search') {
        expect(init?.method).toBe('POST');
        return jsonResponse({
          data: {
            items: [
              {
                content: '方案检索内容',
                document_id: 'knowledge_search_api',
                source: { doc_type: 'Spec', title: '技术方案知识' },
                title: '技术方案知识',
              },
              {
                content: '方案检索内容二',
                document_id: 'knowledge_search_api',
                source: { doc_type: 'Spec', title: '技术方案知识' },
                title: '技术方案知识',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/knowledge/deposits/deposit_api/reject') {
        return jsonResponse({
          data: {
            id: 'deposit_api',
            rejection_reason: '内容重复',
            status: 'rejected',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchTaskWritebackResult('task_solution')).resolves.toMatchObject({
      idempotencyKey: 'mock_issue:task_solution',
      status: 'not_written',
    });
    await expect(createTaskWritebackResult('task_solution')).resolves.toMatchObject({
      issues: [{ id: 'mock_issue_api', title: '技术方案：CRUD 需求' }],
      status: 'completed',
    });
    await expect(fetchKnowledgeDeposits('pending')).resolves.toMatchObject([
      {
        aiTaskId: 'task_solution',
        id: 'deposit_api',
        status: 'pending',
        title: '技术方案知识沉淀',
      },
    ]);
    await expect(fetchKnowledgeSearchResults('方案', 5)).resolves.toMatchObject([
      {
        documentId: 'knowledge_search_api',
        id: 'knowledge_search_api:0',
        sourceLabel: 'Spec · 技术方案知识',
        title: '技术方案知识',
      },
      {
        documentId: 'knowledge_search_api',
        id: 'knowledge_search_api:1',
        sourceLabel: 'Spec · 技术方案知识',
        title: '技术方案知识',
      },
    ]);
    await approveKnowledgeDeposit('deposit_api', {
      permissionRoles: ['admin', 'rd_owner'],
      title: '批准标题',
    });
    await rejectKnowledgeDeposit('deposit_api', '内容重复');

    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toEqual([
      ['/api/writeback/results/task_solution', 'GET', undefined],
      ['/api/writeback/results/task_solution', 'POST', undefined],
      ['/api/knowledge/deposits?status=pending', 'GET', undefined],
      ['/api/knowledge/search', 'POST', JSON.stringify({ query: '方案', top_k: 5 })],
      [
        '/api/knowledge/deposits/deposit_api/approve',
        'POST',
        JSON.stringify({ permission_roles: ['admin', 'rd_owner'], title: '批准标题' }),
      ],
      [
        '/api/knowledge/deposits/deposit_api/reject',
        'POST',
        JSON.stringify({ reason: '内容重复' }),
      ],
    ]);
  });
});
