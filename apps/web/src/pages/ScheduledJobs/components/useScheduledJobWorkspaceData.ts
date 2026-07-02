import { message } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  fetchActiveProductOptions,
  fetchAiAgents,
  fetchAiExecutorRunners,
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
  type AiExecutorRunnerRecord,
  type AiSkillRecord,
  type PluginActionRecord,
  type PluginConnectionRecord,
  type ProductFilterOption,
  type ScheduledJobCatalogRecord,
  type ScheduledJobListQuery,
  type ScheduledJobRecord,
  type ScheduledJobRunObservability,
  type ScheduledJobRunListQuery,
  type ScheduledJobRunRecord,
  type ScheduledJobTemplateRecord,
} from '../../../services/aiBrain';
import type { KnowledgeRecord, ModelGatewayConfigRecord } from '../../../data/management';

export type ScheduledJobRemoteTableMeta = {
  page: number;
  pageSize: number;
  total: number;
};

const defaultJobListQuery: ScheduledJobListQuery = {
  page: 1,
  pageSize: 10,
  sortField: 'next_run_at',
  sortOrder: 'descend',
};

const defaultRunListQuery: ScheduledJobRunListQuery = {
  page: 1,
  pageSize: 10,
  sortField: 'started_at',
  sortOrder: 'descend',
};

export function useScheduledJobWorkspaceData() {
  const [jobs, setJobs] = useState<ScheduledJobRecord[]>([]);
  const [runs, setRuns] = useState<ScheduledJobRunRecord[]>([]);
  const [jobListQuery, setJobListQuery] = useState<ScheduledJobListQuery>(defaultJobListQuery);
  const [runListQuery, setRunListQuery] = useState<ScheduledJobRunListQuery>(defaultRunListQuery);
  const [jobListMeta, setJobListMeta] = useState<ScheduledJobRemoteTableMeta>({
    page: defaultJobListQuery.page ?? 1,
    pageSize: defaultJobListQuery.pageSize ?? 10,
    total: 0,
  });
  const [runListMeta, setRunListMeta] = useState<ScheduledJobRemoteTableMeta>({
    page: defaultRunListQuery.page,
    pageSize: defaultRunListQuery.pageSize ?? 10,
    total: 0,
  });
  const [runObservability, setRunObservability] = useState<ScheduledJobRunObservability | undefined>();
  const [jobTemplates, setJobTemplates] = useState<ScheduledJobTemplateRecord[]>([]);
  const [pluginActions, setPluginActions] = useState<PluginActionRecord[]>([]);
  const [pluginConnections, setPluginConnections] = useState<PluginConnectionRecord[]>([]);
  const [products, setProducts] = useState<ProductFilterOption[]>([]);
  const [agents, setAgents] = useState<AiAgentRecord[]>([]);
  const [aiExecutorRunners, setAiExecutorRunners] = useState<AiExecutorRunnerRecord[]>([]);
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
        nextAiExecutorRunners,
        nextSkills,
        nextKnowledgeDocuments,
        nextModelGatewayConfigs,
      ] =
        await Promise.all([
          fetchScheduledJobs(jobListQuery),
          fetchScheduledJobRuns(runListQuery),
          fetchScheduledJobRunObservability(),
          fetchScheduledJobTemplates(),
          fetchScheduledJobCatalog().catch(() => undefined),
          fetchPluginActions(),
          fetchPluginConnections(),
          fetchActiveProductOptions(),
          fetchAiAgents(),
          fetchAiExecutorRunners({ status: 'active' }),
          fetchAiSkills(),
          fetchManagementKnowledge(),
          fetchModelGatewayConfigs(),
        ]);
      setJobs(nextJobs.rows);
      setRuns(nextRuns.rows);
      setJobListMeta({
        page: nextJobs.page,
        pageSize: nextJobs.pageSize,
        total: nextJobs.total,
      });
      setRunListMeta({
        page: nextRuns.page,
        pageSize: nextRuns.pageSize,
        total: nextRuns.total,
      });
      setRunObservability(nextRunObservability);
      setJobTemplates(nextJobTemplates);
      if (nextJobCatalog) {
        setJobCatalog(nextJobCatalog);
      }
      setPluginActions(nextPluginActions);
      setPluginConnections(nextPluginConnections);
      setProducts(nextProducts);
      setAgents(nextAgents.filter((agent) => agent.status === 'active'));
      setAiExecutorRunners(nextAiExecutorRunners);
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
  }, [jobListQuery, runListQuery]);

  const handleJobListChange = useCallback((query: ScheduledJobListQuery) => {
    setJobListQuery((current) => ({
      ...current,
      ...query,
      page: query.page ?? current.page ?? 1,
      pageSize: query.pageSize ?? current.pageSize ?? 10,
    }));
  }, []);

  const handleRunListChange = useCallback((query: ScheduledJobRunListQuery) => {
    setRunListQuery((current) => ({
      ...current,
      ...query,
      page: query.page ?? current.page,
      pageSize: query.pageSize ?? current.pageSize ?? 10,
    }));
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      void reload();
    });
  }, [reload]);

  return {
    agents,
    aiExecutorRunners,
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
    onJobListChange: handleJobListChange,
    onRunListChange: handleRunListChange,
    skills,
  };
}
