import type { ProColumns } from '@ant-design/pro-components';
import { Button, Descriptions, Modal, Space, Tag, Typography } from 'antd';
import { useCallback, useMemo, useState } from 'react';

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

function buildColumns(openDetail: (row: RoleManagementRow) => void): ProColumns<RoleManagementRow>[] {
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
      width: 190,
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
      width: 220,
      render: (_, row) => renderTagList(row.menu_scope, 3),
    },
    {
      dataIndex: 'permissionText',
      title: '权限点',
      width: 120,
      render: (_, row) => <Tag color="blue">{row.permissions.length} 个权限点</Tag>,
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
      width: 88,
      render: (_, row) => (
        <Button onClick={() => openDetail(row)} type="link">
          详情
        </Button>
      ),
    },
  ];
}

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
  const [detailRole, setDetailRole] = useState<RoleManagementRow>();
  const loadRoles = useCallback(async () => {
    const definitions = await fetchRoleDefinitions();
    return definitions.map(mapRoleRow);
  }, []);
  const { error, reload, rows: dataSource, status } = useRemoteRows(loadRoles);
  const columns = useMemo(() => buildColumns(setDetailRole), []);

  return (
    <>
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
        tableLayout="fixed"
        tableScroll={{ x: 1160 }}
        tableTitle="角色定义"
        title="角色管理"
      />
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
