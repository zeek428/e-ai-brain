import { Modal, Space, Typography, message, type FormInstance } from 'antd';
import { useState } from 'react';

import {
  cancelAiExecutorTask,
  createAiExecutorRunner,
  deleteAiExecutorRunner,
  downloadAiExecutorRunnerInstallPackage,
  fetchAiExecutorTaskLogs,
  retryAiExecutorTask,
  rotateAiExecutorRunnerToken,
  testAiExecutorRunner,
  updateAiExecutorRunner,
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
  const [testingRunnerId, setTestingRunnerId] = useState<string | undefined>();

  const openCreateRunnerModal = () => {
    setEditingRunner(undefined);
    runnerForm.resetFields();
    runnerForm.setFieldsValue({
      claude_command: 'claude',
      codex_command: 'codex',
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
      claude_command: executorCommands.claude || 'claude',
      codex_command: executorCommands.codex || 'codex',
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
      if (result.status === 'succeeded') {
        message.success({
          content: `执行器测试通过，耗时 ${result.latency_ms ?? '-'}ms`,
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

  return {
    cancelRunnerTask,
    closeRotatedRunnerToken: () => setRotatedRunnerToken(undefined),
    closeRunnerLogModal: () => setRunnerLogModalOpen(false),
    closeRunnerModal,
    confirmDeleteRunner,
    copyRunnerSetupCommand,
    downloadRunnerInstallPackage,
    editingRunner,
    openCreateRunnerModal,
    openEditRunnerModal,
    openRunnerLogs,
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
    runRunnerTest,
    submitRotateRunnerToken,
    submitRunner,
    testingRunnerId,
    cancelRotateRunnerToken: () => setRotatingRunner(undefined),
  };
}
