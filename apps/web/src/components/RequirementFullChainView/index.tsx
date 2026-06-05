import { Descriptions, Space, Tag, Timeline, Typography } from 'antd';

import { StatusTag } from '../ManagementListPage';
import type { RequirementFullChainRecord } from '../../services/aiBrain';

const fullChainTypeLabels: Record<string, string> = {
  ai_task: 'AI 任务',
  bug: 'Bug',
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
  bug: 'red',
  code_review_report: 'purple',
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

const { Text } = Typography;

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

function buildFullChainStageItems(fullChain: RequirementFullChainRecord) {
  const summary = fullChain.summary;
  const stages = [
    {
      count: 1,
      detail: `${fullChain.requirement.status} · 1 项`,
      title: '需求',
    },
    {
      count: fullChain.iterationVersion ? 1 : 0,
      detail: fullChain.iterationVersion
        ? `${fullChain.iterationVersion.status ?? '-'} · ${
            fullChain.iterationVersion.code ?? fullChain.iterationVersion.id
          }`
        : '未排期',
      title: '迭代版本',
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
      count: summary.gitSnapshots + summary.codeReviewReports,
      detail: `${summary.gitSnapshots} 快照 / ${summary.codeReviewReports} 报告`,
      title: 'PR/代码评审',
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

export function RequirementFullChainView({ fullChain }: { fullChain: RequirementFullChainRecord }) {
  const stageItems = buildFullChainStageItems(fullChain);
  const firstPendingIndex = stageItems.findIndex((item) => item.status === 'wait');
  const requirementStatus = requirementStatusLabels[fullChain.requirement.status];

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <Descriptions bordered column={2} size="small">
        <Descriptions.Item label="需求" span={2}>
          <Space size={8} wrap>
            <Text strong>{fullChain.requirement.title}</Text>
            <Tag>{fullChain.requirement.id}</Tag>
            <StatusTag
              color={requirementStatus?.color ?? 'default'}
              label={requirementStatus?.label ?? fullChain.requirement.status}
            />
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="产品">
          {fullChain.product?.code ?? fullChain.requirement.product}
          {fullChain.product?.name ? ` · ${fullChain.product.name}` : ''}
        </Descriptions.Item>
        <Descriptions.Item label="迭代版本">
          {fullChain.iterationVersion
            ? `${fullChain.iterationVersion.code ?? fullChain.iterationVersion.id} · ${
                fullChain.iterationVersion.name ?? fullChain.iterationVersion.id
              }`
            : '未排期'}
        </Descriptions.Item>
        <Descriptions.Item label="链路摘要" span={2}>
          <Space size={[4, 4]} wrap>
            {renderSummaryTag('AI 任务', fullChain.summary.aiTasks, 'blue')}
            {renderSummaryTag('Review', fullChain.summary.reviews, 'cyan')}
            {renderSummaryTag('PR/MR 快照', fullChain.summary.gitSnapshots, 'geekblue')}
            {renderSummaryTag('代码评审', fullChain.summary.codeReviewReports, 'purple')}
            {renderSummaryTag('Bug', fullChain.summary.bugs, 'red')}
            {renderSummaryTag('发布记录', fullChain.summary.jenkinsReleases, 'orange')}
            {renderSummaryTag('知识沉淀', fullChain.summary.knowledgeDeposits, 'green')}
          </Space>
        </Descriptions.Item>
      </Descriptions>
      <section aria-label="全链路阶段进度">
        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
          <Text strong>阶段进度</Text>
          <div
            aria-label="阶段进度清单"
            role="list"
            style={{
              display: 'grid',
              gap: 12,
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              width: '100%',
            }}
          >
            {stageItems.map((item, itemIndex) => {
              const isFinished = item.status === 'finish';
              const isCurrent =
                firstPendingIndex >= 0 ? itemIndex === firstPendingIndex : itemIndex === stageItems.length - 1;
              return (
                <div
                  key={item.title}
                  role="listitem"
                  style={{
                    alignItems: 'flex-start',
                    background: isFinished ? '#f0f7ff' : '#fafafa',
                    border: `1px solid ${isCurrent ? '#1677ff' : isFinished ? '#91caff' : '#f0f0f0'}`,
                    borderRadius: 8,
                    display: 'flex',
                    gap: 8,
                    minHeight: 72,
                    minWidth: 0,
                    padding: '10px 12px',
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
                  <span style={{ display: 'block', minWidth: 0 }}>
                    <Text strong style={{ display: 'block', whiteSpace: 'nowrap' }}>
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
      <Timeline
        items={fullChain.timeline.map((item) => ({
          content: (
            <Space orientation="vertical" size={2}>
              <Space size={8} wrap>
                <Tag color={fullChainTypeColors[item.type] ?? 'default'}>
                  {fullChainTypeLabel(item.type)}
                </Tag>
                <Text strong>{item.title}</Text>
                {item.status ? <Tag>{item.status}</Tag> : null}
              </Space>
              <Text type="secondary">
                {item.occurredAt} · {item.subjectId}
              </Text>
            </Space>
          ),
          color: fullChainTypeColors[item.type] ?? 'blue',
        }))}
      />
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
