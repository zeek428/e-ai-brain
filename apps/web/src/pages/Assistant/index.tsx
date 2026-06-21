import {
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  LinkOutlined,
  ProjectOutlined,
  ReloadOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Modal, Space, Tag, Typography, message as toast } from 'antd';
import { type KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  cancelAssistantActionDraft,
  cancelAssistantChatRun,
  chatWithAssistant,
  confirmAssistantActionDraft,
  fetchAssistantDraftTemplates,
  fetchAssistantReferenceCandidates,
  fetchAssistantRoleQuickTasks,
  fetchScheduledJobRuns,
  fetchResultWriteTargets,
  getAssistantActionDraft,
  getStoredCurrentUser,
  markAssistantActionDraftViewed,
  rememberAssistantDraftResolution,
  type AssistantActionDraftRecord,
  type AssistantDraftTemplate,
  type AssistantReference,
  type AssistantDraftResolutionMap,
  type AssistantDraftResolutionRecord,
  type AssistantDraftResourceType,
  type AssistantRoleQuickTaskGroup,
  type AssistantToolResult,
  type AssistantToolResultItem,
  type ResultWriteTargetRecord,
  type ScheduledJobRunRecord,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';
import { AssistantComposer } from './components/AssistantComposer';
import { AssistantChatRunRecovery } from './components/AssistantChatRunRecovery';
import { AssistantActionDraftCards } from './components/AssistantDraftCards';
import { AssistantMessageList } from './components/AssistantMessageList';
import {
  assistantDraftId,
  draftRegeneratePrompt,
  draftStatusLabel,
} from './components/draftPresentation';
import { AssistantReferenceContext } from './components/AssistantReferenceContext';
import { AssistantRuntimeStatus } from './components/AssistantRuntimeStatus';
import {
  AssistantReferencePicker,
  type AssistantReferenceEmptyState,
} from './components/AssistantReferencePicker';
import { AssistantSidebar } from './components/AssistantSidebar';
import {
  AssistantDraftTemplateMarket,
  AssistantMetricsPanel,
} from './components/WorkbenchPanels';
import {
  type ChatMessage,
  useAssistantConversation,
  welcomeMessages,
} from './hooks/useAssistantConversation';
import { useAssistantChatRuns } from './hooks/useAssistantChatRuns';
import { type QueryDraftResolution, useAssistantDrafts } from './hooks/useAssistantDrafts';
import { useAssistantMetricsPanel } from './hooks/useAssistantMetricsPanel';
import { useAssistantReferences } from './hooks/useAssistantReferences';
import { useAssistantRuntimeStatus } from './hooks/useAssistantRuntimeStatus';

const { Text, Title } = Typography;
const ASSISTANT_REFERENCE_CANDIDATE_DEBOUNCE_MS = 250;
const ASSISTANT_REFERENCE_CANDIDATE_LIMIT = 12;
const ASSISTANT_ADD_ACTION_LIMIT = 20;
const assistantStopCommands = ['终止', '停止', '取消', 'stop', 'cancel'];

const scheduledJobRunOnceKeywords = [
  '执行一次',
  '执行一下',
  '运行一次',
  '运行一下',
  '跑一次',
  '跑一下',
  '立即执行',
  '立即运行',
  '手动执行',
  'run once',
  'run now',
  'execute once',
];
const queryReferenceTypes = new Set([
  'ai_agent',
  'ai_skill',
  'ai_task',
  'knowledge_chunk',
  'knowledge_document',
  'knowledge_folder',
  'knowledge_space',
  'plugin_action',
  'plugin_connection',
  'requirement',
  'scheduled_job',
  'scheduled_job_run',
]);
const SCHEDULED_JOB_RUN_POLL_INTERVAL_MS = 5000;

type AssistantScheduledJobRunItem = {
  errorMessage?: string | null;
  id: string;
  latestStatusRefreshed?: boolean;
  progressText?: string;
  recordsImported?: number;
  scheduledJobId?: string;
  status: string;
  title: string;
  triggerType?: string;
  url?: string;
};

type AssistantScheduledJobRunNoticeItem = {
  description: string;
  key: string;
  requiredPermission?: string;
  scheduledJobId?: string;
  status: string;
  title: string;
};

function actionDraftItems(toolResults?: AssistantToolResult[]) {
  return (toolResults ?? [])
    .filter((toolResult) => toolResult.tool === 'assistant.action_draft')
    .flatMap((toolResult) => toolResult.items ?? [])
    .map((item) => {
      const draftId = assistantDraftId(item);
      if (!draftId || item.draft_id === draftId) {
        return item;
      }
      return { ...item, draft_id: draftId };
    })
    .filter(
      (item) =>
        (
          item.action === 'create_scheduled_job'
          || item.action === 'create_ai_agent'
          || item.action === 'create_ai_skill'
          || item.action === 'create_plugin_action'
          || item.action === 'create_plugin_connection'
          || item.action === 'create_rd_task'
          || item.action === 'create_analysis_draft'
        )
        && assistantDraftId(item),
    );
}

function taskCreationGuideItems(toolResults?: AssistantToolResult[]) {
  return (toolResults ?? [])
    .filter((toolResult) => toolResult.tool === 'assistant.task_creation_guide')
    .flatMap((toolResult) => toolResult.items ?? [])
    .filter((item) => item.title && item.prompt);
}

function scheduledJobDiagnosticItems(toolResults?: AssistantToolResult[]) {
  return (toolResults ?? [])
    .filter((toolResult) => toolResult.tool === 'assistant.scheduled_job_diagnostic')
    .flatMap((toolResult) => toolResult.items ?? [])
    .filter((item) => item.id || item.title);
}

function pluginConnectionDiagnosticItems(toolResults?: AssistantToolResult[]) {
  return (toolResults ?? [])
    .filter((toolResult) => toolResult.tool === 'assistant.plugin_connection_diagnostic')
    .flatMap((toolResult) => toolResult.items ?? [])
    .filter((item) => item.id || item.title);
}

function scheduledJobComparisonItems(toolResults?: AssistantToolResult[]) {
  return (toolResults ?? [])
    .filter((toolResult) => toolResult.tool === 'assistant.scheduled_job_run_comparison')
    .flatMap((toolResult) => toolResult.items ?? [])
    .filter((item) => item.id || item.title);
}

function optionalText(value: unknown) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  return String(value);
}

function optionalNumber(value: unknown) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : undefined;
}

function itemText(item: AssistantToolResultItem, field: string) {
  const value = item[field];
  if (Array.isArray(value)) {
    return value.length ? value.map((entry) => String(entry)).join('、') : '-';
  }
  return value === undefined || value === null || value === '' ? '-' : String(value);
}

function itemRecord(item: AssistantToolResultItem, field: string) {
  const value = item[field];
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as AssistantToolResultItem)
    : {};
}

function unknownRecord(value: unknown) {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function isAbortError(error: unknown) {
  return error instanceof Error && error.name === 'AbortError';
}

function assistantChatErrorMessage(error: unknown) {
  const detail = error as Error & { code?: string; traceId?: string };
  if (detail?.code === 'MODEL_GATEWAY_CONFIG_INVALID') {
    return [
      '模型网关未配置，当前仅支持 @ 动作、草案、运行诊断等规则能力。',
      '如需开放式问答，请到「系统管理 / 模型网关」配置默认模型后重试。',
      detail.traceId ? `trace_id=${detail.traceId}` : undefined,
    ].filter(Boolean).join(' ');
  }
  if (detail?.code === 'ASSISTANT_CHAT_FAILED') {
    return [
      'AI 助手调用模型失败，请检查模型网关连通性或稍后重试。',
      detail.traceId ? `trace_id=${detail.traceId}` : undefined,
    ].filter(Boolean).join(' ');
  }
  return formatMutationError(error);
}

function diagnosticStageItems(item: AssistantToolResultItem) {
  return Array.isArray(item.stages)
    ? item.stages.filter(
      (stage): stage is AssistantToolResultItem =>
        Boolean(stage) && typeof stage === 'object' && !Array.isArray(stage),
    )
    : [];
}

function diagnosticStageLabel(stage: string) {
  const labels: Record<string, string> = {
    ai_processing: 'AI处理',
    data_connection: '数据连接',
    result_action: '结果动作',
  };
  return labels[stage] ?? stage;
}

function diagnosticStageQuestion(stage: string) {
  const labels: Record<string, string> = {
    ai_processing: 'AI处理是否成功',
    data_connection: '数据连接是否成功',
    result_action: '结果动作是否写入成功',
  };
  return labels[stage] ?? `${diagnosticStageLabel(stage)}是否成功`;
}

function diagnosticStageOutcome(status: string) {
  const labels: Record<string, string> = {
    failed: '失败',
    queued: '排队中',
    running: '执行中',
    skipped: '已跳过',
    succeeded: '成功',
    warning: '有告警',
  };
  return labels[status] ?? (status === '-' ? '未记录' : status);
}

function pluginConnectionDiagnosticStageLabel(stage: string) {
  const labels: Record<string, string> = {
    connection_config: '连接配置',
    latest_test: '最近测试',
    repair_suggestions: '修复建议',
  };
  return labels[stage] ?? stage;
}

function pluginConnectionRepairSuggestionItems(item: AssistantToolResultItem) {
  return Array.isArray(item.repair_suggestions)
    ? item.repair_suggestions.filter(
      (suggestion): suggestion is AssistantToolResultItem =>
        Boolean(suggestion) && typeof suggestion === 'object' && !Array.isArray(suggestion),
    )
    : [];
}

function diagnosticStatusColor(status: string) {
  if (status === 'succeeded') {
    return 'green';
  }
  if (status === 'failed' || status === 'permission_denied') {
    return 'red';
  }
  if (status === 'warning' || status === 'needs_scheduled_job_reference' || status === 'needs_single_reference') {
    return 'orange';
  }
  if (status === 'running' || status === 'queued') {
    return 'blue';
  }
  return 'default';
}

function diagnosticResultWriteRecordUrl(item: AssistantToolResultItem, stage: AssistantToolResultItem) {
  const recordId = itemText(stage, 'result_write_record_id');
  if (recordId === '-') {
    return undefined;
  }
  const itemUrl = itemText(item, 'url');
  const runId = itemText(item, 'id');
  const baseUrl = itemUrl !== '-'
    ? itemUrl
    : (runId !== '-' ? `/tasks/scheduled-jobs?run_id=${encodeURIComponent(runId)}` : undefined);
  if (!baseUrl) {
    return undefined;
  }
  const separator = baseUrl.includes('?') ? '&' : '?';
  return `${baseUrl}${separator}result_write_record_id=${encodeURIComponent(recordId)}`;
}

function scheduledJobRunReferenceFromToolItem(
  item: AssistantToolResultItem,
): AssistantReference | undefined {
  const id = itemText(item, 'id');
  if (id === '-') {
    return undefined;
  }
  const title = itemText(item, 'title');
  const url = itemText(item, 'url');
  return {
    id,
    title: title === '-' ? id : title,
    type: 'scheduled_job_run',
    url: url === '-' ? `/tasks/scheduled-jobs?run_id=${encodeURIComponent(id)}` : url,
  };
}

function scheduledJobRunReferenceFromRunItem(
  item: AssistantScheduledJobRunItem,
): AssistantReference {
  return {
    id: item.id,
    title: item.title,
    type: 'scheduled_job_run',
    url: item.url ?? `/tasks/scheduled-jobs?run_id=${encodeURIComponent(item.id)}`,
  };
}

function scheduledJobRunFollowupPrompt(
  item: AssistantToolResultItem,
  prompt: string,
) {
  const reference = scheduledJobRunReferenceFromToolItem(item);
  return reference ? `@${reference.title} ${prompt}` : prompt;
}

function scheduledJobRunItemFollowupPrompt(
  item: AssistantScheduledJobRunItem,
  prompt: string,
) {
  const reference = scheduledJobRunReferenceFromRunItem(item);
  return `@${reference.title} ${prompt}`;
}

function pluginConnectionReferenceFromDiagnosticItem(
  item: AssistantToolResultItem,
): AssistantReference | undefined {
  const id = itemText(item, 'id');
  if (id === '-') {
    return undefined;
  }
  const title = itemText(item, 'title');
  const url = itemText(item, 'url');
  return {
    id,
    title: title === '-' ? id : title,
    type: 'plugin_connection',
    url: url === '-' ? `/tasks/plugins?connection_id=${encodeURIComponent(id)}` : url,
  };
}

function pluginConnectionDiagnosticFollowupPrompt(
  item: AssistantToolResultItem,
  prompt: string,
) {
  const reference = pluginConnectionReferenceFromDiagnosticItem(item);
  return reference ? `@${reference.title} ${prompt}` : prompt;
}

function scheduledJobRunStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    cancelled: '已取消',
    failed: '失败',
    needs_scheduled_job_reference: '未执行',
    needs_single_reference: '未执行',
    not_run: '未运行',
    permission_denied: '权限不足',
    queued: '排队中',
    running: '运行中',
    succeeded: '成功',
    waiting_runner: '等待执行器回写',
  };
  return labels[status ?? ''] ?? (status || '未知');
}

function scheduledJobRunExecutionProgressText(run?: ScheduledJobRunRecord) {
  const summary = unknownRecord(run?.result_summary);
  const nodes = unknownRecord(summary?.execution_nodes);
  if (!nodes) {
    return undefined;
  }
  const nodeOrder = ['data_connection', 'runner_execution', 'skill_processing', 'result_action'];
  const nodeLabelFallbacks: Record<string, string> = {
    data_connection: '数据连接获取内容',
    result_action: '动作反馈内容',
    runner_execution: 'AI 执行器执行内容',
    skill_processing: 'AI执行处理内容',
  };
  const activeStatuses = new Set(['claimed', 'pending', 'queued', 'running', 'waiting_runner']);
  for (const nodeKey of nodeOrder) {
    const node = unknownRecord(nodes[nodeKey]);
    if (!node) {
      continue;
    }
    const status = optionalText(node.status);
    if (!status || !activeStatuses.has(status)) {
      continue;
    }
    const label = optionalText(node.label) ?? nodeLabelFallbacks[nodeKey] ?? nodeKey;
    return `执行进度：${label}（${scheduledJobRunStatusLabel(status)}）`;
  }
  return undefined;
}

function scheduledJobRunExecutionFingerprint(run?: ScheduledJobRunRecord) {
  const summary = unknownRecord(run?.result_summary);
  const nodes = unknownRecord(summary?.execution_nodes);
  if (!nodes) {
    return '';
  }
  return JSON.stringify(
    Object.entries(nodes).map(([nodeKey, rawNode]) => {
      const node = unknownRecord(rawNode);
      return {
        errorCode: optionalText(node?.error_code),
        errorMessage: optionalText(node?.error_message),
        key: nodeKey,
        label: optionalText(node?.label),
        modelGatewayLogId: optionalText(node?.model_gateway_log_id),
        pluginInvocationLogId: optionalText(node?.plugin_invocation_log_id),
        runnerTaskId: optionalText(node?.runner_task_id),
        status: optionalText(node?.status),
      };
    }),
  );
}

function scheduledJobRunIsActive(status?: string) {
  return status === 'queued' || status === 'running';
}

function scheduledJobRunDefaultFollowupPrompt(status?: string) {
  return status === 'failed' ? '为什么这次任务失败？' : '帮我分析这次运行结果';
}

function scheduledJobRunRecordChanged(
  current: ScheduledJobRunRecord | undefined,
  next: ScheduledJobRunRecord,
) {
  return (
    !current
    || current.error_code !== next.error_code
    || current.error_message !== next.error_message
    || current.finished_at !== next.finished_at
    || current.plugin_invocation_log_id !== next.plugin_invocation_log_id
    || current.records_imported !== next.records_imported
    || scheduledJobRunExecutionFingerprint(current) !== scheduledJobRunExecutionFingerprint(next)
    || current.status !== next.status
    || current.updated_at !== next.updated_at
  );
}

function scheduledJobRunBaseItems(toolResults?: AssistantToolResult[]) {
  const byRunId = new Map<string, AssistantScheduledJobRunItem>();
  (toolResults ?? [])
    .filter((toolResult) => toolResult.tool === 'assistant.scheduled_job_run')
    .forEach((toolResult) => {
      const summary = toolResult.summary ?? {};
      const sourceItems = toolResult.items?.length
        ? toolResult.items
        : (summary.run_id ? [{ ...summary, id: summary.run_id }] : []);
      sourceItems.forEach((item) => {
        const id = optionalText(item.id ?? item.run_id);
        if (!id || byRunId.has(id)) {
          return;
        }
        const status = optionalText(item.status ?? summary.status) ?? 'unknown';
        byRunId.set(id, {
          errorMessage: optionalText(item.error_message ?? summary.error_message),
          id,
          progressText: optionalText(item.progress_text ?? summary.progress_text),
          recordsImported: optionalNumber(item.records_imported ?? summary.records_imported),
          scheduledJobId: optionalText(item.scheduled_job_id ?? summary.scheduled_job_id),
          status,
          title: optionalText(item.title ?? summary.scheduled_job_name) ?? `运行记录 ${id}`,
          triggerType: optionalText(item.trigger_type ?? summary.trigger_type),
          url: optionalText(item.url) ?? `/tasks/scheduled-jobs?run_id=${id}`,
        });
      });
    });
  return [...byRunId.values()];
}

function scheduledJobRunNoticeDescription(summary: Record<string, unknown>, status: string) {
  const requiredPermission = optionalText(summary.required_permission) ?? 'system.scheduled_jobs.run';
  const errorMessage = optionalText(summary.error_message);
  if (status === 'permission_denied') {
    return `当前账号缺少 ${requiredPermission}，本次尚未执行。`;
  }
  if (status === 'needs_single_reference') {
    return '检测到多个定时作业引用，本次尚未执行。请只保留一个定时作业后再发送。';
  }
  if (status === 'needs_scheduled_job_reference') {
    return '没有找到唯一可执行的定时作业，本次尚未执行。请从 @ 候选选择定时作业，或先确认生成的作业草案。';
  }
  if (status === 'failed') {
    return errorMessage ? `运行未创建成功：${errorMessage}` : '运行未创建成功，请检查定时作业配置。';
  }
  return '本次没有生成新的运行记录，请根据提示补齐配置后再执行。';
}

function scheduledJobRunNoticeTitle(summary: Record<string, unknown>) {
  const jobName = optionalText(summary.scheduled_job_name);
  if (jobName) {
    return jobName;
  }
  const queries = Array.isArray(summary.queries)
    ? summary.queries.map((query) => String(query)).filter(Boolean)
    : [];
  return queries.length ? `执行一次：${queries.join('、')}` : '定时作业执行一次';
}

function scheduledJobRunNoticeItems(toolResults?: AssistantToolResult[]) {
  const visibleStatuses = new Set([
    'failed',
    'needs_scheduled_job_reference',
    'needs_single_reference',
    'permission_denied',
  ]);
  return (toolResults ?? [])
    .filter((toolResult) => toolResult.tool === 'assistant.scheduled_job_run')
    .flatMap((toolResult, index) => {
      const summary = toolResult.summary ?? {};
      const hasRunItem = Boolean(optionalText(summary.run_id))
        || Boolean((toolResult.items ?? []).some((item) => optionalText(item.id ?? item.run_id)));
      if (hasRunItem) {
        return [];
      }
      const status = optionalText(summary.status) ?? 'not_run';
      if (!visibleStatuses.has(status)) {
        return [];
      }
      return [
        {
          description: scheduledJobRunNoticeDescription(summary, status),
          key: `${toolResult.intent ?? 'scheduled_job_run_once'}:${status}:${index}`,
          requiredPermission: optionalText(summary.required_permission),
          scheduledJobId: optionalText(summary.scheduled_job_id),
          status,
          title: scheduledJobRunNoticeTitle(summary),
        },
      ];
    });
}

function scheduledJobRunItems(
  toolResults: AssistantToolResult[] | undefined,
  runById: Record<string, ScheduledJobRunRecord>,
) {
  return scheduledJobRunBaseItems(toolResults).map((item) => {
    const latestRun = runById[item.id];
    if (!latestRun) {
      return item;
    }
    const latestStatus = latestRun.status || item.status;
    const latestStatusRefreshed = latestStatus !== item.status;
    return {
      ...item,
      errorMessage: latestRun.error_message ?? item.errorMessage,
      latestStatusRefreshed,
      progressText: scheduledJobRunExecutionProgressText(latestRun) ?? item.progressText,
      recordsImported: latestRun.records_imported ?? item.recordsImported,
      scheduledJobId: latestRun.scheduled_job_id ?? item.scheduledJobId,
      status: latestStatus,
      title: item.title.includes('/')
        ? item.title.replace(/\/\s*[^/]+$/, `/ ${latestStatus}`)
        : item.title,
      triggerType: latestRun.trigger_type ?? item.triggerType,
    };
  });
}

function scheduledJobRunPollTargets(
  messages: ChatMessage[],
  runById: Record<string, ScheduledJobRunRecord>,
) {
  const byRunId = new Map<string, AssistantScheduledJobRunItem>();
  messages.forEach((message) => {
    scheduledJobRunBaseItems(message.toolResults).forEach((item) => {
      const latestStatus = runById[item.id]?.status ?? item.status;
      if (!scheduledJobRunIsActive(latestStatus)) {
        return;
      }
      byRunId.set(item.id, {
        ...item,
        scheduledJobId: runById[item.id]?.scheduled_job_id ?? item.scheduledJobId,
        status: latestStatus,
      });
    });
  });
  return [...byRunId.values()];
}

function comparisonDifferenceItems(item: AssistantToolResultItem) {
  return Array.isArray(item.differences)
    ? item.differences.filter(
      (difference): difference is AssistantToolResultItem =>
        Boolean(difference) && typeof difference === 'object' && !Array.isArray(difference),
    )
    : [];
}

type ActiveMentionRange = {
  endIndex: number;
  markerIndex: number;
  query: string;
};

function activeMentionRange(value: string): ActiveMentionRange | undefined {
  const markerIndex = Math.max(value.lastIndexOf('@'), value.lastIndexOf('＠'));
  if (markerIndex < 0) {
    return undefined;
  }
  const previousChar = markerIndex > 0 ? value[markerIndex - 1] : '';
  if (previousChar && /[A-Za-z0-9._%+-]/.test(previousChar)) {
    return undefined;
  }
  const tail = value.slice(markerIndex + 1);
  if (tail.includes('\n')) {
    return undefined;
  }
  if (tail.length > 0 && /^\s/.test(tail)) {
    return undefined;
  }
  const rawQuery = tail.split(/\s+/)[0] ?? '';
  const query = rawQuery;
  const endIndex = markerIndex + 1 + rawQuery.length;
  if (!scheduledJobRunOnceRequested(value)) {
    return { endIndex, markerIndex, query };
  }
  return {
    endIndex,
    markerIndex,
    query: trimRunOnceCommandFromMentionQuery(query),
  };
}

function activeMentionQuery(value: string) {
  return activeMentionRange(value)?.query;
}

function uniqueScheduledJobReferenceCandidate(references: AssistantReference[]) {
  const scheduledJobReferences = references.filter((reference) => reference.type === 'scheduled_job');
  return scheduledJobReferences.length === 1 ? scheduledJobReferences[0] : undefined;
}

function scheduledJobRunOnceRequested(value: string) {
  const normalized = value.toLowerCase();
  return scheduledJobRunOnceKeywords.some((keyword) => normalized.includes(keyword));
}

function assistantStopCommandRequested(value: string) {
  const normalized = value.trim().toLowerCase();
  return assistantStopCommands.some((command) => normalized === command);
}

function createAssistantChatRunId() {
  const randomId = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  return `assistant_chat_run_${randomId.replace(/[^a-zA-Z0-9_-]/g, '_')}`;
}

function assistantReferenceEmptyState(value: string) {
  if (scheduledJobRunOnceRequested(value)) {
    return {
      actionHref: '/tasks/scheduled-jobs',
      actionLabel: '去任务中心新增定时作业',
      description: '请先新增或确认一个定时作业，再回到助手里 @ 它执行一次。',
      prompt: '我要新增任务，请先帮我选择任务类型并生成可确认的配置草案',
      promptLabel: '让 AI 生成任务草案',
      title: '没有找到可执行的定时作业引用',
    };
  }
  return {
    actionHref: '/knowledge/documents',
    actionLabel: '去知识库查看文档',
    description: '请换个关键词，或确认你是否有权限访问该对象。',
    prompt: '我要新增任务，请先帮我选择任务类型并生成可确认的配置草案',
    promptLabel: '让 AI 生成任务草案',
    title: '无匹配引用',
  };
}

function currentUserCanRunScheduledJobFromAssistant() {
  const currentUser = getStoredCurrentUser();
  const roles = new Set(currentUser?.roles ?? []);
  const permissions = new Set(currentUser?.permissions ?? []);
  return (
    roles.has('admin')
    || permissions.has('system.admin')
    || permissions.has('system.scheduled_jobs.run')
    || permissions.has('system.scheduled_jobs.manage')
  );
}

function trimRunOnceCommandFromMentionQuery(query: string) {
  const normalizedQuery = query.toLowerCase();
  let endIndex = query.length;
  scheduledJobRunOnceKeywords.forEach((keyword) => {
    const keywordIndex = normalizedQuery.indexOf(keyword);
    if (keywordIndex >= 0) {
      endIndex = Math.min(endIndex, keywordIndex);
    }
  });
  return query.slice(0, endIndex).trim().replace(/[，,。；;：:]+$/u, '');
}

function mergeReferences(...referenceLists: AssistantReference[][]) {
  const references: AssistantReference[] = [];
  const seen = new Set<string>();
  referenceLists.forEach((referenceList) => {
    referenceList.forEach((reference) => {
      const key = referenceKey(reference);
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      references.push(reference);
    });
  });
  return references;
}

function referenceKey(reference: Pick<AssistantReference, 'id' | 'type'>) {
  return `${reference.type}:${reference.id}`;
}

function assistantQueryReferenceParams() {
  if (typeof window === 'undefined') {
    return undefined;
  }
  const params = new URLSearchParams(window.location.search);
  const referenceType = params.get('reference_type')?.trim();
  const referenceId = params.get('reference_id')?.trim();
  if (!referenceType || !referenceId || !queryReferenceTypes.has(referenceType)) {
    return undefined;
  }
  return {
    prompt: params.get('prompt')?.trim() || undefined,
    referenceId,
    referenceType,
  };
}

function assistantQueryDraftId() {
  if (typeof window === 'undefined') {
    return undefined;
  }
  return new URLSearchParams(window.location.search).get('draft_id')?.trim() || undefined;
}

function assistantActionDraftRecordToToolItem(
  draft: AssistantActionDraftRecord,
): AssistantToolResultItem {
  return {
    action: draft.action,
    client_draft_id: draft.client_draft_id,
    draft_id: draft.id,
    payload: draft.payload,
    preview: draft.preview,
    requires_confirmation: true,
    risk_level: draft.risk_level,
    server_draft_id: draft.id,
    status: draft.status,
    title: draft.title,
    wizard_steps: draft.wizard_steps,
  };
}

function assistantDraftResultRunResolution(
  draft: AssistantActionDraftRecord,
): AssistantDraftResolutionRecord | undefined {
  const run = draft.result_run;
  if (!run?.result_id || !run.result_type) {
    return undefined;
  }
  const resourceType = run.result_type as AssistantDraftResourceType;
  if (
    resourceType !== 'assistant_analysis'
    && resourceType !== 'ai_agent'
    && resourceType !== 'ai_skill'
    && resourceType !== 'ai_task'
    && resourceType !== 'plugin_action'
    && resourceType !== 'plugin_connection'
    && resourceType !== 'scheduled_job'
  ) {
    return undefined;
  }
  const resolution: AssistantDraftResolutionRecord = {
    resource_id: run.result_id,
    resource_type: resourceType,
    title: draft.title,
  };
  const scheduledJobRunId = scheduledJobRunIdFromActionResult(run.result);
  if (scheduledJobRunId) {
    resolution.scheduled_job_run_id = scheduledJobRunId;
  }
  return resolution;
}

function assistantDraftResolutionIds(
  draft: Pick<AssistantActionDraftRecord, 'client_draft_id' | 'id'>,
) {
  return [draft.id, draft.client_draft_id]
    .map((value) => (value ? String(value) : undefined))
    .filter(Boolean) as string[];
}

function queryDraftResolutionLabel(status: QueryDraftResolution['status']) {
  if (status === 'loading') {
    return { color: 'processing', text: '加载中' };
  }
  if (status === 'resolved') {
    return { color: 'green', text: '已加载' };
  }
  return { color: 'red', text: '加载失败' };
}

function queryDraftResolutionText(resolution: QueryDraftResolution) {
  if (resolution.status === 'loading') {
    return `正在加载草案：${resolution.draftId}`;
  }
  if (resolution.status === 'resolved') {
    return `已从链接打开草案：${resolution.title || resolution.draftId}`;
  }
  return `草案加载失败：${resolution.draftId} ${resolution.message || '不存在或无权限'}`;
}

function scheduledJobRunIdFromActionResult(result?: Record<string, unknown>) {
  const scheduledJobRun = result?.scheduled_job_run;
  if (!scheduledJobRun || typeof scheduledJobRun !== 'object' || Array.isArray(scheduledJobRun)) {
    return undefined;
  }
  const runId = String((scheduledJobRun as Record<string, unknown>).id ?? '').trim();
  return runId || undefined;
}

function isAssistantActionReference(reference: AssistantReference) {
  return reference.type === 'assistant_action';
}

function assistantActionCommand(reference: AssistantReference) {
  const title = String(reference.title || reference.id).replace(/\s+/g, '').trim();
  return title ? `@${title}` : '@动作';
}

function isScheduledJobCommandReference(reference: AssistantReference) {
  return reference.type === 'scheduled_job';
}

function scheduledJobCommand(reference: AssistantReference) {
  const title = String(reference.title || reference.id).replace(/\s+/g, ' ').trim();
  return title ? `@${title}` : '@定时作业';
}

function inputStartsWithActionCommand(value: string, command?: string) {
  if (!command || !value.startsWith(command)) {
    return false;
  }
  const nextChar = value[command.length];
  return nextChar === undefined || /\s/.test(nextChar);
}

function inputWithMentionCommand(currentValue: string, command: string) {
  const mention = activeMentionRange(currentValue);
  const userText = mention
    ? `${currentValue.slice(0, mention.markerIndex)}${currentValue.slice(mention.endIndex)}`
    : currentValue;
  const normalizedUserText = userText.replace(/[ \t]{2,}/g, ' ').trim();
  return normalizedUserText ? `${command} ${normalizedUserText}` : `${command} `;
}

function inputWithAssistantActionCommand(currentValue: string, reference: AssistantReference) {
  return inputWithMentionCommand(currentValue, assistantActionCommand(reference));
}

function inputWithScheduledJobCommand(currentValue: string, reference: AssistantReference) {
  return inputWithMentionCommand(currentValue, scheduledJobCommand(reference));
}

function AssistantTaskCreationGuideCards({
  items,
  onUsePrompt,
}: {
  items: AssistantToolResultItem[];
  onUsePrompt: (prompt: string) => void;
}) {
  if (!items.length) {
    return null;
  }
  const defaultSteps = ['数据来源', 'AI处理', '结果动作', '调度策略', '确认执行'];
  return (
    <div className="assistant-task-guide">
      <div className="assistant-task-guide-header">
        <Space size={8} wrap>
          <ProjectOutlined />
          <Text strong>任务类型向导</Text>
          <Tag color="blue">草案优先</Tag>
        </Space>
        <Text type="secondary">{defaultSteps.join(' -> ')}</Text>
      </div>
      <div className="assistant-task-guide-grid">
        {items.map((item) => {
          const title = itemText(item, 'title');
          const prompt = itemText(item, 'prompt');
          const dependencies = itemText(item, 'dependencies');
          const wizardSteps = itemText(item, 'wizard_steps');
          return (
            <div className="assistant-task-guide-card" key={itemText(item, 'type')}>
              <div className="assistant-task-guide-card-title">
                <Text strong>{title}</Text>
                <Tag
                  color={
                    item.draft_action === 'create_scheduled_job'
                      ? 'green'
                      : item.draft_action === 'create_rd_task'
                        ? 'blue'
                        : 'default'
                  }
                >
                  {itemText(item, 'draft_action')}
                </Tag>
              </div>
              <Text type="secondary">{itemText(item, 'description')}</Text>
              {dependencies !== '-' ? <Text>依赖：{dependencies}</Text> : null}
              <Text type="secondary">流程：{wizardSteps}</Text>
              <Button size="small" onClick={() => onUsePrompt(prompt)}>
                选择{title}
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AssistantScheduledJobRunCards({
  items,
  onUseRunFollowupPrompt,
}: {
  items: AssistantScheduledJobRunItem[];
  onUseRunFollowupPrompt: (item: AssistantScheduledJobRunItem, prompt: string) => void;
}) {
  if (!items.length) {
    return null;
  }
  return (
    <div className="assistant-run-list">
      {items.map((item) => {
        const isActive = scheduledJobRunIsActive(item.status);
        return (
          <div className="assistant-run-card" key={item.id}>
            <div className="assistant-run-header">
              <Space size={8} wrap>
                <ClockCircleOutlined />
                <Text strong>运行记录</Text>
                <Tag color={diagnosticStatusColor(item.status)}>
                  {scheduledJobRunStatusLabel(item.status)}
                </Tag>
              </Space>
              <Button href={item.url} icon={<LinkOutlined />} size="small" type="link">
                查看运行记录
              </Button>
            </div>
            <Text className="assistant-run-title" strong>
              {item.title}
            </Text>
            <div className="assistant-run-metrics">
              <span>
                <Text type="secondary">运行状态</Text>
                <Text>运行状态：{scheduledJobRunStatusLabel(item.status)}</Text>
              </span>
              <span>
                <Text type="secondary">导入记录</Text>
                <Text>导入记录：{item.recordsImported ?? 0}</Text>
              </span>
              <span>
                <Text type="secondary">触发方式</Text>
                <Text>{item.triggerType ?? 'manual'}</Text>
              </span>
            </div>
            {isActive ? (
              <div className="assistant-run-progress">
                <Text type="secondary">正在执行，完成后会自动刷新状态。</Text>
                {item.progressText ? (
                  <Text type="secondary">{item.progressText}</Text>
                ) : null}
              </div>
            ) : null}
            {item.latestStatusRefreshed ? (
              <Text type="secondary">
                已刷新到最新状态：{scheduledJobRunStatusLabel(item.status)}
              </Text>
            ) : null}
            {item.errorMessage ? (
              <Text type="danger">错误：{item.errorMessage}</Text>
            ) : null}
            <Space className="assistant-run-actions" size={8} wrap>
              <Button
                aria-label="问这次运行"
                icon={<RobotOutlined />}
                size="small"
                onClick={() => onUseRunFollowupPrompt(item, scheduledJobRunDefaultFollowupPrompt(item.status))}
              >
                问这次运行
              </Button>
              {item.status === 'failed' ? (
                <Button
                  aria-label="生成运行修复草案"
                  icon={<FileTextOutlined />}
                  size="small"
                  onClick={() => onUseRunFollowupPrompt(item, '这次失败怎么修？帮我生成修复草案')}
                >
                  生成修复草案
                </Button>
              ) : null}
              <Button
                aria-label="对比这次运行"
                icon={<ReloadOutlined />}
                size="small"
                onClick={() => onUseRunFollowupPrompt(item, '和上次成功有什么不同？')}
              >
                对比上次成功
              </Button>
            </Space>
          </div>
        );
      })}
    </div>
  );
}

function AssistantScheduledJobRunNoticeCards({
  items,
}: {
  items: AssistantScheduledJobRunNoticeItem[];
}) {
  if (!items.length) {
    return null;
  }
  return (
    <div className="assistant-run-list">
      {items.map((item) => (
        <div className="assistant-run-card" key={item.key}>
          <div className="assistant-run-header">
            <Space size={8} wrap>
              <ExclamationCircleOutlined />
              <Text strong>执行状态</Text>
              <Tag color={diagnosticStatusColor(item.status)}>
                {scheduledJobRunStatusLabel(item.status)}
              </Tag>
            </Space>
            {item.scheduledJobId ? (
              <Button
                href={`/tasks/scheduled-jobs?job_id=${encodeURIComponent(item.scheduledJobId)}`}
                icon={<LinkOutlined />}
                size="small"
                type="link"
              >
                查看定时作业
              </Button>
            ) : null}
          </div>
          <Text className="assistant-run-title" strong>
            {item.title}
          </Text>
          <Text>{item.description}</Text>
          {item.requiredPermission ? (
            <Text type="secondary">所需权限：{item.requiredPermission}</Text>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function AssistantScheduledJobDiagnosticCards({
  items,
  onUseRunFollowupPrompt,
}: {
  items: AssistantToolResultItem[];
  onUseRunFollowupPrompt: (item: AssistantToolResultItem, prompt: string) => void;
}) {
  if (!items.length) {
    return null;
  }
  return (
    <div className="assistant-diagnostic-list">
      {items.map((item) => {
        const stages = diagnosticStageItems(item);
        return (
          <div className="assistant-diagnostic-card" key={itemText(item, 'id')}>
            <div className="assistant-diagnostic-header">
              <Space size={8} wrap>
                <ExclamationCircleOutlined />
                <Text strong>运行诊断</Text>
                <Tag color={diagnosticStatusColor(itemText(item, 'status'))}>
                  {itemText(item, 'status')}
                </Tag>
              </Space>
              {item.url ? (
                <Button href={itemText(item, 'url')} icon={<LinkOutlined />} size="small" type="link">
                  运行记录
                </Button>
              ) : null}
            </div>
            <Text className="assistant-diagnostic-title" strong>
              {itemText(item, 'title')}
            </Text>
            <Space className="assistant-diagnostic-actions" size={8} wrap>
              <Button
                aria-label="生成修复草案"
                icon={<FileTextOutlined />}
                size="small"
                onClick={() => onUseRunFollowupPrompt(item, '这次失败怎么修？帮我生成修复草案')}
              >
                生成修复草案
              </Button>
              <Button
                aria-label="对比上次成功"
                icon={<ReloadOutlined />}
                size="small"
                onClick={() => onUseRunFollowupPrompt(item, '和上次成功有什么不同？')}
              >
                对比上次成功
              </Button>
            </Space>
            <div className="assistant-diagnostic-stage-grid">
              {stages.map((stage) => {
                const writeTargetLabel = itemText(stage, 'result_write_target_label');
                const writeTarget = itemText(stage, 'result_write_target');
                const errorMessage = itemText(stage, 'error_message');
                const logId = itemText(stage, 'log_id');
                const resultWriteRecordId = itemText(stage, 'result_write_record_id');
                const resultWriteRecordUrl = diagnosticResultWriteRecordUrl(item, stage);
                const stageName = itemText(stage, 'stage');
                const stageStatus = itemText(stage, 'status');
                return (
                  <div className="assistant-diagnostic-stage" key={stageName}>
                    <Text strong>
                      {diagnosticStageQuestion(stageName)}：{diagnosticStageOutcome(stageStatus)}
                    </Text>
                    <Space size={6} wrap>
                      <Tag color="blue">{diagnosticStageLabel(stageName)}</Tag>
                      <Tag color={diagnosticStatusColor(stageStatus)}>
                        {stageStatus}
                      </Tag>
                    </Space>
                    <Text>{itemText(stage, 'summary')}</Text>
                    {logId !== '-' ? (
                      <Text type="secondary">关联日志：{logId}</Text>
                    ) : null}
                    {writeTargetLabel !== '-' || writeTarget !== '-' ? (
                      <Text type="secondary">
                        写入目标：{writeTargetLabel !== '-' ? writeTargetLabel : writeTarget}
                      </Text>
                    ) : null}
                    {resultWriteRecordId !== '-' ? (
                      resultWriteRecordUrl ? (
                        <Button
                          aria-label={`查看写入记录 ${resultWriteRecordId}`}
                          href={resultWriteRecordUrl}
                          icon={<LinkOutlined />}
                          size="small"
                          type="link"
                        >
                          写入记录：{resultWriteRecordId}
                        </Button>
                      ) : (
                        <Text type="secondary">
                          写入记录：{resultWriteRecordId}
                        </Text>
                      )
                    ) : null}
                    {errorMessage !== '-' ? (
                      <Text type="danger">错误：{errorMessage}</Text>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function AssistantPluginConnectionDiagnosticCards({
  items,
  onUseConnectionFollowupPrompt,
}: {
  items: AssistantToolResultItem[];
  onUseConnectionFollowupPrompt: (item: AssistantToolResultItem, prompt: string) => void;
}) {
  if (!items.length) {
    return null;
  }
  return (
    <div className="assistant-diagnostic-list">
      {items.map((item) => {
        const stages = diagnosticStageItems(item);
        const suggestions = pluginConnectionRepairSuggestionItems(item);
        const status = itemText(item, 'status');
        return (
          <div className="assistant-diagnostic-card" key={itemText(item, 'id')}>
            <div className="assistant-diagnostic-header">
              <Space size={8} wrap>
                <LinkOutlined />
                <Text strong>插件连接诊断</Text>
                <Tag color={diagnosticStatusColor(status)}>{status}</Tag>
              </Space>
              {item.url ? (
                <Button href={itemText(item, 'url')} icon={<LinkOutlined />} size="small" type="link">
                  打开插件连接
                </Button>
              ) : null}
            </div>
            <Text className="assistant-diagnostic-title" strong>
              {itemText(item, 'title')}
            </Text>
            <div className="assistant-comparison-metrics">
              <span>
                <Text type="secondary">失败步骤</Text>
                <Text>{itemText(item, 'failed_step')}</Text>
              </span>
              <span>
                <Text type="secondary">最近测试</Text>
                <Text>{itemText(item, 'checked_at')}</Text>
              </span>
              <span>
                <Text type="secondary">插件</Text>
                <Text>{itemText(item, 'plugin_name')}</Text>
              </span>
            </div>
            <Space className="assistant-diagnostic-actions" size={8} wrap>
              <Button
                aria-label="生成插件连接修复草案"
                icon={<FileTextOutlined />}
                size="small"
                onClick={() => onUseConnectionFollowupPrompt(
                  item,
                  '这个插件连接失败怎么修？请生成修复草案',
                )}
              >
                生成修复草案
              </Button>
              <Button
                aria-label="继续排查插件连接"
                icon={<ExclamationCircleOutlined />}
                size="small"
                onClick={() => onUseConnectionFollowupPrompt(
                  item,
                  '继续排查这个插件连接失败原因',
                )}
              >
                继续排查
              </Button>
            </Space>
            <div className="assistant-diagnostic-stage-grid">
              {stages.map((stage) => (
                <div className="assistant-diagnostic-stage" key={itemText(stage, 'stage')}>
                  <Space size={6} wrap>
                    <Tag color="blue">{pluginConnectionDiagnosticStageLabel(itemText(stage, 'stage'))}</Tag>
                    <Tag color={diagnosticStatusColor(itemText(stage, 'status'))}>
                      {itemText(stage, 'status')}
                    </Tag>
                  </Space>
                  <Text>{itemText(stage, 'summary')}</Text>
                </div>
              ))}
            </div>
            {suggestions.length ? (
              <div className="assistant-action-draft-precheck-issues">
                {suggestions.map((suggestion) => (
                  <Text key={itemText(suggestion, 'code')} type="warning">
                    {itemText(suggestion, 'title')}：{itemText(suggestion, 'detail')}
                  </Text>
                ))}
              </div>
            ) : null}
            {itemText(item, 'error_message') !== '-' ? (
              <Text type="danger">错误：{itemText(item, 'error_message')}</Text>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function AssistantScheduledJobComparisonCards({
  items,
  onUseRunFollowupPrompt,
}: {
  items: AssistantToolResultItem[];
  onUseRunFollowupPrompt: (item: AssistantToolResultItem, prompt: string) => void;
}) {
  if (!items.length) {
    return null;
  }
  return (
    <div className="assistant-comparison-list">
      {items.map((item) => {
        const currentRun = itemRecord(item, 'current_run');
        const baselineRun = itemRecord(item, 'baseline_run');
        const differences = comparisonDifferenceItems(item);
        return (
          <div className="assistant-comparison-card" key={itemText(item, 'id')}>
            <div className="assistant-comparison-header">
              <Space size={8} wrap>
                <ProjectOutlined />
                <Text strong>运行对比</Text>
                <Tag color={diagnosticStatusColor(itemText(currentRun, 'status'))}>
                  当前：{itemText(currentRun, 'status')}
                </Tag>
                <Tag color={diagnosticStatusColor(itemText(baselineRun, 'status'))}>
                  上次成功：{itemText(baselineRun, 'status')}
                </Tag>
              </Space>
              {item.url ? (
                <Button href={itemText(item, 'url')} icon={<LinkOutlined />} size="small" type="link">
                  当前运行
                </Button>
              ) : null}
            </div>
            <Text className="assistant-comparison-title" strong>
              {itemText(item, 'title')}
            </Text>
            <Space className="assistant-comparison-actions" size={8} wrap>
              <Button
                aria-label="生成修复草案"
                icon={<FileTextOutlined />}
                size="small"
                onClick={() => onUseRunFollowupPrompt(item, '这次失败怎么修？帮我生成修复草案')}
              >
                生成修复草案
              </Button>
              <Button
                aria-label="继续诊断"
                icon={<ExclamationCircleOutlined />}
                size="small"
                onClick={() => onUseRunFollowupPrompt(item, '为什么这次任务失败？')}
              >
                继续诊断
              </Button>
            </Space>
            <div className="assistant-comparison-metrics">
              <span>
                <Text type="secondary">当前导入</Text>
                <Text>{itemText(currentRun, 'records_imported')}</Text>
              </span>
              <span>
                <Text type="secondary">上次导入</Text>
                <Text>{itemText(baselineRun, 'records_imported')}</Text>
              </span>
              <span>
                <Text type="secondary">当前耗时</Text>
                <Text>{itemText(currentRun, 'duration_ms')} ms</Text>
              </span>
              <span>
                <Text type="secondary">上次耗时</Text>
                <Text>{itemText(baselineRun, 'duration_ms')} ms</Text>
              </span>
            </div>
            <div className="assistant-comparison-differences">
              {differences.map((difference, index) => {
                const stage = itemText(difference, 'stage');
                const currentSummary = itemText(difference, 'current_summary');
                const baselineSummary = itemText(difference, 'baseline_summary');
                return (
                  <div
                    className="assistant-comparison-difference"
                    key={`${itemText(difference, 'field')}:${index}`}
                  >
                    <Space size={6} wrap>
                      <Tag color={stage !== '-' ? 'blue' : 'default'}>
                        {stage !== '-' ? diagnosticStageLabel(stage) : itemText(difference, 'field')}
                      </Tag>
                      {itemText(difference, 'current_status') !== '-' ? (
                        <Tag color={diagnosticStatusColor(itemText(difference, 'current_status'))}>
                          当前 {itemText(difference, 'current_status')}
                        </Tag>
                      ) : null}
                      {itemText(difference, 'baseline_status') !== '-' ? (
                        <Tag color={diagnosticStatusColor(itemText(difference, 'baseline_status'))}>
                          上次 {itemText(difference, 'baseline_status')}
                        </Tag>
                      ) : null}
                    </Space>
                    {currentSummary !== '-' ? <Text>当前：{currentSummary}</Text> : null}
                    {baselineSummary !== '-' ? <Text>上次：{baselineSummary}</Text> : null}
                    {itemText(difference, 'current') !== '-' || itemText(difference, 'baseline') !== '-' ? (
                      <Text type="secondary">
                        {itemText(difference, 'baseline')} {'->'} {itemText(difference, 'current')}
                      </Text>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function AssistantBubble({
  draftMutationId,
  draftResolutionById,
  draftStatusById,
  message,
  onCancelDraft,
  onConfirmDraft,
  onRegenerateDraft,
  onRestoreFailedRequest,
  onRetryFailedRequest,
  onViewDraft,
  onUseConnectionFollowupPrompt,
  onUseRunCardFollowupPrompt,
  onUseRunFollowupPrompt,
  onUseTaskGuidePrompt,
  resultWriteTargetLabels,
  scheduledJobRunById,
}: {
  draftMutationId?: string;
  draftResolutionById: AssistantDraftResolutionMap;
  draftStatusById: Record<string, string>;
  message: ChatMessage;
  onCancelDraft: (draft: AssistantToolResultItem) => void;
  onConfirmDraft: (draft: AssistantToolResultItem) => void;
  onRegenerateDraft: (draft: AssistantToolResultItem) => void;
  onRestoreFailedRequest: (request: NonNullable<ChatMessage['failedRequest']>) => void;
  onRetryFailedRequest: (request: NonNullable<ChatMessage['failedRequest']>) => void;
  onViewDraft: (draft: AssistantToolResultItem) => Promise<AssistantToolResultItem>;
  onUseConnectionFollowupPrompt: (item: AssistantToolResultItem, prompt: string) => void;
  onUseRunCardFollowupPrompt: (item: AssistantScheduledJobRunItem, prompt: string) => void;
  onUseRunFollowupPrompt: (item: AssistantToolResultItem, prompt: string) => void;
  onUseTaskGuidePrompt: (prompt: string) => void;
  resultWriteTargetLabels: Map<string, string>;
  scheduledJobRunById: Record<string, ScheduledJobRunRecord>;
}) {
  const drafts = actionDraftItems(message.toolResults);
  const taskGuideItems = taskCreationGuideItems(message.toolResults);
  const runNoticeItems = scheduledJobRunNoticeItems(message.toolResults);
  const runItems = scheduledJobRunItems(message.toolResults, scheduledJobRunById);
  const diagnosticItems = scheduledJobDiagnosticItems(message.toolResults);
  const pluginConnectionDiagnostics = pluginConnectionDiagnosticItems(message.toolResults);
  const comparisonItems = scheduledJobComparisonItems(message.toolResults);
  return (
    <div className={`assistant-bubble assistant-bubble-${message.role}`}>
      <div className="assistant-bubble-avatar">
        {message.role === 'assistant' ? <RobotOutlined /> : '我'}
      </div>
      <div className="assistant-bubble-content">
        {message.role === 'assistant' && message.intent?.summary ? (
          <div className="assistant-intent-hint">
            <Tag color="geekblue">{message.intent.summary}</Tag>
          </div>
        ) : null}
        <Text>{message.content}</Text>
        {message.failedRequest ? (
          <Space className="assistant-failed-request-actions" size={8} wrap>
            <Button size="small" type="primary" onClick={() => onRetryFailedRequest(message.failedRequest!)}>
              重试
            </Button>
            <Button size="small" onClick={() => onRestoreFailedRequest(message.failedRequest!)}>
              恢复到输入框
            </Button>
          </Space>
        ) : null}
        {message.references?.length ? (
          <div className="assistant-reference-list">
            {message.references.map((reference) => (
              <Button
                href={reference.url}
                icon={<LinkOutlined />}
                key={`${reference.type}:${reference.id}`}
                size="small"
                type="link"
              >
                {reference.title}
              </Button>
            ))}
          </div>
        ) : null}
        <AssistantActionDraftCards
          draftMutationId={draftMutationId}
          draftResolutionById={draftResolutionById}
          drafts={drafts}
          draftStatusById={draftStatusById}
          onCancelDraft={onCancelDraft}
          onConfirmDraft={onConfirmDraft}
          onRegenerateDraft={onRegenerateDraft}
          onViewDraft={onViewDraft}
          onUseDraftWizardStepPrompt={onUseTaskGuidePrompt}
          resultWriteTargetLabels={resultWriteTargetLabels}
        />
        <AssistantTaskCreationGuideCards
          items={taskGuideItems}
          onUsePrompt={onUseTaskGuidePrompt}
        />
        <AssistantScheduledJobRunNoticeCards items={runNoticeItems} />
        <AssistantScheduledJobRunCards
          items={runItems}
          onUseRunFollowupPrompt={onUseRunCardFollowupPrompt}
        />
        <AssistantScheduledJobDiagnosticCards
          items={diagnosticItems}
          onUseRunFollowupPrompt={onUseRunFollowupPrompt}
        />
        <AssistantPluginConnectionDiagnosticCards
          items={pluginConnectionDiagnostics}
          onUseConnectionFollowupPrompt={onUseConnectionFollowupPrompt}
        />
        <AssistantScheduledJobComparisonCards
          items={comparisonItems}
          onUseRunFollowupPrompt={onUseRunFollowupPrompt}
        />
      </div>
    </div>
  );
}

export default function AssistantPage() {
  const {
    conversationId,
    conversations,
    isLoadingConversations,
    isLoadingMessages,
    isSending,
    lastResponse,
    loadConversationMessages,
    loadConversations,
    messages,
    setConversationId,
    setIsSending,
    setLastResponse,
    setMessages,
    showDuplicateConversations,
    toggleDuplicateConversations,
  } = useAssistantConversation();
  const {
    dismissRunRecovery,
    isLoadingChatRuns,
    isRecoveryDismissed,
    recentlyCancelledChatRuns,
    refreshChatRuns,
    runningChatRuns,
  } = useAssistantChatRuns({
    enabled: !isLoadingConversations && conversations.length > 0,
  });
  const {
    draftMutationId,
    draftResolutionById,
    draftStatusById,
    linkedDraft,
    queryDraftResolution,
    setDraftMutationId,
    setDraftResolutionById,
    setDraftStatusById,
    setLinkedDraft,
    setQueryDraftResolution,
  } = useAssistantDrafts();
  const {
    activeReferenceIndex,
    addActionCandidates,
    committedActionCommand,
    dismissedReferencePickerValue,
    isLoadingAddActions,
    isLoadingReferences,
    orderedReferenceCandidates,
    queryReferenceResolution,
    referenceCandidateGroups,
    referenceCandidates,
    rememberReferences,
    selectedReferenceKeys,
    selectedReferences,
    setActiveReferenceIndex,
    setAddActionCandidates,
    setCommittedActionCommand,
    setDismissedReferencePickerValue,
    setIsLoadingAddActions,
    setIsLoadingReferences,
    setQueryReferenceResolution,
    setReferenceCandidates,
    setSelectedReferences,
  } = useAssistantReferences();
  const [activeAddActionIndex, setActiveAddActionIndex] = useState(-1);
  const [addActionQuery, setAddActionQuery] = useState('');
  const [inputValue, setInputValue] = useState('');
  const [isAddMenuOpen, setIsAddMenuOpen] = useState(false);
  const [draftTemplateMarketOpened, setDraftTemplateMarketOpened] = useState(false);
  const [draftTemplates, setDraftTemplates] = useState<AssistantDraftTemplate[]>([]);
  const [isLoadingDraftTemplates, setIsLoadingDraftTemplates] = useState(false);
  const [isContextExpanded, setIsContextExpanded] = useState(false);
  const runtimeStatus = useAssistantRuntimeStatus();
  const [resultWriteTargets, setResultWriteTargets] = useState<ResultWriteTargetRecord[]>([]);
  const [roleQuickTasksExpanded, setRoleQuickTasksExpanded] = useState(false);
  const [roleQuickTaskGroups, setRoleQuickTaskGroups] = useState<AssistantRoleQuickTaskGroup[]>([]);
  const [scheduledJobRunById, setScheduledJobRunById] = useState<Record<string, ScheduledJobRunRecord>>({});
  const addMenuRef = useRef<HTMLDivElement | null>(null);
  const addMenuTriggerRef = useRef<HTMLElement | null>(null);
  const messageListEndRef = useRef<HTMLDivElement | null>(null);
  const queryDraftHydratedRef = useRef(false);
  const queryReferenceHydratedRef = useRef(false);
  const draftTemplatesLoadRequestedRef = useRef(false);
  const resultWriteTargetsLoadRequestedRef = useRef(false);
  const roleQuickTasksLoadRequestedRef = useRef(false);
  const chatAbortControllerRef = useRef<AbortController | null>(null);
  const activeChatRequestRef = useRef<{
    clientRequestId: string;
    content: string;
    references: AssistantReference[];
    runId: string;
  } | null>(null);
  const {
    assistantMetricDetails,
    assistantMetrics,
    assistantMetricsWindowDays,
    changeAssistantMetricsWindow,
    isLoadingMetricDetails,
    isLoadingMetrics,
    loadAssistantMetrics,
    metricsPanelOpened,
    openAssistantMetricDetails,
    openMetricsPanel,
    setMetricsPanelOpened,
  } = useAssistantMetricsPanel();

  const canSend = useMemo(() => inputValue.trim().length > 0, [inputValue]);
  const hasPluginActionDraft = useMemo(
    () => messages.some((item) => actionDraftItems(item.toolResults).some((draft) => draft.action === 'create_plugin_action')),
    [messages],
  );
  const resultWriteTargetLabels = useMemo(
    () => new Map(resultWriteTargets.map((target) => [target.code, target.form_label || target.label])),
    [resultWriteTargets],
  );
  const roleQuickTaskCount = useMemo(
    () => roleQuickTaskGroups.reduce((total, group) => total + group.tasks.length, 0),
    [roleQuickTaskGroups],
  );

  useEffect(() => () => {
    chatAbortControllerRef.current?.abort();
  }, []);

  const activeMention = useMemo(() => {
    const mention = activeMentionRange(inputValue);
    if (!mention) {
      return undefined;
    }
    if (
      mention.markerIndex === 0
      && inputStartsWithActionCommand(inputValue, committedActionCommand)
    ) {
      return undefined;
    }
    return mention.query;
  }, [committedActionCommand, inputValue]);
  const runOncePermissionHint = useMemo(() => (
    scheduledJobRunOnceRequested(inputValue) && !currentUserCanRunScheduledJobFromAssistant()
  ), [inputValue]);
  const shouldShowReferenceCandidates = !isAddMenuOpen
    && activeMention !== undefined
    && dismissedReferencePickerValue !== inputValue;
  const referenceEmptyState: AssistantReferenceEmptyState = useMemo(
    () => assistantReferenceEmptyState(inputValue),
    [inputValue],
  );
  const activeRunPollTargets = useMemo(
    () => scheduledJobRunPollTargets(messages, scheduledJobRunById),
    [messages, scheduledJobRunById],
  );
  useEffect(() => {
    if (typeof messageListEndRef.current?.scrollIntoView !== 'function') {
      return;
    }
    messageListEndRef.current.scrollIntoView({ block: 'end' });
  }, [isLoadingMessages, isSending, messages, scheduledJobRunById]);

  useEffect(() => {
    if (
      committedActionCommand
      && !inputStartsWithActionCommand(inputValue, committedActionCommand)
    ) {
      setCommittedActionCommand(undefined);
    }
  }, [committedActionCommand, inputValue, setCommittedActionCommand]);

  useEffect(() => {
    if (!isAddMenuOpen) {
      return undefined;
    }
    const closeOnOutsideClick = (event: globalThis.MouseEvent | TouchEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (
        addMenuRef.current?.contains(target)
        || addMenuTriggerRef.current?.contains(target)
      ) {
        return;
      }
      setIsAddMenuOpen(false);
    };
    document.addEventListener('mousedown', closeOnOutsideClick);
    document.addEventListener('touchstart', closeOnOutsideClick);
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick);
      document.removeEventListener('touchstart', closeOnOutsideClick);
    };
  }, [isAddMenuOpen]);

  useEffect(() => {
    if (!isAddMenuOpen) {
      setAddActionCandidates([]);
      setActiveAddActionIndex(-1);
      setIsLoadingAddActions(false);
      return undefined;
    }
    let didCancel = false;
    const controller = new AbortController();
    setIsLoadingAddActions(true);
    const timer = window.setTimeout(() => {
      fetchAssistantReferenceCandidates({
        limit: ASSISTANT_ADD_ACTION_LIMIT,
        query: addActionQuery,
        signal: controller.signal,
        type: 'assistant_action',
      })
        .then((items) => {
          if (!didCancel) {
            const actionItems = items.filter(isAssistantActionReference);
            setAddActionCandidates(actionItems);
            setActiveAddActionIndex(actionItems.length ? 0 : -1);
          }
        })
        .catch((error) => {
          if (!didCancel && (error as Error).name !== 'AbortError') {
            toast.error(formatMutationError(error));
            setAddActionCandidates([]);
            setActiveAddActionIndex(-1);
          }
        })
        .finally(() => {
          if (!didCancel) {
            setIsLoadingAddActions(false);
          }
        });
    }, ASSISTANT_REFERENCE_CANDIDATE_DEBOUNCE_MS);
    return () => {
      didCancel = true;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [
    addActionQuery,
    isAddMenuOpen,
    setAddActionCandidates,
    setIsLoadingAddActions,
  ]);

  useEffect(() => {
    if (!activeRunPollTargets.length) {
      return undefined;
    }
    let didCancel = false;
    let didShowError = false;

    const pollRuns = async () => {
      const targetsByJobId = new Map<string, AssistantScheduledJobRunItem[]>();
      activeRunPollTargets.forEach((target) => {
        const jobKey = target.scheduledJobId ?? '';
        targetsByJobId.set(jobKey, [...(targetsByJobId.get(jobKey) ?? []), target]);
      });
      try {
        await Promise.all(
          [...targetsByJobId.entries()].map(async ([scheduledJobId, targets]) => {
            const runIds = new Set(targets.map((target) => target.id));
            const runs = await fetchScheduledJobRuns(
              scheduledJobId ? { scheduledJobId } : {},
            );
            if (didCancel) {
              return;
            }
            const relevantRuns = runs.filter((run) => runIds.has(run.id));
            if (!relevantRuns.length) {
              return;
            }
            setScheduledJobRunById((currentItems) => {
              let changed = false;
              const nextItems = { ...currentItems };
              relevantRuns.forEach((run) => {
                if (!scheduledJobRunRecordChanged(currentItems[run.id], run)) {
                  return;
                }
                nextItems[run.id] = run;
                changed = true;
              });
              return changed ? nextItems : currentItems;
            });
          }),
        );
      } catch (error) {
        if (!didCancel && !didShowError) {
          didShowError = true;
          toast.error(formatMutationError(error));
        }
      }
    };

    void pollRuns();
    const pollTimer = window.setInterval(() => {
      void pollRuns();
    }, SCHEDULED_JOB_RUN_POLL_INTERVAL_MS);
    return () => {
      didCancel = true;
      window.clearInterval(pollTimer);
    };
  }, [activeRunPollTargets]);

  useEffect(() => {
    if (queryDraftHydratedRef.current) {
      return undefined;
    }
    const draftId = assistantQueryDraftId();
    if (!draftId) {
      return undefined;
    }
    queryDraftHydratedRef.current = true;
    let didCancel = false;
    setQueryDraftResolution({
      draftId,
      status: 'loading',
    });
    getAssistantActionDraft(draftId)
      .then(async (draft) => {
        if (didCancel) {
          return;
        }
        let viewedDraft = draft;
        try {
          viewedDraft = await markAssistantActionDraftViewed(draft.id, 'deeplink');
        } catch (error) {
          toast.warning(formatMutationError(error));
        }
        if (didCancel) {
          return;
        }
        const toolItem = assistantActionDraftRecordToToolItem(viewedDraft);
        setLinkedDraft(toolItem);
        setDraftStatusById((items) => ({ ...items, [viewedDraft.id]: viewedDraft.status }));
        const resultResolution = assistantDraftResultRunResolution(viewedDraft);
        if (resultResolution) {
          const draftIds = assistantDraftResolutionIds(viewedDraft);
          draftIds.forEach((itemDraftId) => {
            rememberAssistantDraftResolution({
              draftId: itemDraftId,
              resourceId: resultResolution.resource_id,
              resourceType: resultResolution.resource_type,
              scheduledJobRunId: resultResolution.scheduled_job_run_id,
              title: resultResolution.title,
            });
          });
          setDraftResolutionById((items) => {
            const nextItems = { ...items };
            draftIds.forEach((itemDraftId) => {
              nextItems[itemDraftId] = resultResolution;
            });
            return nextItems;
          });
        }
        setQueryDraftResolution({
          draftId,
          status: 'resolved',
          title: viewedDraft.title,
        });
      })
      .catch((error) => {
        if (!didCancel) {
          const messageText = formatMutationError(error);
          toast.error(messageText);
          setQueryDraftResolution({
            draftId,
            message: messageText,
            status: 'failed',
          });
        }
      });
    return () => {
      didCancel = true;
    };
  }, [setDraftResolutionById, setDraftStatusById, setLinkedDraft, setQueryDraftResolution]);

  useEffect(() => {
    if (queryReferenceHydratedRef.current) {
      return undefined;
    }
    const queryReference = assistantQueryReferenceParams();
    if (!queryReference) {
      return undefined;
    }
    queryReferenceHydratedRef.current = true;
    if (queryReference.prompt) {
      setInputValue(queryReference.prompt);
    }
    let didCancel = false;
    setQueryReferenceResolution({
      referenceId: queryReference.referenceId,
      referenceType: queryReference.referenceType,
      status: 'loading',
    });
    fetchAssistantReferenceCandidates({
      limit: 1,
      query: queryReference.referenceId,
      type: queryReference.referenceType,
    })
      .then((items) => {
        if (didCancel) {
          return;
        }
        const reference = items.find(
          (item) => item.id === queryReference.referenceId && item.type === queryReference.referenceType,
        );
        if (!reference) {
          toast.warning('引用对象不存在或无权限');
          setQueryReferenceResolution({
            message: '不存在或无权限',
            referenceId: queryReference.referenceId,
            referenceType: queryReference.referenceType,
            status: 'failed',
          });
          return;
        }
        setQueryReferenceResolution({
          referenceId: queryReference.referenceId,
          referenceType: queryReference.referenceType,
          status: 'resolved',
          title: reference.title,
        });
        if (isAssistantActionReference(reference)) {
          const command = assistantActionCommand(reference);
          setCommittedActionCommand(command);
          setInputValue(inputWithAssistantActionCommand(queryReference.prompt ?? '', reference));
          return;
        }
        setSelectedReferences((currentItems) => (
          currentItems.some((item) => item.id === reference.id && item.type === reference.type)
            ? currentItems
            : [...currentItems, reference]
        ));
        rememberReferences([reference]);
      })
      .catch((error) => {
        if (!didCancel) {
          const messageText = formatMutationError(error);
          toast.error(messageText);
          setQueryReferenceResolution({
            message: messageText,
            referenceId: queryReference.referenceId,
            referenceType: queryReference.referenceType,
            status: 'failed',
          });
        }
      });
    return () => {
      didCancel = true;
    };
  }, [
    rememberReferences,
    setCommittedActionCommand,
    setQueryReferenceResolution,
    setSelectedReferences,
  ]);

  useEffect(() => {
    const query = activeMention;
    if (query === undefined) {
      setReferenceCandidates([]);
      setIsLoadingReferences(false);
      return;
    }
    let didCancel = false;
    const controller = new AbortController();
    setIsLoadingReferences(true);
    const timer = window.setTimeout(() => {
      fetchAssistantReferenceCandidates({
        limit: ASSISTANT_REFERENCE_CANDIDATE_LIMIT,
        query,
        signal: controller.signal,
      })
        .then((items) => {
          if (!didCancel) {
            const nextCandidates = items.filter(
              (reference) => !selectedReferenceKeys.has(referenceKey(reference)),
            );
            setReferenceCandidates(nextCandidates);
            setActiveReferenceIndex(nextCandidates.length ? 0 : -1);
          }
        })
        .catch((error) => {
          if (!didCancel && (error as Error).name !== 'AbortError') {
            toast.error(formatMutationError(error));
            setReferenceCandidates([]);
          }
        })
        .finally(() => {
          if (!didCancel) {
            setIsLoadingReferences(false);
          }
        });
    }, ASSISTANT_REFERENCE_CANDIDATE_DEBOUNCE_MS);
    return () => {
      didCancel = true;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [
    activeMention,
    selectedReferenceKeys,
    setActiveReferenceIndex,
    setIsLoadingReferences,
    setReferenceCandidates,
  ]);

  useEffect(() => {
    setActiveReferenceIndex((index) => {
      if (!orderedReferenceCandidates.length) {
        return -1;
      }
      return Math.min(Math.max(index, 0), orderedReferenceCandidates.length - 1);
    });
  }, [orderedReferenceCandidates.length, setActiveReferenceIndex]);

  useEffect(() => {
    if (!getStoredCurrentUser() || roleQuickTasksLoadRequestedRef.current) {
      return undefined;
    }
    let didCancel = false;
    roleQuickTasksLoadRequestedRef.current = true;
    fetchAssistantRoleQuickTasks()
      .then((groups) => {
        if (!didCancel) {
          setRoleQuickTaskGroups(groups);
        }
      })
      .catch(() => {
        if (!didCancel) {
          setRoleQuickTaskGroups([]);
        }
      });
    return () => {
      didCancel = true;
    };
  }, []);

  const loadDraftTemplates = useCallback(async () => {
    if (draftTemplatesLoadRequestedRef.current) {
      return;
    }
    draftTemplatesLoadRequestedRef.current = true;
    setIsLoadingDraftTemplates(true);
    try {
      setDraftTemplates(await fetchAssistantDraftTemplates());
    } catch (error) {
      draftTemplatesLoadRequestedRef.current = false;
      toast.error(formatMutationError(error));
    } finally {
      setIsLoadingDraftTemplates(false);
    }
  }, []);

  useEffect(() => {
    if (!hasPluginActionDraft || resultWriteTargetsLoadRequestedRef.current) {
      return;
    }
    let didCancel = false;
    resultWriteTargetsLoadRequestedRef.current = true;
    fetchResultWriteTargets()
      .then((items) => {
        if (!didCancel) {
          setResultWriteTargets(items);
        }
      })
      .catch((error) => {
        if (!didCancel) {
          toast.error(formatMutationError(error));
        }
      });
    return () => {
      didCancel = true;
    };
  }, [hasPluginActionDraft]);

  const resetComposerState = (options: { clearInput?: boolean; keepDraftLink?: boolean } = {}) => {
    if (options.clearInput) {
      setInputValue('');
    }
    setActiveReferenceIndex(-1);
    setActiveAddActionIndex(-1);
    setAddActionQuery('');
    setIsAddMenuOpen(false);
    setReferenceCandidates([]);
    setCommittedActionCommand(undefined);
    setDismissedReferencePickerValue(undefined);
    setSelectedReferences([]);
    setQueryReferenceResolution(undefined);
    setIsContextExpanded(false);
    if (!options.keepDraftLink) {
      setLinkedDraft(undefined);
      setQueryDraftResolution(undefined);
    }
  };

  const startNewConversation = () => {
    setConversationId(undefined);
    setLastResponse(undefined);
    setMessages(welcomeMessages);
    resetComposerState({ clearInput: true });
  };

  const openDraftTemplateMarket = () => {
    setDraftTemplateMarketOpened(true);
    void loadDraftTemplates();
  };

  const applyDraftTemplate = (template: AssistantDraftTemplate) => {
    setCommittedActionCommand(undefined);
    setInputValue(template.prompt);
  };

  const addSelectedReference = (reference: AssistantReference) => {
    if (isAssistantActionReference(reference)) {
      const command = assistantActionCommand(reference);
      const nextInputValue = inputWithAssistantActionCommand(inputValue, reference);
      setCommittedActionCommand(command);
      setInputValue(nextInputValue);
      setDismissedReferencePickerValue(nextInputValue);
      setActiveReferenceIndex(-1);
      setReferenceCandidates([]);
      return;
    }
    if (isScheduledJobCommandReference(reference)) {
      const command = scheduledJobCommand(reference);
      const nextInputValue = inputWithScheduledJobCommand(inputValue, reference);
      setCommittedActionCommand(command);
      setInputValue(nextInputValue);
      setDismissedReferencePickerValue(nextInputValue);
      setSelectedReferences((items) => (
        items.some((item) => item.id === reference.id && item.type === reference.type)
          ? items
          : [...items, reference]
      ));
      rememberReferences([reference]);
      setActiveReferenceIndex(-1);
      setReferenceCandidates([]);
      return;
    }
    setDismissedReferencePickerValue(inputValue);
    setSelectedReferences((items) => (
      items.some((item) => item.id === reference.id && item.type === reference.type)
        ? items
        : [...items, reference]
    ));
    rememberReferences([reference]);
    setActiveReferenceIndex(-1);
    setReferenceCandidates([]);
  };

  const toggleAddMenu = () => {
    const nextOpen = !isAddMenuOpen;
    setIsAddMenuOpen(nextOpen);
    if (!nextOpen) {
      setAddActionCandidates([]);
      return;
    }
    setAddActionQuery('');
    setAddActionCandidates([]);
    setActiveAddActionIndex(-1);
    setDismissedReferencePickerValue(inputValue);
    setReferenceCandidates([]);
    setActiveReferenceIndex(-1);
  };

  const changeAddActionQuery = (query: string) => {
    setAddActionQuery(query);
    setAddActionCandidates([]);
    setActiveAddActionIndex(-1);
  };

  const selectAddActionCandidate = (reference: AssistantReference) => {
    addSelectedReference(reference);
    setIsAddMenuOpen(false);
  };

  const handleAddActionMenuKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      setIsAddMenuOpen(false);
      return;
    }
    if (!addActionCandidates.length) {
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveAddActionIndex((index) => (index + 1) % addActionCandidates.length);
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveAddActionIndex((index) => (
        index <= 0 ? addActionCandidates.length - 1 : index - 1
      ));
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      const reference = addActionCandidates[Math.max(activeAddActionIndex, 0)];
      if (reference) {
        selectAddActionCandidate(reference);
      }
    }
  };

  const removeSelectedReference = (reference: AssistantReference) => {
    if (
      queryReferenceResolution?.referenceId === reference.id
      && queryReferenceResolution.referenceType === reference.type
    ) {
      setQueryReferenceResolution(undefined);
    }
    setSelectedReferences((items) => (
      items.filter((item) => !(item.id === reference.id && item.type === reference.type))
    ));
  };

  const commandReferenceCandidates = (messageText: string) => {
    if (!scheduledJobRunOnceRequested(messageText)) {
      return [];
    }
    const scheduledJobReference = uniqueScheduledJobReferenceCandidate(orderedReferenceCandidates);
    return scheduledJobReference ? [scheduledJobReference] : [];
  };

  const resolveCommandReferenceCandidates = async (messageText: string) => {
    const currentCandidates = commandReferenceCandidates(messageText);
    if (currentCandidates.length || !scheduledJobRunOnceRequested(messageText)) {
      return currentCandidates;
    }
    const query = activeMentionQuery(messageText);
    if (query === undefined) {
      return [];
    }
    try {
      const items = await fetchAssistantReferenceCandidates({
        limit: ASSISTANT_REFERENCE_CANDIDATE_LIMIT,
        query,
        type: 'scheduled_job',
      });
      const scheduledJobReference = uniqueScheduledJobReferenceCandidate(items);
      return scheduledJobReference ? [scheduledJobReference] : [];
    } catch {
      return [];
    }
  };

  const submitComposerEnter = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.shiftKey || event.nativeEvent.isComposing) {
      return false;
    }
    event.preventDefault();
    if (isSending && assistantStopCommandRequested(inputValue)) {
      stopGenerating();
      return true;
    }
    if (scheduledJobRunOnceRequested(inputValue)) {
      const commandReferences = commandReferenceCandidates(inputValue);
      void sendMessage(inputValue, commandReferences.length ? commandReferences : undefined);
      return true;
    }
    const reference = orderedReferenceCandidates[Math.max(activeReferenceIndex, 0)];
    if (reference) {
      addSelectedReference(reference);
      return true;
    }
    void sendMessage();
    return true;
  };

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.defaultPrevented) {
      return;
    }
    if (event.key === 'Escape' && isAddMenuOpen) {
      event.preventDefault();
      setIsAddMenuOpen(false);
      return;
    }
    if (event.key === 'Enter' && submitComposerEnter(event)) {
      return;
    }
    if (!orderedReferenceCandidates.length) {
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveReferenceIndex((index) => (index + 1) % orderedReferenceCandidates.length);
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveReferenceIndex((index) => (
        index <= 0 ? orderedReferenceCandidates.length - 1 : index - 1
      ));
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      setActiveReferenceIndex(-1);
      setReferenceCandidates([]);
    }
  };

  const loadConversation = async (
    targetConversationId: string,
    options: { preserveComposer?: boolean } = {},
  ) => {
    if (options.preserveComposer) {
      setIsAddMenuOpen(false);
      setReferenceCandidates([]);
      setActiveReferenceIndex(-1);
      setDismissedReferencePickerValue(inputValue);
    } else {
      resetComposerState({ clearInput: true });
    }
    setConversationId(targetConversationId);
    await loadConversationMessages(targetConversationId);
  };

  const hasUnsentComposerState = () => (
    inputValue.trim().length > 0
    || selectedReferences.length > 0
    || Boolean(committedActionCommand)
    || Boolean(queryReferenceResolution)
  );

  const openConversation = (targetConversationId: string) => {
    if (targetConversationId === conversationId) {
      return;
    }
    if (!hasUnsentComposerState()) {
      void loadConversation(targetConversationId, { preserveComposer: false });
      return;
    }
    Modal.confirm({
      cancelText: '丢弃并切换',
      content: '当前输入框或引用上下文尚未发送，可以保留到目标会话，也可以丢弃后切换。',
      okText: '保留并切换',
      title: '切换历史会话',
      onCancel: () => {
        void loadConversation(targetConversationId, { preserveComposer: false });
      },
      onOk: () => {
        void loadConversation(targetConversationId, { preserveComposer: true });
      },
    });
  };

  const sendMessage = async (
    messageText = inputValue,
    referenceOverrides?: AssistantReference[],
    options: { replaceReferences?: boolean } = {},
  ) => {
    const content = messageText.trim();
    if (!content) {
      return;
    }
    if (isSending) {
      if (assistantStopCommandRequested(content)) {
        stopGenerating();
      }
      return;
    }
    const controller = new AbortController();
    const runId = createAssistantChatRunId();
    const clientRequestId = runId;
    chatAbortControllerRef.current?.abort();
    chatAbortControllerRef.current = controller;
    activeChatRequestRef.current = {
      clientRequestId,
      content,
      references: selectedReferences,
      runId,
    };
    setIsSending(true);
    const commandReferences = referenceOverrides ?? await resolveCommandReferenceCandidates(content);
    if (controller.signal.aborted) {
      return;
    }
    const baseReferences = options.replaceReferences ? [] : selectedReferences;
    const referencesForRequest = mergeReferences(
      baseReferences,
      commandReferences,
    );
    activeChatRequestRef.current = {
      clientRequestId,
      content,
      references: referencesForRequest,
      runId,
    };
    rememberReferences(referencesForRequest);
    const userMessage: ChatMessage = {
      clientRequestId,
      content,
      id: `user-${Date.now()}`,
      references: referencesForRequest,
      role: 'user',
      runId,
      status: 'pending',
    };
    setMessages((items) => [...items, userMessage]);
    setInputValue('');
    setIsAddMenuOpen(false);
    setCommittedActionCommand(undefined);
    try {
      const response = await chatWithAssistant({
        clientRequestId,
        context: { source: 'assistant-page' },
        conversationId,
        message: content,
        references: referencesForRequest,
        runId,
        signal: controller.signal,
      });
      setConversationId(response.conversationId);
      setLastResponse(response);
      setActiveReferenceIndex(-1);
      setSelectedReferences([]);
      setReferenceCandidates([]);
      setMessages((items) => [
        ...items.map((item) => (
          item.runId === runId ? { ...item, status: 'completed' } : item
        )),
        {
          content: response.content,
          id: response.messageId,
          intent: response.intent,
          references: response.references,
          role: 'assistant',
          runId: response.runId ?? runId,
          status: response.status,
          toolResults: response.toolResults,
        },
      ]);
      await loadConversations();
    } catch (error) {
      if (isAbortError(error)) {
        return;
      }
      toast.error(assistantChatErrorMessage(error));
      setMessages((items) => [
        ...items,
        {
          content: assistantChatErrorMessage(error),
          clientRequestId,
          failedRequest: {
            content,
            references: referencesForRequest,
          },
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
          runId,
          status: 'failed',
        },
      ]);
    } finally {
      if (chatAbortControllerRef.current === controller) {
        chatAbortControllerRef.current = null;
        activeChatRequestRef.current = null;
        setIsSending(false);
      }
    }
  };

  const stopGenerating = () => {
    const activeRequest = activeChatRequestRef.current;
    if (activeRequest?.runId) {
      void cancelAssistantChatRun(activeRequest.runId).catch(() => {
        // The browser-side abort is still useful even if the server run already finished.
      });
    }
    chatAbortControllerRef.current?.abort();
    chatAbortControllerRef.current = null;
    activeChatRequestRef.current = null;
    setIsSending(false);
    setInputValue((current) => (current.trim() ? current : activeRequest?.content ?? current));
    if (activeRequest?.references.length) {
      setSelectedReferences((current) => (current.length ? current : activeRequest.references));
    }
    setReferenceCandidates([]);
    setActiveReferenceIndex(-1);
    setMessages((items) => [
      ...items.map((item) => (
        activeRequest?.runId && item.runId === activeRequest.runId
          ? { ...item, status: 'cancelled' }
          : item
      )),
      {
        clientRequestId: activeRequest?.clientRequestId,
        content: '已停止生成，可继续输入终止或新的指令。',
        id: `assistant-stopped-${Date.now()}`,
        role: 'assistant',
        runId: activeRequest?.runId,
        status: 'cancelled',
      },
    ]);
  };

  const retryFailedRequest = (request: NonNullable<ChatMessage['failedRequest']>) => {
    void sendMessage(request.content, request.references, { replaceReferences: true });
  };

  const restoreFailedRequest = (request: NonNullable<ChatMessage['failedRequest']>) => {
    setInputValue(request.content);
    setSelectedReferences(request.references);
    setReferenceCandidates([]);
    setActiveReferenceIndex(-1);
    setDismissedReferencePickerValue(undefined);
  };

  const rememberDraftResolution = (
    draft: AssistantToolResultItem,
    resourceId?: string,
    resourceType?: string,
    title?: string,
    scheduledJobRunId?: string,
  ) => {
    if (!resourceId) {
      return;
    }
    if (
      resourceType !== 'assistant_analysis'
      && resourceType !== 'ai_agent'
      && resourceType !== 'ai_skill'
      && resourceType !== 'ai_task'
      && resourceType !== 'plugin_action'
      && resourceType !== 'plugin_connection'
      && resourceType !== 'scheduled_job'
    ) {
      return;
    }
    const draftIds = new Set(
      [draft.draft_id, draft.client_draft_id, draft.server_draft_id]
        .map((value) => (value ? String(value) : undefined))
        .filter(Boolean) as string[],
    );
    draftIds.forEach((draftId) => {
      rememberAssistantDraftResolution({
        draftId,
        resourceId,
        resourceType,
        scheduledJobRunId,
        title,
      });
    });
    setDraftResolutionById((items) => {
      const resolution: AssistantDraftResolutionRecord = {
        resource_id: resourceId,
        resource_type: resourceType,
      };
      if (title) {
        resolution.title = title;
      }
      if (scheduledJobRunId) {
        resolution.scheduled_job_run_id = scheduledJobRunId;
      }
      const next = { ...items };
      draftIds.forEach((draftId) => {
        next[draftId] = resolution;
      });
      return next;
    });
  };

  const regenerateDraft = (draft: AssistantToolResultItem) => {
    setInputValue(draftRegeneratePrompt(draft));
  };

  const useScheduledJobRunFollowupPrompt = (
    item: AssistantToolResultItem,
    prompt: string,
  ) => {
    const reference = scheduledJobRunReferenceFromToolItem(item);
    if (reference) {
      addSelectedReference(reference);
    }
    setInputValue(scheduledJobRunFollowupPrompt(item, prompt));
  };

  const useScheduledJobRunCardFollowupPrompt = (
    item: AssistantScheduledJobRunItem,
    prompt: string,
  ) => {
    addSelectedReference(scheduledJobRunReferenceFromRunItem(item));
    setInputValue(scheduledJobRunItemFollowupPrompt(item, prompt));
  };

  const usePluginConnectionFollowupPrompt = (
    item: AssistantToolResultItem,
    prompt: string,
  ) => {
    const reference = pluginConnectionReferenceFromDiagnosticItem(item);
    if (reference) {
      addSelectedReference(reference);
    }
    setInputValue(pluginConnectionDiagnosticFollowupPrompt(item, prompt));
  };

  const viewDraft = async (draft: AssistantToolResultItem) => {
    const draftId = assistantDraftId(draft);
    if (!draftId) {
      return draft;
    }
    try {
      const result = await markAssistantActionDraftViewed(draftId, 'detail_modal');
      const viewedItem = assistantActionDraftRecordToToolItem(result);
      const toolItem = {
        ...draft,
        ...viewedItem,
        payload: viewedItem.payload ?? draft.payload,
        preview: viewedItem.preview ?? draft.preview,
        wizard_steps: viewedItem.wizard_steps ?? draft.wizard_steps,
      };
      setDraftStatusById((items) => ({ ...items, [draftId]: result.status }));
      setLinkedDraft((currentDraft) => (
        assistantDraftId(currentDraft) === draftId ? toolItem : currentDraft
      ));
      return toolItem;
    } catch (error) {
      toast.warning(formatMutationError(error));
      return draft;
    }
  };

  const confirmDraft = async (draft: AssistantToolResultItem) => {
    const draftId = assistantDraftId(draft);
    if (!draftId) {
      return;
    }
    setDraftMutationId(draftId);
    try {
      const result = await confirmAssistantActionDraft(draftId);
      setDraftStatusById((items) => ({ ...items, [draftId]: result.draft.status }));
      setLinkedDraft((currentDraft) => (
        assistantDraftId(currentDraft) === draftId
          ? assistantActionDraftRecordToToolItem(result.draft)
          : currentDraft
      ));
      rememberDraftResolution(
        draft,
        result.run.result_id,
        result.run.result_type,
        result.draft.title,
        scheduledJobRunIdFromActionResult(result.run.result),
      );
      toast.success('草案已应用');
    } catch (error) {
      const errorMessage = formatMutationError(error);
      try {
        const latestDraft = await getAssistantActionDraft(draftId);
        const latestToolItem = assistantActionDraftRecordToToolItem(latestDraft);
        setDraftStatusById((items) => ({ ...items, [draftId]: latestDraft.status }));
        setLinkedDraft((currentDraft) => (
          assistantDraftId(currentDraft) === draftId
            ? latestToolItem
            : currentDraft
        ));
        toast.error(`${errorMessage}；已同步服务端草案状态：${draftStatusLabel(latestDraft.status).text}`);
      } catch {
        setDraftStatusById((items) => ({ ...items, [draftId]: 'unknown' }));
        toast.error(`${errorMessage}；确认状态未知，可重试。`);
      }
    } finally {
      setDraftMutationId(undefined);
    }
  };

  const cancelDraft = async (draft: AssistantToolResultItem) => {
    const draftId = assistantDraftId(draft);
    if (!draftId) {
      return;
    }
    setDraftMutationId(draftId);
    try {
      const result = await cancelAssistantActionDraft(draftId, '用户在 AI 助手取消');
      setDraftStatusById((items) => ({ ...items, [draftId]: result.status }));
      setLinkedDraft((currentDraft) => (
        assistantDraftId(currentDraft) === draftId
          ? assistantActionDraftRecordToToolItem(result)
          : currentDraft
      ));
      toast.success('草案已取消');
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setDraftMutationId(undefined);
    }
  };

  return (
    <PageContainer title={false}>
      <div className="assistant-workspace">
        <AssistantSidebar
          conversationId={conversationId}
          conversations={conversations}
          isLoadingConversations={isLoadingConversations}
          isLoadingMetrics={isLoadingMetrics}
          showDuplicateConversations={showDuplicateConversations}
          roleQuickTaskCount={roleQuickTaskCount}
          roleQuickTaskGroups={roleQuickTaskGroups}
          roleQuickTasksExpanded={roleQuickTasksExpanded}
          onToggleDuplicateConversations={toggleDuplicateConversations}
          onOpenConversation={openConversation}
          onOpenDraftTemplateMarket={openDraftTemplateMarket}
          onOpenMetricsPanel={openMetricsPanel}
          onStartNewConversation={startNewConversation}
          onToggleRoleQuickTasks={() => setRoleQuickTasksExpanded((expanded) => !expanded)}
          onUseRoleTask={setInputValue}
        />
        <section className="assistant-chat-panel">
          <div className="assistant-chat-header">
            <div className="assistant-chat-title-block">
              <Title className="assistant-chat-title" level={3}>研发助手</Title>
              <Text className="assistant-chat-subtitle" type="secondary">研发大脑系统问答</Text>
            </div>
            {lastResponse ? (
              <Space size={8} wrap>
                <Tag color="blue">{lastResponse.model}</Tag>
                <Tag>{lastResponse.latencyMs} ms</Tag>
              </Space>
            ) : null}
          </div>
          <AssistantRuntimeStatus runtimeStatus={runtimeStatus} />
          <AssistantChatRunRecovery
            isLoading={isLoadingChatRuns}
            isVisible={!isRecoveryDismissed}
            recentlyCancelledRuns={recentlyCancelledChatRuns}
            runningRuns={runningChatRuns}
            onDismiss={dismissRunRecovery}
            onOpenConversation={(targetConversationId) => {
              void loadConversation(targetConversationId, { preserveComposer: true });
            }}
            onRefresh={() => void refreshChatRuns()}
          />
          <AssistantMessageList
            endRef={messageListEndRef}
            isLoadingMessages={isLoadingMessages}
            isSending={isSending}
          >
            {queryDraftResolution ? (
              <div
                aria-label="草案链接状态"
                className={`assistant-query-draft-status assistant-query-draft-status-${queryDraftResolution.status}`}
              >
                <Space size={6} wrap>
                  <Tag color={queryDraftResolutionLabel(queryDraftResolution.status).color}>
                    {queryDraftResolutionLabel(queryDraftResolution.status).text}
                  </Tag>
                  <Text type={queryDraftResolution.status === 'failed' ? 'danger' : 'secondary'}>
                    {queryDraftResolutionText(queryDraftResolution)}
                  </Text>
                </Space>
                {linkedDraft ? (
                  <AssistantActionDraftCards
                    draftMutationId={draftMutationId}
                    draftResolutionById={draftResolutionById}
                    drafts={[linkedDraft]}
                    draftStatusById={draftStatusById}
                    onCancelDraft={cancelDraft}
                    onConfirmDraft={confirmDraft}
                    onRegenerateDraft={regenerateDraft}
                    onViewDraft={viewDraft}
                    onUseDraftWizardStepPrompt={setInputValue}
                    resultWriteTargetLabels={resultWriteTargetLabels}
                  />
                ) : null}
              </div>
            ) : null}
            {messages.map((item) => (
              <AssistantBubble
                draftMutationId={draftMutationId}
                draftResolutionById={draftResolutionById}
                draftStatusById={draftStatusById}
                key={item.id}
                message={item}
                onCancelDraft={cancelDraft}
                onConfirmDraft={confirmDraft}
                onRegenerateDraft={regenerateDraft}
                onRestoreFailedRequest={restoreFailedRequest}
                onRetryFailedRequest={retryFailedRequest}
                onViewDraft={viewDraft}
                onUseConnectionFollowupPrompt={usePluginConnectionFollowupPrompt}
                onUseRunCardFollowupPrompt={useScheduledJobRunCardFollowupPrompt}
                onUseRunFollowupPrompt={useScheduledJobRunFollowupPrompt}
                onUseTaskGuidePrompt={setInputValue}
                resultWriteTargetLabels={resultWriteTargetLabels}
                scheduledJobRunById={scheduledJobRunById}
              />
            ))}
          </AssistantMessageList>
          {lastResponse?.suggestions.length ? (
            <div className="assistant-suggestions">
              {lastResponse.suggestions.map((suggestion) => (
                <Button key={suggestion} size="small" onClick={() => setInputValue(suggestion)}>
                  {suggestion}
                </Button>
              ))}
            </div>
          ) : null}
          <AssistantReferenceContext
            isExpanded={isContextExpanded}
            queryReferenceResolution={queryReferenceResolution}
            selectedReferences={selectedReferences}
            onRemoveReference={removeSelectedReference}
            onToggleExpanded={() => setIsContextExpanded((expanded) => !expanded)}
          />
          <AssistantComposer
            addActionCandidates={addActionCandidates}
            activeAddActionIndex={activeAddActionIndex}
            addMenuRef={addMenuRef}
            addActionQuery={addActionQuery}
            canSend={canSend}
            inputValue={inputValue}
            isAddMenuOpen={isAddMenuOpen}
            isLoadingAddActions={isLoadingAddActions}
            isSending={isSending}
            referencePicker={shouldShowReferenceCandidates ? (
              <AssistantReferencePicker
                activeMention={activeMention}
                activeReferenceIndex={activeReferenceIndex}
                candidateGroups={referenceCandidateGroups}
                emptyState={referenceEmptyState}
                isLoading={isLoadingReferences}
                referenceCount={referenceCandidates.length}
                onAddReference={addSelectedReference}
                onHoverReference={setActiveReferenceIndex}
                onUseEmptyPrompt={() => {
                  setInputValue(referenceEmptyState.prompt);
                  setReferenceCandidates([]);
                  setActiveReferenceIndex(-1);
                  setDismissedReferencePickerValue(undefined);
                }}
              />
            ) : undefined}
            runOncePermissionHint={runOncePermissionHint}
            onChangeInput={(value) => {
              setInputValue(value);
              setDismissedReferencePickerValue(undefined);
            }}
            onChangeAddActionQuery={changeAddActionQuery}
            onCloseAddMenu={() => setIsAddMenuOpen(false)}
            onHoverAddAction={setActiveAddActionIndex}
            onAddActionMenuKeyDown={handleAddActionMenuKeyDown}
            onKeyDown={handleComposerKeyDown}
            onPressEnter={(event) => {
              if (event.defaultPrevented || submitComposerEnter(event)) {
                return;
              }
            }}
            onSelectAddActionCandidate={selectAddActionCandidate}
            onSend={() => void sendMessage()}
            onSetAddMenuTrigger={(node) => {
              addMenuTriggerRef.current = node;
            }}
            onStopSending={stopGenerating}
            onToggleAddMenu={toggleAddMenu}
          />
        </section>
      </div>
      <Modal
        className="assistant-workbench-modal"
        footer={null}
        open={draftTemplateMarketOpened}
        title="草案模板市场"
        width={720}
        onCancel={() => setDraftTemplateMarketOpened(false)}
      >
        <AssistantDraftTemplateMarket
          isLoading={isLoadingDraftTemplates}
          templates={draftTemplates}
          onUseTemplate={(template) => {
            applyDraftTemplate(template);
            setDraftTemplateMarketOpened(false);
          }}
        />
      </Modal>
      <Modal
        className="assistant-workbench-modal"
        footer={null}
        open={metricsPanelOpened}
        title="助手效果指标"
        width={760}
        onCancel={() => setMetricsPanelOpened(false)}
      >
        <AssistantMetricsPanel
          isDetailLoading={isLoadingMetricDetails}
          isLoading={isLoadingMetrics}
          metricDetails={assistantMetricDetails}
          metrics={assistantMetrics}
          onChangeWindow={changeAssistantMetricsWindow}
          onOpenDetail={openAssistantMetricDetails}
          onRefresh={() => void loadAssistantMetrics()}
          windowDays={assistantMetricsWindowDays}
        />
      </Modal>
    </PageContainer>
  );
}
