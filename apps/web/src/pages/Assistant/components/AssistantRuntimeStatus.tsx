import { LinkOutlined, ReloadOutlined, WarningOutlined } from '@ant-design/icons';
import { Button, Space, Tag, Typography } from 'antd';
import { useMemo } from 'react';

import { ExecutionTraceLink } from '../../../components/ExecutionTraceLink';
import type { AssistantRuntimeStatus as AssistantRuntimeStatusRecord } from '../../../services/aiBrain';

const { Text } = Typography;

const RUNTIME_FAILURE_TRACE_SOURCE_TYPES = new Set([
  'assistant_chat_run',
  'model_gateway_log',
  'scheduled_job_run',
]);

function runtimeFailureTraceSourceType(kind?: string | null) {
  const normalizedKind = String(kind ?? '').trim();
  return RUNTIME_FAILURE_TRACE_SOURCE_TYPES.has(normalizedKind) ? normalizedKind : undefined;
}

export function AssistantRuntimeStatus({
  checkedAt,
  isRefreshing,
  onRefresh,
  runtimeStatus,
  showHealthy = false,
}: {
  checkedAt?: string;
  isRefreshing?: boolean;
  onRefresh?: () => void;
  runtimeStatus?: AssistantRuntimeStatusRecord;
  showHealthy?: boolean;
}) {
  const requiredAttentionChecks = useMemo(
    () => (runtimeStatus?.checks ?? []).filter(
      (item) => item.required && !['ok', 'configured', 'disabled'].includes(item.status),
    ),
    [runtimeStatus],
  );
  const recentFailures = runtimeStatus?.operations?.recent_failures ?? [];
  const executorQueue = runtimeStatus?.operations?.executor_queue;
  const queueNeedsAttention = Boolean(
    executorQueue?.visible
    && (
      Number(executorQueue.queued ?? 0) > 0
      || Number(executorQueue.running ?? 0) > 0
      || Number(executorQueue.failed ?? 0) > 0
      || Number(executorQueue.offline_runners ?? 0) > 0
    ),
  );
  const hasAttention = Boolean(
    requiredAttentionChecks.length || recentFailures.length || queueNeedsAttention,
  );
  const shouldShow = Boolean(runtimeStatus ? hasAttention || showHealthy : showHealthy);

  if (!shouldShow) {
    return null;
  }
  const title = requiredAttentionChecks.length
    ? '助手运行依赖异常'
    : (hasAttention ? '助手运行诊断' : '助手运行正常');
  const description = requiredAttentionChecks.length
    ? '部分必需服务不可用，可能影响聊天、草案记录和运行追踪。'
    : (
      hasAttention
        ? '最近有失败或异步执行状态需要关注，可从这里快速定位。'
        : '当前没有需要关注的运行异常。'
    );

  return (
    <div
      aria-label="助手运行状态"
      className="assistant-runtime-status assistant-runtime-status-limited"
    >
      <Space size={6} wrap>
        <WarningOutlined />
        <Text strong>{title}</Text>
        <Text type="secondary">{description}</Text>
        {checkedAt ? (
          <Text type="secondary">{`检测于 ${new Date(checkedAt).toLocaleTimeString()}`}</Text>
        ) : null}
        {onRefresh ? (
          <Button
            aria-label="重新检测"
            icon={<ReloadOutlined />}
            loading={isRefreshing}
            size="small"
            onClick={onRefresh}
          >
            重新检测
          </Button>
        ) : null}
      </Space>
      <div className="assistant-runtime-checks" aria-label="助手运行自检">
        {!runtimeStatus ? (
          <Text type="secondary">暂未获取到运行状态，请重新检测。</Text>
        ) : null}
        {runtimeStatus && !hasAttention ? (
          <Text type="secondary">暂无运行异常，可继续使用 AI 助手。</Text>
        ) : null}
        {requiredAttentionChecks.length ? (
          requiredAttentionChecks.map((item) => (
            <div className="assistant-runtime-check" key={item.key ?? item.code}>
              <Space size={6} wrap>
                <Tag color="red">{item.label ?? item.key ?? item.code}</Tag>
                <Tag color="red">必需</Tag>
                <Text type="secondary">{item.remediation ?? item.detail ?? item.description}</Text>
                {item.action_url ?? item.url ? (
                  <Button href={item.action_url ?? item.url} icon={<LinkOutlined />} size="small" type="link">
                    {item.action_label ?? '去配置'}
                  </Button>
                ) : null}
              </Space>
            </div>
          ))
        ) : null}
        {recentFailures.length ? (
          <div className="assistant-runtime-section" aria-label="助手最近失败">
            <Text strong>最近失败</Text>
            {recentFailures.map((item) => {
              const traceSourceType = runtimeFailureTraceSourceType(item.kind);
              const label = item.label ?? item.kind;
              return (
                <div className="assistant-runtime-check" key={`${item.kind}:${item.id}`}>
                  <Space size={6} wrap>
                    <Tag color={item.kind === 'model_gateway_log' ? 'orange' : 'red'}>
                      {label}
                    </Tag>
                    <Text>{item.title || item.id}</Text>
                    {item.error_code ? <Tag>{item.error_code}</Tag> : null}
                    <Text type="secondary">{item.error_message}</Text>
                    <ExecutionTraceLink
                      asButton
                      buttonProps={{
                        'aria-label': `${label}执行诊断`,
                        icon: <LinkOutlined />,
                        size: 'small',
                      }}
                      fallback={
                        item.url ? (
                          <Button href={item.url} icon={<LinkOutlined />} size="small" type="link">
                            查看
                          </Button>
                        ) : null
                      }
                      sourceId={item.id}
                      sourceType={traceSourceType ?? ''}
                    >
                      执行诊断
                    </ExecutionTraceLink>
                  </Space>
                </div>
              );
            })}
          </div>
        ) : null}
        {queueNeedsAttention && executorQueue ? (
          <div className="assistant-runtime-section" aria-label="AI执行器队列状态">
            <Text strong>AI执行器队列</Text>
            <Space size={6} wrap>
              <Tag color={Number(executorQueue.queued ?? 0) ? 'blue' : 'default'}>
                排队 {executorQueue.queued ?? 0}
              </Tag>
              <Tag color={Number(executorQueue.running ?? 0) ? 'processing' : 'default'}>
                执行中 {executorQueue.running ?? 0}
              </Tag>
              <Tag color={Number(executorQueue.failed ?? 0) ? 'red' : 'default'}>
                失败 {executorQueue.failed ?? 0}
              </Tag>
              <Tag color={Number(executorQueue.offline_runners ?? 0) ? 'orange' : 'default'}>
                离线 Runner {executorQueue.offline_runners ?? 0}
              </Tag>
              <Tag color="default">可用 Runner {executorQueue.active_runners ?? 0}</Tag>
              {executorQueue.oldest_pending_task_id ? (
                <Text type="secondary">
                  最早等待：{executorQueue.oldest_pending_task_id}
                </Text>
              ) : null}
            </Space>
          </div>
        ) : null}
      </div>
    </div>
  );
}
