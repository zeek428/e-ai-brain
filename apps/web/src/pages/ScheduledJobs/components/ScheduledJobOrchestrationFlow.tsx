import { Space, Steps, Tag, Typography } from 'antd';
import type { ReactNode } from 'react';

import type { ScheduledJobTemplateRecord } from '../../../services/aiBrain';

export type ScheduledJobOrchestrationNode = {
  action?: ReactNode;
  details: string[];
  key: string;
  required?: boolean;
  status: string;
  statusColor: string;
  title: string;
};

type ScheduledJobTemplateWizardStep = NonNullable<ScheduledJobTemplateRecord['wizard_steps']>[number];

const defaultScheduledJobWizardSteps: ScheduledJobTemplateWizardStep[] = [
  {
    description: '选择插件连接并完成取数测试',
    key: 'data_connection',
    required: true,
    title: '数据连接',
  },
  {
    description: '选择模型、AI角色和 Skill',
    key: 'ai_processing',
    required: false,
    title: 'AI执行',
  },
  {
    description: '可选引用知识内容',
    key: 'knowledge_reference',
    required: false,
    title: '知识引用',
  },
  {
    description: '选择写入或通知动作',
    key: 'result_write',
    required: true,
    title: '动作',
  },
  {
    description: '设置手动、Cron 或固定间隔',
    key: 'schedule',
    required: true,
    title: '调度',
  },
];

function wizardStepNodeKey(stepKey: string): string {
  if (stepKey === 'result_write') {
    return 'result_action';
  }
  return stepKey;
}

function wizardStepDisplayTitle(step: ScheduledJobTemplateWizardStep): string {
  if (step.key === 'ai_processing' || step.title === 'AI 处理') {
    return 'AI执行';
  }
  if (step.key === 'result_write' || step.title === '结果写入') {
    return '动作';
  }
  return step.title;
}

function wizardStepCurrentIndex(
  steps: ScheduledJobTemplateWizardStep[],
  nodes: ScheduledJobOrchestrationNode[],
) {
  const firstPendingIndex = steps.findIndex((step) => {
    if (!step.required) {
      return false;
    }
    if (step.key === 'schedule') {
      return false;
    }
    const node = nodes.find((item) => item.key === wizardStepNodeKey(step.key));
    return Boolean(node && node.status !== '已配置' && node.status !== '已选择');
  });
  return firstPendingIndex >= 0 ? firstPendingIndex : Math.max(steps.length - 1, 0);
}

export function ScheduledJobOrchestrationFlow({
  nodes,
  wizardSteps = defaultScheduledJobWizardSteps,
}: {
  nodes: ScheduledJobOrchestrationNode[];
  wizardSteps?: ScheduledJobTemplateWizardStep[];
}) {
  const steps = wizardSteps.length ? wizardSteps : defaultScheduledJobWizardSteps;
  return (
    <Space
      aria-label="执行链路"
      orientation="vertical"
      size={10}
      style={{
        background: '#f8fafc',
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        marginBottom: 16,
        padding: 12,
        width: '100%',
      }}
    >
      <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }} wrap>
        <Typography.Text strong>执行链路</Typography.Text>
        <Typography.Text type="secondary">执行链路：数据连接 → AI执行 → 动作 → 运行记录</Typography.Text>
      </Space>
      <Steps
        current={wizardStepCurrentIndex(steps, nodes)}
        items={steps.map((step) => ({
          content: (
            <Space size={4} wrap>
              <Tag color={step.required ? 'orange' : 'default'}>{step.required ? '必填' : '可选'}</Tag>
              {step.description ? <Typography.Text type="secondary">{step.description}</Typography.Text> : null}
            </Space>
          ),
          title: wizardStepDisplayTitle(step),
        }))}
        size="small"
      />
      <div
        style={{
          display: 'grid',
          gap: 10,
          gridTemplateColumns: 'repeat(auto-fit, minmax(155px, 1fr))',
        }}
      >
        {nodes.map((node) => (
          <div
            aria-label={`编排节点 ${node.title}`}
            key={node.key}
            style={{
              background: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              minHeight: 142,
              padding: 10,
            }}
          >
            <Space orientation="vertical" size={8} style={{ width: '100%' }}>
              <Space align="center" wrap>
                <Tag color={node.statusColor}>{node.status}</Tag>
                <Typography.Text strong>{node.title}</Typography.Text>
                {node.required ? <Tag color="orange">必填</Tag> : <Tag>可选</Tag>}
              </Space>
              <Space orientation="vertical" size={4} style={{ minHeight: 46, width: '100%' }}>
                {node.details.length > 0 ? (
                  node.details.map((detail, index) => (
                    <Typography.Text
                      ellipsis={{ tooltip: detail }}
                      key={`${node.key}-${index}-${detail}`}
                      style={{ maxWidth: '100%' }}
                      type="secondary"
                    >
                      {detail}
                    </Typography.Text>
                  ))
                ) : (
                  <Typography.Text type="secondary">尚未选择</Typography.Text>
                )}
              </Space>
              {node.action}
            </Space>
          </div>
        ))}
      </div>
    </Space>
  );
}
