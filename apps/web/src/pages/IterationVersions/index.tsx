import { DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, message } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ProductContextOption, ProductVersionRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createProductVersion,
  deleteProductVersion,
  fetchDeliveryIterationVersions,
  fetchProductContextOptions,
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

const versionStatusLabels: Record<ProductVersionRecord['status'], { color: string; label: string }> = {
  active: { color: 'blue', label: '开发中' },
  archived: { color: 'default', label: '已归档' },
  planning: { color: 'gold', label: '规划中' },
};

export default function IterationVersionsPage() {
  const [form] = Form.useForm<IterationVersionFormValues>();
  const [editingVersion, setEditingVersion] = useState<ProductVersionRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(fetchDeliveryIterationVersions);
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
      status: values.status,
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

  const columns = useMemo<ProColumns<ProductVersionRecord>[]>(
    () => [
      {
        dataIndex: 'productName',
        title: '所属产品',
      },
      {
        dataIndex: 'code',
        title: '版本编码',
      },
      {
        dataIndex: 'name',
        title: '版本名称',
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) => {
          const statusLabel = versionStatusLabels[row.status];
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
      },
      {
        dataIndex: 'startDate',
        title: '开始时间',
        render: (_, row) => row.startDate ?? '-',
      },
      {
        dataIndex: 'releaseDate',
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
            <Popconfirm okText="删除" onConfirm={() => handleDelete(row)} title={`删除版本 ${row.code}？`}>
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
      <ManagementListPage<ProductVersionRecord>
        breadcrumbGroup="需求交付"
        columns={columns}
        dataSource={dataSource}
        filters={[
          { label: '所属产品', name: 'productName', type: 'text' },
          { label: '版本编码', name: 'code', type: 'text' },
          { label: '版本名称', name: 'name', type: 'text' },
          {
            label: '状态',
            name: 'status',
            options: [
              { label: '规划中', value: 'planning' },
              { label: '开发中', value: 'active' },
              { label: '已归档', value: 'archived' },
            ],
            type: 'select',
          },
        ]}
        loading={status === 'loading'}
        notice={formatRemoteRowsError(error ?? productError)}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="新增迭代版本"
        rowKey="id"
        tableTitle="迭代版本列表"
        title="迭代版本"
      />
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
          <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
            <Select
              options={[
                { label: '规划中', value: 'planning' },
                { label: '开发中', value: 'active' },
                { label: '已归档', value: 'archived' },
              ]}
            />
          </Form.Item>
          <Form.Item label="开始时间" name="start_date">
            <Input placeholder="YYYY-MM-DD" />
          </Form.Item>
          <Form.Item label="计划发布时间" name="release_date">
            <Input placeholder="YYYY-MM-DD" />
          </Form.Item>
          <Form.Item label="目标说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
