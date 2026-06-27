import { message as toast } from 'antd';
import { type KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react';

import {
  consumeAssistantRoutePrompt,
  fetchAssistantReferenceCandidates,
  getStoredCurrentUser,
  type AssistantReference,
} from '../../../services/aiBrain';
import { formatMutationError } from '../../../utils/managementCrud';
import {
  activeMentionQuery,
  activeMentionRange,
  assistantStopCommandRequested,
  scheduledJobRunOnceRequested,
  uniqueScheduledJobReferenceCandidate,
} from '../assistantCommandParsing';
import { type AssistantReferenceEmptyState } from '../components/AssistantReferencePicker';
import { useAssistantReferences } from './useAssistantReferences';

const ASSISTANT_REFERENCE_CANDIDATE_DEBOUNCE_MS = 250;
const ASSISTANT_REFERENCE_CANDIDATE_LIMIT = 12;
const ASSISTANT_ADD_ACTION_LIMIT = 20;

const queryReferenceTypes = new Set([
  'ai_agent',
  'ai_skill',
  'ai_executor_runner',
  'ai_executor_task',
  'ai_task',
  'assistant_chat_run',
  'assistant_message',
  'audit_event',
  'code_inspection_report',
  'knowledge_chunk',
  'knowledge_document',
  'knowledge_folder',
  'knowledge_space',
  'model_gateway_log',
  'plugin_action',
  'plugin_connection',
  'plugin_invocation_log',
  'requirement',
  'result_write_record',
  'scheduled_job',
  'scheduled_job_run',
  'scheduled_job_stage',
]);

type AssistantComposerSubmitCallbacks = {
  sendMessage: (messageText?: string, referenceOverrides?: AssistantReference[]) => void;
  stopGenerating: () => void;
};

type AssistantRouteContext = {
  prompt?: string;
  referenceId?: string;
  referenceType?: string;
};

function referenceKey(reference: Pick<AssistantReference, 'id' | 'type'>) {
  return `${reference.type}:${reference.id}`;
}

function assistantRouteContext(): AssistantRouteContext {
  if (typeof window === 'undefined') {
    return {};
  }
  const params = new URLSearchParams(window.location.search);
  const referenceType = params.get('reference_type')?.trim();
  const referenceId = params.get('reference_id')?.trim();
  const pendingRoutePrompt = referenceType && referenceId
    ? consumeAssistantRoutePrompt({ referenceId, referenceType })
    : undefined;
  return {
    prompt: params.get('prompt')?.trim() || pendingRoutePrompt?.prompt,
    referenceId,
    referenceType,
  };
}

function assistantQueryReferenceParams(routeContext: AssistantRouteContext) {
  const { referenceId, referenceType } = routeContext;
  if (!referenceType || !referenceId || !queryReferenceTypes.has(referenceType)) {
    return undefined;
  }
  return {
    prompt: routeContext.prompt,
    referenceId,
    referenceType,
  };
}

function assistantInitialInputValue(routeContext: AssistantRouteContext) {
  return routeContext.prompt ?? '';
}

function assistantReferenceEmptyState(value: string): AssistantReferenceEmptyState {
  if (scheduledJobRunOnceRequested(value)) {
    return {
      actionHref: '/tasks/scheduled-jobs',
      actionLabel: '去任务中心新增定时作业',
      description: '请先新增或确认一个定时作业，再回到助手里 @ 它执行一次。',
      prompt: '我要新增任务，请先帮我选择任务类型并生成可确认的配置草案',
      promptLabel: '让 AI 生成任务草案',
      title: '没有找到可执行的定时作业引用',
    };
  }
  return {
    actionHref: '/knowledge/documents',
    actionLabel: '去知识库查看文档',
    description: '请换个关键词，或确认你是否有权限访问该对象。',
    prompt: '我要新增任务，请先帮我选择任务类型并生成可确认的配置草案',
    promptLabel: '让 AI 生成任务草案',
    title: '无匹配引用',
  };
}

function currentUserCanRunScheduledJobFromAssistant() {
  const currentUser = getStoredCurrentUser();
  const roles = new Set(currentUser?.roles ?? []);
  const permissions = new Set(currentUser?.permissions ?? []);
  return (
    roles.has('admin')
    || permissions.has('system.admin')
    || permissions.has('system.scheduled_jobs.run')
    || permissions.has('system.scheduled_jobs.manage')
  );
}

function isAssistantActionReference(reference: AssistantReference) {
  return reference.type === 'assistant_action';
}

function assistantActionCommand(reference: AssistantReference) {
  const title = String(reference.title || reference.id).replace(/\s+/g, '').trim();
  return title ? `@${title}` : '@动作';
}

function isScheduledJobCommandReference(reference: AssistantReference) {
  return reference.type === 'scheduled_job';
}

function scheduledJobCommand(reference: AssistantReference) {
  const title = String(reference.title || reference.id).replace(/\s+/g, ' ').trim();
  return title ? `@${title}` : '@定时作业';
}

function inputStartsWithActionCommand(value: string, command?: string) {
  if (!command || !value.startsWith(command)) {
    return false;
  }
  const nextChar = value[command.length];
  return nextChar === undefined || /\s/.test(nextChar);
}

function inputWithMentionCommand(currentValue: string, command: string) {
  const mention = activeMentionRange(currentValue);
  const userText = mention
    ? `${currentValue.slice(0, mention.markerIndex)}${currentValue.slice(mention.endIndex)}`
    : currentValue;
  const normalizedUserText = userText.replace(/[ \t]{2,}/g, ' ').trim();
  return normalizedUserText ? `${command} ${normalizedUserText}` : `${command} `;
}

function inputWithAssistantActionCommand(currentValue: string, reference: AssistantReference) {
  return inputWithMentionCommand(currentValue, assistantActionCommand(reference));
}

function inputWithScheduledJobCommand(currentValue: string, reference: AssistantReference) {
  return inputWithMentionCommand(currentValue, scheduledJobCommand(reference));
}

export function useAssistantComposerController({
  isSending,
}: {
  isSending: boolean;
}) {
  const {
    activeReferenceIndex,
    addActionCandidates,
    committedActionCommand,
    dismissedReferencePickerValue,
    isLoadingAddActions,
    isLoadingReferences,
    orderedReferenceCandidates,
    queryReferenceResolution,
    referenceCandidateGroups,
    referenceCandidates,
    rememberReferences,
    selectedReferenceKeys,
    selectedReferences,
    setActiveReferenceIndex,
    setAddActionCandidates,
    setCommittedActionCommand,
    setDismissedReferencePickerValue,
    setIsLoadingAddActions,
    setIsLoadingReferences,
    setQueryReferenceResolution,
    setReferenceCandidates,
    setSelectedReferences,
  } = useAssistantReferences();
  const [activeAddActionIndex, setActiveAddActionIndex] = useState(-1);
  const [addActionQuery, setAddActionQuery] = useState('');
  const [routeContext] = useState(assistantRouteContext);
  const [inputValue, setInputValue] = useState(() => assistantInitialInputValue(routeContext));
  const [isAddMenuOpen, setIsAddMenuOpen] = useState(false);
  const [isContextExpanded, setIsContextExpanded] = useState(false);
  const addMenuRef = useRef<HTMLDivElement | null>(null);
  const addMenuTriggerRef = useRef<HTMLElement | null>(null);
  const queryReferenceHydratedRef = useRef(false);

  const canSend = useMemo(() => inputValue.trim().length > 0, [inputValue]);
  const activeMention = useMemo(() => {
    const mention = activeMentionRange(inputValue);
    if (!mention) {
      return undefined;
    }
    if (
      mention.markerIndex === 0
      && inputStartsWithActionCommand(inputValue, committedActionCommand)
    ) {
      return undefined;
    }
    return mention.query;
  }, [committedActionCommand, inputValue]);
  const runOncePermissionHint = useMemo(() => (
    scheduledJobRunOnceRequested(inputValue) && !currentUserCanRunScheduledJobFromAssistant()
  ), [inputValue]);
  const shouldShowReferenceCandidates = !isAddMenuOpen
    && activeMention !== undefined
    && dismissedReferencePickerValue !== inputValue;
  const referenceEmptyState = useMemo(
    () => assistantReferenceEmptyState(inputValue),
    [inputValue],
  );

  useEffect(() => {
    if (
      committedActionCommand
      && !inputStartsWithActionCommand(inputValue, committedActionCommand)
    ) {
      setCommittedActionCommand(undefined);
    }
  }, [committedActionCommand, inputValue, setCommittedActionCommand]);

  useEffect(() => {
    if (!isAddMenuOpen) {
      return undefined;
    }
    const closeOnOutsideClick = (event: globalThis.MouseEvent | TouchEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (
        addMenuRef.current?.contains(target)
        || addMenuTriggerRef.current?.contains(target)
      ) {
        return;
      }
      setIsAddMenuOpen(false);
    };
    document.addEventListener('mousedown', closeOnOutsideClick);
    document.addEventListener('touchstart', closeOnOutsideClick);
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick);
      document.removeEventListener('touchstart', closeOnOutsideClick);
    };
  }, [isAddMenuOpen]);

  useEffect(() => {
    if (!isAddMenuOpen) {
      setAddActionCandidates([]);
      setIsLoadingAddActions(false);
      return undefined;
    }
    let didCancel = false;
    const controller = new AbortController();
    setIsLoadingAddActions(true);
    const timer = window.setTimeout(() => {
      fetchAssistantReferenceCandidates({
        limit: ASSISTANT_ADD_ACTION_LIMIT,
        query: addActionQuery,
        signal: controller.signal,
        type: 'assistant_action',
      })
        .then((items) => {
          if (!didCancel) {
            const actionItems = items.filter(isAssistantActionReference);
            setAddActionCandidates(actionItems);
            setActiveAddActionIndex(actionItems.length ? 0 : -1);
          }
        })
        .catch((error) => {
          if (!didCancel && (error as Error).name !== 'AbortError') {
            toast.error(formatMutationError(error));
            setAddActionCandidates([]);
            setActiveAddActionIndex(-1);
          }
        })
        .finally(() => {
          if (!didCancel) {
            setIsLoadingAddActions(false);
          }
        });
    }, ASSISTANT_REFERENCE_CANDIDATE_DEBOUNCE_MS);
    return () => {
      didCancel = true;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [
    addActionQuery,
    isAddMenuOpen,
    setAddActionCandidates,
    setIsLoadingAddActions,
  ]);

  useEffect(() => {
    if (queryReferenceHydratedRef.current) {
      return undefined;
    }
    const queryReference = assistantQueryReferenceParams(routeContext);
    if (!queryReference) {
      return undefined;
    }
    queryReferenceHydratedRef.current = true;
    let didCancel = false;
    setQueryReferenceResolution({
      referenceId: queryReference.referenceId,
      referenceType: queryReference.referenceType,
      status: 'loading',
    });
    fetchAssistantReferenceCandidates({
      limit: 1,
      query: queryReference.referenceId,
      type: queryReference.referenceType,
    })
      .then((items) => {
        if (didCancel) {
          return;
        }
        const reference = items.find(
          (item) => item.id === queryReference.referenceId && item.type === queryReference.referenceType,
        );
        if (!reference) {
          toast.warning('引用对象不存在或无权限');
          setQueryReferenceResolution({
            message: '不存在或无权限',
            referenceId: queryReference.referenceId,
            referenceType: queryReference.referenceType,
            status: 'failed',
          });
          return;
        }
        setQueryReferenceResolution({
          referenceId: queryReference.referenceId,
          referenceType: queryReference.referenceType,
          status: 'resolved',
          title: reference.title,
        });
        if (isAssistantActionReference(reference)) {
          const command = assistantActionCommand(reference);
          setCommittedActionCommand(command);
          setInputValue(inputWithAssistantActionCommand(queryReference.prompt ?? '', reference));
          return;
        }
        if (queryReference.prompt) {
          setInputValue(queryReference.prompt);
        }
        setSelectedReferences((currentItems) => (
          currentItems.some((item) => item.id === reference.id && item.type === reference.type)
            ? currentItems
            : [...currentItems, reference]
        ));
        rememberReferences([reference]);
      })
      .catch((error) => {
        if (!didCancel) {
          const messageText = formatMutationError(error);
          toast.error(messageText);
          setQueryReferenceResolution({
            message: messageText,
            referenceId: queryReference.referenceId,
            referenceType: queryReference.referenceType,
            status: 'failed',
          });
        }
      });
    return () => {
      didCancel = true;
    };
  }, [
    rememberReferences,
    setCommittedActionCommand,
    setQueryReferenceResolution,
    setSelectedReferences,
    routeContext,
  ]);

  useEffect(() => {
    const query = activeMention;
    if (query === undefined) {
      setReferenceCandidates([]);
      setIsLoadingReferences(false);
      return;
    }
    let didCancel = false;
    const controller = new AbortController();
    setIsLoadingReferences(true);
    const timer = window.setTimeout(() => {
      fetchAssistantReferenceCandidates({
        limit: ASSISTANT_REFERENCE_CANDIDATE_LIMIT,
        query,
        signal: controller.signal,
      })
        .then((items) => {
          if (!didCancel) {
            const nextCandidates = items.filter(
              (reference) => !selectedReferenceKeys.has(referenceKey(reference)),
            );
            setReferenceCandidates(nextCandidates);
            setActiveReferenceIndex(nextCandidates.length ? 0 : -1);
          }
        })
        .catch((error) => {
          if (!didCancel && (error as Error).name !== 'AbortError') {
            toast.error(formatMutationError(error));
            setReferenceCandidates([]);
          }
        })
        .finally(() => {
          if (!didCancel) {
            setIsLoadingReferences(false);
          }
        });
    }, ASSISTANT_REFERENCE_CANDIDATE_DEBOUNCE_MS);
    return () => {
      didCancel = true;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [
    activeMention,
    selectedReferenceKeys,
    setActiveReferenceIndex,
    setIsLoadingReferences,
    setReferenceCandidates,
  ]);

  useEffect(() => {
    setActiveReferenceIndex((index) => {
      if (!orderedReferenceCandidates.length) {
        return -1;
      }
      return Math.min(Math.max(index, 0), orderedReferenceCandidates.length - 1);
    });
  }, [orderedReferenceCandidates.length, setActiveReferenceIndex]);

  const resetComposerState = (options: { clearInput?: boolean } = {}) => {
    if (options.clearInput) {
      setInputValue('');
    }
    setActiveReferenceIndex(-1);
    setActiveAddActionIndex(-1);
    setAddActionQuery('');
    setIsAddMenuOpen(false);
    setReferenceCandidates([]);
    setCommittedActionCommand(undefined);
    setDismissedReferencePickerValue(undefined);
    setSelectedReferences([]);
    setQueryReferenceResolution(undefined);
    setIsContextExpanded(false);
  };

  const addSelectedReference = (reference: AssistantReference) => {
    if (isAssistantActionReference(reference)) {
      const command = assistantActionCommand(reference);
      const nextInputValue = inputWithAssistantActionCommand(inputValue, reference);
      setCommittedActionCommand(command);
      setInputValue(nextInputValue);
      setDismissedReferencePickerValue(nextInputValue);
      setActiveReferenceIndex(-1);
      setReferenceCandidates([]);
      return;
    }
    if (isScheduledJobCommandReference(reference)) {
      const command = scheduledJobCommand(reference);
      const nextInputValue = inputWithScheduledJobCommand(inputValue, reference);
      setCommittedActionCommand(command);
      setInputValue(nextInputValue);
      setDismissedReferencePickerValue(nextInputValue);
      setSelectedReferences((items) => (
        items.some((item) => item.id === reference.id && item.type === reference.type)
          ? items
          : [...items, reference]
      ));
      rememberReferences([reference]);
      setActiveReferenceIndex(-1);
      setReferenceCandidates([]);
      return;
    }
    setDismissedReferencePickerValue(inputValue);
    setSelectedReferences((items) => (
      items.some((item) => item.id === reference.id && item.type === reference.type)
        ? items
        : [...items, reference]
    ));
    rememberReferences([reference]);
    setActiveReferenceIndex(-1);
    setReferenceCandidates([]);
  };

  const toggleAddMenu = () => {
    const nextOpen = !isAddMenuOpen;
    setIsAddMenuOpen(nextOpen);
    if (!nextOpen) {
      setAddActionCandidates([]);
      return;
    }
    setAddActionQuery('');
    setAddActionCandidates([]);
    setActiveAddActionIndex(-1);
    setDismissedReferencePickerValue(inputValue);
    setReferenceCandidates([]);
    setActiveReferenceIndex(-1);
  };

  const changeAddActionQuery = (query: string) => {
    setAddActionQuery(query);
    setAddActionCandidates([]);
    setActiveAddActionIndex(-1);
  };

  const selectAddActionCandidate = (reference: AssistantReference) => {
    addSelectedReference(reference);
    setIsAddMenuOpen(false);
  };

  const handleAddActionMenuKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      setIsAddMenuOpen(false);
      return;
    }
    if (!addActionCandidates.length) {
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveAddActionIndex((index) => (index + 1) % addActionCandidates.length);
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveAddActionIndex((index) => (
        index <= 0 ? addActionCandidates.length - 1 : index - 1
      ));
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      const reference = addActionCandidates[Math.max(activeAddActionIndex, 0)];
      if (reference) {
        selectAddActionCandidate(reference);
      }
    }
  };

  const removeSelectedReference = (reference: AssistantReference) => {
    if (
      queryReferenceResolution?.referenceId === reference.id
      && queryReferenceResolution.referenceType === reference.type
    ) {
      setQueryReferenceResolution(undefined);
    }
    setSelectedReferences((items) => (
      items.filter((item) => !(item.id === reference.id && item.type === reference.type))
    ));
  };

  const commandReferenceCandidates = (messageText: string) => {
    if (!scheduledJobRunOnceRequested(messageText)) {
      return [];
    }
    const scheduledJobReference = uniqueScheduledJobReferenceCandidate(orderedReferenceCandidates);
    return scheduledJobReference ? [scheduledJobReference] : [];
  };

  const resolveCommandReferenceCandidates = async (messageText: string) => {
    const currentCandidates = commandReferenceCandidates(messageText);
    if (currentCandidates.length || !scheduledJobRunOnceRequested(messageText)) {
      return currentCandidates;
    }
    const query = activeMentionQuery(messageText);
    if (query === undefined) {
      return [];
    }
    try {
      const items = await fetchAssistantReferenceCandidates({
        limit: ASSISTANT_REFERENCE_CANDIDATE_LIMIT,
        query,
        type: 'scheduled_job',
      });
      const scheduledJobReference = uniqueScheduledJobReferenceCandidate(items);
      return scheduledJobReference ? [scheduledJobReference] : [];
    } catch {
      return [];
    }
  };

  const submitComposerEnter = (
    event: KeyboardEvent<HTMLTextAreaElement>,
    { sendMessage, stopGenerating }: AssistantComposerSubmitCallbacks,
  ) => {
    if (event.shiftKey || event.nativeEvent.isComposing) {
      return false;
    }
    event.preventDefault();
    if (isSending && assistantStopCommandRequested(inputValue)) {
      stopGenerating();
      return true;
    }
    if (scheduledJobRunOnceRequested(inputValue)) {
      const commandReferences = commandReferenceCandidates(inputValue);
      sendMessage(inputValue, commandReferences.length ? commandReferences : undefined);
      return true;
    }
    const reference = orderedReferenceCandidates[Math.max(activeReferenceIndex, 0)];
    if (reference) {
      addSelectedReference(reference);
      return true;
    }
    sendMessage();
    return true;
  };

  const handleComposerKeyDown = (
    event: KeyboardEvent<HTMLTextAreaElement>,
    callbacks: AssistantComposerSubmitCallbacks,
  ) => {
    if (event.defaultPrevented) {
      return;
    }
    if (event.key === 'Escape' && isAddMenuOpen) {
      event.preventDefault();
      setIsAddMenuOpen(false);
      return;
    }
    if (event.key === 'Enter' && submitComposerEnter(event, callbacks)) {
      return;
    }
    if (!orderedReferenceCandidates.length) {
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveReferenceIndex((index) => (index + 1) % orderedReferenceCandidates.length);
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveReferenceIndex((index) => (
        index <= 0 ? orderedReferenceCandidates.length - 1 : index - 1
      ));
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      setActiveReferenceIndex(-1);
      setReferenceCandidates([]);
    }
  };

  const prepareConversationSwitch = (options: { preserveComposer?: boolean } = {}) => {
    if (options.preserveComposer) {
      setIsAddMenuOpen(false);
      setReferenceCandidates([]);
      setActiveReferenceIndex(-1);
      setDismissedReferencePickerValue(inputValue);
      return;
    }
    resetComposerState({ clearInput: true });
  };

  const hasUnsentComposerState = () => (
    inputValue.trim().length > 0
    || selectedReferences.length > 0
    || Boolean(committedActionCommand)
    || Boolean(queryReferenceResolution)
  );

  const onChangeInput = (value: string) => {
    setInputValue(value);
    setDismissedReferencePickerValue(undefined);
  };

  return {
    activeAddActionIndex,
    activeMention,
    activeReferenceIndex,
    addActionCandidates,
    addActionQuery,
    addMenuRef,
    addMenuTriggerRef,
    addSelectedReference,
    canSend,
    changeAddActionQuery,
    commandReferenceCandidates,
    committedActionCommand,
    handleAddActionMenuKeyDown,
    handleComposerKeyDown,
    hasUnsentComposerState,
    inputValue,
    isAddMenuOpen,
    isContextExpanded,
    isLoadingAddActions,
    isLoadingReferences,
    onChangeInput,
    orderedReferenceCandidates,
    prepareConversationSwitch,
    queryReferenceResolution,
    referenceCandidateGroups,
    referenceCandidates,
    referenceEmptyState,
    rememberReferences,
    removeSelectedReference,
    resetComposerState,
    resolveCommandReferenceCandidates,
    runOncePermissionHint,
    selectAddActionCandidate,
    selectedReferenceKeys,
    selectedReferences,
    setActiveAddActionIndex,
    setActiveReferenceIndex,
    setCommittedActionCommand,
    setDismissedReferencePickerValue,
    setInputValue,
    setIsAddMenuOpen,
    setIsContextExpanded,
    setQueryReferenceResolution,
    setReferenceCandidates,
    setSelectedReferences,
    shouldShowReferenceCandidates,
    submitComposerEnter,
    toggleAddMenu,
  };
}
