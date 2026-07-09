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
          test_recipient_email: null,
        });
        return jsonResponse({
          data: {
            admin_email: 'admin@example.com',
            admin_email_configured: true,
            test_recipient_email: null,
            test_recipient_email_configured: false,
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
    expect(screen.getByLabelText('测试收件人')).toHaveValue('');
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
    expect(await screen.findByLabelText('系统管理员邮箱')).toHaveValue('admin@example.com');
    expect(screen.getByText('2026-07-03 11:00')).toBeInTheDocument();
  });

  it('saves current email delivery settings before sending a test email', async () => {
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
            test_recipient_email: null,
            test_recipient_email_configured: false,
            updated_at: '2026-07-03T02:30:00+00:00',
            updated_by: 'user_admin',
          },
        });
      }
      if (String(input) === '/api/system/settings' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body));
        expect(body.test_recipient_email).toBe('qa@example.com');
        expect(body.high_risk_confirmation).toMatchObject({
          confirmed: true,
          reason: expect.stringContaining('smtp_password'),
        });
        expect(body.email_delivery).not.toHaveProperty('smtp_secret_ref');
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
            admin_email: body.admin_email,
            email_delivery: {
              ...body.email_delivery,
              smtp_password: undefined,
              smtp_password_configured: true,
            },
            email_delivery_configured: true,
            test_recipient_email: body.test_recipient_email,
            test_recipient_email_configured: true,
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
            message_subject: '[AI Brain] 邮件发送配置测试 test1234',
            recipient_email: 'qa@example.com',
            sent_at: '2026-07-03T03:00:01+00:00',
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
    expect(screen.getByLabelText('测试收件人')).toHaveValue('');
    expect(screen.getByLabelText('SMTP 端口')).toHaveValue('465');
    expect(screen.getByLabelText('SMTP 密码/授权码')).toHaveAttribute(
      'placeholder',
      '已配置，留空则继续沿用',
    );
    expect(screen.queryByLabelText('SMTP 密钥引用')).not.toBeInTheDocument();

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
    fireEvent.change(screen.getByLabelText('测试收件人'), {
      target: { value: 'qa@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /发送测试邮件/ }));
    expect((await screen.findAllByText('确认敏感配置变更')).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/SMTP 密码\/授权码/).length).toBeGreaterThan(1);
    fireEvent.click(screen.getByRole('button', { name: '确认保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/system/settings/email/test',
        'POST',
      ]),
    );
    const methods = fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET']);
    expect(methods).toEqual([
      ['/api/system/settings', 'GET'],
      ['/api/system/settings', 'PATCH'],
      ['/api/system/settings/email/test', 'POST'],
    ]);
    expect(screen.getByLabelText('测试收件人')).toHaveValue('qa@example.com');
    expect(screen.getByLabelText('测试收件人')).not.toHaveValue('alerts@example.com');
  });

  it('does not default the test recipient to the sender email', async () => {
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
            admin_email: null,
            admin_email_configured: false,
            email_delivery: {
              default_from: 'noreply@example.com',
              enabled: true,
              sender_email: 'noreply@example.com',
              smtp_host: 'smtp.example.com',
              smtp_password_configured: true,
              smtp_port: 465,
              smtp_tls: 'ssl',
              smtp_username: 'noreply@example.com',
            },
            email_delivery_configured: true,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<SystemSettingsPage />);

    expect(await screen.findByLabelText('发件邮箱')).toHaveValue('noreply@example.com');
    expect(screen.getByLabelText('测试收件人')).toHaveValue('');
    expect(screen.getByLabelText('测试收件人')).not.toHaveValue('noreply@example.com');
  });

  it('shows an actionable SMTP authentication diagnostic when test delivery fails', async () => {
    const jsonResponse = (body: unknown, status = 200) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status,
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
              sender_email: 'noreply@example.com',
              smtp_host: 'smtp.example.com',
              smtp_password_configured: true,
              smtp_port: 465,
              smtp_tls: 'ssl',
              smtp_username: 'noreply@example.com',
            },
            email_delivery_configured: true,
            test_recipient_email: 'qa@example.com',
            test_recipient_email_configured: true,
          },
        });
      }
      if (String(input) === '/api/system/settings' && init?.method === 'PATCH') {
        return jsonResponse({
          data: {
            admin_email: 'ops@example.com',
            admin_email_configured: true,
            email_delivery: {
              default_from: 'noreply@example.com',
              enabled: true,
              sender_email: 'noreply@example.com',
              smtp_host: 'smtp.example.com',
              smtp_password_configured: true,
              smtp_port: 465,
              smtp_tls: 'ssl',
              smtp_username: 'noreply@example.com',
            },
            email_delivery_configured: true,
            test_recipient_email: 'qa@example.com',
            test_recipient_email_configured: true,
          },
        });
      }
      if (
        String(input) === '/api/system/settings/email/test'
        && init?.method === 'POST'
      ) {
        return jsonResponse(
          {
            detail: {
              code: 'EMAIL_DELIVERY_TEST_FAILED',
              error_type: 'SMTPAuthenticationError',
              message: 'Email delivery test failed',
              trace_id: 'trace_auth_failed',
            },
          },
          502,
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<SystemSettingsPage />);

    expect(await screen.findByLabelText('测试收件人')).toHaveValue('qa@example.com');
    fireEvent.click(screen.getByRole('button', { name: /发送测试邮件/ }));

    expect(await screen.findByText(/SMTP 认证失败/)).toBeInTheDocument();
    expect(screen.getAllByText(/客户端授权码/).length).toBeGreaterThan(0);
  });
});
