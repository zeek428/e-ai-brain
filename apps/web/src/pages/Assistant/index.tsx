import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  LinkOutlined,
  MessageOutlined,
  PlusOutlined,
  ProjectOutlined,
  ReloadOutlined,
  RobotOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Input, Space, Spin, Tag, Typography, message as toast } from 'antd';
import { type KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
  ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
  ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
  cancelAssistantActionDraft,
  chatWithAssistant,
  confirmAssistantActionDraft,
  fetchAssistantConversationMessages,
  fetchAssistantConversations,
  fetchAssistantReferenceCandidates,
  fetchResultWriteTargets,
  readAssistantDraftResolutions,
  rememberAssistantDraftResolution,
  type AssistantChatResponse,
  type AssistantConversationMessage,
  type AssistantReference,
  type AssistantConversationSummary,
  type AssistantDraftResolutionMap,
  type AssistantDraftResolutionRecord,
  type AssistantToolResult,
  type AssistantToolResultItem,
  type ResultWriteTargetRecord,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';

const { Text, Title } = Typography;
const { TextArea } = Input;

type ChatMessage = {
  content: string;
  id: string;
  references?: AssistantReference[];
  role: 'assistant' | 'user';
  toolResults?: AssistantToolResult[];
};

const welcomeMessages: ChatMessage[] = [
  {
    content: '我在，直接问我当前进展。',
    id: 'assistant-welcome',
    role: 'assistant',
  },
];

const starterPrompts = [
  {
    icon: <ProjectOutlined />,
    label: '项目进展',
    prompt: 'AI Brain 项目现在开发到哪里了？',
  },
  {
    icon: <DatabaseOutlined />,
    label: '系统数据',
    prompt: '当前产品、需求、任务和知识沉淀情况如何？',
  },
  {
    icon: <ExclamationCircleOutlined />,
    label: '阻塞与待确认',
    prompt: '当前迭代有哪些阻塞需求、待确认 Review、代码评审结论和高风险 Bug？',
  },
  {
    icon: <ClockCircleOutlined />,
    label: '模型网关',
    prompt: '模型网关和 GitHub PR Review 链路现在是否可用？',
  },
];

const scheduledJobRunOnceKeywords = [
  '执行一次',
  '执行一下',
  '运行一次',
  '运行一下',
  '跑一次',
  '跑一下',
  '立即执行',
  '立即运行',
  '手动执行',
  'run once',
  'run now',
  'execute once',
];

function actionDraftItems(toolResults?: AssistantToolResult[]) {
  return (toolResults ?? [])
    .filter((toolResult) => toolResult.tool === 'assistant.action_draft')
    .flatMap((toolResult) => toolResult.items ?? [])
    .filter(
      (item) =>
        (
          item.action === 'create_scheduled_job'
          || item.action === 'create_plugin_action'
          || item.action === 'create_plugin_connection'
        )
        && item.draft_id,
    );
}

function taskCreationGuideItems(toolResults?: AssistantToolResult[]) {
  return (toolResults ?? [])
    .filter((toolResult) => toolResult.tool === 'assistant.task_creation_guide')
    .flatMap((toolResult) => toolResult.items ?? [])
    .filter((item) => item.title && item.prompt);
}

function itemText(item: AssistantToolResultItem, field: string) {
  const value = item[field];
  if (Array.isArray(value)) {
    return value.length ? value.map((entry) => String(entry)).join('、') : '-';
  }
  return value === undefined || value === null || value === '' ? '-' : String(value);
}

function draftPayloadText(payload: Record<string, unknown> | undefined, field: string) {
  const value = field.split('.').reduce<unknown>((current, key) => {
    if (!current || typeof current !== 'object' || Array.isArray(current)) {
      return undefined;
    }
    return (current as Record<string, unknown>)[key];
  }, payload);
  if (Array.isArray(value)) {
    return value.length ? value.join('、') : '-';
  }
  if (value && typeof value === 'object') {
    return JSON.stringify(value);
  }
  return value === undefined || value === null || value === '' ? '-' : String(value);
}

function draftPayloadLabel(
  payload: Record<string, unknown> | undefined,
  field: string,
  resultWriteTargetLabels: Map<string, string>,
) {
  const value = draftPayloadText(payload, field);
  if (field === 'result_mapping.write_target') {
    return resultWriteTargetLabels.get(value) ?? value;
  }
  return value;
}

function activeMentionQuery(value: string) {
  const markerIndex = value.lastIndexOf('@');
  if (markerIndex < 0) {
    return undefined;
  }
  const tail = value.slice(markerIndex + 1);
  if (tail.includes('\n')) {
    return undefined;
  }
  if (tail.length > 0 && /^\s/.test(tail)) {
    return undefined;
  }
  return tail.split(/\s+/)[0] ?? '';
}

function scheduledJobRunOnceRequested(value: string) {
  const normalized = value.toLowerCase();
  return scheduledJobRunOnceKeywords.some((keyword) => normalized.includes(keyword));
}

function mergeReferences(...referenceLists: AssistantReference[][]) {
  const references: AssistantReference[] = [];
  const seen = new Set<string>();
  referenceLists.forEach((referenceList) => {
    referenceList.forEach((reference) => {
      const key = `${reference.type}:${reference.id}`;
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      references.push(reference);
    });
  });
  return references;
}

function draftStatusLabel(status?: string) {
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
  return { color: 'blue', text: '待确认' };
}

function draftResourceLink(resolution?: AssistantDraftResolutionRecord) {
  if (!resolution) {
    return undefined;
  }
  if (resolution.resource_type === 'scheduled_job') {
    return {
      label: '打开定时作业',
      url: `/tasks/scheduled-jobs?job_id=${resolution.resource_id}`,
    };
  }
  if (resolution.resource_type === 'plugin_action') {
    return {
      label: '打开插件动作',
      url: `/tasks/plugins?action_id=${resolution.resource_id}`,
    };
  }
  return {
    label: '打开插件连接',
    url: `/tasks/plugins?connection_id=${resolution.resource_id}`,
  };
}

function draftRegeneratePrompt(draft: AssistantToolResultItem) {
  return `重新生成「${draft.title ?? '配置草案'}」草案`;
}

function referenceTypeLabel(type: string) {
  const labels: Record<string, string> = {
    ai_agent: 'AI角色',
    ai_skill: 'AI能力',
    ai_task: '任务',
    bug: '缺陷',
    code_review_report: '代码评审',
    human_review: '确认',
    iteration_version: '迭代',
    knowledge_deposit: '知识沉淀',
    knowledge_document: '知识文档',
    plugin_action: '插件动作',
    product: '产品',
    requirement: '需求',
    scheduled_job: '定时作业',
    scheduled_job_run: '运行记录',
  };
  return labels[type] ?? type;
}

function referenceSourceModule(type: string) {
  const modules: Record<string, string> = {
    ai_agent: 'AI能力配置',
    ai_skill: 'AI能力配置',
    ai_task: '需求交付',
    bug: '需求交付',
    code_review_report: '需求交付',
    human_review: '需求交付',
    iteration_version: '需求交付',
    knowledge_deposit: '知识库',
    knowledge_document: '知识库',
    plugin_action: '插件管理',
    product: '产品资产',
    requirement: '需求交付',
    scheduled_job: '任务中心',
    scheduled_job_run: '任务中心',
  };
  return modules[type] ?? 'AI Brain';
}

function referenceUpdatedDate(reference: AssistantReference) {
  const value = reference.updated_at ?? reference.created_at;
  if (!value) {
    return undefined;
  }
  const normalized = String(value);
  return /^\d{4}-\d{2}-\d{2}/.test(normalized) ? normalized.slice(0, 10) : normalized;
}

function referenceMetaText(reference: AssistantReference) {
  return [
    reference.source_module ?? referenceSourceModule(reference.type),
    reference.permission_label ?? '可引用',
    referenceUpdatedDate(reference),
  ].filter(Boolean).join(' · ');
}

function groupedReferenceCandidates(references: AssistantReference[]) {
  const groups: Array<{
    items: Array<{
      index: number;
      reference: AssistantReference;
    }>;
    label: string;
    type: string;
  }> = [];
  const groupByType = new Map<string, typeof groups[number]>();
  references.forEach((reference, index) => {
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

function storeScheduledJobDraft(draft: AssistantToolResultItem) {
  if (!draft.payload || typeof window === 'undefined') {
    return;
  }
  window.sessionStorage.setItem(
    ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
    JSON.stringify({
      draftId: draft.draft_id,
      payload: draft.payload,
      title: draft.title,
    }),
  );
}

function storePluginActionDraft(draft: AssistantToolResultItem) {
  if (!draft.payload || typeof window === 'undefined') {
    return;
  }
  window.sessionStorage.setItem(
    ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
    JSON.stringify({
      draftId: draft.draft_id,
      payload: draft.payload,
      title: draft.title,
    }),
  );
}

function storePluginConnectionDraft(draft: AssistantToolResultItem) {
  if (!draft.payload || typeof window === 'undefined') {
    return;
  }
  window.sessionStorage.setItem(
    ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
    JSON.stringify({
      draftId: draft.draft_id,
      payload: draft.payload,
      title: draft.title,
    }),
  );
}

function AssistantActionDraftCards({
  drafts,
  draftMutationId,
  draftResolutionById,
  draftStatusById,
  onCancelDraft,
  onConfirmDraft,
  onRegenerateDraft,
  resultWriteTargetLabels,
}: {
  draftMutationId?: string;
  draftResolutionById: AssistantDraftResolutionMap;
  drafts: AssistantToolResultItem[];
  draftStatusById: Record<string, string>;
  onCancelDraft: (draft: AssistantToolResultItem) => void;
  onConfirmDraft: (draft: AssistantToolResultItem) => void;
  onRegenerateDraft: (draft: AssistantToolResultItem) => void;
  resultWriteTargetLabels: Map<string, string>;
}) {
  if (!drafts.length) {
    return null;
  }
  return (
    <div className="assistant-action-draft-list">
      {drafts.map((draft) => {
        const payload = draft.payload;
        const isPluginActionDraft = draft.action === 'create_plugin_action';
        const isPluginConnectionDraft = draft.action === 'create_plugin_connection';
        const draftId = draft.draft_id;
        const resolution = draftId ? draftResolutionById[draftId] : undefined;
        const resourceLink = draftResourceLink(resolution);
        const currentStatus = resolution
          ? 'applied'
          : (draftId ? draftStatusById[draftId] : undefined) ?? draft.status ?? 'pending';
        const statusLabel = draftStatusLabel(currentStatus);
        const isPending = currentStatus === 'pending';
        return (
          <div className="assistant-action-draft-card" key={draftId}>
            <div className="assistant-action-draft-header">
              <Space size={8} wrap>
                <FileTextOutlined />
                <Text strong>{draft.title ?? '配置草案'}</Text>
                {draft.risk_level ? <Tag color="orange">风险：{draft.risk_level}</Tag> : null}
                {draft.requires_confirmation ? <Tag color={statusLabel.color}>{statusLabel.text}</Tag> : null}
              </Space>
              <Text type="secondary">
                {isPluginConnectionDraft
                  ? '确认前不会写入插件连接'
                  : isPluginActionDraft
                    ? '确认前不会写入插件动作'
                    : '确认前不会写入作业定义'}
              </Text>
            </div>
            <div className="assistant-action-draft-grid">
              {isPluginConnectionDraft ? (
                <>
                  <span>
                    <Text type="secondary">插件</Text>
                    <Text>{draftPayloadText(payload, 'plugin_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">Endpoint</Text>
                    <Text>{draftPayloadText(payload, 'endpoint_url')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">环境</Text>
                    <Text>{draftPayloadText(payload, 'environment')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">认证</Text>
                    <Text>{draftPayloadText(payload, 'auth_type')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">Params</Text>
                    <Text>{draftPayloadText(payload, 'request_config.query')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">Headers</Text>
                    <Text>{draftPayloadText(payload, 'request_config.headers')}</Text>
                  </span>
                </>
              ) : isPluginActionDraft ? (
                <>
                  <span>
                    <Text type="secondary">动作类型</Text>
                    <Text>{draftPayloadText(payload, 'action_type')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">编码</Text>
                    <Text>{draftPayloadText(payload, 'code')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">插件</Text>
                    <Text>{draftPayloadText(payload, 'plugin_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">连接</Text>
                    <Text>{draftPayloadText(payload, 'connection_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">请求方法</Text>
                    <Text>{draftPayloadText(payload, 'request_config.method')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">请求路径</Text>
                    <Text>{draftPayloadText(payload, 'request_config.path')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">写入目标</Text>
                    <Text>{draftPayloadLabel(payload, 'result_mapping.write_target', resultWriteTargetLabels)}</Text>
                  </span>
                </>
              ) : (
                <>
                  <span>
                    <Text type="secondary">作业类型</Text>
                    <Text>{draftPayloadText(payload, 'job_type')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">调度</Text>
                    <Text>{draftPayloadText(payload, 'cron_expression')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">执行模式</Text>
                    <Text>{draftPayloadText(payload, 'execution_mode')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">AI 模型</Text>
                    <Text>{draftPayloadText(payload, 'model_gateway_config_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">AI角色</Text>
                    <Text>{draftPayloadText(payload, 'agent_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">Skills</Text>
                    <Text>{draftPayloadText(payload, 'skill_ids')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">数据连接</Text>
                    <Text>{draftPayloadText(payload, 'plugin_connection_id')}</Text>
                  </span>
                  <span>
                    <Text type="secondary">结果动作</Text>
                    <Text>{draftPayloadText(payload, 'plugin_action_id')}</Text>
                  </span>
                  {draftPayloadText(payload, 'assistant_prerequisite_draft_ids') !== '-' ? (
                    <span>
                      <Text type="secondary">前置草案</Text>
                      <Text>{draftPayloadText(payload, 'assistant_prerequisite_draft_ids')}</Text>
                    </span>
                  ) : null}
                </>
              )}
            </div>
            <Space size={8} wrap>
              {draftId && isPending ? (
                <>
                  <Button
                    icon={<CheckCircleOutlined />}
                    loading={draftMutationId === draftId}
                    size="small"
                    type="primary"
                    onClick={() => onConfirmDraft(draft)}
                  >
                    确认创建
                  </Button>
                  <Button
                    icon={<CloseCircleOutlined />}
                    loading={draftMutationId === draftId}
                    size="small"
                    onClick={() => onCancelDraft(draft)}
                  >
                    取消
                  </Button>
                </>
              ) : null}
              {resourceLink ? (
                <Button
                  aria-label={resourceLink.label}
                  href={resourceLink.url}
                  icon={<LinkOutlined />}
                  size="small"
                >
                  {resourceLink.label}
                </Button>
              ) : null}
              {!resourceLink && isPluginConnectionDraft ? (
                <Button
                  href="/tasks/plugins"
                  size="small"
                  type="primary"
                  onMouseDown={() => storePluginConnectionDraft(draft)}
                  onClick={() => storePluginConnectionDraft(draft)}
                >
                  应用到插件连接表单
                </Button>
              ) : null}
              {!resourceLink && isPluginActionDraft ? (
                <Button
                  href="/tasks/plugins"
                  size="small"
                  type="primary"
                  onMouseDown={() => storePluginActionDraft(draft)}
                  onClick={() => storePluginActionDraft(draft)}
                >
                  应用到插件动作表单
                </Button>
              ) : null}
              {!resourceLink && !isPluginConnectionDraft && !isPluginActionDraft ? (
                <Button
                  href="/tasks/scheduled-jobs"
                  size="small"
                  type="primary"
                  onMouseDown={() => storeScheduledJobDraft(draft)}
                  onClick={() => storeScheduledJobDraft(draft)}
                >
                  应用到定时作业表单
                </Button>
              ) : null}
              <Button href={`/assistant?draft_id=${draft.draft_id}`} size="small">
                查看草案
              </Button>
              <Button
                aria-label="重新生成"
                icon={<ReloadOutlined />}
                size="small"
                onClick={() => onRegenerateDraft(draft)}
              >
                重新生成
              </Button>
            </Space>
          </div>
        );
      })}
    </div>
  );
}

function AssistantTaskCreationGuideCards({
  items,
  onUsePrompt,
}: {
  items: AssistantToolResultItem[];
  onUsePrompt: (prompt: string) => void;
}) {
  if (!items.length) {
    return null;
  }
  const defaultSteps = ['数据来源', 'AI处理', '结果动作', '调度策略', '确认执行'];
  return (
    <div className="assistant-task-guide">
      <div className="assistant-task-guide-header">
        <Space size={8} wrap>
          <ProjectOutlined />
          <Text strong>任务类型向导</Text>
          <Tag color="blue">草案优先</Tag>
        </Space>
        <Text type="secondary">{defaultSteps.join(' -> ')}</Text>
      </div>
      <div className="assistant-task-guide-grid">
        {items.map((item) => {
          const title = itemText(item, 'title');
          const prompt = itemText(item, 'prompt');
          const dependencies = itemText(item, 'dependencies');
          const wizardSteps = itemText(item, 'wizard_steps');
          return (
            <div className="assistant-task-guide-card" key={itemText(item, 'type')}>
              <div className="assistant-task-guide-card-title">
                <Text strong>{title}</Text>
                <Tag color={item.draft_action === 'create_scheduled_job' ? 'green' : 'default'}>
                  {itemText(item, 'draft_action')}
                </Tag>
              </div>
              <Text type="secondary">{itemText(item, 'description')}</Text>
              {dependencies !== '-' ? <Text>依赖：{dependencies}</Text> : null}
              <Text type="secondary">流程：{wizardSteps}</Text>
              <Button size="small" onClick={() => onUsePrompt(prompt)}>
                选择{title}
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AssistantBubble({
  draftMutationId,
  draftResolutionById,
  draftStatusById,
  message,
  onCancelDraft,
  onConfirmDraft,
  onRegenerateDraft,
  onUseTaskGuidePrompt,
  resultWriteTargetLabels,
}: {
  draftMutationId?: string;
  draftResolutionById: AssistantDraftResolutionMap;
  draftStatusById: Record<string, string>;
  message: ChatMessage;
  onCancelDraft: (draft: AssistantToolResultItem) => void;
  onConfirmDraft: (draft: AssistantToolResultItem) => void;
  onRegenerateDraft: (draft: AssistantToolResultItem) => void;
  onUseTaskGuidePrompt: (prompt: string) => void;
  resultWriteTargetLabels: Map<string, string>;
}) {
  const drafts = actionDraftItems(message.toolResults);
  const taskGuideItems = taskCreationGuideItems(message.toolResults);
  return (
    <div className={`assistant-bubble assistant-bubble-${message.role}`}>
      <div className="assistant-bubble-avatar">
        {message.role === 'assistant' ? <RobotOutlined /> : '我'}
      </div>
      <div className="assistant-bubble-content">
        <Text>{message.content}</Text>
        {message.references?.length ? (
          <div className="assistant-reference-list">
            {message.references.map((reference) => (
              <Button
                href={reference.url}
                icon={<LinkOutlined />}
                key={`${reference.type}:${reference.id}`}
                size="small"
                type="link"
              >
                {reference.title}
              </Button>
            ))}
          </div>
        ) : null}
        <AssistantActionDraftCards
          draftMutationId={draftMutationId}
          draftResolutionById={draftResolutionById}
          drafts={drafts}
          draftStatusById={draftStatusById}
          onCancelDraft={onCancelDraft}
          onConfirmDraft={onConfirmDraft}
          onRegenerateDraft={onRegenerateDraft}
          resultWriteTargetLabels={resultWriteTargetLabels}
        />
        <AssistantTaskCreationGuideCards
          items={taskGuideItems}
          onUsePrompt={onUseTaskGuidePrompt}
        />
      </div>
    </div>
  );
}

export default function AssistantPage() {
  const [conversationId, setConversationId] = useState<string>();
  const [conversations, setConversations] = useState<AssistantConversationSummary[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [draftMutationId, setDraftMutationId] = useState<string>();
  const [draftResolutionById, setDraftResolutionById] = useState<AssistantDraftResolutionMap>(
    () => readAssistantDraftResolutions(),
  );
  const [draftStatusById, setDraftStatusById] = useState<Record<string, string>>({});
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isLoadingReferences, setIsLoadingReferences] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [lastResponse, setLastResponse] = useState<AssistantChatResponse>();
  const [messages, setMessages] = useState<ChatMessage[]>(welcomeMessages);
  const [activeReferenceIndex, setActiveReferenceIndex] = useState(-1);
  const [referenceCandidates, setReferenceCandidates] = useState<AssistantReference[]>([]);
  const [resultWriteTargets, setResultWriteTargets] = useState<ResultWriteTargetRecord[]>([]);
  const [selectedReferences, setSelectedReferences] = useState<AssistantReference[]>([]);
  const resultWriteTargetsLoadRequestedRef = useRef(false);

  const canSend = useMemo(() => inputValue.trim().length > 0 && !isSending, [inputValue, isSending]);
  const hasPluginActionDraft = useMemo(
    () => messages.some((item) => actionDraftItems(item.toolResults).some((draft) => draft.action === 'create_plugin_action')),
    [messages],
  );
  const resultWriteTargetLabels = useMemo(
    () => new Map(resultWriteTargets.map((target) => [target.code, target.form_label || target.label])),
    [resultWriteTargets],
  );
  const selectedReferenceKeys = useMemo(
    () => new Set(selectedReferences.map((reference) => `${reference.type}:${reference.id}`)),
    [selectedReferences],
  );
  const referenceCandidateGroups = useMemo(
    () => groupedReferenceCandidates(referenceCandidates),
    [referenceCandidates],
  );
  const selectedKnowledgeChunkCount = useMemo(
    () => selectedReferences.reduce((total, reference) => total + Number(reference.chunk_count ?? 0), 0),
    [selectedReferences],
  );

  useEffect(() => {
    const query = activeMentionQuery(inputValue);
    if (query === undefined) {
      setReferenceCandidates([]);
      setIsLoadingReferences(false);
      return;
    }
    let didCancel = false;
    setIsLoadingReferences(true);
    fetchAssistantReferenceCandidates({
      limit: 6,
      query,
    })
      .then((items) => {
        if (!didCancel) {
          setReferenceCandidates(
            items.filter((reference) => !selectedReferenceKeys.has(`${reference.type}:${reference.id}`)),
          );
        }
      })
      .catch((error) => {
        if (!didCancel) {
          toast.error(formatMutationError(error));
          setReferenceCandidates([]);
        }
      })
      .finally(() => {
        if (!didCancel) {
          setIsLoadingReferences(false);
        }
      });
    return () => {
      didCancel = true;
    };
  }, [inputValue, selectedReferenceKeys]);

  useEffect(() => {
    setActiveReferenceIndex((index) => {
      if (!referenceCandidates.length) {
        return -1;
      }
      return Math.min(Math.max(index, 0), referenceCandidates.length - 1);
    });
  }, [referenceCandidates.length]);

  const loadConversations = useCallback(async () => {
    setIsLoadingConversations(true);
    try {
      setConversations(await fetchAssistantConversations());
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setIsLoadingConversations(false);
    }
  }, []);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

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

  const startNewConversation = () => {
    setConversationId(undefined);
    setLastResponse(undefined);
    setMessages(welcomeMessages);
    setActiveReferenceIndex(-1);
    setReferenceCandidates([]);
    setSelectedReferences([]);
  };

  const addSelectedReference = (reference: AssistantReference) => {
    setSelectedReferences((items) => (
      items.some((item) => item.id === reference.id && item.type === reference.type)
        ? items
        : [...items, reference]
    ));
    setActiveReferenceIndex(-1);
    setReferenceCandidates([]);
  };

  const removeSelectedReference = (reference: AssistantReference) => {
    setSelectedReferences((items) => (
      items.filter((item) => !(item.id === reference.id && item.type === reference.type))
    ));
  };

  const commandReferenceCandidates = (messageText: string) => {
    if (!scheduledJobRunOnceRequested(messageText)) {
      return [];
    }
    const activeReference = referenceCandidates[Math.max(activeReferenceIndex, 0)];
    const scheduledJobReference = activeReference?.type === 'scheduled_job'
      ? activeReference
      : referenceCandidates.find((reference) => reference.type === 'scheduled_job');
    return scheduledJobReference ? [scheduledJobReference] : [];
  };

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (!referenceCandidates.length) {
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveReferenceIndex((index) => (index + 1) % referenceCandidates.length);
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveReferenceIndex((index) => (
        index <= 0 ? referenceCandidates.length - 1 : index - 1
      ));
      return;
    }
    if (event.key === 'Enter') {
      const commandReferences = commandReferenceCandidates(inputValue);
      if (commandReferences.length) {
        event.preventDefault();
        void sendMessage(inputValue, commandReferences);
        return;
      }
      const reference = referenceCandidates[Math.max(activeReferenceIndex, 0)];
      if (reference) {
        event.preventDefault();
        addSelectedReference(reference);
      }
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      setActiveReferenceIndex(-1);
      setReferenceCandidates([]);
    }
  };

  const openConversation = async (targetConversationId: string) => {
    setConversationId(targetConversationId);
    setIsLoadingMessages(true);
    try {
      const history = await fetchAssistantConversationMessages(targetConversationId);
      setMessages(
        history.length
          ? history.map((item: AssistantConversationMessage) => ({
              content: item.content,
              id: item.id,
              references: item.references,
              role: item.role,
              toolResults: item.toolResults,
            }))
          : welcomeMessages,
      );
      const latestAssistantMessage = [...history].reverse().find((item) => item.role === 'assistant');
      setLastResponse(
        latestAssistantMessage
          ? {
              content: latestAssistantMessage.content,
              conversationId: targetConversationId,
              latencyMs: 0,
              messageId: latestAssistantMessage.id,
              model: latestAssistantMessage.model ?? '',
              references: latestAssistantMessage.references,
              suggestions: latestAssistantMessage.suggestions,
              toolResults: latestAssistantMessage.toolResults,
            }
          : undefined,
      );
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setIsLoadingMessages(false);
    }
  };

  const sendMessage = async (
    messageText = inputValue,
    referenceOverrides?: AssistantReference[],
  ) => {
    const content = messageText.trim();
    if (!content || isSending) {
      return;
    }
    const referencesForRequest = mergeReferences(
      selectedReferences,
      referenceOverrides ?? commandReferenceCandidates(content),
    );
    const userMessage: ChatMessage = {
      content,
      id: `user-${Date.now()}`,
      references: referencesForRequest,
      role: 'user',
    };
    setMessages((items) => [...items, userMessage]);
    setInputValue('');
    setIsSending(true);
    try {
      const response = await chatWithAssistant({
        context: { source: 'assistant-page' },
        conversationId,
        message: content,
        references: referencesForRequest,
      });
      setConversationId(response.conversationId);
      setLastResponse(response);
      setActiveReferenceIndex(-1);
      setSelectedReferences([]);
      setReferenceCandidates([]);
      setMessages((items) => [
        ...items,
        {
          content: response.content,
          id: response.messageId,
          references: response.references,
          role: 'assistant',
          toolResults: response.toolResults,
        },
      ]);
      await loadConversations();
    } catch (error) {
      toast.error(formatMutationError(error));
      setMessages((items) => [
        ...items,
        {
          content: formatMutationError(error),
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const rememberDraftResolution = (
    draft: AssistantToolResultItem,
    resourceId?: string,
    resourceType?: string,
    title?: string,
  ) => {
    if (!resourceId) {
      return;
    }
    if (
      resourceType !== 'plugin_action'
      && resourceType !== 'plugin_connection'
      && resourceType !== 'scheduled_job'
    ) {
      return;
    }
    const draftIds = new Set(
      [draft.draft_id, draft.client_draft_id, draft.server_draft_id]
        .map((value) => (value ? String(value) : undefined))
        .filter(Boolean) as string[],
    );
    draftIds.forEach((draftId) => {
      rememberAssistantDraftResolution({
        draftId,
        resourceId,
        resourceType,
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

  const confirmDraft = async (draft: AssistantToolResultItem) => {
    if (!draft.draft_id) {
      return;
    }
    const draftId = String(draft.draft_id);
    setDraftMutationId(draftId);
    try {
      const result = await confirmAssistantActionDraft(draftId);
      setDraftStatusById((items) => ({ ...items, [draftId]: result.draft.status }));
      rememberDraftResolution(
        draft,
        result.run.result_id,
        result.run.result_type,
        result.draft.title,
      );
      toast.success('草案已应用');
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setDraftMutationId(undefined);
    }
  };

  const cancelDraft = async (draft: AssistantToolResultItem) => {
    if (!draft.draft_id) {
      return;
    }
    const draftId = String(draft.draft_id);
    setDraftMutationId(draftId);
    try {
      const result = await cancelAssistantActionDraft(draftId, '用户在 AI 助手取消');
      setDraftStatusById((items) => ({ ...items, [draftId]: result.status }));
      toast.success('草案已取消');
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setDraftMutationId(undefined);
    }
  };

  return (
    <PageContainer
      breadcrumb={{ items: [{ title: 'AI 助手' }] }}
      title={false}
    >
      <div className="assistant-workspace">
        <aside className="assistant-sidebar">
          <Title level={3}>AI 助手</Title>
          <Button block icon={<PlusOutlined />} onClick={startNewConversation}>
            新对话
          </Button>
          <div className="assistant-prompt-list">
            {starterPrompts.map((item) => (
              <Button
                block
                icon={item.icon}
                key={item.label}
                onClick={() => void sendMessage(item.prompt)}
              >
                {item.label}
              </Button>
            ))}
          </div>
          <div className="assistant-history-panel">
            <div className="assistant-history-title">
              <Text strong>最近对话</Text>
              {isLoadingConversations ? <Spin size="small" /> : null}
            </div>
            <div className="assistant-history-list">
              {conversations.length ? (
                conversations.map((item) => (
                  <Button
                    block
                    className={item.id === conversationId ? 'assistant-history-active' : undefined}
                    icon={<MessageOutlined />}
                    key={item.id}
                    onClick={() => void openConversation(item.id)}
                  >
                    <span className="assistant-history-button-text">
                      <span>{item.title}</span>
                      <span>{item.messageCount} 条</span>
                    </span>
                  </Button>
                ))
              ) : (
                <Text type="secondary">暂无历史对话</Text>
              )}
            </div>
          </div>
          <div className="assistant-context-panel">
            <Text strong>上下文</Text>
            <Space size={[6, 6]} wrap>
              <Tag color="blue">AI Brain</Tag>
              <Tag color="green">项目进展</Tag>
              <Tag color="red">阻塞与待确认</Tag>
              <Tag color="purple">模型网关</Tag>
              <Tag color="geekblue">GitHub PR</Tag>
            </Space>
          </div>
        </aside>
        <section className="assistant-chat-panel">
          <div className="assistant-chat-header">
            <div>
              <Title level={3}>研发助手</Title>
              <Text type="secondary">研发大脑系统问答</Text>
            </div>
            {lastResponse ? (
              <Space size={8} wrap>
                <Tag color="blue">{lastResponse.model}</Tag>
                <Tag>{lastResponse.latencyMs} ms</Tag>
              </Space>
            ) : null}
          </div>
          <div className="assistant-message-list" aria-live="polite">
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
                onUseTaskGuidePrompt={setInputValue}
                resultWriteTargetLabels={resultWriteTargetLabels}
              />
            ))}
            {isLoadingMessages ? (
              <div className="assistant-thinking">
                <Spin size="small" />
                <Text type="secondary">加载中</Text>
              </div>
            ) : null}
            {isSending ? (
              <div className="assistant-thinking">
                <Spin size="small" />
                <Text type="secondary">生成中</Text>
              </div>
            ) : null}
          </div>
          {lastResponse?.suggestions.length ? (
            <div className="assistant-suggestions">
              {lastResponse.suggestions.map((suggestion) => (
                <Button key={suggestion} size="small" onClick={() => setInputValue(suggestion)}>
                  {suggestion}
                </Button>
              ))}
            </div>
          ) : null}
          {selectedReferences.length ? (
            <div className="assistant-selected-reference-list">
              <div className="assistant-selected-reference-header">
                <Text strong>本次上下文</Text>
                <Text type="secondary">
                  {selectedReferences.length} 个引用
                  {selectedKnowledgeChunkCount
                    ? ` · ${selectedKnowledgeChunkCount} 个知识 chunk 将注入模型`
                    : ' · 元数据将注入模型'}
                </Text>
              </div>
              <div className="assistant-selected-reference-tags">
                {selectedReferences.map((reference) => (
                  <Tag
                    closable
                    color="blue"
                    key={`${reference.type}:${reference.id}`}
                    onClose={() => removeSelectedReference(reference)}
                  >
                    {reference.title}
                    <Text type="secondary"> {referenceTypeLabel(reference.type)}</Text>
                  </Tag>
                ))}
              </div>
            </div>
          ) : null}
          {referenceCandidates.length || isLoadingReferences ? (
            <div
              aria-label="引用候选"
              className="assistant-reference-candidates"
            >
              <div className="assistant-reference-candidates-header">
                <Text strong>引用候选</Text>
                <Text type="secondary">↑↓ 选择，Enter 添加</Text>
              </div>
              {isLoadingReferences ? <Spin size="small" /> : null}
              {referenceCandidateGroups.map((group) => (
                <div className="assistant-reference-candidate-group" key={group.type}>
                  <div className="assistant-reference-candidate-group-title">
                    <Text strong>{group.label}</Text>
                    <Tag color="default">{group.items.length}</Tag>
                  </div>
                  {group.items.map(({ index: referenceIndex, reference }) => {
                    const isActive = referenceIndex === activeReferenceIndex;
                    return (
                      <Button
                        className={isActive ? 'assistant-reference-candidate-active' : undefined}
                        icon={<LinkOutlined />}
                        key={`${reference.type}:${reference.id}`}
                        size="small"
                        onClick={() => addSelectedReference(reference)}
                        onMouseEnter={() => setActiveReferenceIndex(referenceIndex)}
                      >
                        <span className="assistant-reference-candidate-main">
                          <span className="assistant-reference-candidate-title">{reference.title}</span>
                          <span className="assistant-reference-candidate-meta">
                            {referenceMetaText(reference)}
                          </span>
                        </span>
                        <Tag color="default">{referenceTypeLabel(reference.type)}</Tag>
                      </Button>
                    );
                  })}
                </div>
              ))}
            </div>
          ) : null}
          <div className="assistant-composer">
            <TextArea
              aria-label="发送给 AI 助手"
              onChange={(event) => setInputValue(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              onPressEnter={(event) => {
                if (referenceCandidates.length) {
                  event.preventDefault();
                  return;
                }
                if (!event.shiftKey) {
                  event.preventDefault();
                  void sendMessage();
                }
              }}
              placeholder="输入问题"
              rows={3}
              value={inputValue}
            />
            <Button
              aria-label="发送"
              disabled={!canSend}
              icon={<SendOutlined />}
              loading={isSending}
              onClick={() => void sendMessage()}
              type="primary"
            >
              发送
            </Button>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
