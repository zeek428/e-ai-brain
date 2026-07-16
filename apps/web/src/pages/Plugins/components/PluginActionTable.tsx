import {
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
  PluginActionListQuery,
  PluginActionRecord,
  PluginConnectionRecord,
  PluginRecord,
} from '../../../services/aiBrain';

type PluginActionRemoteMeta = {
  page: number;
  pageSize: number;
  total: number;
};

type PluginActionTableProps = {
  actions: PluginActionRecord[];
  connectionById: Map<string, PluginConnectionRecord>;
  loading: boolean;
  pluginById: Map<string, PluginRecord>;
  remote: PluginActionRemoteMeta;
  formatWriteTarget: (writeTarget?: string | null) => string;
  onCreateAction: () => void;
  onDeleteAction: (action: PluginActionRecord) => void;
  onEditAction: (action: PluginActionRecord) => void;
  onRemoteChange: (query: PluginActionListQuery) => void;
  onReload: () => void;
  onRunAction: (action: PluginActionRecord) => void | Promise<void>;
  onTrialAction: (action: PluginActionRecord) => void;
};

function normalizeActionSorter(
  sorter: SorterResult<PluginActionRecord> | SorterResult<PluginActionRecord>[],
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

function actionInvocationLabel(
  action: PluginActionRecord,
  pluginById: Map<string, PluginRecord>,
) {
  const plugin = pluginById.get(action.plugin_id);
  if (plugin?.code === 'internal_data_source' && !action.connection_id) {
    return '内部结果写入';
  }
  if (action.action_type === 'mcp_tool') {
    return 'MCP 工具';
  }
  if (action.action_type === 'internal_query') {
    return '内部数据读取';
  }
  return 'HTTP 请求';
}

export function PluginActionTable({
  actions,
  connectionById,
  loading,
  pluginById,
  remote,
  formatWriteTarget,
  onCreateAction,
  onDeleteAction,
  onEditAction,
  onRemoteChange,
  onReload,
  onRunAction,
  onTrialAction,
}: PluginActionTableProps) {
  return (
    <ProTable<PluginActionRecord>
      cardBordered
      className="management-list-table"
      columns={[
        { dataIndex: 'name', sorter: true, title: '名称', ellipsis: true, width: 220 },
        { dataIndex: 'code', sorter: true, title: '编码', ellipsis: true, width: 200 },
        {
          dataIndex: 'action_type',
          sorter: true,
          title: '调用方式',
          width: 140,
          render: (_, row) => actionInvocationLabel(row, pluginById),
        },
        {
          dataIndex: 'plugin_id',
          sorter: true,
          title: '插件',
          ellipsis: true,
          width: 200,
          render: (value) => pluginById.get(String(value))?.name ?? value,
        },
        {
          dataIndex: 'connection_id',
          title: '连接',
          ellipsis: true,
          width: 200,
          render: (value) => (value ? connectionById.get(String(value))?.name ?? value : '-'),
        },
        {
          dataIndex: 'result_mapping',
          title: '写入目标',
          ellipsis: true,
          width: 220,
          render: (_, row) => {
            const resultMapping = row.result_mapping;
            const writeTarget =
              resultMapping && typeof resultMapping === 'object'
                ? resultMapping.write_target
                : undefined;
            return typeof writeTarget === 'string'
              ? formatWriteTarget(writeTarget)
              : formatWriteTarget();
          },
        },
        { dataIndex: 'status', sorter: true, title: '状态', width: 100 },
        {
          fixed: 'right',
          key: 'actions',
          title: '操作',
          valueType: 'option',
          width: 300,
          render: (_, row) => (
            <Space className="management-row-actions" size={0}>
              <Button
                aria-label={`编辑动作 ${row.name}`}
                icon={<EditOutlined />}
                onClick={() => onEditAction(row)}
                type="link"
              >
                编辑
              </Button>
              <Button icon={<PlayCircleOutlined />} onClick={() => onTrialAction(row)} type="link">
                试运行
              </Button>
              <Button onClick={() => void onRunAction(row)} type="link">
                运行
              </Button>
              <Button
                aria-label={`删除动作 ${row.name}`}
                danger
                icon={<DeleteOutlined />}
                onClick={() => onDeleteAction(row)}
                type="link"
              >
                删除
              </Button>
            </Space>
          ),
        },
      ]}
      dataSource={actions}
      dateFormatter="string"
      headerTitle="动作"
      loading={loading}
      onChange={(
        pagination: TablePaginationConfig,
        _filters,
        sorter,
      ) => {
        onRemoteChange({
          page: pagination.current ?? remote.page,
          pageSize: pagination.pageSize ?? remote.pageSize,
          ...normalizeActionSorter(sorter),
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
      scroll={{ x: 1570 }}
      search={false}
      tableLayout="fixed"
      toolBarRender={() => [
        <Button
          aria-label="新增动作"
          icon={<PlusOutlined />}
          key="create-action"
          onClick={onCreateAction}
          type="primary"
        >
          新增动作
        </Button>,
        <Button icon={<ReloadOutlined />} key="reload-actions" onClick={onReload}>
          刷新
        </Button>,
      ]}
    />
  );
}
