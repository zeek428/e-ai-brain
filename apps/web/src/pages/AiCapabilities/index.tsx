import { PlusOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Space, Table, Tabs, Tag, Switch, Upload, message } from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import { useCallback, useEffect, useState } from 'react';

import {
  createAiAgent,
  createAiSkill,
  fetchAiAgents,
  fetchAiSkills,
  uploadAiSkillPackage,
  type AiAgentRecord,
  type AiSkillRecord,
} from '../../services/aiBrain';

type SkillFormValues = {
  code: string;
  name: string;
  prompt_template: string;
  requires_human_review: boolean;
  risk_level: string;
  status: string;
  version: string;
};

type SkillPackageFormValues = {
  code: string;
  name: string;
  requires_human_review: boolean;
  risk_level: string;
  status: string;
  version: string;
};

type AgentFormValues = {
  code: string;
  default_skill_ids?: string;
  model_gateway_config_id?: string;
  name: string;
  status: string;
  system_prompt: string;
};

export default function AiCapabilitiesPage() {
  const [skillForm] = Form.useForm<SkillFormValues>();
  const [skillPackageForm] = Form.useForm<SkillPackageFormValues>();
  const [agentForm] = Form.useForm<AgentFormValues>();
  const [skills, setSkills] = useState<AiSkillRecord[]>([]);
  const [agents, setAgents] = useState<AiAgentRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [skillModalOpen, setSkillModalOpen] = useState(false);
  const [skillPackageModalOpen, setSkillPackageModalOpen] = useState(false);
  const [skillPackageFiles, setSkillPackageFiles] = useState<UploadFile[]>([]);
  const [agentModalOpen, setAgentModalOpen] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [nextSkills, nextAgents] = await Promise.all([fetchAiSkills(), fetchAiAgents()]);
      setSkills(nextSkills);
      setAgents(nextAgents);
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'AI 能力配置加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const submitSkill = async () => {
    const values = await skillForm.validateFields();
    await createAiSkill(values);
    message.success('Skill 已创建');
    setSkillModalOpen(false);
    skillForm.resetFields();
    await reload();
  };

  const submitSkillPackage = async () => {
    const values = await skillPackageForm.validateFields();
    const originFile = skillPackageFiles[0]?.originFileObj;
    if (!originFile) {
      message.warning('请选择 Skill 包 zip 文件');
      return;
    }
    await uploadAiSkillPackage(originFile, {
      code: values.code,
      name: values.name,
      requiresHumanReview: values.requires_human_review,
      riskLevel: values.risk_level,
      status: values.status,
      version: values.version,
    });
    message.success('Skill 包已上传');
    setSkillPackageModalOpen(false);
    setSkillPackageFiles([]);
    skillPackageForm.resetFields();
    await reload();
  };

  const submitAgent = async () => {
    const values = await agentForm.validateFields();
    await createAiAgent({
      ...values,
      default_skill_ids: values.default_skill_ids
        ? values.default_skill_ids.split(',').map((item) => item.trim()).filter(Boolean)
        : [],
    });
    message.success('Agent 已创建');
    setAgentModalOpen(false);
    agentForm.resetFields();
    await reload();
  };

  return (
    <PageContainer title="AI 能力配置">
      <Tabs
        items={[
          {
            key: 'agents',
            label: 'Agent 管理',
            children: (
              <Table<AiAgentRecord>
                loading={loading}
                rowKey="id"
                dataSource={agents}
                tableLayout="fixed"
                title={() => (
                  <Button icon={<PlusOutlined />} type="primary" onClick={() => setAgentModalOpen(true)}>
                    新增 Agent
                  </Button>
                )}
                columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true },
                  { dataIndex: 'code', title: '编码', ellipsis: true },
                  { dataIndex: 'model_gateway_config_id', title: '模型网关', ellipsis: true, render: (value) => value || '-' },
                  {
                    dataIndex: 'default_skill_ids',
                    title: '默认 Skills',
                    ellipsis: true,
                    render: (value) => (Array.isArray(value) && value.length ? value.join(', ') : '-'),
                  },
                  {
                    dataIndex: 'status',
                    title: '状态',
                    width: 120,
                    render: (value) => <Tag color={value === 'active' ? 'green' : 'default'}>{String(value)}</Tag>,
                  },
                ]}
              />
            ),
          },
          {
            key: 'skills',
            label: 'Skill 管理',
            children: (
              <Table<AiSkillRecord>
                loading={loading}
                rowKey="id"
                dataSource={skills}
                tableLayout="fixed"
                title={() => (
                  <Space>
                    <Button icon={<PlusOutlined />} type="primary" onClick={() => setSkillModalOpen(true)}>
                      新增 Skill
                    </Button>
                    <Button onClick={() => setSkillPackageModalOpen(true)}>上传 Skill 包</Button>
                  </Space>
                )}
                columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true },
                  { dataIndex: 'code', title: '编码', ellipsis: true },
                  { dataIndex: 'version', title: '版本', width: 120 },
                  {
                    dataIndex: 'source_type',
                    title: '来源',
                    width: 120,
                    render: (value) => <Tag>{value === 'package' ? '文件包' : '表单'}</Tag>,
                  },
                  {
                    dataIndex: 'requires_human_review',
                    title: '人工确认',
                    width: 120,
                    render: (value) => (value ? '需要' : '不需要'),
                  },
                  {
                    dataIndex: 'status',
                    title: '状态',
                    width: 120,
                    render: (value) => <Tag color={value === 'active' ? 'green' : 'default'}>{String(value)}</Tag>,
                  },
                ]}
              />
            ),
          },
        ]}
      />

      <Modal open={skillModalOpen} title="新增 Skill" onCancel={() => setSkillModalOpen(false)} onOk={submitSkill}>
        <Form form={skillForm} layout="vertical" initialValues={{ requires_human_review: false, risk_level: 'medium', status: 'active', version: '1.0.0' }}>
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="编码" name="code" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="版本" name="version" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Prompt 模板" name="prompt_template" rules={[{ required: true }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Space>
            <Form.Item label="需要人工确认" name="requires_human_review" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="风险等级" name="risk_level">
              <Input />
            </Form.Item>
            <Form.Item label="状态" name="status">
              <Input />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      <Modal
        open={skillPackageModalOpen}
        title="上传 Skill 包"
        onCancel={() => setSkillPackageModalOpen(false)}
        onOk={submitSkillPackage}
      >
        <Form
          form={skillPackageForm}
          layout="vertical"
          initialValues={{
            requires_human_review: false,
            risk_level: 'medium',
            status: 'active',
            version: '1.0.0',
          }}
        >
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="编码" name="code" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="版本" name="version" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Skill 包">
            <Upload
              accept=".zip"
              beforeUpload={() => false}
              fileList={skillPackageFiles}
              maxCount={1}
              onChange={({ fileList }) => setSkillPackageFiles(fileList)}
            >
              <Button>选择 zip 文件</Button>
            </Upload>
          </Form.Item>
          <Space>
            <Form.Item label="需要人工确认" name="requires_human_review" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="风险等级" name="risk_level">
              <Input />
            </Form.Item>
            <Form.Item label="状态" name="status">
              <Input />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      <Modal open={agentModalOpen} title="新增 Agent" onCancel={() => setAgentModalOpen(false)} onOk={submitAgent}>
        <Form form={agentForm} layout="vertical" initialValues={{ status: 'active' }}>
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="编码" name="code" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="模型网关 ID" name="model_gateway_config_id">
            <Input />
          </Form.Item>
          <Form.Item label="默认 Skill IDs" name="default_skill_ids">
            <Input placeholder="多个 ID 用英文逗号分隔" />
          </Form.Item>
          <Form.Item label="系统提示词" name="system_prompt" rules={[{ required: true }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
}
