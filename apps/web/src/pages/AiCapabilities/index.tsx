import { PageContainer, type ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, Tabs, Tag, Switch, Upload, message } from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
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
  input_schema_json?: string;
  name: string;
  output_schema_json?: string;
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

type AiAgentRow = AiAgentRecord & {
  defaultSkillText: string;
  modelGatewayText: string;
  searchText: string;
} & Record<string, unknown>;

type AiSkillRow = AiSkillRecord & {
  reviewValue: string;
  searchText: string;
} & Record<string, unknown>;

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

const SKILL_SOURCE_OPTIONS = [
  { label: '表单', value: 'form' },
  { label: '文件包', value: 'package' },
];

const REVIEW_OPTIONS = [
  { label: '需要', value: 'required' },
  { label: '不需要', value: 'optional' },
];

const stringValue = (value: unknown) => {
  if (typeof value === 'string') {
    return value.trim() || undefined;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return undefined;
};

const modelGatewayIdFromReference = (value: unknown): string | undefined => {
  const primitive = stringValue(value);
  if (primitive) {
    return primitive;
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  const record = value as Record<string, unknown>;
  return (
    stringValue(record.id)
    ?? stringValue(record.config_id)
    ?? stringValue(record.model_gateway_config_id)
  );
};

const modelGatewayReferenceCandidates = (agent: AiAgentRecord) => {
  const record = agent as AiAgentRecord & Record<string, unknown>;
  return [
    record.model_gateway_config_id,
    record.model_gateway_config,
    record.model_gateway_config_snapshot,
    record.resolved_model_gateway_config,
  ];
};

const modelGatewayIdFromAgent = (agent: AiAgentRecord) => {
  for (const candidate of modelGatewayReferenceCandidates(agent)) {
    const configId = modelGatewayIdFromReference(candidate);
    if (configId) {
      return configId;
    }
  }
  return undefined;
};

const modelGatewayLabelFromReference = (value: unknown): string | undefined => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  const record = value as Record<string, unknown>;
  const name =
    stringValue(record.name)
    ?? stringValue(record.label)
    ?? stringValue(record.title)
    ?? modelGatewayIdFromReference(record);
  if (!name) {
    return undefined;
  }
  const model =
    stringValue(record.defaultChatModel)
    ?? stringValue(record.default_chat_model)
    ?? stringValue(record.chat_model)
    ?? stringValue(record.model);
  return model ? `${name} (${model})` : name;
};

const prettyJson = (value: unknown) => JSON.stringify(value && typeof value === 'object' ? value : {}, null, 2);

const parseJsonObject = (value: string | undefined, label: string): Record<string, unknown> => {
  const rawValue = value?.trim() || '{}';
  try {
    const parsed = JSON.parse(rawValue) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error(`${label} 必须是 JSON 对象`);
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    if (error instanceof Error && error.message.includes('必须是 JSON 对象')) {
      throw error;
    }
    throw new Error(`${label} 不是合法 JSON`);
  }
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
    queueMicrotask(() => {
      void reload();
    });
  }, [reload]);

  const openCreateSkill = () => {
    setEditingSkill(undefined);
    skillForm.resetFields();
    skillForm.setFieldsValue({
      input_schema_json: prettyJson({}),
      output_schema_json: prettyJson({}),
      requires_human_review: false,
      risk_level: 'medium',
      status: 'active',
      version: '1.0.0',
    });
    setSkillModalOpen(true);
  };

  const openEditSkill = useCallback((record: AiSkillRecord) => {
    setEditingSkill(record);
    skillForm.setFieldsValue({
      code: record.code,
      input_schema_json: prettyJson(record.input_schema),
      name: record.name,
      output_schema_json: prettyJson(record.output_schema),
      prompt_template: record.prompt_template ?? '',
      requires_human_review: Boolean(record.requires_human_review),
      risk_level: record.risk_level ?? 'medium',
      status: record.status,
      version: record.version ?? '1.0.0',
    });
    setSkillModalOpen(true);
  }, [skillForm]);

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

  const openEditAgent = useCallback((record: AiAgentRecord) => {
    setEditingAgent(record);
    agentForm.setFieldsValue({
      code: record.code,
      default_skill_ids: Array.isArray(record.default_skill_ids) ? record.default_skill_ids.join(', ') : '',
      model_gateway_config_id: modelGatewayIdFromAgent(record) ?? '',
      name: record.name,
      status: record.status,
      system_prompt: record.system_prompt ?? '',
    });
    setAgentModalOpen(true);
  }, [agentForm]);

  const closeAgentModal = () => {
    setAgentModalOpen(false);
    setEditingAgent(undefined);
    agentForm.resetFields();
  };

  const submitSkill = async () => {
    const values = await skillForm.validateFields();
    let schemaPayload: Pick<AiSkillRecord, 'input_schema' | 'output_schema'>;
    try {
      schemaPayload = {
        input_schema: parseJsonObject(values.input_schema_json, '输入 Schema JSON'),
        output_schema: parseJsonObject(values.output_schema_json, '输出 Schema JSON'),
      };
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Schema JSON 不合法');
      return;
    }
    const payload = {
      code: values.code,
      name: values.name,
      prompt_template: values.prompt_template,
      requires_human_review: values.requires_human_review,
      risk_level: values.risk_level,
      status: values.status,
      version: values.version,
      ...schemaPayload,
    };
    if (editingSkill) {
      await updateAiSkill(editingSkill.id, payload);
      message.success('Skill 已更新');
    } else {
      await createAiSkill(payload);
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
      message.success('AI角色已更新');
    } else {
      await createAiAgent(payload);
      message.success('AI角色已创建');
    }
    closeAgentModal();
    await reload();
  };

  const disableSkill = useCallback(async (record: AiSkillRecord) => {
    await updateAiSkill(record.id, { status: 'disabled' });
    message.success('Skill 已删除');
    await reload();
  }, [reload]);

  const disableAgent = useCallback(async (record: AiAgentRecord) => {
    await updateAiAgent(record.id, { status: 'disabled' });
    message.success('AI角色已删除');
    await reload();
  }, [reload]);

  const renderStatusTag = (value: unknown) => {
    const status = String(value ?? '');
    return <StatusTag color={STATUS_COLORS[status] ?? 'default'} label={STATUS_LABELS[status] ?? status} />;
  };

  const modelGatewayConfigName = useCallback((agent: AiAgentRecord) => {
    const candidates = modelGatewayReferenceCandidates(agent);
    for (const candidate of candidates) {
      const configId = modelGatewayIdFromReference(candidate);
      const config = configId ? modelGatewayConfigs.find((item) => item.id === configId) : undefined;
      if (config) {
        return `${config.name} (${config.defaultChatModel})`;
      }
    }
    for (const candidate of candidates) {
      const label = modelGatewayLabelFromReference(candidate);
      if (label) {
        return label;
      }
    }
    const configId = modelGatewayIdFromAgent(agent);
    if (!configId) {
      return '-';
    }
    return configId;
  }, [modelGatewayConfigs]);

  const modelGatewayOptions = [
    { label: '不指定', value: '' },
    ...modelGatewayConfigs.map((config) => ({
      disabled: config.status !== 'active',
      label: `${config.name} / ${config.defaultChatModel}${config.isDefault ? ' / 默认' : ''}`,
      value: config.id,
    })),
  ];

  const agentRows = useMemo<AiAgentRow[]>(
    () =>
      agents.map((agent) => {
        const defaultSkillText = Array.isArray(agent.default_skill_ids) && agent.default_skill_ids.length
          ? agent.default_skill_ids.join(', ')
          : '-';
        const modelGatewayText = modelGatewayConfigName(agent);
        return {
          ...agent,
          defaultSkillText,
          modelGatewayText,
          searchText: [
            agent.name,
            agent.code,
            modelGatewayText,
            defaultSkillText,
            agent.status,
            agent.system_prompt ?? '',
          ].join(' '),
        };
      }),
    [agents, modelGatewayConfigName],
  );

  const skillRows = useMemo<AiSkillRow[]>(
    () =>
      skills.map((skill) => {
        const reviewValue = skill.requires_human_review ? 'required' : 'optional';
        return {
          ...skill,
          reviewValue,
          searchText: [
            skill.name,
            skill.code,
            skill.version ?? '',
            skill.source_type ?? '',
            skill.risk_level ?? '',
            skill.status,
            skill.prompt_template ?? '',
            JSON.stringify(skill.input_schema ?? {}),
            JSON.stringify(skill.output_schema ?? {}),
          ].join(' '),
        };
      }),
    [skills],
  );

  const agentColumns = useMemo<ProColumns<AiAgentRow>[]>(
    () => [
      { dataIndex: 'name', ellipsis: true, title: '名称', width: 220 },
      { dataIndex: 'code', ellipsis: true, title: '编码', width: 180 },
      {
        dataIndex: 'modelGatewayText',
        ellipsis: true,
        title: '模型网关',
        width: 240,
      },
      {
        dataIndex: 'defaultSkillText',
        ellipsis: true,
        title: '默认 Skills',
        width: 220,
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
              title="确认删除该 AI角色？"
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
    [disableAgent, openEditAgent],
  );

  const skillColumns = useMemo<ProColumns<AiSkillRow>[]>(
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
    [disableSkill, openEditSkill],
  );

  return (
    <PageContainer title={false}>
      <Tabs
        items={[
          {
            key: 'agents',
            label: 'AI角色',
            children: (
              <ManagementListPage<AiAgentRow>
                breadcrumbGroup="任务中心"
                columns={agentColumns}
                dataSource={agentRows}
                embedded
                filters={[
                  {
                    label: '关键词',
                    name: 'searchText',
                    placeholder: '搜索名称、编码、模型、Skill 或提示词',
                    type: 'text',
                  },
                  {
                    label: '状态',
                    name: 'status',
                    options: AGENT_STATUS_OPTIONS,
                    type: 'select',
                  },
                  {
                    label: '模型网关',
                    name: 'modelGatewayText',
                    placeholder: '请输入模型网关',
                    type: 'text',
                  },
                ]}
                loading={loading}
                onPrimaryAction={openCreateAgent}
                onReload={reload}
                primaryAction="新增 AI角色"
                rowKey="id"
                tableScroll={{ x: 1156 }}
                tableTitle="AI角色配置"
                title="AI 能力配置"
                viewStorageKey="tasks.ai-capabilities.agents"
              />
            ),
          },
          {
            key: 'skills',
            label: 'Skill 管理',
            children: (
              <ManagementListPage<AiSkillRow>
                breadcrumbGroup="任务中心"
                columns={skillColumns}
                dataSource={skillRows}
                embedded
                filters={[
                  {
                    label: '关键词',
                    name: 'searchText',
                    placeholder: '搜索名称、编码、版本、风险等级或 Prompt',
                    type: 'text',
                  },
                  {
                    label: '状态',
                    name: 'status',
                    options: SKILL_STATUS_OPTIONS,
                    type: 'select',
                  },
                  {
                    label: '来源',
                    name: 'source_type',
                    options: SKILL_SOURCE_OPTIONS,
                    type: 'select',
                  },
                  {
                    label: '人工确认',
                    name: 'reviewValue',
                    options: REVIEW_OPTIONS,
                    type: 'select',
                  },
                ]}
                loading={loading}
                onPrimaryAction={openCreateSkill}
                onReload={reload}
                primaryAction="新增 Skill"
                rowKey="id"
                tableScroll={{ x: 1056 }}
                tableTitle="Skill 管理"
                title="AI 能力配置"
                toolbarActions={[
                  <Button key="upload-skill" onClick={() => setSkillPackageModalOpen(true)}>
                    上传 Skill 包
                  </Button>,
                ]}
                viewStorageKey="tasks.ai-capabilities.skills"
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
        width={760}
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
          <Form.Item
            extra="声明 Skill 需要的输入结构，定时作业运行前会用于链路校验。"
            label="输入 Schema JSON"
            name="input_schema_json"
          >
            <Input.TextArea rows={5} />
          </Form.Item>
          <Form.Item
            extra="声明 Skill 输出结构，结果写入映射必须能从该结构中取到字段。"
            label="输出 Schema JSON"
            name="output_schema_json"
          >
            <Input.TextArea rows={5} />
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
        title={editingAgent ? '编辑 AI角色' : '新增 AI角色'}
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
