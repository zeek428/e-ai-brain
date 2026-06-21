import {
  CloseOutlined,
  LoadingOutlined,
  MessageOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { Button, Space, Tag, Typography } from 'antd';

import { type AssistantChatRun } from '../../../services/aiBrain';
import { formatDisplayDateTime } from '../../../utils/dateTime';

const { Text } = Typography;

function runStartedText(run: AssistantChatRun) {
  return formatDisplayDateTime(run.started_at ?? run.cancelled_at ?? run.finished_at);
}

function RunRecoveryItem({
  onOpenConversation,
  run,
}: {
  onOpenConversation: (conversationId: string) => void;
  run: AssistantChatRun;
}) {
  const isRunning = run.status === 'running';
  return (
    <div className="assistant-chat-run-recovery-item">
      <Space size={6} wrap>
        <Tag color={isRunning ? 'processing' : 'default'}>
          {isRunning ? '生成中' : '已停止'}
        </Tag>
        <Text className="assistant-chat-run-recovery-id" strong>
          {run.id}
        </Text>
        <Text type="secondary">{runStartedText(run)}</Text>
      </Space>
      {run.conversation_id ? (
        <Button
          icon={<MessageOutlined />}
          size="small"
          onClick={() => onOpenConversation(run.conversation_id!)}
        >
          打开会话
        </Button>
      ) : null}
    </div>
  );
}

export function AssistantChatRunRecovery({
  isLoading,
  isVisible,
  onDismiss,
  onOpenConversation,
  onRefresh,
  recentlyCancelledRuns,
  runningRuns,
}: {
  isLoading: boolean;
  isVisible: boolean;
  onDismiss: () => void;
  onOpenConversation: (conversationId: string) => void;
  onRefresh: () => void;
  recentlyCancelledRuns: AssistantChatRun[];
  runningRuns: AssistantChatRun[];
}) {
  const visibleRuns = [...runningRuns, ...recentlyCancelledRuns].slice(0, 4);
  if (!isVisible || !visibleRuns.length) {
    return null;
  }
  return (
    <div aria-label="聊天运行恢复" className="assistant-chat-run-recovery">
      <div className="assistant-chat-run-recovery-header">
        <Space size={8} wrap>
          {runningRuns.length ? <LoadingOutlined /> : null}
          <Text strong>
            {runningRuns.length ? '检测到未完成的助手运行' : '最近停止的助手运行'}
          </Text>
          {runningRuns.length ? <Tag color="processing">运行中 {runningRuns.length}</Tag> : null}
          {recentlyCancelledRuns.length ? (
            <Tag>最近停止 {recentlyCancelledRuns.length}</Tag>
          ) : null}
        </Space>
        <Space size={4}>
          <Button
            aria-label="刷新聊天运行恢复"
            icon={<ReloadOutlined />}
            loading={isLoading}
            size="small"
            type="text"
            onClick={onRefresh}
          />
          <Button
            aria-label="隐藏聊天运行恢复"
            icon={<CloseOutlined />}
            size="small"
            type="text"
            onClick={onDismiss}
          />
        </Space>
      </div>
      <div className="assistant-chat-run-recovery-list">
        {visibleRuns.map((run) => (
          <RunRecoveryItem
            key={run.id}
            run={run}
            onOpenConversation={onOpenConversation}
          />
        ))}
      </div>
    </div>
  );
}
