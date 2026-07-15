import { Col, Form, Input, Row, Select, Switch } from 'antd';
import type { FormItemProps } from 'antd';

import { ScheduledJobFormSection as FormSection } from './ScheduledJobFormSection';

type FormRule = NonNullable<FormItemProps['rules']>[number];

type SelectOption = {
  label: string;
  value: string;
};

type ScheduledJobBasicInfoSectionProps = {
  jobTypeOptions: SelectOption[];
  onJobTypeChange: (jobType?: string) => void;
  onProductChange: () => void;
  productOptions: SelectOption[];
  productRequiredRule: FormRule;
};

export function ScheduledJobBasicInfoSection({
  jobTypeOptions,
  onJobTypeChange,
  onProductChange,
  productOptions,
  productRequiredRule,
}: ScheduledJobBasicInfoSectionProps) {
  const resultActions = Form.useWatch('result_actions');
  const requirementResultActionProductRule: FormRule = {
    validator(_: unknown, value: unknown) {
      const createsRequirements = Array.isArray(resultActions) && resultActions.some(
        (action) => action && typeof action === 'object'
          && (action as { type?: unknown }).type === 'create_requirements',
      );
      if (createsRequirements && !(typeof value === 'string' && value.trim())) {
        return Promise.reject(new Error('创建需求结果动作需要选择产品'));
      }
      return Promise.resolve();
    },
  };

  return (
    <FormSection label="基础信息" marker="基本">
      <Row gutter={12}>
        <Col span={14}>
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Col>
        <Col span={10}>
          <Form.Item label="作业类型" name="job_type" rules={[{ required: true }]}>
            <Select options={jobTypeOptions} onChange={onJobTypeChange} />
          </Form.Item>
        </Col>
        <Col span={18}>
          <Form.Item
            label="所属产品"
            name="product_id"
            rules={[productRequiredRule, requirementResultActionProductRule]}
          >
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="请选择产品"
              onChange={onProductChange}
              options={productOptions}
            />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item label="启用" name="enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Col>
      </Row>
    </FormSection>
  );
}
