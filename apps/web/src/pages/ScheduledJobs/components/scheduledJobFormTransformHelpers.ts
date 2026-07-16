import {
  resolveAssistantDraftResourceId,
  type AssistantScheduledJobDraft,
  type PluginActionRecord,
  type ScheduledJobRecord,
  type ScheduledJobResultAction,
  type ScheduledJobTemplateRecord,
} from '../../../services/aiBrain';

export type ScheduledJobFormValues = {
  agent_id?: string;
  config_json?: Record<string, unknown>;
  cron_expression?: string;
  data_source_mode?: ScheduledJobDataSourceMode;
  enabled: boolean;
  execution_mode: string;
  interval_seconds?: number;
  job_type: string;
  knowledge_document_ids?: string[];
  model_gateway_config_id?: string;
  name: string;
  plugin_action_id?: string | null;
  plugin_action_ids?: string[];
  plugin_connection_id?: string | null;
  plugin_connection_ids?: string[];
  plugin_input_mapping?: Record<string, unknown>;
  plugin_output_mapping?: Record<string, unknown>;
  product_id?: string;
  result_actions?: ScheduledJobResultAction[];
  schedule_type: string;
  skill_ids?: string[];
  source_system: string;
  template?: string;
};

export type ScheduledJobDataSourceMode = 'authorized_read_action' | 'direct_connection';

export type DraftBackedScheduledJobFormValues = ScheduledJobFormValues & {
  plugin_input_mapping?: Record<string, unknown>;
  plugin_output_mapping?: Record<string, unknown>;
};

export type ScheduledJobTemplateSource = {
  sourceId: string;
  sourceType: 'scheduled_job' | 'scheduled_job_run';
  title: string;
  values: Partial<ScheduledJobFormValues>;
};

export type ScheduledJobPageTab = 'jobs' | 'runs';

export const assistantDraftTrackedFields = [
  'agent_id',
  'config_json',
  'cron_expression',
  'enabled',
  'execution_mode',
  'interval_seconds',
  'job_type',
  'knowledge_document_ids',
  'model_gateway_config_id',
  'name',
  'plugin_action_id',
  'plugin_action_ids',
  'plugin_connection_id',
  'plugin_connection_ids',
  'plugin_input_mapping',
  'plugin_output_mapping',
  'product_id',
  'result_actions',
  'schedule_type',
  'skill_ids',
  'source_system',
] as const;

const systemDefaultAiExecutorRunnerId = 'ai_executor_runner_system_default';

function isSystemDefaultAiExecutorConfig(value: unknown): boolean {
  const config = recordValue(value);
  if (!config) {
    return false;
  }
  const allowedKeys = new Set([
    'executor_type',
    'instruction_timeout_seconds',
    'runner_id',
    'runner_label',
    'workspace_root',
  ]);
  if (Object.keys(config).some((key) => !allowedKeys.has(key))) {
    return false;
  }
  const runnerId = recordStringValue(config, 'runner_id');
  if (runnerId && runnerId !== systemDefaultAiExecutorRunnerId) {
    return false;
  }
  const executorType = recordStringValue(config, 'executor_type');
  if (executorType && executorType !== 'model_gateway') {
    return false;
  }
  const runnerLabel = recordStringValue(config, 'runner_label');
  if (runnerLabel && runnerLabel !== '系统默认执行器') {
    return false;
  }
  const workspaceRoot = recordStringValue(config, 'workspace_root');
  if (workspaceRoot && workspaceRoot !== 'model-gateway://scheduled-job') {
    return false;
  }
  const timeout = config.instruction_timeout_seconds;
  if (
    timeout !== undefined
    && timeout !== null
    && timeout !== ''
    && Number(timeout) !== 1800
  ) {
    return false;
  }
  return true;
}

function comparableAssistantDraftFieldValue(field: string, value: unknown): unknown {
  if (field !== 'config_json') {
    return comparableDraftValue(value);
  }
  const configJson = recordValue(value);
  if (!configJson || !isSystemDefaultAiExecutorConfig(configJson.ai_executor)) {
    return comparableDraftValue(value);
  }
  const restConfig = { ...configJson };
  delete restConfig.ai_executor;
  return comparableDraftValue(restConfig);
}

export const creatableJobTypeOptions = [
  { label: '代码仓库巡检（质量 / 安全 / 规范）', value: 'code_repository_inspection' },
  { label: '用户反馈洞察抽取（取数 + AI 分析 + 写入）', value: 'user_feedback_insight_extract' },
  { label: '迭代规划建议生成', value: 'iteration_plan_suggestion_generate' },
  { label: '线上日志 AI 分析', value: 'online_log_ai_analysis' },
  { label: '插件执行调用', value: 'plugin_action_invoke' },
];

export const legacyJobTypeOptions = [
  { label: '用户使用指标采集', value: 'user_usage_metric_collect' },
  { label: '用户反馈采集（仅取数，不调用 AI）', value: 'user_feedback_collect' },
  { label: '线上日志指标采集', value: 'online_log_metric_collect' },
  { label: 'GitLab 每日代码指标采集', value: 'gitlab_daily_code_metric_collect' },
  { label: 'Jenkins 发布记录采集', value: 'jenkins_release_collect' },
  { label: '看板快照刷新', value: 'dashboard_snapshot_refresh' },
  { label: '生命周期上下文刷新', value: 'lifecycle_context_refresh' },
  { label: '待归属数据重试', value: 'pending_attribution_retry' },
];

export const jobTypeOptions = [...creatableJobTypeOptions, ...legacyJobTypeOptions];

export const jobTypeLabelByValue = new Map(jobTypeOptions.map((option) => [option.value, option.label]));

export const executionModeOptions = [
  { label: '不调用 AI', value: 'deterministic' },
  { label: 'AI 辅助', value: 'ai_assisted' },
  { label: 'AI 生成', value: 'ai_generated' },
];

export const executionModeLabelByValue = new Map(executionModeOptions.map((option) => [option.value, option.label]));

export const scheduleTypeOptions = [
  { label: '手动触发', value: 'manual' },
  { label: 'Cron 定时', value: 'cron' },
  { label: '固定间隔', value: 'interval' },
];

export const scheduleTypeLabelByValue = new Map(scheduleTypeOptions.map((option) => [option.value, option.label]));

export const dataSourceModeOptions = [
  { label: '直接取数连接', value: 'direct_connection' },
  { label: '授权连接 + 读取动作', value: 'authorized_read_action' },
];

export const productRequiredJobTypes = ['code_repository_inspection', 'user_feedback_insight_extract'];
export const pluginRequiredJobTypes = [
  'code_repository_inspection',
  'online_log_ai_analysis',
  'plugin_action_invoke',
  'user_feedback_insight_extract',
];
export const nativeCodeInspectionScanMode = 'native_full_scan';

export const codeInspectionScanModeOptions = [
  { label: '本地完整扫描（clone 仓库）', value: nativeCodeInspectionScanMode },
  { label: '同步已有告警', value: 'sync_existing_alerts' },
  { label: '触发平台扫描', value: 'trigger_platform_scan' },
];

export const codeInspectionScannerEngineOptions = [
  { label: '内置规则', value: 'builtin' },
  { label: 'gitleaks 密钥扫描', value: 'gitleaks' },
  { label: 'semgrep 代码安全/规范', value: 'semgrep' },
  { label: 'trivy 依赖/镜像风险', value: 'trivy' },
  { label: 'npm audit', value: 'npm' },
  { label: 'pip-audit', value: 'pip-audit' },
  { label: 'mvn dependency-check', value: 'dependency-check' },
];

export const codeInspectionBuiltinRuleOptions = [
  { label: '硬编码凭据', value: 'secrets' },
  { label: '内部地址暴露', value: 'internal_addresses' },
];

export const codeInspectionIgnoreRuleOptions = [
  { label: 'secrets.hardcoded_credential', value: 'secrets.hardcoded_credential' },
  { label: 'metadata.internal_address_exposure', value: 'metadata.internal_address_exposure' },
];

const codeInspectionPluginActionCodes = new Set([
  'scan_github_code_inspection',
  'scan_gitlab_code_inspection',
]);

export const aiProcessingRequiredJobTypes = [
  'iteration_plan_suggestion_generate',
  'online_log_ai_analysis',
  'user_feedback_insight_extract',
];

export const statusLabelByValue = new Map([
  ['active', '启用'],
  ['disabled', '停用'],
]);

export const runTriggerTypeLabelByValue = new Map([
  ['manual', '手动触发'],
  ['manual_rerun', '运行记录复跑'],
  ['scheduler', '调度触发'],
]);

export const codeInspectionResultActionOptions = [
  { label: '写入代码巡检报告', value: 'write_code_inspection_report' },
  { label: '严重问题自动创建 Bug', value: 'create_bug_for_severe_findings' },
  { label: '发送问题消息通知', value: 'send_notification' },
];

export const resultActionLabelByValue = new Map(
  [
    ...codeInspectionResultActionOptions,
    { label: '仅保存运行结果', value: 'save_scheduled_job_result' },
    { label: '写入内部业务数据 - 用户洞察', value: 'write_internal_user_insights' },
  ].map((option) => [option.value, option.label]),
);

export const severityThresholdOptions = [
  { label: 'critical', value: 'critical' },
  { label: 'high', value: 'high' },
  { label: 'medium', value: 'medium' },
];

export const defaultCodeInspectionResultActions: ScheduledJobResultAction[] = [
  { type: 'write_code_inspection_report' },
  { severity_threshold: 'critical', type: 'create_bug_for_severe_findings' },
  { channels: ['email'], recipients: [], type: 'send_notification' },
];

export function cloneResultActions(actions: ScheduledJobResultAction[]): ScheduledJobResultAction[] {
  return actions.map((action) => ({
    ...action,
    ...(action.channels ? { channels: [...action.channels] } : {}),
    ...(action.recipients ? { recipients: [...action.recipients] } : {}),
  }));
}

export function templatePayloadRecord(template: ScheduledJobTemplateRecord | undefined) {
  return (template?.payload_defaults ?? {}) as Record<string, unknown>;
}

export function templatePayloadString(template: ScheduledJobTemplateRecord | undefined, key: string) {
  const value = templatePayloadRecord(template)[key];
  return typeof value === 'string' && value ? value : undefined;
}

export function templatePayloadBoolean(
  template: ScheduledJobTemplateRecord | undefined,
  key: string,
  fallback: boolean,
) {
  const value = templatePayloadRecord(template)[key];
  return typeof value === 'boolean' ? value : fallback;
}

export function templatePayloadNumber(template: ScheduledJobTemplateRecord | undefined, key: string) {
  const value = templatePayloadRecord(template)[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

export function templatePayloadList(template: ScheduledJobTemplateRecord | undefined, key: string) {
  const value = templatePayloadRecord(template)[key];
  return Array.isArray(value) ? value.map(String).filter(Boolean) : undefined;
}

export function templatePayloadRecordValue(template: ScheduledJobTemplateRecord | undefined, key: string) {
  const value = templatePayloadRecord(template)[key];
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

export function templatePayloadResultActions(template: ScheduledJobTemplateRecord | undefined) {
  const value = templatePayloadRecord(template).result_actions;
  return Array.isArray(value) ? cloneResultActions(value as ScheduledJobResultAction[]) : undefined;
}

export function templateSelector(template: ScheduledJobTemplateRecord | undefined, key: string) {
  const selectors = template?.resource_selectors;
  const value = selectors?.[key];
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

export function stringArrayFromUnknown(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

export function isCodeInspectionPluginAction(action: PluginActionRecord | undefined): action is PluginActionRecord {
  return Boolean(action && codeInspectionPluginActionCodes.has(action.code));
}

export function uniqueStringList(values: Array<string | null | undefined>): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const value of values) {
    if (!value || seen.has(value)) {
      continue;
    }
    seen.add(value);
    result.push(value);
  }
  return result;
}

export function primaryId(ids: string[] | undefined): string | undefined {
  return ids?.[0];
}

export function orchestrationConfigValue(configJson: unknown): Record<string, unknown> {
  if (!configJson || typeof configJson !== 'object' || Array.isArray(configJson)) {
    return {};
  }
  const value = (configJson as Record<string, unknown>).orchestration;
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function multiIdsFromRecord(
  record: Record<string, unknown> | undefined,
  pluralKey: 'plugin_action_ids' | 'plugin_connection_ids',
  singularKey: 'plugin_action_id' | 'plugin_connection_id',
  fallback?: Partial<ScheduledJobRecord>,
): string[] {
  const directIds = stringArrayFromUnknown(record?.[pluralKey]);
  const configIds = stringArrayFromUnknown(orchestrationConfigValue(record?.config_json)[pluralKey]);
  const fallbackIds = stringArrayFromUnknown(fallback?.[pluralKey]);
  return uniqueStringList([
    ...directIds,
    ...configIds,
    recordStringValue(record, singularKey),
    ...fallbackIds,
    fallback?.[singularKey] ? String(fallback[singularKey]) : undefined,
  ]);
}

export function multiIdsFromScheduledJob(
  job: Partial<ScheduledJobRecord> | undefined,
  pluralKey: 'plugin_action_ids' | 'plugin_connection_ids',
  singularKey: 'plugin_action_id' | 'plugin_connection_id',
): string[] {
  return multiIdsFromRecord(job as Record<string, unknown> | undefined, pluralKey, singularKey, job);
}

export function scheduledJobConfigWithOrchestration(
  configJson: Record<string, unknown>,
  pluginConnectionIds: string[],
  pluginActionIds: string[],
  extraOrchestration: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    ...configJson,
    orchestration: {
      ...orchestrationConfigValue(configJson),
      ...extraOrchestration,
      plugin_action_ids: pluginActionIds,
      plugin_connection_ids: pluginConnectionIds,
    },
  };
}

export function dataSourceModeFromConfig(configJson: unknown): ScheduledJobDataSourceMode {
  const orchestration = orchestrationConfigValue(configJson);
  const mode =
    recordStringValue(orchestration, 'data_source_mode')
    ?? recordStringValue(recordValue(configJson), 'data_source_mode');
  return mode === 'authorized_read_action' ? 'authorized_read_action' : 'direct_connection';
}

export function scheduledJobInputMappingForEdit(
  job: Partial<ScheduledJobRecord>,
): Record<string, unknown> {
  const inputMapping = recordValue(job.plugin_input_mapping) ?? {};
  const createsRequirements = (job.result_actions ?? []).some(
    (action) => action.type === 'create_requirements',
  );
  if (job.source_system !== 'internal_data_source' || !createsRequirements) {
    return inputMapping;
  }
  const sourceTypes = stringArrayFromUnknown(inputMapping.source_types);
  return {
    ...inputMapping,
    limit: recordNumberValue(inputMapping, 'limit') ?? 100,
    source_types: sourceTypes.length ? sourceTypes : ['user_insights'],
    window_end: recordStringValue(inputMapping, 'window_end') ?? '{{now}}',
    window_start: recordStringValue(inputMapping, 'window_start') ?? '{{current_date-30}}',
  };
}

export function hasRequiredFormValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  return value !== undefined && value !== null && value !== '';
}

export function codeInspectionUsesNativeScan(jobType: unknown, configJson: unknown): boolean {
  const config = recordValue(configJson) ?? {};
  return (
    String(jobType ?? '') === 'code_repository_inspection'
    && recordStringValue(config, 'scan_mode') === nativeCodeInspectionScanMode
  );
}

export function requiresAiAssembly(
  jobType: unknown,
  executionMode: unknown,
  requiredJobTypes: string[] = aiProcessingRequiredJobTypes,
): boolean {
  return (
    requiredJobTypes.includes(String(jobType ?? ''))
    || ['ai_assisted', 'ai_generated'].includes(String(executionMode ?? ''))
  );
}

function stringFromDraftPayload(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === 'string' && value ? value : undefined;
}

function booleanFromDraftPayload(payload: Record<string, unknown>, key: string, fallback: boolean) {
  const value = payload[key];
  return typeof value === 'boolean' ? value : fallback;
}

function numberFromDraftPayload(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function stringListFromDraftPayload(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

export function recordFromDraftPayload(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function resultActionsFromDraftPayload(payload: Record<string, unknown>) {
  const value = payload.result_actions;
  return Array.isArray(value) ? (value as ScheduledJobResultAction[]) : undefined;
}

export function scheduledJobValuesFromAssistantDraft(
  draft: AssistantScheduledJobDraft,
): DraftBackedScheduledJobFormValues {
  const payload = draft.payload;
  const jobType = stringFromDraftPayload(payload, 'job_type') ?? 'user_feedback_insight_extract';
  const resolvedPluginActionId =
    stringFromDraftPayload(payload, 'plugin_action_id')
    ?? resolveAssistantDraftResourceId(payload, 'plugin_action');
  const resolvedPluginConnectionId =
    stringFromDraftPayload(payload, 'plugin_connection_id')
    ?? resolveAssistantDraftResourceId(payload, 'plugin_connection');
  const resolvedAgentId =
    stringFromDraftPayload(payload, 'agent_id')
    ?? resolveAssistantDraftResourceId(payload, 'ai_agent');
  const resolvedSkillId = resolveAssistantDraftResourceId(payload, 'ai_skill');
  const pluginActionIds = uniqueStringList([
    ...stringListFromDraftPayload(payload, 'plugin_action_ids'),
    resolvedPluginActionId,
  ]);
  const pluginConnectionIds = uniqueStringList([
    ...stringListFromDraftPayload(payload, 'plugin_connection_ids'),
    resolvedPluginConnectionId,
  ]);
  const skillIds = uniqueStringList([
    ...stringListFromDraftPayload(payload, 'skill_ids'),
    resolvedSkillId,
  ]);
  return {
    agent_id: resolvedAgentId,
    config_json: recordFromDraftPayload(payload, 'config_json'),
    cron_expression: stringFromDraftPayload(payload, 'cron_expression'),
    data_source_mode: dataSourceModeFromConfig(recordFromDraftPayload(payload, 'config_json')),
    enabled: booleanFromDraftPayload(payload, 'enabled', true),
    execution_mode:
      stringFromDraftPayload(payload, 'execution_mode')
      ?? (jobType === 'code_repository_inspection' ? 'deterministic' : 'ai_generated'),
    interval_seconds: numberFromDraftPayload(payload, 'interval_seconds'),
    job_type: jobType,
    knowledge_document_ids: stringListFromDraftPayload(payload, 'knowledge_document_ids'),
    model_gateway_config_id: stringFromDraftPayload(payload, 'model_gateway_config_id'),
    name: stringFromDraftPayload(payload, 'name') ?? draft.title ?? 'AI 助手生成定时作业草案',
    plugin_action_id: primaryId(pluginActionIds),
    plugin_action_ids: pluginActionIds,
    plugin_connection_id: primaryId(pluginConnectionIds),
    plugin_connection_ids: pluginConnectionIds,
    plugin_input_mapping: recordFromDraftPayload(payload, 'plugin_input_mapping'),
    plugin_output_mapping: recordFromDraftPayload(payload, 'plugin_output_mapping'),
    product_id: stringFromDraftPayload(payload, 'product_id'),
    result_actions: resultActionsFromDraftPayload(payload),
    schedule_type: stringFromDraftPayload(payload, 'schedule_type') ?? 'manual',
    skill_ids: skillIds,
    source_system: stringFromDraftPayload(payload, 'source_system') ?? 'ai-brain',
    template: undefined,
  };
}

function comparableDraftValue(value: unknown): unknown {
  if (value === undefined || value === null || value === '') {
    return null;
  }
  if (Array.isArray(value)) {
    return value.map(comparableDraftValue);
  }
  if (typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, comparableDraftValue(item)]),
    );
  }
  return value;
}

export function scheduledJobAssistantDraftModifiedFields(
  initialPayload: Partial<ScheduledJobRecord>,
  currentPayload: Partial<ScheduledJobRecord>,
): string[] {
  const initialRecord = initialPayload as Record<string, unknown>;
  const currentRecord = currentPayload as Record<string, unknown>;
  return assistantDraftTrackedFields.filter((field) => (
    JSON.stringify(comparableAssistantDraftFieldValue(field, initialRecord[field]))
    !== JSON.stringify(comparableAssistantDraftFieldValue(field, currentRecord[field]))
  ));
}

export function scheduledJobRunIdFromAssistantResult(result?: Record<string, unknown>) {
  const run = result?.scheduled_job_run;
  if (!run || typeof run !== 'object') {
    return undefined;
  }
  const runId = (run as { id?: unknown }).id;
  return typeof runId === 'string' && runId ? runId : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function snapshotStringValue(snapshot: Record<string, unknown> | undefined, key: string): string | undefined {
  const value = snapshot?.[key];
  return typeof value === 'string' && value ? value : undefined;
}

export function snapshotStringListValue(snapshot: Record<string, unknown> | undefined, key: string): string[] {
  const value = snapshot?.[key];
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

export function recordValue(value: unknown): Record<string, unknown> | undefined {
  return isRecord(value) ? value : undefined;
}

export function recordStringValue(record: Record<string, unknown> | undefined, key: string): string | undefined {
  const value = record?.[key];
  return typeof value === 'string' && value ? value : undefined;
}

function recordNumberValue(record: Record<string, unknown> | undefined, key: string): number | undefined {
  const value = record?.[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function recordBooleanValue(
  record: Record<string, unknown> | undefined,
  key: string,
  fallback: boolean,
): boolean {
  const value = record?.[key];
  return typeof value === 'boolean' ? value : fallback;
}

export function scheduledJobTemplateValuesFromRecord(
  record: Record<string, unknown>,
  {
    fallback,
    nameSuffix = '副本',
  }: {
    fallback?: Partial<ScheduledJobRecord>;
    nameSuffix?: string;
  },
): Partial<ScheduledJobFormValues> {
  const pluginConnectionIds = multiIdsFromRecord(
    record,
    'plugin_connection_ids',
    'plugin_connection_id',
    fallback,
  );
  const pluginActionIds = multiIdsFromRecord(record, 'plugin_action_ids', 'plugin_action_id', fallback);
  const pluginConnectionId = primaryId(pluginConnectionIds);
  const name = recordStringValue(record, 'name') ?? fallback?.name ?? '定时作业';
  const resultActions = Array.isArray(record.result_actions)
    ? (record.result_actions as ScheduledJobResultAction[])
    : fallback?.result_actions;
  const knowledgeDocumentIds = snapshotStringListValue(record, 'knowledge_document_ids');
  const skillIds = snapshotStringListValue(record, 'skill_ids');
  return {
    agent_id: recordStringValue(record, 'agent_id') ?? fallback?.agent_id ?? undefined,
    config_json: recordValue(record.config_json) ?? fallback?.config_json ?? {},
    cron_expression: recordStringValue(record, 'cron_expression') ?? fallback?.cron_expression ?? undefined,
    data_source_mode: dataSourceModeFromConfig(record.config_json ?? fallback?.config_json),
    enabled: recordBooleanValue(record, 'enabled', fallback?.enabled ?? true),
    execution_mode: recordStringValue(record, 'execution_mode') ?? fallback?.execution_mode ?? 'deterministic',
    interval_seconds: recordNumberValue(record, 'interval_seconds') ?? fallback?.interval_seconds ?? undefined,
    job_type: recordStringValue(record, 'job_type') ?? fallback?.job_type ?? 'plugin_action_invoke',
    knowledge_document_ids: knowledgeDocumentIds.length ? knowledgeDocumentIds : fallback?.knowledge_document_ids ?? [],
    model_gateway_config_id:
      recordStringValue(record, 'model_gateway_config_id')
      ?? fallback?.model_gateway_config_id
      ?? undefined,
    name: nameSuffix ? `${name} ${nameSuffix}` : name,
    plugin_action_id: primaryId(pluginActionIds),
    plugin_action_ids: pluginActionIds,
    plugin_connection_id: pluginConnectionId,
    plugin_connection_ids: pluginConnectionIds,
    plugin_input_mapping: recordValue(record.plugin_input_mapping) ?? fallback?.plugin_input_mapping ?? {},
    plugin_output_mapping: recordValue(record.plugin_output_mapping) ?? fallback?.plugin_output_mapping ?? {},
    product_id: recordStringValue(record, 'product_id') ?? fallback?.product_id ?? undefined,
    result_actions: resultActions?.length ? cloneResultActions(resultActions) : undefined,
    schedule_type: recordStringValue(record, 'schedule_type') ?? fallback?.schedule_type ?? 'manual',
    skill_ids: skillIds.length ? skillIds : fallback?.skill_ids ?? [],
    source_system: recordStringValue(record, 'source_system') ?? fallback?.source_system ?? 'ai-brain',
    template: undefined,
  };
}

export function scheduledJobRouteParams(): {
  resultWriteRecordId?: string;
  runId?: string;
  tab?: ScheduledJobPageTab;
} {
  if (typeof window === 'undefined') {
    return { runId: undefined, tab: undefined };
  }
  const params = new URLSearchParams(window.location.search);
  const tab = params.get('tab') === 'runs' ? 'runs' : params.get('tab') === 'jobs' ? 'jobs' : undefined;
  return {
    resultWriteRecordId: params.get('result_write_record_id') ?? undefined,
    runId: params.get('run_id') ?? undefined,
    tab,
  };
}

export function initialScheduledJobPageTab(): ScheduledJobPageTab {
  return scheduledJobRouteParams().tab ?? 'jobs';
}
