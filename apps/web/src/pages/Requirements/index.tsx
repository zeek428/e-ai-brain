import { CalendarOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Alert, Button, Form, Input, Modal, Popconfirm, Select, Space, message } from 'antd';
import { type Key, useCallback, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { RequirementRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  approveManagementRequirement,
  batchScheduleRequirements,
  createManagementRequirement,
  deleteManagementRequirement,
  fetchManagementRequirements,
  fetchRequirementProductContextOptions,
  generateRequirementTask,
  rejectManagementRequirement,
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

export default function RequirementsPage() {
  const [form] = Form.useForm<RequirementFormValues>();
  const [batchForm] = Form.useForm<BatchScheduleFormValues>();
  const [rejectForm] = Form.useForm<{ rejection_reason: string }>();
  const [editingRequirement, setEditingRequirement] = useState<RequirementRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [rejectingRequirement, setRejectingRequirement] = useState<RequirementRecord | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [isBatchSaving, setIsBatchSaving] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(fetchManagementRequirements);
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
  const selectedRequirements = useMemo(() => {
    const selectedIds = new Set(selectedRequirementIds);
    return dataSource.filter((row) => selectedIds.has(row.id));
  }, [dataSource, selectedRequirementIds]);
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
        title: '需求编号',
      },
      {
        dataIndex: 'title',
        title: '需求标题',
      },
      {
        dataIndex: 'product',
        title: '所属产品',
      },
      {
        dataIndex: 'versionName',
        title: '迭代版本',
      },
      {
        dataIndex: 'priority',
        title: '优先级',
        render: (_, row) => (
          <StatusTag color={row.priority === 'P0' ? 'red' : 'blue'} label={row.priority} />
        ),
      },
      {
        dataIndex: 'status',
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
        dataIndex: 'updatedAt',
        title: '更新时间',
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
    [handleApprove, handleDelete, handleGenerateTask, openEditModal, openRejectModal],
  );

  return (
    <>
      <ManagementListPage<RequirementRecord>
        breadcrumbGroup="需求交付"
        columns={columns}
        dataSource={dataSource}
        filters={[
          { label: '需求标题', name: 'title', type: 'text' },
          { label: '所属产品', name: 'product', type: 'text' },
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
        loading={status === 'loading'}
        notice={formatRemoteRowsError(error ?? productContextError)}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="新增需求"
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
