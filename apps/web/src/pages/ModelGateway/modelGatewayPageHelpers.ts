import type { SorterResult } from 'antd/es/table/interface';

import type { ManagementListQuery } from '../../components/ManagementListPage';
import type { ModelGatewayConfigRecord } from '../../data/management';
import type {
  ModelGatewayConfigListQuery,
  ModelGatewayConfigTestResult,
  ModelGatewayLogRecord,
} from '../../services/aiBrain';

export type ModelGatewayFormValues = {
  api_key?: string;
  base_url: string;
  default_chat_model: string;
  default_embedding_model?: string;
  embedding_api_key?: string;
  embedding_base_url?: string;
  embedding_connection_mode: 'custom' | 'disabled' | 'reuse_chat';
  embedding_dimension?: number;
  is_default: boolean;
  max_retries: number;
  name: string;
  provider: string;
  status: ModelGatewayConfigRecord['status'];
  test_target: 'chat' | 'chat_and_embedding' | 'embedding';
  timeout_seconds: number;
};

export const TEST_TARGET_FIELDS: Record<ModelGatewayFormValues['test_target'], (keyof ModelGatewayFormValues)[]> = {
  chat: ['name', 'provider', 'base_url', 'api_key', 'default_chat_model', 'timeout_seconds', 'status', 'test_target'],
  chat_and_embedding: [
    'name',
    'provider',
    'base_url',
    'api_key',
    'default_chat_model',
    'default_embedding_model',
    'timeout_seconds',
    'status',
    'test_target',
  ],
  embedding: ['name', 'provider', 'default_embedding_model', 'timeout_seconds', 'status', 'test_target'],
};

export const chatModelOptions = ['gpt-4.1', 'gpt-4.1-mini', 'gpt-5', 'gpt-5.5', 'codex-auto-review'].map((value) => ({
  value,
}));

export const embeddingModelOptions = ['text-embedding-3-small', 'text-embedding-3-large', 'bge-m3'].map((value) => ({
  value,
}));

export const embeddingModeLabels: Record<ModelGatewayFormValues['embedding_connection_mode'], string> = {
  custom: '单独配置',
  disabled: '禁用',
  reuse_chat: '复用 Chat',
};

const modelGatewaySortFieldMap: Record<string, string> = {
  baseUrl: 'base_url',
  defaultChatModel: 'default_chat_model',
  defaultEmbeddingModel: 'default_embedding_model',
  embeddingConnectionMode: 'embedding_connection_mode',
  id: 'id',
  isDefault: 'is_default',
  name: 'name',
  provider: 'provider',
  status: 'status',
};

const modelGatewayLogSortFieldMap: Record<string, string> = {
  aiTaskId: 'ai_task_id',
  createdAt: 'created_at',
  id: 'id',
  latencyMs: 'latency_ms',
  model: 'model',
  provider: 'provider',
  purpose: 'purpose',
  status: 'status',
};

export function formatDuration(value?: number) {
  return typeof value === 'number' && Number.isFinite(value) ? `${Math.max(0, value)}ms` : '-';
}

function normalizeFilterText(value: unknown): string | undefined {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed || undefined;
}

export function buildModelGatewayListQuery(query: ManagementListQuery): ModelGatewayConfigListQuery {
  const filters = query.filters ?? {};
  return {
    defaultChatModel: normalizeFilterText(filters.defaultChatModel),
    defaultEmbeddingModel: normalizeFilterText(filters.defaultEmbeddingModel),
    embeddingConnectionMode: normalizeFilterText(filters.embeddingConnectionMode),
    isDefault: normalizeFilterText(filters.isDefault),
    name: normalizeFilterText(filters.name),
    page: query.page,
    pageSize: query.pageSize,
    provider: normalizeFilterText(filters.provider),
    sortField: query.sortField ? (modelGatewaySortFieldMap[query.sortField] ?? query.sortField) : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(filters.status),
  };
}

export function formatTestStatus(
  result: ModelGatewayConfigTestResult['chat'] | ModelGatewayConfigTestResult['embedding'],
) {
  if (result.status === 'skipped') {
    return '跳过';
  }
  return result.ok ? '成功' : '失败';
}

export function formatTokenSummary(tokens: Record<string, unknown>) {
  const preferredKeys = ['total_tokens', 'prompt_tokens', 'completion_tokens', 'input_tokens', 'output_tokens'];
  const values = preferredKeys
    .map((key) => [key, tokens[key]] as const)
    .filter(([, value]) => typeof value === 'number' || typeof value === 'string');
  if (values.length > 0) {
    return values.map(([key, value]) => `${key}: ${value}`).join(' / ');
  }
  const fallback = Object.entries(tokens)
    .filter(([, value]) => typeof value === 'number' || typeof value === 'string')
    .slice(0, 3);
  return fallback.length > 0 ? fallback.map(([key, value]) => `${key}: ${value}`).join(' / ') : '-';
}

export function resolveModelGatewayLogSorter(
  sorter: SorterResult<ModelGatewayLogRecord> | SorterResult<ModelGatewayLogRecord>[],
) {
  const activeSorter = Array.isArray(sorter) ? sorter.find((item) => item.order) : sorter;
  if (!activeSorter?.order) {
    return {
      sortField: 'created_at',
      sortOrder: 'descend' as const,
    };
  }
  const rawField = String(activeSorter.columnKey ?? activeSorter.field ?? '');
  return {
    sortField: modelGatewayLogSortFieldMap[rawField] ?? rawField,
    sortOrder: activeSorter.order,
  };
}
