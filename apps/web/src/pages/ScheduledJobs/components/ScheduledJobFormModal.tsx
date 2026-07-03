import { Alert, Button, Form, Input, Modal, Select, Space, Tag, Typography } from 'antd';
import type { FormInstance, FormItemProps } from 'antd';

import type { KnowledgeRecord, ModelGatewayConfigRecord } from '../../../data/management';
import type {
  AiAgentRecord,
  AiExecutorRunnerRecord,
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
  aiExecutorRunners: AiExecutorRunnerRecord[];
  aiAssemblyRuleFactory: (message: string) => FormRule;
  codeInspectionBuiltinRuleSelectOptions: SelectOption[];
  codeInspectionIgnoreRuleSelectOptions: SelectOption[];
  codeInspectionResultActionOptions: SelectOption[];
  genericResultActionOptions: SelectOption[];
  codeInspectionScanModeSelectOptions: SelectOption[];
  codeInspectionScannerEngineSelectOptions: SelectOption[];
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
  sampleReuseDraft?: Record<string, unknown>;
  selectedJobTemplate?: ScheduledJobTemplateRecord;
  selectedJobType?: string;
  selectedProductId?: string;
  selectedRepositoryDefaultBranch?: string;
  severityThresholdSelectOptions: SelectOption[];
  skills: AiSkillRecord[];
  templateSource?: ScheduledJobTemplateSource;
  usesNativeScan: boolean;
  writeStrategyLabelFromAction: (action: PluginActionRecord) => string;
  onApplyJobTemplate: (templateCode?: string) => void;
  onClose: () => void;
  onDryRun: () => void | Promise<void>;
  onJobTypeChange: (jobType?: string) => void;
  onPluginConnectionChange: (connectionIds: unknown) => void;
  onProductChange: () => void;
  onRepositoryChange: (repositoryId?: string) => void;
  onScanModeChange: (scanMode?: string) => void;
  onSubmit: () => void | Promise<void>;
};

function recordValue(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function stringValue(value: unknown): string | undefined {
  return typeof value === 'string' && value ? value : undefined;
}

function numberValue(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function statusColor(status?: string) {
  if (status === 'ready' || status === 'succeeded') {
    return 'green';
  }
  if (status === 'blocked' || status === 'failed' || status === 'missing') {
    return 'red';
  }
  if (status === 'partial' || status === 'pending') {
    return 'orange';
  }
  return 'default';
}

function sampleSourceLabel(value: unknown): string {
  if (value === 'connection_test_response') {
    return '连接测试响应样例';
  }
  if (value === 'action_trial_response') {
    return '动作试运行响应';
  }
  return stringValue(value) ?? '样例响应';
}

function resourceLabel(
  id: unknown,
  items: Array<{ id: string; name?: string }>,
) {
  const resolvedId = stringValue(id);
  if (!resolvedId) {
    return '-';
  }
  const item = items.find((candidate) => candidate.id === resolvedId);
  return item?.name ? `${item.name} (${resolvedId})` : resolvedId;
}

function ScheduledJobSampleReuseDraftSummary({
  pluginActions,
  pluginConnections,
  sampleReuseDraft,
}: {
  pluginActions: PluginActionRecord[];
  pluginConnections: PluginConnectionRecord[];
  sampleReuseDraft?: Record<string, unknown>;
}) {
  if (!sampleReuseDraft) {
    return null;
  }
  const writePreview = recordValue(sampleReuseDraft.write_preview);
  const writeTarget =
    stringValue(writePreview?.write_target_label)
    ?? stringValue(writePreview?.write_target);
  const writeCount =
    numberValue(writePreview?.records_imported)
    ?? numberValue(writePreview?.candidate_count);
  const reuseWizard = recordValue(sampleReuseDraft.reuse_wizard);
  const autoDryRun = sampleReuseDraft.auto_dry_run === true;
  const currentStepLabel = stringValue(reuseWizard?.current_step_label);
  const primaryActionLabel = stringValue(reuseWizard?.primary_action_label);
  const nextActionDescription = stringValue(reuseWizard?.next_action_description);
  const progressLabel = stringValue(reuseWizard?.progress_label);
  const progressPercent = numberValue(reuseWizard?.progress_percent);
  const handoffSummary = Array.isArray(reuseWizard?.handoff_summary)
    ? reuseWizard.handoff_summary
      .map(recordValue)
      .filter((item): item is Record<string, unknown> => Boolean(item))
    : [];
  return (
    <Alert
      aria-label="动作试运行样例"
      description={(
        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
          <Typography.Text>
            已带入动作试运行生成的连接、动作、输入映射和写入预览。请补充必填配置后继续执行全链路试运行，再保存作业。
          </Typography.Text>
          <Space size={[8, 8]} wrap>
            {autoDryRun ? <Tag color="green">打开后自动试运行</Tag> : null}
            <Tag color="blue">连接 {resourceLabel(sampleReuseDraft.connection_id, pluginConnections)}</Tag>
            <Tag color="purple">动作 {resourceLabel(sampleReuseDraft.action_id, pluginActions)}</Tag>
            <Tag color="geekblue">样例来源 {sampleSourceLabel(sampleReuseDraft.sample_source)}</Tag>
            {writeTarget ? <Tag color="cyan">写入目标 {writeTarget}</Tag> : null}
            {writeCount !== undefined ? <Tag color="green">预计写入 {writeCount}</Tag> : null}
            {progressLabel ? (
              <Tag color={progressPercent === 100 ? 'green' : 'blue'}>
                进度：{progressLabel}
              </Tag>
            ) : null}
          </Space>
          {reuseWizard ? (
            <Space aria-label="样例复用向导" orientation="vertical" size={6} style={{ width: '100%' }}>
              <Space size={[8, 8]} wrap>
                {currentStepLabel ? <Tag color="geekblue">当前：{currentStepLabel}</Tag> : null}
                {primaryActionLabel ? <Tag color="blue">下一步：{primaryActionLabel}</Tag> : null}
              </Space>
              {nextActionDescription ? (
                <Typography.Text type="secondary">{nextActionDescription}</Typography.Text>
              ) : null}
              {handoffSummary.length ? (
                <Space size={[8, 8]} wrap>
                  {handoffSummary.map((item, index) => {
                    const itemStatus = stringValue(item.status);
                    const label = stringValue(item.label) ?? stringValue(item.key) ?? '已带入';
                    return (
                      <Tag
                        color={statusColor(itemStatus)}
                        key={`${stringValue(item.key) ?? index}-${itemStatus ?? 'unknown'}`}
                      >
                        {label} · {itemStatus ?? '-'}
                      </Tag>
                    );
                  })}
                </Space>
              ) : null}
            </Space>
          ) : null}
        </Space>
      )}
      showIcon
      style={{ marginBottom: 16 }}
      title="已载入动作试运行样例"
      type="info"
    />
  );
}

export function ScheduledJobFormModal({
  agents,
  aiExecutorRunners,
  aiAssemblyRuleFactory,
  codeInspectionBuiltinRuleSelectOptions,
  codeInspectionIgnoreRuleSelectOptions,
  codeInspectionResultActionOptions,
  genericResultActionOptions,
  codeInspectionScanModeSelectOptions,
  codeInspectionScannerEngineSelectOptions,
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
  sampleReuseDraft,
  selectedJobTemplate,
  selectedJobType,
  selectedProductId,
  selectedRepositoryDefaultBranch,
  severityThresholdSelectOptions,
  skills,
  templateSource,
  usesNativeScan,
  writeStrategyLabelFromAction,
  onApplyJobTemplate,
  onClose,
  onDryRun,
  onJobTypeChange,
  onPluginConnectionChange,
  onProductChange,
  onRepositoryChange,
  onScanModeChange,
  onSubmit,
}: ScheduledJobFormModalProps) {
  const editingCodeRepositoryConfig = recordValue(editingJob?.config_json);
  const showAdvancedRepositoryConfigInitially = Boolean(
    selectedJobType === 'code_repository_inspection'
    && editingCodeRepositoryConfig
    && [
      'repository_id',
      'repository_ids',
      'branch',
      'scanner_engines',
      'scan_rules',
      'severity_threshold',
      'ignore_dirs',
      'ignore_rules',
      'baseline_fingerprints',
      'accepted_risk_fingerprints',
      'quality_gate',
      'incremental_from_commit',
      'async_execution',
    ].some((key) => editingCodeRepositoryConfig[key] !== undefined),
  );

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
      <ScheduledJobSampleReuseDraftSummary
        pluginActions={pluginActions}
        pluginConnections={filteredPluginConnections}
        sampleReuseDraft={sampleReuseDraft}
      />
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
          filteredPluginConnections={filteredPluginConnections}
          onPluginConnectionChange={onPluginConnectionChange}
          requiredForPluginResource={requiredForPluginResource}
          usesNativeScan={usesNativeScan}
        />
        {selectedJobType === 'code_repository_inspection' ? (
          <ScheduledJobCodeRepositorySection
            advancedInitiallyVisible={showAdvancedRepositoryConfigInitially}
            builtinRuleOptions={codeInspectionBuiltinRuleSelectOptions}
            ignoreRuleOptions={codeInspectionIgnoreRuleSelectOptions}
            loadingRepositories={loadingRepositories}
            onRepositoryChange={onRepositoryChange}
            onScanModeChange={onScanModeChange}
            repositories={productRepositories}
            scanModeOptions={codeInspectionScanModeSelectOptions}
            scannerEngineOptions={codeInspectionScannerEngineSelectOptions}
            selectedProductId={selectedProductId}
            selectedRepositoryDefaultBranch={selectedRepositoryDefaultBranch}
            severityThresholdOptions={severityThresholdSelectOptions}
          />
        ) : null}
        <ScheduledJobAiExecutionSection
          agents={agents}
          aiExecutorRunners={aiExecutorRunners}
          executionModeOptions={executionModeSelectOptions}
          knowledgeDocuments={knowledgeDocuments}
          modelGatewayConfigs={modelGatewayConfigs}
          requiredForAiAssembly={aiAssemblyRuleFactory}
          skills={skills}
        />
        <ScheduledJobActionConfigSection
          codeInspectionResultActionOptions={codeInspectionResultActionOptions}
          genericResultActionOptions={genericResultActionOptions}
          isCodeInspectionJob={selectedJobType === 'code_repository_inspection'}
          isGenericResultActionJob={selectedJobType === 'online_log_ai_analysis'}
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
