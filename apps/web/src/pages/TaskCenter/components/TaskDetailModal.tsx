import { Descriptions, Input, Modal, Space, Tabs, Typography } from 'antd';

import { AgentLoopTimeline } from '../../../components/AgentLoopTimeline';
import { ExecutionContextManifest } from '../../../components/ExecutionContextManifest';
import { StatusTag } from '../../../components/ManagementListPage';
import { QualityGatePanel } from '../../../components/QualityGatePanel';
import type {
  TaskCenterTaskDetailRecord,
  TaskCenterTaskRecord,
} from '../../../services/aiBrain';
import { TaskOutputSummary } from './TaskOutputSummary';

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
  onRequestAgentTakeover?: () => Promise<void> | void;
  takeoverLoading?: boolean;
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

function objectRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  return String(value);
}

function codeInspectionLocation(input: Record<string, unknown>) {
  const filePath = displayValue(input.file_path);
  const lineNumber = displayValue(input.line_number);
  if (filePath === '-') {
    return '-';
  }
  return lineNumber === '-' ? filePath : `${filePath}:${lineNumber}`;
}

function hasCodeInspectionContext(input: Record<string, unknown>) {
  return Boolean(
    input.code_inspection_finding_id ||
      input.code_inspection_report_id ||
      input.file_path ||
      input.rule_id,
  );
}

export function TaskDetailModal({
  dialog,
  onClose,
  onRequestAgentTakeover,
  takeoverLoading,
  taskStatusLabels,
  taskTypeLabels,
}: TaskDetailModalProps) {
  const detail = dialog?.detail;
  const inputContext = objectRecord(detail?.inputJson);
  const showCodeInspectionContext = hasCodeInspectionContext(inputContext);
  const overview = detail ? (
    <Space orientation="vertical" size={12} style={{ width: '100%' }}>
      <Descriptions column={{ xs: 1, sm: 2 }} size="small">
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
        <Descriptions.Item label="待确认">{detail.pendingReviewId ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="Graph Runs">{detail.graphRunIds.join(', ') || '-'}</Descriptions.Item>
      </Descriptions>
      {showCodeInspectionContext ? (
        <section className="task-detail-output-section" data-testid="task-code-inspection-context">
          <div className="task-detail-output-header">
            <Text strong>代码巡检定位</Text>
            <Text type="secondary">用于确认 AI 需要处理的具体 finding</Text>
          </div>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="目标位置">{codeInspectionLocation(inputContext)}</Descriptions.Item>
            <Descriptions.Item label="规则 ID">{displayValue(inputContext.rule_id)}</Descriptions.Item>
            <Descriptions.Item label="严重级别">{displayValue(inputContext.severity)}</Descriptions.Item>
            <Descriptions.Item label="Finding">{displayValue(inputContext.code_inspection_finding_id)}</Descriptions.Item>
            <Descriptions.Item label="报告">{displayValue(inputContext.code_inspection_report_id)}</Descriptions.Item>
            <Descriptions.Item label="问题描述">{displayValue(inputContext.description)}</Descriptions.Item>
            <Descriptions.Item label="修复建议">{displayValue(inputContext.recommendation)}</Descriptions.Item>
          </Descriptions>
        </section>
      ) : null}
      <section className="task-detail-output-section">
        <div className="task-detail-output-header">
          <Text strong>AI 输出摘要</Text>
          <Text type="secondary">用于确认结果，原始执行数据保留在“原始数据”页签</Text>
        </div>
        <TaskOutputSummary summary={detail.outputSummary} />
      </section>
    </Space>
  ) : null;
  return (
    <Modal
      footer={null}
      onCancel={onClose}
      open={Boolean(dialog)}
      title={dialog?.task.label ? `任务详情：${dialog.task.label}` : '任务详情'}
      width={1080}
    >
      {dialog?.loading ? <Text type="secondary">任务详情加载中...</Text> : null}
      {!dialog?.loading && detail ? (
        <Tabs
          destroyOnHidden
          items={[
            { children: overview, key: 'overview', label: '任务概览' },
            {
              children: (
                <AgentLoopTimeline
                  loading={takeoverLoading}
                  loop={detail.agentLoop}
                  onTakeover={onRequestAgentTakeover}
                />
              ),
              key: 'agent-loop',
              label: '自治循环',
            },
            {
              children: <QualityGatePanel gate={detail.qualityGate} />,
              key: 'quality-gate',
              label: '质量门禁',
            },
            {
              children: <ExecutionContextManifest manifest={detail.executionContextManifest} />,
              key: 'context-manifest',
              label: '执行上下文',
            },
            {
              children: (
                <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                  <Text strong>执行输入</Text>
                  <Input.TextArea readOnly rows={8} value={formatJsonPreview(detail.inputJson)} />
                  <Text strong>执行输出</Text>
                  <Input.TextArea readOnly rows={10} value={formatJsonPreview(detail.outputJson)} />
                </Space>
              ),
              key: 'raw',
              label: '原始数据',
            },
          ]}
        />
      ) : null}
      {!dialog?.loading && dialog && !detail ? (
        <Text type="secondary">未加载到任务详情。</Text>
      ) : null}
    </Modal>
  );
}
