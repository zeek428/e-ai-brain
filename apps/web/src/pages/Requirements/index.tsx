import type { ProColumns } from '@ant-design/pro-components';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import { requirementRows, type RequirementRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import { fetchManagementRequirements } from '../../services/aiBrain';

const statusLabels: Record<RequirementRecord['status'], { color: string; label: string }> = {
  approved: { color: 'green', label: '已审批' },
  closed: { color: 'default', label: '已关闭' },
  draft: { color: 'default', label: '草稿' },
  pending_approval: { color: 'gold', label: '待审批' },
  rejected: { color: 'red', label: '已拒绝' },
  task_created: { color: 'blue', label: '已生成任务' },
};

const columns: ProColumns<RequirementRecord>[] = [
  {
    dataIndex: 'id',
    title: '需求编号',
  },
  {
    dataIndex: 'title',
    title: '需求标题',
  },
  {
    dataIndex: 'product',
    title: '所属产品',
  },
  {
    dataIndex: 'priority',
    title: '优先级',
    render: (_, row) => <StatusTag color={row.priority === 'P0' ? 'red' : 'blue'} label={row.priority} />,
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
    dataIndex: 'owner',
    title: '负责人',
  },
  {
    dataIndex: 'updatedAt',
    title: '更新时间',
  },
  {
    key: 'actions',
    title: '操作',
    valueType: 'option',
    render: () => ['详情', '审批', '生成任务'],
  },
];

export default function RequirementsPage() {
  const { error, rows: dataSource } = useRemoteRows(requirementRows, fetchManagementRequirements);

  return (
    <ManagementListPage<RequirementRecord>
      breadcrumbGroup="需求交付"
      columns={columns}
      dataSource={dataSource}
      filters={[
        { label: '需求标题', name: 'title', type: 'text' },
        { label: '所属产品', name: 'product', type: 'text' },
        {
          label: '状态',
          name: 'status',
          options: [
            { label: '草稿', value: 'draft' },
            { label: '待审批', value: 'pending_approval' },
            { label: '已审批', value: 'approved' },
            { label: '已拒绝', value: 'rejected' },
            { label: '已生成任务', value: 'task_created' },
            { label: '已关闭', value: 'closed' },
          ],
          type: 'select',
        },
        {
          label: '优先级',
          name: 'priority',
          options: [
            { label: 'P0', value: 'P0' },
            { label: 'P1', value: 'P1' },
            { label: 'P2', value: 'P2' },
          ],
          type: 'select',
        },
      ]}
      notice={formatRemoteRowsError(error)}
      primaryAction="新增需求"
      rowKey="id"
      tableTitle="需求列表"
      title="需求管理"
    />
  );
}
