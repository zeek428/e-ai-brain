import { Descriptions, Space, Table, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useMemo } from 'react';

import type {
  AssistantActionDraftPreviewIssue,
  AssistantActionDraftRecord,
} from '../../../services/aiBrain';
import { formatDisplayDateTime } from '../../../utils/dateTime';
import {
  compactText,
  operationText,
  permissionTag,
  riskTag,
} from './assistantDraftWorkbenchPresentation';

const { Text } = Typography;

type AssistantDraftGovernancePanelProps = {
  detail: AssistantActionDraftRecord;
  diffCount: number;
};

function joinValues(values?: string[] | null) {
  return values && values.length > 0 ? values.join(', ') : '-';
}

function formatLatestAudit(audit: NonNullable<AssistantActionDraftRecord['governance']>['audit']) {
  if (!audit?.latest_event_type) {
    return '-';
  }
  const parts = [
    audit.latest_event_type,
    audit.latest_event_id,
    audit.latest_actor_id ? `操作者 ${audit.latest_actor_id}` : undefined,
    formatDisplayDateTime(audit.latest_event_at),
  ].filter(Boolean);
  return parts.join(' · ');
}

export function AssistantDraftGovernancePanel({
  detail,
  diffCount,
}: AssistantDraftGovernancePanelProps) {
  const governance = detail.governance;
  const impact = governance?.impact;
  const permissions = governance?.permissions;
  const retries = governance?.retries;
  const audit = governance?.audit;
  const risk = governance?.risk;
  const sourceResource = impact?.source_resource;
  const permissionIssues = permissions?.issues ?? [];
  const permissionIssueColumns = useMemo<ColumnsType<AssistantActionDraftPreviewIssue>>(
    () => [
      { dataIndex: 'severity', title: '级别', width: 90 },
      { dataIndex: 'field', title: '字段', width: 160 },
      { dataIndex: 'message', title: '说明', render: (_, row) => compactText(row.message) },
      {
        dataIndex: 'repair_action',
        title: '修复动作',
        width: 180,
        render: (_, row) => row.repair_action?.label ?? row.repair_action?.action ?? '-',
      },
    ],
    [],
  );

  return (
    <Space orientation="vertical" size={12} style={{ width: '100%' }}>
      <Descriptions column={3} size="small" title="执行治理摘要">
        <Descriptions.Item label="风险等级">
          {riskTag(risk?.level ?? detail.risk_level)}
        </Descriptions.Item>
        <Descriptions.Item label="风险原因" span={2}>
          {risk?.reason ?? '-'}
        </Descriptions.Item>
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
          {governance?.diff?.count ?? diffCount} 项
        </Descriptions.Item>
        <Descriptions.Item label="变更字段" span={2}>
          {joinValues(governance?.diff?.changed_fields?.map((field) => field.label ?? field.field ?? '-'))}
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
        <Descriptions.Item label="必需权限">
          {joinValues(permissions?.required_permissions)}
        </Descriptions.Item>
        <Descriptions.Item label="缺失权限">
          {joinValues(permissions?.missing_permissions)}
        </Descriptions.Item>
        <Descriptions.Item label="审计事件">
          {audit?.event_count ?? 0} 条
        </Descriptions.Item>
        <Descriptions.Item label="审计类型">
          {joinValues(audit?.event_types)}
        </Descriptions.Item>
        <Descriptions.Item label="最新审计" span={2}>
          {formatLatestAudit(audit)}
        </Descriptions.Item>
        <Descriptions.Item label="失败/重试">
          {retries?.failure_count ?? 0} 次失败 · {retries?.retry_count ?? 0} 次重试
        </Descriptions.Item>
        <Descriptions.Item label="可重试">
          {retries?.can_retry ? '可重试' : '不可重试'}
        </Descriptions.Item>
        <Descriptions.Item label="重试原因" span={2}>
          {retries?.retry_reason ?? '-'}
        </Descriptions.Item>
        <Descriptions.Item label="最近失败" span={3}>
          {retries?.last_failure_message ?? retries?.last_failure_code ?? '-'}
        </Descriptions.Item>
      </Descriptions>
      {permissionIssues.length > 0 ? (
        <Table<AssistantActionDraftPreviewIssue>
          columns={permissionIssueColumns}
          dataSource={permissionIssues}
          pagination={false}
          rowKey={(row) => `${row.field}-${row.severity}-${row.message}`}
          scroll={{ x: 720 }}
          size="small"
          tableLayout="fixed"
          title={() => '权限问题'}
        />
      ) : null}
    </Space>
  );
}
