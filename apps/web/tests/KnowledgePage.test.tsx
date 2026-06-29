import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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

function knowledgeHealthEnvelope(overrides: Record<string, unknown> = {}) {
  return {
    data: {
      embedding_models: [],
      import_job_counts: [],
      issues: [],
      performance: { duration_ms: 9 },
      retrieval_modes: {
        hybrid_ready: 0,
        keyword_fallback: 0,
        unavailable: 0,
      },
      status_counts: [],
      summary: {
        chunk_ready_documents: 0,
        embedding_ready_chunks: 0,
        index_failed_documents: 0,
        keyword_only_chunks: 0,
        keyword_only_documents: 0,
        missing_chunk_documents: 0,
        processing_documents: 0,
        searchable_documents: 0,
        total_chunks: 0,
        total_documents: 0,
        vector_ready_documents: 0,
      },
      ...overrides,
    },
  };
}

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
  it('keeps the knowledge document list in a fixed-width scrollable table', async () => {
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
                doc_type: 'manual',
                folder_path: '研发手册',
                id: 'knowledge_layout',
                index_status: 'text_indexed',
                knowledge_space_id: 'space_layout',
                permission_roles: ['admin'],
                title: '知识中心布局验证',
                vector_index_error: 'embedding provider unavailable',
              },
            ],
            total: 1,
          },
        });
      }
      if (String(input).startsWith('/api/knowledge/index-health')) {
        return jsonResponse(
          knowledgeHealthEnvelope({
            embedding_models: [{ count: 0, dimension: 1536, model: 'text-embedding-3-small' }],
            issues: [
              {
                action: 'retry_index',
                description: 'embedding provider unavailable',
                document_id: 'knowledge_layout',
                label: '向量待补',
                severity: 'warning',
                status: 'text_indexed',
                title: '知识中心布局验证',
                vector_index_error: 'embedding provider unavailable',
              },
              {
                action: 'open_chunks',
                description: '文档处于可检索状态，但没有生效分块版本。',
                document_id: 'knowledge_layout',
                label: '分块缺失',
                severity: 'warning',
                status: 'text_indexed',
                title: '知识中心布局验证',
              },
            ],
            retrieval_modes: {
              hybrid_ready: 0,
              keyword_fallback: 1,
              unavailable: 0,
            },
            status_counts: [{ count: 1, status: 'text_indexed' }],
            permission_scope: {
              filter_role: null,
              global_knowledge_access: true,
              knowledge_space_scope_ids: [],
              matched_roles: ['admin'],
              mode: 'role_based',
              readable_role_count: 1,
              scope_labels: ['角色 admin 命中 1 个文档'],
            },
            summary: {
              chunk_ready_documents: 0,
              embedding_ready_chunks: 0,
              index_failed_documents: 0,
              keyword_only_chunks: 1,
              keyword_only_documents: 1,
              missing_chunk_documents: 1,
              processing_documents: 0,
              searchable_documents: 1,
              total_chunks: 1,
              total_documents: 1,
              vector_ready_documents: 0,
            },
          }),
        );
      }
      if (input === '/api/knowledge/spaces') {
        return jsonResponse({
          data: {
            items: [{ code: 'layout', id: 'space_layout', name: '布局知识空间' }],
            total: 1,
          },
        });
      }
      if (input === '/api/auth/roles') {
        return jsonResponse(roleCatalogEnvelope);
      }
      if (input === '/api/knowledge/spaces/space_layout/folders') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<KnowledgePage />);

    expect((await screen.findAllByText('知识中心布局验证')).length).toBeGreaterThan(0);
    const healthPanel = screen.getByLabelText('知识索引健康');
    expect(within(healthPanel).getByText('索引健康')).toBeInTheDocument();
    expect(within(healthPanel).getByText('关键词兜底')).toBeInTheDocument();
    expect(within(healthPanel).getByText('向量待补')).toBeInTheDocument();
    expect(within(healthPanel).getByText('分块缺失')).toBeInTheDocument();
    expect(within(healthPanel).getByText('embedding provider unavailable')).toBeInTheDocument();
    expect(within(healthPanel).getByText('文档状态：文本索引 1')).toBeInTheDocument();
    expect(
      within(healthPanel).getByText('Chunk / Embedding：分块文档 0 · 缺分块 1 · Chunk 1 · Embedding 0 · 覆盖率 0%'),
    ).toBeInTheDocument();
    expect(within(healthPanel).getByText('召回模式：混合 0 · 关键词 1 · 不可用 0')).toBeInTheDocument();
    expect(within(healthPanel).getByText('权限命中：角色 admin 命中 1 个文档')).toBeInTheDocument();
    expect(within(healthPanel).getByText('Embedding 模型：text-embedding-3-small/1536维 0')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '知识列表' })).toBeInTheDocument();
    const mainTable = document.querySelector('table[data-table-scroll-x="2000"]');
    expect(mainTable).not.toBeNull();
    expect(mainTable).toHaveAttribute('data-table-layout', 'fixed');
    expect(within(mainTable as HTMLElement).getByText('操作')).toHaveAttribute('data-width', '420');
    expect(screen.getByRole('button', { name: /补向量索引/ })).toBeInTheDocument();
  });

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
      if (input === '/api/knowledge/spaces') {
        return jsonResponse({ data: { items: [], total: 0 } });
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
      if (String(input).startsWith('/api/knowledge/index-health')) {
        return jsonResponse(knowledgeHealthEnvelope());
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<KnowledgePage />);

    expect((await screen.findAllByText('接口知识')).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('button', { name: '沉淀审核' }));

    expect(await screen.findByText('技术方案知识沉淀')).toBeInTheDocument();
    expect(screen.getByText('沉淀内容摘要')).toBeInTheDocument();
    const depositTable = document.querySelector('table[data-table-scroll-x="1120"]');
    expect(depositTable).not.toBeNull();
    expect(depositTable).toHaveAttribute('data-table-layout', 'fixed');
    const fullChainLink = screen.getByRole('link', { name: '全链路' });
    expect(fullChainLink).toHaveAttribute(
      'href',
      '/delivery/full-chain?subject_id=deposit_api&subject_type=knowledge_deposit',
    );
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
      if (input === '/api/knowledge/spaces') {
        return jsonResponse({ data: { items: [], total: 0 } });
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
      if (String(input).startsWith('/api/knowledge/index-health')) {
        return jsonResponse(knowledgeHealthEnvelope());
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<KnowledgePage />);

    expect((await screen.findAllByText('需求评估规则')).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('button', { name: '知识检索' }));
    fireEvent.change(screen.getByLabelText('检索关键词'), { target: { value: '需求评估' } });
    fireEvent.click(screen.getByRole('button', { name: '检索' }));

    expect(await screen.findByText('需求评估规则内容')).toBeInTheDocument();
    expect(screen.getByText('manual · 需求评估规则')).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path, init]) => [String(path).split('?')[0], init?.method ?? 'GET'])).toEqual([
      ['/api/auth/roles', 'GET'],
      ['/api/knowledge/spaces', 'GET'],
      ['/api/knowledge/documents', 'GET'],
      ['/api/knowledge/index-health', 'GET'],
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
      if (input === '/api/knowledge/spaces') {
        return jsonResponse({ data: { items: [], total: 0 } });
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
      if (String(input).startsWith('/api/knowledge/index-health')) {
        return jsonResponse(
          knowledgeHealthEnvelope(
            retryCalled
              ? {}
              : {
                  issues: [
                    {
                      action: 'retry_index',
                      description: 'embedding provider timeout',
                      document_id: 'knowledge_failed',
                      label: '索引失败',
                      severity: 'error',
                      status: 'index_failed',
                      title: '失败知识',
                    },
                  ],
                  summary: {
                    chunk_ready_documents: 0,
                    embedding_ready_chunks: 0,
                    index_failed_documents: 1,
                    keyword_only_chunks: 0,
                    keyword_only_documents: 0,
                    missing_chunk_documents: 0,
                    processing_documents: 0,
                    searchable_documents: 0,
                    total_chunks: 0,
                    total_documents: 1,
                    vector_ready_documents: 0,
                  },
                },
          ),
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<KnowledgePage />);

    expect((await screen.findAllByText('失败知识')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('embedding provider timeout').length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('button', { name: /重试索引/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/knowledge/documents/knowledge_failed/retry-index',
        'POST',
      ]),
    );
    await waitFor(() => expect(screen.getAllByText('已索引').length).toBeGreaterThan(1));
  });

  it('uploads a document into a knowledge space folder', async () => {
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
            items: [],
            total: 0,
          },
        });
      }
      if (input === '/api/auth/roles') {
        return jsonResponse(roleCatalogEnvelope);
      }
      if (input === '/api/knowledge/spaces') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'payment',
                id: 'knowledge_space_payment',
                name: '支付知识空间',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/knowledge/spaces/knowledge_space_payment/folders' && init?.method === 'POST') {
        expect(JSON.parse(String(init?.body))).toEqual({ name: '排障手册' });
        return jsonResponse({
          data: {
            id: 'knowledge_folder_runbook',
            knowledge_space_id: 'knowledge_space_payment',
            name: '排障手册',
            path: '排障手册',
          },
        });
      }
      if (input === '/api/knowledge/spaces/knowledge_space_payment/folders') {
        return jsonResponse({
          data: {
            items: [
              {
                id: 'knowledge_folder_runbook',
                knowledge_space_id: 'knowledge_space_payment',
                name: '排障手册',
                path: '排障手册',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/knowledge/documents/upload') {
        expect(init?.method).toBe('POST');
        const body = JSON.parse(String(init?.body));
        expect(body).toMatchObject({
          chunk_strategy: 'regex_section',
          doc_type: 'manual',
          filename: 'payment-runbook.md',
          folder_id: 'knowledge_folder_runbook',
          knowledge_space_id: 'knowledge_space_payment',
          mime_type: 'text/markdown',
          tags: [],
          title: 'payment-runbook',
        });
        expect(body.content_base64).toEqual(expect.any(String));
        return jsonResponse({
          data: {
            asset: {
              id: 'knowledge_asset_upload',
            },
            document: {
              active_chunk_set_id: null,
              folder_id: 'knowledge_folder_runbook',
              id: 'knowledge_upload',
              index_status: 'importing',
              knowledge_space_id: 'knowledge_space_payment',
              source_asset_id: 'knowledge_asset_upload',
              title: 'payment-runbook',
            },
            import_job: {
              id: 'knowledge_import_job_upload',
              status: 'queued',
            },
          },
        });
      }
      if (String(input).startsWith('/api/knowledge/index-health')) {
        return jsonResponse(knowledgeHealthEnvelope());
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<KnowledgePage />);

    expect(await screen.findByText('知识中心')).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/knowledge/spaces', expect.any(Object)));

    fireEvent.click(screen.getByRole('button', { name: '导入文档' }));
    const documentModalTitle = await screen.findByText('导入知识文档');
    const documentModal = documentModalTitle.closest('.ant-modal') as HTMLElement;
    fireEvent.click(within(documentModal).getByRole('button', { name: /新建/ }));
    const folderModalTitle = await screen.findByText('新建知识目录');
    const folderModal = folderModalTitle.closest('.ant-modal') as HTMLElement;
    const folderNameInput = folderModal.querySelector('input#name') as HTMLInputElement;
    fireEvent.change(folderNameInput, { target: { value: '排障手册' } });
    fireEvent.click(within(folderModal).getByRole('button', { name: /OK|确 定/ }));

    expect(await screen.findByText('排障手册')).toBeInTheDocument();
    const file = new File(['支付失败排查步骤'], 'payment-runbook.md', {
      type: 'text/markdown',
    });
    fireEvent.change(within(documentModal).getByLabelText('选择知识文件'), {
      target: { files: [file] },
    });
    expect(await screen.findByText('payment-runbook.md')).toBeInTheDocument();
    fireEvent.mouseDown(within(documentModal).getByLabelText('分块策略'));
    fireEvent.click(await screen.findByText('正则分块'));

    fireEvent.click(within(documentModal).getByRole('button', { name: /OK|确 定/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/knowledge/documents/upload',
        'POST',
      ]),
    );
  });

  it('opens import job and document asset operation views', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    let importJobStatus = 'queued';
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input) === '/api/knowledge/documents' || String(input).startsWith('/api/knowledge/documents?')) {
        return jsonResponse({
          data: {
            items: [
              {
                active_chunk_set_id: 'knowledge_chunk_set_ops',
                content: '导入任务排查内容',
                doc_type: 'runbook',
                folder_path: '导入任务',
                id: 'knowledge_ops',
                index_status: 'vector_indexed',
                knowledge_space_id: 'space_ops',
                permission_roles: ['admin'],
                source_asset_id: 'knowledge_asset_ops',
                title: '导入任务排查',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/knowledge/spaces') {
        return jsonResponse({
          data: {
            items: [{ code: 'ops', id: 'space_ops', name: '运维知识空间' }],
            total: 1,
          },
        });
      }
      if (input === '/api/auth/roles') {
        return jsonResponse(roleCatalogEnvelope);
      }
      if (input === '/api/knowledge/import-jobs?knowledge_space_id=space_ops') {
        return jsonResponse({
          data: {
            items: [
              {
                asset_filename: 'ops-import.md',
                chunk_strategy: 'parent_child',
                document_id: 'knowledge_ops',
                document_title: '导入任务排查',
                folder_path: '导入任务',
                id: 'knowledge_import_job_ops',
                parser_engine: 'markdown',
                progress: importJobStatus === 'completed' ? 100 : 0,
                status: importJobStatus,
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/knowledge/import-worker/status') {
        return jsonResponse({
          data: {
            active_job_id: 'knowledge_import_job_ops',
            enabled: true,
            failed_count: 0,
            pending_count: importJobStatus === 'completed' ? 0 : 1,
            processed_count: importJobStatus === 'completed' ? 1 : 0,
            queued_job_ids: importJobStatus === 'completed' ? [] : ['knowledge_import_job_ops'],
            running: true,
          },
        });
      }
      if (input === '/api/knowledge/import-jobs/knowledge_import_job_ops/run') {
        expect(init?.method).toBe('POST');
        importJobStatus = 'completed';
        return jsonResponse({
          data: {
            import_job: {
              id: 'knowledge_import_job_ops',
              status: 'completed',
            },
          },
        });
      }
      if (input === '/api/knowledge/documents/knowledge_ops/assets') {
        return jsonResponse({
          data: {
            document_id: 'knowledge_ops',
            items: [
              {
                asset_type: 'original',
                filename: 'ops-import.md',
                id: 'knowledge_asset_ops',
                mime_type: 'text/markdown',
                size_bytes: 123,
                storage_provider: 'minio',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/knowledge/documents/knowledge_ops/chunk-sets') {
        return jsonResponse({
          data: {
            items: [
              {
                chunk_count: 2,
                chunk_strategy: 'parent_child',
                id: 'knowledge_chunk_set_ops',
                is_active: true,
                parser_engine: 'markdown',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/knowledge/documents/knowledge_ops/chunks?chunk_set_id=knowledge_chunk_set_ops') {
        return jsonResponse({
          data: {
            items: [
              {
                chunk_index: 1,
                chunk_set_id: 'knowledge_chunk_set_ops',
                content: '# 导入任务',
                id: 'chunk_parent',
                metadata: { chunk_role: 'parent', heading: '导入任务' },
              },
              {
                chunk_index: 2,
                chunk_set_id: 'knowledge_chunk_set_ops',
                content: 'ops-import 解析完成',
                id: 'chunk_child',
                metadata: {
                  chunk_role: 'child',
                  columns: ['owner', 'risk'],
                  heading: '导入任务',
                  image_count: 2,
                  image_refs: ['image-7-a'],
                  page_number: 7,
                  source_asset_type: 'table_json',
                  source_kind: 'table',
                  table_count: 1,
                  table_index: 1,
                },
                parent_chunk_id: 'chunk_parent',
                parent_content: '# 导入任务',
              },
            ],
            total: 2,
          },
        });
      }
      if (input === '/api/knowledge/documents/batch-move') {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toEqual({
          document_ids: ['knowledge_ops'],
          folder_id: null,
        });
        return jsonResponse({ data: { skipped: [], updated: ['knowledge_ops'] } });
      }
      if (String(input).startsWith('/api/knowledge/index-health')) {
        return jsonResponse(
          knowledgeHealthEnvelope({
            retrieval_modes: {
              hybrid_ready: 1,
              keyword_fallback: 0,
              unavailable: 0,
            },
            summary: {
              chunk_ready_documents: 1,
              embedding_ready_chunks: 2,
              index_failed_documents: 0,
              keyword_only_chunks: 0,
              keyword_only_documents: 0,
              missing_chunk_documents: 0,
              processing_documents: 0,
              searchable_documents: 1,
              total_chunks: 2,
              total_documents: 1,
              vector_ready_documents: 1,
            },
          }),
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<KnowledgePage />);

    expect(await screen.findByText('导入任务排查')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '导入任务' }));

    expect(await screen.findByText('markdown')).toBeInTheDocument();
    expect(screen.getByText('导入 worker')).toBeInTheDocument();
    expect(screen.getByText('运行中')).toBeInTheDocument();
    expect(screen.getByText('待处理 1')).toBeInTheDocument();
    expect(screen.getByText('失败 0')).toBeInTheDocument();
    expect(screen.getByText('ops-import.md')).toBeInTheDocument();
    expect(screen.getByText('0%')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /运行/ }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/knowledge/import-jobs/knowledge_import_job_ops/run',
        'POST',
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '资产' }));

    expect(await screen.findByText('原始文件')).toBeInTheDocument();
    expect(screen.getAllByText('ops-import.md').length).toBeGreaterThan(1);
    expect(screen.getByText('text/markdown')).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/knowledge/documents/knowledge_ops/assets',
        'GET',
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '分块' }));
    expect(await screen.findByText('parent_child')).toBeInTheDocument();
    expect(screen.getAllByText('父块').length).toBeGreaterThan(1);
    expect(screen.getByText('子块')).toBeInTheDocument();
    expect(
      screen.getByText(
        '第 7 页 / 表格 1 / 图片 2 / 表格数 1 / table / table_json / 列：owner, risk / 图：image-7-a',
      ),
    ).toBeInTheDocument();
    expect(screen.getByText('ops-import 解析完成')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('checkbox', { name: '选择 knowledge_ops' }));
    fireEvent.click(screen.getByRole('button', { name: /批量移动/ }));
    fireEvent.click(await screen.findByRole('button', { name: /OK|确 定/ }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/knowledge/documents/batch-move',
        'POST',
      ]),
    );
  });
});
