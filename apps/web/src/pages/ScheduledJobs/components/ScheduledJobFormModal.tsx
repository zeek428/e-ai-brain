import { Button, Form, Input, Modal, Select, Space, Typography } from 'antd';
import type { FormInstance, FormItemProps } from 'antd';

import type { KnowledgeRecord, ModelGatewayConfigRecord } from '../../../data/management';
import type {
  AiAgentRecord,
  AiSkillRecord,
  PluginActionRecord,
  PluginConnectionRecord,
  ProductGitRepositoryOption,
  ScheduledJobDryRunResult,
  ScheduledJobRecord,
  ScheduledJobTemplateRecord,
} from '../../../services/aiBrain';
import { ScheduledJobActionConfigSection } from './ScheduledJobActionConfigSection';
import { ScheduledJobAiExecutionSection } from './ScheduledJobAiExecutionSection';
import { ScheduledJobBasicInfoSection } from './ScheduledJobBasicInfoSection';
import { ScheduledJobCodeRepositorySection } from './ScheduledJobCodeRepositorySection';
import { ScheduledJobDataConnectionSection } from './ScheduledJobDataConnectionSection';
import { ScheduledJobDryRunResultPanel } from './ScheduledJobDryRunResultPanel';
import {
  ScheduledJobOrchestrationFlow,
  type ScheduledJobOrchestrationNode,
} from './ScheduledJobOrchestrationFlow';
import { TemplateSourceSummary } from './ScheduledJobRunTraceDetails';
import { ScheduledJobScheduleConfigSection } from './ScheduledJobScheduleConfigSection';
import type {
  ScheduledJobFormValues,
  ScheduledJobTemplateSource,
} from './scheduledJobFormTransformHelpers';

type FormRule = NonNullable<FormItemProps['rules']>[number];

type SelectOption = {
  label: string;
  value: string;
};

type ScheduledJobFormModalProps = {
  agents: AiAgentRecord[];
  aiAssemblyRuleFactory: (message: string) => FormRule;
  codeInspectionBuiltinRuleSelectOptions: SelectOption[];
  codeInspectionIgnoreRuleSelectOptions: SelectOption[];
  codeInspectionResultActionOptions: SelectOption[];
  codeInspectionScanModeSelectOptions: SelectOption[];
  codeInspectionScannerEngineSelectOptions: SelectOption[];
  connectionEnvironmentSelectOptions: SelectOption[];
  dryRunResult?: ScheduledJobDryRunResult;
  dryRunning: boolean;
  editingJob?: ScheduledJobRecord;
  executionModeSelectOptions: SelectOption[];
  filteredPluginConnections: PluginConnectionRecord[];
  form: FormInstance<ScheduledJobFormValues>;
  jobTemplateOptions: SelectOption[];
  jobTypeSelectOptions: SelectOption[];
  knowledgeDocuments: KnowledgeRecord[];
  loadingRepositories: boolean;
  modalOpen: boolean;
  modelGatewayConfigs: ModelGatewayConfigRecord[];
  orchestrationNodes: ScheduledJobOrchestrationNode[];
  pluginActions: PluginActionRecord[];
  productOptions: SelectOption[];
  productRepositories: ProductGitRepositoryOption[];
  productRequiredRule: FormRule;
  requiredForPluginResource: (message: string) => FormRule;
  scheduleTypeSelectOptions: SelectOption[];
  selectedJobTemplate?: ScheduledJobTemplateRecord;
  selectedJobType?: string;
  selectedRepositoryDefaultBranch?: string;
  severityThresholdSelectOptions: SelectOption[];
  skills: AiSkillRecord[];
  templateSource?: ScheduledJobTemplateSource;
  usesNativeScan: boolean;
  writeStrategyLabelFromAction: (action: PluginActionRecord) => string;
  onApplyJobTemplate: (templateCode?: string) => void;
  onClose: () => void;
  onConnectionEnvironmentChange: (environment?: string) => void;
  onDryRun: () => void | Promise<void>;
  onJobTypeChange: (jobType?: string) => void;
  onPluginConnectionChange: (connectionIds: unknown) => void;
  onProductChange: () => void;
  onRepositoryChange: (repositoryId?: string) => void;
  onScanModeChange: (scanMode?: string) => void;
  onSubmit: () => void | Promise<void>;
};

export function ScheduledJobFormModal({
  agents,
  aiAssemblyRuleFactory,
  codeInspectionBuiltinRuleSelectOptions,
  codeInspectionIgnoreRuleSelectOptions,
  codeInspectionResultActionOptions,
  codeInspectionScanModeSelectOptions,
  codeInspectionScannerEngineSelectOptions,
  connectionEnvironmentSelectOptions,
  dryRunResult,
  dryRunning,
  editingJob,
  executionModeSelectOptions,
  filteredPluginConnections,
  form,
  jobTemplateOptions,
  jobTypeSelectOptions,
  knowledgeDocuments,
  loadingRepositories,
  modalOpen,
  modelGatewayConfigs,
  orchestrationNodes,
  pluginActions,
  productOptions,
  productRepositories,
  productRequiredRule,
  requiredForPluginResource,
  scheduleTypeSelectOptions,
  selectedJobTemplate,
  selectedJobType,
  selectedRepositoryDefaultBranch,
  severityThresholdSelectOptions,
  skills,
  templateSource,
  usesNativeScan,
  writeStrategyLabelFromAction,
  onApplyJobTemplate,
  onClose,
  onConnectionEnvironmentChange,
  onDryRun,
  onJobTypeChange,
  onPluginConnectionChange,
  onProductChange,
  onRepositoryChange,
  onScanModeChange,
  onSubmit,
}: ScheduledJobFormModalProps) {
  return (
    <Modal
      aria-label={editingJob ? '编辑定时作业' : '新增定时作业'}
      destroyOnHidden
      footer={(
        <Space>
          <Button htmlType="button" onClick={onClose}>取消</Button>
          <Button
            htmlType="button"
            loading={dryRunning}
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              void onDryRun();
            }}
          >
            全链路试运行
          </Button>
          <Button htmlType="button" type="primary" onClick={() => void onSubmit()}>
            确定
          </Button>
        </Space>
      )}
      open={modalOpen}
      title={editingJob ? '编辑定时作业' : '新增定时作业'}
      width={820}
      onCancel={onClose}
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
              onChange={onApplyJobTemplate}
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
          onJobTypeChange={onJobTypeChange}
          onProductChange={onProductChange}
          productOptions={productOptions}
          productRequiredRule={productRequiredRule}
        />
        <ScheduledJobDataConnectionSection
          connectionEnvironmentOptions={connectionEnvironmentSelectOptions}
          filteredPluginConnections={filteredPluginConnections}
          onConnectionEnvironmentChange={onConnectionEnvironmentChange}
          onPluginConnectionChange={onPluginConnectionChange}
          requiredForPluginResource={requiredForPluginResource}
          usesNativeScan={usesNativeScan}
        />
        {selectedJobType === 'code_repository_inspection' ? (
          <ScheduledJobCodeRepositorySection
            builtinRuleOptions={codeInspectionBuiltinRuleSelectOptions}
            ignoreRuleOptions={codeInspectionIgnoreRuleSelectOptions}
            loadingRepositories={loadingRepositories}
            onRepositoryChange={onRepositoryChange}
            onScanModeChange={onScanModeChange}
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
          codeInspectionResultActionOptions={codeInspectionResultActionOptions}
          isCodeInspectionJob={selectedJobType === 'code_repository_inspection'}
          pluginActions={pluginActions}
          requiredForPluginResource={requiredForPluginResource}
          severityThresholdOptions={severityThresholdSelectOptions}
          usesNativeScan={usesNativeScan}
          writeStrategyLabelFromAction={writeStrategyLabelFromAction}
        />
        <ScheduledJobScheduleConfigSection scheduleTypeOptions={scheduleTypeSelectOptions} />
        {dryRunResult ? <ScheduledJobDryRunResultPanel result={dryRunResult} /> : null}
      </Form>
    </Modal>
  );
}
