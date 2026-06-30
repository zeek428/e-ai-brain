import { Descriptions, Input, Modal, Space, Typography } from 'antd';

import { StatusTag } from '../../../components/ManagementListPage';
import type {
  TaskCenterTaskDetailRecord,
  TaskCenterTaskRecord,
} from '../../../services/aiBrain';

const { Text } = Typography;

type StatusLabel = {
  color: string;
  label: string;
};

export type TaskDetailDialogState = {
  detail?: TaskCenterTaskDetailRecord;
  loading: boolean;
  task: TaskCenterTaskRecord;
};

type TaskDetailModalProps = {
  dialog?: TaskDetailDialogState;
  onClose: () => void;
  taskStatusLabels: Record<string, StatusLabel>;
  taskTypeLabels: Record<string, string>;
};

function formatJsonPreview(value: unknown) {
  if (value === null || value === undefined || value === '') {
    return '';
  }
  if (typeof value === 'string') {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

export function TaskDetailModal({
  dialog,
  onClose,
  taskStatusLabels,
  taskTypeLabels,
}: TaskDetailModalProps) {
  const detail = dialog?.detail;
  return (
    <Modal
      footer={null}
      onCancel={onClose}
      open={Boolean(dialog)}
      title={dialog?.task.label ? `任务详情：${dialog.task.label}` : '任务详情'}
      width={820}
    >
      {dialog?.loading ? <Text type="secondary">任务详情加载中...</Text> : null}
      {!dialog?.loading && detail ? (
        <Space orientation="vertical" size={12} style={{ width: '100%' }}>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="任务编号">{detail.id}</Descriptions.Item>
            <Descriptions.Item label="任务类型">
              {taskTypeLabels[detail.type] ?? detail.type}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <StatusTag
                color={taskStatusLabels[detail.status]?.color ?? 'default'}
                label={taskStatusLabels[detail.status]?.label ?? detail.status}
              />
            </Descriptions.Item>
            <Descriptions.Item label="当前步骤">{detail.currentStep}</Descriptions.Item>
            <Descriptions.Item label="产品">{detail.productName}</Descriptions.Item>
            <Descriptions.Item label="版本">{detail.versionName}</Descriptions.Item>
            <Descriptions.Item label="模块">{detail.moduleName}</Descriptions.Item>
            <Descriptions.Item label="需求">{detail.requirementTitle}</Descriptions.Item>
            <Descriptions.Item label="待确认">
              {detail.pendingReviewId ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Graph Runs">
              {detail.graphRunIds.join(', ') || '-'}
            </Descriptions.Item>
          </Descriptions>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="输出摘要">{detail.outputSummary}</Descriptions.Item>
          </Descriptions>
          <Input.TextArea readOnly rows={8} value={formatJsonPreview(detail.outputJson)} />
        </Space>
      ) : null}
      {!dialog?.loading && dialog && !detail ? (
        <Text type="secondary">未加载到任务详情。</Text>
      ) : null}
    </Modal>
  );
}
