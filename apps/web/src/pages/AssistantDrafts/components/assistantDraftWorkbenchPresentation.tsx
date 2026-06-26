import { Typography } from 'antd';

import { StatusTag } from '../../../components/ManagementListPage';

export const actionOptions = [
  { label: '定时作业草案', value: 'create_scheduled_job' },
  { label: '插件连接草案', value: 'create_plugin_connection' },
  { label: '插件动作草案', value: 'create_plugin_action' },
  { label: 'AI Skill 草案', value: 'create_ai_skill' },
  { label: 'AI角色草案', value: 'create_ai_agent' },
  { label: '研发任务草案', value: 'create_rd_task' },
  { label: '分析草案', value: 'create_analysis_draft' },
];

export const statusOptions = [
  { label: '待确认', value: 'pending' },
  { label: '已采纳', value: 'confirmed' },
  { label: '已取消', value: 'cancelled' },
  { label: '已过期', value: 'expired' },
  { label: '失败', value: 'failed' },
];

export const validationOptions = [
  { label: '通过', value: 'passed' },
  { label: '阻塞', value: 'blocked' },
  { label: '警告', value: 'warning' },
  { label: '未知', value: 'unknown' },
];

const actionLabels = new Map(actionOptions.map((item) => [item.value, item.label]));
const statusLabels = new Map(statusOptions.map((item) => [item.value, item.label]));
const validationLabels = new Map(validationOptions.map((item) => [item.value, item.label]));

const statusColors = new Map([
  ['cancelled', 'default'],
  ['confirmed', 'green'],
  ['expired', 'default'],
  ['failed', 'red'],
  ['pending', 'blue'],
]);

const validationColors = new Map([
  ['blocked', 'red'],
  ['passed', 'green'],
  ['unknown', 'default'],
  ['warning', 'orange'],
]);

const riskColors = new Map([
  ['critical', 'red'],
  ['high', 'volcano'],
  ['low', 'green'],
  ['medium', 'gold'],
]);

export function actionLabel(value?: string | null) {
  return actionLabels.get(String(value ?? '')) ?? value ?? '-';
}

export function statusTag(status?: string | null) {
  const value = String(status ?? 'unknown');
  return <StatusTag color={statusColors.get(value) ?? 'default'} label={statusLabels.get(value) ?? value} />;
}

export function validationTag(status?: string | null) {
  const value = String(status ?? 'unknown');
  return <StatusTag color={validationColors.get(value) ?? 'default'} label={validationLabels.get(value) ?? value} />;
}

export function riskTag(risk?: string | null) {
  const value = String(risk ?? '-');
  if (value === '-') {
    return '-';
  }
  return <StatusTag color={riskColors.get(value) ?? 'default'} label={value} />;
}

export function compactText(value?: string | null) {
  const text = value || '-';
  return (
    <Typography.Text ellipsis={{ tooltip: text }} style={{ display: 'block', maxWidth: '100%' }}>
      {text}
    </Typography.Text>
  );
}

export function percent(value?: number) {
  return `${Math.round((value ?? 0) * 1000) / 10}%`;
}

export function assistantDraftEditHref(draftId?: string | null) {
  const normalizedDraftId = String(draftId ?? '').trim();
  if (!normalizedDraftId) {
    return undefined;
  }
  const params = new URLSearchParams();
  params.set('draft_id', normalizedDraftId);
  return `/assistant?${params.toString()}`;
}

export function jsonPreview(value?: Record<string, unknown>) {
  return <pre className="audit-json">{JSON.stringify(value ?? {}, null, 2)}</pre>;
}
