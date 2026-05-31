import type { ProColumns } from '@ant-design/pro-components';
import { Space, Tag } from 'antd';
import { useCallback } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { UserRoleDefinition } from '../../data/roles';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import { fetchRoleDefinitions } from '../../services/aiBrain';

type RoleManagementRow = UserRoleDefinition & {
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

const CATEGORY_LABELS: Record<string, string> = {
  delivery: '交付角色',
  knowledge: '知识角色',
  readonly: '只读角色',
  review: '评审角色',
  system: '系统角色',
  workspace: '工作台角色',
};

const columns: ProColumns<RoleManagementRow>[] = [
  {
    dataIndex: 'roleLabel',
    title: '角色',
    render: (_, row) => `${row.name} (${row.code})`,
  },
  {
    dataIndex: 'categoryText',
    title: '分类',
  },
  {
    dataIndex: 'businessRoleText',
    title: '业务角色',
    render: (_, row) => (
      <Space size={[4, 4]} wrap>
        {row.business_roles.map((role) => (
          <Tag key={role}>{role}</Tag>
        ))}
      </Space>
    ),
  },
  {
    dataIndex: 'description',
    title: '定位',
  },
  {
    dataIndex: 'responsibilityText',
    title: '职责',
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
    dataIndex: 'menuScopeText',
    title: '可见入口',
    render: (_, row) => (
      <Space size={[4, 4]} wrap>
        {row.menu_scope.map((menu) => (
          <Tag key={menu}>{menu}</Tag>
        ))}
      </Space>
    ),
  },
  {
    dataIndex: 'limitationText',
    title: '限制边界',
  },
  {
    dataIndex: 'permissionText',
    title: '权限点',
    render: (_, row) => (
      <Space size={[4, 4]} wrap>
        {row.permissions.map((permission) => (
          <Tag key={permission}>{permission}</Tag>
        ))}
      </Space>
    ),
  },
  {
    dataIndex: 'assignableText',
    title: '可分配',
    render: (_, row) =>
      row.is_assignable ? (
        <StatusTag color="green" label="可分配" />
      ) : (
        <StatusTag color="default" label="不可分配" />
      ),
  },
  {
    dataIndex: 'statusText',
    title: '状态',
    render: (_, row) =>
      row.status === 'active' ? (
        <StatusTag color="green" label="启用" />
      ) : (
        <StatusTag color="default" label="停用" />
      ),
  },
];

function mapRoleRow(role: UserRoleDefinition): RoleManagementRow {
  return {
    ...role,
    assignableText: role.is_assignable ? '可分配' : '不可分配',
    businessRoleText: role.business_roles.join(', '),
    categoryText: CATEGORY_LABELS[role.category] ?? role.category,
    limitationText: role.limitations.join('；'),
    menuScopeText: role.menu_scope.join(', '),
    permissionText: role.permissions.join(', '),
    responsibilityText: role.responsibilities.join('；'),
    roleLabel: `${role.name} (${role.code})`,
    statusText: role.status === 'active' ? '启用' : '停用',
  };
}

export default function RolesPage() {
  const loadRoles = useCallback(async () => {
    const definitions = await fetchRoleDefinitions();
    return definitions.map(mapRoleRow);
  }, []);
  const { error, reload, rows: dataSource, status } = useRemoteRows(loadRoles);

  return (
    <ManagementListPage<RoleManagementRow>
      breadcrumbGroup="系统管理"
      columns={columns}
      dataSource={dataSource}
      filters={[
        { label: '角色', name: 'roleLabel', type: 'text' },
        {
          label: '分类',
          name: 'categoryText',
          options: Object.values(CATEGORY_LABELS).map((label) => ({ label, value: label })),
          type: 'select',
        },
        { label: '业务角色', name: 'businessRoleText', type: 'text' },
        { label: '可见入口', name: 'menuScopeText', type: 'text' },
        { label: '权限点', name: 'permissionText', type: 'text' },
        {
          label: '状态',
          name: 'statusText',
          options: [
            { label: '启用', value: '启用' },
            { label: '停用', value: '停用' },
          ],
          type: 'select',
        },
      ]}
      loading={status === 'loading'}
      notice={formatRemoteRowsError(error)}
      onReload={() => void reload()}
      rowKey="code"
      tableTitle="角色定义"
      title="角色管理"
    />
  );
}
