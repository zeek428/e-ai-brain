import type {
  AuditRecord,
  ProductGitRepositoryRecord,
  ProductModuleRecord,
  ProductRecord,
  ProductRelatedSystemRecord,
  ProductVersionBranchConfigRecord,
  ProductVersionRecord,
  UserRecord,
} from '../data/management';
import { formatUserRoles, type UserRoleDefinition } from '../data/roles';
import { formatDisplayDateTime } from '../utils/dateTime';
import {
  API_BASE_URL,
  ApiRequestError,
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
} from './apiClient';
import type {
  ApiEnvelope,
  ApiErrorPayload,
  ListResponse,
  RemoteListPerformance,
  RemoteListQueryEcho,
} from './apiClient';
import {
  requireAccessToken,
} from './authClient';
import type { ScopeGrant } from './authClient';
import type { AssistantActionDraftPreview } from './assistantDraftClient';
import type { RequirementListItem } from './requirementClient';
import {
  type TaskCenterTaskRecord,
} from './taskCenterClient';

export { ApiRequestError, apiRequest };
export type { RemoteListPerformance, RemoteListQueryEcho };
export {
  AUTH_STATE_EVENT,
  clearAccessToken,
  fetchCurrentUser,
  getAccessToken,
  getStoredCurrentUser,
  login,
  logout,
  saveAccessToken,
  saveCurrentUser,
} from './authClient';
export type {
  CurrentUserResponse,
  LoginResponse,
  MenuTreeNode,
  ScopeGrant,
} from './authClient';
export {
  ASSISTANT_DRAFT_RESOLUTION_STORAGE_KEY,
  ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
  ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
  ASSISTANT_RECENT_REFERENCES_STORAGE_KEY,
  ASSISTANT_ROUTE_PROMPT_STORAGE_KEY,
  ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
  assistantScopedStorageKey,
  cancelAssistantActionDraft,
  confirmAssistantActionDraft,
  consumeAssistantRoutePrompt,
  fetchAssistantActionDraftWorkbench,
  getAssistantActionDraft,
  markAssistantActionDraftModified,
  markAssistantActionDraftViewed,
  readAssistantDraftResolutions,
  rememberAssistantDraftResolution,
  rememberAssistantRoutePrompt,
  resolveAssistantDraftResourceId,
  retryAssistantActionDraft,
  updateAssistantActionDraft,
} from './assistantDraftClient';
export type {
  AssistantActionDraftConfirmResponse,
  AssistantActionDraftGovernance,
  AssistantActionDraftPreview,
  AssistantActionDraftPreviewDiff,
  AssistantActionDraftPreviewIssue,
  AssistantActionDraftRecord,
  AssistantActionDraftWorkbenchItem,
  AssistantActionDraftWorkbenchQuery,
  AssistantActionDraftWorkbenchResult,
  AssistantActionDraftWorkbenchSummary,
  AssistantActionRunRecord,
  AssistantDraftResolutionMap,
  AssistantDraftResolutionRecord,
  AssistantDraftResourceType,
  AssistantPluginActionDraft,
  AssistantPluginConnectionDraft,
  AssistantRepairAction,
  AssistantRoutePromptRecord,
  AssistantScheduledJobDraft,
} from './assistantDraftClient';
export {
  exportAssistantMetrics,
  fetchAssistantMetricDetails,
  fetchAssistantMetrics,
} from './assistantMetricsClient';
export type {
  AssistantDraftActionDailyTrend,
  AssistantDraftActionMetric,
  AssistantFunnelStage,
  AssistantMetricDetailItem,
  AssistantMetricDetails,
  AssistantMetrics,
  AssistantMetricsDailyTrend,
  AssistantMetricsExport,
  AssistantMetricsFilters,
  AssistantMetricsProductDimension,
  AssistantMetricsQueryParams,
  AssistantMetricsRoleDimension,
  AssistantMetricsSummary,
  AssistantRunAttributionMetric,
} from './assistantMetricsClient';
export {
  createModelGatewayConfig,
  deleteModelGatewayConfig,
  fetchModelGatewayConfigList,
  fetchModelGatewayConfigs,
  fetchModelGatewayLogs,
  testModelGatewayConfig,
  updateModelGatewayConfig,
} from './modelGatewayClient';
export type {
  ModelGatewayConfigListQuery,
  ModelGatewayConfigMutationPayload,
  ModelGatewayConfigTestResult,
  ModelGatewayLogQuery,
  ModelGatewayLogRecord,
} from './modelGatewayClient';
export {
  createAssistantActionReferenceConfig,
  deleteAssistantActionReferenceConfig,
  fetchAssistantActionReferenceConfigList,
  fetchAssistantActionReferenceConfigs,
  fetchAssistantRoleQuickTaskConfigList,
  fetchAssistantRoleQuickTaskConfigs,
  fetchAssistantRoleQuickTasks,
  patchAssistantActionReferenceConfig,
  setAssistantActionReferenceConfigStatus,
  setAssistantRoleQuickTaskConfigStatus,
  updateAssistantActionReferenceConfigRollout,
  updateAssistantRoleQuickTaskConfigRollout,
} from './assistantConfigClient';
export type {
  AssistantActionReferenceConfig,
  AssistantActionReferenceConfigListQuery,
  AssistantRoleQuickTask,
  AssistantRoleQuickTaskConfig,
  AssistantRoleQuickTaskConfigListQuery,
  AssistantRoleQuickTaskGroup,
} from './assistantConfigClient';
export {
  batchUpdateManagementBugs,
  createManagementBug,
  deleteManagementBug,
  fetchManagementBugList,
  fetchManagementBugs,
  updateManagementBug,
} from './bugClient';
export type {
  BugBatchUpdatePayload,
  BugBatchUpdateResult,
  BugListQuery,
  BugMutationPayload,
} from './bugClient';
export {
  approveManagementRequirement,
  batchAdvanceRequirementStatus,
  batchAssignRequirementOwner,
  batchGenerateRequirementTasks,
  batchScheduleRequirements,
  createManagementRequirement,
  deleteManagementRequirement,
  fetchManagementRequirementList,
  fetchManagementRequirements,
  generateRequirementTask,
  rejectManagementRequirement,
  updateManagementRequirement,
} from './requirementClient';
export type {
  RequirementBatchAdvanceStatusPayload,
  RequirementBatchAdvanceStatusResult,
  RequirementBatchAssignOwnerPayload,
  RequirementBatchAssignOwnerResult,
  RequirementBatchGeneratedTaskItem,
  RequirementBatchGenerateTasksPayload,
  RequirementBatchGenerateTasksResult,
  RequirementBatchSchedulePayload,
  RequirementBatchScheduleResult,
  RequirementBatchSkippedItem,
  RequirementListItem,
  RequirementListQuery,
  RequirementMutationPayload,
  RequirementResponse,
} from './requirementClient';
export {
  approveTaskCenterReview,
  batchCancelTaskCenterTasks,
  batchRetryTaskCenterTasks,
  createAutomatedTestingTask,
  createDevelopmentPlanningTask,
  createPostReleaseAnalysisTask,
  createReleaseReadinessTask,
  createTaskWritebackResult,
  createTechnicalSolutionTask,
  editApproveTaskCenterReview,
  fetchTaskCenterPendingReviewList,
  fetchTaskCenterPendingReviews,
  fetchTaskCenterTaskDetail,
  fetchTaskCenterTasks,
  fetchTaskMarkdown,
  fetchTaskWritebackResult,
  rejectTaskCenterReview,
  requestTaskCenterReviewMoreInfo,
  startTaskCenterTask,
  submitTaskCenterMoreInfo,
} from './taskCenterClient';
export type {
  TaskBatchCancelPayload,
  TaskBatchCancelResult,
  TaskBatchRetriedItem,
  TaskBatchRetryPayload,
  TaskBatchRetryResult,
  TaskBatchSkippedItem,
  TaskCenterReviewListQuery,
  TaskCenterReviewRecord,
  TaskCenterTaskDetailRecord,
  TaskCenterTaskListResult,
  TaskCenterTaskQuery,
  TaskCenterTaskRecord,
  TaskListItem,
  TaskMoreInfoAnswer,
  TaskWritebackIssueRecord,
  TaskWritebackResultRecord,
} from './taskCenterClient';
export {
  fetchCodeInspectionDashboard,
  fetchCodeInspectionDetail,
  fetchCodeInspectionReports,
  requestCodeInspectionFindingSuppression,
  reviewCodeInspectionFindingSuppression,
} from './codeInspectionClient';
export type {
  CodeInspectionDashboardRecord,
  CodeInspectionDetailRecord,
  CodeInspectionFindingRecord,
  CodeInspectionListQuery,
  CodeInspectionNotificationRecord,
  CodeInspectionReportRecord,
} from './codeInspectionClient';
export {
  activateKnowledgeChunkSet,
  approveKnowledgeDeposit,
  batchMoveKnowledgeDocuments,
  cancelKnowledgeImportJob,
  createKnowledgeFolder,
  createKnowledgeSpace,
  createManagementKnowledgeDocument,
  deleteManagementKnowledgeDocument,
  fetchKnowledgeChunks,
  fetchKnowledgeChunkSets,
  fetchKnowledgeDeposits,
  fetchKnowledgeDocumentAssets,
  fetchKnowledgeFolders,
  fetchKnowledgeIndexHealth,
  fetchKnowledgeImportJobs,
  fetchKnowledgeImportWorkerStatus,
  fetchKnowledgeSearchResults,
  fetchKnowledgeSpaces,
  fetchManagementKnowledge,
  fetchManagementKnowledgeList,
  rejectKnowledgeDeposit,
  reparseKnowledgeDocument,
  retryKnowledgeDocumentIndex,
  retryKnowledgeImportJob,
  runKnowledgeImportJob,
  updateKnowledgeFolder,
  updateManagementKnowledgeDocument,
  uploadKnowledgeDocument,
} from './knowledgeClient';
export type {
  KnowledgeAssetRecord,
  KnowledgeChunkRecord,
  KnowledgeChunkSetRecord,
  KnowledgeDepositApprovePayload,
  KnowledgeDepositListItem,
  KnowledgeDepositRecord,
  KnowledgeDocumentListItem,
  KnowledgeDocumentMutationPayload,
  KnowledgeDocumentUploadPayload,
  KnowledgeFolderRecord,
  KnowledgeImportJobRecord,
  KnowledgeImportWorkerStatusRecord,
  KnowledgeIndexHealthIssueRecord,
  KnowledgeIndexHealthRecord,
  KnowledgeListQuery,
  KnowledgeSearchResultRecord,
  KnowledgeSpaceRecord,
} from './knowledgeClient';
export {
  fetchLifecycleFullChain,
  fetchRequirementFullChain,
  fullChainSubjectHref,
} from './lifecycleClient';
export type {
  RequirementFullChainAuditEvent,
  RequirementFullChainRecord,
  RequirementFullChainSummary,
  RequirementFullChainTimelineItem,
} from './lifecycleClient';
export { fetchItTeamDashboard } from './dashboardClient';
export type {
  DashboardAuditSummary,
  DashboardBugSummary,
  DashboardCacheMetadata,
  DashboardGitLabSummary,
  DashboardKnowledgeSummary,
  DashboardOnlineLogSummary,
  DashboardReviewSummary,
  DashboardStatusCount,
  DashboardSummary,
  DashboardTaskSummary,
  DashboardUsageMetricSummary,
  ItTeamDashboard,
} from './dashboardClient';
export {
  fetchActiveProductOptions,
  fetchBugProductContextOptions,
  fetchProductContextOptions,
  fetchRequirementProductContextOptions,
} from './productContextClient';
export type { ProductFilterOption } from './productContextClient';
export { fetchProductVersionDashboard } from './productVersionDashboardClient';
export type { ProductVersionDashboard } from './productVersionDashboardClient';

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
  icon?: string;
  is_system?: boolean;
  menu_type?: string;
  name: string;
  parent_code?: string | null;
  path?: string | null;
  required_permissions?: string[];
  sort_order?: number;
  status?: string;
};

export type MenuResourceMutationPayload = {
  code?: string;
  icon?: string;
  menu_type?: string;
  name?: string;
  parent_code?: string | null;
  path?: string;
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

export type RbacPolicyMatrixRow = {
  category: string;
  diagnostics: Array<{
    code: string;
    level: string;
    message: string;
    permission_codes?: string[];
  }>;
  granted_menu_codes: string[];
  granted_permission_codes: string[];
  high_risk_permission_codes: string[];
  high_risk_permission_count: number;
  is_system: boolean;
  menu_count: number;
  missing_menu_permission_codes: string[];
  permission_count: number;
  required_permission_codes: string[];
  role_code: string;
  role_id: string;
  role_name: string;
  scope_count: number;
  scope_summary: string;
  scopes: ScopeGrant[];
  standalone_permission_codes: string[];
  status: string;
};

export type RbacPolicyMatrix = {
  menus: MenuResourceRecord[];
  permissions: PermissionRecord[];
  roles: SystemRoleRecord[];
  rows: RbacPolicyMatrixRow[];
  summary: {
    active_role_count: number;
    menu_count: number;
    permission_count: number;
    role_count: number;
    roles_with_high_risk_permissions: number;
    roles_with_menu_permission_gaps: number;
    scope_grant_count: number;
  };
};

export type UserPermissionDiagnosticCheck = {
  code: string;
  granted_by_roles?: Array<{
    role_code: string;
    role_name: string;
  }>;
  granted_menu_code?: string | null;
  known?: boolean;
  matched_menu?: {
    code: string;
    name?: string;
    path?: string;
  };
  matched_scopes?: ScopeGrant[];
  message: string;
  missing_permission_codes?: string[];
  permission?: {
    code: string;
    name?: string;
    risk_level?: string | null;
  };
  required_permission_codes?: string[];
  role_codes?: string[];
  status: 'allowed' | 'blocked' | string;
  target?: string;
};

export type UserPermissionDiagnostic = {
  checks: UserPermissionDiagnosticCheck[];
  decision: {
    allowed: boolean;
    blocked_reasons: string[];
    granted_reasons: string[];
  };
  effective: {
    menu_codes: string[];
    permission_codes: string[];
    role_codes: string[];
    scopes: ScopeGrant[];
  };
  user: {
    display_name?: string;
    id: string;
    roles: string[];
    status: string;
    username?: string;
  };
};

export type AssistantChatResponse = {
  content: string;
  conversationId: string;
  intent?: AssistantIntent;
  latencyMs: number;
  messageId: string;
  model: string;
  references: AssistantReference[];
  run?: AssistantChatRun;
  runId?: string;
  status?: string;
  suggestions: string[];
  toolResults: AssistantToolResult[];
};

export type AssistantChatRun = {
  assistant_message_id?: string;
  cancel_reason?: string;
  cancelled_at?: string;
  cancelled_by?: string;
  client_request_id?: string;
  conversation_id?: string;
  error_code?: string;
  error_message?: string;
  finished_at?: string;
  id: string;
  started_at?: string;
  status: string;
  user_message_id?: string;
};

export type AssistantRuntimeStatus = {
  checks?: Array<{
    action_label?: string;
    action_url?: string;
    code: string;
    description?: string;
    detail?: string;
    key?: string;
    label?: string;
    remediation?: string;
    required?: boolean;
    severity?: 'critical' | 'info' | 'warning' | string;
    status: string;
    url?: string;
  }>;
  chat_gateway: string;
  embedding_gateway: string;
  long_memory: string;
  mode: 'deterministic_only' | 'model_gateway' | string;
  model_gateway: string;
  operations?: {
    executor_queue?: {
      active_runners?: number;
      failed?: number;
      offline_runners?: number;
      oldest_pending_task_created_at?: string | null;
      oldest_pending_task_id?: string | null;
      queued?: number;
      running?: number;
      succeeded?: number;
      total_runners?: number;
      visible?: boolean;
    };
    model_gateway_recent_failure?: AssistantRuntimeFailure | null;
    recent_failures?: AssistantRuntimeFailure[];
  };
  ready?: boolean;
  warnings?: Array<{
    code?: string;
    message?: string;
  }>;
};

export type AssistantRuntimeFailure = {
  created_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  id: string;
  kind: string;
  label?: string;
  status?: string | null;
  title?: string | null;
  updated_at?: string | null;
  url?: string | null;
};

export type AssistantIntent = {
  confidence?: number;
  intent_code?: string;
  required_refs?: string[];
  summary?: string;
};

export type AssistantReference = {
  action?: string;
  chunk_count?: number;
  chunk_index?: number;
  created_at?: string;
  document_count?: number;
  document_id?: string;
  folder_path?: string;
  id: string;
  index_status?: string;
  knowledge_space_id?: string;
  permission_label?: string;
  source_module?: string;
  summary?: string;
  prompt?: string;
  title: string;
  type: string;
  updated_at?: string;
  url: string;
};

export type AssistantDraftTemplate = {
  available?: boolean;
  category?: string;
  code: string;
  dependencies?: string[];
  description?: string;
  draft_action?: string;
  name: string;
  prompt: string;
  roles?: string[];
  source_module?: string;
  target_resource?: string;
  template_version?: string;
  wizard_steps?: string[];
};

export type AssistantToolResultItem = {
  action?: string;
  client_draft_id?: string;
  draft_id?: string;
  payload?: Record<string, unknown>;
  preview?: AssistantActionDraftPreview;
  requires_confirmation?: boolean;
  risk_level?: string;
  server_draft_id?: string;
  status?: string;
  title?: string;
  [key: string]: unknown;
};

export type AssistantToolResult = {
  intent?: string;
  items?: AssistantToolResultItem[];
  references?: AssistantReference[];
  summary?: Record<string, unknown>;
  tool: string;
};

export type AssistantConversationSummary = {
  collapsedConversationIds?: string[];
  collapsedMessageCount?: number;
  commandSignature?: string;
  contextScope?: string;
  createdAt?: string;
  duplicateConversationIds?: string[];
  duplicateCount?: number;
  id: string;
  lastMessageAt?: string;
  messageCount: number;
  productId?: string;
  sourceMessageHash?: string;
  title: string;
  updatedAt?: string;
};

export type AssistantConversationPage = {
  items: AssistantConversationSummary[];
  limit: number;
  nextCursor?: string;
  total: number;
};

export type AssistantConversationMessage = {
  cancelledAt?: string;
  clientRequestId?: string;
  completedAt?: string;
  content: string;
  createdAt?: string;
  errorCode?: string;
  failedAt?: string;
  id: string;
  intent?: AssistantIntent;
  model?: string;
  productId?: string;
  role: 'assistant' | 'user';
  runId?: string;
  status?: string;
  references: AssistantReference[];
  suggestions: string[];
  toolResults: AssistantToolResult[];
};

type AssistantChatApiResponse = {
  conversation_id: string;
  latency_ms?: number;
  message: {
    cancelled_at?: string;
    client_request_id?: string;
    completed_at?: string;
    content?: string;
    error_code?: string;
    failed_at?: string;
    id?: string;
    intent?: AssistantIntent;
    references?: AssistantReference[];
    role?: string;
    run_id?: string;
    status?: string;
    tool_results?: AssistantToolResult[];
  };
  model?: string;
  references?: AssistantReference[];
  run?: AssistantChatRun;
  run_id?: string;
  suggestions?: string[];
  tool_results?: AssistantToolResult[];
};

type AssistantConversationApiRecord = {
  collapsed_conversation_ids?: string[];
  collapsed_message_count?: number;
  command_signature?: string;
  context_scope?: string;
  created_at?: string;
  duplicate_conversation_ids?: string[];
  duplicate_count?: number;
  id: string;
  last_message_at?: string;
  message_count?: number;
  product_id?: string;
  source_message_hash?: string;
  title?: string;
  updated_at?: string;
};

type AssistantMessageApiRecord = {
  cancelled_at?: string;
  client_request_id?: string;
  completed_at?: string;
  content?: string;
  created_at?: string;
  error_code?: string;
  failed_at?: string;
  id?: string;
  intent?: AssistantIntent;
  model?: string;
  product_id?: string;
  role?: string;
  run_id?: string;
  status?: string;
  references?: AssistantReference[];
  suggestions?: string[];
  tool_results?: AssistantToolResult[];
};

export type AssistantChatPayload = {
  clientRequestId?: string;
  context?: Record<string, unknown>;
  conversationId?: string;
  message: string;
  productId?: string;
  references?: AssistantReference[];
  runId?: string;
  signal?: AbortSignal;
};

export type ProductResponse = {
  code?: string;
  description?: string | null;
  id: string;
  name?: string;
  owner_team?: string | null;
  status?: string;
};

type RemoteSortOrder = 'ascend' | 'descend';

type RemoteListQuery = {
  page?: number;
  pageSize?: number;
  sortField?: string;
  sortOrder?: RemoteSortOrder;
};

export type ProductListQuery = RemoteListQuery & {
  code?: string;
  name?: string;
  ownerTeam?: string;
  status?: string;
};

export type ProductVersionListQuery = RemoteListQuery & {
  code?: string;
  name?: string;
  product?: string;
  status?: string;
};

export type AuditListQuery = RemoteListQuery & {
  actor?: string;
  eventType?: string;
  result?: string;
  subject?: string;
};

export type ExecutionTraceListQuery = RemoteListQuery & {
  createdFrom?: string;
  createdTo?: string;
  keyword?: string;
  refresh?: boolean;
  sourceId?: string;
  sourceType?: string;
  status?: string;
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

export type MenuListQuery = RemoteListQuery & {
  menu?: string;
  menuType?: string;
  parent?: string;
  path?: string;
  permission?: string;
  status?: string;
};

export type ScheduledJobListQuery = RemoteListQuery & {
  enabled?: boolean;
  jobType?: string;
  keyword?: string;
  name?: string;
  productId?: string;
  sourceSystem?: string;
  status?: string;
};

export type ScheduledJobRunFilterQuery = Partial<RemoteListQuery> & {
  runIds?: string[];
  scheduledJobId?: string;
  status?: string;
};

export type ScheduledJobRunListQuery = ScheduledJobRunFilterQuery & {
  page: number;
};

export type PluginConnectionListQuery = RemoteListQuery & {
  environment?: string;
  keyword?: string;
  pluginId?: string;
  status?: string;
};

export type PluginActionListQuery = RemoteListQuery & {
  keyword?: string;
  pluginId?: string;
  status?: string;
};

export type RdTaskExecutorPolicyListQuery = RemoteListQuery & {
  executorType?: string;
  name?: string;
  productId?: string;
  productName?: string;
  status?: string;
  taskType?: string;
};

export type AiSkillListQuery = RemoteListQuery & {
  code?: string;
  keyword?: string;
  requiresHumanReview?: boolean;
  riskLevel?: string;
  sourceType?: string;
  status?: string;
};

export type AiAgentListQuery = RemoteListQuery & {
  brainAppId?: string;
  keyword?: string;
  modelGatewayConfigId?: string;
  status?: string;
};

export type RemoteListResult<Row> = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: Row[];
  total: number;
};

export type OperationalMetricRecord = {
  category: string;
  id: string;
  name: string;
  status: string;
  updatedAt: string;
  value: string;
};

export type ExecutionTraceNodeRecord = {
  duration_ms?: number | null;
  error_code?: string | null;
  error_message?: string | null;
  finished_at?: string | null;
  id: string;
  label: string;
  metadata?: Record<string, unknown>;
  source_id: string;
  source_type: string;
  started_at?: string | null;
  status: string;
  summary?: string | null;
};

export type ExecutionTraceEdgeRecord = {
  from: string;
  label?: string;
  to: string;
};

export type ExecutionTraceListItem = {
  diagnostic_nodes?: ExecutionTraceNodeRecord[];
  duration_ms?: number | null;
  failed_node_count: number;
  id: string;
  node_count: number;
  related_ids?: Record<string, string[]>;
  root_id: string;
  root_type: string;
  running_node_count: number;
  started_at?: string | null;
  status: string;
  summary: string;
  title: string;
  updated_at?: string | null;
};

export type ExecutionTraceDetailRecord = ExecutionTraceListItem & {
  edges: ExecutionTraceEdgeRecord[];
  nodes: ExecutionTraceNodeRecord[];
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

export type UserMutationPayload = {
  display_name?: string;
  password?: string;
  roles?: string[];
  status?: string;
  username?: string;
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

type FlexibleListItem = Record<string, unknown> & {
  created_at?: string;
  id?: string;
  status?: string;
  updated_at?: string;
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

export async function chatWithAssistant(
  payload: AssistantChatPayload,
): Promise<AssistantChatResponse> {
  const token = requireAccessToken();
  const response = await apiRequest<AssistantChatApiResponse>('/api/assistant/chat', {
    body: {
      client_request_id: payload.clientRequestId,
      context: payload.context,
      conversation_id: payload.conversationId,
      message: payload.message,
      product_id: payload.productId,
      references: payload.references?.map((reference) => ({
        id: reference.id,
        type: reference.type,
      })) ?? [],
      run_id: payload.runId,
    },
    method: 'POST',
    signal: payload.signal,
    token,
  });
  return {
    content: response.message.content ?? '',
    conversationId: response.conversation_id,
    intent: response.message.intent,
    latencyMs: Number(response.latency_ms ?? 0),
    messageId: response.message.id ?? response.conversation_id,
    model: response.model ?? '',
    references: response.message.references ?? response.references ?? [],
    run: response.run,
    runId: response.run_id ?? response.message.run_id ?? response.run?.id,
    status: response.message.status,
    suggestions: response.suggestions ?? [],
    toolResults: response.message.tool_results ?? response.tool_results ?? [],
  };
}

export async function cancelAssistantChatRun(
  runId: string,
  reason = 'user_cancelled',
): Promise<AssistantChatRun> {
  const token = requireAccessToken();
  return apiRequest<AssistantChatRun>(`/api/assistant/chat-runs/${runId}/cancel`, {
    body: { reason },
    method: 'POST',
    token,
  });
}

export async function fetchAssistantChatRuns(params: {
  limit?: number;
  status?: string;
} = {}): Promise<AssistantChatRun[]> {
  const token = requireAccessToken();
  const searchParams = new URLSearchParams();
  if (params.status) {
    searchParams.set('status', params.status);
  }
  if (params.limit) {
    searchParams.set('limit', String(params.limit));
  }
  const query = searchParams.toString();
  const response = await apiRequest<ListResponse<AssistantChatRun>>(
    `/api/assistant/chat-runs${query ? `?${query}` : ''}`,
    {
      method: 'GET',
      token,
    },
  );
  return response.items;
}

export async function fetchAssistantRuntimeStatus(): Promise<AssistantRuntimeStatus> {
  const token = requireAccessToken();
  return apiRequest<AssistantRuntimeStatus>('/api/assistant/runtime-status', {
    method: 'GET',
    token,
  });
}

export async function fetchAssistantReferenceCandidates(params: {
  limit?: number;
  query: string;
  signal?: AbortSignal;
  type?: string;
}): Promise<AssistantReference[]> {
  const token = requireAccessToken();
  const searchParams = new URLSearchParams();
  searchParams.set('query', params.query);
  if (params.type) {
    searchParams.set('type', params.type);
  }
  if (params.limit) {
    searchParams.set('limit', String(params.limit));
  }
  const response = await apiRequest<ListResponse<AssistantReference>>(
    `/api/assistant/reference-candidates?${searchParams.toString()}`,
    {
      method: 'GET',
      signal: params.signal,
      token,
    },
  );
  return response.items;
}

export async function fetchAssistantDraftTemplates(): Promise<AssistantDraftTemplate[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<AssistantDraftTemplate>>(
    '/api/assistant/draft-templates',
    {
      method: 'GET',
      token,
    },
  );
  return response.items;
}

function assistantConversationApiRecordToSummary(
  item: AssistantConversationApiRecord,
): AssistantConversationSummary {
  return {
    collapsedConversationIds: item.collapsed_conversation_ids,
    collapsedMessageCount: item.collapsed_message_count,
    commandSignature: item.command_signature,
    contextScope: item.context_scope,
    createdAt: item.created_at,
    duplicateConversationIds: item.duplicate_conversation_ids,
    duplicateCount: item.duplicate_count,
    id: item.id,
    lastMessageAt: item.last_message_at,
    messageCount: Number(item.message_count ?? 0),
    productId: item.product_id,
    sourceMessageHash: item.source_message_hash,
    title: item.title ?? '新对话',
    updatedAt: item.updated_at,
  };
}

export async function fetchAssistantConversationPage(params: {
  collapse?: boolean;
  cursor?: string;
  limit?: number;
} = {}): Promise<AssistantConversationPage> {
  const token = requireAccessToken();
  const searchParams = new URLSearchParams();
  if (params.collapse === false) {
    searchParams.set('collapse', 'false');
  }
  if (params.cursor) {
    searchParams.set('cursor', params.cursor);
  }
  if (params.limit) {
    searchParams.set('limit', String(params.limit));
  }
  const query = searchParams.toString();
  const response = await apiRequest<ListResponse<AssistantConversationApiRecord>>(
    `/api/assistant/conversations${query ? `?${query}` : ''}`,
    {
      method: 'GET',
      token,
    },
  );
  return {
    items: response.items.map(assistantConversationApiRecordToSummary),
    limit: Number(response.limit ?? params.limit ?? response.items.length),
    nextCursor: response.next_cursor ?? undefined,
    total: Number(response.total ?? response.items.length),
  };
}

export async function fetchAssistantConversations(params: {
  collapse?: boolean;
  cursor?: string;
  limit?: number;
} = {}): Promise<AssistantConversationSummary[]> {
  const response = await fetchAssistantConversationPage(params);
  return response.items;
}

export async function fetchAssistantConversationMessages(
  conversationId: string,
  options: { signal?: AbortSignal } = {},
): Promise<AssistantConversationMessage[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<AssistantMessageApiRecord>>(
    `/api/assistant/conversations/${conversationId}/messages`,
    {
      method: 'GET',
      signal: options.signal,
      token,
    },
  );
  return response.items.map((item) => ({
    cancelledAt: item.cancelled_at,
    clientRequestId: item.client_request_id,
    completedAt: item.completed_at,
    content: item.content ?? '',
    createdAt: item.created_at,
    errorCode: item.error_code,
    failedAt: item.failed_at,
    id: item.id ?? conversationId,
    intent: item.intent,
    model: item.model,
    productId: item.product_id,
    references: item.references ?? [],
    role: item.role === 'user' ? 'user' : 'assistant',
    runId: item.run_id,
    status: item.status,
    suggestions: item.suggestions ?? [],
    toolResults: item.tool_results ?? [],
  }));
}

function formatListDate(value?: string) {
  return formatDisplayDateTime(value);
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

function normalizeObjectRecord(value: unknown): Record<string, unknown> | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  return value as Record<string, unknown>;
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
    performance: products.performance,
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
    performance: versions.performance,
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

export async function fetchSystemMenuList(
  query: MenuListQuery = {},
): Promise<RemoteListResult<MenuResourceRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'menu', query.menu);
  appendQueryParam(params, 'menu_type', query.menuType);
  appendQueryParam(params, 'parent', query.parent);
  appendQueryParam(params, 'path', query.path);
  appendQueryParam(params, 'permission', query.permission);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const menus = await apiRequest<ListResponse<MenuResourceRecord>>(
    queryString ? `/api/system/menus?${queryString}` : '/api/system/menus',
    { token },
  );
  return {
    page: menus.page ?? query.page ?? 1,
    pageSize: menus.page_size ?? query.pageSize ?? 10,
    performance: menus.performance,
    rows: menus.items,
    total: menus.total,
  };
}

export async function fetchSystemPermissionMatrix(): Promise<RbacPolicyMatrix> {
  const token = requireAccessToken();
  const matrix = await apiRequest<RbacPolicyMatrix>('/api/system/permissions/matrix', { token });
  return {
    ...matrix,
    roles: matrix.roles.map(mapSystemRole),
  };
}

export async function fetchSystemPermissionDiagnostics(query: {
  path?: string;
  permissionCode?: string;
  scopeId?: string;
  scopeType?: string;
  userId: string;
}): Promise<UserPermissionDiagnostic> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'user_id', query.userId);
  appendQueryParam(params, 'path', query.path);
  appendQueryParam(params, 'permission_code', query.permissionCode);
  appendQueryParam(params, 'scope_type', query.scopeType);
  appendQueryParam(params, 'scope_id', query.scopeId);
  return apiRequest<UserPermissionDiagnostic>(`/api/system/permissions/diagnostics?${params.toString()}`, {
    token,
  });
}

export async function createSystemMenu(
  payload: MenuResourceMutationPayload & { code: string; name: string },
): Promise<MenuResourceRecord> {
  const token = requireAccessToken();
  return apiRequest<MenuResourceRecord>('/api/system/menus', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateSystemMenu(
  menuCode: string,
  payload: MenuResourceMutationPayload,
): Promise<MenuResourceRecord> {
  const token = requireAccessToken();
  return apiRequest<MenuResourceRecord>(`/api/system/menus/${menuCode}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function setSystemMenuStatus(
  menuCode: string,
  status: 'active' | 'inactive',
): Promise<MenuResourceRecord> {
  const token = requireAccessToken();
  const action = status === 'active' ? 'enable' : 'disable';
  return apiRequest<MenuResourceRecord>(`/api/system/menus/${menuCode}/${action}`, {
    method: 'POST',
    token,
  });
}

export async function deleteSystemMenu(menuCode: string): Promise<{ code: string; deleted: boolean }> {
  const token = requireAccessToken();
  return apiRequest<{ code: string; deleted: boolean }>(`/api/system/menus/${menuCode}`, {
    method: 'DELETE',
    token,
  });
}

export async function reorderSystemMenus(
  items: Array<{ code: string; sort_order: number }>,
): Promise<MenuResourceRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<{ items: MenuResourceRecord[] }>('/api/system/menus/reorder', {
    body: { items },
    method: 'PUT',
    token,
  });
  return response.items;
}

export async function fetchSystemRoleList(
  query: RoleListQuery = {},
): Promise<RemoteListResult<SystemRoleRecord>> {
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
    queryString ? `/api/system/roles?${queryString}` : '/api/system/roles',
    { token },
  );
  return {
    page: roles.page ?? query.page ?? 1,
    pageSize: roles.page_size ?? query.pageSize ?? 10,
    performance: roles.performance,
    rows: roles.items.map(mapSystemRole),
    total: roles.total,
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
    performance: users.performance,
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

export type AiSkillRecord = {
  allowed_tools?: string[];
  code: string;
  id: string;
  input_schema?: Record<string, unknown>;
  manifest?: Record<string, unknown>;
  name: string;
  output_schema?: Record<string, unknown>;
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
  model_gateway_config?: Record<string, unknown> | null;
  model_gateway_config_id?: string | Record<string, unknown> | null;
  model_gateway_config_snapshot?: Record<string, unknown> | null;
  name: string;
  resolved_model_gateway_config?: Record<string, unknown> | null;
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
  plugin_action_ids?: string[];
  plugin_connection_id?: string | null;
  plugin_connection_ids?: string[];
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

export type ScheduledJobCatalogOption = {
  label: string;
  value: string;
};

export type ScheduledJobCatalogJobType = ScheduledJobCatalogOption & {
  category?: string;
  default_execution_mode?: string;
  requires_ai_assembly?: boolean;
  requires_plugin_resource?: boolean;
  requires_product?: boolean;
};

export type ScheduledJobCatalogRecord = {
  code_inspection?: {
    builtin_rules?: ScheduledJobCatalogOption[];
    default_result_actions?: ScheduledJobResultAction[];
    default_scan_mode?: string;
    ignore_rules?: ScheduledJobCatalogOption[];
    native_scan_mode?: string;
    result_actions?: ScheduledJobCatalogOption[];
    scan_modes?: ScheduledJobCatalogOption[];
    scanner_engines?: ScheduledJobCatalogOption[];
    severity_thresholds?: ScheduledJobCatalogOption[];
  };
  connection_environments?: ScheduledJobCatalogOption[];
  execution_modes?: ScheduledJobCatalogOption[];
  job_types?: ScheduledJobCatalogJobType[];
  required_job_types?: {
    ai_processing?: string[];
    plugin_resource?: string[];
    product?: string[];
  };
  schedule_types?: ScheduledJobCatalogOption[];
};

export type ScheduledJobTemplateWizardStepRecord = {
  description?: string;
  key: string;
  required?: boolean;
  title: string;
};

export type ScheduledJobTemplateRecord = {
  available_resource_counts?: Record<string, number>;
  category?: string;
  code: string;
  description?: string;
  installed?: boolean;
  name: string;
  payload_defaults?: Partial<ScheduledJobRecord>;
  publisher?: string;
  recommended_scenarios?: string[];
  resource_selectors?: Record<string, unknown>;
  template_version?: string;
  wizard_steps?: ScheduledJobTemplateWizardStepRecord[];
};

export type ScheduledJobDryRunResult = {
  job_type?: string;
  stages?: {
    ai_processing?: Record<string, unknown>;
    data_connection?: Record<string, unknown>;
    result_actions?: Array<Record<string, unknown>>;
  };
  status: string;
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
  source_run_id?: string | null;
  source_run_summary?: {
    error_code?: string | null;
    finished_at?: string | null;
    id?: string;
    latency_ms?: number | null;
    records_imported?: number;
    started_at?: string | null;
    status?: string | null;
    trigger_type?: string | null;
  } | null;
  started_at?: string | null;
  status: string;
  tool_policy_snapshot?: Record<string, unknown>;
  trigger_type?: string;
  updated_at?: string | null;
};

export type ScheduledJobRunObservability = {
  error_distribution?: Array<{ count: number; error: string }>;
  generated_at?: string;
  job_type_distribution?: Array<{ count: number; job_type: string }>;
  recent_failures?: Array<{
    error_code?: string | null;
    error_message?: string | null;
    id: string;
    job_name?: string;
    latency_ms?: number | null;
    scheduled_job_id?: string | null;
    started_at?: string | null;
  }>;
  slow_runs?: Array<{
    error_code?: string | null;
    id: string;
    job_name?: string;
    latency_ms?: number | null;
    records_imported?: number;
    scheduled_job_id?: string | null;
    started_at?: string | null;
    status?: string;
  }>;
  status_distribution?: Array<{ count: number; status: string }>;
  summary: {
    action_write_runs?: number;
    action_write_success_rate?: number;
    action_write_success_runs?: number;
    average_latency_ms?: number;
    average_records_imported?: number;
    cancelled_runs?: number;
    failed_runs?: number;
    failure_rate?: number;
    model_gateway_called_runs?: number;
    model_gateway_token_total?: number;
    plugin_invocation_runs?: number;
    running_runs?: number;
    success_rate?: number;
    succeeded_runs?: number;
    total_runs?: number;
  };
  trigger_type_distribution?: Array<{ count: number; trigger_type: string }>;
  write_target_distribution?: Array<{ count: number; write_target: string }>;
};

export type PluginRecord = {
  category?: string;
  code: string;
  description?: string | null;
  id: string;
  is_system?: boolean;
  latest_template_version?: string;
  name: string;
  protocol: string;
  risk_level?: string;
  source_plugin_code?: string | null;
  source_plugin_id?: string | null;
  status: string;
  template_version?: string;
  upgrade_available?: boolean;
  version_status?: string;
};

export type PluginMarketplaceItem = {
  action_count: number;
  action_templates?: string[];
  category: string;
  code: string;
  connection_schema?: PluginConnectionSchemaRecord;
  connection_defaults?: Record<string, unknown>;
  connection_count: number;
  connection_template_version?: string;
  description?: string | null;
  id: string;
  installed: boolean;
  is_system?: boolean;
  latest_template_version?: string;
  name: string;
  plugin_id?: string | null;
  protocol: string;
  publisher?: string;
  recommended_scenarios?: string[];
  risk_level?: string;
  status: string;
  summary?: string;
  template_version?: string;
  upgrade_available?: boolean;
  version_status?: string;
};

export type PluginConnectionSchemaFieldRecord = {
  description?: string;
  key: string;
  label: string;
  managed_query_keys?: string[];
  options?: Array<{ label: string; value: string } | string>;
  path?: string;
  placeholder?: string;
  required?: boolean;
  supports_system_variables?: boolean;
  type?: string;
};

export type PluginConnectionSchemaSectionRecord = {
  fields: PluginConnectionSchemaFieldRecord[];
  key: string;
  title: string;
};

export type PluginConnectionSchemaRecord = {
  schema_version?: string;
  sections?: PluginConnectionSchemaSectionRecord[];
};

export type PluginActionTemplateRecord = {
  action_type: string;
  code: string;
  default_code?: string;
  default_name?: string;
  description?: string | null;
  form_defaults?: Record<string, unknown>;
  name: string;
  plugin_code: string;
  plugin_id?: string | null;
  request_config?: Record<string, unknown>;
  result_mapping?: Record<string, unknown>;
  template_version?: string;
};

export type ResultWriteTargetFieldRecord = {
  description?: string;
  key: string;
  label: string;
  placeholder?: string;
  required?: boolean;
};

export type ResultWriteTargetRecord = {
  code: string;
  default_result_mapping: Record<string, unknown>;
  description?: string;
  form_label?: string;
  label: string;
  mapping_fields: ResultWriteTargetFieldRecord[];
  supported_job_types?: string[];
};

export type ResultWriteRecord = {
  created_at?: string | null;
  feedback?: Record<string, unknown>;
  id: string;
  plugin_action_id?: string | null;
  plugin_code?: string | null;
  plugin_connection_id?: string | null;
  plugin_id?: string | null;
  plugin_invocation_log_id?: string | null;
  preview?: Record<string, unknown>;
  records_imported?: number;
  scheduled_job_id?: string | null;
  scheduled_job_name?: string | null;
  scheduled_job_run_id?: string | null;
  source_type?: string;
  status: string;
  summary_fields?: {
    candidate_count?: number;
    delivery_id?: unknown;
    delivery_status?: unknown;
    preview_value?: unknown;
    report_preview?: unknown;
    sample_records?: unknown[];
    source_row_count?: number | null;
    subject?: unknown;
  };
  updated_at?: string | null;
  write_target: string;
  write_target_label?: string;
};

export type PluginConnectionRecord = {
  auth_config?: Record<string, unknown>;
  auth_type?: string;
  endpoint_url: string;
  environment?: string;
  id: string;
  last_test_summary?: {
    checked_at?: string | null;
    error_code?: string | null;
    error_message?: string | null;
    failed_step?: string | null;
    latency_ms?: number | null;
    mocked?: boolean;
    response_status_code?: number | null;
    status?: string | null;
  };
  max_retries?: number;
  name: string;
  plugin_id: string;
  request_config?: Record<string, unknown>;
  status: string;
  test_history?: PluginConnectionTestHistoryRecord[];
  timeout_seconds?: number;
};

export type PluginConnectionRepairSuggestion = {
  code: string;
  detail: string;
  title: string;
};

export type PluginConnectionActionTemplateDraft = {
  action_type?: string;
  code?: string;
  connection_id?: string;
  description?: string;
  name?: string;
  plugin_id?: string;
  request_config?: Record<string, unknown>;
  requires_human_review?: boolean;
  result_mapping?: Record<string, unknown>;
  status?: string;
};

export type PluginConnectionTestHistoryRecord = {
  action_template_draft?: PluginConnectionActionTemplateDraft;
  checked_at?: string;
  error_code?: string | null;
  error_message?: string | null;
  latency_ms?: number;
  repair_suggestions?: PluginConnectionRepairSuggestion[];
  request_summary?: Record<string, unknown>;
  response_summary?: Record<string, unknown>;
  status?: string;
};

export type PluginConnectionTestResult = {
  action_template_draft?: PluginConnectionActionTemplateDraft;
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
  repair_suggestions?: PluginConnectionRepairSuggestion[];
  response_summary?: Record<string, unknown>;
  status: string;
  test_history?: PluginConnectionTestHistoryRecord[];
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

export type AiExecutorRunnerRecord = {
  created_at?: string | null;
  endpoint_url?: string;
  executor_types?: string[];
  heartbeat_age_seconds?: number | null;
  heartbeat_timeout_seconds?: number;
  health_status?: string;
  id: string;
  latest_task_id?: string | null;
  latest_task_status?: string | null;
  last_heartbeat_at?: string | null;
  max_concurrent_tasks?: number;
  metadata?: Record<string, unknown>;
  name: string;
  protocol?: string;
  runner_token?: string;
  setup_command?: string;
  status: string;
  token_configured?: boolean;
  token_rotated_at?: string | null;
  token_version?: number;
  updated_at?: string | null;
  workspace_roots?: string[];
};

export type AiExecutorRunnerListQuery = RemoteListQuery & {
  executorType?: string;
  keyword?: string;
  protocol?: string;
  status?: string;
};

export type AiExecutorTaskRecord = {
  action_id?: string | null;
  ai_task_id?: string | null;
  assigned_at?: string | null;
  cancelled_at?: string | null;
  claimed_at?: string | null;
  completed_at?: string | null;
  created_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  executor_type?: string | null;
  finished_at?: string | null;
  id: string;
  logs?: AiExecutorTaskLogRecord[];
  request_config?: Record<string, unknown>;
  result?: Record<string, unknown>;
  runner_id?: string | null;
  scheduled_job_run_id?: string | null;
  status: string;
  timed_out_at?: string | null;
  updated_at?: string | null;
  workspace_root?: string | null;
};

export type RdTaskExecutorPolicyRecord = {
  branch?: string | null;
  created_at?: string | null;
  created_by?: string | null;
  executor_type: string;
  id: string;
  instruction_template: string;
  name: string;
  output_contract?: Record<string, unknown>;
  priority: number;
  product_id?: string | null;
  product_name?: string | null;
  repository_default_branch?: string | null;
  repository_id?: string | null;
  repository_name?: string | null;
  runner_id?: string | null;
  runner_name?: string | null;
  status: string;
  task_type: string;
  timeout_seconds: number;
  updated_at?: string | null;
  workspace_root: string;
};

export type RdTaskExecutorPolicyPayload = {
  branch?: string | null;
  executor_type?: string;
  instruction_template?: string;
  name?: string;
  output_contract?: Record<string, unknown>;
  priority?: number;
  product_id?: string | null;
  repository_id?: string | null;
  runner_id?: string | null;
  status?: string;
  task_type?: string;
  timeout_seconds?: number;
  workspace_root?: string;
};

export type AiExecutorTaskLogRecord = {
  created_at?: string | null;
  level?: string;
  message: string;
  metadata?: Record<string, unknown>;
  sequence?: number;
};

export type AiExecutorTaskLogsResponse = {
  logs: AiExecutorTaskLogRecord[];
  task: AiExecutorTaskRecord;
};

export type AiExecutorRunnerInstallPackageOptions = {
  arch?: string;
  install_mode?: string;
  target_os?: string;
};

export type AiExecutorRunnerTestDiagnostic = {
  detail?: string | null;
  latency_ms?: number | null;
  name: string;
  status: string;
};

export type AiExecutorRunnerTestResult = {
  checked_at?: string | null;
  diagnostics?: AiExecutorRunnerTestDiagnostic[];
  health_status?: string | null;
  heartbeat_age_seconds?: number | null;
  latency_ms?: number | null;
  runner?: AiExecutorRunnerRecord;
  runner_id: string;
  status: string;
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
  write_preview?: {
    candidate_count?: number;
    preview_value?: unknown;
    records_imported?: number;
    report_preview?: Record<string, unknown>;
    sample_records?: unknown[];
    source_row_count?: number | null;
    write_target?: string;
    write_target_label?: string;
  };
};

export async function fetchPlugins(): Promise<PluginRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<PluginRecord>>('/api/system/plugins', { token });
  return response.items;
}

export async function fetchPluginMarketplace(): Promise<PluginMarketplaceItem[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<PluginMarketplaceItem>>('/api/system/plugin-marketplace', { token });
  return response.items;
}

export async function fetchPluginActionTemplates(): Promise<PluginActionTemplateRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<PluginActionTemplateRecord>>('/api/system/plugin-action-templates', { token });
  return response.items;
}

export async function fetchAiExecutorRunners(query: { status?: string } = {}): Promise<AiExecutorRunnerRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'status', query.status);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const response = await apiRequest<ListResponse<AiExecutorRunnerRecord>>(`/api/system/ai-executor-runners${suffix}`, { token });
  return response.items;
}

export async function fetchAiExecutorRunnersPage(
  query: AiExecutorRunnerListQuery = {},
): Promise<RemoteListResult<AiExecutorRunnerRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'executor_type', query.executorType);
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'protocol', query.protocol);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const response = await apiRequest<ListResponse<AiExecutorRunnerRecord>>(
    `/api/system/ai-executor-runners?${params.toString()}`,
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

export async function createAiExecutorRunner(payload: Partial<AiExecutorRunnerRecord>) {
  const token = requireAccessToken();
  return apiRequest<AiExecutorRunnerRecord>('/api/system/ai-executor-runners', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateAiExecutorRunner(runnerId: string, payload: Partial<AiExecutorRunnerRecord>) {
  const token = requireAccessToken();
  return apiRequest<AiExecutorRunnerRecord>(`/api/system/ai-executor-runners/${runnerId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteAiExecutorRunner(runnerId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/system/ai-executor-runners/${runnerId}`, {
    method: 'DELETE',
    token,
  });
}

export async function rotateAiExecutorRunnerToken(
  runnerId: string,
  payload: { runner_token?: string } = {},
) {
  const token = requireAccessToken();
  return apiRequest<AiExecutorRunnerRecord & { runner_token?: string }>(
    `/api/system/ai-executor-runners/${runnerId}/rotate-token`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
}

export async function testAiExecutorRunner(runnerId: string): Promise<AiExecutorRunnerTestResult> {
  const token = requireAccessToken();
  return apiRequest<AiExecutorRunnerTestResult>(`/api/system/ai-executor-runners/${runnerId}/test`, {
    method: 'POST',
    token,
  });
}

function filenameFromContentDisposition(value: string | null, fallback: string): string {
  if (!value) {
    return fallback;
  }
  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }
  const quotedMatch = value.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }
  const plainMatch = value.match(/filename=([^;]+)/i);
  return plainMatch?.[1]?.trim() || fallback;
}

export async function downloadAiExecutorRunnerInstallPackage(
  runnerId: string,
  options: AiExecutorRunnerInstallPackageOptions = {},
) {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'target_os', options.target_os);
  appendQueryParam(params, 'arch', options.arch);
  appendQueryParam(params, 'install_mode', options.install_mode);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const response = await fetch(`${API_BASE_URL}/api/system/ai-executor-runners/${runnerId}/install-package${suffix}`, {
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
    throw new ApiRequestError({
      code: payload?.detail?.code,
      message: payload?.detail?.message ?? `API request failed: ${response.status}`,
      status: response.status,
      traceId: payload?.detail?.trace_id,
    });
  }
  return {
    blob: await response.blob(),
    filename: filenameFromContentDisposition(
      response.headers.get('Content-Disposition'),
      `ai-brain-runner-${runnerId}.zip`,
    ),
  };
}

export async function fetchAiExecutorTaskLogs(taskId: string): Promise<AiExecutorTaskLogsResponse> {
  const token = requireAccessToken();
  return apiRequest<AiExecutorTaskLogsResponse>(`/api/system/ai-executor-tasks/${taskId}/logs`, {
    token,
  });
}

export async function fetchRdTaskExecutorPolicies(
  query: Pick<RdTaskExecutorPolicyListQuery, 'productId' | 'status' | 'taskType'> = {},
): Promise<RdTaskExecutorPolicyRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'product_id', query.productId);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'task_type', query.taskType);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const response = await apiRequest<ListResponse<RdTaskExecutorPolicyRecord>>(
    `/api/delivery/rd-task-executor-policies${suffix}`,
    { token },
  );
  return response.items;
}

export async function fetchRdTaskExecutorPolicyList(
  query: RdTaskExecutorPolicyListQuery,
): Promise<RemoteListResult<RdTaskExecutorPolicyRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'executor_type', query.executorType);
  appendQueryParam(params, 'name', query.name);
  appendQueryParam(params, 'product_id', query.productId);
  appendQueryParam(params, 'product_name', query.productName);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'task_type', query.taskType);
  appendRemoteListParams(params, query);
  const response = await apiRequest<ListResponse<RdTaskExecutorPolicyRecord>>(
    `/api/delivery/rd-task-executor-policies?${params.toString()}`,
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

export async function createRdTaskExecutorPolicy(payload: RdTaskExecutorPolicyPayload) {
  const token = requireAccessToken();
  return apiRequest<RdTaskExecutorPolicyRecord>('/api/delivery/rd-task-executor-policies', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateRdTaskExecutorPolicy(
  policyId: string,
  payload: RdTaskExecutorPolicyPayload,
) {
  const token = requireAccessToken();
  return apiRequest<RdTaskExecutorPolicyRecord>(
    `/api/delivery/rd-task-executor-policies/${policyId}`,
    {
      body: payload,
      method: 'PATCH',
      token,
    },
  );
}

export async function deleteRdTaskExecutorPolicy(policyId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(
    `/api/delivery/rd-task-executor-policies/${policyId}`,
    {
      method: 'DELETE',
      token,
    },
  );
}

export async function cancelAiExecutorTask(
  taskId: string,
  reason?: string,
): Promise<{ task: AiExecutorTaskRecord }> {
  const token = requireAccessToken();
  return apiRequest<{ task: AiExecutorTaskRecord }>(`/api/system/ai-executor-tasks/${taskId}/cancel`, {
    body: { reason },
    method: 'POST',
    token,
  });
}

export async function fetchResultWriteTargets(): Promise<ResultWriteTargetRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<ResultWriteTargetRecord>>('/api/system/result-write-targets', { token });
  return response.items;
}

export async function fetchResultWriteRecords(query: {
  page?: number;
  pageSize?: number;
  pluginActionId?: string;
  scheduledJobId?: string;
  scheduledJobRunId?: string;
  sortField?: string;
  sortOrder?: 'ascend' | 'descend';
  status?: string;
  writeTarget?: string;
} = {}): Promise<ResultWriteRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'page', query.page);
  appendQueryParam(params, 'page_size', query.pageSize);
  appendQueryParam(params, 'plugin_action_id', query.pluginActionId);
  appendQueryParam(params, 'scheduled_job_id', query.scheduledJobId);
  appendQueryParam(params, 'scheduled_job_run_id', query.scheduledJobRunId);
  appendQueryParam(params, 'sort_by', query.sortField);
  appendQueryParam(
    params,
    'sort_order',
    query.sortOrder === 'ascend' ? 'asc' : query.sortOrder === 'descend' ? 'desc' : undefined,
  );
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'write_target', query.writeTarget);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const response = await apiRequest<ListResponse<ResultWriteRecord>>(`/api/system/result-write-records${suffix}`, { token });
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

export async function copyPlugin(pluginId: string, payload: Partial<PluginRecord>) {
  const token = requireAccessToken();
  return apiRequest<PluginRecord>(`/api/system/plugins/${pluginId}/copy`, {
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
  query: { environment?: string; pluginId?: string; status?: string } = {},
): Promise<PluginConnectionRecord[]> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'environment', query.environment);
  appendQueryParam(params, 'plugin_id', query.pluginId);
  appendQueryParam(params, 'status', query.status);
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<PluginConnectionRecord>>(
    queryString ? `/api/system/plugin-connections?${queryString}` : '/api/system/plugin-connections',
    { token },
  );
  return response.items;
}

export async function fetchPluginConnectionsPage(
  query: PluginConnectionListQuery,
): Promise<RemoteListResult<PluginConnectionRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'environment', query.environment);
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'plugin_id', query.pluginId);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const response = await apiRequest<ListResponse<PluginConnectionRecord>>(
    `/api/system/plugin-connections?${params.toString()}`,
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

export async function fetchPluginActionsPage(
  query: PluginActionListQuery,
): Promise<RemoteListResult<PluginActionRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'plugin_id', query.pluginId);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const response = await apiRequest<ListResponse<PluginActionRecord>>(
    `/api/system/plugin-actions?${params.toString()}`,
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

export async function fetchAiSkills(): Promise<AiSkillRecord[]>;
export async function fetchAiSkills(
  query: AiSkillListQuery,
): Promise<RemoteListResult<AiSkillRecord>>;
export async function fetchAiSkills(
  query?: AiSkillListQuery,
): Promise<AiSkillRecord[] | RemoteListResult<AiSkillRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  if (query) {
    appendQueryParam(params, 'code', query.code);
    appendQueryParam(params, 'keyword', query.keyword);
    appendQueryParam(params, 'requires_human_review', query.requiresHumanReview);
    appendQueryParam(params, 'risk_level', query.riskLevel);
    appendQueryParam(params, 'source_type', query.sourceType);
    appendQueryParam(params, 'status', query.status);
    appendRemoteListParams(params, query);
  }
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<AiSkillRecord>>(
    queryString ? `/api/system/ai-skills?${queryString}` : '/api/system/ai-skills',
    {
      token,
    },
  );
  if (query) {
    return {
      page: response.page ?? query.page ?? 1,
      pageSize: response.page_size ?? query.pageSize ?? 10,
      performance: response.performance,
      rows: response.items,
      total: response.total,
    };
  }
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

export async function fetchAiAgents(): Promise<AiAgentRecord[]>;
export async function fetchAiAgents(
  query: AiAgentListQuery,
): Promise<RemoteListResult<AiAgentRecord>>;
export async function fetchAiAgents(
  query?: AiAgentListQuery,
): Promise<AiAgentRecord[] | RemoteListResult<AiAgentRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  if (query) {
    appendQueryParam(params, 'brain_app_id', query.brainAppId);
    appendQueryParam(params, 'keyword', query.keyword);
    appendQueryParam(params, 'model_gateway_config_id', query.modelGatewayConfigId);
    appendQueryParam(params, 'status', query.status);
    appendRemoteListParams(params, query);
  }
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<AiAgentRecord>>(
    queryString ? `/api/system/ai-agents?${queryString}` : '/api/system/ai-agents',
    {
      token,
    },
  );
  if (query) {
    return {
      page: response.page ?? query.page ?? 1,
      pageSize: response.page_size ?? query.pageSize ?? 10,
      performance: response.performance,
      rows: response.items,
      total: response.total,
    };
  }
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

export async function fetchScheduledJobs(): Promise<ScheduledJobRecord[]>;
export async function fetchScheduledJobs(
  query: ScheduledJobListQuery,
): Promise<RemoteListResult<ScheduledJobRecord>>;
export async function fetchScheduledJobs(
  query?: ScheduledJobListQuery,
): Promise<ScheduledJobRecord[] | RemoteListResult<ScheduledJobRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  if (query) {
    appendQueryParam(params, 'enabled', query.enabled);
    appendQueryParam(params, 'job_type', query.jobType);
    appendQueryParam(params, 'keyword', query.keyword);
    appendQueryParam(params, 'name', query.name);
    appendQueryParam(params, 'product_id', query.productId);
    appendQueryParam(params, 'source_system', query.sourceSystem);
    appendQueryParam(params, 'status', query.status);
    appendRemoteListParams(params, query);
  }
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<ScheduledJobRecord>>(
    queryString ? `/api/system/scheduled-jobs?${queryString}` : '/api/system/scheduled-jobs',
    {
      token,
    },
  );
  if (query) {
    return {
      page: response.page ?? query.page ?? 1,
      pageSize: response.page_size ?? query.pageSize ?? 10,
      performance: response.performance,
      rows: response.items,
      total: response.total,
    };
  }
  return response.items;
}

export async function fetchScheduledJobTemplates(): Promise<ScheduledJobTemplateRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<ListResponse<ScheduledJobTemplateRecord>>(
    '/api/system/scheduled-job-templates',
    { token },
  );
  return response.items;
}

export async function fetchScheduledJobCatalog(): Promise<ScheduledJobCatalogRecord> {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobCatalogRecord>('/api/system/scheduled-job-catalog', { token });
}

export async function generateScheduledJobTemplateFromRun(runId: string): Promise<ScheduledJobTemplateRecord> {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobTemplateRecord>(`/api/system/scheduled-job-runs/${runId}/template`, {
    method: 'POST',
    token,
  });
}

export async function createScheduledJob(payload: Partial<ScheduledJobRecord>) {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobRecord>('/api/system/scheduled-jobs', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function dryRunScheduledJob(payload: Partial<ScheduledJobRecord>) {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobDryRunResult>('/api/system/scheduled-jobs/dry-run', {
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

export async function runScheduledJob(
  jobId: string,
  triggerType: 'manual' | 'manual_rerun' = 'manual',
  sourceRunId?: string,
) {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobRunRecord>(`/api/system/scheduled-jobs/${jobId}/run`, {
    body: { source_run_id: sourceRunId, trigger_type: triggerType },
    method: 'POST',
    token,
  });
}

export async function fetchScheduledJobRuns(): Promise<ScheduledJobRunRecord[]>;
export async function fetchScheduledJobRuns(
  query: ScheduledJobRunListQuery,
): Promise<RemoteListResult<ScheduledJobRunRecord>>;
export async function fetchScheduledJobRuns(
  query: ScheduledJobRunFilterQuery,
): Promise<ScheduledJobRunRecord[]>;
export async function fetchScheduledJobRuns(
  query: ScheduledJobRunFilterQuery | ScheduledJobRunListQuery = {},
): Promise<ScheduledJobRunRecord[] | RemoteListResult<ScheduledJobRunRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  query.runIds?.forEach((runId) => {
    if (runId) {
      params.append('run_id', runId);
    }
  });
  appendQueryParam(params, 'scheduled_job_id', query.scheduledJobId);
  appendQueryParam(params, 'status', query.status);
  const remoteListRequested =
    query.page !== undefined
    || query.pageSize !== undefined
    || query.sortField !== undefined
    || query.sortOrder !== undefined;
  if (remoteListRequested) {
    appendRemoteListParams(params, query);
  }
  const queryString = params.toString();
  const response = await apiRequest<ListResponse<ScheduledJobRunRecord>>(
    queryString ? `/api/system/scheduled-job-runs?${queryString}` : '/api/system/scheduled-job-runs',
    { token },
  );
  if (remoteListRequested) {
    return {
      page: response.page ?? query.page ?? 1,
      pageSize: response.page_size ?? query.pageSize ?? 10,
      performance: response.performance,
      rows: response.items,
      total: response.total,
    };
  }
  return response.items;
}

export async function fetchScheduledJobRunObservability(): Promise<ScheduledJobRunObservability> {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobRunObservability>('/api/system/scheduled-job-runs/observability', {
    token,
  });
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
    performance: events.performance,
    rows: events.items.map(mapAuditRecord),
    total: events.total,
  };
}

export async function fetchExecutionTraces(
  query: ExecutionTraceListQuery = {},
): Promise<RemoteListResult<ExecutionTraceListItem>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'created_from', query.createdFrom);
  appendQueryParam(params, 'created_to', query.createdTo);
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'refresh', query.refresh);
  appendQueryParam(params, 'source_id', query.sourceId);
  appendQueryParam(params, 'source_type', query.sourceType);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const traces = await apiRequest<ListResponse<ExecutionTraceListItem>>(
    queryString
      ? `/api/governance/execution-traces?${queryString}`
      : '/api/governance/execution-traces',
    { token },
  );

  return {
    page: traces.page ?? query.page ?? 1,
    pageSize: traces.page_size ?? query.pageSize ?? 10,
    performance: traces.performance,
    rows: traces.items,
    total: traces.total,
  };
}

export async function fetchExecutionTraceDetail(traceId: string): Promise<ExecutionTraceDetailRecord> {
  const token = requireAccessToken();
  return apiRequest<ExecutionTraceDetailRecord>(`/api/governance/execution-traces/${traceId}`, {
    token,
  });
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

function codeReviewTitleFromTechnicalSolutionTask(task: TaskCenterTaskRecord, mrIid: number) {
  const title = task.label.replace(/^技术方案[:：]\s*/, '').trim();
  return `Code Review：${title || task.label} MR !${mrIid}`;
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
    performance: metrics.performance,
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
