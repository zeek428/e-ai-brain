import { PlayCircleOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, Switch, message } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  createScheduledJob,
  fetchActiveProductOptions,
  fetchAiAgents,
  fetchAiSkills,
  fetchPluginActions,
  fetchPluginConnections,
  fetchScheduledJobRuns,
  fetchScheduledJobs,
  runScheduledJob,
  type AiAgentRecord,
  type AiSkillRecord,
  type PluginActionRecord,
  type PluginConnectionRecord,
  type ProductFilterOption,
  type ScheduledJobRecord,
  type ScheduledJobRunRecord,
} from '../../services/aiBrain';

type ScheduledJobFormValues = {
  agent_id?: string;
  cron_expression?: string;
  enabled: boolean;
  execution_mode: string;
  interval_seconds?: number;
  job_type: string;
  name: string;
  plugin_action_id?: string;
  plugin_connection_id?: string;
  plugin_input_mapping?: string;
  plugin_output_mapping?: string;
  product_id?: string;
  schedule_type: string;
  skill_ids?: string[];
  source_system: string;
  time_parameter_preset?: string;
};

const jobTypeOptions = [
  'iteration_plan_suggestion_generate',
  'online_log_ai_analysis',
  'user_usage_metric_collect',
  'user_feedback_collect',
  'online_log_metric_collect',
  'dashboard_snapshot_refresh',
  'plugin_action_invoke',
  'user_feedback_insight_extract',
].map((value) => ({ label: value, value }));

const pluginInputTimePresetOptions = [
  { label: '不使用动态时间参数', value: 'none' },
  { label: '当前日期', value: 'current_date' },
  { label: '当前日期 - 7 天', value: 'current_date_minus_7' },
  { label: '上一个完整自然周', value: 'last_full_week' },
  { label: '最近 7 天', value: 'last_7_days' },
  { label: '今天', value: 'today' },
  { label: '昨天', value: 'yesterday' },
];

const pluginInputMappingByTimePreset: Record<string, Record<string, string>> = {
  current_date: {
    end_pt: '{{current_date}}',
  },
  current_date_minus_7: {
    end_pt: '{{current_date}}',
    start_pt: '{{current_date-7}}',
  },
  last_7_days: {
    window_end: '{{last_7_days.end}}',
    window_start: '{{last_7_days.start}}',
  },
  last_full_week: {
    week_end: '{{last_full_week.end}}',
    week_start: '{{last_full_week.start}}',
  },
  today: {
    window_end: '{{today.end}}',
    window_start: '{{today.start}}',
  },
  yesterday: {
    window_end: '{{yesterday.end}}',
    window_start: '{{yesterday.start}}',
  },
};

export default function ScheduledJobsPage() {
  const [form] = Form.useForm<ScheduledJobFormValues>();
  const [jobs, setJobs] = useState<ScheduledJobRecord[]>([]);
  const [runs, setRuns] = useState<ScheduledJobRunRecord[]>([]);
  const [pluginActions, setPluginActions] = useState<PluginActionRecord[]>([]);
  const [pluginConnections, setPluginConnections] = useState<PluginConnectionRecord[]>([]);
  const [products, setProducts] = useState<ProductFilterOption[]>([]);
  const [agents, setAgents] = useState<AiAgentRecord[]>([]);
  const [skills, setSkills] = useState<AiSkillRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const selectedJobType = Form.useWatch('job_type', form);

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
      ] =
        await Promise.all([
          fetchScheduledJobs(),
          fetchScheduledJobRuns(),
          fetchPluginActions(),
          fetchPluginConnections(),
          fetchActiveProductOptions(),
          fetchAiAgents(),
          fetchAiSkills(),
        ]);
      setJobs(nextJobs);
      setRuns(nextRuns);
      setPluginActions(nextPluginActions);
      setPluginConnections(nextPluginConnections);
      setProducts(nextProducts);
      setAgents(nextAgents.filter((agent) => agent.status === 'active'));
      setSkills(nextSkills.filter((skill) => skill.status === 'active'));
    } catch (error) {
      message.error(error instanceof Error ? error.message : '定时作业加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const submitJob = async () => {
    const values = await form.validateFields();
    const { time_parameter_preset: _timeParameterPreset, ...payload } = values;
    await createScheduledJob({
      ...payload,
      plugin_input_mapping: values.plugin_input_mapping
        ? JSON.parse(values.plugin_input_mapping) as Record<string, unknown>
        : {},
      plugin_output_mapping: values.plugin_output_mapping
        ? JSON.parse(values.plugin_output_mapping) as Record<string, unknown>
        : {},
      skill_ids: values.skill_ids ?? [],
    });
    message.success('定时作业已创建');
    setModalOpen(false);
    form.resetFields();
    await reload();
  };

  const triggerJob = async (job: ScheduledJobRecord) => {
    await runScheduledJob(job.id);
    message.success('已触发作业运行');
    await reload();
  };

  const applyTimeParameterPreset = (preset: string) => {
    if (preset === 'none') {
      form.setFieldsValue({ plugin_input_mapping: undefined });
      return;
    }
    form.setFieldsValue({
      plugin_input_mapping: JSON.stringify(pluginInputMappingByTimePreset[preset] ?? {}, null, 2),
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
              <Table<ScheduledJobRecord>
                loading={loading}
                rowKey="id"
                dataSource={jobs}
                tableLayout="fixed"
                title={() => (
                  <Space>
                    <Button aria-label="新增作业" icon={<PlusOutlined />} type="primary" onClick={() => setModalOpen(true)}>
                      新增作业
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={reload}>
                      刷新
                    </Button>
                  </Space>
                )}
                columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true },
                  { dataIndex: 'job_type', title: '类型', ellipsis: true },
                  { dataIndex: 'plugin_action_id', title: '插件动作', ellipsis: true, render: (value) => value || '-' },
                  { dataIndex: 'execution_mode', title: '执行模式', width: 150 },
                  { dataIndex: 'schedule_type', title: '调度', width: 120 },
                  { dataIndex: 'next_run_at', title: '下次运行', ellipsis: true, render: (value) => value || '-' },
                  {
                    dataIndex: 'status',
                    title: '状态',
                    width: 120,
                    render: (value, row) => <Tag color={row.enabled ? 'green' : 'default'}>{String(value ?? '-')}</Tag>,
                  },
                  {
                    key: 'actions',
                    title: '操作',
                    width: 140,
                    render: (_, row) => (
                      <Button icon={<PlayCircleOutlined />} onClick={() => triggerJob(row)}>
                        运行
                      </Button>
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
              <Table<ScheduledJobRunRecord>
                loading={loading}
                rowKey="id"
                dataSource={runs}
                tableLayout="fixed"
                columns={[
                  { dataIndex: 'id', title: '运行 ID', ellipsis: true },
                  { dataIndex: 'scheduled_job_id', title: '作业 ID', ellipsis: true },
                  { dataIndex: 'status', title: '状态', width: 120 },
                  { dataIndex: 'trigger_type', title: '触发方式', width: 120 },
                  { dataIndex: 'collector_run_id', title: '采集运行', ellipsis: true, render: (value) => value || '-' },
                  { dataIndex: 'plugin_invocation_log_id', title: '插件调用', ellipsis: true, render: (value) => value || '-' },
                  { dataIndex: 'records_imported', title: '导入数', width: 100 },
                  { dataIndex: 'error_message', title: '错误', ellipsis: true, render: (value) => value || '-' },
                ]}
              />
            ),
          },
        ]}
      />

      <Modal open={modalOpen} title="新增定时作业" onCancel={() => setModalOpen(false)} onOk={submitJob}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            enabled: true,
            execution_mode: 'deterministic',
            schedule_type: 'manual',
            source_system: 'ai-brain',
          }}
        >
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="作业类型" name="job_type" rules={[{ required: true }]}>
            <Select options={jobTypeOptions} />
          </Form.Item>
          <Space>
            <Form.Item label="启用" name="enabled" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="执行模式" name="execution_mode">
              <Select
                options={[
                  { label: 'deterministic', value: 'deterministic' },
                  { label: 'ai_assisted', value: 'ai_assisted' },
                  { label: 'ai_generated', value: 'ai_generated' },
                ]}
              />
            </Form.Item>
            <Form.Item label="调度方式" name="schedule_type">
              <Select
                options={[
                  { label: 'manual', value: 'manual' },
                  { label: 'cron', value: 'cron' },
                  { label: 'interval', value: 'interval' },
                ]}
              />
            </Form.Item>
          </Space>
          <Form.Item
            label="所属产品"
            name="product_id"
            rules={
              selectedJobType === 'user_feedback_insight_extract'
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
          <Form.Item label="Agent" name="agent_id">
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
          <Form.Item label="Skills" name="skill_ids">
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
          <Form.Item label="插件动作" name="plugin_action_id">
            <Select
              allowClear
              options={pluginActions.map((action) => ({
                label: `${action.name} (${action.code})`,
                value: action.id,
              }))}
            />
          </Form.Item>
          <Form.Item label="插件连接" name="plugin_connection_id">
            <Select
              allowClear
              optionFilterProp="label"
              placeholder="默认使用动作绑定连接"
              showSearch
              options={pluginConnections.map((connection) => ({
                label: `${connection.name} (${connection.environment ?? 'default'})`,
                value: connection.id,
              }))}
            />
          </Form.Item>
          <Form.Item label="时间参数" name="time_parameter_preset">
            <Select
              options={pluginInputTimePresetOptions}
              placeholder="选择后自动生成动态参数"
              onChange={applyTimeParameterPreset}
            />
          </Form.Item>
          <Form.Item label="插件输入映射 JSON" name="plugin_input_mapping">
            <Input.TextArea rows={3} placeholder='{"start_pt":"{{current_date-7}}","end_pt":"{{current_date}}"}' />
          </Form.Item>
          <Form.Item label="插件输出映射 JSON" name="plugin_output_mapping">
            <Input.TextArea rows={3} placeholder='{"records_imported_path":"$.commits"}' />
          </Form.Item>
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
    </PageContainer>
  );
}
