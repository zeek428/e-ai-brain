import { formatDisplayDateTime } from '../utils/dateTime';
import {
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
} from './apiClient';
import type { ListResponse, RemoteListPerformance } from './apiClient';
import { requireAccessToken } from './authClient';

type RemoteSortOrder = 'ascend' | 'descend';

type RemoteListQuery = {
  page?: number;
  pageSize?: number;
  sortField?: string;
  sortOrder?: RemoteSortOrder;
};

type RemoteListResult<Row> = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: Row[];
  total: number;
};

type OperationalMetricListQuery = RemoteListQuery & {
  category?: string;
  name?: string;
  status?: string;
};

type FlexibleListItem = Record<string, unknown> & {
  created_at?: string;
  id?: string;
  status?: string;
  updated_at?: string;
};

function formatListDate(value?: string) {
  return formatDisplayDateTime(value);
}

function normalizeObjectRecord(value: unknown): Record<string, unknown> | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  return value as Record<string, unknown>;
}

function formatUnknownValue(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  if (Array.isArray(value)) {
    return value.map(formatUnknownValue).join(', ');
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

function firstKnownValue(item: FlexibleListItem, keys: string[]) {
  for (const key of keys) {
    const value = item[key];
    if (value !== null && value !== undefined && value !== '') {
      return value;
    }
  }
  return undefined;
}

export type OperationalMetricRecord = {
  category: string;
  id: string;
  name: string;
  status: string;
  updatedAt: string;
  value: string;
};

export type GitLabDailyCodeMetricCreatePayload = {
  active_author_count?: number;
  additions?: number;
  author_metrics?: Array<Record<string, unknown>>;
  changed_files?: number;
  commit_count?: number;
  deletions?: number;
  merge_request_count?: number;
  metric_date: string;
  product_id: string;
  quality_score?: number;
  repository_id: string;
  risk_count?: number;
  source_channel?: string;
  status?: string;
};

export type JenkinsReleaseCreatePayload = {
  build_id: string;
  build_number?: number;
  commit_sha?: string;
  deployed_at?: string;
  duration_seconds?: number;
  environment?: string;
  failure_reason?: string;
  job_name: string;
  product_id: string;
  source_channel?: string;
  started_at?: string;
  status?: string;
  trigger_actor?: string;
  version_id: string;
};

export type OnlineLogMetricCreatePayload = {
  anomaly_summary?: string;
  core_event_count?: number;
  environment?: string;
  error_count?: number;
  module_code?: string;
  p95_latency_ms?: number;
  p99_latency_ms?: number;
  product_id: string;
  request_count?: number;
  source_channel?: string;
  status?: string;
  top_errors?: Record<string, unknown>[];
  window_end: string;
  window_start: string;
};

export type CollectorRunRecord = {
  collectorType: string;
  createdBy?: string;
  errorMessage?: string;
  finishedAt?: string;
  id: string;
  payloadSummary: Record<string, unknown>;
  productId?: string;
  recordsImported: number;
  sourceSystem: string;
  startedAt: string;
  status: string;
  updatedAt: string;
};

export type CollectorRunCreatePayload = {
  collector_type: string;
  error_message?: string;
  payload_summary?: Record<string, unknown>;
  product_id?: string;
  records_imported?: number;
  source_system: string;
  started_at?: string;
  status?: string;
};

export type CollectorRunPatchPayload = {
  error_message?: string;
  finished_at?: string;
  payload_summary?: Record<string, unknown>;
  records_imported?: number;
  status?: string;
};

export type PendingAttributionItem = {
  collectorRunId?: string;
  confidence?: number;
  createdAt: string;
  createdBy?: string;
  id: string;
  rawPayload: Record<string, unknown>;
  rawSubjectId?: string;
  resolutionAction?: string;
  resolutionNote?: string;
  resolvedAt?: string;
  resolvedBy?: string;
  resolvedModuleCode?: string;
  resolvedProductId?: string;
  resolvedRequirementId?: string;
  resolvedSubjectId?: string;
  resolvedSubjectType?: string;
  sourceSystem: string;
  sourceType: string;
  status: string;
  suggestedModuleCode?: string;
  suggestedProductId?: string;
  summary: string;
  updatedAt: string;
};

export type PendingAttributionCreatePayload = {
  collector_run_id?: string;
  confidence?: number;
  raw_payload?: Record<string, unknown>;
  raw_subject_id?: string;
  source_system: string;
  source_type: string;
  suggested_module_code?: string;
  suggested_product_id?: string;
  summary: string;
};

export type PendingAttributionResolvePayload = {
  resolution_action: string;
  resolution_note?: string;
  resolved_module_code?: string;
  resolved_product_id?: string;
  resolved_requirement_id?: string;
  resolved_subject_id?: string;
  resolved_subject_type?: string;
};

export type PendingAttributionFilters = {
  collector_run_id?: string;
  resolved_product_id?: string;
  source_type?: string;
  status?: string;
};

function mapOperationalMetrics(
  category: string,
  items: FlexibleListItem[],
): OperationalMetricRecord[] {
  return items.map((item, index) => ({
    category,
    id: formatUnknownValue(item.id ?? `${category}-${index}`),
    name: formatUnknownValue(
      firstKnownValue(item, [
        'name',
        'metric_name',
        'repository_name',
        'release_name',
        'title',
        'job_name',
        'build_id',
        'metric_date',
        'environment',
        'window_start',
      ]),
    ),
    status: formatUnknownValue(item.status),
    updatedAt: formatListDate(
      formatUnknownValue(firstKnownValue(item, ['updated_at', 'created_at', 'observed_at', 'date'])),
    ),
    value: formatUnknownValue(
      firstKnownValue(item, [
        'value',
        'count',
        'score',
        'summary',
        'commit_count',
        'build_id',
        'duration_seconds',
        'error_rate',
        'request_count',
        'p95_latency_ms',
      ]),
    ),
  }));
}

function mapOperationalMetricRecord(item: FlexibleListItem, index: number): OperationalMetricRecord {
  return {
    category: formatUnknownValue(item.category),
    id: formatUnknownValue(item.id ?? `operational-metric-${index}`),
    name: formatUnknownValue(
      firstKnownValue(item, [
        'name',
        'metric_name',
        'repository_name',
        'release_name',
        'title',
        'job_name',
        'build_id',
        'metric_date',
        'environment',
        'window_start',
      ]),
    ),
    status: formatUnknownValue(item.status),
    updatedAt: formatListDate(
      formatUnknownValue(firstKnownValue(item, ['updated_at', 'created_at', 'observed_at', 'date'])),
    ),
    value: formatUnknownValue(
      firstKnownValue(item, [
        'value',
        'count',
        'score',
        'summary',
        'commit_count',
        'quality_score',
        'build_id',
        'duration_seconds',
        'error_rate',
        'request_count',
        'p95_latency_ms',
      ]),
    ),
  };
}

export async function fetchDevopsMetrics(): Promise<OperationalMetricRecord[]> {
  const token = requireAccessToken();
  const [gitlabMetrics, jenkinsReleases, onlineLogs] = await Promise.all([
    apiRequest<ListResponse<FlexibleListItem>>('/api/devops/gitlab/daily-code-metrics', { token }),
    apiRequest<ListResponse<FlexibleListItem>>('/api/devops/jenkins/releases', { token }),
    apiRequest<ListResponse<FlexibleListItem>>('/api/ops/online-log-metrics', { token }),
  ]);

  return [
    ...mapOperationalMetrics('GitLab 指标', gitlabMetrics.items),
    ...mapOperationalMetrics('Jenkins 发布', jenkinsReleases.items),
    ...mapOperationalMetrics('线上日志', onlineLogs.items),
  ];
}

export async function fetchDevopsMetricList(
  query: OperationalMetricListQuery = {},
): Promise<RemoteListResult<OperationalMetricRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'category', query.category);
  appendQueryParam(params, 'name', query.name);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const path = queryString
    ? `/api/devops/operational-metrics?${queryString}`
    : '/api/devops/operational-metrics';
  const metrics = await apiRequest<ListResponse<FlexibleListItem>>(path, { token });

  return {
    page: metrics.page ?? query.page ?? 1,
    pageSize: metrics.page_size ?? query.pageSize ?? 10,
    performance: metrics.performance,
    rows: metrics.items.map(mapOperationalMetricRecord),
    total: metrics.total,
  };
}

export async function createGitLabDailyCodeMetric(
  payload: GitLabDailyCodeMetricCreatePayload,
): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>('/api/devops/gitlab/daily-code-metrics', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function createJenkinsRelease(
  payload: JenkinsReleaseCreatePayload,
): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>('/api/devops/jenkins/releases', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function createOnlineLogMetric(
  payload: OnlineLogMetricCreatePayload,
): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>('/api/ops/online-log-metrics', {
    body: payload,
    method: 'POST',
    token,
  });
}

function mapCollectorRun(item: FlexibleListItem): CollectorRunRecord {
  const payloadSummary = normalizeObjectRecord(item.payload_summary) ?? {};
  return {
    collectorType: formatUnknownValue(item.collector_type),
    createdBy: formatUnknownValue(item.created_by),
    errorMessage: formatUnknownValue(item.error_message),
    finishedAt: formatListDate(formatUnknownValue(item.finished_at)),
    id: formatUnknownValue(item.id),
    payloadSummary,
    productId: formatUnknownValue(item.product_id),
    recordsImported: Number(item.records_imported ?? 0),
    sourceSystem: formatUnknownValue(item.source_system),
    startedAt: formatListDate(formatUnknownValue(item.started_at)),
    status: formatUnknownValue(item.status),
    updatedAt: formatListDate(formatUnknownValue(item.updated_at ?? item.created_at)),
  };
}

export async function fetchCollectorRuns(): Promise<CollectorRunRecord[]> {
  const token = requireAccessToken();
  const runs = await apiRequest<ListResponse<FlexibleListItem>>('/api/collectors/runs', { token });
  return runs.items.map(mapCollectorRun);
}

export async function createCollectorRun(
  payload: CollectorRunCreatePayload,
): Promise<CollectorRunRecord> {
  const token = requireAccessToken();
  const run = await apiRequest<FlexibleListItem>('/api/collectors/runs', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapCollectorRun(run);
}

export async function updateCollectorRun(
  runId: string,
  payload: CollectorRunPatchPayload,
): Promise<CollectorRunRecord> {
  const token = requireAccessToken();
  const run = await apiRequest<FlexibleListItem>(`/api/collectors/runs/${runId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
  return mapCollectorRun(run);
}

function emptyToUndefined(value: string) {
  return value === '-' ? undefined : value;
}

function mapPendingAttributionItem(item: FlexibleListItem): PendingAttributionItem {
  const rawConfidence = item.confidence;
  const confidence =
    typeof rawConfidence === 'number'
      ? rawConfidence
      : rawConfidence === null || rawConfidence === undefined || rawConfidence === ''
        ? undefined
        : Number.isFinite(Number(rawConfidence))
          ? Number(rawConfidence)
        : undefined;
  return {
    collectorRunId: emptyToUndefined(formatUnknownValue(item.collector_run_id)),
    confidence,
    createdAt: formatListDate(formatUnknownValue(item.created_at)),
    createdBy: emptyToUndefined(formatUnknownValue(item.created_by)),
    id: formatUnknownValue(item.id),
    rawPayload: normalizeObjectRecord(item.raw_payload) ?? {},
    rawSubjectId: emptyToUndefined(formatUnknownValue(item.raw_subject_id)),
    resolutionAction: emptyToUndefined(formatUnknownValue(item.resolution_action)),
    resolutionNote: emptyToUndefined(formatUnknownValue(item.resolution_note)),
    resolvedAt: emptyToUndefined(formatListDate(formatUnknownValue(item.resolved_at))),
    resolvedBy: emptyToUndefined(formatUnknownValue(item.resolved_by)),
    resolvedModuleCode: emptyToUndefined(formatUnknownValue(item.resolved_module_code)),
    resolvedProductId: emptyToUndefined(formatUnknownValue(item.resolved_product_id)),
    resolvedRequirementId: emptyToUndefined(formatUnknownValue(item.resolved_requirement_id)),
    resolvedSubjectId: emptyToUndefined(formatUnknownValue(item.resolved_subject_id)),
    resolvedSubjectType: emptyToUndefined(formatUnknownValue(item.resolved_subject_type)),
    sourceSystem: formatUnknownValue(item.source_system),
    sourceType: formatUnknownValue(item.source_type),
    status: formatUnknownValue(item.status),
    suggestedModuleCode: emptyToUndefined(formatUnknownValue(item.suggested_module_code)),
    suggestedProductId: emptyToUndefined(formatUnknownValue(item.suggested_product_id)),
    summary: formatUnknownValue(item.summary),
    updatedAt: formatListDate(formatUnknownValue(item.updated_at ?? item.created_at)),
  };
}

function pendingAttributionQuery(filters: PendingAttributionFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  const query = params.toString();
  return query ? `/api/attribution/pending-items?${query}` : '/api/attribution/pending-items';
}

export async function fetchPendingAttributionItems(
  filters: PendingAttributionFilters = {},
): Promise<PendingAttributionItem[]> {
  const token = requireAccessToken();
  const items = await apiRequest<ListResponse<FlexibleListItem>>(
    pendingAttributionQuery(filters),
    { token },
  );
  return items.items.map(mapPendingAttributionItem);
}

export async function createPendingAttributionItem(
  payload: PendingAttributionCreatePayload,
): Promise<PendingAttributionItem> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>('/api/attribution/pending-items', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapPendingAttributionItem(item);
}

export async function resolvePendingAttributionItem(
  itemId: string,
  payload: PendingAttributionResolvePayload,
): Promise<PendingAttributionItem> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>(
    `/api/attribution/pending-items/${itemId}/resolve`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return mapPendingAttributionItem(item);
}
