import type { ProColumns } from '@ant-design/pro-components';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import { bugRows, type BugRecord } from '../../data/management';

const severityLabels: Record<BugRecord['severity'], { color: string; label: string }> = {
  blocker: { color: 'red', label: '阻断' },
  major: { color: 'orange', label: '严重' },
  minor: { color: 'blue', label: '一般' },
};

const statusLabels: Record<BugRecord['status'], { color: string; label: string }> = {
  open: { color: 'red', label: '待处理' },
  resolved: { color: 'green', label: '已解决' },
  triaged: { color: 'gold', label: '已分诊' },
};

const columns: ProColumns<BugRecord>[] = [
  {
    dataIndex: 'id',
    title: 'Bug 编号',
  },
  {
    dataIndex: 'title',
    title: 'Bug 标题',
  },
  {
    dataIndex: 'module',
    title: '所属模块',
  },
  {
    dataIndex: 'severity',
    title: '严重级别',
    render: (_, row) => {
      const severity = severityLabels[row.severity];
      return <StatusTag color={severity.color} label={severity.label} />;
    },
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
    dataIndex: 'source',
    title: '来源',
    render: (_, row) =>
      row.source === 'ai_test' ? (
        <StatusTag color="purple" label="AI 自动测试" />
      ) : (
        <StatusTag color="default" label="人工登记" />
      ),
  },
  {
    dataIndex: 'assignee',
    title: '处理人',
  },
  {
    key: 'actions',
    title: '操作',
    valueType: 'option',
    render: () => ['详情', '分派', '关闭'],
  },
];

export default function BugsPage() {
  return (
    <ManagementListPage<BugRecord>
      breadcrumbGroup="需求交付"
      columns={columns}
      dataSource={bugRows}
      filters={[
        { label: 'Bug 标题', name: 'title', type: 'text' },
        { label: '所属模块', name: 'module', type: 'text' },
        {
          label: '严重级别',
          name: 'severity',
          options: [
            { label: '阻断', value: 'blocker' },
            { label: '严重', value: 'major' },
            { label: '一般', value: 'minor' },
          ],
          type: 'select',
        },
        {
          label: '状态',
          name: 'status',
          options: [
            { label: '待处理', value: 'open' },
            { label: '已分诊', value: 'triaged' },
            { label: '已解决', value: 'resolved' },
          ],
          type: 'select',
        },
      ]}
      primaryAction="登记 Bug"
      rowKey="id"
      tableTitle="Bug 列表"
      title="Bug 管理"
    />
  );
}
