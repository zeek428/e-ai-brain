import {
  CopyOutlined,
  EyeOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import { Button, Space, Spin, Typography } from 'antd';
import type { TablePaginationConfig } from 'antd';
import type { SorterResult } from 'antd/es/table/interface';

import type {
  ScheduledJobRunObservability,
  ScheduledJobRunListQuery,
  ScheduledJobRunRecord,
} from '../../../services/aiBrain';
import { formatDisplayDateTime } from '../../../utils/dateTime';
import { runTriggerTypeLabelByValue } from './scheduledJobFormTransformHelpers';
import { ScheduledJobRunObservabilityOverview } from './ScheduledJobRunObservabilityOverview';
import type { ScheduledJobRemoteTableMeta } from './useScheduledJobWorkspaceData';

type ScheduledJobRunTableProps = {
  loading: boolean;
  observability?: ScheduledJobRunObservability;
  onCopyRun: (run: ScheduledJobRunRecord) => void;
  onOpenRunDetail: (run: ScheduledJobRunRecord) => void;
  onRemoteChange: (query: ScheduledJobRunListQuery) => void;
  onReload: () => void;
  onRerun: (run: ScheduledJobRunRecord) => void;
  onShowAllRuns: () => void;
  remote: ScheduledJobRemoteTableMeta;
  runningJobId?: string;
  runFilterJobName?: string;
  runs: ScheduledJobRunRecord[];
};

function normalizeRunSorter(
  sorter: SorterResult<ScheduledJobRunRecord> | SorterResult<ScheduledJobRunRecord>[],
) {
  const activeSorter = Array.isArray(sorter)
    ? sorter.find((item) => item.order)
    : sorter.order
      ? sorter
      : undefined;
  if (!activeSorter) {
    return {};
  }
  const field =
    typeof activeSorter.field === 'string'
      ? activeSorter.field
      : typeof activeSorter.columnKey === 'string'
        ? activeSorter.columnKey
        : undefined;
  return {
    sortField: field,
    sortOrder: activeSorter.order === 'ascend' || activeSorter.order === 'descend'
      ? activeSorter.order
      : undefined,
  };
}

export function ScheduledJobRunTable({
  loading,
  observability,
  onCopyRun,
  onOpenRunDetail,
  onRemoteChange,
  onReload,
  onRerun,
  onShowAllRuns,
  remote,
  runningJobId,
  runFilterJobName,
  runs,
}: ScheduledJobRunTableProps) {
  return (
    <>
      <ScheduledJobRunObservabilityOverview loading={loading} observability={observability} />
      {runFilterJobName ? (
        <Space align="center" style={{ marginBottom: 12 }}>
          <Typography.Text type="secondary">当前作业：{runFilterJobName}</Typography.Text>
          <Button onClick={onShowAllRuns} type="link">查看全部</Button>
        </Space>
      ) : null}
      {loading ? (
        <Space aria-label="运行记录加载中" aria-live="polite" size={8} style={{ marginBottom: 12 }}>
          <Spin size="small" />
          <Typography.Text type="secondary">正在加载运行记录...</Typography.Text>
        </Space>
      ) : null}
      <ProTable<ScheduledJobRunRecord>
        cardBordered
        className="management-list-table"
        columns={[
          { dataIndex: 'id', title: '运行 ID', ellipsis: true, width: 220 },
          {
            dataIndex: 'scheduled_job_name',
            title: '作业名称',
            ellipsis: true,
            width: 260,
            render: (_, row) => row.scheduled_job_name || row.scheduled_job_id || '-',
          },
          { dataIndex: 'status', sorter: true, title: '状态', width: 120 },
          {
            dataIndex: 'trigger_type',
            sorter: true,
            title: '触发方式',
            width: 130,
            render: (value) => runTriggerTypeLabelByValue.get(String(value ?? '')) ?? value ?? '-',
          },
          {
            dataIndex: 'started_at',
            sorter: true,
            title: '开始时间',
            width: 180,
            render: (_, row) => formatDisplayDateTime(row.started_at),
          },
          {
            dataIndex: 'finished_at',
            sorter: true,
            title: '完成时间',
            width: 180,
            render: (_, row) => formatDisplayDateTime(row.finished_at),
          },
          { dataIndex: 'source_run_id', title: '复跑来源', ellipsis: true, width: 200, render: (value) => value || '-' },
          { dataIndex: 'collector_run_id', title: '采集运行', ellipsis: true, width: 220, render: (value) => value || '-' },
          { dataIndex: 'plugin_invocation_log_id', title: '插件调用', ellipsis: true, width: 220, render: (value) => value || '-' },
          { dataIndex: 'records_imported', sorter: true, title: '导入数', width: 100 },
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
        locale={{ emptyText: loading ? '正在加载运行记录...' : '暂无运行记录' }}
        loading={loading}
        onChange={(
          pagination: TablePaginationConfig,
          _filters,
          sorter,
        ) => {
          onRemoteChange({
            page: pagination.current ?? remote.page,
            pageSize: pagination.pageSize ?? remote.pageSize,
            ...normalizeRunSorter(sorter),
          });
        }}
        options={{
          density: true,
          fullScreen: true,
          reload: onReload,
          setting: true,
        }}
        pagination={{
          current: remote.page,
          pageSize: remote.pageSize,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
          total: remote.total,
        }}
        rowKey="id"
        scroll={{ x: 1860 }}
        search={false}
        tableLayout="fixed"
      />
    </>
  );
}
