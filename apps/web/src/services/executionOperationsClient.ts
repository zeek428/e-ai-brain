import { apiRequest } from './apiClient';
import { requireAccessToken } from './authClient';

export type ExecutionOperationRecord = {
  id?: string;
  operation_type?: string;
  product_id?: string;
  provider?: string;
  status?: string;
  updated_at?: string;
};

export type ExecutionOperationsOverview = {
  backlog: {
    dead_letter_count: number;
    expired_lease_count: number;
    oldest_pending_seconds: number;
    pending_count: number;
    retry_count: number;
  };
  outbox_status_counts: Record<string, number>;
  reconciliation: {
    items: ExecutionOperationRecord[];
    manual_count: number;
    pending_count: number;
  };
  workers: Array<{
    claimed_count: number;
    updated_at?: string;
    worker_id: string;
  }>;
};

export async function fetchExecutionOperationsOverview(): Promise<ExecutionOperationsOverview> {
  const token = requireAccessToken();
  return apiRequest<ExecutionOperationsOverview>('/api/system/execution-operations-overview', { token });
}

export async function reconcileExecutionOperations() {
  const token = requireAccessToken();
  return apiRequest<{ items: Array<{ id: string; status: string }>; total: number }>(
    '/api/system/execution-operations/reconcile',
    { method: 'POST', token },
  );
}
