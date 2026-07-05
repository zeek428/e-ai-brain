import { PageContainer } from '@ant-design/pro-components';
import { Button, Modal, Space, Tag, Typography, message as toast } from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  fetchAssistantDraftTemplates,
  fetchAssistantRoleQuickTasks,
  fetchResultWriteTargets,
  getStoredCurrentUser,
  type AssistantConversationSummary,
  type AssistantDraftTemplate,
  type AssistantRoleQuickTaskGroup,
  type AssistantToolResultItem,
  type ResultWriteTargetRecord,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';
import { AssistantComposer } from './components/AssistantComposer';
import { AssistantChatRunRecovery } from './components/AssistantChatRunRecovery';
import { AssistantActionDraftCards } from './components/AssistantDraftCards';
import {
  actionDraftItems,
  pluginConnectionDiagnosticFollowupPrompt,
  pluginConnectionReferenceFromDiagnosticItem,
  queryDraftResolutionLabel,
  queryDraftResolutionText,
} from './components/assistantMessageHelpers';
import {
  AssistantBubble,
} from './components/AssistantMessageBubble';
import { AssistantMessageList } from './components/AssistantMessageList';
import { AssistantReferenceContext } from './components/AssistantReferenceContext';
import { AssistantRuntimeStatus } from './components/AssistantRuntimeStatus';
import { AssistantReferencePicker } from './components/AssistantReferencePicker';
import { AssistantSidebar } from './components/AssistantSidebar';
import {
  AssistantDraftTemplateMarket,
  AssistantMetricsPanel,
} from './components/WorkbenchPanels';
import { useAssistantConversation, welcomeMessages } from './hooks/useAssistantConversation';
import { useAssistantChatRuns } from './hooks/useAssistantChatRuns';
import { useAssistantComposerController } from './hooks/useAssistantComposerController';
import { useAssistantDraftLifecycle } from './hooks/useAssistantDraftLifecycle';
import { useAssistantMetricsPanel } from './hooks/useAssistantMetricsPanel';
import { useAssistantRuntimeStatus } from './hooks/useAssistantRuntimeStatus';
import { useAssistantRunPolling } from './hooks/useAssistantRunPolling';
import { useAssistantSendController } from './hooks/useAssistantSendController';
import {
  type AssistantScheduledJobRunItem,
  scheduledJobRunFollowupPrompt,
  scheduledJobRunItemFollowupPrompt,
  scheduledJobRunReferenceFromRunItem,
  scheduledJobRunReferenceFromToolItem,
} from './assistantRunPresentation';
import './Assistant.css';

const { Text, Title } = Typography;

export default function AssistantPage() {
  const {
    conversationId,
    conversations,
    deleteConversations,
    deletingConversationIds,
    hasMoreConversations,
    isLoadingConversations,
    isLoadingMoreConversations,
    isLoadingMessages,
    isSending,
    lastResponse,
    loadConversationMessages,
    loadConversations,
    loadMoreConversations,
    messages,
    setConversationId,
    setIsSending,
    setLastResponse,
    setMessages,
    showDuplicateConversations,
    toggleDuplicateConversations,
  } = useAssistantConversation();
  const {
    dismissRunRecovery,
    isLoadingChatRuns,
    isRecoveryDismissed,
    recentlyCancelledChatRuns,
    refreshChatRuns,
    runningChatRuns,
  } = useAssistantChatRuns({
    enabled: !isLoadingConversations && conversations.length > 0,
  });
  const {
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
    handleAddActionMenuKeyDown,
    handleComposerKeyDown,
    hasUnsentComposerState,
    inputValue,
    isAddMenuOpen,
    isContextExpanded,
    isLoadingAddActions,
    isLoadingReferences,
    onChangeInput,
    prepareConversationSwitch,
    queryReferenceResolution,
    referenceCandidateGroups,
    referenceCandidates,
    referenceEmptyState,
    rememberReferences,
    removeSelectedReference,
    resetComposerState: resetComposerControllerState,
    resolveCommandReferenceCandidates,
    runOncePermissionHint,
    selectAddActionCandidate,
    selectedReferences,
    setActiveAddActionIndex,
    setActiveReferenceIndex,
    setCommittedActionCommand,
    setDismissedReferencePickerValue,
    setInputValue,
    setIsAddMenuOpen,
    setIsContextExpanded,
    setReferenceCandidates,
    setSelectedReferences,
    shouldShowReferenceCandidates,
    submitComposerEnter,
    toggleAddMenu,
  } = useAssistantComposerController({ isSending });
  const {
    cancelDraft,
    confirmDraft,
    draftMutationId,
    draftResolutionById,
    draftStatusById,
    linkedDraft,
    queryDraftResolution,
    regenerateDraft,
    setLinkedDraft,
    setQueryDraftResolution,
    viewDraft,
  } = useAssistantDraftLifecycle({ setInputValue });
  const [draftTemplateMarketOpened, setDraftTemplateMarketOpened] = useState(false);
  const [draftTemplates, setDraftTemplates] = useState<AssistantDraftTemplate[]>([]);
  const [isLoadingDraftTemplates, setIsLoadingDraftTemplates] = useState(false);
  const {
    isRefreshingRuntimeStatus,
    refreshRuntimeStatus,
    runtimeStatus,
    runtimeStatusCheckedAt,
  } = useAssistantRuntimeStatus();
  const [runtimeStatusPanelOpen, setRuntimeStatusPanelOpen] = useState(false);
  const [resultWriteTargets, setResultWriteTargets] = useState<ResultWriteTargetRecord[]>([]);
  const [roleQuickTasksExpanded, setRoleQuickTasksExpanded] = useState(false);
  const [roleQuickTaskGroups, setRoleQuickTaskGroups] = useState<AssistantRoleQuickTaskGroup[]>([]);
  const { scheduledJobRunById } = useAssistantRunPolling(messages);
  const messageListEndRef = useRef<HTMLDivElement | null>(null);
  const queryDraftStatusRef = useRef<HTMLDivElement | null>(null);
  const draftTemplatesLoadRequestedRef = useRef(false);
  const resultWriteTargetsLoadRequestedRef = useRef(false);
  const roleQuickTasksLoadRequestedRef = useRef(false);
  const {
    assistantMetricDetails,
    assistantMetrics,
    assistantMetricsWindowDays,
    changeAssistantMetricsWindow,
    exportAssistantMetricsFile,
    isExportingMetrics,
    isLoadingMetricDetails,
    isLoadingMetrics,
    loadAssistantMetrics,
    metricsPanelOpened,
    openAssistantMetricDetails,
    openMetricsPanel,
    setMetricsPanelOpened,
  } = useAssistantMetricsPanel();
  const {
    restoreFailedRequest,
    retryFailedRequest,
    sendMessage,
    stopGenerating,
  } = useAssistantSendController({
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
  });

  const hasPluginActionDraft = useMemo(
    () => messages.some((item) => actionDraftItems(item.toolResults).some((draft) => draft.action === 'create_plugin_action')),
    [messages],
  );
  const resultWriteTargetLabels = useMemo(
    () => new Map(resultWriteTargets.map((target) => [target.code, target.form_label || target.label])),
    [resultWriteTargets],
  );
  const roleQuickTaskCount = useMemo(
    () => roleQuickTaskGroups.reduce((total, group) => total + group.tasks.length, 0),
    [roleQuickTaskGroups],
  );

  useEffect(() => {
    if (typeof messageListEndRef.current?.scrollIntoView !== 'function') {
      return;
    }
    if (queryDraftResolution && !isSending) {
      return;
    }
    messageListEndRef.current.scrollIntoView({ block: 'end' });
  }, [isLoadingMessages, isSending, messages, queryDraftResolution, scheduledJobRunById]);

  useEffect(() => {
    if (!queryDraftResolution || typeof queryDraftStatusRef.current?.scrollIntoView !== 'function') {
      return;
    }
    queryDraftStatusRef.current.scrollIntoView({ block: 'nearest' });
  }, [linkedDraft, queryDraftResolution]);

  useEffect(() => {
    if (!getStoredCurrentUser() || roleQuickTasksLoadRequestedRef.current) {
      return undefined;
    }
    let didCancel = false;
    roleQuickTasksLoadRequestedRef.current = true;
    fetchAssistantRoleQuickTasks()
      .then((groups) => {
        if (!didCancel) {
          setRoleQuickTaskGroups(groups);
        }
      })
      .catch(() => {
        if (!didCancel) {
          setRoleQuickTaskGroups([]);
        }
      });
    return () => {
      didCancel = true;
    };
  }, []);

  const loadDraftTemplates = useCallback(async () => {
    if (draftTemplatesLoadRequestedRef.current) {
      return;
    }
    draftTemplatesLoadRequestedRef.current = true;
    setIsLoadingDraftTemplates(true);
    try {
      setDraftTemplates(await fetchAssistantDraftTemplates());
    } catch (error) {
      draftTemplatesLoadRequestedRef.current = false;
      toast.error(formatMutationError(error));
    } finally {
      setIsLoadingDraftTemplates(false);
    }
  }, []);

  useEffect(() => {
    if (!hasPluginActionDraft || resultWriteTargetsLoadRequestedRef.current) {
      return;
    }
    let didCancel = false;
    resultWriteTargetsLoadRequestedRef.current = true;
    fetchResultWriteTargets()
      .then((items) => {
        if (!didCancel) {
          setResultWriteTargets(items);
        }
      })
      .catch((error) => {
        if (!didCancel) {
          toast.error(formatMutationError(error));
        }
      });
    return () => {
      didCancel = true;
    };
  }, [hasPluginActionDraft]);

  const resetComposerState = (options: { clearInput?: boolean; keepDraftLink?: boolean } = {}) => {
    resetComposerControllerState({ clearInput: options.clearInput });
    if (!options.keepDraftLink) {
      setLinkedDraft(undefined);
      setQueryDraftResolution(undefined);
    }
  };

  const startNewConversation = () => {
    setConversationId(undefined);
    setLastResponse(undefined);
    setMessages(welcomeMessages);
    resetComposerState({ clearInput: true });
  };

  const openDraftTemplateMarket = () => {
    setDraftTemplateMarketOpened(true);
    void loadDraftTemplates();
  };

  const openRuntimeStatusPanel = useCallback(() => {
    setRuntimeStatusPanelOpen(true);
    if (!runtimeStatus) {
      void refreshRuntimeStatus({ force: true });
    }
  }, [refreshRuntimeStatus, runtimeStatus]);

  const applyDraftTemplate = (template: AssistantDraftTemplate) => {
    setCommittedActionCommand(undefined);
    setInputValue(template.prompt);
  };

  const loadConversation = async (
    targetConversationId: string,
    options: { preserveComposer?: boolean } = {},
  ) => {
    prepareConversationSwitch(options);
    if (!options.preserveComposer) {
      setLinkedDraft(undefined);
      setQueryDraftResolution(undefined);
    }
    setConversationId(targetConversationId);
    await loadConversationMessages(targetConversationId);
  };

  const openConversation = (targetConversationId: string) => {
    if (targetConversationId === conversationId) {
      return;
    }
    if (!hasUnsentComposerState()) {
      void loadConversation(targetConversationId, { preserveComposer: false });
      return;
    }
    Modal.confirm({
      cancelText: '丢弃并切换',
      content: '当前输入框或引用上下文尚未发送，可以保留到目标会话，也可以丢弃后切换。',
      okText: '保留并切换',
      title: '切换历史会话',
      onCancel: () => {
        void loadConversation(targetConversationId, { preserveComposer: false });
      },
      onOk: () => {
        void loadConversation(targetConversationId, { preserveComposer: true });
      },
    });
  };

  const deleteConversation = (conversation: AssistantConversationSummary) => {
    const conversationIds = conversation.collapsedConversationIds?.length
      ? conversation.collapsedConversationIds
      : [conversation.id];
    void deleteConversations(conversationIds);
  };

  const useScheduledJobRunFollowupPrompt = (
    item: AssistantToolResultItem,
    prompt: string,
  ) => {
    const reference = scheduledJobRunReferenceFromToolItem(item);
    if (reference) {
      addSelectedReference(reference);
    }
    setInputValue(scheduledJobRunFollowupPrompt(item, prompt));
  };

  const useScheduledJobRunCardFollowupPrompt = (
    item: AssistantScheduledJobRunItem,
    prompt: string,
  ) => {
    addSelectedReference(scheduledJobRunReferenceFromRunItem(item));
    setInputValue(scheduledJobRunItemFollowupPrompt(item, prompt));
  };

  const usePluginConnectionFollowupPrompt = (
    item: AssistantToolResultItem,
    prompt: string,
  ) => {
    const reference = pluginConnectionReferenceFromDiagnosticItem(item);
    if (reference) {
      addSelectedReference(reference);
    }
    setInputValue(pluginConnectionDiagnosticFollowupPrompt(item, prompt));
  };

  return (
    <PageContainer title={false}>
      <div className="assistant-workspace">
        <AssistantSidebar
          conversationId={conversationId}
          conversations={conversations}
          deletingConversationIds={deletingConversationIds}
          hasMoreConversations={hasMoreConversations}
          isLoadingConversations={isLoadingConversations}
          isLoadingMoreConversations={isLoadingMoreConversations}
          isLoadingMetrics={isLoadingMetrics}
          isRefreshingRuntimeStatus={isRefreshingRuntimeStatus}
          showDuplicateConversations={showDuplicateConversations}
          roleQuickTaskCount={roleQuickTaskCount}
          roleQuickTaskGroups={roleQuickTaskGroups}
          roleQuickTasksExpanded={roleQuickTasksExpanded}
          onDeleteConversation={deleteConversation}
          onToggleDuplicateConversations={toggleDuplicateConversations}
          onLoadMoreConversations={loadMoreConversations}
          onOpenConversation={openConversation}
          onOpenDraftTemplateMarket={openDraftTemplateMarket}
          onOpenMetricsPanel={openMetricsPanel}
          onOpenRuntimeStatusPanel={openRuntimeStatusPanel}
          onStartNewConversation={startNewConversation}
          onToggleRoleQuickTasks={() => setRoleQuickTasksExpanded((expanded) => !expanded)}
          onUseRoleTask={setInputValue}
        />
        <section className="assistant-chat-panel">
          <div className="assistant-chat-header">
            <div className="assistant-chat-title-block">
              <Title className="assistant-chat-title" level={3}>研发助手</Title>
              <Text className="assistant-chat-subtitle" type="secondary">研发大脑系统问答</Text>
            </div>
            {lastResponse ? (
              <Space size={8} wrap>
                <Tag color="blue">{lastResponse.model}</Tag>
                <Tag>{lastResponse.latencyMs} ms</Tag>
              </Space>
            ) : null}
          </div>
          <AssistantChatRunRecovery
            isLoading={isLoadingChatRuns}
            isVisible={!isRecoveryDismissed}
            recentlyCancelledRuns={recentlyCancelledChatRuns}
            runningRuns={runningChatRuns}
            onDismiss={dismissRunRecovery}
            onOpenConversation={(targetConversationId) => {
              void loadConversation(targetConversationId, { preserveComposer: true });
            }}
            onRefresh={() => void refreshChatRuns()}
          />
          <AssistantMessageList
            endRef={messageListEndRef}
            isLoadingMessages={isLoadingMessages}
            isSending={isSending}
          >
            {queryDraftResolution ? (
              <div
                aria-label="草案链接状态"
                className={`assistant-query-draft-status assistant-query-draft-status-${queryDraftResolution.status}`}
                ref={queryDraftStatusRef}
              >
                <Space size={6} wrap>
                  <Tag color={queryDraftResolutionLabel(queryDraftResolution.status).color}>
                    {queryDraftResolutionLabel(queryDraftResolution.status).text}
                  </Tag>
                  <Text type={queryDraftResolution.status === 'failed' ? 'danger' : 'secondary'}>
                    {queryDraftResolutionText(queryDraftResolution)}
                  </Text>
                </Space>
                {linkedDraft ? (
                  <AssistantActionDraftCards
                    draftMutationId={draftMutationId}
                    draftResolutionById={draftResolutionById}
                    drafts={[linkedDraft]}
                    draftStatusById={draftStatusById}
                    onCancelDraft={cancelDraft}
                    onConfirmDraft={confirmDraft}
                    onRegenerateDraft={regenerateDraft}
                    onViewDraft={viewDraft}
                    onUseDraftWizardStepPrompt={setInputValue}
                    resultWriteTargetLabels={resultWriteTargetLabels}
                  />
                ) : null}
              </div>
            ) : null}
            {messages.map((item) => (
              <AssistantBubble
                draftMutationId={draftMutationId}
                draftResolutionById={draftResolutionById}
                draftStatusById={draftStatusById}
                key={item.id}
                message={item}
                onCancelDraft={cancelDraft}
                onConfirmDraft={confirmDraft}
                onRegenerateDraft={regenerateDraft}
                onRestoreFailedRequest={restoreFailedRequest}
                onRetryFailedRequest={retryFailedRequest}
                onViewDraft={viewDraft}
                onUseConnectionFollowupPrompt={usePluginConnectionFollowupPrompt}
                onUseRunCardFollowupPrompt={useScheduledJobRunCardFollowupPrompt}
                onUseRunFollowupPrompt={useScheduledJobRunFollowupPrompt}
                onUseTaskGuidePrompt={setInputValue}
                resultWriteTargetLabels={resultWriteTargetLabels}
                scheduledJobRunById={scheduledJobRunById}
              />
            ))}
          </AssistantMessageList>
          {lastResponse?.suggestions.length ? (
            <div className="assistant-suggestions">
              {lastResponse.suggestions.map((suggestion) => (
                <Button key={suggestion} size="small" onClick={() => setInputValue(suggestion)}>
                  {suggestion}
                </Button>
              ))}
            </div>
          ) : null}
          <AssistantReferenceContext
            isExpanded={isContextExpanded}
            queryReferenceResolution={queryReferenceResolution}
            selectedReferences={selectedReferences}
            onRemoveReference={removeSelectedReference}
            onToggleExpanded={() => setIsContextExpanded((expanded) => !expanded)}
          />
          <AssistantComposer
            addActionCandidates={addActionCandidates}
            activeAddActionIndex={activeAddActionIndex}
            addMenuRef={addMenuRef}
            addActionQuery={addActionQuery}
            canSend={canSend}
            inputValue={inputValue}
            isAddMenuOpen={isAddMenuOpen}
            isLoadingAddActions={isLoadingAddActions}
            isSending={isSending}
            referencePicker={shouldShowReferenceCandidates ? (
              <AssistantReferencePicker
                activeMention={activeMention}
                activeReferenceIndex={activeReferenceIndex}
                candidateGroups={referenceCandidateGroups}
                emptyState={referenceEmptyState}
                isLoading={isLoadingReferences}
                referenceCount={referenceCandidates.length}
                onAddReference={addSelectedReference}
                onHoverReference={setActiveReferenceIndex}
                onUseEmptyPrompt={() => {
                  setInputValue(referenceEmptyState.prompt);
                  setReferenceCandidates([]);
                  setActiveReferenceIndex(-1);
                  setDismissedReferencePickerValue(undefined);
                }}
              />
            ) : undefined}
            runOncePermissionHint={runOncePermissionHint}
            onChangeInput={onChangeInput}
            onChangeAddActionQuery={changeAddActionQuery}
            onCloseAddMenu={() => setIsAddMenuOpen(false)}
            onHoverAddAction={setActiveAddActionIndex}
            onAddActionMenuKeyDown={handleAddActionMenuKeyDown}
            onKeyDown={(event) => handleComposerKeyDown(event, {
              sendMessage: (messageText, references) => void sendMessage(messageText, references),
              stopGenerating,
            })}
            onPressEnter={(event) => {
              if (
                event.defaultPrevented
                || submitComposerEnter(event, {
                  sendMessage: (messageText, references) => void sendMessage(messageText, references),
                  stopGenerating,
                })
              ) {
                return;
              }
            }}
            onSelectAddActionCandidate={selectAddActionCandidate}
            onSend={() => void sendMessage()}
            onSetAddMenuTrigger={(node) => {
              addMenuTriggerRef.current = node;
            }}
            onStopSending={stopGenerating}
            onToggleAddMenu={toggleAddMenu}
          />
        </section>
      </div>
      <Modal
        className="assistant-workbench-modal"
        footer={null}
        open={draftTemplateMarketOpened}
        title="草案模板市场"
        width={720}
        onCancel={() => setDraftTemplateMarketOpened(false)}
      >
        <AssistantDraftTemplateMarket
          isLoading={isLoadingDraftTemplates}
          templates={draftTemplates}
          onUseTemplate={(template) => {
            applyDraftTemplate(template);
            setDraftTemplateMarketOpened(false);
          }}
        />
      </Modal>
      <Modal
        className="assistant-workbench-modal"
        footer={null}
        open={metricsPanelOpened}
        title="助手效果指标"
        width={760}
        onCancel={() => setMetricsPanelOpened(false)}
      >
        <AssistantMetricsPanel
          isDetailLoading={isLoadingMetricDetails}
          isExporting={isExportingMetrics}
          isLoading={isLoadingMetrics}
          metricDetails={assistantMetricDetails}
          metrics={assistantMetrics}
          onChangeWindow={changeAssistantMetricsWindow}
          onExport={exportAssistantMetricsFile}
          onOpenDetail={openAssistantMetricDetails}
          onRefresh={() => void loadAssistantMetrics()}
          windowDays={assistantMetricsWindowDays}
        />
      </Modal>
      <Modal
        className="assistant-workbench-modal"
        footer={null}
        open={runtimeStatusPanelOpen}
        title="运行诊断"
        width={860}
        onCancel={() => setRuntimeStatusPanelOpen(false)}
      >
        <AssistantRuntimeStatus
          checkedAt={runtimeStatusCheckedAt}
          isRefreshing={isRefreshingRuntimeStatus}
          runtimeStatus={runtimeStatus}
          showHealthy
          onRefresh={() => void refreshRuntimeStatus({ force: true })}
        />
      </Modal>
    </PageContainer>
  );
}
