import type { ManagementListQuery } from '../../components/ManagementListPage';
import type { KnowledgeRecord } from '../../data/management';
import type {
  KnowledgeListQuery,
  KnowledgeSpaceRecord,
  KnowledgeStalenessSummary,
} from '../../services/aiBrain';
import type { KnowledgeAdvancedFilterValues } from './types';

export const statusLabels: Record<
  KnowledgeRecord['status'],
  { color: string; label: string }
> = {
  archived: { color: 'default', label: '已归档' },
  importing: { color: 'blue', label: '索引中' },
  indexed: { color: 'green', label: '已索引' },
  index_failed: { color: 'red', label: '索引失败' },
  pending_index: { color: 'gold', label: '待索引' },
  text_indexed: { color: 'cyan', label: '文本索引' },
  vector_indexed: { color: 'green', label: '向量索引' },
};

export const depositStatusLabels: Record<string, { color: string; label: string }> = {
  approved: { color: 'green', label: '已入库' },
  pending: { color: 'gold', label: '待审核' },
  rejected: { color: 'red', label: '已拒绝' },
};

export const importJobStatusLabels: Record<string, { color: string; label: string }> = {
  cancelled: { color: 'default', label: '已取消' },
  completed: { color: 'green', label: '已完成' },
  failed: { color: 'red', label: '失败' },
  parsing: { color: 'blue', label: '解析中' },
  queued: { color: 'default', label: '排队中' },
  uploaded: { color: 'default', label: '已上传' },
};

export const assetTypeLabels: Record<string, string> = {
  image_annotation_json: '图片标注',
  layout_json: '版面数据',
  ocr_json: 'OCR 结果',
  original: '原始文件',
  parsed_markdown: '解析文本',
  table_json: '表格数据',
};

export const modalityLabels: Record<string, string> = {
  image: '图片',
  layout: '版面',
  multimodal: '多模态',
  table: '表格',
  text: '文本',
};

export const KNOWLEDGE_TABLE_SCROLL_X = 1520;
export const KNOWLEDGE_ACTION_COLUMN_WIDTH = 220;
export const INITIAL_STALENESS_SUMMARY: KnowledgeStalenessSummary = {
  expired: 0,
  expiring: 0,
  flaggedOutdated: 0,
  fresh: 0,
};

export function formatAssetSize(sizeBytes: number) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }
  return `${(sizeBytes / 1024 / 1024).toFixed(1)} MB`;
}

const knowledgeSortFieldMap: Record<string, string> = {
  documentType: 'doc_type',
  id: 'id',
  ownerRole: 'permission_roles',
  status: 'index_status',
  title: 'title',
  updatedAt: 'updated_at',
};

export function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

export function hasFilterValues(filters: Record<string, unknown>) {
  return Object.values(filters).some((value) => normalizeFilterText(value));
}

export function normalizeAdvancedFilters(values: KnowledgeAdvancedFilterValues) {
  return {
    documentType: normalizeFilterText(values.documentType),
    folderId: normalizeFilterText(values.folderId),
    ownerRole: normalizeFilterText(values.ownerRole),
  };
}

export function removeAdvancedFilters(filters: ManagementListQuery['filters']) {
  const restFilters = { ...filters };
  delete restFilters.documentType;
  delete restFilters.folderId;
  delete restFilters.ownerRole;
  return restFilters;
}

export function isNoisyKnowledgeSpace(space: KnowledgeSpaceRecord) {
  const normalized = `${space.code} ${space.name} ${space.description ?? ''}`.toLowerCase();
  return [
    'full-chain',
    'smoke',
    'test',
    'tmp',
    'temp',
    'worker',
    'parser',
    '验证',
    '测试',
  ].some((keyword) => normalized.includes(keyword));
}

export function buildKnowledgeListQuery(query: ManagementListQuery): KnowledgeListQuery {
  return {
    documentType: normalizeFilterText(query.filters.documentType),
    folderId: normalizeFilterText(query.filters.folderId),
    keyword: normalizeFilterText(query.filters.title),
    knowledgeSpaceId: normalizeFilterText(query.filters.knowledgeSpaceId),
    ownerRole: normalizeFilterText(query.filters.ownerRole),
    page: query.page,
    pageSize: query.pageSize,
    sortField: query.sortField
      ? knowledgeSortFieldMap[query.sortField] ?? query.sortField
      : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
  };
}
