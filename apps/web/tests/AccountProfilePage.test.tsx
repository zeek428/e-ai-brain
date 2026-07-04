import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import AccountProfilePage from '../src/pages/AccountProfile';

describe('AccountProfilePage', () => {
  afterEach(() => {
    message.destroy();
    cleanup();
    window.localStorage.clear();
    window.history.pushState({}, '', '/');
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('updates current user profile, password, and DingTalk binding state', async () => {
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    const profileResponse = {
      display_name: 'AI Brain Admin',
      dingtalk_binding: {
        bound: true,
        corp_id: 'ding-corp',
        display_name: '钉钉管理员',
        email: 'admin.dingtalk@example.com',
        provider: 'dingtalk',
      },
      email: 'admin@example.com',
      id: 'user_admin',
      menu_tree: [{ code: 'workspace.dashboard', name: '团队看板', path: '/welcome' }],
      mobile: '',
      roles: ['admin'],
      username: 'admin@example.com',
    };
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      if (path === '/api/auth/profile' && (init?.method ?? 'GET') === 'GET') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return new Response(JSON.stringify({ data: profileResponse }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (path === '/api/auth/providers') {
        return new Response(
          JSON.stringify({
            data: {
              dingtalk: {
                enabled: true,
                start_url: '/api/auth/dingtalk/start',
              },
              local: { enabled: true },
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (path === '/api/auth/profile' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body));
        if (body.new_password) {
          expect(body).toEqual({
            current_password: 'old-secret',
            new_password: 'new-secret-123',
          });
          return new Response(JSON.stringify({ data: { user: profileResponse } }), {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          });
        }
        expect(body).toEqual({
          current_password: 'admin123',
          display_name: 'AI Brain Owner',
          email: 'owner@example.com',
          mobile: '+86 13800000000',
        });
        return new Response(
          JSON.stringify({
            data: {
              access_token: 'token-owner',
              user: {
                ...profileResponse,
                display_name: 'AI Brain Owner',
                email: 'owner@example.com',
                mobile: '+86 13800000000',
                username: 'owner@example.com',
              },
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        );
      }
      if (path === '/api/auth/dingtalk/unbind' && init?.method === 'POST') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-owner' });
        return new Response(JSON.stringify({ data: { success: true } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      throw new Error(`Unexpected fetch call: ${path} ${init?.method ?? 'GET'}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<AccountProfilePage />);

    expect(await screen.findByText('admin@example.com')).toBeInTheDocument();
    expect(screen.getByText('钉钉管理员')).toBeInTheDocument();
    expect(screen.getByText('ding-corp')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('显示名称'), {
      target: { value: 'AI Brain Owner' },
    });
    fireEvent.change(screen.getByLabelText('邮箱'), {
      target: { value: 'owner@example.com' },
    });
    fireEvent.change(screen.getByLabelText('手机号'), {
      target: { value: '+86 13800000000' },
    });
    fireEvent.change(screen.getByLabelText('资料当前密码'), {
      target: { value: 'admin123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /保存资料/ }));

    await waitFor(() => expect(window.localStorage.getItem('ai_brain_access_token')).toBe('token-owner'));
    expect(window.localStorage.getItem('ai_brain_current_user')).toContain('owner@example.com');

    fireEvent.change(screen.getByLabelText('密码当前密码'), {
      target: { value: 'old-secret' },
    });
    fireEvent.change(screen.getByLabelText('新密码'), {
      target: { value: 'new-secret-123' },
    });
    fireEvent.change(screen.getByLabelText('确认新密码'), {
      target: { value: 'new-secret-123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /更新密码/ }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/auth/profile',
        expect.objectContaining({ method: 'PATCH' }),
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: /解\s*绑/ }));
    const popconfirm = await screen.findByRole('tooltip');
    fireEvent.click(within(popconfirm).getByRole('button', { name: /解\s*绑/ }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/auth/dingtalk/unbind',
        expect.objectContaining({ method: 'POST' }),
      ),
    );
  });
});
