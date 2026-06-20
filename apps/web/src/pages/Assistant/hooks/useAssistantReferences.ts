import { useCallback, useMemo, useState } from 'react';

import {
  ASSISTANT_RECENT_REFERENCES_STORAGE_KEY,
  assistantScopedStorageKey,
  type AssistantReference,
} from '../../../services/aiBrain';
import { type AssistantReferenceCandidateGroup } from '../components/AssistantReferencePicker';
import { referenceTypeLabel } from '../components/referencePresentation';
import { type AssistantQueryReferenceResolution } from '../components/AssistantReferenceContext';

const MAX_RECENT_REFERENCES = 8;

function referenceKey(reference: Pick<AssistantReference, 'id' | 'type'>) {
  return `${reference.type}:${reference.id}`;
}

function normalizeRecentReferences(value: unknown): AssistantReference[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const references: AssistantReference[] = [];
  const seen = new Set<string>();
  value.forEach((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) {
      return;
    }
    const record = item as Partial<AssistantReference>;
    const id = String(record.id ?? '').trim();
    const title = String(record.title ?? '').trim();
    const type = String(record.type ?? '').trim();
    const url = String(record.url ?? '').trim();
    if (!id || !title || !type || !url) {
      return;
    }
    const reference: AssistantReference = {
      ...record,
      id,
      title,
      type,
      url,
    };
    const key = referenceKey(reference);
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    references.push(reference);
  });
  return references.slice(0, MAX_RECENT_REFERENCES);
}

function readRecentReferences() {
  if (typeof window === 'undefined') {
    return [];
  }
  try {
    return normalizeRecentReferences(
      JSON.parse(
        window.localStorage.getItem(assistantScopedStorageKey(ASSISTANT_RECENT_REFERENCES_STORAGE_KEY)) ?? '[]',
      ),
    );
  } catch {
    return [];
  }
}

function writeRecentReferences(references: AssistantReference[]) {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(
      assistantScopedStorageKey(ASSISTANT_RECENT_REFERENCES_STORAGE_KEY),
      JSON.stringify(references.slice(0, MAX_RECENT_REFERENCES)),
    );
  } catch {
    // Recent references are only a composer convenience.
  }
}

function nextRecentReferences(
  currentReferences: AssistantReference[],
  referencesToRemember: AssistantReference[],
) {
  const nextReferences = [...currentReferences];
  referencesToRemember.forEach((reference) => {
    const key = referenceKey(reference);
    const existingIndex = nextReferences.findIndex((item) => referenceKey(item) === key);
    if (existingIndex >= 0) {
      nextReferences.splice(existingIndex, 1);
    }
    nextReferences.unshift(reference);
  });
  return normalizeRecentReferences(nextReferences);
}

function orderReferenceCandidatesByRecent(
  references: AssistantReference[],
  recentReferences: AssistantReference[],
) {
  const recentOrderByKey = new Map(
    recentReferences.map((reference, index) => [referenceKey(reference), index]),
  );
  return references
    .map((reference, index) => ({
      index,
      recentIndex: recentOrderByKey.get(referenceKey(reference)),
      reference,
    }))
    .sort((left, right) => {
      const leftRecent = left.recentIndex ?? Number.MAX_SAFE_INTEGER;
      const rightRecent = right.recentIndex ?? Number.MAX_SAFE_INTEGER;
      if (leftRecent !== rightRecent) {
        return leftRecent - rightRecent;
      }
      return left.index - right.index;
    })
    .map((item) => item.reference);
}

function groupedReferenceCandidates(
  references: AssistantReference[],
  recentReferences: AssistantReference[],
): AssistantReferenceCandidateGroup[] {
  const groups: AssistantReferenceCandidateGroup[] = [];
  const recentReferenceKeys = new Set(recentReferences.map(referenceKey));
  const recentItems = references
    .map((reference, index) => ({ index, reference }))
    .filter(({ reference }) => recentReferenceKeys.has(referenceKey(reference)));
  if (recentItems.length) {
    groups.push({
      items: recentItems,
      label: '最近使用',
      type: '__recent__',
    });
  }
  const groupByType = new Map<string, AssistantReferenceCandidateGroup>();
  references.forEach((reference, index) => {
    if (recentReferenceKeys.has(referenceKey(reference))) {
      return;
    }
    let group = groupByType.get(reference.type);
    if (!group) {
      group = {
        items: [],
        label: referenceTypeLabel(reference.type),
        type: reference.type,
      };
      groupByType.set(reference.type, group);
      groups.push(group);
    }
    group.items.push({ index, reference });
  });
  return groups;
}

export function useAssistantReferences() {
  const [activeReferenceIndex, setActiveReferenceIndex] = useState(-1);
  const [addActionCandidates, setAddActionCandidates] = useState<AssistantReference[]>([]);
  const [committedActionCommand, setCommittedActionCommand] = useState<string>();
  const [dismissedReferencePickerValue, setDismissedReferencePickerValue] = useState<string>();
  const [isLoadingAddActions, setIsLoadingAddActions] = useState(false);
  const [isLoadingReferences, setIsLoadingReferences] = useState(false);
  const [queryReferenceResolution, setQueryReferenceResolution] = useState<AssistantQueryReferenceResolution>();
  const [referenceCandidates, setReferenceCandidates] = useState<AssistantReference[]>([]);
  const [recentReferences, setRecentReferences] = useState<AssistantReference[]>(() => readRecentReferences());
  const [selectedReferences, setSelectedReferences] = useState<AssistantReference[]>([]);

  const selectedReferenceKeys = useMemo(
    () => new Set(selectedReferences.map(referenceKey)),
    [selectedReferences],
  );
  const orderedReferenceCandidates = useMemo(
    () => orderReferenceCandidatesByRecent(referenceCandidates, recentReferences),
    [recentReferences, referenceCandidates],
  );
  const referenceCandidateGroups = useMemo(
    () => groupedReferenceCandidates(orderedReferenceCandidates, recentReferences),
    [orderedReferenceCandidates, recentReferences],
  );
  const rememberReferences = useCallback((references: AssistantReference[]) => {
    if (!references.length) {
      return;
    }
    setRecentReferences((items) => {
      const nextItems = nextRecentReferences(items, references);
      writeRecentReferences(nextItems);
      return nextItems;
    });
  }, []);

  return {
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
  };
}
