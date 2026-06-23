import {
  CopyOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import {
  Button,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Tabs,
  Tag,
  Switch,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
  assistantScopedStorageKey,
  confirmAssistantActionDraft,
  createScheduledJob,
  deleteScheduledJob,
  dryRunScheduledJob,
  fetchActiveProductOptions,
  fetchAiAgents,
  fetchAiSkills,
  fetchManagementKnowledge,
  fetchModelGatewayConfigs,
  fetchPluginActions,
  fetchPluginConnections,
  fetchResultWriteRecords,
  fetchProductGitRepositories,
  fetchScheduledJobTemplates,
  fetchScheduledJobRunObservability,
  fetchScheduledJobRuns,
  fetchScheduledJobs,
  generateScheduledJobTemplateFromRun,
  rememberAssistantDraftResolution,
  resolveAssistantDraftResourceId,
  runScheduledJob,
  testPluginConnection,
  updateScheduledJob,
  updateAssistantActionDraft,
  type AiAgentRecord,
  type AiSkillRecord,
  type AssistantScheduledJobDraft,
  type PluginActionRecord,
  type PluginConnectionTestResult,
  type PluginConnectionRecord,
  type ProductFilterOption,
  type ProductGitRepositoryOption,
  type ResultWriteRecord,
  type ScheduledJobRecord,
  type ScheduledJobDryRunResult,
  type ScheduledJobResultAction,
  type ScheduledJobRunObservability,
  type ScheduledJobRunRecord,
  type ScheduledJobTemplateRecord,
} from '../../services/aiBrain';
import type { ModelGatewayConfigRecord } from '../../data/management';
import type { KnowledgeRecord } from '../../data/management';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { ScheduledJobActionConfigSection } from './components/ScheduledJobActionConfigSection';
import { ScheduledJobAiExecutionSection } from './components/ScheduledJobAiExecutionSection';
import { ScheduledJobDataConnectionSection } from './components/ScheduledJobDataConnectionSection';
import { ScheduledJobDryRunResultPanel } from './components/ScheduledJobDryRunResultPanel';
import { ScheduledJobFormSection as FormSection } from './components/ScheduledJobFormSection';
import {
  ScheduledJobJsonPreview as JsonPreview,
} from './components/ScheduledJobJsonPreview';
import { ScheduledJobRunResultWriteRecords } from './components/ScheduledJobRunResultWriteRecords';
import { ScheduledJobScheduleConfigSection } from './components/ScheduledJobScheduleConfigSection';
import {
  ScheduledJobOrchestrationFlow,
  type ScheduledJobOrchestrationNode,
} from './components/ScheduledJobOrchestrationFlow';
import {
  RunExecutionChain,
  RunSourceComparison,
  RunTraceDag,
  TemplateSourceSummary,
} from './components/ScheduledJobRunTraceDetails';
import { ScheduledJobRunObservabilityOverview } from './components/ScheduledJobRunObservabilityOverview';
import {
  getRunExecutionNode,
  templateSourceFromConfig,
} from './components/scheduledJobRunTraceHelpers';

type ScheduledJobFormValues = {
  agent_id?: string;
  connection_environment?: string;
  config_json?: Record<string, unknown>;
  cron_expression?: string;
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

type DraftBackedScheduledJobFormValues = ScheduledJobFormValues & {
  plugin_input_mapping?: Record<string, unknown>;
  plugin_output_mapping?: Record<string, unknown>;
};

type ScheduledJobTemplateSource = {
  sourceId: string;
  sourceType: 'scheduled_job' | 'scheduled_job_run';
  title: string;
  values: Partial<ScheduledJobFormValues>;
};

type ScheduledJobPageTab = 'jobs' | 'runs';

const assistantDraftTrackedFields = [
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

const jobTypeOptions = [
  { label: '代码仓库巡检（质量 / 安全 / 规范）', value: 'code_repository_inspection' },
  { label: '用户反馈洞察抽取（取数 + AI 分析 + 写入）', value: 'user_feedback_insight_extract' },
  { label: '迭代规划建议生成', value: 'iteration_plan_suggestion_generate' },
  { label: '线上日志 AI 分析', value: 'online_log_ai_analysis' },
  { label: '用户使用指标采集', value: 'user_usage_metric_collect' },
  { label: '用户反馈采集（仅取数，不调用 AI）', value: 'user_feedback_collect' },
  { label: '线上日志指标采集', value: 'online_log_metric_collect' },
  { label: 'GitLab 每日代码指标采集', value: 'gitlab_daily_code_metric_collect' },
  { label: 'Jenkins 发布记录采集', value: 'jenkins_release_collect' },
  { label: '插件执行调用', value: 'plugin_action_invoke' },
  { label: '看板快照刷新', value: 'dashboard_snapshot_refresh' },
  { label: '生命周期上下文刷新', value: 'lifecycle_context_refresh' },
  { label: '待归属数据重试', value: 'pending_attribution_retry' },
];

const jobTypeLabelByValue = new Map(jobTypeOptions.map((option) => [option.value, option.label]));

const executionModeOptions = [
  { label: '不调用 AI', value: 'deterministic' },
  { label: 'AI 辅助', value: 'ai_assisted' },
  { label: 'AI 生成', value: 'ai_generated' },
];

const executionModeLabelByValue = new Map(executionModeOptions.map((option) => [option.value, option.label]));

const scheduleTypeOptions = [
  { label: '手动触发', value: 'manual' },
  { label: 'Cron 定时', value: 'cron' },
  { label: '固定间隔', value: 'interval' },
];

const scheduleTypeLabelByValue = new Map(scheduleTypeOptions.map((option) => [option.value, option.label]));

const connectionEnvironmentOptions = [
  { label: '默认', value: 'default' },
  { label: '开发', value: 'dev' },
  { label: '测试', value: 'test' },
  { label: '预发', value: 'staging' },
  { label: '生产', value: 'prod' },
  { label: '沙箱', value: 'sandbox' },
];

const productRequiredJobTypes = ['code_repository_inspection', 'user_feedback_insight_extract'];
const pluginRequiredJobTypes = ['code_repository_inspection', 'plugin_action_invoke', 'user_feedback_insight_extract'];
const nativeCodeInspectionScanMode = 'native_full_scan';
const codeInspectionScanModeOptions = [
  { label: '本地完整扫描（clone 仓库）', value: nativeCodeInspectionScanMode },
  { label: '同步已有告警', value: 'sync_existing_alerts' },
  { label: '触发平台扫描', value: 'trigger_platform_scan' },
];
const codeInspectionScannerEngineOptions = [
  { label: '内置规则', value: 'builtin' },
  { label: 'gitleaks 密钥扫描', value: 'gitleaks' },
  { label: 'semgrep 代码安全/规范', value: 'semgrep' },
  { label: 'trivy 依赖/镜像风险', value: 'trivy' },
  { label: 'npm audit', value: 'npm' },
  { label: 'pip-audit', value: 'pip-audit' },
  { label: 'mvn dependency-check', value: 'dependency-check' },
];
const codeInspectionBuiltinRuleOptions = [
  { label: '硬编码凭据', value: 'secrets' },
  { label: '内部地址暴露', value: 'internal_addresses' },
];
const codeInspectionIgnoreRuleOptions = [
  { label: 'secrets.hardcoded_credential', value: 'secrets.hardcoded_credential' },
  { label: 'metadata.internal_address_exposure', value: 'metadata.internal_address_exposure' },
];
const codeInspectionPluginActionCodes = new Set([
  'scan_github_code_inspection',
  'scan_gitlab_code_inspection',
]);
const aiProcessingRequiredJobTypes = [
  'iteration_plan_suggestion_generate',
  'online_log_ai_analysis',
  'user_feedback_insight_extract',
];

const statusLabelByValue = new Map([
  ['active', '启用'],
  ['disabled', '停用'],
]);

const runTriggerTypeLabelByValue = new Map([
  ['manual', '手动触发'],
  ['manual_rerun', '运行记录复跑'],
  ['scheduler', '调度触发'],
]);

const codeInspectionResultActionOptions = [
  { label: '写入代码巡检报告', value: 'write_code_inspection_report' },
  { label: '严重问题自动创建 Bug', value: 'create_bug_for_severe_findings' },
  { label: '严重问题自动创建整改任务', value: 'create_task_for_severe_findings' },
  { label: '发送问题消息通知', value: 'send_notification' },
];

const resultActionLabelByValue = new Map(codeInspectionResultActionOptions.map((option) => [option.value, option.label]));

const severityThresholdOptions = [
  { label: 'critical', value: 'critical' },
  { label: 'high', value: 'high' },
  { label: 'medium', value: 'medium' },
];

const defaultCodeInspectionResultActions: ScheduledJobResultAction[] = [
  { type: 'write_code_inspection_report' },
  { severity_threshold: 'critical', type: 'create_bug_for_severe_findings' },
  { severity_threshold: 'high', type: 'create_task_for_severe_findings' },
  { channels: ['email'], recipients: [], type: 'send_notification' },
];

function cloneResultActions(actions: ScheduledJobResultAction[]): ScheduledJobResultAction[] {
  return actions.map((action) => ({
    ...action,
    ...(action.channels ? { channels: [...action.channels] } : {}),
    ...(action.recipients ? { recipients: [...action.recipients] } : {}),
  }));
}

function templatePayloadRecord(template: ScheduledJobTemplateRecord | undefined) {
  return (template?.payload_defaults ?? {}) as Record<string, unknown>;
}

function templatePayloadString(template: ScheduledJobTemplateRecord | undefined, key: string) {
  const value = templatePayloadRecord(template)[key];
  return typeof value === 'string' && value ? value : undefined;
}

function templatePayloadBoolean(
  template: ScheduledJobTemplateRecord | undefined,
  key: string,
  fallback: boolean,
) {
  const value = templatePayloadRecord(template)[key];
  return typeof value === 'boolean' ? value : fallback;
}

function templatePayloadNumber(template: ScheduledJobTemplateRecord | undefined, key: string) {
  const value = templatePayloadRecord(template)[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function templatePayloadList(template: ScheduledJobTemplateRecord | undefined, key: string) {
  const value = templatePayloadRecord(template)[key];
  return Array.isArray(value) ? value.map(String).filter(Boolean) : undefined;
}

function templatePayloadRecordValue(template: ScheduledJobTemplateRecord | undefined, key: string) {
  const value = templatePayloadRecord(template)[key];
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function templatePayloadResultActions(template: ScheduledJobTemplateRecord | undefined) {
  const value = templatePayloadRecord(template).result_actions;
  return Array.isArray(value) ? cloneResultActions(value as ScheduledJobResultAction[]) : undefined;
}

function templateSelector(template: ScheduledJobTemplateRecord | undefined, key: string) {
  const selectors = template?.resource_selectors;
  const value = selectors?.[key];
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function stringArrayFromUnknown(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

function isCodeInspectionPluginAction(action: PluginActionRecord | undefined): action is PluginActionRecord {
  return Boolean(action && codeInspectionPluginActionCodes.has(action.code));
}

function uniqueStringList(values: Array<string | null | undefined>): string[] {
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

function primaryId(ids: string[] | undefined): string | undefined {
  return ids?.[0];
}

function orchestrationConfigValue(configJson: unknown): Record<string, unknown> {
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

function multiIdsFromScheduledJob(
  job: Partial<ScheduledJobRecord> | undefined,
  pluralKey: 'plugin_action_ids' | 'plugin_connection_ids',
  singularKey: 'plugin_action_id' | 'plugin_connection_id',
): string[] {
  return multiIdsFromRecord(job as Record<string, unknown> | undefined, pluralKey, singularKey, job);
}

function scheduledJobConfigWithOrchestration(
  configJson: Record<string, unknown>,
  pluginConnectionIds: string[],
  pluginActionIds: string[],
): Record<string, unknown> {
  return {
    ...configJson,
    orchestration: {
      ...orchestrationConfigValue(configJson),
      plugin_action_ids: pluginActionIds,
      plugin_connection_ids: pluginConnectionIds,
    },
  };
}

function hasRequiredFormValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  return value !== undefined && value !== null && value !== '';
}

function requiredForJobTypes(jobTypes: string[], message: string) {
  return ({ getFieldValue }: { getFieldValue: (field: string) => unknown }) => ({
    validator(_: unknown, value: unknown) {
      if (jobTypes.includes(String(getFieldValue('job_type') ?? '')) && !hasRequiredFormValue(value)) {
        return Promise.reject(new Error(message));
      }
      return Promise.resolve();
    },
  });
}

function codeInspectionUsesNativeScan(jobType: unknown, configJson: unknown): boolean {
  const config = recordValue(configJson) ?? {};
  return (
    String(jobType ?? '') === 'code_repository_inspection'
    && recordStringValue(config, 'scan_mode') === nativeCodeInspectionScanMode
  );
}

function requiredForPluginResource(message: string) {
  return ({ getFieldValue }: { getFieldValue: (field: string) => unknown }) => ({
    validator(_: unknown, value: unknown) {
      const jobType = String(getFieldValue('job_type') ?? '');
      if (
        pluginRequiredJobTypes.includes(jobType)
        && !codeInspectionUsesNativeScan(jobType, getFieldValue('config_json'))
        && !hasRequiredFormValue(value)
      ) {
        return Promise.reject(new Error(message));
      }
      return Promise.resolve();
    },
  });
}

function requiresAiAssembly(jobType: unknown, executionMode: unknown): boolean {
  return (
    aiProcessingRequiredJobTypes.includes(String(jobType ?? ''))
    || ['ai_assisted', 'ai_generated'].includes(String(executionMode ?? ''))
  );
}

function requiredForAiAssembly(message: string) {
  return ({ getFieldValue }: { getFieldValue: (field: string) => unknown }) => ({
    validator(_: unknown, value: unknown) {
      if (
        requiresAiAssembly(getFieldValue('job_type'), getFieldValue('execution_mode'))
        && !hasRequiredFormValue(value)
      ) {
        return Promise.reject(new Error(message));
      }
      return Promise.resolve();
    },
  });
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

function recordFromDraftPayload(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function resultActionsFromDraftPayload(payload: Record<string, unknown>) {
  const value = payload.result_actions;
  return Array.isArray(value) ? (value as ScheduledJobResultAction[]) : undefined;
}

function scheduledJobValuesFromAssistantDraft(
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

function resultActionLabels(actions?: ScheduledJobResultAction[]) {
  const labels = (actions ?? []).map((action) => resultActionLabelByValue.get(action.type) ?? action.type);
  return labels.join('、');
}

function ellipsisText(value: string | undefined) {
  const text = value || '-';
  return (
    <Typography.Text ellipsis={{ tooltip: text }} style={{ display: 'block', maxWidth: '100%' }}>
      {text}
    </Typography.Text>
  );
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

function scheduledJobAssistantDraftModifiedFields(
  initialPayload: Partial<ScheduledJobRecord>,
  currentPayload: Partial<ScheduledJobRecord>,
): string[] {
  const initialRecord = initialPayload as Record<string, unknown>;
  const currentRecord = currentPayload as Record<string, unknown>;
  return assistantDraftTrackedFields.filter((field) => (
    JSON.stringify(comparableDraftValue(initialRecord[field]))
    !== JSON.stringify(comparableDraftValue(currentRecord[field]))
  ));
}

function scheduledJobRunIdFromAssistantResult(result?: Record<string, unknown>) {
  const run = result?.scheduled_job_run;
  if (!run || typeof run !== 'object') {
    return undefined;
  }
  const runId = (run as { id?: unknown }).id;
  return typeof runId === 'string' && runId ? runId : undefined;
}

function writeStrategyLabelFromAction(action: PluginActionRecord): string {
  const mapping = action.result_mapping ?? {};
  const writeTargetLabel = typeof mapping.write_target_label === 'string' ? mapping.write_target_label : undefined;
  const writeTarget = typeof mapping.write_target === 'string' ? mapping.write_target : undefined;
  const strategyLabel = writeTargetLabel ?? writeTarget ?? action.name;
  return `${strategyLabel} (${action.code})`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function snapshotStringValue(snapshot: Record<string, unknown> | undefined, key: string): string | undefined {
  const value = snapshot?.[key];
  return typeof value === 'string' && value ? value : undefined;
}

function snapshotStringListValue(snapshot: Record<string, unknown> | undefined, key: string): string[] {
  const value = snapshot?.[key];
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

function recordValue(value: unknown): Record<string, unknown> | undefined {
  return isRecord(value) ? value : undefined;
}

function recordStringValue(record: Record<string, unknown> | undefined, key: string): string | undefined {
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

function scheduledJobTemplateValuesFromRecord(
  record: Record<string, unknown>,
  {
    fallback,
    nameSuffix = '副本',
    pluginConnectionById,
  }: {
    fallback?: Partial<ScheduledJobRecord>;
    nameSuffix?: string;
    pluginConnectionById: Map<string, PluginConnectionRecord>;
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
  const connectionEnvironment = pluginConnectionId
    ? pluginConnectionById.get(pluginConnectionId)?.environment ?? 'default'
    : undefined;
  const name = recordStringValue(record, 'name') ?? fallback?.name ?? '定时作业';
  const resultActions = Array.isArray(record.result_actions)
    ? (record.result_actions as ScheduledJobResultAction[])
    : fallback?.result_actions;
  const knowledgeDocumentIds = snapshotStringListValue(record, 'knowledge_document_ids');
  const skillIds = snapshotStringListValue(record, 'skill_ids');
  return {
    agent_id: recordStringValue(record, 'agent_id') ?? fallback?.agent_id ?? undefined,
    config_json: recordValue(record.config_json) ?? fallback?.config_json ?? {},
    connection_environment: connectionEnvironment,
    cron_expression: recordStringValue(record, 'cron_expression') ?? fallback?.cron_expression ?? undefined,
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

function scheduledJobRouteParams(): {
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

function assistantRunFollowupPrompt(run: ScheduledJobRunRecord) {
  return run.status === 'failed' ? '为什么这次任务失败？' : '帮我分析这次运行结果';
}

function assistantRunRepairDraftPrompt() {
  return '这次失败怎么修？帮我生成修复草案';
}

function assistantRunComparisonPrompt() {
  return '和上次成功有什么不同？';
}

function assistantRunFollowupUrl(run: ScheduledJobRunRecord, prompt = assistantRunFollowupPrompt(run)) {
  const params = new URLSearchParams();
  params.set('reference_type', 'scheduled_job_run');
  params.set('reference_id', run.id);
  params.set('prompt', prompt);
  return `/assistant?${params.toString()}`;
}

function initialScheduledJobPageTab(): ScheduledJobPageTab {
  return scheduledJobRouteParams().tab ?? 'jobs';
}

export default function ScheduledJobsPage() {
  const [form] = Form.useForm<ScheduledJobFormValues>();
  const [jobs, setJobs] = useState<ScheduledJobRecord[]>([]);
  const [runs, setRuns] = useState<ScheduledJobRunRecord[]>([]);
  const [runObservability, setRunObservability] = useState<ScheduledJobRunObservability | undefined>();
  const [jobTemplates, setJobTemplates] = useState<ScheduledJobTemplateRecord[]>([]);
  const [pluginActions, setPluginActions] = useState<PluginActionRecord[]>([]);
  const [pluginConnections, setPluginConnections] = useState<PluginConnectionRecord[]>([]);
  const [products, setProducts] = useState<ProductFilterOption[]>([]);
  const [productRepositories, setProductRepositories] = useState<ProductGitRepositoryOption[]>([]);
  const [productRepositoriesLoading, setProductRepositoriesLoading] = useState(false);
  const [agents, setAgents] = useState<AiAgentRecord[]>([]);
  const [skills, setSkills] = useState<AiSkillRecord[]>([]);
  const [knowledgeDocuments, setKnowledgeDocuments] = useState<KnowledgeRecord[]>([]);
  const [modelGatewayConfigs, setModelGatewayConfigs] = useState<ModelGatewayConfigRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingJob, setEditingJob] = useState<ScheduledJobRecord | undefined>();
  const [assistantDraftPayload, setAssistantDraftPayload] = useState<Record<string, unknown> | undefined>();
  const [assistantDraftInitialValues, setAssistantDraftInitialValues] = useState<
    ScheduledJobFormValues | undefined
  >();
  const [assistantDraftSource, setAssistantDraftSource] = useState<
    Pick<AssistantScheduledJobDraft, 'draftId' | 'title'> | undefined
  >();
  const [activeTab, setActiveTab] = useState<ScheduledJobPageTab>(initialScheduledJobPageTab);
  const [handledRouteRunKey, setHandledRouteRunKey] = useState<string | undefined>();
  const [templateSource, setTemplateSource] = useState<ScheduledJobTemplateSource | undefined>();
  const [selectedRun, setSelectedRun] = useState<ScheduledJobRunRecord | undefined>();
  const [linkedResultWriteRecordId, setLinkedResultWriteRecordId] = useState<string | undefined>();
  const [selectedRunResultWriteRecords, setSelectedRunResultWriteRecords] = useState<ResultWriteRecord[]>([]);
  const [selectedRunResultWriteRecordsLoading, setSelectedRunResultWriteRecordsLoading] = useState(false);
  const [generatedRunTemplate, setGeneratedRunTemplate] = useState<ScheduledJobTemplateRecord | undefined>();
  const [runningJobId, setRunningJobId] = useState<string | undefined>();
  const [connectionTestResult, setConnectionTestResult] = useState<PluginConnectionTestResult | undefined>();
  const [testingConnectionId, setTestingConnectionId] = useState<string | undefined>();
  const [dryRunResult, setDryRunResult] = useState<ScheduledJobDryRunResult | undefined>();
  const [dryRunning, setDryRunning] = useState(false);
  const selectedConnectionEnvironment = Form.useWatch('connection_environment', form);
  const selectedPluginConnectionIds = Form.useWatch('plugin_connection_ids', form);
  const selectedPluginActionIds = Form.useWatch('plugin_action_ids', form);
  const selectedExecutionMode = Form.useWatch('execution_mode', form);
  const selectedModelGatewayConfigId = Form.useWatch('model_gateway_config_id', form);
  const selectedAgentId = Form.useWatch('agent_id', form);
  const selectedSkillIds = Form.useWatch('skill_ids', form);
  const selectedKnowledgeDocumentIds = Form.useWatch('knowledge_document_ids', form);
  const selectedResultActions = Form.useWatch('result_actions', form);
  const selectedJobType = Form.useWatch('job_type', form);
  const selectedProductId = Form.useWatch('product_id', form);
  const selectedConfigJson = Form.useWatch('config_json', form);
  const selectedTemplateCode = Form.useWatch('template', form);
  const selectedConfigJsonRecord = useMemo(
    () => recordValue(selectedConfigJson) ?? {},
    [selectedConfigJson],
  );
  const selectedRepositoryId = recordStringValue(selectedConfigJsonRecord, 'repository_id');
  const selectedCodeInspectionUsesNativeScan = codeInspectionUsesNativeScan(
    selectedJobType,
    selectedConfigJsonRecord,
  );
  const normalizedSelectedPluginConnectionIds = useMemo(
    () => stringArrayFromUnknown(selectedPluginConnectionIds),
    [selectedPluginConnectionIds],
  );
  const normalizedSelectedPluginActionIds = useMemo(
    () => stringArrayFromUnknown(selectedPluginActionIds),
    [selectedPluginActionIds],
  );
  const selectedPrimaryPluginConnectionId = primaryId(normalizedSelectedPluginConnectionIds);
  const availableJobTemplates = useMemo(
    () =>
      generatedRunTemplate
        ? [
            ...jobTemplates.filter((template) => template.code !== generatedRunTemplate.code),
            generatedRunTemplate,
          ]
        : jobTemplates,
    [generatedRunTemplate, jobTemplates],
  );
  const selectedJobTemplate = useMemo(
    () => availableJobTemplates.find((template) => template.code === selectedTemplateCode),
    [availableJobTemplates, selectedTemplateCode],
  );
  const jobTemplateOptions = useMemo(
    () =>
      availableJobTemplates.map((template) => ({
        label: template.name,
        value: template.code,
      })),
    [availableJobTemplates],
  );
  const pluginActionById = useMemo(
    () => new Map(pluginActions.map((action) => [action.id, action])),
    [pluginActions],
  );
  const pluginConnectionById = useMemo(
    () => new Map(pluginConnections.map((connection) => [connection.id, connection])),
    [pluginConnections],
  );
  const codeInspectionActionByPluginId = useMemo(() => {
    const actionByPluginId = new Map<string, PluginActionRecord>();
    for (const action of pluginActions) {
      if (!isCodeInspectionPluginAction(action)) {
        continue;
      }
      const existing = actionByPluginId.get(action.plugin_id);
      if (!existing || (existing.status !== 'active' && action.status === 'active')) {
        actionByPluginId.set(action.plugin_id, action);
      }
    }
    return actionByPluginId;
  }, [pluginActions]);
  const productRepositoryById = useMemo(
    () => new Map(productRepositories.map((repository) => [repository.id, repository])),
    [productRepositories],
  );
  const selectedRepositoryDefaultBranch = selectedRepositoryId
    ? productRepositoryById.get(selectedRepositoryId)?.defaultBranch
    : undefined;
  const selectedPluginActionPluginIds = useMemo(
    () =>
      new Set(
        normalizedSelectedPluginActionIds
          .map((actionId) => pluginActionById.get(actionId)?.plugin_id)
          .filter((pluginId): pluginId is string => Boolean(pluginId)),
      ),
    [normalizedSelectedPluginActionIds, pluginActionById],
  );
  const connectionPluginFilterIds = useMemo(
    () =>
      selectedJobType === 'code_repository_inspection' && codeInspectionActionByPluginId.size > 0
        ? new Set(codeInspectionActionByPluginId.keys())
        : selectedPluginActionPluginIds,
    [codeInspectionActionByPluginId, selectedJobType, selectedPluginActionPluginIds],
  );
  const jobById = useMemo(
    () => new Map(jobs.map((job) => [job.id, job])),
    [jobs],
  );
  const filteredPluginConnections = useMemo(
    () =>
      pluginConnections.filter((connection) => {
        const matchesEnvironment =
          !selectedConnectionEnvironment
          || (connection.environment ?? 'default') === selectedConnectionEnvironment;
        const matchesSelectedActionPlugin =
          connectionPluginFilterIds.size === 0
          || connectionPluginFilterIds.has(String(connection.plugin_id));
        return matchesEnvironment && matchesSelectedActionPlugin;
      }),
    [connectionPluginFilterIds, pluginConnections, selectedConnectionEnvironment],
  );

  useEffect(() => {
    if (!selectedCodeInspectionUsesNativeScan) {
      return;
    }
    if (normalizedSelectedPluginConnectionIds.length > 0) {
      form.setFieldValue('plugin_connection_id', undefined);
      form.setFieldValue('plugin_connection_ids', []);
    }
    if (normalizedSelectedPluginActionIds.length > 0) {
      form.setFieldValue('plugin_action_id', undefined);
      form.setFieldValue('plugin_action_ids', []);
    }
  }, [
    form,
    normalizedSelectedPluginActionIds.length,
    normalizedSelectedPluginConnectionIds.length,
    selectedCodeInspectionUsesNativeScan,
  ]);
  const modelGatewayConfigById = useMemo(
    () => new Map(modelGatewayConfigs.map((config) => [config.id, config])),
    [modelGatewayConfigs],
  );
  const agentById = useMemo(
    () => new Map(agents.map((agent) => [agent.id, agent])),
    [agents],
  );
  const skillById = useMemo(
    () => new Map(skills.map((skill) => [skill.id, skill])),
    [skills],
  );
  const knowledgeDocumentById = useMemo(
    () => new Map(knowledgeDocuments.map((document) => [document.id, document])),
    [knowledgeDocuments],
  );
  const selectedRunConfigSnapshot = selectedRun?.config_snapshot;
  const selectedRunAgentId = snapshotStringValue(selectedRunConfigSnapshot, 'agent_id');
  const selectedRunModelGatewayConfigId = snapshotStringValue(selectedRunConfigSnapshot, 'model_gateway_config_id');
  const selectedRunSkillIds = snapshotStringListValue(selectedRunConfigSnapshot, 'skill_ids');
  const selectedRunJobType = snapshotStringValue(selectedRunConfigSnapshot, 'job_type');
  const selectedRunExecutionMode = snapshotStringValue(selectedRunConfigSnapshot, 'execution_mode');
  const selectedRunAgentLabel =
    snapshotStringValue(selectedRun?.resolved_agent_snapshot, 'name')
    ?? (selectedRunAgentId ? agentById.get(selectedRunAgentId)?.name ?? selectedRunAgentId : '-');
  const selectedRunModelLabel =
    selectedRunModelGatewayConfigId
      ? modelGatewayConfigById.get(selectedRunModelGatewayConfigId)?.name ?? selectedRunModelGatewayConfigId
      : '-';
  const selectedRunSkillLabels =
    selectedRun?.resolved_skill_snapshots
      ?.map((skill) => String(skill.name ?? skill.code ?? skill.id ?? ''))
      .filter(Boolean)
      .join('、')
    || selectedRunSkillIds.map((skillId) => skillById.get(skillId)?.name ?? skillId).join('、')
    || '-';

  useEffect(() => {
    if (normalizedSelectedPluginConnectionIds.length === 0) {
      return;
    }
    const nextConnectionIds = normalizedSelectedPluginConnectionIds.filter((connectionId) => {
      const connection = pluginConnectionById.get(connectionId);
      if (!connection) {
        return false;
      }
      const matchesEnvironment =
        !selectedConnectionEnvironment
        || (connection.environment ?? 'default') === selectedConnectionEnvironment;
      const matchesSelectedActionPlugin =
        connectionPluginFilterIds.size === 0
        || connectionPluginFilterIds.has(String(connection.plugin_id));
      return matchesEnvironment && matchesSelectedActionPlugin;
    });
    if (nextConnectionIds.length !== normalizedSelectedPluginConnectionIds.length) {
      form.setFieldValue('plugin_connection_ids', nextConnectionIds);
      form.setFieldValue('plugin_connection_id', primaryId(nextConnectionIds));
    }
  }, [
    form,
    connectionPluginFilterIds,
    normalizedSelectedPluginConnectionIds,
    pluginConnectionById,
    selectedConnectionEnvironment,
  ]);

  useEffect(() => {
    queueMicrotask(() => {
      setConnectionTestResult(undefined);
    });
  }, [selectedPrimaryPluginConnectionId]);

  useEffect(() => {
    if (!modalOpen || selectedJobType !== 'code_repository_inspection' || !selectedProductId) {
      queueMicrotask(() => {
        setProductRepositories([]);
        setProductRepositoriesLoading(false);
      });
      return;
    }
    let ignore = false;
    queueMicrotask(() => {
      setProductRepositoriesLoading(true);
    });
    fetchProductGitRepositories(selectedProductId)
      .then((repositories) => {
        if (ignore) {
          return;
        }
        setProductRepositories(repositories);
        const config = recordValue(form.getFieldValue('config_json')) ?? {};
        const currentRepositoryId = recordStringValue(config, 'repository_id');
        const currentBranch = recordStringValue(config, 'branch');
        const selectedRepository =
          repositories.find((repository) => repository.id === currentRepositoryId)
          ?? (!currentRepositoryId ? repositories[0] : undefined);
        if (!currentRepositoryId && selectedRepository) {
          form.setFieldValue(['config_json', 'repository_id'], selectedRepository.id);
        }
        if (!currentBranch && selectedRepository?.defaultBranch) {
          form.setFieldValue(['config_json', 'branch'], selectedRepository.defaultBranch);
        }
      })
      .catch((error) => {
        if (!ignore) {
          message.error(error instanceof Error ? error.message : '代码仓库加载失败');
          setProductRepositories([]);
        }
      })
      .finally(() => {
        if (!ignore) {
          setProductRepositoriesLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [form, modalOpen, selectedJobType, selectedProductId]);

  const handleCodeInspectionRepositoryChange = useCallback(
    (repositoryId: string | undefined) => {
      form.setFieldValue(['config_json', 'repository_id'], repositoryId);
      const repository = repositoryId ? productRepositoryById.get(repositoryId) : undefined;
      form.setFieldValue(['config_json', 'branch'], repository?.defaultBranch ?? undefined);
    },
    [form, productRepositoryById],
  );

  const testSelectedConnection = useCallback(async () => {
    if (!selectedPrimaryPluginConnectionId) {
      message.warning('请先选择数据连接');
      return;
    }
    const hide = message.loading('正在测试数据连接，请稍候...', 0);
    setTestingConnectionId(selectedPrimaryPluginConnectionId);
    try {
      const result = await testPluginConnection(selectedPrimaryPluginConnectionId);
      setConnectionTestResult(result);
      if (result.status === 'succeeded') {
        message.success(`连接测试成功，耗时 ${result.latency_ms}ms`);
      } else {
        message.error(result.error_message || `连接测试 ${result.status}`);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '连接测试失败');
    } finally {
      hide();
      setTestingConnectionId(undefined);
    }
  }, [selectedPrimaryPluginConnectionId]);

  const handlePluginConnectionChange = useCallback(
    (value: unknown) => {
      if (selectedCodeInspectionUsesNativeScan) {
        form.setFieldValue('plugin_connection_id', undefined);
        form.setFieldValue('plugin_connection_ids', []);
        form.setFieldValue('plugin_action_id', undefined);
        form.setFieldValue('plugin_action_ids', []);
        return;
      }
      let nextConnectionIds = uniqueStringList(stringArrayFromUnknown(value));
      if (selectedJobType === 'code_repository_inspection') {
        const addedConnectionId = nextConnectionIds.find(
          (connectionId) => !normalizedSelectedPluginConnectionIds.includes(connectionId),
        );
        const addedConnection = addedConnectionId ? pluginConnectionById.get(addedConnectionId) : undefined;
        if (
          addedConnection
          && codeInspectionActionByPluginId.has(String(addedConnection.plugin_id))
        ) {
          nextConnectionIds = uniqueStringList([
            addedConnectionId,
            ...nextConnectionIds.filter((connectionId) => {
              if (connectionId === addedConnectionId) {
                return false;
              }
              return pluginConnectionById.get(connectionId)?.plugin_id === addedConnection.plugin_id;
            }),
          ]);
        }
        const primaryConnectionId = primaryId(nextConnectionIds);
        const primaryConnection = primaryConnectionId ? pluginConnectionById.get(primaryConnectionId) : undefined;
        const codeInspectionAction = primaryConnection
          ? codeInspectionActionByPluginId.get(String(primaryConnection.plugin_id))
          : undefined;
        if (codeInspectionAction) {
          form.setFieldValue('plugin_action_id', codeInspectionAction.id);
          form.setFieldValue('plugin_action_ids', [codeInspectionAction.id]);
        }
      }
      form.setFieldValue('plugin_connection_id', primaryId(nextConnectionIds));
      form.setFieldValue('plugin_connection_ids', nextConnectionIds);
    },
    [
      codeInspectionActionByPluginId,
      form,
      normalizedSelectedPluginConnectionIds,
      pluginConnectionById,
      selectedCodeInspectionUsesNativeScan,
      selectedJobType,
    ],
  );

  const handleConnectionEnvironmentChange = useCallback(() => {
    form.setFieldValue('plugin_connection_id', undefined);
    form.setFieldValue('plugin_connection_ids', []);
  }, [form]);

  const orchestrationNodes = useMemo<ScheduledJobOrchestrationNode[]>(() => {
    const selectedConnections = normalizedSelectedPluginConnectionIds
      .map((connectionId) => pluginConnectionById.get(connectionId))
      .filter((connection): connection is PluginConnectionRecord => Boolean(connection));
    const selectedActions = normalizedSelectedPluginActionIds
      .map((actionId) => pluginActionById.get(actionId))
      .filter((action): action is PluginActionRecord => Boolean(action));
    const selectedModel = selectedModelGatewayConfigId
      ? modelGatewayConfigById.get(String(selectedModelGatewayConfigId))
      : undefined;
    const selectedAgent = selectedAgentId ? agentById.get(String(selectedAgentId)) : undefined;
    const normalizedSkillIds = Array.isArray(selectedSkillIds) ? selectedSkillIds.map(String) : [];
    const normalizedKnowledgeDocumentIds = Array.isArray(selectedKnowledgeDocumentIds)
      ? selectedKnowledgeDocumentIds.map(String)
      : [];
    const normalizedResultActions = Array.isArray(selectedResultActions)
      ? (selectedResultActions as ScheduledJobResultAction[])
      : [];
    const skillLabels = normalizedSkillIds
      .map((skillId) => skillById.get(skillId)?.name ?? skillId)
      .filter(Boolean);
    const knowledgeLabels = normalizedKnowledgeDocumentIds
      .map((documentId) => knowledgeDocumentById.get(documentId)?.title ?? documentId)
      .filter(Boolean);
    const jobType = String(selectedJobType ?? '');
    const nativeCodeScan = codeInspectionUsesNativeScan(jobType, selectedConfigJsonRecord);
    const connectionRequired = pluginRequiredJobTypes.includes(jobType) && !nativeCodeScan;
    const actionRequired = pluginRequiredJobTypes.includes(jobType) && !nativeCodeScan;
    const aiRequired = requiresAiAssembly(selectedJobType, selectedExecutionMode);
    const dataStatus = nativeCodeScan
      ? '本地扫描'
      : selectedConnections.length > 0
        ? '已配置'
        : connectionRequired
          ? '待配置'
          : '可选';
    const aiStatus =
      selectedModel && selectedAgent && skillLabels.length > 0
        ? '已配置'
        : aiRequired
          ? '待配置'
          : '可选';
    const knowledgeStatus = knowledgeLabels.length > 0 ? '已选择' : '可选';
    const actionStatus = selectedActions.length > 0 ? '已配置' : actionRequired ? '待配置' : '可选';
    const requestSummary = connectionTestResult?.request_summary;
    const requestUrl = typeof requestSummary?.url === 'string' ? requestSummary.url : undefined;
    const connectionDetails = selectedConnections.flatMap((connection, index) => [
      `${index + 1}. ${connection.name}`,
      connection.environment ? `环境 ${connection.environment}` : undefined,
    ]);
    const actionDetails = [
      ...selectedActions.map((action, index) => `${index + 1}. ${action.name}`),
      normalizedResultActions.length ? resultActionLabels(normalizedResultActions) : undefined,
    ].filter((detail): detail is string => Boolean(detail));

    return [
      {
        action: (
          <Button
            block
            disabled={!selectedPrimaryPluginConnectionId}
            loading={testingConnectionId === selectedPrimaryPluginConnectionId}
            onClick={testSelectedConnection}
            size="small"
          >
            测试数据连接
          </Button>
        ),
        details: [
          ...connectionDetails,
          selectedConnections.length > 1 ? `共 ${selectedConnections.length} 个数据连接` : undefined,
          connectionTestResult ? `连接测试 ${connectionTestResult.status}` : undefined,
          connectionTestResult ? `${connectionTestResult.latency_ms}ms` : undefined,
          requestUrl,
        ].filter((detail): detail is string => Boolean(detail)),
        key: 'data_connection',
        required: connectionRequired,
        status: dataStatus,
        statusColor: dataStatus === '已配置' || dataStatus === '本地扫描' ? 'green' : connectionRequired ? 'orange' : 'default',
        title: '数据连接',
      },
      {
        details: [
          selectedModel?.name,
          selectedAgent?.name,
          skillLabels.length ? skillLabels.join('、') : undefined,
        ].filter((detail): detail is string => Boolean(detail)),
        key: 'ai_processing',
        required: aiRequired,
        status: aiStatus,
        statusColor: aiStatus === '已配置' ? 'green' : aiRequired ? 'orange' : 'default',
        title: 'AI执行',
      },
      {
        details: knowledgeLabels,
        key: 'knowledge_reference',
        required: false,
        status: knowledgeStatus,
        statusColor: knowledgeStatus === '已选择' ? 'blue' : 'default',
        title: '知识引用',
      },
      {
        details: actionDetails,
        key: 'result_action',
        required: actionRequired,
        status: actionStatus,
        statusColor: actionStatus === '已配置' ? 'green' : actionRequired ? 'orange' : 'default',
        title: '动作',
      },
    ];
  }, [
    agentById,
    connectionTestResult,
    knowledgeDocumentById,
    modelGatewayConfigById,
    normalizedSelectedPluginActionIds,
    normalizedSelectedPluginConnectionIds,
    pluginActionById,
    pluginConnectionById,
    selectedAgentId,
    selectedConfigJsonRecord,
    selectedExecutionMode,
    selectedJobType,
    selectedKnowledgeDocumentIds,
    selectedModelGatewayConfigId,
    selectedPrimaryPluginConnectionId,
    selectedResultActions,
    selectedSkillIds,
    skillById,
    testingConnectionId,
    testSelectedConnection,
  ]);

  const findConnectionForAction = useCallback(
    (action: PluginActionRecord | undefined) => {
      if (!action) {
        return undefined;
      }
      return (
        pluginConnections.find((connection) => connection.plugin_id === action.plugin_id && connection.status === 'active')
        ?? pluginConnections.find((connection) => connection.plugin_id === action.plugin_id)
      );
    },
    [pluginConnections],
  );

  const findActionForTemplate = useCallback(
    (template: ScheduledJobTemplateRecord | undefined) => {
      const selector = templateSelector(template, 'plugin_action');
      const codeCandidates = stringArrayFromUnknown(selector.code_candidates);
      const textCandidates = stringArrayFromUnknown(selector.text_candidates).map((candidate) =>
        candidate.toLowerCase(),
      );
      return (
        pluginActions.find(
          (action) => action.status === 'active' && codeCandidates.includes(action.code),
        )
        ?? pluginActions.find((action) => codeCandidates.includes(action.code))
        ?? pluginActions.find((action) => {
          const text = `${action.code} ${action.name}`.toLowerCase();
          return action.status === 'active' && textCandidates.some((candidate) => text.includes(candidate));
        })
        ?? pluginActions.find((action) => {
          const text = `${action.code} ${action.name}`.toLowerCase();
          return textCandidates.some((candidate) => text.includes(candidate));
        })
      );
    },
    [pluginActions],
  );

  const applyJobTemplate = useCallback(
    (templateCode?: string) => {
      const template = availableJobTemplates.find((item) => item.code === templateCode);
      if (!template) {
        return;
      }
      const productId = products[0]?.id;
      const modelGatewayConfigId = modelGatewayConfigs[0]?.id;
      const agentId = agents[0]?.id;
      const skillIds = skills[0]?.id ? [skills[0].id] : [];
      const knowledgeDocumentIds = knowledgeDocuments[0]?.id ? [knowledgeDocuments[0].id] : [];

      const action = findActionForTemplate(template);
      const payloadActionIds = uniqueStringList([
        ...(templatePayloadList(template, 'plugin_action_ids') ?? []),
        templatePayloadString(template, 'plugin_action_id'),
      ]);
      const pluginActionIds = payloadActionIds.length ? payloadActionIds : uniqueStringList([action?.id]);
      const primaryAction = pluginActionIds.length ? pluginActionById.get(pluginActionIds[0]) ?? action : action;
      const connection = findConnectionForAction(primaryAction);
      const payloadConnectionIds = uniqueStringList([
        ...(templatePayloadList(template, 'plugin_connection_ids') ?? []),
        templatePayloadString(template, 'plugin_connection_id'),
      ]);
      const pluginConnectionIds = payloadConnectionIds.length
        ? payloadConnectionIds
        : uniqueStringList([connection?.id]);
      const primaryConnectionId = primaryId(pluginConnectionIds);
      const primaryConnection = primaryConnectionId
        ? pluginConnectionById.get(primaryConnectionId) ?? connection
        : connection;
      const jobType = templatePayloadString(template, 'job_type') ?? 'plugin_action_invoke';
      const templateConfigJson = templatePayloadRecordValue(template, 'config_json') ?? {};
      const nativeCodeScan = codeInspectionUsesNativeScan(jobType, templateConfigJson);
      const executionMode = templatePayloadString(template, 'execution_mode') ?? 'deterministic';
      const aiRequired = requiresAiAssembly(jobType, executionMode);
      form.setFieldsValue({
        agent_id: aiRequired ? agentId : undefined,
        config_json: templateConfigJson,
        connection_environment: nativeCodeScan ? undefined : primaryConnection?.environment ?? undefined,
        cron_expression: templatePayloadString(template, 'cron_expression'),
        enabled: templatePayloadBoolean(template, 'enabled', true),
        execution_mode: executionMode,
        interval_seconds: templatePayloadNumber(template, 'interval_seconds'),
        job_type: jobType,
        knowledge_document_ids:
          templatePayloadList(template, 'knowledge_document_ids')
          ?? (aiRequired ? knowledgeDocumentIds : []),
        model_gateway_config_id: aiRequired ? modelGatewayConfigId : undefined,
        name: templatePayloadString(template, 'name') ?? template.name,
        plugin_action_id: nativeCodeScan ? undefined : primaryId(pluginActionIds),
        plugin_action_ids: nativeCodeScan ? [] : pluginActionIds,
        plugin_connection_id: nativeCodeScan ? undefined : primaryId(pluginConnectionIds),
        plugin_connection_ids: nativeCodeScan ? [] : pluginConnectionIds,
        plugin_input_mapping: templatePayloadRecordValue(template, 'plugin_input_mapping'),
        plugin_output_mapping: templatePayloadRecordValue(template, 'plugin_output_mapping'),
        product_id: productId,
        result_actions: templatePayloadResultActions(template) ?? [],
        schedule_type: templatePayloadString(template, 'schedule_type') ?? 'manual',
        skill_ids: templatePayloadList(template, 'skill_ids') ?? (aiRequired ? skillIds : []),
        source_system: templatePayloadString(template, 'source_system') ?? 'ai-brain',
        template: template.code,
      });
    },
    [
      agents,
      findActionForTemplate,
      findConnectionForAction,
      form,
      availableJobTemplates,
      knowledgeDocuments,
      modelGatewayConfigs,
      pluginActionById,
      pluginConnectionById,
      products,
      skills,
    ],
  );

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [
        nextJobs,
        nextRuns,
        nextRunObservability,
        nextJobTemplates,
        nextPluginActions,
        nextPluginConnections,
        nextProducts,
        nextAgents,
        nextSkills,
        nextKnowledgeDocuments,
        nextModelGatewayConfigs,
      ] =
        await Promise.all([
          fetchScheduledJobs(),
          fetchScheduledJobRuns(),
          fetchScheduledJobRunObservability(),
          fetchScheduledJobTemplates(),
          fetchPluginActions(),
          fetchPluginConnections(),
          fetchActiveProductOptions(),
          fetchAiAgents(),
          fetchAiSkills(),
          fetchManagementKnowledge(),
          fetchModelGatewayConfigs(),
        ]);
      setJobs(nextJobs);
      setRuns(nextRuns);
      setRunObservability(nextRunObservability);
      setJobTemplates(nextJobTemplates);
      setPluginActions(nextPluginActions);
      setPluginConnections(nextPluginConnections);
      setProducts(nextProducts);
      setAgents(nextAgents.filter((agent) => agent.status === 'active'));
      setSkills(nextSkills.filter((skill) => skill.status === 'active'));
      setKnowledgeDocuments(
        nextKnowledgeDocuments.filter((document) =>
          ['indexed', 'text_indexed', 'vector_indexed'].includes(document.status),
        ),
      );
      setModelGatewayConfigs(nextModelGatewayConfigs.filter((config) => config.status === 'active'));
    } catch (error) {
      message.error(error instanceof Error ? error.message : '定时作业加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      void reload();
    });
  }, [reload]);

  useEffect(() => {
    const routeParams = scheduledJobRouteParams();
    const routeTab = routeParams.tab;
    if (routeTab) {
      queueMicrotask(() => {
        setActiveTab(routeTab);
      });
    }
    const routeRunKey = routeParams.runId
      ? `${routeParams.runId}:${routeParams.resultWriteRecordId ?? ''}`
      : undefined;
    if (!routeParams.runId || handledRouteRunKey === routeRunKey) {
      return;
    }
    const routeRun = runs.find((run) => run.id === routeParams.runId);
    if (!routeRun) {
      return;
    }
    queueMicrotask(() => {
      setActiveTab('runs');
      setLinkedResultWriteRecordId(routeParams.resultWriteRecordId);
      setSelectedRun(routeRun);
      setHandledRouteRunKey(routeRunKey);
    });
  }, [handledRouteRunKey, runs]);

  useEffect(() => {
    if (!selectedRun?.id) {
      queueMicrotask(() => {
        setSelectedRunResultWriteRecords([]);
        setSelectedRunResultWriteRecordsLoading(false);
      });
      return;
    }
    let ignore = false;
    queueMicrotask(() => {
      setSelectedRunResultWriteRecordsLoading(true);
    });
    fetchResultWriteRecords({ scheduledJobRunId: selectedRun.id })
      .then((records) => {
        if (!ignore) {
          setSelectedRunResultWriteRecords(records);
        }
      })
      .catch((error) => {
        if (!ignore) {
          setSelectedRunResultWriteRecords([]);
          message.error(error instanceof Error ? error.message : '结果写入记录加载失败');
        }
      })
      .finally(() => {
        if (!ignore) {
          setSelectedRunResultWriteRecordsLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [selectedRun?.id]);

  useEffect(() => {
    if (typeof window === 'undefined' || modalOpen || editingJob) {
      return;
    }
    const storageKey = assistantScopedStorageKey(ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY);
    const rawDraft = window.sessionStorage.getItem(storageKey);
    if (!rawDraft) {
      return;
    }
    window.sessionStorage.removeItem(storageKey);
    try {
      const draft = JSON.parse(rawDraft) as AssistantScheduledJobDraft;
      if (!draft.payload || typeof draft.payload !== 'object' || Array.isArray(draft.payload)) {
        throw new Error('Invalid scheduled job draft payload');
      }
      const draftValues = scheduledJobValuesFromAssistantDraft(draft);
      queueMicrotask(() => {
        setEditingJob(undefined);
        setAssistantDraftPayload(draft.payload);
        setAssistantDraftInitialValues(draftValues);
        setAssistantDraftSource({ draftId: draft.draftId, title: draft.title });
        setConnectionTestResult(undefined);
        form.resetFields();
        form.setFieldsValue(draftValues);
        setModalOpen(true);
        message.success('已载入 AI 助手生成的定时作业草案，请确认后保存');
      });
    } catch {
      queueMicrotask(() => {
        setAssistantDraftPayload(undefined);
        setAssistantDraftInitialValues(undefined);
        setAssistantDraftSource(undefined);
        message.error('AI 助手定时作业草案格式无效');
      });
    }
  }, [editingJob, form, modalOpen]);

  const openCreateJobModal = () => {
    setEditingJob(undefined);
    setAssistantDraftPayload(undefined);
    setAssistantDraftInitialValues(undefined);
    setAssistantDraftSource(undefined);
    setTemplateSource(undefined);
    setGeneratedRunTemplate(undefined);
    setConnectionTestResult(undefined);
    setDryRunResult(undefined);
    form.resetFields();
    form.setFieldsValue({
      enabled: true,
      execution_mode: 'ai_generated',
      job_type: 'user_feedback_insight_extract',
      schedule_type: 'manual',
      source_system: 'ai-brain',
      template: undefined,
    });
    setModalOpen(true);
  };

  const openCopyJobModal = (job: ScheduledJobRecord) => {
    const values = scheduledJobTemplateValuesFromRecord(job as unknown as Record<string, unknown>, {
      fallback: job,
      pluginConnectionById,
    });
    setEditingJob(undefined);
    setAssistantDraftPayload(undefined);
    setAssistantDraftInitialValues(undefined);
    setAssistantDraftSource(undefined);
    setGeneratedRunTemplate(undefined);
    setConnectionTestResult(undefined);
    setDryRunResult(undefined);
    setTemplateSource({
      sourceId: job.id,
      sourceType: 'scheduled_job',
      title: job.name,
      values,
    });
    form.resetFields();
    form.setFieldsValue(values);
    setModalOpen(true);
    message.success('已复制为新作业草稿，请确认后保存');
  };

  const openCopyRunModal = (run: ScheduledJobRunRecord) => {
    const sourceJob = run.scheduled_job_id ? jobById.get(run.scheduled_job_id) : undefined;
    const snapshot = run.config_snapshot ?? {};
    const values = scheduledJobTemplateValuesFromRecord(snapshot, {
      fallback: sourceJob,
      nameSuffix: '运行快照副本',
      pluginConnectionById,
    });
    setSelectedRun(undefined);
    setLinkedResultWriteRecordId(undefined);
    setEditingJob(undefined);
    setAssistantDraftPayload(undefined);
    setAssistantDraftInitialValues(undefined);
    setAssistantDraftSource(undefined);
    setGeneratedRunTemplate(undefined);
    setConnectionTestResult(undefined);
    setDryRunResult(undefined);
    setTemplateSource({
      sourceId: run.id,
      sourceType: 'scheduled_job_run',
      title: run.scheduled_job_id ?? run.id,
      values,
    });
    form.resetFields();
    form.setFieldsValue(values);
    setModalOpen(true);
    message.success('已按本次运行快照生成新作业草稿，请确认后保存');
  };

  const generateTemplateFromRun = async (run: ScheduledJobRunRecord) => {
    try {
      const template = await generateScheduledJobTemplateFromRun(run.id);
      const payloadDefaults = (template.payload_defaults ?? {}) as Record<string, unknown>;
      const values = scheduledJobTemplateValuesFromRecord(payloadDefaults, {
        fallback: template.payload_defaults,
        nameSuffix: '',
        pluginConnectionById,
      });
      const jobType = values.job_type ?? 'user_feedback_insight_extract';
      const executionMode = values.execution_mode ?? 'ai_generated';
      const aiRequired = requiresAiAssembly(jobType, executionMode);
      const enrichedValues = {
        ...values,
        agent_id: aiRequired ? values.agent_id ?? agents[0]?.id : values.agent_id,
        model_gateway_config_id: aiRequired
          ? values.model_gateway_config_id ?? modelGatewayConfigs[0]?.id
          : values.model_gateway_config_id,
        product_id: values.product_id ?? products[0]?.id,
        skill_ids:
          values.skill_ids?.length
            ? values.skill_ids
            : aiRequired && skills[0]?.id
              ? [skills[0].id]
              : [],
      };
      setSelectedRun(undefined);
      setLinkedResultWriteRecordId(undefined);
      setEditingJob(undefined);
      setAssistantDraftPayload(undefined);
      setAssistantDraftInitialValues(undefined);
      setAssistantDraftSource(undefined);
      setConnectionTestResult(undefined);
      setDryRunResult(undefined);
      setGeneratedRunTemplate(template);
      setTemplateSource({
        sourceId: run.id,
        sourceType: 'scheduled_job_run',
        title: template.name,
        values: enrichedValues,
      });
      form.resetFields();
      form.setFieldsValue({
        ...enrichedValues,
        template: template.code,
      });
      setModalOpen(true);
      message.success('已从成功运行生成作业模板');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '运行模板生成失败');
    }
  };

  const openEditJobModal = (job: ScheduledJobRecord) => {
    const pluginConnectionIds = multiIdsFromScheduledJob(job, 'plugin_connection_ids', 'plugin_connection_id');
    const pluginActionIds = multiIdsFromScheduledJob(job, 'plugin_action_ids', 'plugin_action_id');
    const primaryConnectionId = primaryId(pluginConnectionIds);
    const editConfigJson = recordValue(job.config_json) ?? {};
    if (job.job_type === 'code_repository_inspection' && !recordStringValue(editConfigJson, 'scan_mode')) {
      editConfigJson.scan_mode = 'sync_existing_alerts';
    }
    const nativeCodeScan = codeInspectionUsesNativeScan(job.job_type, editConfigJson);
    setEditingJob(job);
    setAssistantDraftPayload(undefined);
    setAssistantDraftInitialValues(undefined);
    setAssistantDraftSource(undefined);
    setTemplateSource(undefined);
    setGeneratedRunTemplate(undefined);
    setConnectionTestResult(undefined);
    setDryRunResult(undefined);
    form.resetFields();
    form.setFieldsValue({
      agent_id: job.agent_id ?? undefined,
      connection_environment: !nativeCodeScan && primaryConnectionId
        ? pluginConnectionById.get(primaryConnectionId)?.environment ?? 'default'
        : undefined,
      config_json: editConfigJson,
      cron_expression: job.cron_expression ?? undefined,
      enabled: job.enabled ?? true,
      execution_mode: job.execution_mode ?? 'deterministic',
      interval_seconds: job.interval_seconds ?? undefined,
      job_type: job.job_type,
      knowledge_document_ids: job.knowledge_document_ids ?? [],
      model_gateway_config_id: job.model_gateway_config_id ?? undefined,
      name: job.name,
      plugin_action_id: nativeCodeScan ? undefined : primaryId(pluginActionIds),
      plugin_action_ids: nativeCodeScan ? [] : pluginActionIds,
      plugin_connection_id: nativeCodeScan ? undefined : primaryConnectionId,
      plugin_connection_ids: nativeCodeScan ? [] : pluginConnectionIds,
      product_id: job.product_id ?? undefined,
      result_actions: job.result_actions?.length ? job.result_actions : defaultCodeInspectionResultActions,
      schedule_type: job.schedule_type ?? 'manual',
      skill_ids: job.skill_ids ?? [],
      source_system: job.source_system ?? 'ai-brain',
      template: undefined,
    });
    setModalOpen(true);
  };

  const closeJobModal = () => {
    setModalOpen(false);
    setEditingJob(undefined);
    setAssistantDraftPayload(undefined);
    setAssistantDraftInitialValues(undefined);
    setAssistantDraftSource(undefined);
    setTemplateSource(undefined);
    setGeneratedRunTemplate(undefined);
    setConnectionTestResult(undefined);
    setDryRunning(false);
    setDryRunResult(undefined);
    form.resetFields();
  };

  const buildJobRequestPayload = (values: ScheduledJobFormValues): Partial<ScheduledJobRecord> => {
    const { template, ...jobValues } = values;
    const selectedTemplate = availableJobTemplates.find((item) => item.code === template);
    delete jobValues.connection_environment;
    const pluginConnectionIds = uniqueStringList(
      Array.isArray(values.plugin_connection_ids)
        ? values.plugin_connection_ids
        : [values.plugin_connection_id],
    );
    const pluginActionIds = uniqueStringList(
      Array.isArray(values.plugin_action_ids)
        ? values.plugin_action_ids
        : [values.plugin_action_id],
    );
    jobValues.plugin_connection_id = primaryId(pluginConnectionIds) ?? null;
    jobValues.plugin_connection_ids = pluginConnectionIds;
    jobValues.plugin_action_id = primaryId(pluginActionIds) ?? null;
    jobValues.plugin_action_ids = pluginActionIds;
    const draftConfigJson = recordFromDraftPayload(assistantDraftPayload ?? {}, 'config_json') ?? {};
    const templateConfigJson = templateSource?.values.config_json ?? {};
    const templateSourceConfig =
      templateSource && !editingJob
        ? {
            template_source: {
              source_id: templateSource.sourceId,
              source_type: templateSource.sourceType,
              title: templateSource.title,
            },
          }
        : {};
    const assistantDraftConfig =
      assistantDraftPayload && !editingJob
        ? {
            assistant_draft: {
              draft_id: assistantDraftSource?.draftId,
              source: 'assistant.action_draft',
              title: assistantDraftSource?.title,
            },
          }
        : {};
    const requestPayload: Partial<ScheduledJobRecord> = {
      ...jobValues,
      config_json: scheduledJobConfigWithOrchestration(
        {
          ...(editingJob?.config_json ?? {}),
          ...templateConfigJson,
          ...draftConfigJson,
          ...(values.config_json ?? {}),
          ...templateSourceConfig,
          ...assistantDraftConfig,
        },
        pluginConnectionIds,
        pluginActionIds,
      ),
      plugin_input_mapping:
        editingJob?.plugin_input_mapping
        ?? templateSource?.values.plugin_input_mapping
        ?? values.plugin_input_mapping
        ?? recordFromDraftPayload(assistantDraftPayload ?? {}, 'plugin_input_mapping')
        ?? templatePayloadRecordValue(selectedTemplate, 'plugin_input_mapping')
        ?? {},
      plugin_output_mapping:
        editingJob?.plugin_output_mapping
        ?? templateSource?.values.plugin_output_mapping
        ?? values.plugin_output_mapping
        ?? recordFromDraftPayload(assistantDraftPayload ?? {}, 'plugin_output_mapping')
        ?? templatePayloadRecordValue(selectedTemplate, 'plugin_output_mapping')
        ?? {},
      knowledge_document_ids: values.knowledge_document_ids ?? [],
      result_actions:
        values.job_type === 'code_repository_inspection'
          ? values.result_actions?.length
            ? values.result_actions
            : templatePayloadResultActions(selectedTemplate) ?? cloneResultActions(defaultCodeInspectionResultActions)
          : [],
      skill_ids: values.skill_ids ?? [],
    };
    if (codeInspectionUsesNativeScan(requestPayload.job_type, requestPayload.config_json)) {
      requestPayload.plugin_action_id = null;
      requestPayload.plugin_action_ids = [];
      requestPayload.plugin_connection_id = null;
      requestPayload.plugin_connection_ids = [];
      requestPayload.config_json = scheduledJobConfigWithOrchestration(
        recordValue(requestPayload.config_json) ?? {},
        [],
        [],
      );
    }
    return requestPayload;
  };

  const currentValidatedJobPayload = async () => {
    await form.validateFields();
    return buildJobRequestPayload(form.getFieldsValue(true) as ScheduledJobFormValues);
  };

  const dryRunJob = async () => {
    let requestPayload: Partial<ScheduledJobRecord>;
    try {
      requestPayload = await currentValidatedJobPayload();
    } catch {
      return;
    }
    const hide = message.loading('正在进行全链路试运行，请稍候...', 0);
    setDryRunning(true);
    try {
      const result = await dryRunScheduledJob(requestPayload);
      setDryRunResult(result);
      if (result.status === 'succeeded') {
        message.success('全链路试运行完成');
      } else {
        message.error(`全链路试运行 ${result.status}`);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '全链路试运行失败');
    } finally {
      hide();
      setDryRunning(false);
    }
  };

  const submitJob = async () => {
    let requestPayload: Partial<ScheduledJobRecord>;
    let formValues: ScheduledJobFormValues;
    try {
      await form.validateFields();
      formValues = form.getFieldsValue(true) as ScheduledJobFormValues;
      requestPayload = buildJobRequestPayload(formValues);
    } catch {
      return;
    }
    if (editingJob) {
      await updateScheduledJob(editingJob.id, requestPayload);
      message.success('定时作业已更新');
    } else if (assistantDraftSource?.draftId && assistantDraftInitialValues) {
      const initialPayload = buildJobRequestPayload(assistantDraftInitialValues);
      const modifiedFields = scheduledJobAssistantDraftModifiedFields(
        initialPayload,
        requestPayload,
      );
      await updateAssistantActionDraft(
        assistantDraftSource.draftId,
        requestPayload as Record<string, unknown>,
        modifiedFields,
      );
      const confirmed = await confirmAssistantActionDraft(assistantDraftSource.draftId);
      rememberAssistantDraftResolution({
        draftId: assistantDraftSource.draftId,
        resourceId: confirmed.run.result_id,
        resourceType: 'scheduled_job',
        scheduledJobRunId: scheduledJobRunIdFromAssistantResult(confirmed.run.result),
        title: assistantDraftSource.title ?? formValues.name,
      });
      message.success('助手草案已确认并创建定时作业');
    } else {
      await createScheduledJob(requestPayload);
      message.success('定时作业已创建');
    }
    closeJobModal();
    await reload();
  };

  const triggerJobRun = async (
    jobId: string,
    triggerType: 'manual' | 'manual_rerun' = 'manual',
    sourceRunId?: string,
  ) => {
    const hide = message.loading('作业执行中，请稍候...', 0);
    setRunningJobId(jobId);
    try {
      const run = await runScheduledJob(jobId, triggerType, sourceRunId);
      setLinkedResultWriteRecordId(undefined);
      setSelectedRun(run);
      if (run.status === 'succeeded') {
        message.success('作业运行完成');
      } else if (run.status === 'running' || run.status === 'queued') {
        message.info(`作业${run.status === 'queued' ? '已排队' : '运行中'}，请在运行记录查看进度`);
      } else {
        message.error(run.error_message ? `作业运行失败：${run.error_message}` : `作业运行 ${run.status}`);
      }
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '作业运行失败');
    } finally {
      hide();
      setRunningJobId(undefined);
    }
  };

  const triggerJob = async (job: ScheduledJobRecord) => {
    await triggerJobRun(job.id);
  };

  const confirmDeleteJob = (job: ScheduledJobRecord) => {
    Modal.confirm({
      title: '删除定时作业',
      content: `确定删除「${job.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        await deleteScheduledJob(job.id);
        message.success('定时作业已删除');
        await reload();
      },
    });
  };

  return (
    <PageContainer title="定时作业">
      <Tabs
        activeKey={activeTab}
        onChange={(key) => setActiveTab(key === 'runs' ? 'runs' : 'jobs')}
        items={[
          {
            key: 'jobs',
            label: '作业配置',
            children: (
              <ProTable<ScheduledJobRecord>
                cardBordered
                className="management-list-table"
                dateFormatter="string"
                headerTitle="作业配置"
                loading={loading}
                options={{
                  density: true,
                  fullScreen: true,
                  reload,
                  setting: true,
                }}
                pagination={{
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`,
                }}
                rowKey="id"
                scroll={{ x: 1540 }}
                search={false}
                dataSource={jobs}
                tableLayout="fixed"
                toolBarRender={() => [
                  <Button key="create-job" aria-label="新增作业" icon={<PlusOutlined />} type="primary" onClick={openCreateJobModal}>
                    新增作业
                  </Button>,
                  <Button key="reload-jobs" icon={<ReloadOutlined />} onClick={reload}>
                    刷新
                  </Button>,
                ]}
                columns={[
                  { dataIndex: 'name', title: '名称', width: 220, render: (value) => ellipsisText(String(value ?? '')) },
                  {
                    key: 'template_source',
                    title: '模板来源',
                    width: 220,
                    render: (_, row) => <TemplateSourceSummary source={templateSourceFromConfig(row.config_json)} />,
                  },
                  {
                    dataIndex: 'job_type',
                    title: '类型',
                    width: 190,
                    render: (value) => ellipsisText(jobTypeLabelByValue.get(String(value)) ?? String(value ?? '')),
                  },
                  {
                    dataIndex: 'plugin_connection_id',
                    title: '数据连接',
                    width: 260,
                    render: (_, row) => {
                      const connectionLabels = multiIdsFromScheduledJob(
                        row,
                        'plugin_connection_ids',
                        'plugin_connection_id',
                      ).map((connectionId) => {
                        const connection = pluginConnectionById.get(connectionId);
                        return connection
                          ? `${connection.name} (${connection.environment ?? 'default'})`
                          : connectionId;
                      });
                      return ellipsisText(connectionLabels.join(' / '));
                    },
                  },
                  {
                    key: 'ai_execution',
                    title: 'AI执行',
                    width: 300,
                    render: (_, row) => {
                      const modeLabel = executionModeLabelByValue.get(String(row.execution_mode)) ?? String(row.execution_mode ?? '-');
                      const config = row.model_gateway_config_id
                        ? modelGatewayConfigById.get(String(row.model_gateway_config_id))
                        : undefined;
                      const agent = row.agent_id ? agentById.get(String(row.agent_id)) : undefined;
                      const skillCount = Array.isArray(row.skill_ids) ? row.skill_ids.length : 0;
                      const parts = [
                        modeLabel,
                        row.execution_mode === 'deterministic' ? undefined : config?.name,
                        row.execution_mode === 'deterministic' ? undefined : agent?.name,
                        row.execution_mode === 'deterministic' || !skillCount ? undefined : `${skillCount} Skill`,
                      ].filter((item): item is string => Boolean(item));
                      return ellipsisText(parts.join(' · '));
                    },
                  },
                  {
                    key: 'action',
                    title: '动作',
                    width: 280,
                    render: (_, row) => {
                      const actionLabels = multiIdsFromScheduledJob(row, 'plugin_action_ids', 'plugin_action_id').map(
                        (actionId) => pluginActionById.get(actionId)?.name ?? actionId,
                      );
                      const resultActions = resultActionLabels(row.result_actions as ScheduledJobResultAction[]);
                      return ellipsisText([...actionLabels, resultActions].filter(Boolean).join(' / '));
                    },
                  },
                  {
                    dataIndex: 'schedule_type',
                    title: '调度',
                    width: 180,
                    render: (value, row) => {
                      const scheduleLabel = scheduleTypeLabelByValue.get(String(value)) ?? String(value ?? '-');
                      const scheduleValue = row.cron_expression || (row.interval_seconds ? `${row.interval_seconds}s` : undefined);
                      return ellipsisText([scheduleLabel, scheduleValue].filter(Boolean).join(' · '));
                    },
                  },
                  {
                    dataIndex: 'next_run_at',
                    title: '下次运行',
                    width: 180,
                    render: (_, row) => ellipsisText(formatDisplayDateTime(row.next_run_at)),
                  },
                  {
                    dataIndex: 'status',
                    title: '状态',
                    width: 100,
                    render: (value, row) => (
                      <Tag color={row.enabled ? 'green' : 'default'}>
                        {statusLabelByValue.get(String(value)) ?? String(value ?? '-')}
                      </Tag>
                    ),
                  },
                  {
                    fixed: 'right',
                    key: 'actions',
                    title: '操作',
                    valueType: 'option',
                    width: 330,
                    render: (_, row) => (
                      <Space className="management-row-actions" size={0}>
                        <Button
                          aria-label={`编辑作业 ${row.name}`}
                          icon={<EditOutlined />}
                          onClick={() => openEditJobModal(row)}
                          type="link"
                        >
                          编辑
                        </Button>
                        <Button
                          aria-label={`复制作业 ${row.name}`}
                          icon={<CopyOutlined />}
                          onClick={() => openCopyJobModal(row)}
                          type="link"
                        >
                          复制
                        </Button>
                        <Button
                          aria-label={`运行作业 ${row.name}`}
                          disabled={Boolean(runningJobId)}
                          icon={<PlayCircleOutlined />}
                          loading={runningJobId === row.id}
                          onClick={() => triggerJob(row)}
                          type="link"
                        >
                          运行
                        </Button>
                        <Button
                          aria-label={`删除作业 ${row.name}`}
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => confirmDeleteJob(row)}
                          type="link"
                        >
                          删除
                        </Button>
                      </Space>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'runs',
            label: '运行记录',
            children: (
              <>
                <ScheduledJobRunObservabilityOverview loading={loading} observability={runObservability} />
                <ProTable<ScheduledJobRunRecord>
                  cardBordered
                  className="management-list-table"
                  dateFormatter="string"
                  headerTitle="运行记录"
                  loading={loading}
                  options={{
                    density: true,
                    fullScreen: true,
                    reload,
                    setting: true,
                  }}
                  pagination={{
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 条`,
                  }}
                  rowKey="id"
                  scroll={{ x: 1500 }}
                  search={false}
                  dataSource={runs}
                  tableLayout="fixed"
                  columns={[
                    { dataIndex: 'id', title: '运行 ID', ellipsis: true, width: 220 },
                    { dataIndex: 'scheduled_job_id', title: '作业 ID', ellipsis: true, width: 220 },
                    { dataIndex: 'status', title: '状态', width: 120 },
                    {
                      dataIndex: 'trigger_type',
                      title: '触发方式',
                      width: 130,
                      render: (value) => runTriggerTypeLabelByValue.get(String(value ?? '')) ?? value ?? '-',
                    },
                    { dataIndex: 'source_run_id', title: '复跑来源', ellipsis: true, width: 200, render: (value) => value || '-' },
                    { dataIndex: 'collector_run_id', title: '采集运行', ellipsis: true, width: 220, render: (value) => value || '-' },
                    { dataIndex: 'plugin_invocation_log_id', title: '插件调用', ellipsis: true, width: 220, render: (value) => value || '-' },
                    { dataIndex: 'records_imported', title: '导入数', width: 100 },
                    { dataIndex: 'error_message', title: '错误', ellipsis: true, width: 180, render: (value) => value || '-' },
                    {
                      fixed: 'right',
                      key: 'actions',
                      title: '操作',
                      valueType: 'option',
                      width: 270,
                      render: (_, row) => (
                        <Space size={4}>
                          <Button
                            aria-label={`查看运行结果 ${row.id}`}
                            icon={<EyeOutlined />}
                            onClick={() => {
                              setLinkedResultWriteRecordId(undefined);
                              setSelectedRun(row);
                            }}
                            type="link"
                          >
                            详情
                          </Button>
                          <Button
                            aria-label={`复制运行配置 ${row.id}`}
                            icon={<CopyOutlined />}
                            onClick={() => openCopyRunModal(row)}
                            type="link"
                          >
                            复制配置
                          </Button>
                          <Button
                            aria-label={`复跑运行 ${row.id}`}
                            disabled={Boolean(runningJobId) || !row.scheduled_job_id}
                            icon={<ReloadOutlined />}
                            loading={runningJobId === row.scheduled_job_id}
                            onClick={() => {
                              if (row.scheduled_job_id) {
                                triggerJobRun(row.scheduled_job_id, 'manual_rerun', row.id);
                              }
                            }}
                            type="link"
                          >
                            复跑
                          </Button>
                        </Space>
                      ),
                    },
                  ]}
                />
              </>
            ),
          },
        ]}
      />

      <Modal
        aria-label={editingJob ? '编辑定时作业' : '新增定时作业'}
        destroyOnHidden
        footer={(
          <Space>
            <Button htmlType="button" onClick={closeJobModal}>取消</Button>
            <Button
              htmlType="button"
              loading={dryRunning}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                void dryRunJob();
              }}
            >
              全链路试运行
            </Button>
            <Button htmlType="button" type="primary" onClick={() => void submitJob()}>
              确定
            </Button>
          </Space>
        )}
        open={modalOpen}
        title={editingJob ? '编辑定时作业' : '新增定时作业'}
        width={820}
        onCancel={closeJobModal}
      >
        {templateSource ? (
          <div
            aria-label="当前复制来源"
            style={{
              background: '#f8fafc',
              border: '1px solid #e5e7eb',
              borderRadius: 6,
              marginBottom: 16,
              padding: '10px 12px',
            }}
          >
            <Space wrap>
              <Typography.Text type="secondary">复制来源</Typography.Text>
              <TemplateSourceSummary source={templateSource} />
            </Space>
          </div>
        ) : null}
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            enabled: true,
            execution_mode: 'ai_generated',
            job_type: 'user_feedback_insight_extract',
            schedule_type: 'manual',
            source_system: 'ai-brain',
          }}
        >
          {!editingJob ? (
            <Form.Item label="作业模板" name="template">
              <Select
                allowClear
                options={jobTemplateOptions}
                placeholder="请选择场景模板快速生成配置"
                onChange={applyJobTemplate}
              />
            </Form.Item>
          ) : null}
          <ScheduledJobOrchestrationFlow
            nodes={orchestrationNodes}
            wizardSteps={selectedJobTemplate?.wizard_steps}
          />
          <Form.Item hidden name="source_system">
            <Input />
          </Form.Item>
          <FormSection label="基础信息" marker="基本">
            <Row gutter={12}>
              <Col span={14}>
                <Form.Item label="名称" name="name" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
              </Col>
              <Col span={10}>
                <Form.Item label="作业类型" name="job_type" rules={[{ required: true }]}>
                  <Select
                    options={jobTypeOptions}
                    onChange={(value) => {
                      if (value === 'code_repository_inspection') {
                        form.setFieldsValue({
                          config_json: {
                            ...(recordValue(form.getFieldValue('config_json')) ?? {}),
                            scan_mode: nativeCodeInspectionScanMode,
                          },
                          execution_mode: 'deterministic',
                          plugin_action_id: undefined,
                          plugin_action_ids: [],
                          plugin_connection_id: undefined,
                          plugin_connection_ids: [],
                          result_actions: form.getFieldValue('result_actions')?.length
                            ? form.getFieldValue('result_actions')
                            : cloneResultActions(defaultCodeInspectionResultActions),
                        });
                      }
                    }}
                  />
                </Form.Item>
              </Col>
              <Col span={18}>
                <Form.Item
                  label="所属产品"
                  name="product_id"
                  rules={[requiredForJobTypes(productRequiredJobTypes, '请选择产品')]}
                >
                  <Select
                    allowClear
                    showSearch
                    optionFilterProp="label"
                    placeholder="请选择产品"
                    onChange={() => {
                      if (selectedJobType === 'code_repository_inspection') {
                        form.setFieldValue(['config_json', 'repository_id'], undefined);
                        form.setFieldValue(['config_json', 'branch'], undefined);
                      }
                    }}
                    options={products.map((product) => ({
                      label: `${product.name} (${product.code})`,
                      value: product.id,
                    }))}
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="启用" name="enabled" valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
            </Row>
          </FormSection>
          <ScheduledJobDataConnectionSection
            connectionEnvironmentOptions={connectionEnvironmentOptions}
            filteredPluginConnections={filteredPluginConnections}
            onConnectionEnvironmentChange={handleConnectionEnvironmentChange}
            onPluginConnectionChange={handlePluginConnectionChange}
            requiredForPluginResource={requiredForPluginResource}
            usesNativeScan={selectedCodeInspectionUsesNativeScan}
          />
          {selectedJobType === 'code_repository_inspection' ? (
            <FormSection label="代码仓库配置" marker="仓库">
              <Row gutter={12}>
                <Col span={24}>
                  <Form.Item label="扫描方式" name={['config_json', 'scan_mode']}>
                    <Select
                      options={codeInspectionScanModeOptions}
                      onChange={(value) => {
                        if (value === nativeCodeInspectionScanMode) {
                          form.setFieldValue('plugin_connection_id', undefined);
                          form.setFieldValue('plugin_connection_ids', []);
                          form.setFieldValue('plugin_action_id', undefined);
                          form.setFieldValue('plugin_action_ids', []);
                          form.setFieldValue(['config_json', 'async_execution'], true);
                          form.setFieldValue(['config_json', 'scanner_engines'], ['builtin']);
                          form.setFieldValue(['config_json', 'scan_rules'], ['secrets', 'internal_addresses']);
                        }
                      }}
                    />
                  </Form.Item>
                </Col>
                <Col span={14}>
                  <Form.Item
                    label="代码仓库"
                    name={['config_json', 'repository_id']}
                  >
                    <Select
                      allowClear
                      loading={productRepositoriesLoading}
                      onChange={handleCodeInspectionRepositoryChange}
                      optionFilterProp="label"
                      options={productRepositories.map((repository) => ({
                        label: repository.label,
                        value: repository.id,
                      }))}
                      placeholder="请选择代码仓库"
                      showSearch
                    />
                  </Form.Item>
                </Col>
                <Col span={10}>
                  <Form.Item
                    label="扫描分支"
                    name={['config_json', 'branch']}
                    rules={[{ required: true, message: '请输入扫描分支' }]}
                  >
                    <Input placeholder={selectedRepositoryDefaultBranch ?? 'main'} />
                  </Form.Item>
                </Col>
                <Col span={24}>
                  <Form.Item
                    extra="用于一个产品同时扫描前端、后端、移动端等多个仓库；留空时使用上方单仓库"
                    label="批量代码仓库"
                    name={['config_json', 'repository_ids']}
                  >
                    <Select
                      allowClear
                      loading={productRepositoriesLoading}
                      mode="multiple"
                      optionFilterProp="label"
                      options={productRepositories.map((repository) => ({
                        label: repository.label,
                        value: repository.id,
                      }))}
                      placeholder="请选择多个代码仓库"
                      showSearch
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    initialValue={['builtin']}
                    label="扫描引擎"
                    name={['config_json', 'scanner_engines']}
                  >
                    <Select
                      mode="multiple"
                      optionFilterProp="label"
                      options={codeInspectionScannerEngineOptions}
                      placeholder="请选择扫描引擎"
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    initialValue={['secrets', 'internal_addresses']}
                    label="内置规则"
                    name={['config_json', 'scan_rules']}
                  >
                    <Select
                      mode="multiple"
                      optionFilterProp="label"
                      options={codeInspectionBuiltinRuleOptions}
                      placeholder="请选择内置规则"
                    />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="严重级别阈值" name={['config_json', 'severity_threshold']}>
                    <Select
                      allowClear
                      options={severityThresholdOptions}
                      placeholder="默认 high"
                    />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    initialValue={true}
                    label="异步执行"
                    name={['config_json', 'async_execution']}
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="忽略目录" name={['config_json', 'ignore_dirs']}>
                    <Select mode="tags" placeholder="如 node_modules、dist、coverage" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="忽略规则" name={['config_json', 'ignore_rules']}>
                    <Select
                      mode="multiple"
                      optionFilterProp="label"
                      options={codeInspectionIgnoreRuleOptions}
                      placeholder="请选择要忽略的规则"
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="Baseline Fingerprints" name={['config_json', 'baseline_fingerprints']}>
                    <Select mode="tags" placeholder="粘贴历史问题 fingerprint，回车分隔" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="已接受风险 Fingerprints" name={['config_json', 'accepted_risk_fingerprints']}>
                    <Select mode="tags" placeholder="粘贴已接受风险 fingerprint，回车分隔" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="启用质量门禁"
                    name={['config_json', 'quality_gate', 'enabled']}
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col span={5}>
                  <Form.Item label="Critical 上限" name={['config_json', 'quality_gate', 'critical_max']}>
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={5}>
                  <Form.Item label="High 上限" name={['config_json', 'quality_gate', 'high_max']}>
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item label="Medium 上限" name={['config_json', 'quality_gate', 'medium_max']}>
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="增量基线 Commit" name={['config_json', 'incremental_from_commit']}>
                    <Input placeholder="留空表示全量扫描" />
                  </Form.Item>
                </Col>
              </Row>
            </FormSection>
          ) : null}
          <ScheduledJobAiExecutionSection
            agents={agents}
            executionModeOptions={executionModeOptions}
            knowledgeDocuments={knowledgeDocuments}
            modelGatewayConfigs={modelGatewayConfigs}
            requiredForAiAssembly={requiredForAiAssembly}
            skills={skills}
          />
          <ScheduledJobActionConfigSection
            codeInspectionResultActionOptions={codeInspectionResultActionOptions}
            isCodeInspectionJob={selectedJobType === 'code_repository_inspection'}
            pluginActions={pluginActions}
            requiredForPluginResource={requiredForPluginResource}
            severityThresholdOptions={severityThresholdOptions}
            usesNativeScan={selectedCodeInspectionUsesNativeScan}
            writeStrategyLabelFromAction={writeStrategyLabelFromAction}
          />
          <ScheduledJobScheduleConfigSection scheduleTypeOptions={scheduleTypeOptions} />
          {dryRunResult ? <ScheduledJobDryRunResultPanel result={dryRunResult} /> : null}
        </Form>
      </Modal>

      <Modal
        destroyOnHidden
        footer={(
          <Space>
            <Button
              onClick={() => {
                setSelectedRun(undefined);
                setLinkedResultWriteRecordId(undefined);
              }}
            >
              关闭
            </Button>
            {selectedRun?.status === 'succeeded' ? (
              <Button onClick={() => void generateTemplateFromRun(selectedRun)}>
                生成模板
              </Button>
            ) : null}
            {selectedRun ? (
              <Button
                aria-label="问 AI"
                href={assistantRunFollowupUrl(selectedRun)}
                icon={<RobotOutlined />}
              >
                问 AI
              </Button>
            ) : null}
            {selectedRun?.status === 'failed' ? (
              <>
                <Button
                  aria-label="继续诊断"
                  href={assistantRunFollowupUrl(selectedRun, assistantRunFollowupPrompt(selectedRun))}
                  icon={<RobotOutlined />}
                >
                  继续诊断
                </Button>
                <Button
                  aria-label="生成修复草案"
                  href={assistantRunFollowupUrl(selectedRun, assistantRunRepairDraftPrompt())}
                  icon={<EditOutlined />}
                >
                  生成修复草案
                </Button>
                <Button
                  aria-label="对比上次成功"
                  href={assistantRunFollowupUrl(selectedRun, assistantRunComparisonPrompt())}
                  icon={<ReloadOutlined />}
                >
                  对比上次成功
                </Button>
              </>
            ) : null}
            {selectedRun ? (
              <Button icon={<CopyOutlined />} type="primary" onClick={() => openCopyRunModal(selectedRun)}>
                复制本次配置
              </Button>
            ) : null}
          </Space>
        )}
        open={Boolean(selectedRun)}
        title="运行结果详情"
        width={980}
        onCancel={() => {
          setSelectedRun(undefined);
          setLinkedResultWriteRecordId(undefined);
        }}
      >
        {selectedRun ? (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions
              bordered
              column={2}
              size="small"
              items={[
                { key: 'id', label: '运行 ID', children: selectedRun.id },
                { key: 'status', label: '状态', children: selectedRun.status },
                {
                  key: 'job_type',
                  label: '作业类型',
                  children: selectedRunJobType ? jobTypeLabelByValue.get(selectedRunJobType) ?? selectedRunJobType : '-',
                },
                {
                  key: 'execution_mode',
                  label: 'AI执行',
                  children: selectedRunExecutionMode
                    ? executionModeLabelByValue.get(selectedRunExecutionMode) ?? selectedRunExecutionMode
                    : '-',
                },
                { key: 'model_gateway_config_id', label: 'AI 模型', children: selectedRunModelLabel },
                { key: 'agent_id', label: 'AI角色', children: selectedRunAgentLabel },
                { key: 'skill_ids', label: 'Skills', children: selectedRunSkillLabels },
                {
                  key: 'trigger_type',
                  label: '触发方式',
                  children: runTriggerTypeLabelByValue.get(String(selectedRun.trigger_type ?? '')) ?? selectedRun.trigger_type ?? '-',
                },
                { key: 'records_imported', label: '导入数', children: selectedRun.records_imported ?? 0 },
                { key: 'source_run_id', label: '复跑来源', children: selectedRun.source_run_id || '-' },
                {
                  key: 'template_source',
                  label: '模板来源',
                  children: (
                    <TemplateSourceSummary
                      source={templateSourceFromConfig(recordValue(selectedRun.config_snapshot?.config_json))}
                    />
                  ),
                },
                { key: 'collector_run_id', label: '采集运行', children: selectedRun.collector_run_id || '-' },
                { key: 'plugin_invocation_log_id', label: '插件调用', children: selectedRun.plugin_invocation_log_id || '-' },
                { key: 'scheduled_job_id', label: '作业 ID', children: selectedRun.scheduled_job_id || '-' },
                { key: 'started_at', label: '开始时间', children: formatDisplayDateTime(selectedRun.started_at) },
                { key: 'finished_at', label: '结束时间', children: formatDisplayDateTime(selectedRun.finished_at) },
                { key: 'error_code', label: '错误码', children: selectedRun.error_code || '-' },
                {
                  key: 'error_message',
                  label: '错误信息',
                  children: selectedRun.error_message || '-',
                },
              ]}
            />
            <RunSourceComparison run={selectedRun} />
            <RunExecutionChain run={selectedRun} />
            <RunTraceDag run={selectedRun} />
            <ScheduledJobRunResultWriteRecords
              focusedRecordId={linkedResultWriteRecordId}
              loading={selectedRunResultWriteRecordsLoading}
              records={selectedRunResultWriteRecords}
            />
            <JsonPreview
              title="数据连接获取内容"
              value={getRunExecutionNode(selectedRun, 'data_connection')}
            />
            <JsonPreview
              title="AI执行处理内容"
              value={getRunExecutionNode(selectedRun, 'skill_processing')}
            />
            <JsonPreview
              title="动作反馈内容"
              value={getRunExecutionNode(selectedRun, 'result_action')}
            />
            <JsonPreview
              title="代码巡检报告写入结果"
              value={getRunExecutionNode(selectedRun, 'code_inspection_report')}
            />
            <JsonPreview
              title="严重问题自动创建 Bug"
              value={getRunExecutionNode(selectedRun, 'bug_creation')}
            />
            <JsonPreview
              title="严重问题自动创建整改任务"
              value={getRunExecutionNode(selectedRun, 'task_creation')}
            />
            <JsonPreview
              title="问题消息通知"
              value={getRunExecutionNode(selectedRun, 'notifications')}
            />
            <JsonPreview title="动作执行状态" value={getRunExecutionNode(selectedRun, 'result_actions')} />
            <JsonPreview title="结果摘要" value={selectedRun.result_summary} />
            <JsonPreview title="插件快照" value={selectedRun.resolved_plugin_snapshot} />
            <JsonPreview title="Skill 快照" value={selectedRun.resolved_skill_snapshots} />
            <JsonPreview title="Prompt 快照" value={selectedRun.resolved_prompt_snapshot} />
            <JsonPreview title="作业配置快照" value={selectedRun.config_snapshot} />
          </Space>
        ) : null}
      </Modal>
    </PageContainer>
  );
}
