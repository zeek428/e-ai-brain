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
        scopes: [{ access_level: 'admin', scope_id: '*', scope_type: 'global' }],
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
        scopes: [{ access_level: 'read', scope_id: 'self', scope_type: 'product' }],
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
            items: [],
            page: 1,
            page_size: 10,
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
    expect(await screen.findByText('角色定义')).toBeInTheDocument();
    expect(screen.getByText('系统管理员')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
    expect(screen.getByText('查看者')).toBeInTheDocument();
    expect(screen.getByText('viewer')).toBeInTheDocument();
    expect(screen.getAllByText('系统管理').length).toBeGreaterThan(0);
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

    expect(await screen.findByRole('dialog', { name: '角色详情 · 系统管理员' })).toBeInTheDocument();
    expect(screen.getByText('负责用户、角色、模型网关、审计与系统级配置管理。')).toBeInTheDocument();
    expect(screen.getByText('system.roles.manage')).toBeInTheDocument();
    expect(screen.getByText('system.users.manage')).toBeInTheDocument();
    expect(screen.getByText('governance.audit')).toBeInTheDocument();
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
      if (path === '/api/system/menus' && method === 'GET') {
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
