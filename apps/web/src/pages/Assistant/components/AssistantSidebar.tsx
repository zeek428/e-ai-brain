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

export function AssistantSidebar({
  conversationId,
  conversations,
  isLoadingConversations,
  isLoadingMetrics,
  onToggleDuplicateConversations,
  onOpenConversation,
  onOpenDraftTemplateMarket,
  onOpenMetricsPanel,
  onStartNewConversation,
  onToggleRoleQuickTasks,
  onUseRoleTask,
  roleQuickTaskCount,
  roleQuickTaskGroups,
  roleQuickTasksExpanded,
  showDuplicateConversations,
}: {
  conversationId?: string;
  conversations: AssistantConversationSummary[];
  isLoadingConversations: boolean;
  isLoadingMetrics: boolean;
  onToggleDuplicateConversations: () => void;
  onOpenConversation: (conversationId: string) => void;
  onOpenDraftTemplateMarket: () => void;
  onOpenMetricsPanel: () => void;
  onStartNewConversation: () => void;
  onToggleRoleQuickTasks: () => void;
  onUseRoleTask: (prompt: string) => void;
  roleQuickTaskCount: number;
  roleQuickTaskGroups: AssistantRoleQuickTaskGroup[];
  roleQuickTasksExpanded: boolean;
  showDuplicateConversations: boolean;
}) {
  const collapsedDuplicateCount = useMemo(
    () => conversations.reduce((total, item) => total + Math.max(Number(item.duplicateCount ?? 1) - 1, 0), 0),
    [conversations],
  );

  return (
    <aside className="assistant-sidebar">
      <Title level={3}>AI 助手</Title>
      <Button block icon={<PlusOutlined />} onClick={onStartNewConversation}>
        新对话
      </Button>
      <div className="assistant-history-panel">
        <div className="assistant-history-title">
          <span className="assistant-history-heading">
            <Text strong>最近对话</Text>
            {!showDuplicateConversations && collapsedDuplicateCount ? (
              <Text type="secondary">{`已收起 ${collapsedDuplicateCount} 条重复`}</Text>
            ) : null}
          </span>
          {collapsedDuplicateCount || showDuplicateConversations ? (
            <Button
              size="small"
              type="text"
              onClick={onToggleDuplicateConversations}
            >
              {showDuplicateConversations ? '收起重复' : '展开重复'}
            </Button>
          ) : null}
          {isLoadingConversations ? <Spin size="small" /> : null}
        </div>
        <div className="assistant-history-list">
          {conversations.length ? (
            conversations.map((item) => (
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
                    {item.collapsedMessageCount ?? item.messageCount} 条
                    {Number(item.duplicateCount ?? 1) > 1 ? ` · 合并 ${item.duplicateCount} 个重复` : ''}
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
