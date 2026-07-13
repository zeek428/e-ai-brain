import type { ProColumns } from '@ant-design/pro-components';
import { Form, Modal, Segmented, Select, Space, Switch, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import {
  createExecutionResourceGrant,
  fetchExecutionResourceGrants,
  fetchExecutionResourceProducts,
  updateExecutionResourceGrantStatus,
  type ExecutionResourceGrantRecord,
  type ExecutionResourceProduct,
} from '../../services/executionGovernanceClient';
import {
  fetchAiExecutorRunners,
  fetchPluginConnections,
  type AiExecutorRunnerRecord,
  type PluginConnectionRecord,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { formatMutationError } from '../../utils/managementCrud';

const { Text } = Typography;

type GrantFormValues = {
  environment: string;
  product_id: string;
  resource_key: string;
  resource_type: 'jenkins_connection' | 'runner_target';
};

type DeploymentTarget = {
  code: string;
  connectivityProbeStatus?: string;
  method?: string;
  name: string;
  ready?: boolean;
  runnerCapabilities: string[];
  runnerHealthStatus?: string;
  runnerId: string;
  runnerName: string;
  runnerStatus?: string;
  runnerTrustDomain?: string;
};

type GrantRow = ExecutionResourceGrantRecord & {
  environment_name: string;
  product_name: string;
  resource_readiness: ResourceReadiness;
  resource_name: string;
};

type ResourceReadiness = {
  color: 'default' | 'green' | 'orange' | 'red';
  label: string;
  ready: boolean;
};

const ENVIRONMENT_OPTIONS = [
  { label: '开发环境', value: 'dev' },
  { label: '测试环境', value: 'test' },
  { label: '预发布环境', value: 'staging' },
  { label: '生产环境', value: 'prod' },
];

const RESOURCE_TYPE_OPTIONS = [
  { label: 'Runner 目标', value: 'runner_target' },
  { label: 'Jenkins 连接', value: 'jenkins_connection' },
];

const STATUS_OPTIONS = [
  { label: '启用', value: 'active' },
  { label: '停用', value: 'disabled' },
];

function environmentLabel(value: string) {
  return ENVIRONMENT_OPTIONS.find((item) => item.value === value)?.label ?? value;
}

function resourceTypeLabel(value: string) {
  return RESOURCE_TYPE_OPTIONS.find((item) => item.value === value)?.label ?? value;
}

function deploymentTargets(runners: AiExecutorRunnerRecord[]): DeploymentTarget[] {
  return runners.flatMap((runner) => {
    const targets = Array.isArray(runner.metadata?.deployment_targets)
      ? runner.metadata.deployment_targets
      : [];
    return targets.flatMap((value) => {
      if (!value || typeof value !== 'object' || Array.isArray(value)) {
        return [];
      }
      const item = value as Record<string, unknown>;
      const code = String(item.code ?? '').trim();
      if (!code) {
        return [];
      }
      const probe = item.connectivity_probe;
      const connectivityProbeStatus = probe
        && typeof probe === 'object'
        && !Array.isArray(probe)
        ? String((probe as Record<string, unknown>).status ?? '').trim() || undefined
        : undefined;
      return [{
        code,
        connectivityProbeStatus,
        method: String(item.method ?? '').trim() || undefined,
        name: String(item.name ?? code),
        ready: item.ready !== false,
        runnerCapabilities: runner.capabilities ?? [],
        runnerHealthStatus: runner.health_status,
        runnerId: runner.id,
        runnerName: runner.name,
        runnerStatus: runner.status,
        runnerTrustDomain: runner.trust_domain,
      }];
    });
  });
}

function runnerTargetReadiness(target?: DeploymentTarget): ResourceReadiness {
  if (!target) return { color: 'red', label: '部署目标未上报', ready: false };
  if (target.runnerStatus !== 'active') return { color: 'red', label: 'Runner 未启用', ready: false };
  if (target.runnerHealthStatus && target.runnerHealthStatus !== 'online') {
    return { color: 'orange', label: 'Runner 未在线', ready: false };
  }
  if (!target.runnerCapabilities.includes('deployment')) {
    return { color: 'red', label: '未启用部署能力', ready: false };
  }
  if (target.runnerTrustDomain !== 'deployment') {
    return { color: 'red', label: '非部署信任域', ready: false };
  }
  if (!target.ready) return { color: 'orange', label: '部署目标未就绪', ready: false };
  if (target.connectivityProbeStatus === 'stale') {
    return { color: 'orange', label: '真实探测已过期', ready: false };
  }
  if (target.connectivityProbeStatus === 'failed' || target.connectivityProbeStatus === 'timed_out') {
    return { color: 'red', label: '真实探测失败', ready: false };
  }
  if (target.connectivityProbeStatus !== 'succeeded') {
    return { color: 'orange', label: '未完成真实探测', ready: false };
  }
  return { color: 'green', label: '已就绪', ready: true };
}

function jenkinsConnectionReadiness(connection?: PluginConnectionRecord): ResourceReadiness {
  if (!connection) return { color: 'red', label: 'Jenkins 连接不存在', ready: false };
  if (connection.status !== 'active') return { color: 'orange', label: 'Jenkins 连接未启用', ready: false };
  return { color: 'green', label: '已就绪', ready: true };
}

export default function ExecutionResourcesPage() {
  const [form] = Form.useForm<GrantFormValues>();
  const [grants, setGrants] = useState<ExecutionResourceGrantRecord[]>([]);
  const [products, setProducts] = useState<ExecutionResourceProduct[]>([]);
  const [runners, setRunners] = useState<AiExecutorRunnerRecord[]>([]);
  const [connections, setConnections] = useState<PluginConnectionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const selectedResourceType = Form.useWatch('resource_type', form) ?? 'runner_target';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextGrants, nextProducts, nextRunners, nextConnections] = await Promise.all([
        fetchExecutionResourceGrants(),
        fetchExecutionResourceProducts(),
        fetchAiExecutorRunners(),
        fetchPluginConnections(),
      ]);
      setGrants(nextGrants);
      setProducts(nextProducts);
      setRunners(nextRunners);
      setConnections(nextConnections);
    } catch (error) {
      message.error(formatMutationError(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = globalThis.setTimeout(() => void load(), 0);
    return () => globalThis.clearTimeout(timer);
  }, [load]);

  const targets = useMemo(() => deploymentTargets(runners), [runners]);
  const jenkinsConnections = useMemo(
    () => connections.filter((item) =>
      item.plugin_code === 'jenkins' || String(item.plugin_name ?? '').toLowerCase().includes('jenkins')),
    [connections],
  );
  const rows = useMemo<GrantRow[]>(() => grants.map((grant) => {
    const product = products.find((item) => item.id === grant.product_id);
    const target = targets.find((item) => item.runnerId === grant.resource_id && item.code === grant.target_code);
    const connection = connections.find((item) => item.id === grant.resource_id);
    const resourceReadiness = grant.resource_type === 'runner_target'
      ? runnerTargetReadiness(target)
      : jenkinsConnectionReadiness(connection);
    return {
      ...grant,
      environment_name: environmentLabel(grant.environment),
      product_name: product?.name ?? grant.product_id,
      resource_readiness: resourceReadiness,
      resource_name: grant.resource_type === 'runner_target'
        ? target?.name ?? grant.target_code ?? grant.resource_id
        : connection?.name ?? grant.resource_id,
    };
  }), [connections, grants, products, targets]);

  const resourceOptions = useMemo(() => selectedResourceType === 'runner_target'
    ? targets.filter((target) => runnerTargetReadiness(target).ready).map((target) => ({
        label: `${target.name} · ${target.runnerName}${target.method ? ` · ${target.method.toUpperCase()}` : ''}`,
        value: `${target.runnerId}::${target.code}`,
      }))
    : jenkinsConnections.filter((connection) => jenkinsConnectionReadiness(connection).ready).map((connection) => ({
        label: `${connection.name} · ${connection.environment ?? 'default'}`,
        value: connection.id,
      })), [jenkinsConnections, selectedResourceType, targets]);
  const resourceNotFoundContent = selectedResourceType === 'runner_target'
    ? '没有可授权的 Runner 目标：请检查 Runner 在线、部署信任域、目标上报和真实连通性探测。'
    : '没有可授权的 Jenkins 连接：请先在插件管理中创建并启用 Jenkins 连接。';

  const openCreate = () => {
    form.resetFields();
    form.setFieldsValue({
      environment: 'prod',
      product_id: products[0]?.id,
      resource_type: 'runner_target',
    });
    setModalOpen(true);
  };

  const submit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const [resourceId, targetCode = ''] = values.resource_key.split('::', 2);
      await createExecutionResourceGrant({
        environment: values.environment,
        product_id: values.product_id,
        resource_id: resourceId,
        resource_type: values.resource_type,
        target_code: values.resource_type === 'runner_target' ? targetCode : null,
      });
      message.success('执行资源授权已创建');
      setModalOpen(false);
      await load();
    } catch (error) {
      message.error(formatMutationError(error));
    } finally {
      setSubmitting(false);
    }
  };

  const toggleStatus = async (row: GrantRow, checked: boolean) => {
    try {
      await updateExecutionResourceGrantStatus(row.id, {
        status: checked ? 'active' : 'disabled',
        version: row.version,
      });
      message.success(checked ? '授权已启用' : '授权已停用');
      await load();
    } catch (error) {
      message.error(formatMutationError(error));
    }
  };

  const columns: ProColumns<GrantRow>[] = [
    { dataIndex: 'product_name', title: '产品', width: 180 },
    {
      dataIndex: 'environment_name',
      render: (_, row) => <Tag color={row.environment === 'prod' ? 'red' : 'blue'}>{row.environment_name}</Tag>,
      title: '环境',
      width: 120,
    },
    {
      dataIndex: 'resource_type',
      render: (_, row) => resourceTypeLabel(row.resource_type),
      title: '资源类型',
      width: 140,
    },
    {
      dataIndex: 'resource_name',
      render: (_, row) => (
        <Space orientation="vertical" size={2}>
          <Text strong>{row.resource_name}</Text>
          <Text type="secondary">{row.resource_id}{row.target_code ? ` / ${row.target_code}` : ''}</Text>
        </Space>
      ),
      title: '执行资源',
      width: 280,
    },
    {
      dataIndex: 'resource_readiness',
      render: (_, row) => <Tag color={row.resource_readiness.color}>{row.resource_readiness.label}</Tag>,
      title: '资源就绪状态',
      width: 150,
    },
    {
      dataIndex: 'status',
      render: (_, row) => <StatusTag color={row.status === 'active' ? 'green' : 'default'} label={row.status === 'active' ? '启用' : '停用'} />,
      title: '状态',
      width: 100,
    },
    {
      dataIndex: 'updated_at',
      render: (value) => formatDisplayDateTime(value as string | undefined),
      title: '更新时间',
      width: 170,
    },
    {
      fixed: 'right',
      render: (_, row) => (
        <Switch
          aria-label={`${row.status === 'active' ? '停用' : '启用'}${row.resource_name}授权`}
          checked={row.status === 'active'}
          checkedChildren="启用"
          unCheckedChildren="停用"
          onChange={(checked) => void toggleStatus(row, checked)}
        />
      ),
      title: '授权开关',
      width: 110,
    },
  ];

  return (
    <>
      <ManagementListPage<GrantRow>
        breadcrumbGroup="系统管理"
        columns={columns}
        dataSource={rows}
        filters={[
          { label: '产品', name: 'product_name', type: 'text' },
          { label: '环境', name: 'environment', options: ENVIRONMENT_OPTIONS, type: 'select' },
          { label: '资源类型', name: 'resource_type', options: RESOURCE_TYPE_OPTIONS, type: 'select' },
          { label: '状态', name: 'status', options: STATUS_OPTIONS, type: 'select' },
        ]}
        loading={loading}
        onPrimaryAction={openCreate}
        onReload={() => void load()}
        primaryAction="新增授权"
        rowKey="id"
        tableLayout="fixed"
        tableScroll={{ x: 1250 }}
        tableTitle="执行资源授权"
        title="执行资源授权"
        viewStorageKey="system.execution_resources"
      />
      <Modal
        confirmLoading={submitting}
        destroyOnHidden
        okText="创建授权"
        open={modalOpen}
        title="新增执行资源授权"
        width={680}
        onCancel={() => setModalOpen(false)}
        onOk={() => void submit()}
      >
        <Form<GrantFormValues> form={form} labelCol={{ span: 6 }} layout="horizontal">
          <Form.Item label="产品" name="product_id" rules={[{ required: true, message: '请选择产品' }]}>
            <Select options={products.map((item) => ({ label: item.name, value: item.id }))} showSearch />
          </Form.Item>
          <Form.Item label="环境" name="environment" rules={[{ required: true, message: '请选择环境' }]}>
            <Segmented block options={ENVIRONMENT_OPTIONS} />
          </Form.Item>
          <Form.Item label="资源类型" name="resource_type" rules={[{ required: true, message: '请选择资源类型' }]}>
            <Segmented
              block
              options={RESOURCE_TYPE_OPTIONS}
              onChange={() => form.setFieldValue('resource_key', undefined)}
            />
          </Form.Item>
          <Form.Item label="执行资源" name="resource_key" rules={[{ required: true, message: '请选择执行资源' }]}>
            <Select
              notFoundContent={resourceNotFoundContent}
              optionFilterProp="label"
              options={resourceOptions}
              showSearch
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
