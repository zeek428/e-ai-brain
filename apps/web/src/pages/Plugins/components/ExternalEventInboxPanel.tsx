import { ReloadOutlined } from '@ant-design/icons';
import { Button, Input, Popconfirm, Select, Space, Table, Tag, Tooltip, Typography, message } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  fetchExternalEventInbox,
  retryExternalEvent,
  type ExternalEventInboxRecord,
} from '../../../services/executionGovernanceClient';
import { formatDisplayDateTime } from '../../../utils/dateTime';
import { formatMutationError } from '../../../utils/managementCrud';

const { Text } = Typography;

const PROVIDER_OPTIONS = [
  { label: 'GitHub', value: 'github' },
  { label: 'GitLab', value: 'gitlab' },
  { label: 'Jenkins', value: 'jenkins' },
  { label: 'Prometheus', value: 'prometheus' },
  { label: 'OpenTelemetry', value: 'opentelemetry' },
  { label: 'Sentry', value: 'sentry' },
  { label: '用户行为', value: 'user_behavior' },
];

const STATUS_OPTIONS = [
  { label: '待处理', value: 'pending' },
  { label: '处理中', value: 'processing' },
  { label: '已处理', value: 'processed' },
  { label: '失败', value: 'failed' },
  { label: '死信', value: 'dead_letter' },
  { label: '已忽略', value: 'ignored' },
];

function statusTag(status: string) {
  const label = STATUS_OPTIONS.find((item) => item.value === status)?.label ?? status;
  const color = status === 'processed'
    ? 'success'
    : status === 'dead_letter' || status === 'failed'
      ? 'error'
      : status === 'processing'
        ? 'processing'
        : 'default';
  return <Tag color={color}>{label}</Tag>;
}

export function ExternalEventInboxPanel() {
  const [items, setItems] = useState<ExternalEventInboxRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [provider, setProvider] = useState<string>();
  const [status, setStatus] = useState<string>();
  const [eventType, setEventType] = useState<string>();
  const [retryingId, setRetryingId] = useState<string>();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchExternalEventInbox({ eventType, page, pageSize, provider, status });
      setItems(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error(formatMutationError(error));
    } finally {
      setLoading(false);
    }
  }, [eventType, page, pageSize, provider, status]);

  useEffect(() => {
    const timer = globalThis.setTimeout(() => void load(), 0);
    return () => globalThis.clearTimeout(timer);
  }, [load]);

  const retry = async (event: ExternalEventInboxRecord) => {
    setRetryingId(event.id);
    try {
      await retryExternalEvent(event.id, '管理员从 Webhook 事件列表重试');
      message.success('事件已重新进入待处理队列');
      await load();
    } catch (error) {
      message.error(formatMutationError(error));
    } finally {
      setRetryingId(undefined);
    }
  };

  return (
    <Space orientation="vertical" size={12} style={{ width: '100%' }}>
      <div style={{ alignItems: 'center', display: 'flex', gap: 12, justifyContent: 'space-between' }}>
        <Space size={8} wrap>
          <Select
            allowClear
            aria-label="Webhook 提供方"
            options={PROVIDER_OPTIONS}
            placeholder="提供方"
            style={{ width: 150 }}
            value={provider}
            onChange={(value) => { setPage(1); setProvider(value); }}
          />
          <Select
            allowClear
            aria-label="Webhook 状态"
            options={STATUS_OPTIONS}
            placeholder="状态"
            style={{ width: 130 }}
            value={status}
            onChange={(value) => { setPage(1); setStatus(value); }}
          />
          <Input.Search
            allowClear
            aria-label="Webhook 事件类型"
            placeholder="事件类型"
            style={{ width: 220 }}
            onSearch={(value) => { setPage(1); setEventType(value.trim() || undefined); }}
          />
        </Space>
        <Tooltip title="刷新 Webhook 事件">
          <Button aria-label="刷新 Webhook 事件" icon={<ReloadOutlined />} onClick={() => void load()} />
        </Tooltip>
      </div>
      <Table<ExternalEventInboxRecord>
        columns={[
          {
            dataIndex: 'provider',
            render: (value) => <Tag>{String(value).toUpperCase()}</Tag>,
            title: '提供方',
            width: 120,
          },
          { dataIndex: 'event_type', ellipsis: true, title: '事件类型', width: 180 },
          {
            key: 'scope',
            render: (_, row) => (
              <Space orientation="vertical" size={2}>
                <Text>{row.context.product_id || '-' } / {row.context.environment || '-'}</Text>
                <Text type="secondary">{row.context.connection_id || '-'}</Text>
              </Space>
            ),
            title: '产品 / 环境',
            width: 190,
          },
          { dataIndex: 'status', render: (value) => statusTag(String(value)), title: '状态', width: 100 },
          { dataIndex: 'attempt_count', title: '尝试次数', width: 100 },
          {
            dataIndex: 'error_message',
            ellipsis: true,
            render: (value) => value ? <Text type="danger">{String(value)}</Text> : '-',
            title: '错误摘要',
            width: 180,
          },
          {
            dataIndex: 'received_at',
            render: (value) => formatDisplayDateTime(String(value)),
            title: '接收时间',
            width: 170,
          },
          {
            fixed: 'right',
            key: 'actions',
            render: (_, row) => ['failed', 'dead_letter'].includes(row.status) ? (
              <Popconfirm
                cancelText="取消"
                description="事件将清空错误并重新进入 Inbox 队列。"
                okText="确认重试"
                title="重试该 Webhook 事件？"
                onConfirm={() => retry(row)}
              >
                <Button
                  aria-label={`重试事件 ${row.id}`}
                  loading={retryingId === row.id}
                  size="small"
                  type="link"
                >
                  重试
                </Button>
              </Popconfirm>
            ) : null,
            title: '操作',
            width: 90,
          },
        ]}
        dataSource={items}
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          showSizeChanger: true,
          showTotal: (count) => `共 ${count} 条`,
          total,
          onChange: (nextPage, nextPageSize) => {
            setPage(nextPageSize === pageSize ? nextPage : 1);
            setPageSize(nextPageSize);
          },
        }}
        rowKey="id"
        scroll={{ x: 1150 }}
        size="small"
      />
    </Space>
  );
}
