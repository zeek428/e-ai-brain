import { Button, Descriptions, Modal, Space, Table, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useMemo } from 'react';

import { ExecutionTraceLink } from '../../../components/ExecutionTraceLink';
import type {
  AssistantActionDraftPreviewDiff,
  AssistantActionDraftPreviewIssue,
  AssistantActionDraftRecord,
} from '../../../services/aiBrain';
import { formatDisplayDateTime } from '../../../utils/dateTime';
import {
  actionLabel,
  assistantDraftEditHref,
  compactText,
  jsonPreview,
  operationText,
  permissionTag,
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
  const diffColumns = useMemo<ColumnsType<AssistantActionDraftPreviewDiff>>(
    () => [
      { dataIndex: 'label', title: '字段', width: 150, render: (_, row) => compactText(row.label ?? row.field) },
      { dataIndex: 'change_type', title: '变更', width: 90, render: (_, row) => operationText(row.change_type) },
      {
        dataIndex: 'current',
        title: '当前值',
        width: 240,
        render: (_, row) => compactText(JSON.stringify(row.current ?? '-')),
      },
      {
        dataIndex: 'proposed',
        title: '草案值',
        width: 280,
        render: (_, row) => compactText(JSON.stringify(row.proposed ?? '-')),
      },
    ],
    [],
  );
  const detailIssues = detail?.preview?.validation?.issues ?? [];
  const detailDiffs = detail?.preview?.diffs ?? [];
  const governance = detail?.governance;
  const impact = governance?.impact;
  const permissions = governance?.permissions;
  const retries = governance?.retries;
  const audit = governance?.audit;
  const requiredPermissions = permissions?.required_permissions?.join(', ') || '-';
  const missingPermissions = permissions?.missing_permissions?.join(', ') || '-';
  const sourceResource = impact?.source_resource;

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
          <Descriptions column={3} size="small" title="执行治理摘要">
            <Descriptions.Item label="影响对象">
              {operationText(impact?.operation)} · {impact?.resource_type ?? '-'}
              {impact?.resource_id ? ` · ${impact.resource_id}` : ''}
            </Descriptions.Item>
            <Descriptions.Item label="来源对象" span={2}>
              {sourceResource
                ? `${sourceResource.resource_type ?? '-'} · ${sourceResource.title ?? sourceResource.resource_id ?? '-'}`
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="字段差异">
              {governance?.diff?.count ?? detailDiffs.length} 项
            </Descriptions.Item>
            <Descriptions.Item label="Payload 字段">
              {impact?.payload_field_count ?? Object.keys(detail.payload ?? {}).length} 项
            </Descriptions.Item>
            <Descriptions.Item label="权限校验">
              <Space size={4}>
                {permissionTag(permissions?.status)}
                {permissions?.issue_count ? <Text type="secondary">{permissions.issue_count}</Text> : null}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="必需权限" span={2}>
              {requiredPermissions}
            </Descriptions.Item>
            <Descriptions.Item label="缺失权限">
              {missingPermissions}
            </Descriptions.Item>
            <Descriptions.Item label="审计事件">
              {audit?.event_count ?? 0} 条
            </Descriptions.Item>
            <Descriptions.Item label="最新审计" span={2}>
              {audit?.latest_event_type
                ? `${audit.latest_event_type} · ${formatDisplayDateTime(audit.latest_event_at)}`
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="失败/重试">
              {retries?.failure_count ?? 0} 次失败 · {retries?.retry_count ?? 0} 次重试
            </Descriptions.Item>
            <Descriptions.Item label="最近失败" span={2}>
              {retries?.last_failure_message ?? retries?.last_failure_code ?? '-'}
            </Descriptions.Item>
          </Descriptions>
          <Table<AssistantActionDraftPreviewDiff>
            columns={diffColumns}
            dataSource={detailDiffs}
            pagination={false}
            rowKey={(row) => `${row.field}-${row.change_type}`}
            scroll={{ x: 760 }}
            size="small"
            tableLayout="fixed"
            title={() => '执行前后差异'}
          />
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
