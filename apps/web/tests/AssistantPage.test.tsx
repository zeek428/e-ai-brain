import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import AssistantPage from '../src/pages/Assistant';
import {
  ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
  ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
  ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
  chatWithAssistant,
  fetchAssistantConversationMessages,
  fetchAssistantConversations,
} from '../src/services/aiBrain';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  window.sessionStorage.clear();
  void message.destroy();
  notification.destroy();
  Modal.destroyAll();
});

function resultWriteTargetsResponse() {
  return new Response(
    JSON.stringify({
      data: {
        items: [
          {
            code: 'code_inspection_reports',
            default_result_mapping: { write_target: 'code_inspection_reports' },
            form_label: '代码巡检报告',
            label: '代码巡检报告',
            mapping_fields: [],
          },
          {
            code: 'email_notifications',
            default_result_mapping: { write_target: 'email_notifications' },
            form_label: '邮件通知记录',
            label: '邮件通知记录',
            mapping_fields: [],
          },
        ],
        total: 2,
      },
    }),
    { headers: { 'Content-Type': 'application/json' }, status: 200 },
  );
}

describe('AssistantPage', () => {
  it('renders an AI assistant chat surface that can answer AI Brain progress questions', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        expect(init?.method ?? 'GET').toBe('GET');
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (input === '/api/assistant/chat') {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toMatchObject({
          message: 'AI Brain 项目现在开发到哪里了？',
        });
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_api',
              latency_ms: 358,
              message: {
                content: 'AI Brain 已完成 GitHub PR Review 支持，当前正在开发 AI 助手聊天界面。',
                id: 'assistant_message_api',
                references: [
                  {
                    id: 'requirement_084',
                    title: 'AI 助手历史记录迭代',
                    type: 'requirement',
                    url: '/delivery/requirements?requirement_id=requirement_084',
                  },
                  {
                    id: 'task_api',
                    title: 'AI 助手前端任务',
                    type: 'ai_task',
                    url: '/delivery/rd-tasks?task_id=task_api',
                  },
                ],
                role: 'assistant',
              },
              model: 'codex-auto-review',
              suggestions: ['查看任务中心', '检查 GitHub PR', '打开模型网关'],
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);

    render(<AssistantPage />);

    expect(screen.getAllByText('AI 助手').length).toBeGreaterThan(0);
    expect(screen.getAllByText('项目进展').length).toBeGreaterThan(0);
    expect(screen.getAllByText('阻塞与待确认').length).toBeGreaterThan(0);
    expect(screen.getAllByText('模型网关').length).toBeGreaterThan(0);
    const assistantInput = screen.getByLabelText('发送给 AI 助手');
    expect(assistantInput).toHaveAttribute('rows', '3');
    fireEvent.change(assistantInput, {
      target: { value: 'AI Brain 项目现在开发到哪里了？' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(
      await screen.findByText('AI Brain 已完成 GitHub PR Review 支持，当前正在开发 AI 助手聊天界面。'),
    ).toBeInTheDocument();
    expect(screen.getByText('查看任务中心')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /AI 助手历史记录迭代/ })).toHaveAttribute(
      'href',
      '/delivery/requirements?requirement_id=requirement_084',
    );
    expect(screen.getByRole('link', { name: /AI 助手前端任务/ })).toHaveAttribute(
      'href',
      '/delivery/rd-tasks?task_id=task_api',
    );
    expect(screen.getByText('codex-auto-review')).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toEqual([
      ['/api/assistant/conversations', 'GET'],
      ['/api/assistant/chat', 'POST'],
      ['/api/assistant/conversations', 'GET'],
    ]);
    expect(
      consoleErrorSpy.mock.calls.some((call) => String(call[0]).includes('NaN') && String(call[0]).includes('height')),
    ).toBe(false);
  });

  it('selects knowledge references with @ candidates and sends them to chat', async () => {
    let chatRequestBody: Record<string, unknown> | undefined;
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (String(input).startsWith('/api/assistant/reference-candidates?')) {
        expect(init?.method ?? 'GET').toBe('GET');
        const params = new URLSearchParams(String(input).split('?')[1]);
        expect(params.get('query')).toBe('支付');
        expect(params.get('type')).toBeNull();
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  chunk_count: 1,
                  id: 'knowledge_payment_runbook',
                  index_status: 'indexed',
                  title: '支付页超时排障手册',
                  type: 'knowledge_document',
                  url: '/knowledge/documents?document_id=knowledge_payment_runbook',
                },
              ],
              total: 1,
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      if (input === '/api/assistant/chat') {
        expect(init?.method).toBe('POST');
        chatRequestBody = JSON.parse(String(init?.body)) as Record<string, unknown>;
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_reference',
              latency_ms: 218,
              message: {
                content: '支付页应先检查网关超时和回调幂等键。',
                id: 'assistant_message_reference',
                references: [
                  {
                    id: 'knowledge_payment_runbook',
                    title: '支付页超时排障手册',
                    type: 'knowledge_document',
                    url: '/knowledge/documents?document_id=knowledge_payment_runbook',
                  },
                ],
                role: 'assistant',
              },
              model: 'codex-auto-review',
              suggestions: [],
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '基于 @支付 分析提交无响应' },
    });
    fireEvent.click(await screen.findByRole('button', { name: /支付页超时排障手册/ }));
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('支付页应先检查网关超时和回调幂等键。')).toBeInTheDocument();
    expect(chatRequestBody).toMatchObject({
      message: '基于 @支付 分析提交无响应',
      references: [{ id: 'knowledge_payment_runbook', type: 'knowledge_document' }],
    });
  });

  it('opens default reference candidates when the user types a bare @', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (String(input).startsWith('/api/assistant/reference-candidates?')) {
        expect(init?.method ?? 'GET').toBe('GET');
        const params = new URLSearchParams(String(input).split('?')[1]);
        expect(params.get('query')).toBe('');
        expect(params.get('type')).toBeNull();
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  id: 'requirement_assistant_iteration',
                  title: 'AI 助手历史记录迭代',
                  type: 'requirement',
                  url: '/delivery/requirements?requirement_id=requirement_assistant_iteration',
                },
              ],
              total: 1,
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '@' },
    });

    expect(await screen.findByRole('button', { name: /AI 助手历史记录迭代/ })).toBeInTheDocument();
    expect(screen.getByText('需求')).toBeInTheDocument();
  });

  it('selects scheduled job run references with @ candidates and sends them to chat', async () => {
    let chatRequestBody: Record<string, unknown> | undefined;
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (String(input).startsWith('/api/assistant/reference-candidates?')) {
        expect(init?.method ?? 'GET').toBe('GET');
        const params = new URLSearchParams(String(input).split('?')[1]);
        expect(params.get('query')).toBe('反馈');
        expect(params.get('type')).toBeNull();
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  id: 'scheduled_job_run_feedback_failed',
                  title: '每周反馈洞察定时作业 / failed',
                  type: 'scheduled_job_run',
                  url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed',
                },
              ],
              total: 1,
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      if (input === '/api/assistant/chat') {
        expect(init?.method).toBe('POST');
        chatRequestBody = JSON.parse(String(init?.body)) as Record<string, unknown>;
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_run_reference',
              latency_ms: 181,
              message: {
                content: '这次失败发生在结果动作写入阶段。',
                id: 'assistant_message_run_reference',
                references: [
                  {
                    id: 'scheduled_job_run_feedback_failed',
                    title: '每周反馈洞察定时作业 / failed',
                    type: 'scheduled_job_run',
                    url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed',
                  },
                ],
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'scheduled_job_diagnostic',
                    items: [],
                    summary: { failed_count: 1, run_count: 1 },
                    tool: 'assistant.scheduled_job_diagnostic',
                  },
                ],
              },
              model: 'codex-auto-review',
              suggestions: [],
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '为什么 @反馈 这次失败？' },
    });
    fireEvent.click(await screen.findByRole('button', { name: /每周反馈洞察定时作业/ }));
    expect(screen.getByText('运行记录')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('这次失败发生在结果动作写入阶段。')).toBeInTheDocument();
    expect(chatRequestBody).toMatchObject({
      message: '为什么 @反馈 这次失败？',
      references: [{ id: 'scheduled_job_run_feedback_failed', type: 'scheduled_job_run' }],
    });
  });

  it('loads current-user AI assistant conversations and opens historical messages', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  id: 'conversation_api',
                  last_message_at: '2026-06-03T09:00:00+00:00',
                  message_count: 2,
                  title: 'AI Brain 现在开发到哪里了？',
                  updated_at: '2026-06-03T09:00:00+00:00',
                },
              ],
              total: 1,
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      if (input === '/api/assistant/conversations/conversation_api/messages') {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  content: 'AI Brain 现在开发到哪里了？',
                  id: 'assistant_message_user',
                  role: 'user',
                },
                {
                  content: '当前已经支持按用户保存聊天历史。',
                  id: 'assistant_message_reply',
                  model: 'codex-auto-review',
                  references: [
                    {
                      id: 'conversation_requirement',
                      title: '聊天历史需求',
                      type: 'requirement',
                      url: '/delivery/requirements?requirement_id=conversation_requirement',
                    },
                  ],
                  role: 'assistant',
                  suggestions: ['查看任务中心'],
                },
              ],
              total: 2,
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    fireEvent.click(await screen.findByRole('button', { name: /AI Brain 现在开发到哪里了？/ }));

    expect(await screen.findByText('当前已经支持按用户保存聊天历史。')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /聊天历史需求/ })).toHaveAttribute(
      'href',
      '/delivery/requirements?requirement_id=conversation_requirement',
    );
    expect(screen.getAllByText('AI Brain 现在开发到哪里了？').length).toBeGreaterThan(0);
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toEqual([
      ['/api/assistant/conversations', 'GET'],
      ['/api/assistant/conversations/conversation_api/messages', 'GET'],
    ]);
  });

  it('renders assistant action drafts as configuration cards', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (input === '/api/assistant/chat') {
        expect(init?.method).toBe('POST');
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_draft',
              latency_ms: 198,
              message: {
                content: '我已生成一个待确认的代码巡检定时作业草案。',
                id: 'assistant_message_draft',
                references: [
                  {
                    id: 'assistant_draft_code_repository_inspection',
                    title: '代码仓库质量安全规范巡检',
                    type: 'assistant_action_draft',
                    url: '/assistant?draft_id=assistant_draft_code_repository_inspection',
                  },
                ],
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'scheduled_job_draft',
                    items: [
                      {
                        action: 'create_scheduled_job',
                        draft_id: 'assistant_draft_code_repository_inspection',
                        payload: {
                          agent_id: 'agent_code_inspection',
                          cron_expression: '0 2 * * MON',
                          execution_mode: 'ai_generated',
                          job_type: 'code_repository_inspection',
                          model_gateway_config_id: 'model_gateway_code',
                          plugin_action_id: 'plugin_action_github_scan',
                          plugin_connection_id: 'connection_github_prod',
                          skill_ids: ['skill_code_inspection'],
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        title: '代码仓库质量安全规范巡检',
                      },
                    ],
                    summary: {
                      draft_count: 1,
                      requires_confirmation: true,
                      target: 'scheduled_jobs',
                    },
                    tool: 'assistant.action_draft',
                  },
                ],
              },
              model: 'codex-auto-review',
              suggestions: [],
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '帮我创建每周代码巡检定时作业' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('我已生成一个待确认的代码巡检定时作业草案。')).toBeInTheDocument();
    expect(screen.getByText('确认前不会写入作业定义')).toBeInTheDocument();
    expect(screen.getByText('作业类型')).toBeInTheDocument();
    expect(screen.getByText('code_repository_inspection')).toBeInTheDocument();
    expect(screen.getByText('执行模式')).toBeInTheDocument();
    expect(screen.getByText('ai_generated')).toBeInTheDocument();
    expect(screen.getByText('AI 模型')).toBeInTheDocument();
    expect(screen.getByText('model_gateway_code')).toBeInTheDocument();
    expect(screen.getByText('AI角色')).toBeInTheDocument();
    expect(screen.getByText('agent_code_inspection')).toBeInTheDocument();
    expect(screen.getByText('Skills')).toBeInTheDocument();
    expect(screen.getByText('skill_code_inspection')).toBeInTheDocument();
    expect(screen.getByText('connection_github_prod')).toBeInTheDocument();
    const applyDraftLink = screen.getByRole('link', { name: '应用到定时作业表单' });
    expect(applyDraftLink).toHaveAttribute(
      'href',
      '/tasks/scheduled-jobs',
    );
    fireEvent.mouseDown(applyDraftLink);
    expect(JSON.parse(window.sessionStorage.getItem(ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY) ?? '{}')).toEqual({
      draftId: 'assistant_draft_code_repository_inspection',
      payload: {
        agent_id: 'agent_code_inspection',
        cron_expression: '0 2 * * MON',
        execution_mode: 'ai_generated',
        job_type: 'code_repository_inspection',
        model_gateway_config_id: 'model_gateway_code',
        plugin_action_id: 'plugin_action_github_scan',
        plugin_connection_id: 'connection_github_prod',
        skill_ids: ['skill_code_inspection'],
      },
      title: '代码仓库质量安全规范巡检',
    });
    expect(screen.getByRole('link', { name: '查看草案' })).toHaveAttribute(
      'href',
      '/assistant?draft_id=assistant_draft_code_repository_inspection',
    );
  });

  it('confirms server-side assistant action drafts from the draft card', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (input === '/api/assistant/chat') {
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_server_draft',
              latency_ms: 128,
              message: {
                content: '我已生成一个服务端草案。',
                id: 'assistant_message_server_draft',
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'scheduled_job_draft',
                    items: [
                      {
                        action: 'create_scheduled_job',
                        client_draft_id: 'assistant_draft_weekly_feedback_insight',
                        draft_id: 'assistant_action_draft_001',
                        payload: {
                          execution_mode: 'deterministic',
                          job_type: 'dashboard_snapshot_refresh',
                          name: 'AI 助手草案仪表盘刷新',
                          schedule_type: 'manual',
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        server_draft_id: 'assistant_action_draft_001',
                        status: 'pending',
                        title: '创建仪表盘刷新定时任务',
                      },
                    ],
                    summary: { draft_count: 1, requires_confirmation: true },
                    tool: 'assistant.action_draft',
                  },
                ],
              },
              model: 'codex-auto-review',
              suggestions: [],
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      if (input === '/api/assistant/action-drafts/assistant_action_draft_001/confirm') {
        expect(init?.method).toBe('POST');
        return new Response(
          JSON.stringify({
            data: {
              draft: {
                action: 'create_scheduled_job',
                id: 'assistant_action_draft_001',
                payload: {},
                status: 'confirmed',
                title: '创建仪表盘刷新定时任务',
              },
              run: {
                action: 'create_scheduled_job',
                draft_id: 'assistant_action_draft_001',
                id: 'assistant_action_run_001',
                result_id: 'scheduled_job_001',
                result_type: 'scheduled_job',
                status: 'succeeded',
              },
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '帮我创建仪表盘刷新草案' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    fireEvent.click(await screen.findByRole('button', { name: /确认创建/ }));

    expect(await screen.findByText('已确认')).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
      '/api/assistant/action-drafts/assistant_action_draft_001/confirm',
      'POST',
    ]);
  });

  it('renders assistant plugin action drafts as configuration cards', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (input === '/api/system/result-write-targets') {
        expect(init?.method ?? 'GET').toBe('GET');
        return resultWriteTargetsResponse();
      }
      if (input === '/api/assistant/chat') {
        expect(init?.method).toBe('POST');
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_plugin_action_draft',
              latency_ms: 168,
              message: {
                content: '我已生成一个待确认的 GitHub 代码巡检动作草案。',
                id: 'assistant_message_plugin_action_draft',
                references: [
                  {
                    id: 'assistant_draft_github_plugin_action',
                    title: 'GitHub 代码巡检动作',
                    type: 'assistant_action_draft',
                    url: '/assistant?draft_id=assistant_draft_github_plugin_action',
                  },
                ],
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'plugin_action_draft',
                    items: [
                      {
                        action: 'create_plugin_action',
                        draft_id: 'assistant_draft_github_plugin_action',
                        payload: {
                          action_type: 'http_request',
                          code: 'scan_github_code_inspection',
                          connection_id: 'connection_github_prod',
                          name: 'GitHub 代码巡检',
                          plugin_id: 'plugin_standard_github',
                          request_config: {
                            method: 'GET',
                            path: '/repos/{{owner}}/{{repo}}/code-scanning/alerts',
                            query: { per_page: 100, state: 'open' },
                          },
                          result_mapping: { write_target: 'code_inspection_reports' },
                          status: 'active',
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        title: 'GitHub 代码巡检动作',
                      },
                    ],
                    summary: {
                      draft_count: 1,
                      requires_confirmation: true,
                      target: 'plugin_actions',
                    },
                    tool: 'assistant.action_draft',
                  },
                ],
              },
              model: 'codex-auto-review',
              suggestions: [],
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '帮我新增 GitHub 代码巡检插件动作' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('我已生成一个待确认的 GitHub 代码巡检动作草案。')).toBeInTheDocument();
    expect(screen.getByText('确认前不会写入插件动作')).toBeInTheDocument();
    expect(screen.getByText('动作类型')).toBeInTheDocument();
    expect(screen.getByText('http_request')).toBeInTheDocument();
    expect(screen.getByText('scan_github_code_inspection')).toBeInTheDocument();
    expect(screen.getByText('/repos/{{owner}}/{{repo}}/code-scanning/alerts')).toBeInTheDocument();
    expect(await screen.findByText('代码巡检报告')).toBeInTheDocument();
    const applyDraftLink = screen.getByRole('link', { name: '应用到插件动作表单' });
    expect(applyDraftLink).toHaveAttribute('href', '/tasks/plugins');
    fireEvent.mouseDown(applyDraftLink);
    expect(JSON.parse(window.sessionStorage.getItem(ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY) ?? '{}')).toEqual({
      draftId: 'assistant_draft_github_plugin_action',
      payload: {
        action_type: 'http_request',
        code: 'scan_github_code_inspection',
        connection_id: 'connection_github_prod',
        name: 'GitHub 代码巡检',
        plugin_id: 'plugin_standard_github',
        request_config: {
          method: 'GET',
          path: '/repos/{{owner}}/{{repo}}/code-scanning/alerts',
          query: { per_page: 100, state: 'open' },
        },
        result_mapping: { write_target: 'code_inspection_reports' },
        status: 'active',
      },
      title: 'GitHub 代码巡检动作',
    });
  });

  it('renders assistant email action drafts with the notification write target label', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (input === '/api/system/result-write-targets') {
        expect(init?.method ?? 'GET').toBe('GET');
        return resultWriteTargetsResponse();
      }
      if (input === '/api/assistant/chat') {
        expect(init?.method).toBe('POST');
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_email_action_draft',
              latency_ms: 141,
              message: {
                content: '我已生成一个待确认的邮箱通知动作草案。',
                id: 'assistant_message_email_action_draft',
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'plugin_action_draft',
                    items: [
                      {
                        action: 'create_plugin_action',
                        draft_id: 'assistant_draft_email_plugin_action',
                        payload: {
                          action_type: 'http_request',
                          code: 'send_email_notification',
                          connection_id: 'connection_email_prod',
                          name: '发送邮件通知',
                          plugin_id: 'plugin_standard_email',
                          request_config: {
                            headers: { 'Content-Type': 'application/json' },
                            method: 'POST',
                            path: '/messages/send',
                            query: {
                              body_template: '{{result_summary}}',
                              subject_template: '{{subject_template}}',
                              to: '{{default_to}}',
                            },
                          },
                          result_mapping: {
                            delivery_id_path: '$.message_id',
                            delivery_status_path: '$.status',
                            recipients_path: '$.recipients',
                            subject_path: '$.subject',
                            write_target: 'email_notifications',
                          },
                          status: 'active',
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        title: '邮箱通知发送动作',
                      },
                    ],
                    summary: {
                      draft_count: 1,
                      requires_confirmation: true,
                      target: 'plugin_actions',
                    },
                    tool: 'assistant.action_draft',
                  },
                ],
              },
              model: 'codex-auto-review',
              suggestions: [],
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '帮我新增邮箱通知动作' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('我已生成一个待确认的邮箱通知动作草案。')).toBeInTheDocument();
    expect(await screen.findByText('邮件通知记录')).toBeInTheDocument();
    expect(screen.getByText('/messages/send')).toBeInTheDocument();
    const applyDraftLink = screen.getByRole('link', { name: '应用到插件动作表单' });
    fireEvent.mouseDown(applyDraftLink);
    expect(JSON.parse(window.sessionStorage.getItem(ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY) ?? '{}')).toMatchObject({
      draftId: 'assistant_draft_email_plugin_action',
      payload: {
        result_mapping: {
          delivery_id_path: '$.message_id',
          delivery_status_path: '$.status',
          recipients_path: '$.recipients',
          subject_path: '$.subject',
          write_target: 'email_notifications',
        },
      },
      title: '邮箱通知发送动作',
    });
  });

  it('renders assistant plugin connection drafts as configuration cards', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (input === '/api/assistant/chat') {
        expect(init?.method).toBe('POST');
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_plugin_connection_draft',
              latency_ms: 171,
              message: {
                content: '我已生成一个待确认的 GitHub API 连接草案。',
                id: 'assistant_message_plugin_connection_draft',
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'plugin_connection_draft',
                    items: [
                      {
                        action: 'create_plugin_connection',
                        draft_id: 'assistant_draft_github_plugin_connection',
                        payload: {
                          auth_config: { token_ref: 'vault/github/token' },
                          auth_type: 'bearer',
                          endpoint_url: 'https://api.github.com',
                          environment: 'prod',
                          max_retries: 1,
                          name: '生产 GitHub 连接',
                          plugin_id: 'plugin_standard_github',
                          request_config: {
                            headers: {
                              Accept: 'application/vnd.github+json',
                              'X-GitHub-Api-Version': '2022-11-28',
                            },
                            query: { owner: '', repo: '' },
                          },
                          status: 'active',
                          timeout_seconds: 30,
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        title: 'GitHub API 连接',
                      },
                    ],
                    summary: {
                      draft_count: 1,
                      requires_confirmation: true,
                      target: 'plugin_connections',
                    },
                    tool: 'assistant.action_draft',
                  },
                ],
              },
              model: 'codex-auto-review',
              suggestions: [],
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '帮我新增 GitHub 插件连接' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('我已生成一个待确认的 GitHub API 连接草案。')).toBeInTheDocument();
    expect(screen.getByText('确认前不会写入插件连接')).toBeInTheDocument();
    expect(screen.getByText('Endpoint')).toBeInTheDocument();
    expect(screen.getByText('https://api.github.com')).toBeInTheDocument();
    expect(screen.getByText('认证')).toBeInTheDocument();
    expect(screen.getByText('bearer')).toBeInTheDocument();
    expect(screen.getByText('Headers')).toBeInTheDocument();
    expect(screen.getByText('{"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}')).toBeInTheDocument();
    const applyDraftLink = screen.getByRole('link', { name: '应用到插件连接表单' });
    expect(applyDraftLink).toHaveAttribute('href', '/tasks/plugins');
    fireEvent.mouseDown(applyDraftLink);
    expect(JSON.parse(window.sessionStorage.getItem(ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY) ?? '{}')).toEqual({
      draftId: 'assistant_draft_github_plugin_connection',
      payload: {
        auth_config: { token_ref: 'vault/github/token' },
        auth_type: 'bearer',
        endpoint_url: 'https://api.github.com',
        environment: 'prod',
        max_retries: 1,
        name: '生产 GitHub 连接',
        plugin_id: 'plugin_standard_github',
        request_config: {
          headers: {
            Accept: 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
          },
          query: { owner: '', repo: '' },
        },
        status: 'active',
        timeout_seconds: 30,
      },
      title: 'GitHub API 连接',
    });
  });

  it('renders assistant code inspection setup drafts as ordered configuration cards', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (input === '/api/system/result-write-targets') {
        expect(init?.method ?? 'GET').toBe('GET');
        return resultWriteTargetsResponse();
      }
      if (input === '/api/assistant/chat') {
        expect(init?.method).toBe('POST');
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_code_inspection_setup_draft',
              latency_ms: 183,
              message: {
                content: '我已生成 GitHub 代码巡检的一组待确认配置草案。',
                id: 'assistant_message_code_inspection_setup_draft',
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'code_inspection_setup_draft',
                    items: [
                      {
                        action: 'create_plugin_connection',
                        draft_id: 'assistant_draft_github_plugin_connection',
                        payload: {
                          auth_type: 'bearer',
                          endpoint_url: 'https://api.github.com',
                          environment: 'prod',
                          name: '生产 GitHub 连接',
                          plugin_id: 'plugin_standard_github',
                          request_config: {
                            headers: { Accept: 'application/vnd.github+json' },
                            query: { owner: '', repo: '' },
                          },
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        title: 'GitHub API 连接',
                      },
                      {
                        action: 'create_plugin_action',
                        draft_id: 'assistant_draft_github_plugin_action',
                        payload: {
                          action_type: 'http_request',
                          code: 'scan_github_code_inspection',
                          connection_id: null,
                          name: 'GitHub 代码巡检',
                          plugin_id: 'plugin_standard_github',
                          request_config: {
                            method: 'GET',
                            path: '/repos/{{owner}}/{{repo}}/code-scanning/alerts',
                          },
                          result_mapping: { write_target: 'code_inspection_reports' },
                          status: 'active',
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        title: 'GitHub 代码巡检动作',
                      },
                      {
                        action: 'create_scheduled_job',
                        draft_id: 'assistant_draft_code_repository_inspection',
                        payload: {
                          assistant_prerequisite_draft_ids: [
                            'assistant_draft_github_plugin_connection',
                            'assistant_draft_github_plugin_action',
                          ],
                          cron_expression: '0 2 * * MON',
                          execution_mode: 'deterministic',
                          job_type: 'code_repository_inspection',
                          plugin_action_id: null,
                          plugin_connection_id: null,
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        title: '代码仓库质量安全规范巡检',
                      },
                    ],
                    summary: {
                      draft_count: 3,
                      requires_confirmation: true,
                      target: 'code_inspection_setup',
                    },
                    tool: 'assistant.action_draft',
                  },
                ],
              },
              model: 'codex-auto-review',
              suggestions: [],
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '帮我配置 GitHub 代码巡检定时作业' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('我已生成 GitHub 代码巡检的一组待确认配置草案。')).toBeInTheDocument();
    expect(screen.getByText('确认前不会写入插件连接')).toBeInTheDocument();
    expect(screen.getByText('确认前不会写入插件动作')).toBeInTheDocument();
    expect(screen.getByText('确认前不会写入作业定义')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '应用到插件连接表单' })).toHaveAttribute('href', '/tasks/plugins');
    expect(screen.getByRole('link', { name: '应用到插件动作表单' })).toHaveAttribute('href', '/tasks/plugins');
    expect(screen.getByRole('link', { name: '应用到定时作业表单' })).toHaveAttribute('href', '/tasks/scheduled-jobs');
    expect(await screen.findByText('代码巡检报告')).toBeInTheDocument();
    expect(screen.getByText('前置草案')).toBeInTheDocument();
    expect(screen.getByText('assistant_draft_github_plugin_connection、assistant_draft_github_plugin_action')).toBeInTheDocument();
  });

  it('posts AI assistant chat messages to the assistant API', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(input).toBe('/api/assistant/chat');
      expect(init?.method).toBe('POST');
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      expect(JSON.parse(String(init?.body))).toEqual({
        context: { source: 'chat-page' },
        conversation_id: 'conversation_api',
        message: '系统进展如何？',
        product_id: 'product_118',
        references: [],
      });
      return new Response(
        JSON.stringify({
          data: {
            conversation_id: 'conversation_api',
            latency_ms: 241,
            message: {
              content: '当前已进入 AI 助手迭代开发。',
              id: 'assistant_message_api',
              references: [
                {
                  id: 'requirement_api',
                  title: 'AI 助手迭代需求',
                  type: 'requirement',
                  url: '/delivery/requirements?requirement_id=requirement_api',
                },
              ],
              role: 'assistant',
            },
            model: 'codex-auto-review',
            suggestions: ['查看任务中心'],
          },
        }),
        { headers: { 'Content-Type': 'application/json' }, status: 200 },
      );
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      chatWithAssistant({
        context: { source: 'chat-page' },
        conversationId: 'conversation_api',
        message: '系统进展如何？',
        productId: 'product_118',
      }),
    ).resolves.toMatchObject({
      conversationId: 'conversation_api',
      content: '当前已进入 AI 助手迭代开发。',
      model: 'codex-auto-review',
      references: [
        {
          id: 'requirement_api',
          title: 'AI 助手迭代需求',
          type: 'requirement',
          url: '/delivery/requirements?requirement_id=requirement_api',
        },
      ],
      suggestions: ['查看任务中心'],
    });
  });

  it('fetches current-user AI assistant conversation history', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        expect(init?.method ?? 'GET').toBe('GET');
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  created_at: '2026-06-03T09:00:00+00:00',
                  id: 'conversation_api',
                  last_message_at: '2026-06-03T09:01:00+00:00',
                  message_count: 2,
                  product_id: 'product_118',
                  title: '系统进展如何？',
                  updated_at: '2026-06-03T09:01:00+00:00',
                },
              ],
              total: 1,
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      if (input === '/api/assistant/conversations/conversation_api/messages') {
        expect(init?.method ?? 'GET').toBe('GET');
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  content: '系统进展如何？',
                  created_at: '2026-06-03T09:00:00+00:00',
                  id: 'assistant_message_user',
                  product_id: 'product_118',
                  role: 'user',
                },
                {
                  content: '当前已进入 AI 助手迭代开发。',
                  created_at: '2026-06-03T09:01:00+00:00',
                  id: 'assistant_message_api',
                  model: 'codex-auto-review',
                  references: [
                    {
                      id: 'task_api',
                      title: 'AI 助手任务',
                      type: 'ai_task',
                      url: '/delivery/rd-tasks?task_id=task_api',
                    },
                  ],
                  role: 'assistant',
                  suggestions: ['查看任务中心'],
                },
              ],
              total: 2,
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchAssistantConversations()).resolves.toEqual([
      {
        createdAt: '2026-06-03T09:00:00+00:00',
        id: 'conversation_api',
        lastMessageAt: '2026-06-03T09:01:00+00:00',
        messageCount: 2,
        productId: 'product_118',
        title: '系统进展如何？',
        updatedAt: '2026-06-03T09:01:00+00:00',
      },
    ]);
    await expect(fetchAssistantConversationMessages('conversation_api')).resolves.toEqual([
      {
        content: '系统进展如何？',
        createdAt: '2026-06-03T09:00:00+00:00',
        id: 'assistant_message_user',
        model: undefined,
        productId: 'product_118',
        references: [],
        role: 'user',
        suggestions: [],
        toolResults: [],
      },
      {
        content: '当前已进入 AI 助手迭代开发。',
        createdAt: '2026-06-03T09:01:00+00:00',
        id: 'assistant_message_api',
        model: 'codex-auto-review',
        productId: undefined,
        references: [
          {
            id: 'task_api',
            title: 'AI 助手任务',
            type: 'ai_task',
            url: '/delivery/rd-tasks?task_id=task_api',
          },
        ],
        role: 'assistant',
        suggestions: ['查看任务中心'],
        toolResults: [],
      },
    ]);
  });
});
