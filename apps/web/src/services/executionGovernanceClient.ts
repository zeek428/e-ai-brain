import { apiRequest, type ListResponse } from './apiClient';
import { requireAccessToken } from './authClient';

export type ExecutionResourceGrantRecord = {
  created_at?: string;
  created_by?: string;
  environment: string;
  id: string;
  product_id: string;
  resource_id: string;
  resource_type: 'jenkins_connection' | 'runner_target';
  status: 'active' | 'disabled';
  target_code?: string | null;
  updated_at?: string;
  version: number;
};

export type ExecutionResourceGrantQuery = {
  environment?: string;
  productId?: string;
  resourceType?: string;
  status?: string;
};

export type ExecutionResourceGrantPayload = {
  environment: string;
  product_id: string;
  resource_id: string;
  resource_type: 'jenkins_connection' | 'runner_target';
  target_code?: string | null;
};

export type ExecutionResourceProduct = {
  id: string;
  name: string;
  status?: string;
};

export type ExternalEventInboxRecord = {
  attempt_count: number;
  context: {
    connection_id?: string | null;
    environment?: string | null;
    product_id?: string | null;
    version_id?: string | null;
  };
  delivery_id: string;
  error_message?: string | null;
  event_type: string;
  id: string;
  payload_hash: string;
  processed_at?: string | null;
  provider: string;
  received_at: string;
  signature_status: string;
  status: string;
  updated_at: string;
};

export type ExternalEventInboxPage = {
  items: ExternalEventInboxRecord[];
  page: number;
  page_size: number;
  total: number;
};

function append(params: URLSearchParams, key: string, value?: string) {
  if (value) {
    params.set(key, value);
  }
}

export async function fetchExecutionResourceGrants(
  query: ExecutionResourceGrantQuery = {},
): Promise<ExecutionResourceGrantRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  append(params, 'environment', query.environment);
  append(params, 'product_id', query.productId);
  append(params, 'resource_type', query.resourceType);
  append(params, 'status', query.status);
  const queryString = params.toString();
  const response = await apiRequest<{ items: ExecutionResourceGrantRecord[]; total: number }>(
    queryString ? `/api/system/execution-resources?${queryString}` : '/api/system/execution-resources',
    { token },
  );
  return response.items;
}

export async function fetchExecutionResourceProducts(): Promise<ExecutionResourceProduct[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<ExecutionResourceProduct>>(
    '/api/products?active_only=true&page_size=100',
    { token },
  );
  return response.items;
}

export async function createExecutionResourceGrant(payload: ExecutionResourceGrantPayload) {
  const token = requireAccessToken();
  return apiRequest<ExecutionResourceGrantRecord>('/api/system/execution-resources', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateExecutionResourceGrantStatus(
  grantId: string,
  payload: { status: 'active' | 'disabled'; version: number },
) {
  const token = requireAccessToken();
  return apiRequest<ExecutionResourceGrantRecord>(`/api/system/execution-resources/${grantId}`, {
    body: payload,
    method: 'PUT',
    token,
  });
}

export async function fetchExternalEventInbox(query: {
  eventType?: string;
  page?: number;
  pageSize?: number;
  provider?: string;
  status?: string;
} = {}): Promise<ExternalEventInboxPage> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  append(params, 'event_type', query.eventType);
  params.set('page', String(query.page ?? 1));
  params.set('page_size', String(query.pageSize ?? 20));
  append(params, 'provider', query.provider);
  append(params, 'status', query.status);
  return apiRequest<ExternalEventInboxPage>(`/api/system/external-events?${params.toString()}`, { token });
}

export async function retryExternalEvent(eventId: string, reason?: string) {
  const token = requireAccessToken();
  return apiRequest<ExternalEventInboxRecord>(`/api/system/external-events/${eventId}/retry`, {
    body: { reason: reason || null },
    method: 'POST',
    token,
  });
}
