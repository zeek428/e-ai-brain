import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import MenusPage from '../src/pages/Menus';
import RolesPage from '../src/pages/Roles';
import UsersPage from '../src/pages/Users';

const roleCatalogEnvelope = {
  data: {
    items: [
      {
        id: 'role_admin',
        code: 'admin',
        description: '负责用户、角色、模型网关、审计与系统级配置管理。',
        is_assignable: true,
        is_system: true,
        menu_codes: ['system', 'system.roles', 'governance.audit'],
        name: '系统管理员',
        permission_codes: ['system.roles.read', 'system.roles.manage', 'system.users.manage'],
        scopes: [{ access_level: 'admin', scope_id: '*', scope_name: '全局', scope_type: 'global' }],
        sort_order: 10,
        status: 'active',
      },
      {
        id: 'role_viewer',
        code: 'viewer',
        description: '只能查看有权限访问的工作台数据、任务结果、知识和看板摘要。',
        is_assignable: true,
        is_system: true,
        menu_codes: ['workspace.dashboard'],
        name: '查看者',
        permission_codes: ['workspace.read'],
        scopes: [
          {
            access_level: 'read',
            scope_id: 'product_scope_matrix',
            scope_name: 'AI Brain',
            scope_type: 'product',
          },
        ],
        sort_order: 60,
        status: 'active',
      },
    ],
    total: 2,
  },
};

describe('system management pages', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    notification.destroy();
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
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
      expect(String(input)).toMatch(/^\/api\/users\?/);
      expect(String(input)).toContain('page=1');
      expect(String(input)).toContain('page_size=10');
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      return new Response(
        JSON.stringify({
          data: {
            items: [
              {
                dingtalk_binding: {
                  bound: true,
                  corp_name: '青锋科技',
                  display_name: '钉钉查看者',
                  identity_id: 'external_identity_viewer',
                  provider: 'dingtalk',
                },
                display_name: '查看者',
                id: 'user_viewer',
                local_password_configured: false,
                login_methods: ['dingtalk'],
                mobile: '+86 13800000000',
                roles: ['viewer'],
                status: 'active',
                username: 'viewer@example.com',
              },
            ],
            page: 1,
            page_size: 10,
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

    render(<UsersPage />);

    fireEvent.click(screen.getByRole('button', { name: /新增用户/ }));

    expect(await screen.findByText('viewer@example.com')).toBeInTheDocument();
    expect(screen.getByText('钉钉')).toBeInTheDocument();
    expect(screen.getByText('青锋科技')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /解绑钉钉/ })).toBeInTheDocument();
    expect((await screen.findAllByText(/查看者/)).length).toBeGreaterThan(0);
    expect(screen.queryByPlaceholderText('admin, product_owner, rd_owner')).not.toBeInTheDocument();
  });

  it('renders system role management from the backend role catalog', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input) === '/api/system/permissions') {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                { code: 'system.roles.manage', name: '角色管理', status: 'active' },
                { code: 'system.roles.read', name: '查看角色', status: 'active' },
                { code: 'system.users.manage', name: '用户管理', status: 'active' },
                { code: 'workspace.read', name: '工作台读取', status: 'active' },
              ],
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (String(input) === '/api/system/menus') {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                { code: 'system', menu_type: 'group', name: '系统管理', path: '/system' },
                {
                  code: 'system.roles',
                  menu_type: 'page',
                  name: '角色管理',
                  path: '/system/roles',
                  required_permissions: ['system.roles.manage'],
                },
                {
                  code: 'governance.audit',
                  menu_type: 'page',
                  name: '审计与运行',
                  path: '/governance/audit',
                  required_permissions: [],
                },
                {
                  code: 'workspace.dashboard',
                  menu_type: 'page',
                  name: '团队看板',
                  path: '/welcome',
                  required_permissions: ['workspace.read'],
                },
              ],
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (String(input) === '/api/system/permissions/matrix') {
        return new Response(
          JSON.stringify({
            data: {
              menus: [
                { code: 'system', menu_type: 'group', name: '系统管理', path: '/system' },
                {
                  code: 'system.roles',
                  menu_type: 'page',
                  name: '角色管理',
                  path: '/system/roles',
                  required_permissions: ['system.roles.manage'],
                },
                {
                  code: 'governance.audit',
                  menu_type: 'page',
                  name: '审计与运行',
                  path: '/governance/audit',
                  required_permissions: [],
                },
                {
                  code: 'workspace.dashboard',
                  menu_type: 'page',
                  name: '团队看板',
                  path: '/welcome',
                  required_permissions: ['workspace.read'],
                },
              ],
              permissions: [
                { code: 'system.roles.manage', name: '角色管理', risk_level: 'high', status: 'active' },
                { code: 'system.roles.read', name: '查看角色', status: 'active' },
                { code: 'system.users.manage', name: '用户管理', status: 'active' },
                { code: 'workspace.read', name: '工作台读取', status: 'active' },
              ],
              roles: roleCatalogEnvelope.data.items,
              rows: [
                {
                  category: 'system',
                  diagnostics: [
                    {
                      code: 'high_risk_permission',
                      level: 'risk',
                      message: '包含高风险权限点',
                      permission_codes: ['system.roles.manage'],
                    },
                  ],
                  granted_menu_codes: ['system', 'system.roles', 'governance.audit'],
                  granted_permission_codes: ['system.roles.read', 'system.roles.manage', 'system.users.manage'],
                  high_risk_permission_codes: ['system.roles.manage'],
                  high_risk_permission_count: 1,
                  is_system: true,
                  menu_count: 3,
                  missing_menu_permission_codes: [],
                  permission_count: 3,
                  required_permission_codes: ['system.roles.manage'],
                  role_code: 'admin',
                  role_id: 'role_admin',
                  role_name: '系统管理员',
                  scope_count: 1,
                  scope_summary: '全局 1 项',
                  scopes: [{ access_level: 'admin', scope_id: '*', scope_name: '全局', scope_type: 'global' }],
                  standalone_permission_codes: ['system.roles.read', 'system.users.manage'],
                  status: 'active',
                },
                {
                  category: 'readonly',
                  diagnostics: [
                    {
                      code: 'menu_permission_gap',
                      level: 'warning',
                      message: '已授权菜单缺少对应权限点',
                      permission_codes: ['workspace.read'],
                    },
                  ],
                  granted_menu_codes: ['workspace.dashboard'],
                  granted_permission_codes: [],
                  high_risk_permission_codes: [],
                  high_risk_permission_count: 0,
                  is_system: true,
                  menu_count: 1,
                  missing_menu_permission_codes: ['workspace.read'],
                  permission_count: 0,
                  required_permission_codes: ['workspace.read'],
                  role_code: 'viewer',
                  role_id: 'role_viewer',
                  role_name: '查看者',
                  scope_count: 1,
                  scope_summary: '产品 1 项',
                  scopes: [
                    {
                      access_level: 'read',
                      scope_id: 'product_scope_matrix',
                      scope_name: 'AI Brain',
                      scope_type: 'product',
                    },
                  ],
                  standalone_permission_codes: [],
                  status: 'active',
                },
              ],
              summary: {
                active_role_count: 2,
                menu_count: 4,
                permission_count: 4,
                role_count: 2,
                roles_with_high_risk_permissions: 1,
                roles_with_menu_permission_gaps: 1,
                scope_grant_count: 2,
              },
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (String(input).startsWith('/api/system/permissions/diagnostics?')) {
        expect(String(input)).toContain('user_id=user_viewer');
        return new Response(
          JSON.stringify({
            data: {
              checks: [
                {
                  code: 'user_status',
                  message: '用户状态为启用',
                  status: 'allowed',
                  target: 'active',
                },
                {
                  code: 'permission',
                  message: '用户未拥有该权限点',
                  permission: {
                    code: 'workspace.read',
                    name: '工作台读取',
                    risk_level: 'normal',
                  },
                  status: 'blocked',
                  target: 'workspace.read',
                },
              ],
              decision: {
                allowed: false,
                blocked_reasons: ['缺少权限点：workspace.read'],
                granted_reasons: ['角色：viewer'],
              },
              effective: {
                menu_codes: ['workspace.dashboard'],
                permission_codes: [],
                role_codes: ['viewer'],
                scopes: [],
              },
              user: {
                display_name: '查看者',
                id: 'user_viewer',
                roles: ['viewer'],
                status: 'active',
                username: 'viewer@example.com',
              },
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (String(input).startsWith('/api/system/permissions/menu-preview?')) {
        expect(String(input)).toContain('user_id=user_viewer');
        return new Response(
          JSON.stringify({
            data: {
              blocked_menus: [
                {
                  code: 'workspace.dashboard',
                  message: '缺少权限点：workspace.read',
                  missing_permission_codes: ['workspace.read'],
                  name: '团队看板',
                  path: '/welcome',
                  reason: 'missing_permissions',
                  required_permission_codes: ['workspace.read'],
                },
              ],
              effective: {
                menu_codes: ['workspace.dashboard'],
                permission_codes: [],
                role_codes: ['viewer'],
                scopes: [],
              },
              menu_tree: [],
              scope_summary: '未配置范围',
              summary: {
                blocked_menu_count: 1,
                granted_menu_count: 0,
                visible_menu_count: 0,
              },
              user: {
                display_name: '查看者',
                id: 'user_viewer',
                roles: ['viewer'],
                status: 'active',
                username: 'viewer@example.com',
              },
              visible_menu_codes: [],
              visible_menus: [],
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (String(input).startsWith('/api/system/roles?')) {
        const url = new URL(String(input), 'http://localhost');
        expect(url.searchParams.get('page')).toBe('1');
        expect(url.searchParams.get('page_size')).toBe('10');
        expect(url.searchParams.get('sort_by')).toBe('sort_order');
        expect(url.searchParams.get('sort_order')).toBe('asc');
        return new Response(
          JSON.stringify({
            data: {
              ...roleCatalogEnvelope.data,
              page: 1,
              page_size: 10,
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      expect(String(input)).toBe('/api/system/roles');
      return new Response(
        JSON.stringify({
          data: roleCatalogEnvelope.data,
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      );
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<RolesPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('系统管理');
    expect(await screen.findByText('权限审计矩阵')).toBeInTheDocument();
    expect(screen.getByText('用户权限诊断')).toBeInTheDocument();
    expect(screen.getByText('角色权限与范围预览')).toBeInTheDocument();
    expect(screen.getByText('全局范围 1')).toBeInTheDocument();
    expect(screen.getByText('产品范围 1')).toBeInTheDocument();
    expect(screen.getByText('未配置范围 0')).toBeInTheDocument();
    expect(screen.getByText('高风险权限：system.roles.manage')).toBeInTheDocument();
    expect(screen.getByText('菜单权限缺口：workspace.read')).toBeInTheDocument();
    expect(screen.getByText('1 个菜单权限缺口')).toBeInTheDocument();
    expect(screen.getByText('1 个高风险角色')).toBeInTheDocument();
    expect(screen.getByText('已授权菜单缺少对应权限点')).toBeInTheDocument();
    expect(await screen.findByText('角色定义')).toBeInTheDocument();
    expect(screen.getAllByText('系统管理员').length).toBeGreaterThan(0);
    expect(screen.getAllByText('admin').length).toBeGreaterThan(0);
    expect(screen.getAllByText('查看者').length).toBeGreaterThan(0);
    expect(screen.getAllByText('viewer').length).toBeGreaterThan(0);
    expect(screen.getAllByText('系统管理').length).toBeGreaterThan(0);
    expect(screen.getAllByText('全局 · * · 管理').length).toBeGreaterThan(0);
    expect(screen.getAllByText('AI Brain · product_scope_matrix · 读取').length).toBeGreaterThan(0);
    expect(screen.getAllByText('3 个入口').length).toBeGreaterThan(0);
    expect(screen.getAllByText('3 个权限点').length).toBeGreaterThan(0);
    expect(screen.getAllByText('1 个权限点').length).toBeGreaterThan(0);
    expect(screen.getByText('职责与范围')).toBeInTheDocument();
    expect(screen.queryByText('负责用户、角色、模型网关、审计与系统级配置管理。')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '新增角色' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '编辑' }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('button', { name: '复制' }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('button', { name: '角色配置' }).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: '权限' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '菜单' })).not.toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '范围' }).length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText('诊断用户 ID'), { target: { value: 'user_viewer' } });
    fireEvent.click(screen.getByRole('button', { name: '运行诊断' }));

    expect(await screen.findByText('存在阻断')).toBeInTheDocument();
    expect(screen.getAllByText('缺少权限点：workspace.read').length).toBeGreaterThan(0);
    expect(screen.getByText('角色：viewer')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: '角色配置' })[0]);

    expect(await screen.findByRole('dialog', { name: '角色配置 · 系统管理员' })).toBeInTheDocument();
    expect(screen.getByLabelText('角色管理')).toBeChecked();
    expect(screen.getAllByLabelText(/查看角色/).some((item) => item instanceof HTMLInputElement && item.checked)).toBe(
      true,
    );
    expect(
      screen
        .getAllByLabelText(/角色管理 \(system.roles.manage\)/)
        .some((item) => item instanceof HTMLInputElement && item.checked),
    ).toBe(true);
    expect(
      screen
        .getAllByLabelText(/团队看板/)
        .every((item) => item instanceof HTMLInputElement && !item.checked),
    ).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: '角色配置 · 系统管理员' })).not.toBeInTheDocument(),
    );

    fireEvent.click(screen.getAllByRole('button', { name: '详情' })[0]);

    const detailDialog = await screen.findByRole('dialog', { name: '角色详情 · 系统管理员' });
    expect(detailDialog).toBeInTheDocument();
    expect(screen.getByText('负责用户、角色、模型网关、审计与系统级配置管理。')).toBeInTheDocument();
    expect(screen.getByText('system.roles.manage')).toBeInTheDocument();
    expect(screen.getByText('system.users.manage')).toBeInTheDocument();
    expect(screen.getByText('governance.audit')).toBeInTheDocument();
    expect(within(detailDialog).getByText('访问预览')).toBeInTheDocument();
    expect(within(detailDialog).getByText('/system/roles')).toBeInTheDocument();
    expect(within(detailDialog).getByText('角色管理 (system.roles.manage)')).toBeInTheDocument();
    expect(within(detailDialog).getAllByText('全局 · * · 管理').length).toBeGreaterThan(0);
    expect(within(detailDialog).getByText('1 个高风险权限')).toBeInTheDocument();
  });

  it('manages menu resources from the system menu page', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (path === '/api/system/permissions' && method === 'GET') {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  category: 'system',
                  code: 'system.menus.manage',
                  name: '管理菜单',
                  status: 'active',
                },
              ],
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (path.startsWith('/api/system/menus') && method === 'GET') {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  code: 'system',
                  is_system: true,
                  menu_type: 'group',
                  name: '系统管理',
                  path: '/system',
                  required_permissions: [],
                  sort_order: 60,
                  status: 'active',
                },
                {
                  code: 'system.menus',
                  is_system: true,
                  menu_type: 'page',
                  name: '菜单管理',
                  parent_code: 'system',
                  path: '/system/menus',
                  required_permissions: ['system.menus.manage'],
                  sort_order: 64,
                  status: 'active',
                },
              ],
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (path === '/api/system/menus' && method === 'POST') {
        return new Response(
          JSON.stringify({
            data: {
              code: 'system.help',
              icon: 'QuestionCircleOutlined',
              is_system: false,
              menu_type: 'page',
              name: '系统帮助',
              parent_code: 'system',
              path: '/system/help',
              required_permissions: ['system.menus.manage'],
              sort_order: 65,
              status: 'active',
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      return Promise.reject(new Error(`Unexpected fetch call: ${path}`));
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<MenusPage />);

    expect(await screen.findByText('菜单资源')).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([path]) => (
        String(path).startsWith('/api/system/menus?')
        && String(path).includes('page=1')
        && String(path).includes('page_size=10')
        && String(path).includes('sort_by=sort_order')
        && String(path).includes('sort_order=asc')
      ))).toBe(true),
    );
    expect(screen.getAllByText('菜单管理').length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('button', { name: '新增菜单' }));
    const menuDialog = within(await screen.findByRole('dialog', { name: '新增菜单' }));

    fireEvent.change(menuDialog.getByLabelText('菜单编码'), {
      target: { value: 'system.help' },
    });
    fireEvent.change(menuDialog.getByLabelText('菜单名称'), {
      target: { value: '系统帮助' },
    });
    fireEvent.change(menuDialog.getByLabelText(/路由路径/), {
      target: { value: '/system/help' },
    });
    fireEvent.change(menuDialog.getByLabelText('图标'), {
      target: { value: 'QuestionCircleOutlined' },
    });
    fireEvent.change(menuDialog.getByLabelText('排序号'), {
      target: { value: '65' },
    });
    fireEvent.click(menuDialog.getByLabelText(/管理菜单 \(system.menus.manage\)/));
    fireEvent.click(menuDialog.getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/system/menus',
        'POST',
      ]),
    );
    const createCall = fetchMock.mock.calls.find(
      ([path, init]) => path === '/api/system/menus' && init?.method === 'POST',
    );
    expect(JSON.parse(String(createCall?.[1]?.body))).toEqual({
      code: 'system.help',
      icon: 'QuestionCircleOutlined',
      menu_type: 'page',
      name: '系统帮助',
      path: '/system/help',
      required_permissions: ['system.menus.manage'],
      sort_order: 65,
      status: 'active',
    });
  });
});
