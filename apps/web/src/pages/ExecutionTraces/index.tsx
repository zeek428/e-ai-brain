import type { ProColumns } from '@ant-design/pro-components';
import { Button, Modal, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import { formatRemoteRowsError, normalizeRemoteRowsError, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  fetchExecutionTraceDetail,
  fetchExecutionTraces,
  type ExecutionTraceDetailRecord,
  type ExecutionTraceListItem,
  type ExecutionTraceListQuery,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { formatMutationError } from '../../utils/managementCrud';
import { ExecutionTraceDetailContent } from './components/ExecutionTraceDetailContent';

const sourceTypeOptions = [
  { label: '定时作业运行', value: 'scheduled_job_run' },
  { label: '定时作业阶段', value: 'scheduled_job_stage' },
  { label: '插件调用', value: 'plugin_invocation_log' },
  { label: 'AI 执行器 Runner', value: 'ai_executor_runner' },
  { label: 'AI 执行器任务', value: 'ai_executor_task' },
  { label: 'AI 助手运行', value: 'assistant_chat_run' },
  { label: 'AI 助手消息', value: 'assistant_message' },
  { label: '模型网关调用', value: 'model_gateway_log' },
  { label: '代码巡检报告', value: 'code_inspection_report' },
  { label: '结果写入记录', value: 'result_write_record' },
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
    sourceId: normalizeFilterText(query.filters.sourceId),
    sourceType: normalizeFilterText(query.filters.sourceType),
    status: normalizeFilterText(query.filters.status),
  };
}

function initialTraceListQuery(): ManagementListQuery {
  if (typeof window === 'undefined') {
    return {
      filters: {},
      page: 1,
      pageSize: 10,
      sortField: 'started_at',
      sortOrder: 'descend',
    };
  }
  const params = new URLSearchParams(window.location.search);
  const filters: Record<string, unknown> = {};
  const keyword = normalizeFilterText(params.get('keyword'));
  const sourceId = normalizeFilterText(params.get('source_id') ?? params.get('sourceId'));
  const sourceType = normalizeFilterText(params.get('source_type') ?? params.get('sourceType'));
  const status = normalizeFilterText(params.get('status'));
  const createdFrom = normalizeFilterText(params.get('created_from') ?? params.get('createdFrom'));
  const createdTo = normalizeFilterText(params.get('created_to') ?? params.get('createdTo'));
  if (keyword) {
    filters.keyword = keyword;
  }
  if (sourceId) {
    filters.sourceId = sourceId;
  }
  if (sourceType) {
    filters.sourceType = sourceType;
  }
  if (status) {
    filters.status = status;
  }
  if (createdFrom || createdTo) {
    filters.startedAt = [createdFrom ?? '', createdTo ?? ''];
  }
  return {
    filters,
    page: Number(params.get('page') ?? 1) || 1,
    pageSize: Number(params.get('page_size') ?? params.get('pageSize') ?? 10) || 10,
    sortField: params.get('sort_by') ?? params.get('sortField') ?? 'started_at',
    sortOrder: params.get('sort_order') === 'asc' ? 'ascend' : 'descend',
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

export default function ExecutionTracesPage() {
  const autoOpenedSourceIdRef = useRef<string | undefined>(undefined);
  const [detailState, setDetailState] = useState<{
    detail?: ExecutionTraceDetailRecord;
    loading: boolean;
    row?: ExecutionTraceListItem;
  }>();
  const [listQuery, setListQuery] = useState<ManagementListQuery>(() => initialTraceListQuery());
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

  const deepLinkSourceId = normalizeFilterText(listQuery.filters.sourceId);

  useEffect(() => {
    if (!deepLinkSourceId || listState.status !== 'ready' || listState.rows.length !== 1) {
      return;
    }
    if (autoOpenedSourceIdRef.current === deepLinkSourceId) {
      return;
    }
    autoOpenedSourceIdRef.current = deepLinkSourceId;
    void openDetail(listState.rows[0]);
  }, [deepLinkSourceId, listState.rows, listState.status, openDetail]);

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

  return (
    <>
      <ManagementListPage<ExecutionTraceListItem>
        breadcrumbGroup="运营治理"
        columns={columns}
        dataSource={listState.rows}
        filters={[
          { label: '关键词', name: 'keyword', type: 'text' },
          { label: '来源 ID', name: 'sourceId', type: 'text' },
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
          <ExecutionTraceDetailContent
            compactText={compactText}
            detail={detailState.detail}
            formatDuration={formatDuration}
            multilineText={multilineText}
            sourceTypeLabel={sourceTypeLabel}
            statusTag={statusTag}
          />
        ) : null}
      </Modal>
    </>
  );
}
