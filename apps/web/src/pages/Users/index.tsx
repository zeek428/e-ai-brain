import { DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, message } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import { userRows, type UserRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createManagementUser,
  deleteManagementUser,
  fetchManagementUsers,
  updateManagementUser,
} from '../../services/aiBrain';
import { formatMutationError, joinTextList, splitCommaText, trimText } from '../../utils/managementCrud';

type UserFormValues = {
  display_name: string;
  password?: string;
  roles?: string;
  status: UserRecord['status'];
  username: string;
};

export default function UsersPage() {
  const [form] = Form.useForm<UserFormValues>();
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(userRows, fetchManagementUsers);

  const openCreateModal = () => {
    setEditingUser(null);
    form.resetFields();
    form.setFieldsValue({
      roles: 'viewer',
      status: 'active',
    });
    setIsModalOpen(true);
  };

  const openEditModal = useCallback((row: UserRecord) => {
    setEditingUser(row);
    form.setFieldsValue({
      display_name: row.displayName,
      roles: joinTextList(row.roles),
      status: row.status,
      username: row.username,
    });
    setIsModalOpen(true);
  }, [form]);

  const handleSave = async () => {
    const values = await form.validateFields();
    const roles = splitCommaText(values.roles);
    const payload = {
      display_name: values.display_name.trim(),
      password: trimText(values.password),
      roles: roles.length ? roles : ['viewer'],
      status: values.status,
      username: values.username.trim(),
    };

    setIsSaving(true);
    try {
      if (editingUser) {
        await updateManagementUser(editingUser.id, payload);
        message.success('用户已更新');
      } else {
        await createManagementUser(payload);
        message.success('用户已创建');
      }
      setIsModalOpen(false);
      await reload();
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = useCallback(async (row: UserRecord) => {
    try {
      await deleteManagementUser(row.id);
      message.success('用户已删除');
      await reload();
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [reload]);

  const columns = useMemo<ProColumns<UserRecord>[]>(
    () => [
      {
        dataIndex: 'username',
        title: '登录账号',
      },
      {
        dataIndex: 'displayName',
        title: '显示名称',
      },
      {
        dataIndex: 'rolesText',
        title: '角色',
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
            <Popconfirm okText="删除" onConfirm={() => handleDelete(row)} title={`删除用户 ${row.username}？`}>
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
      <ManagementListPage<UserRecord>
        breadcrumbGroup="系统管理"
        columns={columns}
        dataSource={dataSource}
        filters={[
          { label: '登录账号', name: 'username', type: 'text' },
          { label: '显示名称', name: 'displayName', type: 'text' },
          { label: '角色', name: 'rolesText', type: 'text' },
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
        primaryAction="新增用户"
        rowKey="id"
        tableTitle="用户列表"
        title="用户管理"
      />
      <Modal
        confirmLoading={isSaving}
        destroyOnHidden
        onCancel={() => setIsModalOpen(false)}
        onOk={() => void handleSave()}
        open={isModalOpen}
        title={editingUser ? '编辑用户' : '新增用户'}
      >
        <Form<UserFormValues> form={form} layout="vertical">
          <Form.Item label="登录账号" name="username" rules={[{ required: true, message: '请输入登录账号' }]}>
            <Input disabled={Boolean(editingUser)} />
          </Form.Item>
          <Form.Item label="显示名称" name="display_name" rules={[{ required: true, message: '请输入显示名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item
            label={editingUser ? '重置密码' : '登录密码'}
            name="password"
            rules={editingUser ? [] : [{ required: true, message: '请输入登录密码' }]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item label="角色" name="roles">
            <Input placeholder="admin, product_owner, rd_owner" />
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
