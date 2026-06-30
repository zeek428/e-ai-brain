import type { ProColumns } from '@ant-design/pro-components';
import { Button, Popconfirm, Space, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  ManagementListPage,
  type ManagementListQuery,
} from '../../components/ManagementListPage';
import { ExecutionTraceLink } from '../../components/ExecutionTraceLink';
import { formatRemoteRowsError, normalizeRemoteRowsError, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  cancelAssistantActionDraft,
  confirmAssistantActionDraft,
  fetchAssistantActionDraftWorkbench,
  markAssistantActionDraftViewed,
  retryAssistantActionDraft,
  type AssistantActionDraftRecord,
  type AssistantActionDraftWorkbenchItem,
  type AssistantActionDraftWorkbenchQuery,
  type AssistantActionDraftWorkbenchSummary,
  type RemoteListPerformance,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { formatMutationError } from '../../utils/managementCrud';
import { AssistantDraftDetailModal } from './components/AssistantDraftDetailModal';
import { AssistantDraftGovernanceQueue } from './components/AssistantDraftGovernanceQueue';
import { AssistantDraftSummaryStrip } from './components/AssistantDraftSummaryStrip';
import {
  actionLabel,
  actionOptions,
  assistantDraftEditHref,
  compactText,
  operationText,
  permissionTag,
  riskTag,
  statusOptions,
  statusTag,
  validationOptions,
  validationTag,
} from './components/assistantDraftWorkbenchPresentation';

const { Text } = Typography;

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
    performance?: RemoteListPerformance;
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
      performance: result.performance,
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
            performance: result.performance,
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

  const retryDraft = useCallback(async (row: AssistantActionDraftWorkbenchItem) => {
    setMutatingId(row.id);
    try {
      await retryAssistantActionDraft(row.id, '从草案任务台重新打开失败草案');
      message.success('草案已重新打开');
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
        dataIndex: 'impact_resource_type',
        title: '影响对象',
        width: 180,
        render: (_, row) => (
          <Space orientation="vertical" size={0} style={{ width: '100%' }}>
            <Text>{operationText(row.impact_operation)} · {row.impact_resource_type ?? '-'}</Text>
            <Text type="secondary">{row.impact_changed_field_count ?? 0} 项差异</Text>
          </Space>
        ),
      },
      {
        dataIndex: 'permission_status',
        title: '权限',
        width: 120,
        render: (_, row) => (
          <Space size={4}>
            {permissionTag(row.permission_status)}
            {row.permission_issue_count ? <Text type="secondary">{row.permission_issue_count}</Text> : null}
          </Space>
        ),
      },
      {
        dataIndex: 'audit_event_count',
        title: '审计/重试',
        width: 150,
        render: (_, row) => (
          <Space orientation="vertical" size={0} style={{ width: '100%' }}>
            <Text>{row.audit_event_count ?? 0} 条审计</Text>
            <Text type="secondary">
              {row.failure_count ?? 0} 失败 / {row.retry_count ?? 0} 重试
            </Text>
          </Space>
        ),
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
            {row.status === 'failed' ? (
              <Popconfirm
                okText="重新打开"
                onConfirm={() => void retryDraft(row)}
                title="将失败草案重新打开为待确认状态，重新确认前不会写入业务配置。是否继续？"
              >
                <Button loading={mutatingId === row.id} type="link">
                  重新打开
                </Button>
              </Popconfirm>
            ) : null}
          </Space>
        ),
      },
    ],
    [cancelDraft, confirmDraft, mutatingId, openDetail, retryDraft],
  );

  return (
    <>
      <ManagementListPage<AssistantActionDraftWorkbenchItem>
        beforeTable={(
          <>
            <AssistantDraftSummaryStrip summary={listState.summary} />
            <AssistantDraftGovernanceQueue rows={listState.rows} summary={listState.summary} />
          </>
        )}
        breadcrumbGroup="AI 助手"
        columns={columns}
        dataSource={listState.rows}
        viewStorageKey="assistant.drafts"
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
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="id"
        tableTitle="草案任务列表"
        title="草案任务台"
      />
      <AssistantDraftDetailModal
        detail={detail}
        loading={detailLoading}
        onClose={() => setDetail(undefined)}
      />
    </>
  );
}
