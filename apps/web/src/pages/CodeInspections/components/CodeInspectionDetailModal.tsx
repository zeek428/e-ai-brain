import { Button, Descriptions, Modal, Space, Table, Tag, Typography } from 'antd';

import { ExecutionTraceLink } from '../../../components/ExecutionTraceLink';
import {
  type CodeInspectionDetailRecord,
  type CodeInspectionFindingRecord,
  type CodeInspectionNotificationRecord,
  type CodeInspectionReportRecord,
} from '../../../services/aiBrain';
import { formatDisplayDateTime } from '../../../utils/dateTime';
import {
  bugLink,
  committerLabel,
  committerSummaryText,
  compactText,
  detailSingleLineText,
  findingProblemText,
  severityColorByValue,
  suppressionReasonText,
  suppressionStatusTag,
  taskLink,
} from './codeInspectionPresentation';

export type CodeInspectionDetailState = {
  detail?: CodeInspectionDetailRecord;
  loading: boolean;
  report?: CodeInspectionReportRecord;
};

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
  const hasIncrementalSnapshot =
    Boolean(report.incremental_from_commit) ||
    (report.incremental_file_count !== undefined && report.incremental_file_count !== null);
  const scanScope =
    hasIncrementalSnapshot
      ? '增量扫描'
      : report.is_full_scan === true
        ? '全量扫描'
        : '-';
  return [
    { key: 'scan_scope', label: '扫描范围', children: scanScope },
    { key: 'scan_mode', label: '扫描模式', children: compactText(report.scan_mode) },
    {
      key: 'incremental_from_commit',
      label: '增量基线 Commit',
      children: compactText(report.incremental_from_commit),
    },
    {
      key: 'incremental_file_count',
      label: '增量文件数',
      children: report.incremental_file_count ?? '-',
    },
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
      label: '任务推进',
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
      label: '待推进任务',
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
      key: 'expired_accepted_risk',
      label: '到期接受风险',
      children: `${governance?.expired_accepted_risk_count ?? 0} 个`,
    },
    {
      key: 'action_items',
      label: '治理待办',
      children: actionItems.length ? actionItems.map((item) => `${item.label} ${item.count ?? 0}`).join('；') : '-',
    },
  ];
}

type CodeInspectionDetailModalProps = {
  detailState?: CodeInspectionDetailState;
  onClose: () => void;
  onOpenAcceptedRisk: (finding: CodeInspectionFindingRecord) => void;
  onSuppressionAction: (finding: CodeInspectionFindingRecord, action: 'approve' | 'reject' | 'request') => void;
  suppressionActionLoading?: string;
};

export function CodeInspectionDetailModal({
  detailState,
  onClose,
  onOpenAcceptedRisk,
  onSuppressionAction,
  suppressionActionLoading,
}: CodeInspectionDetailModalProps) {
  const detail = detailState?.detail;
  return (
    <Modal
      aria-label="代码巡检详情"
      footer={<Button onClick={onClose}>关闭</Button>}
      open={Boolean(detailState)}
      title="代码巡检详情"
      width="min(1280px, calc(100vw - 48px))"
      onCancel={onClose}
    >
      {detailState?.loading ? (
        <Typography.Text type="secondary">详情加载中...</Typography.Text>
      ) : detail ? (
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Descriptions
            bordered
            column={2}
            size="small"
            items={[
              { key: 'id', label: '报告 ID', children: detail.report.id },
              { key: 'risk', label: '风险级别', children: detail.report.risk_level },
              { key: 'repository', label: '仓库', children: detail.report.repository_name || '-' },
              { key: 'branch', label: '分支', children: detail.report.branch || '-' },
              { key: 'committer_count', label: '提交人数', children: detail.report.committer_count ?? 0 },
              {
                key: 'committers',
                label: '主要提交人',
                children: committerSummaryText(detail.report),
              },
              { key: 'finding_count', label: '问题数', children: detail.report.finding_count },
              { key: 'severe_count', label: '严重问题', children: detail.report.severe_finding_count },
              { key: 'bugs', label: '创建 Bug', children: detail.report.created_bug_ids?.join('、') || '-' },
              { key: 'tasks', label: '已推进任务', children: detail.report.created_task_ids?.join('、') || '-' },
              { key: 'summary', label: '摘要', children: detail.report.summary || '-' },
            ]}
          />
          <Descriptions bordered column={2} items={sourceTraceItems(detail.report)} size="small" title="来源链路" />
          <Descriptions bordered column={2} items={scanSnapshotItems(detail.report)} size="small" title="扫描快照" />
          <Descriptions bordered column={2} items={scanSummaryItems(detail)} size="small" title="扫描摘要" />
          <Descriptions
            bordered
            column={3}
            items={codeInspectionGovernanceItems(detail)}
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
            dataSource={detail.scan_summary?.rule_distribution ?? []}
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
            dataSource={detail.scan_summary?.file_distribution ?? []}
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
                title: 'AI Task',
                width: 150,
                render: (value) => taskLink(String(value ?? '')),
              },
              {
                dataIndex: 'suppression_status',
                title: '忽略审批',
                width: 190,
                render: (_, row) => (
                  <Space orientation="vertical" size={2}>
                    {suppressionStatusTag(row.suppression_status, row.suppression_reason)}
                    {row.suppression_reason ? (
                      <Typography.Text type="secondary">
                        {suppressionReasonText(row.suppression_reason)}
                      </Typography.Text>
                    ) : null}
                    {row.suppression_owner ? (
                      <Typography.Text type="secondary">
                        责任人：{row.suppression_owner}
                      </Typography.Text>
                    ) : null}
                    {row.suppression_expires_at ? (
                      <Typography.Text type="secondary">
                        到期：{formatDisplayDateTime(row.suppression_expires_at)}
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
                    return <Typography.Text type="secondary">已治理</Typography.Text>;
                  }
                  if (status === 'pending') {
                    return (
                      <Space size={4}>
                        <Button
                          loading={suppressionActionLoading === `approve:${row.id}`}
                          size="small"
                          type="link"
                          onClick={() => void onSuppressionAction(row, 'approve')}
                        >
                          批准忽略
                        </Button>
                        <Button
                          danger
                          loading={suppressionActionLoading === `reject:${row.id}`}
                          size="small"
                          type="link"
                          onClick={() => void onSuppressionAction(row, 'reject')}
                        >
                          驳回
                        </Button>
                      </Space>
                    );
                  }
                  return (
                    <Space size={4}>
                      <Button
                        loading={suppressionActionLoading === `request:${row.id}`}
                        size="small"
                        type="link"
                        onClick={() => void onSuppressionAction(row, 'request')}
                      >
                        {status === 'rejected' ? '重新申请误报' : '申请误报'}
                      </Button>
                      <Button size="small" type="link" onClick={() => onOpenAcceptedRisk(row)}>
                        接受风险
                      </Button>
                    </Space>
                  );
                },
              },
            ]}
            dataSource={detail.findings}
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
            dataSource={detail.notifications}
            pagination={false}
            rowKey="id"
            size="small"
          />
        </Space>
      ) : null}
    </Modal>
  );
}
