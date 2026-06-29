import type { KnowledgeRecord } from '../data/management';
import { formatDisplayDateTime } from '../utils/dateTime';
import {
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
  type ListResponse,
  type RemoteListPerformance,
} from './apiClient';
import { requireAccessToken } from './authClient';

type RemoteSortOrder = 'ascend' | 'descend';

type RemoteListQuery = {
  page?: number;
  pageSize?: number;
  sortField?: string;
  sortOrder?: RemoteSortOrder;
};

type RemoteListResult<Row> = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: Row[];
  total: number;
};

export type KnowledgeListQuery = RemoteListQuery & {
  documentType?: string;
  folderId?: string;
  keyword?: string;
  knowledgeSpaceId?: string;
  ownerRole?: string;
  status?: string;
};

export type KnowledgeDepositRecord = {
  aiTaskId: string;
  content: string;
  id: string;
  knowledgeDocumentId?: string | null;
  rejectionReason?: string;
  status: string;
  title: string;
};

export type KnowledgeDepositApprovePayload = {
  permissionRoles?: string[];
  title?: string;
};

export type KnowledgeSearchResultRecord = {
  chunkId?: string;
  chunkIndex?: number;
  content: string;
  documentId: string;
  id: string;
  parentChunkId?: string;
  parentContent?: string;
  retrievalMode?: 'keyword' | 'vector';
  sourceLabel: string;
  title: string;
};

export type KnowledgeSpaceRecord = {
  code: string;
  description?: string;
  id: string;
  name: string;
};

export type KnowledgeFolderRecord = {
  id: string;
  knowledgeSpaceId: string;
  name: string;
  parentFolderId?: string | null;
  path: string;
};

export type KnowledgeAssetRecord = {
  assetType: string;
  filename: string;
  id: string;
  mimeType?: string;
  sizeBytes: number;
  storageProvider?: string;
};

export type KnowledgeImportJobRecord = {
  assetFilename?: string;
  chunkStrategy?: string;
  documentId: string;
  documentTitle?: string;
  errorMessage?: string;
  folderPath?: string;
  id: string;
  parserEngine?: string;
  progress: number;
  status: string;
  updatedAt?: string;
};

export type KnowledgeImportWorkerStatusRecord = {
  activeJobId?: string | null;
  enabled: boolean;
  failedCount: number;
  pendingCount: number;
  processedCount: number;
  queuedJobIds: string[];
  running: boolean;
  workerId?: string | null;
};

export type KnowledgeIndexHealthIssueRecord = {
  action: 'open_chunks' | 'open_import_jobs' | 'retry_index';
  description: string;
  documentId: string;
  indexError?: string | null;
  knowledgeSpaceId?: string | null;
  label: string;
  severity: 'error' | 'processing' | 'warning';
  status: KnowledgeRecord['status'];
  title: string;
  updatedAt?: string;
  vectorIndexError?: string | null;
};

export type KnowledgeIndexHealthRecord = {
  embeddingModels: Array<{
    count: number;
    dimension?: number | null;
    model: string;
  }>;
  importJobCounts: Array<{ count: number; status: string }>;
  issues: KnowledgeIndexHealthIssueRecord[];
  performance?: RemoteListPerformance;
  permissionScope?: {
    filterRole?: string | null;
    globalKnowledgeAccess: boolean;
    knowledgeSpaceScopeIds: string[];
    matchedRoles: string[];
    mode: string;
    readableRoleCount: number;
    scopeLabels: string[];
  };
  retrievalModes: {
    hybridReady: number;
    keywordFallback: number;
    unavailable: number;
  };
  statusCounts: Array<{ count: number; status: string }>;
  summary: {
    chunkReadyDocuments: number;
    embeddingReadyChunks: number;
    indexFailedDocuments: number;
    keywordOnlyChunks: number;
    keywordOnlyDocuments: number;
    missingChunkDocuments: number;
    processingDocuments: number;
    searchableDocuments: number;
    totalChunks: number;
    totalDocuments: number;
    vectorReadyDocuments: number;
  };
};

export type KnowledgeChunkSetRecord = {
  activatedAt?: string;
  chunkCount: number;
  chunkStrategy: string;
  id: string;
  isActive: boolean;
  parserEngine: string;
  status: string;
};

export type KnowledgeChunkRecord = {
  chunkIndex: number;
  chunkRole?: string;
  chunkSetId?: string;
  content: string;
  heading?: string;
  id: string;
  imageCount?: number;
  imageRefs?: string[];
  parentChunkId?: string;
  parentContent?: string;
  pageNumber?: number;
  sectionTitle?: string;
  sourceAssetType?: string;
  sourceKind?: string;
  splitPattern?: string;
  tableColumns?: string[];
  tableCount?: number;
  tableIndex?: number;
};

export type KnowledgeDocumentUploadPayload = {
  chunk_strategy?: string;
  content_base64: string;
  doc_type?: string;
  filename: string;
  folder_id?: string;
  knowledge_space_id: string;
  mime_type?: string;
  parser_engine?: string;
  tags?: string[];
  title: string;
};

export type KnowledgeDocumentMutationPayload = {
  content?: string;
  doc_type?: string;
  folder_id?: string | null;
  index_error?: string | null;
  index_status?: string;
  knowledge_space_id?: string | null;
  permission_roles?: string[];
  tags?: string[];
  title?: string;
};

export type KnowledgeDocumentListItem = {
  active_chunk_set_id?: string | null;
  content?: string;
  created_at?: string;
  doc_type?: string;
  folder_id?: string | null;
  folder_path?: string | null;
  id: string;
  index_error?: string | null;
  index_status?: string;
  knowledge_space_id?: string | null;
  permission_roles?: string[];
  source_asset_id?: string | null;
  tags?: string[];
  title: string;
  updated_at?: string;
  vector_index_error?: string | null;
};

type KnowledgeSpaceListItem = {
  code: string;
  description?: string;
  id: string;
  name: string;
};

type KnowledgeFolderListItem = {
  id: string;
  knowledge_space_id: string;
  name: string;
  parent_folder_id?: string | null;
  path?: string;
};

type KnowledgeAssetListItem = {
  asset_type?: string;
  filename?: string;
  id: string;
  mime_type?: string;
  size_bytes?: number;
  storage_provider?: string;
};

type KnowledgeImportJobListItem = {
  asset_filename?: string;
  chunk_strategy?: string;
  document_id: string;
  document_title?: string;
  error_message?: string | null;
  folder_path?: string;
  id: string;
  parser_engine?: string;
  progress?: number;
  status?: string;
  updated_at?: string;
};

type KnowledgeImportWorkerStatusItem = {
  active_job_id?: string | null;
  enabled?: boolean;
  failed_count?: number;
  pending_count?: number;
  processed_count?: number;
  queued_job_ids?: string[];
  running?: boolean;
  worker_id?: string | null;
};

type KnowledgeChunkSetListItem = {
  activated_at?: string;
  chunk_count?: number;
  chunk_strategy?: string;
  id: string;
  is_active?: boolean;
  parser_engine?: string;
  status?: string;
};

type KnowledgeChunkListItem = {
  chunk_index?: number;
  chunk_set_id?: string;
  content?: string;
  id: string;
  metadata?: {
    columns?: string[];
    chunk_role?: string;
    heading?: string;
    image_count?: number;
    image_refs?: string[];
    page_number?: number;
    section_title?: string;
    source_asset_type?: string;
    source_kind?: string;
    split_pattern?: string;
    table_count?: number;
    table_index?: number;
  };
  parent_chunk_id?: string;
  parent_content?: string;
};

export type KnowledgeDepositListItem = {
  ai_task_id: string;
  content?: string;
  id: string;
  knowledge_document_id?: string | null;
  rejection_reason?: string;
  status?: string;
  title?: string;
};

type KnowledgeSearchResultItem = {
  chunk_id?: string;
  chunk_index?: number;
  content?: string;
  document_id: string;
  retrieval_mode?: string;
  source?: {
    asset_id?: string;
    chunk_id?: string;
    chunk_set_id?: string;
    doc_type?: string;
    folder_id?: string;
    knowledge_space_id?: string;
    parent_chunk_id?: string;
    parent_content?: string;
    title?: string;
  };
  title?: string;
};

type KnowledgeIndexHealthIssueItem = {
  action?: string;
  description?: string;
  document_id: string;
  index_error?: string | null;
  knowledge_space_id?: string | null;
  label?: string;
  severity?: string;
  status?: string;
  title?: string;
  updated_at?: string;
  vector_index_error?: string | null;
};

type KnowledgeIndexHealthItem = {
  embedding_models?: Array<{
    count?: number;
    dimension?: number | null;
    model?: string;
  }>;
  import_job_counts?: Array<{ count?: number; status?: string }>;
  issues?: KnowledgeIndexHealthIssueItem[];
  performance?: RemoteListPerformance;
  permission_scope?: {
    filter_role?: string | null;
    global_knowledge_access?: boolean;
    knowledge_space_scope_ids?: string[];
    matched_roles?: string[];
    mode?: string;
    readable_role_count?: number;
    scope_labels?: string[];
  };
  retrieval_modes?: {
    hybrid_ready?: number;
    keyword_fallback?: number;
    unavailable?: number;
  };
  status_counts?: Array<{ count?: number; status?: string }>;
  summary?: {
    chunk_ready_documents?: number;
    embedding_ready_chunks?: number;
    index_failed_documents?: number;
    keyword_only_chunks?: number;
    keyword_only_documents?: number;
    missing_chunk_documents?: number;
    processing_documents?: number;
    searchable_documents?: number;
    total_chunks?: number;
    total_documents?: number;
    vector_ready_documents?: number;
  };
};

function formatListDate(value?: string) {
  return formatDisplayDateTime(value);
}

function normalizeKnowledgeStatus(status?: string): KnowledgeRecord['status'] {
  if (
    status === 'archived' ||
    status === 'importing' ||
    status === 'indexed' ||
    status === 'index_failed' ||
    status === 'pending_index' ||
    status === 'text_indexed' ||
    status === 'vector_indexed'
  ) {
    return status;
  }
  if (status === 'failed') {
    return 'index_failed';
  }
  return 'pending_index';
}

export function mapKnowledgeRecord(document: KnowledgeDocumentListItem): KnowledgeRecord {
  return {
    activeChunkSetId: document.active_chunk_set_id ?? undefined,
    content: document.content,
    documentType: document.doc_type ?? '-',
    folderId: document.folder_id ?? undefined,
    folderPath: document.folder_path ?? undefined,
    id: document.id,
    indexError: document.index_error,
    knowledgeSpaceId: document.knowledge_space_id ?? undefined,
    ownerRole: document.permission_roles?.join(', ') || '-',
    permissionRoles: document.permission_roles,
    sourceAssetId: document.source_asset_id ?? undefined,
    status: normalizeKnowledgeStatus(document.index_status),
    tags: document.tags,
    title: document.title,
    updatedAt: formatListDate(document.updated_at ?? document.created_at),
    vectorIndexError: document.vector_index_error,
  };
}

function mapKnowledgeSpace(item: KnowledgeSpaceListItem): KnowledgeSpaceRecord {
  return {
    code: item.code,
    description: item.description,
    id: item.id,
    name: item.name,
  };
}

function mapKnowledgeFolder(item: KnowledgeFolderListItem): KnowledgeFolderRecord {
  return {
    id: item.id,
    knowledgeSpaceId: item.knowledge_space_id,
    name: item.name,
    parentFolderId: item.parent_folder_id,
    path: item.path ?? item.name,
  };
}

function mapKnowledgeAsset(item: KnowledgeAssetListItem): KnowledgeAssetRecord {
  return {
    assetType: item.asset_type ?? '-',
    filename: item.filename ?? item.id,
    id: item.id,
    mimeType: item.mime_type,
    sizeBytes: Number(item.size_bytes ?? 0),
    storageProvider: item.storage_provider,
  };
}

function mapKnowledgeImportJob(item: KnowledgeImportJobListItem): KnowledgeImportJobRecord {
  return {
    assetFilename: item.asset_filename,
    chunkStrategy: item.chunk_strategy,
    documentId: item.document_id,
    documentTitle: item.document_title,
    errorMessage: item.error_message ?? undefined,
    folderPath: item.folder_path,
    id: item.id,
    parserEngine: item.parser_engine,
    progress: Number(item.progress ?? 0),
    status: item.status ?? '-',
    updatedAt: formatListDate(item.updated_at),
  };
}

function mapKnowledgeChunkSet(item: KnowledgeChunkSetListItem): KnowledgeChunkSetRecord {
  return {
    activatedAt: formatListDate(item.activated_at),
    chunkCount: Number(item.chunk_count ?? 0),
    chunkStrategy: item.chunk_strategy ?? '-',
    id: item.id,
    isActive: Boolean(item.is_active),
    parserEngine: item.parser_engine ?? '-',
    status: item.status ?? '-',
  };
}

function mapKnowledgeChunk(item: KnowledgeChunkListItem): KnowledgeChunkRecord {
  return {
    chunkIndex: Number(item.chunk_index ?? 0),
    chunkRole: item.metadata?.chunk_role,
    chunkSetId: item.chunk_set_id,
    content: item.content ?? '',
    heading: item.metadata?.heading,
    id: item.id,
    imageCount: item.metadata?.image_count,
    imageRefs: item.metadata?.image_refs,
    parentChunkId: item.parent_chunk_id,
    parentContent: item.parent_content,
    pageNumber: item.metadata?.page_number,
    sectionTitle: item.metadata?.section_title,
    sourceAssetType: item.metadata?.source_asset_type,
    sourceKind: item.metadata?.source_kind,
    splitPattern: item.metadata?.split_pattern,
    tableColumns: item.metadata?.columns,
    tableCount: item.metadata?.table_count,
    tableIndex: item.metadata?.table_index,
  };
}

function mapKnowledgeImportWorkerStatus(
  item: KnowledgeImportWorkerStatusItem,
): KnowledgeImportWorkerStatusRecord {
  return {
    activeJobId: item.active_job_id ?? null,
    enabled: Boolean(item.enabled),
    failedCount: Number(item.failed_count ?? 0),
    pendingCount: Number(item.pending_count ?? 0),
    processedCount: Number(item.processed_count ?? 0),
    queuedJobIds: item.queued_job_ids ?? [],
    running: Boolean(item.running),
    workerId: item.worker_id ?? null,
  };
}

export function mapKnowledgeDeposit(deposit: KnowledgeDepositListItem): KnowledgeDepositRecord {
  return {
    aiTaskId: deposit.ai_task_id,
    content: deposit.content ?? '-',
    id: deposit.id,
    knowledgeDocumentId: deposit.knowledge_document_id,
    rejectionReason: deposit.rejection_reason,
    status: deposit.status ?? '-',
    title: deposit.title ?? deposit.id,
  };
}

function mapKnowledgeSearchResult(
  item: KnowledgeSearchResultItem,
  index: number,
): KnowledgeSearchResultRecord {
  const sourceParts = [
    item.source?.doc_type,
    item.source?.title,
    item.chunk_index ? `chunk ${item.chunk_index}` : undefined,
  ].filter(Boolean);
  return {
    chunkId: item.chunk_id ?? item.source?.chunk_id,
    chunkIndex: item.chunk_index,
    content: item.content ?? '-',
    documentId: item.document_id,
    id: item.chunk_id ?? `${item.document_id}:${index}`,
    parentChunkId: item.source?.parent_chunk_id,
    parentContent: item.source?.parent_content,
    retrievalMode: item.retrieval_mode === 'vector' ? 'vector' : 'keyword',
    sourceLabel: sourceParts.length ? sourceParts.join(' · ') : '-',
    title: item.title ?? item.document_id,
  };
}

function normalizeKnowledgeHealthAction(
  action?: string,
): KnowledgeIndexHealthIssueRecord['action'] {
  if (action === 'open_chunks' || action === 'open_import_jobs' || action === 'retry_index') {
    return action;
  }
  return 'retry_index';
}

function normalizeKnowledgeHealthSeverity(
  severity?: string,
): KnowledgeIndexHealthIssueRecord['severity'] {
  if (severity === 'error' || severity === 'processing' || severity === 'warning') {
    return severity;
  }
  return 'warning';
}

function mapKnowledgeIndexHealth(item: KnowledgeIndexHealthItem): KnowledgeIndexHealthRecord {
  const summary = item.summary ?? {};
  return {
    embeddingModels: (item.embedding_models ?? []).map((model) => ({
      count: Number(model.count ?? 0),
      dimension: model.dimension,
      model: model.model ?? 'not_configured',
    })),
    importJobCounts: (item.import_job_counts ?? []).map((count) => ({
      count: Number(count.count ?? 0),
      status: count.status ?? 'unknown',
    })),
    issues: (item.issues ?? []).map((issue) => ({
      action: normalizeKnowledgeHealthAction(issue.action),
      description: issue.description ?? '-',
      documentId: issue.document_id,
      indexError: issue.index_error,
      knowledgeSpaceId: issue.knowledge_space_id,
      label: issue.label ?? '-',
      severity: normalizeKnowledgeHealthSeverity(issue.severity),
      status: normalizeKnowledgeStatus(issue.status),
      title: issue.title ?? issue.document_id,
      updatedAt: formatListDate(issue.updated_at),
      vectorIndexError: issue.vector_index_error,
    })),
    performance: item.performance,
    permissionScope: item.permission_scope
      ? {
          filterRole: item.permission_scope.filter_role,
          globalKnowledgeAccess: Boolean(item.permission_scope.global_knowledge_access),
          knowledgeSpaceScopeIds: item.permission_scope.knowledge_space_scope_ids ?? [],
          matchedRoles: item.permission_scope.matched_roles ?? [],
          mode: item.permission_scope.mode ?? 'unknown',
          readableRoleCount: Number(item.permission_scope.readable_role_count ?? 0),
          scopeLabels: item.permission_scope.scope_labels ?? [],
        }
      : undefined,
    retrievalModes: {
      hybridReady: Number(item.retrieval_modes?.hybrid_ready ?? 0),
      keywordFallback: Number(item.retrieval_modes?.keyword_fallback ?? 0),
      unavailable: Number(item.retrieval_modes?.unavailable ?? 0),
    },
    statusCounts: (item.status_counts ?? []).map((count) => ({
      count: Number(count.count ?? 0),
      status: count.status ?? 'unknown',
    })),
    summary: {
      chunkReadyDocuments: Number(summary.chunk_ready_documents ?? 0),
      embeddingReadyChunks: Number(summary.embedding_ready_chunks ?? 0),
      indexFailedDocuments: Number(summary.index_failed_documents ?? 0),
      keywordOnlyChunks: Number(summary.keyword_only_chunks ?? 0),
      keywordOnlyDocuments: Number(summary.keyword_only_documents ?? 0),
      missingChunkDocuments: Number(summary.missing_chunk_documents ?? 0),
      processingDocuments: Number(summary.processing_documents ?? 0),
      searchableDocuments: Number(summary.searchable_documents ?? 0),
      totalChunks: Number(summary.total_chunks ?? 0),
      totalDocuments: Number(summary.total_documents ?? 0),
      vectorReadyDocuments: Number(summary.vector_ready_documents ?? 0),
    },
  };
}

export async function fetchManagementKnowledge(): Promise<KnowledgeRecord[]> {
  const token = requireAccessToken();
  const documents = await apiRequest<ListResponse<KnowledgeDocumentListItem>>(
    '/api/knowledge/documents',
    { token },
  );

  return documents.items.map(mapKnowledgeRecord);
}

export async function fetchManagementKnowledgeList(
  query: KnowledgeListQuery = {},
): Promise<RemoteListResult<KnowledgeRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'doc_type', query.documentType);
  appendQueryParam(params, 'knowledge_space_id', query.knowledgeSpaceId);
  appendQueryParam(params, 'folder_id', query.folderId);
  appendQueryParam(params, 'permission_role', query.ownerRole);
  appendQueryParam(params, 'index_status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const documents = await apiRequest<ListResponse<KnowledgeDocumentListItem>>(
    queryString ? `/api/knowledge/documents?${queryString}` : '/api/knowledge/documents',
    { token },
  );

  return {
    page: documents.page ?? query.page ?? 1,
    pageSize: documents.page_size ?? query.pageSize ?? 10,
    performance: documents.performance,
    rows: documents.items.map(mapKnowledgeRecord),
    total: documents.total,
  };
}

export async function fetchKnowledgeIndexHealth(
  query: KnowledgeListQuery = {},
): Promise<KnowledgeIndexHealthRecord> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'keyword', query.keyword);
  appendQueryParam(params, 'doc_type', query.documentType);
  appendQueryParam(params, 'knowledge_space_id', query.knowledgeSpaceId);
  appendQueryParam(params, 'folder_id', query.folderId);
  appendQueryParam(params, 'permission_role', query.ownerRole);
  appendQueryParam(params, 'index_status', query.status);
  appendQueryParam(params, 'issue_limit', 8);
  const queryString = params.toString();
  const health = await apiRequest<KnowledgeIndexHealthItem>(
    queryString ? `/api/knowledge/index-health?${queryString}` : '/api/knowledge/index-health',
    { token },
  );
  return mapKnowledgeIndexHealth(health);
}

export async function fetchKnowledgeSpaces(): Promise<KnowledgeSpaceRecord[]> {
  const token = requireAccessToken();
  const spaces = await apiRequest<ListResponse<KnowledgeSpaceListItem>>('/api/knowledge/spaces', {
    token,
  });
  return spaces.items.map(mapKnowledgeSpace);
}

export async function createKnowledgeSpace(payload: {
  code: string;
  description?: string;
  name: string;
}): Promise<KnowledgeSpaceRecord> {
  const token = requireAccessToken();
  const space = await apiRequest<KnowledgeSpaceListItem>('/api/knowledge/spaces', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapKnowledgeSpace(space);
}

export async function fetchKnowledgeFolders(spaceId: string): Promise<KnowledgeFolderRecord[]> {
  const token = requireAccessToken();
  const folders = await apiRequest<ListResponse<KnowledgeFolderListItem>>(
    `/api/knowledge/spaces/${spaceId}/folders`,
    { token },
  );
  return folders.items.map(mapKnowledgeFolder);
}

export async function createKnowledgeFolder(
  spaceId: string,
  payload: { name: string; parent_folder_id?: string },
): Promise<KnowledgeFolderRecord> {
  const token = requireAccessToken();
  const folder = await apiRequest<KnowledgeFolderListItem>(
    `/api/knowledge/spaces/${spaceId}/folders`,
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
  return mapKnowledgeFolder(folder);
}

export async function updateKnowledgeFolder(
  folderId: string,
  payload: {
    name?: string;
    parent_folder_id?: string | null;
    sort_order?: number;
    status?: string;
  },
): Promise<KnowledgeFolderRecord> {
  const token = requireAccessToken();
  const folder = await apiRequest<KnowledgeFolderListItem>(`/api/knowledge/folders/${folderId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
  return mapKnowledgeFolder(folder);
}

export async function fetchKnowledgeDocumentAssets(
  documentId: string,
): Promise<KnowledgeAssetRecord[]> {
  const token = requireAccessToken();
  const assets = await apiRequest<ListResponse<KnowledgeAssetListItem>>(
    `/api/knowledge/documents/${documentId}/assets`,
    { token },
  );
  return assets.items.map(mapKnowledgeAsset);
}

export async function fetchKnowledgeImportJobs(params: {
  knowledgeSpaceId?: string;
  status?: string;
} = {}): Promise<KnowledgeImportJobRecord[]> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  appendQueryParam(query, 'knowledge_space_id', params.knowledgeSpaceId);
  appendQueryParam(query, 'status', params.status);
  const queryString = query.toString();
  const importJobs = await apiRequest<ListResponse<KnowledgeImportJobListItem>>(
    queryString ? `/api/knowledge/import-jobs?${queryString}` : '/api/knowledge/import-jobs',
    { token },
  );
  return importJobs.items.map(mapKnowledgeImportJob);
}

export async function fetchKnowledgeImportWorkerStatus(): Promise<KnowledgeImportWorkerStatusRecord> {
  const token = requireAccessToken();
  const status = await apiRequest<KnowledgeImportWorkerStatusItem>(
    '/api/knowledge/import-worker/status',
    { token },
  );
  return mapKnowledgeImportWorkerStatus(status);
}

export async function runKnowledgeImportJob(jobId: string) {
  const token = requireAccessToken();
  return apiRequest<{ import_job: KnowledgeImportJobListItem }>(
    `/api/knowledge/import-jobs/${jobId}/run`,
    { method: 'POST', token },
  );
}

export async function retryKnowledgeImportJob(jobId: string) {
  const token = requireAccessToken();
  return apiRequest<{ import_job: KnowledgeImportJobListItem }>(
    `/api/knowledge/import-jobs/${jobId}/retry`,
    { method: 'POST', token },
  );
}

export async function cancelKnowledgeImportJob(jobId: string) {
  const token = requireAccessToken();
  return apiRequest<{ import_job: KnowledgeImportJobListItem }>(
    `/api/knowledge/import-jobs/${jobId}/cancel`,
    { method: 'POST', token },
  );
}

export async function fetchKnowledgeChunkSets(
  documentId: string,
): Promise<KnowledgeChunkSetRecord[]> {
  const token = requireAccessToken();
  const chunkSets = await apiRequest<ListResponse<KnowledgeChunkSetListItem>>(
    `/api/knowledge/documents/${documentId}/chunk-sets`,
    { token },
  );
  return chunkSets.items.map(mapKnowledgeChunkSet);
}

export async function fetchKnowledgeChunks(
  documentId: string,
  chunkSetId?: string,
): Promise<KnowledgeChunkRecord[]> {
  const token = requireAccessToken();
  const query = new URLSearchParams();
  appendQueryParam(query, 'chunk_set_id', chunkSetId);
  const queryString = query.toString();
  const chunks = await apiRequest<ListResponse<KnowledgeChunkListItem>>(
    queryString
      ? `/api/knowledge/documents/${documentId}/chunks?${queryString}`
      : `/api/knowledge/documents/${documentId}/chunks`,
    { token },
  );
  return chunks.items.map(mapKnowledgeChunk);
}

export async function activateKnowledgeChunkSet(documentId: string, chunkSetId: string) {
  const token = requireAccessToken();
  return apiRequest<{ document: KnowledgeDocumentListItem }>(
    `/api/knowledge/documents/${documentId}/chunk-sets/${chunkSetId}/activate`,
    { method: 'POST', token },
  );
}

export async function reparseKnowledgeDocument(
  documentId: string,
  payload: { chunk_strategy?: string; parser_engine?: string },
) {
  const token = requireAccessToken();
  return apiRequest<{ import_job: KnowledgeImportJobListItem }>(
    `/api/knowledge/documents/${documentId}/reparse`,
    { body: payload, method: 'POST', token },
  );
}

export async function batchMoveKnowledgeDocuments(documentIds: string[], folderId?: string | null) {
  const token = requireAccessToken();
  return apiRequest<{ skipped: Array<{ id: string; reason: string }>; updated: string[] }>(
    '/api/knowledge/documents/batch-move',
    {
      body: { document_ids: documentIds, folder_id: folderId ?? null },
      method: 'POST',
      token,
    },
  );
}

export async function uploadKnowledgeDocument(payload: KnowledgeDocumentUploadPayload) {
  const token = requireAccessToken();
  return apiRequest<{ document: KnowledgeDocumentListItem }>('/api/knowledge/documents/upload', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function createManagementKnowledgeDocument(payload: KnowledgeDocumentMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<{ id: string }>('/api/knowledge/documents', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateManagementKnowledgeDocument(
  documentId: string,
  payload: KnowledgeDocumentMutationPayload,
) {
  const token = requireAccessToken();
  return apiRequest<{ id: string }>(`/api/knowledge/documents/${documentId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteManagementKnowledgeDocument(documentId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/knowledge/documents/${documentId}`, {
    method: 'DELETE',
    token,
  });
}

export async function retryKnowledgeDocumentIndex(documentId: string) {
  const token = requireAccessToken();
  return apiRequest<{ id: string; index_error?: string | null; index_status?: string }>(
    `/api/knowledge/documents/${documentId}/retry-index`,
    {
      method: 'POST',
      token,
    },
  );
}

export async function fetchKnowledgeDeposits(
  status = 'pending',
): Promise<KnowledgeDepositRecord[]> {
  const token = requireAccessToken();
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  const deposits = await apiRequest<ListResponse<KnowledgeDepositListItem>>(
    `/api/knowledge/deposits${query}`,
    { token },
  );
  return deposits.items.map(mapKnowledgeDeposit);
}

export async function fetchKnowledgeSearchResults(
  query: string,
  topK = 5,
  knowledgeSpaceId?: string,
): Promise<KnowledgeSearchResultRecord[]> {
  const token = requireAccessToken();
  const results = await apiRequest<ListResponse<KnowledgeSearchResultItem>>(
    '/api/knowledge/search',
    {
      body: {
        knowledge_space_id: knowledgeSpaceId,
        query,
        top_k: topK,
      },
      method: 'POST',
      token,
    },
  );
  return results.items.map(mapKnowledgeSearchResult);
}

export async function approveKnowledgeDeposit(
  depositId: string,
  payload: KnowledgeDepositApprovePayload = {},
): Promise<KnowledgeDepositRecord> {
  const token = requireAccessToken();
  const deposit = await apiRequest<KnowledgeDepositListItem>(
    `/api/knowledge/deposits/${depositId}/approve`,
    {
      body: {
        permission_roles: payload.permissionRoles ?? ['admin'],
        title: payload.title,
      },
      method: 'POST',
      token,
    },
  );
  return mapKnowledgeDeposit(deposit);
}

export async function rejectKnowledgeDeposit(
  depositId: string,
  reason: string,
): Promise<KnowledgeDepositRecord> {
  const token = requireAccessToken();
  const deposit = await apiRequest<KnowledgeDepositListItem>(
    `/api/knowledge/deposits/${depositId}/reject`,
    {
      body: { reason },
      method: 'POST',
      token,
    },
  );
  return mapKnowledgeDeposit(deposit);
}
