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
        expect(JSON.parse(String(init.body))).toEqual({ admin_email: 'admin@example.com' });
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
    expect(screen.getByText('已配置')).toBeInTheDocument();
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
});
