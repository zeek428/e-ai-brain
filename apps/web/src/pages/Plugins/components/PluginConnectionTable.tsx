import {
  ApiOutlined,
  DeleteOutlined,
  EditOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import { Button, Space } from 'antd';
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
  loading: boolean;
  pluginById: Map<string, PluginRecord>;
  remote: PluginConnectionRemoteMeta;
  discoveringConnectionId?: string;
  testingConnectionId?: string;
  onCreateConnection: () => void;
  onDeleteConnection: (connection: PluginConnectionRecord) => void;
  onDiscoverTools: (connection: PluginConnectionRecord) => void | Promise<void>;
  onEditConnection: (connection: PluginConnectionRecord) => void;
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

function pluginDisplayName(
  connection: PluginConnectionRecord,
  pluginById: Map<string, PluginRecord>,
) {
  const projectedName = connection.plugin_name?.trim();
  const projectedCode = connection.plugin_code?.trim();
  return (
    projectedName
    || pluginById.get(connection.plugin_id)?.name
    || projectedCode
    || connection.plugin_id
  );
}

export function PluginConnectionTable({
  connections,
  discoveringConnectionId,
  loading,
  pluginById,
  remote,
  testingConnectionId,
  onCreateConnection,
  onDeleteConnection,
  onDiscoverTools,
  onEditConnection,
  onRemoteChange,
  onReload,
  onTestConnection,
}: PluginConnectionTableProps) {
  return (
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
            render: (_, row) => pluginDisplayName(row, pluginById),
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
            width: 340,
            render: (_, row) => {
              const isTestingConnection = testingConnectionId === row.id;
              const isDiscoveringConnection = discoveringConnectionId === row.id;
              const plugin = pluginById.get(row.plugin_id);
              const pluginCode = row.plugin_code ?? plugin?.code ?? '';
              const isDingTalkMcpConnection = pluginCode.startsWith('dingtalk_');
              const hasBusyConnection = Boolean(testingConnectionId || discoveringConnectionId);
              return (
                <Space className="management-row-actions" size={0}>
                  <Button
                    aria-label={`编辑连接 ${row.name}`}
                    disabled={hasBusyConnection}
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
                    disabled={hasBusyConnection}
                    htmlType="button"
                    icon={<PlayCircleOutlined />}
                    loading={isTestingConnection}
                    onClick={() => void onTestConnection(row)}
                    type="link"
                  >
                    {isTestingConnection ? '测试中' : '测试'}
                  </Button>
                  {isDingTalkMcpConnection ? (
                    <Button
                      aria-label={
                        isDiscoveringConnection
                          ? `发现能力中 ${row.name}`
                          : `发现能力 ${row.name}`
                      }
                      disabled={hasBusyConnection}
                      htmlType="button"
                      icon={<ApiOutlined />}
                      loading={isDiscoveringConnection}
                      onClick={() => void onDiscoverTools(row)}
                      type="link"
                    >
                      {isDiscoveringConnection ? '发现中' : '发现能力'}
                    </Button>
                  ) : null}
                  <Button
                    aria-label={`删除连接 ${row.name}`}
                    danger
                    disabled={hasBusyConnection}
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
      scroll={{ x: 1540 }}
      search={false}
      tableLayout="fixed"
      toolBarRender={() => [
        <Button
          aria-label="新增连接"
          icon={<PlusOutlined />}
          key="create-connection"
          onClick={onCreateConnection}
          type="primary"
        >
          新增连接
        </Button>,
        <Button icon={<ReloadOutlined />} key="reload-connections" onClick={onReload}>
          刷新
        </Button>,
      ]}
    />
  );
}
