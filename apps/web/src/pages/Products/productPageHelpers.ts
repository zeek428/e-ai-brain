import type { ManagementListQuery } from '../../components/ManagementListPage';
import type {
  ProductGitRepositoryRecord,
  ProductModuleRecord,
  ProductRecord,
  ProductRelatedSystemRecord,
  ProductVersionRecord,
} from '../../data/management';
import {
  ApiRequestError,
  type CurrentUserResponse,
  type ProductListQuery,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';

export type ProductFormValues = {
  code?: string;
  default_version_code?: string;
  default_version_name?: string;
  description?: string;
  name: string;
  owner_team?: string;
  status: ProductRecord['status'];
};

export type ResourceKind = 'module' | 'relatedSystem' | 'repository' | 'version';

export type ProductResourceFormValues = {
  code?: string;
  credential_ref?: string;
  default_branch?: string;
  description?: string;
  git_provider?: string;
  name: string;
  owner_team?: string;
  project_id?: string;
  project_path?: string;
  release_date?: string;
  remote_url?: string;
  repo_type?: string;
  root_path?: string;
  start_date?: string;
  status?: string;
};

export type ProductResourceEditor =
  | { kind: 'module'; record?: ProductModuleRecord; submitting: boolean }
  | { kind: 'relatedSystem'; record?: ProductRelatedSystemRecord; submitting: boolean }
  | { kind: 'repository'; record?: ProductGitRepositoryRecord; submitting: boolean }
  | { kind: 'version'; record?: ProductVersionRecord; submitting: boolean };

export const versionStatusLabels: Record<ProductVersionRecord['status'], { color: string; label: string }> = {
  active: { color: 'blue', label: '开发中' },
  archived: { color: 'default', label: '历史归档' },
  planning: { color: 'gold', label: '规划中' },
  released: { color: 'green', label: '已发布' },
  testing: { color: 'purple', label: '测试中' },
};

export const versionCreateStatusOptions = [
  { label: '规划中', value: 'planning' },
  { label: '开发中', value: 'active' },
];

export const activeStatusLabels: Record<'active' | 'inactive', { color: string; label: string }> = {
  active: { color: 'green', label: '启用' },
  inactive: { color: 'default', label: '停用' },
};

export function resourceEditorTitle(editor?: ProductResourceEditor) {
  if (!editor) {
    return '产品配置';
  }
  const action = editor.record ? '编辑' : '新增';
  if (editor.kind === 'version') {
    return `${action}版本`;
  }
  if (editor.kind === 'module') {
    return `${action}模块`;
  }
  if (editor.kind === 'relatedSystem') {
    return `${action}相关系统`;
  }
  return `${action} Git 资源`;
}

const productSortFieldMap: Record<string, string> = {
  code: 'code',
  moduleCount: 'module_count',
  name: 'name',
  ownerTeam: 'owner_team',
  status: 'status',
  version: 'current_version_name',
};

export function formatProductDeleteError(error: unknown) {
  if (error instanceof ApiRequestError && error.code === 'RESOURCE_IN_USE') {
    const relatedCounts = error.detail?.related_counts as Record<string, unknown> | undefined;
    const countItems = [
      { count: Number(relatedCounts?.requirements ?? 0), unit: '条需求' },
      { count: Number(relatedCounts?.ai_tasks ?? 0), unit: '个AI任务' },
      { count: Number(relatedCounts?.bugs ?? 0), unit: '个Bug' },
    ].filter((item) => item.count > 0);
    const summary = countItems.map((item) => `${item.count} ${item.unit}`).join('、');
    return summary
      ? `无法删除产品，仍关联 ${summary}。请先迁移或删除关联业务记录，也可以将产品状态改为停用。`
      : '无法删除产品，仍有关联业务记录。请先迁移或删除关联业务记录，也可以将产品状态改为停用。';
  }
  return formatMutationError(error);
}

export function canManageProductResources(user: CurrentUserResponse | undefined) {
  if (!user) {
    return true;
  }
  const roles = new Set(user.roles ?? []);
  const permissions = new Set(user.permissions ?? []);
  return (
    roles.has('admin') ||
    roles.has('product_owner') ||
    permissions.has('system.admin') ||
    permissions.has('product.manage')
  );
}

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

export function buildProductListQuery(query: ManagementListQuery): ProductListQuery {
  return {
    code: normalizeFilterText(query.filters.code),
    name: normalizeFilterText(query.filters.name),
    ownerTeam: normalizeFilterText(query.filters.ownerTeam),
    page: query.page,
    pageSize: query.pageSize,
    sortField: query.sortField ? productSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
  };
}
