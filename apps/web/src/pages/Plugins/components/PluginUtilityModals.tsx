import { CheckCircleOutlined, ReloadOutlined, StopOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { SelectProps } from 'antd';
import { Alert, Button, Input, Modal, Select, Space, Table, Tag, Typography } from 'antd';

import { ExecutionTraceLink } from '../../../components/ExecutionTraceLink';
import type {
  AiExecutorRunnerRecord,
  AiExecutorApprovalRequestRecord,
  AiExecutorTaskLogRecord,
  AiExecutorTaskRecord,
  PluginActionRecord,
  PluginActionTrialResult,
  PluginSystemVariableRecord,
} from '../../../services/aiBrain';
import { formatDisplayDateTime } from '../../../utils/dateTime';
import { ReuseWizardSummary, RunnerApprovalRequestBlock, TrialWritePreviewBlock } from './PluginDiagnostics';
import { compactJson } from './pluginDiagnosticsHelpers';
import { trialSeedCanCreateScheduledJobDraft } from './pluginTrialDraftHelpers';

type SystemVariableModalProps = {
  columns: ColumnsType<PluginSystemVariableRecord>;
  items: PluginSystemVariableRecord[];
  onClose: () => void;
  open: boolean;
  timezone: string;
};

type RunnerLogModalProps = {
  loading: boolean;
  onCancelTask: () => void;
  onClose: () => void;
  onRetryTask: () => void;
  open: boolean;
  rows: AiExecutorTaskLogRecord[];
  task?: AiExecutorTaskRecord;
};

type RunnerApprovalRequestsModalProps = {
  approvingId?: string;
  loading: boolean;
  onApprove: (record: AiExecutorApprovalRequestRecord) => void | Promise<void>;
  onClose: () => void;
  onRefresh: () => void | Promise<void>;
  open: boolean;
  rows: AiExecutorApprovalRequestRecord[];
};

type PluginActionTrialModalProps = {
  action?: PluginActionRecord;
  connectionId?: string;
  connectionOptions: SelectProps['options'];
  inputJson: string;
  onApproveAiExecutor?: () => void | Promise<void>;
  onCreateScheduledJobDraft?: () => void;
  onConnectionChange: (value: string | undefined) => void;
  onInputJsonChange: (value: string) => void;
  onRun: () => void;
  onClose: () => void;
  open: boolean;
  result?: PluginActionTrialResult;
  running: boolean;
  sampleResponseSummary?: Record<string, unknown>;
};

type RunnerTokenRotationNoticeProps = {
  onClose: () => void;
  token?: string;
};

type RunnerTokenRotationModalProps = {
  loading: boolean;
  onCancel: () => void;
  onSubmit: () => void | Promise<void>;
  runner?: AiExecutorRunnerRecord;
};

const TERMINAL_RUNNER_TASK_STATUSES = new Set([
  'cancelled',
  'dead_letter',
  'failed',
  'succeeded',
  'timed_out',
]);

const RETRYABLE_RUNNER_TASK_STATUSES = new Set([
  'cancelled',
  'dead_letter',
  'failed',
  'timed_out',
]);

function approvalRequestStatusColor(status?: string) {
  if (status === 'pending') {
    return 'orange';
  }
  if (status === 'approved') {
    return 'green';
  }
  if (status === 'rejected' || status === 'expired') {
    return 'red';
  }
  return 'default';
}

function approvalRequestTitle(record: AiExecutorApprovalRequestRecord) {
  const rawTitle = record.approval_request?.title;
  return typeof rawTitle === 'string' && rawTitle.trim() ? rawTitle : '高风险操作审批';
}

export function SystemVariableModal({
  columns,
  items,
  onClose,
  open,
  timezone,
}: SystemVariableModalProps) {
  return (
    <Modal footer={null} onCancel={onClose} open={open} title="全部系统变量" width={920}>
      <Space orientation="vertical" size={12} style={{ display: 'flex' }}>
        <Typography.Text type="secondary">
          解析时区：{timezone}。表达式和值都可以复制，保存配置时保留表达式，运行时再按时区解析。
        </Typography.Text>
        <Table<PluginSystemVariableRecord>
          columns={columns}
          dataSource={items}
          pagination={false}
          rowKey="expression"
          scroll={{ x: 720 }}
          size="small"
        />
      </Space>
    </Modal>
  );
}

export function RunnerLogModal({
  loading,
  onCancelTask,
  onClose,
  onRetryTask,
  open,
  rows,
  task,
}: RunnerLogModalProps) {
  const canCancelTask = Boolean(task?.id) && !TERMINAL_RUNNER_TASK_STATUSES.has(String(task?.status));
  const canRetryTask = Boolean(task?.id) && RETRYABLE_RUNNER_TASK_STATUSES.has(String(task?.status));
  return (
    <Modal
      aria-label="Runner 执行日志"
      destroyOnHidden
      footer={(
        <Space>
          <Button onClick={onClose}>关闭</Button>
          <Button
            aria-label="重试任务"
            disabled={!canRetryTask}
            icon={<ReloadOutlined />}
            loading={loading}
            onClick={onRetryTask}
            type="primary"
          >
            重试任务
          </Button>
          <Button
            aria-label="取消任务"
            danger
            disabled={!canCancelTask}
            icon={<StopOutlined />}
            loading={loading}
            onClick={onCancelTask}
          >
            取消任务
          </Button>
        </Space>
      )}
      open={open}
      title="Runner 执行日志"
      width={820}
      onCancel={onClose}
    >
      <Space orientation="vertical" size={12} style={{ width: '100%' }}>
        <Space wrap>
          <Typography.Text strong>任务 ID</Typography.Text>
          <Typography.Text code copyable={task?.id ? { text: task.id } : false}>
            {task?.id ?? '-'}
          </Typography.Text>
          <Tag>{task?.status ?? '-'}</Tag>
          <ExecutionTraceLink fallback={null} sourceId={task?.id} sourceType="ai_executor_task">
            任务诊断
          </ExecutionTraceLink>
          <ExecutionTraceLink fallback={null} sourceId={task?.runner_id} sourceType="ai_executor_runner">
            Runner 诊断
          </ExecutionTraceLink>
          <ExecutionTraceLink fallback={null} sourceId={task?.scheduled_job_run_id} sourceType="scheduled_job_run">
            来源运行诊断
          </ExecutionTraceLink>
        </Space>
        <Table<AiExecutorTaskLogRecord>
          columns={[
            { dataIndex: 'sequence', title: '#', width: 72 },
            { dataIndex: 'level', title: '级别', width: 100, render: (value) => String(value ?? 'info') },
            {
              dataIndex: 'message',
              title: '日志内容',
              render: (value) => (
                <Typography.Text style={{ whiteSpace: 'pre-wrap' }}>
                  {String(value ?? '')}
                </Typography.Text>
              ),
            },
            {
              key: 'created_at',
              title: '时间',
              width: 220,
              render: (_, row) =>
                formatDisplayDateTime(row.created_at ?? String((row as unknown as Record<string, unknown>).timestamp ?? '-')),
            },
          ]}
          dataSource={rows}
          loading={loading}
          pagination={false}
          rowKey={(row) => `${row.sequence ?? row.created_at ?? row.message}-${row.message}`}
          size="small"
        />
      </Space>
    </Modal>
  );
}

export function RunnerApprovalRequestsModal({
  approvingId,
  loading,
  onApprove,
  onClose,
  onRefresh,
  open,
  rows,
}: RunnerApprovalRequestsModalProps) {
  return (
    <Modal
      destroyOnHidden
      footer={(
        <Space>
          <Button onClick={onClose}>关闭</Button>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void onRefresh()}>
            刷新
          </Button>
        </Space>
      )}
      onCancel={onClose}
      open={open}
      title="AI 执行器审批请求"
      width={980}
    >
      <Table<AiExecutorApprovalRequestRecord>
        columns={[
          {
            dataIndex: 'id',
            title: '请求',
            width: 210,
            render: (value, row) => (
              <Space orientation="vertical" size={2}>
                <Typography.Text strong>{approvalRequestTitle(row)}</Typography.Text>
                <Typography.Text code copyable={{ text: String(value ?? '') }}>
                  {String(value ?? '-')}
                </Typography.Text>
              </Space>
            ),
          },
          {
            dataIndex: 'status',
            title: '状态',
            width: 110,
            render: (value) => (
              <Tag color={approvalRequestStatusColor(String(value ?? ''))}>
                {String(value ?? '-')}
              </Tag>
            ),
          },
          {
            key: 'runner',
            title: '执行上下文',
            width: 260,
            render: (_, row) => (
              <Space orientation="vertical" size={2}>
                <Typography.Text>执行器：{row.executor_type ?? '-'}</Typography.Text>
                <Typography.Text type="secondary">Runner：{row.runner_id ?? '-'}</Typography.Text>
                <Typography.Text ellipsis={{ tooltip: row.workspace_root }} type="secondary">
                  工作区：{row.workspace_root ?? '-'}
                </Typography.Text>
              </Space>
            ),
          },
          {
            dataIndex: 'blocked_operations',
            title: '命中风险',
            width: 230,
            render: (value) => Array.isArray(value) && value.length ? (
              <Space size={[4, 4]} wrap>
                {value.map((item) => (
                  <Tag color="red" key={item}>{item}</Tag>
                ))}
              </Space>
            ) : '-',
          },
          {
            dataIndex: 'requested_at',
            title: '申请时间',
            width: 180,
            render: (_, row) => formatDisplayDateTime(row.requested_at ?? row.created_at),
          },
          {
            key: 'actions',
            title: '操作',
            width: 120,
            render: (_, row) => (
              <Button
                aria-label={`审批请求 ${row.id}`}
                disabled={row.status !== 'pending'}
                icon={<CheckCircleOutlined />}
                loading={approvingId === row.id}
                onClick={() => void onApprove(row)}
                type="link"
              >
                审批
              </Button>
            ),
          },
        ]}
        dataSource={rows}
        loading={loading}
        pagination={false}
        rowKey="id"
        scroll={{ x: 1100 }}
        size="small"
      />
    </Modal>
  );
}

export function RunnerTokenRotationNotice({
  onClose,
  token,
}: RunnerTokenRotationNoticeProps) {
  if (!token) {
    return null;
  }
  return (
    <Alert
      closable
      description={(
        <Space orientation="vertical" size={6}>
          <Typography.Text>新 Token 仅本次返回，请同步更新本地 Runner 配置。</Typography.Text>
          <Typography.Text code copyable={{ text: token }}>
            {token}
          </Typography.Text>
        </Space>
      )}
      onClose={onClose}
      showIcon
      style={{ marginTop: 16 }}
      title="Runner Token 已轮换"
      type="success"
    />
  );
}

export function RunnerTokenRotationModal({
  loading,
  onCancel,
  onSubmit,
  runner,
}: RunnerTokenRotationModalProps) {
  return (
    <Modal
      cancelText="取消"
      confirmLoading={loading}
      destroyOnHidden
      okText="确定"
      onCancel={onCancel}
      onOk={() => void onSubmit()}
      open={Boolean(runner)}
      title="轮换 Runner Token"
    >
      <Space orientation="vertical" size={8}>
        <Typography.Text>
          轮换后旧 Token 会立即失效，请将新 Token 配置到本地 Runner。
        </Typography.Text>
        <Typography.Text type="secondary">
          当前执行器：{runner?.name ?? '-'}
        </Typography.Text>
      </Space>
    </Modal>
  );
}

export function PluginActionTrialModal({
  action,
  connectionId,
  connectionOptions,
  inputJson,
  onCreateScheduledJobDraft,
  onConnectionChange,
  onApproveAiExecutor,
  onInputJsonChange,
  onRun,
  onClose,
  open,
  result,
  running,
  sampleResponseSummary,
}: PluginActionTrialModalProps) {
  const dryRunSeed = result?.scheduled_job_dry_run_seed;
  const canCreateScheduledJobDraft = trialSeedCanCreateScheduledJobDraft(result);
  return (
    <Modal
      confirmLoading={running}
      okText="试运行"
      open={open}
      title={`动作试运行${action ? `：${action.name}` : ''}`}
      width={820}
      onCancel={onClose}
      onOk={onRun}
    >
      <Space orientation="vertical" size={12} style={{ width: '100%' }}>
        <Space wrap>
          <Typography.Text strong>连接</Typography.Text>
          <Select
            allowClear
            options={connectionOptions}
            style={{ width: 320 }}
            value={connectionId}
            onChange={onConnectionChange}
          />
        </Space>
        <div>
          <Typography.Text strong>试运行输入 JSON</Typography.Text>
          <Input.TextArea rows={5} value={inputJson} onChange={(event) => onInputJsonChange(event.target.value)} />
        </div>
        {sampleResponseSummary ? (
          <Alert
            description="本次试运行将复用连接测试返回的响应样例，只计算映射命中和写入预览，不再次请求第三方接口。"
            showIcon
            title="使用连接测试响应样例"
            type="info"
          />
        ) : null}
        {result ? (
          <Space orientation="vertical" size={10} style={{ width: '100%' }}>
            <div>
              状态：<Tag color={result.status === 'succeeded' ? 'green' : 'red'}>{result.status}</Tag>
              耗时：{result.latency_ms}ms
            </div>
            {result.error_message ? <Alert title={result.error_message} type="error" /> : null}
            <RunnerApprovalRequestBlock
              action={onApproveAiExecutor && result.error_detail?.approval_request ? (
                <Button loading={running} onClick={() => void onApproveAiExecutor()} type="primary">
                  审批并重新试运行
                </Button>
              ) : undefined}
              value={result.error_detail?.approval_request}
            />
            {dryRunSeed ? (
              <Alert
                action={canCreateScheduledJobDraft ? (
                  <Button
                    href="/tasks/scheduled-jobs?tab=jobs"
                    size="small"
                    type="primary"
                    onClick={(event) => {
                      event.preventDefault();
                      onCreateScheduledJobDraft?.();
                    }}
                  >
                    生成作业草稿
                  </Button>
                ) : undefined}
                description={(
                  <Space orientation="vertical" size={6} style={{ width: '100%' }}>
                    <Typography.Text>
                      {canCreateScheduledJobDraft
                        ? '本次响应已生成定时作业试运行种子，后续可复用连接、输入映射和写入预览来创建作业。'
                        : '本次动作试运行还不能生成作业草稿，请先处理缺失项后重新试运行。'}
                    </Typography.Text>
                    <ReuseWizardSummary value={dryRunSeed.reuse_wizard} />
                  </Space>
                )}
                showIcon
                title={canCreateScheduledJobDraft ? '可复用到定时作业 dry-run' : '动作试运行未就绪'}
                type={canCreateScheduledJobDraft ? 'success' : 'warning'}
              />
            ) : null}
            <Typography.Text strong>请求预览</Typography.Text>
            <pre style={{ background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, whiteSpace: 'pre-wrap' }}>
              {compactJson(result.request_preview)}
            </pre>
            <Typography.Text strong>结果映射命中</Typography.Text>
            <Table
              columns={[
                { dataIndex: 'key', title: '字段' },
                { dataIndex: 'path', title: 'JSONPath' },
                { dataIndex: 'matched', title: '命中', render: (value: boolean) => <Tag color={value ? 'green' : 'red'}>{value ? '是' : '否'}</Tag> },
                { dataIndex: 'value_preview', title: '值预览', ellipsis: true, render: (value: unknown) => compactJson(value) },
              ]}
              dataSource={result.mapping_hits ?? []}
              pagination={false}
              rowKey="key"
              size="small"
            />
            <TrialWritePreviewBlock value={result.write_preview} />
            <Typography.Text strong>响应摘要</Typography.Text>
            <pre style={{ background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, whiteSpace: 'pre-wrap' }}>
              {compactJson(result.response_summary)}
            </pre>
          </Space>
        ) : null}
      </Space>
    </Modal>
  );
}
