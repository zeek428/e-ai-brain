import { fullChainSubjectHref, type AssistantReference } from '../../../services/aiBrain';
import { formatDisplayDate } from '../../../utils/dateTime';

export const ASSISTANT_KNOWLEDGE_CONTEXT_CHUNK_LIMIT = 8;

export function referenceTypeLabel(type: string) {
  const labels: Record<string, string> = {
    assistant_action: '动作',
    ai_agent: 'AI角色',
    ai_skill: 'Skill',
    ai_executor_runner: 'AI 执行器 Runner',
    ai_executor_task: 'AI 执行器任务',
    ai_task: '研发任务',
    assistant_chat_run: 'AI 助手运行',
    assistant_message: 'AI 助手消息',
    audit_event: '审计事件',
    branch_config: '代码分支',
    bug: '缺陷',
    code_inspection_report: '代码巡检',
    code_review_report: '代码评审',
    human_review: '确认',
    iteration_version: '迭代',
    knowledge_deposit: '知识沉淀',
    knowledge_chunk: '知识片段',
    knowledge_document: '知识文档',
    knowledge_folder: '知识目录',
    knowledge_space: '知识空间',
    model_gateway_log: '模型调用',
    plugin_action: '动作',
    plugin_connection: '插件连接',
    plugin_invocation_log: '插件调用',
    product: '产品',
    product_version_branch_config: '代码分支',
    requirement: '需求',
    result_write_record: '结果写入',
    scheduled_job: '定时作业',
    scheduled_job_run: '运行记录',
    scheduled_job_stage: '作业阶段',
  };
  return labels[type] ?? type;
}

export function referenceSourceModule(type: string) {
  const modules: Record<string, string> = {
    assistant_action: '动作',
    ai_agent: 'AI能力配置',
    ai_skill: 'AI能力配置',
    ai_executor_runner: '执行诊断',
    ai_executor_task: '执行诊断',
    ai_task: '需求交付',
    assistant_chat_run: '执行诊断',
    assistant_message: '执行诊断',
    audit_event: '审计与诊断',
    branch_config: '需求交付',
    bug: '需求交付',
    code_inspection_report: '执行诊断',
    code_review_report: '需求交付',
    human_review: '需求交付',
    iteration_version: '需求交付',
    knowledge_deposit: '知识库',
    knowledge_chunk: '知识库',
    knowledge_document: '知识库',
    knowledge_folder: '知识库',
    knowledge_space: '知识库',
    model_gateway_log: '执行诊断',
    plugin_action: '插件管理',
    plugin_connection: '插件管理',
    plugin_invocation_log: '执行诊断',
    product: '产品资产',
    product_version_branch_config: '需求交付',
    requirement: '需求交付',
    result_write_record: '执行诊断',
    scheduled_job: '任务中心',
    scheduled_job_run: '任务中心',
    scheduled_job_stage: '执行诊断',
  };
  return modules[type] ?? 'AI Brain';
}

export function referenceUpdatedDate(reference: AssistantReference) {
  const value = reference.updated_at ?? reference.created_at;
  if (!value) {
    return undefined;
  }
  return formatDisplayDate(value);
}

export function referencePermissionTagColor(reference: AssistantReference) {
  const label = String(reference.permission_label ?? '').toLowerCase();
  if (label.includes('无权限') || label.includes('denied') || label.includes('forbidden')) {
    return 'red';
  }
  if (label.includes('受限') || label.includes('limited')) {
    return 'orange';
  }
  return 'green';
}

export function referenceMetaText(reference: AssistantReference) {
  return [
    reference.source_module ?? referenceSourceModule(reference.type),
    reference.permission_label ?? '可引用',
    referenceUpdatedDate(reference),
  ].filter(Boolean).join(' · ');
}

export function referenceKnowledgeChunkCount(reference: AssistantReference) {
  if (reference.type === 'knowledge_chunk') {
    return 1;
  }
  if (!['knowledge_document', 'knowledge_folder', 'knowledge_space'].includes(reference.type)) {
    return 0;
  }
  return Number(reference.chunk_count ?? 0);
}

export function referenceInjectionText(reference: AssistantReference) {
  if (reference.type === 'assistant_action') {
    return '动作指令将填入输入框';
  }
  if (reference.type === 'knowledge_chunk') {
    return '1 个知识 chunk 将注入模型';
  }
  if (['knowledge_document', 'knowledge_folder', 'knowledge_space'].includes(reference.type)) {
    const chunkCount = referenceKnowledgeChunkCount(reference);
    if (chunkCount > ASSISTANT_KNOWLEDGE_CONTEXT_CHUNK_LIMIT) {
      return `最多 ${ASSISTANT_KNOWLEDGE_CONTEXT_CHUNK_LIMIT} 个知识 chunk 将按权限注入模型`;
    }
    return chunkCount > 0
      ? `${chunkCount} 个知识 chunk 将注入模型`
      : '知识元数据将注入模型';
  }
  return '引用元数据将注入模型';
}

export function selectedReferenceInjectionSummary(references: AssistantReference[]) {
  const knowledgeChunkCount = references.reduce(
    (total, reference) => total + referenceKnowledgeChunkCount(reference),
    0,
  );
  if (!knowledgeChunkCount) {
    return '元数据将注入模型';
  }
  if (knowledgeChunkCount > ASSISTANT_KNOWLEDGE_CONTEXT_CHUNK_LIMIT) {
    return `最多 ${ASSISTANT_KNOWLEDGE_CONTEXT_CHUNK_LIMIT} 个知识 chunk 将按权限注入模型`;
  }
  return `${knowledgeChunkCount} 个知识 chunk 将注入模型`;
}

export function referenceSummaryText(reference: AssistantReference) {
  const summary = String(reference.summary ?? '').trim();
  return summary || '暂无摘要，仅注入引用元数据。';
}

const fullChainReferenceSubjectTypes: Record<string, string> = {
  ai_task: 'ai_task',
  audit_event: 'audit_event',
  branch_config: 'branch_config',
  bug: 'bug',
  code_inspection_report: 'code_inspection_report',
  code_review_report: 'code_review_report',
  gitlab_mr_snapshot: 'gitlab_mr_snapshot',
  human_review: 'human_review',
  iteration_version: 'iteration_version',
  knowledge_deposit: 'knowledge_deposit',
  product_version: 'product_version',
  product_version_branch_config: 'product_version_branch_config',
  requirement: 'requirement',
};

export function assistantReferenceFullChainHref(reference: AssistantReference) {
  const subjectType = fullChainReferenceSubjectTypes[reference.type];
  if (!subjectType) {
    return undefined;
  }
  return fullChainSubjectHref(subjectType, reference.id);
}
