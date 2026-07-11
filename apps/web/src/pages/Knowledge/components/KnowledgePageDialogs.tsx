import {
  EditOutlined,
  FileSearchOutlined,
  FolderAddOutlined,
  NodeIndexOutlined,
  ReloadOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Alert, Button, Drawer, Form, Input, InputNumber, Modal, Select, Space, Spin, Tabs, Typography } from 'antd';
import type { FormInstance } from 'antd';
import type { ChangeEvent, Key, RefObject } from 'react';

import { RequirementFullChainView } from '../../../components/RequirementFullChainView';
import { StatusTag } from '../../../components/ManagementListPage';
import type { KnowledgeRecord, RequirementRecord } from '../../../data/management';
import { formatRemoteRowsError, type RemoteRowsError } from '../../../hooks/useRemoteRows';
import type {
  KnowledgeAssetRecord,
  KnowledgeChunkRecord,
  KnowledgeChunkSetRecord,
  KnowledgeCitationFeedbackRecord,
  KnowledgeDepositRecord,
  KnowledgeDocumentVersionRecord,
  RequirementFullChainRecord,
} from '../../../services/aiBrain';
import { joinTextList } from '../../../utils/managementCrud';
import type {
  KnowledgeAdvancedFilterValues,
  KnowledgeBatchMoveFormValues,
  KnowledgeFolderEditFormValues,
  KnowledgeFolderFormValues,
  KnowledgeFormValues,
  KnowledgeSpaceFormValues,
  RejectDepositFormValues,
} from '../types';

const { Text } = Typography;

const documentVersionStatusLabels: Record<string, string> = {
  active: '当前生效',
  expired: '已过期',
  failed: '处理失败',
  processing: '处理中',
  superseded: '已替代',
};

const freshnessStatusLabels: Record<string, string> = {
  expired: '已过期',
  expiring: '即将过期',
  failed: '处理失败',
  flagged_outdated: '被标记过期',
  fresh: '有效',
  superseded: '已替代',
  unknown: '未知',
};

const citationFeedbackLabels: Record<string, string> = {
  incorrect: '内容错误',
  not_useful: '无用',
  outdated: '内容已过期',
  partial: '部分有用',
  useful: '有用',
};

type KnowledgePageDialogsProps = {
  advancedFilterSubmitRef: RefObject<HTMLButtonElement | null>;
  advancedFilterValues: KnowledgeAdvancedFilterValues;
  assetColumns: ProColumns<KnowledgeAssetRecord>[];
  assetRows: KnowledgeAssetRecord[];
  assetsDocument: KnowledgeRecord | null;
  assetsLoading: boolean;
  batchMoveSubmitRef: RefObject<HTMLButtonElement | null>;
  chunkColumns: ProColumns<KnowledgeChunkRecord>[];
  chunkRows: KnowledgeChunkRecord[];
  chunkSetColumns: ProColumns<KnowledgeChunkSetRecord>[];
  chunkSetRows: KnowledgeChunkSetRecord[];
  chunkSetsLoading: boolean;
  chunksDocument: KnowledgeRecord | null;
  chunksLoading: boolean;
  clearAdvancedFilters: () => void;
  closeFullChainModal: () => void;
  detailDocument: KnowledgeRecord | null;
  detailFeedbackRows: KnowledgeCitationFeedbackRecord[];
  detailGovernanceLoading: boolean;
  detailVersionRows: KnowledgeDocumentVersionRecord[];
  documentFormRef: RefObject<FormInstance<KnowledgeFormValues> | null>;
  documentInitialValues: Partial<KnowledgeFormValues>;
  documentSubmitRef: RefObject<HTMLButtonElement | null>;
  editingDocument: KnowledgeRecord | null;
  folderEditSubmitRef: RefObject<HTMLButtonElement | null>;
  folderOptions: { label: string; value: string }[];
  folderSubmitRef: RefObject<HTMLButtonElement | null>;
  fullChain: RequirementFullChainRecord | null;
  fullChainDeposit: KnowledgeDepositRecord | null;
  fullChainError?: RemoteRowsError;
  fullChainVersionRequirements: RequirementRecord[];
  handleAdvancedFilterSubmit: (values: KnowledgeAdvancedFilterValues) => void;
  handleBatchMove: (values: KnowledgeBatchMoveFormValues) => void | Promise<void>;
  handleCreateFolder: (values: KnowledgeFolderFormValues) => void | Promise<void>;
  handleCreateSpace: (values: KnowledgeSpaceFormValues) => void | Promise<void>;
  handleEditFolder: (values: KnowledgeFolderEditFormValues) => void | Promise<void>;
  handleFileInputChange: (event: ChangeEvent<HTMLInputElement>) => void | Promise<void>;
  handleRejectDeposit: (values: RejectDepositFormValues) => void | Promise<void>;
  handleReparseDocument: (row: KnowledgeRecord) => void | Promise<void>;
  handleSave: (values: KnowledgeFormValues) => void | Promise<void>;
  isAdvancedFilterOpen: boolean;
  isAssetsModalOpen: boolean;
  isBatchMoveModalOpen: boolean;
  isChunksModalOpen: boolean;
  isFolderEditModalOpen: boolean;
  isFolderModalOpen: boolean;
  isFullChainLoading: boolean;
  isModalOpen: boolean;
  isSaving: boolean;
  isSpaceModalOpen: boolean;
  onCloseAssetsModal: () => void;
  onCloseBatchMoveModal: () => void;
  onCloseChunksModal: () => void;
  onCloseDetailDrawer: () => void;
  onCloseDocumentModal: () => void;
  onCloseFolderEditModal: () => void;
  onCloseFolderModal: () => void;
  onCloseSpaceModal: () => void;
  onEditDocument: (row: KnowledgeRecord) => void;
  onOpenAssetsModal: (row: KnowledgeRecord) => void | Promise<void>;
  onOpenChunksModal: (row: KnowledgeRecord) => void | Promise<void>;
  onLoadProcessingProfiles: () => void | Promise<unknown>;
  onLoadDocumentGovernance: (row: KnowledgeRecord) => void | Promise<void>;
  processingProfileOptions: { label: string; value: string }[];
  rejectDepositSubmitRef: RefObject<HTMLButtonElement | null>;
  rejectingDeposit: KnowledgeDepositRecord | null;
  roleOptions: { label: string; value: string }[];
  selectedRowKeys: Key[];
  selectedSpaceId?: string;
  selectedUploadFile: {
    file: File;
    filename: string;
    mimeType: string;
    sizeBytes: number;
  } | null;
  setIsAdvancedFilterOpen: (open: boolean) => void;
  setIsFolderModalOpen: (open: boolean) => void;
  setRejectingDeposit: (row: KnowledgeDepositRecord | null) => void;
  setSelectedSpaceId: (spaceId?: string) => void;
  spaceNameById: Map<string, string>;
  spaceOptions: { label: string; value: string }[];
  spaceSubmitRef: RefObject<HTMLButtonElement | null>;
  statusLabels: Record<KnowledgeRecord['status'], { color: string; label: string }>;
};

function hasAdvancedFilterValues(filters: Record<string, unknown>) {
  return Object.values(filters).some((value) => String(value ?? '').trim());
}

export function KnowledgePageDialogs({
  advancedFilterSubmitRef,
  advancedFilterValues,
  assetColumns,
  assetRows,
  assetsDocument,
  assetsLoading,
  batchMoveSubmitRef,
  chunkColumns,
  chunkRows,
  chunkSetColumns,
  chunkSetRows,
  chunkSetsLoading,
  chunksDocument,
  chunksLoading,
  clearAdvancedFilters,
  closeFullChainModal,
  detailDocument,
  detailFeedbackRows,
  detailGovernanceLoading,
  detailVersionRows,
  documentFormRef,
  documentInitialValues,
  documentSubmitRef,
  editingDocument,
  folderEditSubmitRef,
  folderOptions,
  folderSubmitRef,
  fullChain,
  fullChainDeposit,
  fullChainError,
  fullChainVersionRequirements,
  handleAdvancedFilterSubmit,
  handleBatchMove,
  handleCreateFolder,
  handleCreateSpace,
  handleEditFolder,
  handleFileInputChange,
  handleRejectDeposit,
  handleReparseDocument,
  handleSave,
  isAdvancedFilterOpen,
  isAssetsModalOpen,
  isBatchMoveModalOpen,
  isChunksModalOpen,
  isFolderEditModalOpen,
  isFolderModalOpen,
  isFullChainLoading,
  isModalOpen,
  isSaving,
  isSpaceModalOpen,
  onCloseAssetsModal,
  onCloseBatchMoveModal,
  onCloseChunksModal,
  onCloseDetailDrawer,
  onCloseDocumentModal,
  onCloseFolderEditModal,
  onCloseFolderModal,
  onCloseSpaceModal,
  onEditDocument,
  onOpenAssetsModal,
  onOpenChunksModal,
  onLoadProcessingProfiles,
  onLoadDocumentGovernance,
  processingProfileOptions,
  rejectDepositSubmitRef,
  rejectingDeposit,
  roleOptions,
  selectedRowKeys,
  selectedSpaceId,
  selectedUploadFile,
  setIsAdvancedFilterOpen,
  setIsFolderModalOpen,
  setRejectingDeposit,
  setSelectedSpaceId,
  spaceNameById,
  spaceOptions,
  spaceSubmitRef,
  statusLabels,
}: KnowledgePageDialogsProps) {
  return (
    <>
      <Modal
        destroyOnHidden
        onCancel={() => setIsAdvancedFilterOpen(false)}
        onOk={() => advancedFilterSubmitRef.current?.click()}
        open={isAdvancedFilterOpen}
        title="高级筛选"
      >
        <Form<KnowledgeAdvancedFilterValues>
          initialValues={advancedFilterValues}
          key={`knowledge-advanced-filter-${JSON.stringify(advancedFilterValues)}`}
          layout="vertical"
          onFinish={handleAdvancedFilterSubmit}
          preserve={false}
        >
          <Form.Item label="目录" name="folderId">
            <Select allowClear options={folderOptions} placeholder="全部目录" />
          </Form.Item>
          <Form.Item label="类型" name="documentType">
            <Select
              allowClear
              options={[
                { label: 'PRD', value: 'PRD' },
                { label: 'Spec', value: 'Spec' },
                { label: 'Deposit', value: 'Deposit' },
                { label: 'Manual', value: 'manual' },
              ]}
              placeholder="全部类型"
            />
          </Form.Item>
          <Form.Item label="权限角色" name="ownerRole">
            <Input placeholder="如 admin / viewer" />
          </Form.Item>
          <Space>
            <Button htmlType="button" onClick={clearAdvancedFilters}>
              清空高级筛选
            </Button>
            {hasAdvancedFilterValues(advancedFilterValues) ? (
              <Text type="secondary">已启用高级筛选</Text>
            ) : null}
          </Space>
          <button ref={advancedFilterSubmitRef} style={{ display: 'none' }} type="submit" />
        </Form>
      </Modal>
      <Modal
        footer={null}
        onCancel={onCloseAssetsModal}
        open={isAssetsModalOpen}
        title={assetsDocument ? `文档资产：${assetsDocument.title}` : '文档资产'}
        width={860}
      >
        <ProTable<KnowledgeAssetRecord>
          columns={assetColumns}
          dataSource={assetRows}
          loading={assetsLoading}
          options={false}
          pagination={false}
          rowKey="id"
          search={false}
        />
        {assetRows.length === 0 && !assetsLoading ? (
          <Text type="secondary">当前文档没有可查看资产。</Text>
        ) : null}
      </Modal>
      <Modal
        footer={null}
        onCancel={onCloseChunksModal}
        open={isChunksModalOpen}
        title={chunksDocument ? `分块版本：${chunksDocument.title}` : '分块版本'}
        width={1100}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <ProTable<KnowledgeChunkSetRecord>
            columns={chunkSetColumns}
            dataSource={chunkSetRows}
            loading={chunkSetsLoading}
            options={false}
            pagination={false}
            rowKey="id"
            search={false}
          />
          <ProTable<KnowledgeChunkRecord>
            columns={chunkColumns}
            dataSource={chunkRows}
            loading={chunksLoading}
            options={false}
            pagination={false}
            rowKey="id"
            search={false}
          />
          {chunkRows.length === 0 && !chunksLoading ? (
            <Text type="secondary">当前分块版本没有可预览 chunk。</Text>
          ) : null}
        </Space>
      </Modal>
      <Drawer
        onClose={onCloseDetailDrawer}
        open={Boolean(detailDocument)}
        size="large"
        title={detailDocument?.title ?? '知识详情'}
      >
        {detailDocument ? (
          <div className="knowledge-detail-drawer">
            <Tabs
              items={[
                {
                  children: (
                    <div className="knowledge-detail-meta">
                      <Text type="secondary">知识编号</Text>
                      <Text>{detailDocument.id}</Text>
                      <Text type="secondary">知识空间</Text>
                      <Text>
                        {detailDocument.knowledgeSpaceId
                          ? spaceNameById.get(detailDocument.knowledgeSpaceId) ?? detailDocument.knowledgeSpaceId
                          : '-'}
                      </Text>
                      <Text type="secondary">目录</Text>
                      <Text>{detailDocument.folderPath ?? '-'}</Text>
                      <Text type="secondary">类型</Text>
                      <Text>{detailDocument.documentType}</Text>
                      <Text type="secondary">权限角色</Text>
                      <Text>{detailDocument.ownerRole}</Text>
                      <Text type="secondary">状态</Text>
                      <StatusTag
                        color={statusLabels[detailDocument.status].color}
                        label={statusLabels[detailDocument.status].label}
                      />
                      <Text type="secondary">更新时间</Text>
                      <Text>{detailDocument.updatedAt ?? '-'}</Text>
                      <Text type="secondary">标签</Text>
                      <Text>{joinTextList(detailDocument.tags) || '-'}</Text>
                    </div>
                  ),
                  key: 'overview',
                  label: '概览',
                },
                {
                  children: (
                    <div className="knowledge-detail-content">
                      {detailDocument.content?.trim() || '暂无正文内容。'}
                    </div>
                  ),
                  key: 'content',
                  label: '正文',
                },
                {
                  children: (
                    <div className="knowledge-detail-meta">
                      <Text type="secondary">索引状态</Text>
                      <StatusTag
                        color={statusLabels[detailDocument.status].color}
                        label={statusLabels[detailDocument.status].label}
                      />
                      <Text type="secondary">生效分块</Text>
                      <Text>{detailDocument.activeChunkSetId ?? '-'}</Text>
                      <Text type="secondary">生效文档版本</Text>
                      <Text>
                        {detailDocument.documentVersion
                          ? `v${detailDocument.documentVersion} · ${detailDocument.activeDocumentVersionId ?? '-'}`
                          : '-'}
                      </Text>
                      <Text type="secondary">源资产</Text>
                      <Text>{detailDocument.sourceAssetId ?? '-'}</Text>
                      <Text type="secondary">索引错误</Text>
                      <Text>{detailDocument.indexError || detailDocument.vectorIndexError || '-'}</Text>
                    </div>
                  ),
                  key: 'hits',
                  label: '引用/命中',
                },
                {
                  children: (
                    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
                      <ProTable<KnowledgeDocumentVersionRecord>
                        columns={[
                          { dataIndex: 'version', render: (_, row) => `v${row.version}`, title: '版本' },
                          { dataIndex: 'status', render: (_, row) => documentVersionStatusLabels[row.status] ?? row.status, title: '状态' },
                          { dataIndex: 'freshnessStatus', render: (_, row) => freshnessStatusLabels[row.freshnessStatus] ?? row.freshnessStatus, title: '有效性' },
                          { dataIndex: 'processingProfileId', render: (_, row) => row.processingProfileId ?? '-', title: '处理配置' },
                          { dataIndex: 'expiresAt', render: (_, row) => row.expiresAt ?? '-', title: '过期时间' },
                          { dataIndex: 'outdatedFeedbackCount', title: '过期反馈' },
                        ]}
                        dataSource={detailVersionRows}
                        loading={detailGovernanceLoading}
                        options={false}
                        pagination={false}
                        rowKey="id"
                        search={false}
                      />
                      <ProTable<KnowledgeCitationFeedbackRecord>
                        columns={[
                          { dataIndex: 'feedbackValue', render: (_, row) => citationFeedbackLabels[row.feedbackValue] ?? row.feedbackValue, title: '反馈' },
                          { dataIndex: 'documentVersionId', render: (_, row) => row.documentVersionId ?? '-', title: '文档版本' },
                          { dataIndex: 'chunkId', render: (_, row) => row.chunkId ?? '-', title: 'Chunk' },
                          { dataIndex: 'comment', render: (_, row) => row.comment ?? '-', title: '说明' },
                          { dataIndex: 'createdAt', render: (_, row) => row.createdAt ?? '-', title: '时间' },
                        ]}
                        dataSource={detailFeedbackRows}
                        loading={detailGovernanceLoading}
                        options={false}
                        pagination={false}
                        rowKey="id"
                        search={false}
                      />
                    </Space>
                  ),
                  key: 'versions',
                  label: '版本与反馈',
                },
                {
                  children: (
                    <Space wrap>
                      <Button icon={<FileSearchOutlined />} onClick={() => void onOpenAssetsModal(detailDocument)}>
                        资产
                      </Button>
                      <Button icon={<NodeIndexOutlined />} onClick={() => void onOpenChunksModal(detailDocument)}>
                        分块
                      </Button>
                      <Button icon={<EditOutlined />} onClick={() => onEditDocument(detailDocument)}>
                        编辑
                      </Button>
                      <Button icon={<ReloadOutlined />} onClick={() => void handleReparseDocument(detailDocument)}>
                        重解析
                      </Button>
                    </Space>
                  ),
                  key: 'assets',
                  label: '资产与分块',
                },
              ]}
              onChange={(key) => {
                if (key === 'versions' && detailVersionRows.length === 0) {
                  void onLoadDocumentGovernance(detailDocument);
                }
              }}
            />
          </div>
        ) : null}
      </Drawer>
      <Modal
        destroyOnHidden
        footer={null}
        onCancel={closeFullChainModal}
        open={Boolean(fullChainDeposit)}
        style={{ maxWidth: 'calc(100vw - 40px)' }}
        styles={{ body: { maxHeight: 'calc(100vh - 180px)', overflowX: 'hidden', overflowY: 'auto' } }}
        title={fullChainDeposit ? `知识沉淀全链路 · ${fullChainDeposit.id}` : '知识沉淀全链路'}
        width={1040}
      >
        <Spin spinning={isFullChainLoading}>
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            {fullChainError ? <Alert message={formatRemoteRowsError(fullChainError)} type="error" /> : null}
            {fullChain ? (
              <RequirementFullChainView
                fullChain={fullChain}
                versionRequirements={fullChainVersionRequirements}
              />
            ) : null}
          </Space>
        </Spin>
      </Modal>
      <Modal
        confirmLoading={isSaving}
        destroyOnHidden
        onCancel={onCloseDocumentModal}
        onOk={() => documentSubmitRef.current?.click()}
        open={isModalOpen}
        title={editingDocument ? '编辑知识文档' : '导入知识文档'}
      >
        <Form<KnowledgeFormValues>
          initialValues={documentInitialValues}
          layout="vertical"
          onFinish={(values) => void handleSave(values)}
          preserve={false}
          ref={documentFormRef}
        >
          <Form.Item
            label="知识空间"
            name="knowledge_space_id"
            rules={[{ required: true, message: '请选择知识空间' }]}
          >
            <Select
              onChange={(value) => {
                setSelectedSpaceId(value);
                documentFormRef.current?.setFieldValue('folder_id', undefined);
              }}
              options={spaceOptions}
              placeholder="选择知识空间"
            />
          </Form.Item>
          <Form.Item label="目录" name="folder_id">
            <Space.Compact style={{ width: '100%' }}>
              <Select
                allowClear
                disabled={!selectedSpaceId}
                options={folderOptions}
                placeholder="选择目录"
              />
              <Button htmlType="button" icon={<FolderAddOutlined />} onClick={() => setIsFolderModalOpen(true)}>
                新建
              </Button>
            </Space.Compact>
          </Form.Item>
          <Form.Item label="知识标题" name="title" rules={[{ required: true, message: '请输入知识标题' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="类型" name="doc_type" rules={[{ required: true, message: '请输入知识类型' }]}>
            <Input placeholder="manual / PRD / Spec / Deposit" />
          </Form.Item>
          {!editingDocument ? (
            <>
              <Form.Item label="解析器" name="parser_engine">
                <Select
                  options={[
                    { label: '纯文本', value: 'plain_text' },
                    { label: 'Markdown', value: 'markdown' },
                    { label: 'PDF 文本', value: 'pdf_text' },
                    { label: '多模态 OCR / 版面 / 表格', value: 'multimodal' },
                    { label: 'OCR JSON', value: 'ocr_json' },
                    { label: '表格 JSON', value: 'table_json' },
                  ]}
                  placeholder="按文件类型自动选择"
                />
              </Form.Item>
              <Form.Item label="处理配置" name="processing_profile_id">
                <Select
                  allowClear
                  onOpenChange={(open) => {
                    if (open) {
                      void onLoadProcessingProfiles();
                    }
                  }}
                  options={processingProfileOptions}
                  placeholder="多模态解析时选择"
                />
              </Form.Item>
              <Form.Item label="有效天数" name="expires_in_days">
                <InputNumber min={1} max={3650} precision={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="分块策略" name="chunk_strategy">
                <Select
                  options={[
                    { label: '简单文本', value: 'simple_text' },
                    { label: '父子分块', value: 'parent_child' },
                    { label: '正则分块', value: 'regex_section' },
                  ]}
                  placeholder="简单文本"
                />
              </Form.Item>
            </>
          ) : null}
          <Form.Item label="权限角色" name="permission_roles" rules={[{ required: true, message: '请选择权限角色' }]}>
            <Select
              disabled={roleOptions.length === 0}
              mode="multiple"
              optionFilterProp="label"
              options={roleOptions}
              placeholder="请选择权限角色"
            />
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Input />
          </Form.Item>
          {!editingDocument ? (
            <Form.Item label="上传文件">
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Button icon={<UploadOutlined />}>
                  <label style={{ cursor: 'pointer' }}>
                    选择文件
                    <input
                      aria-label="选择知识文件"
                      onChange={(event) => void handleFileInputChange(event)}
                      accept=".csv,.jpeg,.jpg,.json,.md,.markdown,.pdf,.png,.tif,.tiff,.txt,.webp"
                      style={{ display: 'none' }}
                      type="file"
                    />
                  </label>
                </Button>
                {selectedUploadFile ? (
                  <Text type="secondary">
                    {selectedUploadFile.filename} · {Math.ceil(selectedUploadFile.sizeBytes / 1024)} KB ·
                    {selectedUploadFile.mimeType}
                  </Text>
                ) : null}
              </Space>
            </Form.Item>
          ) : null}
          {editingDocument ? (
            <Form.Item label="索引状态" name="index_status">
              <Select
                options={[
                  { label: '已索引', value: 'indexed' },
                  { label: '文本索引', value: 'text_indexed' },
                  { label: '向量索引', value: 'vector_indexed' },
                  { label: '待索引', value: 'pending_index' },
                  { label: '索引中', value: 'importing' },
                  { label: '索引失败', value: 'index_failed' },
                  { label: '已归档', value: 'archived' },
                ]}
              />
            </Form.Item>
          ) : null}
          <Form.Item label="内容" name="content">
            <Input.TextArea rows={5} />
          </Form.Item>
          <button ref={documentSubmitRef} style={{ display: 'none' }} type="submit" />
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        onCancel={onCloseSpaceModal}
        onOk={() => spaceSubmitRef.current?.click()}
        open={isSpaceModalOpen}
        title="新建知识空间"
      >
        <Form<KnowledgeSpaceFormValues>
          layout="vertical"
          onFinish={(values) => void handleCreateSpace(values)}
          preserve={false}
        >
          <Form.Item label="空间编码" name="code" rules={[{ required: true, message: '请输入空间编码' }]}>
            <Input placeholder="payments" />
          </Form.Item>
          <Form.Item label="空间名称" name="name" rules={[{ required: true, message: '请输入空间名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <button ref={spaceSubmitRef} style={{ display: 'none' }} type="submit" />
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        onCancel={onCloseFolderModal}
        onOk={() => folderSubmitRef.current?.click()}
        open={isFolderModalOpen}
        title="新建知识目录"
      >
        <Form<KnowledgeFolderFormValues>
          layout="vertical"
          onFinish={(values) => void handleCreateFolder(values)}
          preserve={false}
        >
          <Form.Item label="目录名称" name="name" rules={[{ required: true, message: '请输入目录名称' }]}>
            <Input />
          </Form.Item>
          <button ref={folderSubmitRef} style={{ display: 'none' }} type="submit" />
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        onCancel={onCloseFolderEditModal}
        onOk={() => folderEditSubmitRef.current?.click()}
        open={isFolderEditModalOpen}
        title="目录整理"
      >
        <Form<KnowledgeFolderEditFormValues>
          layout="vertical"
          onFinish={(values) => void handleEditFolder(values)}
          preserve={false}
        >
          <Form.Item label="目录" name="folder_id" rules={[{ required: true, message: '请选择目录' }]}>
            <Select options={folderOptions} />
          </Form.Item>
          <Form.Item label="目录名称" name="name">
            <Input />
          </Form.Item>
          <Form.Item label="父目录" name="parent_folder_id">
            <Select allowClear options={folderOptions} />
          </Form.Item>
          <Form.Item label="排序" name="sort_order">
            <InputNumber min={0} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select
              options={[
                { label: '启用', value: 'active' },
                { label: '归档', value: 'archived' },
              ]}
            />
          </Form.Item>
          <button ref={folderEditSubmitRef} style={{ display: 'none' }} type="submit" />
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        onCancel={onCloseBatchMoveModal}
        onOk={() => batchMoveSubmitRef.current?.click()}
        open={isBatchMoveModalOpen}
        title="批量移动知识"
      >
        <Form<KnowledgeBatchMoveFormValues>
          layout="vertical"
          onFinish={(values) => void handleBatchMove(values)}
          preserve={false}
        >
          <Form.Item label="目标目录" name="folder_id">
            <Select allowClear options={folderOptions} placeholder="移动到空间根目录" />
          </Form.Item>
          <Text type="secondary">已选择 {selectedRowKeys.length} 条知识文档。</Text>
          <button ref={batchMoveSubmitRef} style={{ display: 'none' }} type="submit" />
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        onCancel={() => setRejectingDeposit(null)}
        onOk={() => rejectDepositSubmitRef.current?.click()}
        open={Boolean(rejectingDeposit)}
        title={rejectingDeposit ? `拒绝沉淀：${rejectingDeposit.title}` : '拒绝沉淀'}
      >
        <Form<RejectDepositFormValues>
          layout="vertical"
          onFinish={(values) => void handleRejectDeposit(values)}
          preserve={false}
        >
          <Form.Item label="拒绝原因" name="reason" rules={[{ required: true, message: '请输入拒绝原因' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <button ref={rejectDepositSubmitRef} style={{ display: 'none' }} type="submit" />
        </Form>
      </Modal>
    </>
  );
}
