import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { ProTable, type ProColumns } from '@ant-design/pro-components';
import {
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
  fetchDeploymentSchemes,
  updateDeploymentScheme,
  type DeploymentJenkinsConnectionRecord,
  type DeploymentMethod,
  type DeploymentRunnerTargetRecord,
  type DeploymentSchemeCreatePayload,
  type DeploymentSchemeRecord,
} from '../../services/aiBrain';

type DeploymentSchemeFormValues = {
  code: string;
  deploymentMethod: DeploymentMethod;
  environment: string;
  isDefault: boolean;
  jenkinsConnectionId?: string;
  jenkinsJobName?: string;
  name: string;
  parametersJson?: string;
  productId: string;
  runnerId?: string;
  status: 'active' | 'disabled';
  targetCode?: string;
  timeoutSeconds: number;
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
  return {
    code: scheme.code,
    deploymentMethod: scheme.deploymentMethod,
    environment: scheme.environment,
    isDefault: scheme.isDefault,
    jenkinsConnectionId: scheme.jenkinsConnectionId,
    jenkinsJobName: scheme.jenkinsJobName,
    name: scheme.name,
    parametersJson:
      parameters && typeof parameters === 'object' && !Array.isArray(parameters)
        ? JSON.stringify(parameters, null, 2)
        : undefined,
    productId: scheme.productId,
    runnerId: scheme.runnerId,
    status: scheme.status,
    targetCode: scheme.targetCode,
    timeoutSeconds: scheme.timeoutSeconds,
  };
}

function schemePayload(values: DeploymentSchemeFormValues): DeploymentSchemeCreatePayload {
  const payload: DeploymentSchemeCreatePayload = {
    code: values.code.trim(),
    config: {},
    deployment_method: values.deploymentMethod,
    environment: values.environment,
    is_default: values.isDefault,
    name: values.name.trim(),
    product_id: values.productId,
    status: values.status,
    timeout_seconds: values.timeoutSeconds,
  };
  if (values.deploymentMethod === 'ssh' || values.deploymentMethod === 'docker') {
    payload.runner_id = values.runnerId;
    payload.target_code = values.targetCode;
  }
  if (values.deploymentMethod === 'jenkins') {
    payload.jenkins_connection_id = values.jenkinsConnectionId;
    payload.jenkins_job_name = values.jenkinsJobName?.trim();
    payload.config = { parameters: parseParametersJson(values.parametersJson) };
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
  const [runnerTargets, setRunnerTargets] = useState<DeploymentRunnerTargetRecord[]>([]);
  const [connections, setConnections] = useState<DeploymentJenkinsConnectionRecord[]>([]);
  const deploymentMethod = Form.useWatch('deploymentMethod', form);
  const selectedRunnerId = Form.useWatch('runnerId', form);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [nextSchemes, nextRunnerTargets, nextConnections] = canManage
        ? await Promise.all([
            fetchDeploymentSchemes(),
            fetchDeploymentRunnerTargets(),
            fetchDeploymentJenkinsConnections(),
          ])
        : [await fetchDeploymentSchemes(), [], []];
      setSchemes(nextSchemes);
      setRunnerTargets(nextRunnerTargets);
      setConnections(nextConnections);
      onSchemesChanged(nextSchemes);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '部署方案加载失败');
    } finally {
      setLoading(false);
    }
  }, [canManage, onSchemesChanged]);

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
      deploymentMethod: 'manual',
      environment: 'prod',
      isDefault: false,
      productId: productOptions.length === 1 ? productOptions[0]?.value : undefined,
      status: 'active',
      timeoutSeconds: 1800,
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
  };

  const confirmDelete = useCallback((scheme: DeploymentSchemeRecord) => {
    Modal.confirm({
      content: `确定删除部署方案「${scheme.name}」吗？已被部署单使用的方案不能删除。`,
      okButtonProps: { danger: true },
      onOk: async () => {
        await deleteDeploymentScheme(scheme.id);
        message.success('部署方案已删除');
        await reload();
      },
      title: '删除部署方案',
    });
  }, [reload]);

  const columns = useMemo<ProColumns<DeploymentSchemeRecord>[]>(
    () => [
      { dataIndex: 'name', ellipsis: true, title: '方案名称', width: 210 },
      {
        dataIndex: 'productId',
        render: (_, row) => productNameById.get(row.productId) ?? row.productId,
        title: '所属产品',
        width: 170,
      },
      { dataIndex: 'environment', title: '环境', width: 110 },
      {
        dataIndex: 'deploymentMethod',
        render: (value) => deploymentMethodLabels[String(value)] ?? String(value),
        title: '部署方式',
        width: 120,
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
        title: '默认方案',
        width: 110,
      },
      {
        dataIndex: 'status',
        render: (value) => <Tag color={value === 'active' ? 'green' : 'default'}>{value === 'active' ? '启用' : '停用'}</Tag>,
        title: '状态',
        width: 100,
      },
      { dataIndex: 'updatedAt', ellipsis: true, title: '更新时间', width: 170 },
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
        options={false}
        pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
        rowKey="id"
        scroll={{ x: 1520 }}
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
            <Select disabled={Boolean(editingScheme)} options={productOptions} />
          </Form.Item>
          <Form.Item label="方案编码" name="code" rules={[{ required: true, message: '请输入方案编码' }]}>
            <Input placeholder="prod-compose" />
          </Form.Item>
          <Form.Item label="方案名称" name="name" rules={[{ required: true, message: '请输入方案名称' }]}>
            <Input placeholder="生产 Docker 部署" />
          </Form.Item>
          <Form.Item label="环境" name="environment" rules={[{ required: true }]}>
            <Select options={environmentOptions} />
          </Form.Item>
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
