import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  LinkOutlined,
  MoreOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { Button, Dropdown, Space, Tag, Typography, type MenuProps } from 'antd';
import { useMemo, useState } from 'react';

import {
  ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
  ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
  ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
  assistantScopedStorageKey,
  type AssistantDraftResolutionMap,
  type AssistantDraftResolutionRecord,
  type AssistantToolResultItem,
} from '../../../services/aiBrain';
import { AssistantDraftDetailModal } from './AssistantDraftDetailModal';
import { AssistantDraftPreviewBlock } from './AssistantDraftPreviewBlock';
import { AssistantDraftWizardBlock } from './AssistantDraftWizardBlock';
import { draftWizardSteps } from './assistantDraftWizardHelpers';
import { assistantDraftId, draftStatusLabel } from './draftPresentation';

const { Text } = Typography;

type DraftPayloadField = {
  label: string;
  value: string;
};

function itemRecord(item: Record<string, unknown>, field: string) {
  const value = item[field];
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function draftPayloadValue(payload: Record<string, unknown> | undefined, field: string) {
  return field.split('.').reduce<unknown>((current, key) => {
    if (!current || typeof current !== 'object' || Array.isArray(current)) {
      return undefined;
    }
    return (current as Record<string, unknown>)[key];
  }, payload);
}

function draftPayloadText(payload: Record<string, unknown> | undefined, field: string) {
  const value = draftPayloadValue(payload, field);
  if (Array.isArray(value)) {
    return value.length ? value.join('、') : '-';
  }
  if (value && typeof value === 'object') {
    return JSON.stringify(value);
  }
  return value === undefined || value === null || value === '' ? '-' : String(value);
}

function draftPrerequisiteText(
  payload: Record<string, unknown> | undefined,
  dependencyLabels: Map<string, string>,
) {
  const value = draftPayloadValue(payload, 'assistant_prerequisite_draft_ids');
  if (!Array.isArray(value) || !value.length) {
    return '-';
  }
  return value
    .map((item) => {
      const dependencyId = String(item ?? '').trim();
      return dependencyLabels.get(dependencyId) ?? dependencyId;
    })
    .join('、');
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

function assistantDraftDependencyIds(
  draft: Pick<AssistantToolResultItem, 'client_draft_id' | 'draft_id' | 'server_draft_id'>,
) {
  return [draft.draft_id, draft.server_draft_id, draft.client_draft_id]
    .map((value) => String(value ?? '').trim())
    .filter(Boolean);
}

function assistantDraftDependencyLabelMap(drafts: AssistantToolResultItem[]) {
  const items = new Map<string, string>();
  drafts.forEach((draft) => {
    const title = String(draft.title ?? '').trim();
    assistantDraftDependencyIds(draft).forEach((draftId) => {
      items.set(draftId, title || draftId);
    });
  });
  return items;
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
  if (resolution.resource_type === 'ai_skill') {
    return {
      label: '打开 Skill',
      url: `/tasks/ai-capabilities?skill_id=${resolution.resource_id}`,
    };
  }
  if (resolution.resource_type === 'ai_agent') {
    return {
      label: '打开 AI角色',
      url: `/tasks/ai-capabilities?agent_id=${resolution.resource_id}`,
    };
  }
  if (resolution.resource_type === 'plugin_action') {
    return {
      label: '打开插件动作',
      url: `/tasks/plugins?action_id=${resolution.resource_id}`,
    };
  }
  if (resolution.resource_type === 'assistant_analysis') {
    return {
      label: '打开分析结果',
      url: `/assistant?draft_id=${resolution.resource_id}`,
    };
  }
  if (resolution.resource_type === 'ai_task') {
    return {
      label: '打开研发任务',
      url: `/delivery/rd-tasks?task_id=${resolution.resource_id}`,
    };
  }
  return {
    label: '打开插件连接',
    url: `/tasks/plugins?connection_id=${resolution.resource_id}`,
  };
}

function draftRunResourceLink(resolution?: AssistantDraftResolutionRecord) {
  if (
    !resolution
    || resolution.resource_type !== 'scheduled_job'
    || !resolution.scheduled_job_run_id
  ) {
    return undefined;
  }
  return {
    label: '打开本次运行',
    url: `/tasks/scheduled-jobs?job_id=${resolution.resource_id}&run_id=${resolution.scheduled_job_run_id}`,
  };
}

function assistantDraftRunOnceRequested(draft: AssistantToolResultItem) {
  if (draft.run_once_requested === true) {
    return true;
  }
  const payload = draft.payload && typeof draft.payload === 'object' && !Array.isArray(draft.payload)
    ? (draft.payload as Record<string, unknown>)
    : {};
  const configJson = itemRecord(payload, 'config_json');
  const runOnceRequest = itemRecord(configJson, 'assistant_run_once_request');
  return runOnceRequest.requested === true || runOnceRequest.requested === 'true';
}

function storeScheduledJobDraft(draft: AssistantToolResultItem) {
  if (!draft.payload || typeof window === 'undefined') {
    return;
  }
  window.sessionStorage.setItem(
    assistantScopedStorageKey(ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY),
    JSON.stringify({
      draftId: assistantDraftId(draft),
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
    assistantScopedStorageKey(ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY),
    JSON.stringify({
      draftId: assistantDraftId(draft),
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
    assistantScopedStorageKey(ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY),
    JSON.stringify({
      draftId: assistantDraftId(draft),
      payload: draft.payload,
      title: draft.title,
    }),
  );
}

function draftPayloadFields({
  draft,
  draftDependencyLabels,
  resultWriteTargetLabels,
}: {
  draft: AssistantToolResultItem;
  draftDependencyLabels: Map<string, string>;
  resultWriteTargetLabels: Map<string, string>;
}): DraftPayloadField[] {
  const payload = draft.payload;
  const field = (label: string, path: string): DraftPayloadField => ({
    label,
    value: draftPayloadText(payload, path),
  });
  if (draft.action === 'create_plugin_connection') {
    return [
      field('插件', 'plugin_id'),
      field('Endpoint', 'endpoint_url'),
      field('环境', 'environment'),
      field('认证', 'auth_type'),
      field('Params', 'request_config.query'),
      field('Headers', 'request_config.headers'),
    ];
  }
  if (draft.action === 'create_plugin_action') {
    return [
      field('动作类型', 'action_type'),
      field('编码', 'code'),
      field('插件', 'plugin_id'),
      field('连接', 'connection_id'),
      field('请求方法', 'request_config.method'),
      field('请求路径', 'request_config.path'),
      {
        label: '写入目标',
        value: draftPayloadLabel(payload, 'result_mapping.write_target', resultWriteTargetLabels),
      },
    ];
  }
  if (draft.action === 'create_rd_task') {
    return [
      field('需求', 'requirement_id'),
      field('任务类型', 'task_type'),
      field('负责人角色', 'input.owner_role'),
      field('验收标准', 'input.acceptance_criteria'),
    ];
  }
  if (draft.action === 'create_ai_skill') {
    return [
      field('名称', 'name'),
      field('编码', 'code'),
      field('Prompt 模板', 'prompt_template'),
      field('上下文', 'required_context'),
      field('风险等级', 'risk_level'),
      field('状态', 'status'),
    ];
  }
  if (draft.action === 'create_ai_agent') {
    const fields = [
      field('名称', 'name'),
      field('编码', 'code'),
      field('业务大脑', 'brain_app_id'),
      field('AI 模型', 'model_gateway_config_id'),
      field('默认 Skills', 'default_skill_ids'),
      field('系统 Prompt', 'system_prompt'),
    ];
    if (draftPayloadText(payload, 'assistant_prerequisite_draft_ids') !== '-') {
      fields.push({
        label: '前置草案',
        value: draftPrerequisiteText(payload, draftDependencyLabels),
      });
    }
    return fields;
  }
  if (draft.action === 'create_analysis_draft') {
    return [
      field('分析类型', 'analysis_type'),
      field('来源模块', 'source_module'),
      field('摘要指标', 'summary'),
      field('风险/治理项', 'findings'),
    ];
  }

  const fields = [
    field('作业类型', 'job_type'),
    field('调度', 'cron_expression'),
    field('执行模式', 'execution_mode'),
    field('AI 模型', 'model_gateway_config_id'),
    field('AI角色', 'agent_id'),
    field('Skills', 'skill_ids'),
    field('数据连接', 'plugin_connection_id'),
    field('结果动作', 'plugin_action_id'),
  ];
  if (draftPayloadText(payload, 'assistant_prerequisite_draft_ids') !== '-') {
    fields.push({
      label: '前置草案',
      value: draftPrerequisiteText(payload, draftDependencyLabels),
    });
  }
  return fields;
}

export function AssistantActionDraftCards({
  drafts,
  draftMutationId,
  draftResolutionById,
  draftStatusById,
  onCancelDraft,
  onConfirmDraft,
  onRegenerateDraft,
  onViewDraft,
  onUseDraftWizardStepPrompt,
  resultWriteTargetLabels,
}: {
  draftMutationId?: string;
  draftResolutionById: AssistantDraftResolutionMap;
  drafts: AssistantToolResultItem[];
  draftStatusById: Record<string, string>;
  onCancelDraft: (draft: AssistantToolResultItem) => void;
  onConfirmDraft: (draft: AssistantToolResultItem) => void;
  onRegenerateDraft: (draft: AssistantToolResultItem) => void;
  onViewDraft?: (draft: AssistantToolResultItem) => Promise<AssistantToolResultItem>;
  onUseDraftWizardStepPrompt: (prompt: string) => void;
  resultWriteTargetLabels: Map<string, string>;
}) {
  const [detailDraft, setDetailDraft] = useState<AssistantToolResultItem>();
  const draftDependencyLabels = useMemo(
    () => assistantDraftDependencyLabelMap(drafts),
    [drafts],
  );
  const currentDraftStatus = (draft: AssistantToolResultItem) => {
    const draftId = assistantDraftId(draft);
    const resolution = draftId ? draftResolutionById[draftId] : undefined;
    return resolution
      ? 'applied'
      : (draftId ? draftStatusById[draftId] : undefined) ?? draft.status ?? 'pending';
  };
  const openDraftDetail = async (draft: AssistantToolResultItem) => {
    if (!onViewDraft) {
      setDetailDraft(draft);
      return;
    }
    const viewedDraft = await onViewDraft(draft);
    setDetailDraft(viewedDraft);
  };
  if (!drafts.length) {
    return null;
  }
  return (
    <div className="assistant-action-draft-list">
      {drafts.map((draft) => {
        const isAiCapabilityDraft = draft.action === 'create_ai_agent'
          || draft.action === 'create_ai_skill';
        const isAnalysisDraft = draft.action === 'create_analysis_draft';
        const isPluginActionDraft = draft.action === 'create_plugin_action';
        const isPluginConnectionDraft = draft.action === 'create_plugin_connection';
        const isRdTaskDraft = draft.action === 'create_rd_task';
        const draftId = assistantDraftId(draft);
        const resolution = draftId ? draftResolutionById[draftId] : undefined;
        const resourceLink = draftResourceLink(resolution);
        const runResourceLink = draftRunResourceLink(resolution);
        const isRunOnceDraft = assistantDraftRunOnceRequested(draft);
        const currentStatus = currentDraftStatus(draft);
        const statusLabel = draftStatusLabel(currentStatus);
        const isPending = currentStatus === 'pending';
        const isRetryable = isPending || currentStatus === 'unknown';
        const canApplyDraftToForm = currentStatus === 'pending';
        const isPreviewBlocked = draft.preview?.validation?.status === 'blocked';
        const wizardSteps = draftWizardSteps(draft, draftDependencyLabels);
        const writeNotice = isPluginConnectionDraft
          ? '确认前不会写入插件连接'
          : isPluginActionDraft
            ? '确认前不会写入插件动作'
            : isAiCapabilityDraft
              ? '确认前不会写入 AI 能力配置'
              : isRdTaskDraft
                ? '确认前不会创建研发任务'
                : isAnalysisDraft
                  ? '确认前不会写入分析结果'
                  : '确认前不会写入作业定义';
        const payloadFields = draftPayloadFields({
          draft,
          draftDependencyLabels,
          resultWriteTargetLabels,
        });
        const moreActionItems: MenuProps['items'] = [];
        if (canApplyDraftToForm && !resourceLink && isPluginConnectionDraft) {
          moreActionItems.push({
            key: 'apply-plugin-connection',
            label: (
              <a
                href="/tasks/plugins"
                onClick={() => storePluginConnectionDraft(draft)}
                onMouseDown={() => storePluginConnectionDraft(draft)}
              >
                应用到插件连接表单
              </a>
            ),
          });
        }
        if (canApplyDraftToForm && !resourceLink && isPluginActionDraft) {
          moreActionItems.push({
            key: 'apply-plugin-action',
            label: (
              <a
                href="/tasks/plugins"
                onClick={() => storePluginActionDraft(draft)}
                onMouseDown={() => storePluginActionDraft(draft)}
              >
                应用到插件动作表单
              </a>
            ),
          });
        }
        if (
          canApplyDraftToForm
          && !resourceLink
          && !isAiCapabilityDraft
          && !isPluginConnectionDraft
          && !isPluginActionDraft
          && !isRdTaskDraft
          && !isAnalysisDraft
        ) {
          moreActionItems.push({
            key: 'apply-scheduled-job',
            label: (
              <a
                href="/tasks/scheduled-jobs"
                onClick={() => storeScheduledJobDraft(draft)}
                onMouseDown={() => storeScheduledJobDraft(draft)}
              >
                应用到定时作业表单
              </a>
            ),
          });
        }
        if (draftId) {
          moreActionItems.push({
            key: 'open-draft-link',
            label: <a href={`/assistant?draft_id=${draftId}`}>打开草案链接</a>,
          });
        }
        moreActionItems.push({
          key: 'regenerate',
          label: '重新生成',
          icon: <ReloadOutlined />,
          onClick: () => onRegenerateDraft(draft),
        });
        return (
          <div className="assistant-action-draft-card" key={draftId}>
            <div className="assistant-action-draft-header">
              <Space size={8} wrap>
                <FileTextOutlined />
                <Text strong>{draft.title ?? '配置草案'}</Text>
                {draft.risk_level ? <Tag color="orange">风险：{draft.risk_level}</Tag> : null}
                {draft.requires_confirmation ? <Tag color={statusLabel.color}>{statusLabel.text}</Tag> : null}
                {isRunOnceDraft ? <Tag color="geekblue">确认后执行一次</Tag> : null}
                {isRunOnceDraft && isPending ? <Tag color="gold">尚未执行</Tag> : null}
              </Space>
              <Text type="secondary">
                {isRunOnceDraft ? `${writeNotice}；确认后会立即执行一次` : writeNotice}
              </Text>
            </div>
            <div className="assistant-action-draft-grid">
              {payloadFields.map((field) => (
                <span key={field.label}>
                  <Text type="secondary">{field.label}</Text>
                  <Text>{field.value}</Text>
                </span>
              ))}
            </div>
            <AssistantDraftWizardBlock
              draftTitle={draft.title}
              steps={wizardSteps}
              onUsePrerequisitePrompt={onUseDraftWizardStepPrompt}
            />
            <AssistantDraftPreviewBlock
              draftTitle={draft.title}
              preview={draft.preview}
              onUseRepairAction={onUseDraftWizardStepPrompt}
            />
            <Space size={8} wrap>
              {draftId && isRetryable ? (
                <>
                  <Button
                    disabled={isPreviewBlocked}
                    icon={<CheckCircleOutlined />}
                    loading={draftMutationId === draftId}
                    size="small"
                    type="primary"
                    onClick={() => onConfirmDraft(draft)}
                  >
                    {isRunOnceDraft ? '确认并执行一次' : '确认创建'}
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
              {runResourceLink ? (
                <Button
                  aria-label={runResourceLink.label}
                  href={runResourceLink.url}
                  icon={<LinkOutlined />}
                  size="small"
                >
                  {runResourceLink.label}
                </Button>
              ) : null}
              <Button size="small" onClick={() => { void openDraftDetail(draft); }}>
                查看详情
              </Button>
              <Dropdown menu={{ items: moreActionItems }} placement="bottomRight" trigger={['click']}>
                <Button aria-label="更多草案操作" icon={<MoreOutlined />} size="small">
                  更多
                </Button>
              </Dropdown>
            </Space>
          </div>
        );
      })}
      <AssistantDraftDetailModal
        draft={detailDraft}
        status={detailDraft ? currentDraftStatus(detailDraft) : undefined}
        onClose={() => setDetailDraft(undefined)}
      />
    </div>
  );
}
