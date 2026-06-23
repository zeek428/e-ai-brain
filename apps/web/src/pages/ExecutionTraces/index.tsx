import type { ProColumns } from '@ant-design/pro-components';
import { Button, Descriptions, Modal, Space, Table, Tag, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import { formatRemoteRowsError, normalizeRemoteRowsError, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  fetchExecutionTraceDetail,
  fetchExecutionTraces,
  type ExecutionTraceDetailRecord,
  type ExecutionTraceEdgeRecord,
  type ExecutionTraceListItem,
  type ExecutionTraceListQuery,
  type ExecutionTraceNodeRecord,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { formatMutationError } from '../../utils/managementCrud';

const { Text } = Typography;

const sourceTypeOptions = [
  { label: '定时作业运行', value: 'scheduled_job_run' },
  { label: '插件调用', value: 'plugin_invocation_log' },
  { label: 'AI 执行器任务', value: 'ai_executor_task' },
  { label: '模型网关调用', value: 'model_gateway_log' },
  { label: '代码巡检报告', value: 'code_inspection_report' },
  { label: '审计事件', value: 'audit_event' },
];

const sourceTypeLabels = new Map(sourceTypeOptions.map((item) => [item.value, item.label]));

const statusOptions = [
  { label: '成功', value: 'succeeded' },
  { label: '失败', value: 'failed' },
  { label: '运行中', value: 'running' },
  { label: '排队中', value: 'queued' },
  { label: '部分完成', value: 'partial' },
  { label: '已跳过', value: 'skipped' },
  { label: '已取消', value: 'cancelled' },
  { label: '未知', value: 'unknown' },
];

const statusLabels = new Map(statusOptions.map((item) => [item.value, item.label]));

const statusColors = new Map([
  ['cancelled', 'default'],
  ['failed', 'red'],
  ['partial', 'orange'],
  ['queued', 'blue'],
  ['running', 'processing'],
  ['skipped', 'default'],
  ['succeeded', 'green'],
  ['unknown', 'default'],
]);

const traceSortFieldMap: Record<string, string> = {
  duration_ms: 'duration_ms',
  failed_node_count: 'failed_node_count',
  id: 'id',
  node_count: 'node_count',
  root_type: 'root_type',
  started_at: 'started_at',
  status: 'status',
  updated_at: 'updated_at',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function normalizeDateRange(value: unknown) {
  if (!Array.isArray(value)) {
    return {};
  }
  return {
    createdFrom: normalizeFilterText(value[0]),
    createdTo: normalizeFilterText(value[1]),
  };
}

function buildTraceQuery(query: ManagementListQuery): ExecutionTraceListQuery {
  const dateRange = normalizeDateRange(query.filters.startedAt);
  return {
    ...dateRange,
    keyword: normalizeFilterText(query.filters.keyword),
    page: query.page,
    pageSize: query.pageSize,
    sortField: query.sortField
      ? traceSortFieldMap[query.sortField] ?? query.sortField
      : undefined,
    sortOrder: query.sortOrder,
    sourceType: normalizeFilterText(query.filters.sourceType),
    status: normalizeFilterText(query.filters.status),
  };
}

function sourceTypeLabel(value?: string | null) {
  return sourceTypeLabels.get(String(value ?? '')) ?? value ?? '-';
}

function statusTag(status?: string | null) {
  const value = String(status ?? 'unknown');
  return <StatusTag color={statusColors.get(value) ?? 'default'} label={statusLabels.get(value) ?? value} />;
}

function compactText(value?: string | null) {
  const text = value || '-';
  return (
    <Typography.Text ellipsis={{ tooltip: text }} style={{ display: 'block', maxWidth: '100%' }}>
      {text}
    </Typography.Text>
  );
}

function multilineText(value?: string | null) {
  const text = value || '-';
  return (
    <Typography.Text style={{ display: 'block', whiteSpace: 'normal', wordBreak: 'break-word' }}>
      {text}
    </Typography.Text>
  );
}

function formatDuration(value?: number | null) {
  if (value === undefined || value === null) {
    return '-';
  }
  if (value < 1000) {
    return `${value} ms`;
  }
  return `${(value / 1000).toFixed(2)} s`;
}

function RelatedIds({ relatedIds }: { relatedIds?: Record<string, string[]> }) {
  const entries = Object.entries(relatedIds ?? {}).filter(([, ids]) => ids.length > 0);
  if (entries.length === 0) {
    return <Text type="secondary">暂无关联对象。</Text>;
  }
  return (
    <Space direction="vertical" size={8} style={{ width: '100%' }}>
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

export default function ExecutionTracesPage() {
  const [detailState, setDetailState] = useState<{
    detail?: ExecutionTraceDetailRecord;
    loading: boolean;
    row?: ExecutionTraceListItem;
  }>();
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'started_at',
    sortOrder: 'descend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    rows: ExecutionTraceListItem[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });

  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchExecutionTraces(buildTraceQuery(listQuery));
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        rows: result.rows,
        status: 'ready',
        total: result.total,
      });
    } catch (loadError: unknown) {
      setListState((current) => ({
        ...current,
        error: normalizeRemoteRowsError(loadError),
        rows: [],
        status: 'error',
      }));
    }
  }, [listQuery]);

  useEffect(() => {
    let isCurrent = true;
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchExecutionTraces(buildTraceQuery(listQuery))
      .then((result) => {
        if (isCurrent) {
          setListState({
            page: result.page,
            pageSize: result.pageSize,
            rows: result.rows,
            status: 'ready',
            total: result.total,
          });
        }
      })
      .catch((loadError: unknown) => {
        if (isCurrent) {
          setListState((current) => ({
            ...current,
            error: normalizeRemoteRowsError(loadError),
            rows: [],
            status: 'error',
          }));
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [listQuery]);

  const openDetail = useCallback(async (row: ExecutionTraceListItem) => {
    setDetailState({ loading: true, row });
    try {
      const detail = await fetchExecutionTraceDetail(row.id);
      setDetailState({ detail, loading: false, row });
    } catch (detailError) {
      setDetailState(undefined);
      message.error(formatMutationError(detailError));
    }
  }, []);

  const columns = useMemo<ProColumns<ExecutionTraceListItem>[]>(
    () => [
      {
        dataIndex: 'title',
        sorter: true,
        title: '链路标题',
        width: 240,
        render: (_, row) => compactText(row.title),
      },
      {
        dataIndex: 'root_type',
        sorter: true,
        title: '根类型',
        width: 140,
        render: (_, row) => sourceTypeLabel(row.root_type),
      },
      {
        dataIndex: 'status',
        sorter: true,
        title: '状态',
        width: 120,
        render: (_, row) => statusTag(row.status),
      },
      {
        dataIndex: 'summary',
        title: '摘要',
        width: 300,
        render: (_, row) => compactText(row.summary),
      },
      {
        dataIndex: 'node_count',
        sorter: true,
        title: '节点',
        width: 100,
      },
      {
        dataIndex: 'failed_node_count',
        sorter: true,
        title: '失败节点',
        width: 110,
      },
      {
        dataIndex: 'duration_ms',
        sorter: true,
        title: '耗时',
        width: 110,
        render: (_, row) => formatDuration(row.duration_ms),
      },
      {
        dataIndex: 'started_at',
        sorter: true,
        title: '开始时间',
        width: 160,
        render: (_, row) => formatDisplayDateTime(row.started_at),
      },
      {
        dataIndex: 'updated_at',
        sorter: true,
        title: '更新时间',
        width: 160,
        render: (_, row) => formatDisplayDateTime(row.updated_at),
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        width: 120,
        render: (_, row) => (
          <Button onClick={() => void openDetail(row)} type="link">
            详情
          </Button>
        ),
      },
    ],
    [openDetail],
  );

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
    [],
  );

  const edgeColumns = useMemo<ColumnsType<ExecutionTraceEdgeRecord>>(
    () => [
      { dataIndex: 'from', title: '上游节点', width: 300, render: (_, row) => compactText(row.from) },
      { dataIndex: 'label', title: '关系', width: 120, render: (_, row) => row.label || '-' },
      { dataIndex: 'to', title: '下游节点', width: 300, render: (_, row) => compactText(row.to) },
    ],
    [],
  );

  return (
    <>
      <ManagementListPage<ExecutionTraceListItem>
        breadcrumbGroup="运营治理"
        columns={columns}
        dataSource={listState.rows}
        filters={[
          { label: '关键词', name: 'keyword', type: 'text' },
          {
            label: '根类型',
            name: 'sourceType',
            options: sourceTypeOptions,
            type: 'select',
          },
          {
            label: '状态',
            name: 'status',
            options: statusOptions,
            type: 'select',
          },
          { label: '开始时间', name: 'startedAt', type: 'dateRange' },
        ]}
        loading={listState.status === 'loading'}
        notice={formatRemoteRowsError(listState.error)}
        onReload={() => void reload()}
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          total: listState.total,
        }}
        rowKey="id"
        tableTitle="执行诊断列表"
        title="执行诊断"
      />
      <Modal
        footer={null}
        loading={detailState?.loading}
        onCancel={() => setDetailState(undefined)}
        open={Boolean(detailState)}
        title="执行诊断详情"
        width={1040}
      >
        {detailState?.detail ? (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions column={3} size="small">
              <Descriptions.Item label="链路标题" span={2}>
                {detailState.detail.title}
              </Descriptions.Item>
              <Descriptions.Item label="状态">{statusTag(detailState.detail.status)}</Descriptions.Item>
              <Descriptions.Item label="根类型">{sourceTypeLabel(detailState.detail.root_type)}</Descriptions.Item>
              <Descriptions.Item label="根 ID">{detailState.detail.root_id}</Descriptions.Item>
              <Descriptions.Item label="耗时">{formatDuration(detailState.detail.duration_ms)}</Descriptions.Item>
              <Descriptions.Item label="开始时间">
                {formatDisplayDateTime(detailState.detail.started_at)}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {formatDisplayDateTime(detailState.detail.updated_at)}
              </Descriptions.Item>
              <Descriptions.Item label="节点统计">
                {detailState.detail.node_count} 个节点，{detailState.detail.failed_node_count} 个失败
              </Descriptions.Item>
              <Descriptions.Item label="摘要" span={3}>
                {multilineText(detailState.detail.summary)}
              </Descriptions.Item>
            </Descriptions>
            <section>
              <Text strong>关联对象</Text>
              <div style={{ marginTop: 8 }}>
                <RelatedIds relatedIds={detailState.detail.related_ids} />
              </div>
            </section>
            <Table<ExecutionTraceNodeRecord>
              columns={nodeColumns}
              dataSource={detailState.detail.nodes}
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
              dataSource={detailState.detail.edges}
              pagination={false}
              rowKey={(row) => `${row.from}-${row.label}-${row.to}`}
              scroll={{ x: 760 }}
              size="small"
              tableLayout="fixed"
              title={() => '节点关系'}
            />
          </Space>
        ) : null}
      </Modal>
    </>
  );
}
