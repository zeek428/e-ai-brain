import {
  AuditOutlined,
  DeploymentUnitOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Space, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ManagementListQuery } from '../../components/ManagementListPage';
import {
  fetchAssistantRoleQuickTaskConfigList,
  setAssistantRoleQuickTaskConfigStatus,
  updateAssistantRoleQuickTaskConfigRollout,
  type AssistantRoleQuickTaskConfig,
  type AssistantRoleQuickTaskConfigListQuery,
  type RemoteListPerformance,
} from '../../services/aiBrain';

type RolloutFormValues = {
  enterprise_id?: string;
  percentage?: number | string;
  template_version?: string;
};

type AssistantRoleQuickTaskRow = AssistantRoleQuickTaskConfig & {
  groupStatusValue: 'disabled' | 'enabled';
  statusValue: 'disabled' | 'enabled';
} & Record<string, unknown>;

const { Text } = Typography;

const quickTaskSortFieldMap: Record<string, string> = {
  groupStatusValue: 'group_enabled',
  statusValue: 'enabled',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildRoleQuickTaskListQuery(
  query: ManagementListQuery,
): AssistantRoleQuickTaskConfigListQuery {
  const filters = query.filters;
  return {
    enterpriseId: normalizeFilterText(filters.enterprise_id),
    groupStatus: normalizeFilterText(filters.group_status),
    keyword: normalizeFilterText(filters.keyword),
    page: query.page,
    pageSize: query.pageSize,
    permission: normalizeFilterText(filters.permission),
    role: normalizeFilterText(filters.role),
    sortField: query.sortField
      ? quickTaskSortFieldMap[query.sortField] ?? query.sortField
      : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(filters.status),
    targetDraftType: normalizeFilterText(filters.target_draft_type),
    templateVersion: normalizeFilterText(filters.template_version),
  };
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

function rolloutPercentage(record: AssistantRoleQuickTaskConfig) {
  const value = record.rollout_json?.percentage;
  return typeof value === 'number' ? value : undefined;
}

function auditUrl(record: AssistantRoleQuickTaskConfig) {
  const params = new URLSearchParams();
  params.set('subject_type', 'assistant_role_quick_task');
  params.set('subject_id', record.id);
  return `/governance/audit?${params.toString()}`;
}

export default function AssistantRoleQuickTasksPage() {
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'group_sort_order',
    sortOrder: 'ascend',
  });
  const [listState, setListState] = useState<{
    page: number;
    pageSize: number;
    performance?: RemoteListPerformance;
    rows: AssistantRoleQuickTaskConfig[];
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
  const [rolloutSubmitting, setRolloutSubmitting] = useState(false);
  const [rolloutTarget, setRolloutTarget] = useState<AssistantRoleQuickTaskConfig | undefined>();
  const [rolloutForm] = Form.useForm<RolloutFormValues>();

  const loadConfigs = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchAssistantRoleQuickTaskConfigList(
        buildRoleQuickTaskListQuery(listQuery),
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
      setListState((current) => ({ ...current, rows: [], status: 'error' }));
      message.error(error instanceof Error ? error.message : '快捷任务配置加载失败');
    }
  }, [listQuery]);

  useEffect(() => {
    let isCurrent = true;
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchAssistantRoleQuickTaskConfigList(buildRoleQuickTaskListQuery(listQuery))
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
          setListState((current) => ({ ...current, rows: [], status: 'error' }));
          message.error(error instanceof Error ? error.message : '快捷任务配置加载失败');
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [listQuery]);

  const configs = listState.rows;
  const groupedCount = useMemo(
    () => new Set(configs.map((item) => item.group_key)).size,
    [configs],
  );
  const enabledCount = useMemo(
    () => configs.filter((item) => item.enabled).length,
    [configs],
  );
  const configRows = useMemo<AssistantRoleQuickTaskRow[]>(
    () =>
      configs.map((record) => ({
        ...record,
        groupStatusValue: record.group_enabled ? 'enabled' : 'disabled',
        statusValue: record.enabled ? 'enabled' : 'disabled',
      })),
    [configs],
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

  const toggleStatus = async (record: AssistantRoleQuickTaskConfig) => {
    markMutating([record.id], true);
    try {
      const updated = await setAssistantRoleQuickTaskConfigStatus(record.id, {
        enabled: !record.enabled,
        group_enabled: record.group_enabled,
      });
      await loadConfigs();
      message.success(updated.enabled ? '快捷任务已启用' : '快捷任务已停用');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '快捷任务状态更新失败');
    } finally {
      markMutating([record.id], false);
    }
  };

  const openRollout = (record: AssistantRoleQuickTaskConfig) => {
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
      const updated = await updateAssistantRoleQuickTaskConfigRollout(rolloutTarget.id, {
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
      message.success('快捷任务灰度已更新');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '快捷任务灰度更新失败');
    } finally {
      setRolloutSubmitting(false);
    }
  };

  const columns: ProColumns<AssistantRoleQuickTaskRow>[] = [
    {
      dataIndex: 'title',
      fixed: 'left',
      render: (_value, record) => (
        <Space orientation="vertical" size={2}>
          <Text strong>{record.title}</Text>
          <Text type="secondary">{record.task_key}</Text>
          <Text type="secondary">{record.prompt}</Text>
        </Space>
      ),
      sorter: true,
      title: '任务',
      width: 280,
    },
    {
      dataIndex: 'group_label',
      render: (_value, record) => (
        <Space orientation="vertical" size={2}>
          <Text>{record.group_label}</Text>
          <Text type="secondary">{record.group_key}</Text>
        </Space>
      ),
      sorter: true,
      title: '分组',
      width: 190,
    },
    {
      dataIndex: 'statusValue',
      render: (_value, record) => (
        <Space size={4} wrap>
          <StatusTag
            color={record.enabled ? 'green' : 'default'}
            label={record.enabled ? '启用' : '停用'}
          />
          <StatusTag
            color={record.group_enabled ? 'blue' : 'default'}
            label={record.group_enabled ? '分组启用' : '分组停用'}
          />
        </Space>
      ),
      sorter: true,
      title: '状态',
      width: 160,
    },
    {
      dataIndex: 'group_roles',
      render: (_value, record) => tagList(record.group_roles),
      title: '角色',
      width: 170,
    },
    {
      dataIndex: 'permissions',
      render: (_value, record) => tagList(record.permissions),
      title: '权限',
      width: 210,
    },
    {
      dataIndex: 'target_draft_type',
      render: (_value, record) =>
        record.target_draft_type ? <Tag>{record.target_draft_type}</Tag> : '-',
      sorter: true,
      title: '草案模板',
      width: 190,
    },
    {
      dataIndex: 'enterprise_id',
      render: (_value, record) => record.enterprise_id || <Text type="secondary">全局</Text>,
      sorter: true,
      title: '企业',
      width: 130,
    },
    {
      dataIndex: 'template_version',
      render: (_value, record) => record.template_version || <Text type="secondary">默认</Text>,
      sorter: true,
      title: '模板版本',
      width: 130,
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
          </Space>
        );
      },
      title: '操作',
      width: 240,
    },
  ];

  return (
    <>
      <ManagementListPage<AssistantRoleQuickTaskRow>
        breadcrumbGroup="AI 助手"
        columns={columns}
        dataSource={configRows}
        filters={[
          {
            label: '搜索',
            name: 'keyword',
            placeholder: '搜索任务、分组、角色、权限或草案类型',
            type: 'text',
          },
          {
            label: '任务状态',
            name: 'status',
            options: [
              { label: '启用', value: 'enabled' },
              { label: '停用', value: 'disabled' },
            ],
            type: 'select',
          },
          {
            label: '分组状态',
            name: 'group_status',
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
            label: '草案模板',
            name: 'target_draft_type',
            placeholder: '输入草案类型',
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
        onReload={() => void loadConfigs()}
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="id"
        tableLayout="fixed"
        tableScroll={{ x: 1660 }}
        tableTitle="AI助手快捷任务配置"
        title="AI助手快捷任务配置"
        viewStorageKey="assistant.role_quick_tasks"
        beforeTable={
          <Space style={{ marginBottom: 16, width: '100%' }} wrap>
            <Tag color="blue">共 {listState.total} 项</Tag>
            <Tag color="green">当前页 {enabledCount} 项启用</Tag>
            <Tag>当前页 {groupedCount} 个分组</Tag>
          </Space>
        }
      />

      <Modal
        destroyOnHidden
        confirmLoading={rolloutSubmitting}
        onCancel={() => {
          setRolloutTarget(undefined);
          rolloutForm.resetFields();
        }}
        onOk={() => rolloutForm.submit()}
        open={Boolean(rolloutTarget)}
        title={`快捷任务灰度 · ${rolloutTarget?.title ?? ''}`}
      >
        <Form form={rolloutForm} layout="vertical" onFinish={(values) => void submitRollout(values)}>
          <Form.Item label="企业 ID" name="enterprise_id">
            <Input placeholder="留空表示全局" />
          </Form.Item>
          <Form.Item label="模板版本" name="template_version">
            <Input placeholder="例如 2026.07" />
          </Form.Item>
          <Form.Item label="灰度比例" name="percentage">
            <Input max={100} min={0} type="number" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
