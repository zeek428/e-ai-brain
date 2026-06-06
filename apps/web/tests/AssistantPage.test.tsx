import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import AssistantPage from '../src/pages/Assistant';
import {
  chatWithAssistant,
  fetchAssistantConversationMessages,
  fetchAssistantConversations,
} from '../src/services/aiBrain';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  void message.destroy();
  notification.destroy();
  Modal.destroyAll();
});

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
                    url: '/tasks/management?task_id=task_api',
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
      '/tasks/management?task_id=task_api',
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
                      url: '/tasks/management?task_id=task_api',
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
            url: '/tasks/management?task_id=task_api',
          },
        ],
        role: 'assistant',
        suggestions: ['查看任务中心'],
      },
    ]);
  });
});
