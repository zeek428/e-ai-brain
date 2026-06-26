import { CopyOutlined, LinkOutlined, RobotOutlined } from '@ant-design/icons';
import { Alert, Button, Descriptions, Space, Table, Tag, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useMemo, type ReactNode } from 'react';

import {
  type ExecutionTraceDetailRecord,
  type ExecutionTraceEdgeRecord,
  type ExecutionTraceNodeRecord,
} from '../../../services/aiBrain';
import { formatDisplayDateTime } from '../../../utils/dateTime';

const { Text } = Typography;

const ATTENTION_NODE_STATUSES = new Set(['cancelled', 'failed', 'pending', 'queued', 'running']);
const DIAGNOSTIC_NODE_LIMIT = 5;
const FAILED_NODE_STATUSES = new Set(['cancelled', 'failed']);

type ExecutionTraceDetailContentProps = {
  compactText: (value?: string | null) => ReactNode;
  detail: ExecutionTraceDetailRecord;
  formatDuration: (value?: number | null) => string;
  multilineText: (value?: string | null) => ReactNode;
  sourceTypeLabel: (value?: string | null) => string;
  statusTag: (status?: string | null) => ReactNode;
};

function RelatedIds({
  relatedIds,
  sourceTypeLabel,
}: {
  relatedIds?: Record<string, string[]>;
  sourceTypeLabel: (value?: string | null) => string;
}) {
  const entries = Object.entries(relatedIds ?? {}).filter(([, ids]) => ids.length > 0);
  if (entries.length === 0) {
    return <Text type="secondary">暂无关联对象。</Text>;
  }
  return (
    <Space orientation="vertical" size={8} style={{ width: '100%' }}>
      {entries.map(([sourceType, ids]) => (
        <Space key={sourceType} size={6} wrap>
          <Tag>{sourceTypeLabel(sourceType)}</Tag>
          {ids.slice(0, 8).map((id) => (
            <Tag key={id}>
              <Typography.Link href={executionTraceSourceHref(id, sourceType)}>{id}</Typography.Link>
            </Tag>
          ))}
          {ids.length > 8 ? <Text type="secondary">等 {ids.length} 个</Text> : null}
        </Space>
      ))}
    </Space>
  );
}

function jsonPreview(value?: Record<string, unknown>) {
  return <pre className="audit-json">{JSON.stringify(value ?? {}, null, 2)}</pre>;
}

function executionTraceSourceHref(sourceId?: string | null, sourceType?: string | null) {
  const params = new URLSearchParams();
  params.set('source_id', String(sourceId || ''));
  if (sourceType) {
    params.set('source_type', sourceType);
  }
  return `/governance/execution-traces?${params.toString()}`;
}

function assistantDiagnosticHref(
  detail: ExecutionTraceDetailRecord,
  node: ExecutionTraceNodeRecord,
  sourceTypeLabel: (value?: string | null) => string,
) {
  const params = new URLSearchParams();
  params.set('reference_type', node.source_type);
  params.set('reference_id', node.source_id);
  params.set(
    'prompt',
    [
      `请基于执行诊断链路「${detail.title}」继续排查。`,
      `重点分析节点：${sourceTypeLabel(node.source_type)} ${node.source_id}，当前状态 ${node.status}。`,
      node.error_message ? `错误信息：${node.error_message}` : '',
      node.summary ? `摘要：${node.summary}` : '',
      '请给出可能原因、需要查看的证据和修复步骤。',
    ].filter(Boolean).join('\n'),
  );
  return `/assistant?${params.toString()}`;
}

function attentionNodesForDetail(detail: ExecutionTraceDetailRecord) {
  return detail.diagnostic_nodes?.length
    ? detail.diagnostic_nodes
    : detail.nodes.filter((node) => ATTENTION_NODE_STATUSES.has(node.status));
}

function buildDiagnosticPackage(
  detail: ExecutionTraceDetailRecord,
  attentionNodes: ExecutionTraceNodeRecord[],
  sourceTypeLabel: (value?: string | null) => string,
) {
  return {
    duration_ms: detail.duration_ms,
    failed_node_count: detail.failed_node_count,
    node_count: detail.node_count,
    related_ids: detail.related_ids ?? {},
    root_id: detail.root_id,
    root_type: detail.root_type,
    root_type_label: sourceTypeLabel(detail.root_type),
    started_at: detail.started_at,
    status: detail.status,
    summary: detail.summary,
    title: detail.title,
    trace_id: detail.id,
    updated_at: detail.updated_at,
    diagnostic_nodes: attentionNodes.slice(0, DIAGNOSTIC_NODE_LIMIT).map((node) => ({
      duration_ms: node.duration_ms,
      error_code: node.error_code,
      error_message: node.error_message,
      label: node.label,
      source_id: node.source_id,
      source_type: node.source_type,
      source_type_label: sourceTypeLabel(node.source_type),
      status: node.status,
      summary: node.summary,
    })),
  };
}

function buildTraceDiagnosticPrompt(
  detail: ExecutionTraceDetailRecord,
  attentionNodes: ExecutionTraceNodeRecord[],
  sourceTypeLabel: (value?: string | null) => string,
) {
  const diagnosticPackage = buildDiagnosticPackage(detail, attentionNodes, sourceTypeLabel);
  const relatedSummary = Object.entries(detail.related_ids ?? {})
    .filter(([, ids]) => ids.length > 0)
    .slice(0, 8)
    .map(([sourceType, ids]) => `${sourceTypeLabel(sourceType)}: ${ids.slice(0, 5).join(', ')}`)
    .join('\n');
  const nodeLines = diagnosticPackage.diagnostic_nodes.length
    ? diagnosticPackage.diagnostic_nodes.map((node, index) => (
        [
          `${index + 1}. ${node.source_type_label} ${node.source_id}`,
          `状态: ${node.status}`,
          node.error_code ? `错误码: ${node.error_code}` : '',
          node.error_message ? `错误: ${node.error_message}` : '',
          node.summary ? `摘要: ${node.summary}` : '',
        ].filter(Boolean).join('；')
      )).join('\n')
    : '未发现失败、取消、运行中或排队节点。';
  return [
    `请基于执行诊断链路「${detail.title}」分析运行问题。`,
    `链路: ${detail.id}，根对象: ${sourceTypeLabel(detail.root_type)} ${detail.root_id}，状态: ${detail.status}。`,
    `节点统计: ${detail.node_count} 个节点，${detail.failed_node_count} 个失败，耗时 ${detail.duration_ms ?? '-'} ms。`,
    detail.summary ? `链路摘要: ${detail.summary}` : '',
    relatedSummary ? `关联对象:\n${relatedSummary}` : '',
    `重点诊断节点:\n${nodeLines}`,
    '请按“最可能原因 / 需要查看的证据 / 修复步骤 / 是否可重试”输出建议。',
  ].filter(Boolean).join('\n\n');
}

function assistantTraceDiagnosticHref(
  detail: ExecutionTraceDetailRecord,
  attentionNodes: ExecutionTraceNodeRecord[],
  sourceTypeLabel: (value?: string | null) => string,
) {
  const params = new URLSearchParams();
  params.set('reference_type', detail.root_type);
  params.set('reference_id', detail.root_id);
  params.set('prompt', buildTraceDiagnosticPrompt(detail, attentionNodes, sourceTypeLabel));
  return `/assistant?${params.toString()}`;
}

async function copyDiagnosticPackage(
  detail: ExecutionTraceDetailRecord,
  attentionNodes: ExecutionTraceNodeRecord[],
  sourceTypeLabel: (value?: string | null) => string,
) {
  const clipboard = navigator.clipboard;
  if (!clipboard?.writeText) {
    message.warning('当前浏览器不支持剪贴板写入');
    return;
  }
  await clipboard.writeText(JSON.stringify(buildDiagnosticPackage(detail, attentionNodes, sourceTypeLabel), null, 2));
  message.success('已复制执行诊断包');
}

function TraceDiagnostics({
  detail,
  multilineText,
  sourceTypeLabel,
  statusTag,
}: {
  detail: ExecutionTraceDetailRecord;
  multilineText: (value?: string | null) => ReactNode;
  sourceTypeLabel: (value?: string | null) => string;
  statusTag: (status?: string | null) => ReactNode;
}) {
  const attentionNodes = attentionNodesForDetail(detail);
  const failedNodes = attentionNodes.filter((node) => FAILED_NODE_STATUSES.has(node.status));
  if (attentionNodes.length === 0) {
    return (
      <Alert
        action={(
          <Space size={6} wrap>
            <Button
              href={assistantTraceDiagnosticHref(detail, attentionNodes, sourceTypeLabel)}
              icon={<RobotOutlined />}
              size="small"
            >
              问 AI 分析链路
            </Button>
            <Button
              icon={<CopyOutlined />}
              onClick={() => void copyDiagnosticPackage(detail, attentionNodes, sourceTypeLabel)}
              size="small"
            >
              复制诊断包
            </Button>
          </Space>
        )}
        title="诊断建议"
        description="当前链路没有失败或运行中节点，可继续查看关联对象、节点关系和脱敏元数据确认写入结果，也可以将整条链路诊断包带入 AI 助手继续分析。"
        showIcon
        type="success"
      />
    );
  }

  const alertType = failedNodes.length > 0 ? 'error' : 'warning';
  const alertSummary = failedNodes.length > 0
    ? `发现 ${failedNodes.length} 个失败节点`
    : `发现 ${attentionNodes.length} 个运行中或排队节点`;

  return (
    <Alert
      action={(
        <Space size={6} wrap>
          <Button
            href={assistantTraceDiagnosticHref(detail, attentionNodes, sourceTypeLabel)}
            icon={<RobotOutlined />}
            size="small"
            type="primary"
          >
            问 AI 分析链路
          </Button>
          <Button
            icon={<CopyOutlined />}
            onClick={() => void copyDiagnosticPackage(detail, attentionNodes, sourceTypeLabel)}
            size="small"
          >
            复制诊断包
          </Button>
        </Space>
      )}
      title="诊断建议"
      description={(
        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
          <Text>{alertSummary}，建议优先从下面的节点继续排查；诊断包只包含链路摘要、关联 ID 和脱敏节点信息。</Text>
          {attentionNodes.slice(0, 5).map((node) => (
            <Space
              align="start"
              key={node.id}
              size={8}
              style={{ justifyContent: 'space-between', width: '100%' }}
              wrap
            >
              <Space orientation="vertical" size={4} style={{ flex: 1, minWidth: 260 }}>
                <Space size={6} wrap>
                  <Tag>{sourceTypeLabel(node.source_type)}</Tag>
                  {statusTag(node.status)}
                  <Typography.Link href={executionTraceSourceHref(node.source_id, node.source_type)}>
                    {node.source_id}
                  </Typography.Link>
                </Space>
                {multilineText(node.error_message || node.summary || node.label)}
              </Space>
              <Space size={6} wrap>
                <Button
                  href={executionTraceSourceHref(node.source_id, node.source_type)}
                  icon={<LinkOutlined />}
                  size="small"
                >
                  打开诊断链接
                </Button>
                <Button
                  href={assistantDiagnosticHref(detail, node, sourceTypeLabel)}
                  icon={<RobotOutlined />}
                  size="small"
                  type="primary"
                >
                  问 AI
                </Button>
              </Space>
            </Space>
          ))}
          {attentionNodes.length > 5 ? (
            <Text type="secondary">还有 {attentionNodes.length - 5} 个节点可在下方节点表继续查看。</Text>
          ) : null}
        </Space>
      )}
      showIcon
      type={alertType}
    />
  );
}

export function ExecutionTraceDetailContent({
  compactText,
  detail,
  formatDuration,
  multilineText,
  sourceTypeLabel,
  statusTag,
}: ExecutionTraceDetailContentProps) {
  const nodeColumns = useMemo<ColumnsType<ExecutionTraceNodeRecord>>(
    () => [
      {
        dataIndex: 'label',
        title: '节点',
        width: 150,
        render: (_, row) => compactText(row.label),
      },
      {
        dataIndex: 'source_type',
        title: '来源',
        width: 150,
        render: (_, row) => sourceTypeLabel(row.source_type),
      },
      {
        dataIndex: 'source_id',
        title: '来源 ID',
        width: 220,
        render: (_, row) => (
          <Typography.Link
            ellipsis
            href={executionTraceSourceHref(row.source_id, row.source_type)}
            title={row.source_id}
            style={{ display: 'block', maxWidth: '100%' }}
          >
            {row.source_id}
          </Typography.Link>
        ),
      },
      {
        dataIndex: 'status',
        title: '状态',
        width: 110,
        render: (_, row) => statusTag(row.status),
      },
      {
        dataIndex: 'summary',
        title: '摘要 / 错误',
        width: 320,
        render: (_, row) => multilineText(row.error_message || row.summary),
      },
      {
        dataIndex: 'started_at',
        title: '开始时间',
        width: 160,
        render: (_, row) => formatDisplayDateTime(row.started_at),
      },
      {
        dataIndex: 'duration_ms',
        title: '耗时',
        width: 110,
        render: (_, row) => formatDuration(row.duration_ms),
      },
    ],
    [compactText, formatDuration, multilineText, sourceTypeLabel, statusTag],
  );

  const edgeColumns = useMemo<ColumnsType<ExecutionTraceEdgeRecord>>(
    () => [
      { dataIndex: 'from', title: '上游节点', width: 300, render: (_, row) => compactText(row.from) },
      { dataIndex: 'label', title: '关系', width: 120, render: (_, row) => row.label || '-' },
      { dataIndex: 'to', title: '下游节点', width: 300, render: (_, row) => compactText(row.to) },
    ],
    [compactText],
  );

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <Descriptions column={3} size="small">
        <Descriptions.Item label="链路标题" span={2}>
          {detail.title}
        </Descriptions.Item>
        <Descriptions.Item label="状态">{statusTag(detail.status)}</Descriptions.Item>
        <Descriptions.Item label="根类型">{sourceTypeLabel(detail.root_type)}</Descriptions.Item>
        <Descriptions.Item label="根 ID">{detail.root_id}</Descriptions.Item>
        <Descriptions.Item label="耗时">{formatDuration(detail.duration_ms)}</Descriptions.Item>
        <Descriptions.Item label="开始时间">
          {formatDisplayDateTime(detail.started_at)}
        </Descriptions.Item>
        <Descriptions.Item label="更新时间">
          {formatDisplayDateTime(detail.updated_at)}
        </Descriptions.Item>
        <Descriptions.Item label="节点统计">
          {detail.node_count} 个节点，{detail.failed_node_count} 个失败
        </Descriptions.Item>
        <Descriptions.Item label="摘要" span={3}>
          {multilineText(detail.summary)}
        </Descriptions.Item>
      </Descriptions>
      <section>
        <Text strong>关联对象</Text>
        <div style={{ marginTop: 8 }}>
          <RelatedIds relatedIds={detail.related_ids} sourceTypeLabel={sourceTypeLabel} />
        </div>
      </section>
      <TraceDiagnostics
        detail={detail}
        multilineText={multilineText}
        sourceTypeLabel={sourceTypeLabel}
        statusTag={statusTag}
      />
      <Table<ExecutionTraceNodeRecord>
        columns={nodeColumns}
        dataSource={detail.nodes}
        expandable={{
          expandedRowRender: (row) => jsonPreview(row.metadata),
          rowExpandable: (row) => Boolean(row.metadata && Object.keys(row.metadata).length),
        }}
        pagination={false}
        rowKey="id"
        scroll={{ x: 1320 }}
        size="small"
        tableLayout="fixed"
        title={() => '执行节点'}
      />
      <Table<ExecutionTraceEdgeRecord>
        columns={edgeColumns}
        dataSource={detail.edges}
        pagination={false}
        rowKey={(row) => `${row.from}-${row.label}-${row.to}`}
        scroll={{ x: 760 }}
        size="small"
        tableLayout="fixed"
        title={() => '节点关系'}
      />
    </Space>
  );
}
