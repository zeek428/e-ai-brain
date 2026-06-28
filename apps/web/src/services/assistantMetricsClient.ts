import { apiRequest } from './apiClient';
import { requireAccessToken } from './authClient';

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
  draft_deeplink_viewed_count?: number;
  draft_detail_viewed_count?: number;
  draft_expired_count?: number;
  draft_failed_count?: number;
  draft_inferred_viewed_count?: number;
  draft_pending_count?: number;
  draft_resolution_rate?: number;
  draft_total?: number;
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
