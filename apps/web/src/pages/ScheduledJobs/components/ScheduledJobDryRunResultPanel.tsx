import { Space, Tag, Typography } from 'antd';

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
        <ScheduledJobDryRunSourceSummary result={result} />
        <ScheduledJobDryRunMappingSummary result={result} />
        <ScheduledJobJsonPreview title="数据连接预览" value={result.stages?.data_connection} />
        <ScheduledJobJsonPreview title="AI契约校验" value={result.stages?.ai_processing} />
        <ScheduledJobJsonPreview title="结果写入预览" value={result.stages?.result_actions} />
      </Space>
    </div>
  );
}
