import { message as toast } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';

import {
  fetchAssistantConversationMessages,
  fetchAssistantConversations,
  type AssistantChatResponse,
  type AssistantConversationMessage,
  type AssistantConversationSummary,
  type AssistantIntent,
  type AssistantReference,
  type AssistantToolResult,
} from '../../../services/aiBrain';
import { formatMutationError } from '../../../utils/managementCrud';

export type ChatMessage = {
  cancelledAt?: string;
  clientRequestId?: string;
  completedAt?: string;
  content: string;
  errorCode?: string;
  failedAt?: string;
  failedRequest?: {
    content: string;
    references: AssistantReference[];
  };
  id: string;
  intent?: AssistantIntent;
  references?: AssistantReference[];
  role: 'assistant' | 'user';
  runId?: string;
  status?: string;
  toolResults?: AssistantToolResult[];
};

export const welcomeMessages: ChatMessage[] = [
  {
    content: '我在，直接问我当前进展。',
    id: 'assistant-welcome',
    role: 'assistant',
  },
];

function assistantMessageToChatMessage(item: AssistantConversationMessage): ChatMessage {
  return {
    cancelledAt: item.cancelledAt,
    clientRequestId: item.clientRequestId,
    completedAt: item.completedAt,
    content: item.content,
    errorCode: item.errorCode,
    failedAt: item.failedAt,
    id: item.id,
    intent: item.intent,
    references: item.references,
    role: item.role,
    runId: item.runId,
    status: item.status,
    toolResults: item.toolResults,
  };
}

function latestAssistantResponse(
  history: AssistantConversationMessage[],
  conversationId: string,
): AssistantChatResponse | undefined {
  const latestAssistantMessage = [...history].reverse().find((item) => item.role === 'assistant');
  if (!latestAssistantMessage) {
    return undefined;
  }
  return {
    content: latestAssistantMessage.content,
    conversationId,
    intent: latestAssistantMessage.intent,
    latencyMs: 0,
    messageId: latestAssistantMessage.id,
    model: latestAssistantMessage.model ?? '',
    references: latestAssistantMessage.references,
    runId: latestAssistantMessage.runId,
    status: latestAssistantMessage.status,
    suggestions: latestAssistantMessage.suggestions,
    toolResults: latestAssistantMessage.toolResults,
  };
}

export function useAssistantConversation() {
  const loadConversationAbortRef = useRef<AbortController | null>(null);
  const loadConversationRequestSeqRef = useRef(0);
  const [conversationId, setConversationId] = useState<string>();
  const [conversations, setConversations] = useState<AssistantConversationSummary[]>([]);
  const [showDuplicateConversations, setShowDuplicateConversations] = useState(false);
  const [isLoadingConversations, setIsLoadingConversations] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [lastResponse, setLastResponse] = useState<AssistantChatResponse>();
  const [messages, setMessages] = useState<ChatMessage[]>(welcomeMessages);

  const fetchConversationList = useCallback(async (showDuplicates: boolean) => {
    return fetchAssistantConversations({ collapse: !showDuplicates });
  }, []);

  const loadConversations = useCallback(async () => {
    setIsLoadingConversations(true);
    try {
      setConversations(await fetchConversationList(showDuplicateConversations));
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setIsLoadingConversations(false);
    }
  }, [fetchConversationList, showDuplicateConversations]);

  const toggleDuplicateConversations = useCallback(() => {
    const nextShowDuplicates = !showDuplicateConversations;
    setShowDuplicateConversations(nextShowDuplicates);
    setIsLoadingConversations(true);
    fetchConversationList(nextShowDuplicates)
      .then(setConversations)
      .catch((error) => {
        toast.error(formatMutationError(error));
      })
      .finally(() => {
        setIsLoadingConversations(false);
      });
  }, [fetchConversationList, showDuplicateConversations]);

  const loadConversationMessages = useCallback(async (targetConversationId: string) => {
    loadConversationAbortRef.current?.abort();
    const requestSeq = loadConversationRequestSeqRef.current + 1;
    loadConversationRequestSeqRef.current = requestSeq;
    const controller = new AbortController();
    loadConversationAbortRef.current = controller;
    setIsLoadingMessages(true);
    try {
      const history = await fetchAssistantConversationMessages(
        targetConversationId,
        { signal: controller.signal },
      );
      if (loadConversationRequestSeqRef.current !== requestSeq) {
        return;
      }
      setMessages(history.length ? history.map(assistantMessageToChatMessage) : welcomeMessages);
      setLastResponse(latestAssistantResponse(history, targetConversationId));
    } catch (error) {
      if ((error as Error).name !== 'AbortError' && loadConversationRequestSeqRef.current === requestSeq) {
        toast.error(formatMutationError(error));
      }
    } finally {
      if (loadConversationRequestSeqRef.current === requestSeq) {
        setIsLoadingMessages(false);
      }
      if (loadConversationAbortRef.current === controller) {
        loadConversationAbortRef.current = null;
      }
    }
  }, []);

  useEffect(() => {
    let didCancel = false;
    fetchConversationList(false)
      .then((items) => {
        if (!didCancel) {
          setConversations(items);
        }
      })
      .catch((error) => {
        if (!didCancel) {
          toast.error(formatMutationError(error));
        }
      })
      .finally(() => {
        if (!didCancel) {
          setIsLoadingConversations(false);
        }
      });
    return () => {
      didCancel = true;
    };
  }, [fetchConversationList]);

  useEffect(() => () => {
    loadConversationAbortRef.current?.abort();
  }, []);

  return {
    conversationId,
    conversations,
    isLoadingConversations,
    isLoadingMessages,
    isSending,
    lastResponse,
    loadConversationMessages,
    loadConversations,
    messages,
    setConversationId,
    setIsSending,
    setLastResponse,
    setMessages,
    showDuplicateConversations,
    toggleDuplicateConversations,
  };
}
