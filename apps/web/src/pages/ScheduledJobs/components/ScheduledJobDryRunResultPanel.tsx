import { Space, Tag, Typography } from 'antd';

import type { ScheduledJobDryRunResult } from '../../../services/aiBrain';
import { ScheduledJobJsonPreview } from './ScheduledJobJsonPreview';

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
        <ScheduledJobJsonPreview title="数据连接预览" value={result.stages?.data_connection} />
        <ScheduledJobJsonPreview title="AI契约校验" value={result.stages?.ai_processing} />
        <ScheduledJobJsonPreview title="结果写入预览" value={result.stages?.result_actions} />
      </Space>
    </div>
  );
}
