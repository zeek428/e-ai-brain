import type { ProColumns } from '@ant-design/pro-components';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import { productRows, type ProductRecord } from '../../data/management';

const columns: ProColumns<ProductRecord>[] = [
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
    render: () => ['详情', '编辑', '版本/模块'],
  },
];

export default function ProductsPage() {
  return (
    <ManagementListPage<ProductRecord>
      breadcrumbGroup="产品资产"
      columns={columns}
      dataSource={productRows}
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
      primaryAction="新增产品"
      rowKey="code"
      tableTitle="产品列表"
      title="产品管理"
    />
  );
}
