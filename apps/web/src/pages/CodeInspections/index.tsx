import type { ProColumns } from '@ant-design/pro-components';
import { Button, Descriptions, Modal, Space, Table, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import { ExecutionTraceLink } from '../../components/ExecutionTraceLink';
import {
  fetchCodeInspectionDetail,
  fetchCodeInspectionDashboard,
  fullChainSubjectHref,
  type CodeInspectionDashboardRecord,
  fetchCodeInspectionReports,
  requestCodeInspectionFindingSuppression,
  reviewCodeInspectionFindingSuppression,
  type CodeInspectionDetailRecord,
  type CodeInspectionFindingRecord,
  type CodeInspectionListQuery,
  type CodeInspectionNotificationRecord,
  type CodeInspectionReportRecord,
  type RemoteListPerformance,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { formatMutationError } from '../../utils/managementCrud';
import { CodeInspectionGovernanceOverview } from './components/CodeInspectionGovernanceOverview';
import {
  bugLink,
  committerLabel,
  committerSummaryText,
  compactText,
  detailSingleLineText,
  findingProblemText,
  riskColorByValue,
  severityColorByValue,
  suppressionReasonText,
  suppressionStatusTag,
  taskLink,
} from './components/codeInspectionPresentation';

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

function readCodeInspectionDeepLinkReportId() {
  const search = new URLSearchParams(window.location.search);
  const sourceType = search.get('source_type');
  if (sourceType && sourceType !== 'code_inspection_report') {
    return undefined;
  }
  return search.get('report_id') ?? search.get('source_id') ?? undefined;
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

function percentageText(value?: number) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }
  return `${Math.round(value * 1000) / 10}%`;
}

function codeInspectionGovernanceItems(detail: CodeInspectionDetailRecord) {
  const governance = detail.governance_summary;
  const actionItems = governance?.action_items ?? [];
  return [
    {
      key: 'status',
      label: '闭环状态',
      children:
        governance?.status === 'healthy' ? (
          <Tag color="green">已闭环</Tag>
        ) : governance?.status === 'pending_review' ? (
          <Tag color="gold">待审批</Tag>
        ) : (
          <Tag color="red">需处理</Tag>
        ),
    },
    {
      key: 'active_severe',
      label: '有效严重问题',
      children: `${governance?.active_severe_finding_count ?? detail.report.severe_finding_count ?? 0} 个`,
    },
    {
      key: 'bug_coverage',
      label: 'Bug 覆盖',
      children: `${governance?.covered_by_bug_count ?? detail.report.created_bug_ids?.length ?? 0} 个 · ${percentageText(
        governance?.bug_coverage_rate,
      )}`,
    },
    {
      key: 'task_coverage',
      label: '整改任务覆盖',
      children: `${governance?.covered_by_task_count ?? detail.report.created_task_ids?.length ?? 0} 个 · ${percentageText(
        governance?.task_coverage_rate,
      )}`,
    },
    {
      key: 'uncovered_bug',
      label: '未关联 Bug',
      children: `${governance?.uncovered_bug_finding_count ?? 0} 个`,
    },
    {
      key: 'uncovered_task',
      label: '未派生任务',
      children: `${governance?.uncovered_task_finding_count ?? 0} 个`,
    },
    {
      key: 'pending_suppression',
      label: '待审批忽略',
      children: `${governance?.pending_suppression_count ?? 0} 个`,
    },
    {
      key: 'accepted_risk',
      label: '已接受风险',
      children: `${governance?.accepted_risk_count ?? 0} 个`,
    },
    {
      key: 'action_items',
      label: '治理待办',
      children: actionItems.length ? actionItems.map((item) => `${item.label} ${item.count ?? 0}`).join('；') : '-',
    },
  ];
}

export default function CodeInspectionsPage() {
  const deepLinkReportId = useMemo(() => readCodeInspectionDeepLinkReportId(), []);
  const isDeepLinkHandledRef = useRef(false);
  const [detailState, setDetailState] = useState<{
    detail?: CodeInspectionDetailRecord;
    loading: boolean;
    report?: CodeInspectionReportRecord;
  }>();
  const [suppressionActionLoading, setSuppressionActionLoading] = useState<string>();
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
    performance?: RemoteListPerformance;
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
        performance: result.performance,
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

  const openDetailById = useCallback(async (reportId: string, report?: CodeInspectionReportRecord) => {
    setDetailState({
      loading: true,
      report: report ?? {
        finding_count: 0,
        id: reportId,
        risk_level: '-',
        severe_finding_count: 0,
        status: '-',
      },
    });
    try {
      const detail = await fetchCodeInspectionDetail(reportId);
      setDetailState({ detail, loading: false, report: detail.report });
    } catch (error) {
      setDetailState(undefined);
      message.error(formatMutationError(error));
    }
  }, []);

  const openDetail = useCallback((report: CodeInspectionReportRecord) => {
    void openDetailById(report.id, report);
  }, [openDetailById]);

  useEffect(() => {
    if (!deepLinkReportId || isDeepLinkHandledRef.current) {
      return;
    }
    isDeepLinkHandledRef.current = true;
    void openDetailById(deepLinkReportId);
  }, [deepLinkReportId, openDetailById]);

  const handleSuppressionAction = useCallback(
    async (finding: CodeInspectionFindingRecord, action: 'approve' | 'reject' | 'request') => {
      const reportId = detailState?.report?.id ?? detailState?.detail?.report.id;
      if (!reportId) {
        return;
      }
      const loadingKey = `${action}:${finding.id}`;
      setSuppressionActionLoading(loadingKey);
      try {
        const detail =
          action === 'request'
            ? await requestCodeInspectionFindingSuppression(reportId, finding.id, {
                note: '从代码巡检详情申请误报忽略',
                reason: 'false_positive',
              })
            : await reviewCodeInspectionFindingSuppression(reportId, finding.id, {
                decision: action,
                note: action === 'approve' ? '确认误报，批准忽略' : '不符合忽略条件',
              });
        setDetailState({ detail, loading: false, report: detail.report });
        message.success(
          action === 'request' ? '已提交忽略审批' : action === 'approve' ? '已批准忽略' : '已驳回忽略申请',
        );
        void reload();
      } catch (error) {
        message.error(formatMutationError(error));
      } finally {
        setSuppressionActionLoading(undefined);
      }
    },
    [detailState?.detail?.report.id, detailState?.report?.id, reload],
  );

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
        width: 160,
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
        width: 180,
        render: (_, row) => (
          <Space size={4}>
            <Button href={fullChainSubjectHref('code_inspection_report', row.id)} type="link">
              全链路
            </Button>
            <Button onClick={() => void openDetail(row)} type="link">
              详情
            </Button>
          </Space>
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
        viewStorageKey="governance.code_inspections"
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
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="id"
        tableScroll={{ x: 2040 }}
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
                { key: 'tasks', label: '整改任务', children: detailState.detail.report.created_task_ids?.join('、') || '-' },
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
            <Descriptions
              bordered
              column={3}
              items={codeInspectionGovernanceItems(detailState.detail)}
              size="small"
              title="治理闭环"
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
                {
                  dataIndex: 'created_task_id',
                  title: '整改任务',
                  width: 150,
                  render: (value) => taskLink(String(value ?? '')),
                },
                {
                  dataIndex: 'suppression_status',
                  title: '忽略审批',
                  width: 150,
                  render: (_, row) => (
                    <Space orientation="vertical" size={2}>
                      {suppressionStatusTag(row.suppression_status)}
                      {row.suppression_reason ? (
                        <Typography.Text type="secondary">
                          {suppressionReasonText(row.suppression_reason)}
                        </Typography.Text>
                      ) : null}
                    </Space>
                  ),
                },
                {
                  key: 'suppression_actions',
                  title: '治理操作',
                  width: 220,
                  render: (_, row) => {
                    const status = row.suppression_status || 'none';
                    if (status === 'approved') {
                      return <Typography.Text type="secondary">已忽略</Typography.Text>;
                    }
                    if (status === 'pending') {
                      return (
                        <Space size={4}>
                          <Button
                            loading={suppressionActionLoading === `approve:${row.id}`}
                            size="small"
                            type="link"
                            onClick={() => void handleSuppressionAction(row, 'approve')}
                          >
                            批准忽略
                          </Button>
                          <Button
                            danger
                            loading={suppressionActionLoading === `reject:${row.id}`}
                            size="small"
                            type="link"
                            onClick={() => void handleSuppressionAction(row, 'reject')}
                          >
                            驳回
                          </Button>
                        </Space>
                      );
                    }
                    return (
                      <Button
                        loading={suppressionActionLoading === `request:${row.id}`}
                        size="small"
                        type="link"
                        onClick={() => void handleSuppressionAction(row, 'request')}
                      >
                        {status === 'rejected' ? '重新申请' : '申请忽略'}
                      </Button>
                    );
                  },
                },
              ]}
              dataSource={detailState.detail.findings}
              pagination={false}
              rowKey="id"
              scroll={{ x: 2050 }}
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
