import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import ModelGatewayPage from '../src/pages/ModelGateway';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  void message.destroy();
  notification.destroy();
  Modal.destroyAll();
});

describe('ModelGatewayPage', () => {
  it('manages model gateway configs without exposing api keys', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (String(input).startsWith('/api/system/model-gateway-configs?') && init?.method === 'GET') {
        expect(String(input)).toContain('page=1');
        expect(String(input)).toContain('page_size=10');
        expect(String(input)).toContain('sort_by=name');
        expect(String(input)).toContain('sort_order=asc');
        return jsonResponse({
          data: {
            items: [
              {
                api_key_configured: true,
                base_url: 'https://api.example.com/v1',
                default_chat_model: 'gpt-4.1',
                default_embedding_model: 'text-embedding-3-large',
                id: 'model_config_default',
                is_default: true,
                max_retries: 1,
                name: '默认模型网关',
                provider: 'openai_compatible',
                status: 'active',
                timeout_seconds: 60,
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      if (String(input).startsWith('/api/model-gateway/logs?') && init?.method === 'GET') {
        expect(String(input)).toContain('page=1');
        expect(String(input)).toContain('page_size=5');
        expect(String(input)).toContain('sort_by=created_at');
        expect(String(input)).toContain('sort_order=desc');
        return jsonResponse({
          data: {
            items: [
              {
                ai_task_id: 'task_model_gateway_001',
                created_at: '2026-06-26T07:01:02+00:00',
                error: null,
                id: 'model_gateway_log_001',
                latency_ms: 42,
                model: 'gpt-4.1',
                model_gateway_config_id: 'model_config_default',
                provider: 'openai_compatible',
                purpose: 'assistant_chat',
                status: 'succeeded',
                tokens: { completion_tokens: 8, prompt_tokens: 13, total_tokens: 21 },
              },
            ],
            page: 1,
            page_size: 5,
            performance: {
              duration_ms: 9,
              p95_target_ms: 400,
              result_count: 1,
              slow: false,
              slow_threshold_ms: 400,
              total: 1,
            },
            total: 1,
          },
        });
      }
      if (input === '/api/system/model-gateway-configs') {
        if (init?.method === 'POST') {
          expect(JSON.parse(String(init.body))).toMatchObject({
            api_key: 'sk-live-secret',
            base_url: 'https://api.example.com/v1',
            default_chat_model: 'gpt-4.1',
            default_embedding_model: 'text-embedding-3-large',
            is_default: true,
            max_retries: 2,
            name: '新模型网关',
            provider: 'openai_compatible',
            status: 'active',
            timeout_seconds: 90,
          });
          return jsonResponse({
            data: {
              api_key_configured: true,
              base_url: 'https://api.example.com/v1',
              default_chat_model: 'gpt-4.1',
              default_embedding_model: 'text-embedding-3-large',
              id: 'model_config_new',
              is_default: true,
              max_retries: 2,
              name: '新模型网关',
              provider: 'openai_compatible',
              status: 'active',
              timeout_seconds: 90,
            },
          });
        }
      }
      if (input === '/api/system/model-gateway-configs/test') {
        expect(JSON.parse(String(init?.body))).toMatchObject({
          api_key: 'sk-live-secret',
          base_url: 'https://api.example.com/v1',
          default_chat_model: 'gpt-4.1',
          default_embedding_model: 'text-embedding-3-large',
          name: '新模型网关',
          provider: 'openai_compatible',
          status: 'active',
          test_target: 'chat',
          timeout_seconds: 90,
        });
        return jsonResponse({
          data: {
            chat: { latency_ms: 18, model: 'gpt-4.1', ok: true, status: 'succeeded' },
            embedding: {
              model: 'text-embedding-3-large',
              ok: true,
              status: 'skipped',
            },
            ok: true,
            test_target: 'chat',
          },
        });
      }
      if (input === '/api/system/model-gateway-configs/model_config_default') {
        if (init?.method === 'PATCH') {
          const body = JSON.parse(String(init.body));
          expect(body).toMatchObject({
            base_url: 'https://api.example.com/v1',
            default_chat_model: 'gpt-4.1-mini',
            default_embedding_model: 'text-embedding-3-large',
            is_default: true,
            max_retries: 1,
            name: '默认模型网关',
            provider: 'openai_compatible',
            status: 'active',
            timeout_seconds: 60,
          });
          expect(body).not.toHaveProperty('api_key');
          return jsonResponse({
            data: {
              api_key_configured: true,
              base_url: 'https://api.example.com/v1',
              default_chat_model: 'gpt-4.1-mini',
              default_embedding_model: 'text-embedding-3-large',
              id: 'model_config_default',
              is_default: true,
              max_retries: 1,
              name: '默认模型网关',
              provider: 'openai_compatible',
              status: 'active',
              timeout_seconds: 60,
            },
          });
        }
        if (init?.method === 'DELETE') {
          return jsonResponse({ data: { deleted: true, id: 'model_config_default' } });
        }
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<ModelGatewayPage />);

    expect(await screen.findByText('默认模型网关')).toBeInTheDocument();
    expect(await screen.findByText('model_gateway_log_001')).toBeInTheDocument();
    expect(screen.getByText('查询 9ms')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '调用诊断' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=model_gateway_log_001&source_type=model_gateway_log',
    );
    expect(screen.getByText('模型网关配置')).toBeInTheDocument();
    expect(screen.getByText('已配置')).toBeInTheDocument();
    expect(screen.queryByText('sk-live-secret')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /新增配置/ }));
    let dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('配置名称'), { target: { value: '新模型网关' } });
    fireEvent.change(within(dialog).getByLabelText('Provider'), { target: { value: 'openai_compatible' } });
    fireEvent.change(within(dialog).getByLabelText('Base URL'), { target: { value: 'https://api.example.com/v1' } });
    fireEvent.change(within(dialog).getByLabelText('API Key'), { target: { value: 'sk-live-secret' } });
    fireEvent.change(within(dialog).getByLabelText('默认 Chat 模型'), { target: { value: 'gpt-4.1' } });
    fireEvent.click(within(dialog).getByLabelText('复用 Chat'));
    await waitFor(() => expect(within(dialog).getByLabelText('默认 Embedding 模型')).toBeInTheDocument());
    fireEvent.change(within(dialog).getByLabelText('默认 Embedding 模型'), {
      target: { value: 'text-embedding-3-large' },
    });
    fireEvent.change(within(dialog).getByLabelText('超时秒数'), { target: { value: '90' } });
    fireEvent.change(within(dialog).getByLabelText('最大重试'), { target: { value: '2' } });
    fireEvent.click(within(dialog).getByLabelText('默认配置'));
    fireEvent.click(within(dialog).getByLabelText('仅 Chat'));
    fireEvent.click(within(dialog).getByRole('button', { name: /测试连接/ }));

    expect(await within(dialog).findByText(/Chat 成功/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Embedding 跳过/)).toBeInTheDocument();
    expect(screen.queryByText('sk-live-secret')).not.toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/system/model-gateway-configs',
        'POST',
      ]),
    );

    fireEvent.click(screen.getAllByRole('button', { name: /编辑/ })[0]);
    dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('默认 Chat 模型'), { target: { value: 'gpt-4.1-mini' } });
    fireEvent.click(within(dialog).getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toContainEqual([
        '/api/system/model-gateway-configs/model_config_default',
        'PATCH',
      ]),
    );
  }, 10000);
});
