import type {
  BugRecord,
  ProductVersionBranchConfigRecord,
  ProductVersionRecord,
  RequirementRecord,
} from '../data/management';
import { formatDisplayDateTime } from '../utils/dateTime';
import { apiRequest } from './apiClient';
import { requireAccessToken } from './authClient';

type ProductVersionListItem = {
  code?: string;
  created_at?: string | null;
  description?: string | null;
  id: string;
  name: string;
  product_code?: string;
  product_id: string;
  product_name?: string;
  release_date?: string | null;
  start_date?: string | null;
  status?: string;
  updated_at?: string | null;
};

type ProductVersionBranchConfigListItem = {
  base_branch?: string | null;
  branch_status?: string | null;
  creation_source?: string | null;
  description?: string | null;
  id: string;
  product_id: string;
  repository_default_branch?: string | null;
  repository_id: string;
  repository_name?: string | null;
  repository_path?: string | null;
  repository_provider?: string | null;
  version_id: string;
  working_branch?: string | null;
};

type RequirementListItem = {
  assignee?: string;
  content?: string;
  created_at?: string;
  created_by?: string;
  id: string;
  module_code?: string;
  priority?: string;
  product_code?: string;
  product_id?: string;
  product_name?: string;
  source?: string;
  status?: string;
  title: string;
  updated_at?: string;
  version_code?: string;
  version_id?: string;
  version_name?: string;
};

type BugListItem = {
  assignee?: string;
  created_at?: string;
  description?: string;
  duplicate_of_bug_id?: string | null;
  evidence?: unknown;
  id: string;
  module_code?: string;
  product_id?: string;
  related_task_id?: string | null;
  reproduce_steps?: unknown;
  requirement_id?: string | null;
  severity?: string;
  source?: string;
  status?: string;
  title: string;
  version_code?: string;
  version_id?: string | null;
  version_name?: string;
};

type ProductVersionDashboardTaskItem = {
  created_at?: string;
  created_by?: string;
  current_step?: string | null;
  id: string;
  product_id?: string;
  product_name?: string;
  requirement_id?: string;
  status?: string;
  task_type?: string;
  title?: string;
  updated_at?: string;
};

type ProductVersionDashboardCodeInspectionReport = {
  branch?: string | null;
  created_at?: string;
  finding_count: number;
  id: string;
  repository_name?: string | null;
  risk_level: string;
  summary?: string;
};

type ProductVersionDashboardBranchQualityGovernanceItem = {
  branch?: string | null;
  branch_config_id?: string | null;
  created_bug_count?: number;
  created_task_count?: number;
  finding_count?: number;
  id: string;
  latest_report_id?: string | null;
  latest_report_summary?: string | null;
  latest_report_time?: string | null;
  quality_gate_failed_report_count?: number;
  quality_gate_violation_count?: number;
  report_count?: number;
  repository_id?: string | null;
  repository_name?: string | null;
  severe_finding_count?: number;
  status?: string;
  uncovered_severe_bug_count?: number;
  uncovered_severe_task_count?: number;
};

type ProductVersionDashboardCodeReviewReport = {
  archived_at?: string | null;
  executor?: { name?: string; type?: string } | null;
  finding_count?: number;
  gitlab_mr_snapshot_id?: string | null;
  gitlab_writeback_performed?: boolean;
  id: string;
  review_id?: string | null;
  risk_level?: string;
  status?: string;
  summary?: string;
  task_id?: string | null;
  task_title?: string | null;
};

type ProductVersionDashboardReleaseItem = {
  build_id?: unknown;
  created_at?: unknown;
  deployed_at?: unknown;
  id?: unknown;
  job_name?: unknown;
  started_at?: unknown;
  status?: unknown;
};

type ProductVersionDashboardKnowledgeDepositItem = {
  ai_task_id?: string | null;
  id: string;
  knowledge_chunk_count?: number;
  knowledge_document_id?: string | null;
  knowledge_document_title?: string | null;
  knowledge_embedding_chunk_count?: number;
  knowledge_index_error?: string | null;
  knowledge_index_status?: string | null;
  knowledge_retrieval_mode?: string | null;
  status?: string;
  task_title?: string | null;
  title?: string;
  updated_at?: string | null;
};

type ProductVersionDashboardBlockerItem = {
  action_label?: string;
  action_target_id?: string;
  action_target_type?: string;
  id?: string;
  reason?: string;
  resolution_hint?: string;
  severity?: string;
  source_type?: string;
  title?: string;
};

type ProductVersionDashboardAccessIssue = {
  code?: string;
  message?: string;
  section?: string;
};

type ProductVersionDashboardSummary = {
  blockers: number;
  branch_configs: number;
  branch_quality_action_required: number;
  branch_quality_pending_scan: number;
  bugs: number;
  code_inspection_reports: number;
  code_review_reports: number;
  knowledge_deposits: number;
  open_bugs: number;
  pending_code_review_reports: number;
  releases: number;
  requirements: number;
  searchable_knowledge_deposits: number;
  severe_bugs: number;
  severe_code_inspection_reports: number;
  tasks: number;
  vectorized_knowledge_deposits: number;
};

type ProductVersionDashboardStatusCount = {
  count: number;
  status: string;
};

type ProductVersionDashboardRequirementImpact = {
  block_reason?: string;
  from_status?: string;
  id: string;
  status?: string;
  title: string;
  to_status?: string;
};

type ProductVersionDashboardStatusImpactResponse = {
  blocked_requirements?: ProductVersionDashboardRequirementImpact[];
  target_status: string;
  unchanged_requirements?: ProductVersionDashboardRequirementImpact[];
  updated_requirements?: ProductVersionDashboardRequirementImpact[];
};

type ProductVersionDashboardResponse = {
  access_issues?: ProductVersionDashboardAccessIssue[];
  blockers?: ProductVersionDashboardBlockerItem[];
  branch_configs?: ProductVersionBranchConfigListItem[];
  branch_quality_governance?: ProductVersionDashboardBranchQualityGovernanceItem[];
  bug_status_counts?: ProductVersionDashboardStatusCount[];
  bugs?: BugListItem[];
  code_inspection_reports?: ProductVersionDashboardCodeInspectionReport[];
  code_review_reports?: ProductVersionDashboardCodeReviewReport[];
  knowledge_deposits?: ProductVersionDashboardKnowledgeDepositItem[];
  releases?: ProductVersionDashboardReleaseItem[];
  requirement_status_counts?: ProductVersionDashboardStatusCount[];
  requirements?: RequirementListItem[];
  status_impact?: ProductVersionDashboardStatusImpactResponse | null;
  summary?: Partial<ProductVersionDashboardSummary>;
  task_status_counts?: ProductVersionDashboardStatusCount[];
  tasks?: ProductVersionDashboardTaskItem[];
  version: ProductVersionListItem;
};

export type ProductVersionDashboard = {
  accessIssues: Array<{
    code: string;
    message: string;
    section: string;
  }>;
  blockers: Array<{
    actionLabel: string;
    actionTargetId?: string;
    actionTargetType: string;
    id?: string;
    reason: string;
    resolutionHint: string;
    severity: string;
    sourceType: string;
    title: string;
  }>;
  branchConfigs: ProductVersionBranchConfigRecord[];
  branchQualityGovernance: Array<{
    branch: string;
    branchConfigId?: string;
    createdBugCount: number;
    createdTaskCount: number;
    findingCount: number;
    id: string;
    latestReportId?: string;
    latestReportSummary?: string;
    latestReportTime: string;
    qualityGateFailedReportCount: number;
    qualityGateViolationCount: number;
    reportCount: number;
    repositoryId?: string;
    repositoryName: string;
    severeFindingCount: number;
    status: string;
    uncoveredSevereBugCount: number;
    uncoveredSevereTaskCount: number;
  }>;
  bugStatusCounts: ProductVersionDashboardStatusCount[];
  bugs: BugRecord[];
  codeInspectionReports: ProductVersionDashboardCodeInspectionReport[];
  codeReviewReports: Array<{
    executorName: string;
    executorType: string;
    findingCount: number;
    gitlabMrSnapshotId?: string;
    id: string;
    reviewId?: string;
    riskLevel: string;
    status: string;
    summary: string;
    taskId?: string;
    taskTitle: string;
    writebackPerformed: boolean;
  }>;
  knowledgeDeposits: Array<{
    aiTaskId?: string;
    id: string;
    knowledgeChunkCount: number;
    knowledgeDocumentId?: string;
    knowledgeDocumentTitle?: string;
    knowledgeEmbeddingChunkCount: number;
    knowledgeIndexError?: string;
    knowledgeIndexStatus?: string;
    knowledgeRetrievalMode: string;
    status: string;
    taskTitle: string;
    title: string;
    updatedAt: string;
  }>;
  releases: Array<{
    buildId?: string;
    createdAt: string;
    id: string;
    jobName?: string;
    status: string;
  }>;
  requirementStatusCounts: ProductVersionDashboardStatusCount[];
  requirements: RequirementRecord[];
  statusImpact?: {
    blockedRequirements: ProductVersionDashboardRequirementImpact[];
    targetStatus: ProductVersionRecord['status'];
    unchangedRequirements: ProductVersionDashboardRequirementImpact[];
    updatedRequirements: ProductVersionDashboardRequirementImpact[];
  };
  summary: ProductVersionDashboardSummary;
  taskStatusCounts: ProductVersionDashboardStatusCount[];
  tasks: Array<{
    createdAt: string;
    createdAtValue?: string;
    currentStep?: string;
    id: string;
    label: string;
    owner: string;
    product: string;
    productId?: string;
    requirementId?: string;
    status: string;
    type: string;
  }>;
  version: ProductVersionRecord;
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

function normalizeDashboardCount(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function normalizeProductVersionStatus(status?: string): ProductVersionRecord['status'] {
  if (status === 'archived' || status === 'planning' || status === 'released' || status === 'testing') {
    return status;
  }
  return 'active';
}

function normalizeProductVersionBranchStatus(status?: string | null): ProductVersionBranchConfigRecord['branchStatus'] {
  const allowed = new Set(['active', 'archived', 'merged', 'not_created', 'released', 'testing']);
  return allowed.has(status ?? '') ? (status as ProductVersionBranchConfigRecord['branchStatus']) : 'not_created';
}

function normalizeProductVersionBranchCreationSource(
  source?: string | null,
): ProductVersionBranchConfigRecord['creationSource'] {
  const allowed = new Set(['ai_task', 'github_sync', 'gitlab_sync', 'manual']);
  return allowed.has(source ?? '') ? (source as ProductVersionBranchConfigRecord['creationSource']) : 'manual';
}

function normalizePriority(priority?: string): RequirementRecord['priority'] {
  if (priority === 'P0' || priority === 'P2') {
    return priority;
  }
  return 'P1';
}

function normalizeRequirementStatus(status?: string): RequirementRecord['status'] {
  if (status === 'pending_approval') {
    return 'submitted';
  }
  if (status === 'task_created') {
    return 'designing';
  }
  if (
    status === 'accepted' ||
    status === 'approved' ||
    status === 'cancelled' ||
    status === 'closed' ||
    status === 'code_reviewing' ||
    status === 'deferred' ||
    status === 'designing' ||
    status === 'developing' ||
    status === 'draft' ||
    status === 'planned' ||
    status === 'ready_for_dev' ||
    status === 'ready_for_release' ||
    status === 'rejected' ||
    status === 'released' ||
    status === 'submitted' ||
    status === 'testing'
  ) {
    return status;
  }
  return 'draft';
}

function normalizeBugSeverity(severity?: string): BugRecord['severity'] {
  if (severity === 'blocker' || severity === 'critical' || severity === 'minor') {
    return severity;
  }
  return 'major';
}

function normalizeBugStatus(status?: string): BugRecord['status'] {
  if (
    status === 'assigned' ||
    status === 'closed' ||
    status === 'fixed' ||
    status === 'needs_info' ||
    status === 'open' ||
    status === 'reopened' ||
    status === 'triaged' ||
    status === 'verified'
  ) {
    return status;
  }
  return 'open';
}

function normalizeBugSource(source?: string): BugRecord['source'] {
  if (source === 'ai_auto_test' || source === 'ai_post_release' || source === 'code_inspection') {
    return source;
  }
  return 'manual_test';
}

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => (typeof item === 'string' ? item : (JSON.stringify(item) ?? '')))
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeObjectRecord(value: unknown): Record<string, unknown> | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  return value as Record<string, unknown>;
}

function mapProductVersionRecord(version: ProductVersionListItem): ProductVersionRecord {
  return {
    code: version.code ?? version.id,
    createdAt: formatListDate(version.created_at ?? undefined),
    description: version.description ?? undefined,
    id: version.id,
    name: version.name,
    productCode: version.product_code,
    productId: version.product_id,
    productName: version.product_name,
    releaseDate: version.release_date ?? undefined,
    startDate: version.start_date ?? undefined,
    status: normalizeProductVersionStatus(version.status),
    updatedAt: formatListDate(version.updated_at ?? version.created_at ?? undefined),
  };
}

function mapProductVersionBranchConfigRecord(
  branchConfig: ProductVersionBranchConfigListItem,
): ProductVersionBranchConfigRecord {
  return {
    baseBranch: branchConfig.base_branch ?? branchConfig.repository_default_branch ?? 'main',
    branchStatus: normalizeProductVersionBranchStatus(branchConfig.branch_status),
    creationSource: normalizeProductVersionBranchCreationSource(branchConfig.creation_source),
    description: branchConfig.description,
    id: branchConfig.id,
    productId: branchConfig.product_id,
    repositoryDefaultBranch: branchConfig.repository_default_branch,
    repositoryId: branchConfig.repository_id,
    repositoryName: branchConfig.repository_name,
    repositoryPath: branchConfig.repository_path,
    repositoryProvider: branchConfig.repository_provider,
    versionId: branchConfig.version_id,
    workingBranch: branchConfig.working_branch ?? '-',
  };
}

function mapRequirementRecord(requirement: RequirementListItem): RequirementRecord {
  return {
    content: requirement.content,
    createdAt: formatListDate(requirement.created_at),
    id: requirement.id,
    moduleCode: requirement.module_code ?? undefined,
    owner: requirement.assignee ?? requirement.created_by ?? '-',
    priority: normalizePriority(requirement.priority),
    product: requirement.product_code ?? requirement.product_name ?? requirement.product_id ?? '-',
    productId: requirement.product_id,
    source: requirement.source ?? 'business_department',
    status: normalizeRequirementStatus(requirement.status),
    title: requirement.title,
    updatedAt: formatListDate(requirement.updated_at ?? requirement.created_at),
    versionId: requirement.version_id,
    versionName: requirement.version_id
      ? (requirement.version_name ?? requirement.version_code ?? requirement.version_id)
      : '未排期',
  };
}

function mapBugRecord(bug: BugListItem): BugRecord {
  return {
    assignee: bug.assignee ?? '-',
    createdAt: formatListDate(bug.created_at),
    description: bug.description,
    duplicateOfBugId: bug.duplicate_of_bug_id ?? undefined,
    evidence: normalizeObjectRecord(bug.evidence),
    id: bug.id,
    module: bug.module_code ?? '-',
    productId: bug.product_id,
    relatedTaskId: bug.related_task_id ?? undefined,
    reproduceSteps: normalizeStringList(bug.reproduce_steps),
    requirementId: bug.requirement_id ?? undefined,
    severity: normalizeBugSeverity(bug.severity),
    source: normalizeBugSource(bug.source),
    status: normalizeBugStatus(bug.status),
    title: bug.title,
    versionId: bug.version_id ?? undefined,
    versionName: bug.version_id ? formatUnknownValue(bug.version_name ?? bug.version_code ?? bug.version_id) : '未关联',
  };
}

function mapTaskRecord(task: ProductVersionDashboardTaskItem): ProductVersionDashboard['tasks'][number] {
  return {
    createdAt: formatListDate(task.created_at ?? task.updated_at),
    createdAtValue: task.created_at ?? task.updated_at,
    currentStep: task.current_step ?? undefined,
    id: task.id,
    label: task.title ?? task.task_type ?? task.id,
    owner: task.created_by ?? '-',
    product: task.product_name ?? task.product_id ?? '-',
    productId: task.product_id,
    requirementId: task.requirement_id,
    status: task.status ?? '-',
    type: task.task_type ?? '-',
  };
}

function mapProductVersionDashboard(dashboard: ProductVersionDashboardResponse): ProductVersionDashboard {
  const summary = dashboard.summary ?? {};
  const statusImpact = dashboard.status_impact
    ? {
        blockedRequirements: dashboard.status_impact.blocked_requirements ?? [],
        targetStatus: normalizeProductVersionStatus(dashboard.status_impact.target_status),
        unchangedRequirements: dashboard.status_impact.unchanged_requirements ?? [],
        updatedRequirements: dashboard.status_impact.updated_requirements ?? [],
      }
    : undefined;
  return {
    accessIssues: (dashboard.access_issues ?? []).map((issue) => ({
      code: issue.code ?? '-',
      message: issue.message ?? '-',
      section: issue.section ?? '-',
    })),
    blockers: (dashboard.blockers ?? []).map((blocker) => ({
      actionLabel: blocker.action_label ?? '处理',
      actionTargetId: blocker.action_target_id ?? blocker.id,
      actionTargetType: blocker.action_target_type ?? blocker.source_type ?? '-',
      id: blocker.id,
      reason: blocker.reason ?? '-',
      resolutionHint: blocker.resolution_hint ?? '打开关联对象并处理阻塞原因。',
      severity: blocker.severity ?? 'medium',
      sourceType: blocker.source_type ?? '-',
      title: blocker.title ?? blocker.id ?? '-',
    })),
    branchConfigs: (dashboard.branch_configs ?? []).map(mapProductVersionBranchConfigRecord),
    branchQualityGovernance: (dashboard.branch_quality_governance ?? []).map((item) => ({
      branch: item.branch ?? '-',
      branchConfigId: item.branch_config_id ?? undefined,
      createdBugCount: normalizeDashboardCount(item.created_bug_count),
      createdTaskCount: normalizeDashboardCount(item.created_task_count),
      findingCount: normalizeDashboardCount(item.finding_count),
      id: item.id,
      latestReportId: item.latest_report_id ?? undefined,
      latestReportSummary: item.latest_report_summary ?? undefined,
      latestReportTime: formatListDate(item.latest_report_time ?? undefined),
      qualityGateFailedReportCount: normalizeDashboardCount(item.quality_gate_failed_report_count),
      qualityGateViolationCount: normalizeDashboardCount(item.quality_gate_violation_count),
      reportCount: normalizeDashboardCount(item.report_count),
      repositoryId: item.repository_id ?? undefined,
      repositoryName: item.repository_name ?? item.repository_id ?? '-',
      severeFindingCount: normalizeDashboardCount(item.severe_finding_count),
      status: item.status ?? '-',
      uncoveredSevereBugCount: normalizeDashboardCount(item.uncovered_severe_bug_count),
      uncoveredSevereTaskCount: normalizeDashboardCount(item.uncovered_severe_task_count),
    })),
    bugStatusCounts: dashboard.bug_status_counts ?? [],
    bugs: (dashboard.bugs ?? []).map(mapBugRecord),
    codeInspectionReports: dashboard.code_inspection_reports ?? [],
    codeReviewReports: (dashboard.code_review_reports ?? []).map((report) => ({
      executorName: formatUnknownValue(report.executor?.name),
      executorType: formatUnknownValue(report.executor?.type),
      findingCount: normalizeDashboardCount(report.finding_count),
      gitlabMrSnapshotId: report.gitlab_mr_snapshot_id ?? undefined,
      id: report.id,
      reviewId: report.review_id ?? undefined,
      riskLevel: report.risk_level ?? '-',
      status: report.status ?? '-',
      summary: report.summary ?? report.id,
      taskId: report.task_id ?? undefined,
      taskTitle: report.task_title ?? report.task_id ?? '-',
      writebackPerformed: Boolean(report.gitlab_writeback_performed),
    })),
    knowledgeDeposits: (dashboard.knowledge_deposits ?? []).map((deposit) => ({
      aiTaskId: deposit.ai_task_id ?? undefined,
      id: deposit.id,
      knowledgeChunkCount: normalizeDashboardCount(deposit.knowledge_chunk_count),
      knowledgeDocumentId: deposit.knowledge_document_id ?? undefined,
      knowledgeDocumentTitle: deposit.knowledge_document_title ?? undefined,
      knowledgeEmbeddingChunkCount: normalizeDashboardCount(deposit.knowledge_embedding_chunk_count),
      knowledgeIndexError: deposit.knowledge_index_error ?? undefined,
      knowledgeIndexStatus: deposit.knowledge_index_status ?? undefined,
      knowledgeRetrievalMode: deposit.knowledge_retrieval_mode ?? 'unavailable',
      status: deposit.status ?? '-',
      taskTitle: deposit.task_title ?? deposit.ai_task_id ?? '-',
      title: deposit.title ?? deposit.id,
      updatedAt: formatListDate(deposit.updated_at ?? undefined),
    })),
    releases: (dashboard.releases ?? []).map((release) => ({
      buildId: formatUnknownValue(release.build_id),
      createdAt: formatListDate(formatUnknownValue(release.deployed_at ?? release.started_at ?? release.created_at)),
      id: formatUnknownValue(release.id),
      jobName: formatUnknownValue(release.job_name),
      status: formatUnknownValue(release.status),
    })),
    requirementStatusCounts: dashboard.requirement_status_counts ?? [],
    requirements: (dashboard.requirements ?? []).map(mapRequirementRecord),
    statusImpact,
    summary: {
      blockers: normalizeDashboardCount(summary.blockers),
      branch_configs: normalizeDashboardCount(summary.branch_configs),
      branch_quality_action_required: normalizeDashboardCount(summary.branch_quality_action_required),
      branch_quality_pending_scan: normalizeDashboardCount(summary.branch_quality_pending_scan),
      bugs: normalizeDashboardCount(summary.bugs),
      code_inspection_reports: normalizeDashboardCount(summary.code_inspection_reports),
      code_review_reports: normalizeDashboardCount(summary.code_review_reports),
      knowledge_deposits: normalizeDashboardCount(summary.knowledge_deposits),
      open_bugs: normalizeDashboardCount(summary.open_bugs),
      pending_code_review_reports: normalizeDashboardCount(summary.pending_code_review_reports),
      releases: normalizeDashboardCount(summary.releases),
      requirements: normalizeDashboardCount(summary.requirements),
      searchable_knowledge_deposits: normalizeDashboardCount(summary.searchable_knowledge_deposits),
      severe_bugs: normalizeDashboardCount(summary.severe_bugs),
      severe_code_inspection_reports: normalizeDashboardCount(summary.severe_code_inspection_reports),
      tasks: normalizeDashboardCount(summary.tasks),
      vectorized_knowledge_deposits: normalizeDashboardCount(summary.vectorized_knowledge_deposits),
    },
    taskStatusCounts: dashboard.task_status_counts ?? [],
    tasks: (dashboard.tasks ?? []).map(mapTaskRecord),
    version: mapProductVersionRecord(dashboard.version),
  };
}

export async function fetchProductVersionDashboard(versionId: string): Promise<ProductVersionDashboard> {
  const token = requireAccessToken();
  const dashboard = await apiRequest<ProductVersionDashboardResponse>(`/api/product-versions/${versionId}/dashboard`, {
    token,
  });
  return mapProductVersionDashboard(dashboard);
}
