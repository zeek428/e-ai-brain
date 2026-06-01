import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Select, Space } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ProductRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createUserFeedback,
  fetchManagementProducts,
  fetchUserInsights,
  updateUserFeedback,
  type UserFeedbackCreatePayload,
  type UserInsightRecord,
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

function buildFeedbackPayload(values: FeedbackFormValues): UserFeedbackCreatePayload {
  return {
    content: values.content.trim(),
    feedback_type: values.feedbackType,
    product_id: values.productId,
    source_channel: values.sourceChannel?.trim() || 'in_app',
  };
}

function statusColor(status: string) {
  if (status === 'resolved' || status === 'archived') {
    return 'green';
  }
  if (status === 'open') {
    return 'blue';
  }
  return status === '-' ? 'default' : 'gold';
}

function useProductOptions() {
  const [products, setProducts] = useState<ProductRecord[]>([]);

  useEffect(() => {
    let mounted = true;
    void fetchManagementProducts()
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

  return useMemo(
    () =>
      products.map((product) => ({
        label: product.name,
        value: product.id,
      })),
    [products],
  );
}

function useInsightColumns(onTriage: (row: UserInsightRecord) => void) {
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
        render: (_, row) =>
          row.category === '用户反馈' ? (
            <Button onClick={() => onTriage(row)} size="small" type="link">
              处理反馈
            </Button>
          ) : null,
        title: '操作',
      },
    ],
    [onTriage],
  );
}

export default function InsightsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [triageTarget, setTriageTarget] = useState<UserInsightRecord | null>(null);
  const [createForm] = Form.useForm<FeedbackFormValues>();
  const [triageForm] = Form.useForm<TriageFormValues>();
  const productOptions = useProductOptions();
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(fetchUserInsights);
  const columns = useInsightColumns((row) => {
    setTriageTarget(row);
    triageForm.setFieldsValue({
      status: row.status === '-' || row.status === 'open' ? 'triaged' : row.status,
      triageNote: undefined,
    });
  });

  useEffect(() => {
    if (!createOpen || productOptions.length !== 1 || createForm.getFieldValue('productId')) {
      return;
    }
    createForm.setFieldValue('productId', productOptions[0]?.value);
  }, [createForm, createOpen, productOptions]);

  const submitFeedback = async () => {
    const values = await createForm.validateFields();
    await createUserFeedback(buildFeedbackPayload(values));
    setCreateOpen(false);
    createForm.resetFields();
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
      />
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
    </>
  );
}
