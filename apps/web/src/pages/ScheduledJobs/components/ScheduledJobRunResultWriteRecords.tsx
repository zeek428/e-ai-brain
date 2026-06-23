import { Space, Table, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';

import type { ResultWriteRecord } from '../../../services/aiBrain';
import { formatDisplayDateTime } from '../../../utils/dateTime';
import { ScheduledJobJsonPreview } from './ScheduledJobJsonPreview';
import { formatJsonValue } from './scheduledJobJsonPreviewHelpers';

function resultWriteRecordFieldText(value: unknown): string {
  if (value === undefined || value === null || value === '') {
    return '-';
  }
  if (Array.isArray(value)) {
    return value.length ? value.map((item) => resultWriteRecordFieldText(item)).join('、') : '-';
  }
  if (typeof value === 'object') {
    return formatJsonValue(value);
  }
  return String(value);
}

function resultWriteRecordSummaryText(record: ResultWriteRecord) {
  const fields = record.summary_fields ?? {};
  const parts = [
    fields.subject ? `主题：${resultWriteRecordFieldText(fields.subject)}` : undefined,
    fields.delivery_status ? `状态：${resultWriteRecordFieldText(fields.delivery_status)}` : undefined,
    fields.delivery_id ? `ID：${resultWriteRecordFieldText(fields.delivery_id)}` : undefined,
    fields.sample_records?.length
      ? `样例：${resultWriteRecordFieldText(fields.sample_records)}`
      : undefined,
    fields.preview_value !== undefined
      ? `预览：${resultWriteRecordFieldText(fields.preview_value)}`
      : undefined,
  ].filter(Boolean);
  return parts.length ? parts.join(' / ') : '-';
}

function resultWriteRecordSourceLabel(sourceType?: string) {
  if (sourceType === 'scheduled_job_run') {
    return '定时作业运行';
  }
  if (sourceType === 'plugin_invocation_log') {
    return '插件调用日志';
  }
  return sourceType || '-';
}

function resultWriteRecordStatusColor(status?: string) {
  if (status === 'succeeded') {
    return 'green';
  }
  if (status === 'failed') {
    return 'red';
  }
  if (status === 'not_run') {
    return 'default';
  }
  return 'blue';
}

export function ScheduledJobRunResultWriteRecords({
  focusedRecordId,
  loading,
  records,
}: {
  focusedRecordId?: string;
  loading: boolean;
  records: ResultWriteRecord[];
}) {
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([]);

  useEffect(() => {
    queueMicrotask(() => {
      if (!focusedRecordId) {
        setExpandedRowKeys([]);
        return;
      }
      const hasFocusedRecord = records.some((record) => record.id === focusedRecordId);
      setExpandedRowKeys(hasFocusedRecord ? [focusedRecordId] : []);
    });
  }, [focusedRecordId, records]);

  return (
    <Space orientation="vertical" size={8} style={{ width: '100%' }}>
      <Typography.Text strong>结果写入记录</Typography.Text>
      <Table<ResultWriteRecord>
        columns={[
          {
            dataIndex: 'write_target_label',
            title: '写入目标',
            width: 160,
            render: (_, record) => (
              <Tag color="blue">{record.write_target_label || record.write_target}</Tag>
            ),
          },
          {
            dataIndex: 'status',
            title: '状态',
            width: 110,
            render: (value) => (
              <Tag color={resultWriteRecordStatusColor(String(value ?? ''))}>{String(value ?? '-')}</Tag>
            ),
          },
          {
            key: 'source',
            title: '来源',
            width: 180,
            render: (_, record) => resultWriteRecordSourceLabel(record.source_type),
          },
          {
            key: 'summary',
            title: '写入摘要',
            ellipsis: true,
            render: (_, record) => resultWriteRecordSummaryText(record),
          },
          { dataIndex: 'records_imported', title: '写入数', width: 90 },
          {
            dataIndex: 'plugin_invocation_log_id',
            title: '调用日志',
            ellipsis: true,
            width: 190,
            render: (value) => value || '-',
          },
          {
            dataIndex: 'created_at',
            title: '时间',
            ellipsis: true,
            width: 210,
            render: (value) => formatDisplayDateTime(value),
          },
        ]}
        dataSource={records}
        expandable={{
          expandedRowKeys,
          onExpandedRowsChange: (keys) => setExpandedRowKeys(keys.map(String)),
          expandedRowRender: (record) => (
            <Space orientation="vertical" size={10} style={{ width: '100%' }}>
              <ScheduledJobJsonPreview title="结果摘要字段" value={record.summary_fields} />
              <ScheduledJobJsonPreview title="写入预览" value={record.preview} />
              <ScheduledJobJsonPreview title="执行反馈" value={record.feedback} />
            </Space>
          ),
        }}
        loading={loading}
        locale={{ emptyText: '暂无结果写入记录' }}
        pagination={false}
        rowKey="id"
        scroll={{ x: 1040 }}
        size="small"
      />
    </Space>
  );
}
