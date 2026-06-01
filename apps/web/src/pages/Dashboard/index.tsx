import {
  AuditOutlined,
  BookOutlined,
  CheckCircleOutlined,
  FileDoneOutlined,
  ProjectOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { PageContainer, StatisticCard } from '@ant-design/pro-components';
import { Alert, Button, Empty, Space, Tag, Typography } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { formatRemoteRowsError, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  fetchActiveProductOptions,
  fetchItTeamDashboard,
  type DashboardAuditSummary,
  type DashboardKnowledgeSummary,
  type DashboardStatusCount,
  type DashboardTaskSummary,
  type ItTeamDashboard,
  type ProductFilterOption,
} from '../../services/aiBrain';

const { Text, Title } = Typography;
const allProductsValue = '__all_products__';

const statusLabels: Record<string, { color: string; label: string }> = {
  approved: { color: 'green', label: '已审批' },
  completed: { color: 'green', label: '已完成' },
  draft: { color: 'default', label: '草稿' },
  failed: { color: 'red', label: '失败' },
  pending_approval: { color: 'gold', label: '待审批' },
  rejected: { color: 'red', label: '已拒绝' },
  running: { color: 'blue', label: '运行中' },
  task_created: { color: 'blue', label: '已生成任务' },
  waiting_more_info: { color: 'orange', label: '待补充' },
  waiting_review: { color: 'gold', label: '待确认' },
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

  const productOptions = useMemo(
    () => [
      { label: '全部产品', value: allProductsValue },
      ...productOptionsSource.map((product) => ({ label: product.name, value: product.id })),
    ],
    [productOptionsSource],
  );

  const reload = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const nextDashboard = await fetchItTeamDashboard({ productId: selectedProductId });
      setDashboard(nextDashboard);
    } catch (loadError) {
      setDashboard(undefined);
      setError(normalizeError(loadError));
    } finally {
      setLoading(false);
    }
  }, [selectedProductId]);

  useEffect(() => {
    let isCurrent = true;
    fetchItTeamDashboard({ productId: selectedProductId })
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
  }, [selectedProductId]);

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
          <Text type="secondary">真实数据窗口：{dashboard?.timeRange ?? '-'}</Text>
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
        <section className="dashboard-panel dashboard-panel-wide">
          <Title level={4}>审计摘要</Title>
          <AuditList events={dashboard?.recentAuditEvents ?? []} />
        </section>
      </div>
    </PageContainer>
  );
}
