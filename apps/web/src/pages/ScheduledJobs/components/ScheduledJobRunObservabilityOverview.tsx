import { Card, Col, Descriptions, Row, Space, Statistic, Table, Tag } from 'antd';

import type { ScheduledJobRunObservability } from '../../../services/aiBrain';
import { runNodeTagColor } from './scheduledJobRunTraceHelpers';

type ObservabilityFailureRow = NonNullable<ScheduledJobRunObservability['recent_failures']>[number];
type ObservabilitySlowRunRow = NonNullable<ScheduledJobRunObservability['slow_runs']>[number];

function metricNumber(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function distributionText(items: Array<Record<string, unknown>> | undefined, key: string): string {
  if (!items?.length) {
    return '-';
  }
  return items
    .slice(0, 3)
    .map((item) => `${String(item[key] ?? '-')}: ${String(item.count ?? 0)}`)
    .join(' / ');
}

export function ScheduledJobRunObservabilityOverview({
  loading,
  observability,
}: {
  loading: boolean;
  observability?: ScheduledJobRunObservability;
}) {
  const summary = observability?.summary ?? {};
  const recentFailures = observability?.recent_failures ?? [];
  const slowRuns = observability?.slow_runs ?? [];

  return (
    <Space orientation="vertical" size={12} style={{ marginBottom: 16, width: '100%' }}>
      <Row gutter={[12, 12]}>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic title="总运行数" value={metricNumber(summary.total_runs)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic precision={2} suffix="%" title="成功率" value={metricNumber(summary.success_rate)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic precision={2} suffix="%" title="失败率" value={metricNumber(summary.failure_rate)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic
              precision={0}
              suffix="ms"
              title="平均耗时"
              value={metricNumber(summary.average_latency_ms)}
            />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic title="AI 调用次数" value={metricNumber(summary.model_gateway_called_runs)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic title="Token 总量" value={metricNumber(summary.model_gateway_token_total)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic title="插件调用次数" value={metricNumber(summary.plugin_invocation_runs)} />
          </Card>
        </Col>
        <Col lg={6} md={12} xs={24}>
          <Card size="small" loading={loading}>
            <Statistic
              precision={2}
              suffix="%"
              title="结果写入成功率"
              value={metricNumber(summary.action_write_success_rate)}
            />
          </Card>
        </Col>
      </Row>
      <Card size="small" title="运行健康概览" loading={loading}>
        <Descriptions
          column={{ lg: 3, md: 2, xs: 1 }}
          size="small"
          items={[
            {
              key: 'status_distribution',
              label: '状态分布',
              children: distributionText(observability?.status_distribution, 'status'),
            },
            {
              key: 'job_type_distribution',
              label: '作业类型',
              children: distributionText(observability?.job_type_distribution, 'job_type'),
            },
            {
              key: 'trigger_type_distribution',
              label: '触发方式',
              children: distributionText(observability?.trigger_type_distribution, 'trigger_type'),
            },
            {
              key: 'write_target_distribution',
              label: '写入目标',
              children: distributionText(observability?.write_target_distribution, 'write_target'),
            },
            {
              key: 'error_distribution',
              label: '失败原因',
              children: distributionText(observability?.error_distribution, 'error'),
            },
            {
              key: 'average_records_imported',
              label: '平均导入数',
              children: metricNumber(summary.average_records_imported),
            },
          ]}
        />
      </Card>
      <Row gutter={[12, 12]}>
        <Col lg={12} xs={24}>
          <Card size="small" title="最近失败">
            <Table<ObservabilityFailureRow>
              columns={[
                { dataIndex: 'id', ellipsis: true, title: '运行 ID', width: 190 },
                { dataIndex: 'job_name', ellipsis: true, title: '作业', width: 170 },
                {
                  dataIndex: 'error_code',
                  ellipsis: true,
                  title: '错误码',
                  width: 140,
                  render: (value) => value || '-',
                },
                { dataIndex: 'error_message', ellipsis: true, title: '错误信息', render: (value) => value || '-' },
              ]}
              dataSource={recentFailures}
              locale={{ emptyText: '暂无失败记录' }}
              pagination={false}
              rowKey="id"
              scroll={{ x: 680 }}
              size="small"
            />
          </Card>
        </Col>
        <Col lg={12} xs={24}>
          <Card size="small" title="慢运行">
            <Table<ObservabilitySlowRunRow>
              columns={[
                { dataIndex: 'id', ellipsis: true, title: '运行 ID', width: 190 },
                { dataIndex: 'job_name', ellipsis: true, title: '作业', width: 170 },
                { dataIndex: 'latency_ms', title: '耗时 ms', width: 110, render: (value) => value ?? '-' },
                { dataIndex: 'records_imported', title: '导入数', width: 90, render: (value) => value ?? 0 },
                {
                  dataIndex: 'status',
                  title: '状态',
                  width: 100,
                  render: (value) => <Tag color={runNodeTagColor(String(value ?? ''))}>{String(value ?? '-')}</Tag>,
                },
              ]}
              dataSource={slowRuns}
              locale={{ emptyText: '暂无慢运行记录' }}
              pagination={false}
              rowKey="id"
              scroll={{ x: 660 }}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
