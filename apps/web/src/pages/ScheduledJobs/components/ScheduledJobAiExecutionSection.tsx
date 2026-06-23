import { Col, Form, Row, Select } from 'antd';
import type { FormItemProps } from 'antd';

import type { KnowledgeRecord, ModelGatewayConfigRecord } from '../../../data/management';
import type { AiAgentRecord, AiSkillRecord } from '../../../services/aiBrain';
import { ScheduledJobFormSection } from './ScheduledJobFormSection';

type FormRule = NonNullable<FormItemProps['rules']>[number];

export function ScheduledJobAiExecutionSection({
  agents,
  executionModeOptions,
  knowledgeDocuments,
  modelGatewayConfigs,
  requiredForAiAssembly,
  skills,
}: {
  agents: AiAgentRecord[];
  executionModeOptions: Array<{ label: string; value: string }>;
  knowledgeDocuments: KnowledgeRecord[];
  modelGatewayConfigs: ModelGatewayConfigRecord[];
  requiredForAiAssembly: (message: string) => FormRule;
  skills: AiSkillRecord[];
}) {
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
