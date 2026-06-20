import { LinkOutlined, RobotOutlined } from '@ant-design/icons';
import { Button, Space, Tag, Typography } from 'antd';
import { useMemo } from 'react';

import type { AssistantRuntimeStatus as AssistantRuntimeStatusRecord } from '../../../services/aiBrain';

const { Text } = Typography;

export function AssistantRuntimeStatus({
  runtimeStatus,
}: {
  runtimeStatus?: AssistantRuntimeStatusRecord;
}) {
  const attentionChecks = useMemo(
    () => (runtimeStatus?.checks ?? []).filter(
      (item) => !['ok', 'configured', 'disabled'].includes(item.status),
    ),
    [runtimeStatus],
  );

  if (!runtimeStatus) {
    return null;
  }

  return (
    <div
      aria-label="助手运行状态"
      className={`assistant-runtime-status assistant-runtime-status-${runtimeStatus.mode === 'model_gateway' ? 'ready' : 'limited'}`}
    >
      <Space size={6} wrap>
        <RobotOutlined />
        <Text strong>
          {runtimeStatus.mode === 'model_gateway' ? '模型网关已配置' : '规则能力模式'}
        </Text>
        <Text type="secondary">
          {runtimeStatus.mode === 'model_gateway'
            ? `可用模型问答 · chat=${runtimeStatus.chat_gateway} · embedding=${runtimeStatus.embedding_gateway}`
            : runtimeStatus.warnings?.[0]?.message
              ?? '模型网关未配置，开放式问答会提示配置后重试。'}
        </Text>
      </Space>
      {attentionChecks.length ? (
        <div className="assistant-runtime-checks" aria-label="助手运行自检">
          {attentionChecks.map((item) => (
            <div className="assistant-runtime-check" key={item.code}>
              <Space size={6} wrap>
                <Tag color={item.status === 'error' || item.status === 'failed' ? 'red' : 'gold'}>
                  {item.code}
                </Tag>
                <Text type="secondary">{item.remediation ?? item.description}</Text>
                {item.url ? (
                  <Button href={item.url} icon={<LinkOutlined />} size="small" type="link">
                    {item.action_label ?? '去配置'}
                  </Button>
                ) : null}
              </Space>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
