import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import { getInitialState } from '../src/app';
import LoginPage from '../src/pages/Login';
import { handleLogout, redirectToLoginIfNeeded } from '../src/runtimeAuth';
import { AUTH_STATE_EVENT, clearAccessToken, saveCurrentUser } from '../src/services/aiBrain';

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
});
