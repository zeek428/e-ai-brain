import { Alert, Col, Form, Input, InputNumber, Radio, Row, Select, Typography } from 'antd';
import type { FormItemProps } from 'antd';

import type { PluginActionRecord, PluginConnectionRecord } from '../../../services/aiBrain';
import { SYSTEM_VARIABLE_OPTIONS } from '../../Plugins/components/pluginSystemVariableOptions';
import { dataSourceModeOptions } from './scheduledJobFormTransformHelpers';
import { ScheduledJobFormSection } from './ScheduledJobFormSection';

type FormRule = NonNullable<FormItemProps['rules']>[number];

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

function recordValue(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function schemaProperties(action: PluginActionRecord | undefined): Record<string, Record<string, unknown>> {
  const inputSchema = recordValue(action?.input_schema);
  const requestConfig = recordValue(action?.request_config);
  const toolSchema = recordValue(requestConfig?.tool_schema);
  const schema = inputSchema ?? toolSchema;
  const properties = recordValue(schema?.properties);
  if (!properties) {
    return {};
  }
  return Object.fromEntries(
    Object.entries(properties)
      .filter(([, value]) => recordValue(value))
      .map(([key, value]) => [key, value as Record<string, unknown>]),
  );
}

function requiredSchemaFields(action: PluginActionRecord | undefined): Set<string> {
  const inputSchema = recordValue(action?.input_schema);
  const requestConfig = recordValue(action?.request_config);
  const toolSchema = recordValue(requestConfig?.tool_schema);
  const required = inputSchema?.required ?? toolSchema?.required;
  return new Set(Array.isArray(required) ? required.map(String) : []);
}

function actionToolName(action: PluginActionRecord): string {
  const requestConfig = recordValue(action.request_config);
  const toolName = requestConfig?.tool_name;
  return typeof toolName === 'string' ? toolName : '';
}

function isReadAction(action: PluginActionRecord): boolean {
  const text = `${action.code} ${action.name} ${action.action_type} ${actionToolName(action)}`.toLowerCase();
  return [
    'get',
    'list',
    'query',
    'read',
    'receive',
    'scan',
    'search',
    'collect',
    '读取',
    '查询',
    '搜索',
    '列出',
    '接收',
    '获取',
    '扫描',
  ].some((keyword) => text.includes(keyword));
}

function actionLabel(action: PluginActionRecord): string {
  const toolName = actionToolName(action);
  return toolName ? `${action.name} (${toolName})` : action.name;
}

const internalDataSourceTypeOptions = [
  { label: '用户洞察数据', value: 'user_insights' },
  { label: '需求数据', value: 'requirements' },
  { label: '产品数据', value: 'products' },
  { label: 'Bug 数据', value: 'bugs' },
];

const internalDataSourceWindowOptions = [
  {
    description: '当前日期前 30 天，适合近 30 天用户洞察范围',
    label: '当前日期 - 30 天',
    value: '{{current_date-30}}',
  },
  ...SYSTEM_VARIABLE_OPTIONS,
];

function isInternalDataSourceAction(action: PluginActionRecord | undefined): boolean {
  return Boolean(action && actionToolName(action) === 'internal_data_source.query');
}

function connectionLabel(connection: PluginConnectionRecord): string {
  const pluginName = connection.plugin_name ?? (
    connection.plugin_code === 'internal_data_source' ? '内部数据源' : undefined
  );
  return pluginName ? `${connection.name} · ${pluginName}` : connection.name;
}

function isInternalDataSourceConnection(connection: PluginConnectionRecord): boolean {
  return connection.plugin_code === 'internal_data_source'
    || connection.plugin_name === '内部数据源';
}

function displayConnections(connections: PluginConnectionRecord[]): PluginConnectionRecord[] {
  return [
    ...connections.filter(isInternalDataSourceConnection),
    ...connections.filter((connection) => !isInternalDataSourceConnection(connection)),
  ];
}

function inputLabel(key: string, property: Record<string, unknown>): string {
  if (key === 'document_id') {
    return '文档 ID / 文档 URL';
  }
  if (key === 'max_rows') {
    return '最大行数';
  }
  if (key === 'folder_id') {
    return '文件夹 ID';
  }
  if (key === 'keyword') {
    return '关键词';
  }
  return typeof property.title === 'string' ? property.title : key;
}

function inputPlaceholder(key: string, property: Record<string, unknown>): string | undefined {
  if (key === 'document_id') {
    return '填写 document_id；只有页面 URL 时可先用搜索动作获取文档 ID';
  }
  if (typeof property.description === 'string') {
    return property.description;
  }
  return undefined;
}

function renderSchemaInput(
  action: PluginActionRecord,
  key: string,
  property: Record<string, unknown>,
) {
  if (isInternalDataSourceAction(action) && key === 'source_types') {
    return <Select mode="multiple" options={internalDataSourceTypeOptions} placeholder="请选择源数据" />;
  }
  if (isInternalDataSourceAction(action) && (key === 'window_start' || key === 'window_end')) {
    return (
      <Select
        allowClear
        optionFilterProp="label"
        options={internalDataSourceWindowOptions}
        placeholder={`请选择${inputLabel(key, property)}`}
        showSearch
      />
    );
  }
  if (Array.isArray(property.enum)) {
    return <Select options={property.enum.map((value) => ({ label: String(value), value }))} />;
  }
  const type = property.type;
  if (type === 'integer' || type === 'number') {
    return <InputNumber min={0} placeholder={inputPlaceholder(key, property)} style={{ width: '100%' }} />;
  }
  if (type === 'boolean') {
    return (
      <Select
        allowClear
        options={[
          { label: '是', value: true },
          { label: '否', value: false },
        ]}
        placeholder={inputPlaceholder(key, property)}
      />
    );
  }
  return <Input placeholder={inputPlaceholder(key, property)} />;
}

function DataSourceActionParameters({
  action,
}: {
  action?: PluginActionRecord;
}) {
  if (!action) {
    return null;
  }
  const properties = schemaProperties(action);
  const entries = Object.entries(properties).slice(0, 6);
  if (!entries.length) {
    return (
      <Typography.Text type="secondary">
        当前读取动作未声明参数 Schema，如需传参可在动作模板中维护输入字段。
      </Typography.Text>
    );
  }
  const requiredFields = requiredSchemaFields(action);
  return (
    <Row gutter={12}>
      {entries.map(([key, property]) => (
        <Col key={key} span={key === 'document_id' ? 24 : 12}>
          <Form.Item
            label={inputLabel(key, property)}
            name={['plugin_input_mapping', key]}
            rules={requiredFields.has(key) ? [{ required: true, message: `请填写${inputLabel(key, property)}` }] : []}
          >
            {renderSchemaInput(action, key, property)}
          </Form.Item>
        </Col>
      ))}
    </Row>
  );
}

export function ScheduledJobDataConnectionSection({
  filteredPluginConnections,
  onPluginConnectionChange,
  pluginActions,
  requiredForPluginResource,
  usesNativeScan,
}: {
  filteredPluginConnections: PluginConnectionRecord[];
  onPluginConnectionChange: (value: unknown) => void;
  pluginActions: PluginActionRecord[];
  requiredForPluginResource: (message: string) => FormRule;
  usesNativeScan: boolean;
}) {
  return (
    <ScheduledJobFormSection label="数据来源" marker="输入">
      <Form.Item label="数据来源方式" name="data_source_mode">
        <Radio.Group
          optionType="button"
          options={dataSourceModeOptions}
        />
      </Form.Item>
      <Form.Item noStyle shouldUpdate>
        {({ getFieldValue }) => {
          const dataSourceMode = String(getFieldValue('data_source_mode') ?? 'direct_connection');
          const selectableConnections = displayConnections(filteredPluginConnections);
          const selectedConnectionIds = stringArray(getFieldValue('plugin_connection_ids'));
          const selectedPluginIds = new Set(
            selectedConnectionIds
              .map((connectionId) =>
                filteredPluginConnections.find((connection) => connection.id === connectionId)?.plugin_id,
              )
              .filter((pluginId): pluginId is string => Boolean(pluginId)),
          );
          const candidateActions = selectedPluginIds.size
            ? pluginActions.filter((action) => selectedPluginIds.has(action.plugin_id))
            : pluginActions;
          const readActions = candidateActions.filter(isReadAction);
          const actionOptions = (readActions.length ? readActions : candidateActions).map((action) => ({
            label: actionLabel(action),
            value: action.id,
          }));
          const selectedActionId = stringArray(getFieldValue('plugin_action_ids'))[0];
          const selectedAction = selectedActionId
            ? pluginActions.find((action) => action.id === selectedActionId)
            : undefined;
          const usesInternalDataSource = isInternalDataSourceAction(selectedAction);
          const connectionFieldLabel = dataSourceMode === 'authorized_read_action' ? '授权连接' : '取数连接';
          const actionLabelText = '数据读取动作';
          return (
            <>
              <Form.Item
                label={connectionFieldLabel}
                name="plugin_connection_ids"
                rules={[requiredForPluginResource(`请选择${connectionFieldLabel}`)]}
                extra={
                  usesNativeScan
                    ? '可选 GitHub/GitLab 凭据连接；代码 URL 仍以产品代码库配置为准'
                    : dataSourceMode === 'authorized_read_action'
                      ? '用于钉钉文档、GitHub、GitLab、邮箱等授权型连接，具体读取对象由下方读取动作参数决定'
                      : '用于内部业务数据、用户反馈、AI 客服聊天记录、HTTP API 等直接取数连接，可选择多个同类连接'
                }
              >
                <Select
                  allowClear
                  mode="multiple"
                  maxTagCount={2}
                  onChange={onPluginConnectionChange}
                  optionFilterProp="label"
                  placeholder={usesNativeScan ? '请选择 Git 凭据连接，可留空' : `请选择${connectionFieldLabel}`}
                  showSearch
                  options={selectableConnections.map((connection) => ({
                    label: connectionLabel(connection),
                    value: connection.id,
                  }))}
                />
              </Form.Item>
              {!usesNativeScan ? (
                <Form.Item
                  label={actionLabelText}
                  name="plugin_action_ids"
                  rules={[requiredForPluginResource(`请选择${actionLabelText}`)]}
                  extra={
                    dataSourceMode === 'authorized_read_action'
                      ? '例如读取指定钉钉文档、搜索钉钉文档、查询仓库或收取邮件'
                      : '仅用于调用所选连接获取原始数据，并携带默认结果映射；结果写入请在下方结果动作中配置'
                  }
                >
                  <Select
                    allowClear
                    maxTagCount={2}
                    mode="multiple"
                    optionFilterProp="label"
                    placeholder={`请选择${actionLabelText}`}
                    showSearch
                    options={actionOptions}
                  />
                </Form.Item>
              ) : null}
              {!usesNativeScan && (dataSourceMode === 'authorized_read_action' || usesInternalDataSource) ? (
                <DataSourceActionParameters action={selectedAction} />
              ) : null}
              {usesInternalDataSource ? (
                <Alert
                  showIcon
                  type="info"
                  title="AI 将从用户洞察中识别高价值、可落地的改进方向，并创建到所选产品的需求池。"
                />
              ) : null}
            </>
          );
        }}
      </Form.Item>
    </ScheduledJobFormSection>
  );
}
