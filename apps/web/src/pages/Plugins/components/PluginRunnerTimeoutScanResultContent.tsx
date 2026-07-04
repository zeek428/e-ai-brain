import { Space, Tag, Typography } from 'antd';

import type { AiExecutorTaskTimeoutScanResponse } from '../../../services/aiBrain';

function timeoutScanStatusColor(status?: string) {
  if (status === 'attention_required') {
    return 'red';
  }
  if (status === 'requeued') {
    return 'orange';
  }
  if (status === 'no_changes') {
    return 'green';
  }
  return 'default';
}

function actionSeverityColor(severity?: string) {
  if (severity === 'error') {
    return 'red';
  }
  if (severity === 'warning') {
    return 'orange';
  }
  if (severity === 'success') {
    return 'green';
  }
  if (severity === 'info') {
    return 'blue';
  }
  return 'default';
}

export function PluginRunnerTimeoutScanResultContent({
  result,
}: {
  result: AiExecutorTaskTimeoutScanResponse;
}) {
  const summary = result.summary;
  return (
    <Space orientation="vertical" size={10} style={{ width: '100%' }}>
      <Space size={[8, 8]} wrap>
        <Tag color={timeoutScanStatusColor(summary?.status)}>状态 {summary?.status ?? '-'}</Tag>
        <Tag>影响 {summary?.total_affected ?? 0}</Tag>
        <Tag color={summary?.requeued_count ? 'orange' : 'default'}>重派 {summary?.requeued_count ?? 0}</Tag>
        <Tag color={summary?.dead_letter_count ? 'red' : 'default'}>死信 {summary?.dead_letter_count ?? 0}</Tag>
        <Tag color={summary?.timed_out_count ? 'red' : 'default'}>超时 {summary?.timed_out_count ?? 0}</Tag>
      </Space>
      <Typography.Text>{summary?.message ?? 'Runner 超时扫描完成。'}</Typography.Text>
      {result.next_actions?.length ? (
        <Space aria-label="Runner 超时扫描下一步" orientation="vertical" size={6}>
          {result.next_actions.map((action) => (
            <Space key={action.key} size={[8, 8]} wrap>
              <Tag color={actionSeverityColor(action.severity)}>{action.label}</Tag>
              <Typography.Text type="secondary">{action.description}</Typography.Text>
            </Space>
          ))}
        </Space>
      ) : null}
    </Space>
  );
}
