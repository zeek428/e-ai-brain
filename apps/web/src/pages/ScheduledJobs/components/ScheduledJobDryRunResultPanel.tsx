import { Alert, Space, Tag, Typography } from 'antd';

import type { ScheduledJobDryRunResult } from '../../../services/aiBrain';
import { ScheduledJobJsonPreview } from './ScheduledJobJsonPreview';

function recordValue(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function isRecordValue(value: Record<string, unknown> | undefined): value is Record<string, unknown> {
  return Boolean(value);
}

function stringValue(value: unknown): string | undefined {
  return typeof value === 'string' && value ? value : undefined;
}

function numberValue(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function previewSourceLabel(source: unknown): string {
  if (source === 'connection_test_response') {
    return '连接测试响应样例';
  }
  if (source === 'action_trial_response') {
    return '动作试运行响应';
  }
  if (source === 'skill_output_schema') {
    return 'Skill 输出样例';
  }
  if (source === 'data_connection_response') {
    return '数据连接响应';
  }
  if (source === 'not_available') {
    return '未生成';
  }
  return stringValue(source) ?? '-';
}

function actionPreviewLabel(action: Record<string, unknown>): string {
  return (
    stringValue(action.action_name)
    ?? stringValue(action.action_code)
    ?? stringValue(action.action_id)
    ?? stringValue(action.write_target_label)
    ?? stringValue(action.write_target)
    ?? '动作'
  );
}

function actionPreviewCount(action: Record<string, unknown>): number | undefined {
  const writePreview = recordValue(action.write_preview);
  return numberValue(writePreview?.candidate_count) ?? numberValue(writePreview?.records_imported);
}

function checkedPathLabel(path: Record<string, unknown>): string {
  const field = stringValue(path.field) ?? '字段';
  const jsonPath = stringValue(path.path) ?? '-';
  const supported = path.supported === false ? '未命中' : '已命中';
  return `${field}: ${jsonPath} ${supported}`;
}

function statusColor(status?: string) {
  if (status === 'ready' || status === 'succeeded') {
    return 'green';
  }
  if (status === 'blocked' || status === 'failed') {
    return 'red';
  }
  if (status === 'partial' || status === 'pending') {
    return 'orange';
  }
  return 'default';
}

const missingRequirementLabels: Record<string, string> = {
  action_trial_response: '动作试运行响应样例',
  action_trial_succeeded: '动作试运行成功结果',
  action_write_preview: '动作写入预览',
  ai_output_preview: 'AI 输出预览',
  connection_test_response: '连接测试响应样例',
  data_connection_sample: '数据连接样例',
  write_preview: '写入预览',
};

function requirementLabel(value: string): string {
  return missingRequirementLabels[value] ?? value;
}

function ScheduledJobDryRunMappingSummary({ result }: { result: ScheduledJobDryRunResult }) {
  const aiProcessing = recordValue(result.stages?.ai_processing);
  const mappingContract = recordValue(aiProcessing?.mapping_contract);
  if (!mappingContract) {
    return null;
  }
  const checkedPaths = Array.isArray(mappingContract.checked_paths)
    ? mappingContract.checked_paths.map(recordValue).filter(isRecordValue)
    : [];
  const invalidFields = Array.isArray(mappingContract.invalid_fields)
    ? mappingContract.invalid_fields.map(recordValue).filter(isRecordValue)
    : [];
  const status = stringValue(mappingContract.status) ?? stringValue(aiProcessing?.mapping_status) ?? 'not_required';
  return (
    <Space aria-label="Skill 输出映射校验摘要" orientation="vertical" size={8} style={{ width: '100%' }}>
      <Space size={[8, 8]} wrap>
        <Typography.Text type="secondary">Skill 输出映射</Typography.Text>
        <Tag color={status === 'succeeded' ? 'green' : status === 'failed' ? 'red' : 'default'}>
          {status}
        </Tag>
        <Tag color="blue">已校验 {checkedPaths.length} 个字段</Tag>
        {invalidFields.length ? <Tag color="red">异常 {invalidFields.length} 个</Tag> : null}
      </Space>
      {checkedPaths.length ? (
        <Space size={[8, 8]} wrap>
          {checkedPaths.map((path, index) => (
            <Tag color={path.supported === false ? 'red' : 'green'} key={`${checkedPathLabel(path)}-${index}`}>
              {checkedPathLabel(path)}
            </Tag>
          ))}
        </Space>
      ) : null}
    </Space>
  );
}

function ScheduledJobDryRunSourceSummary({ result }: { result: ScheduledJobDryRunResult }) {
  const aiProcessing = recordValue(result.stages?.ai_processing);
  const resultActions = Array.isArray(result.stages?.result_actions)
    ? result.stages.result_actions.map(recordValue).filter(isRecordValue)
    : [];
  const outputPreviewSource = aiProcessing?.output_preview_source;
  if (!outputPreviewSource && resultActions.length === 0) {
    return null;
  }

  return (
    <Space aria-label="试运行预览来源" size={[8, 8]} wrap>
      {outputPreviewSource ? (
        <>
          <Typography.Text type="secondary">AI输出来源</Typography.Text>
          <Tag color="blue">{previewSourceLabel(outputPreviewSource)}</Tag>
        </>
      ) : null}
      {resultActions.map((action, index) => {
        const count = actionPreviewCount(action);
        const source = previewSourceLabel(action.write_preview_source);
        return (
          <Tag color="purple" key={`${actionPreviewLabel(action)}-${index}`}>
            {actionPreviewLabel(action)}
            {count !== undefined ? ` · 预计写入 ${count} 条` : ''}
            {` · ${source}`}
          </Tag>
        );
      })}
    </Space>
  );
}

function ScheduledJobDryRunSampleReuseSummary({ result }: { result: ScheduledJobDryRunResult }) {
  const sampleReuse = recordValue(result.sample_reuse);
  if (!sampleReuse) {
    return null;
  }
  const steps = Array.isArray(sampleReuse.reusable_steps)
    ? sampleReuse.reusable_steps.map(recordValue).filter(isRecordValue)
    : [];
  const dataConnectionSample = recordValue(sampleReuse.data_connection_sample);
  const reuseWizard = recordValue(sampleReuse.reuse_wizard);
  const wizardSteps = Array.isArray(reuseWizard?.steps)
    ? reuseWizard.steps.map(recordValue).filter(isRecordValue)
    : [];
  const missingRequirements = Array.isArray(reuseWizard?.missing_requirements)
    ? reuseWizard.missing_requirements.map(String).filter(Boolean)
    : [];
  const handoffSummary = Array.isArray(reuseWizard?.handoff_summary)
    ? reuseWizard.handoff_summary.map(recordValue).filter(isRecordValue)
    : [];
  const preferredSource = previewSourceLabel(sampleReuse.preferred_action_preview_source);
  const dataSampleSource = previewSourceLabel(dataConnectionSample?.source);
  const recordsImported = numberValue(dataConnectionSample?.records_imported);
  const currentStepLabel = stringValue(reuseWizard?.current_step_label);
  const nextActionDescription = stringValue(reuseWizard?.next_action_description);
  const progressLabel = stringValue(reuseWizard?.progress_label);
  const progressPercent = numberValue(reuseWizard?.progress_percent);
  const wizardStatus = stringValue(reuseWizard?.status);
  const primaryActionLabel = stringValue(reuseWizard?.primary_action_label);
  const canContinue = reuseWizard?.can_continue === true;
  const blockedSteps = numberValue(reuseWizard?.blocked_steps);
  const missingRequirementText = missingRequirements.map(requirementLabel).join('、');
  return (
    <Space aria-label="样例复用摘要" orientation="vertical" size={8} style={{ width: '100%' }}>
      <Space size={[8, 8]} wrap>
        <Typography.Text type="secondary">样例复用</Typography.Text>
        <Tag color={dataConnectionSample?.status === 'ready' ? 'green' : 'default'}>
          数据样例 {dataConnectionSample?.status === 'ready' ? '可复用' : '未生成'}
        </Tag>
        {recordsImported !== undefined ? <Tag color="blue">样例行数 {recordsImported}</Tag> : null}
        <Tag color="geekblue">来源 {dataSampleSource}</Tag>
        <Tag color="purple">动作预览 {preferredSource}</Tag>
        {progressLabel ? (
          <Tag color={progressPercent === 100 ? 'green' : 'blue'}>
            进度：{progressLabel}
          </Tag>
        ) : null}
      </Space>
      {reuseWizard ? (
        <Space orientation="vertical" size={6} style={{ width: '100%' }}>
          <Space size={[8, 8]} wrap>
            {currentStepLabel ? <Tag color="geekblue">当前：{currentStepLabel}</Tag> : null}
            {wizardStatus ? <Tag color={statusColor(wizardStatus)}>向导 {wizardStatus}</Tag> : null}
            {primaryActionLabel ? <Tag color="blue">下一步：{primaryActionLabel}</Tag> : null}
            {missingRequirements.length ? (
              <Tag color="red">缺失 {missingRequirementText}</Tag>
            ) : null}
            {blockedSteps ? (
              <Tag color="red">阻断步骤 {blockedSteps}</Tag>
            ) : null}
          </Space>
          <Alert
            title={canContinue ? '样例复用链路已就绪' : '样例复用链路暂未就绪'}
            description={(
              <Space orientation="vertical" size={4}>
                {missingRequirementText ? (
                  <Typography.Text>需要处理：{missingRequirementText}</Typography.Text>
                ) : null}
                {nextActionDescription ? (
                  <Typography.Text type="secondary">{nextActionDescription}</Typography.Text>
                ) : null}
              </Space>
            )}
            showIcon
            type={canContinue ? 'success' : 'warning'}
          />
          {handoffSummary.length ? (
            <Space size={[8, 8]} wrap>
              {handoffSummary.map((item, index) => {
                const status = stringValue(item.status) ?? 'unknown';
                return (
                  <Tag color={statusColor(status)} key={`${stringValue(item.key) ?? index}-${status}`}>
                    {stringValue(item.label) ?? stringValue(item.key) ?? '已带入'} · {status}
                  </Tag>
                );
              })}
            </Space>
          ) : null}
        </Space>
      ) : null}
      {wizardSteps.length ? (
        <Space size={[8, 8]} wrap>
          {wizardSteps.map((step, index) => {
            const status = stringValue(step.status) ?? 'unknown';
            return (
              <Tag color={statusColor(status)} key={`${stringValue(step.key) ?? index}-${status}`}>
                {stringValue(step.label) ?? stringValue(step.key) ?? '复用步骤'} · {status}
              </Tag>
            );
          })}
        </Space>
      ) : null}
      {steps.length ? (
        <Space size={[8, 8]} wrap>
          {steps.map((step, index) => {
            const status = stringValue(step.status) ?? 'unknown';
            return (
              <Tag color={status === 'ready' ? 'green' : status === 'not_configured' ? 'orange' : 'default'} key={`${stringValue(step.key) ?? index}-${status}`}>
                {stringValue(step.label) ?? stringValue(step.key) ?? '复用步骤'} · {status}
              </Tag>
            );
          })}
        </Space>
      ) : null}
    </Space>
  );
}

export function ScheduledJobDryRunResultPanel({ result }: { result: ScheduledJobDryRunResult }) {
  return (
    <div
      aria-label="全链路试运行结果"
      style={{
        background: '#f8fafc',
        border: '1px solid #dbeafe',
        borderRadius: 6,
        marginTop: 16,
        padding: 16,
      }}
    >
      <Space orientation="vertical" size={16} style={{ width: '100%' }}>
        <Space>
          <Typography.Text strong>全链路试运行结果</Typography.Text>
          <Tag color={result.status === 'succeeded' ? 'green' : 'red'}>{result.status}</Tag>
          <Typography.Text type="secondary">{result.job_type}</Typography.Text>
        </Space>
        <ScheduledJobDryRunSampleReuseSummary result={result} />
        <ScheduledJobDryRunSourceSummary result={result} />
        <ScheduledJobDryRunMappingSummary result={result} />
        <ScheduledJobJsonPreview title="数据连接预览" value={result.stages?.data_connection} />
        <ScheduledJobJsonPreview title="AI契约校验" value={result.stages?.ai_processing} />
        <ScheduledJobJsonPreview title="结果写入预览" value={result.stages?.result_actions} />
      </Space>
    </div>
  );
}
