import { Card, Col, Descriptions, Row, Space, Statistic, Table, Tag } from 'antd';
import type { ReactNode } from 'react';

import type { CodeInspectionDashboardRecord } from '../../../services/aiBrain';
import {
  committerLabel,
  compactText,
  riskColorByValue,
  severityColorByValue,
} from './codeInspectionPresentation';

function percentText(value?: number | null) {
  const normalized = typeof value === 'number' && Number.isFinite(value) ? value : 0;
  return `${Math.round(normalized * 100)}%`;
}

function severityTag(value?: string | null) {
  const text = value || '-';
  return <Tag color={severityColorByValue.get(text) ?? riskColorByValue.get(text) ?? 'default'}>{text}</Tag>;
}

function governanceStatusTag(value?: string | null) {
  const colorByStatus = new Map([
    ['action_required', 'red'],
    ['pending_review', 'orange'],
    ['healthy', 'green'],
  ]);
  const textByStatus = new Map([
    ['action_required', '待闭环'],
    ['pending_review', '待审批'],
    ['healthy', '健康'],
  ]);
  const text = value || '-';
  return <Tag color={colorByStatus.get(text) ?? 'default'}>{textByStatus.get(text) ?? text}</Tag>;
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

export function CodeInspectionGovernanceOverview({
  dashboard,
  loading,
}: {
  dashboard?: CodeInspectionDashboardRecord;
  loading: boolean;
}) {
  const summary = dashboard?.summary;
  const ruleGovernance = dashboard?.rule_governance;
  const governancePressure = dashboard?.governance_pressure;
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
      <Card loading={loading} size="small" title="治理压力总览">
        <Descriptions
          column={{ lg: 4, md: 2, xs: 1 }}
          items={[
            {
              key: 'status',
              label: '闭环状态',
              children: governanceStatusTag(governancePressure?.status),
            },
            {
              key: 'action_required_committers',
              label: '待闭环提交人',
              children: governancePressure?.action_required_committer_count ?? 0,
            },
            {
              key: 'action_required_branches',
              label: '待闭环分支',
              children: governancePressure?.action_required_branch_count ?? 0,
            },
            {
              key: 'pending_review_branches',
              label: '待审批分支',
              children: governancePressure?.pending_review_branch_count ?? 0,
            },
            {
              key: 'uncovered_bug',
              label: '缺 Bug',
              children: governancePressure?.uncovered_bug_finding_count ?? 0,
            },
            {
              key: 'uncovered_task',
              label: '缺整改任务',
              children: governancePressure?.uncovered_task_finding_count ?? 0,
            },
            {
              key: 'quality_gate_failed',
              label: '门禁失败报告',
              children: governancePressure?.quality_gate_failed_report_count ?? 0,
            },
            {
              key: 'quality_gate_violations',
              label: '门禁失败项',
              children: governancePressure?.quality_gate_violation_count ?? 0,
            },
            {
              key: 'expired_risk',
              label: '到期接受风险',
              children: governancePressure?.expired_accepted_risk_count ?? 0,
            },
            {
              key: 'pending_suppression',
              label: '待审批忽略',
              children: governancePressure?.pending_suppression_count ?? 0,
            },
          ]}
          size="small"
        />
      </Card>
      <Card loading={loading} size="small" title="规则包与误报治理">
        <Space orientation="vertical" size={12} style={{ width: '100%' }}>
          <Descriptions
            column={{ lg: 4, md: 2, xs: 1 }}
            items={[
              {
                key: 'rules_version',
                label: '最近规则版本',
                children: (
                  <Space wrap>
                    <span>{ruleGovernance?.latest_report_rules_version ?? '-'}</span>
                    {ruleGovernance?.mixed_rules_version ? <Tag color="orange">版本不一致</Tag> : null}
                  </Space>
                ),
              },
              {
                key: 'scanner_version',
                label: '最近扫描器版本',
                children: (
                  <Space wrap>
                    <span>{ruleGovernance?.latest_report_scanner_version ?? '-'}</span>
                    {ruleGovernance?.mixed_scanner_version ? <Tag color="orange">版本不一致</Tag> : null}
                  </Space>
                ),
              },
              {
                key: 'suppressed_count',
                label: '已过滤问题',
                children: ruleGovernance?.suppressed_finding_count ?? 0,
              },
              {
                key: 'expired_accepted_risk',
                label: '到期接受风险',
                children: ruleGovernance?.expired_accepted_risk_count ?? 0,
              },
              {
                key: 'suppressed_reports',
                label: '涉及报告',
                children: ruleGovernance?.report_with_suppression_count ?? 0,
              },
            ]}
            size="small"
          />
          <Row gutter={[12, 12]}>
            <Col lg={8} xs={24}>
              {compactMetricTable({
                columns: [
                  { dataIndex: 'rules_version', title: '规则版本', width: 180 },
                  { dataIndex: 'count', title: '报告数', width: 90 },
                ],
                dataSource: ruleGovernance?.rule_version_distribution ?? [],
                rowKey: 'rules_version',
              })}
            </Col>
            <Col lg={8} xs={24}>
              {compactMetricTable({
                columns: [
                  { dataIndex: 'scanner_version', title: '扫描器版本', width: 180 },
                  { dataIndex: 'count', title: '报告数', width: 90 },
                ],
                dataSource: ruleGovernance?.scanner_version_distribution ?? [],
                rowKey: 'scanner_version',
              })}
            </Col>
            <Col lg={8} xs={24}>
              {compactMetricTable({
                columns: [
                  { dataIndex: 'reason', title: '过滤原因', width: 160 },
                  { dataIndex: 'count', title: '数量', width: 90 },
                ],
                dataSource: ruleGovernance?.suppression_distribution ?? [],
                rowKey: 'reason',
              })}
            </Col>
          </Row>
        </Space>
      </Card>
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
        <Col lg={24} xs={24}>
          <Card loading={loading} size="small" title="分支治理待办">
            {compactMetricTable({
              columns: [
                { dataIndex: 'branch', title: '分支', width: 160 },
                {
                  dataIndex: 'repository_name',
                  render: (_, row) => compactText(String(row.repository_name ?? row.repository_id ?? '-')),
                  title: '仓库',
                  width: 220,
                },
                {
                  dataIndex: 'status',
                  render: (value) => governanceStatusTag(String(value ?? '')),
                  title: '状态',
                  width: 100,
                },
                { dataIndex: 'report_count', title: '报告', width: 80 },
                { dataIndex: 'active_severe_finding_count', title: '活跃严重', width: 110 },
                { dataIndex: 'uncovered_bug_finding_count', title: '缺 Bug', width: 90 },
                { dataIndex: 'uncovered_task_finding_count', title: '缺整改任务', width: 120 },
                { dataIndex: 'quality_gate_failed_report_count', title: '门禁失败报告', width: 130 },
                { dataIndex: 'quality_gate_violation_count', title: '门禁失败项', width: 120 },
                { dataIndex: 'pending_suppression_count', title: '待审批忽略', width: 120 },
                { dataIndex: 'expired_accepted_risk_count', title: '到期风险', width: 100 },
                {
                  dataIndex: 'latest_report_summary',
                  render: (_, row) => compactText(String(row.latest_report_summary ?? row.latest_report_id ?? '-')),
                  title: '最近报告',
                  width: 260,
                },
              ],
              dataSource: dashboard?.branch_governance ?? [],
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
        <Col lg={24} xs={24}>
          <Card loading={loading} size="small" title="提交人治理待办">
            {compactMetricTable({
              columns: [
                {
                  dataIndex: 'email',
                  render: (_, row) => compactText(committerLabel(row)),
                  title: '提交人',
                  width: 260,
                },
                {
                  dataIndex: 'status',
                  render: (value) => governanceStatusTag(String(value ?? '')),
                  title: '状态',
                  width: 100,
                },
                { dataIndex: 'report_count', title: '报告', width: 80 },
                { dataIndex: 'active_severe_finding_count', title: '活跃严重', width: 110 },
                { dataIndex: 'uncovered_bug_finding_count', title: '缺 Bug', width: 90 },
                { dataIndex: 'uncovered_task_finding_count', title: '缺整改任务', width: 120 },
                { dataIndex: 'pending_suppression_count', title: '待审批忽略', width: 120 },
                { dataIndex: 'accepted_risk_count', title: '已接受风险', width: 120 },
                { dataIndex: 'expired_accepted_risk_count', title: '到期风险', width: 100 },
                {
                  dataIndex: 'latest_report_summary',
                  render: (_, row) => compactText(String(row.latest_report_summary ?? row.latest_report_id ?? '-')),
                  title: '最近报告',
                  width: 260,
                },
              ],
              dataSource: dashboard?.committer_governance ?? [],
              rowKey: (row) => row.email ?? row.username ?? row.name ?? 'unknown',
            })}
          </Card>
        </Col>
      </Row>
      <Row gutter={[12, 12]}>
        <Col lg={14} xs={24}>
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
        </Col>
        <Col lg={10} xs={24}>
          <Card loading={loading} size="small" title="门禁失败原因">
            {compactMetricTable({
              columns: [
                { dataIndex: 'metric', title: '指标/规则', width: 170 },
                {
                  dataIndex: 'severity',
                  render: (value) => severityTag(String(value ?? '')),
                  title: '级别',
                  width: 100,
                },
                { dataIndex: 'violation_count', title: '触发', width: 90 },
                { dataIndex: 'report_count', title: '报告', width: 90 },
                {
                  dataIndex: 'actual',
                  render: (_, row) => `${row.actual ?? '-'} / ${row.limit ?? '-'}`,
                  title: '实际/阈值',
                  width: 120,
                },
                {
                  dataIndex: 'latest_report_summary',
                  render: (_, row) => compactText(String(row.latest_report_summary ?? row.latest_report_id ?? '-')),
                  title: '最近报告',
                  width: 220,
                },
              ],
              dataSource: dashboard?.quality_gate_violations ?? [],
              rowKey: 'metric',
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
