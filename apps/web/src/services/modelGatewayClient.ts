import type { ModelGatewayConfigRecord } from '../data/management';
import {
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
} from './apiClient';
import type {
  ListResponse,
  RemoteListPerformance,
} from './apiClient';
import { requireAccessToken } from './authClient';

type RemoteSortOrder = 'ascend' | 'descend';

type ModelGatewayRemoteListQuery = {
  page?: number;
  pageSize?: number;
  sortField?: string;
  sortOrder?: RemoteSortOrder;
};

type ModelGatewayRemoteListResult<Row> = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: Row[];
  total: number;
};

export type ModelGatewayConfigListQuery = ModelGatewayRemoteListQuery & {
  defaultChatModel?: string;
  defaultEmbeddingModel?: string;
  embeddingConnectionMode?: string;
  isDefault?: string;
  name?: string;
  provider?: string;
  status?: string;
};

export type ModelGatewayLogQuery = ModelGatewayRemoteListQuery & {
  aiTaskId?: string;
  purpose?: string;
  status?: string;
};

export type ModelGatewayConfigMutationPayload = {
  api_key?: string;
  base_url?: string;
  config_id?: string;
  default_chat_model?: string;
  default_embedding_model?: string | null;
  embedding_api_key?: string;
  embedding_base_url?: string | null;
  embedding_connection_mode?: 'custom' | 'disabled' | 'reuse_chat';
  embedding_dimension?: number | null;
  is_default?: boolean;
  max_retries?: number;
  name?: string;
  provider?: string;
  status?: string;
  test_target?: 'chat' | 'chat_and_embedding' | 'embedding';
  timeout_seconds?: number;
};

export type ModelGatewayConfigTestResult = {
  chat: {
    error_code?: string;
    latency_ms?: number;
    model: string;
    ok: boolean;
    status: string;
  };
  embedding: {
    dimension?: number;
    error_code?: string;
    latency_ms?: number;
    model: string;
    ok: boolean;
    status: string;
  };
  ok: boolean;
  test_target?: string;
};

type ModelGatewayConfigListItem = {
  api_key_configured?: boolean;
  base_url?: string;
  default_chat_model?: string;
  default_embedding_model?: string | null;
  embedding_api_key_configured?: boolean;
  embedding_base_url?: string | null;
  embedding_connection_mode?: string;
  embedding_dimension?: number | null;
  id: string;
  is_default?: boolean;
  max_retries?: number;
  name: string;
  provider?: string;
  status?: string;
  timeout_seconds?: number;
};

type ModelGatewayLogListItem = {
  ai_task_id?: string | null;
  created_at?: string;
  error?: string | null;
  id: string;
  latency_ms?: number | null;
  model?: string;
  model_gateway_config_id?: string | null;
  provider?: string;
  purpose?: string;
  status?: string;
  tokens?: Record<string, unknown>;
  updated_at?: string;
};

export type ModelGatewayLogRecord = {
  aiTaskId?: string | null;
  createdAt?: string;
  error?: string | null;
  id: string;
  latencyMs?: number | null;
  model: string;
  modelGatewayConfigId?: string | null;
  provider: string;
  purpose: string;
  status: string;
  tokens: Record<string, unknown>;
  updatedAt?: string;
};

function normalizeModelGatewayStatus(status?: string): ModelGatewayConfigRecord['status'] {
  return status === 'inactive' ? 'inactive' : 'active';
}

function mapModelGatewayConfig(config: ModelGatewayConfigListItem): ModelGatewayConfigRecord {
  const apiKeyConfigured = Boolean(config.api_key_configured);
  const embeddingConnectionMode =
    config.embedding_connection_mode === 'custom' || config.embedding_connection_mode === 'disabled'
      ? config.embedding_connection_mode
      : 'reuse_chat';
  return {
    apiKeyConfigured,
    baseUrl: config.base_url ?? '-',
    defaultChatModel: config.default_chat_model ?? '-',
    defaultEmbeddingModel: config.default_embedding_model ?? null,
    embeddingApiKeyConfigured: Boolean(config.embedding_api_key_configured),
    embeddingBaseUrl: config.embedding_base_url ?? null,
    embeddingConnectionMode,
    embeddingDimension: config.embedding_dimension ?? null,
    id: config.id,
    isDefault: Boolean(config.is_default),
    keyStatus: apiKeyConfigured ? '已配置' : '未配置',
    maxRetries: config.max_retries ?? 0,
    name: config.name,
    provider: config.provider ?? '-',
    status: normalizeModelGatewayStatus(config.status),
    timeoutSeconds: config.timeout_seconds ?? 0,
  };
}

function mapModelGatewayLog(log: ModelGatewayLogListItem): ModelGatewayLogRecord {
  return {
    aiTaskId: log.ai_task_id ?? null,
    createdAt: log.created_at,
    error: log.error ?? null,
    id: log.id,
    latencyMs: log.latency_ms ?? null,
    model: log.model ?? '-',
    modelGatewayConfigId: log.model_gateway_config_id ?? null,
    provider: log.provider ?? '-',
    purpose: log.purpose ?? '-',
    status: log.status ?? '-',
    tokens: log.tokens && typeof log.tokens === 'object' ? log.tokens : {},
    updatedAt: log.updated_at,
  };
}

export async function fetchModelGatewayConfigList(
  query: ModelGatewayConfigListQuery = {},
): Promise<ModelGatewayRemoteListResult<ModelGatewayConfigRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'default_chat_model', query.defaultChatModel);
  appendQueryParam(params, 'default_embedding_model', query.defaultEmbeddingModel);
  appendQueryParam(params, 'embedding_connection_mode', query.embeddingConnectionMode);
  appendQueryParam(params, 'is_default', query.isDefault);
  appendQueryParam(params, 'name', query.name);
  appendQueryParam(params, 'provider', query.provider);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const configs = await apiRequest<ListResponse<ModelGatewayConfigListItem>>(
    queryString ? `/api/system/model-gateway-configs?${queryString}` : '/api/system/model-gateway-configs',
    { token },
  );
  return {
    page: configs.page ?? query.page ?? 1,
    pageSize: configs.page_size ?? query.pageSize ?? 10,
    performance: configs.performance,
    rows: configs.items.map(mapModelGatewayConfig),
    total: configs.total,
  };
}

export async function fetchModelGatewayConfigs(): Promise<ModelGatewayConfigRecord[]> {
  const token = requireAccessToken();
  const configs = await apiRequest<ListResponse<ModelGatewayConfigListItem>>(
    '/api/system/model-gateway-configs',
    { token },
  );
  return configs.items.map(mapModelGatewayConfig);
}

export async function fetchModelGatewayLogs(
  query: ModelGatewayLogQuery = {},
): Promise<ModelGatewayRemoteListResult<ModelGatewayLogRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'ai_task_id', query.aiTaskId);
  appendQueryParam(params, 'purpose', query.purpose);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const logs = await apiRequest<ListResponse<ModelGatewayLogListItem>>(
    queryString ? `/api/model-gateway/logs?${queryString}` : '/api/model-gateway/logs',
    { token },
  );
  return {
    page: logs.page ?? query.page ?? 1,
    pageSize: logs.page_size ?? query.pageSize ?? 10,
    performance: logs.performance,
    rows: logs.items.map(mapModelGatewayLog),
    total: logs.total,
  };
}

export async function createModelGatewayConfig(payload: ModelGatewayConfigMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<ModelGatewayConfigListItem>('/api/system/model-gateway-configs', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateModelGatewayConfig(
  configId: string,
  payload: ModelGatewayConfigMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<ModelGatewayConfigListItem>(`/api/system/model-gateway-configs/${configId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function testModelGatewayConfig(
  payload: ModelGatewayConfigMutationPayload,
): Promise<ModelGatewayConfigTestResult> {
  const token = requireAccessToken();
  return apiRequest<ModelGatewayConfigTestResult>('/api/system/model-gateway-configs/test', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function deleteModelGatewayConfig(configId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(
    `/api/system/model-gateway-configs/${configId}`,
    {
      method: 'DELETE',
      token,
    },
  );
}
