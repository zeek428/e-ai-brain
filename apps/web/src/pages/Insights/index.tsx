import type { ProColumns } from '@ant-design/pro-components';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import { fetchUserInsights, type UserInsightRecord } from '../../services/aiBrain';

const columns: ProColumns<UserInsightRecord>[] = [
  {
    dataIndex: 'category',
    title: '数据类型',
  },
  {
    dataIndex: 'summary',
    title: '摘要',
  },
  {
    dataIndex: 'owner',
    title: '归属用户',
  },
  {
    dataIndex: 'status',
    title: '状态',
    render: (_, row) => <StatusTag color={row.status === '-' ? 'default' : 'blue'} label={row.status} />,
  },
  {
    dataIndex: 'updatedAt',
    title: '更新时间',
  },
];

export default function InsightsPage() {
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(fetchUserInsights);

  return (
    <ManagementListPage<UserInsightRecord>
      breadcrumbGroup="运营治理"
      columns={columns}
      dataSource={dataSource}
      filters={[
        {
          label: '数据类型',
          name: 'category',
          options: [
            { label: '使用趋势', value: '使用趋势' },
            { label: '用户反馈', value: '用户反馈' },
            { label: '迭代建议', value: '迭代建议' },
          ],
          type: 'select',
        },
        { label: '摘要', name: 'summary', type: 'text' },
        { label: '状态', name: 'status', type: 'text' },
      ]}
      loading={status === 'loading'}
      notice={formatRemoteRowsError(error)}
      onReload={() => void reload()}
      rowKey="id"
      tableTitle="用户洞察/迭代规划"
      title="用户洞察/迭代规划"
    />
  );
}
