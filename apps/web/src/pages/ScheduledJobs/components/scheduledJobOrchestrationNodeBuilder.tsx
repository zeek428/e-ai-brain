import { Button } from 'antd';

import type { KnowledgeRecord, ModelGatewayConfigRecord } from '../../../data/management';
import type {
  AiAgentRecord,
  AiSkillRecord,
  PluginActionRecord,
  PluginConnectionRecord,
  PluginConnectionTestResult,
  ScheduledJobResultAction,
} from '../../../services/aiBrain';
import type { ScheduledJobOrchestrationNode } from './ScheduledJobOrchestrationFlow';
import {
  codeInspectionUsesNativeScan,
  requiresAiAssembly,
} from './scheduledJobFormTransformHelpers';

export type ScheduledJobOrchestrationNodeBuilderInput = {
  agentById: Map<string, AiAgentRecord>;
  aiProcessingRequiredTypes: string[];
  connectionTestResult?: PluginConnectionTestResult;
  formatResultActionLabels: (actions: ScheduledJobResultAction[]) => string;
  knowledgeDocumentById: Map<string, KnowledgeRecord>;
  modelGatewayConfigById: Map<string, ModelGatewayConfigRecord>;
  normalizedSelectedPluginActionIds: string[];
  normalizedSelectedPluginConnectionIds: string[];
  pluginActionById: Map<string, PluginActionRecord>;
  pluginConnectionById: Map<string, PluginConnectionRecord>;
  pluginRequiredTypes: string[];
  selectedAgentId?: unknown;
  selectedConfigJsonRecord: Record<string, unknown>;
  selectedExecutionMode?: unknown;
  selectedJobType?: unknown;
  selectedKnowledgeDocumentIds?: unknown;
  selectedModelGatewayConfigId?: unknown;
  selectedPrimaryPluginConnectionId?: string;
  selectedResultActions?: unknown;
  selectedSkillIds?: unknown;
  skillById: Map<string, AiSkillRecord>;
  testingConnectionId?: string;
  testSelectedConnection: () => void | Promise<void>;
};

function stringsFromMaybeArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : [];
}

function compactDetails(details: Array<string | undefined>) {
  return details.filter((detail): detail is string => Boolean(detail));
}

export function buildScheduledJobOrchestrationNodes({
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
}: ScheduledJobOrchestrationNodeBuilderInput): ScheduledJobOrchestrationNode[] {
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
  const normalizedSkillIds = stringsFromMaybeArray(selectedSkillIds);
  const normalizedKnowledgeDocumentIds = stringsFromMaybeArray(selectedKnowledgeDocumentIds);
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
  const actionDetails = compactDetails([
    ...selectedActions.map((action, index) => `${index + 1}. ${action.name}`),
    normalizedResultActions.length ? formatResultActionLabels(normalizedResultActions) : undefined,
  ]);

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
      details: compactDetails([
        ...connectionDetails,
        selectedConnections.length > 1 ? `共 ${selectedConnections.length} 个数据连接` : undefined,
        connectionTestResult ? `连接测试 ${connectionTestResult.status}` : undefined,
        connectionTestResult ? `${connectionTestResult.latency_ms}ms` : undefined,
        requestUrl,
      ]),
      key: 'data_connection',
      required: connectionRequired,
      status: dataStatus,
      statusColor: dataStatus === '已配置' || dataStatus === '本地扫描'
        ? 'green'
        : connectionRequired
          ? 'orange'
          : 'default',
      title: '数据连接',
    },
    {
      details: compactDetails([
        selectedModel?.name,
        selectedAgent?.name,
        skillLabels.length ? skillLabels.join('、') : undefined,
      ]),
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
}
