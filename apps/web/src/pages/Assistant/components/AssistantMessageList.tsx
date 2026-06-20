import { Spin, Typography } from 'antd';
import { type ReactNode, type RefObject } from 'react';

const { Text } = Typography;

export function AssistantMessageList({
  children,
  endRef,
  isLoadingMessages,
  isSending,
}: {
  children: ReactNode;
  endRef: RefObject<HTMLDivElement | null>;
  isLoadingMessages: boolean;
  isSending: boolean;
}) {
  return (
    <div className="assistant-message-list" aria-live="polite">
      {children}
      {isLoadingMessages ? (
        <div className="assistant-thinking">
          <Spin size="small" />
          <Text type="secondary">加载中</Text>
        </div>
      ) : null}
      {isSending ? (
        <div className="assistant-thinking">
          <Spin size="small" />
          <Text type="secondary">生成中</Text>
        </div>
      ) : null}
      <div ref={endRef} aria-hidden="true" />
    </div>
  );
}
