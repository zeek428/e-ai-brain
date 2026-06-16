import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
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
  saveCurrentUser,
} from '../src/services/aiBrain';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.history.pushState({}, '', '/');
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

  it('shows admin role quick tasks and fills the run-failure prompt', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    saveCurrentUser({
      display_name: 'AI Brain Admin',
      id: 'user_admin',
      roles: ['admin'],
      username: 'admin@example.com',
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    expect(screen.getByText('角色快捷任务')).toBeInTheDocument();
    expect(screen.getByText('管理员快捷任务')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '插件连接' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'AI能力' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '定时作业' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '运行失败' }));

    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue(
      '请诊断最近失败的定时作业运行，按数据连接、AI处理、结果动作给出原因和修复建议。',
    );
    expect(fetchMock.mock.calls.map(([path]) => path)).toEqual(['/api/assistant/conversations']);
  });

  it('shows engineering quick tasks for rd_owner users', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-rd' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-rd');
    saveCurrentUser({
      display_name: '研发负责人',
      id: 'user_rd',
      roles: ['rd_owner'],
      username: 'rd@example.com',
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    expect(screen.getByText('角色快捷任务')).toBeInTheDocument();
    expect(screen.getByText('研发快捷任务')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '任务阻塞' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '代码巡检' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '缺陷修复' })).toBeInTheDocument();
    expect(screen.queryByText('管理员快捷任务')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '代码巡检' }));

    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue(
      '请帮我生成或检查代码巡检任务草案，并说明数据连接、AI处理和结果动作依赖。',
    );
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
    expect(screen.getAllByText('需求').length).toBeGreaterThan(0);
  });

  it('groups @ reference candidates with metadata and supports keyboard selection', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (String(input).startsWith('/api/assistant/reference-candidates?')) {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  id: 'knowledge_weekly_feedback',
                  permission_label: '可引用',
                  source_module: '知识库',
                  title: '每周反馈洞察手册',
                  type: 'knowledge_document',
                  updated_at: '2026-06-16T08:30:00+08:00',
                  url: '/knowledge/documents?document_id=knowledge_weekly_feedback',
                },
                {
                  id: 'scheduled_job_feedback_weekly',
                  permission_label: '管理员可引用',
                  source_module: '任务中心',
                  title: '提取每周用户反馈有价值信息',
                  type: 'scheduled_job',
                  updated_at: '2026-06-15T18:00:00+08:00',
                  url: '/tasks/scheduled-jobs?job_id=scheduled_job_feedback_weekly',
                },
                {
                  id: 'ai_skill_feedback_summary',
                  permission_label: '管理员可引用',
                  source_module: 'AI能力配置',
                  title: '反馈洞察 Skill',
                  type: 'ai_skill',
                  updated_at: '2026-06-14T09:00:00+08:00',
                  url: '/tasks/ai-capabilities?skill_id=ai_skill_feedback_summary',
                },
              ],
              total: 3,
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

    const assistantInput = screen.getByLabelText('发送给 AI 助手');
    fireEvent.change(assistantInput, {
      target: { value: '@' },
    });

    expect((await screen.findAllByText('知识文档')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('定时作业').length).toBeGreaterThan(0);
    expect(screen.getAllByText('AI能力').length).toBeGreaterThan(0);
    expect(screen.getByText('知识库 · 可引用 · 2026-06-16')).toBeInTheDocument();
    expect(screen.getByText('任务中心 · 管理员可引用 · 2026-06-15')).toBeInTheDocument();

    fireEvent.keyDown(assistantInput, { key: 'ArrowDown' });
    fireEvent.keyDown(assistantInput, { key: 'Enter' });

    expect(screen.getByText('提取每周用户反馈有价值信息')).toBeInTheDocument();
    expect(screen.getAllByText('定时作业').length).toBeGreaterThan(0);
  });

  it('sends @ scheduled job run-once commands with the active candidate reference', async () => {
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
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  id: 'scheduled_job_feedback_weekly',
                  permission_label: '管理员可引用',
                  source_module: '任务中心',
                  title: '提取每周用户反馈有价值信息',
                  type: 'scheduled_job',
                  updated_at: '2026-06-15T18:00:00+08:00',
                  url: '/tasks/scheduled-jobs?job_id=scheduled_job_feedback_weekly',
                },
              ],
              total: 1,
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      if (input === '/api/assistant/chat') {
        chatRequestBody = JSON.parse(String(init?.body));
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_run_once',
              latency_ms: 12,
              message: {
                content: '已执行「提取每周用户反馈有价值信息」一次，运行记录 scheduled_job_run_001 已成功完成。',
                id: 'assistant_message_run_once',
                references: [
                  {
                    id: 'scheduled_job_feedback_weekly',
                    title: '提取每周用户反馈有价值信息',
                    type: 'scheduled_job',
                    url: '/tasks/scheduled-jobs?job_id=scheduled_job_feedback_weekly',
                  },
                  {
                    id: 'scheduled_job_run_001',
                    title: '提取每周用户反馈有价值信息 / succeeded',
                    type: 'scheduled_job_run',
                    url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_001',
                  },
                ],
                role: 'assistant',
                suggestions: [],
                tool_results: [
                  {
                    intent: 'scheduled_job_run_once',
                    items: [],
                    summary: { run_id: 'scheduled_job_run_001', status: 'succeeded' },
                    tool: 'assistant.scheduled_job_run',
                  },
                ],
              },
              model: 'assistant-deterministic',
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

    const assistantInput = screen.getByLabelText('发送给 AI 助手');
    fireEvent.change(assistantInput, {
      target: { value: '@提取每周用户反馈有价值信息 执行一次' },
    });

    await screen.findByRole('button', { name: /提取每周用户反馈有价值信息/ });
    fireEvent.keyDown(assistantInput, { key: 'Enter' });

    expect(await screen.findByText(/已执行「提取每周用户反馈有价值信息」一次/)).toBeInTheDocument();
    expect(chatRequestBody).toMatchObject({
      message: '@提取每周用户反馈有价值信息 执行一次',
      references: [
        {
          id: 'scheduled_job_feedback_weekly',
          type: 'scheduled_job',
        },
      ],
    });
  });

  it('keeps grouped @ reference hover selection aligned with the original candidate', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (String(input).startsWith('/api/assistant/reference-candidates?')) {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  id: 'knowledge_weekly_feedback',
                  permission_label: '可引用',
                  source_module: '知识库',
                  title: '每周反馈洞察手册',
                  type: 'knowledge_document',
                  updated_at: '2026-06-16T08:30:00+08:00',
                  url: '/knowledge/documents?document_id=knowledge_weekly_feedback',
                },
                {
                  id: 'scheduled_job_feedback_weekly',
                  permission_label: '管理员可引用',
                  source_module: '任务中心',
                  title: '提取每周用户反馈有价值信息',
                  type: 'scheduled_job',
                  updated_at: '2026-06-15T18:00:00+08:00',
                  url: '/tasks/scheduled-jobs?job_id=scheduled_job_feedback_weekly',
                },
                {
                  id: 'ai_skill_feedback_summary',
                  permission_label: '管理员可引用',
                  source_module: 'AI能力配置',
                  title: '反馈洞察 Skill',
                  type: 'ai_skill',
                  updated_at: '2026-06-14T09:00:00+08:00',
                  url: '/tasks/ai-capabilities?skill_id=ai_skill_feedback_summary',
                },
                {
                  id: 'scheduled_job_feedback_review',
                  permission_label: '管理员可引用',
                  source_module: '任务中心',
                  title: '每周反馈趋势复盘',
                  type: 'scheduled_job',
                  updated_at: '2026-06-13T18:00:00+08:00',
                  url: '/tasks/scheduled-jobs?job_id=scheduled_job_feedback_review',
                },
              ],
              total: 4,
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

    const assistantInput = screen.getByLabelText('发送给 AI 助手');
    fireEvent.change(assistantInput, {
      target: { value: '@' },
    });

    const secondScheduledJob = await screen.findByRole('button', { name: /每周反馈趋势复盘/ });
    fireEvent.mouseEnter(secondScheduledJob);
    fireEvent.keyDown(assistantInput, { key: 'Enter' });

    const selectedReferenceList = (await screen.findByText('本次上下文'))
      .closest('.assistant-selected-reference-list');
    expect(selectedReferenceList).not.toBeNull();
    const selectedReferenceTags = selectedReferenceList?.querySelector('.assistant-selected-reference-tags');
    expect(selectedReferenceTags).not.toBeNull();
    expect(within(selectedReferenceTags as HTMLElement).getByText('每周反馈趋势复盘')).toBeInTheDocument();
    expect(within(selectedReferenceTags as HTMLElement).queryByText('反馈洞察 Skill')).not.toBeInTheDocument();
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

  it('preselects scheduled job run references from route query parameters', async () => {
    let chatRequestBody: Record<string, unknown> | undefined;
    window.history.pushState(
      {},
      '',
      '/assistant?reference_type=scheduled_job_run&reference_id=scheduled_job_run_feedback_failed&prompt=%E4%B8%BA%E4%BB%80%E4%B9%88%E8%BF%99%E6%AC%A1%E4%BB%BB%E5%8A%A1%E5%A4%B1%E8%B4%A5%EF%BC%9F',
    );
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
        expect(params.get('query')).toBe('scheduled_job_run_feedback_failed');
        expect(params.get('type')).toBe('scheduled_job_run');
        expect(params.get('limit')).toBe('1');
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
              conversation_id: 'conversation_run_route_reference',
              latency_ms: 156,
              message: {
                content: '这次失败发生在结果动作写入阶段。',
                id: 'assistant_message_run_route_reference',
                references: [
                  {
                    id: 'scheduled_job_run_feedback_failed',
                    title: '每周反馈洞察定时作业 / failed',
                    type: 'scheduled_job_run',
                    url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed',
                  },
                ],
                role: 'assistant',
                tool_results: [],
              },
              model: 'assistant-deterministic',
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

    expect(await screen.findByText('每周反馈洞察定时作业 / failed')).toBeInTheDocument();
    expect(screen.getByText('本次上下文')).toBeInTheDocument();
    expect(screen.getByText('运行记录')).toBeInTheDocument();
    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue('为什么这次任务失败？');

    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('这次失败发生在结果动作写入阶段。')).toBeInTheDocument();
    expect(chatRequestBody).toMatchObject({
      message: '为什么这次任务失败？',
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

    expect(await screen.findByText('已应用')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '打开定时作业' })).toHaveAttribute(
      'href',
      '/tasks/scheduled-jobs?job_id=scheduled_job_001',
    );
    fireEvent.click(screen.getByRole('button', { name: '重新生成' }));
    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue('重新生成「创建仪表盘刷新定时任务」草案');
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
      '/api/assistant/action-drafts/assistant_action_draft_001/confirm',
      'POST',
    ]);
  });

  it('shows assistant action draft precheck issues before confirmation', async () => {
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
              conversation_id: 'conversation_draft_precheck',
              latency_ms: 128,
              message: {
                content: '我已生成一个需要补齐字段的服务端草案。',
                id: 'assistant_message_draft_precheck',
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'scheduled_job_draft',
                    items: [
                      {
                        action: 'create_scheduled_job',
                        draft_id: 'assistant_action_draft_precheck',
                        payload: {
                          execution_mode: 'deterministic',
                          job_type: 'user_feedback_insight_extract',
                          name: '缺少配置的反馈洞察作业',
                          schedule_type: 'cron',
                        },
                        preview: {
                          diffs: [
                            {
                              change_type: 'create',
                              current: null,
                              field: 'name',
                              label: '名称',
                              proposed: '缺少配置的反馈洞察作业',
                            },
                            {
                              change_type: 'create',
                              current: null,
                              field: 'schedule_type',
                              label: '调度类型',
                              proposed: 'cron',
                            },
                          ],
                          target: {
                            operation: 'create',
                            resource_id: null,
                            resource_type: 'scheduled_job',
                          },
                          validation: {
                            issues: [
                              {
                                field: 'cron_expression',
                                message: 'cron_expression is required',
                                severity: 'error',
                              },
                              {
                                field: 'plugin_action_id',
                                message: 'user_feedback_insight_extract requires plugin_action_id',
                                severity: 'error',
                              },
                            ],
                            status: 'blocked',
                          },
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        status: 'pending',
                        title: '创建反馈洞察定时任务',
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
      if (input === '/api/assistant/action-drafts/assistant_action_draft_precheck/confirm') {
        throw new Error('Blocked drafts should not be confirmed from the card');
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '帮我创建缺字段的反馈洞察草案' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('应用前预检')).toBeInTheDocument();
    expect(screen.getByText('阻塞')).toBeInTheDocument();
    expect(screen.getByText('名称')).toBeInTheDocument();
    expect(screen.getByText('- -> 缺少配置的反馈洞察作业')).toBeInTheDocument();
    expect(screen.getByText('cron_expression is required')).toBeInTheDocument();
    expect(screen.getByText('user_feedback_insight_extract requires plugin_action_id')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /确认创建/ })).toBeDisabled();
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

  it('renders a task creation guide and lets users choose a draft-first path', async () => {
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
              conversation_id: 'conversation_task_guide',
              latency_ms: 8,
              message: {
                content: '你想新增哪类任务？我会先生成可确认的向导草案。',
                id: 'assistant_message_task_guide',
                references: [],
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'task_creation_guide',
                    items: [
                      {
                        dependencies: ['GitHub/GitLab 连接', '代码巡检动作'],
                        description: '按仓库、分支、AI处理和结果动作生成定时作业草案。',
                        draft_action: 'create_scheduled_job',
                        prompt: '帮我配置代码巡检定时作业草案',
                        title: '代码巡检',
                        type: 'code_inspection',
                        wizard_steps: ['数据来源', 'AI处理', '结果动作', '调度策略', '确认执行'],
                      },
                      {
                        dependencies: ['用户反馈数据连接', '反馈洞察动作'],
                        description: '抽取每周用户反馈并写入洞察结果。',
                        draft_action: 'create_scheduled_job',
                        prompt: '帮我配置每周用户反馈洞察定时作业草案',
                        title: '反馈洞察',
                        type: 'feedback_insight',
                        wizard_steps: ['数据来源', 'AI处理', '结果动作', '调度策略', '确认执行'],
                      },
                    ],
                    summary: {
                      draft_first: true,
                      option_count: 2,
                      wizard_steps: ['数据来源', 'AI处理', '结果动作', '调度策略', '确认执行'],
                    },
                    tool: 'assistant.task_creation_guide',
                  },
                ],
              },
              model: 'assistant-deterministic',
              suggestions: ['新增研发任务', '配置代码巡检定时作业'],
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

    const assistantInput = screen.getByLabelText('发送给 AI 助手');
    fireEvent.change(assistantInput, { target: { value: '我要新增任务' } });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('任务类型向导')).toBeInTheDocument();
    expect(screen.getByText('数据来源 -> AI处理 -> 结果动作 -> 调度策略 -> 确认执行')).toBeInTheDocument();
    expect(screen.getByText('代码巡检')).toBeInTheDocument();
    expect(screen.getByText('依赖：GitHub/GitLab 连接、代码巡检动作')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '选择代码巡检' }));
    expect(assistantInput).toHaveValue('帮我配置代码巡检定时作业草案');
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
