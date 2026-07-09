import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { Alert, Button, Form, Input, Select, Space, Typography } from 'antd';

import { ScheduledJobFormSection } from './ScheduledJobFormSection';

const notificationChannelOptions = [
  { label: '邮件', value: 'email' },
  { label: '钉钉机器人', value: 'dingtalk' },
];

export function ScheduledJobActionConfigSection({
  codeInspectionResultActionOptions,
  genericResultActionOptions,
  isCodeInspectionJob,
  isGenericResultActionJob,
  severityThresholdOptions,
}: {
  codeInspectionResultActionOptions: Array<{ label: string; value: string }>;
  genericResultActionOptions: Array<{ label: string; value: string }>;
  isCodeInspectionJob: boolean;
  isGenericResultActionJob: boolean;
  severityThresholdOptions: Array<{ label: string; value: string }>;
}) {
  const resultActionOptions = isCodeInspectionJob
    ? codeInspectionResultActionOptions
    : genericResultActionOptions;
  const showResultActions = isCodeInspectionJob || isGenericResultActionJob;

  return (
    <ScheduledJobFormSection label="结果动作" marker="输出">
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
      ) : (
        <Alert
          showIcon
          type="info"
          title="当前作业使用数据来源动作的结果映射生成写入反馈"
        />
      )}
    </ScheduledJobFormSection>
  );
}
