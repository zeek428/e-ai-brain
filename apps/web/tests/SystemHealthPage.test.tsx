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
            operations: {
              ai_executor_ops: {
                failure_reason_distribution: [{ count: 1, reason: 'AI_EXECUTOR_TASK_FAILED' }],
                latest_active_tasks: [
                  {
                    id: 'runner_task_queued',
                    runner_id: 'runner_1',
                    status: 'queued',
                  },
                ],
                latest_failures: [
                  {
                    error_code: 'AI_EXECUTOR_TASK_FAILED',
                    id: 'runner_task_failed',
                    status: 'failed',
                  },
                ],
                operation_targets: {
                  cancellable_count: 1,
                  retryable_count: 1,
                  timeout_scan_count: 0,
                },
                runner_health: { active_runner_count: 1 },
                summary: {
                  failed_total: 1,
                  pending_approval_count: 1,
                  queue_pressure: 0.5,
                  queued_count: 2,
                  running_count: 1,
                },
                task_status_counts: { queued: 2, running: 1 },
              },
              alert_center: {
                alerts: [
                  {
                    action_href: '/tasks/plugins',
                    component: 'dingtalk_mcp',
                    id: 'check:dingtalk_mcp',
                    message: '到插件管理重新测试钉钉知识库连接。',
                    owner: '平台运维',
                    severity: 'low',
                    source: 'system_check',
                    status: 'open',
                    title: '钉钉 MCP 连接',
                  },
                ],
                summary: {
                  high_count: 0,
                  low_count: 1,
                  medium_count: 0,
                  open_count: 1,
                },
              },
              dingtalk_lifecycle: {
                login: { configured: true, enabled: true },
                mcp: {
                  connection_count: 1,
                  failed_connection_count: 1,
                  key_expiry_alerts: [
                    {
                      connection_id: 'connection_dingtalk_health_center',
                      connection_name: '钉钉知识库',
                      days_left: 12,
                      severity: 'warning',
                    },
                  ],
                  soon_expiring_count: 1,
                },
                user_bindings: { active_identity_count: 3 },
              },
              help_and_retention: {
                retention_policies: [
                  {
                    configured: false,
                    days: 365,
                    env: 'AUDIT_RETENTION_DAYS',
                    key: 'audit_events',
                    note: '合规审计建议至少保留一年。',
                    title: '审计事件',
                  },
                ],
                screenshots: {
                  coverage: { expected_count: 2, ready_count: 2 },
                  screenshots: [{ article: '系统健康', exists: true, route: '/system/health' }],
                },
              },
              knowledge_quality_loop: {
                quality_gates: [{ metric: 'searchable_ratio', passed: true, value: 1 }],
                summary: {
                  index_failed_documents: 0,
                  pending_deposit_count: 0,
                  searchable_ratio: 1,
                  total_documents: 6,
                },
              },
              permission_diagnostics: {
                diagnostics: [{ level: 'warning', message: '存在菜单授权与权限点不一致的角色' }],
                summary: {
                  active_role_count: 5,
                  roles_with_high_risk_permissions: 1,
                  roles_with_menu_permission_gaps: 1,
                },
              },
              product_onboarding_scores: {
                products: [
                  {
                    missing_items: ['未维护关联系统'],
                    name: 'AI Brain',
                    product_id: 'product_ai_brain',
                    score: 90,
                    status: 'ready',
                  },
                ],
                summary: {
                  at_risk_count: 0,
                  average_score: 90,
                  partial_count: 0,
                  ready_count: 1,
                },
              },
            },
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
    expect(screen.getByText('平台治理运维台')).toBeInTheDocument();
    expect(screen.getByText('系统健康告警中心')).toBeInTheDocument();
    expect(screen.getByText('AI 任务执行运维台')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '扫超时' })).toBeInTheDocument();
    expect(screen.getByText('runner_task_queued')).toBeInTheDocument();
    expect(screen.getByText('runner_task_failed')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /取\s*消/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /重\s*试/ })).toBeInTheDocument();
    expect(screen.getByText('知识中心质量闭环')).toBeInTheDocument();
    expect(screen.getByText('产品接入完整度评分')).toBeInTheDocument();
    expect(screen.getByText('钉钉授权生命周期')).toBeInTheDocument();
    expect(screen.getByText('帮助截图自动化与数据归档策略')).toBeInTheDocument();
    expect(screen.getByText('AI Brain')).toBeInTheDocument();
    expect(screen.getByText('SMTP 邮件发送')).toBeInTheDocument();
    expect(screen.getAllByText('钉钉 MCP 连接').length).toBeGreaterThan(0);
    expect(screen.getByText('URL key 已过期')).toBeInTheDocument();
    expect(screen.getByText('smtp.example.com')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /刷新/ }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });
});
