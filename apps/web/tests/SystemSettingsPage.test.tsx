import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { message, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import SystemSettingsPage from '../src/pages/SystemSettings';

describe('SystemSettingsPage', () => {
  afterEach(() => {
    cleanup();
    message.destroy();
    notification.destroy();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('loads and updates the system administrator email', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input) === '/api/system/settings' && (init?.method ?? 'GET') === 'GET') {
        return jsonResponse({
          data: {
            admin_email: 'ops@example.com',
            admin_email_configured: true,
            updated_at: '2026-07-03T02:30:00+00:00',
            updated_by: 'user_admin',
          },
        });
      }
      if (String(input) === '/api/system/settings' && init?.method === 'PATCH') {
        expect(JSON.parse(String(init.body))).toMatchObject({
          admin_email: 'admin@example.com',
          email_delivery: {
            enabled: false,
            smtp_tls: 'starttls',
          },
        });
        return jsonResponse({
          data: {
            admin_email: 'admin@example.com',
            admin_email_configured: true,
            updated_at: '2026-07-03T03:00:00+00:00',
            updated_by: 'user_admin',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<SystemSettingsPage />);

    const emailInput = await screen.findByLabelText('系统管理员邮箱');
    expect(emailInput).toHaveValue('ops@example.com');
    expect(screen.getByText('管理员邮箱已配置')).toBeInTheDocument();
    expect(screen.getByText('2026-07-03 10:30')).toBeInTheDocument();

    fireEvent.change(emailInput, { target: { value: 'admin@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /保存/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/system/settings',
        'PATCH',
      ]),
    );
    expect(await screen.findByDisplayValue('admin@example.com')).toBeInTheDocument();
    expect(screen.getByText('2026-07-03 11:00')).toBeInTheDocument();
  });

  it('edits and tests email delivery settings without echoing the password', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input) === '/api/system/settings' && (init?.method ?? 'GET') === 'GET') {
        return jsonResponse({
          data: {
            admin_email: 'ops@example.com',
            admin_email_configured: true,
            email_delivery: {
              default_from: 'noreply@example.com',
              enabled: true,
              reply_to: 'support@example.com',
              sender_email: 'noreply@example.com',
              smtp_host: 'smtp.example.com',
              smtp_password_configured: true,
              smtp_port: 465,
              smtp_secret_ref: '',
              smtp_tls: 'ssl',
              smtp_username: 'noreply@example.com',
            },
            email_delivery_configured: true,
            updated_at: '2026-07-03T02:30:00+00:00',
            updated_by: 'user_admin',
          },
        });
      }
      if (String(input) === '/api/system/settings' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body));
        expect(body.email_delivery).toMatchObject({
          default_from: 'alerts@example.com',
          enabled: true,
          reply_to: 'support@example.com',
          sender_email: 'alerts@example.com',
          smtp_host: 'smtp.example.com',
          smtp_password: 'new-secret-password',
          smtp_port: 587,
          smtp_tls: 'starttls',
          smtp_username: 'alerts@example.com',
        });
        return jsonResponse({
          data: {
            ...body,
            email_delivery: {
              ...body.email_delivery,
              smtp_password: undefined,
              smtp_password_configured: true,
            },
            email_delivery_configured: true,
            updated_at: '2026-07-03T03:00:00+00:00',
            updated_by: 'user_admin',
          },
        });
      }
      if (
        String(input) === '/api/system/settings/email/test'
        && init?.method === 'POST'
      ) {
        expect(JSON.parse(String(init.body))).toEqual({ recipient_email: 'qa@example.com' });
        return jsonResponse({
          data: {
            delivery_status: 'sent',
            recipient_email: 'qa@example.com',
            smtp_host: 'smtp.example.com',
            smtp_port: 587,
            smtp_tls: 'starttls',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<SystemSettingsPage />);

    expect(await screen.findByLabelText('SMTP Host')).toHaveValue('smtp.example.com');
    expect(screen.getByLabelText('SMTP 端口')).toHaveValue('465');
    expect(screen.getByLabelText('SMTP 密码/授权码')).toHaveAttribute(
      'placeholder',
      '已配置，留空则继续沿用',
    );

    fireEvent.change(screen.getByLabelText('发件邮箱'), {
      target: { value: 'alerts@example.com' },
    });
    fireEvent.change(screen.getByLabelText('默认发件人'), {
      target: { value: 'alerts@example.com' },
    });
    fireEvent.change(screen.getByLabelText('SMTP 用户名'), {
      target: { value: 'alerts@example.com' },
    });
    fireEvent.change(screen.getByLabelText('SMTP 端口'), {
      target: { value: '587' },
    });
    fireEvent.mouseDown(screen.getByLabelText('加密方式'));
    fireEvent.click(await screen.findByText('STARTTLS'));
    fireEvent.change(screen.getByLabelText('SMTP 密码/授权码'), {
      target: { value: 'new-secret-password' },
    });
    fireEvent.click(screen.getByRole('button', { name: /保存/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/system/settings',
        'PATCH',
      ]),
    );

    fireEvent.change(screen.getByLabelText('测试收件人'), {
      target: { value: 'qa@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /发送测试邮件/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/system/settings/email/test',
        'POST',
      ]),
    );
  });
});
