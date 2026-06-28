import {
  apiRequest,
  appendQueryParam,
} from './apiClient';
import type { ListResponse, RemoteListPerformance } from './apiClient';
import { requireAccessToken } from './authClient';

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

type CodeInspectionListResult = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: CodeInspectionReportRecord[];
  total: number;
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
): Promise<CodeInspectionListResult> {
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
    performance: response.performance,
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
      body: {
        note: payload.note,
        reason: payload.reason ?? 'false_positive',
      },
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
      body: payload,
      method: 'POST',
      token,
    },
  );
}
