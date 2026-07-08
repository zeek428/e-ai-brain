import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { message, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import SystemHealthPage from '../src/pages/SystemHealth';

describe('SystemHealthPage', () => {
  afterEach(() => {
    cleanup();
    message.destroy();
    notification.destroy();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders aggregated health checks and operations shortcuts', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      expect(String(input)).toBe('/api/system/health');
      return new Response(
        JSON.stringify({
          data: {
            checked_at: '2026-07-08T08:30:00+00:00',
            checks: [
              {
                action_href: '/system/settings',
                category: '外部通知',
                component: 'smtp',
                description: '邮件发送配置完整。',
                fix_suggestion: '定期发送测试邮件。',
                key: 'smtp',
                metrics: { enabled: true, smtp_host: 'smtp.example.com' },
                status: 'configured',
                title: 'SMTP 邮件发送',
              },
              {
                action_href: '/tasks/plugins',
                category: '插件集成',
                component: 'dingtalk_mcp',
                description: '已安装钉钉 MCP 插件，但最近测试失败。',
                fix_suggestion: '到插件管理重新测试钉钉知识库连接。',
                key: 'dingtalk_mcp',
                last_error: 'URL key 已过期',
                metrics: { connection_count: 1, failed_connection_count: 1 },
                status: 'warning',
                title: '钉钉 MCP 连接',
              },
            ],
            overall_status: 'warning',
            recommendations: [
              {
                action_href: '/tasks/plugins',
                component: 'dingtalk_mcp',
                message: '到插件管理重新测试钉钉知识库连接。',
                severity: 'medium',
                title: '钉钉 MCP 连接',
              },
            ],
            summary: {
              category_counts: {},
              critical_count: 0,
              needs_attention_count: 1,
              ok_count: 1,
              status_counts: { configured: 1, warning: 1 },
              total: 2,
            },
            trace_id: 'trace_health_001',
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

    render(<SystemHealthPage />);

    expect(await screen.findByText('系统可用，但仍有配置待完善')).toBeInTheDocument();
    expect(screen.getByText(/Trace ID：trace_health_001/)).toBeInTheDocument();
    expect(screen.getByText('权限诊断')).toBeInTheDocument();
    expect(screen.getByText('模型网关')).toBeInTheDocument();
    expect(screen.getByText('SMTP 邮件发送')).toBeInTheDocument();
    expect(screen.getAllByText('钉钉 MCP 连接').length).toBeGreaterThan(0);
    expect(screen.getByText('URL key 已过期')).toBeInTheDocument();
    expect(screen.getByText('smtp.example.com')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /刷新/ }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });
});
