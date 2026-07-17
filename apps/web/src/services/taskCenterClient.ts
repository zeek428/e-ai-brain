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
  collaborationRunId?: string;
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
  workItemId?: string;
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
  agentLoop?: Record<string, unknown>;
  currentStep: string;
  executionContextManifest?: Record<string, unknown>;
  graphRunIds: string[];
  inputJson: unknown;
  moduleName: string;
  outputJson: unknown;
  outputSummary: string;
  pendingReviewId?: string;
  productName: string;
  qualityGate?: Record<string, unknown>;
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
  collaboration_run_id?: string;
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
  work_item_id?: string;
};

type TaskDetailItem = TaskListItem & {
  agent_loop?: unknown;
  execution_context_manifest?: unknown;
  graph_runs?: unknown[];
  input?: unknown;
  input_json?: unknown;
  module_code?: string;
  output?: unknown;
  output_json?: unknown;
  output_summary?: unknown;
  pending_review?: unknown;
  product_context?: unknown;
  quality_gate?: unknown;
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

const TASK_OUTPUT_SUMMARY_MARKERS = [
  '**整改状态',
  '整改状态：',
  '整改状态:',
  '## 整改',
  '**整改结果',
  '整改结果：',
  '整改结果:',
  '**执行结果',
  '执行结果：',
  '执行结果:',
  '**修复结果',
  '修复结果：',
  '修复结果:',
  '**处理结果',
  '处理结果：',
  '处理结果:',
  '**验证方式',
  '验证方式：',
  '验证方式:',
];

const ANSI_ESCAPE_CHARACTER = String.fromCharCode(27);
const ANSI_ESCAPE_PATTERN = new RegExp(`${ANSI_ESCAPE_CHARACTER}\\[[0-?]*[ -/]*[@-~]`, 'g');

function truncateReadableSummary(text: string) {
  const maxSummaryLength = 6000;
  if (text.length <= maxSummaryLength) {
    return text;
  }
  return `${text.slice(0, maxSummaryLength).trimEnd()}\n\n...（摘要已截断）`;
}

function stringAtPath(value: unknown, path: string[]) {
  let current = value;
  for (const key of path) {
    const record = normalizeObjectRecord(current);
    if (!record) {
      return undefined;
    }
    current = record[key];
  }
  return typeof current === 'string' && current.trim() ? current.trim() : undefined;
}

function stripCodexTokenHeader(text: string) {
  const tokenPattern = /^tokens used\s*\n\s*[\d,]+\s*$/gim;
  let tokenEndIndex = -1;
  let match: RegExpExecArray | null;
  while ((match = tokenPattern.exec(text)) !== null) {
    tokenEndIndex = match.index + match[0].length;
  }
  return tokenEndIndex >= 0 ? text.slice(tokenEndIndex).trim() : text;
}

function outputPreviewSummary(outputPreview: unknown) {
  if (typeof outputPreview !== 'string' || !outputPreview.trim()) {
    return undefined;
  }
  let text = outputPreview
    .replace(/\r\n/g, '\n')
    .replace(ANSI_ESCAPE_PATTERN, '')
    .trim();
  let markerIndex = -1;
  TASK_OUTPUT_SUMMARY_MARKERS.forEach((marker) => {
    const index = text.indexOf(marker);
    if (index >= 0 && (markerIndex < 0 || index < markerIndex)) {
      markerIndex = index;
    }
  });
  text = markerIndex >= 0 ? text.slice(markerIndex).trim() : stripCodexTokenHeader(text);
  text = text.replace(/^tokens used\s*\n\s*[\d,]+\s*/i, '').trim();
  if (!text || ((text.startsWith('{') || text.startsWith('[')) && text.includes('output_preview'))) {
    return undefined;
  }
  return truncateReadableSummary(text);
}

function readableTaskOutputSummary(output: unknown) {
  const summaryPaths = [
    ['summary'],
    ['output_summary'],
    ['result', 'summary'],
    ['result', 'output_summary'],
    ['result', 'result', 'summary'],
    ['result', 'result', 'output_summary'],
    ['result', 'parsed_output', 'summary'],
    ['result', 'parsed_output', 'output_summary'],
    ['result', 'parsed_output', 'result', 'summary'],
  ];
  for (const path of summaryPaths) {
    const summary = stringAtPath(output, path);
    if (summary) {
      return truncateReadableSummary(summary);
    }
  }

  const previewPaths = [
    ['output_preview'],
    ['result', 'output_preview'],
    ['result', 'result', 'output_preview'],
  ];
  for (const path of previewPaths) {
    const summary = outputPreviewSummary(stringAtPath(output, path));
    if (summary) {
      return summary;
    }
  }
  return undefined;
}

export function mapTaskRecord(task: TaskListItem): TaskCenterTaskRecord {
  return {
    collaborationRunId: task.collaboration_run_id ?? undefined,
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
    workItemId: task.work_item_id ?? undefined,
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
    agentLoop: normalizeObjectRecord(detail.agent_loop),
    createdAt: formatListDate(detail.created_at ?? detail.updated_at),
    createdAtValue: detail.created_at ?? detail.updated_at,
    currentStep: formatUnknownValue(detail.current_step),
    executionContextManifest: normalizeObjectRecord(detail.execution_context_manifest),
    graphRunIds,
    id: detail.id,
    inputJson: detail.input ?? detail.input_json ?? {},
    label: detail.title ?? detail.task_type ?? detail.id,
    moduleName: formatUnknownValue(module.name ?? module.code ?? detail.module_code),
    outputJson: output ?? {},
    outputSummary: formatUnknownValue(
      detail.output_summary ?? readableTaskOutputSummary(output) ?? outputRecord?.summary ?? output,
    ),
    owner: detail.created_by ?? '-',
    pendingReviewId:
      typeof pendingReview?.id === 'string' && pendingReview.id ? pendingReview.id : undefined,
    product: formatUnknownValue(product.name ?? product.code ?? detail.product_id),
    productId: detail.product_id,
    productName: formatUnknownValue(product.name ?? product.code ?? detail.product_id),
    qualityGate: normalizeObjectRecord(detail.quality_gate),
    requirementId: detail.requirement_id,
    requirementTitle: formatUnknownValue(
      requirementSnapshot.title ?? requirementSnapshot.summary ?? detail.requirement_id,
    ),
    status: detail.status ?? '-',
    type: detail.task_type ?? '-',
    versionName: formatUnknownValue(version.name ?? version.code ?? detail.version_id),
  };
}

export async function requestTaskAgentLoopTakeover(taskId: string, reason?: string) {
  const token = requireAccessToken();
  return apiRequest<{
    agent_loop: Record<string, unknown>;
    cancelled_runner_task_ids: string[];
    current_step: string;
    review_id: string;
    status: string;
    task_id: string;
  }>(`/api/ai-tasks/${taskId}/agent-loop/takeover`, {
    body: { reason: reason || null },
    method: 'POST',
    token,
  });
}

export async function startTaskCenterTask(taskId: string) {
  const token = requireAccessToken();
  return apiRequest<{ review_id: string; status: string }>(`/api/ai-tasks/${taskId}/start`, {
    method: 'POST',
    token,
  });
}

export async function cancelTaskCenterTask(taskId: string) {
  const token = requireAccessToken();
  return apiRequest<{ id: string; status: string }>(`/api/ai-tasks/${taskId}/cancel`, {
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
    contentSummary: formatUnknownValue(readableTaskOutputSummary(review.content) ?? review.content?.summary),
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
