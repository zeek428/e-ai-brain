import { Typography } from 'antd';
import type { CSSProperties } from 'react';

import type { AssistantActionDraftWorkbenchSummary } from '../../../services/aiBrain';
import { percent } from './assistantDraftWorkbenchPresentation';

const { Text } = Typography;

const summaryStripStyle: CSSProperties = {
  display: 'grid',
  gap: 12,
  gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
  marginBottom: 16,
  width: '100%',
};

const summaryItemStyle: CSSProperties = {
  background: '#ffffff',
  border: '1px solid #edf1f7',
  borderRadius: 8,
  boxSizing: 'border-box',
  display: 'grid',
  gap: 6,
  minWidth: 0,
  padding: '12px 14px',
};

const summaryValueStyle: CSSProperties = {
  fontSize: 20,
  lineHeight: 1.2,
};

const warningValueStyle: CSSProperties = {
  ...summaryValueStyle,
  color: '#d46b08',
};

const dangerValueStyle: CSSProperties = {
  ...summaryValueStyle,
  color: '#cf1322',
};

function count(value?: number) {
  return value ?? 0;
}

export function AssistantDraftSummaryStrip({
  summary,
}: {
  summary?: AssistantActionDraftWorkbenchSummary;
}) {
  const statusCounts = summary?.status_counts ?? {};
  const governanceCounts = summary?.governance_counts ?? {};
  const validationCounts = summary?.validation_counts ?? {};
  const metrics = [
    { label: '待确认草案', value: statusCounts.pending ?? 0 },
    { label: '失败草案', value: statusCounts.failed ?? 0 },
    { label: '已采纳草案', value: statusCounts.confirmed ?? 0 },
    { label: '采纳率', value: percent(summary?.adoption_rate) },
    { label: '处理率', value: percent(summary?.resolution_rate) },
    { label: '用户修改率', value: percent(summary?.user_modified_rate) },
    {
      label: '高风险草案',
      value: count(governanceCounts.high_risk),
      valueStyle: count(governanceCounts.high_risk) > 0 ? dangerValueStyle : summaryValueStyle,
    },
    {
      label: '权限阻塞',
      value: count(governanceCounts.permission_blocked),
      valueStyle: count(governanceCounts.permission_blocked) > 0 ? dangerValueStyle : summaryValueStyle,
    },
    {
      label: '校验阻塞',
      value: count(governanceCounts.validation_blocked ?? validationCounts.blocked),
      valueStyle: count(governanceCounts.validation_blocked ?? validationCounts.blocked) > 0
        ? warningValueStyle
        : summaryValueStyle,
    },
    {
      label: '失败/重试',
      value: `${count(governanceCounts.failed)} / ${count(governanceCounts.retry_total)}`,
      valueStyle: count(governanceCounts.failed) > 0 ? dangerValueStyle : summaryValueStyle,
    },
    {
      label: '审计事件',
      value: count(governanceCounts.audit_events),
    },
  ];
  return (
    <div aria-label="草案任务台指标" className="assistant-draft-summary-strip" role="list" style={summaryStripStyle}>
      {metrics.map((metric) => (
        <div className="assistant-draft-summary-item" key={metric.label} role="listitem" style={summaryItemStyle}>
          <Text type="secondary">{metric.label}</Text>
          <strong style={metric.valueStyle ?? summaryValueStyle}>{metric.value}</strong>
        </div>
      ))}
    </div>
  );
}
