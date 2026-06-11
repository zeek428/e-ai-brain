import { ApiOutlined, DeleteOutlined, EditOutlined, PlayCircleOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Alert, Button, Checkbox, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, Switch, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  createPlugin,
  createPluginAction,
  createPluginConnection,
  deletePlugin,
  deletePluginAction,
  deletePluginConnection,
  fetchPluginActions,
  fetchPluginConnections,
  fetchPluginInvocationLogs,
  fetchPluginSystemVariables,
  fetchPlugins,
  fetchScheduledJobs,
  invokePluginAction,
  testPluginConnection,
  trialPluginAction,
  updatePlugin,
  updatePluginAction,
  updatePluginConnection,
  type PluginActionTrialResult,
  type PluginActionRecord,
  type PluginConnectionRecord,
  type PluginInvocationLogRecord,
  type PluginRecord,
  type PluginSystemVariableRecord,
  type ScheduledJobRecord,
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
  connection_header_rows?: RequestParameterRow[];
  connection_param_rows?: RequestParameterRow[];
  endpoint_url: string;
  environment: string;
  header_name?: string;
  max_retries: number;
  name: string;
  password_ref?: string;
  plugin_id: string;
  request_config?: string;
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
  insights_path?: string;
  max_rows?: number;
  method?: string;
  name: string;
  param_rows?: RequestParameterRow[];
  path?: string;
  plugin_id: string;
  request_config?: string;
  requires_human_review: boolean;
  records_imported_path?: string;
  result_mapping?: string;
  rows_path?: string;
  returned_fields?: string;
  scenario?: string;
  status: string;
  table_name?: string;
  time_field?: string;
  write_target?: string;
};

type RequestParameterRow = {
  description?: string;
  enabled?: boolean;
  name?: string;
  type?: 'boolean' | 'number' | 'string';
  value?: string;
};

type DeleteUsageGroup = {
  items: string[];
  label: string;
};

const MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO = 'maxcompute_weekly_feedback';
const MAXCOMPUTE_DEFAULT_FIELDS =
  'feedback_id,user_id,product_id,module_code,feedback_type,content,sentiment,created_at';
const MAXCOMPUTE_DEFAULT_RESULT_MAPPING = {
  insights_path: '$.insights',
  records_imported_path: '$.row_count',
  rows_path: '$.rows',
  write_target: 'user_feedback_insights',
};
const SCHEDULED_JOB_RESULT_DEFAULT_MAPPING = {
  write_target: 'scheduled_job_result',
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

const resultWriteTargetOptions = [
  { label: '仅保存运行结果', value: 'scheduled_job_result' },
  { label: '用户洞察表', value: 'user_feedback_insights' },
];

const resultWriteTargetLabelByValue = new Map(
  resultWriteTargetOptions.map((option) => [option.value, option.label]),
);

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

function usageItemName(item: { code?: string; id?: string; name?: string | null }) {
  return item.name || item.code || item.id || '-';
}

function hasDeleteUsage(groups: DeleteUsageGroup[]) {
  return groups.some((group) => group.items.length > 0);
}

function deleteUsageContent(groups: DeleteUsageGroup[]) {
  return (
    <Space orientation="vertical" size={8}>
      <Typography.Text>当前对象正在被使用，不能删除。请先解除下面的引用，或将其停用。</Typography.Text>
      {groups.filter((group) => group.items.length > 0).map((group) => (
        <div key={group.label}>
          <Typography.Text strong>{group.label}：</Typography.Text>
          <Typography.Text>{group.items.slice(0, 5).join('、')}</Typography.Text>
          {group.items.length > 5 ? <Typography.Text type="secondary"> 等 {group.items.length} 个</Typography.Text> : null}
        </div>
      ))}
    </Space>
  );
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

function recordToRows(record: unknown): RequestParameterRow[] {
  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    return [];
  }
  return Object.entries(record as Record<string, unknown>).map(([name, value]) => ({
    enabled: true,
    name,
    type: typeof value === 'number' ? 'number' : typeof value === 'boolean' ? 'boolean' : 'string',
    value: typeof value === 'string' ? value : String(value),
  }));
}

function configSection(config: Record<string, unknown> | undefined, key: string): unknown {
  const section = config?.[key];
  return section && typeof section === 'object' && !Array.isArray(section) ? section : undefined;
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

function buildActionRequestPreview(
  values: Partial<ActionFormValues> | undefined,
  connection?: PluginConnectionRecord,
): Record<string, unknown> {
  const formValues = values ?? {};
  const config =
    formValues.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO
      ? buildMaxComputeRequestConfig(formValues)
      : buildVisualRequestConfig(formValues);
  const method = String(config.method ?? 'POST').toUpperCase();
  const connectionRequestConfig = connection?.request_config ?? {};
  const connectionQuery =
    connectionRequestConfig.query && typeof connectionRequestConfig.query === 'object'
      ? connectionRequestConfig.query
      : {};
  const actionQuery = config.query && typeof config.query === 'object' ? config.query : {};
  const query = { ...(connectionQuery as Record<string, unknown>), ...(actionQuery as Record<string, unknown>) };
  const connectionHeaders =
    connectionRequestConfig.headers && typeof connectionRequestConfig.headers === 'object'
      ? connectionRequestConfig.headers
      : {};
  const actionHeaders = config.headers && typeof config.headers === 'object' ? config.headers : {};
  const headers = { ...(connectionHeaders as Record<string, unknown>), ...(actionHeaders as Record<string, unknown>) };
  const path = String(config.path ?? '');
  const baseUrl = connection?.endpoint_url?.replace(/\/$/, '') ?? '';
  const queryString = new URLSearchParams(query as Record<string, string>).toString();
  return {
    endpoint: connection?.endpoint_url ?? '-',
    headers,
    method,
    path: path || (config.tool_name ? '(MCP tools/call)' : ''),
    query,
    tool_name: config.tool_name,
    url: path
      ? `${baseUrl}/${path.replace(/^\//, '')}${queryString ? `?${queryString}` : ''}`
      : `${baseUrl}${queryString ? `?${queryString}` : ''}`,
  };
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

function buildConnectionRequestConfig(values: Partial<ConnectionFormValues>): Record<string, unknown> {
  const config: Record<string, unknown> = {};
  const query = rowsToRecord(values.connection_param_rows);
  const headers = rowsToRecord(values.connection_header_rows);
  if (Object.keys(query).length > 0) {
    config.query = query;
  }
  if (Object.keys(headers).length > 0) {
    config.headers = headers;
  }
  return config;
}

function buildConnectionPayload(
  values: ConnectionFormValues,
  authConfig: Record<string, unknown>,
  requestConfig: Record<string, unknown>,
): Partial<PluginConnectionRecord> {
  return {
    auth_config: authConfig,
    auth_type: values.auth_type,
    endpoint_url: values.endpoint_url,
    environment: values.environment,
    max_retries: values.max_retries,
    name: values.name,
    plugin_id: values.plugin_id,
    request_config: requestConfig,
    status: values.status,
    timeout_seconds: values.timeout_seconds,
  };
}

function buildActionPayload(
  values: ActionFormValues,
  requestConfig: Record<string, unknown>,
  resultMapping: Record<string, unknown>,
): Partial<PluginActionRecord> {
  return {
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
  };
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

function compactJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

function mergeWriteTarget(
  resultMapping: Record<string, unknown>,
  writeTarget?: string,
): Record<string, unknown> {
  const nextMapping = { ...resultMapping };
  if (writeTarget) {
    nextMapping.write_target = writeTarget;
  }
  return nextMapping;
}

function defaultResultMappingForWriteTarget(writeTarget?: string): Record<string, unknown> {
  if (writeTarget === 'user_feedback_insights') {
    return { ...MAXCOMPUTE_DEFAULT_RESULT_MAPPING };
  }
  return { ...SCHEDULED_JOB_RESULT_DEFAULT_MAPPING };
}

function writeTargetFromResultMapping(resultMapping: Record<string, unknown>): string {
  return typeof resultMapping.write_target === 'string'
    ? resultMapping.write_target
    : 'scheduled_job_result';
}

function stringMappingValue(resultMapping: Record<string, unknown>, key: string): string | undefined {
  const value = resultMapping[key];
  return typeof value === 'string' ? value : undefined;
}

function resultMappingVisualFields(resultMapping: Record<string, unknown>): Partial<ActionFormValues> {
  return {
    insights_path: stringMappingValue(resultMapping, 'insights_path'),
    records_imported_path: stringMappingValue(resultMapping, 'records_imported_path'),
    rows_path: stringMappingValue(resultMapping, 'rows_path'),
    write_target: writeTargetFromResultMapping(resultMapping),
  };
}

function buildVisualResultMapping(values: Partial<ActionFormValues>): Record<string, unknown> {
  const writeTarget = values.write_target || 'scheduled_job_result';
  if (writeTarget === 'user_feedback_insights') {
    return mergeWriteTarget(
      {
        insights_path: values.insights_path?.trim() || '$.insights',
        records_imported_path: values.records_imported_path?.trim() || '$.row_count',
        rows_path: values.rows_path?.trim() || '$.rows',
      },
      writeTarget,
    );
  }
  return mergeWriteTarget(
    {
      ...(values.records_imported_path?.trim()
        ? { records_imported_path: values.records_imported_path.trim() }
        : {}),
    },
    writeTarget,
  );
}

function JsonDiagnosticsBlock({ title, value }: { title: string; value?: unknown }) {
  if (value === undefined || value === null) {
    return null;
  }
  return (
    <div>
      <Typography.Text strong>{title}</Typography.Text>
      <pre
        style={{
          background: '#f8fafc',
          border: '1px solid #e5e7eb',
          borderRadius: 6,
          margin: '8px 0 0',
          maxHeight: 260,
          overflow: 'auto',
          padding: 12,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {compactJson(value)}
      </pre>
    </div>
  );
}

function RequestParameterRows({
  addText,
  name,
  namePlaceholder,
  title,
  valuePlaceholder,
}: {
  addText: string;
  name: 'connection_header_rows' | 'connection_param_rows' | 'header_rows' | 'param_rows';
  namePlaceholder: string;
  title: string;
  valuePlaceholder: string;
}) {
  const form = Form.useFormInstance();
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
  const [scheduledJobs, setScheduledJobs] = useState<ScheduledJobRecord[]>([]);
  const [systemVariables, setSystemVariables] = useState<PluginSystemVariableRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [pluginModalOpen, setPluginModalOpen] = useState(false);
  const [connectionModalOpen, setConnectionModalOpen] = useState(false);
  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [editingPlugin, setEditingPlugin] = useState<PluginRecord | undefined>();
  const [editingConnection, setEditingConnection] = useState<PluginConnectionRecord | undefined>();
  const [editingAction, setEditingAction] = useState<PluginActionRecord | undefined>();
  const [trialModalOpen, setTrialModalOpen] = useState(false);
  const [trialAction, setTrialAction] = useState<PluginActionRecord | undefined>();
  const [trialConnectionId, setTrialConnectionId] = useState<string | undefined>();
  const [trialInputJson, setTrialInputJson] = useState('{}');
  const [trialResult, setTrialResult] = useState<PluginActionTrialResult | undefined>();
  const [trialRunning, setTrialRunning] = useState(false);
  const [actionScenario, setActionScenario] = useState<string | undefined>();
  const [advancedConnectionJsonOpen, setAdvancedConnectionJsonOpen] = useState(false);
  const [advancedConnectionRequestJsonOpen, setAdvancedConnectionRequestJsonOpen] = useState(false);
  const [advancedActionJsonOpen, setAdvancedActionJsonOpen] = useState(false);
  const [testingConnectionId, setTestingConnectionId] = useState<string | undefined>();
  const selectedConnectionAuthType = Form.useWatch('auth_type', connectionForm);
  const actionFormValues = Form.useWatch([], actionForm) as ActionFormValues | undefined;

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
  const connectionById = useMemo(
    () => new Map(connections.map((connection) => [connection.id, connection])),
    [connections],
  );
  const pluginById = useMemo(() => new Map(plugins.map((plugin) => [plugin.id, plugin])), [plugins]);
  const actionById = useMemo(() => new Map(actions.map((action) => [action.id, action])), [actions]);
  const requestPreview = useMemo(
    () => buildActionRequestPreview(actionFormValues, connectionById.get(actionFormValues?.connection_id ?? '')),
    [actionFormValues, connectionById],
  );
  const integrationChains = useMemo(() => {
    const chains = scheduledJobs
      .filter((job) => job.plugin_action_id)
      .map((job) => {
        const action = actionById.get(String(job.plugin_action_id));
        const connection = action?.connection_id ? connectionById.get(action.connection_id) : undefined;
        const plugin = action?.plugin_id ? pluginById.get(action.plugin_id) : undefined;
        return { action, connection, job, plugin };
      })
      .filter((chain) => chain.action);
    if (chains.length > 0) {
      return chains;
    }
    return actions.slice(0, 3).map((action) => ({
      action,
      connection: action.connection_id ? connectionById.get(action.connection_id) : undefined,
      job: undefined,
      plugin: pluginById.get(action.plugin_id),
    }));
  }, [actionById, actions, connectionById, pluginById, scheduledJobs]);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [nextPlugins, nextConnections, nextActions, nextLogs, nextJobs] = await Promise.all([
        fetchPlugins(),
        fetchPluginConnections(),
        fetchPluginActions(),
        fetchPluginInvocationLogs(),
        fetchScheduledJobs(),
      ]);
      setPlugins(nextPlugins);
      setConnections(nextConnections);
      setActions(nextActions);
      setLogs(nextLogs);
      setScheduledJobs(nextJobs);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '插件配置加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    fetchPluginSystemVariables('Asia/Shanghai')
      .then((result) => setSystemVariables(result.items))
      .catch(() => setSystemVariables([]));
  }, []);

  const openCreatePluginModal = () => {
    setEditingPlugin(undefined);
    pluginForm.resetFields();
    pluginForm.setFieldsValue({
      category: 'general',
      protocol: 'http',
      risk_level: 'medium',
      status: 'active',
    });
    setPluginModalOpen(true);
  };

  const openEditPluginModal = (plugin: PluginRecord) => {
    setEditingPlugin(plugin);
    pluginForm.resetFields();
    pluginForm.setFieldsValue({
      category: plugin.category ?? 'general',
      code: plugin.code,
      description: plugin.description ?? undefined,
      name: plugin.name,
      protocol: plugin.protocol,
      risk_level: plugin.risk_level ?? 'medium',
      status: plugin.status,
    });
    setPluginModalOpen(true);
  };

  const closePluginModal = () => {
    setPluginModalOpen(false);
    setEditingPlugin(undefined);
    pluginForm.resetFields();
  };

  const submitPlugin = async () => {
    const values = await pluginForm.validateFields();
    if (editingPlugin) {
      await updatePlugin(editingPlugin.id, values);
      message.success('插件已更新');
    } else {
      await createPlugin(values);
      message.success('插件已创建');
    }
    closePluginModal();
    await reload();
  };

  const warnDeleteUsage = (title: string, groups: DeleteUsageGroup[]) => {
    Modal.warning({
      content: deleteUsageContent(groups),
      okText: '知道了',
      title,
      width: 640,
    });
  };

  const pluginDeleteUsageGroups = (plugin: PluginRecord): DeleteUsageGroup[] => {
    const pluginConnections = connections.filter((connection) => connection.plugin_id === plugin.id);
    const pluginActions = actions.filter((action) => action.plugin_id === plugin.id);
    const connectionIds = new Set(pluginConnections.map((connection) => connection.id));
    const actionIds = new Set(pluginActions.map((action) => action.id));
    return [
      { items: pluginConnections.map(usageItemName), label: '连接' },
      { items: pluginActions.map(usageItemName), label: '动作' },
      {
        items: scheduledJobs
          .filter((job) => (
            actionIds.has(String(job.plugin_action_id ?? ''))
            || connectionIds.has(String(job.plugin_connection_id ?? ''))
          ))
          .map(usageItemName),
        label: '定时作业',
      },
      {
        items: logs
          .filter((log) => (
            log.plugin_id === plugin.id
            || actionIds.has(String(log.action_id ?? ''))
            || connectionIds.has(String(log.connection_id ?? ''))
          ))
          .map(usageItemName),
        label: '调用日志',
      },
    ];
  };

  const connectionDeleteUsageGroups = (connection: PluginConnectionRecord): DeleteUsageGroup[] => [
    {
      items: actions
        .filter((action) => action.connection_id === connection.id)
        .map(usageItemName),
      label: '动作',
    },
    {
      items: scheduledJobs
        .filter((job) => job.plugin_connection_id === connection.id)
        .map(usageItemName),
      label: '定时作业',
    },
    {
      items: logs
        .filter((log) => log.connection_id === connection.id)
        .map(usageItemName),
      label: '调用日志',
    },
  ];

  const actionDeleteUsageGroups = (action: PluginActionRecord): DeleteUsageGroup[] => [
    {
      items: scheduledJobs
        .filter((job) => job.plugin_action_id === action.id)
        .map(usageItemName),
      label: '定时作业',
    },
    {
      items: logs
        .filter((log) => log.action_id === action.id)
        .map(usageItemName),
      label: '调用日志',
    },
  ];

  const confirmDeletePlugin = (plugin: PluginRecord) => {
    const usageGroups = pluginDeleteUsageGroups(plugin);
    if (hasDeleteUsage(usageGroups)) {
      warnDeleteUsage(`插件「${plugin.name}」正在使用中`, usageGroups);
      return;
    }
    Modal.confirm({
      cancelText: '取消',
      content: `确定删除插件「${plugin.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      title: '删除插件',
      onOk: async () => {
        try {
          await deletePlugin(plugin.id);
          message.success('插件已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '插件删除失败');
        }
      },
    });
  };

  const confirmDeleteConnection = (connection: PluginConnectionRecord) => {
    const usageGroups = connectionDeleteUsageGroups(connection);
    if (hasDeleteUsage(usageGroups)) {
      warnDeleteUsage(`连接「${connection.name}」正在使用中`, usageGroups);
      return;
    }
    Modal.confirm({
      cancelText: '取消',
      content: `确定删除连接「${connection.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      title: '删除连接',
      onOk: async () => {
        try {
          await deletePluginConnection(connection.id);
          message.success('连接已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '连接删除失败');
        }
      },
    });
  };

  const confirmDeleteAction = (action: PluginActionRecord) => {
    const usageGroups = actionDeleteUsageGroups(action);
    if (hasDeleteUsage(usageGroups)) {
      warnDeleteUsage(`动作「${action.name}」正在使用中`, usageGroups);
      return;
    }
    Modal.confirm({
      cancelText: '取消',
      content: `确定删除动作「${action.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      title: '删除动作',
      onOk: async () => {
        try {
          await deletePluginAction(action.id);
          message.success('动作已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '动作删除失败');
        }
      },
    });
  };

  const openCreateConnectionModal = () => {
    setEditingConnection(undefined);
    setAdvancedConnectionJsonOpen(false);
    setAdvancedConnectionRequestJsonOpen(false);
    connectionForm.resetFields();
    connectionForm.setFieldsValue({
      auth_type: 'none',
      environment: 'default',
      max_retries: 0,
      status: 'active',
      timeout_seconds: 30,
    });
    setConnectionModalOpen(true);
  };

  const openEditConnectionModal = (connection: PluginConnectionRecord) => {
    const authConfig = connection.auth_config ?? {};
    const requestConfig = connection.request_config ?? {};
    setEditingConnection(connection);
    setAdvancedConnectionJsonOpen(false);
    setAdvancedConnectionRequestJsonOpen(false);
    connectionForm.resetFields();
    connectionForm.setFieldsValue({
      auth_config: stableJson(authConfig),
      auth_type: connection.auth_type ?? 'none',
      connection_header_rows: recordToRows(configSection(requestConfig, 'headers')),
      connection_param_rows: recordToRows(configSection(requestConfig, 'query')),
      endpoint_url: connection.endpoint_url,
      environment: connection.environment ?? 'default',
      header_name: typeof authConfig.header_name === 'string' ? authConfig.header_name : undefined,
      max_retries: connection.max_retries ?? 0,
      name: connection.name,
      password_ref: typeof authConfig.password_ref === 'string' ? authConfig.password_ref : undefined,
      plugin_id: connection.plugin_id,
      request_config: stableJson(requestConfig),
      secret_ref: typeof authConfig.secret_ref === 'string' ? authConfig.secret_ref : undefined,
      status: connection.status,
      timeout_seconds: connection.timeout_seconds ?? 30,
      token_ref: typeof authConfig.token_ref === 'string' ? authConfig.token_ref : undefined,
      username_ref: typeof authConfig.username_ref === 'string' ? authConfig.username_ref : undefined,
    });
    setConnectionModalOpen(true);
  };

  const closeConnectionModal = () => {
    setConnectionModalOpen(false);
    setEditingConnection(undefined);
    setAdvancedConnectionJsonOpen(false);
    setAdvancedConnectionRequestJsonOpen(false);
    connectionForm.resetFields();
  };

  const submitConnection = async () => {
    try {
      const values = await connectionForm.validateFields();
      const authConfig = advancedConnectionJsonOpen
        ? parseJsonObject(values.auth_config, '认证配置')
        : buildConnectionAuthConfig(values);
      const requestConfig = advancedConnectionRequestJsonOpen
        ? parseJsonObject(values.request_config, '请求配置')
        : buildConnectionRequestConfig(values);
      const payload = buildConnectionPayload(values, authConfig, requestConfig);
      if (editingConnection) {
        await updatePluginConnection(editingConnection.id, payload);
        message.success('连接已更新');
      } else {
        await createPluginConnection(payload);
        message.success('连接已创建');
      }
      closeConnectionModal();
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : editingConnection ? '连接更新失败' : '连接创建失败');
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
      const resultMapping = advancedActionJsonOpen
        ? mergeWriteTarget(parseJsonObject(values.result_mapping, '结果映射'), values.write_target)
        : buildVisualResultMapping(values);
      const payload = buildActionPayload(values, requestConfig, resultMapping);
      if (editingAction) {
        await updatePluginAction(editingAction.id, payload);
        message.success('动作已更新');
      } else {
        await createPluginAction(payload);
        message.success('动作已创建');
      }
      closeActionModal();
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : editingAction ? '动作更新失败' : '动作创建失败');
    }
  };

  const openCreateActionModal = () => {
    setEditingAction(undefined);
    setActionScenario(undefined);
    setAdvancedActionJsonOpen(false);
    actionForm.resetFields();
    actionForm.setFieldsValue({
      action_type: 'http_request',
      method: 'GET',
      requires_human_review: false,
      result_mapping: stableJson(SCHEDULED_JOB_RESULT_DEFAULT_MAPPING),
      status: 'active',
      ...resultMappingVisualFields(SCHEDULED_JOB_RESULT_DEFAULT_MAPPING),
    });
    setActionModalOpen(true);
  };

  const openEditActionModal = (action: PluginActionRecord) => {
    const requestConfig = action.request_config ?? {};
    const resultMapping = action.result_mapping ?? {};
    const isMaxComputeAction = requestConfig.tool_name === 'maxcompute.execute_sql';
    setEditingAction(action);
    setActionScenario(isMaxComputeAction ? MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO : undefined);
    setAdvancedActionJsonOpen(!isMaxComputeAction && action.action_type === 'mcp_tool');
    actionForm.resetFields();
    actionForm.setFieldsValue({
      action_type: action.action_type,
      code: action.code,
      connection_id: action.connection_id ?? undefined,
      description: action.description ?? undefined,
      header_rows: recordToRows(configSection(requestConfig, 'headers')),
      max_rows: typeof requestConfig.limit === 'number' ? requestConfig.limit : undefined,
      method: typeof requestConfig.method === 'string' ? requestConfig.method : 'GET',
      name: action.name,
      param_rows: recordToRows(configSection(requestConfig, 'query')),
      path: typeof requestConfig.path === 'string' ? requestConfig.path : undefined,
      plugin_id: action.plugin_id,
      request_config: stableJson(requestConfig),
      requires_human_review: action.requires_human_review,
      result_mapping: stableJson(resultMapping),
      returned_fields: Array.isArray(requestConfig.fields)
        ? requestConfig.fields.join(',')
        : undefined,
      scenario: isMaxComputeAction ? MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO : undefined,
      status: action.status,
      table_name: typeof requestConfig.table === 'string' ? requestConfig.table : undefined,
      time_field: typeof requestConfig.time_field === 'string' ? requestConfig.time_field : undefined,
      ...resultMappingVisualFields(resultMapping),
    });
    setActionModalOpen(true);
  };

  const closeActionModal = () => {
    setActionModalOpen(false);
    setEditingAction(undefined);
    setActionScenario(undefined);
    setAdvancedActionJsonOpen(false);
    actionForm.resetFields();
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
      ...resultMappingVisualFields(MAXCOMPUTE_DEFAULT_RESULT_MAPPING),
    };
    actionForm.setFieldsValue(nextValues);
  };

  const applyWriteTargetDefaults = (writeTarget?: string) => {
    const resultMapping = defaultResultMappingForWriteTarget(writeTarget);
    actionForm.setFieldsValue({
      result_mapping: stableJson(resultMapping),
      ...resultMappingVisualFields(resultMapping),
    });
  };

  const toggleAdvancedActionJson = () => {
    const nextOpen = !advancedActionJsonOpen;
    if (nextOpen) {
      syncActionJsonFromVisual();
    }
    setAdvancedActionJsonOpen(nextOpen);
  };

  const syncActionJsonFromVisual = () => {
    const values = actionForm.getFieldsValue();
    const requestConfig =
      values.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO
        ? buildMaxComputeRequestConfig(values)
        : buildVisualRequestConfig(values);
    actionForm.setFieldsValue({
      request_config: stableJson(requestConfig),
      result_mapping: stableJson(buildVisualResultMapping(values)),
    });
  };

  const applyActionJsonToVisual = () => {
    try {
      const config = parseJsonObject(actionForm.getFieldValue('request_config'), '请求配置');
      const resultMapping = parseJsonObject(actionForm.getFieldValue('result_mapping'), '结果映射');
      actionForm.setFieldsValue({
        header_rows: recordToRows(config.headers),
        method: typeof config.method === 'string' ? config.method : 'GET',
        param_rows: recordToRows(config.query),
        path: typeof config.path === 'string' ? config.path : undefined,
        ...resultMappingVisualFields(resultMapping),
      });
      message.success('已从 JSON 同步到可视化字段');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'JSON 解析失败');
    }
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

  const syncConnectionRequestJsonFromVisual = () => {
    const values = connectionForm.getFieldsValue();
    connectionForm.setFieldValue('request_config', stableJson(buildConnectionRequestConfig(values)));
  };

  const toggleAdvancedConnectionRequestJson = () => {
    const nextOpen = !advancedConnectionRequestJsonOpen;
    if (nextOpen) {
      syncConnectionRequestJsonFromVisual();
    }
    setAdvancedConnectionRequestJsonOpen(nextOpen);
  };

  const applyConnectionJsonToVisual = () => {
    try {
      const config = parseJsonObject(connectionForm.getFieldValue('auth_config'), '认证配置');
      connectionForm.setFieldsValue({
        header_name: typeof config.header_name === 'string' ? config.header_name : undefined,
        password_ref: typeof config.password_ref === 'string' ? config.password_ref : undefined,
        secret_ref: typeof config.secret_ref === 'string' ? config.secret_ref : undefined,
        token_ref: typeof config.token_ref === 'string' ? config.token_ref : undefined,
        username_ref: typeof config.username_ref === 'string' ? config.username_ref : undefined,
      });
      message.success('已从认证 JSON 同步到可视化字段');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'JSON 解析失败');
    }
  };

  const applyConnectionRequestJsonToVisual = () => {
    try {
      const config = parseJsonObject(connectionForm.getFieldValue('request_config'), '请求配置');
      connectionForm.setFieldsValue({
        connection_header_rows: recordToRows(config.headers),
        connection_param_rows: recordToRows(config.query),
      });
      message.success('已从请求 JSON 同步到 Params / Headers');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'JSON 解析失败');
    }
  };

  const runAction = async (action: PluginActionRecord) => {
    await invokePluginAction(action.id);
    message.success('插件动作已执行');
    await reload();
  };

  const runConnectionTest = async (connection: PluginConnectionRecord) => {
    if (testingConnectionId) {
      return;
    }
    const messageKey = `plugin-connection-test-${connection.id}`;
    setTestingConnectionId(connection.id);
    message.loading({
      content: `正在测试连接「${connection.name}」，请稍候...`,
      duration: 0,
      key: messageKey,
    });
    try {
      const result = await testPluginConnection(connection.id);
      const requestSummary = result.request_summary ?? {};
      const placeholderHeaders = Array.isArray(requestSummary.masked_placeholder_headers)
        ? requestSummary.masked_placeholder_headers.map(String)
        : [];
      Modal.info({
        content: (
          <Space orientation="vertical" size={10} style={{ width: '100%' }}>
            <div>状态：<Tag color={result.status === 'succeeded' ? 'green' : 'red'}>{result.status}</Tag>耗时：{result.latency_ms}ms</div>
            {placeholderHeaders.length > 0 ? (
              <Alert
                description={`最终请求仍包含脱敏占位：${placeholderHeaders.join('、')}。请重新填写真实 Header 值，或改用认证配置字段维护 Authorization。`}
                message="Authorization 等敏感 Header 不能使用 *** 占位发起请求"
                showIcon
                type="error"
              />
            ) : null}
            {result.error_message ? (
              <Alert description={result.error_message} message="错误信息" showIcon type="error" />
            ) : null}
            <Table
              columns={[
                { dataIndex: 'name', title: '检查项', width: 190 },
                { dataIndex: 'status', title: '状态', width: 130, render: (value: string) => <Tag>{value}</Tag> },
                {
                  dataIndex: 'detail',
                  title: '说明',
                  render: (value?: string) => (
                    <Typography.Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {value ?? '-'}
                    </Typography.Text>
                  ),
                },
                { dataIndex: 'latency_ms', title: '耗时 ms', width: 100, render: (value?: number) => value ?? '-' },
              ]}
              dataSource={result.diagnostics ?? []}
              pagination={false}
              rowKey="name"
              scroll={{ x: 920 }}
              size="small"
            />
            <JsonDiagnosticsBlock title="完整请求信息" value={requestSummary} />
            <JsonDiagnosticsBlock title="远端响应信息" value={result.response_summary} />
          </Space>
        ),
        title: '连接测试诊断',
        width: 980,
      });
      if (result.status === 'succeeded') {
        message.success({
          content: `连接测试成功，耗时 ${result.latency_ms}ms`,
          duration: 3,
          key: messageKey,
        });
      } else {
        message.error({
          content: result.error_message || '连接测试失败',
          duration: 5,
          key: messageKey,
        });
      }
    } catch (error) {
      message.error({
        content: error instanceof Error ? error.message : '连接测试失败',
        duration: 5,
        key: messageKey,
      });
    } finally {
      setTestingConnectionId(undefined);
    }
  };

  const openTrialModal = (action: PluginActionRecord) => {
    setTrialAction(action);
    setTrialConnectionId(action.connection_id ?? undefined);
    setTrialInputJson('{}');
    setTrialResult(undefined);
    setTrialModalOpen(true);
  };

  const runActionTrial = async () => {
    if (!trialAction) {
      return;
    }
    try {
      setTrialRunning(true);
      const parsedInput = parseJsonObject(trialInputJson, '试运行输入');
      const result = await trialPluginAction(trialAction.id, {
        connection_id: trialConnectionId,
        input_payload: parsedInput,
      });
      setTrialResult(result);
      if (result.status === 'succeeded') {
        message.success('试运行完成');
      } else {
        message.error(result.error_message || '试运行失败');
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '试运行失败');
    } finally {
      setTrialRunning(false);
    }
  };

  return (
    <PageContainer title="插件管理">
      <Space orientation="vertical" size={12} style={{ width: '100%', marginBottom: 16 }}>
        <Alert
          title="系统变量预览"
          description={
            <Space wrap>
              {(systemVariables.length > 0 ? systemVariables : systemVariableOptions.map((item) => ({
                expression: item.value,
                label: item.label,
                value: item.value,
              }))).map((item) => (
                <Tag key={item.expression}>
                  {item.label}: {item.expression} = {item.value}
                </Tag>
              ))}
            </Space>
          }
          showIcon
          type="info"
        />
        <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12 }}>
          <Typography.Text strong>调用链路</Typography.Text>
          <Space orientation="vertical" size={8} style={{ display: 'flex', marginTop: 10 }}>
            {integrationChains.length > 0 ? integrationChains.map((chain, index) => (
              <Space key={`${chain.action?.id ?? index}-${chain.job?.id ?? 'action'}`} wrap>
                <Tag color="blue">插件：{chain.plugin?.name ?? chain.action?.plugin_id}</Tag>
                <Typography.Text type="secondary">→</Typography.Text>
                <Tag color="cyan">连接：{chain.connection?.name ?? chain.action?.connection_id ?? '未绑定'}</Tag>
                <Typography.Text type="secondary">→</Typography.Text>
                <Tag color="purple">动作：{chain.action?.name}</Tag>
                <Typography.Text type="secondary">→</Typography.Text>
                <Tag color={chain.job ? 'green' : 'default'}>定时作业：{chain.job?.name ?? '未绑定'}</Tag>
              </Space>
            )) : (
              <Typography.Text type="secondary">暂无可展示链路</Typography.Text>
            )}
          </Space>
        </div>
      </Space>
      <Tabs
        items={[
          {
            key: 'plugins',
            label: '插件',
            children: (
              <ProTable<PluginRecord>
                cardBordered
                className="management-list-table"
                dateFormatter="string"
                headerTitle="插件"
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
                scroll={{ x: 1132 }}
                search={false}
                dataSource={plugins}
                tableLayout="fixed"
                toolBarRender={() => [
                  <Button key="create-plugin" aria-label="新增插件" icon={<PlusOutlined />} type="primary" onClick={openCreatePluginModal}>
                    新增插件
                  </Button>,
                  <Button key="reload-plugins" icon={<ReloadOutlined />} onClick={reload}>
                    刷新
                  </Button>,
                ]}
                columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true, width: 220 },
                  { dataIndex: 'code', title: '编码', ellipsis: true, width: 200 },
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
                  {
                    fixed: 'right',
                    key: 'actions',
                    title: '操作',
                    valueType: 'option',
                    width: 164,
                    render: (_, row) => (
                      <Space className="management-row-actions" size={0}>
                        <Button
                          aria-label={`编辑插件 ${row.name}`}
                          icon={<EditOutlined />}
                          onClick={() => openEditPluginModal(row)}
                          type="link"
                        >
                          编辑
                        </Button>
                        <Button
                          aria-label={`删除插件 ${row.name}`}
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => confirmDeletePlugin(row)}
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
            key: 'connections',
            label: '连接',
            children: (
              <ProTable<PluginConnectionRecord>
                cardBordered
                className="management-list-table"
                dateFormatter="string"
                headerTitle="连接"
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
                scroll={{ x: 1420 }}
                search={false}
                dataSource={connections}
                tableLayout="fixed"
                toolBarRender={() => [
                  <Button key="create-connection" aria-label="新增连接" icon={<PlusOutlined />} type="primary" onClick={openCreateConnectionModal}>
                    新增连接
                  </Button>,
                  <Button key="reload-connections" icon={<ReloadOutlined />} onClick={reload}>
                    刷新
                  </Button>,
                ]}
                columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true, width: 220 },
                  {
                    dataIndex: 'plugin_id',
                    title: '插件',
                    ellipsis: true,
                    width: 220,
                    render: (value) => pluginById.get(String(value))?.name ?? value,
                  },
                  {
                    dataIndex: 'environment',
                    title: '环境',
                    width: 130,
                    render: (value) => connectionEnvironmentLabelByValue.get(String(value)) ?? String(value ?? '-'),
                  },
                  { dataIndex: 'auth_type', title: '认证', width: 130 },
                  { dataIndex: 'endpoint_url', title: 'Endpoint', ellipsis: true, width: 320 },
                  { dataIndex: 'status', title: '状态', width: 110 },
                  {
                    fixed: 'right',
                    key: 'actions',
                    title: '操作',
                    valueType: 'option',
                    width: 260,
                    render: (_, row) => {
                      const isTestingConnection = testingConnectionId === row.id;
                      return (
                        <Space className="management-row-actions" size={0}>
                          <Button
                            aria-label={`编辑连接 ${row.name}`}
                            disabled={Boolean(testingConnectionId)}
                            icon={<EditOutlined />}
                            onClick={() => openEditConnectionModal(row)}
                            type="link"
                          >
                            编辑
                          </Button>
                          <Button
                            aria-label={
                              isTestingConnection
                                ? `连接测试中 ${row.name}`
                                : `测试连接 ${row.name}`
                            }
                            disabled={Boolean(testingConnectionId)}
                            icon={<PlayCircleOutlined />}
                            loading={isTestingConnection}
                            onClick={() => runConnectionTest(row)}
                            type="link"
                          >
                            {isTestingConnection ? '测试中' : '测试'}
                          </Button>
                          <Button
                            aria-label={`删除连接 ${row.name}`}
                            danger
                            disabled={Boolean(testingConnectionId)}
                            icon={<DeleteOutlined />}
                            onClick={() => confirmDeleteConnection(row)}
                            type="link"
                          >
                            删除
                          </Button>
                        </Space>
                      );
                    },
                  },
                ]}
              />
            ),
          },
          {
            key: 'actions',
            label: '动作',
            children: (
              <ProTable<PluginActionRecord>
                cardBordered
                className="management-list-table"
                dateFormatter="string"
                headerTitle="动作"
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
                scroll={{ x: 1570 }}
                search={false}
                dataSource={actions}
                tableLayout="fixed"
                toolBarRender={() => [
                  <Button key="create-action" aria-label="新增动作" icon={<PlusOutlined />} type="primary" onClick={openCreateActionModal}>
                    新增动作
                  </Button>,
                  <Button key="reload-actions" icon={<ReloadOutlined />} onClick={reload}>
                    刷新
                  </Button>,
                ]}
                columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true, width: 220 },
                  { dataIndex: 'code', title: '编码', ellipsis: true, width: 200 },
                  { dataIndex: 'action_type', title: '类型', width: 130 },
                  {
                    dataIndex: 'plugin_id',
                    title: '插件',
                    ellipsis: true,
                    width: 200,
                    render: (value) => pluginById.get(String(value))?.name ?? value,
                  },
                  {
                    dataIndex: 'connection_id',
                    title: '连接',
                    ellipsis: true,
                    width: 200,
                    render: (value) => value ? connectionById.get(String(value))?.name ?? value : '-',
                  },
                  {
                    dataIndex: 'result_mapping',
                    title: '写入目标',
                    ellipsis: true,
                    width: 220,
                    render: (value) => {
                      const writeTarget = value && typeof value === 'object'
                        ? (value as unknown as Record<string, unknown>).write_target
                        : undefined;
                      return typeof writeTarget === 'string'
                        ? resultWriteTargetLabelByValue.get(writeTarget) ?? writeTarget
                        : '仅保存运行结果';
                    },
                  },
                  { dataIndex: 'status', title: '状态', width: 100 },
                  {
                    fixed: 'right',
                    key: 'actions',
                    title: '操作',
                    valueType: 'option',
                    width: 300,
                    render: (_, row) => (
                      <Space className="management-row-actions" size={0}>
                        <Button
                          aria-label={`编辑动作 ${row.name}`}
                          icon={<EditOutlined />}
                          onClick={() => openEditActionModal(row)}
                          type="link"
                        >
                          编辑
                        </Button>
                        <Button icon={<PlayCircleOutlined />} onClick={() => openTrialModal(row)} type="link">
                          试运行
                        </Button>
                        <Button onClick={() => runAction(row)} type="link">运行</Button>
                        <Button
                          aria-label={`删除动作 ${row.name}`}
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => confirmDeleteAction(row)}
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
            key: 'logs',
            label: '调用日志',
            children: (
              <ProTable<PluginInvocationLogRecord>
                cardBordered
                className="management-list-table"
                dateFormatter="string"
                headerTitle="调用日志"
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
                scroll={{ x: 1210 }}
                search={false}
                dataSource={logs}
                tableLayout="fixed"
                columns={[
                  { dataIndex: 'id', title: '日志 ID', ellipsis: true, width: 240 },
                  { dataIndex: 'action_id', title: '动作 ID', ellipsis: true, width: 240 },
                  { dataIndex: 'scheduled_job_id', title: '定时作业', ellipsis: true, width: 240, render: (value) => value || '-' },
                  { dataIndex: 'status', title: '状态', width: 110 },
                  { dataIndex: 'latency_ms', title: '耗时 ms', width: 110 },
                  { dataIndex: 'error_message', title: '错误', ellipsis: true, width: 270, render: (value) => value || '-' },
                ]}
              />
            ),
          },
        ]}
      />

      <Modal
        open={pluginModalOpen}
        title={editingPlugin ? '编辑插件' : '新增插件'}
        onCancel={closePluginModal}
        onOk={submitPlugin}
      >
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
        title={editingConnection ? '编辑连接' : '新增连接'}
        width={860}
        onCancel={closeConnectionModal}
        onOk={submitConnection}
      >
        <Form
          form={connectionForm}
          layout="vertical"
          initialValues={{ auth_type: 'none', environment: 'default', max_retries: 0, status: 'active', timeout_seconds: 30 }}
          onValuesChange={(changedValues, allValues) => {
            if (
              advancedConnectionRequestJsonOpen
              && !Object.prototype.hasOwnProperty.call(changedValues, 'request_config')
            ) {
              connectionForm.setFieldValue('request_config', stableJson(buildConnectionRequestConfig(allValues)));
            }
          }}
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
            <>
              <Space style={{ marginBottom: 8 }}>
                <Button onClick={() => {
                  const values = connectionForm.getFieldsValue();
                  connectionForm.setFieldValue('auth_config', stableJson(buildConnectionAuthConfig(values)));
                }}>
                  同步可视化到 JSON
                </Button>
                <Button onClick={applyConnectionJsonToVisual}>从 JSON 应用到字段</Button>
              </Space>
              <Form.Item label="认证配置 JSON" name="auth_config">
                <Input.TextArea rows={4} placeholder='{"header_name":"PRIVATE-TOKEN","secret_ref":"vault/gitlab/token"}' />
              </Form.Item>
            </>
          ) : null}
          <RequestParameterRows
            addText="添加 Params"
            name="connection_param_rows"
            namePlaceholder="参数名"
            title="Params"
            valuePlaceholder="参数值"
          />
          <RequestParameterRows
            addText="添加 Headers"
            name="connection_header_rows"
            namePlaceholder="Header 名"
            title="Headers"
            valuePlaceholder="Header 值"
          />
          <Button type="link" onClick={toggleAdvancedConnectionRequestJson}>
            高级请求 JSON 修改
          </Button>
          {advancedConnectionRequestJsonOpen ? (
            <>
              <Space style={{ marginBottom: 8 }}>
                <Button onClick={syncConnectionRequestJsonFromVisual}>同步可视化到 JSON</Button>
                <Button onClick={applyConnectionRequestJsonToVisual}>从 JSON 应用到 Params / Headers</Button>
              </Space>
              <Form.Item label="请求配置 JSON" name="request_config">
                <Input.TextArea rows={4} placeholder='{"query":{"start_pt":"{{current_date-7}}"},"headers":{"Authorization":"APPCODE xxx"}}' />
              </Form.Item>
            </>
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
        title={editingAction ? '编辑动作' : '新增动作'}
        onCancel={closeActionModal}
        onOk={submitAction}
      >
        <Form
          form={actionForm}
          layout="vertical"
          onValuesChange={(changedValues, allValues) => {
            if (
              advancedActionJsonOpen
              && !Object.prototype.hasOwnProperty.call(changedValues, 'request_config')
              && !Object.prototype.hasOwnProperty.call(changedValues, 'result_mapping')
            ) {
              const requestConfig =
                allValues.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO
                  ? buildMaxComputeRequestConfig(allValues)
                  : buildVisualRequestConfig(allValues);
              actionForm.setFieldsValue({
                request_config: stableJson(requestConfig),
                result_mapping: stableJson(buildVisualResultMapping(allValues)),
              });
            }
          }}
          initialValues={{
            action_type: 'http_request',
            method: 'GET',
            requires_human_review: false,
            write_target: 'scheduled_job_result',
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
          <Form.Item label="结果写入目标" name="write_target">
            <Select options={resultWriteTargetOptions} onChange={applyWriteTargetDefaults} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(previous, current) => previous.write_target !== current.write_target}>
            {({ getFieldValue }) =>
              getFieldValue('write_target') === 'user_feedback_insights' ? (
                <Space wrap>
                  <Form.Item
                    label="洞察列表 JSONPath"
                    name="insights_path"
                    rules={[{ required: true, message: '请输入洞察列表路径' }]}
                  >
                    <Input placeholder="$.insights" style={{ width: 220 }} />
                  </Form.Item>
                  <Form.Item label="源表行数 JSONPath" name="records_imported_path">
                    <Input placeholder="$.row_count" style={{ width: 220 }} />
                  </Form.Item>
                  <Form.Item label="原始行列表 JSONPath" name="rows_path">
                    <Input placeholder="$.rows" style={{ width: 220 }} />
                  </Form.Item>
                </Space>
              ) : (
                <Form.Item label="导入数量 JSONPath" name="records_imported_path">
                  <Input placeholder="$.row_count" />
                </Form.Item>
              )
            }
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
          <div style={{ background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <Typography.Text strong>请求预览</Typography.Text>
            <pre style={{ margin: '8px 0 0', whiteSpace: 'pre-wrap' }}>{compactJson(requestPreview)}</pre>
          </div>
          <Button type="link" onClick={toggleAdvancedActionJson}>
            高级 JSON 修改
          </Button>
          {advancedActionJsonOpen ? (
            <>
              <Space style={{ marginBottom: 8 }}>
                <Button onClick={syncActionJsonFromVisual}>同步可视化到 JSON</Button>
                <Button onClick={applyActionJsonToVisual}>从 JSON 应用到 Params / Headers</Button>
              </Space>
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

      <Modal
        confirmLoading={trialRunning}
        okText="试运行"
        open={trialModalOpen}
        title={`动作试运行${trialAction ? `：${trialAction.name}` : ''}`}
        width={820}
        onCancel={() => setTrialModalOpen(false)}
        onOk={runActionTrial}
      >
        <Space orientation="vertical" size={12} style={{ width: '100%' }}>
          <Space wrap>
            <Typography.Text strong>连接</Typography.Text>
            <Select
              allowClear
              options={connectionOptions}
              style={{ width: 320 }}
              value={trialConnectionId}
              onChange={setTrialConnectionId}
            />
          </Space>
          <div>
            <Typography.Text strong>试运行输入 JSON</Typography.Text>
            <Input.TextArea
              rows={5}
              value={trialInputJson}
              onChange={(event) => setTrialInputJson(event.target.value)}
            />
          </div>
          {trialResult ? (
            <Space orientation="vertical" size={10} style={{ width: '100%' }}>
              <div>
                状态：<Tag color={trialResult.status === 'succeeded' ? 'green' : 'red'}>{trialResult.status}</Tag>
                耗时：{trialResult.latency_ms}ms
              </div>
              {trialResult.error_message ? <Alert title={trialResult.error_message} type="error" /> : null}
              <Typography.Text strong>请求预览</Typography.Text>
              <pre style={{ background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, whiteSpace: 'pre-wrap' }}>
                {compactJson(trialResult.request_preview)}
              </pre>
              <Typography.Text strong>结果映射命中</Typography.Text>
              <Table
                columns={[
                  { dataIndex: 'key', title: '字段' },
                  { dataIndex: 'path', title: 'JSONPath' },
                  { dataIndex: 'matched', title: '命中', render: (value: boolean) => <Tag color={value ? 'green' : 'red'}>{value ? '是' : '否'}</Tag> },
                  { dataIndex: 'value_preview', title: '值预览', ellipsis: true, render: (value: unknown) => compactJson(value) },
                ]}
                dataSource={trialResult.mapping_hits ?? []}
                pagination={false}
                rowKey="key"
                size="small"
              />
              <Typography.Text strong>响应摘要</Typography.Text>
              <pre style={{ background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, whiteSpace: 'pre-wrap' }}>
                {compactJson(trialResult.response_summary)}
              </pre>
            </Space>
          ) : null}
        </Space>
      </Modal>
    </PageContainer>
  );
}
