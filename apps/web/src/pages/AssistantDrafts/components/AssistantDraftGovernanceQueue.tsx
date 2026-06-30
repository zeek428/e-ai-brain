import { Button, Space, Typography } from 'antd';
import type { CSSProperties } from 'react';

import { StatusTag } from '../../../components/ManagementListPage';
import type {
  AssistantActionDraftWorkbenchItem,
  AssistantActionDraftWorkbenchSummary,
} from '../../../services/aiBrain';
import { assistantDraftEditHref, compactText } from './assistantDraftWorkbenchPresentation';

const { Text } = Typography;

const queueStyle: CSSProperties = {
  border: '1px solid #edf1f7',
  borderRadius: 8,
  marginBottom: 16,
  overflowX: 'auto',
  padding: 12,
};

const queueHeaderStyle: CSSProperties = {
  alignItems: 'center',
  display: 'flex',
  justifyContent: 'space-between',
  marginBottom: 8,
};

const queueListStyle: CSSProperties = {
  display: 'grid',
  gap: 8,
};

const queueItemStyle: CSSProperties = {
  alignItems: 'center',
  background: '#fafafa',
  borderRadius: 8,
  display: 'grid',
  gap: 12,
  gridTemplateColumns: '120px minmax(180px, 1fr) minmax(160px, 1.4fr) auto',
  minWidth: 0,
  padding: '10px 12px',
};

type GovernanceQueueItem = {
  action: string;
  count: number;
  key: string;
  sample?: AssistantActionDraftWorkbenchItem;
  status: {
    color: string;
    label: string;
  };
  title: string;
};

function count(value?: number) {
  return value ?? 0;
}

function buildGovernanceQueue(
  summary: AssistantActionDraftWorkbenchSummary | undefined,
  rows: AssistantActionDraftWorkbenchItem[],
) {
  const governanceCounts = summary?.governance_counts ?? {};
  const validationCounts = summary?.validation_counts ?? {};
  const statusCounts = summary?.status_counts ?? {};
  const riskCounts = summary?.risk_counts ?? {};
  const auditMissingRows = rows.filter((row) => (row.audit_event_count ?? 0) === 0);
  const permissionBlockedRows = rows.filter((row) => row.permission_status === 'blocked');
  const validationBlockedRows = rows.filter((row) => row.validation_status === 'blocked');
  const failedRows = rows.filter((row) => row.status === 'failed');
  const highRiskRows = rows.filter((row) => row.risk_level === 'high' || row.risk_level === 'critical');
  const permissionBlockedCount = Math.max(
    count(governanceCounts.permission_blocked),
    permissionBlockedRows.length,
  );
  const validationBlockedCount = Math.max(
    count(governanceCounts.validation_blocked ?? validationCounts.blocked),
    validationBlockedRows.length,
  );
  const failedCount = Math.max(count(governanceCounts.failed ?? statusCounts.failed), failedRows.length);
  const highRiskCount = Math.max(
    count(governanceCounts.high_risk ?? ((riskCounts.high ?? 0) + (riskCounts.critical ?? 0))),
    highRiskRows.length,
  );
  const items: GovernanceQueueItem[] = [
    {
      action: '补齐权限或调整草案后再确认',
      count: permissionBlockedCount,
      key: 'permission_blocked',
      sample: permissionBlockedRows[0],
      status: { color: 'red', label: 'P0' },
      title: '权限阻断草案',
    },
    {
      action: '补齐必填字段和校验问题',
      count: validationBlockedCount,
      key: 'validation_blocked',
      sample: validationBlockedRows[0],
      status: { color: 'volcano', label: 'P0' },
      title: '校验阻断草案',
    },
    {
      action: '查看失败原因并重新打开',
      count: failedCount,
      key: 'failed_retry',
      sample: failedRows[0],
      status: { color: 'red', label: 'P0' },
      title: '失败草案待重试',
    },
    {
      action: '逐条核对影响对象和执行前后差异',
      count: highRiskCount,
      key: 'high_risk',
      sample: highRiskRows[0],
      status: { color: 'orange', label: 'P1' },
      title: '高风险草案',
    },
    {
      action: '打开详情确认审计链路是否已生成',
      count: auditMissingRows.length,
      key: 'audit_missing',
      sample: auditMissingRows[0],
      status: { color: 'gold', label: 'P1' },
      title: '当前页审计缺口',
    },
  ];

  return items.filter((item) => item.count > 0);
}

export function AssistantDraftGovernanceQueue({
  rows,
  summary,
}: {
  rows: AssistantActionDraftWorkbenchItem[];
  summary?: AssistantActionDraftWorkbenchSummary;
}) {
  const queueItems = buildGovernanceQueue(summary, rows);

  return (
    <section aria-label="草案治理优先队列" style={queueStyle}>
      <div style={queueHeaderStyle}>
        <Text strong>治理优先队列</Text>
        <Text type="secondary">{queueItems.length > 0 ? `${queueItems.length} 类待处理` : '暂无高优先级治理项'}</Text>
      </div>
      {queueItems.length > 0 ? (
        <div role="list" style={queueListStyle}>
          {queueItems.map((item) => (
            <div key={item.key} role="listitem" style={queueItemStyle}>
              <Space size={8}>
                <StatusTag color={item.status.color} label={item.status.label} />
                <Text strong>{item.count}</Text>
              </Space>
              <div>
                <Text strong>{item.title}</Text>
                <br />
                <Text type="secondary">{item.action}</Text>
              </div>
              <div style={{ minWidth: 0 }}>
                <Text type="secondary">代表草案</Text>
                {compactText(item.sample?.title)}
              </div>
              {item.sample ? (
                <Button href={assistantDraftEditHref(item.sample.id)} size="small" type="link">
                  处理
                </Button>
              ) : (
                <Text type="secondary">-</Text>
              )}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
