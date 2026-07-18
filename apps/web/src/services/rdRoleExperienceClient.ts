import { apiRequest, appendQueryParam, type ListResponse } from './apiClient';
import { requireAccessToken } from './authClient';

export type RdRoleExperience = {
  brain_app_id: string;
  confidence: number;
  content: Record<string, unknown>;
  id: string;
  product_scope: string[];
  repository_trust_domains: string[];
  review_version: number;
  risk_scope: { maximum?: string };
  role_code: string;
  scenario: string;
  status: 'pending' | 'approved' | 'rejected' | 'retired';
  tool_trust_domains: string[];
  work_item_type: string;
};

export type RdRoleExperienceFilters = {
  brain_app_id?: string;
  evidence_subject_id?: string;
  minimum_confidence?: number;
  page?: number;
  page_size?: number;
  product_id?: string;
  repository_trust_domain?: string;
  risk_level?: string;
  role_code?: string;
  scenario?: string;
  status?: RdRoleExperience['status'];
  tool_trust_domain?: string;
  version?: number;
  work_item_type?: string;
};

function querySuffix(filters: RdRoleExperienceFilters) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    appendQueryParam(params, key, value === undefined ? undefined : String(value));
  }
  return params.toString() ? `?${params.toString()}` : '';
}

export async function fetchRdRoleExperiences(filters: RdRoleExperienceFilters) {
  const token = requireAccessToken();
  return apiRequest<ListResponse<RdRoleExperience>>(
    `/api/delivery/rd-role-experiences${querySuffix(filters)}`,
    { token },
  );
}

export async function decideRdRoleExperience(
  experienceId: string,
  payload: { comment?: string; decision: 'approve' | 'reject' | 'retire'; version: number },
) {
  const token = requireAccessToken();
  return apiRequest<RdRoleExperience>(`/api/delivery/rd-role-experiences/${experienceId}/decide`, {
    body: { ...payload, idempotency_key: crypto.randomUUID() },
    method: 'POST',
    token,
  });
}
