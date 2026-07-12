import {
  ApartmentOutlined,
  CalendarOutlined,
  DeleteOutlined,
  EditOutlined,
  LinkOutlined,
  MoreOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Alert, Button, Dropdown, Form, Input, Modal, Select, Space, Spin, message } from 'antd';
import { type Key, useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementBatchResultModal, type ManagementBatchResult } from '../../components/ManagementBatchResultModal';
import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import { RequirementFullChainView } from '../../components/RequirementFullChainView';
import type { RequirementRecord } from '../../data/management';
import { formatRemoteRowsError, normalizeRemoteRowsError, useRemoteRows, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  AUTH_STATE_EVENT,
  approveManagementRequirement,
  batchAdvanceRequirementStatus,
  batchAssignRequirementOwner,
  batchGenerateRequirementTasks,
  batchScheduleRequirements,
  createManagementRequirement,
  deleteManagementRequirement,
  fetchManagementRequirementList,
  fetchRequirementFullChain,
  fetchRequirementProductContextOptions,
  generateRequirementTask,
  getStoredCurrentUser,
  rejectManagementRequirement,
  type CurrentUserResponse,
  type RemoteListPerformance,
  type RequirementFullChainRecord,
  updateManagementRequirement,
} from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';
import {
  batchAdvanceTargetOptions,
  batchAssignableStatuses,
  buildRequirementListQuery,
  formatRequirementDeleteError,
  hasAnyRequirementRole,
  requirementRejectRoles,
  requirementSourceLabels,
  requirementSourceOptions,
  requirementWriteRoles,
  statusLabels,
  type BatchAdvanceStatusFormValues,
  type BatchAssignOwnerFormValues,
  type BatchGenerateTaskFormValues,
  type BatchScheduleFormValues,
  type RequirementFormValues,
} from './requirementPageHelpers';

export default function RequirementsPage() {
  const [form] = Form.useForm<RequirementFormValues>();
  const [batchForm] = Form.useForm<BatchScheduleFormValues>();
  const [batchAdvanceStatusForm] = Form.useForm<BatchAdvanceStatusFormValues>();
  const [batchAssignOwnerForm] = Form.useForm<BatchAssignOwnerFormValues>();
  const [batchGenerateForm] = Form.useForm<BatchGenerateTaskFormValues>();
  const [rejectForm] = Form.useForm<{ rejection_reason: string }>();
  const [editingRequirement, setEditingRequirement] = useState<RequirementRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isBatchAdvanceStatusModalOpen, setIsBatchAdvanceStatusModalOpen] = useState(false);
  const [isBatchAssignOwnerModalOpen, setIsBatchAssignOwnerModalOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [isBatchGenerateModalOpen, setIsBatchGenerateModalOpen] = useState(false);
  const [rejectingRequirement, setRejectingRequirement] = useState<RequirementRecord | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [fullChainRequirement, setFullChainRequirement] = useState<RequirementRecord | null>(null);
  const [fullChain, setFullChain] = useState<RequirementFullChainRecord | null>(null);
  const [fullChainError, setFullChainError] = useState<RemoteRowsError>();
  const [fullChainVersionRequirements, setFullChainVersionRequirements] = useState<RequirementRecord[]>([]);
  const [isFullChainLoading, setIsFullChainLoading] = useState(false);
  const [batchResult, setBatchResult] = useState<ManagementBatchResult | null>(null);
  const [isBatchAdvanceStatusSaving, setIsBatchAdvanceStatusSaving] = useState(false);
  const [isBatchAssignOwnerSaving, setIsBatchAssignOwnerSaving] = useState(false);
  const [isBatchGenerateSaving, setIsBatchGenerateSaving] = useState(false);
  const [isBatchSaving, setIsBatchSaving] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'createdAt',
    sortOrder: 'descend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    performance?: RemoteListPerformance;
    rows: RequirementRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const {
    error: productContextError,
    reload: reloadProductContexts,
    rows: productContexts,
    status: productContextStatus,
  } = useRemoteRows(fetchRequirementProductContextOptions);
  const [currentUser, setCurrentUser] = useState<CurrentUserResponse | undefined>(() => getStoredCurrentUser());
  const selectedProductId = Form.useWatch('product_id', form);
  const selectedBatchProductId = Form.useWatch('product_id', batchForm);
  const canWriteRequirements = useMemo(
    () => hasAnyRequirementRole(currentUser, requirementWriteRoles),
    [currentUser],
  );
  const canRejectRequirements = useMemo(
    () => hasAnyRequirementRole(currentUser, requirementRejectRoles),
    [currentUser],
  );
  const selectedProduct = useMemo(
    () => productContexts.find((product) => product.id === selectedProductId),
    [productContexts, selectedProductId],
  );
  const selectedBatchProduct = useMemo(
    () => productContexts.find((product) => product.id === selectedBatchProductId),
    [productContexts, selectedBatchProductId],
  );
  const selectedRequirementIds = useMemo(
    () => selectedRowKeys.map((key) => String(key)),
    [selectedRowKeys],
  );
  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchManagementRequirementList(buildRequirementListQuery(listQuery));
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        performance: result.performance,
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
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchManagementRequirementList(buildRequirementListQuery(listQuery))
      .then((result) => {
        if (isCurrent) {
          setListState({
            page: result.page,
            pageSize: result.pageSize,
            performance: result.performance,
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

  const selectedRequirements = useMemo(() => {
    const selectedIds = new Set(selectedRequirementIds);
    return listState.rows.filter((row) => selectedIds.has(row.id));
  }, [listState.rows, selectedRequirementIds]);
  const selectedBatchGeneratableRequirements = useMemo(
    () => selectedRequirements.filter((row) => row.status === 'planned'),
    [selectedRequirements],
  );
  const productOptions = useMemo(
    () =>
      productContexts.map((product) => ({
        label: `${product.code} · ${product.name}`,
        value: product.id,
      })),
    [productContexts],
  );
  const versionOptions = useMemo(() => {
    if (!selectedProduct) {
      return [];
    }
    return selectedProduct.versions.map((version) => ({
      label: `${version.code} · ${version.name}`,
      value: version.id,
    }));
  }, [selectedProduct]);
  const batchVersionOptions = useMemo(() => {
    if (!selectedBatchProduct) {
      return [];
    }
    return selectedBatchProduct.versions.map((version) => ({
      label: `${version.code} · ${version.name}`,
      value: version.id,
    }));
  }, [selectedBatchProduct]);

  useEffect(() => {
    const syncCurrentUser = () => setCurrentUser(getStoredCurrentUser());
    syncCurrentUser();
    globalThis.addEventListener?.(AUTH_STATE_EVENT, syncCurrentUser);
    return () => {
      globalThis.removeEventListener?.(AUTH_STATE_EVENT, syncCurrentUser);
    };
  }, []);

  const ensureCanWriteRequirements = useCallback((actionLabel: string) => {
    if (canWriteRequirements) {
      return true;
    }
    message.warning(`当前账号没有需求写权限，不能${actionLabel}`);
    return false;
  }, [canWriteRequirements]);

  const ensureCanRejectRequirements = useCallback((actionLabel: string) => {
    if (canRejectRequirements) {
      return true;
    }
    message.warning(`当前账号没有需求驳回权限，不能${actionLabel}`);
    return false;
  }, [canRejectRequirements]);

  const openCreateModal = useCallback(() => {
    if (!ensureCanWriteRequirements('新增需求')) {
      return;
    }
    setEditingRequirement(null);
    form.resetFields();
    const firstProduct = productContexts[0];
    form.setFieldsValue({
      priority: 'P1',
      product_id: firstProduct?.id,
      source: 'business_department',
      version_id: undefined,
    });
    setIsModalOpen(true);
  }, [ensureCanWriteRequirements, form, productContexts]);

  const handleProductChange = useCallback(() => {
    form.setFieldsValue({
      module_code: undefined,
      version_id: undefined,
    });
  }, [form]);

  const showBatchResult = useCallback((result: ManagementBatchResult) => {
    setBatchResult(result);
    const skippedText = result.skipped.length ? `，跳过 ${result.skipped.length} 条` : '';
    message.success(`${result.primaryLabel} ${result.primaryCount} 条需求${skippedText}`);
  }, []);

  const openEditModal = useCallback((row: RequirementRecord) => {
    if (!ensureCanWriteRequirements('编辑需求')) {
      return;
    }
    setEditingRequirement(row);
    form.setFieldsValue({
      content: row.content ?? '',
      module_code: row.moduleCode,
      priority: row.priority,
      product_id: row.productId ?? row.product,
      source: row.source ?? 'business_department',
      title: row.title,
      version_id: row.versionId,
    });
    setIsModalOpen(true);
  }, [ensureCanWriteRequirements, form]);

  const handleSave = async () => {
    if (!ensureCanWriteRequirements(editingRequirement ? '编辑需求' : '新增需求')) {
      return;
    }
    const values = await form.validateFields();
    const payload = {
      content: values.content.trim(),
      module_code: trimText(values.module_code),
      priority: values.priority,
      product_id: values.product_id.trim(),
      source: values.source,
      title: values.title.trim(),
      ...(trimText(values.version_id) ? { version_id: trimText(values.version_id) } : {}),
    };

    setIsSaving(true);
    try {
      if (editingRequirement) {
        await updateManagementRequirement(editingRequirement.id, payload);
        message.success('需求已更新');
      } else {
        await createManagementRequirement(payload);
        message.success('需求已创建');
      }
      setIsModalOpen(false);
      void reloadProductContexts();
      void reload();
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = useCallback(async (row: RequirementRecord) => {
    if (!ensureCanWriteRequirements('删除需求')) {
      return;
    }
    try {
      await deleteManagementRequirement(row.id);
      message.success('需求已删除');
      await reload();
    } catch (deleteError) {
      message.error(formatRequirementDeleteError(deleteError));
    }
  }, [ensureCanWriteRequirements, reload]);

  const openBatchScheduleModal = useCallback(() => {
    if (!ensureCanWriteRequirements('批量排期')) {
      return;
    }
    if (selectedRequirements.length === 0) {
      message.warning('请先选择要排期的需求');
      return;
    }
    const productIds = Array.from(
      new Set(
        selectedRequirements
          .map((row) => row.productId)
          .filter((productId): productId is string => Boolean(productId)),
      ),
    );
    if (productIds.length !== 1) {
      message.warning('请选择同一产品下的需求进行批量排期');
      return;
    }
    const productId = productIds[0];
    const productContext = productContexts.find((product) => product.id === productId);
    batchForm.resetFields();
    batchForm.setFieldsValue({
      product_id: productId,
      reason: undefined,
      version_id:
        productContext?.versions.length === 1 ? productContext.versions[0].id : undefined,
    });
    setIsBatchModalOpen(true);
  }, [batchForm, ensureCanWriteRequirements, productContexts, selectedRequirements]);

  const handleBatchSchedule = async () => {
    if (!ensureCanWriteRequirements('批量排期')) {
      return;
    }
    let values: BatchScheduleFormValues;
    try {
      values = await batchForm.validateFields();
    } catch {
      return;
    }
    setIsBatchSaving(true);
    try {
      const result = await batchScheduleRequirements({
        product_id: values.product_id,
        reason: trimText(values.reason),
        requirement_ids: selectedRequirementIds,
        version_id: values.version_id,
      });
      showBatchResult({
        batchId: result.batchId,
        primaryCount: result.updatedCount,
        primaryLabel: '已归集',
        skipped: result.skipped,
        title: '批量排期结果',
      });
      setIsBatchModalOpen(false);
      setSelectedRowKeys([]);
      await reload();
      void reloadProductContexts();
    } catch (batchError) {
      message.error(formatMutationError(batchError));
    } finally {
      setIsBatchSaving(false);
    }
  };

  const openBatchAssignOwnerModal = useCallback(() => {
    if (!ensureCanWriteRequirements('批量分配负责人')) {
      return;
    }
    if (selectedRequirements.length === 0) {
      message.warning('请先选择要分配负责人的需求');
      return;
    }
    batchAssignOwnerForm.resetFields();
    setIsBatchAssignOwnerModalOpen(true);
  }, [batchAssignOwnerForm, ensureCanWriteRequirements, selectedRequirements.length]);

  const handleBatchAssignOwner = async () => {
    if (!ensureCanWriteRequirements('批量分配负责人')) {
      return;
    }
    let values: BatchAssignOwnerFormValues;
    try {
      values = await batchAssignOwnerForm.validateFields();
    } catch {
      return;
    }
    setIsBatchAssignOwnerSaving(true);
    try {
      const result = await batchAssignRequirementOwner({
        assignee: values.assignee.trim(),
        reason: trimText(values.reason),
        requirement_ids: selectedRequirementIds,
      });
      showBatchResult({
        batchId: result.batchId,
        primaryCount: result.updatedCount,
        primaryLabel: '已分配',
        skipped: result.skipped,
        title: '批量分配负责人结果',
      });
      setIsBatchAssignOwnerModalOpen(false);
      setSelectedRowKeys([]);
      await reload();
    } catch (batchError) {
      message.error(formatMutationError(batchError));
    } finally {
      setIsBatchAssignOwnerSaving(false);
    }
  };

  const openBatchAdvanceStatusModal = useCallback(() => {
    if (!ensureCanWriteRequirements('批量推进状态')) {
      return;
    }
    if (selectedRequirements.length === 0) {
      message.warning('请先选择要推进状态的需求');
      return;
    }
    batchAdvanceStatusForm.resetFields();
    batchAdvanceStatusForm.setFieldsValue({ target_status: 'ready_for_dev' });
    setIsBatchAdvanceStatusModalOpen(true);
  }, [batchAdvanceStatusForm, ensureCanWriteRequirements, selectedRequirements.length]);

  const handleBatchAdvanceStatus = async () => {
    if (!ensureCanWriteRequirements('批量推进状态')) {
      return;
    }
    let values: BatchAdvanceStatusFormValues;
    try {
      values = await batchAdvanceStatusForm.validateFields();
    } catch {
      return;
    }
    setIsBatchAdvanceStatusSaving(true);
    try {
      const result = await batchAdvanceRequirementStatus({
        reason: trimText(values.reason),
        requirement_ids: selectedRequirementIds,
        target_status: values.target_status,
      });
      const targetLabel = statusLabels[result.targetStatus]?.label ?? result.targetStatus;
      showBatchResult({
        batchId: result.batchId,
        primaryCount: result.updatedCount,
        primaryLabel: `已推进到${targetLabel}`,
        skipped: result.skipped,
        title: '批量推进状态结果',
      });
      setIsBatchAdvanceStatusModalOpen(false);
      setSelectedRowKeys([]);
      await reload();
    } catch (batchError) {
      message.error(formatMutationError(batchError));
    } finally {
      setIsBatchAdvanceStatusSaving(false);
    }
  };

  const openBatchGenerateTaskModal = useCallback(() => {
    if (!ensureCanWriteRequirements('批量生成任务')) {
      return;
    }
    if (selectedRequirements.length === 0) {
      message.warning('请先选择要生成任务的需求');
      return;
    }
    const productIds = Array.from(
      new Set(
        selectedRequirements
          .map((row) => row.productId)
          .filter((productId): productId is string => Boolean(productId)),
      ),
    );
    if (productIds.length !== 1) {
      message.warning('请选择同一产品下的需求批量生成任务');
      return;
    }
    if (selectedBatchGeneratableRequirements.length === 0) {
      message.warning('请选择已排期需求生成任务');
      return;
    }
    batchGenerateForm.resetFields();
    setIsBatchGenerateModalOpen(true);
  }, [batchGenerateForm, ensureCanWriteRequirements, selectedBatchGeneratableRequirements.length, selectedRequirements]);

  const handleBatchGenerateTasks = async () => {
    if (!ensureCanWriteRequirements('批量生成任务')) {
      return;
    }
    let values: BatchGenerateTaskFormValues;
    try {
      values = await batchGenerateForm.validateFields();
    } catch {
      return;
    }
    const productId = selectedRequirements.find((row) => row.productId)?.productId;
    if (!productId) {
      message.warning('未找到所选需求的产品');
      return;
    }
    setIsBatchGenerateSaving(true);
    try {
      const result = await batchGenerateRequirementTasks({
        product_id: productId,
        reason: trimText(values.reason),
        requirement_ids: selectedRequirementIds,
      });
      showBatchResult({
        batchId: result.batchId,
        primaryCount: result.generatedCount,
        primaryLabel: '已生成任务',
        skipped: result.skipped,
        title: '批量生成任务结果',
      });
      setIsBatchGenerateModalOpen(false);
      setSelectedRowKeys([]);
      await reload();
    } catch (batchError) {
      message.error(formatMutationError(batchError));
    } finally {
      setIsBatchGenerateSaving(false);
    }
  };

  const handleApprove = useCallback(async (row: RequirementRecord) => {
    if (!ensureCanWriteRequirements('审批需求')) {
      return;
    }
    try {
      await approveManagementRequirement(row.id);
      message.success('需求已审批通过');
      await reload();
    } catch (decisionError) {
      message.error(formatMutationError(decisionError));
    }
  }, [ensureCanWriteRequirements, reload]);

  const openRejectModal = useCallback((row: RequirementRecord) => {
    if (!ensureCanRejectRequirements('驳回需求')) {
      return;
    }
    setRejectingRequirement(row);
    rejectForm.resetFields();
  }, [ensureCanRejectRequirements, rejectForm]);

  const handleReject = async () => {
    if (!rejectingRequirement) {
      return;
    }
    if (!ensureCanRejectRequirements('驳回需求')) {
      return;
    }
    const values = await rejectForm.validateFields();
    try {
      await rejectManagementRequirement(
        rejectingRequirement.id,
        values.rejection_reason.trim(),
      );
      message.success('需求已驳回');
      setRejectingRequirement(null);
      await reload();
    } catch (decisionError) {
      message.error(formatMutationError(decisionError));
    }
  };

  const handleGenerateTask = useCallback(async (row: RequirementRecord) => {
    if (!ensureCanWriteRequirements('生成任务')) {
      return;
    }
    try {
      const result = await generateRequirementTask(row.id);
      message.success(`已生成 ${result.task_type} 任务：${result.task_id}`);
      await reload();
    } catch (decisionError) {
      message.error(formatMutationError(decisionError));
    }
  }, [ensureCanWriteRequirements, reload]);

  const openFullChainModal = useCallback(async (row: RequirementRecord) => {
    setFullChainRequirement(row);
    setFullChain(null);
    setFullChainError(undefined);
    setFullChainVersionRequirements([]);
    setIsFullChainLoading(true);
    try {
      const loadedChain = await fetchRequirementFullChain(row.id);
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

  const openDeleteConfirm = useCallback((row: RequirementRecord) => {
    if (!ensureCanWriteRequirements('删除需求')) {
      return;
    }
    Modal.confirm({
      content: '仅未生成 AI 任务的需求可以删除。已生成任务的需求请先通过全链路或任务中心处理关联任务；如需求不再推进，可关闭或取消需求。',
      okText: '删除',
      okButtonProps: { danger: true },
      title: `删除需求 ${row.id}？`,
      onOk: () => handleDelete(row),
    });
  }, [ensureCanWriteRequirements, handleDelete]);

  const toolbarActions = useMemo(
    () => canWriteRequirements ? [
      <Button
        disabled={selectedRowKeys.length === 0}
        key="batch-assign-owner"
        onClick={openBatchAssignOwnerModal}
      >
        批量分配负责人
      </Button>,
      <Button
        disabled={selectedRowKeys.length === 0}
        key="batch-advance-status"
        onClick={openBatchAdvanceStatusModal}
      >
        批量推进状态
      </Button>,
      <Button
        disabled={selectedRowKeys.length === 0}
        icon={<CalendarOutlined />}
        key="batch-schedule"
        onClick={openBatchScheduleModal}
      >
        批量排期
      </Button>,
      <Button
        disabled={selectedRowKeys.length === 0}
        icon={<RocketOutlined />}
        key="batch-generate-tasks"
        onClick={openBatchGenerateTaskModal}
      >
        批量生成任务
      </Button>,
    ] : [],
    [
      canWriteRequirements,
      openBatchAdvanceStatusModal,
      openBatchAssignOwnerModal,
      openBatchGenerateTaskModal,
      openBatchScheduleModal,
      selectedRowKeys.length,
    ],
  );

  const columns = useMemo<ProColumns<RequirementRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        ellipsis: true,
        sorter: true,
        title: '需求编号',
        width: 162,
      },
      {
        dataIndex: 'title',
        ellipsis: true,
        sorter: true,
        title: '需求标题',
        width: 260,
      },
      {
        dataIndex: 'product',
        ellipsis: true,
        sorter: true,
        title: '所属产品',
        width: 168,
      },
      {
        dataIndex: 'versionName',
        ellipsis: true,
        sorter: true,
        title: '迭代版本',
        width: 240,
      },
      {
        dataIndex: 'priority',
        sorter: true,
        title: '优先级',
        render: (_, row) => (
          <StatusTag color={row.priority === 'P0' ? 'red' : 'blue'} label={row.priority} />
        ),
        width: 88,
      },
      {
        dataIndex: 'source',
        sorter: true,
        title: '需求来源',
        render: (_, row) => requirementSourceLabels[row.source ?? 'business_department'] ?? row.source ?? '-',
        width: 120,
      },
      {
        dataIndex: 'status',
        sorter: true,
        title: '状态',
        render: (_, row) => {
          const statusLabel = statusLabels[row.status];
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
        width: 112,
      },
      {
        dataIndex: 'owner',
        ellipsis: true,
        title: '负责人',
        width: 136,
      },
      {
        dataIndex: 'createdAt',
        ellipsis: true,
        sorter: true,
        title: '创建时间',
        width: 168,
      },
      {
        fixed: 'right',
        key: 'actions',
        title: '操作',
        valueType: 'option',
        width: 164,
        render: (_, row) => (
          <Space className="requirement-list-actions" size={4}>
            <Button
              className="requirement-list-primary-action"
              icon={<ApartmentOutlined aria-hidden="true" />}
              onClick={() => void openFullChainModal(row)}
              type="link"
            >
              全链路
            </Button>
            <Dropdown
              menu={{
                items: [
                  {
                    icon: <LinkOutlined />,
                    key: 'detail-page',
                    label: <a href={`/delivery/requirements/${row.id}/full-chain`}>详情页</a>,
                  },
                  ...(canWriteRequirements
                    ? [
                        {
                          icon: <EditOutlined />,
                          key: 'edit',
                          label: '编辑',
                        },
                      ]
                    : []),
                  ...(canWriteRequirements && row.status === 'submitted'
                    ? [
                        {
                          key: 'approve',
                          label: '审批通过',
                        },
                      ]
                    : []),
                  ...(canRejectRequirements && row.status === 'submitted'
                    ? [
                        {
                          danger: true,
                          key: 'reject',
                          label: '驳回',
                        },
                      ]
                    : []),
                  ...(canWriteRequirements && row.status === 'planned'
                    ? [
                        {
                          key: 'generate-task',
                          label: '生成任务',
                        },
                      ]
                    : []),
                  ...(canWriteRequirements
                    ? [
                        {
                          danger: true,
                          icon: <DeleteOutlined />,
                          key: 'delete',
                          label: '删除',
                        },
                      ]
                    : []),
                ],
                onClick: ({ key }) => {
                  if (key === 'detail-page') {
                    return;
                  }
                  if (key === 'edit') {
                    openEditModal(row);
                    return;
                  }
                  if (key === 'approve') {
                    void handleApprove(row);
                    return;
                  }
                  if (key === 'reject') {
                    openRejectModal(row);
                    return;
                  }
                  if (key === 'generate-task') {
                    void handleGenerateTask(row);
                    return;
                  }
                  if (key === 'delete') {
                    openDeleteConfirm(row);
                  }
                },
              }}
              trigger={['click']}
            >
              <Button icon={<MoreOutlined />} type="link">
                更多
              </Button>
            </Dropdown>
          </Space>
        ),
      },
    ],
    [
      canRejectRequirements,
      canWriteRequirements,
      handleApprove,
      handleGenerateTask,
      openDeleteConfirm,
      openEditModal,
      openFullChainModal,
      openRejectModal,
    ],
  );

  return (
    <>
      <div className="requirements-management-list">
        <ManagementListPage<RequirementRecord>
          breadcrumbGroup="需求交付"
          columns={columns}
          dataSource={listState.rows}
          viewStorageKey="delivery.requirements"
          filters={[
            { label: '需求标题', name: 'title', type: 'text' },
            {
              label: '所属产品',
              name: 'productId',
              options: productOptions,
              type: 'select',
            },
            { label: '迭代版本', name: 'versionName', type: 'text' },
            {
              label: '需求来源',
              name: 'source',
              options: requirementSourceOptions,
              type: 'select',
            },
            {
              label: '状态',
              name: 'status',
              options: [
                { label: '草稿', value: 'draft' },
                { label: '待评审', value: 'submitted' },
                { label: '需求池', value: 'approved' },
                { label: '已排期', value: 'planned' },
                { label: '设计中', value: 'designing' },
                { label: '待开发', value: 'ready_for_dev' },
                { label: '开发中', value: 'developing' },
                { label: '代码评审中', value: 'code_reviewing' },
                { label: '测试中', value: 'testing' },
                { label: '待发布', value: 'ready_for_release' },
                { label: '部署中', value: 'deploying' },
                { label: '已发布', value: 'released' },
                { label: '已验收', value: 'accepted' },
                { label: '已拒绝', value: 'rejected' },
                { label: '暂缓', value: 'deferred' },
                { label: '已取消', value: 'cancelled' },
                { label: '已关闭', value: 'closed' },
              ],
              type: 'select',
            },
            {
              label: '优先级',
              name: 'priority',
              options: [
                { label: 'P0', value: 'P0' },
                { label: 'P1', value: 'P1' },
                { label: 'P2', value: 'P2' },
              ],
              type: 'select',
            },
          ]}
          loading={listState.status === 'loading'}
          notice={formatRemoteRowsError(listState.error ?? productContextError)}
          onPrimaryAction={canWriteRequirements ? openCreateModal : undefined}
          onReload={() => void reload()}
          primaryAction={canWriteRequirements ? '新增需求' : undefined}
          remote={{
            onChange: setListQuery,
            page: listState.page,
            pageSize: listState.pageSize,
            total: listState.total,
          }}
          rowKey="id"
          rowSelection={canWriteRequirements
            ? {
                getCheckboxProps: (row) => ({
                  disabled: !batchAssignableStatuses.has(row.status),
                }),
                onChange: (keys) => setSelectedRowKeys(keys),
                selectedRowKeys,
              }
            : undefined}
          tableLayout="fixed"
          tableScroll={{ x: 1720 }}
          tableTitle=""
          title="需求管理"
          toolbarActions={toolbarActions}
        />
      </div>
      <Modal
        className="requirement-full-chain-modal"
        destroyOnHidden
        footer={null}
        onCancel={() => {
          setFullChainRequirement(null);
          setFullChain(null);
          setFullChainError(undefined);
          setFullChainVersionRequirements([]);
        }}
        open={Boolean(fullChainRequirement)}
        style={{ maxWidth: 'calc(100vw - 40px)' }}
        styles={{ body: { maxHeight: 'calc(100vh - 180px)', overflowX: 'hidden', overflowY: 'auto' } }}
        title={fullChainRequirement ? `需求全链路 · ${fullChainRequirement.id}` : '需求全链路'}
        width={1040}
      >
        <Spin spinning={isFullChainLoading}>
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            {fullChainError ? (
              <Alert title={formatRemoteRowsError(fullChainError)} type="error" />
            ) : null}
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
        confirmLoading={isBatchSaving}
        destroyOnHidden
        okText="确认归集"
        onCancel={() => setIsBatchModalOpen(false)}
        onOk={() => void handleBatchSchedule()}
        open={isBatchModalOpen}
        title="批量排期需求"
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Alert title={`已选择 ${selectedRequirements.length} 条需求`} type="info" />
          <Form<BatchScheduleFormValues> form={batchForm} layout="vertical">
            <Form.Item label="所属产品" name="product_id" rules={[{ required: true, message: '请选择产品' }]}>
              <Select disabled options={productOptions} />
            </Form.Item>
            <Form.Item label="目标版本" name="version_id" rules={[{ required: true, message: '请选择目标版本' }]}>
              <Select
                loading={productContextStatus === 'loading'}
                optionFilterProp="label"
                options={batchVersionOptions}
                placeholder="请选择要归集到的迭代版本"
                showSearch
              />
            </Form.Item>
            <Form.Item label="归集原因" name="reason">
              <Input.TextArea rows={2} />
            </Form.Item>
          </Form>
        </Space>
      </Modal>
      <Modal
        confirmLoading={isBatchAssignOwnerSaving}
        destroyOnHidden
        okText="确认分配"
        onCancel={() => setIsBatchAssignOwnerModalOpen(false)}
        onOk={() => void handleBatchAssignOwner()}
        open={isBatchAssignOwnerModalOpen}
        title="批量分配负责人"
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Alert title={`已选择 ${selectedRequirements.length} 条需求`} type="info" />
          <Form<BatchAssignOwnerFormValues> form={batchAssignOwnerForm} layout="vertical">
            <Form.Item
              label="负责人"
              name="assignee"
              rules={[{ message: '请输入负责人', required: true, whitespace: true }]}
            >
              <Input placeholder="请输入负责人账号或姓名" />
            </Form.Item>
            <Form.Item label="分配原因" name="reason">
              <Input.TextArea placeholder="可填写批量分配原因" rows={2} />
            </Form.Item>
          </Form>
        </Space>
      </Modal>
      <Modal
        confirmLoading={isBatchAdvanceStatusSaving}
        destroyOnHidden
        okText="确认推进"
        onCancel={() => setIsBatchAdvanceStatusModalOpen(false)}
        onOk={() => void handleBatchAdvanceStatus()}
        open={isBatchAdvanceStatusModalOpen}
        title="批量推进状态"
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            description="仅支持按研发流程向前推进，终态、重复或不符合路径的需求会由后端跳过。"
            title={`已选择 ${selectedRequirements.length} 条需求`}
            type="info"
          />
          <Form<BatchAdvanceStatusFormValues> form={batchAdvanceStatusForm} layout="vertical">
            <Form.Item
              label="目标状态"
              name="target_status"
              rules={[{ message: '请选择目标状态', required: true }]}
            >
              <Select options={batchAdvanceTargetOptions} placeholder="请选择目标状态" />
            </Form.Item>
            <Form.Item label="推进原因" name="reason">
              <Input.TextArea placeholder="可填写批量推进原因" rows={2} />
            </Form.Item>
          </Form>
        </Space>
      </Modal>
      <Modal
        confirmLoading={isBatchGenerateSaving}
        destroyOnHidden
        okText="确认生成"
        onCancel={() => setIsBatchGenerateModalOpen(false)}
        onOk={() => void handleBatchGenerateTasks()}
        open={isBatchGenerateModalOpen}
        title="批量生成任务"
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            title={`将为 ${selectedBatchGeneratableRequirements.length} 条已排期需求生成产品详细设计任务`}
            type="info"
          />
          {selectedRequirements.length > selectedBatchGeneratableRequirements.length ? (
            <Alert
              showIcon
              title={`另有 ${
                selectedRequirements.length - selectedBatchGeneratableRequirements.length
              } 条非已排期需求将由后端跳过`}
              type="warning"
            />
          ) : null}
          <Form<BatchGenerateTaskFormValues> form={batchGenerateForm} layout="vertical">
            <Form.Item label="生成原因" name="reason">
              <Input.TextArea rows={2} />
            </Form.Item>
          </Form>
        </Space>
      </Modal>
      <ManagementBatchResultModal onClose={() => setBatchResult(null)} result={batchResult} />
      <Modal
        confirmLoading={isSaving}
        destroyOnHidden
        onCancel={() => setIsModalOpen(false)}
        onOk={() => void handleSave()}
        open={isModalOpen}
        title={editingRequirement ? '编辑需求' : '新增需求'}
      >
        <Form<RequirementFormValues> form={form} layout="vertical">
          <Form.Item label="需求标题" name="title" rules={[{ required: true, message: '请输入需求标题' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="所属产品" name="product_id" rules={[{ required: true, message: '请选择产品' }]}>
            <Select
              loading={productContextStatus === 'loading'}
              onChange={handleProductChange}
              optionFilterProp="label"
              options={productOptions}
              placeholder="请选择产品"
              showSearch
            />
          </Form.Item>
          <Form.Item
            extra="可暂不选择；审批后进入需求池，后续在迭代版本中排期。"
            label="目标版本"
            name="version_id"
          >
            <Select
              allowClear
              disabled={!selectedProduct}
              loading={productContextStatus === 'loading'}
              options={versionOptions}
              placeholder={selectedProduct ? '请选择版本，可留空' : '请先选择产品'}
            />
          </Form.Item>
          <Form.Item label="模块编码" name="module_code">
            <Input />
          </Form.Item>
          <Form.Item label="需求来源" name="source" rules={[{ required: true, message: '请选择需求来源' }]}>
            <Select options={requirementSourceOptions} />
          </Form.Item>
          <Form.Item label="优先级" name="priority" rules={[{ required: true, message: '请选择优先级' }]}>
            <Select
              options={[
                { label: 'P0', value: 'P0' },
                { label: 'P1', value: 'P1' },
                { label: 'P2', value: 'P2' },
              ]}
            />
          </Form.Item>
          <Form.Item label="需求内容" name="content" rules={[{ required: true, message: '请输入需求内容' }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        onCancel={() => setRejectingRequirement(null)}
        onOk={() => void handleReject()}
        open={Boolean(rejectingRequirement)}
        title="驳回需求"
      >
        <Form<{ rejection_reason: string }> form={rejectForm} layout="vertical">
          <Form.Item
            label="驳回原因"
            name="rejection_reason"
            rules={[{ required: true, message: '请输入驳回原因' }]}
          >
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
