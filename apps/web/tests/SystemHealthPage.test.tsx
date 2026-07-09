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
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    const healthEnvelope = {
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
                first_seen_at: '2026-07-08T07:30:00+00:00',
                id: 'check:dingtalk_mcp',
                message: '到插件管理重新测试钉钉知识库连接。',
                owner: '平台运维',
                severity: 'low',
                source: 'system_check',
                status: 'open',
                title: '钉钉 MCP 连接',
              },
            ],
            rules: [
              {
                enabled: true,
                id: 'rule_health',
                name: '钉钉 MCP 失败规则',
                severity_min: 'medium',
                source: 'system_check',
              },
            ],
            summary: {
              enabled_rule_count: 1,
              high_count: 0,
              low_count: 1,
              medium_count: 0,
              open_count: 1,
              resolving_count: 0,
              rule_count: 1,
            },
            trend: [{ closed: 0, date: '2026-07-08', opened: 1 }],
          },
          dingtalk_lifecycle: {
            authorization_boundaries: [
              {
                description: '个人授权代表具体用户，授权失效或人员离职会影响连接。',
                subject_type: 'user',
                title: '个人授权',
              },
              {
                description: '系统授权代表企业统一连接，适合知识库等共享能力。',
                subject_type: 'system',
                title: '系统授权',
              },
              {
                description: '应用授权代表钉钉应用身份，适合稳定的企业级自动化。',
                subject_type: 'app',
                title: '应用授权',
              },
            ],
            authorization_subject_summary: { app: 0, system: 1, unknown: 0, user: 0 },
            authorization_subjects: [
              {
                boundary: '系统授权适合企业统一连接，由管理员集中维护和轮换。',
                connection_id: 'connection_dingtalk_health_center',
                connection_name: '钉钉知识库',
                corp_id: 'dingcorp_health',
                corp_name: '青锋科技',
                days_left: 12,
                expires_at: '2026-07-20T00:00:00+00:00',
                expiry_status: 'warning',
                last_test_status: 'failed',
                subject_label: '钉钉知识库 · 系统授权',
                subject_type: 'system',
                subject_type_label: '系统授权',
              },
            ],
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
            governance_candidates: [
              {
                document_id: 'knowledge_document_failed',
                index_status: 'index_failed',
                knowledge_space_name: '研发知识空间',
                reason: '索引未完成或失败',
                severity: 'high',
                suggested_action: '重新索引并查看导入/解析日志',
                title: '研发规范索引失败',
                updated_at: '2026-07-01T00:00:00+08:00',
              },
              {
                document_id: 'knowledge_document_stale',
                index_status: 'text_indexed',
                knowledge_space_name: '研发知识空间',
                reason: '仅关键词索引，缺少向量召回、180 天未更新',
                severity: 'medium',
                suggested_action: '补齐 Embedding 配置并重建向量索引；确认内容是否过期，更新文档或归档',
                title: '长期未更新知识文档',
                updated_at: '2024-01-01T00:00:00+08:00',
              },
            ],
            governance_summary: {
              governance_candidate_count: 2,
              keyword_only_document_count: 1,
              stale_document_count: 1,
              zero_chunk_document_count: 0,
            },
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
    };
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      const path = String(input);
      const method = init?.method ?? 'GET';
      calls.push({
        body: init?.body ? JSON.parse(String(init.body)) : undefined,
        method,
        path,
      });
      if (path === '/api/system/health') {
        return jsonResponse(healthEnvelope);
      }
      if (path === '/api/system/alerts/check%3Adingtalk_mcp' && method === 'PATCH') {
        return jsonResponse({ data: { ...healthEnvelope.data.operations.alert_center.alerts[0], status: 'closed' } });
      }
      if (path === '/api/system/alerts/subscriptions' && method === 'POST') {
        return jsonResponse({
          data: {
            channel: 'email',
            enabled: true,
            id: 'alert_subscription_1',
            scope: 'global',
            severity_min: 'medium',
            target: 'ops@example.com',
          },
        });
      }
      if (path === '/api/system/alerts/rules' && method === 'POST') {
        return jsonResponse({
          data: {
            enabled: true,
            id: 'alert_rule_new',
            name: '模型网关告警',
            severity_min: 'medium',
            source: 'system_check',
          },
        });
      }
      if (path === '/api/system/alerts/rules/rule_health' && method === 'PATCH') {
        return jsonResponse({
          data: {
            enabled: false,
            id: 'rule_health',
            name: '钉钉 MCP 失败规则',
            severity_min: 'medium',
            source: 'system_check',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${method} ${path}`);
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
    expect(screen.getByRole('button', { name: '新增订阅' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '新增规则' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /停用规则 钉钉 MCP 失败规则/ })).toBeInTheDocument();
    expect(screen.getByText('AI 任务执行运维台')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '扫超时' })).toBeInTheDocument();
    expect(screen.getByText('runner_task_queued')).toBeInTheDocument();
    expect(screen.getByText('runner_task_failed')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /取\s*消/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /重\s*试/ })).toBeInTheDocument();
    expect(screen.getByText('知识中心质量闭环')).toBeInTheDocument();
    expect(screen.getByLabelText('知识治理待办')).toHaveTextContent('治理待办 2');
    expect(screen.getByLabelText('知识治理待办')).toHaveTextContent('研发规范索引失败');
    expect(screen.getByLabelText('知识治理待办')).toHaveTextContent('长期未更新知识文档');
    expect(screen.getByLabelText('知识治理待办')).toHaveTextContent('补齐 Embedding 配置并重建向量索引');
    expect(screen.getByText('产品接入完整度评分')).toBeInTheDocument();
    expect(screen.getByText('钉钉授权生命周期')).toBeInTheDocument();
    expect(screen.getByLabelText('钉钉授权主体统计')).toHaveTextContent('系统 1');
    expect(screen.getByLabelText('钉钉授权边界说明')).toHaveTextContent('个人授权代表具体用户');
    expect(screen.getByLabelText('钉钉授权边界说明')).toHaveTextContent('系统授权代表企业统一连接');
    expect(screen.getByLabelText('钉钉授权主体清单')).toHaveTextContent('钉钉知识库 · 系统授权');
    expect(screen.getByLabelText('钉钉授权主体清单')).toHaveTextContent('企业 青锋科技');
    expect(screen.getByLabelText('钉钉授权主体清单')).toHaveTextContent('剩余 12 天');
    expect(screen.getByText('帮助截图自动化与数据归档策略')).toBeInTheDocument();
    expect(screen.getByText('AI Brain')).toBeInTheDocument();
    expect(screen.getByText('SMTP 邮件发送')).toBeInTheDocument();
    expect(screen.getAllByText('钉钉 MCP 连接').length).toBeGreaterThan(0);
    expect(screen.getByText('URL key 已过期')).toBeInTheDocument();
    expect(screen.getByText('smtp.example.com')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '处理告警 钉钉 MCP 连接' }));
    expect(await screen.findByText('处理告警')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('关闭'));
    fireEvent.change(screen.getByLabelText('负责人'), { target: { value: 'lzk' } });
    fireEvent.change(screen.getByLabelText('关闭原因'), { target: { value: '授权已更新' } });
    fireEvent.change(screen.getByLabelText('复盘记录'), { target: { value: '补充到期提醒' } });
    fireEvent.click(screen.getByRole('button', { name: '保存处理' }));
    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          body: expect.objectContaining({
            close_reason: '授权已更新',
            owner: 'lzk',
            postmortem: '补充到期提醒',
            status: 'closed',
          }),
          method: 'PATCH',
          path: '/api/system/alerts/check%3Adingtalk_mcp',
        }),
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增订阅' }));
    expect(await screen.findByText('新增告警订阅')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('通知目标'), { target: { value: 'ops@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: '保存订阅' }));
    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          body: expect.objectContaining({
            channel: 'email',
            severity_min: 'medium',
            target: 'ops@example.com',
          }),
          method: 'POST',
          path: '/api/system/alerts/subscriptions',
        }),
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增规则' }));
    expect(await screen.findByText('新增告警规则')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('规则名称'), { target: { value: '模型网关告警' } });
    fireEvent.change(screen.getByLabelText('组件'), { target: { value: 'model_gateway' } });
    fireEvent.change(screen.getByLabelText('条件 JSON'), { target: { value: '{"status":"warning"}' } });
    fireEvent.click(screen.getByRole('button', { name: '保存规则' }));
    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          body: expect.objectContaining({
            component: 'model_gateway',
            condition_json: { status: 'warning' },
            name: '模型网关告警',
          }),
          method: 'POST',
          path: '/api/system/alerts/rules',
        }),
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: /停用规则 钉钉 MCP 失败规则/ }));
    await waitFor(() =>
      expect(calls).toContainEqual(
        expect.objectContaining({
          body: { enabled: false },
          method: 'PATCH',
          path: '/api/system/alerts/rules/rule_health',
        }),
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: /刷新/ }));

    await waitFor(() => expect(calls.filter((call) => call.path === '/api/system/health')).toHaveLength(6));
  });
});
