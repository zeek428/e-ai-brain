import { Button, Space, Typography } from 'antd';

import { StatusTag } from '../../../components/ManagementListPage';
import type { KnowledgeRecord } from '../../../data/management';
import type { KnowledgeIndexHealthRecord } from '../../../services/aiBrain';

const { Text } = Typography;

const searchableKnowledgeStatuses = new Set<KnowledgeRecord['status']>([
  'indexed',
  'text_indexed',
  'vector_indexed',
]);

type KnowledgeHealthIssue = {
  action: 'open_chunks' | 'open_import_jobs' | 'retry_index';
  description: string;
  document: KnowledgeRecord;
  key: string;
  label: string;
  severity: 'error' | 'processing' | 'warning';
  title: string;
};

type KnowledgeHealthSummary = {
  chunkReadyCount: number;
  failedCount: number;
  healthIssues: KnowledgeHealthIssue[];
  keywordOnlyCount: number;
  missingChunkCount: number;
  pendingCount: number;
  searchableCount: number;
  total: number;
  vectorReadyCount: number;
};

export type KnowledgeIndexHealthState = {
  error?: string;
  record?: KnowledgeIndexHealthRecord;
  status: 'error' | 'loading' | 'ready';
};

type KnowledgeIndexHealthPanelProps = {
  healthState: KnowledgeIndexHealthState;
  listRows: KnowledgeRecord[];
  listTotal: number;
  onOpenChunks: (document: KnowledgeRecord) => void;
  onOpenImportJobs: () => void;
  onRetryIndex: (document: KnowledgeRecord) => void | Promise<void>;
};

function buildKnowledgeHealthSummary(rows: KnowledgeRecord[]): KnowledgeHealthSummary {
  const failedDocuments = rows.filter((row) => row.status === 'index_failed');
  const pendingDocuments = rows.filter((row) => row.status === 'importing' || row.status === 'pending_index');
  const keywordOnlyDocuments = rows.filter((row) => row.status === 'text_indexed');
  const vectorReadyDocuments = rows.filter((row) => row.status === 'indexed' || row.status === 'vector_indexed');
  const chunkReadyDocuments = rows.filter((row) => Boolean(row.activeChunkSetId));
  const missingChunkDocuments = rows.filter(
    (row) => searchableKnowledgeStatuses.has(row.status) && !row.activeChunkSetId,
  );
  const searchableDocuments = rows.filter((row) => searchableKnowledgeStatuses.has(row.status));
  const healthIssues: KnowledgeHealthIssue[] = [
    ...failedDocuments.map<KnowledgeHealthIssue>((document) => ({
      action: 'retry_index',
      description: document.indexError || document.vectorIndexError || '索引任务失败，需重试或检查模型网关。',
      document,
      key: `failed-${document.id}`,
      label: '索引失败',
      severity: 'error',
      title: document.title,
    })),
    ...keywordOnlyDocuments.map<KnowledgeHealthIssue>((document) => ({
      action: 'retry_index',
      description: document.vectorIndexError || '当前可通过关键词检索，向量索引未完成。',
      document,
      key: `keyword-only-${document.id}`,
      label: '向量待补',
      severity: 'warning',
      title: document.title,
    })),
    ...missingChunkDocuments.map<KnowledgeHealthIssue>((document) => ({
      action: 'open_chunks',
      description: '文档处于可检索状态，但没有生效分块版本。',
      document,
      key: `missing-chunks-${document.id}`,
      label: '分块缺失',
      severity: 'warning',
      title: document.title,
    })),
    ...pendingDocuments.map<KnowledgeHealthIssue>((document) => ({
      action: 'open_import_jobs',
      description: '导入或索引任务仍在排队/处理中。',
      document,
      key: `pending-${document.id}`,
      label: '处理中',
      severity: 'processing',
      title: document.title,
    })),
  ].slice(0, 6);

  return {
    chunkReadyCount: chunkReadyDocuments.length,
    failedCount: failedDocuments.length,
    healthIssues,
    keywordOnlyCount: keywordOnlyDocuments.length,
    missingChunkCount: missingChunkDocuments.length,
    pendingCount: pendingDocuments.length,
    searchableCount: searchableDocuments.length,
    total: rows.length,
    vectorReadyCount: vectorReadyDocuments.length,
  };
}

function remoteIssueDocument(
  issue: KnowledgeIndexHealthRecord['issues'][number],
  rowsById: Map<string, KnowledgeRecord>,
): KnowledgeRecord {
  const currentPageDocument = rowsById.get(issue.documentId);
  if (currentPageDocument) {
    return currentPageDocument;
  }
  return {
    documentType: '-',
    id: issue.documentId,
    indexError: issue.indexError,
    knowledgeSpaceId: issue.knowledgeSpaceId ?? undefined,
    ownerRole: '-',
    permissionRoles: [],
    status: issue.status,
    title: issue.title,
    updatedAt: issue.updatedAt ?? '-',
    vectorIndexError: issue.vectorIndexError,
  };
}

function buildRemoteKnowledgeHealthSummary(
  health: KnowledgeIndexHealthRecord,
  rows: KnowledgeRecord[],
): KnowledgeHealthSummary {
  const rowsById = new Map(rows.map((row) => [row.id, row]));
  return {
    chunkReadyCount: health.summary.chunkReadyDocuments,
    failedCount: health.summary.indexFailedDocuments,
    healthIssues: health.issues.map((issue) => ({
      action: issue.action,
      description: issue.description,
      document: remoteIssueDocument(issue, rowsById),
      key: `health-${issue.documentId}-${issue.label}`,
      label: issue.label,
      severity: issue.severity,
      title: issue.title,
    })),
    keywordOnlyCount: health.summary.keywordOnlyDocuments,
    missingChunkCount: health.summary.missingChunkDocuments,
    pendingCount: health.summary.processingDocuments,
    searchableCount: health.summary.searchableDocuments,
    total: health.summary.totalDocuments,
    vectorReadyCount: health.summary.vectorReadyDocuments,
  };
}

function buildKnowledgeHealthMetrics(summary: KnowledgeHealthSummary, record?: KnowledgeIndexHealthRecord) {
  return [
    { key: 'total', label: '范围文档', value: summary.total },
    { key: 'searchable', label: '可检索', value: summary.searchableCount },
    { key: 'vector_ready', label: '向量就绪', value: summary.vectorReadyCount },
    { key: 'keyword_only', label: '关键词兜底', value: summary.keywordOnlyCount },
    { key: 'failed', label: '索引失败', value: summary.failedCount },
    { key: 'pending', label: '处理中', value: summary.pendingCount },
    { key: 'chunk_ready', label: '分块版本', value: summary.chunkReadyCount },
    { key: 'chunks', label: 'Chunk', value: record?.summary.totalChunks ?? '-' },
    { key: 'embedding_chunks', label: 'Embedding', value: record?.summary.embeddingReadyChunks ?? '-' },
    { key: 'hybrid_retrieval', label: '混合召回', value: record?.retrievalModes.hybridReady ?? '-' },
  ];
}

function formatEmbeddingModels(record?: KnowledgeIndexHealthRecord) {
  if (!record || record.embeddingModels.length === 0) {
    return '未统计';
  }
  return record.embeddingModels
    .map((model) => `${model.model}${model.dimension ? `/${model.dimension}维` : ''} ${model.count}`)
    .join('、');
}

function formatImportJobs(record?: KnowledgeIndexHealthRecord) {
  if (!record || record.importJobCounts.length === 0) {
    return '无导入任务';
  }
  return record.importJobCounts.map((job) => `${job.status} ${job.count}`).join('、');
}

function formatRetrievalModes(record?: KnowledgeIndexHealthRecord) {
  if (!record) {
    return '当前页推断';
  }
  const { hybridReady, keywordFallback, unavailable } = record.retrievalModes;
  return `混合 ${hybridReady} · 关键词 ${keywordFallback} · 不可用 ${unavailable}`;
}

export function KnowledgeIndexHealthPanel({
  healthState,
  listRows,
  listTotal,
  onOpenChunks,
  onOpenImportJobs,
  onRetryIndex,
}: KnowledgeIndexHealthPanelProps) {
  const localSummary = buildKnowledgeHealthSummary(listRows);
  const summary = healthState.record
    ? buildRemoteKnowledgeHealthSummary(healthState.record, listRows)
    : localSummary;
  const healthMetrics = buildKnowledgeHealthMetrics(summary, healthState.record);
  const healthStatus =
    summary.failedCount > 0
      ? { color: 'red', label: '需处理' }
      : summary.keywordOnlyCount > 0 || summary.missingChunkCount > 0
        ? { color: 'gold', label: '可优化' }
        : { color: 'green', label: '正常' };

  const renderAction = (issue: KnowledgeHealthIssue) => {
    if (issue.action === 'retry_index') {
      return (
        <Button
          aria-label={`处理索引健康问题 ${issue.document.title}`}
          onClick={() => void onRetryIndex(issue.document)}
          size="small"
          type="link"
        >
          处理
        </Button>
      );
    }
    if (issue.action === 'open_chunks') {
      return (
        <Button
          aria-label={`查看分块健康问题 ${issue.document.title}`}
          onClick={() => onOpenChunks(issue.document)}
          size="small"
          type="link"
        >
          分块
        </Button>
      );
    }
    return (
      <Button
        aria-label={`查看导入任务 ${issue.document.title}`}
        onClick={onOpenImportJobs}
        size="small"
        type="link"
      >
        导入任务
      </Button>
    );
  };

  return (
    <section aria-label="知识索引健康" className="knowledge-health-panel">
      <div className="knowledge-health-header">
        <Space size={8} wrap>
          <Text strong>索引健康</Text>
          <StatusTag color={healthStatus.color} label={healthStatus.label} />
        </Space>
        <Space size={8} wrap>
          {healthState.status === 'loading' ? <StatusTag color="blue" label="刷新中" /> : null}
          {healthState.status === 'error' ? <StatusTag color="red" label="健康统计失败" /> : null}
          <Text type="secondary">
            当前筛选范围 · 列表 {listTotal} 条
            {healthState.record?.performance?.duration_ms !== undefined
              ? ` · 健康统计 ${healthState.record.performance.duration_ms}ms`
              : ' · 当前页兜底'}
          </Text>
        </Space>
      </div>
      <div className="knowledge-health-metrics" role="list">
        {healthMetrics.map((metric) => (
          <div className="knowledge-health-metric" key={metric.key} role="listitem">
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </div>
        ))}
      </div>
      <div className="knowledge-health-signals">
        <Text type="secondary">召回模式：{formatRetrievalModes(healthState.record)}</Text>
        <Text type="secondary">Embedding 模型：{formatEmbeddingModels(healthState.record)}</Text>
        <Text type="secondary">导入任务：{formatImportJobs(healthState.record)}</Text>
      </div>
      <div className="knowledge-health-issues">
        {summary.healthIssues.length > 0 ? (
          summary.healthIssues.map((issue) => (
            <div className="knowledge-health-issue" key={issue.key}>
              <StatusTag
                color={
                  issue.severity === 'error'
                    ? 'red'
                    : issue.severity === 'processing'
                      ? 'blue'
                      : 'gold'
                }
                label={issue.label}
              />
              <div className="knowledge-health-issue-content">
                <Text strong>{issue.title}</Text>
                <Text type="secondary">{issue.description}</Text>
              </div>
              {renderAction(issue)}
            </div>
          ))
        ) : (
          <Text type="secondary">
            {healthState.error ?? '当前筛选范围没有索引失败、向量待补或分块缺失文档。'}
          </Text>
        )}
      </div>
    </section>
  );
}
