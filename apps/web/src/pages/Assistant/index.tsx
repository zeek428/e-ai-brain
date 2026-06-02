import {
  ClockCircleOutlined,
  DatabaseOutlined,
  ProjectOutlined,
  RobotOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Input, Space, Spin, Tag, Typography, message as toast } from 'antd';
import { useMemo, useState } from 'react';

import { chatWithAssistant, type AssistantChatResponse } from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';

const { Text, Title } = Typography;
const { TextArea } = Input;

type ChatMessage = {
  content: string;
  id: string;
  role: 'assistant' | 'user';
};

const starterPrompts = [
  {
    icon: <ProjectOutlined />,
    label: '项目进展',
    prompt: 'AI Brain 项目现在开发到哪里了？',
  },
  {
    icon: <DatabaseOutlined />,
    label: '系统数据',
    prompt: '当前产品、需求、任务和知识沉淀情况如何？',
  },
  {
    icon: <ClockCircleOutlined />,
    label: '模型网关',
    prompt: '模型网关和 GitHub PR Review 链路现在是否可用？',
  },
];

function AssistantBubble({ message }: { message: ChatMessage }) {
  return (
    <div className={`assistant-bubble assistant-bubble-${message.role}`}>
      <div className="assistant-bubble-avatar">
        {message.role === 'assistant' ? <RobotOutlined /> : '我'}
      </div>
      <div className="assistant-bubble-content">
        <Text>{message.content}</Text>
      </div>
    </div>
  );
}

export default function AssistantPage() {
  const [conversationId, setConversationId] = useState<string>();
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [lastResponse, setLastResponse] = useState<AssistantChatResponse>();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      content: '我在，直接问我当前进展。',
      id: 'assistant-welcome',
      role: 'assistant',
    },
  ]);

  const canSend = useMemo(() => inputValue.trim().length > 0 && !isSending, [inputValue, isSending]);

  const sendMessage = async (messageText = inputValue) => {
    const content = messageText.trim();
    if (!content || isSending) {
      return;
    }
    const userMessage: ChatMessage = {
      content,
      id: `user-${Date.now()}`,
      role: 'user',
    };
    setMessages((items) => [...items, userMessage]);
    setInputValue('');
    setIsSending(true);
    try {
      const response = await chatWithAssistant({
        context: { source: 'assistant-page' },
        conversationId,
        message: content,
      });
      setConversationId(response.conversationId);
      setLastResponse(response);
      setMessages((items) => [
        ...items,
        {
          content: response.content,
          id: response.messageId,
          role: 'assistant',
        },
      ]);
    } catch (error) {
      toast.error(formatMutationError(error));
      setMessages((items) => [
        ...items,
        {
          content: formatMutationError(error),
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <PageContainer
      breadcrumb={{ items: [{ title: 'AI 助手' }] }}
      title={false}
    >
      <div className="assistant-workspace">
        <aside className="assistant-sidebar">
          <Title level={3}>AI 助手</Title>
          <div className="assistant-prompt-list">
            {starterPrompts.map((item) => (
              <Button
                block
                icon={item.icon}
                key={item.label}
                onClick={() => void sendMessage(item.prompt)}
              >
                {item.label}
              </Button>
            ))}
          </div>
          <div className="assistant-context-panel">
            <Text strong>上下文</Text>
            <Space size={[6, 6]} wrap>
              <Tag color="blue">AI Brain</Tag>
              <Tag color="green">项目进展</Tag>
              <Tag color="purple">模型网关</Tag>
              <Tag color="geekblue">GitHub PR</Tag>
            </Space>
          </div>
        </aside>
        <section className="assistant-chat-panel">
          <div className="assistant-chat-header">
            <div>
              <Title level={3}>研发助手</Title>
              <Text type="secondary">研发大脑系统问答</Text>
            </div>
            {lastResponse ? (
              <Space size={8} wrap>
                <Tag color="blue">{lastResponse.model}</Tag>
                <Tag>{lastResponse.latencyMs} ms</Tag>
              </Space>
            ) : null}
          </div>
          <div className="assistant-message-list" aria-live="polite">
            {messages.map((item) => (
              <AssistantBubble key={item.id} message={item} />
            ))}
            {isSending ? (
              <div className="assistant-thinking">
                <Spin size="small" />
                <Text type="secondary">生成中</Text>
              </div>
            ) : null}
          </div>
          {lastResponse?.suggestions.length ? (
            <div className="assistant-suggestions">
              {lastResponse.suggestions.map((suggestion) => (
                <Button key={suggestion} size="small" onClick={() => setInputValue(suggestion)}>
                  {suggestion}
                </Button>
              ))}
            </div>
          ) : null}
          <div className="assistant-composer">
            <TextArea
              aria-label="发送给 AI 助手"
              autoSize={{ maxRows: 5, minRows: 2 }}
              onChange={(event) => setInputValue(event.target.value)}
              onPressEnter={(event) => {
                if (!event.shiftKey) {
                  event.preventDefault();
                  void sendMessage();
                }
              }}
              placeholder="输入问题"
              value={inputValue}
            />
            <Button
              aria-label="发送"
              disabled={!canSend}
              icon={<SendOutlined />}
              loading={isSending}
              onClick={() => void sendMessage()}
              type="primary"
            >
              发送
            </Button>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
