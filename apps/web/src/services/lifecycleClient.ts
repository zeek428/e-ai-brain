import type {
  BugRecord,
  ProductVersionBranchConfigRecord,
  RequirementRecord,
} from '../data/management';
import { formatDisplayDateTime } from '../utils/dateTime';
import { apiRequest } from './apiClient';
import { requireAccessToken } from './authClient';
import { mapBugRecord, type BugListItem } from './bugClient';
import type { CodeInspectionReportRecord } from './codeInspectionClient';
import type { ExecutionTraceListItem } from './diagnosticsClient';
import {
  mapKnowledgeDeposit,
  type KnowledgeDepositListItem,
  type KnowledgeDepositRecord,
} from './knowledgeClient';
import { mapRequirementRecord, type RequirementListItem } from './requirementClient';
import { mapTaskRecord, type TaskCenterTaskRecord, type TaskListItem } from './taskCenterClient';

type CodeReviewDiffTreeItem = {
  additions: number;
  deletions: number;
  fileCount: number;
  path: string;
};

type CodeReviewRiskSummary = {
  fileCount?: number;
  largestFile?: {
    additions?: number;
    deletions?: number;
    lineCount?: number;
    path?: string;
  } | null;
  riskLevel?: string;
  totalAdditions?: number;
  totalChangedLines?: number;
  totalDeletions?: number;
};

type CodeReviewDiffChangeSummary = {
  addedFiles?: string[];
  addedFilesCount?: number;
  modifiedFiles?: string[];
  modifiedFilesCount?: number;
  removedFiles?: string[];
  removedFilesCount?: number;
};

type CodeReviewPreviousSnapshot = {
  createdAt?: string;
  headSha?: string;
  id?: string;
  snapshotHash?: string;
};

type GitLabMergeRequestSnapshot = {
  changedFilesSummary: unknown[];
  createdAt?: string;
  diffChangeSummary?: CodeReviewDiffChangeSummary;
  diffLimitBytes?: number;
  diffFileTree: CodeReviewDiffTreeItem[];
  diffSizeBytes?: number;
  id: string;
  mrIid: number;
  previousSnapshot?: CodeReviewPreviousSnapshot | null;
  reviewChecklist: string[];
  repositoryId: string;
  riskSummary?: CodeReviewRiskSummary;
  snapshotReused?: boolean;
};

type CodeReviewReportRecord = {
  executor?: unknown;
  findings: unknown[];
  gitlabWritebackPerformed: boolean;
  id: string;
  riskLevel: string;
  status: string;
  summary: string;
  writebackTemplate?: {
    body: string;
    format: string;
    title: string;
    writebackAllowed: boolean;
    writebackReason: string;
  };
};

export type RequirementFullChainTimelineItem = {
  occurredAt: string;
  occurredAtValue?: string;
  status?: string;
  subjectId: string;
  title: string;
  type: string;
};

export type RequirementFullChainAuditEvent = {
  actorId?: string;
  aiTaskId?: string;
  createdAt: string;
  eventType: string;
  id: string;
  subjectId?: string;
  subjectType?: string;
};

export type RequirementFullChainSummary = {
  aiTasks: number;
  auditEvents: number;
  branchConfigs: number;
  bugs: number;
  codeInspectionReports: number;
  codeReviewReports: number;
  executionTraces: number;
  gitSnapshots: number;
  jenkinsReleases: number;
  knowledgeDeposits: number;
  reviews: number;
  timelineEvents: number;
};

export type RequirementFullChainRecord = {
  aiTasks: TaskCenterTaskRecord[];
  anchor?: {
    resolvedRequirementId?: string;
    subjectId?: string;
    subjectType?: string;
  };
  bugs: BugRecord[];
  auditEvents: RequirementFullChainAuditEvent[];
  branchConfigs: ProductVersionBranchConfigRecord[];
  codeInspectionReports: CodeInspectionReportRecord[];
  codeReviewReports: CodeReviewReportRecord[];
  executionTraces: ExecutionTraceListItem[];
  gitSnapshots: GitLabMergeRequestSnapshot[];
  iterationVersion?: {
    code?: string;
    id: string;
    name?: string;
    status?: string;
  };
  jenkinsReleases: Array<{
    buildId?: string;
    createdAt: string;
    id: string;
    jobName?: string;
    status: string;
  }>;
  knowledgeDeposits: KnowledgeDepositRecord[];
  product?: {
    code?: string;
    id: string;
    name?: string;
  };
  requirement: RequirementRecord;
  reviews: Array<{
    aiTaskId?: string;
    createdAt: string;
    id: string;
    status: string;
  }>;
  status: string;
  summary: RequirementFullChainSummary;
  timeline: RequirementFullChainTimelineItem[];
};

type FlexibleListItem = Record<string, unknown> & {
  created_at?: string;
  id?: string;
  status?: string;
  updated_at?: string;
};

type ProductResponse = {
  code?: string;
  description?: string | null;
  id: string;
  name?: string;
  owner_team?: string | null;
  status?: string;
};

type ProductVersionListItem = {
  code?: string;
  id: string;
  name?: string;
  product_id: string;
  status?: string;
};

type ProductVersionBranchConfigListItem = {
  base_branch?: string;
  branch_status?: string;
  creation_source?: string;
  description?: string | null;
  id: string;
  product_id: string;
  repository_default_branch?: string | null;
  repository_id: string;
  repository_name?: string | null;
  repository_path?: string | null;
  repository_provider?: string | null;
  version_id: string;
  working_branch?: string;
};

type GitLabMergeRequestPreviewResponse = {
  diff_file_tree?: Array<{
    additions?: number;
    deletions?: number;
    file_count?: number;
    path?: string;
  }>;
  risk_summary?: {
    file_count?: number;
    largest_file?: {
      additions?: number;
      deletions?: number;
      line_count?: number;
      path?: string;
    } | null;
    risk_level?: string;
    total_additions?: number;
    total_changed_lines?: number;
    total_deletions?: number;
  };
};

type GitLabMergeRequestSnapshotResponse = {
  changed_files_summary?: unknown[];
  created_at?: string;
  diff_change_summary?: {
    added_files?: string[];
    added_files_count?: number;
    modified_files?: string[];
    modified_files_count?: number;
    removed_files?: string[];
    removed_files_count?: number;
  };
  diff_file_tree?: GitLabMergeRequestPreviewResponse['diff_file_tree'];
  diff_limit_bytes?: number;
  diff_size_bytes?: number;
  id: string;
  mr_iid: number;
  previous_snapshot?: {
    created_at?: string;
    head_sha?: string;
    id?: string;
    snapshot_hash?: string;
  } | null;
  review_checklist?: string[];
  repository_id: string;
  risk_summary?: GitLabMergeRequestPreviewResponse['risk_summary'];
  snapshot_reused?: boolean;
};

type CodeReviewReportResponse = {
  executor?: unknown;
  findings?: unknown[];
  gitlab_writeback_performed?: boolean;
  id: string;
  risk_level?: string;
  status?: string;
  summary?: string;
  writeback_template?: {
    body?: string;
    format?: string;
    title?: string;
    writeback_allowed?: boolean;
    writeback_reason?: string;
  };
};

type PendingReviewListItem = {
  ai_task_id: string;
  created_at?: string;
  id: string;
  status?: string;
};

type RequirementFullChainTimelineItemResponse = {
  occurred_at?: string;
  status?: string | null;
  subject_id?: string;
  title?: string;
  type?: string;
};

type RequirementFullChainResponse = {
  ai_tasks?: TaskListItem[];
  audit_events?: FlexibleListItem[];
  anchor?: {
    resolved_requirement_id?: string;
    subject_id?: string;
    subject_type?: string;
  };
  bugs?: BugListItem[];
  branch_configs?: ProductVersionBranchConfigListItem[];
  code_inspection_reports?: CodeInspectionReportRecord[];
  code_review_reports?: CodeReviewReportResponse[];
  execution_traces?: ExecutionTraceListItem[];
  git_snapshots?: GitLabMergeRequestSnapshotResponse[];
  iteration_version?: ProductVersionListItem | null;
  jenkins_releases?: FlexibleListItem[];
  knowledge_deposits?: KnowledgeDepositListItem[];
  product?: ProductResponse | null;
  requirement: RequirementListItem;
  reviews?: PendingReviewListItem[];
  status?: string;
  summary?: Partial<{
    ai_tasks: number;
    audit_events: number;
    branch_configs: number;
    bugs: number;
    code_inspection_reports: number;
    code_review_reports: number;
    execution_traces: number;
    git_snapshots: number;
    jenkins_releases: number;
    knowledge_deposits: number;
    reviews: number;
    timeline_events: number;
  }>;
  timeline?: RequirementFullChainTimelineItemResponse[];
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

function emptyToUndefined(value: string) {
  return value === '-' ? undefined : value;
}

function normalizeDashboardCount(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function normalizeDiffFileTree(
  items?: GitLabMergeRequestPreviewResponse['diff_file_tree'],
): CodeReviewDiffTreeItem[] {
  return (items ?? []).map((item) => ({
    additions: item.additions ?? 0,
    deletions: item.deletions ?? 0,
    fileCount: item.file_count ?? 0,
    path: item.path ?? '-',
  }));
}

function normalizeRiskSummary(
  summary?: GitLabMergeRequestPreviewResponse['risk_summary'],
): CodeReviewRiskSummary | undefined {
  if (!summary) {
    return undefined;
  }
  return {
    fileCount: summary.file_count,
    largestFile: summary.largest_file
      ? {
          additions: summary.largest_file.additions,
          deletions: summary.largest_file.deletions,
          lineCount: summary.largest_file.line_count,
          path: summary.largest_file.path,
        }
      : null,
    riskLevel: summary.risk_level,
    totalAdditions: summary.total_additions,
    totalChangedLines: summary.total_changed_lines,
    totalDeletions: summary.total_deletions,
  };
}

function normalizeProductVersionBranchStatus(
  status?: string,
): ProductVersionBranchConfigRecord['branchStatus'] {
  const allowed = new Set(['active', 'archived', 'merged', 'not_created', 'released', 'testing']);
  return allowed.has(status ?? '')
    ? (status as ProductVersionBranchConfigRecord['branchStatus'])
    : 'not_created';
}

function normalizeProductVersionBranchCreationSource(
  source?: string,
): ProductVersionBranchConfigRecord['creationSource'] {
  const allowed = new Set(['ai_task', 'github_sync', 'gitlab_sync', 'manual']);
  return allowed.has(source ?? '')
    ? (source as ProductVersionBranchConfigRecord['creationSource'])
    : 'manual';
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

function mapRequirementFullChain(
  chain: RequirementFullChainResponse,
): RequirementFullChainRecord {
  const summary = chain.summary ?? {};
  return {
    aiTasks: (chain.ai_tasks ?? []).map(mapTaskRecord),
    anchor: chain.anchor
      ? {
          resolvedRequirementId: chain.anchor.resolved_requirement_id,
          subjectId: chain.anchor.subject_id,
          subjectType: chain.anchor.subject_type,
        }
      : undefined,
    bugs: (chain.bugs ?? []).map(mapBugRecord),
    auditEvents: (chain.audit_events ?? []).map((event) => ({
      actorId: emptyToUndefined(formatUnknownValue(event.actor_id)),
      aiTaskId: emptyToUndefined(formatUnknownValue(event.ai_task_id)),
      createdAt: formatListDate(formatUnknownValue(event.created_at)),
      eventType: formatUnknownValue(event.event_type),
      id: formatUnknownValue(event.id),
      subjectId: emptyToUndefined(formatUnknownValue(event.subject_id)),
      subjectType: emptyToUndefined(formatUnknownValue(event.subject_type)),
    })),
    branchConfigs: (chain.branch_configs ?? []).map(mapProductVersionBranchConfigRecord),
    codeInspectionReports: chain.code_inspection_reports ?? [],
    codeReviewReports: (chain.code_review_reports ?? []).map((report) => ({
      executor: report.executor,
      findings: report.findings ?? [],
      gitlabWritebackPerformed: report.gitlab_writeback_performed ?? false,
      id: report.id,
      riskLevel: report.risk_level ?? '-',
      status: report.status ?? '-',
      summary: report.summary ?? report.id,
    })),
    executionTraces: chain.execution_traces ?? [],
    gitSnapshots: (chain.git_snapshots ?? []).map((snapshot) => ({
      changedFilesSummary: snapshot.changed_files_summary ?? [],
      createdAt: formatListDate(snapshot.created_at),
      diffLimitBytes: snapshot.diff_limit_bytes,
      diffFileTree: normalizeDiffFileTree(snapshot.diff_file_tree),
      diffSizeBytes: snapshot.diff_size_bytes,
      id: snapshot.id,
      mrIid: snapshot.mr_iid,
      reviewChecklist: snapshot.review_checklist ?? [],
      repositoryId: snapshot.repository_id,
      riskSummary: normalizeRiskSummary(snapshot.risk_summary),
    })),
    iterationVersion: chain.iteration_version
      ? {
          code: chain.iteration_version.code,
          id: chain.iteration_version.id,
          name: chain.iteration_version.name,
          status: chain.iteration_version.status,
        }
      : undefined,
    jenkinsReleases: (chain.jenkins_releases ?? []).map((release) => ({
      buildId: formatUnknownValue(release.build_id),
      createdAt: formatListDate(formatUnknownValue(
        release.deployed_at ?? release.started_at ?? release.created_at,
      )),
      id: formatUnknownValue(release.id),
      jobName: formatUnknownValue(release.job_name),
      status: formatUnknownValue(release.status),
    })),
    knowledgeDeposits: (chain.knowledge_deposits ?? []).map(mapKnowledgeDeposit),
    product: chain.product
      ? {
          code: chain.product.code,
          id: chain.product.id,
          name: chain.product.name,
        }
      : undefined,
    requirement: mapRequirementRecord(chain.requirement),
    reviews: (chain.reviews ?? []).map((review) => ({
      aiTaskId: review.ai_task_id,
      createdAt: formatListDate(formatUnknownValue(review.created_at)),
      id: review.id,
      status: review.status ?? '-',
    })),
    status: chain.status ?? 'available',
    summary: {
      aiTasks: normalizeDashboardCount(summary.ai_tasks),
      auditEvents: normalizeDashboardCount(summary.audit_events),
      branchConfigs: normalizeDashboardCount(summary.branch_configs),
      bugs: normalizeDashboardCount(summary.bugs),
      codeInspectionReports: normalizeDashboardCount(summary.code_inspection_reports),
      codeReviewReports: normalizeDashboardCount(summary.code_review_reports),
      executionTraces: normalizeDashboardCount(summary.execution_traces),
      gitSnapshots: normalizeDashboardCount(summary.git_snapshots),
      jenkinsReleases: normalizeDashboardCount(summary.jenkins_releases),
      knowledgeDeposits: normalizeDashboardCount(summary.knowledge_deposits),
      reviews: normalizeDashboardCount(summary.reviews),
      timelineEvents: normalizeDashboardCount(summary.timeline_events),
    },
    timeline: (chain.timeline ?? []).map((item) => ({
      occurredAt: formatListDate(item.occurred_at),
      occurredAtValue: item.occurred_at,
      status: item.status ?? undefined,
      subjectId: item.subject_id ?? '-',
      title: item.title ?? item.subject_id ?? '-',
      type: item.type ?? '-',
    })),
  };
}

export async function fetchRequirementFullChain(
  requirementId: string,
): Promise<RequirementFullChainRecord> {
  const token = requireAccessToken();
  const chain = await apiRequest<RequirementFullChainResponse>(
    `/api/requirements/${requirementId}/full-chain`,
    { token },
  );

  return mapRequirementFullChain(chain);
}

export async function fetchLifecycleFullChain(
  subjectType: string,
  subjectId: string,
): Promise<RequirementFullChainRecord> {
  const token = requireAccessToken();
  const params = new URLSearchParams({
    subject_id: subjectId,
    subject_type: subjectType,
  });
  const chain = await apiRequest<RequirementFullChainResponse>(
    `/api/lifecycle/full-chain?${params.toString()}`,
    { token },
  );

  return mapRequirementFullChain(chain);
}

export function fullChainSubjectHref(subjectType: string, subjectId: string) {
  const params = new URLSearchParams({
    subject_id: subjectId,
    subject_type: subjectType,
  });
  return `/delivery/full-chain?${params.toString()}`;
}
