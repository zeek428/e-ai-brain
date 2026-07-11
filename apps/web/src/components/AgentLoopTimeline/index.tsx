import { PauseCircleOutlined } from '@ant-design/icons';
import { Alert, Button, Descriptions, Empty, Popconfirm, Space, Tag, Timeline, Typography } from 'antd';

import './governance.css';

const { Text } = Typography;

type AgentLoopTimelineProps = {
  loading?: boolean;
  loop?: Record<string, unknown>;
  onTakeover?: () => Promise<void> | void;
};

const STATUS_LABELS: Record<string, { color: string; label: string }> = {
  executing: { color: 'processing', label: '执行中' },
  failed: { color: 'error', label: '未通过' },
  passed: { color: 'success', label: '已通过' },
  safety_blocked: { color: 'error', label: '安全边界阻断' },
  stopped: { color: 'default', label: '已停止' },
  succeeded: { color: 'success', label: '已完成' },
  verifying: { color: 'processing', label: '独立验证中' },
  waiting_review: { color: 'warning', label: '等待人工确认' },
};

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function records(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.map(record).filter((item) => Object.keys(item).length) : [];
}

function texts(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => String(item ?? '').trim()).filter(Boolean);
  }
  return [];
}

function display(value: unknown, fallback = '-') {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  return String(value);
}

function statusTag(status: unknown) {
  const key = String(status || 'unknown');
  const config = STATUS_LABELS[key] ?? { color: 'default', label: key };
  return <Tag color={config.color}>{config.label}</Tag>;
}

function budgetValue(used: unknown, budget: unknown, suffix = '') {
  if (budget === null || budget === undefined || budget === '') {
    return `${display(used, '0')}${suffix} / 不限`;
  }
  return `${display(used, '0')}${suffix} / ${display(budget)}${suffix}`;
}

function iterationPlan(iteration: Record<string, unknown>) {
  const plan = record(iteration.plan);
  const steps = texts(plan.steps);
  if (!steps.length) {
    return null;
  }
  return (
    <div className="agent-governance-detail-row">
      <Text type="secondary">执行计划</Text>
      <ol>{steps.map((step) => <li key={step}>{step}</li>)}</ol>
    </div>
  );
}

function iterationEvidence(iteration: Record<string, unknown>) {
  const evidence = records(iteration.test_evidence);
  if (!evidence.length) {
    return null;
  }
  return (
    <div className="agent-governance-detail-row">
      <Text type="secondary">测试证据</Text>
      <div className="agent-governance-evidence-list">
        {evidence.map((item, index) => (
          <div key={`${display(item.command, 'evidence')}-${index}`}>
            <Tag color={item.status === 'passed' ? 'success' : 'error'}>
              {item.status === 'passed' ? '通过' : display(item.status)}
            </Tag>
            <Text code>{display(item.command ?? item.summary)}</Text>
          </div>
        ))}
      </div>
    </div>
  );
}

function iterationFailures(iteration: Record<string, unknown>) {
  const failures = record(iteration.failure_analysis);
  const reasons = records(failures.blocked_reasons);
  if (!reasons.length && !failures.summary) {
    return null;
  }
  return (
    <Alert
      description={reasons.map((reason) => display(reason.message ?? reason.code)).join('；') || display(failures.summary)}
      showIcon
      title="失败分析"
      type="warning"
    />
  );
}

export function AgentLoopTimeline({ loading, loop, onTakeover }: AgentLoopTimelineProps) {
  if (!loop) {
    return <Empty description="该任务未启用 Agent 自治循环" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  const iterations = records(loop.iterations);
  const status = String(loop.status || 'unknown');
  const canTakeover = ['executing', 'verifying'].includes(status) && Boolean(onTakeover);
  return (
    <Space className="agent-governance-panel" orientation="vertical" size={16} style={{ width: '100%' }}>
      <div className="agent-governance-panel-header">
        <Space size={8} wrap>
          <Text strong>自治执行状态</Text>
          {statusTag(status)}
        </Space>
        {canTakeover ? (
          <Popconfirm
            cancelText="继续自治执行"
            description="接管会停止当前 Runner，但保留隔离代码，后续由人工确认合入或丢弃。"
            okText="确认接管"
            title="转为人工接管？"
            onConfirm={onTakeover}
          >
            <Button aria-label="转人工接管" icon={<PauseCircleOutlined />} loading={loading}>转人工接管</Button>
          </Popconfirm>
        ) : null}
      </div>
      {loop.stop_reason ? (
        <Alert showIcon title={`停止原因：${display(loop.stop_reason)}`} type="warning" />
      ) : null}
      <Descriptions bordered column={{ xs: 1, sm: 2, md: 3 }} size="small">
        <Descriptions.Item label="循环编号">{display(loop.id)}</Descriptions.Item>
        <Descriptions.Item label="当前轮次">
          {display(loop.current_iteration, '0')} / {display(loop.max_iterations, '1')}
        </Descriptions.Item>
        <Descriptions.Item label="上下文版本">v{display(loop.context_version, '1')}</Descriptions.Item>
        <Descriptions.Item label="时长上限">{display(loop.max_duration_seconds)} 秒</Descriptions.Item>
        <Descriptions.Item label="Token 预算">
          {budgetValue(loop.token_used, loop.token_budget)}
        </Descriptions.Item>
        <Descriptions.Item label="费用预算">
          {budgetValue(loop.cost_used, loop.cost_budget, ' USD')}
        </Descriptions.Item>
      </Descriptions>
      {iterations.length ? (
        <Timeline
          items={iterations.map((iteration) => ({
            color: iteration.status === 'passed' ? 'green' : iteration.status === 'failed' ? 'red' : 'blue',
            content: (
              <div className="agent-governance-iteration">
                <Space size={8} wrap>
                  <Text strong>第 {display(iteration.iteration_number)} 轮</Text>
                  {statusTag(iteration.status)}
                  <Tag>上下文 v{display(iteration.context_version, '1')}</Tag>
                </Space>
                {iteration.change_summary ? (
                  <div className="agent-governance-detail-row">
                    <Text type="secondary">修改摘要</Text>
                    <Text>{display(iteration.change_summary)}</Text>
                  </div>
                ) : null}
                {iterationPlan(iteration)}
                {iterationEvidence(iteration)}
                {iterationFailures(iteration)}
              </div>
            ),
          }))}
        />
      ) : (
        <Empty description="尚未产生执行轮次" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}
    </Space>
  );
}
