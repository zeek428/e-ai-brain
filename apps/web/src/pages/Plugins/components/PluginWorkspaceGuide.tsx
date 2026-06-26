import type { ColumnsType } from 'antd/es/table';
import { Alert, Button, Space, Tag, Typography } from 'antd';
import { Fragment, useEffect, useMemo, useState } from 'react';

import {
  fetchPluginSystemVariables,
  type PluginSystemVariableRecord,
} from '../../../services/aiBrain';
import { SystemVariableModal } from './PluginUtilityModals';
import { SYSTEM_VARIABLE_OPTIONS } from './pluginSystemVariableOptions';

const systemVariableDescriptionByExpression = new Map(
  SYSTEM_VARIABLE_OPTIONS.map((option) => [option.value, option.description]),
);

const genericIntegrationChainSteps = [
  { color: 'blue', label: '插件', text: '定义三方系统能力与协议' },
  { color: 'cyan', label: '连接', text: '维护环境、Endpoint、认证和公共参数' },
  { color: 'purple', label: '动作', text: '定义请求、变量和结果映射' },
  { color: 'green', label: '定时作业', text: '编排取数、AI 处理和结果写入' },
];

const systemVariablePreviewColumns: ColumnsType<PluginSystemVariableRecord> = [
  {
    dataIndex: 'label',
    key: 'label',
    title: '变量',
    width: 180,
    render: (value: string, record) => (
      <Space orientation="vertical" size={0}>
        <Typography.Text strong>{value}</Typography.Text>
        {record.description ? (
          <Typography.Text type="secondary">{record.description}</Typography.Text>
        ) : null}
      </Space>
    ),
  },
  {
    dataIndex: 'expression',
    key: 'expression',
    title: '表达式',
    width: 220,
    render: (value: string) => (
      <Typography.Text code copyable={{ text: value }}>
        {value}
      </Typography.Text>
    ),
  },
  {
    dataIndex: 'value',
    key: 'value',
    title: '当前解析值',
    width: 260,
    render: (value: string) => (
      <Typography.Text code copyable={value !== '加载后显示' ? { text: value } : false}>
        {value}
      </Typography.Text>
    ),
  },
];

function fallbackSystemVariableItems(): PluginSystemVariableRecord[] {
  return SYSTEM_VARIABLE_OPTIONS.map((item) => ({
    description: item.description,
    expression: item.value,
    label: item.label,
    value: '加载后显示',
  }));
}

export function PluginWorkspaceGuide() {
  const [systemVariables, setSystemVariables] = useState<PluginSystemVariableRecord[]>([]);
  const [systemVariableTimezone, setSystemVariableTimezone] = useState('Asia/Shanghai');
  const [systemVariableModalOpen, setSystemVariableModalOpen] = useState(false);

  useEffect(() => {
    fetchPluginSystemVariables('Asia/Shanghai')
      .then((result) => {
        setSystemVariables(result.items);
        setSystemVariableTimezone(result.timezone || 'Asia/Shanghai');
      })
      .catch(() => {
        setSystemVariables([]);
        setSystemVariableTimezone('Asia/Shanghai');
      });
  }, []);

  const systemVariablePreviewItems = useMemo<PluginSystemVariableRecord[]>(() => {
    const items = systemVariables.length > 0 ? systemVariables : fallbackSystemVariableItems();
    return items.map((item) => ({
      ...item,
      description: item.description ?? systemVariableDescriptionByExpression.get(item.expression),
    }));
  }, [systemVariables]);

  const compactSystemVariablePreviewItems = useMemo(() => {
    const preferredExpressions = ['{{current_date}}', '{{current_date-7}}', '{{last_full_week.start}}'];
    const itemByExpression = new Map(systemVariablePreviewItems.map((item) => [item.expression, item]));
    const preferredItems = preferredExpressions
      .map((expression) => itemByExpression.get(expression))
      .filter((item): item is PluginSystemVariableRecord => Boolean(item));
    return preferredItems.length > 0 ? preferredItems : systemVariablePreviewItems.slice(0, 3);
  }, [systemVariablePreviewItems]);

  return (
    <Space orientation="vertical" size={12} style={{ width: '100%', marginBottom: 16 }}>
      <Alert
        title={(
          <Space wrap>
            <Typography.Text strong>系统变量预览</Typography.Text>
            <Tag color="blue">Timezone: {systemVariableTimezone}</Tag>
          </Space>
        )}
        description={(
          <Space orientation="vertical" size={10} style={{ display: 'flex', width: '100%' }}>
            <Space wrap size={[8, 8]}>
              <Typography.Text type="secondary">常用变量</Typography.Text>
              {compactSystemVariablePreviewItems.map((item) => (
                <Tag key={item.expression}>
                  {item.label}：{item.expression} = {item.value}
                </Tag>
              ))}
              <Button onClick={() => setSystemVariableModalOpen(true)} size="small" type="link">
                查看全部变量
              </Button>
            </Space>
            <Typography.Text type="secondary">
              可复制表达式到连接 Params、Headers 或动作参数值，支持类似 {'{{current_date-7}}'} 的天数偏移。
            </Typography.Text>
          </Space>
        )}
        showIcon
        type="info"
      />
      <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12 }}>
        <Typography.Text strong>通用调用链路</Typography.Text>
        <Space orientation="vertical" size={8} style={{ display: 'flex', marginTop: 10 }}>
          <Space wrap>
            {genericIntegrationChainSteps.map((step, index) => (
              <Fragment key={step.label}>
                {index > 0 ? <Typography.Text type="secondary">→</Typography.Text> : null}
                <Tag color={step.color}>
                  {step.label}：{step.text}
                </Tag>
              </Fragment>
            ))}
          </Space>
          <Typography.Text type="secondary">
            适用于 MaxCompute、GitHub、GitLab、邮箱和自定义 HTTP/MCP 集成场景。
          </Typography.Text>
        </Space>
      </div>
      <SystemVariableModal
        columns={systemVariablePreviewColumns}
        items={systemVariablePreviewItems}
        onClose={() => setSystemVariableModalOpen(false)}
        open={systemVariableModalOpen}
        timezone={systemVariableTimezone}
      />
    </Space>
  );
}
