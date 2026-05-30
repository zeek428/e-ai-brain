import { DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, message } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import { requirementRows, type RequirementRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createManagementRequirement,
  deleteManagementRequirement,
  fetchManagementRequirements,
  updateManagementRequirement,
} from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';

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
  const [editingRequirement, setEditingRequirement] = useState<RequirementRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(requirementRows, fetchManagementRequirements);

  const openCreateModal = () => {
    setEditingRequirement(null);
    form.resetFields();
    form.setFieldsValue({ priority: 'P1' });
    setIsModalOpen(true);
  };

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
      version_id: values.version_id.trim(),
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
      await reload();
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
            <Popconfirm okText="删除" onConfirm={() => handleDelete(row)} title={`删除需求 ${row.id}？`}>
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [handleDelete, openEditModal],
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
        notice={formatRemoteRowsError(error)}
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
          <Form.Item label="产品 ID" name="product_id" rules={[{ required: true, message: '请输入产品 ID' }]}>
            <Input placeholder="例如 product_001" />
          </Form.Item>
          <Form.Item label="版本 ID" name="version_id" rules={[{ required: true, message: '请输入版本 ID' }]}>
            <Input placeholder="例如 version_001" />
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
    </>
  );
}
