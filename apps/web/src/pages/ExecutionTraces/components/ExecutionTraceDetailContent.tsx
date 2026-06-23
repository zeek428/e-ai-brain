import { Descriptions, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useMemo, type ReactNode } from 'react';

import {
  type ExecutionTraceDetailRecord,
  type ExecutionTraceEdgeRecord,
  type ExecutionTraceNodeRecord,
} from '../../../services/aiBrain';
import { formatDisplayDateTime } from '../../../utils/dateTime';

const { Text } = Typography;

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
            <Tag key={id}>{id}</Tag>
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
        render: (_, row) => compactText(row.source_id),
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
