import { Descriptions, Space, Tag, Typography } from 'antd';

import { type ScheduledJobRunRecord } from '../../../services/aiBrain';
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

export function RunTraceDag({ run }: { run: ScheduledJobRunRecord }) {
  const rawTraceGraph = run.result_summary?.trace_graph;
  const traceGraph = isTraceRecord(rawTraceGraph) ? rawTraceGraph : undefined;
  const nodes = Array.isArray(traceGraph?.nodes)
    ? traceGraph.nodes.filter(isTraceRecord)
    : [];
  const edges = Array.isArray(traceGraph?.edges)
    ? traceGraph.edges.filter(isTraceRecord)
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
