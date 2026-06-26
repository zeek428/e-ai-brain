import { Typography } from 'antd';

import type { AssistantActionDraftWorkbenchSummary } from '../../../services/aiBrain';
import { percent } from './assistantDraftWorkbenchPresentation';

const { Text } = Typography;

export function AssistantDraftSummaryStrip({
  summary,
}: {
  summary?: AssistantActionDraftWorkbenchSummary;
}) {
  const statusCounts = summary?.status_counts ?? {};
  const metrics = [
    { label: '待确认草案', value: statusCounts.pending ?? 0 },
    { label: '失败草案', value: statusCounts.failed ?? 0 },
    { label: '已采纳草案', value: statusCounts.confirmed ?? 0 },
    { label: '采纳率', value: percent(summary?.adoption_rate) },
    { label: '处理率', value: percent(summary?.resolution_rate) },
    { label: '用户修改率', value: percent(summary?.user_modified_rate) },
  ];
  return (
    <div className="assistant-draft-summary-strip">
      {metrics.map((metric) => (
        <div className="assistant-draft-summary-item" key={metric.label}>
          <Text type="secondary">{metric.label}</Text>
          <strong>{metric.value}</strong>
        </div>
      ))}
    </div>
  );
}
