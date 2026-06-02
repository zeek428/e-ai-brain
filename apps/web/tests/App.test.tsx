import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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
import ModelGatewayPage from '../src/pages/ModelGateway';
import ProductsPage from '../src/pages/Products';
import RequirementsPage from '../src/pages/Requirements';
import RolesPage from '../src/pages/Roles';
import UsersPage from '../src/pages/Users';
import {
  approveManagementRequirement,
  approveKnowledgeDeposit,
  approveTaskCenterReview,
  apiRequest,
  AUTH_STATE_EVENT,
  clearAccessToken,
  createAutomatedTestingTask,
  createDevelopmentPlanningTask,
  createPostReleaseAnalysisTask,
  createReleaseReadinessTask,
  createManagementBug,
  createModelGatewayConfig,
  createTaskWritebackResult,
  createManagementKnowledgeDocument,
  createManagementProduct,
  createManagementRequirement,
  createManagementUser,
  createCodeReviewTask,
  createTechnicalSolutionTask,
  deleteManagementBug,
  deleteModelGatewayConfig,
  deleteManagementKnowledgeDocument,
  deleteManagementProduct,
  deleteManagementRequirement,
  deleteManagementUser,
  fetchActiveProductOptions,
  fetchItTeamDashboard,
  fetchModelGatewayConfigs,
  fetchTaskMarkdown,
  fetchCodeReviewReport,
  fetchKnowledgeDeposits,
  fetchKnowledgeSearchResults,
  fetchProductGitRepositories,
  fetchTaskWritebackResult,
  generateRequirementTask,
  previewGitLabMergeRequest,
  rejectKnowledgeDeposit,
  rejectManagementRequirement,
  requestTaskCenterReviewMoreInfo,
  snapshotGitLabMergeRequest,
  saveCurrentUser,
  startTaskCenterTask,
  submitTaskCenterMoreInfo,
  updateManagementBug,
  updateManagementKnowledgeDocument,
  updateManagementProduct,
  updateManagementRequirement,
  updateManagementUser,
  updateModelGatewayConfig,
} from '../src/services/aiBrain';
import { handleLogout, redirectToLoginIfNeeded } from '../src/runtimeAuth';
import TaskCenterPage from '../src/pages/TaskCenter';
import { getInitialState } from '../src/app';

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
    expect(routes).toContain("name: '系统管理'");
    expect(routes).toContain("name: '产品管理'");
    expect(routes).toContain("name: '需求管理'");
    expect(routes).toContain("name: '知识中心'");
    expect(routes).toContain("name: '审计与运行'");
    expect(routes).toContain("path: '/delivery/requirements'");
    expect(routes).toContain("path: '/assets/products'");
    expect(routes).toContain("path: '/governance/audit'");
    expect(routes).not.toContain("path: '/governance/users'");
    expect(routes).toContain("path: '/system/users'");
    expect(routes).toContain("name: '用户管理'");
    expect(routes).toContain("path: '/system/roles'");
    expect(routes).toContain("name: '角色管理'");
    expect(routes).toContain("component: './Roles'");
    expect(routes).toContain("path: '/system/model-gateway'");
    expect(routes).toContain("name: '模型网关'");
    expect(routes).toContain("component: './ModelGateway'");
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
            user: {
              display_name: 'AI Brain Admin',
              id: 'user_admin',
              roles: ['admin'],
              username: 'admin@example.com',
            },
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

  it('hydrates the layout user from the authenticated current-user API', async () => {
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(input).toBe('/api/auth/me');
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      return new Response(
        JSON.stringify({
          data: {
            display_name: '真实用户',
            id: 'user_real',
            roles: ['product_owner', 'rd_owner'],
            username: 'real@example.com',
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(getInitialState()).resolves.toEqual({
      currentUser: {
        name: '真实用户',
        role: 'product_owner, rd_owner',
      },
    });
    expect(window.localStorage.getItem('ai_brain_current_user')).toContain('real@example.com');
  });

  it('notifies the layout when local auth state changes', () => {
    const listener = vi.fn();
    window.addEventListener(AUTH_STATE_EVENT, listener);

    saveCurrentUser({
      display_name: 'AI Brain Admin',
      id: 'user_admin',
      roles: ['admin'],
      username: 'admin@example.com',
    });
    clearAccessToken();

    window.removeEventListener(AUTH_STATE_EVENT, listener);
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it('sends already authenticated users away from the login page', async () => {
    window.history.pushState({}, '', '/login');
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(async (input, init) => {
        expect(input).toBe('/api/auth/me');
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return new Response(
          JSON.stringify({
            data: {
              display_name: 'AI Brain Admin',
              id: 'user_admin',
              roles: ['admin'],
              username: 'admin@example.com',
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }),
    );

    render(<LoginPage />);

    await waitFor(() => expect(window.location.pathname).toBe('/welcome'));
  });

  it('keeps users on login and clears stale tokens when the stored token is invalid', async () => {
    window.history.pushState({}, '', '/login');
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
              trace_id: 'trace_login_expired',
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 401,
          },
        ),
      ),
    );

    render(<LoginPage />);

    await waitFor(() => {
      expect(window.localStorage.getItem('ai_brain_access_token')).toBeNull();
    });
    expect(window.localStorage.getItem('ai_brain_current_user')).toBeNull();
    expect(window.location.pathname).toBe('/login');
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

  it('renders the task center from backend tasks without a demo workflow', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/reviews/pending') {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  ai_task_id: 'task_api',
                  content: { summary: '接口任务输出摘要' },
                  id: 'review_api',
                  stage: 'product_detail_design',
                  status: 'pending',
                  version: 1,
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
      expect(input).toBe('/api/ai-tasks');
      return new Response(
        JSON.stringify({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_api',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'waiting_review',
                task_type: 'product_detail_design',
                title: '接口任务',
              },
              {
                created_by: 'user_admin',
                id: 'task_design_done',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'product_detail_design',
                title: '已确认详细设计',
              },
              {
                created_by: 'user_admin',
                id: 'task_solution_done',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'technical_solution',
                title: '技术方案：接口任务',
              },
              {
                created_by: 'user_admin',
                id: 'task_code_review',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'waiting_review',
                task_type: 'code_review',
                title: 'Code Review：接口任务',
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
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '任务管理' })).not.toBeInTheDocument();
    expect(
      screen.queryByText('研发大脑 v1 MVP：从需求审批到方案确认、GitLab 输入快照、内部 Review 和知识沉淀。'),
    ).not.toBeInTheDocument();
    expect(screen.getByText('任务列表')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('任务中心');
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.queryByText('MVP-A 基础 + GitLab 输入闭环')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '运行 MVP 演示流程' })).not.toBeInTheDocument();
    expect(await screen.findByText('接口任务')).toBeInTheDocument();
    expect(screen.getAllByText('产品详细设计')).not.toHaveLength(0);
    expect(screen.getByRole('button', { name: '待确认' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '操作' })).toHaveLength(4);
    expect(screen.queryByRole('button', { name: '确认输出' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '生成技术方案' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '导出 Markdown' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '模拟 Issue' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '创建 Code Review' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '生成开发计划' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '生成自动化测试' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '生成发布评估' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '查看报告' })).not.toBeInTheDocument();
    expect(screen.queryByText('确认台')).not.toBeInTheDocument();
    expect(screen.queryByText('确认编号')).not.toBeInTheDocument();
    const completedTaskRow = screen.getByText('技术方案：接口任务').closest('tr');
    expect(completedTaskRow).not.toBeNull();
    fireEvent.click(within(completedTaskRow as HTMLElement).getByRole('button', { name: '操作' }));
    const operationDialog = await screen.findByTestId('task-operation-dialog');
    const summarySection = screen.getByTestId('task-operation-summary');
    const actionSection = screen.getByTestId('task-operation-actions');
    expect(screen.getByText('任务操作')).toBeInTheDocument();
    expect(summarySection).toHaveTextContent('技术方案：接口任务');
    expect(operationDialog).toContainElement(summarySection);
    expect(operationDialog).toContainElement(actionSection);
    expect(summarySection.compareDocumentPosition(actionSection)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(actionSection).toHaveClass('task-operation-actions');
    expect(screen.getByRole('button', { name: '生成开发计划' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成自动化测试' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成发布评估' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '创建 Code Review' })).toBeInTheDocument();
    fireEvent.click(screen.getAllByLabelText('Close')[0]);
    fireEvent.click(screen.getByRole('button', { name: '待确认' }));
    expect(await screen.findByText('接口任务输出摘要')).toBeInTheDocument();
    expect(screen.getAllByText('确认编号')).not.toHaveLength(0);
    expect(screen.getByRole('button', { name: '确认通过' })).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  });

  it('opens task row operations in vertical dialogs aligned with management pages', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/reviews/pending') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ai-tasks') {
        return jsonResponse({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_solution_done',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'technical_solution',
                title: '技术方案：弹窗操作',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/products/product_api/git-repositories?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              {
                default_branch: 'main',
                git_provider: 'gitlab',
                id: 'repo_api',
                name: 'AI Brain 仓库',
                project_path: 'platform/ai-brain',
                status: 'active',
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

    render(<TaskCenterPage />);

    expect(await screen.findByText('技术方案：弹窗操作')).toBeInTheDocument();
    const taskRow = screen.getByText('技术方案：弹窗操作').closest('tr');
    expect(taskRow).not.toBeNull();
    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));

    expect(await screen.findByText('任务操作')).toBeInTheDocument();
    expect(screen.getByTestId('task-operation-summary')).toHaveTextContent('技术方案：弹窗操作');
    expect(screen.queryByText('确认台')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '创建 Code Review' }));

    expect(await screen.findByText(/创建 Code Review：技术方案：弹窗操作/)).toBeInTheDocument();
    const codeReviewForm = screen.getByRole('form', { name: '创建 Code Review 参数' });
    expect(codeReviewForm).toHaveClass('ant-form-vertical');
    expect(codeReviewForm).not.toHaveClass('ant-form-inline');
    expect(screen.getByText('AI Brain 仓库 (platform/ai-brain)')).toBeInTheDocument();
  });

  it('offers post-release analysis from completed release readiness rows', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/reviews/pending') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      expect(input).toBe('/api/ai-tasks');
      return jsonResponse({
        data: {
          items: [
            {
              created_by: 'user_admin',
              id: 'task_release_done',
              product_id: 'product_api',
              requirement_id: 'requirement_api',
              status: 'completed',
              task_type: 'release_readiness',
              title: '发布评估：弹窗操作',
            },
          ],
          total: 1,
        },
      });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('发布评估：弹窗操作')).toBeInTheDocument();
    const taskRow = screen.getByText('发布评估：弹窗操作').closest('tr');
    expect(taskRow).not.toBeNull();
    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));

    expect(await screen.findByText('任务操作')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成上线后分析' })).toBeInTheDocument();
  });

  it('opens mock issue writeback from completed task rows', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/reviews/pending') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ai-tasks') {
        return jsonResponse({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_solution_done',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'completed',
                task_type: 'technical_solution',
                title: '技术方案：写回需求',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/writeback/results/task_solution_done' && init?.method !== 'POST') {
        return jsonResponse({
          data: {
            idempotency_key: 'mock_issue:task_solution_done',
            issues: [],
            status: 'not_written',
            task_id: 'task_solution_done',
          },
        });
      }
      if (input === '/api/writeback/results/task_solution_done' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            idempotency_key: 'mock_issue:task_solution_done',
            issues: [
              {
                id: 'mock_issue_api',
                source_task_id: 'task_solution_done',
                status: 'open',
                title: '技术方案：写回需求',
              },
            ],
            status: 'completed',
            task_id: 'task_solution_done',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('技术方案：写回需求')).toBeInTheDocument();
    const taskRow = screen.getByText('技术方案：写回需求').closest('tr');
    expect(taskRow).not.toBeNull();
    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));

    expect(await screen.findByText('任务操作')).toBeInTheDocument();
    expect(screen.getByTestId('task-operation-summary')).toHaveTextContent('技术方案：写回需求');
    expect(screen.getByRole('button', { name: '创建 Code Review' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '模拟 Issue' }));

    expect(await screen.findByText(/模拟 Issue 写回/)).toBeInTheDocument();
    expect(screen.getByText('未写回')).toBeInTheDocument();
    expect(screen.getByText('mock_issue:task_solution_done')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '生成模拟 Issue' }));

    expect(await screen.findByText('已生成')).toBeInTheDocument();
    expect(screen.getByText('mock_issue_api')).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toEqual([
      ['/api/ai-tasks', 'GET'],
      ['/api/reviews/pending', 'GET'],
      ['/api/writeback/results/task_solution_done', 'GET'],
      ['/api/writeback/results/task_solution_done', 'POST'],
    ]);
  });

  it('requests and submits more information from task management dialogs', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/ai-tasks') {
        return jsonResponse({
          data: {
            items: [
              {
                created_by: 'user_admin',
                id: 'task_more_info',
                product_id: 'product_api',
                requirement_id: 'requirement_api',
                status: 'waiting_more_info',
                task_type: 'product_detail_design',
                title: '待补充详细设计',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/reviews/pending') {
        return jsonResponse({
          data: {
            items: [
              {
                ai_task_id: 'task_review',
                content: { summary: '需要人工确认的输出' },
                id: 'review_more_info',
                stage: 'product_detail_design',
                status: 'pending',
                version: 1,
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/reviews/review_more_info/request-more-info') {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toEqual({
          questions: ['请补充验收边界'],
          version: 1,
        });
        return jsonResponse({
          data: {
            review_status: 'requested_more_info',
            task_status: 'waiting_more_info',
          },
        });
      }
      if (input === '/api/ai-tasks/task_more_info/more-info') {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toEqual({
          answers: [{ answer: '补充 P0 验收边界', question: '补充说明' }],
        });
        return jsonResponse({ data: { id: 'task_more_info', status: 'draft' } });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    expect(await screen.findByText('待补充详细设计')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '待确认' }));
    expect(await screen.findByText('需要人工确认的输出')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '要求补充' }));
    fireEvent.change(screen.getByLabelText('补充问题'), {
      target: { value: '请补充验收边界' },
    });
    fireEvent.click(screen.getByRole('button', { name: '提交补充问题' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/reviews/review_more_info/request-more-info',
        'POST',
      ]),
    );

    const taskRow = screen.getByText('待补充详细设计').closest('tr');
    expect(taskRow).not.toBeNull();
    fireEvent.click(within(taskRow as HTMLElement).getByRole('button', { name: '操作' }));
    expect(await screen.findByText('任务操作')).toBeInTheDocument();
    expect(screen.getByTestId('task-operation-summary')).toHaveTextContent('待补充详细设计');
    fireEvent.click(screen.getByRole('button', { name: '提交补充信息' }));
    fireEvent.change(screen.getByLabelText('补充说明'), {
      target: { value: '补充 P0 验收边界' },
    });
    fireEvent.click(screen.getByRole('button', { name: '提交补充内容' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/ai-tasks/task_more_info/more-info',
        'POST',
      ]),
    );
  });

  it('manages model gateway configs without exposing api keys', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/system/model-gateway-configs') {
        if (init?.method === 'POST') {
          expect(JSON.parse(String(init.body))).toMatchObject({
            api_key: 'sk-live-secret',
            base_url: 'https://api.example.com/v1',
            default_chat_model: 'gpt-4.1',
            default_embedding_model: 'text-embedding-3-large',
            is_default: true,
            max_retries: 2,
            name: '新模型网关',
            provider: 'openai_compatible',
            status: 'active',
            timeout_seconds: 90,
          });
          return jsonResponse({
            data: {
              api_key_configured: true,
              base_url: 'https://api.example.com/v1',
              default_chat_model: 'gpt-4.1',
              default_embedding_model: 'text-embedding-3-large',
              id: 'model_config_new',
              is_default: true,
              max_retries: 2,
              name: '新模型网关',
              provider: 'openai_compatible',
              status: 'active',
              timeout_seconds: 90,
            },
          });
        }
        return jsonResponse({
          data: {
            items: [
              {
                api_key_configured: true,
                base_url: 'https://api.example.com/v1',
                default_chat_model: 'gpt-4.1',
                default_embedding_model: 'text-embedding-3-large',
                id: 'model_config_default',
                is_default: true,
                max_retries: 1,
                name: '默认模型网关',
                provider: 'openai_compatible',
                status: 'active',
                timeout_seconds: 60,
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/system/model-gateway-configs/model_config_default') {
        if (init?.method === 'PATCH') {
          const body = JSON.parse(String(init.body));
          expect(body).toMatchObject({
            base_url: 'https://api.example.com/v1',
            default_chat_model: 'gpt-4.1-mini',
            default_embedding_model: 'text-embedding-3-large',
            is_default: true,
            max_retries: 1,
            name: '默认模型网关',
            provider: 'openai_compatible',
            status: 'active',
            timeout_seconds: 60,
          });
          expect(body).not.toHaveProperty('api_key');
          return jsonResponse({
            data: {
              api_key_configured: true,
              base_url: 'https://api.example.com/v1',
              default_chat_model: 'gpt-4.1-mini',
              default_embedding_model: 'text-embedding-3-large',
              id: 'model_config_default',
              is_default: true,
              max_retries: 1,
              name: '默认模型网关',
              provider: 'openai_compatible',
              status: 'active',
              timeout_seconds: 60,
            },
          });
        }
        if (init?.method === 'DELETE') {
          return jsonResponse({ data: { deleted: true, id: 'model_config_default' } });
        }
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<ModelGatewayPage />);

    expect(await screen.findByText('默认模型网关')).toBeInTheDocument();
    expect(screen.getByText('模型网关配置')).toBeInTheDocument();
    expect(screen.getByText('已配置')).toBeInTheDocument();
    expect(screen.queryByText('sk-live-secret')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /新增配置/ }));
    let dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('配置名称'), { target: { value: '新模型网关' } });
    fireEvent.change(within(dialog).getByLabelText('Provider'), { target: { value: 'openai_compatible' } });
    fireEvent.change(within(dialog).getByLabelText('Base URL'), { target: { value: 'https://api.example.com/v1' } });
    fireEvent.change(within(dialog).getByLabelText('API Key'), { target: { value: 'sk-live-secret' } });
    fireEvent.change(within(dialog).getByLabelText('默认 Chat 模型'), { target: { value: 'gpt-4.1' } });
    fireEvent.change(within(dialog).getByLabelText('默认 Embedding 模型'), {
      target: { value: 'text-embedding-3-large' },
    });
    fireEvent.change(within(dialog).getByLabelText('超时秒数'), { target: { value: '90' } });
    fireEvent.change(within(dialog).getByLabelText('最大重试'), { target: { value: '2' } });
    fireEvent.click(within(dialog).getByLabelText('默认配置'));
    fireEvent.click(within(dialog).getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/system/model-gateway-configs',
        'POST',
      ]),
    );

    fireEvent.click(screen.getAllByRole('button', { name: /编辑/ })[0]);
    dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('默认 Chat 模型'), { target: { value: 'gpt-4.1-mini' } });
    fireEvent.click(within(dialog).getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/system/model-gateway-configs/model_config_default',
        'PATCH',
      ]),
    );
  });

  it('opens knowledge deposit review and approves a pending deposit', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/knowledge/documents') {
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
      if (input === '/api/knowledge/documents') {
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
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toEqual([
      ['/api/knowledge/documents', 'GET'],
      ['/api/auth/roles', 'GET'],
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
      if (input === '/api/knowledge/documents') {
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
    await waitFor(() => expect(screen.getByText('已索引')).toBeInTheDocument());
  });

  it('renders dashboard and operation pages without placeholder data', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      if (input === '/api/dashboard/it-team') {
        return jsonResponse({
          data: {
            latest_tasks: [
              {
                id: 'task_dashboard',
                status: 'waiting_review',
                task_type: 'product_detail_design',
                title: '首页看板任务',
              },
            ],
            pending_reviews: [{ id: 'review_dashboard', stage: 'product_detail_design' }],
            recent_audit_events: [
              { event_type: 'ai_task.started', id: 'audit_dashboard' },
            ],
            recent_knowledge_documents: [{ id: 'knowledge_dashboard', title: '首页知识' }],
            bug_status_counts: [{ count: 2, status: 'open' }],
            gitlab_daily_summary: {
              average_quality_score: 88.5,
              changed_files: 12,
              commit_count: 9,
              merge_request_count: 2,
              metric_count: 1,
              risk_count: 1,
            },
            iteration_suggestion_status_counts: [{ count: 1, status: 'suggested' }],
            jenkins_release_status_counts: [{ count: 1, status: 'failed' }],
            latest_high_severity_bugs: [
              {
                id: 'bug_dashboard',
                severity: 'critical',
                status: 'open',
                title: '首页严重 Bug',
              },
            ],
            online_log_summary: {
              error_count: 4,
              error_rate: 0.02,
              max_p95_latency_ms: 318.5,
              max_p99_latency_ms: 640.25,
              metric_count: 1,
              request_count: 200,
            },
            requirement_status_counts: [
              { count: 1, status: 'pending_approval' },
              { count: 1, status: 'task_created' },
            ],
            summary: {
              active_products: 1,
              ai_tasks: 3,
              audit_events: 8,
              bugs: 2,
              gitlab_commits: 9,
              high_severity_bugs: 1,
              iteration_suggestions: 1,
              jenkins_releases: 1,
              knowledge_deposits: 2,
              knowledge_documents: 4,
              online_errors: 4,
              open_bugs: 2,
              pending_reviews: 1,
              requirements: 5,
              usage_events: 120,
              user_feedback: 3,
            },
            task_status_counts: [{ count: 1, status: 'waiting_review' }],
            time_range: '7d',
            usage_metric_summary: {
              active_users: 42,
              conversion_count: 15,
              error_count: 2,
              event_count: 120,
              metric_count: 1,
            },
            user_feedback_status_counts: [{ count: 3, status: 'open' }],
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    const { rerender } = render(<DashboardPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '欢迎' })).not.toBeInTheDocument();
    expect(screen.queryByText('欢迎使用 AI Brain')).not.toBeInTheDocument();
    expect(screen.queryByText('从左侧菜单进入任务中心、需求交付、产品资产和运营治理。')).not.toBeInTheDocument();
    expect(await screen.findByText('IT 团队看板')).toBeInTheDocument();
    expect(screen.getByText('需求总数')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('首页看板任务')).toBeInTheDocument();
    expect(screen.getByText('首页知识')).toBeInTheDocument();
    expect(screen.getByText('ai_task.started')).toBeInTheDocument();
    expect(screen.getByText('开放 Bug')).toBeInTheDocument();
    expect(screen.getByText('严重 Bug')).toBeInTheDocument();
    expect(screen.getByText('GitLab 提交')).toBeInTheDocument();
    expect(screen.getByText('发布记录')).toBeInTheDocument();
    expect(screen.getByText('用户反馈')).toBeInTheDocument();
    expect(screen.getByText('使用事件')).toBeInTheDocument();
    expect(screen.getAllByText('迭代建议').length).toBeGreaterThan(0);
    expect(screen.getByText('首页严重 Bug')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Bug 明细/ })).toHaveAttribute(
      'href',
      '/delivery/bugs',
    );
    expect(screen.getByRole('link', { name: /运营明细/ })).toHaveAttribute(
      'href',
      '/governance/devops',
    );

    rerender(<DevopsPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '研发运营看板' })).not.toBeInTheDocument();
    expect(screen.queryByText('后续阶段')).not.toBeInTheDocument();
    expect(screen.queryByText('GitLab/Jenkins/线上日志真实运营采集属于后续增强。')).not.toBeInTheDocument();
    expect(screen.queryByText('待接入')).not.toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('运营治理');
    expect(screen.getByText('研发运营指标')).toBeInTheDocument();
    expect(screen.getByText('GitLab 指标')).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toEqual(
        expect.arrayContaining([
          '/api/devops/gitlab/daily-code-metrics',
          '/api/devops/jenkins/releases',
          '/api/ops/online-log-metrics',
          '/api/products?active_only=true',
        ]),
      ),
    );

    rerender(<InsightsPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '用户洞察/迭代规划' })).not.toBeInTheDocument();
    expect(screen.queryByText('后续阶段')).not.toBeInTheDocument();
    expect(screen.queryByText('当前预留入口，后续接入用户使用、反馈和 AI 迭代建议。')).not.toBeInTheDocument();
    expect(screen.queryByText('待接入')).not.toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('运营治理');
    expect(screen.getByText('使用趋势')).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toEqual(
        expect.arrayContaining([
          '/api/insights/usage-metrics',
          '/api/insights/user-feedback',
          '/api/planning/iteration-suggestions',
        ]),
      ),
    );
  });

  it('reloads the dashboard with a selected product filter', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      if (input === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              { code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' },
              { code: 'ops-platform', id: 'product_ops', name: '运营平台', status: 'active' },
            ],
            total: 2,
          },
        });
      }
      if (input === '/api/dashboard/it-team?product_id=product_api') {
        return jsonResponse({
          data: {
            latest_tasks: [
              {
                id: 'task_product_dashboard',
                status: 'waiting_review',
                task_type: 'technical_solution',
                title: '研发平台筛选任务',
              },
            ],
            pending_reviews: [],
            recent_audit_events: [],
            recent_knowledge_documents: [],
            requirement_status_counts: [{ count: 2, status: 'approved' }],
            summary: {
              active_products: 1,
              ai_tasks: 1,
              audit_events: 0,
              knowledge_deposits: 0,
              knowledge_documents: 0,
              pending_reviews: 0,
              requirements: 2,
            },
            task_status_counts: [{ count: 1, status: 'waiting_review' }],
            time_range: 'all',
          },
        });
      }
      if (input === '/api/dashboard/it-team?product_id=product_api&time_range=7d') {
        return jsonResponse({
          data: {
            latest_tasks: [
              {
                id: 'task_product_dashboard',
                status: 'waiting_review',
                task_type: 'technical_solution',
                title: '研发平台筛选任务',
              },
            ],
            pending_reviews: [],
            recent_audit_events: [],
            recent_knowledge_documents: [],
            requirement_status_counts: [{ count: 2, status: 'approved' }],
            summary: {
              active_products: 1,
              ai_tasks: 1,
              audit_events: 0,
              bugs: 1,
              gitlab_commits: 3,
              high_severity_bugs: 1,
              iteration_suggestions: 1,
              jenkins_releases: 1,
              knowledge_deposits: 0,
              knowledge_documents: 0,
              online_errors: 2,
              open_bugs: 1,
              pending_reviews: 0,
              requirements: 2,
              usage_events: 20,
              user_feedback: 1,
            },
            task_status_counts: [{ count: 1, status: 'waiting_review' }],
            time_range: '7d',
          },
        });
      }
      if (input === '/api/dashboard/it-team') {
        return jsonResponse({
          data: {
            latest_tasks: [],
            pending_reviews: [],
            recent_audit_events: [],
            recent_knowledge_documents: [],
            requirement_status_counts: [],
            summary: {
              active_products: 2,
              ai_tasks: 0,
              audit_events: 0,
              knowledge_deposits: 0,
              knowledge_documents: 0,
              pending_reviews: 0,
              requirements: 0,
            },
            task_status_counts: [],
            time_range: 'all',
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DashboardPage />);

    expect(await screen.findByText('IT 团队看板')).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toContain('/api/products?active_only=true'),
    );
    fireEvent.change(await screen.findByLabelText('产品筛选'), {
      target: { value: 'product_api' },
    });

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toContain(
        '/api/dashboard/it-team?product_id=product_api',
      ),
    );
    fireEvent.change(screen.getByLabelText('时间范围'), {
      target: { value: '7d' },
    });
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toContain(
        '/api/dashboard/it-team?product_id=product_api&time_range=7d',
      ),
    );
    expect(await screen.findByText('研发平台筛选任务')).toBeInTheDocument();
    expect(screen.getAllByText('2')).not.toHaveLength(0);
    expect(screen.getByRole('link', { name: /运营明细/ })).toHaveAttribute(
      'href',
      '/governance/devops?product_id=product_api&time_range=7d',
    );
    expect(screen.getByRole('link', { name: /洞察明细/ })).toHaveAttribute(
      'href',
      '/governance/insights?product_id=product_api&time_range=7d',
    );
    expect(
      fetchMock.mock.calls
        .map(([path]) => String(path))
        .some((path) => path.includes('/versions?active_only=true')),
    ).toBe(false);
  });

  it('creates and triages real user feedback from the insights page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' }],
            total: 1,
          },
        });
      }
      if (input === '/api/products/product_api/versions?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/insights/user-feedback' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            content: '新反馈内容',
            created_by: 'user_admin',
            id: 'feedback_created',
            product_id: 'product_api',
            status: 'open',
          },
        });
      }
      if (input === '/api/insights/user-feedback/feedback_existing' && init?.method === 'PATCH') {
        return jsonResponse({
          data: {
            content: '已有反馈内容',
            id: 'feedback_existing',
            product_id: 'product_api',
            status: 'triaged',
            triage_note: '已纳入优化池',
          },
        });
      }
      if (input === '/api/insights/user-feedback') {
        return jsonResponse({
          data: {
            items: [
              {
                content: '已有反馈内容',
                created_by: 'user_admin',
                id: 'feedback_existing',
                product_id: 'product_api',
                status: 'open',
                updated_at: '2026-06-01T08:00:00Z',
              },
            ],
            total: 1,
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<InsightsPage />);

    expect(await screen.findByText('已有反馈内容')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '登记反馈' }));
    fireEvent.mouseDown(screen.getByLabelText('所属产品'));
    fireEvent.click(await screen.findByRole('option', { name: '研发平台' }));
    fireEvent.change(screen.getByLabelText('反馈内容'), { target: { value: '新反馈内容' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/insights/user-feedback',
        'POST',
        JSON.stringify({
          content: '新反馈内容',
          feedback_type: 'improvement',
          product_id: 'product_api',
          source_channel: 'in_app',
        }),
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '处理反馈' }));
    fireEvent.mouseDown(screen.getByLabelText('处理状态'));
    fireEvent.click(await screen.findByRole('option', { name: '已分诊' }));
    fireEvent.change(screen.getByLabelText('处理备注'), { target: { value: '已纳入优化池' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/insights/user-feedback/feedback_existing',
        'PATCH',
        JSON.stringify({
          status: 'triaged',
          triage_note: '已纳入优化池',
        }),
      ]),
    );
  });

  it('records real usage metrics from the insights page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' }],
            total: 1,
          },
        });
      }
      if (input === '/api/products/product_api/versions?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/insights/usage-metrics' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            active_users: 42,
            feature_code: 'semantic-search',
            id: 'usage_created',
            product_id: 'product_api',
            user_segment: 'rd',
            window_start: '2026-06-01T00:00:00Z',
          },
        });
      }
      if (input === '/api/insights/usage-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<InsightsPage />);

    await screen.findByRole('button', { name: '登记使用指标' });
    fireEvent.click(screen.getByRole('button', { name: '登记使用指标' }));
    fireEvent.mouseDown(screen.getByLabelText('所属产品'));
    fireEvent.click(await screen.findByRole('option', { name: '研发平台' }));
    fireEvent.change(screen.getByLabelText('模块编码'), { target: { value: 'search' } });
    fireEvent.change(screen.getByLabelText('功能编码'), { target: { value: 'semantic-search' } });
    fireEvent.change(screen.getByLabelText('用户分群'), { target: { value: 'rd' } });
    fireEvent.change(screen.getByLabelText('窗口开始'), { target: { value: '2026-06-01T00:00:00Z' } });
    fireEvent.change(screen.getByLabelText('窗口结束'), { target: { value: '2026-06-01T01:00:00Z' } });
    fireEvent.change(screen.getByLabelText('活跃用户'), { target: { value: '42' } });
    fireEvent.change(screen.getByLabelText('事件次数'), { target: { value: '120' } });
    fireEvent.change(screen.getByLabelText('转化次数'), { target: { value: '15' } });
    fireEvent.change(screen.getByLabelText('转化率'), { target: { value: '0.36' } });
    fireEvent.change(screen.getByLabelText('平均时长秒'), { target: { value: '36.5' } });
    fireEvent.change(screen.getByLabelText('跳出率'), { target: { value: '0.18' } });
    fireEvent.change(screen.getByLabelText('错误次数'), { target: { value: '2' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/insights/usage-metrics',
        'POST',
        JSON.stringify({
          active_users: 42,
          avg_duration_seconds: 36.5,
          bounce_rate: 0.18,
          conversion_count: 15,
          conversion_rate: 0.36,
          error_count: 2,
          event_count: 120,
          feature_code: 'semantic-search',
          module_code: 'search',
          product_id: 'product_api',
          source_channel: 'manual_import',
          user_segment: 'rd',
          window_end: '2026-06-01T01:00:00Z',
          window_start: '2026-06-01T00:00:00Z',
        }),
      ]),
    );
  });

  it('records real GitLab daily code metrics from the DevOps page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/devops/gitlab/daily-code-metrics' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            commit_count: 7,
            id: 'gitlab_metric_created',
            metric_date: '2026-06-01',
            product_id: 'product_api',
            repository_id: 'repo_api',
            status: 'collected',
          },
        });
      }
      if (input === '/api/devops/gitlab/daily-code-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/devops/jenkins/releases') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ops/online-log-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' }],
            total: 1,
          },
        });
      }
      if (input === '/api/products/product_api/versions?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/products/product_api/git-repositories?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              {
                default_branch: 'main',
                git_provider: 'gitlab',
                id: 'repo_api',
                name: '研发平台 API',
                project_path: 'rd/platform-api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DevopsPage />);

    await screen.findByRole('button', { name: '登记 GitLab 指标' });
    fireEvent.click(screen.getByRole('button', { name: '登记 GitLab 指标' }));
    fireEvent.mouseDown(screen.getByLabelText('所属产品'));
    fireEvent.click(await screen.findByRole('option', { name: '研发平台' }));
    fireEvent.mouseDown(screen.getByLabelText('Git 仓库'));
    fireEvent.click(await screen.findByRole('option', { name: '研发平台 API (rd/platform-api)' }));
    fireEvent.change(screen.getByLabelText('指标日期'), { target: { value: '2026-06-01' } });
    fireEvent.change(screen.getByLabelText('提交数'), { target: { value: '7' } });
    fireEvent.change(screen.getByLabelText('活跃作者数'), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText('MR 数'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('变更文件数'), { target: { value: '18' } });
    fireEvent.change(screen.getByLabelText('新增行数'), { target: { value: '320' } });
    fireEvent.change(screen.getByLabelText('删除行数'), { target: { value: '48' } });
    fireEvent.change(screen.getByLabelText('质量评分'), { target: { value: '88.5' } });
    fireEvent.change(screen.getByLabelText('风险数量'), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/devops/gitlab/daily-code-metrics',
        'POST',
        JSON.stringify({
          active_author_count: 4,
          additions: 320,
          changed_files: 18,
          commit_count: 7,
          deletions: 48,
          merge_request_count: 2,
          metric_date: '2026-06-01',
          product_id: 'product_api',
          quality_score: 88.5,
          repository_id: 'repo_api',
          risk_count: 1,
          source_channel: 'manual_import',
          status: 'collected',
        }),
      ]),
    );
  });

  it('records real Jenkins release records from the DevOps page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/devops/jenkins/releases' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            build_id: 'build-20260601-17',
            id: 'jenkins_release_created',
            job_name: 'rd-platform-deploy',
            product_id: 'product_release',
            status: 'success',
            version_id: 'version_release',
          },
        });
      }
      if (input === '/api/devops/gitlab/daily-code-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/devops/jenkins/releases') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ops/online-log-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: 'release-platform', id: 'product_release', name: '发布平台', status: 'active' }],
            total: 1,
          },
        });
      }
      if (input === '/api/products/product_release/versions?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: 'v1.2.0', id: 'version_release', name: 'v1.2.0', status: 'active' }],
            total: 1,
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DevopsPage />);

    await screen.findByRole('button', { name: '登记 Jenkins 发布' });
    fireEvent.click(screen.getByRole('button', { name: '登记 Jenkins 发布' }));
    fireEvent.change(screen.getByLabelText('Jenkins Job'), { target: { value: 'rd-platform-deploy' } });
    fireEvent.change(screen.getByLabelText('Build ID'), { target: { value: 'build-20260601-17' } });
    fireEvent.change(screen.getByLabelText('Build 编号'), { target: { value: '17' } });
    fireEvent.change(screen.getByLabelText('发布环境'), { target: { value: 'staging' } });
    fireEvent.change(screen.getByLabelText('触发人'), { target: { value: 'jenkins-admin' } });
    fireEvent.change(screen.getByLabelText('Commit SHA'), { target: { value: 'abc123def456' } });
    fireEvent.change(screen.getByLabelText('耗时秒数'), { target: { value: '480' } });
    fireEvent.change(screen.getByLabelText('开始时间'), { target: { value: '2026-06-01T12:22:00Z' } });
    fireEvent.change(screen.getByLabelText('部署时间'), { target: { value: '2026-06-01T12:30:00Z' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/devops/jenkins/releases',
        'POST',
        JSON.stringify({
          build_id: 'build-20260601-17',
          build_number: 17,
          commit_sha: 'abc123def456',
          deployed_at: '2026-06-01T12:30:00Z',
          duration_seconds: 480,
          environment: 'staging',
          job_name: 'rd-platform-deploy',
          product_id: 'product_release',
          source_channel: 'manual_import',
          started_at: '2026-06-01T12:22:00Z',
          status: 'success',
          trigger_actor: 'jenkins-admin',
          version_id: 'version_release',
        }),
      ]),
    );
  });

  it('records real online log metrics from the DevOps page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/ops/online-log-metrics' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            environment: 'prod',
            id: 'online_log_metric_created',
            product_id: 'product_ops',
            status: 'collected',
            window_start: '2026-06-01T00:00:00Z',
          },
        });
      }
      if (input === '/api/devops/gitlab/daily-code-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/devops/jenkins/releases') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ops/online-log-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'ops-platform',
                id: 'product_ops',
                modules: [{ code: 'checkout', id: 'module_checkout', name: '结算模块', status: 'active' }],
                name: '线上运营平台',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/products/product_ops/versions?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DevopsPage />);

    await screen.findByRole('button', { name: '登记线上日志' });
    fireEvent.click(screen.getByRole('button', { name: '登记线上日志' }));
    fireEvent.change(screen.getByLabelText('模块编码'), { target: { value: 'checkout' } });
    fireEvent.change(screen.getByLabelText('运行环境'), { target: { value: 'prod' } });
    fireEvent.change(screen.getByLabelText('窗口开始'), { target: { value: '2026-06-01T00:00:00Z' } });
    fireEvent.change(screen.getByLabelText('窗口结束'), { target: { value: '2026-06-01T01:00:00Z' } });
    fireEvent.change(screen.getByLabelText('请求数'), { target: { value: '2400' } });
    fireEvent.change(screen.getByLabelText('错误数'), { target: { value: '12' } });
    fireEvent.change(screen.getByLabelText('P95 延迟毫秒'), { target: { value: '318.5' } });
    fireEvent.change(screen.getByLabelText('P99 延迟毫秒'), { target: { value: '640.25' } });
    fireEvent.change(screen.getByLabelText('核心事件数'), { target: { value: '240' } });
    fireEvent.change(screen.getByLabelText('Top Errors JSON'), {
      target: { value: '[{"count":7,"message":"PaymentTimeout"}]' },
    });
    fireEvent.change(screen.getByLabelText('异常摘要'), {
      target: { value: 'checkout error spike after release' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/ops/online-log-metrics',
        'POST',
        JSON.stringify({
          anomaly_summary: 'checkout error spike after release',
          core_event_count: 240,
          environment: 'prod',
          error_count: 12,
          module_code: 'checkout',
          p95_latency_ms: 318.5,
          p99_latency_ms: 640.25,
          product_id: 'product_ops',
          request_count: 2400,
          source_channel: 'manual_import',
          status: 'collected',
          top_errors: [{ count: 7, message: 'PaymentTimeout' }],
          window_end: '2026-06-01T01:00:00Z',
          window_start: '2026-06-01T00:00:00Z',
        }),
      ]),
    );
  });

  it('loads real collector runs without placeholder rows from the DevOps page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      if (input === '/api/devops/gitlab/daily-code-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/devops/jenkins/releases') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ops/online-log-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/collectors/runs') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/products?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DevopsPage />);

    await screen.findByText('采集运行记录');
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toEqual(
        expect.arrayContaining(['/api/collectors/runs']),
      ),
    );
    expect(screen.queryByText('collector_run_demo')).not.toBeInTheDocument();
    expect(screen.queryByText('示例采集运行')).not.toBeInTheDocument();
  });

  it('creates real collector runs from the DevOps page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/collectors/runs' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            collector_type: 'gitlab_daily_code_metric',
            id: 'collector_run_created',
            payload_summary: { repository_path: 'rd/platform-api' },
            product_id: 'product_api',
            records_imported: 3,
            source_system: 'gitlab',
            started_at: '2026-06-01T08:00:00Z',
            status: 'running',
          },
        });
      }
      if (input === '/api/collectors/runs') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/devops/gitlab/daily-code-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/devops/jenkins/releases') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ops/online-log-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' }],
            total: 1,
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DevopsPage />);

    await screen.findByRole('button', { name: '登记采集运行' });
    fireEvent.click(screen.getByRole('button', { name: '登记采集运行' }));
    fireEvent.mouseDown(screen.getByLabelText('采集类型'));
    fireEvent.click(await screen.findByRole('option', { name: 'GitLab 日代码指标' }));
    fireEvent.mouseDown(screen.getByLabelText('所属产品'));
    fireEvent.click(await screen.findByRole('option', { name: '研发平台' }));
    fireEvent.change(screen.getByLabelText('来源系统'), { target: { value: 'gitlab' } });
    fireEvent.change(screen.getByLabelText('开始时间'), { target: { value: '2026-06-01T08:00:00Z' } });
    fireEvent.change(screen.getByLabelText('导入记录数'), { target: { value: '3' } });
    fireEvent.change(screen.getByLabelText('Payload 摘要 JSON'), {
      target: { value: '{"repository_path":"rd/platform-api"}' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/collectors/runs',
        'POST',
        JSON.stringify({
          collector_type: 'gitlab_daily_code_metric',
          payload_summary: { repository_path: 'rd/platform-api' },
          product_id: 'product_api',
          records_imported: 3,
          source_system: 'gitlab',
          started_at: '2026-06-01T08:00:00Z',
          status: 'running',
        }),
      ]),
    );
  });

  it('completes running collector runs from the DevOps page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/collectors/runs/collector_run_001' && init?.method === 'PATCH') {
        return jsonResponse({
          data: {
            collector_type: 'user_feedback',
            id: 'collector_run_001',
            product_id: 'product_api',
            records_imported: 2,
            source_system: 'feedback-api',
            status: 'succeeded',
          },
        });
      }
      if (input === '/api/collectors/runs') {
        return jsonResponse({
          data: {
            items: [
              {
                collector_type: 'user_feedback',
                id: 'collector_run_001',
                product_id: 'product_api',
                records_imported: 2,
                source_system: 'feedback-api',
                started_at: '2026-06-01T08:00:00Z',
                status: 'running',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/devops/gitlab/daily-code-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/devops/jenkins/releases') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ops/online-log-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/products?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DevopsPage />);

    await screen.findByText('collector_run_001');
    fireEvent.click(screen.getByRole('button', { name: /标记成功/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/collectors/runs/collector_run_001',
        'PATCH',
        JSON.stringify({ status: 'succeeded' }),
      ]),
    );
  });

  it('generates and decides real iteration suggestions from the insights page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' }],
            total: 1,
          },
        });
      }
      if (input === '/api/products/product_api/versions?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: '2026Q3', id: 'version_api', name: '2026 Q3', status: 'planning' }],
            total: 1,
          },
        });
      }
      if (input === '/api/planning/iteration-suggestions' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            items: [
              {
                id: 'suggestion_generated',
                planning_cycle: '2026Q3',
                priority: 'P1',
                product_id: 'product_api',
                status: 'suggested',
                title: '新迭代建议',
                updated_at: '2026-06-01T08:30:00Z',
              },
            ],
            total: 1,
          },
        });
      }
      if (
        input === '/api/planning/iteration-suggestions/suggestion_existing/decide' &&
        init?.method === 'POST'
      ) {
        return jsonResponse({
          data: {
            converted_requirement_id: 'requirement_from_suggestion',
            decision: 'edited_accepted',
            id: 'suggestion_existing',
            status: 'converted_to_requirement',
            title: '优化知识检索',
          },
        });
      }
      if (input === '/api/planning/iteration-suggestions') {
        return jsonResponse({
          data: {
            items: [
              {
                confidence_level: 'medium',
                id: 'suggestion_existing',
                planning_cycle: '2026Q3',
                priority: 'P1',
                product_id: 'product_api',
                status: 'suggested',
                title: '优化知识检索',
                updated_at: '2026-06-01T08:00:00Z',
              },
            ],
            total: 1,
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<InsightsPage />);

    expect(await screen.findByText('优化知识检索')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '生成迭代建议' }));
    fireEvent.mouseDown(screen.getByLabelText('所属产品'));
    fireEvent.click(await screen.findByRole('option', { name: '研发平台' }));
    fireEvent.mouseDown(screen.getByLabelText('目标版本'));
    fireEvent.click(await screen.findByRole('option', { name: '2026 Q3' }));
    fireEvent.change(screen.getByLabelText('规划周期'), { target: { value: '2026Q3' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/planning/iteration-suggestions',
        'POST',
        JSON.stringify({
          constraints: { max_suggestions: 10 },
          planning_cycle: '2026Q3',
          product_id: 'product_api',
          version_id: 'version_api',
        }),
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '确认建议' }));
    fireEvent.change(screen.getByLabelText('确认备注'), { target: { value: '进入下阶段' } });
    fireEvent.click(screen.getByLabelText('转为正式需求'));
    fireEvent.change(await screen.findByLabelText('需求标题'), { target: { value: '优化知识检索体验' } });
    fireEvent.change(screen.getByLabelText('需求范围'), { target: { value: '优先处理检索召回与排序' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/planning/iteration-suggestions/suggestion_existing/decide',
        'POST',
        JSON.stringify({
          comment: '进入下阶段',
          convert_to_requirement: true,
          decision: 'edited_accepted',
          edited_scope: '优先处理检索召回与排序',
          edited_title: '优化知识检索体验',
        }),
      ]),
    );
  });

  it('renders management modules as query filters with table lists', async () => {
    const { rerender } = render(<ProductsPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('产品资产');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('欢迎');
    expect(screen.getByRole('navigation', { name: '面包屑' })).not.toHaveTextContent('工作台');
    expect(screen.queryByRole('heading', { level: 1, name: '产品管理' })).not.toBeInTheDocument();
    expect(screen.queryByText('API ready')).not.toBeInTheDocument();
    expect(screen.getByRole('form', { name: '查询表格' })).toBeInTheDocument();
    expect(screen.getByText('产品列表')).toBeInTheDocument();
    expect(screen.getAllByText('产品编码')).not.toHaveLength(0);
    expect(screen.queryByText('AI-BRAIN')).not.toBeInTheDocument();

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
      if (input === '/api/audit/events') {
        return jsonResponse({
          data: {
            items: [
              {
                actor_id: 'user_admin',
                ai_task_id: 'task_audit',
                created_at: '2026-05-31T08:00:00+00:00',
                event_type: 'requirement.approved',
                id: 'audit_api',
                payload: { comment: '进入 MVP-A' },
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
    fireEvent.click(within(auditRow as HTMLElement).getByRole('button', { name: '详情' }));
    expect(await screen.findByText('审计详情')).toBeInTheDocument();
    expect(screen.getAllByText('requirement: requirement_api')).not.toHaveLength(0);
    expect(screen.getByText(/进入 MVP-A/)).toBeInTheDocument();

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

  it('filters management table rows from query conditions', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const path = String(input);
      if (path.includes('/versions')) {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      return new Response(
        JSON.stringify({
          data: {
            items: [
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
            ],
            total: 2,
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

    expect(screen.getByText('RD-BRAIN')).toBeInTheDocument();
    expect(screen.queryByText('AI-BRAIN')).not.toBeInTheDocument();

    fireEvent.reset(screen.getByRole('form', { name: '查询表格' }));

    expect(screen.getByText('AI-BRAIN')).toBeInTheDocument();
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

      if (path === '/api/products') {
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
    expect(screen.getAllByText('v1 MVP').length).toBeGreaterThan(0);
    expect(screen.getByText('知识模块')).toBeInTheDocument();
    expect(screen.getByText('platform/ai-brain')).toBeInTheDocument();
    expect(screen.getByText('已配置')).toBeInTheDocument();
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
  });

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

    expect(gitRepositories).toEqual([
      expect.objectContaining({
        credentialRefConfigured: true,
        credentialStatus: '已配置',
        id: 'repo_api',
        projectPath: 'platform/ai-brain',
      }),
    ]);
    expect(JSON.stringify(gitRepositories)).not.toContain('env:GITLAB_READONLY_TOKEN');
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
    ]);
  });

  it('does not flash local requirement examples while authenticated data is loading', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    let resolveProducts: (response: Response) => void = () => {};
    let resolveActiveProducts: (response: Response) => void = () => {};
    let resolveRequirements: (response: Response) => void = () => {};
    const productsPromise = new Promise<Response>((resolve) => {
      resolveProducts = resolve;
    });
    const activeProductsPromise = new Promise<Response>((resolve) => {
      resolveActiveProducts = resolve;
    });
    const requirementsPromise = new Promise<Response>((resolve) => {
      resolveRequirements = resolve;
    });
    const fetchMock = vi.fn<typeof fetch>((input) => {
      const path = String(input);
      if (path === '/api/products') {
        return productsPromise;
      }
      if (path === '/api/products?active_only=true') {
        return activeProductsPromise;
      }
      if (path === '/api/requirements') {
        return requirementsPromise;
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<RequirementsPage />);

    expect(screen.queryByText('产品详细设计辅助')).not.toBeInTheDocument();

    resolveProducts(jsonResponse({ data: { items: [], total: 0 } }));
    resolveActiveProducts(jsonResponse({ data: { items: [], total: 0 } }));
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
      if (path === '/api/products') {
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
      if (path === '/api/products/product_api/versions' || path === '/api/products/product_api/versions?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/requirements') {
        return jsonResponse({
          data: {
            items: [
              {
                id: 'requirement_api',
                priority: 'P1',
                product_id: 'product_api',
                status: 'pending_approval',
                title: '接口需求',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/bugs') {
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
      if (path === '/api/knowledge/documents') {
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
      if (path === '/api/auth/roles') {
        return jsonResponse(roleCatalogEnvelope);
      }
      if (path === '/api/users') {
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
            total: 1,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${path}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    const { rerender } = render(<ProductsPage />);

    expect(screen.getByRole('button', { name: /新增产品/ })).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: /编辑/ })).not.toHaveLength(0);
    expect(screen.getAllByRole('button', { name: /删除/ })).not.toHaveLength(0);

    rerender(<RequirementsPage />);
    expect(screen.getByRole('button', { name: /新增需求/ })).toBeInTheDocument();
    expect(await screen.findAllByRole('button', { name: /编辑/ })).not.toHaveLength(0);
    expect(screen.getAllByRole('button', { name: /删除/ })).not.toHaveLength(0);

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

  it('edits bug lifecycle evidence and duplicate merge fields from backend data', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
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
      if (path === '/api/products/product_api/versions?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/bugs' && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                assignee: 'qa@example.com',
                description: '支付链路失败',
                duplicate_of_bug_id: 'bug_target',
                evidence: { log_id: 'log-1' },
                id: 'bug_main',
                module_code: 'checkout',
                product_id: 'product_api',
                reproduce_steps: ['打开支付页', '点击支付'],
                severity: 'major',
                source: 'manual_test',
                status: 'closed',
                title: '支付失败',
                version_id: 'version_api',
              },
              {
                assignee: 'rd@example.com',
                description: '同类支付问题',
                id: 'bug_target',
                module_code: 'checkout',
                product_id: 'product_api',
                reproduce_steps: [],
                severity: 'minor',
                source: 'ai_auto_test',
                status: 'triaged',
                title: '支付重复问题',
                version_id: 'version_api',
              },
            ],
            total: 2,
          },
        });
      }
      if (path === '/api/bugs/bug_main' && method === 'PATCH') {
        return jsonResponse({ data: { id: 'bug_main' } });
      }
      throw new Error(`Unexpected fetch call: ${path} ${method}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<BugsPage />);

    expect(await screen.findByText('支付失败')).toBeInTheDocument();
    const bugRow = screen.getByText('支付失败').closest('tr');
    expect(bugRow).not.toBeNull();
    fireEvent.click(within(bugRow as HTMLElement).getByRole('button', { name: /编辑/ }));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByLabelText('复现步骤')).toHaveValue('打开支付页\n点击支付');
    expect(within(dialog).getByLabelText('证据 JSON')).toHaveValue(
      JSON.stringify({ log_id: 'log-1' }, null, 2),
    );
    expect(within(dialog).getByLabelText('重复归并')).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText('复现步骤'), {
      target: { value: '打开支付页\n点击支付\n查看错误提示' },
    });
    fireEvent.change(within(dialog).getByLabelText('证据 JSON'), {
      target: { value: JSON.stringify({ log_id: 'log-2', screenshot: 'pay-fail.png' }, null, 2) },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/bugs/bug_main',
        'PATCH',
        JSON.stringify({
          assignee: 'qa@example.com',
          description: '支付链路失败',
          duplicate_of_bug_id: 'bug_target',
          evidence: { log_id: 'log-2', screenshot: 'pay-fail.png' },
          reproduce_steps: ['打开支付页', '点击支付', '查看错误提示'],
          severity: 'major',
          status: 'closed',
          title: '支付失败',
        }),
      ]),
    );
  });

  it('uses explicitly defined role options in the user management modal', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (String(input) === '/api/auth/roles') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return new Response(JSON.stringify(roleCatalogEnvelope), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      expect(String(input)).toBe('/api/users');
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      return new Response(
        JSON.stringify({
          data: {
            items: [],
            total: 0,
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

    render(<UsersPage />);

    fireEvent.click(screen.getByRole('button', { name: /新增用户/ }));

    expect(await screen.findByText(/查看者/)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText('admin, product_owner, rd_owner')).not.toBeInTheDocument();
  });

  it('renders system role management from the backend role catalog', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(String(input)).toBe('/api/auth/roles');
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      return new Response(JSON.stringify(roleCatalogEnvelope), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<RolesPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('系统管理');
    expect(await screen.findByText('角色定义')).toBeInTheDocument();
    expect(screen.getByText('系统管理员 (admin)')).toBeInTheDocument();
    expect(screen.getByText('查看者 (viewer)')).toBeInTheDocument();
    expect(screen.getByText('平台管理员')).toBeInTheDocument();
    expect(screen.getByText('只读参与者')).toBeInTheDocument();
    expect(screen.getAllByText('系统管理').length).toBeGreaterThan(0);
    expect(screen.getByText('授权业务列表')).toBeInTheDocument();
    expect(screen.getByText('系统治理。')).toBeInTheDocument();
    expect(screen.getByText('无写入或审批决策权限。')).toBeInTheDocument();
    expect(screen.getByText('不能执行写操作、审批或配置变更。')).toBeInTheDocument();
    expect(screen.getByText('system.users.manage')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /新增角色|删除/ })).not.toBeInTheDocument();
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
      if (path === '/api/products/product_api/versions' || path === '/api/products/product_api/versions?active_only=true') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1',
                product_id: 'product_api',
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
      if (path === '/api/auth/roles') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return jsonResponse(roleCatalogEnvelope);
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
                source: 'ai_post_release',
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
    expect(screen.getByText('AI 上线后分析')).toBeInTheDocument();

    rerender(<KnowledgePage />);

    expect(await screen.findByText('接口知识文档')).toBeInTheDocument();
    expect(screen.getByText('admin, rd_owner')).toBeInTheDocument();

    rerender(<AuditPage />);

    expect(await screen.findByText('product.created')).toBeInTheDocument();
    expect(screen.getByText('product: product_api')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith('/api/auth/login', expect.anything());
  });

  it('shows backend load failures without local example rows', async () => {
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

    expect(screen.queryByText('AI-BRAIN')).not.toBeInTheDocument();
    expect(await screen.findByText(/接口异常，未加载到数据/)).toBeInTheDocument();
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

  it('sends review and task more-info mutations to backend APIs', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/reviews/review_api/request-more-info') {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBe(
          JSON.stringify({
            questions: ['请补充验收边界'],
            version: 1,
          }),
        );
        return jsonResponse({
          data: {
            review_status: 'requested_more_info',
            task_status: 'waiting_more_info',
          },
        });
      }
      if (input === '/api/ai-tasks/task_api/more-info') {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBe(
          JSON.stringify({
            answers: [{ answer: '补充 P0 验收边界', question: '补充说明' }],
          }),
        );
        return jsonResponse({ data: { id: 'task_api', status: 'draft' } });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      requestTaskCenterReviewMoreInfo('review_api', 1, ['请补充验收边界']),
    ).resolves.toMatchObject({
      review_status: 'requested_more_info',
      task_status: 'waiting_more_info',
    });
    await expect(
      submitTaskCenterMoreInfo('task_api', [
        { answer: '补充 P0 验收边界', question: '补充说明' },
      ]),
    ).resolves.toMatchObject({ id: 'task_api', status: 'draft' });
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toEqual([
      ['/api/reviews/review_api/request-more-info', 'POST'],
      ['/api/ai-tasks/task_api/more-info', 'POST'],
    ]);
  });

  it('sends model gateway config CRUD mutations to backend APIs without plaintext in list rows', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/system/model-gateway-configs' && init?.method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                api_key_configured: true,
                base_url: 'https://api.example.com/v1',
                default_chat_model: 'gpt-4.1',
                default_embedding_model: 'text-embedding-3-large',
                id: 'model_config_api',
                is_default: true,
                max_retries: 1,
                name: '默认模型网关',
                provider: 'openai_compatible',
                status: 'active',
                timeout_seconds: 60,
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/system/model-gateway-configs' && init?.method === 'POST') {
        expect(init.body).toBe(
          JSON.stringify({
            api_key: 'sk-live-secret',
            base_url: 'https://api.example.com/v1',
            default_chat_model: 'gpt-4.1',
            default_embedding_model: 'text-embedding-3-large',
            is_default: true,
            max_retries: 1,
            name: '默认模型网关',
            provider: 'openai_compatible',
            status: 'active',
            timeout_seconds: 60,
          }),
        );
        return jsonResponse({ data: { id: 'model_config_api', status: 'active' } });
      }
      if (input === '/api/system/model-gateway-configs/model_config_api' && init?.method === 'PATCH') {
        expect(init.body).toBe(
          JSON.stringify({
            default_chat_model: 'gpt-4.1-mini',
            status: 'active',
          }),
        );
        return jsonResponse({ data: { id: 'model_config_api', status: 'active' } });
      }
      if (input === '/api/system/model-gateway-configs/model_config_api' && init?.method === 'DELETE') {
        return jsonResponse({ data: { deleted: true, id: 'model_config_api' } });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchModelGatewayConfigs()).resolves.toEqual([
      expect.objectContaining({
        apiKeyConfigured: true,
        keyStatus: '已配置',
        name: '默认模型网关',
      }),
    ]);
    await createModelGatewayConfig({
      api_key: 'sk-live-secret',
      base_url: 'https://api.example.com/v1',
      default_chat_model: 'gpt-4.1',
      default_embedding_model: 'text-embedding-3-large',
      is_default: true,
      max_retries: 1,
      name: '默认模型网关',
      provider: 'openai_compatible',
      status: 'active',
      timeout_seconds: 60,
    });
    await updateModelGatewayConfig('model_config_api', {
      default_chat_model: 'gpt-4.1-mini',
      status: 'active',
    });
    await deleteModelGatewayConfig('model_config_api');

    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toEqual([
      ['/api/system/model-gateway-configs', 'GET'],
      ['/api/system/model-gateway-configs', 'POST'],
      ['/api/system/model-gateway-configs/model_config_api', 'PATCH'],
      ['/api/system/model-gateway-configs/model_config_api', 'DELETE'],
    ]);
  });

  it('fetches the dashboard with product and time range query parameters', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      expect(input).toBe('/api/dashboard/it-team?product_id=product_api&time_range=7d');
      return jsonResponse({
        data: {
          bug_status_counts: [{ count: 1, status: 'open' }],
          gitlab_daily_summary: {
            average_quality_score: 91,
            changed_files: 5,
            commit_count: 3,
            merge_request_count: 1,
            metric_count: 1,
            risk_count: 0,
          },
          iteration_suggestion_status_counts: [{ count: 1, status: 'suggested' }],
          jenkins_release_status_counts: [{ count: 1, status: 'success' }],
          latest_high_severity_bugs: [
            {
              id: 'bug_api',
              severity: 'critical',
              status: 'open',
              title: 'API Dashboard Bug',
            },
          ],
          latest_tasks: [],
          online_log_summary: {
            error_count: 2,
            error_rate: 0.01,
            max_p95_latency_ms: 128,
            max_p99_latency_ms: 256,
            metric_count: 1,
            request_count: 200,
          },
          pending_reviews: [],
          recent_audit_events: [],
          recent_knowledge_documents: [],
          requirement_status_counts: [{ count: 2, status: 'approved' }],
          summary: {
            active_products: 1,
            ai_tasks: 1,
            audit_events: 0,
            bugs: 1,
            gitlab_commits: 3,
            high_severity_bugs: 1,
            iteration_suggestions: 1,
            jenkins_releases: 1,
            knowledge_deposits: 0,
            knowledge_documents: 0,
            online_errors: 2,
            open_bugs: 1,
            pending_reviews: 0,
            requirements: 2,
            usage_events: 20,
            user_feedback: 1,
          },
          task_status_counts: [],
          time_range: '7d',
          usage_metric_summary: {
            active_users: 4,
            conversion_count: 2,
            error_count: 1,
            event_count: 20,
            metric_count: 1,
          },
          user_feedback_status_counts: [{ count: 1, status: 'open' }],
        },
      });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchItTeamDashboard({ productId: 'product_api', timeRange: '7d' })).resolves.toMatchObject({
      bugStatusCounts: [{ count: 1, status: 'open' }],
      gitlabDailySummary: expect.objectContaining({ commitCount: 3, metricCount: 1 }),
      latestHighSeverityBugs: [{ id: 'bug_api', severity: 'critical', status: 'open', title: 'API Dashboard Bug' }],
      onlineLogSummary: expect.objectContaining({ errorCount: 2, errorRate: 0.01 }),
      requirementStatusCounts: [{ count: 2, status: 'approved' }],
      summary: expect.objectContaining({ activeProducts: 1, openBugs: 1, requirements: 2 }),
      timeRange: '7d',
    });
  });

  it('fetches active product filter options without loading versions', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      expect(input).toBe('/api/products?active_only=true');
      return jsonResponse({
        data: {
          items: [
            { code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' },
          ],
          total: 1,
        },
      });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchActiveProductOptions()).resolves.toEqual([
      { code: 'rd-platform', id: 'product_api', name: '研发平台' },
    ]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('sends management CRUD mutations to backend APIs with the stored token', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/export/tasks/task_solution/markdown') {
        return new Response('# Markdown 导出', {
          headers: { 'Content-Type': 'text/markdown' },
          status: 200,
        });
      }
      if (input === '/api/products/product_api/git-repositories?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              {
                git_provider: 'gitlab',
                id: 'repo_api',
                name: 'AI Brain API',
                project_path: 'platform/ai-brain',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/devops/gitlab/merge-requests/repo_api/42/preview') {
        return jsonResponse({
          data: {
            author: 'alice',
            changed_file_count: 3,
            mr_iid: 42,
            repository_id: 'repo_api',
            title: 'feat: review flow',
          },
        });
      }
      if (input === '/api/devops/gitlab/merge-requests/repo_api/42/snapshot') {
        return jsonResponse({
          data: {
            id: 'snapshot_api',
            mr_iid: 42,
            repository_id: 'repo_api',
          },
        });
      }
      if (input === '/api/ai-tasks/task_code_review/code-review-report') {
        return jsonResponse({
          data: {
            findings: [{ severity: 'high', summary: '缺少边界测试' }],
            gitlab_writeback_performed: false,
            id: 'report_api',
            risk_level: 'medium',
            status: 'pending_review',
            summary: '发现 1 个高风险问题',
          },
        });
      }
      return jsonResponse({
        data: {
          id: String(input).includes('/api/products') ? 'product_api' : 'resource_api',
          status: 'active',
        },
      });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await createManagementProduct({ code: 'CRUD', name: 'CRUD 产品', status: 'active' });
    await updateManagementProduct('product_api', { name: '更新产品' });
    await deleteManagementProduct('product_api');
    await createManagementRequirement({
      content: '需求内容',
      priority: 'P1',
      product_id: 'product_api',
      title: 'CRUD 需求',
      version_id: 'version_api',
    });
    await updateManagementRequirement('requirement_api', { title: '更新需求' });
    await approveManagementRequirement('requirement_api');
    await rejectManagementRequirement('requirement_api', '目标不清晰');
    await generateRequirementTask('requirement_api');
    await deleteManagementRequirement('requirement_api');
    await createManagementBug({
      description: 'Bug 描述',
      product_id: 'product_api',
      severity: 'major',
      source: 'manual_test',
      title: 'CRUD Bug',
    });
    await updateManagementBug('bug_api', { assignee: 'rd_owner@example.com' });
    await deleteManagementBug('bug_api');
    await createManagementKnowledgeDocument({
      content: '知识内容',
      permission_roles: ['admin'],
      title: 'CRUD 知识',
    });
    await updateManagementKnowledgeDocument('knowledge_api', { title: '更新知识' });
    await deleteManagementKnowledgeDocument('knowledge_api');
    await createManagementUser({
      display_name: 'CRUD 用户',
      password: 'secret123',
      roles: ['viewer'],
      status: 'active',
      username: 'crud@example.com',
    });
    await updateManagementUser('user_api', { display_name: '更新用户' });
    await deleteManagementUser('user_api');
    await startTaskCenterTask('task_api');
    await approveTaskCenterReview('review_api', 1);
    await createTechnicalSolutionTask({
      id: 'task_design',
      label: '产品详细设计：CRUD 需求',
      owner: 'user_admin',
      productId: 'product_api',
      requirementId: 'requirement_api',
      status: 'completed',
      type: 'product_detail_design',
    });
    await createDevelopmentPlanningTask({
      id: 'task_solution',
      label: '技术方案：CRUD 需求',
      owner: 'user_admin',
      productId: 'product_api',
      requirementId: 'requirement_api',
      status: 'completed',
      type: 'technical_solution',
    });
    await createAutomatedTestingTask({
      id: 'task_solution',
      label: '技术方案：CRUD 需求',
      owner: 'user_admin',
      productId: 'product_api',
      requirementId: 'requirement_api',
      status: 'completed',
      type: 'technical_solution',
    });
    await createReleaseReadinessTask({
      id: 'task_solution',
      label: '技术方案：CRUD 需求',
      owner: 'user_admin',
      productId: 'product_api',
      requirementId: 'requirement_api',
      status: 'completed',
      type: 'technical_solution',
    });
    await createPostReleaseAnalysisTask({
      id: 'task_release',
      label: '发布评估：CRUD 需求',
      owner: 'user_admin',
      productId: 'product_api',
      requirementId: 'requirement_api',
      status: 'completed',
      type: 'release_readiness',
    });
    await expect(fetchTaskMarkdown('task_solution')).resolves.toBe('# Markdown 导出');
    await fetchProductGitRepositories('product_api');
    await previewGitLabMergeRequest('repo_api', 42);
    await snapshotGitLabMergeRequest({
      mrIid: 42,
      repositoryId: 'repo_api',
      requirementId: 'requirement_api',
      technicalSolutionTaskId: 'task_solution',
    });
    await createCodeReviewTask(
      {
        id: 'task_solution',
        label: '技术方案：CRUD 需求',
        owner: 'user_admin',
        productId: 'product_api',
        requirementId: 'requirement_api',
        status: 'completed',
        type: 'technical_solution',
      },
      'snapshot_api',
      42,
    );
    await expect(fetchCodeReviewReport('task_code_review')).resolves.toMatchObject({
      gitlabWritebackPerformed: false,
      riskLevel: 'medium',
      status: 'pending_review',
    });

    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toEqual([
      ['/api/products', 'POST'],
      ['/api/products/product_api', 'PATCH'],
      ['/api/products/product_api', 'DELETE'],
      ['/api/requirements', 'POST'],
      ['/api/requirements/requirement_api', 'PATCH'],
      ['/api/requirements/requirement_api/approve', 'POST'],
      ['/api/requirements/requirement_api/reject', 'POST'],
      ['/api/requirements/requirement_api/generate-task', 'POST'],
      ['/api/requirements/requirement_api', 'DELETE'],
      ['/api/bugs', 'POST'],
      ['/api/bugs/bug_api', 'PATCH'],
      ['/api/bugs/bug_api', 'DELETE'],
      ['/api/knowledge/documents', 'POST'],
      ['/api/knowledge/documents/knowledge_api', 'PATCH'],
      ['/api/knowledge/documents/knowledge_api', 'DELETE'],
      ['/api/users', 'POST'],
      ['/api/users/user_api', 'PATCH'],
      ['/api/users/user_api', 'DELETE'],
      ['/api/ai-tasks/task_api/start', 'POST'],
      ['/api/reviews/review_api/approve', 'POST'],
      ['/api/ai-tasks', 'POST'],
      ['/api/ai-tasks', 'POST'],
      ['/api/ai-tasks', 'POST'],
      ['/api/ai-tasks', 'POST'],
      ['/api/ai-tasks', 'POST'],
      ['/api/export/tasks/task_solution/markdown', 'GET'],
      ['/api/products/product_api/git-repositories?active_only=true', 'GET'],
      ['/api/devops/gitlab/merge-requests/repo_api/42/preview', 'GET'],
      ['/api/devops/gitlab/merge-requests/repo_api/42/snapshot', 'POST'],
      ['/api/ai-tasks', 'POST'],
      ['/api/ai-tasks/task_code_review/code-review-report', 'GET'],
    ]);
    expect(fetchMock.mock.calls[20]?.[1]?.body).toBe(
      JSON.stringify({
        input: { product_detail_design_task_id: 'task_design' },
        requirement_id: 'requirement_api',
        task_type: 'technical_solution',
        title: '技术方案：CRUD 需求',
      }),
    );
    expect(fetchMock.mock.calls[21]?.[1]?.body).toBe(
      JSON.stringify({
        input: { technical_solution_task_id: 'task_solution' },
        requirement_id: 'requirement_api',
        task_type: 'development_planning',
        title: '开发计划：CRUD 需求',
      }),
    );
    expect(fetchMock.mock.calls[22]?.[1]?.body).toBe(
      JSON.stringify({
        input: { technical_solution_task_id: 'task_solution' },
        requirement_id: 'requirement_api',
        task_type: 'automated_testing',
        title: '自动化测试：CRUD 需求',
      }),
    );
    expect(fetchMock.mock.calls[23]?.[1]?.body).toBe(
      JSON.stringify({
        input: { technical_solution_task_id: 'task_solution' },
        requirement_id: 'requirement_api',
        task_type: 'release_readiness',
        title: '发布评估：CRUD 需求',
      }),
    );
    expect(fetchMock.mock.calls[24]?.[1]?.body).toBe(
      JSON.stringify({
        input: { release_readiness_task_id: 'task_release' },
        requirement_id: 'requirement_api',
        task_type: 'post_release_analysis',
        title: '上线后分析：CRUD 需求',
      }),
    );
    expect(fetchMock.mock.calls[28]?.[1]?.body).toBe(
      JSON.stringify({
        requirement_id: 'requirement_api',
        technical_solution_task_id: 'task_solution',
      }),
    );
    expect(fetchMock.mock.calls[29]?.[1]?.body).toBe(
      JSON.stringify({
        input: { gitlab_mr_snapshot_id: 'snapshot_api' },
        requirement_id: 'requirement_api',
        task_type: 'code_review',
        title: 'Code Review：CRUD 需求 MR !42',
      }),
    );
  });

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
