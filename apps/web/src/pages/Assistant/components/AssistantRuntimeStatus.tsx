import { LinkOutlined, ReloadOutlined, WarningOutlined } from '@ant-design/icons';
import { Button, Space, Tag, Typography } from 'antd';
import { useMemo } from 'react';

import type { AssistantRuntimeStatus as AssistantRuntimeStatusRecord } from '../../../services/aiBrain';

const { Text } = Typography;

export function AssistantRuntimeStatus({
  checkedAt,
  isRefreshing,
  onRefresh,
  runtimeStatus,
}: {
  checkedAt?: string;
  isRefreshing?: boolean;
  onRefresh?: () => void;
  runtimeStatus?: AssistantRuntimeStatusRecord;
}) {
  const requiredAttentionChecks = useMemo(
    () => (runtimeStatus?.checks ?? []).filter(
      (item) => item.required && !['ok', 'configured', 'disabled'].includes(item.status),
    ),
    [runtimeStatus],
  );

  if (!runtimeStatus || !requiredAttentionChecks.length) {
    return null;
  }

  return (
    <div
      aria-label="助手运行状态"
      className="assistant-runtime-status assistant-runtime-status-limited"
    >
      <Space size={6} wrap>
        <WarningOutlined />
        <Text strong>助手运行依赖异常</Text>
        <Text type="secondary">部分必需服务不可用，可能影响聊天、草案记录和运行追踪。</Text>
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
        {requiredAttentionChecks.map((item) => (
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
        ))}
      </div>
    </div>
  );
}
