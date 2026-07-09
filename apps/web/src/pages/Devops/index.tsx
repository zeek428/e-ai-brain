import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Select, Space, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { DateStringPicker } from '../../components/DateStringPicker';
import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import type { ProductContextOption, RequirementRecord } from '../../data/management';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  type RemoteRowsError,
} from '../../hooks/useRemoteRows';
import {
  cancelDeploymentRequest,
  completeDeploymentRequest,
  createDeploymentRequest,
  createGitLabDailyCodeMetric,
  createJenkinsRelease,
  createOnlineLogMetric,
  fetchDevopsMetricList,
  fetchManagementRequirementList,
  fetchProductContextOptions,
  fetchProductGitRepositories,
  startDeploymentRequest,
  type DeploymentCancelPayload,
  type DeploymentCompletePayload,
  type DeploymentRequestCreatePayload,
  type DeploymentStartPayload,
  type GitLabDailyCodeMetricCreatePayload,
  type JenkinsReleaseCreatePayload,
  type OnlineLogMetricCreatePayload,
  type OperationalMetricRecord,
  type OperationalMetricListQuery,
  type ProductGitRepositoryOption,
  type RemoteListPerformance,
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

type DeploymentRequestFormValues = {
  artifactVersion?: string;
  assignedOpsUser?: string;
  commitSha?: string;
  deployWindowEnd?: string;
  deployWindowStart?: string;
  environment?: string;
  releaseBranch?: string;
  releaseReadinessTaskId?: string;
  requirementIds: string[];
  riskLevel?: string;
  rollbackPlan?: string;
  productId: string;
  title: string;
  versionId: string;
};

type DeploymentActionType = 'cancel' | 'failed' | 'rolled_back' | 'start' | 'success';

type DeploymentActionFormValues = {
  externalBuildId?: string;
  externalJobName?: string;
  failureReason?: string;
  logUrl?: string;
  reason?: string;
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
const deploymentDefaultEnvironment = 'prod';
const deploymentEligibleRequirementStatuses = new Set<RequirementRecord['status']>([
  'ready_for_release',
  'testing',
]);
const jenkinsStatusOptions = [
  { label: 'success', value: 'success' },
  { label: 'failed', value: 'failed' },
  { label: 'running', value: 'running' },
  { label: 'canceled', value: 'canceled' },
];
const deploymentRiskOptions = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
  { label: '严重', value: 'critical' },
];
const deploymentStatusLabels: Record<string, { color: string; label: string }> = {
  approved: { color: 'blue', label: '已准入' },
  cancelled: { color: 'default', label: '已取消' },
  deploying: { color: 'processing', label: '部署中' },
  draft: { color: 'default', label: '草稿' },
  failed: { color: 'red', label: '部署失败' },
  pending_ops: { color: 'gold', label: '待运维执行' },
  rolled_back: { color: 'volcano', label: '已回滚' },
  succeeded: { color: 'green', label: '部署成功' },
};
const deploymentRequirementStatusLabels: Record<string, string> = {
  ready_for_release: '待发布',
  testing: '测试中',
};
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

function buildDeploymentRequestPayload(values: DeploymentRequestFormValues): DeploymentRequestCreatePayload {
  return {
    artifact_version: optionalText(values.artifactVersion),
    assigned_ops_user: optionalText(values.assignedOpsUser),
    commit_sha: optionalText(values.commitSha),
    deploy_window_end: optionalText(values.deployWindowEnd),
    deploy_window_start: optionalText(values.deployWindowStart),
    environment: optionalText(values.environment) ?? deploymentDefaultEnvironment,
    release_branch: optionalText(values.releaseBranch),
    release_readiness_task_id: optionalText(values.releaseReadinessTaskId),
    requirement_ids: values.requirementIds,
    risk_level: values.riskLevel ?? 'medium',
    rollback_plan: optionalText(values.rollbackPlan),
    product_id: values.productId,
    title: values.title.trim(),
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

const baseColumns: ProColumns<OperationalMetricRecord>[] = [
  {
    dataIndex: 'category',
    ellipsis: true,
    sorter: true,
    title: '指标来源',
    width: 140,
  },
  {
    dataIndex: 'name',
    ellipsis: true,
    sorter: true,
    title: '指标名称',
    width: 180,
  },
  {
    dataIndex: 'value',
    ellipsis: true,
    sorter: true,
    title: '指标值',
    width: 140,
  },
  {
    dataIndex: 'status',
    sorter: true,
    title: '状态',
    render: (_, row) => {
      const deploymentStatus = row.category === '运维部署' ? deploymentStatusLabels[row.status] : undefined;
      return (
        <StatusTag
          color={deploymentStatus?.color ?? (row.status === '-' ? 'default' : 'blue')}
          label={deploymentStatus?.label ?? row.status}
        />
      );
    },
    width: 110,
  },
  {
    dataIndex: 'updatedAt',
    ellipsis: true,
    sorter: true,
    title: '更新时间',
    width: 160,
  },
];

export default function DevopsPage() {
  const [metricForm] = Form.useForm<GitLabMetricFormValues>();
  const [jenkinsForm] = Form.useForm<JenkinsReleaseFormValues>();
  const [deploymentForm] = Form.useForm<DeploymentRequestFormValues>();
  const [deploymentActionForm] = Form.useForm<DeploymentActionFormValues>();
  const [onlineLogForm] = Form.useForm<OnlineLogMetricFormValues>();
  const [metricOpen, setMetricOpen] = useState(false);
  const [jenkinsOpen, setJenkinsOpen] = useState(false);
  const [deploymentOpen, setDeploymentOpen] = useState(false);
  const [deploymentAction, setDeploymentAction] = useState<{
    record: OperationalMetricRecord;
    type: DeploymentActionType;
  } | null>(null);
  const [deploymentRequirements, setDeploymentRequirements] = useState<RequirementRecord[]>([]);
  const [deploymentRequirementsLoading, setDeploymentRequirementsLoading] = useState(false);
  const [onlineLogOpen, setOnlineLogOpen] = useState(false);
  const [productContexts, setProductContexts] = useState<ProductContextOption[]>([]);
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
    performance?: RemoteListPerformance;
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
  const selectedProductId = Form.useWatch('productId', metricForm);
  const selectedJenkinsProductId = Form.useWatch('productId', jenkinsForm);
  const selectedDeploymentProductId = Form.useWatch('productId', deploymentForm);
  const selectedDeploymentVersionId = Form.useWatch('versionId', deploymentForm);
  const productOptions = useMemo(() => productOptionsFromContexts(productContexts), [productContexts]);
  const jenkinsVersionOptions = useMemo(
    () => versionOptionsFromContexts(productContexts, selectedJenkinsProductId),
    [productContexts, selectedJenkinsProductId],
  );
  const deploymentVersionOptions = useMemo(
    () => versionOptionsFromContexts(productContexts, selectedDeploymentProductId),
    [productContexts, selectedDeploymentProductId],
  );
  const deploymentRequirementOptions = useMemo(
    () =>
      deploymentRequirements
        .filter((requirement) => deploymentEligibleRequirementStatuses.has(requirement.status))
        .map((requirement) => ({
          label: `${requirement.id} · ${requirement.title} · ${
            deploymentRequirementStatusLabels[requirement.status] ?? requirement.status
          }`,
          value: requirement.id,
        })),
    [deploymentRequirements],
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
    if (!deploymentOpen || productOptions.length !== 1 || deploymentForm.getFieldValue('productId')) {
      return;
    }
    deploymentForm.setFieldValue('productId', productOptions[0]?.value);
  }, [deploymentForm, deploymentOpen, productOptions]);

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
    if (!deploymentOpen || deploymentVersionOptions.length !== 1 || deploymentForm.getFieldValue('versionId')) {
      return;
    }
    deploymentForm.setFieldValue('versionId', deploymentVersionOptions[0]?.value);
  }, [deploymentForm, deploymentOpen, deploymentVersionOptions]);

  useEffect(() => {
    if (!deploymentOpen || !selectedDeploymentProductId || !selectedDeploymentVersionId) {
      setDeploymentRequirements([]);
      return;
    }
    let mounted = true;
    setDeploymentRequirementsLoading(true);
    deploymentForm.setFieldValue('requirementIds', []);
    void fetchManagementRequirementList({
      page: 1,
      pageSize: 100,
      productId: selectedDeploymentProductId,
      versionId: selectedDeploymentVersionId,
    })
      .then((result) => {
        if (mounted) {
          setDeploymentRequirements(result.rows);
          const eligibleRequirements = result.rows.filter((requirement) =>
            deploymentEligibleRequirementStatuses.has(requirement.status),
          );
          if (eligibleRequirements.length === 1) {
            deploymentForm.setFieldValue('requirementIds', [eligibleRequirements[0]?.id]);
          }
        }
      })
      .catch(() => {
        if (mounted) {
          setDeploymentRequirements([]);
        }
      })
      .finally(() => {
        if (mounted) {
          setDeploymentRequirementsLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [deploymentForm, deploymentOpen, selectedDeploymentProductId, selectedDeploymentVersionId]);

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

  const submitDeploymentRequest = async () => {
    if (!deploymentForm.getFieldValue('productId') && productOptions.length === 1) {
      deploymentForm.setFieldValue('productId', productOptions[0]?.value);
    }
    const productId = deploymentForm.getFieldValue('productId') as string | undefined;
    const currentVersionOptions = versionOptionsFromContexts(productContexts, productId);
    if (!deploymentForm.getFieldValue('versionId') && currentVersionOptions.length === 1) {
      deploymentForm.setFieldValue('versionId', currentVersionOptions[0]?.value);
    }
    const values = await deploymentForm.validateFields();
    await createDeploymentRequest(buildDeploymentRequestPayload(values));
    message.success('部署单已创建');
    setDeploymentOpen(false);
    deploymentForm.resetFields();
    setDeploymentRequirements([]);
    await reload();
  };

  const openDeploymentAction = useCallback((record: OperationalMetricRecord, type: DeploymentActionType) => {
    deploymentActionForm.resetFields();
    setDeploymentAction({ record, type });
  }, [deploymentActionForm]);

  const submitDeploymentAction = async () => {
    if (!deploymentAction) {
      return;
    }
    const values = await deploymentActionForm.validateFields();
    const sharedPayload: DeploymentStartPayload = {
      executor_type: 'manual',
      external_build_id: optionalText(values.externalBuildId),
      external_job_name: optionalText(values.externalJobName),
      log_url: optionalText(values.logUrl),
    };
    const deploymentId = deploymentAction.record.id;
    if (deploymentAction.type === 'start') {
      await startDeploymentRequest(deploymentId, sharedPayload);
      message.success('部署已启动');
    } else if (deploymentAction.type === 'success') {
      const payload: DeploymentCompletePayload = {
        ...sharedPayload,
        status: 'success',
      };
      await completeDeploymentRequest(deploymentId, payload);
      message.success('部署已标记成功');
    } else if (deploymentAction.type === 'failed' || deploymentAction.type === 'rolled_back') {
      const payload: DeploymentCompletePayload = {
        ...sharedPayload,
        failure_reason: values.failureReason?.trim(),
        status: deploymentAction.type,
      };
      await completeDeploymentRequest(deploymentId, payload);
      message.success(deploymentAction.type === 'failed' ? '部署已标记失败' : '部署已标记回滚');
    } else if (deploymentAction.type === 'cancel') {
      const payload: DeploymentCancelPayload = {
        reason: optionalText(values.reason),
      };
      await cancelDeploymentRequest(deploymentId, payload);
      message.success('部署已取消');
    }
    setDeploymentAction(null);
    deploymentActionForm.resetFields();
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

  const columns = useMemo<ProColumns<OperationalMetricRecord>[]>(
    () => [
      ...baseColumns,
      {
        key: 'action',
        render: (_, row) => {
          if (row.category !== '运维部署') {
            return '-';
          }
          const status = row.status;
          const canStart = status === 'approved' || status === 'failed' || status === 'pending_ops';
          const canComplete = status === 'deploying';
          const canCancel = !['cancelled', 'rolled_back', 'succeeded'].includes(status);
          return (
            <Space size={4} wrap>
              {canStart ? (
                <Button onClick={() => openDeploymentAction(row, 'start')} size="small" type="link">
                  启动
                </Button>
              ) : null}
              {canComplete ? (
                <>
                  <Button onClick={() => openDeploymentAction(row, 'success')} size="small" type="link">
                    成功
                  </Button>
                  <Button onClick={() => openDeploymentAction(row, 'failed')} size="small" type="link">
                    失败
                  </Button>
                  <Button onClick={() => openDeploymentAction(row, 'rolled_back')} size="small" type="link">
                    回滚
                  </Button>
                </>
              ) : null}
              {canCancel ? (
                <Button danger onClick={() => openDeploymentAction(row, 'cancel')} size="small" type="link">
                  取消
                </Button>
              ) : null}
            </Space>
          );
        },
        title: '操作',
        width: 210,
      },
    ],
    [openDeploymentAction],
  );

  const deploymentActionTitle =
    deploymentAction?.type === 'start'
      ? '启动部署'
      : deploymentAction?.type === 'success'
        ? '确认部署成功'
        : deploymentAction?.type === 'failed'
          ? '登记部署失败'
          : deploymentAction?.type === 'rolled_back'
            ? '登记部署回滚'
            : '取消部署';
  const deploymentActionNeedsFailureReason =
    deploymentAction?.type === 'failed' || deploymentAction?.type === 'rolled_back';
  const deploymentActionIsCancel = deploymentAction?.type === 'cancel';

  return (
    <>
      <ManagementListPage<OperationalMetricRecord>
        breadcrumbGroup="运营治理"
        columns={columns}
        dataSource={listState.rows}
        viewStorageKey="governance.devops"
        filters={[
          {
            label: '指标来源',
            name: 'category',
            options: [
              { label: 'GitLab 指标', value: 'GitLab 指标' },
              { label: 'Jenkins 发布', value: 'Jenkins 发布' },
              { label: '运维部署', value: '运维部署' },
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
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="id"
        tableTitle="日志监控指标"
        title="日志监控"
        toolbarActions={[
          <Button aria-label="登记 GitLab 指标" key="gitlab-metric" onClick={() => setMetricOpen(true)}>
            登记 GitLab 指标
          </Button>,
          <Button aria-label="登记 Jenkins 发布" key="jenkins-release" onClick={() => setJenkinsOpen(true)}>
            登记 Jenkins 发布
          </Button>,
          <Button aria-label="发起部署" key="deployment-request" onClick={() => setDeploymentOpen(true)} type="primary">
            发起部署
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
        okText="创建部署单"
        okButtonProps={{ 'aria-label': '创建部署单' }}
        onCancel={() => {
          setDeploymentOpen(false);
          deploymentForm.resetFields();
          setDeploymentRequirements([]);
        }}
        onOk={() => void submitDeploymentRequest()}
        open={deploymentOpen}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
        title="发起运维部署"
      >
        <Form<DeploymentRequestFormValues> form={deploymentForm} initialValues={{ environment: deploymentDefaultEnvironment, riskLevel: 'medium' }} layout="vertical">
          <Form.Item label="所属产品" name="productId" rules={[{ required: true, message: '请选择所属产品' }]}>
            <Select
              onChange={() => {
                deploymentForm.setFieldsValue({ requirementIds: [], versionId: undefined });
                setDeploymentRequirements([]);
              }}
              options={productOptions}
            />
          </Form.Item>
          <Form.Item label="产品版本" name="versionId" rules={[{ required: true, message: '请选择产品版本' }]}>
            <Select
              onChange={() => {
                deploymentForm.setFieldValue('requirementIds', []);
              }}
              options={deploymentVersionOptions}
            />
          </Form.Item>
          <Form.Item label="部署标题" name="title" rules={[{ required: true, message: '请输入部署标题' }]}>
            <Input placeholder="例如：生产环境发布 2026.07.09" />
          </Form.Item>
          <Form.Item label="部署需求" name="requirementIds" rules={[{ required: true, message: '请选择待部署需求' }]}>
            <Select
              disabled={!selectedDeploymentVersionId}
              loading={deploymentRequirementsLoading}
              mode="multiple"
              options={deploymentRequirementOptions}
              placeholder={selectedDeploymentVersionId ? '请选择测试完成或待发布需求' : '请先选择产品版本'}
            />
          </Form.Item>
          <Form.Item label="部署环境" name="environment">
            <Input placeholder={deploymentDefaultEnvironment} />
          </Form.Item>
          <Form.Item label="风险等级" name="riskLevel">
            <Select options={deploymentRiskOptions} />
          </Form.Item>
          <Form.Item label="发布分支" name="releaseBranch">
            <Input placeholder="release/2026.07" />
          </Form.Item>
          <Form.Item label="Commit SHA" name="commitSha">
            <Input />
          </Form.Item>
          <Form.Item label="制品版本" name="artifactVersion">
            <Input />
          </Form.Item>
          <Form.Item label="部署窗口开始" name="deployWindowStart">
            <DateStringPicker mode="dateTime" placeholder="请选择部署窗口开始时间" />
          </Form.Item>
          <Form.Item label="部署窗口结束" name="deployWindowEnd">
            <DateStringPicker mode="dateTime" placeholder="请选择部署窗口结束时间" />
          </Form.Item>
          <Form.Item label="运维负责人" name="assignedOpsUser">
            <Input placeholder="用户 ID 或账号" />
          </Form.Item>
          <Form.Item label="发布评估任务 ID" name="releaseReadinessTaskId">
            <Input placeholder="可选，关联已确认的发布评估任务" />
          </Form.Item>
          <Form.Item label="回滚方案" name="rollbackPlan">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        okText="确认"
        okButtonProps={{ 'aria-label': '确认部署操作' }}
        onCancel={() => setDeploymentAction(null)}
        onOk={() => void submitDeploymentAction()}
        open={deploymentAction !== null}
        title={deploymentActionTitle}
      >
        <Form<DeploymentActionFormValues> form={deploymentActionForm} layout="vertical">
          <Form.Item label="部署单">
            <Input disabled value={deploymentAction?.record.name ?? deploymentAction?.record.id ?? '-'} />
          </Form.Item>
          {deploymentActionIsCancel ? (
            <Form.Item label="取消原因" name="reason">
              <Input.TextArea rows={3} />
            </Form.Item>
          ) : (
            <>
              <Form.Item label="外部 Job" name="externalJobName">
                <Input placeholder="Jenkins Job / Pipeline" />
              </Form.Item>
              <Form.Item label="外部 Build ID" name="externalBuildId">
                <Input />
              </Form.Item>
              <Form.Item label="日志链接" name="logUrl">
                <Input />
              </Form.Item>
              {deploymentActionNeedsFailureReason ? (
                <Form.Item
                  label={deploymentAction?.type === 'rolled_back' ? '回滚原因' : '失败原因'}
                  name="failureReason"
                  rules={[{ required: true, message: '请输入原因' }]}
                >
                  <Input.TextArea rows={3} />
                </Form.Item>
              ) : null}
            </>
          )}
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
