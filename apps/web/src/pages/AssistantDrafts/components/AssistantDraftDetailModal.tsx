import { Button, Descriptions, Modal, Space, Table, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useMemo } from 'react';

import { ExecutionTraceLink } from '../../../components/ExecutionTraceLink';
import type {
  AssistantActionDraftPreviewIssue,
  AssistantActionDraftRecord,
} from '../../../services/aiBrain';
import { formatDisplayDateTime } from '../../../utils/dateTime';
import {
  actionLabel,
  assistantDraftEditHref,
  compactText,
  jsonPreview,
  riskTag,
  statusTag,
  validationTag,
} from './assistantDraftWorkbenchPresentation';

const { Text } = Typography;

type AssistantDraftDetailModalProps = {
  detail?: AssistantActionDraftRecord;
  loading: boolean;
  onClose: () => void;
};

export function AssistantDraftDetailModal({
  detail,
  loading,
  onClose,
}: AssistantDraftDetailModalProps) {
  const issueColumns = useMemo<ColumnsType<AssistantActionDraftPreviewIssue>>(
    () => [
      { dataIndex: 'severity', title: '级别', width: 90 },
      { dataIndex: 'field', title: '字段', width: 160 },
      { dataIndex: 'message', title: '说明', render: (_, row) => compactText(row.message) },
    ],
    [],
  );
  const detailIssues = detail?.preview?.validation?.issues ?? [];

  return (
    <Modal
      footer={null}
      loading={loading}
      onCancel={onClose}
      open={Boolean(detail)}
      title="草案详情"
      width={1040}
    >
      {detail ? (
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Space wrap>
            <Button href={assistantDraftEditHref(detail.id)} type="primary">
              继续编辑
            </Button>
            <ExecutionTraceLink asButton sourceId={detail.source_message_id} sourceType="assistant_message">
              来源链路
            </ExecutionTraceLink>
          </Space>
          <Descriptions column={3} size="small">
            <Descriptions.Item label="草案标题" span={2}>{detail.title}</Descriptions.Item>
            <Descriptions.Item label="状态">{statusTag(detail.status)}</Descriptions.Item>
            <Descriptions.Item label="草案类型">{actionLabel(detail.action)}</Descriptions.Item>
            <Descriptions.Item label="风险">{riskTag(detail.risk_level)}</Descriptions.Item>
            <Descriptions.Item label="校验">{validationTag(detail.preview?.validation?.status)}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{formatDisplayDateTime(detail.created_at)}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{formatDisplayDateTime(detail.updated_at)}</Descriptions.Item>
            <Descriptions.Item label="结果">
              {detail.result_run?.status ? `${detail.result_run.status} · ${detail.result_run.result_type ?? '-'}` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="来源消息">{detail.source_message_id ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="来源链路">
              <ExecutionTraceLink asButton sourceId={detail.source_message_id} sourceType="assistant_message">
                来源链路
              </ExecutionTraceLink>
            </Descriptions.Item>
          </Descriptions>
          <Table<AssistantActionDraftPreviewIssue>
            columns={issueColumns}
            dataSource={detailIssues}
            pagination={false}
            rowKey={(row) => `${row.field}-${row.severity}-${row.message}`}
            scroll={{ x: 720 }}
            size="small"
            tableLayout="fixed"
            title={() => '校验问题'}
          />
          <section>
            <Text strong>草案 Payload</Text>
            <div style={{ marginTop: 8 }}>{jsonPreview(detail.payload)}</div>
          </section>
        </Space>
      ) : null}
    </Modal>
  );
}
