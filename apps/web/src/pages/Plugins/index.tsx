import { PageContainer } from '@ant-design/pro-components';
import { Form, Modal, Space, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
  ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
  assistantScopedStorageKey,
  confirmAssistantActionDraft,
  createAiExecutorRunner,
  copyPlugin,
  createPlugin,
  createPluginAction,
  createPluginConnection,
  cancelAiExecutorTask,
  deletePlugin,
  deletePluginAction,
  deletePluginConnection,
  deleteAiExecutorRunner,
  downloadAiExecutorRunnerInstallPackage,
  fetchAiExecutorTaskLogs,
  fetchAiExecutorRunners,
  fetchPluginActions,
  fetchPluginActionTemplates,
  fetchPluginConnections,
  fetchPluginMarketplace,
  fetchPlugins,
  fetchResultWriteTargets,
  fetchScheduledJobs,
  invokePluginAction,
  rememberAssistantDraftResolution,
  rotateAiExecutorRunnerToken,
  testAiExecutorRunner,
  testPluginConnection,
  trialPluginAction,
  updateAssistantActionDraft,
  updateAiExecutorRunner,
  updatePlugin,
  updatePluginAction,
  updatePluginConnection,
  type AssistantPluginActionDraft,
  type AssistantPluginConnectionDraft,
  type AiExecutorTaskLogRecord,
  type AiExecutorTaskRecord,
  type AiExecutorRunnerRecord,
  type AiExecutorRunnerTestResult,
  type PluginActionTrialResult,
  type PluginActionRecord,
  type PluginActionTemplateRecord,
  type PluginConnectionRecord,
  type PluginConnectionTestResult,
  type PluginMarketplaceItem,
  type PluginRecord,
  type ResultWriteTargetRecord,
  type ScheduledJobRecord,
} from '../../services/aiBrain';
import {
  type PluginConnectionFormValues,
} from './components/PluginConnectionModal';
import {
  type PluginActionFormValues,
} from './components/PluginActionModal';
import type { PluginFormValues } from './components/PluginModal';
import { PluginManagementModals } from './components/PluginManagementModals';
import { PluginManagementTabs } from './components/PluginManagementTabs';
import {
  PluginConnectionTestDiagnosticsContent,
  RunnerTestDiagnosticsContent,
} from './components/PluginDiagnostics';
import {
  runnerExecutorCommandsFromMetadata,
  runnerPackageOptionsFromMetadata,
  type AiExecutorRunnerFormValues,
} from './components/pluginRunnerHelpers';
import {
  DEFAULT_RESULT_WRITE_TARGET,
  MAXCOMPUTE_DEFAULT_FIELDS,
  MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO,
  actionScenarioForExistingAction,
  arrayToLines,
  buildActionPayload,
  buildActionRequestPreview,
  buildConnectionAuthConfig,
  buildConnectionPayload,
  buildConnectionRequestConfig,
  buildMaxComputeRequestConfig,
  buildVisualRequestConfig,
  buildVisualResultMapping,
  configSection,
  defaultResultMappingForWriteTarget,
  endpointUrlFromSchemaValues,
  isFormValidationError,
  isPlainRecord,
  mergeWriteTarget,
  numberValue,
  parseJsonObject,
  pluginActionDraftFormValues,
  pluginAssistantDraftModifiedFields,
  pluginConnectionDraftFormValues,
  pluginConnectionTemplateFormValues,
  recordToRows,
  resultMappingVisualFields,
  resultWriteTargetLabel,
  runnerPayload,
  schemaManagedRequestKeys,
  schemaValuesFromPayload,
  stableJson,
  stringValue,
} from './components/pluginFormTransformHelpers';
import { PluginWorkspaceGuide } from './components/PluginWorkspaceGuide';
import { SYSTEM_VARIABLE_OPTIONS } from './components/pluginSystemVariableOptions';
import {
  actionDeleteUsageGroups,
  connectionDeleteUsageGroups,
  deleteUsageContent,
  hasDeleteUsage,
  pluginDeleteUsageGroups,
  type DeleteUsageGroup,
} from './components/pluginDeleteUsageHelpers';

type ConnectionFormValues = PluginConnectionFormValues;

type ActionFormValues = PluginActionFormValues;

const connectionEnvironmentOptions = [
  { label: '默认', value: 'default' },
  { label: '开发', value: 'dev' },
  { label: '测试', value: 'test' },
  { label: '预发 / Staging', value: 'staging' },
  { label: '生产', value: 'prod' },
  { label: '沙箱', value: 'sandbox' },
];

const connectionEnvironmentLabelByValue = new Map(
  connectionEnvironmentOptions.map((option) => [option.value, option.label]),
);

export default function PluginsPage() {
  const [pluginForm] = Form.useForm<PluginFormValues>();
  const [connectionForm] = Form.useForm<ConnectionFormValues>();
  const [actionForm] = Form.useForm<ActionFormValues>();
  const [runnerForm] = Form.useForm<AiExecutorRunnerFormValues>();
  const [plugins, setPlugins] = useState<PluginRecord[]>([]);
  const [marketplaceItems, setMarketplaceItems] = useState<PluginMarketplaceItem[]>([]);
  const [actionTemplates, setActionTemplates] = useState<PluginActionTemplateRecord[]>([]);
  const [resultWriteTargets, setResultWriteTargets] = useState<ResultWriteTargetRecord[]>([]);
  const [runners, setRunners] = useState<AiExecutorRunnerRecord[]>([]);
  const [connections, setConnections] = useState<PluginConnectionRecord[]>([]);
  const [actions, setActions] = useState<PluginActionRecord[]>([]);
  const [scheduledJobs, setScheduledJobs] = useState<ScheduledJobRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [pluginModalOpen, setPluginModalOpen] = useState(false);
  const [connectionModalOpen, setConnectionModalOpen] = useState(false);
  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [runnerModalOpen, setRunnerModalOpen] = useState(false);
  const [connectionSubmitAction, setConnectionSubmitAction] = useState<'save' | 'save-test'>();
  const [editingPlugin, setEditingPlugin] = useState<PluginRecord | undefined>();
  const [editingConnection, setEditingConnection] = useState<PluginConnectionRecord | undefined>();
  const [editingAction, setEditingAction] = useState<PluginActionRecord | undefined>();
  const [editingRunner, setEditingRunner] = useState<AiExecutorRunnerRecord | undefined>();
  const [rotatingRunner, setRotatingRunner] = useState<AiExecutorRunnerRecord | undefined>();
  const [rotatingRunnerLoading, setRotatingRunnerLoading] = useState(false);
  const [rotatedRunnerToken, setRotatedRunnerToken] = useState<string | undefined>();
  const [runnerLogModalOpen, setRunnerLogModalOpen] = useState(false);
  const [runnerLogLoading, setRunnerLogLoading] = useState(false);
  const [runnerLogTask, setRunnerLogTask] = useState<AiExecutorTaskRecord | undefined>();
  const [runnerLogRows, setRunnerLogRows] = useState<AiExecutorTaskLogRecord[]>([]);
  const [assistantConnectionDraftSource, setAssistantConnectionDraftSource] = useState<
    { draftId?: string; payload: Record<string, unknown>; title?: string } | undefined
  >();
  const [assistantActionDraftSource, setAssistantActionDraftSource] = useState<
    { draftId?: string; payload: Record<string, unknown>; title?: string } | undefined
  >();
  const [trialModalOpen, setTrialModalOpen] = useState(false);
  const [trialAction, setTrialAction] = useState<PluginActionRecord | undefined>();
  const [trialConnectionId, setTrialConnectionId] = useState<string | undefined>();
  const [trialInputJson, setTrialInputJson] = useState('{}');
  const [trialResult, setTrialResult] = useState<PluginActionTrialResult | undefined>();
  const [trialRunning, setTrialRunning] = useState(false);
  const [actionScenario, setActionScenario] = useState<string | undefined>();
  const [connectionEnvironmentFilter, setConnectionEnvironmentFilter] = useState<string | undefined>();
  const [advancedConnectionJsonOpen, setAdvancedConnectionJsonOpen] = useState(false);
  const [advancedConnectionRequestJsonOpen, setAdvancedConnectionRequestJsonOpen] = useState(false);
  const [advancedActionJsonOpen, setAdvancedActionJsonOpen] = useState(false);
  const [testingConnectionId, setTestingConnectionId] = useState<string | undefined>();
  const [testingRunnerId, setTestingRunnerId] = useState<string | undefined>();
  const selectedConnectionAuthType = Form.useWatch('auth_type', connectionForm);
  const selectedConnectionPluginId = Form.useWatch('plugin_id', connectionForm);
  const actionFormValues = Form.useWatch([], actionForm) as ActionFormValues | undefined;

  const pluginOptions = useMemo(
    () => plugins.map((plugin) => ({ label: `${plugin.name} (${plugin.protocol})`, value: plugin.id })),
    [plugins],
  );
  const connectionOptions = useMemo(
    () =>
      connections.map((connection) => ({
        label: `${connection.name} (${connection.environment ?? 'default'})`,
        value: connection.id,
      })),
    [connections],
  );
  const connectionById = useMemo(
    () => new Map(connections.map((connection) => [connection.id, connection])),
    [connections],
  );
  const pluginById = useMemo(() => new Map(plugins.map((plugin) => [plugin.id, plugin])), [plugins]);
  const marketplaceItemByPluginCode = useMemo(
    () => new Map(marketplaceItems.map((item) => [item.code, item])),
    [marketplaceItems],
  );
  const marketplaceItemByPluginId = useMemo(
    () => new Map(
      marketplaceItems
        .filter((item) => item.plugin_id)
        .map((item) => [String(item.plugin_id), item]),
    ),
    [marketplaceItems],
  );
  const selectedConnectionPlugin = selectedConnectionPluginId
    ? pluginById.get(String(selectedConnectionPluginId))
    : undefined;
  const selectedConnectionPluginCode = selectedConnectionPlugin?.code;
  const selectedConnectionIsGithub = selectedConnectionPluginCode === 'github';
  const selectedConnectionIsGitlab = selectedConnectionPluginCode === 'gitlab';
  const selectedConnectionMarketplaceItem = selectedConnectionPlugin
    ? marketplaceItemByPluginCode.get(selectedConnectionPlugin.code)
      ?? marketplaceItemByPluginId.get(selectedConnectionPlugin.id)
    : undefined;
  const selectedConnectionSchema = selectedConnectionMarketplaceItem?.connection_schema;
  const actionTemplateOptions = useMemo(
    () => actionTemplates.map((template) => ({ label: template.name, value: template.code })),
    [actionTemplates],
  );
  const resultWriteTargetOptions = useMemo(
    () => resultWriteTargets.map((target) => ({
      label: target.form_label || target.label,
      value: target.code,
    })),
    [resultWriteTargets],
  );
  const requestPreview = useMemo(
    () => buildActionRequestPreview(actionFormValues, connectionById.get(actionFormValues?.connection_id ?? '')),
    [actionFormValues, connectionById],
  );
  const connectionDefaultsForPlugin = useCallback((plugin?: PluginRecord) => {
    const item = plugin
      ? marketplaceItemByPluginCode.get(plugin.code) ?? marketplaceItemByPluginId.get(plugin.id)
      : undefined;
    return pluginConnectionTemplateFormValues(item, { pluginId: plugin?.id });
  }, [marketplaceItemByPluginCode, marketplaceItemByPluginId]);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [
        nextPlugins,
        nextMarketplaceItems,
        nextActionTemplates,
        nextResultWriteTargets,
        nextRunners,
        nextConnections,
        nextActions,
        nextJobs,
      ] = await Promise.all([
        fetchPlugins(),
        fetchPluginMarketplace(),
        fetchPluginActionTemplates(),
        fetchResultWriteTargets(),
        fetchAiExecutorRunners(),
        fetchPluginConnections({ environment: connectionEnvironmentFilter }),
        fetchPluginActions(),
        fetchScheduledJobs(),
      ]);
      setPlugins(nextPlugins);
      setMarketplaceItems(nextMarketplaceItems);
      setActionTemplates(nextActionTemplates);
      setResultWriteTargets(nextResultWriteTargets);
      setRunners(nextRunners);
      setConnections(nextConnections);
      setActions(nextActions);
      setScheduledJobs(nextJobs);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '插件配置加载失败');
    } finally {
      setLoading(false);
    }
  }, [connectionEnvironmentFilter]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [reload]);

  const openCreatePluginModal = () => {
    setEditingPlugin(undefined);
    pluginForm.resetFields();
    pluginForm.setFieldsValue({
      category: 'general',
      protocol: 'http',
      risk_level: 'medium',
      status: 'active',
    });
    setPluginModalOpen(true);
  };

  const openEditPluginModal = (plugin: PluginRecord) => {
    if (plugin.is_system) {
      message.info('官方标准插件不能修改，请在连接里维护接入参数');
      return;
    }
    setEditingPlugin(plugin);
    pluginForm.resetFields();
    pluginForm.setFieldsValue({
      category: plugin.category ?? 'general',
      code: plugin.code,
      description: plugin.description ?? undefined,
      name: plugin.name,
      protocol: plugin.protocol,
      risk_level: plugin.risk_level ?? 'medium',
      status: plugin.status,
    });
    setPluginModalOpen(true);
  };

  const closePluginModal = () => {
    setPluginModalOpen(false);
    setEditingPlugin(undefined);
    pluginForm.resetFields();
  };

  const submitPlugin = async () => {
    const values = await pluginForm.validateFields();
    if (editingPlugin) {
      await updatePlugin(editingPlugin.id, values);
      message.success('插件已更新');
    } else {
      await createPlugin(values);
      message.success('插件已创建');
    }
    closePluginModal();
    await reload();
  };

  const copyOfficialPlugin = async (plugin: PluginRecord) => {
    await copyPlugin(plugin.id, {
      code: `${plugin.code}_custom`,
      name: `${plugin.name} 副本`,
    });
    message.success('官方插件已复制为自定义插件');
    await reload();
  };

  const openCreateRunnerModal = () => {
    setEditingRunner(undefined);
    runnerForm.resetFields();
    runnerForm.setFieldsValue({
      claude_command: 'claude',
      codex_command: 'codex',
      endpoint_url: `${window.location.origin.replace(/:\d+$/, ':8000')}/api/system/ai-executor-runners`,
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

  const latestRunnerTaskId = (runner: AiExecutorRunnerRecord): string | undefined => {
    const metadataTaskId = runner.metadata?.latest_task_id;
    return runner.latest_task_id ?? (typeof metadataTaskId === 'string' ? metadataTaskId : undefined);
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

  const warnDeleteUsage = (title: string, groups: DeleteUsageGroup[]) => {
    Modal.warning({
      content: deleteUsageContent(groups),
      okText: '知道了',
      title,
      width: 640,
    });
  };

  const confirmDeletePlugin = (plugin: PluginRecord) => {
    if (plugin.is_system) {
      message.info('官方标准插件不能删除，请在连接里维护接入参数');
      return;
    }
    const usageGroups = pluginDeleteUsageGroups({ actions, connections, plugin, scheduledJobs });
    if (hasDeleteUsage(usageGroups)) {
      warnDeleteUsage(`插件「${plugin.name}」正在使用中`, usageGroups);
      return;
    }
    Modal.confirm({
      cancelText: '取消',
      content: `确定删除插件「${plugin.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      title: '删除插件',
      onOk: async () => {
        try {
          await deletePlugin(plugin.id);
          message.success('插件已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '插件删除失败');
        }
      },
    });
  };

  const confirmDeleteConnection = (connection: PluginConnectionRecord) => {
    const usageGroups = connectionDeleteUsageGroups({ actions, connection, scheduledJobs });
    if (hasDeleteUsage(usageGroups)) {
      warnDeleteUsage(`连接「${connection.name}」正在使用中`, usageGroups);
      return;
    }
    Modal.confirm({
      cancelText: '取消',
      content: `确定删除连接「${connection.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      title: '删除连接',
      onOk: async () => {
        try {
          await deletePluginConnection(connection.id);
          message.success('连接已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '连接删除失败');
        }
      },
    });
  };

  const confirmDeleteAction = (action: PluginActionRecord) => {
    const usageGroups = actionDeleteUsageGroups({ action, scheduledJobs });
    if (hasDeleteUsage(usageGroups)) {
      warnDeleteUsage(`动作「${action.name}」正在使用中`, usageGroups);
      return;
    }
    Modal.confirm({
      cancelText: '取消',
      content: `确定删除动作「${action.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      title: '删除动作',
      onOk: async () => {
        try {
          await deletePluginAction(action.id);
          message.success('动作已删除');
          await reload();
        } catch (error) {
          message.error(error instanceof Error ? error.message : '动作删除失败');
        }
      },
    });
  };

  const openCreateConnectionModal = useCallback(() => {
    setEditingConnection(undefined);
    setAssistantConnectionDraftSource(undefined);
    setAdvancedConnectionJsonOpen(false);
    setAdvancedConnectionRequestJsonOpen(false);
    connectionForm.resetFields();
    const defaultPlugin = plugins[0];
    const defaults = connectionDefaultsForPlugin(defaultPlugin);
    connectionForm.setFieldsValue({
      auth_type: 'none',
      environment: 'default',
      max_retries: 0,
      plugin_id: defaultPlugin?.id,
      status: 'active',
      timeout_seconds: 30,
      ...defaults,
    });
    setConnectionModalOpen(true);
  }, [connectionDefaultsForPlugin, connectionForm, plugins]);

  const openCreateConnectionForPlugin = (pluginId?: string | null) => {
    setEditingConnection(undefined);
    setAssistantConnectionDraftSource(undefined);
    setAdvancedConnectionJsonOpen(false);
    setAdvancedConnectionRequestJsonOpen(false);
    connectionForm.resetFields();
    const plugin = pluginId ? pluginById.get(pluginId) : undefined;
    const defaults = connectionDefaultsForPlugin(plugin);
    connectionForm.setFieldsValue({
      auth_type: 'none',
      environment: 'default',
      max_retries: 0,
      plugin_id: pluginId ?? undefined,
      status: 'active',
      timeout_seconds: 30,
      ...defaults,
      ...(plugin && !defaults?.name ? { name: `${plugin.name} 连接` } : {}),
    });
    setConnectionModalOpen(true);
  };

  const openEditConnectionModal = (connection: PluginConnectionRecord) => {
    const authConfig = connection.auth_config ?? {};
    const requestConfig = connection.request_config ?? {};
    const plugin = pluginById.get(connection.plugin_id);
    const schema = plugin
      ? marketplaceItemByPluginCode.get(plugin.code)?.connection_schema
        ?? marketplaceItemByPluginId.get(plugin.id)?.connection_schema
      : undefined;
    setEditingConnection(connection);
    setAssistantConnectionDraftSource(undefined);
    setAdvancedConnectionJsonOpen(false);
    setAdvancedConnectionRequestJsonOpen(false);
    connectionForm.resetFields();
    connectionForm.setFieldsValue({
      auth_config: stableJson(authConfig),
      auth_type: connection.auth_type ?? 'none',
      connection_header_rows: recordToRows(
        configSection(requestConfig, 'headers'),
        schemaManagedRequestKeys(schema, 'headers'),
      ),
      connection_param_rows: recordToRows(
        configSection(requestConfig, 'query'),
        schemaManagedRequestKeys(schema, 'query'),
      ),
      endpoint_url: connection.endpoint_url,
      environment: connection.environment ?? 'default',
      header_name: typeof authConfig.header_name === 'string' ? authConfig.header_name : undefined,
      max_retries: connection.max_retries ?? 0,
      name: connection.name,
      password_ref: typeof authConfig.password_ref === 'string' ? authConfig.password_ref : undefined,
      plugin_id: connection.plugin_id,
      request_config: stableJson(requestConfig),
      schema_values: schemaValuesFromPayload(connection, schema),
      secret_ref: typeof authConfig.secret_ref === 'string' ? authConfig.secret_ref : undefined,
      status: connection.status,
      timeout_seconds: connection.timeout_seconds ?? 30,
      token_ref: typeof authConfig.token_ref === 'string' ? authConfig.token_ref : undefined,
      username_ref: typeof authConfig.username_ref === 'string' ? authConfig.username_ref : undefined,
    });
    setConnectionModalOpen(true);
  };

  const closeConnectionModal = () => {
    setConnectionModalOpen(false);
    setEditingConnection(undefined);
    setAssistantConnectionDraftSource(undefined);
    setAdvancedConnectionJsonOpen(false);
    setAdvancedConnectionRequestJsonOpen(false);
    connectionForm.resetFields();
  };

  const applyConnectionPluginDefaults = (pluginId: string) => {
    const plugin = pluginById.get(pluginId);
    const defaults = connectionDefaultsForPlugin(plugin);
    const schema = plugin
      ? marketplaceItemByPluginCode.get(plugin.code)?.connection_schema
        ?? marketplaceItemByPluginId.get(plugin.id)?.connection_schema
      : undefined;
    if (!defaults) {
      return;
    }
    const nextValues: Partial<ConnectionFormValues> = {
      header_name: undefined,
      password_ref: undefined,
      plugin_id: pluginId,
      schema_values: {},
      secret_ref: undefined,
      token_ref: undefined,
      username_ref: undefined,
      ...defaults,
    };
    const mergedValues = {
      ...connectionForm.getFieldsValue(),
      ...nextValues,
    };
    if (advancedConnectionJsonOpen) {
      nextValues.auth_config = stableJson(buildConnectionAuthConfig(mergedValues));
    }
    if (advancedConnectionRequestJsonOpen) {
      nextValues.request_config = stableJson(buildConnectionRequestConfig(mergedValues, schema));
    }
    connectionForm.setFieldsValue(nextValues);
  };

  const submitConnection = async (options: { testAfterSave?: boolean } = {}) => {
    try {
      setConnectionSubmitAction(options.testAfterSave ? 'save-test' : 'save');
      const values = await connectionForm.validateFields();
      const authConfig = advancedConnectionJsonOpen
        ? parseJsonObject(values.auth_config, '认证配置')
        : buildConnectionAuthConfig(values);
      if (selectedConnectionIsGithub) {
        const tokenRef = typeof authConfig.token_ref === 'string' ? authConfig.token_ref.trim() : '';
        if (values.auth_type !== 'bearer' || !tokenRef) {
          throw new Error('GitHub 连接必须填写 Token 或密钥引用');
        }
      }
      const requestConfig = advancedConnectionRequestJsonOpen
        ? parseJsonObject(values.request_config, '请求配置')
        : buildConnectionRequestConfig(values, selectedConnectionSchema);
      const payload = buildConnectionPayload(values, authConfig, requestConfig, selectedConnectionSchema);
      let savedConnection: PluginConnectionRecord;
      if (editingConnection) {
        const updatedConnection = await updatePluginConnection(editingConnection.id, payload);
        savedConnection = {
          ...editingConnection,
          ...payload,
          ...updatedConnection,
          id: updatedConnection.id ?? editingConnection.id,
          name: updatedConnection.name ?? payload.name ?? editingConnection.name,
          plugin_id: updatedConnection.plugin_id ?? payload.plugin_id ?? editingConnection.plugin_id,
          endpoint_url: updatedConnection.endpoint_url ?? payload.endpoint_url ?? editingConnection.endpoint_url,
          status: updatedConnection.status ?? payload.status ?? editingConnection.status,
        };
        message.success('连接已更新');
      } else {
        const createdConnection = assistantConnectionDraftSource?.draftId
          ? undefined
          : await createPluginConnection(payload);
        if (assistantConnectionDraftSource?.draftId) {
          const confirmedPayload = payload as Record<string, unknown>;
          await updateAssistantActionDraft(
            assistantConnectionDraftSource.draftId,
            confirmedPayload,
            pluginAssistantDraftModifiedFields(
              assistantConnectionDraftSource.payload,
              confirmedPayload,
            ),
          );
          const confirmed = await confirmAssistantActionDraft(assistantConnectionDraftSource.draftId);
          const confirmedRecord = (
            confirmed.run.result && typeof confirmed.run.result === 'object'
              ? confirmed.run.result
              : {}
          ) as Partial<PluginConnectionRecord>;
          savedConnection = {
            ...payload,
            ...confirmedRecord,
            id: confirmed.run.result_id ?? confirmedRecord.id ?? '',
            name: confirmedRecord.name ?? payload.name ?? values.name,
            plugin_id: confirmedRecord.plugin_id ?? payload.plugin_id ?? values.plugin_id,
            endpoint_url: confirmedRecord.endpoint_url ?? payload.endpoint_url ?? values.endpoint_url,
            status: confirmedRecord.status ?? payload.status ?? values.status,
          };
          rememberAssistantDraftResolution({
            draftId: assistantConnectionDraftSource.draftId,
            resourceId: confirmed.run.result_id,
            resourceType: 'plugin_connection',
            title: assistantConnectionDraftSource.title,
          });
          message.success('助手草案已确认并创建连接');
        } else if (createdConnection) {
          savedConnection = {
            ...payload,
            ...createdConnection,
            id: createdConnection.id,
            name: createdConnection.name ?? payload.name ?? values.name,
            plugin_id: createdConnection.plugin_id ?? payload.plugin_id ?? values.plugin_id,
            endpoint_url: createdConnection.endpoint_url ?? payload.endpoint_url ?? values.endpoint_url,
            status: createdConnection.status ?? payload.status ?? values.status,
          };
          rememberAssistantDraftResolution({
            draftId: assistantConnectionDraftSource?.draftId,
            resourceId: createdConnection.id,
            resourceType: 'plugin_connection',
            title: assistantConnectionDraftSource?.title,
          });
          message.success('连接已创建');
        } else {
          throw new Error('连接创建失败');
        }
      }
      closeConnectionModal();
      await reload();
      if (options.testAfterSave) {
        await runConnectionTest(savedConnection);
      }
    } catch (error) {
      if (isFormValidationError(error)) {
        const firstField = error.errorFields[0]?.name;
        if (firstField) {
          connectionForm.scrollToField(firstField);
        }
        return;
      }
      message.error(error instanceof Error ? error.message : editingConnection ? '连接更新失败' : '连接创建失败');
    } finally {
      setConnectionSubmitAction(undefined);
    }
  };

  const submitAction = async () => {
    try {
      const values = await actionForm.validateFields();
      const requestConfig =
        values.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO && !advancedActionJsonOpen
          ? buildMaxComputeRequestConfig(values)
          : advancedActionJsonOpen
            ? parseJsonObject(values.request_config, '请求配置')
            : buildVisualRequestConfig(values);
      const resultMapping = advancedActionJsonOpen
        ? mergeWriteTarget(parseJsonObject(values.result_mapping, '结果映射'), values.write_target)
        : buildVisualResultMapping(values, resultWriteTargets);
      const payload = buildActionPayload(values, requestConfig, resultMapping);
      if (editingAction) {
        await updatePluginAction(editingAction.id, payload);
        message.success('动作已更新');
      } else if (assistantActionDraftSource?.draftId) {
        const confirmedPayload = payload as Record<string, unknown>;
        await updateAssistantActionDraft(
          assistantActionDraftSource.draftId,
          confirmedPayload,
          pluginAssistantDraftModifiedFields(
            assistantActionDraftSource.payload,
            confirmedPayload,
          ),
        );
        const confirmed = await confirmAssistantActionDraft(assistantActionDraftSource.draftId);
        rememberAssistantDraftResolution({
          draftId: assistantActionDraftSource.draftId,
          resourceId: confirmed.run.result_id,
          resourceType: 'plugin_action',
          title: assistantActionDraftSource.title,
        });
        message.success('助手草案已确认并创建动作');
      } else {
        const createdAction = await createPluginAction(payload);
        rememberAssistantDraftResolution({
          draftId: assistantActionDraftSource?.draftId,
          resourceId: createdAction.id,
          resourceType: 'plugin_action',
          title: assistantActionDraftSource?.title,
        });
        message.success('动作已创建');
      }
      closeActionModal();
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : editingAction ? '动作更新失败' : '动作创建失败');
    }
  };

  const openCreateActionModal = useCallback(() => {
    setEditingAction(undefined);
    setAssistantActionDraftSource(undefined);
    setActionScenario(undefined);
    setAdvancedActionJsonOpen(false);
    actionForm.resetFields();
    const defaultResultMapping = defaultResultMappingForWriteTarget(DEFAULT_RESULT_WRITE_TARGET, resultWriteTargets);
    actionForm.setFieldsValue({
      action_type: 'http_request',
      method: 'GET',
      requires_human_review: false,
      result_mapping: stableJson(defaultResultMapping),
      status: 'active',
      ...resultMappingVisualFields(defaultResultMapping, resultWriteTargets),
    });
    setActionModalOpen(true);
  }, [actionForm, resultWriteTargets]);

  const marketplaceActionScenario = (item: PluginMarketplaceItem) => {
    const template = actionTemplates.find((candidate) => candidate.plugin_code === item.code);
    if (template) {
      return template.code;
    }
    return undefined;
  };

  const openCreateActionForMarketplacePlugin = (item: PluginMarketplaceItem) => {
    const scenario = marketplaceActionScenario(item);
    if (!scenario) {
      message.warning('动作模板目录未返回该官方插件模板，请刷新服务端模板目录后重试');
      return;
    }
    openCreateActionModal();
    applyActionScenario(scenario);
  };

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      const storageKey = assistantScopedStorageKey(ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY);
      const rawDraft = window.sessionStorage.getItem(storageKey);
      if (!rawDraft) {
        return;
      }
      window.sessionStorage.removeItem(storageKey);
      try {
        const draft = JSON.parse(rawDraft) as AssistantPluginConnectionDraft;
        if (!isPlainRecord(draft.payload)) {
          return;
        }
        openCreateConnectionModal();
        setAssistantConnectionDraftSource({
          draftId: draft.draftId,
          payload: draft.payload,
          title: draft.title,
        });
        const pluginId = stringValue(draft.payload.plugin_id);
        const plugin = pluginId ? pluginById.get(pluginId) : undefined;
        const schema = plugin
          ? marketplaceItemByPluginCode.get(plugin.code)?.connection_schema
            ?? marketplaceItemByPluginId.get(plugin.id)?.connection_schema
          : undefined;
        connectionForm.setFieldsValue(pluginConnectionDraftFormValues(draft.payload, schema));
        message.success(`已应用助手草案：${draft.title || '插件连接'}`);
      } catch (error) {
        message.error(error instanceof Error ? error.message : '助手插件连接草案解析失败');
      }
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [
    connectionForm,
    marketplaceItemByPluginCode,
    marketplaceItemByPluginId,
    openCreateConnectionModal,
    pluginById,
  ]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const storageKey = assistantScopedStorageKey(ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY);
    if (!window.sessionStorage.getItem(storageKey) || resultWriteTargets.length === 0) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      const rawDraft = window.sessionStorage.getItem(storageKey);
      if (!rawDraft) {
        return;
      }
      window.sessionStorage.removeItem(storageKey);
      try {
        const draft = JSON.parse(rawDraft) as AssistantPluginActionDraft;
        if (!isPlainRecord(draft.payload)) {
          return;
        }
        openCreateActionModal();
        setAssistantActionDraftSource({
          draftId: draft.draftId,
          payload: draft.payload,
          title: draft.title,
        });
        actionForm.setFieldsValue(pluginActionDraftFormValues(draft.payload, resultWriteTargets));
        message.success(`已应用助手草案：${draft.title || '动作'}`);
      } catch (error) {
        message.error(error instanceof Error ? error.message : '助手动作草案解析失败');
      }
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [actionForm, openCreateActionModal, resultWriteTargets]);

  const openEditActionModal = (action: PluginActionRecord) => {
    const requestConfig = action.request_config ?? {};
    const resultMapping = action.result_mapping ?? {};
    const isMaxComputeAction = requestConfig.tool_name === 'maxcompute.execute_sql';
    const scenario = isMaxComputeAction
      ? MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO
      : actionScenarioForExistingAction(action, actionTemplates, plugins);
    setEditingAction(action);
    setAssistantActionDraftSource(undefined);
    setActionScenario(scenario);
    setAdvancedActionJsonOpen(!isMaxComputeAction && action.action_type === 'mcp_tool');
    actionForm.resetFields();
    actionForm.setFieldsValue({
      action_type: action.action_type,
      code: action.code,
      connection_id: action.connection_id ?? undefined,
      description: action.description ?? undefined,
      header_rows: recordToRows(configSection(requestConfig, 'headers')),
      max_rows: typeof requestConfig.limit === 'number' ? requestConfig.limit : undefined,
      method: typeof requestConfig.method === 'string' ? requestConfig.method : 'GET',
      name: action.name,
      param_rows: recordToRows(configSection(requestConfig, 'query')),
      path: typeof requestConfig.path === 'string' ? requestConfig.path : undefined,
      plugin_id: action.plugin_id,
      request_config: stableJson(requestConfig),
      requires_human_review: action.requires_human_review,
      result_mapping: stableJson(resultMapping),
      returned_fields: Array.isArray(requestConfig.fields)
        ? requestConfig.fields.join(',')
        : undefined,
      scenario,
      status: action.status,
      table_name: typeof requestConfig.table === 'string' ? requestConfig.table : undefined,
      time_field: typeof requestConfig.time_field === 'string' ? requestConfig.time_field : undefined,
      ...resultMappingVisualFields(resultMapping, resultWriteTargets),
    });
    setActionModalOpen(true);
  };

  const closeActionModal = () => {
    setActionModalOpen(false);
    setEditingAction(undefined);
    setAssistantActionDraftSource(undefined);
    setActionScenario(undefined);
    setAdvancedActionJsonOpen(false);
    actionForm.resetFields();
  };

  const applyActionScenario = (scenario?: string) => {
    setActionScenario(scenario);
    const pluginByCode = (code: string) => plugins.find((plugin) => plugin.code === code);
    const connectionForPlugin = (pluginId?: string) =>
      pluginId ? connections.find((connection) => connection.plugin_id === pluginId)?.id : undefined;
    const template = actionTemplates.find((item) => item.code === scenario);
    if (template) {
      const plugin = pluginByCode(template.plugin_code) ?? plugins.find((item) => item.id === template.plugin_id);
      const requestConfig = isPlainRecord(template.request_config) ? template.request_config : {};
      const resultMapping = isPlainRecord(template.result_mapping)
        ? template.result_mapping
        : defaultResultMappingForWriteTarget(DEFAULT_RESULT_WRITE_TARGET, resultWriteTargets);
      const formDefaults = isPlainRecord(template.form_defaults) ? template.form_defaults : {};
      const isMaxComputeTemplate = template.code === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO;
      const tableName = stringValue(
        formDefaults.table_name,
        stringValue(requestConfig.table, 'ods_user_feedback'),
      );
      const timeField = stringValue(
        formDefaults.time_field,
        stringValue(requestConfig.time_field, 'created_at'),
      );
      const returnedFields = stringValue(
        formDefaults.returned_fields,
        Array.isArray(requestConfig.fields)
          ? requestConfig.fields.map(String).join(',')
          : MAXCOMPUTE_DEFAULT_FIELDS,
      );
      const maxRows = numberValue(formDefaults.max_rows, numberValue(requestConfig.limit, 1000));
      const templatePluginId = stringValue(template.plugin_id) || undefined;
      const pluginId = plugin?.id ?? templatePluginId ?? (
        isMaxComputeTemplate && plugins.length === 1 ? plugins[0].id : undefined
      );
      const nextValues: Partial<ActionFormValues> = {
        action_type: stringValue(template.action_type, 'http_request'),
        code: stringValue(template.default_code, template.code),
        connection_id: connectionForPlugin(pluginId)
          ?? (isMaxComputeTemplate && connections.length === 1 ? connections[0].id : undefined),
        header_rows: recordToRows(requestConfig.headers),
        max_rows: maxRows,
        method: stringValue(requestConfig.method, 'GET'),
        name: stringValue(template.default_name, template.name),
        param_rows: recordToRows(requestConfig.query),
        path: stringValue(requestConfig.path) || undefined,
        plugin_id: pluginId,
        request_config: stableJson(requestConfig),
        result_mapping: stableJson(resultMapping),
        returned_fields: returnedFields,
        table_name: tableName,
        time_field: timeField,
        ...resultMappingVisualFields(resultMapping, resultWriteTargets),
      };
      actionForm.setFieldsValue(nextValues);
      return;
    }
    if (scenario) {
      message.warning('动作模板目录未返回该场景，请刷新后重试');
    }
  };

  const applyWriteTargetDefaults = (writeTarget?: string) => {
    const resultMapping = defaultResultMappingForWriteTarget(writeTarget, resultWriteTargets);
    actionForm.setFieldsValue({
      result_mapping: stableJson(resultMapping),
      ...resultMappingVisualFields(resultMapping, resultWriteTargets),
    });
  };

  const toggleAdvancedActionJson = () => {
    const nextOpen = !advancedActionJsonOpen;
    if (nextOpen) {
      syncActionJsonFromVisual();
    }
    setAdvancedActionJsonOpen(nextOpen);
  };

  const syncActionJsonFromVisual = () => {
    const values = actionForm.getFieldsValue();
    const requestConfig =
      values.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO
        ? buildMaxComputeRequestConfig(values)
        : buildVisualRequestConfig(values);
    actionForm.setFieldsValue({
      request_config: stableJson(requestConfig),
      result_mapping: stableJson(buildVisualResultMapping(values, resultWriteTargets)),
    });
  };

  const applyActionJsonToVisual = () => {
    try {
      const config = parseJsonObject(actionForm.getFieldValue('request_config'), '请求配置');
      const resultMapping = parseJsonObject(actionForm.getFieldValue('result_mapping'), '结果映射');
      actionForm.setFieldsValue({
        header_rows: recordToRows(config.headers),
        method: typeof config.method === 'string' ? config.method : 'GET',
        param_rows: recordToRows(config.query),
        path: typeof config.path === 'string' ? config.path : undefined,
        ...resultMappingVisualFields(resultMapping, resultWriteTargets),
      });
      message.success('已从 JSON 同步到可视化字段');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'JSON 解析失败');
    }
  };

  const toggleAdvancedConnectionJson = () => {
    const nextOpen = !advancedConnectionJsonOpen;
    if (nextOpen) {
      const values = connectionForm.getFieldsValue();
      connectionForm.setFieldsValue({
        auth_config: values.auth_config?.trim()
          ? values.auth_config
          : stableJson(buildConnectionAuthConfig(values)),
      });
    }
    setAdvancedConnectionJsonOpen(nextOpen);
  };

  const syncConnectionRequestJsonFromVisual = () => {
    const values = connectionForm.getFieldsValue();
    connectionForm.setFieldValue('request_config', stableJson(buildConnectionRequestConfig(values, selectedConnectionSchema)));
  };

  const toggleAdvancedConnectionRequestJson = () => {
    const nextOpen = !advancedConnectionRequestJsonOpen;
    if (nextOpen) {
      syncConnectionRequestJsonFromVisual();
    }
    setAdvancedConnectionRequestJsonOpen(nextOpen);
  };

  const applyConnectionJsonToVisual = () => {
    try {
      const config = parseJsonObject(connectionForm.getFieldValue('auth_config'), '认证配置');
      connectionForm.setFieldsValue({
        header_name: typeof config.header_name === 'string' ? config.header_name : undefined,
        password_ref: typeof config.password_ref === 'string' ? config.password_ref : undefined,
        secret_ref: typeof config.secret_ref === 'string' ? config.secret_ref : undefined,
        token_ref: typeof config.token_ref === 'string' ? config.token_ref : undefined,
        username_ref: typeof config.username_ref === 'string' ? config.username_ref : undefined,
      });
      message.success('已从认证 JSON 同步到可视化字段');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'JSON 解析失败');
    }
  };

  const applyConnectionRequestJsonToVisual = () => {
    try {
      const config = parseJsonObject(connectionForm.getFieldValue('request_config'), '请求配置');
      connectionForm.setFieldsValue({
        connection_header_rows: recordToRows(
          config.headers,
          schemaManagedRequestKeys(selectedConnectionSchema, 'headers'),
        ),
        connection_param_rows: recordToRows(
          config.query,
          schemaManagedRequestKeys(selectedConnectionSchema, 'query'),
        ),
        schema_values: schemaValuesFromPayload({ request_config: config }, selectedConnectionSchema),
      });
      message.success('已从请求 JSON 同步到 Params / Headers');
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'JSON 解析失败');
    }
  };

  const runAction = async (action: PluginActionRecord) => {
    await invokePluginAction(action.id);
    message.success('动作运行已完成');
    await reload();
  };

  const openActionFromConnectionTest = (
    connection: PluginConnectionRecord,
    result: PluginConnectionTestResult,
  ) => {
    const draft = result.action_template_draft;
    if (!draft) {
      message.warning('当前测试结果缺少动作模板草案');
      return;
    }
    Modal.destroyAll();
    setEditingAction(undefined);
    setAssistantActionDraftSource(undefined);
    setActionScenario(undefined);
    setAdvancedActionJsonOpen(false);
    actionForm.resetFields();
    actionForm.setFieldsValue(pluginActionDraftFormValues({
      ...draft,
      connection_id: draft.connection_id ?? connection.id,
      plugin_id: draft.plugin_id ?? connection.plugin_id,
    } as Record<string, unknown>, resultWriteTargets));
    setActionModalOpen(true);
  };

  const updateConnectionAfterTest = (
    connection: PluginConnectionRecord,
    result: PluginConnectionTestResult,
  ) => {
    setConnections((currentConnections) =>
      currentConnections.map((item) =>
        item.id === connection.id
          ? {
              ...item,
              last_test_summary: {
                checked_at: result.checked_at,
                error_code: result.error_code,
                error_message: result.error_message,
                failed_step: result.diagnostics?.find((step) => step.status === 'failed')?.name,
                latency_ms: result.latency_ms,
                mocked: result.mocked,
                response_status_code: typeof result.response_summary?.status_code === 'number'
                  ? result.response_summary.status_code
                  : null,
                status: result.status,
              },
              test_history: result.test_history ?? item.test_history,
            }
          : item,
      ),
    );
  };

  const openConnectionTestDiagnostics = (
    connection: PluginConnectionRecord,
    result: PluginConnectionTestResult,
  ) => {
    Modal.info({
      content: (
        <PluginConnectionTestDiagnosticsContent
          connection={connection}
          result={result}
          onCopyAsActionTemplate={() => openActionFromConnectionTest(connection, result)}
        />
      ),
      title: '连接测试诊断',
      width: 980,
    });
  };

  const runConnectionTest = async (connection: PluginConnectionRecord) => {
    if (testingConnectionId) {
      return;
    }
    const messageKey = `plugin-connection-test-${connection.id}`;
    setTestingConnectionId(connection.id);
    message.loading({
      content: `正在测试连接「${connection.name}」，请稍候...`,
      duration: 0,
      key: messageKey,
    });
    try {
      const result = await testPluginConnection(connection.id);
      updateConnectionAfterTest(connection, result);
      openConnectionTestDiagnostics(connection, result);
      if (result.status === 'succeeded') {
        message.success({
          content: `连接测试成功，耗时 ${result.latency_ms}ms`,
          duration: 3,
          key: messageKey,
        });
      } else {
        message.error({
          content: result.error_message || '连接测试失败',
          duration: 5,
          key: messageKey,
        });
      }
    } catch (error) {
      message.error({
        content: error instanceof Error ? error.message : '连接测试失败',
        duration: 5,
        key: messageKey,
      });
    } finally {
      setTestingConnectionId(undefined);
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

  const syncConnectionAuthJsonFromVisual = () => {
    const values = connectionForm.getFieldsValue();
    connectionForm.setFieldValue('auth_config', stableJson(buildConnectionAuthConfig(values)));
  };

  const handleConnectionValuesChange = (
    changedValues: Partial<ConnectionFormValues>,
    allValues: ConnectionFormValues,
  ) => {
    if (
      selectedConnectionIsGitlab
      && Object.prototype.hasOwnProperty.call(changedValues, 'schema_values')
    ) {
      const nextEndpointUrl = endpointUrlFromSchemaValues(allValues, selectedConnectionSchema);
      if (nextEndpointUrl && nextEndpointUrl !== allValues.endpoint_url) {
        connectionForm.setFieldValue('endpoint_url', nextEndpointUrl);
      }
    }
    if (
      advancedConnectionRequestJsonOpen
      && !Object.prototype.hasOwnProperty.call(changedValues, 'request_config')
    ) {
      connectionForm.setFieldValue(
        'request_config',
        stableJson(buildConnectionRequestConfig(allValues, selectedConnectionSchema)),
      );
    }
  };

  const handleActionValuesChange = (
    changedValues: Partial<ActionFormValues>,
    allValues: ActionFormValues,
  ) => {
    if (
      advancedActionJsonOpen
      && !Object.prototype.hasOwnProperty.call(changedValues, 'request_config')
      && !Object.prototype.hasOwnProperty.call(changedValues, 'result_mapping')
    ) {
      const requestConfig =
        allValues.scenario === MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO
          ? buildMaxComputeRequestConfig(allValues)
          : buildVisualRequestConfig(allValues);
      actionForm.setFieldsValue({
        request_config: stableJson(requestConfig),
        result_mapping: stableJson(buildVisualResultMapping(allValues, resultWriteTargets)),
      });
    }
  };

  const openTrialModal = (action: PluginActionRecord) => {
    setTrialAction(action);
    setTrialConnectionId(action.connection_id ?? undefined);
    setTrialInputJson('{}');
    setTrialResult(undefined);
    setTrialModalOpen(true);
  };

  const runActionTrial = async () => {
    if (!trialAction) {
      return;
    }
    try {
      setTrialRunning(true);
      const parsedInput = parseJsonObject(trialInputJson, '试运行输入');
      const result = await trialPluginAction(trialAction.id, {
        connection_id: trialConnectionId,
        input_payload: parsedInput,
      });
      setTrialResult(result);
      if (result.status === 'succeeded') {
        message.success('试运行完成');
      } else {
        message.error(result.error_message || '试运行失败');
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '试运行失败');
    } finally {
      setTrialRunning(false);
    }
  };

  return (
    <PageContainer title="插件管理">
      <PluginWorkspaceGuide />
      <PluginManagementTabs
        actions={actions}
        connectionById={connectionById}
        connectionEnvironmentFilter={connectionEnvironmentFilter}
        connectionEnvironmentLabels={connectionEnvironmentLabelByValue}
        connectionEnvironmentOptions={connectionEnvironmentOptions}
        connections={connections}
        formatWriteTarget={(writeTarget) => resultWriteTargetLabel(
          writeTarget ?? DEFAULT_RESULT_WRITE_TARGET,
          resultWriteTargets,
        )}
        loading={loading}
        marketplaceItems={marketplaceItems}
        pluginById={pluginById}
        plugins={plugins}
        runners={runners}
        testingConnectionId={testingConnectionId}
        testingRunnerId={testingRunnerId}
        onCopyOfficialPlugin={(plugin) => void copyOfficialPlugin(plugin)}
        onCopyRunnerSetupCommand={copyRunnerSetupCommand}
        onCreateAction={openCreateActionModal}
        onCreateActionForMarketplacePlugin={openCreateActionForMarketplacePlugin}
        onCreateConnection={openCreateConnectionModal}
        onCreateConnectionForPlugin={openCreateConnectionForPlugin}
        onCreatePlugin={openCreatePluginModal}
        onCreateRunner={openCreateRunnerModal}
        onDeleteAction={confirmDeleteAction}
        onDeleteConnection={confirmDeleteConnection}
        onDeletePlugin={confirmDeletePlugin}
        onDeleteRunner={confirmDeleteRunner}
        onDownloadRunnerInstallPackage={(runner) => void downloadRunnerInstallPackage(runner)}
        onEditAction={openEditActionModal}
        onEditConnection={openEditConnectionModal}
        onEditPlugin={openEditPluginModal}
        onEditRunner={openEditRunnerModal}
        onEnvironmentFilterChange={setConnectionEnvironmentFilter}
        onOpenRunnerLogs={(runner) => void openRunnerLogs(runner)}
        onReload={reload}
        onRotateRunnerToken={rotateRunnerToken}
        onRunAction={runAction}
        onTestConnection={runConnectionTest}
        onTestRunner={(runner) => void runRunnerTest(runner)}
        onTrialAction={openTrialModal}
      />

      <PluginManagementModals
        actionForm={actionForm}
        actionModalOpen={actionModalOpen}
        actionScenario={actionScenario}
        actionTemplateOptions={actionTemplateOptions}
        advancedActionJsonOpen={advancedActionJsonOpen}
        advancedConnectionJsonOpen={advancedConnectionJsonOpen}
        advancedConnectionRequestJsonOpen={advancedConnectionRequestJsonOpen}
        connectionEnvironmentOptions={connectionEnvironmentOptions}
        connectionForm={connectionForm}
        connectionModalOpen={connectionModalOpen}
        connectionOptions={connectionOptions}
        connectionSubmitAction={connectionSubmitAction}
        defaultWriteTarget={DEFAULT_RESULT_WRITE_TARGET}
        editingAction={editingAction}
        editingConnection={Boolean(editingConnection)}
        editingPlugin={Boolean(editingPlugin)}
        editingRunner={Boolean(editingRunner)}
        maxComputeScenario={MAXCOMPUTE_WEEKLY_FEEDBACK_SCENARIO}
        pluginCode={
          typeof selectedConnectionPluginCode === 'string' ? selectedConnectionPluginCode : undefined
        }
        pluginForm={pluginForm}
        pluginModalOpen={pluginModalOpen}
        pluginOptions={pluginOptions}
        requestPreview={requestPreview}
        resultWriteTargetOptions={resultWriteTargetOptions}
        resultWriteTargets={resultWriteTargets}
        rotatedRunnerToken={rotatedRunnerToken}
        rotatingRunner={rotatingRunner}
        rotatingRunnerLoading={rotatingRunnerLoading}
        runnerForm={runnerForm}
        runnerLogLoading={runnerLogLoading}
        runnerLogModalOpen={runnerLogModalOpen}
        runnerLogRows={runnerLogRows}
        runnerLogTask={runnerLogTask}
        runnerModalOpen={runnerModalOpen}
        selectedConnectionAuthType={
          typeof selectedConnectionAuthType === 'string' ? selectedConnectionAuthType : undefined
        }
        selectedConnectionIsGithub={selectedConnectionIsGithub}
        selectedConnectionSchema={selectedConnectionSchema}
        systemVariableOptions={SYSTEM_VARIABLE_OPTIONS}
        trialAction={trialAction}
        trialConnectionId={trialConnectionId}
        trialInputJson={trialInputJson}
        trialModalOpen={trialModalOpen}
        trialResult={trialResult}
        trialRunning={trialRunning}
        onActionValuesChange={handleActionValuesChange}
        onApplyActionJsonToVisual={applyActionJsonToVisual}
        onApplyActionScenario={applyActionScenario}
        onApplyConnectionAuthJsonToVisual={applyConnectionJsonToVisual}
        onApplyConnectionPluginDefaults={applyConnectionPluginDefaults}
        onApplyConnectionRequestJsonToVisual={applyConnectionRequestJsonToVisual}
        onCancelRunnerTask={cancelRunnerTask}
        onCloseActionModal={closeActionModal}
        onCloseConnectionModal={closeConnectionModal}
        onClosePluginModal={closePluginModal}
        onCloseRotatedRunnerToken={() => setRotatedRunnerToken(undefined)}
        onCloseRunnerLogModal={() => setRunnerLogModalOpen(false)}
        onCloseRunnerModal={closeRunnerModal}
        onConnectionValuesChange={handleConnectionValuesChange}
        onRotateRunnerTokenCancel={() => setRotatingRunner(undefined)}
        onRotateRunnerTokenSubmit={submitRotateRunnerToken}
        onRunActionTrial={runActionTrial}
        onSubmitAction={submitAction}
        onSubmitConnection={() => submitConnection()}
        onSubmitConnectionAndTest={() => submitConnection({ testAfterSave: true })}
        onSubmitPlugin={submitPlugin}
        onSubmitRunner={submitRunner}
        onSyncActionJsonFromVisual={syncActionJsonFromVisual}
        onSyncConnectionAuthJsonFromVisual={syncConnectionAuthJsonFromVisual}
        onSyncConnectionRequestJsonFromVisual={syncConnectionRequestJsonFromVisual}
        onToggleActionAdvancedJson={toggleAdvancedActionJson}
        onToggleConnectionAdvancedAuthJson={toggleAdvancedConnectionJson}
        onToggleConnectionAdvancedRequestJson={toggleAdvancedConnectionRequestJson}
        onTrialConnectionChange={setTrialConnectionId}
        onTrialInputJsonChange={setTrialInputJson}
        onTrialModalClose={() => setTrialModalOpen(false)}
        onWriteTargetChange={applyWriteTargetDefaults}
      />
    </PageContainer>
  );
}
