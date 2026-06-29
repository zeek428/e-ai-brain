import {
  ArrowRightOutlined,
  CodeOutlined,
  EyeOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { Alert, Button, Space, Tag, Typography } from 'antd';

import type { ProductVersionRecord } from '../../../data/management';
import {
  fullChainSubjectHref,
  type ProductVersionDashboard,
} from '../../../services/aiBrain';
import {
  dashboardHealthLevelLabels,
  internalHref,
  type DashboardHealthItem,
  type DashboardReadinessItem,
  type LabelItem,
} from './versionDashboardModel';

const { Text } = Typography;

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

export function VersionDashboardMetrics({
  dashboard,
}: VersionDashboardMetricsProps) {
  const severeRiskCount =
    dashboard.summary.severe_bugs +
    dashboard.summary.severe_code_inspection_reports;
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
      {dashboardMetric('代码评审', dashboard.summary.code_review_reports)}
      {dashboardMetric(
        '待确认评审',
        dashboard.summary.pending_code_review_reports,
        dashboard.summary.pending_code_review_reports ? '#d48806' : undefined,
      )}
      {dashboardMetric('发布记录', dashboard.summary.releases)}
      {dashboardMetric(
        '阻塞项',
        dashboard.summary.blockers,
        dashboard.summary.blockers ? '#cf1322' : undefined,
      )}
    </Space>
  );
}

type VersionDashboardHealthSummaryProps = {
  items: DashboardHealthItem[];
};

type VersionDashboardReadinessChecklistProps = {
  items: DashboardReadinessItem[];
};

export function VersionDashboardReadinessChecklist({
  items,
}: VersionDashboardReadinessChecklistProps) {
  return (
    <div>
      <Text strong>发布准备清单</Text>
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
