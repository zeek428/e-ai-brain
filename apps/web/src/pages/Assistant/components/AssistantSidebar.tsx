import {
  AppstoreOutlined,
  BarChartOutlined,
  DownOutlined,
  MessageOutlined,
  PlusOutlined,
  UpOutlined,
} from '@ant-design/icons';
import { Button, Spin, Typography } from 'antd';
import { useMemo } from 'react';

import {
  type AssistantConversationSummary,
  type AssistantRoleQuickTaskGroup,
} from '../../../services/aiBrain';

const { Text, Title } = Typography;

type AssistantConversationDisplayItem = AssistantConversationSummary & {
  duplicateCount: number;
};

function conversationDedupKey(item: AssistantConversationSummary) {
  const normalizedTitle = (item.title || '').trim().replace(/\s+/g, ' ').toLocaleLowerCase();
  return normalizedTitle || item.id;
}

function dedupeConversationsForSidebar(
  conversations: AssistantConversationSummary[],
  activeConversationId?: string,
) {
  const grouped = new Map<string, AssistantConversationDisplayItem>();
  for (const conversation of conversations) {
    const key = conversationDedupKey(conversation);
    const existing = grouped.get(key);
    if (!existing) {
      grouped.set(key, {
        ...conversation,
        duplicateCount: 1,
      });
      continue;
    }
    existing.duplicateCount += 1;
    if (conversation.id === activeConversationId) {
      grouped.set(key, {
        ...conversation,
        duplicateCount: existing.duplicateCount,
      });
    }
  }
  return [...grouped.values()];
}

export function AssistantSidebar({
  conversationId,
  conversations,
  isLoadingConversations,
  isLoadingMetrics,
  onOpenConversation,
  onOpenDraftTemplateMarket,
  onOpenMetricsPanel,
  onStartNewConversation,
  onToggleRoleQuickTasks,
  onUseRoleTask,
  roleQuickTaskCount,
  roleQuickTaskGroups,
  roleQuickTasksExpanded,
}: {
  conversationId?: string;
  conversations: AssistantConversationSummary[];
  isLoadingConversations: boolean;
  isLoadingMetrics: boolean;
  onOpenConversation: (conversationId: string) => void;
  onOpenDraftTemplateMarket: () => void;
  onOpenMetricsPanel: () => void;
  onStartNewConversation: () => void;
  onToggleRoleQuickTasks: () => void;
  onUseRoleTask: (prompt: string) => void;
  roleQuickTaskCount: number;
  roleQuickTaskGroups: AssistantRoleQuickTaskGroup[];
  roleQuickTasksExpanded: boolean;
}) {
  const visibleConversations = useMemo(
    () => dedupeConversationsForSidebar(conversations, conversationId),
    [conversationId, conversations],
  );

  return (
    <aside className="assistant-sidebar">
      <Title level={3}>AI 助手</Title>
      <Button block icon={<PlusOutlined />} onClick={onStartNewConversation}>
        新对话
      </Button>
      <div className="assistant-history-panel">
        <div className="assistant-history-title">
          <Text strong>最近对话</Text>
          {isLoadingConversations ? <Spin size="small" /> : null}
        </div>
        <div className="assistant-history-list">
          {visibleConversations.length ? (
            visibleConversations.map((item) => (
              <Button
                block
                className={item.id === conversationId ? 'assistant-history-active' : undefined}
                icon={<MessageOutlined />}
                key={item.id}
                onClick={() => onOpenConversation(item.id)}
              >
                <span className="assistant-history-button-text">
                  <span>{item.title}</span>
                  <span>
                    {item.messageCount} 条
                    {item.duplicateCount > 1 ? ` · 合并 ${item.duplicateCount} 个重复` : ''}
                  </span>
                </span>
              </Button>
            ))
          ) : (
            <Text type="secondary">暂无历史对话</Text>
          )}
        </div>
      </div>
      {roleQuickTaskGroups.length ? (
        <div aria-label="角色快捷任务" className="assistant-role-task-panel">
          <div className="assistant-role-task-header">
            <span className="assistant-role-task-title">
              <Text strong>角色快捷任务</Text>
              <Text type="secondary">
                {`${roleQuickTaskGroups.length} 组 · ${roleQuickTaskCount} 项`}
              </Text>
            </span>
            <Button
              aria-label={roleQuickTasksExpanded ? '收起角色快捷任务' : '展开角色快捷任务'}
              icon={roleQuickTasksExpanded ? <UpOutlined /> : <DownOutlined />}
              size="small"
              type="text"
              onClick={onToggleRoleQuickTasks}
            >
              {roleQuickTasksExpanded ? '收起' : '展开'}
            </Button>
          </div>
          {roleQuickTasksExpanded ? (
            <div className="assistant-role-task-groups">
              {roleQuickTaskGroups.map((group) => (
                <div className="assistant-role-task-group" key={group.key}>
                  <Text type="secondary">{group.label}</Text>
                  <div className="assistant-role-task-list">
                    {group.tasks.map((task) => (
                      <Button
                        block
                        key={task.key}
                        size="small"
                        onClick={() => onUseRoleTask(task.prompt)}
                      >
                        {task.label}
                      </Button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      <div className="assistant-sidebar-more-panel">
        <div className="assistant-sidebar-section-header">
          <Text strong>更多能力</Text>
        </div>
        <div className="assistant-sidebar-tool-grid">
          <Button
            aria-label="草案模板市场"
            icon={<AppstoreOutlined />}
            onClick={onOpenDraftTemplateMarket}
          >
            草案模板
          </Button>
          <Button
            aria-label="查看助手效果指标"
            icon={<BarChartOutlined />}
            loading={isLoadingMetrics}
            onClick={onOpenMetricsPanel}
          >
            效果指标
          </Button>
        </div>
      </div>
    </aside>
  );
}
