import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('@ant-design/pro-components', async () => {
  const React = await import('react');

  function PageContainer({
    breadcrumb,
    children,
    content,
    extra,
    title,
  }: {
    breadcrumb?: { items?: Array<{ title: React.ReactNode }> };
    children?: React.ReactNode;
    content?: React.ReactNode;
    extra?: React.ReactNode;
    title?: React.ReactNode;
  }) {
    return React.createElement(
      'main',
      null,
      breadcrumb?.items?.length
        ? React.createElement(
            'nav',
            { 'aria-label': '面包屑' },
            breadcrumb.items.map((item) =>
              React.createElement('span', { key: String(item.title) }, item.title),
            ),
          )
        : null,
      React.createElement('h1', null, title),
      content ? React.createElement('p', null, content) : null,
      extra,
      children,
    );
  }

  function ProCard({
    children,
    extra,
    title,
  }: {
    children?: React.ReactNode;
    extra?: React.ReactNode;
    title?: React.ReactNode;
  }) {
    return React.createElement(
      'section',
      null,
      title ? React.createElement('h2', null, title) : null,
      extra,
      children,
    );
  }

  ProCard.Group = ({ children }: { children?: React.ReactNode }) =>
    React.createElement('section', null, children);

  function ProTable<Row extends { [key: string]: unknown }>({
    columns,
    dataSource,
    headerTitle,
    onReset,
    onSubmit,
    rowKey,
    toolBarRender,
  }: {
    columns: Array<{
      dataIndex?: keyof Row;
      hideInTable?: boolean;
      key?: string;
      render?: (value: unknown, row: Row) => React.ReactNode;
      search?: false;
      title: React.ReactNode;
      valueEnum?: Record<string, { text: React.ReactNode }>;
      valueType?: string;
    }>;
    dataSource: Row[];
    headerTitle?: React.ReactNode;
    onReset?: () => void;
    onSubmit?: (values: Record<string, FormDataEntryValue>) => void;
    rowKey: keyof Row;
    toolBarRender?: () => React.ReactNode[];
  }) {
    const searchColumns = columns.filter((column) => column.search !== false);
    const tableColumns = columns.filter((column) => !column.hideInTable);

    return React.createElement(
      'section',
      null,
      headerTitle ? React.createElement('h2', null, headerTitle) : null,
      React.createElement(
        'form',
        {
          'aria-label': '查询表格',
          onReset: () => onReset?.(),
          onSubmit: (event: React.FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            onSubmit?.(Object.fromEntries(new FormData(event.currentTarget)));
          },
        },
        searchColumns.map((column) =>
          React.createElement(
            'label',
            { key: String(column.dataIndex) },
            column.title,
            column.valueType === 'select'
              ? React.createElement(
                  'select',
                  { name: String(column.dataIndex) },
                  React.createElement('option', { value: '' }, '全部'),
                  Object.entries(column.valueEnum ?? {}).map(([value, option]) =>
                    React.createElement('option', { key: value, value }, option.text),
                  ),
                )
              : React.createElement('input', { name: String(column.dataIndex), type: 'text' }),
          ),
        ),
        React.createElement('button', { type: 'submit' }, '查询'),
        React.createElement('button', { type: 'reset' }, '重置'),
      ),
      toolBarRender?.(),
      React.createElement(
        'table',
        null,
        React.createElement(
          'thead',
          null,
          React.createElement(
            'tr',
            null,
            tableColumns.map((column) =>
              React.createElement('th', { key: String(column.key ?? column.dataIndex) }, column.title),
            ),
          ),
        ),
        React.createElement(
          'tbody',
          null,
          dataSource.map((row) =>
            React.createElement(
              'tr',
              { key: String(row[rowKey]) },
              tableColumns.map((column) =>
                React.createElement(
                  'td',
                  { key: String(column.key ?? column.dataIndex ?? column.title) },
                  column.render
                    ? column.render(column.dataIndex ? row[column.dataIndex] : undefined, row)
                    : String(column.dataIndex ? row[column.dataIndex] : ''),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  function StatisticCard({ statistic }: { statistic: Record<string, React.ReactNode> }) {
    return React.createElement(
      'section',
      null,
      statistic.prefix,
      React.createElement('h3', null, statistic.title),
      React.createElement('p', null, statistic.value),
      React.createElement('p', null, statistic.description),
    );
  }

  StatisticCard.Group = ({ children }: { children?: React.ReactNode }) =>
    React.createElement('section', null, children);

  function QueryFilter({
    children,
    'aria-label': ariaLabel,
    onFinish,
    onReset,
  }: {
    'aria-label'?: string;
    children?: React.ReactNode;
    onFinish?: (values: Record<string, FormDataEntryValue>) => void;
    onReset?: () => void;
  }) {
    return React.createElement(
      'form',
      {
        'aria-label': ariaLabel ?? '查询条件',
        onReset: () => onReset?.(),
        onSubmit: (event: React.FormEvent<HTMLFormElement>) => {
          event.preventDefault();
          onFinish?.(Object.fromEntries(new FormData(event.currentTarget)));
        },
      },
      children,
      React.createElement('button', { type: 'submit' }, '查询'),
      React.createElement('button', { type: 'reset' }, '重置'),
    );
  }

  function ProFormText({ label, name }: { label: React.ReactNode; name: string }) {
    return React.createElement(
      'label',
      null,
      label,
      React.createElement('input', { name, type: 'text' }),
    );
  }

  function ProFormSelect({
    label,
    name,
    options = [],
  }: {
    label: React.ReactNode;
    name: string;
    options?: Array<{ label: string; value: string }>;
  }) {
    return React.createElement(
      'label',
      null,
      label,
      React.createElement(
        'select',
        { name },
        React.createElement('option', { value: '' }, '全部'),
        options.map((option) =>
          React.createElement('option', { key: option.value, value: option.value }, option.label),
        ),
      ),
    );
  }

  return { PageContainer, ProCard, ProFormSelect, ProFormText, ProTable, QueryFilter, StatisticCard };
});

import BugsPage from '../src/pages/Bugs';
import AuditPage from '../src/pages/Audit';
import DashboardPage from '../src/pages/Dashboard';
import DevopsPage from '../src/pages/Devops';
import InsightsPage from '../src/pages/Insights';
import KnowledgePage from '../src/pages/Knowledge';
import LoginPage from '../src/pages/Login';
import ProductsPage from '../src/pages/Products';
import RequirementsPage from '../src/pages/Requirements';
import { apiRequest } from '../src/services/aiBrain';
import { handleLogout, redirectToLoginIfNeeded } from '../src/runtimeAuth';
import TaskCenterPage from '../src/pages/TaskCenter';

describe('AI Brain Ant Design Pro workbench', () => {
  afterEach(() => {
    cleanup();
    window.localStorage.clear();
    window.history.pushState({}, '', '/');
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('registers the MVP workbench entries through Umi route config', () => {
    const routes = readFileSync(join(__dirname, '..', 'config', 'routes.ts'), 'utf8');

    expect(routes).toContain("path: '/login'");
    expect(routes).toContain("component: './Login'");
    expect(routes).toContain('layout: false');
    expect(routes).toContain("path: '/welcome'");
    expect(routes).toContain("name: '欢迎'");
    expect(routes).toContain("path: '/tasks'");
    expect(routes).toContain("name: '任务中心'");
    expect(routes).toContain("path: '/tasks/management'");
    expect(routes).toContain("name: '任务管理'");
    expect(routes).toContain("redirect: '/tasks/management'");
    expect(routes).toContain("redirect: '/login'");
    expect(routes).not.toContain("name: '工作台'");
    expect(routes).toContain("name: '需求交付'");
    expect(routes).toContain("name: '产品资产'");
    expect(routes).toContain("name: '运营治理'");
    expect(routes).toContain("name: '产品管理'");
    expect(routes).toContain("name: '需求管理'");
    expect(routes).toContain("name: '知识中心'");
    expect(routes).toContain("name: '审计与运行'");
    expect(routes).toContain("path: '/delivery/requirements'");
    expect(routes).toContain("path: '/assets/products'");
    expect(routes).toContain("path: '/governance/audit'");
    expect(routes).toContain("component: './TaskCenter'");
  });

  it('logs in with the development account and redirects to the requested page', async () => {
    window.history.pushState({}, '', '/login?redirect=%2Fdelivery%2Fbugs');
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(input).toBe('/api/auth/login');
      expect(init?.method).toBe('POST');
      expect(JSON.parse(String(init?.body))).toEqual({
        password: 'admin123',
        username: 'admin@example.com',
      });
      return new Response(
        JSON.stringify({
          data: {
            access_token: 'token-admin',
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<LoginPage />);
    fireEvent.click(screen.getByRole('button', { name: /登\s*录/ }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(window.localStorage.getItem('ai_brain_access_token')).toBe('token-admin');
    expect(window.location.pathname).toBe('/delivery/bugs');
  });

  it('sends already authenticated users away from the login page', async () => {
    window.history.pushState({}, '', '/login');
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');

    render(<LoginPage />);

    await waitFor(() => expect(window.location.pathname).toBe('/welcome'));
  });

  it('redirects anonymous users to login and clears the session on logout', async () => {
    expect(redirectToLoginIfNeeded('/delivery/bugs', '?severity=critical')).toBe(true);
    expect(window.location.pathname).toBe('/login');
    expect(window.location.search).toBe('?redirect=%2Fdelivery%2Fbugs%3Fseverity%3Dcritical');

    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    window.history.pushState({}, '', '/delivery/bugs');
    expect(redirectToLoginIfNeeded('/delivery/bugs')).toBe(false);

    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(input).toBe('/api/auth/logout');
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      return new Response(JSON.stringify({ data: { success: true } }), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    await handleLogout();

    expect(window.localStorage.getItem('ai_brain_access_token')).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(window.location.pathname).toBe('/login');
  });

  it('renders the task center with Pro page content first screen', () => {
    render(<TaskCenterPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '任务管理' })).not.toBeInTheDocument();
    expect(
      screen.queryByText('研发大脑 v1 MVP：从需求审批到方案确认、GitLab 输入快照、内部 Review 和知识沉淀。'),
    ).not.toBeInTheDocument();
    expect(screen.getByText('任务列表')).toBeInTheDocument();
    expect(screen.getByText('MVP-A 基础 + GitLab 输入闭环')).toBeInTheDocument();
    expect(screen.getByText('产品详细设计')).toBeInTheDocument();
    expect(screen.getByText('确认台')).toBeInTheDocument();
  });

  it('renders non-ledger module overview pages from shared Pro page scaffolding', () => {
    const { rerender } = render(<DashboardPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '欢迎' })).not.toBeInTheDocument();
    expect(screen.getByText('欢迎使用 AI Brain')).toBeInTheDocument();
    expect(screen.getByText('从左侧菜单进入任务中心、需求交付、产品资产和运营治理。')).toBeInTheDocument();

    rerender(<DevopsPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '研发运营看板' })).not.toBeInTheDocument();
    expect(screen.queryByText('后续阶段')).not.toBeInTheDocument();
    expect(screen.queryByText('GitLab/Jenkins/线上日志真实运营采集属于后续增强。')).not.toBeInTheDocument();
    expect(screen.getByText('GitLab 指标')).toBeInTheDocument();

    rerender(<InsightsPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '用户洞察/迭代规划' })).not.toBeInTheDocument();
    expect(screen.queryByText('后续阶段')).not.toBeInTheDocument();
    expect(screen.queryByText('当前预留入口，后续接入用户使用、反馈和 AI 迭代建议。')).not.toBeInTheDocument();
    expect(screen.getByText('使用趋势')).toBeInTheDocument();
  });

  it('renders management modules as query filters with table lists', () => {
    const { rerender } = render(<ProductsPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('产品资产');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('工作台');
    expect(screen.queryByRole('heading', { level: 1, name: '产品管理' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('产品列表')).toBeInTheDocument();
    expect(screen.getAllByText('产品编码')).not.toHaveLength(0);
    expect(screen.getByText('AI-BRAIN')).toBeInTheDocument();

    rerender(<RequirementsPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('需求交付');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.queryByRole('heading', { level: 1, name: '需求管理' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(
      screen.queryByText('按产品、标题、状态和优先级查询需求台账，并从列表进入审批、关闭和生成 AI 任务操作。'),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('需求列表')).toBeInTheDocument();
    expect(screen.getAllByText('需求标题')).not.toHaveLength(0);
    expect(screen.getByText('产品详细设计辅助')).toBeInTheDocument();

    rerender(<BugsPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('需求交付');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.queryByRole('heading', { level: 1, name: 'Bug 管理' })).not.toBeInTheDocument();
    expect(screen.queryByText('MVP 占位数据')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('Bug 列表')).toBeInTheDocument();
    expect(screen.getAllByText('严重级别')).not.toHaveLength(0);
    expect(screen.getByText('登录态过期提示异常')).toBeInTheDocument();

    rerender(<KnowledgePage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('产品资产');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.queryByRole('heading', { level: 1, name: '知识中心' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('知识列表')).toBeInTheDocument();
    expect(screen.getAllByText('知识标题')).not.toHaveLength(0);
    expect(screen.getByText('AI Brain v1 产品需求文档')).toBeInTheDocument();

    rerender(<AuditPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('运营治理');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.queryByRole('heading', { level: 1, name: '审计与运行' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('审计列表')).toBeInTheDocument();
    expect(screen.getAllByText('事件类型')).not.toHaveLength(0);
    expect(screen.getByText('requirement.approved')).toBeInTheDocument();
  });

  it('filters management table rows from query conditions', () => {
    render(<ProductsPage />);

    fireEvent.change(screen.getByLabelText('产品编码'), { target: { value: 'RD-BRAIN' } });
    fireEvent.submit(screen.getByRole('form', { name: '查询表格' }));

    expect(screen.getByText('RD-BRAIN')).toBeInTheDocument();
    expect(screen.queryByText('AI-BRAIN')).not.toBeInTheDocument();

    fireEvent.reset(screen.getByRole('form', { name: '查询表格' }));

    expect(screen.getByText('AI-BRAIN')).toBeInTheDocument();
  });

  it('hydrates management tables from backend API list endpoints when available', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);

      if (path === '/api/products') {
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
      if (path === '/api/requirements') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                created_at: '2026-05-30T08:30:00+00:00',
                id: 'requirement_api',
                priority: 'P0',
                product_id: 'product_api',
                status: 'approved',
                title: '接口需求',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/knowledge/documents') {
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
      if (path === '/api/bugs') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                assignee: 'rd_owner@example.com',
                id: 'bug_api',
                module_code: 'knowledge',
                severity: 'critical',
                source: 'ai_auto_test',
                status: 'needs_info',
                title: '接口 Bug',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/audit/events') {
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

    const { rerender } = render(<ProductsPage />);

    expect(await screen.findByText('API-PRODUCT')).toBeInTheDocument();
    expect(screen.queryByText('AI-BRAIN')).not.toBeInTheDocument();

    rerender(<RequirementsPage />);

    expect(await screen.findByText('接口需求')).toBeInTheDocument();
    expect(screen.getByText('API-PRODUCT')).toBeInTheDocument();

    rerender(<BugsPage />);

    expect(await screen.findByText('接口 Bug')).toBeInTheDocument();
    expect(screen.getAllByText('致命')).not.toHaveLength(0);
    expect(screen.getAllByText('待补充')).not.toHaveLength(0);

    rerender(<KnowledgePage />);

    expect(await screen.findByText('接口知识文档')).toBeInTheDocument();
    expect(screen.getByText('admin, rd_owner')).toBeInTheDocument();

    rerender(<AuditPage />);

    expect(await screen.findByText('product.created')).toBeInTheDocument();
    expect(screen.getByText('product: product_api')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith('/api/auth/login', expect.anything());
  });

  it('shows backend load failures when management tables fall back to local examples', async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      new Response(
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
      ),
    );
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<ProductsPage />);

    expect(screen.getByText('AI-BRAIN')).toBeInTheDocument();
    expect(await screen.findByText(/接口异常，当前展示示例数据/)).toBeInTheDocument();
    expect(screen.getByText(/FORBIDDEN/)).toBeInTheDocument();
    expect(screen.getByText(/trace_denied/)).toBeInTheDocument();
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

  it('runs the MVP API workflow and renders the resulting task context', async () => {
    const responses = [
      { data: { id: 'product_001' } },
      { data: { id: 'version_001' } },
      { data: { id: 'requirement_001', status: 'pending_approval' } },
      { data: { id: 'requirement_001', status: 'approved' } },
      { data: { task_id: 'task_001', task_status: 'draft' } },
      {
        data: {
          id: 'task_001',
          status: 'waiting_review',
          review_id: 'review_001',
          current_step: 'interrupt_for_human_review',
        },
      },
      {
        data: {
          id: 'task_001',
          status: 'waiting_review',
          current_step: 'interrupt_for_human_review',
          output: { kind: 'product_detail_design' },
        },
      },
      {
        data: {
          status: 'available',
          summary: { downstream_count: 7, risk_count: 0 },
        },
      },
    ];
    const fetchMock = vi.fn<typeof fetch>(async () => {
      const body = responses.shift();
      if (!body) {
        throw new Error('Unexpected fetch call');
      }
      return new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);
    fireEvent.click(screen.getByRole('button', { name: '运行 MVP 演示流程' }));

    expect(await screen.findAllByText('waiting_review')).not.toHaveLength(0);
    expect(screen.getByText('task_001')).toBeInTheDocument();
    expect(screen.getByText('review_001')).toBeInTheDocument();
    expect(screen.getByText('interrupt_for_human_review')).toBeInTheDocument();
    expect(screen.getByText('下游关系 7')).toBeInTheDocument();

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(8));
    expect(fetchMock.mock.calls[0][0]).toBe('/api/products');
    expect(fetchMock.mock.calls[5][0]).toBe('/api/ai-tasks/task_001/start');
    expect(fetchMock.mock.calls[7][0]).toContain('/api/lifecycle/context?subject_type=requirement');
    expect(fetchMock.mock.calls[7][1]?.headers).toMatchObject({
      Authorization: 'Bearer token-admin',
    });
    expect(fetchMock).not.toHaveBeenCalledWith('/api/auth/login', expect.anything());
  });
});
