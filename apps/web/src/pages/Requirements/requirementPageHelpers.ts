import type { ManagementListQuery } from '../../components/ManagementListPage';
import type { RequirementRecord } from '../../data/management';
import {
  ApiRequestError,
  type CurrentUserResponse,
  type RequirementListQuery,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';

export const statusLabels: Record<RequirementRecord['status'], { color: string; label: string }> = {
  accepted: { color: 'green', label: '已验收' },
  approved: { color: 'green', label: '需求池' },
  cancelled: { color: 'default', label: '已取消' },
  closed: { color: 'default', label: '已关闭' },
  code_reviewing: { color: 'purple', label: '代码评审中' },
  deferred: { color: 'default', label: '暂缓' },
  designing: { color: 'blue', label: '设计中' },
  developing: { color: 'geekblue', label: '开发中' },
  draft: { color: 'default', label: '草稿' },
  planned: { color: 'cyan', label: '已排期' },
  ready_for_dev: { color: 'lime', label: '待开发' },
  ready_for_release: { color: 'orange', label: '待发布' },
  rejected: { color: 'red', label: '已拒绝' },
  released: { color: 'green', label: '已发布' },
  submitted: { color: 'gold', label: '待评审' },
  testing: { color: 'volcano', label: '测试中' },
};

export type RequirementFormValues = {
  content: string;
  module_code?: string;
  priority: RequirementRecord['priority'];
  product_id: string;
  source: string;
  title: string;
  version_id?: string;
};

export type BatchScheduleFormValues = {
  product_id: string;
  reason?: string;
  version_id: string;
};

export type BatchAssignOwnerFormValues = {
  assignee: string;
  reason?: string;
};

export type BatchAdvanceStatusFormValues = {
  reason?: string;
  target_status: RequirementRecord['status'];
};

export type BatchGenerateTaskFormValues = {
  reason?: string;
};

export const batchAssignableStatuses = new Set<RequirementRecord['status']>([
  'accepted',
  'approved',
  'code_reviewing',
  'deferred',
  'designing',
  'developing',
  'draft',
  'planned',
  'ready_for_dev',
  'ready_for_release',
  'rejected',
  'released',
  'submitted',
  'testing',
]);

export const batchAdvanceTargetOptions: Array<{ label: string; value: RequirementRecord['status'] }> = [
  { label: '已排期', value: 'planned' },
  { label: '待开发', value: 'ready_for_dev' },
  { label: '开发中', value: 'developing' },
  { label: '代码评审中', value: 'code_reviewing' },
  { label: '测试中', value: 'testing' },
  { label: '待发布', value: 'ready_for_release' },
  { label: '已发布', value: 'released' },
  { label: '已验收', value: 'accepted' },
  { label: '暂缓', value: 'deferred' },
  { label: '已取消', value: 'cancelled' },
  { label: '已关闭', value: 'closed' },
];

const requirementSortFieldMap: Record<string, string> = {
  createdAt: 'created_at',
  id: 'id',
  priority: 'priority',
  product: 'product_name',
  source: 'source',
  status: 'status',
  title: 'title',
  versionName: 'version_name',
};

export const requirementSourceOptions = [
  { label: '业务部门', value: 'business_department' },
  { label: '产品规划', value: 'product_planning' },
  { label: '用户反馈', value: 'user_feedback' },
  { label: '内部调研', value: 'internal_research' },
  { label: '其他', value: 'other' },
];

export const requirementSourceLabels = requirementSourceOptions.reduce<Record<string, string>>(
  (labels, option) => ({ ...labels, [option.value]: option.label }),
  {},
);

export const requirementWriteRoles = new Set(['product_owner', 'rd_owner']);
export const requirementRejectRoles = new Set(['product_owner']);

export function hasAnyRequirementRole(
  user: CurrentUserResponse | undefined,
  allowedRoles: Set<string>,
) {
  const roles = new Set(user?.roles ?? []);
  if (roles.has('admin')) {
    return true;
  }
  return Array.from(allowedRoles).some((role) => roles.has(role));
}

export function formatRequirementDeleteError(error: unknown) {
  if (error instanceof ApiRequestError && error.code === 'RESOURCE_IN_USE') {
    const relatedCounts = error.detail?.related_counts as Record<string, unknown> | undefined;
    const taskCount = Number(relatedCounts?.ai_tasks ?? relatedCounts?.tasks ?? 0);
    const taskSummary =
      Number.isFinite(taskCount) && taskCount > 0 ? ` ${taskCount} 个 AI 任务` : ' AI 任务';
    return `无法删除需求，已生成${taskSummary}。请先在全链路或任务中心处理关联任务；如需求不再推进，可将需求关闭或取消。`;
  }
  return formatMutationError(error);
}

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

export function buildRequirementListQuery(query: ManagementListQuery): RequirementListQuery {
  return {
    page: query.page,
    pageSize: query.pageSize,
    priority: normalizeFilterText(query.filters.priority),
    product: normalizeFilterText(query.filters.product),
    productId: normalizeFilterText(query.filters.productId),
    source: normalizeFilterText(query.filters.source),
    sortField: query.sortField ? requirementSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
    title: normalizeFilterText(query.filters.title),
    version: normalizeFilterText(query.filters.versionName),
  };
}
