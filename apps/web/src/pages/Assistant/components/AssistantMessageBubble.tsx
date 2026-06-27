import {
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  LinkOutlined,
  ProjectOutlined,
  ReloadOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { Button, Space, Tag, Typography } from 'antd';

import {
  type AssistantDraftResolutionMap,
  type AssistantToolResult,
  type AssistantToolResultItem,
  type ScheduledJobRunRecord,
} from '../../../services/aiBrain';
import {
  type AssistantScheduledJobRunItem,
  type AssistantScheduledJobRunNoticeItem,
  scheduledJobRunDefaultFollowupPrompt,
  scheduledJobRunIsActive,
  scheduledJobRunItems,
  scheduledJobRunNoticeItems,
  scheduledJobRunStatusLabel,
} from '../assistantRunPresentation';
import { type ChatMessage } from '../hooks/useAssistantConversation';
import { ExecutionTraceLink } from '../../../components/ExecutionTraceLink';
import { AssistantActionDraftCards } from './AssistantDraftCards';
import { actionDraftItems } from './assistantMessageHelpers';
import { assistantReferenceFullChainHref } from './referencePresentation';

const { Text } = Typography;

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

function diagnosticStageLogSourceType(stage: string, logId: string) {
  if (!logId || logId === '-') {
    return undefined;
  }
  if (stage === 'ai_processing' || logId.startsWith('model_gateway_log')) {
    return 'model_gateway_log';
  }
  if (
    stage === 'data_connection'
    || stage === 'result_action'
    || logId.startsWith('plugin_invocation_log')
  ) {
    return 'plugin_invocation_log';
  }
  return undefined;
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

function comparisonDifferenceItems(item: AssistantToolResultItem) {
  return Array.isArray(item.differences)
    ? item.differences.filter(
      (difference): difference is AssistantToolResultItem =>
        Boolean(difference) && typeof difference === 'object' && !Array.isArray(difference),
    )
    : [];
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
                const logSourceType = diagnosticStageLogSourceType(stageName, logId);
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
                      <Text type="secondary">
                        关联日志：
                        <ExecutionTraceLink
                          fallback={logId}
                          sourceId={logId}
                          sourceType={logSourceType ?? ''}
                        >
                          {logId}
                        </ExecutionTraceLink>
                      </Text>
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

export function AssistantBubble({
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
            {message.references.map((reference) => {
              const fullChainHref = assistantReferenceFullChainHref(reference);
              return (
                <Space key={`${reference.type}:${reference.id}`} size={4} wrap>
                  <Button
                    href={reference.url}
                    icon={<LinkOutlined />}
                    size="small"
                    type="link"
                  >
                    {reference.title}
                  </Button>
                  {fullChainHref ? (
                    <Button href={fullChainHref} size="small" type="link">
                      全链路
                    </Button>
                  ) : null}
                </Space>
              );
            })}
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
