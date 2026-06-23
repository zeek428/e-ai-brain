import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import { Button, Space, Tag, Typography } from 'antd';

import type { PluginRecord } from '../../../services/aiBrain';
import {
  OFFICIAL_PLUGIN_LABEL,
  pluginCategoryLabel,
  pluginVersionStatusTag,
} from './pluginCatalogHelpers';

type PluginTableProps = {
  loading: boolean;
  onCopyOfficialPlugin: (plugin: PluginRecord) => void;
  onCreatePlugin: () => void;
  onDeletePlugin: (plugin: PluginRecord) => void;
  onEditPlugin: (plugin: PluginRecord) => void;
  onReload: () => void;
  plugins: PluginRecord[];
};

export function PluginTable({
  loading,
  onCopyOfficialPlugin,
  onCreatePlugin,
  onDeletePlugin,
  onEditPlugin,
  onReload,
  plugins,
}: PluginTableProps) {
  return (
    <ProTable<PluginRecord>
      cardBordered
      className="management-list-table"
      columns={[
        {
          dataIndex: 'name',
          title: '名称',
          ellipsis: true,
          width: 240,
          render: (_, row) => (
            <Space wrap={false}>
              <Typography.Text ellipsis style={{ maxWidth: 150 }}>
                {row.name}
              </Typography.Text>
              {row.is_system ? <Tag color="blue">{OFFICIAL_PLUGIN_LABEL}</Tag> : null}
            </Space>
          ),
        },
        { dataIndex: 'code', title: '编码', ellipsis: true, width: 200 },
        { dataIndex: 'protocol', title: '协议', width: 120 },
        {
          dataIndex: 'template_version',
          title: '模板版本',
          width: 120,
          render: (_, row) => pluginVersionStatusTag(row),
        },
        {
          dataIndex: 'category',
          title: '分类',
          width: 150,
          render: (value) => pluginCategoryLabel(value),
        },
        { dataIndex: 'risk_level', title: '风险', width: 100 },
        {
          dataIndex: 'status',
          title: '状态',
          width: 110,
          render: (value) => <Tag color={value === 'active' ? 'green' : 'default'}>{String(value)}</Tag>,
        },
        {
          fixed: 'right',
          key: 'actions',
          title: '操作',
          valueType: 'option',
          width: 164,
          render: (_, row) => {
            if (row.is_system) {
              return (
                <Space className="management-row-actions" size={0}>
                  <Button
                    aria-label={`复制官方插件 ${row.name}`}
                    icon={<PlusOutlined />}
                    onClick={() => onCopyOfficialPlugin(row)}
                    type="link"
                  >
                    复制
                  </Button>
                </Space>
              );
            }
            return (
              <Space className="management-row-actions" size={0}>
                <Button
                  aria-label={`编辑插件 ${row.name}`}
                  icon={<EditOutlined />}
                  onClick={() => onEditPlugin(row)}
                  type="link"
                >
                  编辑
                </Button>
                <Button
                  aria-label={`删除插件 ${row.name}`}
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => onDeletePlugin(row)}
                  type="link"
                >
                  删除
                </Button>
              </Space>
            );
          },
        },
      ]}
      dataSource={plugins}
      dateFormatter="string"
      headerTitle="插件"
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
      scroll={{ x: 1252 }}
      search={false}
      tableLayout="fixed"
      toolBarRender={() => [
        <Button
          aria-label="新增插件"
          icon={<PlusOutlined />}
          key="create-plugin"
          onClick={onCreatePlugin}
          type="primary"
        >
          新增插件
        </Button>,
        <Button icon={<ReloadOutlined />} key="reload-plugins" onClick={onReload}>
          刷新
        </Button>,
      ]}
    />
  );
}
