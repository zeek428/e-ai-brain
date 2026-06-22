import type {
  AssistantReference,
  AssistantToolResult,
  AssistantToolResultItem,
  ScheduledJobRunRecord,
} from '../../services/aiBrain';
import type { ChatMessage } from './hooks/useAssistantConversation';

export type AssistantScheduledJobRunItem = {
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

export type AssistantScheduledJobRunNoticeItem = {
  description: string;
  key: string;
  requiredPermission?: string;
  scheduledJobId?: string;
  status: string;
  title: string;
};

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

function unknownRecord(value: unknown) {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

export function scheduledJobRunReferenceFromToolItem(
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

export function scheduledJobRunReferenceFromRunItem(
  item: AssistantScheduledJobRunItem,
): AssistantReference {
  return {
    id: item.id,
    title: item.title,
    type: 'scheduled_job_run',
    url: item.url ?? `/tasks/scheduled-jobs?run_id=${encodeURIComponent(item.id)}`,
  };
}

export function scheduledJobRunFollowupPrompt(
  item: AssistantToolResultItem,
  prompt: string,
) {
  const reference = scheduledJobRunReferenceFromToolItem(item);
  return reference ? `@${reference.title} ${prompt}` : prompt;
}

export function scheduledJobRunItemFollowupPrompt(
  item: AssistantScheduledJobRunItem,
  prompt: string,
) {
  const reference = scheduledJobRunReferenceFromRunItem(item);
  return `@${reference.title} ${prompt}`;
}

export function scheduledJobRunStatusLabel(status?: string) {
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

export function scheduledJobRunIsActive(status?: string) {
  return status === 'queued' || status === 'running';
}

export function scheduledJobRunDefaultFollowupPrompt(status?: string) {
  return status === 'failed' ? '为什么这次任务失败？' : '帮我分析这次运行结果';
}

export function scheduledJobRunRecordChanged(
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

export function scheduledJobRunNoticeItems(toolResults?: AssistantToolResult[]) {
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

export function scheduledJobRunItems(
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

export function scheduledJobRunPollTargets(
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
