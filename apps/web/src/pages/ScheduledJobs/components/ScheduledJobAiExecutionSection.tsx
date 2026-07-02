import { Alert, Col, Form, Input, InputNumber, Row, Select, Space, Tag, Typography } from 'antd';
import type { FormItemProps } from 'antd';

import type { KnowledgeRecord, ModelGatewayConfigRecord } from '../../../data/management';
import type { AiAgentRecord, AiExecutorRunnerRecord, AiSkillRecord } from '../../../services/aiBrain';
import { ScheduledJobFormSection } from './ScheduledJobFormSection';

type FormRule = NonNullable<FormItemProps['rules']>[number];

const executorTypeLabels = new Map([
  ['model_gateway', '系统默认模型'],
  ['codex', 'Codex'],
  ['claude', 'Claude Code'],
  ['hermes', 'Hermes'],
  ['openclaw', 'OpenClaw'],
]);

function executorTypeLabel(value?: string) {
  return executorTypeLabels.get(String(value || '')) ?? String(value || '-');
}

function healthColor(status?: string) {
  if (status === 'managed' || status === 'online') {
    return 'green';
  }
  if (status === 'offline' || status === 'never_connected') {
    return 'orange';
  }
  if (status === 'disabled') {
    return 'default';
  }
  return 'blue';
}

function defaultExecutorType(runner?: AiExecutorRunnerRecord) {
  const executorTypes = runner?.executor_types ?? [];
  if (executorTypes.includes('model_gateway')) {
    return 'model_gateway';
  }
  return executorTypes[0] ?? 'model_gateway';
}

function defaultWorkspaceRoot(runner: AiExecutorRunnerRecord | undefined, executorType: string) {
  if (executorType === 'model_gateway') {
    return 'model-gateway://scheduled-job';
  }
  const workspaceRoots = runner?.workspace_roots ?? [];
  const concreteRoot = workspaceRoots.find((item) => item && item !== '*');
  return concreteRoot ?? '';
}

export function ScheduledJobAiExecutionSection({
  agents,
  aiExecutorRunners,
  executionModeOptions,
  knowledgeDocuments,
  modelGatewayConfigs,
  requiredForAiAssembly,
  skills,
}: {
  agents: AiAgentRecord[];
  aiExecutorRunners: AiExecutorRunnerRecord[];
  executionModeOptions: Array<{ label: string; value: string }>;
  knowledgeDocuments: KnowledgeRecord[];
  modelGatewayConfigs: ModelGatewayConfigRecord[];
  requiredForAiAssembly: (message: string) => FormRule;
  skills: AiSkillRecord[];
}) {
  const form = Form.useFormInstance();
  const selectedRunnerId = Form.useWatch(['config_json', 'ai_executor', 'runner_id'], form);
  const selectedExecutorType = Form.useWatch(['config_json', 'ai_executor', 'executor_type'], form);
  const selectedRunner = aiExecutorRunners.find((runner) => runner.id === selectedRunnerId)
    ?? aiExecutorRunners.find((runner) => runner.id === 'ai_executor_runner_system_default')
    ?? aiExecutorRunners[0];
  const executorTypeOptions = (selectedRunner?.executor_types?.length
    ? selectedRunner.executor_types
    : ['model_gateway']).map((executorType) => ({
    label: executorTypeLabel(executorType),
    value: executorType,
  }));
  const resolvedExecutorType = selectedExecutorType || defaultExecutorType(selectedRunner);
  const localRunnerSelected = resolvedExecutorType !== 'model_gateway';

  const applyRunnerSelection = (runnerId?: string) => {
    const runner = aiExecutorRunners.find((item) => item.id === runnerId);
    const executorType = defaultExecutorType(runner);
    const currentConfig = form.getFieldValue(['config_json', 'ai_executor']) ?? {};
    form.setFieldValue(['config_json', 'ai_executor'], {
      ...currentConfig,
      executor_type: executorType,
      instruction_timeout_seconds: currentConfig.instruction_timeout_seconds ?? 1800,
      runner_id: runner?.id,
      runner_label: runner?.name,
      workspace_root: defaultWorkspaceRoot(runner, executorType),
    });
  };

  return (
    <ScheduledJobFormSection label="AI执行配置" marker="处理">
      <Row gutter={12}>
        <Col span={8}>
          <Form.Item label="AI执行" name="execution_mode">
            <Select options={executionModeOptions} />
          </Form.Item>
        </Col>
        <Col span={16}>
          <Form.Item
            label="AI执行器"
            name={['config_json', 'ai_executor', 'runner_id']}
            initialValue="ai_executor_runner_system_default"
          >
            <Select
              optionFilterProp="label"
              placeholder="请选择 AI执行器"
              showSearch
              onChange={applyRunnerSelection}
              options={aiExecutorRunners.map((runner) => ({
                label: `${runner.name} (${(runner.executor_types ?? []).map(executorTypeLabel).join('/') || runner.protocol || runner.id})`,
                value: runner.id,
              }))}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="执行器类型"
            name={['config_json', 'ai_executor', 'executor_type']}
            initialValue="model_gateway"
          >
            <Select
              options={executorTypeOptions}
              onChange={(executorType) => {
                const currentConfig = form.getFieldValue(['config_json', 'ai_executor']) ?? {};
                form.setFieldValue(['config_json', 'ai_executor'], {
                  ...currentConfig,
                  executor_type: executorType,
                  workspace_root: defaultWorkspaceRoot(selectedRunner, executorType),
                });
              }}
            />
          </Form.Item>
        </Col>
        <Col span={16}>
          <Form.Item
            dependencies={['execution_mode', 'job_type']}
            label="AI 模型"
            name="model_gateway_config_id"
            rules={[requiredForAiAssembly('请选择 AI 模型')]}
          >
            <Select
              allowClear
              optionFilterProp="label"
              placeholder="请选择 AI 模型"
              showSearch
              options={modelGatewayConfigs.map((config) => ({
                label: `${config.name} (${config.defaultChatModel})`,
                value: config.id,
              }))}
            />
          </Form.Item>
        </Col>
        {localRunnerSelected ? (
          <>
            <Col span={16}>
              <Form.Item
                label="工作区"
                name={['config_json', 'ai_executor', 'workspace_root']}
                rules={[{ required: true, message: '请输入 Runner 工作区' }]}
              >
                <Input placeholder="例如 /Users/you/source/e-ai-brain" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="执行超时秒数"
                name={['config_json', 'ai_executor', 'instruction_timeout_seconds']}
                initialValue={1800}
              >
                <InputNumber min={60} max={86400} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Alert
                showIcon
                type="info"
                title={(
                  <Space size={[8, 8]} wrap>
                    <Typography.Text>Runner 完成后会自动回写任务运行结果，并继续执行后续动作。</Typography.Text>
                    {selectedRunner ? (
                      <>
                        <Tag color={healthColor(selectedRunner.health_status)}>
                          {selectedRunner.health_status ?? selectedRunner.status}
                        </Tag>
                        <Tag>{selectedRunner.protocol}</Tag>
                      </>
                    ) : null}
                  </Space>
                )}
              />
            </Col>
          </>
        ) : null}
        <Col span={12}>
          <Form.Item
            dependencies={['execution_mode', 'job_type']}
            label="AI角色"
            name="agent_id"
            rules={[requiredForAiAssembly('请选择 AI角色')]}
          >
            <Select
              allowClear
              optionFilterProp="label"
              placeholder="请选择 AI角色"
              showSearch
              options={agents.map((agent) => ({
                label: `${agent.name} (${agent.code})`,
                value: agent.id,
              }))}
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            dependencies={['execution_mode', 'job_type']}
            label="Skills"
            name="skill_ids"
            rules={[requiredForAiAssembly('请选择 Skills')]}
          >
            <Select
              allowClear
              mode="multiple"
              optionFilterProp="label"
              placeholder="请选择 Skills"
              showSearch
              options={skills.map((skill) => ({
                label: `${skill.name} (${skill.code})`,
                value: skill.id,
              }))}
            />
          </Form.Item>
        </Col>
        <Col span={24}>
          <Form.Item label="知识引用" name="knowledge_document_ids">
            <Select
              allowClear
              mode="multiple"
              optionFilterProp="label"
              placeholder="请选择知识文档"
              showSearch
              options={knowledgeDocuments.map((document) => ({
                label: `${document.title} (${document.documentType})`,
                value: document.id,
              }))}
            />
          </Form.Item>
        </Col>
      </Row>
    </ScheduledJobFormSection>
  );
}
