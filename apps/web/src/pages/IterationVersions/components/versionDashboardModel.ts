import type { ProductVersionRecord, RequirementRecord } from '../../../data/management';
import { fullChainSubjectHref, type ProductVersionDashboard } from '../../../services/aiBrain';

export type LabelItem = { color: string; label: string };

export type DashboardHealthItem = {
  actionHref?: string;
  actionLabel?: string;
  detail: string;
  key: string;
  level: 'error' | 'info' | 'success' | 'warning';
  title: string;
  value: string;
};

export type DashboardReadinessItem = DashboardHealthItem;

type DashboardRequirementImpact = NonNullable<ProductVersionDashboard['statusImpact']>['updatedRequirements'][number];

export type DashboardGovernanceConclusion = {
  detail: string;
  level: DashboardHealthItem['level'];
  nextAction: string;
  risks: string[];
  title: string;
  value: string;
};

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
  code_review_report: '代码评审',
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
    sourceType === 'code_review_report' ||
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
  code_review_report: 4,
  requirement: 5,
  product_version_branch_config: 6,
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
  if (targetType === 'code_review_report') {
    return internalHref('/delivery/rd-tasks', {
      code_review_report_id: targetId,
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
    action_required: { color: 'red', label: '待治理' },
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
    pending_scan: { color: 'gold', label: '待巡检' },
    pending_review: { color: 'gold', label: '待确认' },
    healthy: { color: 'green', label: '已闭环' },
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

export function summarizeBranchQualityGovernance(dashboard: ProductVersionDashboard) {
  const branchRows = dashboard.branchQualityGovernance ?? [];
  const sumBranchField = (field: keyof ProductVersionDashboard['branchQualityGovernance'][number]) =>
    branchRows.reduce((total, row) => total + Number(row[field] ?? 0), 0);

  return {
    acceptedRiskCount: dashboard.summary.branch_quality_accepted_risks,
    actionRequiredBranchCount: dashboard.summary.branch_quality_action_required,
    activeSevereFindingCount: dashboard.summary.branch_quality_active_severe_findings,
    expiredAcceptedRiskCount: dashboard.summary.branch_quality_expired_accepted_risks,
    falsePositiveCount: dashboard.summary.branch_quality_false_positives,
    pendingScanBranchCount: dashboard.summary.branch_quality_pending_scan,
    pendingSuppressionCount: dashboard.summary.branch_quality_pending_suppressions,
    qualityGateFailedReportCount: sumBranchField('qualityGateFailedReportCount'),
    qualityGateViolationCount: sumBranchField('qualityGateViolationCount'),
    uncoveredSevereBugCount: sumBranchField('uncoveredSevereBugCount'),
    uncoveredSevereTaskCount: sumBranchField('uncoveredSevereTaskCount'),
  };
}

function uniqueRiskLabels(labels: Array<string | undefined>) {
  return [...new Set(labels.filter(Boolean) as string[])];
}

export function buildDashboardGovernanceConclusion(
  dashboard?: ProductVersionDashboard,
): DashboardGovernanceConclusion | undefined {
  if (!dashboard) {
    return undefined;
  }
  const branchQuality = summarizeBranchQualityGovernance(dashboard);
  const blockerCount = dashboard.summary.blockers || dashboard.blockers.length;
  const severeRiskCount =
    dashboard.summary.severe_bugs +
    dashboard.summary.severe_code_inspection_reports +
    branchQuality.activeSevereFindingCount;
  const pendingCodeReviewCount = dashboard.summary.pending_code_review_reports;
  const blockedRequirementCount = dashboard.statusImpact?.blockedRequirements.length ?? 0;
  const hasKnowledgeGap =
    dashboard.summary.knowledge_deposits > 0 &&
    dashboard.summary.searchable_knowledge_deposits < dashboard.summary.knowledge_deposits;
  const hasDeliveryEvidenceGap =
    !dashboard.summary.branch_configs ||
    !dashboard.summary.code_inspection_reports ||
    !dashboard.summary.code_review_reports ||
    !dashboard.summary.knowledge_deposits;

  const riskLabels = uniqueRiskLabels([
    blockerCount ? `发布阻塞 ${blockerCount}` : undefined,
    dashboard.summary.open_bugs ? `未关闭 Bug ${dashboard.summary.open_bugs}` : undefined,
    severeRiskCount ? `严重质量风险 ${severeRiskCount}` : undefined,
    branchQuality.qualityGateFailedReportCount
      ? `门禁失败 ${branchQuality.qualityGateFailedReportCount}`
      : undefined,
    branchQuality.actionRequiredBranchCount
      ? `待治理分支 ${branchQuality.actionRequiredBranchCount}`
      : undefined,
    branchQuality.pendingSuppressionCount
      ? `待审批忽略 ${branchQuality.pendingSuppressionCount}`
      : undefined,
    branchQuality.expiredAcceptedRiskCount
      ? `到期接受风险 ${branchQuality.expiredAcceptedRiskCount}`
      : undefined,
    pendingCodeReviewCount ? `待确认评审 ${pendingCodeReviewCount}` : undefined,
    blockedRequirementCount ? `状态推进阻塞 ${blockedRequirementCount}` : undefined,
    hasKnowledgeGap ? '知识索引未全部可检索' : undefined,
  ]);

  if (blockerCount) {
    return {
      detail: `当前版本有 ${blockerCount} 个发布阻塞项，未关闭 Bug ${dashboard.summary.open_bugs} 个，门禁失败 ${branchQuality.qualityGateFailedReportCount} 份，状态推进阻塞需求 ${blockedRequirementCount} 条。`,
      level: 'error',
      nextAction: '先处理阻塞队列中的 Bug、发布记录和分支问题，再重新查看推进影响。',
      risks: riskLabels,
      title: '版本治理结论',
      value: '版本暂不建议推进',
    };
  }

  if (
    severeRiskCount ||
    branchQuality.qualityGateFailedReportCount ||
    branchQuality.actionRequiredBranchCount ||
    branchQuality.expiredAcceptedRiskCount ||
    dashboard.summary.open_bugs
  ) {
    return {
      detail: `严重质量风险 ${severeRiskCount} 个，待治理分支 ${branchQuality.actionRequiredBranchCount} 个，到期接受风险 ${branchQuality.expiredAcceptedRiskCount} 个，未关闭 Bug ${dashboard.summary.open_bugs} 个。`,
      level: 'warning',
      nextAction: '先完成质量门禁、严重巡检和 Bug 收敛，再推进版本状态。',
      risks: riskLabels,
      title: '版本治理结论',
      value: '版本需治理后推进',
    };
  }

  if (pendingCodeReviewCount || blockedRequirementCount || hasKnowledgeGap || hasDeliveryEvidenceGap) {
    return {
      detail: `待确认评审 ${pendingCodeReviewCount} 份，状态推进阻塞需求 ${blockedRequirementCount} 条，交付证据覆盖：分支 ${dashboard.summary.branch_configs}、巡检 ${dashboard.summary.code_inspection_reports}、评审 ${dashboard.summary.code_review_reports}、知识 ${dashboard.summary.knowledge_deposits}。`,
      level: 'warning',
      nextAction: '补齐待确认评审、知识索引或交付证据后，再执行版本推进。',
      risks: riskLabels.length ? riskLabels : ['交付证据待补齐'],
      title: '版本治理结论',
      value: '版本证据待补齐',
    };
  }

  return {
    detail: `需求 ${dashboard.summary.requirements} 条，任务 ${dashboard.summary.tasks} 个，分支 ${dashboard.summary.branch_configs} 个，巡检 ${dashboard.summary.code_inspection_reports} 份，知识沉淀 ${dashboard.summary.knowledge_deposits} 条。`,
    level: 'success',
    nextAction: dashboard.statusImpact ? '可按状态推进预览继续操作。' : '当前状态暂无下一阶段，可继续观察交付健康。',
    risks: ['暂无关键阻塞'],
    title: '版本治理结论',
    value: '版本具备推进基础',
  };
}

export function buildDashboardHealthItems(dashboard?: ProductVersionDashboard): DashboardHealthItem[] {
  if (!dashboard) {
    return [];
  }
  const severeRiskCount = dashboard.summary.severe_bugs + dashboard.summary.severe_code_inspection_reports;
  const notCreatedBranchCount = dashboard.branchConfigs.filter(
    (branchConfig) => branchConfig.branchStatus === 'not_created',
  ).length;
  const actionRequiredBranchQualityCount = dashboard.summary.branch_quality_action_required;
  const pendingScanBranchQualityCount = dashboard.summary.branch_quality_pending_scan;
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
  const branchQuality = summarizeBranchQualityGovernance(dashboard);
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
        ? `已登记 ${dashboard.branchConfigs.length} 个代码分支配置，未创建 ${notCreatedBranchCount} 个，质量待治理 ${actionRequiredBranchQualityCount} 个，待巡检 ${pendingScanBranchQualityCount} 个。`
        : '尚未登记版本代码分支，进入开发/测试前需要补齐。',
      key: 'branches',
      level:
        !dashboard.branchConfigs.length ||
        notCreatedBranchCount ||
        actionRequiredBranchQualityCount ||
        pendingScanBranchQualityCount
          ? 'warning'
          : 'success',
      title: '代码分支',
      value: notCreatedBranchCount
        ? `${notCreatedBranchCount} 个分支未创建`
        : actionRequiredBranchQualityCount
          ? `${actionRequiredBranchQualityCount} 个分支待治理`
          : pendingScanBranchQualityCount
            ? `${pendingScanBranchQualityCount} 个分支待巡检`
            : dashboard.branchConfigs.length
              ? '分支已登记'
              : '暂无分支',
    },
    {
      detail: dashboard.codeInspectionReports.length
        ? `已有 ${dashboard.codeInspectionReports.length} 份巡检报告，高风险 ${highRiskInspectionCount} 份，待治理分支 ${actionRequiredBranchQualityCount} 个，活跃严重 ${branchQuality.activeSevereFindingCount} 个，门禁失败 ${branchQuality.qualityGateFailedReportCount} 份，待审批忽略 ${branchQuality.pendingSuppressionCount} 个，到期风险 ${branchQuality.expiredAcceptedRiskCount} 个。`
        : '当前版本还没有代码巡检报告，进入测试/发布前建议补齐。',
      key: 'inspection',
      level:
        branchQuality.qualityGateFailedReportCount ||
        branchQuality.expiredAcceptedRiskCount ||
        highRiskInspectionCount ||
        actionRequiredBranchQualityCount
          ? 'warning'
          : dashboard.codeInspectionReports.length
            ? 'success'
            : 'info',
      title: '代码巡检',
      value: branchQuality.qualityGateFailedReportCount
        ? `${branchQuality.qualityGateFailedReportCount} 份门禁失败`
        : actionRequiredBranchQualityCount
        ? `${actionRequiredBranchQualityCount} 个分支待治理`
        : highRiskInspectionCount
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
  const actionRequiredBranchQualityCount = dashboard.summary.branch_quality_action_required;
  const pendingScanBranchQualityCount = dashboard.summary.branch_quality_pending_scan;
  const highRiskInspectionCount = dashboard.codeInspectionReports.filter((report) => {
    const riskLevel = report.risk_level.toLowerCase();
    return riskLevel === 'blocker' || riskLevel === 'critical' || riskLevel === 'high';
  }).length;
  const pendingCodeReviewCount = dashboard.summary.pending_code_review_reports;
  const releaseBlockerCount = dashboard.blockers.filter((blocker) => blocker.sourceType === 'jenkins_release').length;
  const branchQuality = summarizeBranchQualityGovernance(dashboard);
  const firstBranchConfig = dashboard.branchConfigs[0];
  const firstTask = dashboard.tasks[0];
  const firstCodeReviewReport = dashboard.codeReviewReports[0];
  const firstKnowledgeDeposit = dashboard.knowledgeDeposits[0];
  const taskActionHref = firstTask
    ? internalHref('/delivery/rd-tasks', { task_id: firstTask.id })
    : dashboard.version.productId
      ? internalHref('/delivery/rd-tasks', { product_id: dashboard.version.productId })
      : undefined;
  return [
    {
      actionHref: internalHref('/delivery/requirements', { version_id: dashboard.version.id }),
      actionLabel: blockedRequirementCount ? '处理需求' : '查看需求',
      detail: blockedRequirementCount
        ? `${dashboard.summary.requirements} 条需求 · 阻塞 ${blockedRequirementCount} 条`
        : `${dashboard.summary.requirements} 条需求 · 可推进`,
      key: 'requirements',
      level: blockedRequirementCount ? 'warning' : 'success',
      title: '需求范围',
      value: blockedRequirementCount ? '范围有阻塞' : '范围可推进',
    },
    {
      actionHref: taskActionHref,
      actionLabel: '查看任务',
      detail: runningTaskCount
        ? `${dashboard.summary.tasks} 个任务 · 运行中 ${runningTaskCount} 个`
        : `${dashboard.summary.tasks} 个任务 · 暂无运行中`,
      key: 'tasks',
      level: runningTaskCount ? 'info' : 'success',
      title: '研发任务',
      value: runningTaskCount ? '任务进行中' : '任务稳定',
    },
    {
      actionHref: firstBranchConfig
        ? internalHref('/delivery/versions', {
            branch_config_id: firstBranchConfig.id,
            version_id: dashboard.version.id,
          })
        : internalHref('/delivery/versions', { version_id: dashboard.version.id }),
      actionLabel: '处理分支',
      detail: notCreatedBranchCount
        ? `${dashboard.summary.branch_configs} 个分支 · 未创建 ${notCreatedBranchCount} 个`
        : actionRequiredBranchQualityCount || pendingScanBranchQualityCount
          ? `${dashboard.summary.branch_configs} 个分支 · 待治理 ${actionRequiredBranchQualityCount} 个 · 待巡检 ${pendingScanBranchQualityCount} 个`
          : `${dashboard.summary.branch_configs} 个分支 · 已登记`,
      key: 'branches',
      level:
        notCreatedBranchCount || actionRequiredBranchQualityCount || pendingScanBranchQualityCount
          ? 'warning'
          : 'success',
      title: '代码分支',
      value: notCreatedBranchCount
        ? '分支待维护'
        : actionRequiredBranchQualityCount || pendingScanBranchQualityCount
          ? '分支质量待治理'
          : '分支就绪',
    },
    {
      actionHref: internalHref('/governance/code-inspections', { version_id: dashboard.version.id }),
      actionLabel: '查看巡检',
      detail: highRiskInspectionCount
        ? `${dashboard.summary.code_inspection_reports} 份报告 · 高风险 ${highRiskInspectionCount} 份`
        : actionRequiredBranchQualityCount ||
            pendingScanBranchQualityCount ||
            branchQuality.qualityGateFailedReportCount ||
            branchQuality.pendingSuppressionCount ||
            branchQuality.expiredAcceptedRiskCount
          ? `${dashboard.summary.code_inspection_reports} 份报告 · 待治理分支 ${actionRequiredBranchQualityCount} 个 · 待巡检 ${pendingScanBranchQualityCount} 个 · 门禁失败 ${branchQuality.qualityGateFailedReportCount} 份 · 待审批忽略 ${branchQuality.pendingSuppressionCount} 个 · 到期风险 ${branchQuality.expiredAcceptedRiskCount} 个`
          : `${dashboard.summary.code_inspection_reports} 份报告 · 暂无高风险`,
      key: 'inspections',
      level:
        highRiskInspectionCount ||
        actionRequiredBranchQualityCount ||
        pendingScanBranchQualityCount ||
        branchQuality.qualityGateFailedReportCount ||
        branchQuality.expiredAcceptedRiskCount
          ? 'warning'
          : 'success',
      title: '代码巡检',
      value:
        highRiskInspectionCount ||
        actionRequiredBranchQualityCount ||
        pendingScanBranchQualityCount ||
        branchQuality.qualityGateFailedReportCount ||
        branchQuality.expiredAcceptedRiskCount
          ? '质量待治理'
          : '质量可控',
    },
    {
      actionHref: firstCodeReviewReport
        ? internalHref('/delivery/rd-tasks', { code_review_report_id: firstCodeReviewReport.id })
        : taskActionHref,
      actionLabel: pendingCodeReviewCount ? '处理评审' : '查看评审',
      detail: pendingCodeReviewCount
        ? `${dashboard.summary.code_review_reports} 份报告 · 待确认 ${pendingCodeReviewCount} 份`
        : `${dashboard.summary.code_review_reports} 份报告 · 暂无待确认`,
      key: 'code-reviews',
      level: pendingCodeReviewCount ? 'warning' : 'success',
      title: '代码评审',
      value: pendingCodeReviewCount ? '评审待确认' : '评审已收敛',
    },
    {
      actionHref: internalHref('/delivery/bugs', { version_id: dashboard.version.id }),
      actionLabel: dashboard.summary.open_bugs ? '处理版本 Bug' : '查看版本 Bug',
      detail: dashboard.summary.open_bugs
        ? `${dashboard.summary.bugs} 个 Bug · 未关闭 ${dashboard.summary.open_bugs} 个`
        : `${dashboard.summary.bugs} 个 Bug · 已收敛`,
      key: 'bugs',
      level: dashboard.summary.open_bugs ? 'error' : 'success',
      title: 'Bug 收敛',
      value: dashboard.summary.open_bugs ? 'Bug 待关闭' : 'Bug 已收敛',
    },
    {
      actionHref: firstKnowledgeDeposit
        ? fullChainSubjectHref('knowledge_deposit', firstKnowledgeDeposit.id)
        : fullChainSubjectHref('product_version', dashboard.version.id),
      actionLabel: '查看沉淀',
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
      actionHref: internalHref('/governance/devops', { version_id: dashboard.version.id }),
      actionLabel: releaseBlockerCount ? '补充发布' : '查看发布',
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
