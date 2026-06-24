import {
  ArrowRightOutlined,
  CalendarOutlined,
  CodeOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Alert, Button, Checkbox, Form, Input, Modal, Popconfirm, Select, Space, Table, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { DateStringPicker } from '../../components/DateStringPicker';
import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import type {
  ProductContextOption,
  ProductGitRepositoryRecord,
  ProductVersionBranchConfigRecord,
  ProductVersionRecord,
  RequirementRecord,
} from '../../data/management';
import { formatRemoteRowsError, normalizeRemoteRowsError, useRemoteRows, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  advanceProductVersionStatus,
  batchScheduleRequirements,
  createProductVersion,
  createProductVersionBranchConfig,
  deleteProductVersionBranchConfig,
  deleteProductVersion,
  fetchDeliveryIterationVersionList,
  fetchManagementRequirements,
  fetchProductContextOptions,
  fetchProductGitRepositoryRecords,
  fetchProductVersionBranchConfigs,
  type ProductVersionAdvanceStatusResult,
  type ProductVersionBranchConfigMutationPayload,
  type ProductVersionListQuery,
  updateProductVersionBranchConfig,
  updateProductVersion,
} from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';

type IterationVersionFormValues = {
  code: string;
  description?: string;
  name: string;
  product_id: string;
  release_date?: string;
  start_date?: string;
  status: ProductVersionRecord['status'];
};

type CollectRequirementsFormValues = {
  reason?: string;
};

type AdvanceVersionFormValues = {
  force?: boolean;
  reason?: string;
  target_status: ProductVersionRecord['status'];
};

type BranchConfigFormValues = {
  base_branch?: string;
  branch_status: ProductVersionBranchConfigRecord['branchStatus'];
  creation_source: ProductVersionBranchConfigRecord['creationSource'];
  description?: string;
  repository_id: string;
  working_branch: string;
};

const versionStatusLabels: Record<ProductVersionRecord['status'], { color: string; label: string }> = {
  active: { color: 'blue', label: '开发中' },
  archived: { color: 'default', label: '历史归档' },
  planning: { color: 'gold', label: '规划中' },
  released: { color: 'green', label: '已发布' },
  testing: { color: 'purple', label: '测试中' },
};
const requirementStatusLabels: Record<RequirementRecord['status'], { color: string; label: string }> = {
  accepted: { color: 'green', label: '已验收' },
  approved: { color: 'green', label: '需求池' },
  cancelled: { color: 'default', label: '已取消' },
  closed: { color: 'default', label: '已关闭' },
  code_reviewing: { color: 'purple', label: '代码评审中' },
  deferred: { color: 'default', label: '暂缓' },
  designing: { color: 'blue', label: '设计中' },
  developing: { color: 'geekblue', label: '开发中' },
  draft: { color: 'default', label: '草稿' },
  planned: { color: 'cyan', label: '已排期' },
  ready_for_dev: { color: 'lime', label: '待开发' },
  ready_for_release: { color: 'orange', label: '待发布' },
  rejected: { color: 'red', label: '已拒绝' },
  released: { color: 'green', label: '已发布' },
  submitted: { color: 'gold', label: '待评审' },
  testing: { color: 'volcano', label: '测试中' },
};

const collectableRequirementStatuses = new Set<RequirementRecord['status']>(['approved', 'planned']);
const collectableVersionStatuses = new Set<ProductVersionRecord['status']>(['active', 'planning']);
const versionStatusAdvanceTargets: Partial<Record<ProductVersionRecord['status'], ProductVersionRecord['status']>> = {
  active: 'testing',
  planning: 'active',
  testing: 'released',
};
const branchStatusLabels: Record<ProductVersionBranchConfigRecord['branchStatus'], { color: string; label: string }> = {
  active: { color: 'blue', label: '开发中' },
  archived: { color: 'default', label: '已归档' },
  merged: { color: 'green', label: '已合并' },
  not_created: { color: 'default', label: '未创建' },
  released: { color: 'green', label: '已发布' },
  testing: { color: 'purple', label: '测试中' },
};
const branchCreationSourceLabels: Record<ProductVersionBranchConfigRecord['creationSource'], string> = {
  ai_task: 'AI 任务生成',
  github_sync: 'GitHub 同步',
  gitlab_sync: 'GitLab 同步',
  manual: '手工登记',
};

const versionStatusOptions = [
  { label: '规划中', value: 'planning' },
  { label: '开发中', value: 'active' },
  { label: '测试中', value: 'testing' },
  { label: '已发布', value: 'released' },
  { label: '历史归档', value: 'archived' },
];
const versionCreateStatusOptions = versionStatusOptions.filter((option) =>
  ['active', 'planning'].includes(option.value),
);
const branchStatusOptions = Object.entries(branchStatusLabels).map(([value, item]) => ({
  label: item.label,
  value,
}));
const branchCreationSourceOptions = Object.entries(branchCreationSourceLabels).map(([value, label]) => ({
  label,
  value,
}));
const versionSortFieldMap: Record<string, string> = {
  code: 'code',
  name: 'name',
  productName: 'product_name',
  releaseDate: 'release_date',
  startDate: 'start_date',
  status: 'status',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildVersionListQuery(query: ManagementListQuery): ProductVersionListQuery {
  return {
    code: normalizeFilterText(query.filters.code),
    name: normalizeFilterText(query.filters.name),
    page: query.page,
    pageSize: query.pageSize,
    product: normalizeFilterText(query.filters.productName),
    sortField: query.sortField ? versionSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
  };
}

export default function IterationVersionsPage() {
  const [form] = Form.useForm<IterationVersionFormValues>();
  const [branchForm] = Form.useForm<BranchConfigFormValues>();
  const [collectForm] = Form.useForm<CollectRequirementsFormValues>();
  const [advanceForm] = Form.useForm<AdvanceVersionFormValues>();
  const [editingVersion, setEditingVersion] = useState<ProductVersionRecord | null>(null);
  const [collectingVersion, setCollectingVersion] = useState<ProductVersionRecord | null>(null);
  const [advancingVersion, setAdvancingVersion] = useState<ProductVersionRecord | null>(null);
  const [viewingVersion, setViewingVersion] = useState<ProductVersionRecord | null>(null);
  const [branchConfigVersion, setBranchConfigVersion] = useState<ProductVersionRecord | null>(null);
  const [editingBranchConfig, setEditingBranchConfig] = useState<ProductVersionBranchConfigRecord | null>(null);
  const [advancePreview, setAdvancePreview] = useState<ProductVersionAdvanceStatusResult | null>(null);
  const [branchConfigs, setBranchConfigs] = useState<ProductVersionBranchConfigRecord[]>([]);
  const [branchRepositories, setBranchRepositories] = useState<ProductGitRepositoryRecord[]>([]);
  const [collectRequirementIds, setCollectRequirementIds] = useState<string[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isAdvancePreviewLoading, setIsAdvancePreviewLoading] = useState(false);
  const [isAdvanceSaving, setIsAdvanceSaving] = useState(false);
  const [isCollectSaving, setIsCollectSaving] = useState(false);
  const [isBranchConfigLoading, setIsBranchConfigLoading] = useState(false);
  const [isBranchConfigSaving, setIsBranchConfigSaving] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'code',
    sortOrder: 'ascend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    rows: ProductVersionRecord[];
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
    error: requirementError,
    reload: reloadRequirements,
    rows: requirements,
    status: requirementStatus,
  } = useRemoteRows(fetchManagementRequirements);
  const {
    error: productError,
    rows: productContexts,
    status: productStatus,
  } = useRemoteRows(fetchProductContextOptions);

  const productOptions = useMemo(
    () =>
      productContexts.map((product: ProductContextOption) => ({
        label: `${product.code} · ${product.name}`,
        value: product.id,
      })),
    [productContexts],
  );
  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchDeliveryIterationVersionList(buildVersionListQuery(listQuery));
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
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchDeliveryIterationVersionList(buildVersionListQuery(listQuery))
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

  const collectableRequirements = useMemo(() => {
    if (!collectingVersion?.productId) {
      return [];
    }
    return requirements.filter(
      (requirement) =>
        requirement.productId === collectingVersion.productId &&
        collectableRequirementStatuses.has(requirement.status),
    );
  }, [collectingVersion, requirements]);
  const currentVersionRequirements = useMemo(() => {
    if (!viewingVersion) {
      return [];
    }
    return requirements
      .filter((requirement) => requirement.versionId === viewingVersion.id)
      .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
  }, [requirements, viewingVersion]);
  const advanceTargetOptions = useMemo(() => {
    const nextStatus = advancingVersion ? versionStatusAdvanceTargets[advancingVersion.status] : undefined;
    return nextStatus
      ? [{ label: versionStatusLabels[nextStatus].label, value: nextStatus }]
      : [];
  }, [advancingVersion]);
  const branchRepositoryOptions = useMemo(
    () =>
      branchRepositories.map((repository) => ({
        label: `${repository.name} · ${repository.provider} · ${repository.projectPath ?? repository.remoteUrl}`,
        value: repository.id,
      })),
    [branchRepositories],
  );

  const loadBranchConfigs = useCallback(async (version: ProductVersionRecord) => {
    if (!version.productId) {
      message.error('版本缺少所属产品，无法维护代码分支');
      return;
    }
    setIsBranchConfigLoading(true);
    try {
      const [repositories, configs] = await Promise.all([
        fetchProductGitRepositoryRecords(version.productId),
        fetchProductVersionBranchConfigs(version.id),
      ]);
      const activeRepositories = repositories.filter((repository) => repository.status === 'active');
      setBranchRepositories(activeRepositories);
      setBranchConfigs(configs);
      if (activeRepositories.length === 1) {
        branchForm.setFieldsValue({
          base_branch: activeRepositories[0].defaultBranch,
          repository_id: activeRepositories[0].id,
        });
      }
    } catch (loadError) {
      message.error(formatMutationError(loadError));
      setBranchRepositories([]);
      setBranchConfigs([]);
    } finally {
      setIsBranchConfigLoading(false);
    }
  }, [branchForm]);

  const openBranchConfigModal = useCallback((row: ProductVersionRecord) => {
    setBranchConfigVersion(row);
    setEditingBranchConfig(null);
    branchForm.resetFields();
    void loadBranchConfigs(row);
  }, [branchForm, loadBranchConfigs]);

  const openEditBranchConfig = useCallback((row: ProductVersionBranchConfigRecord) => {
    setEditingBranchConfig(row);
    branchForm.setFieldsValue({
      base_branch: row.baseBranch,
      branch_status: row.branchStatus,
      creation_source: row.creationSource,
      description: row.description ?? undefined,
      repository_id: row.repositoryId,
      working_branch: row.workingBranch,
    });
  }, [branchForm]);

  const handleSaveBranchConfig = async () => {
    if (!branchConfigVersion) {
      return;
    }
    const values = await branchForm.validateFields();
    const payload: ProductVersionBranchConfigMutationPayload = {
      base_branch: trimText(values.base_branch),
      branch_status: values.branch_status,
      creation_source: values.creation_source,
      description: trimText(values.description),
      repository_id: values.repository_id,
      working_branch: values.working_branch.trim(),
    };
    setIsBranchConfigSaving(true);
    try {
      if (editingBranchConfig) {
        await updateProductVersionBranchConfig(editingBranchConfig.id, payload);
        message.success('代码分支已更新');
      } else {
        await createProductVersionBranchConfig(branchConfigVersion.id, payload);
        message.success('代码分支已保存');
      }
      setEditingBranchConfig(null);
      branchForm.resetFields();
      await loadBranchConfigs(branchConfigVersion);
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsBranchConfigSaving(false);
    }
  };

  const handleDeleteBranchConfig = useCallback(async (row: ProductVersionBranchConfigRecord) => {
    if (!branchConfigVersion) {
      return;
    }
    try {
      await deleteProductVersionBranchConfig(row.id);
      message.success('代码分支已删除');
      await loadBranchConfigs(branchConfigVersion);
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [branchConfigVersion, loadBranchConfigs]);

  const openCreateModal = () => {
    setEditingVersion(null);
    form.resetFields();
    form.setFieldsValue({
      product_id: productContexts[0]?.id,
      status: 'planning',
    });
    setIsModalOpen(true);
  };

  const openEditModal = useCallback((row: ProductVersionRecord) => {
    setEditingVersion(row);
    form.setFieldsValue({
      code: row.code,
      description: row.description,
      name: row.name,
      product_id: row.productId,
      release_date: row.releaseDate,
      start_date: row.startDate,
      status: row.status,
    });
    setIsModalOpen(true);
  }, [form]);

  const handleSave = async () => {
    const values = await form.validateFields();
    const payload = {
      code: trimText(values.code),
      description: trimText(values.description),
      name: values.name.trim(),
      release_date: trimText(values.release_date),
      start_date: trimText(values.start_date),
      ...(editingVersion ? {} : { status: values.status ?? 'planning' }),
    };
    setIsSaving(true);
    try {
      if (editingVersion) {
        await updateProductVersion(editingVersion.id, payload);
        message.success('迭代版本已更新');
      } else {
        await createProductVersion(values.product_id, payload);
        message.success('迭代版本已创建');
      }
      setIsModalOpen(false);
      await reload();
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = useCallback(async (row: ProductVersionRecord) => {
    try {
      await deleteProductVersion(row.id);
      message.success('迭代版本已删除');
      await reload();
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [reload]);

  const openCollectModal = useCallback((row: ProductVersionRecord) => {
    if (!collectableVersionStatuses.has(row.status)) {
      message.warning('只有规划中或开发中的版本可以归集需求');
      return;
    }
    setCollectingVersion(row);
    setCollectRequirementIds([]);
    collectForm.resetFields();
  }, [collectForm]);

  const handleCollectRequirements = async () => {
    if (!collectingVersion?.productId) {
      message.error('版本缺少所属产品，无法归集需求');
      return;
    }
    if (collectRequirementIds.length === 0) {
      message.warning('请至少选择一条需求');
      return;
    }
    let values: CollectRequirementsFormValues;
    try {
      values = await collectForm.validateFields();
    } catch {
      return;
    }
    setIsCollectSaving(true);
    try {
      const result = await batchScheduleRequirements({
        product_id: collectingVersion.productId,
        reason: trimText(values.reason),
        requirement_ids: collectRequirementIds,
        version_id: collectingVersion.id,
      });
      const skippedText = result.skippedCount ? `，跳过 ${result.skippedCount} 条` : '';
      message.success(`已归集 ${result.updatedCount} 条需求${skippedText}`);
      setCollectingVersion(null);
      setCollectRequirementIds([]);
      await reload();
      await reloadRequirements();
    } catch (collectError) {
      message.error(formatMutationError(collectError));
    } finally {
      setIsCollectSaving(false);
    }
  };

  const openAdvanceModal = useCallback((row: ProductVersionRecord) => {
    const nextStatus = versionStatusAdvanceTargets[row.status];
    if (!nextStatus) {
      message.warning('当前版本状态没有可推进的下一阶段');
      return;
    }
    setAdvancingVersion(row);
    setAdvancePreview(null);
    advanceForm.resetFields();
    advanceForm.setFieldsValue({
      force: false,
      reason: undefined,
      target_status: nextStatus,
    });
  }, [advanceForm]);

  const handlePreviewAdvance = async () => {
    if (!advancingVersion) {
      return;
    }
    let values: AdvanceVersionFormValues;
    try {
      values = await advanceForm.validateFields();
    } catch {
      return;
    }
    setIsAdvancePreviewLoading(true);
    try {
      const result = await advanceProductVersionStatus(advancingVersion.id, {
        force: Boolean(values.force),
        preview_only: true,
        reason: trimText(values.reason),
        target_status: values.target_status,
      });
      setAdvancePreview(result);
    } catch (previewError) {
      message.error(formatMutationError(previewError));
    } finally {
      setIsAdvancePreviewLoading(false);
    }
  };

  const handleAdvanceVersion = async () => {
    if (!advancingVersion) {
      return;
    }
    if (!advancePreview) {
      message.warning('请先生成影响预览');
      return;
    }
    let values: AdvanceVersionFormValues;
    try {
      values = await advanceForm.validateFields();
    } catch {
      return;
    }
    setIsAdvanceSaving(true);
    try {
      const result = await advanceProductVersionStatus(advancingVersion.id, {
        force: Boolean(values.force),
        preview_only: false,
        reason: trimText(values.reason),
        target_status: values.target_status,
      });
      message.success(`版本已推进到${versionStatusLabels[result.targetStatus].label}`);
      setAdvancingVersion(null);
      setAdvancePreview(null);
      await reload();
      await reloadRequirements();
    } catch (advanceError) {
      message.error(formatMutationError(advanceError));
    } finally {
      setIsAdvanceSaving(false);
    }
  };

  const columns = useMemo<ProColumns<ProductVersionRecord>[]>(
    () => [
      {
        dataIndex: 'productName',
        sorter: true,
        title: '所属产品',
      },
      {
        dataIndex: 'code',
        sorter: true,
        title: '版本编码',
      },
      {
        dataIndex: 'name',
        sorter: true,
        title: '版本名称',
      },
      {
        dataIndex: 'status',
        sorter: true,
        title: '状态',
        render: (_, row) => {
          const statusLabel = versionStatusLabels[row.status];
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
      },
      {
        dataIndex: 'startDate',
        sorter: true,
        title: '开始时间',
        render: (_, row) => row.startDate ?? '-',
      },
      {
        dataIndex: 'releaseDate',
        sorter: true,
        title: '计划发布时间',
        render: (_, row) => row.releaseDate ?? '-',
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button icon={<EditOutlined />} onClick={() => openEditModal(row)} type="link">
              编辑
            </Button>
            <Button icon={<EyeOutlined />} onClick={() => setViewingVersion(row)} type="link">
              查看需求
            </Button>
            <Button
              disabled={!versionStatusAdvanceTargets[row.status]}
              icon={<ArrowRightOutlined />}
              onClick={() => openAdvanceModal(row)}
              type="link"
            >
              推进状态
            </Button>
            <Button icon={<CodeOutlined />} onClick={() => openBranchConfigModal(row)} type="link">
              代码分支
            </Button>
            <Button
              disabled={!collectableVersionStatuses.has(row.status)}
              icon={<CalendarOutlined />}
              onClick={() => openCollectModal(row)}
              type="link"
            >
              归集需求
            </Button>
            <Popconfirm okText="删除" onConfirm={() => handleDelete(row)} title={`删除版本 ${row.code}？`}>
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [handleDelete, openAdvanceModal, openBranchConfigModal, openCollectModal, openEditModal],
  );

  return (
    <>
      <ManagementListPage<ProductVersionRecord>
        breadcrumbGroup="需求交付"
        columns={columns}
        dataSource={listState.rows}
        viewStorageKey="delivery.versions"
        filters={[
          { label: '所属产品', name: 'productName', type: 'text' },
          { label: '版本编码', name: 'code', type: 'text' },
          { label: '版本名称', name: 'name', type: 'text' },
          {
            label: '状态',
            name: 'status',
            options: versionStatusOptions,
            type: 'select',
          },
        ]}
        loading={listState.status === 'loading'}
        notice={formatRemoteRowsError(listState.error ?? productError ?? requirementError)}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="新增迭代版本"
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          total: listState.total,
        }}
        rowKey="id"
        tableTitle="迭代版本列表"
        title="迭代版本"
      />
      <Modal
        destroyOnHidden
        footer={null}
        onCancel={() => {
          setBranchConfigVersion(null);
          setEditingBranchConfig(null);
          setBranchConfigs([]);
          setBranchRepositories([]);
        }}
        open={Boolean(branchConfigVersion)}
        title={branchConfigVersion ? `代码分支 · ${branchConfigVersion.code}` : '代码分支'}
        width={980}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            title={
              branchConfigVersion
                ? `${branchConfigVersion.productName ?? branchConfigVersion.productId} · ${
                    branchConfigVersion.name
                  }`
                : '请选择迭代版本'
            }
            description="迭代版本维护版本级代码分支，开发任务和 PR/Review 继承该分支上下文。"
            type="info"
          />
          <Form<BranchConfigFormValues>
            form={branchForm}
            layout="vertical"
            onValuesChange={(changedValues) => {
              if ('repository_id' in changedValues && !editingBranchConfig) {
                const repository = branchRepositories.find((item) => item.id === changedValues.repository_id);
                if (repository) {
                  branchForm.setFieldValue('base_branch', repository.defaultBranch);
                }
              }
            }}
          >
            <Form.Item label="关联代码库" name="repository_id" rules={[{ required: true, message: '请选择代码库' }]}>
              <Select
                disabled={Boolean(editingBranchConfig)}
                loading={isBranchConfigLoading}
                optionFilterProp="label"
                options={branchRepositoryOptions}
                placeholder="请选择代码库"
                showSearch
              />
            </Form.Item>
            <Form.Item label="基准分支" name="base_branch">
              <Input placeholder="main / master" />
            </Form.Item>
            <Form.Item label="开发分支" name="working_branch" rules={[{ required: true, message: '请输入开发分支' }]}>
              <Input placeholder="release/2026-06 或 feature/version-code" />
            </Form.Item>
            <Form.Item label="分支状态" name="branch_status" initialValue="not_created">
              <Select options={branchStatusOptions} />
            </Form.Item>
            <Form.Item label="创建来源" name="creation_source" initialValue="manual">
              <Select options={branchCreationSourceOptions} />
            </Form.Item>
            <Form.Item label="说明" name="description">
              <Input.TextArea rows={2} />
            </Form.Item>
            <Space>
              <Button loading={isBranchConfigSaving} onClick={() => void handleSaveBranchConfig()} type="primary">
                {editingBranchConfig ? '保存分支' : '新增分支'}
              </Button>
              {editingBranchConfig ? (
                <Button
                  onClick={() => {
                    setEditingBranchConfig(null);
                    branchForm.resetFields();
                  }}
                >
                  取消编辑
                </Button>
              ) : null}
            </Space>
          </Form>
          <Table<ProductVersionBranchConfigRecord>
            columns={[
              { dataIndex: 'repositoryName', title: '代码库' },
              { dataIndex: 'baseBranch', title: '基准分支' },
              { dataIndex: 'workingBranch', title: '开发分支' },
              {
                dataIndex: 'branchStatus',
                render: (_, row) => {
                  const statusLabel = branchStatusLabels[row.branchStatus];
                  return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
                },
                title: '状态',
              },
              {
                dataIndex: 'creationSource',
                render: (_, row) => branchCreationSourceLabels[row.creationSource],
                title: '来源',
              },
              {
                key: 'actions',
                render: (_, row) => (
                  <Space size={4}>
                    <Button icon={<EditOutlined />} onClick={() => openEditBranchConfig(row)} type="link">
                      编辑
                    </Button>
                    <Popconfirm okText="删除" onConfirm={() => handleDeleteBranchConfig(row)} title="删除该分支配置？">
                      <Button danger icon={<DeleteOutlined />} type="link">
                        删除
                      </Button>
                    </Popconfirm>
                  </Space>
                ),
                title: '操作',
              },
            ]}
            dataSource={branchConfigs}
            loading={isBranchConfigLoading}
            locale={{ emptyText: '当前版本暂无代码分支配置' }}
            pagination={false}
            rowKey="id"
            size="small"
          />
        </Space>
      </Modal>
      <Modal
        destroyOnHidden
        footer={null}
        onCancel={() => setViewingVersion(null)}
        open={Boolean(viewingVersion)}
        title={viewingVersion ? `查看需求 · ${viewingVersion.code}` : '查看需求'}
        width={920}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            title={
              viewingVersion
                ? `${viewingVersion.productName ?? viewingVersion.productId} · ${viewingVersion.name} · ${
                    versionStatusLabels[viewingVersion.status].label
                  } · ${currentVersionRequirements.length} 条需求`
                : '请选择迭代版本'
            }
            type="info"
          />
          <Table<RequirementRecord>
            columns={[
              { dataIndex: 'id', title: '需求编号' },
              { dataIndex: 'title', title: '需求标题' },
              {
                dataIndex: 'status',
                render: (_, row) => {
                  const statusLabel = requirementStatusLabels[row.status];
                  return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
                },
                title: '状态',
              },
              {
                dataIndex: 'priority',
                render: (_, row) => (
                  <StatusTag color={row.priority === 'P0' ? 'red' : 'blue'} label={row.priority} />
                ),
                title: '优先级',
              },
              { dataIndex: 'updatedAt', title: '更新时间' },
            ]}
            dataSource={currentVersionRequirements}
            locale={{
              emptyText: requirementStatus === 'loading' ? '正在加载需求' : '当前版本暂无需求',
            }}
            pagination={currentVersionRequirements.length > 5 ? { pageSize: 5 } : false}
            rowKey="id"
            size="small"
          />
        </Space>
      </Modal>
      <Modal
        confirmLoading={isSaving}
        destroyOnHidden
        onCancel={() => setIsModalOpen(false)}
        onOk={() => void handleSave()}
        open={isModalOpen}
        title={editingVersion ? '编辑迭代版本' : '新增迭代版本'}
      >
        <Form<IterationVersionFormValues> form={form} layout="vertical">
          <Form.Item label="所属产品" name="product_id" rules={[{ required: true, message: '请选择产品' }]}>
            <Select
              disabled={Boolean(editingVersion)}
              loading={productStatus === 'loading'}
              optionFilterProp="label"
              options={productOptions}
              placeholder="请选择产品"
              showSearch
            />
          </Form.Item>
          <Form.Item label="版本编码" name="code" rules={[{ required: true, message: '请输入版本编码' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="版本名称" name="name" rules={[{ required: true, message: '请输入版本名称' }]}>
            <Input />
          </Form.Item>
          {!editingVersion ? (
            <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
              <Select options={versionCreateStatusOptions} />
            </Form.Item>
          ) : null}
          <Form.Item label="开始时间" name="start_date">
            <DateStringPicker placeholder="请选择开始时间" />
          </Form.Item>
          <Form.Item label="计划发布时间" name="release_date">
            <DateStringPicker placeholder="请选择计划发布时间" />
          </Form.Item>
          <Form.Item label="目标说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        confirmLoading={isAdvanceSaving}
        destroyOnHidden
        okText="确认推进"
        onCancel={() => {
          setAdvancingVersion(null);
          setAdvancePreview(null);
        }}
        onOk={() => void handleAdvanceVersion()}
        open={Boolean(advancingVersion)}
        title="推进版本状态"
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            title={
              advancingVersion
                ? `${advancingVersion.code} · ${versionStatusLabels[advancingVersion.status].label}`
                : '请选择迭代版本'
            }
            type="info"
          />
          <Form<AdvanceVersionFormValues>
            form={advanceForm}
            layout="vertical"
            onValuesChange={(changedValues) => {
              if ('target_status' in changedValues) {
                setAdvancePreview(null);
              }
            }}
          >
            <Form.Item label="目标状态" name="target_status" rules={[{ required: true, message: '请选择目标状态' }]}>
              <Select options={advanceTargetOptions} />
            </Form.Item>
            <Form.Item label="推进原因" name="reason">
              <Input.TextArea rows={2} />
            </Form.Item>
            <Form.Item name="force" valuePropName="checked">
              <Checkbox>允许带风险推进</Checkbox>
            </Form.Item>
            <Button loading={isAdvancePreviewLoading} onClick={() => void handlePreviewAdvance()}>
              生成影响预览
            </Button>
          </Form>
          {advancePreview ? (
            <Space orientation="vertical" size={12} style={{ width: '100%' }}>
              <Alert title={`将推进 ${advancePreview.updatedRequirements.length} 条需求`} type="success" />
              {advancePreview.updatedRequirements.map((requirement) => (
                <div key={requirement.id}>
                  {requirement.title} · {requirement.from_status} → {requirement.to_status}
                </div>
              ))}
              <Alert
                title={`阻塞 ${advancePreview.blockedRequirements.length} 条需求`}
                type={advancePreview.blockedRequirements.length ? 'warning' : 'info'}
              />
              {advancePreview.blockedRequirements.map((requirement) => (
                <div key={requirement.id}>
                  {requirement.title} · {requirement.status} · {requirement.block_reason}
                </div>
              ))}
            </Space>
          ) : null}
        </Space>
      </Modal>
      <Modal
        confirmLoading={isCollectSaving}
        destroyOnHidden
        okText="确认归集"
        onCancel={() => setCollectingVersion(null)}
        onOk={() => void handleCollectRequirements()}
        open={Boolean(collectingVersion)}
        title={collectingVersion ? `归集需求到 ${collectingVersion.code}` : '归集需求'}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            title={
              collectingVersion
                ? `${collectingVersion.productName ?? collectingVersion.productId} · ${collectingVersion.name}`
                : '请选择迭代版本'
            }
            type="info"
          />
          {collectableRequirements.length ? (
            <Checkbox.Group
              onChange={(values) => setCollectRequirementIds(values.map((value) => String(value)))}
              value={collectRequirementIds}
            >
              <Space orientation="vertical">
                {collectableRequirements.map((requirement) => (
                  <Checkbox key={requirement.id} value={requirement.id}>
                    {requirement.title}
                    <span style={{ color: '#667085', marginLeft: 8 }}>
                      {requirement.versionName ?? '未排期'} · {requirement.id}
                    </span>
                  </Checkbox>
                ))}
              </Space>
            </Checkbox.Group>
          ) : (
            <Alert
              title={
                requirementStatus === 'loading'
                  ? '正在加载可归集需求'
                  : '当前版本所属产品暂无需求池或已排期需求'
              }
              type="warning"
            />
          )}
          <Form<CollectRequirementsFormValues> form={collectForm} layout="vertical">
            <Form.Item label="归集原因" name="reason">
              <Input.TextArea rows={2} />
            </Form.Item>
          </Form>
        </Space>
      </Modal>
    </>
  );
}
