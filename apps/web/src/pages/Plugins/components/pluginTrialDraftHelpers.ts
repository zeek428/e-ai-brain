import type {
  PluginActionRecord,
  PluginActionTrialResult,
} from '../../../services/aiBrain';
import { isPlainRecord, stringValue } from './pluginFormTransformHelpers';

export function trialSeedCanCreateScheduledJobDraft(trialResult?: PluginActionTrialResult) {
  const seed = trialResult?.scheduled_job_dry_run_seed;
  if (!seed || trialResult?.status !== 'succeeded') {
    return false;
  }
  const reuseWizard = isPlainRecord(seed.reuse_wizard) ? seed.reuse_wizard : undefined;
  if (!reuseWizard) {
    return true;
  }
  if (reuseWizard.can_continue === false || reuseWizard.draft_payload_ready === false) {
    return false;
  }
  return (
    reuseWizard.can_continue === true
    || reuseWizard.draft_payload_ready === true
    || reuseWizard.status === 'ready'
  );
}

export function scheduledJobDraftFromTrial(options: {
  trialAction?: PluginActionRecord;
  trialConnectionId?: string;
  trialResult?: PluginActionTrialResult;
}) {
  const { trialAction, trialConnectionId, trialResult } = options;
  const seed = trialResult?.scheduled_job_dry_run_seed;
  if (!trialAction || !seed || !trialSeedCanCreateScheduledJobDraft(trialResult)) {
    return undefined;
  }
  const seedConnectionId = stringValue(seed.plugin_connection_id, trialConnectionId ?? trialResult?.connection_id);
  const seedActionId = stringValue(seed.plugin_action_id, trialAction.id);
  const inputMapping = isPlainRecord(seed.plugin_input_mapping)
    ? seed.plugin_input_mapping
    : isPlainRecord(seed.input_payload)
      ? seed.input_payload
      : {};
  const outputMapping = isPlainRecord(seed.plugin_output_mapping)
    ? seed.plugin_output_mapping
    : trialAction.result_mapping ?? {};
  const writeTarget = stringValue(outputMapping.write_target);
  const inferredJobType =
    writeTarget === 'user_feedback_insights'
      ? 'user_feedback_insight_extract'
      : writeTarget === 'code_inspection_reports'
        ? 'code_repository_inspection'
        : 'plugin_action_invoke';
  return {
    payload: {
      config_json: {
        sample_reuse: {
          auto_dry_run: true,
          action_id: seedActionId,
          connection_id: seedConnectionId,
          response_summary: seed.response_summary,
          reuse_wizard: seed.reuse_wizard,
          sample_source: seed.sample_source ?? 'action_trial_response',
          write_preview: seed.write_preview,
        },
      },
      enabled: true,
      execution_mode: inferredJobType === 'plugin_action_invoke' ? 'deterministic' : 'ai_generated',
      job_type: inferredJobType,
      name: `${trialAction.name} 定时作业`,
      plugin_action_id: seedActionId,
      plugin_action_ids: seedActionId ? [seedActionId] : [],
      plugin_connection_id: seedConnectionId,
      plugin_connection_ids: seedConnectionId ? [seedConnectionId] : [],
      plugin_input_mapping: inputMapping,
      plugin_output_mapping: outputMapping,
      schedule_type: 'manual',
      source_system: 'plugin-action-trial',
    },
    title: `从动作试运行创建：${trialAction.name}`,
  };
}
