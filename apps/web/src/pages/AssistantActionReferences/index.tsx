import {
  AuditOutlined,
  DeleteOutlined,
  DeploymentUnitOutlined,
  EditOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
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

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ManagementListQuery } from '../../components/ManagementListPage';
import {
  createAssistantActionReferenceConfig,
  deleteAssistantActionReferenceConfig,
  fetchAssistantActionReferenceConfigList,
  patchAssistantActionReferenceConfig,
  setAssistantActionReferenceConfigStatus,
  updateAssistantActionReferenceConfigRollout,
  type AssistantActionReferenceConfig,
  type AssistantActionReferenceConfigListQuery,
  type RemoteListPerformance,
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

type AssistantActionReferenceRow = AssistantActionReferenceConfig & {
  statusValue: 'disabled' | 'enabled';
} & Record<string, unknown>;

const { Text } = Typography;

const actionReferenceSortFieldMap: Record<string, string> = {
  statusValue: 'enabled',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildActionReferenceListQuery(
  query: ManagementListQuery,
): AssistantActionReferenceConfigListQuery {
  const filters = query.filters;
  return {
    enterpriseId: normalizeFilterText(filters.enterprise_id),
    keyword: normalizeFilterText(filters.keyword),
    page: query.page,
    pageSize: query.pageSize,
    permission: normalizeFilterText(filters.permission),
    role: normalizeFilterText(filters.role),
    sortField: query.sortField
      ? actionReferenceSortFieldMap[query.sortField] ?? query.sortField
      : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(filters.status),
    templateVersion: normalizeFilterText(filters.template_version),
  };
}

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
  const [configSubmitting, setConfigSubmitting] = useState(false);
  const [deletingConfigId, setDeletingConfigId] = useState<string>();
  const [editingConfig, setEditingConfig] = useState<AssistantActionReferenceConfig>();
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'sort_order',
    sortOrder: 'ascend',
  });
  const [listState, setListState] = useState<{
    page: number;
    pageSize: number;
    performance?: RemoteListPerformance;
    rows: AssistantActionReferenceConfig[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const [mutatingConfigIds, setMutatingConfigIds] = useState<Set<string>>(() => new Set());
  const [rolloutTarget, setRolloutTarget] = useState<AssistantActionReferenceConfig>();
  const [rolloutSubmitting, setRolloutSubmitting] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [configForm] = Form.useForm<ActionReferenceFormValues>();
  const [rolloutForm] = Form.useForm<RolloutFormValues>();

  const loadConfigs = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchAssistantActionReferenceConfigList(
        buildActionReferenceListQuery(listQuery),
      );
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        performance: result.performance,
        rows: result.rows,
        status: 'ready',
        total: result.total,
      });
    } catch (error) {
      setListState((current) => ({
        ...current,
        rows: [],
        status: 'error',
      }));
      message.error(error instanceof Error ? error.message : '@ 能力配置加载失败');
    }
  }, [listQuery]);

  const handleListQueryChange = useCallback((nextQuery: ManagementListQuery) => {
    setListState((current) => ({ ...current, status: 'loading' }));
    setListQuery(nextQuery);
  }, []);

  useEffect(() => {
    let isCurrent = true;
    fetchAssistantActionReferenceConfigList(buildActionReferenceListQuery(listQuery))
      .then((result) => {
        if (isCurrent) {
          setListState({
            page: result.page,
            pageSize: result.pageSize,
            performance: result.performance,
            rows: result.rows,
            status: 'ready',
            total: result.total,
          });
        }
      })
      .catch((error: unknown) => {
        if (isCurrent) {
          setListState((current) => ({
            ...current,
            rows: [],
            status: 'error',
          }));
          message.error(error instanceof Error ? error.message : '@ 能力配置加载失败');
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [listQuery]);

  const configs = listState.rows;

  const enabledCount = useMemo(
    () => configs.filter((item) => item.enabled).length,
    [configs],
  );
  const configRows = useMemo<AssistantActionReferenceRow[]>(
    () =>
      configs.map((record) => ({
        ...record,
        statusValue: record.enabled ? 'enabled' : 'disabled',
      })),
    [configs],
  );
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
      sort_order: (Math.max(0, ...configs.map((config) => config.sort_order)) || 0) + 10,
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
      void updated;
      closeConfigModal();
      await loadConfigs();
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
      await loadConfigs();
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
      void updatedRecords;
      setSelectedRowKeys([]);
      await loadConfigs();
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
      void updated;
      setRolloutTarget(undefined);
      rolloutForm.resetFields();
      await loadConfigs();
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
      setSelectedRowKeys((keys) => keys.filter((key) => key !== record.id));
      await loadConfigs();
      message.success('@ 能力已删除');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '@ 能力删除失败');
    } finally {
      markMutating([record.id], false);
      setDeletingConfigId(undefined);
    }
  };

  const columns: ProColumns<AssistantActionReferenceRow>[] = [
    {
      dataIndex: 'title',
      fixed: 'left',
      sorter: true,
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
      dataIndex: 'statusValue',
      sorter: true,
      render: (_value, record) => (
        <StatusTag
          color={record.enabled ? 'green' : 'default'}
          label={record.enabled ? '启用' : '停用'}
        />
      ),
      title: '状态',
      width: 90,
    },
    {
      dataIndex: 'sort_order',
      sorter: true,
      title: '排序',
      width: 90,
    },
    {
      dataIndex: 'permissions',
      render: (_value, record) => tagList(record.permissions),
      title: '权限预览',
      width: 180,
    },
    {
      dataIndex: 'roles',
      render: (_value, record) => tagList(record.roles),
      title: '角色',
      width: 180,
    },
    {
      dataIndex: 'aliases',
      render: (_value, record) => tagList(record.aliases.slice(0, 8)),
      title: '关键词',
      width: 180,
    },
    {
      dataIndex: 'enterprise_id',
      sorter: true,
      render: (_value, record) => record.enterprise_id || <Text type="secondary">全局</Text>,
      title: '企业',
      width: 120,
    },
    {
      dataIndex: 'template_version',
      sorter: true,
      render: (_value, record) => record.template_version || <Text type="secondary">默认</Text>,
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
    <>
      <ManagementListPage<AssistantActionReferenceRow>
        breadcrumbGroup="AI 助手"
        columns={columns}
        dataSource={configRows}
        viewStorageKey="assistant.action_references"
        filters={[
          {
            label: '搜索',
            name: 'keyword',
            placeholder: '搜索标题、关键词、角色、权限或 URL',
            type: 'text',
          },
          {
            label: '状态',
            name: 'status',
            options: [
              { label: '启用', value: 'enabled' },
              { label: '停用', value: 'disabled' },
            ],
            type: 'select',
          },
          {
            label: '角色',
            name: 'role',
            placeholder: '输入角色',
            type: 'text',
          },
          {
            label: '权限',
            name: 'permission',
            placeholder: '输入权限点',
            type: 'text',
          },
          {
            label: '企业',
            name: 'enterprise_id',
            placeholder: '输入企业 ID',
            type: 'text',
          },
          {
            label: '模板版本',
            name: 'template_version',
            placeholder: '输入模板版本',
            type: 'text',
          },
        ]}
        loading={listState.status === 'loading'}
        onPrimaryAction={openCreateConfig}
        onReload={() => void loadConfigs()}
        primaryAction="新增能力"
        remote={{
          onChange: handleListQueryChange,
          page: listState.page,
          pageSize: listState.pageSize,
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="id"
        rowSelection={{
          onChange: (keys) => setSelectedRowKeys(keys.map(String)),
          selectedRowKeys,
        }}
        tableLayout="fixed"
        tableScroll={{ x: 1480 }}
        tableTitle="AI助手 @ 能力配置"
        title="@ 能力配置"
        beforeTable={
          <Space style={{ marginBottom: 16, width: '100%' }} wrap>
            <Tag color="blue">共 {listState.total} 项</Tag>
            <Tag color="green">当前页 {enabledCount} 项启用</Tag>
            <Text type="secondary">已选择 {selectedConfigs.length} 项</Text>
          </Space>
        }
        toolbarActions={[
          <Button
            disabled={!selectedConfigs.length}
            key="batch-enable"
            loading={batchAction === 'enable'}
            onClick={() => void batchSetStatus(true)}
          >
            批量启用
          </Button>,
          <Button
            disabled={!selectedConfigs.length}
            key="batch-disable"
            loading={batchAction === 'disable'}
            onClick={() => void batchSetStatus(false)}
          >
            批量停用
          </Button>,
        ]}
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
    </>
  );
}
