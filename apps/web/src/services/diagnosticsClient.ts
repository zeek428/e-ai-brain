import type { AuditRecord } from '../data/management';
import { formatDisplayDateTime } from '../utils/dateTime';
import {
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
  type ListResponse,
  type RemoteListPerformance,
} from './apiClient';
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

export type AuditListQuery = RemoteListQuery & {
  actor?: string;
  eventType?: string;
  result?: string;
  subject?: string;
};

export type ExecutionTraceListQuery = RemoteListQuery & {
  createdFrom?: string;
  createdTo?: string;
  keyword?: string;
  refresh?: boolean;
  sourceId?: string;
  sourceType?: string;
  status?: string;
};

export type ExecutionTraceNodeRecord = {
  duration_ms?: number | null;
  error_code?: string | null;
  error_message?: string | null;
  finished_at?: string | null;
  id: string;
  label: string;
  metadata?: Record<string, unknown>;
  source_id: string;
  source_type: string;
  started_at?: string | null;
  status: string;
  summary?: string | null;
};

export type ExecutionTraceEdgeRecord = {
  from: string;
  label?: string;
  to: string;
};

export type ExecutionTraceListItem = {
  diagnostic_nodes?: ExecutionTraceNodeRecord[];
  duration_ms?: number | null;
  failed_node_count: number;
  id: string;
  node_count: number;
  related_ids?: Record<string, string[]>;
  root_id: string;
  root_type: string;
  running_node_count: number;
  started_at?: string | null;
  status: string;
  summary: string;
  title: string;
  updated_at?: string | null;
};

export type ExecutionTraceDetailRecord = ExecutionTraceListItem & {
  edges: ExecutionTraceEdgeRecord[];
  nodes: ExecutionTraceNodeRecord[];
};

export type LifecycleRelationRecord = {
  relationType: string;
  subjectId: string;
  subjectType: string;
  summary: string;
};

export type LifecycleRiskSignalRecord = {
  impactSummary: string;
  recommendation: string;
  riskType: string;
  severity: string;
  sourceSubjectId: string;
  sourceSubjectType: string;
};

export type LifecycleContextRecord = {
  downstream: LifecycleRelationRecord[];
  missingContext: string[];
  riskSignals: LifecycleRiskSignalRecord[];
  status: string;
  summary: {
    downstreamCount: number;
    riskCount: number;
    upstreamCount: number;
  };
  upstream: LifecycleRelationRecord[];
};

type AuditEventListItem = {
  actor_id?: string;
  ai_task_id?: string | null;
  created_at?: string;
  event_type: string;
  id: string;
  payload?: Record<string, unknown>;
  result?: string;
  subject_id?: string;
  subject_type?: string;
};

type LifecycleRelationItem = {
  relation_type?: string;
  subject_id?: string;
  subject_type?: string;
  summary?: string;
};

type LifecycleRiskSignalItem = {
  impact_summary?: string;
  recommendation?: string;
  risk_type?: string;
  severity?: string;
  source_subject_id?: string;
  source_subject_type?: string;
};

type LifecycleContextResponse = {
  downstream?: LifecycleRelationItem[];
  missing_context?: string[];
  risk_signals?: LifecycleRiskSignalItem[];
  status?: string;
  summary?: Partial<{
    downstream_count: number;
    risk_count: number;
    upstream_count: number;
  }>;
  upstream?: LifecycleRelationItem[];
};

function formatListDate(value?: string) {
  return formatDisplayDateTime(value);
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

function normalizeDashboardCount(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function mapAuditRecord(event: AuditEventListItem): AuditRecord {
  return {
    actor: event.actor_id ?? '-',
    aiTaskId: event.ai_task_id ?? undefined,
    eventType: event.event_type,
    id: event.id,
    payload: event.payload,
    result: event.result === 'failed' ? 'failed' : 'success',
    subject:
      event.subject_type && event.subject_id ? `${event.subject_type}: ${event.subject_id}` : '-',
    subjectId: event.subject_id,
    subjectType: event.subject_type,
    timestamp: formatListDate(event.created_at),
  };
}

function mapLifecycleRelation(item: LifecycleRelationItem): LifecycleRelationRecord {
  return {
    relationType: formatUnknownValue(item.relation_type),
    subjectId: formatUnknownValue(item.subject_id),
    subjectType: formatUnknownValue(item.subject_type),
    summary: formatUnknownValue(item.summary),
  };
}

export async function fetchManagementAudit(): Promise<AuditRecord[]> {
  const token = requireAccessToken();
  const events = await apiRequest<ListResponse<AuditEventListItem>>('/api/audit/events', { token });

  return events.items.map(mapAuditRecord);
}

export async function fetchManagementAuditList(
  query: AuditListQuery = {},
): Promise<RemoteListResult<AuditRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'actor', query.actor);
  appendQueryParam(params, 'event_type', query.eventType);
  appendQueryParam(params, 'result', query.result);
  appendQueryParam(params, 'subject', query.subject);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const events = await apiRequest<ListResponse<AuditEventListItem>>(
    queryString ? `/api/audit/events?${queryString}` : '/api/audit/events',
    { token },
  );

  return {
    page: events.page ?? query.page ?? 1,
    pageSize: events.page_size ?? query.pageSize ?? 10,
    performance: events.performance,
    rows: events.items.map(mapAuditRecord),
    total: events.total,
  };
}

export async function fetchExecutionTraces(
  query: ExecutionTraceListQuery = {},
): Promise<RemoteListResult<ExecutionTraceListItem>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'created_from', query.createdFrom);
  appendQueryParam(params, 'created_to', query.createdTo);
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'refresh', query.refresh);
  appendQueryParam(params, 'source_id', query.sourceId);
  appendQueryParam(params, 'source_type', query.sourceType);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const traces = await apiRequest<ListResponse<ExecutionTraceListItem>>(
    queryString
      ? `/api/governance/execution-traces?${queryString}`
      : '/api/governance/execution-traces',
    { token },
  );

  return {
    page: traces.page ?? query.page ?? 1,
    pageSize: traces.page_size ?? query.pageSize ?? 10,
    performance: traces.performance,
    rows: traces.items,
    total: traces.total,
  };
}

export async function fetchExecutionTraceDetail(
  traceId: string,
): Promise<ExecutionTraceDetailRecord> {
  const token = requireAccessToken();
  return apiRequest<ExecutionTraceDetailRecord>(`/api/governance/execution-traces/${traceId}`, {
    token,
  });
}

export async function fetchLifecycleContext(params: {
  productId?: string;
  subjectId?: string;
  subjectType?: string;
}): Promise<LifecycleContextRecord> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  if (params.subjectType) {
    query.set('subject_type', params.subjectType);
  }
  if (params.subjectId) {
    query.set('subject_id', params.subjectId);
  }
  if (params.productId) {
    query.set('product_id', params.productId);
  }
  const context = await apiRequest<LifecycleContextResponse>(
    `/api/lifecycle/context?${query.toString()}`,
    { token },
  );
  const summary = context.summary ?? {};
  return {
    downstream: (context.downstream ?? []).map(mapLifecycleRelation),
    missingContext: context.missing_context ?? [],
    riskSignals: (context.risk_signals ?? []).map((item) => ({
      impactSummary: formatUnknownValue(item.impact_summary),
      recommendation: formatUnknownValue(item.recommendation),
      riskType: formatUnknownValue(item.risk_type),
      severity: formatUnknownValue(item.severity),
      sourceSubjectId: formatUnknownValue(item.source_subject_id),
      sourceSubjectType: formatUnknownValue(item.source_subject_type),
    })),
    status: formatUnknownValue(context.status),
    summary: {
      downstreamCount: normalizeDashboardCount(summary.downstream_count),
      riskCount: normalizeDashboardCount(summary.risk_count),
      upstreamCount: normalizeDashboardCount(summary.upstream_count),
    },
    upstream: (context.upstream ?? []).map(mapLifecycleRelation),
  };
}
