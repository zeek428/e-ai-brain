import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import { getInitialState, layout } from '../src/app';
import DingTalkLoginCallbackPage from '../src/pages/DingTalkLoginCallback';
import LoginPage from '../src/pages/Login';
import { handleLogout, redirectToLoginIfNeeded } from '../src/runtimeAuth';
import {
  AUTH_STATE_EVENT,
  buildDingTalkStartUrl,
  clearAccessToken,
  saveCurrentUser,
} from '../src/services/aiBrain';

describe('AI Brain auth flow and routes', () => {
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

  it('registers the MVP workbench entries through Umi route config', () => {
    const routes = readFileSync(join(__dirname, '..', 'config', 'routes.ts'), 'utf8');

    expect(routes).toContain("path: '/login/dingtalk/callback'");
    expect(routes).toContain("component: './DingTalkLoginCallback'");
    expect(routes).toContain("path: '/login'");
    expect(routes).toContain("component: './Login'");
    expect(routes).toContain('layout: false');
    expect(routes).toContain("path: '/welcome'");
    expect(routes).toContain("name: '团队看板'");
    expect(routes).toContain("path: '/assistant'");
    expect(routes).toContain("name: 'AI 助手'");
    expect(routes).toContain("component: './Assistant'");
    expect(routes).not.toContain("name: '欢迎'");
    expect(routes).toContain("path: '/tasks'");
    expect(routes).toContain("name: '任务中心'");
    expect(routes).toContain("redirect: '/tasks/scheduled-jobs'");
    expect(routes).not.toContain("name: '任务管理'");
    expect(routes).toContain("redirect: '/login'");
    expect(routes).not.toContain("name: '工作台'");
    expect(routes).toContain("name: '需求交付'");
    expect(routes).toContain("path: '/delivery/rd-tasks'");
    expect(routes).toContain("name: '研发任务'");
    expect(routes).toContain("name: '产品资产'");
    expect(routes).toContain("name: '运营治理'");
    expect(routes).toContain("name: '系统管理'");
    expect(routes).toContain("name: '产品管理'");
    expect(routes).toContain("name: '需求管理'");
    expect(routes).toContain("name: '迭代版本'");
    expect(routes).toContain("name: '知识中心'");
    expect(routes).toContain("name: '审计与运行'");
    expect(routes).toContain("path: '/delivery/requirements'");
    expect(routes).toContain("path: '/delivery/versions'");
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
    expect(routes).toContain("path: '/tasks/ai-capabilities'");
    expect(routes).toContain("name: 'AI 能力配置'");
    expect(routes).toContain("component: './AiCapabilities'");
    expect(routes).toContain("path: '/tasks/scheduled-jobs'");
    expect(routes).toContain("name: '定时作业'");
    expect(routes).toContain("component: './ScheduledJobs'");
    expect(routes).toContain("path: '/tasks/plugins'");
    expect(routes).toContain("name: '插件管理'");
    expect(routes).toContain("component: './Plugins'");
    expect(routes).toContain("path: '/system/ai-capabilities'");
    expect(routes).toContain("redirect: '/tasks/ai-capabilities'");
    expect(routes).toContain("path: '/system/scheduled-jobs'");
    expect(routes).toContain("redirect: '/tasks/scheduled-jobs'");
    expect(routes).toContain("path: '/system/plugins'");
    expect(routes).toContain("redirect: '/tasks/plugins'");
    expect(routes).toContain("path: '/tasks/management'");
    expect(routes).toContain("redirect: '/delivery/rd-tasks'");
    expect(routes).toContain("path: '/workspace/tasks'");
    expect(routes).toContain("component: './TaskCenter'");
  });

  it('logs in with the development account and redirects to the requested page', async () => {
    window.history.pushState({}, '', '/login?redirect=%2Fdelivery%2Fbugs');
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/auth/providers') {
        return new Response(
          JSON.stringify({
            data: {
              dingtalk: {
                display_name: '钉钉登录',
                enabled: false,
              },
              local: {
                display_name: '账号密码登录',
                enabled: true,
              },
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (input === '/api/auth/me') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return new Response(
          JSON.stringify({
            data: {
              display_name: 'AI Brain Admin',
              id: 'user_admin',
              menu_tree: [{ code: 'workspace.dashboard', name: '团队看板', path: '/welcome' }],
              roles: ['admin'],
              username: 'admin@example.com',
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
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

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(window.localStorage.getItem('ai_brain_access_token')).toBe('token-admin');
    expect(window.localStorage.getItem('ai_brain_current_user')).toContain('menu_tree');
    expect(window.location.pathname).toBe('/delivery/bugs');
  });

  it('shows the DingTalk login option when the backend enables the provider', async () => {
    window.history.pushState({}, '', '/login?redirect=%2Fdelivery%2Fbugs');
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(async (input) => {
        expect(input).toBe('/api/auth/providers');
        return new Response(
          JSON.stringify({
            data: {
              dingtalk: {
                display_name: '钉钉登录',
                enabled: true,
                start_url: '/api/auth/dingtalk/start',
              },
              local: {
                display_name: '账号密码登录',
                enabled: true,
              },
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

    expect(await screen.findByRole('button', { name: /钉钉登录/ })).toBeInTheDocument();
    expect(buildDingTalkStartUrl('/delivery/bugs')).toBe(
      '/api/auth/dingtalk/start?redirect=%2Fdelivery%2Fbugs',
    );
  });

  it('exchanges a DingTalk callback ticket and redirects to the requested page', async () => {
    window.history.pushState(
      {},
      '',
      '/login/dingtalk/callback?ticket=ticket-001&redirect=%2Fdelivery%2Fbugs',
    );
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/auth/dingtalk/exchange-ticket') {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toEqual({ ticket: 'ticket-001' });
        return new Response(
          JSON.stringify({
            data: {
              access_token: 'token-dingtalk',
              user: {
                display_name: '钉钉张三',
                id: 'user_dingtalk',
                roles: ['viewer'],
                username: 'zhangsan@example.com',
              },
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      expect(input).toBe('/api/auth/me');
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-dingtalk' });
      return new Response(
        JSON.stringify({
          data: {
            display_name: '钉钉张三',
            id: 'user_dingtalk',
            menu_tree: [{ code: 'workspace.dashboard', name: '团队看板', path: '/welcome' }],
            roles: ['viewer'],
            username: 'zhangsan@example.com',
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<DingTalkLoginCallbackPage />);

    await waitFor(() => expect(window.location.pathname).toBe('/delivery/bugs'));
    expect(window.localStorage.getItem('ai_brain_access_token')).toBe('token-dingtalk');
    expect(window.localStorage.getItem('ai_brain_current_user')).toContain('menu_tree');
    expect(fetchMock).toHaveBeenCalledTimes(2);
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
            menu_tree: [{ code: 'workspace.dashboard', name: '团队看板', path: '/welcome' }],
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
        id: 'user_real',
        isAuthenticated: true,
        menuTree: [{ code: 'workspace.dashboard', name: '团队看板', path: '/welcome' }],
        name: '真实用户',
        role: 'product_owner, rd_owner',
        username: 'real@example.com',
      },
    });
    expect(window.localStorage.getItem('ai_brain_current_user')).toContain('real@example.com');
  });

  it('filters the left menu from the authorized menu tree returned by auth me', () => {
    const menuConfig = layout({
      initialState: {
        currentUser: {
          menuTree: [
            {
              children: [
                {
                  code: 'delivery.bugs',
                  name: 'Bug 管理',
                  path: '/delivery/bugs',
                },
              ],
              code: 'delivery',
              name: '需求交付',
              path: '/delivery',
            },
          ],
          isAuthenticated: true,
          name: '测试用户',
          role: 'tester',
        },
      },
    });
    const menuDataRender = menuConfig.menuDataRender as (routes: Array<Record<string, unknown>>) => Array<Record<string, unknown>>;
    const filteredMenu = menuDataRender([
      {
        name: '需求交付',
        path: '/delivery',
        routes: [
          { name: '需求管理', path: '/delivery/requirements' },
          { name: 'Bug 管理', path: '/delivery/bugs' },
        ],
      },
      {
        name: '系统管理',
        path: '/system',
        routes: [{ name: '角色管理', path: '/system/roles' }],
      },
    ]);

    expect(filteredMenu).toHaveLength(1);
    expect(filteredMenu[0]).toMatchObject({
      name: '需求交付',
      routes: [{ name: 'Bug 管理', path: '/delivery/bugs' }],
    });
  });

  it('sorts the left menu using the authorized menu tree order', () => {
    const menuConfig = layout({
      initialState: {
        currentUser: {
          menuTree: [
            {
              children: [{ code: 'system.roles', name: '角色管理', path: '/system/roles' }],
              code: 'system',
              name: '系统管理',
              path: '/system',
            },
            {
              children: [
                {
                  code: 'system.scheduled_jobs',
                  name: '定时作业',
                  path: '/tasks/scheduled-jobs',
                },
                {
                  code: 'system.ai_capabilities',
                  name: 'AI 能力配置',
                  path: '/tasks/ai-capabilities',
                },
              ],
              code: 'task',
              name: '任务中心',
              path: '/tasks',
            },
          ],
          isAuthenticated: true,
          name: '系统管理员',
          role: 'admin',
        },
      },
    });
    const menuDataRender = menuConfig.menuDataRender as (routes: Array<Record<string, unknown>>) => Array<Record<string, unknown>>;
    const filteredMenu = menuDataRender([
      {
        name: '任务中心',
        path: '/tasks',
        children: [
          { name: 'AI 能力配置', path: '/tasks/ai-capabilities' },
          { name: '定时作业', path: '/tasks/scheduled-jobs' },
        ],
        routes: [
          { name: 'AI 能力配置', path: '/tasks/ai-capabilities' },
          { name: '定时作业', path: '/tasks/scheduled-jobs' },
        ],
      },
      {
        name: '系统管理',
        path: '/system',
        routes: [{ name: '角色管理', path: '/system/roles' }],
      },
    ]);

    expect(filteredMenu.map((item) => item.name)).toEqual(['系统管理', '任务中心']);
    expect((filteredMenu[1].routes as Array<Record<string, unknown>>).map((item) => item.name)).toEqual([
      '定时作业',
      'AI 能力配置',
    ]);
    expect((filteredMenu[1].children as Array<Record<string, unknown>>).map((item) => item.name)).toEqual([
      '定时作业',
      'AI 能力配置',
    ]);
  });

  it('uses the latest stored menu tree instead of stale initial state menus', () => {
    saveCurrentUser({
      display_name: '产品负责人',
      id: 'user_produce',
      menu_tree: [
        {
          children: [
            {
              code: 'product.products',
              name: '产品管理',
              path: '/assets/products',
            },
          ],
          code: 'product.assets',
          name: '产品资产',
          path: '/assets',
        },
      ],
      roles: ['product_owner'],
      username: 'produce',
    });
    const menuConfig = layout({
      initialState: {
        currentUser: {
          menuTree: [
            {
              children: [{ code: 'system.roles', name: '角色管理', path: '/system/roles' }],
              code: 'system',
              name: '系统管理',
              path: '/system',
            },
          ],
          isAuthenticated: true,
          name: '系统管理员',
          role: 'admin',
        },
      },
    });
    const menuDataRender = menuConfig.menuDataRender as (routes: Array<Record<string, unknown>>) => Array<Record<string, unknown>>;
    const filteredMenu = menuDataRender([
      {
        name: '产品资产',
        path: '/assets',
        routes: [{ name: '产品管理', path: '/assets/products' }],
      },
      {
        name: '系统管理',
        path: '/system',
        routes: [{ name: '角色管理', path: '/system/roles' }],
      },
    ]);

    expect(filteredMenu).toHaveLength(1);
    expect(filteredMenu[0]).toMatchObject({
      name: '产品资产',
      routes: [{ name: '产品管理', path: '/assets/products' }],
    });
  });

  it('hides the left menu for authenticated users without granted menus', () => {
    const menuConfig = layout({
      initialState: {
        currentUser: {
          isAuthenticated: true,
          menuTree: [],
          name: '无菜单用户',
          role: 'limited_user',
        },
      },
    });
    const menuDataRender = menuConfig.menuDataRender as (routes: Array<Record<string, unknown>>) => Array<Record<string, unknown>>;
    const filteredMenu = menuDataRender([
      {
        name: '团队看板',
        path: '/welcome',
      },
      {
        name: '系统管理',
        path: '/system',
        routes: [{ name: '角色管理', path: '/system/roles' }],
      },
    ]);

    expect(filteredMenu).toEqual([]);
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
    expect(redirectToLoginIfNeeded('/login/dingtalk/callback', '?ticket=abc')).toBe(false);
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
});
