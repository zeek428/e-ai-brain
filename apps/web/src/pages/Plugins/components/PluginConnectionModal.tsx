import { PlayCircleOutlined } from '@ant-design/icons';
import type { FormInstance } from 'antd';
import { Alert, Button, Col, Form, Input, InputNumber, Modal, Row, Select, Space, Tag, Typography } from 'antd';

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
  query_key?: string;
  request_config?: string;
  request_method?: string;
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
  pluginProtocol?: string;
  pluginOptions: SelectOption[];
  productOptions: SelectOption[];
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
  pluginProtocol,
  pluginOptions,
  productOptions,
  schema,
  systemVariableOptions,
}: PluginConnectionModalProps) {
  const selectedPluginId = Form.useWatch('plugin_id', form);
  const selectedPluginOption = pluginOptions.find((option) => option.value === selectedPluginId);
  const isInternalDataSourceConnection = pluginCode === 'internal_data_source';
  const isGitlabConnection = pluginCode === 'gitlab';
  const isDingTalkConnection = pluginCode?.startsWith('dingtalk_') ?? false;
  const isHttpConnection = pluginProtocol === 'http'
    || ['email', 'github', 'gitlab'].includes(pluginCode ?? '')
    || selectedPluginOption?.label.endsWith('(http)') === true;
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
        {!isInternalDataSourceConnection ? (
          <Form.Item
            extra={
              isDingTalkConnection
                ? '从钉钉 AI Hub MCP 详情复制 StreamableHttp URL 或 JSON Config 中的 url，支持粘贴包含 key 的完整 URL。'
                : undefined
            }
            label={isDingTalkConnection ? 'StreamableHttp URL' : isHttpConnection ? '请求地址（Endpoint URL）' : 'Endpoint URL'}
            name="endpoint_url"
            rules={[{ required: true }]}
          >
            <Input
              placeholder={
                isDingTalkConnection
                  ? 'https://mcp-gw.dingtalk.com/server/<实例ID>?key=...'
                  : isHttpConnection
                    ? 'https://api.example.com/v1/resources'
                    : undefined
              }
            />
          </Form.Item>
        ) : (
          <Form.Item hidden name="endpoint_url">
            <Input type="hidden" />
          </Form.Item>
        )}
        <Form.Item hidden name="environment">
          <Input type="hidden" />
        </Form.Item>
        {!isInternalDataSourceConnection ? (
          <Form.Item label="认证" name="auth_type">
            <Select
              options={[
                { label: 'none', value: 'none' },
                { label: 'bearer', value: 'bearer' },
                { label: 'api_key_header', value: 'api_key_header' },
                { label: 'basic', value: 'basic' },
                { label: 'url_key', value: 'url_key' },
              ]}
            />
          </Form.Item>
        ) : (
          <Form.Item hidden name="auth_type">
            <Input type="hidden" />
          </Form.Item>
        )}
        {!isInternalDataSourceConnection && !advancedAuthJsonOpen && authType === 'api_key_header' ? (
          <Space wrap>
            <Form.Item label="Header 名" name="header_name">
              <Input placeholder="Authorization" />
            </Form.Item>
            <Form.Item
              extra={
                isGitlabConnection
                  ? '填写 GitLab Personal Access Token，或平台可解析的密钥引用。本地联调可直接填 glpat_xxx；生产建议填 vault/gitlab/token 或 env:GITLAB_TOKEN。'
                  : undefined
              }
              label="Header 值/密钥引用"
              name="secret_ref"
              rules={
                isGitlabConnection
                  ? [{ required: true, message: '请填写 GitLab Token 或密钥引用' }]
                  : undefined
              }
            >
              <Input placeholder="vault/path/to/token 或 APPCODE xxx" style={{ width: 320 }} />
            </Form.Item>
          </Space>
        ) : null}
        {!isInternalDataSourceConnection && !advancedAuthJsonOpen && authType === 'bearer' ? (
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
        {!isInternalDataSourceConnection && !advancedAuthJsonOpen && authType === 'basic' ? (
          <Space wrap>
            <Form.Item label="用户名引用" name="username_ref">
              <Input placeholder="vault/path/to/username" />
            </Form.Item>
            <Form.Item label="密码引用" name="password_ref">
              <Input placeholder="vault/path/to/password" />
            </Form.Item>
          </Space>
        ) : null}
        {!isInternalDataSourceConnection && !advancedAuthJsonOpen && authType === 'url_key' ? (
          <>
            {isDingTalkConnection ? (
              <Alert
                description={(
                  <Space orientation="vertical" size={6}>
                    <Space size={[6, 6]} wrap>
                      <Tag color="blue">个人授权</Tag>
                      <Tag color="blue">系统授权</Tag>
                      <Tag color="blue">应用授权</Tag>
                    </Space>
                    <Typography.Text>StreamableHttp URL 获取方式</Typography.Text>
                    <Typography.Text type="secondary">
                      完成钉钉 MCP 授权后优先复制完整 StreamableHttp URL；系统会自动提取 key。也可以填写不带 key 的 URL，并在下方填 Vault 引用，例如 vault/dingtalk/shared/url_key。
                    </Typography.Text>
                  </Space>
                )}
                showIcon
                style={{ marginBottom: 12 }}
                title="授权配置向导"
                type="info"
              />
            ) : null}
            <Row className="plugin-connection-url-key-grid" gutter={[16, 0]}>
              <Col className="plugin-connection-url-key-query" xs={24}>
                <Form.Item label="查询参数名" name="query_key">
                  <Input placeholder="key" />
                </Form.Item>
              </Col>
              <Col className="plugin-connection-url-key-secret" xs={24}>
                <Form.Item
                  extra={
                    isDingTalkConnection
                      ? '如果 StreamableHttp URL 已包含 key，这里可以留空；生产建议改用 vault/dingtalk/doc/key 或 env:DINGTALK_MCP_KEY。'
                      : '填写 URL 查询参数形式的密钥，保存后调用时会自动追加到请求 URL。'
                  }
                  label="URL Key / 密钥引用"
                  name="secret_ref"
                  rules={
                    isDingTalkConnection
                      ? [{
                        validator: (_: unknown, value: unknown) => {
                          const endpointUrl = String(form.getFieldValue('endpoint_url') ?? '');
                          const hasEndpointKey = /[?&]key=/.test(endpointUrl);
                          if (String(value ?? '').trim() || hasEndpointKey) {
                            return Promise.resolve();
                          }
                          return Promise.reject(new Error('请粘贴包含 key 的 StreamableHttp URL，或填写 URL Key / 密钥引用'));
                        },
                      }]
                      : undefined
                  }
                >
                  <Input placeholder="dingtalk key / vault/dingtalk/doc/key / env:DINGTALK_MCP_KEY" />
                </Form.Item>
              </Col>
            </Row>
          </>
        ) : null}
        {!isInternalDataSourceConnection ? (
          <Button onClick={onToggleAdvancedAuthJson} type="link">
            高级认证 JSON 修改
          </Button>
        ) : null}
        {!isInternalDataSourceConnection && advancedAuthJsonOpen ? (
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
          productOptions={productOptions}
          schema={schema}
          systemVariableOptions={systemVariableOptions}
        />
        {!isInternalDataSourceConnection ? (
          <>
            {isHttpConnection ? (
              <Form.Item
                extra="直接数据源可填写完整接口地址；GitHub、GitLab 等标准插件可保留基础地址，由动作场景补充固定请求路径。"
                label="请求方法"
                name="request_method"
              >
                <Select
                  options={['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((value) => ({ label: value, value }))}
                  placeholder="GET"
                  style={{ width: 180 }}
                />
              </Form.Item>
            ) : null}
            <RequestParameterRows
              addText="添加 Params"
              name="connection_param_rows"
              namePlaceholder="参数名"
              systemVariableOptions={systemVariableOptions}
              title="Params"
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
          </>
        ) : null}
        <Button onClick={onToggleAdvancedRequestJson} type="link">
          {isInternalDataSourceConnection ? '高级过滤 JSON 修改' : '高级请求 JSON 修改'}
        </Button>
        {advancedRequestJsonOpen ? (
          <>
            <Space style={{ marginBottom: 8 }}>
              <Button onClick={onSyncRequestJsonFromVisual}>
                {isInternalDataSourceConnection ? '同步源数据配置到 JSON' : '同步可视化到 JSON'}
              </Button>
              <Button onClick={onApplyRequestJsonToVisual}>
                {isInternalDataSourceConnection ? '从 JSON 应用到源数据字段' : '从 JSON 应用到 Params / Headers'}
              </Button>
            </Space>
            <Form.Item
              extra={
                isInternalDataSourceConnection
                  ? '可在这里补充每类源数据独立过滤 source_filters，例如只读取 P0 需求或 critical Bug。'
                  : undefined
              }
              label={isInternalDataSourceConnection ? '过滤配置 JSON' : '请求配置 JSON'}
              name="request_config"
            >
              <Input.TextArea
                placeholder={
                  isInternalDataSourceConnection
                    ? '{"query":{"source_filters":{"requirements":{"priority":"P0"},"bugs":{"severity":"critical"}}}}'
                    : '{"method":"GET","query":{"start_pt":"{{current_date-7}}"},"headers":{"Authorization":"APPCODE xxx"}}'
                }
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
