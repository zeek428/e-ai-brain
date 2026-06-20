import { LinkOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Space, Spin, Tag, Typography } from 'antd';

import { type AssistantReference } from '../../../services/aiBrain';
import {
  referencePermissionTagColor,
  referenceSourceModule,
  referenceSummaryText,
  referenceTypeLabel,
  referenceUpdatedDate,
} from './referencePresentation';

const { Text } = Typography;

export type AssistantReferenceCandidateGroup = {
  items: Array<{
    index: number;
    reference: AssistantReference;
  }>;
  label: string;
  type: string;
};

export type AssistantReferenceEmptyState = {
  actionHref: string;
  actionLabel: string;
  description: string;
  prompt: string;
  promptLabel: string;
  title: string;
};

export function AssistantReferencePicker({
  activeMention,
  activeReferenceIndex,
  candidateGroups,
  emptyState,
  isLoading,
  referenceCount,
  onAddReference,
  onHoverReference,
  onUseEmptyPrompt,
}: {
  activeMention?: string;
  activeReferenceIndex: number;
  candidateGroups: AssistantReferenceCandidateGroup[];
  emptyState: AssistantReferenceEmptyState;
  isLoading: boolean;
  referenceCount: number;
  onAddReference: (reference: AssistantReference) => void;
  onHoverReference: (index: number) => void;
  onUseEmptyPrompt: () => void;
}) {
  return (
    <div
      aria-label="引用候选"
      className="assistant-reference-candidates"
    >
      <div className="assistant-reference-candidates-header">
        <Text strong>引用候选</Text>
        <Space size={8} wrap>
          {activeMention ? <Text type="secondary">{`搜索：${activeMention}`}</Text> : null}
          <Text type="secondary">↑↓ 选择，Enter 添加</Text>
        </Space>
      </div>
      {isLoading ? (
        <div className="assistant-reference-candidates-loading">
          <Spin size="small" />
          <Text type="secondary">正在搜索引用</Text>
        </div>
      ) : null}
      {!isLoading && !referenceCount ? (
        <div className="assistant-reference-candidates-empty">
          <Space orientation="vertical" size={8}>
            <Space size={[6, 6]} wrap>
              <Tag color="default">{emptyState.title}</Tag>
              <Text type="secondary">{emptyState.description}</Text>
            </Space>
            <Space className="assistant-reference-candidates-empty-actions" size={8} wrap>
              <Button href={emptyState.actionHref} size="small" type="link">
                {emptyState.actionLabel}
              </Button>
              <Button size="small" onClick={onUseEmptyPrompt}>
                {emptyState.promptLabel}
              </Button>
            </Space>
          </Space>
        </div>
      ) : null}
      <div className="assistant-reference-candidates-scroll">
        {candidateGroups.map((group) => (
          <div className="assistant-reference-candidate-group" key={group.type}>
            <div className="assistant-reference-candidate-group-title">
              <Text strong>{group.label}</Text>
              <Tag color="default">{group.items.length}</Tag>
            </div>
            {group.items.map(({ index: referenceIndex, reference }) => {
              const isActive = referenceIndex === activeReferenceIndex;
              return (
                <Button
                  className={isActive ? 'assistant-reference-candidate-active' : undefined}
                  icon={reference.type === 'assistant_action' ? <PlusOutlined /> : <LinkOutlined />}
                  key={`${reference.type}:${reference.id}`}
                  size="small"
                  onClick={() => onAddReference(reference)}
                  onMouseEnter={() => onHoverReference(referenceIndex)}
                >
                  <span className="assistant-reference-candidate-main">
                    <span className="assistant-reference-candidate-title">{reference.title}</span>
                    <span className="assistant-reference-candidate-chips">
                      <Tag color="default">{referenceTypeLabel(reference.type)}</Tag>
                      <Tag color={referencePermissionTagColor(reference)}>
                        权限：{reference.permission_label ?? '可引用'}
                      </Tag>
                      <Tag color="blue">
                        来源：{reference.source_module ?? referenceSourceModule(reference.type)}
                      </Tag>
                      <Tag color="default">
                        更新：{referenceUpdatedDate(reference) ?? '暂无'}
                      </Tag>
                    </span>
                    <span className="assistant-reference-candidate-summary">
                      {referenceSummaryText(reference)}
                    </span>
                  </span>
                </Button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
