import {
  CopyOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import {
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Steps,
  Table,
  Tabs,
  Tag,
  Switch,
  Typography,
  message,
} from 'antd';
import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
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
  fetchScheduledJobTemplates,
  fetchScheduledJobRunObservability,
  fetchScheduledJobRuns,
  fetchScheduledJobs,
  generateScheduledJobTemplateFromRun,
  resolveAssistantDraftResourceId,
  runScheduledJob,
  testPluginConnection,
  updateScheduledJob,
  type AiAgentRecord,
  type AiSkillRecord,
  type AssistantScheduledJobDraft,
  type PluginActionRecord,
  type PluginConnectionTestResult,
  type PluginConnectionRecord,
  type ProductFilterOption,
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

type TemplateSourceView = {
  sourceId?: string;
  sourceType?: string;
  title?: string;
};

type ScheduledJobPageTab = 'jobs' | 'runs';

type ScheduledJobOrchestrationNode = {
  action?: ReactNode;
  details: string[];
  key: string;
  required?: boolean;
  status: string;
  statusColor: string;
  title: string;
};

type ScheduledJobTemplateWizardStep = NonNullable<ScheduledJobTemplateRecord['wizard_steps']>[number];

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

const templateSourceTypeLabelByValue = new Map([
  ['scheduled_job', '作业'],
  ['scheduled_job_run', '运行记录'],
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

const notificationChannelOptions = [
  { label: '邮件', value: 'email' },
  { label: '钉钉机器人', value: 'dingtalk' },
];

const defaultCodeInspectionResultActions: ScheduledJobResultAction[] = [
  { type: 'write_code_inspection_report' },
  { severity_threshold: 'critical', type: 'create_bug_for_severe_findings' },
  { severity_threshold: 'high', type: 'create_task_for_severe_findings' },
  { channels: ['email'], recipients: [], type: 'send_notification' },
];

const defaultScheduledJobWizardSteps: ScheduledJobTemplateWizardStep[] = [
  {
    description: '选择插件连接并完成取数测试',
    key: 'data_connection',
    required: true,
    title: '数据连接',
  },
  {
    description: '选择模型、AI角色和 Skill',
    key: 'ai_processing',
    required: false,
    title: 'AI执行',
  },
  {
    description: '可选引用知识内容',
    key: 'knowledge_reference',
    required: false,
    title: '知识引用',
  },
  {
    description: '选择写入或通知动作',
    key: 'result_write',
    required: true,
    title: '动作',
  },
  {
    description: '设置手动、Cron 或固定间隔',
    key: 'schedule',
    required: true,
    title: '调度',
  },
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
  const pluginActionIds = uniqueStringList([
    ...stringListFromDraftPayload(payload, 'plugin_action_ids'),
    resolvedPluginActionId,
  ]);
  const pluginConnectionIds = uniqueStringList([
    ...stringListFromDraftPayload(payload, 'plugin_connection_ids'),
    resolvedPluginConnectionId,
  ]);
  return {
    agent_id: stringFromDraftPayload(payload, 'agent_id'),
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
    skill_ids: stringListFromDraftPayload(payload, 'skill_ids'),
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

function isEmptyJsonValue(value: unknown): boolean {
  return (
    value == null
    || (Array.isArray(value) && value.length === 0)
    || (typeof value === 'object'
      && !Array.isArray(value)
      && Object.keys(value as Record<string, unknown>).length === 0)
  );
}

function formatJsonValue(value: unknown): string {
  if (isEmptyJsonValue(value)) {
    return '暂无数据';
  }
  return JSON.stringify(value, null, 2);
}

function JsonPreview({ title, value }: { title: string; value: unknown }) {
  return (
    <Space orientation="vertical" size={6} style={{ width: '100%' }}>
      <Typography.Text strong>{title}</Typography.Text>
      <Typography.Paragraph
        copyable={!isEmptyJsonValue(value)}
        style={{
          background: '#f6f8fa',
          border: '1px solid #e5e7eb',
          borderRadius: 6,
          marginBottom: 0,
          maxHeight: 260,
          overflow: 'auto',
          padding: 12,
          whiteSpace: 'pre-wrap',
        }}
      >
        {formatJsonValue(value)}
      </Typography.Paragraph>
    </Space>
  );
}

function resultWriteRecordFieldText(value: unknown): string {
  if (value === undefined || value === null || value === '') {
    return '-';
  }
  if (Array.isArray(value)) {
    return value.length ? value.map((item) => resultWriteRecordFieldText(item)).join('、') : '-';
  }
  if (typeof value === 'object') {
    return formatJsonValue(value);
  }
  return String(value);
}

function writeStrategyLabelFromAction(action: PluginActionRecord): string {
  const mapping = action.result_mapping ?? {};
  const writeTargetLabel = typeof mapping.write_target_label === 'string' ? mapping.write_target_label : undefined;
  const writeTarget = typeof mapping.write_target === 'string' ? mapping.write_target : undefined;
  const strategyLabel = writeTargetLabel ?? writeTarget ?? action.name;
  return `${strategyLabel} (${action.code})`;
}

function resultWriteRecordSummaryText(record: ResultWriteRecord) {
  const fields = record.summary_fields ?? {};
  const parts = [
    fields.subject ? `主题：${resultWriteRecordFieldText(fields.subject)}` : undefined,
    fields.delivery_status ? `状态：${resultWriteRecordFieldText(fields.delivery_status)}` : undefined,
    fields.delivery_id ? `ID：${resultWriteRecordFieldText(fields.delivery_id)}` : undefined,
    fields.sample_records?.length
      ? `样例：${resultWriteRecordFieldText(fields.sample_records)}`
      : undefined,
    fields.preview_value !== undefined
      ? `预览：${resultWriteRecordFieldText(fields.preview_value)}`
      : undefined,
  ].filter(Boolean);
  return parts.length ? parts.join(' / ') : '-';
}

function resultWriteRecordSourceLabel(sourceType?: string) {
  if (sourceType === 'scheduled_job_run') {
    return '定时作业运行';
  }
  if (sourceType === 'plugin_invocation_log') {
    return '插件调用日志';
  }
  return sourceType || '-';
}

function resultWriteRecordStatusColor(status?: string) {
  if (status === 'succeeded') {
    return 'green';
  }
  if (status === 'failed') {
    return 'red';
  }
  if (status === 'not_run') {
    return 'default';
  }
  return 'blue';
}

function RunResultWriteRecords({
  loading,
  records,
}: {
  loading: boolean;
  records: ResultWriteRecord[];
}) {
  return (
    <Space orientation="vertical" size={8} style={{ width: '100%' }}>
      <Typography.Text strong>结果写入记录</Typography.Text>
      <Table<ResultWriteRecord>
        columns={[
          {
            dataIndex: 'write_target_label',
            title: '写入目标',
            width: 160,
            render: (_, record) => (
              <Tag color="blue">{record.write_target_label || record.write_target}</Tag>
            ),
          },
          {
            dataIndex: 'status',
            title: '状态',
            width: 110,
            render: (value) => (
              <Tag color={resultWriteRecordStatusColor(String(value ?? ''))}>{String(value ?? '-')}</Tag>
            ),
          },
          {
            key: 'source',
            title: '来源',
            width: 180,
            render: (_, record) => resultWriteRecordSourceLabel(record.source_type),
          },
          {
            key: 'summary',
            title: '写入摘要',
            ellipsis: true,
            render: (_, record) => resultWriteRecordSummaryText(record),
          },
          { dataIndex: 'records_imported', title: '写入数', width: 90 },
          {
            dataIndex: 'plugin_invocation_log_id',
            title: '调用日志',
            ellipsis: true,
            width: 190,
            render: (value) => value || '-',
          },
          {
            dataIndex: 'created_at',
            title: '时间',
            ellipsis: true,
            width: 210,
            render: (value) => value || '-',
          },
        ]}
        dataSource={records}
        expandable={{
          expandedRowRender: (record) => (
            <Space orientation="vertical" size={10} style={{ width: '100%' }}>
              <JsonPreview title="结果摘要字段" value={record.summary_fields} />
              <JsonPreview title="写入预览" value={record.preview} />
              <JsonPreview title="执行反馈" value={record.feedback} />
            </Space>
          ),
        }}
        loading={loading}
        locale={{ emptyText: '暂无结果写入记录' }}
        pagination={false}
        rowKey="id"
        scroll={{ x: 1040 }}
        size="small"
      />
    </Space>
  );
}

function FormSection({
  children,
  label,
  marker,
}: {
  children: ReactNode;
  label: string;
  marker: string;
}) {
  return (
    <div
      aria-label={label}
      style={{
        borderTop: '1px solid #e5e7eb',
        paddingTop: 14,
      }}
    >
      <Space orientation="vertical" size={10} style={{ width: '100%' }}>
        <Space align="center" size={8}>
          <Tag color="blue">{marker}</Tag>
          <Typography.Text strong>{label}</Typography.Text>
        </Space>
        {children}
      </Space>
    </div>
  );
}

function wizardStepNodeKey(stepKey: string): string {
  if (stepKey === 'result_write') {
    return 'result_action';
  }
  return stepKey;
}

function wizardStepDisplayTitle(step: ScheduledJobTemplateWizardStep): string {
  if (step.key === 'ai_processing' || step.title === 'AI 处理') {
    return 'AI执行';
  }
  if (step.key === 'result_write' || step.title === '结果写入') {
    return '动作';
  }
  return step.title;
}

function wizardStepCurrentIndex(
  steps: ScheduledJobTemplateWizardStep[],
  nodes: ScheduledJobOrchestrationNode[],
) {
  const firstPendingIndex = steps.findIndex((step) => {
    if (!step.required) {
      return false;
    }
    if (step.key === 'schedule') {
      return false;
    }
    const node = nodes.find((item) => item.key === wizardStepNodeKey(step.key));
    return Boolean(node && node.status !== '已配置' && node.status !== '已选择');
  });
  return firstPendingIndex >= 0 ? firstPendingIndex : Math.max(steps.length - 1, 0);
}

function ScheduledJobOrchestrationFlow({
  nodes,
  wizardSteps = defaultScheduledJobWizardSteps,
}: {
  nodes: ScheduledJobOrchestrationNode[];
  wizardSteps?: ScheduledJobTemplateWizardStep[];
}) {
  const steps = wizardSteps.length ? wizardSteps : defaultScheduledJobWizardSteps;
  return (
    <Space
      aria-label="执行链路"
      orientation="vertical"
      size={10}
      style={{
        background: '#f8fafc',
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        marginBottom: 16,
        padding: 12,
        width: '100%',
      }}
    >
      <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }} wrap>
        <Typography.Text strong>执行链路</Typography.Text>
        <Typography.Text type="secondary">执行链路：数据连接 → AI执行 → 动作 → 运行记录</Typography.Text>
      </Space>
      <Steps
        current={wizardStepCurrentIndex(steps, nodes)}
        items={steps.map((step) => ({
          content: (
            <Space size={4} wrap>
              <Tag color={step.required ? 'orange' : 'default'}>{step.required ? '必填' : '可选'}</Tag>
              {step.description ? <Typography.Text type="secondary">{step.description}</Typography.Text> : null}
            </Space>
          ),
          title: wizardStepDisplayTitle(step),
        }))}
        size="small"
      />
      <div
        style={{
          display: 'grid',
          gap: 10,
          gridTemplateColumns: 'repeat(auto-fit, minmax(155px, 1fr))',
        }}
      >
        {nodes.map((node) => (
          <div
            aria-label={`编排节点 ${node.title}`}
            key={node.key}
            style={{
              background: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              minHeight: 142,
              padding: 10,
            }}
          >
            <Space orientation="vertical" size={8} style={{ width: '100%' }}>
              <Space align="center" wrap>
                <Tag color={node.statusColor}>{node.status}</Tag>
                <Typography.Text strong>{node.title}</Typography.Text>
                {node.required ? <Tag color="orange">必填</Tag> : <Tag>可选</Tag>}
              </Space>
              <Space orientation="vertical" size={4} style={{ minHeight: 46, width: '100%' }}>
                {node.details.length > 0 ? (
                  node.details.map((detail, index) => (
                    <Typography.Text
                      ellipsis={{ tooltip: detail }}
                      key={`${node.key}-${index}-${detail}`}
                      style={{ maxWidth: '100%' }}
                      type="secondary"
                    >
                      {detail}
                    </Typography.Text>
                  ))
                ) : (
                  <Typography.Text type="secondary">尚未选择</Typography.Text>
                )}
              </Space>
              {node.action}
            </Space>
          </div>
        ))}
      </div>
    </Space>
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function getRunExecutionNode(run: ScheduledJobRunRecord, nodeKey: string): unknown {
  const nodes = run.result_summary?.execution_nodes;
  if (isRecord(nodes)) {
    return nodes[nodeKey];
  }
  return undefined;
}

function nodeFieldText(value: unknown): string | undefined {
  if (typeof value === 'string' && value) {
    return value;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return undefined;
}

function nodeNestedValue(node: Record<string, unknown>, path: string): unknown {
  return path.split('.').reduce<unknown>((current, key) => {
    if (!isRecord(current)) {
      return undefined;
    }
    return current[key];
  }, node);
}

function nodeNestedFieldText(node: Record<string, unknown>, path: string): string | undefined {
  const value = nodeNestedValue(node, path);
  if (Array.isArray(value)) {
    const primitiveValues = value.filter((item) => ['string', 'number', 'boolean'].includes(typeof item));
    return primitiveValues.length ? primitiveValues.join('、') : undefined;
  }
  return nodeFieldText(value);
}

function nodeNestedArrayCountText(node: Record<string, unknown>, path: string): string | undefined {
  const value = nodeNestedValue(node, path);
  return Array.isArray(value) ? String(value.length) : undefined;
}

function runNodeTagColor(status: string | undefined): string {
  if (status === 'succeeded') {
    return 'green';
  }
  if (status === 'failed') {
    return 'red';
  }
  if (status === 'skipped') {
    return 'default';
  }
  return 'blue';
}

function templateSourceFromConfig(configJson: Record<string, unknown> | undefined): TemplateSourceView | undefined {
  const rawTemplateSource = configJson?.template_source;
  if (!isRecord(rawTemplateSource)) {
    return undefined;
  }
  const source = {
    sourceId: nodeFieldText(rawTemplateSource.source_id),
    sourceType: nodeFieldText(rawTemplateSource.source_type),
    title: nodeFieldText(rawTemplateSource.title),
  };
  return source.sourceId || source.sourceType || source.title ? source : undefined;
}

function templateSourceDisplayText(source: TemplateSourceView): string {
  const title = source.title || source.sourceId || '-';
  return source.sourceId && source.sourceId !== title ? `${title} (${source.sourceId})` : title;
}

function TemplateSourceSummary({ source }: { source: TemplateSourceView | undefined }) {
  if (!source) {
    return <Typography.Text type="secondary">-</Typography.Text>;
  }
  const typeLabel = templateSourceTypeLabelByValue.get(String(source.sourceType ?? '')) ?? source.sourceType ?? '模板';
  const displayText = templateSourceDisplayText(source);
  return (
    <Space
      aria-label={`模板来源 ${source.sourceId ?? source.title ?? source.sourceType ?? 'unknown'}`}
      size={6}
      style={{ maxWidth: '100%' }}
    >
      <Tag color={source.sourceType === 'scheduled_job_run' ? 'purple' : 'blue'}>{typeLabel}</Tag>
      <Typography.Text ellipsis={{ tooltip: displayText }} style={{ maxWidth: 180 }}>
        {displayText}
      </Typography.Text>
    </Space>
  );
}

function RunExecutionNodeCard({
  nodeKey,
  title,
  value,
}: {
  nodeKey: string;
  title: string;
  value: unknown;
}) {
  const node = isRecord(value) ? value : {};
  const status = nodeFieldText(node.status) ?? (isEmptyJsonValue(value) ? '暂无数据' : 'available');
  const metrics = [
    { label: '请求方法', value: nodeFieldText(node.request_method) ?? nodeNestedFieldText(node, 'request_summary.method') ?? nodeNestedFieldText(node, 'request_summary.request_preview.method') },
    { label: '请求 URL', value: nodeFieldText(node.request_url) ?? nodeNestedFieldText(node, 'request_summary.url') ?? nodeNestedFieldText(node, 'request_summary.request_preview.url') },
    { label: 'HTTP 状态', value: nodeFieldText(node.response_status_code) ?? nodeNestedFieldText(node, 'response_summary.status_code') },
    { label: '耗时 ms', value: nodeFieldText(node.latency_ms) },
    { label: '模型调用', value: typeof node.model_gateway_called === 'boolean' ? (node.model_gateway_called ? '已调用' : '未调用') : undefined },
    { label: '处理模式', value: nodeFieldText(node.processing_mode) },
    { label: '模型配置', value: nodeFieldText(node.model_gateway_config_id) },
    { label: '模型日志', value: nodeFieldText(node.model_log_id) ?? nodeFieldText(node.model_gateway_log_id) },
    { label: '知识引用', value: nodeNestedArrayCountText(node, 'input.knowledge_references') },
    { label: '候选结果', value: nodeNestedFieldText(node, 'output.candidate_count') ?? nodeNestedFieldText(node, 'output.finding_count') },
    { label: '风险等级', value: nodeNestedFieldText(node, 'output.risk_level') },
    { label: '写入目标', value: nodeFieldText(node.write_target_label) ?? nodeFieldText(node.write_target) },
    { label: nodeKey === 'data_connection' ? '行数' : '写入数量', value: nodeFieldText(node.records_imported) },
    { label: '跳过数量', value: nodeFieldText(node.skipped_insights) ?? nodeNestedFieldText(node, 'feedback.skipped_insights') },
    { label: '报告 ID', value: nodeNestedFieldText(node, 'feedback.report_id') ?? nodeFieldText(node.report_id) },
    { label: '创建记录', value: nodeNestedFieldText(node, 'feedback.created_ids') ?? nodeNestedFieldText(node, 'created_ids') },
    { label: 'Bug 数量', value: nodeNestedArrayCountText(node, 'feedback.bug_ids') ?? nodeNestedArrayCountText(node, 'created_bug_ids') },
    { label: '任务数量', value: nodeNestedArrayCountText(node, 'feedback.task_ids') ?? nodeNestedArrayCountText(node, 'created_task_ids') },
    { label: '整改任务', value: nodeNestedFieldText(node, 'feedback.task_ids') ?? nodeNestedFieldText(node, 'created_task_ids') },
    { label: '通知数量', value: nodeNestedArrayCountText(node, 'feedback.notification_ids') ?? nodeNestedArrayCountText(node, 'created_notification_ids') },
    { label: '投递 ID', value: nodeNestedFieldText(node, 'feedback.delivery_id') },
    { label: '投递状态', value: nodeNestedFieldText(node, 'feedback.delivery_status') },
    { label: '收件人', value: nodeNestedFieldText(node, 'feedback.sample_records') },
    { label: '执行器', value: nodeFieldText(node.executor_type) },
    { label: '执行器实例', value: nodeFieldText(node.runner_id) },
    { label: '任务 ID', value: nodeFieldText(node.runner_task_id) },
    { label: '工作区', value: nodeFieldText(node.workspace_root) },
    { label: '完成时间', value: nodeFieldText(node.finished_at) },
    { label: '日志条数', value: nodeNestedArrayCountText(node, 'logs') },
    { label: '执行结果', value: nodeNestedFieldText(node, 'result_json.summary') ?? nodeNestedFieldText(node, 'result_json.result') },
    { label: '源数据量', value: nodeFieldText(node.source_row_count) ?? nodeFieldText(node.row_count) },
    { label: '连接', value: nodeFieldText(node.connection_id) },
    { label: '环境', value: nodeFieldText(node.connection_environment) },
    { label: '动作', value: nodeFieldText(node.action_id) },
    { label: '失败原因', value: nodeFieldText(node.error_message) },
  ].filter((item) => item.value);

  return (
    <div
      aria-label={`流程节点 ${title}`}
      style={{
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        minHeight: 132,
        padding: 12,
      }}
    >
      <Space orientation="vertical" size={8} style={{ width: '100%' }}>
        <Space align="center" wrap>
          <Tag color={runNodeTagColor(status)}>{status}</Tag>
          <Typography.Text strong>{title}</Typography.Text>
        </Space>
        {metrics.length > 0 ? (
          <Space orientation="vertical" size={4} style={{ width: '100%' }}>
            {metrics.map((item) => (
              <div key={`${nodeKey}-${item.label}`} style={{ display: 'flex', gap: 8 }}>
                <Typography.Text style={{ color: '#64748b', minWidth: 72 }}>{item.label}</Typography.Text>
                <Typography.Text
                  ellipsis={{ tooltip: item.value }}
                  style={{ flex: 1, minWidth: 0 }}
                >
                  {item.value}
                </Typography.Text>
              </div>
            ))}
          </Space>
        ) : (
          <Typography.Text type="secondary">暂无节点摘要</Typography.Text>
        )}
      </Space>
    </div>
  );
}

function RunExecutionChain({ run }: { run: ScheduledJobRunRecord }) {
  const nodes = [
    { key: 'data_connection', title: '数据连接获取内容' },
    ...(getRunExecutionNode(run, 'runner_execution')
      ? [{ key: 'runner_execution', title: 'AI 执行器执行内容' }]
      : []),
    { key: 'skill_processing', title: 'AI执行处理内容' },
    { key: 'result_action', title: '动作反馈内容' },
    ...(getRunExecutionNode(run, 'task_creation')
      ? [{ key: 'task_creation', title: '整改任务创建反馈' }]
      : []),
  ];
  return (
    <Space orientation="vertical" size={10} style={{ width: '100%' }}>
      <Typography.Text strong>运行链路</Typography.Text>
      <div
        style={{
          display: 'grid',
          gap: 12,
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        }}
      >
        {nodes.map((node) => (
          <RunExecutionNodeCard
            key={node.key}
            nodeKey={node.key}
            title={node.title}
            value={getRunExecutionNode(run, node.key)}
          />
        ))}
      </div>
    </Space>
  );
}

function RunTraceDag({ run }: { run: ScheduledJobRunRecord }) {
  const traceGraph = isRecord(run.result_summary?.trace_graph) ? run.result_summary.trace_graph : undefined;
  const nodes = Array.isArray(traceGraph?.nodes)
    ? traceGraph.nodes.filter(isRecord)
    : [];
  const edges = Array.isArray(traceGraph?.edges)
    ? traceGraph.edges.filter(isRecord)
    : [];
  if (!nodes.length && !edges.length) {
    return null;
  }
  return (
    <Space orientation="vertical" size={10} style={{ width: '100%' }}>
      <Typography.Text strong>运行 Trace DAG</Typography.Text>
      <div
        style={{
          display: 'grid',
          gap: 12,
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        }}
      >
        {nodes.map((node) => {
          const id = nodeFieldText(node.id) ?? nodeFieldText(node.label) ?? 'trace_node';
          const label = nodeFieldText(node.label) ?? id;
          const duration = typeof node.duration_ms === 'number' ? `${node.duration_ms}ms` : '-';
          const retryCount = typeof node.retry_count === 'number' ? node.retry_count : 0;
          const error = nodeFieldText(node.error);
          const status = nodeFieldText(node.status) ?? 'unknown';
          return (
            <div
              aria-label={`Trace 节点 ${label}`}
              key={id}
              style={{
                border: '1px solid #dbeafe',
                borderRadius: 8,
                background: '#f8fbff',
                padding: 12,
              }}
            >
              <Space orientation="vertical" size={8} style={{ width: '100%' }}>
                <Space wrap>
                  <Tag color={runNodeTagColor(status)}>{status}</Tag>
                  <Typography.Text strong>{label}</Typography.Text>
                </Space>
                <Space wrap size={8}>
                  <Tag color="blue">{duration}</Tag>
                  <Tag>重试 {retryCount}</Tag>
                  {error ? <Tag color="red">{error}</Tag> : null}
                </Space>
                <Typography.Paragraph
                  style={{
                    background: '#fff',
                    border: '1px solid #e5e7eb',
                    borderRadius: 6,
                    marginBottom: 0,
                    maxHeight: 120,
                    overflow: 'auto',
                    padding: 8,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {formatJsonValue({ input: node.input, output: node.output })}
                </Typography.Paragraph>
              </Space>
            </div>
          );
        })}
      </div>
      {edges.length ? (
        <Space wrap>
          {edges.map((edge, index) => {
            const from = nodeFieldText(edge.from) ?? '-';
            const to = nodeFieldText(edge.to) ?? '-';
            return <Tag key={`${from}-${to}-${index}`}>{from} → {to}</Tag>;
          })}
        </Space>
      ) : null}
    </Space>
  );
}

function RunSourceComparison({ run }: { run: ScheduledJobRunRecord }) {
  const source = run.source_run_summary;
  if (!source) {
    return null;
  }
  return (
    <Space orientation="vertical" size={8} style={{ width: '100%' }}>
      <Typography.Text strong>复跑对比</Typography.Text>
      <Descriptions
        bordered
        column={2}
        size="small"
        items={[
          { key: 'source_id', label: '来源运行', children: source.id || run.source_run_id || '-' },
          {
            key: 'source_trigger_type',
            label: '来源触发',
            children: runTriggerTypeLabelByValue.get(String(source.trigger_type ?? '')) ?? source.trigger_type ?? '-',
          },
          { key: 'source_status', label: '来源状态', children: source.status || '-' },
          { key: 'current_status', label: '本次状态', children: run.status || '-' },
          { key: 'source_records_imported', label: '来源导入数', children: source.records_imported ?? 0 },
          { key: 'current_records_imported', label: '本次导入数', children: run.records_imported ?? 0 },
          { key: 'source_error_code', label: '来源错误码', children: source.error_code || '-' },
          { key: 'source_latency_ms', label: '来源耗时 ms', children: source.latency_ms ?? '-' },
        ]}
      />
    </Space>
  );
}

function metricNumber(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function distributionText(items: Array<Record<string, unknown>> | undefined, key: string): string {
  if (!items?.length) {
    return '-';
  }
  return items
    .slice(0, 3)
    .map((item) => `${String(item[key] ?? '-')}: ${String(item.count ?? 0)}`)
    .join(' / ');
}

type ObservabilityFailureRow = NonNullable<ScheduledJobRunObservability['recent_failures']>[number];
type ObservabilitySlowRunRow = NonNullable<ScheduledJobRunObservability['slow_runs']>[number];

function ScheduledJobRunObservabilityOverview({
  loading,
  observability,
}: {
  loading: boolean;
  observability?: ScheduledJobRunObservability;
}) {
  const summary = observability?.summary ?? {};
  const recentFailures = observability?.recent_failures ?? [];
  const slowRuns = observability?.slow_runs ?? [];

  return (
    <Space orientation="vertical" size={12} style={{ marginBottom: 16, width: '100%' }}>
      <Row gutter={[12, 12]}>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic title="总运行数" value={metricNumber(summary.total_runs)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic precision={2} suffix="%" title="成功率" value={metricNumber(summary.success_rate)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic precision={2} suffix="%" title="失败率" value={metricNumber(summary.failure_rate)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic precision={0} suffix="ms" title="平均耗时" value={metricNumber(summary.average_latency_ms)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic title="AI 调用次数" value={metricNumber(summary.model_gateway_called_runs)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic title="Token 总量" value={metricNumber(summary.model_gateway_token_total)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic title="插件调用次数" value={metricNumber(summary.plugin_invocation_runs)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic
              precision={2}
              suffix="%"
              title="结果写入成功率"
              value={metricNumber(summary.action_write_success_rate)}
            />
          </Card>
        </Col>
      </Row>
      <Card
        size="small"
        title="运行健康概览"
        loading={loading}
      >
        <Descriptions
          column={{ lg: 3, md: 2, xs: 1 }}
          size="small"
          items={[
            {
              key: 'status_distribution',
              label: '状态分布',
              children: distributionText(observability?.status_distribution, 'status'),
            },
            {
              key: 'job_type_distribution',
              label: '作业类型',
              children: distributionText(observability?.job_type_distribution, 'job_type'),
            },
            {
              key: 'trigger_type_distribution',
              label: '触发方式',
              children: distributionText(observability?.trigger_type_distribution, 'trigger_type'),
            },
            {
              key: 'write_target_distribution',
              label: '写入目标',
              children: distributionText(observability?.write_target_distribution, 'write_target'),
            },
            {
              key: 'error_distribution',
              label: '失败原因',
              children: distributionText(observability?.error_distribution, 'error'),
            },
            {
              key: 'average_records_imported',
              label: '平均导入数',
              children: metricNumber(summary.average_records_imported),
            },
          ]}
        />
      </Card>
      <Row gutter={[12, 12]}>
        <Col lg={12} xs={24}>
          <Card size="small" title="最近失败">
            <Table<ObservabilityFailureRow>
              columns={[
                { dataIndex: 'id', ellipsis: true, title: '运行 ID', width: 190 },
                { dataIndex: 'job_name', ellipsis: true, title: '作业', width: 170 },
                { dataIndex: 'error_code', ellipsis: true, title: '错误码', width: 140, render: (value) => value || '-' },
                { dataIndex: 'error_message', ellipsis: true, title: '错误信息', render: (value) => value || '-' },
              ]}
              dataSource={recentFailures}
              locale={{ emptyText: '暂无失败记录' }}
              pagination={false}
              rowKey="id"
              scroll={{ x: 680 }}
              size="small"
            />
          </Card>
        </Col>
        <Col lg={12} xs={24}>
          <Card size="small" title="慢运行">
            <Table<ObservabilitySlowRunRow>
              columns={[
                { dataIndex: 'id', ellipsis: true, title: '运行 ID', width: 190 },
                { dataIndex: 'job_name', ellipsis: true, title: '作业', width: 170 },
                { dataIndex: 'latency_ms', title: '耗时 ms', width: 110, render: (value) => value ?? '-' },
                { dataIndex: 'records_imported', title: '导入数', width: 90, render: (value) => value ?? 0 },
                {
                  dataIndex: 'status',
                  title: '状态',
                  width: 100,
                  render: (value) => <Tag color={runNodeTagColor(String(value ?? ''))}>{String(value ?? '-')}</Tag>,
                },
              ]}
              dataSource={slowRuns}
              locale={{ emptyText: '暂无慢运行记录' }}
              pagination={false}
              rowKey="id"
              scroll={{ x: 660 }}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </Space>
  );
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

function scheduledJobRouteParams(): { runId?: string; tab?: ScheduledJobPageTab } {
  if (typeof window === 'undefined') {
    return { runId: undefined, tab: undefined };
  }
  const params = new URLSearchParams(window.location.search);
  const tab = params.get('tab') === 'runs' ? 'runs' : params.get('tab') === 'jobs' ? 'jobs' : undefined;
  return {
    runId: params.get('run_id') ?? undefined,
    tab,
  };
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
  const [agents, setAgents] = useState<AiAgentRecord[]>([]);
  const [skills, setSkills] = useState<AiSkillRecord[]>([]);
  const [knowledgeDocuments, setKnowledgeDocuments] = useState<KnowledgeRecord[]>([]);
  const [modelGatewayConfigs, setModelGatewayConfigs] = useState<ModelGatewayConfigRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingJob, setEditingJob] = useState<ScheduledJobRecord | undefined>();
  const [assistantDraftPayload, setAssistantDraftPayload] = useState<Record<string, unknown> | undefined>();
  const [assistantDraftSource, setAssistantDraftSource] = useState<
    Pick<AssistantScheduledJobDraft, 'draftId' | 'title'> | undefined
  >();
  const [activeTab, setActiveTab] = useState<ScheduledJobPageTab>(initialScheduledJobPageTab);
  const [handledRouteRunId, setHandledRouteRunId] = useState<string | undefined>();
  const [templateSource, setTemplateSource] = useState<ScheduledJobTemplateSource | undefined>();
  const [selectedRun, setSelectedRun] = useState<ScheduledJobRunRecord | undefined>();
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
  const selectedTemplateCode = Form.useWatch('template', form);
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
  const jobById = useMemo(
    () => new Map(jobs.map((job) => [job.id, job])),
    [jobs],
  );
  const filteredPluginConnections = useMemo(
    () =>
      pluginConnections.filter(
        (connection) =>
          !selectedConnectionEnvironment
          || (connection.environment ?? 'default') === selectedConnectionEnvironment,
      ),
    [pluginConnections, selectedConnectionEnvironment],
  );
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
    if (!selectedConnectionEnvironment || normalizedSelectedPluginConnectionIds.length === 0) {
      return;
    }
    const nextConnectionIds = normalizedSelectedPluginConnectionIds.filter((connectionId) => {
      const connection = pluginConnectionById.get(connectionId);
      return connection && (connection.environment ?? 'default') === selectedConnectionEnvironment;
    });
    if (nextConnectionIds.length !== normalizedSelectedPluginConnectionIds.length) {
      form.setFieldValue('plugin_connection_ids', nextConnectionIds);
      form.setFieldValue('plugin_connection_id', primaryId(nextConnectionIds));
    }
  }, [form, normalizedSelectedPluginConnectionIds, pluginConnectionById, selectedConnectionEnvironment]);

  useEffect(() => {
    setConnectionTestResult(undefined);
  }, [selectedPrimaryPluginConnectionId]);

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
    const connectionRequired = pluginRequiredJobTypes.includes(jobType);
    const actionRequired = pluginRequiredJobTypes.includes(jobType);
    const aiRequired = requiresAiAssembly(selectedJobType, selectedExecutionMode);
    const dataStatus = selectedConnections.length > 0 ? '已配置' : connectionRequired ? '待配置' : '可选';
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
        statusColor: dataStatus === '已配置' ? 'green' : connectionRequired ? 'orange' : 'default',
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
      const executionMode = templatePayloadString(template, 'execution_mode') ?? 'deterministic';
      const aiRequired = requiresAiAssembly(jobType, executionMode);
      form.setFieldsValue({
        agent_id: aiRequired ? agentId : undefined,
        config_json: templatePayloadRecordValue(template, 'config_json') ?? {},
        connection_environment: primaryConnection?.environment ?? undefined,
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
        plugin_action_id: primaryId(pluginActionIds),
        plugin_action_ids: pluginActionIds,
        plugin_connection_id: primaryId(pluginConnectionIds),
        plugin_connection_ids: pluginConnectionIds,
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
    void reload();
  }, [reload]);

  useEffect(() => {
    const routeParams = scheduledJobRouteParams();
    if (routeParams.tab) {
      setActiveTab(routeParams.tab);
    }
    if (!routeParams.runId || handledRouteRunId === routeParams.runId) {
      return;
    }
    const routeRun = runs.find((run) => run.id === routeParams.runId);
    if (!routeRun) {
      return;
    }
    setActiveTab('runs');
    setSelectedRun(routeRun);
    setHandledRouteRunId(routeParams.runId);
  }, [handledRouteRunId, runs]);

  useEffect(() => {
    if (!selectedRun?.id) {
      setSelectedRunResultWriteRecords([]);
      setSelectedRunResultWriteRecordsLoading(false);
      return;
    }
    let ignore = false;
    setSelectedRunResultWriteRecordsLoading(true);
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
    const rawDraft = window.sessionStorage.getItem(ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY);
    if (!rawDraft) {
      return;
    }
    window.sessionStorage.removeItem(ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY);
    try {
      const draft = JSON.parse(rawDraft) as AssistantScheduledJobDraft;
      if (!draft.payload || typeof draft.payload !== 'object' || Array.isArray(draft.payload)) {
        throw new Error('Invalid scheduled job draft payload');
      }
      const draftValues = scheduledJobValuesFromAssistantDraft(draft);
      setEditingJob(undefined);
      setAssistantDraftPayload(draft.payload);
      setAssistantDraftSource({ draftId: draft.draftId, title: draft.title });
      setConnectionTestResult(undefined);
      form.resetFields();
      form.setFieldsValue(draftValues);
      setModalOpen(true);
      message.success('已载入 AI 助手生成的定时作业草案，请确认后保存');
    } catch {
      setAssistantDraftPayload(undefined);
      setAssistantDraftSource(undefined);
      message.error('AI 助手定时作业草案格式无效');
    }
  }, [editingJob, form, modalOpen]);

  const openCreateJobModal = () => {
    setEditingJob(undefined);
    setAssistantDraftPayload(undefined);
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
    setEditingJob(undefined);
    setAssistantDraftPayload(undefined);
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
      setEditingJob(undefined);
      setAssistantDraftPayload(undefined);
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
    setEditingJob(job);
    setAssistantDraftPayload(undefined);
    setAssistantDraftSource(undefined);
    setTemplateSource(undefined);
    setGeneratedRunTemplate(undefined);
    setConnectionTestResult(undefined);
    setDryRunResult(undefined);
    form.resetFields();
    form.setFieldsValue({
      agent_id: job.agent_id ?? undefined,
      connection_environment: primaryConnectionId
        ? pluginConnectionById.get(primaryConnectionId)?.environment ?? 'default'
        : undefined,
      config_json: job.config_json ?? {},
      cron_expression: job.cron_expression ?? undefined,
      enabled: job.enabled ?? true,
      execution_mode: job.execution_mode ?? 'deterministic',
      interval_seconds: job.interval_seconds ?? undefined,
      job_type: job.job_type,
      knowledge_document_ids: job.knowledge_document_ids ?? [],
      model_gateway_config_id: job.model_gateway_config_id ?? undefined,
      name: job.name,
      plugin_action_id: primaryId(pluginActionIds),
      plugin_action_ids: pluginActionIds,
      plugin_connection_id: primaryConnectionId,
      plugin_connection_ids: pluginConnectionIds,
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
    const pluginConnectionIds = uniqueStringList([
      ...(values.plugin_connection_ids ?? []),
      values.plugin_connection_id,
    ]);
    const pluginActionIds = uniqueStringList([
      ...(values.plugin_action_ids ?? []),
      values.plugin_action_id,
    ]);
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
    try {
      requestPayload = await currentValidatedJobPayload();
    } catch {
      return;
    }
    if (editingJob) {
      await updateScheduledJob(editingJob.id, requestPayload);
      message.success('定时作业已更新');
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
      setSelectedRun(run);
      message.success('作业运行完成');
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
                  { dataIndex: 'next_run_at', title: '下次运行', width: 180, render: (value) => ellipsisText(String(value ?? '')) },
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
                            onClick={() => setSelectedRun(row)}
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
                          execution_mode: 'deterministic',
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
          <FormSection label="数据连接配置" marker="输入">
            <Row gutter={12}>
              <Col span={8}>
                <Form.Item label="连接环境" name="connection_environment">
                  <Select
                    allowClear
                    options={connectionEnvironmentOptions}
                    placeholder="筛选数据连接环境"
                    onChange={() => {
                      form.setFieldValue('plugin_connection_id', undefined);
                      form.setFieldValue('plugin_connection_ids', []);
                    }}
                  />
                </Form.Item>
              </Col>
              <Col span={16}>
                <Form.Item
                  label="数据连接"
                  name="plugin_connection_ids"
                  rules={[requiredForJobTypes(pluginRequiredJobTypes, '请选择数据连接')]}
                  extra="可选择多个连接，运行时按配置顺序作为数据来源"
                >
                  <Select
                    allowClear
                    mode="multiple"
                    maxTagCount={2}
                    optionFilterProp="label"
                    placeholder="请选择取数连接"
                    showSearch
                    options={filteredPluginConnections.map((connection) => ({
                      label: `${connection.name} (${connection.environment ?? 'default'})`,
                      value: connection.id,
                    }))}
                  />
                </Form.Item>
              </Col>
            </Row>
          </FormSection>
          <FormSection label="AI执行配置" marker="处理">
            <Row gutter={12}>
              <Col span={8}>
                <Form.Item label="AI执行" name="execution_mode">
                  <Select options={executionModeOptions} />
                </Form.Item>
              </Col>
              <Col span={16}>
                <Form.Item
                  dependencies={['execution_mode', 'job_type']}
                  label="AI 模型"
                  name="model_gateway_config_id"
                  rules={[requiredForAiAssembly('请选择 AI 模型')]}
                >
                  <Select
                    allowClear
                    optionFilterProp="label"
                    placeholder="请选择 AI 模型"
                    showSearch
                    options={modelGatewayConfigs.map((config) => ({
                      label: `${config.name} (${config.defaultChatModel})`,
                      value: config.id,
                    }))}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  dependencies={['execution_mode', 'job_type']}
                  label="AI角色"
                  name="agent_id"
                  rules={[requiredForAiAssembly('请选择 AI角色')]}
                >
                  <Select
                    allowClear
                    optionFilterProp="label"
                    placeholder="请选择 AI角色"
                    showSearch
                    options={agents.map((agent) => ({
                      label: `${agent.name} (${agent.code})`,
                      value: agent.id,
                    }))}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  dependencies={['execution_mode', 'job_type']}
                  label="Skills"
                  name="skill_ids"
                  rules={[requiredForAiAssembly('请选择 Skills')]}
                >
                  <Select
                    allowClear
                    mode="multiple"
                    optionFilterProp="label"
                    placeholder="请选择 Skills"
                    showSearch
                    options={skills.map((skill) => ({
                      label: `${skill.name} (${skill.code})`,
                      value: skill.id,
                    }))}
                  />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item label="知识引用" name="knowledge_document_ids">
                  <Select
                    allowClear
                    mode="multiple"
                    optionFilterProp="label"
                    placeholder="请选择知识文档"
                    showSearch
                    options={knowledgeDocuments.map((document) => ({
                      label: `${document.title} (${document.documentType})`,
                      value: document.id,
                    }))}
                  />
                </Form.Item>
              </Col>
            </Row>
          </FormSection>
          <FormSection label="动作配置" marker="输出">
            <Form.Item
              label="写入策略"
              name="plugin_action_ids"
              rules={[requiredForJobTypes(pluginRequiredJobTypes, '请选择写入策略')]}
              extra="选择结果写到哪里或通知到哪里，后台按配置顺序执行对应动作"
            >
              <Select
                allowClear
                mode="multiple"
                maxTagCount={2}
                optionFilterProp="label"
                placeholder="请选择写入策略"
                showSearch
                options={pluginActions.map((action) => ({
                  label: writeStrategyLabelFromAction(action),
                  value: action.id,
                }))}
              />
            </Form.Item>
          {selectedJobType === 'code_repository_inspection' ? (
            <Form.List name="result_actions">
              {(fields, { add, remove }) => (
                <Space orientation="vertical" size={8} style={{ width: '100%' }}>
                  <Typography.Text strong>结果动作</Typography.Text>
                  {fields.map(({ key, ...field }) => (
                    <Space key={key} align="start" size={8} style={{ width: '100%' }}>
                      <Form.Item
                        {...field}
                        name={[field.name, 'type']}
                        rules={[{ required: true, message: '请选择结果动作' }]}
                        style={{ flex: 1, marginBottom: 8 }}
                      >
                        <Select options={codeInspectionResultActionOptions} placeholder="请选择结果动作" />
                      </Form.Item>
                      <Form.Item noStyle shouldUpdate>
                        {({ getFieldValue }) => {
                          const actionType = getFieldValue(['result_actions', field.name, 'type']);
                          if (
                            actionType === 'create_bug_for_severe_findings'
                            || actionType === 'create_task_for_severe_findings'
                          ) {
                            return (
                              <Form.Item
                                name={[field.name, 'severity_threshold']}
                                style={{ marginBottom: 8, width: 150 }}
                              >
                                <Select options={severityThresholdOptions} placeholder="严重级别" />
                              </Form.Item>
                            );
                          }
                          if (actionType === 'send_notification') {
                            return (
                              <Space orientation="vertical" size={8} style={{ width: 360 }}>
                                <Form.Item
                                  name={[field.name, 'channels']}
                                  rules={[{ required: true, message: '请选择通知渠道' }]}
                                  style={{ marginBottom: 0 }}
                                >
                                  <Select mode="multiple" options={notificationChannelOptions} placeholder="通知渠道" />
                                </Form.Item>
                                <Form.Item name={[field.name, 'recipients']} style={{ marginBottom: 0 }}>
                                  <Select mode="tags" placeholder="邮件收件人" tokenSeparators={[',', '，']} />
                                </Form.Item>
                                <Form.Item name={[field.name, 'webhook_url']} style={{ marginBottom: 8 }}>
                                  <Input placeholder="钉钉机器人 Webhook" />
                                </Form.Item>
                              </Space>
                            );
                          }
                          return null;
                        }}
                      </Form.Item>
                      <Button danger icon={<DeleteOutlined />} onClick={() => remove(field.name)} />
                    </Space>
                  ))}
                  <Button icon={<PlusOutlined />} onClick={() => add({ type: 'write_code_inspection_report' })}>
                    新增结果动作
                  </Button>
                </Space>
              )}
            </Form.List>
          ) : null}
          </FormSection>
          <FormSection label="调度配置" marker="调度">
            <Space align="start" wrap>
              <Form.Item label="调度方式" name="schedule_type">
                <Select options={scheduleTypeOptions} style={{ minWidth: 140 }} />
              </Form.Item>
              <Form.Item label="Cron 表达式" name="cron_expression">
                <Input placeholder="例如：0 9 * * MON" style={{ width: 220 }} />
              </Form.Item>
              <Form.Item label="间隔秒数" name="interval_seconds">
                <InputNumber min={1} placeholder="例如：3600" style={{ width: 160 }} />
              </Form.Item>
            </Space>
          </FormSection>
          {dryRunResult ? (
            <div
              aria-label="全链路试运行结果"
              style={{
                background: '#f8fafc',
                border: '1px solid #dbeafe',
                borderRadius: 6,
                marginTop: 16,
                padding: 16,
              }}
            >
              <Space orientation="vertical" size={16} style={{ width: '100%' }}>
                <Space>
                  <Typography.Text strong>全链路试运行结果</Typography.Text>
                  <Tag color={dryRunResult.status === 'succeeded' ? 'green' : 'red'}>{dryRunResult.status}</Tag>
                  <Typography.Text type="secondary">{dryRunResult.job_type}</Typography.Text>
                </Space>
                <JsonPreview title="数据连接预览" value={dryRunResult.stages?.data_connection} />
                <JsonPreview title="AI契约校验" value={dryRunResult.stages?.ai_processing} />
                <JsonPreview title="结果写入预览" value={dryRunResult.stages?.result_actions} />
              </Space>
            </div>
          ) : null}
        </Form>
      </Modal>

      <Modal
        destroyOnHidden
        footer={(
          <Space>
            <Button onClick={() => setSelectedRun(undefined)}>关闭</Button>
            {selectedRun?.status === 'succeeded' ? (
              <Button onClick={() => void generateTemplateFromRun(selectedRun)}>
                生成模板
              </Button>
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
        onCancel={() => setSelectedRun(undefined)}
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
                { key: 'started_at', label: '开始时间', children: selectedRun.started_at || '-' },
                { key: 'finished_at', label: '结束时间', children: selectedRun.finished_at || '-' },
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
            <RunResultWriteRecords
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
