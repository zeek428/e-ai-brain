import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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
  it('shows a transparent current-context summary even before references are selected', async () => {
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
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    const currentContext = await screen.findByLabelText('本次上下文');
    expect(within(currentContext).getByText('本次上下文')).toBeInTheDocument();
    expect(within(currentContext).getByText('0 个显式引用')).toBeInTheDocument();
    expect(within(currentContext).getByText('0 个知识 chunk 注入模型')).toBeInTheDocument();
    expect(within(currentContext).getByText('未注入知识正文')).toBeInTheDocument();
    expect(within(currentContext).getByText('仅使用系统上下文和当前会话')).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path]) => path)).toEqual(['/api/assistant/conversations']);
  });

  it('loads assistant effectiveness metrics from the workbench sidebar', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (input === '/api/assistant/metrics') {
        return new Response(
          JSON.stringify({
            data: {
              drafts_by_action: [
                {
                  action: 'create_scheduled_job',
                  cancelled_count: 1,
                  confirmed_count: 2,
                  expired_count: 0,
                  failed_count: 0,
                  pending_count: 1,
                  total: 4,
                },
              ],
              summary: {
                draft_adoption_rate: 0.5,
                draft_cancelled_count: 1,
                draft_confirmed_count: 2,
                draft_expired_count: 0,
                draft_failed_count: 0,
                draft_pending_count: 1,
                draft_total: 4,
                draft_user_modified_count: 1,
                draft_user_modified_rate: 0.25,
                failed_run_repaired_count: 2,
                failed_run_repair_rate: 1,
                failed_run_total: 2,
                knowledge_reference_count: 6,
                knowledge_reference_hit_count: 3,
                knowledge_reference_hit_rate: 0.6,
                knowledge_reference_request_count: 5,
                reference_usage_rate: 0.75,
                referenced_user_message_count: 3,
                scheduled_job_run_failed_count: 1,
                scheduled_job_run_succeeded_count: 4,
                scheduled_job_run_success_rate: 0.8,
                scheduled_job_run_total: 5,
                user_message_total: 4,
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

    fireEvent.click(screen.getByRole('button', { name: '查看指标' }));

    expect(screen.getByText('助手效果指标')).toBeInTheDocument();
    expect(await screen.findByLabelText('指标 草案生成数')).toHaveTextContent('4');
    expect(screen.getByLabelText('指标 草案确认率')).toHaveTextContent('50%');
    expect(screen.getByLabelText('指标 用户修改率')).toHaveTextContent('25%');
    expect(screen.getByLabelText('指标 @ 引用使用率')).toHaveTextContent('75%');
    expect(screen.getByLabelText('指标 作业运行成功率')).toHaveTextContent('80%');
    expect(screen.getByLabelText('指标 失败修复率')).toHaveTextContent('100%');
    expect(screen.getByLabelText('指标 知识引用命中率')).toHaveTextContent('60%');
    expect(screen.getByText('草案状态')).toBeInTheDocument();
    expect(screen.getByLabelText('草案状态 待确认')).toHaveTextContent('1');
    expect(screen.getByLabelText('草案状态 已应用')).toHaveTextContent('2');
    expect(screen.getByLabelText('草案状态 已取消')).toHaveTextContent('1');
    expect(screen.getByText('草案类型')).toBeInTheDocument();
    expect(screen.getByLabelText('草案类型 create_scheduled_job')).toHaveTextContent(
      '创建定时作业',
    );
    expect(screen.getByLabelText('草案类型 create_scheduled_job')).toHaveTextContent(
      '总数 4 · 待确认 1 · 已应用 2 · 已取消 1',
    );
    expect(screen.getByLabelText('草案类型 create_scheduled_job')).toHaveTextContent(
      '处理率 75%',
    );
    expect(screen.getByText('运行追踪')).toBeInTheDocument();
    expect(screen.getByLabelText('运行追踪 作业运行')).toHaveTextContent(
      '成功 4 · 失败 1 · 总数 5',
    );
    expect(screen.getByLabelText('运行追踪 失败修复')).toHaveTextContent(
      '已修复 2 · 失败运行 2',
    );
    expect(screen.getByText('引用追踪')).toBeInTheDocument();
    expect(screen.getByLabelText('引用追踪 用户消息')).toHaveTextContent(
      '已引用 3 · 用户消息 4',
    );
    expect(screen.getByLabelText('引用追踪 知识命中')).toHaveTextContent(
      '命中 3 · 请求 5 · 知识引用 6',
    );
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toEqual([
      ['/api/assistant/conversations', 'GET'],
      ['/api/assistant/metrics', 'GET'],
    ]);
  });

  it('loads assistant draft template market and applies a template prompt', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (input === '/api/assistant/draft-templates') {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  available: true,
                  category: 'insights',
                  code: 'weekly_feedback_insight',
                  description: '每周从用户反馈中提取高价值洞察。',
                  draft_action: 'create_scheduled_job',
                  name: '周反馈洞察',
                  prompt: '请帮我生成每周用户反馈洞察定时作业草案，并在确认后执行一次。',
                  roles: ['product_owner'],
                  source_module: '用户洞察',
                  target_resource: 'scheduled_job',
                  template_version: 'v1',
                  wizard_steps: ['数据来源', 'AI处理', '结果动作', '调度策略', '确认执行'],
                },
                {
                  available: false,
                  category: 'operations',
                  code: 'online_log_anomaly_analysis',
                  description: '分析线上日志异常并生成处理草案。',
                  draft_action: 'create_scheduled_job',
                  name: '线上日志异常分析',
                  prompt: '请生成线上日志异常分析定时作业草案。',
                  roles: ['admin'],
                  source_module: '运行数据',
                  target_resource: 'scheduled_job',
                  template_version: 'v1',
                  wizard_steps: ['数据来源', 'AI处理', '结果动作', '调度策略', '确认执行'],
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

    fireEvent.click(screen.getByRole('button', { name: '草案模板市场' }));

    expect(await screen.findByText('周反馈洞察')).toBeInTheDocument();
    expect(screen.getByText('每周从用户反馈中提取高价值洞察。')).toBeInTheDocument();
    expect(screen.getByText('暂未完整接入')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '使用模板 周反馈洞察' }));

    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue(
      '请帮我生成每周用户反馈洞察定时作业草案，并在确认后执行一次。',
    );
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toEqual([
      ['/api/assistant/conversations', 'GET'],
      ['/api/assistant/draft-templates', 'GET'],
    ]);
  });

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
                  chunk_count: 2,
                  id: 'knowledge_payment_runbook',
                  index_status: 'indexed',
                  permission_label: '可引用',
                  source_module: '知识库',
                  summary: '支付页提交无响应时，先检查网关超时、回调状态和前端埋点。',
                  title: '支付页超时排障手册',
                  type: 'knowledge_document',
                  updated_at: '2026-06-14T08:00:00+00:00',
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
    const referenceCandidatePanel = await screen.findByLabelText('引用候选');
    expect(within(referenceCandidatePanel).getByText('权限：可引用')).toBeInTheDocument();
    expect(within(referenceCandidatePanel).getByText('来源：知识库')).toBeInTheDocument();
    expect(within(referenceCandidatePanel).getByText('更新：2026-06-14')).toBeInTheDocument();
    expect(
      within(referenceCandidatePanel).getByText(
        '支付页提交无响应时，先检查网关超时、回调状态和前端埋点。',
      ),
    ).toBeInTheDocument();
    fireEvent.click(within(referenceCandidatePanel).getByRole('button', { name: /支付页超时排障手册/ }));

    const selectedReferenceList = screen.getByText('本次上下文')
      .closest('.assistant-selected-reference-list');
    expect(selectedReferenceList).not.toBeNull();
    expect(within(selectedReferenceList as HTMLElement).getAllByText(/2 个知识 chunk 将注入模型/).length)
      .toBeGreaterThan(0);
    expect(within(selectedReferenceList as HTMLElement).getByText('知识库 · 可引用 · 2026-06-14')).toBeInTheDocument();
    expect(
      within(selectedReferenceList as HTMLElement).getByText(
        '支付页提交无响应时，先检查网关超时、回调状态和前端埋点。',
      ),
    ).toBeInTheDocument();
    expect(
      within(selectedReferenceList as HTMLElement).getByRole('button', { name: '移除 支付页超时排障手册' }),
    ).toBeInTheDocument();
    fireEvent.click(
      within(selectedReferenceList as HTMLElement).getByRole(
        'button',
        { name: '查看摘要 支付页超时排障手册' },
      ),
    );
    const referenceDialog = await screen.findByRole('dialog', { name: '引用摘要 - 支付页超时排障手册' });
    expect(within(referenceDialog).getByText('引用类型')).toBeInTheDocument();
    expect(within(referenceDialog).getByText('知识文档')).toBeInTheDocument();
    expect(within(referenceDialog).getByText('来源模块')).toBeInTheDocument();
    expect(within(referenceDialog).getByText('知识库')).toBeInTheDocument();
    expect(within(referenceDialog).getByText('注入口径')).toBeInTheDocument();
    expect(within(referenceDialog).getByText('2 个知识 chunk 将注入模型')).toBeInTheDocument();
    expect(
      within(referenceDialog).getByText('支付页提交无响应时，先检查网关超时、回调状态和前端埋点。'),
    ).toBeInTheDocument();
    fireEvent.click(within(referenceDialog).getByRole('button', { name: /Close/ }));

    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('支付页应先检查网关超时和回调幂等键。')).toBeInTheDocument();
    expect(chatRequestBody).toMatchObject({
      message: '基于 @支付 分析提交无响应',
      references: [{ id: 'knowledge_payment_runbook', type: 'knowledge_document' }],
    });
  });

  it('keeps the @ reference picker visible when no candidates match', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (String(input).startsWith('/api/assistant/reference-candidates?')) {
        const params = new URLSearchParams(String(input).split('?')[1]);
        expect(params.get('query')).toBe('不存在');
        return new Response(
          JSON.stringify({
            data: {
              items: [],
              total: 0,
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
      target: { value: '@不存在' },
    });

    const referenceCandidatePanel = await screen.findByLabelText('引用候选');
    expect(await within(referenceCandidatePanel).findByText('无匹配引用')).toBeInTheDocument();
    expect(
      within(referenceCandidatePanel).getByText('请换个关键词，或确认你是否有权限访问该对象。'),
    ).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toEqual([
      ['/api/assistant/conversations', 'GET'],
      ['/api/assistant/reference-candidates?query=%E4%B8%8D%E5%AD%98%E5%9C%A8&limit=12', 'GET'],
    ]);
  });

  it('shows the backend injection limit for large knowledge document references', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (String(input).startsWith('/api/assistant/reference-candidates?')) {
        const params = new URLSearchParams(String(input).split('?')[1]);
        expect(params.get('query')).toBe('上线');
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  chunk_count: 24,
                  id: 'knowledge_release_runbook',
                  index_status: 'indexed',
                  permission_label: '可引用',
                  source_module: '知识库',
                  summary: '上线排障手册包含发布、回滚、监控和复盘步骤。',
                  title: '上线排障手册',
                  type: 'knowledge_document',
                  updated_at: '2026-06-16T08:00:00+00:00',
                  url: '/knowledge/documents?document_id=knowledge_release_runbook',
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
      target: { value: '基于 @上线 总结风险' },
    });
    fireEvent.click(await screen.findByRole('button', { name: /上线排障手册/ }));

    const selectedReferenceList = screen.getByText('本次上下文')
      .closest('.assistant-selected-reference-list');
    expect(selectedReferenceList).not.toBeNull();
    expect(
      within(selectedReferenceList as HTMLElement).getAllByText(/最多 8 个知识 chunk 将按权限注入模型/).length,
    ).toBeGreaterThan(0);
    expect(
      within(selectedReferenceList as HTMLElement).queryByText(/24 个知识 chunk 将注入模型/),
    ).not.toBeInTheDocument();
  });

  it('selects knowledge space references with scoped chunk injection copy', async () => {
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
        const params = new URLSearchParams(String(input).split('?')[1]);
        expect(params.get('query')).toBe('知识空间');
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  chunk_count: 12,
                  document_count: 3,
                  id: 'knowledge_space_support',
                  permission_label: '可引用',
                  source_module: '知识库',
                  summary: '支付与订单支持知识空间。3 篇可检索知识文档，12 个知识 chunk 可按权限注入。',
                  title: '支付支持知识空间',
                  type: 'knowledge_space',
                  updated_at: '2026-06-14T08:30:00+00:00',
                  url: '/knowledge/documents?knowledge_space_id=knowledge_space_support',
                },
              ],
              total: 1,
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      if (input === '/api/assistant/chat') {
        chatRequestBody = JSON.parse(String(init?.body)) as Record<string, unknown>;
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_space_reference',
              latency_ms: 120,
              message: {
                content: '已基于支付支持知识空间总结排障重点。',
                id: 'assistant_message_space_reference',
                references: [
                  {
                    id: 'knowledge_space_support',
                    title: '支付支持知识空间',
                    type: 'knowledge_space',
                    url: '/knowledge/documents?knowledge_space_id=knowledge_space_support',
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
      target: { value: '基于 @知识空间 总结支付排障重点' },
    });
    fireEvent.click(await screen.findByRole('button', { name: /支付支持知识空间/ }));

    const selectedReferenceList = screen.getByText('本次上下文')
      .closest('.assistant-selected-reference-list');
    expect(selectedReferenceList).not.toBeNull();
    expect(within(selectedReferenceList as HTMLElement).getByText('知识空间')).toBeInTheDocument();
    expect(
      within(selectedReferenceList as HTMLElement).getAllByText(/最多 8 个知识 chunk 将按权限注入模型/).length,
    ).toBeGreaterThan(0);
    expect(
      within(selectedReferenceList as HTMLElement).getByText(
        '支付与订单支持知识空间。3 篇可检索知识文档，12 个知识 chunk 可按权限注入。',
      ),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('已基于支付支持知识空间总结排障重点。')).toBeInTheDocument();
    expect(chatRequestBody).toMatchObject({
      message: '基于 @知识空间 总结支付排障重点',
      references: [{ id: 'knowledge_space_support', type: 'knowledge_space' }],
    });
  });

  it('selects a specific knowledge chunk with @ candidates and sends chunk reference', async () => {
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
        expect(params.get('query')).toBe('loading');
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  chunk_count: 1,
                  chunk_index: 0,
                  document_id: 'knowledge_payment_runbook',
                  id: 'knowledge_payment_runbook_chunk_001',
                  permission_label: '可引用',
                  source_module: '知识库',
                  summary: '支付页提交无响应：检查网关 30 秒超时、回调幂等键和前端 loading 状态。',
                  title: '支付页超时排障手册 #1',
                  type: 'knowledge_chunk',
                  updated_at: '2026-06-14T08:00:00+00:00',
                  url: '/knowledge/documents?document_id=knowledge_payment_runbook&chunk_id=knowledge_payment_runbook_chunk_001',
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
              conversation_id: 'conversation_chunk_reference',
              latency_ms: 166,
              message: {
                content: '只使用这段 chunk 分析 loading 状态。',
                id: 'assistant_message_chunk_reference',
                references: [
                  {
                    id: 'knowledge_payment_runbook_chunk_001',
                    title: '支付页超时排障手册 #1',
                    type: 'knowledge_chunk',
                    url: '/knowledge/documents?document_id=knowledge_payment_runbook&chunk_id=knowledge_payment_runbook_chunk_001',
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
      target: { value: '基于 @loading 分析支付页' },
    });
    fireEvent.click(await screen.findByRole('button', { name: /支付页超时排障手册 #1/ }));

    const selectedReferenceList = screen.getByText('本次上下文')
      .closest('.assistant-selected-reference-list');
    expect(selectedReferenceList).not.toBeNull();
    expect(within(selectedReferenceList as HTMLElement).getAllByText(/1 个知识 chunk 将注入模型/).length)
      .toBeGreaterThan(0);
    expect(within(selectedReferenceList as HTMLElement).getByText('知识片段')).toBeInTheDocument();
    expect(
      within(selectedReferenceList as HTMLElement).getByText(
        '支付页提交无响应：检查网关 30 秒超时、回调幂等键和前端 loading 状态。',
      ),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('只使用这段 chunk 分析 loading 状态。')).toBeInTheDocument();
    expect(chatRequestBody).toMatchObject({
      message: '基于 @loading 分析支付页',
      references: [{ id: 'knowledge_payment_runbook_chunk_001', type: 'knowledge_chunk' }],
    });
  });

  it('promotes previously selected @ references into a recent group', async () => {
    const referenceItems = [
      {
        chunk_count: 2,
        id: 'knowledge_payment_runbook',
        index_status: 'indexed',
        permission_label: '可引用',
        source_module: '知识库',
        summary: '支付页提交无响应时，先检查网关超时、回调状态和前端埋点。',
        title: '支付页超时排障手册',
        type: 'knowledge_document',
        updated_at: '2026-06-14T08:00:00+00:00',
        url: '/knowledge/documents?document_id=knowledge_payment_runbook',
      },
      {
        chunk_count: 1,
        id: 'knowledge_checkout_runbook',
        index_status: 'indexed',
        permission_label: '可引用',
        source_module: '知识库',
        summary: '收银台提交失败时检查表单状态和支付回调。',
        title: '收银台提交排障手册',
        type: 'knowledge_document',
        updated_at: '2026-06-13T08:00:00+00:00',
        url: '/knowledge/documents?document_id=knowledge_checkout_runbook',
      },
    ];
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
              items: referenceItems,
              total: referenceItems.length,
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
      target: { value: '@支付' },
    });
    fireEvent.click(await screen.findByRole('button', { name: /支付页超时排障手册/ }));
    fireEvent.click(screen.getByRole('button', { name: '移除 支付页超时排障手册' }));
    fireEvent.change(assistantInput, {
      target: { value: '@' },
    });

    const referenceCandidatePanel = await screen.findByLabelText('引用候选');
    expect(within(referenceCandidatePanel).getByText('最近使用')).toBeInTheDocument();
    expect(within(referenceCandidatePanel).getAllByRole('button', { name: /支付页超时排障手册/ })).toHaveLength(1);
    expect(within(referenceCandidatePanel).getAllByText('知识文档').length).toBeGreaterThan(0);
    expect(within(referenceCandidatePanel).getByRole('button', { name: /收银台提交排障手册/ })).toBeInTheDocument();
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

  it('shows testing quick tasks for test_owner users', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-test-owner' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-test-owner');
    saveCurrentUser({
      display_name: '测试负责人',
      id: 'user_test_owner',
      roles: ['test_owner'],
      username: 'test-owner@example.com',
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    expect(screen.getByText('角色快捷任务')).toBeInTheDocument();
    expect(screen.getByText('测试快捷任务')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '测试缺陷' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '自动化测试' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '发布风险' })).toBeInTheDocument();
    expect(screen.queryByText('管理员快捷任务')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '自动化测试' }));

    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue(
      '请检查自动化测试相关任务、失败原因和可生成的测试草案。',
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
        expect(params.get('limit')).toBe('12');
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
                  id: 'plugin_connection_feedback',
                  permission_label: '管理员可引用',
                  source_module: '插件管理',
                  title: '用户反馈数据连接',
                  type: 'plugin_connection',
                  updated_at: '2026-06-15T16:00:00+08:00',
                  url: '/tasks/plugins?connection_id=plugin_connection_feedback',
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
                  id: 'ai_task_feedback_analysis',
                  permission_label: '可引用',
                  source_module: '需求交付',
                  title: '反馈洞察研发任务',
                  type: 'ai_task',
                  updated_at: '2026-06-13T10:00:00+08:00',
                  url: '/delivery/rd-tasks?task_id=ai_task_feedback_analysis',
                },
              ],
              total: 5,
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

    const referenceCandidatePanel = await screen.findByLabelText('引用候选');
    expect(within(referenceCandidatePanel).getAllByText('知识文档').length).toBeGreaterThan(0);
    expect(within(referenceCandidatePanel).getAllByText('研发任务').length).toBeGreaterThan(0);
    expect(within(referenceCandidatePanel).getAllByText('定时作业').length).toBeGreaterThan(0);
    expect(within(referenceCandidatePanel).getAllByText('插件连接').length).toBeGreaterThan(0);
    expect(within(referenceCandidatePanel).getAllByText('Skill').length).toBeGreaterThan(0);
    expect(within(referenceCandidatePanel).getByText('来源：知识库')).toBeInTheDocument();
    expect(within(referenceCandidatePanel).getAllByText('权限：可引用').length).toBeGreaterThan(0);
    expect(within(referenceCandidatePanel).getByText('更新：2026-06-16')).toBeInTheDocument();
    expect(within(referenceCandidatePanel).getByText('来源：任务中心')).toBeInTheDocument();
    expect(within(referenceCandidatePanel).getAllByText('权限：管理员可引用').length).toBeGreaterThan(0);
    expect(within(referenceCandidatePanel).getAllByText('更新：2026-06-15').length).toBeGreaterThan(0);
    expect(within(referenceCandidatePanel).getByText('来源：插件管理')).toBeInTheDocument();

    fireEvent.keyDown(assistantInput, { key: 'ArrowDown' });
    fireEvent.keyDown(assistantInput, { key: 'Enter' });

    expect(screen.getByText('提取每周用户反馈有价值信息')).toBeInTheDocument();
    expect(screen.getAllByText('定时作业').length).toBeGreaterThan(0);
  });

  it('sends @ scheduled job run-once commands with the active candidate reference', async () => {
    let chatRequestBody: Record<string, unknown> | undefined;
    const scrollIntoViewMock = vi.fn();
    Object.defineProperty(Element.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoViewMock,
    });
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
                content: '已触发「提取每周用户反馈有价值信息」执行一次，运行记录 scheduled_job_run_001 当前状态为 running。',
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
                    title: '提取每周用户反馈有价值信息 / running',
                    type: 'scheduled_job_run',
                    url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_001',
                  },
                ],
                role: 'assistant',
                suggestions: [],
                tool_results: [
                  {
                    intent: 'scheduled_job_run_once',
                    items: [
                      {
                        id: 'scheduled_job_run_001',
                        records_imported: 0,
                        scheduled_job_id: 'scheduled_job_feedback_weekly',
                        status: 'running',
                        title: '提取每周用户反馈有价值信息 / running',
                        trigger_type: 'manual',
                        type: 'scheduled_job_run',
                        url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_001',
                      },
                    ],
                    summary: {
                      run_id: 'scheduled_job_run_001',
                      scheduled_job_id: 'scheduled_job_feedback_weekly',
                      status: 'running',
                    },
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
      if (input === '/api/system/scheduled-job-runs?scheduled_job_id=scheduled_job_feedback_weekly') {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  error_code: null,
                  error_message: null,
                  finished_at: '2026-06-17T02:53:50.260971+00:00',
                  id: 'scheduled_job_run_001',
                  records_imported: 19,
                  scheduled_job_id: 'scheduled_job_feedback_weekly',
                  started_at: '2026-06-17T02:53:15.835137+00:00',
                  status: 'succeeded',
                  trigger_type: 'manual',
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

    const assistantInput = screen.getByLabelText('发送给 AI 助手');
    fireEvent.change(assistantInput, {
      target: { value: '@提取每周用户反馈有价值信息 执行一次' },
    });

    await screen.findByRole('button', { name: /提取每周用户反馈有价值信息/ });
    fireEvent.keyDown(assistantInput, { key: 'Enter' });

    expect(await screen.findByText(/已触发「提取每周用户反馈有价值信息」执行一次/)).toBeInTheDocument();
    expect(await screen.findByText('运行状态：成功')).toBeInTheDocument();
    expect(screen.getByText('已刷新到最新状态：成功')).toBeInTheDocument();
    expect(screen.getByText('导入记录：19')).toBeInTheDocument();
    expect(scrollIntoViewMock).toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: '问这次运行' }));
    expect(assistantInput).toHaveValue('@提取每周用户反馈有价值信息 / succeeded 为什么这次任务失败？');
    const currentContext = screen.getByLabelText('本次上下文');
    expect(within(currentContext).getByText('运行记录')).toBeInTheDocument();
    expect(within(currentContext).getByText('任务中心 · 可引用')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '生成运行修复草案' }));
    expect(assistantInput).toHaveValue(
      '@提取每周用户反馈有价值信息 / succeeded 这次失败怎么修？帮我生成修复草案',
    );

    fireEvent.click(screen.getByRole('button', { name: '对比这次运行' }));
    expect(assistantInput).toHaveValue('@提取每周用户反馈有价值信息 / succeeded 和上次成功有什么不同？');

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

  it('resolves @ scheduled job run-once commands when sent before candidates finish loading', async () => {
    let chatRequestBody: Record<string, unknown> | undefined;
    const referenceRequestParams: URLSearchParams[] = [];
    const resolveReferenceRequests: Array<() => void> = [];
    const scheduledJobReference = {
      id: 'scheduled_job_feedback_weekly',
      permission_label: '管理员可引用',
      source_module: '任务中心',
      title: '提取每周用户反馈有价值信息',
      type: 'scheduled_job',
      updated_at: '2026-06-15T18:00:00+08:00',
      url: '/tasks/scheduled-jobs?job_id=scheduled_job_feedback_weekly',
    };
    const referenceResponse = () => new Response(
      JSON.stringify({
        data: {
          items: [scheduledJobReference],
          total: 1,
        },
      }),
      { headers: { 'Content-Type': 'application/json' }, status: 200 },
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
        const params = new URLSearchParams(String(input).split('?')[1] ?? '');
        referenceRequestParams.push(params);
        return new Promise<Response>((resolve) => {
          resolveReferenceRequests.push(() => resolve(referenceResponse()));
        });
      }
      if (input === '/api/assistant/chat') {
        chatRequestBody = JSON.parse(String(init?.body));
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_run_once',
              latency_ms: 12,
              message: {
                content: '已触发「提取每周用户反馈有价值信息」执行一次，运行记录 scheduled_job_run_001 当前状态为 running。',
                id: 'assistant_message_run_once',
                references: [
                  scheduledJobReference,
                  {
                    id: 'scheduled_job_run_001',
                    title: '提取每周用户反馈有价值信息 / running',
                    type: 'scheduled_job_run',
                    url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_001',
                  },
                ],
                role: 'assistant',
                suggestions: [],
                tool_results: [
                  {
                    intent: 'scheduled_job_run_once',
                    items: [
                      {
                        id: 'scheduled_job_run_001',
                        records_imported: 0,
                        scheduled_job_id: 'scheduled_job_feedback_weekly',
                        status: 'running',
                        title: '提取每周用户反馈有价值信息 / running',
                        trigger_type: 'manual',
                        type: 'scheduled_job_run',
                        url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_001',
                      },
                    ],
                    summary: {
                      run_id: 'scheduled_job_run_001',
                      scheduled_job_id: 'scheduled_job_feedback_weekly',
                      status: 'running',
                    },
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

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '@提取每周用户反馈有价值信息 执行一次' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    await waitFor(() => expect(resolveReferenceRequests.length).toBeGreaterThan(0));
    resolveReferenceRequests.splice(0).forEach((resolve) => resolve());

    await waitFor(() => expect(chatRequestBody).toBeDefined());
    expect(referenceRequestParams.some((params) => params.get('type') === 'scheduled_job')).toBe(true);
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

  it('shows active run progress for @ scheduled job run-once commands', async () => {
    let runPollCount = 0;
    const scheduledJobReference = {
      id: 'scheduled_job_feedback_weekly',
      permission_label: '管理员可引用',
      source_module: '任务中心',
      title: '提取每周用户反馈有价值信息',
      type: 'scheduled_job',
      updated_at: '2026-06-15T18:00:00+08:00',
      url: '/tasks/scheduled-jobs?job_id=scheduled_job_feedback_weekly',
    };
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
          JSON.stringify({ data: { items: [scheduledJobReference], total: 1 } }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      if (input === '/api/assistant/chat') {
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_run_once',
              latency_ms: 12,
              message: {
                content: '已触发「提取每周用户反馈有价值信息」执行一次，运行记录 scheduled_job_run_001 当前状态为 running。',
                id: 'assistant_message_run_once',
                references: [
                  scheduledJobReference,
                  {
                    id: 'scheduled_job_run_001',
                    title: '提取每周用户反馈有价值信息 / running',
                    type: 'scheduled_job_run',
                    url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_001',
                  },
                ],
                role: 'assistant',
                suggestions: [],
                tool_results: [
                  {
                    intent: 'scheduled_job_run_once',
                    items: [
                      {
                        id: 'scheduled_job_run_001',
                        records_imported: 0,
                        scheduled_job_id: 'scheduled_job_feedback_weekly',
                        status: 'running',
                        title: '提取每周用户反馈有价值信息 / running',
                        trigger_type: 'manual',
                        type: 'scheduled_job_run',
                        url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_001',
                      },
                    ],
                    summary: {
                      run_id: 'scheduled_job_run_001',
                      scheduled_job_id: 'scheduled_job_feedback_weekly',
                      status: 'running',
                    },
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
      if (input === '/api/system/scheduled-job-runs?scheduled_job_id=scheduled_job_feedback_weekly') {
        runPollCount += 1;
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  error_code: null,
                  error_message: null,
                  finished_at: null,
                  id: 'scheduled_job_run_001',
                  records_imported: 0,
                  result_summary: runPollCount === 1
                    ? {}
                    : {
                        execution_nodes: {
                          data_connection: {
                            label: '数据连接获取内容',
                            status: 'succeeded',
                          },
                          result_action: {
                            label: '动作反馈内容',
                            status: 'waiting_runner',
                          },
                          runner_execution: {
                            label: 'AI 执行器执行内容',
                            status: 'queued',
                          },
                        },
                      },
                  scheduled_job_id: 'scheduled_job_feedback_weekly',
                  started_at: '2026-06-17T02:53:15.835137+00:00',
                  status: 'running',
                  trigger_type: 'manual',
                  updated_at: runPollCount === 1
                    ? '2026-06-17T02:53:15.835137+00:00'
                    : '2026-06-17T02:53:20.835137+00:00',
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
      target: { value: '@提取每周用户反馈有价值信息 执行一次' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText(/已触发「提取每周用户反馈有价值信息」执行一次/)).toBeInTheDocument();
    await waitFor(() => expect(runPollCount).toBeGreaterThanOrEqual(2));
    expect(await screen.findByText('执行进度：AI 执行器执行内容（排队中）')).toBeInTheDocument();
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
                    items: [
                      {
                        id: 'scheduled_job_run_feedback_failed',
                        scheduled_job_id: 'scheduled_job_feedback_weekly',
                        stages: [
                          {
                            error_message: null,
                            log_id: null,
                            stage: 'data_connection',
                            status: 'succeeded',
                            summary: '从 MaxCompute 读取 128 条反馈。',
                          },
                          {
                            error_message: null,
                            log_id: 'model_gateway_log_feedback_failed',
                            stage: 'ai_processing',
                            status: 'succeeded',
                            summary: '生成 6 条洞察。',
                          },
                          {
                            error_code: 'RESULT_WRITE_FAILED',
                            error_message: 'HTTP 500: downstream write failed',
                            log_id: 'plugin_invocation_log_feedback_failed',
                            result_write_record_id: 'result_write_record_scheduled_job_run_feedback_failed',
                            result_write_status: 'failed',
                            result_write_target: 'user_feedback_insights',
                            result_write_target_label: '用户洞察表',
                            stage: 'result_action',
                            status: 'failed',
                            summary: '写入反馈洞察表失败。',
                          },
                        ],
                        status: 'failed',
                        title: '每周反馈洞察定时作业 / failed',
                        url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed',
                      },
                    ],
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
    expect(screen.getByText('运行诊断')).toBeInTheDocument();
    expect(screen.getByText('数据连接')).toBeInTheDocument();
    expect(screen.getByText('AI处理')).toBeInTheDocument();
    expect(screen.getByText('结果动作')).toBeInTheDocument();
    expect(screen.getByText('数据连接是否成功：成功')).toBeInTheDocument();
    expect(screen.getByText('AI处理是否成功：成功')).toBeInTheDocument();
    expect(screen.getByText('结果动作是否写入成功：失败')).toBeInTheDocument();
    expect(screen.getByText('写入反馈洞察表失败。')).toBeInTheDocument();
    expect(screen.getByText('关联日志：model_gateway_log_feedback_failed')).toBeInTheDocument();
    expect(screen.getByText('关联日志：plugin_invocation_log_feedback_failed')).toBeInTheDocument();
    expect(screen.getByText('写入目标：用户洞察表')).toBeInTheDocument();
    expect(screen.getByText('错误：HTTP 500: downstream write failed')).toBeInTheDocument();
    expect(screen.getByRole('link', {
      name: '查看写入记录 result_write_record_scheduled_job_run_feedback_failed',
    })).toHaveAttribute(
      'href',
      '/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed&result_write_record_id=result_write_record_scheduled_job_run_feedback_failed',
    );
    fireEvent.click(screen.getByRole('button', { name: '生成修复草案' }));
    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue(
      '@每周反馈洞察定时作业 / failed 这次失败怎么修？帮我生成修复草案',
    );
    const selectedReferenceList = screen.getByText('本次上下文')
      .closest('.assistant-selected-reference-list');
    expect(selectedReferenceList).not.toBeNull();
    expect(within(selectedReferenceList as HTMLElement).getByText('每周反馈洞察定时作业 / failed'))
      .toBeInTheDocument();
    expect(chatRequestBody).toMatchObject({
      message: '为什么 @反馈 这次失败？',
      references: [{ id: 'scheduled_job_run_feedback_failed', type: 'scheduled_job_run' }],
    });
  });

  it('renders plugin connection diagnostics and lets users continue with the connection reference', async () => {
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
        expect(JSON.parse(String(init?.body))).toMatchObject({
          message: '为什么插件连接失败？',
        });
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_plugin_connection_diagnostic',
              latency_ms: 9,
              message: {
                content: '我已读取最近插件连接测试记录，找到 1 个失败连接。',
                id: 'assistant_message_plugin_connection_diagnostic',
                references: [
                  {
                    id: 'plugin_connection_maxcompute',
                    title: 'MaxCompute 用户反馈连接',
                    type: 'plugin_connection',
                    url: '/tasks/plugins?connection_id=plugin_connection_maxcompute',
                  },
                ],
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'plugin_connection_diagnostic',
                    items: [
                      {
                        checked_at: '2026-06-17T09:20:00+00:00',
                        connection_status: 'active',
                        endpoint_url: 'https://feedback.example.com',
                        environment: 'prod',
                        error_code: 'HTTP_ERROR',
                        error_message: 'HTTP 403: forbidden',
                        failed_step: 'http_request',
                        id: 'plugin_connection_maxcompute',
                        plugin_id: 'plugin_http',
                        plugin_name: '通用 HTTP 插件',
                        repair_suggestions: [
                          {
                            code: 'http_authentication_failed',
                            detail: '检查认证方式、Token/API Key、Header 名和目标环境权限。',
                            title: '检查认证配置',
                          },
                        ],
                        stages: [
                          {
                            stage: 'connection_config',
                            status: 'succeeded',
                            summary: '连接状态 active，环境 prod，插件 通用 HTTP 插件。',
                          },
                          {
                            stage: 'latest_test',
                            status: 'failed',
                            summary: '最近测试状态 failed，失败步骤 http_request，错误：HTTP 403: forbidden。',
                          },
                          {
                            stage: 'repair_suggestions',
                            status: 'warning',
                            summary: '已生成 1 条修复建议。',
                          },
                        ],
                        status: 'failed',
                        title: 'MaxCompute 用户反馈连接',
                        url: '/tasks/plugins?connection_id=plugin_connection_maxcompute',
                      },
                    ],
                    summary: {
                      diagnosed_count: 1,
                      failed_count: 1,
                      source: 'plugin_connection.last_test_summary',
                    },
                    tool: 'assistant.plugin_connection_diagnostic',
                  },
                ],
              },
              model: 'assistant-deterministic',
              suggestions: ['生成插件连接修复草案', '打开插件管理'],
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
    fireEvent.change(assistantInput, { target: { value: '为什么插件连接失败？' } });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('插件连接诊断')).toBeInTheDocument();
    expect(screen.getAllByText('MaxCompute 用户反馈连接').length).toBeGreaterThan(0);
    expect(screen.getByText('失败步骤')).toBeInTheDocument();
    expect(screen.getByText('http_request')).toBeInTheDocument();
    expect(screen.getByText('连接配置')).toBeInTheDocument();
    expect(screen.getAllByText('最近测试').length).toBeGreaterThan(0);
    expect(screen.getAllByText('修复建议').length).toBeGreaterThan(0);
    expect(screen.getByText('最近测试状态 failed，失败步骤 http_request，错误：HTTP 403: forbidden。'))
      .toBeInTheDocument();
    expect(screen.getByText('检查认证配置：检查认证方式、Token/API Key、Header 名和目标环境权限。'))
      .toBeInTheDocument();
    expect(screen.getByRole('link', { name: /打开插件连接/ })).toHaveAttribute(
      'href',
      '/tasks/plugins?connection_id=plugin_connection_maxcompute',
    );

    fireEvent.click(screen.getAllByRole('button', { name: '生成插件连接修复草案' })[0]);

    expect(assistantInput).toHaveValue(
      '@MaxCompute 用户反馈连接 这个插件连接失败怎么修？请生成修复草案',
    );
    const selectedReferenceList = screen.getByText('本次上下文')
      .closest('.assistant-selected-reference-list');
    expect(selectedReferenceList).not.toBeNull();
    expect(within(selectedReferenceList as HTMLElement).getByText('插件连接')).toBeInTheDocument();
    expect(within(selectedReferenceList as HTMLElement).getByText('MaxCompute 用户反馈连接'))
      .toBeInTheDocument();
  });

  it('renders scheduled job run comparison tool results', async () => {
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
        chatRequestBody = JSON.parse(String(init?.body)) as Record<string, unknown>;
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_run_comparison',
              latency_ms: 190,
              message: {
                content: '这次和上次成功相比，差异集中在结果动作写入阶段。',
                id: 'assistant_message_run_comparison',
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
                    intent: 'scheduled_job_run_comparison',
                    items: [
                      {
                        baseline_run: {
                          duration_ms: 3600,
                          id: 'scheduled_job_run_feedback_success',
                          records_imported: 120,
                          status: 'succeeded',
                        },
                        current_run: {
                          duration_ms: 4200,
                          error_message: '结果写入动作返回 500',
                          id: 'scheduled_job_run_feedback_failed',
                          records_imported: 128,
                          status: 'failed',
                        },
                        differences: [
                          {
                            baseline: 'succeeded',
                            current: 'failed',
                            field: 'status',
                          },
                          {
                            baseline_result_write_status: 'succeeded',
                            baseline_status: 'succeeded',
                            baseline_summary: '写入反馈洞察表成功。',
                            current_result_write_status: 'failed',
                            current_status: 'failed',
                            current_summary: '写入反馈洞察表失败。',
                            field: 'stage.result_action',
                            stage: 'result_action',
                          },
                        ],
                        id: 'scheduled_job_run_feedback_failed',
                        scheduled_job_id: 'scheduled_job_feedback_weekly',
                        title: '每周反馈洞察定时作业 / failed',
                        url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed',
                      },
                    ],
                    references: [
                      {
                        id: 'scheduled_job_run_feedback_success',
                        title: '每周反馈洞察定时作业 / succeeded',
                        type: 'scheduled_job_run',
                        url: '/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_success',
                      },
                    ],
                    summary: { baseline_found_count: 1, comparison_count: 1 },
                    tool: 'assistant.scheduled_job_run_comparison',
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
      target: { value: '这次 @反馈 和上次成功有什么不同？' },
    });
    fireEvent.click(await screen.findByRole('button', { name: /每周反馈洞察定时作业/ }));
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('运行对比')).toBeInTheDocument();
    expect(screen.getByText('当前：failed')).toBeInTheDocument();
    expect(screen.getByText('上次成功：succeeded')).toBeInTheDocument();
    expect(screen.getByText('结果动作')).toBeInTheDocument();
    expect(screen.getByText('当前：写入反馈洞察表失败。')).toBeInTheDocument();
    expect(screen.getByText('上次：写入反馈洞察表成功。')).toBeInTheDocument();
    expect(chatRequestBody).toMatchObject({
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
    expect(screen.getByText('已从链接带入运行记录：每周反馈洞察定时作业 / failed')).toBeInTheDocument();
    expect(screen.getByText('运行记录')).toBeInTheDocument();
    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue('为什么这次任务失败？');

    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('这次失败发生在结果动作写入阶段。')).toBeInTheDocument();
    expect(chatRequestBody).toMatchObject({
      message: '为什么这次任务失败？',
      references: [{ id: 'scheduled_job_run_feedback_failed', type: 'scheduled_job_run' }],
    });
  });

  it('preselects knowledge space references from route query parameters', async () => {
    let chatRequestBody: Record<string, unknown> | undefined;
    window.history.pushState(
      {},
      '',
      '/assistant?reference_type=knowledge_space&reference_id=knowledge_space_support&prompt=%E6%80%BB%E7%BB%93%E8%BF%99%E4%B8%AA%E7%9F%A5%E8%AF%86%E7%A9%BA%E9%97%B4',
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
        expect(params.get('query')).toBe('knowledge_space_support');
        expect(params.get('type')).toBe('knowledge_space');
        expect(params.get('limit')).toBe('1');
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  chunk_count: 12,
                  document_count: 3,
                  id: 'knowledge_space_support',
                  permission_label: '可引用',
                  source_module: '知识库',
                  summary: '支付与订单支持知识空间。3 篇可检索知识文档，12 个知识 chunk 可按权限注入。',
                  title: '支付支持知识空间',
                  type: 'knowledge_space',
                  updated_at: '2026-06-14T08:30:00+00:00',
                  url: '/knowledge/documents?knowledge_space_id=knowledge_space_support',
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
              conversation_id: 'conversation_knowledge_space_route_reference',
              latency_ms: 120,
              message: {
                content: '已基于支付支持知识空间总结上下文。',
                id: 'assistant_message_knowledge_space_route_reference',
                references: [
                  {
                    id: 'knowledge_space_support',
                    title: '支付支持知识空间',
                    type: 'knowledge_space',
                    url: '/knowledge/documents?knowledge_space_id=knowledge_space_support',
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

    const currentContext = await screen.findByLabelText('本次上下文');
    expect(within(currentContext).getByText('已从链接带入知识空间：支付支持知识空间')).toBeInTheDocument();
    expect(within(currentContext).getByText('知识空间')).toBeInTheDocument();
    expect(
      within(currentContext).getAllByText(/最多 8 个知识 chunk 将按权限注入模型/).length,
    ).toBeGreaterThan(0);
    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue('总结这个知识空间');

    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('已基于支付支持知识空间总结上下文。')).toBeInTheDocument();
    expect(chatRequestBody).toMatchObject({
      message: '总结这个知识空间',
      references: [{ id: 'knowledge_space_support', type: 'knowledge_space' }],
    });
  });

  it('keeps route reference resolution status visible when the linked context is missing', async () => {
    window.history.pushState(
      {},
      '',
      '/assistant?reference_type=scheduled_job_run&reference_id=scheduled_job_run_missing&prompt=%E4%B8%BA%E4%BB%80%E4%B9%88%E8%BF%99%E6%AC%A1%E4%BB%BB%E5%8A%A1%E5%A4%B1%E8%B4%A5%EF%BC%9F',
    );
    let resolveReferenceCandidates: ((response: Response) => void) | undefined;
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (String(input).startsWith('/api/assistant/reference-candidates?')) {
        const params = new URLSearchParams(String(input).split('?')[1]);
        expect(params.get('query')).toBe('scheduled_job_run_missing');
        expect(params.get('type')).toBe('scheduled_job_run');
        return new Promise<Response>((resolve) => {
          resolveReferenceCandidates = resolve;
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    const currentContext = await screen.findByLabelText('本次上下文');
    expect(within(currentContext).getByText('正在解析运行记录引用：scheduled_job_run_missing')).toBeInTheDocument();
    resolveReferenceCandidates?.(
      new Response(
        JSON.stringify({
          data: {
            items: [],
            total: 0,
          },
        }),
        { headers: { 'Content-Type': 'application/json' }, status: 200 },
      ),
    );
    expect(
      await within(currentContext).findByText('引用解析失败：运行记录 scheduled_job_run_missing 不存在或无权限'),
    ).toBeInTheDocument();
    expect(within(currentContext).getByText('0 个显式引用')).toBeInTheDocument();
    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue('为什么这次任务失败？');
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
                        wizard_steps: [
                          {
                            depends_on: [],
                            key: 'data_source',
                            status: 'ready',
                            summary: '已选择 GitHub 代码巡检动作',
                            title: '数据来源',
                          },
                          {
                            depends_on: [],
                            key: 'ai_processing',
                            status: 'ready',
                            summary: '已选择代码巡检 AI角色和 Skill',
                            title: 'AI处理',
                          },
                          {
                            depends_on: [],
                            key: 'result_action',
                            status: 'ready',
                            summary: '写代码巡检报告、严重问题建 Bug、发送通知',
                            title: '结果动作',
                          },
                          {
                            depends_on: [],
                            key: 'schedule',
                            status: 'ready',
                            summary: 'cron: 0 2 * * MON',
                            title: '调度策略',
                          },
                          {
                            depends_on: [],
                            key: 'confirm',
                            status: 'pending',
                            summary: '确认后创建定时作业',
                            title: '确认执行',
                          },
                        ],
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
    expect(screen.getByText('配置向导')).toBeInTheDocument();
    expect(screen.getByText('数据来源：已就绪')).toBeInTheDocument();
    expect(screen.getByText('AI处理：已就绪')).toBeInTheDocument();
    expect(screen.getByText('确认执行：待确认')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'AI生成数据来源草案' }));
    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue(
      '为「代码仓库质量安全规范巡检」生成或调整「数据来源」步骤草案。当前状态：已就绪。请给出建议配置、字段校验和下一步确认动作',
    );
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

  it('offers prerequisite draft prompts from blocked wizard steps', async () => {
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
              conversation_id: 'conversation_wizard_prerequisite',
              latency_ms: 166,
              message: {
                content: '我先生成一个待补齐依赖的代码巡检定时作业草案。',
                id: 'assistant_message_wizard_prerequisite',
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'scheduled_job_draft',
                    items: [
                      {
                        action: 'create_scheduled_job',
                        draft_id: 'assistant_draft_code_repository_inspection_missing_dependencies',
                        payload: {
                          cron_expression: '0 2 * * MON',
                          execution_mode: 'ai_generated',
                          job_type: 'code_repository_inspection',
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        title: '代码仓库质量安全规范巡检',
                        wizard_steps: [
                          {
                            depends_on: ['GitHub 连接', '代码巡检动作'],
                            key: 'data_source',
                            status: 'needs_prerequisite',
                            summary: '需要先配置 GitHub 连接和代码巡检动作',
                            title: '数据来源',
                          },
                          {
                            depends_on: ['代码巡检 Skill', 'AI角色'],
                            key: 'ai_processing',
                            status: 'blocked',
                            summary: '需要先配置代码巡检 Skill 和 AI角色',
                            title: 'AI处理',
                          },
                        ],
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
      target: { value: '帮我创建代码巡检定时作业' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('数据来源：需先确认前置草案')).toBeInTheDocument();
    expect(screen.getByText('AI处理：已阻塞')).toBeInTheDocument();
    expect(screen.getByText('依赖：GitHub 连接、代码巡检动作')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'AI生成AI处理草案' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '手动调整数据来源' })).toHaveAttribute(
      'href',
      '/tasks/plugins',
    );
    expect(screen.getByRole('link', { name: '手动调整AI处理' })).toHaveAttribute(
      'href',
      '/settings/ai-capabilities',
    );

    fireEvent.click(screen.getByRole('button', { name: '生成数据来源前置草案' }));

    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue(
      '为「代码仓库质量安全规范巡检」补齐「数据来源」前置配置草案。依赖：GitHub 连接、代码巡检动作',
    );
  });

  it('renders assistant draft cards when only server_draft_id is present', async () => {
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
              conversation_id: 'conversation_local_draft',
              latency_ms: 88,
              message: {
                content: '我生成了一个本地配置草案。',
                id: 'assistant_message_local_draft',
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'scheduled_job_draft',
                    items: [
                      {
                        action: 'create_scheduled_job',
                        payload: {
                          execution_mode: 'deterministic',
                          job_type: 'dashboard_snapshot_refresh',
                          name: '本地草案仪表盘刷新',
                          schedule_type: 'manual',
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        server_draft_id: 'assistant_action_draft_server_only',
                        status: 'pending',
                        title: '创建本地仪表盘刷新草案',
                      },
                    ],
                    summary: { draft_count: 1, requires_confirmation: true },
                    tool: 'assistant.action_draft',
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

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '帮我生成一个本地草案' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('我生成了一个本地配置草案。')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: '查看详情' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看草案' })).toHaveAttribute(
      'href',
      '/assistant?draft_id=assistant_action_draft_server_only',
    );
  });

  it('loads a server-side draft from route query and renders its tracking card', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (input === '/api/assistant/action-drafts/assistant_action_draft_deeplink') {
        return new Response(
          JSON.stringify({
            data: {
              action: 'create_scheduled_job',
              client_draft_id: 'assistant_draft_weekly_feedback_insight',
              created_at: '2026-06-17T08:00:00+00:00',
              created_by: 'user_admin',
              id: 'assistant_action_draft_deeplink',
              payload: {
                cron_expression: '0 9 * * MON',
                execution_mode: 'ai_agent',
                job_type: 'user_feedback_insight_extract',
                name: '每周用户反馈洞察',
              },
              preview: {
                diffs: [
                  {
                    change_type: 'create',
                    current: null,
                    field: 'name',
                    label: '作业名称',
                    proposed: '每周用户反馈洞察',
                  },
                ],
                validation: {
                  issues: [],
                  status: 'passed',
                },
              },
              risk_level: 'medium',
              status: 'pending',
              title: '每周用户反馈洞察定时作业草案',
              updated_at: '2026-06-17T08:00:00+00:00',
              wizard_steps: [
                {
                  depends_on: [],
                  key: 'data_source',
                  status: 'ready',
                  summary: '已选择用户反馈数据来源',
                  title: '数据来源',
                },
                {
                  depends_on: ['data_source'],
                  key: 'ai_processing',
                  status: 'needs_prerequisite',
                  summary: '需要选择 AI角色、Skill 和模型网关',
                  title: 'AI处理',
                },
                {
                  depends_on: ['data_source', 'ai_processing'],
                  key: 'confirm',
                  status: 'pending',
                  summary: '确认后创建定时作业',
                  title: '确认执行',
                },
              ],
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    window.history.pushState({}, '', '/assistant?draft_id=assistant_action_draft_deeplink');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    const draftLinkStatus = await screen.findByLabelText('草案链接状态');
    expect(within(draftLinkStatus).getByText('已加载')).toBeInTheDocument();
    expect(
      within(draftLinkStatus).getByText('已从链接打开草案：每周用户反馈洞察定时作业草案'),
    ).toBeInTheDocument();
    expect(within(draftLinkStatus).getByText('每周用户反馈洞察定时作业草案')).toBeInTheDocument();
    expect(within(draftLinkStatus).getAllByText('待确认').length).toBeGreaterThanOrEqual(1);
    expect(within(draftLinkStatus).getByText('配置向导')).toBeInTheDocument();
    expect(within(draftLinkStatus).getByText('数据来源：已就绪')).toBeInTheDocument();
    expect(within(draftLinkStatus).getByText('已选择用户反馈数据来源')).toBeInTheDocument();
    expect(within(draftLinkStatus).getByText('AI处理：需先确认前置草案')).toBeInTheDocument();
    expect(within(draftLinkStatus).getByText('依赖：data_source')).toBeInTheDocument();
    expect(within(draftLinkStatus).getByText('应用前预检')).toBeInTheDocument();
    expect(within(draftLinkStatus).getByText('作业名称')).toBeInTheDocument();
    expect(within(draftLinkStatus).getByRole('button', { name: /确认创建/ })).toBeInTheDocument();
    expect(within(draftLinkStatus).getByRole('button', { name: /取消/ })).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toEqual(
      expect.arrayContaining([
        ['/api/assistant/conversations', 'GET'],
        ['/api/assistant/action-drafts/assistant_action_draft_deeplink', 'GET'],
      ]),
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
                result: {
                  scheduled_job_run: {
                    id: 'scheduled_job_run_001',
                    scheduled_job_id: 'scheduled_job_001',
                    status: 'succeeded',
                    trigger_type: 'manual',
                  },
                },
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
    expect(screen.getByRole('link', { name: '打开本次运行' })).toHaveAttribute(
      'href',
      '/tasks/scheduled-jobs?job_id=scheduled_job_001&run_id=scheduled_job_run_001',
    );
    fireEvent.click(screen.getByRole('button', { name: '重新生成' }));
    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue('重新生成「创建仪表盘刷新定时任务」草案');
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
      '/api/assistant/action-drafts/assistant_action_draft_001/confirm',
      'POST',
    ]);
  });

  it('marks assistant action drafts as failed when confirmation fails', async () => {
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
              conversation_id: 'conversation_failed_draft',
              latency_ms: 128,
              message: {
                content: '我已生成一个服务端草案。',
                id: 'assistant_message_failed_draft',
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'scheduled_job_draft',
                    items: [
                      {
                        action: 'create_scheduled_job',
                        draft_id: 'assistant_action_draft_failed_confirm',
                        payload: {
                          execution_mode: 'deterministic',
                          job_type: 'dashboard_snapshot_refresh',
                          name: '会确认失败的定时任务',
                          schedule_type: 'manual',
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        server_draft_id: 'assistant_action_draft_failed_confirm',
                        status: 'pending',
                        title: '创建会失败的定时任务',
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
      if (input === '/api/assistant/action-drafts/assistant_action_draft_failed_confirm/confirm') {
        expect(init?.method).toBe('POST');
        return new Response(
          JSON.stringify({
            error: {
              code: 'DRAFT_VALIDATION_FAILED',
              message: '草案校验失败：缺少数据连接',
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 409 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<AssistantPage />);

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '帮我创建一个会失败的草案' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    fireEvent.click(await screen.findByRole('button', { name: /确认创建/ }));

    expect(await screen.findByText('失败')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /确认创建/ })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '重新生成' }));
    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue('重新生成「创建会失败的定时任务」草案');
  });

  it('makes run-once draft confirmation explicit when an @ command needs a new scheduled job', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/assistant/conversations') {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (String(input).startsWith('/api/assistant/reference-candidates?')) {
        return new Response(JSON.stringify({ data: { items: [], total: 0 } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      if (input === '/api/assistant/chat') {
        return new Response(
          JSON.stringify({
            data: {
              conversation_id: 'conversation_run_once_draft',
              latency_ms: 41,
              message: {
                content: '还没有找到可执行的定时作业：提取每周用户反馈有价值信息。我先生成周反馈洞察定时作业草案，确认并补齐校验项后再执行一次。',
                id: 'assistant_message_run_once_draft',
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'scheduled_job_draft',
                    items: [
                      {
                        action: 'create_scheduled_job',
                        client_draft_id: 'assistant_draft_weekly_feedback_insight',
                        draft_id: 'assistant_action_draft_feedback_run_once',
                        payload: {
                          config_json: {
                            assistant_run_once_request: {
                              requested: true,
                              source_message: '@提取每周用户反馈有价值信息 执行一次',
                            },
                          },
                          execution_mode: 'ai_generated',
                          job_type: 'user_feedback_insight_extract',
                          name: '每周用户反馈洞察抽取',
                          schedule_type: 'cron',
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        run_once_requested: true,
                        server_draft_id: 'assistant_action_draft_feedback_run_once',
                        status: 'pending',
                        title: '创建周反馈洞察定时作业',
                      },
                    ],
                    summary: {
                      draft_count: 1,
                      requires_confirmation: true,
                      run_once_requested: true,
                      status: 'draft_required',
                    },
                    tool: 'assistant.action_draft',
                  },
                ],
              },
              model: 'assistant-deterministic',
              suggestions: ['查看并确认草案'],
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
      target: { value: '@提取每周用户反馈有价值信息 执行一次' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('确认后执行一次')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /确认并执行一次/ })).toBeInTheDocument();
    expect(screen.getByText('确认前不会写入作业定义；确认后会立即执行一次')).toBeInTheDocument();
  });

  it('does not allow expired assistant drafts to be applied through forms', async () => {
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
              conversation_id: 'conversation_expired_draft',
              latency_ms: 31,
              message: {
                content: '这个草案已经过期，需要重新生成后再确认。',
                id: 'assistant_message_expired_draft',
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'scheduled_job_draft',
                    items: [
                      {
                        action: 'create_scheduled_job',
                        client_draft_id: 'assistant_draft_expired_weekly_feedback',
                        draft_id: 'assistant_action_draft_expired',
                        payload: {
                          execution_mode: 'ai_generated',
                          job_type: 'user_feedback_insight_extract',
                          name: '已过期的周反馈洞察草案',
                          schedule_type: 'cron',
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        server_draft_id: 'assistant_action_draft_expired',
                        status: 'expired',
                        title: '创建周反馈洞察定时作业',
                      },
                    ],
                    summary: { draft_count: 1, requires_confirmation: false },
                    tool: 'assistant.action_draft',
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

    fireEvent.change(screen.getByLabelText('发送给 AI 助手'), {
      target: { value: '帮我创建周反馈洞察草案' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('已过期')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /确认创建/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '取消' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: '应用到定时作业表单' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '重新生成' }));
    expect(screen.getByLabelText('发送给 AI 助手')).toHaveValue('重新生成「创建周反馈洞察定时作业」草案');
  });

  it('renders and confirms assistant analysis drafts from the draft card', async () => {
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
              conversation_id: 'conversation_analysis_draft',
              latency_ms: 128,
              message: {
                content: '我已生成一个知识库巡检分析草案。',
                id: 'assistant_message_analysis_draft',
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'knowledge_base_inspection_draft',
                    items: [
                      {
                        action: 'create_analysis_draft',
                        client_draft_id: 'assistant_draft_knowledge_base_inspection',
                        draft_id: 'assistant_action_draft_analysis',
                        payload: {
                          analysis_type: 'knowledge_base_inspection',
                          findings: [{ title: '旧版发布检查清单', type: 'index_failed' }],
                          source_module: 'knowledge',
                          summary: { index_failed_document_count: 1 },
                          title: '知识库巡检',
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        server_draft_id: 'assistant_action_draft_analysis',
                        status: 'pending',
                        title: '知识库巡检',
                        wizard_steps: [
                          {
                            depends_on: ['知识文档索引', '知识沉淀候选'],
                            key: 'data_source',
                            status: 'ready',
                            summary: '读取 2 篇知识文档和 1 条待处理知识沉淀',
                            title: '数据来源',
                          },
                          {
                            depends_on: [],
                            key: 'ai_processing',
                            status: 'ready',
                            summary: '生成索引失败、权限异常、过期知识和沉淀候选巡检结论',
                            title: 'AI处理',
                          },
                          {
                            depends_on: [],
                            key: 'result_action',
                            status: 'ready',
                            summary: '确认后写入助手分析结果并提供追踪入口',
                            title: '结果动作',
                          },
                          {
                            depends_on: [],
                            key: 'schedule',
                            status: 'skipped',
                            summary: '一次性分析草案，不创建定时调度',
                            title: '调度策略',
                          },
                          {
                            depends_on: [],
                            key: 'confirm',
                            status: 'pending',
                            summary: '等待人工确认后归档分析结果',
                            title: '确认执行',
                          },
                        ],
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
      if (input === '/api/assistant/action-drafts/assistant_action_draft_analysis/confirm') {
        expect(init?.method).toBe('POST');
        return new Response(
          JSON.stringify({
            data: {
              draft: {
                action: 'create_analysis_draft',
                id: 'assistant_action_draft_analysis',
                payload: {},
                status: 'confirmed',
                title: '知识库巡检',
              },
              run: {
                action: 'create_analysis_draft',
                draft_id: 'assistant_action_draft_analysis',
                id: 'assistant_action_run_analysis',
                result_id: 'assistant_action_draft_analysis',
                result_type: 'assistant_analysis',
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
      target: { value: '请生成知识库巡检草案' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('我已生成一个知识库巡检分析草案。')).toBeInTheDocument();
    expect(screen.getByText('确认前不会写入分析结果')).toBeInTheDocument();
    expect(screen.getByText('分析类型')).toBeInTheDocument();
    expect(screen.getByText('knowledge_base_inspection')).toBeInTheDocument();
    expect(screen.getByText('摘要指标')).toBeInTheDocument();
    expect(screen.getByText('{"index_failed_document_count":1}')).toBeInTheDocument();
    expect(screen.getByText('配置向导')).toBeInTheDocument();
    expect(screen.getByText('一次性分析草案，不创建定时调度')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: '应用到定时作业表单' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /确认创建/ }));

    expect(await screen.findByText('已应用')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '打开分析结果' })).toHaveAttribute(
      'href',
      '/assistant?draft_id=assistant_action_draft_analysis',
    );
  });

  it('renders and confirms AI capability prerequisite drafts from the draft card', async () => {
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
              conversation_id: 'conversation_ai_capability_drafts',
              latency_ms: 18,
              message: {
                content: '我已生成 2 个可确认的 AI 能力草案。',
                id: 'assistant_message_ai_capability_drafts',
                role: 'assistant',
                tool_results: [
                  {
                    intent: 'code_inspection_setup_draft',
                    items: [
                      {
                        action: 'create_ai_skill',
                        client_draft_id: 'assistant_draft_code_inspection_ai_skill',
                        draft_id: 'assistant_action_draft_skill',
                        payload: {
                          code: 'code_inspection_analysis',
                          name: '代码巡检分析 Skill',
                          prompt_template: '请归一化代码扫描结果并输出风险摘要。',
                          required_context: ['code_repository_inspection'],
                          risk_level: 'medium',
                          status: 'active',
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        server_draft_id: 'assistant_action_draft_skill',
                        status: 'pending',
                        title: '代码巡检分析 Skill',
                      },
                      {
                        action: 'create_ai_agent',
                        client_draft_id: 'assistant_draft_code_inspection_ai_agent',
                        draft_id: 'assistant_action_draft_agent',
                        payload: {
                          brain_app_id: 'rd_brain',
                          code: 'code_inspection_agent',
                          default_skill_ids: ['assistant_draft_code_inspection_ai_skill'],
                          model_gateway_config_id: 'model_gateway_default',
                          name: '代码巡检 AI角色',
                          system_prompt: '你负责代码仓库质量、安全和规范巡检。',
                          status: 'active',
                        },
                        requires_confirmation: true,
                        risk_level: 'medium',
                        server_draft_id: 'assistant_action_draft_agent',
                        status: 'pending',
                        title: '代码巡检 AI角色',
                      },
                    ],
                    summary: { draft_count: 2, requires_confirmation: true },
                    tool: 'assistant.action_draft',
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
      if (input === '/api/assistant/action-drafts/assistant_action_draft_skill/confirm') {
        expect(init?.method).toBe('POST');
        return new Response(
          JSON.stringify({
            data: {
              draft: {
                action: 'create_ai_skill',
                id: 'assistant_action_draft_skill',
                payload: {},
                status: 'confirmed',
                title: '代码巡检分析 Skill',
              },
              run: {
                action: 'create_ai_skill',
                draft_id: 'assistant_action_draft_skill',
                id: 'assistant_action_run_skill',
                result_id: 'skill_001',
                result_type: 'ai_skill',
                status: 'succeeded',
              },
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      if (input === '/api/assistant/action-drafts/assistant_action_draft_agent/confirm') {
        expect(init?.method).toBe('POST');
        return new Response(
          JSON.stringify({
            data: {
              draft: {
                action: 'create_ai_agent',
                id: 'assistant_action_draft_agent',
                payload: {},
                status: 'confirmed',
                title: '代码巡检 AI角色',
              },
              run: {
                action: 'create_ai_agent',
                draft_id: 'assistant_action_draft_agent',
                id: 'assistant_action_run_agent',
                result_id: 'agent_001',
                result_type: 'ai_agent',
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
      target: { value: '帮我配置 AI 代码巡检定时作业草案' },
    });
    fireEvent.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findAllByText('代码巡检分析 Skill')).toHaveLength(2);
    expect(screen.getByText('Prompt 模板')).toBeInTheDocument();
    expect(screen.getByText('请归一化代码扫描结果并输出风险摘要。')).toBeInTheDocument();
    expect(screen.getAllByText('代码巡检 AI角色')).toHaveLength(2);
    expect(screen.getByText('系统 Prompt')).toBeInTheDocument();
    expect(screen.getByText('你负责代码仓库质量、安全和规范巡检。')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: /确认创建/ })[0]);

    expect(await screen.findByRole('link', { name: '打开 Skill' })).toHaveAttribute(
      'href',
      '/tasks/ai-capabilities?skill_id=skill_001',
    );

    fireEvent.click(screen.getAllByRole('button', { name: /确认创建/ })[0]);

    expect(await screen.findByRole('link', { name: '打开 AI角色' })).toHaveAttribute(
      'href',
      '/tasks/ai-capabilities?agent_id=agent_001',
    );
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

    fireEvent.click(screen.getByRole('button', { name: '查看详情' }));

    const detailDialog = await screen.findByRole('dialog', { name: /草案详情/ });
    expect(within(detailDialog).getByText('草案状态')).toBeInTheDocument();
    expect(within(detailDialog).getByText('待确认')).toBeInTheDocument();
    expect(within(detailDialog).getByText('Payload')).toBeInTheDocument();
    expect(detailDialog).toHaveTextContent('"job_type": "user_feedback_insight_extract"');
    expect(within(detailDialog).getByText('字段差异')).toBeInTheDocument();
    expect(detailDialog).toHaveTextContent('名称');
    expect(detailDialog).toHaveTextContent('- -> 缺少配置的反馈洞察作业');
    expect(within(detailDialog).getByText('校验问题')).toBeInTheDocument();
    expect(detailDialog).toHaveTextContent('cron_expression is required');
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
                        dependencies: [],
                        description: '选择或 @ 一个已规划需求后，生成可确认的产品详细设计研发任务草案。',
                        draft_action: 'create_rd_task',
                        prompt: '我要新增研发任务，请先让我 @需求 后生成产品详细设计任务草案',
                        title: '研发任务',
                        type: 'rd_task',
                        wizard_steps: ['选择需求', '产品/版本', '任务类型', '确认创建'],
                      },
                      {
                        dependencies: ['数据连接', 'AI能力', '结果动作'],
                        description: '按数据来源、AI处理、结果动作和调度策略生成可确认的定时作业草案。',
                        draft_action: 'create_scheduled_job',
                        prompt: '帮我新增定时作业，先按数据来源、AI处理、结果动作和调度策略生成草案',
                        title: '定时作业',
                        type: 'scheduled_job',
                        wizard_steps: ['数据来源', 'AI处理', '结果动作', '调度策略', '确认执行'],
                      },
                      {
                        dependencies: ['插件连接'],
                        description: '为 GitHub、GitLab、邮箱等插件生成结果动作草案，确认前不写入真实动作。',
                        draft_action: 'create_plugin_action',
                        prompt: '帮我新增插件动作，先生成可确认的动作草案',
                        title: '插件动作',
                        type: 'plugin_action',
                        wizard_steps: ['插件', '连接', '请求配置', '结果映射', '确认创建'],
                      },
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
                      option_count: 5,
                      wizard_steps: ['数据来源', 'AI处理', '结果动作', '调度策略', '确认执行'],
                    },
                    tool: 'assistant.task_creation_guide',
                  },
                ],
              },
              model: 'assistant-deterministic',
              suggestions: [
                '新增研发任务',
                '新增定时作业',
                '新增插件动作',
                '配置代码巡检定时作业',
                '配置每周用户反馈洞察定时作业',
              ],
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
    expect(screen.getByText('研发任务')).toBeInTheDocument();
    expect(screen.getByText('定时作业')).toBeInTheDocument();
    expect(screen.getByText('插件动作')).toBeInTheDocument();
    expect(screen.getByText('代码巡检')).toBeInTheDocument();
    expect(screen.getByText('反馈洞察')).toBeInTheDocument();
    expect(screen.getByText('依赖：数据连接、AI能力、结果动作')).toBeInTheDocument();
    expect(screen.getByText('依赖：插件连接')).toBeInTheDocument();
    expect(screen.getByText('依赖：GitHub/GitLab 连接、代码巡检动作')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '新增定时作业' }));
    expect(assistantInput).toHaveValue('新增定时作业');
    fireEvent.change(assistantInput, { target: { value: '' } });
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
