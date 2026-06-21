import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { PageContainer, ProTable, type ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Tag, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { StatusTag } from '../../components/ManagementListPage';
import type { ProductGitRepositoryRecord, ProductRecord } from '../../data/management';
import {
  createRdTaskExecutorPolicy,
  deleteRdTaskExecutorPolicy,
  fetchAiExecutorRunners,
  fetchManagementProducts,
  fetchProductGitRepositoryRecords,
  fetchRdTaskExecutorPolicies,
  updateRdTaskExecutorPolicy,
  type AiExecutorRunnerRecord,
  type RdTaskExecutorPolicyRecord,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { formatMutationError } from '../../utils/managementCrud';

type PolicyFormValues = {
  branch?: string;
  executor_type: string;
  instruction_template: string;
  name: string;
  output_contract_json?: string;
  priority: number;
  product_id?: string;
  repository_id?: string;
  runner_id?: string;
  status: string;
  task_type: string;
  timeout_seconds: number;
  workspace_root: string;
};

const TASK_TYPE_OPTIONS = [
  { label: 'PRD / 原型 / 产品详细设计', value: 'product_detail_design' },
  { label: '技术方案设计', value: 'technical_solution' },
  { label: '代码实现 / 开发计划', value: 'development_planning' },
  { label: '代码评审', value: 'code_review' },
  { label: '自动化测试', value: 'automated_testing' },
  { label: '代码整改', value: 'code_inspection_remediation' },
  { label: '发布上线评估', value: 'release_readiness' },
  { label: '上线后分析', value: 'post_release_analysis' },
];

const EXECUTOR_OPTIONS = [
  { label: 'Codex', value: 'codex' },
  { label: 'Claude Code', value: 'claude' },
  { label: 'OpenClaw', value: 'openclaw' },
];

const STATUS_OPTIONS = [
  { label: '启用', value: 'active' },
  { label: '停用', value: 'disabled' },
];

const STATUS_COLORS: Record<string, string> = {
  active: 'green',
  disabled: 'default',
};

function taskTypeLabel(value: string) {
  return TASK_TYPE_OPTIONS.find((item) => item.value === value)?.label ?? value;
}

function executorLabel(value: string) {
  return EXECUTOR_OPTIONS.find((item) => item.value === value)?.label ?? value;
}

function mutationError(error: unknown, fallback: string) {
  const detail = formatMutationError(error);
  return detail === '请求失败' ? fallback : detail;
}

function stableJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

function parseJsonObject(value: string | undefined, field: string) {
  const text = (value ?? '').trim();
  if (!text) {
    return {};
  }
  try {
    const parsed = JSON.parse(text);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      throw new Error(`${field} must be a JSON object`);
    }
    return parsed as Record<string, unknown>;
  } catch {
    throw new Error(`${field} 不是合法 JSON 对象`);
  }
}

export default function RdExecutorPoliciesPage() {
  const [form] = Form.useForm<PolicyFormValues>();
  const [editingPolicy, setEditingPolicy] = useState<RdTaskExecutorPolicyRecord | undefined>();
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [policies, setPolicies] = useState<RdTaskExecutorPolicyRecord[]>([]);
  const [products, setProducts] = useState<ProductRecord[]>([]);
  const [repositories, setRepositories] = useState<ProductGitRepositoryRecord[]>([]);
  const [runners, setRunners] = useState<AiExecutorRunnerRecord[]>([]);
  const selectedExecutorType = Form.useWatch('executor_type', form);

  const reload = useCallback(async () => {
    await Promise.resolve();
    setLoading(true);
    try {
      const [nextPolicies, nextProducts, nextRunners] = await Promise.all([
        fetchRdTaskExecutorPolicies(),
        fetchManagementProducts(),
        fetchAiExecutorRunners({ status: 'active' }),
      ]);
      setPolicies(nextPolicies);
      setProducts(nextProducts);
      setRunners(nextRunners.filter((runner) => runner.id !== 'ai_executor_runner_system_default'));
    } catch (error) {
      message.error(mutationError(error, '加载研发执行器策略失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  const productOptions = useMemo(
    () => [
      { label: '全局默认', value: '' },
      ...products.map((product) => ({ label: product.name, value: product.id })),
    ],
    [products],
  );

  const repositoryOptions = useMemo(
    () => [
      { label: '不绑定', value: '' },
      ...repositories.map((repository) => ({
        label: `${repository.name} (${repository.defaultBranch})`,
        value: repository.id,
      })),
    ],
    [repositories],
  );

  const runnerOptions = useMemo(() => {
    return runners
      .filter((runner) => !selectedExecutorType || (runner.executor_types ?? []).includes(selectedExecutorType))
      .map((runner) => ({
        label: `${runner.name} (${(runner.executor_types ?? []).map(executorLabel).join(', ')})`,
        value: runner.id,
      }));
  }, [runners, selectedExecutorType]);

  const loadRepositories = useCallback(async (productId?: string | null) => {
    if (!productId) {
      setRepositories([]);
      return;
    }
    try {
      setRepositories(await fetchProductGitRepositoryRecords(productId));
    } catch (error) {
      setRepositories([]);
      message.error(mutationError(error, '加载产品代码库失败'));
    }
  }, []);

  const openCreateModal = () => {
    setEditingPolicy(undefined);
    setRepositories([]);
    form.resetFields();
    form.setFieldsValue({
      executor_type: 'codex',
      instruction_template: '请基于研发任务 {{task_id}} / {{task_title}} 在当前仓库完成分析，并输出结构化结果。',
      output_contract_json: stableJson({ summary: 'string', details: 'object' }),
      priority: 100,
      status: 'active',
      task_type: 'product_detail_design',
      timeout_seconds: 1800,
      workspace_root: '',
    });
    setModalOpen(true);
  };

  const openEditModal = async (policy: RdTaskExecutorPolicyRecord) => {
    setEditingPolicy(policy);
    await loadRepositories(policy.product_id);
    form.resetFields();
    form.setFieldsValue({
      branch: policy.branch ?? undefined,
      executor_type: policy.executor_type,
      instruction_template: policy.instruction_template,
      name: policy.name,
      output_contract_json: stableJson(policy.output_contract ?? {}),
      priority: policy.priority,
      product_id: policy.product_id ?? '',
      repository_id: policy.repository_id ?? '',
      runner_id: policy.runner_id ?? undefined,
      status: policy.status,
      task_type: policy.task_type,
      timeout_seconds: policy.timeout_seconds,
      workspace_root: policy.workspace_root,
    });
    setModalOpen(true);
  };

  const submitPolicy = async () => {
    try {
      const values = await form.validateFields();
      const outputContract = parseJsonObject(values.output_contract_json, '输出契约');
      const payload = {
        branch: values.branch || null,
        executor_type: values.executor_type,
        instruction_template: values.instruction_template,
        name: values.name,
        output_contract: outputContract,
        priority: values.priority,
        product_id: values.product_id || null,
        repository_id: values.repository_id || null,
        runner_id: values.runner_id || null,
        status: values.status,
        task_type: values.task_type,
        timeout_seconds: values.timeout_seconds,
        workspace_root: values.workspace_root,
      };
      if (editingPolicy) {
        await updateRdTaskExecutorPolicy(editingPolicy.id, payload);
        message.success('研发执行器策略已更新');
      } else {
        await createRdTaskExecutorPolicy(payload);
        message.success('研发执行器策略已创建');
      }
      setModalOpen(false);
      await reload();
    } catch (error) {
      message.error(mutationError(error, '保存研发执行器策略失败'));
    }
  };

  const removePolicy = async (policy: RdTaskExecutorPolicyRecord) => {
    try {
      await deleteRdTaskExecutorPolicy(policy.id);
      message.success('研发执行器策略已删除');
      await reload();
    } catch (error) {
      message.error(mutationError(error, '删除研发执行器策略失败'));
    }
  };

  const columns: ProColumns<RdTaskExecutorPolicyRecord>[] = [
    {
      dataIndex: 'name',
      title: '策略名称',
      width: 220,
    },
    {
      dataIndex: 'task_type',
      render: (_, row) => <Tag>{taskTypeLabel(row.task_type)}</Tag>,
      title: '任务类型',
      width: 190,
    },
    {
      dataIndex: 'executor_type',
      render: (_, row) => <Tag color="blue">{executorLabel(row.executor_type)}</Tag>,
      title: '执行器',
      width: 130,
    },
    {
      dataIndex: 'runner_name',
      render: (_, row) => row.runner_name ?? row.runner_id ?? '-',
      title: 'Runner',
      width: 220,
    },
    {
      dataIndex: 'product_name',
      render: (_, row) => row.product_name ?? '全局默认',
      title: '产品',
      width: 160,
    },
    {
      dataIndex: 'repository_name',
      render: (_, row) => row.repository_name ?? row.repository_id ?? '-',
      title: '代码库',
      width: 180,
    },
    {
      dataIndex: 'workspace_root',
      ellipsis: true,
      title: '工作区',
      width: 260,
    },
    {
      dataIndex: 'priority',
      sorter: (left, right) => left.priority - right.priority,
      title: '优先级',
      width: 100,
    },
    {
      dataIndex: 'status',
      render: (_, row) => (
        <StatusTag color={STATUS_COLORS[row.status] ?? 'default'} label={row.status === 'active' ? '启用' : '停用'} />
      ),
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
        <Space>
          <Button size="small" type="link" onClick={() => openEditModal(row)}>
            编辑
          </Button>
          <Popconfirm title={`删除策略「${row.name}」？`} onConfirm={() => removePolicy(row)}>
            <Button danger size="small" type="link">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
      title: '操作',
      valueType: 'option',
      width: 140,
    },
  ];

  return (
    <PageContainer title="研发执行器策略">
      <ProTable<RdTaskExecutorPolicyRecord>
        columns={columns}
        dataSource={policies}
        loading={loading}
        pagination={{ pageSize: 10 }}
        rowKey="id"
        search={false}
        scroll={{ x: 1810 }}
        toolBarRender={() => [
          <Button key="reload" icon={<ReloadOutlined />} onClick={reload}>
            刷新
          </Button>,
          <Button key="create" icon={<PlusOutlined />} type="primary" onClick={openCreateModal}>
            新增策略
          </Button>,
        ]}
      />

      <Modal
        destroyOnHidden
        open={modalOpen}
        title={editingPolicy ? '编辑研发执行器策略' : '新增研发执行器策略'}
        width={760}
        onCancel={() => setModalOpen(false)}
        onOk={submitPolicy}
      >
        <Form<PolicyFormValues> form={form} labelCol={{ span: 6 }} layout="horizontal">
          <Form.Item label="策略名称" name="name" rules={[{ required: true, message: '请输入策略名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="任务类型" name="task_type" rules={[{ required: true, message: '请选择任务类型' }]}>
            <Select optionFilterProp="label" options={TASK_TYPE_OPTIONS} showSearch />
          </Form.Item>
          <Form.Item label="执行器" name="executor_type" rules={[{ required: true, message: '请选择执行器' }]}>
            <Select
              options={EXECUTOR_OPTIONS}
              onChange={() => {
                form.setFieldValue('runner_id', undefined);
              }}
            />
          </Form.Item>
          <Form.Item label="Runner" name="runner_id" rules={[{ required: true, message: '请选择 Runner' }]}>
            <Select options={runnerOptions} />
          </Form.Item>
          <Form.Item label="产品" name="product_id">
            <Select
              options={productOptions}
              onChange={async (value) => {
                form.setFieldValue('repository_id', '');
                await loadRepositories(value);
              }}
            />
          </Form.Item>
          <Form.Item label="代码库" name="repository_id">
            <Select options={repositoryOptions} />
          </Form.Item>
          <Form.Item label="分支" name="branch">
            <Input />
          </Form.Item>
          <Form.Item label="工作区" name="workspace_root" rules={[{ required: true, message: '请输入工作区路径' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="超时秒数" name="timeout_seconds" rules={[{ required: true, message: '请输入超时秒数' }]}>
            <InputNumber max={86400} min={60} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="优先级" name="priority" rules={[{ required: true, message: '请输入优先级' }]}>
            <InputNumber max={10000} min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item label="指令模板" name="instruction_template" rules={[{ required: true, message: '请输入指令模板' }]}>
            <Input.TextArea rows={5} />
          </Form.Item>
          <Form.Item label="输出契约" name="output_contract_json">
            <Input.TextArea rows={5} />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
}
