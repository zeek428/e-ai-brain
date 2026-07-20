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
} from './apiClient';
import { requireAccessToken } from './authClient';

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
  runtime_capabilities?: {
    prompt_execution?: string;
    schema_validation?: string;
    script_execution?: string;
    script_files?: string[];
    script_note?: string;
  };
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
  description?: string | null;
  execution_policy?: Record<string, unknown>;
  id: string;
  manifest?: Record<string, unknown>;
  model_gateway_config?: Record<string, unknown> | null;
  model_gateway_config_id?: string | Record<string, unknown> | null;
  model_gateway_config_snapshot?: Record<string, unknown> | null;
  name: string;
  package_checksum?: string | null;
  package_entry?: string | null;
  package_files?: string[];
  package_size_bytes?: number;
  package_uri?: string | null;
  resolved_model_gateway_config?: Record<string, unknown> | null;
  runtime_capabilities?: {
    default_skill_binding?: string;
    package_context?: string;
    script_execution?: string;
    script_files?: string[];
    script_note?: string;
    system_prompt_execution?: string;
  };
  source_type?: string;
  status: string;
  system_prompt?: string;
  tool_policy?: Record<string, unknown>;
};

export type AiAgentPackageUploadOptions = {
  brainAppId?: string;
  code: string;
  defaultSkillIds?: string[];
  modelGatewayConfigId?: string;
  name: string;
  status?: string;
  version?: string;
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
  last_failure_at?: string | null;
  last_run_at?: string | null;
  last_success_at?: string | null;
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
  content_template?: string;
  document_id?: string;
  max_items?: number;
  plugin_action_id?: string;
  plugin_connection_id?: string;
  priority?: string;
  recipients?: string[];
  requirements_path?: string;
  severity_threshold?: string;
  source?: string;
  type: string;
  webhook_url?: string;
  write_mode?: string;
};

export type ScheduledJobCatalogOption = {
  label: string;
  value: string;
};

export type ScheduledJobCatalogJobType = ScheduledJobCatalogOption & {
  allow_create?: boolean;
  category?: string;
  default_execution_mode?: string;
  requires_ai_assembly?: boolean;
  requires_plugin_resource?: boolean;
  requires_product?: boolean;
  runnable?: boolean;
  unavailable_reason?: string;
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
  generic_result_actions?: ScheduledJobCatalogOption[];
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
  secret?: boolean;
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
  sample_reuse?: Record<string, unknown>;
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
  scheduled_job_name?: string | null;
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

export type ScheduledJobTraceNodeRerunControl = {
  key?: string;
  label?: string;
  reason?: string;
  required?: boolean;
  satisfied?: boolean;
  status?: string;
};

export type ScheduledJobTraceNodeRerunControlSummary = {
  blocked_count?: number;
  missing_count?: number;
  needs_review_count?: number;
  satisfied_count?: number;
  status_counts?: Record<string, number>;
  total?: number;
};

export type ScheduledJobTraceNodeRerunNextAction = {
  description?: string;
  key?: string;
  label?: string;
  missing_controls?: string[];
  request?: Record<string, unknown>;
  side_effect_policy?: string;
  status?: string;
};

export type ScheduledJobTraceNodeRerunPreview = {
  blocked_by?: string[];
  can_preview_from_snapshot?: boolean;
  control_summary?: ScheduledJobTraceNodeRerunControlSummary;
  debug_actions?: Array<Record<string, unknown>>;
  execution_policy?: Record<string, unknown>;
  full_run_request?: Record<string, unknown>;
  missing_controls?: string[];
  next_actions?: ScheduledJobTraceNodeRerunNextAction[];
  node_id?: string;
  preflight_status?: string;
  rerun_plan?: Record<string, unknown>;
  rerun_controls?: ScheduledJobTraceNodeRerunControl[];
  rerun_supported?: boolean;
  run_id?: string;
  safe_next_action?: string;
  side_effect_policy?: string;
  snapshot_preview?: Record<string, unknown>;
  snapshot_status?: Record<string, unknown>;
  stage?: string;
  stage_label?: string;
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
  authorization_guide?: {
    credential_reuse?: {
      description?: string;
      example_refs?: string[];
      supports_vault_ref?: boolean;
    };
    subjects?: Array<{
      label?: string;
      scenario?: string;
      type?: string;
    }>;
    url_key?: {
      description?: string;
      query_key?: string;
      steps?: string[];
      title?: string;
    };
  };
  business_scenario_templates?: Array<{
    code?: string;
    name?: string;
    steps?: string[];
  }>;
  capability_discovery?: {
    drift_policy?: Record<string, string>;
    jsonrpc_method?: string;
    known_tools?: string[];
    mode?: string;
  };
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
  governance_policy?: {
    allowed_roles?: string[];
    high_risk_controls?: string[];
    product_scope_required?: boolean;
  };
  observability?: {
    health_dashboard?: {
      enabled?: boolean;
      title?: string;
    };
    metrics?: string[];
  };
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
  secret?: boolean;
  supports_system_variables?: boolean;
  type?: string;
  visible_when_source_types?: string[];
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
  governance?: Record<string, unknown>;
  name: string;
  plugin_code: string;
  plugin_id?: string | null;
  request_config?: Record<string, unknown>;
  requires_human_review?: boolean;
  risk_tier?: string;
  result_mapping?: Record<string, unknown>;
  template_version?: string;
};

export type PluginConnectionToolDiscoveryResult = {
  checked_at?: string;
  connection_id: string;
  discovered_tools?: Array<{
    description?: string | null;
    input_schema?: Record<string, unknown>;
    name: string;
  }>;
  known_tools?: string[];
  latency_ms?: number;
  missing_tools?: string[];
  new_tools?: string[];
  plugin_id?: string;
  request_summary?: Record<string, unknown>;
  response_summary?: Record<string, unknown>;
  schema_changed_tools?: string[];
  status: string;
  suggestions?: Array<{
    detail?: string;
    tool_name?: string;
    type?: string;
  }>;
  tool_count?: number;
};

export type PluginObservabilityResult = {
  action_trend?: Array<{ action_code?: string; count?: number }>;
  connection_health?: Array<Record<string, unknown>>;
  failure_reason_distribution?: Array<{ count?: number; reason?: string }>;
  key_expiry_alerts?: Array<Record<string, unknown>>;
  provider: string;
  redacted_recent_replays?: Array<{
    request_preview?: Record<string, unknown>;
    status?: string;
    trace_id?: string;
  }>;
  summary?: {
    average_latency_ms?: number | null;
    failed_invocations?: number;
    latency_p95_ms?: number | null;
    success_rate?: number | null;
    succeeded_invocations?: number;
    total_invocations?: number;
  };
};

export type ResultWriteTargetFieldRecord = {
  description?: string;
  key: string;
  label: string;
  options?: Array<{ label: string; value: string }>;
  placeholder?: string;
  required?: boolean;
  type?: 'input' | 'select' | 'textarea';
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
  plugin_code?: string | null;
  plugin_id: string;
  plugin_name?: string | null;
  request_config?: Record<string, unknown>;
  schema_values?: Record<string, unknown>;
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
  scheduled_job_sample_seed?: Record<string, unknown>;
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
  scheduled_job_sample_seed?: Record<string, unknown>;
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
  capabilities?: string[];
  created_at?: string | null;
  endpoint_url?: string;
  executor_types?: string[];
  heartbeat_age_seconds?: number | null;
  heartbeat_timeout_seconds?: number;
  health_alert?: {
    action_label?: string;
    code?: string;
    heartbeat_age_seconds?: number | null;
    heartbeat_timeout_seconds?: number;
    message?: string;
    severity?: string;
  } | null;
  health_status?: string;
  id: string;
  latest_task_id?: string | null;
  latest_task_status?: string | null;
  last_heartbeat_at?: string | null;
  max_concurrent_tasks?: number;
  metadata?: Record<string, unknown>;
  name: string;
  protocol?: string;
  trust_domain?: 'coding' | 'deployment' | 'verification';
  queue_summary?: {
    available_slots?: number;
    cancelled?: number;
    claimed?: number;
    counts_by_status?: Record<string, number>;
    dead_letter?: number;
    failed?: number;
    failed_total?: number;
    latest_failure?: {
      error_code?: string | null;
      error_message?: string | null;
      finished_at?: string | null;
      id?: string | null;
      status?: string | null;
      updated_at?: string | null;
    };
    max_concurrent_tasks?: number;
    queued?: number;
    running?: number;
    running_total?: number;
    succeeded?: number;
    terminal_total?: number;
    timed_out?: number;
    total?: number;
  };
  readiness_summary?: {
    attention_count?: number;
    blocked_count?: number;
    controls?: Array<{
      key?: string;
      label?: string;
      reason?: string;
      required?: boolean;
      satisfied?: boolean;
      status?: string;
    }>;
    missing_count?: number;
    readiness_status?: string;
    satisfied_count?: number;
    status_counts?: Record<string, number>;
    total?: number;
  };
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

export type AiExecutorApprovalRequestRecord = {
  action_id?: string | null;
  ai_task_id?: string | null;
  approval?: Record<string, unknown>;
  approval_request?: Record<string, unknown>;
  approved_at?: string | null;
  approved_by?: string | null;
  blocked_operations?: string[];
  connection_id?: string | null;
  created_at?: string | null;
  executor_type?: string;
  expires_at?: string | null;
  id: string;
  reason?: string | null;
  requested_at?: string | null;
  requested_by?: string | null;
  risk_level?: string;
  runner_id?: string | null;
  scheduled_job_id?: string | null;
  scheduled_job_run_id?: string | null;
  status: string;
  updated_at?: string | null;
  workspace_root?: string;
};

export type AiExecutorApprovalRequestListQuery = RemoteListQuery & {
  actionId?: string;
  runnerId?: string;
  status?: string;
};

export type AiExecutorApprovalRequestApprovalResponse = {
  action?: PluginActionRecord | null;
  approval: Record<string, unknown>;
  approval_request: AiExecutorApprovalRequestRecord;
};

export type RdTaskExecutorPolicyRecord = {
  autonomy_mode?: string;
  auto_merge_risk_threshold?: string;
  branch?: string | null;
  code_change_review_mode?: string;
  cost_budget?: number | null;
  created_at?: string | null;
  created_by?: string | null;
  executor_type: string;
  id: string;
  instruction_template: string;
  name: string;
  max_duration_seconds?: number;
  max_iterations?: number;
  output_contract?: Record<string, unknown>;
  priority: number;
  product_id?: string | null;
  product_name?: string | null;
  repository_default_branch?: string | null;
  repository_id?: string | null;
  repository_name?: string | null;
  quality_gate_policy_id?: string | null;
  runner_id?: string | null;
  runner_name?: string | null;
  status: string;
  task_type: string;
  timeout_seconds: number;
  token_budget?: number | null;
  updated_at?: string | null;
  workspace_root: string;
};

export type RdTaskExecutorPolicyPayload = {
  autonomy_mode?: string;
  auto_merge_risk_threshold?: string;
  branch?: string | null;
  code_change_review_mode?: string;
  cost_budget?: number | null;
  executor_type?: string;
  instruction_template?: string;
  name?: string;
  max_duration_seconds?: number;
  max_iterations?: number;
  output_contract?: Record<string, unknown>;
  priority?: number;
  product_id?: string | null;
  repository_id?: string | null;
  quality_gate_policy_id?: string | null;
  runner_id?: string | null;
  status?: string;
  task_type?: string;
  timeout_seconds?: number;
  token_budget?: number | null;
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

export type AiExecutorTaskRetryResponse = {
  source_task: AiExecutorTaskRecord;
  task: AiExecutorTaskRecord;
};

export type AiExecutorTaskTimeoutScanNextAction = {
  description?: string;
  key: string;
  label: string;
  severity?: string;
  task_ids?: string[];
};

export type AiExecutorTaskTimeoutScanSummary = {
  dead_letter_count: number;
  manual_attention_required: boolean;
  message: string;
  requeued_count: number;
  scanned_at: string;
  status: string;
  timed_out_count: number;
  total_affected: number;
};

export type AiExecutorTaskTimeoutScanResponse = {
  dead_letter_task_ids: string[];
  next_actions: AiExecutorTaskTimeoutScanNextAction[];
  requeued_task_ids: string[];
  summary: AiExecutorTaskTimeoutScanSummary;
  timed_out_task_ids: string[];
  tasks: AiExecutorTaskRecord[];
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
  probe_tasks?: Array<{
    id: string;
    status: string;
    target_code: string;
  }>;
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
  error_detail?: Record<string, unknown> | null;
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
  sample_source?: string;
  scheduled_job_dry_run_seed?: Record<string, unknown>;
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

export async function fetchPluginObservability(
  provider = 'dingtalk',
): Promise<PluginObservabilityResult> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'provider', provider);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<PluginObservabilityResult>(`/api/system/plugin-observability${suffix}`, {
    token,
  });
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

export async function fetchAiExecutorApprovalRequestsPage(
  query: AiExecutorApprovalRequestListQuery = {},
): Promise<RemoteListResult<AiExecutorApprovalRequestRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'action_id', query.actionId);
  appendQueryParam(params, 'runner_id', query.runnerId);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const response = await apiRequest<ListResponse<AiExecutorApprovalRequestRecord>>(
    `/api/system/ai-executor-approval-requests?${params.toString()}`,
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

export async function approveAiExecutorApprovalRequest(
  approvalRequestId: string,
  payload: {
    approval_id?: string;
    approved_operations?: string[];
    expires_at?: string;
    reason?: string;
  } = {},
): Promise<AiExecutorApprovalRequestApprovalResponse> {
  const token = requireAccessToken();
  return apiRequest<AiExecutorApprovalRequestApprovalResponse>(
    `/api/system/ai-executor-approval-requests/${approvalRequestId}/approve`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
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

export async function retryAiExecutorTask(
  taskId: string,
  reason?: string,
): Promise<AiExecutorTaskRetryResponse> {
  const token = requireAccessToken();
  return apiRequest<AiExecutorTaskRetryResponse>(`/api/system/ai-executor-tasks/${taskId}/retry`, {
    body: { reason },
    method: 'POST',
    token,
  });
}

export async function timeoutAiExecutorTasks(
  payload: { now?: string | null } = {},
): Promise<AiExecutorTaskTimeoutScanResponse> {
  const token = requireAccessToken();
  return apiRequest<AiExecutorTaskTimeoutScanResponse>('/api/system/ai-executor-tasks/timeout-scan', {
    body: payload,
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

export async function discoverPluginConnectionTools(connectionId: string) {
  const token = requireAccessToken();
  return apiRequest<PluginConnectionToolDiscoveryResult>(
    `/api/system/plugin-connections/${connectionId}/discover-tools`,
    {
      method: 'POST',
      token,
    },
  );
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

export async function approvePluginActionAiExecutor(
  actionId: string,
  payload: {
    approval_id?: string;
    approval_request?: Record<string, unknown>;
    approved_operations?: string[];
    expires_at?: string;
    reason?: string;
  },
) {
  const token = requireAccessToken();
  return apiRequest<{ action: PluginActionRecord; approval: Record<string, unknown> }>(
    `/api/system/plugin-actions/${actionId}/ai-executor-approval`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
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
  payload: {
    connection_id?: string | null;
    input_payload?: Record<string, unknown>;
    sample_response_summary?: Record<string, unknown>;
  } = {},
) {
  const token = requireAccessToken();
  const body: Record<string, unknown> = {
    connection_id: payload.connection_id,
    input_payload: payload.input_payload ?? {},
  };
  if (payload.sample_response_summary) {
    body.sample_response_summary = payload.sample_response_summary;
  }
  return apiRequest<PluginActionTrialResult>(`/api/system/plugin-actions/${actionId}/trial`, {
    body,
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

export async function uploadAiAgentPackage(
  file: File,
  options: AiAgentPackageUploadOptions,
) {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'brain_app_id', options.brainAppId ?? 'rd_brain');
  appendQueryParam(params, 'code', options.code);
  appendQueryParam(params, 'name', options.name);
  appendQueryParam(params, 'version', options.version ?? '1.0.0');
  appendQueryParam(params, 'status', options.status ?? 'active');
  appendQueryParam(params, 'model_gateway_config_id', options.modelGatewayConfigId);
  for (const skillId of options.defaultSkillIds ?? []) {
    if (skillId) {
      params.append('default_skill_ids', skillId);
    }
  }
  const response = await fetch(`${API_BASE_URL}/api/system/ai-agents/upload?${params}`, {
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
  const payload = (await response.json()) as ApiEnvelope<AiAgentRecord>;
  return payload.data;
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

export async function fetchScheduledJobTraceNodeRerunPreview(
  runId: string,
  nodeId: string,
): Promise<ScheduledJobTraceNodeRerunPreview> {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobTraceNodeRerunPreview>(
    `/api/system/scheduled-job-runs/${encodeURIComponent(runId)}/trace-nodes/${encodeURIComponent(nodeId)}/rerun-preview`,
    { token },
  );
}

export async function rerunScheduledJobTraceNode(
  runId: string,
  nodeId: string,
): Promise<ScheduledJobRunRecord> {
  const token = requireAccessToken();
  return apiRequest<ScheduledJobRunRecord>(
    `/api/system/scheduled-job-runs/${encodeURIComponent(runId)}/trace-nodes/${encodeURIComponent(nodeId)}/rerun`,
    {
      method: 'POST',
      token,
    },
  );
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
    body: {
      return_immediately: true,
      source_run_id: sourceRunId,
      trigger_type: triggerType,
    },
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
