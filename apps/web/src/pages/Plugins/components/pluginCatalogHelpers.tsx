import { Tag } from 'antd';

export const OFFICIAL_PLUGIN_LABEL = '官方标准';

export const pluginCategoryOptions = [
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

const pluginVersionStatusLabelByValue = new Map([
  ['custom', '自定义'],
  ['latest', '最新'],
  ['upgrade_available', '可升级'],
]);

export function pluginCategoryLabel(value: unknown) {
  return pluginCategoryLabelByValue.get(String(value)) ?? String(value ?? '-');
}

export function pluginVersionStatusTag(record: {
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
