import { message as toast } from 'antd';
import { useEffect } from 'react';

import {
  cancelAssistantActionDraft,
  confirmAssistantActionDraft,
  getAssistantActionDraft,
  markAssistantActionDraftViewed,
  rememberAssistantDraftResolution,
  type AssistantActionDraftRecord,
  type AssistantDraftResolutionRecord,
  type AssistantDraftResourceType,
  type AssistantToolResultItem,
} from '../../../services/aiBrain';
import { formatMutationError } from '../../../utils/managementCrud';
import {
  assistantDraftId,
  draftRegeneratePrompt,
  draftStatusLabel,
} from '../components/draftPresentation';
import { useAssistantDrafts } from './useAssistantDrafts';

function assistantQueryDraftId() {
  if (typeof window === 'undefined') {
    return undefined;
  }
  return new URLSearchParams(window.location.search).get('draft_id')?.trim() || undefined;
}

export function assistantActionDraftRecordToToolItem(
  draft: AssistantActionDraftRecord,
): AssistantToolResultItem {
  return {
    action: draft.action,
    client_draft_id: draft.client_draft_id,
    draft_id: draft.id,
    payload: draft.payload,
    preview: draft.preview,
    requires_confirmation: true,
    risk_level: draft.risk_level,
    server_draft_id: draft.id,
    status: draft.status,
    title: draft.title,
    wizard_steps: draft.wizard_steps,
  };
}

function scheduledJobRunIdFromActionResult(result?: Record<string, unknown>) {
  const scheduledJobRun = result?.scheduled_job_run;
  if (!scheduledJobRun || typeof scheduledJobRun !== 'object' || Array.isArray(scheduledJobRun)) {
    return undefined;
  }
  const runId = String((scheduledJobRun as Record<string, unknown>).id ?? '').trim();
  return runId || undefined;
}

function assistantDraftResultRunResolution(
  draft: AssistantActionDraftRecord,
): AssistantDraftResolutionRecord | undefined {
  const run = draft.result_run;
  if (!run?.result_id || !run.result_type) {
    return undefined;
  }
  const resourceType = run.result_type as AssistantDraftResourceType;
  if (
    resourceType !== 'assistant_analysis'
    && resourceType !== 'ai_agent'
    && resourceType !== 'ai_skill'
    && resourceType !== 'ai_task'
    && resourceType !== 'plugin_action'
    && resourceType !== 'plugin_connection'
    && resourceType !== 'scheduled_job'
  ) {
    return undefined;
  }
  const resolution: AssistantDraftResolutionRecord = {
    resource_id: run.result_id,
    resource_type: resourceType,
    title: draft.title,
  };
  const scheduledJobRunId = scheduledJobRunIdFromActionResult(run.result);
  if (scheduledJobRunId) {
    resolution.scheduled_job_run_id = scheduledJobRunId;
  }
  return resolution;
}

function assistantDraftResolutionIds(
  draft: Pick<AssistantActionDraftRecord, 'client_draft_id' | 'id'>,
) {
  return [draft.id, draft.client_draft_id]
    .map((value) => (value ? String(value) : undefined))
    .filter(Boolean) as string[];
}

function persistedDraftResolutionIds(draft: AssistantToolResultItem) {
  return [draft.draft_id, draft.client_draft_id, draft.server_draft_id]
    .map((value) => (value ? String(value) : undefined))
    .filter(Boolean) as string[];
}

export function useAssistantDraftLifecycle({
  setInputValue,
}: {
  setInputValue: (value: string) => void;
}) {
  const {
    draftMutationId,
    draftResolutionById,
    draftStatusById,
    linkedDraft,
    queryDraftResolution,
    setDraftMutationId,
    setDraftResolutionById,
    setDraftStatusById,
    setLinkedDraft,
    setQueryDraftResolution,
  } = useAssistantDrafts();

  useEffect(() => {
    const draftId = assistantQueryDraftId();
    if (!draftId) {
      return undefined;
    }
    let didCancel = false;
    setQueryDraftResolution({
      draftId,
      status: 'loading',
    });
    getAssistantActionDraft(draftId)
      .then(async (draft) => {
        if (didCancel) {
          return;
        }
        let viewedDraft = draft;
        try {
          viewedDraft = await markAssistantActionDraftViewed(draft.id, 'deeplink');
        } catch (error) {
          toast.warning(formatMutationError(error));
        }
        if (didCancel) {
          return;
        }
        const toolItem = assistantActionDraftRecordToToolItem(viewedDraft);
        setLinkedDraft(toolItem);
        setDraftStatusById((items) => ({ ...items, [viewedDraft.id]: viewedDraft.status }));
        const resultResolution = assistantDraftResultRunResolution(viewedDraft);
        if (resultResolution) {
          const draftIds = assistantDraftResolutionIds(viewedDraft);
          draftIds.forEach((itemDraftId) => {
            rememberAssistantDraftResolution({
              draftId: itemDraftId,
              resourceId: resultResolution.resource_id,
              resourceType: resultResolution.resource_type,
              scheduledJobRunId: resultResolution.scheduled_job_run_id,
              title: resultResolution.title,
            });
          });
          setDraftResolutionById((items) => {
            const nextItems = { ...items };
            draftIds.forEach((itemDraftId) => {
              nextItems[itemDraftId] = resultResolution;
            });
            return nextItems;
          });
        }
        setQueryDraftResolution({
          draftId,
          status: 'resolved',
          title: viewedDraft.title,
        });
      })
      .catch((error) => {
        if (!didCancel) {
          const messageText = formatMutationError(error);
          toast.error(messageText);
          setQueryDraftResolution({
            draftId,
            message: messageText,
            status: 'failed',
          });
        }
      });
    return () => {
      didCancel = true;
    };
  }, [setDraftResolutionById, setDraftStatusById, setLinkedDraft, setQueryDraftResolution]);

  const rememberDraftResolution = (
    draft: AssistantToolResultItem,
    resourceId?: string,
    resourceType?: string,
    title?: string,
    scheduledJobRunId?: string,
  ) => {
    if (!resourceId) {
      return;
    }
    if (
      resourceType !== 'assistant_analysis'
      && resourceType !== 'ai_agent'
      && resourceType !== 'ai_skill'
      && resourceType !== 'ai_task'
      && resourceType !== 'plugin_action'
      && resourceType !== 'plugin_connection'
      && resourceType !== 'scheduled_job'
    ) {
      return;
    }
    const draftIds = new Set(persistedDraftResolutionIds(draft));
    draftIds.forEach((draftId) => {
      rememberAssistantDraftResolution({
        draftId,
        resourceId,
        resourceType,
        scheduledJobRunId,
        title,
      });
    });
    setDraftResolutionById((items) => {
      const resolution: AssistantDraftResolutionRecord = {
        resource_id: resourceId,
        resource_type: resourceType,
      };
      if (title) {
        resolution.title = title;
      }
      if (scheduledJobRunId) {
        resolution.scheduled_job_run_id = scheduledJobRunId;
      }
      const next = { ...items };
      draftIds.forEach((draftId) => {
        next[draftId] = resolution;
      });
      return next;
    });
  };

  const regenerateDraft = (draft: AssistantToolResultItem) => {
    setInputValue(draftRegeneratePrompt(draft));
  };

  const viewDraft = async (draft: AssistantToolResultItem) => {
    const draftId = assistantDraftId(draft);
    if (!draftId) {
      return draft;
    }
    try {
      const result = await markAssistantActionDraftViewed(draftId, 'detail_modal');
      const viewedItem = assistantActionDraftRecordToToolItem(result);
      const toolItem = {
        ...draft,
        ...viewedItem,
        payload: viewedItem.payload ?? draft.payload,
        preview: viewedItem.preview ?? draft.preview,
        wizard_steps: viewedItem.wizard_steps ?? draft.wizard_steps,
      };
      setDraftStatusById((items) => ({ ...items, [draftId]: result.status }));
      setLinkedDraft((currentDraft) => (
        assistantDraftId(currentDraft) === draftId ? toolItem : currentDraft
      ));
      return toolItem;
    } catch (error) {
      toast.warning(formatMutationError(error));
      return draft;
    }
  };

  const confirmDraft = async (draft: AssistantToolResultItem) => {
    const draftId = assistantDraftId(draft);
    if (!draftId) {
      return;
    }
    setDraftMutationId(draftId);
    try {
      const result = await confirmAssistantActionDraft(draftId);
      setDraftStatusById((items) => ({ ...items, [draftId]: result.draft.status }));
      setLinkedDraft((currentDraft) => (
        assistantDraftId(currentDraft) === draftId
          ? assistantActionDraftRecordToToolItem(result.draft)
          : currentDraft
      ));
      rememberDraftResolution(
        draft,
        result.run.result_id,
        result.run.result_type,
        result.draft.title,
        scheduledJobRunIdFromActionResult(result.run.result),
      );
      toast.success('草案已应用');
    } catch (error) {
      const errorMessage = formatMutationError(error);
      try {
        const latestDraft = await getAssistantActionDraft(draftId);
        const latestToolItem = assistantActionDraftRecordToToolItem(latestDraft);
        setDraftStatusById((items) => ({ ...items, [draftId]: latestDraft.status }));
        setLinkedDraft((currentDraft) => (
          assistantDraftId(currentDraft) === draftId
            ? latestToolItem
            : currentDraft
        ));
        toast.error(`${errorMessage}；已同步服务端草案状态：${draftStatusLabel(latestDraft.status).text}`);
      } catch {
        setDraftStatusById((items) => ({ ...items, [draftId]: 'unknown' }));
        toast.error(`${errorMessage}；确认状态未知，可重试。`);
      }
    } finally {
      setDraftMutationId(undefined);
    }
  };

  const cancelDraft = async (draft: AssistantToolResultItem) => {
    const draftId = assistantDraftId(draft);
    if (!draftId) {
      return;
    }
    setDraftMutationId(draftId);
    try {
      const result = await cancelAssistantActionDraft(draftId, '用户在 AI 助手取消');
      setDraftStatusById((items) => ({ ...items, [draftId]: result.status }));
      setLinkedDraft((currentDraft) => (
        assistantDraftId(currentDraft) === draftId
          ? assistantActionDraftRecordToToolItem(result)
          : currentDraft
      ));
      toast.success('草案已取消');
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setDraftMutationId(undefined);
    }
  };

  return {
    cancelDraft,
    confirmDraft,
    draftMutationId,
    draftResolutionById,
    draftStatusById,
    linkedDraft,
    queryDraftResolution,
    regenerateDraft,
    setDraftResolutionById,
    setDraftStatusById,
    setLinkedDraft,
    setQueryDraftResolution,
    viewDraft,
  };
}
