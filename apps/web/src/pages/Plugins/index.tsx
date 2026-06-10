import { ApiOutlined, DeleteOutlined, PlayCircleOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Checkbox, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, Switch, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  createPlugin,
  createPluginAction,
  createPluginConnection,
  fetchPluginActions,
  fetchPluginConnections,
  fetchPluginInvocationLogs,
  fetchPlugins,
  invokePluginAction,
  testPluginConnection,
  type PluginActionRecord,
  type PluginConnectionRecord,
  type PluginInvocationLogRecord,
  type PluginRecord,
} from '../../services/aiBrain';

type PluginFormValues = {
  category: string;
  code: string;
  description?: string;
  name: string;
  protocol: string;
  risk_level: string;
  status: string;
};

type ConnectionFormValues = {
  auth_config?: string;
  auth_type: string;
  endpoint_url: string;
  environment: string;
  header_name?: string;
  max_retries: number;
  name: string;
  password_ref?: string;
  plugin_id: string;
  secret_ref?: string;
  status: string;
  timeout_seconds: number;
  token_ref?: string;
  username_ref?: string;
};

type ActionFormValues = {
  action_type: string;
  code: string;
  connection_id?: string;
  description?: string;
  header_rows?: RequestParameterRow[];
  max_rows?: number;
  method?: string;
  name: string;
  param_rows?: RequestParameterRow[];
  path?: string;
  plugin_id: string;
  request_config?: string;
  requires_human_review: boolean;
  result_mapping?: string;
  returned_fields?: string;
  scenario?: string;
  status: string;
  table_name?: string;
  time_field?: string;
};

type RequestParameterRow = {
  description?: string;
  enabled?: boolean;
  name?: string;
  type?: 'boolean' | 'number' | 'string';
  value?: string;
};

const MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO = 'maxcompute_weekly_feedback';
const MAXCOMPUTE_DEFAULT_FIELDS =
  'feedback_id,user_id,product_id,module_code,feedback_type,content,sentiment,created_at';
const MAXCOMPUTE_DEFAULT_RESULT_MAPPING = {
  insights_path: '$.insights',
  records_imported_path: '$.row_count',
  rows_path: '$.rows',
};

const requestMethodOptions = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((value) => ({
  label: value,
  value,
}));

const requestParameterTypeOptions = [
  { label: 'string', value: 'string' },
  { label: 'number', value: 'number' },
  { label: 'boolean', value: 'boolean' },
];

const systemVariableOptions = [
  { label: '当前日期 YYYYMMDD', value: '{{current_date}}' },
  { label: '当前日期 - 7 天', value: '{{current_date-7}}' },
  { label: '当前日期 ISO', value: '{{date_iso}}' },
  { label: '当前日期 ISO - 7 天', value: '{{date_iso-7}}' },
  { label: '当前时间', value: '{{now}}' },
  { label: '今天开始', value: '{{today.start}}' },
  { label: '今天开始 - 7 天', value: '{{today.start-7}}' },
  { label: '上一完整周开始', value: '{{last_full_week.start}}' },
  { label: '上一完整周结束', value: '{{last_full_week.end}}' },
];

const pluginCategoryOptions = [
  { label: '通用集成', value: 'general' },
  { label: '数据仓库 / BI', value: 'data_warehouse' },
  { label: 'DevOps / 代码平台', value: 'devops' },
  { label: '需求 / 缺陷系统', value: 'issue_tracking' },
  { label: '日志 / 监控', value: 'observability' },
  { label: '知识库 / 文档', value: 'knowledge_base' },
  { label: '协同 / 通知', value: 'collaboration' },
  { label: 'AI / 模型服务', value: 'ai_service' },
  { label: '业务系统', value: 'business_system' },
];

const pluginCategoryLabelByValue = new Map(
  pluginCategoryOptions.map((option) => [option.value, option.label]),
);

const connectionEnvironmentOptions = [
  { label: '默认', value: 'default' },
  { label: '开发', value: 'dev' },
  { label: '测试', value: 'test' },
  { label: '预发 / Staging', value: 'staging' },
  { label: '生产', value: 'prod' },
  { label: '沙箱', value: 'sandbox' },
];

const connectionEnvironmentLabelByValue = new Map(
  connectionEnvironmentOptions.map((option) => [option.value, option.label]),
);

function stableJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function buildMaxComputeRequestConfig(values: Partial<ActionFormValues>): Record<string, unknown> {
  const table = values.table_name?.trim() || 'ods_user_feedback';
  const timeField = values.time_field?.trim() || 'created_at';
  const fields = (values.returned_fields || MAXCOMPUTE_DEFAULT_FIELDS)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
  const limit = values.max_rows && values.max_rows > 0 ? values.max_rows : 1000;
  return {
    fields,
    limit,
    sql_template: `SELECT ${fields.join(', ')} FROM ${table} WHERE ${timeField} >= '\${week_start}' AND ${timeField} < '\${week_end}' LIMIT ${limit}`,
    table,
    time_field: timeField,
    tool_name: 'maxcompute.execute_sql',
  };
}

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

function buildVisualRequestConfig(values: Partial<ActionFormValues>): Record<string, unknown> {
  const config: Record<string, unknown> = {};
  const method = values.method || 'GET';
  const path = values.path?.trim();
  const query = rowsToRecord(values.param_rows);
  const headers = rowsToRecord(values.header_rows);
  config.method = method;
  if (path) {
    config.path = path;
  }
  if (Object.keys(query).length > 0) {
    config.query = query;
  }
  if (Object.keys(headers).length > 0) {
    config.headers = headers;
  }
  return config;
}

function buildConnectionAuthConfig(values: Partial<ConnectionFormValues>): Record<string, unknown> {
  if (values.auth_type === 'bearer') {
    return values.token_ref?.trim() ? { token_ref: values.token_ref.trim() } : {};
  }
  if (values.auth_type === 'api_key_header') {
    return {
      header_name: values.header_name?.trim() || 'X-API-Key',
      ...(values.secret_ref?.trim() ? { secret_ref: values.secret_ref.trim() } : {}),
    };
  }
  if (values.auth_type === 'basic') {
    return {
      ...(values.username_ref?.trim() ? { username_ref: values.username_ref.trim() } : {}),
      ...(values.password_ref?.trim() ? { password_ref: values.password_ref.trim() } : {}),
    };
  }
  return {};
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

function RequestParameterRows({
  addText,
  name,
  namePlaceholder,
  title,
  valuePlaceholder,
}: {
  addText: string;
  name: 'header_rows' | 'param_rows';
  namePlaceholder: string;
  title: string;
  valuePlaceholder: string;
}) {
  const form = Form.useFormInstance<ActionFormValues>();
  return (
    <Form.List name={name}>
      {(fields, { add, remove }) => (
        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
          <div style={{ color: '#53627a', fontWeight: 600 }}>{title}</div>
          <Space orientation="vertical" size={6} style={{ width: '100%' }}>
            {fields.map((field) => (
              <Space key={field.key} align="baseline" wrap>
                <Form.Item
                  name={[field.name, 'enabled']}
                  valuePropName="checked"
                  initialValue
                  style={{ marginBottom: 0 }}
                >
                  <Checkbox />
                </Form.Item>
                <Form.Item name={[field.name, 'name']} style={{ marginBottom: 0 }}>
                  <Input placeholder={namePlaceholder} style={{ width: 180 }} />
                </Form.Item>
                <Form.Item name={[field.name, 'value']} style={{ marginBottom: 0 }}>
                  <Input placeholder={valuePlaceholder} style={{ width: 260 }} />
                </Form.Item>
                <Select
                  allowClear
                  options={systemVariableOptions}
                  placeholder="系统变量"
                  style={{ width: 190 }}
                  onChange={(value) => {
                    if (value) {
                      form.setFieldValue([name, field.name, 'value'], value);
                    }
                  }}
                />
                <Form.Item name={[field.name, 'type']} initialValue="string" style={{ marginBottom: 0 }}>
                  <Select options={requestParameterTypeOptions} style={{ width: 120 }} />
                </Form.Item>
                <Form.Item name={[field.name, 'description']} style={{ marginBottom: 0 }}>
                  <Input placeholder="说明" style={{ width: 180 }} />
                </Form.Item>
                <Button aria-label="删除参数" icon={<DeleteOutlined />} onClick={() => remove(field.name)} />
              </Space>
            ))}
          </Space>
          <Button
            icon={<PlusOutlined />}
            onClick={() => add({ enabled: true, type: 'string' })}
            type="dashed"
          >
            {addText}
          </Button>
        </Space>
      )}
    </Form.List>
  );
}

export default function PluginsPage() {
  const [pluginForm] = Form.useForm<PluginFormValues>();
  const [connectionForm] = Form.useForm<ConnectionFormValues>();
  const [actionForm] = Form.useForm<ActionFormValues>();
  const [plugins, setPlugins] = useState<PluginRecord[]>([]);
  const [connections, setConnections] = useState<PluginConnectionRecord[]>([]);
  const [actions, setActions] = useState<PluginActionRecord[]>([]);
  const [logs, setLogs] = useState<PluginInvocationLogRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [pluginModalOpen, setPluginModalOpen] = useState(false);
  const [connectionModalOpen, setConnectionModalOpen] = useState(false);
  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [actionScenario, setActionScenario] = useState<string | undefined>();
  const [advancedConnectionJsonOpen, setAdvancedConnectionJsonOpen] = useState(false);
  const [advancedActionJsonOpen, setAdvancedActionJsonOpen] = useState(false);
  const selectedConnectionAuthType = Form.useWatch('auth_type', connectionForm);

  const pluginOptions = useMemo(
    () => plugins.map((plugin) => ({ label: `${plugin.name} (${plugin.protocol})`, value: plugin.id })),
    [plugins],
  );
  const connectionOptions = useMemo(
    () =>
      connections.map((connection) => ({
        label: `${connection.name} (${connection.environment ?? 'default'})`,
        value: connection.id,
      })),
    [connections],
  );

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [nextPlugins, nextConnections, nextActions, nextLogs] = await Promise.all([
        fetchPlugins(),
        fetchPluginConnections(),
        fetchPluginActions(),
        fetchPluginInvocationLogs(),
      ]);
      setPlugins(nextPlugins);
      setConnections(nextConnections);
      setActions(nextActions);
      setLogs(nextLogs);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '插件配置加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const submitPlugin = async () => {
    const values = await pluginForm.validateFields();
    await createPlugin(values);
    message.success('插件已创建');
    setPluginModalOpen(false);
    pluginForm.resetFields();
    await reload();
  };

  const submitConnection = async () => {
    try {
      const values = await connectionForm.validateFields();
      await createPluginConnection({
        ...values,
        auth_config: advancedConnectionJsonOpen
          ? parseJsonObject(values.auth_config, '认证配置')
          : buildConnectionAuthConfig(values),
      });
      message.success('连接已创建');
      setConnectionModalOpen(false);
      setAdvancedConnectionJsonOpen(false);
      connectionForm.resetFields();
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '连接创建失败');
    }
  };

  const submitAction = async () => {
    try {
      const values = await actionForm.validateFields();
      const requestConfig =
        values.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO && !advancedActionJsonOpen
          ? buildMaxComputeRequestConfig(values)
          : advancedActionJsonOpen
            ? parseJsonObject(values.request_config, '请求配置')
            : buildVisualRequestConfig(values);
      const resultMapping =
        values.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO && !values.result_mapping?.trim()
          ? MAXCOMPUTE_DEFAULT_RESULT_MAPPING
          : parseJsonObject(values.result_mapping, '结果映射');
      await createPluginAction({
        action_type: values.action_type,
        code: values.code,
        connection_id: values.connection_id,
        description: values.description,
        name: values.name,
        plugin_id: values.plugin_id,
        request_config: requestConfig,
        requires_human_review: values.requires_human_review,
        result_mapping: resultMapping,
        status: values.status,
      });
      message.success('动作已创建');
      setActionModalOpen(false);
      setActionScenario(undefined);
      setAdvancedActionJsonOpen(false);
      actionForm.resetFields();
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '动作创建失败');
    }
  };

  const openActionModal = () => {
    setActionScenario(undefined);
    setAdvancedActionJsonOpen(false);
    setActionModalOpen(true);
  };

  const applyActionScenario = (scenario?: string) => {
    setActionScenario(scenario);
    if (scenario !== MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO) {
      return;
    }
    const nextValues: Partial<ActionFormValues> = {
      action_type: 'mcp_tool',
      code: 'fetch_weekly_user_feedback',
      connection_id: connections.length === 1 ? connections[0].id : undefined,
      max_rows: 1000,
      name: '获取本周用户反馈数据',
      plugin_id: plugins.length === 1 ? plugins[0].id : undefined,
      request_config: stableJson(
        buildMaxComputeRequestConfig({
          max_rows: 1000,
          returned_fields: MAXCOMPUTE_DEFAULT_FIELDS,
          table_name: 'ods_user_feedback',
          time_field: 'created_at',
        }),
      ),
      result_mapping: stableJson(MAXCOMPUTE_DEFAULT_RESULT_MAPPING),
      returned_fields: MAXCOMPUTE_DEFAULT_FIELDS,
      table_name: 'ods_user_feedback',
      time_field: 'created_at',
    };
    actionForm.setFieldsValue(nextValues);
  };

  const toggleAdvancedActionJson = () => {
    const nextOpen = !advancedActionJsonOpen;
    if (nextOpen) {
      const values = actionForm.getFieldsValue();
      const requestConfig =
        values.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO
          ? buildMaxComputeRequestConfig(values)
          : buildVisualRequestConfig(values);
      actionForm.setFieldsValue({
        request_config: values.request_config?.trim()
          ? values.request_config
          : stableJson(requestConfig),
        result_mapping: values.result_mapping?.trim()
          ? values.result_mapping
          : values.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO
            ? stableJson(MAXCOMPUTE_DEFAULT_RESULT_MAPPING)
            : stableJson({}),
      });
    }
    setAdvancedActionJsonOpen(nextOpen);
  };

  const toggleAdvancedConnectionJson = () => {
    const nextOpen = !advancedConnectionJsonOpen;
    if (nextOpen) {
      const values = connectionForm.getFieldsValue();
      connectionForm.setFieldsValue({
        auth_config: values.auth_config?.trim()
          ? values.auth_config
          : stableJson(buildConnectionAuthConfig(values)),
      });
    }
    setAdvancedConnectionJsonOpen(nextOpen);
  };

  const runAction = async (action: PluginActionRecord) => {
    await invokePluginAction(action.id);
    message.success('插件动作已执行');
    await reload();
  };

  const runConnectionTest = async (connection: PluginConnectionRecord) => {
    const result = await testPluginConnection(connection.id);
    if (result.status === 'succeeded') {
      message.success(`连接测试成功，耗时 ${result.latency_ms}ms`);
    } else {
      message.error(result.error_message || '连接测试失败');
    }
  };

  return (
    <PageContainer title="插件管理">
      <Tabs
        items={[
          {
            key: 'plugins',
            label: '插件',
            children: (
              <Table<PluginRecord>
                loading={loading}
                rowKey="id"
                dataSource={plugins}
                tableLayout="fixed"
                title={() => (
                  <Space>
                    <Button aria-label="新增插件" icon={<PlusOutlined />} type="primary" onClick={() => setPluginModalOpen(true)}>
                      新增插件
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={reload}>
                      刷新
                    </Button>
                  </Space>
                )}
                columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true },
                  { dataIndex: 'code', title: '编码', ellipsis: true },
                  { dataIndex: 'protocol', title: '协议', width: 120 },
                  {
                    dataIndex: 'category',
                    title: '分类',
                    width: 150,
                    render: (value) => pluginCategoryLabelByValue.get(String(value)) ?? String(value ?? '-'),
                  },
                  { dataIndex: 'risk_level', title: '风险', width: 100 },
                  {
                    dataIndex: 'status',
                    title: '状态',
                    width: 110,
                    render: (value) => <Tag color={value === 'active' ? 'green' : 'default'}>{String(value)}</Tag>,
                  },
                ]}
              />
            ),
          },
          {
            key: 'connections',
            label: '连接',
            children: (
              <Table<PluginConnectionRecord>
                loading={loading}
                rowKey="id"
                dataSource={connections}
                tableLayout="fixed"
                title={() => (
                  <Space>
                    <Button aria-label="新增连接" icon={<PlusOutlined />} type="primary" onClick={() => setConnectionModalOpen(true)}>
                      新增连接
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={reload}>
                      刷新
                    </Button>
                  </Space>
                )}
                columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true },
                  { dataIndex: 'plugin_id', title: '插件 ID', ellipsis: true },
                  {
                    dataIndex: 'environment',
                    title: '环境',
                    width: 130,
                    render: (value) => connectionEnvironmentLabelByValue.get(String(value)) ?? String(value ?? '-'),
                  },
                  { dataIndex: 'auth_type', title: '认证', width: 130 },
                  { dataIndex: 'endpoint_url', title: 'Endpoint', ellipsis: true },
                  { dataIndex: 'status', title: '状态', width: 110 },
                  {
                    key: 'actions',
                    title: '操作',
                    width: 120,
                    render: (_, row) => (
                      <Button aria-label="测试" icon={<PlayCircleOutlined />} onClick={() => runConnectionTest(row)}>
                        测试
                      </Button>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'actions',
            label: '动作',
            children: (
              <Table<PluginActionRecord>
                loading={loading}
                rowKey="id"
                dataSource={actions}
                tableLayout="fixed"
                title={() => (
                  <Space>
                    <Button aria-label="新增动作" icon={<PlusOutlined />} type="primary" onClick={openActionModal}>
                      新增动作
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={reload}>
                      刷新
                    </Button>
                  </Space>
                )}
                columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true },
                  { dataIndex: 'code', title: '编码', ellipsis: true },
                  { dataIndex: 'action_type', title: '类型', width: 130 },
                  { dataIndex: 'plugin_id', title: '插件 ID', ellipsis: true },
                  { dataIndex: 'connection_id', title: '连接 ID', ellipsis: true },
                  { dataIndex: 'status', title: '状态', width: 100 },
                  {
                    key: 'actions',
                    title: '操作',
                    width: 130,
                    render: (_, row) => (
                      <Button icon={<PlayCircleOutlined />} onClick={() => runAction(row)}>
                        运行
                      </Button>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'logs',
            label: '调用日志',
            children: (
              <Table<PluginInvocationLogRecord>
                loading={loading}
                rowKey="id"
                dataSource={logs}
                tableLayout="fixed"
                columns={[
                  { dataIndex: 'id', title: '日志 ID', ellipsis: true },
                  { dataIndex: 'action_id', title: '动作 ID', ellipsis: true },
                  { dataIndex: 'scheduled_job_id', title: '定时作业', ellipsis: true, render: (value) => value || '-' },
                  { dataIndex: 'status', title: '状态', width: 110 },
                  { dataIndex: 'latency_ms', title: '耗时 ms', width: 110 },
                  { dataIndex: 'error_message', title: '错误', ellipsis: true, render: (value) => value || '-' },
                ]}
              />
            ),
          },
        ]}
      />

      <Modal open={pluginModalOpen} title="新增插件" onCancel={() => setPluginModalOpen(false)} onOk={submitPlugin}>
        <Form
          form={pluginForm}
          layout="vertical"
          initialValues={{ category: 'general', protocol: 'http', risk_level: 'medium', status: 'active' }}
        >
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input prefix={<ApiOutlined />} />
          </Form.Item>
          <Form.Item label="编码" name="code" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="协议" name="protocol">
            <Select
              options={[
                { label: 'HTTP', value: 'http' },
                { label: 'MCP HTTP', value: 'mcp_http' },
                { label: 'MCP Stdio', value: 'mcp_stdio' },
              ]}
            />
          </Form.Item>
          <Form.Item label="分类" name="category" rules={[{ required: true, message: '请选择插件分类' }]}>
            <Select options={pluginCategoryOptions} />
          </Form.Item>
          <Form.Item label="风险等级" name="risk_level">
            <Select
              options={[
                { label: 'low', value: 'low' },
                { label: 'medium', value: 'medium' },
                { label: 'high', value: 'high' },
              ]}
            />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select
              options={[
                { label: 'active', value: 'active' },
                { label: 'draft', value: 'draft' },
                { label: 'disabled', value: 'disabled' },
              ]}
            />
          </Form.Item>
          <Form.Item label="说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={connectionModalOpen}
        title="新增连接"
        onCancel={() => {
          setConnectionModalOpen(false);
          setAdvancedConnectionJsonOpen(false);
        }}
        onOk={submitConnection}
      >
        <Form
          form={connectionForm}
          layout="vertical"
          initialValues={{ auth_type: 'none', environment: 'default', max_retries: 0, status: 'active', timeout_seconds: 30 }}
        >
          <Form.Item label="插件" name="plugin_id" rules={[{ required: true }]}>
            <Select options={pluginOptions} />
          </Form.Item>
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Endpoint URL" name="endpoint_url" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Space>
            <Form.Item label="环境" name="environment">
              <Select options={connectionEnvironmentOptions} />
            </Form.Item>
            <Form.Item label="认证" name="auth_type">
              <Select
                options={[
                  { label: 'none', value: 'none' },
                  { label: 'bearer', value: 'bearer' },
                  { label: 'api_key_header', value: 'api_key_header' },
                  { label: 'basic', value: 'basic' },
                ]}
              />
            </Form.Item>
          </Space>
          {!advancedConnectionJsonOpen && selectedConnectionAuthType === 'api_key_header' ? (
            <Space wrap>
              <Form.Item label="Header 名" name="header_name">
                <Input placeholder="Authorization" />
              </Form.Item>
              <Form.Item label="Header 值/密钥引用" name="secret_ref">
                <Input placeholder="vault/path/to/token 或 APPCODE xxx" style={{ width: 320 }} />
              </Form.Item>
            </Space>
          ) : null}
          {!advancedConnectionJsonOpen && selectedConnectionAuthType === 'bearer' ? (
            <Form.Item label="Token 引用" name="token_ref">
              <Input placeholder="vault/path/to/token" />
            </Form.Item>
          ) : null}
          {!advancedConnectionJsonOpen && selectedConnectionAuthType === 'basic' ? (
            <Space wrap>
              <Form.Item label="用户名引用" name="username_ref">
                <Input placeholder="vault/path/to/username" />
              </Form.Item>
              <Form.Item label="密码引用" name="password_ref">
                <Input placeholder="vault/path/to/password" />
              </Form.Item>
            </Space>
          ) : null}
          <Button type="link" onClick={toggleAdvancedConnectionJson}>
            高级认证 JSON 修改
          </Button>
          {advancedConnectionJsonOpen ? (
            <Form.Item label="认证配置 JSON" name="auth_config">
              <Input.TextArea rows={4} placeholder='{"header_name":"PRIVATE-TOKEN","secret_ref":"vault/gitlab/token"}' />
            </Form.Item>
          ) : null}
          <Space>
            <Form.Item label="超时秒数" name="timeout_seconds">
              <InputNumber min={1} />
            </Form.Item>
            <Form.Item label="重试次数" name="max_retries">
              <InputNumber min={0} />
            </Form.Item>
            <Form.Item label="状态" name="status">
              <Select
                options={[
                  { label: 'active', value: 'active' },
                  { label: 'draft', value: 'draft' },
                  { label: 'disabled', value: 'disabled' },
                ]}
              />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      <Modal
        cancelText="取消"
        okText="确定"
        open={actionModalOpen}
        title="新增动作"
        onCancel={() => {
          setActionModalOpen(false);
          setActionScenario(undefined);
          setAdvancedActionJsonOpen(false);
        }}
        onOk={submitAction}
      >
        <Form
          form={actionForm}
          layout="vertical"
          initialValues={{
            action_type: 'http_request',
            method: 'GET',
            requires_human_review: false,
            status: 'active',
          }}
        >
          <Form.Item label="配置场景" name="scenario">
            <Select
              allowClear
              onChange={applyActionScenario}
              options={[{ label: 'MaxCompute 每周用户反馈', value: MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO }]}
            />
          </Form.Item>
          <Form.Item label="插件" name="plugin_id" rules={[{ required: true }]}>
            <Select options={pluginOptions} />
          </Form.Item>
          <Form.Item label="连接" name="connection_id">
            <Select allowClear options={connectionOptions} />
          </Form.Item>
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="编码" name="code" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Space>
            <Form.Item label="动作类型" name="action_type">
              <Select
                options={[
                  { label: 'http_request', value: 'http_request' },
                  { label: 'mcp_tool', value: 'mcp_tool' },
                ]}
              />
            </Form.Item>
            <Form.Item label="人工确认" name="requires_human_review" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="状态" name="status">
              <Select
                options={[
                  { label: 'active', value: 'active' },
                  { label: 'draft', value: 'draft' },
                  { label: 'disabled', value: 'disabled' },
                ]}
              />
            </Form.Item>
          </Space>
          {actionScenario !== MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO ? (
            <>
              <Space wrap>
                <Form.Item label="请求方法" name="method">
                  <Select options={requestMethodOptions} style={{ width: 140 }} />
                </Form.Item>
                <Form.Item label="请求路径" name="path">
                  <Input placeholder="/api/path" style={{ width: 320 }} />
                </Form.Item>
              </Space>
              <RequestParameterRows
                addText="添加 Params"
                name="param_rows"
                namePlaceholder="参数名"
                title="Params"
                valuePlaceholder="参数值"
              />
              <RequestParameterRows
                addText="添加 Headers"
                name="header_rows"
                namePlaceholder="Header 名"
                title="Headers"
                valuePlaceholder="Header 值"
              />
            </>
          ) : null}
          {actionScenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO ? (
            <>
              <Form.Item label="表名" name="table_name">
                <Input />
              </Form.Item>
              <Space wrap>
                <Form.Item label="时间字段" name="time_field">
                  <Input />
                </Form.Item>
                <Form.Item label="最大行数" name="max_rows">
                  <InputNumber min={1} style={{ width: 160 }} />
                </Form.Item>
              </Space>
              <Form.Item label="返回字段" name="returned_fields">
                <Input />
              </Form.Item>
            </>
          ) : null}
          <Button type="link" onClick={toggleAdvancedActionJson}>
            高级 JSON 修改
          </Button>
          {advancedActionJsonOpen ? (
            <>
              <Form.Item label="请求配置 JSON" name="request_config">
                <Input.TextArea rows={5} placeholder='{"method":"GET","path":"/api/v4/projects/1/metrics"}' />
              </Form.Item>
              <Form.Item label="结果映射 JSON" name="result_mapping">
                <Input.TextArea rows={3} placeholder='{"records_imported_path":"$.commits"}' />
              </Form.Item>
            </>
          ) : null}
          <Form.Item label="说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
}
