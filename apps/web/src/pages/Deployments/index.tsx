import { FileTextOutlined, SyncOutlined } from '@ant-design/icons';
import { PageContainer, type ProColumns } from '@ant-design/pro-components';
import {
  Button,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Spin,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { DateStringPicker } from '../../components/DateStringPicker';
import {
  ManagementListPage,
  StatusTag,
  type ManagementListQuery,
} from '../../components/ManagementListPage';
import type { ProductContextOption, RequirementRecord } from '../../data/management';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  type RemoteRowsError,
} from '../../hooks/useRemoteRows';
import {
  AUTH_STATE_EVENT,
  cancelDeploymentRequest,
  completeDeploymentRequest,
  createDeploymentRequest,
  fetchDeploymentSchemes,
  fetchDeploymentRequestDetail,
  fetchDeploymentRequestList,
  fetchDeploymentRunLogs,
  fetchManagementRequirementList,
  fetchProductContextOptions,
  getStoredCurrentUser,
  startDeploymentRequest,
  syncDeploymentRun,
  type DeploymentCancelPayload,
  type DeploymentCompletePayload,
  type DeploymentRequestCreatePayload,
  type DeploymentRunLogRecord,
  type DeploymentRequestRecord,
  type DeploymentSchemeRecord,
  type DeploymentStartPayload,
  type OperationalMetricRecord,
  type RemoteListPerformance,
} from '../../services/aiBrain';
import { DeploymentSchemePanel } from './DeploymentSchemePanel';
import { DeploymentDetailDrawer } from './DeploymentDetailDrawer';

type DeploymentRequestFormValues = {
  artifactDigest?: string;
  artifactVersion?: string;
  assignedOpsUser?: string;
  commitSha?: string;
  deployWindowEnd?: string;
  deployWindowStart?: string;
  deploymentSchemeId?: string;
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

const deploymentDefaultEnvironment = 'prod';
const deploymentEligibleRequirementStatuses = new Set<RequirementRecord['status']>([
  'ready_for_release',
  'testing',
]);
const deploymentRiskOptions = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' },
  { label: '严重', value: 'critical' },
];
const deploymentRiskLabels: Record<string, { color: string; label: string }> = {
  critical: { color: 'red', label: '严重' },
  high: { color: 'volcano', label: '高' },
  low: { color: 'green', label: '低' },
  medium: { color: 'gold', label: '中' },
};
const deploymentMethodLabels: Record<string, string> = {
  docker: 'Docker',
  jenkins: 'Jenkins',
  manual: '人工部署',
  ssh: 'SSH',
};
const deploymentChannelLabels: Record<string, string> = {
  integration: '系统集成',
  manual: '人工',
  runner: 'Runner',
};
const deploymentStatusLabels: Record<string, { color: string; label: string }> = {
  approved: { color: 'blue', label: '已准入' },
  cancelled: { color: 'default', label: '已取消' },
  cancelling: { color: 'orange', label: '取消中' },
  deploying: { color: 'processing', label: '部署中' },
  draft: { color: 'default', label: '草稿' },
  failed: { color: 'red', label: '部署失败' },
  pending_ops: { color: 'gold', label: '待运维执行' },
  rolled_back: { color: 'volcano', label: '已回滚' },
  succeeded: { color: 'green', label: '部署成功' },
};
const deploymentStatusOptions = Object.entries(deploymentStatusLabels).map(([value, item]) => ({
  label: item.label,
  value,
}));
const deploymentRequirementStatusLabels: Record<string, string> = {
  ready_for_release: '待发布',
  testing: '测试中',
};

function optionalText(value?: string) {
  const trimmed = value?.trim();
  return trimmed || undefined;
}

function productOptionsFromContexts(productContexts: ProductContextOption[]) {
  return productContexts.map((product) => ({ label: product.name, value: product.id }));
}

function versionOptionsFromContexts(productContexts: ProductContextOption[], productId?: string) {
  const product = productContexts.find((item) => item.id === productId);
  return (product?.versions ?? []).map((version) => ({ label: version.name, value: version.id }));
}

function buildDeploymentRequestPayload(
  values: DeploymentRequestFormValues,
): DeploymentRequestCreatePayload {
  return {
    artifact_digest: optionalText(values.artifactDigest),
    artifact_version: optionalText(values.artifactVersion),
    assigned_ops_user: optionalText(values.assignedOpsUser),
    commit_sha: optionalText(values.commitSha),
    deploy_window_end: optionalText(values.deployWindowEnd),
    deploy_window_start: optionalText(values.deployWindowStart),
    deployment_scheme_id: optionalText(values.deploymentSchemeId),
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

const deploymentSortFieldMap: Record<string, string> = {
  id: 'updated_at',
  name: 'title',
  status: 'status',
  updatedAt: 'updated_at',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function routeKeyword() {
  if (typeof window === 'undefined') {
    return undefined;
  }
  const params = new URLSearchParams(window.location.search);
  return params.get('deployment_id') ?? params.get('version_id') ?? undefined;
}

function deploymentListQuery(query: ManagementListQuery) {
  return {
    page: query.page,
    pageSize: query.pageSize,
    sortField: query.sortField
      ? deploymentSortFieldMap[query.sortField] ?? query.sortField
      : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
    title: normalizeFilterText(query.filters.keyword),
  };
}

function deploymentMetricRow(record: DeploymentRequestRecord): OperationalMetricRecord {
  return {
    category: '运维部署',
    deploymentMethod: record.deploymentMethod,
    deploymentSchemeId: record.deploymentSchemeId,
    environment: record.environment,
    executorChannel: record.executorChannel,
    id: record.id,
    name: record.title,
    productId: record.productId,
    requirementIds: record.requirementIds,
    riskLevel: record.riskLevel,
    status: record.status,
    updatedAt: record.updatedAt,
    value: `${record.currentWave}/${record.totalWaves}`,
    versionId: record.versionId,
  };
}

export default function DeploymentsPage() {
  const initialRouteKeyword = useMemo(routeKeyword, []);
  const [activeTab, setActiveTab] = useState('requests');
  const [deploymentForm] = Form.useForm<DeploymentRequestFormValues>();
  const [deploymentActionForm] = Form.useForm<DeploymentActionFormValues>();
  const [deploymentOpen, setDeploymentOpen] = useState(false);
  const [detailDeploymentId, setDetailDeploymentId] = useState<string>();
  const [deploymentLogState, setDeploymentLogState] = useState<{
    loading: boolean;
    logs: DeploymentRunLogRecord[];
    record?: OperationalMetricRecord;
  }>({ loading: false, logs: [] });
  const [deploymentAction, setDeploymentAction] = useState<{
    record: OperationalMetricRecord;
    type: DeploymentActionType;
  } | null>(null);
  const [deploymentRequirements, setDeploymentRequirements] = useState<RequirementRecord[]>([]);
  const [deploymentRequirementsLoading, setDeploymentRequirementsLoading] = useState(false);
  const [deploymentSchemes, setDeploymentSchemes] = useState<DeploymentSchemeRecord[]>([]);
  const [productContexts, setProductContexts] = useState<ProductContextOption[]>([]);
  const [listQuery, setListQuery] = useState<ManagementListQuery>(() => ({
    filters: initialRouteKeyword ? { keyword: initialRouteKeyword } : {},
    page: 1,
    pageSize: 10,
    sortField: 'updatedAt',
    sortOrder: 'descend',
  }));
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    performance?: RemoteListPerformance;
    rows: OperationalMetricRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({ page: 1, pageSize: 10, rows: [], status: 'loading', total: 0 });

  const [currentPermissions, setCurrentPermissions] = useState(
    () => new Set(getStoredCurrentUser()?.permissions ?? []),
  );
  const canCreate = currentPermissions.has('deployment.create');
  const canExecute = currentPermissions.has('deployment.execute');
  const canCancel = currentPermissions.has('deployment.cancel');
  const canManageSchemes = currentPermissions.has('deployment.scheme.manage');
  const selectedDeploymentProductId = Form.useWatch('productId', deploymentForm);
  const selectedDeploymentVersionId = Form.useWatch('versionId', deploymentForm);
  const selectedDeploymentEnvironment = Form.useWatch('environment', deploymentForm);
  const productOptions = useMemo(() => productOptionsFromContexts(productContexts), [productContexts]);
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
  const deploymentSchemeOptions = useMemo(
    () =>
      deploymentSchemes
        .filter(
          (scheme) =>
            scheme.status === 'active'
            && scheme.productId === selectedDeploymentProductId
            && scheme.environment === (selectedDeploymentEnvironment || deploymentDefaultEnvironment),
        )
        .map((scheme) => ({
          label: `${scheme.name} · ${deploymentMethodLabels[scheme.deploymentMethod]}`,
          value: scheme.id,
        })),
    [deploymentSchemes, selectedDeploymentEnvironment, selectedDeploymentProductId],
  );
  const productNameById = useMemo(
    () => new Map(productContexts.map((product) => [product.id, product.name])),
    [productContexts],
  );
  const versionNameById = useMemo(
    () =>
      new Map(
        productContexts.flatMap((product) =>
          (product.versions ?? []).map((version) => [version.id, version.name] as const),
        ),
      ),
    [productContexts],
  );

  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchDeploymentRequestList(deploymentListQuery(listQuery));
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        rows: result.rows.map(deploymentMetricRow),
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

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (
      activeTab !== 'requests'
      || !listState.rows.some((row) => row.status === 'deploying' || row.status === 'cancelling')
    ) {
      return;
    }
    const timer = globalThis.setInterval(() => void reload(), 5000);
    return () => globalThis.clearInterval(timer);
  }, [activeTab, listState.rows, reload]);

  useEffect(() => {
    const syncCurrentPermissions = () => {
      setCurrentPermissions(new Set(getStoredCurrentUser()?.permissions ?? []));
    };
    globalThis.addEventListener?.(AUTH_STATE_EVENT, syncCurrentPermissions);
    return () => {
      globalThis.removeEventListener?.(AUTH_STATE_EVENT, syncCurrentPermissions);
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    void Promise.all([fetchProductContextOptions(), fetchDeploymentSchemes()])
      .then(([contexts, schemes]) => {
        if (!mounted) return;
        setProductContexts(contexts);
        setDeploymentSchemes(schemes);
      })
      .catch(() => {
        if (!mounted) return;
        setProductContexts([]);
        setDeploymentSchemes([]);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!deploymentOpen || !selectedDeploymentProductId) return;
    const environment = selectedDeploymentEnvironment || deploymentDefaultEnvironment;
    const eligibleSchemes = deploymentSchemes.filter(
      (scheme) =>
        scheme.productId === selectedDeploymentProductId
        && scheme.environment === environment
        && scheme.status === 'active',
    );
    const currentSchemeId = deploymentForm.getFieldValue('deploymentSchemeId');
    if (eligibleSchemes.some((scheme) => scheme.id === currentSchemeId)) return;
    const selectedScheme = eligibleSchemes.find((scheme) => scheme.isDefault)
      ?? (eligibleSchemes.length === 1 ? eligibleSchemes[0] : undefined);
    deploymentForm.setFieldValue('deploymentSchemeId', selectedScheme?.id);
  }, [
    deploymentForm,
    deploymentOpen,
    deploymentSchemes,
    selectedDeploymentEnvironment,
    selectedDeploymentProductId,
  ]);

  useEffect(() => {
    if (!deploymentOpen || productOptions.length !== 1 || deploymentForm.getFieldValue('productId')) {
      return;
    }
    deploymentForm.setFieldValue('productId', productOptions[0]?.value);
  }, [deploymentForm, deploymentOpen, productOptions]);

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
        if (!mounted) return;
        setDeploymentRequirements(result.rows);
        const eligibleRequirements = result.rows.filter((requirement) =>
          deploymentEligibleRequirementStatuses.has(requirement.status),
        );
        if (eligibleRequirements.length === 1) {
          deploymentForm.setFieldValue('requirementIds', [eligibleRequirements[0]?.id]);
        }
      })
      .catch(() => {
        if (mounted) setDeploymentRequirements([]);
      })
      .finally(() => {
        if (mounted) setDeploymentRequirementsLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [deploymentForm, deploymentOpen, selectedDeploymentProductId, selectedDeploymentVersionId]);

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

  const openDeploymentAction = useCallback(
    (record: OperationalMetricRecord, type: DeploymentActionType) => {
      deploymentActionForm.resetFields();
      setDeploymentAction({ record, type });
    },
    [deploymentActionForm],
  );

  const deploymentWithRuns = useCallback(async (record: OperationalMetricRecord) => {
    return fetchDeploymentRequestDetail(record.id);
  }, []);

  const openDeploymentLogs = useCallback(async (record: OperationalMetricRecord) => {
    setDeploymentLogState({ loading: true, logs: [], record });
    try {
      const deployment = await deploymentWithRuns(record);
      const run = deployment.runs[0];
      if (!run) throw new Error('当前部署单还没有运行记录');
      const logs = await fetchDeploymentRunLogs(deployment.id, run.id);
      setDeploymentLogState({ loading: false, logs, record });
    } catch (error) {
      setDeploymentLogState({ loading: false, logs: [], record });
      message.error(error instanceof Error ? error.message : '部署日志加载失败');
    }
  }, [deploymentWithRuns]);

  const syncDeploymentStatus = useCallback(async (record: OperationalMetricRecord) => {
    try {
      const deployment = await deploymentWithRuns(record);
      const run = deployment.runs[0];
      if (!run) throw new Error('当前部署单还没有运行记录');
      await syncDeploymentRun(deployment.id, run.id);
      message.success('部署状态已同步');
      await reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '部署状态同步失败');
    }
  }, [deploymentWithRuns, reload]);

  const submitDeploymentAction = async () => {
    if (!deploymentAction) return;
    const values = await deploymentActionForm.validateFields();
    const sharedPayload: DeploymentStartPayload = {
      executor_type: 'manual',
      external_build_id: optionalText(values.externalBuildId),
      external_job_name: optionalText(values.externalJobName),
      log_url: optionalText(values.logUrl),
    };
    const deploymentId = deploymentAction.record.id;
    if (deploymentAction.type === 'start') {
      await startDeploymentRequest(deploymentId, {});
      message.success('部署已启动');
    } else if (deploymentAction.type === 'success') {
      await completeDeploymentRequest(deploymentId, { ...sharedPayload, status: 'success' });
      message.success('部署已标记成功');
    } else if (deploymentAction.type === 'failed' || deploymentAction.type === 'rolled_back') {
      const payload: DeploymentCompletePayload = {
        ...sharedPayload,
        failure_reason: values.failureReason?.trim(),
        status: deploymentAction.type,
      };
      await completeDeploymentRequest(deploymentId, payload);
      message.success(deploymentAction.type === 'failed' ? '部署已标记失败' : '部署已标记回滚');
    } else {
      const payload: DeploymentCancelPayload = { reason: optionalText(values.reason) };
      const cancelled = await cancelDeploymentRequest(deploymentId, payload);
      message.success(cancelled.status === 'cancelling' ? '取消请求已提交' : '部署已取消');
    }
    setDeploymentAction(null);
    deploymentActionForm.resetFields();
    await reload();
  };

  const columns = useMemo<ProColumns<OperationalMetricRecord>[]>(
    () => [
      { dataIndex: 'id', ellipsis: true, sorter: true, title: '部署编号', width: 180 },
      { dataIndex: 'name', ellipsis: true, sorter: true, title: '部署标题', width: 220 },
      {
        dataIndex: 'productId',
        render: (_, row) => productNameById.get(row.productId ?? '') ?? row.productId ?? '-',
        title: '所属产品',
        width: 160,
      },
      {
        dataIndex: 'versionId',
        render: (_, row) => versionNameById.get(row.versionId ?? '') ?? row.versionId ?? '-',
        title: '迭代版本',
        width: 160,
      },
      { dataIndex: 'environment', title: '部署环境', width: 120 },
      {
        dataIndex: 'deploymentMethod',
        render: (_, row) => deploymentMethodLabels[row.deploymentMethod ?? 'manual'],
        title: '部署方式',
        width: 120,
      },
      {
        dataIndex: 'executorChannel',
        render: (_, row) => deploymentChannelLabels[row.executorChannel ?? 'manual'],
        title: '执行通道',
        width: 120,
      },
      {
        dataIndex: 'requirementIds',
        render: (_, row) => row.requirementIds?.length ?? 0,
        title: '需求数',
        width: 90,
      },
      {
        dataIndex: 'riskLevel',
        render: (_, row) => {
          const risk = row.riskLevel ? deploymentRiskLabels[row.riskLevel] : undefined;
          return <Tag color={risk?.color ?? 'default'}>{risk?.label ?? row.riskLevel ?? '-'}</Tag>;
        },
        title: '风险等级',
        width: 110,
      },
      {
        dataIndex: 'status',
        render: (_, row) => {
          const status = deploymentStatusLabels[row.status];
          return <StatusTag color={status?.color ?? 'default'} label={status?.label ?? row.status} />;
        },
        sorter: true,
        title: '状态',
        width: 120,
      },
      { dataIndex: 'updatedAt', ellipsis: true, sorter: true, title: '更新时间', width: 160 },
      {
        fixed: 'right',
        key: 'action',
        render: (_, row) => {
          const canStart = ['approved', 'failed', 'pending_ops'].includes(row.status);
          const canComplete = row.status === 'deploying' && (row.executorChannel ?? 'manual') === 'manual';
          const rowCanCancel = !['cancelled', 'rolled_back', 'succeeded'].includes(row.status);
          const showStart = canExecute && canStart;
          const showComplete = canExecute && canComplete;
          const showCancel = canCancel && rowCanCancel;
          const showLogs = !['approved', 'draft', 'pending_ops'].includes(row.status);
          const showSync =
            canExecute
            && row.deploymentMethod === 'jenkins'
            && ['cancelling', 'deploying'].includes(row.status);
          if (!showStart && !showComplete && !showCancel && !showLogs && !showSync) {
            return '-';
          }
          return (
            <Space size={4} wrap={false}>
              <Button onClick={() => setDetailDeploymentId(row.id)} size="small" type="link">详情</Button>
              {showStart ? (
                <Button onClick={() => openDeploymentAction(row, 'start')} size="small" type="link">启动</Button>
              ) : null}
              {showComplete ? (
                <>
                  <Button onClick={() => openDeploymentAction(row, 'success')} size="small" type="link">成功</Button>
                  <Button onClick={() => openDeploymentAction(row, 'failed')} size="small" type="link">失败</Button>
                  <Button onClick={() => openDeploymentAction(row, 'rolled_back')} size="small" type="link">回滚</Button>
                </>
              ) : null}
              {showCancel ? (
                <Button danger onClick={() => openDeploymentAction(row, 'cancel')} size="small" type="link">取消</Button>
              ) : null}
              {showLogs ? (
                <Button
                  aria-label="查看部署日志"
                  icon={<FileTextOutlined />}
                  onClick={() => void openDeploymentLogs(row)}
                  size="small"
                  type="link"
                >
                  日志
                </Button>
              ) : null}
              {showSync ? (
                <Button
                  aria-label="同步部署状态"
                  icon={<SyncOutlined />}
                  onClick={() => void syncDeploymentStatus(row)}
                  size="small"
                  type="link"
                >
                  同步
                </Button>
              ) : null}
            </Space>
          );
        },
        title: '操作',
        width: 420,
      },
    ],
    [
      canCancel,
      canExecute,
      openDeploymentAction,
      openDeploymentLogs,
      productNameById,
      syncDeploymentStatus,
      versionNameById,
    ],
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
  const deploymentActionIsStart = deploymentAction?.type === 'start';

  return (
    <PageContainer
      breadcrumb={{ items: [{ title: '运营治理' }, { title: '运维部署' }] }}
      title={false}
    >
      <Tabs
        activeKey={activeTab}
        items={[
          { key: 'requests', label: '部署单' },
          { key: 'schemes', label: '部署方案' },
        ]}
        onChange={setActiveTab}
      />
      {activeTab === 'requests' ? (
        <ManagementListPage<OperationalMetricRecord>
        embedded
        breadcrumbGroup="运营治理"
        columns={columns}
        dataSource={listState.rows}
        filters={[
          { label: '部署关键字', name: 'keyword', type: 'text' },
          { label: '状态', name: 'status', options: deploymentStatusOptions, type: 'select' },
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
        tableScroll={{ x: 2020 }}
        tableTitle="部署单列表"
        title="运维部署"
        toolbarActions={
          canCreate
            ? [
                <Button key="deployment-request" onClick={() => setDeploymentOpen(true)} type="primary">
                  发起部署
                </Button>,
              ]
            : []
        }
        viewStorageKey="governance.deployments"
        />
      ) : (
        <DeploymentSchemePanel
          canManage={canManageSchemes}
          onSchemesChanged={setDeploymentSchemes}
          productContexts={productContexts}
        />
      )}
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
        <Form<DeploymentRequestFormValues>
          form={deploymentForm}
          initialValues={{ environment: deploymentDefaultEnvironment, riskLevel: 'medium' }}
          layout="vertical"
        >
          <Form.Item label="所属产品" name="productId" rules={[{ required: true, message: '请选择所属产品' }]}>
            <Select
              onChange={() => {
                deploymentForm.setFieldsValue({ deploymentSchemeId: undefined, requirementIds: [], versionId: undefined });
                setDeploymentRequirements([]);
              }}
              options={productOptions}
            />
          </Form.Item>
          <Form.Item label="产品版本" name="versionId" rules={[{ required: true, message: '请选择产品版本' }]}>
            <Select onChange={() => deploymentForm.setFieldValue('requirementIds', [])} options={deploymentVersionOptions} />
          </Form.Item>
          <Form.Item label="部署标题" name="title" rules={[{ required: true, message: '请输入部署标题' }]}>
            <Input placeholder="例如：生产环境发布 2026.07.10" />
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
          <Form.Item label="部署环境" name="environment" rules={[{ required: true, message: '请选择部署环境' }]}>
            <Select
              onChange={() => deploymentForm.setFieldValue('deploymentSchemeId', undefined)}
              options={[
                { label: '开发环境', value: 'dev' },
                { label: '测试环境', value: 'test' },
                { label: '预发布环境', value: 'staging' },
                { label: '生产环境', value: 'prod' },
                { label: '沙箱环境', value: 'sandbox' },
              ]}
            />
          </Form.Item>
          <Form.Item label="部署方案" name="deploymentSchemeId" rules={[{ required: true, message: '请选择部署方案' }]}>
            <Select
              disabled={!selectedDeploymentProductId}
              options={deploymentSchemeOptions}
              placeholder={selectedDeploymentProductId ? '请选择当前产品和环境的部署方案' : '请先选择所属产品'}
            />
          </Form.Item>
          <Form.Item label="风险等级" name="riskLevel"><Select options={deploymentRiskOptions} /></Form.Item>
          <Form.Item label="发布分支" name="releaseBranch"><Input placeholder="release/2026.07" /></Form.Item>
          <Form.Item label="Commit SHA" name="commitSha"><Input /></Form.Item>
          <Form.Item label="制品版本" name="artifactVersion"><Input /></Form.Item>
          <Form.Item
            label="制品 SHA-256"
            name="artifactDigest"
            rules={[
              {
                pattern: /^sha256:[0-9a-fA-F]{64}$/,
                message: '请输入 sha256: 开头的完整制品摘要',
              },
            ]}
          >
            <Input placeholder="sha256:..." />
          </Form.Item>
          <Form.Item label="部署窗口开始" name="deployWindowStart">
            <DateStringPicker mode="dateTime" placeholder="请选择部署窗口开始时间" />
          </Form.Item>
          <Form.Item label="部署窗口结束" name="deployWindowEnd">
            <DateStringPicker mode="dateTime" placeholder="请选择部署窗口结束时间" />
          </Form.Item>
          <Form.Item label="运维负责人" name="assignedOpsUser"><Input placeholder="用户 ID 或账号" /></Form.Item>
          <Form.Item label="发布评估任务 ID" name="releaseReadinessTaskId">
            <Input placeholder="可选，关联已确认的发布评估任务" />
          </Form.Item>
          <Form.Item label="回滚方案" name="rollbackPlan"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
      <Drawer
        onClose={() => setDeploymentLogState({ loading: false, logs: [] })}
        open={Boolean(deploymentLogState.record)}
        title={`部署日志 · ${deploymentLogState.record?.name ?? ''}`}
        size="large"
      >
        <Spin spinning={deploymentLogState.loading}>
          {deploymentLogState.logs.length ? (
            <Space orientation="vertical" size={12} style={{ width: '100%' }}>
              {deploymentLogState.logs.map((log, index) => (
                <div key={`${log.createdAt ?? 'log'}-${index}`}>
                  <Space align="start" orientation="vertical" size={4} style={{ width: '100%' }}>
                    <Space size={8} wrap>
                      <Tag color={log.level === 'error' ? 'red' : log.level === 'warning' ? 'orange' : 'blue'}>
                        {log.level.toUpperCase()}
                      </Tag>
                      <Tag>{log.source}</Tag>
                      <Typography.Text type="secondary">{log.createdAt ?? '-'}</Typography.Text>
                    </Space>
                    <Typography.Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {log.message}
                    </Typography.Text>
                  </Space>
                </div>
              ))}
            </Space>
          ) : deploymentLogState.loading ? null : <Empty description="暂无部署日志" />}
        </Spin>
      </Drawer>
      <DeploymentDetailDrawer
        deploymentId={detailDeploymentId}
        onClose={() => setDetailDeploymentId(undefined)}
      />
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
          <Form.Item label="部署单"><Input disabled value={deploymentAction?.record.name ?? '-'} /></Form.Item>
          <Form.Item label="部署方式">
            <Input
              disabled
              value={deploymentMethodLabels[deploymentAction?.record.deploymentMethod ?? 'manual']}
            />
          </Form.Item>
          <Form.Item label="执行通道">
            <Input
              disabled
              value={deploymentChannelLabels[deploymentAction?.record.executorChannel ?? 'manual']}
            />
          </Form.Item>
          {deploymentActionIsCancel ? (
            <Form.Item label="取消原因" name="reason"><Input.TextArea rows={3} /></Form.Item>
          ) : deploymentActionIsStart ? null : (
            <>
              <Form.Item label="外部 Job" name="externalJobName"><Input placeholder="Jenkins Job / Pipeline" /></Form.Item>
              <Form.Item label="外部 Build ID" name="externalBuildId"><Input /></Form.Item>
              <Form.Item label="日志链接" name="logUrl"><Input /></Form.Item>
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
    </PageContainer>
  );
}
