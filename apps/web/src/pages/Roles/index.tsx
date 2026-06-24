import type { ProColumns } from '@ant-design/pro-components';
import {
  Button,
  Checkbox,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ManagementListQuery } from '../../components/ManagementListPage';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  type RemoteRowsError,
} from '../../hooks/useRemoteRows';
import {
  copySystemRole,
  createSystemRole,
  fetchSystemPermissionMatrix,
  fetchSystemPermissionDiagnostics,
  fetchSystemRoleList,
  setSystemRoleStatus,
  updateSystemRole,
  updateSystemRoleMenus,
  updateSystemRolePermissions,
  updateSystemRoleScopes,
  type MenuResourceRecord,
  type PermissionRecord,
  type RbacPolicyMatrix,
  type RbacPolicyMatrixRow,
  type RoleListQuery,
  type ScopeGrant,
  type SystemRoleRecord,
  type UserPermissionDiagnostic,
  type UserPermissionDiagnosticCheck,
} from '../../services/aiBrain';

type RoleManagementRow = SystemRoleRecord & {
  assignableText: string;
  businessRoleText: string;
  categoryText: string;
  limitationText: string;
  menuScopeText: string;
  permissionText: string;
  roleLabel: string;
  responsibilityText: string;
  statusText: string;
};

type RoleFormValues = {
  category: string;
  code: string;
  description?: string;
  is_assignable?: boolean;
  name: string;
  sort_order?: number;
};

type PermissionDiagnosticFormValues = {
  path?: string;
  permissionCode?: string;
  scopeId?: string;
  scopeType?: string;
  userId?: string;
};

type GrantModal =
  | { role: RoleManagementRow; type: 'grants' | 'scopes' }
  | undefined;

const CATEGORY_LABELS: Record<string, string> = {
  delivery: '交付角色',
  knowledge: '知识角色',
  readonly: '只读角色',
  review: '评审角色',
  system: '系统角色',
  workspace: '工作台角色',
};
const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ label, value }));
const roleSortFieldMap: Record<string, string> = {
  categoryText: 'category',
  roleLabel: 'sort_order',
  statusText: 'status',
};

const { Paragraph, Text } = Typography;

function renderTagList(items: string[], maxVisible = items.length) {
  const visibleItems = items.slice(0, maxVisible);
  return (
    <Space size={[4, 4]} wrap>
      {visibleItems.map((item) => (
        <Tag key={item}>{item}</Tag>
      ))}
      {items.length > visibleItems.length ? <Tag>+{items.length - visibleItems.length}</Tag> : null}
    </Space>
  );
}

function renderRoleScopeSummary(row: RoleManagementRow) {
  return (
    <Space orientation="vertical" size={4}>
      <Space size={[4, 4]} wrap>
        <Tag>{row.responsibilities.length} 项职责</Tag>
        <Tag>{row.limitations.length} 条边界</Tag>
      </Space>
      <Text type="secondary">
        {row.data_scope ? '已配置数据范围' : '未配置数据范围'} ·{' '}
        {row.decision_scope ? '已配置决策范围' : '未配置决策范围'}
      </Text>
    </Space>
  );
}

function renderCountSummary(count: number, unit: string) {
  return <Tag color={count > 0 ? 'blue' : 'default'}>{`${count} ${unit}`}</Tag>;
}

function renderCompactCodes(codes: string[], maxVisible = 3) {
  if (!codes.length) {
    return <Text type="secondary">-</Text>;
  }
  const visibleCodes = codes.slice(0, maxVisible);
  return (
    <Space size={[4, 4]} wrap>
      {visibleCodes.map((code) => (
        <Tag key={code}>{code}</Tag>
      ))}
      {codes.length > visibleCodes.length ? <Tag>+{codes.length - visibleCodes.length}</Tag> : null}
    </Space>
  );
}

function matrixColumns(): ColumnsType<RbacPolicyMatrixRow> {
  return [
    {
      dataIndex: 'role_name',
      fixed: 'left',
      render: (_, row) => (
        <Space orientation="vertical" size={2}>
          <Text strong>{row.role_name}</Text>
          <Text type="secondary">{row.role_code}</Text>
        </Space>
      ),
      title: '角色',
      width: 180,
    },
    {
      dataIndex: 'permission_count',
      render: (_, row) => (
        <Space size={[4, 4]} wrap>
          <Tag color="blue">{row.permission_count} 权限点</Tag>
          {row.high_risk_permission_count > 0 ? (
            <Tag color="red">{row.high_risk_permission_count} 高风险</Tag>
          ) : null}
        </Space>
      ),
      title: '权限',
      width: 170,
    },
    {
      dataIndex: 'menu_count',
      render: (_, row) => <Tag color={row.menu_count ? 'cyan' : 'default'}>{row.menu_count} 菜单</Tag>,
      title: '菜单',
      width: 120,
    },
    {
      dataIndex: 'missing_menu_permission_codes',
      render: (_, row) =>
        row.missing_menu_permission_codes.length ? (
          renderCompactCodes(row.missing_menu_permission_codes)
        ) : (
          <StatusTag color="green" label="已对齐" />
        ),
      title: '菜单权限缺口',
      width: 240,
    },
    {
      dataIndex: 'scope_summary',
      ellipsis: true,
      title: '数据范围',
      width: 180,
    },
    {
      dataIndex: 'diagnostics',
      render: (_, row) =>
        row.diagnostics.length ? (
          <Space size={[4, 4]} wrap>
            {row.diagnostics.map((item) => (
              <Tag color={item.level === 'risk' ? 'red' : 'gold'} key={item.code}>
                {item.message}
              </Tag>
            ))}
          </Space>
        ) : (
          <StatusTag color="green" label="正常" />
        ),
      title: '诊断',
      width: 220,
    },
  ];
}

function diagnosticStatusLabel(status: string) {
  return status === 'allowed' ? '通过' : '阻断';
}

function diagnosticStatusColor(status: string) {
  return status === 'allowed' ? 'green' : 'red';
}

function renderDiagnosticReasons(reasons: string[]) {
  if (!reasons.length) {
    return <Text type="secondary">-</Text>;
  }
  return (
    <Space size={[4, 4]} wrap>
      {reasons.map((reason) => (
        <Tag key={reason}>{reason}</Tag>
      ))}
    </Space>
  );
}

function diagnosticCheckColumns(): ColumnsType<UserPermissionDiagnosticCheck> {
  return [
    {
      dataIndex: 'code',
      render: (_, row) => (
        <Space orientation="vertical" size={2}>
          <Text strong>{row.code}</Text>
          {row.target ? <Text type="secondary">{row.target}</Text> : null}
        </Space>
      ),
      title: '检查项',
      width: 180,
    },
    {
      dataIndex: 'status',
      render: (_, row) => (
        <StatusTag color={diagnosticStatusColor(row.status)} label={diagnosticStatusLabel(row.status)} />
      ),
      title: '状态',
      width: 100,
    },
    {
      dataIndex: 'message',
      render: (_, row) => (
        <Space orientation="vertical" size={4}>
          <Text>{row.message}</Text>
          {row.missing_permission_codes?.length ? (
            <Text type="secondary">缺少：{row.missing_permission_codes.join(', ')}</Text>
          ) : null}
          {row.granted_by_roles?.length ? (
            <Text type="secondary">
              来源角色：{row.granted_by_roles.map((role) => role.role_name || role.role_code).join('、')}
            </Text>
          ) : null}
        </Space>
      ),
      title: '说明',
    },
  ];
}

function buildColumns({
  configureGrant,
  copyRole,
  editRole,
  openDetail,
  toggleStatus,
}: {
  configureGrant: (row: RoleManagementRow, type: 'grants' | 'scopes') => void;
  copyRole: (row: RoleManagementRow) => void;
  editRole: (row: RoleManagementRow) => void;
  openDetail: (row: RoleManagementRow) => void;
  toggleStatus: (row: RoleManagementRow) => void;
}): ProColumns<RoleManagementRow>[] {
  return [
    {
      dataIndex: 'roleLabel',
      fixed: 'left',
      title: '角色',
      width: 200,
      render: (_, row) => (
        <Space orientation="vertical" size={2}>
          <Text strong>{row.name}</Text>
          <Text type="secondary">{row.code}</Text>
          <StatusTag color="default" label={row.categoryText} />
        </Space>
      ),
    },
    {
      dataIndex: 'businessRoleText',
      title: '业务角色',
      width: 150,
      render: (_, row) => renderTagList(row.business_roles, 2),
    },
    {
      dataIndex: 'responsibilityText',
      title: '职责与范围',
      width: 220,
      render: (_, row) => renderRoleScopeSummary(row),
    },
    {
      dataIndex: 'menuScopeText',
      title: '可见入口',
      width: 120,
      render: (_, row) => renderCountSummary(row.menu_scope.length, '个入口'),
    },
    {
      dataIndex: 'permissionText',
      title: '权限点',
      width: 120,
      render: (_, row) => renderCountSummary(row.permissions.length, '个权限点'),
    },
    {
      dataIndex: 'statusText',
      title: '状态',
      width: 120,
      render: (_, row) => (
        <Space orientation="vertical" size={4}>
          {row.status === 'active' ? (
            <StatusTag color="green" label="启用" />
          ) : (
            <StatusTag color="default" label="停用" />
          )}
          {row.is_assignable ? (
            <StatusTag color="green" label="可分配" />
          ) : (
            <StatusTag color="default" label="不可分配" />
          )}
        </Space>
      ),
    },
    {
      fixed: 'right',
      title: '操作',
      valueType: 'option',
      width: 280,
      render: (_, row) => (
        <Space size={0} wrap>
          <Button onClick={() => openDetail(row)} type="link">
            详情
          </Button>
          <Button onClick={() => editRole(row)} type="link">
            编辑
          </Button>
          <Button onClick={() => copyRole(row)} type="link">
            复制
          </Button>
          <Button onClick={() => configureGrant(row, 'grants')} type="link">
            角色配置
          </Button>
          <Button onClick={() => configureGrant(row, 'scopes')} type="link">
            范围
          </Button>
          <Button disabled={row.is_system && row.status === 'active'} onClick={() => toggleStatus(row)} type="link">
            {row.status === 'active' ? '停用' : '启用'}
          </Button>
        </Space>
      ),
    },
  ];
}

function mapRoleRow(role: SystemRoleRecord): RoleManagementRow {
  return {
    ...role,
    assignableText: role.is_assignable ? '可分配' : '不可分配',
    businessRoleText: role.business_roles.join(', '),
    categoryText: CATEGORY_LABELS[role.category] ?? role.category,
    limitationText: role.limitations.join('；'),
    menuScopeText: role.menu_codes.join(', '),
    permissionText: role.permission_codes.join(', '),
    responsibilityText: role.responsibilities.join('；'),
    roleLabel: `${role.name} (${role.code})`,
    statusText: role.status === 'active' ? '启用' : '停用',
  };
}

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildRoleListQuery(query: ManagementListQuery): RoleListQuery {
  const filters = query.filters;
  return {
    businessRole: normalizeFilterText(filters.businessRoleText),
    category: normalizeFilterText(filters.category),
    menuScope: normalizeFilterText(filters.menuScopeText),
    page: query.page,
    pageSize: query.pageSize,
    permission: normalizeFilterText(filters.permissionText),
    role: normalizeFilterText(filters.roleLabel),
    sortField: query.sortField ? roleSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(filters.status),
  };
}

function toggleArrayValue(values: string[] | undefined, value: string, checked: boolean) {
  const nextValues = new Set(values ?? []);
  if (checked) {
    nextValues.add(value);
  } else {
    nextValues.delete(value);
  }
  return [...nextValues];
}

function getMenuPermissionCodes(menu: MenuResourceRecord, permissions: PermissionRecord[]) {
  const activePermissions = permissions.filter((permission) => permission.status !== 'inactive');
  const requiredCodes = new Set(menu.required_permissions ?? []);
  const prefix = `${menu.code}.`;
  const prefixMatches = activePermissions
    .filter((permission) => permission.code.startsWith(prefix))
    .map((permission) => permission.code);

  if (prefixMatches.length > 0) {
    return [...new Set([...requiredCodes, ...prefixMatches])];
  }

  const requiredCategories = new Set(
    activePermissions
      .filter((permission) => requiredCodes.has(permission.code))
      .map((permission) => permission.category)
      .filter(Boolean),
  );
  const categoryMatches = activePermissions
    .filter((permission) => permission.category && requiredCategories.has(permission.category))
    .map((permission) => permission.code);

  return [...new Set([...requiredCodes, ...categoryMatches])];
}

export default function RolesPage() {
  const [detailRole, setDetailRole] = useState<RoleManagementRow>();
  const [editingRole, setEditingRole] = useState<RoleManagementRow>();
  const [grantModal, setGrantModal] = useState<GrantModal>();
  const [roleFormOpen, setRoleFormOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [permissions, setPermissions] = useState<PermissionRecord[]>([]);
  const [menus, setMenus] = useState<MenuResourceRecord[]>([]);
  const [policyMatrix, setPolicyMatrix] = useState<RbacPolicyMatrix>();
  const [policyMatrixError, setPolicyMatrixError] = useState<RemoteRowsError>();
  const [policyMatrixLoading, setPolicyMatrixLoading] = useState(false);
  const [permissionDiagnosticResult, setPermissionDiagnosticResult] = useState<UserPermissionDiagnostic>();
  const [permissionDiagnosticError, setPermissionDiagnosticError] = useState<RemoteRowsError>();
  const [permissionDiagnosticLoading, setPermissionDiagnosticLoading] = useState(false);
  const [roleForm] = Form.useForm<RoleFormValues>();
  const [permissionDiagnosticForm] = Form.useForm<PermissionDiagnosticFormValues>();
  const [grantForm] = Form.useForm<{
    menuCodes?: string[];
    permissionCodes?: string[];
    scopes?: ScopeGrant[];
  }>();
  const watchedGrantMenuCodes = Form.useWatch('menuCodes', grantForm);
  const watchedGrantPermissionCodes = Form.useWatch('permissionCodes', grantForm);
  const selectedGrantMenuCodes = useMemo(() => watchedGrantMenuCodes ?? [], [watchedGrantMenuCodes]);
  const selectedGrantPermissionCodes = useMemo(
    () => watchedGrantPermissionCodes ?? [],
    [watchedGrantPermissionCodes],
  );
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'roleLabel',
    sortOrder: 'ascend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    rows: RoleManagementRow[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const loadPolicyMatrix = useCallback(async () => {
    setPolicyMatrixLoading(true);
    try {
      const matrix = await fetchSystemPermissionMatrix();
      setPolicyMatrix(matrix);
      setPolicyMatrixError(undefined);
      setPermissions(matrix.permissions);
      setMenus(matrix.menus);
    } catch (loadError: unknown) {
      setPolicyMatrix(undefined);
      setPolicyMatrixError(normalizeRemoteRowsError(loadError));
      setPermissions([]);
      setMenus([]);
    } finally {
      setPolicyMatrixLoading(false);
    }
  }, []);
  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchSystemRoleList(buildRoleListQuery(listQuery));
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        rows: result.rows.map(mapRoleRow),
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
    fetchSystemRoleList(buildRoleListQuery(listQuery))
      .then((result) => {
        if (isCurrent) {
          setListState({
            page: result.page,
            pageSize: result.pageSize,
            rows: result.rows.map(mapRoleRow),
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
  useEffect(() => {
    void loadPolicyMatrix();
  }, [loadPolicyMatrix]);

  const runPermissionDiagnostic = useCallback(async () => {
    const values = await permissionDiagnosticForm.validateFields();
    setPermissionDiagnosticLoading(true);
    try {
      const result = await fetchSystemPermissionDiagnostics({
        path: normalizeFilterText(values.path),
        permissionCode: normalizeFilterText(values.permissionCode),
        scopeId: normalizeFilterText(values.scopeId),
        scopeType: normalizeFilterText(values.scopeType),
        userId: normalizeFilterText(values.userId) ?? '',
      });
      setPermissionDiagnosticResult(result);
      setPermissionDiagnosticError(undefined);
    } catch (loadError: unknown) {
      setPermissionDiagnosticResult(undefined);
      setPermissionDiagnosticError(normalizeRemoteRowsError(loadError));
    } finally {
      setPermissionDiagnosticLoading(false);
    }
  }, [permissionDiagnosticForm]);

  const openCreateRole = useCallback(() => {
    setEditingRole(undefined);
    roleForm.resetFields();
    roleForm.setFieldsValue({ category: 'workspace', is_assignable: true });
    setRoleFormOpen(true);
  }, [roleForm]);
  const openEditRole = useCallback((row: RoleManagementRow) => {
    setEditingRole(row);
    roleForm.setFieldsValue({
      category: row.category,
      code: row.code,
      description: row.description,
      is_assignable: row.is_assignable,
      name: row.name,
      sort_order: row.sort_order,
    });
    setRoleFormOpen(true);
  }, [roleForm]);
  const openGrantModal = useCallback((row: RoleManagementRow, type: 'grants' | 'scopes') => {
    setGrantModal({ role: row, type });
    grantForm.setFieldsValue({
      menuCodes: row.menu_codes,
      permissionCodes: row.permission_codes,
      scopes: row.scopes.length
        ? row.scopes
        : [{ access_level: 'read', scope_id: '', scope_type: 'product' }],
    });
  }, [grantForm]);
  const submitRoleForm = async () => {
    const values = await roleForm.validateFields();
    setSubmitting(true);
    try {
      if (editingRole) {
        await updateSystemRole(editingRole.id, values);
        message.success('角色已更新');
      } else {
        await createSystemRole(values);
        message.success('角色已创建');
      }
      setRoleFormOpen(false);
      setEditingRole(undefined);
      await reload();
      await loadPolicyMatrix();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '角色保存失败');
    } finally {
      setSubmitting(false);
    }
  };
  const submitGrantForm = async () => {
    if (!grantModal) {
      return;
    }
    const values = await grantForm.validateFields();
    setSubmitting(true);
    try {
      if (grantModal.type === 'grants') {
        await updateSystemRoleMenus(grantModal.role.id, values.menuCodes ?? []);
        await updateSystemRolePermissions(grantModal.role.id, values.permissionCodes ?? []);
      } else {
        await updateSystemRoleScopes(
          grantModal.role.id,
          (values.scopes ?? []).filter((scope) => scope.scope_type && scope.scope_id),
        );
      }
      message.success('授权配置已更新');
      setGrantModal(undefined);
      await reload();
      await loadPolicyMatrix();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '授权配置保存失败');
    } finally {
      setSubmitting(false);
    }
  };
  const toggleRoleStatus = useCallback(async (row: RoleManagementRow) => {
    setSubmitting(true);
    try {
      await setSystemRoleStatus(row.id, row.status === 'active' ? 'inactive' : 'active');
      message.success(row.status === 'active' ? '角色已停用' : '角色已启用');
      await reload();
      await loadPolicyMatrix();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '角色状态更新失败');
    } finally {
      setSubmitting(false);
    }
  }, [loadPolicyMatrix, reload]);
  const copyRole = useCallback(
    (row: RoleManagementRow) => {
      Modal.confirm({
        content: `将复制 ${row.name} 的权限、菜单和范围配置。`,
        onOk: async () => {
          const suffix = new Date().getTime().toString().slice(-6);
          try {
            await copySystemRole(row.id, {
              code: `${row.code}_copy_${suffix}`,
              description: row.description,
              name: `${row.name} 副本`,
            });
            message.success('角色已复制');
            await reload();
            await loadPolicyMatrix();
          } catch (error) {
            message.error(error instanceof Error ? error.message : '角色复制失败');
          }
        },
        title: '复制角色',
      });
    },
    [loadPolicyMatrix, reload],
  );
  const columns = useMemo(
    () =>
      buildColumns({
        configureGrant: openGrantModal,
        copyRole,
        editRole: openEditRole,
        openDetail: setDetailRole,
        toggleStatus: toggleRoleStatus,
      }),
    [copyRole, openEditRole, openGrantModal, toggleRoleStatus],
  );
  const policyMatrixColumns = useMemo(() => matrixColumns(), []);
  const permissionDiagnosticColumns = useMemo(() => diagnosticCheckColumns(), []);
  const policyMatrixPanel = useMemo(() => {
    const summary = policyMatrix?.summary;
    return (
      <section className="role-policy-matrix" aria-label="权限审计矩阵">
        <div className="role-policy-matrix-header">
          <Space orientation="vertical" size={4}>
            <Text strong>权限审计矩阵</Text>
            <Text type="secondary">
              按角色汇总权限点、菜单入口、数据范围和授权缺口，帮助排查入口可见但接口无权等问题。
            </Text>
          </Space>
          <Button loading={policyMatrixLoading} onClick={() => void loadPolicyMatrix()}>
            刷新矩阵
          </Button>
        </div>
        {summary ? (
          <Space className="role-policy-matrix-summary" size={[8, 8]} wrap>
            <Tag color="blue">{summary.role_count} 个角色</Tag>
            <Tag color="cyan">{summary.permission_count} 个权限点</Tag>
            <Tag color="geekblue">{summary.menu_count} 个菜单</Tag>
            <Tag color={summary.roles_with_menu_permission_gaps > 0 ? 'gold' : 'green'}>
              {summary.roles_with_menu_permission_gaps} 个菜单权限缺口
            </Tag>
            <Tag color={summary.roles_with_high_risk_permissions > 0 ? 'red' : 'green'}>
              {summary.roles_with_high_risk_permissions} 个高风险角色
            </Tag>
            <Tag>{summary.scope_grant_count} 条范围授权</Tag>
          </Space>
        ) : null}
        {policyMatrixError ? (
          <Text className="role-policy-matrix-error" type="danger">
            {formatRemoteRowsError(policyMatrixError)}
          </Text>
        ) : null}
        <Table<RbacPolicyMatrixRow>
          columns={policyMatrixColumns}
          dataSource={policyMatrix?.rows ?? []}
          loading={policyMatrixLoading}
          pagination={false}
          rowKey="role_code"
          scroll={{ x: 1110 }}
          size="small"
          tableLayout="fixed"
        />
      </section>
    );
  }, [
    loadPolicyMatrix,
    policyMatrix?.rows,
    policyMatrix?.summary,
    policyMatrixColumns,
    policyMatrixError,
    policyMatrixLoading,
  ]);
  const activeMenus = useMemo(
    () =>
      menus
        .filter((menu) => menu.status !== 'inactive' && menu.menu_type !== 'hidden_page')
        .sort((left, right) => (left.sort_order ?? 0) - (right.sort_order ?? 0)),
    [menus],
  );
  const permissionByCode = useMemo(
    () => new Map(permissions.map((permission) => [permission.code, permission])),
    [permissions],
  );
  const menuPermissionCodesByMenu = useMemo(() => {
    const entries = activeMenus.map((menu) => [menu.code, getMenuPermissionCodes(menu, permissions)] as const);
    return new Map(entries);
  }, [activeMenus, permissions]);
  const mappedPermissionCodes = useMemo(
    () => new Set([...menuPermissionCodesByMenu.values()].flat()),
    [menuPermissionCodesByMenu],
  );
  const otherPermissions = useMemo(
    () =>
      permissions
        .filter((permission) => permission.status !== 'inactive' && !mappedPermissionCodes.has(permission.code))
        .sort((left, right) => left.code.localeCompare(right.code)),
    [mappedPermissionCodes, permissions],
  );
  const permissionDiagnosticPanel = useMemo(
    () => (
      <section className="role-policy-matrix role-permission-diagnostic" aria-label="用户权限诊断">
        <div className="role-policy-matrix-header">
          <Space orientation="vertical" size={4}>
            <Text strong>用户权限诊断</Text>
            <Text type="secondary">
              输入用户和目标入口、权限点或数据范围，解释当前账号为什么能访问或被阻断。
            </Text>
          </Space>
        </div>
        <Form<PermissionDiagnosticFormValues>
          className="role-permission-diagnostic-form"
          form={permissionDiagnosticForm}
          layout="vertical"
          onFinish={() => void runPermissionDiagnostic()}
        >
          <Form.Item
            label="诊断用户 ID"
            name="userId"
            rules={[{ required: true, message: '请输入用户 ID' }]}
          >
            <Input placeholder="user_admin / user_xxx" />
          </Form.Item>
          <Form.Item label="菜单路径" name="path">
            <Input placeholder="/system/roles" />
          </Form.Item>
          <Form.Item label="权限点" name="permissionCode">
            <Select
              allowClear
              options={permissions.map((permission) => ({
                label: `${permission.name} · ${permission.code}`,
                value: permission.code,
              }))}
              optionFilterProp="label"
              placeholder="请选择权限点"
              showSearch
            />
          </Form.Item>
          <Form.Item label="范围类型" name="scopeType">
            <Select
              allowClear
              options={[
                { label: '全局', value: 'global' },
                { label: '产品', value: 'product' },
                { label: '知识空间', value: 'knowledge_space' },
                { label: '部门', value: 'department' },
                { label: '评审任务', value: 'review_assignment' },
              ]}
              placeholder="可选"
            />
          </Form.Item>
          <Form.Item label="范围 ID" name="scopeId">
            <Input placeholder="* / product_001" />
          </Form.Item>
          <Form.Item className="role-permission-diagnostic-actions" label=" ">
            <Space>
              <Button htmlType="submit" loading={permissionDiagnosticLoading} type="primary">
                运行诊断
              </Button>
              <Button
                onClick={() => {
                  permissionDiagnosticForm.resetFields();
                  setPermissionDiagnosticError(undefined);
                  setPermissionDiagnosticResult(undefined);
                }}
              >
                清空
              </Button>
            </Space>
          </Form.Item>
        </Form>
        {permissionDiagnosticError ? (
          <Text className="role-policy-matrix-error" type="danger">
            {formatRemoteRowsError(permissionDiagnosticError)}
          </Text>
        ) : null}
        {permissionDiagnosticResult ? (
          <div className="role-permission-diagnostic-result">
            <Space size={[8, 8]} wrap>
              <StatusTag
                color={permissionDiagnosticResult.decision.allowed ? 'green' : 'red'}
                label={permissionDiagnosticResult.decision.allowed ? '允许访问' : '存在阻断'}
              />
              <Tag>{permissionDiagnosticResult.user.id}</Tag>
              <Tag>{permissionDiagnosticResult.user.status}</Tag>
              <Tag>{permissionDiagnosticResult.effective.role_codes.length} 个角色</Tag>
              <Tag>{permissionDiagnosticResult.effective.permission_codes.length} 个权限点</Tag>
              <Tag>{permissionDiagnosticResult.effective.menu_codes.length} 个菜单</Tag>
            </Space>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="阻断原因" span={2}>
                {renderDiagnosticReasons(permissionDiagnosticResult.decision.blocked_reasons)}
              </Descriptions.Item>
              <Descriptions.Item label="授权来源" span={2}>
                {renderDiagnosticReasons(permissionDiagnosticResult.decision.granted_reasons)}
              </Descriptions.Item>
            </Descriptions>
            <Table<UserPermissionDiagnosticCheck>
              columns={permissionDiagnosticColumns}
              dataSource={permissionDiagnosticResult.checks}
              pagination={false}
              rowKey="code"
              scroll={{ x: 760 }}
              size="small"
              tableLayout="fixed"
            />
          </div>
        ) : null}
      </section>
    ),
    [
      permissionDiagnosticColumns,
      permissionDiagnosticError,
      permissionDiagnosticForm,
      permissionDiagnosticLoading,
      permissionDiagnosticResult,
      permissions,
      runPermissionDiagnostic,
    ],
  );
  const updateGrantMenuSelection = useCallback(
    (menu: MenuResourceRecord, checked: boolean) => {
      const nextMenuCodes = toggleArrayValue(selectedGrantMenuCodes, menu.code, checked);
      const relatedPermissionCodes = menuPermissionCodesByMenu.get(menu.code) ?? [];
      const nextPermissionCodes = checked
        ? selectedGrantPermissionCodes
        : selectedGrantPermissionCodes.filter((code) => !relatedPermissionCodes.includes(code));
      grantForm.setFieldsValue({
        menuCodes: nextMenuCodes,
        permissionCodes: nextPermissionCodes,
      });
    },
    [grantForm, menuPermissionCodesByMenu, selectedGrantMenuCodes, selectedGrantPermissionCodes],
  );
  const updateGrantPermissionSelection = useCallback(
    (menu: MenuResourceRecord | undefined, permissionCode: string, checked: boolean) => {
      const nextPermissionCodes = toggleArrayValue(selectedGrantPermissionCodes, permissionCode, checked);
      const nextMenuCodes = checked && menu
        ? toggleArrayValue(selectedGrantMenuCodes, menu.code, true)
        : selectedGrantMenuCodes;
      grantForm.setFieldsValue({
        menuCodes: nextMenuCodes,
        permissionCodes: nextPermissionCodes,
      });
    },
    [grantForm, selectedGrantMenuCodes, selectedGrantPermissionCodes],
  );

  return (
    <>
      <ManagementListPage<RoleManagementRow>
        breadcrumbGroup="系统管理"
        columns={columns}
        dataSource={listState.rows}
        filters={[
          { label: '角色', name: 'roleLabel', type: 'text' },
          {
            label: '分类',
            name: 'category',
            options: CATEGORY_OPTIONS,
            type: 'select',
          },
          { label: '业务角色', name: 'businessRoleText', type: 'text' },
          { label: '可见入口', name: 'menuScopeText', type: 'text' },
          { label: '权限点', name: 'permissionText', type: 'text' },
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
        onPrimaryAction={openCreateRole}
        onReload={() => void reload()}
        primaryAction="新增角色"
        beforeTable={
          <>
            {permissionDiagnosticPanel}
            {policyMatrixPanel}
          </>
        }
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          total: listState.total,
        }}
        rowKey="code"
        tableLayout="fixed"
        tableTitle="角色定义"
        title="角色管理"
      />
      <Modal
        confirmLoading={submitting}
        destroyOnHidden
        onCancel={() => setRoleFormOpen(false)}
        onOk={() => void submitRoleForm()}
        open={roleFormOpen}
        title={editingRole ? `编辑角色 · ${editingRole.name}` : '新增角色'}
        width={640}
      >
        <Form<RoleFormValues>
          form={roleForm}
          layout="vertical"
          preserve={false}
        >
          <Form.Item
            label="角色编码"
            name="code"
            rules={[{ required: true, message: '请输入角色编码' }]}
          >
            <Input disabled={Boolean(editingRole)} placeholder="frontend_reviewer" />
          </Form.Item>
          <Form.Item label="角色名称" name="name" rules={[{ required: true, message: '请输入角色名称' }]}>
            <Input placeholder="前端评审" />
          </Form.Item>
          <Form.Item label="分类" name="category" rules={[{ required: true, message: '请选择分类' }]}>
            <Select options={CATEGORY_OPTIONS} />
          </Form.Item>
          <Form.Item label="定位描述" name="description">
            <Input.TextArea autoSize={{ minRows: 3, maxRows: 5 }} placeholder="说明该角色的职责边界" />
          </Form.Item>
          <Space align="start" size={24}>
            <Form.Item label="可分配" name="is_assignable" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="排序" name="sort_order">
              <InputNumber min={0} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
      <Modal
        confirmLoading={submitting}
        destroyOnHidden
        onCancel={() => setGrantModal(undefined)}
        onOk={() => void submitGrantForm()}
        open={Boolean(grantModal)}
        title={
          grantModal
            ? `${grantModal.type === 'grants' ? '角色配置' : '配置范围'} · ${grantModal.role.name}`
            : '授权配置'
        }
        width={880}
      >
        <Form form={grantForm} layout="vertical" preserve={false}>
          {grantModal?.type === 'grants' ? (
            <>
              <Form.Item name="menuCodes" hidden>
                <Select mode="multiple" />
              </Form.Item>
              <Form.Item name="permissionCodes" hidden>
                <Select mode="multiple" />
              </Form.Item>
              <div className="role-grant-config">
                {activeMenus.map((menu) => {
                  const isMenuChecked = selectedGrantMenuCodes.includes(menu.code);
                  const menuPermissionCodes = menuPermissionCodesByMenu.get(menu.code) ?? [];
                  return (
                    <section className="role-grant-menu" key={menu.code}>
                      <div className="role-grant-menu-header">
                        <Checkbox
                          checked={isMenuChecked}
                          onChange={(event) => updateGrantMenuSelection(menu, event.target.checked)}
                        >
                          <Text strong>{menu.name}</Text>
                        </Checkbox>
                        <Text type="secondary">{menu.path ?? menu.code}</Text>
                      </div>
                      <div className="role-grant-permissions">
                        {menuPermissionCodes.length > 0 ? (
                          menuPermissionCodes.map((permissionCode) => {
                            const permission = permissionByCode.get(permissionCode);
                            return (
                              <Checkbox
                                checked={selectedGrantPermissionCodes.includes(permissionCode)}
                                disabled={!isMenuChecked}
                                key={permissionCode}
                                onChange={(event) =>
                                  updateGrantPermissionSelection(menu, permissionCode, event.target.checked)
                                }
                              >
                                {permission ? `${permission.name} (${permission.code})` : permissionCode}
                              </Checkbox>
                            );
                          })
                        ) : (
                          <Text type="secondary">该菜单无独立操作权限</Text>
                        )}
                      </div>
                    </section>
                  );
                })}
                {otherPermissions.length > 0 ? (
                  <section className="role-grant-menu">
                    <div className="role-grant-menu-header">
                      <Text strong>其他权限</Text>
                      <Text type="secondary">未绑定到具体菜单的系统能力</Text>
                    </div>
                    <div className="role-grant-permissions">
                      {otherPermissions.map((permission) => (
                        <Checkbox
                          checked={selectedGrantPermissionCodes.includes(permission.code)}
                          key={permission.code}
                          onChange={(event) =>
                            updateGrantPermissionSelection(undefined, permission.code, event.target.checked)
                          }
                        >
                          {permission.name} ({permission.code})
                        </Checkbox>
                      ))}
                    </div>
                  </section>
                ) : null}
              </div>
            </>
          ) : null}
          {grantModal?.type === 'scopes' ? (
            <Form.List name="scopes">
              {(fields, { add, remove }) => (
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  {fields.map((field) => (
                    <Space align="baseline" key={field.key} wrap>
                      <Form.Item {...field} label="范围类型" name={[field.name, 'scope_type']}>
                        <Select
                          options={[
                            { label: '全局', value: 'global' },
                            { label: '产品', value: 'product' },
                            { label: '知识空间', value: 'knowledge_space' },
                            { label: '部门', value: 'department' },
                            { label: '评审任务', value: 'review_assignment' },
                          ]}
                          style={{ width: 150 }}
                        />
                      </Form.Item>
                      <Form.Item {...field} label="范围 ID" name={[field.name, 'scope_id']}>
                        <Input placeholder="* / product_001" style={{ width: 180 }} />
                      </Form.Item>
                      <Form.Item {...field} label="级别" name={[field.name, 'access_level']}>
                        <Select
                          options={[
                            { label: '读取', value: 'read' },
                            { label: '写入', value: 'write' },
                            { label: '管理', value: 'admin' },
                          ]}
                          style={{ width: 120 }}
                        />
                      </Form.Item>
                      <Button onClick={() => remove(field.name)} type="link">
                        移除
                      </Button>
                    </Space>
                  ))}
                  <Button onClick={() => add({ access_level: 'read', scope_id: '', scope_type: 'product' })}>
                    添加范围
                  </Button>
                </Space>
              )}
            </Form.List>
          ) : null}
        </Form>
      </Modal>
      <Modal
        footer={null}
        onCancel={() => setDetailRole(undefined)}
        open={Boolean(detailRole)}
        title={detailRole ? `角色详情 · ${detailRole.name}` : '角色详情'}
        width={880}
      >
        {detailRole ? (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="角色编码">{detailRole.code}</Descriptions.Item>
            <Descriptions.Item label="分类">{detailRole.categoryText}</Descriptions.Item>
            <Descriptions.Item label="业务角色">{renderTagList(detailRole.business_roles)}</Descriptions.Item>
            <Descriptions.Item label="状态">
              {detailRole.status === 'active' ? (
                <StatusTag color="green" label="启用" />
              ) : (
                <StatusTag color="default" label="停用" />
              )}
            </Descriptions.Item>
            <Descriptions.Item label="定位" span={2}>
              <Paragraph>{detailRole.description || '-'}</Paragraph>
            </Descriptions.Item>
            <Descriptions.Item label="职责" span={2}>
              {detailRole.responsibilities.length ? (
                <ul>
                  {detailRole.responsibilities.map((responsibility) => (
                    <li key={responsibility}>{responsibility}</li>
                  ))}
                </ul>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="数据范围">{detailRole.data_scope || '-'}</Descriptions.Item>
            <Descriptions.Item label="决策范围">{detailRole.decision_scope || '-'}</Descriptions.Item>
            <Descriptions.Item label="可见入口" span={2}>
              {renderTagList(detailRole.menu_scope)}
            </Descriptions.Item>
            <Descriptions.Item label="限制边界" span={2}>
              {detailRole.limitations.length ? (
                <ul>
                  {detailRole.limitations.map((limitation) => (
                    <li key={limitation}>{limitation}</li>
                  ))}
                </ul>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="权限点" span={2}>
              {renderTagList(detailRole.permissions)}
            </Descriptions.Item>
          </Descriptions>
        ) : null}
      </Modal>
    </>
  );
}
