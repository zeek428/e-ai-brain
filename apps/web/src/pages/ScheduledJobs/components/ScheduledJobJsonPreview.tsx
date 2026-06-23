import { Space, Typography } from 'antd';

import { formatJsonValue, isEmptyJsonValue } from './scheduledJobJsonPreviewHelpers';

export function ScheduledJobJsonPreview({ title, value }: { title: string; value: unknown }) {
  return (
    <Space orientation="vertical" size={6} style={{ width: '100%' }}>
      <Typography.Text strong>{title}</Typography.Text>
      <Typography.Paragraph
        copyable={!isEmptyJsonValue(value)}
        style={{
          background: '#f6f8fa',
          border: '1px solid #e5e7eb',
          borderRadius: 6,
          marginBottom: 0,
          maxHeight: 260,
          overflow: 'auto',
          padding: 12,
          whiteSpace: 'pre-wrap',
        }}
      >
        {formatJsonValue(value)}
      </Typography.Paragraph>
    </Space>
  );
}
