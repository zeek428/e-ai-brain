import { message } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  fetchActiveProductOptions,
  fetchAiAgents,
  fetchAiSkills,
  fetchManagementKnowledge,
  fetchModelGatewayConfigs,
  fetchPluginActions,
  fetchPluginConnections,
  fetchScheduledJobCatalog,
  fetchScheduledJobRunObservability,
  fetchScheduledJobRuns,
  fetchScheduledJobTemplates,
  fetchScheduledJobs,
  type AiAgentRecord,
  type AiSkillRecord,
  type PluginActionRecord,
  type PluginConnectionRecord,
  type ProductFilterOption,
  type ScheduledJobCatalogRecord,
  type ScheduledJobRecord,
  type ScheduledJobRunObservability,
  type ScheduledJobRunRecord,
  type ScheduledJobTemplateRecord,
} from '../../../services/aiBrain';
import type { KnowledgeRecord, ModelGatewayConfigRecord } from '../../../data/management';

export function useScheduledJobWorkspaceData() {
  const [jobs, setJobs] = useState<ScheduledJobRecord[]>([]);
  const [runs, setRuns] = useState<ScheduledJobRunRecord[]>([]);
  const [runObservability, setRunObservability] = useState<ScheduledJobRunObservability | undefined>();
  const [jobTemplates, setJobTemplates] = useState<ScheduledJobTemplateRecord[]>([]);
  const [pluginActions, setPluginActions] = useState<PluginActionRecord[]>([]);
  const [pluginConnections, setPluginConnections] = useState<PluginConnectionRecord[]>([]);
  const [products, setProducts] = useState<ProductFilterOption[]>([]);
  const [agents, setAgents] = useState<AiAgentRecord[]>([]);
  const [skills, setSkills] = useState<AiSkillRecord[]>([]);
  const [knowledgeDocuments, setKnowledgeDocuments] = useState<KnowledgeRecord[]>([]);
  const [modelGatewayConfigs, setModelGatewayConfigs] = useState<ModelGatewayConfigRecord[]>([]);
  const [jobCatalog, setJobCatalog] = useState<ScheduledJobCatalogRecord | undefined>();
  const [loading, setLoading] = useState(false);

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

  return {
    agents,
    jobCatalog,
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
    runs,
    skills,
  };
}
