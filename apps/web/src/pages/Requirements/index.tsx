import { DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, message } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { RequirementRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createProductVersion,
  approveManagementRequirement,
  createManagementRequirement,
  deleteManagementRequirement,
  fetchProductContextOptions,
  fetchManagementRequirements,
  generateRequirementTask,
  rejectManagementRequirement,
  updateManagementRequirement,
} from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';

const AUTO_VERSION_ID = '__auto_default_version__';

const statusLabels: Record<RequirementRecord['status'], { color: string; label: string }> = {
  approved: { color: 'green', label: '已审批' },
  closed: { color: 'default', label: '已关闭' },
  draft: { color: 'default', label: '草稿' },
  pending_approval: { color: 'gold', label: '待审批' },
  rejected: { color: 'red', label: '已拒绝' },
  task_created: { color: 'blue', label: '已生成任务' },
};

type RequirementFormValues = {
  content: string;
  module_code?: string;
  priority: RequirementRecord['priority'];
  product_id: string;
  title: string;
  version_id: string;
};

export default function RequirementsPage() {
  const [form] = Form.useForm<RequirementFormValues>();
  const [rejectForm] = Form.useForm<{ rejection_reason: string }>();
  const [editingRequirement, setEditingRequirement] = useState<RequirementRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [rejectingRequirement, setRejectingRequirement] = useState<RequirementRecord | null>(null);
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
  } = useRemoteRows(fetchProductContextOptions);
  const selectedProductId = Form.useWatch('product_id', form);
  const selectedProduct = useMemo(
    () => productContexts.find((product) => product.id === selectedProductId),
    [productContexts, selectedProductId],
  );
  const productOptions = useMemo(
    () =>
      productContexts.map((product) => ({
        label: `${product.code} · ${product.name}`,
        value: product.id,
      })),
    [productContexts],
  );
  const resolveDefaultVersionValue = useCallback(
    (productId?: string) => {
      const product = productContexts.find((item) => item.id === productId);
      return product?.versions[0]?.id ?? AUTO_VERSION_ID;
    },
    [productContexts],
  );
  const versionOptions = useMemo(() => {
    if (!selectedProduct) {
      return [];
    }
    if (selectedProduct.versions.length === 0) {
      return [{ label: '自动创建默认版本 v1', value: AUTO_VERSION_ID }];
    }
    return selectedProduct.versions.map((version) => ({
      label: `${version.code} · ${version.name}`,
      value: version.id,
    }));
  }, [selectedProduct]);

  const openCreateModal = () => {
    setEditingRequirement(null);
    form.resetFields();
    const firstProduct = productContexts[0];
    form.setFieldsValue({
      priority: 'P1',
      product_id: firstProduct?.id,
      version_id: firstProduct ? resolveDefaultVersionValue(firstProduct.id) : undefined,
    });
    setIsModalOpen(true);
  };

  const handleProductChange = useCallback((productId: string) => {
    form.setFieldsValue({
      module_code: undefined,
      version_id: resolveDefaultVersionValue(productId),
    });
  }, [form, resolveDefaultVersionValue]);

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
    let versionId = values.version_id;
    const payload = {
      content: values.content.trim(),
      module_code: trimText(values.module_code),
      priority: values.priority,
      product_id: values.product_id.trim(),
      title: values.title.trim(),
      version_id: versionId.trim(),
    };

    setIsSaving(true);
    try {
      if (versionId === AUTO_VERSION_ID) {
        const version = await createProductVersion(values.product_id.trim(), {
          code: 'v1',
          name: 'v1',
          status: 'active',
        });
        versionId = version.id;
        payload.version_id = version.id;
      }
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
            {row.status === 'pending_approval' ? (
              <>
                <Button onClick={() => handleApprove(row)} type="link">
                  审批通过
                </Button>
                <Button danger onClick={() => openRejectModal(row)} type="link">
                  驳回
                </Button>
              </>
            ) : null}
            {row.status === 'approved' ? (
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
              { label: '待审批', value: 'pending_approval' },
              { label: '已审批', value: 'approved' },
              { label: '已拒绝', value: 'rejected' },
              { label: '已生成任务', value: 'task_created' },
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
        tableTitle="需求列表"
        title="需求管理"
      />
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
            extra={selectedProduct?.versions.length === 0 ? '该产品暂无版本，保存时将创建真实默认版本 v1。' : undefined}
            label="目标版本"
            name="version_id"
            rules={[{ required: true, message: '请选择版本' }]}
          >
            <Select
              disabled={!selectedProduct}
              loading={productContextStatus === 'loading'}
              options={versionOptions}
              placeholder="请选择版本"
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
