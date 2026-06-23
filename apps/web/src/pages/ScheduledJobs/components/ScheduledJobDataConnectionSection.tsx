import { Col, Form, Row, Select } from 'antd';
import type { FormItemProps } from 'antd';

import type { PluginConnectionRecord } from '../../../services/aiBrain';
import { ScheduledJobFormSection } from './ScheduledJobFormSection';

type FormRule = NonNullable<FormItemProps['rules']>[number];

export function ScheduledJobDataConnectionSection({
  connectionEnvironmentOptions,
  filteredPluginConnections,
  onConnectionEnvironmentChange,
  onPluginConnectionChange,
  requiredForPluginResource,
  usesNativeScan,
}: {
  connectionEnvironmentOptions: Array<{ label: string; value: string }>;
  filteredPluginConnections: PluginConnectionRecord[];
  onConnectionEnvironmentChange: () => void;
  onPluginConnectionChange: (value: unknown) => void;
  requiredForPluginResource: (message: string) => FormRule;
  usesNativeScan: boolean;
}) {
  return (
    <ScheduledJobFormSection label="数据连接配置" marker="输入">
      <Row gutter={12}>
        <Col span={8}>
          <Form.Item label="连接环境" name="connection_environment">
            <Select
              allowClear
              options={connectionEnvironmentOptions}
              placeholder="筛选数据连接环境"
              onChange={onConnectionEnvironmentChange}
            />
          </Form.Item>
        </Col>
        <Col span={16}>
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
                label: `${connection.name} (${connection.environment ?? 'default'})`,
                value: connection.id,
              }))}
            />
          </Form.Item>
        </Col>
      </Row>
    </ScheduledJobFormSection>
  );
}
