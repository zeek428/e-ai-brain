import { useCallback, useEffect, useState } from 'react';
import { message } from 'antd';

import {
  fetchScheduledJobRuns,
  fetchResultWriteRecords,
  type AiAgentRecord,
  type AiSkillRecord,
  type ResultWriteRecord,
  type ScheduledJobRunRecord,
} from '../../../services/aiBrain';
import type { ModelGatewayConfigRecord } from '../../../data/management';
import {
  scheduledJobRouteParams,
  snapshotStringListValue,
  snapshotStringValue,
  type ScheduledJobPageTab,
} from './scheduledJobFormTransformHelpers';

export type ScheduledJobRunDetailLabels = {
  agentLabel: string;
  executionModeLabel: string;
  jobTypeLabel: string;
  modelLabel: string;
  skillLabels: string;
};

export function useScheduledJobRunDetailState({
  agentById,
  executionModeLabelMap,
  jobTypeLabelMap,
  modelGatewayConfigById,
  runs,
  skillById,
  onRouteTabChange,
}: {
  agentById: Map<string, AiAgentRecord>;
  executionModeLabelMap: Map<string, string>;
  jobTypeLabelMap: Map<string, string>;
  modelGatewayConfigById: Map<string, ModelGatewayConfigRecord>;
  runs: ScheduledJobRunRecord[];
  skillById: Map<string, AiSkillRecord>;
  onRouteTabChange: (tab: ScheduledJobPageTab) => void;
}) {
  const [selectedRun, setSelectedRun] = useState<ScheduledJobRunRecord | undefined>();
  const [focusedResultWriteRecordId, setFocusedResultWriteRecordId] = useState<string | undefined>();
  const [resultWriteRecords, setResultWriteRecords] = useState<ResultWriteRecord[]>([]);
  const [resultWriteRecordsLoading, setResultWriteRecordsLoading] = useState(false);
  const [runDetailRefreshing, setRunDetailRefreshing] = useState(false);
  const [handledRouteRunKey, setHandledRouteRunKey] = useState<string | undefined>();

  const openRunDetail = (run: ScheduledJobRunRecord, resultWriteRecordId?: string) => {
    setFocusedResultWriteRecordId(resultWriteRecordId);
    setSelectedRun(run);
  };

  const closeRunDetail = () => {
    setSelectedRun(undefined);
    setFocusedResultWriteRecordId(undefined);
  };

  const refreshRunDetail = useCallback(async () => {
    const runId = selectedRun?.id;
    if (!runId) {
      return;
    }
    setRunDetailRefreshing(true);
    try {
      const latestRuns = await fetchScheduledJobRuns({ runIds: [runId] });
      const latestRun = latestRuns.find((item) => item.id === runId);
      if (!latestRun) {
        message.warning('暂未查询到该运行记录的最新数据');
        return;
      }
      setSelectedRun((current) => (current?.id === runId ? latestRun : current));
    } catch (error) {
      message.error(error instanceof Error ? error.message : '运行结果刷新失败');
    } finally {
      setRunDetailRefreshing(false);
    }
  }, [selectedRun?.id]);

  useEffect(() => {
    const routeParams = scheduledJobRouteParams();
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
      onRouteTabChange('runs');
      openRunDetail(routeRun, routeParams.resultWriteRecordId);
      setHandledRouteRunKey(routeRunKey);
    });
  }, [handledRouteRunKey, onRouteTabChange, runs]);

  useEffect(() => {
    if (!selectedRun?.id) {
      queueMicrotask(() => {
        setResultWriteRecords([]);
        setResultWriteRecordsLoading(false);
      });
      return;
    }
    let ignore = false;
    queueMicrotask(() => {
      setResultWriteRecordsLoading(true);
    });
    fetchResultWriteRecords({ scheduledJobRunId: selectedRun.id })
      .then((records) => {
        if (!ignore) {
          setResultWriteRecords(records);
        }
      })
      .catch((error) => {
        if (!ignore) {
          setResultWriteRecords([]);
          message.error(error instanceof Error ? error.message : '结果写入记录加载失败');
        }
      })
      .finally(() => {
        if (!ignore) {
          setResultWriteRecordsLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, [selectedRun]);

  const selectedRunConfigSnapshot = selectedRun?.config_snapshot;
  const selectedRunAgentId = snapshotStringValue(selectedRunConfigSnapshot, 'agent_id');
  const selectedRunModelGatewayConfigId = snapshotStringValue(selectedRunConfigSnapshot, 'model_gateway_config_id');
  const selectedRunSkillIds = snapshotStringListValue(selectedRunConfigSnapshot, 'skill_ids');
  const selectedRunJobType = snapshotStringValue(selectedRunConfigSnapshot, 'job_type');
  const selectedRunExecutionMode = snapshotStringValue(selectedRunConfigSnapshot, 'execution_mode');
  const labels: ScheduledJobRunDetailLabels = {
    agentLabel:
      snapshotStringValue(selectedRun?.resolved_agent_snapshot, 'name')
      ?? (selectedRunAgentId ? agentById.get(selectedRunAgentId)?.name ?? selectedRunAgentId : '-'),
    executionModeLabel: selectedRunExecutionMode
      ? executionModeLabelMap.get(selectedRunExecutionMode) ?? selectedRunExecutionMode
      : '-',
    jobTypeLabel: selectedRunJobType
      ? jobTypeLabelMap.get(selectedRunJobType) ?? selectedRunJobType
      : '-',
    modelLabel: selectedRunModelGatewayConfigId
      ? modelGatewayConfigById.get(selectedRunModelGatewayConfigId)?.name ?? selectedRunModelGatewayConfigId
      : '-',
    skillLabels:
      selectedRun?.resolved_skill_snapshots
        ?.map((skill) => String(skill.name ?? skill.code ?? skill.id ?? ''))
        .filter(Boolean)
        .join('、')
      || selectedRunSkillIds.map((skillId) => skillById.get(skillId)?.name ?? skillId).join('、')
      || '-',
  };

  return {
    closeRunDetail,
    focusedResultWriteRecordId,
    labels,
    openRunDetail,
    refreshRunDetail,
    resultWriteRecords,
    resultWriteRecordsLoading,
    runDetailRefreshing,
    selectedRun,
  };
}
