import { Tabs } from 'antd';

import type { ModelGatewayConfigRecord } from '../../../data/management';
import type {
  AiAgentRecord,
  PluginActionRecord,
  PluginConnectionRecord,
  ScheduledJobRecord,
  ScheduledJobResultAction,
  ScheduledJobRunObservability,
  ScheduledJobRunRecord,
} from '../../../services/aiBrain';
import { ScheduledJobConfigTable } from './ScheduledJobConfigTable';
import { ScheduledJobRunTable } from './ScheduledJobRunTable';
import type { ScheduledJobPageTab } from './scheduledJobFormTransformHelpers';

type ScheduledJobManagementTabsProps = {
  activeTab: ScheduledJobPageTab;
  agentById: Map<string, AiAgentRecord>;
  confirmDeleteJob: (job: ScheduledJobRecord) => void;
  executionModeLabelMap: Map<string, string>;
  formatResultActionLabels: (actions?: ScheduledJobResultAction[]) => string;
  jobTypeLabelMap: Map<string, string>;
  jobs: ScheduledJobRecord[];
  loading: boolean;
  modelGatewayConfigById: Map<string, ModelGatewayConfigRecord>;
  onCopyJob: (job: ScheduledJobRecord) => void;
  onCopyRun: (run: ScheduledJobRunRecord) => void;
  onCreateJob: () => void;
  onEditJob: (job: ScheduledJobRecord) => void;
  onOpenRunDetail: (run: ScheduledJobRunRecord) => void;
  onReload: () => void;
  onRerun: (run: ScheduledJobRunRecord) => void;
  onRunJob: (job: ScheduledJobRecord) => void;
  onTabChange: (tab: ScheduledJobPageTab) => void;
  pluginActionById: Map<string, PluginActionRecord>;
  pluginConnectionById: Map<string, PluginConnectionRecord>;
  runObservability?: ScheduledJobRunObservability;
  runningJobId?: string;
  runs: ScheduledJobRunRecord[];
  scheduleTypeLabelMap: Map<string, string>;
};

export function ScheduledJobManagementTabs({
  activeTab,
  agentById,
  confirmDeleteJob,
  executionModeLabelMap,
  formatResultActionLabels,
  jobTypeLabelMap,
  jobs,
  loading,
  modelGatewayConfigById,
  onCopyJob,
  onCopyRun,
  onCreateJob,
  onEditJob,
  onOpenRunDetail,
  onReload,
  onRerun,
  onRunJob,
  onTabChange,
  pluginActionById,
  pluginConnectionById,
  runObservability,
  runningJobId,
  runs,
  scheduleTypeLabelMap,
}: ScheduledJobManagementTabsProps) {
  return (
    <Tabs
      activeKey={activeTab}
      items={[
        {
          key: 'jobs',
          label: '作业配置',
          children: (
            <ScheduledJobConfigTable
              agentById={agentById}
              confirmDeleteJob={confirmDeleteJob}
              executionModeLabelMap={executionModeLabelMap}
              formatResultActionLabels={formatResultActionLabels}
              jobTypeLabelMap={jobTypeLabelMap}
              jobs={jobs}
              loading={loading}
              modelGatewayConfigById={modelGatewayConfigById}
              onCopyJob={onCopyJob}
              onCreateJob={onCreateJob}
              onEditJob={onEditJob}
              onReload={onReload}
              onRunJob={onRunJob}
              pluginActionById={pluginActionById}
              pluginConnectionById={pluginConnectionById}
              runningJobId={runningJobId}
              scheduleTypeLabelMap={scheduleTypeLabelMap}
            />
          ),
        },
        {
          key: 'runs',
          label: '运行记录',
          children: (
            <ScheduledJobRunTable
              loading={loading}
              observability={runObservability}
              onCopyRun={onCopyRun}
              onOpenRunDetail={onOpenRunDetail}
              onReload={onReload}
              onRerun={onRerun}
              runningJobId={runningJobId}
              runs={runs}
            />
          ),
        },
      ]}
      onChange={(key) => onTabChange(key === 'runs' ? 'runs' : 'jobs')}
    />
  );
}
