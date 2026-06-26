import { PageContainer } from '@ant-design/pro-components';
import {
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Tabs,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
  assistantScopedStorageKey,
  confirmAssistantActionDraft,
  createScheduledJob,
  deleteScheduledJob,
  dryRunScheduledJob,
  fetchActiveProductOptions,
  fetchAiAgents,
  fetchAiSkills,
  fetchManagementKnowledge,
  fetchModelGatewayConfigs,
  fetchPluginActions,
  fetchPluginConnections,
  fetchResultWriteRecords,
  fetchProductGitRepositories,
  fetchScheduledJobCatalog,
  fetchScheduledJobTemplates,
  fetchScheduledJobRunObservability,
  fetchScheduledJobRuns,
  fetchScheduledJobs,
  generateScheduledJobTemplateFromRun,
  rememberAssistantDraftResolution,
  runScheduledJob,
  testPluginConnection,
  updateScheduledJob,
  updateAssistantActionDraft,
  type AiAgentRecord,
  type AiSkillRecord,
  type AssistantScheduledJobDraft,
  type PluginActionRecord,
  type PluginConnectionTestResult,
  type PluginConnectionRecord,
  type ProductFilterOption,
  type ProductGitRepositoryOption,
  type ResultWriteRecord,
  type ScheduledJobRecord,
  type ScheduledJobDryRunResult,
  type ScheduledJobCatalogRecord,
  type ScheduledJobResultAction,
  type ScheduledJobRunObservability,
  type ScheduledJobRunRecord,
  type ScheduledJobTemplateRecord,
} from '../../services/aiBrain';
import type { ModelGatewayConfigRecord } from '../../data/management';
import type { KnowledgeRecord } from '../../data/management';
import { ScheduledJobActionConfigSection } from './components/ScheduledJobActionConfigSection';
import { ScheduledJobAiExecutionSection } from './components/ScheduledJobAiExecutionSection';
import { ScheduledJobBasicInfoSection } from './components/ScheduledJobBasicInfoSection';
import { ScheduledJobCodeRepositorySection } from './components/ScheduledJobCodeRepositorySection';
import { ScheduledJobConfigTable } from './components/ScheduledJobConfigTable';
import { ScheduledJobDataConnectionSection } from './components/ScheduledJobDataConnectionSection';
import { ScheduledJobDryRunResultPanel } from './components/ScheduledJobDryRunResultPanel';
import { ScheduledJobScheduleConfigSection } from './components/ScheduledJobScheduleConfigSection';
import { ScheduledJobRunDetailModal } from './components/ScheduledJobRunDetailModal';
import { ScheduledJobRunTable } from './components/ScheduledJobRunTable';
import {
  ScheduledJobOrchestrationFlow,
  type ScheduledJobOrchestrationNode,
} from './components/ScheduledJobOrchestrationFlow';
import {
  TemplateSourceSummary,
} from './components/ScheduledJobRunTraceDetails';
import { useScheduledJobCatalogOptions } from './components/scheduledJobCatalogOptions';
import {
  cloneResultActions,
  codeInspectionUsesNativeScan,
  initialScheduledJobPageTab,
  isCodeInspectionPluginAction,
  multiIdsFromScheduledJob,
  nativeCodeInspectionScanMode,
  primaryId,
  recordStringValue,
  recordValue,
  recordFromDraftPayload,
  requiresAiAssembly,
  scheduledJobAssistantDraftModifiedFields,
  scheduledJobConfigWithOrchestration,
  scheduledJobRouteParams,
  scheduledJobRunIdFromAssistantResult,
  scheduledJobTemplateValuesFromRecord,
  scheduledJobValuesFromAssistantDraft,
  snapshotStringListValue,
  snapshotStringValue,
  stringArrayFromUnknown,
  templatePayloadBoolean,
  templatePayloadList,
  templatePayloadNumber,
  templatePayloadRecordValue,
  templatePayloadResultActions,
  templatePayloadString,
  templateSelector,
  uniqueStringList,
  type ScheduledJobFormValues,
  type ScheduledJobPageTab,
  type ScheduledJobTemplateSource,
} from './components/scheduledJobFormTransformHelpers';

function writeStrategyLabelFromAction(action: PluginActionRecord): string {
  const mapping = action.result_mapping ?? {};
  const writeTargetLabel = typeof mapping.write_target_label === 'string' ? mapping.write_target_label : undefined;
  const writeTarget = typeof mapping.write_target === 'string' ? mapping.write_target : undefined;
  const strategyLabel = writeTargetLabel ?? writeTarget ?? action.name;
  return `${strategyLabel} (${action.code})`;
}

export default function ScheduledJobsPage() {
  const [form] = Form.useForm<ScheduledJobFormValues>();
  const [jobs, setJobs] = useState<ScheduledJobRecord[]>([]);
  const [runs, setRuns] = useState<ScheduledJobRunRecord[]>([]);
  const [runObservability, setRunObservability] = useState<ScheduledJobRunObservability | undefined>();
  const [jobTemplates, setJobTemplates] = useState<ScheduledJobTemplateRecord[]>([]);
  const [pluginActions, setPluginActions] = useState<PluginActionRecord[]>([]);
  const [pluginConnections, setPluginConnections] = useState<PluginConnectionRecord[]>([]);
  const [products, setProducts] = useState<ProductFilterOption[]>([]);
  const [productRepositories, setProductRepositories] = useState<ProductGitRepositoryOption[]>([]);
  const [productRepositoriesLoading, setProductRepositoriesLoading] = useState(false);
  const [agents, setAgents] = useState<AiAgentRecord[]>([]);
  const [skills, setSkills] = useState<AiSkillRecord[]>([]);
  const [knowledgeDocuments, setKnowledgeDocuments] = useState<KnowledgeRecord[]>([]);
  const [modelGatewayConfigs, setModelGatewayConfigs] = useState<ModelGatewayConfigRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingJob, setEditingJob] = useState<ScheduledJobRecord | undefined>();
  const [assistantDraftPayload, setAssistantDraftPayload] = useState<Record<string, unknown> | undefined>();
  const [assistantDraftInitialValues, setAssistantDraftInitialValues] = useState<
    ScheduledJobFormValues | undefined
  >();
  const [assistantDraftSource, setAssistantDraftSource] = useState<
    Pick<AssistantScheduledJobDraft, 'draftId' | 'title'> | undefined
  >();
  const [activeTab, setActiveTab] = useState<ScheduledJobPageTab>(initialScheduledJobPageTab);
  const [handledRouteRunKey, setHandledRouteRunKey] = useState<string | undefined>();
  const [templateSource, setTemplateSource] = useState<ScheduledJobTemplateSource | undefined>();
  const [selectedRun, setSelectedRun] = useState<ScheduledJobRunRecord | undefined>();
  const [linkedResultWriteRecordId, setLinkedResultWriteRecordId] = useState<string | undefined>();
  const [selectedRunResultWriteRecords, setSelectedRunResultWriteRecords] = useState<ResultWriteRecord[]>([]);
  const [selectedRunResultWriteRecordsLoading, setSelectedRunResultWriteRecordsLoading] = useState(false);
  const [generatedRunTemplate, setGeneratedRunTemplate] = useState<ScheduledJobTemplateRecord | undefined>();
  const [runningJobId, setRunningJobId] = useState<string | undefined>();
  const [connectionTestResult, setConnectionTestResult] = useState<PluginConnectionTestResult | undefined>();
  const [testingConnectionId, setTestingConnectionId] = useState<string | undefined>();
  const [dryRunResult, setDryRunResult] = useState<ScheduledJobDryRunResult | undefined>();
  const [dryRunning, setDryRunning] = useState(false);
  const [jobCatalog, setJobCatalog] = useState<ScheduledJobCatalogRecord | undefined>();
  const selectedConnectionEnvironment = Form.useWatch('connection_environment', form);
  const selectedPluginConnectionIds = Form.useWatch('plugin_connection_ids', form);
  const selectedPluginActionIds = Form.useWatch('plugin_action_ids', form);
  const selectedExecutionMode = Form.useWatch('execution_mode', form);
  const selectedModelGatewayConfigId = Form.useWatch('model_gateway_config_id', form);
  const selectedAgentId = Form.useWatch('agent_id', form);
  const selectedSkillIds = Form.useWatch('skill_ids', form);
  const selectedKnowledgeDocumentIds = Form.useWatch('knowledge_document_ids', form);
  const selectedResultActions = Form.useWatch('result_actions', form);
  const selectedJobType = Form.useWatch('job_type', form);
  const selectedProductId = Form.useWatch('product_id', form);
  const selectedConfigJson = Form.useWatch('config_json', form);
  const selectedTemplateCode = Form.useWatch('template', form);
  const selectedConfigJsonRecord = useMemo(
    () => recordValue(selectedConfigJson) ?? {},
    [selectedConfigJson],
  );
  const {
    aiAssemblyRuleFactory,
    aiProcessingRequiredTypes,
    codeInspectionBuiltinRuleSelectOptions,
    codeInspectionIgnoreRuleSelectOptions,
    codeInspectionResultActionSelectOptions,
    codeInspectionScanModeSelectOptions,
    codeInspectionScannerEngineSelectOptions,
    connectionEnvironmentSelectOptions,
    defaultCodeInspectionActions,
    executionModeLabelMap,
    executionModeSelectOptions,
    formatResultActionLabels,
    jobTypeLabelMap,
    jobTypeSelectOptions,
    pluginRequiredTypes,
    pluginResourceRuleFactory,
    productRequiredRuleFactory,
    scheduleTypeLabelMap,
    scheduleTypeSelectOptions,
    severityThresholdSelectOptions,
  } = useScheduledJobCatalogOptions(jobCatalog);
  const selectedRepositoryId = recordStringValue(selectedConfigJsonRecord, 'repository_id');
  const selectedCodeInspectionUsesNativeScan = codeInspectionUsesNativeScan(
    selectedJobType,
    selectedConfigJsonRecord,
  );
  const normalizedSelectedPluginConnectionIds = useMemo(
    () => stringArrayFromUnknown(selectedPluginConnectionIds),
    [selectedPluginConnectionIds],
  );
  const normalizedSelectedPluginActionIds = useMemo(
    () => stringArrayFromUnknown(selectedPluginActionIds),
    [selectedPluginActionIds],
  );
  const selectedPrimaryPluginConnectionId = primaryId(normalizedSelectedPluginConnectionIds);
  const availableJobTemplates = useMemo(
    () =>
      generatedRunTemplate
        ? [
            ...jobTemplates.filter((template) => template.code !== generatedRunTemplate.code),
            generatedRunTemplate,
          ]
        : jobTemplates,
    [generatedRunTemplate, jobTemplates],
  );
  const selectedJobTemplate = useMemo(
    () => availableJobTemplates.find((template) => template.code === selectedTemplateCode),
    [availableJobTemplates, selectedTemplateCode],
  );
  const jobTemplateOptions = useMemo(
    () =>
      availableJobTemplates.map((template) => ({
        label: template.name,
        value: template.code,
      })),
    [availableJobTemplates],
  );
  const pluginActionById = useMemo(
    () => new Map(pluginActions.map((action) => [action.id, action])),
    [pluginActions],
  );
  const pluginConnectionById = useMemo(
    () => new Map(pluginConnections.map((connection) => [connection.id, connection])),
    [pluginConnections],
  );
  const codeInspectionActionByPluginId = useMemo(() => {
    const actionByPluginId = new Map<string, PluginActionRecord>();
    for (const action of pluginActions) {
      if (!isCodeInspectionPluginAction(action)) {
        continue;
      }
      const existing = actionByPluginId.get(action.plugin_id);
      if (!existing || (existing.status !== 'active' && action.status === 'active')) {
        actionByPluginId.set(action.plugin_id, action);
      }
    }
    return actionByPluginId;
  }, [pluginActions]);
  const productRepositoryById = useMemo(
    () => new Map(productRepositories.map((repository) => [repository.id, repository])),
    [productRepositories],
  );
  const selectedRepositoryDefaultBranch = selectedRepositoryId
    ? productRepositoryById.get(selectedRepositoryId)?.defaultBranch
    : undefined;
  const selectedPluginActionPluginIds = useMemo(
    () =>
      new Set(
        normalizedSelectedPluginActionIds
          .map((actionId) => pluginActionById.get(actionId)?.plugin_id)
          .filter((pluginId): pluginId is string => Boolean(pluginId)),
      ),
    [normalizedSelectedPluginActionIds, pluginActionById],
  );
  const connectionPluginFilterIds = useMemo(
    () =>
      selectedJobType === 'code_repository_inspection' && codeInspectionActionByPluginId.size > 0
        ? new Set(codeInspectionActionByPluginId.keys())
        : selectedPluginActionPluginIds,
    [codeInspectionActionByPluginId, selectedJobType, selectedPluginActionPluginIds],
  );
  const jobById = useMemo(
    () => new Map(jobs.map((job) => [job.id, job])),
    [jobs],
  );
  const filteredPluginConnections = useMemo(
    () =>
      pluginConnections.filter((connection) => {
        const matchesEnvironment =
          !selectedConnectionEnvironment
          || (connection.environment ?? 'default') === selectedConnectionEnvironment;
        const matchesSelectedActionPlugin =
          connectionPluginFilterIds.size === 0
          || connectionPluginFilterIds.has(String(connection.plugin_id));
        return matchesEnvironment && matchesSelectedActionPlugin;
      }),
    [connectionPluginFilterIds, pluginConnections, selectedConnectionEnvironment],
  );

  useEffect(() => {
    if (!selectedCodeInspectionUsesNativeScan) {
      return;
    }
    if (normalizedSelectedPluginConnectionIds.length > 0) {
      form.setFieldValue('plugin_connection_id', undefined);
      form.setFieldValue('plugin_connection_ids', []);
    }
    if (normalizedSelectedPluginActionIds.length > 0) {
      form.setFieldValue('plugin_action_id', undefined);
      form.setFieldValue('plugin_action_ids', []);
    }
  }, [
    form,
    normalizedSelectedPluginActionIds.length,
    normalizedSelectedPluginConnectionIds.length,
    selectedCodeInspectionUsesNativeScan,
  ]);
  const modelGatewayConfigById = useMemo(
    () => new Map(modelGatewayConfigs.map((config) => [config.id, config])),
    [modelGatewayConfigs],
  );
  const agentById = useMemo(
    () => new Map(agents.map((agent) => [agent.id, agent])),
    [agents],
  );
  const skillById = useMemo(
    () => new Map(skills.map((skill) => [skill.id, skill])),
    [skills],
  );
  const knowledgeDocumentById = useMemo(
    () => new Map(knowledgeDocuments.map((document) => [document.id, document])),
    [knowledgeDocuments],
  );
  const selectedRunConfigSnapshot = selectedRun?.config_snapshot;
  const selectedRunAgentId = snapshotStringValue(selectedRunConfigSnapshot, 'agent_id');
  const selectedRunModelGatewayConfigId = snapshotStringValue(selectedRunConfigSnapshot, 'model_gateway_config_id');
  const selectedRunSkillIds = snapshotStringListValue(selectedRunConfigSnapshot, 'skill_ids');
  const selectedRunJobType = snapshotStringValue(selectedRunConfigSnapshot, 'job_type');
  const selectedRunExecutionMode = snapshotStringValue(selectedRunConfigSnapshot, 'execution_mode');
  const selectedRunJobTypeLabel = selectedRunJobType
    ? jobTypeLabelMap.get(selectedRunJobType) ?? selectedRunJobType
    : '-';
  const selectedRunExecutionModeLabel = selectedRunExecutionMode
    ? executionModeLabelMap.get(selectedRunExecutionMode) ?? selectedRunExecutionMode
    : '-';
  const selectedRunAgentLabel =
    snapshotStringValue(selectedRun?.resolved_agent_snapshot, 'name')
    ?? (selectedRunAgentId ? agentById.get(selectedRunAgentId)?.name ?? selectedRunAgentId : '-');
  const selectedRunModelLabel =
    selectedRunModelGatewayConfigId
      ? modelGatewayConfigById.get(selectedRunModelGatewayConfigId)?.name ?? selectedRunModelGatewayConfigId
      : '-';
  const selectedRunSkillLabels =
    selectedRun?.resolved_skill_snapshots
      ?.map((skill) => String(skill.name ?? skill.code ?? skill.id ?? ''))
      .filter(Boolean)
      .join('、')
    || selectedRunSkillIds.map((skillId) => skillById.get(skillId)?.name ?? skillId).join('、')
    || '-';

  useEffect(() => {
    if (normalizedSelectedPluginConnectionIds.length === 0) {
      return;
    }
    const nextConnectionIds = normalizedSelectedPluginConnectionIds.filter((connectionId) => {
      const connection = pluginConnectionById.get(connectionId);
      if (!connection) {
        return false;
      }
      const matchesEnvironment =
        !selectedConnectionEnvironment
        || (connection.environment ?? 'default') === selectedConnectionEnvironment;
      const matchesSelectedActionPlugin =
        connectionPluginFilterIds.size === 0
        || connectionPluginFilterIds.has(String(connection.plugin_id));
      return matchesEnvironment && matchesSelectedActionPlugin;
    });
    if (nextConnectionIds.length !== normalizedSelectedPluginConnectionIds.length) {
      form.setFieldValue('plugin_connection_ids', nextConnectionIds);
      form.setFieldValue('plugin_connection_id', primaryId(nextConnectionIds));
    }
  }, [
    form,
    connectionPluginFilterIds,
    normalizedSelectedPluginConnectionIds,
    pluginConnectionById,
    selectedConnectionEnvironment,
  ]);

  useEffect(() => {
    queueMicrotask(() => {
      setConnectionTestResult(undefined);
    });
  }, [selectedPrimaryPluginConnectionId]);

  useEffect(() => {
    if (!modalOpen || selectedJobType !== 'code_repository_inspection' || !selectedProductId) {
      queueMicrotask(() => {
        setProductRepositories([]);
        setProductRepositoriesLoading(false);
      });
      return;
    }
    let ignore = false;
    queueMicrotask(() => {
      setProductRepositoriesLoading(true);
    });
    fetchProductGitRepositories(selectedProductId)
      .then((repositories) => {
        if (ignore) {
          return;
        }
        setProductRepositories(repositories);
        const config = recordValue(form.getFieldValue('config_json')) ?? {};
        const currentRepositoryId = recordStringValue(config, 'repository_id');
        const currentBranch = recordStringValue(config, 'branch');
        const selectedRepository =
          repositories.find((repository) => repository.id === currentRepositoryId)
          ?? (!currentRepositoryId ? repositories[0] : undefined);
        if (!currentRepositoryId && selectedRepository) {
          form.setFieldValue(['config_json', 'repository_id'], selectedRepository.id);
        }
        if (!currentBranch && selectedRepository?.defaultBranch) {
          form.setFieldValue(['config_json', 'branch'], selectedRepository.defaultBranch);
        }
      })
      .catch((error) => {
        if (!ignore) {
          message.error(error instanceof Error ? error.message : '代码仓库加载失败');
          setProductRepositories([]);
        }
      })
      .finally(() => {
        if (!ignore) {
          setProductRepositoriesLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [form, modalOpen, selectedJobType, selectedProductId]);

  const handleCodeInspectionRepositoryChange = useCallback(
    (repositoryId: string | undefined) => {
      form.setFieldValue(['config_json', 'repository_id'], repositoryId);
      const repository = repositoryId ? productRepositoryById.get(repositoryId) : undefined;
      form.setFieldValue(['config_json', 'branch'], repository?.defaultBranch ?? undefined);
    },
    [form, productRepositoryById],
  );

  const testSelectedConnection = useCallback(async () => {
    if (!selectedPrimaryPluginConnectionId) {
      message.warning('请先选择数据连接');
      return;
    }
    const hide = message.loading('正在测试数据连接，请稍候...', 0);
    setTestingConnectionId(selectedPrimaryPluginConnectionId);
    try {
      const result = await testPluginConnection(selectedPrimaryPluginConnectionId);
      setConnectionTestResult(result);
      if (result.status === 'succeeded') {
        message.success(`连接测试成功，耗时 ${result.latency_ms}ms`);
      } else {
        message.error(result.error_message || `连接测试 ${result.status}`);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '连接测试失败');
    } finally {
      hide();
      setTestingConnectionId(undefined);
    }
  }, [selectedPrimaryPluginConnectionId]);

  const handlePluginConnectionChange = useCallback(
    (value: unknown) => {
      if (selectedCodeInspectionUsesNativeScan) {
        form.setFieldValue('plugin_connection_id', undefined);
        form.setFieldValue('plugin_connection_ids', []);
        form.setFieldValue('plugin_action_id', undefined);
        form.setFieldValue('plugin_action_ids', []);
        return;
      }
      let nextConnectionIds = uniqueStringList(stringArrayFromUnknown(value));
      if (selectedJobType === 'code_repository_inspection') {
        const addedConnectionId = nextConnectionIds.find(
          (connectionId) => !normalizedSelectedPluginConnectionIds.includes(connectionId),
        );
        const addedConnection = addedConnectionId ? pluginConnectionById.get(addedConnectionId) : undefined;
        if (
          addedConnection
          && codeInspectionActionByPluginId.has(String(addedConnection.plugin_id))
        ) {
          nextConnectionIds = uniqueStringList([
            addedConnectionId,
            ...nextConnectionIds.filter((connectionId) => {
              if (connectionId === addedConnectionId) {
                return false;
              }
              return pluginConnectionById.get(connectionId)?.plugin_id === addedConnection.plugin_id;
            }),
          ]);
        }
        const primaryConnectionId = primaryId(nextConnectionIds);
        const primaryConnection = primaryConnectionId ? pluginConnectionById.get(primaryConnectionId) : undefined;
        const codeInspectionAction = primaryConnection
          ? codeInspectionActionByPluginId.get(String(primaryConnection.plugin_id))
          : undefined;
        if (codeInspectionAction) {
          form.setFieldValue('plugin_action_id', codeInspectionAction.id);
          form.setFieldValue('plugin_action_ids', [codeInspectionAction.id]);
        }
      }
      form.setFieldValue('plugin_connection_id', primaryId(nextConnectionIds));
      form.setFieldValue('plugin_connection_ids', nextConnectionIds);
    },
    [
      codeInspectionActionByPluginId,
      form,
      normalizedSelectedPluginConnectionIds,
      pluginConnectionById,
      selectedCodeInspectionUsesNativeScan,
      selectedJobType,
    ],
  );

  const handleConnectionEnvironmentChange = useCallback(() => {
    form.setFieldValue('plugin_connection_id', undefined);
    form.setFieldValue('plugin_connection_ids', []);
  }, [form]);

  const orchestrationNodes = useMemo<ScheduledJobOrchestrationNode[]>(() => {
    const selectedConnections = normalizedSelectedPluginConnectionIds
      .map((connectionId) => pluginConnectionById.get(connectionId))
      .filter((connection): connection is PluginConnectionRecord => Boolean(connection));
    const selectedActions = normalizedSelectedPluginActionIds
      .map((actionId) => pluginActionById.get(actionId))
      .filter((action): action is PluginActionRecord => Boolean(action));
    const selectedModel = selectedModelGatewayConfigId
      ? modelGatewayConfigById.get(String(selectedModelGatewayConfigId))
      : undefined;
    const selectedAgent = selectedAgentId ? agentById.get(String(selectedAgentId)) : undefined;
    const normalizedSkillIds = Array.isArray(selectedSkillIds) ? selectedSkillIds.map(String) : [];
    const normalizedKnowledgeDocumentIds = Array.isArray(selectedKnowledgeDocumentIds)
      ? selectedKnowledgeDocumentIds.map(String)
      : [];
    const normalizedResultActions = Array.isArray(selectedResultActions)
      ? (selectedResultActions as ScheduledJobResultAction[])
      : [];
    const skillLabels = normalizedSkillIds
      .map((skillId) => skillById.get(skillId)?.name ?? skillId)
      .filter(Boolean);
    const knowledgeLabels = normalizedKnowledgeDocumentIds
      .map((documentId) => knowledgeDocumentById.get(documentId)?.title ?? documentId)
      .filter(Boolean);
    const jobType = String(selectedJobType ?? '');
    const nativeCodeScan = codeInspectionUsesNativeScan(jobType, selectedConfigJsonRecord);
    const connectionRequired = pluginRequiredTypes.includes(jobType) && !nativeCodeScan;
    const actionRequired = pluginRequiredTypes.includes(jobType) && !nativeCodeScan;
    const aiRequired = requiresAiAssembly(selectedJobType, selectedExecutionMode, aiProcessingRequiredTypes);
    const dataStatus = nativeCodeScan
      ? '本地扫描'
      : selectedConnections.length > 0
        ? '已配置'
        : connectionRequired
          ? '待配置'
          : '可选';
    const aiStatus =
      selectedModel && selectedAgent && skillLabels.length > 0
        ? '已配置'
        : aiRequired
          ? '待配置'
          : '可选';
    const knowledgeStatus = knowledgeLabels.length > 0 ? '已选择' : '可选';
    const actionStatus = selectedActions.length > 0 ? '已配置' : actionRequired ? '待配置' : '可选';
    const requestSummary = connectionTestResult?.request_summary;
    const requestUrl = typeof requestSummary?.url === 'string' ? requestSummary.url : undefined;
    const connectionDetails = selectedConnections.flatMap((connection, index) => [
      `${index + 1}. ${connection.name}`,
      connection.environment ? `环境 ${connection.environment}` : undefined,
    ]);
    const actionDetails = [
      ...selectedActions.map((action, index) => `${index + 1}. ${action.name}`),
      normalizedResultActions.length ? formatResultActionLabels(normalizedResultActions) : undefined,
    ].filter((detail): detail is string => Boolean(detail));

    return [
      {
        action: (
          <Button
            block
            disabled={!selectedPrimaryPluginConnectionId}
            loading={testingConnectionId === selectedPrimaryPluginConnectionId}
            onClick={testSelectedConnection}
            size="small"
          >
            测试数据连接
          </Button>
        ),
        details: [
          ...connectionDetails,
          selectedConnections.length > 1 ? `共 ${selectedConnections.length} 个数据连接` : undefined,
          connectionTestResult ? `连接测试 ${connectionTestResult.status}` : undefined,
          connectionTestResult ? `${connectionTestResult.latency_ms}ms` : undefined,
          requestUrl,
        ].filter((detail): detail is string => Boolean(detail)),
        key: 'data_connection',
        required: connectionRequired,
        status: dataStatus,
        statusColor: dataStatus === '已配置' || dataStatus === '本地扫描' ? 'green' : connectionRequired ? 'orange' : 'default',
        title: '数据连接',
      },
      {
        details: [
          selectedModel?.name,
          selectedAgent?.name,
          skillLabels.length ? skillLabels.join('、') : undefined,
        ].filter((detail): detail is string => Boolean(detail)),
        key: 'ai_processing',
        required: aiRequired,
        status: aiStatus,
        statusColor: aiStatus === '已配置' ? 'green' : aiRequired ? 'orange' : 'default',
        title: 'AI执行',
      },
      {
        details: knowledgeLabels,
        key: 'knowledge_reference',
        required: false,
        status: knowledgeStatus,
        statusColor: knowledgeStatus === '已选择' ? 'blue' : 'default',
        title: '知识引用',
      },
      {
        details: actionDetails,
        key: 'result_action',
        required: actionRequired,
        status: actionStatus,
        statusColor: actionStatus === '已配置' ? 'green' : actionRequired ? 'orange' : 'default',
        title: '动作',
      },
    ];
  }, [
    agentById,
    aiProcessingRequiredTypes,
    connectionTestResult,
    formatResultActionLabels,
    knowledgeDocumentById,
    modelGatewayConfigById,
    normalizedSelectedPluginActionIds,
    normalizedSelectedPluginConnectionIds,
    pluginActionById,
    pluginConnectionById,
    pluginRequiredTypes,
    selectedAgentId,
    selectedConfigJsonRecord,
    selectedExecutionMode,
    selectedJobType,
    selectedKnowledgeDocumentIds,
    selectedModelGatewayConfigId,
    selectedPrimaryPluginConnectionId,
    selectedResultActions,
    selectedSkillIds,
    skillById,
    testingConnectionId,
    testSelectedConnection,
  ]);

  const findConnectionForAction = useCallback(
    (action: PluginActionRecord | undefined) => {
      if (!action) {
        return undefined;
      }
      return (
        pluginConnections.find((connection) => connection.plugin_id === action.plugin_id && connection.status === 'active')
        ?? pluginConnections.find((connection) => connection.plugin_id === action.plugin_id)
      );
    },
    [pluginConnections],
  );

  const findActionForTemplate = useCallback(
    (template: ScheduledJobTemplateRecord | undefined) => {
      const selector = templateSelector(template, 'plugin_action');
      const codeCandidates = stringArrayFromUnknown(selector.code_candidates);
      const textCandidates = stringArrayFromUnknown(selector.text_candidates).map((candidate) =>
        candidate.toLowerCase(),
      );
      return (
        pluginActions.find(
          (action) => action.status === 'active' && codeCandidates.includes(action.code),
        )
        ?? pluginActions.find((action) => codeCandidates.includes(action.code))
        ?? pluginActions.find((action) => {
          const text = `${action.code} ${action.name}`.toLowerCase();
          return action.status === 'active' && textCandidates.some((candidate) => text.includes(candidate));
        })
        ?? pluginActions.find((action) => {
          const text = `${action.code} ${action.name}`.toLowerCase();
          return textCandidates.some((candidate) => text.includes(candidate));
        })
      );
    },
    [pluginActions],
  );

  const applyJobTemplate = useCallback(
    (templateCode?: string) => {
      const template = availableJobTemplates.find((item) => item.code === templateCode);
      if (!template) {
        return;
      }
      const productId = products[0]?.id;
      const modelGatewayConfigId = modelGatewayConfigs[0]?.id;
      const agentId = agents[0]?.id;
      const skillIds = skills[0]?.id ? [skills[0].id] : [];
      const knowledgeDocumentIds = knowledgeDocuments[0]?.id ? [knowledgeDocuments[0].id] : [];

      const action = findActionForTemplate(template);
      const payloadActionIds = uniqueStringList([
        ...(templatePayloadList(template, 'plugin_action_ids') ?? []),
        templatePayloadString(template, 'plugin_action_id'),
      ]);
      const pluginActionIds = payloadActionIds.length ? payloadActionIds : uniqueStringList([action?.id]);
      const primaryAction = pluginActionIds.length ? pluginActionById.get(pluginActionIds[0]) ?? action : action;
      const connection = findConnectionForAction(primaryAction);
      const payloadConnectionIds = uniqueStringList([
        ...(templatePayloadList(template, 'plugin_connection_ids') ?? []),
        templatePayloadString(template, 'plugin_connection_id'),
      ]);
      const pluginConnectionIds = payloadConnectionIds.length
        ? payloadConnectionIds
        : uniqueStringList([connection?.id]);
      const primaryConnectionId = primaryId(pluginConnectionIds);
      const primaryConnection = primaryConnectionId
        ? pluginConnectionById.get(primaryConnectionId) ?? connection
        : connection;
      const jobType = templatePayloadString(template, 'job_type') ?? 'plugin_action_invoke';
      const templateConfigJson = templatePayloadRecordValue(template, 'config_json') ?? {};
      const nativeCodeScan = codeInspectionUsesNativeScan(jobType, templateConfigJson);
      const executionMode = templatePayloadString(template, 'execution_mode') ?? 'deterministic';
      const aiRequired = requiresAiAssembly(jobType, executionMode, aiProcessingRequiredTypes);
      form.setFieldsValue({
        agent_id: aiRequired ? agentId : undefined,
        config_json: templateConfigJson,
        connection_environment: nativeCodeScan ? undefined : primaryConnection?.environment ?? undefined,
        cron_expression: templatePayloadString(template, 'cron_expression'),
        enabled: templatePayloadBoolean(template, 'enabled', true),
        execution_mode: executionMode,
        interval_seconds: templatePayloadNumber(template, 'interval_seconds'),
        job_type: jobType,
        knowledge_document_ids:
          templatePayloadList(template, 'knowledge_document_ids')
          ?? (aiRequired ? knowledgeDocumentIds : []),
        model_gateway_config_id: aiRequired ? modelGatewayConfigId : undefined,
        name: templatePayloadString(template, 'name') ?? template.name,
        plugin_action_id: nativeCodeScan ? undefined : primaryId(pluginActionIds),
        plugin_action_ids: nativeCodeScan ? [] : pluginActionIds,
        plugin_connection_id: nativeCodeScan ? undefined : primaryId(pluginConnectionIds),
        plugin_connection_ids: nativeCodeScan ? [] : pluginConnectionIds,
        plugin_input_mapping: templatePayloadRecordValue(template, 'plugin_input_mapping'),
        plugin_output_mapping: templatePayloadRecordValue(template, 'plugin_output_mapping'),
        product_id: productId,
        result_actions: templatePayloadResultActions(template) ?? [],
        schedule_type: templatePayloadString(template, 'schedule_type') ?? 'manual',
        skill_ids: templatePayloadList(template, 'skill_ids') ?? (aiRequired ? skillIds : []),
        source_system: templatePayloadString(template, 'source_system') ?? 'ai-brain',
        template: template.code,
      });
    },
    [
      agents,
      aiProcessingRequiredTypes,
      findActionForTemplate,
      findConnectionForAction,
      form,
      availableJobTemplates,
      knowledgeDocuments,
      modelGatewayConfigs,
      pluginActionById,
      pluginConnectionById,
      products,
      skills,
    ],
  );

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [
        nextJobs,
        nextRuns,
        nextRunObservability,
        nextJobTemplates,
        nextJobCatalog,
        nextPluginActions,
        nextPluginConnections,
        nextProducts,
        nextAgents,
        nextSkills,
        nextKnowledgeDocuments,
        nextModelGatewayConfigs,
      ] =
        await Promise.all([
          fetchScheduledJobs(),
          fetchScheduledJobRuns(),
          fetchScheduledJobRunObservability(),
          fetchScheduledJobTemplates(),
          fetchScheduledJobCatalog().catch(() => undefined),
          fetchPluginActions(),
          fetchPluginConnections(),
          fetchActiveProductOptions(),
          fetchAiAgents(),
          fetchAiSkills(),
          fetchManagementKnowledge(),
          fetchModelGatewayConfigs(),
        ]);
      setJobs(nextJobs);
      setRuns(nextRuns);
      setRunObservability(nextRunObservability);
      setJobTemplates(nextJobTemplates);
      if (nextJobCatalog) {
        setJobCatalog(nextJobCatalog);
      }
      setPluginActions(nextPluginActions);
      setPluginConnections(nextPluginConnections);
      setProducts(nextProducts);
      setAgents(nextAgents.filter((agent) => agent.status === 'active'));
      setSkills(nextSkills.filter((skill) => skill.status === 'active'));
      setKnowledgeDocuments(
        nextKnowledgeDocuments.filter((document) =>
          ['indexed', 'text_indexed', 'vector_indexed'].includes(document.status),
        ),
      );
      setModelGatewayConfigs(nextModelGatewayConfigs.filter((config) => config.status === 'active'));
    } catch (error) {
      message.error(error instanceof Error ? error.message : '定时作业加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      void reload();
    });
  }, [reload]);

  useEffect(() => {
    const routeParams = scheduledJobRouteParams();
    const routeTab = routeParams.tab;
    if (routeTab) {
      queueMicrotask(() => {
        setActiveTab(routeTab);
      });
    }
    const routeRunKey = routeParams.runId
      ? `${routeParams.runId}:${routeParams.resultWriteRecordId ?? ''}`
      : undefined;
    if (!routeParams.runId || handledRouteRunKey === routeRunKey) {
      return;
    }
    const routeRun = runs.find((run) => run.id === routeParams.runId);
    if (!routeRun) {
      return;
    }
    queueMicrotask(() => {
      setActiveTab('runs');
      setLinkedResultWriteRecordId(routeParams.resultWriteRecordId);
      setSelectedRun(routeRun);
      setHandledRouteRunKey(routeRunKey);
    });
  }, [handledRouteRunKey, runs]);

  useEffect(() => {
    if (!selectedRun?.id) {
      queueMicrotask(() => {
        setSelectedRunResultWriteRecords([]);
        setSelectedRunResultWriteRecordsLoading(false);
      });
      return;
    }
    let ignore = false;
    queueMicrotask(() => {
      setSelectedRunResultWriteRecordsLoading(true);
    });
    fetchResultWriteRecords({ scheduledJobRunId: selectedRun.id })
      .then((records) => {
        if (!ignore) {
          setSelectedRunResultWriteRecords(records);
        }
      })
      .catch((error) => {
        if (!ignore) {
          setSelectedRunResultWriteRecords([]);
          message.error(error instanceof Error ? error.message : '结果写入记录加载失败');
        }
      })
      .finally(() => {
        if (!ignore) {
          setSelectedRunResultWriteRecordsLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [selectedRun?.id]);

  useEffect(() => {
    if (typeof window === 'undefined' || modalOpen || editingJob) {
      return;
    }
    const storageKey = assistantScopedStorageKey(ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY);
    const rawDraft = window.sessionStorage.getItem(storageKey);
    if (!rawDraft) {
      return;
    }
    window.sessionStorage.removeItem(storageKey);
    try {
      const draft = JSON.parse(rawDraft) as AssistantScheduledJobDraft;
      if (!draft.payload || typeof draft.payload !== 'object' || Array.isArray(draft.payload)) {
        throw new Error('Invalid scheduled job draft payload');
      }
      const draftValues = scheduledJobValuesFromAssistantDraft(draft);
      queueMicrotask(() => {
        setEditingJob(undefined);
        setAssistantDraftPayload(draft.payload);
        setAssistantDraftInitialValues(draftValues);
        setAssistantDraftSource({ draftId: draft.draftId, title: draft.title });
        setConnectionTestResult(undefined);
        form.resetFields();
        form.setFieldsValue(draftValues);
        setModalOpen(true);
        message.success('已载入 AI 助手生成的定时作业草案，请确认后保存');
      });
    } catch {
      queueMicrotask(() => {
        setAssistantDraftPayload(undefined);
        setAssistantDraftInitialValues(undefined);
        setAssistantDraftSource(undefined);
        message.error('AI 助手定时作业草案格式无效');
      });
    }
  }, [editingJob, form, modalOpen]);

  const openCreateJobModal = () => {
    setEditingJob(undefined);
    setAssistantDraftPayload(undefined);
    setAssistantDraftInitialValues(undefined);
    setAssistantDraftSource(undefined);
    setTemplateSource(undefined);
    setGeneratedRunTemplate(undefined);
    setConnectionTestResult(undefined);
    setDryRunResult(undefined);
    form.resetFields();
    form.setFieldsValue({
      enabled: true,
      execution_mode: 'ai_generated',
      job_type: 'user_feedback_insight_extract',
      schedule_type: 'manual',
      source_system: 'ai-brain',
      template: undefined,
    });
    setModalOpen(true);
  };

  const openCopyJobModal = (job: ScheduledJobRecord) => {
    const values = scheduledJobTemplateValuesFromRecord(job as unknown as Record<string, unknown>, {
      fallback: job,
      pluginConnectionById,
    });
    setEditingJob(undefined);
    setAssistantDraftPayload(undefined);
    setAssistantDraftInitialValues(undefined);
    setAssistantDraftSource(undefined);
    setGeneratedRunTemplate(undefined);
    setConnectionTestResult(undefined);
    setDryRunResult(undefined);
    setTemplateSource({
      sourceId: job.id,
      sourceType: 'scheduled_job',
      title: job.name,
      values,
    });
    form.resetFields();
    form.setFieldsValue(values);
    setModalOpen(true);
    message.success('已复制为新作业草稿，请确认后保存');
  };

  const openCopyRunModal = (run: ScheduledJobRunRecord) => {
    const sourceJob = run.scheduled_job_id ? jobById.get(run.scheduled_job_id) : undefined;
    const snapshot = run.config_snapshot ?? {};
    const values = scheduledJobTemplateValuesFromRecord(snapshot, {
      fallback: sourceJob,
      nameSuffix: '运行快照副本',
      pluginConnectionById,
    });
    setSelectedRun(undefined);
    setLinkedResultWriteRecordId(undefined);
    setEditingJob(undefined);
    setAssistantDraftPayload(undefined);
    setAssistantDraftInitialValues(undefined);
    setAssistantDraftSource(undefined);
    setGeneratedRunTemplate(undefined);
    setConnectionTestResult(undefined);
    setDryRunResult(undefined);
    setTemplateSource({
      sourceId: run.id,
      sourceType: 'scheduled_job_run',
      title: run.scheduled_job_id ?? run.id,
      values,
    });
    form.resetFields();
    form.setFieldsValue(values);
    setModalOpen(true);
    message.success('已按本次运行快照生成新作业草稿，请确认后保存');
  };

  const generateTemplateFromRun = async (run: ScheduledJobRunRecord) => {
    try {
      const template = await generateScheduledJobTemplateFromRun(run.id);
      const payloadDefaults = (template.payload_defaults ?? {}) as Record<string, unknown>;
      const values = scheduledJobTemplateValuesFromRecord(payloadDefaults, {
        fallback: template.payload_defaults,
        nameSuffix: '',
        pluginConnectionById,
      });
      const jobType = values.job_type ?? 'user_feedback_insight_extract';
      const executionMode = values.execution_mode ?? 'ai_generated';
      const aiRequired = requiresAiAssembly(jobType, executionMode, aiProcessingRequiredTypes);
      const enrichedValues = {
        ...values,
        agent_id: aiRequired ? values.agent_id ?? agents[0]?.id : values.agent_id,
        model_gateway_config_id: aiRequired
          ? values.model_gateway_config_id ?? modelGatewayConfigs[0]?.id
          : values.model_gateway_config_id,
        product_id: values.product_id ?? products[0]?.id,
        skill_ids:
          values.skill_ids?.length
            ? values.skill_ids
            : aiRequired && skills[0]?.id
              ? [skills[0].id]
              : [],
      };
      setSelectedRun(undefined);
      setLinkedResultWriteRecordId(undefined);
      setEditingJob(undefined);
      setAssistantDraftPayload(undefined);
      setAssistantDraftInitialValues(undefined);
      setAssistantDraftSource(undefined);
      setConnectionTestResult(undefined);
      setDryRunResult(undefined);
      setGeneratedRunTemplate(template);
      setTemplateSource({
        sourceId: run.id,
        sourceType: 'scheduled_job_run',
        title: template.name,
        values: enrichedValues,
      });
      form.resetFields();
      form.setFieldsValue({
        ...enrichedValues,
        template: template.code,
      });
      setModalOpen(true);
      message.success('已从成功运行生成作业模板');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '运行模板生成失败');
    }
  };

  const openEditJobModal = (job: ScheduledJobRecord) => {
    const pluginConnectionIds = multiIdsFromScheduledJob(job, 'plugin_connection_ids', 'plugin_connection_id');
    const pluginActionIds = multiIdsFromScheduledJob(job, 'plugin_action_ids', 'plugin_action_id');
    const primaryConnectionId = primaryId(pluginConnectionIds);
    const editConfigJson = recordValue(job.config_json) ?? {};
    if (job.job_type === 'code_repository_inspection' && !recordStringValue(editConfigJson, 'scan_mode')) {
      editConfigJson.scan_mode = 'sync_existing_alerts';
    }
    const nativeCodeScan = codeInspectionUsesNativeScan(job.job_type, editConfigJson);
    setEditingJob(job);
    setAssistantDraftPayload(undefined);
    setAssistantDraftInitialValues(undefined);
    setAssistantDraftSource(undefined);
    setTemplateSource(undefined);
    setGeneratedRunTemplate(undefined);
    setConnectionTestResult(undefined);
    setDryRunResult(undefined);
    form.resetFields();
    form.setFieldsValue({
      agent_id: job.agent_id ?? undefined,
      connection_environment: !nativeCodeScan && primaryConnectionId
        ? pluginConnectionById.get(primaryConnectionId)?.environment ?? 'default'
        : undefined,
      config_json: editConfigJson,
      cron_expression: job.cron_expression ?? undefined,
      enabled: job.enabled ?? true,
      execution_mode: job.execution_mode ?? 'deterministic',
      interval_seconds: job.interval_seconds ?? undefined,
      job_type: job.job_type,
      knowledge_document_ids: job.knowledge_document_ids ?? [],
      model_gateway_config_id: job.model_gateway_config_id ?? undefined,
      name: job.name,
      plugin_action_id: nativeCodeScan ? undefined : primaryId(pluginActionIds),
      plugin_action_ids: nativeCodeScan ? [] : pluginActionIds,
      plugin_connection_id: nativeCodeScan ? undefined : primaryConnectionId,
      plugin_connection_ids: nativeCodeScan ? [] : pluginConnectionIds,
      product_id: job.product_id ?? undefined,
      result_actions: job.result_actions?.length ? job.result_actions : defaultCodeInspectionActions,
      schedule_type: job.schedule_type ?? 'manual',
      skill_ids: job.skill_ids ?? [],
      source_system: job.source_system ?? 'ai-brain',
      template: undefined,
    });
    setModalOpen(true);
  };

  const closeJobModal = () => {
    setModalOpen(false);
    setEditingJob(undefined);
    setAssistantDraftPayload(undefined);
    setAssistantDraftInitialValues(undefined);
    setAssistantDraftSource(undefined);
    setTemplateSource(undefined);
    setGeneratedRunTemplate(undefined);
    setConnectionTestResult(undefined);
    setDryRunning(false);
    setDryRunResult(undefined);
    form.resetFields();
  };

  const buildJobRequestPayload = (values: ScheduledJobFormValues): Partial<ScheduledJobRecord> => {
    const { template, ...jobValues } = values;
    const selectedTemplate = availableJobTemplates.find((item) => item.code === template);
    delete jobValues.connection_environment;
    const pluginConnectionIds = uniqueStringList(
      Array.isArray(values.plugin_connection_ids)
        ? values.plugin_connection_ids
        : [values.plugin_connection_id],
    );
    const pluginActionIds = uniqueStringList(
      Array.isArray(values.plugin_action_ids)
        ? values.plugin_action_ids
        : [values.plugin_action_id],
    );
    jobValues.plugin_connection_id = primaryId(pluginConnectionIds) ?? null;
    jobValues.plugin_connection_ids = pluginConnectionIds;
    jobValues.plugin_action_id = primaryId(pluginActionIds) ?? null;
    jobValues.plugin_action_ids = pluginActionIds;
    const draftConfigJson = recordFromDraftPayload(assistantDraftPayload ?? {}, 'config_json') ?? {};
    const templateConfigJson = templateSource?.values.config_json ?? {};
    const templateSourceConfig =
      templateSource && !editingJob
        ? {
            template_source: {
              source_id: templateSource.sourceId,
              source_type: templateSource.sourceType,
              title: templateSource.title,
            },
          }
        : {};
    const assistantDraftConfig =
      assistantDraftPayload && !editingJob
        ? {
            assistant_draft: {
              draft_id: assistantDraftSource?.draftId,
              source: 'assistant.action_draft',
              title: assistantDraftSource?.title,
            },
          }
        : {};
    const requestPayload: Partial<ScheduledJobRecord> = {
      ...jobValues,
      config_json: scheduledJobConfigWithOrchestration(
        {
          ...(editingJob?.config_json ?? {}),
          ...templateConfigJson,
          ...draftConfigJson,
          ...(values.config_json ?? {}),
          ...templateSourceConfig,
          ...assistantDraftConfig,
        },
        pluginConnectionIds,
        pluginActionIds,
      ),
      plugin_input_mapping:
        editingJob?.plugin_input_mapping
        ?? templateSource?.values.plugin_input_mapping
        ?? values.plugin_input_mapping
        ?? recordFromDraftPayload(assistantDraftPayload ?? {}, 'plugin_input_mapping')
        ?? templatePayloadRecordValue(selectedTemplate, 'plugin_input_mapping')
        ?? {},
      plugin_output_mapping:
        editingJob?.plugin_output_mapping
        ?? templateSource?.values.plugin_output_mapping
        ?? values.plugin_output_mapping
        ?? recordFromDraftPayload(assistantDraftPayload ?? {}, 'plugin_output_mapping')
        ?? templatePayloadRecordValue(selectedTemplate, 'plugin_output_mapping')
        ?? {},
      knowledge_document_ids: values.knowledge_document_ids ?? [],
      result_actions:
        values.job_type === 'code_repository_inspection'
          ? values.result_actions?.length
            ? values.result_actions
            : templatePayloadResultActions(selectedTemplate) ?? cloneResultActions(defaultCodeInspectionActions)
          : [],
      skill_ids: values.skill_ids ?? [],
    };
    if (codeInspectionUsesNativeScan(requestPayload.job_type, requestPayload.config_json)) {
      requestPayload.plugin_action_id = null;
      requestPayload.plugin_action_ids = [];
      requestPayload.plugin_connection_id = null;
      requestPayload.plugin_connection_ids = [];
      requestPayload.config_json = scheduledJobConfigWithOrchestration(
        recordValue(requestPayload.config_json) ?? {},
        [],
        [],
      );
    }
    return requestPayload;
  };

  const currentValidatedJobPayload = async () => {
    await form.validateFields();
    return buildJobRequestPayload(form.getFieldsValue(true) as ScheduledJobFormValues);
  };

  const dryRunJob = async () => {
    let requestPayload: Partial<ScheduledJobRecord>;
    try {
      requestPayload = await currentValidatedJobPayload();
    } catch {
      return;
    }
    const hide = message.loading('正在进行全链路试运行，请稍候...', 0);
    setDryRunning(true);
    try {
      const result = await dryRunScheduledJob(requestPayload);
      setDryRunResult(result);
      if (result.status === 'succeeded') {
        message.success('全链路试运行完成');
      } else {
        message.error(`全链路试运行 ${result.status}`);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '全链路试运行失败');
    } finally {
      hide();
      setDryRunning(false);
    }
  };

  const submitJob = async () => {
    let requestPayload: Partial<ScheduledJobRecord>;
    let formValues: ScheduledJobFormValues;
    try {
      await form.validateFields();
      formValues = form.getFieldsValue(true) as ScheduledJobFormValues;
      requestPayload = buildJobRequestPayload(formValues);
    } catch {
      return;
    }
    if (editingJob) {
      await updateScheduledJob(editingJob.id, requestPayload);
      message.success('定时作业已更新');
    } else if (assistantDraftSource?.draftId && assistantDraftInitialValues) {
      const initialPayload = buildJobRequestPayload(assistantDraftInitialValues);
      const modifiedFields = scheduledJobAssistantDraftModifiedFields(
        initialPayload,
        requestPayload,
      );
      await updateAssistantActionDraft(
        assistantDraftSource.draftId,
        requestPayload as Record<string, unknown>,
        modifiedFields,
      );
      const confirmed = await confirmAssistantActionDraft(assistantDraftSource.draftId);
      rememberAssistantDraftResolution({
        draftId: assistantDraftSource.draftId,
        resourceId: confirmed.run.result_id,
        resourceType: 'scheduled_job',
        scheduledJobRunId: scheduledJobRunIdFromAssistantResult(confirmed.run.result),
        title: assistantDraftSource.title ?? formValues.name,
      });
      message.success('助手草案已确认并创建定时作业');
    } else {
      await createScheduledJob(requestPayload);
      message.success('定时作业已创建');
    }
    closeJobModal();
    await reload();
  };

  const triggerJobRun = async (
    jobId: string,
    triggerType: 'manual' | 'manual_rerun' = 'manual',
    sourceRunId?: string,
  ) => {
    const hide = message.loading('作业执行中，请稍候...', 0);
    setRunningJobId(jobId);
    try {
      const run = await runScheduledJob(jobId, triggerType, sourceRunId);
      setLinkedResultWriteRecordId(undefined);
      setSelectedRun(run);
      if (run.status === 'succeeded') {
        message.success('作业运行完成');
      } else if (run.status === 'running' || run.status === 'queued') {
        message.info(`作业${run.status === 'queued' ? '已排队' : '运行中'}，请在运行记录查看进度`);
      } else {
        message.error(run.error_message ? `作业运行失败：${run.error_message}` : `作业运行 ${run.status}`);
      }
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '作业运行失败');
    } finally {
      hide();
      setRunningJobId(undefined);
    }
  };

  const triggerJob = async (job: ScheduledJobRecord) => {
    await triggerJobRun(job.id);
  };

  const confirmDeleteJob = (job: ScheduledJobRecord) => {
    Modal.confirm({
      title: '删除定时作业',
      content: `确定删除「${job.name}」吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        await deleteScheduledJob(job.id);
        message.success('定时作业已删除');
        await reload();
      },
    });
  };

  return (
    <PageContainer title="定时作业">
      <Tabs
        activeKey={activeTab}
        onChange={(key) => setActiveTab(key === 'runs' ? 'runs' : 'jobs')}
        items={[
          {
            key: 'jobs',
            label: '作业配置',
            children: (
              <ScheduledJobConfigTable
                agentById={agentById}
                confirmDeleteJob={confirmDeleteJob}
                executionModeLabelMap={executionModeLabelMap}
                formatResultActionLabels={formatResultActionLabels}
                jobTypeLabelMap={jobTypeLabelMap}
                jobs={jobs}
                loading={loading}
                modelGatewayConfigById={modelGatewayConfigById}
                onCopyJob={openCopyJobModal}
                onCreateJob={openCreateJobModal}
                onEditJob={openEditJobModal}
                onReload={reload}
                onRunJob={triggerJob}
                pluginActionById={pluginActionById}
                pluginConnectionById={pluginConnectionById}
                runningJobId={runningJobId}
                scheduleTypeLabelMap={scheduleTypeLabelMap}
              />
            ),
          },
          {
            key: 'runs',
            label: '运行记录',
            children: (
              <ScheduledJobRunTable
                loading={loading}
                observability={runObservability}
                onCopyRun={openCopyRunModal}
                onOpenRunDetail={(row) => {
                  setLinkedResultWriteRecordId(undefined);
                  setSelectedRun(row);
                }}
                onReload={reload}
                onRerun={(row) => {
                  if (row.scheduled_job_id) {
                    void triggerJobRun(row.scheduled_job_id, 'manual_rerun', row.id);
                  }
                }}
                runningJobId={runningJobId}
                runs={runs}
              />
            ),
          },
        ]}
      />

      <Modal
        aria-label={editingJob ? '编辑定时作业' : '新增定时作业'}
        destroyOnHidden
        footer={(
          <Space>
            <Button htmlType="button" onClick={closeJobModal}>取消</Button>
            <Button
              htmlType="button"
              loading={dryRunning}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                void dryRunJob();
              }}
            >
              全链路试运行
            </Button>
            <Button htmlType="button" type="primary" onClick={() => void submitJob()}>
              确定
            </Button>
          </Space>
        )}
        open={modalOpen}
        title={editingJob ? '编辑定时作业' : '新增定时作业'}
        width={820}
        onCancel={closeJobModal}
      >
        {templateSource ? (
          <div
            aria-label="当前复制来源"
            style={{
              background: '#f8fafc',
              border: '1px solid #e5e7eb',
              borderRadius: 6,
              marginBottom: 16,
              padding: '10px 12px',
            }}
          >
            <Space wrap>
              <Typography.Text type="secondary">复制来源</Typography.Text>
              <TemplateSourceSummary source={templateSource} />
            </Space>
          </div>
        ) : null}
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            enabled: true,
            execution_mode: 'ai_generated',
            job_type: 'user_feedback_insight_extract',
            schedule_type: 'manual',
            source_system: 'ai-brain',
          }}
        >
          {!editingJob ? (
            <Form.Item label="作业模板" name="template">
              <Select
                allowClear
                options={jobTemplateOptions}
                placeholder="请选择场景模板快速生成配置"
                onChange={applyJobTemplate}
              />
            </Form.Item>
          ) : null}
          <ScheduledJobOrchestrationFlow
            nodes={orchestrationNodes}
            wizardSteps={selectedJobTemplate?.wizard_steps}
          />
          <Form.Item hidden name="source_system">
            <Input />
          </Form.Item>
          <ScheduledJobBasicInfoSection
            jobTypeOptions={jobTypeSelectOptions}
            onJobTypeChange={(value) => {
              if (value === 'code_repository_inspection') {
                form.setFieldsValue({
                  config_json: {
                    ...(recordValue(form.getFieldValue('config_json')) ?? {}),
                    scan_mode: nativeCodeInspectionScanMode,
                  },
                  execution_mode: 'deterministic',
                  plugin_action_id: undefined,
                  plugin_action_ids: [],
                  plugin_connection_id: undefined,
                  plugin_connection_ids: [],
                  result_actions: form.getFieldValue('result_actions')?.length
                    ? form.getFieldValue('result_actions')
                    : cloneResultActions(defaultCodeInspectionActions),
                });
              }
            }}
            onProductChange={() => {
              if (selectedJobType === 'code_repository_inspection') {
                form.setFieldValue(['config_json', 'repository_id'], undefined);
                form.setFieldValue(['config_json', 'branch'], undefined);
              }
            }}
            productOptions={products.map((product) => ({
              label: `${product.name} (${product.code})`,
              value: product.id,
            }))}
            productRequiredRule={productRequiredRuleFactory('请选择产品')}
          />
          <ScheduledJobDataConnectionSection
            connectionEnvironmentOptions={connectionEnvironmentSelectOptions}
            filteredPluginConnections={filteredPluginConnections}
            onConnectionEnvironmentChange={handleConnectionEnvironmentChange}
            onPluginConnectionChange={handlePluginConnectionChange}
            requiredForPluginResource={pluginResourceRuleFactory}
            usesNativeScan={selectedCodeInspectionUsesNativeScan}
          />
          {selectedJobType === 'code_repository_inspection' ? (
            <ScheduledJobCodeRepositorySection
              builtinRuleOptions={codeInspectionBuiltinRuleSelectOptions}
              ignoreRuleOptions={codeInspectionIgnoreRuleSelectOptions}
              loadingRepositories={productRepositoriesLoading}
              onRepositoryChange={handleCodeInspectionRepositoryChange}
              onScanModeChange={(value) => {
                if (value === nativeCodeInspectionScanMode) {
                  form.setFieldValue('plugin_connection_id', undefined);
                  form.setFieldValue('plugin_connection_ids', []);
                  form.setFieldValue('plugin_action_id', undefined);
                  form.setFieldValue('plugin_action_ids', []);
                  form.setFieldValue(['config_json', 'async_execution'], true);
                  form.setFieldValue(['config_json', 'scanner_engines'], ['builtin']);
                  form.setFieldValue(['config_json', 'scan_rules'], ['secrets', 'internal_addresses']);
                }
              }}
              repositories={productRepositories}
              scanModeOptions={codeInspectionScanModeSelectOptions}
              scannerEngineOptions={codeInspectionScannerEngineSelectOptions}
              selectedRepositoryDefaultBranch={selectedRepositoryDefaultBranch}
              severityThresholdOptions={severityThresholdSelectOptions}
            />
          ) : null}
          <ScheduledJobAiExecutionSection
            agents={agents}
            executionModeOptions={executionModeSelectOptions}
            knowledgeDocuments={knowledgeDocuments}
            modelGatewayConfigs={modelGatewayConfigs}
            requiredForAiAssembly={aiAssemblyRuleFactory}
            skills={skills}
          />
          <ScheduledJobActionConfigSection
            codeInspectionResultActionOptions={codeInspectionResultActionSelectOptions}
            isCodeInspectionJob={selectedJobType === 'code_repository_inspection'}
            pluginActions={pluginActions}
            requiredForPluginResource={pluginResourceRuleFactory}
            severityThresholdOptions={severityThresholdSelectOptions}
            usesNativeScan={selectedCodeInspectionUsesNativeScan}
            writeStrategyLabelFromAction={writeStrategyLabelFromAction}
          />
          <ScheduledJobScheduleConfigSection scheduleTypeOptions={scheduleTypeSelectOptions} />
          {dryRunResult ? <ScheduledJobDryRunResultPanel result={dryRunResult} /> : null}
        </Form>
      </Modal>

      <ScheduledJobRunDetailModal
        agentLabel={selectedRunAgentLabel}
        executionModeLabel={selectedRunExecutionModeLabel}
        focusedResultWriteRecordId={linkedResultWriteRecordId}
        jobTypeLabel={selectedRunJobTypeLabel}
        modelLabel={selectedRunModelLabel}
        onClose={() => {
          setSelectedRun(undefined);
          setLinkedResultWriteRecordId(undefined);
        }}
        onCopyRun={openCopyRunModal}
        onGenerateTemplate={generateTemplateFromRun}
        resultWriteRecords={selectedRunResultWriteRecords}
        resultWriteRecordsLoading={selectedRunResultWriteRecordsLoading}
        run={selectedRun}
        skillLabels={selectedRunSkillLabels}
      />
    </PageContainer>
  );
}
