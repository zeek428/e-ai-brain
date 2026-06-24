import {
  DatabaseOutlined,
  DeleteOutlined,
  EditOutlined,
  FileSearchOutlined,
  FolderAddOutlined,
  FolderOpenOutlined,
  NodeIndexOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  StopOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Typography, message } from 'antd';
import type { FormInstance } from 'antd';
import { type ChangeEvent, type Key, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ManagementListQuery } from '../../components/ManagementListPage';
import type { KnowledgeRecord } from '../../data/management';
import { type UserRoleDefinition, toUserRoleOptions } from '../../data/roles';
import { formatRemoteRowsError, normalizeRemoteRowsError, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  approveKnowledgeDeposit,
  activateKnowledgeChunkSet,
  batchMoveKnowledgeDocuments,
  cancelKnowledgeImportJob,
  createKnowledgeFolder,
  createKnowledgeSpace,
  createManagementKnowledgeDocument,
  deleteManagementKnowledgeDocument,
  fetchKnowledgeChunks,
  fetchKnowledgeChunkSets,
  fetchKnowledgeDeposits,
  fetchKnowledgeDocumentAssets,
  fetchKnowledgeFolders,
  fetchKnowledgeImportJobs,
  fetchKnowledgeImportWorkerStatus,
  fetchKnowledgeSearchResults,
  fetchKnowledgeSpaces,
  fetchManagementKnowledgeList,
  fetchRoleDefinitions,
  rejectKnowledgeDeposit,
  reparseKnowledgeDocument,
  retryKnowledgeImportJob,
  retryKnowledgeDocumentIndex,
  runKnowledgeImportJob,
  updateManagementKnowledgeDocument,
  updateKnowledgeFolder,
  uploadKnowledgeDocument,
  type KnowledgeChunkRecord,
  type KnowledgeChunkSetRecord,
  type KnowledgeFolderRecord,
  type KnowledgeAssetRecord,
  type KnowledgeImportJobRecord,
  type KnowledgeImportWorkerStatusRecord,
  type KnowledgeListQuery,
  type KnowledgeDepositRecord,
  type KnowledgeSearchResultRecord,
  type KnowledgeSpaceRecord,
} from '../../services/aiBrain';
import { formatMutationError, joinTextList, splitCommaText } from '../../utils/managementCrud';

const { Text } = Typography;

const statusLabels: Record<KnowledgeRecord['status'], { color: string; label: string }> = {
  archived: { color: 'default', label: '已归档' },
  importing: { color: 'blue', label: '索引中' },
  indexed: { color: 'green', label: '已索引' },
  index_failed: { color: 'red', label: '索引失败' },
  pending_index: { color: 'gold', label: '待索引' },
  text_indexed: { color: 'cyan', label: '文本索引' },
  vector_indexed: { color: 'green', label: '向量索引' },
};

const depositStatusLabels: Record<string, { color: string; label: string }> = {
  approved: { color: 'green', label: '已入库' },
  pending: { color: 'gold', label: '待审核' },
  rejected: { color: 'red', label: '已拒绝' },
};

const importJobStatusLabels: Record<string, { color: string; label: string }> = {
  cancelled: { color: 'default', label: '已取消' },
  completed: { color: 'green', label: '已完成' },
  failed: { color: 'red', label: '失败' },
  parsing: { color: 'blue', label: '解析中' },
  queued: { color: 'default', label: '排队中' },
  uploaded: { color: 'default', label: '已上传' },
};

const assetTypeLabels: Record<string, string> = {
  ocr_json: 'OCR 结果',
  original: '原始文件',
  parsed_markdown: '解析文本',
  table_json: '表格数据',
};

function formatAssetSize(sizeBytes: number) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }
  return `${(sizeBytes / 1024 / 1024).toFixed(1)} MB`;
}

type KnowledgeFormValues = {
  chunk_strategy?: string;
  content?: string;
  doc_type: string;
  folder_id?: string;
  index_status?: KnowledgeRecord['status'];
  knowledge_space_id?: string;
  permission_roles?: string[];
  parser_engine?: string;
  tags?: string;
  title: string;
};

type KnowledgeSpaceFormValues = {
  code: string;
  description?: string;
  name: string;
};

type KnowledgeFolderFormValues = {
  name: string;
};

type KnowledgeFolderEditFormValues = {
  folder_id: string;
  name?: string;
  parent_folder_id?: string;
  sort_order?: number;
  status?: string;
};

type KnowledgeBatchMoveFormValues = {
  folder_id?: string;
};

type RejectDepositFormValues = {
  reason: string;
};

type KnowledgeSearchFormValues = {
  knowledge_space_id?: string;
  query: string;
  top_k?: number;
};

const knowledgeSortFieldMap: Record<string, string> = {
  documentType: 'doc_type',
  id: 'id',
  ownerRole: 'permission_roles',
  status: 'index_status',
  title: 'title',
  updatedAt: 'updated_at',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildKnowledgeListQuery(query: ManagementListQuery): KnowledgeListQuery {
  return {
    documentType: normalizeFilterText(query.filters.documentType),
    folderId: normalizeFilterText(query.filters.folderId),
    keyword: normalizeFilterText(query.filters.title),
    knowledgeSpaceId: normalizeFilterText(query.filters.knowledgeSpaceId),
    ownerRole: normalizeFilterText(query.filters.ownerRole),
    page: query.page,
    pageSize: query.pageSize,
    sortField: query.sortField ? knowledgeSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
  };
}

export default function KnowledgePage() {
  const documentFormRef = useRef<FormInstance<KnowledgeFormValues>>(null);
  const documentSubmitRef = useRef<HTMLButtonElement>(null);
  const batchMoveSubmitRef = useRef<HTMLButtonElement>(null);
  const folderEditSubmitRef = useRef<HTMLButtonElement>(null);
  const folderSubmitRef = useRef<HTMLButtonElement>(null);
  const rejectDepositSubmitRef = useRef<HTMLButtonElement>(null);
  const spaceSubmitRef = useRef<HTMLButtonElement>(null);
  const [assetRows, setAssetRows] = useState<KnowledgeAssetRecord[]>([]);
  const [assetsLoading, setAssetsLoading] = useState(false);
  const [depositRows, setDepositRows] = useState<KnowledgeDepositRecord[]>([]);
  const [depositsLoading, setDepositsLoading] = useState(false);
  const [importJobRows, setImportJobRows] = useState<KnowledgeImportJobRecord[]>([]);
  const [importJobsLoading, setImportJobsLoading] = useState(false);
  const [importWorkerStatus, setImportWorkerStatus] =
    useState<KnowledgeImportWorkerStatusRecord | null>(null);
  const [importWorkerStatusLoading, setImportWorkerStatusLoading] = useState(false);
  const [chunkRows, setChunkRows] = useState<KnowledgeChunkRecord[]>([]);
  const [chunkSetRows, setChunkSetRows] = useState<KnowledgeChunkSetRecord[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [chunkSetsLoading, setChunkSetsLoading] = useState(false);
  const [isAssetsModalOpen, setIsAssetsModalOpen] = useState(false);
  const [isBatchMoveModalOpen, setIsBatchMoveModalOpen] = useState(false);
  const [isChunksModalOpen, setIsChunksModalOpen] = useState(false);
  const [isDepositsModalOpen, setIsDepositsModalOpen] = useState(false);
  const [isFolderEditModalOpen, setIsFolderEditModalOpen] = useState(false);
  const [isFolderModalOpen, setIsFolderModalOpen] = useState(false);
  const [isImportJobsModalOpen, setIsImportJobsModalOpen] = useState(false);
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const [isSpaceModalOpen, setIsSpaceModalOpen] = useState(false);
  const [editingDocument, setEditingDocument] = useState<KnowledgeRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [rejectingDeposit, setRejectingDeposit] = useState<KnowledgeDepositRecord | null>(null);
  const [searchRows, setSearchRows] = useState<KnowledgeSearchResultRecord[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [documentInitialValues, setDocumentInitialValues] = useState<Partial<KnowledgeFormValues>>({});
  const [searchInitialValues, setSearchInitialValues] = useState<Partial<KnowledgeSearchFormValues>>({ top_k: 5 });
  const [selectedSpaceId, setSelectedSpaceId] = useState<string | undefined>();
  const [selectedUploadFile, setSelectedUploadFile] = useState<{
    contentBase64: string;
    filename: string;
    mimeType: string;
  } | null>(null);
  const [folders, setFolders] = useState<KnowledgeFolderRecord[]>([]);
  const [spaces, setSpaces] = useState<KnowledgeSpaceRecord[]>([]);
  const [roleCatalogError, setRoleCatalogError] = useState<string | undefined>();
  const [roleDefinitions, setRoleDefinitions] = useState<UserRoleDefinition[]>([]);
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'updatedAt',
    sortOrder: 'descend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    rows: KnowledgeRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const [assetsDocument, setAssetsDocument] = useState<KnowledgeRecord | null>(null);
  const [chunksDocument, setChunksDocument] = useState<KnowledgeRecord | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const roleOptions = useMemo(() => toUserRoleOptions(roleDefinitions), [roleDefinitions]);
  const spaceOptions = useMemo(
    () => spaces.map((space) => ({ label: `${space.name} (${space.code})`, value: space.id })),
    [spaces],
  );
  const folderOptions = useMemo(
    () => folders.map((folder) => ({ label: folder.path, value: folder.id })),
    [folders],
  );
  const spaceNameById = useMemo(
    () => new Map(spaces.map((space) => [space.id, space.name])),
    [spaces],
  );

  const reloadSpaces = useCallback(async () => {
    const nextSpaces = await fetchKnowledgeSpaces();
    setSpaces(nextSpaces);
    if (!selectedSpaceId && nextSpaces.length > 0) {
      setSelectedSpaceId(nextSpaces[0].id);
    }
  }, [selectedSpaceId]);

  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchManagementKnowledgeList(buildKnowledgeListQuery(listQuery));
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        rows: result.rows,
        status: 'ready',
        total: result.total,
      });
    } catch (loadError: unknown) {
      setListState((current) => ({
        ...current,
        error: normalizeRemoteRowsError(loadError),
        rows: [],
        status: 'error',
      }));
    }
  }, [listQuery]);

  useEffect(() => {
    let isCurrent = true;

    fetchRoleDefinitions()
      .then((definitions) => {
        if (isCurrent) {
          setRoleDefinitions(definitions);
          setRoleCatalogError(undefined);
        }
      })
      .catch((roleError: unknown) => {
        if (isCurrent) {
          setRoleDefinitions([]);
          setRoleCatalogError(`角色目录加载失败：${formatMutationError(roleError)}`);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  useEffect(() => {
    void reloadSpaces().catch((spaceError: unknown) => {
      message.error(formatMutationError(spaceError));
    });
  }, [reloadSpaces]);

  useEffect(() => {
    if (!selectedSpaceId) {
      setFolders([]);
      return;
    }
    void fetchKnowledgeFolders(selectedSpaceId)
      .then(setFolders)
      .catch((folderError: unknown) => {
        setFolders([]);
        message.error(formatMutationError(folderError));
      });
  }, [selectedSpaceId]);

  useEffect(() => {
    let isCurrent = true;
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchManagementKnowledgeList(buildKnowledgeListQuery(listQuery))
      .then((result) => {
        if (isCurrent) {
          setListState({
            page: result.page,
            pageSize: result.pageSize,
            rows: result.rows,
            status: 'ready',
            total: result.total,
          });
        }
      })
      .catch((loadError: unknown) => {
        if (isCurrent) {
          setListState((current) => ({
            ...current,
            error: normalizeRemoteRowsError(loadError),
            rows: [],
            status: 'error',
          }));
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [listQuery]);

  const openCreateModal = () => {
    setEditingDocument(null);
    setSelectedUploadFile(null);
    setDocumentInitialValues({
      chunk_strategy: 'simple_text',
      doc_type: 'manual',
      knowledge_space_id: selectedSpaceId,
      parser_engine: undefined,
      permission_roles: ['admin'],
    });
    setIsModalOpen(true);
  };

  const reloadDeposits = useCallback(async () => {
    setDepositsLoading(true);
    try {
      const deposits = await fetchKnowledgeDeposits('pending');
      setDepositRows(deposits);
    } catch (depositError) {
      message.error(formatMutationError(depositError));
    } finally {
      setDepositsLoading(false);
    }
  }, []);

  const openDepositsModal = useCallback(() => {
    setIsDepositsModalOpen(true);
    void reloadDeposits();
  }, [reloadDeposits]);

  const reloadImportJobs = useCallback(async (spaceId?: string) => {
    setImportJobsLoading(true);
    try {
      const importJobs = await fetchKnowledgeImportJobs({ knowledgeSpaceId: spaceId });
      setImportJobRows(importJobs);
    } catch (importJobError) {
      setImportJobRows([]);
      message.error(formatMutationError(importJobError));
    } finally {
      setImportJobsLoading(false);
    }
  }, []);

  const reloadImportWorkerStatus = useCallback(async () => {
    setImportWorkerStatusLoading(true);
    try {
      const status = await fetchKnowledgeImportWorkerStatus();
      setImportWorkerStatus(status);
    } catch (statusError) {
      setImportWorkerStatus(null);
      message.error(formatMutationError(statusError));
    } finally {
      setImportWorkerStatusLoading(false);
    }
  }, []);

  const openImportJobsModal = useCallback(() => {
    const spaceId = selectedSpaceId ?? spaces[0]?.id;
    setIsImportJobsModalOpen(true);
    void reloadImportJobs(spaceId);
    void reloadImportWorkerStatus();
  }, [reloadImportJobs, reloadImportWorkerStatus, selectedSpaceId, spaces]);

  const openSearchModal = useCallback(() => {
    setSearchInitialValues({ knowledge_space_id: selectedSpaceId, top_k: 5 });
    setSearchRows([]);
    setHasSearched(false);
    setIsSearchModalOpen(true);
  }, [selectedSpaceId]);

  const openEditModal = useCallback((row: KnowledgeRecord) => {
    setEditingDocument(row);
    setSelectedUploadFile(null);
    setDocumentInitialValues({
      content: row.content ?? '',
      doc_type: row.documentType,
      folder_id: row.folderId,
      index_status: row.status,
      knowledge_space_id: row.knowledgeSpaceId,
      permission_roles: row.permissionRoles?.length
        ? row.permissionRoles
        : splitCommaText(row.ownerRole),
      tags: joinTextList(row.tags),
      title: row.title,
    });
    setIsModalOpen(true);
    if (row.knowledgeSpaceId) {
      setSelectedSpaceId(row.knowledgeSpaceId);
    }
  }, []);

  const openAssetsModal = useCallback(async (row: KnowledgeRecord) => {
    setAssetsDocument(row);
    setAssetRows([]);
    setIsAssetsModalOpen(true);
    setAssetsLoading(true);
    try {
      const assets = await fetchKnowledgeDocumentAssets(row.id);
      setAssetRows(assets);
    } catch (assetError) {
      message.error(formatMutationError(assetError));
    } finally {
      setAssetsLoading(false);
    }
  }, []);

  const reloadChunks = useCallback(async (row: KnowledgeRecord, chunkSetId?: string) => {
    setChunksLoading(true);
    try {
      const chunks = await fetchKnowledgeChunks(row.id, chunkSetId);
      setChunkRows(chunks);
    } catch (chunkError) {
      setChunkRows([]);
      message.error(formatMutationError(chunkError));
    } finally {
      setChunksLoading(false);
    }
  }, []);

  const openChunksModal = useCallback(async (row: KnowledgeRecord) => {
    setChunksDocument(row);
    setChunkRows([]);
    setChunkSetRows([]);
    setIsChunksModalOpen(true);
    setChunkSetsLoading(true);
    try {
      const chunkSets = await fetchKnowledgeChunkSets(row.id);
      setChunkSetRows(chunkSets);
      const activeChunkSet = chunkSets.find((item) => item.isActive);
      await reloadChunks(row, activeChunkSet?.id);
    } catch (chunkSetError) {
      message.error(formatMutationError(chunkSetError));
    } finally {
      setChunkSetsLoading(false);
    }
  }, [reloadChunks]);

  const handleImportJobAction = useCallback(async (
    row: KnowledgeImportJobRecord,
    action: 'cancel' | 'retry' | 'run',
  ) => {
    try {
      if (action === 'run') {
        await runKnowledgeImportJob(row.id);
        message.success('导入任务已处理');
      } else if (action === 'retry') {
        await retryKnowledgeImportJob(row.id);
        message.success('导入任务已重新入队');
      } else {
        await cancelKnowledgeImportJob(row.id);
        message.success('导入任务已取消');
      }
      await Promise.all([
        reloadImportJobs(selectedSpaceId ?? spaces[0]?.id),
        reloadImportWorkerStatus(),
        reload(),
      ]);
    } catch (jobError) {
      message.error(formatMutationError(jobError));
    }
  }, [reload, reloadImportJobs, reloadImportWorkerStatus, selectedSpaceId, spaces]);

  const handleActivateChunkSet = useCallback(async (row: KnowledgeChunkSetRecord) => {
    if (!chunksDocument) {
      return;
    }
    try {
      await activateKnowledgeChunkSet(chunksDocument.id, row.id);
      message.success('分块版本已切换');
      const nextChunkSets = await fetchKnowledgeChunkSets(chunksDocument.id);
      setChunkSetRows(nextChunkSets);
      await reloadChunks(chunksDocument, row.id);
      await reload();
    } catch (chunkSetError) {
      message.error(formatMutationError(chunkSetError));
    }
  }, [chunksDocument, reload, reloadChunks]);

  const handleReparseDocument = useCallback(async (row: KnowledgeRecord) => {
    try {
      await reparseKnowledgeDocument(row.id, {
        chunk_strategy: 'parent_child',
        parser_engine: 'markdown',
      });
      message.success('文档已重新入队解析');
      await Promise.all([reloadImportJobs(selectedSpaceId ?? spaces[0]?.id), reload()]);
    } catch (reparseError) {
      message.error(formatMutationError(reparseError));
    }
  }, [reload, reloadImportJobs, selectedSpaceId, spaces]);

  const handleEditFolder = async (values: KnowledgeFolderEditFormValues) => {
    const folder = folders.find((item) => item.id === values.folder_id);
    if (!folder) {
      message.error('请选择知识目录');
      return;
    }
    try {
      await updateKnowledgeFolder(folder.id, {
        name: values.name?.trim() || folder.name,
        parent_folder_id: values.parent_folder_id ?? null,
        sort_order: values.sort_order,
        status: values.status,
      });
      const nextFolders = await fetchKnowledgeFolders(folder.knowledgeSpaceId);
      setFolders(nextFolders);
      setIsFolderEditModalOpen(false);
      message.success('知识目录已更新');
    } catch (folderError) {
      message.error(formatMutationError(folderError));
    }
  };

  const handleBatchMove = async (values: KnowledgeBatchMoveFormValues) => {
    if (selectedRowKeys.length === 0) {
      message.error('请选择要移动的知识文档');
      return;
    }
    try {
      const result = await batchMoveKnowledgeDocuments(
        selectedRowKeys.map(String),
        values.folder_id ?? null,
      );
      setSelectedRowKeys([]);
      setIsBatchMoveModalOpen(false);
      message.success(`已移动 ${result.updated.length} 条知识文档`);
      await reload();
    } catch (moveError) {
      message.error(formatMutationError(moveError));
    }
  };

  const handleSave = async (values: KnowledgeFormValues) => {
    if (!editingDocument && !selectedUploadFile && !values.content?.trim()) {
      message.error('请输入知识内容或选择上传文件');
      return;
    }
    const payload = {
      content: values.content?.trim(),
      doc_type: values.doc_type.trim(),
      folder_id: values.folder_id,
      index_status: editingDocument ? values.index_status : undefined,
      knowledge_space_id: values.knowledge_space_id,
      permission_roles: values.permission_roles ?? [],
      tags: splitCommaText(values.tags),
      title: values.title.trim(),
    };

    setIsSaving(true);
    try {
      if (editingDocument) {
        await updateManagementKnowledgeDocument(editingDocument.id, payload);
        message.success('知识文档已更新');
      } else if (selectedUploadFile && values.knowledge_space_id) {
        await uploadKnowledgeDocument({
          content_base64: selectedUploadFile.contentBase64,
          chunk_strategy: values.chunk_strategy,
          doc_type: values.doc_type.trim(),
          filename: selectedUploadFile.filename,
          folder_id: values.folder_id,
          knowledge_space_id: values.knowledge_space_id,
          mime_type: selectedUploadFile.mimeType,
          parser_engine: values.parser_engine,
          tags: splitCommaText(values.tags),
          title: values.title.trim(),
        });
        message.success('知识文件已上传，导入任务已入队');
      } else {
        await createManagementKnowledgeDocument(payload);
        message.success('知识文档已导入');
      }
      setIsModalOpen(false);
      void reload();
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = useCallback(async (row: KnowledgeRecord) => {
    try {
      await deleteManagementKnowledgeDocument(row.id);
      message.success('知识文档已删除');
      await reload();
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [reload]);

  const handleRetryIndex = useCallback(async (row: KnowledgeRecord) => {
    try {
      await retryKnowledgeDocumentIndex(row.id);
      message.success('知识索引已重试');
      await reload();
    } catch (retryError) {
      message.error(formatMutationError(retryError));
    }
  }, [reload]);

  const handleApproveDeposit = useCallback(async (row: KnowledgeDepositRecord) => {
    try {
      await approveKnowledgeDeposit(row.id, {
        permissionRoles: ['admin'],
        title: row.title,
      });
      message.success('知识沉淀已入库');
      await Promise.all([reloadDeposits(), reload()]);
    } catch (depositError) {
      message.error(formatMutationError(depositError));
    }
  }, [reload, reloadDeposits]);

  const openRejectDepositModal = useCallback((row: KnowledgeDepositRecord) => {
    setRejectingDeposit(row);
  }, []);

  const handleRejectDeposit = async (values: RejectDepositFormValues) => {
    if (!rejectingDeposit) {
      return;
    }
    try {
      await rejectKnowledgeDeposit(rejectingDeposit.id, values.reason.trim());
      message.success('知识沉淀已拒绝');
      setRejectingDeposit(null);
      await reloadDeposits();
    } catch (depositError) {
      message.error(formatMutationError(depositError));
    }
  };

  const handleSearch = async (values: KnowledgeSearchFormValues) => {
    setSearchLoading(true);
    try {
      const results = await fetchKnowledgeSearchResults(
        values.query.trim(),
        values.top_k ?? 5,
        values.knowledge_space_id,
      );
      setSearchRows(results);
      setHasSearched(true);
    } catch (searchError) {
      message.error(formatMutationError(searchError));
    } finally {
      setSearchLoading(false);
    }
  };

  const handleCreateSpace = async (values: KnowledgeSpaceFormValues) => {
    try {
      const space = await createKnowledgeSpace({
        code: values.code.trim(),
        description: values.description?.trim(),
        name: values.name.trim(),
      });
      setIsSpaceModalOpen(false);
      setSelectedSpaceId(space.id);
      documentFormRef.current?.setFieldValue('knowledge_space_id', space.id);
      setDocumentInitialValues((current) => ({ ...current, knowledge_space_id: space.id }));
      await reloadSpaces();
      message.success('知识空间已创建');
    } catch (spaceError) {
      message.error(formatMutationError(spaceError));
    }
  };

  const handleCreateFolder = async (values: KnowledgeFolderFormValues) => {
    const spaceId = documentFormRef.current?.getFieldValue('knowledge_space_id') || selectedSpaceId;
    if (!spaceId) {
      message.error('请先选择知识空间');
      return;
    }
    try {
      const folder = await createKnowledgeFolder(spaceId, { name: values.name.trim() });
      setIsFolderModalOpen(false);
      setSelectedSpaceId(spaceId);
      const nextFolders = await fetchKnowledgeFolders(spaceId);
      setFolders(nextFolders);
      documentFormRef.current?.setFieldValue('folder_id', folder.id);
      setDocumentInitialValues((current) => ({ ...current, folder_id: folder.id }));
      message.success('知识目录已创建');
    } catch (folderError) {
      message.error(formatMutationError(folderError));
    }
  };

  const handleFileInputChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      setSelectedUploadFile(null);
      return;
    }
    const contentBase64 = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = String(reader.result ?? '');
        resolve(result.includes(',') ? result.split(',')[1] : result);
      };
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
    setSelectedUploadFile({
      contentBase64,
      filename: file.name,
      mimeType: file.type || 'application/octet-stream',
    });
    if (!documentFormRef.current?.getFieldValue('title')) {
      const title = file.name.replace(/\.[^.]+$/, '');
      documentFormRef.current?.setFieldValue('title', title);
      setDocumentInitialValues((current) => ({ ...current, title }));
    }
  };

  const assetColumns = useMemo<ProColumns<KnowledgeAssetRecord>[]>(
    () => [
      {
        dataIndex: 'filename',
        title: '文件名',
      },
      {
        dataIndex: 'assetType',
        title: '资产类型',
        render: (_, row) => assetTypeLabels[row.assetType] ?? row.assetType,
      },
      {
        dataIndex: 'mimeType',
        title: 'MIME',
        render: (_, row) => row.mimeType ?? '-',
      },
      {
        dataIndex: 'sizeBytes',
        title: '大小',
        render: (_, row) => formatAssetSize(row.sizeBytes),
      },
      {
        dataIndex: 'storageProvider',
        title: '存储',
        render: (_, row) => row.storageProvider ?? '-',
      },
    ],
    [],
  );

  const importJobColumns = useMemo<ProColumns<KnowledgeImportJobRecord>[]>(
    () => [
      {
        dataIndex: 'documentTitle',
        title: '知识文档',
        render: (_, row) => row.documentTitle ?? row.documentId,
      },
      {
        dataIndex: 'assetFilename',
        title: '源文件',
        render: (_, row) => row.assetFilename ?? '-',
      },
      {
        dataIndex: 'folderPath',
        title: '目录',
        render: (_, row) => row.folderPath ?? '-',
      },
      {
        dataIndex: 'parserEngine',
        title: '解析器',
        render: (_, row) => row.parserEngine ?? '-',
      },
      {
        dataIndex: 'chunkStrategy',
        title: '切片策略',
        render: (_, row) => row.chunkStrategy ?? '-',
      },
      {
        dataIndex: 'progress',
        title: '进度',
        render: (_, row) => `${row.progress}%`,
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) => {
          const label = importJobStatusLabels[row.status] ?? { color: 'default', label: row.status };
          return <StatusTag color={label.color} label={label.label} />;
        },
      },
      {
        dataIndex: 'errorMessage',
        title: '失败原因',
        render: (_, row) => row.errorMessage ?? '-',
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            {['queued', 'failed'].includes(row.status) ? (
              <Button icon={<PlayCircleOutlined />} onClick={() => void handleImportJobAction(row, 'run')} type="link">
                运行
              </Button>
            ) : null}
            {['failed', 'cancelled'].includes(row.status) ? (
              <Button icon={<ReloadOutlined />} onClick={() => void handleImportJobAction(row, 'retry')} type="link">
                重试
              </Button>
            ) : null}
            {['queued', 'failed'].includes(row.status) ? (
              <Button danger icon={<StopOutlined />} onClick={() => void handleImportJobAction(row, 'cancel')} type="link">
                取消
              </Button>
            ) : null}
          </Space>
        ),
      },
    ],
    [handleImportJobAction],
  );

  const chunkSetColumns = useMemo<ProColumns<KnowledgeChunkSetRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        title: '分块版本',
      },
      {
        dataIndex: 'parserEngine',
        title: '解析器',
      },
      {
        dataIndex: 'chunkStrategy',
        title: '分块策略',
      },
      {
        dataIndex: 'chunkCount',
        title: 'chunk 数',
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) => (row.isActive ? <StatusTag color="green" label="当前生效" /> : row.status),
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button onClick={() => chunksDocument && void reloadChunks(chunksDocument, row.id)} type="link">
              预览
            </Button>
            {!row.isActive ? (
              <Button onClick={() => void handleActivateChunkSet(row)} type="link">
                切换
              </Button>
            ) : null}
          </Space>
        ),
      },
    ],
    [chunksDocument, handleActivateChunkSet, reloadChunks],
  );

  const chunkColumns = useMemo<ProColumns<KnowledgeChunkRecord>[]>(
    () => [
      {
        dataIndex: 'chunkIndex',
        title: '#',
        width: 64,
      },
      {
        dataIndex: 'chunkRole',
        title: '角色',
        render: (_, row) => {
          if (row.chunkRole === 'parent') {
            return '父块';
          }
          if (row.chunkRole === 'child') {
            return '子块';
          }
          if (row.chunkRole === 'regex_section') {
            return '正则分块';
          }
          return '普通块';
        },
      },
      {
        dataIndex: 'heading',
        title: '标题层级',
        render: (_, row) => row.heading ?? '-',
      },
      {
        key: 'source',
        title: '来源',
        render: (_, row) => {
          const sourceParts = [
            row.pageNumber ? `第 ${row.pageNumber} 页` : undefined,
            row.tableIndex ? `表格 ${row.tableIndex}` : undefined,
            row.imageCount ? `图片 ${row.imageCount}` : undefined,
            row.tableCount ? `表格数 ${row.tableCount}` : undefined,
            row.sectionTitle ? `分段：${row.sectionTitle}` : undefined,
            row.splitPattern ? `规则：${row.splitPattern}` : undefined,
            row.sourceKind,
            row.sourceAssetType,
            row.tableColumns?.length ? `列：${row.tableColumns.join(', ')}` : undefined,
            row.imageRefs?.length ? `图：${row.imageRefs.join(', ')}` : undefined,
          ].filter(Boolean);
          return sourceParts.length > 0 ? sourceParts.join(' / ') : '-';
        },
      },
      {
        dataIndex: 'content',
        title: '内容',
      },
      {
        dataIndex: 'parentChunkId',
        title: '父块',
        render: (_, row) => row.parentChunkId ?? '-',
      },
    ],
    [],
  );

  const columns = useMemo<ProColumns<KnowledgeRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        sorter: true,
        title: '知识编号',
      },
      {
        dataIndex: 'title',
        sorter: true,
        title: '知识标题',
      },
      {
        dataIndex: 'knowledgeSpaceId',
        title: '知识空间',
        render: (_, row) => (row.knowledgeSpaceId ? spaceNameById.get(row.knowledgeSpaceId) ?? row.knowledgeSpaceId : '-'),
      },
      {
        dataIndex: 'folderPath',
        title: '目录',
        render: (_, row) => row.folderPath ?? '-',
      },
      {
        dataIndex: 'documentType',
        sorter: true,
        title: '类型',
      },
      {
        dataIndex: 'ownerRole',
        sorter: true,
        title: '权限角色',
      },
      {
        dataIndex: 'status',
        sorter: true,
        title: '状态',
        render: (_, row) => {
          const statusLabel = statusLabels[row.status];
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
      },
      {
        dataIndex: 'indexError',
        title: '索引错误',
        render: (_, row) => row.indexError || row.vectorIndexError || '-',
      },
      {
        dataIndex: 'updatedAt',
        sorter: true,
        title: '更新时间',
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button aria-label="资产" icon={<FileSearchOutlined />} onClick={() => void openAssetsModal(row)} type="link">
              资产
            </Button>
            <Button aria-label="分块" icon={<NodeIndexOutlined />} onClick={() => void openChunksModal(row)} type="link">
              分块
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => void handleReparseDocument(row)} type="link">
              重解析
            </Button>
            <Button icon={<EditOutlined />} onClick={() => openEditModal(row)} type="link">
              编辑
            </Button>
            {row.status === 'index_failed' || row.status === 'text_indexed' ? (
              <Button icon={<ReloadOutlined />} onClick={() => handleRetryIndex(row)} type="link">
                {row.status === 'text_indexed' ? '补向量索引' : '重试索引'}
              </Button>
            ) : null}
            <Popconfirm okText="删除" onConfirm={() => handleDelete(row)} title={`删除知识 ${row.id}？`}>
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [
      handleDelete,
      handleReparseDocument,
      handleRetryIndex,
      openAssetsModal,
      openChunksModal,
      openEditModal,
      spaceNameById,
    ],
  );

  const depositColumns = useMemo<ProColumns<KnowledgeDepositRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        title: '沉淀编号',
      },
      {
        dataIndex: 'title',
        title: '沉淀标题',
      },
      {
        dataIndex: 'aiTaskId',
        title: '任务编号',
      },
      {
        dataIndex: 'content',
        title: '内容摘要',
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) => {
          const label = depositStatusLabels[row.status] ?? { color: 'default', label: row.status };
          return <StatusTag color={label.color} label={label.label} />;
        },
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) =>
          row.status === 'pending' ? (
            <Space size={4}>
              <Button onClick={() => handleApproveDeposit(row)} type="link">
                批准入库
              </Button>
              <Button danger onClick={() => openRejectDepositModal(row)} type="link">
                拒绝
              </Button>
            </Space>
          ) : null,
      },
    ],
    [handleApproveDeposit, openRejectDepositModal],
  );

  const searchColumns = useMemo<ProColumns<KnowledgeSearchResultRecord>[]>(
    () => [
      {
        dataIndex: 'title',
        title: '知识标题',
      },
      {
        dataIndex: 'sourceLabel',
        title: '来源',
      },
      {
        dataIndex: 'retrievalMode',
        title: '召回模式',
        render: (_, row) => (row.retrievalMode === 'vector' ? '向量' : '关键词'),
      },
      {
        dataIndex: 'content',
        title: '内容摘要',
      },
    ],
    [],
  );

  return (
    <>
      <ManagementListPage<KnowledgeRecord>
        breadcrumbGroup="产品资产"
        columns={columns}
        dataSource={listState.rows}
        viewStorageKey="assets.knowledge"
        filters={[
          { label: '知识标题', name: 'title', type: 'text' },
          {
            label: '知识空间',
            name: 'knowledgeSpaceId',
            options: spaceOptions,
            type: 'select',
          },
          {
            label: '目录',
            name: 'folderId',
            options: folderOptions,
            type: 'select',
          },
          {
            label: '类型',
            name: 'documentType',
            options: [
              { label: 'PRD', value: 'PRD' },
              { label: 'Spec', value: 'Spec' },
              { label: 'Deposit', value: 'Deposit' },
              { label: 'Manual', value: 'manual' },
            ],
            type: 'select',
          },
          { label: '权限角色', name: 'ownerRole', type: 'text' },
          {
            label: '状态',
            name: 'status',
            options: [
              { label: '已索引', value: 'indexed' },
              { label: '文本索引', value: 'text_indexed' },
              { label: '向量索引', value: 'vector_indexed' },
              { label: '待索引', value: 'pending_index' },
              { label: '索引中', value: 'importing' },
              { label: '索引失败', value: 'index_failed' },
              { label: '已归档', value: 'archived' },
            ],
            type: 'select',
          },
        ]}
        loading={listState.status === 'loading'}
        notice={formatRemoteRowsError(listState.error) ?? roleCatalogError}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="导入文档"
        remote={{
          onChange: (query) => {
            const nextSpaceId = normalizeFilterText(query.filters.knowledgeSpaceId);
            if (nextSpaceId) {
              setSelectedSpaceId(nextSpaceId);
            }
            setListQuery(query);
          },
          page: listState.page,
          pageSize: listState.pageSize,
          total: listState.total,
        }}
        rowKey="id"
        rowSelection={{
          onChange: (keys) => setSelectedRowKeys(keys),
          selectedRowKeys,
        }}
        tableTitle="知识列表"
        title="知识中心"
        toolbarActions={[
          <Button icon={<PlusOutlined />} key="create-space" onClick={() => setIsSpaceModalOpen(true)}>
            新建空间
          </Button>,
          <Button aria-label="导入任务" icon={<DatabaseOutlined />} key="import-jobs" onClick={openImportJobsModal}>
            导入任务
          </Button>,
          <Button icon={<FolderOpenOutlined />} key="folder-edit" onClick={() => setIsFolderEditModalOpen(true)}>
            目录整理
          </Button>,
          <Button
            disabled={selectedRowKeys.length === 0}
            icon={<FolderOpenOutlined />}
            key="batch-move"
            onClick={() => setIsBatchMoveModalOpen(true)}
          >
            批量移动
          </Button>,
          <Button aria-label="知识检索" icon={<SearchOutlined />} key="knowledge-search" onClick={openSearchModal}>
            知识检索
          </Button>,
          <Button key="deposit-review" onClick={openDepositsModal}>
            沉淀审核
          </Button>,
        ]}
      />
      <Modal
        footer={null}
        onCancel={() => setIsImportJobsModalOpen(false)}
        open={isImportJobsModalOpen}
        title="导入任务"
        width={980}
      >
        <Space
          style={{ justifyContent: 'space-between', marginBottom: 12, width: '100%' }}
          wrap
        >
          <Space wrap>
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
          <Button
            icon={<ReloadOutlined />}
            loading={importWorkerStatusLoading}
            onClick={() => void reloadImportWorkerStatus()}
          >
            刷新状态
          </Button>
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
      </Modal>
      <Modal
        footer={null}
        onCancel={() => setIsAssetsModalOpen(false)}
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
        onCancel={() => setIsChunksModalOpen(false)}
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
      <Modal
        destroyOnHidden
        footer={null}
        onCancel={() => setIsSearchModalOpen(false)}
        open={isSearchModalOpen}
        title="知识检索"
        width={860}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Form<KnowledgeSearchFormValues>
            initialValues={searchInitialValues}
            layout="inline"
            onFinish={(values) => void handleSearch(values)}
            preserve={false}
          >
            <Form.Item label="知识空间" name="knowledge_space_id">
              <Select
                allowClear
                onChange={(value) => setSelectedSpaceId(value)}
                options={spaceOptions}
                placeholder="全部可访问空间"
                style={{ minWidth: 220 }}
              />
            </Form.Item>
            <Form.Item
              label="检索关键词"
              name="query"
              rules={[{ required: true, message: '请输入检索关键词' }]}
            >
              <Input aria-label="检索关键词" placeholder="输入需求、技术方案或规则关键词" />
            </Form.Item>
            <Form.Item label="返回条数" name="top_k">
              <InputNumber min={1} max={20} precision={0} />
            </Form.Item>
            <Form.Item>
              <Button
                aria-label="检索"
                htmlType="submit"
                loading={searchLoading}
                type="primary"
              >
                检索
              </Button>
            </Form.Item>
          </Form>
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
        </Space>
      </Modal>
      <Modal
        footer={null}
        onCancel={() => setIsDepositsModalOpen(false)}
        open={isDepositsModalOpen}
        title="沉淀审核"
        width={920}
      >
        <ProTable<KnowledgeDepositRecord>
          columns={depositColumns}
          dataSource={depositRows}
          loading={depositsLoading}
          options={false}
          pagination={false}
          rowKey="id"
          search={false}
        />
        {depositRows.length === 0 && !depositsLoading ? (
          <Text type="secondary">当前没有待审核知识沉淀。</Text>
        ) : null}
      </Modal>
      <Modal
        confirmLoading={isSaving}
        destroyOnHidden
        onCancel={() => setIsModalOpen(false)}
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
          <Form.Item label="知识空间" name="knowledge_space_id">
            <Select
              allowClear
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
                    { label: 'OCR JSON', value: 'ocr_json' },
                    { label: '表格 JSON', value: 'table_json' },
                  ]}
                  placeholder="按文件类型自动选择"
                />
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
                      style={{ display: 'none' }}
                      type="file"
                    />
                  </label>
                </Button>
                {selectedUploadFile ? (
                  <Text type="secondary">{selectedUploadFile.filename}</Text>
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
        onCancel={() => setIsSpaceModalOpen(false)}
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
        onCancel={() => setIsFolderModalOpen(false)}
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
        onCancel={() => setIsFolderEditModalOpen(false)}
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
        onCancel={() => setIsBatchMoveModalOpen(false)}
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
