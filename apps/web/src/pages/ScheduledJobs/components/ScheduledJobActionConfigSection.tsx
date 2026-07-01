import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Form, Input, Select, Space, Typography } from 'antd';
import type { FormItemProps } from 'antd';

import type { PluginActionRecord } from '../../../services/aiBrain';
import { ScheduledJobFormSection } from './ScheduledJobFormSection';

type FormRule = NonNullable<FormItemProps['rules']>[number];

const notificationChannelOptions = [
  { label: '邮件', value: 'email' },
  { label: '钉钉机器人', value: 'dingtalk' },
];

export function ScheduledJobActionConfigSection({
  codeInspectionResultActionOptions,
  genericResultActionOptions,
  isCodeInspectionJob,
  isGenericResultActionJob,
  pluginActions,
  requiredForPluginResource,
  severityThresholdOptions,
  usesNativeScan,
  writeStrategyLabelFromAction,
}: {
  codeInspectionResultActionOptions: Array<{ label: string; value: string }>;
  genericResultActionOptions: Array<{ label: string; value: string }>;
  isCodeInspectionJob: boolean;
  isGenericResultActionJob: boolean;
  pluginActions: PluginActionRecord[];
  requiredForPluginResource: (message: string) => FormRule;
  severityThresholdOptions: Array<{ label: string; value: string }>;
  usesNativeScan: boolean;
  writeStrategyLabelFromAction: (action: PluginActionRecord) => string;
}) {
  const writeStrategyExtra = usesNativeScan
    ? '本地完整扫描使用下方结果动作写入代码巡检报告'
    : '选择结果写到哪里或通知到哪里，后台按配置顺序执行对应动作';

  const resultActionOptions = isCodeInspectionJob
    ? codeInspectionResultActionOptions
    : genericResultActionOptions;
  const showResultActions = isCodeInspectionJob || isGenericResultActionJob;

  return (
    <ScheduledJobFormSection label="动作配置" marker="输出">
      <Form.Item
        label="写入策略"
        name="plugin_action_ids"
        rules={[requiredForPluginResource('请选择写入策略')]}
        extra={writeStrategyExtra}
      >
        <Select
          allowClear
          disabled={usesNativeScan}
          mode="multiple"
          maxTagCount={2}
          optionFilterProp="label"
          placeholder="请选择写入策略"
          showSearch
          options={pluginActions.map((action) => ({
            label: writeStrategyLabelFromAction(action),
            value: action.id,
          }))}
        />
      </Form.Item>
      {showResultActions ? (
        <Form.List name="result_actions">
          {(fields, { add, remove }) => (
            <Space orientation="vertical" size={8} style={{ width: '100%' }}>
              <Typography.Text strong>结果动作</Typography.Text>
              {fields.map(({ key, ...field }) => (
                <Space key={key} align="start" size={8} style={{ width: '100%' }}>
                  <Form.Item
                    {...field}
                    name={[field.name, 'type']}
                    rules={[{ required: true, message: '请选择结果动作' }]}
                    style={{ flex: 1, marginBottom: 8 }}
                  >
                    <Select options={resultActionOptions} placeholder="请选择结果动作" />
                  </Form.Item>
                  <Form.Item noStyle shouldUpdate>
                    {({ getFieldValue }) => {
                      const actionType = getFieldValue(['result_actions', field.name, 'type']);
                      if (
                        actionType === 'create_bug_for_severe_findings'
                        || actionType === 'create_task_for_severe_findings'
                      ) {
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
                          <Space orientation="vertical" size={8} style={{ width: 360 }}>
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
              <Button
                icon={<PlusOutlined />}
                onClick={() => add({ type: isCodeInspectionJob ? 'write_code_inspection_report' : 'save_scheduled_job_result' })}
              >
                新增结果动作
              </Button>
            </Space>
          )}
        </Form.List>
      ) : null}
    </ScheduledJobFormSection>
  );
}
