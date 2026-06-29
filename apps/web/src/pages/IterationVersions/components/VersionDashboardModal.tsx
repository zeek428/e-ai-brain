import {
  ArrowRightOutlined,
  CodeOutlined,
  EyeOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Empty,
  Modal,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd';

import { StatusTag } from '../../../components/ManagementListPage';
import type {
  ProductVersionBranchConfigRecord,
  ProductVersionRecord,
  RequirementRecord,
} from '../../../data/management';
import {
  fullChainSubjectHref,
  type ProductVersionDashboard,
} from '../../../services/aiBrain';

const { Text } = Typography;

type LabelItem = { color: string; label: string };

type VersionDashboardModalProps = {
  branchCreationSourceLabels: Record<
    ProductVersionBranchConfigRecord['creationSource'],
    string
  >;
  branchStatusLabels: Record<
    ProductVersionBranchConfigRecord['branchStatus'],
    LabelItem
  >;
  dashboard?: ProductVersionDashboard;
  loading?: boolean;
  onAdvanceVersion: (version: ProductVersionRecord) => void;
  onClose: () => void;
  onMaintainBranches: (version: ProductVersionRecord) => void;
  onViewRequirements: (version: ProductVersionRecord) => void;
  open: boolean;
  requirementStatusLabels: Record<RequirementRecord['status'], LabelItem>;
  version?: ProductVersionRecord;
  versionStatusLabels: Record<ProductVersionRecord['status'], LabelItem>;
};

const dashboardBlockerSourceLabels: Record<string, string> = {
  bug: 'Bug',
  code_inspection_report: '代码巡检',
  jenkins_release: '发布记录',
  product_version_branch_config: '代码分支',
  requirement: '需求',
};

function dashboardDate(value?: string | null) {
  return value || '-';
}

function internalHref(
  path: string,
  params: Record<string, string | undefined>,
) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      searchParams.set(key, value);
    }
  });
  const queryString = searchParams.toString();
  return queryString ? `${path}?${queryString}` : path;
}

function blockerSubjectType(sourceType: string) {
  if (
    sourceType === 'bug' ||
    sourceType === 'code_inspection_report' ||
    sourceType === 'jenkins_release' ||
    sourceType === 'product_version_branch_config' ||
    sourceType === 'requirement'
  ) {
    return sourceType;
  }
  return undefined;
}

function blockerActionHref(
  blocker: ProductVersionDashboard['blockers'][number],
  versionId: string,
) {
  const targetType = blocker.actionTargetType || blocker.sourceType;
  const targetId = blocker.actionTargetId || blocker.id;
  if (!targetId) {
    return undefined;
  }
  if (targetType === 'requirement') {
    return internalHref('/delivery/requirements', { requirement_id: targetId });
  }
  if (targetType === 'bug') {
    return internalHref('/delivery/bugs', { bug_id: targetId });
  }
  if (targetType === 'code_inspection_report') {
    return internalHref('/governance/code-inspections', {
      source_id: targetId,
    });
  }
  if (targetType === 'product_version_branch_config') {
    return internalHref('/delivery/versions', {
      branch_config_id: targetId,
      version_id: versionId,
    });
  }
  if (targetType === 'jenkins_release') {
    return internalHref('/governance/devops', {
      release_id: targetId,
      version_id: versionId,
    });
  }
  return undefined;
}

function buildStatusImpactRows(
  statusImpact?: ProductVersionDashboard['statusImpact'],
) {
  if (!statusImpact) {
    return [];
  }
  return [
    ...statusImpact.updatedRequirements.map((item) => ({
      ...item,
      impact: 'updated',
      impactLabel: '同步推进',
    })),
    ...statusImpact.blockedRequirements.map((item) => ({
      ...item,
      impact: 'blocked',
      impactLabel: '阻塞',
    })),
    ...statusImpact.unchangedRequirements.map((item) => ({
      ...item,
      impact: 'unchanged',
      impactLabel: '保持不变',
    })),
  ];
}

type DashboardHealthItem = {
  detail: string;
  key: string;
  level: 'error' | 'info' | 'success' | 'warning';
  title: string;
  value: string;
};

const dashboardHealthLevelLabels: Record<
  DashboardHealthItem['level'],
  LabelItem
> = {
  error: { color: 'red', label: '需处理' },
  info: { color: 'blue', label: '关注' },
  success: { color: 'green', label: '正常' },
  warning: { color: 'gold', label: '有风险' },
};

function blockerSourceSummary(blockers: ProductVersionDashboard['blockers']) {
  const sourceCounts = blockers.reduce<Record<string, number>>(
    (accumulator, blocker) => {
      const source =
        dashboardBlockerSourceLabels[blocker.sourceType] ?? blocker.sourceType;
      accumulator[source] = (accumulator[source] ?? 0) + 1;
      return accumulator;
    },
    {},
  );
  return Object.entries(sourceCounts)
    .map(([source, count]) => `${source} ${count}`)
    .join('、');
}

function buildDashboardHealthItems(
  dashboard?: ProductVersionDashboard,
): DashboardHealthItem[] {
  if (!dashboard) {
    return [];
  }
  const severeRiskCount =
    dashboard.summary.severe_bugs +
    dashboard.summary.severe_code_inspection_reports;
  const notCreatedBranchCount = dashboard.branchConfigs.filter(
    (branchConfig) => branchConfig.branchStatus === 'not_created',
  ).length;
  const failedReleaseCount = dashboard.releases.filter((release) => {
    const status = release.status.toLowerCase();
    return (
      status === 'failed' ||
      status === 'failure' ||
      status === 'canceled' ||
      status === 'cancelled'
    );
  }).length;
  const highRiskInspectionCount = dashboard.codeInspectionReports.filter(
    (report) => {
      const riskLevel = report.risk_level.toLowerCase();
      return (
        riskLevel === 'blocker' ||
        riskLevel === 'critical' ||
        riskLevel === 'high'
      );
    },
  ).length;
  return [
    {
      detail: dashboard.blockers.length
        ? `阻塞来源：${blockerSourceSummary(dashboard.blockers)}。`
        : '需求、分支、质量和发布记录暂无阻塞项。',
      key: 'blockers',
      level: dashboard.blockers.length ? 'error' : 'success',
      title: '发布准入',
      value: dashboard.blockers.length
        ? `${dashboard.blockers.length} 个阻塞项`
        : '暂无阻塞',
    },
    {
      detail: `严重 Bug ${dashboard.summary.severe_bugs}，严重巡检 ${dashboard.summary.severe_code_inspection_reports}，未关闭 Bug ${dashboard.summary.open_bugs}。`,
      key: 'quality',
      level:
        severeRiskCount || dashboard.summary.open_bugs ? 'warning' : 'success',
      title: '质量风险',
      value: severeRiskCount ? `${severeRiskCount} 个严重风险` : '质量风险可控',
    },
    {
      detail: dashboard.branchConfigs.length
        ? `已登记 ${dashboard.branchConfigs.length} 个代码分支配置，未创建 ${notCreatedBranchCount} 个。`
        : '尚未登记版本代码分支，进入开发/测试前需要补齐。',
      key: 'branches',
      level:
        !dashboard.branchConfigs.length || notCreatedBranchCount
          ? 'warning'
          : 'success',
      title: '代码分支',
      value: notCreatedBranchCount
        ? `${notCreatedBranchCount} 个分支未创建`
        : dashboard.branchConfigs.length
          ? '分支已登记'
          : '暂无分支',
    },
    {
      detail: dashboard.codeInspectionReports.length
        ? `已有 ${dashboard.codeInspectionReports.length} 份巡检报告，高风险 ${highRiskInspectionCount} 份。`
        : '当前版本还没有代码巡检报告，进入测试/发布前建议补齐。',
      key: 'inspection',
      level: highRiskInspectionCount
        ? 'warning'
        : dashboard.codeInspectionReports.length
          ? 'success'
          : 'info',
      title: '代码巡检',
      value: highRiskInspectionCount
        ? `${highRiskInspectionCount} 份高风险`
        : `${dashboard.codeInspectionReports.length} 份报告`,
    },
    {
      detail: dashboard.releases.length
        ? `已有 ${dashboard.releases.length} 条发布记录，失败/取消 ${failedReleaseCount} 条。`
        : '当前版本暂无发布记录。',
      key: 'releases',
      level: failedReleaseCount
        ? 'error'
        : dashboard.releases.length
          ? 'success'
          : 'info',
      title: '发布流水线',
      value: failedReleaseCount
        ? `${failedReleaseCount} 条失败发布`
        : `${dashboard.releases.length} 条发布记录`,
    },
  ];
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

function dashboardStatusTag(
  value: string | null | undefined,
  statusLabelMap: Record<string, LabelItem>,
) {
  const key = String(value ?? '-');
  const item = statusLabelMap[key] ?? { color: 'default', label: key };
  return <Tag color={item.color}>{item.label}</Tag>;
}

export function VersionDashboardModal({
  branchCreationSourceLabels,
  branchStatusLabels,
  dashboard,
  loading,
  onAdvanceVersion,
  onClose,
  onMaintainBranches,
  onViewRequirements,
  open,
  requirementStatusLabels,
  version,
  versionStatusLabels,
}: VersionDashboardModalProps) {
  const dashboardVersion = dashboard?.version ?? version;
  const statusLabelMap: Record<string, LabelItem> = {
    ...versionStatusLabels,
    ...requirementStatusLabels,
    active: { color: 'blue', label: '开发中' },
    assigned: { color: 'blue', label: '已分派' },
    closed: { color: 'default', label: '已关闭' },
    completed: { color: 'green', label: '已完成' },
    failed: { color: 'red', label: '失败' },
    fixed: { color: 'cyan', label: '已修复' },
    high: { color: 'orange', label: '高风险' },
    low: { color: 'green', label: '低风险' },
    medium: { color: 'gold', label: '中风险' },
    open: { color: 'red', label: '打开' },
    passed: { color: 'green', label: '通过' },
    ready_for_release: { color: 'orange', label: '待发布' },
    reopened: { color: 'volcano', label: '重新打开' },
    running: { color: 'blue', label: '运行中' },
    succeeded: { color: 'green', label: '成功' },
    triaged: { color: 'gold', label: '已分诊' },
    verified: { color: 'green', label: '已验证' },
    waiting_review: { color: 'gold', label: '待确认' },
  };
  const dashboardStatusImpactRows = buildStatusImpactRows(
    dashboard?.statusImpact,
  );
  const dashboardHealthItems = buildDashboardHealthItems(dashboard);
  const renderStatusTag = (value?: string | null) =>
    dashboardStatusTag(value, statusLabelMap);

  return (
    <Modal
      destroyOnHidden
      footer={null}
      onCancel={onClose}
      open={open}
      title={
        dashboardVersion ? `版本总览 · ${dashboardVersion.code}` : '版本总览'
      }
      width={1180}
    >
      <Spin spinning={loading ?? false}>
        {dashboard ? (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Alert
              action={
                <Button
                  href={fullChainSubjectHref(
                    'product_version',
                    dashboard.version.id,
                  )}
                  icon={<LinkOutlined />}
                  size="small"
                >
                  版本全链路
                </Button>
              }
              description={`开始时间：${dashboardDate(dashboard.version.startDate)}；计划发布时间：${dashboardDate(
                dashboard.version.releaseDate,
              )}`}
              title={`${dashboard.version.productName ?? dashboard.version.productId ?? '-'} · ${
                dashboard.version.name
              } · ${versionStatusLabels[dashboard.version.status].label}`}
              type={dashboard.summary.blockers ? 'warning' : 'success'}
            />
            {dashboard.accessIssues.map((issue) => (
              <Alert
                key={`${issue.section}-${issue.code}`}
                showIcon
                title={issue.message}
                type="warning"
              />
            ))}
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
                  href={fullChainSubjectHref(
                    'product_version',
                    dashboard.version.id,
                  )}
                  icon={<LinkOutlined />}
                >
                  版本全链路
                </Button>
              </Space>
            </div>
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
                dashboard.summary.severe_bugs +
                  dashboard.summary.severe_code_inspection_reports,
                dashboard.summary.severe_bugs +
                  dashboard.summary.severe_code_inspection_reports
                  ? '#cf1322'
                  : undefined,
              )}
              {dashboardMetric(
                '代码巡检',
                dashboard.summary.code_inspection_reports,
              )}
              {dashboardMetric('发布记录', dashboard.summary.releases)}
              {dashboardMetric(
                '阻塞项',
                dashboard.summary.blockers,
                dashboard.summary.blockers ? '#cf1322' : undefined,
              )}
            </Space>
            <div>
              <Text strong>交付健康摘要</Text>
              <Space size={12} style={{ display: 'flex', marginTop: 8 }} wrap>
                {dashboardHealthItems.map((item) => {
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
            {dashboard.statusImpact ? (
              <Alert
                description={`将同步 ${dashboard.statusImpact.updatedRequirements.length} 条需求，阻塞 ${dashboard.statusImpact.blockedRequirements.length} 条，保持不变 ${dashboard.statusImpact.unchangedRequirements.length} 条。`}
                showIcon
                title={`下一阶段：${versionStatusLabels[dashboard.statusImpact.targetStatus].label}`}
                type={
                  dashboard.statusImpact.blockedRequirements.length
                    ? 'warning'
                    : 'info'
                }
              />
            ) : (
              <Alert
                showIcon
                title="当前版本状态没有可推进的下一阶段"
                type="info"
              />
            )}
            {dashboard.statusImpact ? (
              <div>
                <Text strong>推进影响明细</Text>
                <Table<(typeof dashboardStatusImpactRows)[number]>
                  columns={[
                    {
                      dataIndex: 'impact',
                      render: (value, row) => {
                        const color =
                          value === 'blocked'
                            ? 'red'
                            : value === 'updated'
                              ? 'blue'
                              : 'default';
                        return <Tag color={color}>{row.impactLabel}</Tag>;
                      },
                      title: '影响',
                      width: 120,
                    },
                    {
                      dataIndex: 'id',
                      render: (value) => (
                        <Typography.Link
                          href={internalHref('/delivery/requirements', {
                            requirement_id: String(value),
                          })}
                        >
                          {String(value)}
                        </Typography.Link>
                      ),
                      title: '需求编号',
                      width: 160,
                    },
                    {
                      dataIndex: 'title',
                      render: (value) => (
                        <Text ellipsis style={{ maxWidth: 260 }}>
                          {String(value ?? '-')}
                        </Text>
                      ),
                      title: '需求标题',
                      width: 280,
                    },
                    {
                      dataIndex: 'from_status',
                      render: (value) => renderStatusTag(String(value ?? '-')),
                      title: '当前状态',
                      width: 130,
                    },
                    {
                      dataIndex: 'to_status',
                      render: (value) =>
                        value ? (
                          renderStatusTag(String(value))
                        ) : (
                          <Text type="secondary">-</Text>
                        ),
                      title: '目标状态',
                      width: 130,
                    },
                    {
                      dataIndex: 'block_reason',
                      render: (value) => (
                        <Text ellipsis style={{ maxWidth: 280 }}>
                          {String(value ?? '-')}
                        </Text>
                      ),
                      title: '说明',
                    },
                    {
                      key: 'action',
                      render: (_, row) => (
                        <Button
                          href={fullChainSubjectHref('requirement', row.id)}
                          icon={<LinkOutlined />}
                          size="small"
                          type="link"
                        >
                          全链路
                        </Button>
                      ),
                      title: '操作',
                      width: 110,
                    },
                  ]}
                  dataSource={dashboardStatusImpactRows}
                  locale={{ emptyText: '下一阶段暂无需求状态影响' }}
                  pagination={
                    dashboardStatusImpactRows.length > 5
                      ? { pageSize: 5 }
                      : false
                  }
                  rowKey={(row) => `${row.impact}-${row.id}`}
                  scroll={{ x: 1090 }}
                  size="small"
                />
              </div>
            ) : null}
            <div>
              <Text strong>阻塞项</Text>
              <Table<ProductVersionDashboard['blockers'][number]>
                columns={[
                  {
                    dataIndex: 'sourceType',
                    render: (value) =>
                      dashboardBlockerSourceLabels[String(value)] ??
                      String(value ?? '-'),
                    title: '来源',
                    width: 120,
                  },
                  {
                    dataIndex: 'title',
                    render: (value) => (
                      <Text ellipsis style={{ maxWidth: 220 }}>
                        {String(value ?? '-')}
                      </Text>
                    ),
                    title: '标题',
                    width: 240,
                  },
                  {
                    dataIndex: 'severity',
                    render: (value) => renderStatusTag(String(value)),
                    title: '级别',
                    width: 120,
                  },
                  {
                    dataIndex: 'reason',
                    render: (value) => (
                      <Text ellipsis style={{ maxWidth: 460 }}>
                        {String(value ?? '-')}
                      </Text>
                    ),
                    title: '原因',
                    width: 360,
                  },
                  {
                    dataIndex: 'resolutionHint',
                    render: (value) => (
                      <Text ellipsis style={{ maxWidth: 340 }}>
                        {String(value ?? '-')}
                      </Text>
                    ),
                    title: '解除条件',
                    width: 360,
                  },
                  {
                    key: 'action',
                    render: (_, row) => {
                      const subjectType = blockerSubjectType(
                        String(row.sourceType ?? ''),
                      );
                      const actionHref = blockerActionHref(
                        row,
                        dashboard.version.id,
                      );
                      return (
                        <Space size={4}>
                          {actionHref ? (
                            <Button href={actionHref} size="small" type="link">
                              {row.actionLabel}
                            </Button>
                          ) : null}
                          {subjectType && row.id ? (
                            <Button
                              href={fullChainSubjectHref(subjectType, row.id)}
                              icon={<LinkOutlined />}
                              size="small"
                              type="link"
                            >
                              全链路
                            </Button>
                          ) : null}
                          {!actionHref && !(subjectType && row.id) ? (
                            <Text type="secondary">-</Text>
                          ) : null}
                        </Space>
                      );
                    },
                    title: '操作',
                    width: 180,
                  },
                ]}
                dataSource={dashboard.blockers}
                locale={{
                  emptyText: (
                    <Empty
                      description="暂无阻塞项"
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                    />
                  ),
                }}
                pagination={false}
                rowKey={(row) => `${row.sourceType}-${row.id ?? row.title}`}
                scroll={{ x: 1490 }}
                size="small"
              />
            </div>
            <div>
              <Text strong>需求与任务</Text>
              <Table<RequirementRecord>
                columns={[
                  {
                    dataIndex: 'id',
                    render: (value) => (
                      <Typography.Link
                        href={internalHref('/delivery/requirements', {
                          requirement_id: String(value),
                        })}
                      >
                        {String(value)}
                      </Typography.Link>
                    ),
                    title: '需求编号',
                    width: 160,
                  },
                  {
                    dataIndex: 'title',
                    render: (value) => (
                      <Text ellipsis style={{ maxWidth: 260 }}>
                        {String(value ?? '-')}
                      </Text>
                    ),
                    title: '需求标题',
                    width: 280,
                  },
                  {
                    dataIndex: 'status',
                    render: (value) => renderStatusTag(String(value)),
                    title: '状态',
                    width: 120,
                  },
                  { dataIndex: 'priority', title: '优先级', width: 100 },
                  { dataIndex: 'updatedAt', title: '更新时间', width: 170 },
                  {
                    key: 'action',
                    render: (_, row) => (
                      <Button
                        href={fullChainSubjectHref('requirement', row.id)}
                        icon={<LinkOutlined />}
                        size="small"
                        type="link"
                      >
                        全链路
                      </Button>
                    ),
                    title: '操作',
                    width: 110,
                  },
                ]}
                dataSource={dashboard.requirements}
                locale={{ emptyText: '当前版本暂无需求' }}
                pagination={
                  dashboard.requirements.length > 5 ? { pageSize: 5 } : false
                }
                rowKey="id"
                scroll={{ x: 940 }}
                size="small"
              />
              <Table<ProductVersionDashboard['tasks'][number]>
                columns={[
                  {
                    dataIndex: 'id',
                    render: (value) => (
                      <Typography.Link
                        href={internalHref('/delivery/rd-tasks', {
                          task_id: String(value),
                        })}
                      >
                        {String(value)}
                      </Typography.Link>
                    ),
                    title: '任务编号',
                    width: 160,
                  },
                  {
                    dataIndex: 'label',
                    render: (value) => (
                      <Text ellipsis style={{ maxWidth: 260 }}>
                        {String(value ?? '-')}
                      </Text>
                    ),
                    title: '任务标题',
                    width: 280,
                  },
                  { dataIndex: 'type', title: '类型', width: 130 },
                  {
                    dataIndex: 'status',
                    render: (value) => renderStatusTag(String(value)),
                    title: '状态',
                    width: 120,
                  },
                  { dataIndex: 'owner', title: '负责人', width: 120 },
                  {
                    key: 'action',
                    render: (_, row) => (
                      <Button
                        href={fullChainSubjectHref('ai_task', row.id)}
                        icon={<LinkOutlined />}
                        size="small"
                        type="link"
                      >
                        全链路
                      </Button>
                    ),
                    title: '操作',
                    width: 110,
                  },
                ]}
                dataSource={dashboard.tasks}
                locale={{ emptyText: '当前版本暂无 AI 任务' }}
                pagination={
                  dashboard.tasks.length > 5 ? { pageSize: 5 } : false
                }
                rowKey="id"
                scroll={{ x: 920 }}
                size="small"
              />
            </div>
            <div>
              <Text strong>质量与交付</Text>
              <Table<ProductVersionDashboard['bugs'][number]>
                columns={[
                  {
                    dataIndex: 'id',
                    render: (value) => (
                      <Typography.Link
                        href={internalHref('/delivery/bugs', {
                          bug_id: String(value),
                        })}
                      >
                        {String(value)}
                      </Typography.Link>
                    ),
                    title: 'Bug 编号',
                    width: 150,
                  },
                  {
                    dataIndex: 'title',
                    render: (value) => (
                      <Text ellipsis style={{ maxWidth: 240 }}>
                        {String(value ?? '-')}
                      </Text>
                    ),
                    title: 'Bug 标题',
                    width: 260,
                  },
                  {
                    dataIndex: 'severity',
                    render: (value) => renderStatusTag(String(value)),
                    title: '严重级别',
                    width: 120,
                  },
                  {
                    dataIndex: 'status',
                    render: (value) => renderStatusTag(String(value)),
                    title: '状态',
                    width: 120,
                  },
                  { dataIndex: 'assignee', title: '负责人', width: 120 },
                  {
                    key: 'action',
                    render: (_, row) => (
                      <Button
                        href={fullChainSubjectHref('bug', row.id)}
                        icon={<LinkOutlined />}
                        size="small"
                        type="link"
                      >
                        全链路
                      </Button>
                    ),
                    title: '操作',
                    width: 110,
                  },
                ]}
                dataSource={dashboard.bugs}
                locale={{ emptyText: '当前版本暂无 Bug' }}
                pagination={dashboard.bugs.length > 5 ? { pageSize: 5 } : false}
                rowKey="id"
                scroll={{ x: 900 }}
                size="small"
              />
              <Table<ProductVersionDashboard['codeInspectionReports'][number]>
                columns={[
                  {
                    dataIndex: 'repository_name',
                    render: (value, row) => (
                      <Typography.Link
                        href={fullChainSubjectHref(
                          'code_inspection_report',
                          row.id,
                        )}
                      >
                        {String(value ?? row.id)}
                      </Typography.Link>
                    ),
                    title: '代码库',
                    width: 180,
                  },
                  { dataIndex: 'branch', title: '分支', width: 170 },
                  {
                    dataIndex: 'risk_level',
                    render: (value) => renderStatusTag(String(value)),
                    title: '风险',
                    width: 120,
                  },
                  { dataIndex: 'finding_count', title: '问题数', width: 100 },
                  {
                    dataIndex: 'summary',
                    render: (value) => (
                      <Text ellipsis style={{ maxWidth: 300 }}>
                        {String(value ?? '-')}
                      </Text>
                    ),
                    title: '摘要',
                    width: 320,
                  },
                  {
                    dataIndex: 'created_at',
                    render: (value) => dashboardDate(String(value ?? '')),
                    title: '创建时间',
                    width: 170,
                  },
                  {
                    key: 'action',
                    render: (_, row) => (
                      <Space size={4}>
                        <Button
                          href={internalHref('/governance/code-inspections', {
                            source_id: row.id,
                          })}
                          icon={<LinkOutlined />}
                          size="small"
                          type="link"
                        >
                          详情
                        </Button>
                        <Button
                          href={fullChainSubjectHref(
                            'code_inspection_report',
                            row.id,
                          )}
                          size="small"
                          type="link"
                        >
                          全链路
                        </Button>
                      </Space>
                    ),
                    title: '操作',
                    width: 150,
                  },
                ]}
                dataSource={dashboard.codeInspectionReports}
                locale={{ emptyText: '当前版本暂无代码巡检报告' }}
                pagination={
                  dashboard.codeInspectionReports.length > 5
                    ? { pageSize: 5 }
                    : false
                }
                rowKey="id"
                scroll={{ x: 1210 }}
                size="small"
              />
              <Table<ProductVersionDashboard['branchConfigs'][number]>
                columns={[
                  { dataIndex: 'repositoryName', title: '代码库', width: 180 },
                  { dataIndex: 'baseBranch', title: '基准分支', width: 150 },
                  {
                    dataIndex: 'workingBranch',
                    render: (value, row) => (
                      <Typography.Link
                        href={internalHref('/delivery/versions', {
                          branch_config_id: row.id,
                          version_id: row.versionId,
                        })}
                      >
                        {String(value ?? '-')}
                      </Typography.Link>
                    ),
                    title: '开发分支',
                    width: 200,
                  },
                  {
                    dataIndex: 'branchStatus',
                    render: (_, row) => {
                      const statusLabel = branchStatusLabels[row.branchStatus];
                      return (
                        <StatusTag
                          color={statusLabel.color}
                          label={statusLabel.label}
                        />
                      );
                    },
                    title: '状态',
                    width: 120,
                  },
                  {
                    dataIndex: 'creationSource',
                    render: (_, row) =>
                      branchCreationSourceLabels[row.creationSource],
                    title: '来源',
                    width: 140,
                  },
                  {
                    key: 'action',
                    render: (_, row) => (
                      <Button
                        href={fullChainSubjectHref(
                          'product_version_branch_config',
                          row.id,
                        )}
                        icon={<LinkOutlined />}
                        size="small"
                        type="link"
                      >
                        全链路
                      </Button>
                    ),
                    title: '操作',
                    width: 110,
                  },
                ]}
                dataSource={dashboard.branchConfigs}
                locale={{ emptyText: '当前版本暂无代码分支配置' }}
                pagination={false}
                rowKey="id"
                scroll={{ x: 900 }}
                size="small"
              />
              <Table<ProductVersionDashboard['releases'][number]>
                columns={[
                  {
                    dataIndex: 'id',
                    render: (value) => (
                      <Typography.Link
                        href={internalHref('/governance/devops', {
                          version_id: dashboard.version.id,
                        })}
                      >
                        {String(value ?? '-')}
                      </Typography.Link>
                    ),
                    title: '发布编号',
                    width: 180,
                  },
                  { dataIndex: 'jobName', title: '作业', width: 200 },
                  { dataIndex: 'buildId', title: '构建号', width: 130 },
                  {
                    dataIndex: 'status',
                    render: (value) => renderStatusTag(String(value)),
                    title: '状态',
                    width: 120,
                  },
                  { dataIndex: 'createdAt', title: '时间', width: 170 },
                  {
                    key: 'action',
                    render: (_, row) => (
                      <Button
                        href={fullChainSubjectHref('jenkins_release', row.id)}
                        icon={<LinkOutlined />}
                        size="small"
                        type="link"
                      >
                        全链路
                      </Button>
                    ),
                    title: '操作',
                    width: 110,
                  },
                ]}
                dataSource={dashboard.releases}
                locale={{ emptyText: '当前版本暂无发布记录' }}
                pagination={
                  dashboard.releases.length > 5 ? { pageSize: 5 } : false
                }
                rowKey="id"
                scroll={{ x: 910 }}
                size="small"
              />
            </div>
          </Space>
        ) : null}
      </Spin>
    </Modal>
  );
}
