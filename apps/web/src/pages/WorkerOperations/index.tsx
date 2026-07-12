import { ReloadOutlined, WarningOutlined } from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Alert, Button, Card, Col, Empty, Row, Space, Statistic, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  fetchExecutionOperationsOverview,
  reconcileExecutionOperations,
  type ExecutionOperationRecord,
  type ExecutionOperationsOverview,
} from '../../services/executionOperationsClient';
import { formatDisplayDateTime } from '../../utils/dateTime';

const { Text } = Typography;

function durationLabel(seconds: number) {
  if (seconds < 60) return `${seconds} 秒`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟`;
  return `${Math.floor(seconds / 3600)} 小时`;
}

function statusTag(status?: string) {
  const color = status === 'manual_reconciliation' ? 'red' : status === 'unknown' ? 'gold' : 'blue';
  const label = status === 'manual_reconciliation' ? '待人工对账' : status === 'unknown' ? '待确认' : '对账中';
  return <Tag color={color}>{label}</Tag>;
}

export default function WorkerOperationsPage() {
  const [data, setData] = useState<ExecutionOperationsOverview>();
  const [loading, setLoading] = useState(true);
  const [reconciling, setReconciling] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setData(await fetchExecutionOperationsOverview());
    } catch (error) {
      message.error(error instanceof Error ? error.message : '加载 Worker 运维数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void fetchExecutionOperationsOverview()
      .then((response) => {
        if (active) setData(response);
      })
      .catch((error: unknown) => {
        if (active) message.error(error instanceof Error ? error.message : '加载 Worker 运维数据失败');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const reconcile = async () => {
    setReconciling(true);
    try {
      const response = await reconcileExecutionOperations();
      message.success(response.total ? `已发起 ${response.total} 项只读对账` : '没有待对账的外部操作');
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '执行外部对账失败');
    } finally {
      setReconciling(false);
    }
  };

  const backlog = data?.backlog;
  return (
    <PageContainer
      extra={<Space><Button loading={reconciling} onClick={() => void reconcile()}>执行对账</Button><Button icon={<ReloadOutlined />} loading={loading} onClick={() => void reload()}>刷新</Button></Space>}
      title="Worker 运维"
    >
      <Alert
        showIcon
        icon={<WarningOutlined />}
        title="外部操作出现未知结果时不会自动重放。请先由 Provider 对账确认，再决定后续处置。"
        type={data?.reconciliation.manual_count ? 'warning' : 'info'}
      />
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col lg={5} md={8} sm={12} xs={24}><Card loading={loading}><Statistic title="待处理事件" value={backlog?.pending_count ?? 0} /></Card></Col>
        <Col lg={5} md={8} sm={12} xs={24}><Card loading={loading}><Statistic title="最长积压" value={durationLabel(backlog?.oldest_pending_seconds ?? 0)} /></Card></Col>
        <Col lg={5} md={8} sm={12} xs={24}><Card loading={loading}><Statistic title="超时租约" value={backlog?.expired_lease_count ?? 0} styles={{ content: { color: backlog?.expired_lease_count ? '#cf1322' : undefined } }} /></Card></Col>
        <Col lg={5} md={8} sm={12} xs={24}><Card loading={loading}><Statistic title="死信事件" value={backlog?.dead_letter_count ?? 0} styles={{ content: { color: backlog?.dead_letter_count ? '#cf1322' : undefined } }} /></Card></Col>
        <Col lg={4} md={8} sm={12} xs={24}><Card loading={loading}><Statistic title="重试事件" value={backlog?.retry_count ?? 0} /></Card></Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col lg={10} xs={24}>
          <Card title="Worker 心跳" loading={loading}>
            {data?.workers.length ? (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {data.workers.map((worker) => (
                  <div key={worker.worker_id} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                    <Space direction="vertical" size={0}><Text strong>{worker.worker_id}</Text><Text type="secondary">最近心跳 {formatDisplayDateTime(worker.updated_at)}</Text></Space>
                    <Text>本轮处理 {worker.claimed_count}</Text>
                  </div>
                ))}
              </Space>
            ) : <Empty description="尚未记录 Worker 心跳" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </Card>
        </Col>
        <Col lg={14} xs={24}>
          <Card title={`外部操作对账（${data?.reconciliation.manual_count ?? 0} 项待人工确认）`} loading={loading}>
            <ProTable<ExecutionOperationRecord>
              columns={[
                { dataIndex: 'operation_type', title: '操作类型', ellipsis: true },
                { dataIndex: 'provider', title: 'Provider', width: 120 },
                { dataIndex: 'status', title: '状态', width: 130, render: (_, row) => statusTag(row.status) },
                { dataIndex: 'updated_at', title: '最近更新', width: 180, renderText: (value) => formatDisplayDateTime(value) },
              ]}
              dataSource={data?.reconciliation.items ?? []}
              options={false}
              pagination={false}
              rowKey={(row) => row.id ?? `${row.provider}-${row.updated_at}`}
              search={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </PageContainer>
  );
}
