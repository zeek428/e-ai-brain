import {
  type AssistantReference,
  type AssistantToolResult,
  type AssistantToolResultItem,
} from '../../../services/aiBrain';
import { type QueryDraftResolution } from '../hooks/useAssistantDrafts';
import { assistantDraftId } from './draftPresentation';

export function actionDraftItems(toolResults?: AssistantToolResult[]) {
  return (toolResults ?? [])
    .filter((toolResult) => toolResult.tool === 'assistant.action_draft')
    .flatMap((toolResult) => toolResult.items ?? [])
    .map((item) => {
      const draftId = assistantDraftId(item);
      if (!draftId || item.draft_id === draftId) {
        return item;
      }
      return { ...item, draft_id: draftId };
    })
    .filter(
      (item) =>
        (
          item.action === 'create_scheduled_job'
          || item.action === 'create_ai_agent'
          || item.action === 'create_ai_skill'
          || item.action === 'create_plugin_action'
          || item.action === 'create_plugin_connection'
          || item.action === 'create_rd_task'
          || item.action === 'create_analysis_draft'
        )
        && assistantDraftId(item),
    );
}

function itemText(item: AssistantToolResultItem, field: string) {
  const value = item[field];
  if (Array.isArray(value)) {
    return value.length ? value.map((entry) => String(entry)).join('、') : '-';
  }
  return value === undefined || value === null || value === '' ? '-' : String(value);
}

export function pluginConnectionReferenceFromDiagnosticItem(
  item: AssistantToolResultItem,
): AssistantReference | undefined {
  const id = itemText(item, 'id');
  if (id === '-') {
    return undefined;
  }
  const title = itemText(item, 'title');
  const url = itemText(item, 'url');
  return {
    id,
    title: title === '-' ? id : title,
    type: 'plugin_connection',
    url: url === '-' ? `/tasks/plugins?connection_id=${encodeURIComponent(id)}` : url,
  };
}

export function pluginConnectionDiagnosticFollowupPrompt(
  item: AssistantToolResultItem,
  prompt: string,
) {
  const reference = pluginConnectionReferenceFromDiagnosticItem(item);
  return reference ? `@${reference.title} ${prompt}` : prompt;
}

export function queryDraftResolutionLabel(status: QueryDraftResolution['status']) {
  if (status === 'loading') {
    return { color: 'processing', text: '加载中' };
  }
  if (status === 'resolved') {
    return { color: 'green', text: '已加载' };
  }
  return { color: 'red', text: '加载失败' };
}

export function queryDraftResolutionText(resolution: QueryDraftResolution) {
  if (resolution.status === 'loading') {
    return `正在加载草案：${resolution.draftId}`;
  }
  if (resolution.status === 'resolved') {
    return `已从链接打开草案：${resolution.title || resolution.draftId}`;
  }
  return `草案加载失败：${resolution.draftId} ${resolution.message || '不存在或无权限'}`;
}
