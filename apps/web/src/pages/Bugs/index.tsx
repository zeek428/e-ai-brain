import { CheckSquareOutlined, DeleteOutlined, EditOutlined, EyeOutlined, UploadOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, Tag, message } from 'antd';
import {
  type ChangeEvent,
  type ClipboardEvent as ReactClipboardEvent,
  type Key,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import {
  ManagementBatchResultModal,
  type ManagementBatchResult,
} from '../../components/ManagementBatchResultModal';
import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import type { BugRecord } from '../../data/management';
import { formatRemoteRowsError, normalizeRemoteRowsError, useRemoteRows, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  AUTH_STATE_EVENT,
  batchUpdateManagementBugs,
  createManagementBug,
  deleteManagementBug,
  fetchBugProductContextOptions,
  fullChainSubjectHref,
  fetchManagementBugImagePreview,
  fetchManagementBugs,
  fetchManagementBugList,
  getStoredCurrentUser,
  type BugImageEvidenceItem,
  type BugImageUploadSource,
  type CurrentUserResponse,
  type RemoteListPerformance,
  updateManagementBug,
  uploadManagementBugImage,
} from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';
import {
  buildBugListQuery,
  bugImageMimeTypes,
  canManageBugResources,
  clipboardImageFiles,
  evidenceImages,
  evidenceJsonRule,
  evidenceWithImages,
  evidenceWithoutImages,
  formatEvidenceJson,
  formatReproduceSteps,
  isFormValidationError,
  parseEvidenceJson,
  parseReproduceSteps,
  readFileAsBase64,
  severityLabels,
  sourceLabels,
  statusLabels,
  type BugBatchFormValues,
  type BugFormValues,
} from './bugPageHelpers';

export default function BugsPage() {
  const [form] = Form.useForm<BugFormValues>();
  const [batchForm] = Form.useForm<BugBatchFormValues>();
  const imageInputRef = useRef<HTMLInputElement>(null);
  const [editingBug, setEditingBug] = useState<BugRecord | null>(null);
  const [bugImages, setBugImages] = useState<BugImageEvidenceItem[]>([]);
  const [batchResult, setBatchResult] = useState<ManagementBatchResult | null>(null);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [isBatchSaving, setIsBatchSaving] = useState(false);
  const [imagePreview, setImagePreview] = useState<{ title: string; url: string }>();
  const [previewingImageKey, setPreviewingImageKey] = useState<string>();
  const [isImageUploading, setIsImageUploading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
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
    rows: BugRecord[];
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
    rows: productContexts,
    status: productContextStatus,
  } = useRemoteRows(fetchBugProductContextOptions);
  const {
    error: duplicateBugsError,
    reload: reloadDuplicateBugs,
    rows: duplicateBugs,
  } = useRemoteRows(fetchManagementBugs);
  const [currentUser, setCurrentUser] = useState<CurrentUserResponse | undefined>(() => getStoredCurrentUser());
  const selectedProductId = Form.useWatch('product_id', form);
  const canManageBugs = useMemo(
    () => canManageBugResources(currentUser),
    [currentUser],
  );
  const selectedBugIds = useMemo(
    () => selectedRowKeys.map((key) => String(key)),
    [selectedRowKeys],
  );
  const selectedProduct = useMemo(
    () => productContexts.find((product) => product.id === selectedProductId),
    [productContexts, selectedProductId],
  );
  const previewUrlRef = useRef<string | undefined>(undefined);
  const productOptions = useMemo(
    () =>
      productContexts.map((product) => ({
        label: `${product.code} · ${product.name}`,
        value: product.id,
      })),
    [productContexts],
  );
  const versionOptions = useMemo(
    () =>
      selectedProduct?.versions.map((version) => ({
        label: `${version.code} · ${version.name}`,
        value: version.id,
      })) ?? [],
    [selectedProduct],
  );
  const duplicateBugOptions = useMemo(
    () => {
      const duplicateProductId = editingBug?.productId ?? selectedProductId;
      return duplicateBugs
        .filter(
          (bug) =>
            bug.id !== editingBug?.id &&
            (!duplicateProductId || bug.productId === duplicateProductId),
        )
        .map((bug) => ({
          label: `${bug.id} · ${bug.title}`,
          value: bug.id,
        }));
    },
    [duplicateBugs, editingBug?.id, editingBug?.productId, selectedProductId],
  );
  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchManagementBugList(buildBugListQuery(listQuery));
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

  const replaceBugImagePreview = useCallback((nextPreview?: { title: string; url: string }) => {
    if (previewUrlRef.current && typeof URL.revokeObjectURL === 'function') {
      URL.revokeObjectURL(previewUrlRef.current);
    }
    previewUrlRef.current = nextPreview?.url;
    setImagePreview(nextPreview);
  }, []);

  const closeBugImagePreview = useCallback(() => {
    replaceBugImagePreview(undefined);
  }, [replaceBugImagePreview]);

  useEffect(() => () => {
    if (previewUrlRef.current && typeof URL.revokeObjectURL === 'function') {
      URL.revokeObjectURL(previewUrlRef.current);
    }
  }, []);

  useEffect(() => {
    const syncCurrentUser = () => setCurrentUser(getStoredCurrentUser());
    syncCurrentUser();
    globalThis.addEventListener?.(AUTH_STATE_EVENT, syncCurrentUser);
    return () => {
      globalThis.removeEventListener?.(AUTH_STATE_EVENT, syncCurrentUser);
    };
  }, []);

  useEffect(() => {
    if (canManageBugs) {
      return;
    }
    setSelectedRowKeys([]);
    setIsBatchModalOpen(false);
    setIsModalOpen(false);
    closeBugImagePreview();
  }, [canManageBugs, closeBugImagePreview]);

  const ensureCanManageBugs = useCallback((actionLabel: string) => {
    if (canManageBugs) {
      return true;
    }
    message.warning(`当前账号只有 Bug 只读权限，不能${actionLabel}`);
    return false;
  }, [canManageBugs]);

  const openCreateModal = () => {
    if (!ensureCanManageBugs('登记 Bug')) {
      return;
    }
    setEditingBug(null);
    setBugImages([]);
    closeBugImagePreview();
    form.resetFields();
    const firstProduct =
      productContexts.find((product) => product.code?.toUpperCase() === 'AI-BRAIN') ??
      productContexts[0];
    form.setFieldsValue({
      duplicate_of_bug_id: undefined,
      evidence_json: '',
      product_id: firstProduct?.id,
      reproduce_steps_text: '',
      severity: 'major',
      source: 'manual_test',
      version_id: firstProduct?.versions[0]?.id,
    });
    setIsModalOpen(true);
  };

  useEffect(() => {
    let isCurrent = true;
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchManagementBugList(buildBugListQuery(listQuery))
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

  const handleProductChange = useCallback((productId: string) => {
    const product = productContexts.find((item) => item.id === productId);
    form.setFieldsValue({
      module_code: undefined,
      version_id: product?.versions[0]?.id,
    });
  }, [form, productContexts]);

  const handleDuplicateChange = useCallback((bugId?: string) => {
    if (bugId && editingBug) {
      form.setFieldsValue({ status: 'closed' });
    }
  }, [editingBug, form]);

  const openEditModal = useCallback((row: BugRecord) => {
    if (!ensureCanManageBugs('编辑 Bug')) {
      return;
    }
    setEditingBug(row);
    setBugImages(evidenceImages(row.evidence));
    closeBugImagePreview();
    form.resetFields();
    form.setFieldsValue({
      assignee: row.assignee === '-' ? undefined : row.assignee,
      description: row.description ?? '',
      duplicate_of_bug_id: row.duplicateOfBugId,
      evidence_json: formatEvidenceJson(evidenceWithoutImages(row.evidence)),
      reproduce_steps_text: formatReproduceSteps(row.reproduceSteps),
      severity: row.severity,
      status: row.status,
      title: row.title,
    });
    setIsModalOpen(true);
  }, [closeBugImagePreview, ensureCanManageBugs, form]);

  const handleSave = async () => {
    if (!ensureCanManageBugs(editingBug ? '编辑 Bug' : '登记 Bug')) {
      return;
    }
    try {
      const values = await form.validateFields();
      const duplicateOfBugId = trimText(values.duplicate_of_bug_id);
      const evidence = evidenceWithImages(parseEvidenceJson(values.evidence_json), bugImages);
      const reproduceSteps = parseReproduceSteps(values.reproduce_steps_text);
      setIsSaving(true);
      if (editingBug) {
        await updateManagementBug(editingBug.id, {
          assignee: trimText(values.assignee),
          description: values.description.trim(),
          duplicate_of_bug_id: duplicateOfBugId ?? null,
          evidence,
          reproduce_steps: reproduceSteps,
          severity: values.severity,
          status: values.status,
          title: values.title.trim(),
        });
        message.success('Bug 已更新');
      } else {
        await createManagementBug({
          assignee: trimText(values.assignee),
          description: values.description.trim(),
          duplicate_of_bug_id: duplicateOfBugId,
          evidence,
          module_code: trimText(values.module_code),
          product_id: values.product_id?.trim(),
          related_task_id: trimText(values.related_task_id),
          reproduce_steps: reproduceSteps,
          requirement_id: trimText(values.requirement_id),
          severity: values.severity,
          source: values.source,
          title: values.title.trim(),
          version_id: trimText(values.version_id),
        });
        message.success('Bug 已登记');
      }
      setIsModalOpen(false);
      closeBugImagePreview();
      void reloadDuplicateBugs();
      void reload();
    } catch (saveError) {
      if (isFormValidationError(saveError)) {
        return;
      }
      message.error(formatMutationError(saveError));
    } finally {
      setIsSaving(false);
    }
  };

  const openBugImagePreview = useCallback(async (image: BugImageEvidenceItem) => {
    if (typeof URL.createObjectURL !== 'function') {
      message.error('当前浏览器不支持图片预览');
      return;
    }
    setPreviewingImageKey(image.object_key);
    try {
      const blob = await fetchManagementBugImagePreview(image);
      const url = URL.createObjectURL(blob);
      replaceBugImagePreview({ title: image.filename, url });
    } catch (previewError) {
      message.error(formatMutationError(previewError));
    } finally {
      setPreviewingImageKey(undefined);
    }
  }, [replaceBugImagePreview]);

  const uploadBugImageFiles = useCallback(async (
    files: File[],
    source: BugImageUploadSource,
  ) => {
    if (!ensureCanManageBugs('上传 Bug 图片')) {
      return;
    }
    const imageFiles = files.filter((file) => bugImageMimeTypes.has(file.type));
    if (imageFiles.length === 0) {
      message.warning('请选择 PNG、JPEG、GIF 或 WebP 图片');
      return;
    }
    setIsImageUploading(true);
    try {
      const uploadedImages = await Promise.all(
        imageFiles.map(async (file) =>
          uploadManagementBugImage({
            content_base64: await readFileAsBase64(file),
            filename: file.name,
            mime_type: file.type,
            source,
          }),
        ),
      );
      setBugImages((current) => [...current, ...uploadedImages]);
    } catch (uploadError) {
      message.error(formatMutationError(uploadError));
    } finally {
      setIsImageUploading(false);
    }
  }, [ensureCanManageBugs]);

  const handleImageFileChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.currentTarget.files ?? []);
    event.currentTarget.value = '';
    void uploadBugImageFiles(files, 'file_picker');
  }, [uploadBugImageFiles]);

  const handleImagePaste = useCallback((event: ReactClipboardEvent<HTMLTextAreaElement>) => {
    const files = clipboardImageFiles(event);
    if (files.length === 0) {
      return;
    }
    event.preventDefault();
    void uploadBugImageFiles(files, 'clipboard');
  }, [uploadBugImageFiles]);

  const removeBugImage = useCallback((objectKey: string) => {
    if (!ensureCanManageBugs('移除 Bug 图片')) {
      return;
    }
    setBugImages((current) => current.filter((image) => image.object_key !== objectKey));
  }, [ensureCanManageBugs]);

  const handleDelete = useCallback(async (row: BugRecord) => {
    if (!ensureCanManageBugs('删除 Bug')) {
      return;
    }
    try {
      await deleteManagementBug(row.id);
      message.success('Bug 已删除');
      await reloadDuplicateBugs();
      await reload();
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [ensureCanManageBugs, reload, reloadDuplicateBugs]);

  const openBatchModal = useCallback(() => {
    if (!ensureCanManageBugs('批量处理 Bug')) {
      return;
    }
    if (selectedBugIds.length === 0) {
      message.warning('请选择需要批量处理的 Bug');
      return;
    }
    batchForm.resetFields();
    setIsBatchModalOpen(true);
  }, [batchForm, ensureCanManageBugs, selectedBugIds.length]);

  const handleBatchUpdate = useCallback(async () => {
    if (!ensureCanManageBugs('批量处理 Bug')) {
      return;
    }
    try {
      const values = await batchForm.validateFields();
      const payload = {
        assignee: trimText(values.assignee),
        bug_ids: selectedBugIds,
        reason: trimText(values.reason),
        severity: values.severity,
        status: values.status,
      };
      if (!payload.status && !payload.severity && !payload.assignee) {
        message.warning('请至少选择一个批量更新字段');
        return;
      }
      setIsBatchSaving(true);
      const result = await batchUpdateManagementBugs(payload);
      setBatchResult({
        batchId: result.batchId,
        primaryCount: result.updatedCount,
        primaryLabel: '更新数',
        skipped: result.skipped,
        title: 'Bug 批量处理结果',
      });
      message.success(`Bug 批量处理完成：更新 ${result.updatedCount} 条，跳过 ${result.skippedCount} 条`);
      setSelectedRowKeys([]);
      setIsBatchModalOpen(false);
      await reloadDuplicateBugs();
      await reload();
    } catch (batchError) {
      if (isFormValidationError(batchError)) {
        return;
      }
      message.error(formatMutationError(batchError));
    } finally {
      setIsBatchSaving(false);
    }
  }, [batchForm, ensureCanManageBugs, reload, reloadDuplicateBugs, selectedBugIds]);

  const toolbarActions = useMemo(
    () => canManageBugs ? [
      <Button
        disabled={selectedRowKeys.length === 0}
        icon={<CheckSquareOutlined />}
        key="batch-update"
        onClick={openBatchModal}
      >
        批量处理
      </Button>,
    ] : [],
    [canManageBugs, openBatchModal, selectedRowKeys.length],
  );

  const columns = useMemo<ProColumns<BugRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        sorter: true,
        title: 'Bug 编号',
      },
      {
        dataIndex: 'title',
        sorter: true,
        title: 'Bug 标题',
      },
      {
        dataIndex: 'module',
        sorter: true,
        title: '所属模块',
      },
      {
        dataIndex: 'versionName',
        sorter: true,
        title: '迭代版本',
      },
      {
        dataIndex: 'severity',
        sorter: true,
        title: '严重级别',
        render: (_, row) => {
          const severity = severityLabels[row.severity];
          return <StatusTag color={severity.color} label={severity.label} />;
        },
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
        dataIndex: 'source',
        sorter: true,
        title: '来源',
        render: (_, row) => {
          const source = sourceLabels[row.source];
          return <StatusTag color={source.color} label={source.label} />;
        },
      },
      {
        dataIndex: 'assignee',
        sorter: true,
        title: '处理人',
      },
      {
        dataIndex: 'createdAt',
        sorter: true,
        title: '创建时间',
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button href={fullChainSubjectHref('bug', row.id)} type="link">
              全链路
            </Button>
            {canManageBugs ? (
              <>
                <Button icon={<EditOutlined />} onClick={() => openEditModal(row)} type="link">
                  编辑
                </Button>
                <Popconfirm okText="删除" onConfirm={() => handleDelete(row)} title={`删除 Bug ${row.id}？`}>
                  <Button danger icon={<DeleteOutlined />} type="link">
                    删除
                  </Button>
                </Popconfirm>
              </>
            ) : null}
          </Space>
        ),
      },
    ],
    [canManageBugs, handleDelete, openEditModal],
  );

  return (
    <>
      <ManagementListPage<BugRecord>
        breadcrumbGroup="需求交付"
        columns={columns}
        dataSource={listState.rows}
        viewStorageKey="delivery.bugs"
        filters={[
          { label: 'Bug 标题', name: 'title', type: 'text' },
          { label: '所属模块', name: 'module', type: 'text' },
          { label: '迭代版本', name: 'versionName', type: 'text' },
          {
            label: '严重级别',
            name: 'severity',
            options: [
              { label: '阻断', value: 'blocker' },
              { label: '致命', value: 'critical' },
              { label: '严重', value: 'major' },
              { label: '一般', value: 'minor' },
            ],
            type: 'select',
          },
          {
            label: '状态',
            name: 'status',
            options: [
              { label: '待处理', value: 'open' },
              { label: '待补充', value: 'needs_info' },
              { label: '已分诊', value: 'triaged' },
              { label: '已分派', value: 'assigned' },
              { label: '已修复', value: 'fixed' },
              { label: '已验证', value: 'verified' },
              { label: '已关闭', value: 'closed' },
              { label: '重新打开', value: 'reopened' },
            ],
            type: 'select',
          },
        ]}
        loading={listState.status === 'loading'}
        notice={formatRemoteRowsError(listState.error ?? productContextError ?? duplicateBugsError)}
        onPrimaryAction={canManageBugs ? openCreateModal : undefined}
        onReload={() => void reload()}
        primaryAction={canManageBugs ? '登记 Bug' : undefined}
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="id"
        rowSelection={canManageBugs
          ? {
              onChange: setSelectedRowKeys,
              selectedRowKeys,
            }
          : undefined}
        tableTitle="Bug 列表"
        title="Bug 管理"
        toolbarActions={toolbarActions}
      />
      <ManagementBatchResultModal onClose={() => setBatchResult(null)} result={batchResult} />
      <Modal
        cancelText="取消"
        confirmLoading={isBatchSaving}
        destroyOnHidden
        onCancel={() => setIsBatchModalOpen(false)}
        okText="批量处理"
        onOk={handleBatchUpdate}
        open={isBatchModalOpen}
        title={`批量处理 Bug（${selectedBugIds.length} 条）`}
        width={560}
      >
        <Form<BugBatchFormValues> form={batchForm} layout="vertical">
          <Form.Item label="状态" name="status">
            <Select
              allowClear
              options={[
                { label: '待处理', value: 'open' },
                { label: '待补充', value: 'needs_info' },
                { label: '已分诊', value: 'triaged' },
                { label: '已分派', value: 'assigned' },
                { label: '已修复', value: 'fixed' },
                { label: '已验证', value: 'verified' },
                { label: '已关闭', value: 'closed' },
                { label: '重新打开', value: 'reopened' },
              ]}
              placeholder="可选，按状态机批量推进"
            />
          </Form.Item>
          <Form.Item label="严重级别" name="severity">
            <Select
              allowClear
              options={[
                { label: '阻断', value: 'blocker' },
                { label: '致命', value: 'critical' },
                { label: '严重', value: 'major' },
                { label: '一般', value: 'minor' },
              ]}
              placeholder="可选"
            />
          </Form.Item>
          <Form.Item label="处理人" name="assignee">
            <Input placeholder="可选，例如 qa@example.com" />
          </Form.Item>
          <Form.Item label="处理说明" name="reason">
            <Input.TextArea placeholder="可选，写入批量审计" rows={2} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        cancelText="取消"
        confirmLoading={isSaving}
        destroyOnHidden
        onCancel={() => {
          setIsModalOpen(false);
          closeBugImagePreview();
        }}
        okText="保存"
        okButtonProps={{ disabled: isImageUploading }}
        onOk={handleSave}
        open={isModalOpen}
        title={editingBug ? '编辑 Bug' : '登记 Bug'}
        width={680}
      >
        <Form<BugFormValues> form={form} layout="vertical">
          <Form.Item label="Bug 标题" name="title" rules={[{ required: true, message: '请输入 Bug 标题' }]}>
            <Input />
          </Form.Item>
          {!editingBug ? (
            <>
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
              <Form.Item label="目标版本" name="version_id">
                <Select
                  allowClear
                  disabled={!selectedProduct || versionOptions.length === 0}
                  loading={productContextStatus === 'loading'}
                  options={versionOptions}
                  placeholder={selectedProduct ? '请选择版本，可留空' : '请先选择产品'}
                />
              </Form.Item>
              <Form.Item label="模块编码" name="module_code">
                <Input />
              </Form.Item>
              <Form.Item label="来源" name="source" rules={[{ required: true, message: '请选择来源' }]}>
                <Select
                  options={[
                    { label: '人工登记', value: 'manual_test' },
                    { label: 'AI 自动测试', value: 'ai_auto_test' },
                    { label: 'AI 上线后分析', value: 'ai_post_release' },
                  ]}
                />
              </Form.Item>
              <Form.Item label="关联需求 ID" name="requirement_id">
                <Input />
              </Form.Item>
              <Form.Item label="关联任务 ID" name="related_task_id">
                <Input />
              </Form.Item>
            </>
          ) : (
            <Form.Item label="来源">
              <Input aria-label="来源" disabled value={sourceLabels[editingBug.source].label} />
            </Form.Item>
          )}
          <Form.Item label="严重级别" name="severity" rules={[{ required: true, message: '请选择严重级别' }]}>
            <Select
              options={[
                { label: '阻断', value: 'blocker' },
                { label: '致命', value: 'critical' },
                { label: '严重', value: 'major' },
                { label: '一般', value: 'minor' },
              ]}
            />
          </Form.Item>
          {editingBug ? (
            <Form.Item label="状态" name="status">
              <Select
                options={[
                  { label: '待处理', value: 'open' },
                  { label: '待补充', value: 'needs_info' },
                  { label: '已分诊', value: 'triaged' },
                  { label: '已分派', value: 'assigned' },
                  { label: '已修复', value: 'fixed' },
                  { label: '已验证', value: 'verified' },
                  { label: '已关闭', value: 'closed' },
                  { label: '重新打开', value: 'reopened' },
                ]}
              />
            </Form.Item>
          ) : null}
          <Form.Item label="重复归并" name="duplicate_of_bug_id">
            <Select
              allowClear
              disabled={duplicateBugOptions.length === 0}
              onChange={handleDuplicateChange}
              optionFilterProp="label"
              options={duplicateBugOptions}
              placeholder={duplicateBugOptions.length === 0 ? '暂无可归并 Bug' : '选择主 Bug，可留空'}
              showSearch
            />
          </Form.Item>
          <Form.Item label="处理人" name="assignee">
            <Input />
          </Form.Item>
          <Form.Item label="描述" name="description" rules={[{ required: true, message: '请输入 Bug 描述' }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item label="复现步骤" name="reproduce_steps_text">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item label="Bug 图片">
            <Space orientation="vertical" style={{ width: '100%' }}>
              <Space wrap>
                <Button
                  icon={<UploadOutlined />}
                  loading={isImageUploading}
                  onClick={() => imageInputRef.current?.click()}
                >
                  选择图片
                </Button>
                <Tag>{bugImages.length} 张</Tag>
                <input
                  accept="image/*"
                  aria-label="选择图片文件"
                  multiple
                  onChange={handleImageFileChange}
                  ref={imageInputRef}
                  style={{ display: 'none' }}
                  type="file"
                />
              </Space>
              <Input.TextArea
                aria-label="粘贴图片区域"
                onPaste={handleImagePaste}
                placeholder="粘贴图片"
                readOnly
                rows={2}
                value=""
              />
              {bugImages.length ? (
                <Space orientation="vertical" style={{ width: '100%' }}>
                  {bugImages.map((image) => (
                    <Space
                      key={`${image.id}:${image.object_key}`}
                      style={{
                        border: '1px solid #d9d9d9',
                        borderRadius: 6,
                        justifyContent: 'space-between',
                        padding: '6px 8px',
                        width: '100%',
                      }}
                    >
                      <Button
                        aria-label={`预览图片 ${image.filename}`}
                        icon={<EyeOutlined />}
                        loading={previewingImageKey === image.object_key}
                        onClick={() => void openBugImagePreview(image)}
                        size="small"
                        style={{
                          maxWidth: 360,
                          overflow: 'hidden',
                          paddingInline: 0,
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                        title={image.filename}
                        type="link"
                      >
                        {image.filename}
                      </Button>
                      <Space size={4}>
                        <Tag>{image.storage_provider}</Tag>
                        <Button
                          aria-label={`移除图片 ${image.filename}`}
                          icon={<DeleteOutlined />}
                          onClick={() => removeBugImage(image.object_key)}
                          size="small"
                          type="text"
                        />
                      </Space>
                    </Space>
                  ))}
                </Space>
              ) : null}
            </Space>
          </Form.Item>
          <Form.Item label="证据 JSON" name="evidence_json" rules={[evidenceJsonRule()]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        footer={null}
        onCancel={closeBugImagePreview}
        open={Boolean(imagePreview)}
        title={imagePreview?.title ?? '图片预览'}
        width={720}
      >
        {imagePreview ? (
          <img
            alt={imagePreview.title}
            src={imagePreview.url}
            style={{
              display: 'block',
              margin: '0 auto',
              maxHeight: '70vh',
              maxWidth: '100%',
            }}
          />
        ) : null}
      </Modal>
    </>
  );
}
