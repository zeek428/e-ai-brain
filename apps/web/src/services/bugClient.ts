import type { BugRecord } from '../data/management';
import { formatDisplayDateTime } from '../utils/dateTime';
import {
  API_BASE_URL,
  ApiRequestError,
  type ApiErrorPayload,
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
  type ListResponse,
  type RemoteListPerformance,
} from './apiClient';
import { handleUnauthorizedApiResponse, requireAccessToken } from './authClient';

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

export type BugListQuery = RemoteListQuery & {
  module?: string;
  severity?: string;
  status?: string;
  title?: string;
  version?: string;
};

export type BugBatchUpdatePayload = {
  assignee?: string;
  bug_ids: string[];
  reason?: string;
  severity?: string;
  status?: string;
};

export type BugBatchUpdateResult = {
  batchId: string;
  skipped: Array<{ code: string; id: string; message: string }>;
  skippedCount: number;
  updated: BugRecord[];
  updatedCount: number;
};

export type BugPromoteAiTaskResult = {
  start?: {
    current_step?: string;
    executor_task_id?: string;
    runner_id?: string;
    status?: string;
  } | null;
  task: {
    current_step?: string;
    id: string;
    status: string;
    task_type: string;
    title?: string;
  };
};

export type BugImageUploadSource = 'clipboard' | 'file_picker';

export type BugImageEvidenceItem = {
  bucket: string;
  content_hash: string;
  filename: string;
  id: string;
  mime_type: string;
  object_key: string;
  size_bytes: number;
  source: BugImageUploadSource;
  storage_provider: string;
  uploaded_at: string;
  uploaded_by: string;
};

export type BugImageUploadPayload = {
  content_base64: string;
  filename: string;
  mime_type: string;
  source: BugImageUploadSource;
};

export type BugMutationPayload = {
  assignee?: string;
  description?: string;
  duplicate_of_bug_id?: string | null;
  evidence?: Record<string, unknown>;
  module_code?: string;
  product_id?: string;
  related_task_id?: string;
  requirement_id?: string;
  reproduce_steps?: string[];
  severity?: string;
  source?: string;
  status?: string;
  title?: string;
  version_id?: string;
};

export type BugListItem = {
  assignee?: string | null;
  created_at?: string;
  description?: string;
  duplicate_of_bug_id?: string | null;
  evidence?: unknown;
  id: string;
  module_code?: string | null;
  product_id?: string;
  related_task_id?: string | null;
  reproduce_steps?: unknown;
  requirement_id?: string | null;
  severity?: string;
  source?: string;
  status?: string;
  title: string;
  version_code?: string | null;
  version_id?: string | null;
  version_name?: string | null;
};

function formatListDate(value?: string) {
  return formatDisplayDateTime(value);
}

function normalizeBugSeverity(severity?: string): BugRecord['severity'] {
  if (severity === 'blocker' || severity === 'critical' || severity === 'minor') {
    return severity;
  }
  return 'major';
}

function normalizeBugStatus(status?: string): BugRecord['status'] {
  if (
    status === 'assigned' ||
    status === 'closed' ||
    status === 'fixed' ||
    status === 'needs_info' ||
    status === 'open' ||
    status === 'reopened' ||
    status === 'triaged' ||
    status === 'verified'
  ) {
    return status;
  }
  return 'open';
}

function normalizeBugSource(source?: string): BugRecord['source'] {
  if (source === 'ai_auto_test' || source === 'ai_post_release' || source === 'code_inspection') {
    return source;
  }
  return 'manual_test';
}

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => (typeof item === 'string' ? item : JSON.stringify(item) ?? ''))
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeObjectRecord(value: unknown): Record<string, unknown> | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  return value as Record<string, unknown>;
}

function normalizeDashboardCount(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
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

export function mapBugRecord(bug: BugListItem): BugRecord {
  return {
    assignee: bug.assignee ?? '-',
    createdAt: formatListDate(bug.created_at),
    description: bug.description,
    duplicateOfBugId: bug.duplicate_of_bug_id ?? undefined,
    evidence: normalizeObjectRecord(bug.evidence),
    id: bug.id,
    module: bug.module_code ?? '-',
    productId: bug.product_id,
    relatedTaskId: bug.related_task_id ?? undefined,
    reproduceSteps: normalizeStringList(bug.reproduce_steps),
    requirementId: bug.requirement_id ?? undefined,
    severity: normalizeBugSeverity(bug.severity),
    source: normalizeBugSource(bug.source),
    status: normalizeBugStatus(bug.status),
    title: bug.title,
    versionId: bug.version_id ?? undefined,
    versionName: bug.version_id
      ? formatUnknownValue(bug.version_name ?? bug.version_code ?? bug.version_id)
      : '未关联',
  };
}

export async function fetchManagementBugs(): Promise<BugRecord[]> {
  const token = requireAccessToken();
  const bugs = await apiRequest<ListResponse<BugListItem>>('/api/bugs', { token });

  return bugs.items.map(mapBugRecord);
}

export async function fetchManagementBugList(
  query: BugListQuery = {},
): Promise<RemoteListResult<BugRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'module', query.module);
  appendQueryParam(params, 'severity', query.severity);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'title', query.title);
  appendQueryParam(params, 'version', query.version);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const bugs = await apiRequest<ListResponse<BugListItem>>(
    queryString ? `/api/bugs?${queryString}` : '/api/bugs',
    { token },
  );

  return {
    page: bugs.page ?? query.page ?? 1,
    pageSize: bugs.page_size ?? query.pageSize ?? 10,
    performance: bugs.performance,
    rows: bugs.items.map(mapBugRecord),
    total: bugs.total,
  };
}

export async function createManagementBug(payload: BugMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<{ id: string }>('/api/bugs', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function uploadManagementBugImage(
  payload: BugImageUploadPayload,
): Promise<BugImageEvidenceItem> {
  const token = requireAccessToken();
  return apiRequest<BugImageEvidenceItem>('/api/bugs/images/upload', {
    body: payload,
    method: 'POST',
    token,
  });
}

function bugImagePreviewPath(image: BugImageEvidenceItem) {
  const params = new URLSearchParams();
  appendQueryParam(params, 'bucket', image.bucket);
  appendQueryParam(params, 'object_key', image.object_key);
  appendQueryParam(params, 'mime_type', image.mime_type);
  return `/api/bugs/images/preview?${params.toString()}`;
}

export async function fetchManagementBugImagePreview(
  image: BugImageEvidenceItem,
): Promise<Blob> {
  const token = requireAccessToken();
  const response = await fetch(`${API_BASE_URL}${bugImagePreviewPath(image)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    method: 'GET',
  });
  if (!response.ok) {
    let payload: ApiErrorPayload | undefined;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = undefined;
    }
    const requestError = new ApiRequestError({
      code: payload?.detail?.code,
      detail: payload?.detail,
      message: payload?.detail?.message ?? `API request failed: ${response.status}`,
      status: response.status,
      traceId: payload?.detail?.trace_id,
    });
    if (response.status === 401) {
      handleUnauthorizedApiResponse();
    }
    throw requestError;
  }
  return response.blob();
}

export async function updateManagementBug(bugId: string, payload: BugMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<{ id: string }>(`/api/bugs/${bugId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function batchUpdateManagementBugs(
  payload: BugBatchUpdatePayload,
): Promise<BugBatchUpdateResult> {
  const token = requireAccessToken();
  const result = await apiRequest<{
    batch_id: string;
    skipped?: Array<{ code?: string; id?: string; message?: string }>;
    skipped_count?: number;
    updated?: BugListItem[];
    updated_count?: number;
  }>('/api/bugs/batch-update', {
    body: payload,
    method: 'POST',
    token,
  });

  return {
    batchId: result.batch_id,
    skipped: (result.skipped ?? []).map((item) => ({
      code: item.code ?? 'UNKNOWN',
      id: item.id ?? '-',
      message: item.message ?? '-',
    })),
    skippedCount: normalizeDashboardCount(result.skipped_count),
    updated: (result.updated ?? []).map(mapBugRecord),
    updatedCount: normalizeDashboardCount(result.updated_count),
  };
}

export async function promoteBugToAiTask(bugId: string): Promise<BugPromoteAiTaskResult> {
  const token = requireAccessToken();
  return apiRequest<BugPromoteAiTaskResult>(`/api/bugs/${bugId}/promote-ai-task`, {
    body: { auto_start: true },
    method: 'POST',
    token,
  });
}

export async function deleteManagementBug(bugId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/bugs/${bugId}`, {
    method: 'DELETE',
    token,
  });
}
