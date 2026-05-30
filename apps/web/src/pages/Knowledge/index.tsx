import type { ProColumns } from '@ant-design/pro-components';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import { knowledgeRows, type KnowledgeRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import { fetchManagementKnowledge } from '../../services/aiBrain';

const statusLabels: Record<KnowledgeRecord['status'], { color: string; label: string }> = {
  failed: { color: 'red', label: '索引失败' },
  indexed: { color: 'green', label: '已索引' },
  pending_index: { color: 'gold', label: '待索引' },
  review_pending: { color: 'blue', label: '待审核' },
};

const columns: ProColumns<KnowledgeRecord>[] = [
  {
    dataIndex: 'id',
    title: '知识编号',
  },
  {
    dataIndex: 'title',
    title: '知识标题',
  },
  {
    dataIndex: 'documentType',
    title: '类型',
  },
  {
    dataIndex: 'ownerRole',
    title: '权限角色',
  },
  {
    dataIndex: 'status',
    title: '状态',
    render: (_, row) => {
      const status = statusLabels[row.status];
      return <StatusTag color={status.color} label={status.label} />;
    },
  },
  {
    dataIndex: 'updatedAt',
    title: '更新时间',
  },
  {
    key: 'actions',
    title: '操作',
    valueType: 'option',
    render: () => ['详情', '审核', '检索验证'],
  },
];

export default function KnowledgePage() {
  const { error, rows: dataSource } = useRemoteRows(knowledgeRows, fetchManagementKnowledge);

  return (
    <ManagementListPage<KnowledgeRecord>
      breadcrumbGroup="产品资产"
      columns={columns}
      dataSource={dataSource}
      filters={[
        { label: '知识标题', name: 'title', type: 'text' },
        {
          label: '类型',
          name: 'documentType',
          options: [
            { label: 'PRD', value: 'PRD' },
            { label: 'Spec', value: 'Spec' },
            { label: 'Deposit', value: 'Deposit' },
          ],
          type: 'select',
        },
        { label: '权限角色', name: 'ownerRole', type: 'text' },
        {
          label: '状态',
          name: 'status',
          options: [
            { label: '已索引', value: 'indexed' },
            { label: '待索引', value: 'pending_index' },
            { label: '待审核', value: 'review_pending' },
            { label: '索引失败', value: 'failed' },
          ],
          type: 'select',
        },
      ]}
      notice={formatRemoteRowsError(error)}
      primaryAction="导入文档"
      rowKey="id"
      tableTitle="知识列表"
      title="知识中心"
    />
  );
}
