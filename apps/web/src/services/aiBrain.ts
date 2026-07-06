import type {
  ProductGitRepositoryRecord,
  ProductModuleRecord,
  ProductRecord,
  ProductRelatedSystemRecord,
  ProductVersionBranchConfigRecord,
  ProductVersionRecord,
} from '../data/management';
import { formatDisplayDateTime } from '../utils/dateTime';
import {
  ApiRequestError,
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
} from './apiClient';
import type {
  ListResponse,
  RemoteListPerformance,
  RemoteListQueryEcho,
} from './apiClient';
import {
  requireAccessToken,
} from './authClient';
import type { AssistantActionDraftPreview } from './assistantDraftClient';
import {
  type TaskCenterTaskRecord,
} from './taskCenterClient';

export { ApiRequestError, apiRequest };
export type { RemoteListPerformance, RemoteListQueryEcho };
export {
  AUTH_STATE_EVENT,
  buildDingTalkStartUrl,
  clearAccessToken,
  exchangeDingTalkTicket,
  fetchAuthProfile,
  fetchAuthProviders,
  fetchLoginChallenge,
  fetchCurrentUser,
  getAccessToken,
  getStoredCurrentUser,
  login,
  logout,
  saveAccessToken,
  saveCurrentUser,
  startDingTalkBind,
  unbindDingTalkAccount,
  updateAuthProfile,
} from './authClient';
export type {
  AuthProfileResponse,
  AuthProfileUpdatePayload,
  AuthProfileUpdateResponse,
  AuthProviderConfig,
  AuthProvidersResponse,
  CurrentUserResponse,
  DingTalkBindingSummary,
  DingTalkBindStartResponse,
  LoginChallengeAnswer,
  LoginChallengeResponse,
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
  fetchManagementBugImagePreview,
  fetchManagementBugList,
  fetchManagementBugs,
  uploadManagementBugImage,
  updateManagementBug,
} from './bugClient';
export type {
  BugBatchUpdatePayload,
  BugBatchUpdateResult,
  BugImageEvidenceItem,
  BugImageUploadPayload,
  BugImageUploadSource,
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
  askKnowledgeRag,
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
  uploadKnowledgeDocumentFile,
} from './knowledgeClient';
export type {
  KnowledgeAssetRecord,
  KnowledgeChunkRecord,
  KnowledgeChunkSetRecord,
  KnowledgeDepositApprovePayload,
  KnowledgeDepositListItem,
  KnowledgeDepositRecord,
  KnowledgeDocumentListItem,
  KnowledgeDocumentFileUploadPayload,
  KnowledgeDocumentMutationPayload,
  KnowledgeDocumentUploadPayload,
  KnowledgeFolderRecord,
  KnowledgeImportJobRecord,
  KnowledgeImportWorkerStatusRecord,
  KnowledgeIndexHealthIssueRecord,
  KnowledgeIndexHealthRecord,
  KnowledgeListQuery,
  KnowledgeRagAnswerRecord,
  KnowledgeRagCitationRecord,
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
export {
  fetchExecutionTraceDetail,
  fetchExecutionTraces,
  fetchLifecycleContext,
  fetchManagementAudit,
  fetchManagementAuditList,
} from './diagnosticsClient';
export type {
  AuditListQuery,
  ExecutionTraceDetailRecord,
  ExecutionTraceEdgeRecord,
  ExecutionTraceListItem,
  ExecutionTraceListQuery,
  ExecutionTraceNodeRecord,
  LifecycleContextRecord,
  LifecycleRelationRecord,
  LifecycleRiskSignalRecord,
} from './diagnosticsClient';
export {
  convertUserFeedbackToRequirement,
  createIterationSuggestions,
  createUserFeedback,
  createUserUsageMetric,
  decideIterationSuggestion,
  fetchUserInsightList,
  fetchUserInsights,
  updateUserFeedback,
} from './userInsightsClient';
export type {
  IterationSuggestionCreatePayload,
  IterationSuggestionDecisionPayload,
  UserFeedbackConvertRequirementPayload,
  UserFeedbackCreatePayload,
  UserFeedbackPatchPayload,
  UserInsightListQuery,
  UserInsightRecord,
  UserUsageMetricCreatePayload,
} from './userInsightsClient';
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
  DashboardTrend,
  DashboardTrendPoint,
  DashboardTrendSeries,
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
export {
  copySystemRole,
  createManagementUser,
  createSystemMenu,
  createSystemRole,
  deleteManagementUser,
  deleteSystemMenu,
  fetchManagementUserList,
  fetchManagementUsers,
  fetchRoleDefinitionList,
  fetchRoleDefinitions,
  fetchSystemMenuList,
  fetchSystemMenus,
  fetchSystemPermissionDiagnostics,
  fetchSystemPermissionMatrix,
  fetchSystemPermissions,
  fetchSystemRoleList,
  fetchSystemSettings,
  reorderSystemMenus,
  setSystemMenuStatus,
  setSystemRoleStatus,
  testSystemEmailDelivery,
  unbindSystemExternalIdentity,
  updateManagementUser,
  updateSystemMenu,
  updateSystemRole,
  updateSystemRoleMenus,
  updateSystemRolePermissions,
  updateSystemRoleScopes,
  updateSystemSettings,
} from './systemManagementClient';
export type {
  MenuListQuery,
  MenuResourceMutationPayload,
  MenuResourceRecord,
  PermissionRecord,
  RbacPolicyMatrix,
  RbacPolicyMatrixRow,
  RoleListQuery,
  SystemEmailDeliverySettings,
  SystemEmailDeliveryTestPayload,
  SystemEmailDeliveryTestResult,
  SystemRoleRecord,
  SystemSettingsMutationPayload,
  SystemSettingsRecord,
  UserListQuery,
  UserMutationPayload,
  UserPermissionDiagnostic,
  UserPermissionDiagnosticCheck,
} from './systemManagementClient';

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

export type AssistantConversationDeleteResult = {
  actionRunCount: number;
  chatRunCount: number;
  conversationIds: string[];
  deleted: boolean;
  deletedConversationCount: number;
  draftCount: number;
  messageCount: number;
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

export type OperationalMetricListQuery = RemoteListQuery & {
  category?: string;
  name?: string;
  status?: string;
};

export type RemoteListResult<Row> = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: Row[];
  total: number;
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
  project_path?: string | null;
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

type AssistantConversationDeleteApiResponse = {
  action_run_count?: number;
  chat_run_count?: number;
  conversation_ids?: string[];
  deleted?: boolean;
  deleted_conversation_count?: number;
  draft_count?: number;
  message_count?: number;
};

export async function deleteAssistantConversation(
  conversationId: string,
  options: { conversationIds?: string[] } = {},
): Promise<AssistantConversationDeleteResult> {
  const token = requireAccessToken();
  const response = await apiRequest<AssistantConversationDeleteApiResponse>(
    `/api/assistant/conversations/${encodeURIComponent(conversationId)}`,
    {
      body: { conversation_ids: options.conversationIds ?? [conversationId] },
      method: 'DELETE',
      token,
    },
  );
  return {
    actionRunCount: Number(response.action_run_count ?? 0),
    chatRunCount: Number(response.chat_run_count ?? 0),
    conversationIds: response.conversation_ids ?? [conversationId],
    deleted: response.deleted === true,
    deletedConversationCount: Number(response.deleted_conversation_count ?? 0),
    draftCount: Number(response.draft_count ?? 0),
    messageCount: Number(response.message_count ?? 0),
  };
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

export async function fetchManagementProduct(productId: string): Promise<ProductRecord> {
  const token = requireAccessToken();
  const product = await apiRequest<ProductResponse>(`/api/products/${productId}`, { token });
  return mapProductRecord({
    code: product.code,
    id: product.id,
    name: product.name ?? product.id,
    owner_team: product.owner_team,
    status: product.status,
  });
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

export * from './systemOperationsClient';
export * from './devopsOperationsClient';
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
