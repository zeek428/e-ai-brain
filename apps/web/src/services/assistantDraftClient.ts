import {
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
} from './apiClient';
import type { ListResponse, RemoteListPerformance } from './apiClient';
import {
  getStoredCurrentUser,
  requireAccessToken,
  setAuthLocalCacheClearHandler,
} from './authClient';

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

type RemoteSortOrder = 'ascend' | 'descend';

type AssistantDraftRemoteListQuery = {
  page?: number;
  pageSize?: number;
  sortField?: string;
  sortOrder?: RemoteSortOrder;
};

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
  auto_dry_run?: boolean;
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
  confirm_blocked_count?: number;
  confirm_ready_count?: number;
  decision_counts?: Record<string, number>;
  draft_total: number;
  governance_counts?: {
    audit_events?: number;
    failed?: number;
    high_risk?: number;
    permission_blocked?: number;
    permission_issues?: number;
    permission_warning?: number;
    retry_total?: number;
    validation_blocked?: number;
    validation_issues?: number;
    validation_warning?: number;
  };
  permission_counts?: Record<string, number>;
  resolution_rate: number;
  risk_counts?: Record<string, number>;
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
  can_confirm?: boolean;
  decision_label?: string | null;
  decision_next_action?: string | null;
  decision_reason?: string | null;
  decision_status?: string | null;
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

export type AssistantActionDraftWorkbenchQuery = AssistantDraftRemoteListQuery & {
  action?: string;
  createdFrom?: string;
  createdTo?: string;
  keyword?: string;
  status?: string;
  validationStatus?: string;
};

export type AssistantActionDraftWorkbenchResult = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: AssistantActionDraftWorkbenchItem[];
  summary: AssistantActionDraftWorkbenchSummary;
  total: number;
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
  decision?: {
    blocking_count?: number;
    can_confirm?: boolean;
    can_retry?: boolean;
    label?: string | null;
    next_action?: string | null;
    reason?: string | null;
    status?: string | null;
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
