import { PlayCircleOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Checkbox, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, Switch, Typography, message } from 'antd';
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
  plugin_input_rows?: RequestParameterRow[];
  plugin_output_mapping?: string;
  product_id?: string;
  schedule_type: string;
  skill_ids?: string[];
  source_system: string;
  time_parameter_preset?: string;
};

type RequestParameterRow = {
  description?: string;
  enabled?: boolean;
  name?: string;
  type?: 'boolean' | 'number' | 'string';
  value?: string;
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

const requestParameterTypeOptions = [
  { label: 'string', value: 'string' },
  { label: 'number', value: 'number' },
  { label: 'boolean', value: 'boolean' },
];

const systemVariableOptions = [
  { label: '当前日期 YYYYMMDD', value: '{{current_date}}' },
  { label: '当前日期 - 7 天', value: '{{current_date-7}}' },
  { label: '当前时间', value: '{{now}}' },
  { label: '上一完整周开始', value: '{{last_full_week.start}}' },
  { label: '上一完整周结束', value: '{{last_full_week.end}}' },
  { label: '最近 7 天开始', value: '{{last_7_days.start}}' },
  { label: '最近 7 天结束', value: '{{last_7_days.end}}' },
];

function parseParameterValue(row: RequestParameterRow): unknown {
  const value = row.value ?? '';
  if (row.type === 'number') {
    const numericValue = Number(value);
    return Number.isFinite(numericValue) ? numericValue : value;
  }
  if (row.type === 'boolean') {
    return value === 'true' || value === '1' || value === '是';
  }
  return value;
}

function rowsToRecord(rows: RequestParameterRow[] | undefined): Record<string, unknown> {
  return (rows ?? []).reduce<Record<string, unknown>>((result, row) => {
    const name = row.name?.trim();
    if (row.enabled === false || !name) {
      return result;
    }
    result[name] = parseParameterValue(row);
    return result;
  }, {});
}

function recordToRows(record: Record<string, unknown>): RequestParameterRow[] {
  return Object.entries(record).map(([name, value]) => ({
    enabled: true,
    name,
    type: typeof value === 'number' ? 'number' : typeof value === 'boolean' ? 'boolean' : 'string',
    value: typeof value === 'string' ? value : String(value),
  }));
}

function parseJsonObject(value: string | undefined, field: string): Record<string, unknown> {
  if (!value?.trim()) {
    return {};
  }
  try {
    const parsed = JSON.parse(value) as unknown;
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    // fall through to a consistent validation message
  }
  throw new Error(`${field} 必须是 JSON 对象`);
}

function stableJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function PluginInputRows() {
  const form = Form.useFormInstance<ScheduledJobFormValues>();
  return (
    <Form.List name="plugin_input_rows">
      {(fields, { add, remove }) => (
        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
          <Typography.Text strong>插件输入映射</Typography.Text>
          {fields.map((field) => (
            <Space key={field.key} align="baseline" wrap>
              <Form.Item name={[field.name, 'enabled']} valuePropName="checked" initialValue style={{ marginBottom: 0 }}>
                <Checkbox />
              </Form.Item>
              <Form.Item name={[field.name, 'name']} style={{ marginBottom: 0 }}>
                <Input placeholder="参数名，如 start_pt" style={{ width: 180 }} />
              </Form.Item>
              <Form.Item name={[field.name, 'value']} style={{ marginBottom: 0 }}>
                <Input placeholder="参数值，如 {{current_date-7}}" style={{ width: 260 }} />
              </Form.Item>
              <Select
                allowClear
                options={systemVariableOptions}
                placeholder="系统变量"
                style={{ width: 190 }}
                onChange={(value) => {
                  if (value) {
                    form.setFieldValue(['plugin_input_rows', field.name, 'value'], value);
                  }
                }}
              />
              <Form.Item name={[field.name, 'type']} initialValue="string" style={{ marginBottom: 0 }}>
                <Select options={requestParameterTypeOptions} style={{ width: 120 }} />
              </Form.Item>
              <Form.Item name={[field.name, 'description']} style={{ marginBottom: 0 }}>
                <Input placeholder="说明" style={{ width: 180 }} />
              </Form.Item>
              <Button aria-label="删除输入参数" onClick={() => remove(field.name)}>
                删除
              </Button>
            </Space>
          ))}
          <Button icon={<PlusOutlined />} onClick={() => add({ enabled: true, type: 'string' })} type="dashed">
            添加输入参数
          </Button>
        </Space>
      )}
    </Form.List>
  );
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
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [advancedPluginInputJsonOpen, setAdvancedPluginInputJsonOpen] = useState(false);
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
    const {
      plugin_input_rows: _pluginInputRows,
      time_parameter_preset: _timeParameterPreset,
      ...payload
    } = values;
    await createScheduledJob({
      ...payload,
      plugin_input_mapping: advancedPluginInputJsonOpen
        ? parseJsonObject(values.plugin_input_mapping, '插件输入映射')
        : rowsToRecord(values.plugin_input_rows),
      plugin_output_mapping: values.plugin_output_mapping
        ? parseJsonObject(values.plugin_output_mapping, '插件输出映射')
        : {},
      skill_ids: values.skill_ids ?? [],
    });
    message.success('定时作业已创建');
    setModalOpen(false);
    setAdvancedPluginInputJsonOpen(false);
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
      form.setFieldsValue({ plugin_input_mapping: undefined, plugin_input_rows: [] });
      return;
    }
    const nextMapping = pluginInputMappingByTimePreset[preset] ?? {};
    form.setFieldsValue({
      plugin_input_mapping: stableJson(nextMapping),
      plugin_input_rows: recordToRows(nextMapping),
    });
  };

  const syncPluginInputJsonFromRows = () => {
    form.setFieldValue('plugin_input_mapping', stableJson(rowsToRecord(form.getFieldValue('plugin_input_rows'))));
  };

  const applyPluginInputJsonToRows = () => {
    try {
      const mapping = parseJsonObject(form.getFieldValue('plugin_input_mapping'), '插件输入映射');
      form.setFieldValue('plugin_input_rows', recordToRows(mapping));
      message.success('已从 JSON 同步到输入映射表格');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'JSON 解析失败');
    }
  };

  const toggleAdvancedPluginInputJson = () => {
    const nextOpen = !advancedPluginInputJsonOpen;
    if (nextOpen) {
      syncPluginInputJsonFromRows();
    }
    setAdvancedPluginInputJsonOpen(nextOpen);
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

      <Modal
        open={modalOpen}
        title="新增定时作业"
        onCancel={() => {
          setModalOpen(false);
          setAdvancedPluginInputJsonOpen(false);
        }}
        onOk={submitJob}
      >
        <Form
          form={form}
          layout="vertical"
          onValuesChange={(changedValues) => {
            if (
              advancedPluginInputJsonOpen
              && Object.prototype.hasOwnProperty.call(changedValues, 'plugin_input_rows')
            ) {
              syncPluginInputJsonFromRows();
            }
          }}
          initialValues={{
            enabled: true,
            execution_mode: 'deterministic',
            plugin_input_rows: [],
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
          <PluginInputRows />
          <Button type="link" onClick={toggleAdvancedPluginInputJson}>
            高级输入映射 JSON 修改
          </Button>
          {advancedPluginInputJsonOpen ? (
            <>
              <Space style={{ marginBottom: 8 }}>
                <Button onClick={syncPluginInputJsonFromRows}>同步表格到 JSON</Button>
                <Button onClick={applyPluginInputJsonToRows}>从 JSON 应用到表格</Button>
              </Space>
              <Form.Item label="插件输入映射 JSON" name="plugin_input_mapping">
                <Input.TextArea rows={3} placeholder='{"start_pt":"{{current_date-7}}","end_pt":"{{current_date}}"}' />
              </Form.Item>
            </>
          ) : null}
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
