import { Modal, Space, Tag, Typography } from 'antd';

import type { AssistantToolResultItem } from '../../../services/aiBrain';
import { draftPreviewValueText } from './assistantDraftPreviewHelpers';
import { draftStatusLabel } from './draftPresentation';

const { Text } = Typography;

function optionalText(value: unknown) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  return String(value);
}

export function AssistantDraftDetailModal({
  draft,
  onClose,
  status,
}: {
  draft?: AssistantToolResultItem;
  onClose: () => void;
  status?: string;
}) {
  const statusLabel = draftStatusLabel(status ?? draft?.status);
  const diffs = draft?.preview?.diffs ?? [];
  const issues = draft?.preview?.validation?.issues ?? [];
  const sourceResource = draft?.preview?.target?.source_resource;
  const sourceResourceTitle = optionalText(
    sourceResource?.title ?? sourceResource?.resource_id,
  );
  return (
    <Modal
      footer={null}
      open={Boolean(draft)}
      title={`草案详情 - ${draft?.title ?? '配置草案'}`}
      width={760}
      onCancel={onClose}
    >
      {draft ? (
        <div className="assistant-draft-detail">
          <Space size={8} wrap>
            <Text strong>草案状态</Text>
            <Tag color={statusLabel.color}>{statusLabel.text}</Tag>
            <Tag color="default">{draft.action ?? 'unknown_action'}</Tag>
            {draft.risk_level ? <Tag color="orange">风险：{draft.risk_level}</Tag> : null}
          </Space>
          {sourceResourceTitle ? (
            <div className="assistant-draft-detail-section">
              <Text strong>对比来源</Text>
              <Text>{sourceResourceTitle}</Text>
            </div>
          ) : null}
          <div className="assistant-draft-detail-section">
            <Text strong>Payload</Text>
            <pre>{JSON.stringify(draft.payload ?? {}, null, 2)}</pre>
          </div>
          {diffs.length ? (
            <div className="assistant-draft-detail-section">
              <Text strong>字段差异</Text>
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
            </div>
          ) : null}
          {issues.length ? (
            <div className="assistant-draft-detail-section">
              <Text strong>校验问题</Text>
              <div className="assistant-action-draft-precheck-issues">
                {issues.map((issue) => (
                  <Text
                    key={`${issue.field}:${issue.message}`}
                    type={issue.severity === 'error' ? 'danger' : 'warning'}
                  >
                    {issue.message}
                  </Text>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </Modal>
  );
}
