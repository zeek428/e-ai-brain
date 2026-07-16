import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { Alert, Button, Form, Input, Select, Space, Typography } from 'antd';

import type { PluginActionRecord, PluginConnectionRecord } from '../../../services/aiBrain';
import { ScheduledJobFormSection } from './ScheduledJobFormSection';

const notificationChannelOptions = [
  { label: '邮件', value: 'email' },
  { label: '钉钉机器人', value: 'dingtalk' },
];

function ScheduledJobResultActionFields({
  dingtalkActionOptions,
  fieldName,
  pluginConnectionOptions,
  severityThresholdOptions,
}: {
  dingtalkActionOptions: Array<{ label: string; value: string }>;
  fieldName: number;
  pluginConnectionOptions: Array<{ label: string; value: string }>;
  severityThresholdOptions: Array<{ label: string; value: string }>;
}) {
  const actionType = Form.useWatch(['result_actions', fieldName, 'type']);

  if (
    actionType === 'create_bug_for_severe_findings'
    || actionType === 'create_task_for_severe_findings'
  ) {
    return (
      <Form.Item name={[fieldName, 'severity_threshold']} style={{ marginBottom: 8, width: 150 }}>
        <Select options={severityThresholdOptions} placeholder="严重级别" />
      </Form.Item>
    );
  }
  if (actionType === 'send_notification') {
    return (
      <Space orientation="vertical" size={8} style={{ width: 360 }}>
        <Form.Item
          name={[fieldName, 'channels']}
          rules={[{ required: true, message: '请选择通知渠道' }]}
          style={{ marginBottom: 0 }}
        >
          <Select mode="multiple" options={notificationChannelOptions} placeholder="通知渠道" />
        </Form.Item>
        <Form.Item name={[fieldName, 'recipients']} style={{ marginBottom: 0 }}>
          <Select mode="tags" placeholder="邮件收件人" tokenSeparators={[',', '，']} />
        </Form.Item>
        <Form.Item name={[fieldName, 'webhook_url']} style={{ marginBottom: 8 }}>
          <Input placeholder="钉钉机器人 Webhook" />
        </Form.Item>
      </Space>
    );
  }
  if (actionType === 'create_requirements' || actionType === 'write_internal_user_insights') {
    return null;
  }
  if (actionType === 'sync_dingtalk_document') {
    return (
      <Space orientation="vertical" size={8} style={{ width: '100%' }}>
        <div
          style={{
            display: 'grid',
            gap: 8,
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            width: '100%',
          }}
        >
          <Form.Item
            name={[fieldName, 'plugin_action_id']}
            rules={[{ required: true, message: '请选择钉钉更新动作' }]}
            style={{ marginBottom: 0 }}
          >
            <Select
              options={dingtalkActionOptions}
              placeholder="钉钉文档 - 更新内容"
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item name={[fieldName, 'plugin_connection_id']} style={{ marginBottom: 0 }}>
            <Select
              allowClear
              options={pluginConnectionOptions}
              placeholder="钉钉连接"
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
        </div>
        <div
          style={{
            display: 'grid',
            gap: 8,
            gridTemplateColumns: 'minmax(180px, 1fr) minmax(100px, 120px)',
            width: '100%',
          }}
        >
          <Form.Item
            name={[fieldName, 'document_id']}
            rules={[{ required: true, message: '请输入钉钉文档链接或 ID' }]}
            style={{ marginBottom: 0 }}
          >
            <Input placeholder="钉钉文档链接或 ID" />
          </Form.Item>
          <Form.Item name={[fieldName, 'write_mode']} initialValue="append" style={{ marginBottom: 0 }}>
            <Select
              options={[
                { label: '追加', value: 'append' },
                { label: '覆盖', value: 'overwrite' },
              ]}
            />
          </Form.Item>
        </div>
        <Form.Item
          name={[fieldName, 'content_template']}
          initialValue="{{dingtalk_markdown}}"
          style={{ marginBottom: 8 }}
        >
          <Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} placeholder="写入内容模板" />
        </Form.Item>
      </Space>
    );
  }

  return null;
}

export function ScheduledJobActionConfigSection({
  codeInspectionResultActionOptions,
  genericResultActionOptions,
  isCodeInspectionJob,
  isGenericResultActionJob,
  selectedJobType,
  pluginActions,
  pluginConnections,
  severityThresholdOptions,
}: {
  codeInspectionResultActionOptions: Array<{ label: string; value: string }>;
  genericResultActionOptions: Array<{ label: string; value: string }>;
  isCodeInspectionJob: boolean;
  isGenericResultActionJob: boolean;
  selectedJobType?: string;
  pluginActions: PluginActionRecord[];
  pluginConnections: PluginConnectionRecord[];
  severityThresholdOptions: Array<{ label: string; value: string }>;
}) {
  const supportsDingtalkDocumentSync = [
    'plugin_action_invoke',
    'user_feedback_insight_extract',
  ].includes(selectedJobType ?? '');
  const isUserFeedbackInsightJob = selectedJobType === 'user_feedback_insight_extract';
  const visibleGenericResultActionOptions = genericResultActionOptions.filter((option) => {
    if (option.value === 'create_requirements') {
      return selectedJobType === 'plugin_action_invoke';
    }
    if (option.value === 'write_internal_user_insights') {
      return selectedJobType === 'plugin_action_invoke';
    }
    if (option.value === 'sync_dingtalk_document') {
      return supportsDingtalkDocumentSync;
    }
    return true;
  });
  const resultActionOptions = isCodeInspectionJob
    ? codeInspectionResultActionOptions
    : visibleGenericResultActionOptions;
  const showResultActions = isCodeInspectionJob || isGenericResultActionJob;
  const dingtalkActionOptions = pluginActions
    .filter((action) => {
      const mapping = action.result_mapping ?? {};
      const text = `${action.code ?? ''} ${action.name ?? ''}`.toLowerCase();
      return mapping.write_target === 'dingtalk_document' || text.includes('dingtalk') || text.includes('钉钉');
    })
    .map((action) => ({ label: `${action.name} (${action.code})`, value: action.id }));
  const pluginConnectionOptions = pluginConnections.map((connection) => ({
    label: `${connection.name} (${connection.status ?? '-'})`,
    value: connection.id,
  }));

  return (
    <ScheduledJobFormSection label="结果动作" marker="输出">
      {showResultActions ? (
        <Form.List name="result_actions">
          {(fields, { add, remove }) => (
            <Space orientation="vertical" size={8} style={{ width: '100%' }}>
              <Typography.Text strong>结果动作</Typography.Text>
              {isUserFeedbackInsightJob ? (
                <Alert
                  showIcon
                  type="info"
                  title="用户洞察会在 AI 分析成功后自动写入"
                  description="此处仅配置额外输出，例如同步钉钉文档或发送通知；不需要配置代码巡检报告或创建 Bug。"
                />
              ) : null}
              {fields.map(({ key, ...field }) => (
                <Space key={key} align="start" size={8} style={{ width: '100%' }}>
                  <Form.Item
                    {...field}
                    name={[field.name, 'type']}
                    rules={[{ required: true, message: '请选择结果动作' }]}
                    style={{ flex: 1, marginBottom: 8 }}
                  >
                    <Select
                      aria-label="结果动作类型"
                      options={resultActionOptions}
                      placeholder="请选择结果动作"
                    />
                  </Form.Item>
                  <ScheduledJobResultActionFields
                    dingtalkActionOptions={dingtalkActionOptions}
                    fieldName={field.name}
                    pluginConnectionOptions={pluginConnectionOptions}
                    severityThresholdOptions={severityThresholdOptions}
                  />
                  <Button danger icon={<DeleteOutlined />} onClick={() => remove(field.name)} />
                </Space>
              ))}
              <Button
                icon={<PlusOutlined />}
                onClick={() => add({ type: isCodeInspectionJob ? 'write_code_inspection_report' : 'save_scheduled_job_result' })}
              >
                新增结果动作
              </Button>
              {supportsDingtalkDocumentSync ? (
                <Button
                  icon={<PlusOutlined />}
                  onClick={() => add({
                    content_template: '{{dingtalk_markdown}}',
                    type: 'sync_dingtalk_document',
                    write_mode: 'append',
                  })}
                >
                  新增钉钉文档更新
                </Button>
              ) : null}
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
