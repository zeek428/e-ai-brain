import {
  AppstoreOutlined,
  BarChartOutlined,
  DeleteOutlined,
  DownOutlined,
  MessageOutlined,
  PlusOutlined,
  UpOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Button, Popconfirm, Spin, Typography } from 'antd';
import { useMemo } from 'react';

import {
  type AssistantConversationSummary,
  type AssistantRoleQuickTaskGroup,
} from '../../../services/aiBrain';

const { Text, Title } = Typography;

export function AssistantSidebar({
  conversationId,
  conversations,
  deletingConversationIds,
  isLoadingConversations,
  isLoadingMoreConversations,
  isLoadingMetrics,
  isRefreshingRuntimeStatus,
  onToggleDuplicateConversations,
  onDeleteConversation,
  onOpenConversation,
  onOpenDraftTemplateMarket,
  onOpenMetricsPanel,
  onOpenRuntimeStatusPanel,
  onLoadMoreConversations,
  onStartNewConversation,
  onToggleRoleQuickTasks,
  onUseRoleTask,
  roleQuickTaskCount,
  roleQuickTaskGroups,
  roleQuickTasksExpanded,
  showDuplicateConversations,
  hasMoreConversations,
}: {
  conversationId?: string;
  conversations: AssistantConversationSummary[];
  deletingConversationIds: string[];
  hasMoreConversations: boolean;
  isLoadingConversations: boolean;
  isLoadingMoreConversations: boolean;
  isLoadingMetrics: boolean;
  isRefreshingRuntimeStatus?: boolean;
  onToggleDuplicateConversations: () => void;
  onDeleteConversation: (conversation: AssistantConversationSummary) => void;
  onOpenConversation: (conversationId: string) => void;
  onOpenDraftTemplateMarket: () => void;
  onOpenMetricsPanel: () => void;
  onOpenRuntimeStatusPanel: () => void;
  onLoadMoreConversations: () => void;
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
            <>
              {conversations.map((item) => {
                const deleteIds = item.collapsedConversationIds?.length
                  ? item.collapsedConversationIds
                  : [item.id];
                const deleteCount = deleteIds.length;
                const isDeleting = deleteIds.some((deleteId) => (
                  deletingConversationIds.includes(deleteId)
                ));
                return (
                  <div
                    className={item.id === conversationId
                      ? 'assistant-history-row assistant-history-active'
                      : 'assistant-history-row'}
                    key={item.id}
                  >
                    <Button
                      block
                      className="assistant-history-open-button"
                      icon={<MessageOutlined />}
                      onClick={() => onOpenConversation(item.id)}
                    >
                      <span className="assistant-history-button-text">
                        <span>{item.title}</span>
                        <span>
                          {item.collapsedMessageCount ?? item.messageCount} 条
                          {Number(item.duplicateCount ?? 1) > 1
                            ? ` · 合并 ${item.duplicateCount} 个重复`
                            : ''}
                        </span>
                      </span>
                    </Button>
                    <Popconfirm
                      cancelText="取消"
                      okButtonProps={{ danger: true, loading: isDeleting }}
                      okText="删除"
                      title={deleteCount > 1
                        ? `删除这组 ${deleteCount} 条对话记录？`
                        : `删除对话「${item.title}」？`}
                      onConfirm={() => onDeleteConversation(item)}
                    >
                      <Button
                        aria-label="删除对话"
                        className="assistant-history-delete-button"
                        danger
                        disabled={isDeleting}
                        icon={<DeleteOutlined />}
                        loading={isDeleting}
                        type="text"
                      />
                    </Popconfirm>
                  </div>
                );
              })}
              {hasMoreConversations ? (
                <Button
                  block
                  className="assistant-history-load-more"
                  loading={isLoadingMoreConversations}
                  size="small"
                  onClick={onLoadMoreConversations}
                >
                  加载更多
                </Button>
              ) : null}
            </>
          ) : isLoadingConversations ? (
            <Text type="secondary">历史对话加载中</Text>
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
          <Button
            aria-label="查看助手运行诊断"
            icon={<WarningOutlined />}
            loading={isRefreshingRuntimeStatus}
            onClick={onOpenRuntimeStatusPanel}
          >
            运行诊断
          </Button>
        </div>
      </div>
    </aside>
  );
}
