import { ProjectOutlined } from '@ant-design/icons';
import { Button, Space, Tag, Typography } from 'antd';

import type { AssistantDraftWizardStep } from './assistantDraftWizardHelpers';

const { Text } = Typography;

function draftWizardStatusLabel(status?: string) {
  if (status === 'ready') {
    return { color: 'green', text: '已就绪' };
  }
  if (status === 'needs_prerequisite') {
    return { color: 'orange', text: '需先确认前置草案' };
  }
  if (status === 'pending') {
    return { color: 'blue', text: '待确认' };
  }
  if (status === 'skipped') {
    return { color: 'default', text: '已跳过' };
  }
  if (status === 'blocked') {
    return { color: 'red', text: '已阻塞' };
  }
  return { color: 'default', text: status || '未设置' };
}

function draftWizardPrerequisitePrompt(
  draftTitle: string | undefined,
  step: AssistantDraftWizardStep,
) {
  const stepTitle = step.title || step.key || '当前步骤';
  const dependencies = step.depends_on ?? [];
  const dependencyText = dependencies.length ? `。依赖：${dependencies.join('、')}` : '';
  return `为「${draftTitle || '配置草案'}」补齐「${stepTitle}」前置配置草案${dependencyText}`;
}

function draftWizardStepDraftPrompt(
  draftTitle: string | undefined,
  step: AssistantDraftWizardStep,
) {
  const stepTitle = step.title || step.key || '当前步骤';
  const dependencies = step.depends_on ?? [];
  const dependencyText = dependencies.length ? `。依赖：${dependencies.join('、')}` : '';
  const statusText = draftWizardStatusLabel(step.status).text;
  return `为「${draftTitle || '配置草案'}」生成或调整「${stepTitle}」步骤草案。当前状态：${statusText}${dependencyText}。请给出建议配置、字段校验和下一步确认动作`;
}

function canGenerateWizardPrerequisite(step: AssistantDraftWizardStep) {
  return step.status === 'needs_prerequisite' || step.status === 'blocked';
}

function draftWizardManualAdjustUrl(step: AssistantDraftWizardStep) {
  const key = String(step.key ?? '').toLowerCase();
  const title = String(step.title ?? '').toLowerCase();
  if (
    key.includes('data')
    || key.includes('source')
    || key.includes('connection')
    || key.includes('result')
    || key.includes('action')
    || title.includes('数据来源')
    || title.includes('结果动作')
  ) {
    return '/tasks/plugins';
  }
  if (
    key.includes('ai')
    || key.includes('agent')
    || key.includes('skill')
    || title.includes('ai')
    || title.includes('角色')
    || title.includes('skill')
  ) {
    return '/settings/ai-capabilities';
  }
  return '/tasks/scheduled-jobs';
}

export function AssistantDraftWizardBlock({
  draftTitle,
  onUsePrerequisitePrompt,
  steps,
}: {
  draftTitle?: string;
  onUsePrerequisitePrompt?: (prompt: string) => void;
  steps: AssistantDraftWizardStep[];
}) {
  if (!steps.length) {
    return null;
  }
  return (
    <div className="assistant-draft-wizard">
      <div className="assistant-draft-wizard-header">
        <Space size={8} wrap>
          <ProjectOutlined />
          <Text strong>配置向导</Text>
        </Space>
      </div>
      <div className="assistant-draft-wizard-steps">
        {steps.map((step, index) => {
          const label = draftWizardStatusLabel(step.status);
          const title = step.title || step.key || `步骤 ${index + 1}`;
          const canGeneratePrerequisite = Boolean(onUsePrerequisitePrompt)
            && canGenerateWizardPrerequisite(step);
          const canGenerateStepDraft = Boolean(onUsePrerequisitePrompt);
          const manualAdjustUrl = draftWizardManualAdjustUrl(step);
          return (
            <div className="assistant-draft-wizard-step" key={step.key || title}>
              <Space size={6} wrap>
                <Text strong>{`${title}：${label.text}`}</Text>
                <Tag color={label.color}>{label.text}</Tag>
              </Space>
              {step.summary ? <Text type="secondary">{step.summary}</Text> : null}
              {step.depends_on?.length ? (
                <Text type="secondary">依赖：{step.depends_on.join('、')}</Text>
              ) : null}
              {canGenerateStepDraft || canGeneratePrerequisite || manualAdjustUrl ? (
                <Space size={6} wrap>
                  {canGenerateStepDraft ? (
                    <Button
                      size="small"
                      onClick={() => onUsePrerequisitePrompt?.(
                        draftWizardStepDraftPrompt(draftTitle, step),
                      )}
                    >
                      AI生成{title}草案
                    </Button>
                  ) : null}
                  {canGeneratePrerequisite ? (
                    <Button
                      size="small"
                      onClick={() => onUsePrerequisitePrompt?.(
                        draftWizardPrerequisitePrompt(draftTitle, step),
                      )}
                    >
                      生成{title}前置草案
                    </Button>
                  ) : null}
                  <Button href={manualAdjustUrl} size="small">
                    手动调整{title}
                  </Button>
                </Space>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
