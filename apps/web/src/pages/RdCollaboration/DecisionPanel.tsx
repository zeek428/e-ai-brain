import { Alert, Button, Card, Empty, Space, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  decideRdDecisionRequest,
  fetchRdDecisionRequest,
  type RdDecisionRequest,
} from '../../services/rdCollaborationClient';
import { formatMutationError } from '../../utils/managementCrud';

type Props = {
  decisionRequestId?: string | null;
  onDecided: () => void;
};

export function DecisionPanel({ decisionRequestId, onDecided }: Props) {
  const [decision, setDecision] = useState<RdDecisionRequest>();
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!decisionRequestId) {
      setDecision(undefined);
      return;
    }
    setError(undefined);
    try {
      setDecision(await fetchRdDecisionRequest(decisionRequestId));
    } catch (loadError) {
      setError(formatMutationError(loadError));
    }
  }, [decisionRequestId]);

  useEffect(() => {
    const timer = globalThis.setTimeout(() => void load(), 0);
    return () => globalThis.clearTimeout(timer);
  }, [load]);

  const decide = async (selected_option: string) => {
    if (!decision) {
      return;
    }
    setSaving(true);
    try {
      await decideRdDecisionRequest(decision.id, { selected_option, version: decision.version });
      message.success('人工决策已提交，平台会按冻结恢复规则继续协作');
      await load();
      onDecided();
    } catch (decisionError) {
      message.error(formatMutationError(decisionError));
    } finally {
      setSaving(false);
    }
  };

  if (!decisionRequestId) {
    return <Empty description="当前没有待处理的人工决策" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  if (error) {
    return <Alert action={<Button size="small" onClick={() => void load()}>重试</Button>} title={error} type="error" />;
  }
  if (!decision) {
    return <Empty description="正在加载人工决策" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  return (
    <Card size="small" title="需要人工确认">
      <Space orientation="vertical" style={{ width: '100%' }}>
        <Space wrap>
          <Tag color={decision.status === 'pending' ? 'gold' : 'default'}>{decision.status}</Tag>
          <Typography.Text type="secondary">决策版本 v{decision.version}</Typography.Text>
        </Space>
        <Typography.Paragraph>{decision.prompt ?? decision.reason ?? '请选择受控处理方式。'}</Typography.Paragraph>
        <Space wrap>
          {(decision.options_json ?? []).map((option) => (
            <Button
              key={option.code}
              loading={saving}
              type="primary"
              onClick={() => void decide(option.code)}
            >
              {option.label ?? option.code}
            </Button>
          ))}
        </Space>
      </Space>
    </Card>
  );
}
