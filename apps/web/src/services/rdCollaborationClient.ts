import { apiRequest, appendQueryParam, type ListResponse } from './apiClient';
import { requireAccessToken } from './authClient';

export type RdRoleDefinition = {
  assignable_subject_types: Array<'ai_employee' | 'human_user'>;
  capabilities: string[];
  code: string;
  id: string;
  maximum_risk_level: 'low' | 'medium' | 'high' | 'critical';
  name: string;
  responsibilities: string[];
  status: 'active' | 'disabled';
};

export type RdAiEmployee = {
  capability_tags: string[];
  code: string;
  id: string;
  name: string;
  persona_version: number;
  status: 'active' | 'disabled' | 'retired';
  work_style_version: number;
};

export type CreateRdRolePayload = {
  assignable_subject_types: Array<'ai_employee' | 'human_user'>;
  capabilities: string[];
  code: string;
  maximum_risk_level: 'low' | 'medium' | 'high' | 'critical';
  name: string;
  responsibilities: string[];
  status?: 'active' | 'disabled';
};

export type RdExecutorProfile = {
  code: string;
  executor_type: string;
  health_status: 'unknown' | 'healthy' | 'degraded' | 'unavailable';
  id: string;
  name: string;
  runner_id?: string | null;
  status: 'active' | 'disabled' | 'retired';
  supported_role_codes: string[];
};

export type RdPolicyRoleBinding = {
  actor_mode: 'human' | 'ai' | 'hybrid';
  candidate_ai_employee_ids?: string[];
  candidate_human_user_ids?: string[];
  context_config?: Record<string, unknown>;
  primary_executor_profile_id?: string | null;
  required_permissions?: string[];
  reviewer_role_codes?: string[];
  role_code: string;
  status: 'active' | 'disabled';
  tool_config?: Record<string, unknown>;
};

export type RdDeliveryPolicy = {
  assessment_config: Record<string, unknown>;
  autonomy_config: Record<string, unknown>;
  brain_app_id: string;
  delivery_target: 'ready_for_release' | 'deployed';
  deployment_config: Record<string, unknown>;
  experience_reuse_config: Record<string, unknown>;
  git_config: Record<string, unknown>;
  id: string;
  iteration_config: Record<string, unknown>;
  matching_config: Record<string, unknown>;
  name: string;
  policy_version: number;
  product_id?: string | null;
  product_name?: string | null;
  quality_gate_config: Record<string, unknown>;
  role_bindings: RdPolicyRoleBinding[];
  status: 'active' | 'disabled';
  team_config: Record<string, unknown>;
  updated_at?: string;
};

export type RdDeliveryPolicyPayload = Omit<RdDeliveryPolicy, 'id' | 'policy_version' | 'product_name' | 'updated_at'>;

export type CreateRdAiEmployeePayload = {
  brain_app_id?: string;
  capability_tags: string[];
  code: string;
  name: string;
  persona_json: Record<string, unknown>;
  persona_version?: number;
  status?: 'active' | 'disabled' | 'retired';
  work_style_json: Record<string, unknown>;
  work_style_version?: number;
};

function querySuffix(query: Record<string, string | undefined>) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    appendQueryParam(params, key, value);
  }
  return params.toString() ? `?${params.toString()}` : '';
}

export async function fetchRdDeliveryPolicies(): Promise<RdDeliveryPolicy[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<RdDeliveryPolicy>>(
    '/api/delivery/rd-task-executor-policies',
    { token },
  );
  return response.items;
}

export async function createRdDeliveryPolicy(payload: RdDeliveryPolicyPayload) {
  const token = requireAccessToken();
  const response = await apiRequest<{ policy: RdDeliveryPolicy }>(
    '/api/delivery/rd-task-executor-policies',
    { body: payload, method: 'POST', token },
  );
  return response.policy;
}

export async function updateRdDeliveryPolicy(
  policyId: string,
  expectedPolicyVersion: number,
  changes: Partial<RdDeliveryPolicyPayload>,
) {
  const token = requireAccessToken();
  const response = await apiRequest<{ policy: RdDeliveryPolicy }>(
    `/api/delivery/rd-task-executor-policies/${policyId}`,
    { body: { changes, expected_policy_version: expectedPolicyVersion }, method: 'PATCH', token },
  );
  return response.policy;
}

export async function fetchRdRoles(status?: 'active' | 'disabled') {
  const token = requireAccessToken();
  const response = await apiRequest<{ items: RdRoleDefinition[] }>(
    `/api/delivery/rd-roles${querySuffix({ status })}`,
    { token },
  );
  return response.items;
}

export async function createRdRole(payload: CreateRdRolePayload) {
  const token = requireAccessToken();
  return apiRequest<RdRoleDefinition>('/api/delivery/rd-roles', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function fetchRdAiEmployees(status?: 'active' | 'disabled' | 'retired') {
  const token = requireAccessToken();
  const response = await apiRequest<{ items: RdAiEmployee[] }>(
    `/api/delivery/rd-ai-employees${querySuffix({ status })}`,
    { token },
  );
  return response.items;
}

export async function createRdAiEmployee(payload: CreateRdAiEmployeePayload) {
  const token = requireAccessToken();
  return apiRequest<RdAiEmployee>('/api/delivery/rd-ai-employees', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function fetchRdExecutorProfiles(status?: 'active' | 'disabled' | 'retired') {
  const token = requireAccessToken();
  const response = await apiRequest<{ items: RdExecutorProfile[] }>(
    `/api/delivery/rd-executor-profiles${querySuffix({ status })}`,
    { token },
  );
  return response.items;
}

export type RdCollaborationRun = {
  delivery_target: 'ready_for_release' | 'deployed';
  id: string;
  policy_snapshot_id?: string;
  product_version_id: string;
  status: string;
  strategy_snapshot_id?: string;
  suspended_decision_request_id?: string | null;
};

export type RdWorkItem = {
  id: string;
  owner_seat_id?: string | null;
  priority?: string;
  risk_level?: string;
  status: string;
  title: string;
  version: number;
};

export type RdWorkItemDependency = {
  dependency_type?: string;
  predecessor_work_item_id: string;
  status: string;
  successor_work_item_id: string;
};

export type RdDecisionRequest = {
  id: string;
  options_json?: Array<{ code: string; description?: string; label?: string }>;
  prompt?: string;
  reason?: string;
  status: string;
  subject_type?: string;
  version: number;
};

export async function fetchRdCollaborationRun(runId: string) {
  const token = requireAccessToken();
  return apiRequest<RdCollaborationRun & { seats: Array<Record<string, unknown>>; scope: Array<Record<string, unknown>> }>(
    `/api/delivery/rd-collaboration-runs/${runId}`,
    { token },
  );
}

export async function startRdCollaborationRun(
  versionId: string,
  payload: { reason?: string; request_id: string; scope_version: number },
) {
  const token = requireAccessToken();
  return apiRequest<RdCollaborationRun>(`/api/product-versions/${versionId}/collaboration-runs`, {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function fetchRdWorkItems(runId: string) {
  const token = requireAccessToken();
  return apiRequest<{ dependencies: RdWorkItemDependency[]; items: RdWorkItem[] }>(
    `/api/delivery/rd-collaboration-runs/${runId}/work-items`,
    { token },
  );
}

export async function decideRdDecisionRequest(
  decisionRequestId: string,
  payload: { comment?: string; selected_option: string; version: number },
) {
  const token = requireAccessToken();
  return apiRequest<unknown>(`/api/delivery/decision-requests/${decisionRequestId}/decide`, {
    body: { ...payload, idempotency_key: crypto.randomUUID() },
    method: 'POST',
    token,
  });
}

export async function fetchRdDecisionRequest(decisionRequestId: string) {
  const token = requireAccessToken();
  return apiRequest<RdDecisionRequest>(`/api/delivery/decision-requests/${decisionRequestId}`, { token });
}
