import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Select } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ProductContextOption } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createGitLabDailyCodeMetric,
  createJenkinsRelease,
  createOnlineLogMetric,
  fetchDevopsMetrics,
  fetchProductContextOptions,
  fetchProductGitRepositories,
  type GitLabDailyCodeMetricCreatePayload,
  type JenkinsReleaseCreatePayload,
  type OnlineLogMetricCreatePayload,
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

type JenkinsReleaseFormValues = {
  buildId: string;
  buildNumber?: string;
  commitSha?: string;
  deployedAt?: string;
  durationSeconds?: string;
  environment?: string;
  failureReason?: string;
  jobName: string;
  productId: string;
  startedAt?: string;
  status?: string;
  triggerActor?: string;
  versionId: string;
};

type OnlineLogMetricFormValues = {
  anomalySummary?: string;
  coreEventCount?: string;
  environment?: string;
  errorCount?: string;
  moduleCode?: string;
  p95LatencyMs?: string;
  p99LatencyMs?: string;
  productId: string;
  requestCount?: string;
  topErrors?: string;
  windowEnd: string;
  windowStart: string;
};

const gitlabMetricStatus = 'collected';
const jenkinsReleaseStatus = 'success';
const onlineLogMetricStatus = 'collected';
const jenkinsStatusOptions = [
  { label: 'success', value: 'success' },
  { label: 'failed', value: 'failed' },
  { label: 'running', value: 'running' },
  { label: 'canceled', value: 'canceled' },
];

function parseTopErrors(value?: string): Record<string, unknown>[] {
  const trimmed = value?.trim();
  if (!trimmed) {
    return [];
  }
  const parsed = JSON.parse(trimmed) as unknown;
  return Array.isArray(parsed) ? (parsed as Record<string, unknown>[]) : [];
}

function topErrorsJsonRule() {
  return {
    validator: async (_: unknown, value?: string) => {
      const trimmed = value?.trim();
      if (!trimmed) {
        return;
      }
      try {
        const parsed = JSON.parse(trimmed) as unknown;
        if (!Array.isArray(parsed)) {
          throw new Error('Top Errors JSON 请输入数组 JSON');
        }
      } catch (error) {
        if (error instanceof Error && error.message.includes('数组 JSON')) {
          throw error;
        }
        throw new Error('Top Errors JSON 请输入合法 JSON');
      }
    },
  };
}

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

function optionalText(value?: string) {
  const trimmed = value?.trim();
  return trimmed || undefined;
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

function versionOptionsFromContexts(productContexts: ProductContextOption[], productId?: string) {
  const product = productContexts.find((item) => item.id === productId);
  return (product?.versions ?? []).map((version) => ({
    label: version.name,
    value: version.id,
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

function buildJenkinsReleasePayload(values: JenkinsReleaseFormValues): JenkinsReleaseCreatePayload {
  return {
    build_id: values.buildId.trim(),
    build_number: optionalNumber(values.buildNumber),
    commit_sha: optionalText(values.commitSha),
    deployed_at: optionalText(values.deployedAt),
    duration_seconds: optionalNumber(values.durationSeconds),
    environment: optionalText(values.environment) ?? 'prod',
    failure_reason: optionalText(values.failureReason),
    job_name: values.jobName.trim(),
    product_id: values.productId,
    source_channel: 'manual_import',
    started_at: optionalText(values.startedAt),
    status: values.status ?? jenkinsReleaseStatus,
    trigger_actor: optionalText(values.triggerActor),
    version_id: values.versionId,
  };
}

function buildOnlineLogMetricPayload(values: OnlineLogMetricFormValues): OnlineLogMetricCreatePayload {
  return {
    anomaly_summary: optionalText(values.anomalySummary),
    core_event_count: numberOrZero(values.coreEventCount),
    environment: optionalText(values.environment) ?? 'prod',
    error_count: numberOrZero(values.errorCount),
    module_code: optionalText(values.moduleCode),
    p95_latency_ms: optionalNumber(values.p95LatencyMs),
    p99_latency_ms: optionalNumber(values.p99LatencyMs),
    product_id: values.productId,
    request_count: numberOrZero(values.requestCount),
    source_channel: 'manual_import',
    status: onlineLogMetricStatus,
    top_errors: parseTopErrors(values.topErrors),
    window_end: values.windowEnd.trim(),
    window_start: values.windowStart.trim(),
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
  const [jenkinsForm] = Form.useForm<JenkinsReleaseFormValues>();
  const [onlineLogForm] = Form.useForm<OnlineLogMetricFormValues>();
  const [metricOpen, setMetricOpen] = useState(false);
  const [jenkinsOpen, setJenkinsOpen] = useState(false);
  const [onlineLogOpen, setOnlineLogOpen] = useState(false);
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
  const selectedJenkinsProductId = Form.useWatch('productId', jenkinsForm);
  const productOptions = useMemo(() => productOptionsFromContexts(productContexts), [productContexts]);
  const jenkinsVersionOptions = useMemo(
    () => versionOptionsFromContexts(productContexts, selectedJenkinsProductId),
    [productContexts, selectedJenkinsProductId],
  );
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
    if (!jenkinsOpen || productOptions.length !== 1 || jenkinsForm.getFieldValue('productId')) {
      return;
    }
    jenkinsForm.setFieldValue('productId', productOptions[0]?.value);
  }, [jenkinsForm, jenkinsOpen, productOptions]);

  useEffect(() => {
    if (!onlineLogOpen || productOptions.length !== 1 || onlineLogForm.getFieldValue('productId')) {
      return;
    }
    onlineLogForm.setFieldValue('productId', productOptions[0]?.value);
  }, [onlineLogForm, onlineLogOpen, productOptions]);

  useEffect(() => {
    if (!jenkinsOpen || jenkinsVersionOptions.length !== 1 || jenkinsForm.getFieldValue('versionId')) {
      return;
    }
    jenkinsForm.setFieldValue('versionId', jenkinsVersionOptions[0]?.value);
  }, [jenkinsForm, jenkinsOpen, jenkinsVersionOptions]);

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

  const submitJenkinsRelease = async () => {
    if (!jenkinsForm.getFieldValue('productId') && productOptions.length === 1) {
      jenkinsForm.setFieldValue('productId', productOptions[0]?.value);
    }
    const productId = jenkinsForm.getFieldValue('productId') as string | undefined;
    const currentVersionOptions = versionOptionsFromContexts(productContexts, productId);
    if (!jenkinsForm.getFieldValue('versionId') && currentVersionOptions.length === 1) {
      jenkinsForm.setFieldValue('versionId', currentVersionOptions[0]?.value);
    }
    const values = await jenkinsForm.validateFields();
    await createJenkinsRelease(buildJenkinsReleasePayload(values));
    setJenkinsOpen(false);
    jenkinsForm.resetFields();
    await reload();
  };

  const submitOnlineLogMetric = async () => {
    if (!onlineLogForm.getFieldValue('productId') && productOptions.length === 1) {
      onlineLogForm.setFieldValue('productId', productOptions[0]?.value);
    }
    const values = await onlineLogForm.validateFields();
    await createOnlineLogMetric(buildOnlineLogMetricPayload(values));
    setOnlineLogOpen(false);
    onlineLogForm.resetFields();
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
          <Button aria-label="登记 Jenkins 发布" key="jenkins-release" onClick={() => setJenkinsOpen(true)}>
            登记 Jenkins 发布
          </Button>,
          <Button aria-label="登记线上日志" key="online-log" onClick={() => setOnlineLogOpen(true)}>
            登记线上日志
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
      <Modal
        destroyOnHidden
        okText="保存"
        okButtonProps={{ 'aria-label': '保存' }}
        onCancel={() => setJenkinsOpen(false)}
        onOk={() => void submitJenkinsRelease()}
        open={jenkinsOpen}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
        title="登记 Jenkins 发布"
      >
        <Form<JenkinsReleaseFormValues> form={jenkinsForm} layout="vertical">
          <Form.Item label="所属产品" name="productId" rules={[{ required: true, message: '请选择所属产品' }]}>
            <Select options={productOptions} />
          </Form.Item>
          <Form.Item label="产品版本" name="versionId" rules={[{ required: true, message: '请选择产品版本' }]}>
            <Select options={jenkinsVersionOptions} />
          </Form.Item>
          <Form.Item label="Jenkins Job" name="jobName" rules={[{ required: true, message: '请输入 Jenkins Job' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Build ID" name="buildId" rules={[{ required: true, message: '请输入 Build ID' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Build 编号" name="buildNumber" rules={[optionalNonNegativeIntegerRule('Build 编号')]}>
            <Input />
          </Form.Item>
          <Form.Item label="发布环境" name="environment">
            <Input placeholder="prod" />
          </Form.Item>
          <Form.Item label="发布状态" name="status" initialValue={jenkinsReleaseStatus}>
            <Select options={jenkinsStatusOptions} />
          </Form.Item>
          <Form.Item label="触发人" name="triggerActor">
            <Input />
          </Form.Item>
          <Form.Item label="Commit SHA" name="commitSha">
            <Input />
          </Form.Item>
          <Form.Item label="耗时秒数" name="durationSeconds" rules={[optionalNonNegativeIntegerRule('耗时秒数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="开始时间" name="startedAt">
            <Input placeholder="2026-06-01T12:22:00Z" />
          </Form.Item>
          <Form.Item label="部署时间" name="deployedAt">
            <Input placeholder="2026-06-01T12:30:00Z" />
          </Form.Item>
          <Form.Item label="失败原因" name="failureReason">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        okText="保存"
        okButtonProps={{ 'aria-label': '保存' }}
        onCancel={() => setOnlineLogOpen(false)}
        onOk={() => void submitOnlineLogMetric()}
        open={onlineLogOpen}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
        title="登记线上日志"
      >
        <Form<OnlineLogMetricFormValues> form={onlineLogForm} layout="vertical">
          <Form.Item label="所属产品" name="productId" rules={[{ required: true, message: '请选择所属产品' }]}>
            <Select options={productOptions} />
          </Form.Item>
          <Form.Item label="模块编码" name="moduleCode">
            <Input />
          </Form.Item>
          <Form.Item label="运行环境" name="environment">
            <Input placeholder="prod" />
          </Form.Item>
          <Form.Item label="窗口开始" name="windowStart" rules={[{ required: true, message: '请输入窗口开始时间' }]}>
            <Input placeholder="2026-06-01T00:00:00Z" />
          </Form.Item>
          <Form.Item label="窗口结束" name="windowEnd" rules={[{ required: true, message: '请输入窗口结束时间' }]}>
            <Input placeholder="2026-06-01T01:00:00Z" />
          </Form.Item>
          <Form.Item label="请求数" name="requestCount" rules={[optionalNonNegativeIntegerRule('请求数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="错误数" name="errorCount" rules={[optionalNonNegativeIntegerRule('错误数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="P95 延迟毫秒" name="p95LatencyMs" rules={[optionalNonNegativeNumberRule('P95 延迟毫秒')]}>
            <Input />
          </Form.Item>
          <Form.Item label="P99 延迟毫秒" name="p99LatencyMs" rules={[optionalNonNegativeNumberRule('P99 延迟毫秒')]}>
            <Input />
          </Form.Item>
          <Form.Item label="核心事件数" name="coreEventCount" rules={[optionalNonNegativeIntegerRule('核心事件数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="Top Errors JSON" name="topErrors" rules={[topErrorsJsonRule()]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item label="异常摘要" name="anomalySummary">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
