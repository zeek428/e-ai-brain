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
  roles: string[];
  username: string;
};

export type AssistantChatResponse = {
  content: string;
  conversationId: string;
  latencyMs: number;
  messageId: string;
  model: string;
  suggestions: string[];
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
  suggestions: string[];
};

type AssistantChatApiResponse = {
  conversation_id: string;
  latency_ms?: number;
  message: {
    content?: string;
    id?: string;
    role?: string;
  };
  model?: string;
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

export type TaskCenterTaskRecord = {
  createdAt: string;
  createdAtValue?: string;
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
  status?: string;
  taskType?: string;
};

export type TaskCenterTaskListResult = {
  page: number;
  pageSize: number;
  rows: TaskCenterTaskRecord[];
  total: number;
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
  mrIid: number;
  repositoryId: string;
  sourceBranch?: string;
  targetBranch?: string;
  title: string;
  webUrl?: string;
  writebackAllowed: boolean;
};

export type GitLabMergeRequestSnapshot = {
  diffLimitBytes?: number;
  diffSizeBytes?: number;
  id: string;
  mrIid: number;
  repositoryId: string;
};

export type CodeReviewReportRecord = {
  executor?: unknown;
  findings: unknown[];
  gitlabWritebackPerformed: boolean;
  id: string;
  riskLevel: string;
  status: string;
  summary: string;
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
  retrievalMode?: 'keyword' | 'vector';
  sourceLabel: string;
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
  title?: string;
  version_id?: string | null;
};

export type RequirementBatchSchedulePayload = {
  product_id: string;
  reason?: string;
  requirement_ids: string[];
  version_id: string;
};

type RequirementBatchScheduleSkippedItem = {
  code: string;
  id: string;
  message: string;
};

type RequirementBatchScheduleResponse = {
  batch_id: string;
  product_id: string;
  reason?: string | null;
  skipped: RequirementBatchScheduleSkippedItem[];
  skipped_count: number;
  updated: RequirementListItem[];
  updated_count: number;
  version_id: string;
};

export type RequirementBatchScheduleResult = {
  batchId: string;
  productId: string;
  reason?: string | null;
  skipped: RequirementBatchScheduleSkippedItem[];
  skippedCount: number;
  updated: RequirementRecord[];
  updatedCount: number;
  versionId: string;
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
  index_error?: string | null;
  index_status?: string;
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
  content?: string;
  created_at?: string;
  created_by?: string;
  id: string;
  module_code?: string | null;
  priority?: string;
  product_code?: string;
  product_id: string;
  product_name?: string;
  status?: string;
  title: string;
  updated_at?: string;
  version_code?: string | null;
  version_id?: string;
  version_name?: string | null;
};

type KnowledgeDocumentListItem = {
  content?: string;
  created_at?: string;
  doc_type?: string;
  id: string;
  index_error?: string | null;
  index_status?: string;
  permission_roles?: string[];
  tags?: string[];
  title: string;
  updated_at?: string;
  vector_index_error?: string | null;
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
  mr_iid: number;
  repository_id: string;
  source_branch?: string;
  target_branch?: string;
  title?: string;
  web_url?: string;
  writeback_allowed?: boolean;
};

type GitLabMergeRequestSnapshotResponse = {
  diff_limit_bytes?: number;
  diff_size_bytes?: number;
  id: string;
  mr_iid: number;
  repository_id: string;
};

type CodeReviewReportResponse = {
  executor?: unknown;
  findings?: unknown[];
  gitlab_writeback_performed?: boolean;
  id: string;
  risk_level?: string;
  status?: string;
  summary?: string;
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
    chunk_id?: string;
    doc_type?: string;
    title?: string;
  };
  title?: string;
};

type PendingReviewListItem = {
  ai_task_id: string;
  content?: Record<string, unknown>;
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
  limitations?: string[];
  menu_scope?: string[];
  name: string;
  permissions?: string[];
  responsibilities?: string[];
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
  params: { productId?: string; timeRange?: string } = {},
): Promise<ItTeamDashboard> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  if (params.productId) {
    query.set('product_id', params.productId);
  }
  if (params.timeRange) {
    query.set('time_range', params.timeRange);
  }
  const path = query.toString()
    ? `/api/dashboard/it-team?${query.toString()}`
    : '/api/dashboard/it-team';
  const dashboard = await apiRequest<DashboardResponse>(path, { token });
  const summary = dashboard.summary ?? {};
  const gitlabDailySummary = dashboard.gitlab_daily_summary ?? {};
  const onlineLogSummary = dashboard.online_log_summary ?? {};
  const usageMetricSummary = dashboard.usage_metric_summary ?? {};
  return {
    bugStatusCounts: mapDashboardStatusCounts(dashboard.bug_status_counts),
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

  return products.items.map((product) => ({
    code: product.code ?? product.id,
    id: product.id,
    moduleCount: product.module_count ?? 0,
    name: product.name,
    ownerTeam: product.owner_team ?? '-',
    status: normalizeProductStatus(product.status),
    version:
      product.current_version_name ??
      versionsByProductId.get(product.id)?.find((version) => version.status === 'active')?.name ??
      versionsByProductId.get(product.id)?.[0]?.name ??
      '未配置',
  }));
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
    apiRequest<ListResponse<ProductListItem>>('/api/products?active_only=true', { token }),
    apiRequest<ListResponse<ProductVersionListItem>>('/api/product-versions?active_only=true', {
      token,
    }),
  ]);
  return mapProductContexts(products.items, versions.items);
}

export async function fetchBugProductContextOptions(): Promise<ProductContextOption[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    apiRequest<ListResponse<ProductListItem>>('/api/products?active_only=true', { token }),
    apiRequest<ListResponse<ProductVersionListItem>>('/api/product-versions', { token }),
  ]);
  return mapProductContexts(products.items, versions.items.filter(isBugAssignableVersion));
}

export async function fetchRequirementProductContextOptions(): Promise<ProductContextOption[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    apiRequest<ListResponse<ProductListItem>>('/api/products?active_only=true', { token }),
    apiRequest<ListResponse<ProductVersionListItem>>('/api/product-versions', { token }),
  ]);
  return mapProductContexts(
    products.items,
    versions.items.filter(isRequirementSchedulableVersion),
  );
}

export async function fetchActiveProductOptions(): Promise<ProductFilterOption[]> {
  const token = requireAccessToken();
  const products = await apiRequest<ListResponse<ProductListItem>>('/api/products?active_only=true', {
    token,
  });
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
    menu_scope: role.menu_scope ?? [],
    name: role.name,
    permissions: role.permissions ?? [],
    responsibilities: role.responsibilities ?? [],
    sort_order: role.sort_order ?? 0,
    status: role.status ?? 'active',
  };
}

export async function fetchRoleDefinitions(): Promise<UserRoleDefinition[]> {
  const token = requireAccessToken();
  const roles = await apiRequest<ListResponse<RoleDefinitionListItem>>('/api/auth/roles', { token });
  return roles.items.map(mapRoleDefinition);
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

function mapRequirementRecord(requirement: RequirementListItem): RequirementRecord {
  return {
    content: requirement.content,
    id: requirement.id,
    moduleCode: requirement.module_code ?? undefined,
    owner: requirement.created_by ?? '-',
    priority: normalizePriority(requirement.priority),
    product: requirement.product_code ?? requirement.product_name ?? requirement.product_id,
    productId: requirement.product_id,
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

export async function fetchManagementRequirements(): Promise<RequirementRecord[]> {
  const token = requireAccessToken();
  const requirements = await apiRequest<ListResponse<RequirementListItem>>('/api/requirements', {
    token,
  });

  return requirements.items.map(mapRequirementRecord);
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

  return documents.items.map((document) => ({
    content: document.content,
    documentType: document.doc_type ?? '-',
    id: document.id,
    indexError: document.index_error,
    ownerRole: document.permission_roles?.join(', ') || '-',
    permissionRoles: document.permission_roles,
    status: normalizeKnowledgeStatus(document.index_status),
    tags: document.tags,
    title: document.title,
    updatedAt: formatListDate(document.updated_at ?? document.created_at),
    vectorIndexError: document.vector_index_error,
  }));
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

  return events.items.map((event) => ({
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
  }));
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
  if ((query.page ?? 1) !== 1) {
    appendQueryParam(params, 'page', query.page);
  }
  if ((query.pageSize ?? 10) !== 10) {
    appendQueryParam(params, 'page_size', query.pageSize);
  }
  const taskQueryString = params.toString();
  const taskPath = taskQueryString ? `/api/ai-tasks?${taskQueryString}` : '/api/ai-tasks';
  const tasks = await apiRequest<ListResponse<TaskListItem>>(taskPath, { token });

  return {
    page: tasks.page ?? query.page ?? 1,
    pageSize: tasks.page_size ?? query.pageSize ?? 10,
    rows: tasks.items.map((task) => ({
      createdAt: formatListDate(task.created_at ?? task.updated_at),
      createdAtValue: task.created_at ?? task.updated_at,
      id: task.id,
      label: task.title ?? task.task_type ?? task.id,
      owner: task.created_by ?? '-',
      product: task.product_name ?? task.product_id ?? '-',
      productId: task.product_id,
      requirementId: task.requirement_id,
      status: task.status ?? '-',
      type: task.task_type ?? '-',
    })),
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
    mrIid: preview.mr_iid,
    repositoryId: preview.repository_id,
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
    mrIid: preview.mr_iid,
    repositoryId: preview.repository_id,
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
    diffLimitBytes: snapshot.diff_limit_bytes,
    diffSizeBytes: snapshot.diff_size_bytes,
    id: snapshot.id,
    mrIid: snapshot.mr_iid,
    repositoryId: snapshot.repository_id,
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
    diffLimitBytes: snapshot.diff_limit_bytes,
    diffSizeBytes: snapshot.diff_size_bytes,
    id: snapshot.id,
    mrIid: snapshot.mr_iid,
    repositoryId: snapshot.repository_id,
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
    retrievalMode: item.retrieval_mode === 'vector' ? 'vector' : 'keyword',
    sourceLabel: sourceParts.length ? sourceParts.join(' · ') : '-',
    title: item.title ?? item.document_id,
  };
}

export async function fetchKnowledgeSearchResults(
  query: string,
  topK = 5,
): Promise<KnowledgeSearchResultRecord[]> {
  const token = requireAccessToken();
  const results = await apiRequest<ListResponse<KnowledgeSearchResultItem>>(
    '/api/knowledge/search',
    {
      body: {
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
      convertedRequirementId: formatUnknownValue(item.converted_requirement_id),
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
