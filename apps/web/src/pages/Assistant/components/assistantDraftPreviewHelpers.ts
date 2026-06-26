import type { AssistantRepairAction } from '../../../services/aiBrain';

export function draftPreviewStatusLabel(status?: string) {
  if (status === 'blocked') {
    return { color: 'red', text: '阻塞' };
  }
  if (status === 'warning') {
    return { color: 'orange', text: '需确认' };
  }
  return { color: 'green', text: '通过' };
}

export function draftPreviewValueText(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  if (Array.isArray(value)) {
    return value.length ? value.map(String).join('、') : '-';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

export function assistantRepairActionUrl(action?: AssistantRepairAction) {
  if (!action || action.action !== 'open_plugin_connection_test' || !action.resource_id) {
    return undefined;
  }
  return `/tasks/plugins?connection_id=${encodeURIComponent(action.resource_id)}&open_test=1`;
}

export function assistantRepairActionPrompt(
  draftTitle: string | undefined,
  action: AssistantRepairAction,
) {
  const targetTitle = draftTitle ? `「${draftTitle}」` : '当前草案';
  if (action.action === 'generate_plugin_action_draft') {
    return `请为${targetTitle}补齐结果动作草案`;
  }
  if (action.action === 'generate_connection_draft') {
    return `请为${targetTitle}补齐数据连接草案`;
  }
  if (action.action === 'generate_ai_agent_draft') {
    return `请为${targetTitle}补齐 AI角色草案`;
  }
  if (action.action === 'generate_ai_skill_draft') {
    return `请为${targetTitle}补齐 AI Skill 草案`;
  }
  if (action.action === 'select_model_gateway') {
    return `请为${targetTitle}选择可用模型网关配置`;
  }
  if (action.action === 'edit_field') {
    return `请修正${targetTitle}的 ${action.field ?? '阻塞字段'}`;
  }
  return `请修复${targetTitle}的校验问题：${action.label ?? action.action}`;
}
