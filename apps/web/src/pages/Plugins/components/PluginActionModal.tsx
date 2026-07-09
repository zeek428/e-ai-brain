import type { FormInstance } from 'antd';
import { Button, Form, Input, InputNumber, Modal, Select, Space, Switch, Typography } from 'antd';

import type { ResultWriteTargetRecord } from '../../../services/aiBrain';
import {
  RequestParameterRows,
} from './PluginConnectionFormFields';
import {
  compactJson,
} from './pluginDiagnosticsHelpers';

type RequestParameterRow = {
  description?: string;
  enabled?: boolean;
  name?: string;
  type?: 'boolean' | 'number' | 'string';
  value?: string;
};

export type PluginActionFormValues = {
  action_type: string;
  branch_path?: string;
  code: string;
  commit_sha_path?: string;
  content_template?: string;
  connection_id?: string;
  delivery_id_path?: string;
  delivery_status_path?: string;
  description?: string;
  document_id?: string;
  document_id_path?: string;
  findings_path?: string;
  header_rows?: RequestParameterRow[];
  insights_path?: string;
  max_rows?: number;
  method?: string;
  name: string;
  param_rows?: RequestParameterRow[];
  path?: string;
  plugin_id?: string;
  request_config?: string;
  requires_human_review: boolean;
  records_imported_path?: string;
  recipients_path?: string;
  repository_id_path?: string;
  result_mapping?: string;
  risk_level_path?: string;
  rows_path?: string;
  returned_fields?: string;
  scenario?: string;
  status: string;
  status_path?: string;
  subject_path?: string;
  summary_path?: string;
  table_name?: string;
  time_field?: string;
  write_mode?: string;
  write_target?: string;
};

type SelectOption = {
  label: string;
  value: string;
};

type SystemVariableOption = SelectOption & {
  description?: string;
};

type PluginActionModalProps = {
  actionScenario?: string;
  advancedJsonOpen: boolean;
  connectionOptions: SelectOption[];
  defaultWriteTarget: string;
  form: FormInstance<PluginActionFormValues>;
  isEditing: boolean;
  maxComputeScenario: string;
  onApplyJsonToVisual: () => void;
  onCancel: () => void;
  onSubmit: () => void | Promise<void>;
  onSyncJsonFromVisual: () => void;
  onToggleAdvancedJson: () => void;
  onValuesChange: (
    changedValues: Partial<PluginActionFormValues>,
    allValues: PluginActionFormValues,
  ) => void;
  onWriteTargetChange: (writeTarget?: string) => void;
  open: boolean;
  requestPreview: Record<string, unknown>;
  resultWriteTargetOptions: SelectOption[];
  resultWriteTargets: ResultWriteTargetRecord[];
  scenarioOptions: SelectOption[];
  systemVariableOptions: SystemVariableOption[];
  onScenarioChange: (scenario?: string) => void;
};

const requestMethodOptions = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((value) => ({
  label: value,
  value,
}));

const HIDDEN_RESULT_MAPPING_FIELD_TARGETS = new Set(['user_feedback_insights']);

function resultWriteTargetRecordByCode(
  writeTargets: ResultWriteTargetRecord[],
  writeTarget: string | undefined,
  defaultWriteTarget: string,
) {
  return writeTargets.find((target) => target.code === (writeTarget || defaultWriteTarget));
}

function resultMappingFieldControl(field: ResultWriteTargetRecord['mapping_fields'][number]) {
  if (field.type === 'select') {
    return <Select options={field.options ?? []} placeholder={field.placeholder} style={{ width: 220 }} />;
  }
  if (field.type === 'textarea') {
    return <Input.TextArea placeholder={field.placeholder} rows={3} style={{ width: 460 }} />;
  }
  return <Input placeholder={field.placeholder} style={{ width: 220 }} />;
}

function ResultWriteTargetMappingFields({
  defaultWriteTarget,
  writeTarget,
  writeTargets,
}: {
  defaultWriteTarget: string;
  writeTarget?: string;
  writeTargets: ResultWriteTargetRecord[];
}) {
  const target = resultWriteTargetRecordByCode(writeTargets, writeTarget, defaultWriteTarget);
  if (target && HIDDEN_RESULT_MAPPING_FIELD_TARGETS.has(target.code)) {
    return null;
  }
  if (target?.mapping_fields.length) {
    return (
      <Space wrap>
        {target.mapping_fields.map((field) => (
          <Form.Item
            key={field.key}
            label={field.label}
            name={field.key}
            rules={field.required ? [{ required: true, message: `请输入${field.label}` }] : undefined}
          >
            {resultMappingFieldControl(field)}
          </Form.Item>
        ))}
      </Space>
    );
  }
  return null;
}

export function PluginActionModal({
  actionScenario,
  advancedJsonOpen,
  connectionOptions,
  defaultWriteTarget,
  form,
  isEditing,
  maxComputeScenario,
  onApplyJsonToVisual,
  onCancel,
  onScenarioChange,
  onSubmit,
  onSyncJsonFromVisual,
  onToggleAdvancedJson,
  onValuesChange,
  onWriteTargetChange,
  open,
  requestPreview,
  resultWriteTargetOptions,
  resultWriteTargets,
  scenarioOptions,
  systemVariableOptions,
}: PluginActionModalProps) {
  return (
    <Modal
      cancelText="取消"
      okText="确定"
      onCancel={onCancel}
      onOk={() => void onSubmit()}
      open={open}
      title={isEditing ? '编辑动作' : '新增动作'}
    >
      <Form
        form={form}
        initialValues={{
          action_type: 'http_request',
          method: 'GET',
          requires_human_review: false,
          status: 'active',
          write_target: defaultWriteTarget,
        }}
        layout="vertical"
        onValuesChange={onValuesChange}
      >
        <Form.Item label="配置场景" name="scenario">
          <Select
            allowClear
            onChange={onScenarioChange}
            options={scenarioOptions}
          />
        </Form.Item>
        <Form.Item hidden name="plugin_id">
          <Input type="hidden" />
        </Form.Item>
        <Form.Item label="连接" name="connection_id">
          <Select allowClear options={connectionOptions} />
        </Form.Item>
        <Form.Item label="结果写入目标" name="write_target">
          <Select options={resultWriteTargetOptions} onChange={onWriteTargetChange} />
        </Form.Item>
        <Form.Item noStyle shouldUpdate={(previous, current) => previous.write_target !== current.write_target}>
          {({ getFieldValue }) => {
            const writeTarget = getFieldValue('write_target');
            return (
              <ResultWriteTargetMappingFields
                defaultWriteTarget={defaultWriteTarget}
                writeTarget={writeTarget}
                writeTargets={resultWriteTargets}
              />
            );
          }}
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
        {actionScenario !== maxComputeScenario ? (
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
              systemVariableOptions={systemVariableOptions}
              title="Params"
              valuePlaceholder="参数值"
            />
            <RequestParameterRows
              addText="添加 Headers"
              name="header_rows"
              namePlaceholder="Header 名"
              systemVariableOptions={systemVariableOptions}
              title="Headers"
              valuePlaceholder="Header 值"
            />
          </>
        ) : null}
        {actionScenario === maxComputeScenario ? (
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
        <Button onClick={onToggleAdvancedJson} type="link">
          高级 JSON 修改
        </Button>
        {!advancedJsonOpen ? (
          <>
            <Form.Item hidden name="request_config">
              <Input type="hidden" />
            </Form.Item>
            <Form.Item hidden name="result_mapping">
              <Input type="hidden" />
            </Form.Item>
          </>
        ) : null}
        {advancedJsonOpen ? (
          <>
            <Space style={{ marginBottom: 8 }}>
              <Button onClick={onSyncJsonFromVisual}>同步可视化到 JSON</Button>
              <Button onClick={onApplyJsonToVisual}>从 JSON 应用到 Params / Headers</Button>
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
  );
}
