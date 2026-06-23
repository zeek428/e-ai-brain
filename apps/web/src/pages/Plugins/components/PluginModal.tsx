import { ApiOutlined } from '@ant-design/icons';
import type { FormInstance } from 'antd';
import { Form, Input, Modal, Select } from 'antd';

import { pluginCategoryOptions } from './pluginCatalogHelpers';

export type PluginFormValues = {
  category: string;
  code: string;
  description?: string;
  name: string;
  protocol: string;
  risk_level: string;
  status: string;
};

type PluginModalProps = {
  form: FormInstance<PluginFormValues>;
  isEditing: boolean;
  onCancel: () => void;
  onSubmit: () => void | Promise<void>;
  open: boolean;
};

export function PluginModal({
  form,
  isEditing,
  onCancel,
  onSubmit,
  open,
}: PluginModalProps) {
  return (
    <Modal
      onCancel={onCancel}
      onOk={() => void onSubmit()}
      open={open}
      title={isEditing ? '编辑插件' : '新增插件'}
    >
      <Form
        form={form}
        initialValues={{ category: 'general', protocol: 'http', risk_level: 'medium', status: 'active' }}
        layout="vertical"
      >
        <Form.Item label="名称" name="name" rules={[{ required: true }]}>
          <Input prefix={<ApiOutlined />} />
        </Form.Item>
        <Form.Item label="编码" name="code" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item label="协议" name="protocol">
          <Select
            options={[
              { label: 'HTTP', value: 'http' },
              { label: 'MCP HTTP', value: 'mcp_http' },
              { label: 'MCP Stdio', value: 'mcp_stdio' },
              { label: 'Runner Polling', value: 'runner_polling' },
              { label: 'Runner WebSocket', value: 'runner_websocket' },
            ]}
          />
        </Form.Item>
        <Form.Item label="分类" name="category" rules={[{ required: true, message: '请选择插件分类' }]}>
          <Select options={pluginCategoryOptions} />
        </Form.Item>
        <Form.Item label="风险等级" name="risk_level">
          <Select
            options={[
              { label: 'low', value: 'low' },
              { label: 'medium', value: 'medium' },
              { label: 'high', value: 'high' },
            ]}
          />
        </Form.Item>
        <Form.Item label="状态" name="status">
          <Select
            options={[
              { label: 'active', value: 'active' },
              { label: 'draft', value: 'draft' },
              { label: 'disabled', value: 'disabled' },
            ]}
          />
        </Form.Item>
        <Form.Item label="说明" name="description">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
