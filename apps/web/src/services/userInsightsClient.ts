import { formatDisplayDateTime } from '../utils/dateTime';
import {
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
  type ListResponse,
  type RemoteListPerformance,
} from './apiClient';
import { requireAccessToken } from './authClient';
import type { RequirementListItem } from './requirementClient';

type RemoteSortOrder = 'ascend' | 'descend';

type RemoteListQuery = {
  page?: number;
  pageSize?: number;
  sortField?: string;
  sortOrder?: RemoteSortOrder;
};

type RemoteListResult<Row> = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: Row[];
  total: number;
};

type FlexibleListItem = Record<string, unknown> & {
  id?: string;
};

export type UserInsightListQuery = RemoteListQuery & {
  category?: string;
  status?: string;
  summary?: string;
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

function formatListDate(value?: string) {
  return formatDisplayDateTime(value);
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

function firstKnownValue(item: FlexibleListItem, keys: string[]) {
  for (const key of keys) {
    const value = item[key];
    if (value !== null && value !== undefined && value !== '') {
      return value;
    }
  }
  return undefined;
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
