import {
  AlertOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  DashboardOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import {
  Alert,
  Button,
  Descriptions,
  Empty,
  Skeleton,
  Space,
  Statistic,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  fetchSystemHealth,
  type SystemHealthCheckRecord,
  type SystemHealthReport,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { navigateTo } from '../../utils/navigation';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  type RemoteRowsError,
} from '../../hooks/useRemoteRows';

const { Paragraph, Text, Title } = Typography;

const STATUS_LABELS: Record<string, string> = {
  configured: '已配置',
  degraded: '需关注',
  disabled: '已停用',
  enabled: '已启用',
  error: '异常',
  failed: '失败',
  info: '提示',
  managed: '托管',
  not_configured: '未配置',
  ok: '正常',
  warning: '待完善',
};

const STATUS_COLORS: Record<string, string> = {
  configured: 'green',
  degraded: 'orange',
  disabled: 'default',
  enabled: 'green',
  error: 'red',
  failed: 'red',
  info: 'blue',
  managed: 'green',
  not_configured: 'default',
  ok: 'green',
  warning: 'gold',
};

const OVERALL_COPY: Record<string, { color: string; icon: ReactNode; title: string }> = {
  degraded: {
    color: 'orange',
    icon: <AlertOutlined aria-hidden="true" />,
    title: '存在需要关注的运行项',
  },
  error: {
    color: 'red',
    icon: <ExclamationCircleOutlined aria-hidden="true" />,
    title: '存在阻断级配置或依赖异常',
  },
  ok: {
    color: 'green',
    icon: <CheckCircleOutlined aria-hidden="true" />,
    title: '系统关键能力状态良好',
  },
  warning: {
    color: 'gold',
    icon: <InfoCircleOutlined aria-hidden="true" />,
    title: '系统可用，但仍有配置待完善',
  },
};

function statusTag(status: string) {
  return <Tag color={STATUS_COLORS[status] ?? 'default'}>{STATUS_LABELS[status] ?? status}</Tag>;
}

function formatMetricValue(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  if (typeof value === 'boolean') {
    return value ? '是' : '否';
  }
  if (Array.isArray(value)) {
    return value.length ? value.join('、') : '-';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

function metricEntries(metrics?: Record<string, unknown>) {
  return Object.entries(metrics ?? {}).filter(([, value]) => value !== undefined);
}

function groupChecksByCategory(checks: SystemHealthCheckRecord[]) {
  return checks.reduce<Record<string, SystemHealthCheckRecord[]>>((groups, check) => {
    const category = check.category || '未分类';
    groups[category] = [...(groups[category] ?? []), check];
    return groups;
  }, {});
}

function attentionChecks(checks: SystemHealthCheckRecord[]) {
  const attention = new Set(['degraded', 'error', 'failed', 'warning']);
  return checks.filter((check) => attention.has(check.status));
}

function SystemHealthCheckItem({ check }: { check: SystemHealthCheckRecord }) {
  const metrics = metricEntries(check.metrics);
  return (
    <section className="system-health-check">
      <div className="system-health-check-main">
        <div className="system-health-check-title">
          <Space size={8} wrap>
            <strong>{check.title}</strong>
            {statusTag(check.status)}
            <Tag>{check.component}</Tag>
          </Space>
          {check.action_href ? (
            <Button onClick={() => navigateTo(check.action_href as string)} size="small" type="link">
              查看配置
            </Button>
          ) : null}
        </div>
        <Paragraph className="system-health-description">{check.description}</Paragraph>
        {check.last_error ? (
          <Alert
            className="system-health-check-alert"
            showIcon
            title={check.last_error}
            type="warning"
          />
        ) : null}
        <Text type="secondary">{check.fix_suggestion}</Text>
      </div>
      {metrics.length ? (
        <Descriptions
          className="system-health-metrics"
          column={{ lg: 3, md: 2, sm: 1, xs: 1 }}
          items={metrics.slice(0, 6).map(([key, value]) => ({
            key,
            label: key,
            children: formatMetricValue(value),
          }))}
          size="small"
        />
      ) : null}
    </section>
  );
}

function SystemHealthShortcut({
  description,
  icon,
  title,
  to,
}: {
  description: string;
  icon: ReactNode;
  title: string;
  to: string;
}) {
  return (
    <button className="system-health-shortcut" onClick={() => navigateTo(to)} type="button">
      <span className="system-health-shortcut-icon">{icon}</span>
      <span>
        <strong>{title}</strong>
        <Text type="secondary">{description}</Text>
      </span>
    </button>
  );
}

export default function SystemHealthPage() {
  const [report, setReport] = useState<SystemHealthReport>();
  const [error, setError] = useState<RemoteRowsError>();
  const [loading, setLoading] = useState(true);

  const loadHealth = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const loaded = await fetchSystemHealth();
      setReport(loaded);
    } catch (loadError) {
      const normalized = normalizeRemoteRowsError(loadError);
      setError(normalized);
      message.error(normalized.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadHealth();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadHealth]);

  const groupedChecks = useMemo(
    () => groupChecksByCategory(report?.checks ?? []),
    [report?.checks],
  );
  const focusChecks = useMemo(
    () => attentionChecks(report?.checks ?? []),
    [report?.checks],
  );
  const overall = OVERALL_COPY[report?.overall_status ?? 'ok'] ?? OVERALL_COPY.warning;

  return (
    <PageContainer
      breadcrumb={{ items: [{ title: '系统管理' }, { title: '系统健康' }] }}
      extra={[
        <Button
          icon={<QuestionCircleOutlined aria-hidden="true" />}
          key="help"
          onClick={() => navigateTo('/help?article=system-health')}
        >
          查看本页帮助
        </Button>,
        <Button
          icon={<ReloadOutlined aria-hidden="true" />}
          key="reload"
          loading={loading}
          onClick={() => void loadHealth()}
        >
          刷新
        </Button>,
      ]}
      title={false}
    >
      <main className="system-health-page">
        {error ? (
          <Alert
            className="management-list-alert"
            showIcon
            title={formatRemoteRowsError(error)}
            type="warning"
          />
        ) : null}

        {loading && !report ? (
          <section className="system-health-panel">
            <Skeleton active paragraph={{ rows: 8 }} />
          </section>
        ) : report ? (
          <>
            <section className="system-health-hero" data-status={report.overall_status}>
              <div className="system-health-hero-copy">
                <Space align="center" size={12}>
                  <span className="system-health-overall-icon">{overall.icon}</span>
                  <Title level={3}>{overall.title}</Title>
                </Space>
                <Paragraph>
                  统一检查平台依赖、核心配置、运行失败和治理闭环。最近检查时间：
                  {formatDisplayDateTime(report.checked_at)}，Trace ID：{report.trace_id}
                </Paragraph>
              </div>
              <div className="system-health-summary-grid">
                <Statistic title="检查项" value={report.summary.total} />
                <Statistic title="正常" value={report.summary.ok_count} styles={{ content: { color: '#389e0d' } }} />
                <Statistic
                  title="需关注"
                  value={report.summary.needs_attention_count}
                  styles={{ content: { color: report.summary.needs_attention_count ? '#d48806' : '#389e0d' } }}
                />
                <Statistic
                  title="阻断异常"
                  value={report.summary.critical_count}
                  styles={{ content: { color: report.summary.critical_count ? '#cf1322' : '#389e0d' } }}
                />
              </div>
            </section>

            <section className="system-health-shortcuts" aria-label="运维快捷入口">
              <SystemHealthShortcut
                description="查看 API、AI 任务、插件和作业链路"
                icon={<DashboardOutlined aria-hidden="true" />}
                title="执行诊断"
                to="/governance/execution-traces"
              />
              <SystemHealthShortcut
                description="按用户、菜单和权限点定位 Forbidden"
                icon={<SafetyCertificateOutlined aria-hidden="true" />}
                title="权限诊断"
                to="/system/roles"
              />
              <SystemHealthShortcut
                description="检查默认模型、embedding 和调用失败"
                icon={<ApiOutlined aria-hidden="true" />}
                title="模型网关"
                to="/system/model-gateway"
              />
              <SystemHealthShortcut
                description="维护钉钉 MCP、Runner 和插件连接"
                icon={<ToolOutlined aria-hidden="true" />}
                title="插件运维"
                to="/tasks/plugins"
              />
            </section>

            <section className="system-health-panel">
              <div className="system-health-section-heading">
                <Title level={4}>优先处理</Title>
                <Text type="secondary">按异常和风险程度聚合最需要处理的配置或运行问题</Text>
              </div>
              {focusChecks.length ? (
                <div className="system-health-recommendations">
                  {report.recommendations.map((item) => (
                    <div className="system-health-recommendation" key={`${item.component}:${item.title}`}>
                      <div>
                        <Space size={8} wrap>
                          <Tag color={item.severity === 'high' ? 'red' : 'gold'}>
                            {item.severity === 'high' ? '高优先级' : '中优先级'}
                          </Tag>
                          <strong>{item.title}</strong>
                        </Space>
                        <Paragraph>{item.message}</Paragraph>
                      </div>
                      {item.action_href ? (
                        <Button
                          onClick={() => navigateTo(item.action_href as string)}
                          size="small"
                          type="link"
                        >
                          处理
                        </Button>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <Empty description="暂无需要优先处理的系统健康问题" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </section>

            {Object.entries(groupedChecks).map(([category, checks]) => (
              <section className="system-health-panel" key={category}>
                <div className="system-health-section-heading">
                  <Title level={4}>{category}</Title>
                  <Space wrap>{checks.map((check) => statusTag(check.status))}</Space>
                </div>
                <div className="system-health-check-list">
                  {checks.map((check) => (
                    <SystemHealthCheckItem check={check} key={check.key} />
                  ))}
                </div>
              </section>
            ))}
          </>
        ) : null}
      </main>
    </PageContainer>
  );
}
