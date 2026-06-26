import { Button, Space, Tag, Typography } from 'antd';

import type { AssistantActionDraftPreview } from '../../../services/aiBrain';
import {
  assistantRepairActionPrompt,
  assistantRepairActionUrl,
  draftPreviewStatusLabel,
  draftPreviewValueText,
} from './assistantDraftPreviewHelpers';

const { Text } = Typography;

export function AssistantDraftPreviewBlock({
  draftTitle,
  onUseRepairAction,
  preview,
}: {
  draftTitle?: string;
  onUseRepairAction?: (prompt: string) => void;
  preview?: AssistantActionDraftPreview;
}) {
  if (!preview) {
    return null;
  }
  const diffs = (preview.diffs ?? []).slice(0, 4);
  const issues = preview.validation?.issues ?? [];
  const statusLabel = draftPreviewStatusLabel(preview.validation?.status);
  return (
    <div className="assistant-action-draft-precheck">
      <Space size={8} wrap>
        <Text strong>应用前预检</Text>
        <Tag color={statusLabel.color}>{statusLabel.text}</Tag>
      </Space>
      {diffs.length ? (
        <div className="assistant-action-draft-precheck-diffs">
          {diffs.map((diff) => (
            <span key={diff.field}>
              <Text type="secondary">{diff.label ?? diff.field}</Text>
              <Text>
                {draftPreviewValueText(diff.current)} -&gt; {draftPreviewValueText(diff.proposed)}
              </Text>
            </span>
          ))}
        </div>
      ) : null}
      {issues.length ? (
        <div className="assistant-action-draft-precheck-issues">
          {issues.map((issue) => {
            const repairAction = issue.repair_action;
            const repairUrl = assistantRepairActionUrl(repairAction);
            return (
              <span key={`${issue.field}:${issue.message}`}>
                <Text type={issue.severity === 'error' ? 'danger' : 'warning'}>
                  {issue.message}
                </Text>
                {repairAction?.label ? (
                  <Button
                    href={repairUrl}
                    size="small"
                    onClick={repairUrl ? undefined : () => onUseRepairAction?.(
                      assistantRepairActionPrompt(draftTitle, repairAction),
                    )}
                  >
                    {repairAction.label}
                  </Button>
                ) : null}
              </span>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
