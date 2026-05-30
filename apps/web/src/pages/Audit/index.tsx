import type { ProColumns } from '@ant-design/pro-components';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { AuditRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import { fetchManagementAudit } from '../../services/aiBrain';

const columns: ProColumns<AuditRecord>[] = [
  {
    dataIndex: 'id',
    title: '审计编号',
  },
  {
    dataIndex: 'eventType',
    title: '事件类型',
  },
  {
    dataIndex: 'subject',
    title: '主体',
  },
  {
    dataIndex: 'actor',
    title: '操作者',
  },
  {
    dataIndex: 'result',
    title: '结果',
    render: (_, row) =>
      row.result === 'success' ? (
        <StatusTag color="green" label="成功" />
      ) : (
        <StatusTag color="red" label="失败" />
      ),
  },
  {
    dataIndex: 'timestamp',
    title: '发生时间',
  },
  {
    key: 'actions',
    title: '操作',
    valueType: 'option',
    render: () => ['详情', '链路追踪'],
  },
];

export default function AuditPage() {
  const { error, rows: dataSource } = useRemoteRows(fetchManagementAudit);

  return (
    <ManagementListPage<AuditRecord>
      breadcrumbGroup="运营治理"
      columns={columns}
      dataSource={dataSource}
      filters={[
        { label: '事件类型', name: 'eventType', type: 'text' },
        { label: '主体', name: 'subject', type: 'text' },
        { label: '操作者', name: 'actor', type: 'text' },
        {
          label: '结果',
          name: 'result',
          options: [
            { label: '成功', value: 'success' },
            { label: '失败', value: 'failed' },
          ],
          type: 'select',
        },
      ]}
      notice={formatRemoteRowsError(error)}
      rowKey="id"
      tableTitle="审计列表"
      title="审计与运行"
    />
  );
}
