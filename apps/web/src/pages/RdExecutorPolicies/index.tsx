import type { ProColumns } from '@ant-design/pro-components';
import { Alert, Button, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Tag, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ManagementListQuery } from '../../components/ManagementListPage';
import type { ProductGitRepositoryRecord, ProductRecord } from '../../data/management';
import {
  createRdTaskExecutorPolicy,
  deleteRdTaskExecutorPolicy,
  fetchAiExecutorRunners,
  fetchManagementProducts,
  fetchProductGitRepositoryRecords,
  fetchRdTaskExecutorPolicies,
  fetchRdTaskExecutorPolicyList,
  updateRdTaskExecutorPolicy,
  type AiExecutorRunnerRecord,
  type RdTaskExecutorPolicyRecord,
  type RemoteListPerformance,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { formatMutationError } from '../../utils/managementCrud';

type PolicyFormValues = {
  branch?: string;
  code_change_review_mode: string;
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

type RdTaskExecutorPolicyRow = RdTaskExecutorPolicyRecord & Record<string, unknown>;

type PolicyHitHint = {
  color: string;
  description: string;
  label: string;
};

type ModalPolicyPreview = {
  detail?: string;
  message: string;
  type: 'info' | 'success' | 'warning';
  warning?: string;
};

const LEGACY_CODE_INSPECTION_REMEDIATION_TYPE = 'code_inspection_remediation';

const TASK_TYPE_LABEL_OPTIONS = [
  { label: 'PRD / 原型 / 产品详细设计', value: 'product_detail_design' },
  { label: '技术方案设计', value: 'technical_solution' },
  { label: '代码实现 / 开发计划', value: 'development_planning' },
  { label: '代码评审', value: 'code_review' },
  { label: '自动化测试', value: 'automated_testing' },
  { label: '代码巡检整改', value: LEGACY_CODE_INSPECTION_REMEDIATION_TYPE },
  { label: 'Bug 修复', value: 'bug_fix' },
  { label: '发布上线评估', value: 'release_readiness' },
  { label: '上线后分析', value: 'post_release_analysis' },
];

const TASK_TYPE_OPTIONS = TASK_TYPE_LABEL_OPTIONS.filter(
  (item) => item.value !== LEGACY_CODE_INSPECTION_REMEDIATION_TYPE,
);

const EXECUTOR_OPTIONS = [
  { label: 'Codex', value: 'codex' },
  { label: 'Claude Code', value: 'claude' },
  { label: 'OpenClaw', value: 'openclaw' },
];

const STATUS_OPTIONS = [
  { label: '启用', value: 'active' },
  { label: '停用', value: 'disabled' },
];

const CODE_CHANGE_REVIEW_MODE_OPTIONS = [
  { label: '人工确认', value: 'manual_review' },
  { label: '自动提交代码修改', value: 'auto_commit' },
];

const STATUS_COLORS: Record<string, string> = {
  active: 'green',
  disabled: 'default',
};

function taskTypeLabel(value: string) {
  return TASK_TYPE_LABEL_OPTIONS.find((item) => item.value === value)?.label ?? value;
}

function executorLabel(value: string) {
  return EXECUTOR_OPTIONS.find((item) => item.value === value)?.label ?? value;
}

function codeChangeReviewModeLabel(value: string | undefined) {
  return CODE_CHANGE_REVIEW_MODE_OPTIONS.find((item) => item.value === value)?.label ?? '人工确认';
}

function normalizeProductId(value: string | null | undefined) {
  return String(value ?? '').trim();
}

function productNameLabel(products: ProductRecord[], productId: string | null | undefined) {
  const normalizedProductId = normalizeProductId(productId);
  if (!normalizedProductId) {
    return '未指定产品';
  }
  return products.find((product) => product.id === normalizedProductId)?.name ?? normalizedProductId;
}

function isActivePolicy(policy: Pick<RdTaskExecutorPolicyRecord, 'status'>) {
  return policy.status === 'active';
}

function policyMatchesTask(
  policy: Pick<RdTaskExecutorPolicyRecord, 'product_id' | 'status' | 'task_type'>,
  taskType: string | undefined,
  productId: string | null | undefined,
) {
  if (!taskType || !isActivePolicy(policy) || policy.task_type !== taskType) {
    return false;
  }
  const policyProductId = normalizeProductId(policy.product_id);
  const targetProductId = normalizeProductId(productId);
  return !policyProductId || policyProductId === targetProductId;
}

function sortPoliciesForTask(
  policies: RdTaskExecutorPolicyRecord[],
  taskType: string | undefined,
  productId: string | null | undefined,
) {
  const targetProductId = normalizeProductId(productId);
  return policies
    .filter((policy) => policyMatchesTask(policy, taskType, targetProductId))
    .sort((left, right) => {
      const leftProductId = normalizeProductId(left.product_id);
      const rightProductId = normalizeProductId(right.product_id);
      const leftScopeRank = leftProductId === targetProductId ? 0 : 1;
      const rightScopeRank = rightProductId === targetProductId ? 0 : 1;
      if (leftScopeRank !== rightScopeRank) {
        return leftScopeRank - rightScopeRank;
      }
      if (left.priority !== right.priority) {
        return left.priority - right.priority;
      }
      return left.id.localeCompare(right.id);
    });
}

function samePolicyScope(left: RdTaskExecutorPolicyRecord, right: RdTaskExecutorPolicyRecord) {
  return left.task_type === right.task_type && normalizeProductId(left.product_id) === normalizeProductId(right.product_id);
}

function buildPolicyHitHint(policy: RdTaskExecutorPolicyRecord, policies: RdTaskExecutorPolicyRecord[]): PolicyHitHint {
  if (!isActivePolicy(policy)) {
    return {
      color: 'default',
      description: '停用策略不会参与任务命中',
      label: '不参与',
    };
  }
  const productId = normalizeProductId(policy.product_id);
  const candidates = sortPoliciesForTask(policies, policy.task_type, productId);
  const winner = candidates[0];
  if (winner && winner.id !== policy.id) {
    return {
      color: 'red',
      description: `当前会命中「${winner.name}」`,
      label: '被覆盖',
    };
  }
  const productSpecificCount = policies.filter(
    (candidate) =>
      isActivePolicy(candidate) &&
      candidate.task_type === policy.task_type &&
      normalizeProductId(candidate.product_id),
  ).length;
  if (!productId && productSpecificCount > 0) {
    return {
      color: 'gold',
      description: '同任务类型已有产品专用策略，产品任务会优先命中产品专用策略',
      label: '通用兜底',
    };
  }
  const sameScopeCandidates = candidates.filter((candidate) => samePolicyScope(candidate, policy));
  if (sameScopeCandidates.length > 1) {
    return {
      color: 'blue',
      description: `同范围还有 ${sameScopeCandidates.length - 1} 条候选，按优先级和策略 ID 排序`,
      label: '当前命中',
    };
  }
  return {
    color: 'green',
    description: productId ? '当前产品任务会优先命中该策略' : '未指定产品的任务会命中该通用策略',
    label: '当前命中',
  };
}

function buildModalPolicyPreview({
  currentPolicy,
  policies,
  products,
}: {
  currentPolicy: RdTaskExecutorPolicyRecord;
  policies: RdTaskExecutorPolicyRecord[];
  products: ProductRecord[];
}): ModalPolicyPreview {
  if (!currentPolicy.task_type) {
    return { message: '请选择任务类型后查看命中预览', type: 'info' };
  }
  if (!isActivePolicy(currentPolicy)) {
    return {
      message: '当前表单策略停用，不参与任务命中',
      type: 'warning',
    };
  }
  const productId = normalizeProductId(currentPolicy.product_id);
  const candidates = sortPoliciesForTask(policies, currentPolicy.task_type, productId);
  const winner = candidates[0];
  const samePriorityCandidates = candidates.filter(
    (candidate) =>
      samePolicyScope(candidate, currentPolicy) && candidate.priority === currentPolicy.priority,
  );
  const warning =
    samePriorityCandidates.length > 1
      ? '存在同级策略，priority 相同，保存后会继续按策略 ID 兜底排序，建议调整优先级'
      : undefined;
  if (winner?.id === currentPolicy.id) {
    return {
      detail: productId
        ? `当前配置会优先命中 ${productNameLabel(products, productId)} 的 ${taskTypeLabel(currentPolicy.task_type)} 任务`
        : '当前表单策略将作为通用兜底策略',
      message: '命中预览',
      type: warning ? 'warning' : 'success',
      warning,
    };
  }
  return {
    detail: winner
      ? `当前配置会命中「${winner.name}」，当前表单策略不会被优先命中`
      : '当前没有可命中的启用策略',
    message: '命中预览',
    type: 'warning',
    warning,
  };
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

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildPolicyListQuery(query: ManagementListQuery) {
  return {
    executorType: normalizeFilterText(query.filters.executor_type),
    name: normalizeFilterText(query.filters.name),
    page: query.page,
    pageSize: query.pageSize,
    productName: normalizeFilterText(query.filters.product_name),
    sortField: query.sortField,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
    taskType: normalizeFilterText(query.filters.task_type),
  };
}

export default function RdExecutorPoliciesPage() {
  const [form] = Form.useForm<PolicyFormValues>();
  const [editingPolicy, setEditingPolicy] = useState<RdTaskExecutorPolicyRecord | undefined>();
  const [referenceLoading, setReferenceLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [products, setProducts] = useState<ProductRecord[]>([]);
  const [repositories, setRepositories] = useState<ProductGitRepositoryRecord[]>([]);
  const [runners, setRunners] = useState<AiExecutorRunnerRecord[]>([]);
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'priority',
    sortOrder: 'ascend',
  });
  const [listState, setListState] = useState<{
    page: number;
    pageSize: number;
    performance?: RemoteListPerformance;
    rows: RdTaskExecutorPolicyRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const [policyCandidates, setPolicyCandidates] = useState<RdTaskExecutorPolicyRecord[]>([]);
  const selectedExecutorType = Form.useWatch('executor_type', form);
  const watchedCodeChangeReviewMode = Form.useWatch('code_change_review_mode', form);
  const watchedName = Form.useWatch('name', form);
  const watchedPriority = Form.useWatch('priority', form);
  const watchedProductId = Form.useWatch('product_id', form);
  const watchedStatus = Form.useWatch('status', form);
  const watchedTaskType = Form.useWatch('task_type', form);

  const loadReferences = useCallback(async () => {
    setReferenceLoading(true);
    try {
      const [nextProducts, nextRunners] = await Promise.all([
        fetchManagementProducts(),
        fetchAiExecutorRunners({ status: 'active' }),
      ]);
      setProducts(nextProducts);
      setRunners(nextRunners.filter((runner) => runner.id !== 'ai_executor_runner_system_default'));
    } catch (error) {
      message.error(mutationError(error, '加载研发执行器策略配置资源失败'));
    } finally {
      setReferenceLoading(false);
    }
  }, []);

  const loadPolicies = useCallback(async (query: ManagementListQuery) => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchRdTaskExecutorPolicyList(buildPolicyListQuery(query));
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
      message.error(mutationError(error, '加载研发执行器策略失败'));
    }
  }, []);

  const loadPolicyCandidates = useCallback(async () => {
    try {
      setPolicyCandidates(await fetchRdTaskExecutorPolicies());
    } catch (error) {
      message.error(mutationError(error, '加载研发执行器策略命中预览失败'));
    }
  }, []);

  const reload = useCallback(async () => {
    await Promise.all([loadPolicies(listQuery), loadPolicyCandidates(), loadReferences()]);
  }, [listQuery, loadPolicies, loadPolicyCandidates, loadReferences]);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) {
        void loadReferences();
      }
    });
    return () => {
      cancelled = true;
    };
  }, [loadReferences]);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) {
        void loadPolicies(listQuery);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [listQuery, loadPolicies]);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) {
        void loadPolicyCandidates();
      }
    });
    return () => {
      cancelled = true;
    };
  }, [loadPolicyCandidates]);

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
  const conflictPolicies = policyCandidates.length ? policyCandidates : listState.rows;
  const modalPreview = useMemo(() => {
    const currentPolicy: RdTaskExecutorPolicyRecord = {
      code_change_review_mode: watchedCodeChangeReviewMode ?? 'manual_review',
      executor_type: selectedExecutorType ?? 'codex',
      id: editingPolicy?.id ?? '__current_form_policy__',
      instruction_template: '',
      name: String(watchedName || '').trim() || '当前表单策略',
      priority: Number(watchedPriority || 100),
      product_id: watchedProductId || null,
      status: watchedStatus || 'active',
      task_type: watchedTaskType || '',
      timeout_seconds: 1800,
      workspace_root: '',
    };
    const nextPolicies = [
      ...conflictPolicies.filter((policy) => policy.id !== editingPolicy?.id),
      currentPolicy,
    ];
    return buildModalPolicyPreview({
      currentPolicy,
      policies: nextPolicies,
      products,
    });
  }, [
    conflictPolicies,
    editingPolicy?.id,
    products,
    selectedExecutorType,
    watchedCodeChangeReviewMode,
    watchedName,
    watchedPriority,
    watchedProductId,
    watchedStatus,
    watchedTaskType,
  ]);
  const taskTypeOptions = useMemo(() => {
    if (editingPolicy?.task_type !== LEGACY_CODE_INSPECTION_REMEDIATION_TYPE) {
      return TASK_TYPE_OPTIONS;
    }
    return [
      {
        disabled: true,
        label: '代码巡检整改（历史兼容，建议改用 Bug 修复）',
        value: LEGACY_CODE_INSPECTION_REMEDIATION_TYPE,
      },
      ...TASK_TYPE_OPTIONS,
    ];
  }, [editingPolicy?.task_type]);

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
      code_change_review_mode: 'manual_review',
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
      code_change_review_mode: policy.code_change_review_mode ?? 'manual_review',
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
        code_change_review_mode: values.code_change_review_mode,
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
      await Promise.all([loadPolicies(listQuery), loadPolicyCandidates()]);
    } catch (error) {
      message.error(mutationError(error, '保存研发执行器策略失败'));
    }
  };

  const removePolicy = async (policy: RdTaskExecutorPolicyRecord) => {
    try {
      await deleteRdTaskExecutorPolicy(policy.id);
      message.success('研发执行器策略已删除');
      await Promise.all([loadPolicies(listQuery), loadPolicyCandidates()]);
    } catch (error) {
      message.error(mutationError(error, '删除研发执行器策略失败'));
    }
  };

  const columns: ProColumns<RdTaskExecutorPolicyRow>[] = [
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
      dataIndex: 'code_change_review_mode',
      render: (_, row) => (
        <Tag color={row.code_change_review_mode === 'auto_commit' ? 'green' : 'gold'}>
          {codeChangeReviewModeLabel(row.code_change_review_mode)}
        </Tag>
      ),
      title: '代码提交方式',
      width: 160,
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
      dataIndex: 'policy_hit_hint',
      render: (_, row) => {
        const hint = buildPolicyHitHint(row, conflictPolicies);
        return (
          <Space orientation="vertical" size={2}>
            <Tag color={hint.color}>{hint.label}</Tag>
            <span style={{ color: 'rgba(0, 0, 0, 0.45)', fontSize: 12 }}>{hint.description}</span>
          </Space>
        );
      },
      title: '命中提示',
      width: 260,
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
    <>
      <ManagementListPage<RdTaskExecutorPolicyRow>
        breadcrumbGroup="需求交付"
        columns={columns}
        dataSource={listState.rows as RdTaskExecutorPolicyRow[]}
        viewStorageKey="delivery.rd_executor_policies"
        filters={[
          { label: '策略名称', name: 'name', type: 'text' },
          { label: '任务类型', name: 'task_type', options: taskTypeOptions, type: 'select' },
          { label: '执行器', name: 'executor_type', options: EXECUTOR_OPTIONS, type: 'select' },
          { label: '产品', name: 'product_name', type: 'text' },
          { label: '状态', name: 'status', options: STATUS_OPTIONS, type: 'select' },
        ]}
        loading={referenceLoading || listState.status === 'loading'}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="新增策略"
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="id"
        tableLayout="fixed"
        tableScroll={{ x: 2290 }}
        tableTitle="研发执行器策略"
        title="研发执行器策略"
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
            <Select optionFilterProp="label" options={taskTypeOptions} showSearch />
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
          <Form.Item
            label="代码提交方式"
            name="code_change_review_mode"
            rules={[{ required: true, message: '请选择代码提交方式' }]}
          >
            <Select options={CODE_CHANGE_REVIEW_MODE_OPTIONS} />
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
          <Form.Item label="策略预览">
            <Alert
              description={
                <Space orientation="vertical" size={4}>
                  {modalPreview.detail ? <span>{modalPreview.detail}</span> : null}
                  {modalPreview.warning ? <span>{modalPreview.warning}</span> : null}
                </Space>
              }
              showIcon
              title={modalPreview.message}
              type={modalPreview.type}
            />
          </Form.Item>
          <Form.Item label="指令模板" name="instruction_template" rules={[{ required: true, message: '请输入指令模板' }]}>
            <Input.TextArea rows={5} />
          </Form.Item>
          <Form.Item label="输出契约" name="output_contract_json">
            <Input.TextArea rows={5} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
