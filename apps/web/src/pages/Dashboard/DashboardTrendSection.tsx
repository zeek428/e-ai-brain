import { Line } from '@ant-design/charts';
import { Empty, Typography } from 'antd';

import { type DashboardTrend, type DashboardTrendSeries } from '../../services/aiBrain';

const { Text, Title } = Typography;

type DashboardTrendCategory = {
  key: string;
  seriesKeys: string[];
  title: string;
};

type DashboardTrendDatum = {
  metric: string;
  period: string;
  value: number;
};

const dashboardTrendCategories: DashboardTrendCategory[] = [
  {
    key: 'delivery',
    seriesKeys: ['requirements_created', 'ai_tasks_created', 'completed_tasks'],
    title: '交付趋势',
  },
  {
    key: 'risk',
    seriesKeys: ['bugs_created', 'high_severity_bugs', 'online_errors'],
    title: '风险趋势',
  },
  {
    key: 'engineering',
    seriesKeys: ['gitlab_commits', 'merge_requests', 'jenkins_releases'],
    title: '工程趋势',
  },
  {
    key: 'user',
    seriesKeys: ['usage_events', 'active_users', 'user_feedback', 'iteration_suggestions'],
    title: '用户趋势',
  },
];

function trendSeriesForCategory(trend: DashboardTrend, category: DashboardTrendCategory) {
  const allowedKeys = new Set(category.seriesKeys);
  return trend.series.filter((series) => allowedKeys.has(series.key));
}

function trendChartData(trend: DashboardTrend, series: DashboardTrendSeries[]): DashboardTrendDatum[] {
  return trend.points.flatMap((point) =>
    series.map((item) => ({
      metric: item.label,
      period: point.period,
      value: Number(point[item.key] ?? 0),
    })),
  );
}

function canRenderDashboardCharts() {
  const userAgent = typeof navigator === 'undefined' ? '' : navigator.userAgent.toLowerCase();
  return (
    typeof window !== 'undefined'
    && typeof window.ResizeObserver !== 'undefined'
    && !userAgent.includes('jsdom')
  );
}

function DashboardTrendFallback({ data }: { data: DashboardTrendDatum[] }) {
  const latestData = [...data].slice(-12);
  if (!latestData.some((item) => item.value > 0)) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  return (
    <div className="dashboard-trend-fallback">
      {latestData.map((item) => (
        <div className="dashboard-metric-row" key={`${item.period}-${item.metric}`}>
          <Text type="secondary">{`${item.period} · ${item.metric}`}</Text>
          <Text strong>{item.value}</Text>
        </div>
      ))}
    </div>
  );
}

function DashboardTrendChart({
  category,
  trend,
}: {
  category: DashboardTrendCategory;
  trend: DashboardTrend;
}) {
  const series = trendSeriesForCategory(trend, category);
  const data = trendChartData(trend, series);
  const hasData = data.some((item) => item.value > 0);
  const chartConfig = {
    axis: {
      x: { labelAutoHide: true, title: false },
      y: { nice: true, title: false },
    },
    colorField: 'metric',
    data,
    height: 220,
    legend: {
      color: {
        position: 'bottom',
      },
    },
    point: {
      shapeField: 'circle',
      sizeField: 3,
    },
    smooth: true,
    style: {
      lineWidth: 2,
    },
    xField: 'period',
    yField: 'value',
  };
  return (
    <section className="dashboard-trend-panel">
      <div className="dashboard-trend-panel-header">
        <Title level={4}>{category.title}</Title>
        <Text type="secondary">{trend.grain === 'day' ? '按日' : trend.grain}</Text>
      </div>
      {hasData ? (
        <div className="dashboard-trend-chart">
          {canRenderDashboardCharts() ? <Line {...chartConfig} /> : <DashboardTrendFallback data={data} />}
        </div>
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}
    </section>
  );
}

export function DashboardTrendSection({ trend }: { trend: DashboardTrend }) {
  if (trend.points.length === 0 || trend.series.length === 0) {
    return null;
  }
  return (
    <section className="dashboard-trend-section">
      <div className="dashboard-section-heading">
        <div>
          <Title level={4}>真实趋势</Title>
          <Text type="secondary">
            {trend.windowStart} 至 {trend.windowEnd}
          </Text>
        </div>
      </div>
      <div className="dashboard-trend-grid">
        {dashboardTrendCategories.map((category) => (
          <DashboardTrendChart category={category} key={category.key} trend={trend} />
        ))}
      </div>
    </section>
  );
}
