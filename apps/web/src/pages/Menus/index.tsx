import type { ProColumns } from '@ant-design/pro-components';
import {
  Button,
  Checkbox,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ManagementListQuery } from '../../components/ManagementListPage';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  type RemoteRowsError,
} from '../../hooks/useRemoteRows';
import {
  createSystemMenu,
  deleteSystemMenu,
  fetchSystemMenuList,
  fetchSystemMenus,
  fetchSystemPermissions,
  setSystemMenuStatus,
  updateSystemMenu,
  type MenuListQuery,
  type MenuResourceMutationPayload,
  type MenuResourceRecord,
  type PermissionRecord,
  type RemoteListPerformance,
} from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';

type MenuManagementRow = MenuResourceRecord & {
  parentText: string;
  permissionText: string;
  routeText: string;
  statusText: string;
  typeText: string;
};

type MenuFormValues = {
  code: string;
  icon?: string;
  menu_type: string;
  name: string;
  parent_code?: string;
  path?: string;
  required_permissions?: string[];
  sort_order?: number;
  status: string;
};

const MENU_TYPE_LABELS: Record<string, string> = {
  group: '分组',
  hidden_page: '隐藏页面',
  page: '页面',
};

const MENU_TYPE_OPTIONS = Object.entries(MENU_TYPE_LABELS).map(([value, label]) => ({
  label,
  value,
}));

const STATUS_OPTIONS = [
  { label: '启用', value: 'active' },
  { label: '停用', value: 'inactive' },
];

const { Text } = Typography;

const menuSortFieldMap: Record<string, string> = {
  menu_type: 'menu_type',
  parentText: 'parent_code',
  routeText: 'path',
  statusText: 'status',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildMenuListQuery(query: ManagementListQuery): MenuListQuery {
  const filters = query.filters;
  return {
    menu: normalizeFilterText(filters.menu),
    menuType: normalizeFilterText(filters.menu_type),
    page: query.page,
    pageSize: query.pageSize,
    parent: normalizeFilterText(filters.parent),
    path: normalizeFilterText(filters.path),
    permission: normalizeFilterText(filters.permission),
    sortField: query.sortField ? menuSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(filters.status),
  };
}

function renderPermissionTags(codes: string[]) {
  if (!codes.length) {
    return <Text type="secondary">无</Text>;
  }
  return (
    <Space size={[4, 4]} wrap>
      {codes.slice(0, 3).map((code) => (
        <Tag key={code}>{code}</Tag>
      ))}
      {codes.length > 3 ? <Tag>+{codes.length - 3}</Tag> : null}
    </Space>
  );
}

function mapMenuRow(menu: MenuResourceRecord, menuNameByCode: Map<string, string>): MenuManagementRow {
  const requiredPermissions = menu.required_permissions ?? [];
  return {
    ...menu,
    parentText: menu.parent_code
      ? `${menuNameByCode.get(menu.parent_code) ?? menu.parent_code} (${menu.parent_code})`
      : '根菜单',
    permissionText: requiredPermissions.join(', '),
    routeText: menu.path ?? '',
    statusText: menu.status === 'inactive' ? '停用' : '启用',
    typeText: MENU_TYPE_LABELS[menu.menu_type ?? 'page'] ?? menu.menu_type ?? '页面',
  };
}

function buildMenuPayload(values: MenuFormValues): MenuResourceMutationPayload & { code: string; name: string } {
  return {
    code: values.code.trim(),
    icon: trimText(values.icon),
    menu_type: values.menu_type,
    name: values.name.trim(),
    parent_code: trimText(values.parent_code),
    path: trimText(values.path),
    required_permissions: values.required_permissions ?? [],
    sort_order: Number(values.sort_order ?? 100),
    status: values.status,
  };
}

export default function MenusPage() {
  const [form] = Form.useForm<MenuFormValues>();
  const [editingMenu, setEditingMenu] = useState<MenuManagementRow>();
  const [formOpen, setFormOpen] = useState(false);
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'sort_order',
    sortOrder: 'ascend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    performance?: RemoteListPerformance;
    rows: MenuResourceRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const [menuCatalog, setMenuCatalog] = useState<MenuResourceRecord[]>([]);
  const [notice, setNotice] = useState<string>();
  const [permissions, setPermissions] = useState<PermissionRecord[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [supportLoading, setSupportLoading] = useState(false);

  const reloadSupportData = useCallback(async () => {
    setSupportLoading(true);
    setNotice(undefined);
    try {
      const [menuRows, permissionRows] = await Promise.all([fetchSystemMenus(), fetchSystemPermissions()]);
      setMenuCatalog(menuRows);
      setPermissions(permissionRows);
    } catch (loadError: unknown) {
      setMenuCatalog([]);
      setNotice(formatMutationError(loadError));
    } finally {
      setSupportLoading(false);
    }
  }, []);

  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchSystemMenuList(buildMenuListQuery(listQuery));
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

  useEffect(() => {
    void reloadSupportData();
  }, [reloadSupportData]);

  useEffect(() => {
    let isCurrent = true;
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchSystemMenuList(buildMenuListQuery(listQuery))
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

  const menuNameByCode = useMemo(
    () => new Map(menuCatalog.map((menu) => [menu.code, menu.name])),
    [menuCatalog],
  );
  const rows = useMemo(
    () => listState.rows.map((menu) => mapMenuRow(menu, menuNameByCode)),
    [listState.rows, menuNameByCode],
  );

  const parentOptions = useMemo(
    () =>
      menuCatalog
        .filter((menu) => !editingMenu || menu.code !== editingMenu.code)
        .map((menu) => ({
          label: `${menu.name} (${menu.code})`,
          value: menu.code,
        })),
    [editingMenu, menuCatalog],
  );

  const permissionOptions = useMemo(
    () =>
      permissions
        .filter((permission) => permission.status !== 'inactive')
        .map((permission) => ({
          label: `${permission.name} (${permission.code})`,
          value: permission.code,
        })),
    [permissions],
  );

  const openCreate = useCallback(() => {
    setEditingMenu(undefined);
    form.resetFields();
    form.setFieldsValue({
      menu_type: 'page',
      required_permissions: [],
      sort_order: 100,
      status: 'active',
    });
    setFormOpen(true);
  }, [form]);

  const openEdit = useCallback(
    (row: MenuManagementRow) => {
      setEditingMenu(row);
      form.setFieldsValue({
        code: row.code,
        icon: row.icon,
        menu_type: row.menu_type ?? 'page',
        name: row.name,
        parent_code: row.parent_code ?? undefined,
        path: row.path ?? undefined,
        required_permissions: row.required_permissions ?? [],
        sort_order: row.sort_order,
        status: row.status ?? 'active',
      });
      setFormOpen(true);
    },
    [form],
  );

  const submitForm = async () => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      const payload = buildMenuPayload(values);
      if (editingMenu) {
        const { code, ...updates } = payload;
        void code;
        await updateSystemMenu(editingMenu.code, updates);
        message.success('菜单已更新');
      } else {
        await createSystemMenu(payload);
        message.success('菜单已新增');
      }
      setFormOpen(false);
      setEditingMenu(undefined);
      await Promise.all([reload(), reloadSupportData()]);
    } catch (saveError: unknown) {
      message.error(formatMutationError(saveError));
    } finally {
      setSubmitting(false);
    }
  };

  const toggleStatus = useCallback(async (row: MenuManagementRow) => {
    setSubmitting(true);
    try {
      const nextStatus = row.status === 'inactive' ? 'active' : 'inactive';
      await setSystemMenuStatus(row.code, nextStatus);
      message.success(nextStatus === 'active' ? '菜单已启用' : '菜单已停用');
      await Promise.all([reload(), reloadSupportData()]);
    } catch (statusError: unknown) {
      message.error(formatMutationError(statusError));
    } finally {
      setSubmitting(false);
    }
  }, [reload, reloadSupportData]);

  const removeMenu = useCallback(async (row: MenuManagementRow) => {
    setSubmitting(true);
    try {
      await deleteSystemMenu(row.code);
      message.success('菜单已删除');
      await Promise.all([reload(), reloadSupportData()]);
    } catch (deleteError: unknown) {
      message.error(formatMutationError(deleteError));
    } finally {
      setSubmitting(false);
    }
  }, [reload, reloadSupportData]);

  const columns = useMemo<ProColumns<MenuManagementRow>[]>(
    () => [
      {
        dataIndex: 'name',
        fixed: 'left',
        sorter: true,
        title: '菜单',
        width: 220,
        render: (_, row) => (
          <Space orientation="vertical" size={2}>
            <Text strong>{row.name}</Text>
            <Text type="secondary">{row.code}</Text>
          </Space>
        ),
      },
      {
        dataIndex: 'typeText',
        sorter: true,
        title: '类型',
        width: 120,
      },
      {
        dataIndex: 'parentText',
        sorter: true,
        title: '父级菜单',
        width: 180,
      },
      {
        dataIndex: 'routeText',
        sorter: true,
        title: '路由路径',
        width: 180,
        render: (_, row) => row.path || <Text type="secondary">无</Text>,
      },
      {
        dataIndex: 'permissionText',
        title: '访问权限点',
        width: 260,
        render: (_, row) => renderPermissionTags(row.required_permissions ?? []),
      },
      {
        dataIndex: 'sort_order',
        sorter: true,
        title: '排序',
        width: 100,
      },
      {
        dataIndex: 'statusText',
        sorter: true,
        title: '状态',
        width: 110,
        render: (_, row) =>
          row.status === 'inactive' ? (
            <StatusTag color="default" label="停用" />
          ) : (
            <StatusTag color="green" label="启用" />
          ),
      },
      {
        fixed: 'right',
        title: '操作',
        valueType: 'option',
        width: 240,
        render: (_, row) => (
          <Space size={0} wrap>
            <Button onClick={() => openEdit(row)} type="link">
              编辑
            </Button>
            <Button disabled={submitting} onClick={() => void toggleStatus(row)} type="link">
              {row.status === 'inactive' ? '启用' : '停用'}
            </Button>
            <Popconfirm
              disabled={row.is_system}
              okText="删除"
              onConfirm={() => void removeMenu(row)}
              title="确认删除该菜单？"
            >
              <Button danger disabled={row.is_system || submitting} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [openEdit, removeMenu, submitting, toggleStatus],
  );

  return (
    <>
      <ManagementListPage<MenuManagementRow>
        breadcrumbGroup="系统管理"
        columns={columns}
        dataSource={rows}
        viewStorageKey="system.menus"
        filters={[
          { label: '菜单', name: 'menu', type: 'text' },
          { label: '父级菜单', name: 'parent', type: 'text' },
          { label: '路由路径', name: 'path', type: 'text' },
          { label: '权限点', name: 'permission', type: 'text' },
          {
            label: '类型',
            name: 'menu_type',
            options: MENU_TYPE_OPTIONS,
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
        loading={listState.status === 'loading' || supportLoading}
        notice={notice ?? formatRemoteRowsError(listState.error)}
        onPrimaryAction={openCreate}
        onReload={() => {
          void reload();
          void reloadSupportData();
        }}
        primaryAction="新增菜单"
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="code"
        tableLayout="fixed"
        tableTitle="菜单资源"
        title="菜单管理"
      />
      <Modal
        confirmLoading={submitting}
        destroyOnHidden
        okText="保存"
        onCancel={() => setFormOpen(false)}
        onOk={() => void submitForm()}
        open={formOpen}
        title={editingMenu ? `编辑菜单 · ${editingMenu.name}` : '新增菜单'}
      >
        <Form<MenuFormValues>
          form={form}
          layout="vertical"
          preserve={false}
          requiredMark="optional"
        >
          <Form.Item
            label="菜单编码"
            name="code"
            rules={[{ required: true, message: '请输入菜单编码' }]}
          >
            <Input disabled={Boolean(editingMenu)} placeholder="system.help" />
          </Form.Item>
          <Form.Item
            label="菜单名称"
            name="name"
            rules={[{ required: true, message: '请输入菜单名称' }]}
          >
            <Input placeholder="系统帮助" />
          </Form.Item>
          <Form.Item
            label="菜单类型"
            name="menu_type"
            rules={[{ required: true, message: '请选择菜单类型' }]}
          >
            <Select options={MENU_TYPE_OPTIONS} />
          </Form.Item>
          <Form.Item label="父级菜单" name="parent_code">
            <Select allowClear options={parentOptions} placeholder="请选择父级菜单，可留空" showSearch />
          </Form.Item>
          <Form.Item label="路由路径" name="path">
            <Input placeholder="/system/help" />
          </Form.Item>
          <Form.Item label="图标" name="icon">
            <Input aria-label="图标" placeholder="QuestionCircleOutlined" />
          </Form.Item>
          <Form.Item
            label="排序号"
            name="sort_order"
            rules={[{ required: true, message: '请输入排序号' }]}
          >
            <InputNumber min={0} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            label="状态"
            name="status"
            rules={[{ required: true, message: '请选择状态' }]}
          >
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item label="访问权限点" name="required_permissions">
            <Checkbox.Group options={permissionOptions} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
