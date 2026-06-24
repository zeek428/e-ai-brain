import type { ProColumns } from '@ant-design/pro-components';
import { Button, Descriptions, Modal, Popconfirm, Space, Table, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  ManagementListPage,
  StatusTag,
  type ManagementListQuery,
} from '../../components/ManagementListPage';
import { ExecutionTraceLink } from '../../components/ExecutionTraceLink';
import { formatRemoteRowsError, normalizeRemoteRowsError, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  cancelAssistantActionDraft,
  confirmAssistantActionDraft,
  fetchAssistantActionDraftWorkbench,
  markAssistantActionDraftViewed,
  type AssistantActionDraftPreviewIssue,
  type AssistantActionDraftRecord,
  type AssistantActionDraftWorkbenchItem,
  type AssistantActionDraftWorkbenchQuery,
  type AssistantActionDraftWorkbenchSummary,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { formatMutationError } from '../../utils/managementCrud';

const { Text } = Typography;

const actionOptions = [
  { label: '定时作业草案', value: 'create_scheduled_job' },
  { label: '插件连接草案', value: 'create_plugin_connection' },
  { label: '插件动作草案', value: 'create_plugin_action' },
  { label: 'AI Skill 草案', value: 'create_ai_skill' },
  { label: 'AI角色草案', value: 'create_ai_agent' },
  { label: '研发任务草案', value: 'create_rd_task' },
  { label: '分析草案', value: 'create_analysis_draft' },
];

const actionLabels = new Map(actionOptions.map((item) => [item.value, item.label]));

const statusOptions = [
  { label: '待确认', value: 'pending' },
  { label: '已采纳', value: 'confirmed' },
  { label: '已取消', value: 'cancelled' },
  { label: '已过期', value: 'expired' },
  { label: '失败', value: 'failed' },
];

const statusLabels = new Map(statusOptions.map((item) => [item.value, item.label]));

const statusColors = new Map([
  ['cancelled', 'default'],
  ['confirmed', 'green'],
  ['expired', 'default'],
  ['failed', 'red'],
  ['pending', 'blue'],
]);

const validationOptions = [
  { label: '通过', value: 'passed' },
  { label: '阻塞', value: 'blocked' },
  { label: '警告', value: 'warning' },
  { label: '未知', value: 'unknown' },
];

const validationLabels = new Map(validationOptions.map((item) => [item.value, item.label]));

const validationColors = new Map([
  ['blocked', 'red'],
  ['passed', 'green'],
  ['unknown', 'default'],
  ['warning', 'orange'],
]);

const riskColors = new Map([
  ['critical', 'red'],
  ['high', 'volcano'],
  ['low', 'green'],
  ['medium', 'gold'],
]);

const sortFieldMap: Record<string, string> = {
  action: 'action',
  created_at: 'created_at',
  modified_field_count: 'modified_field_count',
  result_status: 'result_status',
  risk_level: 'risk_level',
  status: 'status',
  title: 'title',
  updated_at: 'updated_at',
  validation_issue_count: 'validation_issue_count',
  validation_status: 'validation_status',
  view_count: 'view_count',
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

function buildWorkbenchQuery(query: ManagementListQuery): AssistantActionDraftWorkbenchQuery {
  const dateRange = normalizeDateRange(query.filters.createdAt);
  return {
    ...dateRange,
    action: normalizeFilterText(query.filters.action),
    keyword: normalizeFilterText(query.filters.keyword),
    page: query.page,
    pageSize: query.pageSize,
    sortField: query.sortField
      ? sortFieldMap[query.sortField] ?? query.sortField
      : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
    validationStatus: normalizeFilterText(query.filters.validationStatus),
  };
}

function actionLabel(value?: string | null) {
  return actionLabels.get(String(value ?? '')) ?? value ?? '-';
}

function statusTag(status?: string | null) {
  const value = String(status ?? 'unknown');
  return <StatusTag color={statusColors.get(value) ?? 'default'} label={statusLabels.get(value) ?? value} />;
}

function validationTag(status?: string | null) {
  const value = String(status ?? 'unknown');
  return <StatusTag color={validationColors.get(value) ?? 'default'} label={validationLabels.get(value) ?? value} />;
}

function riskTag(risk?: string | null) {
  const value = String(risk ?? '-');
  if (value === '-') {
    return '-';
  }
  return <StatusTag color={riskColors.get(value) ?? 'default'} label={value} />;
}

function compactText(value?: string | null) {
  const text = value || '-';
  return (
    <Typography.Text ellipsis={{ tooltip: text }} style={{ display: 'block', maxWidth: '100%' }}>
      {text}
    </Typography.Text>
  );
}

function percent(value?: number) {
  return `${Math.round((value ?? 0) * 1000) / 10}%`;
}

function assistantDraftEditHref(draftId?: string | null) {
  const normalizedDraftId = String(draftId ?? '').trim();
  if (!normalizedDraftId) {
    return undefined;
  }
  const params = new URLSearchParams();
  params.set('draft_id', normalizedDraftId);
  return `/assistant?${params.toString()}`;
}

function SummaryStrip({ summary }: { summary?: AssistantActionDraftWorkbenchSummary }) {
  const statusCounts = summary?.status_counts ?? {};
  const metrics = [
    { label: '待确认草案', value: statusCounts.pending ?? 0 },
    { label: '失败草案', value: statusCounts.failed ?? 0 },
    { label: '已采纳草案', value: statusCounts.confirmed ?? 0 },
    { label: '采纳率', value: percent(summary?.adoption_rate) },
    { label: '处理率', value: percent(summary?.resolution_rate) },
    { label: '用户修改率', value: percent(summary?.user_modified_rate) },
  ];
  return (
    <div className="assistant-draft-summary-strip">
      {metrics.map((metric) => (
        <div className="assistant-draft-summary-item" key={metric.label}>
          <Text type="secondary">{metric.label}</Text>
          <strong>{metric.value}</strong>
        </div>
      ))}
    </div>
  );
}

function jsonPreview(value?: Record<string, unknown>) {
  return <pre className="audit-json">{JSON.stringify(value ?? {}, null, 2)}</pre>;
}

export default function AssistantDraftsPage() {
  const [detail, setDetail] = useState<AssistantActionDraftRecord>();
  const [detailLoading, setDetailLoading] = useState(false);
  const [mutatingId, setMutatingId] = useState<string>();
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'updated_at',
    sortOrder: 'descend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    rows: AssistantActionDraftWorkbenchItem[];
    status: 'error' | 'loading' | 'ready';
    summary?: AssistantActionDraftWorkbenchSummary;
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });

  const loadRows = useCallback(async (query: ManagementListQuery) => {
    const result = await fetchAssistantActionDraftWorkbench(buildWorkbenchQuery(query));
    setListState({
      page: result.page,
      pageSize: result.pageSize,
      rows: result.rows,
      status: 'ready',
      summary: result.summary,
      total: result.total,
    });
  }, []);

  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      await loadRows(listQuery);
    } catch (loadError: unknown) {
      setListState((current) => ({
        ...current,
        error: normalizeRemoteRowsError(loadError),
        rows: [],
        status: 'error',
      }));
    }
  }, [listQuery, loadRows]);

  useEffect(() => {
    let isCurrent = true;
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchAssistantActionDraftWorkbench(buildWorkbenchQuery(listQuery))
      .then((result) => {
        if (isCurrent) {
          setListState({
            page: result.page,
            pageSize: result.pageSize,
            rows: result.rows,
            status: 'ready',
            summary: result.summary,
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

  const openDetail = useCallback(async (row: AssistantActionDraftWorkbenchItem) => {
    setDetailLoading(true);
    try {
      setDetail(await markAssistantActionDraftViewed(row.id, 'detail_modal'));
    } catch (error) {
      message.error(formatMutationError(error));
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const confirmDraft = useCallback(async (row: AssistantActionDraftWorkbenchItem) => {
    setMutatingId(row.id);
    try {
      await confirmAssistantActionDraft(row.id);
      message.success('草案已确认');
      await reload();
    } catch (error) {
      message.error(formatMutationError(error));
    } finally {
      setMutatingId(undefined);
    }
  }, [reload]);

  const cancelDraft = useCallback(async (row: AssistantActionDraftWorkbenchItem) => {
    setMutatingId(row.id);
    try {
      await cancelAssistantActionDraft(row.id, '从草案任务台取消');
      message.success('草案已取消');
      await reload();
    } catch (error) {
      message.error(formatMutationError(error));
    } finally {
      setMutatingId(undefined);
    }
  }, [reload]);

  const columns = useMemo<ProColumns<AssistantActionDraftWorkbenchItem>[]>(
    () => [
      {
        dataIndex: 'title',
        sorter: true,
        title: '草案标题',
        width: 240,
        render: (_, row) => compactText(row.title),
      },
      {
        dataIndex: 'action',
        sorter: true,
        title: '草案类型',
        width: 140,
        render: (_, row) => actionLabel(row.action),
      },
      {
        dataIndex: 'status',
        sorter: true,
        title: '状态',
        width: 110,
        render: (_, row) => statusTag(row.status),
      },
      {
        dataIndex: 'validation_status',
        sorter: true,
        title: '校验',
        width: 110,
        render: (_, row) => (
          <Space size={4}>
            {validationTag(row.validation_status)}
            {row.validation_issue_count ? <Text type="secondary">{row.validation_issue_count}</Text> : null}
          </Space>
        ),
      },
      {
        dataIndex: 'risk_level',
        sorter: true,
        title: '风险',
        width: 100,
        render: (_, row) => riskTag(row.risk_level),
      },
      {
        dataIndex: 'result_status',
        sorter: true,
        title: '结果',
        width: 140,
        render: (_, row) => row.result_status ? `${row.result_status} · ${row.result_type ?? '-'}` : '-',
      },
      {
        dataIndex: 'source_message_id',
        title: '来源链路',
        width: 120,
        render: (_, row) => (
          <ExecutionTraceLink asButton sourceId={row.source_message_id} sourceType="assistant_message">
            来源链路
          </ExecutionTraceLink>
        ),
      },
      {
        dataIndex: 'view_count',
        sorter: true,
        title: '查看',
        width: 90,
      },
      {
        dataIndex: 'modified_field_count',
        sorter: true,
        title: '修改',
        width: 90,
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
        width: 260,
        render: (_, row) => (
          <Space size={4}>
            <Button onClick={() => void openDetail(row)} type="link">
              详情
            </Button>
            <Button href={assistantDraftEditHref(row.id)} type="link">
              继续编辑
            </Button>
            {row.status === 'pending' ? (
              <Popconfirm
                okText="确认"
                onConfirm={() => void confirmDraft(row)}
                title="确认后会写入对应业务配置，是否继续？"
              >
                <Button loading={mutatingId === row.id} type="link">
                  确认
                </Button>
              </Popconfirm>
            ) : null}
            {row.status === 'pending' ? (
              <Popconfirm
                okText="取消"
                onConfirm={() => void cancelDraft(row)}
                title="取消后不能再确认该草案，是否继续？"
              >
                <Button danger loading={mutatingId === row.id} type="link">
                  取消
                </Button>
              </Popconfirm>
            ) : null}
          </Space>
        ),
      },
    ],
    [cancelDraft, confirmDraft, mutatingId, openDetail],
  );

  const issueColumns = useMemo<ColumnsType<AssistantActionDraftPreviewIssue>>(
    () => [
      { dataIndex: 'severity', title: '级别', width: 90 },
      { dataIndex: 'field', title: '字段', width: 160 },
      { dataIndex: 'message', title: '说明', render: (_, row) => compactText(row.message) },
    ],
    [],
  );

  const detailIssues = detail?.preview?.validation?.issues ?? [];

  return (
    <>
      <ManagementListPage<AssistantActionDraftWorkbenchItem>
        beforeTable={<SummaryStrip summary={listState.summary} />}
        breadcrumbGroup="AI 助手"
        columns={columns}
        dataSource={listState.rows}
        filters={[
          { label: '关键词', name: 'keyword', type: 'text' },
          { label: '草案类型', name: 'action', options: actionOptions, type: 'select' },
          { label: '状态', name: 'status', options: statusOptions, type: 'select' },
          { label: '校验', name: 'validationStatus', options: validationOptions, type: 'select' },
          { label: '创建时间', name: 'createdAt', type: 'dateRange' },
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
        tableTitle="草案任务列表"
        title="草案任务台"
      />
      <Modal
        footer={null}
        loading={detailLoading}
        onCancel={() => setDetail(undefined)}
        open={Boolean(detail)}
        title="草案详情"
        width={1040}
      >
        {detail ? (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Space wrap>
              <Button href={assistantDraftEditHref(detail.id)} type="primary">
                继续编辑
              </Button>
              <ExecutionTraceLink asButton sourceId={detail.source_message_id} sourceType="assistant_message">
                来源链路
              </ExecutionTraceLink>
            </Space>
            <Descriptions column={3} size="small">
              <Descriptions.Item label="草案标题" span={2}>{detail.title}</Descriptions.Item>
              <Descriptions.Item label="状态">{statusTag(detail.status)}</Descriptions.Item>
              <Descriptions.Item label="草案类型">{actionLabel(detail.action)}</Descriptions.Item>
              <Descriptions.Item label="风险">{riskTag(detail.risk_level)}</Descriptions.Item>
              <Descriptions.Item label="校验">{validationTag(detail.preview?.validation?.status)}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{formatDisplayDateTime(detail.created_at)}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{formatDisplayDateTime(detail.updated_at)}</Descriptions.Item>
              <Descriptions.Item label="结果">
                {detail.result_run?.status ? `${detail.result_run.status} · ${detail.result_run.result_type ?? '-'}` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="来源消息">{detail.source_message_id ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="来源链路">
                <ExecutionTraceLink asButton sourceId={detail.source_message_id} sourceType="assistant_message">
                  来源链路
                </ExecutionTraceLink>
              </Descriptions.Item>
            </Descriptions>
            <Table<AssistantActionDraftPreviewIssue>
              columns={issueColumns}
              dataSource={detailIssues}
              pagination={false}
              rowKey={(row) => `${row.field}-${row.severity}-${row.message}`}
              scroll={{ x: 720 }}
              size="small"
              tableLayout="fixed"
              title={() => '校验问题'}
            />
            <section>
              <Text strong>草案 Payload</Text>
              <div style={{ marginTop: 8 }}>{jsonPreview(detail.payload)}</div>
            </section>
          </Space>
        ) : null}
      </Modal>
    </>
  );
}
