import { Form, Input, InputNumber, Select, Space } from 'antd';

import { ScheduledJobFormSection } from './ScheduledJobFormSection';

type ScheduleTypeOption = {
  label: string;
  value: string;
};

export function ScheduledJobScheduleConfigSection({
  scheduleTypeOptions,
}: {
  scheduleTypeOptions: ScheduleTypeOption[];
}) {
  return (
    <ScheduledJobFormSection label="调度配置" marker="调度">
      <Space align="start" wrap>
        <Form.Item label="调度方式" name="schedule_type">
          <Select options={scheduleTypeOptions} style={{ minWidth: 140 }} />
        </Form.Item>
        <Form.Item label="Cron 表达式" name="cron_expression">
          <Input placeholder="例如：0 9 * * MON" style={{ width: 220 }} />
        </Form.Item>
        <Form.Item label="间隔秒数" name="interval_seconds">
          <InputNumber min={1} placeholder="例如：3600" style={{ width: 160 }} />
        </Form.Item>
      </Space>
    </ScheduledJobFormSection>
  );
}
