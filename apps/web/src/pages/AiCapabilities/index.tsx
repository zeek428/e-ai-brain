import { PlusOutlined } from '@ant-design/icons';
import { PageContainer, ProTable, type ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, Tabs, Tag, Switch, Upload, message } from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { StatusTag } from '../../components/ManagementListPage';
import type { ModelGatewayConfigRecord } from '../../data/management';
import {
  createAiAgent,
  createAiSkill,
  fetchAiAgents,
  fetchModelGatewayConfigs,
  fetchAiSkills,
  updateAiAgent,
  updateAiSkill,
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

const SKILL_STATUS_OPTIONS = [
  { label: '启用', value: 'active' },
  { label: '草稿', value: 'draft' },
  { label: '停用', value: 'disabled' },
];

const AGENT_STATUS_OPTIONS = [
  { label: '启用', value: 'active' },
  { label: '停用', value: 'disabled' },
];

const STATUS_LABELS: Record<string, string> = {
  active: '启用',
  disabled: '停用',
  draft: '草稿',
};

const STATUS_COLORS: Record<string, string> = {
  active: 'green',
  disabled: 'default',
  draft: 'gold',
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
  const [editingSkill, setEditingSkill] = useState<AiSkillRecord>();
  const [editingAgent, setEditingAgent] = useState<AiAgentRecord>();
  const [modelGatewayConfigs, setModelGatewayConfigs] = useState<ModelGatewayConfigRecord[]>([]);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [nextSkills, nextAgents, nextModelGatewayConfigs] = await Promise.all([
        fetchAiSkills(),
        fetchAiAgents(),
        fetchModelGatewayConfigs(),
      ]);
      setSkills(nextSkills);
      setAgents(nextAgents);
      setModelGatewayConfigs(nextModelGatewayConfigs);
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'AI 能力配置加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const openCreateSkill = () => {
    setEditingSkill(undefined);
    skillForm.resetFields();
    skillForm.setFieldsValue({
      requires_human_review: false,
      risk_level: 'medium',
      status: 'active',
      version: '1.0.0',
    });
    setSkillModalOpen(true);
  };

  const openEditSkill = (record: AiSkillRecord) => {
    setEditingSkill(record);
    skillForm.setFieldsValue({
      code: record.code,
      name: record.name,
      prompt_template: record.prompt_template ?? '',
      requires_human_review: Boolean(record.requires_human_review),
      risk_level: record.risk_level ?? 'medium',
      status: record.status,
      version: record.version ?? '1.0.0',
    });
    setSkillModalOpen(true);
  };

  const closeSkillModal = () => {
    setSkillModalOpen(false);
    setEditingSkill(undefined);
    skillForm.resetFields();
  };

  const openCreateAgent = () => {
    setEditingAgent(undefined);
    agentForm.resetFields();
    agentForm.setFieldsValue({ status: 'active' });
    setAgentModalOpen(true);
  };

  const openEditAgent = (record: AiAgentRecord) => {
    setEditingAgent(record);
    agentForm.setFieldsValue({
      code: record.code,
      default_skill_ids: Array.isArray(record.default_skill_ids) ? record.default_skill_ids.join(', ') : '',
      model_gateway_config_id: record.model_gateway_config_id ?? '',
      name: record.name,
      status: record.status,
      system_prompt: record.system_prompt ?? '',
    });
    setAgentModalOpen(true);
  };

  const closeAgentModal = () => {
    setAgentModalOpen(false);
    setEditingAgent(undefined);
    agentForm.resetFields();
  };

  const submitSkill = async () => {
    const values = await skillForm.validateFields();
    if (editingSkill) {
      await updateAiSkill(editingSkill.id, values);
      message.success('Skill 已更新');
    } else {
      await createAiSkill(values);
      message.success('Skill 已创建');
    }
    closeSkillModal();
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
    const payload = {
      ...values,
      default_skill_ids: values.default_skill_ids
        ? values.default_skill_ids.split(',').map((item) => item.trim()).filter(Boolean)
        : [],
      model_gateway_config_id: values.model_gateway_config_id?.trim() || null,
    };
    if (editingAgent) {
      await updateAiAgent(editingAgent.id, payload);
      message.success('Agent 已更新');
    } else {
      await createAiAgent(payload);
      message.success('Agent 已创建');
    }
    closeAgentModal();
    await reload();
  };

  const disableSkill = async (record: AiSkillRecord) => {
    await updateAiSkill(record.id, { status: 'disabled' });
    message.success('Skill 已删除');
    await reload();
  };

  const disableAgent = async (record: AiAgentRecord) => {
    await updateAiAgent(record.id, { status: 'disabled' });
    message.success('Agent 已删除');
    await reload();
  };

  const renderStatusTag = (value: unknown) => {
    const status = String(value ?? '');
    return <StatusTag color={STATUS_COLORS[status] ?? 'default'} label={STATUS_LABELS[status] ?? status} />;
  };

  const modelGatewayConfigName = (configId?: string | null) => {
    if (!configId) {
      return '-';
    }
    const config = modelGatewayConfigs.find((item) => item.id === configId);
    return config ? `${config.name} (${config.defaultChatModel})` : configId;
  };

  const modelGatewayOptions = [
    { label: '不指定', value: '' },
    ...modelGatewayConfigs.map((config) => ({
      disabled: config.status !== 'active',
      label: `${config.name} / ${config.defaultChatModel}${config.isDefault ? ' / 默认' : ''}`,
      value: config.id,
    })),
  ];

  const agentColumns = useMemo<ProColumns<AiAgentRecord>[]>(
    () => [
      { dataIndex: 'name', ellipsis: true, title: '名称', width: 220 },
      { dataIndex: 'code', ellipsis: true, title: '编码', width: 180 },
      {
        dataIndex: 'model_gateway_config_id',
        ellipsis: true,
        title: '模型网关',
        width: 240,
        render: (value) => modelGatewayConfigName(value ? String(value) : undefined),
      },
      {
        dataIndex: 'default_skill_ids',
        ellipsis: true,
        title: '默认 Skills',
        width: 220,
        render: (value) => (Array.isArray(value) && value.length ? value.join(', ') : '-'),
      },
      {
        dataIndex: 'status',
        title: '状态',
        width: 112,
        render: renderStatusTag,
      },
      {
        fixed: 'right',
        key: 'actions',
        title: '操作',
        valueType: 'option',
        width: 164,
        render: (_, record) => (
          <Space className="management-row-actions" size={0}>
            <Button type="link" onClick={() => openEditAgent(record)}>
              编辑
            </Button>
            <Popconfirm
              title="确认删除该 Agent？"
              description="删除后状态将变为停用，已有运行记录不会被移除。"
              okText="删除"
              cancelText="取消"
              onConfirm={() => disableAgent(record)}
            >
              <Button danger disabled={record.status === 'disabled'} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [modelGatewayConfigs],
  );

  const skillColumns = useMemo<ProColumns<AiSkillRecord>[]>(
    () => [
      { dataIndex: 'name', ellipsis: true, title: '名称', width: 220 },
      { dataIndex: 'code', ellipsis: true, title: '编码', width: 200 },
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
        width: 112,
        render: renderStatusTag,
      },
      {
        fixed: 'right',
        key: 'actions',
        title: '操作',
        valueType: 'option',
        width: 164,
        render: (_, record) => (
          <Space className="management-row-actions" size={0}>
            <Button type="link" onClick={() => openEditSkill(record)}>
              编辑
            </Button>
            <Popconfirm
              title="确认删除该 Skill？"
              description="删除后状态将变为停用，已有运行记录不会被移除。"
              okText="删除"
              cancelText="取消"
              onConfirm={() => disableSkill(record)}
            >
              <Button danger disabled={record.status === 'disabled'} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [],
  );

  return (
    <PageContainer title="AI 能力配置">
      <Tabs
        items={[
          {
            key: 'agents',
            label: 'Agent 管理',
            children: (
              <ProTable<AiAgentRecord>
                cardBordered
                className="management-list-table"
                columns={agentColumns}
                dateFormatter="string"
                headerTitle="Agent 管理"
                loading={loading}
                options={{
                  density: true,
                  fullScreen: true,
                  reload,
                  setting: true,
                }}
                pagination={{
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`,
                }}
                rowKey="id"
                scroll={{ x: 1156 }}
                search={false}
                dataSource={agents}
                tableLayout="fixed"
                toolBarRender={() => [
                  <Button key="create-agent" icon={<PlusOutlined />} type="primary" onClick={openCreateAgent}>
                    新增 Agent
                  </Button>,
                ]}
              />
            ),
          },
          {
            key: 'skills',
            label: 'Skill 管理',
            children: (
              <ProTable<AiSkillRecord>
                cardBordered
                className="management-list-table"
                columns={skillColumns}
                dateFormatter="string"
                headerTitle="Skill 管理"
                loading={loading}
                options={{
                  density: true,
                  fullScreen: true,
                  reload,
                  setting: true,
                }}
                pagination={{
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`,
                }}
                rowKey="id"
                scroll={{ x: 1056 }}
                search={false}
                dataSource={skills}
                tableLayout="fixed"
                toolBarRender={() => [
                  <Button key="create-skill" icon={<PlusOutlined />} type="primary" onClick={openCreateSkill}>
                    新增 Skill
                  </Button>,
                  <Button key="upload-skill" onClick={() => setSkillPackageModalOpen(true)}>
                    上传 Skill 包
                  </Button>,
                ]}
              />
            ),
          },
        ]}
      />

      <Modal
        open={skillModalOpen}
        title={editingSkill ? '编辑 Skill' : '新增 Skill'}
        okText="保存"
        onCancel={closeSkillModal}
        onOk={submitSkill}
      >
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
              <Select options={SKILL_STATUS_OPTIONS} />
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
              <Select options={SKILL_STATUS_OPTIONS} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      <Modal
        open={agentModalOpen}
        title={editingAgent ? '编辑 Agent' : '新增 Agent'}
        okText="保存"
        onCancel={closeAgentModal}
        onOk={submitAgent}
      >
        <Form form={agentForm} layout="vertical" initialValues={{ status: 'active' }}>
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="编码" name="code" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="模型网关" name="model_gateway_config_id">
            <Select
              optionFilterProp="label"
              options={modelGatewayOptions}
              placeholder="选择模型网关"
              showSearch
            />
          </Form.Item>
          <Form.Item label="默认 Skill IDs" name="default_skill_ids">
            <Input placeholder="多个 ID 用英文逗号分隔" />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select options={AGENT_STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item label="系统提示词" name="system_prompt" rules={[{ required: true }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
}
