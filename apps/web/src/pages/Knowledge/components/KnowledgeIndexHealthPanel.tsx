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

const knowledgeStatusLabels: Record<string, string> = {
  archived: '已归档',
  importing: '索引中',
  indexed: '已索引',
  index_failed: '索引失败',
  pending_index: '待索引',
  text_indexed: '文本索引',
  vector_indexed: '向量索引',
};

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

type KnowledgeGovernanceSection = {
  detail: string;
  facts: string[];
  key: string;
  label: string;
  status: {
    color: string;
    label: string;
  };
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

function formatDocumentStatusCounts(record: KnowledgeIndexHealthRecord | undefined, rows: KnowledgeRecord[]) {
  const counts = record?.statusCounts?.length
    ? record.statusCounts
    : Object.entries(
        rows.reduce<Record<string, number>>((accumulator, row) => {
          accumulator[row.status] = (accumulator[row.status] ?? 0) + 1;
          return accumulator;
        }, {}),
      ).map(([status, count]) => ({ count, status }));
  if (!counts.length) {
    return record ? '无文档' : '当前页无文档';
  }
  return counts
    .map((item) => `${knowledgeStatusLabels[item.status] ?? item.status} ${item.count}`)
    .join('、');
}

function formatChunkEmbeddingCoverage(summary: KnowledgeHealthSummary, record?: KnowledgeIndexHealthRecord) {
  const totalChunks = Number(record?.summary.totalChunks ?? 0);
  const embeddingReadyChunks = Number(record?.summary.embeddingReadyChunks ?? 0);
  const embeddingCoverage = totalChunks > 0 ? `${Math.round((embeddingReadyChunks / totalChunks) * 100)}%` : '-';
  return [
    `分块文档 ${summary.chunkReadyCount}`,
    `缺分块 ${summary.missingChunkCount}`,
    `Chunk ${record ? totalChunks : '-'}`,
    `Embedding ${record ? embeddingReadyChunks : '-'}`,
    `覆盖率 ${embeddingCoverage}`,
  ].join(' · ');
}

function formatRetrievalModes(record?: KnowledgeIndexHealthRecord) {
  if (!record) {
    return '当前页推断';
  }
  const { hybridReady, keywordFallback, unavailable } = record.retrievalModes;
  return `混合 ${hybridReady} · 关键词 ${keywordFallback} · 不可用 ${unavailable}`;
}

function formatPermissionScope(record?: KnowledgeIndexHealthRecord) {
  if (!record?.permissionScope) {
    return '当前页推断';
  }
  const labels = record.permissionScope.scopeLabels.filter(Boolean);
  if (labels.length > 0) {
    return labels.join('、');
  }
  if (record.permissionScope.knowledgeSpaceScopeIds.length > 0) {
    return `知识空间 ${record.permissionScope.knowledgeSpaceScopeIds.length} 个`;
  }
  return record.permissionScope.globalKnowledgeAccess ? '全局知识权限' : '无命中说明';
}

function buildKnowledgeGovernanceSections(
  summary: KnowledgeHealthSummary,
  record: KnowledgeIndexHealthRecord | undefined,
  rows: KnowledgeRecord[],
): KnowledgeGovernanceSection[] {
  const totalChunks = Number(record?.summary.totalChunks ?? 0);
  const embeddingReadyChunks = Number(record?.summary.embeddingReadyChunks ?? 0);
  const parseStatus =
    summary.failedCount > 0
      ? { color: 'red', label: '失败待处理' }
      : summary.pendingCount > 0
        ? { color: 'blue', label: '解析中' }
        : summary.total > 0
          ? { color: 'green', label: '解析可用' }
          : { color: 'default', label: '暂无文档' };
  const chunkStatus =
    summary.missingChunkCount > 0
      ? { color: 'gold', label: '分块待补' }
      : totalChunks > 0
        ? { color: 'green', label: '分块可用' }
        : { color: 'default', label: '暂无 Chunk' };
  const embeddingStatus =
    summary.searchableCount > 0 && summary.vectorReadyCount === 0
      ? { color: 'gold', label: '关键词兜底' }
      : embeddingReadyChunks > 0
        ? { color: 'green', label: '向量可用' }
        : chunkStatus;
  const retrievalUsable = Number(record?.retrievalModes.hybridReady ?? 0) + Number(record?.retrievalModes.keywordFallback ?? 0);
  const retrievalStatus =
    Number(record?.retrievalModes.unavailable ?? 0) > 0
      ? { color: 'red', label: '存在不可用' }
      : retrievalUsable > 0
        ? { color: 'green', label: '检索可用' }
        : { color: 'default', label: '等待索引' };

  return [
    {
      detail: `状态分布：${formatDocumentStatusCounts(record, rows)}`,
      facts: [`失败 ${summary.failedCount}`, `处理中 ${summary.pendingCount}`, `可检索 ${summary.searchableCount}`],
      key: 'parse',
      label: '解析状态',
      status: parseStatus,
    },
    {
      detail: formatChunkEmbeddingCoverage(summary, record),
      facts: [`分块文档 ${summary.chunkReadyCount}`, `向量文档 ${summary.vectorReadyCount}`, `缺分块 ${summary.missingChunkCount}`],
      key: 'chunk_embedding',
      label: 'Chunk & Embedding',
      status: embeddingStatus,
    },
    {
      detail: `权限命中：${formatPermissionScope(record)}`,
      facts: [formatRetrievalModes(record), `模型：${formatEmbeddingModels(record)}`],
      key: 'retrieval_permission',
      label: '检索与权限',
      status: retrievalStatus,
    },
  ];
}

function issueActionText(issue: KnowledgeHealthIssue) {
  if (issue.action === 'open_chunks') {
    return '查看分块';
  }
  if (issue.action === 'open_import_jobs') {
    return '导入任务';
  }
  return issue.document.status === 'text_indexed' ? '补向量' : '重试索引';
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
  const governanceSections = buildKnowledgeGovernanceSections(summary, healthState.record, listRows);
  const healthStatus =
    summary.failedCount > 0
      ? { color: 'red', label: '需处理' }
      : summary.keywordOnlyCount > 0 || summary.missingChunkCount > 0
        ? { color: 'gold', label: '可优化' }
        : { color: 'green', label: '正常' };

  const renderAction = (issue: KnowledgeHealthIssue) => {
    const actionText = issueActionText(issue);
    if (issue.action === 'retry_index') {
      return (
        <Button
          aria-label={`${actionText} ${issue.document.title}`}
          onClick={() => void onRetryIndex(issue.document)}
          size="small"
          type="link"
        >
          {actionText}
        </Button>
      );
    }
    if (issue.action === 'open_chunks') {
      return (
        <Button
          aria-label={`${actionText} ${issue.document.title}`}
          onClick={() => onOpenChunks(issue.document)}
          size="small"
          type="link"
        >
          {actionText}
        </Button>
      );
    }
    return (
      <Button
        aria-label={`${actionText} ${issue.document.title}`}
        onClick={onOpenImportJobs}
        size="small"
        type="link"
      >
        {actionText}
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
      <div className="knowledge-health-governance" role="list">
        {governanceSections.map((section) => (
          <div className="knowledge-health-governance-card" key={section.key} role="listitem">
            <div className="knowledge-health-governance-title">
              <Text strong>{section.label}</Text>
              <StatusTag color={section.status.color} label={section.status.label} />
            </div>
            <Text type="secondary">{section.detail}</Text>
            <div className="knowledge-health-governance-facts">
              {section.facts.map((fact) => (
                <span key={fact}>{fact}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="knowledge-health-signals">
        <Text type="secondary">文档状态：{formatDocumentStatusCounts(healthState.record, listRows)}</Text>
        <Text type="secondary">Chunk / Embedding：{formatChunkEmbeddingCoverage(summary, healthState.record)}</Text>
        <Text type="secondary">召回模式：{formatRetrievalModes(healthState.record)}</Text>
        <Text type="secondary">权限命中：{formatPermissionScope(healthState.record)}</Text>
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
                <Text type="secondary">
                  {knowledgeStatusLabels[issue.document.status] ?? issue.document.status} · {issueActionText(issue)}
                </Text>
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
