import { Alert, Card, Typography } from 'antd';

import type { RdCollaborationRun } from '../../services/rdCollaborationClient';

type Props = {
  run: Pick<RdCollaborationRun, 'delivery_target' | 'product_version_id' | 'status'>;
};

export function DeploymentPanel({ run }: Props) {
  const eligible = run.delivery_target === 'deployed' && run.status === 'ready_for_release';
  if (!eligible) {
    return null;
  }
  return (
    <Card style={{ marginTop: 16 }} title="既有部署域">
      <Alert
        showIcon
        title="部署仅能在既有部署域按独立权限、人工门禁和冻结交付证据继续处理。研发协同不会创建或启动部署。"
        type="warning"
      />
      <Typography.Paragraph style={{ marginTop: 12 }}>
        <a href={`/governance/deployments?version_id=${encodeURIComponent(run.product_version_id)}`}>查看既有部署请求</a>
      </Typography.Paragraph>
    </Card>
  );
}
