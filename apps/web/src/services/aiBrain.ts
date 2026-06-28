import type {
  AuditRecord,
  BugRecord,
  KnowledgeRecord,
  ModelGatewayConfigRecord,
  ProductContextOption,
  ProductGitRepositoryRecord,
  ProductModuleRecord,
  ProductRecord,
  ProductRelatedSystemRecord,
  ProductVersionBranchConfigRecord,
  ProductVersionOption,
  ProductVersionRecord,
  RequirementRecord,
  UserRecord,
} from '../data/management';
import { formatUserRoles, type UserRoleDefinition } from '../data/roles';
import { formatDisplayDateTime } from '../utils/dateTime';
import {
  API_BASE_URL,
  ApiRequestError,
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
} from './apiClient';
import type {
  ApiEnvelope,
  ApiErrorPayload,
  ListResponse,
  RemoteListPerformance,
  RemoteListQueryEcho,
} from './apiClient';
import {
  getStoredCurrentUser,
  handleUnauthorizedApiResponse,
  requireAccessToken,
  setAuthLocalCacheClearHandler,
} from './authClient';
import type { ScopeGrant } from './authClient';

export { ApiRequestError, apiRequest };
export type { RemoteListPerformance, RemoteListQueryEcho };
export {
  AUTH_STATE_EVENT,
  clearAccessToken,
  fetchCurrentUser,
  getAccessToken,
  getStoredCurrentUser,
  login,
  logout,
  saveAccessToken,
  saveCurrentUser,
} from './authClient';
export type {
  CurrentUserResponse,
  LoginResponse,
  MenuTreeNode,
  ScopeGrant,
} from './authClient';
export { fetchItTeamDashboard } from './dashboardClient';
export type {
  DashboardAuditSummary,
  DashboardBugSummary,
  DashboardCacheMetadata,
  DashboardGitLabSummary,
  DashboardKnowledgeSummary,
  DashboardOnlineLogSummary,
  DashboardReviewSummary,
  DashboardStatusCount,
  DashboardSummary,
  DashboardTaskSummary,
  DashboardUsageMetricSummary,
  ItTeamDashboard,
} from './dashboardClient';

const PRODUCT_CONTEXT_PAGE_SIZE = 100;
const VERSION_CONTEXT_PAGE_SIZE = 100;
const CONTEXT_OPTION_MAX_PAGE_COUNT = 50;

export type PermissionRecord = {
  category?: string;
  code: string;
  description?: string;
  is_system?: boolean;
  name: string;
  risk_level?: string;
  status?: string;
};

export type MenuResourceRecord = {
  code: string;
  icon?: string;
  is_system?: boolean;
  menu_type?: string;
  name: string;
  parent_code?: string | null;
  path?: string | null;
  required_permissions?: string[];
  sort_order?: number;
  status?: string;
};

export type MenuResourceMutationPayload = {
  code?: string;
  icon?: string;
  menu_type?: string;
  name?: string;
  parent_code?: string | null;
  path?: string;
  required_permissions?: string[];
  sort_order?: number;
  status?: string;
};

export type SystemRoleRecord = UserRoleDefinition & {
  id: string;
  is_system: boolean;
  menu_codes: string[];
  permission_codes: string[];
  scopes: ScopeGrant[];
};

export type RbacPolicyMatrixRow = {
  category: string;
  diagnostics: Array<{
    code: string;
    level: string;
    message: string;
    permission_codes?: string[];
  }>;
  granted_menu_codes: string[];
  granted_permission_codes: string[];
  high_risk_permission_codes: string[];
  high_risk_permission_count: number;
  is_system: boolean;
  menu_count: number;
  missing_menu_permission_codes: string[];
  permission_count: number;
  required_permission_codes: string[];
  role_code: string;
  role_id: string;
  role_name: string;
  scope_count: number;
  scope_summary: string;
  scopes: ScopeGrant[];
  standalone_permission_codes: string[];
  status: string;
};

export type RbacPolicyMatrix = {
  menus: MenuResourceRecord[];
  permissions: PermissionRecord[];
  roles: SystemRoleRecord[];
  rows: RbacPolicyMatrixRow[];
  summary: {
    active_role_count: number;
    menu_count: number;
    permission_count: number;
    role_count: number;
    roles_with_high_risk_permissions: number;
    roles_with_menu_permission_gaps: number;
    scope_grant_count: number;
  };
};

export type UserPermissionDiagnosticCheck = {
  code: string;
  granted_by_roles?: Array<{
    role_code: string;
    role_name: string;
  }>;
  granted_menu_code?: string | null;
  known?: boolean;
  matched_menu?: {
    code: string;
    name?: string;
    path?: string;
  };
  matched_scopes?: ScopeGrant[];
  message: string;
  missing_permission_codes?: string[];
  permission?: {
    code: string;
    name?: string;
    risk_level?: string | null;
  };
  required_permission_codes?: string[];
  role_codes?: string[];
  status: 'allowed' | 'blocked' | string;
  target?: string;
};

export type UserPermissionDiagnostic = {
  checks: UserPermissionDiagnosticCheck[];
  decision: {
    allowed: boolean;
    blocked_reasons: string[];
    granted_reasons: string[];
  };
  effective: {
    menu_codes: string[];
    permission_codes: string[];
    role_codes: string[];
    scopes: ScopeGrant[];
  };
  user: {
    display_name?: string;
    id: string;
    roles: string[];
    status: string;
    username?: string;
  };
};

export type AssistantChatResponse = {
  content: string;
  conversationId: string;
  intent?: AssistantIntent;
  latencyMs: number;
  messageId: string;
  model: string;
  references: AssistantReference[];
  run?: AssistantChatRun;
  runId?: string;
  status?: string;
  suggestions: string[];
  toolResults: AssistantToolResult[];
};

export type AssistantChatRun = {
  assistant_message_id?: string;
  cancel_reason?: string;
  cancelled_at?: string;
  cancelled_by?: string;
  client_request_id?: string;
  conversation_id?: string;
  error_code?: string;
  error_message?: string;
  finished_at?: string;
  id: string;
  started_at?: string;
  status: string;
  user_message_id?: string;
};

export type AssistantRuntimeStatus = {
  checks?: Array<{
    action_label?: string;
    action_url?: string;
    code: string;
    description?: string;
    detail?: string;
    key?: string;
    label?: string;
    remediation?: string;
    required?: boolean;
    severity?: 'critical' | 'info' | 'warning' | string;
    status: string;
    url?: string;
  }>;
  chat_gateway: string;
  embedding_gateway: string;
  long_memory: string;
  mode: 'deterministic_only' | 'model_gateway' | string;
  model_gateway: string;
  operations?: {
    executor_queue?: {
      active_runners?: number;
      failed?: number;
      offline_runners?: number;
      oldest_pending_task_created_at?: string | null;
      oldest_pending_task_id?: string | null;
      queued?: number;
      running?: number;
      succeeded?: number;
      total_runners?: number;
      visible?: boolean;
    };
    model_gateway_recent_failure?: AssistantRuntimeFailure | null;
    recent_failures?: AssistantRuntimeFailure[];
  };
  ready?: boolean;
  warnings?: Array<{
    code?: string;
    message?: string;
  }>;
};

export type AssistantRuntimeFailure = {
  created_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  id: string;
  kind: string;
  label?: string;
  status?: string | null;
  title?: string | null;
  updated_at?: string | null;
  url?: string | null;
};

export type AssistantIntent = {
  confidence?: number;
  intent_code?: string;
  required_refs?: string[];
  summary?: string;
};

export type AssistantReference = {
  action?: string;
  chunk_count?: number;
  chunk_index?: number;
  created_at?: string;
  document_count?: number;
  document_id?: string;
  folder_path?: string;
  id: string;
  index_status?: string;
  knowledge_space_id?: string;
  permission_label?: string;
  source_module?: string;
  summary?: string;
  prompt?: string;
  title: string;
  type: string;
  updated_at?: string;
  url: string;
};

export type AssistantDraftTemplate = {
  available?: boolean;
  category?: string;
  code: string;
  dependencies?: string[];
  description?: string;
  draft_action?: string;
  name: string;
  prompt: string;
  roles?: string[];
  source_module?: string;
  target_resource?: string;
  template_version?: string;
  wizard_steps?: string[];
};

export type AssistantMetricsSummary = {
  action_run_failed_count?: number;
  action_run_succeeded_count?: number;
  action_run_success_rate?: number;
  action_run_total?: number;
  chat_run_average_duration_ms?: number | null;
  chat_run_cancel_rate?: number;
  chat_run_cancelled_count?: number;
  chat_run_failed_count?: number;
  chat_run_failure_rate?: number;
  chat_run_model_failed_count?: number;
  chat_run_model_failure_rate?: number;
  chat_run_running_count?: number;
  chat_run_succeeded_count?: number;
  chat_run_success_rate?: number;
  chat_run_total?: number;
  draft_adoption_rate?: number;
  draft_cancelled_count?: number;
  draft_confirmed_count?: number;
  draft_expired_count?: number;
  draft_failed_count?: number;
  draft_inferred_viewed_count?: number;
  draft_pending_count?: number;
  draft_resolution_rate?: number;
  draft_total?: number;
  draft_deeplink_viewed_count?: number;
  draft_detail_viewed_count?: number;
  draft_tracked_viewed_count?: number;
  draft_user_modified_count?: number;
  draft_user_modified_rate?: number;
  draft_viewed_count?: number;
  failed_run_repair_rate?: number;
  failed_run_repaired_count?: number;
  failed_run_total?: number;
  knowledge_reference_count?: number;
  knowledge_reference_hit_count?: number;
  knowledge_reference_hit_rate?: number;
  knowledge_reference_request_count?: number;
  message_total?: number;
  reference_total?: number;
  reference_usage_rate?: number;
  referenced_user_message_count?: number;
  scheduled_job_run_failed_count?: number;
  scheduled_job_run_succeeded_count?: number;
  scheduled_job_run_success_rate?: number;
  scheduled_job_run_total?: number;
  user_message_total?: number;
};

export type AssistantDraftActionMetric = {
  action: string;
  cancelled_count?: number;
  confirmed_count?: number;
  expired_count?: number;
  failed_count?: number;
  pending_count?: number;
  total?: number;
};

export type AssistantFunnelStage = {
  count?: number;
  key: string;
  label: string;
  sort_order?: number;
};

export type AssistantRunAttributionMetric = {
  count?: number;
  key: string;
  label: string;
};

export type AssistantMetricsFilters = {
  action?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  product_id?: string | null;
  role?: string | null;
  window_days?: number | null;
};

export type AssistantMetricsProductDimension = {
  chat_run_total?: number;
  draft_adoption_rate?: number;
  draft_confirmed_count?: number;
  draft_total?: number;
  message_total?: number;
  product_id: string;
  scheduled_job_run_failed_count?: number;
  scheduled_job_run_succeeded_count?: number;
  scheduled_job_run_success_rate?: number;
  scheduled_job_run_total?: number;
};

export type AssistantMetricsRoleDimension = {
  chat_run_total?: number;
  draft_total?: number;
  message_total?: number;
  role: string;
  scheduled_job_run_total?: number;
};

export type AssistantMetricsDailyTrend = {
  action_run_failed_count?: number;
  action_run_succeeded_count?: number;
  action_run_total?: number;
  chat_run_failed_count?: number;
  chat_run_succeeded_count?: number;
  chat_run_total?: number;
  day: string;
  draft_confirmed_count?: number;
  draft_total?: number;
  message_total?: number;
  scheduled_job_run_failed_count?: number;
  scheduled_job_run_succeeded_count?: number;
  scheduled_job_run_total?: number;
};

export type AssistantDraftActionDailyTrend = AssistantDraftActionMetric & {
  day: string;
};

export type AssistantMetrics = {
  dimensions?: {
    products?: AssistantMetricsProductDimension[];
    roles?: AssistantMetricsRoleDimension[];
  };
  drafts_by_action: AssistantDraftActionMetric[];
  filters?: AssistantMetricsFilters;
  funnel?: {
    stages?: AssistantFunnelStage[];
  };
  instrumentation?: {
    notes?: Array<{
      code?: string;
      level?: string;
      message?: string;
    }>;
    view_metrics?: {
      effective_viewed_count?: number;
      inferred_legacy_count?: number;
      tracked_count?: number;
    };
  };
  scheduled_job_run_attribution?: {
    items?: AssistantRunAttributionMetric[];
    total?: number;
  };
  summary: AssistantMetricsSummary;
  trends?: {
    daily?: AssistantMetricsDailyTrend[];
    drafts_by_action_daily?: AssistantDraftActionDailyTrend[];
  };
  window?: {
    days?: number | null;
    label?: string;
  };
};

export type AssistantMetricDetailItem = {
  action?: string;
  created_at?: string;
  description?: string;
  id: string;
  status?: string;
  title: string;
  type: string;
  updated_at?: string;
  url?: string;
};

export type AssistantMetricDetails = {
  filters?: AssistantMetricsFilters;
  items: AssistantMetricDetailItem[];
  metric: string;
  title: string;
  total: number;
  window?: {
    days?: number | null;
    label?: string;
  };
};

export type AssistantMetricsQueryParams = {
  action?: string;
  dateFrom?: string;
  dateTo?: string;
  productId?: string;
  role?: string;
  windowDays?: number;
};

export type AssistantMetricsExport = {
  content: AssistantMetrics | string;
  contentType: string;
  filename: string;
  format: string;
};

export type AssistantActionReferenceConfig = {
  action_key: string;
  aliases: string[];
  created_at?: string;
  created_by?: string | null;
  enabled: boolean;
  enterprise_id?: string | null;
  id: string;
  metadata_json: Record<string, unknown>;
  permissions: string[];
  prompt: string;
  roles: string[];
  rollout_json: Record<string, unknown>;
  sort_order: number;
  summary: string;
  template_version?: string | null;
  title: string;
  updated_at?: string;
  updated_by?: string | null;
  url: string;
};

export type AssistantRoleQuickTask = {
  analytics_key?: string;
  enabled?: boolean;
  key: string;
  label: string;
  permissions?: string[];
  prompt: string;
  sort_order?: number;
  target_draft_type?: string | null;
};

export type AssistantRoleQuickTaskGroup = {
  enabled?: boolean;
  key: string;
  label: string;
  roles?: string[];
  sort_order?: number;
  tasks: AssistantRoleQuickTask[];
};

export type AssistantRoleQuickTaskConfig = {
  analytics_key?: string | null;
  created_at?: string;
  created_by?: string | null;
  enabled: boolean;
  enterprise_id?: string | null;
  group_enabled: boolean;
  group_key: string;
  group_label: string;
  group_roles: string[];
  group_sort_order: number;
  id: string;
  metadata_json: Record<string, unknown>;
  permissions: string[];
  prompt: string;
  rollout_json: Record<string, unknown>;
  sort_order: number;
  target_draft_type?: string | null;
  task_key: string;
  template_version?: string | null;
  title: string;
  updated_at?: string;
  updated_by?: string | null;
};

export type AssistantToolResultItem = {
  action?: string;
  client_draft_id?: string;
  draft_id?: string;
  payload?: Record<string, unknown>;
  preview?: AssistantActionDraftPreview;
  requires_confirmation?: boolean;
  risk_level?: string;
  server_draft_id?: string;
  status?: string;
  title?: string;
  [key: string]: unknown;
};

export type AssistantToolResult = {
  intent?: string;
  items?: AssistantToolResultItem[];
  references?: AssistantReference[];
  summary?: Record<string, unknown>;
  tool: string;
};

export const ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY =
  'ai_brain_assistant_scheduled_job_draft';
export const ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY =
  'ai_brain_assistant_plugin_action_draft';
export const ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY =
  'ai_brain_assistant_plugin_connection_draft';
export const ASSISTANT_DRAFT_RESOLUTION_STORAGE_KEY =
  'ai_brain_assistant_draft_resolution';
export const ASSISTANT_RECENT_REFERENCES_STORAGE_KEY =
  'ai_brain_assistant_recent_references';
export const ASSISTANT_ROUTE_PROMPT_STORAGE_KEY =
  'ai_brain_assistant_route_prompt';

const ASSISTANT_SCOPED_STORAGE_KEYS = [
  ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
  ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
  ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
  ASSISTANT_DRAFT_RESOLUTION_STORAGE_KEY,
  ASSISTANT_RECENT_REFERENCES_STORAGE_KEY,
  ASSISTANT_ROUTE_PROMPT_STORAGE_KEY,
];

const ASSISTANT_ROUTE_PROMPT_TTL_MS = 10 * 60 * 1000;

export function assistantScopedStorageKey(baseKey: string) {
  const userId = getStoredCurrentUser()?.id;
  return userId ? `${baseKey}:${userId}` : `${baseKey}:anonymous`;
}

export type AssistantRoutePromptRecord = {
  created_at: number;
  prompt: string;
  reference_id?: string;
  reference_type?: string;
};

function normalizeAssistantRoutePromptRecord(value: unknown): AssistantRoutePromptRecord | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  const record = value as Partial<AssistantRoutePromptRecord>;
  const prompt = String(record.prompt ?? '').trim();
  if (!prompt) {
    return undefined;
  }
  const createdAt = Number(record.created_at ?? Date.now());
  if (Number.isFinite(createdAt) && Date.now() - createdAt > ASSISTANT_ROUTE_PROMPT_TTL_MS) {
    return undefined;
  }
  const referenceId = String(record.reference_id ?? '').trim();
  const referenceType = String(record.reference_type ?? '').trim();
  return {
    created_at: Number.isFinite(createdAt) ? createdAt : Date.now(),
    prompt,
    ...(referenceId ? { reference_id: referenceId } : {}),
    ...(referenceType ? { reference_type: referenceType } : {}),
  };
}

export function rememberAssistantRoutePrompt(params: {
  prompt?: string | null;
  referenceId?: string | null;
  referenceType?: string | null;
}) {
  if (typeof window === 'undefined') {
    return;
  }
  const prompt = String(params.prompt ?? '').trim();
  if (!prompt) {
    return;
  }
  const record: AssistantRoutePromptRecord = {
    created_at: Date.now(),
    prompt,
  };
  const referenceId = String(params.referenceId ?? '').trim();
  const referenceType = String(params.referenceType ?? '').trim();
  if (referenceId) {
    record.reference_id = referenceId;
  }
  if (referenceType) {
    record.reference_type = referenceType;
  }
  window.sessionStorage.setItem(
    assistantScopedStorageKey(ASSISTANT_ROUTE_PROMPT_STORAGE_KEY),
    JSON.stringify(record),
  );
}

export function consumeAssistantRoutePrompt(params: {
  referenceId?: string | null;
  referenceType?: string | null;
} = {}) {
  if (typeof window === 'undefined') {
    return undefined;
  }
  const storageKey = assistantScopedStorageKey(ASSISTANT_ROUTE_PROMPT_STORAGE_KEY);
  let record: AssistantRoutePromptRecord | undefined;
  try {
    record = normalizeAssistantRoutePromptRecord(
      JSON.parse(window.sessionStorage.getItem(storageKey) ?? 'null'),
    );
  } catch {
    record = undefined;
  }
  if (!record) {
    window.sessionStorage.removeItem(storageKey);
    return undefined;
  }
  const referenceId = String(params.referenceId ?? '').trim();
  const referenceType = String(params.referenceType ?? '').trim();
  const isMismatchedReference =
    (referenceId && record.reference_id && record.reference_id !== referenceId)
    || (referenceType && record.reference_type && record.reference_type !== referenceType);
  window.sessionStorage.removeItem(storageKey);
  return isMismatchedReference ? undefined : record;
}

function clearAssistantLocalCachesForCurrentUser() {
  if (typeof globalThis.localStorage === 'undefined' || typeof globalThis.sessionStorage === 'undefined') {
    return;
  }
  ASSISTANT_SCOPED_STORAGE_KEYS.forEach((baseKey) => {
    const scopedKey = assistantScopedStorageKey(baseKey);
    globalThis.localStorage.removeItem(scopedKey);
    globalThis.sessionStorage.removeItem(scopedKey);
    globalThis.localStorage.removeItem(baseKey);
    globalThis.sessionStorage.removeItem(baseKey);
  });
}

setAuthLocalCacheClearHandler(clearAssistantLocalCachesForCurrentUser);

export type AssistantDraftResourceType =
  | 'ai_agent'
  | 'ai_skill'
  | 'ai_task'
  | 'assistant_analysis'
  | 'plugin_action'
  | 'plugin_connection'
  | 'scheduled_job';

export type AssistantDraftResolutionRecord = {
  resource_id: string;
  resource_type: AssistantDraftResourceType;
  scheduled_job_run_id?: string;
  title?: string;
};

export type AssistantDraftResolutionMap = Record<string, AssistantDraftResolutionRecord>;

export type AssistantScheduledJobDraft = {
  draftId?: string;
  payload: Record<string, unknown>;
  title?: string;
};

export type AssistantPluginActionDraft = AssistantScheduledJobDraft;
export type AssistantPluginConnectionDraft = AssistantScheduledJobDraft;

export function readAssistantDraftResolutions(): AssistantDraftResolutionMap {
  if (typeof window === 'undefined') {
    return {};
  }
  try {
    const parsed = JSON.parse(
      window.sessionStorage.getItem(assistantScopedStorageKey(ASSISTANT_DRAFT_RESOLUTION_STORAGE_KEY)) ?? '{}',
    ) as unknown;
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as AssistantDraftResolutionMap;
    }
  } catch {
    // Ignore malformed session data and let the next save repair it.
  }
  return {};
}

export function rememberAssistantDraftResolution(params: {
  draftId?: string;
  resourceId?: string;
  resourceType: AssistantDraftResourceType;
  scheduledJobRunId?: string;
  title?: string;
}) {
  if (typeof window === 'undefined' || !params.draftId || !params.resourceId) {
    return;
  }
  const resolutions = readAssistantDraftResolutions();
  const nextRecord: AssistantDraftResolutionRecord = {
    resource_id: params.resourceId,
    resource_type: params.resourceType,
  };
  if (params.title) {
    nextRecord.title = params.title;
  }
  if (params.scheduledJobRunId) {
    nextRecord.scheduled_job_run_id = params.scheduledJobRunId;
  }
  window.sessionStorage.setItem(
    assistantScopedStorageKey(ASSISTANT_DRAFT_RESOLUTION_STORAGE_KEY),
    JSON.stringify({ ...resolutions, [params.draftId]: nextRecord }),
  );
}

export function resolveAssistantDraftResourceId(
  payload: Record<string, unknown>,
  resourceType: AssistantDraftResourceType,
): string | undefined {
  const prerequisiteIds = Array.isArray(payload.assistant_prerequisite_draft_ids)
    ? payload.assistant_prerequisite_draft_ids.map(String).filter(Boolean)
    : [];
  if (!prerequisiteIds.length) {
    return undefined;
  }
  const resolutions = readAssistantDraftResolutions();
  const matchingResolution = prerequisiteIds
    .map((draftId) => resolutions[draftId])
    .find((resolution) => resolution?.resource_type === resourceType && resolution.resource_id);
  return matchingResolution?.resource_id;
}

export type AssistantConversationSummary = {
  collapsedConversationIds?: string[];
  collapsedMessageCount?: number;
  commandSignature?: string;
  contextScope?: string;
  createdAt?: string;
  duplicateConversationIds?: string[];
  duplicateCount?: number;
  id: string;
  lastMessageAt?: string;
  messageCount: number;
  productId?: string;
  sourceMessageHash?: string;
  title: string;
  updatedAt?: string;
};

export type AssistantConversationPage = {
  items: AssistantConversationSummary[];
  limit: number;
  nextCursor?: string;
  total: number;
};

export type AssistantConversationMessage = {
  cancelledAt?: string;
  clientRequestId?: string;
  completedAt?: string;
  content: string;
  createdAt?: string;
  errorCode?: string;
  failedAt?: string;
  id: string;
  intent?: AssistantIntent;
  model?: string;
  productId?: string;
  role: 'assistant' | 'user';
  runId?: string;
  status?: string;
  references: AssistantReference[];
  suggestions: string[];
  toolResults: AssistantToolResult[];
};

type AssistantChatApiResponse = {
  conversation_id: string;
  latency_ms?: number;
  message: {
    cancelled_at?: string;
    client_request_id?: string;
    completed_at?: string;
    content?: string;
    error_code?: string;
    failed_at?: string;
    id?: string;
    intent?: AssistantIntent;
    references?: AssistantReference[];
    role?: string;
    run_id?: string;
    status?: string;
    tool_results?: AssistantToolResult[];
  };
  model?: string;
  references?: AssistantReference[];
  run?: AssistantChatRun;
  run_id?: string;
  suggestions?: string[];
  tool_results?: AssistantToolResult[];
};

type AssistantConversationApiRecord = {
  collapsed_conversation_ids?: string[];
  collapsed_message_count?: number;
  command_signature?: string;
  context_scope?: string;
  created_at?: string;
  duplicate_conversation_ids?: string[];
  duplicate_count?: number;
  id: string;
  last_message_at?: string;
  message_count?: number;
  product_id?: string;
  source_message_hash?: string;
  title?: string;
  updated_at?: string;
};

type AssistantMessageApiRecord = {
  cancelled_at?: string;
  client_request_id?: string;
  completed_at?: string;
  content?: string;
  created_at?: string;
  error_code?: string;
  failed_at?: string;
  id?: string;
  intent?: AssistantIntent;
  model?: string;
  product_id?: string;
  role?: string;
  run_id?: string;
  status?: string;
  references?: AssistantReference[];
  suggestions?: string[];
  tool_results?: AssistantToolResult[];
};

export type AssistantChatPayload = {
  clientRequestId?: string;
  context?: Record<string, unknown>;
  conversationId?: string;
  message: string;
  productId?: string;
  references?: AssistantReference[];
  runId?: string;
  signal?: AbortSignal;
};

export type AssistantActionDraftRecord = {
  action: string;
  cancel_reason?: string;
  client_draft_id?: string;
  confirmed_at?: string;
  confirmed_by?: string;
  created_at?: string;
  created_by?: string;
  expires_at?: string;
  id: string;
  governance?: AssistantActionDraftGovernance;
  metadata_json?: Record<string, unknown>;
  payload: Record<string, unknown>;
  preview?: AssistantActionDraftPreview;
  result_run?: AssistantActionRunRecord;
  result_run_id?: string;
  risk_level?: string;
  source_message_id?: string;
  status: string;
  title: string;
  updated_at?: string;
  wizard_steps?: unknown[];
};

export type AssistantActionDraftWorkbenchSummary = {
  adoption_rate: number;
  draft_total: number;
  resolution_rate: number;
  status_counts: Record<string, number>;
  user_modified_count: number;
  user_modified_rate: number;
  validation_counts: Record<string, number>;
};

export type AssistantActionDraftWorkbenchItem = {
  action: string;
  cancel_reason?: string | null;
  client_draft_id?: string | null;
  confirmed_at?: string | null;
  created_at?: string | null;
  created_by?: string | null;
  expires_at?: string | null;
  id: string;
  audit_event_count?: number;
  failure_count?: number;
  impact_changed_field_count?: number;
  impact_operation?: string | null;
  impact_resource_id?: string | null;
  impact_resource_type?: string | null;
  latest_audit_event_at?: string | null;
  latest_audit_event_type?: string | null;
  modified_field_count: number;
  permission_issue_count?: number;
  permission_status?: string | null;
  retry_count?: number;
  result_id?: string | null;
  result_run_id?: string | null;
  result_status?: string | null;
  result_type?: string | null;
  risk_level?: string | null;
  source_link: string;
  source_message_id?: string | null;
  status: string;
  title: string;
  updated_at?: string | null;
  user_modified: boolean;
  validation_issue_count: number;
  validation_status: string;
  view_count: number;
  wizard_step_count: number;
};

export type AssistantActionDraftWorkbenchQuery = RemoteListQuery & {
  action?: string;
  createdFrom?: string;
  createdTo?: string;
  keyword?: string;
  status?: string;
  validationStatus?: string;
};

export type AssistantActionDraftWorkbenchResult =
  RemoteListResult<AssistantActionDraftWorkbenchItem> & {
    summary: AssistantActionDraftWorkbenchSummary;
  };

export type AssistantActionDraftPreviewDiff = {
  change_type: string;
  current?: unknown;
  field: string;
  label?: string;
  proposed?: unknown;
};

export type AssistantActionDraftPreviewIssue = {
  field: string;
  message: string;
  repair_action?: AssistantRepairAction;
  severity: 'error' | 'warning' | string;
};

export type AssistantRepairAction = {
  action: string;
  field?: string;
  label?: string;
  resource_id?: string;
  resource_type?: string;
};

export type AssistantActionDraftPreview = {
  diffs?: AssistantActionDraftPreviewDiff[];
  target?: {
    operation?: string;
    resource_id?: string | null;
    resource_type?: string;
    source_resource?: {
      resource_id?: string | null;
      resource_type?: string;
      title?: string;
    };
  };
  validation?: {
    issues?: AssistantActionDraftPreviewIssue[];
    status?: 'blocked' | 'passed' | 'warning' | string;
  };
};

export type AssistantActionDraftGovernance = {
  audit?: {
    event_count?: number;
    event_types?: string[];
    latest_actor_id?: string | null;
    latest_event_at?: string | null;
    latest_event_id?: string | null;
    latest_event_type?: string | null;
  };
  diff?: {
    changed_fields?: Array<{
      change_type?: string;
      field?: string;
      label?: string;
    }>;
    count?: number;
  };
  impact?: {
    changed_field_count?: number;
    operation?: string | null;
    payload_field_count?: number;
    resource_id?: string | null;
    resource_type?: string | null;
    source_resource?: {
      resource_id?: string | null;
      resource_type?: string | null;
      title?: string | null;
    } | null;
  };
  permissions?: {
    issue_count?: number;
    issues?: AssistantActionDraftPreviewIssue[];
    missing_permissions?: string[];
    required_permissions?: string[];
    status?: string | null;
  };
  retries?: {
    can_retry?: boolean;
    failure_count?: number;
    last_failure_code?: string | null;
    last_failure_message?: string | null;
    retry_count?: number;
    retry_reason?: string | null;
  };
  risk?: {
    level?: string | null;
    reason?: string | null;
  };
};

export type AssistantActionRunRecord = {
  action: string;
  draft_id: string;
  id: string;
  result?: Record<string, unknown>;
  result_id?: string;
  result_type?: string;
  status: string;
};

export type AssistantActionDraftConfirmResponse = {
  draft: AssistantActionDraftRecord;
  run: AssistantActionRunRecord;
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

export type RequirementFullChainTimelineItem = {
  occurredAt: string;
  occurredAtValue?: string;
  status?: string;
  subjectId: string;
  title: string;
  type: string;
};

export type RequirementFullChainAuditEvent = {
  actorId?: string;
  aiTaskId?: string;
  createdAt: string;
  eventType: string;
  id: string;
  subjectId?: string;
  subjectType?: string;
};

export type RequirementFullChainSummary = {
  aiTasks: number;
  auditEvents: number;
  branchConfigs: number;
  bugs: number;
  codeInspectionReports: number;
  codeReviewReports: number;
  executionTraces: number;
  gitSnapshots: number;
  jenkinsReleases: number;
  knowledgeDeposits: number;
  reviews: number;
  timelineEvents: number;
};

export type RequirementFullChainRecord = {
  aiTasks: TaskCenterTaskRecord[];
  anchor?: {
    resolvedRequirementId?: string;
    subjectId?: string;
    subjectType?: string;
  };
  bugs: BugRecord[];
  auditEvents: RequirementFullChainAuditEvent[];
  branchConfigs: ProductVersionBranchConfigRecord[];
  codeInspectionReports: CodeInspectionReportRecord[];
  codeReviewReports: CodeReviewReportRecord[];
  executionTraces: ExecutionTraceListItem[];
  gitSnapshots: GitLabMergeRequestSnapshot[];
  iterationVersion?: {
    code?: string;
    id: string;
    name?: string;
    status?: string;
  };
  jenkinsReleases: Array<{
    buildId?: string;
    createdAt: string;
    id: string;
    jobName?: string;
    status: string;
  }>;
  knowledgeDeposits: KnowledgeDepositRecord[];
  product?: {
    code?: string;
    id: string;
    name?: string;
  };
  requirement: RequirementRecord;
  reviews: Array<{
    aiTaskId?: string;
    createdAt: string;
    id: string;
    status: string;
  }>;
  status: string;
  summary: RequirementFullChainSummary;
  timeline: RequirementFullChainTimelineItem[];
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

type RemoteSortOrder = 'ascend' | 'descend';

type RemoteListQuery = {
  page?: number;
  pageSize?: number;
  sortField?: string;
  sortOrder?: RemoteSortOrder;
};

export type RequirementListQuery = RemoteListQuery & {
  priority?: string;
  product?: string;
  source?: string;
  status?: string;
  title?: string;
  version?: string;
  versionId?: string;
};

export type ProductListQuery = RemoteListQuery & {
  code?: string;
  name?: string;
  ownerTeam?: string;
  status?: string;
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

export type ProductVersionListQuery = RemoteListQuery & {
  code?: string;
  name?: string;
  product?: string;
  status?: string;
};

export type KnowledgeListQuery = RemoteListQuery & {
  documentType?: string;
  folderId?: string;
  keyword?: string;
  knowledgeSpaceId?: string;
  ownerRole?: string;
  status?: string;
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

export type OperationalMetricListQuery = RemoteListQuery & {
  category?: string;
  name?: string;
  status?: string;
};

export type UserInsightListQuery = RemoteListQuery & {
  category?: string;
  status?: string;
  summary?: string;
};

export type UserListQuery = RemoteListQuery & {
  displayName?: string;
  role?: string;
  status?: string;
  username?: string;
};

export type RoleListQuery = RemoteListQuery & {
  businessRole?: string;
  category?: string;
  menuScope?: string;
  permission?: string;
  role?: string;
  status?: string;
};

export type MenuListQuery = RemoteListQuery & {
  menu?: string;
  menuType?: string;
  parent?: string;
  path?: string;
  permission?: string;
  status?: string;
};

export type AssistantActionReferenceConfigListQuery = RemoteListQuery & {
  enterpriseId?: string;
  keyword?: string;
  permission?: string;
  role?: string;
  status?: string;
  templateVersion?: string;
};

export type AssistantRoleQuickTaskConfigListQuery = RemoteListQuery & {
  enterpriseId?: string;
  groupStatus?: string;
  keyword?: string;
  permission?: string;
  role?: string;
  status?: string;
  targetDraftType?: string;
  templateVersion?: string;
};

export type ModelGatewayConfigListQuery = RemoteListQuery & {
  defaultChatModel?: string;
  defaultEmbeddingModel?: string;
  embeddingConnectionMode?: string;
  isDefault?: string;
  name?: string;
  provider?: string;
  status?: string;
};

export type ModelGatewayLogQuery = RemoteListQuery & {
  aiTaskId?: string;
  purpose?: string;
  status?: string;
};

export type ScheduledJobListQuery = RemoteListQuery & {
  enabled?: boolean;
  jobType?: string;
  keyword?: string;
  name?: string;
  productId?: string;
  sourceSystem?: string;
  status?: string;
};

export type ScheduledJobRunFilterQuery = Partial<RemoteListQuery> & {
  runIds?: string[];
  scheduledJobId?: string;
  status?: string;
};

export type ScheduledJobRunListQuery = ScheduledJobRunFilterQuery & {
  page: number;
};

export type PluginConnectionListQuery = RemoteListQuery & {
  environment?: string;
  keyword?: string;
  pluginId?: string;
  status?: string;
};

export type PluginActionListQuery = RemoteListQuery & {
  keyword?: string;
  pluginId?: string;
  status?: string;
};

export type RdTaskExecutorPolicyListQuery = RemoteListQuery & {
  executorType?: string;
  name?: string;
  productId?: string;
  productName?: string;
  status?: string;
  taskType?: string;
};

export type AiSkillListQuery = RemoteListQuery & {
  code?: string;
  keyword?: string;
  requiresHumanReview?: boolean;
  riskLevel?: string;
  sourceType?: string;
  status?: string;
};

export type AiAgentListQuery = RemoteListQuery & {
  brainAppId?: string;
  keyword?: string;
  modelGatewayConfigId?: string;
  status?: string;
};

export type RemoteListResult<Row> = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: Row[];
  total: number;
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

type TaskBatchSkippedItem = {
  code: string;
  id: string;
  message: string;
};

type TaskBatchRetriedItem = {
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

export type OperationalMetricRecord = {
  category: string;
  id: string;
  name: string;
  status: string;
  updatedAt: string;
  value: string;
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

export type UserInsightRecord = {
  category: string;
  confidenceLevel?: string;
  convertedRequirementId?: string;
  featureCode?: string;
  feedbackType?: string;
  id: string;
  moduleCode?: string;
  owner: string;
  planningCycle?: string;
  priority?: string;
  productId?: string;
  status: string;
  summary: string;
  updatedAt: string;
  updatedAtSortValue?: string;
  versionId?: string;
};

export type UserFeedbackCreatePayload = {
  content: string;
  feedback_type: string;
  feature_code?: string;
  module_code?: string;
  product_id: string;
  satisfaction_score?: number;
  sentiment?: string;
  source_channel: string;
  tags?: string[];
};

export type UserFeedbackPatchPayload = {
  content?: string;
  satisfaction_score?: number;
  sentiment?: string;
  status?: string;
  tags?: string[];
  triage_note?: string;
};

export type UserFeedbackConvertRequirementPayload = {
  content?: string;
  module_code?: string;
  priority?: string;
  product_id?: string;
  title: string;
  triage_note?: string;
  version_id?: string;
};

export type UserUsageMetricCreatePayload = {
  active_users?: number;
  avg_duration_seconds?: number;
  bounce_rate?: number;
  conversion_count?: number;
  conversion_rate?: number;
  error_count?: number;
  event_count?: number;
  feature_code: string;
  module_code?: string;
  product_id: string;
  source_channel?: string;
  user_segment?: string;
  window_end: string;
  window_start: string;
};

export type GitLabDailyCodeMetricCreatePayload = {
  active_author_count?: number;
  additions?: number;
  author_metrics?: Array<Record<string, unknown>>;
  changed_files?: number;
  commit_count?: number;
  deletions?: number;
  merge_request_count?: number;
  metric_date: string;
  product_id: string;
  quality_score?: number;
  repository_id: string;
  risk_count?: number;
  source_channel?: string;
  status?: string;
};

export type JenkinsReleaseCreatePayload = {
  build_id: string;
  build_number?: number;
  commit_sha?: string;
  deployed_at?: string;
  duration_seconds?: number;
  environment?: string;
  failure_reason?: string;
  job_name: string;
  product_id: string;
  source_channel?: string;
  started_at?: string;
  status?: string;
  trigger_actor?: string;
  version_id: string;
};

export type OnlineLogMetricCreatePayload = {
  anomaly_summary?: string;
  core_event_count?: number;
  environment?: string;
  error_count?: number;
  module_code?: string;
  p95_latency_ms?: number;
  p99_latency_ms?: number;
  product_id: string;
  request_count?: number;
  source_channel?: string;
  status?: string;
  top_errors?: Record<string, unknown>[];
  window_end: string;
  window_start: string;
};

export type CollectorRunRecord = {
  collectorType: string;
  createdBy?: string;
  errorMessage?: string;
  finishedAt?: string;
  id: string;
  payloadSummary: Record<string, unknown>;
  productId?: string;
  recordsImported: number;
  sourceSystem: string;
  startedAt: string;
  status: string;
  updatedAt: string;
};

export type CollectorRunCreatePayload = {
  collector_type: string;
  error_message?: string;
  payload_summary?: Record<string, unknown>;
  product_id?: string;
  records_imported?: number;
  source_system: string;
  started_at?: string;
  status?: string;
};

export type CollectorRunPatchPayload = {
  error_message?: string;
  finished_at?: string;
  payload_summary?: Record<string, unknown>;
  records_imported?: number;
  status?: string;
};

export type PendingAttributionItem = {
  collectorRunId?: string;
  confidence?: number;
  createdAt: string;
  createdBy?: string;
  id: string;
  rawPayload: Record<string, unknown>;
  rawSubjectId?: string;
  resolutionAction?: string;
  resolutionNote?: string;
  resolvedAt?: string;
  resolvedBy?: string;
  resolvedModuleCode?: string;
  resolvedProductId?: string;
  resolvedRequirementId?: string;
  resolvedSubjectId?: string;
  resolvedSubjectType?: string;
  sourceSystem: string;
  sourceType: string;
  status: string;
  suggestedModuleCode?: string;
  suggestedProductId?: string;
  summary: string;
  updatedAt: string;
};

export type PendingAttributionCreatePayload = {
  collector_run_id?: string;
  confidence?: number;
  raw_payload?: Record<string, unknown>;
  raw_subject_id?: string;
  source_system: string;
  source_type: string;
  suggested_module_code?: string;
  suggested_product_id?: string;
  summary: string;
};

export type PendingAttributionResolvePayload = {
  resolution_action: string;
  resolution_note?: string;
  resolved_module_code?: string;
  resolved_product_id?: string;
  resolved_requirement_id?: string;
  resolved_subject_id?: string;
  resolved_subject_type?: string;
};

export type PendingAttributionFilters = {
  collector_run_id?: string;
  resolved_product_id?: string;
  source_type?: string;
  status?: string;
};

export type IterationSuggestionCreatePayload = {
  constraints?: Record<string, unknown>;
  module_codes?: string[];
  planning_cycle: string;
  product_id: string;
  version_id?: string | null;
};

export type IterationSuggestionDecisionPayload = {
  comment?: string;
  convert_to_requirement: boolean;
  decision: string;
  edited_scope?: string;
  edited_title?: string;
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
  diffFileTree: CodeReviewDiffTreeItem[];
  mrIid: number;
  permissionDiagnostics?: CodeReviewPermissionDiagnostics;
  reviewChecklist: string[];
  repositoryId: string;
  riskSummary?: CodeReviewRiskSummary;
  sourceBranch?: string;
  targetBranch?: string;
  title: string;
  webUrl?: string;
  writebackAllowed: boolean;
};

export type CodeReviewPermissionDiagnostics = {
  baseUrlConfigured?: boolean;
  credentialRefConfigured?: boolean;
  provider?: string;
  repositoryPathConfigured?: boolean;
  tokenAvailable?: boolean;
  writebackAllowed?: boolean;
  writebackReason?: string;
};

export type CodeReviewDiffTreeItem = {
  additions: number;
  deletions: number;
  fileCount: number;
  path: string;
};

export type CodeReviewRiskSummary = {
  fileCount?: number;
  largestFile?: {
    additions?: number;
    deletions?: number;
    lineCount?: number;
    path?: string;
  } | null;
  riskLevel?: string;
  totalAdditions?: number;
  totalChangedLines?: number;
  totalDeletions?: number;
};

export type GitLabMergeRequestSnapshot = {
  changedFilesSummary: unknown[];
  createdAt?: string;
  diffChangeSummary?: CodeReviewDiffChangeSummary;
  diffLimitBytes?: number;
  diffFileTree: CodeReviewDiffTreeItem[];
  diffSizeBytes?: number;
  id: string;
  mrIid: number;
  previousSnapshot?: CodeReviewPreviousSnapshot | null;
  reviewChecklist: string[];
  repositoryId: string;
  riskSummary?: CodeReviewRiskSummary;
  snapshotReused?: boolean;
};

export type CodeReviewDiffChangeSummary = {
  addedFiles?: string[];
  addedFilesCount?: number;
  modifiedFiles?: string[];
  modifiedFilesCount?: number;
  removedFiles?: string[];
  removedFilesCount?: number;
};

export type CodeReviewPreviousSnapshot = {
  createdAt?: string;
  headSha?: string;
  id?: string;
  snapshotHash?: string;
};

export type CodeReviewReportRecord = {
  executor?: unknown;
  findings: unknown[];
  gitlabWritebackPerformed: boolean;
  id: string;
  riskLevel: string;
  status: string;
  summary: string;
  writebackTemplate?: {
    body: string;
    format: string;
    title: string;
    writebackAllowed: boolean;
    writebackReason: string;
  };
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

export type KnowledgeDepositRecord = {
  aiTaskId: string;
  content: string;
  id: string;
  knowledgeDocumentId?: string | null;
  rejectionReason?: string;
  status: string;
  title: string;
};

export type KnowledgeDepositApprovePayload = {
  permissionRoles?: string[];
  title?: string;
};

export type KnowledgeSearchResultRecord = {
  chunkId?: string;
  chunkIndex?: number;
  content: string;
  documentId: string;
  id: string;
  parentChunkId?: string;
  parentContent?: string;
  retrievalMode?: 'keyword' | 'vector';
  sourceLabel: string;
  title: string;
};

export type KnowledgeSpaceRecord = {
  code: string;
  description?: string;
  id: string;
  name: string;
};

export type KnowledgeFolderRecord = {
  id: string;
  knowledgeSpaceId: string;
  name: string;
  parentFolderId?: string | null;
  path: string;
};

export type KnowledgeAssetRecord = {
  assetType: string;
  filename: string;
  id: string;
  mimeType?: string;
  sizeBytes: number;
  storageProvider?: string;
};

export type KnowledgeImportJobRecord = {
  assetFilename?: string;
  chunkStrategy?: string;
  documentId: string;
  documentTitle?: string;
  errorMessage?: string;
  folderPath?: string;
  id: string;
  parserEngine?: string;
  progress: number;
  status: string;
  updatedAt?: string;
};

export type KnowledgeImportWorkerStatusRecord = {
  activeJobId?: string | null;
  enabled: boolean;
  failedCount: number;
  pendingCount: number;
  processedCount: number;
  queuedJobIds: string[];
  running: boolean;
  workerId?: string | null;
};

export type KnowledgeChunkSetRecord = {
  activatedAt?: string;
  chunkCount: number;
  chunkStrategy: string;
  id: string;
  isActive: boolean;
  parserEngine: string;
  status: string;
};

export type KnowledgeChunkRecord = {
  chunkIndex: number;
  chunkRole?: string;
  chunkSetId?: string;
  content: string;
  heading?: string;
  id: string;
  imageCount?: number;
  imageRefs?: string[];
  parentChunkId?: string;
  parentContent?: string;
  pageNumber?: number;
  sectionTitle?: string;
  sourceAssetType?: string;
  sourceKind?: string;
  splitPattern?: string;
  tableColumns?: string[];
  tableCount?: number;
  tableIndex?: number;
};

export type KnowledgeDocumentUploadPayload = {
  chunk_strategy?: string;
  content_base64: string;
  doc_type?: string;
  filename: string;
  folder_id?: string;
  knowledge_space_id: string;
  mime_type?: string;
  parser_engine?: string;
  tags?: string[];
  title: string;
};

export type ProductFilterOption = {
  code: string;
  id: string;
  name: string;
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
  description?: string | null;
  id: string;
  name: string;
  product_code?: string;
  product_id: string;
  product_name?: string;
  release_date?: string | null;
  start_date?: string | null;
  status?: string;
};

type ProductModuleListItem = {
  code?: string;
  description?: string | null;
  id: string;
  name: string;
  owner_team?: string | null;
  product_id: string;
  status?: string;
};

type ProductRelatedSystemListItem = {
  code?: string;
  description?: string | null;
  id: string;
  name: string;
  owner_team?: string | null;
  product_id?: string | null;
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

type RequirementBatchSkippedItem = {
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

type RequirementBatchGeneratedTaskItem = {
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

export type ProductVersionMutationPayload = {
  code?: string;
  description?: string;
  name: string;
  release_date?: string;
  start_date?: string;
  status?: string;
};

export type ProductVersionAdvanceStatusPayload = {
  force?: boolean;
  preview_only?: boolean;
  reason?: string;
  target_status: string;
};

type ProductVersionAdvanceRequirementImpact = {
  block_reason?: string;
  from_status?: string;
  id: string;
  status?: string;
  title: string;
  to_status?: string;
};

type ProductVersionAdvanceStatusResponse = {
  blocked_requirements: ProductVersionAdvanceRequirementImpact[];
  force: boolean;
  from_status: string;
  preview_only: boolean;
  target_status: string;
  unchanged_requirements: ProductVersionAdvanceRequirementImpact[];
  updated_requirements: ProductVersionAdvanceRequirementImpact[];
  version: ProductVersionListItem;
};

type ProductVersionDashboardBlockerItem = {
  id?: string;
  reason?: string;
  severity?: string;
  source_type?: string;
  title?: string;
};

type ProductVersionDashboardAccessIssue = {
  code?: string;
  message?: string;
  section?: string;
};

type ProductVersionDashboardSummary = {
  blockers: number;
  branch_configs: number;
  bugs: number;
  code_inspection_reports: number;
  open_bugs: number;
  releases: number;
  requirements: number;
  severe_bugs: number;
  severe_code_inspection_reports: number;
  tasks: number;
};

type ProductVersionDashboardStatusCount = {
  count: number;
  status: string;
};

type ProductVersionDashboardStatusImpactResponse = {
  blocked_requirements?: ProductVersionAdvanceRequirementImpact[];
  target_status: string;
  unchanged_requirements?: ProductVersionAdvanceRequirementImpact[];
  updated_requirements?: ProductVersionAdvanceRequirementImpact[];
};

type ProductVersionDashboardResponse = {
  access_issues?: ProductVersionDashboardAccessIssue[];
  blockers?: ProductVersionDashboardBlockerItem[];
  branch_configs?: ProductVersionBranchConfigListItem[];
  bug_status_counts?: ProductVersionDashboardStatusCount[];
  bugs?: BugListItem[];
  code_inspection_reports?: CodeInspectionReportRecord[];
  releases?: FlexibleListItem[];
  requirement_status_counts?: ProductVersionDashboardStatusCount[];
  requirements?: RequirementListItem[];
  status_impact?: ProductVersionDashboardStatusImpactResponse | null;
  summary?: Partial<ProductVersionDashboardSummary>;
  task_status_counts?: ProductVersionDashboardStatusCount[];
  tasks?: TaskListItem[];
  version: ProductVersionListItem;
};

export type ProductVersionAdvanceStatusResult = {
  blockedRequirements: ProductVersionAdvanceRequirementImpact[];
  force: boolean;
  fromStatus: ProductVersionRecord['status'];
  previewOnly: boolean;
  targetStatus: ProductVersionRecord['status'];
  unchangedRequirements: ProductVersionAdvanceRequirementImpact[];
  updatedRequirements: ProductVersionAdvanceRequirementImpact[];
  version: ProductVersionRecord;
};

export type ProductVersionDashboard = {
  accessIssues: Array<{
    code: string;
    message: string;
    section: string;
  }>;
  blockers: Array<{
    id?: string;
    reason: string;
    severity: string;
    sourceType: string;
    title: string;
  }>;
  branchConfigs: ProductVersionBranchConfigRecord[];
  bugStatusCounts: ProductVersionDashboardStatusCount[];
  bugs: BugRecord[];
  codeInspectionReports: CodeInspectionReportRecord[];
  releases: Array<{
    buildId?: string;
    createdAt: string;
    id: string;
    jobName?: string;
    status: string;
  }>;
  requirementStatusCounts: ProductVersionDashboardStatusCount[];
  requirements: RequirementRecord[];
  statusImpact?: {
    blockedRequirements: ProductVersionAdvanceRequirementImpact[];
    targetStatus: ProductVersionRecord['status'];
    unchangedRequirements: ProductVersionAdvanceRequirementImpact[];
    updatedRequirements: ProductVersionAdvanceRequirementImpact[];
  };
  summary: ProductVersionDashboardSummary;
  taskStatusCounts: ProductVersionDashboardStatusCount[];
  tasks: TaskCenterTaskRecord[];
  version: ProductVersionRecord;
};

export type ProductModuleMutationPayload = {
  code?: string;
  description?: string;
  display_order?: number;
  name: string;
  owner_team?: string;
  status?: string;
};

export type ProductGitRepositoryMutationPayload = {
  credential_ref?: string;
  default_branch?: string;
  git_provider?: string;
  name: string;
  project_id?: string;
  project_path?: string;
  remote_url?: string;
  repo_type?: string;
  root_path?: string;
  status?: string;
};

export type ProductVersionBranchConfigMutationPayload = {
  base_branch?: string;
  branch_status?: string;
  creation_source?: string;
  description?: string;
  repository_id: string;
  working_branch: string;
};

export type ProductRelatedSystemMutationPayload = {
  code?: string;
  description?: string;
  display_order?: number;
  name: string;
  owner_team?: string;
  product_id?: string;
  status?: string;
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

export type KnowledgeDocumentMutationPayload = {
  content?: string;
  doc_type?: string;
  folder_id?: string | null;
  index_error?: string | null;
  index_status?: string;
  knowledge_space_id?: string | null;
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

export type ModelGatewayConfigMutationPayload = {
  api_key?: string;
  base_url?: string;
  config_id?: string;
  default_chat_model?: string;
  default_embedding_model?: string | null;
  embedding_api_key?: string;
  embedding_base_url?: string | null;
  embedding_connection_mode?: 'custom' | 'disabled' | 'reuse_chat';
  embedding_dimension?: number | null;
  is_default?: boolean;
  max_retries?: number;
  name?: string;
  provider?: string;
  status?: string;
  test_target?: 'chat' | 'chat_and_embedding' | 'embedding';
  timeout_seconds?: number;
};

export type ModelGatewayConfigTestResult = {
  chat: {
    error_code?: string;
    latency_ms?: number;
    model: string;
    ok: boolean;
    status: string;
  };
  embedding: {
    dimension?: number;
    error_code?: string;
    latency_ms?: number;
    model: string;
    ok: boolean;
    status: string;
  };
  ok: boolean;
  test_target?: string;
};

type RequirementListItem = {
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

type KnowledgeDocumentListItem = {
  active_chunk_set_id?: string | null;
  content?: string;
  created_at?: string;
  doc_type?: string;
  folder_id?: string | null;
  folder_path?: string | null;
  id: string;
  index_error?: string | null;
  index_status?: string;
  knowledge_space_id?: string | null;
  permission_roles?: string[];
  source_asset_id?: string | null;
  tags?: string[];
  title: string;
  updated_at?: string;
  vector_index_error?: string | null;
};

type KnowledgeSpaceListItem = {
  code: string;
  description?: string;
  id: string;
  name: string;
};

type KnowledgeFolderListItem = {
  id: string;
  knowledge_space_id: string;
  name: string;
  parent_folder_id?: string | null;
  path?: string;
};

type KnowledgeAssetListItem = {
  asset_type?: string;
  filename?: string;
  id: string;
  mime_type?: string;
  size_bytes?: number;
  storage_provider?: string;
};

type KnowledgeImportJobListItem = {
  asset_filename?: string;
  chunk_strategy?: string;
  document_id: string;
  document_title?: string;
  error_message?: string | null;
  folder_path?: string;
  id: string;
  parser_engine?: string;
  progress?: number;
  status?: string;
  updated_at?: string;
};

type KnowledgeImportWorkerStatusItem = {
  active_job_id?: string | null;
  enabled?: boolean;
  failed_count?: number;
  pending_count?: number;
  processed_count?: number;
  queued_job_ids?: string[];
  running?: boolean;
  worker_id?: string | null;
};

type KnowledgeChunkSetListItem = {
  activated_at?: string;
  chunk_count?: number;
  chunk_strategy?: string;
  id: string;
  is_active?: boolean;
  parser_engine?: string;
  status?: string;
};

type KnowledgeChunkListItem = {
  chunk_index?: number;
  chunk_set_id?: string;
  content?: string;
  id: string;
  metadata?: {
    columns?: string[];
    chunk_role?: string;
    heading?: string;
    image_count?: number;
    image_refs?: string[];
    page_number?: number;
    section_title?: string;
    source_asset_type?: string;
    source_kind?: string;
    split_pattern?: string;
    table_count?: number;
    table_index?: number;
  };
  parent_chunk_id?: string;
  parent_content?: string;
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

type RequirementFullChainTimelineItemResponse = {
  occurred_at?: string;
  status?: string | null;
  subject_id?: string;
  title?: string;
  type?: string;
};

type RequirementFullChainResponse = {
  ai_tasks?: TaskListItem[];
  audit_events?: FlexibleListItem[];
  anchor?: {
    resolved_requirement_id?: string;
    subject_id?: string;
    subject_type?: string;
  };
  bugs?: BugListItem[];
  branch_configs?: ProductVersionBranchConfigListItem[];
  code_inspection_reports?: CodeInspectionReportRecord[];
  code_review_reports?: CodeReviewReportResponse[];
  execution_traces?: ExecutionTraceListItem[];
  git_snapshots?: GitLabMergeRequestSnapshotResponse[];
  iteration_version?: ProductVersionListItem | null;
  jenkins_releases?: FlexibleListItem[];
  knowledge_deposits?: KnowledgeDepositListItem[];
  product?: ProductResponse | null;
  requirement: RequirementListItem;
  reviews?: PendingReviewListItem[];
  status?: string;
  summary?: Partial<{
    ai_tasks: number;
    audit_events: number;
    branch_configs: number;
    bugs: number;
    code_inspection_reports: number;
    code_review_reports: number;
    execution_traces: number;
    git_snapshots: number;
    jenkins_releases: number;
    knowledge_deposits: number;
    reviews: number;
    timeline_events: number;
  }>;
  timeline?: RequirementFullChainTimelineItemResponse[];
};

type BugListItem = {
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

type TaskListItem = {
  created_at?: string;
  created_by?: string;
  current_step?: string | null;
  id: string;
  product_id?: string;
  product_name?: string | null;
  requirement_id?: string;
  status?: string;
  task_type?: string;
  title?: string;
  updated_at?: string;
};

type TaskDetailItem = TaskListItem & {
  current_step?: string | null;
  graph_runs?: unknown;
  input?: unknown;
  input_json?: unknown;
  module_code?: string | null;
  output?: unknown;
  output_json?: unknown;
  pending_review?: unknown;
  product_context?: unknown;
  requirement_snapshot?: unknown;
  version_id?: string | null;
};

type ProductGitRepositoryListItem = {
  credential_ref_configured?: boolean;
  default_branch?: string;
  git_provider?: string;
  id: string;
  name: string;
  project_id?: string | null;
  project_path?: string | null;
  remote_url?: string | null;
  repo_type?: string;
  root_path?: string;
  status?: string;
};

type ProductVersionBranchConfigListItem = {
  base_branch?: string;
  branch_status?: string;
  creation_source?: string;
  description?: string | null;
  id: string;
  product_id: string;
  repository_default_branch?: string | null;
  repository_id: string;
  repository_name?: string | null;
  repository_path?: string | null;
  repository_provider?: string | null;
  version_id: string;
  working_branch?: string;
};

type ModelGatewayConfigListItem = {
  api_key_configured?: boolean;
  base_url?: string;
  default_chat_model?: string;
  default_embedding_model?: string | null;
  embedding_api_key_configured?: boolean;
  embedding_base_url?: string | null;
  embedding_connection_mode?: string;
  embedding_dimension?: number | null;
  id: string;
  is_default?: boolean;
  max_retries?: number;
  name: string;
  provider?: string;
  status?: string;
  timeout_seconds?: number;
};

type ModelGatewayLogListItem = {
  ai_task_id?: string | null;
  created_at?: string;
  error?: string | null;
  id: string;
  latency_ms?: number | null;
  model?: string;
  model_gateway_config_id?: string | null;
  provider?: string;
  purpose?: string;
  status?: string;
  tokens?: Record<string, unknown>;
  updated_at?: string;
};

type GitLabMergeRequestPreviewResponse = {
  author?: unknown;
  changed_file_count?: number;
  changed_files_summary?: unknown[];
  diff_file_tree?: Array<{
    additions?: number;
    deletions?: number;
    file_count?: number;
    path?: string;
  }>;
  mr_iid: number;
  permission_diagnostics?: {
    base_url_configured?: boolean;
    credential_ref_configured?: boolean;
    provider?: string;
    repository_path_configured?: boolean;
    token_available?: boolean;
    writeback_allowed?: boolean;
    writeback_reason?: string;
  };
  review_checklist?: string[];
  repository_id: string;
  risk_summary?: {
    file_count?: number;
    largest_file?: {
      additions?: number;
      deletions?: number;
      line_count?: number;
      path?: string;
    } | null;
    risk_level?: string;
    total_additions?: number;
    total_changed_lines?: number;
    total_deletions?: number;
  };
  source_branch?: string;
  target_branch?: string;
  title?: string;
  web_url?: string;
  writeback_allowed?: boolean;
};

type GitLabMergeRequestSnapshotResponse = {
  changed_files_summary?: unknown[];
  created_at?: string;
  diff_change_summary?: {
    added_files?: string[];
    added_files_count?: number;
    modified_files?: string[];
    modified_files_count?: number;
    removed_files?: string[];
    removed_files_count?: number;
  };
  diff_file_tree?: GitLabMergeRequestPreviewResponse['diff_file_tree'];
  diff_limit_bytes?: number;
  diff_size_bytes?: number;
  id: string;
  mr_iid: number;
  previous_snapshot?: {
    created_at?: string;
    head_sha?: string;
    id?: string;
    snapshot_hash?: string;
  } | null;
  review_checklist?: string[];
  repository_id: string;
  risk_summary?: GitLabMergeRequestPreviewResponse['risk_summary'];
  snapshot_reused?: boolean;
};

type CodeReviewReportResponse = {
  archived_at?: string;
  created_at?: string;
  executor?: unknown;
  findings?: unknown[];
  gitlab_writeback_performed?: boolean;
  id: string;
  risk_level?: string;
  status?: string;
  summary?: string;
  writeback_template?: {
    body?: string;
    format?: string;
    title?: string;
    writeback_allowed?: boolean;
    writeback_reason?: string;
  };
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

type KnowledgeDepositListItem = {
  ai_task_id: string;
  content?: string;
  id: string;
  knowledge_document_id?: string | null;
  rejection_reason?: string;
  status?: string;
  title?: string;
};

type KnowledgeSearchResultItem = {
  chunk_id?: string;
  chunk_index?: number;
  content?: string;
  document_id: string;
  retrieval_mode?: string;
  source?: {
    asset_id?: string;
    chunk_id?: string;
    chunk_set_id?: string;
    doc_type?: string;
    folder_id?: string;
    knowledge_space_id?: string;
    parent_chunk_id?: string;
    parent_content?: string;
    title?: string;
  };
  title?: string;
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

type RoleDefinitionListItem = {
  business_roles?: string[];
  category?: string;
  code: string;
  data_scope?: string;
  decision_scope?: string;
  description?: string;
  is_assignable?: boolean;
  is_system?: boolean;
  limitations?: string[];
  menu_codes?: string[];
  menu_scope?: string[];
  name: string;
  permission_codes?: string[];
  permissions?: string[];
  responsibilities?: string[];
  scopes?: ScopeGrant[];
  id?: string;
  sort_order?: number;
  status?: string;
};

export async function chatWithAssistant(
  payload: AssistantChatPayload,
): Promise<AssistantChatResponse> {
  const token = requireAccessToken();
  const response = await apiRequest<AssistantChatApiResponse>('/api/assistant/chat', {
    body: {
      client_request_id: payload.clientRequestId,
      context: payload.context,
      conversation_id: payload.conversationId,
      message: payload.message,
      product_id: payload.productId,
      references: payload.references?.map((reference) => ({
        id: reference.id,
        type: reference.type,
      })) ?? [],
      run_id: payload.runId,
    },
    method: 'POST',
    signal: payload.signal,
    token,
  });
  return {
    content: response.message.content ?? '',
    conversationId: response.conversation_id,
    intent: response.message.intent,
    latencyMs: Number(response.latency_ms ?? 0),
    messageId: response.message.id ?? response.conversation_id,
    model: response.model ?? '',
    references: response.message.references ?? response.references ?? [],
    run: response.run,
    runId: response.run_id ?? response.message.run_id ?? response.run?.id,
    status: response.message.status,
    suggestions: response.suggestions ?? [],
    toolResults: response.message.tool_results ?? response.tool_results ?? [],
  };
}

export async function cancelAssistantChatRun(
  runId: string,
  reason = 'user_cancelled',
): Promise<AssistantChatRun> {
  const token = requireAccessToken();
  return apiRequest<AssistantChatRun>(`/api/assistant/chat-runs/${runId}/cancel`, {
    body: { reason },
    method: 'POST',
    token,
  });
}

export async function fetchAssistantChatRuns(params: {
  limit?: number;
  status?: string;
} = {}): Promise<AssistantChatRun[]> {
  const token = requireAccessToken();
  const searchParams = new URLSearchParams();
  if (params.status) {
    searchParams.set('status', params.status);
  }
  if (params.limit) {
    searchParams.set('limit', String(params.limit));
  }
  const query = searchParams.toString();
  const response = await apiRequest<ListResponse<AssistantChatRun>>(
    `/api/assistant/chat-runs${query ? `?${query}` : ''}`,
    {
      method: 'GET',
      token,
    },
  );
  return response.items;
}

export async function fetchAssistantRuntimeStatus(): Promise<AssistantRuntimeStatus> {
  const token = requireAccessToken();
  return apiRequest<AssistantRuntimeStatus>('/api/assistant/runtime-status', {
    method: 'GET',
    token,
  });
}

export async function fetchAssistantReferenceCandidates(params: {
  limit?: number;
  query: string;
  signal?: AbortSignal;
  type?: string;
}): Promise<AssistantReference[]> {
  const token = requireAccessToken();
  const searchParams = new URLSearchParams();
  searchParams.set('query', params.query);
  if (params.type) {
    searchParams.set('type', params.type);
  }
  if (params.limit) {
    searchParams.set('limit', String(params.limit));
  }
  const response = await apiRequest<ListResponse<AssistantReference>>(
    `/api/assistant/reference-candidates?${searchParams.toString()}`,
    {
      method: 'GET',
      signal: params.signal,
      token,
    },
  );
  return response.items;
}

export async function fetchAssistantDraftTemplates(): Promise<AssistantDraftTemplate[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<AssistantDraftTemplate>>(
    '/api/assistant/draft-templates',
    {
      method: 'GET',
      token,
    },
  );
  return response.items;
}

function appendAssistantMetricsQueryParams(
  searchParams: URLSearchParams,
  params: AssistantMetricsQueryParams = {},
) {
  if (params.action) {
    searchParams.set('action', params.action);
  }
  if (params.dateFrom) {
    searchParams.set('date_from', params.dateFrom);
  }
  if (params.dateTo) {
    searchParams.set('date_to', params.dateTo);
  }
  if (params.productId) {
    searchParams.set('product_id', params.productId);
  }
  if (params.role) {
    searchParams.set('role', params.role);
  }
  if (params.windowDays) {
    searchParams.set('window_days', String(params.windowDays));
  }
}

export async function fetchAssistantMetrics(
  params: AssistantMetricsQueryParams = {},
): Promise<AssistantMetrics> {
  const token = requireAccessToken();
  const searchParams = new URLSearchParams();
  appendAssistantMetricsQueryParams(searchParams, params);
  const query = searchParams.toString();
  return apiRequest<AssistantMetrics>(`/api/assistant/metrics${query ? `?${query}` : ''}`, {
    method: 'GET',
    token,
  });
}

export async function fetchAssistantMetricDetails(params: {
  action?: string;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
  metric: string;
  productId?: string;
  role?: string;
  windowDays?: number;
}): Promise<AssistantMetricDetails> {
  const token = requireAccessToken();
  const searchParams = new URLSearchParams();
  searchParams.set('metric', params.metric);
  appendAssistantMetricsQueryParams(searchParams, params);
  if (params.limit) {
    searchParams.set('limit', String(params.limit));
  }
  return apiRequest<AssistantMetricDetails>(
    `/api/assistant/metrics/details?${searchParams.toString()}`,
    {
      method: 'GET',
      token,
    },
  );
}

export async function exportAssistantMetrics(params: AssistantMetricsQueryParams & {
  format?: 'csv' | 'json';
} = {}): Promise<AssistantMetricsExport> {
  const token = requireAccessToken();
  const searchParams = new URLSearchParams();
  appendAssistantMetricsQueryParams(searchParams, params);
  searchParams.set('format', params.format ?? 'csv');
  const response = await apiRequest<{
    content: AssistantMetrics | string;
    content_type: string;
    filename: string;
    format: string;
  }>(`/api/assistant/metrics/export?${searchParams.toString()}`, {
    method: 'GET',
    token,
  });
  return {
    content: response.content,
    contentType: response.content_type,
    filename: response.filename,
    format: response.format,
  };
}

export async function fetchAssistantActionReferenceConfigs(): Promise<AssistantActionReferenceConfig[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<AssistantActionReferenceConfig>>(
    '/api/assistant/action-reference-configs',
    {
      method: 'GET',
      token,
    },
  );
  return response.items;
}

export async function fetchAssistantActionReferenceConfigList(
  query: AssistantActionReferenceConfigListQuery = {},
): Promise<RemoteListResult<AssistantActionReferenceConfig>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'role', query.role);
  appendQueryParam(params, 'permission', query.permission);
  appendQueryParam(params, 'enterprise_id', query.enterpriseId);
  appendQueryParam(params, 'template_version', query.templateVersion);
  appendRemoteListParams(params, query);
  const response = await apiRequest<ListResponse<AssistantActionReferenceConfig>>(
    `/api/assistant/action-reference-configs?${params.toString()}`,
    {
      method: 'GET',
      token,
    },
  );
  return {
    page: response.page ?? query.page ?? 1,
    pageSize: response.page_size ?? query.pageSize ?? 10,
    performance: response.performance,
    rows: response.items,
    total: response.total,
  };
}

export async function createAssistantActionReferenceConfig(
  payload: Omit<AssistantActionReferenceConfig, 'created_at' | 'created_by' | 'id' | 'updated_at' | 'updated_by'> & {
    id?: string;
  },
): Promise<AssistantActionReferenceConfig> {
  const token = requireAccessToken();
  return apiRequest<AssistantActionReferenceConfig>('/api/assistant/action-reference-configs', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function patchAssistantActionReferenceConfig(
  configId: string,
  payload: Partial<Omit<AssistantActionReferenceConfig, 'created_at' | 'created_by' | 'id' | 'updated_at' | 'updated_by'>>,
): Promise<AssistantActionReferenceConfig> {
  const token = requireAccessToken();
  return apiRequest<AssistantActionReferenceConfig>(
    `/api/assistant/action-reference-configs/${configId}`,
    {
      body: payload,
      method: 'PATCH',
      token,
    },
  );
}

export async function setAssistantActionReferenceConfigStatus(
  configId: string,
  enabled: boolean,
): Promise<AssistantActionReferenceConfig> {
  const token = requireAccessToken();
  return apiRequest<AssistantActionReferenceConfig>(
    `/api/assistant/action-reference-configs/${configId}/status`,
    {
      body: { enabled },
      method: 'POST',
      token,
    },
  );
}

export async function updateAssistantActionReferenceConfigRollout(
  configId: string,
  payload: Pick<AssistantActionReferenceConfig, 'enterprise_id' | 'rollout_json' | 'template_version'>,
): Promise<AssistantActionReferenceConfig> {
  const token = requireAccessToken();
  return apiRequest<AssistantActionReferenceConfig>(
    `/api/assistant/action-reference-configs/${configId}/rollout`,
    {
      body: payload,
      method: 'PUT',
      token,
    },
  );
}

export async function deleteAssistantActionReferenceConfig(
  configId: string,
): Promise<AssistantActionReferenceConfig> {
  const token = requireAccessToken();
  return apiRequest<AssistantActionReferenceConfig>(
    `/api/assistant/action-reference-configs/${configId}`,
    {
      method: 'DELETE',
      token,
    },
  );
}

export async function fetchAssistantRoleQuickTasks(): Promise<AssistantRoleQuickTaskGroup[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<AssistantRoleQuickTaskGroup>>(
    '/api/assistant/role-quick-tasks',
    {
      method: 'GET',
      token,
    },
  );
  return response.items;
}

export async function fetchAssistantRoleQuickTaskConfigs(): Promise<AssistantRoleQuickTaskConfig[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<AssistantRoleQuickTaskConfig>>(
    '/api/assistant/role-quick-task-configs',
    {
      method: 'GET',
      token,
    },
  );
  return response.items;
}

export async function fetchAssistantRoleQuickTaskConfigList(
  query: AssistantRoleQuickTaskConfigListQuery = {},
): Promise<RemoteListResult<AssistantRoleQuickTaskConfig>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'group_status', query.groupStatus);
  appendQueryParam(params, 'role', query.role);
  appendQueryParam(params, 'permission', query.permission);
  appendQueryParam(params, 'enterprise_id', query.enterpriseId);
  appendQueryParam(params, 'target_draft_type', query.targetDraftType);
  appendQueryParam(params, 'template_version', query.templateVersion);
  appendRemoteListParams(params, query);
  const response = await apiRequest<ListResponse<AssistantRoleQuickTaskConfig>>(
    `/api/assistant/role-quick-task-configs?${params.toString()}`,
    {
      method: 'GET',
      token,
    },
  );
  return {
    page: response.page ?? query.page ?? 1,
    pageSize: response.page_size ?? query.pageSize ?? 10,
    performance: response.performance,
    rows: response.items,
    total: response.total,
  };
}

export async function setAssistantRoleQuickTaskConfigStatus(
  configId: string,
  payload: {
    enabled: boolean;
    group_enabled?: boolean;
  },
): Promise<AssistantRoleQuickTaskConfig> {
  const token = requireAccessToken();
  return apiRequest<AssistantRoleQuickTaskConfig>(
    `/api/assistant/role-quick-task-configs/${configId}/status`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
}

export async function updateAssistantRoleQuickTaskConfigRollout(
  configId: string,
  payload: {
    enterprise_id?: string | null;
    rollout_json: Record<string, unknown>;
    template_version?: string | null;
  },
): Promise<AssistantRoleQuickTaskConfig> {
  const token = requireAccessToken();
  return apiRequest<AssistantRoleQuickTaskConfig>(
    `/api/assistant/role-quick-task-configs/${configId}/rollout`,
    {
      body: payload,
      method: 'PUT',
      token,
    },
  );
}

export async function getAssistantActionDraft(
  draftId: string,
): Promise<AssistantActionDraftRecord> {
  const token = requireAccessToken();
  return apiRequest<AssistantActionDraftRecord>(`/api/assistant/action-drafts/${draftId}`, {
    method: 'GET',
    token,
  });
}

export async function fetchAssistantActionDraftWorkbench(
  query: AssistantActionDraftWorkbenchQuery = {},
): Promise<AssistantActionDraftWorkbenchResult> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'action', query.action);
  appendQueryParam(params, 'created_from', query.createdFrom);
  appendQueryParam(params, 'created_to', query.createdTo);
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'validation_status', query.validationStatus);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<AssistantActionDraftWorkbenchItem> & {
    summary: AssistantActionDraftWorkbenchSummary;
  }>(
    queryString
      ? `/api/assistant/action-drafts?${queryString}`
      : '/api/assistant/action-drafts',
    { token },
  );

  return {
    page: response.page ?? query.page ?? 1,
    pageSize: response.page_size ?? query.pageSize ?? 10,
    performance: response.performance,
    rows: response.items,
    summary: response.summary,
    total: response.total,
  };
}

export async function confirmAssistantActionDraft(
  draftId: string,
): Promise<AssistantActionDraftConfirmResponse> {
  const token = requireAccessToken();
  return apiRequest<AssistantActionDraftConfirmResponse>(
    `/api/assistant/action-drafts/${draftId}/confirm`,
    {
      method: 'POST',
      token,
    },
  );
}

export async function updateAssistantActionDraft(
  draftId: string,
  payload: Record<string, unknown>,
  modifiedFields: string[] = [],
): Promise<AssistantActionDraftRecord> {
  const token = requireAccessToken();
  return apiRequest<AssistantActionDraftRecord>(
    `/api/assistant/action-drafts/${draftId}`,
    {
      body: {
        modified_fields: modifiedFields,
        payload,
      },
      method: 'PATCH',
      token,
    },
  );
}

export async function cancelAssistantActionDraft(
  draftId: string,
  reason?: string,
): Promise<AssistantActionDraftRecord> {
  const token = requireAccessToken();
  return apiRequest<AssistantActionDraftRecord>(
    `/api/assistant/action-drafts/${draftId}/cancel`,
    {
      body: { reason },
      method: 'POST',
      token,
    },
  );
}

export async function retryAssistantActionDraft(
  draftId: string,
  reason?: string,
): Promise<AssistantActionDraftRecord> {
  const token = requireAccessToken();
  return apiRequest<AssistantActionDraftRecord>(
    `/api/assistant/action-drafts/${draftId}/retry`,
    {
      body: { reason },
      method: 'POST',
      token,
    },
  );
}

export async function markAssistantActionDraftModified(
  draftId: string,
  modifiedFields: string[],
): Promise<AssistantActionDraftRecord> {
  const token = requireAccessToken();
  return apiRequest<AssistantActionDraftRecord>(
    `/api/assistant/action-drafts/${draftId}/modification`,
    {
      body: {
        modified_fields: modifiedFields,
        user_modified: true,
      },
      method: 'POST',
      token,
    },
  );
}

export async function markAssistantActionDraftViewed(
  draftId: string,
  surface?: string,
): Promise<AssistantActionDraftRecord> {
  const token = requireAccessToken();
  return apiRequest<AssistantActionDraftRecord>(
    `/api/assistant/action-drafts/${draftId}/view`,
    {
      body: { surface },
      method: 'POST',
      token,
    },
  );
}

function assistantConversationApiRecordToSummary(
  item: AssistantConversationApiRecord,
): AssistantConversationSummary {
  return {
    collapsedConversationIds: item.collapsed_conversation_ids,
    collapsedMessageCount: item.collapsed_message_count,
    commandSignature: item.command_signature,
    contextScope: item.context_scope,
    createdAt: item.created_at,
    duplicateConversationIds: item.duplicate_conversation_ids,
    duplicateCount: item.duplicate_count,
    id: item.id,
    lastMessageAt: item.last_message_at,
    messageCount: Number(item.message_count ?? 0),
    productId: item.product_id,
    sourceMessageHash: item.source_message_hash,
    title: item.title ?? '新对话',
    updatedAt: item.updated_at,
  };
}

export async function fetchAssistantConversationPage(params: {
  collapse?: boolean;
  cursor?: string;
  limit?: number;
} = {}): Promise<AssistantConversationPage> {
  const token = requireAccessToken();
  const searchParams = new URLSearchParams();
  if (params.collapse === false) {
    searchParams.set('collapse', 'false');
  }
  if (params.cursor) {
    searchParams.set('cursor', params.cursor);
  }
  if (params.limit) {
    searchParams.set('limit', String(params.limit));
  }
  const query = searchParams.toString();
  const response = await apiRequest<ListResponse<AssistantConversationApiRecord>>(
    `/api/assistant/conversations${query ? `?${query}` : ''}`,
    {
      method: 'GET',
      token,
    },
  );
  return {
    items: response.items.map(assistantConversationApiRecordToSummary),
    limit: Number(response.limit ?? params.limit ?? response.items.length),
    nextCursor: response.next_cursor ?? undefined,
    total: Number(response.total ?? response.items.length),
  };
}

export async function fetchAssistantConversations(params: {
  collapse?: boolean;
  cursor?: string;
  limit?: number;
} = {}): Promise<AssistantConversationSummary[]> {
  const response = await fetchAssistantConversationPage(params);
  return response.items;
}

export async function fetchAssistantConversationMessages(
  conversationId: string,
  options: { signal?: AbortSignal } = {},
): Promise<AssistantConversationMessage[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<AssistantMessageApiRecord>>(
    `/api/assistant/conversations/${conversationId}/messages`,
    {
      method: 'GET',
      signal: options.signal,
      token,
    },
  );
  return response.items.map((item) => ({
    cancelledAt: item.cancelled_at,
    clientRequestId: item.client_request_id,
    completedAt: item.completed_at,
    content: item.content ?? '',
    createdAt: item.created_at,
    errorCode: item.error_code,
    failedAt: item.failed_at,
    id: item.id ?? conversationId,
    intent: item.intent,
    model: item.model,
    productId: item.product_id,
    references: item.references ?? [],
    role: item.role === 'user' ? 'user' : 'assistant',
    runId: item.run_id,
    status: item.status,
    suggestions: item.suggestions ?? [],
    toolResults: item.tool_results ?? [],
  }));
}

function formatListDate(value?: string) {
  return formatDisplayDateTime(value);
}

function normalizeProductStatus(status?: string): ProductRecord['status'] {
  return status === 'inactive' ? 'inactive' : 'active';
}

function normalizeProductVersionStatus(status?: string): ProductVersionRecord['status'] {
  if (
    status === 'archived' ||
    status === 'planning' ||
    status === 'released' ||
    status === 'testing'
  ) {
    return status;
  }
  return 'active';
}

function normalizeActiveInactiveStatus(
  status?: string,
): ProductModuleRecord['status'] | ProductGitRepositoryRecord['status'] {
  return status === 'inactive' ? 'inactive' : 'active';
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

function normalizeKnowledgeStatus(status?: string): KnowledgeRecord['status'] {
  if (
    status === 'archived' ||
    status === 'importing' ||
    status === 'indexed' ||
    status === 'index_failed' ||
    status === 'pending_index' ||
    status === 'text_indexed' ||
    status === 'vector_indexed'
  ) {
    return status;
  }
  if (status === 'failed') {
    return 'index_failed';
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

function normalizeModelGatewayStatus(status?: string): ModelGatewayConfigRecord['status'] {
  return status === 'inactive' ? 'inactive' : 'active';
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
    return formatUnknownValue(author.name ?? author.username ?? author.login);
  }
  return formatUnknownValue(value);
}

function normalizeDiffFileTree(
  items?: GitLabMergeRequestPreviewResponse['diff_file_tree'],
): CodeReviewDiffTreeItem[] {
  return (items ?? []).map((item) => ({
    additions: item.additions ?? 0,
    deletions: item.deletions ?? 0,
    fileCount: item.file_count ?? 0,
    path: item.path ?? '-',
  }));
}

function normalizeRiskSummary(
  summary?: GitLabMergeRequestPreviewResponse['risk_summary'],
): CodeReviewRiskSummary | undefined {
  if (!summary) {
    return undefined;
  }
  return {
    fileCount: summary.file_count,
    largestFile: summary.largest_file
      ? {
          additions: summary.largest_file.additions,
          deletions: summary.largest_file.deletions,
          lineCount: summary.largest_file.line_count,
          path: summary.largest_file.path,
        }
      : null,
    riskLevel: summary.risk_level,
    totalAdditions: summary.total_additions,
    totalChangedLines: summary.total_changed_lines,
    totalDeletions: summary.total_deletions,
  };
}

function normalizePermissionDiagnostics(
  diagnostics?: GitLabMergeRequestPreviewResponse['permission_diagnostics'],
): CodeReviewPermissionDiagnostics | undefined {
  if (!diagnostics) {
    return undefined;
  }
  return {
    baseUrlConfigured: diagnostics.base_url_configured,
    credentialRefConfigured: diagnostics.credential_ref_configured,
    provider: diagnostics.provider,
    repositoryPathConfigured: diagnostics.repository_path_configured,
    tokenAvailable: diagnostics.token_available,
    writebackAllowed: diagnostics.writeback_allowed,
    writebackReason: diagnostics.writeback_reason,
  };
}

function normalizeDiffChangeSummary(
  summary?: GitLabMergeRequestSnapshotResponse['diff_change_summary'],
): CodeReviewDiffChangeSummary | undefined {
  if (!summary) {
    return undefined;
  }
  return {
    addedFiles: summary.added_files ?? [],
    addedFilesCount: summary.added_files_count ?? 0,
    modifiedFiles: summary.modified_files ?? [],
    modifiedFilesCount: summary.modified_files_count ?? 0,
    removedFiles: summary.removed_files ?? [],
    removedFilesCount: summary.removed_files_count ?? 0,
  };
}

function normalizePreviousSnapshot(
  snapshot?: GitLabMergeRequestSnapshotResponse['previous_snapshot'],
): CodeReviewPreviousSnapshot | null {
  if (!snapshot) {
    return null;
  }
  return {
    createdAt: formatListDate(snapshot.created_at),
    headSha: snapshot.head_sha,
    id: snapshot.id,
    snapshotHash: snapshot.snapshot_hash,
  };
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

function normalizeDashboardCount(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

export async function fetchManagementProducts(): Promise<ProductRecord[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    apiRequest<ListResponse<ProductListItem>>('/api/products', { token }),
    apiRequest<ListResponse<ProductVersionListItem>>('/api/product-versions', { token }),
  ]);
  const versionsByProductId = versions.items.reduce(
    (groupedVersions, version) => {
      const rows = groupedVersions.get(version.product_id) ?? [];
      rows.push(version);
      groupedVersions.set(version.product_id, rows);
      return groupedVersions;
    },
    new Map<string, ProductVersionListItem[]>(),
  );

  return products.items.map((product) =>
    mapProductRecord(product, versionsByProductId.get(product.id)),
  );
}

function mapProductRecord(
  product: ProductListItem,
  versions: ProductVersionListItem[] = [],
): ProductRecord {
  return {
    code: product.code ?? product.id,
    id: product.id,
    moduleCount: product.module_count ?? 0,
    name: product.name,
    ownerTeam: product.owner_team ?? '-',
    status: normalizeProductStatus(product.status),
    version:
      product.current_version_name ??
      versions.find((version) => version.status === 'active')?.name ??
      versions[0]?.name ??
      '未配置',
  };
}

export async function fetchManagementProductList(
  query: ProductListQuery = {},
): Promise<RemoteListResult<ProductRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'code', query.code);
  appendQueryParam(params, 'name', query.name);
  appendQueryParam(params, 'owner_team', query.ownerTeam);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const products = await apiRequest<ListResponse<ProductListItem>>(
    queryString ? `/api/products?${queryString}` : '/api/products',
    { token },
  );

  return {
    page: products.page ?? query.page ?? 1,
    pageSize: products.page_size ?? query.pageSize ?? 10,
    performance: products.performance,
    rows: products.items.map((product) => mapProductRecord(product)),
    total: products.total,
  };
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
    description: version.description ?? undefined,
    id: version.id,
    name: version.name,
    status: version.status ?? '-',
  };
}

function isRequirementSchedulableVersion(version: ProductVersionListItem): boolean {
  return ['active', 'planning'].includes((version.status ?? '').toLowerCase());
}

function isBugAssignableVersion(version: ProductVersionListItem): boolean {
  return (version.status ?? '').toLowerCase() !== 'archived';
}

function mapProductContexts(
  products: ProductListItem[],
  versions: ProductVersionListItem[],
): ProductContextOption[] {
  const versionsByProductId = versions.reduce(
    (groupedVersions, version) => {
      const rows = groupedVersions.get(version.product_id) ?? [];
      rows.push(version);
      groupedVersions.set(version.product_id, rows);
      return groupedVersions;
    },
    new Map<string, ProductVersionListItem[]>(),
  );

  return products.map((product) => ({
    code: product.code ?? product.id,
    id: product.id,
    name: product.name,
    versions: (versionsByProductId.get(product.id) ?? []).map(mapProductVersionOption),
  }));
}

function paginatedListPath(path: string, page: number, pageSize: number) {
  const [basePath, queryString = ''] = path.split('?');
  const params = new URLSearchParams(queryString);
  params.set('page_size', String(pageSize));
  if (page > 1) {
    params.set('page', String(page));
  } else {
    params.delete('page');
  }
  return `${basePath}?${params.toString()}`;
}

async function fetchAllListItems<T>(
  path: string,
  {
    pageSize,
    token,
  }: {
    pageSize: number;
    token: string;
  },
): Promise<T[]> {
  const items: T[] = [];
  let currentPage = 1;
  let currentPageSize = pageSize;

  for (let pageCount = 0; pageCount < CONTEXT_OPTION_MAX_PAGE_COUNT; pageCount += 1) {
    const response = await apiRequest<ListResponse<T>>(
      paginatedListPath(path, currentPage, currentPageSize),
      { token },
    );
    items.push(...response.items);
    const total = response.total ?? items.length;
    if (items.length >= total || response.items.length === 0) {
      break;
    }
    currentPage = (response.page ?? currentPage) + 1;
    currentPageSize = response.page_size ?? currentPageSize;
  }

  return items;
}

function mapProductVersionRecord(version: ProductVersionListItem): ProductVersionRecord {
  return {
    code: version.code ?? version.id,
    description: version.description ?? undefined,
    id: version.id,
    name: version.name,
    productCode: version.product_code,
    productId: version.product_id,
    productName: version.product_name,
    releaseDate: version.release_date ?? undefined,
    startDate: version.start_date ?? undefined,
    status: normalizeProductVersionStatus(version.status),
  };
}

function mapProductModuleRecord(module: ProductModuleListItem): ProductModuleRecord {
  return {
    code: module.code ?? module.id,
    id: module.id,
    name: module.name,
    ownerTeam: module.owner_team ?? '-',
    status: normalizeActiveInactiveStatus(module.status),
  };
}

function mapProductRelatedSystemRecord(
  relatedSystem: ProductRelatedSystemListItem,
): ProductRelatedSystemRecord {
  return {
    code: relatedSystem.code ?? relatedSystem.id,
    description: relatedSystem.description,
    id: relatedSystem.id,
    name: relatedSystem.name,
    ownerTeam: relatedSystem.owner_team ?? '-',
    productId: relatedSystem.product_id,
    status: normalizeActiveInactiveStatus(relatedSystem.status),
  };
}

function mapProductGitRepositoryRecord(
  repository: ProductGitRepositoryListItem,
): ProductGitRepositoryRecord {
  const credentialRefConfigured = repository.credential_ref_configured ?? false;
  return {
    credentialRefConfigured,
    credentialStatus: credentialRefConfigured ? '已配置' : '未配置',
    defaultBranch: repository.default_branch ?? 'main',
    id: repository.id,
    name: repository.name,
    projectId: repository.project_id,
    projectPath: repository.project_path,
    provider: repository.git_provider ?? 'gitlab',
    remoteUrl: repository.remote_url ?? '-',
    repoType: repository.repo_type ?? 'code',
    rootPath: repository.root_path ?? '/',
    status: normalizeActiveInactiveStatus(repository.status),
  };
}

function normalizeProductVersionBranchStatus(
  status?: string,
): ProductVersionBranchConfigRecord['branchStatus'] {
  const allowed = new Set(['active', 'archived', 'merged', 'not_created', 'released', 'testing']);
  return allowed.has(status ?? '') ? (status as ProductVersionBranchConfigRecord['branchStatus']) : 'not_created';
}

function normalizeProductVersionBranchCreationSource(
  source?: string,
): ProductVersionBranchConfigRecord['creationSource'] {
  const allowed = new Set(['ai_task', 'github_sync', 'gitlab_sync', 'manual']);
  return allowed.has(source ?? '') ? (source as ProductVersionBranchConfigRecord['creationSource']) : 'manual';
}

function mapProductVersionBranchConfigRecord(
  branchConfig: ProductVersionBranchConfigListItem,
): ProductVersionBranchConfigRecord {
  return {
    baseBranch: branchConfig.base_branch ?? branchConfig.repository_default_branch ?? 'main',
    branchStatus: normalizeProductVersionBranchStatus(branchConfig.branch_status),
    creationSource: normalizeProductVersionBranchCreationSource(branchConfig.creation_source),
    description: branchConfig.description,
    id: branchConfig.id,
    productId: branchConfig.product_id,
    repositoryDefaultBranch: branchConfig.repository_default_branch,
    repositoryId: branchConfig.repository_id,
    repositoryName: branchConfig.repository_name,
    repositoryPath: branchConfig.repository_path,
    repositoryProvider: branchConfig.repository_provider,
    versionId: branchConfig.version_id,
    workingBranch: branchConfig.working_branch ?? '-',
  };
}

export async function fetchProductVersions(productId: string): Promise<ProductVersionRecord[]> {
  const token = requireAccessToken();
  const versions = await apiRequest<ListResponse<ProductVersionListItem>>(
    `/api/products/${productId}/versions`,
    { token },
  );
  return versions.items.map(mapProductVersionRecord);
}

export async function fetchDeliveryIterationVersions(): Promise<ProductVersionRecord[]> {
  const token = requireAccessToken();
  const versions = await apiRequest<ListResponse<ProductVersionListItem>>(
    '/api/product-versions',
    { token },
  );
  return versions.items.map(mapProductVersionRecord);
}

export async function fetchDeliveryIterationVersionList(
  query: ProductVersionListQuery = {},
): Promise<RemoteListResult<ProductVersionRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'code', query.code);
  appendQueryParam(params, 'name', query.name);
  appendQueryParam(params, 'product', query.product);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const versions = await apiRequest<ListResponse<ProductVersionListItem>>(
    queryString ? `/api/product-versions?${queryString}` : '/api/product-versions',
    { token },
  );

  return {
    page: versions.page ?? query.page ?? 1,
    pageSize: versions.page_size ?? query.pageSize ?? 10,
    performance: versions.performance,
    rows: versions.items.map(mapProductVersionRecord),
    total: versions.total,
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

export async function updateProductVersion(
  versionId: string,
  payload: Partial<ProductVersionMutationPayload>,
) {
  const token = requireAccessToken();
  return apiRequest<ProductVersionListItem>(`/api/product-versions/${versionId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function advanceProductVersionStatus(
  versionId: string,
  payload: ProductVersionAdvanceStatusPayload,
): Promise<ProductVersionAdvanceStatusResult> {
  const token = requireAccessToken();
  const result = await apiRequest<ProductVersionAdvanceStatusResponse>(
    `/api/product-versions/${versionId}/advance-status`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return {
    blockedRequirements: result.blocked_requirements,
    force: result.force,
    fromStatus: normalizeProductVersionStatus(result.from_status),
    previewOnly: result.preview_only,
    targetStatus: normalizeProductVersionStatus(result.target_status),
    unchangedRequirements: result.unchanged_requirements,
    updatedRequirements: result.updated_requirements,
    version: mapProductVersionRecord(result.version),
  };
}

export async function deleteProductVersion(versionId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/product-versions/${versionId}`, {
    method: 'DELETE',
    token,
  });
}

export async function fetchProductVersionBranchConfigs(
  versionId: string,
): Promise<ProductVersionBranchConfigRecord[]> {
  const token = requireAccessToken();
  const branchConfigs = await apiRequest<ListResponse<ProductVersionBranchConfigListItem>>(
    `/api/product-versions/${versionId}/branch-configs`,
    { token },
  );
  return branchConfigs.items.map(mapProductVersionBranchConfigRecord);
}

function mapProductVersionDashboard(
  dashboard: ProductVersionDashboardResponse,
): ProductVersionDashboard {
  const summary = dashboard.summary ?? {};
  const statusImpact = dashboard.status_impact
    ? {
        blockedRequirements: dashboard.status_impact.blocked_requirements ?? [],
        targetStatus: normalizeProductVersionStatus(dashboard.status_impact.target_status),
        unchangedRequirements: dashboard.status_impact.unchanged_requirements ?? [],
        updatedRequirements: dashboard.status_impact.updated_requirements ?? [],
      }
    : undefined;
  return {
    accessIssues: (dashboard.access_issues ?? []).map((issue) => ({
      code: issue.code ?? '-',
      message: issue.message ?? '-',
      section: issue.section ?? '-',
    })),
    blockers: (dashboard.blockers ?? []).map((blocker) => ({
      id: blocker.id,
      reason: blocker.reason ?? '-',
      severity: blocker.severity ?? 'medium',
      sourceType: blocker.source_type ?? '-',
      title: blocker.title ?? blocker.id ?? '-',
    })),
    branchConfigs: (dashboard.branch_configs ?? []).map(mapProductVersionBranchConfigRecord),
    bugStatusCounts: dashboard.bug_status_counts ?? [],
    bugs: (dashboard.bugs ?? []).map(mapBugRecord),
    codeInspectionReports: dashboard.code_inspection_reports ?? [],
    releases: (dashboard.releases ?? []).map((release) => ({
      buildId: formatUnknownValue(release.build_id),
      createdAt: formatListDate(formatUnknownValue(release.deployed_at ?? release.started_at ?? release.created_at)),
      id: formatUnknownValue(release.id),
      jobName: formatUnknownValue(release.job_name),
      status: formatUnknownValue(release.status),
    })),
    requirementStatusCounts: dashboard.requirement_status_counts ?? [],
    requirements: (dashboard.requirements ?? []).map(mapRequirementRecord),
    statusImpact,
    summary: {
      blockers: normalizeDashboardCount(summary.blockers),
      branch_configs: normalizeDashboardCount(summary.branch_configs),
      bugs: normalizeDashboardCount(summary.bugs),
      code_inspection_reports: normalizeDashboardCount(summary.code_inspection_reports),
      open_bugs: normalizeDashboardCount(summary.open_bugs),
      releases: normalizeDashboardCount(summary.releases),
      requirements: normalizeDashboardCount(summary.requirements),
      severe_bugs: normalizeDashboardCount(summary.severe_bugs),
      severe_code_inspection_reports: normalizeDashboardCount(summary.severe_code_inspection_reports),
      tasks: normalizeDashboardCount(summary.tasks),
    },
    taskStatusCounts: dashboard.task_status_counts ?? [],
    tasks: (dashboard.tasks ?? []).map(mapTaskRecord),
    version: mapProductVersionRecord(dashboard.version),
  };
}

export async function fetchProductVersionDashboard(
  versionId: string,
): Promise<ProductVersionDashboard> {
  const token = requireAccessToken();
  const dashboard = await apiRequest<ProductVersionDashboardResponse>(
    `/api/product-versions/${versionId}/dashboard`,
    { token },
  );
  return mapProductVersionDashboard(dashboard);
}

export async function createProductVersionBranchConfig(
  versionId: string,
  payload: ProductVersionBranchConfigMutationPayload,
): Promise<ProductVersionBranchConfigRecord> {
  const token = requireAccessToken();
  const branchConfig = await apiRequest<ProductVersionBranchConfigListItem>(
    `/api/product-versions/${versionId}/branch-configs`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return mapProductVersionBranchConfigRecord(branchConfig);
}

export async function updateProductVersionBranchConfig(
  branchConfigId: string,
  payload: Partial<ProductVersionBranchConfigMutationPayload>,
): Promise<ProductVersionBranchConfigRecord> {
  const token = requireAccessToken();
  const branchConfig = await apiRequest<ProductVersionBranchConfigListItem>(
    `/api/product-version-branch-configs/${branchConfigId}`,
    {
      body: payload,
      method: 'PATCH',
      token,
    },
  );
  return mapProductVersionBranchConfigRecord(branchConfig);
}

export async function deleteProductVersionBranchConfig(branchConfigId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(
    `/api/product-version-branch-configs/${branchConfigId}`,
    {
      method: 'DELETE',
      token,
    },
  );
}

export async function fetchProductModules(productId: string): Promise<ProductModuleRecord[]> {
  const token = requireAccessToken();
  const modules = await apiRequest<ListResponse<ProductModuleListItem>>(
    `/api/products/${productId}/modules`,
    { token },
  );
  return modules.items.map(mapProductModuleRecord);
}

export async function createProductModule(
  productId: string,
  payload: ProductModuleMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<ProductModuleListItem>(`/api/products/${productId}/modules`, {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateProductModule(
  moduleId: string,
  payload: Partial<ProductModuleMutationPayload>,
) {
  const token = requireAccessToken();
  return apiRequest<ProductModuleListItem>(`/api/product-modules/${moduleId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteProductModule(moduleId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/product-modules/${moduleId}`, {
    method: 'DELETE',
    token,
  });
}

export async function fetchProductRelatedSystems(
  productId: string,
): Promise<ProductRelatedSystemRecord[]> {
  const token = requireAccessToken();
  const relatedSystems = await apiRequest<ListResponse<ProductRelatedSystemListItem>>(
    `/api/system/related-systems?product_id=${encodeURIComponent(productId)}`,
    { token },
  );
  return relatedSystems.items.map(mapProductRelatedSystemRecord);
}

export async function createProductRelatedSystem(
  productId: string,
  payload: ProductRelatedSystemMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<ProductRelatedSystemListItem>('/api/system/related-systems', {
    body: { ...payload, product_id: productId },
    method: 'POST',
    token,
  });
}

export async function updateProductRelatedSystem(
  relatedSystemId: string,
  payload: Partial<ProductRelatedSystemMutationPayload>,
) {
  const token = requireAccessToken();
  return apiRequest<ProductRelatedSystemListItem>(
    `/api/system/related-systems/${relatedSystemId}`,
    {
      body: payload,
      method: 'PATCH',
      token,
    },
  );
}

export async function deleteProductRelatedSystem(relatedSystemId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(
    `/api/system/related-systems/${relatedSystemId}`,
    {
      method: 'DELETE',
      token,
    },
  );
}

export async function fetchProductGitRepositoryRecords(
  productId: string,
): Promise<ProductGitRepositoryRecord[]> {
  const token = requireAccessToken();
  const repositories = await apiRequest<ListResponse<ProductGitRepositoryListItem>>(
    `/api/products/${productId}/git-repositories`,
    { token },
  );
  return repositories.items.map(mapProductGitRepositoryRecord);
}

export async function createProductGitRepository(
  productId: string,
  payload: ProductGitRepositoryMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<ProductGitRepositoryListItem>(`/api/products/${productId}/git-repositories`, {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateProductGitRepository(
  repositoryId: string,
  payload: Partial<ProductGitRepositoryMutationPayload>,
) {
  const token = requireAccessToken();
  return apiRequest<ProductGitRepositoryListItem>(`/api/product-git-repositories/${repositoryId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteProductGitRepository(repositoryId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(
    `/api/product-git-repositories/${repositoryId}`,
    {
      method: 'DELETE',
      token,
    },
  );
}

export async function fetchProductContextOptions(): Promise<ProductContextOption[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    fetchAllListItems<ProductListItem>('/api/products?active_only=true', {
      pageSize: PRODUCT_CONTEXT_PAGE_SIZE,
      token,
    }),
    fetchAllListItems<ProductVersionListItem>('/api/product-versions?active_only=true', {
      pageSize: VERSION_CONTEXT_PAGE_SIZE,
      token,
    }),
  ]);
  return mapProductContexts(products, versions);
}

export async function fetchBugProductContextOptions(): Promise<ProductContextOption[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    fetchAllListItems<ProductListItem>('/api/products?active_only=true', {
      pageSize: PRODUCT_CONTEXT_PAGE_SIZE,
      token,
    }),
    fetchAllListItems<ProductVersionListItem>('/api/product-versions', {
      pageSize: VERSION_CONTEXT_PAGE_SIZE,
      token,
    }),
  ]);
  return mapProductContexts(products, versions.filter(isBugAssignableVersion));
}

export async function fetchRequirementProductContextOptions(): Promise<ProductContextOption[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    fetchAllListItems<ProductListItem>('/api/products?active_only=true', {
      pageSize: PRODUCT_CONTEXT_PAGE_SIZE,
      token,
    }),
    fetchAllListItems<ProductVersionListItem>('/api/product-versions', {
      pageSize: VERSION_CONTEXT_PAGE_SIZE,
      token,
    }),
  ]);
  return mapProductContexts(
    products,
    versions.filter(isRequirementSchedulableVersion),
  );
}

export async function fetchActiveProductOptions(): Promise<ProductFilterOption[]> {
  const token = requireAccessToken();
  const products = await fetchAllListItems<ProductListItem>('/api/products?active_only=true', {
    pageSize: PRODUCT_CONTEXT_PAGE_SIZE,
    token,
  });
  return products.map((product) => ({
    code: product.code ?? product.id,
    id: product.id,
    name: product.name,
  }));
}

function mapRoleDefinition(role: RoleDefinitionListItem): UserRoleDefinition {
  return {
    business_roles: role.business_roles ?? [],
    category: role.category ?? 'workspace',
    code: role.code,
    data_scope: role.data_scope ?? '',
    decision_scope: role.decision_scope ?? '',
    description: role.description ?? '',
    is_assignable: role.is_assignable ?? true,
    limitations: role.limitations ?? [],
    menu_scope: role.menu_scope ?? role.menu_codes ?? [],
    name: role.name,
    permissions: role.permissions ?? role.permission_codes ?? [],
    responsibilities: role.responsibilities ?? [],
    sort_order: role.sort_order ?? 0,
    status: role.status ?? 'active',
  };
}

function mapSystemRole(role: RoleDefinitionListItem): SystemRoleRecord {
  const roleDefinition = mapRoleDefinition(role);
  return {
    ...roleDefinition,
    id: role.id ?? role.code,
    is_system: role.is_system ?? false,
    menu_codes: role.menu_codes ?? role.menu_scope ?? [],
    permission_codes: role.permission_codes ?? role.permissions ?? [],
    scopes: role.scopes ?? [],
  };
}

export async function fetchRoleDefinitions(): Promise<UserRoleDefinition[]> {
  const token = requireAccessToken();
  const roles = await apiRequest<ListResponse<RoleDefinitionListItem>>('/api/auth/roles', { token });
  return roles.items.map(mapRoleDefinition);
}

export async function fetchRoleDefinitionList(
  query: RoleListQuery = {},
): Promise<RemoteListResult<UserRoleDefinition>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'business_role', query.businessRole);
  appendQueryParam(params, 'category', query.category);
  appendQueryParam(params, 'menu_scope', query.menuScope);
  appendQueryParam(params, 'permission', query.permission);
  appendQueryParam(params, 'role', query.role);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const roles = await apiRequest<ListResponse<RoleDefinitionListItem>>(
    queryString ? `/api/auth/roles?${queryString}` : '/api/auth/roles',
    { token },
  );
  return {
    page: roles.page ?? query.page ?? 1,
    pageSize: roles.page_size ?? query.pageSize ?? 10,
    rows: roles.items.map(mapRoleDefinition),
    total: roles.total,
  };
}

export async function fetchSystemPermissions(): Promise<PermissionRecord[]> {
  const token = requireAccessToken();
  const permissions = await apiRequest<{ items: PermissionRecord[] }>('/api/system/permissions', {
    token,
  });
  return permissions.items;
}

export async function fetchSystemMenus(): Promise<MenuResourceRecord[]> {
  const token = requireAccessToken();
  const menus = await apiRequest<{ items: MenuResourceRecord[] }>('/api/system/menus', { token });
  return menus.items;
}

export async function fetchSystemMenuList(
  query: MenuListQuery = {},
): Promise<RemoteListResult<MenuResourceRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'menu', query.menu);
  appendQueryParam(params, 'menu_type', query.menuType);
  appendQueryParam(params, 'parent', query.parent);
  appendQueryParam(params, 'path', query.path);
  appendQueryParam(params, 'permission', query.permission);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const menus = await apiRequest<ListResponse<MenuResourceRecord>>(
    queryString ? `/api/system/menus?${queryString}` : '/api/system/menus',
    { token },
  );
  return {
    page: menus.page ?? query.page ?? 1,
    pageSize: menus.page_size ?? query.pageSize ?? 10,
    performance: menus.performance,
    rows: menus.items,
    total: menus.total,
  };
}

export async function fetchSystemPermissionMatrix(): Promise<RbacPolicyMatrix> {
  const token = requireAccessToken();
  const matrix = await apiRequest<RbacPolicyMatrix>('/api/system/permissions/matrix', { token });
  return {
    ...matrix,
    roles: matrix.roles.map(mapSystemRole),
  };
}

export async function fetchSystemPermissionDiagnostics(query: {
  path?: string;
  permissionCode?: string;
  scopeId?: string;
  scopeType?: string;
  userId: string;
}): Promise<UserPermissionDiagnostic> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'user_id', query.userId);
  appendQueryParam(params, 'path', query.path);
  appendQueryParam(params, 'permission_code', query.permissionCode);
  appendQueryParam(params, 'scope_type', query.scopeType);
  appendQueryParam(params, 'scope_id', query.scopeId);
  return apiRequest<UserPermissionDiagnostic>(`/api/system/permissions/diagnostics?${params.toString()}`, {
    token,
  });
}

export async function createSystemMenu(
  payload: MenuResourceMutationPayload & { code: string; name: string },
): Promise<MenuResourceRecord> {
  const token = requireAccessToken();
  return apiRequest<MenuResourceRecord>('/api/system/menus', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateSystemMenu(
  menuCode: string,
  payload: MenuResourceMutationPayload,
): Promise<MenuResourceRecord> {
  const token = requireAccessToken();
  return apiRequest<MenuResourceRecord>(`/api/system/menus/${menuCode}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function setSystemMenuStatus(
  menuCode: string,
  status: 'active' | 'inactive',
): Promise<MenuResourceRecord> {
  const token = requireAccessToken();
  const action = status === 'active' ? 'enable' : 'disable';
  return apiRequest<MenuResourceRecord>(`/api/system/menus/${menuCode}/${action}`, {
    method: 'POST',
    token,
  });
}

export async function deleteSystemMenu(menuCode: string): Promise<{ code: string; deleted: boolean }> {
  const token = requireAccessToken();
  return apiRequest<{ code: string; deleted: boolean }>(`/api/system/menus/${menuCode}`, {
    method: 'DELETE',
    token,
  });
}

export async function reorderSystemMenus(
  items: Array<{ code: string; sort_order: number }>,
): Promise<MenuResourceRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<{ items: MenuResourceRecord[] }>('/api/system/menus/reorder', {
    body: { items },
    method: 'PUT',
    token,
  });
  return response.items;
}

export async function fetchSystemRoleList(
  query: RoleListQuery = {},
): Promise<RemoteListResult<SystemRoleRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'business_role', query.businessRole);
  appendQueryParam(params, 'category', query.category);
  appendQueryParam(params, 'menu_scope', query.menuScope);
  appendQueryParam(params, 'permission', query.permission);
  appendQueryParam(params, 'role', query.role);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const roles = await apiRequest<ListResponse<RoleDefinitionListItem>>(
    queryString ? `/api/system/roles?${queryString}` : '/api/system/roles',
    { token },
  );
  return {
    page: roles.page ?? query.page ?? 1,
    pageSize: roles.page_size ?? query.pageSize ?? 10,
    performance: roles.performance,
    rows: roles.items.map(mapSystemRole),
    total: roles.total,
  };
}

export async function createSystemRole(payload: {
  category: string;
  code: string;
  description?: string;
  is_assignable?: boolean;
  name: string;
  sort_order?: number;
}): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>('/api/system/roles', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapSystemRole(role);
}

export async function updateSystemRole(
  roleId: string,
  payload: {
    category?: string;
    description?: string;
    is_assignable?: boolean;
    name?: string;
    sort_order?: number;
  },
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
  return mapSystemRole(role);
}

export async function copySystemRole(
  roleId: string,
  payload: {
    code: string;
    description?: string;
    name?: string;
  },
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/copy`, {
    body: payload,
    method: 'POST',
    token,
  });
  return mapSystemRole(role);
}

export async function setSystemRoleStatus(
  roleId: string,
  status: 'active' | 'inactive',
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const action = status === 'active' ? 'enable' : 'disable';
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/${action}`, {
    method: 'POST',
    token,
  });
  return mapSystemRole(role);
}

export async function updateSystemRolePermissions(
  roleId: string,
  permissionCodes: string[],
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/permissions`, {
    body: { permission_codes: permissionCodes },
    method: 'PUT',
    token,
  });
  return mapSystemRole(role);
}

export async function updateSystemRoleMenus(
  roleId: string,
  menuCodes: string[],
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/menus`, {
    body: { menu_codes: menuCodes },
    method: 'PUT',
    token,
  });
  return mapSystemRole(role);
}

export async function updateSystemRoleScopes(
  roleId: string,
  scopes: ScopeGrant[],
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/scopes`, {
    body: { scopes },
    method: 'PUT',
    token,
  });
  return mapSystemRole(role);
}

export async function fetchManagementUsers(
  roleDefinitions: UserRoleDefinition[] = [],
): Promise<UserRecord[]> {
  const token = requireAccessToken();
  const users = await apiRequest<ListResponse<UserListItem>>('/api/users', { token });

  return users.items.map((user) => {
    const roles = user.roles ?? [];
    return {
      displayName: user.display_name,
      id: user.id,
      roles,
      rolesText: formatUserRoles(roles, roleDefinitions),
      status: user.status === 'inactive' ? 'inactive' : 'active',
      username: user.username,
    };
  });
}

export async function fetchManagementUserList(
  roleDefinitions: UserRoleDefinition[] = [],
  query: UserListQuery = {},
): Promise<RemoteListResult<UserRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'display_name', query.displayName);
  appendQueryParam(params, 'role', query.role);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'username', query.username);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const users = await apiRequest<ListResponse<UserListItem>>(
    queryString ? `/api/users?${queryString}` : '/api/users',
    { token },
  );

  return {
    page: users.page ?? query.page ?? 1,
    pageSize: users.page_size ?? query.pageSize ?? 10,
    performance: users.performance,
    rows: users.items.map((user) => {
      const roles = user.roles ?? [];
      return {
        displayName: user.display_name,
        id: user.id,
        roles,
        rolesText: formatUserRoles(roles, roleDefinitions),
        status: user.status === 'inactive' ? 'inactive' : 'active',
        username: user.username,
      };
    }),
    total: users.total,
  };
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

function mapModelGatewayConfig(config: ModelGatewayConfigListItem): ModelGatewayConfigRecord {
  const apiKeyConfigured = Boolean(config.api_key_configured);
  const embeddingConnectionMode =
    config.embedding_connection_mode === 'custom' || config.embedding_connection_mode === 'disabled'
      ? config.embedding_connection_mode
      : 'reuse_chat';
  return {
    apiKeyConfigured,
    baseUrl: config.base_url ?? '-',
    defaultChatModel: config.default_chat_model ?? '-',
    defaultEmbeddingModel: config.default_embedding_model ?? null,
    embeddingApiKeyConfigured: Boolean(config.embedding_api_key_configured),
    embeddingBaseUrl: config.embedding_base_url ?? null,
    embeddingConnectionMode,
    embeddingDimension: config.embedding_dimension ?? null,
    id: config.id,
    isDefault: Boolean(config.is_default),
    keyStatus: apiKeyConfigured ? '已配置' : '未配置',
    maxRetries: config.max_retries ?? 0,
    name: config.name,
    provider: config.provider ?? '-',
    status: normalizeModelGatewayStatus(config.status),
    timeoutSeconds: config.timeout_seconds ?? 0,
  };
}

export type ModelGatewayLogRecord = {
  aiTaskId?: string | null;
  createdAt?: string;
  error?: string | null;
  id: string;
  latencyMs?: number | null;
  model: string;
  modelGatewayConfigId?: string | null;
  provider: string;
  purpose: string;
  status: string;
  tokens: Record<string, unknown>;
  updatedAt?: string;
};

function mapModelGatewayLog(log: ModelGatewayLogListItem): ModelGatewayLogRecord {
  return {
    aiTaskId: log.ai_task_id ?? null,
    createdAt: log.created_at,
    error: log.error ?? null,
    id: log.id,
    latencyMs: log.latency_ms ?? null,
    model: log.model ?? '-',
    modelGatewayConfigId: log.model_gateway_config_id ?? null,
    provider: log.provider ?? '-',
    purpose: log.purpose ?? '-',
    status: log.status ?? '-',
    tokens: log.tokens && typeof log.tokens === 'object' ? log.tokens : {},
    updatedAt: log.updated_at,
  };
}

export async function fetchModelGatewayConfigList(
  query: ModelGatewayConfigListQuery = {},
): Promise<RemoteListResult<ModelGatewayConfigRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'default_chat_model', query.defaultChatModel);
  appendQueryParam(params, 'default_embedding_model', query.defaultEmbeddingModel);
  appendQueryParam(params, 'embedding_connection_mode', query.embeddingConnectionMode);
  appendQueryParam(params, 'is_default', query.isDefault);
  appendQueryParam(params, 'name', query.name);
  appendQueryParam(params, 'provider', query.provider);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const configs = await apiRequest<ListResponse<ModelGatewayConfigListItem>>(
    queryString ? `/api/system/model-gateway-configs?${queryString}` : '/api/system/model-gateway-configs',
    { token },
  );
  return {
    page: configs.page ?? query.page ?? 1,
    pageSize: configs.page_size ?? query.pageSize ?? 10,
    performance: configs.performance,
    rows: configs.items.map(mapModelGatewayConfig),
    total: configs.total,
  };
}

export async function fetchModelGatewayConfigs(): Promise<ModelGatewayConfigRecord[]> {
  const token = requireAccessToken();
  const configs = await apiRequest<ListResponse<ModelGatewayConfigListItem>>(
    '/api/system/model-gateway-configs',
    { token },
  );
  return configs.items.map(mapModelGatewayConfig);
}

export async function fetchModelGatewayLogs(
  query: ModelGatewayLogQuery = {},
): Promise<RemoteListResult<ModelGatewayLogRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'ai_task_id', query.aiTaskId);
  appendQueryParam(params, 'purpose', query.purpose);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const logs = await apiRequest<ListResponse<ModelGatewayLogListItem>>(
    queryString ? `/api/model-gateway/logs?${queryString}` : '/api/model-gateway/logs',
    { token },
  );
  return {
    page: logs.page ?? query.page ?? 1,
    pageSize: logs.page_size ?? query.pageSize ?? 10,
    performance: logs.performance,
    rows: logs.items.map(mapModelGatewayLog),
    total: logs.total,
  };
}

export async function createModelGatewayConfig(payload: ModelGatewayConfigMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<ModelGatewayConfigListItem>('/api/system/model-gateway-configs', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateModelGatewayConfig(
  configId: string,
  payload: ModelGatewayConfigMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<ModelGatewayConfigListItem>(`/api/system/model-gateway-configs/${configId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function testModelGatewayConfig(
  payload: ModelGatewayConfigMutationPayload,
): Promise<ModelGatewayConfigTestResult> {
  const token = requireAccessToken();
  return apiRequest<ModelGatewayConfigTestResult>('/api/system/model-gateway-configs/test', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function deleteModelGatewayConfig(configId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(
    `/api/system/model-gateway-configs/${configId}`,
    {
      method: 'DELETE',
      token,
    },
  );
}

export type AiSkillRecord = {
  allowed_tools?: string[];
  code: string;
  id: string;
  input_schema?: Record<string, unknown>;
  manifest?: Record<string, unknown>;
  name: string;
  output_schema?: Record<string, unknown>;
  package_checksum?: string | null;
  package_entry?: string | null;
  package_files?: string[];
  package_size_bytes?: number;
  package_uri?: string | null;
  prompt_template?: string;
  requires_human_review?: boolean;
  risk_level?: string;
  source_type?: string;
  status: string;
  version?: string;
};

export type AiSkillPackageUploadOptions = {
  code: string;
  name: string;
  requiresHumanReview?: boolean;
  riskLevel?: string;
  status?: string;
  version?: string;
};

async function readUploadFileBytes(file: File): Promise<ArrayBuffer> {
  if (typeof file.arrayBuffer === 'function') {
    return file.arrayBuffer();
  }
  return new Response(file).arrayBuffer();
}

export type AiAgentRecord = {
  brain_app_id?: string;
  code: string;
  default_skill_ids?: string[];
  id: string;
  model_gateway_config?: Record<string, unknown> | null;
  model_gateway_config_id?: string | Record<string, unknown> | null;
  model_gateway_config_snapshot?: Record<string, unknown> | null;
  name: string;
  resolved_model_gateway_config?: Record<string, unknown> | null;
  status: string;
  system_prompt?: string;
  tool_policy?: Record<string, unknown>;
};

export type ScheduledJobRecord = {
  agent_id?: string | null;
  config_json?: Record<string, unknown>;
  cron_expression?: string | null;
  enabled?: boolean;
  execution_mode?: string;
  id: string;
  interval_seconds?: number | null;
  job_type: string;
  knowledge_document_ids?: string[];
  model_gateway_config_id?: string | null;
  name: string;
  next_run_at?: string | null;
  plugin_action_id?: string | null;
  plugin_action_ids?: string[];
  plugin_connection_id?: string | null;
  plugin_connection_ids?: string[];
  plugin_input_mapping?: Record<string, unknown>;
  plugin_output_mapping?: Record<string, unknown>;
  product_id?: string | null;
  result_actions?: ScheduledJobResultAction[];
  schedule_type?: string;
  skill_ids?: string[];
  source_system?: string;
  status?: string;
  timezone?: string;
};

export type ScheduledJobResultAction = {
  channels?: string[];
  recipients?: string[];
  severity_threshold?: string;
  type: string;
  webhook_url?: string;
};

export type ScheduledJobCatalogOption = {
  label: string;
  value: string;
};

export type ScheduledJobCatalogJobType = ScheduledJobCatalogOption & {
  category?: string;
  default_execution_mode?: string;
  requires_ai_assembly?: boolean;
  requires_plugin_resource?: boolean;
  requires_product?: boolean;
};

export type ScheduledJobCatalogRecord = {
  code_inspection?: {
    builtin_rules?: ScheduledJobCatalogOption[];
    default_result_actions?: ScheduledJobResultAction[];
    default_scan_mode?: string;
    ignore_rules?: ScheduledJobCatalogOption[];
    native_scan_mode?: string;
    result_actions?: ScheduledJobCatalogOption[];
    scan_modes?: ScheduledJobCatalogOption[];
    scanner_engines?: ScheduledJobCatalogOption[];
    severity_thresholds?: ScheduledJobCatalogOption[];
  };
  connection_environments?: ScheduledJobCatalogOption[];
  execution_modes?: ScheduledJobCatalogOption[];
  job_types?: ScheduledJobCatalogJobType[];
  required_job_types?: {
    ai_processing?: string[];
    plugin_resource?: string[];
    product?: string[];
  };
  schedule_types?: ScheduledJobCatalogOption[];
};

export type ScheduledJobTemplateWizardStepRecord = {
  description?: string;
  key: string;
  required?: boolean;
  title: string;
};

export type ScheduledJobTemplateRecord = {
  available_resource_counts?: Record<string, number>;
  category?: string;
  code: string;
  description?: string;
  installed?: boolean;
  name: string;
  payload_defaults?: Partial<ScheduledJobRecord>;
  publisher?: string;
  recommended_scenarios?: string[];
  resource_selectors?: Record<string, unknown>;
  template_version?: string;
  wizard_steps?: ScheduledJobTemplateWizardStepRecord[];
};

export type ScheduledJobDryRunResult = {
  job_type?: string;
  stages?: {
    ai_processing?: Record<string, unknown>;
    data_connection?: Record<string, unknown>;
    result_actions?: Array<Record<string, unknown>>;
  };
  status: string;
};

export type ScheduledJobRunRecord = {
  config_snapshot?: Record<string, unknown>;
  collector_run_id?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  finished_at?: string | null;
  id: string;
  plugin_invocation_log_id?: string | null;
  records_imported?: number;
  resolved_agent_snapshot?: Record<string, unknown>;
  resolved_plugin_snapshot?: Record<string, unknown>;
  resolved_prompt_snapshot?: Record<string, unknown>;
  resolved_skill_snapshots?: Array<Record<string, unknown>>;
  result_summary?: Record<string, unknown>;
  scheduled_job_id?: string;
  source_run_id?: string | null;
  source_run_summary?: {
    error_code?: string | null;
    finished_at?: string | null;
    id?: string;
    latency_ms?: number | null;
    records_imported?: number;
    started_at?: string | null;
    status?: string | null;
    trigger_type?: string | null;
  } | null;
  started_at?: string | null;
  status: string;
  tool_policy_snapshot?: Record<string, unknown>;
  trigger_type?: string;
  updated_at?: string | null;
};

export type ScheduledJobRunObservability = {
  error_distribution?: Array<{ count: number; error: string }>;
  generated_at?: string;
  job_type_distribution?: Array<{ count: number; job_type: string }>;
  recent_failures?: Array<{
    error_code?: string | null;
    error_message?: string | null;
    id: string;
    job_name?: string;
    latency_ms?: number | null;
    scheduled_job_id?: string | null;
    started_at?: string | null;
  }>;
  slow_runs?: Array<{
    error_code?: string | null;
    id: string;
    job_name?: string;
    latency_ms?: number | null;
    records_imported?: number;
    scheduled_job_id?: string | null;
    started_at?: string | null;
    status?: string;
  }>;
  status_distribution?: Array<{ count: number; status: string }>;
  summary: {
    action_write_runs?: number;
    action_write_success_rate?: number;
    action_write_success_runs?: number;
    average_latency_ms?: number;
    average_records_imported?: number;
    cancelled_runs?: number;
    failed_runs?: number;
    failure_rate?: number;
    model_gateway_called_runs?: number;
    model_gateway_token_total?: number;
    plugin_invocation_runs?: number;
    running_runs?: number;
    success_rate?: number;
    succeeded_runs?: number;
    total_runs?: number;
  };
  trigger_type_distribution?: Array<{ count: number; trigger_type: string }>;
  write_target_distribution?: Array<{ count: number; write_target: string }>;
};

export type PluginRecord = {
  category?: string;
  code: string;
  description?: string | null;
  id: string;
  is_system?: boolean;
  latest_template_version?: string;
  name: string;
  protocol: string;
  risk_level?: string;
  source_plugin_code?: string | null;
  source_plugin_id?: string | null;
  status: string;
  template_version?: string;
  upgrade_available?: boolean;
  version_status?: string;
};

export type PluginMarketplaceItem = {
  action_count: number;
  action_templates?: string[];
  category: string;
  code: string;
  connection_schema?: PluginConnectionSchemaRecord;
  connection_defaults?: Record<string, unknown>;
  connection_count: number;
  connection_template_version?: string;
  description?: string | null;
  id: string;
  installed: boolean;
  is_system?: boolean;
  latest_template_version?: string;
  name: string;
  plugin_id?: string | null;
  protocol: string;
  publisher?: string;
  recommended_scenarios?: string[];
  risk_level?: string;
  status: string;
  summary?: string;
  template_version?: string;
  upgrade_available?: boolean;
  version_status?: string;
};

export type PluginConnectionSchemaFieldRecord = {
  description?: string;
  key: string;
  label: string;
  managed_query_keys?: string[];
  options?: Array<{ label: string; value: string } | string>;
  path?: string;
  placeholder?: string;
  required?: boolean;
  supports_system_variables?: boolean;
  type?: string;
};

export type PluginConnectionSchemaSectionRecord = {
  fields: PluginConnectionSchemaFieldRecord[];
  key: string;
  title: string;
};

export type PluginConnectionSchemaRecord = {
  schema_version?: string;
  sections?: PluginConnectionSchemaSectionRecord[];
};

export type PluginActionTemplateRecord = {
  action_type: string;
  code: string;
  default_code?: string;
  default_name?: string;
  description?: string | null;
  form_defaults?: Record<string, unknown>;
  name: string;
  plugin_code: string;
  plugin_id?: string | null;
  request_config?: Record<string, unknown>;
  result_mapping?: Record<string, unknown>;
  template_version?: string;
};

export type ResultWriteTargetFieldRecord = {
  description?: string;
  key: string;
  label: string;
  placeholder?: string;
  required?: boolean;
};

export type ResultWriteTargetRecord = {
  code: string;
  default_result_mapping: Record<string, unknown>;
  description?: string;
  form_label?: string;
  label: string;
  mapping_fields: ResultWriteTargetFieldRecord[];
  supported_job_types?: string[];
};

export type ResultWriteRecord = {
  created_at?: string | null;
  feedback?: Record<string, unknown>;
  id: string;
  plugin_action_id?: string | null;
  plugin_code?: string | null;
  plugin_connection_id?: string | null;
  plugin_id?: string | null;
  plugin_invocation_log_id?: string | null;
  preview?: Record<string, unknown>;
  records_imported?: number;
  scheduled_job_id?: string | null;
  scheduled_job_name?: string | null;
  scheduled_job_run_id?: string | null;
  source_type?: string;
  status: string;
  summary_fields?: {
    candidate_count?: number;
    delivery_id?: unknown;
    delivery_status?: unknown;
    preview_value?: unknown;
    report_preview?: unknown;
    sample_records?: unknown[];
    source_row_count?: number | null;
    subject?: unknown;
  };
  updated_at?: string | null;
  write_target: string;
  write_target_label?: string;
};

export type PluginConnectionRecord = {
  auth_config?: Record<string, unknown>;
  auth_type?: string;
  endpoint_url: string;
  environment?: string;
  id: string;
  last_test_summary?: {
    checked_at?: string | null;
    error_code?: string | null;
    error_message?: string | null;
    failed_step?: string | null;
    latency_ms?: number | null;
    mocked?: boolean;
    response_status_code?: number | null;
    status?: string | null;
  };
  max_retries?: number;
  name: string;
  plugin_id: string;
  request_config?: Record<string, unknown>;
  status: string;
  test_history?: PluginConnectionTestHistoryRecord[];
  timeout_seconds?: number;
};

export type PluginConnectionRepairSuggestion = {
  code: string;
  detail: string;
  title: string;
};

export type PluginConnectionActionTemplateDraft = {
  action_type?: string;
  code?: string;
  connection_id?: string;
  description?: string;
  name?: string;
  plugin_id?: string;
  request_config?: Record<string, unknown>;
  requires_human_review?: boolean;
  result_mapping?: Record<string, unknown>;
  status?: string;
};

export type PluginConnectionTestHistoryRecord = {
  action_template_draft?: PluginConnectionActionTemplateDraft;
  checked_at?: string;
  error_code?: string | null;
  error_message?: string | null;
  latency_ms?: number;
  repair_suggestions?: PluginConnectionRepairSuggestion[];
  request_summary?: Record<string, unknown>;
  response_summary?: Record<string, unknown>;
  status?: string;
};

export type PluginConnectionTestResult = {
  action_template_draft?: PluginConnectionActionTemplateDraft;
  checked_at: string;
  connection_id: string;
  diagnostics?: Array<{
    detail?: string;
    error_code?: string;
    latency_ms?: number;
    name: string;
    status: string;
    status_code?: number;
  }>;
  endpoint_url?: string;
  environment?: string;
  error_code?: string | null;
  error_message?: string | null;
  latency_ms: number;
  mocked?: boolean;
  plugin_id: string;
  protocol: string;
  request_summary?: Record<string, unknown>;
  repair_suggestions?: PluginConnectionRepairSuggestion[];
  response_summary?: Record<string, unknown>;
  status: string;
  test_history?: PluginConnectionTestHistoryRecord[];
};

export type PluginActionRecord = {
  action_type: string;
  code: string;
  connection_id?: string | null;
  description?: string | null;
  id: string;
  input_schema?: Record<string, unknown>;
  name: string;
  output_schema?: Record<string, unknown>;
  plugin_id: string;
  request_config?: Record<string, unknown>;
  requires_human_review?: boolean;
  result_mapping?: Record<string, unknown>;
  status: string;
};

export type PluginInvocationLogRecord = {
  action_id: string;
  connection_id?: string | null;
  error_message?: string | null;
  id: string;
  latency_ms?: number;
  plugin_id: string;
  request_summary?: Record<string, unknown>;
  response_summary?: Record<string, unknown>;
  scheduled_job_id?: string | null;
  scheduled_job_run_id?: string | null;
  status: string;
  trigger_type?: string;
};

export type AiExecutorRunnerRecord = {
  created_at?: string | null;
  endpoint_url?: string;
  executor_types?: string[];
  heartbeat_age_seconds?: number | null;
  heartbeat_timeout_seconds?: number;
  health_status?: string;
  id: string;
  latest_task_id?: string | null;
  latest_task_status?: string | null;
  last_heartbeat_at?: string | null;
  max_concurrent_tasks?: number;
  metadata?: Record<string, unknown>;
  name: string;
  protocol?: string;
  runner_token?: string;
  setup_command?: string;
  status: string;
  token_configured?: boolean;
  token_rotated_at?: string | null;
  token_version?: number;
  updated_at?: string | null;
  workspace_roots?: string[];
};

export type AiExecutorRunnerListQuery = RemoteListQuery & {
  executorType?: string;
  keyword?: string;
  protocol?: string;
  status?: string;
};

export type AiExecutorTaskRecord = {
  action_id?: string | null;
  ai_task_id?: string | null;
  assigned_at?: string | null;
  cancelled_at?: string | null;
  claimed_at?: string | null;
  completed_at?: string | null;
  created_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  executor_type?: string | null;
  finished_at?: string | null;
  id: string;
  logs?: AiExecutorTaskLogRecord[];
  request_config?: Record<string, unknown>;
  result?: Record<string, unknown>;
  runner_id?: string | null;
  scheduled_job_run_id?: string | null;
  status: string;
  timed_out_at?: string | null;
  updated_at?: string | null;
  workspace_root?: string | null;
};

export type RdTaskExecutorPolicyRecord = {
  branch?: string | null;
  created_at?: string | null;
  created_by?: string | null;
  executor_type: string;
  id: string;
  instruction_template: string;
  name: string;
  output_contract?: Record<string, unknown>;
  priority: number;
  product_id?: string | null;
  product_name?: string | null;
  repository_default_branch?: string | null;
  repository_id?: string | null;
  repository_name?: string | null;
  runner_id?: string | null;
  runner_name?: string | null;
  status: string;
  task_type: string;
  timeout_seconds: number;
  updated_at?: string | null;
  workspace_root: string;
};

export type RdTaskExecutorPolicyPayload = {
  branch?: string | null;
  executor_type?: string;
  instruction_template?: string;
  name?: string;
  output_contract?: Record<string, unknown>;
  priority?: number;
  product_id?: string | null;
  repository_id?: string | null;
  runner_id?: string | null;
  status?: string;
  task_type?: string;
  timeout_seconds?: number;
  workspace_root?: string;
};

export type AiExecutorTaskLogRecord = {
  created_at?: string | null;
  level?: string;
  message: string;
  metadata?: Record<string, unknown>;
  sequence?: number;
};

export type AiExecutorTaskLogsResponse = {
  logs: AiExecutorTaskLogRecord[];
  task: AiExecutorTaskRecord;
};

export type AiExecutorRunnerInstallPackageOptions = {
  arch?: string;
  install_mode?: string;
  target_os?: string;
};

export type AiExecutorRunnerTestDiagnostic = {
  detail?: string | null;
  latency_ms?: number | null;
  name: string;
  status: string;
};

export type AiExecutorRunnerTestResult = {
  checked_at?: string | null;
  diagnostics?: AiExecutorRunnerTestDiagnostic[];
  health_status?: string | null;
  heartbeat_age_seconds?: number | null;
  latency_ms?: number | null;
  runner?: AiExecutorRunnerRecord;
  runner_id: string;
  status: string;
};

export type PluginSystemVariableRecord = {
  description?: string;
  expression: string;
  label: string;
  value: string;
};

export type PluginActionTrialResult = {
  action_id: string;
  connection_id: string;
  error_code?: string | null;
  error_message?: string | null;
  latency_ms: number;
  mapping_hits?: Array<{
    key: string;
    matched: boolean;
    path: string;
    value_preview?: unknown;
  }>;
  plugin_id: string;
  request_preview?: Record<string, unknown>;
  response_summary?: Record<string, unknown>;
  status: string;
  write_preview?: {
    candidate_count?: number;
    preview_value?: unknown;
    records_imported?: number;
    report_preview?: Record<string, unknown>;
    sample_records?: unknown[];
    source_row_count?: number | null;
    write_target?: string;
    write_target_label?: string;
  };
};

export async function fetchPlugins(): Promise<PluginRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<PluginRecord>>('/api/system/plugins', { token });
  return response.items;
}

export async function fetchPluginMarketplace(): Promise<PluginMarketplaceItem[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<PluginMarketplaceItem>>('/api/system/plugin-marketplace', { token });
  return response.items;
}

export async function fetchPluginActionTemplates(): Promise<PluginActionTemplateRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<PluginActionTemplateRecord>>('/api/system/plugin-action-templates', { token });
  return response.items;
}

export async function fetchAiExecutorRunners(query: { status?: string } = {}): Promise<AiExecutorRunnerRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'status', query.status);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const response = await apiRequest<ListResponse<AiExecutorRunnerRecord>>(`/api/system/ai-executor-runners${suffix}`, { token });
  return response.items;
}

export async function fetchAiExecutorRunnersPage(
  query: AiExecutorRunnerListQuery = {},
): Promise<RemoteListResult<AiExecutorRunnerRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'executor_type', query.executorType);
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'protocol', query.protocol);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const response = await apiRequest<ListResponse<AiExecutorRunnerRecord>>(
    `/api/system/ai-executor-runners?${params.toString()}`,
    { token },
  );
  return {
    page: response.page ?? query.page ?? 1,
    pageSize: response.page_size ?? query.pageSize ?? 10,
    performance: response.performance,
    rows: response.items,
    total: response.total,
  };
}

export async function createAiExecutorRunner(payload: Partial<AiExecutorRunnerRecord>) {
  const token = requireAccessToken();
  return apiRequest<AiExecutorRunnerRecord>('/api/system/ai-executor-runners', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateAiExecutorRunner(runnerId: string, payload: Partial<AiExecutorRunnerRecord>) {
  const token = requireAccessToken();
  return apiRequest<AiExecutorRunnerRecord>(`/api/system/ai-executor-runners/${runnerId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteAiExecutorRunner(runnerId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/system/ai-executor-runners/${runnerId}`, {
    method: 'DELETE',
    token,
  });
}

export async function rotateAiExecutorRunnerToken(
  runnerId: string,
  payload: { runner_token?: string } = {},
) {
  const token = requireAccessToken();
  return apiRequest<AiExecutorRunnerRecord & { runner_token?: string }>(
    `/api/system/ai-executor-runners/${runnerId}/rotate-token`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
}

export async function testAiExecutorRunner(runnerId: string): Promise<AiExecutorRunnerTestResult> {
  const token = requireAccessToken();
  return apiRequest<AiExecutorRunnerTestResult>(`/api/system/ai-executor-runners/${runnerId}/test`, {
    method: 'POST',
    token,
  });
}

function filenameFromContentDisposition(value: string | null, fallback: string): string {
  if (!value) {
    return fallback;
  }
  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }
  const quotedMatch = value.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }
  const plainMatch = value.match(/filename=([^;]+)/i);
  return plainMatch?.[1]?.trim() || fallback;
}

export async function downloadAiExecutorRunnerInstallPackage(
  runnerId: string,
  options: AiExecutorRunnerInstallPackageOptions = {},
) {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'target_os', options.target_os);
  appendQueryParam(params, 'arch', options.arch);
  appendQueryParam(params, 'install_mode', options.install_mode);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const response = await fetch(`${API_BASE_URL}/api/system/ai-executor-runners/${runnerId}/install-package${suffix}`, {
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
    throw new ApiRequestError({
      code: payload?.detail?.code,
      message: payload?.detail?.message ?? `API request failed: ${response.status}`,
      status: response.status,
      traceId: payload?.detail?.trace_id,
    });
  }
  return {
    blob: await response.blob(),
    filename: filenameFromContentDisposition(
      response.headers.get('Content-Disposition'),
      `ai-brain-runner-${runnerId}.zip`,
    ),
  };
}

export async function fetchAiExecutorTaskLogs(taskId: string): Promise<AiExecutorTaskLogsResponse> {
  const token = requireAccessToken();
  return apiRequest<AiExecutorTaskLogsResponse>(`/api/system/ai-executor-tasks/${taskId}/logs`, {
    token,
  });
}

export async function fetchRdTaskExecutorPolicies(
  query: Pick<RdTaskExecutorPolicyListQuery, 'productId' | 'status' | 'taskType'> = {},
): Promise<RdTaskExecutorPolicyRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'product_id', query.productId);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'task_type', query.taskType);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const response = await apiRequest<ListResponse<RdTaskExecutorPolicyRecord>>(
    `/api/delivery/rd-task-executor-policies${suffix}`,
    { token },
  );
  return response.items;
}

export async function fetchRdTaskExecutorPolicyList(
  query: RdTaskExecutorPolicyListQuery,
): Promise<RemoteListResult<RdTaskExecutorPolicyRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'executor_type', query.executorType);
  appendQueryParam(params, 'name', query.name);
  appendQueryParam(params, 'product_id', query.productId);
  appendQueryParam(params, 'product_name', query.productName);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'task_type', query.taskType);
  appendRemoteListParams(params, query);
  const response = await apiRequest<ListResponse<RdTaskExecutorPolicyRecord>>(
    `/api/delivery/rd-task-executor-policies?${params.toString()}`,
    { token },
  );
  return {
    page: response.page ?? query.page ?? 1,
    pageSize: response.page_size ?? query.pageSize ?? 10,
    performance: response.performance,
    rows: response.items,
    total: response.total,
  };
}

export async function createRdTaskExecutorPolicy(payload: RdTaskExecutorPolicyPayload) {
  const token = requireAccessToken();
  return apiRequest<RdTaskExecutorPolicyRecord>('/api/delivery/rd-task-executor-policies', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateRdTaskExecutorPolicy(
  policyId: string,
  payload: RdTaskExecutorPolicyPayload,
) {
  const token = requireAccessToken();
  return apiRequest<RdTaskExecutorPolicyRecord>(
    `/api/delivery/rd-task-executor-policies/${policyId}`,
    {
      body: payload,
      method: 'PATCH',
      token,
    },
  );
}

export async function deleteRdTaskExecutorPolicy(policyId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(
    `/api/delivery/rd-task-executor-policies/${policyId}`,
    {
      method: 'DELETE',
      token,
    },
  );
}

export async function cancelAiExecutorTask(
  taskId: string,
  reason?: string,
): Promise<{ task: AiExecutorTaskRecord }> {
  const token = requireAccessToken();
  return apiRequest<{ task: AiExecutorTaskRecord }>(`/api/system/ai-executor-tasks/${taskId}/cancel`, {
    body: { reason },
    method: 'POST',
    token,
  });
}

export async function fetchResultWriteTargets(): Promise<ResultWriteTargetRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<ResultWriteTargetRecord>>('/api/system/result-write-targets', { token });
  return response.items;
}

export async function fetchResultWriteRecords(query: {
  page?: number;
  pageSize?: number;
  pluginActionId?: string;
  scheduledJobId?: string;
  scheduledJobRunId?: string;
  sortField?: string;
  sortOrder?: 'ascend' | 'descend';
  status?: string;
  writeTarget?: string;
} = {}): Promise<ResultWriteRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'page', query.page);
  appendQueryParam(params, 'page_size', query.pageSize);
  appendQueryParam(params, 'plugin_action_id', query.pluginActionId);
  appendQueryParam(params, 'scheduled_job_id', query.scheduledJobId);
  appendQueryParam(params, 'scheduled_job_run_id', query.scheduledJobRunId);
  appendQueryParam(params, 'sort_by', query.sortField);
  appendQueryParam(
    params,
    'sort_order',
    query.sortOrder === 'ascend' ? 'asc' : query.sortOrder === 'descend' ? 'desc' : undefined,
  );
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'write_target', query.writeTarget);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const response = await apiRequest<ListResponse<ResultWriteRecord>>(`/api/system/result-write-records${suffix}`, { token });
  return response.items;
}

export async function createPlugin(payload: Partial<PluginRecord>) {
  const token = requireAccessToken();
  return apiRequest<PluginRecord>('/api/system/plugins', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function copyPlugin(pluginId: string, payload: Partial<PluginRecord>) {
  const token = requireAccessToken();
  return apiRequest<PluginRecord>(`/api/system/plugins/${pluginId}/copy`, {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updatePlugin(pluginId: string, payload: Partial<PluginRecord>) {
  const token = requireAccessToken();
  return apiRequest<PluginRecord>(`/api/system/plugins/${pluginId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deletePlugin(pluginId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/system/plugins/${pluginId}`, {
    method: 'DELETE',
    token,
  });
}

export async function fetchPluginConnections(
  query: { environment?: string; pluginId?: string; status?: string } = {},
): Promise<PluginConnectionRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'environment', query.environment);
  appendQueryParam(params, 'plugin_id', query.pluginId);
  appendQueryParam(params, 'status', query.status);
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<PluginConnectionRecord>>(
    queryString ? `/api/system/plugin-connections?${queryString}` : '/api/system/plugin-connections',
    { token },
  );
  return response.items;
}

export async function fetchPluginConnectionsPage(
  query: PluginConnectionListQuery,
): Promise<RemoteListResult<PluginConnectionRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'environment', query.environment);
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'plugin_id', query.pluginId);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const response = await apiRequest<ListResponse<PluginConnectionRecord>>(
    `/api/system/plugin-connections?${params.toString()}`,
    { token },
  );
  return {
    page: response.page ?? query.page ?? 1,
    pageSize: response.page_size ?? query.pageSize ?? 10,
    performance: response.performance,
    rows: response.items,
    total: response.total,
  };
}

export async function createPluginConnection(payload: Partial<PluginConnectionRecord>) {
  const token = requireAccessToken();
  return apiRequest<PluginConnectionRecord>('/api/system/plugin-connections', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updatePluginConnection(
  connectionId: string,
  payload: Partial<PluginConnectionRecord>,
) {
  const token = requireAccessToken();
  return apiRequest<PluginConnectionRecord>(`/api/system/plugin-connections/${connectionId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deletePluginConnection(connectionId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/system/plugin-connections/${connectionId}`, {
    method: 'DELETE',
    token,
  });
}

export async function testPluginConnection(connectionId: string) {
  const token = requireAccessToken();
  return apiRequest<PluginConnectionTestResult>(`/api/system/plugin-connections/${connectionId}/test`, {
    method: 'POST',
    token,
  });
}

export async function fetchPluginSystemVariables(timezone = 'Asia/Shanghai') {
  const token = requireAccessToken();
  const params = new URLSearchParams({ timezone });
  const response = await apiRequest<{ items: PluginSystemVariableRecord[]; timezone: string }>(
    `/api/system/plugin-system-variables?${params.toString()}`,
    { token },
  );
  return response;
}

export async function fetchPluginActions(
  query: { pluginId?: string; status?: string } = {},
): Promise<PluginActionRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'plugin_id', query.pluginId);
  appendQueryParam(params, 'status', query.status);
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<PluginActionRecord>>(
    queryString ? `/api/system/plugin-actions?${queryString}` : '/api/system/plugin-actions',
    { token },
  );
  return response.items;
}

export async function fetchPluginActionsPage(
  query: PluginActionListQuery,
): Promise<RemoteListResult<PluginActionRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'plugin_id', query.pluginId);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const response = await apiRequest<ListResponse<PluginActionRecord>>(
    `/api/system/plugin-actions?${params.toString()}`,
    { token },
  );
  return {
    page: response.page ?? query.page ?? 1,
    pageSize: response.page_size ?? query.pageSize ?? 10,
    performance: response.performance,
    rows: response.items,
    total: response.total,
  };
}

export async function createPluginAction(payload: Partial<PluginActionRecord>) {
  const token = requireAccessToken();
  return apiRequest<PluginActionRecord>('/api/system/plugin-actions', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updatePluginAction(actionId: string, payload: Partial<PluginActionRecord>) {
  const token = requireAccessToken();
  return apiRequest<PluginActionRecord>(`/api/system/plugin-actions/${actionId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deletePluginAction(actionId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/system/plugin-actions/${actionId}`, {
    method: 'DELETE',
    token,
  });
}

export async function invokePluginAction(actionId: string, inputPayload: Record<string, unknown> = {}) {
  const token = requireAccessToken();
  return apiRequest<PluginInvocationLogRecord>(`/api/system/plugin-actions/${actionId}/invoke`, {
    body: { input_payload: inputPayload, trigger_type: 'manual' },
    method: 'POST',
    token,
  });
}

export async function trialPluginAction(
  actionId: string,
  payload: { connection_id?: string | null; input_payload?: Record<string, unknown> } = {},
) {
  const token = requireAccessToken();
  return apiRequest<PluginActionTrialResult>(`/api/system/plugin-actions/${actionId}/trial`, {
    body: {
      connection_id: payload.connection_id,
      input_payload: payload.input_payload ?? {},
    },
    method: 'POST',
    token,
  });
}

export async function fetchPluginInvocationLogs(
  query: { actionId?: string; scheduledJobId?: string; status?: string } = {},
): Promise<PluginInvocationLogRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'action_id', query.actionId);
  appendQueryParam(params, 'scheduled_job_id', query.scheduledJobId);
  appendQueryParam(params, 'status', query.status);
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<PluginInvocationLogRecord>>(
    queryString ? `/api/system/plugin-invocation-logs?${queryString}` : '/api/system/plugin-invocation-logs',
    { token },
  );
  return response.items;
}

export async function fetchAiSkills(): Promise<AiSkillRecord[]>;
export async function fetchAiSkills(
  query: AiSkillListQuery,
): Promise<RemoteListResult<AiSkillRecord>>;
export async function fetchAiSkills(
  query?: AiSkillListQuery,
): Promise<AiSkillRecord[] | RemoteListResult<AiSkillRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  if (query) {
    appendQueryParam(params, 'code', query.code);
    appendQueryParam(params, 'keyword', query.keyword);
    appendQueryParam(params, 'requires_human_review', query.requiresHumanReview);
    appendQueryParam(params, 'risk_level', query.riskLevel);
    appendQueryParam(params, 'source_type', query.sourceType);
    appendQueryParam(params, 'status', query.status);
    appendRemoteListParams(params, query);
  }
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<AiSkillRecord>>(
    queryString ? `/api/system/ai-skills?${queryString}` : '/api/system/ai-skills',
    {
      token,
    },
  );
  if (query) {
    return {
      page: response.page ?? query.page ?? 1,
      pageSize: response.page_size ?? query.pageSize ?? 10,
      performance: response.performance,
      rows: response.items,
      total: response.total,
    };
  }
  return response.items;
}

export async function createAiSkill(payload: Partial<AiSkillRecord>) {
  const token = requireAccessToken();
  return apiRequest<AiSkillRecord>('/api/system/ai-skills', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function uploadAiSkillPackage(
  file: File,
  options: AiSkillPackageUploadOptions,
) {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'code', options.code);
  appendQueryParam(params, 'name', options.name);
  appendQueryParam(params, 'version', options.version ?? '1.0.0');
  appendQueryParam(params, 'status', options.status ?? 'active');
  appendQueryParam(params, 'risk_level', options.riskLevel ?? 'medium');
  appendQueryParam(
    params,
    'requires_human_review',
    options.requiresHumanReview ? 'true' : 'false',
  );
  const response = await fetch(`${API_BASE_URL}/api/system/ai-skills/upload?${params}`, {
    body: await readUploadFileBytes(file),
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/zip',
    },
    method: 'POST',
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
  const payload = (await response.json()) as ApiEnvelope<AiSkillRecord>;
  return payload.data;
}

export async function updateAiSkill(skillId: string, payload: Partial<AiSkillRecord>) {
  const token = requireAccessToken();
  return apiRequest<AiSkillRecord>(`/api/system/ai-skills/${skillId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function fetchAiAgents(): Promise<AiAgentRecord[]>;
export async function fetchAiAgents(
  query: AiAgentListQuery,
): Promise<RemoteListResult<AiAgentRecord>>;
export async function fetchAiAgents(
  query?: AiAgentListQuery,
): Promise<AiAgentRecord[] | RemoteListResult<AiAgentRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  if (query) {
    appendQueryParam(params, 'brain_app_id', query.brainAppId);
    appendQueryParam(params, 'keyword', query.keyword);
    appendQueryParam(params, 'model_gateway_config_id', query.modelGatewayConfigId);
    appendQueryParam(params, 'status', query.status);
    appendRemoteListParams(params, query);
  }
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<AiAgentRecord>>(
    queryString ? `/api/system/ai-agents?${queryString}` : '/api/system/ai-agents',
    {
      token,
    },
  );
  if (query) {
    return {
      page: response.page ?? query.page ?? 1,
      pageSize: response.page_size ?? query.pageSize ?? 10,
      performance: response.performance,
      rows: response.items,
      total: response.total,
    };
  }
  return response.items;
}

export async function createAiAgent(payload: Partial<AiAgentRecord>) {
  const token = requireAccessToken();
  return apiRequest<AiAgentRecord>('/api/system/ai-agents', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateAiAgent(agentId: string, payload: Partial<AiAgentRecord>) {
  const token = requireAccessToken();
  return apiRequest<AiAgentRecord>(`/api/system/ai-agents/${agentId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function fetchScheduledJobs(): Promise<ScheduledJobRecord[]>;
export async function fetchScheduledJobs(
  query: ScheduledJobListQuery,
): Promise<RemoteListResult<ScheduledJobRecord>>;
export async function fetchScheduledJobs(
  query?: ScheduledJobListQuery,
): Promise<ScheduledJobRecord[] | RemoteListResult<ScheduledJobRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  if (query) {
    appendQueryParam(params, 'enabled', query.enabled);
    appendQueryParam(params, 'job_type', query.jobType);
    appendQueryParam(params, 'keyword', query.keyword);
    appendQueryParam(params, 'name', query.name);
    appendQueryParam(params, 'product_id', query.productId);
    appendQueryParam(params, 'source_system', query.sourceSystem);
    appendQueryParam(params, 'status', query.status);
    appendRemoteListParams(params, query);
  }
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<ScheduledJobRecord>>(
    queryString ? `/api/system/scheduled-jobs?${queryString}` : '/api/system/scheduled-jobs',
    {
      token,
    },
  );
  if (query) {
    return {
      page: response.page ?? query.page ?? 1,
      pageSize: response.page_size ?? query.pageSize ?? 10,
      performance: response.performance,
      rows: response.items,
      total: response.total,
    };
  }
  return response.items;
}

export async function fetchScheduledJobTemplates(): Promise<ScheduledJobTemplateRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<ScheduledJobTemplateRecord>>(
    '/api/system/scheduled-job-templates',
    { token },
  );
  return response.items;
}

export async function fetchScheduledJobCatalog(): Promise<ScheduledJobCatalogRecord> {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobCatalogRecord>('/api/system/scheduled-job-catalog', { token });
}

export async function generateScheduledJobTemplateFromRun(runId: string): Promise<ScheduledJobTemplateRecord> {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobTemplateRecord>(`/api/system/scheduled-job-runs/${runId}/template`, {
    method: 'POST',
    token,
  });
}

export async function createScheduledJob(payload: Partial<ScheduledJobRecord>) {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobRecord>('/api/system/scheduled-jobs', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function dryRunScheduledJob(payload: Partial<ScheduledJobRecord>) {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobDryRunResult>('/api/system/scheduled-jobs/dry-run', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateScheduledJob(jobId: string, payload: Partial<ScheduledJobRecord>) {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobRecord>(`/api/system/scheduled-jobs/${jobId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteScheduledJob(jobId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/system/scheduled-jobs/${jobId}`, {
    method: 'DELETE',
    token,
  });
}

export async function runScheduledJob(
  jobId: string,
  triggerType: 'manual' | 'manual_rerun' = 'manual',
  sourceRunId?: string,
) {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobRunRecord>(`/api/system/scheduled-jobs/${jobId}/run`, {
    body: { source_run_id: sourceRunId, trigger_type: triggerType },
    method: 'POST',
    token,
  });
}

export async function fetchScheduledJobRuns(): Promise<ScheduledJobRunRecord[]>;
export async function fetchScheduledJobRuns(
  query: ScheduledJobRunListQuery,
): Promise<RemoteListResult<ScheduledJobRunRecord>>;
export async function fetchScheduledJobRuns(
  query: ScheduledJobRunFilterQuery,
): Promise<ScheduledJobRunRecord[]>;
export async function fetchScheduledJobRuns(
  query: ScheduledJobRunFilterQuery | ScheduledJobRunListQuery = {},
): Promise<ScheduledJobRunRecord[] | RemoteListResult<ScheduledJobRunRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  query.runIds?.forEach((runId) => {
    if (runId) {
      params.append('run_id', runId);
    }
  });
  appendQueryParam(params, 'scheduled_job_id', query.scheduledJobId);
  appendQueryParam(params, 'status', query.status);
  const remoteListRequested =
    query.page !== undefined
    || query.pageSize !== undefined
    || query.sortField !== undefined
    || query.sortOrder !== undefined;
  if (remoteListRequested) {
    appendRemoteListParams(params, query);
  }
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<ScheduledJobRunRecord>>(
    queryString ? `/api/system/scheduled-job-runs?${queryString}` : '/api/system/scheduled-job-runs',
    { token },
  );
  if (remoteListRequested) {
    return {
      page: response.page ?? query.page ?? 1,
      pageSize: response.page_size ?? query.pageSize ?? 10,
      performance: response.performance,
      rows: response.items,
      total: response.total,
    };
  }
  return response.items;
}

export async function fetchScheduledJobRunObservability(): Promise<ScheduledJobRunObservability> {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobRunObservability>('/api/system/scheduled-job-runs/observability', {
    token,
  });
}

export type CodeInspectionReportRecord = {
  artifact_ref?: string | null;
  branch?: string | null;
  checkout_path?: string | null;
  checkout_path_retained?: boolean;
  commit_sha?: string | null;
  committer_count?: number;
  committer_summary?: Array<{
    bug_count?: number;
    email?: string | null;
    finding_count?: number;
    name?: string | null;
    severe_finding_count?: number;
    username?: string | null;
  }>;
  created_at?: string;
  created_bug_ids?: string[];
  created_task_ids?: string[];
  finding_count: number;
  id: string;
  notification_ids?: string[];
  plugin_action_id?: string | null;
  plugin_connection_id?: string | null;
  plugin_invocation_log_id?: string | null;
  previous_comparison?: Record<string, unknown>;
  previous_report_id?: string | null;
  product_id?: string | null;
  quality_gate?: Record<string, unknown>;
  repository_id?: string | null;
  repository_name?: string | null;
  repository_path?: string | null;
  remote_url_hash?: string | null;
  remote_url_summary?: string | null;
  risk_level: string;
  rules_loaded?: string[];
  rules_version?: string | null;
  scan_finished_at?: string | null;
  scan_mode?: string | null;
  scan_started_at?: string | null;
  scanner_name?: string | null;
  scanner_version?: string | null;
  scan_profile?: Record<string, unknown>;
  scheduled_job_id?: string | null;
  scheduled_job_run_id?: string | null;
  severe_finding_count: number;
  source_system?: string | null;
  status: string;
  summary?: string;
  suppressed_finding_count?: number;
  suppression_summary?: Record<string, unknown>;
};

export type CodeInspectionFindingRecord = {
  category?: string;
  committer_email?: string | null;
  committer_name?: string | null;
  committer_username?: string | null;
  created_bug_id?: string | null;
  created_task_id?: string | null;
  description?: string;
  file_path?: string;
  id: string;
  line_number?: number | null;
  recommendation?: string;
  report_id: string;
  rule_id?: string;
  severity: string;
  suppression_note?: string | null;
  suppression_reason?: string | null;
  suppression_requested_at?: string | null;
  suppression_requested_by?: string | null;
  suppression_reviewed_at?: string | null;
  suppression_reviewed_by?: string | null;
  suppression_status?: 'approved' | 'none' | 'pending' | 'rejected' | string;
  title: string;
};

export type CodeInspectionNotificationRecord = {
  channel: string;
  created_at?: string;
  id: string;
  message?: string;
  report_id: string;
  status: string;
  target?: string | null;
};

export type CodeInspectionDetailRecord = {
  findings: CodeInspectionFindingRecord[];
  governance_summary?: {
    accepted_risk_count?: number;
    action_items?: Array<{ code?: string; count?: number; label?: string }>;
    active_severe_finding_count?: number;
    bug_coverage_rate?: number;
    covered_by_bug_count?: number;
    covered_by_task_count?: number;
    pending_suppression_count?: number;
    severe_threshold?: string;
    status?: 'action_required' | 'healthy' | 'pending_review' | string;
    suppressed_finding_count?: number;
    task_coverage_rate?: number;
    uncovered_bug_finding_count?: number;
    uncovered_task_finding_count?: number;
  };
  notifications: CodeInspectionNotificationRecord[];
  report: CodeInspectionReportRecord & Record<string, unknown>;
  scan_summary?: {
    committer_distribution?: Array<Record<string, unknown>>;
    coverage?: Record<string, unknown>;
    file_distribution?: Array<Record<string, unknown>>;
    previous_comparison?: Record<string, unknown>;
    quality_gate?: Record<string, unknown>;
    rule_distribution?: Array<Record<string, unknown>>;
    scan_profile?: Record<string, unknown>;
    suppression_summary?: Record<string, unknown>;
  };
};

export type CodeInspectionDashboardRecord = {
  branch_ranking: Array<{
    branch?: string | null;
    finding_count: number;
    report_count: number;
    repository_id?: string | null;
    repository_name?: string | null;
    severe_finding_count: number;
  }>;
  category_distribution: Array<{ category: string; count: number }>;
  committer_ranking: Array<{
    bug_count: number;
    email?: string | null;
    finding_count: number;
    name?: string | null;
    severe_finding_count: number;
    username?: string | null;
  }>;
  repository_ranking: Array<{
    branch_count: number;
    finding_count: number;
    report_count: number;
    repository_id?: string | null;
    repository_name?: string | null;
    repository_path?: string | null;
    risk_level: string;
    severe_finding_count: number;
  }>;
  risk_distribution: Array<{ count: number; risk_level: string }>;
  rule_distribution: Array<{
    category?: string;
    finding_count: number;
    rule_id: string;
    severity: string;
    severe_finding_count: number;
  }>;
  rule_governance?: {
    latest_report_rules_version?: string | null;
    latest_report_scanner_version?: string | null;
    mixed_rules_version?: boolean;
    mixed_scanner_version?: boolean;
    report_with_suppression_count?: number;
    rule_version_distribution?: Array<{ count: number; rules_version: string }>;
    scanner_version_distribution?: Array<{ count: number; scanner_version: string }>;
    suppressed_finding_count?: number;
    suppression_distribution?: Array<{ count: number; reason: string }>;
  };
  quality_gate_violations?: Array<{
    actual?: number | string | null;
    latest_report_id?: string | null;
    latest_report_summary?: string | null;
    limit?: number | string | null;
    metric: string;
    report_count: number;
    severity: string;
    violation_count: number;
  }>;
  severity_distribution: Array<{ count: number; severity: string }>;
  sla: {
    bug_coverage_rate: number;
    covered_by_bug_count: number;
    covered_by_task_count: number;
    oldest_uncovered_at?: string | null;
    oldest_without_task_at?: string | null;
    severe_finding_count: number;
    severe_threshold: string;
    status: 'at_risk' | 'healthy' | string;
    task_coverage_rate: number;
    uncovered_severe_finding_count: number;
    uncovered_task_finding_count: number;
  };
  summary: {
    bug_created_count: number;
    critical_finding_count: number;
    failed_report_count: number;
    finding_count: number;
    high_finding_count: number;
    repository_count: number;
    report_count: number;
    severe_finding_count: number;
  };
  trend: Array<{
    bug_count: number;
    date: string;
    finding_count: number;
    quality_gate_failed_count: number;
    quality_gate_passed_count: number;
    quality_gate_skipped_count: number;
    quality_gate_unknown_count: number;
    report_count: number;
    severe_finding_count: number;
  }>;
};

export type CodeInspectionListQuery = {
  committer?: string;
  page?: number;
  pageSize?: number;
  productId?: string;
  repositoryId?: string;
  riskLevel?: string;
  sortField?: string;
  sortOrder?: 'ascend' | 'descend';
  status?: string;
  title?: string;
};

function appendCodeInspectionQuery(params: URLSearchParams, query: CodeInspectionListQuery = {}) {
  appendQueryParam(params, 'committer', query.committer);
  appendQueryParam(params, 'product_id', query.productId);
  appendQueryParam(params, 'repository_id', query.repositoryId);
  appendQueryParam(params, 'risk_level', query.riskLevel);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'title', query.title);
}

export async function fetchCodeInspectionReports(
  query: CodeInspectionListQuery = {},
): Promise<RemoteListResult<CodeInspectionReportRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'page', query.page ?? 1);
  appendQueryParam(params, 'page_size', query.pageSize ?? 10);
  appendCodeInspectionQuery(params, query);
  appendQueryParam(params, 'sort_by', query.sortField);
  appendQueryParam(params, 'sort_order', query.sortOrder === 'ascend' ? 'asc' : 'desc');
  const response = await apiRequest<ListResponse<CodeInspectionReportRecord>>(
    `/api/governance/code-inspections?${params.toString()}`,
    { token },
  );
  return {
    page: response.page ?? query.page ?? 1,
    pageSize: response.page_size ?? query.pageSize ?? 10,
    rows: response.items,
    total: response.total,
  };
}

export async function fetchCodeInspectionDashboard(query: CodeInspectionListQuery = {}) {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendCodeInspectionQuery(params, query);
  const queryString = params.toString();
  return apiRequest<CodeInspectionDashboardRecord>(
    queryString
      ? `/api/governance/code-inspections/dashboard?${queryString}`
      : '/api/governance/code-inspections/dashboard',
    { token },
  );
}

export async function fetchCodeInspectionDetail(reportId: string): Promise<CodeInspectionDetailRecord> {
  const token = requireAccessToken();
  return apiRequest<CodeInspectionDetailRecord>(`/api/governance/code-inspections/${reportId}`, {
    token,
  });
}

export async function requestCodeInspectionFindingSuppression(
  reportId: string,
  findingId: string,
  payload: { note?: string; reason?: string } = {},
): Promise<CodeInspectionDetailRecord> {
  const token = requireAccessToken();
  return apiRequest<CodeInspectionDetailRecord>(
    `/api/governance/code-inspections/${reportId}/findings/${findingId}/suppression-request`,
    {
      body: JSON.stringify({
        note: payload.note,
        reason: payload.reason ?? 'false_positive',
      }),
      method: 'POST',
      token,
    },
  );
}

export async function reviewCodeInspectionFindingSuppression(
  reportId: string,
  findingId: string,
  payload: { decision: 'approve' | 'reject'; note?: string },
): Promise<CodeInspectionDetailRecord> {
  const token = requireAccessToken();
  return apiRequest<CodeInspectionDetailRecord>(
    `/api/governance/code-inspections/${reportId}/findings/${findingId}/suppression-review`,
    {
      body: JSON.stringify(payload),
      method: 'POST',
      token,
    },
  );
}

function mapRequirementRecord(requirement: RequirementListItem): RequirementRecord {
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

function mapTaskRecord(task: TaskListItem): TaskCenterTaskRecord {
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

function mapRequirementFullChain(
  chain: RequirementFullChainResponse,
): RequirementFullChainRecord {
  const summary = chain.summary ?? {};
  return {
    aiTasks: (chain.ai_tasks ?? []).map(mapTaskRecord),
    anchor: chain.anchor
      ? {
          resolvedRequirementId: chain.anchor.resolved_requirement_id,
          subjectId: chain.anchor.subject_id,
          subjectType: chain.anchor.subject_type,
        }
      : undefined,
    bugs: (chain.bugs ?? []).map(mapBugRecord),
    auditEvents: (chain.audit_events ?? []).map((event) => ({
      actorId: emptyToUndefined(formatUnknownValue(event.actor_id)),
      aiTaskId: emptyToUndefined(formatUnknownValue(event.ai_task_id)),
      createdAt: formatListDate(formatUnknownValue(event.created_at)),
      eventType: formatUnknownValue(event.event_type),
      id: formatUnknownValue(event.id),
      subjectId: emptyToUndefined(formatUnknownValue(event.subject_id)),
      subjectType: emptyToUndefined(formatUnknownValue(event.subject_type)),
    })),
    branchConfigs: (chain.branch_configs ?? []).map(mapProductVersionBranchConfigRecord),
    codeInspectionReports: chain.code_inspection_reports ?? [],
    codeReviewReports: (chain.code_review_reports ?? []).map((report) => ({
      executor: report.executor,
      findings: report.findings ?? [],
      gitlabWritebackPerformed: report.gitlab_writeback_performed ?? false,
      id: report.id,
      riskLevel: report.risk_level ?? '-',
      status: report.status ?? '-',
      summary: report.summary ?? report.id,
    })),
    executionTraces: chain.execution_traces ?? [],
    gitSnapshots: (chain.git_snapshots ?? []).map((snapshot) => ({
      changedFilesSummary: snapshot.changed_files_summary ?? [],
      createdAt: formatListDate(snapshot.created_at),
      diffLimitBytes: snapshot.diff_limit_bytes,
      diffFileTree: normalizeDiffFileTree(snapshot.diff_file_tree),
      diffSizeBytes: snapshot.diff_size_bytes,
      id: snapshot.id,
      mrIid: snapshot.mr_iid,
      reviewChecklist: snapshot.review_checklist ?? [],
      repositoryId: snapshot.repository_id,
      riskSummary: normalizeRiskSummary(snapshot.risk_summary),
    })),
    iterationVersion: chain.iteration_version
      ? {
          code: chain.iteration_version.code,
          id: chain.iteration_version.id,
          name: chain.iteration_version.name,
          status: chain.iteration_version.status,
        }
      : undefined,
    jenkinsReleases: (chain.jenkins_releases ?? []).map((release) => ({
      buildId: formatUnknownValue(release.build_id),
      createdAt: formatListDate(formatUnknownValue(release.deployed_at ?? release.started_at ?? release.created_at)),
      id: formatUnknownValue(release.id),
      jobName: formatUnknownValue(release.job_name),
      status: formatUnknownValue(release.status),
    })),
    knowledgeDeposits: (chain.knowledge_deposits ?? []).map(mapKnowledgeDeposit),
    product: chain.product
      ? {
          code: chain.product.code,
          id: chain.product.id,
          name: chain.product.name,
        }
      : undefined,
    requirement: mapRequirementRecord(chain.requirement),
    reviews: (chain.reviews ?? []).map((review) => ({
      aiTaskId: review.ai_task_id,
      createdAt: formatListDate(formatUnknownValue(review.created_at)),
      id: review.id,
      status: review.status ?? '-',
    })),
    status: chain.status ?? 'available',
    summary: {
      aiTasks: normalizeDashboardCount(summary.ai_tasks),
      auditEvents: normalizeDashboardCount(summary.audit_events),
      branchConfigs: normalizeDashboardCount(summary.branch_configs),
      bugs: normalizeDashboardCount(summary.bugs),
      codeInspectionReports: normalizeDashboardCount(summary.code_inspection_reports),
      codeReviewReports: normalizeDashboardCount(summary.code_review_reports),
      executionTraces: normalizeDashboardCount(summary.execution_traces),
      gitSnapshots: normalizeDashboardCount(summary.git_snapshots),
      jenkinsReleases: normalizeDashboardCount(summary.jenkins_releases),
      knowledgeDeposits: normalizeDashboardCount(summary.knowledge_deposits),
      reviews: normalizeDashboardCount(summary.reviews),
      timelineEvents: normalizeDashboardCount(summary.timeline_events),
    },
    timeline: (chain.timeline ?? []).map((item) => ({
      occurredAt: formatListDate(item.occurred_at),
      occurredAtValue: item.occurred_at,
      status: item.status ?? undefined,
      subjectId: item.subject_id ?? '-',
      title: item.title ?? item.subject_id ?? '-',
      type: item.type ?? '-',
    })),
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

export async function fetchRequirementFullChain(
  requirementId: string,
): Promise<RequirementFullChainRecord> {
  const token = requireAccessToken();
  const chain = await apiRequest<RequirementFullChainResponse>(
    `/api/requirements/${requirementId}/full-chain`,
    { token },
  );

  return mapRequirementFullChain(chain);
}

export async function fetchLifecycleFullChain(
  subjectType: string,
  subjectId: string,
): Promise<RequirementFullChainRecord> {
  const token = requireAccessToken();
  const params = new URLSearchParams({
    subject_id: subjectId,
    subject_type: subjectType,
  });
  const chain = await apiRequest<RequirementFullChainResponse>(
    `/api/lifecycle/full-chain?${params.toString()}`,
    { token },
  );

  return mapRequirementFullChain(chain);
}

export function fullChainSubjectHref(subjectType: string, subjectId: string) {
  const params = new URLSearchParams({
    subject_id: subjectId,
    subject_type: subjectType,
  });
  return `/delivery/full-chain?${params.toString()}`;
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

export async function fetchManagementKnowledge(): Promise<KnowledgeRecord[]> {
  const token = requireAccessToken();
  const documents = await apiRequest<ListResponse<KnowledgeDocumentListItem>>(
    '/api/knowledge/documents',
    { token },
  );

  return documents.items.map(mapKnowledgeRecord);
}

function mapKnowledgeRecord(document: KnowledgeDocumentListItem): KnowledgeRecord {
  return {
    activeChunkSetId: document.active_chunk_set_id ?? undefined,
    content: document.content,
    documentType: document.doc_type ?? '-',
    folderId: document.folder_id ?? undefined,
    folderPath: document.folder_path ?? undefined,
    id: document.id,
    indexError: document.index_error,
    knowledgeSpaceId: document.knowledge_space_id ?? undefined,
    ownerRole: document.permission_roles?.join(', ') || '-',
    permissionRoles: document.permission_roles,
    sourceAssetId: document.source_asset_id ?? undefined,
    status: normalizeKnowledgeStatus(document.index_status),
    tags: document.tags,
    title: document.title,
    updatedAt: formatListDate(document.updated_at ?? document.created_at),
    vectorIndexError: document.vector_index_error,
  };
}

export async function fetchManagementKnowledgeList(
  query: KnowledgeListQuery = {},
): Promise<RemoteListResult<KnowledgeRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'doc_type', query.documentType);
  appendQueryParam(params, 'knowledge_space_id', query.knowledgeSpaceId);
  appendQueryParam(params, 'folder_id', query.folderId);
  appendQueryParam(params, 'permission_role', query.ownerRole);
  appendQueryParam(params, 'index_status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const documents = await apiRequest<ListResponse<KnowledgeDocumentListItem>>(
    queryString ? `/api/knowledge/documents?${queryString}` : '/api/knowledge/documents',
    { token },
  );

  return {
    page: documents.page ?? query.page ?? 1,
    pageSize: documents.page_size ?? query.pageSize ?? 10,
    performance: documents.performance,
    rows: documents.items.map(mapKnowledgeRecord),
    total: documents.total,
  };
}

function mapKnowledgeSpace(item: KnowledgeSpaceListItem): KnowledgeSpaceRecord {
  return {
    code: item.code,
    description: item.description,
    id: item.id,
    name: item.name,
  };
}

function mapKnowledgeFolder(item: KnowledgeFolderListItem): KnowledgeFolderRecord {
  return {
    id: item.id,
    knowledgeSpaceId: item.knowledge_space_id,
    name: item.name,
    parentFolderId: item.parent_folder_id,
    path: item.path ?? item.name,
  };
}

function mapKnowledgeAsset(item: KnowledgeAssetListItem): KnowledgeAssetRecord {
  return {
    assetType: item.asset_type ?? '-',
    filename: item.filename ?? item.id,
    id: item.id,
    mimeType: item.mime_type,
    sizeBytes: Number(item.size_bytes ?? 0),
    storageProvider: item.storage_provider,
  };
}

function mapKnowledgeImportJob(item: KnowledgeImportJobListItem): KnowledgeImportJobRecord {
  return {
    assetFilename: item.asset_filename,
    chunkStrategy: item.chunk_strategy,
    documentId: item.document_id,
    documentTitle: item.document_title,
    errorMessage: item.error_message ?? undefined,
    folderPath: item.folder_path,
    id: item.id,
    parserEngine: item.parser_engine,
    progress: Number(item.progress ?? 0),
    status: item.status ?? '-',
    updatedAt: formatListDate(item.updated_at),
  };
}

function mapKnowledgeChunkSet(item: KnowledgeChunkSetListItem): KnowledgeChunkSetRecord {
  return {
    activatedAt: formatListDate(item.activated_at),
    chunkCount: Number(item.chunk_count ?? 0),
    chunkStrategy: item.chunk_strategy ?? '-',
    id: item.id,
    isActive: Boolean(item.is_active),
    parserEngine: item.parser_engine ?? '-',
    status: item.status ?? '-',
  };
}

function mapKnowledgeChunk(item: KnowledgeChunkListItem): KnowledgeChunkRecord {
  return {
    chunkIndex: Number(item.chunk_index ?? 0),
    chunkRole: item.metadata?.chunk_role,
    chunkSetId: item.chunk_set_id,
    content: item.content ?? '',
    heading: item.metadata?.heading,
    id: item.id,
    imageCount: item.metadata?.image_count,
    imageRefs: item.metadata?.image_refs,
    parentChunkId: item.parent_chunk_id,
    parentContent: item.parent_content,
    pageNumber: item.metadata?.page_number,
    sectionTitle: item.metadata?.section_title,
    sourceAssetType: item.metadata?.source_asset_type,
    sourceKind: item.metadata?.source_kind,
    splitPattern: item.metadata?.split_pattern,
    tableColumns: item.metadata?.columns,
    tableCount: item.metadata?.table_count,
    tableIndex: item.metadata?.table_index,
  };
}

function mapKnowledgeImportWorkerStatus(
  item: KnowledgeImportWorkerStatusItem,
): KnowledgeImportWorkerStatusRecord {
  return {
    activeJobId: item.active_job_id ?? null,
    enabled: Boolean(item.enabled),
    failedCount: Number(item.failed_count ?? 0),
    pendingCount: Number(item.pending_count ?? 0),
    processedCount: Number(item.processed_count ?? 0),
    queuedJobIds: item.queued_job_ids ?? [],
    running: Boolean(item.running),
    workerId: item.worker_id ?? null,
  };
}

export async function fetchKnowledgeSpaces(): Promise<KnowledgeSpaceRecord[]> {
  const token = requireAccessToken();
  const spaces = await apiRequest<ListResponse<KnowledgeSpaceListItem>>('/api/knowledge/spaces', {
    token,
  });
  return spaces.items.map(mapKnowledgeSpace);
}

export async function createKnowledgeSpace(payload: {
  code: string;
  description?: string;
  name: string;
}): Promise<KnowledgeSpaceRecord> {
  const token = requireAccessToken();
  const space = await apiRequest<KnowledgeSpaceListItem>('/api/knowledge/spaces', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapKnowledgeSpace(space);
}

export async function fetchKnowledgeFolders(spaceId: string): Promise<KnowledgeFolderRecord[]> {
  const token = requireAccessToken();
  const folders = await apiRequest<ListResponse<KnowledgeFolderListItem>>(
    `/api/knowledge/spaces/${spaceId}/folders`,
    { token },
  );
  return folders.items.map(mapKnowledgeFolder);
}

export async function createKnowledgeFolder(
  spaceId: string,
  payload: { name: string; parent_folder_id?: string },
): Promise<KnowledgeFolderRecord> {
  const token = requireAccessToken();
  const folder = await apiRequest<KnowledgeFolderListItem>(
    `/api/knowledge/spaces/${spaceId}/folders`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return mapKnowledgeFolder(folder);
}

export async function updateKnowledgeFolder(
  folderId: string,
  payload: {
    name?: string;
    parent_folder_id?: string | null;
    sort_order?: number;
    status?: string;
  },
): Promise<KnowledgeFolderRecord> {
  const token = requireAccessToken();
  const folder = await apiRequest<KnowledgeFolderListItem>(`/api/knowledge/folders/${folderId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
  return mapKnowledgeFolder(folder);
}

export async function fetchKnowledgeDocumentAssets(
  documentId: string,
): Promise<KnowledgeAssetRecord[]> {
  const token = requireAccessToken();
  const assets = await apiRequest<ListResponse<KnowledgeAssetListItem>>(
    `/api/knowledge/documents/${documentId}/assets`,
    { token },
  );
  return assets.items.map(mapKnowledgeAsset);
}

export async function fetchKnowledgeImportJobs(params: {
  knowledgeSpaceId?: string;
  status?: string;
} = {}): Promise<KnowledgeImportJobRecord[]> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  appendQueryParam(query, 'knowledge_space_id', params.knowledgeSpaceId);
  appendQueryParam(query, 'status', params.status);
  const queryString = query.toString();
  const importJobs = await apiRequest<ListResponse<KnowledgeImportJobListItem>>(
    queryString ? `/api/knowledge/import-jobs?${queryString}` : '/api/knowledge/import-jobs',
    { token },
  );
  return importJobs.items.map(mapKnowledgeImportJob);
}

export async function fetchKnowledgeImportWorkerStatus(): Promise<KnowledgeImportWorkerStatusRecord> {
  const token = requireAccessToken();
  const status = await apiRequest<KnowledgeImportWorkerStatusItem>(
    '/api/knowledge/import-worker/status',
    { token },
  );
  return mapKnowledgeImportWorkerStatus(status);
}

export async function runKnowledgeImportJob(jobId: string) {
  const token = requireAccessToken();
  return apiRequest<{ import_job: KnowledgeImportJobListItem }>(
    `/api/knowledge/import-jobs/${jobId}/run`,
    { method: 'POST', token },
  );
}

export async function retryKnowledgeImportJob(jobId: string) {
  const token = requireAccessToken();
  return apiRequest<{ import_job: KnowledgeImportJobListItem }>(
    `/api/knowledge/import-jobs/${jobId}/retry`,
    { method: 'POST', token },
  );
}

export async function cancelKnowledgeImportJob(jobId: string) {
  const token = requireAccessToken();
  return apiRequest<{ import_job: KnowledgeImportJobListItem }>(
    `/api/knowledge/import-jobs/${jobId}/cancel`,
    { method: 'POST', token },
  );
}

export async function fetchKnowledgeChunkSets(documentId: string): Promise<KnowledgeChunkSetRecord[]> {
  const token = requireAccessToken();
  const chunkSets = await apiRequest<ListResponse<KnowledgeChunkSetListItem>>(
    `/api/knowledge/documents/${documentId}/chunk-sets`,
    { token },
  );
  return chunkSets.items.map(mapKnowledgeChunkSet);
}

export async function fetchKnowledgeChunks(
  documentId: string,
  chunkSetId?: string,
): Promise<KnowledgeChunkRecord[]> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  appendQueryParam(query, 'chunk_set_id', chunkSetId);
  const queryString = query.toString();
  const chunks = await apiRequest<ListResponse<KnowledgeChunkListItem>>(
    queryString
      ? `/api/knowledge/documents/${documentId}/chunks?${queryString}`
      : `/api/knowledge/documents/${documentId}/chunks`,
    { token },
  );
  return chunks.items.map(mapKnowledgeChunk);
}

export async function activateKnowledgeChunkSet(documentId: string, chunkSetId: string) {
  const token = requireAccessToken();
  return apiRequest<{ document: KnowledgeDocumentListItem }>(
    `/api/knowledge/documents/${documentId}/chunk-sets/${chunkSetId}/activate`,
    { method: 'POST', token },
  );
}

export async function reparseKnowledgeDocument(
  documentId: string,
  payload: { chunk_strategy?: string; parser_engine?: string },
) {
  const token = requireAccessToken();
  return apiRequest<{ import_job: KnowledgeImportJobListItem }>(
    `/api/knowledge/documents/${documentId}/reparse`,
    { body: payload, method: 'POST', token },
  );
}

export async function batchMoveKnowledgeDocuments(documentIds: string[], folderId?: string | null) {
  const token = requireAccessToken();
  return apiRequest<{ skipped: Array<{ id: string; reason: string }>; updated: string[] }>(
    '/api/knowledge/documents/batch-move',
    {
      body: { document_ids: documentIds, folder_id: folderId ?? null },
      method: 'POST',
      token,
    },
  );
}

export async function uploadKnowledgeDocument(payload: KnowledgeDocumentUploadPayload) {
  const token = requireAccessToken();
  return apiRequest<{ document: KnowledgeDocumentListItem }>('/api/knowledge/documents/upload', {
    body: payload,
    method: 'POST',
    token,
  });
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

export async function retryKnowledgeDocumentIndex(documentId: string) {
  const token = requireAccessToken();
  return apiRequest<{ id: string; index_error?: string | null; index_status?: string }>(
    `/api/knowledge/documents/${documentId}/retry-index`,
    {
      method: 'POST',
      token,
    },
  );
}

export async function fetchManagementAudit(): Promise<AuditRecord[]> {
  const token = requireAccessToken();
  const events = await apiRequest<ListResponse<AuditEventListItem>>('/api/audit/events', { token });

  return events.items.map(mapAuditRecord);
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

export async function fetchExecutionTraceDetail(traceId: string): Promise<ExecutionTraceDetailRecord> {
  const token = requireAccessToken();
  return apiRequest<ExecutionTraceDetailRecord>(`/api/governance/execution-traces/${traceId}`, {
    token,
  });
}

function mapLifecycleRelation(item: LifecycleRelationItem): LifecycleRelationRecord {
  return {
    relationType: formatUnknownValue(item.relation_type),
    subjectId: formatUnknownValue(item.subject_id),
    subjectType: formatUnknownValue(item.subject_type),
    summary: formatUnknownValue(item.summary),
  };
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

export async function fetchManagementBugs(): Promise<BugRecord[]> {
  const token = requireAccessToken();
  const bugs = await apiRequest<ListResponse<BugListItem>>('/api/bugs', { token });

  return bugs.items.map((bug) => ({
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
  }));
}

function mapBugRecord(bug: BugListItem): BugRecord {
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

export async function deleteManagementBug(bugId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/bugs/${bugId}`, {
    method: 'DELETE',
    token,
  });
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

function codeReviewTitleFromTechnicalSolutionTask(task: TaskCenterTaskRecord, mrIid: number) {
  const title = task.label.replace(/^技术方案[:：]\s*/, '').trim();
  return `Code Review：${title || task.label} MR !${mrIid}`;
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
    diffFileTree: normalizeDiffFileTree(preview.diff_file_tree),
    mrIid: preview.mr_iid,
    permissionDiagnostics: normalizePermissionDiagnostics(preview.permission_diagnostics),
    reviewChecklist: preview.review_checklist ?? [],
    repositoryId: preview.repository_id,
    riskSummary: normalizeRiskSummary(preview.risk_summary),
    sourceBranch: preview.source_branch,
    targetBranch: preview.target_branch,
    title: preview.title ?? `MR !${preview.mr_iid}`,
    webUrl: preview.web_url,
    writebackAllowed: preview.writeback_allowed ?? false,
  };
}

export async function previewCodeReviewPullRequest(
  repository: ProductGitRepositoryOption,
  mrIid: number,
): Promise<GitLabMergeRequestPreview> {
  if (repository.provider !== 'github') {
    return previewGitLabMergeRequest(repository.id, mrIid);
  }
  const token = requireAccessToken();
  const preview = await apiRequest<GitLabMergeRequestPreviewResponse>(
    `/api/devops/github/pull-requests/${repository.id}/${mrIid}/preview`,
    { token },
  );

  return {
    author: formatGitLabAuthor(preview.author),
    changedFileCount: preview.changed_file_count ?? 0,
    changedFilesSummary: preview.changed_files_summary ?? [],
    diffFileTree: normalizeDiffFileTree(preview.diff_file_tree),
    mrIid: preview.mr_iid,
    permissionDiagnostics: normalizePermissionDiagnostics(preview.permission_diagnostics),
    reviewChecklist: preview.review_checklist ?? [],
    repositoryId: preview.repository_id,
    riskSummary: normalizeRiskSummary(preview.risk_summary),
    sourceBranch: preview.source_branch,
    targetBranch: preview.target_branch,
    title: preview.title ?? `PR #${preview.mr_iid}`,
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
    changedFilesSummary: snapshot.changed_files_summary ?? [],
    createdAt: formatListDate(snapshot.created_at),
    diffChangeSummary: normalizeDiffChangeSummary(snapshot.diff_change_summary),
    diffLimitBytes: snapshot.diff_limit_bytes,
    diffFileTree: normalizeDiffFileTree(snapshot.diff_file_tree),
    diffSizeBytes: snapshot.diff_size_bytes,
    id: snapshot.id,
    mrIid: snapshot.mr_iid,
    previousSnapshot: normalizePreviousSnapshot(snapshot.previous_snapshot),
    reviewChecklist: snapshot.review_checklist ?? [],
    repositoryId: snapshot.repository_id,
    riskSummary: normalizeRiskSummary(snapshot.risk_summary),
    snapshotReused: snapshot.snapshot_reused,
  };
}

export async function snapshotCodeReviewPullRequest({
  mrIid,
  repository,
  requirementId,
  technicalSolutionTaskId,
}: {
  mrIid: number;
  repository: ProductGitRepositoryOption;
  requirementId: string;
  technicalSolutionTaskId: string;
}): Promise<GitLabMergeRequestSnapshot> {
  if (repository.provider !== 'github') {
    return snapshotGitLabMergeRequest({
      mrIid,
      repositoryId: repository.id,
      requirementId,
      technicalSolutionTaskId,
    });
  }
  const token = requireAccessToken();
  const snapshot = await apiRequest<GitLabMergeRequestSnapshotResponse>(
    `/api/devops/github/pull-requests/${repository.id}/${mrIid}/snapshot`,
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
    changedFilesSummary: snapshot.changed_files_summary ?? [],
    createdAt: formatListDate(snapshot.created_at),
    diffChangeSummary: normalizeDiffChangeSummary(snapshot.diff_change_summary),
    diffLimitBytes: snapshot.diff_limit_bytes,
    diffFileTree: normalizeDiffFileTree(snapshot.diff_file_tree),
    diffSizeBytes: snapshot.diff_size_bytes,
    id: snapshot.id,
    mrIid: snapshot.mr_iid,
    previousSnapshot: normalizePreviousSnapshot(snapshot.previous_snapshot),
    reviewChecklist: snapshot.review_checklist ?? [],
    repositoryId: snapshot.repository_id,
    riskSummary: normalizeRiskSummary(snapshot.risk_summary),
    snapshotReused: snapshot.snapshot_reused,
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
    writebackTemplate: report.writeback_template
      ? {
          body: report.writeback_template.body ?? '',
          format: report.writeback_template.format ?? 'markdown',
          title: report.writeback_template.title ?? 'AI Brain Code Review',
          writebackAllowed: report.writeback_template.writeback_allowed ?? false,
          writebackReason: report.writeback_template.writeback_reason ?? '-',
        }
      : undefined,
  };
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

function mapKnowledgeDeposit(deposit: KnowledgeDepositListItem): KnowledgeDepositRecord {
  return {
    aiTaskId: deposit.ai_task_id,
    content: deposit.content ?? '-',
    id: deposit.id,
    knowledgeDocumentId: deposit.knowledge_document_id,
    rejectionReason: deposit.rejection_reason,
    status: deposit.status ?? '-',
    title: deposit.title ?? deposit.id,
  };
}

export async function fetchKnowledgeDeposits(
  status = 'pending',
): Promise<KnowledgeDepositRecord[]> {
  const token = requireAccessToken();
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  const deposits = await apiRequest<ListResponse<KnowledgeDepositListItem>>(
    `/api/knowledge/deposits${query}`,
    { token },
  );
  return deposits.items.map(mapKnowledgeDeposit);
}

function mapKnowledgeSearchResult(item: KnowledgeSearchResultItem, index: number): KnowledgeSearchResultRecord {
  const sourceParts = [
    item.source?.doc_type,
    item.source?.title,
    item.chunk_index ? `chunk ${item.chunk_index}` : undefined,
  ].filter(Boolean);
  return {
    chunkId: item.chunk_id ?? item.source?.chunk_id,
    chunkIndex: item.chunk_index,
    content: item.content ?? '-',
    documentId: item.document_id,
    id: item.chunk_id ?? `${item.document_id}:${index}`,
    parentChunkId: item.source?.parent_chunk_id,
    parentContent: item.source?.parent_content,
    retrievalMode: item.retrieval_mode === 'vector' ? 'vector' : 'keyword',
    sourceLabel: sourceParts.length ? sourceParts.join(' · ') : '-',
    title: item.title ?? item.document_id,
  };
}

export async function fetchKnowledgeSearchResults(
  query: string,
  topK = 5,
  knowledgeSpaceId?: string,
): Promise<KnowledgeSearchResultRecord[]> {
  const token = requireAccessToken();
  const results = await apiRequest<ListResponse<KnowledgeSearchResultItem>>(
    '/api/knowledge/search',
    {
      body: {
        knowledge_space_id: knowledgeSpaceId,
        query,
        top_k: topK,
      },
      method: 'POST',
      token,
    },
  );
  return results.items.map(mapKnowledgeSearchResult);
}

export async function approveKnowledgeDeposit(
  depositId: string,
  payload: KnowledgeDepositApprovePayload = {},
): Promise<KnowledgeDepositRecord> {
  const token = requireAccessToken();
  const deposit = await apiRequest<KnowledgeDepositListItem>(
    `/api/knowledge/deposits/${depositId}/approve`,
    {
      body: {
        permission_roles: payload.permissionRoles ?? ['admin'],
        title: payload.title,
      },
      method: 'POST',
      token,
    },
  );
  return mapKnowledgeDeposit(deposit);
}

export async function rejectKnowledgeDeposit(
  depositId: string,
  reason: string,
): Promise<KnowledgeDepositRecord> {
  const token = requireAccessToken();
  const deposit = await apiRequest<KnowledgeDepositListItem>(
    `/api/knowledge/deposits/${depositId}/reject`,
    {
      body: { reason },
      method: 'POST',
      token,
    },
  );
  return mapKnowledgeDeposit(deposit);
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
      firstKnownValue(item, [
        'name',
        'metric_name',
        'repository_name',
        'release_name',
        'title',
        'job_name',
        'build_id',
        'metric_date',
        'environment',
        'window_start',
      ]),
    ),
    status: formatUnknownValue(item.status),
    updatedAt: formatListDate(
      formatUnknownValue(firstKnownValue(item, ['updated_at', 'created_at', 'observed_at', 'date'])),
    ),
    value: formatUnknownValue(
      firstKnownValue(item, [
        'value',
        'count',
        'score',
        'summary',
        'commit_count',
        'build_id',
        'duration_seconds',
        'error_rate',
        'request_count',
        'p95_latency_ms',
      ]),
    ),
  }));
}

function mapOperationalMetricRecord(item: FlexibleListItem, index: number): OperationalMetricRecord {
  return {
    category: formatUnknownValue(item.category),
    id: formatUnknownValue(item.id ?? `operational-metric-${index}`),
    name: formatUnknownValue(
      firstKnownValue(item, [
        'name',
        'metric_name',
        'repository_name',
        'release_name',
        'title',
        'job_name',
        'build_id',
        'metric_date',
        'environment',
        'window_start',
      ]),
    ),
    status: formatUnknownValue(item.status),
    updatedAt: formatListDate(
      formatUnknownValue(firstKnownValue(item, ['updated_at', 'created_at', 'observed_at', 'date'])),
    ),
    value: formatUnknownValue(
      firstKnownValue(item, [
        'value',
        'count',
        'score',
        'summary',
        'commit_count',
        'quality_score',
        'build_id',
        'duration_seconds',
        'error_rate',
        'request_count',
        'p95_latency_ms',
      ]),
    ),
  };
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

export async function fetchDevopsMetricList(
  query: OperationalMetricListQuery = {},
): Promise<RemoteListResult<OperationalMetricRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'category', query.category);
  appendQueryParam(params, 'name', query.name);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const path = queryString
    ? `/api/devops/operational-metrics?${queryString}`
    : '/api/devops/operational-metrics';
  const metrics = await apiRequest<ListResponse<FlexibleListItem>>(path, { token });

  return {
    page: metrics.page ?? query.page ?? 1,
    pageSize: metrics.page_size ?? query.pageSize ?? 10,
    performance: metrics.performance,
    rows: metrics.items.map(mapOperationalMetricRecord),
    total: metrics.total,
  };
}

export async function createGitLabDailyCodeMetric(
  payload: GitLabDailyCodeMetricCreatePayload,
): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>('/api/devops/gitlab/daily-code-metrics', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function createJenkinsRelease(
  payload: JenkinsReleaseCreatePayload,
): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>('/api/devops/jenkins/releases', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function createOnlineLogMetric(
  payload: OnlineLogMetricCreatePayload,
): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>('/api/ops/online-log-metrics', {
    body: payload,
    method: 'POST',
    token,
  });
}

function mapCollectorRun(item: FlexibleListItem): CollectorRunRecord {
  const payloadSummary = normalizeObjectRecord(item.payload_summary) ?? {};
  return {
    collectorType: formatUnknownValue(item.collector_type),
    createdBy: formatUnknownValue(item.created_by),
    errorMessage: formatUnknownValue(item.error_message),
    finishedAt: formatListDate(formatUnknownValue(item.finished_at)),
    id: formatUnknownValue(item.id),
    payloadSummary,
    productId: formatUnknownValue(item.product_id),
    recordsImported: Number(item.records_imported ?? 0),
    sourceSystem: formatUnknownValue(item.source_system),
    startedAt: formatListDate(formatUnknownValue(item.started_at)),
    status: formatUnknownValue(item.status),
    updatedAt: formatListDate(formatUnknownValue(item.updated_at ?? item.created_at)),
  };
}

export async function fetchCollectorRuns(): Promise<CollectorRunRecord[]> {
  const token = requireAccessToken();
  const runs = await apiRequest<ListResponse<FlexibleListItem>>('/api/collectors/runs', { token });
  return runs.items.map(mapCollectorRun);
}

export async function createCollectorRun(
  payload: CollectorRunCreatePayload,
): Promise<CollectorRunRecord> {
  const token = requireAccessToken();
  const run = await apiRequest<FlexibleListItem>('/api/collectors/runs', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapCollectorRun(run);
}

export async function updateCollectorRun(
  runId: string,
  payload: CollectorRunPatchPayload,
): Promise<CollectorRunRecord> {
  const token = requireAccessToken();
  const run = await apiRequest<FlexibleListItem>(`/api/collectors/runs/${runId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
  return mapCollectorRun(run);
}

function emptyToUndefined(value: string) {
  return value === '-' ? undefined : value;
}

function mapPendingAttributionItem(item: FlexibleListItem): PendingAttributionItem {
  const rawConfidence = item.confidence;
  const confidence =
    typeof rawConfidence === 'number'
      ? rawConfidence
      : rawConfidence === null || rawConfidence === undefined || rawConfidence === ''
        ? undefined
        : Number.isFinite(Number(rawConfidence))
          ? Number(rawConfidence)
        : undefined;
  return {
    collectorRunId: emptyToUndefined(formatUnknownValue(item.collector_run_id)),
    confidence,
    createdAt: formatListDate(formatUnknownValue(item.created_at)),
    createdBy: emptyToUndefined(formatUnknownValue(item.created_by)),
    id: formatUnknownValue(item.id),
    rawPayload: normalizeObjectRecord(item.raw_payload) ?? {},
    rawSubjectId: emptyToUndefined(formatUnknownValue(item.raw_subject_id)),
    resolutionAction: emptyToUndefined(formatUnknownValue(item.resolution_action)),
    resolutionNote: emptyToUndefined(formatUnknownValue(item.resolution_note)),
    resolvedAt: emptyToUndefined(formatListDate(formatUnknownValue(item.resolved_at))),
    resolvedBy: emptyToUndefined(formatUnknownValue(item.resolved_by)),
    resolvedModuleCode: emptyToUndefined(formatUnknownValue(item.resolved_module_code)),
    resolvedProductId: emptyToUndefined(formatUnknownValue(item.resolved_product_id)),
    resolvedRequirementId: emptyToUndefined(formatUnknownValue(item.resolved_requirement_id)),
    resolvedSubjectId: emptyToUndefined(formatUnknownValue(item.resolved_subject_id)),
    resolvedSubjectType: emptyToUndefined(formatUnknownValue(item.resolved_subject_type)),
    sourceSystem: formatUnknownValue(item.source_system),
    sourceType: formatUnknownValue(item.source_type),
    status: formatUnknownValue(item.status),
    suggestedModuleCode: emptyToUndefined(formatUnknownValue(item.suggested_module_code)),
    suggestedProductId: emptyToUndefined(formatUnknownValue(item.suggested_product_id)),
    summary: formatUnknownValue(item.summary),
    updatedAt: formatListDate(formatUnknownValue(item.updated_at ?? item.created_at)),
  };
}

function pendingAttributionQuery(filters: PendingAttributionFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  const query = params.toString();
  return query ? `/api/attribution/pending-items?${query}` : '/api/attribution/pending-items';
}

export async function fetchPendingAttributionItems(
  filters: PendingAttributionFilters = {},
): Promise<PendingAttributionItem[]> {
  const token = requireAccessToken();
  const items = await apiRequest<ListResponse<FlexibleListItem>>(
    pendingAttributionQuery(filters),
    { token },
  );
  return items.items.map(mapPendingAttributionItem);
}

export async function createPendingAttributionItem(
  payload: PendingAttributionCreatePayload,
): Promise<PendingAttributionItem> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>('/api/attribution/pending-items', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapPendingAttributionItem(item);
}

export async function resolvePendingAttributionItem(
  itemId: string,
  payload: PendingAttributionResolvePayload,
): Promise<PendingAttributionItem> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>(
    `/api/attribution/pending-items/${itemId}/resolve`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return mapPendingAttributionItem(item);
}

function mapUserInsights(category: string, items: FlexibleListItem[]): UserInsightRecord[] {
  return items.map((item, index) => {
    const updatedAtSortValue = formatUnknownValue(
      firstKnownValue(item, ['updated_at', 'created_at', 'observed_at', 'window_start']),
    );
    return {
      category,
      confidenceLevel: formatUnknownValue(item.confidence_level),
      convertedRequirementId: formatUnknownValue(item.converted_requirement_id ?? item.related_requirement_id),
      featureCode: formatUnknownValue(item.feature_code),
      feedbackType: formatUnknownValue(item.feedback_type),
      id: formatUnknownValue(item.id ?? `${category}-${index}`),
      moduleCode: formatUnknownValue(item.module_code),
      owner: formatUnknownValue(firstKnownValue(item, ['user_id', 'owner_id', 'created_by', 'actor_id'])),
      planningCycle: formatUnknownValue(item.planning_cycle),
      priority: formatUnknownValue(item.priority),
      productId: formatUnknownValue(item.product_id),
      status: formatUnknownValue(item.status),
      summary: formatUnknownValue(
        firstKnownValue(item, [
          'summary',
          'title',
          'content',
          'feedback_text',
          'suggestion',
          'recommendation_reason',
          'feature_code',
        ]),
      ),
      updatedAt: formatListDate(updatedAtSortValue),
      updatedAtSortValue,
      versionId: formatUnknownValue(item.version_id),
    };
  });
}

function mapUserInsightRecord(item: FlexibleListItem, index: number): UserInsightRecord {
  const updatedAtSortValue = formatUnknownValue(
    firstKnownValue(item, ['updated_at', 'created_at', 'observed_at', 'window_start']),
  );
  return {
    category: formatUnknownValue(item.category),
    confidenceLevel: formatUnknownValue(item.confidence_level),
    convertedRequirementId: formatUnknownValue(item.converted_requirement_id ?? item.related_requirement_id),
    featureCode: formatUnknownValue(item.feature_code),
    feedbackType: formatUnknownValue(item.feedback_type),
    id: formatUnknownValue(item.id ?? `user-insight-${index}`),
    moduleCode: formatUnknownValue(item.module_code),
    owner: formatUnknownValue(firstKnownValue(item, ['owner', 'user_id', 'owner_id', 'created_by', 'actor_id'])),
    planningCycle: formatUnknownValue(item.planning_cycle),
    priority: formatUnknownValue(item.priority),
    productId: formatUnknownValue(item.product_id),
    status: formatUnknownValue(item.status),
    summary: formatUnknownValue(
      firstKnownValue(item, [
        'summary',
        'title',
        'content',
        'feedback_text',
        'suggestion',
        'recommendation_reason',
        'feature_code',
      ]),
    ),
    updatedAt: formatListDate(updatedAtSortValue),
    updatedAtSortValue,
    versionId: formatUnknownValue(item.version_id),
  };
}

function sortUserInsightsByUpdatedAt(records: UserInsightRecord[]): UserInsightRecord[] {
  return [...records].sort((left, right) => {
    const rightTime = Date.parse(right.updatedAtSortValue ?? '');
    const leftTime = Date.parse(left.updatedAtSortValue ?? '');
    const timeDiff = (Number.isFinite(rightTime) ? rightTime : 0) - (Number.isFinite(leftTime) ? leftTime : 0);
    if (timeDiff !== 0) {
      return timeDiff;
    }
    return right.id.localeCompare(left.id);
  });
}

export async function fetchUserInsights(): Promise<UserInsightRecord[]> {
  const token = requireAccessToken();
  const [usageMetrics, feedbackItems, iterationSuggestions] = await Promise.all([
    apiRequest<ListResponse<FlexibleListItem>>('/api/insights/usage-metrics', { token }),
    apiRequest<ListResponse<FlexibleListItem>>('/api/insights/user-feedback', { token }),
    apiRequest<ListResponse<FlexibleListItem>>('/api/planning/iteration-suggestions', { token }),
  ]);

  return sortUserInsightsByUpdatedAt([
    ...mapUserInsights('使用趋势', usageMetrics.items),
    ...mapUserInsights('用户反馈', feedbackItems.items),
    ...mapUserInsights('迭代建议', iterationSuggestions.items),
  ]);
}

export async function fetchUserInsightList(
  query: UserInsightListQuery = {},
): Promise<RemoteListResult<UserInsightRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'category', query.category);
  appendQueryParam(params, 'summary', query.summary);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const path = queryString ? `/api/insights/items?${queryString}` : '/api/insights/items';
  const insights = await apiRequest<ListResponse<FlexibleListItem>>(path, { token });

  return {
    page: insights.page ?? query.page ?? 1,
    pageSize: insights.page_size ?? query.pageSize ?? 10,
    performance: insights.performance,
    rows: insights.items.map(mapUserInsightRecord),
    total: insights.total,
  };
}

export async function createUserFeedback(payload: UserFeedbackCreatePayload): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>('/api/insights/user-feedback', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function createUserUsageMetric(
  payload: UserUsageMetricCreatePayload,
): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>('/api/insights/usage-metrics', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateUserFeedback(
  feedbackId: string,
  payload: UserFeedbackPatchPayload,
): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>(`/api/insights/user-feedback/${feedbackId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function convertUserFeedbackToRequirement(
  feedbackId: string,
  payload: UserFeedbackConvertRequirementPayload,
): Promise<{ feedback: FlexibleListItem; requirement: RequirementListItem }> {
  const token = requireAccessToken();
  return apiRequest<{ feedback: FlexibleListItem; requirement: RequirementListItem }>(
    `/api/insights/user-feedback/${feedbackId}/convert-requirement`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
}

export async function createIterationSuggestions(
  payload: IterationSuggestionCreatePayload,
): Promise<ListResponse<FlexibleListItem>> {
  const token = requireAccessToken();
  return apiRequest<ListResponse<FlexibleListItem>>('/api/planning/iteration-suggestions', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function decideIterationSuggestion(
  suggestionId: string,
  payload: IterationSuggestionDecisionPayload,
): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>(`/api/planning/iteration-suggestions/${suggestionId}/decide`, {
    body: payload,
    method: 'POST',
    token,
  });
}
