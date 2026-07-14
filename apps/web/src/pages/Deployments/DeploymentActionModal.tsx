import { FileTextOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Form,
  Input,
  Modal,
  Space,
  Tag,
  Typography,
  type FormInstance,
} from 'antd';

import type {
  DeploymentConnectivityProbeRecord,
  OperationalMetricRecord,
} from '../../services/aiBrain';

export type DeploymentActionType =
  | 'cancel'
  | 'failed'
  | 'probe_and_start'
  | 'rolled_back'
  | 'start'
  | 'success';

export type DeploymentAction = {
  record: OperationalMetricRecord;
  type: DeploymentActionType;
};

export type DeploymentActionFormValues = {
  externalBuildId?: string;
  externalJobName?: string;
  failureReason?: string;
  logUrl?: string;
  reason?: string;
};

const activeRunnerProbeStatuses = new Set(['claimed', 'queued', 'running']);
const runnerProbeStatusLabels: Record<string, string> = {
  claimed: 'Runner 已认领任务',
  queued: '等待 Runner 接单',
  running: 'Runner 正在探测',
  succeeded: '连通性探测通过',
};

const deploymentMethodLabels: Record<string, string> = {
  docker: 'Docker',
  jenkins: 'Jenkins',
  manual: '人工部署',
  ssh: 'SSH',
};

const deploymentChannelLabels: Record<string, string> = {
  integration: '系统集成',
  manual: '人工',
  runner: 'Runner',
};

function isDeploymentRunnerProbeActive(status?: string) {
  return activeRunnerProbeStatuses.has(status ?? '');
}

function runnerProbeStatusLabel(status?: string) {
  return runnerProbeStatusLabels[status ?? ''] ?? '等待重新探测';
}

type DeploymentActionModalProps = {
  action: DeploymentAction | null;
  form: FormInstance<DeploymentActionFormValues>;
  loading: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  onOpenProbeLogs: () => void;
  probe: DeploymentConnectivityProbeRecord | null;
};

export function DeploymentActionModal({
  action,
  form,
  loading,
  onCancel,
  onConfirm,
  onOpenProbeLogs,
  probe,
}: DeploymentActionModalProps) {
  const actionTitle =
    action?.type === 'probe_and_start'
      ? '重新探测并启动部署'
      : action?.type === 'start'
        ? '启动部署'
        : action?.type === 'success'
          ? '确认部署成功'
          : action?.type === 'failed'
            ? '登记部署失败'
            : action?.type === 'rolled_back'
              ? '登记部署回滚'
              : '取消部署';
  const actionNeedsFailureReason = action?.type === 'failed' || action?.type === 'rolled_back';
  const actionIsCancel = action?.type === 'cancel';
  const actionIsStart = action?.type === 'start' || action?.type === 'probe_and_start';
  const probeIsActive = isDeploymentRunnerProbeActive(probe?.status);
  const probeOkText = probeIsActive
    ? '继续等待并启动'
    : probe?.retry?.allowed
      ? '重新探测'
      : '开始探测';

  return (
    <Modal
      confirmLoading={loading}
      destroyOnHidden
      okText={action?.type === 'probe_and_start' ? probeOkText : '确认'}
      okButtonProps={{ 'aria-label': '确认部署操作' }}
      onCancel={onCancel}
      onOk={onConfirm}
      open={action !== null}
      title={actionTitle}
    >
      <Form<DeploymentActionFormValues> form={form} layout="vertical">
        <Form.Item label="部署单"><Input disabled value={action?.record.name ?? '-'} /></Form.Item>
        <Form.Item label="部署方式">
          <Input disabled value={deploymentMethodLabels[action?.record.deploymentMethod ?? 'manual']} />
        </Form.Item>
        <Form.Item label="执行通道">
          <Input disabled value={deploymentChannelLabels[action?.record.executorChannel ?? 'manual']} />
        </Form.Item>
        {action?.type === 'probe_and_start' && probe ? (
          <Alert
            description={(
              <Space orientation="vertical" size={6} style={{ width: '100%' }}>
                <Typography.Text>{probe.failure?.message ?? runnerProbeStatusLabel(probe.status)}</Typography.Text>
                <Space size={8} wrap>
                  {probe.task ? <Tag>任务 {probe.task.id}</Tag> : null}
                  {probeIsActive ? <Tag color="processing">{runnerProbeStatusLabel(probe.status)}</Tag> : null}
                  {probe.task?.remainingWaitSeconds !== undefined ? (
                    <Typography.Text type="secondary">剩余等待约 {probe.task.remainingWaitSeconds} 秒</Typography.Text>
                  ) : null}
                  {probe.retry?.allowed ? <Tag color="orange">可立即重新探测</Tag> : null}
                  {probe.kind === 'runner' && probe.logUrl ? (
                    <Button
                      aria-label="查看 Runner 日志"
                      icon={<FileTextOutlined />}
                      onClick={onOpenProbeLogs}
                      size="small"
                      type="link"
                    >
                      查看 Runner 日志
                    </Button>
                  ) : null}
                </Space>
              </Space>
            )}
            title={probe.ready ? '连通性探测通过，正在启动部署' : runnerProbeStatusLabel(probe.status)}
            showIcon
            type={probe.ready ? 'success' : probe.failure ? 'error' : 'info'}
          />
        ) : null}
        {actionIsCancel ? (
          <Form.Item label="取消原因" name="reason"><Input.TextArea rows={3} /></Form.Item>
        ) : actionIsStart ? null : (
          <>
            <Form.Item label="外部 Job" name="externalJobName"><Input placeholder="Jenkins Job / Pipeline" /></Form.Item>
            <Form.Item label="外部 Build ID" name="externalBuildId"><Input /></Form.Item>
            <Form.Item label="日志链接" name="logUrl"><Input /></Form.Item>
            {actionNeedsFailureReason ? (
              <Form.Item
                label={action?.type === 'rolled_back' ? '回滚原因' : '失败原因'}
                name="failureReason"
                rules={[{ required: true, message: '请输入原因' }]}
              >
                <Input.TextArea rows={3} />
              </Form.Item>
            ) : null}
          </>
        )}
      </Form>
    </Modal>
  );
}
