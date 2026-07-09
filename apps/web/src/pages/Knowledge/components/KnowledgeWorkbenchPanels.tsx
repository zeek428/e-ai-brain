import { CheckOutlined, CloseOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, InputNumber, Select, Space, Tabs, Typography } from 'antd';
import type { ReactNode } from 'react';

import { StatusTag } from '../../../components/ManagementListPage';
import type { KnowledgeRecord } from '../../../data/management';
import type {
  KnowledgeDepositRecord,
  KnowledgeFolderRecord,
  KnowledgeImportJobRecord,
  KnowledgeImportWorkerStatusRecord,
  KnowledgeQualityFeedbackValue,
  KnowledgeRagAnswerRecord,
  KnowledgeRagCitationRecord,
  KnowledgeSearchResultRecord,
  KnowledgeSpaceRecord,
} from '../../../services/aiBrain';
import type {
  KnowledgeQuickSearchFormValues,
  KnowledgeSearchFormValues,
  KnowledgeWorkbenchTab,
} from '../types';
import type { KnowledgeIndexHealthState } from './KnowledgeIndexHealthPanel';

const { Text } = Typography;

type KnowledgeWorkbenchPanelsProps = {
  activeWorkbenchTab: KnowledgeWorkbenchTab;
  depositColumns: ProColumns<KnowledgeDepositRecord>[];
  depositRows: KnowledgeDepositRecord[];
  depositsLoading: boolean;
  folders: KnowledgeFolderRecord[];
  hasSearched: boolean;
  hiddenNoisySpaceCount: number;
  importJobColumns: ProColumns<KnowledgeImportJobRecord>[];
  importJobRows: KnowledgeImportJobRecord[];
  importJobsLoading: boolean;
  importWorkerStatus: KnowledgeImportWorkerStatusRecord | null;
  importWorkerStatusLoading: boolean;
  knowledgeHealthPanel: ReactNode;
  knowledgeHealthState: KnowledgeIndexHealthState;
  listRows: KnowledgeRecord[];
  listTotal: number;
  onCreateFolder: () => void;
  onOpenSearch: () => void;
  onReloadDeposits: () => void;
  onReloadImportJobs: (spaceId?: string) => void;
  onReloadImportWorkerStatus: () => void;
  onRecordCitationClick: (citation: KnowledgeRagCitationRecord) => void | Promise<void>;
  onSearch: (values: KnowledgeSearchFormValues) => void | Promise<void>;
  onSelectFolder: (folderId?: string) => void;
  onSelectSpace: (spaceId: string) => void;
  onSetActiveWorkbenchTab: (tab: KnowledgeWorkbenchTab) => void;
  onSetSelectedSpaceId: (spaceId?: string) => void;
  onSubmitRagFeedback: (feedbackValue: KnowledgeQualityFeedbackValue) => void | Promise<void>;
  onToggleNoisySpaces: () => void;
  onUpdateSpaceSearchText: (value: string) => void;
  onWorkbenchTabChange: (tabKey: string) => void;
  ragAnswer: KnowledgeRagAnswerRecord | null;
  ragFeedbackSubmittingValue?: KnowledgeQualityFeedbackValue;
  ragFeedbackValue?: KnowledgeQualityFeedbackValue;
  searchColumns: ProColumns<KnowledgeSearchResultRecord>[];
  searchLoading: boolean;
  searchRows: KnowledgeSearchResultRecord[];
  selectedFolderId?: string;
  selectedSpace?: KnowledgeSpaceRecord;
  selectedSpaceId?: string;
  showNoisySpaces: boolean;
  spaceOptions: { label: string; value: string }[];
  spaceSearchText: string;
  spaces: KnowledgeSpaceRecord[];
  visibleSpaces: KnowledgeSpaceRecord[];
};

const KNOWLEDGE_DEPOSIT_TABLE_SCROLL_X = 1120;

export function KnowledgeWorkbenchPanels({
  activeWorkbenchTab,
  depositColumns,
  depositRows,
  depositsLoading,
  folders,
  hasSearched,
  hiddenNoisySpaceCount,
  importJobColumns,
  importJobRows,
  importJobsLoading,
  importWorkerStatus,
  importWorkerStatusLoading,
  knowledgeHealthPanel,
  knowledgeHealthState,
  listRows,
  listTotal,
  onCreateFolder,
  onOpenSearch,
  onReloadDeposits,
  onReloadImportJobs,
  onReloadImportWorkerStatus,
  onRecordCitationClick,
  onSearch,
  onSelectFolder,
  onSelectSpace,
  onSetActiveWorkbenchTab,
  onSetSelectedSpaceId,
  onSubmitRagFeedback,
  onToggleNoisySpaces,
  onUpdateSpaceSearchText,
  onWorkbenchTabChange,
  ragAnswer,
  ragFeedbackSubmittingValue,
  ragFeedbackValue,
  searchColumns,
  searchLoading,
  searchRows,
  selectedFolderId,
  selectedSpace,
  selectedSpaceId,
  showNoisySpaces,
  spaceOptions,
  spaceSearchText,
  spaces,
  visibleSpaces,
}: KnowledgeWorkbenchPanelsProps) {
  const healthSummary = knowledgeHealthState.record?.summary;
  const healthTotal = healthSummary?.totalDocuments ?? listTotal;
  const healthSearchable =
    healthSummary?.searchableDocuments ??
    listRows.filter((row) => ['indexed', 'text_indexed', 'vector_indexed'].includes(row.status))
      .length;
  const healthFailed =
    healthSummary?.indexFailedDocuments ??
    listRows.filter((row) => row.status === 'index_failed').length;
  const healthProcessing =
    healthSummary?.processingDocuments ??
    listRows.filter((row) => row.status === 'importing' || row.status === 'pending_index').length;
  const healthVectorReady =
    healthSummary?.vectorReadyDocuments ??
    listRows.filter((row) => row.status === 'indexed' || row.status === 'vector_indexed').length;
  const healthCoverage = healthTotal > 0 ? Math.round((healthVectorReady / healthTotal) * 100) : 0;
  const currentImportSpaceId = selectedSpaceId ?? spaces[0]?.id;
  const ragQualityEventId = ragAnswer?.metrics?.qualityEventId;

  const renderRagAnswer = (emptyText: string) => {
    if (!ragAnswer) {
      return (
        <div className="knowledge-rag-empty">
          <Text type="secondary">{emptyText}</Text>
        </div>
      );
    }
    const feedbackDisabled = !ragQualityEventId || Boolean(ragFeedbackSubmittingValue);
    return (
      <div className="knowledge-rag-answer">
        <Text strong>引用式回答</Text>
        <div className="knowledge-rag-answer-body">{ragAnswer.answer}</div>
        {ragAnswer.citations.length > 0 ? (
          <div className="knowledge-rag-citations">
            <Text type="secondary">引用来源</Text>
            <Space wrap>
              {ragAnswer.citations.map((citation, index) => (
                <Button
                  disabled={!ragQualityEventId}
                  key={`${citation.id}-${index}`}
                  onClick={() => void onRecordCitationClick(citation)}
                  size="small"
                  title={ragQualityEventId ? '记录一次引用点击' : '本次问答缺少质量事件，暂不能记录点击'}
                  type="link"
                >
                  #{index + 1} {citation.title}
                </Button>
              ))}
            </Space>
          </div>
        ) : null}
        <div className="knowledge-rag-answer-footer">
          <Text type="secondary">
            引用 {ragAnswer.metrics?.citationCount ?? ragAnswer.citations.length} 条 ·
            延迟 {ragAnswer.metrics?.latencyMs ?? '-'} ms
          </Text>
          <Space wrap>
            <Button
              disabled={feedbackDisabled}
              icon={<CheckOutlined />}
              loading={ragFeedbackSubmittingValue === 'useful'}
              onClick={() => void onSubmitRagFeedback('useful')}
              size="small"
              title={ragQualityEventId ? '标记本次回答有用' : '本次问答缺少质量事件，暂不能反馈'}
              type={ragFeedbackValue === 'useful' ? 'primary' : 'default'}
            >
              有用
            </Button>
            <Button
              danger={ragFeedbackValue === 'not_useful'}
              disabled={feedbackDisabled}
              icon={<CloseOutlined />}
              loading={ragFeedbackSubmittingValue === 'not_useful'}
              onClick={() => void onSubmitRagFeedback('not_useful')}
              size="small"
              title={ragQualityEventId ? '标记本次回答无用' : '本次问答缺少质量事件，暂不能反馈'}
              type={ragFeedbackValue === 'not_useful' ? 'primary' : 'default'}
            >
              无用
            </Button>
          </Space>
        </div>
      </div>
    );
  };

  const knowledgeHealthSummaryPanel = (
    <section aria-label="知识索引健康摘要" className="knowledge-health-summary">
      <div className="knowledge-health-summary-main">
        <div className="knowledge-health-summary-title">
          <Text strong>索引健康</Text>
          <Text type="secondary">
            {knowledgeHealthState.status === 'loading'
              ? '正在刷新'
              : knowledgeHealthState.status === 'error'
                ? knowledgeHealthState.error ?? '加载失败'
                : `向量覆盖率 ${healthCoverage}%`}
          </Text>
        </div>
        <div className="knowledge-health-summary-grid">
          <div className="knowledge-health-summary-item">
            <Text type="secondary">可检索</Text>
            <Text strong>{healthSearchable}</Text>
          </div>
          <div className="knowledge-health-summary-item">
            <Text type="secondary">索引失败</Text>
            <Text strong type={healthFailed > 0 ? 'danger' : undefined}>{healthFailed}</Text>
          </div>
          <div className="knowledge-health-summary-item">
            <Text type="secondary">处理中</Text>
            <Text strong>{healthProcessing}</Text>
          </div>
          <div className="knowledge-health-summary-item">
            <Text type="secondary">文档总数</Text>
            <Text strong>{healthTotal}</Text>
          </div>
        </div>
      </div>
      <Button onClick={() => onSetActiveWorkbenchTab('governance')}>查看治理</Button>
    </section>
  );

  const knowledgeQuestionPanel = (
    <section aria-label="知识问答" className="knowledge-question-panel">
      <div className="knowledge-panel-header">
        <div>
          <Text strong>知识问答</Text>
          <Text type="secondary">
            基于混合召回生成引用式回答，适合查制度、方案、需求背景和排障经验。
          </Text>
        </div>
      </div>
      <Form<KnowledgeSearchFormValues>
        className="knowledge-question-form"
        initialValues={{ knowledge_space_id: selectedSpaceId, top_k: 5 }}
        key={`knowledge-question-${selectedSpaceId ?? 'all'}`}
        layout="inline"
        onFinish={(values) => void onSearch(values)}
      >
        <Form.Item label="知识空间" name="knowledge_space_id">
          <SelectKnowledgeSpace
            onChange={onSetSelectedSpaceId}
            options={spaceOptions}
          />
        </Form.Item>
        <Form.Item
          label="检索关键词"
          name="query"
          rules={[{ required: true, message: '请输入检索关键词' }]}
        >
          <Input aria-label="检索关键词" placeholder="输入问题或关键词" />
        </Form.Item>
        <Form.Item label="返回条数" name="top_k">
          <InputNumber min={1} max={20} precision={0} />
        </Form.Item>
        <Form.Item>
          <Button aria-label="检索" htmlType="submit" loading={searchLoading} type="primary">
            检索问答
          </Button>
        </Form.Item>
      </Form>
      {renderRagAnswer('输入问题后展示答案、召回证据和可访问来源。')}
      <ProTable<KnowledgeSearchResultRecord>
        columns={searchColumns}
        dataSource={searchRows}
        loading={searchLoading}
        options={false}
        pagination={false}
        rowKey="id"
        search={false}
      />
      {hasSearched && searchRows.length === 0 && !searchLoading ? (
        <Text type="secondary">没有检索到可访问的知识结果。</Text>
      ) : null}
    </section>
  );

  const knowledgeImportJobsPanel = (
    <section aria-label="导入任务" className="knowledge-tab-panel">
      <div className="knowledge-panel-header">
        <div>
          <Text strong>导入任务</Text>
          <Text type="secondary">查看文件解析、分块和索引入队状态。</Text>
        </div>
        <Button
          icon={<ReloadOutlined />}
          loading={importWorkerStatusLoading}
          onClick={() => {
            onReloadImportJobs(currentImportSpaceId);
            onReloadImportWorkerStatus();
          }}
        >
          刷新状态
        </Button>
      </div>
      <Space className="knowledge-worker-summary" wrap>
        <Text strong>导入 worker</Text>
        <StatusTag
          color={importWorkerStatus?.enabled ? 'blue' : 'default'}
          label={importWorkerStatus?.enabled ? '已启用' : '未启用'}
        />
        <StatusTag
          color={importWorkerStatus?.running ? 'green' : 'default'}
          label={importWorkerStatus?.running ? '运行中' : '已停止'}
        />
        <Text type="secondary">待处理 {importWorkerStatus?.pendingCount ?? 0}</Text>
        <Text type="secondary">处理中 {importWorkerStatus?.activeJobId ?? '-'}</Text>
        <Text type="secondary">已处理 {importWorkerStatus?.processedCount ?? 0}</Text>
        <Text type={importWorkerStatus?.failedCount ? 'danger' : 'secondary'}>
          失败 {importWorkerStatus?.failedCount ?? 0}
        </Text>
      </Space>
      <ProTable<KnowledgeImportJobRecord>
        columns={importJobColumns}
        dataSource={importJobRows}
        loading={importJobsLoading}
        options={false}
        pagination={false}
        rowKey="id"
        search={false}
      />
      {importJobRows.length === 0 && !importJobsLoading ? (
        <Text type="secondary">当前没有导入任务。</Text>
      ) : null}
    </section>
  );

  const knowledgeDepositsPanel = (
    <section aria-label="沉淀审核" className="knowledge-tab-panel">
      <div className="knowledge-panel-header">
        <div>
          <Text strong>沉淀审核</Text>
          <Text type="secondary">审核 AI 任务沉淀，批准后进入当前知识空间。</Text>
        </div>
        <Button icon={<ReloadOutlined />} loading={depositsLoading} onClick={onReloadDeposits}>
          刷新
        </Button>
      </div>
      <ProTable<KnowledgeDepositRecord>
        columns={depositColumns}
        dataSource={depositRows}
        loading={depositsLoading}
        options={false}
        pagination={false}
        rowKey="id"
        search={false}
        scroll={{ x: KNOWLEDGE_DEPOSIT_TABLE_SCROLL_X }}
        tableLayout="fixed"
      />
      {depositRows.length === 0 && !depositsLoading ? (
        <Text type="secondary">当前没有待审核知识沉淀。</Text>
      ) : null}
    </section>
  );

  const knowledgeWorkbenchPanel = (
    <div className="knowledge-workbench">
      <section aria-label="知识空间目录" className="knowledge-workbench-nav">
        <div className="knowledge-workbench-section-title">
          <Text strong>知识空间</Text>
          <Text type="secondary">{visibleSpaces.length}/{spaces.length} 个</Text>
        </div>
        <Input.Search
          allowClear
          onChange={(event) => onUpdateSpaceSearchText(event.currentTarget.value)}
          placeholder="搜索空间"
          size="small"
          value={spaceSearchText}
        />
        <div className="knowledge-space-list">
          {visibleSpaces.map((space) => (
            <Button
              block
              className={space.id === selectedSpaceId ? 'is-active' : undefined}
              key={space.id}
              onClick={() => onSelectSpace(space.id)}
            >
              {space.name}
            </Button>
          ))}
          {spaces.length === 0 ? <Text type="secondary">暂无可访问空间</Text> : null}
          {spaces.length > 0 && visibleSpaces.length === 0 ? <Text type="secondary">没有匹配的空间</Text> : null}
        </div>
        {hiddenNoisySpaceCount > 0 ? (
          <Button onClick={onToggleNoisySpaces} size="small" type="link">
            {showNoisySpaces ? '收起测试空间' : `显示测试空间 ${hiddenNoisySpaceCount}`}
          </Button>
        ) : null}
        <div className="knowledge-workbench-section-title">
          <Text strong>目录</Text>
          <Button disabled={!selectedSpaceId} onClick={onCreateFolder} size="small">
            新建
          </Button>
        </div>
        <div className="knowledge-folder-list">
          <Button
            block
            className={!selectedFolderId ? 'is-active' : undefined}
            onClick={() => onSelectFolder(undefined)}
          >
            空间根目录
          </Button>
          {folders.map((folder) => (
            <Button
              block
              className={folder.id === selectedFolderId ? 'is-active' : undefined}
              key={folder.id}
              onClick={() => onSelectFolder(folder.id)}
            >
              {folder.path}
            </Button>
          ))}
        </div>
      </section>
      <section aria-label="知识检索问答" className="knowledge-workbench-rag">
        <div className="knowledge-rag-header">
          <div>
            <Text strong>知识问答</Text>
            <Text type="secondary">
              {selectedSpace ? `当前空间：${selectedSpace.name}` : '全部可访问空间'}
            </Text>
          </div>
          <Button icon={<SearchOutlined />} onClick={onOpenSearch}>
            问答检索
          </Button>
        </div>
        <Form<KnowledgeQuickSearchFormValues>
          className="knowledge-rag-form"
          initialValues={{ top_k: 6 }}
          key={selectedSpaceId || 'all'}
          layout="inline"
          onFinish={(values) =>
            void onSearch({
              knowledge_space_id: selectedSpaceId,
              query: values.quick_query,
              top_k: values.top_k,
            })
          }
        >
          <Form.Item
            name="quick_query"
            rules={[{ required: true, message: '请输入问题或关键词' }]}
          >
            <Input placeholder="搜索制度、方案、需求背景或直接提问" />
          </Form.Item>
          <Form.Item name="top_k">
            <InputNumber min={1} max={12} precision={0} />
          </Form.Item>
          <Form.Item>
            <Button htmlType="submit" loading={searchLoading} type="primary">
              问答
            </Button>
          </Form.Item>
        </Form>
        {renderRagAnswer('输入问题后展示引用式答案和召回证据。')}
      </section>
    </div>
  );

  return (
    <div className="knowledge-page-stack">
      <Tabs
        activeKey={activeWorkbenchTab}
        className="knowledge-workbench-tabs"
        items={[
          {
            children: (
              <div className="knowledge-page-stack">
                {knowledgeWorkbenchPanel}
                {knowledgeHealthSummaryPanel}
              </div>
            ),
            key: 'documents',
            label: '文档库',
          },
          {
            children: knowledgeQuestionPanel,
            key: 'search',
            label: '问答检索',
          },
          {
            children: knowledgeHealthPanel,
            key: 'governance',
            label: '索引治理',
          },
          {
            children: knowledgeImportJobsPanel,
            key: 'imports',
            label: '导入任务',
          },
          {
            children: knowledgeDepositsPanel,
            key: 'deposits',
            label: '沉淀审核',
          },
        ]}
        onChange={onWorkbenchTabChange}
      />
    </div>
  );
}

function SelectKnowledgeSpace({
  onChange,
  options,
}: {
  onChange: (value?: string) => void;
  options: { label: string; value: string }[];
}) {
  return (
    <Select
      allowClear
      onChange={onChange}
      options={options}
      placeholder="全部可访问空间"
      style={{ minWidth: 220 }}
    />
  );
}
