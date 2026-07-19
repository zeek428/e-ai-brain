import { Button, Card, Descriptions, Space, Tag, Typography } from 'antd';

import type { ProductVersionDashboard } from '../../../services/aiBrain';

const { Text } = Typography;

const roleLabels: Record<string, string> = {
  developer: '开发员工',
  documenter: '文档员工',
  operator: '运营员工',
  product_manager: '产品经理员工',
  project_owner: '项目负责人员工',
  tester: '测试员工',
};

type VersionDashboardCollaborationPanelProps = {
  onAction: (action: NonNullable<ProductVersionDashboard['rdCollaboration']>['action']) => void;
  overview?: ProductVersionDashboard['rdCollaboration'];
};

function roleLabel(roleCode: string) {
  return roleLabels[roleCode] ?? roleCode;
}

export function VersionDashboardCollaborationPanel({
  onAction,
  overview,
}: VersionDashboardCollaborationPanelProps) {
  if (!overview) {
    return null;
  }
  const run = overview.activeRun ?? overview.latestRun;
  return (
    <Card size="small" title="研发协同">
      {run ? (
        <Descriptions bordered column={4} size="small">
          <Descriptions.Item label="协同状态">
            <Tag color={run.status === 'completed' ? 'green' : 'blue'}>{run.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="工作项">{run.totalWorkItemCount} 个</Descriptions.Item>
          <Descriptions.Item label="阻塞工作项">{run.blockedWorkItemCount} 个</Descriptions.Item>
          <Descriptions.Item label="待人工决策">{run.pendingDecisionCount} 个</Descriptions.Item>
          <Descriptions.Item label="待人工处理">{run.waitingHumanWorkItemCount} 个</Descriptions.Item>
          <Descriptions.Item label="岗位" span={2}>
            {run.roleCodes.length ? run.roleCodes.map(roleLabel).join('、') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="席位">{run.seatCount} 个</Descriptions.Item>
          <Descriptions.Item label="范围版本">v{run.scopeVersion}</Descriptions.Item>
          <Descriptions.Item label="AI 席位容量" span={2}>
            {`可用 AI 席位：${run.capacity.available} / ${run.capacity.frozen}`}
          </Descriptions.Item>
          <Descriptions.Item label="资源冲突">
            {`已串行化资源冲突：${run.parallelConflictCount}`}
          </Descriptions.Item>
        </Descriptions>
      ) : (
        <Text type="secondary">当前版本尚未启动研发协同，可直接从这里按冻结策略启动。</Text>
      )}
      <Space style={{ marginTop: 12 }} wrap>
        <Button onClick={() => onAction(overview.action)} type="primary">
          {overview.action.label}
        </Button>
        <Text type="secondary">
          启动后自动生成并校验工作项；开发、测试和远程提交完成后停在待发布，不会触发部署。
        </Text>
      </Space>
    </Card>
  );
}
