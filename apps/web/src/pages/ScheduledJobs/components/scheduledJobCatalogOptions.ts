import type { FormItemProps } from 'antd';
import { useCallback, useMemo } from 'react';

import type {
  ScheduledJobCatalogRecord,
  ScheduledJobResultAction,
} from '../../../services/aiBrain';
import {
  aiProcessingRequiredJobTypes,
  cloneResultActions,
  codeInspectionBuiltinRuleOptions,
  codeInspectionIgnoreRuleOptions,
  codeInspectionResultActionOptions,
  codeInspectionScanModeOptions,
  codeInspectionScannerEngineOptions,
  codeInspectionUsesNativeScan,
  connectionEnvironmentOptions,
  defaultCodeInspectionResultActions,
  executionModeOptions,
  hasRequiredFormValue,
  jobTypeOptions,
  pluginRequiredJobTypes,
  productRequiredJobTypes,
  requiresAiAssembly,
  resultActionLabelByValue,
  scheduleTypeOptions,
  severityThresholdOptions,
} from './scheduledJobFormTransformHelpers';

type FormRule = NonNullable<FormItemProps['rules']>[number];

function requiredForJobTypes(jobTypes: string[], message: string): FormRule {
  return ({ getFieldValue }: { getFieldValue: (field: string) => unknown }) => ({
    validator(_: unknown, value: unknown) {
      if (jobTypes.includes(String(getFieldValue('job_type') ?? '')) && !hasRequiredFormValue(value)) {
        return Promise.reject(new Error(message));
      }
      return Promise.resolve();
    },
  });
}

function requiredForPluginResource(jobTypes: string[], message: string): FormRule {
  return ({ getFieldValue }: { getFieldValue: (field: string) => unknown }) => ({
    validator(_: unknown, value: unknown) {
      const jobType = String(getFieldValue('job_type') ?? '');
      if (
        jobTypes.includes(jobType)
        && !codeInspectionUsesNativeScan(jobType, getFieldValue('config_json'))
        && !hasRequiredFormValue(value)
      ) {
        return Promise.reject(new Error(message));
      }
      return Promise.resolve();
    },
  });
}

function requiredForAiAssembly(aiRequiredJobTypes: string[], message: string): FormRule {
  return ({ getFieldValue }: { getFieldValue: (field: string) => unknown }) => ({
    validator(_: unknown, value: unknown) {
      if (
        requiresAiAssembly(getFieldValue('job_type'), getFieldValue('execution_mode'), aiRequiredJobTypes)
        && !hasRequiredFormValue(value)
      ) {
        return Promise.reject(new Error(message));
      }
      return Promise.resolve();
    },
  });
}

export function useScheduledJobCatalogOptions(jobCatalog: ScheduledJobCatalogRecord | undefined) {
  const jobTypeSelectOptions = useMemo(
    () => (jobCatalog?.job_types?.length
      ? jobCatalog.job_types.map((option) => ({ label: option.label, value: option.value }))
      : jobTypeOptions),
    [jobCatalog],
  );
  const jobTypeLabelMap = useMemo(
    () => new Map(jobTypeSelectOptions.map((option) => [option.value, option.label])),
    [jobTypeSelectOptions],
  );
  const executionModeSelectOptions = useMemo(
    () => (jobCatalog?.execution_modes?.length ? jobCatalog.execution_modes : executionModeOptions),
    [jobCatalog],
  );
  const executionModeLabelMap = useMemo(
    () => new Map(executionModeSelectOptions.map((option) => [option.value, option.label])),
    [executionModeSelectOptions],
  );
  const scheduleTypeSelectOptions = useMemo(
    () => (jobCatalog?.schedule_types?.length ? jobCatalog.schedule_types : scheduleTypeOptions),
    [jobCatalog],
  );
  const scheduleTypeLabelMap = useMemo(
    () => new Map(scheduleTypeSelectOptions.map((option) => [option.value, option.label])),
    [scheduleTypeSelectOptions],
  );
  const connectionEnvironmentSelectOptions = useMemo(
    () => (jobCatalog?.connection_environments?.length
      ? jobCatalog.connection_environments
      : connectionEnvironmentOptions),
    [jobCatalog],
  );
  const productRequiredTypes = useMemo(
    () => (jobCatalog?.required_job_types?.product?.length
      ? jobCatalog.required_job_types.product
      : productRequiredJobTypes),
    [jobCatalog],
  );
  const pluginRequiredTypes = useMemo(
    () => (jobCatalog?.required_job_types?.plugin_resource?.length
      ? jobCatalog.required_job_types.plugin_resource
      : pluginRequiredJobTypes),
    [jobCatalog],
  );
  const aiProcessingRequiredTypes = useMemo(
    () => (jobCatalog?.required_job_types?.ai_processing?.length
      ? jobCatalog.required_job_types.ai_processing
      : aiProcessingRequiredJobTypes),
    [jobCatalog],
  );
  const codeInspectionScanModeSelectOptions = useMemo(
    () => (jobCatalog?.code_inspection?.scan_modes?.length
      ? jobCatalog.code_inspection.scan_modes
      : codeInspectionScanModeOptions),
    [jobCatalog],
  );
  const codeInspectionScannerEngineSelectOptions = useMemo(
    () => (jobCatalog?.code_inspection?.scanner_engines?.length
      ? jobCatalog.code_inspection.scanner_engines
      : codeInspectionScannerEngineOptions),
    [jobCatalog],
  );
  const codeInspectionBuiltinRuleSelectOptions = useMemo(
    () => (jobCatalog?.code_inspection?.builtin_rules?.length
      ? jobCatalog.code_inspection.builtin_rules
      : codeInspectionBuiltinRuleOptions),
    [jobCatalog],
  );
  const codeInspectionIgnoreRuleSelectOptions = useMemo(
    () => (jobCatalog?.code_inspection?.ignore_rules?.length
      ? jobCatalog.code_inspection.ignore_rules
      : codeInspectionIgnoreRuleOptions),
    [jobCatalog],
  );
  const codeInspectionResultActionSelectOptions = useMemo(
    () => (jobCatalog?.code_inspection?.result_actions?.length
      ? jobCatalog.code_inspection.result_actions
      : codeInspectionResultActionOptions),
    [jobCatalog],
  );
  const severityThresholdSelectOptions = useMemo(
    () => (jobCatalog?.code_inspection?.severity_thresholds?.length
      ? jobCatalog.code_inspection.severity_thresholds
      : severityThresholdOptions),
    [jobCatalog],
  );
  const defaultCodeInspectionActions = useMemo(
    () => (jobCatalog?.code_inspection?.default_result_actions?.length
      ? cloneResultActions(jobCatalog.code_inspection.default_result_actions)
      : cloneResultActions(defaultCodeInspectionResultActions)),
    [jobCatalog],
  );
  const codeInspectionResultActionLabelMap = useMemo(
    () => new Map(codeInspectionResultActionSelectOptions.map((option) => [option.value, option.label])),
    [codeInspectionResultActionSelectOptions],
  );
  const productRequiredRuleFactory = useCallback(
    (message: string) => requiredForJobTypes(productRequiredTypes, message),
    [productRequiredTypes],
  );
  const pluginResourceRuleFactory = useCallback(
    (message: string) => requiredForPluginResource(pluginRequiredTypes, message),
    [pluginRequiredTypes],
  );
  const aiAssemblyRuleFactory = useCallback(
    (message: string) => requiredForAiAssembly(aiProcessingRequiredTypes, message),
    [aiProcessingRequiredTypes],
  );
  const formatResultActionLabels = useCallback(
    (actions?: ScheduledJobResultAction[]) => {
      const labels = (actions ?? []).map(
        (action) =>
          codeInspectionResultActionLabelMap.get(action.type)
          ?? resultActionLabelByValue.get(action.type)
          ?? action.type,
      );
      return labels.join('、');
    },
    [codeInspectionResultActionLabelMap],
  );

  return {
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
    connectionEnvironmentSelectOptions,
    severityThresholdSelectOptions,
  };
}
