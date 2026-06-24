import type { ProColumns } from '@ant-design/pro-components';
import { Button, Card, Col, Descriptions, Modal, Row, Space, Statistic, Table, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react';

import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import { ExecutionTraceLink } from '../../components/ExecutionTraceLink';
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
import { formatDisplayDateTime } from '../../utils/dateTime';
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

const detailSingleLineTextStyle: CSSProperties = {
  display: 'block',
  maxWidth: '100%',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const detailMultiLineTextStyle: CSSProperties = {
  display: 'block',
  lineHeight: 1.5,
  maxWidth: '100%',
  whiteSpace: 'normal',
  wordBreak: 'break-word',
};

function detailSingleLineText(value?: string | null) {
  const text = value || '-';
  return (
    <Typography.Text style={detailSingleLineTextStyle} title={text}>
      {text}
    </Typography.Text>
  );
}

function detailMultiLineText(value?: string | null) {
  const text = value || '-';
  return <Typography.Text style={detailMultiLineTextStyle}>{text}</Typography.Text>;
}

function findingProblemText(row: CodeInspectionFindingRecord) {
  return (
    <Space orientation="vertical" size={4} style={{ width: '100%' }}>
      {detailMultiLineText(row.title)}
      {row.recommendation ? (
        <Typography.Text style={detailMultiLineTextStyle} type="secondary">
          {row.recommendation}
        </Typography.Text>
      ) : null}
    </Space>
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
              suffix={
                <Tag color={sla?.status === 'healthy' ? 'green' : 'orange'}>整体 {sla?.status ?? '-'}</Tag>
              }
              title="Bug 覆盖率"
              value={percentText(sla?.bug_coverage_rate)}
            />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card loading={loading} size="small">
            <Statistic
              suffix={
                <Tag color={sla?.status === 'healthy' ? 'green' : 'orange'}>整体 {sla?.status ?? '-'}</Tag>
              }
              title="整改任务覆盖率"
              value={percentText(sla?.task_coverage_rate)}
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
      <Card loading={loading} size="small" title="质量门禁趋势">
        {compactMetricTable({
          columns: [
            { dataIndex: 'date', title: '日期', width: 140 },
            { dataIndex: 'report_count', title: '报告', width: 90 },
            { dataIndex: 'quality_gate_failed_count', title: '失败', width: 90 },
            { dataIndex: 'quality_gate_passed_count', title: '通过', width: 90 },
            { dataIndex: 'quality_gate_skipped_count', title: '跳过', width: 90 },
            { dataIndex: 'severe_finding_count', title: '严重问题', width: 110 },
            { dataIndex: 'bug_count', title: 'Bug', width: 90 },
          ],
          dataSource: dashboard?.trend ?? [],
          rowKey: 'date',
        })}
      </Card>
      <Card loading={loading} size="small" title="严重问题 SLA">
        <Descriptions
          column={{ lg: 4, md: 2, xs: 1 }}
          items={[
            { key: 'threshold', label: '严重阈值', children: sla?.severe_threshold ?? '-' },
            { key: 'covered', label: '已关联 Bug', children: sla?.covered_by_bug_count ?? 0 },
            { key: 'uncovered', label: '未覆盖严重问题', children: sla?.uncovered_severe_finding_count ?? 0 },
            { key: 'oldest', label: '最早未覆盖', children: sla?.oldest_uncovered_at ?? '-' },
            { key: 'task_covered', label: '已生成整改任务', children: sla?.covered_by_task_count ?? 0 },
            { key: 'task_uncovered', label: '未派生整改任务', children: sla?.uncovered_task_finding_count ?? 0 },
            { key: 'task_oldest', label: '最早未派生任务', children: sla?.oldest_without_task_at ?? '-' },
          ]}
          size="small"
        />
      </Card>
    </Space>
  );
}

function sourceTraceItems(report: CodeInspectionReportRecord) {
  return [
    {
      key: 'execution_trace',
      label: '执行诊断',
      children: (
        <Space wrap size={8}>
          <ExecutionTraceLink sourceId={report.id} sourceType="code_inspection_report">
            巡检报告诊断
          </ExecutionTraceLink>
          <ExecutionTraceLink sourceId={report.scheduled_job_run_id} sourceType="scheduled_job_run">
            运行诊断
          </ExecutionTraceLink>
          <ExecutionTraceLink sourceId={report.plugin_invocation_log_id} sourceType="plugin_invocation_log">
            插件诊断
          </ExecutionTraceLink>
        </Space>
      ),
    },
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
    {
      key: 'plugin_invocation_log_id',
      label: '插件调用',
      children: (
        <ExecutionTraceLink
          sourceId={report.plugin_invocation_log_id}
          sourceType="plugin_invocation_log"
          style={{ display: 'block', maxWidth: '100%' }}
        >
          {report.plugin_invocation_log_id}
        </ExecutionTraceLink>
      ),
    },
  ];
}

function scanSnapshotItems(report: CodeInspectionReportRecord) {
  return [
    { key: 'scan_mode', label: '扫描模式', children: compactText(report.scan_mode) },
    { key: 'scanner_name', label: '扫描器', children: compactText(report.scanner_name) },
    { key: 'scanner_version', label: '扫描器版本', children: compactText(report.scanner_version) },
    { key: 'rules_version', label: '规则版本', children: compactText(report.rules_version) },
    { key: 'rules_loaded', label: '加载规则', children: compactText(report.rules_loaded?.join('、')) },
    { key: 'commit_sha', label: 'Commit', children: compactText(report.commit_sha) },
    { key: 'remote_url_summary', label: '远端摘要', children: compactText(report.remote_url_summary) },
    { key: 'remote_url_hash', label: '远端 Hash', children: compactText(report.remote_url_hash) },
    { key: 'artifact_ref', label: '代码快照', children: compactText(report.artifact_ref) },
    {
      key: 'checkout_path_retained',
      label: 'Checkout 保留',
      children: report.checkout_path_retained ? '已保留' : '未保留',
    },
    { key: 'scan_started_at', label: '开始时间', children: compactText(formatDisplayDateTime(report.scan_started_at)) },
    { key: 'scan_finished_at', label: '结束时间', children: compactText(formatDisplayDateTime(report.scan_finished_at)) },
  ];
}

function recordValue(record: Record<string, unknown> | undefined, key: string, fallback = '-') {
  const value = record?.[key];
  if (value === undefined || value === null || value === '') {
    return fallback;
  }
  return String(value);
}

function arrayValue(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map((item) => String(item || '').trim()).filter(Boolean)
    : [];
}

function scannerStatusText(scanProfile?: Record<string, unknown>) {
  const status = scanProfile?.external_scanner_status as Record<string, unknown> | undefined;
  if (!status) {
    return '-';
  }
  const executed = arrayValue(status.executed);
  const skipped = arrayValue(status.skipped);
  const failed = arrayValue(status.failed);
  const parts = [
    executed.length ? `已执行 ${executed.join('、')}` : undefined,
    skipped.length ? `已跳过 ${skipped.join('、')}` : undefined,
    failed.length ? `失败 ${failed.join('、')}` : undefined,
  ].filter(Boolean);
  return parts.join('；') || '-';
}

function scanSummaryItems(detail: CodeInspectionDetailRecord) {
  const summary = detail.scan_summary;
  const coverage = summary?.coverage;
  const suppression = summary?.suppression_summary;
  const qualityGate = summary?.quality_gate ?? detail.report.quality_gate;
  const comparison = summary?.previous_comparison ?? detail.report.previous_comparison;
  const scanProfile = (summary?.scan_profile ?? detail.report.scan_profile) as
    | Record<string, unknown>
    | undefined;
  const scannerEngines = arrayValue(scanProfile?.scanner_engines);
  return [
    {
      key: 'quality_gate',
      label: '质量门禁',
      children: recordValue(qualityGate, 'status'),
    },
    {
      key: 'suppressed_finding_count',
      label: '过滤问题数',
      children: recordValue(coverage, 'suppressed_finding_count', String(detail.report.suppressed_finding_count ?? 0)),
    },
    {
      key: 'baseline',
      label: 'Baseline 过滤',
      children: recordValue(suppression, 'baseline', '0'),
    },
    {
      key: 'accepted_risk',
      label: '已接受风险',
      children: recordValue(suppression, 'accepted_risk', '0'),
    },
    {
      key: 'coverage',
      label: '扫描覆盖',
      children: `${recordValue(coverage, 'files_scanned', String(detail.report.files_scanned ?? 0))} 文件 / ${recordValue(
        coverage,
        'lines_scanned',
        String(detail.report.lines_scanned ?? 0),
      )} 行`,
    },
    {
      key: 'scanner_engines',
      label: '扫描引擎',
      children: scannerEngines.length ? scannerEngines.join('、') : '-',
    },
    {
      key: 'external_scanner_status',
      label: '外部引擎状态',
      children: scannerStatusText(scanProfile),
    },
    {
      key: 'previous_comparison',
      label: '与上次对比',
      children: comparison
        ? `问题 ${recordValue(comparison, 'finding_delta', '0')}，严重 ${recordValue(comparison, 'severe_finding_delta', '0')}`
        : '-',
    },
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
    queueMicrotask(() => {
      void reload();
    });
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
        render: (_, row) => compactText(formatDisplayDateTime(row.created_at)),
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
        width="min(1280px, calc(100vw - 48px))"
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
            <Descriptions
              bordered
              column={2}
              items={scanSnapshotItems(detailState.detail.report)}
              size="small"
              title="扫描快照"
            />
            <Descriptions
              bordered
              column={2}
              items={scanSummaryItems(detailState.detail)}
              size="small"
              title="扫描摘要"
            />
            <Table<Record<string, unknown>>
              columns={[
                {
                  dataIndex: 'rule_id',
                  title: '规则',
                  width: 260,
                  render: (value) => detailSingleLineText(String(value ?? '')),
                },
                { dataIndex: 'category', title: '分类', width: 140 },
                { dataIndex: 'severity', title: '最高级别', width: 120 },
                { dataIndex: 'finding_count', title: '问题数', width: 100 },
                { dataIndex: 'severe_finding_count', title: '严重问题', width: 100 },
              ]}
              dataSource={detailState.detail.scan_summary?.rule_distribution ?? []}
              pagination={false}
              rowKey={(row) => String(row.rule_id ?? JSON.stringify(row))}
              scroll={{ x: 720 }}
              size="small"
              tableLayout="fixed"
              title={() => '规则命中分布'}
            />
            <Table<Record<string, unknown>>
              columns={[
                {
                  dataIndex: 'file_path',
                  title: '文件',
                  width: 420,
                  render: (value) => detailSingleLineText(String(value ?? '')),
                },
                { dataIndex: 'finding_count', title: '问题数', width: 100 },
                { dataIndex: 'severe_finding_count', title: '严重问题', width: 100 },
              ]}
              dataSource={detailState.detail.scan_summary?.file_distribution ?? []}
              pagination={false}
              rowKey={(row) => String(row.file_path ?? JSON.stringify(row))}
              scroll={{ x: 640 }}
              size="small"
              tableLayout="fixed"
              title={() => '文件维度问题'}
            />
            <Table<CodeInspectionFindingRecord>
              columns={[
                {
                  dataIndex: 'severity',
                  title: '级别',
                  width: 110,
                  render: (value) => <Tag color={severityColorByValue.get(String(value))}>{String(value)}</Tag>,
                },
                {
                  dataIndex: 'category',
                  title: '分类',
                  width: 130,
                  render: (value) => detailSingleLineText(String(value ?? '')),
                },
                {
                  dataIndex: 'rule_id',
                  title: '规则',
                  width: 260,
                  render: (value) => detailSingleLineText(String(value ?? '')),
                },
                {
                  dataIndex: 'title',
                  title: '问题 / 建议',
                  width: 520,
                  render: (_, row) => findingProblemText(row),
                },
                {
                  dataIndex: 'committer_email',
                  title: '提交人',
                  width: 180,
                  render: (_, row) =>
                    detailSingleLineText(
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
                  render: (_, row) =>
                    detailSingleLineText(`${row.file_path || '-'}${row.line_number ? `:${row.line_number}` : ''}`),
                },
                { dataIndex: 'created_bug_id', title: 'Bug', width: 140, render: (value) => bugLink(String(value ?? '')) },
              ]}
              dataSource={detailState.detail.findings}
              pagination={false}
              rowKey="id"
              scroll={{ x: 1600 }}
              size="small"
              tableLayout="fixed"
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
