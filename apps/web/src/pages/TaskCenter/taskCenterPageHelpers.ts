import type { TableProps } from 'antd';

import type { ManagementListQuery } from '../../components/ManagementListPage';
import type { RemoteRowsError } from '../../hooks/useRemoteRows';
import type {
  CurrentUserResponse,
  GitLabMergeRequestPreview,
  GitLabMergeRequestSnapshot,
  RemoteListPerformance,
  TaskCenterReviewRecord,
  TaskCenterTaskRecord,
} from '../../services/aiBrain';

export const taskStatusLabels: Record<string, { color: string; label: string }> = {
  cancelled: { color: 'default', label: '已取消' },
  completed: { color: 'green', label: '已完成' },
  draft: { color: 'default', label: '草稿' },
  failed: { color: 'red', label: '失败' },
  running: { color: 'blue', label: '运行中' },
  waiting_more_info: { color: 'orange', label: '待补充' },
  waiting_review: { color: 'gold', label: '待确认' },
  writing_back: { color: 'purple', label: '写回中' },
};

export const taskBatchCancellableStatuses = new Set([
  'draft',
  'running',
  'waiting_more_info',
  'waiting_review',
  'writing_back',
]);

export const taskBatchRetryableFailureSteps = new Set([
  'code_review_executor_failed',
  'model_gateway_failed',
]);

export const PENDING_REVIEW_TABLE_SCROLL = { x: 1040 } satisfies TableProps<TaskCenterReviewRecord>['scroll'];

export const taskTypeLabels: Record<string, string> = {
  automated_testing: '自动化测试',
  code_review: 'Code Review',
  development_planning: '开发计划',
  post_release_analysis: '上线后分析',
  product_detail_design: '产品详细设计',
  release_readiness: '发布评估',
  technical_solution: '技术方案',
};

export const writebackStatusLabels: Record<string, { color: string; label: string }> = {
  completed: { color: 'green', label: '已生成' },
  failed: { color: 'red', label: '失败' },
  not_written: { color: 'default', label: '未写回' },
};

const taskOperationRoles = new Set(['product_owner', 'rd_owner', 'reviewer']);

export function hasTaskOperationRole(user: CurrentUserResponse | undefined) {
  const roles = new Set(user?.roles ?? []);
  if (roles.has('admin')) {
    return true;
  }
  return Array.from(taskOperationRoles).some((role) => roles.has(role));
}

export type TaskActionItem = {
  key: string;
  label: string;
  onClick: () => void;
  type?: 'default' | 'primary';
};

export type RequestMoreInfoFormValues = {
  questions: string;
};

export type EditApproveFormValues = {
  summary: string;
};

export type RejectReviewFormValues = {
  reason: string;
};

export type SubmitMoreInfoFormValues = {
  answer: string;
};

export type TaskRowsState = {
  error?: RemoteRowsError;
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: TaskCenterTaskRecord[];
  status: 'error' | 'loading' | 'ready';
  total: number;
};

export type ReviewRowsState = {
  error?: RemoteRowsError;
  rows: TaskCenterReviewRecord[];
  status: 'error' | 'loading' | 'ready';
};

function normalizeQueryValue(value: unknown) {
  return String(value ?? '').trim();
}

function normalizeQueryDate(value: unknown, boundary: 'end' | 'start') {
  const raw = normalizeQueryValue(
    typeof value === 'object' &&
      value !== null &&
      'format' in value &&
      typeof value.format === 'function'
      ? value.format('YYYY-MM-DD')
      : value,
  );
  if (!raw) {
    return undefined;
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    return boundary === 'end' ? `${raw}T23:59:59Z` : `${raw}T00:00:00Z`;
  }
  return raw;
}

function normalizeQueryDateRange(value: unknown) {
  if (Array.isArray(value)) {
    return [value[0], value[1]] as const;
  }
  const [start = '', end = ''] = normalizeQueryValue(value).split(',');
  return [start, end] as const;
}

const taskSortFieldMap: Record<string, string> = {
  createdAt: 'created_at',
  label: 'title',
  owner: 'created_by',
  product: 'product_name',
  status: 'status',
  type: 'task_type',
};

export function buildTaskCenterQuery(query: ManagementListQuery) {
  const [createdFrom, createdTo] = normalizeQueryDateRange(query.filters.createdAtValue);
  return {
    createdFrom: normalizeQueryDate(createdFrom, 'start'),
    createdTo: normalizeQueryDate(createdTo, 'end'),
    keyword: normalizeQueryValue(query.filters.label) || undefined,
    owner: normalizeQueryValue(query.filters.owner) || undefined,
    page: query.page,
    pageSize: query.pageSize,
    productId: normalizeQueryValue(query.filters.productId) || undefined,
    sortField: query.sortField ? taskSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeQueryValue(query.filters.status) || undefined,
    taskType: normalizeQueryValue(query.filters.type) || undefined,
  };
}

export function splitTextLines(value: string) {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
}

export function formatFinding(finding: unknown, index: number) {
  if (!finding || typeof finding !== 'object' || Array.isArray(finding)) {
    return `${index + 1}. ${String(finding ?? '-')}`;
  }
  const item = finding as Record<string, unknown>;
  const filePath = item.file_path ?? item.file ?? item.path ?? item.filename;
  const line =
    item.line_start ??
    item.line ??
    item.line_number ??
    item.start_line ??
    item.lineStart;
  const location = [filePath, line ? `:${line}` : undefined].filter(Boolean).join('');
  const summary = item.message ?? item.summary ?? item.suggestion ?? JSON.stringify(item);
  return `${index + 1}. ${[item.severity, location, summary].filter(Boolean).join(' · ')}`;
}

function formatRiskLevel(level?: string) {
  if (level === 'high') {
    return '高';
  }
  if (level === 'medium') {
    return '中';
  }
  if (level === 'low') {
    return '低';
  }
  return level || '-';
}

export function formatRiskSummary(preview?: GitLabMergeRequestPreview) {
  const summary = preview?.riskSummary;
  if (!summary) {
    return '-';
  }
  const largestFile = summary.largestFile?.path
    ? `最大文件 ${summary.largestFile.path} (${summary.largestFile.lineCount ?? 0} 行)`
    : '无最大文件';
  return `${formatRiskLevel(summary.riskLevel)}风险 · ${summary.fileCount ?? 0} 文件 · +${
    summary.totalAdditions ?? 0
  }/-${summary.totalDeletions ?? 0} · ${largestFile}`;
}

export function formatPermissionDiagnostics(preview?: GitLabMergeRequestPreview) {
  const diagnostics = preview?.permissionDiagnostics;
  if (!diagnostics) {
    return '未返回诊断信息';
  }
  return [
    `Provider: ${diagnostics.provider ?? '-'}`,
    `Base URL: ${diagnostics.baseUrlConfigured ? '已配置' : '未配置'}`,
    `仓库路径: ${diagnostics.repositoryPathConfigured ? '已配置' : '未配置'}`,
    `凭据引用: ${diagnostics.credentialRefConfigured ? '已配置' : '未配置'}`,
    `Token: ${diagnostics.tokenAvailable ? '可用' : '不可用'}`,
    `远端回写: ${diagnostics.writebackAllowed ? '允许' : '只读'}`,
  ].join(' · ');
}

export function formatSnapshotDiffSummary(snapshot: GitLabMergeRequestSnapshot) {
  const summary = snapshot.diffChangeSummary;
  if (!summary || !snapshot.previousSnapshot) {
    return '首次快照，无上一快照对比';
  }
  return `新增 ${summary.addedFilesCount ?? 0} 文件，修改 ${
    summary.modifiedFilesCount ?? 0
  } 文件，移除 ${summary.removedFilesCount ?? 0} 文件`;
}

export function formatChangedFileSummary(file: unknown, index: number) {
  if (!file || typeof file !== 'object' || Array.isArray(file)) {
    return `${index + 1}. ${String(file ?? '-')}`;
  }
  const item = file as Record<string, unknown>;
  const path = item.path ?? item.file_path ?? item.file ?? item.filename ?? '-';
  return `${index + 1}. ${path} · +${item.additions ?? 0}/-${item.deletions ?? 0}`;
}
