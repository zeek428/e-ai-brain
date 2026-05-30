import type { ProColumns } from '@ant-design/pro-components';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import { fetchDevopsMetrics, type OperationalMetricRecord } from '../../services/aiBrain';

const columns: ProColumns<OperationalMetricRecord>[] = [
  {
    dataIndex: 'category',
    title: '指标来源',
  },
  {
    dataIndex: 'name',
    title: '指标名称',
  },
  {
    dataIndex: 'value',
    title: '指标值',
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

export default function DevopsPage() {
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(fetchDevopsMetrics);

  return (
    <ManagementListPage<OperationalMetricRecord>
      breadcrumbGroup="运营治理"
      columns={columns}
      dataSource={dataSource}
      filters={[
        {
          label: '指标来源',
          name: 'category',
          options: [
            { label: 'GitLab 指标', value: 'GitLab 指标' },
            { label: 'Jenkins 发布', value: 'Jenkins 发布' },
            { label: '线上日志', value: '线上日志' },
          ],
          type: 'select',
        },
        { label: '指标名称', name: 'name', type: 'text' },
        { label: '状态', name: 'status', type: 'text' },
      ]}
      loading={status === 'loading'}
      notice={formatRemoteRowsError(error)}
      onReload={() => void reload()}
      rowKey="id"
      tableTitle="研发运营指标"
      title="研发运营看板"
    />
  );
}
