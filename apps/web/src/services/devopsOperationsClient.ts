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
  excludeCategory?: string;
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
  deploymentMethod?: DeploymentMethod;
  deploymentSchemeId?: string;
  environment?: string;
  executorChannel?: string;
  id: string;
  name: string;
  productId?: string;
  requirementIds?: string[];
  riskLevel?: string;
  status: string;
  updatedAt: string;
  value: string;
  versionId?: string;
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

export type DeploymentRunRecord = {
  createdAt: string;
  deploymentMethod: string;
  executionSnapshot: Record<string, unknown>;
  executorChannel: string;
  executorType: string;
  externalBuildId?: string;
  externalBuildUrl?: string;
  externalJobName?: string;
  externalQueueUrl?: string;
  failureReason?: string;
  finishedAt?: string;
  id: string;
  logUrl?: string;
  healthStatus?: string;
  operation?: string;
  pluginInvocationLogId?: string;
  runnerTaskId?: string;
  startedAt?: string;
  status: string;
  steps: DeploymentRunStepRecord[];
  updatedAt: string;
  waveNumber?: number;
  waveTotal?: number;
};

export type DeploymentRunStepRecord = {
  evidence: Record<string, unknown>;
  finishedAt?: string;
  id: string;
  sequence: number;
  startedAt?: string;
  status: string;
  stepType: string;
  summary?: string;
};

export type DeploymentDispatchEventRecord = {
  attemptCount: number;
  eventType: string;
  id: string;
  lastError?: string;
  processedAt?: string;
  status: string;
  updatedAt?: string;
};

export type DeploymentAuditEventRecord = {
  actorId?: string;
  createdAt?: string;
  eventType: string;
  id: string;
  payload: Record<string, unknown>;
};

export type DeploymentQualityGateRecord = {
  blockedReasons: string[];
  checks: Array<{
    checkType: string;
    id: string;
    source: string;
    status: string;
    summary?: string;
  }>;
  id?: string;
  status?: string;
  summary?: string;
};

export type DeploymentMethod = 'docker' | 'jenkins' | 'manual' | 'ssh';

export type DeploymentSchemeRecord = {
  code: string;
  config: Record<string, unknown>;
  deploymentMethod: DeploymentMethod;
  environment: string;
  executorChannel: string;
  id: string;
  isDefault: boolean;
  jenkinsConnectionId?: string;
  jenkinsJobName?: string;
  name: string;
  healthCheckConfig: Record<string, unknown>;
  preflightConfig: Record<string, unknown>;
  productId: string;
  rollbackConfig: Record<string, unknown>;
  rolloutStrategy: 'all_at_once' | 'batch' | 'blue_green' | 'canary';
  runnerId?: string;
  status: 'active' | 'disabled';
  targetCode?: string;
  timeoutSeconds: number;
  updatedAt?: string;
  version: number;
  waveConfig: Record<string, unknown>;
  windowEnforcement: 'disabled' | 'strict' | 'warn';
};

export type DeploymentRunnerTargetRecord = {
  code: string;
  connectivityProbeCheckedAt?: string;
  connectivityProbeStatus?: string;
  method: 'docker' | 'ssh';
  name: string;
  ready: boolean;
  runnerId: string;
  healthCheckConfigured: boolean;
  rollbackConfigured: boolean;
  supportsBlueGreen: boolean;
};

export type DeploymentJenkinsConnectionRecord = {
  environment: string;
  id: string;
  name: string;
  ready: boolean;
  status: string;
};

export type DeploymentConnectivityProbeRecord = {
  deploymentId: string;
  kind: 'jenkins' | 'runner';
  maxAgeSeconds: number;
  probe: Record<string, unknown>;
  ready: boolean;
  status: string;
  taskId?: string;
};

export type DeploymentJenkinsConnectionProbeRecord = {
  connectionId: string;
  jobName: string;
  probe: Record<string, unknown>;
};

export type DeploymentSchemeCreatePayload = {
  code: string;
  config?: Record<string, unknown>;
  deployment_method: DeploymentMethod;
  environment?: string;
  is_default?: boolean;
  jenkins_connection_id?: string;
  jenkins_job_name?: string;
  health_check_config?: Record<string, unknown>;
  name: string;
  product_id: string;
  preflight_config?: Record<string, unknown>;
  rollback_config?: Record<string, unknown>;
  rollout_strategy?: 'all_at_once' | 'batch' | 'blue_green' | 'canary';
  runner_id?: string;
  status?: 'active' | 'disabled';
  target_code?: string;
  timeout_seconds?: number;
  wave_config?: Record<string, unknown>;
  window_enforcement?: 'disabled' | 'strict' | 'warn';
};

export type DeploymentSchemeUpdatePayload = Partial<DeploymentSchemeCreatePayload> & {
  version: number;
};

export type DeploymentRunLogRecord = {
  createdAt?: string;
  level: string;
  message: string;
  source: string;
};

export type DeploymentRequestRecord = {
  auditEvents: DeploymentAuditEventRecord[];
  artifactVersion?: string;
  artifactDigest?: string;
  commitSha?: string;
  currentWave: number;
  createdAt: string;
  deploymentMethod: DeploymentMethod;
  deploymentSchemeId?: string;
  environment: string;
  executorChannel: string;
  failureReason?: string;
  finishedAt?: string;
  gateSummary: Record<string, unknown>;
  id: string;
  productId: string;
  releaseBranch?: string;
  requirementIds: string[];
  dispatchEvents: DeploymentDispatchEventRecord[];
  qualityGate?: DeploymentQualityGateRecord;
  riskLevel: string;
  rollbackPlan?: string;
  runs: DeploymentRunRecord[];
  schemeSnapshot: Record<string, unknown>;
  startedAt?: string;
  status: string;
  title: string;
  totalWaves: number;
  updatedAt: string;
  versionId: string;
  windowEnforcement?: string;
};

export type DeploymentRequestListQuery = RemoteListQuery & {
  environment?: string;
  productId?: string;
  status?: string;
  title?: string;
  versionId?: string;
};

export type DeploymentSchemeListQuery = RemoteListQuery & {
  deploymentMethod?: DeploymentMethod;
  environment?: string;
  name?: string;
  productId?: string;
  status?: 'active' | 'disabled';
};

export type DeploymentRequestCreatePayload = {
  artifact_digest?: string;
  artifact_version?: string;
  assigned_ops_user?: string;
  commit_sha?: string;
  deploy_window_end?: string;
  deploy_window_start?: string;
  deployment_scheme_id?: string;
  environment?: string;
  release_branch?: string;
  release_readiness_task_id?: string;
  requirement_ids: string[];
  risk_level?: string;
  rollback_plan?: string;
  product_id: string;
  title: string;
  version_id: string;
};

export type DeploymentStartPayload = {
  executor_type?: string;
  external_build_id?: string;
  external_job_name?: string;
  log_url?: string;
};

export type DeploymentCompletePayload = DeploymentStartPayload & {
  failure_reason?: string;
  finished_at?: string;
  status: 'failed' | 'rolled_back' | 'success';
};

export type DeploymentCancelPayload = {
  reason?: string;
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
        'environment',
        'artifact_version',
        'metric_date',
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
        'environment',
        'artifact_version',
        'requirement_ids',
        'duration_seconds',
        'error_rate',
        'request_count',
        'p95_latency_ms',
      ]),
    ),
  }));
}

function mapOperationalMetricRecord(item: FlexibleListItem, index: number): OperationalMetricRecord {
  const requirementIds = Array.isArray(item.requirement_ids)
    ? item.requirement_ids.map((value) => String(value))
    : undefined;
  return {
    category: formatUnknownValue(item.category),
    deploymentMethod: item.deployment_method
      ? deploymentMethodValue(item.deployment_method)
      : undefined,
    deploymentSchemeId: item.deployment_scheme_id ? String(item.deployment_scheme_id) : undefined,
    environment: item.environment ? String(item.environment) : undefined,
    executorChannel: item.executor_channel ? String(item.executor_channel) : undefined,
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
        'environment',
        'artifact_version',
        'metric_date',
        'window_start',
      ]),
    ),
    status: formatUnknownValue(item.status),
    productId: item.product_id ? String(item.product_id) : undefined,
    requirementIds,
    riskLevel: item.risk_level ? String(item.risk_level) : undefined,
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
        'environment',
        'artifact_version',
        'requirement_ids',
        'duration_seconds',
        'error_rate',
        'request_count',
        'p95_latency_ms',
      ]),
    ),
    versionId: item.version_id ? String(item.version_id) : undefined,
  };
}

export async function fetchDevopsMetrics(): Promise<OperationalMetricRecord[]> {
  const token = requireAccessToken();
  const [gitlabMetrics, jenkinsReleases, deploymentRequests, onlineLogs] = await Promise.all([
    apiRequest<ListResponse<FlexibleListItem>>('/api/devops/gitlab/daily-code-metrics', { token }),
    apiRequest<ListResponse<FlexibleListItem>>('/api/devops/jenkins/releases', { token }),
    apiRequest<ListResponse<FlexibleListItem>>('/api/devops/deployments', { token }),
    apiRequest<ListResponse<FlexibleListItem>>('/api/ops/online-log-metrics', { token }),
  ]);

  return [
    ...mapOperationalMetrics('GitLab 指标', gitlabMetrics.items),
    ...mapOperationalMetrics('Jenkins 发布', jenkinsReleases.items),
    ...mapOperationalMetrics('运维部署', deploymentRequests.items),
    ...mapOperationalMetrics('线上日志', onlineLogs.items),
  ];
}

export async function fetchDevopsMetricList(
  query: OperationalMetricListQuery = {},
): Promise<RemoteListResult<OperationalMetricRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'category', query.category);
  appendQueryParam(params, 'exclude_category', query.excludeCategory);
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

export async function fetchDeploymentRequests(params: {
  environment?: string;
  productId?: string;
  status?: string;
  versionId?: string;
} = {}): Promise<DeploymentRequestRecord[]> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  appendQueryParam(query, 'environment', params.environment);
  appendQueryParam(query, 'product_id', params.productId);
  appendQueryParam(query, 'status', params.status);
  appendQueryParam(query, 'version_id', params.versionId);
  const queryString = query.toString();
  const response = await apiRequest<ListResponse<FlexibleListItem>>(
    queryString ? `/api/devops/deployments?${queryString}` : '/api/devops/deployments',
    { token },
  );
  return response.items.map(mapDeploymentRequest);
}

export async function fetchDeploymentRequestList(
  params: DeploymentRequestListQuery = {},
): Promise<RemoteListResult<DeploymentRequestRecord>> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  appendRemoteListParams(query, params);
  appendQueryParam(query, 'environment', params.environment);
  appendQueryParam(query, 'product_id', params.productId);
  appendQueryParam(query, 'status', params.status);
  appendQueryParam(query, 'title', params.title);
  appendQueryParam(query, 'version_id', params.versionId);
  const response = await apiRequest<ListResponse<FlexibleListItem>>(
    `/api/devops/deployments?${query.toString()}`,
    { token },
  );
  return {
    page: response.page ?? params.page ?? 1,
    pageSize: response.page_size ?? params.pageSize ?? 10,
    rows: response.items.map(mapDeploymentRequest),
    total: response.total,
  };
}

export async function fetchDeploymentRequestDetail(
  deploymentRequestId: string,
): Promise<DeploymentRequestRecord> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>(
    `/api/devops/deployments/${encodeURIComponent(deploymentRequestId)}`,
    { token },
  );
  return mapDeploymentRequest(item);
}

export async function fetchDeploymentSchemes(params: {
  deploymentMethod?: DeploymentMethod;
  environment?: string;
  productId?: string;
  status?: 'active' | 'disabled';
} = {}): Promise<DeploymentSchemeRecord[]> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  appendQueryParam(query, 'deployment_method', params.deploymentMethod);
  appendQueryParam(query, 'environment', params.environment);
  appendQueryParam(query, 'product_id', params.productId);
  appendQueryParam(query, 'status', params.status);
  const queryString = query.toString();
  const response = await apiRequest<ListResponse<FlexibleListItem>>(
    queryString
      ? `/api/devops/deployment-schemes?${queryString}`
      : '/api/devops/deployment-schemes',
    { token },
  );
  return response.items.map(mapDeploymentScheme);
}

export async function fetchDeploymentSchemeList(
  params: DeploymentSchemeListQuery = {},
): Promise<RemoteListResult<DeploymentSchemeRecord>> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  appendRemoteListParams(query, params);
  appendQueryParam(query, 'deployment_method', params.deploymentMethod);
  appendQueryParam(query, 'environment', params.environment);
  appendQueryParam(query, 'name', params.name);
  appendQueryParam(query, 'product_id', params.productId);
  appendQueryParam(query, 'status', params.status);
  const response = await apiRequest<ListResponse<FlexibleListItem>>(
    `/api/devops/deployment-schemes?${query.toString()}`,
    { token },
  );
  return {
    page: response.page ?? params.page ?? 1,
    pageSize: response.page_size ?? params.pageSize ?? 10,
    rows: response.items.map(mapDeploymentScheme),
    total: response.total,
  };
}

export async function fetchDeploymentRunnerTargets(params: {
  environment?: string;
  method?: 'docker' | 'ssh';
  productId?: string;
  runnerId?: string;
} = {}): Promise<DeploymentRunnerTargetRecord[]> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  appendQueryParam(query, 'method', params.method);
  appendQueryParam(query, 'environment', params.environment);
  appendQueryParam(query, 'product_id', params.productId);
  appendQueryParam(query, 'runner_id', params.runnerId);
  const queryString = query.toString();
  const response = await apiRequest<ListResponse<FlexibleListItem>>(
    queryString
      ? `/api/devops/deployment-runner-targets?${queryString}`
      : '/api/devops/deployment-runner-targets',
    { token },
  );
  return response.items.map(mapDeploymentRunnerTarget);
}

export async function fetchDeploymentJenkinsConnections(params: {
  environment?: string;
  productId?: string;
} = {}): Promise<DeploymentJenkinsConnectionRecord[]> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  appendQueryParam(query, 'environment', params.environment);
  appendQueryParam(query, 'product_id', params.productId);
  const queryString = query.toString();
  const response = await apiRequest<ListResponse<FlexibleListItem>>(
    queryString
      ? `/api/devops/deployment-jenkins-connections?${queryString}`
      : '/api/devops/deployment-jenkins-connections',
    { token },
  );
  return response.items.map((item) => ({
    environment: formatUnknownValue(item.environment || 'prod'),
    id: formatUnknownValue(item.id),
    name: formatUnknownValue(item.name),
    ready: item.ready !== false,
    status: formatUnknownValue(item.status),
  }));
}

export async function createDeploymentScheme(
  payload: DeploymentSchemeCreatePayload,
): Promise<DeploymentSchemeRecord> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>('/api/devops/deployment-schemes', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapDeploymentScheme(item);
}

export async function updateDeploymentScheme(
  schemeId: string,
  payload: DeploymentSchemeUpdatePayload,
): Promise<DeploymentSchemeRecord> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>(
    `/api/devops/deployment-schemes/${encodeURIComponent(schemeId)}`,
    { body: payload, method: 'PATCH', token },
  );
  return mapDeploymentScheme(item);
}

export async function deleteDeploymentScheme(schemeId: string): Promise<void> {
  const token = requireAccessToken();
  await apiRequest<FlexibleListItem>(
    `/api/devops/deployment-schemes/${encodeURIComponent(schemeId)}`,
    { method: 'DELETE', token },
  );
}

export async function createDeploymentRequest(
  payload: DeploymentRequestCreatePayload,
): Promise<DeploymentRequestRecord> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>('/api/devops/deployments', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapDeploymentRequest(item);
}

export async function startDeploymentRequest(
  deploymentRequestId: string,
  payload: DeploymentStartPayload = {},
): Promise<DeploymentRequestRecord> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>(
    `/api/devops/deployments/${encodeURIComponent(deploymentRequestId)}/start`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return mapDeploymentRequest(item);
}

function mapDeploymentConnectivityProbe(item: FlexibleListItem): DeploymentConnectivityProbeRecord {
  return {
    deploymentId: formatUnknownValue(item.deployment_id),
    kind: item.kind === 'jenkins' ? 'jenkins' : 'runner',
    maxAgeSeconds: numberOrUndefined(item.max_age_seconds) ?? 0,
    probe: normalizeObjectRecord(item.probe) ?? {},
    ready: Boolean(item.ready),
    status: formatUnknownValue(item.status),
    taskId: emptyToUndefined(formatUnknownValue(item.task_id)),
  };
}

export async function requestDeploymentConnectivityProbe(
  deploymentRequestId: string,
): Promise<DeploymentConnectivityProbeRecord> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>(
    `/api/devops/deployments/${encodeURIComponent(deploymentRequestId)}/connectivity-probe`,
    { method: 'POST', token },
  );
  return mapDeploymentConnectivityProbe(item);
}

export async function fetchDeploymentConnectivityProbe(
  deploymentRequestId: string,
): Promise<DeploymentConnectivityProbeRecord> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>(
    `/api/devops/deployments/${encodeURIComponent(deploymentRequestId)}/connectivity-probe`,
    { method: 'GET', token },
  );
  return mapDeploymentConnectivityProbe(item);
}

export async function probeDeploymentJenkinsConnection(
  connectionId: string,
  payload: { environment: string; jenkins_job_name: string; product_id: string },
): Promise<DeploymentJenkinsConnectionProbeRecord> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>(
    `/api/devops/deployment-jenkins-connections/${encodeURIComponent(connectionId)}/connectivity-probe`,
    { body: payload, method: 'POST', token },
  );
  return {
    connectionId: formatUnknownValue(item.connection_id),
    jobName: formatUnknownValue(item.job_name),
    probe: normalizeObjectRecord(item.probe) ?? {},
  };
}

export async function completeDeploymentRequest(
  deploymentRequestId: string,
  payload: DeploymentCompletePayload,
): Promise<DeploymentRequestRecord> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>(
    `/api/devops/deployments/${encodeURIComponent(deploymentRequestId)}/complete`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return mapDeploymentRequest(item);
}

export async function cancelDeploymentRequest(
  deploymentRequestId: string,
  payload: DeploymentCancelPayload = {},
): Promise<DeploymentRequestRecord> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>(
    `/api/devops/deployments/${encodeURIComponent(deploymentRequestId)}/cancel`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return mapDeploymentRequest(item);
}

export async function syncDeploymentRun(
  deploymentRequestId: string,
  deploymentRunId: string,
): Promise<DeploymentRequestRecord> {
  const token = requireAccessToken();
  const result = await apiRequest<{
    deployment: FlexibleListItem;
    run: FlexibleListItem;
  }>(
    `/api/devops/deployments/${encodeURIComponent(deploymentRequestId)}/runs/${encodeURIComponent(deploymentRunId)}/sync`,
    { method: 'POST', token },
  );
  return mapDeploymentRequest(result.deployment);
}

export async function fetchDeploymentRunLogs(
  deploymentRequestId: string,
  deploymentRunId: string,
): Promise<DeploymentRunLogRecord[]> {
  const token = requireAccessToken();
  const result = await apiRequest<{ items: FlexibleListItem[] }>(
    `/api/devops/deployments/${encodeURIComponent(deploymentRequestId)}/runs/${encodeURIComponent(deploymentRunId)}/logs`,
    { token },
  );
  return (result.items ?? []).map((item) => ({
    createdAt: emptyToUndefined(formatListDate(formatUnknownValue(item.created_at))),
    level: formatUnknownValue(item.level || 'info'),
    message: formatUnknownValue(item.message),
    source: formatUnknownValue(item.source || 'deployment'),
  }));
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

function normalizeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => String(item ?? '').trim())
    .filter(Boolean);
}

function deploymentMethodValue(value: unknown): DeploymentMethod {
  const method = formatUnknownValue(value);
  return method === 'ssh' || method === 'docker' || method === 'jenkins' ? method : 'manual';
}

function mapDeploymentScheme(item: FlexibleListItem): DeploymentSchemeRecord {
  return {
    code: formatUnknownValue(item.code),
    config: normalizeObjectRecord(item.config) ?? {},
    deploymentMethod: deploymentMethodValue(item.deployment_method),
    environment: formatUnknownValue(item.environment),
    executorChannel: formatUnknownValue(item.executor_channel),
    healthCheckConfig: normalizeObjectRecord(item.health_check_config) ?? {},
    id: formatUnknownValue(item.id),
    isDefault: Boolean(item.is_default),
    jenkinsConnectionId: emptyToUndefined(formatUnknownValue(item.jenkins_connection_id)),
    jenkinsJobName: emptyToUndefined(formatUnknownValue(item.jenkins_job_name)),
    name: formatUnknownValue(item.name),
    preflightConfig: normalizeObjectRecord(item.preflight_config) ?? {},
    productId: formatUnknownValue(item.product_id),
    rollbackConfig: normalizeObjectRecord(item.rollback_config) ?? {},
    rolloutStrategy: (
      ['batch', 'blue_green', 'canary'].includes(formatUnknownValue(item.rollout_strategy))
        ? formatUnknownValue(item.rollout_strategy)
        : 'all_at_once'
    ) as DeploymentSchemeRecord['rolloutStrategy'],
    runnerId: emptyToUndefined(formatUnknownValue(item.runner_id)),
    status: item.status === 'disabled' ? 'disabled' : 'active',
    targetCode: emptyToUndefined(formatUnknownValue(item.target_code)),
    timeoutSeconds: Number(item.timeout_seconds ?? 1800),
    updatedAt: emptyToUndefined(formatListDate(formatUnknownValue(item.updated_at))),
    version: Number(item.version ?? 1),
    waveConfig: normalizeObjectRecord(item.wave_config) ?? {},
    windowEnforcement: (
      ['disabled', 'strict'].includes(formatUnknownValue(item.window_enforcement))
        ? formatUnknownValue(item.window_enforcement)
        : 'warn'
    ) as DeploymentSchemeRecord['windowEnforcement'],
  };
}

function mapDeploymentRunnerTarget(item: FlexibleListItem): DeploymentRunnerTargetRecord {
  return {
    code: formatUnknownValue(item.code),
    connectivityProbeCheckedAt: item.connectivity_probe_checked_at
      ? formatUnknownValue(item.connectivity_probe_checked_at)
      : undefined,
    connectivityProbeStatus: item.connectivity_probe_status
      ? formatUnknownValue(item.connectivity_probe_status)
      : undefined,
    method: item.method === 'ssh' ? 'ssh' : 'docker',
    name: formatUnknownValue(item.name),
    healthCheckConfigured: Boolean(item.health_check_configured),
    ready: item.ready !== false,
    rollbackConfigured: Boolean(item.rollback_configured),
    runnerId: formatUnknownValue(item.runner_id),
    supportsBlueGreen: Boolean(item.supports_blue_green),
  };
}

function mapDeploymentRun(item: FlexibleListItem): DeploymentRunRecord {
  return {
    createdAt: formatListDate(formatUnknownValue(item.created_at)),
    deploymentMethod: formatUnknownValue(item.deployment_method || 'manual'),
    executionSnapshot: normalizeObjectRecord(item.execution_snapshot) ?? {},
    executorChannel: formatUnknownValue(item.executor_channel || 'manual'),
    executorType: formatUnknownValue(item.executor_type),
    externalBuildId: emptyToUndefined(formatUnknownValue(item.external_build_id)),
    externalBuildUrl: emptyToUndefined(formatUnknownValue(item.external_build_url)),
    externalJobName: emptyToUndefined(formatUnknownValue(item.external_job_name)),
    externalQueueUrl: emptyToUndefined(formatUnknownValue(item.external_queue_url)),
    failureReason: emptyToUndefined(formatUnknownValue(item.failure_reason)),
    finishedAt: emptyToUndefined(formatListDate(formatUnknownValue(item.finished_at))),
    id: formatUnknownValue(item.id),
    logUrl: emptyToUndefined(formatUnknownValue(item.log_url)),
    healthStatus: emptyToUndefined(formatUnknownValue(item.health_status)),
    operation: emptyToUndefined(formatUnknownValue(item.operation)),
    pluginInvocationLogId: emptyToUndefined(formatUnknownValue(item.plugin_invocation_log_id)),
    runnerTaskId: emptyToUndefined(formatUnknownValue(item.runner_task_id)),
    startedAt: emptyToUndefined(formatListDate(formatUnknownValue(item.started_at))),
    status: formatUnknownValue(item.status),
    steps: Array.isArray(item.steps)
      ? item.steps.map((step) => mapDeploymentRunStep(step as FlexibleListItem))
      : [],
    updatedAt: formatListDate(formatUnknownValue(item.updated_at ?? item.created_at)),
    waveNumber: numberOrUndefined(item.wave_number),
    waveTotal: numberOrUndefined(item.wave_total),
  };
}

function numberOrUndefined(value: unknown) {
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function mapDeploymentRunStep(item: FlexibleListItem): DeploymentRunStepRecord {
  return {
    evidence: normalizeObjectRecord(item.evidence) ?? {},
    finishedAt: emptyToUndefined(formatListDate(formatUnknownValue(item.finished_at))),
    id: formatUnknownValue(item.id),
    sequence: numberOrUndefined(item.sequence) ?? 0,
    startedAt: emptyToUndefined(formatListDate(formatUnknownValue(item.started_at))),
    status: formatUnknownValue(item.status),
    stepType: formatUnknownValue(item.step_type),
    summary: emptyToUndefined(formatUnknownValue(item.summary)),
  };
}

function mapDeploymentRequest(item: FlexibleListItem): DeploymentRequestRecord {
  const qualityGate = normalizeObjectRecord(item.quality_gate);
  return {
    auditEvents: Array.isArray(item.audit_events)
      ? item.audit_events.map((event) => {
          const raw = event as FlexibleListItem;
          return {
            actorId: emptyToUndefined(formatUnknownValue(raw.actor_id)),
            createdAt: emptyToUndefined(formatListDate(formatUnknownValue(raw.created_at))),
            eventType: formatUnknownValue(raw.event_type),
            id: formatUnknownValue(raw.id),
            payload: normalizeObjectRecord(raw.payload) ?? {},
          };
        })
      : [],
    artifactVersion: emptyToUndefined(formatUnknownValue(item.artifact_version)),
    artifactDigest: emptyToUndefined(formatUnknownValue(item.artifact_digest)),
    commitSha: emptyToUndefined(formatUnknownValue(item.commit_sha)),
    currentWave: numberOrUndefined(item.current_wave) ?? 0,
    createdAt: formatListDate(formatUnknownValue(item.created_at)),
    deploymentMethod: deploymentMethodValue(item.deployment_method),
    deploymentSchemeId: emptyToUndefined(formatUnknownValue(item.deployment_scheme_id)),
    environment: formatUnknownValue(item.environment),
    executorChannel: formatUnknownValue(item.executor_channel || 'manual'),
    failureReason: emptyToUndefined(formatUnknownValue(item.failure_reason)),
    finishedAt: emptyToUndefined(formatListDate(formatUnknownValue(item.finished_at))),
    gateSummary: normalizeObjectRecord(item.gate_summary) ?? {},
    id: formatUnknownValue(item.id),
    productId: formatUnknownValue(item.product_id),
    releaseBranch: emptyToUndefined(formatUnknownValue(item.release_branch)),
    dispatchEvents: Array.isArray(item.dispatch_events)
      ? item.dispatch_events.map((event) => {
          const raw = event as FlexibleListItem;
          return {
            attemptCount: numberOrUndefined(raw.attempt_count) ?? 0,
            eventType: formatUnknownValue(raw.event_type),
            id: formatUnknownValue(raw.id),
            lastError: emptyToUndefined(formatUnknownValue(raw.last_error)),
            processedAt: emptyToUndefined(formatListDate(formatUnknownValue(raw.processed_at))),
            status: formatUnknownValue(raw.status),
            updatedAt: emptyToUndefined(formatListDate(formatUnknownValue(raw.updated_at))),
          };
        })
      : [],
    qualityGate: qualityGate
      ? {
          blockedReasons: Array.isArray(qualityGate.blocked_reasons)
            ? qualityGate.blocked_reasons.map((reason) => {
                if (reason && typeof reason === 'object' && !Array.isArray(reason)) {
                  const record = reason as Record<string, unknown>;
                  return formatUnknownValue(record.message || record.code);
                }
                return formatUnknownValue(reason);
              }).filter(Boolean)
            : [],
          checks: Array.isArray(qualityGate.checks)
            ? qualityGate.checks.map((check) => {
                const raw = check as FlexibleListItem;
                return {
                  checkType: formatUnknownValue(raw.check_type),
                  id: formatUnknownValue(raw.id),
                  source: formatUnknownValue(raw.source),
                  status: formatUnknownValue(raw.status),
                  summary: emptyToUndefined(formatUnknownValue(raw.summary)),
                };
              })
            : [],
          id: emptyToUndefined(formatUnknownValue(qualityGate.id)),
          status: emptyToUndefined(formatUnknownValue(qualityGate.status)),
          summary: emptyToUndefined(formatUnknownValue(qualityGate.summary)),
        }
      : undefined,
    requirementIds: normalizeStringArray(item.requirement_ids),
    riskLevel: formatUnknownValue(item.risk_level),
    rollbackPlan: emptyToUndefined(formatUnknownValue(item.rollback_plan)),
    runs: Array.isArray(item.runs) ? item.runs.map((run) => mapDeploymentRun(run as FlexibleListItem)) : [],
    schemeSnapshot: normalizeObjectRecord(item.scheme_snapshot) ?? {},
    startedAt: emptyToUndefined(formatListDate(formatUnknownValue(item.started_at))),
    status: formatUnknownValue(item.status),
    title: formatUnknownValue(item.title),
    totalWaves: numberOrUndefined(item.total_waves) ?? 1,
    updatedAt: formatListDate(formatUnknownValue(item.updated_at ?? item.created_at)),
    versionId: formatUnknownValue(item.version_id),
    windowEnforcement: emptyToUndefined(formatUnknownValue(item.window_enforcement)),
  };
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
