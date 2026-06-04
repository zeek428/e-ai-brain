import { ApartmentOutlined, CalendarOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Alert, Button, Descriptions, Form, Input, Modal, Popconfirm, Select, Space, Spin, Tag, Timeline, Typography, message } from 'antd';
import { type Key, useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import type { RequirementRecord } from '../../data/management';
import { formatRemoteRowsError, normalizeRemoteRowsError, useRemoteRows, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  approveManagementRequirement,
  batchScheduleRequirements,
  createManagementRequirement,
  deleteManagementRequirement,
  fetchManagementRequirementList,
  fetchRequirementFullChain,
  fetchRequirementProductContextOptions,
  generateRequirementTask,
  rejectManagementRequirement,
  type RequirementFullChainRecord,
  type RequirementListQuery,
  updateManagementRequirement,
} from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';

const statusLabels: Record<RequirementRecord['status'], { color: string; label: string }> = {
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

type RequirementFormValues = {
  content: string;
  module_code?: string;
  priority: RequirementRecord['priority'];
  product_id: string;
  title: string;
  version_id?: string;
};

type BatchScheduleFormValues = {
  product_id: string;
  reason?: string;
  version_id: string;
};

const batchSchedulableStatuses = new Set<RequirementRecord['status']>(['approved', 'planned']);
const requirementSortFieldMap: Record<string, string> = {
  createdAt: 'created_at',
  id: 'id',
  priority: 'priority',
  product: 'product_name',
  status: 'status',
  title: 'title',
  versionName: 'version_name',
};

const fullChainTypeLabels: Record<string, string> = {
  ai_task: 'AI 任务',
  bug: 'Bug',
  code_review_report: '代码评审',
  git_snapshot: 'PR/MR 快照',
  iteration_version: '迭代版本',
  jenkins_release: '发布',
  knowledge_deposit: '知识沉淀',
  requirement: '需求',
  review: '人工确认',
};

const taskTypeLabels: Record<string, string> = {
  automated_testing: '自动化测试',
  code_review: '代码评审',
  development_planning: '开发计划',
  post_release_analysis: '上线后分析',
  product_detail_design: '产品详细设计',
  release_readiness: '发布评估',
  technical_solution: '技术方案',
};

const fullChainTypeColors: Record<string, string> = {
  bug: 'red',
  code_review_report: 'purple',
  git_snapshot: 'blue',
  jenkins_release: 'orange',
  knowledge_deposit: 'green',
  review: 'cyan',
};

const { Text } = Typography;

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function fullChainTypeLabel(type: string) {
  return fullChainTypeLabels[type] ?? type;
}

function renderSummaryTag(label: string, value: number, color?: string) {
  const separator = /^[A-Za-z]/.test(label) ? ' ' : '';
  return (
    <Tag color={color}>
      {value} 个{separator}
      {label}
    </Tag>
  );
}

function formatRiskLevel(level?: string) {
  if (level === 'high') {
    return '高';
  }
  if (level === 'medium') {
    return '中';
  }
  if (level === 'low') {
    return '低';
  }
  return level || '-';
}

function formatSnapshotRisk(snapshot: RequirementFullChainRecord['gitSnapshots'][number]) {
  const summary = snapshot.riskSummary;
  if (!summary) {
    return '-';
  }
  const largestFile = summary.largestFile?.path
    ? `最大文件 ${summary.largestFile.path} (${summary.largestFile.lineCount ?? 0} 行)`
    : '无最大文件';
  return `${formatRiskLevel(summary.riskLevel)}风险 · ${summary.fileCount ?? 0} 文件 · +${
    summary.totalAdditions ?? 0
  }/-${summary.totalDeletions ?? 0} · ${largestFile}`;
}

function buildRequirementListQuery(query: ManagementListQuery): RequirementListQuery {
  return {
    page: query.page,
    pageSize: query.pageSize,
    priority: normalizeFilterText(query.filters.priority),
    product: normalizeFilterText(query.filters.product),
    sortField: query.sortField ? requirementSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
    title: normalizeFilterText(query.filters.title),
    version: normalizeFilterText(query.filters.versionName),
  };
}

export default function RequirementsPage() {
  const [form] = Form.useForm<RequirementFormValues>();
  const [batchForm] = Form.useForm<BatchScheduleFormValues>();
  const [rejectForm] = Form.useForm<{ rejection_reason: string }>();
  const [editingRequirement, setEditingRequirement] = useState<RequirementRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [rejectingRequirement, setRejectingRequirement] = useState<RequirementRecord | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [fullChainRequirement, setFullChainRequirement] = useState<RequirementRecord | null>(null);
  const [fullChain, setFullChain] = useState<RequirementFullChainRecord | null>(null);
  const [fullChainError, setFullChainError] = useState<RemoteRowsError>();
  const [isFullChainLoading, setIsFullChainLoading] = useState(false);
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
  const selectedProductId = Form.useWatch('product_id', form);
  const selectedBatchProductId = Form.useWatch('product_id', batchForm);
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

  const openCreateModal = () => {
    setEditingRequirement(null);
    form.resetFields();
    const firstProduct = productContexts[0];
    form.setFieldsValue({
      priority: 'P1',
      product_id: firstProduct?.id,
      version_id: undefined,
    });
    setIsModalOpen(true);
  };

  const handleProductChange = useCallback(() => {
    form.setFieldsValue({
      module_code: undefined,
      version_id: undefined,
    });
  }, [form]);

  const openEditModal = useCallback((row: RequirementRecord) => {
    setEditingRequirement(row);
    form.setFieldsValue({
      content: row.content ?? '',
      module_code: row.moduleCode,
      priority: row.priority,
      product_id: row.productId ?? row.product,
      title: row.title,
      version_id: row.versionId,
    });
    setIsModalOpen(true);
  }, [form]);

  const handleSave = async () => {
    const values = await form.validateFields();
    const payload = {
      content: values.content.trim(),
      module_code: trimText(values.module_code),
      priority: values.priority,
      product_id: values.product_id.trim(),
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
    try {
      await deleteManagementRequirement(row.id);
      message.success('需求已删除');
      await reload();
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [reload]);

  const openBatchScheduleModal = useCallback(() => {
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
  }, [batchForm, productContexts, selectedRequirements]);

  const handleBatchSchedule = async () => {
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
      const skippedText = result.skippedCount ? `，跳过 ${result.skippedCount} 条` : '';
      message.success(`已归集 ${result.updatedCount} 条需求${skippedText}`);
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

  const handleApprove = useCallback(async (row: RequirementRecord) => {
    try {
      await approveManagementRequirement(row.id);
      message.success('需求已审批通过');
      await reload();
    } catch (decisionError) {
      message.error(formatMutationError(decisionError));
    }
  }, [reload]);

  const openRejectModal = useCallback((row: RequirementRecord) => {
    setRejectingRequirement(row);
    rejectForm.resetFields();
  }, [rejectForm]);

  const handleReject = async () => {
    if (!rejectingRequirement) {
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
    try {
      const result = await generateRequirementTask(row.id);
      message.success(`已生成 ${result.task_type} 任务：${result.task_id}`);
      await reload();
    } catch (decisionError) {
      message.error(formatMutationError(decisionError));
    }
  }, [reload]);

  const openFullChainModal = useCallback(async (row: RequirementRecord) => {
    setFullChainRequirement(row);
    setFullChain(null);
    setFullChainError(undefined);
    setIsFullChainLoading(true);
    try {
      setFullChain(await fetchRequirementFullChain(row.id));
    } catch (loadError: unknown) {
      setFullChainError(normalizeRemoteRowsError(loadError));
    } finally {
      setIsFullChainLoading(false);
    }
  }, []);

  const toolbarActions = useMemo(
    () => [
      <Button
        disabled={selectedRowKeys.length === 0}
        icon={<CalendarOutlined />}
        key="batch-schedule"
        onClick={openBatchScheduleModal}
      >
        批量排期
      </Button>,
    ],
    [openBatchScheduleModal, selectedRowKeys.length],
  );

  const columns = useMemo<ProColumns<RequirementRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        sorter: true,
        title: '需求编号',
      },
      {
        dataIndex: 'title',
        sorter: true,
        title: '需求标题',
      },
      {
        dataIndex: 'product',
        sorter: true,
        title: '所属产品',
      },
      {
        dataIndex: 'versionName',
        sorter: true,
        title: '迭代版本',
      },
      {
        dataIndex: 'priority',
        sorter: true,
        title: '优先级',
        render: (_, row) => (
          <StatusTag color={row.priority === 'P0' ? 'red' : 'blue'} label={row.priority} />
        ),
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
        dataIndex: 'owner',
        title: '负责人',
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
            <Button icon={<ApartmentOutlined aria-hidden="true" />} onClick={() => void openFullChainModal(row)} type="link">
              全链路
            </Button>
            <Button icon={<EditOutlined />} onClick={() => openEditModal(row)} type="link">
              编辑
            </Button>
            {row.status === 'submitted' ? (
              <>
                <Button onClick={() => handleApprove(row)} type="link">
                  审批通过
                </Button>
                <Button danger onClick={() => openRejectModal(row)} type="link">
                  驳回
                </Button>
              </>
            ) : null}
            {row.status === 'planned' ? (
              <Button onClick={() => handleGenerateTask(row)} type="link">
                生成任务
              </Button>
            ) : null}
            <Popconfirm okText="删除" onConfirm={() => handleDelete(row)} title={`删除需求 ${row.id}？`}>
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [handleApprove, handleDelete, handleGenerateTask, openEditModal, openFullChainModal, openRejectModal],
  );

  return (
    <>
      <ManagementListPage<RequirementRecord>
        breadcrumbGroup="需求交付"
        columns={columns}
        dataSource={listState.rows}
        filters={[
          { label: '需求标题', name: 'title', type: 'text' },
          { label: '所属产品', name: 'product', type: 'text' },
          { label: '迭代版本', name: 'versionName', type: 'text' },
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
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="新增需求"
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          total: listState.total,
        }}
        rowKey="id"
        rowSelection={{
          getCheckboxProps: (row) => ({
            disabled: !batchSchedulableStatuses.has(row.status),
          }),
          onChange: (keys) => setSelectedRowKeys(keys),
          selectedRowKeys,
        }}
        tableTitle="需求列表"
        title="需求管理"
        toolbarActions={toolbarActions}
      />
      <Modal
        destroyOnHidden
        footer={null}
        onCancel={() => {
          setFullChainRequirement(null);
          setFullChain(null);
          setFullChainError(undefined);
        }}
        open={Boolean(fullChainRequirement)}
        title={fullChainRequirement ? `需求全链路 · ${fullChainRequirement.id}` : '需求全链路'}
        width={960}
      >
        <Spin spinning={isFullChainLoading}>
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            {fullChainError ? (
              <Alert message={formatRemoteRowsError(fullChainError)} type="error" />
            ) : null}
            {fullChain ? (
              <>
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="需求" span={2}>
                    <Space size={8} wrap>
                      <Text strong>{fullChain.requirement.title}</Text>
                      <Tag>{fullChain.requirement.id}</Tag>
                      <StatusTag
                        color={statusLabels[fullChain.requirement.status]?.color ?? 'default'}
                        label={statusLabels[fullChain.requirement.status]?.label ?? fullChain.requirement.status}
                      />
                    </Space>
                  </Descriptions.Item>
                  <Descriptions.Item label="产品">
                    {fullChain.product?.code ?? fullChain.requirement.product}
                    {fullChain.product?.name ? ` · ${fullChain.product.name}` : ''}
                  </Descriptions.Item>
                  <Descriptions.Item label="迭代版本">
                    {fullChain.iterationVersion
                      ? `${fullChain.iterationVersion.code ?? fullChain.iterationVersion.id} · ${fullChain.iterationVersion.name ?? fullChain.iterationVersion.id}`
                      : '未排期'}
                  </Descriptions.Item>
                  <Descriptions.Item label="链路摘要" span={2}>
                    <Space size={[4, 4]} wrap>
                      {renderSummaryTag('AI 任务', fullChain.summary.aiTasks, 'blue')}
                      {renderSummaryTag('Review', fullChain.summary.reviews, 'cyan')}
                      {renderSummaryTag('PR/MR 快照', fullChain.summary.gitSnapshots, 'geekblue')}
                      {renderSummaryTag('代码评审', fullChain.summary.codeReviewReports, 'purple')}
                      {renderSummaryTag('Bug', fullChain.summary.bugs, 'red')}
                      {renderSummaryTag('发布记录', fullChain.summary.jenkinsReleases, 'orange')}
                      {renderSummaryTag('知识沉淀', fullChain.summary.knowledgeDeposits, 'green')}
                    </Space>
                  </Descriptions.Item>
                </Descriptions>
                <Timeline
                  items={fullChain.timeline.map((item) => ({
                    content: (
                      <Space orientation="vertical" size={2}>
                        <Space size={8} wrap>
                          <Tag color={fullChainTypeColors[item.type] ?? 'default'}>
                            {fullChainTypeLabel(item.type)}
                          </Tag>
                          <Text strong>{item.title}</Text>
                          {item.status ? <Tag>{item.status}</Tag> : null}
                        </Space>
                        <Text type="secondary">
                          {item.occurredAt} · {item.subjectId}
                        </Text>
                      </Space>
                    ),
                    color: fullChainTypeColors[item.type] ?? 'blue',
                  }))}
                />
                {fullChain.aiTasks.length ? (
                  <Descriptions bordered column={2} size="small" title="AI 任务明细">
                    {fullChain.aiTasks.map((task) => (
                      <Descriptions.Item key={task.id} label={taskTypeLabels[task.type] ?? task.type}>
                        <Space orientation="vertical" size={2}>
                          <Text>{task.label}</Text>
                          <Text type="secondary">{task.id} · {task.status}</Text>
                        </Space>
                      </Descriptions.Item>
                    ))}
                  </Descriptions>
                ) : null}
                {fullChain.gitSnapshots.length ? (
                  <Descriptions bordered column={1} size="small" title="PR/MR 证据">
                    {fullChain.gitSnapshots.map((snapshot) => (
                      <Descriptions.Item key={snapshot.id} label={`快照 ${snapshot.mrIid}`}>
                        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
                          <Space size={[6, 6]} wrap>
                            <Tag color="geekblue">{snapshot.id}</Tag>
                            <Tag color="purple">{formatSnapshotRisk(snapshot)}</Tag>
                            {snapshot.diffSizeBytes !== undefined ? (
                              <Tag>diff {snapshot.diffSizeBytes} bytes</Tag>
                            ) : null}
                          </Space>
                          {snapshot.diffFileTree.length ? (
                            <Space size={[6, 6]} wrap>
                              {snapshot.diffFileTree.map((item) => (
                                <Tag key={item.path} color="blue">
                                  {item.path} · {item.fileCount} 文件 · +{item.additions}/-{item.deletions}
                                </Tag>
                              ))}
                            </Space>
                          ) : null}
                          {snapshot.reviewChecklist.length ? (
                            <Space orientation="vertical" size={2}>
                              {snapshot.reviewChecklist.map((item) => (
                                <Text key={item} type="secondary">
                                  {item}
                                </Text>
                              ))}
                            </Space>
                          ) : null}
                        </Space>
                      </Descriptions.Item>
                    ))}
                  </Descriptions>
                ) : null}
              </>
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
              <Input.TextArea autoSize={{ minRows: 2 }} />
            </Form.Item>
          </Form>
        </Space>
      </Modal>
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
            <Input.TextArea autoSize={{ minRows: 4 }} />
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
            <Input.TextArea autoSize={{ minRows: 3 }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
