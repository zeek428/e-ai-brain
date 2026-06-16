import {
  ApiOutlined,
  CopyOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  FileTextOutlined,
  KeyOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Alert, Button, Checkbox, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, Switch, Typography, message } from 'antd';
import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';

import {
  ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
  ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
  createAiExecutorRunner,
  copyPlugin,
  createPlugin,
  createPluginAction,
  createPluginConnection,
  cancelAiExecutorTask,
  deletePlugin,
  deletePluginAction,
  deletePluginConnection,
  deleteAiExecutorRunner,
  downloadAiExecutorRunnerInstallPackage,
  fetchAiExecutorTaskLogs,
  fetchAiExecutorRunners,
  fetchPluginActions,
  fetchPluginActionTemplates,
  fetchPluginConnections,
  fetchPluginMarketplace,
  fetchPluginSystemVariables,
  fetchPlugins,
  fetchResultWriteTargets,
  fetchScheduledJobs,
  invokePluginAction,
  rememberAssistantDraftResolution,
  resolveAssistantDraftResourceId,
  rotateAiExecutorRunnerToken,
  testAiExecutorRunner,
  testPluginConnection,
  trialPluginAction,
  updateAiExecutorRunner,
  updatePlugin,
  updatePluginAction,
  updatePluginConnection,
  type AssistantPluginActionDraft,
  type AssistantPluginConnectionDraft,
  type AiExecutorTaskLogRecord,
  type AiExecutorTaskRecord,
  type AiExecutorRunnerRecord,
  type AiExecutorRunnerTestResult,
  type PluginActionTrialResult,
  type PluginActionRecord,
  type PluginActionTemplateRecord,
  type PluginConnectionRecord,
  type PluginConnectionRepairSuggestion,
  type PluginConnectionSchemaFieldRecord,
  type PluginConnectionSchemaRecord,
  type PluginConnectionTestHistoryRecord,
  type PluginConnectionTestResult,
  type PluginMarketplaceItem,
  type PluginRecord,
  type PluginSystemVariableRecord,
  type ResultWriteTargetRecord,
  type ScheduledJobRecord,
} from '../../services/aiBrain';

type PluginFormValues = {
  category: string;
  code: string;
  description?: string;
  name: string;
  protocol: string;
  risk_level: string;
  status: string;
};

type ConnectionFormValues = {
  auth_config?: string;
  auth_type: string;
  connection_header_rows?: RequestParameterRow[];
  connection_param_rows?: RequestParameterRow[];
  endpoint_url: string;
  environment: string;
  header_name?: string;
  max_retries: number;
  name: string;
  password_ref?: string;
  plugin_id: string;
  request_config?: string;
  schema_values?: Record<string, unknown>;
  secret_ref?: string;
  status: string;
  timeout_seconds: number;
  token_ref?: string;
  username_ref?: string;
};

type ActionFormValues = {
  action_type: string;
  branch_path?: string;
  code: string;
  commit_sha_path?: string;
  connection_id?: string;
  delivery_id_path?: string;
  delivery_status_path?: string;
  description?: string;
  findings_path?: string;
  header_rows?: RequestParameterRow[];
  insights_path?: string;
  max_rows?: number;
  method?: string;
  name: string;
  param_rows?: RequestParameterRow[];
  path?: string;
  plugin_id: string;
  request_config?: string;
  requires_human_review: boolean;
  records_imported_path?: string;
  recipients_path?: string;
  repository_id_path?: string;
  result_mapping?: string;
  risk_level_path?: string;
  rows_path?: string;
  returned_fields?: string;
  scenario?: string;
  status: string;
  subject_path?: string;
  summary_path?: string;
  table_name?: string;
  time_field?: string;
  write_target?: string;
};

type AiExecutorRunnerFormValues = {
  claude_command?: string;
  codex_command?: string;
  endpoint_url: string;
  executor_types: string[];
  hermes_command?: string;
  heartbeat_timeout_seconds: number;
  install_mode?: string;
  max_concurrent_tasks: number;
  metadata?: string;
  name: string;
  openclaw_command?: string;
  package_arch?: string;
  protocol: string;
  runner_token?: string;
  status: string;
  target_os?: string;
  workspace_roots?: string;
};

type RequestParameterRow = {
  description?: string;
  enabled?: boolean;
  name?: string;
  type?: 'boolean' | 'number' | 'string';
  value?: string;
};

type DeleteUsageGroup = {
  items: string[];
  label: string;
};

const MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO = 'maxcompute_weekly_feedback';
const MAXCOMPUTE_DEFAULT_FIELDS =
  'feedback_id,user_id,product_id,module_code,feedback_type,content,sentiment,created_at';
const DEFAULT_RESULT_WRITE_TARGET = 'scheduled_job_result';
const SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID = 'ai_executor_runner_system_default';
const SYSTEM_DEFAULT_AI_EXECUTOR_TYPE = 'model_gateway';

const requestMethodOptions = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((value) => ({
  label: value,
  value,
}));

const requestParameterTypeOptions = [
  { label: 'string', value: 'string' },
  { label: 'number', value: 'number' },
  { label: 'boolean', value: 'boolean' },
];

const aiExecutorTypeOptions = [
  { label: 'Codex', value: 'codex' },
  { label: 'Claude Code', value: 'claude' },
  { label: 'Hermes', value: 'hermes' },
  { label: 'OpenClaw', value: 'openclaw' },
];

const aiExecutorTypeLabelByValue = new Map([
  [SYSTEM_DEFAULT_AI_EXECUTOR_TYPE, '系统默认模型'],
  ...aiExecutorTypeOptions.map((option) => [option.value, option.label] as const),
]);

const aiExecutorCommandFieldByType = new Map([
  ['codex', 'codex_command'],
  ['claude', 'claude_command'],
  ['hermes', 'hermes_command'],
  ['openclaw', 'openclaw_command'],
] as const);

const aiExecutorRunnerTargetOsOptions = [
  { label: 'Linux', value: 'linux' },
  { label: 'macOS', value: 'macos' },
  { label: 'Windows', value: 'windows' },
  { label: 'Docker', value: 'docker' },
  { label: '通用手动安装', value: 'manual' },
];

const aiExecutorRunnerArchOptions = [
  { label: 'amd64', value: 'amd64' },
  { label: 'arm64', value: 'arm64' },
  { label: 'universal', value: 'universal' },
];

const defaultInstallModeByTargetOs = new Map([
  ['docker', 'docker'],
  ['linux', 'systemd'],
  ['macos', 'launchd'],
  ['manual', 'manual'],
  ['windows', 'service'],
]);

const installModeOptionsByTargetOs = new Map([
  ['docker', [{ label: 'Docker Compose', value: 'docker' }]],
  ['linux', [
    { label: 'systemd 服务', value: 'systemd' },
    { label: 'Shell 脚本', value: 'shell' },
  ]],
  ['macos', [
    { label: 'launchd 服务', value: 'launchd' },
    { label: 'Shell 脚本', value: 'shell' },
  ]],
  ['manual', [{ label: '手动启动脚本', value: 'manual' }]],
  ['windows', [
    { label: 'Windows Service', value: 'service' },
    { label: 'PowerShell 脚本', value: 'powershell' },
  ]],
]);

const aiExecutorRunnerProtocolOptions = [
  { label: 'Runner Polling', value: 'runner_polling' },
  { label: 'Runner WebSocket', value: 'runner_websocket' },
  { label: 'MCP HTTP', value: 'mcp_http' },
  { label: 'MCP Stdio', value: 'mcp_stdio' },
];

const systemVariableOptions = [
  { description: 'YYYYMMDD 格式，适合分区字段', label: '当前日期', value: '{{current_date}}' },
  { description: '当前日期前 7 天，适合近 7 天起始分区', label: '当前日期 - 7 天', value: '{{current_date-7}}' },
  { description: 'YYYY-MM-DD 格式，适合 API 日期参数', label: '当前日期 ISO', value: '{{date_iso}}' },
  { description: 'ISO 日期前 7 天', label: '当前日期 ISO - 7 天', value: '{{date_iso-7}}' },
  { description: '当前时间，带时区偏移', label: '当前时间', value: '{{now}}' },
  { description: '今天 00:00:00', label: '今天开始', value: '{{today.start}}' },
  { description: '今天 00:00:00 前 7 天', label: '今天开始 - 7 天', value: '{{today.start-7}}' },
  { description: '上一完整自然周周一 00:00:00', label: '上一完整周开始', value: '{{last_full_week.start}}' },
  { description: '本周一 00:00:00', label: '上一完整周结束', value: '{{last_full_week.end}}' },
];

const systemVariableDescriptionByExpression = new Map(
  systemVariableOptions.map((option) => [option.value, option.description]),
);

const pluginCategoryOptions = [
  { label: '通用集成', value: 'general' },
  { label: '数据仓库 / BI', value: 'data_warehouse' },
  { label: 'DevOps / 代码平台', value: 'devops' },
  { label: '需求 / 缺陷系统', value: 'issue_tracking' },
  { label: '日志 / 监控', value: 'observability' },
  { label: '知识库 / 文档', value: 'knowledge_base' },
  { label: '协同 / 通知', value: 'collaboration' },
  { label: 'AI / 模型服务', value: 'ai_service' },
  { label: '业务系统', value: 'business_system' },
];

const pluginCategoryLabelByValue = new Map(
  pluginCategoryOptions.map((option) => [option.value, option.label]),
);

const connectionEnvironmentOptions = [
  { label: '默认', value: 'default' },
  { label: '开发', value: 'dev' },
  { label: '测试', value: 'test' },
  { label: '预发 / Staging', value: 'staging' },
  { label: '生产', value: 'prod' },
  { label: '沙箱', value: 'sandbox' },
];

const connectionEnvironmentLabelByValue = new Map(
  connectionEnvironmentOptions.map((option) => [option.value, option.label]),
);

const OFFICIAL_PLUGIN_LABEL = '官方标准';
const pluginVersionStatusLabelByValue = new Map([
  ['custom', '自定义'],
  ['latest', '最新'],
  ['upgrade_available', '可升级'],
]);

const genericIntegrationChainSteps = [
  { color: 'blue', label: '插件', text: '定义三方系统能力与协议' },
  { color: 'cyan', label: '连接', text: '维护环境、Endpoint、认证和公共参数' },
  { color: 'purple', label: '动作', text: '定义请求、变量和结果映射' },
  { color: 'green', label: '定时作业', text: '编排取数、AI 处理和结果写入' },
];

function pluginVersionStatusTag(record: {
  template_version?: string;
  upgrade_available?: boolean;
  version_status?: string;
}) {
  const version = record.template_version ?? '-';
  const status = record.upgrade_available ? 'upgrade_available' : record.version_status ?? 'custom';
  const label = pluginVersionStatusLabelByValue.get(status) ?? status;
  const color = status === 'upgrade_available' ? 'orange' : status === 'latest' ? 'green' : 'default';
  return <Tag color={color}>{`${version} ${label}`}</Tag>;
}

function stableJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function linesToArray(value?: string): string[] {
  return (value ?? '')
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
}

function arrayToLines(value?: string[]): string {
  return (value ?? []).join('\n');
}

function aiExecutorTypeLabel(value: unknown): string {
  const key = String(value ?? '');
  return aiExecutorTypeLabelByValue.get(key) ?? key;
}

function runnerExecutorCommandsFromValues(values: AiExecutorRunnerFormValues): Record<string, string> {
  return Object.fromEntries(
    Array.from(aiExecutorCommandFieldByType.entries())
      .map(([executorType, field]) => [executorType, stringValue(values[field]).trim()] as const)
      .filter(([, command]) => Boolean(command)),
  );
}

function runnerExecutorCommandsFromMetadata(metadata: Record<string, unknown> | undefined): Record<string, string> {
  const commands = isPlainRecord(metadata?.executor_commands) ? metadata.executor_commands : {};
  return Object.fromEntries(
    Array.from(aiExecutorCommandFieldByType.keys())
      .map((executorType) => [executorType, stringValue(commands[executorType])] as const)
      .filter(([, command]) => Boolean(command)),
  );
}

function runnerInstallModeOptions(targetOs: unknown) {
  const key = stringValue(targetOs, 'linux');
  return installModeOptionsByTargetOs.get(key) ?? installModeOptionsByTargetOs.get('linux') ?? [];
}

function runnerDefaultInstallMode(targetOs: unknown) {
  const key = stringValue(targetOs, 'linux');
  return defaultInstallModeByTargetOs.get(key) ?? 'systemd';
}

function runnerPackageOptionsFromMetadata(metadata: Record<string, unknown> | undefined) {
  const targetOs = stringValue(metadata?.target_os, 'linux');
  return {
    arch: stringValue(metadata?.package_arch, targetOs === 'manual' ? 'universal' : 'amd64'),
    install_mode: stringValue(metadata?.install_mode, runnerDefaultInstallMode(targetOs)),
    target_os: targetOs,
  };
}

function runnerPayload(values: AiExecutorRunnerFormValues): Partial<AiExecutorRunnerRecord> {
  const metadata = values.metadata ? parseJsonObject(values.metadata, 'Runner Metadata') : {};
  const executorCommands = runnerExecutorCommandsFromValues(values);
  delete metadata.executor_commands;
  if (Object.keys(executorCommands).length > 0) {
    metadata.executor_commands = executorCommands;
  }
  delete metadata.install_mode;
  if (values.install_mode) {
    metadata.install_mode = values.install_mode;
  }
  delete metadata.package_arch;
  if (values.package_arch) {
    metadata.package_arch = values.package_arch;
  }
  delete metadata.target_os;
  if (values.target_os) {
    metadata.target_os = values.target_os;
  }
  return {
    endpoint_url: values.endpoint_url,
    executor_types: values.executor_types,
    heartbeat_timeout_seconds: values.heartbeat_timeout_seconds,
    max_concurrent_tasks: values.max_concurrent_tasks,
    metadata,
    name: values.name,
    protocol: values.protocol,
    ...(values.runner_token ? { runner_token: values.runner_token } : {}),
    status: values.status,
    workspace_roots: linesToArray(values.workspace_roots),
  };
}

function usageItemName(item: { code?: string; id?: string; name?: string | null }) {
  return item.name || item.code || item.id || '-';
}

function hasDeleteUsage(groups: DeleteUsageGroup[]) {
  return groups.some((group) => group.items.length > 0);
}

function deleteUsageContent(groups: DeleteUsageGroup[]) {
  return (
    <Space orientation="vertical" size={8}>
      <Typography.Text>当前对象正在被使用，不能删除。请先解除下面的引用，或将其停用。</Typography.Text>
      {groups.filter((group) => group.items.length > 0).map((group) => (
        <div key={group.label}>
          <Typography.Text strong>{group.label}：</Typography.Text>
          <Typography.Text>{group.items.slice(0, 5).join('、')}</Typography.Text>
          {group.items.length > 5 ? <Typography.Text type="secondary"> 等 {group.items.length} 个</Typography.Text> : null}
        </div>
      ))}
    </Space>
  );
}

function buildMaxComputeRequestConfig(values: Partial<ActionFormValues>): Record<string, unknown> {
  const table = values.table_name?.trim() || 'ods_user_feedback';
  const timeField = values.time_field?.trim() || 'created_at';
  const fields = (values.returned_fields || MAXCOMPUTE_DEFAULT_FIELDS)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
  const limit = values.max_rows && values.max_rows > 0 ? values.max_rows : 1000;
  return {
    fields,
    limit,
    sql_template: `SELECT ${fields.join(', ')} FROM ${table} WHERE ${timeField} >= '\${week_start}' AND ${timeField} < '\${week_end}' LIMIT ${limit}`,
    table,
    time_field: timeField,
    tool_name: 'maxcompute.execute_sql',
  };
}

function parseParameterValue(row: RequestParameterRow): unknown {
  const value = row.value ?? '';
  if (row.type === 'number') {
    const numericValue = Number(value);
    return Number.isFinite(numericValue) ? numericValue : value;
  }
  if (row.type === 'boolean') {
    return value === 'true' || value === '1' || value === '是';
  }
  return value;
}

function rowsToRecord(rows: RequestParameterRow[] | undefined): Record<string, unknown> {
  return (rows ?? []).reduce<Record<string, unknown>>((result, row) => {
    const name = row.name?.trim();
    if (row.enabled === false || !name) {
      return result;
    }
    result[name] = parseParameterValue(row);
    return result;
  }, {});
}

function recordToRows(record: unknown, excludeKeys: Set<string> = new Set()): RequestParameterRow[] {
  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    return [];
  }
  return Object.entries(record as Record<string, unknown>)
    .filter(([name]) => !excludeKeys.has(name))
    .map(([name, value]) => ({
      enabled: true,
      name,
      type: typeof value === 'number' ? 'number' : typeof value === 'boolean' ? 'boolean' : 'string',
      value: typeof value === 'string' ? value : String(value),
    }));
}

function configSection(config: Record<string, unknown> | undefined, key: string): unknown {
  const section = config?.[key];
  return section && typeof section === 'object' && !Array.isArray(section) ? section : undefined;
}

function schemaFields(schema?: PluginConnectionSchemaRecord): PluginConnectionSchemaFieldRecord[] {
  return (schema?.sections ?? []).flatMap((section) => section.fields ?? []);
}

function schemaManagedRequestKeys(
  schema: PluginConnectionSchemaRecord | undefined,
  section: 'headers' | 'query',
): Set<string> {
  const keys = new Set<string>();
  schemaFields(schema).forEach((field) => {
    if (section === 'query') {
      (field.managed_query_keys ?? []).forEach((key) => keys.add(key));
    }
    const key =
      (() => {
        const segments = pathSegments(field.path);
        return segments[0] === 'request_config' && segments[1] === section ? segments[2] : undefined;
      })();
    if (key) {
      keys.add(key);
    }
  });
  return keys;
}

function pathSegments(path?: string): string[] {
  return path ? path.split('.').map((segment) => segment.trim()).filter(Boolean) : [];
}

function valueAtPath(source: Record<string, unknown>, path?: string): unknown {
  return pathSegments(path).reduce<unknown>((current, segment) => {
    if (!current || typeof current !== 'object' || Array.isArray(current)) {
      return undefined;
    }
    return (current as Record<string, unknown>)[segment];
  }, source);
}

function setValueAtPath(target: Record<string, unknown>, path: string | undefined, value: unknown) {
  const segments = pathSegments(path);
  if (segments.length === 0) {
    return;
  }
  let cursor = target;
  segments.slice(0, -1).forEach((segment) => {
    const next = cursor[segment];
    if (!next || typeof next !== 'object' || Array.isArray(next)) {
      cursor[segment] = {};
    }
    cursor = cursor[segment] as Record<string, unknown>;
  });
  cursor[segments[segments.length - 1]] = value;
}

function parseGitRepositoryAddress(value: unknown): { owner: string; repo: string } | undefined {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }
  const sshMatch = trimmed.match(/^[^@\s]+@[^:\s]+:(.+)$/);
  let path = sshMatch?.[1] ?? trimmed;
  if (!sshMatch) {
    const firstSegment = trimmed.split('/')[0] ?? '';
    const looksLikeUrl = trimmed.includes('://') || firstSegment.includes('.');
    try {
      if (looksLikeUrl) {
        const url = new URL(trimmed.includes('://') ? trimmed : `https://${trimmed}`);
        path = url.pathname;
      }
    } catch {
      path = trimmed;
    }
  }
  const segments = path
    .replace(/^\/+/, '')
    .replace(/\/+$/, '')
    .split('/')
    .filter(Boolean);
  const repoSegments = segments[0] === 'repos' ? segments.slice(1) : segments;
  const owner = repoSegments[0]?.trim();
  const repo = repoSegments[1]?.replace(/\.git$/i, '').trim();
  return owner && repo ? { owner, repo } : undefined;
}

function safeDecodeURIComponent(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function parseGitLabProjectAddress(
  value: unknown,
): { endpointUrl?: string; projectId: string; projectPath: string } | undefined {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }
  const sshMatch = trimmed.match(/^[^@\s]+@([^:\s]+):(.+)$/);
  let endpointUrl: string | undefined;
  let path = sshMatch?.[2] ?? trimmed;
  if (sshMatch) {
    endpointUrl = `https://${sshMatch[1]}`;
  } else {
    const firstSegment = trimmed.split('/')[0] ?? '';
    const looksLikeUrl =
      trimmed.includes('://')
      || firstSegment.includes('.')
      || firstSegment.includes(':')
      || firstSegment === 'localhost';
    try {
      if (looksLikeUrl) {
        const url = new URL(trimmed.includes('://') ? trimmed : `http://${trimmed}`);
        endpointUrl = `${url.protocol}//${url.host}`;
        path = url.pathname;
      }
    } catch {
      path = trimmed;
    }
  }
  const normalizedPath = path.split('/-/', 1)[0] ?? path;
  let segments = normalizedPath
    .replace(/^\/+/, '')
    .replace(/\/+$/, '')
    .split('/')
    .filter(Boolean);
  if (segments.length >= 4 && segments[0] === 'api' && segments[2] === 'projects') {
    segments = [safeDecodeURIComponent(segments[3])];
  }
  const projectPath = safeDecodeURIComponent(segments.join('/')).replace(/\.git$/i, '').replace(/^\/+|\/+$/g, '');
  if (!projectPath || !projectPath.includes('/')) {
    return undefined;
  }
  return {
    endpointUrl,
    projectId: encodeURIComponent(projectPath),
    projectPath,
  };
}

function buildGitRepositoryAddress(payload: Record<string, unknown>): string | undefined {
  const requestConfig = isPlainRecord(payload.request_config) ? payload.request_config : {};
  const query = isPlainRecord(requestConfig.query) ? requestConfig.query : {};
  const explicitUrl = stringValue(query.repository_url).trim();
  if (explicitUrl) {
    return explicitUrl;
  }
  const owner = stringValue(query.owner).trim();
  const repo = stringValue(query.repo).trim();
  if (!owner || !repo) {
    return undefined;
  }
  const endpointUrl = stringValue(payload.endpoint_url);
  try {
    const endpoint = endpointUrl ? new URL(endpointUrl) : undefined;
    if (endpoint?.hostname === 'api.github.com') {
      return `https://github.com/${owner}/${repo}.git`;
    }
  } catch {
    // fall back to the portable owner/repo shorthand
  }
  return `${owner}/${repo}`;
}

function buildGitLabProjectAddress(payload: Record<string, unknown>): string | undefined {
  const requestConfig = isPlainRecord(payload.request_config) ? payload.request_config : {};
  const query = isPlainRecord(requestConfig.query) ? requestConfig.query : {};
  const explicitUrl = stringValue(query.gitlab_project_url).trim()
    || stringValue(query.repository_url).trim();
  if (explicitUrl) {
    return explicitUrl;
  }
  const projectPath = stringValue(query.project_path).trim();
  if (projectPath) {
    const endpointUrl = stringValue(payload.endpoint_url).replace(/\/+$/, '');
    return endpointUrl ? `${endpointUrl}/${projectPath}.git` : projectPath;
  }
  const projectId = stringValue(query.project_id).trim();
  if (!projectId) {
    return undefined;
  }
  const decodedProjectId = safeDecodeURIComponent(projectId);
  const endpointUrl = stringValue(payload.endpoint_url).replace(/\/+$/, '');
  return endpointUrl ? `${endpointUrl}/${decodedProjectId}.git` : decodedProjectId;
}

function schemaValuesFromPayload(
  payload: Record<string, unknown>,
  schema?: PluginConnectionSchemaRecord,
): Record<string, unknown> {
  return Object.fromEntries(
    schemaFields(schema)
      .map((field) => [
        field.key,
        field.type === 'github_repository_url'
          ? buildGitRepositoryAddress(payload)
          : field.type === 'gitlab_project_url'
            ? buildGitLabProjectAddress(payload)
          : valueAtPath(payload, field.path),
      ])
      .filter(([, value]) => value !== undefined),
  );
}

function applySchemaValuesToRequestConfig(
  requestConfig: Record<string, unknown>,
  schema: PluginConnectionSchemaRecord | undefined,
  schemaValues: Record<string, unknown> | undefined,
) {
  if (!schemaValues) {
    return requestConfig;
  }
  const root: Record<string, unknown> = { request_config: { ...requestConfig } };
  schemaFields(schema).forEach((field) => {
    const value = schemaValues[field.key];
    if (value === undefined) {
      return;
    }
    if (field.type === 'github_repository_url') {
      const parsed = parseGitRepositoryAddress(value);
      setValueAtPath(root, 'request_config.query.owner', parsed?.owner ?? '');
      setValueAtPath(root, 'request_config.query.repo', parsed?.repo ?? '');
      return;
    }
    if (field.type === 'gitlab_project_url') {
      const parsed = parseGitLabProjectAddress(value);
      setValueAtPath(root, 'request_config.query.api_version', 'v4');
      setValueAtPath(root, 'request_config.query.group_id', parsed?.projectPath.split('/', 1)[0] ?? '');
      setValueAtPath(root, 'request_config.query.project_id', parsed?.projectId ?? '');
      setValueAtPath(root, 'request_config.query.project_path', parsed?.projectPath ?? '');
      return;
    }
    if (!field.path?.startsWith('request_config.')) {
      return;
    }
    setValueAtPath(root, field.path, value);
  });
  return isPlainRecord(root.request_config) ? root.request_config : requestConfig;
}

function buildVisualRequestConfig(values: Partial<ActionFormValues>): Record<string, unknown> {
  const config: Record<string, unknown> = {};
  const method = values.method || 'GET';
  const path = values.path?.trim();
  const query = rowsToRecord(values.param_rows);
  const headers = rowsToRecord(values.header_rows);
  config.method = method;
  if (path) {
    config.path = path;
  }
  if (Object.keys(query).length > 0) {
    config.query = query;
  }
  if (Object.keys(headers).length > 0) {
    config.headers = headers;
  }
  return config;
}

function buildActionRequestPreview(
  values: Partial<ActionFormValues> | undefined,
  connection?: PluginConnectionRecord,
): Record<string, unknown> {
  const formValues = values ?? {};
  const config =
    formValues.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO
      ? buildMaxComputeRequestConfig(formValues)
      : buildVisualRequestConfig(formValues);
  const method = String(config.method ?? 'POST').toUpperCase();
  const connectionRequestConfig = connection?.request_config ?? {};
  const connectionQuery =
    connectionRequestConfig.query && typeof connectionRequestConfig.query === 'object'
      ? connectionRequestConfig.query
      : {};
  const actionQuery = config.query && typeof config.query === 'object' ? config.query : {};
  const query = { ...(connectionQuery as Record<string, unknown>), ...(actionQuery as Record<string, unknown>) };
  const connectionHeaders =
    connectionRequestConfig.headers && typeof connectionRequestConfig.headers === 'object'
      ? connectionRequestConfig.headers
      : {};
  const actionHeaders = config.headers && typeof config.headers === 'object' ? config.headers : {};
  const headers = { ...(connectionHeaders as Record<string, unknown>), ...(actionHeaders as Record<string, unknown>) };
  const path = String(config.path ?? '');
  const baseUrl = connection?.endpoint_url?.replace(/\/$/, '') ?? '';
  const queryString = new URLSearchParams(query as Record<string, string>).toString();
  return {
    endpoint: connection?.endpoint_url ?? '-',
    headers,
    method,
    path: path || (config.tool_name ? '(MCP tools/call)' : ''),
    query,
    tool_name: config.tool_name,
    url: path
      ? `${baseUrl}/${path.replace(/^\//, '')}${queryString ? `?${queryString}` : ''}`
      : `${baseUrl}${queryString ? `?${queryString}` : ''}`,
  };
}

function buildConnectionAuthConfig(values: Partial<ConnectionFormValues>): Record<string, unknown> {
  if (values.auth_type === 'bearer') {
    return values.token_ref?.trim() ? { token_ref: values.token_ref.trim() } : {};
  }
  if (values.auth_type === 'api_key_header') {
    return {
      header_name: values.header_name?.trim() || 'X-API-Key',
      ...(values.secret_ref?.trim() ? { secret_ref: values.secret_ref.trim() } : {}),
    };
  }
  if (values.auth_type === 'basic') {
    return {
      ...(values.username_ref?.trim() ? { username_ref: values.username_ref.trim() } : {}),
      ...(values.password_ref?.trim() ? { password_ref: values.password_ref.trim() } : {}),
    };
  }
  return {};
}

function buildConnectionRequestConfig(
  values: Partial<ConnectionFormValues>,
  schema?: PluginConnectionSchemaRecord,
): Record<string, unknown> {
  const config: Record<string, unknown> = {};
  const query = rowsToRecord(values.connection_param_rows);
  const headers = rowsToRecord(values.connection_header_rows);
  if (Object.keys(query).length > 0) {
    config.query = query;
  }
  if (Object.keys(headers).length > 0) {
    config.headers = headers;
  }
  return applySchemaValuesToRequestConfig(config, schema, values.schema_values);
}

function endpointUrlFromSchemaValues(
  values: Partial<ConnectionFormValues>,
  schema?: PluginConnectionSchemaRecord,
): string | undefined {
  for (const field of schemaFields(schema)) {
    if (field.type !== 'gitlab_project_url') {
      continue;
    }
    const parsed = parseGitLabProjectAddress(values.schema_values?.[field.key]);
    if (parsed?.endpointUrl) {
      return parsed.endpointUrl;
    }
  }
  return values.endpoint_url;
}

function buildConnectionPayload(
  values: ConnectionFormValues,
  authConfig: Record<string, unknown>,
  requestConfig: Record<string, unknown>,
  schema?: PluginConnectionSchemaRecord,
): Partial<PluginConnectionRecord> {
  return {
    auth_config: authConfig,
    auth_type: values.auth_type,
    endpoint_url: endpointUrlFromSchemaValues(values, schema) ?? values.endpoint_url,
    environment: values.environment,
    max_retries: values.max_retries,
    name: values.name,
    plugin_id: values.plugin_id,
    request_config: requestConfig,
    status: values.status,
    timeout_seconds: values.timeout_seconds,
  };
}

function buildActionPayload(
  values: ActionFormValues,
  requestConfig: Record<string, unknown>,
  resultMapping: Record<string, unknown>,
): Partial<PluginActionRecord> {
  return {
    action_type: values.action_type,
    code: values.code,
    connection_id: values.connection_id,
    description: values.description,
    name: values.name,
    plugin_id: values.plugin_id,
    request_config: requestConfig,
    requires_human_review: values.requires_human_review,
    result_mapping: resultMapping,
    status: values.status,
  };
}

function parseJsonObject(value: string | undefined, field: string): Record<string, unknown> {
  if (!value?.trim()) {
    return {};
  }
  try {
    const parsed = JSON.parse(value) as unknown;
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    // fall through to a consistent validation message
  }
  throw new Error(`${field} 必须是 JSON 对象`);
}

function isFormValidationError(error: unknown): error is { errorFields: Array<{ name?: Array<string | number> }> } {
  return (
    Boolean(error)
    && typeof error === 'object'
    && Array.isArray((error as { errorFields?: unknown }).errorFields)
  );
}

function compactJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

function mergeWriteTarget(
  resultMapping: Record<string, unknown>,
  writeTarget?: string,
): Record<string, unknown> {
  const nextMapping = { ...resultMapping };
  if (writeTarget) {
    nextMapping.write_target = writeTarget;
  }
  return nextMapping;
}

function resultWriteTargetRecordByCode(
  writeTargets: ResultWriteTargetRecord[] = [],
  writeTarget?: string,
) {
  return writeTargets.find((target) => target.code === (writeTarget || DEFAULT_RESULT_WRITE_TARGET));
}

function defaultResultMappingForWriteTarget(
  writeTarget?: string,
  writeTargets: ResultWriteTargetRecord[] = [],
): Record<string, unknown> {
  const normalizedWriteTarget = writeTarget || DEFAULT_RESULT_WRITE_TARGET;
  const registryDefault = resultWriteTargetRecordByCode(writeTargets, writeTarget)?.default_result_mapping;
  if (registryDefault) {
    return { ...registryDefault };
  }
  return { write_target: normalizedWriteTarget };
}

function resultWriteTargetLabel(
  writeTarget?: string,
  writeTargets: ResultWriteTargetRecord[] = [],
): string {
  const target = resultWriteTargetRecordByCode(writeTargets, writeTarget);
  if (target) {
    return target.form_label || target.label;
  }
  return writeTarget || DEFAULT_RESULT_WRITE_TARGET;
}

function writeTargetFromResultMapping(resultMapping: Record<string, unknown>): string {
  return typeof resultMapping.write_target === 'string'
    ? resultMapping.write_target
    : DEFAULT_RESULT_WRITE_TARGET;
}

function stringMappingValue(resultMapping: Record<string, unknown>, key: string): string | undefined {
  const value = resultMapping[key];
  return typeof value === 'string' ? value : undefined;
}

function resultMappingVisualFields(
  resultMapping: Record<string, unknown>,
  writeTargets: ResultWriteTargetRecord[] = [],
): Partial<ActionFormValues> {
  const values: Partial<ActionFormValues> & Record<string, string | undefined> = {
    branch_path: stringMappingValue(resultMapping, 'branch_path'),
    commit_sha_path: stringMappingValue(resultMapping, 'commit_sha_path'),
    delivery_id_path: stringMappingValue(resultMapping, 'delivery_id_path'),
    delivery_status_path: stringMappingValue(resultMapping, 'delivery_status_path'),
    findings_path: stringMappingValue(resultMapping, 'findings_path'),
    insights_path: stringMappingValue(resultMapping, 'insights_path'),
    records_imported_path: stringMappingValue(resultMapping, 'records_imported_path'),
    recipients_path: stringMappingValue(resultMapping, 'recipients_path'),
    repository_id_path: stringMappingValue(resultMapping, 'repository_id_path'),
    risk_level_path: stringMappingValue(resultMapping, 'risk_level_path'),
    rows_path: stringMappingValue(resultMapping, 'rows_path'),
    subject_path: stringMappingValue(resultMapping, 'subject_path'),
    summary_path: stringMappingValue(resultMapping, 'summary_path'),
    write_target: writeTargetFromResultMapping(resultMapping),
  };
  const target = resultWriteTargetRecordByCode(writeTargets, values.write_target);
  target?.mapping_fields.forEach((field) => {
    values[field.key] = stringMappingValue(resultMapping, field.key);
  });
  return values;
}

function buildVisualResultMapping(
  values: Partial<ActionFormValues>,
  writeTargets: ResultWriteTargetRecord[] = [],
): Record<string, unknown> {
  const writeTarget = values.write_target || DEFAULT_RESULT_WRITE_TARGET;
  const target = resultWriteTargetRecordByCode(writeTargets, writeTarget);
  if (target) {
    const nextMapping = { ...target.default_result_mapping };
    const rawValues = values as Record<string, unknown>;
    target.mapping_fields.forEach((field) => {
      const rawValue = rawValues[field.key];
      if (typeof rawValue === 'string' && rawValue.trim()) {
        nextMapping[field.key] = rawValue.trim();
      }
    });
    return mergeWriteTarget(nextMapping, writeTarget);
  }
  return mergeWriteTarget(
    {
      ...(values.records_imported_path?.trim()
        ? { records_imported_path: values.records_imported_path.trim() }
        : {}),
    },
    writeTarget,
  );
}

function JsonDiagnosticsBlock({ title, value }: { title: string; value?: unknown }) {
  if (value === undefined || value === null) {
    return null;
  }
  return (
    <div>
      <Typography.Text strong>{title}</Typography.Text>
      <pre
        style={{
          background: '#f8fafc',
          border: '1px solid #e5e7eb',
          borderRadius: 6,
          margin: '8px 0 0',
          maxHeight: 260,
          overflow: 'auto',
          padding: 12,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {compactJson(value)}
      </pre>
    </div>
  );
}

function ResultWriteTargetMappingFields({
  writeTarget,
  writeTargets,
}: {
  writeTarget?: string;
  writeTargets: ResultWriteTargetRecord[];
}) {
  const target = resultWriteTargetRecordByCode(writeTargets, writeTarget);
  if (target?.mapping_fields.length) {
    return (
      <Space wrap>
        {target.mapping_fields.map((field) => (
          <Form.Item
            key={field.key}
            label={field.label}
            name={field.key}
            rules={field.required ? [{ required: true, message: `请输入${field.label}` }] : undefined}
          >
            <Input placeholder={field.placeholder} style={{ width: 220 }} />
          </Form.Item>
        ))}
      </Space>
    );
  }
  return null;
}

function TrialWritePreviewBlock({ value }: { value?: PluginActionTrialResult['write_preview'] }) {
  if (!value) {
    return null;
  }
  const writeTargetLabel = value.write_target_label || value.write_target || '-';
  const sampleRecords = value.sample_records ?? [];
  const hasReportPreview = value.report_preview && Object.keys(value.report_preview).length > 0;
  const hasPreviewValue = value.preview_value !== undefined;
  return (
    <Space
      orientation="vertical"
      size={8}
      style={{
        background: '#f8fafc',
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        padding: 12,
        width: '100%',
      }}
    >
      <Typography.Text strong>写入预览</Typography.Text>
      <Space wrap>
        <Tag color="blue">写入目标：{writeTargetLabel}</Tag>
        <Tag color="green">预计写入：{value.records_imported ?? 0}</Tag>
        <Tag>候选记录：{value.candidate_count ?? 0}</Tag>
        {value.source_row_count !== undefined && value.source_row_count !== null ? (
          <Tag>源数据：{value.source_row_count}</Tag>
        ) : null}
      </Space>
      {hasReportPreview ? (
        <>
          <Typography.Text type="secondary">报告字段预览</Typography.Text>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{compactJson(value.report_preview)}</pre>
        </>
      ) : null}
      {sampleRecords.length ? (
        <>
          <Typography.Text type="secondary">样例记录</Typography.Text>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{compactJson(sampleRecords)}</pre>
        </>
      ) : null}
      {hasPreviewValue ? (
        <>
          <Typography.Text type="secondary">预览值</Typography.Text>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{compactJson(value.preview_value)}</pre>
        </>
      ) : null}
    </Space>
  );
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback;
}

function booleanValue(value: unknown, fallback = false) {
  return typeof value === 'boolean' ? value : fallback;
}

function numberValue(value: unknown, fallback: number) {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function actionScenarioForExistingAction(
  action: PluginActionRecord,
  templates: PluginActionTemplateRecord[],
  plugins: PluginRecord[],
): string | undefined {
  const actionRequestConfig = action.request_config ?? {};
  const actionResultMapping = action.result_mapping ?? {};
  const actionPlugin = plugins.find((plugin) => plugin.id === action.plugin_id);
  for (const template of templates) {
    const templatePluginMatches =
      template.plugin_id === action.plugin_id || template.plugin_code === actionPlugin?.code;
    if (!templatePluginMatches) {
      continue;
    }
    const templateActionType = stringValue(template.action_type, 'http_request');
    if (templateActionType !== action.action_type) {
      continue;
    }
    const templateRequestConfig = isPlainRecord(template.request_config) ? template.request_config : {};
    const templateResultMapping = isPlainRecord(template.result_mapping) ? template.result_mapping : {};
    const templateDefaultCode = stringValue(template.default_code, template.code);
    const codeMatches = [template.code, templateDefaultCode].filter(Boolean).includes(action.code);
    const requestPathMatches =
      Boolean(stringValue(templateRequestConfig.path))
      && stringValue(templateRequestConfig.path) === stringValue(actionRequestConfig.path);
    const writeTargetMatches =
      Boolean(stringValue(templateResultMapping.write_target))
      && stringValue(templateResultMapping.write_target) === stringValue(actionResultMapping.write_target);
    if (codeMatches || (requestPathMatches && writeTargetMatches)) {
      return template.code;
    }
  }
  return undefined;
}

function pluginConnectionDraftFormValues(
  payload: Record<string, unknown>,
  schema?: PluginConnectionSchemaRecord,
): Partial<ConnectionFormValues> {
  const authConfig = isPlainRecord(payload.auth_config) ? payload.auth_config : {};
  const requestConfig = isPlainRecord(payload.request_config) ? payload.request_config : {};
  return {
    auth_config: stableJson(authConfig),
    auth_type: stringValue(payload.auth_type, 'none'),
    connection_header_rows: recordToRows(
      requestConfig.headers,
      schemaManagedRequestKeys(schema, 'headers'),
    ),
    connection_param_rows: recordToRows(
      requestConfig.query,
      schemaManagedRequestKeys(schema, 'query'),
    ),
    endpoint_url: stringValue(payload.endpoint_url),
    environment: stringValue(payload.environment, 'default'),
    header_name: stringValue(authConfig.header_name) || undefined,
    max_retries: numberValue(payload.max_retries, 0),
    name: stringValue(payload.name),
    password_ref: stringValue(authConfig.password_ref) || undefined,
    plugin_id: stringValue(payload.plugin_id),
    request_config: stableJson(requestConfig),
    schema_values: schemaValuesFromPayload(payload, schema),
    secret_ref: stringValue(authConfig.secret_ref) || undefined,
    status: stringValue(payload.status, 'active'),
    timeout_seconds: numberValue(payload.timeout_seconds, 30),
    token_ref: stringValue(authConfig.token_ref) || undefined,
    username_ref: stringValue(authConfig.username_ref) || undefined,
  };
}

function pluginConnectionTemplateFormValues(
  item: PluginMarketplaceItem | undefined,
  options: { pluginId?: string } = {},
): Partial<ConnectionFormValues> | undefined {
  if (!item) {
    return undefined;
  }
  const defaults = isPlainRecord(item?.connection_defaults) ? item.connection_defaults : undefined;
  if (!defaults) {
    return undefined;
  }
  return pluginConnectionDraftFormValues({
    ...defaults,
    plugin_id: options.pluginId || stringValue(defaults.plugin_id) || item?.plugin_id || undefined,
  }, item.connection_schema);
}

function marketplaceConnectionSchemaFields(item: PluginMarketplaceItem) {
  return (item.connection_schema?.sections ?? []).flatMap((section) =>
    (section.fields ?? []).map((field) => ({
      ...field,
      sectionTitle: section.title,
    })),
  );
}

function MarketplaceConnectionSchemaSummary({ item }: { item: PluginMarketplaceItem }) {
  const fields = marketplaceConnectionSchemaFields(item);
  if (!fields.length) {
    return <Typography.Text type="secondary">按默认连接模板配置</Typography.Text>;
  }
  return (
    <Space wrap size={4}>
      {fields.slice(0, 5).map((field) => (
        <Tag color={field.required ? 'orange' : 'default'} key={`${field.sectionTitle}-${field.key}`}>
          {field.label}
        </Tag>
      ))}
      {fields.length > 5 ? <Tag>+{fields.length - 5}</Tag> : null}
    </Space>
  );
}

function MarketplaceConnectionSchemaDetail({ item }: { item: PluginMarketplaceItem }) {
  const fields = marketplaceConnectionSchemaFields(item);
  if (!fields.length) {
    return <Typography.Text type="secondary">该官方插件暂未声明连接表单 schema，将使用默认连接模板。</Typography.Text>;
  }
  return (
    <Table
      columns={[
        { dataIndex: 'sectionTitle', title: '分组', width: 160 },
        {
          dataIndex: 'label',
          title: '字段',
          width: 180,
          render: (value, row) => (
            <Space size={4}>
              <Typography.Text>{String(value)}</Typography.Text>
              {row.required ? <Tag color="orange">必填</Tag> : null}
              {row.supports_system_variables ? <Tag color="blue">变量</Tag> : null}
            </Space>
          ),
        },
        { dataIndex: 'path', title: '写入路径', width: 260 },
        { dataIndex: 'type', title: '类型', width: 120 },
        { dataIndex: 'description', title: '说明', ellipsis: true },
      ]}
      dataSource={fields}
      pagination={false}
      rowKey={(row) => `${row.sectionTitle}-${row.key}`}
      scroll={{ x: 920 }}
      size="small"
    />
  );
}

function pluginActionDraftFormValues(
  payload: Record<string, unknown>,
  writeTargets: ResultWriteTargetRecord[] = [],
): Partial<ActionFormValues> {
  const requestConfig = isPlainRecord(payload.request_config) ? payload.request_config : {};
  const resultMapping = isPlainRecord(payload.result_mapping)
    ? payload.result_mapping
    : defaultResultMappingForWriteTarget(DEFAULT_RESULT_WRITE_TARGET, writeTargets);
  const resolvedConnectionId =
    stringValue(payload.connection_id) || resolveAssistantDraftResourceId(payload, 'plugin_connection');
  return {
    action_type: stringValue(payload.action_type, 'http_request'),
    code: stringValue(payload.code),
    connection_id: resolvedConnectionId || undefined,
    description: stringValue(payload.description) || undefined,
    header_rows: recordToRows(requestConfig.headers),
    method: stringValue(requestConfig.method, 'GET'),
    name: stringValue(payload.name),
    param_rows: recordToRows(requestConfig.query),
    path: stringValue(requestConfig.path),
    plugin_id: stringValue(payload.plugin_id),
    request_config: stableJson(requestConfig),
    requires_human_review: booleanValue(payload.requires_human_review),
    result_mapping: stableJson(resultMapping),
    status: stringValue(payload.status, 'active'),
    ...resultMappingVisualFields(resultMapping, writeTargets),
  };
}

function diagnosticText(value: unknown): string {
  if (value === undefined || value === null || value === '') {
    return '-';
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return compactJson(value);
}

function connectionTestStatusColor(status: string) {
  if (status === 'succeeded') {
    return 'green';
  }
  if (status === 'failed') {
    return 'red';
  }
  return 'default';
}

function runnerHealthStatusColor(status: string | undefined) {
  if (status === 'managed') {
    return 'blue';
  }
  if (status === 'online') {
    return 'green';
  }
  if (status === 'offline') {
    return 'orange';
  }
  if (status === 'never_connected') {
    return 'default';
  }
  if (status === 'disabled') {
    return 'red';
  }
  return 'blue';
}

function isSystemDefaultRunner(runner: AiExecutorRunnerRecord) {
  return runner.id === SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID
    || runner.protocol === SYSTEM_DEFAULT_AI_EXECUTOR_TYPE
    || runner.metadata?.is_system === true;
}

function ConnectionLastTestSummary({ connection }: { connection: PluginConnectionRecord }) {
  const summary = connection.last_test_summary;
  if (!summary?.status) {
    return <Typography.Text type="secondary">未测试</Typography.Text>;
  }
  const detail = summary.error_code
    || summary.failed_step
    || (summary.response_status_code ? `HTTP ${summary.response_status_code}` : undefined)
    || summary.checked_at
    || '-';
  return (
    <Space orientation="vertical" size={2} style={{ width: '100%' }}>
      <Space size={6} wrap>
        <Tag color={connectionTestStatusColor(String(summary.status))}>{summary.status}</Tag>
        {typeof summary.latency_ms === 'number' ? (
          <Typography.Text>{summary.latency_ms}ms</Typography.Text>
        ) : null}
      </Space>
      <Typography.Text
        ellipsis={{ tooltip: summary.error_message || detail }}
        style={{ display: 'block', maxWidth: '100%' }}
        type={summary.status === 'failed' ? 'danger' : 'secondary'}
      >
        {detail}
      </Typography.Text>
    </Space>
  );
}

function ConnectionRequestDebugPanel({
  onCopyAsActionTemplate,
  repairSuggestions = [],
  requestSummary,
  testHistory = [],
}: {
  onCopyAsActionTemplate?: () => void;
  repairSuggestions?: PluginConnectionRepairSuggestion[];
  requestSummary?: unknown;
  testHistory?: PluginConnectionTestHistoryRecord[];
}) {
  if (!isPlainRecord(requestSummary)) {
    return null;
  }
  const headers = isPlainRecord(requestSummary.headers) ? requestSummary.headers : {};
  const headerSources = isPlainRecord(requestSummary.header_sources) ? requestSummary.header_sources : {};
  const headerNames = Array.from(new Set([...Object.keys(headers), ...Object.keys(headerSources)]));
  const headerRows = headerNames.map((name) => ({
    name,
    source: diagnosticText(headerSources[name]),
    value: diagnosticText(headers[name]),
  }));
  const variableResolutions = Array.isArray(requestSummary.variable_resolutions)
    ? requestSummary.variable_resolutions.filter(isPlainRecord)
    : [];
  const variableRows = variableResolutions.map((item, index) => ({
    expression: diagnosticText(item.expression),
    name: diagnosticText(item.name),
    offset_days: item.offset_days === undefined || item.offset_days === null
      ? '-'
      : diagnosticText(item.offset_days),
    path: diagnosticText(item.path),
    resolved_text: diagnosticText(item.resolved_text),
    resolved_value: diagnosticText(item.resolved_value),
    rowKey: `${diagnosticText(item.path)}-${diagnosticText(item.token)}-${index}`,
    status: diagnosticText(item.status),
    token: diagnosticText(item.token),
  }));
  const variableDiffRows = variableRows.map((item) => ({
    after: item.resolved_text,
    before: item.expression,
    path: item.path,
    rowKey: item.rowKey,
    status: item.status,
  }));
  const historyRows = testHistory.map((item, index) => {
    const historyRequest = isPlainRecord(item.request_summary) ? item.request_summary : {};
    const historyResponse = isPlainRecord(item.response_summary) ? item.response_summary : {};
    return {
      action_template_draft: item.action_template_draft,
      checked_at: diagnosticText(item.checked_at),
      error_message: diagnosticText(item.error_message),
      latency_ms: item.latency_ms === undefined || item.latency_ms === null ? '-' : `${item.latency_ms}ms`,
      method: diagnosticText(historyRequest.method),
      repair_suggestions: item.repair_suggestions ?? [],
      request_summary: historyRequest,
      response_status: diagnosticText(historyResponse.status_code),
      response_summary: historyResponse,
      rowKey: `${diagnosticText(item.checked_at)}-${index}`,
      status: diagnosticText(item.status),
      url: diagnosticText(historyRequest.url),
    };
  });
  const curlCommand = diagnosticText(requestSummary.curl_command);

  return (
    <Space orientation="vertical" size={10} style={{ width: '100%' }}>
      <Typography.Text strong>请求调试台</Typography.Text>
      <div
        style={{
          border: '1px solid #e5e7eb',
          borderRadius: 8,
          padding: 12,
        }}
      >
        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
          <div>
            <Typography.Text style={{ color: '#64748b', display: 'block', marginBottom: 4 }}>
              最终请求 URL
            </Typography.Text>
            <Typography.Text copyable style={{ wordBreak: 'break-all' }}>
              {diagnosticText(requestSummary.url)}
            </Typography.Text>
          </div>
          <Space wrap>
            <Tag>Method: {diagnosticText(requestSummary.method)}</Tag>
            <Tag>Protocol: {diagnosticText(requestSummary.protocol)}</Tag>
          </Space>
          {curlCommand !== '-' ? (
            <div>
              <Typography.Text style={{ color: '#64748b', display: 'block', marginBottom: 4 }}>
                可复制 cURL
              </Typography.Text>
              <Typography.Text copyable style={{ wordBreak: 'break-all' }}>
                {curlCommand}
              </Typography.Text>
            </div>
          ) : null}
          <JsonDiagnosticsBlock title="Query 参数" value={requestSummary.query} />
          <JsonDiagnosticsBlock title="请求 Body" value={requestSummary.body} />
        </Space>
      </div>
      <div>
        <Space align="center" style={{ justifyContent: 'space-between', marginBottom: 8, width: '100%' }} wrap>
          <Space size={8} wrap>
            <Typography.Text strong>请求回放台</Typography.Text>
            <Typography.Text type="secondary">最近测试记录</Typography.Text>
          </Space>
          {onCopyAsActionTemplate ? (
            <Button size="small" onClick={onCopyAsActionTemplate}>
              复制为动作模板
            </Button>
          ) : null}
        </Space>
        {historyRows.length > 0 ? (
          <Table
            columns={[
              { dataIndex: 'checked_at', title: '测试时间', width: 190 },
              { dataIndex: 'status', title: '状态', width: 110, render: (value: string) => <Tag>{value}</Tag> },
              { dataIndex: 'latency_ms', title: '耗时', width: 90 },
              { dataIndex: 'method', title: '方法', width: 90 },
              {
                dataIndex: 'url',
                title: '请求 URL',
                render: (value: string) => (
                  <Typography.Text copyable style={{ wordBreak: 'break-word' }}>
                    {value}
                  </Typography.Text>
                ),
              },
              { dataIndex: 'response_status', title: '响应码', width: 100 },
            ]}
            dataSource={historyRows}
            expandable={{
              expandedRowRender: (record) => (
                <Space orientation="vertical" size={8} style={{ width: '100%' }}>
                  <Space orientation="vertical" size={4} style={{ width: '100%' }}>
                    <Typography.Text strong>历史请求详情</Typography.Text>
                    {record.error_message !== '-' ? (
                      <Alert description={record.error_message} showIcon title="历史错误信息" type="error" />
                    ) : null}
                  </Space>
                  {record.repair_suggestions.length > 0 ? (
                    <Space orientation="vertical" size={6} style={{ width: '100%' }}>
                      <Typography.Text strong>历史修复建议</Typography.Text>
                      {record.repair_suggestions.map((suggestion) => (
                        <Alert
                          description={suggestion.detail}
                          key={suggestion.code}
                          showIcon
                          title={suggestion.title}
                          type="warning"
                        />
                      ))}
                    </Space>
                  ) : null}
                  <JsonDiagnosticsBlock title="历史完整请求 JSON" value={record.request_summary} />
                  <JsonDiagnosticsBlock title="历史远端响应信息" value={record.response_summary} />
                  <JsonDiagnosticsBlock title="历史动作模板草案" value={record.action_template_draft} />
                </Space>
              ),
              rowExpandable: () => true,
            }}
            pagination={false}
            rowKey="rowKey"
            scroll={{ x: 980 }}
            size="small"
          />
        ) : (
          <Typography.Text type="secondary">暂无历史测试记录，本次结果会作为第一条回放保存。</Typography.Text>
        )}
      </div>
      {repairSuggestions.length > 0 ? (
        <div>
          <Typography.Text strong>修复建议</Typography.Text>
          <Space orientation="vertical" size={8} style={{ marginTop: 8, width: '100%' }}>
            {repairSuggestions.map((suggestion) => (
              <Alert
                description={suggestion.detail}
                key={suggestion.code}
                showIcon
                title={suggestion.title}
                type="warning"
              />
            ))}
          </Space>
        </div>
      ) : null}
      <div>
        <Space size={8} style={{ marginBottom: 8 }} wrap>
          <Typography.Text strong>动态变量解析</Typography.Text>
          <Tag>Timezone: {diagnosticText(requestSummary.variable_resolution_timezone)}</Tag>
        </Space>
        {variableDiffRows.length > 0 ? (
          <div style={{ marginBottom: 10 }}>
            <Typography.Text strong>变量解析前 / 后差异</Typography.Text>
            <Table
              columns={[
                { dataIndex: 'path', title: '位置', width: 180 },
                {
                  dataIndex: 'before',
                  title: '解析前',
                  render: (value: string) => (
                    <Typography.Text copyable style={{ wordBreak: 'break-word' }}>
                      {value}
                    </Typography.Text>
                  ),
                },
                {
                  dataIndex: 'after',
                  title: '解析后',
                  render: (value: string) => (
                    <Typography.Text copyable style={{ wordBreak: 'break-word' }}>
                      {value}
                    </Typography.Text>
                  ),
                },
                { dataIndex: 'status', title: '状态', width: 110, render: (value: string) => <Tag>{value}</Tag> },
              ]}
              dataSource={variableDiffRows}
              pagination={false}
              rowKey="rowKey"
              scroll={{ x: 760 }}
              size="small"
            />
          </div>
        ) : null}
        {variableRows.length > 0 ? (
          <Table
            columns={[
              { dataIndex: 'path', title: '位置', width: 180 },
              {
                dataIndex: 'expression',
                title: '原始表达式',
                width: 220,
                render: (value: string) => (
                  <Typography.Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {value}
                  </Typography.Text>
                ),
              },
              { dataIndex: 'token', title: '变量', width: 160 },
              { dataIndex: 'offset_days', title: '偏移天数', width: 100 },
              {
                dataIndex: 'resolved_value',
                title: '解析值',
                width: 180,
                render: (value: string) => (
                  <Typography.Text copyable style={{ wordBreak: 'break-word' }}>
                    {value}
                  </Typography.Text>
                ),
              },
              {
                dataIndex: 'resolved_text',
                title: '最终值',
                render: (value: string) => (
                  <Typography.Text copyable style={{ wordBreak: 'break-word' }}>
                    {value}
                  </Typography.Text>
                ),
              },
              { dataIndex: 'status', title: '状态', width: 110, render: (value: string) => <Tag>{value}</Tag> },
            ]}
            dataSource={variableRows}
            pagination={false}
            rowKey="rowKey"
            scroll={{ x: 1120 }}
            size="small"
          />
        ) : (
          <Typography.Text type="secondary">未检测到动态变量，当前请求参数按保存值直接发送。</Typography.Text>
        )}
      </div>
      {headerRows.length > 0 ? (
        <div>
          <Typography.Text strong>Header 来源</Typography.Text>
          <Table
            columns={[
              { dataIndex: 'name', title: 'Header', width: 220 },
              {
                dataIndex: 'value',
                title: '最终值',
                render: (value: string) => (
                  <Typography.Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {value}
                  </Typography.Text>
                ),
              },
              {
                dataIndex: 'source',
                title: '来源',
                width: 240,
                render: (value: string) => (
                  <Typography.Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {value}
                  </Typography.Text>
                ),
              },
            ]}
            dataSource={headerRows}
            pagination={false}
            rowKey="name"
            scroll={{ x: 760 }}
            size="small"
          />
        </div>
      ) : null}
      <JsonDiagnosticsBlock title="原始请求配置" value={requestSummary.original_request_config} />
      <JsonDiagnosticsBlock title="完整请求 JSON" value={requestSummary} />
    </Space>
  );
}

function RequestParameterRows({
  addText,
  name,
  namePlaceholder,
  title,
  valuePlaceholder,
}: {
  addText: string;
  name: 'connection_header_rows' | 'connection_param_rows' | 'header_rows' | 'param_rows';
  namePlaceholder: string;
  title: string;
  valuePlaceholder: string;
}) {
  const form = Form.useFormInstance();
  return (
    <Form.List name={name}>
      {(fields, { add, remove }) => (
        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
          <div style={{ color: '#53627a', fontWeight: 600 }}>{title}</div>
          <Space orientation="vertical" size={6} style={{ width: '100%' }}>
            {fields.map((field) => (
              <Space key={field.key} align="baseline" wrap>
                <Form.Item
                  name={[field.name, 'enabled']}
                  valuePropName="checked"
                  initialValue
                  style={{ marginBottom: 0 }}
                >
                  <Checkbox />
                </Form.Item>
                <Form.Item name={[field.name, 'name']} style={{ marginBottom: 0 }}>
                  <Input placeholder={namePlaceholder} style={{ width: 180 }} />
                </Form.Item>
                <Form.Item name={[field.name, 'value']} style={{ marginBottom: 0 }}>
                  <Input placeholder={valuePlaceholder} style={{ width: 260 }} />
                </Form.Item>
                <Select
                  allowClear
                  options={systemVariableOptions}
                  placeholder="系统变量"
                  style={{ width: 190 }}
                  onChange={(value) => {
                    if (value) {
                      form.setFieldValue([name, field.name, 'value'], value);
                    }
                  }}
                />
                <Form.Item name={[field.name, 'type']} initialValue="string" style={{ marginBottom: 0 }}>
                  <Select options={requestParameterTypeOptions} style={{ width: 120 }} />
                </Form.Item>
                <Form.Item name={[field.name, 'description']} style={{ marginBottom: 0 }}>
                  <Input placeholder="说明" style={{ width: 180 }} />
                </Form.Item>
                <Button aria-label="删除参数" icon={<DeleteOutlined />} onClick={() => remove(field.name)} />
              </Space>
            ))}
          </Space>
          <Button
            icon={<PlusOutlined />}
            onClick={() => add({ enabled: true, type: 'string' })}
            type="dashed"
          >
            {addText}
          </Button>
        </Space>
      )}
    </Form.List>
  );
}

function normalizeSchemaOptions(field: PluginConnectionSchemaFieldRecord) {
  return (field.options ?? []).map((option) => (
    typeof option === 'string' ? { label: option, value: option } : option
  ));
}

function ConnectionSchemaFields({
  pluginCode,
  schema,
}: {
  pluginCode?: string;
  schema?: PluginConnectionSchemaRecord;
}) {
  const form = Form.useFormInstance();
  const sections = schema?.sections ?? [];
  if (!sections.length) {
    return null;
  }

  return (
    <Space orientation="vertical" size={12} style={{ width: '100%' }}>
      {pluginCode === 'github' ? (
        <Alert
          description="Params 属于高级查询参数，只有需要补充 GitHub API query 时再填写，例如 state、per_page、ref。Headers 默认保留 Accept 和 X-GitHub-Api-Version。"
          showIcon
          title="GitHub 连接只需要粘贴仓库地址；系统会自动解析 owner/repo，Params 不用再填。"
          type="info"
        />
      ) : null}
      {pluginCode === 'gitlab' ? (
        <Alert
          description="填写本地 GitLab 项目地址后，系统会自动同步 Endpoint URL，并解析 project_id/project_path 给 GitLab API 使用。Params 只用于补充额外查询参数。"
          showIcon
          title="GitLab 连接只需要粘贴本地项目地址。"
          type="info"
        />
      ) : null}
      {sections.map((section) => (
        <Space key={section.key} orientation="vertical" size={8} style={{ width: '100%' }}>
          <div style={{ color: '#53627a', fontWeight: 600 }}>{section.title}</div>
          <Space wrap align="start">
            {(section.fields ?? []).map((field) => {
              const rules = [
                ...(field.required ? [{ required: true, message: `请输入${field.label}` }] : []),
                ...(field.type === 'github_repository_url'
                  ? [{
                    validator: (_: unknown, value: unknown) => (
                      !value || parseGitRepositoryAddress(value)
                        ? Promise.resolve()
                        : Promise.reject(new Error('请输入有效的 GitHub 仓库地址，例如 https://github.com/acme/ai-brain.git'))
                    ),
                  }]
                  : []),
                ...(field.type === 'gitlab_project_url'
                  ? [{
                    validator: (_: unknown, value: unknown) => (
                      !value || parseGitLabProjectAddress(value)
                        ? Promise.resolve()
                        : Promise.reject(new Error('请输入有效的 GitLab 地址，例如 http://gitlab.local/acme/ai-brain.git'))
                    ),
                  }]
                  : []),
              ];
              const fieldName = ['schema_values', field.key];
              const schemaOptions = normalizeSchemaOptions(field);
              const control = field.type === 'select' && schemaOptions.length > 0 ? (
                <Select
                  allowClear={!field.required}
                  options={schemaOptions}
                  placeholder={field.placeholder || field.label}
                  style={{ width: 240 }}
                />
              ) : field.type === 'number' ? (
                <InputNumber placeholder={field.placeholder || field.label} style={{ width: 240 }} />
              ) : field.type === 'boolean' ? (
                <Switch />
              ) : (
                <Input
                  placeholder={field.placeholder || field.label}
                  style={{ width: ['github_repository_url', 'gitlab_project_url'].includes(field.type ?? '') ? 420 : 240 }}
                />
              );
              return (
                <Space key={field.key} align="baseline" size={6}>
                  <Form.Item
                    extra={field.description}
                    label={field.label}
                    name={fieldName}
                    rules={rules.length ? rules : undefined}
                    style={{ marginBottom: 8 }}
                    valuePropName={field.type === 'boolean' ? 'checked' : 'value'}
                  >
                    {control}
                  </Form.Item>
                  {field.supports_system_variables ? (
                    <Select
                      allowClear
                      options={systemVariableOptions}
                      placeholder="系统变量"
                      style={{ width: 190, marginTop: 30 }}
                      onChange={(value) => {
                        if (value) {
                          form.setFieldValue(fieldName, value);
                        }
                      }}
                    />
                  ) : null}
                </Space>
              );
            })}
          </Space>
        </Space>
      ))}
    </Space>
  );
}

export default function PluginsPage() {
  const [pluginForm] = Form.useForm<PluginFormValues>();
  const [connectionForm] = Form.useForm<ConnectionFormValues>();
  const [actionForm] = Form.useForm<ActionFormValues>();
  const [runnerForm] = Form.useForm<AiExecutorRunnerFormValues>();
  const [plugins, setPlugins] = useState<PluginRecord[]>([]);
  const [marketplaceItems, setMarketplaceItems] = useState<PluginMarketplaceItem[]>([]);
  const [actionTemplates, setActionTemplates] = useState<PluginActionTemplateRecord[]>([]);
  const [resultWriteTargets, setResultWriteTargets] = useState<ResultWriteTargetRecord[]>([]);
  const [runners, setRunners] = useState<AiExecutorRunnerRecord[]>([]);
  const [connections, setConnections] = useState<PluginConnectionRecord[]>([]);
  const [actions, setActions] = useState<PluginActionRecord[]>([]);
  const [scheduledJobs, setScheduledJobs] = useState<ScheduledJobRecord[]>([]);
  const [systemVariables, setSystemVariables] = useState<PluginSystemVariableRecord[]>([]);
  const [systemVariableTimezone, setSystemVariableTimezone] = useState('Asia/Shanghai');
  const [systemVariableModalOpen, setSystemVariableModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [pluginModalOpen, setPluginModalOpen] = useState(false);
  const [connectionModalOpen, setConnectionModalOpen] = useState(false);
  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [runnerModalOpen, setRunnerModalOpen] = useState(false);
  const [connectionSubmitAction, setConnectionSubmitAction] = useState<'save' | 'save-test'>();
  const [editingPlugin, setEditingPlugin] = useState<PluginRecord | undefined>();
  const [editingConnection, setEditingConnection] = useState<PluginConnectionRecord | undefined>();
  const [editingAction, setEditingAction] = useState<PluginActionRecord | undefined>();
  const [editingRunner, setEditingRunner] = useState<AiExecutorRunnerRecord | undefined>();
  const [rotatingRunner, setRotatingRunner] = useState<AiExecutorRunnerRecord | undefined>();
  const [rotatingRunnerLoading, setRotatingRunnerLoading] = useState(false);
  const [rotatedRunnerToken, setRotatedRunnerToken] = useState<string | undefined>();
  const [runnerLogModalOpen, setRunnerLogModalOpen] = useState(false);
  const [runnerLogLoading, setRunnerLogLoading] = useState(false);
  const [runnerLogTask, setRunnerLogTask] = useState<AiExecutorTaskRecord | undefined>();
  const [runnerLogRows, setRunnerLogRows] = useState<AiExecutorTaskLogRecord[]>([]);
  const [assistantConnectionDraftSource, setAssistantConnectionDraftSource] = useState<
    { draftId?: string; title?: string } | undefined
  >();
  const [assistantActionDraftSource, setAssistantActionDraftSource] = useState<
    { draftId?: string; title?: string } | undefined
  >();
  const [trialModalOpen, setTrialModalOpen] = useState(false);
  const [trialAction, setTrialAction] = useState<PluginActionRecord | undefined>();
  const [trialConnectionId, setTrialConnectionId] = useState<string | undefined>();
  const [trialInputJson, setTrialInputJson] = useState('{}');
  const [trialResult, setTrialResult] = useState<PluginActionTrialResult | undefined>();
  const [trialRunning, setTrialRunning] = useState(false);
  const [actionScenario, setActionScenario] = useState<string | undefined>();
  const [connectionEnvironmentFilter, setConnectionEnvironmentFilter] = useState<string | undefined>();
  const [advancedConnectionJsonOpen, setAdvancedConnectionJsonOpen] = useState(false);
  const [advancedConnectionRequestJsonOpen, setAdvancedConnectionRequestJsonOpen] = useState(false);
  const [advancedActionJsonOpen, setAdvancedActionJsonOpen] = useState(false);
  const [testingConnectionId, setTestingConnectionId] = useState<string | undefined>();
  const [testingRunnerId, setTestingRunnerId] = useState<string | undefined>();
  const selectedConnectionAuthType = Form.useWatch('auth_type', connectionForm);
  const selectedConnectionPluginId = Form.useWatch('plugin_id', connectionForm);
  const actionFormValues = Form.useWatch([], actionForm) as ActionFormValues | undefined;

  const pluginOptions = useMemo(
    () => plugins.map((plugin) => ({ label: `${plugin.name} (${plugin.protocol})`, value: plugin.id })),
    [plugins],
  );
  const connectionOptions = useMemo(
    () =>
      connections.map((connection) => ({
        label: `${connection.name} (${connection.environment ?? 'default'})`,
        value: connection.id,
      })),
    [connections],
  );
  const connectionById = useMemo(
    () => new Map(connections.map((connection) => [connection.id, connection])),
    [connections],
  );
  const pluginById = useMemo(() => new Map(plugins.map((plugin) => [plugin.id, plugin])), [plugins]);
  const marketplaceItemByPluginCode = useMemo(
    () => new Map(marketplaceItems.map((item) => [item.code, item])),
    [marketplaceItems],
  );
  const marketplaceItemByPluginId = useMemo(
    () => new Map(
      marketplaceItems
        .filter((item) => item.plugin_id)
        .map((item) => [String(item.plugin_id), item]),
    ),
    [marketplaceItems],
  );
  const selectedConnectionPlugin = selectedConnectionPluginId
    ? pluginById.get(String(selectedConnectionPluginId))
    : undefined;
  const selectedConnectionPluginCode = selectedConnectionPlugin?.code;
  const selectedConnectionIsGithub = selectedConnectionPluginCode === 'github';
  const selectedConnectionIsGitlab = selectedConnectionPluginCode === 'gitlab';
  const selectedConnectionMarketplaceItem = selectedConnectionPlugin
    ? marketplaceItemByPluginCode.get(selectedConnectionPlugin.code)
      ?? marketplaceItemByPluginId.get(selectedConnectionPlugin.id)
    : undefined;
  const selectedConnectionSchema = selectedConnectionMarketplaceItem?.connection_schema;
  const actionTemplateOptions = useMemo(
    () => actionTemplates.map((template) => ({ label: template.name, value: template.code })),
    [actionTemplates],
  );
  const resultWriteTargetOptions = useMemo(
    () => resultWriteTargets.map((target) => ({
      label: target.form_label || target.label,
      value: target.code,
    })),
    [resultWriteTargets],
  );
  const systemVariablePreviewItems = useMemo<PluginSystemVariableRecord[]>(() => {
    const items = systemVariables.length > 0
      ? systemVariables
      : systemVariableOptions.map((item) => ({
        description: item.description,
        expression: item.value,
        label: item.label,
        value: '加载后显示',
      }));
    return items.map((item) => ({
      ...item,
      description: item.description ?? systemVariableDescriptionByExpression.get(item.expression),
    }));
  }, [systemVariables]);
  const compactSystemVariablePreviewItems = useMemo(() => {
    const preferredExpressions = ['{{current_date}}', '{{current_date-7}}', '{{last_full_week.start}}'];
    const itemByExpression = new Map(systemVariablePreviewItems.map((item) => [item.expression, item]));
    const preferredItems = preferredExpressions
      .map((expression) => itemByExpression.get(expression))
      .filter((item): item is PluginSystemVariableRecord => Boolean(item));
    return preferredItems.length > 0 ? preferredItems : systemVariablePreviewItems.slice(0, 3);
  }, [systemVariablePreviewItems]);
  const systemVariablePreviewColumns = useMemo(() => [
    {
      dataIndex: 'label',
      key: 'label',
      title: '变量',
      width: 180,
      render: (value: string, record: PluginSystemVariableRecord) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text strong>{value}</Typography.Text>
          {record.description ? (
            <Typography.Text type="secondary">{record.description}</Typography.Text>
          ) : null}
        </Space>
      ),
    },
    {
      dataIndex: 'expression',
      key: 'expression',
      title: '表达式',
      width: 220,
      render: (value: string) => (
        <Typography.Text code copyable={{ text: value }}>
          {value}
        </Typography.Text>
      ),
    },
    {
      dataIndex: 'value',
      key: 'value',
      title: '当前解析值',
      width: 260,
      render: (value: string) => (
        <Typography.Text code copyable={value !== '加载后显示' ? { text: value } : false}>
          {value}
        </Typography.Text>
      ),
    },
  ], []);
  const requestPreview = useMemo(
    () => buildActionRequestPreview(actionFormValues, connectionById.get(actionFormValues?.connection_id ?? '')),
    [actionFormValues, connectionById],
  );
  const connectionDefaultsForPlugin = useCallback((plugin?: PluginRecord) => {
    const item = plugin
      ? marketplaceItemByPluginCode.get(plugin.code) ?? marketplaceItemByPluginId.get(plugin.id)
      : undefined;
    return pluginConnectionTemplateFormValues(item, { pluginId: plugin?.id });
  }, [marketplaceItemByPluginCode, marketplaceItemByPluginId]);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [
        nextPlugins,
        nextMarketplaceItems,
        nextActionTemplates,
        nextResultWriteTargets,
        nextRunners,
        nextConnections,
        nextActions,
        nextJobs,
      ] = await Promise.all([
        fetchPlugins(),
        fetchPluginMarketplace(),
        fetchPluginActionTemplates(),
        fetchResultWriteTargets(),
        fetchAiExecutorRunners(),
        fetchPluginConnections({ environment: connectionEnvironmentFilter }),
        fetchPluginActions(),
        fetchScheduledJobs(),
      ]);
      setPlugins(nextPlugins);
      setMarketplaceItems(nextMarketplaceItems);
      setActionTemplates(nextActionTemplates);
      setResultWriteTargets(nextResultWriteTargets);
      setRunners(nextRunners);
      setConnections(nextConnections);
      setActions(nextActions);
      setScheduledJobs(nextJobs);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '插件配置加载失败');
    } finally {
      setLoading(false);
    }
  }, [connectionEnvironmentFilter]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [reload]);

  useEffect(() => {
    fetchPluginSystemVariables('Asia/Shanghai')
      .then((result) => {
        setSystemVariables(result.items);
        setSystemVariableTimezone(result.timezone || 'Asia/Shanghai');
      })
      .catch(() => {
        setSystemVariables([]);
        setSystemVariableTimezone('Asia/Shanghai');
      });
  }, []);

  const openCreatePluginModal = () => {
    setEditingPlugin(undefined);
    pluginForm.resetFields();
    pluginForm.setFieldsValue({
      category: 'general',
      protocol: 'http',
      risk_level: 'medium',
      status: 'active',
    });
    setPluginModalOpen(true);
  };

  const openEditPluginModal = (plugin: PluginRecord) => {
    if (plugin.is_system) {
      message.info('官方标准插件不能修改，请在连接里维护接入参数');
      return;
    }
    setEditingPlugin(plugin);
    pluginForm.resetFields();
    pluginForm.setFieldsValue({
      category: plugin.category ?? 'general',
      code: plugin.code,
      description: plugin.description ?? undefined,
      name: plugin.name,
      protocol: plugin.protocol,
      risk_level: plugin.risk_level ?? 'medium',
      status: plugin.status,
    });
    setPluginModalOpen(true);
  };

  const closePluginModal = () => {
    setPluginModalOpen(false);
    setEditingPlugin(undefined);
    pluginForm.resetFields();
  };

  const submitPlugin = async () => {
    const values = await pluginForm.validateFields();
    if (editingPlugin) {
      await updatePlugin(editingPlugin.id, values);
      message.success('插件已更新');
    } else {
      await createPlugin(values);
      message.success('插件已创建');
    }
    closePluginModal();
    await reload();
  };

  const copyOfficialPlugin = async (plugin: PluginRecord) => {
    await copyPlugin(plugin.id, {
      code: `${plugin.code}_custom`,
      name: `${plugin.name} 副本`,
    });
    message.success('官方插件已复制为自定义插件');
    await reload();
  };

  const openCreateRunnerModal = () => {
    setEditingRunner(undefined);
    runnerForm.resetFields();
    runnerForm.setFieldsValue({
      claude_command: 'claude',
      codex_command: 'codex',
      endpoint_url: `${window.location.origin.replace(/:\d+$/, ':8000')}/api/system/ai-executor-runners`,
      executor_types: ['codex', 'openclaw'],
      hermes_command: 'hermes',
      heartbeat_timeout_seconds: 120,
      install_mode: 'systemd',
      max_concurrent_tasks: 1,
      metadata: '{}',
      openclaw_command: 'openclaw',
      package_arch: 'amd64',
      protocol: 'runner_polling',
      status: 'active',
      target_os: 'linux',
      workspace_roots: '/Users/zeek/source/e-ai-brain',
    });
    setRunnerModalOpen(true);
  };

  const openEditRunnerModal = (runner: AiExecutorRunnerRecord) => {
    setEditingRunner(runner);
    runnerForm.resetFields();
    const executorCommands = runnerExecutorCommandsFromMetadata(runner.metadata);
    const packageOptions = runnerPackageOptionsFromMetadata(runner.metadata);
    runnerForm.setFieldsValue({
      claude_command: executorCommands.claude || 'claude',
      codex_command: executorCommands.codex || 'codex',
      endpoint_url: runner.endpoint_url ?? 'runner://local',
      executor_types: runner.executor_types ?? ['codex'],
      hermes_command: executorCommands.hermes || 'hermes',
      heartbeat_timeout_seconds: runner.heartbeat_timeout_seconds ?? 120,
      install_mode: packageOptions.install_mode,
      max_concurrent_tasks: runner.max_concurrent_tasks ?? 1,
      metadata: stableJson(runner.metadata ?? {}),
      name: runner.name,
      openclaw_command: executorCommands.openclaw || 'openclaw',
      package_arch: packageOptions.arch,
      protocol: runner.protocol ?? 'runner_polling',
      status: runner.status,
      target_os: packageOptions.target_os,
      workspace_roots: arrayToLines(runner.workspace_roots),
    });
    setRunnerModalOpen(true);
  };

  const closeRunnerModal = () => {
    setRunnerModalOpen(false);
    setEditingRunner(undefined);
    runnerForm.resetFields();
  };

  const submitRunner = async () => {
    const values = await runnerForm.validateFields();
    const payload = runnerPayload(values);
    if (editingRunner) {
      await updateAiExecutorRunner(editingRunner.id, payload);
      message.success('执行器已更新');
    } else {
      const created = await createAiExecutorRunner(payload);
      message.success('执行器已创建');
      if (created.runner_token) {
        Modal.info({
          content: (
            <Space orientation="vertical" size={8}>
              <Typography.Text>Runner Token 仅在创建时返回，请配置到本地 Runner。</Typography.Text>
              <Typography.Text code copyable={{ text: created.runner_token }}>
                {created.runner_token}
              </Typography.Text>
            </Space>
          ),
          title: 'Runner Token',
        });
      }
    }
    closeRunnerModal();
    await reload();
  };

  const confirmDeleteRunner = (runner: AiExecutorRunnerRecord) => {
    Modal.confirm({
      content: `确定删除执行器「${runner.name}」吗？有未完成任务时后端会拒绝删除。`,
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteAiExecutorRunner(runner.id);
          message.success('执行器已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '执行器删除失败');
        }
      },
      title: '删除执行器',
    });
  };

  const latestRunnerTaskId = (runner: AiExecutorRunnerRecord): string | undefined => {
    const metadataTaskId = runner.metadata?.latest_task_id;
    return runner.latest_task_id ?? (typeof metadataTaskId === 'string' ? metadataTaskId : undefined);
  };

  const rotateRunnerToken = (runner: AiExecutorRunnerRecord) => {
    setRotatingRunner(runner);
  };

  const downloadRunnerInstallPackage = async (runner: AiExecutorRunnerRecord) => {
    try {
      const { blob, filename } = await downloadAiExecutorRunnerInstallPackage(
        runner.id,
        runnerPackageOptionsFromMetadata(runner.metadata),
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      message.success('Runner 安装包已生成');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Runner 安装包下载失败');
    }
  };

  const copyRunnerSetupCommand = async (command: string) => {
    try {
      await navigator.clipboard.writeText(command);
      message.success('启动命令已复制');
    } catch {
      message.error('启动命令复制失败');
    }
  };

  const submitRotateRunnerToken = async () => {
    if (!rotatingRunner) {
      return;
    }
    setRotatingRunnerLoading(true);
    try {
      const updatedRunner = await rotateAiExecutorRunnerToken(rotatingRunner.id);
      message.success('Runner Token 已轮换');
      setRotatingRunner(undefined);
      if (updatedRunner.runner_token) {
        setRotatedRunnerToken(updatedRunner.runner_token);
      }
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Runner Token 轮换失败');
    } finally {
      setRotatingRunnerLoading(false);
    }
  };

  const openRunnerLogs = async (runner: AiExecutorRunnerRecord) => {
    const taskId = latestRunnerTaskId(runner);
    if (!taskId) {
      message.warning('当前执行器暂无可查看的任务日志');
      return;
    }
    setRunnerLogModalOpen(true);
    setRunnerLogLoading(true);
    try {
      const result = await fetchAiExecutorTaskLogs(taskId);
      setRunnerLogTask(result.task);
      setRunnerLogRows(result.logs ?? []);
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Runner 执行日志加载失败');
    } finally {
      setRunnerLogLoading(false);
    }
  };

  const cancelRunnerTask = async () => {
    if (!runnerLogTask?.id) {
      return;
    }
    setRunnerLogLoading(true);
    try {
      const result = await cancelAiExecutorTask(
        runnerLogTask.id,
        '管理员从插件管理页面取消 Runner 任务',
      );
      setRunnerLogTask(result.task);
      message.success('Runner 任务已取消');
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Runner 任务取消失败');
    } finally {
      setRunnerLogLoading(false);
    }
  };

  const warnDeleteUsage = (title: string, groups: DeleteUsageGroup[]) => {
    Modal.warning({
      content: deleteUsageContent(groups),
      okText: '知道了',
      title,
      width: 640,
    });
  };

  const pluginDeleteUsageGroups = (plugin: PluginRecord): DeleteUsageGroup[] => {
    const pluginConnections = connections.filter((connection) => connection.plugin_id === plugin.id);
    const pluginActions = actions.filter((action) => action.plugin_id === plugin.id);
    const connectionIds = new Set(pluginConnections.map((connection) => connection.id));
    const actionIds = new Set(pluginActions.map((action) => action.id));
    return [
      { items: pluginConnections.map(usageItemName), label: '连接' },
      { items: pluginActions.map(usageItemName), label: '动作' },
      {
        items: scheduledJobs
          .filter((job) => (
            actionIds.has(String(job.plugin_action_id ?? ''))
            || connectionIds.has(String(job.plugin_connection_id ?? ''))
          ))
          .map(usageItemName),
        label: '定时作业',
      },
    ];
  };

  const connectionDeleteUsageGroups = (connection: PluginConnectionRecord): DeleteUsageGroup[] => [
    {
      items: actions
        .filter((action) => action.connection_id === connection.id)
        .map(usageItemName),
      label: '动作',
    },
    {
      items: scheduledJobs
        .filter((job) => job.plugin_connection_id === connection.id)
        .map(usageItemName),
      label: '定时作业',
    },
  ];

  const actionDeleteUsageGroups = (action: PluginActionRecord): DeleteUsageGroup[] => [
    {
      items: scheduledJobs
        .filter((job) => job.plugin_action_id === action.id)
        .map(usageItemName),
      label: '定时作业',
    },
  ];

  const confirmDeletePlugin = (plugin: PluginRecord) => {
    if (plugin.is_system) {
      message.info('官方标准插件不能删除，请在连接里维护接入参数');
      return;
    }
    const usageGroups = pluginDeleteUsageGroups(plugin);
    if (hasDeleteUsage(usageGroups)) {
      warnDeleteUsage(`插件「${plugin.name}」正在使用中`, usageGroups);
      return;
    }
    Modal.confirm({
      cancelText: '取消',
      content: `确定删除插件「${plugin.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      title: '删除插件',
      onOk: async () => {
        try {
          await deletePlugin(plugin.id);
          message.success('插件已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '插件删除失败');
        }
      },
    });
  };

  const confirmDeleteConnection = (connection: PluginConnectionRecord) => {
    const usageGroups = connectionDeleteUsageGroups(connection);
    if (hasDeleteUsage(usageGroups)) {
      warnDeleteUsage(`连接「${connection.name}」正在使用中`, usageGroups);
      return;
    }
    Modal.confirm({
      cancelText: '取消',
      content: `确定删除连接「${connection.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      title: '删除连接',
      onOk: async () => {
        try {
          await deletePluginConnection(connection.id);
          message.success('连接已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '连接删除失败');
        }
      },
    });
  };

  const confirmDeleteAction = (action: PluginActionRecord) => {
    const usageGroups = actionDeleteUsageGroups(action);
    if (hasDeleteUsage(usageGroups)) {
      warnDeleteUsage(`动作「${action.name}」正在使用中`, usageGroups);
      return;
    }
    Modal.confirm({
      cancelText: '取消',
      content: `确定删除动作「${action.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      title: '删除动作',
      onOk: async () => {
        try {
          await deletePluginAction(action.id);
          message.success('动作已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '动作删除失败');
        }
      },
    });
  };

  const openCreateConnectionModal = useCallback(() => {
    setEditingConnection(undefined);
    setAssistantConnectionDraftSource(undefined);
    setAdvancedConnectionJsonOpen(false);
    setAdvancedConnectionRequestJsonOpen(false);
    connectionForm.resetFields();
    const defaultPlugin = plugins[0];
    const defaults = connectionDefaultsForPlugin(defaultPlugin);
    connectionForm.setFieldsValue({
      auth_type: 'none',
      environment: 'default',
      max_retries: 0,
      plugin_id: defaultPlugin?.id,
      status: 'active',
      timeout_seconds: 30,
      ...defaults,
    });
    setConnectionModalOpen(true);
  }, [connectionDefaultsForPlugin, connectionForm, plugins]);

  const openCreateConnectionForPlugin = (pluginId?: string | null) => {
    setEditingConnection(undefined);
    setAssistantConnectionDraftSource(undefined);
    setAdvancedConnectionJsonOpen(false);
    setAdvancedConnectionRequestJsonOpen(false);
    connectionForm.resetFields();
    const plugin = pluginId ? pluginById.get(pluginId) : undefined;
    const defaults = connectionDefaultsForPlugin(plugin);
    connectionForm.setFieldsValue({
      auth_type: 'none',
      environment: 'default',
      max_retries: 0,
      plugin_id: pluginId ?? undefined,
      status: 'active',
      timeout_seconds: 30,
      ...defaults,
      ...(plugin && !defaults?.name ? { name: `${plugin.name} 连接` } : {}),
    });
    setConnectionModalOpen(true);
  };

  const openEditConnectionModal = (connection: PluginConnectionRecord) => {
    const authConfig = connection.auth_config ?? {};
    const requestConfig = connection.request_config ?? {};
    const plugin = pluginById.get(connection.plugin_id);
    const schema = plugin
      ? marketplaceItemByPluginCode.get(plugin.code)?.connection_schema
        ?? marketplaceItemByPluginId.get(plugin.id)?.connection_schema
      : undefined;
    setEditingConnection(connection);
    setAssistantConnectionDraftSource(undefined);
    setAdvancedConnectionJsonOpen(false);
    setAdvancedConnectionRequestJsonOpen(false);
    connectionForm.resetFields();
    connectionForm.setFieldsValue({
      auth_config: stableJson(authConfig),
      auth_type: connection.auth_type ?? 'none',
      connection_header_rows: recordToRows(
        configSection(requestConfig, 'headers'),
        schemaManagedRequestKeys(schema, 'headers'),
      ),
      connection_param_rows: recordToRows(
        configSection(requestConfig, 'query'),
        schemaManagedRequestKeys(schema, 'query'),
      ),
      endpoint_url: connection.endpoint_url,
      environment: connection.environment ?? 'default',
      header_name: typeof authConfig.header_name === 'string' ? authConfig.header_name : undefined,
      max_retries: connection.max_retries ?? 0,
      name: connection.name,
      password_ref: typeof authConfig.password_ref === 'string' ? authConfig.password_ref : undefined,
      plugin_id: connection.plugin_id,
      request_config: stableJson(requestConfig),
      schema_values: schemaValuesFromPayload(connection, schema),
      secret_ref: typeof authConfig.secret_ref === 'string' ? authConfig.secret_ref : undefined,
      status: connection.status,
      timeout_seconds: connection.timeout_seconds ?? 30,
      token_ref: typeof authConfig.token_ref === 'string' ? authConfig.token_ref : undefined,
      username_ref: typeof authConfig.username_ref === 'string' ? authConfig.username_ref : undefined,
    });
    setConnectionModalOpen(true);
  };

  const closeConnectionModal = () => {
    setConnectionModalOpen(false);
    setEditingConnection(undefined);
    setAssistantConnectionDraftSource(undefined);
    setAdvancedConnectionJsonOpen(false);
    setAdvancedConnectionRequestJsonOpen(false);
    connectionForm.resetFields();
  };

  const applyConnectionPluginDefaults = (pluginId: string) => {
    const plugin = pluginById.get(pluginId);
    const defaults = connectionDefaultsForPlugin(plugin);
    const schema = plugin
      ? marketplaceItemByPluginCode.get(plugin.code)?.connection_schema
        ?? marketplaceItemByPluginId.get(plugin.id)?.connection_schema
      : undefined;
    if (!defaults) {
      return;
    }
    const nextValues: Partial<ConnectionFormValues> = {
      header_name: undefined,
      password_ref: undefined,
      plugin_id: pluginId,
      schema_values: {},
      secret_ref: undefined,
      token_ref: undefined,
      username_ref: undefined,
      ...defaults,
    };
    const mergedValues = {
      ...connectionForm.getFieldsValue(),
      ...nextValues,
    };
    if (advancedConnectionJsonOpen) {
      nextValues.auth_config = stableJson(buildConnectionAuthConfig(mergedValues));
    }
    if (advancedConnectionRequestJsonOpen) {
      nextValues.request_config = stableJson(buildConnectionRequestConfig(mergedValues, schema));
    }
    connectionForm.setFieldsValue(nextValues);
  };

  const submitConnection = async (options: { testAfterSave?: boolean } = {}) => {
    try {
      setConnectionSubmitAction(options.testAfterSave ? 'save-test' : 'save');
      const values = await connectionForm.validateFields();
      const authConfig = advancedConnectionJsonOpen
        ? parseJsonObject(values.auth_config, '认证配置')
        : buildConnectionAuthConfig(values);
      if (selectedConnectionIsGithub) {
        const tokenRef = typeof authConfig.token_ref === 'string' ? authConfig.token_ref.trim() : '';
        if (values.auth_type !== 'bearer' || !tokenRef) {
          throw new Error('GitHub 连接必须填写 Token 或密钥引用');
        }
      }
      const requestConfig = advancedConnectionRequestJsonOpen
        ? parseJsonObject(values.request_config, '请求配置')
        : buildConnectionRequestConfig(values, selectedConnectionSchema);
      const payload = buildConnectionPayload(values, authConfig, requestConfig, selectedConnectionSchema);
      let savedConnection: PluginConnectionRecord;
      if (editingConnection) {
        const updatedConnection = await updatePluginConnection(editingConnection.id, payload);
        savedConnection = {
          ...editingConnection,
          ...payload,
          ...updatedConnection,
          id: updatedConnection.id ?? editingConnection.id,
          name: updatedConnection.name ?? payload.name ?? editingConnection.name,
          plugin_id: updatedConnection.plugin_id ?? payload.plugin_id ?? editingConnection.plugin_id,
          endpoint_url: updatedConnection.endpoint_url ?? payload.endpoint_url ?? editingConnection.endpoint_url,
          status: updatedConnection.status ?? payload.status ?? editingConnection.status,
        };
        message.success('连接已更新');
      } else {
        const createdConnection = await createPluginConnection(payload);
        savedConnection = {
          ...payload,
          ...createdConnection,
          id: createdConnection.id,
          name: createdConnection.name ?? payload.name ?? values.name,
          plugin_id: createdConnection.plugin_id ?? payload.plugin_id ?? values.plugin_id,
          endpoint_url: createdConnection.endpoint_url ?? payload.endpoint_url ?? values.endpoint_url,
          status: createdConnection.status ?? payload.status ?? values.status,
        };
        rememberAssistantDraftResolution({
          draftId: assistantConnectionDraftSource?.draftId,
          resourceId: createdConnection.id,
          resourceType: 'plugin_connection',
          title: assistantConnectionDraftSource?.title,
        });
        message.success('连接已创建');
      }
      closeConnectionModal();
      await reload();
      if (options.testAfterSave) {
        await runConnectionTest(savedConnection);
      }
    } catch (error) {
      if (isFormValidationError(error)) {
        const firstField = error.errorFields[0]?.name;
        if (firstField) {
          connectionForm.scrollToField(firstField);
        }
        return;
      }
      message.error(error instanceof Error ? error.message : editingConnection ? '连接更新失败' : '连接创建失败');
    } finally {
      setConnectionSubmitAction(undefined);
    }
  };

  const submitAction = async () => {
    try {
      const values = await actionForm.validateFields();
      const requestConfig =
        values.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO && !advancedActionJsonOpen
          ? buildMaxComputeRequestConfig(values)
          : advancedActionJsonOpen
            ? parseJsonObject(values.request_config, '请求配置')
            : buildVisualRequestConfig(values);
      const resultMapping = advancedActionJsonOpen
        ? mergeWriteTarget(parseJsonObject(values.result_mapping, '结果映射'), values.write_target)
        : buildVisualResultMapping(values, resultWriteTargets);
      const payload = buildActionPayload(values, requestConfig, resultMapping);
      if (editingAction) {
        await updatePluginAction(editingAction.id, payload);
        message.success('动作已更新');
      } else {
        const createdAction = await createPluginAction(payload);
        rememberAssistantDraftResolution({
          draftId: assistantActionDraftSource?.draftId,
          resourceId: createdAction.id,
          resourceType: 'plugin_action',
          title: assistantActionDraftSource?.title,
        });
        message.success('动作已创建');
      }
      closeActionModal();
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : editingAction ? '动作更新失败' : '动作创建失败');
    }
  };

  const openCreateActionModal = useCallback(() => {
    setEditingAction(undefined);
    setAssistantActionDraftSource(undefined);
    setActionScenario(undefined);
    setAdvancedActionJsonOpen(false);
    actionForm.resetFields();
    const defaultResultMapping = defaultResultMappingForWriteTarget(DEFAULT_RESULT_WRITE_TARGET, resultWriteTargets);
    actionForm.setFieldsValue({
      action_type: 'http_request',
      method: 'GET',
      requires_human_review: false,
      result_mapping: stableJson(defaultResultMapping),
      status: 'active',
      ...resultMappingVisualFields(defaultResultMapping, resultWriteTargets),
    });
    setActionModalOpen(true);
  }, [actionForm, resultWriteTargets]);

  const marketplaceActionScenario = (item: PluginMarketplaceItem) => {
    const template = actionTemplates.find((candidate) => candidate.plugin_code === item.code);
    if (template) {
      return template.code;
    }
    return undefined;
  };

  const openCreateActionForMarketplacePlugin = (item: PluginMarketplaceItem) => {
    const scenario = marketplaceActionScenario(item);
    if (!scenario) {
      message.warning('动作模板目录未返回该官方插件模板，请刷新服务端模板目录后重试');
      return;
    }
    openCreateActionModal();
    applyActionScenario(scenario);
  };

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      const rawDraft = window.sessionStorage.getItem(ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY);
      if (!rawDraft) {
        return;
      }
      window.sessionStorage.removeItem(ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY);
      try {
        const draft = JSON.parse(rawDraft) as AssistantPluginConnectionDraft;
        if (!isPlainRecord(draft.payload)) {
          return;
        }
        openCreateConnectionModal();
        setAssistantConnectionDraftSource({ draftId: draft.draftId, title: draft.title });
        const pluginId = stringValue(draft.payload.plugin_id);
        const plugin = pluginId ? pluginById.get(pluginId) : undefined;
        const schema = plugin
          ? marketplaceItemByPluginCode.get(plugin.code)?.connection_schema
            ?? marketplaceItemByPluginId.get(plugin.id)?.connection_schema
          : undefined;
        connectionForm.setFieldsValue(pluginConnectionDraftFormValues(draft.payload, schema));
        message.success(`已应用助手草案：${draft.title || '插件连接'}`);
      } catch (error) {
        message.error(error instanceof Error ? error.message : '助手插件连接草案解析失败');
      }
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [
    connectionForm,
    marketplaceItemByPluginCode,
    marketplaceItemByPluginId,
    openCreateConnectionModal,
    pluginById,
  ]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (!window.sessionStorage.getItem(ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY) || resultWriteTargets.length === 0) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      const rawDraft = window.sessionStorage.getItem(ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY);
      if (!rawDraft) {
        return;
      }
      window.sessionStorage.removeItem(ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY);
      try {
        const draft = JSON.parse(rawDraft) as AssistantPluginActionDraft;
        if (!isPlainRecord(draft.payload)) {
          return;
        }
        openCreateActionModal();
        setAssistantActionDraftSource({ draftId: draft.draftId, title: draft.title });
        actionForm.setFieldsValue(pluginActionDraftFormValues(draft.payload, resultWriteTargets));
        message.success(`已应用助手草案：${draft.title || '动作'}`);
      } catch (error) {
        message.error(error instanceof Error ? error.message : '助手动作草案解析失败');
      }
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [actionForm, openCreateActionModal, resultWriteTargets]);

  const openEditActionModal = (action: PluginActionRecord) => {
    const requestConfig = action.request_config ?? {};
    const resultMapping = action.result_mapping ?? {};
    const isMaxComputeAction = requestConfig.tool_name === 'maxcompute.execute_sql';
    const scenario = isMaxComputeAction
      ? MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO
      : actionScenarioForExistingAction(action, actionTemplates, plugins);
    setEditingAction(action);
    setAssistantActionDraftSource(undefined);
    setActionScenario(scenario);
    setAdvancedActionJsonOpen(!isMaxComputeAction && action.action_type === 'mcp_tool');
    actionForm.resetFields();
    actionForm.setFieldsValue({
      action_type: action.action_type,
      code: action.code,
      connection_id: action.connection_id ?? undefined,
      description: action.description ?? undefined,
      header_rows: recordToRows(configSection(requestConfig, 'headers')),
      max_rows: typeof requestConfig.limit === 'number' ? requestConfig.limit : undefined,
      method: typeof requestConfig.method === 'string' ? requestConfig.method : 'GET',
      name: action.name,
      param_rows: recordToRows(configSection(requestConfig, 'query')),
      path: typeof requestConfig.path === 'string' ? requestConfig.path : undefined,
      plugin_id: action.plugin_id,
      request_config: stableJson(requestConfig),
      requires_human_review: action.requires_human_review,
      result_mapping: stableJson(resultMapping),
      returned_fields: Array.isArray(requestConfig.fields)
        ? requestConfig.fields.join(',')
        : undefined,
      scenario,
      status: action.status,
      table_name: typeof requestConfig.table === 'string' ? requestConfig.table : undefined,
      time_field: typeof requestConfig.time_field === 'string' ? requestConfig.time_field : undefined,
      ...resultMappingVisualFields(resultMapping, resultWriteTargets),
    });
    setActionModalOpen(true);
  };

  const closeActionModal = () => {
    setActionModalOpen(false);
    setEditingAction(undefined);
    setAssistantActionDraftSource(undefined);
    setActionScenario(undefined);
    setAdvancedActionJsonOpen(false);
    actionForm.resetFields();
  };

  const applyActionScenario = (scenario?: string) => {
    setActionScenario(scenario);
    const pluginByCode = (code: string) => plugins.find((plugin) => plugin.code === code);
    const connectionForPlugin = (pluginId?: string) =>
      pluginId ? connections.find((connection) => connection.plugin_id === pluginId)?.id : undefined;
    const template = actionTemplates.find((item) => item.code === scenario);
    if (template) {
      const plugin = pluginByCode(template.plugin_code) ?? plugins.find((item) => item.id === template.plugin_id);
      const requestConfig = isPlainRecord(template.request_config) ? template.request_config : {};
      const resultMapping = isPlainRecord(template.result_mapping)
        ? template.result_mapping
        : defaultResultMappingForWriteTarget(DEFAULT_RESULT_WRITE_TARGET, resultWriteTargets);
      const formDefaults = isPlainRecord(template.form_defaults) ? template.form_defaults : {};
      const isMaxComputeTemplate = template.code === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO;
      const tableName = stringValue(
        formDefaults.table_name,
        stringValue(requestConfig.table, 'ods_user_feedback'),
      );
      const timeField = stringValue(
        formDefaults.time_field,
        stringValue(requestConfig.time_field, 'created_at'),
      );
      const returnedFields = stringValue(
        formDefaults.returned_fields,
        Array.isArray(requestConfig.fields)
          ? requestConfig.fields.map(String).join(',')
          : MAXCOMPUTE_DEFAULT_FIELDS,
      );
      const maxRows = numberValue(formDefaults.max_rows, numberValue(requestConfig.limit, 1000));
      const templatePluginId = stringValue(template.plugin_id) || undefined;
      const pluginId = plugin?.id ?? templatePluginId ?? (
        isMaxComputeTemplate && plugins.length === 1 ? plugins[0].id : undefined
      );
      const nextValues: Partial<ActionFormValues> = {
        action_type: stringValue(template.action_type, 'http_request'),
        code: stringValue(template.default_code, template.code),
        connection_id: connectionForPlugin(pluginId)
          ?? (isMaxComputeTemplate && connections.length === 1 ? connections[0].id : undefined),
        header_rows: recordToRows(requestConfig.headers),
        max_rows: maxRows,
        method: stringValue(requestConfig.method, 'GET'),
        name: stringValue(template.default_name, template.name),
        param_rows: recordToRows(requestConfig.query),
        path: stringValue(requestConfig.path) || undefined,
        plugin_id: pluginId,
        request_config: stableJson(requestConfig),
        result_mapping: stableJson(resultMapping),
        returned_fields: returnedFields,
        table_name: tableName,
        time_field: timeField,
        ...resultMappingVisualFields(resultMapping, resultWriteTargets),
      };
      actionForm.setFieldsValue(nextValues);
      return;
    }
    if (scenario) {
      message.warning('动作模板目录未返回该场景，请刷新后重试');
    }
  };

  const applyWriteTargetDefaults = (writeTarget?: string) => {
    const resultMapping = defaultResultMappingForWriteTarget(writeTarget, resultWriteTargets);
    actionForm.setFieldsValue({
      result_mapping: stableJson(resultMapping),
      ...resultMappingVisualFields(resultMapping, resultWriteTargets),
    });
  };

  const toggleAdvancedActionJson = () => {
    const nextOpen = !advancedActionJsonOpen;
    if (nextOpen) {
      syncActionJsonFromVisual();
    }
    setAdvancedActionJsonOpen(nextOpen);
  };

  const syncActionJsonFromVisual = () => {
    const values = actionForm.getFieldsValue();
    const requestConfig =
      values.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO
        ? buildMaxComputeRequestConfig(values)
        : buildVisualRequestConfig(values);
    actionForm.setFieldsValue({
      request_config: stableJson(requestConfig),
      result_mapping: stableJson(buildVisualResultMapping(values, resultWriteTargets)),
    });
  };

  const applyActionJsonToVisual = () => {
    try {
      const config = parseJsonObject(actionForm.getFieldValue('request_config'), '请求配置');
      const resultMapping = parseJsonObject(actionForm.getFieldValue('result_mapping'), '结果映射');
      actionForm.setFieldsValue({
        header_rows: recordToRows(config.headers),
        method: typeof config.method === 'string' ? config.method : 'GET',
        param_rows: recordToRows(config.query),
        path: typeof config.path === 'string' ? config.path : undefined,
        ...resultMappingVisualFields(resultMapping, resultWriteTargets),
      });
      message.success('已从 JSON 同步到可视化字段');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'JSON 解析失败');
    }
  };

  const toggleAdvancedConnectionJson = () => {
    const nextOpen = !advancedConnectionJsonOpen;
    if (nextOpen) {
      const values = connectionForm.getFieldsValue();
      connectionForm.setFieldsValue({
        auth_config: values.auth_config?.trim()
          ? values.auth_config
          : stableJson(buildConnectionAuthConfig(values)),
      });
    }
    setAdvancedConnectionJsonOpen(nextOpen);
  };

  const syncConnectionRequestJsonFromVisual = () => {
    const values = connectionForm.getFieldsValue();
    connectionForm.setFieldValue('request_config', stableJson(buildConnectionRequestConfig(values, selectedConnectionSchema)));
  };

  const toggleAdvancedConnectionRequestJson = () => {
    const nextOpen = !advancedConnectionRequestJsonOpen;
    if (nextOpen) {
      syncConnectionRequestJsonFromVisual();
    }
    setAdvancedConnectionRequestJsonOpen(nextOpen);
  };

  const applyConnectionJsonToVisual = () => {
    try {
      const config = parseJsonObject(connectionForm.getFieldValue('auth_config'), '认证配置');
      connectionForm.setFieldsValue({
        header_name: typeof config.header_name === 'string' ? config.header_name : undefined,
        password_ref: typeof config.password_ref === 'string' ? config.password_ref : undefined,
        secret_ref: typeof config.secret_ref === 'string' ? config.secret_ref : undefined,
        token_ref: typeof config.token_ref === 'string' ? config.token_ref : undefined,
        username_ref: typeof config.username_ref === 'string' ? config.username_ref : undefined,
      });
      message.success('已从认证 JSON 同步到可视化字段');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'JSON 解析失败');
    }
  };

  const applyConnectionRequestJsonToVisual = () => {
    try {
      const config = parseJsonObject(connectionForm.getFieldValue('request_config'), '请求配置');
      connectionForm.setFieldsValue({
        connection_header_rows: recordToRows(
          config.headers,
          schemaManagedRequestKeys(selectedConnectionSchema, 'headers'),
        ),
        connection_param_rows: recordToRows(
          config.query,
          schemaManagedRequestKeys(selectedConnectionSchema, 'query'),
        ),
        schema_values: schemaValuesFromPayload({ request_config: config }, selectedConnectionSchema),
      });
      message.success('已从请求 JSON 同步到 Params / Headers');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'JSON 解析失败');
    }
  };

  const runAction = async (action: PluginActionRecord) => {
    await invokePluginAction(action.id);
    message.success('动作运行已完成');
    await reload();
  };

  const openActionFromConnectionTest = (
    connection: PluginConnectionRecord,
    result: PluginConnectionTestResult,
  ) => {
    const draft = result.action_template_draft;
    if (!draft) {
      message.warning('当前测试结果缺少动作模板草案');
      return;
    }
    Modal.destroyAll();
    setEditingAction(undefined);
    setAssistantActionDraftSource(undefined);
    setActionScenario(undefined);
    setAdvancedActionJsonOpen(false);
    actionForm.resetFields();
    actionForm.setFieldsValue(pluginActionDraftFormValues({
      ...draft,
      connection_id: draft.connection_id ?? connection.id,
      plugin_id: draft.plugin_id ?? connection.plugin_id,
    } as Record<string, unknown>, resultWriteTargets));
    setActionModalOpen(true);
  };

  const updateConnectionAfterTest = (
    connection: PluginConnectionRecord,
    result: PluginConnectionTestResult,
  ) => {
    setConnections((currentConnections) =>
      currentConnections.map((item) =>
        item.id === connection.id
          ? {
              ...item,
              last_test_summary: {
                checked_at: result.checked_at,
                error_code: result.error_code,
                error_message: result.error_message,
                failed_step: result.diagnostics?.find((step) => step.status === 'failed')?.name,
                latency_ms: result.latency_ms,
                mocked: result.mocked,
                response_status_code: typeof result.response_summary?.status_code === 'number'
                  ? result.response_summary.status_code
                  : null,
                status: result.status,
              },
              test_history: result.test_history ?? item.test_history,
            }
          : item,
      ),
    );
  };

  const runConnectionTest = async (connection: PluginConnectionRecord) => {
    if (testingConnectionId) {
      return;
    }
    const messageKey = `plugin-connection-test-${connection.id}`;
    setTestingConnectionId(connection.id);
    message.loading({
      content: `正在测试连接「${connection.name}」，请稍候...`,
      duration: 0,
      key: messageKey,
    });
    try {
      const result = await testPluginConnection(connection.id);
      updateConnectionAfterTest(connection, result);
      const requestSummary = result.request_summary ?? {};
      const placeholderHeaders = Array.isArray(requestSummary.masked_placeholder_headers)
        ? requestSummary.masked_placeholder_headers.map(String)
        : [];
      Modal.info({
        content: (
          <Space orientation="vertical" size={10} style={{ width: '100%' }}>
            <div>状态：<Tag color={result.status === 'succeeded' ? 'green' : 'red'}>{result.status}</Tag>耗时：{result.latency_ms}ms</div>
            {placeholderHeaders.length > 0 ? (
              <Alert
                description={`最终请求仍包含脱敏占位：${placeholderHeaders.join('、')}。请重新填写真实 Header 值，或改用认证配置字段维护 Authorization。`}
                showIcon
                title="Authorization 等敏感 Header 不能使用 *** 占位发起请求"
                type="error"
              />
            ) : null}
            {result.error_message ? (
              <Alert description={result.error_message} showIcon title="错误信息" type="error" />
            ) : null}
            <Table
              columns={[
                { dataIndex: 'name', title: '检查项', width: 190 },
                { dataIndex: 'status', title: '状态', width: 130, render: (value: string) => <Tag>{value}</Tag> },
                {
                  dataIndex: 'detail',
                  title: '说明',
                  render: (value?: string) => (
                    <Typography.Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {value ?? '-'}
                    </Typography.Text>
                  ),
                },
                { dataIndex: 'latency_ms', title: '耗时 ms', width: 100, render: (value?: number) => value ?? '-' },
              ]}
              dataSource={result.diagnostics ?? []}
              pagination={false}
              rowKey="name"
              scroll={{ x: 920 }}
              size="small"
            />
            <ConnectionRequestDebugPanel
              repairSuggestions={result.repair_suggestions}
              requestSummary={requestSummary}
              testHistory={result.test_history}
              onCopyAsActionTemplate={() => openActionFromConnectionTest(connection, result)}
            />
            <JsonDiagnosticsBlock title="远端响应信息" value={result.response_summary} />
          </Space>
        ),
        title: '连接测试诊断',
        width: 980,
      });
      if (result.status === 'succeeded') {
        message.success({
          content: `连接测试成功，耗时 ${result.latency_ms}ms`,
          duration: 3,
          key: messageKey,
        });
      } else {
        message.error({
          content: result.error_message || '连接测试失败',
          duration: 5,
          key: messageKey,
        });
      }
    } catch (error) {
      message.error({
        content: error instanceof Error ? error.message : '连接测试失败',
        duration: 5,
        key: messageKey,
      });
    } finally {
      setTestingConnectionId(undefined);
    }
  };

  const openRunnerTestDiagnostics = (
    runner: AiExecutorRunnerRecord,
    result: AiExecutorRunnerTestResult,
  ) => {
    const resultRunner = result.runner ?? runner;
    Modal.info({
      content: (
        <Space orientation="vertical" size={10} style={{ width: '100%' }}>
          <Space size={8} wrap>
            <Typography.Text strong>{resultRunner.name ?? runner.name}</Typography.Text>
            <Tag color={connectionTestStatusColor(result.status)}>{result.status}</Tag>
            {result.health_status ? (
              <Tag color={runnerHealthStatusColor(result.health_status)}>{result.health_status}</Tag>
            ) : null}
            <Typography.Text type="secondary">
              耗时 {result.latency_ms ?? '-'}ms
            </Typography.Text>
            {result.checked_at ? (
              <Typography.Text type="secondary">
                检测时间 {result.checked_at}
              </Typography.Text>
            ) : null}
          </Space>
          <Table
            columns={[
              { dataIndex: 'name', title: '检查项', width: 190 },
              {
                dataIndex: 'status',
                title: '状态',
                width: 120,
                render: (value: string) => <Tag color={connectionTestStatusColor(value)}>{value}</Tag>,
              },
              {
                dataIndex: 'detail',
                title: '说明',
                render: (value?: string | null) => (
                  <Typography.Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {value ?? '-'}
                  </Typography.Text>
                ),
              },
              { dataIndex: 'latency_ms', title: '耗时 ms', width: 100, render: (value?: number | null) => value ?? '-' },
            ]}
            dataSource={result.diagnostics ?? []}
            pagination={false}
            rowKey="name"
            scroll={{ x: 760 }}
            size="small"
          />
        </Space>
      ),
      title: '执行器测试诊断',
      width: 820,
    });
  };

  const runRunnerTest = async (runner: AiExecutorRunnerRecord) => {
    if (testingRunnerId) {
      return;
    }
    const messageKey = `ai-executor-runner-test-${runner.id}`;
    setTestingRunnerId(runner.id);
    message.loading({
      content: `正在测试执行器「${runner.name}」，请稍候...`,
      duration: 0,
      key: messageKey,
    });
    try {
      const result = await testAiExecutorRunner(runner.id);
      openRunnerTestDiagnostics(runner, result);
      if (result.status === 'succeeded') {
        message.success({
          content: `执行器测试通过，耗时 ${result.latency_ms ?? '-'}ms`,
          duration: 3,
          key: messageKey,
        });
      } else {
        message.error({
          content: '执行器测试未通过，请查看诊断详情',
          duration: 5,
          key: messageKey,
        });
      }
    } catch (error) {
      message.error({
        content: error instanceof Error ? error.message : '执行器测试失败',
        duration: 5,
        key: messageKey,
      });
    } finally {
      setTestingRunnerId(undefined);
    }
  };

  const openTrialModal = (action: PluginActionRecord) => {
    setTrialAction(action);
    setTrialConnectionId(action.connection_id ?? undefined);
    setTrialInputJson('{}');
    setTrialResult(undefined);
    setTrialModalOpen(true);
  };

  const runActionTrial = async () => {
    if (!trialAction) {
      return;
    }
    try {
      setTrialRunning(true);
      const parsedInput = parseJsonObject(trialInputJson, '试运行输入');
      const result = await trialPluginAction(trialAction.id, {
        connection_id: trialConnectionId,
        input_payload: parsedInput,
      });
      setTrialResult(result);
      if (result.status === 'succeeded') {
        message.success('试运行完成');
      } else {
        message.error(result.error_message || '试运行失败');
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '试运行失败');
    } finally {
      setTrialRunning(false);
    }
  };

  return (
    <PageContainer title="插件管理">
      <Space orientation="vertical" size={12} style={{ width: '100%', marginBottom: 16 }}>
        <Alert
          title={
            <Space wrap>
              <Typography.Text strong>系统变量预览</Typography.Text>
              <Tag color="blue">Timezone: {systemVariableTimezone}</Tag>
            </Space>
          }
          description={
            <Space orientation="vertical" size={10} style={{ display: 'flex', width: '100%' }}>
              <Space wrap size={[8, 8]}>
                <Typography.Text type="secondary">常用变量</Typography.Text>
                {compactSystemVariablePreviewItems.map((item) => (
                  <Tag key={item.expression}>
                    {item.label}：{item.expression} = {item.value}
                  </Tag>
                ))}
                <Button onClick={() => setSystemVariableModalOpen(true)} size="small" type="link">
                  查看全部变量
                </Button>
              </Space>
              <Typography.Text type="secondary">
                可复制表达式到连接 Params、Headers 或动作参数值，支持类似 {'{{current_date-7}}'} 的天数偏移。
              </Typography.Text>
            </Space>
          }
          showIcon
          type="info"
        />
        <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12 }}>
          <Typography.Text strong>通用调用链路</Typography.Text>
          <Space orientation="vertical" size={8} style={{ display: 'flex', marginTop: 10 }}>
            <Space wrap>
              {genericIntegrationChainSteps.map((step, index) => (
                <Fragment key={step.label}>
                  {index > 0 ? <Typography.Text type="secondary">→</Typography.Text> : null}
                  <Tag color={step.color}>
                    {step.label}：{step.text}
                  </Tag>
                </Fragment>
              ))}
            </Space>
            <Typography.Text type="secondary">
              适用于 MaxCompute、GitHub、GitLab、邮箱和自定义 HTTP/MCP 集成场景。
            </Typography.Text>
          </Space>
        </div>
      </Space>
      {systemVariableModalOpen ? (
        <Modal
          footer={null}
          onCancel={() => setSystemVariableModalOpen(false)}
          open={systemVariableModalOpen}
          title="全部系统变量"
          width={920}
        >
          <Space orientation="vertical" size={12} style={{ display: 'flex' }}>
            <Typography.Text type="secondary">
              解析时区：{systemVariableTimezone}。表达式和值都可以复制，保存配置时保留表达式，运行时再按时区解析。
            </Typography.Text>
            <Table<PluginSystemVariableRecord>
              columns={systemVariablePreviewColumns}
              dataSource={systemVariablePreviewItems}
              pagination={false}
              rowKey="expression"
              scroll={{ x: 720 }}
              size="small"
            />
          </Space>
        </Modal>
      ) : null}
      <Tabs
        defaultActiveKey="plugins"
        items={[
          {
            key: 'marketplace',
            label: '插件市场',
            children: (
              <ProTable<PluginMarketplaceItem>
                cardBordered
                className="management-list-table"
                dateFormatter="string"
                headerTitle="官方插件市场"
                loading={loading}
                options={{
                  density: true,
                  fullScreen: true,
                  reload,
                  setting: true,
                }}
                pagination={{
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`,
                }}
                rowKey="id"
                scroll={{ x: 1720 }}
                search={false}
                dataSource={marketplaceItems}
                tableLayout="fixed"
                expandable={{
                  expandedRowRender: (record) => (
                    <Space orientation="vertical" size={8} style={{ width: '100%' }}>
                      <Typography.Text strong>连接表单 schema</Typography.Text>
                      <MarketplaceConnectionSchemaDetail item={record} />
                    </Space>
                  ),
                }}
                columns={[
                  {
                    dataIndex: 'name',
                    title: '插件',
                    ellipsis: true,
                    width: 220,
                    render: (_, row) => (
                      <Space orientation="vertical" size={2}>
                        <Space wrap={false}>
                          <Typography.Text ellipsis style={{ maxWidth: 140 }}>
                            {row.name}
                          </Typography.Text>
                          <Tag color="blue">{OFFICIAL_PLUGIN_LABEL}</Tag>
                        </Space>
                        <Typography.Text type="secondary">{row.publisher ?? 'AI Brain 官方'}</Typography.Text>
                      </Space>
                    ),
                  },
                  {
                    dataIndex: 'category',
                    title: '分类',
                    width: 150,
                    render: (value) => pluginCategoryLabelByValue.get(String(value)) ?? String(value ?? '-'),
                  },
                  { dataIndex: 'protocol', title: '协议', width: 110 },
                  {
                    dataIndex: 'installed',
                    title: '状态',
                    width: 120,
                    render: (_, row) => (
                      <Tag color={row.installed ? 'green' : 'default'}>
                        {row.installed ? '已内置' : '未内置'}
                      </Tag>
                    ),
                  },
                  {
                    dataIndex: 'template_version',
                    title: '模板版本',
                    width: 120,
                    render: (_, row) => pluginVersionStatusTag(row),
                  },
                  {
                    dataIndex: 'summary',
                    title: '能力说明',
                    ellipsis: true,
                    width: 300,
                    render: (value) => value || '-',
                  },
                  {
                    dataIndex: 'recommended_scenarios',
                    title: '推荐场景',
                    width: 260,
                    render: (value) => (
                      <Space wrap size={4}>
                        {(Array.isArray(value) ? value : []).slice(0, 3).map((item) => (
                          <Tag key={String(item)}>{String(item)}</Tag>
                        ))}
                      </Space>
                    ),
                  },
                  {
                    dataIndex: 'action_templates',
                    title: '动作模板',
                    width: 230,
                    render: (value) => (
                      <Space wrap size={4}>
                        {(Array.isArray(value) ? value : []).slice(0, 2).map((item) => (
                          <Tag color="purple" key={String(item)}>{String(item)}</Tag>
                        ))}
                      </Space>
                    ),
                  },
                  {
                    dataIndex: 'connection_schema',
                    title: '连接表单字段',
                    width: 280,
                    render: (_, row) => <MarketplaceConnectionSchemaSummary item={row} />,
                  },
                  {
                    dataIndex: 'connection_count',
                    key: 'runtime',
                    title: '已配置',
                    width: 140,
                    render: (_, row) => (
                      <Space orientation="vertical" size={2}>
                        <Typography.Text>连接 {row.connection_count}</Typography.Text>
                        <Typography.Text>动作 {row.action_count}</Typography.Text>
                      </Space>
                    ),
                  },
                  {
                    dataIndex: 'plugin_id',
                    fixed: 'right',
                    key: 'actions',
                    title: '操作',
                    valueType: 'option',
                    width: 170,
                    render: (_, row) => {
                      return (
                        <Space orientation="vertical" size={2}>
                          <Button
                            aria-label={`配置市场插件 ${row.name}`}
                            disabled={!row.plugin_id}
                            icon={<PlusOutlined />}
                            onClick={() => openCreateConnectionForPlugin(row.plugin_id)}
                            type="link"
                          >
                            配置连接
                          </Button>
                          <Button
                            aria-label={`从市场插件 ${row.name} 创建动作`}
                            disabled={!row.plugin_id}
                            icon={<PlusOutlined />}
                            onClick={() => openCreateActionForMarketplacePlugin(row)}
                            type="link"
                          >
                            创建动作
                          </Button>
                        </Space>
                      );
                    },
                  },
                ]}
              />
            ),
          },
          {
            key: 'plugins',
            label: '插件',
            children: (
              <ProTable<PluginRecord>
                cardBordered
                className="management-list-table"
                dateFormatter="string"
                headerTitle="插件"
                loading={loading}
                options={{
                  density: true,
                  fullScreen: true,
                  reload,
                  setting: true,
                }}
                pagination={{
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`,
                }}
                rowKey="id"
                scroll={{ x: 1252 }}
                search={false}
                dataSource={plugins}
                tableLayout="fixed"
                toolBarRender={() => [
                  <Button key="create-plugin" aria-label="新增插件" icon={<PlusOutlined />} type="primary" onClick={openCreatePluginModal}>
                    新增插件
                  </Button>,
                  <Button key="reload-plugins" icon={<ReloadOutlined />} onClick={reload}>
                    刷新
                  </Button>,
                ]}
                columns={[
                  {
                    dataIndex: 'name',
                    title: '名称',
                    ellipsis: true,
                    width: 240,
                    render: (_, row) => (
                      <Space wrap={false}>
                        <Typography.Text ellipsis style={{ maxWidth: 150 }}>
                          {row.name}
                        </Typography.Text>
                        {row.is_system ? <Tag color="blue">{OFFICIAL_PLUGIN_LABEL}</Tag> : null}
                      </Space>
                    ),
                  },
                  { dataIndex: 'code', title: '编码', ellipsis: true, width: 200 },
                  { dataIndex: 'protocol', title: '协议', width: 120 },
                  {
                    dataIndex: 'template_version',
                    title: '模板版本',
                    width: 120,
                    render: (_, row) => pluginVersionStatusTag(row),
                  },
                  {
                    dataIndex: 'category',
                    title: '分类',
                    width: 150,
                    render: (value) => pluginCategoryLabelByValue.get(String(value)) ?? String(value ?? '-'),
                  },
                  { dataIndex: 'risk_level', title: '风险', width: 100 },
                  {
                    dataIndex: 'status',
                    title: '状态',
                    width: 110,
                    render: (value) => <Tag color={value === 'active' ? 'green' : 'default'}>{String(value)}</Tag>,
                  },
                  {
                    fixed: 'right',
                    key: 'actions',
                    title: '操作',
                    valueType: 'option',
                    width: 164,
                    render: (_, row) => {
                      if (row.is_system) {
                        return (
                          <Space className="management-row-actions" size={0}>
                            <Button
                              aria-label={`复制官方插件 ${row.name}`}
                              icon={<PlusOutlined />}
                              onClick={() => void copyOfficialPlugin(row)}
                              type="link"
                            >
                              复制
                            </Button>
                          </Space>
                        );
                      }
                      return (
                        <Space className="management-row-actions" size={0}>
                          <Button
                            aria-label={`编辑插件 ${row.name}`}
                            icon={<EditOutlined />}
                            onClick={() => openEditPluginModal(row)}
                            type="link"
                          >
                            编辑
                          </Button>
                          <Button
                            aria-label={`删除插件 ${row.name}`}
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => confirmDeletePlugin(row)}
                            type="link"
                          >
                            删除
                          </Button>
                        </Space>
                      );
                    },
                  },
                ]}
              />
            ),
          },
          {
            key: 'connections',
            label: '连接',
            children: (
              <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                <Space wrap>
                  <Typography.Text type="secondary">环境</Typography.Text>
                  <Select
                    allowClear
                    onChange={(value) => setConnectionEnvironmentFilter(value)}
                    options={connectionEnvironmentOptions}
                    placeholder="全部环境"
                    style={{ width: 160 }}
                    value={connectionEnvironmentFilter}
                  />
                  <Button
                    aria-label="新增连接"
                    htmlType="button"
                    icon={<PlusOutlined />}
                    type="primary"
                    onClick={openCreateConnectionModal}
                  >
                    新增连接
                  </Button>
                  <Button
                    htmlType="button"
                    icon={<ReloadOutlined />}
                    onClick={() => void reload()}
                  >
                    刷新
                  </Button>
                </Space>
                <ProTable<PluginConnectionRecord>
                  cardBordered
                  className="management-list-table"
                  dateFormatter="string"
                  headerTitle="连接"
                  loading={loading}
                  options={{
                    density: true,
                    fullScreen: true,
                    reload,
                    setting: true,
                  }}
                  pagination={{
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 条`,
                  }}
                  rowKey="id"
                  scroll={{ x: 1600 }}
                  search={false}
                  dataSource={connections}
                  tableLayout="fixed"
                  columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true, width: 220 },
                  {
                    dataIndex: 'plugin_id',
                    title: '插件',
                    ellipsis: true,
                    width: 220,
                    render: (value) => pluginById.get(String(value))?.name ?? value,
                  },
                  {
                    dataIndex: 'environment',
                    title: '环境',
                    width: 130,
                    render: (value) => connectionEnvironmentLabelByValue.get(String(value)) ?? String(value ?? '-'),
                  },
                  { dataIndex: 'auth_type', title: '认证', width: 130 },
                  { dataIndex: 'endpoint_url', title: 'Endpoint', ellipsis: true, width: 320 },
                  {
                    dataIndex: 'last_test_summary',
                    title: '最近测试',
                    width: 180,
                    render: (_, row) => <ConnectionLastTestSummary connection={row} />,
                  },
                  { dataIndex: 'status', title: '状态', width: 110 },
                  {
                    fixed: 'right',
                    key: 'actions',
                    title: '操作',
                    valueType: 'option',
                    width: 260,
                    render: (_, row) => {
                      const isTestingConnection = testingConnectionId === row.id;
                      return (
                        <Space className="management-row-actions" size={0}>
                          <Button
                            aria-label={`编辑连接 ${row.name}`}
                            disabled={Boolean(testingConnectionId)}
                            htmlType="button"
                            icon={<EditOutlined />}
                            onClick={() => openEditConnectionModal(row)}
                            type="link"
                          >
                            编辑
                          </Button>
                          <Button
                            aria-label={
                              isTestingConnection
                                ? `连接测试中 ${row.name}`
                                : `测试连接 ${row.name}`
                            }
                            disabled={Boolean(testingConnectionId)}
                            htmlType="button"
                            icon={<PlayCircleOutlined />}
                            loading={isTestingConnection}
                            onClick={() => runConnectionTest(row)}
                            type="link"
                          >
                            {isTestingConnection ? '测试中' : '测试'}
                          </Button>
                          <Button
                            aria-label={`删除连接 ${row.name}`}
                            danger
                            disabled={Boolean(testingConnectionId)}
                            htmlType="button"
                            icon={<DeleteOutlined />}
                            onClick={() => confirmDeleteConnection(row)}
                            type="link"
                          >
                            删除
                          </Button>
                        </Space>
                      );
                    },
                  },
                  ]}
                />
              </Space>
            ),
          },
          {
            key: 'runners',
            label: '执行器',
            children: (
              <ProTable<AiExecutorRunnerRecord>
                cardBordered
                className="management-list-table"
                dateFormatter="string"
                headerTitle="AI 执行器"
                loading={loading}
                options={{
                  density: true,
                  fullScreen: true,
                  reload,
                  setting: true,
                }}
                pagination={{
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`,
                }}
                rowKey="id"
                scroll={{ x: 1900 }}
                search={false}
                dataSource={runners}
                tableLayout="fixed"
                expandable={{
                  expandedRowRender: (record) => (
                    <Space orientation="vertical" size={8} style={{ width: '100%' }}>
                      <Typography.Text strong>
                        {isSystemDefaultRunner(record) ? '系统默认执行器说明' : '本地 Runner 启动命令'}
                      </Typography.Text>
                      {record.setup_command ? (
                        <Space size={8} wrap>
                          <code style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                            {String(record.setup_command)}
                          </code>
                          <Button
                            aria-label={`复制启动命令 ${record.name}`}
                            icon={<CopyOutlined />}
                            onClick={() => copyRunnerSetupCommand(String(record.setup_command))}
                            size="small"
                          >
                            复制
                          </Button>
                        </Space>
                      ) : (
                        <Typography.Text type="secondary">创建或刷新 Runner 后由后端生成启动命令。</Typography.Text>
                      )}
                    </Space>
                  ),
                }}
                toolBarRender={() => [
                  <Button key="create-runner" aria-label="新增执行器" icon={<PlusOutlined />} type="primary" onClick={openCreateRunnerModal}>
                    新增执行器
                  </Button>,
                  <Button key="reload-runners" icon={<ReloadOutlined />} onClick={reload}>
                    刷新
                  </Button>,
                ]}
                columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true, width: 220 },
                  { dataIndex: 'protocol', title: '协议', width: 150 },
                  {
                    dataIndex: 'health_status',
                    title: '健康状态',
                    width: 130,
                    render: (_, row) => (
                      <Space orientation="vertical" size={2}>
                        <Tag color={runnerHealthStatusColor(row.health_status)}>{row.health_status ?? 'unknown'}</Tag>
                        {typeof row.heartbeat_age_seconds === 'number' ? (
                          <Typography.Text type="secondary">{row.heartbeat_age_seconds}s</Typography.Text>
                        ) : null}
                      </Space>
                    ),
                  },
                  {
                    dataIndex: 'executor_types',
                    title: '执行器类型',
                    width: 240,
                    render: (value) => Array.isArray(value)
                      ? (
                        <Space wrap size={4}>
                          {value.map((item) => <Tag key={String(item)}>{aiExecutorTypeLabel(item)}</Tag>)}
                        </Space>
                      )
                      : '-',
                  },
                  {
                    dataIndex: 'workspace_roots',
                    title: '工作区白名单',
                    ellipsis: true,
                    width: 280,
                    render: (value) => Array.isArray(value) && value.length > 0 ? value.join(', ') : '*',
                  },
                  {
                    dataIndex: 'last_heartbeat_at',
                    title: '最后心跳',
                    ellipsis: true,
                    width: 220,
                    render: (value) => value || '-',
                  },
                  {
                    dataIndex: 'token_configured',
                    title: 'Token',
                    width: 220,
                    render: (value, row) => {
                      if (isSystemDefaultRunner(row)) {
                        return <Tag color="blue">系统托管</Tag>;
                      }
                      return (
                        <Space orientation="vertical" size={2}>
                          <Space size={6} wrap>
                            <Tag color={value ? 'green' : 'default'}>{value ? '已配置' : '未配置'}</Tag>
                            <Typography.Text>Token v{row.token_version ?? 1}</Typography.Text>
                          </Space>
                          <Typography.Text type="secondary">
                            {row.token_rotated_at ?? '未轮换'}
                          </Typography.Text>
                          {row.latest_task_id ? (
                            <Typography.Text type="secondary">
                              最近任务 {row.latest_task_status ?? '-'}
                            </Typography.Text>
                          ) : null}
                        </Space>
                      );
                    },
                  },
                  {
                    dataIndex: 'status',
                    title: '状态',
                    width: 110,
                    render: (value) => <Tag color={value === 'active' ? 'green' : value === 'offline' ? 'orange' : 'default'}>{String(value)}</Tag>,
                  },
                  {
                    dataIndex: 'setup_command',
                    title: '启动命令',
                    ellipsis: true,
                    width: 320,
                    render: (_, row) => {
                      const command = stringValue(row.setup_command);
                      if (!command) {
                        return '-';
                      }
                      return (
                        <Space size={6} wrap={false}>
                          <code style={{ wordBreak: 'break-all' }}>{command}</code>
                          <Button
                            aria-label={`复制启动命令 ${row.name}`}
                            icon={<CopyOutlined />}
                            onClick={() => copyRunnerSetupCommand(command)}
                            size="small"
                            type="text"
                          />
                        </Space>
                      );
                    },
                  },
                  {
                    fixed: 'right',
                    key: 'actions',
                    title: '操作',
                    valueType: 'option',
                    width: 360,
                    render: (_, row) => {
                      const testButton = (
                        <Button
                          aria-label={`测试执行器 ${row.name}`}
                          icon={<PlayCircleOutlined />}
                          loading={testingRunnerId === row.id}
                          onClick={() => runRunnerTest(row)}
                          type="link"
                        >
                          测试
                        </Button>
                      );
                      if (isSystemDefaultRunner(row)) {
                        return (
                          <Space className="management-row-actions" size={0}>
                            {testButton}
                            <Tag color="blue">系统内置</Tag>
                          </Space>
                        );
                      }
                      return (
                        <Space className="management-row-actions" size={0}>
                          {testButton}
                          <Button
                            aria-label={`轮换 Token ${row.name}`}
                            icon={<KeyOutlined />}
                            onClick={() => rotateRunnerToken(row)}
                            type="link"
                          >
                            轮换
                          </Button>
                          <Button
                            aria-label={`查看执行日志 ${row.name}`}
                            disabled={!latestRunnerTaskId(row)}
                            icon={<FileTextOutlined />}
                            onClick={() => openRunnerLogs(row)}
                            type="link"
                          >
                            日志
                          </Button>
                          <Button
                            aria-label={`下载安装包 ${row.name}`}
                            icon={<DownloadOutlined />}
                            onClick={() => downloadRunnerInstallPackage(row)}
                            type="link"
                          >
                            安装包
                          </Button>
                          <Button
                            aria-label={`编辑执行器 ${row.name}`}
                            icon={<EditOutlined />}
                            onClick={() => openEditRunnerModal(row)}
                            type="link"
                          >
                            编辑
                          </Button>
                          <Button
                            aria-label={`删除执行器 ${row.name}`}
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => confirmDeleteRunner(row)}
                            type="link"
                          >
                            删除
                          </Button>
                        </Space>
                      );
                    },
                  },
                ]}
              />
            ),
          },
          {
            key: 'actions',
            label: '动作',
            children: (
              <ProTable<PluginActionRecord>
                cardBordered
                className="management-list-table"
                dateFormatter="string"
                headerTitle="动作"
                loading={loading}
                options={{
                  density: true,
                  fullScreen: true,
                  reload,
                  setting: true,
                }}
                pagination={{
                  showSizeChanger: true,
                  showTotal: (total) => `共 ${total} 条`,
                }}
                rowKey="id"
                scroll={{ x: 1570 }}
                search={false}
                dataSource={actions}
                tableLayout="fixed"
                toolBarRender={() => [
                  <Button key="create-action" aria-label="新增动作" icon={<PlusOutlined />} type="primary" onClick={openCreateActionModal}>
                    新增动作
                  </Button>,
                  <Button key="reload-actions" icon={<ReloadOutlined />} onClick={reload}>
                    刷新
                  </Button>,
                ]}
                columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true, width: 220 },
                  { dataIndex: 'code', title: '编码', ellipsis: true, width: 200 },
                  { dataIndex: 'action_type', title: '类型', width: 130 },
                  {
                    dataIndex: 'plugin_id',
                    title: '插件',
                    ellipsis: true,
                    width: 200,
                    render: (value) => pluginById.get(String(value))?.name ?? value,
                  },
                  {
                    dataIndex: 'connection_id',
                    title: '连接',
                    ellipsis: true,
                    width: 200,
                    render: (value) => value ? connectionById.get(String(value))?.name ?? value : '-',
                  },
                  {
                    dataIndex: 'result_mapping',
                    title: '写入目标',
                    ellipsis: true,
                    width: 220,
                    render: (value) => {
                      const writeTarget = value && typeof value === 'object'
                        ? (value as unknown as Record<string, unknown>).write_target
                        : undefined;
                      return typeof writeTarget === 'string'
                        ? resultWriteTargetLabel(writeTarget, resultWriteTargets)
                        : resultWriteTargetLabel(DEFAULT_RESULT_WRITE_TARGET, resultWriteTargets);
                    },
                  },
                  { dataIndex: 'status', title: '状态', width: 100 },
                  {
                    fixed: 'right',
                    key: 'actions',
                    title: '操作',
                    valueType: 'option',
                    width: 300,
                    render: (_, row) => (
                      <Space className="management-row-actions" size={0}>
                        <Button
                          aria-label={`编辑动作 ${row.name}`}
                          icon={<EditOutlined />}
                          onClick={() => openEditActionModal(row)}
                          type="link"
                        >
                          编辑
                        </Button>
                        <Button icon={<PlayCircleOutlined />} onClick={() => openTrialModal(row)} type="link">
                          试运行
                        </Button>
                        <Button onClick={() => runAction(row)} type="link">运行</Button>
                        <Button
                          aria-label={`删除动作 ${row.name}`}
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => confirmDeleteAction(row)}
                          type="link"
                        >
                          删除
                        </Button>
                      </Space>
                    ),
                  },
                ]}
              />
            ),
          },
        ]}
      />

      {rotatedRunnerToken ? (
        <Alert
          closable
          onClose={() => setRotatedRunnerToken(undefined)}
          showIcon
          style={{ marginTop: 16 }}
          title="Runner Token 已轮换"
          type="success"
          description={(
            <Space orientation="vertical" size={6}>
              <Typography.Text>新 Token 仅本次返回，请同步更新本地 Runner 配置。</Typography.Text>
              <Typography.Text code copyable={{ text: rotatedRunnerToken }}>
                {rotatedRunnerToken}
              </Typography.Text>
            </Space>
          )}
        />
      ) : null}

      <Modal
        cancelText="取消"
        confirmLoading={rotatingRunnerLoading}
        destroyOnHidden
        okText="确定"
        open={Boolean(rotatingRunner)}
        title="轮换 Runner Token"
        onCancel={() => setRotatingRunner(undefined)}
        onOk={submitRotateRunnerToken}
      >
        <Space orientation="vertical" size={8}>
          <Typography.Text>
            轮换后旧 Token 会立即失效，请将新 Token 配置到本地 Runner。
          </Typography.Text>
          <Typography.Text type="secondary">
            当前执行器：{rotatingRunner?.name ?? '-'}
          </Typography.Text>
        </Space>
      </Modal>

      <Modal
        aria-label="Runner 执行日志"
        destroyOnHidden
        footer={(
          <Space>
            <Button onClick={() => setRunnerLogModalOpen(false)}>关闭</Button>
            <Button
              aria-label="取消任务"
              danger
              disabled={!runnerLogTask?.id || ['cancelled', 'failed', 'succeeded', 'timed_out'].includes(runnerLogTask.status)}
              icon={<StopOutlined />}
              loading={runnerLogLoading}
              onClick={cancelRunnerTask}
            >
              取消任务
            </Button>
          </Space>
        )}
        open={runnerLogModalOpen}
        title="Runner 执行日志"
        width={820}
        onCancel={() => setRunnerLogModalOpen(false)}
      >
        <Space orientation="vertical" size={12} style={{ width: '100%' }}>
          <Space wrap>
            <Typography.Text strong>任务 ID</Typography.Text>
            <Typography.Text code copyable={runnerLogTask?.id ? { text: runnerLogTask.id } : false}>
              {runnerLogTask?.id ?? '-'}
            </Typography.Text>
            <Tag>{runnerLogTask?.status ?? '-'}</Tag>
          </Space>
          <Table<AiExecutorTaskLogRecord>
            columns={[
              { dataIndex: 'sequence', title: '#', width: 72 },
              { dataIndex: 'level', title: '级别', width: 100, render: (value) => String(value ?? 'info') },
              {
                dataIndex: 'message',
                title: '日志内容',
                render: (value) => (
                  <Typography.Text style={{ whiteSpace: 'pre-wrap' }}>
                    {String(value ?? '')}
                  </Typography.Text>
                ),
              },
              {
                key: 'created_at',
                title: '时间',
                width: 220,
                render: (_, row) =>
                  row.created_at ?? String((row as unknown as Record<string, unknown>).timestamp ?? '-'),
              },
            ]}
            dataSource={runnerLogRows}
            loading={runnerLogLoading}
            pagination={false}
            rowKey={(row) => `${row.sequence ?? row.created_at ?? row.message}-${row.message}`}
            size="small"
          />
        </Space>
      </Modal>

      <Modal
        open={pluginModalOpen}
        title={editingPlugin ? '编辑插件' : '新增插件'}
        onCancel={closePluginModal}
        onOk={submitPlugin}
      >
        <Form
          form={pluginForm}
          layout="vertical"
          initialValues={{ category: 'general', protocol: 'http', risk_level: 'medium', status: 'active' }}
        >
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input prefix={<ApiOutlined />} />
          </Form.Item>
          <Form.Item label="编码" name="code" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="协议" name="protocol">
            <Select
              options={[
                { label: 'HTTP', value: 'http' },
                { label: 'MCP HTTP', value: 'mcp_http' },
                { label: 'MCP Stdio', value: 'mcp_stdio' },
                { label: 'Runner Polling', value: 'runner_polling' },
                { label: 'Runner WebSocket', value: 'runner_websocket' },
              ]}
            />
          </Form.Item>
          <Form.Item label="分类" name="category" rules={[{ required: true, message: '请选择插件分类' }]}>
            <Select options={pluginCategoryOptions} />
          </Form.Item>
          <Form.Item label="风险等级" name="risk_level">
            <Select
              options={[
                { label: 'low', value: 'low' },
                { label: 'medium', value: 'medium' },
                { label: 'high', value: 'high' },
              ]}
            />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select
              options={[
                { label: 'active', value: 'active' },
                { label: 'draft', value: 'draft' },
                { label: 'disabled', value: 'disabled' },
              ]}
            />
          </Form.Item>
          <Form.Item label="说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={runnerModalOpen}
        title={editingRunner ? '编辑执行器' : '新增执行器'}
        width={760}
        cancelText="取消"
        okText="确定"
        onCancel={closeRunnerModal}
        onOk={submitRunner}
      >
        <Form
          form={runnerForm}
          layout="vertical"
          initialValues={{
            endpoint_url: 'runner://local',
            executor_types: ['codex', 'openclaw'],
            heartbeat_timeout_seconds: 120,
            install_mode: 'systemd',
            max_concurrent_tasks: 1,
            metadata: '{}',
            package_arch: 'amd64',
            protocol: 'runner_polling',
            status: 'active',
            target_os: 'linux',
          }}
          onValuesChange={(changedValues) => {
            if (Object.prototype.hasOwnProperty.call(changedValues, 'target_os')) {
              const targetOs = stringValue(changedValues.target_os, 'linux');
              runnerForm.setFieldValue('install_mode', runnerDefaultInstallMode(targetOs));
              if (targetOs === 'manual') {
                runnerForm.setFieldValue('package_arch', 'universal');
              } else if (!runnerForm.getFieldValue('package_arch')) {
                runnerForm.setFieldValue('package_arch', 'amd64');
              }
            }
          }}
        >
          <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入执行器名称' }]}>
            <Input placeholder="Zeek Mac 本地执行器" />
          </Form.Item>
          <Space wrap>
            <Form.Item label="协议" name="protocol" rules={[{ required: true }]}>
              <Select options={aiExecutorRunnerProtocolOptions} style={{ width: 180 }} />
            </Form.Item>
            <Form.Item label="状态" name="status" rules={[{ required: true }]}>
              <Select
                options={[
                  { label: 'active', value: 'active' },
                  { label: 'offline', value: 'offline' },
                  { label: 'disabled', value: 'disabled' },
                ]}
                style={{ width: 150 }}
              />
            </Form.Item>
            <Form.Item label="心跳超时秒数" name="heartbeat_timeout_seconds">
              <InputNumber min={10} style={{ width: 160 }} />
            </Form.Item>
            <Form.Item label="最大并发" name="max_concurrent_tasks">
              <InputNumber min={1} style={{ width: 130 }} />
            </Form.Item>
          </Space>
          <Form.Item label="Endpoint" name="endpoint_url" rules={[{ required: true }]}>
            <Input placeholder="runner://local 或 mcp://runner" />
          </Form.Item>
          <Form.Item label="执行器类型" name="executor_types" rules={[{ required: true, message: '请选择至少一个执行器类型' }]}>
            <Select mode="multiple" options={aiExecutorTypeOptions} />
          </Form.Item>
          <Typography.Text strong>执行器命令配置</Typography.Text>
          <Space wrap>
            <Form.Item label="Codex 命令" name="codex_command">
              <Input placeholder="codex" style={{ width: 220 }} />
            </Form.Item>
            <Form.Item label="Claude Code 命令" name="claude_command">
              <Input placeholder="claude" style={{ width: 220 }} />
            </Form.Item>
            <Form.Item label="Hermes 命令" name="hermes_command">
              <Input placeholder="hermes" style={{ width: 220 }} />
            </Form.Item>
            <Form.Item label="OpenClaw 命令" name="openclaw_command">
              <Input placeholder="openclaw" style={{ width: 220 }} />
            </Form.Item>
          </Space>
          <Typography.Text strong>Runner 安装包配置</Typography.Text>
          <Space wrap>
            <Form.Item label="目标系统" name="target_os" rules={[{ required: true, message: '请选择目标系统' }]}>
              <Select options={aiExecutorRunnerTargetOsOptions} style={{ width: 180 }} />
            </Form.Item>
            <Form.Item label="CPU 架构" name="package_arch" rules={[{ required: true, message: '请选择 CPU 架构' }]}>
              <Select options={aiExecutorRunnerArchOptions} style={{ width: 160 }} />
            </Form.Item>
            <Form.Item noStyle shouldUpdate={(prev, current) => prev.target_os !== current.target_os}>
              {({ getFieldValue }) => (
                <Form.Item label="安装模式" name="install_mode" rules={[{ required: true, message: '请选择安装模式' }]}>
                  <Select
                    options={runnerInstallModeOptions(getFieldValue('target_os'))}
                    style={{ width: 190 }}
                  />
                </Form.Item>
              )}
            </Form.Item>
          </Space>
          <Form.Item label="工作区白名单" name="workspace_roots">
            <Input.TextArea
              placeholder="/Users/zeek/source/e-ai-brain"
              rows={3}
            />
          </Form.Item>
          <Form.Item label="Runner Token" name="runner_token">
            <Input.Password placeholder={editingRunner ? '留空表示不修改 Token' : '留空自动生成'} />
          </Form.Item>
          <Form.Item label="Metadata JSON" name="metadata">
            <Input.TextArea rows={4} placeholder='{"codex_path":"/Applications/Codex.app/Contents/Resources/codex"}' />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={connectionModalOpen}
        title={editingConnection ? '编辑连接' : '新增连接'}
        width={860}
        footer={[
          <Button key="cancel" onClick={closeConnectionModal}>
            取消
          </Button>,
          <Button
            key="save"
            disabled={Boolean(connectionSubmitAction)}
            loading={connectionSubmitAction === 'save'}
            onClick={() => void submitConnection()}
          >
            确定
          </Button>,
          <Button
            key="save-test"
            aria-label="保存并测试"
            disabled={Boolean(connectionSubmitAction)}
            icon={<PlayCircleOutlined />}
            loading={connectionSubmitAction === 'save-test'}
            onClick={() => void submitConnection({ testAfterSave: true })}
            type="primary"
          >
            保存并测试
          </Button>,
        ]}
        onCancel={closeConnectionModal}
        onOk={() => void submitConnection()}
      >
        <Form
          form={connectionForm}
          layout="vertical"
          initialValues={{ auth_type: 'none', environment: 'default', max_retries: 0, status: 'active', timeout_seconds: 30 }}
          onValuesChange={(changedValues, allValues) => {
            if (selectedConnectionIsGitlab && Object.prototype.hasOwnProperty.call(changedValues, 'schema_values')) {
              const nextEndpointUrl = endpointUrlFromSchemaValues(allValues, selectedConnectionSchema);
              if (nextEndpointUrl && nextEndpointUrl !== allValues.endpoint_url) {
                connectionForm.setFieldValue('endpoint_url', nextEndpointUrl);
              }
            }
            if (
              advancedConnectionRequestJsonOpen
              && !Object.prototype.hasOwnProperty.call(changedValues, 'request_config')
            ) {
              connectionForm.setFieldValue(
                'request_config',
                stableJson(buildConnectionRequestConfig(allValues, selectedConnectionSchema)),
              );
            }
          }}
        >
          <Form.Item label="插件" name="plugin_id" rules={[{ required: true }]}>
            <Select options={pluginOptions} onChange={applyConnectionPluginDefaults} />
          </Form.Item>
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Endpoint URL" name="endpoint_url" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Space>
            <Form.Item label="环境" name="environment">
              <Select options={connectionEnvironmentOptions} />
            </Form.Item>
            <Form.Item label="认证" name="auth_type">
              <Select
                options={[
                  { label: 'none', value: 'none' },
                  { label: 'bearer', value: 'bearer' },
                  { label: 'api_key_header', value: 'api_key_header' },
                  { label: 'basic', value: 'basic' },
                ]}
              />
            </Form.Item>
          </Space>
          {!advancedConnectionJsonOpen && selectedConnectionAuthType === 'api_key_header' ? (
            <Space wrap>
              <Form.Item label="Header 名" name="header_name">
                <Input placeholder="Authorization" />
              </Form.Item>
              <Form.Item label="Header 值/密钥引用" name="secret_ref">
                <Input placeholder="vault/path/to/token 或 APPCODE xxx" style={{ width: 320 }} />
              </Form.Item>
            </Space>
          ) : null}
          {!advancedConnectionJsonOpen && selectedConnectionAuthType === 'bearer' ? (
            <Form.Item
              extra={
                selectedConnectionIsGithub
                  ? '填写 GitHub Personal Access Token，或平台可解析的密钥引用。本地联调可直接填 ghp_xxx；生产建议填 vault/github/token 或 env:GITHUB_TOKEN。'
                  : '填写 Bearer Token 或平台可解析的密钥引用。'
              }
              label="Token / 密钥引用"
              name="token_ref"
              rules={
                selectedConnectionIsGithub
                  ? [{ required: true, message: '请填写 GitHub Token 或密钥引用' }]
                  : undefined
              }
            >
              <Input placeholder="ghp_xxx / vault/github/token / env:GITHUB_TOKEN" />
            </Form.Item>
          ) : null}
          {!advancedConnectionJsonOpen && selectedConnectionAuthType === 'basic' ? (
            <Space wrap>
              <Form.Item label="用户名引用" name="username_ref">
                <Input placeholder="vault/path/to/username" />
              </Form.Item>
              <Form.Item label="密码引用" name="password_ref">
                <Input placeholder="vault/path/to/password" />
              </Form.Item>
            </Space>
          ) : null}
          <Button type="link" onClick={toggleAdvancedConnectionJson}>
            高级认证 JSON 修改
          </Button>
          {advancedConnectionJsonOpen ? (
            <>
              <Space style={{ marginBottom: 8 }}>
                <Button onClick={() => {
                  const values = connectionForm.getFieldsValue();
                  connectionForm.setFieldValue('auth_config', stableJson(buildConnectionAuthConfig(values)));
                }}>
                  同步可视化到 JSON
                </Button>
                <Button onClick={applyConnectionJsonToVisual}>从 JSON 应用到字段</Button>
              </Space>
              <Form.Item label="认证配置 JSON" name="auth_config">
                <Input.TextArea rows={4} placeholder='{"header_name":"PRIVATE-TOKEN","secret_ref":"vault/gitlab/token"}' />
              </Form.Item>
            </>
          ) : null}
          <ConnectionSchemaFields
            pluginCode={selectedConnectionPluginCode}
            schema={selectedConnectionSchema}
          />
          <RequestParameterRows
            addText="添加 Params"
            name="connection_param_rows"
            namePlaceholder="参数名"
            title="高级查询 Params"
            valuePlaceholder="参数值"
          />
          <RequestParameterRows
            addText="添加 Headers"
            name="connection_header_rows"
            namePlaceholder="Header 名"
            title="Headers"
            valuePlaceholder="Header 值"
          />
          <Button type="link" onClick={toggleAdvancedConnectionRequestJson}>
            高级请求 JSON 修改
          </Button>
          {advancedConnectionRequestJsonOpen ? (
            <>
              <Space style={{ marginBottom: 8 }}>
                <Button onClick={syncConnectionRequestJsonFromVisual}>同步可视化到 JSON</Button>
                <Button onClick={applyConnectionRequestJsonToVisual}>从 JSON 应用到 Params / Headers</Button>
              </Space>
              <Form.Item label="请求配置 JSON" name="request_config">
                <Input.TextArea rows={4} placeholder='{"query":{"start_pt":"{{current_date-7}}"},"headers":{"Authorization":"APPCODE xxx"}}' />
              </Form.Item>
            </>
          ) : null}
          <Space>
            <Form.Item label="超时秒数" name="timeout_seconds">
              <InputNumber min={1} />
            </Form.Item>
            <Form.Item label="重试次数" name="max_retries">
              <InputNumber min={0} />
            </Form.Item>
            <Form.Item label="状态" name="status">
              <Select
                options={[
                  { label: 'active', value: 'active' },
                  { label: 'draft', value: 'draft' },
                  { label: 'disabled', value: 'disabled' },
                ]}
              />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      <Modal
        cancelText="取消"
        okText="确定"
        open={actionModalOpen}
        title={editingAction ? '编辑动作' : '新增动作'}
        onCancel={closeActionModal}
        onOk={submitAction}
      >
        <Form
          form={actionForm}
          layout="vertical"
          onValuesChange={(changedValues, allValues) => {
            if (
              advancedActionJsonOpen
              && !Object.prototype.hasOwnProperty.call(changedValues, 'request_config')
              && !Object.prototype.hasOwnProperty.call(changedValues, 'result_mapping')
            ) {
              const requestConfig =
                allValues.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO
                  ? buildMaxComputeRequestConfig(allValues)
                  : buildVisualRequestConfig(allValues);
              actionForm.setFieldsValue({
                request_config: stableJson(requestConfig),
                result_mapping: stableJson(buildVisualResultMapping(allValues, resultWriteTargets)),
              });
            }
          }}
          initialValues={{
            action_type: 'http_request',
            method: 'GET',
            requires_human_review: false,
            write_target: DEFAULT_RESULT_WRITE_TARGET,
            status: 'active',
          }}
        >
          <Form.Item label="配置场景" name="scenario">
            <Select
              allowClear
              onChange={applyActionScenario}
              options={actionTemplateOptions}
            />
          </Form.Item>
          <Form.Item label="插件" name="plugin_id" rules={[{ required: true }]}>
            <Select options={pluginOptions} />
          </Form.Item>
          <Form.Item label="连接" name="connection_id">
            <Select allowClear options={connectionOptions} />
          </Form.Item>
          <Form.Item label="结果写入目标" name="write_target">
            <Select options={resultWriteTargetOptions} onChange={applyWriteTargetDefaults} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(previous, current) => previous.write_target !== current.write_target}>
            {({ getFieldValue }) => {
              const writeTarget = getFieldValue('write_target');
              return (
                <ResultWriteTargetMappingFields
                  writeTarget={writeTarget}
                  writeTargets={resultWriteTargets}
                />
              );
            }}
          </Form.Item>
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="编码" name="code" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Space>
            <Form.Item label="动作类型" name="action_type">
              <Select
                options={[
                  { label: 'http_request', value: 'http_request' },
                  { label: 'mcp_tool', value: 'mcp_tool' },
                ]}
              />
            </Form.Item>
            <Form.Item label="人工确认" name="requires_human_review" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="状态" name="status">
              <Select
                options={[
                  { label: 'active', value: 'active' },
                  { label: 'draft', value: 'draft' },
                  { label: 'disabled', value: 'disabled' },
                ]}
              />
            </Form.Item>
          </Space>
          {actionScenario !== MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO ? (
            <>
              <Space wrap>
                <Form.Item label="请求方法" name="method">
                  <Select options={requestMethodOptions} style={{ width: 140 }} />
                </Form.Item>
                <Form.Item label="请求路径" name="path">
                  <Input placeholder="/api/path" style={{ width: 320 }} />
                </Form.Item>
              </Space>
              <RequestParameterRows
                addText="添加 Params"
                name="param_rows"
                namePlaceholder="参数名"
                title="Params"
                valuePlaceholder="参数值"
              />
              <RequestParameterRows
                addText="添加 Headers"
                name="header_rows"
                namePlaceholder="Header 名"
                title="Headers"
                valuePlaceholder="Header 值"
              />
            </>
          ) : null}
          {actionScenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO ? (
            <>
              <Form.Item label="表名" name="table_name">
                <Input />
              </Form.Item>
              <Space wrap>
                <Form.Item label="时间字段" name="time_field">
                  <Input />
                </Form.Item>
                <Form.Item label="最大行数" name="max_rows">
                  <InputNumber min={1} style={{ width: 160 }} />
                </Form.Item>
              </Space>
              <Form.Item label="返回字段" name="returned_fields">
                <Input />
              </Form.Item>
            </>
          ) : null}
          <div style={{ background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <Typography.Text strong>请求预览</Typography.Text>
            <pre style={{ margin: '8px 0 0', whiteSpace: 'pre-wrap' }}>{compactJson(requestPreview)}</pre>
          </div>
          <Button type="link" onClick={toggleAdvancedActionJson}>
            高级 JSON 修改
          </Button>
          {advancedActionJsonOpen ? (
            <>
              <Space style={{ marginBottom: 8 }}>
                <Button onClick={syncActionJsonFromVisual}>同步可视化到 JSON</Button>
                <Button onClick={applyActionJsonToVisual}>从 JSON 应用到 Params / Headers</Button>
              </Space>
              <Form.Item label="请求配置 JSON" name="request_config">
                <Input.TextArea rows={5} placeholder='{"method":"GET","path":"/api/v4/projects/1/metrics"}' />
              </Form.Item>
              <Form.Item label="结果映射 JSON" name="result_mapping">
                <Input.TextArea rows={3} placeholder='{"records_imported_path":"$.commits"}' />
              </Form.Item>
            </>
          ) : null}
          <Form.Item label="说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        confirmLoading={trialRunning}
        okText="试运行"
        open={trialModalOpen}
        title={`动作试运行${trialAction ? `：${trialAction.name}` : ''}`}
        width={820}
        onCancel={() => setTrialModalOpen(false)}
        onOk={runActionTrial}
      >
        <Space orientation="vertical" size={12} style={{ width: '100%' }}>
          <Space wrap>
            <Typography.Text strong>连接</Typography.Text>
            <Select
              allowClear
              options={connectionOptions}
              style={{ width: 320 }}
              value={trialConnectionId}
              onChange={setTrialConnectionId}
            />
          </Space>
          <div>
            <Typography.Text strong>试运行输入 JSON</Typography.Text>
            <Input.TextArea
              rows={5}
              value={trialInputJson}
              onChange={(event) => setTrialInputJson(event.target.value)}
            />
          </div>
          {trialResult ? (
            <Space orientation="vertical" size={10} style={{ width: '100%' }}>
              <div>
                状态：<Tag color={trialResult.status === 'succeeded' ? 'green' : 'red'}>{trialResult.status}</Tag>
                耗时：{trialResult.latency_ms}ms
              </div>
              {trialResult.error_message ? <Alert title={trialResult.error_message} type="error" /> : null}
              <Typography.Text strong>请求预览</Typography.Text>
              <pre style={{ background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, whiteSpace: 'pre-wrap' }}>
                {compactJson(trialResult.request_preview)}
              </pre>
              <Typography.Text strong>结果映射命中</Typography.Text>
              <Table
                columns={[
                  { dataIndex: 'key', title: '字段' },
                  { dataIndex: 'path', title: 'JSONPath' },
                  { dataIndex: 'matched', title: '命中', render: (value: boolean) => <Tag color={value ? 'green' : 'red'}>{value ? '是' : '否'}</Tag> },
                  { dataIndex: 'value_preview', title: '值预览', ellipsis: true, render: (value: unknown) => compactJson(value) },
                ]}
                dataSource={trialResult.mapping_hits ?? []}
                pagination={false}
                rowKey="key"
                size="small"
              />
              <TrialWritePreviewBlock value={trialResult.write_preview} />
              <Typography.Text strong>响应摘要</Typography.Text>
              <pre style={{ background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, whiteSpace: 'pre-wrap' }}>
                {compactJson(trialResult.response_summary)}
              </pre>
            </Space>
          ) : null}
        </Space>
      </Modal>
    </PageContainer>
  );
}
