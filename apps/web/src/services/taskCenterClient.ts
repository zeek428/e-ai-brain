import { formatDisplayDateTime } from '../utils/dateTime';
import {
  API_BASE_URL,
  ApiRequestError,
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
  type ApiErrorPayload,
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

export type TaskCenterTaskRecord = {
  createdAt: string;
  createdAtValue?: string;
  currentStep?: string;
  id: string;
  label: string;
  owner: string;
  product: string;
  productId?: string;
  requirementId?: string;
  status: string;
  type: string;
};

export type TaskCenterTaskQuery = {
  createdFrom?: string;
  createdTo?: string;
  keyword?: string;
  owner?: string;
  page?: number;
  pageSize?: number;
  productId?: string;
  sortField?: string;
  sortOrder?: RemoteSortOrder;
  status?: string;
  taskType?: string;
};

export type TaskCenterTaskListResult = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: TaskCenterTaskRecord[];
  total: number;
};

export type TaskCenterReviewListQuery = RemoteListQuery & {
  aiTaskId?: string;
};

export type TaskBatchCancelPayload = {
  reason?: string;
  task_ids: string[];
};

export type TaskBatchRetryPayload = {
  reason?: string;
  task_ids: string[];
};

export type TaskBatchSkippedItem = {
  code: string;
  id: string;
  message: string;
};

export type TaskBatchRetriedItem = {
  current_step?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  id: string;
  review_id?: string | null;
  status: string;
};

type TaskBatchCancelResponse = {
  batch_id: string;
  reason?: string | null;
  skipped: TaskBatchSkippedItem[];
  skipped_count: number;
  updated: Array<{ id: string; status: string }>;
  updated_count: number;
};

type TaskBatchRetryResponse = {
  batch_id: string;
  reason?: string | null;
  retried: TaskBatchRetriedItem[];
  retried_count: number;
  skipped: TaskBatchSkippedItem[];
  skipped_count: number;
  updated: TaskBatchRetriedItem[];
  updated_count: number;
};

export type TaskBatchCancelResult = {
  batchId: string;
  reason?: string | null;
  skipped: TaskBatchSkippedItem[];
  skippedCount: number;
  updated: Array<{ id: string; status: string }>;
  updatedCount: number;
};

export type TaskBatchRetryResult = {
  batchId: string;
  reason?: string | null;
  retried: TaskBatchRetriedItem[];
  retriedCount: number;
  skipped: TaskBatchSkippedItem[];
  skippedCount: number;
  updated: TaskBatchRetriedItem[];
  updatedCount: number;
};

export type TaskCenterTaskDetailRecord = TaskCenterTaskRecord & {
  currentStep: string;
  graphRunIds: string[];
  inputJson: unknown;
  moduleName: string;
  outputJson: unknown;
  outputSummary: string;
  pendingReviewId?: string;
  productName: string;
  requirementTitle: string;
  versionName: string;
};

export type TaskCenterReviewRecord = {
  aiTaskId: string;
  contentSummary: string;
  createdAt?: string;
  id: string;
  stage: string;
  status: string;
  updatedAt?: string;
  version: number;
};

export type TaskMoreInfoAnswer = {
  answer: string;
  question: string;
};

export type TaskWritebackIssueRecord = {
  id: string;
  sourceTaskId?: string;
  status: string;
  title: string;
};

export type TaskWritebackResultRecord = {
  idempotencyKey: string;
  issues: TaskWritebackIssueRecord[];
  status: string;
  taskId: string;
};

export type TaskListItem = {
  created_at?: string;
  created_by?: string;
  current_step?: string;
  id: string;
  product_id?: string;
  product_name?: string;
  requirement_id?: string;
  status?: string;
  task_type?: string;
  title?: string;
  updated_at?: string;
};

type TaskDetailItem = TaskListItem & {
  graph_runs?: unknown[];
  input?: unknown;
  input_json?: unknown;
  module_code?: string;
  output?: unknown;
  output_json?: unknown;
  pending_review?: unknown;
  product_context?: unknown;
  requirement_snapshot?: unknown;
  version_id?: string;
};

type PendingReviewListItem = {
  ai_task_id: string;
  content?: Record<string, unknown>;
  created_at?: string;
  id: string;
  stage?: string;
  status?: string;
  updated_at?: string;
  version: number;
};

type TaskWritebackIssueResponse = {
  id: string;
  source_task_id?: string;
  status?: string;
  title?: string;
};

type TaskWritebackResultResponse = {
  idempotency_key?: string;
  issues?: TaskWritebackIssueResponse[];
  status?: string;
  task_id?: string;
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
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function mapTaskRecord(task: TaskListItem): TaskCenterTaskRecord {
  return {
    createdAt: formatListDate(task.created_at ?? task.updated_at),
    createdAtValue: task.created_at ?? task.updated_at,
    currentStep: task.current_step ?? undefined,
    id: task.id,
    label: task.title ?? task.task_type ?? task.id,
    owner: task.created_by ?? '-',
    product: task.product_name ?? task.product_id ?? '-',
    productId: task.product_id,
    requirementId: task.requirement_id,
    status: task.status ?? '-',
    type: task.task_type ?? '-',
  };
}

export async function fetchTaskCenterTasks(
  query: TaskCenterTaskQuery = {},
): Promise<TaskCenterTaskListResult> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'created_by', query.owner);
  appendQueryParam(params, 'product_id', query.productId);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'task_type', query.taskType);
  appendQueryParam(params, 'created_from', query.createdFrom);
  appendQueryParam(params, 'created_to', query.createdTo);
  appendRemoteListParams(params, query);
  const taskQueryString = params.toString();
  const taskPath = taskQueryString ? `/api/ai-tasks?${taskQueryString}` : '/api/ai-tasks';
  const tasks = await apiRequest<ListResponse<TaskListItem>>(taskPath, { token });

  return {
    page: tasks.page ?? query.page ?? 1,
    pageSize: tasks.page_size ?? query.pageSize ?? 10,
    performance: tasks.performance,
    rows: tasks.items.map(mapTaskRecord),
    total: tasks.total,
  };
}

export async function fetchTaskCenterTaskDetail(
  taskId: string,
): Promise<TaskCenterTaskDetailRecord> {
  const token = requireAccessToken();
  const detail = await apiRequest<TaskDetailItem>(`/api/ai-tasks/${taskId}`, { token });
  const input = normalizeObjectRecord(detail.input) ?? {};
  const productContext =
    normalizeObjectRecord(input.product_context) ??
    normalizeObjectRecord(detail.product_context) ??
    {};
  const product = normalizeObjectRecord(productContext.product) ?? {};
  const version = normalizeObjectRecord(productContext.version) ?? {};
  const module = normalizeObjectRecord(productContext.module) ?? {};
  const requirementSnapshot =
    normalizeObjectRecord(input.requirement_snapshot) ??
    normalizeObjectRecord(detail.requirement_snapshot) ??
    {};
  const output = detail.output ?? detail.output_json;
  const outputRecord = normalizeObjectRecord(output);
  const pendingReview = normalizeObjectRecord(detail.pending_review);
  const graphRunIds = Array.isArray(detail.graph_runs)
    ? detail.graph_runs
        .map((run) => {
          const graphRun = normalizeObjectRecord(run);
          return formatUnknownValue(graphRun?.id ?? graphRun?.status ?? run);
        })
        .filter((runId) => runId !== '-')
    : [];

  return {
    createdAt: formatListDate(detail.created_at ?? detail.updated_at),
    createdAtValue: detail.created_at ?? detail.updated_at,
    currentStep: formatUnknownValue(detail.current_step),
    graphRunIds,
    id: detail.id,
    inputJson: detail.input ?? detail.input_json ?? {},
    label: detail.title ?? detail.task_type ?? detail.id,
    moduleName: formatUnknownValue(module.name ?? module.code ?? detail.module_code),
    outputJson: output ?? {},
    outputSummary: formatUnknownValue(outputRecord?.summary ?? output),
    owner: detail.created_by ?? '-',
    pendingReviewId:
      typeof pendingReview?.id === 'string' && pendingReview.id ? pendingReview.id : undefined,
    product: formatUnknownValue(product.name ?? product.code ?? detail.product_id),
    productId: detail.product_id,
    productName: formatUnknownValue(product.name ?? product.code ?? detail.product_id),
    requirementId: detail.requirement_id,
    requirementTitle: formatUnknownValue(
      requirementSnapshot.title ?? requirementSnapshot.summary ?? detail.requirement_id,
    ),
    status: detail.status ?? '-',
    type: detail.task_type ?? '-',
    versionName: formatUnknownValue(version.name ?? version.code ?? detail.version_id),
  };
}

export async function startTaskCenterTask(taskId: string) {
  const token = requireAccessToken();
  return apiRequest<{ review_id: string; status: string }>(`/api/ai-tasks/${taskId}/start`, {
    method: 'POST',
    token,
  });
}

export async function batchCancelTaskCenterTasks(
  payload: TaskBatchCancelPayload,
): Promise<TaskBatchCancelResult> {
  const token = requireAccessToken();
  const result = await apiRequest<TaskBatchCancelResponse>('/api/ai-tasks/batch-cancel', {
    body: payload,
    method: 'POST',
    token,
  });
  return {
    batchId: result.batch_id,
    reason: result.reason,
    skipped: result.skipped,
    skippedCount: result.skipped_count,
    updated: result.updated,
    updatedCount: result.updated_count,
  };
}

export async function batchRetryTaskCenterTasks(
  payload: TaskBatchRetryPayload,
): Promise<TaskBatchRetryResult> {
  const token = requireAccessToken();
  const result = await apiRequest<TaskBatchRetryResponse>('/api/ai-tasks/batch-retry', {
    body: payload,
    method: 'POST',
    token,
  });
  return {
    batchId: result.batch_id,
    reason: result.reason,
    retried: result.retried,
    retriedCount: result.retried_count,
    skipped: result.skipped,
    skippedCount: result.skipped_count,
    updated: result.updated,
    updatedCount: result.updated_count,
  };
}

function mapPendingReviewRecord(review: PendingReviewListItem): TaskCenterReviewRecord {
  return {
    aiTaskId: review.ai_task_id,
    contentSummary: formatUnknownValue(review.content?.summary),
    createdAt: review.created_at ? formatListDate(review.created_at) : undefined,
    id: review.id,
    stage: review.stage ?? '-',
    status: review.status ?? '-',
    updatedAt: review.updated_at ? formatListDate(review.updated_at) : undefined,
    version: review.version,
  };
}

export async function fetchTaskCenterPendingReviewList(
  query: TaskCenterReviewListQuery = {},
): Promise<RemoteListResult<TaskCenterReviewRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'ai_task_id', query.aiTaskId);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const path = queryString ? `/api/reviews/pending?${queryString}` : '/api/reviews/pending';
  const reviews = await apiRequest<ListResponse<PendingReviewListItem>>(path, { token });

  return {
    page: reviews.page ?? query.page ?? 1,
    pageSize: reviews.page_size ?? query.pageSize ?? 10,
    performance: reviews.performance,
    rows: reviews.items.map(mapPendingReviewRecord),
    total: reviews.total,
  };
}

export async function fetchTaskCenterPendingReviews(
  query: TaskCenterReviewListQuery = {},
): Promise<TaskCenterReviewRecord[]> {
  const reviews = await fetchTaskCenterPendingReviewList(query);
  return reviews.rows;
}

export async function approveTaskCenterReview(reviewId: string, version: number) {
  const token = requireAccessToken();
  return apiRequest<{ review_status: string; task_status: string }>(
    `/api/reviews/${reviewId}/approve`,
    {
      body: { version },
      method: 'POST',
      token,
    },
  );
}

export async function editApproveTaskCenterReview(
  reviewId: string,
  version: number,
  editedContent: Record<string, unknown>,
) {
  const token = requireAccessToken();
  return apiRequest<{ review_status: string; task_status: string }>(
    `/api/reviews/${reviewId}/edit-approve`,
    {
      body: { edited_content: editedContent, version },
      method: 'POST',
      token,
    },
  );
}

export async function rejectTaskCenterReview(
  reviewId: string,
  version: number,
  decisionReason: string,
) {
  const token = requireAccessToken();
  return apiRequest<{ review_status: string; task_status: string }>(
    `/api/reviews/${reviewId}/reject`,
    {
      body: { decision_reason: decisionReason, version },
      method: 'POST',
      token,
    },
  );
}

export async function requestTaskCenterReviewMoreInfo(
  reviewId: string,
  version: number,
  questions: string[],
) {
  const token = requireAccessToken();
  return apiRequest<{ review_status: string; task_status: string }>(
    `/api/reviews/${reviewId}/request-more-info`,
    {
      body: { questions, version },
      method: 'POST',
      token,
    },
  );
}

export async function submitTaskCenterMoreInfo(taskId: string, answers: TaskMoreInfoAnswer[]) {
  const token = requireAccessToken();
  return apiRequest<{ id: string; status: string }>(`/api/ai-tasks/${taskId}/more-info`, {
    body: { answers },
    method: 'POST',
    token,
  });
}

function technicalSolutionTitleFromDesignTask(task: TaskCenterTaskRecord) {
  const title = task.label.replace(/^产品详细设计[:：]\s*/, '').trim();
  return `技术方案：${title || task.label}`;
}

function developmentPlanningTitleFromTechnicalSolutionTask(task: TaskCenterTaskRecord) {
  const title = task.label.replace(/^技术方案[:：]\s*/, '').trim();
  return `开发计划：${title || task.label}`;
}

function automatedTestingTitleFromTechnicalSolutionTask(task: TaskCenterTaskRecord) {
  const title = task.label.replace(/^技术方案[:：]\s*/, '').trim();
  return `自动化测试：${title || task.label}`;
}

function releaseReadinessTitleFromTechnicalSolutionTask(task: TaskCenterTaskRecord) {
  const title = task.label.replace(/^技术方案[:：]\s*/, '').trim();
  return `发布评估：${title || task.label}`;
}

function postReleaseAnalysisTitleFromReleaseReadinessTask(task: TaskCenterTaskRecord) {
  const title = task.label.replace(/^发布评估[:：]\s*/, '').trim();
  return `上线后分析：${title || task.label}`;
}

export async function createTechnicalSolutionTask(task: TaskCenterTaskRecord) {
  const token = requireAccessToken();
  if (!task.requirementId) {
    throw new ApiRequestError({
      code: 'VALIDATION_ERROR',
      message: '缺少需求编号，无法创建技术方案任务。',
      status: 400,
    });
  }
  return apiRequest<{ id: string; status: string }>('/api/ai-tasks', {
    body: {
      input: { product_detail_design_task_id: task.id },
      requirement_id: task.requirementId,
      task_type: 'technical_solution',
      title: technicalSolutionTitleFromDesignTask(task),
    },
    method: 'POST',
    token,
  });
}

export async function createDevelopmentPlanningTask(task: TaskCenterTaskRecord) {
  const token = requireAccessToken();
  if (!task.requirementId) {
    throw new ApiRequestError({
      code: 'VALIDATION_ERROR',
      message: '缺少需求编号，无法创建开发计划任务。',
      status: 400,
    });
  }
  return apiRequest<{ id: string; status: string }>('/api/ai-tasks', {
    body: {
      input: { technical_solution_task_id: task.id },
      requirement_id: task.requirementId,
      task_type: 'development_planning',
      title: developmentPlanningTitleFromTechnicalSolutionTask(task),
    },
    method: 'POST',
    token,
  });
}

export async function createAutomatedTestingTask(task: TaskCenterTaskRecord) {
  const token = requireAccessToken();
  if (!task.requirementId) {
    throw new ApiRequestError({
      code: 'VALIDATION_ERROR',
      message: '缺少需求编号，无法创建自动化测试任务。',
      status: 400,
    });
  }
  return apiRequest<{ id: string; status: string }>('/api/ai-tasks', {
    body: {
      input: { technical_solution_task_id: task.id },
      requirement_id: task.requirementId,
      task_type: 'automated_testing',
      title: automatedTestingTitleFromTechnicalSolutionTask(task),
    },
    method: 'POST',
    token,
  });
}

export async function createReleaseReadinessTask(task: TaskCenterTaskRecord) {
  const token = requireAccessToken();
  if (!task.requirementId) {
    throw new ApiRequestError({
      code: 'VALIDATION_ERROR',
      message: '缺少需求编号，无法创建发布评估任务。',
      status: 400,
    });
  }
  return apiRequest<{ id: string; status: string }>('/api/ai-tasks', {
    body: {
      input: { technical_solution_task_id: task.id },
      requirement_id: task.requirementId,
      task_type: 'release_readiness',
      title: releaseReadinessTitleFromTechnicalSolutionTask(task),
    },
    method: 'POST',
    token,
  });
}

export async function createPostReleaseAnalysisTask(task: TaskCenterTaskRecord) {
  const token = requireAccessToken();
  if (!task.requirementId) {
    throw new ApiRequestError({
      code: 'VALIDATION_ERROR',
      message: '缺少需求编号，无法创建上线后分析任务。',
      status: 400,
    });
  }
  return apiRequest<{ id: string; status: string }>('/api/ai-tasks', {
    body: {
      input: { release_readiness_task_id: task.id },
      requirement_id: task.requirementId,
      task_type: 'post_release_analysis',
      title: postReleaseAnalysisTitleFromReleaseReadinessTask(task),
    },
    method: 'POST',
    token,
  });
}

function mapTaskWritebackResult(
  response: TaskWritebackResultResponse,
  fallbackTaskId: string,
): TaskWritebackResultRecord {
  return {
    idempotencyKey: response.idempotency_key ?? `mock_issue:${fallbackTaskId}`,
    issues: (response.issues ?? []).map((issue) => ({
      id: issue.id,
      sourceTaskId: issue.source_task_id,
      status: issue.status ?? '-',
      title: issue.title ?? issue.id,
    })),
    status: response.status ?? '-',
    taskId: response.task_id ?? fallbackTaskId,
  };
}

export async function fetchTaskWritebackResult(
  taskId: string,
): Promise<TaskWritebackResultRecord> {
  const token = requireAccessToken();
  const result = await apiRequest<TaskWritebackResultResponse>(
    `/api/writeback/results/${taskId}`,
    { token },
  );
  return mapTaskWritebackResult(result, taskId);
}

export async function createTaskWritebackResult(
  taskId: string,
): Promise<TaskWritebackResultRecord> {
  const token = requireAccessToken();
  const result = await apiRequest<TaskWritebackResultResponse>(
    `/api/writeback/results/${taskId}`,
    {
      method: 'POST',
      token,
    },
  );
  return mapTaskWritebackResult(result, taskId);
}

export async function fetchTaskMarkdown(taskId: string): Promise<string> {
  const token = requireAccessToken();
  const response = await fetch(`${API_BASE_URL}/api/export/tasks/${taskId}/markdown`, {
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
      message: payload?.detail?.message ?? `API request failed: ${response.status}`,
      status: response.status,
      traceId: payload?.detail?.trace_id,
    });
    if (response.status === 401) {
      handleUnauthorizedApiResponse();
    }
    throw requestError;
  }
  return response.text();
}
