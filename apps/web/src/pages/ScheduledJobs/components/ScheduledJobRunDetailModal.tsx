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
import { Button, Descriptions, Dropdown, Modal, Space } from 'antd';

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

type ScheduledJobRunDetailModalProps = {
  agentLabel: string;
  executionModeLabel: string;
  focusedResultWriteRecordId?: string;
  jobTypeLabel: string;
  modelLabel: string;
  onClose: () => void;
  onCopyRun: (run: ScheduledJobRunRecord) => void;
  onGenerateTemplate: (run: ScheduledJobRunRecord) => void | Promise<void>;
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

function assistantRunFollowupPrompt(run: ScheduledJobRunRecord) {
  return run.status === 'failed' ? '为什么这次任务失败？' : '帮我分析这次运行结果';
}

function runResultSummaryMessage(run: ScheduledJobRunRecord): string | undefined {
  const message = run.result_summary?.message;
  return typeof message === 'string' && message.trim() ? message : undefined;
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

export function buildScheduledJobRunDetailExportPayload({
  agentLabel,
  executionModeLabel,
  jobTypeLabel,
  modelLabel,
  resultWriteRecords,
  run,
  skillLabels,
}: Pick<
  ScheduledJobRunDetailModalProps,
  | 'agentLabel'
  | 'executionModeLabel'
  | 'jobTypeLabel'
  | 'modelLabel'
  | 'resultWriteRecords'
  | 'run'
  | 'skillLabels'
>) {
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
      config: run.config_snapshot,
      plugin: run.resolved_plugin_snapshot,
      prompt: run.resolved_prompt_snapshot,
      skills: run.resolved_skill_snapshots,
    },
  };
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
      title="运行结果详情"
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
              { key: 'scheduled_job_id', label: '作业 ID', children: run.scheduled_job_id || '-' },
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
          <RunSourceComparison run={run} />
          <RunExecutionChain run={run} />
          <RunTraceDag run={run} />
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
          <JsonPreview title="严重问题自动创建整改任务" value={getRunExecutionNode(run, 'task_creation')} />
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
