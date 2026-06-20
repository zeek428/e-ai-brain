import { type AssistantToolResultItem } from '../../../services/aiBrain';

export function draftStatusLabel(status?: string) {
  if (status === 'confirmed' || status === 'applied') {
    return { color: 'green', text: '已应用' };
  }
  if (status === 'cancelled') {
    return { color: 'default', text: '已取消' };
  }
  if (status === 'expired') {
    return { color: 'orange', text: '已过期' };
  }
  if (status === 'failed') {
    return { color: 'red', text: '失败' };
  }
  if (status === 'unknown') {
    return { color: 'orange', text: '状态未知' };
  }
  return { color: 'blue', text: '待确认' };
}

export function assistantDraftId(
  draft?: Pick<AssistantToolResultItem, 'client_draft_id' | 'draft_id' | 'server_draft_id'>,
) {
  if (!draft) {
    return undefined;
  }
  return [draft.draft_id, draft.server_draft_id, draft.client_draft_id]
    .map((value) => String(value ?? '').trim())
    .find(Boolean);
}

export function draftRegeneratePrompt(draft: AssistantToolResultItem) {
  return `重新生成「${draft.title ?? '配置草案'}」草案`;
}
