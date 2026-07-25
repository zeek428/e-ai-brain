import { Button, Card, Empty, Popconfirm, Space, Tag, Typography } from 'antd';

import type { RdWorkItem, RdWorkItemDependency } from '../../services/rdCollaborationClient';

type Props = {
  dependencies: RdWorkItemDependency[];
  items: RdWorkItem[];
  onResumeCancelled?: (item: RdWorkItem) => Promise<void>;
  resumingWorkItemId?: string;
};

const statusColors: Record<string, string> = {
  blocked: 'orange',
  cancelled: 'default',
  completed: 'green',
  ready: 'blue',
  rework_required: 'red',
  running: 'cyan',
  waiting_human: 'gold',
  waiting_review: 'purple',
};

export function WorkItemDag({
  dependencies,
  items,
  onResumeCancelled,
  resumingWorkItemId,
}: Props) {
  const titles = new Map(items.map((item) => [item.id, item.title]));
  const predecessorText = new Map<string, string[]>();
  for (const dependency of dependencies) {
    predecessorText.set(dependency.successor_work_item_id, [
      ...(predecessorText.get(dependency.successor_work_item_id) ?? []),
      titles.get(dependency.predecessor_work_item_id) ?? dependency.predecessor_work_item_id,
    ]);
  }

  if (!items.length) {
    return <Empty description="尚未生成工作项计划" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  return (
    <Space orientation="vertical" size="small" style={{ width: '100%' }}>
      {items.map((item) => (
        <Card key={item.id} size="small" title={item.title}>
          <Space orientation="vertical" size={4} style={{ width: '100%' }}>
            <Space wrap>
              <Tag color={statusColors[item.status] ?? 'default'}>{item.status}</Tag>
              {item.risk_level ? <Tag>{item.risk_level} 风险</Tag> : null}
              {item.priority ? <Tag>{item.priority}</Tag> : null}
            </Space>
            <Typography.Text type="secondary">
              前置工作项：{(predecessorText.get(item.id) ?? []).join('、') || '无，可并行推进'}
            </Typography.Text>
            {item.status === 'cancelled' && onResumeCancelled ? (
              <Popconfirm
                cancelText="暂不恢复"
                description="旧任务、旧 attempt 与隔离工作区产物会保留。确认后仅创建新的返工机会，由 Worker 重新派发。"
                okText="确认恢复"
                onConfirm={() => onResumeCancelled(item)}
                title="确认已修复根因并恢复该工作项？"
              >
                <Button loading={resumingWorkItemId === item.id} size="small" type="primary">
                  从取消恢复
                </Button>
              </Popconfirm>
            ) : null}
          </Space>
        </Card>
      ))}
    </Space>
  );
}
