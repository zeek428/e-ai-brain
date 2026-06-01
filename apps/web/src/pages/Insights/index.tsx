import type { ProColumns } from '@ant-design/pro-components';
import { Button, Checkbox, Form, Input, Modal, Select, Space } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ProductContextOption } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createIterationSuggestions,
  createUserFeedback,
  createUserUsageMetric,
  decideIterationSuggestion,
  fetchProductContextOptions,
  fetchUserInsights,
  updateUserFeedback,
  type IterationSuggestionCreatePayload,
  type IterationSuggestionDecisionPayload,
  type UserFeedbackCreatePayload,
  type UserInsightRecord,
  type UserUsageMetricCreatePayload,
} from '../../services/aiBrain';

type FeedbackFormValues = {
  content: string;
  feedbackType: string;
  productId: string;
  sourceChannel?: string;
};

type TriageFormValues = {
  status: string;
  triageNote?: string;
};

type UsageMetricFormValues = {
  activeUsers?: string;
  avgDurationSeconds?: string;
  bounceRate?: string;
  conversionCount?: string;
  conversionRate?: string;
  errorCount?: string;
  eventCount?: string;
  featureCode: string;
  moduleCode?: string;
  productId: string;
  sourceChannel?: string;
  userSegment?: string;
  windowEnd: string;
  windowStart: string;
};

function optionalNonNegativeNumberRule(label: string, max?: number) {
  return {
    validator: async (_: unknown, value?: string) => {
      const trimmed = value?.trim();
      if (!trimmed) {
        return;
      }
      const parsed = Number(trimmed);
      if (!Number.isFinite(parsed) || parsed < 0 || (max !== undefined && parsed > max)) {
        throw new Error(`${label}请输入${max === 1 ? '0 到 1 之间的' : '非负'}数字`);
      }
    },
  };
}

function optionalNonNegativeIntegerRule(label: string) {
  return {
    validator: async (_: unknown, value?: string) => {
      const trimmed = value?.trim();
      if (!trimmed) {
        return;
      }
      const parsed = Number(trimmed);
      if (!Number.isInteger(parsed) || parsed < 0) {
        throw new Error(`${label}请输入非负整数`);
      }
    },
  };
}

type SuggestionFormValues = {
  planningCycle: string;
  productId: string;
  versionId: string;
};

type DecisionFormValues = {
  comment?: string;
  convertToRequirement?: boolean;
  decision: string;
  editedScope?: string;
  editedTitle?: string;
};

const feedbackTypeOptions = [
  { label: '改进建议', value: 'improvement' },
  { label: '问题反馈', value: 'bug' },
  { label: '咨询问题', value: 'question' },
  { label: '投诉', value: 'complaint' },
  { label: '表扬', value: 'praise' },
];

const feedbackStatusOptions = [
  { label: '待处理', value: 'open' },
  { label: '已分诊', value: 'triaged' },
  { label: '已关联', value: 'linked' },
  { label: '已解决', value: 'resolved' },
  { label: '已归档', value: 'archived' },
];

const iterationDecisionOptions = [
  { label: '采纳', value: 'accepted' },
  { label: '修改后采纳', value: 'edited_accepted' },
  { label: '驳回', value: 'rejected' },
];

function buildFeedbackPayload(values: FeedbackFormValues): UserFeedbackCreatePayload {
  return {
    content: values.content.trim(),
    feedback_type: values.feedbackType,
    product_id: values.productId,
    source_channel: values.sourceChannel?.trim() || 'in_app',
  };
}

function buildSuggestionPayload(values: SuggestionFormValues): IterationSuggestionCreatePayload {
  return {
    constraints: { max_suggestions: 10 },
    planning_cycle: values.planningCycle.trim(),
    product_id: values.productId,
    version_id: values.versionId,
  };
}

function optionalNumber(value?: string) {
  const trimmed = value?.trim();
  if (!trimmed) {
    return undefined;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function numberOrZero(value?: string) {
  return optionalNumber(value) ?? 0;
}

function buildUsageMetricPayload(values: UsageMetricFormValues): UserUsageMetricCreatePayload {
  return {
    active_users: numberOrZero(values.activeUsers),
    avg_duration_seconds: optionalNumber(values.avgDurationSeconds),
    bounce_rate: optionalNumber(values.bounceRate),
    conversion_count: numberOrZero(values.conversionCount),
    conversion_rate: optionalNumber(values.conversionRate),
    error_count: numberOrZero(values.errorCount),
    event_count: numberOrZero(values.eventCount),
    feature_code: values.featureCode.trim(),
    module_code: values.moduleCode?.trim() || undefined,
    product_id: values.productId,
    source_channel: values.sourceChannel?.trim() || 'manual_import',
    user_segment: values.userSegment?.trim() || 'all',
    window_end: values.windowEnd.trim(),
    window_start: values.windowStart.trim(),
  };
}

function buildDecisionPayload(values: DecisionFormValues): IterationSuggestionDecisionPayload {
  const convertToRequirement = Boolean(values.convertToRequirement && values.decision !== 'rejected');
  return {
    comment: values.comment?.trim() || undefined,
    convert_to_requirement: convertToRequirement,
    decision: values.decision,
    edited_scope: convertToRequirement ? values.editedScope?.trim() || undefined : undefined,
    edited_title: convertToRequirement ? values.editedTitle?.trim() || undefined : undefined,
  };
}

function statusColor(status: string) {
  if (
    status === 'accepted' ||
    status === 'archived' ||
    status === 'converted_to_requirement' ||
    status === 'resolved'
  ) {
    return 'green';
  }
  if (status === 'open') {
    return 'blue';
  }
  if (status === 'rejected') {
    return 'red';
  }
  return status === '-' ? 'default' : 'gold';
}

function useProductContexts() {
  const [products, setProducts] = useState<ProductContextOption[]>([]);

  useEffect(() => {
    let mounted = true;
    void fetchProductContextOptions()
      .then((items) => {
        if (mounted) {
          setProducts(items);
        }
      })
      .catch(() => {
        if (mounted) {
          setProducts([]);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  return products;
}

function productOptionsFromContexts(productContexts: ProductContextOption[]) {
  return productContexts.map((product) => ({
    label: product.name,
    value: product.id,
  }));
}

function versionOptionsFromContexts(productContexts: ProductContextOption[], productId?: string) {
  return (
    productContexts
      .find((product) => product.id === productId)
      ?.versions.map((version) => ({
        label: version.name,
        value: version.id,
      })) ?? []
  );
}

function useInsightColumns(
  onDecide: (row: UserInsightRecord) => void,
  onTriage: (row: UserInsightRecord) => void,
) {
  return useMemo<ProColumns<UserInsightRecord>[]>(
    () => [
      {
        dataIndex: 'category',
        title: '数据类型',
      },
      {
        dataIndex: 'summary',
        title: '摘要',
      },
      {
        dataIndex: 'owner',
        title: '归属用户',
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) => <StatusTag color={statusColor(row.status)} label={row.status} />,
      },
      {
        dataIndex: 'updatedAt',
        title: '更新时间',
      },
      {
        key: 'actions',
        render: (_, row) => {
          if (row.category === '用户反馈') {
            return (
              <Button onClick={() => onTriage(row)} size="small" type="link">
                处理反馈
              </Button>
            );
          }
          if (row.category === '迭代建议' && row.status === 'suggested') {
            return (
              <Button onClick={() => onDecide(row)} size="small" type="link">
                确认建议
              </Button>
            );
          }
          return null;
        },
        title: '操作',
      },
    ],
    [onDecide, onTriage],
  );
}

export default function InsightsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [decisionTarget, setDecisionTarget] = useState<UserInsightRecord | null>(null);
  const [suggestionOpen, setSuggestionOpen] = useState(false);
  const [triageTarget, setTriageTarget] = useState<UserInsightRecord | null>(null);
  const [usageOpen, setUsageOpen] = useState(false);
  const [createForm] = Form.useForm<FeedbackFormValues>();
  const [decisionForm] = Form.useForm<DecisionFormValues>();
  const [suggestionForm] = Form.useForm<SuggestionFormValues>();
  const [triageForm] = Form.useForm<TriageFormValues>();
  const [usageForm] = Form.useForm<UsageMetricFormValues>();
  const productContexts = useProductContexts();
  const productOptions = useMemo(() => productOptionsFromContexts(productContexts), [productContexts]);
  const suggestionProductId = Form.useWatch('productId', suggestionForm);
  const decisionValue = Form.useWatch('decision', decisionForm);
  const convertToRequirement = Form.useWatch('convertToRequirement', decisionForm);
  const versionOptions = useMemo(
    () => versionOptionsFromContexts(productContexts, suggestionProductId),
    [productContexts, suggestionProductId],
  );
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(fetchUserInsights);
  const columns = useInsightColumns(
    (row) => {
      setDecisionTarget(row);
      decisionForm.setFieldsValue({
        comment: undefined,
        convertToRequirement: false,
        decision: 'edited_accepted',
        editedScope: undefined,
        editedTitle: undefined,
      });
    },
    (row) => {
      setTriageTarget(row);
      triageForm.setFieldsValue({
        status: row.status === '-' || row.status === 'open' ? 'triaged' : row.status,
        triageNote: undefined,
      });
    },
  );

  useEffect(() => {
    if (!createOpen || productOptions.length !== 1 || createForm.getFieldValue('productId')) {
      return;
    }
    createForm.setFieldValue('productId', productOptions[0]?.value);
  }, [createForm, createOpen, productOptions]);

  useEffect(() => {
    if (!usageOpen || productOptions.length !== 1 || usageForm.getFieldValue('productId')) {
      return;
    }
    usageForm.setFieldValue('productId', productOptions[0]?.value);
  }, [productOptions, usageForm, usageOpen]);

  useEffect(() => {
    if (!suggestionOpen || productOptions.length !== 1 || suggestionForm.getFieldValue('productId')) {
      return;
    }
    suggestionForm.setFieldValue('productId', productOptions[0]?.value);
  }, [productOptions, suggestionForm, suggestionOpen]);

  useEffect(() => {
    if (!suggestionOpen || versionOptions.length !== 1 || suggestionForm.getFieldValue('versionId')) {
      return;
    }
    suggestionForm.setFieldValue('versionId', versionOptions[0]?.value);
  }, [suggestionForm, suggestionOpen, versionOptions]);

  useEffect(() => {
    if (decisionValue === 'rejected' && decisionForm.getFieldValue('convertToRequirement')) {
      decisionForm.setFieldValue('convertToRequirement', false);
    }
  }, [decisionForm, decisionValue]);

  const submitFeedback = async () => {
    const values = await createForm.validateFields();
    await createUserFeedback(buildFeedbackPayload(values));
    setCreateOpen(false);
    createForm.resetFields();
    await reload();
  };

  const submitSuggestion = async () => {
    const values = await suggestionForm.validateFields();
    await createIterationSuggestions(buildSuggestionPayload(values));
    setSuggestionOpen(false);
    suggestionForm.resetFields();
    await reload();
  };

  const submitUsageMetric = async () => {
    const values = await usageForm.validateFields();
    await createUserUsageMetric(buildUsageMetricPayload(values));
    setUsageOpen(false);
    usageForm.resetFields();
    await reload();
  };

  const submitTriage = async () => {
    if (!triageTarget) {
      return;
    }
    const values = await triageForm.validateFields();
    await updateUserFeedback(triageTarget.id, {
      status: values.status,
      triage_note: values.triageNote?.trim() || undefined,
    });
    setTriageTarget(null);
    triageForm.resetFields();
    await reload();
  };

  const submitDecision = async () => {
    if (!decisionTarget) {
      return;
    }
    const values = await decisionForm.validateFields();
    await decideIterationSuggestion(decisionTarget.id, buildDecisionPayload(values));
    setDecisionTarget(null);
    decisionForm.resetFields();
    await reload();
  };

  return (
    <>
      <ManagementListPage<UserInsightRecord>
        breadcrumbGroup="运营治理"
        columns={columns}
        dataSource={dataSource}
        filters={[
          {
            label: '数据类型',
            name: 'category',
            options: [
              { label: '使用趋势', value: '使用趋势' },
              { label: '用户反馈', value: '用户反馈' },
              { label: '迭代建议', value: '迭代建议' },
            ],
            type: 'select',
          },
          { label: '摘要', name: 'summary', type: 'text' },
          { label: '状态', name: 'status', type: 'text' },
        ]}
        loading={status === 'loading'}
        notice={formatRemoteRowsError(error)}
        onPrimaryAction={() => setCreateOpen(true)}
        onReload={() => void reload()}
        primaryAction="登记反馈"
        rowKey="id"
        tableTitle="用户洞察/迭代规划"
        title="用户洞察/迭代规划"
        toolbarActions={[
          <Button aria-label="登记使用指标" key="usage" onClick={() => setUsageOpen(true)}>
            登记使用指标
          </Button>,
          <Button aria-label="生成迭代建议" key="suggestion" onClick={() => setSuggestionOpen(true)}>
            生成迭代建议
          </Button>,
        ]}
      />
      <Modal
        destroyOnHidden
        okText="保存"
        okButtonProps={{ 'aria-label': '保存' }}
        onCancel={() => setSuggestionOpen(false)}
        onOk={() => void submitSuggestion()}
        open={suggestionOpen}
        title="生成迭代建议"
      >
        <Form<SuggestionFormValues> form={suggestionForm} layout="vertical">
          <Form.Item label="所属产品" name="productId" rules={[{ required: true, message: '请选择所属产品' }]}>
            <Select options={productOptions} />
          </Form.Item>
          <Form.Item label="目标版本" name="versionId" rules={[{ required: true, message: '请选择目标版本' }]}>
            <Select options={versionOptions} />
          </Form.Item>
          <Form.Item label="规划周期" name="planningCycle" rules={[{ required: true, message: '请输入规划周期' }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        okText="保存"
        okButtonProps={{ 'aria-label': '保存' }}
        onCancel={() => setUsageOpen(false)}
        onOk={() => void submitUsageMetric()}
        open={usageOpen}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
        title="登记使用指标"
      >
        <Form<UsageMetricFormValues>
          form={usageForm}
          initialValues={{ sourceChannel: 'manual_import', userSegment: 'all' }}
          layout="vertical"
        >
          <Form.Item label="所属产品" name="productId" rules={[{ required: true, message: '请选择所属产品' }]}>
            <Select options={productOptions} />
          </Form.Item>
          <Form.Item label="模块编码" name="moduleCode">
            <Input />
          </Form.Item>
          <Form.Item label="功能编码" name="featureCode" rules={[{ required: true, message: '请输入功能编码' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="用户分群" name="userSegment">
            <Input />
          </Form.Item>
          <Form.Item label="窗口开始" name="windowStart" rules={[{ required: true, message: '请输入窗口开始时间' }]}>
            <Input placeholder="2026-06-01T00:00:00Z" />
          </Form.Item>
          <Form.Item label="窗口结束" name="windowEnd" rules={[{ required: true, message: '请输入窗口结束时间' }]}>
            <Input placeholder="2026-06-01T01:00:00Z" />
          </Form.Item>
          <Form.Item label="活跃用户" name="activeUsers" rules={[optionalNonNegativeIntegerRule('活跃用户')]}>
            <Input />
          </Form.Item>
          <Form.Item label="事件次数" name="eventCount" rules={[optionalNonNegativeIntegerRule('事件次数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="转化次数" name="conversionCount" rules={[optionalNonNegativeIntegerRule('转化次数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="转化率" name="conversionRate" rules={[optionalNonNegativeNumberRule('转化率', 1)]}>
            <Input placeholder="0.36" />
          </Form.Item>
          <Form.Item label="平均时长秒" name="avgDurationSeconds" rules={[optionalNonNegativeNumberRule('平均时长秒')]}>
            <Input />
          </Form.Item>
          <Form.Item label="跳出率" name="bounceRate" rules={[optionalNonNegativeNumberRule('跳出率', 1)]}>
            <Input placeholder="0.18" />
          </Form.Item>
          <Form.Item label="错误次数" name="errorCount" rules={[optionalNonNegativeIntegerRule('错误次数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="来源渠道" name="sourceChannel">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        okText="保存"
        okButtonProps={{ 'aria-label': '保存' }}
        onCancel={() => setCreateOpen(false)}
        onOk={() => void submitFeedback()}
        open={createOpen}
        title="登记用户反馈"
      >
        <Form<FeedbackFormValues>
          form={createForm}
          initialValues={{ feedbackType: 'improvement', sourceChannel: 'in_app' }}
          layout="vertical"
        >
          <Form.Item label="所属产品" name="productId" rules={[{ required: true, message: '请选择所属产品' }]}>
            <Select options={productOptions} />
          </Form.Item>
          <Form.Item label="反馈类型" name="feedbackType" rules={[{ required: true, message: '请选择反馈类型' }]}>
            <Select options={feedbackTypeOptions} />
          </Form.Item>
          <Form.Item label="反馈内容" name="content" rules={[{ required: true, message: '请输入反馈内容' }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        okText="保存"
        okButtonProps={{ 'aria-label': '保存' }}
        onCancel={() => setTriageTarget(null)}
        onOk={() => void submitTriage()}
        open={Boolean(triageTarget)}
        title="处理用户反馈"
      >
        <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
          <div>{triageTarget?.summary}</div>
          <Form<TriageFormValues> form={triageForm} layout="vertical">
            <Form.Item label="处理状态" name="status" rules={[{ required: true, message: '请选择处理状态' }]}>
              <Select options={feedbackStatusOptions} />
            </Form.Item>
            <Form.Item label="处理备注" name="triageNote">
              <Input.TextArea rows={3} />
            </Form.Item>
          </Form>
        </Space>
      </Modal>
      <Modal
        destroyOnHidden
        okText="保存"
        okButtonProps={{ 'aria-label': '保存' }}
        onCancel={() => setDecisionTarget(null)}
        onOk={() => void submitDecision()}
        open={Boolean(decisionTarget)}
        title="确认迭代建议"
      >
        <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
          <div>{decisionTarget?.summary}</div>
          <Form<DecisionFormValues> form={decisionForm} layout="vertical">
            <Form.Item label="确认结论" name="decision" rules={[{ required: true, message: '请选择确认结论' }]}>
              <Select options={iterationDecisionOptions} />
            </Form.Item>
            <Form.Item label="确认备注" name="comment">
              <Input.TextArea rows={3} />
            </Form.Item>
            <Form.Item name="convertToRequirement" valuePropName="checked">
              <Checkbox disabled={decisionValue === 'rejected'}>转为正式需求</Checkbox>
            </Form.Item>
            {convertToRequirement ? (
              <>
                <Form.Item label="需求标题" name="editedTitle">
                  <Input />
                </Form.Item>
                <Form.Item label="需求范围" name="editedScope">
                  <Input.TextArea rows={3} />
                </Form.Item>
              </>
            ) : null}
          </Form>
        </Space>
      </Modal>
    </>
  );
}
