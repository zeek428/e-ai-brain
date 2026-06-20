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
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ColumnsType } from 'antd/es/table';

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
  const [batchAction, setBatchAction] = useState<'disable' | 'enable'>();
  const [configs, setConfigs] = useState<AssistantActionReferenceConfig[]>([]);
  const [configSubmitting, setConfigSubmitting] = useState(false);
  const [deletingConfigId, setDeletingConfigId] = useState<string>();
  const [editingConfig, setEditingConfig] = useState<AssistantActionReferenceConfig>();
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [mutatingConfigIds, setMutatingConfigIds] = useState<Set<string>>(() => new Set());
  const [rolloutTarget, setRolloutTarget] = useState<AssistantActionReferenceConfig>();
  const [rolloutSubmitting, setRolloutSubmitting] = useState(false);
  const [roleFilter, setRoleFilter] = useState<string>();
  const [searchText, setSearchText] = useState('');
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<'disabled' | 'enabled'>();
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
  const roleOptions = useMemo(
    () => Array.from(new Set(configs.flatMap((item) => item.roles))).sort(),
    [configs],
  );
  const filteredConfigs = useMemo(() => {
    const normalizedSearch = searchText.trim().toLowerCase();
    return configs.filter((record) => {
      if (statusFilter === 'enabled' && !record.enabled) {
        return false;
      }
      if (statusFilter === 'disabled' && record.enabled) {
        return false;
      }
      if (roleFilter && !record.roles.includes(roleFilter)) {
        return false;
      }
      if (!normalizedSearch) {
        return true;
      }
      const searchableText = [
        record.action_key,
        ...record.aliases,
        record.enterprise_id ?? '',
        ...record.permissions,
        record.prompt,
        ...record.roles,
        record.summary,
        record.template_version ?? '',
        record.title,
        record.url,
      ].join(' ').toLowerCase();
      return searchableText.includes(normalizedSearch);
    });
  }, [configs, roleFilter, searchText, statusFilter]);
  const selectedConfigs = useMemo(
    () => configs.filter((item) => selectedRowKeys.includes(item.id)),
    [configs, selectedRowKeys],
  );

  const markMutating = (ids: string[], mutating: boolean) => {
    setMutatingConfigIds((current) => {
      const next = new Set(current);
      ids.forEach((id) => {
        if (mutating) {
          next.add(id);
        } else {
          next.delete(id);
        }
      });
      return next;
    });
  };

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
    setConfigSubmitting(true);
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
    } finally {
      setConfigSubmitting(false);
    }
  };

  const toggleStatus = async (record: AssistantActionReferenceConfig) => {
    markMutating([record.id], true);
    try {
      const updated = await setAssistantActionReferenceConfigStatus(record.id, !record.enabled);
      setConfigs((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      message.success(updated.enabled ? '@ 能力已启用' : '@ 能力已停用');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '@ 能力状态更新失败');
    } finally {
      markMutating([record.id], false);
    }
  };

  const batchSetStatus = async (enabled: boolean) => {
    const targets = selectedConfigs.filter((record) => record.enabled !== enabled);
    if (!targets.length) {
      message.info(enabled ? '所选能力已全部启用' : '所选能力已全部停用');
      return;
    }
    const targetIds = targets.map((record) => record.id);
    setBatchAction(enabled ? 'enable' : 'disable');
    markMutating(targetIds, true);
    try {
      const updatedRecords = await Promise.all(
        targets.map((record) => setAssistantActionReferenceConfigStatus(record.id, enabled)),
      );
      const updatedById = new Map(updatedRecords.map((record) => [record.id, record]));
      setConfigs((items) => items.map((item) => updatedById.get(item.id) ?? item));
      setSelectedRowKeys([]);
      message.success(enabled ? '所选 @ 能力已启用' : '所选 @ 能力已停用');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '批量更新失败');
    } finally {
      markMutating(targetIds, false);
      setBatchAction(undefined);
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
    setRolloutSubmitting(true);
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
    } finally {
      setRolloutSubmitting(false);
    }
  };

  const removeConfig = async (record: AssistantActionReferenceConfig) => {
    setDeletingConfigId(record.id);
    markMutating([record.id], true);
    try {
      await deleteAssistantActionReferenceConfig(record.id);
      setConfigs((items) => items.filter((item) => item.id !== record.id));
      setSelectedRowKeys((keys) => keys.filter((key) => key !== record.id));
      message.success('@ 能力已删除');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '@ 能力删除失败');
    } finally {
      markMutating([record.id], false);
      setDeletingConfigId(undefined);
    }
  };

  const columns: ColumnsType<AssistantActionReferenceConfig> = [
    {
      dataIndex: 'title',
      fixed: 'left',
      render: (_value, record) => (
        <Space orientation="vertical" size={2}>
          <Text strong>{record.title}</Text>
          <Text type="secondary">{record.action_key}</Text>
          <Text type="secondary">{record.summary}</Text>
        </Space>
      ),
      title: '能力',
      width: 260,
    },
    {
      dataIndex: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'default'}>{enabled ? '启用' : '停用'}</Tag>
      ),
      title: '状态',
      width: 90,
    },
    {
      dataIndex: 'sort_order',
      sorter: (left, right) => left.sort_order - right.sort_order,
      title: '排序',
      width: 90,
    },
    {
      dataIndex: 'permissions',
      render: (permissions: string[]) => tagList(permissions),
      title: '权限预览',
      width: 180,
    },
    {
      dataIndex: 'roles',
      render: (roles: string[]) => tagList(roles),
      title: '角色',
      width: 180,
    },
    {
      dataIndex: 'aliases',
      render: (aliases: string[]) => tagList(aliases.slice(0, 8)),
      title: '关键词',
      width: 180,
    },
    {
      dataIndex: 'enterprise_id',
      render: (enterpriseId?: string | null) => enterpriseId || <Text type="secondary">全局</Text>,
      title: '企业',
      width: 120,
    },
    {
      dataIndex: 'template_version',
      render: (version?: string | null) => version || <Text type="secondary">默认</Text>,
      title: '模板版本',
      width: 120,
    },
    {
      key: 'rollout',
      render: (_value, record) => {
        const percentage = rolloutPercentage(record);
        return percentage === undefined ? '-' : `${percentage}%`;
      },
      title: '灰度',
      width: 90,
    },
    {
      fixed: 'right',
      key: 'actions',
      render: (_value, record) => {
        const mutating = mutatingConfigIds.has(record.id);
        return (
          <Space size={8} wrap>
            <Button
              aria-label={`编辑 ${record.title}`}
              disabled={mutating}
              icon={<EditOutlined />}
              onClick={() => openEditConfig(record)}
              size="small"
            >
              编辑
            </Button>
            <Button
              aria-label={`${record.enabled ? '停用' : '启用'} ${record.title}`}
              icon={record.enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
              loading={mutating}
              onClick={() => void toggleStatus(record)}
              size="small"
            >
              {record.enabled ? '停用' : '启用'}
            </Button>
            <Button
              aria-label={`配置灰度 ${record.title}`}
              disabled={mutating}
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
              okButtonProps={{ loading: deletingConfigId === record.id }}
              onConfirm={() => void removeConfig(record)}
              title={`删除 ${record.title}`}
            >
              <Button danger disabled={mutating} icon={<DeleteOutlined />} size="small">
                删除
              </Button>
            </Popconfirm>
          </Space>
        );
      },
      title: '操作',
      width: 360,
    },
  ];

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
      <Space style={{ marginBottom: 16, width: '100%' }} wrap>
        <Input.Search
          allowClear
          onChange={(event) => setSearchText(event.target.value)}
          placeholder="搜索标题、关键词、角色、权限或 URL"
          style={{ width: 320 }}
          value={searchText}
        />
        <Select
          allowClear
          onChange={setStatusFilter}
          options={[
            { label: '启用', value: 'enabled' },
            { label: '停用', value: 'disabled' },
          ]}
          placeholder="状态"
          style={{ width: 120 }}
          value={statusFilter}
        />
        <Select
          allowClear
          onChange={setRoleFilter}
          options={roleOptions.map((role) => ({ label: role, value: role }))}
          placeholder="角色"
          style={{ minWidth: 160 }}
          value={roleFilter}
        />
        <Button
          disabled={!selectedConfigs.length}
          loading={batchAction === 'enable'}
          onClick={() => void batchSetStatus(true)}
        >
          批量启用
        </Button>
        <Button
          disabled={!selectedConfigs.length}
          loading={batchAction === 'disable'}
          onClick={() => void batchSetStatus(false)}
        >
          批量停用
        </Button>
        <Text type="secondary">
          已筛选 {filteredConfigs.length} 项 · 已选择 {selectedConfigs.length} 项
        </Text>
      </Space>

      <Table<AssistantActionReferenceConfig>
        columns={columns}
        dataSource={filteredConfigs}
        loading={loading}
        pagination={{
          defaultPageSize: 8,
          pageSizeOptions: [8, 16, 32],
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 项`,
        }}
        rowKey="id"
        rowSelection={{
          onChange: (keys) => setSelectedRowKeys(keys.map(String)),
          selectedRowKeys,
        }}
        scroll={{ x: 1480 }}
      />

      <Modal
        destroyOnHidden
        confirmLoading={configSubmitting}
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
        confirmLoading={rolloutSubmitting}
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
