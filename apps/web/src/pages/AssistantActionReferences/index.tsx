import {
  AuditOutlined,
  DeleteOutlined,
  DeploymentUnitOutlined,
  EditOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import {
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  createAssistantActionReferenceConfig,
  deleteAssistantActionReferenceConfig,
  fetchAssistantActionReferenceConfigs,
  patchAssistantActionReferenceConfig,
  setAssistantActionReferenceConfigStatus,
  updateAssistantActionReferenceConfigRollout,
  type AssistantActionReferenceConfig,
} from '../../services/aiBrain';

type ActionReferenceFormValues = {
  action_key: string;
  aliases?: string;
  enabled: boolean;
  enterprise_id?: string;
  permissions?: string;
  prompt: string;
  roles?: string;
  sort_order: number;
  summary: string;
  template_version?: string;
  title: string;
  url: string;
};

type RolloutFormValues = {
  enterprise_id?: string;
  percentage?: number | string;
  template_version?: string;
};

const { Text } = Typography;

function splitList(value?: string) {
  return (value ?? '')
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinList(items: string[]) {
  return items.join(', ');
}

function tagList(items: string[]) {
  if (!items.length) {
    return <Text type="secondary">未配置</Text>;
  }
  return (
    <Space size={[4, 4]} wrap>
      {items.map((item) => (
        <Tag key={item}>{item}</Tag>
      ))}
    </Space>
  );
}

function rolloutPercentage(record: AssistantActionReferenceConfig) {
  const value = record.rollout_json?.percentage ?? record.rollout_json?.rollout_percentage;
  return typeof value === 'number' ? value : undefined;
}

function auditUrl(record: AssistantActionReferenceConfig) {
  const params = new URLSearchParams();
  params.set('subject_type', 'assistant_action_reference_config');
  params.set('subject_id', record.id);
  return `/governance/audit?${params.toString()}`;
}

function formValuesFromRecord(record: AssistantActionReferenceConfig): ActionReferenceFormValues {
  return {
    action_key: record.action_key,
    aliases: joinList(record.aliases),
    enabled: record.enabled,
    enterprise_id: record.enterprise_id ?? undefined,
    permissions: joinList(record.permissions),
    prompt: record.prompt,
    roles: joinList(record.roles),
    sort_order: record.sort_order,
    summary: record.summary,
    template_version: record.template_version ?? undefined,
    title: record.title,
    url: record.url,
  };
}

export default function AssistantActionReferencesPage() {
  const [configs, setConfigs] = useState<AssistantActionReferenceConfig[]>([]);
  const [editingConfig, setEditingConfig] = useState<AssistantActionReferenceConfig>();
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [rolloutTarget, setRolloutTarget] = useState<AssistantActionReferenceConfig>();
  const [configForm] = Form.useForm<ActionReferenceFormValues>();
  const [rolloutForm] = Form.useForm<RolloutFormValues>();

  const loadConfigs = useCallback(async () => {
    setLoading(true);
    try {
      setConfigs(await fetchAssistantActionReferenceConfigs());
    } catch (error) {
      message.error(error instanceof Error ? error.message : '@ 能力配置加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      void loadConfigs();
    });
  }, [loadConfigs]);

  const enabledCount = useMemo(
    () => configs.filter((item) => item.enabled).length,
    [configs],
  );

  const closeConfigModal = () => {
    setIsConfigModalOpen(false);
    setEditingConfig(undefined);
    configForm.resetFields();
  };

  const openCreateConfig = () => {
    setEditingConfig(undefined);
    configForm.resetFields();
    configForm.setFieldsValue({
      enabled: true,
      sort_order: (configs.at(-1)?.sort_order ?? 0) + 10,
      url: '/assistant',
    });
    setIsConfigModalOpen(true);
  };

  const openEditConfig = (record: AssistantActionReferenceConfig) => {
    setEditingConfig(record);
    configForm.setFieldsValue(formValuesFromRecord(record));
    setIsConfigModalOpen(true);
  };

  const submitConfig = async (values: ActionReferenceFormValues) => {
    try {
      const payload = {
        action_key: values.action_key.trim(),
        aliases: splitList(values.aliases),
        enabled: values.enabled,
        enterprise_id: values.enterprise_id?.trim() || null,
        metadata_json: editingConfig?.metadata_json ?? {},
        permissions: splitList(values.permissions),
        prompt: values.prompt.trim(),
        roles: splitList(values.roles),
        rollout_json: editingConfig?.rollout_json ?? {},
        sort_order: Number(values.sort_order ?? 0),
        summary: values.summary.trim(),
        template_version: values.template_version?.trim() || null,
        title: values.title.trim(),
        url: values.url.trim(),
      };
      const updated = editingConfig
        ? await patchAssistantActionReferenceConfig(editingConfig.id, payload)
        : await createAssistantActionReferenceConfig(payload);
      setConfigs((items) => {
        const exists = items.some((item) => item.id === updated.id);
        const nextItems = exists
          ? items.map((item) => (item.id === updated.id ? updated : item))
          : [...items, updated];
        return nextItems.sort((left, right) => left.sort_order - right.sort_order);
      });
      closeConfigModal();
      message.success(editingConfig ? '@ 能力已更新' : '@ 能力已创建');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '@ 能力保存失败');
    }
  };

  const toggleStatus = async (record: AssistantActionReferenceConfig) => {
    try {
      const updated = await setAssistantActionReferenceConfigStatus(record.id, !record.enabled);
      setConfigs((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      message.success(updated.enabled ? '@ 能力已启用' : '@ 能力已停用');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '@ 能力状态更新失败');
    }
  };

  const openRollout = (record: AssistantActionReferenceConfig) => {
    setRolloutTarget(record);
    rolloutForm.setFieldsValue({
      enterprise_id: record.enterprise_id ?? undefined,
      percentage: rolloutPercentage(record),
      template_version: record.template_version ?? undefined,
    });
  };

  const submitRollout = async (values: RolloutFormValues) => {
    if (!rolloutTarget) {
      return;
    }
    try {
      const updated = await updateAssistantActionReferenceConfigRollout(rolloutTarget.id, {
        enterprise_id: values.enterprise_id?.trim() || null,
        rollout_json: {
          ...(rolloutTarget.rollout_json ?? {}),
          percentage: Number(values.percentage ?? 100),
        },
        template_version: values.template_version?.trim() || null,
      });
      setConfigs((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setRolloutTarget(undefined);
      rolloutForm.resetFields();
      message.success('@ 能力灰度已更新');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '@ 能力灰度更新失败');
    }
  };

  const removeConfig = async (record: AssistantActionReferenceConfig) => {
    try {
      await deleteAssistantActionReferenceConfig(record.id);
      setConfigs((items) => items.filter((item) => item.id !== record.id));
      message.success('@ 能力已删除');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '@ 能力删除失败');
    }
  };

  return (
    <PageContainer
      title="AI助手 @ 能力配置"
      extra={[
        <Tag color="blue" key="total">{configs.length} 项</Tag>,
        <Tag color="green" key="enabled">{enabledCount} 项启用</Tag>,
        <Button icon={<PlusOutlined />} key="create" onClick={openCreateConfig} type="primary">
          新增能力
        </Button>,
      ]}
    >
      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', minWidth: 1480, width: '100%' }}>
          <thead>
            <tr>
              {['能力', '状态', '排序', '权限预览', '角色', '关键词', '企业', '模板版本', '灰度', '操作'].map((title) => (
                <th
                  key={title}
                  style={{ borderBottom: '1px solid #f0f0f0', padding: '12px 8px', textAlign: 'left' }}
                >
                  {title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody aria-busy={loading}>
            {configs.map((record) => {
              const percentage = rolloutPercentage(record);
              return (
                <tr key={record.id}>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    <Space orientation="vertical" size={2}>
                      <Text strong>{record.title}</Text>
                      <Text type="secondary">{record.action_key}</Text>
                      <Text type="secondary">{record.summary}</Text>
                    </Space>
                  </td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    <Tag color={record.enabled ? 'green' : 'default'}>
                      {record.enabled ? '启用' : '停用'}
                    </Tag>
                  </td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    {record.sort_order}
                  </td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    {tagList(record.permissions)}
                  </td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    {tagList(record.roles)}
                  </td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    {tagList(record.aliases.slice(0, 8))}
                  </td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    {record.enterprise_id || <Text type="secondary">全局</Text>}
                  </td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    {record.template_version || <Text type="secondary">默认</Text>}
                  </td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    {percentage === undefined ? '-' : `${percentage}%`}
                  </td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    <Space size={8} wrap>
                      <Button
                        aria-label={`编辑 ${record.title}`}
                        icon={<EditOutlined />}
                        onClick={() => openEditConfig(record)}
                        size="small"
                      >
                        编辑
                      </Button>
                      <Button
                        aria-label={`${record.enabled ? '停用' : '启用'} ${record.title}`}
                        icon={record.enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                        onClick={() => void toggleStatus(record)}
                        size="small"
                      >
                        {record.enabled ? '停用' : '启用'}
                      </Button>
                      <Button
                        aria-label={`配置灰度 ${record.title}`}
                        icon={<DeploymentUnitOutlined />}
                        onClick={() => openRollout(record)}
                        size="small"
                      >
                        灰度
                      </Button>
                      <Button href={auditUrl(record)} icon={<AuditOutlined />} size="small">
                        审计
                      </Button>
                      <Popconfirm
                        onConfirm={() => void removeConfig(record)}
                        title={`删除 ${record.title}`}
                      >
                        <Button danger icon={<DeleteOutlined />} size="small">
                          删除
                        </Button>
                      </Popconfirm>
                    </Space>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Modal
        destroyOnHidden
        onCancel={closeConfigModal}
        onOk={() => configForm.submit()}
        open={isConfigModalOpen}
        title={editingConfig ? `编辑 @ 能力 · ${editingConfig.title}` : '新增 @ 能力'}
        width={760}
      >
        <Form form={configForm} layout="vertical" onFinish={(values) => void submitConfig(values)}>
          <Space align="start" size={16}>
            <Form.Item
              label="能力标题"
              name="title"
              rules={[{ required: true, message: '请输入能力标题' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="动作 Key"
              name="action_key"
              rules={[{ required: true, message: '请输入动作 Key' }]}
            >
              <Input disabled={Boolean(editingConfig)} />
            </Form.Item>
            <Form.Item label="启用" name="enabled" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
          <Form.Item
            label="摘要"
            name="summary"
            rules={[{ required: true, message: '请输入摘要' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Prompt"
            name="prompt"
            rules={[{ required: true, message: '请输入 Prompt' }]}
          >
            <Input.TextArea rows={3} />
          </Form.Item>
          <Space align="start" size={16}>
            <Form.Item label="排序" name="sort_order" rules={[{ required: true }]}>
              <InputNumber min={0} />
            </Form.Item>
            <Form.Item label="企业 ID" name="enterprise_id">
              <Input placeholder="全局" />
            </Form.Item>
            <Form.Item label="模板版本" name="template_version">
              <Input placeholder="默认" />
            </Form.Item>
          </Space>
          <Form.Item
            label="落地地址"
            name="url"
            rules={[{ required: true, message: '请输入落地地址' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="关键词" name="aliases">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="角色" name="roles">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="权限" name="permissions">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        destroyOnHidden
        onCancel={() => {
          setRolloutTarget(undefined);
          rolloutForm.resetFields();
        }}
        onOk={() => rolloutForm.submit()}
        open={Boolean(rolloutTarget)}
        title={`@ 能力灰度 · ${rolloutTarget?.title ?? ''}`}
      >
        <Form form={rolloutForm} layout="vertical" onFinish={(values) => void submitRollout(values)}>
          <Form.Item label="企业 ID" name="enterprise_id">
            <Input placeholder="全局" />
          </Form.Item>
          <Form.Item label="模板版本" name="template_version">
            <Input placeholder="默认" />
          </Form.Item>
          <Form.Item label="灰度比例" name="percentage">
            <Input max={100} min={0} type="number" />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
}
