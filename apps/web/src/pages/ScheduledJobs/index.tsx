import { DeleteOutlined, EditOutlined, EyeOutlined, PlayCircleOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, Descriptions, Form, Input, InputNumber, Modal, Select, Space, Tabs, Tag, Switch, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  createScheduledJob,
  deleteScheduledJob,
  fetchActiveProductOptions,
  fetchAiAgents,
  fetchAiSkills,
  fetchManagementKnowledge,
  fetchModelGatewayConfigs,
  fetchPluginActions,
  fetchPluginConnections,
  fetchScheduledJobRuns,
  fetchScheduledJobs,
  runScheduledJob,
  updateScheduledJob,
  type AiAgentRecord,
  type AiSkillRecord,
  type PluginActionRecord,
  type PluginConnectionRecord,
  type ProductFilterOption,
  type ScheduledJobRecord,
  type ScheduledJobResultAction,
  type ScheduledJobRunRecord,
} from '../../services/aiBrain';
import type { ModelGatewayConfigRecord } from '../../data/management';
import type { KnowledgeRecord } from '../../data/management';

type ScheduledJobFormValues = {
  agent_id?: string;
  cron_expression?: string;
  enabled: boolean;
  execution_mode: string;
  interval_seconds?: number;
  job_type: string;
  knowledge_document_ids?: string[];
  model_gateway_config_id?: string;
  name: string;
  plugin_action_id?: string;
  plugin_connection_id?: string;
  plugin_input_mapping?: string;
  plugin_output_mapping?: string;
  product_id?: string;
  result_actions?: ScheduledJobResultAction[];
  schedule_type: string;
  skill_ids?: string[];
  source_system: string;
};

const jobTypeOptions = [
  { label: '代码仓库巡检（质量 / 安全 / 规范）', value: 'code_repository_inspection' },
  { label: '用户反馈洞察抽取（取数 + AI 分析 + 写入）', value: 'user_feedback_insight_extract' },
  { label: '迭代规划建议生成', value: 'iteration_plan_suggestion_generate' },
  { label: '线上日志 AI 分析', value: 'online_log_ai_analysis' },
  { label: '用户使用指标采集', value: 'user_usage_metric_collect' },
  { label: '用户反馈采集（仅取数，不调用 AI）', value: 'user_feedback_collect' },
  { label: '线上日志指标采集', value: 'online_log_metric_collect' },
  { label: 'GitLab 每日代码指标采集', value: 'gitlab_daily_code_metric_collect' },
  { label: 'Jenkins 发布记录采集', value: 'jenkins_release_collect' },
  { label: '插件动作调用', value: 'plugin_action_invoke' },
  { label: '看板快照刷新', value: 'dashboard_snapshot_refresh' },
  { label: '生命周期上下文刷新', value: 'lifecycle_context_refresh' },
  { label: '待归属数据重试', value: 'pending_attribution_retry' },
];

const jobTypeLabelByValue = new Map(jobTypeOptions.map((option) => [option.value, option.label]));

const executionModeOptions = [
  { label: '确定性执行', value: 'deterministic' },
  { label: 'AI 辅助', value: 'ai_assisted' },
  { label: 'AI 生成', value: 'ai_generated' },
];

const executionModeLabelByValue = new Map(executionModeOptions.map((option) => [option.value, option.label]));

const scheduleTypeOptions = [
  { label: '手动触发', value: 'manual' },
  { label: 'Cron 定时', value: 'cron' },
  { label: '固定间隔', value: 'interval' },
];

const scheduleTypeLabelByValue = new Map(scheduleTypeOptions.map((option) => [option.value, option.label]));

const statusLabelByValue = new Map([
  ['active', '启用'],
  ['disabled', '停用'],
]);

const codeInspectionResultActionOptions = [
  { label: '写入代码审查表', value: 'write_code_inspection_report' },
  { label: '严重问题自动创建 Bug', value: 'create_bug_for_severe_findings' },
  { label: '发送问题消息通知', value: 'send_notification' },
];

const resultActionLabelByValue = new Map(codeInspectionResultActionOptions.map((option) => [option.value, option.label]));

const severityThresholdOptions = [
  { label: 'critical', value: 'critical' },
  { label: 'high', value: 'high' },
  { label: 'medium', value: 'medium' },
];

const notificationChannelOptions = [
  { label: '邮件', value: 'email' },
  { label: '钉钉机器人', value: 'dingtalk' },
];

const defaultCodeInspectionResultActions: ScheduledJobResultAction[] = [
  { type: 'write_code_inspection_report' },
  { severity_threshold: 'critical', type: 'create_bug_for_severe_findings' },
  { channels: ['email'], recipients: [], type: 'send_notification' },
];

function resultActionLabels(actions?: ScheduledJobResultAction[]) {
  const labels = (actions ?? []).map((action) => resultActionLabelByValue.get(action.type) ?? action.type);
  return labels.join('、');
}

function ellipsisText(value: string | undefined) {
  const text = value || '-';
  return (
    <Typography.Text ellipsis={{ tooltip: text }} style={{ display: 'block', maxWidth: '100%' }}>
      {text}
    </Typography.Text>
  );
}

function isEmptyJsonValue(value: unknown): boolean {
  return (
    value == null
    || (Array.isArray(value) && value.length === 0)
    || (typeof value === 'object'
      && !Array.isArray(value)
      && Object.keys(value as Record<string, unknown>).length === 0)
  );
}

function formatJsonValue(value: unknown): string {
  if (isEmptyJsonValue(value)) {
    return '暂无数据';
  }
  return JSON.stringify(value, null, 2);
}

function JsonPreview({ title, value }: { title: string; value: unknown }) {
  return (
    <Space orientation="vertical" size={6} style={{ width: '100%' }}>
      <Typography.Text strong>{title}</Typography.Text>
      <Typography.Paragraph
        copyable={!isEmptyJsonValue(value)}
        style={{
          background: '#f6f8fa',
          border: '1px solid #e5e7eb',
          borderRadius: 6,
          marginBottom: 0,
          maxHeight: 260,
          overflow: 'auto',
          padding: 12,
          whiteSpace: 'pre-wrap',
        }}
      >
        {formatJsonValue(value)}
      </Typography.Paragraph>
    </Space>
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function getRunExecutionNode(run: ScheduledJobRunRecord, nodeKey: string): unknown {
  const nodes = run.result_summary?.execution_nodes;
  if (isRecord(nodes)) {
    return nodes[nodeKey];
  }
  return undefined;
}

function snapshotStringValue(snapshot: Record<string, unknown> | undefined, key: string): string | undefined {
  const value = snapshot?.[key];
  return typeof value === 'string' && value ? value : undefined;
}

function snapshotStringListValue(snapshot: Record<string, unknown> | undefined, key: string): string[] {
  const value = snapshot?.[key];
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

export default function ScheduledJobsPage() {
  const [form] = Form.useForm<ScheduledJobFormValues>();
  const [jobs, setJobs] = useState<ScheduledJobRecord[]>([]);
  const [runs, setRuns] = useState<ScheduledJobRunRecord[]>([]);
  const [pluginActions, setPluginActions] = useState<PluginActionRecord[]>([]);
  const [pluginConnections, setPluginConnections] = useState<PluginConnectionRecord[]>([]);
  const [products, setProducts] = useState<ProductFilterOption[]>([]);
  const [agents, setAgents] = useState<AiAgentRecord[]>([]);
  const [skills, setSkills] = useState<AiSkillRecord[]>([]);
  const [knowledgeDocuments, setKnowledgeDocuments] = useState<KnowledgeRecord[]>([]);
  const [modelGatewayConfigs, setModelGatewayConfigs] = useState<ModelGatewayConfigRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingJob, setEditingJob] = useState<ScheduledJobRecord | undefined>();
  const [selectedRun, setSelectedRun] = useState<ScheduledJobRunRecord | undefined>();
  const [runningJobId, setRunningJobId] = useState<string | undefined>();
  const selectedJobType = Form.useWatch('job_type', form);
  const aiProcessingRequired = selectedJobType === 'user_feedback_insight_extract';
  const pluginActionRequired = ['code_repository_inspection', 'plugin_action_invoke', 'user_feedback_insight_extract'].includes(
    selectedJobType ?? '',
  );
  const pluginActionById = useMemo(
    () => new Map(pluginActions.map((action) => [action.id, action])),
    [pluginActions],
  );
  const pluginConnectionById = useMemo(
    () => new Map(pluginConnections.map((connection) => [connection.id, connection])),
    [pluginConnections],
  );
  const modelGatewayConfigById = useMemo(
    () => new Map(modelGatewayConfigs.map((config) => [config.id, config])),
    [modelGatewayConfigs],
  );
  const agentById = useMemo(
    () => new Map(agents.map((agent) => [agent.id, agent])),
    [agents],
  );
  const skillById = useMemo(
    () => new Map(skills.map((skill) => [skill.id, skill])),
    [skills],
  );
  const selectedRunConfigSnapshot = selectedRun?.config_snapshot;
  const selectedRunAgentId = snapshotStringValue(selectedRunConfigSnapshot, 'agent_id');
  const selectedRunModelGatewayConfigId = snapshotStringValue(selectedRunConfigSnapshot, 'model_gateway_config_id');
  const selectedRunSkillIds = snapshotStringListValue(selectedRunConfigSnapshot, 'skill_ids');
  const selectedRunJobType = snapshotStringValue(selectedRunConfigSnapshot, 'job_type');
  const selectedRunExecutionMode = snapshotStringValue(selectedRunConfigSnapshot, 'execution_mode');
  const selectedRunAgentLabel =
    snapshotStringValue(selectedRun?.resolved_agent_snapshot, 'name')
    ?? (selectedRunAgentId ? agentById.get(selectedRunAgentId)?.name ?? selectedRunAgentId : '-');
  const selectedRunModelLabel =
    selectedRunModelGatewayConfigId
      ? modelGatewayConfigById.get(selectedRunModelGatewayConfigId)?.name ?? selectedRunModelGatewayConfigId
      : '-';
  const selectedRunSkillLabels =
    selectedRun?.resolved_skill_snapshots
      ?.map((skill) => String(skill.name ?? skill.code ?? skill.id ?? ''))
      .filter(Boolean)
      .join('、')
    || selectedRunSkillIds.map((skillId) => skillById.get(skillId)?.name ?? skillId).join('、')
    || '-';

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [
        nextJobs,
        nextRuns,
        nextPluginActions,
        nextPluginConnections,
        nextProducts,
        nextAgents,
        nextSkills,
        nextKnowledgeDocuments,
        nextModelGatewayConfigs,
      ] =
        await Promise.all([
          fetchScheduledJobs(),
          fetchScheduledJobRuns(),
          fetchPluginActions(),
          fetchPluginConnections(),
          fetchActiveProductOptions(),
          fetchAiAgents(),
          fetchAiSkills(),
          fetchManagementKnowledge(),
          fetchModelGatewayConfigs(),
        ]);
      setJobs(nextJobs);
      setRuns(nextRuns);
      setPluginActions(nextPluginActions);
      setPluginConnections(nextPluginConnections);
      setProducts(nextProducts);
      setAgents(nextAgents.filter((agent) => agent.status === 'active'));
      setSkills(nextSkills.filter((skill) => skill.status === 'active'));
      setKnowledgeDocuments(
        nextKnowledgeDocuments.filter((document) =>
          ['indexed', 'text_indexed', 'vector_indexed'].includes(document.status),
        ),
      );
      setModelGatewayConfigs(nextModelGatewayConfigs.filter((config) => config.status === 'active'));
    } catch (error) {
      message.error(error instanceof Error ? error.message : '定时作业加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const openCreateJobModal = () => {
    setEditingJob(undefined);
    form.resetFields();
    form.setFieldsValue({
      enabled: true,
      execution_mode: 'ai_generated',
      job_type: 'user_feedback_insight_extract',
      schedule_type: 'manual',
      source_system: 'ai-brain',
    });
    setModalOpen(true);
  };

  const openEditJobModal = (job: ScheduledJobRecord) => {
    setEditingJob(job);
    form.resetFields();
    form.setFieldsValue({
      agent_id: job.agent_id ?? undefined,
      cron_expression: job.cron_expression ?? undefined,
      enabled: job.enabled ?? true,
      execution_mode: job.execution_mode ?? 'deterministic',
      interval_seconds: job.interval_seconds ?? undefined,
      job_type: job.job_type,
      knowledge_document_ids: job.knowledge_document_ids ?? [],
      model_gateway_config_id: job.model_gateway_config_id ?? undefined,
      name: job.name,
      plugin_action_id: job.plugin_action_id ?? undefined,
      plugin_connection_id: job.plugin_connection_id ?? undefined,
      product_id: job.product_id ?? undefined,
      result_actions: job.result_actions?.length ? job.result_actions : defaultCodeInspectionResultActions,
      schedule_type: job.schedule_type ?? 'manual',
      skill_ids: job.skill_ids ?? [],
      source_system: job.source_system ?? 'ai-brain',
    });
    setModalOpen(true);
  };

  const closeJobModal = () => {
    setModalOpen(false);
    setEditingJob(undefined);
    form.resetFields();
  };

  const submitJob = async () => {
    const values = await form.validateFields();
    const requestPayload: Partial<ScheduledJobRecord> = {
      ...values,
      plugin_input_mapping: editingJob?.plugin_input_mapping ?? {},
      plugin_output_mapping: editingJob?.plugin_output_mapping ?? {},
      knowledge_document_ids: values.knowledge_document_ids ?? [],
      result_actions:
        values.job_type === 'code_repository_inspection'
          ? values.result_actions?.length
            ? values.result_actions
            : defaultCodeInspectionResultActions
          : [],
      skill_ids: values.skill_ids ?? [],
    };
    if (editingJob) {
      await updateScheduledJob(editingJob.id, requestPayload);
      message.success('定时作业已更新');
    } else {
      await createScheduledJob(requestPayload);
      message.success('定时作业已创建');
    }
    closeJobModal();
    await reload();
  };

  const triggerJob = async (job: ScheduledJobRecord) => {
    const hide = message.loading('作业执行中，请稍候...', 0);
    setRunningJobId(job.id);
    try {
      const run = await runScheduledJob(job.id);
      setSelectedRun(run);
      message.success('作业运行完成');
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '作业运行失败');
    } finally {
      hide();
      setRunningJobId(undefined);
    }
  };

  const confirmDeleteJob = (job: ScheduledJobRecord) => {
    Modal.confirm({
      title: '删除定时作业',
      content: `确定删除「${job.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        await deleteScheduledJob(job.id);
        message.success('定时作业已删除');
        await reload();
      },
    });
  };

  return (
    <PageContainer title="定时作业">
      <Tabs
        items={[
          {
            key: 'jobs',
            label: '作业配置',
            children: (
              <ProTable<ScheduledJobRecord>
                cardBordered
                className="management-list-table"
                dateFormatter="string"
                headerTitle="作业配置"
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
                scroll={{ x: 1860 }}
                search={false}
                dataSource={jobs}
                tableLayout="fixed"
                toolBarRender={() => [
                  <Button key="create-job" aria-label="新增作业" icon={<PlusOutlined />} type="primary" onClick={openCreateJobModal}>
                    新增作业
                  </Button>,
                  <Button key="reload-jobs" icon={<ReloadOutlined />} onClick={reload}>
                    刷新
                  </Button>,
                ]}
                columns={[
                  { dataIndex: 'name', title: '名称', width: 220, render: (value) => ellipsisText(String(value ?? '')) },
                  {
                    dataIndex: 'job_type',
                    title: '类型',
                    width: 190,
                    render: (value) => ellipsisText(jobTypeLabelByValue.get(String(value)) ?? String(value ?? '')),
                  },
                  {
                    dataIndex: 'plugin_connection_id',
                    title: '数据连接',
                    width: 220,
                    render: (value) => {
                      const connection = value ? pluginConnectionById.get(String(value)) : undefined;
                      return ellipsisText(connection ? `${connection.name} (${connection.environment ?? 'default'})` : String(value ?? ''));
                    },
                  },
                  {
                    dataIndex: 'model_gateway_config_id',
                    title: 'AI 模型',
                    width: 220,
                    render: (value) => {
                      const config = value ? modelGatewayConfigById.get(String(value)) : undefined;
                      return ellipsisText(config ? `${config.name} (${config.defaultChatModel})` : String(value ?? ''));
                    },
                  },
                  {
                    dataIndex: 'agent_id',
                    title: 'Agent',
                    width: 180,
                    render: (value) => {
                      const agent = value ? agentById.get(String(value)) : undefined;
                      return ellipsisText(agent ? agent.name : String(value ?? ''));
                    },
                  },
                  {
                    dataIndex: 'skill_ids',
                    title: 'Skills',
                    width: 220,
                    render: (value) => {
                      const labels = Array.isArray(value)
                        ? value.map((skillId) => skillById.get(String(skillId))?.name ?? String(skillId))
                        : [];
                      return ellipsisText(labels.join('、'));
                    },
                  },
                  {
                    dataIndex: 'plugin_action_id',
                    title: '插件动作',
                    width: 220,
                    render: (value) => {
                      const action = value ? pluginActionById.get(String(value)) : undefined;
                      return ellipsisText(action ? action.name : String(value ?? ''));
                    },
                  },
                  {
                    dataIndex: 'result_actions',
                    title: '结果动作',
                    width: 240,
                    render: (value) => ellipsisText(resultActionLabels(value as ScheduledJobResultAction[])),
                  },
                  {
                    dataIndex: 'execution_mode',
                    title: '执行模式',
                    width: 130,
                    render: (value) => executionModeLabelByValue.get(String(value)) ?? String(value ?? '-'),
                  },
                  {
                    dataIndex: 'schedule_type',
                    title: '调度',
                    width: 120,
                    render: (value) => scheduleTypeLabelByValue.get(String(value)) ?? String(value ?? '-'),
                  },
                  { dataIndex: 'next_run_at', title: '下次运行', width: 180, render: (value) => ellipsisText(String(value ?? '')) },
                  {
                    dataIndex: 'status',
                    title: '状态',
                    width: 100,
                    render: (value, row) => (
                      <Tag color={row.enabled ? 'green' : 'default'}>
                        {statusLabelByValue.get(String(value)) ?? String(value ?? '-')}
                      </Tag>
                    ),
                  },
                  {
                    fixed: 'right',
                    key: 'actions',
                    title: '操作',
                    valueType: 'option',
                    width: 260,
                    render: (_, row) => (
                      <Space className="management-row-actions" size={0}>
                        <Button
                          aria-label={`编辑作业 ${row.name}`}
                          icon={<EditOutlined />}
                          onClick={() => openEditJobModal(row)}
                          type="link"
                        >
                          编辑
                        </Button>
                        <Button
                          aria-label={`运行作业 ${row.name}`}
                          disabled={Boolean(runningJobId)}
                          icon={<PlayCircleOutlined />}
                          loading={runningJobId === row.id}
                          onClick={() => triggerJob(row)}
                          type="link"
                        >
                          运行
                        </Button>
                        <Button
                          aria-label={`删除作业 ${row.name}`}
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => confirmDeleteJob(row)}
                          type="link"
                        >
                          删除
                        </Button>
                      </Space>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'runs',
            label: '运行记录',
            children: (
              <ProTable<ScheduledJobRunRecord>
                cardBordered
                className="management-list-table"
                dateFormatter="string"
                headerTitle="运行记录"
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
                scroll={{ x: 1340 }}
                search={false}
                dataSource={runs}
                tableLayout="fixed"
                columns={[
                  { dataIndex: 'id', title: '运行 ID', ellipsis: true, width: 220 },
                  { dataIndex: 'scheduled_job_id', title: '作业 ID', ellipsis: true, width: 220 },
                  { dataIndex: 'status', title: '状态', width: 120 },
                  { dataIndex: 'trigger_type', title: '触发方式', width: 120 },
                  { dataIndex: 'collector_run_id', title: '采集运行', ellipsis: true, width: 220, render: (value) => value || '-' },
                  { dataIndex: 'plugin_invocation_log_id', title: '插件调用', ellipsis: true, width: 220, render: (value) => value || '-' },
                  { dataIndex: 'records_imported', title: '导入数', width: 100 },
                  { dataIndex: 'error_message', title: '错误', ellipsis: true, width: 180, render: (value) => value || '-' },
                  {
                    fixed: 'right',
                    key: 'actions',
                    title: '操作',
                    valueType: 'option',
                    width: 130,
                    render: (_, row) => (
                      <Button
                        aria-label={`查看运行结果 ${row.id}`}
                        icon={<EyeOutlined />}
                        onClick={() => setSelectedRun(row)}
                        type="link"
                      >
                        详情
                      </Button>
                    ),
                  },
                ]}
              />
            ),
          },
        ]}
      />

      <Modal
        open={modalOpen}
        title={editingJob ? '编辑定时作业' : '新增定时作业'}
        width={820}
        onCancel={closeJobModal}
        onOk={submitJob}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            enabled: true,
            execution_mode: 'ai_generated',
            job_type: 'user_feedback_insight_extract',
            schedule_type: 'manual',
            source_system: 'ai-brain',
          }}
        >
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="作业类型" name="job_type" rules={[{ required: true }]}>
            <Select
              options={jobTypeOptions}
              onChange={(value) => {
                if (value === 'code_repository_inspection') {
                  form.setFieldsValue({
                    execution_mode: 'deterministic',
                    result_actions: form.getFieldValue('result_actions')?.length
                      ? form.getFieldValue('result_actions')
                      : defaultCodeInspectionResultActions,
                  });
                }
              }}
            />
          </Form.Item>
          <Space>
            <Form.Item label="启用" name="enabled" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="执行模式" name="execution_mode">
              <Select options={executionModeOptions} />
            </Form.Item>
            <Form.Item label="调度方式" name="schedule_type">
              <Select options={scheduleTypeOptions} />
            </Form.Item>
          </Space>
          <Form.Item
            label="所属产品"
            name="product_id"
            rules={
              aiProcessingRequired || selectedJobType === 'code_repository_inspection'
                ? [{ required: true, message: '请选择产品' }]
                : []
            }
          >
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="请选择产品"
              options={products.map((product) => ({
                label: `${product.name} (${product.code})`,
                value: product.id,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="数据连接"
            name="plugin_connection_id"
            rules={
              pluginActionRequired
                ? [{ required: true, message: '请选择数据连接' }]
                : []
            }
          >
            <Select
              allowClear
              optionFilterProp="label"
              placeholder="请选择取数连接"
              showSearch
              options={pluginConnections.map((connection) => ({
                label: `${connection.name} (${connection.environment ?? 'default'})`,
                value: connection.id,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="AI 模型"
            name="model_gateway_config_id"
            rules={
              aiProcessingRequired
                ? [{ required: true, message: '请选择 AI 模型' }]
                : []
            }
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
          <Form.Item
            label="Agent"
            name="agent_id"
            rules={
              aiProcessingRequired
                ? [{ required: true, message: '请选择 Agent' }]
                : []
            }
          >
            <Select
              allowClear
              optionFilterProp="label"
              placeholder="请选择 Agent"
              showSearch
              options={agents.map((agent) => ({
                label: `${agent.name} (${agent.code})`,
                value: agent.id,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="Skills"
            name="skill_ids"
            rules={
              aiProcessingRequired
                ? [{ required: true, message: '请选择 Skills' }]
                : []
            }
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
          <Form.Item
            label={selectedJobType === 'code_repository_inspection' ? '插件扫描动作' : '结果动作'}
            name="plugin_action_id"
            rules={
              pluginActionRequired
                ? [{ required: true, message: '请选择插件动作' }]
                : []
            }
          >
            <Select
              allowClear
              optionFilterProp="label"
              placeholder="请选择结果动作"
              showSearch
              options={pluginActions.map((action) => ({
                label: `${action.name} (${action.code})`,
                value: action.id,
              }))}
            />
          </Form.Item>
          {selectedJobType === 'code_repository_inspection' ? (
            <Form.List name="result_actions">
              {(fields, { add, remove }) => (
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  <Typography.Text strong>结果动作</Typography.Text>
                  {fields.map((field) => (
                    <Space key={field.key} align="start" size={8} style={{ width: '100%' }}>
                      <Form.Item
                        {...field}
                        name={[field.name, 'type']}
                        rules={[{ required: true, message: '请选择结果动作' }]}
                        style={{ flex: 1, marginBottom: 8 }}
                      >
                        <Select options={codeInspectionResultActionOptions} placeholder="请选择结果动作" />
                      </Form.Item>
                      <Form.Item noStyle shouldUpdate>
                        {({ getFieldValue }) => {
                          const actionType = getFieldValue(['result_actions', field.name, 'type']);
                          if (actionType === 'create_bug_for_severe_findings') {
                            return (
                              <Form.Item
                                name={[field.name, 'severity_threshold']}
                                style={{ marginBottom: 8, width: 150 }}
                              >
                                <Select options={severityThresholdOptions} placeholder="严重级别" />
                              </Form.Item>
                            );
                          }
                          if (actionType === 'send_notification') {
                            return (
                              <Space direction="vertical" size={8} style={{ width: 360 }}>
                                <Form.Item
                                  name={[field.name, 'channels']}
                                  rules={[{ required: true, message: '请选择通知渠道' }]}
                                  style={{ marginBottom: 0 }}
                                >
                                  <Select mode="multiple" options={notificationChannelOptions} placeholder="通知渠道" />
                                </Form.Item>
                                <Form.Item name={[field.name, 'recipients']} style={{ marginBottom: 0 }}>
                                  <Select mode="tags" placeholder="邮件收件人" tokenSeparators={[',', '，']} />
                                </Form.Item>
                                <Form.Item name={[field.name, 'webhook_url']} style={{ marginBottom: 8 }}>
                                  <Input placeholder="钉钉机器人 Webhook" />
                                </Form.Item>
                              </Space>
                            );
                          }
                          return null;
                        }}
                      </Form.Item>
                      <Button danger icon={<DeleteOutlined />} onClick={() => remove(field.name)} />
                    </Space>
                  ))}
                  <Button icon={<PlusOutlined />} onClick={() => add({ type: 'write_code_inspection_report' })}>
                    新增结果动作
                  </Button>
                </Space>
              )}
            </Form.List>
          ) : null}
          <Form.Item label="Cron 表达式" name="cron_expression">
            <Input />
          </Form.Item>
          <Form.Item label="间隔秒数" name="interval_seconds">
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="来源系统" name="source_system" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        footer={<Button onClick={() => setSelectedRun(undefined)}>关闭</Button>}
        open={Boolean(selectedRun)}
        title="运行结果详情"
        width={980}
        onCancel={() => setSelectedRun(undefined)}
      >
        {selectedRun ? (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions
              bordered
              column={2}
              size="small"
              items={[
                { key: 'id', label: '运行 ID', children: selectedRun.id },
                { key: 'status', label: '状态', children: selectedRun.status },
                {
                  key: 'job_type',
                  label: '作业类型',
                  children: selectedRunJobType ? jobTypeLabelByValue.get(selectedRunJobType) ?? selectedRunJobType : '-',
                },
                {
                  key: 'execution_mode',
                  label: '执行模式',
                  children: selectedRunExecutionMode
                    ? executionModeLabelByValue.get(selectedRunExecutionMode) ?? selectedRunExecutionMode
                    : '-',
                },
                { key: 'model_gateway_config_id', label: 'AI 模型', children: selectedRunModelLabel },
                { key: 'agent_id', label: 'Agent', children: selectedRunAgentLabel },
                { key: 'skill_ids', label: 'Skills', children: selectedRunSkillLabels },
                { key: 'trigger_type', label: '触发方式', children: selectedRun.trigger_type || '-' },
                { key: 'records_imported', label: '导入数', children: selectedRun.records_imported ?? 0 },
                { key: 'collector_run_id', label: '采集运行', children: selectedRun.collector_run_id || '-' },
                { key: 'plugin_invocation_log_id', label: '插件调用', children: selectedRun.plugin_invocation_log_id || '-' },
                { key: 'scheduled_job_id', label: '作业 ID', children: selectedRun.scheduled_job_id || '-' },
                { key: 'started_at', label: '开始时间', children: selectedRun.started_at || '-' },
                { key: 'finished_at', label: '结束时间', children: selectedRun.finished_at || '-' },
                { key: 'error_code', label: '错误码', children: selectedRun.error_code || '-' },
                {
                  key: 'error_message',
                  label: '错误信息',
                  children: selectedRun.error_message || '-',
                },
              ]}
            />
            <JsonPreview
              title="数据连接获取内容"
              value={getRunExecutionNode(selectedRun, 'data_connection')}
            />
            <JsonPreview
              title="经过 Skill 处理后的内容"
              value={getRunExecutionNode(selectedRun, 'skill_processing')}
            />
            <JsonPreview
              title="结果动作反馈内容"
              value={getRunExecutionNode(selectedRun, 'result_action')}
            />
            <JsonPreview
              title="代码审查表写入结果"
              value={getRunExecutionNode(selectedRun, 'code_inspection_report')}
            />
            <JsonPreview
              title="严重问题自动创建 Bug"
              value={getRunExecutionNode(selectedRun, 'bug_creation')}
            />
            <JsonPreview
              title="问题消息通知"
              value={getRunExecutionNode(selectedRun, 'notifications')}
            />
            <JsonPreview title="结果摘要" value={selectedRun.result_summary} />
            <JsonPreview title="插件快照" value={selectedRun.resolved_plugin_snapshot} />
            <JsonPreview title="Skill 快照" value={selectedRun.resolved_skill_snapshots} />
            <JsonPreview title="Prompt 快照" value={selectedRun.resolved_prompt_snapshot} />
            <JsonPreview title="作业配置快照" value={selectedRun.config_snapshot} />
          </Space>
        ) : null}
      </Modal>
    </PageContainer>
  );
}
