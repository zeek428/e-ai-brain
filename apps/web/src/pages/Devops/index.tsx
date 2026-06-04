import { ProTable, type ProColumns } from '@ant-design/pro-components';
import { Alert, Button, Form, Input, Modal, Radio, Select, Space } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { DateStringPicker } from '../../components/DateStringPicker';
import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import type { ProductContextOption, ProductModuleRecord, RequirementRecord } from '../../data/management';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  useRemoteRows,
  type RemoteRowsError,
} from '../../hooks/useRemoteRows';
import {
  createGitLabDailyCodeMetric,
  createJenkinsRelease,
  createOnlineLogMetric,
  createCollectorRun,
  fetchCollectorRuns,
  fetchDevopsMetricList,
  fetchManagementRequirements,
  fetchPendingAttributionItems,
  fetchProductContextOptions,
  fetchProductGitRepositories,
  fetchProductModules,
  resolvePendingAttributionItem,
  updateCollectorRun,
  type CollectorRunCreatePayload,
  type CollectorRunRecord,
  type GitLabDailyCodeMetricCreatePayload,
  type JenkinsReleaseCreatePayload,
  type OnlineLogMetricCreatePayload,
  type OperationalMetricRecord,
  type OperationalMetricListQuery,
  type PendingAttributionItem,
  type PendingAttributionResolvePayload,
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

type CollectorRunFormValues = {
  collectorType: string;
  errorMessage?: string;
  payloadSummary?: string;
  productId?: string;
  recordsImported?: string;
  sourceSystem: string;
  startedAt?: string;
  status?: string;
};

type CollectorRunFailureFormValues = {
  errorMessage: string;
};

type PendingAttributionResolveFormValues = {
  resolutionAction: string;
  resolutionNote?: string;
  resolvedModuleCode?: string;
  resolvedProductId?: string;
  resolvedRequirementId?: string;
  resolvedSubjectId?: string;
  resolvedSubjectType?: string;
};

const gitlabMetricStatus = 'collected';
const jenkinsReleaseStatus = 'success';
const onlineLogMetricStatus = 'collected';
const collectorRunStatus = 'running';
const jenkinsStatusOptions = [
  { label: 'success', value: 'success' },
  { label: 'failed', value: 'failed' },
  { label: 'running', value: 'running' },
  { label: 'canceled', value: 'canceled' },
];
const collectorTypeOptions = [
  { label: 'GitLab 日代码指标', value: 'gitlab_daily_code_metric' },
  { label: 'Jenkins 发布', value: 'jenkins_release' },
  { label: '线上日志指标', value: 'online_log_metric' },
  { label: '用户使用指标', value: 'user_usage_metric' },
  { label: '用户反馈', value: 'user_feedback' },
  { label: '迭代建议', value: 'iteration_plan_suggestion' },
];
const collectorRunStatusOptions = [
  { label: 'running', value: 'running' },
  { label: 'succeeded', value: 'succeeded' },
  { label: 'failed', value: 'failed' },
  { label: 'cancelled', value: 'cancelled' },
];
const pendingAttributionResolutionOptions = [
  { label: '归属到已有上下文', value: 'link_existing_context' },
  { label: '忽略为噪声', value: 'ignore_as_noise' },
];

function parseTopErrors(value?: string): Record<string, unknown>[] {
  const trimmed = value?.trim();
  if (!trimmed) {
    return [];
  }
  const parsed = JSON.parse(trimmed) as unknown;
  return Array.isArray(parsed) ? (parsed as Record<string, unknown>[]) : [];
}

function parseJsonObject(value?: string): Record<string, unknown> {
  const trimmed = value?.trim();
  if (!trimmed) {
    return {};
  }
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('请输入对象 JSON');
  }
  return parsed as Record<string, unknown>;
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

function payloadSummaryJsonRule() {
  return {
    validator: async (_: unknown, value?: string) => {
      const trimmed = value?.trim();
      if (!trimmed) {
        return;
      }
      try {
        parseJsonObject(trimmed);
      } catch {
        throw new Error('Payload 摘要 JSON 请输入对象 JSON');
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

function buildCollectorRunPayload(values: CollectorRunFormValues): CollectorRunCreatePayload {
  return {
    collector_type: values.collectorType,
    error_message: optionalText(values.errorMessage),
    payload_summary: parseJsonObject(values.payloadSummary),
    product_id: optionalText(values.productId),
    records_imported: numberOrZero(values.recordsImported),
    source_system: values.sourceSystem.trim(),
    started_at: optionalText(values.startedAt),
    status: values.status ?? collectorRunStatus,
  };
}

function collectorTypeLabel(value: string) {
  return collectorTypeOptions.find((option) => option.value === value)?.label ?? value;
}

function collectorRunStatusColor(status: string) {
  if (status === 'succeeded') {
    return 'green';
  }
  if (status === 'failed') {
    return 'red';
  }
  if (status === 'cancelled') {
    return 'default';
  }
  return 'blue';
}

function pendingAttributionStatusColor(status: string) {
  if (status === 'resolved') {
    return 'green';
  }
  if (status === 'ignored') {
    return 'default';
  }
  return 'gold';
}

function moduleOptionsFromModules(modules: ProductModuleRecord[]) {
  return modules.map((module) => ({
    label: `${module.name} (${module.code})`,
    value: module.code,
  }));
}

function requirementOptionsFromRequirements(requirements: RequirementRecord[], productId?: string) {
  return requirements
    .filter((requirement) => !productId || requirement.productId === productId)
    .map((requirement) => ({
      label: `${requirement.title} (${requirement.id})`,
      value: requirement.id,
    }));
}

function buildPendingAttributionResolvePayload(
  values: PendingAttributionResolveFormValues,
): PendingAttributionResolvePayload {
  if (values.resolutionAction === 'ignore_as_noise') {
    return {
      resolution_action: 'ignore_as_noise',
      resolution_note: optionalText(values.resolutionNote),
    };
  }
  return {
    resolution_action: 'link_existing_context',
    resolution_note: optionalText(values.resolutionNote),
    resolved_module_code: optionalText(values.resolvedModuleCode),
    resolved_product_id: optionalText(values.resolvedProductId),
    resolved_requirement_id: optionalText(values.resolvedRequirementId),
    resolved_subject_id: optionalText(values.resolvedSubjectId),
    resolved_subject_type: optionalText(values.resolvedSubjectType),
  };
}

const operationalMetricSortFieldMap: Record<string, string> = {
  category: 'category',
  name: 'name',
  status: 'status',
  updatedAt: 'updated_at',
  value: 'value',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildOperationalMetricListQuery(query: ManagementListQuery): OperationalMetricListQuery {
  const filters = query.filters;
  return {
    category: normalizeFilterText(filters.category),
    name: normalizeFilterText(filters.name),
    page: query.page,
    pageSize: query.pageSize,
    sortField: query.sortField
      ? operationalMetricSortFieldMap[query.sortField] ?? query.sortField
      : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(filters.status),
  };
}

const columns: ProColumns<OperationalMetricRecord>[] = [
  {
    dataIndex: 'category',
    sorter: true,
    title: '指标来源',
  },
  {
    dataIndex: 'name',
    sorter: true,
    title: '指标名称',
  },
  {
    dataIndex: 'value',
    sorter: true,
    title: '指标值',
  },
  {
    dataIndex: 'status',
    sorter: true,
    title: '状态',
    render: (_, row) => <StatusTag color={row.status === '-' ? 'default' : 'blue'} label={row.status} />,
  },
  {
    dataIndex: 'updatedAt',
    sorter: true,
    title: '更新时间',
  },
];

export default function DevopsPage() {
  const [metricForm] = Form.useForm<GitLabMetricFormValues>();
  const [jenkinsForm] = Form.useForm<JenkinsReleaseFormValues>();
  const [onlineLogForm] = Form.useForm<OnlineLogMetricFormValues>();
  const [collectorRunForm] = Form.useForm<CollectorRunFormValues>();
  const [collectorRunFailureForm] = Form.useForm<CollectorRunFailureFormValues>();
  const [pendingAttributionForm] = Form.useForm<PendingAttributionResolveFormValues>();
  const [metricOpen, setMetricOpen] = useState(false);
  const [jenkinsOpen, setJenkinsOpen] = useState(false);
  const [onlineLogOpen, setOnlineLogOpen] = useState(false);
  const [collectorRunOpen, setCollectorRunOpen] = useState(false);
  const [collectorRunFailureTarget, setCollectorRunFailureTarget] = useState<CollectorRunRecord | null>(null);
  const [pendingAttributionTarget, setPendingAttributionTarget] = useState<PendingAttributionItem | null>(null);
  const [productContexts, setProductContexts] = useState<ProductContextOption[]>([]);
  const [requirements, setRequirements] = useState<RequirementRecord[]>([]);
  const [resolvedProductModules, setResolvedProductModules] = useState<ProductModuleRecord[]>([]);
  const [repositoryState, setRepositoryState] = useState<{
    items: ProductGitRepositoryOption[];
    productId: string;
  } | null>(null);
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
    rows: OperationalMetricRecord[];
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
      const result = await fetchDevopsMetricList(buildOperationalMetricListQuery(listQuery));
      setListState({
        page: result.page,
        pageSize: result.pageSize,
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
  const {
    error: collectorRunError,
    reload: reloadCollectorRuns,
    rows: collectorRuns,
    status: collectorRunRemoteStatus,
  } = useRemoteRows(fetchCollectorRuns);
  const {
    error: pendingAttributionError,
    reload: reloadPendingAttribution,
    rows: pendingAttributionItems,
    status: pendingAttributionRemoteStatus,
  } = useRemoteRows(fetchPendingAttributionItems);
  const selectedProductId = Form.useWatch('productId', metricForm);
  const selectedJenkinsProductId = Form.useWatch('productId', jenkinsForm);
  const pendingAttributionResolutionAction = Form.useWatch('resolutionAction', pendingAttributionForm);
  const pendingAttributionResolvedProductId = Form.useWatch('resolvedProductId', pendingAttributionForm);
  const productOptions = useMemo(() => productOptionsFromContexts(productContexts), [productContexts]);
  const resolvedModuleOptions = useMemo(
    () =>
      pendingAttributionTarget === null || !pendingAttributionResolvedProductId
        ? []
        : moduleOptionsFromModules(resolvedProductModules),
    [pendingAttributionResolvedProductId, pendingAttributionTarget, resolvedProductModules],
  );
  const resolvedRequirementOptions = useMemo(
    () => requirementOptionsFromRequirements(requirements, pendingAttributionResolvedProductId),
    [pendingAttributionResolvedProductId, requirements],
  );
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
    let isCurrent = true;
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchDevopsMetricList(buildOperationalMetricListQuery(listQuery))
      .then((result) => {
        if (isCurrent) {
          setListState({
            page: result.page,
            pageSize: result.pageSize,
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
    if (pendingAttributionTarget === null) {
      return;
    }
    let mounted = true;
    void fetchManagementRequirements()
      .then((items) => {
        if (mounted) {
          setRequirements(items);
        }
      })
      .catch(() => {
        if (mounted) {
          setRequirements([]);
        }
      });
    return () => {
      mounted = false;
    };
  }, [pendingAttributionTarget]);

  useEffect(() => {
    if (pendingAttributionTarget === null) {
      return;
    }
    pendingAttributionForm.setFieldValue('resolvedModuleCode', undefined);
    if (!pendingAttributionResolvedProductId) {
      return;
    }
    let mounted = true;
    void fetchProductModules(pendingAttributionResolvedProductId)
      .then((items) => {
        if (mounted) {
          setResolvedProductModules(items);
          if (
            pendingAttributionTarget.suggestedModuleCode &&
            items.some((item) => item.code === pendingAttributionTarget.suggestedModuleCode)
          ) {
            pendingAttributionForm.setFieldValue(
              'resolvedModuleCode',
              pendingAttributionTarget.suggestedModuleCode,
            );
          }
        }
      })
      .catch(() => {
        if (mounted) {
          setResolvedProductModules([]);
        }
      });
    return () => {
      mounted = false;
    };
  }, [pendingAttributionForm, pendingAttributionResolvedProductId, pendingAttributionTarget]);

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
    if (
      !collectorRunOpen ||
      productOptions.length !== 1 ||
      collectorRunForm.getFieldValue('productId')
    ) {
      return;
    }
    collectorRunForm.setFieldValue('productId', productOptions[0]?.value);
  }, [collectorRunForm, collectorRunOpen, productOptions]);

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

  const submitCollectorRun = async () => {
    if (!collectorRunForm.getFieldValue('productId') && productOptions.length === 1) {
      collectorRunForm.setFieldValue('productId', productOptions[0]?.value);
    }
    const values = await collectorRunForm.validateFields();
    await createCollectorRun(buildCollectorRunPayload(values));
    setCollectorRunOpen(false);
    collectorRunForm.resetFields();
    await reloadCollectorRuns();
  };

  const updateCollectorRunStatus = useCallback(async (run: CollectorRunRecord, nextStatus: string) => {
    await updateCollectorRun(run.id, { status: nextStatus });
    await reloadCollectorRuns();
  }, [reloadCollectorRuns]);

  const submitCollectorRunFailure = async () => {
    if (collectorRunFailureTarget === null) {
      return;
    }
    const values = await collectorRunFailureForm.validateFields();
    await updateCollectorRun(collectorRunFailureTarget.id, {
      error_message: values.errorMessage.trim(),
      status: 'failed',
    });
    collectorRunFailureForm.resetFields();
    setCollectorRunFailureTarget(null);
    await reloadCollectorRuns();
  };

  const openPendingAttributionResolve = useCallback((item: PendingAttributionItem) => {
    setPendingAttributionTarget(item);
    setResolvedProductModules([]);
    pendingAttributionForm.setFieldsValue({
      resolutionAction: 'link_existing_context',
      resolutionNote: undefined,
      resolvedModuleCode: item.suggestedModuleCode,
      resolvedProductId: item.suggestedProductId,
      resolvedRequirementId: undefined,
      resolvedSubjectId: undefined,
      resolvedSubjectType: undefined,
    });
  }, [pendingAttributionForm]);

  const submitPendingAttributionResolve = async () => {
    if (pendingAttributionTarget === null) {
      return;
    }
    const values = await pendingAttributionForm.validateFields();
    await resolvePendingAttributionItem(
      pendingAttributionTarget.id,
      buildPendingAttributionResolvePayload(values),
    );
    pendingAttributionForm.resetFields();
    setPendingAttributionTarget(null);
    setResolvedProductModules([]);
    await reloadPendingAttribution();
  };

  const collectorRunColumns = useMemo<ProColumns<CollectorRunRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        search: false,
        title: '运行 ID',
      },
      {
        dataIndex: 'collectorType',
        search: false,
        title: '采集类型',
        render: (_, row) => collectorTypeLabel(row.collectorType),
      },
      {
        dataIndex: 'sourceSystem',
        search: false,
        title: '来源系统',
      },
      {
        dataIndex: 'productId',
        search: false,
        title: '产品 ID',
      },
      {
        dataIndex: 'status',
        search: false,
        title: '状态',
        render: (_, row) => (
          <StatusTag color={collectorRunStatusColor(row.status)} label={row.status} />
        ),
      },
      {
        dataIndex: 'recordsImported',
        search: false,
        title: '导入记录数',
      },
      {
        dataIndex: 'startedAt',
        search: false,
        title: '开始时间',
      },
      {
        dataIndex: 'finishedAt',
        search: false,
        title: '结束时间',
      },
      {
        dataIndex: 'errorMessage',
        search: false,
        title: '错误说明',
      },
      {
        key: 'actions',
        search: false,
        title: '操作',
        render: (_, row) =>
          row.status === 'running' ? (
            <Space>
              <Button
                aria-label={`标记成功 ${row.id}`}
                onClick={() => void updateCollectorRunStatus(row, 'succeeded')}
                size="small"
              >
                标记成功
              </Button>
              <Button
                aria-label={`标记失败 ${row.id}`}
                onClick={() => setCollectorRunFailureTarget(row)}
                size="small"
              >
                标记失败
              </Button>
              <Button
                aria-label={`取消运行 ${row.id}`}
                onClick={() => void updateCollectorRunStatus(row, 'cancelled')}
                size="small"
              >
                取消运行
              </Button>
            </Space>
          ) : (
            '-'
          ),
      },
    ],
    [updateCollectorRunStatus],
  );

  const pendingAttributionColumns = useMemo<ProColumns<PendingAttributionItem>[]>(
    () => [
      {
        dataIndex: 'id',
        search: false,
        title: '队列 ID',
      },
      {
        dataIndex: 'sourceType',
        search: false,
        title: '来源类型',
        render: (_, row) => collectorTypeLabel(row.sourceType),
      },
      {
        dataIndex: 'sourceSystem',
        search: false,
        title: '来源系统',
      },
      {
        dataIndex: 'rawSubjectId',
        search: false,
        title: '原始主体 ID',
        render: (_, row) => row.rawSubjectId ?? '-',
      },
      {
        dataIndex: 'summary',
        search: false,
        title: '摘要',
      },
      {
        dataIndex: 'suggestedProductId',
        search: false,
        title: '建议产品',
        render: (_, row) => row.suggestedProductId ?? '-',
      },
      {
        dataIndex: 'suggestedModuleCode',
        search: false,
        title: '建议模块',
        render: (_, row) => row.suggestedModuleCode ?? '-',
      },
      {
        dataIndex: 'confidence',
        search: false,
        title: '置信度',
        render: (_, row) => (row.confidence === undefined ? '-' : row.confidence.toFixed(2)),
      },
      {
        dataIndex: 'status',
        search: false,
        title: '状态',
        render: (_, row) => (
          <StatusTag color={pendingAttributionStatusColor(row.status)} label={row.status} />
        ),
      },
      {
        dataIndex: 'createdAt',
        search: false,
        title: '创建时间',
      },
      {
        key: 'actions',
        search: false,
        title: '操作',
        render: (_, row) =>
          row.status === 'pending' ? (
            <Button
              aria-label={`归属处理 ${row.id}`}
              onClick={() => openPendingAttributionResolve(row)}
              size="small"
              type="link"
            >
              归属处理
            </Button>
          ) : (
            '-'
          ),
      },
    ],
    [openPendingAttributionResolve],
  );

  return (
    <>
      <ManagementListPage<OperationalMetricRecord>
        breadcrumbGroup="运营治理"
        columns={columns}
        dataSource={listState.rows}
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
        loading={listState.status === 'loading'}
        notice={formatRemoteRowsError(listState.error)}
        onReload={() => void reload()}
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          total: listState.total,
        }}
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
      <div style={{ margin: '16px 24px 24px' }}>
        {collectorRunError ? (
          <Alert
            className="management-list-alert"
            showIcon
            title={formatRemoteRowsError(collectorRunError)}
            type="warning"
          />
        ) : null}
        <ProTable<CollectorRunRecord>
          cardBordered
          columns={collectorRunColumns}
          dataSource={collectorRuns}
          dateFormatter="string"
          headerTitle="采集运行记录"
          loading={collectorRunRemoteStatus === 'loading'}
          options={{
            density: true,
            reload: () => void reloadCollectorRuns(),
            setting: true,
          }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
          rowKey="id"
          search={false}
          toolBarRender={() => [
            <Button
              aria-label="登记采集运行"
              key="collector-run"
              onClick={() => setCollectorRunOpen(true)}
              type="primary"
            >
              登记采集运行
            </Button>,
          ]}
        />
      </div>
      <div style={{ margin: '16px 24px 24px' }}>
        {pendingAttributionError ? (
          <Alert
            className="management-list-alert"
            showIcon
            title={formatRemoteRowsError(pendingAttributionError)}
            type="warning"
          />
        ) : null}
        <ProTable<PendingAttributionItem>
          cardBordered
          columns={pendingAttributionColumns}
          dataSource={pendingAttributionItems}
          dateFormatter="string"
          headerTitle="待归属数据队列"
          loading={pendingAttributionRemoteStatus === 'loading'}
          options={{
            density: true,
            reload: () => void reloadPendingAttribution(),
            setting: true,
          }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
          rowKey="id"
          search={false}
        />
      </div>
      <Modal
        destroyOnHidden
        okText="保存"
        okButtonProps={{ 'aria-label': '保存' }}
        onCancel={() => setCollectorRunOpen(false)}
        onOk={() => void submitCollectorRun()}
        open={collectorRunOpen}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
        title="登记采集运行"
      >
        <Form<CollectorRunFormValues> form={collectorRunForm} layout="vertical">
          <Form.Item
            initialValue="gitlab_daily_code_metric"
            label="采集类型"
            name="collectorType"
            rules={[{ required: true, message: '请选择采集类型' }]}
          >
            <Select options={collectorTypeOptions} />
          </Form.Item>
          <Form.Item label="所属产品" name="productId">
            <Select allowClear options={productOptions} />
          </Form.Item>
          <Form.Item label="来源系统" name="sourceSystem" rules={[{ required: true, message: '请输入来源系统' }]}>
            <Input placeholder="gitlab" />
          </Form.Item>
          <Form.Item label="采集状态" name="status" initialValue={collectorRunStatus}>
            <Select options={collectorRunStatusOptions} />
          </Form.Item>
          <Form.Item label="开始时间" name="startedAt">
            <DateStringPicker mode="dateTime" placeholder="请选择开始时间" />
          </Form.Item>
          <Form.Item label="导入记录数" name="recordsImported" rules={[optionalNonNegativeIntegerRule('导入记录数')]}>
            <Input />
          </Form.Item>
          <Form.Item label="错误说明" name="errorMessage">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item label="Payload 摘要 JSON" name="payloadSummary" rules={[payloadSummaryJsonRule()]}>
            <Input.TextArea rows={3} placeholder='{"repository_path":"rd/platform-api"}' />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        okText="保存"
        okButtonProps={{ 'aria-label': '保存' }}
        onCancel={() => {
          pendingAttributionForm.resetFields();
          setPendingAttributionTarget(null);
          setResolvedProductModules([]);
        }}
        onOk={() => void submitPendingAttributionResolve()}
        open={pendingAttributionTarget !== null}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
        title="归属处理"
      >
        <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
          <div>{pendingAttributionTarget?.summary}</div>
          <Form<PendingAttributionResolveFormValues> form={pendingAttributionForm} layout="vertical">
            <Form.Item
              initialValue="link_existing_context"
              label="处理方式"
              name="resolutionAction"
              rules={[{ required: true, message: '请选择处理方式' }]}
            >
              <Radio.Group
                optionType="button"
                options={pendingAttributionResolutionOptions}
              />
            </Form.Item>
            <Form.Item
              label="归属产品"
              name="resolvedProductId"
              rules={[
                {
                  validator: async (_: unknown, value?: string) => {
                    if (
                      pendingAttributionForm.getFieldValue('resolutionAction') !==
                        'ignore_as_noise' &&
                      !value
                    ) {
                      throw new Error('请选择归属产品');
                    }
                  },
                },
              ]}
            >
              <Select
                allowClear
                disabled={pendingAttributionResolutionAction === 'ignore_as_noise'}
                options={productOptions}
              />
            </Form.Item>
            <Form.Item label="归属模块" name="resolvedModuleCode">
              <Select
                allowClear
                disabled={
                  pendingAttributionResolutionAction === 'ignore_as_noise' ||
                  !pendingAttributionResolvedProductId
                }
                options={resolvedModuleOptions}
              />
            </Form.Item>
            <Form.Item label="关联需求" name="resolvedRequirementId">
              <Select
                allowClear
                disabled={
                  pendingAttributionResolutionAction === 'ignore_as_noise' ||
                  !pendingAttributionResolvedProductId
                }
                options={resolvedRequirementOptions}
              />
            </Form.Item>
            <Form.Item label="关联主体类型" name="resolvedSubjectType">
              <Input disabled={pendingAttributionResolutionAction === 'ignore_as_noise'} />
            </Form.Item>
            <Form.Item label="关联主体 ID" name="resolvedSubjectId">
              <Input disabled={pendingAttributionResolutionAction === 'ignore_as_noise'} />
            </Form.Item>
            <Form.Item label="处理说明" name="resolutionNote">
              <Input.TextArea rows={3} />
            </Form.Item>
          </Form>
        </Space>
      </Modal>
      <Modal
        destroyOnHidden
        okText="保存"
        okButtonProps={{ 'aria-label': '保存' }}
        onCancel={() => {
          collectorRunFailureForm.resetFields();
          setCollectorRunFailureTarget(null);
        }}
        onOk={() => void submitCollectorRunFailure()}
        open={collectorRunFailureTarget !== null}
        title="标记采集失败"
      >
        <Form<CollectorRunFailureFormValues> form={collectorRunFailureForm} layout="vertical">
          <Form.Item label="错误说明" name="errorMessage" rules={[{ required: true, message: '请输入错误说明' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
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
            <DateStringPicker placeholder="请选择指标日期" />
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
            <DateStringPicker mode="dateTime" placeholder="请选择开始时间" />
          </Form.Item>
          <Form.Item label="部署时间" name="deployedAt">
            <DateStringPicker mode="dateTime" placeholder="请选择部署时间" />
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
            <DateStringPicker mode="dateTime" placeholder="请选择窗口开始时间" />
          </Form.Item>
          <Form.Item label="窗口结束" name="windowEnd" rules={[{ required: true, message: '请输入窗口结束时间' }]}>
            <DateStringPicker mode="dateTime" placeholder="请选择窗口结束时间" />
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
