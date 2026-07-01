import { PlayCircleOutlined } from '@ant-design/icons';
import type { FormInstance } from 'antd';
import { Button, Form, Input, InputNumber, Modal, Select, Space } from 'antd';

import type {
  PluginConnectionSchemaRecord,
} from '../../../services/aiBrain';
import {
  ConnectionSchemaFields,
  RequestParameterRows,
} from './PluginConnectionFormFields';

type RequestParameterRow = {
  description?: string;
  enabled?: boolean;
  name?: string;
  type?: 'boolean' | 'number' | 'string';
  value?: string;
};

export type PluginConnectionFormValues = {
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
  schema_values?: Record<string, unknown>;
  secret_ref?: string;
  status: string;
  timeout_seconds: number;
  token_ref?: string;
  username_ref?: string;
};

type SelectOption = {
  label: string;
  value: string;
};

type SystemVariableOption = SelectOption & {
  description?: string;
};

type PluginConnectionModalProps = {
  advancedAuthJsonOpen: boolean;
  advancedRequestJsonOpen: boolean;
  authType?: string;
  connectionSubmitAction?: 'save' | 'save-test';
  form: FormInstance<PluginConnectionFormValues>;
  isEditing: boolean;
  isGithubConnection: boolean;
  onApplyAuthJsonToVisual: () => void;
  onApplyRequestJsonToVisual: () => void;
  onCancel: () => void;
  onPluginChange: (pluginId: string) => void;
  onSubmit: () => void | Promise<void>;
  onSubmitAndTest: () => void | Promise<void>;
  onSyncAuthJsonFromVisual: () => void;
  onSyncRequestJsonFromVisual: () => void;
  onToggleAdvancedAuthJson: () => void;
  onToggleAdvancedRequestJson: () => void;
  onValuesChange: (
    changedValues: Partial<PluginConnectionFormValues>,
    allValues: PluginConnectionFormValues,
  ) => void;
  open: boolean;
  pluginCode?: string;
  pluginOptions: SelectOption[];
  schema?: PluginConnectionSchemaRecord;
  systemVariableOptions: SystemVariableOption[];
};

export function PluginConnectionModal({
  advancedAuthJsonOpen,
  advancedRequestJsonOpen,
  authType,
  connectionSubmitAction,
  form,
  isEditing,
  isGithubConnection,
  onApplyAuthJsonToVisual,
  onApplyRequestJsonToVisual,
  onCancel,
  onPluginChange,
  onSubmit,
  onSubmitAndTest,
  onSyncAuthJsonFromVisual,
  onSyncRequestJsonFromVisual,
  onToggleAdvancedAuthJson,
  onToggleAdvancedRequestJson,
  onValuesChange,
  open,
  pluginCode,
  pluginOptions,
  schema,
  systemVariableOptions,
}: PluginConnectionModalProps) {
  return (
    <Modal
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button
          disabled={Boolean(connectionSubmitAction)}
          key="save"
          loading={connectionSubmitAction === 'save'}
          onClick={() => void onSubmit()}
        >
          确定
        </Button>,
        <Button
          aria-label="保存并测试"
          disabled={Boolean(connectionSubmitAction)}
          icon={<PlayCircleOutlined />}
          key="save-test"
          loading={connectionSubmitAction === 'save-test'}
          onClick={() => void onSubmitAndTest()}
          type="primary"
        >
          保存并测试
        </Button>,
      ]}
      onCancel={onCancel}
      onOk={() => void onSubmit()}
      open={open}
      title={isEditing ? '编辑连接' : '新增连接'}
      width={860}
    >
      <Form
        form={form}
        initialValues={{
          auth_type: 'none',
          environment: 'default',
          max_retries: 0,
          status: 'active',
          timeout_seconds: 30,
        }}
        layout="vertical"
        onValuesChange={onValuesChange}
      >
        <Form.Item label="插件" name="plugin_id" rules={[{ required: true }]}>
          <Select onChange={onPluginChange} options={pluginOptions} />
        </Form.Item>
        <Form.Item label="名称" name="name" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item label="Endpoint URL" name="endpoint_url" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item hidden name="environment">
          <Input type="hidden" />
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
        {!advancedAuthJsonOpen && authType === 'api_key_header' ? (
          <Space wrap>
            <Form.Item label="Header 名" name="header_name">
              <Input placeholder="Authorization" />
            </Form.Item>
            <Form.Item label="Header 值/密钥引用" name="secret_ref">
              <Input placeholder="vault/path/to/token 或 APPCODE xxx" style={{ width: 320 }} />
            </Form.Item>
          </Space>
        ) : null}
        {!advancedAuthJsonOpen && authType === 'bearer' ? (
          <Form.Item
            extra={
              isGithubConnection
                ? '填写 GitHub Personal Access Token，或平台可解析的密钥引用。本地联调可直接填 ghp_xxx；生产建议填 vault/github/token 或 env:GITHUB_TOKEN。'
                : '填写 Bearer Token 或平台可解析的密钥引用。'
            }
            label="Token / 密钥引用"
            name="token_ref"
            rules={
              isGithubConnection
                ? [{ required: true, message: '请填写 GitHub Token 或密钥引用' }]
                : undefined
            }
          >
            <Input placeholder="ghp_xxx / vault/github/token / env:GITHUB_TOKEN" />
          </Form.Item>
        ) : null}
        {!advancedAuthJsonOpen && authType === 'basic' ? (
          <Space wrap>
            <Form.Item label="用户名引用" name="username_ref">
              <Input placeholder="vault/path/to/username" />
            </Form.Item>
            <Form.Item label="密码引用" name="password_ref">
              <Input placeholder="vault/path/to/password" />
            </Form.Item>
          </Space>
        ) : null}
        <Button onClick={onToggleAdvancedAuthJson} type="link">
          高级认证 JSON 修改
        </Button>
        {advancedAuthJsonOpen ? (
          <>
            <Space style={{ marginBottom: 8 }}>
              <Button onClick={onSyncAuthJsonFromVisual}>同步可视化到 JSON</Button>
              <Button onClick={onApplyAuthJsonToVisual}>从 JSON 应用到字段</Button>
            </Space>
            <Form.Item label="认证配置 JSON" name="auth_config">
              <Input.TextArea
                placeholder='{"header_name":"PRIVATE-TOKEN","secret_ref":"vault/gitlab/token"}'
                rows={4}
              />
            </Form.Item>
          </>
        ) : null}
        <ConnectionSchemaFields
          pluginCode={pluginCode}
          schema={schema}
          systemVariableOptions={systemVariableOptions}
        />
        <RequestParameterRows
          addText="添加 Params"
          name="connection_param_rows"
          namePlaceholder="参数名"
          systemVariableOptions={systemVariableOptions}
          title="高级查询 Params"
          valuePlaceholder="参数值"
        />
        <RequestParameterRows
          addText="添加 Headers"
          name="connection_header_rows"
          namePlaceholder="Header 名"
          systemVariableOptions={systemVariableOptions}
          title="Headers"
          valuePlaceholder="Header 值"
        />
        <Button onClick={onToggleAdvancedRequestJson} type="link">
          高级请求 JSON 修改
        </Button>
        {advancedRequestJsonOpen ? (
          <>
            <Space style={{ marginBottom: 8 }}>
              <Button onClick={onSyncRequestJsonFromVisual}>同步可视化到 JSON</Button>
              <Button onClick={onApplyRequestJsonToVisual}>从 JSON 应用到 Params / Headers</Button>
            </Space>
            <Form.Item label="请求配置 JSON" name="request_config">
              <Input.TextArea
                placeholder='{"query":{"start_pt":"{{current_date-7}}"},"headers":{"Authorization":"APPCODE xxx"}}'
                rows={4}
              />
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
  );
}
