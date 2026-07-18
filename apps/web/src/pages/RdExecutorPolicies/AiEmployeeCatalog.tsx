import { Button, Form, Input, Modal, Space, Table, Tag, message } from 'antd';
import { useState } from 'react';

import {
  createRdAiEmployee,
  type CreateRdAiEmployeePayload,
  type RdAiEmployee,
} from '../../services/rdCollaborationClient';
import { formatMutationError } from '../../utils/managementCrud';

type EmployeeFormValues = {
  capabilityTags: string;
  code: string;
  name: string;
};

type Props = {
  employees: RdAiEmployee[];
  onCreated: (employee: RdAiEmployee) => void;
};

function tagsFromText(value: string) {
  return value
    .split(/[，,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function AiEmployeeCatalog({ employees, onCreated }: Props) {
  const [form] = Form.useForm<EmployeeFormValues>();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleCreate = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const payload: CreateRdAiEmployeePayload = {
        capability_tags: tagsFromText(values.capabilityTags),
        code: values.code.trim(),
        name: values.name.trim(),
        persona_json: { source: 'rd_delivery_policy_page' },
        work_style_json: { collaboration: 'policy_governed' },
      };
      const employee = await createRdAiEmployee(payload);
      onCreated(employee);
      message.success('已新增 AI 数字员工，可在岗位配置中选用');
      setOpen(false);
      form.resetFields();
    } catch (error) {
      message.error(formatMutationError(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <span>AI 数字员工目录</span>
        <Button type="primary" onClick={() => setOpen(true)}>新增 AI 数字员工</Button>
      </Space>
      <Table
        dataSource={employees}
        pagination={false}
        rowKey="id"
        size="small"
        columns={[
          { dataIndex: 'name', title: '员工' },
          { dataIndex: 'code', title: '编码' },
          {
            dataIndex: 'capability_tags',
            title: '能力标签',
            render: (tags: string[]) => tags.map((tag) => <Tag key={tag}>{tag}</Tag>),
          },
          {
            dataIndex: 'status',
            title: '状态',
            render: (status: string) => <Tag color={status === 'active' ? 'green' : 'default'}>{status}</Tag>,
          },
        ]}
      />
      <Modal
        destroyOnHidden
        open={open}
        title="新增 AI 数字员工"
        confirmLoading={saving}
        onCancel={() => setOpen(false)}
        onOk={handleCreate}
      >
        <Form form={form} layout="vertical">
          <Form.Item label="员工名称" name="name" rules={[{ required: true, whitespace: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="员工编码" name="code" rules={[{ required: true, whitespace: true }]}>
            <Input placeholder="例如 ai_developer" />
          </Form.Item>
          <Form.Item label="能力标签" name="capabilityTags" rules={[{ required: true, whitespace: true }]}>
            <Input placeholder="开发、代码评审（以逗号分隔）" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
