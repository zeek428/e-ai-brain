import {
  resolveAssistantDraftResourceId,
  type AiExecutorRunnerRecord,
  type PluginActionRecord,
  type PluginActionTemplateRecord,
  type PluginConnectionRecord,
  type PluginConnectionSchemaFieldRecord,
  type PluginConnectionSchemaRecord,
  type PluginMarketplaceItem,
  type PluginRecord,
  type ResultWriteTargetRecord,
} from '../../../services/aiBrain';
import type { PluginActionFormValues } from './PluginActionModal';
import type { PluginConnectionFormValues } from './PluginConnectionModal';
import {
  parseGitLabProjectAddress,
  parseGitRepositoryAddress,
  safeDecodeURIComponent,
} from './pluginConnectionAddressHelpers';
import {
  runnerExecutorCommandsFromValues,
  type AiExecutorRunnerFormValues,
} from './pluginRunnerHelpers';

export type RequestParameterRow = {
  description?: string;
  enabled?: boolean;
  name?: string;
  type?: 'boolean' | 'number' | 'string';
  value?: string;
};

export const MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO = 'maxcompute_weekly_feedback';
export const MAXCOMPUTE_DEFAULT_FIELDS =
  'feedback_id,user_id,product_id,module_code,feedback_type,content,sentiment,created_at';
export const DEFAULT_RESULT_WRITE_TARGET = 'scheduled_job_result';

export function stableJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function comparablePluginDraftValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(comparablePluginDraftValue);
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, comparablePluginDraftValue(item)]),
    );
  }
  return value;
}

function pluginDraftFieldChanged(
  field: string,
  initialPayload: Record<string, unknown>,
  currentPayload: Record<string, unknown>,
): boolean {
  const initialValue = initialPayload[field];
  const currentValue = currentPayload[field];
  if (field === 'requires_human_review') {
    return Boolean(initialValue) !== Boolean(currentValue);
  }
  if (
    field === 'result_mapping'
    && isPlainRecord(initialValue)
    && isPlainRecord(currentValue)
  ) {
    return Object.keys(initialValue).some((key) => (
      JSON.stringify(comparablePluginDraftValue(initialValue[key]))
      !== JSON.stringify(comparablePluginDraftValue(currentValue[key]))
    ));
  }
  return (
    JSON.stringify(comparablePluginDraftValue(initialValue))
    !== JSON.stringify(comparablePluginDraftValue(currentValue))
  );
}

export function pluginAssistantDraftModifiedFields(
  initialPayload: Record<string, unknown>,
  currentPayload: Record<string, unknown>,
): string[] {
  const ignoredFields = new Set(['assistant_prerequisite_draft_ids']);
  if (Array.isArray(initialPayload.assistant_prerequisite_draft_ids) && !initialPayload.connection_id) {
    ignoredFields.add('connection_id');
  }
  const fields = new Set([
    ...Object.keys(initialPayload),
    ...Object.keys(currentPayload),
  ]);
  return Array.from(fields)
    .filter((field) => !ignoredFields.has(field))
    .filter((field) => pluginDraftFieldChanged(field, initialPayload, currentPayload))
    .sort((left, right) => left.localeCompare(right));
}

export function linesToArray(value?: string): string[] {
  return (value ?? '')
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
}

export function arrayToLines(value?: string[]): string {
  return (value ?? []).join('\n');
}

export function runnerPayload(values: AiExecutorRunnerFormValues): Partial<AiExecutorRunnerRecord> {
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

export function buildMaxComputeRequestConfig(
  values: Partial<PluginActionFormValues>,
): Record<string, unknown> {
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

export function recordToRows(
  record: unknown,
  excludeKeys: Set<string> = new Set(),
): RequestParameterRow[] {
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

export function configSection(config: Record<string, unknown> | undefined, key: string): unknown {
  const section = config?.[key];
  return section && typeof section === 'object' && !Array.isArray(section) ? section : undefined;
}

function schemaFields(schema?: PluginConnectionSchemaRecord): PluginConnectionSchemaFieldRecord[] {
  return (schema?.sections ?? []).flatMap((section) => section.fields ?? []);
}

export function schemaManagedRequestKeys(
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

export function schemaValuesFromPayload(
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

export function buildVisualRequestConfig(values: Partial<PluginActionFormValues>): Record<string, unknown> {
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

export function buildActionRequestPreview(
  values: Partial<PluginActionFormValues> | undefined,
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

export function buildConnectionAuthConfig(
  values: Partial<PluginConnectionFormValues>,
): Record<string, unknown> {
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

export function buildConnectionRequestConfig(
  values: Partial<PluginConnectionFormValues>,
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

export function endpointUrlFromSchemaValues(
  values: Partial<PluginConnectionFormValues>,
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

export function buildConnectionPayload(
  values: PluginConnectionFormValues,
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

export function buildActionPayload(
  values: PluginActionFormValues,
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

export function parseJsonObject(value: string | undefined, field: string): Record<string, unknown> {
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

export function isFormValidationError(
  error: unknown,
): error is { errorFields: Array<{ name?: Array<string | number> }> } {
  return (
    Boolean(error)
    && typeof error === 'object'
    && Array.isArray((error as { errorFields?: unknown }).errorFields)
  );
}

export function mergeWriteTarget(
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

export function defaultResultMappingForWriteTarget(
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

export function resultWriteTargetLabel(
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

export function resultMappingVisualFields(
  resultMapping: Record<string, unknown>,
  writeTargets: ResultWriteTargetRecord[] = [],
): Partial<PluginActionFormValues> {
  const values: Partial<PluginActionFormValues> & Record<string, string | undefined> = {
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

export function buildVisualResultMapping(
  values: Partial<PluginActionFormValues>,
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

export function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function stringValue(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback;
}

function booleanValue(value: unknown, fallback = false) {
  return typeof value === 'boolean' ? value : fallback;
}

export function numberValue(value: unknown, fallback: number) {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

export function actionScenarioForExistingAction(
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

export function pluginConnectionDraftFormValues(
  payload: Record<string, unknown>,
  schema?: PluginConnectionSchemaRecord,
): Partial<PluginConnectionFormValues> {
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

export function pluginConnectionTemplateFormValues(
  item: PluginMarketplaceItem | undefined,
  options: { pluginId?: string } = {},
): Partial<PluginConnectionFormValues> | undefined {
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

export function pluginActionDraftFormValues(
  payload: Record<string, unknown>,
  writeTargets: ResultWriteTargetRecord[] = [],
): Partial<PluginActionFormValues> {
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
