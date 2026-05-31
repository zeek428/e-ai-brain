import { DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Switch, message } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ModelGatewayConfigRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createModelGatewayConfig,
  deleteModelGatewayConfig,
  fetchModelGatewayConfigs,
  updateModelGatewayConfig,
} from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';

type ModelGatewayFormValues = {
  api_key?: string;
  base_url: string;
  default_chat_model: string;
  default_embedding_model: string;
  is_default: boolean;
  max_retries: number;
  name: string;
  provider: string;
  status: ModelGatewayConfigRecord['status'];
  timeout_seconds: number;
};

export default function ModelGatewayPage() {
  const [form] = Form.useForm<ModelGatewayFormValues>();
  const [editingConfig, setEditingConfig] = useState<ModelGatewayConfigRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(fetchModelGatewayConfigs);

  const openCreateModal = () => {
    setEditingConfig(null);
    form.resetFields();
    form.setFieldsValue({
      is_default: dataSource.length === 0,
      max_retries: 1,
      provider: 'openai_compatible',
      status: 'active',
      timeout_seconds: 60,
    });
    setIsModalOpen(true);
  };

  const openEditModal = useCallback((row: ModelGatewayConfigRecord) => {
    setEditingConfig(row);
    form.setFieldsValue({
      base_url: row.baseUrl,
      default_chat_model: row.defaultChatModel,
      default_embedding_model: row.defaultEmbeddingModel,
      is_default: row.isDefault,
      max_retries: row.maxRetries,
      name: row.name,
      provider: row.provider,
      status: row.status,
      timeout_seconds: row.timeoutSeconds,
    });
    setIsModalOpen(true);
  }, [form]);

  const handleSave = async () => {
    const values = await form.validateFields();
    const apiKey = trimText(values.api_key);
    const payload = {
      base_url: values.base_url.trim(),
      default_chat_model: values.default_chat_model.trim(),
      default_embedding_model: values.default_embedding_model.trim(),
      is_default: values.is_default,
      max_retries: Number(values.max_retries ?? 1),
      name: values.name.trim(),
      provider: values.provider.trim(),
      status: values.status,
      timeout_seconds: Number(values.timeout_seconds ?? 60),
      ...(apiKey ? { api_key: apiKey } : {}),
    };

    setIsSaving(true);
    try {
      if (editingConfig) {
        await updateModelGatewayConfig(editingConfig.id, payload);
        message.success('模型网关配置已更新');
      } else {
        await createModelGatewayConfig(payload);
        message.success('模型网关配置已创建');
      }
      setIsModalOpen(false);
      void reload();
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = useCallback(async (row: ModelGatewayConfigRecord) => {
    try {
      await deleteModelGatewayConfig(row.id);
      message.success('模型网关配置已删除');
      await reload();
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [reload]);

  const columns = useMemo<ProColumns<ModelGatewayConfigRecord>[]>(
    () => [
      {
        dataIndex: 'name',
        title: '配置名称',
      },
      {
        dataIndex: 'provider',
        title: 'Provider',
      },
      {
        dataIndex: 'baseUrl',
        title: 'Base URL',
      },
      {
        dataIndex: 'defaultChatModel',
        title: 'Chat 模型',
      },
      {
        dataIndex: 'defaultEmbeddingModel',
        title: 'Embedding 模型',
      },
      {
        dataIndex: 'keyStatus',
        title: 'API Key',
        render: (_, row) => (
          <StatusTag color={row.apiKeyConfigured ? 'green' : 'default'} label={row.keyStatus} />
        ),
      },
      {
        dataIndex: 'isDefault',
        title: '默认',
        render: (_, row) =>
          row.isDefault ? <StatusTag color="blue" label="默认" /> : <StatusTag color="default" label="否" />,
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) =>
          row.status === 'active' ? (
            <StatusTag color="green" label="启用" />
          ) : (
            <StatusTag color="default" label="停用" />
          ),
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button icon={<EditOutlined />} onClick={() => openEditModal(row)} type="link">
              编辑
            </Button>
            <Popconfirm
              okText="删除"
              onConfirm={() => handleDelete(row)}
              title={`删除模型网关配置 ${row.name}？`}
            >
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [handleDelete, openEditModal],
  );

  return (
    <>
      <ManagementListPage<ModelGatewayConfigRecord>
        breadcrumbGroup="系统管理"
        columns={columns}
        dataSource={dataSource}
        filters={[
          { label: '配置名称', name: 'name', type: 'text' },
          { label: 'Provider', name: 'provider', type: 'text' },
          {
            label: '状态',
            name: 'status',
            options: [
              { label: '启用', value: 'active' },
              { label: '停用', value: 'inactive' },
            ],
            type: 'select',
          },
          {
            label: '默认',
            name: 'isDefault',
            options: [
              { label: '默认', value: 'true' },
              { label: '否', value: 'false' },
            ],
            type: 'select',
          },
        ]}
        loading={status === 'loading'}
        notice={formatRemoteRowsError(error)}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="新增配置"
        rowKey="id"
        tableTitle="模型网关配置"
        title="模型网关"
      />
      <Modal
        cancelText="取消"
        confirmLoading={isSaving}
        destroyOnHidden
        okText="保存"
        onCancel={() => setIsModalOpen(false)}
        onOk={() => void handleSave()}
        open={isModalOpen}
        title={editingConfig ? '编辑模型网关配置' : '新增模型网关配置'}
      >
        <Form<ModelGatewayFormValues> form={form} layout="vertical">
          <Form.Item label="配置名称" name="name" rules={[{ required: true, message: '请输入配置名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Provider" name="provider" rules={[{ required: true, message: '请输入 Provider' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Base URL" name="base_url" rules={[{ required: true, message: '请输入 Base URL' }]}>
            <Input placeholder="https://api.example.com/v1" />
          </Form.Item>
          <Form.Item
            extra={editingConfig ? '留空表示保留当前服务端密钥。' : undefined}
            label="API Key"
            name="api_key"
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            label="默认 Chat 模型"
            name="default_chat_model"
            rules={[{ required: true, message: '请输入默认 Chat 模型' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="默认 Embedding 模型"
            name="default_embedding_model"
            rules={[{ required: true, message: '请输入默认 Embedding 模型' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="超时秒数" name="timeout_seconds" rules={[{ required: true, message: '请输入超时秒数' }]}>
            <InputNumber min={1} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="最大重试" name="max_retries" rules={[{ required: true, message: '请输入最大重试次数' }]}>
            <InputNumber min={0} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
            <Select
              options={[
                { label: '启用', value: 'active' },
                { label: '停用', value: 'inactive' },
              ]}
            />
          </Form.Item>
          <Form.Item label="默认配置" name="is_default" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
