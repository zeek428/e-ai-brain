import type { ProColumns } from '@ant-design/pro-components';
import { Button, Descriptions, Form, Input, Modal, Select, Space, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import type { ProductContextOption } from '../../data/management';
import { formatRemoteRowsError, normalizeRemoteRowsError, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  convertUserFeedbackToRequirement,
  createUserFeedback,
  fetchProductContextOptions,
  fetchUserInsightList,
  updateUserFeedback,
  type RemoteListPerformance,
  type UserInsightListQuery,
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

type ConvertRequirementFormValues = {
  content?: string;
  moduleCode?: string;
  priority: string;
  productId: string;
  title: string;
  triageNote?: string;
  versionId?: string;
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

const { Paragraph, Text } = Typography;

const insightSortFieldMap: Record<string, string> = {
  category: 'category',
  owner: 'owner',
  status: 'status',
  summary: 'summary',
  updatedAt: 'updated_at',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildInsightListQuery(query: ManagementListQuery): UserInsightListQuery {
  const filters = query.filters;
  return {
    category: normalizeFilterText(filters.category),
    page: query.page,
    pageSize: query.pageSize,
    productId: normalizeFilterText(filters.productId),
    sortField: query.sortField ? insightSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(filters.status),
    summary: normalizeFilterText(filters.summary),
  };
}

function buildFeedbackPayload(values: FeedbackFormValues): UserFeedbackCreatePayload {
  return {
    content: values.content.trim(),
    feedback_type: values.feedbackType,
    product_id: values.productId,
    source_channel: values.sourceChannel?.trim() || 'in_app',
  };
}

function statusColor(status: string) {
  if (
    status === 'accepted' ||
    status === 'archived' ||
    status === 'converted_to_requirement' ||
    status === 'linked' ||
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

function productNameMap(productContexts: ProductContextOption[]) {
  return Object.fromEntries(productContexts.map((product) => [product.id, product.name]));
}

function productDisplayText(productId: string | undefined, namesById: Record<string, string>) {
  if (!productId || productId === '-') {
    return '-';
  }
  return namesById[productId] || productId;
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
  onConvert: (row: UserInsightRecord) => void,
  onDetail: (row: UserInsightRecord) => void,
  onTriage: (row: UserInsightRecord) => void,
  productNamesById: Record<string, string>,
) {
  return useMemo<ProColumns<UserInsightRecord>[]>(
    () => [
      {
        dataIndex: 'category',
        ellipsis: true,
        sorter: true,
        title: '数据类型',
        width: 96,
      },
      {
        dataIndex: 'summary',
        ellipsis: true,
        render: (_, row) => (
          <Text ellipsis={{ tooltip: row.summary }} style={{ display: 'block', maxWidth: '100%' }}>
            {row.summary}
          </Text>
        ),
        sorter: true,
        title: '摘要',
        width: 320,
      },
      {
        dataIndex: 'productId',
        ellipsis: true,
        render: (_, row) => productDisplayText(row.productId, productNamesById),
        title: '所属产品',
        width: 160,
      },
      {
        dataIndex: 'owner',
        ellipsis: true,
        sorter: true,
        title: '归属用户',
        width: 120,
      },
      {
        dataIndex: 'status',
        sorter: true,
        title: '状态',
        render: (_, row) => <StatusTag color={statusColor(row.status)} label={row.status} />,
        width: 100,
      },
      {
        dataIndex: 'updatedAt',
        sorter: true,
        title: '更新时间',
        width: 130,
      },
      {
        fixed: 'right',
        key: 'actions',
        render: (_, row) => {
          const detailAction = (
            <Button key="detail" onClick={() => onDetail(row)} size="small" type="link">
              详情
            </Button>
          );
          if (row.category === '用户反馈') {
            return (
              <Space size={0}>
                {detailAction}
                <Button
                  disabled={row.status === 'linked'}
                  key="convert"
                  onClick={() => onConvert(row)}
                  size="small"
                  type="link"
                >
                  转需求
                </Button>
                <Button key="triage" onClick={() => onTriage(row)} size="small" type="link">
                  处理反馈
                </Button>
              </Space>
            );
          }
          return detailAction;
        },
        title: '操作',
        width: 128,
      },
    ],
    [onConvert, onDetail, onTriage, productNamesById],
  );
}

export default function InsightsPage() {
  const [convertTarget, setConvertTarget] = useState<UserInsightRecord | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [detailTarget, setDetailTarget] = useState<UserInsightRecord | null>(null);
  const [isConverting, setIsConverting] = useState(false);
  const [triageTarget, setTriageTarget] = useState<UserInsightRecord | null>(null);
  const [createForm] = Form.useForm<FeedbackFormValues>();
  const [convertForm] = Form.useForm<ConvertRequirementFormValues>();
  const [triageForm] = Form.useForm<TriageFormValues>();
  const productContexts = useProductContexts();
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'updatedAt',
    sortOrder: 'descend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    performance?: RemoteListPerformance;
    rows: UserInsightRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchUserInsightList(buildInsightListQuery(listQuery));
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        performance: result.performance,
        rows: result.rows,
        status: 'ready',
        total: result.total,
      });
    } catch (loadError: unknown) {
      setListState((current) => ({
        ...current,
        error: normalizeRemoteRowsError(loadError),
        rows: [],
        status: 'error',
      }));
    }
  }, [listQuery]);
  const productOptions = useMemo(() => productOptionsFromContexts(productContexts), [productContexts]);
  const productNamesById = useMemo(() => productNameMap(productContexts), [productContexts]);
  const convertProductId = Form.useWatch('productId', convertForm);
  const versionOptions = useMemo(
    () => versionOptionsFromContexts(productContexts, convertProductId),
    [convertProductId, productContexts],
  );
  useEffect(() => {
    let isCurrent = true;
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchUserInsightList(buildInsightListQuery(listQuery))
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
      .catch((loadError: unknown) => {
        if (isCurrent) {
          setListState((current) => ({
            ...current,
            error: normalizeRemoteRowsError(loadError),
            rows: [],
            status: 'error',
          }));
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [listQuery]);
  const columns = useInsightColumns(
    (row) => {
      setConvertTarget(row);
      convertForm.setFieldsValue({
        content: row.summary === '-' ? undefined : row.summary,
        moduleCode: row.moduleCode === '-' ? undefined : row.moduleCode,
        priority: 'P1',
        productId: row.productId === '-' ? undefined : row.productId,
        title: row.summary === '-' ? undefined : row.summary.slice(0, 80),
        triageNote: undefined,
        versionId: row.versionId === '-' ? undefined : row.versionId,
      });
    },
    (row) => setDetailTarget(row),
    (row) => {
      setTriageTarget(row);
      triageForm.setFieldsValue({
        status: row.status === '-' || row.status === 'open' ? 'triaged' : row.status,
        triageNote: undefined,
      });
    },
    productNamesById,
  );

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

  const submitConvertRequirement = async () => {
    if (!convertTarget) {
      return;
    }
    const values = await convertForm.validateFields();
    setIsConverting(true);
    try {
      const result = await convertUserFeedbackToRequirement(convertTarget.id, {
        content: values.content?.trim() || undefined,
        module_code: values.moduleCode?.trim() || undefined,
        priority: values.priority,
        product_id: values.productId,
        title: values.title.trim(),
        triage_note: values.triageNote?.trim() || undefined,
        version_id: values.versionId,
      });
      message.success(`已转为需求：${result.requirement.id}`);
      setConvertTarget(null);
      convertForm.resetFields();
      await reload();
    } finally {
      setIsConverting(false);
    }
  };

  return (
    <>
      <ManagementListPage<UserInsightRecord>
        breadcrumbGroup="运营治理"
        columns={columns}
        dataSource={listState.rows}
        viewStorageKey="governance.insights"
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
          {
            label: '所属产品',
            name: 'productId',
            options: productOptions,
            type: 'select',
          },
          { label: '摘要', name: 'summary', type: 'text' },
          { label: '状态', name: 'status', type: 'text' },
        ]}
        loading={listState.status === 'loading'}
        notice={formatRemoteRowsError(listState.error)}
        onPrimaryAction={() => setCreateOpen(true)}
        onReload={() => void reload()}
        primaryAction="登记反馈"
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="id"
        tableLayout="fixed"
        tableScroll={{ x: 1054 }}
        tableTitle="用户洞察"
        title="用户洞察"
      />
      <Modal
        footer={null}
        onCancel={() => setDetailTarget(null)}
        open={Boolean(detailTarget)}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
        title="用户洞察详情"
        width={760}
      >
        {detailTarget ? (
          <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
            <Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>{detailTarget.summary}</Paragraph>
            <Descriptions column={2} size="small">
              <Descriptions.Item label="数据类型">{detailTarget.category}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <StatusTag color={statusColor(detailTarget.status)} label={detailTarget.status} />
              </Descriptions.Item>
              <Descriptions.Item label="归属用户">{detailTarget.owner}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{detailTarget.updatedAt}</Descriptions.Item>
              <Descriptions.Item label="所属产品">
                {productDisplayText(detailTarget.productId, productNamesById)}
              </Descriptions.Item>
              <Descriptions.Item label="版本 ID">{detailTarget.versionId || '-'}</Descriptions.Item>
              <Descriptions.Item label="模块编码">{detailTarget.moduleCode || '-'}</Descriptions.Item>
              <Descriptions.Item label="功能编码">{detailTarget.featureCode || '-'}</Descriptions.Item>
              <Descriptions.Item label="反馈类型">{detailTarget.feedbackType || '-'}</Descriptions.Item>
              <Descriptions.Item label="规划周期">{detailTarget.planningCycle || '-'}</Descriptions.Item>
              <Descriptions.Item label="优先级">{detailTarget.priority || '-'}</Descriptions.Item>
              <Descriptions.Item label="置信度">{detailTarget.confidenceLevel || '-'}</Descriptions.Item>
              <Descriptions.Item label="转化需求 ID">{detailTarget.convertedRequirementId || '-'}</Descriptions.Item>
            </Descriptions>
          </Space>
        ) : null}
      </Modal>
      <Modal
        confirmLoading={isConverting}
        destroyOnHidden
        okText="转为需求"
        okButtonProps={{ 'aria-label': '转为需求' }}
        onCancel={() => setConvertTarget(null)}
        onOk={() => void submitConvertRequirement()}
        open={Boolean(convertTarget)}
        title="用户反馈转需求"
      >
        <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
          <Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>{convertTarget?.summary}</Paragraph>
          <Form<ConvertRequirementFormValues> form={convertForm} layout="vertical">
            <Form.Item label="所属产品" name="productId" rules={[{ required: true, message: '请选择所属产品' }]}>
              <Select optionFilterProp="label" options={productOptions} showSearch />
            </Form.Item>
            <Form.Item label="目标版本" name="versionId">
              <Select allowClear optionFilterProp="label" options={versionOptions} placeholder="可留空" showSearch />
            </Form.Item>
            <Form.Item label="需求标题" name="title" rules={[{ required: true, message: '请输入需求标题' }]}>
              <Input />
            </Form.Item>
            <Form.Item label="优先级" name="priority" rules={[{ required: true, message: '请选择优先级' }]}>
              <Select
                options={[
                  { label: 'P0', value: 'P0' },
                  { label: 'P1', value: 'P1' },
                  { label: 'P2', value: 'P2' },
                ]}
              />
            </Form.Item>
            <Form.Item label="模块编码" name="moduleCode">
              <Input />
            </Form.Item>
            <Form.Item label="需求内容" name="content">
              <Input.TextArea rows={4} />
            </Form.Item>
            <Form.Item label="处理备注" name="triageNote">
              <Input.TextArea rows={2} />
            </Form.Item>
          </Form>
        </Space>
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
    </>
  );
}
