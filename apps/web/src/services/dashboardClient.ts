import { apiRequest } from './apiClient';
import { requireAccessToken } from './authClient';

export type DashboardSummary = {
  activeProducts: number;
  aiTasks: number;
  auditEvents: number;
  bugs: number;
  gitlabCommits: number;
  highSeverityBugs: number;
  iterationSuggestions: number;
  jenkinsReleases: number;
  knowledgeDeposits: number;
  knowledgeDocuments: number;
  onlineErrors: number;
  openBugs: number;
  pendingReviews: number;
  requirements: number;
  usageEvents: number;
  userFeedback: number;
};

export type DashboardStatusCount = {
  count: number;
  status: string;
};

export type DashboardTaskSummary = {
  id: string;
  status: string;
  title: string;
  type: string;
};

export type DashboardReviewSummary = {
  id: string;
  stage: string;
};

export type DashboardKnowledgeSummary = {
  id: string;
  title: string;
};

export type DashboardAuditSummary = {
  eventType: string;
  id: string;
};

export type DashboardBugSummary = {
  id: string;
  severity: string;
  status: string;
  title: string;
};

export type DashboardGitLabSummary = {
  averageQualityScore: number;
  changedFiles: number;
  commitCount: number;
  mergeRequestCount: number;
  metricCount: number;
  riskCount: number;
};

export type DashboardOnlineLogSummary = {
  errorCount: number;
  errorRate: number;
  maxP95LatencyMs: number;
  maxP99LatencyMs: number;
  metricCount: number;
  requestCount: number;
};

export type DashboardUsageMetricSummary = {
  activeUsers: number;
  conversionCount: number;
  errorCount: number;
  eventCount: number;
  metricCount: number;
};

export type DashboardCacheMetadata = {
  cacheEnabled: boolean;
  cacheHit: boolean;
  durationMs: number;
  generatedAt: string;
  slow: boolean;
  ttlSeconds: number;
};

export type DashboardTrendSeries = {
  category: string;
  key: string;
  label: string;
  unit: string;
};

export type DashboardTrendPoint = {
  period: string;
} & Record<string, number | string>;

export type DashboardTrend = {
  grain: string;
  points: DashboardTrendPoint[];
  series: DashboardTrendSeries[];
  timeRange: string;
  windowEnd: string;
  windowStart: string;
};

export type ItTeamDashboard = {
  bugStatusCounts: DashboardStatusCount[];
  cacheMetadata: DashboardCacheMetadata;
  gitlabDailySummary: DashboardGitLabSummary;
  iterationSuggestionStatusCounts: DashboardStatusCount[];
  jenkinsReleaseStatusCounts: DashboardStatusCount[];
  latestTasks: DashboardTaskSummary[];
  latestHighSeverityBugs: DashboardBugSummary[];
  onlineLogSummary: DashboardOnlineLogSummary;
  pendingReviews: DashboardReviewSummary[];
  recentAuditEvents: DashboardAuditSummary[];
  recentKnowledgeDocuments: DashboardKnowledgeSummary[];
  requirementStatusCounts: DashboardStatusCount[];
  summary: DashboardSummary;
  taskStatusCounts: DashboardStatusCount[];
  timeRange: string;
  trend: DashboardTrend;
  usageMetricSummary: DashboardUsageMetricSummary;
  userFeedbackStatusCounts: DashboardStatusCount[];
};

type FlexibleDashboardItem = Record<string, unknown> & {
  created_at?: string;
  id?: string;
  status?: string;
  updated_at?: string;
};

type DashboardResponse = {
  bug_status_counts?: Array<{ count?: number; status?: string }>;
  gitlab_daily_summary?: Partial<{
    average_quality_score: number;
    changed_files: number;
    commit_count: number;
    merge_request_count: number;
    metric_count: number;
    risk_count: number;
  }>;
  iteration_suggestion_status_counts?: Array<{ count?: number; status?: string }>;
  jenkins_release_status_counts?: Array<{ count?: number; status?: string }>;
  latest_high_severity_bugs?: FlexibleDashboardItem[];
  latest_tasks?: FlexibleDashboardItem[];
  metadata?: {
    dashboard_cache?: Partial<{
      cache_enabled: boolean;
      cache_hit: boolean;
      duration_ms: number;
      generated_at: string;
      slow: boolean;
      ttl_seconds: number;
    }>;
  };
  online_log_summary?: Partial<{
    error_count: number;
    error_rate: number;
    max_p95_latency_ms: number;
    max_p99_latency_ms: number;
    metric_count: number;
    request_count: number;
  }>;
  pending_reviews?: FlexibleDashboardItem[];
  recent_audit_events?: FlexibleDashboardItem[];
  recent_knowledge_documents?: FlexibleDashboardItem[];
  requirement_status_counts?: Array<{ count?: number; status?: string }>;
  summary?: Partial<{
    active_products: number;
    ai_tasks: number;
    audit_events: number;
    bugs: number;
    gitlab_commits: number;
    high_severity_bugs: number;
    iteration_suggestions: number;
    jenkins_releases: number;
    knowledge_deposits: number;
    knowledge_documents: number;
    online_errors: number;
    open_bugs: number;
    pending_reviews: number;
    requirements: number;
    usage_events: number;
    user_feedback: number;
  }>;
  task_status_counts?: Array<{ count?: number; status?: string }>;
  time_range?: string;
  trend?: Partial<{
    grain: string;
    points: Array<Record<string, unknown> & { period?: string }>;
    series: Array<Partial<DashboardTrendSeries>>;
    time_range: string;
    window_end: string;
    window_start: string;
  }>;
  usage_metric_summary?: Partial<{
    active_users: number;
    conversion_count: number;
    error_count: number;
    event_count: number;
    metric_count: number;
  }>;
  user_feedback_status_counts?: Array<{ count?: number; status?: string }>;
};

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

function firstKnownValue(item: FlexibleDashboardItem, keys: string[]) {
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

function mapDashboardStatusCounts(
  items?: Array<{ count?: number; status?: string }>,
): DashboardStatusCount[] {
  return (items ?? []).map((item) => ({
    count: normalizeDashboardCount(item.count),
    status: formatUnknownValue(item.status),
  }));
}

function mapDashboardTrend(trend?: DashboardResponse['trend']): DashboardTrend {
  const series = (trend?.series ?? [])
    .map((item) => ({
      category: formatUnknownValue(item.category),
      key: formatUnknownValue(item.key),
      label: formatUnknownValue(item.label),
      unit: formatUnknownValue(item.unit),
    }))
    .filter((item) => item.key !== '-');
  return {
    grain: formatUnknownValue(trend?.grain),
    points: (trend?.points ?? []).map((point) => {
      const mappedPoint: DashboardTrendPoint = {
        period: formatUnknownValue(point.period),
      };
      for (const item of series) {
        mappedPoint[item.key] = normalizeDashboardCount(point[item.key]);
      }
      return mappedPoint;
    }),
    series,
    timeRange: formatUnknownValue(trend?.time_range),
    windowEnd: formatUnknownValue(trend?.window_end),
    windowStart: formatUnknownValue(trend?.window_start),
  };
}

export async function fetchItTeamDashboard(
  params: { forceRefresh?: boolean; productId?: string; timeRange?: string } = {},
): Promise<ItTeamDashboard> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  if (params.productId) {
    query.set('product_id', params.productId);
  }
  if (params.timeRange) {
    query.set('time_range', params.timeRange);
  }
  if (params.forceRefresh) {
    query.set('refresh', 'true');
  }
  const path = query.toString()
    ? `/api/dashboard/it-team?${query.toString()}`
    : '/api/dashboard/it-team';
  const dashboard = await apiRequest<DashboardResponse>(path, { token });
  const summary = dashboard.summary ?? {};
  const gitlabDailySummary = dashboard.gitlab_daily_summary ?? {};
  const dashboardCache = dashboard.metadata?.dashboard_cache ?? {};
  const onlineLogSummary = dashboard.online_log_summary ?? {};
  const usageMetricSummary = dashboard.usage_metric_summary ?? {};
  return {
    bugStatusCounts: mapDashboardStatusCounts(dashboard.bug_status_counts),
    cacheMetadata: {
      cacheEnabled: Boolean(dashboardCache.cache_enabled),
      cacheHit: Boolean(dashboardCache.cache_hit),
      durationMs: normalizeDashboardCount(dashboardCache.duration_ms),
      generatedAt: formatUnknownValue(dashboardCache.generated_at),
      slow: Boolean(dashboardCache.slow),
      ttlSeconds: normalizeDashboardCount(dashboardCache.ttl_seconds),
    },
    gitlabDailySummary: {
      averageQualityScore: normalizeDashboardCount(gitlabDailySummary.average_quality_score),
      changedFiles: normalizeDashboardCount(gitlabDailySummary.changed_files),
      commitCount: normalizeDashboardCount(gitlabDailySummary.commit_count),
      mergeRequestCount: normalizeDashboardCount(gitlabDailySummary.merge_request_count),
      metricCount: normalizeDashboardCount(gitlabDailySummary.metric_count),
      riskCount: normalizeDashboardCount(gitlabDailySummary.risk_count),
    },
    iterationSuggestionStatusCounts: mapDashboardStatusCounts(
      dashboard.iteration_suggestion_status_counts,
    ),
    jenkinsReleaseStatusCounts: mapDashboardStatusCounts(dashboard.jenkins_release_status_counts),
    latestHighSeverityBugs: (dashboard.latest_high_severity_bugs ?? []).map((bug, index) => ({
      id: formatUnknownValue(bug.id ?? `bug-${index}`),
      severity: formatUnknownValue(bug.severity),
      status: formatUnknownValue(bug.status),
      title: formatUnknownValue(firstKnownValue(bug, ['title', 'name'])),
    })),
    latestTasks: (dashboard.latest_tasks ?? []).map((task, index) => ({
      id: formatUnknownValue(task.id ?? `task-${index}`),
      status: formatUnknownValue(task.status),
      title: formatUnknownValue(firstKnownValue(task, ['title', 'name'])),
      type: formatUnknownValue(task.task_type),
    })),
    pendingReviews: (dashboard.pending_reviews ?? []).map((review, index) => ({
      id: formatUnknownValue(review.id ?? `review-${index}`),
      stage: formatUnknownValue(review.stage),
    })),
    recentAuditEvents: (dashboard.recent_audit_events ?? []).map((event, index) => ({
      eventType: formatUnknownValue(event.event_type),
      id: formatUnknownValue(event.id ?? `audit-${index}`),
    })),
    recentKnowledgeDocuments: (dashboard.recent_knowledge_documents ?? []).map(
      (document, index) => ({
        id: formatUnknownValue(document.id ?? `knowledge-${index}`),
        title: formatUnknownValue(document.title),
      }),
    ),
    onlineLogSummary: {
      errorCount: normalizeDashboardCount(onlineLogSummary.error_count),
      errorRate: normalizeDashboardCount(onlineLogSummary.error_rate),
      maxP95LatencyMs: normalizeDashboardCount(onlineLogSummary.max_p95_latency_ms),
      maxP99LatencyMs: normalizeDashboardCount(onlineLogSummary.max_p99_latency_ms),
      metricCount: normalizeDashboardCount(onlineLogSummary.metric_count),
      requestCount: normalizeDashboardCount(onlineLogSummary.request_count),
    },
    requirementStatusCounts: mapDashboardStatusCounts(dashboard.requirement_status_counts),
    summary: {
      activeProducts: normalizeDashboardCount(summary.active_products),
      aiTasks: normalizeDashboardCount(summary.ai_tasks),
      auditEvents: normalizeDashboardCount(summary.audit_events),
      bugs: normalizeDashboardCount(summary.bugs),
      gitlabCommits: normalizeDashboardCount(summary.gitlab_commits),
      highSeverityBugs: normalizeDashboardCount(summary.high_severity_bugs),
      iterationSuggestions: normalizeDashboardCount(summary.iteration_suggestions),
      jenkinsReleases: normalizeDashboardCount(summary.jenkins_releases),
      knowledgeDeposits: normalizeDashboardCount(summary.knowledge_deposits),
      knowledgeDocuments: normalizeDashboardCount(summary.knowledge_documents),
      onlineErrors: normalizeDashboardCount(summary.online_errors),
      openBugs: normalizeDashboardCount(summary.open_bugs),
      pendingReviews: normalizeDashboardCount(summary.pending_reviews),
      requirements: normalizeDashboardCount(summary.requirements),
      usageEvents: normalizeDashboardCount(summary.usage_events),
      userFeedback: normalizeDashboardCount(summary.user_feedback),
    },
    taskStatusCounts: mapDashboardStatusCounts(dashboard.task_status_counts),
    timeRange: formatUnknownValue(dashboard.time_range),
    trend: mapDashboardTrend(dashboard.trend),
    usageMetricSummary: {
      activeUsers: normalizeDashboardCount(usageMetricSummary.active_users),
      conversionCount: normalizeDashboardCount(usageMetricSummary.conversion_count),
      errorCount: normalizeDashboardCount(usageMetricSummary.error_count),
      eventCount: normalizeDashboardCount(usageMetricSummary.event_count),
      metricCount: normalizeDashboardCount(usageMetricSummary.metric_count),
    },
    userFeedbackStatusCounts: mapDashboardStatusCounts(dashboard.user_feedback_status_counts),
  };
}
