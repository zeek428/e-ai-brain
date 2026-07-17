import { Alert, Card, Col, Descriptions, Row, Space, Statistic, Table, Tabs, Tag, Typography } from 'antd';
import type { ReactNode } from 'react';

import type { CodeInspectionDashboardRecord } from '../../../services/aiBrain';
import {
  committerLabel,
  compactText,
  riskColorByValue,
  severityColorByValue,
} from './codeInspectionPresentation';

const { Text } = Typography;

function percentText(value?: number | null) {
  const normalized = typeof value === 'number' && Number.isFinite(value) ? value : 0;
  return `${Math.round(normalized * 100)}%`;
}

function metricValue(value?: number | null) {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
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

function countTag(label: string, value: unknown, color = 'orange') {
  const count = metricValue(typeof value === 'number' ? value : Number(value));
  return <Tag color={count > 0 ? color : 'default'}>{`${label} ${count}`}</Tag>;
}

function issueGapTags(row: Record<string, unknown>) {
  return (
    <Space className="code-inspection-table-tags" size={[4, 4]} wrap>
      {countTag('缺 Bug', row.uncovered_bug_finding_count, 'red')}
      {countTag('缺整改需求', row.uncovered_requirement_finding_count, 'orange')}
    </Space>
  );
}

function qualityGateTags(row: Record<string, unknown>) {
  return (
    <Space className="code-inspection-table-tags" size={[4, 4]} wrap>
      {countTag('报告', row.quality_gate_failed_report_count, 'red')}
      {countTag('失败项', row.quality_gate_violation_count, 'red')}
    </Space>
  );
}

function suppressionRiskTags(row: Record<string, unknown>) {
  return (
    <Space className="code-inspection-table-tags" size={[4, 4]} wrap>
      {countTag('待审批', row.pending_suppression_count, 'gold')}
      {countTag('已接受风险', row.accepted_risk_count, 'blue')}
      {countTag('到期风险', row.expired_accepted_risk_count, 'orange')}
    </Space>
  );
}

function pressureStatusMetric(value?: string | null) {
  const isHealthy = value === 'healthy';
  return (
    <div
      className={
        isHealthy
          ? 'code-inspection-pressure-item is-status'
          : 'code-inspection-pressure-item is-status is-active'
      }
    >
      <Text type="secondary">闭环状态</Text>
      <strong>{isHealthy ? '健康' : '待处理'}</strong>
      {governanceStatusTag(value)}
    </div>
  );
}

function pressureMetric(label: string, value: unknown, color = 'orange') {
  const count = metricValue(typeof value === 'number' ? value : Number(value));
  return (
    <div className={count > 0 ? 'code-inspection-pressure-item is-active' : 'code-inspection-pressure-item'}>
      <Text type="secondary">{label}</Text>
      <strong>{count}</strong>
      <Tag color={count > 0 ? color : 'default'}>{count > 0 ? '待处理' : '无'}</Tag>
    </div>
  );
}

function emptyRiskList() {
  return <Text type="secondary">暂无数据</Text>;
}

function compactRiskListItem({
  count,
  countLabel,
  itemKey,
  meta,
  tags,
  title,
}: {
  count: number;
  countLabel: string;
  itemKey: string;
  meta?: ReactNode;
  tags?: ReactNode;
  title: string;
}) {
  return (
    <div className="code-inspection-risk-list-item" key={itemKey}>
      <Space className="code-inspection-risk-list-main" orientation="vertical" size={4}>
        <Text className="code-inspection-risk-list-title" ellipsis={{ tooltip: title }} strong>
          {title}
        </Text>
        {meta ? <div className="code-inspection-risk-list-meta">{meta}</div> : null}
        {tags ? (
          <Space className="code-inspection-risk-list-tags" size={[4, 4]} wrap>
            {tags}
          </Space>
        ) : null}
      </Space>
      <div className="code-inspection-risk-list-count">
        <strong>{count}</strong>
        <Text type="secondary">{countLabel}</Text>
      </div>
    </div>
  );
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
  const scrollX = columns.reduce((total, column) => total + (column.width ?? 140), 0);
  return (
    <Table<Row>
      className="code-inspection-metric-table"
      columns={columns}
      dataSource={dataSource}
      pagination={false}
      rowKey={rowKey}
      scroll={{ x: scrollX }}
      size="small"
      tableLayout="fixed"
    />
  );
}

type CodeInspectionGovernanceConclusion = {
  detail: string;
  level: 'error' | 'info' | 'success' | 'warning';
  nextAction: string;
  risks: string[];
  value: string;
};

function buildCodeInspectionGovernanceConclusion(
  dashboard?: CodeInspectionDashboardRecord,
): CodeInspectionGovernanceConclusion {
  const summary = dashboard?.summary;
  const governancePressure = dashboard?.governance_pressure;
  const ruleGovernance = dashboard?.rule_governance;
  const sla = dashboard?.sla;
  const reportCount = metricValue(summary?.report_count);
  const severeFindingCount = metricValue(summary?.severe_finding_count);
  const failedReportCount = metricValue(governancePressure?.quality_gate_failed_report_count);
  const qualityGateViolationCount = metricValue(governancePressure?.quality_gate_violation_count);
  const actionRequiredBranchCount = metricValue(governancePressure?.action_required_branch_count);
  const actionRequiredCommitterCount = metricValue(governancePressure?.action_required_committer_count);
  const uncoveredBugCount = metricValue(governancePressure?.uncovered_bug_finding_count);
  const uncoveredRequirementCount = metricValue(governancePressure?.uncovered_requirement_finding_count);
  const pendingSuppressionCount = metricValue(governancePressure?.pending_suppression_count);
  const pendingReviewCount =
    metricValue(governancePressure?.pending_review_branch_count) +
    metricValue(governancePressure?.pending_review_committer_count);
  const expiredAcceptedRiskCount = Math.max(
    metricValue(governancePressure?.expired_accepted_risk_count),
    metricValue(ruleGovernance?.expired_accepted_risk_count),
  );

  if (!dashboard || (reportCount === 0 && severeFindingCount === 0)) {
    return {
      detail: '当前筛选范围暂无巡检报告。',
      level: 'info',
      nextAction: '先创建或运行代码仓库巡检作业，再回到本页查看治理结论。',
      risks: ['暂无报告'],
      value: '暂无巡检数据',
    };
  }

  const risks = [
    failedReportCount > 0 ? `门禁失败报告 ${failedReportCount}` : undefined,
    qualityGateViolationCount > 0 ? `门禁失败项 ${qualityGateViolationCount}` : undefined,
    actionRequiredBranchCount > 0 ? `待闭环分支 ${actionRequiredBranchCount}` : undefined,
    actionRequiredCommitterCount > 0 ? `待闭环提交人 ${actionRequiredCommitterCount}` : undefined,
    uncoveredBugCount > 0 ? `缺 Bug ${uncoveredBugCount}` : undefined,
    pendingSuppressionCount + pendingReviewCount > 0
      ? `待审批忽略 ${pendingSuppressionCount + pendingReviewCount}`
      : undefined,
    expiredAcceptedRiskCount > 0 ? `到期接受风险 ${expiredAcceptedRiskCount}` : undefined,
  ].filter((item): item is string => Boolean(item));

  if (!risks.length) {
    risks.push(`Bug 覆盖率 ${percentText(sla?.bug_coverage_rate)}`);
    risks.push(`整改需求覆盖率 ${percentText(sla?.requirement_coverage_rate)}`);
  }

  const detail = `当前范围有 ${reportCount} 份巡检报告、${severeFindingCount} 个严重问题，门禁失败报告 ${failedReportCount} 份、失败项 ${qualityGateViolationCount} 个，缺 Bug ${uncoveredBugCount} 个、待建整改需求 ${uncoveredRequirementCount} 个。`;

  if (failedReportCount > 0 || qualityGateViolationCount > 0) {
    return {
      detail,
      level: 'error',
      nextAction: '先查看“门禁失败原因”和最近失败报告，完成修复或风险接受后再重跑巡检。',
      risks,
      value: '优先处理质量门禁失败',
    };
  }
  if (actionRequiredBranchCount > 0) {
    return {
      detail,
      level: 'warning',
      nextAction: '先处理“分支治理待办”中的待闭环分支，确认 Bug、风险接受，并补齐整改需求后进入评估协作。',
      risks,
      value: '优先处理分支治理待办',
    };
  }
  if (actionRequiredCommitterCount > 0) {
    return {
      detail,
      level: 'warning',
      nextAction: '先处理“提交人治理待办”中的责任人闭环，补齐缺失 Bug、整改需求或忽略审批。',
      risks,
      value: '优先处理提交人治理待办',
    };
  }
  if (uncoveredBugCount > 0) {
    return {
      detail,
      level: 'warning',
      nextAction: '先为严重问题补齐 Bug，并为需要整改的问题创建正式需求。',
      risks,
      value: '优先补齐 Bug',
    };
  }
  if (pendingSuppressionCount + pendingReviewCount > 0) {
    return {
      detail,
      level: 'warning',
      nextAction: '先审批待处理的误报忽略或接受风险申请，避免治理状态长期停留在待确认。',
      risks,
      value: '优先审批忽略申请',
    };
  }
  if (expiredAcceptedRiskCount > 0) {
    return {
      detail,
      level: 'warning',
      nextAction: '先复核已到期的接受风险，重新评估继续接受、转 Bug 或安排整改。',
      risks,
      value: '复核到期接受风险',
    };
  }
  if (severeFindingCount > 0) {
    return {
      detail,
      level: 'info',
      nextAction: '严重问题已完成基础覆盖，继续观察趋势并保持定期巡检。',
      risks,
      value: '严重问题已覆盖',
    };
  }
  return {
    detail,
    level: 'success',
    nextAction: '当前范围暂无优先治理项，可以继续保持定期巡检和趋势观察。',
    risks,
    value: '巡检治理健康',
  };
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
  const governanceConclusion = buildCodeInspectionGovernanceConclusion(dashboard);
  const reportCount = metricValue(summary?.report_count);
  const findingCount = metricValue(summary?.finding_count);
  const severeFindingCount = metricValue(summary?.severe_finding_count);
  const actionRequiredBranchCount = metricValue(governancePressure?.action_required_branch_count);
  const actionRequiredCommitterCount = metricValue(governancePressure?.action_required_committer_count);
  const pendingReviewCount =
    metricValue(governancePressure?.pending_review_branch_count) +
    metricValue(governancePressure?.pending_review_committer_count);
  const qualityGateIssueCount =
    metricValue(governancePressure?.quality_gate_failed_report_count) +
    metricValue(governancePressure?.quality_gate_violation_count);
  const openGovernanceCount =
    actionRequiredBranchCount +
    actionRequiredCommitterCount +
    pendingReviewCount +
    qualityGateIssueCount +
    metricValue(governancePressure?.pending_suppression_count) +
    metricValue(governancePressure?.expired_accepted_risk_count);
  const coverageStatusColor = sla?.status === 'healthy' ? 'green' : 'orange';
  const branchRanking = dashboard?.branch_ranking ?? [];
  const committerRanking = dashboard?.committer_ranking ?? [];
  const repositoryRanking = dashboard?.repository_ranking ?? [];
  const ruleDistribution = dashboard?.rule_distribution ?? [];

  return (
    <Space className="code-inspection-governance-overview" orientation="vertical" size={12}>
      <Alert
        className="code-inspection-decision-panel"
        description={
          <Space orientation="vertical" size={8} style={{ width: '100%' }}>
            <Space className="code-inspection-risk-tags" size={[6, 6]} wrap>
              {governanceConclusion.risks.map((risk) => (
                <Tag key={risk}>{risk}</Tag>
              ))}
            </Space>
            <Text className="code-inspection-decision-next-action" type="secondary">
              {`下一步动作：${governanceConclusion.nextAction}`}
            </Text>
            <details className="code-inspection-decision-details">
              <summary>查看治理依据</summary>
              <div className="code-inspection-decision-detail-body">
                <Text>{governanceConclusion.detail}</Text>
              </div>
            </details>
          </Space>
        }
        title={
          <Space size={8} wrap>
            <Text strong>代码巡检治理结论</Text>
            <Tag color={governanceConclusion.level === 'error' ? 'red' : governanceConclusion.level}>
              {governanceConclusion.value}
            </Tag>
          </Space>
        }
        showIcon
        type={governanceConclusion.level}
      />
      <Row className="code-inspection-kpi-row" gutter={[12, 12]}>
        <Col lg={6} md={12} xs={12}>
          <Card className="code-inspection-kpi-card" loading={loading} size="small">
            <Statistic title="巡检报告" value={reportCount} />
            <Text type="secondary">{`发现问题 ${findingCount}`}</Text>
          </Card>
        </Col>
        <Col lg={6} md={12} xs={12}>
          <Card className="code-inspection-kpi-card" loading={loading} size="small">
            <Statistic title="严重问题" value={severeFindingCount} />
            <Text type="secondary">{`严重阈值 ${sla?.severe_threshold ?? '-'}`}</Text>
          </Card>
        </Col>
        <Col lg={6} md={12} xs={12}>
          <Card className="code-inspection-kpi-card" loading={loading} size="small">
            <Statistic
              suffix={<Tag color={coverageStatusColor}>整体 {sla?.status ?? '-'}</Tag>}
              title="Bug 覆盖率"
              value={percentText(sla?.bug_coverage_rate)}
            />
            <Text type="secondary">{`整改需求 ${percentText(sla?.requirement_coverage_rate)}`}</Text>
          </Card>
        </Col>
        <Col lg={6} md={12} xs={12}>
          <Card className="code-inspection-kpi-card" loading={loading} size="small">
            <Statistic
              suffix={<Tag color={openGovernanceCount > 0 ? 'orange' : 'green'}>待处理</Tag>}
              title="治理待办"
              value={openGovernanceCount}
            />
            <Text type="secondary">{`分支 ${actionRequiredBranchCount} / 提交人 ${actionRequiredCommitterCount}`}</Text>
          </Card>
        </Col>
      </Row>
      <Tabs
        className="code-inspection-governance-tabs"
        defaultActiveKey="todo"
        items={[
          {
            key: 'todo',
            label: '治理待办',
            children: (
              <Space className="code-inspection-governance-tab-pane" orientation="vertical" size={12}>
                <Card loading={loading} size="small" title="治理压力总览">
                  <div className="code-inspection-pressure-grid">
                    {pressureStatusMetric(governancePressure?.status)}
                    {pressureMetric('待闭环提交人', governancePressure?.action_required_committer_count)}
                    {pressureMetric('待闭环分支', governancePressure?.action_required_branch_count)}
                    {pressureMetric('待审批分支', governancePressure?.pending_review_branch_count, 'gold')}
                    {pressureMetric('待审批忽略', governancePressure?.pending_suppression_count, 'gold')}
                    {pressureMetric('缺 Bug', governancePressure?.uncovered_bug_finding_count, 'red')}
                    {pressureMetric('待建整改需求', governancePressure?.uncovered_requirement_finding_count)}
                    {pressureMetric('门禁失败报告', governancePressure?.quality_gate_failed_report_count, 'red')}
                    {pressureMetric('门禁失败项', governancePressure?.quality_gate_violation_count, 'red')}
                    {pressureMetric('到期接受风险', governancePressure?.expired_accepted_risk_count)}
                  </div>
                </Card>
                <Row gutter={[12, 12]}>
                  <Col lg={24} xs={24}>
                    <Card loading={loading} size="small" title="分支治理待办">
                      {compactMetricTable({
                        columns: [
                          { dataIndex: 'branch', title: '分支', width: 140 },
                          {
                            dataIndex: 'repository_name',
                            render: (_, row) => compactText(String(row.repository_name ?? row.repository_id ?? '-')),
                            title: '仓库',
                            width: 210,
                          },
                          {
                            dataIndex: 'status',
                            render: (value) => governanceStatusTag(String(value ?? '')),
                            title: '状态',
                            width: 100,
                          },
                          { dataIndex: 'report_count', title: '报告', width: 80 },
                          { dataIndex: 'active_severe_finding_count', title: '活跃严重', width: 110 },
                          {
                            dataIndex: 'uncovered_bug_finding_count',
                            render: (_, row) => issueGapTags(row),
                            title: '闭环缺口',
                            width: 170,
                          },
                          {
                            dataIndex: 'quality_gate_failed_report_count',
                            render: (_, row) => qualityGateTags(row),
                            title: '门禁',
                            width: 150,
                          },
                          {
                            dataIndex: 'pending_suppression_count',
                            render: (_, row) => suppressionRiskTags(row),
                            title: '忽略/风险',
                            width: 220,
                          },
                          {
                            dataIndex: 'latest_report_summary',
                            render: (_, row) =>
                              compactText(String(row.latest_report_summary ?? row.latest_report_id ?? '-')),
                            title: '最近报告',
                            width: 360,
                          },
                        ],
                        dataSource: dashboard?.branch_governance ?? [],
                        rowKey: (row) => `${row.repository_id ?? row.repository_name ?? '-'}:${row.branch ?? '-'}`,
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
                          {
                            dataIndex: 'uncovered_bug_finding_count',
                            render: (_, row) => issueGapTags(row),
                            title: '闭环缺口',
                            width: 170,
                          },
                          {
                            dataIndex: 'pending_suppression_count',
                            render: (_, row) => suppressionRiskTags(row),
                            title: '忽略/风险',
                            width: 220,
                          },
                          {
                            dataIndex: 'latest_report_summary',
                            render: (_, row) =>
                              compactText(String(row.latest_report_summary ?? row.latest_report_id ?? '-')),
                            title: '最近报告',
                            width: 360,
                          },
                        ],
                        dataSource: dashboard?.committer_governance ?? [],
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
                      { key: 'requirement_covered', label: '已建整改需求', children: sla?.covered_by_requirement_count ?? 0 },
                      { key: 'requirement_uncovered', label: '待建整改需求', children: sla?.uncovered_requirement_finding_count ?? 0 },
                      { key: 'requirement_oldest', label: '最早待建整改需求', children: sla?.oldest_without_requirement_at ?? '-' },
                      { key: 'historical_task_covered', label: '历史 AI Task', children: sla?.historical_covered_by_task_count ?? 0 },
                    ]}
                    size="small"
                  />
                </Card>
              </Space>
            ),
          },
          {
            key: 'risk',
            label: '风险分布',
            children: (
              <Row className="code-inspection-governance-tab-pane" gutter={[12, 12]}>
                <Col lg={12} xs={24}>
                  <Card loading={loading} size="small" title="规则维度统计">
                    {ruleDistribution.length ? (
                      <div className="code-inspection-risk-list">
                        {ruleDistribution.slice(0, 5).map((row) =>
                          compactRiskListItem({
                            count: metricValue(row.finding_count),
                            countLabel: '问题',
                            itemKey: row.rule_id,
                            meta: <Text type="secondary">{row.category || '-'}</Text>,
                            tags: (
                              <>
                                {severityTag(row.severity)}
                                <Tag color={metricValue(row.severe_finding_count) > 0 ? 'red' : 'default'}>
                                  严重 {metricValue(row.severe_finding_count)}
                                </Tag>
                              </>
                            ),
                            title: row.rule_id,
                          }),
                        )}
                      </div>
                    ) : (
                      emptyRiskList()
                    )}
                  </Card>
                </Col>
                <Col lg={12} xs={24}>
                  <Card loading={loading} size="small" title="仓库风险排行">
                    {repositoryRanking.length ? (
                      <div className="code-inspection-risk-list">
                        {repositoryRanking.slice(0, 5).map((row) =>
                          compactRiskListItem({
                            count: metricValue(row.finding_count),
                            countLabel: '问题',
                            itemKey: row.repository_id || row.repository_name || '-',
                            meta: (
                              <Text type="secondary">
                                {`报告 ${metricValue(row.report_count)} / 严重 ${metricValue(row.severe_finding_count)}`}
                              </Text>
                            ),
                            tags: severityTag(row.risk_level),
                            title: row.repository_name || row.repository_id || '-',
                          }),
                        )}
                      </div>
                    ) : (
                      emptyRiskList()
                    )}
                  </Card>
                </Col>
                <Col lg={12} xs={24}>
                  <Card loading={loading} size="small" title="分支风险排行">
                    {branchRanking.length ? (
                      <div className="code-inspection-risk-list">
                        {branchRanking.slice(0, 5).map((row) =>
                          compactRiskListItem({
                            count: metricValue(row.finding_count),
                            countLabel: '问题',
                            itemKey: `${row.repository_id ?? row.repository_name ?? '-'}:${row.branch ?? '-'}`,
                            meta: (
                              <Text type="secondary">
                                {`${row.repository_name || row.repository_id || '-'} / 严重 ${metricValue(
                                  row.severe_finding_count,
                                )}`}
                              </Text>
                            ),
                            tags: <Tag>报告 {metricValue(row.report_count)}</Tag>,
                            title: row.branch || '-',
                          }),
                        )}
                      </div>
                    ) : (
                      emptyRiskList()
                    )}
                  </Card>
                </Col>
                <Col lg={12} xs={24}>
                  <Card loading={loading} size="small" title="提交人风险排行">
                    {committerRanking.length ? (
                      <div className="code-inspection-risk-list">
                        {committerRanking.slice(0, 5).map((row) =>
                          compactRiskListItem({
                            count: metricValue(row.finding_count),
                            countLabel: '问题',
                            itemKey: row.email || row.username || row.name || 'unknown',
                            meta: (
                              <Text type="secondary">
                                {`严重 ${metricValue(row.severe_finding_count)} / Bug ${metricValue(row.bug_count)}`}
                              </Text>
                            ),
                            title: committerLabel(row),
                          }),
                        )}
                      </div>
                    ) : (
                      emptyRiskList()
                    )}
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'quality',
            label: '趋势与规则',
            children: (
              <Space className="code-inspection-governance-tab-pane" orientation="vertical" size={12}>
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
                            render: (_, row) =>
                              compactText(String(row.latest_report_summary ?? row.latest_report_id ?? '-')),
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
              </Space>
            ),
          },
        ]}
      />
    </Space>
  );
}
