import type { ProColumns } from '@ant-design/pro-components';
import { Button, Card, Col, Descriptions, Modal, Row, Space, Statistic, Table, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import {
  fetchCodeInspectionDetail,
  fetchCodeInspectionDashboard,
  type CodeInspectionDashboardRecord,
  fetchCodeInspectionReports,
  type CodeInspectionDetailRecord,
  type CodeInspectionFindingRecord,
  type CodeInspectionListQuery,
  type CodeInspectionNotificationRecord,
  type CodeInspectionReportRecord,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';

const riskColorByValue = new Map([
  ['critical', 'red'],
  ['high', 'orange'],
  ['medium', 'gold'],
  ['low', 'green'],
]);

const severityColorByValue = new Map([
  ['critical', 'red'],
  ['high', 'orange'],
  ['medium', 'gold'],
  ['low', 'green'],
  ['info', 'blue'],
]);

const sortFieldMap: Record<string, string> = {
  createdAt: 'created_at',
  committerCount: 'committer_count',
  findingCount: 'finding_count',
  id: 'id',
  riskLevel: 'risk_level',
  severeFindingCount: 'severe_finding_count',
  status: 'status',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildCodeInspectionQuery(query: ManagementListQuery): CodeInspectionListQuery {
  return {
    committer: normalizeFilterText(query.filters.committer),
    page: query.page,
    pageSize: query.pageSize,
    riskLevel: normalizeFilterText(query.filters.riskLevel),
    sortField: query.sortField ? sortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
    title: normalizeFilterText(query.filters.title),
  };
}

function compactText(value?: string | null) {
  const text = value || '-';
  return (
    <Typography.Text ellipsis={{ tooltip: text }} style={{ display: 'block', maxWidth: '100%' }}>
      {text}
    </Typography.Text>
  );
}

function internalHref(path: string, params: Record<string, string | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      search.set(key, value);
    }
  });
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

function linkedTraceText(value: string | null | undefined, href: string) {
  if (!value) {
    return compactText(value);
  }
  return (
    <Typography.Link
      ellipsis
      href={href}
      style={{ display: 'block', maxWidth: '100%' }}
      title={value}
    >
      {value}
    </Typography.Link>
  );
}

function committerLabel(
  value?: {
    email?: string | null;
    finding_count?: number;
    name?: string | null;
    username?: string | null;
  } | null,
) {
  if (!value) {
    return '-';
  }
  const identity = value.name || value.username || value.email || '-';
  const email = value.email && value.email !== identity ? ` <${value.email}>` : '';
  const count = value.finding_count ? ` (${value.finding_count})` : '';
  return `${identity}${email}${count}`;
}

function committerSummaryText(row: CodeInspectionReportRecord) {
  const summary = row.committer_summary ?? [];
  if (!summary.length) {
    return '-';
  }
  return summary.slice(0, 3).map(committerLabel).join('、');
}

function bugLink(value?: string | null) {
  if (!value) {
    return '-';
  }
  return (
    <Typography.Link href={`/delivery/bugs?title=${encodeURIComponent(value)}`}>
      {value}
    </Typography.Link>
  );
}

function percentText(value?: number | null) {
  const normalized = typeof value === 'number' && Number.isFinite(value) ? value : 0;
  return `${Math.round(normalized * 100)}%`;
}

function severityTag(value?: string | null) {
  const text = value || '-';
  return <Tag color={severityColorByValue.get(text) ?? riskColorByValue.get(text) ?? 'default'}>{text}</Tag>;
}

function compactMetricTable<Row extends Record<string, unknown>>({
  columns,
  dataSource,
  rowKey,
}: {
  columns: Array<{
    dataIndex: keyof Row & string;
    render?: (value: unknown, row: Row) => ReactNode;
    title: string;
    width?: number;
  }>;
  dataSource: Row[];
  rowKey: (keyof Row & string) | ((record: Row, index?: number) => string);
}) {
  return (
    <Table<Row>
      columns={columns}
      dataSource={dataSource}
      pagination={false}
      rowKey={rowKey}
      scroll={{ x: columns.reduce((total, column) => total + (column.width ?? 140), 0) }}
      size="small"
    />
  );
}

function CodeInspectionGovernanceOverview({
  dashboard,
  loading,
}: {
  dashboard?: CodeInspectionDashboardRecord;
  loading: boolean;
}) {
  const summary = dashboard?.summary;
  const sla = dashboard?.sla;
  return (
    <Space orientation="vertical" size={12} style={{ width: '100%', marginBottom: 16 }}>
      <Row gutter={[12, 12]}>
        <Col lg={6} md={12} xs={24}>
          <Card loading={loading} size="small">
            <Statistic title="巡检报告" value={summary?.report_count ?? 0} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card loading={loading} size="small">
            <Statistic title="发现问题" value={summary?.finding_count ?? 0} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card loading={loading} size="small">
            <Statistic title="严重问题" value={summary?.severe_finding_count ?? 0} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card loading={loading} size="small">
            <Statistic
              suffix={<Tag color={sla?.status === 'healthy' ? 'green' : 'orange'}>{sla?.status ?? '-'}</Tag>}
              title="Bug 覆盖率"
              value={percentText(sla?.bug_coverage_rate)}
            />
          </Card>
        </Col>
      </Row>
      <Row gutter={[12, 12]}>
        <Col lg={12} xs={24}>
          <Card loading={loading} size="small" title="规则维度统计">
            {compactMetricTable({
              columns: [
                { dataIndex: 'rule_id', title: '规则', width: 180 },
                {
                  dataIndex: 'severity',
                  render: (value) => severityTag(String(value ?? '')),
                  title: '最高级别',
                  width: 120,
                },
                { dataIndex: 'category', title: '分类', width: 120 },
                { dataIndex: 'finding_count', title: '问题数', width: 100 },
                { dataIndex: 'severe_finding_count', title: '严重', width: 90 },
              ],
              dataSource: dashboard?.rule_distribution ?? [],
              rowKey: 'rule_id',
            })}
          </Card>
        </Col>
        <Col lg={12} xs={24}>
          <Card loading={loading} size="small" title="仓库风险排行">
            {compactMetricTable({
              columns: [
                {
                  dataIndex: 'repository_name',
                  render: (_, row) => compactText(String(row.repository_name ?? row.repository_id ?? '-')),
                  title: '仓库',
                  width: 220,
                },
                {
                  dataIndex: 'risk_level',
                  render: (value) => severityTag(String(value ?? '')),
                  title: '最高风险',
                  width: 120,
                },
                { dataIndex: 'report_count', title: '报告', width: 90 },
                { dataIndex: 'finding_count', title: '问题数', width: 100 },
                { dataIndex: 'severe_finding_count', title: '严重', width: 90 },
              ],
              dataSource: dashboard?.repository_ranking ?? [],
              rowKey: 'repository_id',
            })}
          </Card>
        </Col>
        <Col lg={12} xs={24}>
          <Card loading={loading} size="small" title="分支风险排行">
            {compactMetricTable({
              columns: [
                { dataIndex: 'branch', title: '分支', width: 160 },
                {
                  dataIndex: 'repository_name',
                  render: (_, row) => compactText(String(row.repository_name ?? row.repository_id ?? '-')),
                  title: '仓库',
                  width: 220,
                },
                { dataIndex: 'finding_count', title: '问题数', width: 100 },
                { dataIndex: 'severe_finding_count', title: '严重', width: 90 },
              ],
              dataSource: dashboard?.branch_ranking ?? [],
              rowKey: (row) => `${row.repository_id ?? row.repository_name ?? '-'}:${row.branch ?? '-'}`,
            })}
          </Card>
        </Col>
        <Col lg={12} xs={24}>
          <Card loading={loading} size="small" title="提交人风险排行">
            {compactMetricTable({
              columns: [
                {
                  dataIndex: 'email',
                  render: (_, row) => compactText(committerLabel(row)),
                  title: '提交人',
                  width: 260,
                },
                { dataIndex: 'finding_count', title: '问题数', width: 100 },
                { dataIndex: 'severe_finding_count', title: '严重', width: 90 },
                { dataIndex: 'bug_count', title: 'Bug', width: 90 },
              ],
              dataSource: dashboard?.committer_ranking ?? [],
              rowKey: (row) => row.email ?? row.username ?? row.name ?? 'unknown',
            })}
          </Card>
        </Col>
      </Row>
      <Card loading={loading} size="small" title="严重问题 SLA">
        <Descriptions
          column={{ lg: 4, md: 2, xs: 1 }}
          items={[
            { key: 'threshold', label: '严重阈值', children: sla?.severe_threshold ?? '-' },
            { key: 'covered', label: '已关联 Bug', children: sla?.covered_by_bug_count ?? 0 },
            { key: 'uncovered', label: '未覆盖严重问题', children: sla?.uncovered_severe_finding_count ?? 0 },
            { key: 'oldest', label: '最早未覆盖', children: sla?.oldest_uncovered_at ?? '-' },
          ]}
          size="small"
        />
      </Card>
    </Space>
  );
}

function sourceTraceItems(report: CodeInspectionReportRecord) {
  return [
    { key: 'source_system', label: '来源系统', children: compactText(report.source_system) },
    {
      key: 'scheduled_job_id',
      label: '来源作业',
      children: linkedTraceText(
        report.scheduled_job_id,
        internalHref('/tasks/scheduled-jobs', {
          tab: 'jobs',
          job_id: report.scheduled_job_id ?? undefined,
        }),
      ),
    },
    {
      key: 'scheduled_job_run_id',
      label: '来源运行',
      children: linkedTraceText(
        report.scheduled_job_run_id,
        internalHref('/tasks/scheduled-jobs', {
          tab: 'runs',
          run_id: report.scheduled_job_run_id ?? undefined,
        }),
      ),
    },
    { key: 'plugin_connection_id', label: '数据连接', children: compactText(report.plugin_connection_id) },
    { key: 'plugin_action_id', label: '结果动作', children: compactText(report.plugin_action_id) },
    { key: 'plugin_invocation_log_id', label: '插件调用', children: compactText(report.plugin_invocation_log_id) },
  ];
}

export default function CodeInspectionsPage() {
  const [detailState, setDetailState] = useState<{
    detail?: CodeInspectionDetailRecord;
    loading: boolean;
    report?: CodeInspectionReportRecord;
  }>();
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'createdAt',
    sortOrder: 'descend',
  });
  const [listState, setListState] = useState<{
    page: number;
    pageSize: number;
    rows: CodeInspectionReportRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const [dashboardState, setDashboardState] = useState<{
    dashboard?: CodeInspectionDashboardRecord;
    status: 'error' | 'loading' | 'ready';
  }>({ status: 'loading' });

  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    setDashboardState((current) => ({ ...current, status: 'loading' }));
    try {
      const query = buildCodeInspectionQuery(listQuery);
      const [result, dashboard] = await Promise.all([
        fetchCodeInspectionReports(query),
        fetchCodeInspectionDashboard(query),
      ]);
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        rows: result.rows,
        status: 'ready',
        total: result.total,
      });
      setDashboardState({ dashboard, status: 'ready' });
    } catch (error) {
      message.error(formatMutationError(error));
      setListState((current) => ({ ...current, rows: [], status: 'error' }));
      setDashboardState((current) => ({ ...current, status: 'error' }));
    }
  }, [listQuery]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const openDetail = useCallback(async (report: CodeInspectionReportRecord) => {
    setDetailState({ loading: true, report });
    try {
      const detail = await fetchCodeInspectionDetail(report.id);
      setDetailState({ detail, loading: false, report });
    } catch (error) {
      setDetailState(undefined);
      message.error(formatMutationError(error));
    }
  }, []);

  const columns = useMemo<ProColumns<CodeInspectionReportRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        sorter: true,
        title: '报告 ID',
        width: 210,
        render: (_, row) => compactText(row.id),
      },
      {
        dataIndex: 'repository_name',
        title: '仓库',
        width: 220,
        render: (_, row) => compactText(row.repository_name || row.repository_path || row.repository_id),
      },
      {
        dataIndex: 'branch',
        title: '分支',
        width: 120,
        render: (_, row) => compactText(row.branch),
      },
      {
        dataIndex: 'committerCount',
        sorter: true,
        title: '提交人',
        width: 260,
        render: (_, row) => compactText(committerSummaryText(row)),
      },
      {
        dataIndex: 'riskLevel',
        sorter: true,
        title: '风险级别',
        width: 120,
        render: (_, row) => (
          <Tag color={riskColorByValue.get(row.risk_level) ?? 'default'}>{row.risk_level}</Tag>
        ),
      },
      {
        dataIndex: 'findingCount',
        sorter: true,
        title: '问题数',
        width: 100,
        render: (_, row) => row.finding_count,
      },
      {
        dataIndex: 'severeFindingCount',
        sorter: true,
        title: '严重问题',
        width: 110,
        render: (_, row) => row.severe_finding_count,
      },
      {
        dataIndex: 'status',
        sorter: true,
        title: '状态',
        width: 100,
        render: (_, row) =>
          row.status === 'completed' ? (
            <StatusTag color="green" label="已完成" />
          ) : (
            <StatusTag color="red" label={row.status} />
          ),
      },
      {
        dataIndex: 'summary',
        title: '摘要',
        width: 320,
        render: (_, row) => compactText(row.summary),
      },
      {
        dataIndex: 'createdAt',
        sorter: true,
        title: '创建时间',
        width: 180,
        render: (_, row) => compactText(row.created_at),
      },
      {
        fixed: 'right',
        key: 'actions',
        title: '操作',
        valueType: 'option',
        width: 110,
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
      <ManagementListPage<CodeInspectionReportRecord>
        beforeTable={
          <CodeInspectionGovernanceOverview
            dashboard={dashboardState.dashboard}
            loading={dashboardState.status === 'loading'}
          />
        }
        breadcrumbGroup="运营治理"
        columns={columns}
        dataSource={listState.rows}
        filters={[
          { label: '报告/摘要', name: 'title', type: 'text' },
          { label: '提交人', name: 'committer', placeholder: '姓名 / 邮箱 / 用户名', type: 'text' },
          {
            label: '风险级别',
            name: 'riskLevel',
            options: [
              { label: 'critical', value: 'critical' },
              { label: 'high', value: 'high' },
              { label: 'medium', value: 'medium' },
              { label: 'low', value: 'low' },
            ],
            type: 'select',
          },
          {
            label: '状态',
            name: 'status',
            options: [
              { label: '已完成', value: 'completed' },
              { label: '部分完成', value: 'partial' },
              { label: '失败', value: 'failed' },
            ],
            type: 'select',
          },
        ]}
        loading={listState.status === 'loading'}
        onReload={reload}
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          total: listState.total,
        }}
        rowKey="id"
        tableScroll={{ x: 1740 }}
        tableTitle="代码巡检"
        title="代码巡检"
        toolbarActions={[
          <Button key="reload" onClick={reload}>
            刷新
          </Button>,
        ]}
      />

      <Modal
        footer={<Button onClick={() => setDetailState(undefined)}>关闭</Button>}
        open={Boolean(detailState)}
        title="代码巡检详情"
        width={1040}
        onCancel={() => setDetailState(undefined)}
      >
        {detailState?.loading ? (
          <Typography.Text type="secondary">详情加载中...</Typography.Text>
        ) : detailState?.detail ? (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions
              bordered
              column={2}
              size="small"
              items={[
                { key: 'id', label: '报告 ID', children: detailState.detail.report.id },
                { key: 'risk', label: '风险级别', children: detailState.detail.report.risk_level },
                { key: 'repository', label: '仓库', children: detailState.detail.report.repository_name || '-' },
                { key: 'branch', label: '分支', children: detailState.detail.report.branch || '-' },
                { key: 'committer_count', label: '提交人数', children: detailState.detail.report.committer_count ?? 0 },
                {
                  key: 'committers',
                  label: '主要提交人',
                  children: committerSummaryText(detailState.detail.report),
                },
                { key: 'finding_count', label: '问题数', children: detailState.detail.report.finding_count },
                { key: 'severe_count', label: '严重问题', children: detailState.detail.report.severe_finding_count },
                { key: 'bugs', label: '创建 Bug', children: detailState.detail.report.created_bug_ids?.join('、') || '-' },
                { key: 'summary', label: '摘要', children: detailState.detail.report.summary || '-' },
              ]}
            />
            <Descriptions
              bordered
              column={2}
              items={sourceTraceItems(detailState.detail.report)}
              size="small"
              title="来源链路"
            />
            <Table<CodeInspectionFindingRecord>
              columns={[
                {
                  dataIndex: 'severity',
                  title: '级别',
                  width: 100,
                  render: (value) => <Tag color={severityColorByValue.get(String(value))}>{String(value)}</Tag>,
                },
                { dataIndex: 'category', title: '分类', width: 110 },
                { dataIndex: 'rule_id', title: '规则', width: 120 },
                { dataIndex: 'title', title: '问题', width: 220 },
                {
                  dataIndex: 'committer_email',
                  title: '提交人',
                  width: 260,
                  render: (_, row) =>
                    compactText(
                      committerLabel({
                        email: row.committer_email,
                        name: row.committer_name,
                        username: row.committer_username,
                      }),
                    ),
                },
                {
                  dataIndex: 'file_path',
                  title: '位置',
                  width: 260,
                  render: (_, row) => compactText(`${row.file_path || '-'}${row.line_number ? `:${row.line_number}` : ''}`),
                },
                { dataIndex: 'created_bug_id', title: 'Bug', width: 150, render: (value) => bugLink(String(value ?? '')) },
                { dataIndex: 'recommendation', title: '建议', render: (value) => compactText(String(value ?? '')) },
              ]}
              dataSource={detailState.detail.findings}
              pagination={false}
              rowKey="id"
              scroll={{ x: 1460 }}
              size="small"
            />
            <Table<CodeInspectionNotificationRecord>
              columns={[
                { dataIndex: 'channel', title: '渠道', width: 120 },
                { dataIndex: 'target', title: '目标', width: 320, render: (value) => compactText(String(value ?? '')) },
                { dataIndex: 'status', title: '状态', width: 120 },
                { dataIndex: 'message', title: '消息', render: (value) => compactText(String(value ?? '')) },
              ]}
              dataSource={detailState.detail.notifications}
              pagination={false}
              rowKey="id"
              size="small"
            />
          </Space>
        ) : null}
      </Modal>
    </>
  );
}
