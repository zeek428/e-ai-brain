import { Form, Select } from 'antd';
import type { FormItemProps } from 'antd';

import type { PluginConnectionRecord } from '../../../services/aiBrain';
import { ScheduledJobFormSection } from './ScheduledJobFormSection';

type FormRule = NonNullable<FormItemProps['rules']>[number];

export function ScheduledJobDataConnectionSection({
  filteredPluginConnections,
  onPluginConnectionChange,
  requiredForPluginResource,
  usesNativeScan,
}: {
  filteredPluginConnections: PluginConnectionRecord[];
  onPluginConnectionChange: (value: unknown) => void;
  requiredForPluginResource: (message: string) => FormRule;
  usesNativeScan: boolean;
}) {
  return (
    <ScheduledJobFormSection label="数据连接配置" marker="输入">
      <Form.Item
        label="数据连接"
        name="plugin_connection_ids"
        rules={[requiredForPluginResource('请选择数据连接')]}
        extra={usesNativeScan ? '本地完整扫描直接 clone 产品代码仓库，不需要外部数据连接' : '可选择多个连接，运行时按配置顺序作为数据来源'}
      >
        <Select
          allowClear
          disabled={usesNativeScan}
          mode="multiple"
          maxTagCount={2}
          onChange={onPluginConnectionChange}
          optionFilterProp="label"
          placeholder="请选择取数连接"
          showSearch
          options={filteredPluginConnections.map((connection) => ({
            label: connection.name,
            value: connection.id,
          }))}
        />
      </Form.Item>
    </ScheduledJobFormSection>
  );
}
