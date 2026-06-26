import type { AssistantToolResultItem } from '../../../services/aiBrain';

export type AssistantDraftWizardStep = {
  depends_on?: string[];
  key?: string;
  status?: string;
  summary?: string;
  title?: string;
};

export function draftWizardSteps(
  draft: AssistantToolResultItem,
  dependencyLabels: Map<string, string> = new Map(),
): AssistantDraftWizardStep[] {
  const value = draft.wizard_steps;
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter((item): item is Record<string, unknown> => (
      Boolean(item) && typeof item === 'object' && !Array.isArray(item)
    ))
    .map((item) => ({
      depends_on: Array.isArray(item.depends_on)
        ? item.depends_on.map((dependency) => {
          const dependencyId = String(dependency);
          return dependencyLabels.get(dependencyId) ?? dependencyId;
        })
        : [],
      key: item.key ? String(item.key) : undefined,
      status: item.status ? String(item.status) : undefined,
      summary: item.summary ? String(item.summary) : undefined,
      title: item.title ? String(item.title) : undefined,
    }));
}
