import type { ProColumns } from '@ant-design/pro-components';
import { Button, Descriptions, Modal, Space, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import type { AuditRecord } from '../../data/management';
import { formatRemoteRowsError, normalizeRemoteRowsError, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  fetchLifecycleContext,
  fetchManagementAuditList,
  type AuditListQuery,
  type LifecycleContextRecord,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';

const { Text } = Typography;

function resolveTraceParams(row: AuditRecord) {
  const traceableSubjectTypes = new Set([
    'ai_task',
    'bug',
    'code_review_report',
    'gitlab_daily_code_metric',
    'gitlab_mr_snapshot',
    'human_review',
    'iteration_plan_suggestion',
    'jenkins_release',
    'knowledge_deposit',
    'mock_issue',
    'online_log_metric',
    'requirement',
    'user_feedback',
    'user_usage_metric',
  ]);
  if (row.subjectType && row.subjectId && traceableSubjectTypes.has(row.subjectType)) {
    return { subjectId: row.subjectId, subjectType: row.subjectType };
  }
  if (row.subjectType === 'product' && row.subjectId) {
    return { productId: row.subjectId };
  }
  if (row.aiTaskId) {
    return { subjectId: row.aiTaskId, subjectType: 'ai_task' };
  }
  return undefined;
}

function RelationList({ items }: { items: LifecycleContextRecord['downstream'] }) {
  if (items.length === 0) {
    return <Text type="secondary">暂无链路数据。</Text>;
  }
  return (
    <Space orientation="vertical" size={8} style={{ width: '100%' }}>
      {items.map((item) => (
        <div className="audit-trace-item" key={`${item.relationType}-${item.subjectType}-${item.subjectId}`}>
          <Space size={8} wrap>
            <Tag>{item.relationType}</Tag>
            <Text type="secondary">
              {item.subjectType}: {item.subjectId}
            </Text>
          </Space>
          <Text>{item.summary}</Text>
        </div>
      ))}
    </Space>
  );
}

const auditSortFieldMap: Record<string, string> = {
  actor: 'actor_id',
  eventType: 'event_type',
  id: 'id',
  result: 'result',
  subject: 'subject_type',
  timestamp: 'created_at',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildAuditListQuery(query: ManagementListQuery): AuditListQuery {
  return {
    actor: normalizeFilterText(query.filters.actor),
    eventType: normalizeFilterText(query.filters.eventType),
    page: query.page,
    pageSize: query.pageSize,
    result: normalizeFilterText(query.filters.result),
    sortField: query.sortField ? auditSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    subject: normalizeFilterText(query.filters.subject),
  };
}

export default function AuditPage() {
  const [selectedAudit, setSelectedAudit] = useState<AuditRecord>();
  const [traceDialog, setTraceDialog] = useState<{
    context?: LifecycleContextRecord;
    loading: boolean;
    row: AuditRecord;
  }>();
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'timestamp',
    sortOrder: 'descend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    rows: AuditRecord[];
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
      const result = await fetchManagementAuditList(buildAuditListQuery(listQuery));
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
    fetchManagementAuditList(buildAuditListQuery(listQuery))
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

  const openTraceDialog = useCallback(async (row: AuditRecord) => {
    const params = resolveTraceParams(row);
    if (!params) {
      message.warning('当前审计事件没有可追踪的需求、任务或产品主体。');
      return;
    }
    setTraceDialog({ loading: true, row });
    try {
      const context = await fetchLifecycleContext(params);
      setTraceDialog({ context, loading: false, row });
    } catch (traceError) {
      setTraceDialog(undefined);
      message.error(formatMutationError(traceError));
    }
  }, []);

  const columns = useMemo<ProColumns<AuditRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        sorter: true,
        title: '审计编号',
      },
      {
        dataIndex: 'eventType',
        sorter: true,
        title: '事件类型',
      },
      {
        dataIndex: 'subject',
        sorter: true,
        title: '主体',
      },
      {
        dataIndex: 'actor',
        sorter: true,
        title: '操作者',
      },
      {
        dataIndex: 'result',
        sorter: true,
        title: '结果',
        render: (_, row) =>
          row.result === 'success' ? (
            <StatusTag color="green" label="成功" />
          ) : (
            <StatusTag color="red" label="失败" />
          ),
      },
      {
        dataIndex: 'timestamp',
        sorter: true,
        title: '发生时间',
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button onClick={() => setSelectedAudit(row)} type="link">
              详情
            </Button>
            <Button onClick={() => void openTraceDialog(row)} type="link">
              链路追踪
            </Button>
          </Space>
        ),
      },
    ],
    [openTraceDialog],
  );

  return (
    <>
      <ManagementListPage<AuditRecord>
        breadcrumbGroup="运营治理"
        columns={columns}
        dataSource={listState.rows}
        viewStorageKey="governance.audit"
        filters={[
          { label: '事件类型', name: 'eventType', type: 'text' },
          { label: '主体', name: 'subject', type: 'text' },
          { label: '操作者', name: 'actor', type: 'text' },
          {
            label: '结果',
            name: 'result',
            options: [
              { label: '成功', value: 'success' },
              { label: '失败', value: 'failed' },
            ],
            type: 'select',
          },
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
        tableTitle="审计列表"
        title="审计与运行"
      />
      <Modal
        footer={null}
        onCancel={() => setSelectedAudit(undefined)}
        open={Boolean(selectedAudit)}
        title="审计详情"
        width={720}
      >
        {selectedAudit ? (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="事件类型">{selectedAudit.eventType}</Descriptions.Item>
              <Descriptions.Item label="主体">{selectedAudit.subject}</Descriptions.Item>
              <Descriptions.Item label="AI 任务">{selectedAudit.aiTaskId ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="操作者">{selectedAudit.actor}</Descriptions.Item>
              <Descriptions.Item label="发生时间">{selectedAudit.timestamp}</Descriptions.Item>
            </Descriptions>
            <pre className="audit-json">{JSON.stringify(selectedAudit.payload ?? {}, null, 2)}</pre>
          </Space>
        ) : null}
      </Modal>
      <Modal
        footer={null}
        loading={traceDialog?.loading}
        onCancel={() => setTraceDialog(undefined)}
        open={Boolean(traceDialog)}
        title="链路追踪"
        width={760}
      >
        {traceDialog?.context ? (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions column={3} size="small">
              <Descriptions.Item label="上游">
                {traceDialog.context.summary.upstreamCount}
              </Descriptions.Item>
              <Descriptions.Item label="下游">
                {traceDialog.context.summary.downstreamCount}
              </Descriptions.Item>
              <Descriptions.Item label="风险">
                {traceDialog.context.summary.riskCount}
              </Descriptions.Item>
            </Descriptions>
            <section>
              <Text strong>下游链路</Text>
              <RelationList items={traceDialog.context.downstream} />
            </section>
            <section>
              <Text strong>风险信号</Text>
              {traceDialog.context.riskSignals.length ? (
                <Space orientation="vertical" size={8} style={{ width: '100%' }}>
                  {traceDialog.context.riskSignals.map((risk) => (
                    <div
                      className="audit-trace-item"
                      key={`${risk.riskType}-${risk.sourceSubjectType}-${risk.sourceSubjectId}`}
                    >
                      <Space size={8} wrap>
                        <Tag color={risk.severity === 'high' ? 'red' : 'orange'}>
                          {risk.riskType}
                        </Tag>
                        <Text type="secondary">{risk.severity}</Text>
                      </Space>
                      <Text type="secondary">
                        {risk.sourceSubjectType}: {risk.sourceSubjectId}
                      </Text>
                      <Text>{risk.impactSummary}</Text>
                      <Text type="secondary">{risk.recommendation}</Text>
                    </div>
                  ))}
                </Space>
              ) : (
                <Text type="secondary">暂无风险信号。</Text>
              )}
            </section>
            <section>
              <Text strong>缺失上下文</Text>
              <div>
                {traceDialog.context.missingContext.length ? (
                  traceDialog.context.missingContext.map((item) => <Tag key={item}>{item}</Tag>)
                ) : (
                  <Text type="secondary">暂无缺失上下文。</Text>
                )}
              </div>
            </section>
          </Space>
        ) : null}
      </Modal>
    </>
  );
}
