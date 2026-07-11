import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  DeploymentUnitOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Collapse,
  Descriptions,
  Drawer,
  Empty,
  Result,
  Space,
  Spin,
  Tabs,
  Tag,
  Timeline,
  Typography,
} from 'antd';
import { useEffect, useMemo, useState } from 'react';

import {
  fetchDeploymentRequestDetail,
  type DeploymentRequestRecord,
  type DeploymentRunStepRecord,
} from '../../services/aiBrain';

import './DeploymentDetailDrawer.less';

const { Text, Title } = Typography;

const statusLabels: Record<string, { color: string; label: string }> = {
  cancelled: { color: 'default', label: '已取消' },
  completed: { color: 'green', label: '已完成' },
  dead_letter: { color: 'red', label: '死信' },
  deploying: { color: 'processing', label: '部署中' },
  failed: { color: 'red', label: '失败' },
  healthy: { color: 'green', label: '健康' },
  passed: { color: 'green', label: '通过' },
  pending: { color: 'default', label: '等待中' },
  pending_ops: { color: 'gold', label: '待运维执行' },
  processing: { color: 'processing', label: '处理中' },
  queued: { color: 'blue', label: '已排队' },
  rolled_back: { color: 'volcano', label: '已回滚' },
  rolling_back: { color: 'orange', label: '回滚中' },
  running: { color: 'processing', label: '执行中' },
  skipped: { color: 'default', label: '已跳过' },
  succeeded: { color: 'green', label: '部署成功' },
  success: { color: 'green', label: '成功' },
  unhealthy: { color: 'red', label: '异常' },
  waiting_takeover: { color: 'orange', label: '待人工接管' },
};

const stepLabels: Record<string, string> = {
  deploy: '部署执行',
  health_check: '健康检查',
  preflight: '部署前检查',
  rollback: '回滚',
  smoke_test: '冒烟测试',
  traffic_switch: '流量切换',
};

function StatusTag({ status }: { status?: string }) {
  const definition = statusLabels[status ?? ''] ?? { color: 'default', label: status || '-' };
  return <Tag color={definition.color}>{definition.label}</Tag>;
}

function stepIcon(step: DeploymentRunStepRecord) {
  if (step.status === 'passed') return <CheckCircleOutlined />;
  if (step.status === 'failed') return <CloseCircleOutlined />;
  return <ClockCircleOutlined />;
}

function ExecutionTimeline({ deployment }: { deployment: DeploymentRequestRecord }) {
  if (!deployment.runs.length) return <Empty description="暂无执行记录" />;
  return (
    <Space className="deployment-detail-runs" orientation="vertical" size={20}>
      {deployment.runs.map((run) => (
        <section className="deployment-detail-run" key={run.id}>
          <Space size={8} wrap>
            <Title level={5}>{run.operation === 'rollback' ? '回滚运行' : '部署运行'}</Title>
            <StatusTag status={run.status} />
            <StatusTag status={run.healthStatus} />
            <Text type="secondary">
              第 {run.waveNumber ?? 1} / {run.waveTotal ?? deployment.totalWaves} 波
            </Text>
          </Space>
          <Timeline
            items={run.steps.map((step) => ({
              content: (
                <div className="deployment-detail-step">
                  <Space size={8} wrap>
                    <Text strong>{stepLabels[step.stepType] ?? step.stepType}</Text>
                    <StatusTag status={step.status} />
                    {step.startedAt ? <Text type="secondary">{step.startedAt}</Text> : null}
                  </Space>
                  {step.summary ? <div>{step.summary}</div> : null}
                </div>
              ),
              color: step.status === 'failed' ? 'red' : step.status === 'passed' ? 'green' : 'blue',
              icon: stepIcon(step),
            }))}
          />
        </section>
      ))}
    </Space>
  );
}

function GatePanel({ deployment }: { deployment: DeploymentRequestRecord }) {
  const gate = deployment.qualityGate;
  if (!gate) return <Empty description="暂无前置质量门禁" />;
  return (
    <section>
      <Space size={8} wrap>
        <Title level={5}>质量门禁</Title>
        <StatusTag status={gate.status} />
      </Space>
      {gate.summary ? <Text>{gate.summary}</Text> : null}
      {gate.blockedReasons.length ? (
        <Alert
          message="门禁阻断"
          description={gate.blockedReasons.join('；')}
          showIcon
          type="error"
        />
      ) : null}
      {gate.checks.length ? (
        <div className="deployment-detail-list">
          {gate.checks.map((check) => (
            <div className="deployment-detail-list-row" key={check.id ?? check.checkType}>
              <div className="deployment-detail-list-content">
                <Text strong>{check.checkType}</Text>
                <Text type="secondary">{check.summary || check.source}</Text>
              </div>
              <StatusTag status={check.status} />
            </div>
          ))}
        </div>
      ) : <Empty description="暂无检查项" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
    </section>
  );
}

function DispatchAndAudit({ deployment }: { deployment: DeploymentRequestRecord }) {
  return (
    <Space className="deployment-detail-runs" orientation="vertical" size={24}>
      <section>
        <Title level={5}>派发记录</Title>
        {deployment.dispatchEvents.length ? (
          <div className="deployment-detail-list">
            {deployment.dispatchEvents.map((event) => (
              <div className="deployment-detail-list-row" key={event.id}>
                <div className="deployment-detail-list-content">
                  <Text strong>{event.eventType}</Text>
                  <Text type="secondary">
                    尝试 {event.attemptCount} 次{event.lastError ? ` · ${event.lastError}` : ''}
                  </Text>
                </div>
                <StatusTag status={event.status} />
              </div>
            ))}
          </div>
        ) : <Empty description="暂无派发记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
      </section>
      <section>
        <Title level={5}>审计记录</Title>
        {deployment.auditEvents.length ? (
          <div className="deployment-detail-list">
            {deployment.auditEvents.map((event) => (
              <div className="deployment-detail-list-row" key={event.id}>
                <div className="deployment-detail-list-content">
                  <Text strong>{event.eventType}</Text>
                  <Text type="secondary">
                    {[event.actorId, event.createdAt].filter(Boolean).join(' · ')}
                  </Text>
                </div>
              </div>
            ))}
          </div>
        ) : <Empty description="暂无审计记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
      </section>
    </Space>
  );
}

export function DeploymentDetailDrawer({
  deploymentId,
  onClose,
}: {
  deploymentId?: string;
  onClose: () => void;
}) {
  const [state, setState] = useState<{
    data?: DeploymentRequestRecord;
    deploymentId?: string;
    error?: string;
  }>({});

  useEffect(() => {
    if (!deploymentId) {
      return;
    }
    let active = true;
    void fetchDeploymentRequestDetail(deploymentId)
      .then((data) => {
        if (active) setState({ data, deploymentId });
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            deploymentId,
            error: error instanceof Error ? error.message : '部署详情加载失败',
          });
        }
      });
    return () => {
      active = false;
    };
  }, [deploymentId]);

  const currentData = state.deploymentId === deploymentId ? state.data : undefined;
  const currentError = state.deploymentId === deploymentId ? state.error : undefined;
  const loading = Boolean(deploymentId) && state.deploymentId !== deploymentId;

  const tabs = useMemo(() => {
    if (!currentData) return [];
    return [
      { children: <ExecutionTimeline deployment={currentData} />, key: 'execution', label: '执行链路' },
      { children: <GatePanel deployment={currentData} />, key: 'gate', label: '门禁与审批' },
      {
        children: <DispatchAndAudit deployment={currentData} />,
        key: 'dispatch',
        label: '派发与审计',
      },
    ];
  }, [currentData]);

  return (
    <Drawer
      destroyOnHidden
      onClose={onClose}
      open={Boolean(deploymentId)}
      title={`部署详情 · ${currentData?.title ?? deploymentId ?? ''}`}
      size="min(920px, 94vw)"
    >
      <Spin spinning={loading}>
        {currentError ? <Result status="error" subTitle={currentError} title="详情加载失败" /> : null}
        {currentData ? (
          <Space className="deployment-detail-runs" orientation="vertical" size={20}>
            <Descriptions bordered column={{ lg: 3, md: 2, sm: 1, xs: 1 }} size="small">
              <Descriptions.Item label="部署编号">{currentData.id}</Descriptions.Item>
              <Descriptions.Item label="状态"><StatusTag status={currentData.status} /></Descriptions.Item>
              <Descriptions.Item label="波次">
                第 {currentData.currentWave || 0} / {currentData.totalWaves} 波
              </Descriptions.Item>
              <Descriptions.Item label="产品">{currentData.productId}</Descriptions.Item>
              <Descriptions.Item label="版本">{currentData.versionId}</Descriptions.Item>
              <Descriptions.Item label="环境">{currentData.environment}</Descriptions.Item>
              <Descriptions.Item label="执行方式">
                <Space><DeploymentUnitOutlined />{currentData.deploymentMethod}</Space>
              </Descriptions.Item>
              <Descriptions.Item label="风险">{currentData.riskLevel}</Descriptions.Item>
              <Descriptions.Item label="需求数">{currentData.requirementIds.length}</Descriptions.Item>
              <Descriptions.Item label="制品版本">{currentData.artifactVersion || '-'}</Descriptions.Item>
              <Descriptions.Item label="Commit">{currentData.commitSha || '-'}</Descriptions.Item>
              <Descriptions.Item label="制品摘要">{currentData.artifactDigest || '-'}</Descriptions.Item>
              <Descriptions.Item label="窗口策略">{currentData.windowEnforcement || '-'}</Descriptions.Item>
            </Descriptions>
            {currentData.failureReason ? (
              <Alert message="执行异常" description={currentData.failureReason} showIcon type="error" />
            ) : null}
            <Tabs items={tabs} />
            <Collapse
              ghost
              items={[
                {
                  children: <pre className="deployment-detail-json">{JSON.stringify(currentData, null, 2)}</pre>,
                  key: 'diagnostics',
                  label: '诊断数据',
                },
              ]}
            />
          </Space>
        ) : null}
      </Spin>
    </Drawer>
  );
}
