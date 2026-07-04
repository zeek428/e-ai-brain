import type {
  ResultWriteRecord,
  ScheduledJobRunRecord,
} from '../../../services/aiBrain';
import { getRunExecutionNode } from './scheduledJobRunTraceHelpers';

export type ScheduledJobRunDetailExportPayloadOptions = {
  agentLabel: string;
  executionModeLabel: string;
  jobTypeLabel: string;
  modelLabel: string;
  resultWriteRecords: ResultWriteRecord[];
  run?: ScheduledJobRunRecord;
  skillLabels: string;
};

export function buildScheduledJobRunDetailExportPayload({
  agentLabel,
  executionModeLabel,
  jobTypeLabel,
  modelLabel,
  resultWriteRecords,
  run,
  skillLabels,
}: ScheduledJobRunDetailExportPayloadOptions) {
  if (!run) {
    return undefined;
  }
  return {
    export_version: 'scheduled_job_run_detail.v1',
    exported_at: new Date().toISOString(),
    labels: {
      agent: agentLabel,
      execution_mode: executionModeLabel,
      job_type: jobTypeLabel,
      model: modelLabel,
      skills: skillLabels,
    },
    result_write_records: resultWriteRecords,
    run,
    sections: {
      ai_processing: getRunExecutionNode(run, 'skill_processing'),
      bug_creation: getRunExecutionNode(run, 'bug_creation'),
      code_inspection_report: getRunExecutionNode(run, 'code_inspection_report'),
      data_connection: getRunExecutionNode(run, 'data_connection'),
      notifications: getRunExecutionNode(run, 'notifications'),
      result_action: getRunExecutionNode(run, 'result_action'),
      result_actions: getRunExecutionNode(run, 'result_actions'),
      task_creation: getRunExecutionNode(run, 'task_creation'),
    },
    snapshots: {
      agent: run.resolved_agent_snapshot,
      config: run.config_snapshot,
      plugin: run.resolved_plugin_snapshot,
      prompt: run.resolved_prompt_snapshot,
      skills: run.resolved_skill_snapshots,
    },
  };
}
