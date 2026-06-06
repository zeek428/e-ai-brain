import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  createModelGatewayConfig,
  deleteModelGatewayConfig,
  fetchModelGatewayConfigs,
  testModelGatewayConfig,
  updateModelGatewayConfig,
} from '../src/services/aiBrain';

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('model gateway service API mappings', () => {
  it('sends model gateway config CRUD mutations to backend APIs without plaintext in list rows', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/system/model-gateway-configs' && init?.method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                api_key_configured: true,
                base_url: 'https://api.example.com/v1',
                default_chat_model: 'gpt-4.1',
                default_embedding_model: 'text-embedding-3-large',
                id: 'model_config_api',
                is_default: true,
                max_retries: 1,
                name: '默认模型网关',
                provider: 'openai_compatible',
                status: 'active',
                timeout_seconds: 60,
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/system/model-gateway-configs' && init?.method === 'POST') {
        expect(init.body).toBe(
          JSON.stringify({
            api_key: 'sk-live-secret',
            base_url: 'https://api.example.com/v1',
            default_chat_model: 'gpt-4.1',
            default_embedding_model: 'text-embedding-3-large',
            is_default: true,
            max_retries: 1,
            name: '默认模型网关',
            provider: 'openai_compatible',
            status: 'active',
            timeout_seconds: 60,
          }),
        );
        return jsonResponse({ data: { id: 'model_config_api', status: 'active' } });
      }
      if (input === '/api/system/model-gateway-configs/model_config_api' && init?.method === 'PATCH') {
        expect(init.body).toBe(
          JSON.stringify({
            default_chat_model: 'gpt-4.1-mini',
            status: 'active',
          }),
        );
        return jsonResponse({ data: { id: 'model_config_api', status: 'active' } });
      }
      if (input === '/api/system/model-gateway-configs/model_config_api' && init?.method === 'DELETE') {
        return jsonResponse({ data: { deleted: true, id: 'model_config_api' } });
      }
      if (input === '/api/system/model-gateway-configs/test' && init?.method === 'POST') {
        expect(init.body).toBe(
          JSON.stringify({
            api_key: 'sk-live-secret',
            base_url: 'https://api.example.com/v1',
            default_chat_model: 'gpt-4.1',
            default_embedding_model: 'text-embedding-3-large',
            is_default: true,
            max_retries: 1,
            name: '默认模型网关',
            provider: 'openai_compatible',
            status: 'active',
            test_target: 'chat',
            timeout_seconds: 60,
          }),
        );
        return jsonResponse({
          data: {
            chat: { latency_ms: 8, model: 'gpt-4.1', ok: true, status: 'succeeded' },
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
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchModelGatewayConfigs()).resolves.toEqual([
      expect.objectContaining({
        apiKeyConfigured: true,
        keyStatus: '已配置',
        name: '默认模型网关',
      }),
    ]);
    await createModelGatewayConfig({
      api_key: 'sk-live-secret',
      base_url: 'https://api.example.com/v1',
      default_chat_model: 'gpt-4.1',
      default_embedding_model: 'text-embedding-3-large',
      is_default: true,
      max_retries: 1,
      name: '默认模型网关',
      provider: 'openai_compatible',
      status: 'active',
      timeout_seconds: 60,
    });
    await updateModelGatewayConfig('model_config_api', {
      default_chat_model: 'gpt-4.1-mini',
      status: 'active',
    });
    await expect(
      testModelGatewayConfig({
        api_key: 'sk-live-secret',
        base_url: 'https://api.example.com/v1',
        default_chat_model: 'gpt-4.1',
        default_embedding_model: 'text-embedding-3-large',
        is_default: true,
        max_retries: 1,
        name: '默认模型网关',
        provider: 'openai_compatible',
        status: 'active',
        test_target: 'chat',
        timeout_seconds: 60,
      }),
    ).resolves.toMatchObject({
      chat: { ok: true },
      embedding: { ok: true, status: 'skipped' },
      ok: true,
      test_target: 'chat',
    });
    await deleteModelGatewayConfig('model_config_api');

    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toEqual([
      ['/api/system/model-gateway-configs', 'GET'],
      ['/api/system/model-gateway-configs', 'POST'],
      ['/api/system/model-gateway-configs/model_config_api', 'PATCH'],
      ['/api/system/model-gateway-configs/test', 'POST'],
      ['/api/system/model-gateway-configs/model_config_api', 'DELETE'],
    ]);
  });
});
