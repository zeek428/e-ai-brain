import type { ManagementListQuery } from '../../../components/ManagementListPage';
import type {
  AiAgentListQuery,
  AiAgentRecord,
  AiSkillListQuery,
  AiSkillRecord,
  RemoteListPerformance,
} from '../../../services/aiBrain';

export type SkillFormValues = {
  code: string;
  input_schema_json?: string;
  name: string;
  output_schema_json?: string;
  prompt_template: string;
  requires_human_review: boolean;
  risk_level: string;
  status: string;
  version: string;
};

export type SkillPackageFormValues = {
  code: string;
  name: string;
  requires_human_review: boolean;
  risk_level: string;
  status: string;
  version: string;
};

export type AgentFormValues = {
  code: string;
  default_skill_ids?: string;
  model_gateway_config_id?: string;
  name: string;
  status: string;
  system_prompt: string;
};

export type AgentPackageFormValues = {
  brain_app_id: string;
  code: string;
  default_skill_ids?: string[];
  model_gateway_config_id?: string;
  name: string;
  status: string;
  version: string;
};

export type AiAgentRow = AiAgentRecord & {
  defaultSkillText: string;
  modelGatewayText: string;
  searchText: string;
} & Record<string, unknown>;

export type AiSkillRow = AiSkillRecord & {
  reviewValue: string;
  searchText: string;
} & Record<string, unknown>;

export type RemotePageState = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  total: number;
};

export const DEFAULT_LIST_QUERY: ManagementListQuery = {
  filters: {},
  page: 1,
  pageSize: 10,
  sortField: 'code',
  sortOrder: 'ascend',
};

export const SKILL_STATUS_OPTIONS = [
  { label: '启用', value: 'active' },
  { label: '草稿', value: 'draft' },
  { label: '停用', value: 'disabled' },
];

export const AGENT_STATUS_OPTIONS = [
  { label: '启用', value: 'active' },
  { label: '停用', value: 'disabled' },
];

export const STATUS_LABELS: Record<string, string> = {
  active: '启用',
  disabled: '停用',
  draft: '草稿',
};

export const STATUS_COLORS: Record<string, string> = {
  active: 'green',
  disabled: 'default',
  draft: 'gold',
};

export const SKILL_SOURCE_OPTIONS = [
  { label: '表单', value: 'inline' },
  { label: '文件包', value: 'package' },
];

export const REVIEW_OPTIONS = [
  { label: '需要', value: 'required' },
  { label: '不需要', value: 'optional' },
];

export const stringValue = (value: unknown) => {
  if (typeof value === 'string') {
    return value.trim() || undefined;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return undefined;
};

const filterText = (filters: Record<string, unknown>, key: string) => stringValue(filters[key]);

const agentSortField = (field?: string) => {
  if (field === 'name' || field === 'status') {
    return field;
  }
  if (field === 'modelGatewayText') {
    return 'model_gateway_config_id';
  }
  return 'code';
};

const skillSortField = (field?: string) => {
  if (
    field === 'name' ||
    field === 'version' ||
    field === 'source_type' ||
    field === 'requires_human_review' ||
    field === 'status'
  ) {
    return field;
  }
  return 'code';
};

export const agentListQuery = (query: ManagementListQuery): AiAgentListQuery => {
  const keyword = [
    filterText(query.filters, 'searchText'),
    filterText(query.filters, 'modelGatewayText'),
  ].filter(Boolean).join(' ');
  return {
    keyword: keyword || undefined,
    page: query.page,
    pageSize: query.pageSize,
    sortField: agentSortField(query.sortField),
    sortOrder: query.sortOrder ?? 'ascend',
    status: filterText(query.filters, 'status'),
  };
};

export const skillListQuery = (query: ManagementListQuery): AiSkillListQuery => {
  const reviewValue = filterText(query.filters, 'reviewValue');
  return {
    keyword: filterText(query.filters, 'searchText'),
    page: query.page,
    pageSize: query.pageSize,
    requiresHumanReview:
      reviewValue === 'required' ? true : reviewValue === 'optional' ? false : undefined,
    sortField: skillSortField(query.sortField),
    sortOrder: query.sortOrder ?? 'ascend',
    sourceType: filterText(query.filters, 'source_type'),
    status: filterText(query.filters, 'status'),
  };
};

export const modelGatewayIdFromReference = (value: unknown): string | undefined => {
  const primitive = stringValue(value);
  if (primitive) {
    return primitive;
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  const record = value as Record<string, unknown>;
  return (
    stringValue(record.id)
    ?? stringValue(record.config_id)
    ?? stringValue(record.model_gateway_config_id)
  );
};

export const modelGatewayReferenceCandidates = (agent: AiAgentRecord) => {
  const record = agent as AiAgentRecord & Record<string, unknown>;
  return [
    record.model_gateway_config_id,
    record.model_gateway_config,
    record.model_gateway_config_snapshot,
    record.resolved_model_gateway_config,
  ];
};

export const modelGatewayIdFromAgent = (agent: AiAgentRecord) => {
  for (const candidate of modelGatewayReferenceCandidates(agent)) {
    const configId = modelGatewayIdFromReference(candidate);
    if (configId) {
      return configId;
    }
  }
  return undefined;
};

export const modelGatewayLabelFromReference = (value: unknown): string | undefined => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  const record = value as Record<string, unknown>;
  const name =
    stringValue(record.name)
    ?? stringValue(record.label)
    ?? stringValue(record.title)
    ?? modelGatewayIdFromReference(record);
  if (!name) {
    return undefined;
  }
  const model =
    stringValue(record.defaultChatModel)
    ?? stringValue(record.default_chat_model)
    ?? stringValue(record.chat_model)
    ?? stringValue(record.model);
  return model ? `${name} (${model})` : name;
};

export const prettyJson = (value: unknown) =>
  JSON.stringify(value && typeof value === 'object' ? value : {}, null, 2);

export const parseJsonObject = (value: string | undefined, label: string): Record<string, unknown> => {
  const rawValue = value?.trim() || '{}';
  try {
    const parsed = JSON.parse(rawValue) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error(`${label} 必须是 JSON 对象`);
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    if (error instanceof Error && error.message.includes('必须是 JSON 对象')) {
      throw error;
    }
    throw new Error(`${label} 不是合法 JSON`);
  }
};
