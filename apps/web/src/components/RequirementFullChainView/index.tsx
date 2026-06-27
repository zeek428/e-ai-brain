import { Button, Collapse, Descriptions, Select, Space, Tag, Timeline, Typography } from 'antd';
import { useMemo, useState } from 'react';

import { StatusTag } from '../ManagementListPage';
import type { RequirementRecord } from '../../data/management';
import type { RequirementFullChainRecord } from '../../services/aiBrain';

const fullChainTypeLabels: Record<string, string> = {
  ai_task: 'AI 任务',
  audit_event: '审计事件',
  branch_config: '代码分支',
  bug: 'Bug',
  code_inspection_report: '代码巡检',
  code_review_report: '代码评审',
  git_snapshot: 'PR/MR 快照',
  iteration_version: '迭代版本',
  jenkins_release: '发布',
  knowledge_deposit: '知识沉淀',
  requirement: '需求',
  review: '人工确认',
};

const taskTypeLabels: Record<string, string> = {
  automated_testing: '自动化测试',
  code_review: '代码评审',
  development_planning: '开发计划',
  post_release_analysis: '上线后分析',
  product_detail_design: '产品详细设计',
  release_readiness: '发布评估',
  technical_solution: '技术方案',
};

const fullChainTypeColors: Record<string, string> = {
  audit_event: 'default',
  branch_config: 'gold',
  bug: 'red',
  code_review_report: 'purple',
  code_inspection_report: 'magenta',
  git_snapshot: 'blue',
  jenkins_release: 'orange',
  knowledge_deposit: 'green',
  review: 'cyan',
};

const requirementStatusLabels: Record<string, { color: string; label: string }> = {
  accepted: { color: 'green', label: '已验收' },
  approved: { color: 'green', label: '需求池' },
  cancelled: { color: 'default', label: '已取消' },
  closed: { color: 'default', label: '已关闭' },
  code_reviewing: { color: 'purple', label: '代码评审中' },
  deferred: { color: 'default', label: '暂缓' },
  designing: { color: 'blue', label: '设计中' },
  developing: { color: 'geekblue', label: '开发中' },
  draft: { color: 'default', label: '草稿' },
  planned: { color: 'cyan', label: '已排期' },
  ready_for_dev: { color: 'lime', label: '待开发' },
  ready_for_release: { color: 'orange', label: '待发布' },
  rejected: { color: 'red', label: '已拒绝' },
  released: { color: 'green', label: '已发布' },
  submitted: { color: 'gold', label: '待评审' },
  testing: { color: 'volcano', label: '测试中' },
};

const iterationVersionStatusLabels: Record<string, { color: string; label: string }> = {
  active: { color: 'blue', label: '开发中' },
  archived: { color: 'default', label: '已归档' },
  planning: { color: 'gold', label: '规划中' },
  released: { color: 'green', label: '已发布' },
  testing: { color: 'purple', label: '测试中' },
};

const branchStatusLabels: Record<string, { color: string; label: string }> = {
  active: { color: 'blue', label: '使用中' },
  archived: { color: 'default', label: '已归档' },
  merged: { color: 'purple', label: '已合并' },
  not_created: { color: 'default', label: '未创建' },
  released: { color: 'green', label: '已发布' },
  testing: { color: 'volcano', label: '测试中' },
};

const { Link, Text } = Typography;

function fullChainTypeLabel(type: string) {
  return fullChainTypeLabels[type] ?? type;
}

function renderSummaryTag(label: string, value: number, color?: string) {
  const separator = /^[A-Za-z]/.test(label) ? ' ' : '';
  return (
    <Tag color={color}>
      {value} 个{separator}
      {label}
    </Tag>
  );
}

function formatRequirementStatus(status: string) {
  return requirementStatusLabels[status]?.label ?? status;
}

function formatIterationVersionStatus(status?: string) {
  if (!status) {
    return '-';
  }
  return iterationVersionStatusLabels[status]?.label ?? status;
}

function renderTimelineStatusTag(type: string, status?: string) {
  if (!status) {
    return null;
  }
  if (type === 'requirement') {
    const statusLabel = requirementStatusLabels[status];
    return <StatusTag color={statusLabel?.color ?? 'default'} label={statusLabel?.label ?? status} />;
  }
  if (type === 'iteration_version') {
    const statusLabel = iterationVersionStatusLabels[status];
    return <StatusTag color={statusLabel?.color ?? 'default'} label={statusLabel?.label ?? status} />;
  }
  return <Tag>{status}</Tag>;
}

function buildFullChainStageItems(fullChain: RequirementFullChainRecord) {
  const summary = fullChain.summary;
  const stages = [
    {
      count: 1,
      detail: `${formatRequirementStatus(fullChain.requirement.status)} · 1 项`,
      title: '需求',
    },
    {
      count: fullChain.iterationVersion ? 1 : 0,
      detail: fullChain.iterationVersion
        ? `${formatIterationVersionStatus(fullChain.iterationVersion.status)} · ${
            fullChain.iterationVersion.code ?? fullChain.iterationVersion.id
          }`
        : '未排期',
      title: '迭代版本',
    },
    {
      count: summary.branchConfigs,
      detail: `${summary.branchConfigs} 条`,
      title: '代码分支',
    },
    {
      count: summary.aiTasks,
      detail: `${summary.aiTasks} 项`,
      title: 'AI 任务',
    },
    {
      count: summary.reviews,
      detail: `${summary.reviews} 项`,
      title: 'Review',
    },
    {
      count: summary.gitSnapshots + summary.codeReviewReports + summary.codeInspectionReports,
      detail: `${summary.gitSnapshots} 快照 / ${summary.codeReviewReports} 评审 / ${summary.codeInspectionReports} 巡检`,
      title: 'PR/代码评审/巡检',
    },
    {
      count: summary.bugs,
      detail: `${summary.bugs} 项`,
      title: 'Bug',
    },
    {
      count: summary.jenkinsReleases,
      detail: `${summary.jenkinsReleases} 项`,
      title: '发布',
    },
    {
      count: summary.knowledgeDeposits,
      detail: `${summary.knowledgeDeposits} 项`,
      title: '知识沉淀',
    },
    {
      count: summary.auditEvents,
      detail: `${summary.auditEvents} 条`,
      title: '审计事件',
    },
  ];

  return stages.map((stage, index) => ({
    detail: stage.detail,
    index: index + 1,
    status: stage.count > 0 ? ('finish' as const) : ('wait' as const),
    title: stage.title,
  }));
}

function formatRiskLevel(level?: string) {
  if (level === 'high') {
    return '高';
  }
  if (level === 'medium') {
    return '中';
  }
  if (level === 'low') {
    return '低';
  }
  return level || '-';
}

function formatSnapshotRisk(snapshot: RequirementFullChainRecord['gitSnapshots'][number]) {
  const summary = snapshot.riskSummary;
  if (!summary) {
    return '-';
  }
  const largestFile = summary.largestFile?.path
    ? `最大文件 ${summary.largestFile.path} (${summary.largestFile.lineCount ?? 0} 行)`
    : '无最大文件';
  return `${formatRiskLevel(summary.riskLevel)}风险 · ${summary.fileCount ?? 0} 文件 · +${
    summary.totalAdditions ?? 0
  }/-${summary.totalDeletions ?? 0} · ${largestFile}`;
}

function markdownValue(value: unknown) {
  if (value === undefined || value === null || value === '') {
    return '-';
  }
  return String(value).replaceAll('|', '\\|').replace(/\r?\n/g, ' ');
}

function markdownList<T>(items: T[], renderItem: (item: T) => string) {
  if (!items.length) {
    return '- 暂无关联记录';
  }
  return items.map(renderItem).join('\n');
}

function buildFullChainMarkdownReport(fullChain: RequirementFullChainRecord) {
  const requirementStatus = formatRequirementStatus(fullChain.requirement.status);
  const iterationVersion = fullChain.iterationVersion;
  const productName = `${fullChain.product?.code ?? fullChain.requirement.product}${
    fullChain.product?.name ? ` · ${fullChain.product.name}` : ''
  }`;
  const versionName = iterationVersion
    ? `${iterationVersion.code ?? iterationVersion.id} · ${iterationVersion.name ?? iterationVersion.id} · ${formatIterationVersionStatus(
        iterationVersion.status,
      )}`
    : '未排期';

  return [
    `# 需求全链路报告：${fullChain.requirement.title}`,
    '',
    `生成时间：${new Date().toISOString()}`,
    '',
    '## 链路摘要',
    '',
    `- 需求：${fullChain.requirement.title} (${fullChain.requirement.id})`,
    `- 状态：${requirementStatus}`,
    `- 产品：${productName}`,
    `- 迭代版本：${versionName}`,
    `- 代码分支：${fullChain.summary.branchConfigs}`,
    `- AI 任务：${fullChain.summary.aiTasks}`,
    `- Review：${fullChain.summary.reviews}`,
    `- PR/MR 快照：${fullChain.summary.gitSnapshots}`,
    `- 代码评审：${fullChain.summary.codeReviewReports}`,
    `- 代码巡检：${fullChain.summary.codeInspectionReports}`,
    `- Bug：${fullChain.summary.bugs}`,
    `- 发布记录：${fullChain.summary.jenkinsReleases}`,
    `- 知识沉淀：${fullChain.summary.knowledgeDeposits}`,
    `- 审计事件：${fullChain.summary.auditEvents}`,
    '',
    '## 阶段明细',
    '',
    '### 代码分支',
    markdownList(
      fullChain.branchConfigs,
      (branch) =>
        `- ${branch.repositoryName ?? branch.repositoryId} · ${branch.baseBranch} -> ${branch.workingBranch} · ${
          branchStatusLabels[branch.branchStatus]?.label ?? branch.branchStatus
        }`,
    ),
    '',
    '### AI 任务',
    markdownList(
      fullChain.aiTasks,
      (task) => `- ${task.label} (${task.id}) · ${taskTypeLabels[task.type] ?? task.type} · ${task.status}`,
    ),
    '',
    '### Review',
    markdownList(
      fullChain.reviews,
      (review) => `- ${review.aiTaskId ? `${review.aiTaskId} · ` : ''}${review.id} · ${review.status} · ${review.createdAt}`,
    ),
    '',
    '### PR/MR 快照',
    markdownList(
      fullChain.gitSnapshots,
      (snapshot) => `- ${snapshot.id} · MR/PR ${snapshot.mrIid} · ${formatSnapshotRisk(snapshot)}`,
    ),
    '',
    '### 代码评审',
    markdownList(
      fullChain.codeReviewReports,
      (report) => `- ${report.summary || `代码评审：${report.id}`} (${report.id}) · ${report.status} · ${formatRiskLevel(report.riskLevel)}风险`,
    ),
    '',
    '### 代码巡检',
    markdownList(
      fullChain.codeInspectionReports,
      (report) =>
        `- ${report.summary || `代码巡检：${report.id}`} (${report.id}) · ${report.status} · ${formatRiskLevel(
          report.risk_level,
        )}风险`,
    ),
    '',
    '### Bug',
    markdownList(fullChain.bugs, (bug) => `- ${bug.title} (${bug.id}) · ${bug.severity} · ${bug.status}`),
    '',
    '### 发布记录',
    markdownList(
      fullChain.jenkinsReleases,
      (release) =>
        `- ${release.jobName ? `${release.jobName} · ` : ''}${release.buildId ?? release.id} (${release.id}) · ${release.status}`,
    ),
    '',
    '### 知识沉淀',
    markdownList(
      fullChain.knowledgeDeposits,
      (deposit) => `- ${deposit.title} (${deposit.id}) · ${deposit.status}`,
    ),
    '',
    '### 审计事件',
    markdownList(
      fullChain.auditEvents,
      (event) =>
        `- ${event.eventType} (${event.id}) · ${event.actorId ?? '-'} · ${event.subjectType ?? '-'}:${
          event.subjectId ?? '-'
        } · ${event.createdAt}`,
    ),
    '',
    '## 时间线',
    '',
    '| 时间 | 类型 | 标题 | 状态 | 关联对象 |',
    '| --- | --- | --- | --- | --- |',
    ...fullChain.timeline.map(
      (item) =>
        `| ${markdownValue(item.occurredAt)} | ${markdownValue(fullChainTypeLabel(item.type))} | ${markdownValue(
          item.title,
        )} | ${markdownValue(item.status)} | ${markdownValue(item.subjectId)} |`,
    ),
    '',
  ].join('\n');
}

function downloadFullChainMarkdownReport(fullChain: RequirementFullChainRecord) {
  const report = buildFullChainMarkdownReport(fullChain);
  const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `requirement-full-chain-${fullChain.requirement.id}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function buildVersionRequirementStats(requirements: RequirementRecord[]) {
  return requirements.reduce<Record<string, number>>((stats, requirement) => {
    stats[requirement.status] = (stats[requirement.status] ?? 0) + 1;
    return stats;
  }, {});
}

function withQuery(path: string, key: string, value: string) {
  return `${path}?${key}=${encodeURIComponent(value)}`;
}

function withQueryParams(path: string, params: Record<string, string | undefined>) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      searchParams.set(key, value);
    }
  });
  const queryString = searchParams.toString();
  return queryString ? `${path}?${queryString}` : path;
}

function renderEntityDetail({
  href,
  linkLabel,
  meta,
  title,
}: {
  href: string;
  linkLabel: string;
  meta: string;
  title: string;
}) {
  return (
    <Space key={`${href}-${title}`} orientation="vertical" size={2}>
      <Text>{title}</Text>
      <Space size={8} wrap>
        <Text type="secondary">{meta}</Text>
        <Link href={href}>{linkLabel}</Link>
      </Space>
    </Space>
  );
}

function renderEmptyStage() {
  return <Text type="secondary">暂无关联记录</Text>;
}

function buildStageDetailItems(fullChain: RequirementFullChainRecord) {
  const requirement = fullChain.requirement;
  const iterationVersion = fullChain.iterationVersion;
  const items = [
    {
      children: renderEntityDetail({
        href: withQuery('/delivery/requirements', 'requirement_id', requirement.id),
        linkLabel: `查看需求 ${requirement.id}`,
        meta: `${formatRequirementStatus(requirement.status)} · ${requirement.createdAt}`,
        title: requirement.title,
      }),
      key: 'requirement',
      label: '需求',
    },
    {
      children: iterationVersion
        ? renderEntityDetail({
            href: withQuery('/delivery/versions', 'version_id', iterationVersion.id),
            linkLabel: `查看迭代 ${iterationVersion.id}`,
            meta: `${formatIterationVersionStatus(iterationVersion.status)} · ${iterationVersion.id}`,
            title: iterationVersion.name ?? iterationVersion.code ?? iterationVersion.id,
          })
        : renderEmptyStage(),
      key: 'iteration_version',
      label: '迭代版本',
    },
    {
      children: fullChain.branchConfigs.length ? (
        <Space orientation="vertical" size={10}>
          {fullChain.branchConfigs.map((branch) =>
            renderEntityDetail({
              href: withQueryParams('/delivery/versions', {
                branch_config_id: branch.id,
                version_id: branch.versionId,
              }),
              linkLabel: `查看分支 ${branch.id}`,
              meta: `${branch.baseBranch} -> ${branch.workingBranch} · ${
                branchStatusLabels[branch.branchStatus]?.label ?? branch.branchStatus
              }`,
              title: `${branch.repositoryName ?? branch.repositoryId} · ${branch.workingBranch}`,
            }),
          )}
        </Space>
      ) : (
        renderEmptyStage()
      ),
      key: 'branch_configs',
      label: `代码分支 (${fullChain.branchConfigs.length})`,
    },
    {
      children: fullChain.aiTasks.length ? (
        <Space orientation="vertical" size={10}>
          {fullChain.aiTasks.map((task) =>
            renderEntityDetail({
              href: withQuery('/delivery/rd-tasks', 'task_id', task.id),
              linkLabel: `查看任务 ${task.id}`,
              meta: `${taskTypeLabels[task.type] ?? task.type} · ${task.status} · ${task.createdAt}`,
              title: task.label,
            }),
          )}
        </Space>
      ) : (
        renderEmptyStage()
      ),
      key: 'ai_tasks',
      label: `AI 任务 (${fullChain.aiTasks.length})`,
    },
    {
      children: fullChain.reviews.length ? (
        <Space orientation="vertical" size={10}>
          {fullChain.reviews.map((review) =>
            renderEntityDetail({
              href: withQuery('/delivery/rd-tasks', 'review_id', review.id),
              linkLabel: `查看 Review ${review.id}`,
              meta: `${review.status} · ${review.createdAt}`,
              title: review.aiTaskId ? `人工确认：${review.aiTaskId}` : `人工确认：${review.id}`,
            }),
          )}
        </Space>
      ) : (
        renderEmptyStage()
      ),
      key: 'reviews',
      label: `Review (${fullChain.reviews.length})`,
    },
    {
      children: fullChain.gitSnapshots.length || fullChain.codeReviewReports.length || fullChain.codeInspectionReports.length ? (
        <Space orientation="vertical" size={10}>
          {fullChain.gitSnapshots.map((snapshot) =>
            renderEntityDetail({
              href: withQuery('/delivery/rd-tasks', 'git_snapshot_id', snapshot.id),
              linkLabel: `查看快照 ${snapshot.id}`,
              meta: `MR/PR ${snapshot.mrIid} · ${formatSnapshotRisk(snapshot)}`,
              title: `PR/MR 快照：${snapshot.id}`,
            }),
          )}
          {fullChain.codeReviewReports.map((report) =>
            renderEntityDetail({
              href: withQuery('/delivery/rd-tasks', 'code_review_report_id', report.id),
              linkLabel: `查看代码评审 ${report.id}`,
              meta: `${report.status} · ${formatRiskLevel(report.riskLevel)}风险`,
              title: report.summary || `代码评审：${report.id}`,
            }),
          )}
          {fullChain.codeInspectionReports.map((report) =>
            renderEntityDetail({
              href: withQuery('/governance/code-inspections', 'source_id', report.id),
              linkLabel: `查看代码巡检 ${report.id}`,
              meta: `${report.status} · ${formatRiskLevel(report.risk_level)}风险 · ${report.branch ?? '-'}`,
              title: report.summary || `代码巡检：${report.id}`,
            }),
          )}
        </Space>
      ) : (
        renderEmptyStage()
      ),
      key: 'code_review',
      label: `PR/代码评审/巡检 (${
        fullChain.gitSnapshots.length + fullChain.codeReviewReports.length + fullChain.codeInspectionReports.length
      })`,
    },
    {
      children: fullChain.bugs.length ? (
        <Space orientation="vertical" size={10}>
          {fullChain.bugs.map((bug) =>
            renderEntityDetail({
              href: withQuery('/delivery/bugs', 'bug_id', bug.id),
              linkLabel: `查看 Bug ${bug.id}`,
              meta: `${bug.severity} · ${bug.status} · ${bug.createdAt}`,
              title: bug.title,
            }),
          )}
        </Space>
      ) : (
        renderEmptyStage()
      ),
      key: 'bugs',
      label: `Bug (${fullChain.bugs.length})`,
    },
    {
      children: fullChain.jenkinsReleases.length ? (
        <Space orientation="vertical" size={10}>
          {fullChain.jenkinsReleases.map((release) =>
            renderEntityDetail({
              href: withQuery('/governance/devops', 'release_id', release.id),
              linkLabel: `查看发布 ${release.id}`,
              meta: `${release.status} · ${release.createdAt}`,
              title: release.jobName ? `${release.jobName} · ${release.buildId ?? release.id}` : release.id,
            }),
          )}
        </Space>
      ) : (
        renderEmptyStage()
      ),
      key: 'jenkins_releases',
      label: `发布 (${fullChain.jenkinsReleases.length})`,
    },
    {
      children: fullChain.knowledgeDeposits.length ? (
        <Space orientation="vertical" size={10}>
          {fullChain.knowledgeDeposits.map((deposit) =>
            renderEntityDetail({
              href: withQuery('/knowledge/documents', 'deposit_id', deposit.id),
              linkLabel: `查看知识沉淀 ${deposit.id}`,
              meta: `${deposit.status} · ${deposit.id}`,
              title: deposit.title,
            }),
          )}
        </Space>
      ) : (
        renderEmptyStage()
      ),
      key: 'knowledge_deposits',
      label: `知识沉淀 (${fullChain.knowledgeDeposits.length})`,
    },
    {
      children: fullChain.auditEvents.length ? (
        <Space orientation="vertical" size={10}>
          {fullChain.auditEvents.map((event) =>
            renderEntityDetail({
              href: withQuery('/governance/audit', 'audit_id', event.id),
              linkLabel: `查看审计 ${event.id}`,
              meta: `${event.actorId ?? '-'} · ${event.subjectType ?? '-'}:${event.subjectId ?? '-'} · ${
                event.createdAt
              }`,
              title: event.eventType,
            }),
          )}
        </Space>
      ) : (
        renderEmptyStage()
      ),
      key: 'audit_events',
      label: `审计事件 (${fullChain.auditEvents.length})`,
    },
  ];
  return items;
}

export function RequirementFullChainView({
  fullChain,
  versionRequirements = [],
}: {
  fullChain: RequirementFullChainRecord;
  versionRequirements?: RequirementRecord[];
}) {
  const [timelineTypeFilters, setTimelineTypeFilters] = useState<string[]>([]);
  const stageItems = buildFullChainStageItems(fullChain);
  const firstPendingIndex = stageItems.findIndex((item) => item.status === 'wait');
  const requirementStatus = requirementStatusLabels[fullChain.requirement.status];
  const versionRequirementStats = useMemo(
    () => buildVersionRequirementStats(versionRequirements),
    [versionRequirements],
  );
  const timelineTypeOptions = useMemo(
    () =>
      Array.from(new Set(fullChain.timeline.map((item) => item.type))).map((type) => ({
        label: fullChainTypeLabel(type),
        value: type,
      })),
    [fullChain.timeline],
  );
  const visibleTimeline = timelineTypeFilters.length
    ? fullChain.timeline.filter((item) => timelineTypeFilters.includes(item.type))
    : fullChain.timeline;

  return (
    <Space className="requirement-full-chain-view" orientation="vertical" size={16} style={{ width: '100%' }}>
      <section aria-label="需求链路摘要" className="requirement-full-chain-summary">
        <div className="requirement-full-chain-summary-label">需求</div>
        <div className="requirement-full-chain-summary-value requirement-full-chain-summary-wide">
          <Space align="center" size={8} wrap>
            <Space size={8} wrap>
              <Text strong>{fullChain.requirement.title}</Text>
              <Tag>{fullChain.requirement.id}</Tag>
              <StatusTag
                color={requirementStatus?.color ?? 'default'}
                label={requirementStatus?.label ?? fullChain.requirement.status}
              />
            </Space>
            <Button onClick={() => downloadFullChainMarkdownReport(fullChain)} size="small">
              导出链路报告
            </Button>
          </Space>
        </div>
        <div className="requirement-full-chain-summary-label">产品</div>
        <div className="requirement-full-chain-summary-value">
          {fullChain.product?.code ?? fullChain.requirement.product}
          {fullChain.product?.name ? ` · ${fullChain.product.name}` : ''}
        </div>
        <div className="requirement-full-chain-summary-label">迭代版本</div>
        <div className="requirement-full-chain-summary-value">
          {fullChain.iterationVersion
            ? `${fullChain.iterationVersion.code ?? fullChain.iterationVersion.id} · ${
                fullChain.iterationVersion.name ?? fullChain.iterationVersion.id
              }`
            : '未排期'}
        </div>
        <div className="requirement-full-chain-summary-label">链路摘要</div>
        <div className="requirement-full-chain-summary-value requirement-full-chain-summary-wide">
          <Space size={[4, 4]} wrap>
            {renderSummaryTag('AI 任务', fullChain.summary.aiTasks, 'blue')}
            {renderSummaryTag('Review', fullChain.summary.reviews, 'cyan')}
            {renderSummaryTag('代码分支', fullChain.summary.branchConfigs, 'gold')}
            {renderSummaryTag('PR/MR 快照', fullChain.summary.gitSnapshots, 'geekblue')}
            {renderSummaryTag('代码评审', fullChain.summary.codeReviewReports, 'purple')}
            {renderSummaryTag('代码巡检', fullChain.summary.codeInspectionReports, 'magenta')}
            {renderSummaryTag('Bug', fullChain.summary.bugs, 'red')}
            {renderSummaryTag('发布记录', fullChain.summary.jenkinsReleases, 'orange')}
            {renderSummaryTag('知识沉淀', fullChain.summary.knowledgeDeposits, 'green')}
            {renderSummaryTag('审计事件', fullChain.summary.auditEvents)}
          </Space>
        </div>
      </section>
      <section aria-label="全链路阶段进度">
        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
          <Text strong>阶段进度</Text>
          <div
            aria-label="阶段进度清单"
            className="requirement-full-chain-stage-grid"
            role="list"
          >
            {stageItems.map((item, itemIndex) => {
              const isFinished = item.status === 'finish';
              const isCurrent =
                firstPendingIndex >= 0 ? itemIndex === firstPendingIndex : itemIndex === stageItems.length - 1;
              return (
                <div
                  key={item.title}
                  className="requirement-full-chain-stage-card"
                  role="listitem"
                  style={{
                    background: isFinished ? '#f0f7ff' : '#fafafa',
                    border: `1px solid ${isCurrent ? '#1677ff' : isFinished ? '#91caff' : '#f0f0f0'}`,
                  }}
                >
                  <span
                    aria-hidden="true"
                    style={{
                      alignItems: 'center',
                      background: isFinished ? '#1677ff' : '#f0f0f0',
                      borderRadius: '50%',
                      color: isFinished ? '#fff' : '#595959',
                      display: 'inline-flex',
                      flex: '0 0 24px',
                      fontSize: 14,
                      height: 24,
                      justifyContent: 'center',
                      lineHeight: '24px',
                      marginTop: 1,
                      width: 24,
                    }}
                  >
                    {isFinished ? '✓' : item.index}
                  </span>
                  <span className="requirement-full-chain-stage-content">
                    <Text strong style={{ display: 'block' }}>
                      {item.title}
                    </Text>
                    <Text
                      type="secondary"
                      style={{
                        display: 'block',
                        lineHeight: 1.45,
                        overflowWrap: 'anywhere',
                        wordBreak: 'normal',
                      }}
                    >
                      {item.detail}
                    </Text>
                  </span>
                </div>
              );
            })}
          </div>
        </Space>
      </section>
      <section aria-label="全链路阶段明细">
        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
          <Text strong>阶段明细</Text>
          <Collapse
            defaultActiveKey={[
              'requirement',
              'iteration_version',
              'branch_configs',
              'ai_tasks',
              'reviews',
              'code_review',
              'bugs',
              'jenkins_releases',
              'knowledge_deposits',
              'audit_events',
            ]}
            items={buildStageDetailItems(fullChain)}
            size="small"
          />
        </Space>
      </section>
      {versionRequirements.length ? (
        <section aria-label="版本内需求对比">
          <Space orientation="vertical" size={8} style={{ width: '100%' }}>
            <Space align="center" size={8} wrap>
              <Text strong>版本内需求对比</Text>
              <Text type="secondary">
                当前版本共 {versionRequirements.length} 条需求，当前需求 {fullChain.requirement.id}
              </Text>
            </Space>
            <Space size={[4, 4]} wrap>
              {Object.entries(versionRequirementStats).map(([status, count]) => {
                const statusLabel = requirementStatusLabels[status];
                return (
                  <StatusTag
                    key={status}
                    color={statusLabel?.color ?? 'default'}
                    label={`${statusLabel?.label ?? status} ${count}`}
                  />
                );
              })}
            </Space>
            <Descriptions bordered column={1} size="small">
              {versionRequirements.slice(0, 8).map((requirement) => {
                const statusLabel = requirementStatusLabels[requirement.status];
                return (
                  <Descriptions.Item
                    key={requirement.id}
                    label={requirement.id === fullChain.requirement.id ? '当前需求' : requirement.id}
                  >
                    <Space size={8} wrap>
                      <Text strong={requirement.id === fullChain.requirement.id}>{requirement.title}</Text>
                      <StatusTag
                        color={statusLabel?.color ?? 'default'}
                        label={statusLabel?.label ?? requirement.status}
                      />
                      <Tag>{requirement.priority}</Tag>
                    </Space>
                  </Descriptions.Item>
                );
              })}
            </Descriptions>
          </Space>
        </section>
      ) : null}
      <section aria-label="全链路时间线">
        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
          <Space align="center" size={12} wrap>
            <Text strong>时间线</Text>
            <Select
              allowClear
              aria-label="时间线类型筛选"
              mode="multiple"
              onChange={setTimelineTypeFilters}
              options={timelineTypeOptions}
              placeholder="按类型筛选"
              style={{ minWidth: 260 }}
              value={timelineTypeFilters}
            />
            <Text type="secondary">
              {visibleTimeline.length} / {fullChain.timeline.length} 个事件
            </Text>
          </Space>
          {visibleTimeline.length ? (
            <Timeline
              items={visibleTimeline.map((item) => ({
                content: (
                  <Space orientation="vertical" size={2}>
                    <Space size={8} wrap>
                      <Tag color={fullChainTypeColors[item.type] ?? 'default'}>
                        {fullChainTypeLabel(item.type)}
                      </Tag>
                      <Text strong>{item.title}</Text>
                      {renderTimelineStatusTag(item.type, item.status)}
                    </Space>
                    <Text type="secondary">
                      {item.occurredAt} · {item.subjectId}
                    </Text>
                  </Space>
                ),
                color: fullChainTypeColors[item.type] ?? 'blue',
              }))}
            />
          ) : (
            renderEmptyStage()
          )}
        </Space>
      </section>
      {fullChain.aiTasks.length ? (
        <Descriptions bordered column={2} size="small" title="AI 任务明细">
          {fullChain.aiTasks.map((task) => (
            <Descriptions.Item key={task.id} label={taskTypeLabels[task.type] ?? task.type}>
              <Space orientation="vertical" size={2}>
                <Text>{task.label}</Text>
                <Text type="secondary">
                  {task.id} · {task.status}
                </Text>
              </Space>
            </Descriptions.Item>
          ))}
        </Descriptions>
      ) : null}
      {fullChain.gitSnapshots.length ? (
        <Descriptions bordered column={1} size="small" title="PR/MR 证据">
          {fullChain.gitSnapshots.map((snapshot) => (
            <Descriptions.Item key={snapshot.id} label={`快照 ${snapshot.mrIid}`}>
              <Space orientation="vertical" size={8} style={{ width: '100%' }}>
                <Space size={[6, 6]} wrap>
                  <Tag color="geekblue">{snapshot.id}</Tag>
                  <Tag color="purple">{formatSnapshotRisk(snapshot)}</Tag>
                  {snapshot.diffSizeBytes !== undefined ? <Tag>diff {snapshot.diffSizeBytes} bytes</Tag> : null}
                </Space>
                {snapshot.diffFileTree.length ? (
                  <Space size={[6, 6]} wrap>
                    {snapshot.diffFileTree.map((item) => (
                      <Tag key={item.path} color="blue">
                        {item.path} · {item.fileCount} 文件 · +{item.additions}/-{item.deletions}
                      </Tag>
                    ))}
                  </Space>
                ) : null}
                {snapshot.reviewChecklist.length ? (
                  <Space orientation="vertical" size={2}>
                    {snapshot.reviewChecklist.map((item) => (
                      <Text key={item} type="secondary">
                        {item}
                      </Text>
                    ))}
                  </Space>
                ) : null}
              </Space>
            </Descriptions.Item>
          ))}
        </Descriptions>
      ) : null}
    </Space>
  );
}
