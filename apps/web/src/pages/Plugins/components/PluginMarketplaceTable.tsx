import { PlusOutlined } from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import { Button, Space, Tag, Typography } from 'antd';

import type { PluginMarketplaceItem } from '../../../services/aiBrain';
import {
  OFFICIAL_PLUGIN_LABEL,
  pluginCategoryLabel,
  pluginVersionStatusTag,
} from './pluginCatalogHelpers';
import {
  MarketplaceConnectionSchemaDetail,
  MarketplaceConnectionSchemaSummary,
} from './PluginDiagnostics';

type PluginMarketplaceTableProps = {
  items: PluginMarketplaceItem[];
  loading: boolean;
  onCreateAction: (item: PluginMarketplaceItem) => void;
  onCreateConnection: (pluginId?: string | null) => void;
  onReload: () => void;
};

export function PluginMarketplaceTable({
  items,
  loading,
  onCreateAction,
  onCreateConnection,
  onReload,
}: PluginMarketplaceTableProps) {
  return (
    <ProTable<PluginMarketplaceItem>
      cardBordered
      className="management-list-table"
      columns={[
        {
          dataIndex: 'name',
          title: '插件',
          ellipsis: true,
          width: 220,
          render: (_, row) => (
            <Space orientation="vertical" size={2}>
              <Space wrap={false}>
                <Typography.Text ellipsis style={{ maxWidth: 140 }}>
                  {row.name}
                </Typography.Text>
                <Tag color="blue">{OFFICIAL_PLUGIN_LABEL}</Tag>
              </Space>
              <Typography.Text type="secondary">{row.publisher ?? 'AI Brain 官方'}</Typography.Text>
            </Space>
          ),
        },
        {
          dataIndex: 'category',
          title: '分类',
          width: 150,
          render: (value) => pluginCategoryLabel(value),
        },
        { dataIndex: 'protocol', title: '协议', width: 110 },
        {
          dataIndex: 'installed',
          title: '状态',
          width: 120,
          render: (_, row) => (
            <Tag color={row.installed ? 'green' : 'default'}>
              {row.installed ? '已内置' : '未内置'}
            </Tag>
          ),
        },
        {
          dataIndex: 'template_version',
          title: '模板版本',
          width: 120,
          render: (_, row) => pluginVersionStatusTag(row),
        },
        {
          dataIndex: 'summary',
          title: '能力说明',
          ellipsis: true,
          width: 300,
          render: (value) => value || '-',
        },
        {
          dataIndex: 'recommended_scenarios',
          title: '推荐场景',
          width: 260,
          render: (value) => (
            <Space wrap size={4}>
              {(Array.isArray(value) ? value : []).slice(0, 3).map((item) => (
                <Tag key={String(item)}>{String(item)}</Tag>
              ))}
            </Space>
          ),
        },
        {
          dataIndex: 'action_templates',
          title: '动作模板',
          width: 230,
          render: (value) => (
            <Space wrap size={4}>
              {(Array.isArray(value) ? value : []).slice(0, 2).map((item) => (
                <Tag color="purple" key={String(item)}>{String(item)}</Tag>
              ))}
            </Space>
          ),
        },
        {
          dataIndex: 'connection_schema',
          title: '连接表单字段',
          width: 280,
          render: (_, row) => <MarketplaceConnectionSchemaSummary item={row} />,
        },
        {
          dataIndex: 'connection_count',
          key: 'runtime',
          title: '已配置',
          width: 140,
          render: (_, row) => (
            <Space orientation="vertical" size={2}>
              <Typography.Text>连接 {row.connection_count}</Typography.Text>
              <Typography.Text>动作 {row.action_count}</Typography.Text>
            </Space>
          ),
        },
        {
          dataIndex: 'plugin_id',
          fixed: 'right',
          key: 'actions',
          title: '操作',
          valueType: 'option',
          width: 170,
          render: (_, row) => (
            <Space orientation="vertical" size={2}>
              <Button
                aria-label={`配置市场插件 ${row.name}`}
                disabled={!row.plugin_id}
                icon={<PlusOutlined />}
                onClick={() => onCreateConnection(row.plugin_id)}
                type="link"
              >
                配置连接
              </Button>
              <Button
                aria-label={`从市场插件 ${row.name} 创建动作`}
                disabled={!row.plugin_id}
                icon={<PlusOutlined />}
                onClick={() => onCreateAction(row)}
                type="link"
              >
                创建动作
              </Button>
            </Space>
          ),
        },
      ]}
      dataSource={items}
      dateFormatter="string"
      expandable={{
        expandedRowRender: (record) => (
          <Space orientation="vertical" size={8} style={{ width: '100%' }}>
            <Typography.Text strong>连接表单 schema</Typography.Text>
            <MarketplaceConnectionSchemaDetail item={record} />
          </Space>
        ),
      }}
      headerTitle="官方插件市场"
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
      scroll={{ x: 1720 }}
      search={false}
      tableLayout="fixed"
    />
  );
}
