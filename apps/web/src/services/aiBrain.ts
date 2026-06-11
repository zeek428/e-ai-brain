import type {
  AuditRecord,
  BugRecord,
  KnowledgeRecord,
  ModelGatewayConfigRecord,
  ProductContextOption,
  ProductGitRepositoryRecord,
  ProductModuleRecord,
  ProductRecord,
  ProductRelatedSystemRecord,
  ProductVersionBranchConfigRecord,
  ProductVersionOption,
  ProductVersionRecord,
  RequirementRecord,
  UserRecord,
} from '../data/management';
import { formatUserRoles, type UserRoleDefinition } from '../data/roles';
import { navigateTo } from '../utils/navigation';

const configuredApiBaseUrl = process.env.UMI_APP_API_BASE_URL ?? '';
const API_BASE_URL = configuredApiBaseUrl.endsWith('/')
  ? configuredApiBaseUrl.slice(0, -1)
  : configuredApiBaseUrl;

type ApiEnvelope<T> = {
  data: T;
};

type ApiErrorPayload = {
  detail?: {
    code?: string;
    message?: string;
    trace_id?: string;
  };
};

type ListResponse<T> = {
  items: T[];
  page?: number;
  page_size?: number;
  total: number;
};

const PRODUCT_CONTEXT_PAGE_SIZE = 100;
const VERSION_CONTEXT_PAGE_SIZE = 100;

const ACCESS_TOKEN_STORAGE_KEY = 'ai_brain_access_token';
const CURRENT_USER_STORAGE_KEY = 'ai_brain_current_user';
export const AUTH_STATE_EVENT = 'ai-brain-auth-state-changed';

function emitAuthStateChanged() {
  if (typeof globalThis.dispatchEvent !== 'function' || typeof Event !== 'function') {
    return;
  }
  globalThis.dispatchEvent(new Event(AUTH_STATE_EVENT));
}

export class ApiRequestError extends Error {
  code?: string;
  status: number;
  traceId?: string;

  constructor({
    code,
    message,
    status,
    traceId,
  }: {
    code?: string;
    message: string;
    status: number;
    traceId?: string;
  }) {
    super(message);
    this.name = 'ApiRequestError';
    this.code = code;
    this.status = status;
    this.traceId = traceId;
  }
}

export type LoginResponse = {
  access_token: string;
  user: CurrentUserResponse;
};

export type CurrentUserResponse = {
  display_name: string;
  id: string;
  menu_tree?: MenuTreeNode[];
  permissions?: string[];
  route_permissions?: Record<string, string[]>;
  roles: string[];
  scope_summary?: ScopeGrant[];
  username: string;
};

export type MenuTreeNode = {
  children?: MenuTreeNode[];
  code: string;
  name: string;
  path?: string | null;
};

export type ScopeGrant = {
  access_level: string;
  scope_id: string;
  scope_type: string;
};

export type PermissionRecord = {
  category?: string;
  code: string;
  description?: string;
  is_system?: boolean;
  name: string;
  risk_level?: string;
  status?: string;
};

export type MenuResourceRecord = {
  code: string;
  menu_type?: string;
  name: string;
  parent_code?: string | null;
  path?: string | null;
  required_permissions?: string[];
  sort_order?: number;
  status?: string;
};

export type SystemRoleRecord = UserRoleDefinition & {
  id: string;
  is_system: boolean;
  menu_codes: string[];
  permission_codes: string[];
  scopes: ScopeGrant[];
};

export type AssistantChatResponse = {
  content: string;
  conversationId: string;
  latencyMs: number;
  messageId: string;
  model: string;
  references: AssistantReference[];
  suggestions: string[];
};

export type AssistantReference = {
  id: string;
  title: string;
  type: string;
  url: string;
};

export type AssistantConversationSummary = {
  createdAt?: string;
  id: string;
  lastMessageAt?: string;
  messageCount: number;
  productId?: string;
  title: string;
  updatedAt?: string;
};

export type AssistantConversationMessage = {
  content: string;
  createdAt?: string;
  id: string;
  model?: string;
  productId?: string;
  role: 'assistant' | 'user';
  references: AssistantReference[];
  suggestions: string[];
};

type AssistantChatApiResponse = {
  conversation_id: string;
  latency_ms?: number;
  message: {
    content?: string;
    id?: string;
    references?: AssistantReference[];
    role?: string;
  };
  model?: string;
  references?: AssistantReference[];
  suggestions?: string[];
};

type AssistantConversationApiRecord = {
  created_at?: string;
  id: string;
  last_message_at?: string;
  message_count?: number;
  product_id?: string;
  title?: string;
  updated_at?: string;
};

type AssistantMessageApiRecord = {
  content?: string;
  created_at?: string;
  id?: string;
  model?: string;
  product_id?: string;
  role?: string;
  references?: AssistantReference[];
  suggestions?: string[];
};

export type AssistantChatPayload = {
  context?: Record<string, unknown>;
  conversationId?: string;
  message: string;
  productId?: string;
};

export type ProductResponse = {
  code?: string;
  description?: string | null;
  id: string;
  name?: string;
  owner_team?: string | null;
  status?: string;
};

export type RequirementResponse = {
  id: string;
  status: string;
};

export type RequirementFullChainTimelineItem = {
  occurredAt: string;
  occurredAtValue?: string;
  status?: string;
  subjectId: string;
  title: string;
  type: string;
};

export type RequirementFullChainSummary = {
  aiTasks: number;
  bugs: number;
  codeReviewReports: number;
  gitSnapshots: number;
  jenkinsReleases: number;
  knowledgeDeposits: number;
  reviews: number;
  timelineEvents: number;
};

export type RequirementFullChainRecord = {
  aiTasks: TaskCenterTaskRecord[];
  bugs: BugRecord[];
  codeReviewReports: CodeReviewReportRecord[];
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

export type TaskCenterTaskRecord = {
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
};

export type TaskCenterTaskQuery = {
  createdFrom?: string;
  createdTo?: string;
  keyword?: string;
  owner?: string;
  page?: number;
  pageSize?: number;
  productId?: string;
  sortField?: string;
  sortOrder?: RemoteSortOrder;
  status?: string;
  taskType?: string;
};

type RemoteSortOrder = 'ascend' | 'descend';

type RemoteListQuery = {
  page?: number;
  pageSize?: number;
  sortField?: string;
  sortOrder?: RemoteSortOrder;
};

export type RequirementListQuery = RemoteListQuery & {
  priority?: string;
  product?: string;
  source?: string;
  status?: string;
  title?: string;
  version?: string;
  versionId?: string;
};

export type ProductListQuery = RemoteListQuery & {
  code?: string;
  name?: string;
  ownerTeam?: string;
  status?: string;
};

export type BugListQuery = RemoteListQuery & {
  module?: string;
  severity?: string;
  status?: string;
  title?: string;
  version?: string;
};

export type BugBatchUpdatePayload = {
  assignee?: string;
  bug_ids: string[];
  reason?: string;
  severity?: string;
  status?: string;
};

export type BugBatchUpdateResult = {
  batchId: string;
  skipped: Array<{ code: string; id: string; message: string }>;
  skippedCount: number;
  updated: BugRecord[];
  updatedCount: number;
};

export type ProductVersionListQuery = RemoteListQuery & {
  code?: string;
  name?: string;
  product?: string;
  status?: string;
};

export type KnowledgeListQuery = RemoteListQuery & {
  documentType?: string;
  folderId?: string;
  keyword?: string;
  knowledgeSpaceId?: string;
  ownerRole?: string;
  status?: string;
};

export type AuditListQuery = RemoteListQuery & {
  actor?: string;
  eventType?: string;
  result?: string;
  subject?: string;
};

export type OperationalMetricListQuery = RemoteListQuery & {
  category?: string;
  name?: string;
  status?: string;
};

export type UserInsightListQuery = RemoteListQuery & {
  category?: string;
  status?: string;
  summary?: string;
};

export type UserListQuery = RemoteListQuery & {
  displayName?: string;
  role?: string;
  status?: string;
  username?: string;
};

export type RoleListQuery = RemoteListQuery & {
  businessRole?: string;
  category?: string;
  menuScope?: string;
  permission?: string;
  role?: string;
  status?: string;
};

export type ModelGatewayConfigListQuery = RemoteListQuery & {
  defaultChatModel?: string;
  defaultEmbeddingModel?: string;
  embeddingConnectionMode?: string;
  isDefault?: string;
  name?: string;
  provider?: string;
  status?: string;
};

export type RemoteListResult<Row> = {
  page: number;
  pageSize: number;
  rows: Row[];
  total: number;
};

export type TaskCenterTaskListResult = {
  page: number;
  pageSize: number;
  rows: TaskCenterTaskRecord[];
  total: number;
};

export type TaskBatchCancelPayload = {
  reason?: string;
  task_ids: string[];
};

export type TaskBatchRetryPayload = {
  reason?: string;
  task_ids: string[];
};

type TaskBatchSkippedItem = {
  code: string;
  id: string;
  message: string;
};

type TaskBatchRetriedItem = {
  current_step?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  id: string;
  review_id?: string | null;
  status: string;
};

type TaskBatchCancelResponse = {
  batch_id: string;
  reason?: string | null;
  skipped: TaskBatchSkippedItem[];
  skipped_count: number;
  updated: Array<{ id: string; status: string }>;
  updated_count: number;
};

type TaskBatchRetryResponse = {
  batch_id: string;
  reason?: string | null;
  retried: TaskBatchRetriedItem[];
  retried_count: number;
  skipped: TaskBatchSkippedItem[];
  skipped_count: number;
  updated: TaskBatchRetriedItem[];
  updated_count: number;
};

export type TaskBatchCancelResult = {
  batchId: string;
  reason?: string | null;
  skipped: TaskBatchSkippedItem[];
  skippedCount: number;
  updated: Array<{ id: string; status: string }>;
  updatedCount: number;
};

export type TaskBatchRetryResult = {
  batchId: string;
  reason?: string | null;
  retried: TaskBatchRetriedItem[];
  retriedCount: number;
  skipped: TaskBatchSkippedItem[];
  skippedCount: number;
  updated: TaskBatchRetriedItem[];
  updatedCount: number;
};

export type TaskCenterTaskDetailRecord = TaskCenterTaskRecord & {
  currentStep: string;
  graphRunIds: string[];
  inputJson: unknown;
  moduleName: string;
  outputJson: unknown;
  outputSummary: string;
  pendingReviewId?: string;
  productName: string;
  requirementTitle: string;
  versionName: string;
};

export type TaskCenterReviewRecord = {
  aiTaskId: string;
  contentSummary: string;
  id: string;
  stage: string;
  status: string;
  version: number;
};

export type TaskMoreInfoAnswer = {
  answer: string;
  question: string;
};

export type OperationalMetricRecord = {
  category: string;
  id: string;
  name: string;
  status: string;
  updatedAt: string;
  value: string;
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

export type GitLabDailyCodeMetricCreatePayload = {
  active_author_count?: number;
  additions?: number;
  author_metrics?: Array<Record<string, unknown>>;
  changed_files?: number;
  commit_count?: number;
  deletions?: number;
  merge_request_count?: number;
  metric_date: string;
  product_id: string;
  quality_score?: number;
  repository_id: string;
  risk_count?: number;
  source_channel?: string;
  status?: string;
};

export type JenkinsReleaseCreatePayload = {
  build_id: string;
  build_number?: number;
  commit_sha?: string;
  deployed_at?: string;
  duration_seconds?: number;
  environment?: string;
  failure_reason?: string;
  job_name: string;
  product_id: string;
  source_channel?: string;
  started_at?: string;
  status?: string;
  trigger_actor?: string;
  version_id: string;
};

export type OnlineLogMetricCreatePayload = {
  anomaly_summary?: string;
  core_event_count?: number;
  environment?: string;
  error_count?: number;
  module_code?: string;
  p95_latency_ms?: number;
  p99_latency_ms?: number;
  product_id: string;
  request_count?: number;
  source_channel?: string;
  status?: string;
  top_errors?: Record<string, unknown>[];
  window_end: string;
  window_start: string;
};

export type CollectorRunRecord = {
  collectorType: string;
  createdBy?: string;
  errorMessage?: string;
  finishedAt?: string;
  id: string;
  payloadSummary: Record<string, unknown>;
  productId?: string;
  recordsImported: number;
  sourceSystem: string;
  startedAt: string;
  status: string;
  updatedAt: string;
};

export type CollectorRunCreatePayload = {
  collector_type: string;
  error_message?: string;
  payload_summary?: Record<string, unknown>;
  product_id?: string;
  records_imported?: number;
  source_system: string;
  started_at?: string;
  status?: string;
};

export type CollectorRunPatchPayload = {
  error_message?: string;
  finished_at?: string;
  payload_summary?: Record<string, unknown>;
  records_imported?: number;
  status?: string;
};

export type PendingAttributionItem = {
  collectorRunId?: string;
  confidence?: number;
  createdAt: string;
  createdBy?: string;
  id: string;
  rawPayload: Record<string, unknown>;
  rawSubjectId?: string;
  resolutionAction?: string;
  resolutionNote?: string;
  resolvedAt?: string;
  resolvedBy?: string;
  resolvedModuleCode?: string;
  resolvedProductId?: string;
  resolvedRequirementId?: string;
  resolvedSubjectId?: string;
  resolvedSubjectType?: string;
  sourceSystem: string;
  sourceType: string;
  status: string;
  suggestedModuleCode?: string;
  suggestedProductId?: string;
  summary: string;
  updatedAt: string;
};

export type PendingAttributionCreatePayload = {
  collector_run_id?: string;
  confidence?: number;
  raw_payload?: Record<string, unknown>;
  raw_subject_id?: string;
  source_system: string;
  source_type: string;
  suggested_module_code?: string;
  suggested_product_id?: string;
  summary: string;
};

export type PendingAttributionResolvePayload = {
  resolution_action: string;
  resolution_note?: string;
  resolved_module_code?: string;
  resolved_product_id?: string;
  resolved_requirement_id?: string;
  resolved_subject_id?: string;
  resolved_subject_type?: string;
};

export type PendingAttributionFilters = {
  collector_run_id?: string;
  resolved_product_id?: string;
  source_type?: string;
  status?: string;
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

export type LifecycleRelationRecord = {
  relationType: string;
  subjectId: string;
  subjectType: string;
  summary: string;
};

export type LifecycleRiskSignalRecord = {
  impactSummary: string;
  recommendation: string;
  riskType: string;
  severity: string;
  sourceSubjectId: string;
  sourceSubjectType: string;
};

export type LifecycleContextRecord = {
  downstream: LifecycleRelationRecord[];
  missingContext: string[];
  riskSignals: LifecycleRiskSignalRecord[];
  status: string;
  summary: {
    downstreamCount: number;
    riskCount: number;
    upstreamCount: number;
  };
  upstream: LifecycleRelationRecord[];
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
  usageMetricSummary: DashboardUsageMetricSummary;
  userFeedbackStatusCounts: DashboardStatusCount[];
};

export type ProductGitRepositoryOption = {
  defaultBranch: string;
  id: string;
  label: string;
  name: string;
  projectId?: string | null;
  projectPath?: string | null;
  provider: string;
  status: string;
};

export type GitLabMergeRequestPreview = {
  author: string;
  changedFileCount: number;
  changedFilesSummary: unknown[];
  diffFileTree: CodeReviewDiffTreeItem[];
  mrIid: number;
  permissionDiagnostics?: CodeReviewPermissionDiagnostics;
  reviewChecklist: string[];
  repositoryId: string;
  riskSummary?: CodeReviewRiskSummary;
  sourceBranch?: string;
  targetBranch?: string;
  title: string;
  webUrl?: string;
  writebackAllowed: boolean;
};

export type CodeReviewPermissionDiagnostics = {
  baseUrlConfigured?: boolean;
  credentialRefConfigured?: boolean;
  provider?: string;
  repositoryPathConfigured?: boolean;
  tokenAvailable?: boolean;
  writebackAllowed?: boolean;
  writebackReason?: string;
};

export type CodeReviewDiffTreeItem = {
  additions: number;
  deletions: number;
  fileCount: number;
  path: string;
};

export type CodeReviewRiskSummary = {
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

export type GitLabMergeRequestSnapshot = {
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

export type CodeReviewDiffChangeSummary = {
  addedFiles?: string[];
  addedFilesCount?: number;
  modifiedFiles?: string[];
  modifiedFilesCount?: number;
  removedFiles?: string[];
  removedFilesCount?: number;
};

export type CodeReviewPreviousSnapshot = {
  createdAt?: string;
  headSha?: string;
  id?: string;
  snapshotHash?: string;
};

export type CodeReviewReportRecord = {
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

export type TaskWritebackIssueRecord = {
  id: string;
  sourceTaskId?: string;
  status: string;
  title: string;
};

export type TaskWritebackResultRecord = {
  idempotencyKey: string;
  issues: TaskWritebackIssueRecord[];
  status: string;
  taskId: string;
};

export type KnowledgeDepositRecord = {
  aiTaskId: string;
  content: string;
  id: string;
  knowledgeDocumentId?: string | null;
  rejectionReason?: string;
  status: string;
  title: string;
};

export type KnowledgeDepositApprovePayload = {
  permissionRoles?: string[];
  title?: string;
};

export type KnowledgeSearchResultRecord = {
  chunkId?: string;
  chunkIndex?: number;
  content: string;
  documentId: string;
  id: string;
  parentChunkId?: string;
  parentContent?: string;
  retrievalMode?: 'keyword' | 'vector';
  sourceLabel: string;
  title: string;
};

export type KnowledgeSpaceRecord = {
  code: string;
  description?: string;
  id: string;
  name: string;
};

export type KnowledgeFolderRecord = {
  id: string;
  knowledgeSpaceId: string;
  name: string;
  parentFolderId?: string | null;
  path: string;
};

export type KnowledgeAssetRecord = {
  assetType: string;
  filename: string;
  id: string;
  mimeType?: string;
  sizeBytes: number;
  storageProvider?: string;
};

export type KnowledgeImportJobRecord = {
  assetFilename?: string;
  chunkStrategy?: string;
  documentId: string;
  documentTitle?: string;
  errorMessage?: string;
  folderPath?: string;
  id: string;
  parserEngine?: string;
  progress: number;
  status: string;
  updatedAt?: string;
};

export type KnowledgeImportWorkerStatusRecord = {
  activeJobId?: string | null;
  enabled: boolean;
  failedCount: number;
  pendingCount: number;
  processedCount: number;
  queuedJobIds: string[];
  running: boolean;
  workerId?: string | null;
};

export type KnowledgeChunkSetRecord = {
  activatedAt?: string;
  chunkCount: number;
  chunkStrategy: string;
  id: string;
  isActive: boolean;
  parserEngine: string;
  status: string;
};

export type KnowledgeChunkRecord = {
  chunkIndex: number;
  chunkRole?: string;
  chunkSetId?: string;
  content: string;
  heading?: string;
  id: string;
  imageCount?: number;
  imageRefs?: string[];
  parentChunkId?: string;
  parentContent?: string;
  pageNumber?: number;
  sectionTitle?: string;
  sourceAssetType?: string;
  sourceKind?: string;
  splitPattern?: string;
  tableColumns?: string[];
  tableCount?: number;
  tableIndex?: number;
};

export type KnowledgeDocumentUploadPayload = {
  chunk_strategy?: string;
  content_base64: string;
  doc_type?: string;
  filename: string;
  folder_id?: string;
  knowledge_space_id: string;
  mime_type?: string;
  parser_engine?: string;
  tags?: string[];
  title: string;
};

export type ProductFilterOption = {
  code: string;
  id: string;
  name: string;
};

type ProductListItem = {
  code?: string;
  current_version_name?: string;
  id: string;
  module_count?: number;
  name: string;
  owner_team?: string | null;
  status?: string;
};

type ProductVersionListItem = {
  code?: string;
  description?: string | null;
  id: string;
  name: string;
  product_code?: string;
  product_id: string;
  product_name?: string;
  release_date?: string | null;
  start_date?: string | null;
  status?: string;
};

type ProductModuleListItem = {
  code?: string;
  description?: string | null;
  id: string;
  name: string;
  owner_team?: string | null;
  product_id: string;
  status?: string;
};

type ProductRelatedSystemListItem = {
  code?: string;
  description?: string | null;
  id: string;
  name: string;
  owner_team?: string | null;
  product_id?: string | null;
  status?: string;
};

export type ProductMutationPayload = {
  code?: string;
  description?: string;
  display_order?: number;
  name?: string;
  owner_team?: string;
  status?: string;
};

export type RequirementMutationPayload = {
  content?: string;
  module_code?: string;
  priority?: string;
  product_id?: string;
  source?: string;
  title?: string;
  version_id?: string | null;
};

export type RequirementBatchSchedulePayload = {
  product_id: string;
  reason?: string;
  requirement_ids: string[];
  version_id: string;
};

type RequirementBatchSkippedItem = {
  code: string;
  id: string;
  message: string;
};

type RequirementBatchScheduleResponse = {
  batch_id: string;
  product_id: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skipped_count: number;
  updated: RequirementListItem[];
  updated_count: number;
  version_id: string;
};

export type RequirementBatchScheduleResult = {
  batchId: string;
  productId: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skippedCount: number;
  updated: RequirementRecord[];
  updatedCount: number;
  versionId: string;
};

export type RequirementBatchAssignOwnerPayload = {
  assignee: string;
  reason?: string;
  requirement_ids: string[];
};

type RequirementBatchAssignOwnerResponse = {
  assignee: string;
  batch_id: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skipped_count: number;
  updated: RequirementListItem[];
  updated_count: number;
};

export type RequirementBatchAssignOwnerResult = {
  assignee: string;
  batchId: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skippedCount: number;
  updated: RequirementRecord[];
  updatedCount: number;
};

export type RequirementBatchAdvanceStatusPayload = {
  reason?: string;
  requirement_ids: string[];
  target_status: string;
};

type RequirementBatchAdvanceStatusResponse = {
  batch_id: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skipped_count: number;
  target_status: string;
  updated: RequirementListItem[];
  updated_count: number;
};

export type RequirementBatchAdvanceStatusResult = {
  batchId: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skippedCount: number;
  targetStatus: RequirementRecord['status'];
  updated: RequirementRecord[];
  updatedCount: number;
};

export type RequirementBatchGenerateTasksPayload = {
  product_id: string;
  reason?: string;
  requirement_ids: string[];
};

type RequirementBatchGeneratedTaskItem = {
  requirement_id: string;
  task_id: string;
  task_status: string;
  task_type: string;
};

type RequirementBatchGenerateTasksResponse = {
  batch_id: string;
  generated: RequirementBatchGeneratedTaskItem[];
  generated_count: number;
  product_id: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skipped_count: number;
};

export type RequirementBatchGenerateTasksResult = {
  batchId: string;
  generated: RequirementBatchGeneratedTaskItem[];
  generatedCount: number;
  productId: string;
  reason?: string | null;
  skipped: RequirementBatchSkippedItem[];
  skippedCount: number;
};

export type ProductVersionMutationPayload = {
  code?: string;
  description?: string;
  name: string;
  release_date?: string;
  start_date?: string;
  status?: string;
};

export type ProductVersionAdvanceStatusPayload = {
  force?: boolean;
  preview_only?: boolean;
  reason?: string;
  target_status: string;
};

type ProductVersionAdvanceRequirementImpact = {
  block_reason?: string;
  from_status?: string;
  id: string;
  status?: string;
  title: string;
  to_status?: string;
};

type ProductVersionAdvanceStatusResponse = {
  blocked_requirements: ProductVersionAdvanceRequirementImpact[];
  force: boolean;
  from_status: string;
  preview_only: boolean;
  target_status: string;
  unchanged_requirements: ProductVersionAdvanceRequirementImpact[];
  updated_requirements: ProductVersionAdvanceRequirementImpact[];
  version: ProductVersionListItem;
};

export type ProductVersionAdvanceStatusResult = {
  blockedRequirements: ProductVersionAdvanceRequirementImpact[];
  force: boolean;
  fromStatus: ProductVersionRecord['status'];
  previewOnly: boolean;
  targetStatus: ProductVersionRecord['status'];
  unchangedRequirements: ProductVersionAdvanceRequirementImpact[];
  updatedRequirements: ProductVersionAdvanceRequirementImpact[];
  version: ProductVersionRecord;
};

export type ProductModuleMutationPayload = {
  code?: string;
  description?: string;
  display_order?: number;
  name: string;
  owner_team?: string;
  status?: string;
};

export type ProductGitRepositoryMutationPayload = {
  credential_ref?: string;
  default_branch?: string;
  git_provider?: string;
  name: string;
  project_id?: string;
  project_path?: string;
  remote_url?: string;
  repo_type?: string;
  root_path?: string;
  status?: string;
};

export type ProductVersionBranchConfigMutationPayload = {
  base_branch?: string;
  branch_status?: string;
  creation_source?: string;
  description?: string;
  repository_id: string;
  working_branch: string;
};

export type ProductRelatedSystemMutationPayload = {
  code?: string;
  description?: string;
  display_order?: number;
  name: string;
  owner_team?: string;
  product_id?: string;
  status?: string;
};

export type BugMutationPayload = {
  assignee?: string;
  description?: string;
  duplicate_of_bug_id?: string | null;
  evidence?: Record<string, unknown>;
  module_code?: string;
  product_id?: string;
  related_task_id?: string;
  requirement_id?: string;
  reproduce_steps?: string[];
  severity?: string;
  source?: string;
  status?: string;
  title?: string;
  version_id?: string;
};

export type KnowledgeDocumentMutationPayload = {
  content?: string;
  doc_type?: string;
  folder_id?: string | null;
  index_error?: string | null;
  index_status?: string;
  knowledge_space_id?: string | null;
  permission_roles?: string[];
  tags?: string[];
  title?: string;
};

export type UserMutationPayload = {
  display_name?: string;
  password?: string;
  roles?: string[];
  status?: string;
  username?: string;
};

export type ModelGatewayConfigMutationPayload = {
  api_key?: string;
  base_url?: string;
  config_id?: string;
  default_chat_model?: string;
  default_embedding_model?: string | null;
  embedding_api_key?: string;
  embedding_base_url?: string | null;
  embedding_connection_mode?: 'custom' | 'disabled' | 'reuse_chat';
  embedding_dimension?: number | null;
  is_default?: boolean;
  max_retries?: number;
  name?: string;
  provider?: string;
  status?: string;
  test_target?: 'chat' | 'chat_and_embedding' | 'embedding';
  timeout_seconds?: number;
};

export type ModelGatewayConfigTestResult = {
  chat: {
    error_code?: string;
    latency_ms?: number;
    model: string;
    ok: boolean;
    status: string;
  };
  embedding: {
    dimension?: number;
    error_code?: string;
    latency_ms?: number;
    model: string;
    ok: boolean;
    status: string;
  };
  ok: boolean;
  test_target?: string;
};

type RequirementListItem = {
  assignee?: string | null;
  content?: string;
  created_at?: string;
  created_by?: string;
  id: string;
  module_code?: string | null;
  priority?: string;
  product_code?: string;
  product_id: string;
  product_name?: string;
  source?: string;
  status?: string;
  title: string;
  updated_at?: string;
  version_code?: string | null;
  version_id?: string;
  version_name?: string | null;
};

type KnowledgeDocumentListItem = {
  active_chunk_set_id?: string | null;
  content?: string;
  created_at?: string;
  doc_type?: string;
  folder_id?: string | null;
  folder_path?: string | null;
  id: string;
  index_error?: string | null;
  index_status?: string;
  knowledge_space_id?: string | null;
  permission_roles?: string[];
  source_asset_id?: string | null;
  tags?: string[];
  title: string;
  updated_at?: string;
  vector_index_error?: string | null;
};

type KnowledgeSpaceListItem = {
  code: string;
  description?: string;
  id: string;
  name: string;
};

type KnowledgeFolderListItem = {
  id: string;
  knowledge_space_id: string;
  name: string;
  parent_folder_id?: string | null;
  path?: string;
};

type KnowledgeAssetListItem = {
  asset_type?: string;
  filename?: string;
  id: string;
  mime_type?: string;
  size_bytes?: number;
  storage_provider?: string;
};

type KnowledgeImportJobListItem = {
  asset_filename?: string;
  chunk_strategy?: string;
  document_id: string;
  document_title?: string;
  error_message?: string | null;
  folder_path?: string;
  id: string;
  parser_engine?: string;
  progress?: number;
  status?: string;
  updated_at?: string;
};

type KnowledgeImportWorkerStatusItem = {
  active_job_id?: string | null;
  enabled?: boolean;
  failed_count?: number;
  pending_count?: number;
  processed_count?: number;
  queued_job_ids?: string[];
  running?: boolean;
  worker_id?: string | null;
};

type KnowledgeChunkSetListItem = {
  activated_at?: string;
  chunk_count?: number;
  chunk_strategy?: string;
  id: string;
  is_active?: boolean;
  parser_engine?: string;
  status?: string;
};

type KnowledgeChunkListItem = {
  chunk_index?: number;
  chunk_set_id?: string;
  content?: string;
  id: string;
  metadata?: {
    columns?: string[];
    chunk_role?: string;
    heading?: string;
    image_count?: number;
    image_refs?: string[];
    page_number?: number;
    section_title?: string;
    source_asset_type?: string;
    source_kind?: string;
    split_pattern?: string;
    table_count?: number;
    table_index?: number;
  };
  parent_chunk_id?: string;
  parent_content?: string;
};

type AuditEventListItem = {
  actor_id?: string;
  ai_task_id?: string | null;
  created_at?: string;
  event_type: string;
  id: string;
  payload?: Record<string, unknown>;
  result?: string;
  subject_id?: string;
  subject_type?: string;
};

type LifecycleRelationItem = {
  relation_type?: string;
  subject_id?: string;
  subject_type?: string;
  summary?: string;
};

type LifecycleRiskSignalItem = {
  impact_summary?: string;
  recommendation?: string;
  risk_type?: string;
  severity?: string;
  source_subject_id?: string;
  source_subject_type?: string;
};

type LifecycleContextResponse = {
  downstream?: LifecycleRelationItem[];
  missing_context?: string[];
  risk_signals?: LifecycleRiskSignalItem[];
  status?: string;
  summary?: Partial<{
    downstream_count: number;
    risk_count: number;
    upstream_count: number;
  }>;
  upstream?: LifecycleRelationItem[];
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
  bugs?: BugListItem[];
  code_review_reports?: CodeReviewReportResponse[];
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
    bugs: number;
    code_review_reports: number;
    git_snapshots: number;
    jenkins_releases: number;
    knowledge_deposits: number;
    reviews: number;
    timeline_events: number;
  }>;
  timeline?: RequirementFullChainTimelineItemResponse[];
};

type BugListItem = {
  assignee?: string | null;
  created_at?: string;
  description?: string;
  duplicate_of_bug_id?: string | null;
  evidence?: unknown;
  id: string;
  module_code?: string | null;
  product_id?: string;
  related_task_id?: string | null;
  reproduce_steps?: unknown;
  requirement_id?: string | null;
  severity?: string;
  source?: string;
  status?: string;
  title: string;
  version_code?: string | null;
  version_id?: string | null;
  version_name?: string | null;
};

type TaskListItem = {
  created_at?: string;
  created_by?: string;
  current_step?: string | null;
  id: string;
  product_id?: string;
  product_name?: string | null;
  requirement_id?: string;
  status?: string;
  task_type?: string;
  title?: string;
  updated_at?: string;
};

type TaskDetailItem = TaskListItem & {
  current_step?: string | null;
  graph_runs?: unknown;
  input?: unknown;
  input_json?: unknown;
  module_code?: string | null;
  output?: unknown;
  output_json?: unknown;
  pending_review?: unknown;
  product_context?: unknown;
  requirement_snapshot?: unknown;
  version_id?: string | null;
};

type ProductGitRepositoryListItem = {
  credential_ref_configured?: boolean;
  default_branch?: string;
  git_provider?: string;
  id: string;
  name: string;
  project_id?: string | null;
  project_path?: string | null;
  remote_url?: string | null;
  repo_type?: string;
  root_path?: string;
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

type ModelGatewayConfigListItem = {
  api_key_configured?: boolean;
  base_url?: string;
  default_chat_model?: string;
  default_embedding_model?: string | null;
  embedding_api_key_configured?: boolean;
  embedding_base_url?: string | null;
  embedding_connection_mode?: string;
  embedding_dimension?: number | null;
  id: string;
  is_default?: boolean;
  max_retries?: number;
  name: string;
  provider?: string;
  status?: string;
  timeout_seconds?: number;
};

type GitLabMergeRequestPreviewResponse = {
  author?: unknown;
  changed_file_count?: number;
  changed_files_summary?: unknown[];
  diff_file_tree?: Array<{
    additions?: number;
    deletions?: number;
    file_count?: number;
    path?: string;
  }>;
  mr_iid: number;
  permission_diagnostics?: {
    base_url_configured?: boolean;
    credential_ref_configured?: boolean;
    provider?: string;
    repository_path_configured?: boolean;
    token_available?: boolean;
    writeback_allowed?: boolean;
    writeback_reason?: string;
  };
  review_checklist?: string[];
  repository_id: string;
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
  source_branch?: string;
  target_branch?: string;
  title?: string;
  web_url?: string;
  writeback_allowed?: boolean;
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
  archived_at?: string;
  created_at?: string;
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

type TaskWritebackIssueResponse = {
  id: string;
  source_task_id?: string;
  status?: string;
  title?: string;
};

type TaskWritebackResultResponse = {
  idempotency_key?: string;
  issues?: TaskWritebackIssueResponse[];
  status?: string;
  task_id?: string;
};

type KnowledgeDepositListItem = {
  ai_task_id: string;
  content?: string;
  id: string;
  knowledge_document_id?: string | null;
  rejection_reason?: string;
  status?: string;
  title?: string;
};

type KnowledgeSearchResultItem = {
  chunk_id?: string;
  chunk_index?: number;
  content?: string;
  document_id: string;
  retrieval_mode?: string;
  source?: {
    asset_id?: string;
    chunk_id?: string;
    chunk_set_id?: string;
    doc_type?: string;
    folder_id?: string;
    knowledge_space_id?: string;
    parent_chunk_id?: string;
    parent_content?: string;
    title?: string;
  };
  title?: string;
};

type PendingReviewListItem = {
  ai_task_id: string;
  content?: Record<string, unknown>;
  created_at?: string;
  id: string;
  stage?: string;
  status?: string;
  version: number;
};

type FlexibleListItem = Record<string, unknown> & {
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
  latest_high_severity_bugs?: FlexibleListItem[];
  latest_tasks?: FlexibleListItem[];
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
  pending_reviews?: FlexibleListItem[];
  recent_audit_events?: FlexibleListItem[];
  recent_knowledge_documents?: FlexibleListItem[];
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
  usage_metric_summary?: Partial<{
    active_users: number;
    conversion_count: number;
    error_count: number;
    event_count: number;
    metric_count: number;
  }>;
  user_feedback_status_counts?: Array<{ count?: number; status?: string }>;
};

type UserListItem = {
  display_name: string;
  id: string;
  roles?: string[];
  status?: string;
  username: string;
};

type RoleDefinitionListItem = {
  business_roles?: string[];
  category?: string;
  code: string;
  data_scope?: string;
  decision_scope?: string;
  description?: string;
  is_assignable?: boolean;
  is_system?: boolean;
  limitations?: string[];
  menu_codes?: string[];
  menu_scope?: string[];
  name: string;
  permission_codes?: string[];
  permissions?: string[];
  responsibilities?: string[];
  scopes?: ScopeGrant[];
  id?: string;
  sort_order?: number;
  status?: string;
};

export async function apiRequest<T>(
  path: string,
  options: {
    method?: string;
    token?: string;
    body?: unknown;
  } = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: options.body ? JSON.stringify(options.body) : undefined,
    headers: {
      'Content-Type': 'application/json',
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    },
    method: options.method ?? 'GET',
  });
  if (!response.ok) {
    let payload: ApiErrorPayload | undefined;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = undefined;
    }
    const requestError = new ApiRequestError({
      code: payload?.detail?.code,
      message: payload?.detail?.message ?? `API request failed: ${response.status}`,
      status: response.status,
      traceId: payload?.detail?.trace_id,
    });
    if (response.status === 401 && !path.startsWith('/api/auth/login')) {
      handleUnauthorizedApiResponse();
    }
    throw requestError;
  }
  const payload = (await response.json()) as ApiEnvelope<T>;
  return payload.data;
}

export async function chatWithAssistant(
  payload: AssistantChatPayload,
): Promise<AssistantChatResponse> {
  const token = requireAccessToken();
  const response = await apiRequest<AssistantChatApiResponse>('/api/assistant/chat', {
    body: {
      context: payload.context,
      conversation_id: payload.conversationId,
      message: payload.message,
      product_id: payload.productId,
    },
    method: 'POST',
    token,
  });
  return {
    content: response.message.content ?? '',
    conversationId: response.conversation_id,
    latencyMs: Number(response.latency_ms ?? 0),
    messageId: response.message.id ?? response.conversation_id,
    model: response.model ?? '',
    references: response.message.references ?? response.references ?? [],
    suggestions: response.suggestions ?? [],
  };
}

export async function fetchAssistantConversations(): Promise<AssistantConversationSummary[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<AssistantConversationApiRecord>>(
    '/api/assistant/conversations',
    {
      method: 'GET',
      token,
    },
  );
  return response.items.map((item) => ({
    createdAt: item.created_at,
    id: item.id,
    lastMessageAt: item.last_message_at,
    messageCount: Number(item.message_count ?? 0),
    productId: item.product_id,
    title: item.title ?? '新对话',
    updatedAt: item.updated_at,
  }));
}

export async function fetchAssistantConversationMessages(
  conversationId: string,
): Promise<AssistantConversationMessage[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<AssistantMessageApiRecord>>(
    `/api/assistant/conversations/${conversationId}/messages`,
    {
      method: 'GET',
      token,
    },
  );
  return response.items.map((item) => ({
    content: item.content ?? '',
    createdAt: item.created_at,
    id: item.id ?? conversationId,
    model: item.model,
    productId: item.product_id,
    references: item.references ?? [],
    role: item.role === 'user' ? 'user' : 'assistant',
    suggestions: item.suggestions ?? [],
  }));
}

export function getAccessToken() {
  const storedToken =
    typeof globalThis.localStorage === 'undefined'
      ? undefined
      : globalThis.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  return storedToken || process.env.UMI_APP_API_TOKEN || undefined;
}

function requireAccessToken() {
  const token = getAccessToken();
  if (!token) {
    throw new ApiRequestError({
      code: 'AUTH_REQUIRED',
      message: '缺少访问令牌，请先登录后再加载真实数据。',
      status: 401,
    });
  }
  return token;
}

export function saveAccessToken(token: string) {
  if (typeof globalThis.localStorage === 'undefined') {
    return;
  }
  globalThis.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
}

export function saveCurrentUser(user: CurrentUserResponse) {
  if (!user || typeof globalThis.localStorage === 'undefined') {
    return;
  }
  globalThis.localStorage.setItem(CURRENT_USER_STORAGE_KEY, JSON.stringify(user));
  emitAuthStateChanged();
}

export function getStoredCurrentUser(): CurrentUserResponse | undefined {
  if (typeof globalThis.localStorage === 'undefined') {
    return undefined;
  }
  const value = globalThis.localStorage.getItem(CURRENT_USER_STORAGE_KEY);
  if (!value) {
    return undefined;
  }
  try {
    return JSON.parse(value) as CurrentUserResponse;
  } catch {
    globalThis.localStorage.removeItem(CURRENT_USER_STORAGE_KEY);
    return undefined;
  }
}

export function clearAccessToken() {
  if (typeof globalThis.localStorage === 'undefined') {
    return;
  }
  globalThis.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  globalThis.localStorage.removeItem(CURRENT_USER_STORAGE_KEY);
  emitAuthStateChanged();
}

function handleUnauthorizedApiResponse() {
  clearAccessToken();
  if (typeof window === 'undefined') {
    return;
  }
  const { pathname, search } = window.location;
  if (pathname === '/login') {
    return;
  }
  const target = `${pathname}${search}`;
  navigateTo(`/login?redirect=${encodeURIComponent(target)}`);
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const loginResponse = await apiRequest<LoginResponse>('/api/auth/login', {
    body: { username, password },
    method: 'POST',
  });
  saveAccessToken(loginResponse.access_token);
  saveCurrentUser(loginResponse.user);
  return loginResponse;
}

export async function fetchCurrentUser(): Promise<CurrentUserResponse> {
  const token = requireAccessToken();
  const user = await apiRequest<CurrentUserResponse>('/api/auth/me', { token });
  saveCurrentUser(user);
  return user;
}

export async function logout(): Promise<void> {
  const token = getAccessToken();
  clearAccessToken();
  if (!token) {
    return;
  }
  try {
    await apiRequest<{ success: boolean }>('/api/auth/logout', {
      method: 'POST',
      token,
    });
  } catch {
    // Local logout should still complete if the server token is already expired.
  }
}

function formatListDate(value?: string) {
  if (!value) {
    return '-';
  }
  return value.replace('T', ' ').replace(/\.\d+/, '').replace('+00:00', '').slice(0, 16);
}

function normalizeProductStatus(status?: string): ProductRecord['status'] {
  return status === 'inactive' ? 'inactive' : 'active';
}

function normalizeProductVersionStatus(status?: string): ProductVersionRecord['status'] {
  if (
    status === 'archived' ||
    status === 'planning' ||
    status === 'released' ||
    status === 'testing'
  ) {
    return status;
  }
  return 'active';
}

function normalizeActiveInactiveStatus(
  status?: string,
): ProductModuleRecord['status'] | ProductGitRepositoryRecord['status'] {
  return status === 'inactive' ? 'inactive' : 'active';
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

function normalizeKnowledgeStatus(status?: string): KnowledgeRecord['status'] {
  if (
    status === 'archived' ||
    status === 'importing' ||
    status === 'indexed' ||
    status === 'index_failed' ||
    status === 'pending_index' ||
    status === 'text_indexed' ||
    status === 'vector_indexed'
  ) {
    return status;
  }
  if (status === 'failed') {
    return 'index_failed';
  }
  return 'pending_index';
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
  if (source === 'ai_auto_test' || source === 'ai_post_release') {
    return source;
  }
  return 'manual_test';
}

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => (typeof item === 'string' ? item : JSON.stringify(item) ?? ''))
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeObjectRecord(value: unknown): Record<string, unknown> | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  return value as Record<string, unknown>;
}

function normalizeModelGatewayStatus(status?: string): ModelGatewayConfigRecord['status'] {
  return status === 'inactive' ? 'inactive' : 'active';
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

function formatGitLabAuthor(value: unknown): string {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const author = value as Record<string, unknown>;
    return formatUnknownValue(author.name ?? author.username ?? author.login);
  }
  return formatUnknownValue(value);
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

function normalizePermissionDiagnostics(
  diagnostics?: GitLabMergeRequestPreviewResponse['permission_diagnostics'],
): CodeReviewPermissionDiagnostics | undefined {
  if (!diagnostics) {
    return undefined;
  }
  return {
    baseUrlConfigured: diagnostics.base_url_configured,
    credentialRefConfigured: diagnostics.credential_ref_configured,
    provider: diagnostics.provider,
    repositoryPathConfigured: diagnostics.repository_path_configured,
    tokenAvailable: diagnostics.token_available,
    writebackAllowed: diagnostics.writeback_allowed,
    writebackReason: diagnostics.writeback_reason,
  };
}

function normalizeDiffChangeSummary(
  summary?: GitLabMergeRequestSnapshotResponse['diff_change_summary'],
): CodeReviewDiffChangeSummary | undefined {
  if (!summary) {
    return undefined;
  }
  return {
    addedFiles: summary.added_files ?? [],
    addedFilesCount: summary.added_files_count ?? 0,
    modifiedFiles: summary.modified_files ?? [],
    modifiedFilesCount: summary.modified_files_count ?? 0,
    removedFiles: summary.removed_files ?? [],
    removedFilesCount: summary.removed_files_count ?? 0,
  };
}

function normalizePreviousSnapshot(
  snapshot?: GitLabMergeRequestSnapshotResponse['previous_snapshot'],
): CodeReviewPreviousSnapshot | null {
  if (!snapshot) {
    return null;
  }
  return {
    createdAt: formatListDate(snapshot.created_at),
    headSha: snapshot.head_sha,
    id: snapshot.id,
    snapshotHash: snapshot.snapshot_hash,
  };
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

export async function fetchManagementProducts(): Promise<ProductRecord[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    apiRequest<ListResponse<ProductListItem>>('/api/products', { token }),
    apiRequest<ListResponse<ProductVersionListItem>>('/api/product-versions', { token }),
  ]);
  const versionsByProductId = versions.items.reduce(
    (groupedVersions, version) => {
      const rows = groupedVersions.get(version.product_id) ?? [];
      rows.push(version);
      groupedVersions.set(version.product_id, rows);
      return groupedVersions;
    },
    new Map<string, ProductVersionListItem[]>(),
  );

  return products.items.map((product) =>
    mapProductRecord(product, versionsByProductId.get(product.id)),
  );
}

function mapProductRecord(
  product: ProductListItem,
  versions: ProductVersionListItem[] = [],
): ProductRecord {
  return {
    code: product.code ?? product.id,
    id: product.id,
    moduleCount: product.module_count ?? 0,
    name: product.name,
    ownerTeam: product.owner_team ?? '-',
    status: normalizeProductStatus(product.status),
    version:
      product.current_version_name ??
      versions.find((version) => version.status === 'active')?.name ??
      versions[0]?.name ??
      '未配置',
  };
}

export async function fetchManagementProductList(
  query: ProductListQuery = {},
): Promise<RemoteListResult<ProductRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'code', query.code);
  appendQueryParam(params, 'name', query.name);
  appendQueryParam(params, 'owner_team', query.ownerTeam);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const products = await apiRequest<ListResponse<ProductListItem>>(
    queryString ? `/api/products?${queryString}` : '/api/products',
    { token },
  );

  return {
    page: products.page ?? query.page ?? 1,
    pageSize: products.page_size ?? query.pageSize ?? 10,
    rows: products.items.map((product) => mapProductRecord(product)),
    total: products.total,
  };
}

export async function createManagementProduct(payload: ProductMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<ProductResponse>('/api/products', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateManagementProduct(productId: string, payload: ProductMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<ProductResponse>(`/api/products/${productId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteManagementProduct(productId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/products/${productId}`, {
    method: 'DELETE',
    token,
  });
}

function mapProductVersionOption(version: ProductVersionListItem): ProductVersionOption {
  return {
    code: version.code ?? version.id,
    description: version.description ?? undefined,
    id: version.id,
    name: version.name,
    status: version.status ?? '-',
  };
}

function isRequirementSchedulableVersion(version: ProductVersionListItem): boolean {
  return ['active', 'planning'].includes((version.status ?? '').toLowerCase());
}

function isBugAssignableVersion(version: ProductVersionListItem): boolean {
  return (version.status ?? '').toLowerCase() !== 'archived';
}

function mapProductContexts(
  products: ProductListItem[],
  versions: ProductVersionListItem[],
): ProductContextOption[] {
  const versionsByProductId = versions.reduce(
    (groupedVersions, version) => {
      const rows = groupedVersions.get(version.product_id) ?? [];
      rows.push(version);
      groupedVersions.set(version.product_id, rows);
      return groupedVersions;
    },
    new Map<string, ProductVersionListItem[]>(),
  );

  return products.map((product) => ({
    code: product.code ?? product.id,
    id: product.id,
    name: product.name,
    versions: (versionsByProductId.get(product.id) ?? []).map(mapProductVersionOption),
  }));
}

function mapProductVersionRecord(version: ProductVersionListItem): ProductVersionRecord {
  return {
    code: version.code ?? version.id,
    description: version.description ?? undefined,
    id: version.id,
    name: version.name,
    productCode: version.product_code,
    productId: version.product_id,
    productName: version.product_name,
    releaseDate: version.release_date ?? undefined,
    startDate: version.start_date ?? undefined,
    status: normalizeProductVersionStatus(version.status),
  };
}

function mapProductModuleRecord(module: ProductModuleListItem): ProductModuleRecord {
  return {
    code: module.code ?? module.id,
    id: module.id,
    name: module.name,
    ownerTeam: module.owner_team ?? '-',
    status: normalizeActiveInactiveStatus(module.status),
  };
}

function mapProductRelatedSystemRecord(
  relatedSystem: ProductRelatedSystemListItem,
): ProductRelatedSystemRecord {
  return {
    code: relatedSystem.code ?? relatedSystem.id,
    description: relatedSystem.description,
    id: relatedSystem.id,
    name: relatedSystem.name,
    ownerTeam: relatedSystem.owner_team ?? '-',
    productId: relatedSystem.product_id,
    status: normalizeActiveInactiveStatus(relatedSystem.status),
  };
}

function mapProductGitRepositoryRecord(
  repository: ProductGitRepositoryListItem,
): ProductGitRepositoryRecord {
  const credentialRefConfigured = repository.credential_ref_configured ?? false;
  return {
    credentialRefConfigured,
    credentialStatus: credentialRefConfigured ? '已配置' : '未配置',
    defaultBranch: repository.default_branch ?? 'main',
    id: repository.id,
    name: repository.name,
    projectId: repository.project_id,
    projectPath: repository.project_path,
    provider: repository.git_provider ?? 'gitlab',
    remoteUrl: repository.remote_url ?? '-',
    repoType: repository.repo_type ?? 'code',
    rootPath: repository.root_path ?? '/',
    status: normalizeActiveInactiveStatus(repository.status),
  };
}

function normalizeProductVersionBranchStatus(
  status?: string,
): ProductVersionBranchConfigRecord['branchStatus'] {
  const allowed = new Set(['active', 'archived', 'merged', 'not_created', 'released', 'testing']);
  return allowed.has(status ?? '') ? (status as ProductVersionBranchConfigRecord['branchStatus']) : 'not_created';
}

function normalizeProductVersionBranchCreationSource(
  source?: string,
): ProductVersionBranchConfigRecord['creationSource'] {
  const allowed = new Set(['ai_task', 'github_sync', 'gitlab_sync', 'manual']);
  return allowed.has(source ?? '') ? (source as ProductVersionBranchConfigRecord['creationSource']) : 'manual';
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

export async function fetchProductVersions(productId: string): Promise<ProductVersionRecord[]> {
  const token = requireAccessToken();
  const versions = await apiRequest<ListResponse<ProductVersionListItem>>(
    `/api/products/${productId}/versions`,
    { token },
  );
  return versions.items.map(mapProductVersionRecord);
}

export async function fetchDeliveryIterationVersions(): Promise<ProductVersionRecord[]> {
  const token = requireAccessToken();
  const versions = await apiRequest<ListResponse<ProductVersionListItem>>(
    '/api/product-versions',
    { token },
  );
  return versions.items.map(mapProductVersionRecord);
}

export async function fetchDeliveryIterationVersionList(
  query: ProductVersionListQuery = {},
): Promise<RemoteListResult<ProductVersionRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'code', query.code);
  appendQueryParam(params, 'name', query.name);
  appendQueryParam(params, 'product', query.product);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const versions = await apiRequest<ListResponse<ProductVersionListItem>>(
    queryString ? `/api/product-versions?${queryString}` : '/api/product-versions',
    { token },
  );

  return {
    page: versions.page ?? query.page ?? 1,
    pageSize: versions.page_size ?? query.pageSize ?? 10,
    rows: versions.items.map(mapProductVersionRecord),
    total: versions.total,
  };
}

export async function createProductVersion(
  productId: string,
  payload: ProductVersionMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<ProductVersionListItem>(`/api/products/${productId}/versions`, {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateProductVersion(
  versionId: string,
  payload: Partial<ProductVersionMutationPayload>,
) {
  const token = requireAccessToken();
  return apiRequest<ProductVersionListItem>(`/api/product-versions/${versionId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function advanceProductVersionStatus(
  versionId: string,
  payload: ProductVersionAdvanceStatusPayload,
): Promise<ProductVersionAdvanceStatusResult> {
  const token = requireAccessToken();
  const result = await apiRequest<ProductVersionAdvanceStatusResponse>(
    `/api/product-versions/${versionId}/advance-status`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return {
    blockedRequirements: result.blocked_requirements,
    force: result.force,
    fromStatus: normalizeProductVersionStatus(result.from_status),
    previewOnly: result.preview_only,
    targetStatus: normalizeProductVersionStatus(result.target_status),
    unchangedRequirements: result.unchanged_requirements,
    updatedRequirements: result.updated_requirements,
    version: mapProductVersionRecord(result.version),
  };
}

export async function deleteProductVersion(versionId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/product-versions/${versionId}`, {
    method: 'DELETE',
    token,
  });
}

export async function fetchProductVersionBranchConfigs(
  versionId: string,
): Promise<ProductVersionBranchConfigRecord[]> {
  const token = requireAccessToken();
  const branchConfigs = await apiRequest<ListResponse<ProductVersionBranchConfigListItem>>(
    `/api/product-versions/${versionId}/branch-configs`,
    { token },
  );
  return branchConfigs.items.map(mapProductVersionBranchConfigRecord);
}

export async function createProductVersionBranchConfig(
  versionId: string,
  payload: ProductVersionBranchConfigMutationPayload,
): Promise<ProductVersionBranchConfigRecord> {
  const token = requireAccessToken();
  const branchConfig = await apiRequest<ProductVersionBranchConfigListItem>(
    `/api/product-versions/${versionId}/branch-configs`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return mapProductVersionBranchConfigRecord(branchConfig);
}

export async function updateProductVersionBranchConfig(
  branchConfigId: string,
  payload: Partial<ProductVersionBranchConfigMutationPayload>,
): Promise<ProductVersionBranchConfigRecord> {
  const token = requireAccessToken();
  const branchConfig = await apiRequest<ProductVersionBranchConfigListItem>(
    `/api/product-version-branch-configs/${branchConfigId}`,
    {
      body: payload,
      method: 'PATCH',
      token,
    },
  );
  return mapProductVersionBranchConfigRecord(branchConfig);
}

export async function deleteProductVersionBranchConfig(branchConfigId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(
    `/api/product-version-branch-configs/${branchConfigId}`,
    {
      method: 'DELETE',
      token,
    },
  );
}

export async function fetchProductModules(productId: string): Promise<ProductModuleRecord[]> {
  const token = requireAccessToken();
  const modules = await apiRequest<ListResponse<ProductModuleListItem>>(
    `/api/products/${productId}/modules`,
    { token },
  );
  return modules.items.map(mapProductModuleRecord);
}

export async function createProductModule(
  productId: string,
  payload: ProductModuleMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<ProductModuleListItem>(`/api/products/${productId}/modules`, {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateProductModule(
  moduleId: string,
  payload: Partial<ProductModuleMutationPayload>,
) {
  const token = requireAccessToken();
  return apiRequest<ProductModuleListItem>(`/api/product-modules/${moduleId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteProductModule(moduleId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/product-modules/${moduleId}`, {
    method: 'DELETE',
    token,
  });
}

export async function fetchProductRelatedSystems(
  productId: string,
): Promise<ProductRelatedSystemRecord[]> {
  const token = requireAccessToken();
  const relatedSystems = await apiRequest<ListResponse<ProductRelatedSystemListItem>>(
    `/api/system/related-systems?product_id=${encodeURIComponent(productId)}`,
    { token },
  );
  return relatedSystems.items.map(mapProductRelatedSystemRecord);
}

export async function createProductRelatedSystem(
  productId: string,
  payload: ProductRelatedSystemMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<ProductRelatedSystemListItem>('/api/system/related-systems', {
    body: { ...payload, product_id: productId },
    method: 'POST',
    token,
  });
}

export async function updateProductRelatedSystem(
  relatedSystemId: string,
  payload: Partial<ProductRelatedSystemMutationPayload>,
) {
  const token = requireAccessToken();
  return apiRequest<ProductRelatedSystemListItem>(
    `/api/system/related-systems/${relatedSystemId}`,
    {
      body: payload,
      method: 'PATCH',
      token,
    },
  );
}

export async function deleteProductRelatedSystem(relatedSystemId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(
    `/api/system/related-systems/${relatedSystemId}`,
    {
      method: 'DELETE',
      token,
    },
  );
}

export async function fetchProductGitRepositoryRecords(
  productId: string,
): Promise<ProductGitRepositoryRecord[]> {
  const token = requireAccessToken();
  const repositories = await apiRequest<ListResponse<ProductGitRepositoryListItem>>(
    `/api/products/${productId}/git-repositories`,
    { token },
  );
  return repositories.items.map(mapProductGitRepositoryRecord);
}

export async function createProductGitRepository(
  productId: string,
  payload: ProductGitRepositoryMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<ProductGitRepositoryListItem>(`/api/products/${productId}/git-repositories`, {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateProductGitRepository(
  repositoryId: string,
  payload: Partial<ProductGitRepositoryMutationPayload>,
) {
  const token = requireAccessToken();
  return apiRequest<ProductGitRepositoryListItem>(`/api/product-git-repositories/${repositoryId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteProductGitRepository(repositoryId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(
    `/api/product-git-repositories/${repositoryId}`,
    {
      method: 'DELETE',
      token,
    },
  );
}

export async function fetchProductContextOptions(): Promise<ProductContextOption[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    apiRequest<ListResponse<ProductListItem>>(
      `/api/products?active_only=true&page_size=${PRODUCT_CONTEXT_PAGE_SIZE}`,
      { token },
    ),
    apiRequest<ListResponse<ProductVersionListItem>>(
      `/api/product-versions?active_only=true&page_size=${VERSION_CONTEXT_PAGE_SIZE}`,
      { token },
    ),
  ]);
  return mapProductContexts(products.items, versions.items);
}

export async function fetchBugProductContextOptions(): Promise<ProductContextOption[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    apiRequest<ListResponse<ProductListItem>>(
      `/api/products?active_only=true&page_size=${PRODUCT_CONTEXT_PAGE_SIZE}`,
      { token },
    ),
    apiRequest<ListResponse<ProductVersionListItem>>(
      `/api/product-versions?page_size=${VERSION_CONTEXT_PAGE_SIZE}`,
      { token },
    ),
  ]);
  return mapProductContexts(products.items, versions.items.filter(isBugAssignableVersion));
}

export async function fetchRequirementProductContextOptions(): Promise<ProductContextOption[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    apiRequest<ListResponse<ProductListItem>>(
      `/api/products?active_only=true&page_size=${PRODUCT_CONTEXT_PAGE_SIZE}`,
      { token },
    ),
    apiRequest<ListResponse<ProductVersionListItem>>(
      `/api/product-versions?page_size=${VERSION_CONTEXT_PAGE_SIZE}`,
      { token },
    ),
  ]);
  return mapProductContexts(
    products.items,
    versions.items.filter(isRequirementSchedulableVersion),
  );
}

export async function fetchActiveProductOptions(): Promise<ProductFilterOption[]> {
  const token = requireAccessToken();
  const products = await apiRequest<ListResponse<ProductListItem>>(
    `/api/products?active_only=true&page_size=${PRODUCT_CONTEXT_PAGE_SIZE}`,
    { token },
  );
  return products.items.map((product) => ({
    code: product.code ?? product.id,
    id: product.id,
    name: product.name,
  }));
}

function mapRoleDefinition(role: RoleDefinitionListItem): UserRoleDefinition {
  return {
    business_roles: role.business_roles ?? [],
    category: role.category ?? 'workspace',
    code: role.code,
    data_scope: role.data_scope ?? '',
    decision_scope: role.decision_scope ?? '',
    description: role.description ?? '',
    is_assignable: role.is_assignable ?? true,
    limitations: role.limitations ?? [],
    menu_scope: role.menu_scope ?? role.menu_codes ?? [],
    name: role.name,
    permissions: role.permissions ?? role.permission_codes ?? [],
    responsibilities: role.responsibilities ?? [],
    sort_order: role.sort_order ?? 0,
    status: role.status ?? 'active',
  };
}

function mapSystemRole(role: RoleDefinitionListItem): SystemRoleRecord {
  const roleDefinition = mapRoleDefinition(role);
  return {
    ...roleDefinition,
    id: role.id ?? role.code,
    is_system: role.is_system ?? false,
    menu_codes: role.menu_codes ?? role.menu_scope ?? [],
    permission_codes: role.permission_codes ?? role.permissions ?? [],
    scopes: role.scopes ?? [],
  };
}

export async function fetchRoleDefinitions(): Promise<UserRoleDefinition[]> {
  const token = requireAccessToken();
  const roles = await apiRequest<ListResponse<RoleDefinitionListItem>>('/api/auth/roles', { token });
  return roles.items.map(mapRoleDefinition);
}

export async function fetchRoleDefinitionList(
  query: RoleListQuery = {},
): Promise<RemoteListResult<UserRoleDefinition>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'business_role', query.businessRole);
  appendQueryParam(params, 'category', query.category);
  appendQueryParam(params, 'menu_scope', query.menuScope);
  appendQueryParam(params, 'permission', query.permission);
  appendQueryParam(params, 'role', query.role);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const roles = await apiRequest<ListResponse<RoleDefinitionListItem>>(
    queryString ? `/api/auth/roles?${queryString}` : '/api/auth/roles',
    { token },
  );
  return {
    page: roles.page ?? query.page ?? 1,
    pageSize: roles.page_size ?? query.pageSize ?? 10,
    rows: roles.items.map(mapRoleDefinition),
    total: roles.total,
  };
}

function filterSystemRoles(rows: SystemRoleRecord[], query: RoleListQuery) {
  const includes = (value: string | string[] | undefined, keyword?: string) => {
    if (!keyword) {
      return true;
    }
    const source = Array.isArray(value) ? value.join(', ') : value ?? '';
    return source.toLowerCase().includes(keyword.toLowerCase());
  };

  return rows.filter(
    (role) =>
      includes(`${role.name} ${role.code}`, query.role) &&
      includes(role.category, query.category) &&
      includes(role.menu_codes, query.menuScope) &&
      includes(role.permission_codes, query.permission) &&
      includes(role.status, query.status) &&
      includes(role.business_roles, query.businessRole),
  );
}

function sortSystemRoles(rows: SystemRoleRecord[], query: RoleListQuery) {
  const sortField = query.sortField;
  if (!sortField || !query.sortOrder) {
    return rows;
  }
  const direction = query.sortOrder === 'descend' ? -1 : 1;
  return [...rows].sort((left, right) => {
    const leftValue = String(left[sortField as keyof SystemRoleRecord] ?? '');
    const rightValue = String(right[sortField as keyof SystemRoleRecord] ?? '');
    return leftValue.localeCompare(rightValue, 'zh-Hans-CN') * direction;
  });
}

export async function fetchSystemPermissions(): Promise<PermissionRecord[]> {
  const token = requireAccessToken();
  const permissions = await apiRequest<{ items: PermissionRecord[] }>('/api/system/permissions', {
    token,
  });
  return permissions.items;
}

export async function fetchSystemMenus(): Promise<MenuResourceRecord[]> {
  const token = requireAccessToken();
  const menus = await apiRequest<{ items: MenuResourceRecord[] }>('/api/system/menus', { token });
  return menus.items;
}

export async function fetchSystemRoleList(
  query: RoleListQuery = {},
): Promise<RemoteListResult<SystemRoleRecord>> {
  const token = requireAccessToken();
  const roles = await apiRequest<{ items: RoleDefinitionListItem[] }>('/api/system/roles', {
    token,
  });
  const filteredRows = filterSystemRoles(roles.items.map(mapSystemRole), query);
  const sortedRows = sortSystemRoles(filteredRows, query);
  const page = query.page ?? 1;
  const pageSize = query.pageSize ?? 10;
  const start = (page - 1) * pageSize;
  return {
    page,
    pageSize,
    rows: sortedRows.slice(start, start + pageSize),
    total: sortedRows.length,
  };
}

export async function createSystemRole(payload: {
  category: string;
  code: string;
  description?: string;
  is_assignable?: boolean;
  name: string;
  sort_order?: number;
}): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>('/api/system/roles', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapSystemRole(role);
}

export async function updateSystemRole(
  roleId: string,
  payload: {
    category?: string;
    description?: string;
    is_assignable?: boolean;
    name?: string;
    sort_order?: number;
  },
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
  return mapSystemRole(role);
}

export async function copySystemRole(
  roleId: string,
  payload: {
    code: string;
    description?: string;
    name?: string;
  },
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/copy`, {
    body: payload,
    method: 'POST',
    token,
  });
  return mapSystemRole(role);
}

export async function setSystemRoleStatus(
  roleId: string,
  status: 'active' | 'inactive',
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const action = status === 'active' ? 'enable' : 'disable';
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/${action}`, {
    method: 'POST',
    token,
  });
  return mapSystemRole(role);
}

export async function updateSystemRolePermissions(
  roleId: string,
  permissionCodes: string[],
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/permissions`, {
    body: { permission_codes: permissionCodes },
    method: 'PUT',
    token,
  });
  return mapSystemRole(role);
}

export async function updateSystemRoleMenus(
  roleId: string,
  menuCodes: string[],
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/menus`, {
    body: { menu_codes: menuCodes },
    method: 'PUT',
    token,
  });
  return mapSystemRole(role);
}

export async function updateSystemRoleScopes(
  roleId: string,
  scopes: ScopeGrant[],
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/scopes`, {
    body: { scopes },
    method: 'PUT',
    token,
  });
  return mapSystemRole(role);
}

export async function fetchManagementUsers(
  roleDefinitions: UserRoleDefinition[] = [],
): Promise<UserRecord[]> {
  const token = requireAccessToken();
  const users = await apiRequest<ListResponse<UserListItem>>('/api/users', { token });

  return users.items.map((user) => {
    const roles = user.roles ?? [];
    return {
      displayName: user.display_name,
      id: user.id,
      roles,
      rolesText: formatUserRoles(roles, roleDefinitions),
      status: user.status === 'inactive' ? 'inactive' : 'active',
      username: user.username,
    };
  });
}

export async function fetchManagementUserList(
  roleDefinitions: UserRoleDefinition[] = [],
  query: UserListQuery = {},
): Promise<RemoteListResult<UserRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'display_name', query.displayName);
  appendQueryParam(params, 'role', query.role);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'username', query.username);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const users = await apiRequest<ListResponse<UserListItem>>(
    queryString ? `/api/users?${queryString}` : '/api/users',
    { token },
  );

  return {
    page: users.page ?? query.page ?? 1,
    pageSize: users.page_size ?? query.pageSize ?? 10,
    rows: users.items.map((user) => {
      const roles = user.roles ?? [];
      return {
        displayName: user.display_name,
        id: user.id,
        roles,
        rolesText: formatUserRoles(roles, roleDefinitions),
        status: user.status === 'inactive' ? 'inactive' : 'active',
        username: user.username,
      };
    }),
    total: users.total,
  };
}

export async function createManagementUser(payload: UserMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<UserListItem>('/api/users', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateManagementUser(userId: string, payload: UserMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<UserListItem>(`/api/users/${userId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteManagementUser(userId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/users/${userId}`, {
    method: 'DELETE',
    token,
  });
}

function mapModelGatewayConfig(config: ModelGatewayConfigListItem): ModelGatewayConfigRecord {
  const apiKeyConfigured = Boolean(config.api_key_configured);
  const embeddingConnectionMode =
    config.embedding_connection_mode === 'custom' || config.embedding_connection_mode === 'disabled'
      ? config.embedding_connection_mode
      : 'reuse_chat';
  return {
    apiKeyConfigured,
    baseUrl: config.base_url ?? '-',
    defaultChatModel: config.default_chat_model ?? '-',
    defaultEmbeddingModel: config.default_embedding_model ?? null,
    embeddingApiKeyConfigured: Boolean(config.embedding_api_key_configured),
    embeddingBaseUrl: config.embedding_base_url ?? null,
    embeddingConnectionMode,
    embeddingDimension: config.embedding_dimension ?? null,
    id: config.id,
    isDefault: Boolean(config.is_default),
    keyStatus: apiKeyConfigured ? '已配置' : '未配置',
    maxRetries: config.max_retries ?? 0,
    name: config.name,
    provider: config.provider ?? '-',
    status: normalizeModelGatewayStatus(config.status),
    timeoutSeconds: config.timeout_seconds ?? 0,
  };
}

export async function fetchModelGatewayConfigList(
  query: ModelGatewayConfigListQuery = {},
): Promise<RemoteListResult<ModelGatewayConfigRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'default_chat_model', query.defaultChatModel);
  appendQueryParam(params, 'default_embedding_model', query.defaultEmbeddingModel);
  appendQueryParam(params, 'embedding_connection_mode', query.embeddingConnectionMode);
  appendQueryParam(params, 'is_default', query.isDefault);
  appendQueryParam(params, 'name', query.name);
  appendQueryParam(params, 'provider', query.provider);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const configs = await apiRequest<ListResponse<ModelGatewayConfigListItem>>(
    queryString ? `/api/system/model-gateway-configs?${queryString}` : '/api/system/model-gateway-configs',
    { token },
  );
  return {
    page: configs.page ?? query.page ?? 1,
    pageSize: configs.page_size ?? query.pageSize ?? 10,
    rows: configs.items.map(mapModelGatewayConfig),
    total: configs.total,
  };
}

export async function fetchModelGatewayConfigs(): Promise<ModelGatewayConfigRecord[]> {
  const token = requireAccessToken();
  const configs = await apiRequest<ListResponse<ModelGatewayConfigListItem>>(
    '/api/system/model-gateway-configs',
    { token },
  );
  return configs.items.map(mapModelGatewayConfig);
}

export async function createModelGatewayConfig(payload: ModelGatewayConfigMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<ModelGatewayConfigListItem>('/api/system/model-gateway-configs', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateModelGatewayConfig(
  configId: string,
  payload: ModelGatewayConfigMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<ModelGatewayConfigListItem>(`/api/system/model-gateway-configs/${configId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function testModelGatewayConfig(
  payload: ModelGatewayConfigMutationPayload,
): Promise<ModelGatewayConfigTestResult> {
  const token = requireAccessToken();
  return apiRequest<ModelGatewayConfigTestResult>('/api/system/model-gateway-configs/test', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function deleteModelGatewayConfig(configId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(
    `/api/system/model-gateway-configs/${configId}`,
    {
      method: 'DELETE',
      token,
    },
  );
}

export type AiSkillRecord = {
  allowed_tools?: string[];
  code: string;
  id: string;
  manifest?: Record<string, unknown>;
  name: string;
  package_checksum?: string | null;
  package_entry?: string | null;
  package_files?: string[];
  package_size_bytes?: number;
  package_uri?: string | null;
  prompt_template?: string;
  requires_human_review?: boolean;
  risk_level?: string;
  source_type?: string;
  status: string;
  version?: string;
};

export type AiSkillPackageUploadOptions = {
  code: string;
  name: string;
  requiresHumanReview?: boolean;
  riskLevel?: string;
  status?: string;
  version?: string;
};

async function readUploadFileBytes(file: File): Promise<ArrayBuffer> {
  if (typeof file.arrayBuffer === 'function') {
    return file.arrayBuffer();
  }
  return new Response(file).arrayBuffer();
}

export type AiAgentRecord = {
  brain_app_id?: string;
  code: string;
  default_skill_ids?: string[];
  id: string;
  model_gateway_config_id?: string | null;
  name: string;
  status: string;
  system_prompt?: string;
  tool_policy?: Record<string, unknown>;
};

export type ScheduledJobRecord = {
  agent_id?: string | null;
  config_json?: Record<string, unknown>;
  cron_expression?: string | null;
  enabled?: boolean;
  execution_mode?: string;
  id: string;
  interval_seconds?: number | null;
  job_type: string;
  knowledge_document_ids?: string[];
  model_gateway_config_id?: string | null;
  name: string;
  next_run_at?: string | null;
  plugin_action_id?: string | null;
  plugin_connection_id?: string | null;
  plugin_input_mapping?: Record<string, unknown>;
  plugin_output_mapping?: Record<string, unknown>;
  product_id?: string | null;
  result_actions?: ScheduledJobResultAction[];
  schedule_type?: string;
  skill_ids?: string[];
  source_system?: string;
  status?: string;
  timezone?: string;
};

export type ScheduledJobResultAction = {
  channels?: string[];
  recipients?: string[];
  severity_threshold?: string;
  type: string;
  webhook_url?: string;
};

export type ScheduledJobRunRecord = {
  config_snapshot?: Record<string, unknown>;
  collector_run_id?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  finished_at?: string | null;
  id: string;
  plugin_invocation_log_id?: string | null;
  records_imported?: number;
  resolved_agent_snapshot?: Record<string, unknown>;
  resolved_plugin_snapshot?: Record<string, unknown>;
  resolved_prompt_snapshot?: Record<string, unknown>;
  resolved_skill_snapshots?: Array<Record<string, unknown>>;
  result_summary?: Record<string, unknown>;
  scheduled_job_id?: string;
  started_at?: string | null;
  status: string;
  tool_policy_snapshot?: Record<string, unknown>;
  trigger_type?: string;
};

export type PluginRecord = {
  category?: string;
  code: string;
  description?: string | null;
  id: string;
  name: string;
  protocol: string;
  risk_level?: string;
  status: string;
};

export type PluginConnectionRecord = {
  auth_config?: Record<string, unknown>;
  auth_type?: string;
  endpoint_url: string;
  environment?: string;
  id: string;
  max_retries?: number;
  name: string;
  plugin_id: string;
  request_config?: Record<string, unknown>;
  status: string;
  timeout_seconds?: number;
};

export type PluginConnectionTestResult = {
  checked_at: string;
  connection_id: string;
  diagnostics?: Array<{
    detail?: string;
    error_code?: string;
    latency_ms?: number;
    name: string;
    status: string;
    status_code?: number;
  }>;
  endpoint_url?: string;
  environment?: string;
  error_code?: string | null;
  error_message?: string | null;
  latency_ms: number;
  mocked?: boolean;
  plugin_id: string;
  protocol: string;
  request_summary?: Record<string, unknown>;
  response_summary?: Record<string, unknown>;
  status: string;
};

export type PluginActionRecord = {
  action_type: string;
  code: string;
  connection_id?: string | null;
  description?: string | null;
  id: string;
  input_schema?: Record<string, unknown>;
  name: string;
  output_schema?: Record<string, unknown>;
  plugin_id: string;
  request_config?: Record<string, unknown>;
  requires_human_review?: boolean;
  result_mapping?: Record<string, unknown>;
  status: string;
};

export type PluginInvocationLogRecord = {
  action_id: string;
  connection_id?: string | null;
  error_message?: string | null;
  id: string;
  latency_ms?: number;
  plugin_id: string;
  request_summary?: Record<string, unknown>;
  response_summary?: Record<string, unknown>;
  scheduled_job_id?: string | null;
  scheduled_job_run_id?: string | null;
  status: string;
  trigger_type?: string;
};

export type PluginSystemVariableRecord = {
  description?: string;
  expression: string;
  label: string;
  value: string;
};

export type PluginActionTrialResult = {
  action_id: string;
  connection_id: string;
  error_code?: string | null;
  error_message?: string | null;
  latency_ms: number;
  mapping_hits?: Array<{
    key: string;
    matched: boolean;
    path: string;
    value_preview?: unknown;
  }>;
  plugin_id: string;
  request_preview?: Record<string, unknown>;
  response_summary?: Record<string, unknown>;
  status: string;
};

export async function fetchPlugins(): Promise<PluginRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<PluginRecord>>('/api/system/plugins', { token });
  return response.items;
}

export async function createPlugin(payload: Partial<PluginRecord>) {
  const token = requireAccessToken();
  return apiRequest<PluginRecord>('/api/system/plugins', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updatePlugin(pluginId: string, payload: Partial<PluginRecord>) {
  const token = requireAccessToken();
  return apiRequest<PluginRecord>(`/api/system/plugins/${pluginId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deletePlugin(pluginId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/system/plugins/${pluginId}`, {
    method: 'DELETE',
    token,
  });
}

export async function fetchPluginConnections(
  query: { pluginId?: string; status?: string } = {},
): Promise<PluginConnectionRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'plugin_id', query.pluginId);
  appendQueryParam(params, 'status', query.status);
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<PluginConnectionRecord>>(
    queryString ? `/api/system/plugin-connections?${queryString}` : '/api/system/plugin-connections',
    { token },
  );
  return response.items;
}

export async function createPluginConnection(payload: Partial<PluginConnectionRecord>) {
  const token = requireAccessToken();
  return apiRequest<PluginConnectionRecord>('/api/system/plugin-connections', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updatePluginConnection(
  connectionId: string,
  payload: Partial<PluginConnectionRecord>,
) {
  const token = requireAccessToken();
  return apiRequest<PluginConnectionRecord>(`/api/system/plugin-connections/${connectionId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deletePluginConnection(connectionId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/system/plugin-connections/${connectionId}`, {
    method: 'DELETE',
    token,
  });
}

export async function testPluginConnection(connectionId: string) {
  const token = requireAccessToken();
  return apiRequest<PluginConnectionTestResult>(`/api/system/plugin-connections/${connectionId}/test`, {
    method: 'POST',
    token,
  });
}

export async function fetchPluginSystemVariables(timezone = 'Asia/Shanghai') {
  const token = requireAccessToken();
  const params = new URLSearchParams({ timezone });
  const response = await apiRequest<{ items: PluginSystemVariableRecord[]; timezone: string }>(
    `/api/system/plugin-system-variables?${params.toString()}`,
    { token },
  );
  return response;
}

export async function fetchPluginActions(
  query: { pluginId?: string; status?: string } = {},
): Promise<PluginActionRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'plugin_id', query.pluginId);
  appendQueryParam(params, 'status', query.status);
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<PluginActionRecord>>(
    queryString ? `/api/system/plugin-actions?${queryString}` : '/api/system/plugin-actions',
    { token },
  );
  return response.items;
}

export async function createPluginAction(payload: Partial<PluginActionRecord>) {
  const token = requireAccessToken();
  return apiRequest<PluginActionRecord>('/api/system/plugin-actions', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updatePluginAction(actionId: string, payload: Partial<PluginActionRecord>) {
  const token = requireAccessToken();
  return apiRequest<PluginActionRecord>(`/api/system/plugin-actions/${actionId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deletePluginAction(actionId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/system/plugin-actions/${actionId}`, {
    method: 'DELETE',
    token,
  });
}

export async function invokePluginAction(actionId: string, inputPayload: Record<string, unknown> = {}) {
  const token = requireAccessToken();
  return apiRequest<PluginInvocationLogRecord>(`/api/system/plugin-actions/${actionId}/invoke`, {
    body: { input_payload: inputPayload, trigger_type: 'manual' },
    method: 'POST',
    token,
  });
}

export async function trialPluginAction(
  actionId: string,
  payload: { connection_id?: string | null; input_payload?: Record<string, unknown> } = {},
) {
  const token = requireAccessToken();
  return apiRequest<PluginActionTrialResult>(`/api/system/plugin-actions/${actionId}/trial`, {
    body: {
      connection_id: payload.connection_id,
      input_payload: payload.input_payload ?? {},
    },
    method: 'POST',
    token,
  });
}

export async function fetchPluginInvocationLogs(
  query: { actionId?: string; scheduledJobId?: string; status?: string } = {},
): Promise<PluginInvocationLogRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'action_id', query.actionId);
  appendQueryParam(params, 'scheduled_job_id', query.scheduledJobId);
  appendQueryParam(params, 'status', query.status);
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<PluginInvocationLogRecord>>(
    queryString ? `/api/system/plugin-invocation-logs?${queryString}` : '/api/system/plugin-invocation-logs',
    { token },
  );
  return response.items;
}

export async function fetchAiSkills(): Promise<AiSkillRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<AiSkillRecord>>('/api/system/ai-skills', {
    token,
  });
  return response.items;
}

export async function createAiSkill(payload: Partial<AiSkillRecord>) {
  const token = requireAccessToken();
  return apiRequest<AiSkillRecord>('/api/system/ai-skills', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function uploadAiSkillPackage(
  file: File,
  options: AiSkillPackageUploadOptions,
) {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'code', options.code);
  appendQueryParam(params, 'name', options.name);
  appendQueryParam(params, 'version', options.version ?? '1.0.0');
  appendQueryParam(params, 'status', options.status ?? 'active');
  appendQueryParam(params, 'risk_level', options.riskLevel ?? 'medium');
  appendQueryParam(
    params,
    'requires_human_review',
    options.requiresHumanReview ? 'true' : 'false',
  );
  const response = await fetch(`${API_BASE_URL}/api/system/ai-skills/upload?${params}`, {
    body: await readUploadFileBytes(file),
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/zip',
    },
    method: 'POST',
  });
  if (!response.ok) {
    let payload: ApiErrorPayload | undefined;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = undefined;
    }
    throw new ApiRequestError({
      code: payload?.detail?.code,
      message: payload?.detail?.message ?? `API request failed: ${response.status}`,
      status: response.status,
      traceId: payload?.detail?.trace_id,
    });
  }
  const payload = (await response.json()) as ApiEnvelope<AiSkillRecord>;
  return payload.data;
}

export async function updateAiSkill(skillId: string, payload: Partial<AiSkillRecord>) {
  const token = requireAccessToken();
  return apiRequest<AiSkillRecord>(`/api/system/ai-skills/${skillId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function fetchAiAgents(): Promise<AiAgentRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<AiAgentRecord>>('/api/system/ai-agents', {
    token,
  });
  return response.items;
}

export async function createAiAgent(payload: Partial<AiAgentRecord>) {
  const token = requireAccessToken();
  return apiRequest<AiAgentRecord>('/api/system/ai-agents', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateAiAgent(agentId: string, payload: Partial<AiAgentRecord>) {
  const token = requireAccessToken();
  return apiRequest<AiAgentRecord>(`/api/system/ai-agents/${agentId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function fetchScheduledJobs(): Promise<ScheduledJobRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<ScheduledJobRecord>>('/api/system/scheduled-jobs', {
    token,
  });
  return response.items;
}

export async function createScheduledJob(payload: Partial<ScheduledJobRecord>) {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobRecord>('/api/system/scheduled-jobs', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateScheduledJob(jobId: string, payload: Partial<ScheduledJobRecord>) {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobRecord>(`/api/system/scheduled-jobs/${jobId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteScheduledJob(jobId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/system/scheduled-jobs/${jobId}`, {
    method: 'DELETE',
    token,
  });
}

export async function runScheduledJob(jobId: string) {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobRunRecord>(`/api/system/scheduled-jobs/${jobId}/run`, {
    method: 'POST',
    token,
  });
}

export async function fetchScheduledJobRuns(
  query: { scheduledJobId?: string; status?: string } = {},
): Promise<ScheduledJobRunRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'scheduled_job_id', query.scheduledJobId);
  appendQueryParam(params, 'status', query.status);
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<ScheduledJobRunRecord>>(
    queryString ? `/api/system/scheduled-job-runs?${queryString}` : '/api/system/scheduled-job-runs',
    { token },
  );
  return response.items;
}

export type CodeInspectionReportRecord = {
  branch?: string | null;
  commit_sha?: string | null;
  created_at?: string;
  created_bug_ids?: string[];
  finding_count: number;
  id: string;
  notification_ids?: string[];
  product_id?: string | null;
  repository_id?: string | null;
  repository_name?: string | null;
  repository_path?: string | null;
  risk_level: string;
  severe_finding_count: number;
  status: string;
  summary?: string;
};

export type CodeInspectionFindingRecord = {
  category?: string;
  created_bug_id?: string | null;
  description?: string;
  file_path?: string;
  id: string;
  line_number?: number | null;
  recommendation?: string;
  report_id: string;
  rule_id?: string;
  severity: string;
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
  notifications: CodeInspectionNotificationRecord[];
  report: CodeInspectionReportRecord & Record<string, unknown>;
};

export type CodeInspectionListQuery = {
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

export async function fetchCodeInspectionReports(query: CodeInspectionListQuery = {}) {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'page', query.page ?? 1);
  appendQueryParam(params, 'page_size', query.pageSize ?? 10);
  appendQueryParam(params, 'product_id', query.productId);
  appendQueryParam(params, 'repository_id', query.repositoryId);
  appendQueryParam(params, 'risk_level', query.riskLevel);
  appendQueryParam(params, 'sort_by', query.sortField);
  appendQueryParam(params, 'sort_order', query.sortOrder === 'ascend' ? 'asc' : 'desc');
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'title', query.title);
  const response = await apiRequest<ListResponse<CodeInspectionReportRecord>>(
    `/api/governance/code-inspections?${params.toString()}`,
    { token },
  );
  return {
    page: response.page ?? query.page ?? 1,
    pageSize: response.page_size ?? query.pageSize ?? 10,
    rows: response.items,
    total: response.total,
  };
}

export async function fetchCodeInspectionDetail(reportId: string): Promise<CodeInspectionDetailRecord> {
  const token = requireAccessToken();
  return apiRequest<CodeInspectionDetailRecord>(`/api/governance/code-inspections/${reportId}`, {
    token,
  });
}

function mapRequirementRecord(requirement: RequirementListItem): RequirementRecord {
  return {
    content: requirement.content,
    id: requirement.id,
    moduleCode: requirement.module_code ?? undefined,
    owner: requirement.assignee ?? requirement.created_by ?? '-',
    priority: normalizePriority(requirement.priority),
    product: requirement.product_code ?? requirement.product_name ?? requirement.product_id,
    productId: requirement.product_id,
    source: requirement.source ?? 'business_department',
    status: normalizeRequirementStatus(requirement.status),
    title: requirement.title,
    createdAt: formatListDate(requirement.created_at),
    updatedAt: formatListDate(requirement.updated_at ?? requirement.created_at),
    versionId: requirement.version_id,
    versionName: requirement.version_id
      ? (requirement.version_name ?? requirement.version_code ?? requirement.version_id)
      : '未排期',
  };
}

function mapTaskRecord(task: TaskListItem): TaskCenterTaskRecord {
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

function mapRequirementFullChain(
  chain: RequirementFullChainResponse,
): RequirementFullChainRecord {
  const summary = chain.summary ?? {};
  return {
    aiTasks: (chain.ai_tasks ?? []).map(mapTaskRecord),
    bugs: (chain.bugs ?? []).map(mapBugRecord),
    codeReviewReports: (chain.code_review_reports ?? []).map((report) => ({
      executor: report.executor,
      findings: report.findings ?? [],
      gitlabWritebackPerformed: report.gitlab_writeback_performed ?? false,
      id: report.id,
      riskLevel: report.risk_level ?? '-',
      status: report.status ?? '-',
      summary: report.summary ?? report.id,
    })),
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
      createdAt: formatListDate(formatUnknownValue(release.deployed_at ?? release.started_at ?? release.created_at)),
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
      bugs: normalizeDashboardCount(summary.bugs),
      codeReviewReports: normalizeDashboardCount(summary.code_review_reports),
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

export async function fetchManagementRequirements(): Promise<RequirementRecord[]> {
  const token = requireAccessToken();
  const requirements = await apiRequest<ListResponse<RequirementListItem>>('/api/requirements', {
    token,
  });

  return requirements.items.map(mapRequirementRecord);
}

export async function fetchManagementRequirementList(
  query: RequirementListQuery = {},
): Promise<RemoteListResult<RequirementRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'priority', query.priority);
  appendQueryParam(params, 'product', query.product);
  appendQueryParam(params, 'source', query.source);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'title', query.title);
  appendQueryParam(params, 'version', query.version);
  appendQueryParam(params, 'version_id', query.versionId);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const requirements = await apiRequest<ListResponse<RequirementListItem>>(
    queryString ? `/api/requirements?${queryString}` : '/api/requirements',
    { token },
  );

  return {
    page: requirements.page ?? query.page ?? 1,
    pageSize: requirements.page_size ?? query.pageSize ?? 10,
    rows: requirements.items.map(mapRequirementRecord),
    total: requirements.total,
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

export async function createManagementRequirement(payload: RequirementMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<RequirementResponse>('/api/requirements', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateManagementRequirement(
  requirementId: string,
  payload: RequirementMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<RequirementResponse>(`/api/requirements/${requirementId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function batchScheduleRequirements(
  payload: RequirementBatchSchedulePayload,
): Promise<RequirementBatchScheduleResult> {
  const token = requireAccessToken();
  const result = await apiRequest<RequirementBatchScheduleResponse>(
    '/api/requirements/batch-schedule',
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return {
    batchId: result.batch_id,
    productId: result.product_id,
    reason: result.reason,
    skipped: result.skipped,
    skippedCount: result.skipped_count,
    updated: result.updated.map(mapRequirementRecord),
    updatedCount: result.updated_count,
    versionId: result.version_id,
  };
}

export async function batchAssignRequirementOwner(
  payload: RequirementBatchAssignOwnerPayload,
): Promise<RequirementBatchAssignOwnerResult> {
  const token = requireAccessToken();
  const result = await apiRequest<RequirementBatchAssignOwnerResponse>(
    '/api/requirements/batch-assign-owner',
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return {
    assignee: result.assignee,
    batchId: result.batch_id,
    reason: result.reason,
    skipped: result.skipped,
    skippedCount: result.skipped_count,
    updated: result.updated.map(mapRequirementRecord),
    updatedCount: result.updated_count,
  };
}

export async function batchAdvanceRequirementStatus(
  payload: RequirementBatchAdvanceStatusPayload,
): Promise<RequirementBatchAdvanceStatusResult> {
  const token = requireAccessToken();
  const result = await apiRequest<RequirementBatchAdvanceStatusResponse>(
    '/api/requirements/batch-advance-status',
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return {
    batchId: result.batch_id,
    reason: result.reason,
    skipped: result.skipped,
    skippedCount: result.skipped_count,
    targetStatus: normalizeRequirementStatus(result.target_status),
    updated: result.updated.map(mapRequirementRecord),
    updatedCount: result.updated_count,
  };
}

export async function batchGenerateRequirementTasks(
  payload: RequirementBatchGenerateTasksPayload,
): Promise<RequirementBatchGenerateTasksResult> {
  const token = requireAccessToken();
  const result = await apiRequest<RequirementBatchGenerateTasksResponse>(
    '/api/requirements/batch-generate-tasks',
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return {
    batchId: result.batch_id,
    generated: result.generated,
    generatedCount: result.generated_count,
    productId: result.product_id,
    reason: result.reason,
    skipped: result.skipped,
    skippedCount: result.skipped_count,
  };
}

export async function deleteManagementRequirement(requirementId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/requirements/${requirementId}`, {
    method: 'DELETE',
    token,
  });
}

export async function approveManagementRequirement(requirementId: string) {
  const token = requireAccessToken();
  return apiRequest<RequirementResponse>(`/api/requirements/${requirementId}/approve`, {
    body: {},
    method: 'POST',
    token,
  });
}

export async function rejectManagementRequirement(requirementId: string, rejectionReason: string) {
  const token = requireAccessToken();
  return apiRequest<RequirementResponse>(`/api/requirements/${requirementId}/reject`, {
    body: { rejection_reason: rejectionReason },
    method: 'POST',
    token,
  });
}

export async function generateRequirementTask(requirementId: string) {
  const token = requireAccessToken();
  return apiRequest<{ task_id: string; task_status: string; task_type: string }>(
    `/api/requirements/${requirementId}/generate-task`,
    {
      method: 'POST',
      token,
    },
  );
}

export async function fetchManagementKnowledge(): Promise<KnowledgeRecord[]> {
  const token = requireAccessToken();
  const documents = await apiRequest<ListResponse<KnowledgeDocumentListItem>>(
    '/api/knowledge/documents',
    { token },
  );

  return documents.items.map(mapKnowledgeRecord);
}

function mapKnowledgeRecord(document: KnowledgeDocumentListItem): KnowledgeRecord {
  return {
    activeChunkSetId: document.active_chunk_set_id ?? undefined,
    content: document.content,
    documentType: document.doc_type ?? '-',
    folderId: document.folder_id ?? undefined,
    folderPath: document.folder_path ?? undefined,
    id: document.id,
    indexError: document.index_error,
    knowledgeSpaceId: document.knowledge_space_id ?? undefined,
    ownerRole: document.permission_roles?.join(', ') || '-',
    permissionRoles: document.permission_roles,
    sourceAssetId: document.source_asset_id ?? undefined,
    status: normalizeKnowledgeStatus(document.index_status),
    tags: document.tags,
    title: document.title,
    updatedAt: formatListDate(document.updated_at ?? document.created_at),
    vectorIndexError: document.vector_index_error,
  };
}

export async function fetchManagementKnowledgeList(
  query: KnowledgeListQuery = {},
): Promise<RemoteListResult<KnowledgeRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'doc_type', query.documentType);
  appendQueryParam(params, 'knowledge_space_id', query.knowledgeSpaceId);
  appendQueryParam(params, 'folder_id', query.folderId);
  appendQueryParam(params, 'permission_role', query.ownerRole);
  appendQueryParam(params, 'index_status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const documents = await apiRequest<ListResponse<KnowledgeDocumentListItem>>(
    queryString ? `/api/knowledge/documents?${queryString}` : '/api/knowledge/documents',
    { token },
  );

  return {
    page: documents.page ?? query.page ?? 1,
    pageSize: documents.page_size ?? query.pageSize ?? 10,
    rows: documents.items.map(mapKnowledgeRecord),
    total: documents.total,
  };
}

function mapKnowledgeSpace(item: KnowledgeSpaceListItem): KnowledgeSpaceRecord {
  return {
    code: item.code,
    description: item.description,
    id: item.id,
    name: item.name,
  };
}

function mapKnowledgeFolder(item: KnowledgeFolderListItem): KnowledgeFolderRecord {
  return {
    id: item.id,
    knowledgeSpaceId: item.knowledge_space_id,
    name: item.name,
    parentFolderId: item.parent_folder_id,
    path: item.path ?? item.name,
  };
}

function mapKnowledgeAsset(item: KnowledgeAssetListItem): KnowledgeAssetRecord {
  return {
    assetType: item.asset_type ?? '-',
    filename: item.filename ?? item.id,
    id: item.id,
    mimeType: item.mime_type,
    sizeBytes: Number(item.size_bytes ?? 0),
    storageProvider: item.storage_provider,
  };
}

function mapKnowledgeImportJob(item: KnowledgeImportJobListItem): KnowledgeImportJobRecord {
  return {
    assetFilename: item.asset_filename,
    chunkStrategy: item.chunk_strategy,
    documentId: item.document_id,
    documentTitle: item.document_title,
    errorMessage: item.error_message ?? undefined,
    folderPath: item.folder_path,
    id: item.id,
    parserEngine: item.parser_engine,
    progress: Number(item.progress ?? 0),
    status: item.status ?? '-',
    updatedAt: formatListDate(item.updated_at),
  };
}

function mapKnowledgeChunkSet(item: KnowledgeChunkSetListItem): KnowledgeChunkSetRecord {
  return {
    activatedAt: formatListDate(item.activated_at),
    chunkCount: Number(item.chunk_count ?? 0),
    chunkStrategy: item.chunk_strategy ?? '-',
    id: item.id,
    isActive: Boolean(item.is_active),
    parserEngine: item.parser_engine ?? '-',
    status: item.status ?? '-',
  };
}

function mapKnowledgeChunk(item: KnowledgeChunkListItem): KnowledgeChunkRecord {
  return {
    chunkIndex: Number(item.chunk_index ?? 0),
    chunkRole: item.metadata?.chunk_role,
    chunkSetId: item.chunk_set_id,
    content: item.content ?? '',
    heading: item.metadata?.heading,
    id: item.id,
    imageCount: item.metadata?.image_count,
    imageRefs: item.metadata?.image_refs,
    parentChunkId: item.parent_chunk_id,
    parentContent: item.parent_content,
    pageNumber: item.metadata?.page_number,
    sectionTitle: item.metadata?.section_title,
    sourceAssetType: item.metadata?.source_asset_type,
    sourceKind: item.metadata?.source_kind,
    splitPattern: item.metadata?.split_pattern,
    tableColumns: item.metadata?.columns,
    tableCount: item.metadata?.table_count,
    tableIndex: item.metadata?.table_index,
  };
}

function mapKnowledgeImportWorkerStatus(
  item: KnowledgeImportWorkerStatusItem,
): KnowledgeImportWorkerStatusRecord {
  return {
    activeJobId: item.active_job_id ?? null,
    enabled: Boolean(item.enabled),
    failedCount: Number(item.failed_count ?? 0),
    pendingCount: Number(item.pending_count ?? 0),
    processedCount: Number(item.processed_count ?? 0),
    queuedJobIds: item.queued_job_ids ?? [],
    running: Boolean(item.running),
    workerId: item.worker_id ?? null,
  };
}

export async function fetchKnowledgeSpaces(): Promise<KnowledgeSpaceRecord[]> {
  const token = requireAccessToken();
  const spaces = await apiRequest<ListResponse<KnowledgeSpaceListItem>>('/api/knowledge/spaces', {
    token,
  });
  return spaces.items.map(mapKnowledgeSpace);
}

export async function createKnowledgeSpace(payload: {
  code: string;
  description?: string;
  name: string;
}): Promise<KnowledgeSpaceRecord> {
  const token = requireAccessToken();
  const space = await apiRequest<KnowledgeSpaceListItem>('/api/knowledge/spaces', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapKnowledgeSpace(space);
}

export async function fetchKnowledgeFolders(spaceId: string): Promise<KnowledgeFolderRecord[]> {
  const token = requireAccessToken();
  const folders = await apiRequest<ListResponse<KnowledgeFolderListItem>>(
    `/api/knowledge/spaces/${spaceId}/folders`,
    { token },
  );
  return folders.items.map(mapKnowledgeFolder);
}

export async function createKnowledgeFolder(
  spaceId: string,
  payload: { name: string; parent_folder_id?: string },
): Promise<KnowledgeFolderRecord> {
  const token = requireAccessToken();
  const folder = await apiRequest<KnowledgeFolderListItem>(
    `/api/knowledge/spaces/${spaceId}/folders`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return mapKnowledgeFolder(folder);
}

export async function updateKnowledgeFolder(
  folderId: string,
  payload: {
    name?: string;
    parent_folder_id?: string | null;
    sort_order?: number;
    status?: string;
  },
): Promise<KnowledgeFolderRecord> {
  const token = requireAccessToken();
  const folder = await apiRequest<KnowledgeFolderListItem>(`/api/knowledge/folders/${folderId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
  return mapKnowledgeFolder(folder);
}

export async function fetchKnowledgeDocumentAssets(
  documentId: string,
): Promise<KnowledgeAssetRecord[]> {
  const token = requireAccessToken();
  const assets = await apiRequest<ListResponse<KnowledgeAssetListItem>>(
    `/api/knowledge/documents/${documentId}/assets`,
    { token },
  );
  return assets.items.map(mapKnowledgeAsset);
}

export async function fetchKnowledgeImportJobs(params: {
  knowledgeSpaceId?: string;
  status?: string;
} = {}): Promise<KnowledgeImportJobRecord[]> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  appendQueryParam(query, 'knowledge_space_id', params.knowledgeSpaceId);
  appendQueryParam(query, 'status', params.status);
  const queryString = query.toString();
  const importJobs = await apiRequest<ListResponse<KnowledgeImportJobListItem>>(
    queryString ? `/api/knowledge/import-jobs?${queryString}` : '/api/knowledge/import-jobs',
    { token },
  );
  return importJobs.items.map(mapKnowledgeImportJob);
}

export async function fetchKnowledgeImportWorkerStatus(): Promise<KnowledgeImportWorkerStatusRecord> {
  const token = requireAccessToken();
  const status = await apiRequest<KnowledgeImportWorkerStatusItem>(
    '/api/knowledge/import-worker/status',
    { token },
  );
  return mapKnowledgeImportWorkerStatus(status);
}

export async function runKnowledgeImportJob(jobId: string) {
  const token = requireAccessToken();
  return apiRequest<{ import_job: KnowledgeImportJobListItem }>(
    `/api/knowledge/import-jobs/${jobId}/run`,
    { method: 'POST', token },
  );
}

export async function retryKnowledgeImportJob(jobId: string) {
  const token = requireAccessToken();
  return apiRequest<{ import_job: KnowledgeImportJobListItem }>(
    `/api/knowledge/import-jobs/${jobId}/retry`,
    { method: 'POST', token },
  );
}

export async function cancelKnowledgeImportJob(jobId: string) {
  const token = requireAccessToken();
  return apiRequest<{ import_job: KnowledgeImportJobListItem }>(
    `/api/knowledge/import-jobs/${jobId}/cancel`,
    { method: 'POST', token },
  );
}

export async function fetchKnowledgeChunkSets(documentId: string): Promise<KnowledgeChunkSetRecord[]> {
  const token = requireAccessToken();
  const chunkSets = await apiRequest<ListResponse<KnowledgeChunkSetListItem>>(
    `/api/knowledge/documents/${documentId}/chunk-sets`,
    { token },
  );
  return chunkSets.items.map(mapKnowledgeChunkSet);
}

export async function fetchKnowledgeChunks(
  documentId: string,
  chunkSetId?: string,
): Promise<KnowledgeChunkRecord[]> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  appendQueryParam(query, 'chunk_set_id', chunkSetId);
  const queryString = query.toString();
  const chunks = await apiRequest<ListResponse<KnowledgeChunkListItem>>(
    queryString
      ? `/api/knowledge/documents/${documentId}/chunks?${queryString}`
      : `/api/knowledge/documents/${documentId}/chunks`,
    { token },
  );
  return chunks.items.map(mapKnowledgeChunk);
}

export async function activateKnowledgeChunkSet(documentId: string, chunkSetId: string) {
  const token = requireAccessToken();
  return apiRequest<{ document: KnowledgeDocumentListItem }>(
    `/api/knowledge/documents/${documentId}/chunk-sets/${chunkSetId}/activate`,
    { method: 'POST', token },
  );
}

export async function reparseKnowledgeDocument(
  documentId: string,
  payload: { chunk_strategy?: string; parser_engine?: string },
) {
  const token = requireAccessToken();
  return apiRequest<{ import_job: KnowledgeImportJobListItem }>(
    `/api/knowledge/documents/${documentId}/reparse`,
    { body: payload, method: 'POST', token },
  );
}

export async function batchMoveKnowledgeDocuments(documentIds: string[], folderId?: string | null) {
  const token = requireAccessToken();
  return apiRequest<{ skipped: Array<{ id: string; reason: string }>; updated: string[] }>(
    '/api/knowledge/documents/batch-move',
    {
      body: { document_ids: documentIds, folder_id: folderId ?? null },
      method: 'POST',
      token,
    },
  );
}

export async function uploadKnowledgeDocument(payload: KnowledgeDocumentUploadPayload) {
  const token = requireAccessToken();
  return apiRequest<{ document: KnowledgeDocumentListItem }>('/api/knowledge/documents/upload', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function createManagementKnowledgeDocument(payload: KnowledgeDocumentMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<{ id: string }>('/api/knowledge/documents', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateManagementKnowledgeDocument(
  documentId: string,
  payload: KnowledgeDocumentMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<{ id: string }>(`/api/knowledge/documents/${documentId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteManagementKnowledgeDocument(documentId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/knowledge/documents/${documentId}`, {
    method: 'DELETE',
    token,
  });
}

export async function retryKnowledgeDocumentIndex(documentId: string) {
  const token = requireAccessToken();
  return apiRequest<{ id: string; index_error?: string | null; index_status?: string }>(
    `/api/knowledge/documents/${documentId}/retry-index`,
    {
      method: 'POST',
      token,
    },
  );
}

export async function fetchManagementAudit(): Promise<AuditRecord[]> {
  const token = requireAccessToken();
  const events = await apiRequest<ListResponse<AuditEventListItem>>('/api/audit/events', { token });

  return events.items.map(mapAuditRecord);
}

function mapAuditRecord(event: AuditEventListItem): AuditRecord {
  return {
    actor: event.actor_id ?? '-',
    aiTaskId: event.ai_task_id ?? undefined,
    eventType: event.event_type,
    id: event.id,
    payload: event.payload,
    result: event.result === 'failed' ? 'failed' : 'success',
    subject:
      event.subject_type && event.subject_id ? `${event.subject_type}: ${event.subject_id}` : '-',
    subjectId: event.subject_id,
    subjectType: event.subject_type,
    timestamp: formatListDate(event.created_at),
  };
}

export async function fetchManagementAuditList(
  query: AuditListQuery = {},
): Promise<RemoteListResult<AuditRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'actor', query.actor);
  appendQueryParam(params, 'event_type', query.eventType);
  appendQueryParam(params, 'result', query.result);
  appendQueryParam(params, 'subject', query.subject);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const events = await apiRequest<ListResponse<AuditEventListItem>>(
    queryString ? `/api/audit/events?${queryString}` : '/api/audit/events',
    { token },
  );

  return {
    page: events.page ?? query.page ?? 1,
    pageSize: events.page_size ?? query.pageSize ?? 10,
    rows: events.items.map(mapAuditRecord),
    total: events.total,
  };
}

function mapLifecycleRelation(item: LifecycleRelationItem): LifecycleRelationRecord {
  return {
    relationType: formatUnknownValue(item.relation_type),
    subjectId: formatUnknownValue(item.subject_id),
    subjectType: formatUnknownValue(item.subject_type),
    summary: formatUnknownValue(item.summary),
  };
}

export async function fetchLifecycleContext(params: {
  productId?: string;
  subjectId?: string;
  subjectType?: string;
}): Promise<LifecycleContextRecord> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  if (params.subjectType) {
    query.set('subject_type', params.subjectType);
  }
  if (params.subjectId) {
    query.set('subject_id', params.subjectId);
  }
  if (params.productId) {
    query.set('product_id', params.productId);
  }
  const context = await apiRequest<LifecycleContextResponse>(
    `/api/lifecycle/context?${query.toString()}`,
    { token },
  );
  const summary = context.summary ?? {};
  return {
    downstream: (context.downstream ?? []).map(mapLifecycleRelation),
    missingContext: context.missing_context ?? [],
    riskSignals: (context.risk_signals ?? []).map((item) => ({
      impactSummary: formatUnknownValue(item.impact_summary),
      recommendation: formatUnknownValue(item.recommendation),
      riskType: formatUnknownValue(item.risk_type),
      severity: formatUnknownValue(item.severity),
      sourceSubjectId: formatUnknownValue(item.source_subject_id),
      sourceSubjectType: formatUnknownValue(item.source_subject_type),
    })),
    status: formatUnknownValue(context.status),
    summary: {
      downstreamCount: normalizeDashboardCount(summary.downstream_count),
      riskCount: normalizeDashboardCount(summary.risk_count),
      upstreamCount: normalizeDashboardCount(summary.upstream_count),
    },
    upstream: (context.upstream ?? []).map(mapLifecycleRelation),
  };
}

export async function fetchManagementBugs(): Promise<BugRecord[]> {
  const token = requireAccessToken();
  const bugs = await apiRequest<ListResponse<BugListItem>>('/api/bugs', { token });

  return bugs.items.map((bug) => ({
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
    versionName: bug.version_id
      ? formatUnknownValue(bug.version_name ?? bug.version_code ?? bug.version_id)
      : '未关联',
  }));
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
    versionName: bug.version_id
      ? formatUnknownValue(bug.version_name ?? bug.version_code ?? bug.version_id)
      : '未关联',
  };
}

export async function fetchManagementBugList(
  query: BugListQuery = {},
): Promise<RemoteListResult<BugRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'module', query.module);
  appendQueryParam(params, 'severity', query.severity);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'title', query.title);
  appendQueryParam(params, 'version', query.version);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const bugs = await apiRequest<ListResponse<BugListItem>>(
    queryString ? `/api/bugs?${queryString}` : '/api/bugs',
    { token },
  );

  return {
    page: bugs.page ?? query.page ?? 1,
    pageSize: bugs.page_size ?? query.pageSize ?? 10,
    rows: bugs.items.map(mapBugRecord),
    total: bugs.total,
  };
}

export async function createManagementBug(payload: BugMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<{ id: string }>('/api/bugs', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateManagementBug(bugId: string, payload: BugMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<{ id: string }>(`/api/bugs/${bugId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function batchUpdateManagementBugs(
  payload: BugBatchUpdatePayload,
): Promise<BugBatchUpdateResult> {
  const token = requireAccessToken();
  const result = await apiRequest<{
    batch_id: string;
    skipped?: Array<{ code?: string; id?: string; message?: string }>;
    skipped_count?: number;
    updated?: BugListItem[];
    updated_count?: number;
  }>('/api/bugs/batch-update', {
    body: payload,
    method: 'POST',
    token,
  });

  return {
    batchId: result.batch_id,
    skipped: (result.skipped ?? []).map((item) => ({
      code: item.code ?? 'UNKNOWN',
      id: item.id ?? '-',
      message: item.message ?? '-',
    })),
    skippedCount: normalizeDashboardCount(result.skipped_count),
    updated: (result.updated ?? []).map(mapBugRecord),
    updatedCount: normalizeDashboardCount(result.updated_count),
  };
}

export async function deleteManagementBug(bugId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/bugs/${bugId}`, {
    method: 'DELETE',
    token,
  });
}

function appendQueryParam(params: URLSearchParams, key: string, value?: string | number) {
  if (value === undefined || value === null || value === '') {
    return;
  }
  params.set(key, String(value));
}

function appendRemoteListParams(params: URLSearchParams, query: RemoteListQuery) {
  appendQueryParam(params, 'page', query.page ?? 1);
  appendQueryParam(params, 'page_size', query.pageSize ?? 10);
  appendQueryParam(params, 'sort_by', query.sortField);
  appendQueryParam(
    params,
    'sort_order',
    query.sortOrder === 'ascend' ? 'asc' : query.sortOrder === 'descend' ? 'desc' : undefined,
  );
}

export async function fetchTaskCenterTasks(
  query: TaskCenterTaskQuery = {},
): Promise<TaskCenterTaskListResult> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'created_by', query.owner);
  appendQueryParam(params, 'product_id', query.productId);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'task_type', query.taskType);
  appendQueryParam(params, 'created_from', query.createdFrom);
  appendQueryParam(params, 'created_to', query.createdTo);
  appendRemoteListParams(params, query);
  const taskQueryString = params.toString();
  const taskPath = taskQueryString ? `/api/ai-tasks?${taskQueryString}` : '/api/ai-tasks';
  const tasks = await apiRequest<ListResponse<TaskListItem>>(taskPath, { token });

  return {
    page: tasks.page ?? query.page ?? 1,
    pageSize: tasks.page_size ?? query.pageSize ?? 10,
    rows: tasks.items.map(mapTaskRecord),
    total: tasks.total,
  };
}

export async function fetchTaskCenterTaskDetail(
  taskId: string,
): Promise<TaskCenterTaskDetailRecord> {
  const token = requireAccessToken();
  const detail = await apiRequest<TaskDetailItem>(`/api/ai-tasks/${taskId}`, { token });
  const input = normalizeObjectRecord(detail.input) ?? {};
  const productContext =
    normalizeObjectRecord(input.product_context) ??
    normalizeObjectRecord(detail.product_context) ??
    {};
  const product = normalizeObjectRecord(productContext.product) ?? {};
  const version = normalizeObjectRecord(productContext.version) ?? {};
  const module = normalizeObjectRecord(productContext.module) ?? {};
  const requirementSnapshot =
    normalizeObjectRecord(input.requirement_snapshot) ??
    normalizeObjectRecord(detail.requirement_snapshot) ??
    {};
  const output = detail.output ?? detail.output_json;
  const outputRecord = normalizeObjectRecord(output);
  const pendingReview = normalizeObjectRecord(detail.pending_review);
  const graphRunIds = Array.isArray(detail.graph_runs)
    ? detail.graph_runs
        .map((run) => {
          const graphRun = normalizeObjectRecord(run);
          return formatUnknownValue(graphRun?.id ?? graphRun?.status ?? run);
        })
        .filter((runId) => runId !== '-')
    : [];

  return {
    createdAt: formatListDate(detail.created_at ?? detail.updated_at),
    createdAtValue: detail.created_at ?? detail.updated_at,
    currentStep: formatUnknownValue(detail.current_step),
    graphRunIds,
    id: detail.id,
    inputJson: detail.input ?? detail.input_json ?? {},
    label: detail.title ?? detail.task_type ?? detail.id,
    moduleName: formatUnknownValue(module.name ?? module.code ?? detail.module_code),
    outputJson: output ?? {},
    outputSummary: formatUnknownValue(outputRecord?.summary ?? output),
    owner: detail.created_by ?? '-',
    pendingReviewId:
      typeof pendingReview?.id === 'string' && pendingReview.id ? pendingReview.id : undefined,
    product: formatUnknownValue(product.name ?? product.code ?? detail.product_id),
    productId: detail.product_id,
    productName: formatUnknownValue(product.name ?? product.code ?? detail.product_id),
    requirementId: detail.requirement_id,
    requirementTitle: formatUnknownValue(
      requirementSnapshot.title ?? requirementSnapshot.summary ?? detail.requirement_id,
    ),
    status: detail.status ?? '-',
    type: detail.task_type ?? '-',
    versionName: formatUnknownValue(version.name ?? version.code ?? detail.version_id),
  };
}

export async function startTaskCenterTask(taskId: string) {
  const token = requireAccessToken();
  return apiRequest<{ review_id: string; status: string }>(`/api/ai-tasks/${taskId}/start`, {
    method: 'POST',
    token,
  });
}

export async function batchCancelTaskCenterTasks(
  payload: TaskBatchCancelPayload,
): Promise<TaskBatchCancelResult> {
  const token = requireAccessToken();
  const result = await apiRequest<TaskBatchCancelResponse>('/api/ai-tasks/batch-cancel', {
    body: payload,
    method: 'POST',
    token,
  });
  return {
    batchId: result.batch_id,
    reason: result.reason,
    skipped: result.skipped,
    skippedCount: result.skipped_count,
    updated: result.updated,
    updatedCount: result.updated_count,
  };
}

export async function batchRetryTaskCenterTasks(
  payload: TaskBatchRetryPayload,
): Promise<TaskBatchRetryResult> {
  const token = requireAccessToken();
  const result = await apiRequest<TaskBatchRetryResponse>('/api/ai-tasks/batch-retry', {
    body: payload,
    method: 'POST',
    token,
  });
  return {
    batchId: result.batch_id,
    reason: result.reason,
    retried: result.retried,
    retriedCount: result.retried_count,
    skipped: result.skipped,
    skippedCount: result.skipped_count,
    updated: result.updated,
    updatedCount: result.updated_count,
  };
}

export async function fetchTaskCenterPendingReviews(): Promise<TaskCenterReviewRecord[]> {
  const token = requireAccessToken();
  const reviews = await apiRequest<ListResponse<PendingReviewListItem>>('/api/reviews/pending', {
    token,
  });

  return reviews.items.map((review) => ({
    aiTaskId: review.ai_task_id,
    contentSummary: formatUnknownValue(review.content?.summary),
    id: review.id,
    stage: review.stage ?? '-',
    status: review.status ?? '-',
    version: review.version,
  }));
}

export async function approveTaskCenterReview(reviewId: string, version: number) {
  const token = requireAccessToken();
  return apiRequest<{ review_status: string; task_status: string }>(
    `/api/reviews/${reviewId}/approve`,
    {
      body: { version },
      method: 'POST',
      token,
    },
  );
}

export async function editApproveTaskCenterReview(
  reviewId: string,
  version: number,
  editedContent: Record<string, unknown>,
) {
  const token = requireAccessToken();
  return apiRequest<{ review_status: string; task_status: string }>(
    `/api/reviews/${reviewId}/edit-approve`,
    {
      body: { edited_content: editedContent, version },
      method: 'POST',
      token,
    },
  );
}

export async function rejectTaskCenterReview(
  reviewId: string,
  version: number,
  decisionReason: string,
) {
  const token = requireAccessToken();
  return apiRequest<{ review_status: string; task_status: string }>(
    `/api/reviews/${reviewId}/reject`,
    {
      body: { decision_reason: decisionReason, version },
      method: 'POST',
      token,
    },
  );
}

export async function requestTaskCenterReviewMoreInfo(
  reviewId: string,
  version: number,
  questions: string[],
) {
  const token = requireAccessToken();
  return apiRequest<{ review_status: string; task_status: string }>(
    `/api/reviews/${reviewId}/request-more-info`,
    {
      body: { questions, version },
      method: 'POST',
      token,
    },
  );
}

export async function submitTaskCenterMoreInfo(taskId: string, answers: TaskMoreInfoAnswer[]) {
  const token = requireAccessToken();
  return apiRequest<{ id: string; status: string }>(`/api/ai-tasks/${taskId}/more-info`, {
    body: { answers },
    method: 'POST',
    token,
  });
}

function technicalSolutionTitleFromDesignTask(task: TaskCenterTaskRecord) {
  const title = task.label.replace(/^产品详细设计[:：]\s*/, '').trim();
  return `技术方案：${title || task.label}`;
}

function codeReviewTitleFromTechnicalSolutionTask(task: TaskCenterTaskRecord, mrIid: number) {
  const title = task.label.replace(/^技术方案[:：]\s*/, '').trim();
  return `Code Review：${title || task.label} MR !${mrIid}`;
}

function developmentPlanningTitleFromTechnicalSolutionTask(task: TaskCenterTaskRecord) {
  const title = task.label.replace(/^技术方案[:：]\s*/, '').trim();
  return `开发计划：${title || task.label}`;
}

function automatedTestingTitleFromTechnicalSolutionTask(task: TaskCenterTaskRecord) {
  const title = task.label.replace(/^技术方案[:：]\s*/, '').trim();
  return `自动化测试：${title || task.label}`;
}

function releaseReadinessTitleFromTechnicalSolutionTask(task: TaskCenterTaskRecord) {
  const title = task.label.replace(/^技术方案[:：]\s*/, '').trim();
  return `发布评估：${title || task.label}`;
}

function postReleaseAnalysisTitleFromReleaseReadinessTask(task: TaskCenterTaskRecord) {
  const title = task.label.replace(/^发布评估[:：]\s*/, '').trim();
  return `上线后分析：${title || task.label}`;
}

export async function createTechnicalSolutionTask(task: TaskCenterTaskRecord) {
  const token = requireAccessToken();
  if (!task.requirementId) {
    throw new ApiRequestError({
      code: 'VALIDATION_ERROR',
      message: '缺少需求编号，无法创建技术方案任务。',
      status: 400,
    });
  }
  return apiRequest<{ id: string; status: string }>('/api/ai-tasks', {
    body: {
      input: { product_detail_design_task_id: task.id },
      requirement_id: task.requirementId,
      task_type: 'technical_solution',
      title: technicalSolutionTitleFromDesignTask(task),
    },
    method: 'POST',
    token,
  });
}

export async function createDevelopmentPlanningTask(task: TaskCenterTaskRecord) {
  const token = requireAccessToken();
  if (!task.requirementId) {
    throw new ApiRequestError({
      code: 'VALIDATION_ERROR',
      message: '缺少需求编号，无法创建开发计划任务。',
      status: 400,
    });
  }
  return apiRequest<{ id: string; status: string }>('/api/ai-tasks', {
    body: {
      input: { technical_solution_task_id: task.id },
      requirement_id: task.requirementId,
      task_type: 'development_planning',
      title: developmentPlanningTitleFromTechnicalSolutionTask(task),
    },
    method: 'POST',
    token,
  });
}

export async function createAutomatedTestingTask(task: TaskCenterTaskRecord) {
  const token = requireAccessToken();
  if (!task.requirementId) {
    throw new ApiRequestError({
      code: 'VALIDATION_ERROR',
      message: '缺少需求编号，无法创建自动化测试任务。',
      status: 400,
    });
  }
  return apiRequest<{ id: string; status: string }>('/api/ai-tasks', {
    body: {
      input: { technical_solution_task_id: task.id },
      requirement_id: task.requirementId,
      task_type: 'automated_testing',
      title: automatedTestingTitleFromTechnicalSolutionTask(task),
    },
    method: 'POST',
    token,
  });
}

export async function createReleaseReadinessTask(task: TaskCenterTaskRecord) {
  const token = requireAccessToken();
  if (!task.requirementId) {
    throw new ApiRequestError({
      code: 'VALIDATION_ERROR',
      message: '缺少需求编号，无法创建发布评估任务。',
      status: 400,
    });
  }
  return apiRequest<{ id: string; status: string }>('/api/ai-tasks', {
    body: {
      input: { technical_solution_task_id: task.id },
      requirement_id: task.requirementId,
      task_type: 'release_readiness',
      title: releaseReadinessTitleFromTechnicalSolutionTask(task),
    },
    method: 'POST',
    token,
  });
}

export async function createPostReleaseAnalysisTask(task: TaskCenterTaskRecord) {
  const token = requireAccessToken();
  if (!task.requirementId) {
    throw new ApiRequestError({
      code: 'VALIDATION_ERROR',
      message: '缺少需求编号，无法创建上线后分析任务。',
      status: 400,
    });
  }
  return apiRequest<{ id: string; status: string }>('/api/ai-tasks', {
    body: {
      input: { release_readiness_task_id: task.id },
      requirement_id: task.requirementId,
      task_type: 'post_release_analysis',
      title: postReleaseAnalysisTitleFromReleaseReadinessTask(task),
    },
    method: 'POST',
    token,
  });
}

export async function fetchProductGitRepositories(
  productId: string,
): Promise<ProductGitRepositoryOption[]> {
  const token = requireAccessToken();
  const repositories = await apiRequest<ListResponse<ProductGitRepositoryListItem>>(
    `/api/products/${productId}/git-repositories?active_only=true`,
    { token },
  );

  return repositories.items.map((repository) => ({
    defaultBranch: repository.default_branch ?? 'main',
    id: repository.id,
    label: repository.project_path
      ? `${repository.name} (${repository.project_path})`
      : repository.name,
    name: repository.name,
    projectId: repository.project_id,
    projectPath: repository.project_path,
    provider: repository.git_provider ?? 'gitlab',
    status: repository.status ?? '-',
  }));
}

export async function previewGitLabMergeRequest(
  repositoryId: string,
  mrIid: number,
): Promise<GitLabMergeRequestPreview> {
  const token = requireAccessToken();
  const preview = await apiRequest<GitLabMergeRequestPreviewResponse>(
    `/api/devops/gitlab/merge-requests/${repositoryId}/${mrIid}/preview`,
    { token },
  );

  return {
    author: formatGitLabAuthor(preview.author),
    changedFileCount: preview.changed_file_count ?? 0,
    changedFilesSummary: preview.changed_files_summary ?? [],
    diffFileTree: normalizeDiffFileTree(preview.diff_file_tree),
    mrIid: preview.mr_iid,
    permissionDiagnostics: normalizePermissionDiagnostics(preview.permission_diagnostics),
    reviewChecklist: preview.review_checklist ?? [],
    repositoryId: preview.repository_id,
    riskSummary: normalizeRiskSummary(preview.risk_summary),
    sourceBranch: preview.source_branch,
    targetBranch: preview.target_branch,
    title: preview.title ?? `MR !${preview.mr_iid}`,
    webUrl: preview.web_url,
    writebackAllowed: preview.writeback_allowed ?? false,
  };
}

export async function previewCodeReviewPullRequest(
  repository: ProductGitRepositoryOption,
  mrIid: number,
): Promise<GitLabMergeRequestPreview> {
  if (repository.provider !== 'github') {
    return previewGitLabMergeRequest(repository.id, mrIid);
  }
  const token = requireAccessToken();
  const preview = await apiRequest<GitLabMergeRequestPreviewResponse>(
    `/api/devops/github/pull-requests/${repository.id}/${mrIid}/preview`,
    { token },
  );

  return {
    author: formatGitLabAuthor(preview.author),
    changedFileCount: preview.changed_file_count ?? 0,
    changedFilesSummary: preview.changed_files_summary ?? [],
    diffFileTree: normalizeDiffFileTree(preview.diff_file_tree),
    mrIid: preview.mr_iid,
    permissionDiagnostics: normalizePermissionDiagnostics(preview.permission_diagnostics),
    reviewChecklist: preview.review_checklist ?? [],
    repositoryId: preview.repository_id,
    riskSummary: normalizeRiskSummary(preview.risk_summary),
    sourceBranch: preview.source_branch,
    targetBranch: preview.target_branch,
    title: preview.title ?? `PR #${preview.mr_iid}`,
    webUrl: preview.web_url,
    writebackAllowed: preview.writeback_allowed ?? false,
  };
}

export async function snapshotGitLabMergeRequest({
  mrIid,
  repositoryId,
  requirementId,
  technicalSolutionTaskId,
}: {
  mrIid: number;
  repositoryId: string;
  requirementId: string;
  technicalSolutionTaskId: string;
}): Promise<GitLabMergeRequestSnapshot> {
  const token = requireAccessToken();
  const snapshot = await apiRequest<GitLabMergeRequestSnapshotResponse>(
    `/api/devops/gitlab/merge-requests/${repositoryId}/${mrIid}/snapshot`,
    {
      body: {
        requirement_id: requirementId,
        technical_solution_task_id: technicalSolutionTaskId,
      },
      method: 'POST',
      token,
    },
  );

  return {
    changedFilesSummary: snapshot.changed_files_summary ?? [],
    createdAt: formatListDate(snapshot.created_at),
    diffChangeSummary: normalizeDiffChangeSummary(snapshot.diff_change_summary),
    diffLimitBytes: snapshot.diff_limit_bytes,
    diffFileTree: normalizeDiffFileTree(snapshot.diff_file_tree),
    diffSizeBytes: snapshot.diff_size_bytes,
    id: snapshot.id,
    mrIid: snapshot.mr_iid,
    previousSnapshot: normalizePreviousSnapshot(snapshot.previous_snapshot),
    reviewChecklist: snapshot.review_checklist ?? [],
    repositoryId: snapshot.repository_id,
    riskSummary: normalizeRiskSummary(snapshot.risk_summary),
    snapshotReused: snapshot.snapshot_reused,
  };
}

export async function snapshotCodeReviewPullRequest({
  mrIid,
  repository,
  requirementId,
  technicalSolutionTaskId,
}: {
  mrIid: number;
  repository: ProductGitRepositoryOption;
  requirementId: string;
  technicalSolutionTaskId: string;
}): Promise<GitLabMergeRequestSnapshot> {
  if (repository.provider !== 'github') {
    return snapshotGitLabMergeRequest({
      mrIid,
      repositoryId: repository.id,
      requirementId,
      technicalSolutionTaskId,
    });
  }
  const token = requireAccessToken();
  const snapshot = await apiRequest<GitLabMergeRequestSnapshotResponse>(
    `/api/devops/github/pull-requests/${repository.id}/${mrIid}/snapshot`,
    {
      body: {
        requirement_id: requirementId,
        technical_solution_task_id: technicalSolutionTaskId,
      },
      method: 'POST',
      token,
    },
  );

  return {
    changedFilesSummary: snapshot.changed_files_summary ?? [],
    createdAt: formatListDate(snapshot.created_at),
    diffChangeSummary: normalizeDiffChangeSummary(snapshot.diff_change_summary),
    diffLimitBytes: snapshot.diff_limit_bytes,
    diffFileTree: normalizeDiffFileTree(snapshot.diff_file_tree),
    diffSizeBytes: snapshot.diff_size_bytes,
    id: snapshot.id,
    mrIid: snapshot.mr_iid,
    previousSnapshot: normalizePreviousSnapshot(snapshot.previous_snapshot),
    reviewChecklist: snapshot.review_checklist ?? [],
    repositoryId: snapshot.repository_id,
    riskSummary: normalizeRiskSummary(snapshot.risk_summary),
    snapshotReused: snapshot.snapshot_reused,
  };
}

export async function createCodeReviewTask(
  task: TaskCenterTaskRecord,
  gitlabMrSnapshotId: string,
  mrIid: number,
) {
  const token = requireAccessToken();
  if (!task.requirementId) {
    throw new ApiRequestError({
      code: 'VALIDATION_ERROR',
      message: '缺少需求编号，无法创建 Code Review 任务。',
      status: 400,
    });
  }
  return apiRequest<{ id: string; status: string }>('/api/ai-tasks', {
    body: {
      input: { gitlab_mr_snapshot_id: gitlabMrSnapshotId },
      requirement_id: task.requirementId,
      task_type: 'code_review',
      title: codeReviewTitleFromTechnicalSolutionTask(task, mrIid),
    },
    method: 'POST',
    token,
  });
}

export async function fetchCodeReviewReport(taskId: string): Promise<CodeReviewReportRecord> {
  const token = requireAccessToken();
  const report = await apiRequest<CodeReviewReportResponse>(
    `/api/ai-tasks/${taskId}/code-review-report`,
    { token },
  );

  return {
    executor: report.executor,
    findings: report.findings ?? [],
    gitlabWritebackPerformed: report.gitlab_writeback_performed ?? false,
    id: report.id,
    riskLevel: report.risk_level ?? '-',
    status: report.status ?? '-',
    summary: report.summary ?? '-',
    writebackTemplate: report.writeback_template
      ? {
          body: report.writeback_template.body ?? '',
          format: report.writeback_template.format ?? 'markdown',
          title: report.writeback_template.title ?? 'AI Brain Code Review',
          writebackAllowed: report.writeback_template.writeback_allowed ?? false,
          writebackReason: report.writeback_template.writeback_reason ?? '-',
        }
      : undefined,
  };
}

function mapTaskWritebackResult(
  response: TaskWritebackResultResponse,
  fallbackTaskId: string,
): TaskWritebackResultRecord {
  return {
    idempotencyKey: response.idempotency_key ?? `mock_issue:${fallbackTaskId}`,
    issues: (response.issues ?? []).map((issue) => ({
      id: issue.id,
      sourceTaskId: issue.source_task_id,
      status: issue.status ?? '-',
      title: issue.title ?? issue.id,
    })),
    status: response.status ?? '-',
    taskId: response.task_id ?? fallbackTaskId,
  };
}

export async function fetchTaskWritebackResult(
  taskId: string,
): Promise<TaskWritebackResultRecord> {
  const token = requireAccessToken();
  const result = await apiRequest<TaskWritebackResultResponse>(
    `/api/writeback/results/${taskId}`,
    { token },
  );
  return mapTaskWritebackResult(result, taskId);
}

export async function createTaskWritebackResult(
  taskId: string,
): Promise<TaskWritebackResultRecord> {
  const token = requireAccessToken();
  const result = await apiRequest<TaskWritebackResultResponse>(
    `/api/writeback/results/${taskId}`,
    {
      method: 'POST',
      token,
    },
  );
  return mapTaskWritebackResult(result, taskId);
}

function mapKnowledgeDeposit(deposit: KnowledgeDepositListItem): KnowledgeDepositRecord {
  return {
    aiTaskId: deposit.ai_task_id,
    content: deposit.content ?? '-',
    id: deposit.id,
    knowledgeDocumentId: deposit.knowledge_document_id,
    rejectionReason: deposit.rejection_reason,
    status: deposit.status ?? '-',
    title: deposit.title ?? deposit.id,
  };
}

export async function fetchKnowledgeDeposits(
  status = 'pending',
): Promise<KnowledgeDepositRecord[]> {
  const token = requireAccessToken();
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  const deposits = await apiRequest<ListResponse<KnowledgeDepositListItem>>(
    `/api/knowledge/deposits${query}`,
    { token },
  );
  return deposits.items.map(mapKnowledgeDeposit);
}

function mapKnowledgeSearchResult(item: KnowledgeSearchResultItem, index: number): KnowledgeSearchResultRecord {
  const sourceParts = [
    item.source?.doc_type,
    item.source?.title,
    item.chunk_index ? `chunk ${item.chunk_index}` : undefined,
  ].filter(Boolean);
  return {
    chunkId: item.chunk_id ?? item.source?.chunk_id,
    chunkIndex: item.chunk_index,
    content: item.content ?? '-',
    documentId: item.document_id,
    id: item.chunk_id ?? `${item.document_id}:${index}`,
    parentChunkId: item.source?.parent_chunk_id,
    parentContent: item.source?.parent_content,
    retrievalMode: item.retrieval_mode === 'vector' ? 'vector' : 'keyword',
    sourceLabel: sourceParts.length ? sourceParts.join(' · ') : '-',
    title: item.title ?? item.document_id,
  };
}

export async function fetchKnowledgeSearchResults(
  query: string,
  topK = 5,
  knowledgeSpaceId?: string,
): Promise<KnowledgeSearchResultRecord[]> {
  const token = requireAccessToken();
  const results = await apiRequest<ListResponse<KnowledgeSearchResultItem>>(
    '/api/knowledge/search',
    {
      body: {
        knowledge_space_id: knowledgeSpaceId,
        query,
        top_k: topK,
      },
      method: 'POST',
      token,
    },
  );
  return results.items.map(mapKnowledgeSearchResult);
}

export async function approveKnowledgeDeposit(
  depositId: string,
  payload: KnowledgeDepositApprovePayload = {},
): Promise<KnowledgeDepositRecord> {
  const token = requireAccessToken();
  const deposit = await apiRequest<KnowledgeDepositListItem>(
    `/api/knowledge/deposits/${depositId}/approve`,
    {
      body: {
        permission_roles: payload.permissionRoles ?? ['admin'],
        title: payload.title,
      },
      method: 'POST',
      token,
    },
  );
  return mapKnowledgeDeposit(deposit);
}

export async function rejectKnowledgeDeposit(
  depositId: string,
  reason: string,
): Promise<KnowledgeDepositRecord> {
  const token = requireAccessToken();
  const deposit = await apiRequest<KnowledgeDepositListItem>(
    `/api/knowledge/deposits/${depositId}/reject`,
    {
      body: { reason },
      method: 'POST',
      token,
    },
  );
  return mapKnowledgeDeposit(deposit);
}

export async function fetchTaskMarkdown(taskId: string): Promise<string> {
  const token = requireAccessToken();
  const response = await fetch(`${API_BASE_URL}/api/export/tasks/${taskId}/markdown`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    method: 'GET',
  });
  if (!response.ok) {
    let payload: ApiErrorPayload | undefined;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = undefined;
    }
    const requestError = new ApiRequestError({
      code: payload?.detail?.code,
      message: payload?.detail?.message ?? `API request failed: ${response.status}`,
      status: response.status,
      traceId: payload?.detail?.trace_id,
    });
    if (response.status === 401) {
      handleUnauthorizedApiResponse();
    }
    throw requestError;
  }
  return response.text();
}

function mapOperationalMetrics(
  category: string,
  items: FlexibleListItem[],
): OperationalMetricRecord[] {
  return items.map((item, index) => ({
    category,
    id: formatUnknownValue(item.id ?? `${category}-${index}`),
    name: formatUnknownValue(
      firstKnownValue(item, [
        'name',
        'metric_name',
        'repository_name',
        'release_name',
        'title',
        'job_name',
        'build_id',
        'metric_date',
        'environment',
        'window_start',
      ]),
    ),
    status: formatUnknownValue(item.status),
    updatedAt: formatListDate(
      formatUnknownValue(firstKnownValue(item, ['updated_at', 'created_at', 'observed_at', 'date'])),
    ),
    value: formatUnknownValue(
      firstKnownValue(item, [
        'value',
        'count',
        'score',
        'summary',
        'commit_count',
        'build_id',
        'duration_seconds',
        'error_rate',
        'request_count',
        'p95_latency_ms',
      ]),
    ),
  }));
}

function mapOperationalMetricRecord(item: FlexibleListItem, index: number): OperationalMetricRecord {
  return {
    category: formatUnknownValue(item.category),
    id: formatUnknownValue(item.id ?? `operational-metric-${index}`),
    name: formatUnknownValue(
      firstKnownValue(item, [
        'name',
        'metric_name',
        'repository_name',
        'release_name',
        'title',
        'job_name',
        'build_id',
        'metric_date',
        'environment',
        'window_start',
      ]),
    ),
    status: formatUnknownValue(item.status),
    updatedAt: formatListDate(
      formatUnknownValue(firstKnownValue(item, ['updated_at', 'created_at', 'observed_at', 'date'])),
    ),
    value: formatUnknownValue(
      firstKnownValue(item, [
        'value',
        'count',
        'score',
        'summary',
        'commit_count',
        'quality_score',
        'build_id',
        'duration_seconds',
        'error_rate',
        'request_count',
        'p95_latency_ms',
      ]),
    ),
  };
}

export async function fetchDevopsMetrics(): Promise<OperationalMetricRecord[]> {
  const token = requireAccessToken();
  const [gitlabMetrics, jenkinsReleases, onlineLogs] = await Promise.all([
    apiRequest<ListResponse<FlexibleListItem>>('/api/devops/gitlab/daily-code-metrics', { token }),
    apiRequest<ListResponse<FlexibleListItem>>('/api/devops/jenkins/releases', { token }),
    apiRequest<ListResponse<FlexibleListItem>>('/api/ops/online-log-metrics', { token }),
  ]);

  return [
    ...mapOperationalMetrics('GitLab 指标', gitlabMetrics.items),
    ...mapOperationalMetrics('Jenkins 发布', jenkinsReleases.items),
    ...mapOperationalMetrics('线上日志', onlineLogs.items),
  ];
}

export async function fetchDevopsMetricList(
  query: OperationalMetricListQuery = {},
): Promise<RemoteListResult<OperationalMetricRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'category', query.category);
  appendQueryParam(params, 'name', query.name);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const path = queryString
    ? `/api/devops/operational-metrics?${queryString}`
    : '/api/devops/operational-metrics';
  const metrics = await apiRequest<ListResponse<FlexibleListItem>>(path, { token });

  return {
    page: metrics.page ?? query.page ?? 1,
    pageSize: metrics.page_size ?? query.pageSize ?? 10,
    rows: metrics.items.map(mapOperationalMetricRecord),
    total: metrics.total,
  };
}

export async function createGitLabDailyCodeMetric(
  payload: GitLabDailyCodeMetricCreatePayload,
): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>('/api/devops/gitlab/daily-code-metrics', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function createJenkinsRelease(
  payload: JenkinsReleaseCreatePayload,
): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>('/api/devops/jenkins/releases', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function createOnlineLogMetric(
  payload: OnlineLogMetricCreatePayload,
): Promise<FlexibleListItem> {
  const token = requireAccessToken();
  return apiRequest<FlexibleListItem>('/api/ops/online-log-metrics', {
    body: payload,
    method: 'POST',
    token,
  });
}

function mapCollectorRun(item: FlexibleListItem): CollectorRunRecord {
  const payloadSummary = normalizeObjectRecord(item.payload_summary) ?? {};
  return {
    collectorType: formatUnknownValue(item.collector_type),
    createdBy: formatUnknownValue(item.created_by),
    errorMessage: formatUnknownValue(item.error_message),
    finishedAt: formatListDate(formatUnknownValue(item.finished_at)),
    id: formatUnknownValue(item.id),
    payloadSummary,
    productId: formatUnknownValue(item.product_id),
    recordsImported: Number(item.records_imported ?? 0),
    sourceSystem: formatUnknownValue(item.source_system),
    startedAt: formatListDate(formatUnknownValue(item.started_at)),
    status: formatUnknownValue(item.status),
    updatedAt: formatListDate(formatUnknownValue(item.updated_at ?? item.created_at)),
  };
}

export async function fetchCollectorRuns(): Promise<CollectorRunRecord[]> {
  const token = requireAccessToken();
  const runs = await apiRequest<ListResponse<FlexibleListItem>>('/api/collectors/runs', { token });
  return runs.items.map(mapCollectorRun);
}

export async function createCollectorRun(
  payload: CollectorRunCreatePayload,
): Promise<CollectorRunRecord> {
  const token = requireAccessToken();
  const run = await apiRequest<FlexibleListItem>('/api/collectors/runs', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapCollectorRun(run);
}

export async function updateCollectorRun(
  runId: string,
  payload: CollectorRunPatchPayload,
): Promise<CollectorRunRecord> {
  const token = requireAccessToken();
  const run = await apiRequest<FlexibleListItem>(`/api/collectors/runs/${runId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
  return mapCollectorRun(run);
}

function emptyToUndefined(value: string) {
  return value === '-' ? undefined : value;
}

function mapPendingAttributionItem(item: FlexibleListItem): PendingAttributionItem {
  const rawConfidence = item.confidence;
  const confidence =
    typeof rawConfidence === 'number'
      ? rawConfidence
      : rawConfidence === null || rawConfidence === undefined || rawConfidence === ''
        ? undefined
        : Number.isFinite(Number(rawConfidence))
          ? Number(rawConfidence)
        : undefined;
  return {
    collectorRunId: emptyToUndefined(formatUnknownValue(item.collector_run_id)),
    confidence,
    createdAt: formatListDate(formatUnknownValue(item.created_at)),
    createdBy: emptyToUndefined(formatUnknownValue(item.created_by)),
    id: formatUnknownValue(item.id),
    rawPayload: normalizeObjectRecord(item.raw_payload) ?? {},
    rawSubjectId: emptyToUndefined(formatUnknownValue(item.raw_subject_id)),
    resolutionAction: emptyToUndefined(formatUnknownValue(item.resolution_action)),
    resolutionNote: emptyToUndefined(formatUnknownValue(item.resolution_note)),
    resolvedAt: emptyToUndefined(formatListDate(formatUnknownValue(item.resolved_at))),
    resolvedBy: emptyToUndefined(formatUnknownValue(item.resolved_by)),
    resolvedModuleCode: emptyToUndefined(formatUnknownValue(item.resolved_module_code)),
    resolvedProductId: emptyToUndefined(formatUnknownValue(item.resolved_product_id)),
    resolvedRequirementId: emptyToUndefined(formatUnknownValue(item.resolved_requirement_id)),
    resolvedSubjectId: emptyToUndefined(formatUnknownValue(item.resolved_subject_id)),
    resolvedSubjectType: emptyToUndefined(formatUnknownValue(item.resolved_subject_type)),
    sourceSystem: formatUnknownValue(item.source_system),
    sourceType: formatUnknownValue(item.source_type),
    status: formatUnknownValue(item.status),
    suggestedModuleCode: emptyToUndefined(formatUnknownValue(item.suggested_module_code)),
    suggestedProductId: emptyToUndefined(formatUnknownValue(item.suggested_product_id)),
    summary: formatUnknownValue(item.summary),
    updatedAt: formatListDate(formatUnknownValue(item.updated_at ?? item.created_at)),
  };
}

function pendingAttributionQuery(filters: PendingAttributionFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  const query = params.toString();
  return query ? `/api/attribution/pending-items?${query}` : '/api/attribution/pending-items';
}

export async function fetchPendingAttributionItems(
  filters: PendingAttributionFilters = {},
): Promise<PendingAttributionItem[]> {
  const token = requireAccessToken();
  const items = await apiRequest<ListResponse<FlexibleListItem>>(
    pendingAttributionQuery(filters),
    { token },
  );
  return items.items.map(mapPendingAttributionItem);
}

export async function createPendingAttributionItem(
  payload: PendingAttributionCreatePayload,
): Promise<PendingAttributionItem> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>('/api/attribution/pending-items', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapPendingAttributionItem(item);
}

export async function resolvePendingAttributionItem(
  itemId: string,
  payload: PendingAttributionResolvePayload,
): Promise<PendingAttributionItem> {
  const token = requireAccessToken();
  const item = await apiRequest<FlexibleListItem>(
    `/api/attribution/pending-items/${itemId}/resolve`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return mapPendingAttributionItem(item);
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
