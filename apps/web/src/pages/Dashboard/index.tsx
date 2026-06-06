import {
  AuditOutlined,
  BarChartOutlined,
  BookOutlined,
  BugOutlined,
  CheckCircleOutlined,
  CloudServerOutlined,
  FileDoneOutlined,
  LineChartOutlined,
  ProjectOutlined,
  ReloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  UserSwitchOutlined,
} from '@ant-design/icons';
import { PageContainer, StatisticCard } from '@ant-design/pro-components';
import { Alert, Button, Empty, Space, Tag, Typography } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

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

const { Text, Title } = Typography;
const allProductsValue = '__all_products__';
const allTimeRangeValue = 'all';

const timeRangeOptions = [
  { label: '全部时间', value: allTimeRangeValue },
  { label: '近 7 天', value: '7d' },
  { label: '近 30 天', value: '30d' },
];

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

function StatusCountList({ counts }: { counts: DashboardStatusCount[] }) {
  if (counts.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  return (
    <Space orientation="vertical" size={8}>
      {counts.map((item) => {
        const statusLabel = statusLabels[item.status] ?? { color: 'default', label: item.status };
        return (
          <Space key={item.status} size={8}>
            <Tag color={statusLabel.color}>{statusLabel.label}</Tag>
            <Text strong>{item.count}</Text>
          </Space>
        );
      })}
    </Space>
  );
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

  return (
    <PageContainer title={false}>
      <div className="dashboard-header">
        <div>
          <Title level={3}>IT 团队看板</Title>
          <Text type="secondary">
            真实数据窗口：{dashboard?.timeRange ?? '-'}
            {dashboard?.cacheMetadata.generatedAt && dashboard.cacheMetadata.generatedAt !== '-' ? (
              <>
                {' · '}生成时间：{dashboard.cacheMetadata.generatedAt}
                {' · '}
                {dashboard.cacheMetadata.cacheHit ? '缓存命中' : '实时刷新'}
                {' · '}
                {dashboard.cacheMetadata.durationMs}ms
              </>
            ) : null}
          </Text>
        </div>
        <div className="dashboard-actions">
          <select
            aria-label="产品筛选"
            className="dashboard-product-select"
            onChange={(event) => {
              const { value } = event.currentTarget;
              setSelectedProductId(value === allProductsValue ? undefined : value);
            }}
            value={selectedProductId ?? allProductsValue}
          >
            {productOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            aria-label="时间范围"
            className="dashboard-product-select"
            onChange={(event) => setSelectedTimeRange(event.currentTarget.value)}
            value={selectedTimeRange}
          >
            {timeRangeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void reload()}>
            刷新
          </Button>
        </div>
      </div>
      {error ? (
        <Alert className="management-list-alert" showIcon title={formatRemoteRowsError(error)} type="error" />
      ) : null}
      <StatisticCard.Group className="dashboard-stat-grid">
        <StatisticCard
          statistic={{
            prefix: <FileDoneOutlined />,
            title: '需求总数',
            value: dashboard?.summary.requirements ?? 0,
          }}
        />
        <StatisticCard
          statistic={{
            prefix: <ProjectOutlined />,
            title: 'AI 任务',
            value: dashboard?.summary.aiTasks ?? 0,
          }}
        />
        <StatisticCard
          statistic={{
            prefix: <CheckCircleOutlined />,
            title: '待确认',
            value: dashboard?.summary.pendingReviews ?? 0,
          }}
        />
        <StatisticCard
          statistic={{
            prefix: <BookOutlined />,
            title: '知识文档',
            value: dashboard?.summary.knowledgeDocuments ?? 0,
          }}
        />
        <StatisticCard
          statistic={{
            prefix: <SafetyCertificateOutlined />,
            title: '知识沉淀',
            value: dashboard?.summary.knowledgeDeposits ?? 0,
          }}
        />
        <StatisticCard
          statistic={{
            prefix: <AuditOutlined />,
            title: '审计事件',
            value: dashboard?.summary.auditEvents ?? 0,
          }}
        />
        <StatisticCard
          statistic={{
            prefix: <BugOutlined />,
            title: '开放 Bug',
            value: dashboard?.summary.openBugs ?? 0,
          }}
        />
        <StatisticCard
          statistic={{
            prefix: <SafetyCertificateOutlined />,
            title: '严重 Bug',
            value: dashboard?.summary.highSeverityBugs ?? 0,
          }}
        />
        <StatisticCard
          statistic={{
            prefix: <BarChartOutlined />,
            title: 'GitLab 提交',
            value: dashboard?.summary.gitlabCommits ?? 0,
          }}
        />
        <StatisticCard
          statistic={{
            prefix: <CloudServerOutlined />,
            title: '发布记录',
            value: dashboard?.summary.jenkinsReleases ?? 0,
          }}
        />
        <StatisticCard
          statistic={{
            prefix: <UserSwitchOutlined />,
            title: '用户反馈',
            value: dashboard?.summary.userFeedback ?? 0,
          }}
        />
        <StatisticCard
          statistic={{
            prefix: <LineChartOutlined />,
            title: '使用事件',
            value: dashboard?.summary.usageEvents ?? 0,
          }}
        />
        <StatisticCard
          statistic={{
            prefix: <RobotOutlined />,
            title: '迭代建议',
            value: dashboard?.summary.iterationSuggestions ?? 0,
          }}
        />
      </StatisticCard.Group>
      <div className="dashboard-grid">
        <section className="dashboard-panel">
          <Title level={4}>需求状态</Title>
          <StatusCountList counts={dashboard?.requirementStatusCounts ?? []} />
        </section>
        <section className="dashboard-panel">
          <Title level={4}>任务状态</Title>
          <StatusCountList counts={dashboard?.taskStatusCounts ?? []} />
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
          <StatusCountList counts={dashboard?.bugStatusCounts ?? []} />
          <Title level={5}>高严重级别</Title>
          <BugList bugs={dashboard?.latestHighSeverityBugs ?? []} />
          <div className="dashboard-panel-actions">
            <Button href={drilldownUrl('/delivery/bugs')} icon={<BugOutlined />} size="small">
              Bug 明细
            </Button>
          </div>
        </section>
        <section className="dashboard-panel">
          <Title level={4}>日志监控</Title>
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
          <StatusCountList counts={dashboard?.jenkinsReleaseStatusCounts ?? []} />
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
          <StatusCountList counts={dashboard?.userFeedbackStatusCounts ?? []} />
          <StatusCountList counts={dashboard?.iterationSuggestionStatusCounts ?? []} />
          <div className="dashboard-panel-actions">
            <Button href={drilldownUrl('/governance/insights')} icon={<RobotOutlined />} size="small">
              洞察明细
            </Button>
          </div>
        </section>
        <section className="dashboard-panel dashboard-panel-wide">
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
