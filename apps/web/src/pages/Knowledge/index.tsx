import {
  DeleteOutlined,
  EditOutlined,
  FileSearchOutlined,
  FolderOpenOutlined,
  MoreOutlined,
  NodeIndexOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  StopOutlined,
} from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Dropdown, Modal, Space, message } from 'antd';
import type { FormInstance } from 'antd';
import { type ChangeEvent, type Key, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ManagementListQuery } from '../../components/ManagementListPage';
import type { KnowledgeRecord, RequirementRecord } from '../../data/management';
import { type UserRoleDefinition, toUserRoleOptions } from '../../data/roles';
import { formatRemoteRowsError, normalizeRemoteRowsError, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  approveKnowledgeDeposit,
  askKnowledgeRag,
  activateKnowledgeChunkSet,
  batchMoveKnowledgeDocuments,
  cancelKnowledgeImportJob,
  createKnowledgeFolder,
  createKnowledgeProcessingProfile,
  createKnowledgeSpace,
  createManagementKnowledgeDocument,
  deleteManagementKnowledgeDocument,
  fetchKnowledgeChunks,
  fetchKnowledgeCitationFeedback,
  fetchKnowledgeChunkSets,
  fetchKnowledgeDeposits,
  fetchKnowledgeDocumentAssets,
  fetchKnowledgeDocumentVersions,
  fetchKnowledgeFolders,
  fetchKnowledgeIndexHealth,
  fetchKnowledgeImportJobs,
  fetchKnowledgeImportWorkerStatus,
  fetchKnowledgeProcessingProfiles,
  fetchKnowledgeSearchResults,
  fetchKnowledgeSpaces,
  fetchKnowledgeStaleness,
  fetchLifecycleFullChain,
  fetchManagementKnowledgeList,
  fetchManagementRequirementList,
  fetchRoleDefinitions,
  rejectKnowledgeDeposit,
  recordKnowledgeCitationClick,
  recordKnowledgeQualityFeedback,
  reparseKnowledgeDocument,
  retryKnowledgeImportJob,
  retryKnowledgeDocumentIndex,
  runKnowledgeImportJob,
  scanKnowledgeStaleness,
  updateManagementKnowledgeDocument,
  updateKnowledgeFolder,
  updateKnowledgeProcessingProfile,
  uploadKnowledgeDocumentFile,
  type KnowledgeChunkRecord,
  type KnowledgeCitationFeedbackRecord,
  type KnowledgeChunkSetRecord,
  type KnowledgeFolderRecord,
  type KnowledgeDocumentVersionRecord,
  type KnowledgeAssetRecord,
  type KnowledgeImportJobRecord,
  type KnowledgeImportWorkerStatusRecord,
  type KnowledgeProcessingProfileRecord,
  type KnowledgeStalenessRecord,
  type KnowledgeQualityFeedbackValue,
  type KnowledgeDepositRecord,
  type KnowledgeRagAnswerRecord,
  type KnowledgeRagCitationRecord,
  type KnowledgeSearchResultRecord,
  type KnowledgeSpaceRecord,
  type RemoteListPerformance,
  type RequirementFullChainRecord,
} from '../../services/aiBrain';
import { formatMutationError, joinTextList, splitCommaText } from '../../utils/managementCrud';
import {
  KnowledgeIndexHealthPanel,
  type KnowledgeIndexHealthState,
} from './components/KnowledgeIndexHealthPanel';
import { KnowledgePageDialogs } from './components/KnowledgePageDialogs';
import {
  KnowledgeProcessingGovernancePanel,
  type KnowledgeProcessingProfileFormValues,
} from './components/KnowledgeProcessingGovernancePanel';
import { KnowledgeWorkbenchPanels } from './components/KnowledgeWorkbenchPanels';
import {
  assetTypeLabels,
  buildKnowledgeListQuery,
  depositStatusLabels,
  formatAssetSize,
  hasFilterValues,
  importJobStatusLabels,
  INITIAL_STALENESS_SUMMARY,
  isNoisyKnowledgeSpace,
  KNOWLEDGE_ACTION_COLUMN_WIDTH,
  KNOWLEDGE_TABLE_SCROLL_X,
  modalityLabels,
  normalizeAdvancedFilters,
  normalizeFilterText,
  removeAdvancedFilters,
  statusLabels,
} from './knowledgePageHelpers';
import type {
  KnowledgeAdvancedFilterValues,
  KnowledgeBatchMoveFormValues,
  KnowledgeFolderEditFormValues,
  KnowledgeFolderFormValues,
  KnowledgeFormValues,
  KnowledgeSearchFormValues,
  KnowledgeSpaceFormValues,
  KnowledgeWorkbenchTab,
  RejectDepositFormValues,
} from './types';

export default function KnowledgePage() {
  const advancedFilterSubmitRef = useRef<HTMLButtonElement>(null);
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
  const [processingProfiles, setProcessingProfiles] = useState<KnowledgeProcessingProfileRecord[]>([]);
  const [processingGovernanceLoading, setProcessingGovernanceLoading] = useState(false);
  const [stalenessScanning, setStalenessScanning] = useState(false);
  const [stalenessItems, setStalenessItems] = useState<KnowledgeStalenessRecord[]>([]);
  const [stalenessSummary, setStalenessSummary] = useState(INITIAL_STALENESS_SUMMARY);
  const [chunkRows, setChunkRows] = useState<KnowledgeChunkRecord[]>([]);
  const [detailVersionRows, setDetailVersionRows] = useState<KnowledgeDocumentVersionRecord[]>([]);
  const [detailFeedbackRows, setDetailFeedbackRows] = useState<KnowledgeCitationFeedbackRecord[]>([]);
  const [detailGovernanceLoading, setDetailGovernanceLoading] = useState(false);
  const [chunkSetRows, setChunkSetRows] = useState<KnowledgeChunkSetRecord[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [chunkSetsLoading, setChunkSetsLoading] = useState(false);
  const [isAssetsModalOpen, setIsAssetsModalOpen] = useState(false);
  const [isBatchMoveModalOpen, setIsBatchMoveModalOpen] = useState(false);
  const [isChunksModalOpen, setIsChunksModalOpen] = useState(false);
  const [isFolderEditModalOpen, setIsFolderEditModalOpen] = useState(false);
  const [isFolderModalOpen, setIsFolderModalOpen] = useState(false);
  const [isSpaceModalOpen, setIsSpaceModalOpen] = useState(false);
  const [activeWorkbenchTab, setActiveWorkbenchTab] = useState<KnowledgeWorkbenchTab>('documents');
  const [advancedFilterValues, setAdvancedFilterValues] = useState<KnowledgeAdvancedFilterValues>({});
  const [editingDocument, setEditingDocument] = useState<KnowledgeRecord | null>(null);
  const [isAdvancedFilterOpen, setIsAdvancedFilterOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [fullChainDeposit, setFullChainDeposit] = useState<KnowledgeDepositRecord | null>(null);
  const [fullChain, setFullChain] = useState<RequirementFullChainRecord | null>(null);
  const [fullChainError, setFullChainError] = useState<RemoteRowsError>();
  const [fullChainVersionRequirements, setFullChainVersionRequirements] = useState<RequirementRecord[]>([]);
  const [isFullChainLoading, setIsFullChainLoading] = useState(false);
  const [rejectingDeposit, setRejectingDeposit] = useState<KnowledgeDepositRecord | null>(null);
  const [detailDocument, setDetailDocument] = useState<KnowledgeRecord | null>(null);
  const [searchRows, setSearchRows] = useState<KnowledgeSearchResultRecord[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [ragAnswer, setRagAnswer] = useState<KnowledgeRagAnswerRecord | null>(null);
  const [ragFeedbackSubmittingValue, setRagFeedbackSubmittingValue] =
    useState<KnowledgeQualityFeedbackValue>();
  const [ragFeedbackValue, setRagFeedbackValue] = useState<KnowledgeQualityFeedbackValue>();
  const [isSaving, setIsSaving] = useState(false);
  const [documentInitialValues, setDocumentInitialValues] = useState<Partial<KnowledgeFormValues>>({});
  const [selectedSpaceId, setSelectedSpaceId] = useState<string | undefined>();
  const [selectedUploadFile, setSelectedUploadFile] = useState<{
    file: File;
    filename: string;
    mimeType: string;
    sizeBytes: number;
  } | null>(null);
  const [folders, setFolders] = useState<KnowledgeFolderRecord[]>([]);
  const [showNoisySpaces, setShowNoisySpaces] = useState(false);
  const [spaceSearchText, setSpaceSearchText] = useState('');
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
    performance?: RemoteListPerformance;
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
  const [knowledgeHealthState, setKnowledgeHealthState] = useState<KnowledgeIndexHealthState>({
    status: 'loading',
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
  const processingProfileOptions = useMemo(
    () => processingProfiles
      .filter((profile) => profile.status === 'active')
      .map((profile) => ({
        label: `${profile.name} (${profile.providerType})`,
        value: profile.id,
      })),
    [processingProfiles],
  );
  const spaceNameById = useMemo(
    () => new Map(spaces.map((space) => [space.id, space.name])),
    [spaces],
  );
  const selectedSpace = useMemo(
    () => spaces.find((space) => space.id === selectedSpaceId),
    [selectedSpaceId, spaces],
  );
  const selectedFolderId = normalizeFilterText(listQuery.filters.folderId);
  const visibleSpaces = useMemo(() => {
    const searchText = spaceSearchText.trim().toLowerCase();
    return spaces.filter((space) => {
      const matchesSearch = searchText
        ? `${space.name} ${space.code}`.toLowerCase().includes(searchText)
        : true;
      if (!matchesSearch) {
        return false;
      }
      if (showNoisySpaces || space.id === selectedSpaceId) {
        return true;
      }
      return !isNoisyKnowledgeSpace(space);
    });
  }, [selectedSpaceId, showNoisySpaces, spaceSearchText, spaces]);
  const hiddenNoisySpaceCount = useMemo(
    () => spaces.filter((space) => isNoisyKnowledgeSpace(space) && space.id !== selectedSpaceId).length,
    [selectedSpaceId, spaces],
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
    setKnowledgeHealthState((current) => ({ ...current, status: 'loading' }));
    try {
      const query = buildKnowledgeListQuery(listQuery);
      const result = await fetchManagementKnowledgeList(query);
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        performance: result.performance,
        rows: result.rows,
        status: 'ready',
        total: result.total,
      });
      const health = await fetchKnowledgeIndexHealth(query);
      setKnowledgeHealthState({
        record: health,
        status: 'ready',
      });
    } catch (loadError: unknown) {
      setListState((current) => ({
        ...current,
        error: normalizeRemoteRowsError(loadError),
        rows: [],
        status: 'error',
      }));
      setKnowledgeHealthState({
        error: formatMutationError(loadError),
        status: 'error',
      });
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
    setKnowledgeHealthState((current) => ({ ...current, status: 'loading' }));
    const query = buildKnowledgeListQuery(listQuery);
    Promise.all([
      fetchManagementKnowledgeList(query),
      fetchKnowledgeIndexHealth(query),
    ])
      .then(([result, health]) => {
        if (isCurrent) {
          setListState({
            page: result.page,
            pageSize: result.pageSize,
            performance: result.performance,
            rows: result.rows,
            status: 'ready',
            total: result.total,
          });
          setKnowledgeHealthState({
            record: health,
            status: 'ready',
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
          setKnowledgeHealthState({
            error: formatMutationError(loadError),
            status: 'error',
          });
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

  const closeFullChainModal = useCallback(() => {
    setFullChainDeposit(null);
    setFullChain(null);
    setFullChainError(undefined);
    setFullChainVersionRequirements([]);
    setIsFullChainLoading(false);
  }, []);

  const openFullChainModal = useCallback(async (row: KnowledgeDepositRecord) => {
    setFullChainDeposit(row);
    setFullChain(null);
    setFullChainError(undefined);
    setFullChainVersionRequirements([]);
    setIsFullChainLoading(true);
    try {
      const loadedChain = await fetchLifecycleFullChain('knowledge_deposit', row.id);
      setFullChain(loadedChain);
      if (loadedChain.iterationVersion?.id) {
        try {
          const versionRequirements = await fetchManagementRequirementList({
            page: 1,
            pageSize: 100,
            sortField: 'created_at',
            sortOrder: 'descend',
            versionId: loadedChain.iterationVersion.id,
          });
          setFullChainVersionRequirements(versionRequirements.rows);
        } catch {
          setFullChainVersionRequirements([]);
        }
      }
    } catch (loadError: unknown) {
      setFullChainError(normalizeRemoteRowsError(loadError));
      setFullChainVersionRequirements([]);
    } finally {
      setIsFullChainLoading(false);
    }
  }, []);

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

  const reloadProcessingProfiles = useCallback(async () => {
    const profiles = await fetchKnowledgeProcessingProfiles();
    setProcessingProfiles(profiles);
    return profiles;
  }, []);

  const reloadProcessingGovernance = useCallback(async () => {
    setProcessingGovernanceLoading(true);
    try {
      const [profiles, staleness] = await Promise.all([
        fetchKnowledgeProcessingProfiles(),
        fetchKnowledgeStaleness(selectedSpaceId),
      ]);
      setProcessingProfiles(profiles);
      setStalenessItems(staleness.items);
      setStalenessSummary(staleness.summary);
    } catch (governanceError) {
      message.error(formatMutationError(governanceError));
    } finally {
      setProcessingGovernanceLoading(false);
    }
  }, [selectedSpaceId]);

  const handleCreateProcessingProfile = useCallback(async (
    values: KnowledgeProcessingProfileFormValues,
  ) => {
    await createKnowledgeProcessingProfile({
      capabilities: values.capabilities,
      credential_ref: values.credential_ref?.trim() || undefined,
      name: values.name.trim(),
      provider_config: {
        ...(values.endpoint_url?.trim() ? { endpoint_url: values.endpoint_url.trim() } : {}),
        ...(values.stale_after_days ? { stale_after_days: values.stale_after_days } : {}),
      },
      provider_type: values.provider_type,
    });
    message.success('知识处理配置已创建');
    await reloadProcessingGovernance();
  }, [reloadProcessingGovernance]);

  const handleToggleProcessingProfile = useCallback(async (
    profile: KnowledgeProcessingProfileRecord,
    enabled: boolean,
  ) => {
    await updateKnowledgeProcessingProfile(profile.id, {
      status: enabled ? 'active' : 'disabled',
    });
    message.success(enabled ? '处理配置已启用' : '处理配置已停用');
    await reloadProcessingGovernance();
  }, [reloadProcessingGovernance]);

  const handleScanStaleness = useCallback(async () => {
    setStalenessScanning(true);
    try {
      const result = await scanKnowledgeStaleness();
      message.success(`过期扫描完成，发现 ${result.expiredCount} 个过期版本`);
      await reloadProcessingGovernance();
    } catch (scanError) {
      message.error(formatMutationError(scanError));
    } finally {
      setStalenessScanning(false);
    }
  }, [reloadProcessingGovernance]);

  const openImportJobsModal = useCallback(() => {
    const spaceId = selectedSpaceId ?? spaces[0]?.id;
    setActiveWorkbenchTab('imports');
    void reloadImportJobs(spaceId);
    void reloadImportWorkerStatus();
  }, [reloadImportJobs, reloadImportWorkerStatus, selectedSpaceId, spaces]);

  const openSearchModal = useCallback(() => {
    setSearchRows([]);
    setHasSearched(false);
    setRagAnswer(null);
    setActiveWorkbenchTab('search');
  }, []);

  const handleWorkbenchTabChange = useCallback((tabKey: string) => {
    const nextTab = tabKey as KnowledgeWorkbenchTab;
    setActiveWorkbenchTab(nextTab);
    if (nextTab === 'imports') {
      const spaceId = selectedSpaceId ?? spaces[0]?.id;
      void reloadImportJobs(spaceId);
      void reloadImportWorkerStatus();
    }
    if (nextTab === 'deposits') {
      void reloadDeposits();
    }
    if (nextTab === 'processing') {
      void reloadProcessingGovernance();
    }
  }, [
    reloadDeposits,
    reloadImportJobs,
    reloadImportWorkerStatus,
    reloadProcessingGovernance,
    selectedSpaceId,
    spaces,
  ]);

  const selectWorkbenchSpace = useCallback((spaceId: string) => {
    setSelectedSpaceId(spaceId);
    setListQuery((current) => ({
      ...current,
      filters: {
        ...current.filters,
        folderId: undefined,
        knowledgeSpaceId: spaceId,
      },
      page: 1,
    }));
  }, []);

  const selectWorkbenchFolder = useCallback((folderId?: string) => {
    setListQuery((current) => ({
      ...current,
      filters: {
        ...current.filters,
        folderId,
        knowledgeSpaceId: selectedSpaceId,
      },
      page: 1,
    }));
  }, [selectedSpaceId]);

  const openDocumentDetail = useCallback((row: KnowledgeRecord) => {
    setDetailDocument(row);
    setDetailVersionRows([]);
    setDetailFeedbackRows([]);
  }, []);

  const loadDocumentGovernance = useCallback(async (row: KnowledgeRecord) => {
    setDetailGovernanceLoading(true);
    try {
      const [versions, feedback] = await Promise.all([
        fetchKnowledgeDocumentVersions(row.id),
        fetchKnowledgeCitationFeedback(row.id),
      ]);
      setDetailVersionRows(versions);
      setDetailFeedbackRows(feedback);
    } catch (governanceError) {
      message.error(formatMutationError(governanceError));
    } finally {
      setDetailGovernanceLoading(false);
    }
  }, []);

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
        chunk_strategy: row.chunkStrategy ?? 'parent_child',
        parser_engine: row.parserEngine ?? 'markdown',
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
    if (!values.knowledge_space_id) {
      message.error('请选择知识空间');
      return;
    }
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
      } else if (selectedUploadFile) {
        await uploadKnowledgeDocumentFile({
          chunkStrategy: values.chunk_strategy,
          docType: values.doc_type.trim(),
          file: selectedUploadFile.file,
          folderId: values.folder_id,
          knowledgeSpaceId: values.knowledge_space_id,
          parserEngine: values.parser_engine,
          processingProfileId: values.processing_profile_id,
          expiresInDays: values.expires_in_days,
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

  const confirmDeleteDocument = useCallback((row: KnowledgeRecord) => {
    Modal.confirm({
      content: '删除后该文档不会再出现在知识检索和问答结果中。',
      okButtonProps: { danger: true },
      okText: '删除',
      onOk: () => handleDelete(row),
      title: `删除知识 ${row.id}？`,
    });
  }, [handleDelete]);

  const handleRetryIndex = useCallback(async (row: KnowledgeRecord) => {
    try {
      await retryKnowledgeDocumentIndex(row.id);
      message.success('知识索引已重试');
      await reload();
    } catch (retryError) {
      message.error(formatMutationError(retryError));
    }
  }, [reload]);

  const handleAdvancedFilterSubmit = useCallback((values: KnowledgeAdvancedFilterValues) => {
    const normalizedValues = normalizeAdvancedFilters(values);
    setAdvancedFilterValues(normalizedValues);
    setIsAdvancedFilterOpen(false);
    setListQuery((current) => ({
      ...current,
      filters: {
        ...removeAdvancedFilters(current.filters),
        ...normalizedValues,
      },
      page: 1,
    }));
  }, []);

  const clearAdvancedFilters = useCallback(() => {
    setAdvancedFilterValues({});
    setListQuery((current) => ({
      ...current,
      filters: removeAdvancedFilters(current.filters),
      page: 1,
    }));
  }, []);

  const handleListQueryChange = useCallback((query: ManagementListQuery) => {
    const isFullReset =
      !hasFilterValues(query.filters) &&
      query.page === 1 &&
      !query.sortField &&
      !query.sortOrder;
    const nextAdvancedValues = isFullReset ? {} : advancedFilterValues;
    if (isFullReset && hasFilterValues(advancedFilterValues)) {
      setAdvancedFilterValues({});
    }
    const nextFilters: ManagementListQuery['filters'] = {
      ...query.filters,
      ...nextAdvancedValues,
    };
    const nextSpaceId = normalizeFilterText(nextFilters.knowledgeSpaceId);
    if (nextSpaceId) {
      setSelectedSpaceId(nextSpaceId);
    }
    setListQuery({
      ...query,
      filters: nextFilters,
    });
  }, [advancedFilterValues]);

  const handleApproveDeposit = useCallback(async (row: KnowledgeDepositRecord) => {
    if (!selectedSpaceId) {
      message.error('请先选择沉淀入库的知识空间');
      return;
    }
    try {
      await approveKnowledgeDeposit(row.id, {
        folderId: undefined,
        knowledgeSpaceId: selectedSpaceId,
        permissionRoles: ['admin'],
        title: row.title,
      });
      message.success('知识沉淀已入库');
      await Promise.all([reloadDeposits(), reload()]);
    } catch (depositError) {
      message.error(formatMutationError(depositError));
    }
  }, [reload, reloadDeposits, selectedSpaceId]);

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
    setRagAnswer(null);
    setRagFeedbackSubmittingValue(undefined);
    setRagFeedbackValue(undefined);
    try {
      const searchSpaceId = values.knowledge_space_id || selectedSpaceId;
      const [results, answer] = await Promise.all([
        fetchKnowledgeSearchResults(
          values.query.trim(),
          values.top_k ?? 5,
          searchSpaceId,
        ),
        askKnowledgeRag(
          values.query.trim(),
          values.top_k ?? 6,
          searchSpaceId,
        ).catch(() => null),
      ]);
      setSearchRows(results);
      setRagAnswer(answer);
      setHasSearched(true);
    } catch (searchError) {
      message.error(formatMutationError(searchError));
    } finally {
      setSearchLoading(false);
    }
  };

  const handleRagFeedback = useCallback(
    async (feedbackValue: KnowledgeQualityFeedbackValue) => {
      const relatedEventId = ragAnswer?.metrics?.qualityEventId;
      if (!relatedEventId) {
        message.warning('本次问答缺少质量事件，暂不能记录反馈');
        return;
      }
      setRagFeedbackSubmittingValue(feedbackValue);
      try {
        const primaryCitation = ragAnswer?.citations[0];
        await recordKnowledgeQualityFeedback({
          citationChunkId: primaryCitation?.chunkId,
          citationDocumentId: primaryCitation?.documentId,
          feedbackValue,
          relatedEventId,
        });
        setRagFeedbackValue(feedbackValue);
        message.success(
          feedbackValue === 'useful'
            ? '已记录有用反馈'
            : feedbackValue === 'outdated'
              ? '已标记引用内容过期'
              : '已记录无用反馈',
        );
      } catch (feedbackError) {
        message.error(formatMutationError(feedbackError));
      } finally {
        setRagFeedbackSubmittingValue(undefined);
      }
    },
    [ragAnswer],
  );

  const handleRecordCitationClick = useCallback(
    async (citation: KnowledgeRagCitationRecord) => {
      const relatedEventId = ragAnswer?.metrics?.qualityEventId;
      if (!relatedEventId) {
        message.warning('本次问答缺少质量事件，暂不能记录引用点击');
        return;
      }
      try {
        await recordKnowledgeCitationClick({
          citationChunkId: citation.chunkId,
          citationDocumentId: citation.documentId,
          relatedEventId,
        });
        message.success('已记录引用点击');
      } catch (citationError) {
        message.error(formatMutationError(citationError));
      }
    },
    [ragAnswer?.metrics?.qualityEventId],
  );

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
    setSelectedUploadFile({
      file,
      filename: file.name,
      mimeType: file.type || 'application/octet-stream',
      sizeBytes: file.size,
    });
    if (file.type.startsWith('image/')) {
      documentFormRef.current?.setFieldValue('parser_engine', 'multimodal');
      void reloadProcessingProfiles().catch((profileError) => {
        message.error(formatMutationError(profileError));
      });
    }
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
        dataIndex: 'documentVersionId',
        title: '文档版本',
        render: (_, row) => row.documentVersionId ?? '-',
      },
      {
        dataIndex: 'pageNumber',
        title: '页码',
        render: (_, row) => row.pageNumber ?? '-',
        width: 80,
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
      {
        key: 'provider',
        title: '解析 Provider',
        render: (_, row) => String(row.providerMetadata?.model ?? row.providerMetadata?.provider_type ?? '-'),
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
        dataIndex: 'modality',
        title: '模态',
        render: (_, row) => modalityLabels[row.modality ?? 'text'] ?? row.modality ?? '文本',
        width: 90,
      },
      {
        dataIndex: 'documentVersionId',
        title: '文档版本',
        render: (_, row) => row.documentVersionId ?? '-',
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
        width: 170,
      },
      {
        dataIndex: 'title',
        render: (_, row) => (
          <Button onClick={() => openDocumentDetail(row)} type="link">
            {row.title}
          </Button>
        ),
        sorter: true,
        title: '知识标题',
        width: 220,
      },
      {
        dataIndex: 'knowledgeSpaceId',
        title: '知识空间',
        render: (_, row) => (row.knowledgeSpaceId ? spaceNameById.get(row.knowledgeSpaceId) ?? row.knowledgeSpaceId : '-'),
        width: 220,
      },
      {
        dataIndex: 'folderPath',
        title: '目录',
        render: (_, row) => row.folderPath ?? '-',
        width: 180,
      },
      {
        dataIndex: 'documentType',
        sorter: true,
        title: '类型',
        width: 120,
      },
      {
        dataIndex: 'ownerRole',
        sorter: true,
        title: '权限角色',
        width: 140,
      },
      {
        dataIndex: 'status',
        sorter: true,
        title: '状态',
        render: (_, row) => {
          const statusLabel = statusLabels[row.status];
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
        width: 120,
      },
      {
        dataIndex: 'indexError',
        title: '索引错误',
        render: (_, row) => row.indexError || row.vectorIndexError || '-',
        width: 240,
      },
      {
        dataIndex: 'updatedAt',
        sorter: true,
        title: '更新时间',
        width: 170,
      },
      {
        fixed: 'right',
        key: 'actions',
        title: '操作',
        valueType: 'option',
        width: KNOWLEDGE_ACTION_COLUMN_WIDTH,
        render: (_, row) => (
          <Space className="knowledge-document-actions" size={4} wrap={false}>
            <Button aria-label="资产" icon={<FileSearchOutlined />} onClick={() => void openAssetsModal(row)} type="link">
              资产
            </Button>
            <Button aria-label="分块" icon={<NodeIndexOutlined />} onClick={() => void openChunksModal(row)} type="link">
              分块
            </Button>
            <Button aria-label="编辑" icon={<EditOutlined />} onClick={() => openEditModal(row)} type="link">
              编辑
            </Button>
            <Button aria-label="删除" danger icon={<DeleteOutlined />} onClick={() => confirmDeleteDocument(row)} type="link">
              删除
            </Button>
            <Dropdown
              menu={{
                items: [
                  {
                    icon: <ReloadOutlined />,
                    key: 'reparse',
                    label: '重解析',
                  },
                  row.status === 'index_failed' || row.status === 'text_indexed'
                    ? {
                        icon: <ReloadOutlined />,
                        key: 'retry-index',
                        label: row.status === 'text_indexed' ? '补向量索引' : '重试索引',
                      }
                    : null,
                ].filter(Boolean),
                onClick: ({ key }) => {
                  if (key === 'reparse') {
                    void handleReparseDocument(row);
                  }
                  if (key === 'retry-index') {
                    void handleRetryIndex(row);
                  }
                },
              }}
            >
              <Button aria-label={`更多操作 ${row.id}`} icon={<MoreOutlined />} type="link">
                更多
              </Button>
            </Dropdown>
          </Space>
        ),
      },
    ],
    [
      confirmDeleteDocument,
      handleReparseDocument,
      handleRetryIndex,
      openDocumentDetail,
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
        ellipsis: true,
        title: '沉淀编号',
        width: 160,
      },
      {
        dataIndex: 'title',
        ellipsis: true,
        title: '沉淀标题',
        width: 220,
      },
      {
        dataIndex: 'aiTaskId',
        ellipsis: true,
        title: '任务编号',
        width: 180,
      },
      {
        dataIndex: 'content',
        ellipsis: true,
        title: '内容摘要',
        width: 260,
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) => {
          const label = depositStatusLabels[row.status] ?? { color: 'default', label: row.status };
          return <StatusTag color={label.color} label={label.label} />;
        },
        width: 110,
      },
      {
        fixed: 'right',
        key: 'actions',
        title: '操作',
        valueType: 'option',
        width: 190,
        render: (_, row) => (
          <Space size={4} wrap={false}>
            <Button onClick={() => void openFullChainModal(row)} type="link">
              全链路
            </Button>
            {row.status === 'pending' ? (
              <>
                <Button onClick={() => handleApproveDeposit(row)} type="link">
                  批准入库
                </Button>
                <Button danger onClick={() => openRejectDepositModal(row)} type="link">
                  拒绝
                </Button>
              </>
            ) : null}
          </Space>
        ),
      },
    ],
    [handleApproveDeposit, openFullChainModal, openRejectDepositModal],
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
        render: (_, row) => {
          if (row.retrievalMode === 'hybrid') {
            return 'Hybrid';
          }
          return row.retrievalMode === 'vector' ? '向量' : '关键词';
        },
        width: 100,
      },
      {
        dataIndex: 'score',
        title: '分数',
        render: (_, row) => (row.score == null ? '-' : row.score.toFixed(4)),
        width: 90,
      },
      {
        dataIndex: 'content',
        title: '内容摘要',
      },
    ],
    [],
  );

  const knowledgeHealthPanel = (
    <KnowledgeIndexHealthPanel
      healthState={knowledgeHealthState}
      listRows={listState.rows}
      listTotal={listState.total}
      onOpenChunks={openChunksModal}
      onOpenImportJobs={openImportJobsModal}
      onRetryIndex={handleRetryIndex}
    />
  );

  const knowledgeProcessingGovernancePanel = (
    <KnowledgeProcessingGovernancePanel
      loading={processingGovernanceLoading}
      onCreateProfile={handleCreateProcessingProfile}
      onRefresh={() => void reloadProcessingGovernance()}
      onScanStaleness={handleScanStaleness}
      onToggleProfile={handleToggleProcessingProfile}
      profiles={processingProfiles}
      scanning={stalenessScanning}
      stalenessItems={stalenessItems}
      stalenessSummary={stalenessSummary}
    />
  );

  const knowledgeBeforeTable = (
    <KnowledgeWorkbenchPanels
      activeWorkbenchTab={activeWorkbenchTab}
      depositColumns={depositColumns}
      depositRows={depositRows}
      depositsLoading={depositsLoading}
      folders={folders}
      hasSearched={hasSearched}
      hiddenNoisySpaceCount={hiddenNoisySpaceCount}
      importJobColumns={importJobColumns}
      importJobRows={importJobRows}
      importJobsLoading={importJobsLoading}
      importWorkerStatus={importWorkerStatus}
      importWorkerStatusLoading={importWorkerStatusLoading}
      knowledgeHealthPanel={knowledgeHealthPanel}
      knowledgeHealthState={knowledgeHealthState}
      processingGovernancePanel={knowledgeProcessingGovernancePanel}
      processingProfiles={processingProfiles}
      listRows={listState.rows}
      listTotal={listState.total}
      onCreateFolder={() => setIsFolderModalOpen(true)}
      onOpenSearch={openSearchModal}
      onReloadDeposits={() => void reloadDeposits()}
      onReloadImportJobs={(spaceId) => void reloadImportJobs(spaceId)}
      onReloadImportWorkerStatus={() => void reloadImportWorkerStatus()}
      onRecordCitationClick={handleRecordCitationClick}
      onSearch={handleSearch}
      onSelectFolder={selectWorkbenchFolder}
      onSelectSpace={selectWorkbenchSpace}
      onSetActiveWorkbenchTab={setActiveWorkbenchTab}
      onSetSelectedSpaceId={setSelectedSpaceId}
      onSubmitRagFeedback={handleRagFeedback}
      onToggleNoisySpaces={() => setShowNoisySpaces((current) => !current)}
      onUpdateSpaceSearchText={setSpaceSearchText}
      onWorkbenchTabChange={handleWorkbenchTabChange}
      ragAnswer={ragAnswer}
      ragFeedbackSubmittingValue={ragFeedbackSubmittingValue}
      ragFeedbackValue={ragFeedbackValue}
      searchColumns={searchColumns}
      searchLoading={searchLoading}
      searchRows={searchRows}
      selectedFolderId={selectedFolderId}
      selectedSpace={selectedSpace}
      selectedSpaceId={selectedSpaceId}
      showNoisySpaces={showNoisySpaces}
      spaceOptions={spaceOptions}
      spaceSearchText={spaceSearchText}
      spaces={spaces}
      visibleSpaces={visibleSpaces}
    />
  );

  return (
    <>
      <ManagementListPage<KnowledgeRecord>
        beforeTable={knowledgeBeforeTable}
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
          onChange: handleListQueryChange,
          page: listState.page,
          pageSize: listState.pageSize,
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="id"
        rowSelection={{
          onChange: (keys) => setSelectedRowKeys(keys),
          selectedRowKeys,
        }}
        tableLayout="fixed"
        tableScroll={{ x: KNOWLEDGE_TABLE_SCROLL_X }}
        tableTitle="知识列表"
        title="知识中心"
        toolbarActions={[
          <Button icon={<PlusOutlined />} key="create-space" onClick={() => setIsSpaceModalOpen(true)}>
            新建空间
          </Button>,
          <Button key="advanced-filter" onClick={() => setIsAdvancedFilterOpen(true)}>
            高级筛选
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
        ]}
      />
      <KnowledgePageDialogs
        advancedFilterSubmitRef={advancedFilterSubmitRef}
        advancedFilterValues={advancedFilterValues}
        assetColumns={assetColumns}
        assetRows={assetRows}
        assetsDocument={assetsDocument}
        assetsLoading={assetsLoading}
        batchMoveSubmitRef={batchMoveSubmitRef}
        chunkColumns={chunkColumns}
        chunkRows={chunkRows}
        chunkSetColumns={chunkSetColumns}
        chunkSetRows={chunkSetRows}
        chunkSetsLoading={chunkSetsLoading}
        chunksDocument={chunksDocument}
        chunksLoading={chunksLoading}
        clearAdvancedFilters={clearAdvancedFilters}
        closeFullChainModal={closeFullChainModal}
        detailDocument={detailDocument}
        detailFeedbackRows={detailFeedbackRows}
        detailGovernanceLoading={detailGovernanceLoading}
        detailVersionRows={detailVersionRows}
        documentFormRef={documentFormRef}
        documentInitialValues={documentInitialValues}
        documentSubmitRef={documentSubmitRef}
        editingDocument={editingDocument}
        folderEditSubmitRef={folderEditSubmitRef}
        folderOptions={folderOptions}
        folderSubmitRef={folderSubmitRef}
        fullChain={fullChain}
        fullChainDeposit={fullChainDeposit}
        fullChainError={fullChainError}
        fullChainVersionRequirements={fullChainVersionRequirements}
        handleAdvancedFilterSubmit={handleAdvancedFilterSubmit}
        handleBatchMove={handleBatchMove}
        handleCreateFolder={handleCreateFolder}
        handleCreateSpace={handleCreateSpace}
        handleEditFolder={handleEditFolder}
        handleFileInputChange={handleFileInputChange}
        handleRejectDeposit={handleRejectDeposit}
        handleReparseDocument={handleReparseDocument}
        handleSave={handleSave}
        isAdvancedFilterOpen={isAdvancedFilterOpen}
        isAssetsModalOpen={isAssetsModalOpen}
        isBatchMoveModalOpen={isBatchMoveModalOpen}
        isChunksModalOpen={isChunksModalOpen}
        isFolderEditModalOpen={isFolderEditModalOpen}
        isFolderModalOpen={isFolderModalOpen}
        isFullChainLoading={isFullChainLoading}
        isModalOpen={isModalOpen}
        isSaving={isSaving}
        isSpaceModalOpen={isSpaceModalOpen}
        onCloseAssetsModal={() => setIsAssetsModalOpen(false)}
        onCloseBatchMoveModal={() => setIsBatchMoveModalOpen(false)}
        onCloseChunksModal={() => setIsChunksModalOpen(false)}
        onCloseDetailDrawer={() => setDetailDocument(null)}
        onCloseDocumentModal={() => setIsModalOpen(false)}
        onCloseFolderEditModal={() => setIsFolderEditModalOpen(false)}
        onCloseFolderModal={() => setIsFolderModalOpen(false)}
        onCloseSpaceModal={() => setIsSpaceModalOpen(false)}
        onEditDocument={openEditModal}
        onOpenAssetsModal={openAssetsModal}
        onOpenChunksModal={openChunksModal}
        onLoadProcessingProfiles={reloadProcessingProfiles}
        onLoadDocumentGovernance={loadDocumentGovernance}
        processingProfileOptions={processingProfileOptions}
        rejectDepositSubmitRef={rejectDepositSubmitRef}
        rejectingDeposit={rejectingDeposit}
        roleOptions={roleOptions}
        selectedRowKeys={selectedRowKeys}
        selectedSpaceId={selectedSpaceId}
        selectedUploadFile={selectedUploadFile}
        setIsAdvancedFilterOpen={setIsAdvancedFilterOpen}
        setIsFolderModalOpen={setIsFolderModalOpen}
        setRejectingDeposit={setRejectingDeposit}
        setSelectedSpaceId={setSelectedSpaceId}
        spaceNameById={spaceNameById}
        spaceOptions={spaceOptions}
        spaceSubmitRef={spaceSubmitRef}
        statusLabels={statusLabels}
      />
    </>
  );
}
