import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { ProTable, type ProColumns } from '@ant-design/pro-components';
import {
  Alert,
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Segmented,
  Select,
  Space,
  Switch,
  Tag,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import type { ProductContextOption } from '../../data/management';
import {
  createDeploymentScheme,
  deleteDeploymentScheme,
  fetchDeploymentJenkinsConnections,
  fetchDeploymentRunnerTargets,
  fetchDeploymentSchemeList,
  fetchDeploymentSchemes,
  updateDeploymentScheme,
  type DeploymentJenkinsConnectionRecord,
  type DeploymentMethod,
  type DeploymentRunnerTargetRecord,
  type DeploymentSchemeCreatePayload,
  type DeploymentSchemeRecord,
} from '../../services/aiBrain';
import { navigateTo } from '../../utils/navigation';

type DeploymentSchemeFormValues = {
  autoRollback: boolean;
  autoRollbackRiskThreshold: 'low' | 'medium';
  batchWaveCount?: number;
  blueActiveSlot?: string;
  blueTargetSlot?: string;
  canaryPercent?: number;
  code: string;
  deploymentMethod: DeploymentMethod;
  environment: string;
  isDefault: boolean;
  healthCheckRequired: boolean;
  jenkinsConnectionId?: string;
  jenkinsHealthJobName?: string;
  jenkinsJobName?: string;
  jenkinsRollbackJobName?: string;
  name: string;
  parametersJson?: string;
  productId: string;
  runnerId?: string;
  rollbackEnabled: boolean;
  rolloutStrategy: 'all_at_once' | 'batch' | 'blue_green' | 'canary';
  status: 'active' | 'disabled';
  targetCode?: string;
  timeoutSeconds: number;
  windowEnforcement: 'disabled' | 'strict' | 'warn';
};

const deploymentMethodOptions = [
  { label: '人工部署', value: 'manual' },
  { label: 'SSH', value: 'ssh' },
  { label: 'Docker', value: 'docker' },
  { label: 'Jenkins', value: 'jenkins' },
];

const deploymentMethodLabels: Record<string, string> = {
  docker: 'Docker',
  jenkins: 'Jenkins',
  manual: '人工部署',
  ssh: 'SSH',
};

const environmentOptions = [
  { label: '开发环境', value: 'dev' },
  { label: '测试环境', value: 'test' },
  { label: '预发布环境', value: 'staging' },
  { label: '生产环境', value: 'prod' },
  { label: '沙箱环境', value: 'sandbox' },
];

const rolloutStrategyOptions = [
  { label: '全量', value: 'all_at_once' },
  { label: '灰度', value: 'canary' },
  { label: '分批', value: 'batch' },
  { label: '蓝绿', value: 'blue_green' },
];

const windowEnforcementOptions = [
  { label: '严格执行', value: 'strict' },
  { label: '仅告警', value: 'warn' },
  { label: '不校验', value: 'disabled' },
];

function parseParametersJson(value?: string): Record<string, unknown> {
  const text = value?.trim();
  if (!text) return {};
  const parsed: unknown = JSON.parse(text);
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('Jenkins 参数必须是 JSON 对象');
  }
  return parsed as Record<string, unknown>;
}

function schemeFormValues(scheme: DeploymentSchemeRecord): DeploymentSchemeFormValues {
  const parameters = scheme.config.parameters;
  const waveConfig = scheme.waveConfig;
  const healthConfig = scheme.healthCheckConfig;
  const rollbackConfig = scheme.rollbackConfig;
  return {
    autoRollback: Boolean(rollbackConfig.auto_on_failure),
    autoRollbackRiskThreshold:
      rollbackConfig.auto_risk_threshold === 'low' ? 'low' : 'medium',
    batchWaveCount: Number(waveConfig.wave_count || 2),
    blueActiveSlot: typeof waveConfig.active_slot === 'string' ? waveConfig.active_slot : 'blue',
    blueTargetSlot: typeof waveConfig.target_slot === 'string' ? waveConfig.target_slot : 'green',
    canaryPercent: Number(waveConfig.canary_percent || 10),
    code: scheme.code,
    deploymentMethod: scheme.deploymentMethod,
    environment: scheme.environment,
    isDefault: scheme.isDefault,
    healthCheckRequired: Boolean(healthConfig.required),
    jenkinsConnectionId: scheme.jenkinsConnectionId,
    jenkinsHealthJobName:
      typeof healthConfig.job_name === 'string' ? healthConfig.job_name : undefined,
    jenkinsJobName: scheme.jenkinsJobName,
    jenkinsRollbackJobName:
      typeof rollbackConfig.job_name === 'string' ? rollbackConfig.job_name : undefined,
    name: scheme.name,
    parametersJson:
      parameters && typeof parameters === 'object' && !Array.isArray(parameters)
        ? JSON.stringify(parameters, null, 2)
        : undefined,
    productId: scheme.productId,
    runnerId: scheme.runnerId,
    rollbackEnabled: Boolean(rollbackConfig.enabled),
    rolloutStrategy: scheme.rolloutStrategy,
    status: scheme.status,
    targetCode: scheme.targetCode,
    timeoutSeconds: scheme.timeoutSeconds,
    windowEnforcement: scheme.windowEnforcement,
  };
}

function schemePayload(values: DeploymentSchemeFormValues): DeploymentSchemeCreatePayload {
  const payload: DeploymentSchemeCreatePayload = {
    code: values.code.trim(),
    config: {},
    deployment_method: values.deploymentMethod,
    environment: values.environment,
    is_default: values.isDefault,
    health_check_config: {},
    name: values.name.trim(),
    preflight_config: {
      require_artifact: values.windowEnforcement === 'strict',
      require_rollback: values.environment === 'prod',
    },
    product_id: values.productId,
    rollback_config: {},
    rollout_strategy: values.rolloutStrategy,
    status: values.status,
    timeout_seconds: values.timeoutSeconds,
    wave_config: {},
    window_enforcement: values.windowEnforcement,
  };
  if (values.rolloutStrategy === 'canary') {
    payload.wave_config = { canary_percent: values.canaryPercent ?? 10 };
  } else if (values.rolloutStrategy === 'batch') {
    payload.wave_config = { wave_count: values.batchWaveCount ?? 2 };
  } else if (values.rolloutStrategy === 'blue_green') {
    payload.wave_config = {
      active_slot: values.blueActiveSlot?.trim(),
      rollback_action: 'target.blue_green_rollback',
      switch_action: 'target.blue_green_switch',
      target_slot: values.blueTargetSlot?.trim(),
    };
  }
  if (values.deploymentMethod === 'ssh' || values.deploymentMethod === 'docker') {
    payload.runner_id = values.runnerId;
    payload.target_code = values.targetCode;
    payload.health_check_config = { required: values.healthCheckRequired };
    payload.rollback_config = {
      auto_on_failure: values.autoRollback,
      auto_risk_threshold: values.autoRollbackRiskThreshold,
      enabled: values.rollbackEnabled,
      human_takeover_on_failure: true,
      strategy: 'target_command',
    };
  }
  if (values.deploymentMethod === 'jenkins') {
    payload.jenkins_connection_id = values.jenkinsConnectionId;
    payload.jenkins_job_name = values.jenkinsJobName?.trim();
    payload.config = { parameters: parseParametersJson(values.parametersJson) };
    payload.health_check_config = values.jenkinsHealthJobName?.trim()
      ? { job_name: values.jenkinsHealthJobName.trim() }
      : {};
    payload.rollback_config = values.jenkinsRollbackJobName?.trim()
      ? {
          auto_on_failure: values.autoRollback,
          auto_risk_threshold: values.autoRollbackRiskThreshold,
          enabled: values.rollbackEnabled,
          human_takeover_on_failure: true,
          job_name: values.jenkinsRollbackJobName.trim(),
        }
      : {};
  }
  return payload;
}

export function DeploymentSchemePanel({
  canManage,
  productContexts,
  onSchemesChanged,
}: {
  canManage: boolean;
  onSchemesChanged: (schemes: DeploymentSchemeRecord[]) => void;
  productContexts: ProductContextOption[];
}) {
  const [form] = Form.useForm<DeploymentSchemeFormValues>();
  const [editingScheme, setEditingScheme] = useState<DeploymentSchemeRecord>();
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [schemes, setSchemes] = useState<DeploymentSchemeRecord[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortField, setSortField] = useState('updated_at');
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend'>('descend');
  const [total, setTotal] = useState(0);
  const [runnerTargets, setRunnerTargets] = useState<DeploymentRunnerTargetRecord[]>([]);
  const [connections, setConnections] = useState<DeploymentJenkinsConnectionRecord[]>([]);
  const deploymentMethod = Form.useWatch('deploymentMethod', form);
  const environment = Form.useWatch('environment', form);
  const productId = Form.useWatch('productId', form);
  const rolloutStrategy = Form.useWatch('rolloutStrategy', form);
  const selectedRunnerId = Form.useWatch('runnerId', form);
  const windowEnforcement = Form.useWatch('windowEnforcement', form);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchDeploymentSchemeList({
        page,
        pageSize,
        sortField,
        sortOrder,
      });
      setSchemes(result.rows);
      setTotal(result.total);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '部署方案加载失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, sortField, sortOrder]);

  const refreshParentSchemes = useCallback(async () => {
    onSchemesChanged(await fetchDeploymentSchemes());
  }, [onSchemesChanged]);

  useEffect(() => {
    let active = true;
    const timer = globalThis.setTimeout(() => {
      if (!canManage || !modalOpen || !productId || !environment) {
        setRunnerTargets([]);
        setConnections([]);
        return;
      }
      void Promise.all([
        fetchDeploymentRunnerTargets({ environment, productId }),
        fetchDeploymentJenkinsConnections({ environment, productId }),
      ])
        .then(([nextTargets, nextConnections]) => {
          if (!active) return;
          setRunnerTargets(nextTargets);
          setConnections(nextConnections);
        })
        .catch((error: unknown) => {
          if (!active) return;
          setRunnerTargets([]);
          setConnections([]);
          message.error(error instanceof Error ? error.message : '执行资源加载失败');
        });
    }, 0);
    return () => {
      active = false;
      globalThis.clearTimeout(timer);
    };
  }, [canManage, environment, modalOpen, productId]);

  useEffect(() => {
    const timer = globalThis.setTimeout(() => void reload(), 0);
    return () => globalThis.clearTimeout(timer);
  }, [reload]);

  const productNameById = useMemo(
    () => new Map(productContexts.map((product) => [product.id, product.name])),
    [productContexts],
  );
  const productOptions = useMemo(
    () => productContexts.map((product) => ({ label: product.name, value: product.id })),
    [productContexts],
  );
  const methodTargets = useMemo(
    () => runnerTargets.filter((target) => target.method === deploymentMethod),
    [deploymentMethod, runnerTargets],
  );
  const runnerOptions = useMemo(
    () =>
      Array.from(new Set(methodTargets.map((target) => target.runnerId))).map((runnerId) => ({
        label: runnerId,
        value: runnerId,
      })),
    [methodTargets],
  );
  const targetOptions = useMemo(
    () =>
      methodTargets
        .filter((target) => target.runnerId === selectedRunnerId)
        .map((target) => ({
          disabled: !target.ready,
          label: target.ready ? target.name : `${target.name}（未就绪）`,
          value: target.code,
        })),
    [methodTargets, selectedRunnerId],
  );
  const jenkinsConnectionOptions = useMemo(
    () =>
      connections
        .map((connection) => ({
          disabled: !connection.ready,
          label: connection.ready ? connection.name : `${connection.name}（未就绪）`,
          value: connection.id,
        })),
    [connections],
  );
  const runnerResourceMissing = Boolean(
    productId
    && environment
    && (deploymentMethod === 'ssh' || deploymentMethod === 'docker')
    && methodTargets.length === 0,
  );
  const jenkinsResourceMissing = Boolean(
    productId
    && environment
    && deploymentMethod === 'jenkins'
    && connections.length === 0,
  );

  useEffect(() => {
    if (!modalOpen || (deploymentMethod !== 'ssh' && deploymentMethod !== 'docker')) return;
    if (!form.getFieldValue('runnerId') && runnerOptions.length === 1) {
      form.setFieldValue('runnerId', runnerOptions[0]?.value);
    }
  }, [deploymentMethod, form, modalOpen, runnerOptions]);

  useEffect(() => {
    if (!modalOpen || form.getFieldValue('targetCode') || targetOptions.length !== 1) return;
    const target = targetOptions[0];
    if (!target?.disabled) form.setFieldValue('targetCode', target?.value);
  }, [form, modalOpen, targetOptions]);

  const closeModal = () => {
    setModalOpen(false);
    setEditingScheme(undefined);
    form.resetFields();
  };

  const openCreateModal = () => {
    setEditingScheme(undefined);
    form.resetFields();
    form.setFieldsValue({
      autoRollback: false,
      autoRollbackRiskThreshold: 'medium',
      batchWaveCount: 2,
      blueActiveSlot: 'blue',
      blueTargetSlot: 'green',
      canaryPercent: 10,
      deploymentMethod: 'manual',
      environment: 'prod',
      healthCheckRequired: true,
      isDefault: false,
      productId: productOptions.length === 1 ? productOptions[0]?.value : undefined,
      rollbackEnabled: true,
      rolloutStrategy: 'all_at_once',
      status: 'active',
      timeoutSeconds: 1800,
      windowEnforcement: 'strict',
    });
    setModalOpen(true);
  };

  const openEditModal = useCallback((scheme: DeploymentSchemeRecord) => {
    setEditingScheme(scheme);
    form.setFieldsValue(schemeFormValues(scheme));
    setModalOpen(true);
  }, [form]);

  const saveScheme = async () => {
    const values = await form.validateFields();
    let payload: DeploymentSchemeCreatePayload;
    try {
      payload = schemePayload(values);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '部署方案配置无效');
      return;
    }
    if (editingScheme) {
      await updateDeploymentScheme(editingScheme.id, { ...payload, version: editingScheme.version });
      message.success('部署方案已更新');
    } else {
      await createDeploymentScheme(payload);
      message.success('部署方案已创建');
    }
    closeModal();
    await reload();
    await refreshParentSchemes();
  };

  const confirmDelete = useCallback((scheme: DeploymentSchemeRecord) => {
    Modal.confirm({
      content: `确定删除部署方案「${scheme.name}」吗？已被部署单使用的方案不能删除。`,
      okButtonProps: { danger: true },
      onOk: async () => {
        await deleteDeploymentScheme(scheme.id);
        message.success('部署方案已删除');
        await reload();
        await refreshParentSchemes();
      },
      title: '删除部署方案',
    });
  }, [refreshParentSchemes, reload]);

  const columns = useMemo<ProColumns<DeploymentSchemeRecord>[]>(
    () => [
      { dataIndex: 'name', ellipsis: true, sorter: true, title: '方案名称', width: 210 },
      {
        dataIndex: 'productId',
        render: (_, row) => productNameById.get(row.productId) ?? row.productId,
        title: '所属产品',
        width: 170,
      },
      { dataIndex: 'environment', sorter: true, title: '环境', width: 110 },
      {
        dataIndex: 'deploymentMethod',
        render: (value) => deploymentMethodLabels[String(value)] ?? String(value),
        sorter: true,
        title: '部署方式',
        width: 120,
      },
      {
        dataIndex: 'rolloutStrategy',
        render: (value) => ({
          all_at_once: '全量',
          batch: '分批',
          blue_green: '蓝绿',
          canary: '灰度',
        })[String(value)] ?? String(value),
        title: '发布策略',
        width: 110,
      },
      {
        dataIndex: 'windowEnforcement',
        render: (value) => ({ disabled: '不校验', strict: '严格', warn: '告警' })[String(value)] ?? String(value),
        title: '窗口策略',
        width: 110,
      },
      {
        dataIndex: 'executorChannel',
        render: (value) => ({ integration: '系统集成', manual: '人工', runner: 'Runner' })[String(value)] ?? String(value),
        title: '执行通道',
        width: 120,
      },
      {
        key: 'binding',
        render: (_, row) =>
          row.runnerId
            ? `${row.runnerId} · ${row.targetCode ?? '-'}`
            : row.jenkinsConnectionId
              ? `${row.jenkinsConnectionId} · ${row.jenkinsJobName ?? '-'}`
              : '-',
        title: '执行资源',
        width: 260,
      },
      {
        dataIndex: 'isDefault',
        render: (value) => (value ? <Tag color="blue">默认</Tag> : '-'),
        sorter: true,
        title: '默认方案',
        width: 110,
      },
      {
        dataIndex: 'status',
        render: (value) => <Tag color={value === 'active' ? 'green' : 'default'}>{value === 'active' ? '启用' : '停用'}</Tag>,
        sorter: true,
        title: '状态',
        width: 100,
      },
      { dataIndex: 'updatedAt', ellipsis: true, sorter: true, title: '更新时间', width: 170 },
      {
        fixed: 'right',
        key: 'actions',
        render: (_, row) =>
          canManage ? (
            <Space className="management-row-actions" size={0} wrap={false}>
              <Button icon={<EditOutlined />} onClick={() => openEditModal(row)} type="link">编辑</Button>
              <Button danger icon={<DeleteOutlined />} onClick={() => confirmDelete(row)} type="link">删除</Button>
            </Space>
          ) : '-',
        title: '操作',
        width: 150,
      },
    ],
    [canManage, confirmDelete, openEditModal, productNameById],
  );

  return (
    <>
      <ProTable<DeploymentSchemeRecord>
        cardBordered
        columns={columns}
        dataSource={schemes}
        headerTitle="部署方案列表"
        loading={loading}
        onChange={(nextPagination, _filters, sorter) => {
          const activeSorter = Array.isArray(sorter) ? sorter[0] : sorter;
          const fieldMap: Record<string, string> = {
            deploymentMethod: 'deployment_method',
            environment: 'environment',
            isDefault: 'is_default',
            name: 'name',
            status: 'status',
            updatedAt: 'updated_at',
          };
          setPage(nextPagination.current ?? 1);
          setPageSize(nextPagination.pageSize ?? 10);
          if (activeSorter?.field && activeSorter.order) {
            setSortField(fieldMap[String(activeSorter.field)] ?? String(activeSorter.field));
            setSortOrder(activeSorter.order);
          }
        }}
        options={false}
        pagination={{
          current: page,
          pageSize,
          showSizeChanger: true,
          showTotal: (count) => `共 ${count} 条`,
          total,
        }}
        rowKey="id"
        scroll={{ x: 1740 }}
        search={false}
        tableLayout="fixed"
        toolBarRender={() => [
          <Button icon={<ReloadOutlined />} key="reload" onClick={() => void reload()}>刷新</Button>,
          canManage ? (
            <Button
              aria-label="新增部署方案"
              icon={<PlusOutlined />}
              key="create"
              onClick={openCreateModal}
              type="primary"
            >
              新增部署方案
            </Button>
          ) : null,
        ]}
      />
      <Modal
        destroyOnHidden
        okButtonProps={{ 'aria-label': '保存部署方案' }}
        okText="保存"
        onCancel={closeModal}
        onOk={() => void saveScheme()}
        open={modalOpen}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
        title={editingScheme ? '编辑部署方案' : '新增部署方案'}
      >
        <Form<DeploymentSchemeFormValues> form={form} layout="vertical">
          <Form.Item label="所属产品" name="productId" rules={[{ required: true, message: '请选择所属产品' }]}>
            <Select
              disabled={Boolean(editingScheme)}
              onChange={() => form.setFieldsValue({
                jenkinsConnectionId: undefined,
                runnerId: undefined,
                targetCode: undefined,
              })}
              options={productOptions}
            />
          </Form.Item>
          <Form.Item label="方案编码" name="code" rules={[{ required: true, message: '请输入方案编码' }]}>
            <Input placeholder="prod-compose" />
          </Form.Item>
          <Form.Item label="方案名称" name="name" rules={[{ required: true, message: '请输入方案名称' }]}>
            <Input placeholder="生产 Docker 部署" />
          </Form.Item>
          <Form.Item label="环境" name="environment" rules={[{ required: true }]}>
            <Select
              onChange={(value) => {
                form.setFieldValue('windowEnforcement', value === 'prod' ? 'strict' : 'warn');
                form.setFieldsValue({
                  jenkinsConnectionId: undefined,
                  runnerId: undefined,
                  targetCode: undefined,
                });
              }}
              options={environmentOptions}
            />
          </Form.Item>
          <Form.Item label="部署窗口" name="windowEnforcement" rules={[{ required: true }]}>
            <Segmented block options={windowEnforcementOptions} />
          </Form.Item>
          <Form.Item label="发布策略" name="rolloutStrategy" rules={[{ required: true }]}>
            <Segmented block options={rolloutStrategyOptions} />
          </Form.Item>
          {rolloutStrategy === 'canary' ? (
            <Form.Item label="灰度流量比例" name="canaryPercent" rules={[{ required: true }]}>
              <InputNumber max={99} min={1} style={{ width: '100%' }} suffix="%" />
            </Form.Item>
          ) : null}
          {rolloutStrategy === 'batch' ? (
            <Form.Item label="发布批次数" name="batchWaveCount" rules={[{ required: true }]}>
              <InputNumber max={20} min={2} style={{ width: '100%' }} />
            </Form.Item>
          ) : null}
          {rolloutStrategy === 'blue_green' ? (
            <Space align="start" size={12} style={{ display: 'flex' }}>
              <Form.Item label="当前槽位" name="blueActiveSlot" rules={[{ required: true }]}>
                <Input placeholder="blue" />
              </Form.Item>
              <Form.Item label="目标槽位" name="blueTargetSlot" rules={[{ required: true }]}>
                <Input placeholder="green" />
              </Form.Item>
            </Space>
          ) : null}
          <Form.Item label="部署方式" name="deploymentMethod" rules={[{ required: true }]}>
            <Segmented
              block
              onChange={() => form.setFieldsValue({
                jenkinsConnectionId: undefined,
                jenkinsJobName: undefined,
                runnerId: undefined,
                targetCode: undefined,
              })}
              options={deploymentMethodOptions}
            />
          </Form.Item>
          {runnerResourceMissing ? (
            <Alert
              action={(
                <Space size={4} wrap>
                  <Button onClick={() => navigateTo('/tasks/plugins')} size="small" type="link">配置部署 Runner</Button>
                  <Button onClick={() => navigateTo('/system/execution-resources')} size="small" type="link">授权部署目标</Button>
                </Space>
              )}
              description="需要部署信任域 Runner 在线上报对应 SSH 或 Docker 目标，并授权给当前产品和环境。"
              title={`${deploymentMethod === 'ssh' ? 'SSH' : 'Docker'} 部署资源尚未就绪`}
              showIcon
              type="warning"
            />
          ) : null}
          {jenkinsResourceMissing ? (
            <Alert
              action={(
                <Space size={4} wrap>
                  <Button onClick={() => navigateTo('/tasks/plugins')} size="small" type="link">配置 Jenkins 连接</Button>
                  <Button onClick={() => navigateTo('/system/execution-resources')} size="small" type="link">授权 Jenkins 连接</Button>
                </Space>
              )}
              description="需要启用当前环境的 Jenkins 连接，并授权给当前产品和环境。"
              title="Jenkins 部署资源尚未就绪"
              showIcon
              type="warning"
            />
          ) : null}
          {deploymentMethod === 'ssh' || deploymentMethod === 'docker' ? (
            <>
              <Form.Item label="Runner" name="runnerId" rules={[{ required: true, message: '请选择 Runner' }]}>
                <Select
                  onChange={() => form.setFieldValue('targetCode', undefined)}
                  options={runnerOptions}
                  placeholder="请选择具备部署能力的 Runner"
                />
              </Form.Item>
              <Form.Item label="部署目标" name="targetCode" rules={[{ required: true, message: '请选择部署目标' }]}>
                <Select disabled={!selectedRunnerId} options={targetOptions} />
              </Form.Item>
              <Form.Item label="部署后健康检查" name="healthCheckRequired" valuePropName="checked">
                <Switch />
              </Form.Item>
            </>
          ) : null}
          {deploymentMethod === 'jenkins' ? (
            <>
              <Form.Item
                label="Jenkins 连接"
                name="jenkinsConnectionId"
                rules={[{ required: true, message: '请选择 Jenkins 连接' }]}
              >
                <Select options={jenkinsConnectionOptions} />
              </Form.Item>
              <Form.Item label="Jenkins Job" name="jenkinsJobName" rules={[{ required: true, message: '请输入 Jenkins Job' }]}>
                <Input />
              </Form.Item>
              <Form.Item label="Jenkins 参数 JSON" name="parametersJson">
                <Input.TextArea placeholder={'{"IMAGE_TAG":"2026.07.11"}'} rows={4} />
              </Form.Item>
              <Form.Item
                label="健康检查 Job"
                name="jenkinsHealthJobName"
                rules={[
                  {
                    required: environment === 'prod' && windowEnforcement === 'strict',
                    message: '严格生产方案必须配置健康检查 Job',
                  },
                ]}
              >
                <Input placeholder="folder/verify-product" />
              </Form.Item>
              <Form.Item
                label="回滚 Job"
                name="jenkinsRollbackJobName"
                rules={[
                  {
                    required: environment === 'prod' && windowEnforcement === 'strict',
                    message: '严格生产方案必须配置回滚 Job',
                  },
                ]}
              >
                <Input placeholder="folder/rollback-product" />
              </Form.Item>
            </>
          ) : null}
          {deploymentMethod !== 'manual' ? (
            <>
              <Form.Item label="启用真实回滚" name="rollbackEnabled" valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item label="健康失败自动回滚" name="autoRollback" valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item label="自动回滚最高风险" name="autoRollbackRiskThreshold" rules={[{ required: true }]}>
                <Select
                  options={[
                    { label: '低风险', value: 'low' },
                    { label: '中风险', value: 'medium' },
                  ]}
                />
              </Form.Item>
            </>
          ) : null}
          <Form.Item label="超时秒数" name="timeoutSeconds" rules={[{ required: true }]}>
            <InputNumber max={86400} min={30} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="状态" name="status" rules={[{ required: true }]}>
            <Select options={[{ label: '启用', value: 'active' }, { label: '停用', value: 'disabled' }]} />
          </Form.Item>
          <Form.Item label="设为默认方案" name="isDefault" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
