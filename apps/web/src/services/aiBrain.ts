import type {
  AuditRecord,
  BugRecord,
  KnowledgeRecord,
  ProductRecord,
  RequirementRecord,
  UserRecord,
} from '../data/management';

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
};

export type ProductResponse = {
  code?: string;
  description?: string | null;
  id: string;
  name?: string;
  owner_team?: string | null;
  status?: string;
};

export type VersionResponse = {
  id: string;
};

export type RequirementResponse = {
  id: string;
  status: string;
};

export type GeneratedTaskResponse = {
  task_id: string;
  task_status: string;
};

export type StartedTaskResponse = {
  id: string;
  status: string;
  review_id: string;
  current_step?: string;
};

export type TaskDetailResponse = {
  id: string;
  status: string;
  current_step?: string;
  output?: {
    kind?: string;
  };
};

export type LifecycleResponse = {
  status: string;
  summary: {
    downstream_count: number;
    risk_count: number;
  };
};

export type MvpWorkflowResult = {
  requirementId: string;
  taskId: string;
  reviewId: string;
  taskStatus: string;
  currentStep: string;
  downstreamCount: number;
  riskCount: number;
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
    throw new ApiRequestError({
      code: payload?.detail?.code,
      message: payload?.detail?.message ?? `API request failed: ${response.status}`,
      status: response.status,
      traceId: payload?.detail?.trace_id,
    });
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

export function clearAccessToken() {
  if (typeof globalThis.localStorage === 'undefined') {
    return;
  }
  globalThis.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const loginResponse = await apiRequest<LoginResponse>('/api/auth/login', {
    body: { username, password },
    method: 'POST',
  });
  saveAccessToken(loginResponse.access_token);
  return loginResponse;
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

export async function fetchManagementProducts(): Promise<ProductRecord[]> {
  const token = requireAccessToken();
  const products = await apiRequest<ListResponse<ProductListItem>>('/api/products', { token });

  return products.items.map((product) => ({
    code: product.code ?? product.id,
    id: product.id,
    moduleCount: product.module_count ?? 0,
    name: product.name,
    ownerTeam: product.owner_team ?? '-',
    status: normalizeProductStatus(product.status),
    version: product.current_version_name ?? '未配置',
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

export async function runMvpWorkflow(): Promise<MvpWorkflowResult> {
  const suffix = Date.now().toString(36);
  const token = requireAccessToken();
  const product = await apiRequest<ProductResponse>('/api/products', {
    method: 'POST',
    token,
    body: {
      code: `demo-${suffix}`,
      name: `AI Brain Demo ${suffix}`,
      owner_team: 'AI Platform',
    },
  });
  const version = await apiRequest<VersionResponse>(`/api/products/${product.id}/versions`, {
    method: 'POST',
    token,
    body: { code: `v-${suffix}`, name: 'v1 MVP', status: 'active' },
  });
  const requirement = await apiRequest<RequirementResponse>('/api/requirements', {
    method: 'POST',
    token,
    body: {
      content: '从前端触发需求审批到产品详细设计人工确认点。',
      priority: 'P1',
      product_id: product.id,
      title: `前端演示需求 ${suffix}`,
      version_id: version.id,
    },
  });
  await apiRequest<RequirementResponse>(`/api/requirements/${requirement.id}/approve`, {
    method: 'POST',
    token,
    body: { comment: '前端演示流审批通过' },
  });
  const generated = await apiRequest<GeneratedTaskResponse>(
    `/api/requirements/${requirement.id}/generate-task`,
    {
      method: 'POST',
      token,
    },
  );
  const started = await apiRequest<StartedTaskResponse>(
    `/api/ai-tasks/${generated.task_id}/start`,
    {
      method: 'POST',
      token,
    },
  );
  const task = await apiRequest<TaskDetailResponse>(`/api/ai-tasks/${generated.task_id}`, {
    token,
  });
  const lifecycle = await apiRequest<LifecycleResponse>(
    `/api/lifecycle/context?subject_type=requirement&subject_id=${requirement.id}&direction=both&include_risks=true`,
    { token },
  );

  return {
    currentStep: task.current_step ?? started.current_step ?? 'unknown',
    downstreamCount: lifecycle.summary.downstream_count,
    requirementId: requirement.id,
    reviewId: started.review_id,
    riskCount: lifecycle.summary.risk_count,
    taskId: generated.task_id,
    taskStatus: task.status,
  };
}
