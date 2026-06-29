import type {
  ProductVersionRecord,
  RequirementRecord,
} from '../../../data/management';
import type { ProductVersionDashboard } from '../../../services/aiBrain';

export type LabelItem = { color: string; label: string };

export type DashboardHealthItem = {
  detail: string;
  key: string;
  level: 'error' | 'info' | 'success' | 'warning';
  title: string;
  value: string;
};

type DashboardRequirementImpact = NonNullable<
  ProductVersionDashboard['statusImpact']
>['updatedRequirements'][number];

export type DashboardStatusImpactRow = DashboardRequirementImpact & {
  impact: 'blocked' | 'unchanged' | 'updated';
  impactLabel: string;
};

export const dashboardBlockerSourceLabels: Record<string, string> = {
  bug: 'Bug',
  code_inspection_report: '代码巡检',
  jenkins_release: '发布记录',
  product_version_branch_config: '代码分支',
  requirement: '需求',
};

export const dashboardHealthLevelLabels: Record<
  DashboardHealthItem['level'],
  LabelItem
> = {
  error: { color: 'red', label: '需处理' },
  info: { color: 'blue', label: '关注' },
  success: { color: 'green', label: '正常' },
  warning: { color: 'gold', label: '有风险' },
};

export function dashboardDate(value?: string | null) {
  return value || '-';
}

export function internalHref(
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

export function blockerSubjectType(sourceType: string) {
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

export function blockerActionHref(
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

export function buildStatusImpactRows(
  statusImpact?: ProductVersionDashboard['statusImpact'],
): DashboardStatusImpactRow[] {
  if (!statusImpact) {
    return [];
  }
  return [
    ...statusImpact.updatedRequirements.map((item) => ({
      ...item,
      impact: 'updated' as const,
      impactLabel: '同步推进',
    })),
    ...statusImpact.blockedRequirements.map((item) => ({
      ...item,
      impact: 'blocked' as const,
      impactLabel: '阻塞',
    })),
    ...statusImpact.unchangedRequirements.map((item) => ({
      ...item,
      impact: 'unchanged' as const,
      impactLabel: '保持不变',
    })),
  ];
}

export function buildStatusLabelMap(
  versionStatusLabels: Record<ProductVersionRecord['status'], LabelItem>,
  requirementStatusLabels: Record<RequirementRecord['status'], LabelItem>,
): Record<string, LabelItem> {
  return {
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
}

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

export function buildDashboardHealthItems(
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
