import { PageContainer, type ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, Tabs, Tag, Switch, Upload, message } from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ManagementListQuery } from '../../components/ManagementListPage';
import type { ModelGatewayConfigRecord } from '../../data/management';
import {
  createAiAgent,
  createAiSkill,
  fetchAiAgents,
  fetchModelGatewayConfigs,
  fetchAiSkills,
  updateAiAgent,
  updateAiSkill,
  uploadAiAgentPackage,
  uploadAiSkillPackage,
  type AiAgentRecord,
  type AiSkillRecord,
} from '../../services/aiBrain';
import {
  AGENT_STATUS_OPTIONS,
  DEFAULT_LIST_QUERY,
  REVIEW_OPTIONS,
  SKILL_SOURCE_OPTIONS,
  SKILL_STATUS_OPTIONS,
  STATUS_COLORS,
  STATUS_LABELS,
  agentListQuery,
  modelGatewayIdFromAgent,
  modelGatewayIdFromReference,
  modelGatewayLabelFromReference,
  modelGatewayReferenceCandidates,
  parseJsonObject,
  prettyJson,
  skillListQuery,
  type AgentFormValues,
  type AgentPackageFormValues,
  type AiAgentRow,
  type AiSkillRow,
  type RemotePageState,
  type SkillFormValues,
  type SkillPackageFormValues,
} from './components/aiCapabilitiesHelpers';

export default function AiCapabilitiesPage() {
  const [skillForm] = Form.useForm<SkillFormValues>();
  const [skillPackageForm] = Form.useForm<SkillPackageFormValues>();
  const [agentForm] = Form.useForm<AgentFormValues>();
  const [agentPackageForm] = Form.useForm<AgentPackageFormValues>();
  const [skills, setSkills] = useState<AiSkillRecord[]>([]);
  const [agents, setAgents] = useState<AiAgentRecord[]>([]);
  const skillQueryRef = useRef<ManagementListQuery>(DEFAULT_LIST_QUERY);
  const agentQueryRef = useRef<ManagementListQuery>(DEFAULT_LIST_QUERY);
  const [skillPageState, setSkillPageState] = useState<RemotePageState>({
    page: DEFAULT_LIST_QUERY.page,
    pageSize: DEFAULT_LIST_QUERY.pageSize,
    total: 0,
  });
  const [agentPageState, setAgentPageState] = useState<RemotePageState>({
    page: DEFAULT_LIST_QUERY.page,
    pageSize: DEFAULT_LIST_QUERY.pageSize,
    total: 0,
  });
  const [loading, setLoading] = useState(false);
  const [skillModalOpen, setSkillModalOpen] = useState(false);
  const [skillPackageModalOpen, setSkillPackageModalOpen] = useState(false);
  const [skillPackageFiles, setSkillPackageFiles] = useState<UploadFile[]>([]);
  const [agentModalOpen, setAgentModalOpen] = useState(false);
  const [agentPackageModalOpen, setAgentPackageModalOpen] = useState(false);
  const [agentPackageFiles, setAgentPackageFiles] = useState<UploadFile[]>([]);
  const [editingSkill, setEditingSkill] = useState<AiSkillRecord>();
  const [editingAgent, setEditingAgent] = useState<AiAgentRecord>();
  const [modelGatewayConfigs, setModelGatewayConfigs] = useState<ModelGatewayConfigRecord[]>([]);

  const loadSkills = useCallback(async (query: ManagementListQuery = skillQueryRef.current) => {
    skillQueryRef.current = query;
    setLoading(true);
    try {
      const result = await fetchAiSkills(skillListQuery(query));
      setSkills(result.rows);
      setSkillPageState({
        page: result.page,
        pageSize: result.pageSize,
        performance: result.performance,
        total: result.total,
      });
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Skill 列表加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAgents = useCallback(async (query: ManagementListQuery = agentQueryRef.current) => {
    agentQueryRef.current = query;
    setLoading(true);
    try {
      const result = await fetchAiAgents(agentListQuery(query));
      setAgents(result.rows);
      setAgentPageState({
        page: result.page,
        pageSize: result.pageSize,
        performance: result.performance,
        total: result.total,
      });
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'AI角色列表加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [nextSkills, nextAgents, nextModelGatewayConfigs] = await Promise.all([
        fetchAiSkills(skillListQuery(skillQueryRef.current)),
        fetchAiAgents(agentListQuery(agentQueryRef.current)),
        fetchModelGatewayConfigs(),
      ]);
      setSkills(nextSkills.rows);
      setAgents(nextAgents.rows);
      setSkillPageState({
        page: nextSkills.page,
        pageSize: nextSkills.pageSize,
        performance: nextSkills.performance,
        total: nextSkills.total,
      });
      setAgentPageState({
        page: nextAgents.page,
        pageSize: nextAgents.pageSize,
        performance: nextAgents.performance,
        total: nextAgents.total,
      });
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

  const openAgentPackageModal = () => {
    agentPackageForm.resetFields();
    agentPackageForm.setFieldsValue({
      brain_app_id: 'rd_brain',
      default_skill_ids: [],
      status: 'active',
      version: '1.0.0',
    });
    setAgentPackageFiles([]);
    setAgentPackageModalOpen(true);
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

  const submitAgentPackage = async () => {
    const values = await agentPackageForm.validateFields();
    const originFile = agentPackageFiles[0]?.originFileObj;
    if (!originFile) {
      message.warning('请选择 Agent 包 zip 文件');
      return;
    }
    await uploadAiAgentPackage(originFile, {
      brainAppId: values.brain_app_id || 'rd_brain',
      code: values.code,
      defaultSkillIds: values.default_skill_ids ?? [],
      modelGatewayConfigId: values.model_gateway_config_id || undefined,
      name: values.name,
      status: values.status,
      version: values.version,
    });
    message.success('Agent 包已上传');
    setAgentPackageModalOpen(false);
    setAgentPackageFiles([]);
    agentPackageForm.resetFields();
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

  const skillOptions = skills.map((skill) => ({
    disabled: skill.status !== 'active',
    label: `${skill.name} / ${skill.code}${skill.status === 'active' ? '' : ' / 停用'}`,
    value: skill.id,
  }));

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
        dataIndex: 'source_type',
        title: '来源',
        width: 120,
        render: (value) => <Tag>{value === 'package' ? '文件包' : '表单'}</Tag>,
      },
      {
        key: 'runtime_capabilities',
        title: '运行边界',
        width: 220,
        render: (_, record) => {
          const scriptExecution = record.runtime_capabilities?.script_execution;
          return (
            <Space size={4} wrap>
              <Tag color="blue">系统提示词</Tag>
              <Tag color="geekblue">默认 Skill</Tag>
              {record.source_type === 'package' ? <Tag color="cyan">文件包上下文</Tag> : null}
              {scriptExecution === 'disabled_pending_sandbox' ? (
                <Tag color="orange">脚本不自动执行</Tag>
              ) : null}
            </Space>
          );
        },
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
        key: 'runtime_capabilities',
        title: '运行边界',
        width: 180,
        render: (_, record) => {
          const scriptExecution = record.runtime_capabilities?.script_execution;
          return (
            <Space size={4} wrap>
              <Tag color="blue">Prompt/Schema</Tag>
              {scriptExecution === 'disabled_pending_sandbox' ? (
                <Tag color="orange">脚本不自动执行</Tag>
              ) : null}
            </Space>
          );
        },
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
                remote={{
                  onChange: loadAgents,
                  page: agentPageState.page,
                  pageSize: agentPageState.pageSize,
                  performance: agentPageState.performance,
                  total: agentPageState.total,
                }}
                rowKey="id"
                tableScroll={{ x: 1496 }}
                tableTitle="AI角色配置"
                title="AI 能力配置"
                toolbarActions={[
                  <Button key="upload-agent" onClick={openAgentPackageModal}>
                    上传 Agent 包
                  </Button>,
                ]}
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
                remote={{
                  onChange: loadSkills,
                  page: skillPageState.page,
                  pageSize: skillPageState.pageSize,
                  performance: skillPageState.performance,
                  total: skillPageState.total,
                }}
                rowKey="id"
                tableScroll={{ x: 1236 }}
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
          <Form.Item
            extra="zip 内需包含 skill.yaml 或 SKILL.md；SKILL.md 会作为 Prompt 模板，Schema 文件参与输出契约校验，scripts/ 目录脚本仅记录运行边界，不会自动执行。"
            label="Skill 包"
          >
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
        open={agentPackageModalOpen}
        title="上传 Agent 包"
        onCancel={() => setAgentPackageModalOpen(false)}
        onOk={submitAgentPackage}
        width={720}
      >
        <Form
          form={agentPackageForm}
          layout="vertical"
          initialValues={{
            brain_app_id: 'rd_brain',
            default_skill_ids: [],
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
          <Space style={{ width: '100%' }} wrap>
            <Form.Item label="业务脑" name="brain_app_id" rules={[{ required: true }]}>
              <Input style={{ width: 180 }} />
            </Form.Item>
            <Form.Item label="版本" name="version" rules={[{ required: true }]}>
              <Input style={{ width: 180 }} />
            </Form.Item>
            <Form.Item label="状态" name="status">
              <Select options={AGENT_STATUS_OPTIONS} style={{ width: 160 }} />
            </Form.Item>
          </Space>
          <Form.Item label="模型网关" name="model_gateway_config_id">
            <Select
              optionFilterProp="label"
              options={modelGatewayOptions}
              placeholder="可由 agent.yaml 指定"
              showSearch
            />
          </Form.Item>
          <Form.Item label="默认 Skills" name="default_skill_ids">
            <Select
              mode="multiple"
              optionFilterProp="label"
              options={skillOptions}
              placeholder="可由 agent.yaml 指定"
              showSearch
            />
          </Form.Item>
          <Form.Item
            extra="zip 内需包含 agent.yaml 和 AGENT.md；AGENT.md 会作为系统提示词，脚本文件仅记录运行边界，不会自动执行。"
            label="Agent 包"
          >
            <Upload
              accept=".zip"
              beforeUpload={() => false}
              fileList={agentPackageFiles}
              maxCount={1}
              onChange={({ fileList }) => setAgentPackageFiles(fileList)}
            >
              <Button>选择 zip 文件</Button>
            </Upload>
          </Form.Item>
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
