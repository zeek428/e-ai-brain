import type {
  AssistantScheduledJobDraft,
  PluginActionRecord,
} from '../../services/aiBrain';
import {
  recordFromDraftPayload,
  recordValue,
  stringArrayFromUnknown,
} from './components/scheduledJobFormTransformHelpers';

export function writeStrategyLabelFromAction(action: PluginActionRecord): string {
  const mapping = action.result_mapping ?? {};
  const writeTargetLabel = typeof mapping.write_target_label === 'string' ? mapping.write_target_label : undefined;
  const writeTarget = typeof mapping.write_target === 'string' ? mapping.write_target : undefined;
  return action.name || writeTargetLabel || writeTarget || action.id;
}

export function scheduledJobDraftHasReusableResponse(payload: Record<string, unknown>) {
  const configJson = recordFromDraftPayload(payload, 'config_json');
  const sampleReuse = recordValue(configJson?.sample_reuse);
  return Boolean(recordValue(sampleReuse?.response_summary));
}

type TemplateSelectableRecord = {
  code?: string;
  id?: string;
  name?: string;
  status?: string;
};

export function findByTemplateSelector<T extends TemplateSelectableRecord>(
  items: T[],
  selector: Record<string, unknown>,
): T | undefined {
  const codeCandidates = stringArrayFromUnknown(selector.code_candidates);
  const fallbackCodeCandidates = stringArrayFromUnknown(selector.fallback_code_candidates);
  const textCandidates = stringArrayFromUnknown(selector.text_candidates).map((candidate) =>
    candidate.toLowerCase(),
  );
  const isActive = (item: T) => item.status === 'active';
  const findByCodeCandidate = (candidates: string[], activeOnly: boolean) => {
    for (const candidate of candidates) {
      const matched = items.find((item) => {
        if (activeOnly && !isActive(item)) {
          return false;
        }
        return String(item.code ?? '') === candidate || String(item.id ?? '') === candidate;
      });
      if (matched) {
        return matched;
      }
    }
    return undefined;
  };
  const findByTextCandidate = (activeOnly: boolean) => {
    for (const candidate of textCandidates) {
      const matched = items.find((item) => {
        if (activeOnly && !isActive(item)) {
          return false;
        }
        const text = `${item.code ?? ''} ${item.name ?? ''} ${item.id ?? ''}`.toLowerCase();
        return text.includes(candidate);
      });
      if (matched) {
        return matched;
      }
    }
    return undefined;
  };
  return (
    findByCodeCandidate(codeCandidates, true)
    ?? findByCodeCandidate(codeCandidates, false)
    ?? findByTextCandidate(true)
    ?? findByTextCandidate(false)
    ?? findByCodeCandidate(fallbackCodeCandidates, true)
    ?? findByCodeCandidate(fallbackCodeCandidates, false)
    ?? items.find(isActive)
    ?? items[0]
  );
}

export function scheduledJobDraftRequestsAutoDryRun(draft: AssistantScheduledJobDraft) {
  if (draft.auto_dry_run === true) {
    return true;
  }
  if (draft.payload.auto_dry_run === true) {
    return true;
  }
  const configJson = recordFromDraftPayload(draft.payload, 'config_json');
  const sampleReuse = recordValue(configJson?.sample_reuse);
  return sampleReuse?.auto_dry_run === true;
}
