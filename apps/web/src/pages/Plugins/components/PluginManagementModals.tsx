import type { FormInstance } from 'antd';

import type {
  AiExecutorRunnerRecord,
  AiExecutorTaskLogRecord,
  AiExecutorTaskRecord,
  PluginActionRecord,
  PluginActionTrialResult,
  PluginConnectionSchemaRecord,
  ResultWriteTargetRecord,
} from '../../../services/aiBrain';
import {
  PluginActionModal,
  type PluginActionFormValues,
} from './PluginActionModal';
import {
  PluginConnectionModal,
  type PluginConnectionFormValues,
} from './PluginConnectionModal';
import { PluginModal, type PluginFormValues } from './PluginModal';
import { PluginRunnerModal } from './PluginRunnerModal';
import type { AiExecutorRunnerFormValues } from './pluginRunnerHelpers';
import {
  PluginActionTrialModal,
  RunnerLogModal,
  RunnerTokenRotationModal,
  RunnerTokenRotationNotice,
} from './PluginUtilityModals';

type SelectOption = {
  label: string;
  value: string;
};

type SystemVariableOption = SelectOption & {
  description?: string;
};

type PluginManagementModalsProps = {
  actionForm: FormInstance<PluginActionFormValues>;
  actionModalOpen: boolean;
  actionScenario?: string;
  actionTemplateOptions: SelectOption[];
  advancedActionJsonOpen: boolean;
  advancedConnectionJsonOpen: boolean;
  advancedConnectionRequestJsonOpen: boolean;
  connectionForm: FormInstance<PluginConnectionFormValues>;
  connectionModalOpen: boolean;
  connectionOptions: SelectOption[];
  connectionSubmitAction?: 'save' | 'save-test';
  defaultWriteTarget: string;
  editingAction?: PluginActionRecord;
  editingConnection: boolean;
  editingPlugin: boolean;
  editingRunner: boolean;
  maxComputeScenario: string;
  pluginCode?: string;
  pluginForm: FormInstance<PluginFormValues>;
  pluginModalOpen: boolean;
  pluginOptions: SelectOption[];
  requestPreview: Record<string, unknown>;
  resultWriteTargetOptions: SelectOption[];
  resultWriteTargets: ResultWriteTargetRecord[];
  rotatedRunnerToken?: string;
  rotatingRunner?: AiExecutorRunnerRecord;
  rotatingRunnerLoading: boolean;
  runnerForm: FormInstance<AiExecutorRunnerFormValues>;
  runnerLogLoading: boolean;
  runnerLogModalOpen: boolean;
  runnerLogRows: AiExecutorTaskLogRecord[];
  runnerLogTask?: AiExecutorTaskRecord;
  runnerModalOpen: boolean;
  selectedConnectionAuthType?: string;
  selectedConnectionIsGithub: boolean;
  selectedConnectionSchema?: PluginConnectionSchemaRecord;
  systemVariableOptions: SystemVariableOption[];
  trialAction?: PluginActionRecord;
  trialConnectionId?: string;
  trialInputJson: string;
  trialModalOpen: boolean;
  trialResult?: PluginActionTrialResult;
  trialRunning: boolean;
  onActionValuesChange: (
    changedValues: Partial<PluginActionFormValues>,
    allValues: PluginActionFormValues,
  ) => void;
  onApplyActionJsonToVisual: () => void;
  onApplyActionScenario: (scenario?: string) => void;
  onApplyConnectionAuthJsonToVisual: () => void;
  onApplyConnectionPluginDefaults: (pluginId: string) => void;
  onApplyConnectionRequestJsonToVisual: () => void;
  onCancelRunnerTask: () => void;
  onCloseActionModal: () => void;
  onCloseConnectionModal: () => void;
  onClosePluginModal: () => void;
  onCloseRotatedRunnerToken: () => void;
  onCloseRunnerLogModal: () => void;
  onCloseRunnerModal: () => void;
  onConnectionValuesChange: (
    changedValues: Partial<PluginConnectionFormValues>,
    allValues: PluginConnectionFormValues,
  ) => void;
  onRotateRunnerTokenCancel: () => void;
  onRotateRunnerTokenSubmit: () => void | Promise<void>;
  onRunActionTrial: () => void | Promise<void>;
  onRetryRunnerTask: () => void;
  onSubmitAction: () => void | Promise<void>;
  onSubmitConnection: () => void | Promise<void>;
  onSubmitConnectionAndTest: () => void | Promise<void>;
  onSubmitPlugin: () => void | Promise<void>;
  onSubmitRunner: () => void | Promise<void>;
  onSyncActionJsonFromVisual: () => void;
  onSyncConnectionAuthJsonFromVisual: () => void;
  onSyncConnectionRequestJsonFromVisual: () => void;
  onToggleActionAdvancedJson: () => void;
  onToggleConnectionAdvancedAuthJson: () => void;
  onToggleConnectionAdvancedRequestJson: () => void;
  onTrialConnectionChange: (connectionId?: string) => void;
  onTrialInputJsonChange: (inputJson: string) => void;
  onTrialModalClose: () => void;
  onWriteTargetChange: (writeTarget?: string) => void;
};

export function PluginManagementModals({
  actionForm,
  actionModalOpen,
  actionScenario,
  actionTemplateOptions,
  advancedActionJsonOpen,
  advancedConnectionJsonOpen,
  advancedConnectionRequestJsonOpen,
  connectionForm,
  connectionModalOpen,
  connectionOptions,
  connectionSubmitAction,
  defaultWriteTarget,
  editingAction,
  editingConnection,
  editingPlugin,
  editingRunner,
  maxComputeScenario,
  pluginCode,
  pluginForm,
  pluginModalOpen,
  pluginOptions,
  requestPreview,
  resultWriteTargetOptions,
  resultWriteTargets,
  rotatedRunnerToken,
  rotatingRunner,
  rotatingRunnerLoading,
  runnerForm,
  runnerLogLoading,
  runnerLogModalOpen,
  runnerLogRows,
  runnerLogTask,
  runnerModalOpen,
  selectedConnectionAuthType,
  selectedConnectionIsGithub,
  selectedConnectionSchema,
  systemVariableOptions,
  trialAction,
  trialConnectionId,
  trialInputJson,
  trialModalOpen,
  trialResult,
  trialRunning,
  onActionValuesChange,
  onApplyActionJsonToVisual,
  onApplyActionScenario,
  onApplyConnectionAuthJsonToVisual,
  onApplyConnectionPluginDefaults,
  onApplyConnectionRequestJsonToVisual,
  onCancelRunnerTask,
  onCloseActionModal,
  onCloseConnectionModal,
  onClosePluginModal,
  onCloseRotatedRunnerToken,
  onCloseRunnerLogModal,
  onCloseRunnerModal,
  onConnectionValuesChange,
  onRotateRunnerTokenCancel,
  onRotateRunnerTokenSubmit,
  onRunActionTrial,
  onRetryRunnerTask,
  onSubmitAction,
  onSubmitConnection,
  onSubmitConnectionAndTest,
  onSubmitPlugin,
  onSubmitRunner,
  onSyncActionJsonFromVisual,
  onSyncConnectionAuthJsonFromVisual,
  onSyncConnectionRequestJsonFromVisual,
  onToggleActionAdvancedJson,
  onToggleConnectionAdvancedAuthJson,
  onToggleConnectionAdvancedRequestJson,
  onTrialConnectionChange,
  onTrialInputJsonChange,
  onTrialModalClose,
  onWriteTargetChange,
}: PluginManagementModalsProps) {
  return (
    <>
      <RunnerTokenRotationNotice
        onClose={onCloseRotatedRunnerToken}
        token={rotatedRunnerToken}
      />

      <RunnerTokenRotationModal
        loading={rotatingRunnerLoading}
        onCancel={onRotateRunnerTokenCancel}
        onSubmit={onRotateRunnerTokenSubmit}
        runner={rotatingRunner}
      />

      <RunnerLogModal
        loading={runnerLogLoading}
        onCancelTask={onCancelRunnerTask}
        onClose={onCloseRunnerLogModal}
        onRetryTask={onRetryRunnerTask}
        open={runnerLogModalOpen}
        rows={runnerLogRows}
        task={runnerLogTask}
      />

      <PluginModal
        form={pluginForm}
        isEditing={editingPlugin}
        onCancel={onClosePluginModal}
        onSubmit={onSubmitPlugin}
        open={pluginModalOpen}
      />

      <PluginRunnerModal
        form={runnerForm}
        isEditing={editingRunner}
        onCancel={onCloseRunnerModal}
        onSubmit={onSubmitRunner}
        open={runnerModalOpen}
      />

      <PluginConnectionModal
        advancedAuthJsonOpen={advancedConnectionJsonOpen}
        advancedRequestJsonOpen={advancedConnectionRequestJsonOpen}
        authType={selectedConnectionAuthType}
        connectionSubmitAction={connectionSubmitAction}
        form={connectionForm}
        isEditing={editingConnection}
        isGithubConnection={selectedConnectionIsGithub}
        onApplyAuthJsonToVisual={onApplyConnectionAuthJsonToVisual}
        onApplyRequestJsonToVisual={onApplyConnectionRequestJsonToVisual}
        onCancel={onCloseConnectionModal}
        onPluginChange={onApplyConnectionPluginDefaults}
        onSubmit={onSubmitConnection}
        onSubmitAndTest={onSubmitConnectionAndTest}
        onSyncAuthJsonFromVisual={onSyncConnectionAuthJsonFromVisual}
        onSyncRequestJsonFromVisual={onSyncConnectionRequestJsonFromVisual}
        onToggleAdvancedAuthJson={onToggleConnectionAdvancedAuthJson}
        onToggleAdvancedRequestJson={onToggleConnectionAdvancedRequestJson}
        onValuesChange={onConnectionValuesChange}
        open={connectionModalOpen}
        pluginCode={pluginCode}
        pluginOptions={pluginOptions}
        schema={selectedConnectionSchema}
        systemVariableOptions={systemVariableOptions}
      />

      <PluginActionModal
        actionScenario={actionScenario}
        advancedJsonOpen={advancedActionJsonOpen}
        connectionOptions={connectionOptions}
        defaultWriteTarget={defaultWriteTarget}
        form={actionForm}
        isEditing={Boolean(editingAction)}
        maxComputeScenario={maxComputeScenario}
        onApplyJsonToVisual={onApplyActionJsonToVisual}
        onCancel={onCloseActionModal}
        onScenarioChange={onApplyActionScenario}
        onSubmit={onSubmitAction}
        onSyncJsonFromVisual={onSyncActionJsonFromVisual}
        onToggleAdvancedJson={onToggleActionAdvancedJson}
        onValuesChange={onActionValuesChange}
        onWriteTargetChange={onWriteTargetChange}
        open={actionModalOpen}
        requestPreview={requestPreview}
        resultWriteTargetOptions={resultWriteTargetOptions}
        resultWriteTargets={resultWriteTargets}
        scenarioOptions={actionTemplateOptions}
        systemVariableOptions={systemVariableOptions}
      />

      <PluginActionTrialModal
        action={trialAction}
        connectionId={trialConnectionId}
        connectionOptions={connectionOptions}
        inputJson={trialInputJson}
        onClose={onTrialModalClose}
        onConnectionChange={onTrialConnectionChange}
        onInputJsonChange={onTrialInputJsonChange}
        onRun={onRunActionTrial}
        open={trialModalOpen}
        result={trialResult}
        running={trialRunning}
      />
    </>
  );
}
