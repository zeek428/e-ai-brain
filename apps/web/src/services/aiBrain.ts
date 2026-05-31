import type {
  AuditRecord,
  BugRecord,
  KnowledgeRecord,
  ProductContextOption,
  ProductRecord,
  ProductVersionOption,
  RequirementRecord,
  UserRecord,
} from '../data/management';
import { navigateTo } from '../utils/navigation';

const configuredApiBaseUrl = process.env.UMI_APP_API_BASE_URL ?? '';
const API_BASE_URL = configuredApiBaseUrl.endsWith('/')
  ? configuredApiBaseUrl.slice(0, -1)
  : configuredApiBaseUrl;

type ApiEnvelope<T> = {
  data: T;
};

type ApiErrorPayload = {
  detail?: {
    code?: string;
    message?: string;
    trace_id?: string;
  };
};

type ListResponse<T> = {
  items: T[];
  total: number;
};

const ACCESS_TOKEN_STORAGE_KEY = 'ai_brain_access_token';
const CURRENT_USER_STORAGE_KEY = 'ai_brain_current_user';

export class ApiRequestError extends Error {
  code?: string;
  status: number;
  traceId?: string;

  constructor({
    code,
    message,
    status,
    traceId,
  }: {
    code?: string;
    message: string;
    status: number;
    traceId?: string;
  }) {
    super(message);
    this.name = 'ApiRequestError';
    this.code = code;
    this.status = status;
    this.traceId = traceId;
  }
}

export type LoginResponse = {
  access_token: string;
  user: CurrentUserResponse;
};

export type CurrentUserResponse = {
  display_name: string;
  id: string;
  roles: string[];
  username: string;
};

export type ProductResponse = {
  code?: string;
  description?: string | null;
  id: string;
  name?: string;
  owner_team?: string | null;
  status?: string;
};

export type RequirementResponse = {
  id: string;
  status: string;
};

export type TaskCenterTaskRecord = {
  id: string;
  label: string;
  owner: string;
  productId?: string;
  requirementId?: string;
  status: string;
  type: string;
};

export type TaskCenterReviewRecord = {
  aiTaskId: string;
  contentSummary: string;
  id: string;
  stage: string;
  status: string;
  version: number;
};

export type OperationalMetricRecord = {
  category: string;
  id: string;
  name: string;
  status: string;
  updatedAt: string;
  value: string;
};

export type UserInsightRecord = {
  category: string;
  id: string;
  owner: string;
  status: string;
  summary: string;
  updatedAt: string;
};

export type ProductGitRepositoryOption = {
  defaultBranch: string;
  id: string;
  label: string;
  name: string;
  projectId?: string | null;
  projectPath?: string | null;
  provider: string;
  status: string;
};

export type GitLabMergeRequestPreview = {
  author: string;
  changedFileCount: number;
  changedFilesSummary: unknown[];
  mrIid: number;
  repositoryId: string;
  sourceBranch?: string;
  targetBranch?: string;
  title: string;
  webUrl?: string;
  writebackAllowed: boolean;
};

export type GitLabMergeRequestSnapshot = {
  diffLimitBytes?: number;
  diffSizeBytes?: number;
  id: string;
  mrIid: number;
  repositoryId: string;
};

export type CodeReviewReportRecord = {
  executor?: unknown;
  findings: unknown[];
  gitlabWritebackPerformed: boolean;
  id: string;
  riskLevel: string;
  status: string;
  summary: string;
};

type ProductListItem = {
  code?: string;
  current_version_name?: string;
  id: string;
  module_count?: number;
  name: string;
  owner_team?: string | null;
  status?: string;
};

type ProductVersionListItem = {
  code?: string;
  id: string;
  name: string;
  product_id: string;
  status?: string;
};

export type ProductMutationPayload = {
  code?: string;
  description?: string;
  display_order?: number;
  name?: string;
  owner_team?: string;
  status?: string;
};

export type RequirementMutationPayload = {
  content?: string;
  module_code?: string;
  priority?: string;
  product_id?: string;
  title?: string;
  version_id?: string;
};

export type ProductVersionMutationPayload = {
  code?: string;
  description?: string;
  name: string;
  release_date?: string;
  start_date?: string;
  status?: string;
};

export type BugMutationPayload = {
  assignee?: string;
  description?: string;
  duplicate_of_bug_id?: string;
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

export type KnowledgeDocumentMutationPayload = {
  content?: string;
  doc_type?: string;
  index_status?: string;
  permission_roles?: string[];
  tags?: string[];
  title?: string;
};

export type UserMutationPayload = {
  display_name?: string;
  password?: string;
  roles?: string[];
  status?: string;
  username?: string;
};

type RequirementListItem = {
  content?: string;
  created_at?: string;
  created_by?: string;
  id: string;
  module_code?: string | null;
  priority?: string;
  product_id: string;
  status?: string;
  title: string;
  updated_at?: string;
  version_id?: string;
};

type KnowledgeDocumentListItem = {
  content?: string;
  created_at?: string;
  doc_type?: string;
  id: string;
  index_status?: string;
  permission_roles?: string[];
  tags?: string[];
  title: string;
  updated_at?: string;
};

type AuditEventListItem = {
  actor_id?: string;
  created_at?: string;
  event_type: string;
  id: string;
  result?: string;
  subject_id?: string;
  subject_type?: string;
};

type BugListItem = {
  assignee?: string | null;
  description?: string;
  id: string;
  module_code?: string | null;
  product_id?: string;
  severity?: string;
  source?: string;
  status?: string;
  title: string;
  version_id?: string | null;
};

type TaskListItem = {
  created_by?: string;
  id: string;
  product_id?: string;
  requirement_id?: string;
  status?: string;
  task_type?: string;
  title?: string;
};

type ProductGitRepositoryListItem = {
  default_branch?: string;
  git_provider?: string;
  id: string;
  name: string;
  project_id?: string | null;
  project_path?: string | null;
  status?: string;
};

type GitLabMergeRequestPreviewResponse = {
  author?: unknown;
  changed_file_count?: number;
  changed_files_summary?: unknown[];
  mr_iid: number;
  repository_id: string;
  source_branch?: string;
  target_branch?: string;
  title?: string;
  web_url?: string;
  writeback_allowed?: boolean;
};

type GitLabMergeRequestSnapshotResponse = {
  diff_limit_bytes?: number;
  diff_size_bytes?: number;
  id: string;
  mr_iid: number;
  repository_id: string;
};

type CodeReviewReportResponse = {
  executor?: unknown;
  findings?: unknown[];
  gitlab_writeback_performed?: boolean;
  id: string;
  risk_level?: string;
  status?: string;
  summary?: string;
};

type PendingReviewListItem = {
  ai_task_id: string;
  content?: Record<string, unknown>;
  id: string;
  stage?: string;
  status?: string;
  version: number;
};

type FlexibleListItem = Record<string, unknown> & {
  created_at?: string;
  id?: string;
  status?: string;
  updated_at?: string;
};

type UserListItem = {
  display_name: string;
  id: string;
  roles?: string[];
  status?: string;
  username: string;
};

export async function apiRequest<T>(
  path: string,
  options: {
    method?: string;
    token?: string;
    body?: unknown;
  } = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: options.body ? JSON.stringify(options.body) : undefined,
    headers: {
      'Content-Type': 'application/json',
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    },
    method: options.method ?? 'GET',
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
    if (response.status === 401 && !path.startsWith('/api/auth/login')) {
      handleUnauthorizedApiResponse();
    }
    throw requestError;
  }
  const payload = (await response.json()) as ApiEnvelope<T>;
  return payload.data;
}

export function getAccessToken() {
  const storedToken =
    typeof globalThis.localStorage === 'undefined'
      ? undefined
      : globalThis.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  return storedToken || process.env.UMI_APP_API_TOKEN || undefined;
}

function requireAccessToken() {
  const token = getAccessToken();
  if (!token) {
    throw new ApiRequestError({
      code: 'AUTH_REQUIRED',
      message: '缺少访问令牌，请先登录后再加载真实数据。',
      status: 401,
    });
  }
  return token;
}

export function saveAccessToken(token: string) {
  if (typeof globalThis.localStorage === 'undefined') {
    return;
  }
  globalThis.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
}

export function saveCurrentUser(user: CurrentUserResponse) {
  if (!user || typeof globalThis.localStorage === 'undefined') {
    return;
  }
  globalThis.localStorage.setItem(CURRENT_USER_STORAGE_KEY, JSON.stringify(user));
}

export function getStoredCurrentUser(): CurrentUserResponse | undefined {
  if (typeof globalThis.localStorage === 'undefined') {
    return undefined;
  }
  const value = globalThis.localStorage.getItem(CURRENT_USER_STORAGE_KEY);
  if (!value) {
    return undefined;
  }
  try {
    return JSON.parse(value) as CurrentUserResponse;
  } catch {
    globalThis.localStorage.removeItem(CURRENT_USER_STORAGE_KEY);
    return undefined;
  }
}

export function clearAccessToken() {
  if (typeof globalThis.localStorage === 'undefined') {
    return;
  }
  globalThis.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  globalThis.localStorage.removeItem(CURRENT_USER_STORAGE_KEY);
}

function handleUnauthorizedApiResponse() {
  clearAccessToken();
  if (typeof window === 'undefined') {
    return;
  }
  const { pathname, search } = window.location;
  if (pathname === '/login') {
    return;
  }
  const target = `${pathname}${search}`;
  navigateTo(`/login?redirect=${encodeURIComponent(target)}`);
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const loginResponse = await apiRequest<LoginResponse>('/api/auth/login', {
    body: { username, password },
    method: 'POST',
  });
  saveAccessToken(loginResponse.access_token);
  saveCurrentUser(loginResponse.user);
  return loginResponse;
}

export async function fetchCurrentUser(): Promise<CurrentUserResponse> {
  const token = requireAccessToken();
  const user = await apiRequest<CurrentUserResponse>('/api/auth/me', { token });
  saveCurrentUser(user);
  return user;
}

export async function logout(): Promise<void> {
  const token = getAccessToken();
  clearAccessToken();
  if (!token) {
    return;
  }
  try {
    await apiRequest<{ success: boolean }>('/api/auth/logout', {
      method: 'POST',
      token,
    });
  } catch {
    // Local logout should still complete if the server token is already expired.
  }
}

function formatListDate(value?: string) {
  if (!value) {
    return '-';
  }
  return value.replace('T', ' ').replace(/\.\d+/, '').replace('+00:00', '').slice(0, 16);
}

function normalizeProductStatus(status?: string): ProductRecord['status'] {
  return status === 'inactive' ? 'inactive' : 'active';
}

function normalizePriority(priority?: string): RequirementRecord['priority'] {
  if (priority === 'P0' || priority === 'P2') {
    return priority;
  }
  return 'P1';
}

function normalizeRequirementStatus(status?: string): RequirementRecord['status'] {
  if (
    status === 'approved' ||
    status === 'closed' ||
    status === 'draft' ||
    status === 'pending_approval' ||
    status === 'rejected' ||
    status === 'task_created'
  ) {
    return status;
  }
  return 'draft';
}

function normalizeKnowledgeStatus(status?: string): KnowledgeRecord['status'] {
  if (
    status === 'failed' ||
    status === 'indexed' ||
    status === 'pending_index' ||
    status === 'review_pending'
  ) {
    return status;
  }
  return 'pending_index';
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
  return source === 'ai_auto_test' ? 'ai_auto_test' : 'manual_test';
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

function formatGitLabAuthor(value: unknown): string {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const author = value as Record<string, unknown>;
    return formatUnknownValue(author.name ?? author.username);
  }
  return formatUnknownValue(value);
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

export async function fetchManagementProducts(): Promise<ProductRecord[]> {
  const token = requireAccessToken();
  const products = await apiRequest<ListResponse<ProductListItem>>('/api/products', { token });
  const versionsByProductId = new Map(
    await Promise.all(
      products.items.map(async (product) => {
        const versions = await apiRequest<ListResponse<ProductVersionListItem>>(
          `/api/products/${product.id}/versions`,
          { token },
        );
        return [product.id, versions.items] as const;
      }),
    ),
  );

  return products.items.map((product) => ({
    code: product.code ?? product.id,
    id: product.id,
    moduleCount: product.module_count ?? 0,
    name: product.name,
    ownerTeam: product.owner_team ?? '-',
    status: normalizeProductStatus(product.status),
    version:
      product.current_version_name ??
      versionsByProductId.get(product.id)?.find((version) => version.status === 'active')?.name ??
      versionsByProductId.get(product.id)?.[0]?.name ??
      '未配置',
  }));
}

export async function createManagementProduct(payload: ProductMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<ProductResponse>('/api/products', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateManagementProduct(productId: string, payload: ProductMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<ProductResponse>(`/api/products/${productId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteManagementProduct(productId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/products/${productId}`, {
    method: 'DELETE',
    token,
  });
}

function mapProductVersionOption(version: ProductVersionListItem): ProductVersionOption {
  return {
    code: version.code ?? version.id,
    id: version.id,
    name: version.name,
    status: version.status ?? '-',
  };
}

export async function createProductVersion(
  productId: string,
  payload: ProductVersionMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<ProductVersionListItem>(`/api/products/${productId}/versions`, {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function fetchProductContextOptions(): Promise<ProductContextOption[]> {
  const token = requireAccessToken();
  const products = await apiRequest<ListResponse<ProductListItem>>('/api/products?active_only=true', {
    token,
  });

  return Promise.all(
    products.items.map(async (product) => {
      const versions = await apiRequest<ListResponse<ProductVersionListItem>>(
        `/api/products/${product.id}/versions?active_only=true`,
        { token },
      );

      return {
        code: product.code ?? product.id,
        id: product.id,
        name: product.name,
        versions: versions.items.map(mapProductVersionOption),
      };
    }),
  );
}

export async function fetchManagementUsers(): Promise<UserRecord[]> {
  const token = requireAccessToken();
  const users = await apiRequest<ListResponse<UserListItem>>('/api/users', { token });

  return users.items.map((user) => {
    const roles = user.roles ?? [];
    return {
      displayName: user.display_name,
      id: user.id,
      roles,
      rolesText: roles.join(', ') || '-',
      status: user.status === 'inactive' ? 'inactive' : 'active',
      username: user.username,
    };
  });
}

export async function createManagementUser(payload: UserMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<UserListItem>('/api/users', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateManagementUser(userId: string, payload: UserMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<UserListItem>(`/api/users/${userId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteManagementUser(userId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/users/${userId}`, {
    method: 'DELETE',
    token,
  });
}

export async function fetchManagementRequirements(): Promise<RequirementRecord[]> {
  const token = requireAccessToken();
  const [products, requirements] = await Promise.all([
    apiRequest<ListResponse<ProductListItem>>('/api/products', { token }),
    apiRequest<ListResponse<RequirementListItem>>('/api/requirements', { token }),
  ]);
  const productCodeById = new Map(
    products.items.map((product) => [product.id, product.code ?? product.id]),
  );

  return requirements.items.map((requirement) => ({
    content: requirement.content,
    id: requirement.id,
    moduleCode: requirement.module_code ?? undefined,
    owner: requirement.created_by ?? '-',
    priority: normalizePriority(requirement.priority),
    product: productCodeById.get(requirement.product_id) ?? requirement.product_id,
    productId: requirement.product_id,
    status: normalizeRequirementStatus(requirement.status),
    title: requirement.title,
    updatedAt: formatListDate(requirement.updated_at ?? requirement.created_at),
    versionId: requirement.version_id,
  }));
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

export async function fetchManagementKnowledge(): Promise<KnowledgeRecord[]> {
  const token = requireAccessToken();
  const documents = await apiRequest<ListResponse<KnowledgeDocumentListItem>>(
    '/api/knowledge/documents',
    { token },
  );

  return documents.items.map((document) => ({
    content: document.content,
    documentType: document.doc_type ?? '-',
    id: document.id,
    ownerRole: document.permission_roles?.join(', ') || '-',
    permissionRoles: document.permission_roles,
    status: normalizeKnowledgeStatus(document.index_status),
    tags: document.tags,
    title: document.title,
    updatedAt: formatListDate(document.updated_at ?? document.created_at),
  }));
}

export async function createManagementKnowledgeDocument(payload: KnowledgeDocumentMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<{ id: string }>('/api/knowledge/documents', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateManagementKnowledgeDocument(
  documentId: string,
  payload: KnowledgeDocumentMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<{ id: string }>(`/api/knowledge/documents/${documentId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteManagementKnowledgeDocument(documentId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/knowledge/documents/${documentId}`, {
    method: 'DELETE',
    token,
  });
}

export async function fetchManagementAudit(): Promise<AuditRecord[]> {
  const token = requireAccessToken();
  const events = await apiRequest<ListResponse<AuditEventListItem>>('/api/audit/events', { token });

  return events.items.map((event) => ({
    actor: event.actor_id ?? '-',
    eventType: event.event_type,
    id: event.id,
    result: event.result === 'failed' ? 'failed' : 'success',
    subject:
      event.subject_type && event.subject_id ? `${event.subject_type}: ${event.subject_id}` : '-',
    timestamp: formatListDate(event.created_at),
  }));
}

export async function fetchManagementBugs(): Promise<BugRecord[]> {
  const token = requireAccessToken();
  const bugs = await apiRequest<ListResponse<BugListItem>>('/api/bugs', { token });

  return bugs.items.map((bug) => ({
    assignee: bug.assignee ?? '-',
    description: bug.description,
    id: bug.id,
    module: bug.module_code ?? '-',
    productId: bug.product_id,
    severity: normalizeBugSeverity(bug.severity),
    source: normalizeBugSource(bug.source),
    status: normalizeBugStatus(bug.status),
    title: bug.title,
    versionId: bug.version_id ?? undefined,
  }));
}

export async function createManagementBug(payload: BugMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<{ id: string }>('/api/bugs', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateManagementBug(bugId: string, payload: BugMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<{ id: string }>(`/api/bugs/${bugId}`, {
    body: payload,
    method: 'PATCH',
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

export async function fetchTaskCenterTasks(): Promise<TaskCenterTaskRecord[]> {
  const token = requireAccessToken();
  const tasks = await apiRequest<ListResponse<TaskListItem>>('/api/ai-tasks', { token });

  return tasks.items.map((task) => ({
    id: task.id,
    label: task.title ?? task.task_type ?? task.id,
    owner: task.created_by ?? '-',
    productId: task.product_id,
    requirementId: task.requirement_id,
    status: task.status ?? '-',
    type: task.task_type ?? '-',
  }));
}

export async function startTaskCenterTask(taskId: string) {
  const token = requireAccessToken();
  return apiRequest<{ review_id: string; status: string }>(`/api/ai-tasks/${taskId}/start`, {
    method: 'POST',
    token,
  });
}

export async function fetchTaskCenterPendingReviews(): Promise<TaskCenterReviewRecord[]> {
  const token = requireAccessToken();
  const reviews = await apiRequest<ListResponse<PendingReviewListItem>>('/api/reviews/pending', {
    token,
  });

  return reviews.items.map((review) => ({
    aiTaskId: review.ai_task_id,
    contentSummary: formatUnknownValue(review.content?.summary),
    id: review.id,
    stage: review.stage ?? '-',
    status: review.status ?? '-',
    version: review.version,
  }));
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

function technicalSolutionTitleFromDesignTask(task: TaskCenterTaskRecord) {
  const title = task.label.replace(/^产品详细设计[:：]\s*/, '').trim();
  return `技术方案：${title || task.label}`;
}

function codeReviewTitleFromTechnicalSolutionTask(task: TaskCenterTaskRecord, mrIid: number) {
  const title = task.label.replace(/^技术方案[:：]\s*/, '').trim();
  return `Code Review：${title || task.label} MR !${mrIid}`;
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

export async function fetchProductGitRepositories(
  productId: string,
): Promise<ProductGitRepositoryOption[]> {
  const token = requireAccessToken();
  const repositories = await apiRequest<ListResponse<ProductGitRepositoryListItem>>(
    `/api/products/${productId}/git-repositories?active_only=true`,
    { token },
  );

  return repositories.items.map((repository) => ({
    defaultBranch: repository.default_branch ?? 'main',
    id: repository.id,
    label: repository.project_path
      ? `${repository.name} (${repository.project_path})`
      : repository.name,
    name: repository.name,
    projectId: repository.project_id,
    projectPath: repository.project_path,
    provider: repository.git_provider ?? 'gitlab',
    status: repository.status ?? '-',
  }));
}

export async function previewGitLabMergeRequest(
  repositoryId: string,
  mrIid: number,
): Promise<GitLabMergeRequestPreview> {
  const token = requireAccessToken();
  const preview = await apiRequest<GitLabMergeRequestPreviewResponse>(
    `/api/devops/gitlab/merge-requests/${repositoryId}/${mrIid}/preview`,
    { token },
  );

  return {
    author: formatGitLabAuthor(preview.author),
    changedFileCount: preview.changed_file_count ?? 0,
    changedFilesSummary: preview.changed_files_summary ?? [],
    mrIid: preview.mr_iid,
    repositoryId: preview.repository_id,
    sourceBranch: preview.source_branch,
    targetBranch: preview.target_branch,
    title: preview.title ?? `MR !${preview.mr_iid}`,
    webUrl: preview.web_url,
    writebackAllowed: preview.writeback_allowed ?? false,
  };
}

export async function snapshotGitLabMergeRequest({
  mrIid,
  repositoryId,
  requirementId,
  technicalSolutionTaskId,
}: {
  mrIid: number;
  repositoryId: string;
  requirementId: string;
  technicalSolutionTaskId: string;
}): Promise<GitLabMergeRequestSnapshot> {
  const token = requireAccessToken();
  const snapshot = await apiRequest<GitLabMergeRequestSnapshotResponse>(
    `/api/devops/gitlab/merge-requests/${repositoryId}/${mrIid}/snapshot`,
    {
      body: {
        requirement_id: requirementId,
        technical_solution_task_id: technicalSolutionTaskId,
      },
      method: 'POST',
      token,
    },
  );

  return {
    diffLimitBytes: snapshot.diff_limit_bytes,
    diffSizeBytes: snapshot.diff_size_bytes,
    id: snapshot.id,
    mrIid: snapshot.mr_iid,
    repositoryId: snapshot.repository_id,
  };
}

export async function createCodeReviewTask(
  task: TaskCenterTaskRecord,
  gitlabMrSnapshotId: string,
  mrIid: number,
) {
  const token = requireAccessToken();
  if (!task.requirementId) {
    throw new ApiRequestError({
      code: 'VALIDATION_ERROR',
      message: '缺少需求编号，无法创建 Code Review 任务。',
      status: 400,
    });
  }
  return apiRequest<{ id: string; status: string }>('/api/ai-tasks', {
    body: {
      input: { gitlab_mr_snapshot_id: gitlabMrSnapshotId },
      requirement_id: task.requirementId,
      task_type: 'code_review',
      title: codeReviewTitleFromTechnicalSolutionTask(task, mrIid),
    },
    method: 'POST',
    token,
  });
}

export async function fetchCodeReviewReport(taskId: string): Promise<CodeReviewReportRecord> {
  const token = requireAccessToken();
  const report = await apiRequest<CodeReviewReportResponse>(
    `/api/ai-tasks/${taskId}/code-review-report`,
    { token },
  );

  return {
    executor: report.executor,
    findings: report.findings ?? [],
    gitlabWritebackPerformed: report.gitlab_writeback_performed ?? false,
    id: report.id,
    riskLevel: report.risk_level ?? '-',
    status: report.status ?? '-',
    summary: report.summary ?? '-',
  };
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

function mapOperationalMetrics(
  category: string,
  items: FlexibleListItem[],
): OperationalMetricRecord[] {
  return items.map((item, index) => ({
    category,
    id: formatUnknownValue(item.id ?? `${category}-${index}`),
    name: formatUnknownValue(
      firstKnownValue(item, ['name', 'metric_name', 'repository_name', 'release_name', 'title']),
    ),
    status: formatUnknownValue(item.status),
    updatedAt: formatListDate(
      formatUnknownValue(firstKnownValue(item, ['updated_at', 'created_at', 'observed_at', 'date'])),
    ),
    value: formatUnknownValue(firstKnownValue(item, ['value', 'count', 'score', 'summary'])),
  }));
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

function mapUserInsights(category: string, items: FlexibleListItem[]): UserInsightRecord[] {
  return items.map((item, index) => ({
    category,
    id: formatUnknownValue(item.id ?? `${category}-${index}`),
    owner: formatUnknownValue(firstKnownValue(item, ['user_id', 'owner_id', 'created_by', 'actor_id'])),
    status: formatUnknownValue(item.status),
    summary: formatUnknownValue(
      firstKnownValue(item, ['summary', 'content', 'feedback_text', 'suggestion', 'feature_code']),
    ),
    updatedAt: formatListDate(
      formatUnknownValue(firstKnownValue(item, ['updated_at', 'created_at', 'observed_at', 'window_start'])),
    ),
  }));
}

export async function fetchUserInsights(): Promise<UserInsightRecord[]> {
  const token = requireAccessToken();
  const [usageMetrics, feedbackItems, iterationSuggestions] = await Promise.all([
    apiRequest<ListResponse<FlexibleListItem>>('/api/insights/usage-metrics', { token }),
    apiRequest<ListResponse<FlexibleListItem>>('/api/insights/user-feedback', { token }),
    apiRequest<ListResponse<FlexibleListItem>>('/api/planning/iteration-suggestions', { token }),
  ]);

  return [
    ...mapUserInsights('使用趋势', usageMetrics.items),
    ...mapUserInsights('用户反馈', feedbackItems.items),
    ...mapUserInsights('迭代建议', iterationSuggestions.items),
  ];
}
