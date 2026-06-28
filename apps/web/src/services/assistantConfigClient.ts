import {
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
} from './apiClient';
import type {
  ListResponse,
  RemoteListPerformance,
} from './apiClient';
import { requireAccessToken } from './authClient';

type RemoteSortOrder = 'ascend' | 'descend';

type AssistantConfigListQuery = {
  page?: number;
  pageSize?: number;
  sortField?: string;
  sortOrder?: RemoteSortOrder;
};

type AssistantConfigListResult<Row> = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: Row[];
  total: number;
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

export type AssistantActionReferenceConfigListQuery = AssistantConfigListQuery & {
  enterpriseId?: string;
  keyword?: string;
  permission?: string;
  role?: string;
  status?: string;
  templateVersion?: string;
};

export type AssistantRoleQuickTaskConfigListQuery = AssistantConfigListQuery & {
  enterpriseId?: string;
  groupStatus?: string;
  keyword?: string;
  permission?: string;
  role?: string;
  status?: string;
  targetDraftType?: string;
  templateVersion?: string;
};

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
): Promise<AssistantConfigListResult<AssistantActionReferenceConfig>> {
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
    total: response.total ?? response.items.length,
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
): Promise<AssistantConfigListResult<AssistantRoleQuickTaskConfig>> {
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
    total: response.total ?? response.items.length,
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
