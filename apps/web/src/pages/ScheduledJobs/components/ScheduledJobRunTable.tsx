import {
  CopyOutlined,
  EyeOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import { Button, Space } from 'antd';

import type {
  ScheduledJobRunObservability,
  ScheduledJobRunRecord,
} from '../../../services/aiBrain';
import { runTriggerTypeLabelByValue } from './scheduledJobFormTransformHelpers';
import { ScheduledJobRunObservabilityOverview } from './ScheduledJobRunObservabilityOverview';

type ScheduledJobRunTableProps = {
  loading: boolean;
  observability?: ScheduledJobRunObservability;
  onCopyRun: (run: ScheduledJobRunRecord) => void;
  onOpenRunDetail: (run: ScheduledJobRunRecord) => void;
  onReload: () => void;
  onRerun: (run: ScheduledJobRunRecord) => void;
  runningJobId?: string;
  runs: ScheduledJobRunRecord[];
};

export function ScheduledJobRunTable({
  loading,
  observability,
  onCopyRun,
  onOpenRunDetail,
  onReload,
  onRerun,
  runningJobId,
  runs,
}: ScheduledJobRunTableProps) {
  return (
    <>
      <ScheduledJobRunObservabilityOverview loading={loading} observability={observability} />
      <ProTable<ScheduledJobRunRecord>
        cardBordered
        className="management-list-table"
        columns={[
          { dataIndex: 'id', title: '运行 ID', ellipsis: true, width: 220 },
          { dataIndex: 'scheduled_job_id', title: '作业 ID', ellipsis: true, width: 220 },
          { dataIndex: 'status', title: '状态', width: 120 },
          {
            dataIndex: 'trigger_type',
            title: '触发方式',
            width: 130,
            render: (value) => runTriggerTypeLabelByValue.get(String(value ?? '')) ?? value ?? '-',
          },
          { dataIndex: 'source_run_id', title: '复跑来源', ellipsis: true, width: 200, render: (value) => value || '-' },
          { dataIndex: 'collector_run_id', title: '采集运行', ellipsis: true, width: 220, render: (value) => value || '-' },
          { dataIndex: 'plugin_invocation_log_id', title: '插件调用', ellipsis: true, width: 220, render: (value) => value || '-' },
          { dataIndex: 'records_imported', title: '导入数', width: 100 },
          { dataIndex: 'error_message', title: '错误', ellipsis: true, width: 180, render: (value) => value || '-' },
          {
            fixed: 'right',
            key: 'actions',
            title: '操作',
            valueType: 'option',
            width: 270,
            render: (_, row) => (
              <Space size={4}>
                <Button
                  aria-label={`查看运行结果 ${row.id}`}
                  icon={<EyeOutlined />}
                  onClick={() => onOpenRunDetail(row)}
                  type="link"
                >
                  详情
                </Button>
                <Button
                  aria-label={`复制运行配置 ${row.id}`}
                  icon={<CopyOutlined />}
                  onClick={() => onCopyRun(row)}
                  type="link"
                >
                  复制配置
                </Button>
                <Button
                  aria-label={`复跑运行 ${row.id}`}
                  disabled={Boolean(runningJobId) || !row.scheduled_job_id}
                  icon={<ReloadOutlined />}
                  loading={runningJobId === row.scheduled_job_id}
                  onClick={() => onRerun(row)}
                  type="link"
                >
                  复跑
                </Button>
              </Space>
            ),
          },
        ]}
        dataSource={runs}
        dateFormatter="string"
        headerTitle="运行记录"
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
        scroll={{ x: 1500 }}
        search={false}
        tableLayout="fixed"
      />
    </>
  );
}
