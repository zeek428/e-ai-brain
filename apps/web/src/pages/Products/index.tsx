import { DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, message } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ProductRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createManagementProduct,
  deleteManagementProduct,
  fetchManagementProducts,
  updateManagementProduct,
} from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';

type ProductFormValues = {
  code?: string;
  description?: string;
  name: string;
  owner_team?: string;
  status: ProductRecord['status'];
};

export default function ProductsPage() {
  const [form] = Form.useForm<ProductFormValues>();
  const [editingProduct, setEditingProduct] = useState<ProductRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(fetchManagementProducts);

  const openCreateModal = () => {
    setEditingProduct(null);
    form.resetFields();
    form.setFieldsValue({ status: 'active' });
    setIsModalOpen(true);
  };

  const openEditModal = useCallback((row: ProductRecord) => {
    setEditingProduct(row);
    form.setFieldsValue({
      code: row.code,
      name: row.name,
      owner_team: row.ownerTeam === '-' ? undefined : row.ownerTeam,
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
      owner_team: trimText(values.owner_team),
      status: values.status,
    };

    setIsSaving(true);
    try {
      if (editingProduct) {
        await updateManagementProduct(editingProduct.id, payload);
        message.success('产品已更新');
      } else {
        await createManagementProduct(payload);
        message.success('产品已创建');
      }
      setIsModalOpen(false);
      await reload();
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = useCallback(async (row: ProductRecord) => {
    try {
      await deleteManagementProduct(row.id);
      message.success('产品已删除');
      await reload();
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [reload]);

  const columns = useMemo<ProColumns<ProductRecord>[]>(
    () => [
      {
        dataIndex: 'code',
        title: '产品编码',
      },
      {
        dataIndex: 'name',
        title: '产品名称',
      },
      {
        dataIndex: 'ownerTeam',
        title: '负责团队',
      },
      {
        dataIndex: 'version',
        title: '当前版本',
      },
      {
        dataIndex: 'moduleCount',
        title: '模块数',
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) =>
          row.status === 'active' ? (
            <StatusTag color="green" label="启用" />
          ) : (
            <StatusTag color="default" label="停用" />
          ),
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
            <Popconfirm
              okText="删除"
              onConfirm={() => handleDelete(row)}
              title={`删除产品 ${row.code}？`}
            >
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
      <ManagementListPage<ProductRecord>
        breadcrumbGroup="产品资产"
        columns={columns}
        dataSource={dataSource}
        filters={[
          { label: '产品编码', name: 'code', type: 'text' },
          { label: '产品名称', name: 'name', type: 'text' },
          { label: '负责团队', name: 'ownerTeam', type: 'text' },
          {
            label: '状态',
            name: 'status',
            options: [
              { label: '启用', value: 'active' },
              { label: '停用', value: 'inactive' },
            ],
            type: 'select',
          },
        ]}
        loading={status === 'loading'}
        notice={formatRemoteRowsError(error)}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="新增产品"
        rowKey="id"
        tableTitle="产品列表"
        title="产品管理"
      />
      <Modal
        confirmLoading={isSaving}
        destroyOnHidden
        onCancel={() => setIsModalOpen(false)}
        onOk={() => void handleSave()}
        open={isModalOpen}
        title={editingProduct ? '编辑产品' : '新增产品'}
      >
        <Form<ProductFormValues> form={form} layout="vertical">
          <Form.Item label="产品编码" name="code" rules={[{ required: true, message: '请输入产品编码' }]}>
            <Input placeholder="请输入唯一产品编码" />
          </Form.Item>
          <Form.Item label="产品名称" name="name" rules={[{ required: true, message: '请输入产品名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="负责团队" name="owner_team">
            <Input />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea autoSize={{ minRows: 3 }} />
          </Form.Item>
          <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
            <Select
              options={[
                { label: '启用', value: 'active' },
                { label: '停用', value: 'inactive' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
