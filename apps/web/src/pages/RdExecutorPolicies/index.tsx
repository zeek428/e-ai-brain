import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  createRdDeliveryPolicy,
  fetchRdAiEmployees,
  fetchRdDeliveryPolicies,
  fetchRdExecutorProfiles,
  fetchRdRoles,
  updateRdDeliveryPolicy,
  type RdAiEmployee,
  type RdDeliveryPolicy,
  type RdDeliveryPolicyPayload,
  type RdExecutorProfile,
  type RdPolicyRoleBinding,
  type RdRoleDefinition,
} from '../../services/rdCollaborationClient';
import { formatMutationError } from '../../utils/managementCrud';
import { AiEmployeeCatalog } from './AiEmployeeCatalog';
import { PolicyRoleBindings } from './PolicyRoleBindings';

type PolicyFormValues = {
  deliveryTarget: 'ready_for_release';
  name: string;
  productId?: string;
  status: 'active' | 'disabled';
  taskTypes: string[];
};

type PolicyEditorState = {
  bindings: RdPolicyRoleBinding[];
  policy?: RdDeliveryPolicy;
};

const taskTypeOptions = [
  { label: '需求评估', value: 'requirement_assessment' },
  { label: '迭代归组', value: 'iteration_grouping' },
  { label: '技术方案', value: 'technical_solution' },
  { label: '开发实现', value: 'development_planning' },
  { label: '自动化测试', value: 'automated_testing' },
  { label: '代码评审', value: 'code_review' },
];

function buildPayload(values: PolicyFormValues, bindings: RdPolicyRoleBinding[]): RdDeliveryPolicyPayload {
  const requiredRoleCodes = bindings
    .filter((binding) => binding.status === 'active')
    .map((binding) => binding.role_code);
  return {
    assessment_config: {
      llm_role: 'proposal_only',
      require_human_confirmation_for: ['high', 'critical'],
    },
    autonomy_config: {
      low_risk: 'policy_auto',
      high_risk: 'human_decision_required',
      state_transition_owner: 'deterministic_control_plane',
    },
    brain_app_id: 'rd_brain',
    delivery_target: values.deliveryTarget,
    deployment_config: { enabled: false },
    experience_reuse_config: {
      enabled: true,
      max_context_tokens: 2000,
      max_items: 5,
      policy_compatibility: 'same_policy_schema',
      require_independent_reviewer: true,
    },
    git_config: {
      delivery_evidence_required: true,
      push_remote: true,
      prohibit_deployment: true,
    },
    iteration_config: {
      create_when_no_compatible_planning_version: true,
      prefer_compatible_planning_version: true,
      require_human_decision_on_tie: true,
    },
    matching_config: {
      task_types: values.taskTypes,
    },
    name: values.name.trim(),
    product_id: values.productId?.trim() || null,
    quality_gate_config: {
      require_code_review: true,
      require_test_evidence: true,
      require_trusted_remote_push: true,
    },
    role_bindings: bindings,
    status: values.status,
    team_config: { required_role_codes: requiredRoleCodes },
  };
}

function initialFormValues(policy?: RdDeliveryPolicy): PolicyFormValues {
  return {
    deliveryTarget: 'ready_for_release',
    name: policy?.name ?? '',
    productId: policy?.product_id ?? undefined,
    status: policy?.status ?? 'active',
    taskTypes: Array.isArray(policy?.matching_config?.task_types)
      ? policy.matching_config.task_types.filter((item): item is string => typeof item === 'string')
      : ['requirement_assessment', 'iteration_grouping', 'development_planning', 'automated_testing'],
  };
}

function policyTargetTag(policy: RdDeliveryPolicy) {
  return policy.delivery_target === 'ready_for_release'
    ? <Tag color="blue">推送远程仓库并待发布</Tag>
    : <Tag color="default">不在当前交付范围</Tag>;
}

export default function RdExecutorPoliciesPage() {
  const [form] = Form.useForm<PolicyFormValues>();
  const [policies, setPolicies] = useState<RdDeliveryPolicy[]>([]);
  const [roles, setRoles] = useState<RdRoleDefinition[]>([]);
  const [aiEmployees, setAiEmployees] = useState<RdAiEmployee[]>([]);
  const [profiles, setProfiles] = useState<RdExecutorProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string>();
  const [editor, setEditor] = useState<PolicyEditorState>();
  const [saving, setSaving] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setLoadError(undefined);
    try {
      const [nextPolicies, nextRoles, nextEmployees, nextProfiles] = await Promise.all([
        fetchRdDeliveryPolicies(),
        fetchRdRoles(),
        fetchRdAiEmployees(),
        fetchRdExecutorProfiles(),
      ]);
      setPolicies(nextPolicies);
      setRoles(nextRoles);
      setAiEmployees(nextEmployees);
      setProfiles(nextProfiles);
    } catch (error) {
      setLoadError(formatMutationError(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = globalThis.setTimeout(() => void reload(), 0);
    return () => globalThis.clearTimeout(timer);
  }, [reload]);

  const activePolicies = useMemo(
    () => policies.filter((policy) => policy.status === 'active'),
    [policies],
  );

  const openEditor = (policy?: RdDeliveryPolicy) => {
    form.setFieldsValue(initialFormValues(policy));
    setEditor({ bindings: Array.isArray(policy?.role_bindings) ? policy.role_bindings : [], policy });
  };

  const savePolicy = async () => {
    if (!editor) {
      return;
    }
    const values = await form.validateFields();
    if (!editor.bindings.length) {
      message.warning('请至少配置一个岗位责任主体');
      return;
    }
    setSaving(true);
    try {
      const payload = buildPayload(values, editor.bindings);
      const saved = editor.policy
        ? await updateRdDeliveryPolicy(editor.policy.id, editor.policy.policy_version, payload)
        : await createRdDeliveryPolicy(payload);
      setPolicies((current) => {
        const withoutSaved = current.filter((policy) => policy.id !== saved.id);
        return [...withoutSaved, saved];
      });
      message.success(editor.policy ? '研发执行策略已更新并形成新版本' : '研发执行策略已创建');
      setEditor(undefined);
    } catch (error) {
      message.error(formatMutationError(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <main>
      <Typography.Title level={2}>统一研发执行策略</Typography.Title>
      <Typography.Paragraph type="secondary">
        一套策略覆盖需求评估、优先归组、开发、测试、审核与远程推送。LLM 只生成建议和计划；工作项、依赖、权限、人工关卡与状态转换由确定性控制平面执行。
      </Typography.Paragraph>
      <Alert
        showIcon
        type="info"
        title="当前交付边界：开发、测试、代码审核、可信远程推送与待发布证据。部署默认禁用，不会由本页面或协同流程触发。"
      />
      {loadError ? (
        <Alert
          action={<Button size="small" onClick={() => void reload()}>重试</Button>}
        title={loadError}
          style={{ marginTop: 16 }}
          type="error"
        />
      ) : null}
      <Card style={{ marginTop: 16 }}>
        <Tabs
          items={[
            {
              key: 'policies',
              label: `交付策略（${policies.length}）`,
              children: loading ? <Spin /> : (
                <>
                  <Space style={{ marginBottom: 12 }}>
                    <Button type="primary" onClick={() => openEditor()}>新增研发执行策略</Button>
                    <Button onClick={() => void reload()}>刷新</Button>
                    <Typography.Text type="secondary">启用中：{activePolicies.length}</Typography.Text>
                  </Space>
                  <Table
                    dataSource={policies}
                    pagination={false}
                    rowKey="id"
                    columns={[
                      { dataIndex: 'name', title: '策略名称' },
                      {
                        dataIndex: 'matching_config',
                        title: '适用任务',
                        render: (config: Record<string, unknown>) =>
                          Array.isArray(config?.task_types)
                            ? config.task_types.map((taskType) => <Tag key={String(taskType)}>{String(taskType)}</Tag>)
                            : '-',
                      },
                      {
                        dataIndex: 'role_bindings',
                        title: '岗位责任',
                        render: (bindings: unknown) => {
                          if (!Array.isArray(bindings)) {
                            return '-';
                          }
                          return bindings.map((binding) => {
                            const roleCode = typeof binding?.role_code === 'string' ? binding.role_code : '未配置岗位';
                            return <Tag key={roleCode}>{roleCode}</Tag>;
                          });
                        },
                      },
                      { title: '交付终点', render: (_, policy: RdDeliveryPolicy) => policyTargetTag(policy) },
                      { dataIndex: 'policy_version', title: '版本', render: (version: number) => `v${version}` },
                      {
                        dataIndex: 'status',
                        title: '状态',
                        render: (status: string) => <Tag color={status === 'active' ? 'green' : 'default'}>{status === 'active' ? '启用' : '停用'}</Tag>,
                      },
                      { title: '操作', render: (_, policy: RdDeliveryPolicy) => <Button type="link" onClick={() => openEditor(policy)}>编辑</Button> },
                    ]}
                  />
                </>
              ),
            },
            {
              key: 'employees',
              label: `AI 数字员工（${aiEmployees.length}）`,
              children: loading ? <Spin /> : (
                <AiEmployeeCatalog
                  employees={aiEmployees}
                  onCreated={(employee) => setAiEmployees((current) => [...current, employee])}
                />
              ),
            },
          ]}
        />
      </Card>
      <Modal
        destroyOnHidden
        open={Boolean(editor)}
        title={editor?.policy ? '编辑统一研发执行策略' : '新增统一研发执行策略'}
        width={900}
        confirmLoading={saving}
        onCancel={() => setEditor(undefined)}
        onOk={() => void savePolicy()}
      >
        <Form form={form} layout="vertical">
          <Form.Item label="策略名称" name="name" rules={[{ required: true, whitespace: true }]}>
            <Input placeholder="例如：研发团队标准交付策略" />
          </Form.Item>
          <Form.Item label="产品 ID（留空表示全局策略）" name="productId">
            <Input />
          </Form.Item>
          <Form.Item label="适用任务" name="taskTypes" rules={[{ required: true, type: 'array', min: 1 }]}>
            <Select mode="multiple" options={taskTypeOptions} />
          </Form.Item>
          <Form.Item label="策略状态" name="status" rules={[{ required: true }]}>
            <Select options={[{ label: '启用', value: 'active' }, { label: '停用', value: 'disabled' }]} />
          </Form.Item>
          <Form.Item label="交付终点" name="deliveryTarget">
            <Select disabled options={[{ label: '推送远程仓库并待发布', value: 'ready_for_release' }]} />
          </Form.Item>
        </Form>
        <PolicyRoleBindings
          aiEmployees={aiEmployees}
          executorProfiles={profiles}
          roles={roles}
          value={editor?.bindings}
          onChange={(bindings) => setEditor((current) => current ? { ...current, bindings } : current)}
          onRoleCreated={(role) => setRoles((current) => [...current, role])}
        />
      </Modal>
    </main>
  );
}
