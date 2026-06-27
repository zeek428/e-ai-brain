import {
  DeleteOutlined,
  EditOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import { Button, Select, Space, Typography } from 'antd';
import type { TablePaginationConfig } from 'antd';
import type { SorterResult } from 'antd/es/table/interface';

import type {
  PluginConnectionListQuery,
  PluginConnectionRecord,
  PluginRecord,
} from '../../../services/aiBrain';
import { ConnectionLastTestSummary } from './PluginDiagnostics';

type PluginConnectionRemoteMeta = {
  page: number;
  pageSize: number;
  total: number;
};

type PluginConnectionTableProps = {
  connections: PluginConnectionRecord[];
  environmentFilter?: string;
  environmentLabels: Map<string, string>;
  environmentOptions: Array<{ label: string; value: string }>;
  loading: boolean;
  pluginById: Map<string, PluginRecord>;
  remote: PluginConnectionRemoteMeta;
  testingConnectionId?: string;
  onCreateConnection: () => void;
  onDeleteConnection: (connection: PluginConnectionRecord) => void;
  onEditConnection: (connection: PluginConnectionRecord) => void;
  onEnvironmentFilterChange: (value?: string) => void;
  onRemoteChange: (query: PluginConnectionListQuery) => void;
  onReload: () => void;
  onTestConnection: (connection: PluginConnectionRecord) => void | Promise<void>;
};

function normalizeConnectionSorter(
  sorter: SorterResult<PluginConnectionRecord> | SorterResult<PluginConnectionRecord>[],
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

export function PluginConnectionTable({
  connections,
  environmentFilter,
  environmentLabels,
  environmentOptions,
  loading,
  pluginById,
  remote,
  testingConnectionId,
  onCreateConnection,
  onDeleteConnection,
  onEditConnection,
  onEnvironmentFilterChange,
  onRemoteChange,
  onReload,
  onTestConnection,
}: PluginConnectionTableProps) {
  return (
    <Space orientation="vertical" size={12} style={{ width: '100%' }}>
      <Space wrap>
        <Typography.Text type="secondary">环境</Typography.Text>
        <Select
          allowClear
          onChange={(value) => onEnvironmentFilterChange(value)}
          options={environmentOptions}
          placeholder="全部环境"
          style={{ width: 160 }}
          value={environmentFilter}
        />
        <Button
          aria-label="新增连接"
          htmlType="button"
          icon={<PlusOutlined />}
          onClick={onCreateConnection}
          type="primary"
        >
          新增连接
        </Button>
        <Button htmlType="button" icon={<ReloadOutlined />} onClick={onReload}>
          刷新
        </Button>
      </Space>
      <ProTable<PluginConnectionRecord>
        cardBordered
        className="management-list-table"
        columns={[
          { dataIndex: 'name', sorter: true, title: '名称', ellipsis: true, width: 220 },
          {
            dataIndex: 'plugin_id',
            sorter: true,
            title: '插件',
            ellipsis: true,
            width: 220,
            render: (value) => pluginById.get(String(value))?.name ?? value,
          },
          {
            dataIndex: 'environment',
            sorter: true,
            title: '环境',
            width: 130,
            render: (value) => environmentLabels.get(String(value)) ?? String(value ?? '-'),
          },
          { dataIndex: 'auth_type', title: '认证', width: 130 },
          { dataIndex: 'endpoint_url', sorter: true, title: 'Endpoint', ellipsis: true, width: 320 },
          {
            dataIndex: 'last_test_summary',
            title: '最近测试',
            width: 180,
            render: (_, row) => <ConnectionLastTestSummary connection={row} />,
          },
          { dataIndex: 'status', sorter: true, title: '状态', width: 110 },
          {
            fixed: 'right',
            key: 'actions',
            title: '操作',
            valueType: 'option',
            width: 260,
            render: (_, row) => {
              const isTestingConnection = testingConnectionId === row.id;
              return (
                <Space className="management-row-actions" size={0}>
                  <Button
                    aria-label={`编辑连接 ${row.name}`}
                    disabled={Boolean(testingConnectionId)}
                    htmlType="button"
                    icon={<EditOutlined />}
                    onClick={() => onEditConnection(row)}
                    type="link"
                  >
                    编辑
                  </Button>
                  <Button
                    aria-label={
                      isTestingConnection ? `连接测试中 ${row.name}` : `测试连接 ${row.name}`
                    }
                    disabled={Boolean(testingConnectionId)}
                    htmlType="button"
                    icon={<PlayCircleOutlined />}
                    loading={isTestingConnection}
                    onClick={() => void onTestConnection(row)}
                    type="link"
                  >
                    {isTestingConnection ? '测试中' : '测试'}
                  </Button>
                  <Button
                    aria-label={`删除连接 ${row.name}`}
                    danger
                    disabled={Boolean(testingConnectionId)}
                    htmlType="button"
                    icon={<DeleteOutlined />}
                    onClick={() => onDeleteConnection(row)}
                    type="link"
                  >
                    删除
                  </Button>
                </Space>
              );
            },
          },
        ]}
        dataSource={connections}
        dateFormatter="string"
        headerTitle="连接"
        loading={loading}
        onChange={(
          pagination: TablePaginationConfig,
          _filters,
          sorter,
        ) => {
          onRemoteChange({
            page: pagination.current ?? remote.page,
            pageSize: pagination.pageSize ?? remote.pageSize,
            ...normalizeConnectionSorter(sorter),
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
        scroll={{ x: 1600 }}
        search={false}
        tableLayout="fixed"
      />
    </Space>
  );
}
