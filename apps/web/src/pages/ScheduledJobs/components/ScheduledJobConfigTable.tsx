import {
  CopyOutlined,
  DeleteOutlined,
  EditOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import { Button, Space, Tag, Typography } from 'antd';

import type { ModelGatewayConfigRecord } from '../../../data/management';
import type {
  AiAgentRecord,
  PluginActionRecord,
  PluginConnectionRecord,
  ScheduledJobRecord,
  ScheduledJobResultAction,
} from '../../../services/aiBrain';
import { formatDisplayDateTime } from '../../../utils/dateTime';
import { TemplateSourceSummary } from './ScheduledJobRunTraceDetails';
import {
  multiIdsFromScheduledJob,
  statusLabelByValue,
} from './scheduledJobFormTransformHelpers';
import { templateSourceFromConfig } from './scheduledJobRunTraceHelpers';

type ScheduledJobConfigTableProps = {
  agentById: Map<string, AiAgentRecord>;
  confirmDeleteJob: (job: ScheduledJobRecord) => void;
  executionModeLabelMap: Map<string, string>;
  formatResultActionLabels: (actions?: ScheduledJobResultAction[]) => string;
  jobTypeLabelMap: Map<string, string>;
  jobs: ScheduledJobRecord[];
  loading: boolean;
  modelGatewayConfigById: Map<string, ModelGatewayConfigRecord>;
  onCreateJob: () => void;
  onCopyJob: (job: ScheduledJobRecord) => void;
  onEditJob: (job: ScheduledJobRecord) => void;
  onReload: () => void;
  onRunJob: (job: ScheduledJobRecord) => void;
  pluginActionById: Map<string, PluginActionRecord>;
  pluginConnectionById: Map<string, PluginConnectionRecord>;
  runningJobId?: string;
  scheduleTypeLabelMap: Map<string, string>;
};

function ellipsisText(value: string | undefined) {
  const text = value || '-';
  return (
    <Typography.Text ellipsis={{ tooltip: text }} style={{ display: 'block', maxWidth: '100%' }}>
      {text}
    </Typography.Text>
  );
}

export function ScheduledJobConfigTable({
  agentById,
  confirmDeleteJob,
  executionModeLabelMap,
  formatResultActionLabels,
  jobTypeLabelMap,
  jobs,
  loading,
  modelGatewayConfigById,
  onCreateJob,
  onCopyJob,
  onEditJob,
  onReload,
  onRunJob,
  pluginActionById,
  pluginConnectionById,
  runningJobId,
  scheduleTypeLabelMap,
}: ScheduledJobConfigTableProps) {
  return (
    <ProTable<ScheduledJobRecord>
      cardBordered
      className="management-list-table"
      columns={[
        { dataIndex: 'name', title: '名称', width: 220, render: (value) => ellipsisText(String(value ?? '')) },
        {
          key: 'template_source',
          title: '模板来源',
          width: 220,
          render: (_, row) => <TemplateSourceSummary source={templateSourceFromConfig(row.config_json)} />,
        },
        {
          dataIndex: 'job_type',
          title: '类型',
          width: 190,
          render: (value) => ellipsisText(jobTypeLabelMap.get(String(value)) ?? String(value ?? '')),
        },
        {
          dataIndex: 'plugin_connection_id',
          title: '数据连接',
          width: 260,
          render: (_, row) => {
            const connectionLabels = multiIdsFromScheduledJob(
              row,
              'plugin_connection_ids',
              'plugin_connection_id',
            ).map((connectionId) => {
              const connection = pluginConnectionById.get(connectionId);
              return connection
                ? `${connection.name} (${connection.environment ?? 'default'})`
                : connectionId;
            });
            return ellipsisText(connectionLabels.join(' / '));
          },
        },
        {
          key: 'ai_execution',
          title: 'AI执行',
          width: 300,
          render: (_, row) => {
            const modeLabel = executionModeLabelMap.get(String(row.execution_mode)) ?? String(row.execution_mode ?? '-');
            const config = row.model_gateway_config_id
              ? modelGatewayConfigById.get(String(row.model_gateway_config_id))
              : undefined;
            const agent = row.agent_id ? agentById.get(String(row.agent_id)) : undefined;
            const skillCount = Array.isArray(row.skill_ids) ? row.skill_ids.length : 0;
            const parts = [
              modeLabel,
              row.execution_mode === 'deterministic' ? undefined : config?.name,
              row.execution_mode === 'deterministic' ? undefined : agent?.name,
              row.execution_mode === 'deterministic' || !skillCount ? undefined : `${skillCount} Skill`,
            ].filter((item): item is string => Boolean(item));
            return ellipsisText(parts.join(' · '));
          },
        },
        {
          key: 'action',
          title: '动作',
          width: 280,
          render: (_, row) => {
            const actionLabels = multiIdsFromScheduledJob(row, 'plugin_action_ids', 'plugin_action_id').map(
              (actionId) => pluginActionById.get(actionId)?.name ?? actionId,
            );
            const resultActions = formatResultActionLabels(row.result_actions as ScheduledJobResultAction[]);
            return ellipsisText([...actionLabels, resultActions].filter(Boolean).join(' / '));
          },
        },
        {
          dataIndex: 'schedule_type',
          title: '调度',
          width: 180,
          render: (value, row) => {
            const scheduleLabel = scheduleTypeLabelMap.get(String(value)) ?? String(value ?? '-');
            const scheduleValue = row.cron_expression || (row.interval_seconds ? `${row.interval_seconds}s` : undefined);
            return ellipsisText([scheduleLabel, scheduleValue].filter(Boolean).join(' · '));
          },
        },
        {
          dataIndex: 'next_run_at',
          title: '下次运行',
          width: 180,
          render: (_, row) => ellipsisText(formatDisplayDateTime(row.next_run_at)),
        },
        {
          dataIndex: 'status',
          title: '状态',
          width: 100,
          render: (value, row) => (
            <Tag color={row.enabled ? 'green' : 'default'}>
              {statusLabelByValue.get(String(value)) ?? String(value ?? '-')}
            </Tag>
          ),
        },
        {
          fixed: 'right',
          key: 'actions',
          title: '操作',
          valueType: 'option',
          width: 330,
          render: (_, row) => (
            <Space className="management-row-actions" size={0}>
              <Button
                aria-label={`编辑作业 ${row.name}`}
                icon={<EditOutlined />}
                onClick={() => onEditJob(row)}
                type="link"
              >
                编辑
              </Button>
              <Button
                aria-label={`复制作业 ${row.name}`}
                icon={<CopyOutlined />}
                onClick={() => onCopyJob(row)}
                type="link"
              >
                复制
              </Button>
              <Button
                aria-label={`运行作业 ${row.name}`}
                disabled={Boolean(runningJobId)}
                icon={<PlayCircleOutlined />}
                loading={runningJobId === row.id}
                onClick={() => onRunJob(row)}
                type="link"
              >
                运行
              </Button>
              <Button
                aria-label={`删除作业 ${row.name}`}
                danger
                icon={<DeleteOutlined />}
                onClick={() => confirmDeleteJob(row)}
                type="link"
              >
                删除
              </Button>
            </Space>
          ),
        },
      ]}
      dataSource={jobs}
      dateFormatter="string"
      headerTitle="作业配置"
      loading={loading}
      options={{
        density: true,
        fullScreen: true,
        reload: onReload,
        setting: true,
      }}
      pagination={{
        showSizeChanger: true,
        showTotal: (total) => `共 ${total} 条`,
      }}
      rowKey="id"
      scroll={{ x: 1540 }}
      search={false}
      tableLayout="fixed"
      toolBarRender={() => [
        <Button key="create-job" aria-label="新增作业" icon={<PlusOutlined />} type="primary" onClick={onCreateJob}>
          新增作业
        </Button>,
        <Button key="reload-jobs" icon={<ReloadOutlined />} onClick={onReload}>
          刷新
        </Button>,
      ]}
    />
  );
}
