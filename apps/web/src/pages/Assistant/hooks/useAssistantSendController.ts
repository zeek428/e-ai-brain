import { message as toast } from 'antd';
import { type Dispatch, type SetStateAction, useCallback, useEffect, useRef } from 'react';

import {
  cancelAssistantChatRun,
  chatWithAssistant,
  type AssistantChatResponse,
  type AssistantReference,
} from '../../../services/aiBrain';
import { formatMutationError } from '../../../utils/managementCrud';
import { assistantStopCommandRequested } from '../assistantCommandParsing';
import { type ChatMessage } from './useAssistantConversation';

type ActiveAssistantChatRequest = {
  clientRequestId: string;
  content: string;
  references: AssistantReference[];
  runId: string;
};

type SendMessageOptions = {
  replaceReferences?: boolean;
};

type UseAssistantSendControllerParams = {
  conversationId?: string;
  inputValue: string;
  isSending: boolean;
  loadConversations: () => Promise<void>;
  rememberReferences: (references: AssistantReference[]) => void;
  resolveCommandReferenceCandidates: (messageText: string) => Promise<AssistantReference[]>;
  selectedReferences: AssistantReference[];
  setActiveReferenceIndex: Dispatch<SetStateAction<number>>;
  setCommittedActionCommand: Dispatch<SetStateAction<string | undefined>>;
  setConversationId: Dispatch<SetStateAction<string | undefined>>;
  setDismissedReferencePickerValue: Dispatch<SetStateAction<string | undefined>>;
  setInputValue: Dispatch<SetStateAction<string>>;
  setIsAddMenuOpen: Dispatch<SetStateAction<boolean>>;
  setIsSending: Dispatch<SetStateAction<boolean>>;
  setLastResponse: Dispatch<SetStateAction<AssistantChatResponse | undefined>>;
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  setReferenceCandidates: Dispatch<SetStateAction<AssistantReference[]>>;
  setSelectedReferences: Dispatch<SetStateAction<AssistantReference[]>>;
};

function isAbortError(error: unknown) {
  return error instanceof Error && error.name === 'AbortError';
}

function assistantChatErrorMessage(error: unknown) {
  const detail = error as Error & { code?: string; traceId?: string };
  if (detail?.code === 'MODEL_GATEWAY_CONFIG_INVALID') {
    return [
      '模型网关未配置，当前仅支持 @ 动作、草案、运行诊断等规则能力。',
      '如需开放式问答，请到「系统管理 / 模型网关」配置默认模型后重试。',
      detail.traceId ? `trace_id=${detail.traceId}` : undefined,
    ].filter(Boolean).join(' ');
  }
  if (detail?.code === 'ASSISTANT_CHAT_FAILED') {
    return [
      'AI 助手调用模型失败，请检查模型网关连通性或稍后重试。',
      detail.traceId ? `trace_id=${detail.traceId}` : undefined,
    ].filter(Boolean).join(' ');
  }
  return formatMutationError(error);
}

function createAssistantChatRunId() {
  const randomId = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  return `assistant_chat_run_${randomId.replace(/[^a-zA-Z0-9_-]/g, '_')}`;
}

function referenceKey(reference: Pick<AssistantReference, 'id' | 'type'>) {
  return `${reference.type}:${reference.id}`;
}

function mergeReferences(...referenceLists: AssistantReference[][]) {
  const references: AssistantReference[] = [];
  const seen = new Set<string>();
  referenceLists.forEach((referenceList) => {
    referenceList.forEach((reference) => {
      const key = referenceKey(reference);
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      references.push(reference);
    });
  });
  return references;
}

export function useAssistantSendController({
  conversationId,
  inputValue,
  isSending,
  loadConversations,
  rememberReferences,
  resolveCommandReferenceCandidates,
  selectedReferences,
  setActiveReferenceIndex,
  setCommittedActionCommand,
  setConversationId,
  setDismissedReferencePickerValue,
  setInputValue,
  setIsAddMenuOpen,
  setIsSending,
  setLastResponse,
  setMessages,
  setReferenceCandidates,
  setSelectedReferences,
}: UseAssistantSendControllerParams) {
  const chatAbortControllerRef = useRef<AbortController | null>(null);
  const activeChatRequestRef = useRef<ActiveAssistantChatRequest | null>(null);

  const stopGenerating = useCallback(() => {
    const activeRequest = activeChatRequestRef.current;
    if (activeRequest?.runId) {
      void cancelAssistantChatRun(activeRequest.runId).catch(() => {
        // The browser-side abort is still useful even if the server run already finished.
      });
    }
    chatAbortControllerRef.current?.abort();
    chatAbortControllerRef.current = null;
    activeChatRequestRef.current = null;
    setIsSending(false);
    setInputValue((current) => (current.trim() ? current : activeRequest?.content ?? current));
    if (activeRequest?.references.length) {
      setSelectedReferences((current) => (
        current.length ? current : activeRequest.references
      ));
    }
    setReferenceCandidates([]);
    setActiveReferenceIndex(-1);
    setMessages((items) => [
      ...items.map((item) => (
        activeRequest?.runId && item.runId === activeRequest.runId
          ? { ...item, status: 'cancelled' }
          : item
      )),
      {
        clientRequestId: activeRequest?.clientRequestId,
        content: '已停止生成，可继续输入终止或新的指令。',
        id: `assistant-stopped-${Date.now()}`,
        role: 'assistant',
        runId: activeRequest?.runId,
        status: 'cancelled',
      },
    ]);
  }, [
    setActiveReferenceIndex,
    setInputValue,
    setIsSending,
    setMessages,
    setReferenceCandidates,
    setSelectedReferences,
  ]);

  const sendMessage = useCallback(async (
    messageText = inputValue,
    referenceOverrides?: AssistantReference[],
    options: SendMessageOptions = {},
  ) => {
    const content = messageText.trim();
    if (!content) {
      return;
    }
    if (isSending) {
      if (assistantStopCommandRequested(content)) {
        stopGenerating();
      }
      return;
    }

    const controller = new AbortController();
    const runId = createAssistantChatRunId();
    const clientRequestId = runId;
    let referencesForRequest = selectedReferences;
    chatAbortControllerRef.current?.abort();
    chatAbortControllerRef.current = controller;
    activeChatRequestRef.current = {
      clientRequestId,
      content,
      references: selectedReferences,
      runId,
    };
    setIsSending(true);

    try {
      const commandReferences = referenceOverrides
        ?? await resolveCommandReferenceCandidates(content);
      if (controller.signal.aborted) {
        return;
      }
      const baseReferences = options.replaceReferences ? [] : selectedReferences;
      referencesForRequest = mergeReferences(
        baseReferences,
        commandReferences,
      );
      activeChatRequestRef.current = {
        clientRequestId,
        content,
        references: referencesForRequest,
        runId,
      };
      rememberReferences(referencesForRequest);
      const userMessage: ChatMessage = {
        clientRequestId,
        content,
        id: `user-${Date.now()}`,
        references: referencesForRequest,
        role: 'user',
        runId,
        status: 'pending',
      };
      setMessages((items) => [...items, userMessage]);
      setInputValue('');
      setIsAddMenuOpen(false);
      setCommittedActionCommand(undefined);

      const response = await chatWithAssistant({
        clientRequestId,
        context: { source: 'assistant-page' },
        conversationId,
        message: content,
        references: referencesForRequest,
        runId,
        signal: controller.signal,
      });
      setConversationId(response.conversationId);
      setLastResponse(response);
      setActiveReferenceIndex(-1);
      setSelectedReferences([]);
      setReferenceCandidates([]);
      setMessages((items) => [
        ...items.map((item) => (
          item.runId === runId ? { ...item, status: 'completed' } : item
        )),
        {
          content: response.content,
          id: response.messageId,
          intent: response.intent,
          references: response.references,
          role: 'assistant',
          runId: response.runId ?? runId,
          status: response.status,
          toolResults: response.toolResults,
        },
      ]);
      await loadConversations();
    } catch (error) {
      if (isAbortError(error)) {
        return;
      }
      const errorMessage = assistantChatErrorMessage(error);
      toast.error(errorMessage);
      setMessages((items) => [
        ...items,
        {
          content: errorMessage,
          clientRequestId,
          failedRequest: {
            content,
            references: referencesForRequest,
          },
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
          runId,
          status: 'failed',
        },
      ]);
    } finally {
      if (chatAbortControllerRef.current === controller) {
        chatAbortControllerRef.current = null;
        activeChatRequestRef.current = null;
        setIsSending(false);
      }
    }
  }, [
    conversationId,
    inputValue,
    isSending,
    loadConversations,
    rememberReferences,
    resolveCommandReferenceCandidates,
    selectedReferences,
    setActiveReferenceIndex,
    setCommittedActionCommand,
    setConversationId,
    setInputValue,
    setIsAddMenuOpen,
    setIsSending,
    setLastResponse,
    setMessages,
    setReferenceCandidates,
    setSelectedReferences,
    stopGenerating,
  ]);

  const retryFailedRequest = useCallback((request: NonNullable<ChatMessage['failedRequest']>) => {
    void sendMessage(request.content, request.references, { replaceReferences: true });
  }, [sendMessage]);

  const restoreFailedRequest = useCallback((request: NonNullable<ChatMessage['failedRequest']>) => {
    setInputValue(request.content);
    setSelectedReferences(request.references);
    setReferenceCandidates([]);
    setActiveReferenceIndex(-1);
    setDismissedReferencePickerValue(undefined);
  }, [
    setActiveReferenceIndex,
    setDismissedReferencePickerValue,
    setInputValue,
    setReferenceCandidates,
    setSelectedReferences,
  ]);

  useEffect(() => () => {
    chatAbortControllerRef.current?.abort();
  }, []);

  return {
    restoreFailedRequest,
    retryFailedRequest,
    sendMessage,
    stopGenerating,
  };
}
