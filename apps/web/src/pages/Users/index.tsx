import {
  DeleteOutlined,
  DisconnectOutlined,
  EditOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ManagementListQuery } from '../../components/ManagementListPage';
import type { UserRecord } from '../../data/management';
import { type UserRoleDefinition, toUserRoleOptions } from '../../data/roles';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  type RemoteRowsError,
} from '../../hooks/useRemoteRows';
import {
  createManagementUser,
  deleteManagementUser,
  fetchRoleDefinitions,
  fetchManagementUserList,
  unbindSystemExternalIdentity,
  updateManagementUser,
  type RemoteListPerformance,
} from '../../services/aiBrain';
import type { UserListQuery } from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';

type UserFormValues = {
  display_name: string;
  mobile?: string;
  password?: string;
  roles?: string[];
  status: UserRecord['status'];
  username: string;
};

const userSortFieldMap: Record<string, string> = {
  displayName: 'display_name',
  status: 'status',
  username: 'username',
};

const loginMethodLabels: Record<string, string> = {
  dingtalk: '钉钉',
  password: '账号密码',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildUserListQuery(query: ManagementListQuery): UserListQuery {
  const filters = query.filters;
  return {
    displayName: normalizeFilterText(filters.displayName),
    page: query.page,
    pageSize: query.pageSize,
    role: normalizeFilterText(filters.role),
    sortField: query.sortField ? userSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(filters.status),
    username: normalizeFilterText(filters.username),
  };
}

export default function UsersPage() {
  const [form] = Form.useForm<UserFormValues>();
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isRoleCatalogOpen, setIsRoleCatalogOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [roleDefinitions, setRoleDefinitions] = useState<UserRoleDefinition[]>([]);
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'username',
    sortOrder: 'ascend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    performance?: RemoteListPerformance;
    rows: UserRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const loadRoleDefinitions = useCallback(async () => {
    const definitions = await fetchRoleDefinitions();
    setRoleDefinitions(definitions);
  }, []);

  const roleOptions = useMemo(() => toUserRoleOptions(roleDefinitions), [roleDefinitions]);
  const roleByCode = useMemo(
    () => new Map(roleDefinitions.map((role) => [role.code, role])),
    [roleDefinitions],
  );
  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const definitions = roleDefinitions.length ? roleDefinitions : await fetchRoleDefinitions();
      if (!roleDefinitions.length) {
        setRoleDefinitions(definitions);
      }
      const result = await fetchManagementUserList(definitions, buildUserListQuery(listQuery));
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
  }, [listQuery, roleDefinitions]);

  useEffect(() => {
    void loadRoleDefinitions();
  }, [loadRoleDefinitions]);

  useEffect(() => {
    let isCurrent = true;
    setListState((current) => ({ ...current, status: 'loading' }));
    const load = async () => {
      try {
        const definitions = roleDefinitions.length ? roleDefinitions : await fetchRoleDefinitions();
        if (isCurrent && !roleDefinitions.length) {
          setRoleDefinitions(definitions);
        }
        const result = await fetchManagementUserList(definitions, buildUserListQuery(listQuery));
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
      } catch (loadError: unknown) {
        if (isCurrent) {
          setListState((current) => ({
            ...current,
            error: normalizeRemoteRowsError(loadError),
            rows: [],
            status: 'error',
          }));
        }
      }
    };
    void load();
    return () => {
      isCurrent = false;
    };
  }, [listQuery, roleDefinitions]);

  const openCreateModal = () => {
    setEditingUser(null);
    form.resetFields();
    form.setFieldsValue({
      roles: ['viewer'],
      status: 'active',
    });
    setIsModalOpen(true);
  };

  const openEditModal = useCallback((row: UserRecord) => {
    setEditingUser(row);
    form.setFieldsValue({
      display_name: row.displayName,
      mobile: row.mobile ?? '',
      roles: row.roles,
      status: row.status,
      username: row.username,
    });
    setIsModalOpen(true);
  }, [form]);

  const handleSave = async () => {
    const values = await form.validateFields();
    const roles = values.roles ?? [];
    const payload = {
      display_name: values.display_name.trim(),
      mobile: values.mobile?.trim() ?? '',
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
      void reload();
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

  const handleUnbindDingTalk = useCallback(async (row: UserRecord, force = false) => {
    const identityId = row.dingtalkBinding?.identity_id;
    if (!identityId) {
      return;
    }
    try {
      await unbindSystemExternalIdentity(identityId, force);
      message.success('钉钉账号已解绑');
      await reload();
    } catch (unbindError) {
      const errorCode =
        unbindError instanceof Error
          ? (unbindError as Error & { code?: string }).code
          : undefined;
      if (errorCode === 'DINGTALK_UNBIND_LOGIN_LOCKOUT_RISK' && !force) {
        Modal.confirm({
          content: '该用户未配置本地密码，解绑后可能无法自行登录。确认要以管理员身份强制解绑？',
          okText: '强制解绑',
          okButtonProps: { danger: true },
          onOk: () => handleUnbindDingTalk(row, true),
          title: '存在登录锁定风险',
        });
        return;
      }
      message.error(formatMutationError(unbindError));
    }
  }, [reload]);

  const columns = useMemo<ProColumns<UserRecord>[]>(
    () => [
      {
        dataIndex: 'username',
        sorter: true,
        title: '登录账号',
        width: 220,
      },
      {
        dataIndex: 'displayName',
        sorter: true,
        title: '显示名称',
        width: 180,
      },
      {
        dataIndex: 'mobile',
        title: '手机号',
        width: 150,
        render: (_, row) => row.mobile || '-',
      },
      {
        dataIndex: 'loginMethods',
        title: '登录方式',
        width: 180,
        render: (_, row) => {
          const methods = row.loginMethods.length
            ? row.loginMethods
            : row.localPasswordConfigured
              ? ['password']
              : [];
          return methods.length ? (
            <Space size={[4, 4]} wrap>
              {methods.map((method) => (
                <Tag color={method === 'dingtalk' ? 'blue' : 'green'} key={method}>
                  {loginMethodLabels[method] ?? method}
                </Tag>
              ))}
            </Space>
          ) : (
            <Tag color="red">未配置</Tag>
          );
        },
      },
      {
        dataIndex: ['dingtalkBinding', 'bound'],
        title: '钉钉绑定',
        width: 220,
        render: (_, row) => {
          if (!row.dingtalkBinding?.bound) {
            return <Tag>未绑定</Tag>;
          }
          const corpDisplay =
            row.dingtalkBinding.corp_name ||
            row.dingtalkBinding.corp_id ||
            row.dingtalkBinding.display_name ||
            '已绑定';
          return (
            <Space size={4} wrap>
              <Tag color="blue">已绑定</Tag>
              <span>{corpDisplay}</span>
            </Space>
          );
        },
      },
      {
        dataIndex: 'rolesText',
        title: '角色',
        width: 220,
        render: (_, row) =>
          row.roles.length ? (
            <Space size={[4, 4]} wrap>
              {row.roles.map((role) => (
                <Tag key={role}>{roleByCode.get(role)?.name ?? role}</Tag>
              ))}
            </Space>
          ) : (
            '-'
          ),
      },
      {
        dataIndex: 'status',
        sorter: true,
        title: '状态',
        width: 120,
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
        width: 180,
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
            {row.dingtalkBinding?.bound && row.dingtalkBinding.identity_id ? (
              <Popconfirm
                okText="解绑"
                onConfirm={() => void handleUnbindDingTalk(row)}
                title={`解绑用户 ${row.username} 的钉钉账号？`}
              >
                <Button icon={<DisconnectOutlined />} type="link">
                  解绑钉钉
                </Button>
              </Popconfirm>
            ) : null}
          </Space>
        ),
      },
    ],
    [handleDelete, handleUnbindDingTalk, openEditModal, roleByCode],
  );

  return (
    <>
      <ManagementListPage<UserRecord>
        breadcrumbGroup="系统管理"
        columns={columns}
        dataSource={listState.rows}
        viewStorageKey="system.users"
        filters={[
          { label: '登录账号', name: 'username', type: 'text' },
          { label: '显示名称', name: 'displayName', type: 'text' },
          {
            label: '角色',
            name: 'role',
            options: roleOptions.map((option) => ({
              label: option.label,
              value: option.value,
            })),
            type: 'select',
          },
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
        loading={listState.status === 'loading'}
        notice={formatRemoteRowsError(listState.error)}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="新增用户"
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="id"
        tableTitle="用户列表"
        title="用户管理"
        toolbarActions={[
          <Button
            icon={<SafetyCertificateOutlined />}
            key="roles"
            onClick={() => setIsRoleCatalogOpen(true)}
          >
            角色目录
          </Button>,
        ]}
      />
      <Modal
        destroyOnHidden
        footer={null}
        onCancel={() => setIsRoleCatalogOpen(false)}
        open={isRoleCatalogOpen}
        title="角色目录"
        width={960}
      >
        <Table<UserRoleDefinition>
          columns={[
            {
              dataIndex: 'name',
              title: '角色',
              render: (_, role) => `${role.name} (${role.code})`,
            },
            {
              dataIndex: 'responsibilities',
              title: '职责',
              render: (_, role) => role.responsibilities.join('；'),
            },
            {
              dataIndex: 'business_roles',
              title: '业务角色',
              render: (_, role) => role.business_roles.join('；'),
            },
            {
              dataIndex: 'data_scope',
              title: '数据范围',
            },
            {
              dataIndex: 'decision_scope',
              title: '决策范围',
            },
            {
              dataIndex: 'menu_scope',
              title: '可见入口',
              render: (_, role) => role.menu_scope.join('；'),
            },
            {
              dataIndex: 'limitations',
              title: '限制边界',
              render: (_, role) => role.limitations.join('；'),
            },
            {
              dataIndex: 'permissions',
              title: '权限点',
              render: (_, role) => (
                <Space size={[4, 4]} wrap>
                  {role.permissions.map((permission) => (
                    <Tag key={permission}>{permission}</Tag>
                  ))}
                </Space>
              ),
            },
          ]}
          dataSource={roleDefinitions}
          pagination={false}
          rowKey="code"
          size="small"
        />
      </Modal>
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
          <Form.Item label="手机号" name="mobile">
            <Input autoComplete="tel" />
          </Form.Item>
          {editingUser ? (
            <Form.Item label="认证状态">
              <Space size={[4, 4]} wrap>
                <Tag color={editingUser.localPasswordConfigured ? 'green' : 'default'}>
                  {editingUser.localPasswordConfigured ? '本地密码已配置' : '本地密码未配置'}
                </Tag>
                <Tag color={editingUser.dingtalkBinding?.bound ? 'blue' : 'default'}>
                  {editingUser.dingtalkBinding?.bound ? '钉钉已绑定' : '钉钉未绑定'}
                </Tag>
              </Space>
            </Form.Item>
          ) : null}
          <Form.Item
            label={editingUser ? '重置密码' : '登录密码'}
            name="password"
            rules={editingUser ? [] : [{ required: true, message: '请输入登录密码' }]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item label="角色" name="roles" rules={[{ required: true, message: '请选择角色' }]}>
            <Select
              disabled={roleOptions.length === 0}
              mode="multiple"
              optionFilterProp="label"
              options={roleOptions}
              placeholder="请选择角色"
            />
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
