import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Select } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ProductContextOption } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createGitLabDailyCodeMetric,
  fetchDevopsMetrics,
  fetchProductContextOptions,
  fetchProductGitRepositories,
  type GitLabDailyCodeMetricCreatePayload,
  type OperationalMetricRecord,
  type ProductGitRepositoryOption,
} from '../../services/aiBrain';

type GitLabMetricFormValues = {
  activeAuthorCount?: string;
  additions?: string;
  changedFiles?: string;
  commitCount?: string;
  deletions?: string;
  mergeRequestCount?: string;
  metricDate: string;
  productId: string;
  qualityScore?: string;
  repositoryId: string;
  riskCount?: string;
};

const gitlabMetricStatus = 'collected';

function optionalNonNegativeNumberRule(label: string, max?: number) {
  return {
    validator: async (_: unknown, value?: string) => {
      const trimmed = value?.trim();
      if (!trimmed) {
        return;
      }
      const parsed = Number(trimmed);
      if (!Number.isFinite(parsed) || parsed < 0 || (max !== undefined && parsed > max)) {
        throw new Error(`${label}请输入${max === 100 ? '0 到 100 之间的' : '非负'}数字`);
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

function productOptionsFromContexts(productContexts: ProductContextOption[]) {
  return productContexts.map((product) => ({
    label: product.name,
    value: product.id,
  }));
}

function buildGitLabMetricPayload(values: GitLabMetricFormValues): GitLabDailyCodeMetricCreatePayload {
  return {
    active_author_count: numberOrZero(values.activeAuthorCount),
    additions: numberOrZero(values.additions),
    changed_files: numberOrZero(values.changedFiles),
    commit_count: numberOrZero(values.commitCount),
    deletions: numberOrZero(values.deletions),
    merge_request_count: numberOrZero(values.mergeRequestCount),
    metric_date: values.metricDate.trim(),
    product_id: values.productId,
    quality_score: optionalNumber(values.qualityScore),
    repository_id: values.repositoryId,
    risk_count: numberOrZero(values.riskCount),
    source_channel: 'manual_import',
    status: gitlabMetricStatus,
  };
}

const columns: ProColumns<OperationalMetricRecord>[] = [
  {
    dataIndex: 'category',
    title: '指标来源',
  },
  {
    dataIndex: 'name',
    title: '指标名称',
  },
  {
    dataIndex: 'value',
    title: '指标值',
  },
  {
    dataIndex: 'status',
    title: '状态',
    render: (_, row) => <StatusTag color={row.status === '-' ? 'default' : 'blue'} label={row.status} />,
  },
  {
    dataIndex: 'updatedAt',
    title: '更新时间',
  },
];

export default function DevopsPage() {
  const [metricForm] = Form.useForm<GitLabMetricFormValues>();
  const [metricOpen, setMetricOpen] = useState(false);
  const [productContexts, setProductContexts] = useState<ProductContextOption[]>([]);
  const [repositoryState, setRepositoryState] = useState<{
    items: ProductGitRepositoryOption[];
    productId: string;
  } | null>(null);
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(fetchDevopsMetrics);
  const selectedProductId = Form.useWatch('productId', metricForm);
  const productOptions = useMemo(() => productOptionsFromContexts(productContexts), [productContexts]);
  const repositoryOptions = useMemo(
    () =>
      repositoryState !== null && repositoryState.productId === selectedProductId
        ? repositoryState.items
        : [],
    [repositoryState, selectedProductId],
  );
  const gitRepositoryOptions = useMemo(
    () =>
      repositoryOptions.map((repository) => ({
        label: repository.label,
        value: repository.id,
      })),
    [repositoryOptions],
  );

  useEffect(() => {
    let mounted = true;
    void fetchProductContextOptions()
      .then((items) => {
        if (mounted) {
          setProductContexts(items);
        }
      })
      .catch(() => {
        if (mounted) {
          setProductContexts([]);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!metricOpen || productOptions.length !== 1 || metricForm.getFieldValue('productId')) {
      return;
    }
    metricForm.setFieldValue('productId', productOptions[0]?.value);
  }, [metricForm, metricOpen, productOptions]);

  useEffect(() => {
    if (!metricOpen || !selectedProductId) {
      return;
    }
    let mounted = true;
    metricForm.setFieldValue('repositoryId', undefined);
    void fetchProductGitRepositories(selectedProductId)
      .then((items) => {
        if (mounted) {
          setRepositoryState({ items, productId: selectedProductId });
          if (items.length === 1) {
            metricForm.setFieldValue('repositoryId', items[0]?.id);
          }
        }
      })
      .catch(() => {
        if (mounted) {
          setRepositoryState({ items: [], productId: selectedProductId });
        }
      });
    return () => {
      mounted = false;
    };
  }, [metricForm, metricOpen, selectedProductId]);

  const submitGitLabMetric = async () => {
    const values = await metricForm.validateFields();
    await createGitLabDailyCodeMetric(buildGitLabMetricPayload(values));
    setMetricOpen(false);
    metricForm.resetFields();
    await reload();
  };

  return (
    <>
      <ManagementListPage<OperationalMetricRecord>
        breadcrumbGroup="运营治理"
        columns={columns}
        dataSource={dataSource}
        filters={[
          {
            label: '指标来源',
            name: 'category',
            options: [
              { label: 'GitLab 指标', value: 'GitLab 指标' },
              { label: 'Jenkins 发布', value: 'Jenkins 发布' },
              { label: '线上日志', value: '线上日志' },
            ],
            type: 'select',
          },
          { label: '指标名称', name: 'name', type: 'text' },
          { label: '状态', name: 'status', type: 'text' },
        ]}
        loading={status === 'loading'}
        notice={formatRemoteRowsError(error)}
        onReload={() => void reload()}
        rowKey="id"
        tableTitle="研发运营指标"
        title="研发运营看板"
        toolbarActions={[
          <Button aria-label="登记 GitLab 指标" key="gitlab-metric" onClick={() => setMetricOpen(true)}>
            登记 GitLab 指标
          </Button>,
        ]}
      />
      <Modal
        destroyOnHidden
        okText="保存"
        okButtonProps={{ 'aria-label': '保存' }}
        onCancel={() => setMetricOpen(false)}
        onOk={() => void submitGitLabMetric()}
        open={metricOpen}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
        title="登记 GitLab 指标"
      >
        <Form<GitLabMetricFormValues> form={metricForm} layout="vertical">
          <Form.Item label="所属产品" name="productId" rules={[{ required: true, message: '请选择所属产品' }]}>
            <Select options={productOptions} />
          </Form.Item>
          <Form.Item label="Git 仓库" name="repositoryId" rules={[{ required: true, message: '请选择 Git 仓库' }]}>
            <Select options={gitRepositoryOptions} />
          </Form.Item>
          <Form.Item label="指标日期" name="metricDate" rules={[{ required: true, message: '请输入指标日期' }]}>
            <Input placeholder="2026-06-01" />
          </Form.Item>
          <Form.Item label="提交数" name="commitCount" rules={[optionalNonNegativeIntegerRule('提交数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="活跃作者数" name="activeAuthorCount" rules={[optionalNonNegativeIntegerRule('活跃作者数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="MR 数" name="mergeRequestCount" rules={[optionalNonNegativeIntegerRule('MR 数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="变更文件数" name="changedFiles" rules={[optionalNonNegativeIntegerRule('变更文件数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="新增行数" name="additions" rules={[optionalNonNegativeIntegerRule('新增行数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="删除行数" name="deletions" rules={[optionalNonNegativeIntegerRule('删除行数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="质量评分" name="qualityScore" rules={[optionalNonNegativeNumberRule('质量评分', 100)]}>
            <Input placeholder="88.5" />
          </Form.Item>
          <Form.Item label="风险数量" name="riskCount" rules={[optionalNonNegativeIntegerRule('风险数量')]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
