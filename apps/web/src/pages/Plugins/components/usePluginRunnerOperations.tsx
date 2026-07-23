import { Modal, Space, Typography, message, type FormInstance } from 'antd';
import { useState } from 'react';

import {
  approveAiExecutorApprovalRequest,
  cancelAiExecutorTask,
  createAiExecutorRunner,
  deleteAiExecutorRunner,
  downloadAiExecutorRunnerInstallPackage,
  fetchAiExecutorApprovalRequestsPage,
  fetchAiExecutorTaskLogs,
  retryAiExecutorTask,
  rotateAiExecutorRunnerToken,
  testAiExecutorRunner,
  timeoutAiExecutorTasks,
  updateAiExecutorRunner,
  type AiExecutorApprovalRequestRecord,
  type AiExecutorRunnerRecord,
  type AiExecutorRunnerTestResult,
  type AiExecutorTaskLogRecord,
  type AiExecutorTaskRecord,
} from '../../../services/aiBrain';
import {
  arrayToLines,
  runnerPayload,
  stableJson,
} from './pluginFormTransformHelpers';
import {
  runnerExecutorCommandsFromMetadata,
  runnerPackageOptionsFromMetadata,
  type AiExecutorRunnerFormValues,
} from './pluginRunnerHelpers';
import { RunnerTestDiagnosticsContent } from './PluginDiagnostics';
import { PluginRunnerTimeoutScanResultContent } from './PluginRunnerTimeoutScanResultContent';

function defaultRunnerEndpoint() {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000/api/system/ai-executor-runners';
  }
  return `${window.location.origin.replace(/:\d+$/, ':8000')}/api/system/ai-executor-runners`;
}

function latestRunnerTaskId(runner: AiExecutorRunnerRecord): string | undefined {
  const metadataTaskId = runner.metadata?.latest_task_id;
  return runner.latest_task_id ?? (typeof metadataTaskId === 'string' ? metadataTaskId : undefined);
}

export function usePluginRunnerOperations({
  reload,
  runnerForm,
}: {
  reload: () => Promise<void>;
  runnerForm: FormInstance<AiExecutorRunnerFormValues>;
}) {
  const [runnerModalOpen, setRunnerModalOpen] = useState(false);
  const [editingRunner, setEditingRunner] = useState<AiExecutorRunnerRecord | undefined>();
  const [rotatingRunner, setRotatingRunner] = useState<AiExecutorRunnerRecord | undefined>();
  const [rotatingRunnerLoading, setRotatingRunnerLoading] = useState(false);
  const [rotatedRunnerToken, setRotatedRunnerToken] = useState<string | undefined>();
  const [runnerLogModalOpen, setRunnerLogModalOpen] = useState(false);
  const [runnerLogLoading, setRunnerLogLoading] = useState(false);
  const [runnerLogTask, setRunnerLogTask] = useState<AiExecutorTaskRecord | undefined>();
  const [runnerLogRows, setRunnerLogRows] = useState<AiExecutorTaskLogRecord[]>([]);
  const [scanningRunnerTimeouts, setScanningRunnerTimeouts] = useState(false);
  const [testingRunnerId, setTestingRunnerId] = useState<string | undefined>();
  const [runnerApprovalRequestsOpen, setRunnerApprovalRequestsOpen] = useState(false);
  const [runnerApprovalRequestsLoading, setRunnerApprovalRequestsLoading] = useState(false);
  const [runnerApprovalRequestRows, setRunnerApprovalRequestRows] = useState<AiExecutorApprovalRequestRecord[]>([]);
  const [approvingRunnerApprovalRequestId, setApprovingRunnerApprovalRequestId] = useState<string | undefined>();

  const openCreateRunnerModal = () => {
    setEditingRunner(undefined);
    runnerForm.resetFields();
    runnerForm.setFieldsValue({
      attestation_status: 'pending',
      claude_command: 'claude',
      codex_command: 'codex',
      deployment_capability: false,
      endpoint_url: defaultRunnerEndpoint(),
      executor_types: ['codex', 'openclaw'],
      hermes_command: 'hermes',
      heartbeat_timeout_seconds: 120,
      install_mode: 'systemd',
      max_concurrent_tasks: 1,
      metadata: '{}',
      openclaw_command: 'openclaw',
      package_arch: 'amd64',
      protocol: 'runner_polling',
      status: 'active',
      target_os: 'linux',
      trust_boundary_id: '',
      trust_domain: 'coding',
      workspace_roots: '/Users/zeek/source/e-ai-brain',
    });
    setRunnerModalOpen(true);
  };

  const openEditRunnerModal = (runner: AiExecutorRunnerRecord) => {
    setEditingRunner(runner);
    runnerForm.resetFields();
    const executorCommands = runnerExecutorCommandsFromMetadata(runner.metadata);
    const packageOptions = runnerPackageOptionsFromMetadata(runner.metadata);
    runnerForm.setFieldsValue({
      attestation_status: runner.attestation_status ?? 'pending',
      claude_command: executorCommands.claude || 'claude',
      codex_command: executorCommands.codex || 'codex',
      deployment_capability: (runner.capabilities ?? []).includes('deployment'),
      endpoint_url: runner.endpoint_url ?? 'runner://local',
      executor_types: runner.executor_types ?? ['codex'],
      hermes_command: executorCommands.hermes || 'hermes',
      heartbeat_timeout_seconds: runner.heartbeat_timeout_seconds ?? 120,
      install_mode: packageOptions.install_mode,
      max_concurrent_tasks: runner.max_concurrent_tasks ?? 1,
      metadata: stableJson(runner.metadata ?? {}),
      name: runner.name,
      openclaw_command: executorCommands.openclaw || 'openclaw',
      package_arch: packageOptions.arch,
      protocol: runner.protocol ?? 'runner_polling',
      status: runner.status,
      target_os: packageOptions.target_os,
      trust_boundary_id: runner.trust_boundary_id ?? '',
      trust_domain: runner.trust_domain ?? 'coding',
      workspace_roots: arrayToLines(runner.workspace_roots),
    });
    setRunnerModalOpen(true);
  };

  const closeRunnerModal = () => {
    setRunnerModalOpen(false);
    setEditingRunner(undefined);
    runnerForm.resetFields();
  };

  const submitRunner = async () => {
    const values = await runnerForm.validateFields();
    const payload = runnerPayload(values);
    if (editingRunner) {
      await updateAiExecutorRunner(editingRunner.id, payload);
      message.success('执行器已更新');
    } else {
      const created = await createAiExecutorRunner(payload);
      message.success('执行器已创建');
      if (created.runner_token) {
        Modal.info({
          content: (
            <Space orientation="vertical" size={8}>
              <Typography.Text>Runner Token 仅在创建时返回，请配置到本地 Runner。</Typography.Text>
              <Typography.Text code copyable={{ text: created.runner_token }}>
                {created.runner_token}
              </Typography.Text>
            </Space>
          ),
          title: 'Runner Token',
        });
      }
    }
    closeRunnerModal();
    await reload();
  };

  const confirmDeleteRunner = (runner: AiExecutorRunnerRecord) => {
    Modal.confirm({
      content: `确定删除执行器「${runner.name}」吗？有未完成任务时后端会拒绝删除。`,
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteAiExecutorRunner(runner.id);
          message.success('执行器已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '执行器删除失败');
        }
      },
      title: '删除执行器',
    });
  };

  const rotateRunnerToken = (runner: AiExecutorRunnerRecord) => {
    setRotatingRunner(runner);
  };

  const downloadRunnerInstallPackage = async (runner: AiExecutorRunnerRecord) => {
    try {
      const { blob, filename } = await downloadAiExecutorRunnerInstallPackage(
        runner.id,
        runnerPackageOptionsFromMetadata(runner.metadata),
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      message.success('Runner 安装包已生成');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Runner 安装包下载失败');
    }
  };

  const copyRunnerSetupCommand = async (command: string) => {
    try {
      await navigator.clipboard.writeText(command);
      message.success('启动命令已复制');
    } catch {
      message.error('启动命令复制失败');
    }
  };

  const submitRotateRunnerToken = async () => {
    if (!rotatingRunner) {
      return;
    }
    setRotatingRunnerLoading(true);
    try {
      const updatedRunner = await rotateAiExecutorRunnerToken(rotatingRunner.id);
      message.success('Runner Token 已轮换');
      setRotatingRunner(undefined);
      if (updatedRunner.runner_token) {
        setRotatedRunnerToken(updatedRunner.runner_token);
      }
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Runner Token 轮换失败');
    } finally {
      setRotatingRunnerLoading(false);
    }
  };

  const openRunnerLogs = async (runner: AiExecutorRunnerRecord) => {
    const taskId = latestRunnerTaskId(runner);
    if (!taskId) {
      message.warning('当前执行器暂无可查看的任务日志');
      return;
    }
    setRunnerLogModalOpen(true);
    setRunnerLogLoading(true);
    try {
      const result = await fetchAiExecutorTaskLogs(taskId);
      setRunnerLogTask(result.task);
      setRunnerLogRows(result.logs ?? []);
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Runner 执行日志加载失败');
    } finally {
      setRunnerLogLoading(false);
    }
  };

  const cancelRunnerTask = async () => {
    if (!runnerLogTask?.id) {
      return;
    }
    setRunnerLogLoading(true);
    try {
      const result = await cancelAiExecutorTask(
        runnerLogTask.id,
        '管理员从插件管理页面取消 Runner 任务',
      );
      setRunnerLogTask(result.task);
      message.success('Runner 任务已取消');
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Runner 任务取消失败');
    } finally {
      setRunnerLogLoading(false);
    }
  };

  const retryRunnerTask = async () => {
    if (!runnerLogTask?.id) {
      return;
    }
    setRunnerLogLoading(true);
    try {
      const result = await retryAiExecutorTask(
        runnerLogTask.id,
        '管理员从插件管理页面重试 Runner 任务',
      );
      setRunnerLogTask(result.task);
      setRunnerLogRows(result.task.logs ?? []);
      message.success('Runner 任务已重新入队');
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Runner 任务重试失败');
    } finally {
      setRunnerLogLoading(false);
    }
  };

  const openRunnerTestDiagnostics = (
    runner: AiExecutorRunnerRecord,
    result: AiExecutorRunnerTestResult,
  ) => {
    Modal.info({
      content: <RunnerTestDiagnosticsContent result={result} runner={runner} />,
      title: '执行器测试诊断',
      width: 820,
    });
  };

  const runRunnerTest = async (runner: AiExecutorRunnerRecord) => {
    if (testingRunnerId) {
      return;
    }
    const messageKey = `ai-executor-runner-test-${runner.id}`;
    setTestingRunnerId(runner.id);
    message.loading({
      content: `正在测试执行器「${runner.name}」，请稍候...`,
      duration: 0,
      key: messageKey,
    });
    try {
      const result = await testAiExecutorRunner(runner.id);
      openRunnerTestDiagnostics(runner, result);
      const probeCount = result.probe_tasks?.length ?? 0;
      if (result.status === 'succeeded') {
        message.success({
          content: probeCount > 0
            ? `已下发 ${probeCount} 个真实连通性探测任务，请等待 Runner 回传结果`
            : `执行器测试通过，耗时 ${result.latency_ms ?? '-'}ms`,
          duration: 3,
          key: messageKey,
        });
      } else {
        message.error({
          content: '执行器测试未通过，请查看诊断详情',
          duration: 5,
          key: messageKey,
        });
      }
    } catch (error) {
      message.error({
        content: error instanceof Error ? error.message : '执行器测试失败',
        duration: 5,
        key: messageKey,
      });
    } finally {
      setTestingRunnerId(undefined);
    }
  };

  const refreshRunnerApprovalRequests = async () => {
    setRunnerApprovalRequestsLoading(true);
    try {
      const result = await fetchAiExecutorApprovalRequestsPage({
        page: 1,
        pageSize: 20,
        sortField: 'updated_at',
        sortOrder: 'descend',
        status: 'pending',
      });
      setRunnerApprovalRequestRows(result.rows);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '审批请求加载失败');
    } finally {
      setRunnerApprovalRequestsLoading(false);
    }
  };

  const openRunnerApprovalRequests = async () => {
    setRunnerApprovalRequestsOpen(true);
    await refreshRunnerApprovalRequests();
  };

  const approveRunnerApprovalRequest = async (record: AiExecutorApprovalRequestRecord) => {
    if (approvingRunnerApprovalRequestId) {
      return;
    }
    setApprovingRunnerApprovalRequestId(record.id);
    try {
      await approveAiExecutorApprovalRequest(record.id, {
        reason: '管理员从插件管理执行器页审批放行',
      });
      message.success('审批请求已放行');
      await refreshRunnerApprovalRequests();
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '审批请求放行失败');
    } finally {
      setApprovingRunnerApprovalRequestId(undefined);
    }
  };

  const scanRunnerTimeouts = async () => {
    if (scanningRunnerTimeouts) {
      return;
    }
    const messageKey = 'ai-executor-timeout-scan';
    setScanningRunnerTimeouts(true);
    message.loading({
      content: '正在扫描 Runner 超时和租约过期任务...',
      duration: 0,
      key: messageKey,
    });
    try {
      const result = await timeoutAiExecutorTasks();
      Modal.info({
        content: <PluginRunnerTimeoutScanResultContent result={result} />,
        title: 'Runner 超时扫描',
        width: 760,
      });
      const affected = result.summary?.total_affected ?? 0;
      if (result.summary?.manual_attention_required) {
        message.warning({
          content: result.summary.message,
          duration: 5,
          key: messageKey,
        });
      } else if (affected > 0) {
        message.success({
          content: result.summary?.message ?? `已处理 ${affected} 个 Runner 任务`,
          duration: 4,
          key: messageKey,
        });
      } else {
        message.info({
          content: result.summary?.message ?? '未发现需要处理的 Runner 任务',
          duration: 3,
          key: messageKey,
        });
      }
      await reload();
    } catch (error) {
      message.error({
        content: error instanceof Error ? error.message : 'Runner 超时扫描失败',
        duration: 5,
        key: messageKey,
      });
    } finally {
      setScanningRunnerTimeouts(false);
    }
  };

  return {
    cancelRunnerTask,
    approveRunnerApprovalRequest,
    closeRotatedRunnerToken: () => setRotatedRunnerToken(undefined),
    closeRunnerApprovalRequests: () => setRunnerApprovalRequestsOpen(false),
    closeRunnerLogModal: () => setRunnerLogModalOpen(false),
    closeRunnerModal,
    confirmDeleteRunner,
    copyRunnerSetupCommand,
    downloadRunnerInstallPackage,
    editingRunner,
    openCreateRunnerModal,
    openEditRunnerModal,
    openRunnerApprovalRequests,
    openRunnerLogs,
    refreshRunnerApprovalRequests,
    retryRunnerTask,
    rotateRunnerToken,
    rotatedRunnerToken,
    rotatingRunner,
    rotatingRunnerLoading,
    runnerLogLoading,
    runnerLogModalOpen,
    runnerLogRows,
    runnerLogTask,
    runnerModalOpen,
    runnerApprovalRequestRows,
    runnerApprovalRequestsLoading,
    runnerApprovalRequestsOpen,
    runRunnerTest,
    scanRunnerTimeouts,
    scanningRunnerTimeouts,
    submitRotateRunnerToken,
    submitRunner,
    testingRunnerId,
    approvingRunnerApprovalRequestId,
    cancelRotateRunnerToken: () => setRotatingRunner(undefined),
  };
}
