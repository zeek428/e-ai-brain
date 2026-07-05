import {
  AuditOutlined,
  BarChartOutlined,
  BugOutlined,
  CloudServerOutlined,
  FileDoneOutlined,
  ReloadOutlined,
  RobotOutlined,
  UserSwitchOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Alert, Button, Empty, Select, Space, Tag, Typography } from 'antd';
import { type ReactNode, useCallback, useEffect, useMemo, useState } from 'react';

import { formatRemoteRowsError, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  fetchActiveProductOptions,
  fetchItTeamDashboard,
  type DashboardAuditSummary,
  type DashboardBugSummary,
  type DashboardKnowledgeSummary,
  type DashboardStatusCount,
  type DashboardTaskSummary,
  type ItTeamDashboard,
  type ProductFilterOption,
} from '../../services/aiBrain';
import { DashboardTrendSection } from './DashboardTrendSection';

const { Text, Title } = Typography;
const allProductsValue = '__all_products__';
const allTimeRangeValue = 'all';

const timeRangeOptions = [
  { label: '全部时间', value: allTimeRangeValue },
  { label: '近 7 天', value: '7d' },
  { label: '近 30 天', value: '30d' },
];

const formatDashboardGeneratedAt = (value?: string) => {
  if (!value || value === '-') {
    return '-';
  }
  const isoMatch = value.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})/);
  if (isoMatch) {
    return `${isoMatch[1]} ${isoMatch[2]}`;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const pad = (part: number) => part.toString().padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
};

const statusLabels: Record<string, { color: string; label: string }> = {
  accepted: { color: 'green', label: '已验收' },
  approved: { color: 'green', label: '已审批' },
  assigned: { color: 'blue', label: '已分派' },
  archived: { color: 'default', label: '已归档' },
  canceled: { color: 'default', label: '已取消' },
  closed: { color: 'default', label: '已关闭' },
  completed: { color: 'green', label: '已完成' },
  converted_to_requirement: { color: 'purple', label: '已转需求' },
  draft: { color: 'default', label: '草稿' },
  failed: { color: 'red', label: '失败' },
  fixed: { color: 'cyan', label: '已修复' },
  linked: { color: 'blue', label: '已关联' },
  needs_info: { color: 'orange', label: '需补充' },
  open: { color: 'red', label: '打开' },
  code_reviewing: { color: 'purple', label: '代码评审中' },
  deferred: { color: 'default', label: '已暂缓' },
  designing: { color: 'blue', label: '设计中' },
  developing: { color: 'geekblue', label: '开发中' },
  pending_approval: { color: 'gold', label: '待审批' },
  planned: { color: 'cyan', label: '已排期' },
  ready_for_dev: { color: 'lime', label: '待开发' },
  ready_for_release: { color: 'green', label: '待发布' },
  rejected: { color: 'red', label: '已拒绝' },
  released: { color: 'green', label: '已发布' },
  reopened: { color: 'volcano', label: '重新打开' },
  resolved: { color: 'green', label: '已解决' },
  running: { color: 'blue', label: '运行中' },
  submitted: { color: 'gold', label: '待评审' },
  success: { color: 'green', label: '成功' },
  suggested: { color: 'gold', label: '建议中' },
  task_created: { color: 'blue', label: '已生成任务' },
  testing: { color: 'orange', label: '测试中' },
  triaged: { color: 'gold', label: '已分诊' },
  verified: { color: 'green', label: '已验证' },
  waiting_more_info: { color: 'orange', label: '待补充' },
  waiting_review: { color: 'gold', label: '待确认' },
};

const severityLabels: Record<string, { color: string; label: string }> = {
  blocker: { color: 'red', label: '阻断' },
  critical: { color: 'volcano', label: '严重' },
  major: { color: 'orange', label: '主要' },
  minor: { color: 'blue', label: '次要' },
};

type DashboardHealthLevel = 'healthy' | 'risk' | 'watch';

type DashboardChartItem = {
  color: string;
  key: string;
  label: string;
  value: number;
};

type DashboardFocusMetric = {
  label: string;
  suffix?: string;
  value: number | string;
};

type DashboardFocusCardConfig = {
  icon: ReactNode;
  metrics: DashboardFocusMetric[];
  title: string;
  tone: DashboardHealthLevel | 'info';
  value: number | string;
};

type DashboardActionItem = {
  detail: string;
  href: string;
  key: string;
  level: DashboardHealthLevel;
  title: string;
  value: number | string;
};

type DashboardHealthSummary = {
  detail: string;
  level: DashboardHealthLevel;
  tags: string[];
  value: string;
};

const dashboardChartPalette = [
  '#1677ff',
  '#52c41a',
  '#faad14',
  '#ff7a45',
  '#722ed1',
  '#13c2c2',
  '#eb2f96',
];

const dashboardStatusColorMap: Record<string, string> = {
  accepted: '#52c41a',
  approved: '#52c41a',
  archived: '#8c8c8c',
  closed: '#8c8c8c',
  completed: '#52c41a',
  designing: '#1677ff',
  failed: '#cf1322',
  open: '#cf1322',
  pending_approval: '#faad14',
  released: '#52c41a',
  rejected: '#cf1322',
  running: '#1677ff',
  submitted: '#faad14',
  success: '#52c41a',
  suggested: '#faad14',
  task_created: '#1677ff',
  waiting_more_info: '#ff7a45',
  waiting_review: '#faad14',
};

const dashboardHealthLabels: Record<DashboardHealthLevel, { color: string; label: string }> = {
  healthy: { color: 'green', label: '稳定' },
  risk: { color: 'red', label: '高风险' },
  watch: { color: 'gold', label: '需关注' },
};

function normalizeError(error: unknown): RemoteRowsError {
  if (error instanceof Error) {
    const errorWithDetails = error as Error & {
      code?: string;
      traceId?: string;
    };
    return {
      code: errorWithDetails.code,
      message: error.message,
      traceId: errorWithDetails.traceId,
    };
  }
  return { message: '接口请求失败' };
}

function MetricSummary({
  items,
}: {
  items: Array<{ label: string; suffix?: string; value: number | string }>;
}) {
  return (
    <div className="dashboard-list">
      {items.map((item) => (
        <div className="dashboard-metric-row" key={item.label}>
          <Text type="secondary">{item.label}</Text>
          <Text strong>
            {item.value}
            {item.suffix ? <Text type="secondary"> {item.suffix}</Text> : null}
          </Text>
        </div>
      ))}
    </div>
  );
}

function toDashboardChartItems(counts: DashboardStatusCount[]): DashboardChartItem[] {
  return [...counts]
    .filter((item) => item.count > 0)
    .sort((left, right) => right.count - left.count)
    .map((item, index) => {
      const statusLabel = statusLabels[item.status] ?? { color: 'default', label: item.status };
      return {
        color: dashboardStatusColorMap[item.status] ?? dashboardChartPalette[index % dashboardChartPalette.length],
        key: item.status,
        label: statusLabel.label,
        value: item.count,
      };
    });
}

function DashboardBarChart({ ariaLabel, items }: { ariaLabel: string; items: DashboardChartItem[] }) {
  const total = items.reduce((sum, item) => sum + item.value, 0);
  if (total <= 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  return (
    <div aria-label={ariaLabel} className="dashboard-chart-list" role="list">
      {items.map((item) => {
        const percent = Math.max((item.value / total) * 100, 4);
        return (
          <div className="dashboard-chart-row" key={item.key} role="listitem">
            <div className="dashboard-chart-meta">
              <span className="dashboard-chart-dot" style={{ backgroundColor: item.color }} />
              <Text>{item.label}</Text>
              <Text strong>{item.value}</Text>
            </div>
            <div className="dashboard-chart-track">
              <div
                aria-hidden="true"
                className="dashboard-chart-bar"
                style={{ backgroundColor: item.color, width: `${percent}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function DashboardFocusCard({ icon, metrics, title, tone, value }: DashboardFocusCardConfig) {
  return (
    <section className="dashboard-focus-card" data-tone={tone} role="listitem">
      <div className="dashboard-focus-card-header">
        <span className="dashboard-focus-card-icon">{icon}</span>
        <Text strong>{title}</Text>
      </div>
      <strong className="dashboard-focus-card-value">{value}</strong>
      <div className="dashboard-focus-metrics">
        {metrics.map((metric) => (
          <div className="dashboard-focus-metric" key={metric.label}>
            <Text type="secondary">{metric.label}</Text>
            <Text strong>
              {metric.value}
              {metric.suffix ? <Text type="secondary"> {metric.suffix}</Text> : null}
            </Text>
          </div>
        ))}
      </div>
    </section>
  );
}

function TaskList({ tasks }: { tasks: DashboardTaskSummary[] }) {
  if (tasks.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  return (
    <div className="dashboard-list">
      {tasks.map((task) => (
        <div className="dashboard-list-item" key={task.id}>
          <Text strong>{task.title}</Text>
          <Space size={8} wrap>
            <Tag>{task.type}</Tag>
            <Tag color={statusLabels[task.status]?.color ?? 'default'}>
              {statusLabels[task.status]?.label ?? task.status}
            </Tag>
          </Space>
        </div>
      ))}
    </div>
  );
}

function summarizeDashboardHealth(dashboard?: ItTeamDashboard): DashboardHealthSummary {
  if (!dashboard) {
    return {
      detail: '等待看板数据加载后生成结论。',
      level: 'watch',
      tags: ['等待数据'],
      value: '加载中',
    };
  }
  const onlineErrors = dashboard.summary.onlineErrors || dashboard.onlineLogSummary.errorCount;
  const codeRisks = dashboard.gitlabDailySummary.riskCount;
  const severeBugs = dashboard.summary.highSeverityBugs;
  if (severeBugs > 0 || onlineErrors > 0) {
    return {
      detail: `严重 Bug ${severeBugs} 个，线上错误 ${onlineErrors} 次，建议优先安排缺陷和线上稳定性治理。`,
      level: 'risk',
      tags: ['严重缺陷', '线上稳定性'],
      value: '需重点治理',
    };
  }
  if (dashboard.summary.pendingReviews > 0 || dashboard.summary.openBugs > 0 || codeRisks > 0) {
    return {
      detail: `待确认 ${dashboard.summary.pendingReviews} 个，开放 Bug ${dashboard.summary.openBugs} 个，代码风险 ${codeRisks} 个，需要持续跟进。`,
      level: 'watch',
      tags: ['待确认', '风险跟进'],
      value: '需关注',
    };
  }
  return {
    detail: '当前暂无高优先风险，交付、质量和线上运行处于稳定状态。',
    level: 'healthy',
    tags: ['运行平稳'],
    value: '运行平稳',
  };
}

function DashboardHealthCard({ health }: { health: DashboardHealthSummary }) {
  const label = dashboardHealthLabels[health.level];
  return (
    <section className="dashboard-insight-card dashboard-health-card" data-level={health.level}>
      <div>
        <Text type="secondary">健康结论</Text>
        <Title level={3}>{health.value}</Title>
      </div>
      <Text>{health.detail}</Text>
      <Space size={8} wrap>
        <Tag color={label.color}>{label.label}</Tag>
        {health.tags.map((tag) => (
          <Tag key={tag}>{tag}</Tag>
        ))}
      </Space>
    </section>
  );
}

function DashboardActionQueue({ actions }: { actions: DashboardActionItem[] }) {
  return (
    <section className="dashboard-insight-card">
      <div className="dashboard-insight-title">
        <Title level={4}>治理优先队列</Title>
        <Text type="secondary">按风险和交付影响排序</Text>
      </div>
      {actions.length === 0 ? (
        <Empty description="暂无需优先处理事项" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div className="dashboard-action-list">
          {actions.slice(0, 4).map((action) => {
            const levelLabel = dashboardHealthLabels[action.level];
            return (
              <a className="dashboard-action-item" href={action.href} key={action.key}>
                <span>
                  <Text strong>{action.title}</Text>
                  <Text type="secondary">{action.detail}</Text>
                </span>
                <span className="dashboard-action-value">
                  <Tag color={levelLabel.color}>{levelLabel.label}</Tag>
                  <Text strong>{action.value}</Text>
                </span>
              </a>
            );
          })}
        </div>
      )}
    </section>
  );
}

function BugList({ bugs }: { bugs: DashboardBugSummary[] }) {
  if (bugs.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  return (
    <div className="dashboard-list">
      {bugs.map((bug) => {
        const severityLabel = severityLabels[bug.severity] ?? {
          color: 'default',
          label: bug.severity,
        };
        const statusLabel = statusLabels[bug.status] ?? { color: 'default', label: bug.status };
        return (
          <div className="dashboard-list-item" key={bug.id}>
            <Text strong>{bug.title}</Text>
            <Space size={8} wrap>
              <Tag color={severityLabel.color}>{severityLabel.label}</Tag>
              <Tag color={statusLabel.color}>{statusLabel.label}</Tag>
            </Space>
          </div>
        );
      })}
    </div>
  );
}

function KnowledgeList({ documents }: { documents: DashboardKnowledgeSummary[] }) {
  if (documents.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  return (
    <div className="dashboard-list">
      {documents.map((document) => (
        <div className="dashboard-list-item" key={document.id}>
          <Text strong>{document.title}</Text>
          <Text type="secondary">{document.id}</Text>
        </div>
      ))}
    </div>
  );
}

function AuditList({ events }: { events: DashboardAuditSummary[] }) {
  if (events.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  return (
    <div className="dashboard-list">
      {events.map((event) => (
        <div className="dashboard-list-item" key={event.id}>
          <Text strong>{event.eventType}</Text>
          <Text type="secondary">{event.id}</Text>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<ItTeamDashboard>();
  const [error, setError] = useState<RemoteRowsError>();
  const [loading, setLoading] = useState(true);
  const [productOptionsSource, setProductOptionsSource] = useState<ProductFilterOption[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string>();
  const [selectedTimeRange, setSelectedTimeRange] = useState(allTimeRangeValue);

  const productOptions = useMemo(
    () => [
      { label: '全部产品', value: allProductsValue },
      ...productOptionsSource.map((product) => ({ label: product.name, value: product.id })),
    ],
    [productOptionsSource],
  );

  const selectedApiTimeRange =
    selectedTimeRange === allTimeRangeValue ? undefined : selectedTimeRange;

  const drilldownQuery = useMemo(() => {
    const query = new URLSearchParams();
    if (selectedProductId) {
      query.set('product_id', selectedProductId);
    }
    if (selectedApiTimeRange) {
      query.set('time_range', selectedApiTimeRange);
    }
    return query.toString();
  }, [selectedApiTimeRange, selectedProductId]);

  const drilldownUrl = useCallback(
    (pathname: string) => (drilldownQuery ? `${pathname}?${drilldownQuery}` : pathname),
    [drilldownQuery],
  );

  const reload = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const nextDashboard = await fetchItTeamDashboard({
        forceRefresh: true,
        productId: selectedProductId,
        timeRange: selectedApiTimeRange,
      });
      setDashboard(nextDashboard);
    } catch (loadError) {
      setDashboard(undefined);
      setError(normalizeError(loadError));
    } finally {
      setLoading(false);
    }
  }, [selectedApiTimeRange, selectedProductId]);

  useEffect(() => {
    let isCurrent = true;
    fetchItTeamDashboard({ productId: selectedProductId, timeRange: selectedApiTimeRange })
      .then((nextDashboard) => {
        if (isCurrent) {
          setDashboard(nextDashboard);
          setError(undefined);
        }
      })
      .catch((loadError) => {
        if (isCurrent) {
          setDashboard(undefined);
          setError(normalizeError(loadError));
        }
      })
      .finally(() => {
        if (isCurrent) {
          setLoading(false);
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [selectedApiTimeRange, selectedProductId]);

  useEffect(() => {
    let isCurrent = true;
    void fetchActiveProductOptions()
      .then((items) => {
        if (isCurrent) {
          setProductOptionsSource(items);
        }
      })
      .catch(() => {
        if (isCurrent) {
          setProductOptionsSource([]);
        }
      });
    return () => {
      isCurrent = false;
    };
  }, []);

  const generatedAtText = formatDashboardGeneratedAt(dashboard?.cacheMetadata.generatedAt);
  const onlineErrors = dashboard
    ? dashboard.summary.onlineErrors || dashboard.onlineLogSummary.errorCount
    : 0;
  const qualityScore = dashboard
    ? dashboard.gitlabDailySummary.averageQualityScore.toFixed(1)
    : '0.0';
  const healthSummary = summarizeDashboardHealth(dashboard);
  const focusCards: DashboardFocusCardConfig[] = [
    {
      icon: <FileDoneOutlined />,
      metrics: [
        { label: '需求总数', value: dashboard?.summary.requirements ?? 0 },
        { label: 'AI 任务', value: dashboard?.summary.aiTasks ?? 0 },
        { label: '待确认', value: dashboard?.summary.pendingReviews ?? 0 },
      ],
      title: '交付负载',
      tone: 'info',
      value: dashboard?.summary.requirements ?? 0,
    },
    {
      icon: <BugOutlined />,
      metrics: [
        { label: '开放 Bug', value: dashboard?.summary.openBugs ?? 0 },
        { label: '严重 Bug', value: dashboard?.summary.highSeverityBugs ?? 0 },
        { label: '线上错误', value: onlineErrors },
      ],
      title: '风险压力',
      tone: (dashboard?.summary.highSeverityBugs ?? 0) > 0 || onlineErrors > 0 ? 'risk' : 'healthy',
      value: (dashboard?.summary.highSeverityBugs ?? 0) + onlineErrors,
    },
    {
      icon: <CloudServerOutlined />,
      metrics: [
        { label: 'GitLab 提交', value: dashboard?.summary.gitlabCommits ?? 0 },
        { label: 'Merge Request', value: dashboard?.gitlabDailySummary.mergeRequestCount ?? 0 },
        { label: '发布记录', value: dashboard?.summary.jenkinsReleases ?? 0 },
        { label: '质量分', value: qualityScore },
      ],
      title: '工程活跃',
      tone: (dashboard?.gitlabDailySummary.riskCount ?? 0) > 0 ? 'watch' : 'info',
      value: dashboard?.summary.gitlabCommits ?? 0,
    },
    {
      icon: <UserSwitchOutlined />,
      metrics: [
        { label: '使用事件', value: dashboard?.summary.usageEvents ?? 0 },
        { label: '活跃用户', value: dashboard?.usageMetricSummary.activeUsers ?? 0 },
        { label: '用户反馈', value: dashboard?.summary.userFeedback ?? 0 },
        { label: '迭代建议', value: dashboard?.summary.iterationSuggestions ?? 0 },
      ],
      title: '用户声音',
      tone: 'healthy',
      value: dashboard?.summary.usageEvents ?? 0,
    },
  ];
  const actionItemCandidates: Array<DashboardActionItem | undefined> = dashboard
    ? [
        dashboard.summary.highSeverityBugs > 0
          ? {
              detail: '阻断或严重缺陷需要优先收敛',
              href: drilldownUrl('/delivery/bugs'),
              key: 'severe-bugs',
              level: 'risk',
              title: '严重 Bug 待治理',
              value: dashboard.summary.highSeverityBugs,
            }
          : undefined,
        onlineErrors > 0
          ? {
              detail: '线上错误会直接影响系统可用性',
              href: drilldownUrl('/governance/devops'),
              key: 'online-errors',
              level: 'risk',
              title: '线上错误待排查',
              value: onlineErrors,
            }
          : undefined,
        dashboard.summary.pendingReviews > 0
          ? {
              detail: '待确认会阻塞 AI 任务继续推进',
              href: drilldownUrl('/tasks'),
              key: 'pending-reviews',
              level: 'watch',
              title: '待确认任务',
              value: dashboard.summary.pendingReviews,
            }
          : undefined,
        dashboard.gitlabDailySummary.riskCount > 0
          ? {
              detail: '代码风险建议进入巡检治理闭环',
              href: drilldownUrl('/governance/code-inspections'),
              key: 'code-risks',
              level: 'watch',
              title: '代码风险',
              value: dashboard.gitlabDailySummary.riskCount,
            }
          : undefined,
        dashboard.summary.openBugs > 0
          ? {
              detail: '开放缺陷需要持续分诊和验证',
              href: drilldownUrl('/delivery/bugs'),
              key: 'open-bugs',
              level: 'watch',
              title: '开放 Bug',
              value: dashboard.summary.openBugs,
            }
          : undefined,
        dashboard.summary.iterationSuggestions > 0
          ? {
              detail: '可进入用户洞察确认是否转需求',
              href: drilldownUrl('/governance/insights'),
              key: 'iteration-suggestions',
              level: 'healthy',
              title: 'AI 迭代建议',
              value: dashboard.summary.iterationSuggestions,
            }
          : undefined,
      ]
    : [];
  const actionItems = actionItemCandidates.filter(
    (item): item is DashboardActionItem => item !== undefined,
  );

  return (
    <PageContainer title={false}>
      <div className="dashboard-header">
        <div>
          <Title level={3}>IT 团队看板</Title>
          <Text type="secondary">生成时间：{generatedAtText}</Text>
        </div>
        <div className="dashboard-actions">
          <Select
            aria-label="产品筛选"
            className="dashboard-product-select"
            onChange={(value) => {
              setSelectedProductId(value === allProductsValue ? undefined : value);
            }}
            options={productOptions}
            value={selectedProductId ?? allProductsValue}
          />
          <Select
            aria-label="时间范围"
            className="dashboard-product-select"
            onChange={setSelectedTimeRange}
            options={timeRangeOptions}
            value={selectedTimeRange}
          />
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void reload()}>
            刷新
          </Button>
        </div>
      </div>
      {error ? (
        <Alert className="management-list-alert" showIcon title={formatRemoteRowsError(error)} type="error" />
      ) : null}
      <div className="dashboard-overview-grid">
        <DashboardHealthCard health={healthSummary} />
        <DashboardActionQueue actions={actionItems} />
      </div>
      <div aria-label="团队看板指标" className="dashboard-focus-grid" role="list">
        {focusCards.map((card) => (
          <DashboardFocusCard
            icon={card.icon}
            key={card.title}
            metrics={card.metrics}
            title={card.title}
            tone={card.tone}
            value={card.value}
          />
        ))}
      </div>
      {dashboard?.trend ? <DashboardTrendSection trend={dashboard.trend} /> : null}
      <div className="dashboard-grid">
        <section className="dashboard-panel">
          <Title level={4}>需求状态分布</Title>
          <DashboardBarChart
            ariaLabel="需求状态分布图"
            items={toDashboardChartItems(dashboard?.requirementStatusCounts ?? [])}
          />
        </section>
        <section className="dashboard-panel">
          <Title level={4}>AI 任务状态分布</Title>
          <DashboardBarChart
            ariaLabel="AI 任务状态分布图"
            items={toDashboardChartItems(dashboard?.taskStatusCounts ?? [])}
          />
        </section>
        <section className="dashboard-panel">
          <Title level={4}>最近任务</Title>
          <TaskList tasks={dashboard?.latestTasks ?? []} />
        </section>
        <section className="dashboard-panel">
          <Title level={4}>知识沉淀</Title>
          <KnowledgeList documents={dashboard?.recentKnowledgeDocuments ?? []} />
        </section>
        <section className="dashboard-panel">
          <Title level={4}>Bug 风险</Title>
          <DashboardBarChart
            ariaLabel="Bug 状态分布图"
            items={toDashboardChartItems(dashboard?.bugStatusCounts ?? [])}
          />
          <Title level={5}>高严重级别</Title>
          <BugList bugs={dashboard?.latestHighSeverityBugs ?? []} />
          <div className="dashboard-panel-actions">
            <Button href={drilldownUrl('/delivery/bugs')} icon={<BugOutlined />} size="small">
              Bug 明细
            </Button>
          </div>
        </section>
        <section className="dashboard-panel">
          <Title level={4}>工程与发布</Title>
          <MetricSummary
            items={[
              { label: 'GitLab 指标', value: dashboard?.gitlabDailySummary.metricCount ?? 0 },
              { label: 'Merge Request', value: dashboard?.gitlabDailySummary.mergeRequestCount ?? 0 },
              { label: '代码风险', value: dashboard?.gitlabDailySummary.riskCount ?? 0 },
              { label: '线上错误', value: dashboard?.onlineLogSummary.errorCount ?? 0 },
              { label: '错误率', suffix: '%', value: ((dashboard?.onlineLogSummary.errorRate ?? 0) * 100).toFixed(2) },
              { label: 'P95 延迟', suffix: 'ms', value: dashboard?.onlineLogSummary.maxP95LatencyMs ?? 0 },
            ]}
          />
          <Title level={5}>发布状态分布</Title>
          <DashboardBarChart
            ariaLabel="发布状态分布图"
            items={toDashboardChartItems(dashboard?.jenkinsReleaseStatusCounts ?? [])}
          />
          <div className="dashboard-panel-actions">
            <Button href={drilldownUrl('/governance/devops')} icon={<BarChartOutlined />} size="small">
              日志明细
            </Button>
          </div>
        </section>
        <section className="dashboard-panel">
          <Title level={4}>用户洞察</Title>
          <MetricSummary
            items={[
              { label: '指标记录', value: dashboard?.usageMetricSummary.metricCount ?? 0 },
              { label: '活跃用户', value: dashboard?.usageMetricSummary.activeUsers ?? 0 },
              { label: '转化次数', value: dashboard?.usageMetricSummary.conversionCount ?? 0 },
              { label: '反馈总数', value: dashboard?.summary.userFeedback ?? 0 },
              { label: '迭代建议', value: dashboard?.summary.iterationSuggestions ?? 0 },
            ]}
          />
          <Title level={5}>反馈状态分布</Title>
          <DashboardBarChart
            ariaLabel="用户反馈状态分布图"
            items={toDashboardChartItems(dashboard?.userFeedbackStatusCounts ?? [])}
          />
          <Title level={5}>迭代建议分布</Title>
          <DashboardBarChart
            ariaLabel="迭代建议状态分布图"
            items={toDashboardChartItems(dashboard?.iterationSuggestionStatusCounts ?? [])}
          />
          <div className="dashboard-panel-actions">
            <Button href={drilldownUrl('/governance/insights')} icon={<RobotOutlined />} size="small">
              洞察明细
            </Button>
          </div>
        </section>
        <section className="dashboard-panel">
          <Title level={4}>审计摘要</Title>
          <AuditList events={dashboard?.recentAuditEvents ?? []} />
          <div className="dashboard-panel-actions">
            <Button href={drilldownUrl('/governance/audit')} icon={<AuditOutlined />} size="small">
              审计明细
            </Button>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
