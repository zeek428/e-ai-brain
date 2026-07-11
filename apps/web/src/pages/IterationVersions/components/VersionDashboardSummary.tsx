import {
  ArrowRightOutlined,
  CheckCircleOutlined,
  CodeOutlined,
  EyeOutlined,
  LinkOutlined,
  PauseCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { Alert, Button, Progress, Space, Tag, Typography } from 'antd';
import type { ReactNode } from 'react';

import type { ProductVersionRecord } from '../../../data/management';
import {
  fullChainSubjectHref,
  type ProductVersionDashboard,
} from '../../../services/aiBrain';
import {
  buildDashboardActionQueue,
  dashboardHealthLevelLabels,
  internalHref,
  summarizeBranchQualityGovernance,
  type DashboardGovernanceConclusion,
  type DashboardHealthItem,
  type DashboardReadinessItem,
  type LabelItem,
} from './versionDashboardModel';

const { Text } = Typography;

const evidenceStatusLabels: Record<string, LabelItem> = {
  blocked: { color: 'red', label: '阻断' },
  covered: { color: 'green', label: '已覆盖' },
  inaccessible: { color: 'gold', label: '权限不足' },
  missing: { color: 'gold', label: '待补齐' },
  not_applicable: { color: 'default', label: '不适用' },
  risk: { color: 'orange', label: '待治理' },
};

type VersionDashboardActionsProps = {
  dashboard: ProductVersionDashboard;
  onAdvanceVersion: (version: ProductVersionRecord) => void;
  onMaintainBranches: (version: ProductVersionRecord) => void;
  onViewRequirements: (version: ProductVersionRecord) => void;
  versionStatusLabels: Record<ProductVersionRecord['status'], LabelItem>;
};

export function VersionDashboardActions({
  dashboard,
  onAdvanceVersion,
  onMaintainBranches,
  onViewRequirements,
  versionStatusLabels,
}: VersionDashboardActionsProps) {
  const priorityActions = buildDashboardActionQueue(dashboard).slice(0, 3);

  return (
    <div>
      <Text strong>下一步行动</Text>
      <Space size={8} style={{ display: 'flex', marginTop: 8 }} wrap>
        <Button
          disabled={!dashboard.statusImpact}
          icon={<ArrowRightOutlined />}
          onClick={() => onAdvanceVersion(dashboard.version)}
        >
          {dashboard.statusImpact
            ? `推进到${versionStatusLabels[dashboard.statusImpact.targetStatus].label}`
            : '推进状态'}
        </Button>
        <Button
          icon={<EyeOutlined />}
          onClick={() => onViewRequirements(dashboard.version)}
        >
          查看需求
        </Button>
        <Button
          icon={<CodeOutlined />}
          onClick={() => onMaintainBranches(dashboard.version)}
        >
          维护分支
        </Button>
        <Button
          href={internalHref('/delivery/bugs', {
            version_id: dashboard.version.id,
          })}
        >
          查看 Bug
        </Button>
        <Button
          href={internalHref('/governance/code-inspections', {
            version_id: dashboard.version.id,
          })}
        >
          代码巡检
        </Button>
        <Button
          href={internalHref('/governance/deployments', {
            version_id: dashboard.version.id,
          })}
        >
          运维部署
        </Button>
        <Button
          href={internalHref('/governance/devops', {
            version_id: dashboard.version.id,
          })}
        >
          发布记录
        </Button>
        <Button
          href={fullChainSubjectHref('product_version', dashboard.version.id)}
          icon={<LinkOutlined />}
        >
          版本全链路
        </Button>
      </Space>
      {priorityActions.length ? (
        <div
          style={{
            border: '1px solid #ffccc7',
            borderRadius: 6,
            marginTop: 12,
            padding: 12,
          }}
        >
          <Space align="center" style={{ display: 'flex', marginBottom: 8 }} wrap>
            <Text strong>优先处理建议</Text>
            <Tag color="red">{dashboard.summary.blockers} 个阻塞项</Tag>
          </Space>
          <Space size={8} style={{ display: 'flex' }} wrap>
            {priorityActions.map((item) => (
              <div
                key={`${item.sourceType}-${item.id ?? item.title}-priority`}
                style={{
                  border: '1px solid #f0f0f0',
                  borderRadius: 6,
                  minHeight: 118,
                  padding: '8px 10px',
                  width: 270,
                }}
              >
                <Space size={4} style={{ display: 'flex' }} wrap>
                  <Tag color="blue">优先级 {item.priority}</Tag>
                  <Tag color={item.severity === 'high' ? 'red' : 'gold'}>
                    {item.sourceLabel}
                  </Tag>
                </Space>
                <div style={{ marginTop: 6 }}>
                  <Text strong ellipsis style={{ maxWidth: 238 }}>
                    {String(item.title ?? '-')}
                  </Text>
                </div>
                <div style={{ marginTop: 4 }}>
                  <Text type="secondary">{String(item.reason ?? '-')}</Text>
                </div>
                <Space size={4} style={{ marginTop: 6 }} wrap>
                  {item.actionHref ? (
                    <Button
                      href={item.actionHref}
                      icon={<ArrowRightOutlined />}
                      size="small"
                      type="link"
                    >
                      {item.actionLabel}
                    </Button>
                  ) : null}
                  {item.fullChainHref ? (
                    <Button
                      href={item.fullChainHref}
                      icon={<LinkOutlined />}
                      size="small"
                      type="link"
                    >
                      全链路
                    </Button>
                  ) : null}
                </Space>
              </div>
            ))}
          </Space>
        </div>
      ) : null}
    </div>
  );
}

function dashboardMetric(label: string, value: number, color?: string) {
  return (
    <div
      key={label}
      style={{
        border: '1px solid #f0f0f0',
        borderRadius: 6,
        minWidth: 112,
        padding: '8px 12px',
      }}
    >
      <Text type="secondary">{label}</Text>
      <div style={{ color, fontSize: 20, fontWeight: 600, lineHeight: 1.4 }}>
        {value}
      </div>
    </div>
  );
}

type VersionDashboardMetricsProps = {
  dashboard: ProductVersionDashboard;
};

type VersionDashboardEvidenceCoverageProps = {
  dashboard: ProductVersionDashboard;
};

type VersionDashboardGovernanceConclusionProps = {
  conclusion?: DashboardGovernanceConclusion;
};

export function VersionDashboardGovernanceConclusion({
  conclusion,
}: VersionDashboardGovernanceConclusionProps) {
  if (!conclusion) {
    return null;
  }
  const level = dashboardHealthLevelLabels[conclusion.level];
  const alertType =
    conclusion.level === 'error'
      ? 'error'
      : conclusion.level === 'warning'
        ? 'warning'
        : conclusion.level === 'success'
          ? 'success'
          : 'info';

  return (
    <Alert
      description={
        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
          <Text>{conclusion.detail}</Text>
          <Space size={[6, 6]} wrap>
            <Tag color={level.color}>{level.label}</Tag>
            {conclusion.risks.map((risk) => (
              <Tag key={risk}>{risk}</Tag>
            ))}
          </Space>
          <Text strong>下一步动作：{conclusion.nextAction}</Text>
        </Space>
      }
      title={
        <Space size={8} wrap>
          <Text strong>{conclusion.title}</Text>
          <Text>{conclusion.value}</Text>
        </Space>
      }
      showIcon
      type={alertType}
    />
  );
}

export function VersionDashboardMetrics({
  dashboard,
}: VersionDashboardMetricsProps) {
  const severeRiskCount =
    dashboard.summary.severe_bugs +
    dashboard.summary.severe_code_inspection_reports;
  const branchQuality = summarizeBranchQualityGovernance(dashboard);
  return (
    <Space size={12} wrap>
      {dashboardMetric('需求', dashboard.summary.requirements)}
      {dashboardMetric('AI 任务', dashboard.summary.tasks)}
      {dashboardMetric('代码分支', dashboard.summary.branch_configs)}
      {dashboardMetric(
        'Bug',
        dashboard.summary.bugs,
        dashboard.summary.open_bugs ? '#cf1322' : undefined,
      )}
      {dashboardMetric(
        '未关闭 Bug',
        dashboard.summary.open_bugs,
        dashboard.summary.open_bugs ? '#cf1322' : undefined,
      )}
      {dashboardMetric(
        '严重风险',
        severeRiskCount,
        severeRiskCount ? '#cf1322' : undefined,
      )}
      {dashboardMetric('代码巡检', dashboard.summary.code_inspection_reports)}
      {dashboardMetric(
        '待治理分支',
        branchQuality.actionRequiredBranchCount,
        branchQuality.actionRequiredBranchCount ? '#cf1322' : undefined,
      )}
      {dashboardMetric(
        '门禁失败',
        branchQuality.qualityGateFailedReportCount,
        branchQuality.qualityGateFailedReportCount ? '#cf1322' : undefined,
      )}
      {dashboardMetric(
        '待审批忽略',
        branchQuality.pendingSuppressionCount,
        branchQuality.pendingSuppressionCount ? '#d48806' : undefined,
      )}
      {dashboardMetric(
        '到期风险',
        branchQuality.expiredAcceptedRiskCount,
        branchQuality.expiredAcceptedRiskCount ? '#cf1322' : undefined,
      )}
      {dashboardMetric('代码评审', dashboard.summary.code_review_reports)}
      {dashboardMetric('知识沉淀', dashboard.summary.knowledge_deposits)}
      {dashboardMetric(
        '待确认评审',
        dashboard.summary.pending_code_review_reports,
        dashboard.summary.pending_code_review_reports ? '#d48806' : undefined,
      )}
      {dashboardMetric('运维部署', dashboard.summary.deployments)}
      {dashboardMetric(
        '成功部署',
        dashboard.summary.successful_deployments,
        dashboard.summary.successful_deployments ? '#389e0d' : undefined,
      )}
      {dashboardMetric(
        '失败部署',
        dashboard.summary.failed_deployments,
        dashboard.summary.failed_deployments ? '#cf1322' : undefined,
      )}
      {dashboardMetric('发布记录', dashboard.summary.releases)}
      {dashboardMetric(
        '成功发布',
        dashboard.summary.successful_releases,
        dashboard.summary.successful_releases ? '#389e0d' : undefined,
      )}
      {dashboardMetric(
        '失败发布',
        dashboard.summary.failed_releases,
        dashboard.summary.failed_releases ? '#cf1322' : undefined,
      )}
      {dashboardMetric(
        '阻塞项',
        dashboard.summary.blockers,
        dashboard.summary.blockers ? '#cf1322' : undefined,
      )}
    </Space>
  );
}

function evidenceActionHref(
  domain: ProductVersionDashboard['evidenceCoverage']['domains'][number],
  versionId: string,
) {
  const targetId = domain.actionTargetId;
  const targetType = domain.actionTargetType;
  if (!targetId || !targetType) {
    return undefined;
  }
  if (targetType === 'requirements') {
    return internalHref('/delivery/requirements', { version_id: targetId });
  }
  if (targetType === 'tasks_by_version') {
    return internalHref('/delivery/rd-tasks', { version_id: targetId });
  }
  if (targetType === 'product_version') {
    return internalHref('/delivery/versions', { version_id: targetId });
  }
  if (targetType === 'code_inspection_dashboard') {
    return internalHref('/governance/code-inspections', { version_id: targetId });
  }
  if (targetType === 'code_review_reports_by_version') {
    return internalHref('/delivery/rd-tasks', { version_id: targetId });
  }
  if (targetType === 'bugs') {
    return internalHref('/delivery/bugs', { version_id: targetId });
  }
  if (targetType === 'knowledge_deposits_by_version') {
    return internalHref('/assets/knowledge', { version_id: targetId });
  }
  if (targetType === 'releases') {
    return internalHref('/governance/devops', { version_id: targetId });
  }
  if (targetType === 'deployments') {
    return internalHref('/governance/deployments', { version_id: targetId });
  }
  if (targetType === 'deployment_request') {
    return internalHref('/governance/deployments', {
      deployment_id: targetId,
      version_id: versionId,
    });
  }
  if (targetType === 'product_version_advance') {
    return undefined;
  }
  return internalHref('/delivery/versions', { version_id: versionId });
}

export function VersionDashboardEvidenceCoverage({
  dashboard,
}: VersionDashboardEvidenceCoverageProps) {
  const coverage = dashboard.evidenceCoverage;
  if (!coverage.domains.length && !coverage.totalDomains) {
    return null;
  }
  const level = dashboardHealthLevelLabels[coverage.level];
  const alertType =
    coverage.level === 'error'
      ? 'error'
      : coverage.level === 'warning'
        ? 'warning'
        : coverage.level === 'success'
          ? 'success'
          : 'info';

  return (
    <div>
      <Space align="baseline" style={{ display: 'flex', marginBottom: 8 }} wrap>
        <Text strong>证据覆盖</Text>
        <Tag color={level.color}>{level.label}</Tag>
        <Text type="secondary">
          已覆盖 {coverage.coveredDomains}/{coverage.totalDomains}，阻断{' '}
          {coverage.blockingDomains}，待补齐 {coverage.gapDomains}
        </Text>
      </Space>
      <Alert
        description={
          <Space
            align="center"
            size={12}
            style={{ display: 'flex', width: '100%' }}
            wrap
          >
            <Progress
              percent={coverage.score}
              size={[160, 8]}
              status={coverage.level === 'error' ? 'exception' : 'normal'}
            />
            <Text>{coverage.summary}</Text>
          </Space>
        }
        showIcon
        type={alertType}
      />
      <div
        style={{
          display: 'grid',
          gap: 10,
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          marginTop: 10,
        }}
      >
        {coverage.domains.map((domain) => {
          const domainLevel = dashboardHealthLevelLabels[domain.level];
          const statusLabel = evidenceStatusLabels[domain.status] ?? {
            color: 'default',
            label: domain.status,
          };
          const actionHref = evidenceActionHref(domain, dashboard.version.id);
          return (
            <div
              key={domain.key}
              style={{
                border: `1px solid ${
                  domain.level === 'error'
                    ? '#ffccc7'
                    : domain.level === 'warning'
                      ? '#ffe58f'
                      : '#f0f0f0'
                }`,
                borderRadius: 6,
                minHeight: 126,
                padding: '10px 12px',
              }}
            >
              <Space
                align="center"
                style={{ justifyContent: 'space-between', width: '100%' }}
              >
                <Text strong>{domain.title}</Text>
                <Space size={4} wrap>
                  <Tag color={statusLabel.color}>{statusLabel.label}</Tag>
                  <Tag color={domainLevel.color}>{domainLevel.label}</Tag>
                </Space>
              </Space>
              <div style={{ fontSize: 18, fontWeight: 600, marginTop: 8 }}>
                {domain.value}
              </div>
              <div style={{ marginTop: 4 }}>
                <Text type="secondary">{domain.detail}</Text>
              </div>
              {actionHref && domain.actionLabel ? (
                <Button
                  href={actionHref}
                  icon={<ArrowRightOutlined />}
                  size="small"
                  style={{ marginTop: 8 }}
                  type="link"
                >
                  {domain.actionLabel}
                </Button>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

type VersionDashboardHealthSummaryProps = {
  items: DashboardHealthItem[];
};

type VersionDashboardReadinessChecklistProps = {
  checklist?: ProductVersionDashboard['releaseReadinessChecklist'];
  items: DashboardReadinessItem[];
};

type VersionDashboardDeliveryOverviewProps = {
  dashboard: ProductVersionDashboard;
  items: DashboardReadinessItem[];
  onAdvanceVersion: (version: ProductVersionRecord) => void;
  versionStatusLabels: Record<ProductVersionRecord['status'], LabelItem>;
};

export function VersionDashboardDeliveryOverview({
  dashboard,
  items,
  onAdvanceVersion,
  versionStatusLabels,
}: VersionDashboardDeliveryOverviewProps) {
  return (
    <div>
      <Space align="baseline" style={{ display: 'flex', marginBottom: 8 }} wrap>
        <Text strong>交付链路总览</Text>
        <Text type="secondary">版本推进前的关键环节按研发链路排序，红/黄环节优先治理。</Text>
      </Space>
      <div
        style={{
          display: 'grid',
          gap: 10,
          gridTemplateColumns: 'repeat(auto-fit, minmax(178px, 1fr))',
        }}
      >
        {items.map((item, index) => {
          const level = dashboardHealthLevelLabels[item.level];
          return (
            <div
              key={`delivery-${item.key}`}
              style={{
                border: `1px solid ${item.level === 'error' ? '#ffccc7' : item.level === 'warning' ? '#ffe58f' : '#f0f0f0'}`,
                borderRadius: 6,
                minHeight: 126,
                padding: '10px 12px',
              }}
            >
              <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
                <Tag color="blue">{String(index + 1).padStart(2, '0')}</Tag>
                <Tag color={level.color}>{level.label}</Tag>
              </Space>
              <div style={{ fontWeight: 600, lineHeight: 1.5, marginTop: 8 }}>
                {item.title}
              </div>
              <div style={{ marginTop: 4 }}>
                <Text>{item.value}</Text>
              </div>
              <div style={{ marginTop: 4 }}>
                <Text type="secondary">{item.detail}</Text>
              </div>
              {item.actionHref ? (
                <Button
                  href={item.actionHref}
                  icon={<ArrowRightOutlined />}
                  size="small"
                  style={{ marginTop: 8 }}
                  type="link"
                >
                  {item.actionLabel ?? '查看'}
                </Button>
              ) : item.key === 'status-impact' && dashboard.statusImpact ? (
                <Button
                  icon={<ArrowRightOutlined />}
                  onClick={() => onAdvanceVersion(dashboard.version)}
                  size="small"
                  style={{ marginTop: 8 }}
                  type="link"
                >
                  {`推进到${versionStatusLabels[dashboard.statusImpact.targetStatus].label}`}
                </Button>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function VersionDashboardReadinessChecklist({
  checklist,
  items,
}: VersionDashboardReadinessChecklistProps) {
  const level = checklist ? dashboardHealthLevelLabels[checklist.level] : undefined;
  return (
    <div>
      <Space align="baseline" style={{ display: 'flex' }} wrap>
        <Text strong>{checklist?.title ?? '发布准备清单'}</Text>
        {level ? <Tag color={level.color}>{level.label}</Tag> : null}
        {checklist?.summary ? <Text type="secondary">{checklist.summary}</Text> : null}
      </Space>
      <Space size={8} style={{ display: 'flex', marginTop: 8 }} wrap>
        {items.map((item) => {
          const level = dashboardHealthLevelLabels[item.level];
          return (
            <div
              key={item.key}
              style={{
                border: '1px solid #f0f0f0',
                borderRadius: 6,
                minHeight: 86,
                padding: '8px 10px',
                width: 176,
              }}
            >
              <Space
                align="center"
                style={{
                  justifyContent: 'space-between',
                  width: '100%',
                }}
              >
                <Text strong>{item.title}</Text>
                <Tag color={level.color}>{level.label}</Tag>
              </Space>
              <div
                style={{
                  fontWeight: 600,
                  lineHeight: 1.5,
                  marginTop: 6,
                }}
              >
                {item.value}
              </div>
              <Text type="secondary">{item.detail}</Text>
            </div>
          );
        })}
      </Space>
    </div>
  );
}

export function VersionDashboardHealthSummary({
  items,
}: VersionDashboardHealthSummaryProps) {
  return (
    <div>
      <Text strong>交付健康摘要</Text>
      <Space size={12} style={{ display: 'flex', marginTop: 8 }} wrap>
        {items.map((item) => {
          const level = dashboardHealthLevelLabels[item.level];
          return (
            <div
              key={item.key}
              style={{
                border: '1px solid #f0f0f0',
                borderRadius: 6,
                minHeight: 108,
                padding: '10px 12px',
                width: 210,
              }}
            >
              <Space
                align="center"
                style={{
                  justifyContent: 'space-between',
                  width: '100%',
                }}
              >
                <Text strong>{item.title}</Text>
                <Tag color={level.color}>{level.label}</Tag>
              </Space>
              <div
                style={{
                  fontSize: 18,
                  fontWeight: 600,
                  lineHeight: 1.5,
                  marginTop: 8,
                }}
              >
                {item.value}
              </div>
              <Text type="secondary">{item.detail}</Text>
            </div>
          );
        })}
      </Space>
    </div>
  );
}

function dashboardStatusCountStrip(
  title: string,
  counts: ProductVersionDashboard['requirementStatusCounts'],
  statusLabelMap: Record<string, LabelItem>,
) {
  return (
    <div
      style={{
        border: '1px solid #f0f0f0',
        borderRadius: 6,
        minWidth: 260,
        padding: '8px 12px',
      }}
    >
      <Text strong>{title}</Text>
      <Space size={6} style={{ marginTop: 8 }} wrap>
        {counts.length ? (
          counts.map((item) => (
            <Tag
              key={`${title}-${item.status}`}
              color={statusLabelMap[item.status]?.color ?? 'default'}
            >
              {statusLabelMap[item.status]?.label ?? item.status} {item.count}
            </Tag>
          ))
        ) : (
          <Text type="secondary">暂无数据</Text>
        )}
      </Space>
    </div>
  );
}

type VersionDashboardStatusDistributionProps = {
  dashboard: ProductVersionDashboard;
  statusLabelMap: Record<string, LabelItem>;
};

export function VersionDashboardStatusDistribution({
  dashboard,
  statusLabelMap,
}: VersionDashboardStatusDistributionProps) {
  return (
    <div>
      <Text strong>状态分布</Text>
      <Space size={12} style={{ display: 'flex', marginTop: 8 }} wrap>
        {dashboardStatusCountStrip(
          '需求状态',
          dashboard.requirementStatusCounts,
          statusLabelMap,
        )}
        {dashboardStatusCountStrip(
          '任务状态',
          dashboard.taskStatusCounts,
          statusLabelMap,
        )}
        {dashboardStatusCountStrip(
          'Bug 状态',
          dashboard.bugStatusCounts,
          statusLabelMap,
        )}
      </Space>
    </div>
  );
}

type VersionDashboardStatusImpactNoticeProps = {
  dashboard: ProductVersionDashboard;
  versionStatusLabels: Record<ProductVersionRecord['status'], LabelItem>;
};

type VersionDashboardStatusImpactPreviewProps = {
  dashboard: ProductVersionDashboard;
  statusLabelMap: Record<string, LabelItem>;
  versionStatusLabels: Record<ProductVersionRecord['status'], LabelItem>;
};

export function VersionDashboardStatusImpactNotice({
  dashboard,
  versionStatusLabels,
}: VersionDashboardStatusImpactNoticeProps) {
  if (!dashboard.statusImpact) {
    return (
      <Alert showIcon title="当前版本状态没有可推进的下一阶段" type="info" />
    );
  }

  return (
    <Alert
      description={`将同步 ${dashboard.statusImpact.updatedRequirements.length} 条需求，阻塞 ${dashboard.statusImpact.blockedRequirements.length} 条，保持不变 ${dashboard.statusImpact.unchangedRequirements.length} 条。`}
      showIcon
      title={`下一阶段：${versionStatusLabels[dashboard.statusImpact.targetStatus].label}`}
      type={
        dashboard.statusImpact.blockedRequirements.length ? 'warning' : 'info'
      }
    />
  );
}

function requirementStatusTag(
  status: string | null | undefined,
  statusLabelMap: Record<string, LabelItem>,
) {
  const key = String(status ?? '-');
  const item = statusLabelMap[key] ?? { color: 'default', label: key };
  return <Tag color={item.color}>{item.label}</Tag>;
}

function impactPreviewBlock({
  color,
  detail,
  icon,
  title,
  value,
}: {
  color: string;
  detail: ReactNode;
  icon: ReactNode;
  title: string;
  value: number;
}) {
  return (
    <div
      style={{
        border: `1px solid ${color}`,
        borderRadius: 6,
        minHeight: 128,
        padding: '10px 12px',
      }}
    >
      <Space align="center" size={8}>
        {icon}
        <Text strong>{title}</Text>
      </Space>
      <div style={{ fontSize: 24, fontWeight: 600, lineHeight: 1.5, marginTop: 8 }}>
        {value}
      </div>
      <div style={{ marginTop: 4 }}>{detail}</div>
    </div>
  );
}

export function VersionDashboardStatusImpactPreview({
  dashboard,
  statusLabelMap,
  versionStatusLabels,
}: VersionDashboardStatusImpactPreviewProps) {
  const statusImpact = dashboard.statusImpact;
  if (!statusImpact) {
    return (
      <Alert
        showIcon
        title="状态推进影响预览"
        description="当前版本状态没有可推进的下一阶段。"
        type="info"
      />
    );
  }

  const targetLabel = versionStatusLabels[statusImpact.targetStatus]?.label ?? statusImpact.targetStatus;
  const blockedSamples = statusImpact.blockedRequirements.slice(0, 3);
  const firstUpdated = statusImpact.updatedRequirements[0];
  const firstUnchanged = statusImpact.unchangedRequirements[0];

  return (
    <div>
      <Space align="baseline" style={{ display: 'flex', marginBottom: 8 }} wrap>
        <Text strong>状态推进影响预览</Text>
        <Text type="secondary">推进到 {targetLabel} 前先看同步、阻塞和保持不变的需求影响。</Text>
      </Space>
      <div
        style={{
          display: 'grid',
          gap: 10,
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        }}
      >
        {impactPreviewBlock({
          color: '#91caff',
          detail: firstUpdated ? (
            <Space size={4} wrap>
              <Text type="secondary">示例：</Text>
              <Text ellipsis style={{ maxWidth: 220 }}>
                {firstUpdated.title}
              </Text>
              {requirementStatusTag(firstUpdated.from_status ?? firstUpdated.status, statusLabelMap)}
              <ArrowRightOutlined />
              {requirementStatusTag(firstUpdated.to_status ?? statusImpact.targetStatus, statusLabelMap)}
            </Space>
          ) : (
            <Text type="secondary">暂无需求会同步推进</Text>
          ),
          icon: <CheckCircleOutlined style={{ color: '#1677ff' }} />,
          title: '同步推进',
          value: statusImpact.updatedRequirements.length,
        })}
        {impactPreviewBlock({
          color: statusImpact.blockedRequirements.length ? '#ffccc7' : '#d9f7be',
          detail: blockedSamples.length ? (
            <Space orientation="vertical" size={2} style={{ width: '100%' }}>
              {blockedSamples.map((item) => (
                <Text key={item.id} ellipsis style={{ maxWidth: 300 }} type="secondary">
                  {item.title}：{item.block_reason ?? '状态不满足推进条件'}
                </Text>
              ))}
            </Space>
          ) : (
            <Text type="secondary">暂无推进阻塞</Text>
          ),
          icon: <StopOutlined style={{ color: statusImpact.blockedRequirements.length ? '#cf1322' : '#52c41a' }} />,
          title: '阻塞',
          value: statusImpact.blockedRequirements.length,
        })}
        {impactPreviewBlock({
          color: '#f0f0f0',
          detail: firstUnchanged ? (
            <Space size={4} wrap>
              <Text type="secondary">示例：</Text>
              <Text ellipsis style={{ maxWidth: 220 }}>
                {firstUnchanged.title}
              </Text>
              {requirementStatusTag(firstUnchanged.status ?? firstUnchanged.from_status, statusLabelMap)}
            </Space>
          ) : (
            <Text type="secondary">暂无需求保持不变</Text>
          ),
          icon: <PauseCircleOutlined style={{ color: '#8c8c8c' }} />,
          title: '保持不变',
          value: statusImpact.unchangedRequirements.length,
        })}
      </div>
    </div>
  );
}
