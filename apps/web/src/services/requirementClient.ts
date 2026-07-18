import type { RequirementRecord } from '../data/management';
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

export type RequirementResponse = {
  id: string;
  status: string;
};

export type RequirementDetail = RequirementListItem & {
  assessment_revision?: number;
  revision?: number;
};

export type RequirementAssessmentOpinion = {
  conclusion_json?: Record<string, unknown>;
  confidence?: number | null;
  outcome_code?: string | null;
  risk_level?: string | null;
  role_code: string;
};

export type RequirementAssessment = {
  id: string;
  opinion_round?: number;
  opinions?: RequirementAssessmentOpinion[];
  requirement_id: string;
  requirement_revision: number;
  risk_summary?: Record<string, unknown>;
  status: string;
  structured_assessment?: Record<string, unknown>;
  version: number;
};

export type RequirementListQuery = RemoteListQuery & {
  priority?: string;
  product?: string;
  productId?: string;
  source?: string;
  status?: string;
  title?: string;
  version?: string;
  versionId?: string;
};

export type RequirementMutationPayload = {
  content?: string;
  module_code?: string;
  priority?: string;
  product_id?: string;
  source?: string;
  title?: string;
  version_id?: string | null;
};

export type RequirementBatchSchedulePayload = {
  product_id: string;
  reason?: string;
  requirement_ids: string[];
  version_id: string;
};

export type RequirementBatchSkippedItem = {
  code: string;
  id: string;
  message: string;
};

type RequirementBatchScheduleResponse = {
  batch_id: string;
  product_id: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skipped_count: number;
  updated: RequirementListItem[];
  updated_count: number;
  version_id: string;
};

export type RequirementBatchScheduleResult = {
  batchId: string;
  productId: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skippedCount: number;
  updated: RequirementRecord[];
  updatedCount: number;
  versionId: string;
};

export type RequirementBatchAssignOwnerPayload = {
  assignee: string;
  reason?: string;
  requirement_ids: string[];
};

type RequirementBatchAssignOwnerResponse = {
  assignee: string;
  batch_id: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skipped_count: number;
  updated: RequirementListItem[];
  updated_count: number;
};

export type RequirementBatchAssignOwnerResult = {
  assignee: string;
  batchId: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skippedCount: number;
  updated: RequirementRecord[];
  updatedCount: number;
};

export type RequirementBatchAdvanceStatusPayload = {
  reason?: string;
  requirement_ids: string[];
  target_status: string;
};

type RequirementBatchAdvanceStatusResponse = {
  batch_id: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skipped_count: number;
  target_status: string;
  updated: RequirementListItem[];
  updated_count: number;
};

export type RequirementBatchAdvanceStatusResult = {
  batchId: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skippedCount: number;
  targetStatus: RequirementRecord['status'];
  updated: RequirementRecord[];
  updatedCount: number;
};

export type RequirementBatchGenerateTasksPayload = {
  product_id: string;
  reason?: string;
  requirement_ids: string[];
};

export type RequirementBatchGeneratedTaskItem = {
  requirement_id: string;
  task_id: string;
  task_status: string;
  task_type: string;
};

type RequirementBatchGenerateTasksResponse = {
  batch_id: string;
  generated: RequirementBatchGeneratedTaskItem[];
  generated_count: number;
  product_id: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skipped_count: number;
};

export type RequirementBatchGenerateTasksResult = {
  batchId: string;
  generated: RequirementBatchGeneratedTaskItem[];
  generatedCount: number;
  productId: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skippedCount: number;
};

export type RequirementListItem = {
  assignee?: string | null;
  content?: string;
  created_at?: string;
  created_by?: string;
  id: string;
  module_code?: string | null;
  priority?: string;
  product_code?: string;
  product_id: string;
  product_name?: string;
  source?: string;
  status?: string;
  title: string;
  updated_at?: string;
  version_code?: string | null;
  version_id?: string;
  version_name?: string | null;
};

function formatListDate(value?: string) {
  return formatDisplayDateTime(value);
}

function normalizePriority(priority?: string): RequirementRecord['priority'] {
  if (priority === 'P0' || priority === 'P2') {
    return priority;
  }
  return 'P1';
}

function normalizeRequirementStatus(status?: string): RequirementRecord['status'] {
  if (status === 'pending_approval') {
    return 'submitted';
  }
  if (status === 'task_created') {
    return 'designing';
  }
  if (
    status === 'accepted' ||
    status === 'approved' ||
    status === 'cancelled' ||
    status === 'closed' ||
    status === 'code_reviewing' ||
    status === 'deferred' ||
    status === 'designing' ||
    status === 'developing' ||
    status === 'deploying' ||
    status === 'draft' ||
    status === 'planned' ||
    status === 'ready_for_dev' ||
    status === 'ready_for_release' ||
    status === 'rejected' ||
    status === 'released' ||
    status === 'submitted' ||
    status === 'testing'
  ) {
    return status;
  }
  return 'draft';
}

export function mapRequirementRecord(requirement: RequirementListItem): RequirementRecord {
  return {
    content: requirement.content,
    id: requirement.id,
    moduleCode: requirement.module_code ?? undefined,
    owner: requirement.assignee ?? requirement.created_by ?? '-',
    priority: normalizePriority(requirement.priority),
    product: requirement.product_code ?? requirement.product_name ?? requirement.product_id,
    productId: requirement.product_id,
    source: requirement.source ?? 'business_department',
    status: normalizeRequirementStatus(requirement.status),
    title: requirement.title,
    createdAt: formatListDate(requirement.created_at),
    updatedAt: formatListDate(requirement.updated_at ?? requirement.created_at),
    versionId: requirement.version_id,
    versionName: requirement.version_id
      ? (requirement.version_name ?? requirement.version_code ?? requirement.version_id)
      : '未排期',
  };
}

export async function fetchManagementRequirements(): Promise<RequirementRecord[]> {
  const token = requireAccessToken();
  const requirements = await apiRequest<ListResponse<RequirementListItem>>('/api/requirements', {
    token,
  });

  return requirements.items.map(mapRequirementRecord);
}

export async function fetchManagementRequirementList(
  query: RequirementListQuery = {},
): Promise<RemoteListResult<RequirementRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'priority', query.priority);
  appendQueryParam(params, 'product', query.product);
  appendQueryParam(params, 'product_id', query.productId);
  appendQueryParam(params, 'source', query.source);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'title', query.title);
  appendQueryParam(params, 'version', query.version);
  appendQueryParam(params, 'version_id', query.versionId);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const requirements = await apiRequest<ListResponse<RequirementListItem>>(
    queryString ? `/api/requirements?${queryString}` : '/api/requirements',
    { token },
  );

  return {
    page: requirements.page ?? query.page ?? 1,
    pageSize: requirements.page_size ?? query.pageSize ?? 10,
    performance: requirements.performance,
    rows: requirements.items.map(mapRequirementRecord),
    total: requirements.total,
  };
}

export async function createManagementRequirement(payload: RequirementMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<RequirementResponse>('/api/requirements', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateManagementRequirement(
  requirementId: string,
  payload: RequirementMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<RequirementResponse>(`/api/requirements/${requirementId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function batchScheduleRequirements(
  payload: RequirementBatchSchedulePayload,
): Promise<RequirementBatchScheduleResult> {
  const token = requireAccessToken();
  const result = await apiRequest<RequirementBatchScheduleResponse>(
    '/api/requirements/batch-schedule',
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return {
    batchId: result.batch_id,
    productId: result.product_id,
    reason: result.reason,
    skipped: result.skipped,
    skippedCount: result.skipped_count,
    updated: result.updated.map(mapRequirementRecord),
    updatedCount: result.updated_count,
    versionId: result.version_id,
  };
}

export async function batchAssignRequirementOwner(
  payload: RequirementBatchAssignOwnerPayload,
): Promise<RequirementBatchAssignOwnerResult> {
  const token = requireAccessToken();
  const result = await apiRequest<RequirementBatchAssignOwnerResponse>(
    '/api/requirements/batch-assign-owner',
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return {
    assignee: result.assignee,
    batchId: result.batch_id,
    reason: result.reason,
    skipped: result.skipped,
    skippedCount: result.skipped_count,
    updated: result.updated.map(mapRequirementRecord),
    updatedCount: result.updated_count,
  };
}

export async function batchAdvanceRequirementStatus(
  payload: RequirementBatchAdvanceStatusPayload,
): Promise<RequirementBatchAdvanceStatusResult> {
  const token = requireAccessToken();
  const result = await apiRequest<RequirementBatchAdvanceStatusResponse>(
    '/api/requirements/batch-advance-status',
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return {
    batchId: result.batch_id,
    reason: result.reason,
    skipped: result.skipped,
    skippedCount: result.skipped_count,
    targetStatus: normalizeRequirementStatus(result.target_status),
    updated: result.updated.map(mapRequirementRecord),
    updatedCount: result.updated_count,
  };
}

export async function batchGenerateRequirementTasks(
  payload: RequirementBatchGenerateTasksPayload,
): Promise<RequirementBatchGenerateTasksResult> {
  const token = requireAccessToken();
  const result = await apiRequest<RequirementBatchGenerateTasksResponse>(
    '/api/requirements/batch-generate-tasks',
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return {
    batchId: result.batch_id,
    generated: result.generated,
    generatedCount: result.generated_count,
    productId: result.product_id,
    reason: result.reason,
    skipped: result.skipped,
    skippedCount: result.skipped_count,
  };
}

export async function deleteManagementRequirement(requirementId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/requirements/${requirementId}`, {
    method: 'DELETE',
    token,
  });
}

export async function approveManagementRequirement(requirementId: string) {
  const token = requireAccessToken();
  return apiRequest<RequirementResponse>(`/api/requirements/${requirementId}/approve`, {
    body: {},
    method: 'POST',
    token,
  });
}

export async function rejectManagementRequirement(requirementId: string, rejectionReason: string) {
  const token = requireAccessToken();
  return apiRequest<RequirementResponse>(`/api/requirements/${requirementId}/reject`, {
    body: { rejection_reason: rejectionReason },
    method: 'POST',
    token,
  });
}

export async function generateRequirementTask(requirementId: string) {
  const token = requireAccessToken();
  return apiRequest<{ task_id: string; task_status: string; task_type: string }>(
    `/api/requirements/${requirementId}/generate-task`,
    {
      method: 'POST',
      token,
    },
  );
}

export async function fetchRequirementDetail(requirementId: string) {
  const token = requireAccessToken();
  return apiRequest<RequirementDetail>(`/api/requirements/${requirementId}`, { token });
}

export async function fetchLatestRequirementAssessment(requirementId: string) {
  const token = requireAccessToken();
  return apiRequest<RequirementAssessment>(
    `/api/requirements/${requirementId}/assessments/latest`,
    { token },
  );
}

export async function startRequirementAssessment(
  requirementId: string,
  payload: { reason?: string; request_id: string; requirement_revision: number },
) {
  const token = requireAccessToken();
  return apiRequest<RequirementAssessment>(`/api/requirements/${requirementId}/assessments`, {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function decideRequirementAssessment(
  assessmentId: string,
  payload: { comment?: string; decision: 'accept' | 'defer' | 'reject' | 'request_more_info' | 'request_rework'; version: number },
) {
  const token = requireAccessToken();
  return apiRequest<RequirementAssessment>(`/api/requirement-assessments/${assessmentId}/decisions`, {
    body: { ...payload, idempotency_key: crypto.randomUUID() },
    method: 'POST',
    token,
  });
}

export async function submitRequirementAssessmentAnswers(
  assessmentId: string,
  payload: { answers: Record<string, unknown>; expected_version: number },
) {
  const token = requireAccessToken();
  return apiRequest<RequirementAssessment>(`/api/requirement-assessments/${assessmentId}/answers`, {
    body: { ...payload, idempotency_key: crypto.randomUUID() },
    method: 'POST',
    token,
  });
}
