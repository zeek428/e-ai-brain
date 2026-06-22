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
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  fetchAssistantDraftTemplates,
  fetchAssistantRoleQuickTasks,
  fetchResultWriteTargets,
  getStoredCurrentUser,
  type AssistantDraftTemplate,
  type AssistantDraftResolutionMap,
  type AssistantReference,
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
import { assistantDraftId } from './components/draftPresentation';
import { AssistantReferenceContext } from './components/AssistantReferenceContext';
import { AssistantRuntimeStatus } from './components/AssistantRuntimeStatus';
import { AssistantReferencePicker } from './components/AssistantReferencePicker';
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
import { useAssistantComposerController } from './hooks/useAssistantComposerController';
import { type QueryDraftResolution } from './hooks/useAssistantDrafts';
import { useAssistantDraftLifecycle } from './hooks/useAssistantDraftLifecycle';
import { useAssistantMetricsPanel } from './hooks/useAssistantMetricsPanel';
import { useAssistantRuntimeStatus } from './hooks/useAssistantRuntimeStatus';
import { useAssistantRunPolling } from './hooks/useAssistantRunPolling';
import { useAssistantSendController } from './hooks/useAssistantSendController';
import {
  type AssistantScheduledJobRunItem,
  type AssistantScheduledJobRunNoticeItem,
  scheduledJobRunDefaultFollowupPrompt,
  scheduledJobRunFollowupPrompt,
  scheduledJobRunIsActive,
  scheduledJobRunItemFollowupPrompt,
  scheduledJobRunItems,
  scheduledJobRunNoticeItems,
  scheduledJobRunReferenceFromRunItem,
  scheduledJobRunReferenceFromToolItem,
  scheduledJobRunStatusLabel,
} from './assistantRunPresentation';
import './Assistant.css';

const { Text, Title } = Typography;

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

function comparisonDifferenceItems(item: AssistantToolResultItem) {
  return Array.isArray(item.differences)
    ? item.differences.filter(
      (difference): difference is AssistantToolResultItem =>
        Boolean(difference) && typeof difference === 'object' && !Array.isArray(difference),
    )
    : [];
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
    hasMoreConversations,
    isLoadingConversations,
    isLoadingMoreConversations,
    isLoadingMessages,
    isSending,
    lastResponse,
    loadConversationMessages,
    loadConversations,
    loadMoreConversations,
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
    activeAddActionIndex,
    activeMention,
    activeReferenceIndex,
    addActionCandidates,
    addActionQuery,
    addMenuRef,
    addMenuTriggerRef,
    addSelectedReference,
    canSend,
    changeAddActionQuery,
    handleAddActionMenuKeyDown,
    handleComposerKeyDown,
    hasUnsentComposerState,
    inputValue,
    isAddMenuOpen,
    isContextExpanded,
    isLoadingAddActions,
    isLoadingReferences,
    onChangeInput,
    prepareConversationSwitch,
    queryReferenceResolution,
    referenceCandidateGroups,
    referenceCandidates,
    referenceEmptyState,
    rememberReferences,
    removeSelectedReference,
    resetComposerState: resetComposerControllerState,
    resolveCommandReferenceCandidates,
    runOncePermissionHint,
    selectAddActionCandidate,
    selectedReferences,
    setActiveAddActionIndex,
    setActiveReferenceIndex,
    setCommittedActionCommand,
    setDismissedReferencePickerValue,
    setInputValue,
    setIsAddMenuOpen,
    setIsContextExpanded,
    setReferenceCandidates,
    setSelectedReferences,
    shouldShowReferenceCandidates,
    submitComposerEnter,
    toggleAddMenu,
  } = useAssistantComposerController({ isSending });
  const {
    cancelDraft,
    confirmDraft,
    draftMutationId,
    draftResolutionById,
    draftStatusById,
    linkedDraft,
    queryDraftResolution,
    regenerateDraft,
    setLinkedDraft,
    setQueryDraftResolution,
    viewDraft,
  } = useAssistantDraftLifecycle({ setInputValue });
  const [draftTemplateMarketOpened, setDraftTemplateMarketOpened] = useState(false);
  const [draftTemplates, setDraftTemplates] = useState<AssistantDraftTemplate[]>([]);
  const [isLoadingDraftTemplates, setIsLoadingDraftTemplates] = useState(false);
  const {
    isRefreshingRuntimeStatus,
    refreshRuntimeStatus,
    runtimeStatus,
    runtimeStatusCheckedAt,
  } = useAssistantRuntimeStatus();
  const [runtimeStatusPanelOpen, setRuntimeStatusPanelOpen] = useState(false);
  const [resultWriteTargets, setResultWriteTargets] = useState<ResultWriteTargetRecord[]>([]);
  const [roleQuickTasksExpanded, setRoleQuickTasksExpanded] = useState(false);
  const [roleQuickTaskGroups, setRoleQuickTaskGroups] = useState<AssistantRoleQuickTaskGroup[]>([]);
  const { scheduledJobRunById } = useAssistantRunPolling(messages);
  const messageListEndRef = useRef<HTMLDivElement | null>(null);
  const queryDraftStatusRef = useRef<HTMLDivElement | null>(null);
  const draftTemplatesLoadRequestedRef = useRef(false);
  const resultWriteTargetsLoadRequestedRef = useRef(false);
  const roleQuickTasksLoadRequestedRef = useRef(false);
  const {
    assistantMetricDetails,
    assistantMetrics,
    assistantMetricsWindowDays,
    changeAssistantMetricsWindow,
    exportAssistantMetricsFile,
    isExportingMetrics,
    isLoadingMetricDetails,
    isLoadingMetrics,
    loadAssistantMetrics,
    metricsPanelOpened,
    openAssistantMetricDetails,
    openMetricsPanel,
    setMetricsPanelOpened,
  } = useAssistantMetricsPanel();
  const {
    restoreFailedRequest,
    retryFailedRequest,
    sendMessage,
    stopGenerating,
  } = useAssistantSendController({
    conversationId,
    inputValue,
    isSending,
    loadConversations,
    rememberReferences,
    resolveCommandReferenceCandidates,
    selectedReferences,
    setActiveReferenceIndex,
    setCommittedActionCommand,
    setConversationId,
    setDismissedReferencePickerValue,
    setInputValue,
    setIsAddMenuOpen,
    setIsSending,
    setLastResponse,
    setMessages,
    setReferenceCandidates,
    setSelectedReferences,
  });

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

  useEffect(() => {
    if (typeof messageListEndRef.current?.scrollIntoView !== 'function') {
      return;
    }
    if (queryDraftResolution && !isSending) {
      return;
    }
    messageListEndRef.current.scrollIntoView({ block: 'end' });
  }, [isLoadingMessages, isSending, messages, queryDraftResolution, scheduledJobRunById]);

  useEffect(() => {
    if (!queryDraftResolution || typeof queryDraftStatusRef.current?.scrollIntoView !== 'function') {
      return;
    }
    queryDraftStatusRef.current.scrollIntoView({ block: 'nearest' });
  }, [linkedDraft, queryDraftResolution]);

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
    resetComposerControllerState({ clearInput: options.clearInput });
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

  const openRuntimeStatusPanel = useCallback(() => {
    setRuntimeStatusPanelOpen(true);
    if (!runtimeStatus) {
      void refreshRuntimeStatus({ force: true });
    }
  }, [refreshRuntimeStatus, runtimeStatus]);

  const applyDraftTemplate = (template: AssistantDraftTemplate) => {
    setCommittedActionCommand(undefined);
    setInputValue(template.prompt);
  };

  const loadConversation = async (
    targetConversationId: string,
    options: { preserveComposer?: boolean } = {},
  ) => {
    prepareConversationSwitch(options);
    if (!options.preserveComposer) {
      setLinkedDraft(undefined);
      setQueryDraftResolution(undefined);
    }
    setConversationId(targetConversationId);
    await loadConversationMessages(targetConversationId);
  };

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

  return (
    <PageContainer title={false}>
      <div className="assistant-workspace">
        <AssistantSidebar
          conversationId={conversationId}
          conversations={conversations}
          hasMoreConversations={hasMoreConversations}
          isLoadingConversations={isLoadingConversations}
          isLoadingMoreConversations={isLoadingMoreConversations}
          isLoadingMetrics={isLoadingMetrics}
          isRefreshingRuntimeStatus={isRefreshingRuntimeStatus}
          showDuplicateConversations={showDuplicateConversations}
          roleQuickTaskCount={roleQuickTaskCount}
          roleQuickTaskGroups={roleQuickTaskGroups}
          roleQuickTasksExpanded={roleQuickTasksExpanded}
          onToggleDuplicateConversations={toggleDuplicateConversations}
          onLoadMoreConversations={loadMoreConversations}
          onOpenConversation={openConversation}
          onOpenDraftTemplateMarket={openDraftTemplateMarket}
          onOpenMetricsPanel={openMetricsPanel}
          onOpenRuntimeStatusPanel={openRuntimeStatusPanel}
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
                ref={queryDraftStatusRef}
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
            onChangeInput={onChangeInput}
            onChangeAddActionQuery={changeAddActionQuery}
            onCloseAddMenu={() => setIsAddMenuOpen(false)}
            onHoverAddAction={setActiveAddActionIndex}
            onAddActionMenuKeyDown={handleAddActionMenuKeyDown}
            onKeyDown={(event) => handleComposerKeyDown(event, {
              sendMessage: (messageText, references) => void sendMessage(messageText, references),
              stopGenerating,
            })}
            onPressEnter={(event) => {
              if (
                event.defaultPrevented
                || submitComposerEnter(event, {
                  sendMessage: (messageText, references) => void sendMessage(messageText, references),
                  stopGenerating,
                })
              ) {
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
          isExporting={isExportingMetrics}
          isLoading={isLoadingMetrics}
          metricDetails={assistantMetricDetails}
          metrics={assistantMetrics}
          onChangeWindow={changeAssistantMetricsWindow}
          onExport={exportAssistantMetricsFile}
          onOpenDetail={openAssistantMetricDetails}
          onRefresh={() => void loadAssistantMetrics()}
          windowDays={assistantMetricsWindowDays}
        />
      </Modal>
      <Modal
        className="assistant-workbench-modal"
        footer={null}
        open={runtimeStatusPanelOpen}
        title="运行诊断"
        width={860}
        onCancel={() => setRuntimeStatusPanelOpen(false)}
      >
        <AssistantRuntimeStatus
          checkedAt={runtimeStatusCheckedAt}
          isRefreshing={isRefreshingRuntimeStatus}
          runtimeStatus={runtimeStatus}
          showHealthy
          onRefresh={() => void refreshRuntimeStatus({ force: true })}
        />
      </Modal>
    </PageContainer>
  );
}
