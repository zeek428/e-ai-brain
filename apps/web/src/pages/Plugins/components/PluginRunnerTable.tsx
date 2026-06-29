import {
  CopyOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  FileTextOutlined,
  KeyOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import { Button, Space, Tag, Typography } from 'antd';
import type { TablePaginationConfig } from 'antd';
import type { SorterResult } from 'antd/es/table/interface';

import type { AiExecutorRunnerListQuery, AiExecutorRunnerRecord } from '../../../services/aiBrain';
import { formatDisplayDateTime } from '../../../utils/dateTime';
import { aiExecutorTypeOptions } from './pluginRunnerHelpers';
import { runnerHealthStatusColor } from './pluginDiagnosticsHelpers';

type PluginRunnerTableProps = {
  loading: boolean;
  onCopySetupCommand: (command: string) => void;
  onCreateRunner: () => void;
  onDeleteRunner: (runner: AiExecutorRunnerRecord) => void;
  onDownloadInstallPackage: (runner: AiExecutorRunnerRecord) => void;
  onEditRunner: (runner: AiExecutorRunnerRecord) => void;
  onOpenLogs: (runner: AiExecutorRunnerRecord) => void;
  onRemoteChange: (query: AiExecutorRunnerListQuery) => void;
  onReload: () => void;
  onRotateToken: (runner: AiExecutorRunnerRecord) => void;
  onTestRunner: (runner: AiExecutorRunnerRecord) => void;
  remote: {
    page: number;
    pageSize: number;
    performance?: {
      duration_ms?: number;
    };
    total: number;
  };
  runners: AiExecutorRunnerRecord[];
  testingRunnerId?: string;
};

const SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID = 'ai_executor_runner_system_default';
const SYSTEM_DEFAULT_AI_EXECUTOR_TYPE = 'model_gateway';

const aiExecutorTypeLabelByValue = new Map([
  [SYSTEM_DEFAULT_AI_EXECUTOR_TYPE, '系统默认模型'],
  ...aiExecutorTypeOptions.map((option) => [option.value, option.label] as const),
]);

function stringValue(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback;
}

function aiExecutorTypeLabel(value: unknown): string {
  const key = String(value ?? '');
  return aiExecutorTypeLabelByValue.get(key) ?? key;
}

function isSystemDefaultRunner(runner: AiExecutorRunnerRecord) {
  return runner.id === SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID
    || runner.protocol === SYSTEM_DEFAULT_AI_EXECUTOR_TYPE
    || runner.metadata?.is_system === true;
}

function latestRunnerTaskId(runner: AiExecutorRunnerRecord): string | undefined {
  const metadataTaskId = runner.metadata?.latest_task_id;
  return runner.latest_task_id ?? (typeof metadataTaskId === 'string' ? metadataTaskId : undefined);
}

function normalizeRunnerSorter(
  sorter: SorterResult<AiExecutorRunnerRecord> | SorterResult<AiExecutorRunnerRecord>[],
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

export function PluginRunnerTable({
  loading,
  onCopySetupCommand,
  onCreateRunner,
  onDeleteRunner,
  onDownloadInstallPackage,
  onEditRunner,
  onOpenLogs,
  onRemoteChange,
  onReload,
  onRotateToken,
  onTestRunner,
  remote,
  runners,
  testingRunnerId,
}: PluginRunnerTableProps) {
  return (
    <ProTable<AiExecutorRunnerRecord>
      cardBordered
      className="management-list-table"
      columns={[
        { dataIndex: 'name', sorter: true, title: '名称', ellipsis: true, width: 220 },
        { dataIndex: 'protocol', sorter: true, title: '协议', width: 150 },
        {
          dataIndex: 'health_status',
          title: '健康状态',
          width: 260,
          render: (_, row) => (
            <Space orientation="vertical" size={2}>
              <Tag color={runnerHealthStatusColor(row.health_status)}>{row.health_status ?? 'unknown'}</Tag>
              {typeof row.heartbeat_age_seconds === 'number' ? (
                <Typography.Text type="secondary">{row.heartbeat_age_seconds}s</Typography.Text>
              ) : null}
              {row.health_alert?.message ? (
                <Typography.Text
                  ellipsis={{ tooltip: row.health_alert.message }}
                  type={row.health_alert.severity === 'critical' ? 'danger' : 'secondary'}
                >
                  {row.health_alert.message}
                </Typography.Text>
              ) : null}
            </Space>
          ),
        },
        {
          dataIndex: 'executor_types',
          title: '执行器类型',
          width: 240,
          render: (value) => Array.isArray(value)
            ? (
              <Space wrap size={4}>
                {value.map((item) => <Tag key={String(item)}>{aiExecutorTypeLabel(item)}</Tag>)}
              </Space>
            )
            : '-',
        },
        {
          dataIndex: 'workspace_roots',
          title: '工作区白名单',
          ellipsis: true,
          width: 280,
          render: (value) => Array.isArray(value) && value.length > 0 ? value.join(', ') : '*',
        },
        {
          dataIndex: 'last_heartbeat_at',
          title: '最后心跳',
          sorter: true,
          ellipsis: true,
          width: 220,
          render: (_, row) => formatDisplayDateTime(row.last_heartbeat_at),
        },
        {
          dataIndex: 'token_configured',
          title: 'Token',
          width: 220,
          render: (value, row) => {
            if (isSystemDefaultRunner(row)) {
              return <Tag color="blue">系统托管</Tag>;
            }
            return (
              <Space orientation="vertical" size={2}>
                <Space size={6} wrap>
                  <Tag color={value ? 'green' : 'default'}>{value ? '已配置' : '未配置'}</Tag>
                  <Typography.Text>Token v{row.token_version ?? 1}</Typography.Text>
                </Space>
                <Typography.Text type="secondary">
                  {row.token_rotated_at ? formatDisplayDateTime(row.token_rotated_at) : '未轮换'}
                </Typography.Text>
                {row.latest_task_id ? (
                  <Typography.Text type="secondary">
                    最近任务 {row.latest_task_status ?? '-'}
                  </Typography.Text>
                ) : null}
              </Space>
            );
          },
        },
        {
          dataIndex: 'status',
          title: '状态',
          sorter: true,
          width: 110,
          render: (value) => (
            <Tag color={value === 'active' ? 'green' : value === 'offline' ? 'orange' : 'default'}>
              {String(value)}
            </Tag>
          ),
        },
        {
          dataIndex: 'setup_command',
          title: '启动命令',
          ellipsis: true,
          width: 320,
          render: (_, row) => {
            const command = stringValue(row.setup_command);
            if (!command) {
              return '-';
            }
            return (
              <Space size={6} wrap={false}>
                <code style={{ wordBreak: 'break-all' }}>{command}</code>
                <Button
                  aria-label={`复制启动命令 ${row.name}`}
                  icon={<CopyOutlined />}
                  onClick={() => onCopySetupCommand(command)}
                  size="small"
                  type="text"
                />
              </Space>
            );
          },
        },
        {
          fixed: 'right',
          key: 'actions',
          title: '操作',
          valueType: 'option',
          width: 360,
          render: (_, row) => {
            const testButton = (
              <Button
                aria-label={`测试执行器 ${row.name}`}
                icon={<PlayCircleOutlined />}
                loading={testingRunnerId === row.id}
                onClick={() => onTestRunner(row)}
                type="link"
              >
                测试
              </Button>
            );
            if (isSystemDefaultRunner(row)) {
              return (
                <Space className="management-row-actions" size={0}>
                  {testButton}
                  <Tag color="blue">系统内置</Tag>
                </Space>
              );
            }
            return (
              <Space className="management-row-actions" size={0}>
                {testButton}
                <Button
                  aria-label={`轮换 Token ${row.name}`}
                  icon={<KeyOutlined />}
                  onClick={() => onRotateToken(row)}
                  type="link"
                >
                  轮换
                </Button>
                <Button
                  aria-label={`查看执行日志 ${row.name}`}
                  disabled={!latestRunnerTaskId(row)}
                  icon={<FileTextOutlined />}
                  onClick={() => onOpenLogs(row)}
                  type="link"
                >
                  日志
                </Button>
                <Button
                  aria-label={`下载安装包 ${row.name}`}
                  icon={<DownloadOutlined />}
                  onClick={() => onDownloadInstallPackage(row)}
                  type="link"
                >
                  安装包
                </Button>
                <Button
                  aria-label={`编辑执行器 ${row.name}`}
                  icon={<EditOutlined />}
                  onClick={() => onEditRunner(row)}
                  type="link"
                >
                  编辑
                </Button>
                <Button
                  aria-label={`删除执行器 ${row.name}`}
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => onDeleteRunner(row)}
                  type="link"
                >
                  删除
                </Button>
              </Space>
            );
          },
        },
      ]}
      dataSource={runners}
      dateFormatter="string"
      expandable={{
        expandedRowRender: (record) => (
          <Space orientation="vertical" size={8} style={{ width: '100%' }}>
            <Typography.Text strong>
              {isSystemDefaultRunner(record) ? '系统默认执行器说明' : '本地 Runner 启动命令'}
            </Typography.Text>
            {record.setup_command ? (
              <Space size={8} wrap>
                <code style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                  {String(record.setup_command)}
                </code>
                <Button
                  aria-label={`复制启动命令 ${record.name}`}
                  icon={<CopyOutlined />}
                  onClick={() => onCopySetupCommand(String(record.setup_command))}
                  size="small"
                >
                  复制
                </Button>
              </Space>
            ) : (
              <Typography.Text type="secondary">创建或刷新 Runner 后由后端生成启动命令。</Typography.Text>
            )}
          </Space>
        ),
      }}
      headerTitle="AI 执行器"
      loading={loading}
      onChange={(
        pagination: TablePaginationConfig,
        _filters,
        sorter,
      ) => {
        onRemoteChange({
          page: pagination.current ?? remote.page,
          pageSize: pagination.pageSize ?? remote.pageSize,
          ...normalizeRunnerSorter(sorter),
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
      scroll={{ x: 1900 }}
      search={false}
      tableLayout="fixed"
      toolBarRender={() => [
        remote.performance?.duration_ms !== undefined ? (
          <Tag color="blue" key="query-performance">查询 {remote.performance.duration_ms}ms</Tag>
        ) : null,
        <Button
          aria-label="新增执行器"
          icon={<PlusOutlined />}
          key="create-runner"
          onClick={onCreateRunner}
          type="primary"
        >
          新增执行器
        </Button>,
        <Button icon={<ReloadOutlined />} key="reload-runners" onClick={onReload}>
          刷新
        </Button>,
      ]}
    />
  );
}
