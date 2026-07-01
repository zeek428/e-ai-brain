import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { Alert, Button, Checkbox, Form, Input, InputNumber, Select, Space, Switch } from 'antd';

import { type PluginConnectionSchemaFieldRecord, type PluginConnectionSchemaRecord } from '../../../services/aiBrain';
import { parseGitLabProjectAddress, parseGitRepositoryAddress } from './pluginConnectionAddressHelpers';

type SystemVariableOption = {
  description?: string;
  label: string;
  value: string;
};

const requestParameterTypeOptions = [
  { label: 'string', value: 'string' },
  { label: 'number', value: 'number' },
  { label: 'boolean', value: 'boolean' },
];

type RequestParameterRowsProps = {
  addText: string;
  name: 'connection_header_rows' | 'connection_param_rows' | 'header_rows' | 'param_rows';
  namePlaceholder: string;
  systemVariableOptions: SystemVariableOption[];
  title: string;
  valuePlaceholder: string;
};

export function RequestParameterRows({
  addText,
  name,
  namePlaceholder,
  systemVariableOptions,
  title,
  valuePlaceholder,
}: RequestParameterRowsProps) {
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

function normalizeSchemaOptions(field: PluginConnectionSchemaFieldRecord) {
  return (field.options ?? []).map((option) => (
    typeof option === 'string' ? { label: option, value: option } : option
  ));
}

function stringValues(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).filter(Boolean);
  }
  if (typeof value === 'string') {
    return value.split(',').map((item) => item.trim()).filter(Boolean);
  }
  return value ? [String(value)] : [];
}

function isSchemaFieldVisible(
  field: PluginConnectionSchemaFieldRecord,
  selectedSourceTypes: unknown,
) {
  const requiredSourceTypes = field.visible_when_source_types ?? [];
  if (requiredSourceTypes.length === 0) {
    return true;
  }
  const selected = new Set(stringValues(selectedSourceTypes));
  return requiredSourceTypes.some((sourceType) => selected.has(sourceType));
}

type ConnectionSchemaFieldsProps = {
  pluginCode?: string;
  schema?: PluginConnectionSchemaRecord;
  systemVariableOptions: SystemVariableOption[];
};

export function ConnectionSchemaFields({
  pluginCode,
  schema,
  systemVariableOptions,
}: ConnectionSchemaFieldsProps) {
  const form = Form.useFormInstance();
  const watchedSourceTypes = Form.useWatch(['schema_values', 'source_types'], form);
  const selectedSourceTypes = watchedSourceTypes
    ?? form.getFieldValue(['schema_values', 'source_types']);
  const sections = schema?.sections ?? [];
  if (!sections.length) {
    return null;
  }

  return (
    <Space orientation="vertical" size={12} style={{ width: '100%' }}>
      {pluginCode === 'github' ? (
        <Alert
          description="Params 属于高级查询参数，只有需要补充 GitHub API query 时再填写，例如 state、per_page、ref。Headers 默认保留 Accept 和 X-GitHub-Api-Version。"
          showIcon
          title="GitHub 连接只需要粘贴仓库地址；系统会自动解析 owner/repo，Params 不用再填。"
          type="info"
        />
      ) : null}
      {pluginCode === 'gitlab' ? (
        <Alert
          description="填写本地 GitLab 项目地址后，系统会自动同步 Endpoint URL，并解析 project_id/project_path 给 GitLab API 使用。Params 只用于补充额外查询参数。"
          showIcon
          title="GitLab 连接只需要粘贴本地项目地址。"
          type="info"
        />
      ) : null}
      {pluginCode === 'internal_data_source' ? (
        <Alert
          description="该连接不需要 Endpoint、认证、Params 或 Headers；只需选择要读取的内部业务数据源。常用按源过滤可直接在下方表单选择，高级过滤 JSON 仅用于补充更细粒度 source_filters。"
          showIcon
          title="内部数据源用于读取 AI Brain 内部业务数据。"
          type="info"
        />
      ) : null}
      {sections.map((section) => {
        const visibleFields = (section.fields ?? []).filter((field) => (
          isSchemaFieldVisible(field, selectedSourceTypes)
        ));
        if (visibleFields.length === 0) {
          return null;
        }
        return (
          <Space key={section.key} orientation="vertical" size={8} style={{ width: '100%' }}>
            <div style={{ color: '#53627a', fontWeight: 600 }}>{section.title}</div>
            <Space wrap align="start">
              {visibleFields.map((field) => {
                const rules = [
                  ...(field.required ? [{ required: true, message: `请输入${field.label}` }] : []),
                  ...(field.type === 'github_repository_url'
                    ? [{
                      validator: (_: unknown, value: unknown) => (
                        !value || parseGitRepositoryAddress(value)
                          ? Promise.resolve()
                          : Promise.reject(new Error(
                            '请输入有效的 GitHub 仓库地址，例如 https://github.com/acme/ai-brain.git',
                          ))
                      ),
                    }]
                    : []),
                  ...(field.type === 'gitlab_project_url'
                    ? [{
                      validator: (_: unknown, value: unknown) => (
                        !value || parseGitLabProjectAddress(value)
                          ? Promise.resolve()
                          : Promise.reject(new Error(
                            '请输入有效的 GitLab 地址，例如 http://gitlab.local/acme/ai-brain.git',
                          ))
                      ),
                    }]
                    : []),
                ];
                const fieldName = ['schema_values', field.key];
                const schemaOptions = normalizeSchemaOptions(field);
                const control = field.type === 'multi_select' && schemaOptions.length > 0 ? (
                  <Select
                    mode="multiple"
                    options={schemaOptions}
                    placeholder={field.placeholder || field.label}
                    style={{ minWidth: 320 }}
                  />
                ) : field.type === 'select' && schemaOptions.length > 0 ? (
                  <Select
                    allowClear={!field.required}
                    options={schemaOptions}
                    placeholder={field.placeholder || field.label}
                    style={{ width: 240 }}
                  />
                ) : field.type === 'number' ? (
                  <InputNumber placeholder={field.placeholder || field.label} style={{ width: 240 }} />
                ) : field.type === 'boolean' ? (
                  <Switch />
                ) : (
                  <Input
                    placeholder={field.placeholder || field.label}
                    style={{
                      width: ['github_repository_url', 'gitlab_project_url'].includes(field.type ?? '')
                        ? 420
                        : 240,
                    }}
                  />
                );
                return (
                  <Space key={field.key} align="baseline" size={6}>
                    <Form.Item
                      extra={field.description}
                      label={field.label}
                      name={fieldName}
                      rules={rules.length ? rules : undefined}
                      style={{ marginBottom: 8 }}
                      valuePropName={field.type === 'boolean' ? 'checked' : 'value'}
                    >
                      {control}
                    </Form.Item>
                    {field.supports_system_variables ? (
                      <Select
                        allowClear
                        options={systemVariableOptions}
                        placeholder="系统变量"
                        style={{ width: 190, marginTop: 30 }}
                        onChange={(value) => {
                          if (value) {
                            form.setFieldValue(fieldName, value);
                          }
                        }}
                      />
                    ) : null}
                  </Space>
                );
              })}
            </Space>
          </Space>
        );
      })}
    </Space>
  );
}
