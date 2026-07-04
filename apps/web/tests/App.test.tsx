import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import BugsPage from '../src/pages/Bugs';
import AuditPage from '../src/pages/Audit';
import KnowledgePage from '../src/pages/Knowledge';
import RequirementsPage from '../src/pages/Requirements';
import UsersPage from '../src/pages/Users';
import { apiRequest } from '../src/services/aiBrain';

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
      {
        business_roles: ['只读参与者'],
        code: 'viewer',
        data_scope: '授权范围内的数据。',
        decision_scope: '无写入或审批决策权限。',
        description: '只能查看有权限访问的工作台数据、任务结果、知识和看板摘要。',
        is_assignable: true,
        limitations: ['不能执行写操作、审批或配置变更。'],
        menu_scope: ['首页 IT 团队看板', '授权业务列表'],
        name: '查看者',
        permissions: ['workspace.read'],
        responsibilities: ['查看授权范围内的业务数据。'],
        sort_order: 60,
        status: 'active',
      },
    ],
    total: 2,
  },
};

const knowledgeIndexHealthEnvelope = {
  data: {
    embedding_models: [],
    import_job_counts: [],
    issues: [],
    retrieval_modes: {
      hybrid_ready: 0,
      keyword_fallback: 0,
      unavailable: 0,
    },
    status_counts: [],
    summary: {
      chunk_ready_documents: 1,
      embedding_ready_chunks: 0,
      index_failed_documents: 0,
      keyword_only_chunks: 0,
      keyword_only_documents: 0,
      missing_chunk_documents: 0,
      processing_documents: 0,
      searchable_documents: 1,
      total_chunks: 1,
      total_documents: 1,
      vector_ready_documents: 0,
    },
  },
};

describe('AI Brain Ant Design Pro workbench', () => {
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

  it('renders management modules as query filters with table lists', async () => {
    const { rerender } = render(<RequirementsPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('需求交付');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.queryByRole('heading', { level: 1, name: '需求管理' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(
      screen.queryByText('按产品、标题、状态和优先级查询需求台账，并从列表进入审批、关闭和生成 AI 任务操作。'),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.queryByText('需求列表')).not.toBeInTheDocument();
    expect(screen.getAllByText('需求标题')).not.toHaveLength(0);
    expect(screen.getByText('创建时间')).toBeInTheDocument();
    expect(screen.queryByText('更新时间')).not.toBeInTheDocument();
    expect(screen.queryByText('产品详细设计辅助')).not.toBeInTheDocument();

    rerender(<BugsPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('需求交付');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.queryByRole('heading', { level: 1, name: 'Bug 管理' })).not.toBeInTheDocument();
    expect(screen.queryByText('MVP 占位数据')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('Bug 列表')).toBeInTheDocument();
    expect(screen.getAllByText('严重级别')).not.toHaveLength(0);
    expect(screen.queryByText('登录态过期提示异常')).not.toBeInTheDocument();

    rerender(<KnowledgePage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('产品资产');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.queryByRole('heading', { level: 1, name: '知识中心' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('知识列表')).toBeInTheDocument();
    expect(screen.getAllByText('知识标题')).not.toHaveLength(0);
    expect(screen.queryByText('AI Brain v1 产品需求文档')).not.toBeInTheDocument();

    rerender(<AuditPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('运营治理');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.queryByRole('heading', { level: 1, name: '审计与运行' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('审计列表')).toBeInTheDocument();
    expect(screen.getAllByText('事件类型')).not.toHaveLength(0);
    expect(screen.queryByText('requirement.approved')).not.toBeInTheDocument();
  });

  it('opens real audit detail and lifecycle trace actions from audit rows', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input) === '/api/audit/events' || String(input).startsWith('/api/audit/events?')) {
        return jsonResponse({
          data: {
            items: [
              {
                actor_id: 'user_admin',
                ai_task_id: 'task_audit',
                created_at: '2026-05-31T08:00:00+00:00',
                event_type: 'requirement.approved',
                id: 'audit_api',
                payload: { comment: '进入设计评审' },
                subject_id: 'requirement_api',
                subject_type: 'requirement',
              },
              {
                actor_id: 'user_admin',
                created_at: '2026-06-01T08:00:00+00:00',
                event_type: 'user_feedback.created',
                id: 'audit_feedback',
                payload: { sentiment: 'negative' },
                subject_id: 'feedback_api',
                subject_type: 'user_feedback',
              },
            ],
            total: 2,
          },
        });
      }
      if (input === '/api/lifecycle/context?subject_type=requirement&subject_id=requirement_api') {
        return jsonResponse({
          data: {
            downstream: [
              {
                relation_type: 'generates_product_detail_design',
                subject_id: 'task_audit',
                subject_type: 'ai_task',
                summary: '产品详细设计：审计链路',
              },
            ],
            missing_context: ['automated_testing'],
            risk_signals: [
              {
                impact_summary: 'Review 中风险',
                recommendation: '补充边界测试',
                risk_type: 'code_review_medium_risk',
                severity: 'medium',
                source_subject_id: 'report_api',
                source_subject_type: 'code_review_report',
              },
            ],
            status: 'available',
            summary: { downstream_count: 1, risk_count: 1 },
            upstream: [],
          },
        });
      }
      if (input === '/api/lifecycle/context?subject_type=user_feedback&subject_id=feedback_api') {
        return jsonResponse({
          data: {
            downstream: [
              {
                relation_type: 'observes_user_feedback',
                subject_id: 'feedback_api',
                subject_type: 'user_feedback',
                summary: '知识检索上线后体验变差。',
              },
              {
                relation_type: 'observes_iteration_suggestion',
                subject_id: 'suggestion_api',
                subject_type: 'iteration_plan_suggestion',
                summary: '优化知识检索体验',
              },
            ],
            missing_context: [],
            risk_signals: [
              {
                impact_summary: '负向用户反馈：知识检索上线后体验变差。',
                recommendation: '纳入迭代建议或 Bug 修复队列。',
                risk_type: 'negative_user_feedback',
                severity: 'medium',
                source_subject_id: 'feedback_api',
                source_subject_type: 'user_feedback',
              },
            ],
            status: 'available',
            summary: { downstream_count: 2, risk_count: 1 },
            upstream: [],
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AuditPage />);

    expect(await screen.findByText('requirement.approved')).toBeInTheDocument();
    const auditRow = screen.getByText('requirement.approved').closest('tr');
    expect(auditRow).not.toBeNull();
    expect(within(auditRow as HTMLElement).getByRole('link', { name: '执行诊断' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=audit_api&source_type=audit_event',
    );
    fireEvent.click(within(auditRow as HTMLElement).getByRole('button', { name: '详情' }));
    expect(await screen.findByText('审计详情')).toBeInTheDocument();
    expect(screen.getAllByText('requirement: requirement_api')).not.toHaveLength(0);
    expect(screen.getByText(/进入设计评审/)).toBeInTheDocument();

    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /close/i }));
    fireEvent.click(within(auditRow as HTMLElement).getByRole('button', { name: '链路追踪' }));
    expect(await screen.findByText('generates_product_detail_design')).toBeInTheDocument();
    expect(screen.getByText('code_review_medium_risk')).toBeInTheDocument();
    expect(screen.getByText('code_review_report: report_api')).toBeInTheDocument();
    expect(screen.getByText('automated_testing')).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /close/i }));

    expect(await screen.findByText('user_feedback.created')).toBeInTheDocument();
    const feedbackRow = screen.getByText('user_feedback.created').closest('tr');
    expect(feedbackRow).not.toBeNull();
    fireEvent.click(within(feedbackRow as HTMLElement).getByRole('button', { name: '链路追踪' }));
    expect(await screen.findByText('observes_user_feedback')).toBeInTheDocument();
    expect(screen.getByText('negative_user_feedback')).toBeInTheDocument();
    expect(screen.getAllByText('user_feedback: feedback_api').length).toBeGreaterThanOrEqual(1);
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toContain(
        '/api/lifecycle/context?subject_type=user_feedback&subject_id=feedback_api',
      ),
    );
  });

  it('does not flash local requirement examples while authenticated data is loading', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    let resolveActiveProducts: (response: Response) => void = () => {};
    let resolveRequirements: (response: Response) => void = () => {};
    let resolveRequirementVersions: (response: Response) => void = () => {};
    const activeProductsPromise = new Promise<Response>((resolve) => {
      resolveActiveProducts = resolve;
    });
    const requirementVersionsPromise = new Promise<Response>((resolve) => {
      resolveRequirementVersions = resolve;
    });
    const requirementsPromise = new Promise<Response>((resolve) => {
      resolveRequirements = resolve;
    });
    const fetchMock = vi.fn<typeof fetch>((input) => {
      const path = String(input);
      if (path === '/api/products?active_only=true' || path === '/api/products?active_only=true&page_size=100') {
        return activeProductsPromise;
      }
      if (path === '/api/product-versions' || path.startsWith('/api/product-versions?')) {
        return requirementVersionsPromise;
      }
      if (path === '/api/requirements' || path.startsWith('/api/requirements?')) {
        return requirementsPromise;
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<RequirementsPage />);

    expect(screen.queryByText('产品详细设计辅助')).not.toBeInTheDocument();

    resolveActiveProducts(jsonResponse({ data: { items: [], total: 0 } }));
    resolveRequirementVersions(jsonResponse({ data: { items: [], total: 0 } }));
    resolveRequirements(jsonResponse({ data: { items: [], total: 0 } }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(screen.queryByText('产品详细设计辅助')).not.toBeInTheDocument();
    expect(screen.queryByText(/接口异常/)).not.toBeInTheDocument();
  });

  it('renders executable CRUD buttons on management pages', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const path = String(input);
      if (path === '/api/products' || path.startsWith('/api/products?')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                owner_team: 'API Team',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                owner_team: 'API Team',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions?active_only=true' ||
        path === '/api/product-versions' ||
        path.startsWith('/api/product-versions?')
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1',
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
      if (path === '/api/requirements' || path.startsWith('/api/requirements?')) {
        return jsonResponse({
          data: {
            items: [
              {
                id: 'requirement_api',
                priority: 'P1',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'submitted',
                title: '接口需求',
                version_id: 'version_api',
                version_name: 'v1',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/bugs' || path.startsWith('/api/bugs?')) {
        return jsonResponse({
          data: {
            items: [
              {
                id: 'bug_api',
                product_id: 'product_api',
                severity: 'major',
                source: 'manual_test',
                status: 'open',
                title: '接口 Bug',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/knowledge/documents' || path.startsWith('/api/knowledge/documents?')) {
        return jsonResponse({
          data: {
            items: [
              {
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
      if (path === '/api/knowledge/index-health' || path.startsWith('/api/knowledge/index-health?')) {
        return jsonResponse(knowledgeIndexHealthEnvelope);
      }
      if (path === '/api/auth/roles') {
        return jsonResponse(roleCatalogEnvelope);
      }
      if (path === '/api/users' || path.startsWith('/api/users?')) {
        return jsonResponse({
          data: {
            items: [
              {
                display_name: '接口用户',
                id: 'user_api',
                roles: ['viewer'],
                status: 'active',
                username: 'viewer@example.com',
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${path}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    window.localStorage.setItem(
      'ai_brain_current_user',
      JSON.stringify({
        display_name: 'AI Brain Admin',
        id: 'user_admin',
        permissions: [
          'bugs.manage',
          'knowledge.manage',
          'requirements.manage',
          'system.users.manage',
        ],
        roles: ['admin'],
        username: 'admin@example.com',
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const { rerender } = render(<RequirementsPage />);
    expect(screen.getByRole('button', { name: /新增需求/ })).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: /全链路/ })).not.toHaveLength(0);
    expect(screen.getAllByRole('button', { name: /更多/ })).not.toHaveLength(0);
    expect(screen.queryByRole('link', { name: /详情页/ })).not.toBeInTheDocument();
    expect(screen.getByRole('table')).toHaveAttribute('data-table-scroll-x', '1720');
    expect(screen.getByRole('columnheader', { name: '需求标题' })).toHaveAttribute(
      'data-width',
      '260',
    );
    expect(screen.getByRole('columnheader', { name: '迭代版本' })).toHaveAttribute(
      'data-width',
      '240',
    );
    expect(screen.getByRole('columnheader', { name: '操作' })).toHaveAttribute(
      'data-width',
      '164',
    );

    rerender(<BugsPage />);
    expect(screen.getByRole('button', { name: /登记 Bug/ })).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: /编辑/ })).not.toHaveLength(0);
    expect(screen.getAllByRole('button', { name: /删除/ })).not.toHaveLength(0);

    rerender(<KnowledgePage />);
    expect(screen.getByRole('button', { name: /导入文档/ })).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: /编辑/ })).not.toHaveLength(0);
    expect(screen.getAllByRole('button', { name: /删除/ })).not.toHaveLength(0);

    rerender(<UsersPage />);
    expect(screen.getByRole('button', { name: /新增用户/ })).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: /编辑/ })).not.toHaveLength(0);
    expect(screen.getAllByRole('button', { name: /删除/ })).not.toHaveLength(0);
  });



  it('hydrates management tables from backend API list endpoints when available', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);

      if (path === '/api/products' || path.startsWith('/api/products?')) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                owner_team: 'API Team',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/products?active_only=true') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                owner_team: 'API Team',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions?active_only=true' ||
        path === '/api/product-versions' ||
        path.startsWith('/api/product-versions?')
      ) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1',
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
      if (path === '/api/requirements' || path.startsWith('/api/requirements?')) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                created_at: '2026-05-30T08:30:00+00:00',
                id: 'requirement_api',
                priority: 'P0',
                product_code: 'API-PRODUCT',
                product_id: 'product_api',
                product_name: '接口产品',
                status: 'approved',
                title: '接口需求',
                version_id: 'version_api',
                version_name: 'v1',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/knowledge/documents' || path.startsWith('/api/knowledge/documents?')) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                doc_type: 'Spec',
                id: 'knowledge_api',
                index_status: 'indexed',
                permission_roles: ['admin', 'rd_owner'],
                title: '接口知识文档',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/knowledge/index-health' || path.startsWith('/api/knowledge/index-health?')) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse(knowledgeIndexHealthEnvelope);
      }
      if (path === '/api/auth/roles') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse(roleCatalogEnvelope);
      }
      if (path === '/api/bugs' || path.startsWith('/api/bugs?')) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                assignee: 'rd_owner@example.com',
                id: 'bug_api',
                module_code: 'knowledge',
                severity: 'critical',
                source: 'ai_post_release',
                status: 'needs_info',
                title: '接口 Bug',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/audit/events' || path.startsWith('/api/audit/events?')) {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                actor_id: 'user_admin',
                created_at: '2026-05-30T08:40:00+00:00',
                event_type: 'product.created',
                id: 'audit_api',
                subject_id: 'product_api',
                subject_type: 'product',
              },
            ],
            total: 1,
          },
        });
      }

      throw new Error(`Unexpected fetch call: ${path}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    const { rerender } = render(<RequirementsPage />);

    expect(await screen.findByText('接口需求')).toBeInTheDocument();
    expect(screen.getByText('API-PRODUCT')).toBeInTheDocument();

    rerender(<BugsPage />);

    expect(await screen.findByText('接口 Bug')).toBeInTheDocument();
    expect(screen.getAllByText('致命')).not.toHaveLength(0);
    expect(screen.getAllByText('待补充')).not.toHaveLength(0);
    expect(screen.getByText('AI 上线后分析')).toBeInTheDocument();

    rerender(<KnowledgePage />);

    expect(await screen.findAllByText('接口知识文档')).not.toHaveLength(0);
    expect(screen.getByText('admin, rd_owner')).toBeInTheDocument();

    rerender(<AuditPage />);

    expect(await screen.findByText('product.created')).toBeInTheDocument();
    expect(screen.getByText('product: product_api')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith('/api/auth/login', expect.anything());
  });

  it('preserves backend error code, message and trace id in API failures', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(async () =>
        new Response(
          JSON.stringify({
            detail: {
              code: 'TASK_STATE_INVALID',
              message: 'Task cannot be started from current status',
              trace_id: 'trace_task',
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 409,
          },
        ),
      ),
    );

    await expect(apiRequest('/api/ai-tasks/task_001/start')).rejects.toMatchObject({
      code: 'TASK_STATE_INVALID',
      message: 'Task cannot be started from current status',
      status: 409,
      traceId: 'trace_task',
    });
  });

  it('clears stale login state and redirects to login when an API token expires', async () => {
    window.history.pushState({}, '', '/delivery/requirements?priority=P0');
    window.localStorage.setItem('ai_brain_access_token', 'expired-token');
    window.localStorage.setItem('ai_brain_current_user', JSON.stringify({ username: 'old@example.com' }));
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(async () =>
        new Response(
          JSON.stringify({
            detail: {
              code: 'TOKEN_EXPIRED',
              message: 'Invalid bearer token',
              trace_id: 'trace_expired',
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 401,
          },
        ),
      ),
    );

    await expect(apiRequest('/api/requirements', { token: 'expired-token' })).rejects.toMatchObject({
      code: 'TOKEN_EXPIRED',
      message: 'Invalid bearer token',
      status: 401,
      traceId: 'trace_expired',
    });
    expect(window.localStorage.getItem('ai_brain_access_token')).toBeNull();
    expect(window.localStorage.getItem('ai_brain_current_user')).toBeNull();
    expect(window.location.pathname).toBe('/login');
    expect(window.location.search).toBe(
      '?redirect=%2Fdelivery%2Frequirements%3Fpriority%3DP0',
    );
  });

});
