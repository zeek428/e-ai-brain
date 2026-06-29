import type { ProductVersionRecord, RequirementRecord } from '../../../data/management';
import { fullChainSubjectHref, type ProductVersionDashboard } from '../../../services/aiBrain';

export type LabelItem = { color: string; label: string };

export type DashboardHealthItem = {
  detail: string;
  key: string;
  level: 'error' | 'info' | 'success' | 'warning';
  title: string;
  value: string;
};

export type DashboardReadinessItem = DashboardHealthItem;

type DashboardRequirementImpact = NonNullable<ProductVersionDashboard['statusImpact']>['updatedRequirements'][number];

export type DashboardStatusImpactRow = DashboardRequirementImpact & {
  impact: 'blocked' | 'unchanged' | 'updated';
  impactLabel: string;
};

export type DashboardBlockerActionItem = ProductVersionDashboard['blockers'][number] & {
  actionHref?: string;
  fullChainHref?: string;
  priority: number;
  sourceLabel: string;
};

export const dashboardBlockerSourceLabels: Record<string, string> = {
  bug: 'Bug',
  code_inspection_report: '代码巡检',
  jenkins_release: '发布记录',
  product_version_branch_config: '代码分支',
  requirement: '需求',
};

export const dashboardHealthLevelLabels: Record<DashboardHealthItem['level'], LabelItem> = {
  error: { color: 'red', label: '需处理' },
  info: { color: 'blue', label: '关注' },
  success: { color: 'green', label: '正常' },
  warning: { color: 'gold', label: '有风险' },
};

export function dashboardDate(value?: string | null) {
  return value || '-';
}

export function internalHref(path: string, params: Record<string, string | undefined>) {
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
    sourceType === 'product_version' ||
    sourceType === 'product_version_branch_config' ||
    sourceType === 'requirement'
  ) {
    return sourceType;
  }
  return undefined;
}

const blockerSeverityPriority: Record<string, number> = {
  blocker: 1,
  critical: 1,
  high: 1,
  medium: 2,
  low: 3,
};

const blockerSourcePriority: Record<string, number> = {
  bug: 1,
  jenkins_release: 2,
  code_inspection_report: 3,
  requirement: 4,
  product_version_branch_config: 5,
};

export function blockerActionHref(blocker: ProductVersionDashboard['blockers'][number], versionId: string) {
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
  if (targetType === 'product_version') {
    return internalHref('/governance/devops', { version_id: targetId });
  }
  return undefined;
}

export function buildBlockerActionQueue(dashboard: ProductVersionDashboard): DashboardBlockerActionItem[] {
  return dashboard.blockers
    .map((blocker) => {
      const subjectType = blockerSubjectType(String(blocker.sourceType ?? ''));
      const actionHref = blockerActionHref(blocker, dashboard.version.id);
      const fullChainHref = subjectType && blocker.id ? fullChainSubjectHref(subjectType, blocker.id) : undefined;
      return {
        ...blocker,
        actionHref,
        fullChainHref,
        priority: 0,
        sourceLabel: dashboardBlockerSourceLabels[blocker.sourceType] ?? blocker.sourceType,
      };
    })
    .sort((left, right) => {
      const leftSeverity = blockerSeverityPriority[String(left.severity ?? '').toLowerCase()] ?? 4;
      const rightSeverity = blockerSeverityPriority[String(right.severity ?? '').toLowerCase()] ?? 4;
      if (leftSeverity !== rightSeverity) {
        return leftSeverity - rightSeverity;
      }
      const leftSource = blockerSourcePriority[String(left.sourceType ?? '')] ?? 99;
      const rightSource = blockerSourcePriority[String(right.sourceType ?? '')] ?? 99;
      if (leftSource !== rightSource) {
        return leftSource - rightSource;
      }
      return String(left.title ?? '').localeCompare(String(right.title ?? ''));
    })
    .map((item, index) => ({
      ...item,
      priority: index + 1,
    }));
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
    pending_review: { color: 'gold', label: '待确认' },
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
  const sourceCounts = blockers.reduce<Record<string, number>>((accumulator, blocker) => {
    const source = dashboardBlockerSourceLabels[blocker.sourceType] ?? blocker.sourceType;
    accumulator[source] = (accumulator[source] ?? 0) + 1;
    return accumulator;
  }, {});
  return Object.entries(sourceCounts)
    .map(([source, count]) => `${source} ${count}`)
    .join('、');
}

export function buildDashboardHealthItems(dashboard?: ProductVersionDashboard): DashboardHealthItem[] {
  if (!dashboard) {
    return [];
  }
  const severeRiskCount = dashboard.summary.severe_bugs + dashboard.summary.severe_code_inspection_reports;
  const notCreatedBranchCount = dashboard.branchConfigs.filter(
    (branchConfig) => branchConfig.branchStatus === 'not_created',
  ).length;
  const failedReleaseCount = dashboard.releases.filter((release) => {
    const status = release.status.toLowerCase();
    return status === 'failed' || status === 'failure' || status === 'canceled' || status === 'cancelled';
  }).length;
  const highRiskInspectionCount = dashboard.codeInspectionReports.filter((report) => {
    const riskLevel = report.risk_level.toLowerCase();
    return riskLevel === 'blocker' || riskLevel === 'critical' || riskLevel === 'high';
  }).length;
  const pendingCodeReviewCount = dashboard.codeReviewReports.filter(
    (report) => report.status === 'pending_review' || report.status === 'waiting_review',
  ).length;
  const searchableKnowledgeDepositCount = dashboard.summary.searchable_knowledge_deposits;
  const vectorizedKnowledgeDepositCount = dashboard.summary.vectorized_knowledge_deposits;
  return [
    {
      detail: dashboard.blockers.length
        ? `阻塞来源：${blockerSourceSummary(dashboard.blockers)}。`
        : '需求、分支、质量和发布记录暂无阻塞项。',
      key: 'blockers',
      level: dashboard.blockers.length ? 'error' : 'success',
      title: '发布准入',
      value: dashboard.blockers.length ? `${dashboard.blockers.length} 个阻塞项` : '暂无阻塞',
    },
    {
      detail: `严重 Bug ${dashboard.summary.severe_bugs}，严重巡检 ${dashboard.summary.severe_code_inspection_reports}，未关闭 Bug ${dashboard.summary.open_bugs}。`,
      key: 'quality',
      level: severeRiskCount || dashboard.summary.open_bugs ? 'warning' : 'success',
      title: '质量风险',
      value: severeRiskCount ? `${severeRiskCount} 个严重风险` : '质量风险可控',
    },
    {
      detail: dashboard.branchConfigs.length
        ? `已登记 ${dashboard.branchConfigs.length} 个代码分支配置，未创建 ${notCreatedBranchCount} 个。`
        : '尚未登记版本代码分支，进入开发/测试前需要补齐。',
      key: 'branches',
      level: !dashboard.branchConfigs.length || notCreatedBranchCount ? 'warning' : 'success',
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
      level: highRiskInspectionCount ? 'warning' : dashboard.codeInspectionReports.length ? 'success' : 'info',
      title: '代码巡检',
      value: highRiskInspectionCount
        ? `${highRiskInspectionCount} 份高风险`
        : `${dashboard.codeInspectionReports.length} 份报告`,
    },
    {
      detail: dashboard.codeReviewReports.length
        ? `已有 ${dashboard.codeReviewReports.length} 份代码评审报告，待确认 ${pendingCodeReviewCount} 份。`
        : '当前版本还没有代码评审报告，进入测试前建议补齐。',
      key: 'code-reviews',
      level: pendingCodeReviewCount ? 'warning' : dashboard.codeReviewReports.length ? 'success' : 'info',
      title: '代码评审',
      value: pendingCodeReviewCount
        ? `${pendingCodeReviewCount} 份待确认`
        : `${dashboard.codeReviewReports.length} 份报告`,
    },
    {
      detail: dashboard.knowledgeDeposits.length
        ? `已有 ${dashboard.knowledgeDeposits.length} 条任务知识沉淀，可检索 ${searchableKnowledgeDepositCount} 条，向量就绪 ${vectorizedKnowledgeDepositCount} 条。`
        : '当前版本还没有任务知识沉淀，建议在关键设计、评审和整改完成后沉淀经验。',
      key: 'knowledge-deposits',
      level:
        dashboard.knowledgeDeposits.length && !searchableKnowledgeDepositCount
          ? 'warning'
          : dashboard.knowledgeDeposits.length
            ? 'success'
            : 'info',
      title: '知识沉淀',
      value: dashboard.knowledgeDeposits.length
        ? `${searchableKnowledgeDepositCount}/${dashboard.knowledgeDeposits.length} 可检索`
        : '暂无沉淀',
    },
    {
      detail: dashboard.releases.length
        ? `已有 ${dashboard.releases.length} 条发布记录，失败/取消 ${failedReleaseCount} 条。`
        : '当前版本暂无发布记录。',
      key: 'releases',
      level: failedReleaseCount ? 'error' : dashboard.releases.length ? 'success' : 'info',
      title: '发布流水线',
      value: failedReleaseCount ? `${failedReleaseCount} 条失败发布` : `${dashboard.releases.length} 条发布记录`,
    },
  ];
}

function statusCount(counts: ProductVersionDashboard['taskStatusCounts'], status: string) {
  return counts.find((item) => item.status === status)?.count ?? 0;
}

export function buildDashboardReadinessItems(dashboard?: ProductVersionDashboard): DashboardReadinessItem[] {
  if (!dashboard) {
    return [];
  }
  const blockedRequirementCount = dashboard.statusImpact?.blockedRequirements.length ?? 0;
  const runningTaskCount = statusCount(dashboard.taskStatusCounts, 'running');
  const notCreatedBranchCount = dashboard.branchConfigs.filter(
    (branchConfig) => branchConfig.branchStatus === 'not_created',
  ).length;
  const highRiskInspectionCount = dashboard.codeInspectionReports.filter((report) => {
    const riskLevel = report.risk_level.toLowerCase();
    return riskLevel === 'blocker' || riskLevel === 'critical' || riskLevel === 'high';
  }).length;
  const pendingCodeReviewCount = dashboard.summary.pending_code_review_reports;
  const releaseBlockerCount = dashboard.blockers.filter((blocker) => blocker.sourceType === 'jenkins_release').length;
  return [
    {
      detail: blockedRequirementCount
        ? `${dashboard.summary.requirements} 条需求 · 阻塞 ${blockedRequirementCount} 条`
        : `${dashboard.summary.requirements} 条需求 · 可推进`,
      key: 'requirements',
      level: blockedRequirementCount ? 'warning' : 'success',
      title: '需求范围',
      value: blockedRequirementCount ? '范围有阻塞' : '范围可推进',
    },
    {
      detail: runningTaskCount
        ? `${dashboard.summary.tasks} 个任务 · 运行中 ${runningTaskCount} 个`
        : `${dashboard.summary.tasks} 个任务 · 暂无运行中`,
      key: 'tasks',
      level: runningTaskCount ? 'info' : 'success',
      title: '研发任务',
      value: runningTaskCount ? '任务进行中' : '任务稳定',
    },
    {
      detail: notCreatedBranchCount
        ? `${dashboard.summary.branch_configs} 个分支 · 未创建 ${notCreatedBranchCount} 个`
        : `${dashboard.summary.branch_configs} 个分支 · 已登记`,
      key: 'branches',
      level: notCreatedBranchCount ? 'warning' : 'success',
      title: '代码分支',
      value: notCreatedBranchCount ? '分支待维护' : '分支就绪',
    },
    {
      detail: highRiskInspectionCount
        ? `${dashboard.summary.code_inspection_reports} 份报告 · 高风险 ${highRiskInspectionCount} 份`
        : `${dashboard.summary.code_inspection_reports} 份报告 · 暂无高风险`,
      key: 'inspections',
      level: highRiskInspectionCount ? 'warning' : 'success',
      title: '代码巡检',
      value: highRiskInspectionCount ? '质量待治理' : '质量可控',
    },
    {
      detail: pendingCodeReviewCount
        ? `${dashboard.summary.code_review_reports} 份报告 · 待确认 ${pendingCodeReviewCount} 份`
        : `${dashboard.summary.code_review_reports} 份报告 · 暂无待确认`,
      key: 'code-reviews',
      level: pendingCodeReviewCount ? 'warning' : 'success',
      title: '代码评审',
      value: pendingCodeReviewCount ? '评审待确认' : '评审已收敛',
    },
    {
      detail: dashboard.summary.open_bugs
        ? `${dashboard.summary.bugs} 个 Bug · 未关闭 ${dashboard.summary.open_bugs} 个`
        : `${dashboard.summary.bugs} 个 Bug · 已收敛`,
      key: 'bugs',
      level: dashboard.summary.open_bugs ? 'error' : 'success',
      title: 'Bug 收敛',
      value: dashboard.summary.open_bugs ? 'Bug 待关闭' : 'Bug 已收敛',
    },
    {
      detail: dashboard.summary.knowledge_deposits
        ? `${dashboard.summary.knowledge_deposits} 条知识沉淀 · 可检索 ${dashboard.summary.searchable_knowledge_deposits} 条 · 向量就绪 ${dashboard.summary.vectorized_knowledge_deposits} 条`
        : '暂无知识沉淀，发布前建议沉淀关键设计、巡检和整改经验',
      key: 'knowledge-deposits',
      level:
        dashboard.summary.knowledge_deposits && !dashboard.summary.searchable_knowledge_deposits
          ? 'warning'
          : dashboard.summary.knowledge_deposits
            ? 'success'
            : 'info',
      title: '知识沉淀',
      value: dashboard.summary.knowledge_deposits
        ? `${dashboard.summary.searchable_knowledge_deposits}/${dashboard.summary.knowledge_deposits} 可检索`
        : '沉淀待补齐',
    },
    {
      detail: releaseBlockerCount
        ? `${dashboard.summary.releases} 条记录 · 发布阻塞 ${releaseBlockerCount} 个`
        : `${dashboard.summary.releases} 条记录 · 暂无发布阻塞`,
      key: 'releases',
      level: releaseBlockerCount ? 'error' : 'success',
      title: '发布证据',
      value: releaseBlockerCount ? '发布待补证' : '发布证据可用',
    },
    {
      detail: dashboard.statusImpact
        ? `同步 ${dashboard.statusImpact.updatedRequirements.length} / 阻塞 ${dashboard.statusImpact.blockedRequirements.length} / 保持 ${dashboard.statusImpact.unchangedRequirements.length}`
        : '当前版本没有可推进的下一阶段',
      key: 'status-impact',
      level: dashboard.statusImpact?.blockedRequirements.length
        ? 'warning'
        : dashboard.statusImpact
          ? 'success'
          : 'info',
      title: '状态推进',
      value: dashboard.statusImpact ? '已预览影响' : '无需推进',
    },
  ];
}
