import {
  BugOutlined,
  BulbOutlined,
  CopyOutlined,
  DownOutlined,
  DownloadOutlined,
  EditOutlined,
  FileAddOutlined,
  ReloadOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { Button, Descriptions, Dropdown, Modal, Space, Tag, Typography } from 'antd';

import type {
  ResultWriteRecord,
  ScheduledJobRunRecord,
} from '../../../services/aiBrain';
import { ExecutionTraceLink } from '../../../components/ExecutionTraceLink';
import { formatDisplayDateTime } from '../../../utils/dateTime';
import { ScheduledJobJsonPreview as JsonPreview } from './ScheduledJobJsonPreview';
import { ScheduledJobRunResultWriteRecords } from './ScheduledJobRunResultWriteRecords';
import {
  RunExecutionChain,
  RunSourceComparison,
  RunTraceDag,
  TemplateSourceSummary,
} from './ScheduledJobRunTraceDetails';
import {
  getRunExecutionNode,
  isTraceRecord,
  templateSourceFromConfig,
} from './scheduledJobRunTraceHelpers';
import { buildScheduledJobRunDetailExportPayload } from './scheduledJobRunDetailExport';

type ScheduledJobRunDetailModalProps = {
  agentLabel: string;
  executionModeLabel: string;
  focusedResultWriteRecordId?: string;
  jobTypeLabel: string;
  modelLabel: string;
  onClose: () => void;
  onCopyRun: (run: ScheduledJobRunRecord) => void;
  onGenerateTemplate: (run: ScheduledJobRunRecord) => void | Promise<void>;
  onRefresh: () => void | Promise<void>;
  onTraceFullRunRerunRequested?: (request: Record<string, unknown>) => void | Promise<void>;
  onTraceNodeRerunCreated?: (run: ScheduledJobRunRecord) => void;
  refreshing: boolean;
  resultWriteRecords: ResultWriteRecord[];
  resultWriteRecordsLoading: boolean;
  run?: ScheduledJobRunRecord;
  skillLabels: string;
};

const runTriggerTypeLabelByValue = new Map([
  ['manual', '手动触发'],
  ['manual_rerun', '运行记录复跑'],
  ['scheduler', '调度触发'],
]);

function recordValue(value: unknown): Record<string, unknown> | undefined {
  return isTraceRecord(value) ? value : undefined;
}

function scalarText(value: unknown, fallback = '-') {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return fallback;
}

function assistantRunFollowupPrompt(run: ScheduledJobRunRecord) {
  return run.status === 'failed' ? '为什么这次任务失败？' : '帮我分析这次运行结果';
}

function runResultSummaryMessage(run: ScheduledJobRunRecord): string | undefined {
  const message = run.result_summary?.message;
  return typeof message === 'string' && message.trim() ? message : undefined;
}

function stringValue(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined;
}

function arrayOfRecords(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter(isTraceRecord) : [];
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map((item) => String(item)).filter(Boolean)
    : [];
}

const resultActionLabelByType = new Map([
  ['create_requirements', '创建需求'],
  ['save_scheduled_job_result', '保存运行结果'],
  ['send_notification', '发送通知'],
  ['sync_dingtalk_document', '钉钉文档更新'],
]);

const resultActionLabelByWriteTarget = new Map([
  ['dingtalk_document', '钉钉文档更新'],
  ['email_notifications', '邮件通知'],
  ['requirements', '创建需求'],
  ['scheduled_job_result', '保存运行结果'],
  ['user_feedback_insights', '用户洞察写入'],
]);

function resultActionStatusLabel(status: string | undefined) {
  if (status === 'succeeded') {
    return '成功';
  }
  if (status === 'failed') {
    return '失败';
  }
  if (status === 'not_run') {
    return '未执行';
  }
  if (status === 'running') {
    return '执行中';
  }
  return status || '未知';
}

function resultActionStatusColor(status: string | undefined) {
  if (status === 'succeeded') {
    return 'green';
  }
  if (status === 'failed') {
    return 'red';
  }
  if (status === 'not_run') {
    return 'default';
  }
  return 'blue';
}

function resultActionsFromRun(run: ScheduledJobRunRecord): Array<Record<string, unknown>> {
  const actions = arrayOfRecords(getRunExecutionNode(run, 'result_actions'));
  const primaryAction = recordValue(getRunExecutionNode(run, 'result_action'));
  const executedActions = actions.length ? actions : primaryAction ? [primaryAction] : [];
  const configuredActions = arrayOfRecords(recordValue(run.config_snapshot)?.result_actions);
  const executedActionTypes = new Set(
    executedActions
      .map((action) => stringValue(action.action_type) ?? stringValue(action.type))
      .filter((type): type is string => Boolean(type)),
  );
  const unexecutedConfiguredActions = configuredActions
    .filter((action) => {
      const type = stringValue(action.type);
      return type && !executedActionTypes.has(type);
    })
    .map<Record<string, unknown>>((action) => ({
      action_type: action.type,
      feedback: {
        error_message: '本次运行未执行该已配置动作，未生成调用日志。',
        write_mode: action.write_mode,
      },
      records_imported: 0,
      status: 'not_run',
      write_target: action.type === 'sync_dingtalk_document' ? 'dingtalk_document' : undefined,
    }));
  if (executedActions.length || unexecutedConfiguredActions.length) {
    return [...executedActions, ...unexecutedConfiguredActions];
  }
  return [];
}

function ResultActionExecutionSummary({ run }: { run: ScheduledJobRunRecord }) {
  const actions = resultActionsFromRun(run);
  if (!actions.length) {
    return null;
  }
  return (
    <Space aria-label="结果动作执行情况" orientation="vertical" size={8} style={{ width: '100%' }}>
      <Typography.Text strong>结果动作执行情况</Typography.Text>
      <Descriptions
        bordered
        column={1}
        items={actions.map((action, index) => {
          const feedback = recordValue(action.feedback) ?? {};
          const status = stringValue(action.status);
          const actionType = stringValue(action.action_type) ?? stringValue(action.type);
          const writeTarget = stringValue(action.write_target);
          const label = stringValue(action.action_name)
            ?? resultActionLabelByType.get(actionType ?? '')
            ?? stringValue(action.write_target_label)
            ?? resultActionLabelByWriteTarget.get(writeTarget ?? '')
            ?? '结果动作';
          const recordsImported = action.records_imported ?? feedback.records_imported;
          const documentId = stringValue(feedback.document_id);
          const writeMode = stringValue(feedback.write_mode);
          const invocationLogId = stringValue(feedback.plugin_invocation_log_id);
          const errorMessage = stringValue(action.error_message) ?? stringValue(feedback.error_message);
          return {
            children: (
              <Space size={[8, 8]} wrap>
                <Typography.Text>{label}</Typography.Text>
                <Tag color={resultActionStatusColor(status)}>{resultActionStatusLabel(status)}</Tag>
                {recordsImported !== undefined ? <Tag>写入 {String(recordsImported)} 条</Tag> : null}
                {documentId ? <Tag color="blue">文档 {documentId}</Tag> : null}
                {writeMode ? <Tag>方式 {writeMode === 'append' ? '追加' : '覆盖'}</Tag> : null}
                {invocationLogId ? <Tag color="purple">调用日志 {invocationLogId}</Tag> : null}
                {errorMessage ? <Typography.Text type="danger">{errorMessage}</Typography.Text> : null}
              </Space>
            ),
            key: `${actionType ?? writeTarget ?? 'result_action'}-${index}`,
            label: `动作 ${index + 1}`,
          };
        })}
        size="small"
      />
    </Space>
  );
}

function packageBoundaryItems(run: ScheduledJobRunRecord) {
  const items: Array<{
    entry?: string;
    files: string[];
    label: string;
    note?: string;
    scriptExecution?: string;
  }> = [];
  const agentSnapshot = recordValue(run.resolved_agent_snapshot);
  const agentPackage = recordValue(agentSnapshot?.package_snapshot);
  const agentBoundary = recordValue(agentPackage?.runtime_boundary);
  if (agentBoundary) {
    items.push({
      entry: stringValue(agentPackage?.entry),
      files: stringArray(agentBoundary.script_files),
      label: `AI角色 ${stringValue(agentSnapshot?.name) ?? stringValue(agentSnapshot?.code) ?? '-'}`,
      note: stringValue(agentBoundary.script_note),
      scriptExecution: stringValue(agentBoundary.script_execution),
    });
  }
  for (const skill of arrayOfRecords(run.resolved_skill_snapshots)) {
    const skillPackage = recordValue(skill.package_snapshot);
    const skillBoundary = recordValue(skillPackage?.runtime_boundary);
    if (!skillBoundary) {
      continue;
    }
    items.push({
      entry: stringValue(skillPackage?.entry),
      files: stringArray(skillBoundary.script_files),
      label: `Skill ${stringValue(skill.name) ?? stringValue(skill.code) ?? '-'}`,
      note: stringValue(skillBoundary.script_note),
      scriptExecution: stringValue(skillBoundary.script_execution),
    });
  }
  return items;
}

function ScriptExecutionBoundary({ run }: { run: ScheduledJobRunRecord }) {
  const items = packageBoundaryItems(run);
  if (!items.length) {
    return null;
  }
  return (
    <Space
      aria-label="AI文件包运行边界"
      orientation="vertical"
      size={8}
      style={{
        background: '#f8fafc',
        border: '1px solid #e5e7eb',
        borderRadius: 6,
        padding: 12,
        width: '100%',
      }}
    >
      <Typography.Text strong>AI文件包运行边界</Typography.Text>
      {items.map((item) => (
        <Space key={`${item.label}-${item.entry ?? ''}`} orientation="vertical" size={6} style={{ width: '100%' }}>
          <Space size={[8, 8]} wrap>
            <Typography.Text>{item.label}</Typography.Text>
            {item.entry ? <Tag color="blue">入口 {item.entry}</Tag> : null}
            {item.scriptExecution ? <Tag color="orange">脚本执行 {item.scriptExecution}</Tag> : null}
            {item.files.length ? <Tag color="purple">脚本文件 {item.files.join('、')}</Tag> : <Tag>无脚本文件</Tag>}
          </Space>
          {item.note ? <Typography.Text type="secondary">{item.note}</Typography.Text> : null}
        </Space>
      ))}
    </Space>
  );
}

function RepositoryExecutionDetails({ run }: { run: ScheduledJobRunRecord }) {
  const repositoryExecution = recordValue(run.result_summary?.repository_execution);
  const entries = repositoryExecution ? Object.entries(repositoryExecution) : [];
  if (!entries.length) {
    return null;
  }
  return (
    <Space
      aria-label="代码仓库执行明细"
      orientation="vertical"
      size={10}
      style={{ width: '100%' }}
    >
      <Typography.Text strong>代码仓库执行明细</Typography.Text>
      {entries.map(([repositoryId, rawValue]) => {
        const value = recordValue(rawValue) ?? {};
        const nativeScan = recordValue(value.native_scan) ?? {};
        const skillProcessing = recordValue(value.skill_processing) ?? {};
        const resultAction = recordValue(value.result_action) ?? {};
        const resultFeedback = recordValue(resultAction.feedback) ?? {};
        const report = recordValue(value.code_inspection_report) ?? {};
        return (
          <Descriptions
            bordered
            column={2}
            items={[
              { key: 'repository_id', label: '仓库', children: repositoryId },
              { key: 'scan_status', label: '扫描状态', children: scalarText(nativeScan.status) },
              { key: 'commit_sha', label: 'Commit', children: scalarText(nativeScan.commit_sha) },
              { key: 'scan_count', label: '扫描问题数', children: scalarText(nativeScan.finding_count ?? nativeScan.records_imported, '0') },
              { key: 'ai_status', label: 'AI 状态', children: scalarText(skillProcessing.status) },
              {
                key: 'model_gateway_called',
                label: '调用大模型',
                children: skillProcessing.model_gateway_called ? '是' : '否',
              },
              { key: 'write_status', label: '写入状态', children: scalarText(resultAction.status) },
              { key: 'report_id', label: '报告', children: scalarText(report.report_id ?? resultFeedback.report_id) },
            ]}
            key={repositoryId}
            size="small"
          />
        );
      })}
    </Space>
  );
}

function assistantRunRepairDraftPrompt() {
  return '这次失败怎么修？帮我生成修复草案';
}

function assistantRunComparisonPrompt() {
  return '和上次成功有什么不同？';
}

function assistantRunInsightDraftPrompt() {
  return '请基于这次定时作业运行结果生成用户洞察草案，保留数据来源、AI处理结论和结果动作反馈。';
}

function assistantRunRequirementDraftPrompt() {
  return '请基于这次定时作业运行结果提炼可落地的需求草案，包含背景、目标、价值、验收标准和建议优先级。';
}

function assistantRunBugDraftPrompt() {
  return '请基于这次定时作业运行结果识别需要跟进的缺陷或异常，生成 Bug 草案，包含复现线索、影响范围、严重级别和建议处理人。';
}

function assistantRunFollowupUrl(run: ScheduledJobRunRecord, prompt = assistantRunFollowupPrompt(run)) {
  const params = new URLSearchParams();
  params.set('reference_type', 'scheduled_job_run');
  params.set('reference_id', run.id);
  params.set('prompt', prompt);
  return `/assistant?${params.toString()}`;
}

function exportFilename(run: ScheduledJobRunRecord) {
  const normalizedId = String(run.id || 'scheduled_job_run').replace(/[^\w.-]+/g, '_');
  return `${normalizedId}_detail.json`;
}

function downloadJsonFile(filename: string, payload: unknown) {
  const content = JSON.stringify(payload, null, 2);
  const link = document.createElement('a');
  const canUseBlobUrl = typeof URL.createObjectURL === 'function';
  let objectUrl: string | undefined;
  if (canUseBlobUrl) {
    objectUrl = URL.createObjectURL(new Blob([content], { type: 'application/json;charset=utf-8' }));
    link.href = objectUrl;
  } else {
    link.href = `data:application/json;charset=utf-8,${encodeURIComponent(content)}`;
  }
  link.download = filename;
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  if (objectUrl && typeof URL.revokeObjectURL === 'function') {
    URL.revokeObjectURL(objectUrl);
  }
}

export function ScheduledJobRunDetailModal({
  agentLabel,
  executionModeLabel,
  focusedResultWriteRecordId,
  jobTypeLabel,
  modelLabel,
  onClose,
  onCopyRun,
  onGenerateTemplate,
  onRefresh,
  onTraceFullRunRerunRequested,
  onTraceNodeRerunCreated,
  refreshing,
  resultWriteRecords,
  resultWriteRecordsLoading,
  run,
  skillLabels,
}: ScheduledJobRunDetailModalProps) {
  const exportRunDetail = () => {
    if (!run) {
      return;
    }
    downloadJsonFile(
      exportFilename(run),
      buildScheduledJobRunDetailExportPayload({
        agentLabel,
        executionModeLabel,
        jobTypeLabel,
        modelLabel,
        resultWriteRecords,
        run,
        skillLabels,
      }),
    );
  };

  const businessDraftItems = run
    ? [
        {
          icon: <BulbOutlined />,
          key: 'insight-draft',
          label: <a href={assistantRunFollowupUrl(run, assistantRunInsightDraftPrompt())}>转洞察草案</a>,
        },
        {
          icon: <FileAddOutlined />,
          key: 'requirement-draft',
          label: <a href={assistantRunFollowupUrl(run, assistantRunRequirementDraftPrompt())}>转需求草案</a>,
        },
        {
          icon: <BugOutlined />,
          key: 'bug-draft',
          label: <a href={assistantRunFollowupUrl(run, assistantRunBugDraftPrompt())}>转 Bug 草案</a>,
        },
      ]
    : [];
  const resultSummaryMessage = run ? runResultSummaryMessage(run) : undefined;

  return (
    <Modal
      destroyOnHidden
      footer={(
        <Space wrap>
          <Button onClick={onClose}>关闭</Button>
          {run?.status === 'succeeded' ? (
            <Button onClick={() => void onGenerateTemplate(run)}>
              生成模板
            </Button>
          ) : null}
          {run ? (
            <ExecutionTraceLink asButton sourceId={run.id} sourceType="scheduled_job_run">
              执行诊断
            </ExecutionTraceLink>
          ) : null}
          {run ? (
            <Button aria-label="导出 JSON" icon={<DownloadOutlined />} onClick={exportRunDetail}>
              导出 JSON
            </Button>
          ) : null}
          {run ? (
            <Button
              aria-label="问 AI"
              href={assistantRunFollowupUrl(run)}
              icon={<RobotOutlined />}
            >
              问 AI
            </Button>
          ) : null}
          {run ? (
            <Dropdown menu={{ items: businessDraftItems }} trigger={['click']}>
              <Button aria-label="转业务草案" icon={<BulbOutlined />}>
                转业务草案
                <DownOutlined />
              </Button>
            </Dropdown>
          ) : null}
          {run?.status === 'failed' ? (
            <>
              <Button
                aria-label="继续诊断"
                href={assistantRunFollowupUrl(run, assistantRunFollowupPrompt(run))}
                icon={<RobotOutlined />}
              >
                继续诊断
              </Button>
              <Button
                aria-label="生成修复草案"
                href={assistantRunFollowupUrl(run, assistantRunRepairDraftPrompt())}
                icon={<EditOutlined />}
              >
                生成修复草案
              </Button>
              <Button
                aria-label="对比上次成功"
                href={assistantRunFollowupUrl(run, assistantRunComparisonPrompt())}
                icon={<ReloadOutlined />}
              >
                对比上次成功
              </Button>
            </>
          ) : null}
          {run ? (
            <Button icon={<CopyOutlined />} type="primary" onClick={() => onCopyRun(run)}>
              复制本次配置
            </Button>
          ) : null}
        </Space>
      )}
      open={Boolean(run)}
      title={
        <Space size={8}>
          <span>运行结果详情</span>
          {run ? (
            <Button
              aria-label="刷新运行结果"
              icon={<ReloadOutlined />}
              loading={refreshing}
              size="small"
              onClick={() => void onRefresh()}
            >
              刷新
            </Button>
          ) : null}
        </Space>
      }
      width={980}
      onCancel={onClose}
    >
      {run ? (
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Descriptions
            bordered
            column={2}
            items={[
              { key: 'id', label: '运行 ID', children: run.id },
              { key: 'status', label: '状态', children: run.status },
              ...(resultSummaryMessage
                ? [{ key: 'result_summary_message', label: '运行摘要', children: resultSummaryMessage }]
                : []),
              { key: 'job_type', label: '作业类型', children: jobTypeLabel },
              { key: 'execution_mode', label: 'AI执行', children: executionModeLabel },
              { key: 'model_gateway_config_id', label: 'AI 模型', children: modelLabel },
              { key: 'agent_id', label: 'AI角色', children: agentLabel },
              { key: 'skill_ids', label: 'Skills', children: skillLabels },
              {
                key: 'trigger_type',
                label: '触发方式',
                children: runTriggerTypeLabelByValue.get(String(run.trigger_type ?? '')) ?? run.trigger_type ?? '-',
              },
              { key: 'records_imported', label: '导入数', children: run.records_imported ?? 0 },
              { key: 'source_run_id', label: '复跑来源', children: run.source_run_id || '-' },
              {
                key: 'template_source',
                label: '模板来源',
                children: (
                  <TemplateSourceSummary
                    source={templateSourceFromConfig(recordValue(run.config_snapshot?.config_json))}
                  />
                ),
              },
              { key: 'collector_run_id', label: '采集运行', children: run.collector_run_id || '-' },
              { key: 'plugin_invocation_log_id', label: '插件调用', children: run.plugin_invocation_log_id || '-' },
              {
                key: 'scheduled_job_name',
                label: '作业名称',
                children: run.scheduled_job_name || run.scheduled_job_id || '-',
              },
              { key: 'started_at', label: '开始时间', children: formatDisplayDateTime(run.started_at) },
              { key: 'finished_at', label: '结束时间', children: formatDisplayDateTime(run.finished_at) },
              { key: 'error_code', label: '错误码', children: run.error_code || '-' },
              {
                key: 'error_message',
                label: '错误信息',
                children: run.error_message || '-',
              },
            ]}
            size="small"
          />
          <ResultActionExecutionSummary run={run} />
          <RunSourceComparison run={run} />
          <RunExecutionChain run={run} />
          <RepositoryExecutionDetails run={run} />
          <RunTraceDag
            onFullRunRerunRequested={onTraceFullRunRerunRequested}
            onNodeRerunCreated={onTraceNodeRerunCreated}
            run={run}
          />
          <ScriptExecutionBoundary run={run} />
          <ScheduledJobRunResultWriteRecords
            focusedRecordId={focusedResultWriteRecordId}
            loading={resultWriteRecordsLoading}
            records={resultWriteRecords}
          />
          <JsonPreview title="数据连接获取内容" value={getRunExecutionNode(run, 'data_connection')} />
          <JsonPreview title="AI执行处理内容" value={getRunExecutionNode(run, 'skill_processing')} />
          <JsonPreview title="动作反馈内容" value={getRunExecutionNode(run, 'result_action')} />
          <JsonPreview title="代码巡检报告写入结果" value={getRunExecutionNode(run, 'code_inspection_report')} />
          <JsonPreview title="严重问题自动创建 Bug" value={getRunExecutionNode(run, 'bug_creation')} />
          <JsonPreview title="严重问题自动创建整改需求" value={getRunExecutionNode(run, 'requirement_creation')} />
          <JsonPreview title="问题消息通知" value={getRunExecutionNode(run, 'notifications')} />
          <JsonPreview title="动作执行状态" value={getRunExecutionNode(run, 'result_actions')} />
          <JsonPreview title="结果摘要" value={run.result_summary} />
          <JsonPreview title="插件快照" value={run.resolved_plugin_snapshot} />
          <JsonPreview title="Skill 快照" value={run.resolved_skill_snapshots} />
          <JsonPreview title="Prompt 快照" value={run.resolved_prompt_snapshot} />
          <JsonPreview title="作业配置快照" value={run.config_snapshot} />
        </Space>
      ) : null}
    </Modal>
  );
}
