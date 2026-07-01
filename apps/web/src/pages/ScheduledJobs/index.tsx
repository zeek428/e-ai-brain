import { PageContainer } from '@ant-design/pro-components';
import {
  Form,
  Modal,
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
  fetchProductGitRepositories,
  generateScheduledJobTemplateFromRun,
  rememberAssistantDraftResolution,
  runScheduledJob,
  testPluginConnection,
  updateScheduledJob,
  updateAssistantActionDraft,
  type AssistantScheduledJobDraft,
  type PluginActionRecord,
  type PluginConnectionTestResult,
  type ProductGitRepositoryOption,
  type ScheduledJobRecord,
  type ScheduledJobDryRunResult,
  type ScheduledJobRunRecord,
  type ScheduledJobTemplateRecord,
} from '../../services/aiBrain';
import { ScheduledJobFormModal } from './components/ScheduledJobFormModal';
import { ScheduledJobManagementTabs } from './components/ScheduledJobManagementTabs';
import { ScheduledJobRunDetailModal } from './components/ScheduledJobRunDetailModal';
import { useScheduledJobCatalogOptions } from './components/scheduledJobCatalogOptions';
import { buildScheduledJobOrchestrationNodes } from './components/scheduledJobOrchestrationNodeBuilder';
import { useScheduledJobWorkspaceData } from './components/useScheduledJobWorkspaceData';
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
import { useScheduledJobRunDetailState } from './components/useScheduledJobRunDetailState';

function writeStrategyLabelFromAction(action: PluginActionRecord): string {
  const mapping = action.result_mapping ?? {};
  const writeTargetLabel = typeof mapping.write_target_label === 'string' ? mapping.write_target_label : undefined;
  const writeTarget = typeof mapping.write_target === 'string' ? mapping.write_target : undefined;
  return action.name || writeTargetLabel || writeTarget || action.id;
}

export default function ScheduledJobsPage() {
  const [form] = Form.useForm<ScheduledJobFormValues>();
  const {
    agents,
    jobCatalog,
    jobListMeta,
    jobTemplates,
    jobs,
    knowledgeDocuments,
    loading,
    modelGatewayConfigs,
    pluginActions,
    pluginConnections,
    products,
    reload,
    runObservability,
    runListMeta,
    runs,
    onJobListChange,
    onRunListChange,
    skills,
  } = useScheduledJobWorkspaceData();
  const [productRepositories, setProductRepositories] = useState<ProductGitRepositoryOption[]>([]);
  const [productRepositoriesLoading, setProductRepositoriesLoading] = useState(false);
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
  const [templateSource, setTemplateSource] = useState<ScheduledJobTemplateSource | undefined>();
  const [generatedRunTemplate, setGeneratedRunTemplate] = useState<ScheduledJobTemplateRecord | undefined>();
  const [runningJobId, setRunningJobId] = useState<string | undefined>();
  const [connectionTestResult, setConnectionTestResult] = useState<PluginConnectionTestResult | undefined>();
  const [testingConnectionId, setTestingConnectionId] = useState<string | undefined>();
  const [dryRunResult, setDryRunResult] = useState<ScheduledJobDryRunResult | undefined>();
  const [dryRunning, setDryRunning] = useState(false);
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
        const matchesSelectedActionPlugin =
          connectionPluginFilterIds.size === 0
          || connectionPluginFilterIds.has(String(connection.plugin_id));
        return matchesSelectedActionPlugin;
      }),
    [connectionPluginFilterIds, pluginConnections],
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
  const {
    closeRunDetail,
    focusedResultWriteRecordId,
    labels: selectedRunLabels,
    openRunDetail,
    resultWriteRecords: selectedRunResultWriteRecords,
    resultWriteRecordsLoading: selectedRunResultWriteRecordsLoading,
    selectedRun,
  } = useScheduledJobRunDetailState({
    agentById,
    executionModeLabelMap,
    jobTypeLabelMap,
    modelGatewayConfigById,
    runs,
    skillById,
    onRouteTabChange: setActiveTab,
  });

  useEffect(() => {
    if (normalizedSelectedPluginConnectionIds.length === 0) {
      return;
    }
    const nextConnectionIds = normalizedSelectedPluginConnectionIds.filter((connectionId) => {
      const connection = pluginConnectionById.get(connectionId);
      if (!connection) {
        return false;
      }
      const matchesSelectedActionPlugin =
        connectionPluginFilterIds.size === 0
        || connectionPluginFilterIds.has(String(connection.plugin_id));
      return matchesSelectedActionPlugin;
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

  const orchestrationNodes = useMemo(
    () =>
      buildScheduledJobOrchestrationNodes({
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
      }),
    [
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
    ],
  );

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
      const jobType = templatePayloadString(template, 'job_type') ?? 'plugin_action_invoke';
      const templateConfigJson = templatePayloadRecordValue(template, 'config_json') ?? {};
      const nativeCodeScan = codeInspectionUsesNativeScan(jobType, templateConfigJson);
      const executionMode = templatePayloadString(template, 'execution_mode') ?? 'deterministic';
      const aiRequired = requiresAiAssembly(jobType, executionMode, aiProcessingRequiredTypes);
      form.setFieldsValue({
        agent_id: aiRequired ? agentId : undefined,
        config_json: templateConfigJson,
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
      products,
      skills,
    ],
  );

  useEffect(() => {
    const routeParams = scheduledJobRouteParams();
    const routeTab = routeParams.tab;
    if (routeTab) {
      queueMicrotask(() => {
        setActiveTab(routeTab);
      });
    }
  }, []);

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
    });
    closeRunDetail();
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
      closeRunDetail();
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
      openRunDetail(run);
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

  const handleJobTypeChange = (value?: string) => {
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
  };

  const handleProductChange = () => {
    if (selectedJobType === 'code_repository_inspection') {
      form.setFieldValue(['config_json', 'repository_id'], undefined);
      form.setFieldValue(['config_json', 'branch'], undefined);
    }
  };

  const handleScanModeChange = (value?: string) => {
    if (value === nativeCodeInspectionScanMode) {
      form.setFieldValue('plugin_connection_id', undefined);
      form.setFieldValue('plugin_connection_ids', []);
      form.setFieldValue('plugin_action_id', undefined);
      form.setFieldValue('plugin_action_ids', []);
      form.setFieldValue(['config_json', 'async_execution'], true);
      form.setFieldValue(['config_json', 'scanner_engines'], ['builtin']);
      form.setFieldValue(['config_json', 'scan_rules'], ['secrets', 'internal_addresses']);
    }
  };

  return (
    <PageContainer title={false}>
      <ScheduledJobManagementTabs
        activeTab={activeTab}
        agentById={agentById}
        confirmDeleteJob={confirmDeleteJob}
        executionModeLabelMap={executionModeLabelMap}
        formatResultActionLabels={formatResultActionLabels}
        jobListMeta={jobListMeta}
        jobTypeLabelMap={jobTypeLabelMap}
        jobs={jobs}
        loading={loading}
        modelGatewayConfigById={modelGatewayConfigById}
        pluginActionById={pluginActionById}
        pluginConnectionById={pluginConnectionById}
        runListMeta={runListMeta}
        runObservability={runObservability}
        runningJobId={runningJobId}
        runs={runs}
        scheduleTypeLabelMap={scheduleTypeLabelMap}
        onCopyJob={openCopyJobModal}
        onCopyRun={openCopyRunModal}
        onCreateJob={openCreateJobModal}
        onEditJob={openEditJobModal}
        onJobListChange={onJobListChange}
        onOpenRunDetail={(row) => openRunDetail(row)}
        onReload={reload}
        onRerun={(row) => {
          if (row.scheduled_job_id) {
            void triggerJobRun(row.scheduled_job_id, 'manual_rerun', row.id);
          }
        }}
        onRunListChange={onRunListChange}
        onRunJob={triggerJob}
        onTabChange={setActiveTab}
      />

      <ScheduledJobFormModal
        agents={agents}
        aiAssemblyRuleFactory={aiAssemblyRuleFactory}
        codeInspectionBuiltinRuleSelectOptions={codeInspectionBuiltinRuleSelectOptions}
        codeInspectionIgnoreRuleSelectOptions={codeInspectionIgnoreRuleSelectOptions}
        codeInspectionResultActionOptions={codeInspectionResultActionSelectOptions}
        codeInspectionScanModeSelectOptions={codeInspectionScanModeSelectOptions}
        codeInspectionScannerEngineSelectOptions={codeInspectionScannerEngineSelectOptions}
        dryRunResult={dryRunResult}
        dryRunning={dryRunning}
        editingJob={editingJob}
        executionModeSelectOptions={executionModeSelectOptions}
        filteredPluginConnections={filteredPluginConnections}
        form={form}
        jobTemplateOptions={jobTemplateOptions}
        jobTypeSelectOptions={jobTypeSelectOptions}
        knowledgeDocuments={knowledgeDocuments}
        loadingRepositories={productRepositoriesLoading}
        modalOpen={modalOpen}
        modelGatewayConfigs={modelGatewayConfigs}
        orchestrationNodes={orchestrationNodes}
        pluginActions={pluginActions}
        productOptions={products.map((product) => ({
          label: `${product.name} (${product.code})`,
          value: product.id,
        }))}
        productRepositories={productRepositories}
        productRequiredRule={productRequiredRuleFactory('请选择产品')}
        requiredForPluginResource={pluginResourceRuleFactory}
        scheduleTypeSelectOptions={scheduleTypeSelectOptions}
        selectedJobTemplate={selectedJobTemplate}
        selectedJobType={selectedJobType}
        selectedRepositoryDefaultBranch={selectedRepositoryDefaultBranch}
        severityThresholdSelectOptions={severityThresholdSelectOptions}
        skills={skills}
        templateSource={templateSource}
        usesNativeScan={selectedCodeInspectionUsesNativeScan}
        writeStrategyLabelFromAction={writeStrategyLabelFromAction}
        onApplyJobTemplate={applyJobTemplate}
        onClose={closeJobModal}
        onDryRun={dryRunJob}
        onJobTypeChange={handleJobTypeChange}
        onPluginConnectionChange={handlePluginConnectionChange}
        onProductChange={handleProductChange}
        onRepositoryChange={handleCodeInspectionRepositoryChange}
        onScanModeChange={handleScanModeChange}
        onSubmit={submitJob}
      />

      <ScheduledJobRunDetailModal
        agentLabel={selectedRunLabels.agentLabel}
        executionModeLabel={selectedRunLabels.executionModeLabel}
        focusedResultWriteRecordId={focusedResultWriteRecordId}
        jobTypeLabel={selectedRunLabels.jobTypeLabel}
        modelLabel={selectedRunLabels.modelLabel}
        onClose={closeRunDetail}
        onCopyRun={openCopyRunModal}
        onGenerateTemplate={generateTemplateFromRun}
        resultWriteRecords={selectedRunResultWriteRecords}
        resultWriteRecordsLoading={selectedRunResultWriteRecordsLoading}
        run={selectedRun}
        skillLabels={selectedRunLabels.skillLabels}
      />
    </PageContainer>
  );
}
