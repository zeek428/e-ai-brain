import { Space, Tag, Typography } from 'antd';
import type { ReactNode } from 'react';

export function ScheduledJobFormSection({
  children,
  label,
  marker,
}: {
  children: ReactNode;
  label: string;
  marker: string;
}) {
  return (
    <div
      aria-label={label}
      style={{
        borderTop: '1px solid #e5e7eb',
        paddingTop: 14,
      }}
    >
      <Space orientation="vertical" size={10} style={{ width: '100%' }}>
        <Space align="center" size={8}>
          <Tag color="blue">{marker}</Tag>
          <Typography.Text strong>{label}</Typography.Text>
        </Space>
        {children}
      </Space>
    </div>
  );
}
