import { CopyOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { Alert, Button, Descriptions, message, Space, Tag, Typography } from 'antd';

import { type ScheduledJobRunRecord } from '../../../services/aiBrain';
import {
  fetchScheduledJobTraceNodeRerunPreview,
  rerunScheduledJobTraceNode,
  type ScheduledJobTraceNodeRerunControl,
  type ScheduledJobTraceNodeRerunNextAction,
  type ScheduledJobTraceNodeRerunPreview,
} from '../../../services/systemOperationsClient';
import { formatDisplayDateTime } from '../../../utils/dateTime';
import {
  formatTraceJsonValue,
  getRunExecutionNode,
  isEmptyTraceJsonValue,
  isTraceRecord,
  nodeFieldText,
  nodeNestedArrayCountText,
  nodeNestedFieldText,
  runNodeTagColor,
  type TemplateSourceView,
} from './scheduledJobRunTraceHelpers';

const runTriggerTypeLabelByValue = new Map([
  ['manual', '手动触发'],
  ['manual_rerun', '运行记录复跑'],
  ['scheduler', '调度触发'],
]);

const templateSourceTypeLabelByValue = new Map([
  ['scheduled_job', '作业'],
  ['scheduled_job_run', '运行记录'],
]);

function templateSourceDisplayText(source: TemplateSourceView): string {
  const title = source.title || source.sourceId || '-';
  return source.sourceId && source.sourceId !== title ? `${title} (${source.sourceId})` : title;
}

function traceDebugActionTypes(node: Record<string, unknown>): Set<string> {
  const rawActions = Array.isArray(node.debug_actions) ? node.debug_actions : [];
  return new Set(
    rawActions
      .filter(isTraceRecord)
      .filter((action) => action.enabled !== false)
      .map((action) => nodeFieldText(action.type))
      .filter((type): type is string => Boolean(type)),
  );
}

function copyTraceJson(label: string, value: unknown) {
  const text = formatTraceJsonValue(value);
  if (text === '暂无数据') {
    void message.warning(`${label}暂无可复制内容`);
    return;
  }
  if (!navigator.clipboard?.writeText) {
    void message.warning('当前浏览器不支持直接复制，请从 JSON 区域手动复制');
    return;
  }
  void navigator.clipboard.writeText(text).then(
    () => message.success(`${label}已复制`),
    () => message.error(`${label}复制失败`),
  );
}

function snapshotReadyText(snapshot: Record<string, unknown> | undefined, key: string) {
  return snapshot?.[key] ? '有' : '无';
}

function traceStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

function traceRerunControls(value: unknown): ScheduledJobTraceNodeRerunControl[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isTraceRecord).map((control) => ({
    key: nodeFieldText(control.key),
    label: nodeFieldText(control.label),
    reason: nodeFieldText(control.reason),
    required: control.required === true,
    satisfied: control.satisfied === true,
    status: nodeFieldText(control.status),
  }));
}

function rerunControlStatusColor(status: string | undefined) {
  if (status === 'satisfied') {
    return 'green';
  }
  if (status === 'blocked') {
    return 'red';
  }
  if (status === 'needs_review') {
    return 'orange';
  }
  if (status === 'missing') {
    return 'volcano';
  }
  return 'default';
}

function rerunNextActionStatusColor(status: string | undefined) {
  if (status === 'available') {
    return 'green';
  }
  if (status === 'recommended') {
    return 'blue';
  }
  if (status === 'blocked') {
    return 'red';
  }
  if (status === 'needs_review') {
    return 'orange';
  }
  return 'default';
}

function traceRerunNextActions(value: unknown): ScheduledJobTraceNodeRerunNextAction[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isTraceRecord).map((action) => ({
    description: nodeFieldText(action.description),
    key: nodeFieldText(action.key),
    label: nodeFieldText(action.label),
    missing_controls: Array.isArray(action.missing_controls)
      ? action.missing_controls.map(String).filter(Boolean)
      : undefined,
    request: isTraceRecord(action.request) ? action.request : undefined,
    side_effect_policy: nodeFieldText(action.side_effect_policy),
    status: nodeFieldText(action.status),
  }));
}

function executionPolicyText(policy: unknown) {
  const record = isTraceRecord(policy) ? policy : undefined;
  if (!record) {
    return undefined;
  }
  return nodeFieldText(record.message) ?? (
    record.allowed === true ? '单节点复跑可执行' : '单节点复跑仍受保护'
  );
}

function controlSummaryNumber(summary: unknown, key: string, fallback: number) {
  const record = isTraceRecord(summary) ? summary : undefined;
  const value = record?.[key];
  return typeof value === 'number' ? value : fallback;
}

function rerunControlSummaryText(
  summary: unknown,
  controls: ScheduledJobTraceNodeRerunControl[],
) {
  if (!controls.length && !isTraceRecord(summary)) {
    return undefined;
  }
  const fallbackCounts = controls.reduce(
    (counts, control) => {
      if (control.status === 'satisfied') {
        counts.satisfied += 1;
      } else if (control.status === 'blocked') {
        counts.blocked += 1;
      } else if (control.status === 'needs_review') {
        counts.needsReview += 1;
      } else if (control.status === 'missing') {
        counts.missing += 1;
      }
      return counts;
    },
    { blocked: 0, missing: 0, needsReview: 0, satisfied: 0 },
  );
  const satisfied = controlSummaryNumber(summary, 'satisfied_count', fallbackCounts.satisfied);
  const missing = controlSummaryNumber(summary, 'missing_count', fallbackCounts.missing);
  const blocked = controlSummaryNumber(summary, 'blocked_count', fallbackCounts.blocked);
  const needsReview = controlSummaryNumber(
    summary,
    'needs_review_count',
    fallbackCounts.needsReview,
  );
  return `控制项：已满足 ${satisfied} / 缺失 ${missing} / 阻断 ${blocked} / 待确认 ${needsReview}`;
}

function snapshotPreviewText(preview: unknown, key: string) {
  const snapshotPreview = isTraceRecord(preview) ? preview : undefined;
  const item = isTraceRecord(snapshotPreview?.[key]) ? snapshotPreview[key] : undefined;
  if (!item?.available) {
    return `${key}: 无`;
  }
  const size = typeof item.size_bytes === 'number' ? `${item.size_bytes}B` : '-';
  return `${key}: 有 · ${size}${item.truncated ? ' · 已截断' : ''}`;
}

export function TemplateSourceSummary({ source }: { source: TemplateSourceView | undefined }) {
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
  const node = isTraceRecord(value) ? value : {};
  const status = nodeFieldText(node.status) ?? (
    isEmptyTraceJsonValue(value) ? '暂无数据' : 'available'
  );
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
    { label: '完成时间', value: nodeFieldText(node.finished_at) ? formatDisplayDateTime(node.finished_at as string) : undefined },
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

export function RunExecutionChain({ run }: { run: ScheduledJobRunRecord }) {
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

export function RunTraceDag({
  onFullRunRerunRequested,
  onNodeRerunCreated,
  run,
}: {
  onFullRunRerunRequested?: (request: Record<string, unknown>) => void | Promise<void>;
  onNodeRerunCreated?: (run: ScheduledJobRunRecord) => void;
  run: ScheduledJobRunRecord;
}) {
  const rawTraceGraph = run.result_summary?.trace_graph;
  const traceGraph = isTraceRecord(rawTraceGraph) ? rawTraceGraph : undefined;
  const nodes = Array.isArray(traceGraph?.nodes)
    ? traceGraph.nodes.filter(isTraceRecord)
    : [];
  const edges = Array.isArray(traceGraph?.edges)
    ? traceGraph.edges.filter(isTraceRecord)
    : [];
  const [previewByNodeId, setPreviewByNodeId] = useState<Record<string, ScheduledJobTraceNodeRerunPreview>>({});
  const [previewErrorByNodeId, setPreviewErrorByNodeId] = useState<Record<string, string>>({});
  const [previewLoadingNodeId, setPreviewLoadingNodeId] = useState<string>();
  const [fullRunLoadingNodeId, setFullRunLoadingNodeId] = useState<string>();
  const [rerunLoadingNodeId, setRerunLoadingNodeId] = useState<string>();
  const [rerunResultByNodeId, setRerunResultByNodeId] = useState<Record<string, ScheduledJobRunRecord>>({});
  if (!nodes.length && !edges.length) {
    return null;
  }
  const loadRerunPreview = async (nodeId: string) => {
    setPreviewLoadingNodeId(nodeId);
    setPreviewErrorByNodeId((previous) => {
      const next = { ...previous };
      delete next[nodeId];
      return next;
    });
    try {
      const preview = await fetchScheduledJobTraceNodeRerunPreview(run.id, nodeId);
      setPreviewByNodeId((previous) => ({ ...previous, [nodeId]: preview }));
    } catch (error) {
      setPreviewErrorByNodeId((previous) => ({
        ...previous,
        [nodeId]: error instanceof Error ? error.message : '复跑预检失败',
      }));
    } finally {
      setPreviewLoadingNodeId(undefined);
    }
  };
  const confirmNodeRerun = async (nodeId: string) => {
    setRerunLoadingNodeId(nodeId);
    try {
      const rerunResult = await rerunScheduledJobTraceNode(run.id, nodeId);
      setRerunResultByNodeId((previous) => ({ ...previous, [nodeId]: rerunResult }));
      onNodeRerunCreated?.(rerunResult);
      void message.success('单节点复跑已创建');
    } catch (error) {
      void message.error(error instanceof Error ? error.message : '单节点复跑失败');
    } finally {
      setRerunLoadingNodeId(undefined);
    }
  };
  const confirmFullRunRerun = async (nodeId: string, request: Record<string, unknown>) => {
    if (!onFullRunRerunRequested) {
      void message.warning('当前页面未提供整条复跑入口，请回到运行记录列表发起复跑');
      return;
    }
    setFullRunLoadingNodeId(nodeId);
    try {
      await onFullRunRerunRequested(request);
    } finally {
      setFullRunLoadingNodeId(undefined);
    }
  };
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
          const debugActionTypes = traceDebugActionTypes(node);
          const rerunHint = nodeFieldText(node.rerun_hint);
          const rerunPlan = isTraceRecord(node.rerun_plan) ? node.rerun_plan : undefined;
          const canLoadRerunPreview = Boolean(
            rerunPlan || typeof node.rerun_supported === 'boolean' || rerunHint,
          );
          const snapshotStatus = isTraceRecord(node.snapshot_status)
            ? node.snapshot_status
            : isTraceRecord(rerunPlan?.snapshot_status)
              ? rerunPlan.snapshot_status
              : undefined;
          const rerunPreview = previewByNodeId[id];
          const rerunPreviewError = previewErrorByNodeId[id];
          const rerunResult = rerunResultByNodeId[id];
          const blockedBy = traceStringList(rerunPreview?.blocked_by);
          const missingControls = traceStringList(rerunPreview?.missing_controls);
          const rerunControls = traceRerunControls(rerunPreview?.rerun_controls);
          const rerunNextActions = traceRerunNextActions(rerunPreview?.next_actions);
          const fullRunRequest = rerunNextActions.find(
            (action) => action.key === 'rerun_full_scheduled_job' && action.request,
          )?.request ?? (
            isTraceRecord(rerunPreview?.full_run_request)
              ? rerunPreview.full_run_request
              : undefined
          );
          const rerunAllowed = isTraceRecord(rerunPreview?.execution_policy)
            && rerunPreview?.execution_policy.allowed === true;
          const policyText = executionPolicyText(rerunPreview?.execution_policy);
          const controlSummaryText = rerunControlSummaryText(
            rerunPreview?.control_summary,
            rerunControls,
          );
          const stageLabel = nodeFieldText(node.stage_label);
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
                  {stageLabel ? <Tag color="geekblue">{stageLabel}</Tag> : null}
                  <Typography.Text strong>{label}</Typography.Text>
                </Space>
                <Space wrap size={8}>
                  <Tag color="blue">{duration}</Tag>
                  <Tag>重试 {retryCount}</Tag>
                  {error ? <Tag color="red">{error}</Tag> : null}
                </Space>
                <Space wrap size={8}>
                  {debugActionTypes.has('copy_input') ? (
                    <Button
                      icon={<CopyOutlined />}
                      onClick={() => copyTraceJson('节点输入', node.input)}
                      size="small"
                    >
                      复制输入
                    </Button>
                  ) : null}
                  {debugActionTypes.has('copy_output') ? (
                    <Button
                      icon={<CopyOutlined />}
                      onClick={() => copyTraceJson('节点输出', node.output)}
                      size="small"
                    >
                      复制输出
                    </Button>
                  ) : null}
                  {debugActionTypes.has('copy_error') ? (
                    <Button
                      danger
                      icon={<CopyOutlined />}
                      onClick={() => copyTraceJson('节点错误', node.error)}
                      size="small"
                    >
                      复制错误
                    </Button>
                  ) : null}
                  {debugActionTypes.has('copy_rerun_plan') ? (
                    <Button
                      icon={<CopyOutlined />}
                      onClick={() => copyTraceJson('复跑计划', rerunPlan)}
                      size="small"
                    >
                      复制复跑计划
                    </Button>
                  ) : null}
                  {canLoadRerunPreview ? (
                    <Button
                      aria-label="复跑预检"
                      icon={<SafetyCertificateOutlined />}
                      loading={previewLoadingNodeId === id}
                      onClick={() => void loadRerunPreview(id)}
                      size="small"
                    >
                      复跑预检
                    </Button>
                  ) : null}
                </Space>
                {rerunPlan ? (
                  <Space wrap size={8}>
                    <Tag color={rerunPlan.single_node_supported ? 'green' : 'orange'}>
                      单节点复跑{rerunPlan.single_node_supported ? '可用' : '待保护'}
                    </Tag>
                    <Tag>输入快照 {snapshotReadyText(snapshotStatus, 'input')}</Tag>
                    <Tag>输出快照 {snapshotReadyText(snapshotStatus, 'output')}</Tag>
                    {nodeFieldText(rerunPlan.side_effect_policy) ? (
                      <Tag color="purple">副作用 {nodeFieldText(rerunPlan.side_effect_policy)}</Tag>
                    ) : null}
                    {nodeFieldText(rerunPlan.safe_next_action) ? (
                      <Tag color="blue">建议 {nodeFieldText(rerunPlan.safe_next_action)}</Tag>
                    ) : null}
                  </Space>
                ) : null}
                {rerunPreview ? (
                  <Alert
                    description={(
                      <Space orientation="vertical" size={6} style={{ width: '100%' }}>
                        <Space size={[8, 8]} wrap>
                          <Tag color={rerunPreview.preflight_status === 'ready' ? 'green' : 'orange'}>
                            {rerunPreview.preflight_status ?? 'unknown'}
                          </Tag>
                          {rerunPreview.safe_next_action ? (
                            <Tag color="blue">建议 {rerunPreview.safe_next_action}</Tag>
                          ) : null}
                          {rerunPreview.side_effect_policy ? (
                            <Tag color="purple">副作用 {rerunPreview.side_effect_policy}</Tag>
                          ) : null}
                        </Space>
                        {blockedBy.length ? (
                          <Typography.Text type="secondary">
                            阻断原因：{blockedBy.join('、')}
                          </Typography.Text>
                        ) : null}
                        {policyText ? (
                          <Typography.Text type="secondary">
                            执行策略：{policyText}
                          </Typography.Text>
                        ) : null}
                        {missingControls.length ? (
                          <Typography.Text type="secondary">
                            缺失控制：{missingControls.join('、')}
                          </Typography.Text>
                        ) : null}
                        {controlSummaryText ? (
                          <Typography.Text type="secondary">{controlSummaryText}</Typography.Text>
                        ) : null}
                        {rerunControls.length ? (
                          <Space size={[8, 8]} wrap>
                            {rerunControls.map((control) => {
                              const label = control.label ?? control.key ?? '-';
                              const statusText = control.status ?? 'unknown';
                              return (
                                <Tag
                                  color={rerunControlStatusColor(control.status)}
                                  key={`${control.key ?? label}-${statusText}`}
                                  title={control.reason}
                                >
                                  {label} · {statusText}
                                </Tag>
                              );
                            })}
                          </Space>
                        ) : null}
                        {rerunNextActions.length ? (
                          <Space orientation="vertical" size={4} style={{ width: '100%' }}>
                            <Typography.Text type="secondary">下一步动作</Typography.Text>
                            <Space size={[8, 8]} wrap>
                              {rerunNextActions.map((action, index) => {
                                const label = action.label ?? action.key ?? '动作';
                                const statusText = action.status ?? 'unknown';
                                return (
                                  <Tag
                                    color={rerunNextActionStatusColor(action.status)}
                                    key={`${action.key ?? label}-${index}`}
                                    title={action.description}
                                  >
                                    {label} · {statusText}
                                  </Tag>
                                );
                              })}
                              {rerunAllowed ? (
                                <Button
                                  loading={rerunLoadingNodeId === id}
                                  onClick={() => void confirmNodeRerun(id)}
                                  size="small"
                                  type="primary"
                                >
                                  确认复跑
                                </Button>
                              ) : null}
                              {fullRunRequest ? (
                                <Button
                                  loading={fullRunLoadingNodeId === id}
                                  onClick={() => void confirmFullRunRerun(id, fullRunRequest)}
                                  size="small"
                                >
                                  复跑整条运行记录
                                </Button>
                              ) : null}
                            </Space>
                          </Space>
                        ) : null}
                        <Space size={[8, 8]} wrap>
                          <Tag>{snapshotPreviewText(rerunPreview.snapshot_preview, 'input')}</Tag>
                          <Tag>{snapshotPreviewText(rerunPreview.snapshot_preview, 'output')}</Tag>
                          <Tag>{snapshotPreviewText(rerunPreview.snapshot_preview, 'error')}</Tag>
                        </Space>
                      </Space>
                    )}
                    showIcon
                    type={rerunPreview.preflight_status === 'ready' ? 'success' : 'warning'}
                    title="节点复跑预检"
                  />
                ) : null}
                {rerunResult ? (
                  <Alert
                    description={`新运行记录：${rerunResult.id}，状态：${rerunResult.status}`}
                    showIcon
                    title="单节点复跑已创建"
                    type={rerunResult.status === 'succeeded' ? 'success' : 'info'}
                  />
                ) : null}
                {rerunPreviewError ? (
                  <Alert
                    description={rerunPreviewError}
                    showIcon
                    title="复跑预检失败"
                    type="error"
                  />
                ) : null}
                {rerunHint ? (
                  <Typography.Text type="secondary">{rerunHint}</Typography.Text>
                ) : null}
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
                  {formatTraceJsonValue({ input: node.input, output: node.output })}
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

export function RunSourceComparison({ run }: { run: ScheduledJobRunRecord }) {
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
