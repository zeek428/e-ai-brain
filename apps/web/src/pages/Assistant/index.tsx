import {
  AppstoreOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  LinkOutlined,
  MessageOutlined,
  PlusOutlined,
  ProjectOutlined,
  ReloadOutlined,
  RobotOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Input, Modal, Space, Spin, Tag, Typography, message as toast } from 'antd';
import { type KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
  ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
  ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
  cancelAssistantActionDraft,
  chatWithAssistant,
  confirmAssistantActionDraft,
  fetchAssistantConversationMessages,
  fetchAssistantConversations,
  fetchAssistantDraftTemplates,
  fetchAssistantMetrics,
  fetchAssistantReferenceCandidates,
  fetchScheduledJobRuns,
  fetchResultWriteTargets,
  getStoredCurrentUser,
  readAssistantDraftResolutions,
  rememberAssistantDraftResolution,
  type AssistantActionDraftPreview,
  type AssistantChatResponse,
  type AssistantConversationMessage,
  type AssistantDraftTemplate,
  type AssistantMetrics,
  type AssistantReference,
  type AssistantConversationSummary,
  type AssistantDraftResolutionMap,
  type AssistantDraftResolutionRecord,
  type AssistantToolResult,
  type AssistantToolResultItem,
  type ResultWriteTargetRecord,
  type ScheduledJobRunRecord,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';

const { Text, Title } = Typography;
const { TextArea } = Input;
const ASSISTANT_REFERENCE_CANDIDATE_LIMIT = 12;
const ASSISTANT_KNOWLEDGE_CONTEXT_CHUNK_LIMIT = 8;
const assistantDraftActionLabels: Record<string, string> = {
  create_ai_agent: '创建AI角色',
  create_ai_skill: '创建AI Skill',
  create_analysis_draft: '创建分析草案',
  create_plugin_action: '创建插件动作',
  create_plugin_connection: '创建插件连接',
  create_scheduled_job: '创建定时作业',
};

type ChatMessage = {
  content: string;
  id: string;
  references?: AssistantReference[];
  role: 'assistant' | 'user';
  toolResults?: AssistantToolResult[];
};

type QueryReferenceResolution = {
  message?: string;
  referenceId: string;
  referenceType: string;
  status: 'failed' | 'loading' | 'resolved';
  title?: string;
};

const welcomeMessages: ChatMessage[] = [
  {
    content: '我在，直接问我当前进展。',
    id: 'assistant-welcome',
    role: 'assistant',
  },
];

const starterPrompts = [
  {
    icon: <ProjectOutlined />,
    label: '项目进展',
    prompt: 'AI Brain 项目现在开发到哪里了？',
  },
  {
    icon: <DatabaseOutlined />,
    label: '系统数据',
    prompt: '当前产品、需求、任务和知识沉淀情况如何？',
  },
  {
    icon: <ExclamationCircleOutlined />,
    label: '阻塞与待确认',
    prompt: '当前迭代有哪些阻塞需求、待确认 Review、代码评审结论和高风险 Bug？',
  },
  {
    icon: <ClockCircleOutlined />,
    label: '模型网关',
    prompt: '模型网关和 GitHub PR Review 链路现在是否可用？',
  },
];

type AssistantRoleQuickTask = {
  key: string;
  label: string;
  prompt: string;
};

type AssistantRoleQuickTaskGroup = {
  key: string;
  label: string;
  roles: string[];
  tasks: AssistantRoleQuickTask[];
};

const assistantRoleQuickTaskGroups: AssistantRoleQuickTaskGroup[] = [
  {
    key: 'product',
    label: '产品快捷任务',
    roles: ['product_owner'],
    tasks: [
      {
        key: 'requirement_progress',
        label: '需求进展',
        prompt: '请按产品视角总结当前需求进展、阻塞和下一步推进建议。',
      },
      {
        key: 'feedback_insights',
        label: '反馈洞察',
        prompt: '请汇总最近用户反馈洞察，指出高频问题、影响范围和建议转需求项。',
      },
      {
        key: 'version_risk',
        label: '版本风险',
        prompt: '请从需求、缺陷、发布和用户反馈角度评估当前版本风险。',
      },
    ],
  },
  {
    key: 'engineering',
    label: '研发快捷任务',
    roles: ['rd_owner'],
    tasks: [
      {
        key: 'task_blockers',
        label: '任务阻塞',
        prompt: '请列出当前研发任务阻塞、待确认项和建议处理顺序。',
      },
      {
        key: 'code_inspection',
        label: '代码巡检',
        prompt: '请帮我生成或检查代码巡检任务草案，并说明数据连接、AI处理和结果动作依赖。',
      },
      {
        key: 'defect_fix',
        label: '缺陷修复',
        prompt: '请按严重度梳理待修复缺陷，给出修复优先级和关联需求/任务。',
      },
    ],
  },
  {
    key: 'testing',
    label: '测试快捷任务',
    roles: ['reviewer', 'test_owner', 'tester', 'release_owner'],
    tasks: [
      {
        key: 'test_defects',
        label: '测试缺陷',
        prompt: '请汇总当前测试缺陷、复现状态、阻塞发布的问题和建议责任归属。',
      },
      {
        key: 'automated_tests',
        label: '自动化测试',
        prompt: '请检查自动化测试相关任务、失败原因和可生成的测试草案。',
      },
      {
        key: 'release_risk',
        label: '发布风险',
        prompt: '请从测试结果、未关闭缺陷和发布记录评估当前发布风险。',
      },
    ],
  },
  {
    key: 'admin',
    label: '管理员快捷任务',
    roles: ['admin'],
    tasks: [
      {
        key: 'plugin_connections',
        label: '插件连接',
        prompt: '请检查插件连接配置状态，指出失败连接和可生成的连接草案。',
      },
      {
        key: 'ai_capabilities',
        label: 'AI能力',
        prompt: '请检查 AI 模型、AI角色和 Skill 配置是否完整，并指出缺口。',
      },
      {
        key: 'scheduled_jobs',
        label: '定时作业',
        prompt: '请汇总定时作业配置、运行健康和需要补齐的依赖。',
      },
      {
        key: 'run_failures',
        label: '运行失败',
        prompt: '请诊断最近失败的定时作业运行，按数据连接、AI处理、结果动作给出原因和修复建议。',
      },
    ],
  },
];

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
  'plugin_action',
  'requirement',
  'scheduled_job',
  'scheduled_job_run',
]);
const ASSISTANT_RECENT_REFERENCES_STORAGE_KEY = 'ai_brain_assistant_recent_references';
const MAX_RECENT_REFERENCES = 8;
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

type AssistantDraftWizardStep = {
  depends_on?: string[];
  key?: string;
  status?: string;
  summary?: string;
  title?: string;
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
          || item.action === 'create_analysis_draft'
        )
        && assistantDraftId(item),
    );
}

function assistantDraftActionLabel(action?: string) {
  if (!action) {
    return '未知草案';
  }
  return assistantDraftActionLabels[action] ?? action;
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

function metricCount(value?: number) {
  return Number.isFinite(value) ? new Intl.NumberFormat('zh-CN').format(Number(value)) : '-';
}

function metricPercent(value?: number) {
  if (!Number.isFinite(value)) {
    return '-';
  }
  const percentage = Number(value) * 100;
  const rounded = Math.round(percentage * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1)}%`;
}

function metricRatio(numerator?: number, denominator?: number) {
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || Number(denominator) <= 0) {
    return '-';
  }
  return metricPercent(Number(numerator) / Number(denominator));
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

function assistantDraftRunOnceRequested(draft: AssistantToolResultItem) {
  if (draft.run_once_requested === true) {
    return true;
  }
  const payload = itemRecord(draft, 'payload');
  const configJson = itemRecord(payload, 'config_json');
  const runOnceRequest = itemRecord(configJson, 'assistant_run_once_request');
  return runOnceRequest.requested === true || runOnceRequest.requested === 'true';
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

function diagnosticStatusColor(status: string) {
  if (status === 'succeeded') {
    return 'green';
  }
  if (status === 'failed') {
    return 'red';
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

function scheduledJobRunStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    cancelled: '已取消',
    failed: '失败',
    not_run: '未运行',
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

function scheduledJobRunIsActive(status?: string) {
  return status === 'queued' || status === 'running';
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
    || current.records_imported !== next.records_imported
    || current.status !== next.status
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
      progressText: scheduledJobRunExecutionProgressText(latestRun),
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

function draftPayloadText(payload: Record<string, unknown> | undefined, field: string) {
  const value = field.split('.').reduce<unknown>((current, key) => {
    if (!current || typeof current !== 'object' || Array.isArray(current)) {
      return undefined;
    }
    return (current as Record<string, unknown>)[key];
  }, payload);
  if (Array.isArray(value)) {
    return value.length ? value.join('、') : '-';
  }
  if (value && typeof value === 'object') {
    return JSON.stringify(value);
  }
  return value === undefined || value === null || value === '' ? '-' : String(value);
}

function draftPayloadLabel(
  payload: Record<string, unknown> | undefined,
  field: string,
  resultWriteTargetLabels: Map<string, string>,
) {
  const value = draftPayloadText(payload, field);
  if (field === 'result_mapping.write_target') {
    return resultWriteTargetLabels.get(value) ?? value;
  }
  return value;
}

function draftWizardSteps(draft: AssistantToolResultItem): AssistantDraftWizardStep[] {
  const value = draft.wizard_steps;
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter((item): item is Record<string, unknown> => (
      Boolean(item) && typeof item === 'object' && !Array.isArray(item)
    ))
    .map((item) => ({
      depends_on: Array.isArray(item.depends_on) ? item.depends_on.map(String) : [],
      key: item.key ? String(item.key) : undefined,
      status: item.status ? String(item.status) : undefined,
      summary: item.summary ? String(item.summary) : undefined,
      title: item.title ? String(item.title) : undefined,
    }));
}

function draftWizardStatusLabel(status?: string) {
  if (status === 'ready') {
    return { color: 'green', text: '已就绪' };
  }
  if (status === 'needs_prerequisite') {
    return { color: 'orange', text: '需先确认前置草案' };
  }
  if (status === 'pending') {
    return { color: 'blue', text: '待确认' };
  }
  if (status === 'skipped') {
    return { color: 'default', text: '已跳过' };
  }
  if (status === 'blocked') {
    return { color: 'red', text: '已阻塞' };
  }
  return { color: 'default', text: status || '未设置' };
}

function draftWizardPrerequisitePrompt(draftTitle: string | undefined, step: AssistantDraftWizardStep) {
  const stepTitle = step.title || step.key || '当前步骤';
  const dependencies = step.depends_on ?? [];
  const dependencyText = dependencies.length ? `。依赖：${dependencies.join('、')}` : '';
  return `为「${draftTitle || '配置草案'}」补齐「${stepTitle}」前置配置草案${dependencyText}`;
}

function draftWizardStepDraftPrompt(draftTitle: string | undefined, step: AssistantDraftWizardStep) {
  const stepTitle = step.title || step.key || '当前步骤';
  const dependencies = step.depends_on ?? [];
  const dependencyText = dependencies.length ? `。依赖：${dependencies.join('、')}` : '';
  const statusText = draftWizardStatusLabel(step.status).text;
  return `为「${draftTitle || '配置草案'}」生成或调整「${stepTitle}」步骤草案。当前状态：${statusText}${dependencyText}。请给出建议配置、字段校验和下一步确认动作`;
}

function canGenerateWizardPrerequisite(step: AssistantDraftWizardStep) {
  return step.status === 'needs_prerequisite' || step.status === 'blocked';
}

function draftWizardManualAdjustUrl(step: AssistantDraftWizardStep) {
  const key = String(step.key ?? '').toLowerCase();
  const title = String(step.title ?? '').toLowerCase();
  if (
    key.includes('data')
    || key.includes('source')
    || key.includes('connection')
    || key.includes('result')
    || key.includes('action')
    || title.includes('数据来源')
    || title.includes('结果动作')
  ) {
    return '/tasks/plugins';
  }
  if (
    key.includes('ai')
    || key.includes('agent')
    || key.includes('skill')
    || title.includes('ai')
    || title.includes('角色')
    || title.includes('skill')
  ) {
    return '/settings/ai-capabilities';
  }
  return '/tasks/scheduled-jobs';
}

function activeMentionQuery(value: string) {
  const markerIndex = value.lastIndexOf('@');
  if (markerIndex < 0) {
    return undefined;
  }
  const tail = value.slice(markerIndex + 1);
  if (tail.includes('\n')) {
    return undefined;
  }
  if (tail.length > 0 && /^\s/.test(tail)) {
    return undefined;
  }
  return tail.split(/\s+/)[0] ?? '';
}

function scheduledJobRunOnceRequested(value: string) {
  const normalized = value.toLowerCase();
  return scheduledJobRunOnceKeywords.some((keyword) => normalized.includes(keyword));
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

function selectedAssistantRoleQuickTaskGroups() {
  const roleSet = new Set(getStoredCurrentUser()?.roles ?? []);
  return assistantRoleQuickTaskGroups.filter((group) => (
    group.roles.some((role) => roleSet.has(role))
  ));
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

function queryReferenceResolutionLabel(status: QueryReferenceResolution['status']) {
  if (status === 'loading') {
    return { color: 'processing', text: '解析中' };
  }
  if (status === 'resolved') {
    return { color: 'green', text: '已带入' };
  }
  return { color: 'red', text: '未带入' };
}

function queryReferenceResolutionText(resolution: QueryReferenceResolution) {
  const label = referenceTypeLabel(resolution.referenceType);
  if (resolution.status === 'loading') {
    return `正在解析${label}引用：${resolution.referenceId}`;
  }
  if (resolution.status === 'resolved') {
    return `已从链接带入${label}：${resolution.title || resolution.referenceId}`;
  }
  return `引用解析失败：${label} ${resolution.referenceId} ${resolution.message || '不存在或无权限'}`;
}

function draftStatusLabel(status?: string) {
  if (status === 'confirmed' || status === 'applied') {
    return { color: 'green', text: '已应用' };
  }
  if (status === 'cancelled') {
    return { color: 'default', text: '已取消' };
  }
  if (status === 'expired') {
    return { color: 'orange', text: '已过期' };
  }
  if (status === 'failed') {
    return { color: 'red', text: '失败' };
  }
  return { color: 'blue', text: '待确认' };
}

function draftPreviewStatusLabel(status?: string) {
  if (status === 'blocked') {
    return { color: 'red', text: '阻塞' };
  }
  if (status === 'warning') {
    return { color: 'orange', text: '需确认' };
  }
  return { color: 'green', text: '通过' };
}

function draftPreviewValueText(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  if (Array.isArray(value)) {
    return value.length ? value.map(String).join('、') : '-';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

function draftResourceLink(resolution?: AssistantDraftResolutionRecord) {
  if (!resolution) {
    return undefined;
  }
  if (resolution.resource_type === 'scheduled_job') {
    return {
      label: '打开定时作业',
      url: `/tasks/scheduled-jobs?job_id=${resolution.resource_id}`,
    };
  }
  if (resolution.resource_type === 'ai_skill') {
    return {
      label: '打开 Skill',
      url: `/tasks/ai-capabilities?skill_id=${resolution.resource_id}`,
    };
  }
  if (resolution.resource_type === 'ai_agent') {
    return {
      label: '打开 AI角色',
      url: `/tasks/ai-capabilities?agent_id=${resolution.resource_id}`,
    };
  }
  if (resolution.resource_type === 'plugin_action') {
    return {
      label: '打开插件动作',
      url: `/tasks/plugins?action_id=${resolution.resource_id}`,
    };
  }
  if (resolution.resource_type === 'assistant_analysis') {
    return {
      label: '打开分析结果',
      url: `/assistant?draft_id=${resolution.resource_id}`,
    };
  }
  return {
    label: '打开插件连接',
    url: `/tasks/plugins?connection_id=${resolution.resource_id}`,
  };
}

function draftRunResourceLink(resolution?: AssistantDraftResolutionRecord) {
  if (
    !resolution
    || resolution.resource_type !== 'scheduled_job'
    || !resolution.scheduled_job_run_id
  ) {
    return undefined;
  }
  return {
    label: '打开本次运行',
    url: `/tasks/scheduled-jobs?job_id=${resolution.resource_id}&run_id=${resolution.scheduled_job_run_id}`,
  };
}

function scheduledJobRunIdFromActionResult(result?: Record<string, unknown>) {
  const scheduledJobRun = result?.scheduled_job_run;
  if (!scheduledJobRun || typeof scheduledJobRun !== 'object' || Array.isArray(scheduledJobRun)) {
    return undefined;
  }
  const runId = String((scheduledJobRun as Record<string, unknown>).id ?? '').trim();
  return runId || undefined;
}

function assistantDraftId(draft?: Pick<AssistantToolResultItem, 'client_draft_id' | 'draft_id' | 'server_draft_id'>) {
  if (!draft) {
    return undefined;
  }
  return [draft.draft_id, draft.server_draft_id, draft.client_draft_id]
    .map((value) => String(value ?? '').trim())
    .find(Boolean);
}

function draftRegeneratePrompt(draft: AssistantToolResultItem) {
  return `重新生成「${draft.title ?? '配置草案'}」草案`;
}

function referenceTypeLabel(type: string) {
  const labels: Record<string, string> = {
    ai_agent: 'AI角色',
    ai_skill: 'AI能力',
    ai_task: '任务',
    bug: '缺陷',
    code_review_report: '代码评审',
    human_review: '确认',
    iteration_version: '迭代',
    knowledge_deposit: '知识沉淀',
    knowledge_chunk: '知识片段',
    knowledge_document: '知识文档',
    plugin_action: '插件动作',
    product: '产品',
    requirement: '需求',
    scheduled_job: '定时作业',
    scheduled_job_run: '运行记录',
  };
  return labels[type] ?? type;
}

function referenceSourceModule(type: string) {
  const modules: Record<string, string> = {
    ai_agent: 'AI能力配置',
    ai_skill: 'AI能力配置',
    ai_task: '需求交付',
    bug: '需求交付',
    code_review_report: '需求交付',
    human_review: '需求交付',
    iteration_version: '需求交付',
    knowledge_deposit: '知识库',
    knowledge_chunk: '知识库',
    knowledge_document: '知识库',
    plugin_action: '插件管理',
    product: '产品资产',
    requirement: '需求交付',
    scheduled_job: '任务中心',
    scheduled_job_run: '任务中心',
  };
  return modules[type] ?? 'AI Brain';
}

function referenceUpdatedDate(reference: AssistantReference) {
  const value = reference.updated_at ?? reference.created_at;
  if (!value) {
    return undefined;
  }
  const normalized = String(value);
  return /^\d{4}-\d{2}-\d{2}/.test(normalized) ? normalized.slice(0, 10) : normalized;
}

function referenceMetaText(reference: AssistantReference) {
  return [
    reference.source_module ?? referenceSourceModule(reference.type),
    reference.permission_label ?? '可引用',
    referenceUpdatedDate(reference),
  ].filter(Boolean).join(' · ');
}

function referenceKnowledgeChunkCount(reference: AssistantReference) {
  if (reference.type === 'knowledge_chunk') {
    return 1;
  }
  if (reference.type !== 'knowledge_document') {
    return 0;
  }
  return Number(reference.chunk_count ?? 0);
}

function referenceInjectionText(reference: AssistantReference) {
  if (reference.type === 'knowledge_chunk') {
    return '1 个知识 chunk 将注入模型';
  }
  if (reference.type === 'knowledge_document') {
    const chunkCount = referenceKnowledgeChunkCount(reference);
    if (chunkCount > ASSISTANT_KNOWLEDGE_CONTEXT_CHUNK_LIMIT) {
      return `最多 ${ASSISTANT_KNOWLEDGE_CONTEXT_CHUNK_LIMIT} 个知识 chunk 将按权限注入模型`;
    }
    return chunkCount > 0
      ? `${chunkCount} 个知识 chunk 将注入模型`
      : '知识文档元数据将注入模型';
  }
  return '引用元数据将注入模型';
}

function selectedReferenceInjectionSummary(references: AssistantReference[]) {
  const knowledgeChunkCount = references.reduce(
    (total, reference) => total + referenceKnowledgeChunkCount(reference),
    0,
  );
  if (!knowledgeChunkCount) {
    return '元数据将注入模型';
  }
  if (knowledgeChunkCount > ASSISTANT_KNOWLEDGE_CONTEXT_CHUNK_LIMIT) {
    return `最多 ${ASSISTANT_KNOWLEDGE_CONTEXT_CHUNK_LIMIT} 个知识 chunk 将按权限注入模型`;
  }
  return `${knowledgeChunkCount} 个知识 chunk 将注入模型`;
}

function referenceSummaryText(reference: AssistantReference) {
  const summary = String(reference.summary ?? '').trim();
  return summary || '暂无摘要，仅注入引用元数据。';
}

function AssistantReferenceDetailModal({
  reference,
  onClose,
}: {
  reference?: AssistantReference;
  onClose: () => void;
}) {
  return (
    <Modal
      footer={null}
      open={Boolean(reference)}
      title={`引用摘要 - ${reference?.title ?? '引用'}`}
      width={640}
      onCancel={onClose}
    >
      {reference ? (
        <div className="assistant-reference-detail">
          <div className="assistant-reference-detail-grid">
            <span>
              <Text type="secondary">引用类型</Text>
              <Text>{referenceTypeLabel(reference.type)}</Text>
            </span>
            <span>
              <Text type="secondary">来源模块</Text>
              <Text>{reference.source_module ?? referenceSourceModule(reference.type)}</Text>
            </span>
            <span>
              <Text type="secondary">权限状态</Text>
              <Text>{reference.permission_label ?? '可引用'}</Text>
            </span>
            <span>
              <Text type="secondary">更新时间</Text>
              <Text>{referenceUpdatedDate(reference) ?? '-'}</Text>
            </span>
            <span>
              <Text type="secondary">注入口径</Text>
              <Text>{referenceInjectionText(reference)}</Text>
            </span>
          </div>
          <div className="assistant-reference-detail-section">
            <Text strong>摘要</Text>
            <Text>{referenceSummaryText(reference)}</Text>
          </div>
          <Button href={reference.url} size="small" type="link">
            查看来源
          </Button>
        </div>
      ) : null}
    </Modal>
  );
}

function normalizeRecentReferences(value: unknown): AssistantReference[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const references: AssistantReference[] = [];
  const seen = new Set<string>();
  value.forEach((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) {
      return;
    }
    const record = item as Partial<AssistantReference>;
    const id = String(record.id ?? '').trim();
    const title = String(record.title ?? '').trim();
    const type = String(record.type ?? '').trim();
    const url = String(record.url ?? '').trim();
    if (!id || !title || !type || !url) {
      return;
    }
    const reference: AssistantReference = {
      ...record,
      id,
      title,
      type,
      url,
    };
    const key = referenceKey(reference);
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    references.push(reference);
  });
  return references.slice(0, MAX_RECENT_REFERENCES);
}

function readRecentReferences() {
  if (typeof window === 'undefined') {
    return [];
  }
  try {
    return normalizeRecentReferences(
      JSON.parse(window.localStorage.getItem(ASSISTANT_RECENT_REFERENCES_STORAGE_KEY) ?? '[]'),
    );
  } catch {
    return [];
  }
}

function writeRecentReferences(references: AssistantReference[]) {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(
      ASSISTANT_RECENT_REFERENCES_STORAGE_KEY,
      JSON.stringify(references.slice(0, MAX_RECENT_REFERENCES)),
    );
  } catch {
    // Recent references are an input convenience; failing to persist them should not block chat.
  }
}

function nextRecentReferences(
  currentReferences: AssistantReference[],
  referencesToRemember: AssistantReference[],
) {
  const nextReferences = [...currentReferences];
  referencesToRemember.forEach((reference) => {
    const key = referenceKey(reference);
    const existingIndex = nextReferences.findIndex((item) => referenceKey(item) === key);
    if (existingIndex >= 0) {
      nextReferences.splice(existingIndex, 1);
    }
    nextReferences.unshift(reference);
  });
  return normalizeRecentReferences(nextReferences);
}

function orderReferenceCandidatesByRecent(
  references: AssistantReference[],
  recentReferences: AssistantReference[],
) {
  const recentOrderByKey = new Map(
    recentReferences.map((reference, index) => [referenceKey(reference), index]),
  );
  return references
    .map((reference, index) => ({
      index,
      recentIndex: recentOrderByKey.get(referenceKey(reference)),
      reference,
    }))
    .sort((left, right) => {
      const leftRecent = left.recentIndex ?? Number.MAX_SAFE_INTEGER;
      const rightRecent = right.recentIndex ?? Number.MAX_SAFE_INTEGER;
      if (leftRecent !== rightRecent) {
        return leftRecent - rightRecent;
      }
      return left.index - right.index;
    })
    .map((item) => item.reference);
}

function groupedReferenceCandidates(
  references: AssistantReference[],
  recentReferences: AssistantReference[],
) {
  const groups: Array<{
    items: Array<{
      index: number;
      reference: AssistantReference;
    }>;
    label: string;
    type: string;
  }> = [];
  const recentReferenceKeys = new Set(recentReferences.map(referenceKey));
  const recentItems = references
    .map((reference, index) => ({ index, reference }))
    .filter(({ reference }) => recentReferenceKeys.has(referenceKey(reference)));
  if (recentItems.length) {
    groups.push({
      items: recentItems,
      label: '最近使用',
      type: '__recent__',
    });
  }
  const groupByType = new Map<string, typeof groups[number]>();
  references.forEach((reference, index) => {
    if (recentReferenceKeys.has(referenceKey(reference))) {
      return;
    }
    let group = groupByType.get(reference.type);
    if (!group) {
      group = {
        items: [],
        label: referenceTypeLabel(reference.type),
        type: reference.type,
      };
      groupByType.set(reference.type, group);
      groups.push(group);
    }
    group.items.push({ index, reference });
  });
  return groups;
}

function storeScheduledJobDraft(draft: AssistantToolResultItem) {
  if (!draft.payload || typeof window === 'undefined') {
    return;
  }
  window.sessionStorage.setItem(
    ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
    JSON.stringify({
      draftId: assistantDraftId(draft),
      payload: draft.payload,
      title: draft.title,
    }),
  );
}

function storePluginActionDraft(draft: AssistantToolResultItem) {
  if (!draft.payload || typeof window === 'undefined') {
    return;
  }
  window.sessionStorage.setItem(
    ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
    JSON.stringify({
      draftId: assistantDraftId(draft),
      payload: draft.payload,
      title: draft.title,
    }),
  );
}

function storePluginConnectionDraft(draft: AssistantToolResultItem) {
  if (!draft.payload || typeof window === 'undefined') {
    return;
  }
  window.sessionStorage.setItem(
    ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
    JSON.stringify({
      draftId: assistantDraftId(draft),
      payload: draft.payload,
      title: draft.title,
    }),
  );
}

function AssistantDraftPreviewBlock({ preview }: { preview?: AssistantActionDraftPreview }) {
  if (!preview) {
    return null;
  }
  const diffs = (preview.diffs ?? []).slice(0, 4);
  const issues = preview.validation?.issues ?? [];
  const statusLabel = draftPreviewStatusLabel(preview.validation?.status);
  return (
    <div className="assistant-action-draft-precheck">
      <Space size={8} wrap>
        <Text strong>应用前预检</Text>
        <Tag color={statusLabel.color}>{statusLabel.text}</Tag>
      </Space>
      {diffs.length ? (
        <div className="assistant-action-draft-precheck-diffs">
          {diffs.map((diff) => (
            <span key={diff.field}>
              <Text type="secondary">{diff.label ?? diff.field}</Text>
              <Text>
                {draftPreviewValueText(diff.current)} -&gt; {draftPreviewValueText(diff.proposed)}
              </Text>
            </span>
          ))}
        </div>
      ) : null}
      {issues.length ? (
        <div className="assistant-action-draft-precheck-issues">
          {issues.map((issue) => (
            <Text key={`${issue.field}:${issue.message}`} type={issue.severity === 'error' ? 'danger' : 'warning'}>
              {issue.message}
            </Text>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function AssistantDraftWizardBlock({
  draftTitle,
  onUsePrerequisitePrompt,
  steps,
}: {
  draftTitle?: string;
  onUsePrerequisitePrompt?: (prompt: string) => void;
  steps: AssistantDraftWizardStep[];
}) {
  if (!steps.length) {
    return null;
  }
  return (
    <div className="assistant-draft-wizard">
      <div className="assistant-draft-wizard-header">
        <Space size={8} wrap>
          <ProjectOutlined />
          <Text strong>配置向导</Text>
        </Space>
      </div>
      <div className="assistant-draft-wizard-steps">
        {steps.map((step, index) => {
          const label = draftWizardStatusLabel(step.status);
          const title = step.title || step.key || `步骤 ${index + 1}`;
          const dependsOn = step.depends_on ?? [];
          const canGeneratePrerequisite = Boolean(onUsePrerequisitePrompt)
            && canGenerateWizardPrerequisite(step);
          const canGenerateStepDraft = Boolean(onUsePrerequisitePrompt);
          const manualAdjustUrl = draftWizardManualAdjustUrl(step);
          return (
            <div className="assistant-draft-wizard-step" key={step.key || title}>
              <Space size={6} wrap>
                <Text strong>{`${title}：${label.text}`}</Text>
                <Tag color={label.color}>{label.text}</Tag>
              </Space>
              {step.summary ? <Text type="secondary">{step.summary}</Text> : null}
              {dependsOn.length ? (
                <Text type="secondary">依赖：{dependsOn.join('、')}</Text>
              ) : null}
              {canGenerateStepDraft || canGeneratePrerequisite || manualAdjustUrl ? (
                <Space size={6} wrap>
                  {canGenerateStepDraft ? (
                    <Button
                      size="small"
                      onClick={() => onUsePrerequisitePrompt?.(
                        draftWizardStepDraftPrompt(draftTitle, step),
                      )}
                    >
                      AI生成{title}草案
                    </Button>
                  ) : null}
                  {canGeneratePrerequisite ? (
                    <Button
                      size="small"
                      onClick={() => onUsePrerequisitePrompt?.(
                        draftWizardPrerequisitePrompt(draftTitle, step),
                      )}
                    >
                      生成{title}前置草案
                    </Button>
                  ) : null}
                  <Button href={manualAdjustUrl} size="small">
                    手动调整{title}
                  </Button>
                </Space>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AssistantDraftDetailModal({
  draft,
  onClose,
  status,
}: {
  draft?: AssistantToolResultItem;
  onClose: () => void;
  status?: string;
}) {
  const statusLabel = draftStatusLabel(status ?? draft?.status);
  const diffs = draft?.preview?.diffs ?? [];
  const issues = draft?.preview?.validation?.issues ?? [];
  return (
    <Modal
      footer={null}
      open={Boolean(draft)}
      title={`草案详情 - ${draft?.title ?? '配置草案'}`}
      width={760}
      onCancel={onClose}
    >
      {draft ? (
        <div className="assistant-draft-detail">
          <Space size={8} wrap>
            <Text strong>草案状态</Text>
            <Tag color={statusLabel.color}>{statusLabel.text}</Tag>
            <Tag color="default">{draft.action ?? 'unknown_action'}</Tag>
            {draft.risk_level ? <Tag color="orange">风险：{draft.risk_level}</Tag> : null}
          </Space>
          <div className="assistant-draft-detail-section">
            <Text strong>Payload</Text>
            <pre>{JSON.stringify(draft.payload ?? {}, null, 2)}</pre>
          </div>
          {diffs.length ? (
            <div className="assistant-draft-detail-section">
              <Text strong>字段差异</Text>
              <div className="assistant-action-draft-precheck-diffs">
                {diffs.map((diff) => (
                  <span key={diff.field}>
                    <Text type="secondary">{diff.label ?? diff.field}</Text>
                    <Text>
                      {draftPreviewValueText(diff.current)} -&gt; {draftPreviewValueText(diff.proposed)}
                    </Text>
                  </span>
                ))}
              </div>
            </div>
          ) : null}
          {issues.length ? (
            <div className="assistant-draft-detail-section">
              <Text strong>校验问题</Text>
              <div className="assistant-action-draft-precheck-issues">
                {issues.map((issue) => (
                  <Text
                    key={`${issue.field}:${issue.message}`}
                    type={issue.severity === 'error' ? 'danger' : 'warning'}
                  >
                    {issue.message}
                  </Text>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </Modal>
  );
}

function AssistantActionDraftCards({
  drafts,
  draftMutationId,
  draftResolutionById,
  draftStatusById,
  onCancelDraft,
  onConfirmDraft,
  onRegenerateDraft,
  onUseDraftWizardStepPrompt,
  resultWriteTargetLabels,
}: {
  draftMutationId?: string;
  draftResolutionById: AssistantDraftResolutionMap;
  drafts: AssistantToolResultItem[];
  draftStatusById: Record<string, string>;
  onCancelDraft: (draft: AssistantToolResultItem) => void;
  onConfirmDraft: (draft: AssistantToolResultItem) => void;
  onRegenerateDraft: (draft: AssistantToolResultItem) => void;
  onUseDraftWizardStepPrompt: (prompt: string) => void;
  resultWriteTargetLabels: Map<string, string>;
}) {
  const [detailDraft, setDetailDraft] = useState<AssistantToolResultItem>();
  const currentDraftStatus = (draft: AssistantToolResultItem) => {
    const draftId = assistantDraftId(draft);
    const resolution = draftId ? draftResolutionById[draftId] : undefined;
    return resolution
      ? 'applied'
      : (draftId ? draftStatusById[draftId] : undefined) ?? draft.status ?? 'pending';
  };
  if (!drafts.length) {
    return null;
  }
  return (
    <div className="assistant-action-draft-list">
      {drafts.map((draft) => {
        const payload = draft.payload;
        const isAiAgentDraft = draft.action === 'create_ai_agent';
        const isAiSkillDraft = draft.action === 'create_ai_skill';
        const isAiCapabilityDraft = isAiAgentDraft || isAiSkillDraft;
        const isAnalysisDraft = draft.action === 'create_analysis_draft';
        const isPluginActionDraft = draft.action === 'create_plugin_action';
        const isPluginConnectionDraft = draft.action === 'create_plugin_connection';
        const draftId = assistantDraftId(draft);
        const resolution = draftId ? draftResolutionById[draftId] : undefined;
        const resourceLink = draftResourceLink(resolution);
        const runResourceLink = draftRunResourceLink(resolution);
        const isRunOnceDraft = assistantDraftRunOnceRequested(draft);
        const currentStatus = currentDraftStatus(draft);
        const statusLabel = draftStatusLabel(currentStatus);
        const isPending = currentStatus === 'pending';
        const canApplyDraftToForm = isPending;
        const previewStatus = draft.preview?.validation?.status;
        const isPreviewBlocked = previewStatus === 'blocked';
        const wizardSteps = draftWizardSteps(draft);
        const writeNotice = isPluginConnectionDraft
          ? '确认前不会写入插件连接'
          : isPluginActionDraft
            ? '确认前不会写入插件动作'
            : isAiCapabilityDraft
              ? '确认前不会写入 AI 能力配置'
              : isAnalysisDraft
                ? '确认前不会写入分析结果'
                : '确认前不会写入作业定义';
        return (
          <div className="assistant-action-draft-card" key={draftId}>
            <div className="assistant-action-draft-header">
              <Space size={8} wrap>
                <FileTextOutlined />
                <Text strong>{draft.title ?? '配置草案'}</Text>
                {draft.risk_level ? <Tag color="orange">风险：{draft.risk_level}</Tag> : null}
                {draft.requires_confirmation ? <Tag color={statusLabel.color}>{statusLabel.text}</Tag> : null}
                {isRunOnceDraft ? <Tag color="geekblue">确认后执行一次</Tag> : null}
              </Space>
              <Text type="secondary">
                {isRunOnceDraft ? `${writeNotice}；确认后会立即执行一次` : writeNotice}
              </Text>
            </div>
            <div className="assistant-action-draft-grid">
              {isPluginConnectionDraft ? (
                <>
                  <span>
                    <Text type="secondary">插件</Text>
                    <Text>{draftPayloadText(payload, 'plugin_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">Endpoint</Text>
                    <Text>{draftPayloadText(payload, 'endpoint_url')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">环境</Text>
                    <Text>{draftPayloadText(payload, 'environment')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">认证</Text>
                    <Text>{draftPayloadText(payload, 'auth_type')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">Params</Text>
                    <Text>{draftPayloadText(payload, 'request_config.query')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">Headers</Text>
                    <Text>{draftPayloadText(payload, 'request_config.headers')}</Text>
                  </span>
                </>
              ) : isPluginActionDraft ? (
                <>
                  <span>
                    <Text type="secondary">动作类型</Text>
                    <Text>{draftPayloadText(payload, 'action_type')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">编码</Text>
                    <Text>{draftPayloadText(payload, 'code')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">插件</Text>
                    <Text>{draftPayloadText(payload, 'plugin_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">连接</Text>
                    <Text>{draftPayloadText(payload, 'connection_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">请求方法</Text>
                    <Text>{draftPayloadText(payload, 'request_config.method')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">请求路径</Text>
                    <Text>{draftPayloadText(payload, 'request_config.path')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">写入目标</Text>
                    <Text>{draftPayloadLabel(payload, 'result_mapping.write_target', resultWriteTargetLabels)}</Text>
                  </span>
                </>
              ) : isAiSkillDraft ? (
                <>
                  <span>
                    <Text type="secondary">名称</Text>
                    <Text>{draftPayloadText(payload, 'name')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">编码</Text>
                    <Text>{draftPayloadText(payload, 'code')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">Prompt 模板</Text>
                    <Text>{draftPayloadText(payload, 'prompt_template')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">上下文</Text>
                    <Text>{draftPayloadText(payload, 'required_context')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">风险等级</Text>
                    <Text>{draftPayloadText(payload, 'risk_level')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">状态</Text>
                    <Text>{draftPayloadText(payload, 'status')}</Text>
                  </span>
                </>
              ) : isAiAgentDraft ? (
                <>
                  <span>
                    <Text type="secondary">名称</Text>
                    <Text>{draftPayloadText(payload, 'name')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">编码</Text>
                    <Text>{draftPayloadText(payload, 'code')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">业务大脑</Text>
                    <Text>{draftPayloadText(payload, 'brain_app_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">AI 模型</Text>
                    <Text>{draftPayloadText(payload, 'model_gateway_config_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">默认 Skills</Text>
                    <Text>{draftPayloadText(payload, 'default_skill_ids')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">系统 Prompt</Text>
                    <Text>{draftPayloadText(payload, 'system_prompt')}</Text>
                  </span>
                  {draftPayloadText(payload, 'assistant_prerequisite_draft_ids') !== '-' ? (
                    <span>
                      <Text type="secondary">前置草案</Text>
                      <Text>{draftPayloadText(payload, 'assistant_prerequisite_draft_ids')}</Text>
                    </span>
                  ) : null}
                </>
              ) : isAnalysisDraft ? (
                <>
                  <span>
                    <Text type="secondary">分析类型</Text>
                    <Text>{draftPayloadText(payload, 'analysis_type')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">来源模块</Text>
                    <Text>{draftPayloadText(payload, 'source_module')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">摘要指标</Text>
                    <Text>{draftPayloadText(payload, 'summary')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">风险/治理项</Text>
                    <Text>{draftPayloadText(payload, 'findings')}</Text>
                  </span>
                </>
              ) : (
                <>
                  <span>
                    <Text type="secondary">作业类型</Text>
                    <Text>{draftPayloadText(payload, 'job_type')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">调度</Text>
                    <Text>{draftPayloadText(payload, 'cron_expression')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">执行模式</Text>
                    <Text>{draftPayloadText(payload, 'execution_mode')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">AI 模型</Text>
                    <Text>{draftPayloadText(payload, 'model_gateway_config_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">AI角色</Text>
                    <Text>{draftPayloadText(payload, 'agent_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">Skills</Text>
                    <Text>{draftPayloadText(payload, 'skill_ids')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">数据连接</Text>
                    <Text>{draftPayloadText(payload, 'plugin_connection_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">结果动作</Text>
                    <Text>{draftPayloadText(payload, 'plugin_action_id')}</Text>
                  </span>
                  {draftPayloadText(payload, 'assistant_prerequisite_draft_ids') !== '-' ? (
                    <span>
                      <Text type="secondary">前置草案</Text>
                      <Text>{draftPayloadText(payload, 'assistant_prerequisite_draft_ids')}</Text>
                    </span>
                  ) : null}
                </>
              )}
            </div>
            <AssistantDraftWizardBlock
              draftTitle={draft.title}
              steps={wizardSteps}
              onUsePrerequisitePrompt={onUseDraftWizardStepPrompt}
            />
            <AssistantDraftPreviewBlock preview={draft.preview} />
            <Space size={8} wrap>
              {draftId && isPending ? (
                <>
                  <Button
                    disabled={isPreviewBlocked}
                    icon={<CheckCircleOutlined />}
                    loading={draftMutationId === draftId}
                    size="small"
                    type="primary"
                    onClick={() => onConfirmDraft(draft)}
                  >
                    {isRunOnceDraft ? '确认并执行一次' : '确认创建'}
                  </Button>
                  <Button
                    icon={<CloseCircleOutlined />}
                    loading={draftMutationId === draftId}
                    size="small"
                    onClick={() => onCancelDraft(draft)}
                  >
                    取消
                  </Button>
                </>
              ) : null}
              {resourceLink ? (
                <Button
                  aria-label={resourceLink.label}
                  href={resourceLink.url}
                  icon={<LinkOutlined />}
                  size="small"
                >
                  {resourceLink.label}
                </Button>
              ) : null}
              {runResourceLink ? (
                <Button
                  aria-label={runResourceLink.label}
                  href={runResourceLink.url}
                  icon={<LinkOutlined />}
                  size="small"
                >
                  {runResourceLink.label}
                </Button>
              ) : null}
              {canApplyDraftToForm && !resourceLink && isPluginConnectionDraft ? (
                <Button
                  href="/tasks/plugins"
                  size="small"
                  type="primary"
                  onMouseDown={() => storePluginConnectionDraft(draft)}
                  onClick={() => storePluginConnectionDraft(draft)}
                >
                  应用到插件连接表单
                </Button>
              ) : null}
              {canApplyDraftToForm && !resourceLink && isPluginActionDraft ? (
                <Button
                  href="/tasks/plugins"
                  size="small"
                  type="primary"
                  onMouseDown={() => storePluginActionDraft(draft)}
                  onClick={() => storePluginActionDraft(draft)}
                >
                  应用到插件动作表单
                </Button>
              ) : null}
              {canApplyDraftToForm
              && !resourceLink
              && !isAiCapabilityDraft
              && !isPluginConnectionDraft
              && !isPluginActionDraft
              && !isAnalysisDraft ? (
                <Button
                  href="/tasks/scheduled-jobs"
                  size="small"
                  type="primary"
                  onMouseDown={() => storeScheduledJobDraft(draft)}
                  onClick={() => storeScheduledJobDraft(draft)}
                >
                  应用到定时作业表单
                </Button>
              ) : null}
              <Button size="small" onClick={() => setDetailDraft(draft)}>
                查看详情
              </Button>
              {draftId ? (
                <Button href={`/assistant?draft_id=${draftId}`} size="small">
                  查看草案
                </Button>
              ) : null}
              <Button
                aria-label="重新生成"
                icon={<ReloadOutlined />}
                size="small"
                onClick={() => onRegenerateDraft(draft)}
              >
                重新生成
              </Button>
            </Space>
          </div>
        );
      })}
      <AssistantDraftDetailModal
        draft={detailDraft}
        status={detailDraft ? currentDraftStatus(detailDraft) : undefined}
        onClose={() => setDetailDraft(undefined)}
      />
    </div>
  );
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
                <Tag color={item.draft_action === 'create_scheduled_job' ? 'green' : 'default'}>
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
                onClick={() => onUseRunFollowupPrompt(item, '为什么这次任务失败？')}
              >
                问这次运行
              </Button>
              <Button
                aria-label="生成运行修复草案"
                icon={<FileTextOutlined />}
                size="small"
                onClick={() => onUseRunFollowupPrompt(item, '这次失败怎么修？帮我生成修复草案')}
              >
                生成修复草案
              </Button>
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
                return (
                  <div className="assistant-diagnostic-stage" key={itemText(stage, 'stage')}>
                    <Space size={6} wrap>
                      <Tag color="blue">{diagnosticStageLabel(itemText(stage, 'stage'))}</Tag>
                      <Tag color={diagnosticStatusColor(itemText(stage, 'status'))}>
                        {itemText(stage, 'status')}
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

function AssistantDraftTemplateMarket({
  isLoading,
  onUseTemplate,
  templates,
}: {
  isLoading: boolean;
  onUseTemplate: (template: AssistantDraftTemplate) => void;
  templates: AssistantDraftTemplate[];
}) {
  return (
    <div className="assistant-template-market-panel">
      <div className="assistant-template-market-header">
        <Text strong>模板市场</Text>
        {isLoading ? <Spin size="small" /> : <Tag color="blue">{templates.length}</Tag>}
      </div>
      <div className="assistant-template-market-list">
        {templates.map((template) => (
          <div className="assistant-template-card" key={template.code}>
            <div className="assistant-template-card-title">
              <Text strong>{template.name}</Text>
              <Tag color={template.available === false ? 'default' : 'green'}>
                {template.available === false ? '暂未完整接入' : '可生成草案'}
              </Tag>
            </div>
            <Text className="assistant-template-description" type="secondary">
              {template.description}
            </Text>
            <Space size={[4, 4]} wrap>
              {template.source_module ? <Tag color="blue">{template.source_module}</Tag> : null}
              {template.draft_action ? <Tag color="default">{template.draft_action}</Tag> : null}
              {template.template_version ? <Tag color="default">{template.template_version}</Tag> : null}
            </Space>
            {template.dependencies?.length ? (
              <Text className="assistant-template-meta" type="secondary">
                依赖：{template.dependencies.join('、')}
              </Text>
            ) : null}
            {template.wizard_steps?.length ? (
              <Text className="assistant-template-meta" type="secondary">
                流程：{template.wizard_steps.join(' -> ')}
              </Text>
            ) : null}
            <Button
              aria-label={`使用模板 ${template.name}`}
              disabled={template.available === false}
              size="small"
              onClick={() => onUseTemplate(template)}
            >
              使用模板
            </Button>
          </div>
        ))}
        {!isLoading && !templates.length ? (
          <Text type="secondary">暂无可用模板</Text>
        ) : null}
      </div>
    </div>
  );
}

function AssistantMetricsPanel({
  isLoading,
  metrics,
  onRefresh,
}: {
  isLoading: boolean;
  metrics?: AssistantMetrics;
  onRefresh: () => void;
}) {
  const summary = metrics?.summary ?? {};
  const metricItems = [
    { label: '草案生成数', value: metricCount(summary.draft_total) },
    { label: '草案确认率', value: metricPercent(summary.draft_adoption_rate) },
    { label: '用户修改率', value: metricPercent(summary.draft_user_modified_rate) },
    { label: '@ 引用使用率', value: metricPercent(summary.reference_usage_rate) },
    { label: '作业运行成功率', value: metricPercent(summary.scheduled_job_run_success_rate) },
    { label: '失败修复率', value: metricPercent(summary.failed_run_repair_rate) },
    { label: '知识命中率', value: metricPercent(summary.knowledge_reference_hit_rate) },
  ];
  const draftStatusItems = [
    { label: '待确认', value: metricCount(summary.draft_pending_count) },
    { label: '已应用', value: metricCount(summary.draft_confirmed_count) },
    { label: '已取消', value: metricCount(summary.draft_cancelled_count) },
    { label: '已过期', value: metricCount(summary.draft_expired_count) },
    { label: '失败', value: metricCount(summary.draft_failed_count) },
  ];
  const draftActionItems = metrics?.drafts_by_action ?? [];
  const runTrackingItems = [
    {
      label: '作业运行',
      value: `成功 ${metricCount(summary.scheduled_job_run_succeeded_count)} · 失败 ${metricCount(
        summary.scheduled_job_run_failed_count,
      )} · 总数 ${metricCount(summary.scheduled_job_run_total)}`,
    },
    {
      label: '失败修复',
      value: `已修复 ${metricCount(summary.failed_run_repaired_count)} · 失败运行 ${metricCount(
        summary.failed_run_total,
      )}`,
    },
  ];
  const referenceTrackingItems = [
    {
      label: '用户消息',
      value: `已引用 ${metricCount(summary.referenced_user_message_count)} · 用户消息 ${metricCount(
        summary.user_message_total,
      )}`,
    },
    {
      label: '知识命中',
      value: `命中 ${metricCount(summary.knowledge_reference_hit_count)} · 请求 ${metricCount(
        summary.knowledge_reference_request_count,
      )} · 知识引用 ${metricCount(summary.knowledge_reference_count)}`,
    },
  ];

  return (
    <div className="assistant-metrics-panel">
      <div className="assistant-metrics-header">
        <Space size={6}>
          <BarChartOutlined />
          <Text strong>助手效果指标</Text>
        </Space>
        <Button loading={isLoading} size="small" onClick={onRefresh}>
          {metrics ? '刷新指标' : '查看指标'}
        </Button>
      </div>
      {metrics ? (
        <>
          <div className="assistant-metrics-grid">
            {metricItems.map((item) => (
              <div
                aria-label={`指标 ${item.label}`}
                className="assistant-metric-item"
                key={item.label}
              >
                <Text type="secondary">{item.label}</Text>
                <Text strong>{item.value}</Text>
              </div>
            ))}
          </div>
          <div className="assistant-metrics-breakdown">
            <Text strong>草案状态</Text>
            <Space size={[4, 4]} wrap>
              {draftStatusItems.map((item) => (
                <Tag aria-label={`草案状态 ${item.label}`} key={item.label}>
                  {item.label} {item.value}
                </Tag>
              ))}
            </Space>
          </div>
          {draftActionItems.length ? (
            <div className="assistant-metrics-breakdown">
              <Text strong>草案类型</Text>
              <div className="assistant-metrics-action-list">
                {draftActionItems.map((item) => (
                  <Text
                    aria-label={`草案类型 ${item.action}`}
                    key={item.action}
                    type="secondary"
                  >
                    {assistantDraftActionLabel(item.action)}：总数 {metricCount(item.total)}
                    {' · '}待确认 {metricCount(item.pending_count)}
                    {' · '}已应用 {metricCount(item.confirmed_count)}
                    {' · '}已取消 {metricCount(item.cancelled_count)}
                    {' · '}处理率 {metricRatio(
                      Number(item.total ?? 0) - Number(item.pending_count ?? 0),
                      Number(item.total ?? 0),
                    )}
                  </Text>
                ))}
              </div>
            </div>
          ) : null}
          <div className="assistant-metrics-breakdown">
            <Text strong>运行追踪</Text>
            <div className="assistant-metrics-action-list">
              {runTrackingItems.map((item) => (
                <Text
                  aria-label={`运行追踪 ${item.label}`}
                  key={item.label}
                  type="secondary"
                >
                  {item.label}：{item.value}
                </Text>
              ))}
            </div>
          </div>
          <div className="assistant-metrics-breakdown">
            <Text strong>引用追踪</Text>
            <div className="assistant-metrics-action-list">
              {referenceTrackingItems.map((item) => (
                <Text
                  aria-label={`引用追踪 ${item.label}`}
                  key={item.label}
                  type="secondary"
                >
                  {item.label}：{item.value}
                </Text>
              ))}
            </div>
          </div>
        </>
      ) : (
        <Text type="secondary">跟踪草案、引用、运行和失败修复效果。</Text>
      )}
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
  onUseRunCardFollowupPrompt: (item: AssistantScheduledJobRunItem, prompt: string) => void;
  onUseRunFollowupPrompt: (item: AssistantToolResultItem, prompt: string) => void;
  onUseTaskGuidePrompt: (prompt: string) => void;
  resultWriteTargetLabels: Map<string, string>;
  scheduledJobRunById: Record<string, ScheduledJobRunRecord>;
}) {
  const drafts = actionDraftItems(message.toolResults);
  const taskGuideItems = taskCreationGuideItems(message.toolResults);
  const runItems = scheduledJobRunItems(message.toolResults, scheduledJobRunById);
  const diagnosticItems = scheduledJobDiagnosticItems(message.toolResults);
  const comparisonItems = scheduledJobComparisonItems(message.toolResults);
  return (
    <div className={`assistant-bubble assistant-bubble-${message.role}`}>
      <div className="assistant-bubble-avatar">
        {message.role === 'assistant' ? <RobotOutlined /> : '我'}
      </div>
      <div className="assistant-bubble-content">
        <Text>{message.content}</Text>
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
          onUseDraftWizardStepPrompt={onUseTaskGuidePrompt}
          resultWriteTargetLabels={resultWriteTargetLabels}
        />
        <AssistantTaskCreationGuideCards
          items={taskGuideItems}
          onUsePrompt={onUseTaskGuidePrompt}
        />
        <AssistantScheduledJobRunCards
          items={runItems}
          onUseRunFollowupPrompt={onUseRunCardFollowupPrompt}
        />
        <AssistantScheduledJobDiagnosticCards
          items={diagnosticItems}
          onUseRunFollowupPrompt={onUseRunFollowupPrompt}
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
  const [conversationId, setConversationId] = useState<string>();
  const [conversations, setConversations] = useState<AssistantConversationSummary[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [draftMutationId, setDraftMutationId] = useState<string>();
  const [draftResolutionById, setDraftResolutionById] = useState<AssistantDraftResolutionMap>(
    () => readAssistantDraftResolutions(),
  );
  const [draftStatusById, setDraftStatusById] = useState<Record<string, string>>({});
  const [assistantMetrics, setAssistantMetrics] = useState<AssistantMetrics>();
  const [draftTemplateMarketOpened, setDraftTemplateMarketOpened] = useState(false);
  const [draftTemplates, setDraftTemplates] = useState<AssistantDraftTemplate[]>([]);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingDraftTemplates, setIsLoadingDraftTemplates] = useState(false);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isLoadingReferences, setIsLoadingReferences] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [lastResponse, setLastResponse] = useState<AssistantChatResponse>();
  const [messages, setMessages] = useState<ChatMessage[]>(welcomeMessages);
  const [activeReferenceIndex, setActiveReferenceIndex] = useState(-1);
  const [referenceCandidates, setReferenceCandidates] = useState<AssistantReference[]>([]);
  const [recentReferences, setRecentReferences] = useState<AssistantReference[]>(() => readRecentReferences());
  const [referenceDetail, setReferenceDetail] = useState<AssistantReference>();
  const [queryReferenceResolution, setQueryReferenceResolution] = useState<QueryReferenceResolution>();
  const [resultWriteTargets, setResultWriteTargets] = useState<ResultWriteTargetRecord[]>([]);
  const [scheduledJobRunById, setScheduledJobRunById] = useState<Record<string, ScheduledJobRunRecord>>({});
  const [selectedReferences, setSelectedReferences] = useState<AssistantReference[]>([]);
  const messageListEndRef = useRef<HTMLDivElement | null>(null);
  const queryReferenceHydratedRef = useRef(false);
  const draftTemplatesLoadRequestedRef = useRef(false);
  const resultWriteTargetsLoadRequestedRef = useRef(false);

  const canSend = useMemo(() => inputValue.trim().length > 0 && !isSending, [inputValue, isSending]);
  const hasPluginActionDraft = useMemo(
    () => messages.some((item) => actionDraftItems(item.toolResults).some((draft) => draft.action === 'create_plugin_action')),
    [messages],
  );
  const resultWriteTargetLabels = useMemo(
    () => new Map(resultWriteTargets.map((target) => [target.code, target.form_label || target.label])),
    [resultWriteTargets],
  );
  const selectedReferenceKeys = useMemo(
    () => new Set(selectedReferences.map(referenceKey)),
    [selectedReferences],
  );
  const orderedReferenceCandidates = useMemo(
    () => orderReferenceCandidatesByRecent(referenceCandidates, recentReferences),
    [recentReferences, referenceCandidates],
  );
  const referenceCandidateGroups = useMemo(
    () => groupedReferenceCandidates(orderedReferenceCandidates, recentReferences),
    [orderedReferenceCandidates, recentReferences],
  );
  const roleQuickTaskGroups = useMemo(() => selectedAssistantRoleQuickTaskGroups(), []);
  const selectedReferenceInjectionText = useMemo(
    () => selectedReferenceInjectionSummary(selectedReferences),
    [selectedReferences],
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
        setSelectedReferences((currentItems) => (
          currentItems.some((item) => item.id === reference.id && item.type === reference.type)
            ? currentItems
            : [...currentItems, reference]
        ));
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
  }, []);

  useEffect(() => {
    const query = activeMentionQuery(inputValue);
    if (query === undefined) {
      setReferenceCandidates([]);
      setIsLoadingReferences(false);
      return;
    }
    let didCancel = false;
    setIsLoadingReferences(true);
    fetchAssistantReferenceCandidates({
      limit: ASSISTANT_REFERENCE_CANDIDATE_LIMIT,
      query,
    })
      .then((items) => {
        if (!didCancel) {
          setReferenceCandidates(
            items.filter((reference) => !selectedReferenceKeys.has(referenceKey(reference))),
          );
        }
      })
      .catch((error) => {
        if (!didCancel) {
          toast.error(formatMutationError(error));
          setReferenceCandidates([]);
        }
      })
      .finally(() => {
        if (!didCancel) {
          setIsLoadingReferences(false);
        }
      });
    return () => {
      didCancel = true;
    };
  }, [inputValue, selectedReferenceKeys]);

  useEffect(() => {
    setActiveReferenceIndex((index) => {
      if (!orderedReferenceCandidates.length) {
        return -1;
      }
      return Math.min(Math.max(index, 0), orderedReferenceCandidates.length - 1);
    });
  }, [orderedReferenceCandidates.length]);

  const loadConversations = useCallback(async () => {
    setIsLoadingConversations(true);
    try {
      setConversations(await fetchAssistantConversations());
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setIsLoadingConversations(false);
    }
  }, []);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

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

  const loadAssistantMetrics = useCallback(async () => {
    setIsLoadingMetrics(true);
    try {
      setAssistantMetrics(await fetchAssistantMetrics());
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setIsLoadingMetrics(false);
    }
  }, []);

  const startNewConversation = () => {
    setConversationId(undefined);
    setLastResponse(undefined);
    setMessages(welcomeMessages);
    setActiveReferenceIndex(-1);
    setReferenceCandidates([]);
    setReferenceDetail(undefined);
    setQueryReferenceResolution(undefined);
    setSelectedReferences([]);
  };

  const openDraftTemplateMarket = () => {
    setDraftTemplateMarketOpened((opened) => !opened);
    void loadDraftTemplates();
  };

  const useDraftTemplate = (template: AssistantDraftTemplate) => {
    setInputValue(template.prompt);
  };

  const addSelectedReference = (reference: AssistantReference) => {
    setSelectedReferences((items) => (
      items.some((item) => item.id === reference.id && item.type === reference.type)
        ? items
        : [...items, reference]
    ));
    setRecentReferences((items) => {
      const nextItems = nextRecentReferences(items, [reference]);
      writeRecentReferences(nextItems);
      return nextItems;
    });
    setActiveReferenceIndex(-1);
    setReferenceCandidates([]);
  };

  const removeSelectedReference = (reference: AssistantReference) => {
    setReferenceDetail((currentReference) => (
      currentReference?.id === reference.id && currentReference.type === reference.type
        ? undefined
        : currentReference
    ));
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
    const activeReference = orderedReferenceCandidates[Math.max(activeReferenceIndex, 0)];
    const scheduledJobReference = activeReference?.type === 'scheduled_job'
      ? activeReference
      : orderedReferenceCandidates.find((reference) => reference.type === 'scheduled_job');
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
      });
      const scheduledJobReference = items.find((reference) => reference.type === 'scheduled_job');
      return scheduledJobReference ? [scheduledJobReference] : [];
    } catch {
      return [];
    }
  };

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
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
    if (event.key === 'Enter') {
      const commandReferences = commandReferenceCandidates(inputValue);
      if (commandReferences.length) {
        event.preventDefault();
        void sendMessage(inputValue, commandReferences);
        return;
      }
      const reference = orderedReferenceCandidates[Math.max(activeReferenceIndex, 0)];
      if (reference) {
        event.preventDefault();
        addSelectedReference(reference);
      }
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      setActiveReferenceIndex(-1);
      setReferenceCandidates([]);
    }
  };

  const openConversation = async (targetConversationId: string) => {
    setConversationId(targetConversationId);
    setIsLoadingMessages(true);
    try {
      const history = await fetchAssistantConversationMessages(targetConversationId);
      setMessages(
        history.length
          ? history.map((item: AssistantConversationMessage) => ({
              content: item.content,
              id: item.id,
              references: item.references,
              role: item.role,
              toolResults: item.toolResults,
            }))
          : welcomeMessages,
      );
      const latestAssistantMessage = [...history].reverse().find((item) => item.role === 'assistant');
      setLastResponse(
        latestAssistantMessage
          ? {
              content: latestAssistantMessage.content,
              conversationId: targetConversationId,
              latencyMs: 0,
              messageId: latestAssistantMessage.id,
              model: latestAssistantMessage.model ?? '',
              references: latestAssistantMessage.references,
              suggestions: latestAssistantMessage.suggestions,
              toolResults: latestAssistantMessage.toolResults,
            }
          : undefined,
      );
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setIsLoadingMessages(false);
    }
  };

  const sendMessage = async (
    messageText = inputValue,
    referenceOverrides?: AssistantReference[],
  ) => {
    const content = messageText.trim();
    if (!content || isSending) {
      return;
    }
    setIsSending(true);
    const commandReferences = referenceOverrides ?? await resolveCommandReferenceCandidates(content);
    const referencesForRequest = mergeReferences(
      selectedReferences,
      commandReferences,
    );
    if (referencesForRequest.length) {
      setRecentReferences((items) => {
        const nextItems = nextRecentReferences(items, referencesForRequest);
        writeRecentReferences(nextItems);
        return nextItems;
      });
    }
    const userMessage: ChatMessage = {
      content,
      id: `user-${Date.now()}`,
      references: referencesForRequest,
      role: 'user',
    };
    setMessages((items) => [...items, userMessage]);
    setInputValue('');
    try {
      const response = await chatWithAssistant({
        context: { source: 'assistant-page' },
        conversationId,
        message: content,
        references: referencesForRequest,
      });
      setConversationId(response.conversationId);
      setLastResponse(response);
      setActiveReferenceIndex(-1);
      setReferenceDetail(undefined);
      setSelectedReferences([]);
      setReferenceCandidates([]);
      setMessages((items) => [
        ...items,
        {
          content: response.content,
          id: response.messageId,
          references: response.references,
          role: 'assistant',
          toolResults: response.toolResults,
        },
      ]);
      await loadConversations();
    } catch (error) {
      toast.error(formatMutationError(error));
      setMessages((items) => [
        ...items,
        {
          content: formatMutationError(error),
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
        },
      ]);
    } finally {
      setIsSending(false);
    }
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

  const confirmDraft = async (draft: AssistantToolResultItem) => {
    const draftId = assistantDraftId(draft);
    if (!draftId) {
      return;
    }
    setDraftMutationId(draftId);
    try {
      const result = await confirmAssistantActionDraft(draftId);
      setDraftStatusById((items) => ({ ...items, [draftId]: result.draft.status }));
      rememberDraftResolution(
        draft,
        result.run.result_id,
        result.run.result_type,
        result.draft.title,
        scheduledJobRunIdFromActionResult(result.run.result),
      );
      toast.success('草案已应用');
    } catch (error) {
      setDraftStatusById((items) => ({ ...items, [draftId]: 'failed' }));
      toast.error(formatMutationError(error));
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
      toast.success('草案已取消');
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setDraftMutationId(undefined);
    }
  };

  return (
    <PageContainer
      breadcrumb={{ items: [{ title: 'AI 助手' }] }}
      title={false}
    >
      <div className="assistant-workspace">
        <aside className="assistant-sidebar">
          <Title level={3}>AI 助手</Title>
          <Button block icon={<PlusOutlined />} onClick={startNewConversation}>
            新对话
          </Button>
          <div className="assistant-prompt-list">
            {starterPrompts.map((item) => (
              <Button
                block
                icon={item.icon}
                key={item.label}
                onClick={() => void sendMessage(item.prompt)}
              >
                {item.label}
              </Button>
            ))}
          </div>
          <Button
            aria-label="草案模板市场"
            block
            icon={<AppstoreOutlined />}
            onClick={openDraftTemplateMarket}
          >
            草案模板市场
          </Button>
          {draftTemplateMarketOpened ? (
            <AssistantDraftTemplateMarket
              isLoading={isLoadingDraftTemplates}
              templates={draftTemplates}
              onUseTemplate={useDraftTemplate}
            />
          ) : null}
          <AssistantMetricsPanel
            isLoading={isLoadingMetrics}
            metrics={assistantMetrics}
            onRefresh={() => void loadAssistantMetrics()}
          />
          {roleQuickTaskGroups.length ? (
            <div className="assistant-role-task-panel">
              <Text strong>角色快捷任务</Text>
              {roleQuickTaskGroups.map((group) => (
                <div className="assistant-role-task-group" key={group.key}>
                  <Text type="secondary">{group.label}</Text>
                  <div className="assistant-role-task-list">
                    {group.tasks.map((task) => (
                      <Button
                        block
                        key={task.key}
                        size="small"
                        onClick={() => setInputValue(task.prompt)}
                      >
                        {task.label}
                      </Button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
          <div className="assistant-history-panel">
            <div className="assistant-history-title">
              <Text strong>最近对话</Text>
              {isLoadingConversations ? <Spin size="small" /> : null}
            </div>
            <div className="assistant-history-list">
              {conversations.length ? (
                conversations.map((item) => (
                  <Button
                    block
                    className={item.id === conversationId ? 'assistant-history-active' : undefined}
                    icon={<MessageOutlined />}
                    key={item.id}
                    onClick={() => void openConversation(item.id)}
                  >
                    <span className="assistant-history-button-text">
                      <span>{item.title}</span>
                      <span>{item.messageCount} 条</span>
                    </span>
                  </Button>
                ))
              ) : (
                <Text type="secondary">暂无历史对话</Text>
              )}
            </div>
          </div>
          <div className="assistant-context-panel">
            <Text strong>上下文</Text>
            <Space size={[6, 6]} wrap>
              <Tag color="blue">AI Brain</Tag>
              <Tag color="green">项目进展</Tag>
              <Tag color="red">阻塞与待确认</Tag>
              <Tag color="purple">模型网关</Tag>
              <Tag color="geekblue">GitHub PR</Tag>
            </Space>
          </div>
        </aside>
        <section className="assistant-chat-panel">
          <div className="assistant-chat-header">
            <div>
              <Title level={3}>研发助手</Title>
              <Text type="secondary">研发大脑系统问答</Text>
            </div>
            {lastResponse ? (
              <Space size={8} wrap>
                <Tag color="blue">{lastResponse.model}</Tag>
                <Tag>{lastResponse.latencyMs} ms</Tag>
              </Space>
            ) : null}
          </div>
          <div className="assistant-message-list" aria-live="polite">
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
                onUseRunCardFollowupPrompt={useScheduledJobRunCardFollowupPrompt}
                onUseRunFollowupPrompt={useScheduledJobRunFollowupPrompt}
                onUseTaskGuidePrompt={setInputValue}
                resultWriteTargetLabels={resultWriteTargetLabels}
                scheduledJobRunById={scheduledJobRunById}
              />
            ))}
            {isLoadingMessages ? (
              <div className="assistant-thinking">
                <Spin size="small" />
                <Text type="secondary">加载中</Text>
              </div>
            ) : null}
            {isSending ? (
              <div className="assistant-thinking">
                <Spin size="small" />
                <Text type="secondary">生成中</Text>
              </div>
            ) : null}
            <div ref={messageListEndRef} aria-hidden="true" />
          </div>
          {lastResponse?.suggestions.length ? (
            <div className="assistant-suggestions">
              {lastResponse.suggestions.map((suggestion) => (
                <Button key={suggestion} size="small" onClick={() => setInputValue(suggestion)}>
                  {suggestion}
                </Button>
              ))}
            </div>
          ) : null}
          <div aria-label="本次上下文" className="assistant-selected-reference-list">
            <div className="assistant-selected-reference-header">
              <Text strong>本次上下文</Text>
              <Text type="secondary">
                {selectedReferences.length
                  ? `${selectedReferences.length} 个引用 · ${selectedReferenceInjectionText}`
                  : '0 个显式引用 · 0 个知识 chunk 注入模型'}
              </Text>
            </div>
            {queryReferenceResolution ? (
              <div
                aria-label="链接引用状态"
                className={`assistant-query-reference-status assistant-query-reference-status-${queryReferenceResolution.status}`}
              >
                <Space size={6} wrap>
                  <Tag color={queryReferenceResolutionLabel(queryReferenceResolution.status).color}>
                    {queryReferenceResolutionLabel(queryReferenceResolution.status).text}
                  </Tag>
                  <Text type={queryReferenceResolution.status === 'failed' ? 'danger' : 'secondary'}>
                    {queryReferenceResolutionText(queryReferenceResolution)}
                  </Text>
                </Space>
              </div>
            ) : null}
            {selectedReferences.length ? (
              <div className="assistant-selected-reference-tags">
                {selectedReferences.map((reference) => (
                  <div
                    className="assistant-selected-reference-card"
                    key={`${reference.type}:${reference.id}`}
                  >
                    <div className="assistant-selected-reference-card-header">
                      <Space size={6} wrap>
                        <Tag color="blue">{referenceTypeLabel(reference.type)}</Tag>
                        <Text strong>{reference.title}</Text>
                      </Space>
                      <Button
                        aria-label={`移除 ${reference.title}`}
                        size="small"
                        type="text"
                        onClick={() => removeSelectedReference(reference)}
                      >
                        移除
                      </Button>
                    </div>
                    <Text className="assistant-selected-reference-meta" type="secondary">
                      {referenceMetaText(reference)}
                    </Text>
                    <Text className="assistant-selected-reference-summary">
                      {referenceSummaryText(reference)}
                    </Text>
                    <Space size={6} wrap>
                      <Tag
                        color={
                          reference.type === 'knowledge_document' || reference.type === 'knowledge_chunk'
                            ? 'green'
                            : 'default'
                        }
                      >
                        {referenceInjectionText(reference)}
                      </Tag>
                      <Button
                        aria-label={`查看摘要 ${reference.title}`}
                        size="small"
                        onClick={() => setReferenceDetail(reference)}
                      >
                        查看摘要
                      </Button>
                      <Button href={reference.url} size="small" type="link">
                        查看来源
                      </Button>
                    </Space>
                  </div>
                ))}
              </div>
            ) : (
              <div className="assistant-selected-reference-empty">
                <Space size={6} wrap>
                  <Tag color="default">0 个显式引用</Tag>
                  <Tag color="default">0 个知识 chunk 注入模型</Tag>
                  <Tag color="default">未注入知识正文</Tag>
                </Space>
                <Text type="secondary">仅使用系统上下文和当前会话</Text>
              </div>
            )}
            <AssistantReferenceDetailModal
              reference={referenceDetail}
              onClose={() => setReferenceDetail(undefined)}
            />
          </div>
          {referenceCandidates.length || isLoadingReferences ? (
            <div
              aria-label="引用候选"
              className="assistant-reference-candidates"
            >
              <div className="assistant-reference-candidates-header">
                <Text strong>引用候选</Text>
                <Text type="secondary">↑↓ 选择，Enter 添加</Text>
              </div>
              {isLoadingReferences ? <Spin size="small" /> : null}
              {referenceCandidateGroups.map((group) => (
                <div className="assistant-reference-candidate-group" key={group.type}>
                  <div className="assistant-reference-candidate-group-title">
                    <Text strong>{group.label}</Text>
                    <Tag color="default">{group.items.length}</Tag>
                  </div>
                  {group.items.map(({ index: referenceIndex, reference }) => {
                    const isActive = referenceIndex === activeReferenceIndex;
                    return (
                      <Button
                        className={isActive ? 'assistant-reference-candidate-active' : undefined}
                        icon={<LinkOutlined />}
                        key={`${reference.type}:${reference.id}`}
                        size="small"
                        onClick={() => addSelectedReference(reference)}
                        onMouseEnter={() => setActiveReferenceIndex(referenceIndex)}
                      >
                        <span className="assistant-reference-candidate-main">
                          <span className="assistant-reference-candidate-title">{reference.title}</span>
                          <span className="assistant-reference-candidate-meta">
                            {referenceMetaText(reference)}
                          </span>
                        </span>
                        <Tag color="default">{referenceTypeLabel(reference.type)}</Tag>
                      </Button>
                    );
                  })}
                </div>
              ))}
            </div>
          ) : null}
          <div className="assistant-composer">
            <TextArea
              aria-label="发送给 AI 助手"
              onChange={(event) => setInputValue(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              onPressEnter={(event) => {
                if (referenceCandidates.length) {
                  event.preventDefault();
                  return;
                }
                if (!event.shiftKey) {
                  event.preventDefault();
                  void sendMessage();
                }
              }}
              placeholder="输入问题"
              rows={3}
              value={inputValue}
            />
            <Button
              aria-label="发送"
              disabled={!canSend}
              icon={<SendOutlined />}
              loading={isSending}
              onClick={() => void sendMessage()}
              type="primary"
            >
              发送
            </Button>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
