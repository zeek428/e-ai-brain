import {
  AuditOutlined,
  DeploymentUnitOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import {
  Button,
  Form,
  Input,
  Modal,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  fetchAssistantRoleQuickTaskConfigs,
  setAssistantRoleQuickTaskConfigStatus,
  updateAssistantRoleQuickTaskConfigRollout,
  type AssistantRoleQuickTaskConfig,
} from '../../services/aiBrain';

type RolloutFormValues = {
  enterprise_id?: string;
  percentage?: number | string;
  template_version?: string;
};

const { Text } = Typography;

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
  const [configs, setConfigs] = useState<AssistantRoleQuickTaskConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [rolloutTarget, setRolloutTarget] = useState<AssistantRoleQuickTaskConfig | undefined>();
  const [rolloutForm] = Form.useForm<RolloutFormValues>();

  const loadConfigs = useCallback(async () => {
    setLoading(true);
    try {
      setConfigs(await fetchAssistantRoleQuickTaskConfigs());
    } catch (error) {
      message.error(error instanceof Error ? error.message : '快捷任务配置加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      void loadConfigs();
    });
  }, [loadConfigs]);

  const groupedCount = useMemo(
    () => new Set(configs.map((item) => item.group_key)).size,
    [configs],
  );

  const toggleStatus = async (record: AssistantRoleQuickTaskConfig) => {
    try {
      const updated = await setAssistantRoleQuickTaskConfigStatus(record.id, {
        enabled: !record.enabled,
        group_enabled: record.group_enabled,
      });
      setConfigs((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      message.success(updated.enabled ? '快捷任务已启用' : '快捷任务已停用');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '快捷任务状态更新失败');
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
    try {
      const updated = await updateAssistantRoleQuickTaskConfigRollout(rolloutTarget.id, {
        enterprise_id: values.enterprise_id?.trim() || null,
        rollout_json: {
          percentage: Number(values.percentage ?? 100),
        },
        template_version: values.template_version?.trim() || null,
      });
      setConfigs((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setRolloutTarget(undefined);
      rolloutForm.resetFields();
      message.success('快捷任务灰度已更新');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '快捷任务灰度更新失败');
    }
  };

  return (
    <PageContainer
      title="AI助手快捷任务配置"
      extra={[
        <Tag color="blue" key="groups">{groupedCount} 个分组</Tag>,
        <Tag color="green" key="tasks">{configs.length} 个任务</Tag>,
      ]}
    >
      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', minWidth: 1320, width: '100%' }}>
          <thead>
            <tr>
              {['任务', '分组', '状态', '角色', '权限', '草案模板', '企业', '模板版本', '灰度', '操作'].map((title) => (
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
                      <Text type="secondary">{record.task_key}</Text>
                    </Space>
                  </td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    <Space orientation="vertical" size={2}>
                      <Text>{record.group_label}</Text>
                      <Text type="secondary">{record.group_key}</Text>
                    </Space>
                  </td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    <Space size={4} wrap>
                      <Tag color={record.enabled ? 'green' : 'default'}>
                        {record.enabled ? '启用' : '停用'}
                      </Tag>
                      <Tag color={record.group_enabled ? 'blue' : 'default'}>
                        {record.group_enabled ? '分组启用' : '分组停用'}
                      </Tag>
                    </Space>
                  </td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>{tagList(record.group_roles)}</td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>{tagList(record.permissions)}</td>
                  <td style={{ borderBottom: '1px solid #f0f0f0', padding: 8 }}>
                    {record.target_draft_type ? <Tag>{record.target_draft_type}</Tag> : '-'}
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
                    <Space size={8}>
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
                      <Button
                        href={auditUrl(record)}
                        icon={<AuditOutlined />}
                        size="small"
                      >
                        审计
                      </Button>
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
        onCancel={() => {
          setRolloutTarget(undefined);
          rolloutForm.resetFields();
        }}
        onOk={() => rolloutForm.submit()}
        open={Boolean(rolloutTarget)}
        title={`快捷任务灰度 · ${rolloutTarget?.title ?? ''}`}
      >
        <Form
          form={rolloutForm}
          layout="vertical"
          onFinish={(values) => void submitRollout(values)}
        >
          <Form.Item label="企业 ID" name="enterprise_id">
            <Input placeholder="留空表示全局" />
          </Form.Item>
          <Form.Item label="模板版本" name="template_version">
            <Input placeholder="例如 2026.07" />
          </Form.Item>
          <Form.Item
            label="灰度比例"
            name="percentage"
          >
            <Input max={100} min={0} type="number" />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
}
