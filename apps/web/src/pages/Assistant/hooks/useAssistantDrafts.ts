import { useState } from 'react';

import {
  readAssistantDraftResolutions,
  type AssistantDraftResolutionMap,
  type AssistantToolResultItem,
} from '../../../services/aiBrain';

export type QueryDraftResolution = {
  draftId: string;
  message?: string;
  status: 'failed' | 'loading' | 'resolved';
  title?: string;
};

export function useAssistantDrafts() {
  const [draftMutationId, setDraftMutationId] = useState<string>();
  const [draftResolutionById, setDraftResolutionById] = useState<AssistantDraftResolutionMap>(
    () => readAssistantDraftResolutions(),
  );
  const [draftStatusById, setDraftStatusById] = useState<Record<string, string>>({});
  const [linkedDraft, setLinkedDraft] = useState<AssistantToolResultItem>();
  const [queryDraftResolution, setQueryDraftResolution] = useState<QueryDraftResolution>();

  return {
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
  };
}
