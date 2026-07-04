import type { ProColumns } from '@ant-design/pro-components';
import { Button, DatePicker, Form, Input, Modal, Select, Space, Tag, Typography, message } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import {
  fetchActiveProductOptions,
  fetchCodeInspectionDashboard,
  fetchCodeInspectionDetail,
  fetchCodeInspectionReports,
  fullChainSubjectHref,
  requestCodeInspectionFindingSuppression,
  reviewCodeInspectionFindingSuppression,
  type CodeInspectionDashboardRecord,
  type CodeInspectionFindingRecord,
  type CodeInspectionListQuery,
  type CodeInspectionReportRecord,
  type ProductFilterOption,
  type RemoteListPerformance,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { formatMutationError } from '../../utils/managementCrud';
import { CodeInspectionDetailModal, type CodeInspectionDetailState } from './components/CodeInspectionDetailModal';
import { CodeInspectionGovernanceOverview } from './components/CodeInspectionGovernanceOverview';
import {
  committerSummaryText,
  compactText,
  riskColorByValue,
} from './components/codeInspectionPresentation';

const sortFieldMap: Record<string, string> = {
  createdAt: 'created_at',
  committerCount: 'committer_count',
  findingCount: 'finding_count',
  id: 'id',
  riskLevel: 'risk_level',
  severeFindingCount: 'severe_finding_count',
  status: 'status',
};
const allProductsValue = '__all_products__';

type AcceptedRiskFormValues = {
  expires_at?: Dayjs;
  note?: string;
  owner?: string;
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildCodeInspectionQuery(
  query: ManagementListQuery,
  productId?: string,
): CodeInspectionListQuery {
  return {
    committer: normalizeFilterText(query.filters.committer),
    page: query.page,
    pageSize: query.pageSize,
    productId,
    riskLevel: normalizeFilterText(query.filters.riskLevel),
    sortField: query.sortField ? sortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
    title: normalizeFilterText(query.filters.title),
  };
}

function readCodeInspectionInitialProductId() {
  const search = new URLSearchParams(window.location.search);
  return search.get('product_id')?.trim() || undefined;
}

function productOptionLabel(product: ProductFilterOption) {
  return `${product.code} · ${product.name}`;
}

function productDisplayText(row: CodeInspectionReportRecord) {
  if (row.product_code && row.product_name) {
    return `${row.product_code} · ${row.product_name}`;
  }
  return row.product_name || row.product_code || row.product_id;
}

function codeInspectionFullChainHref(row: CodeInspectionReportRecord) {
  if (!row.full_chain_available) {
    return undefined;
  }
  const subjectType = row.full_chain_subject_type || 'code_inspection_report';
  const subjectId = row.full_chain_subject_id || row.id;
  return fullChainSubjectHref(subjectType, subjectId);
}

function fullChainUnavailableText(row: CodeInspectionReportRecord) {
  if (row.full_chain_unavailable_reason === 'NO_REQUIREMENT_CONTEXT') {
    return '该巡检报告未关联需求全链路';
  }
  return '该巡检报告暂不可打开全链路';
}

function readCodeInspectionDeepLinkReportId() {
  const search = new URLSearchParams(window.location.search);
  const sourceType = search.get('source_type');
  if (sourceType && sourceType !== 'code_inspection_report') {
    return undefined;
  }
  return search.get('report_id') ?? search.get('source_id') ?? undefined;
}

export default function CodeInspectionsPage() {
  const [acceptedRiskForm] = Form.useForm<AcceptedRiskFormValues>();
  const deepLinkReportId = useMemo(() => readCodeInspectionDeepLinkReportId(), []);
  const initialProductId = useMemo(() => readCodeInspectionInitialProductId(), []);
  const isDeepLinkHandledRef = useRef(false);
  const [acceptedRiskFinding, setAcceptedRiskFinding] = useState<CodeInspectionFindingRecord>();
  const [acceptedRiskSubmitting, setAcceptedRiskSubmitting] = useState(false);
  const [detailState, setDetailState] = useState<CodeInspectionDetailState>();
  const [suppressionActionLoading, setSuppressionActionLoading] = useState<string>();
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'createdAt',
    sortOrder: 'descend',
  });
  const [productOptionsSource, setProductOptionsSource] = useState<ProductFilterOption[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string | undefined>(initialProductId);
  const [listState, setListState] = useState<{
    page: number;
    pageSize: number;
    performance?: RemoteListPerformance;
    rows: CodeInspectionReportRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const [dashboardState, setDashboardState] = useState<{
    dashboard?: CodeInspectionDashboardRecord;
    status: 'error' | 'loading' | 'ready';
  }>({ status: 'loading' });

  const productOptions = useMemo(
    () => [
      { label: '全部产品', value: allProductsValue },
      ...productOptionsSource.map((product) => ({
        label: productOptionLabel(product),
        value: product.id,
      })),
    ],
    [productOptionsSource],
  );
  const selectedProduct = productOptionsSource.find((product) => product.id === selectedProductId);
  const selectedProductLabel = selectedProduct ? productOptionLabel(selectedProduct) : '全部产品';

  useEffect(() => {
    let isCurrent = true;
    void fetchActiveProductOptions()
      .then((items) => {
        if (isCurrent) {
          setProductOptionsSource(items);
        }
      })
      .catch((error) => {
        if (isCurrent) {
          setProductOptionsSource([]);
          message.error(formatMutationError(error));
        }
      });
    return () => {
      isCurrent = false;
    };
  }, []);

  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    setDashboardState((current) => ({ ...current, status: 'loading' }));
    try {
      const query = buildCodeInspectionQuery(listQuery, selectedProductId);
      const [result, dashboard] = await Promise.all([
        fetchCodeInspectionReports(query),
        fetchCodeInspectionDashboard(query),
      ]);
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        performance: result.performance,
        rows: result.rows,
        status: 'ready',
        total: result.total,
      });
      setDashboardState({ dashboard, status: 'ready' });
    } catch (error) {
      message.error(formatMutationError(error));
      setListState((current) => ({ ...current, rows: [], status: 'error' }));
      setDashboardState((current) => ({ ...current, status: 'error' }));
    }
  }, [listQuery, selectedProductId]);

  useEffect(() => {
    queueMicrotask(() => {
      void reload();
    });
  }, [reload]);

  const openDetailById = useCallback(async (reportId: string, report?: CodeInspectionReportRecord) => {
    setDetailState({
      loading: true,
      report: report ?? {
        finding_count: 0,
        id: reportId,
        risk_level: '-',
        severe_finding_count: 0,
        status: '-',
      },
    });
    try {
      const detail = await fetchCodeInspectionDetail(reportId);
      setDetailState({ detail, loading: false, report: detail.report });
    } catch (error) {
      setDetailState(undefined);
      message.error(formatMutationError(error));
    }
  }, []);

  const openDetail = useCallback((report: CodeInspectionReportRecord) => {
    void openDetailById(report.id, report);
  }, [openDetailById]);

  const handleProductChange = useCallback((value: string) => {
    setSelectedProductId(value === allProductsValue ? undefined : value);
    setListQuery((current) => ({ ...current, page: 1 }));
  }, []);

  useEffect(() => {
    if (!deepLinkReportId || isDeepLinkHandledRef.current) {
      return;
    }
    isDeepLinkHandledRef.current = true;
    void openDetailById(deepLinkReportId);
  }, [deepLinkReportId, openDetailById]);

  const closeAcceptedRiskModal = useCallback(() => {
    setAcceptedRiskFinding(undefined);
    acceptedRiskForm.resetFields();
  }, [acceptedRiskForm]);

  const openAcceptedRiskModal = useCallback(
    (finding: CodeInspectionFindingRecord) => {
      setAcceptedRiskFinding(finding);
      acceptedRiskForm.setFieldsValue({
        expires_at: dayjs().add(30, 'day'),
        note: '临时接受风险，到期后复核',
        owner:
          finding.suppression_owner ||
          finding.committer_email ||
          finding.committer_username ||
          finding.committer_name ||
          '',
      });
    },
    [acceptedRiskForm],
  );

  const submitAcceptedRisk = useCallback(async () => {
    const reportId = detailState?.report?.id ?? detailState?.detail?.report.id;
    const finding = acceptedRiskFinding;
    if (!reportId || !finding) {
      return;
    }
    const values = await acceptedRiskForm.validateFields();
    setAcceptedRiskSubmitting(true);
    try {
      const detail = await requestCodeInspectionFindingSuppression(reportId, finding.id, {
        expires_at: values.expires_at?.toISOString(),
        note: values.note?.trim() || '临时接受风险，到期后复核',
        owner: values.owner?.trim() || undefined,
        reason: 'accepted_risk',
      });
      setDetailState({ detail, loading: false, report: detail.report });
      message.success('已提交接受风险审批');
      closeAcceptedRiskModal();
      void reload();
    } catch (error) {
      message.error(formatMutationError(error));
    } finally {
      setAcceptedRiskSubmitting(false);
    }
  }, [
    acceptedRiskFinding,
    acceptedRiskForm,
    closeAcceptedRiskModal,
    detailState?.detail?.report.id,
    detailState?.report?.id,
    reload,
  ]);

  const handleSuppressionAction = useCallback(
    async (finding: CodeInspectionFindingRecord, action: 'approve' | 'reject' | 'request') => {
      const reportId = detailState?.report?.id ?? detailState?.detail?.report.id;
      if (!reportId) {
        return;
      }
      const loadingKey = `${action}:${finding.id}`;
      setSuppressionActionLoading(loadingKey);
      try {
        const detail =
          action === 'request'
            ? await requestCodeInspectionFindingSuppression(reportId, finding.id, {
                note: '从代码巡检详情申请误报忽略',
                reason: 'false_positive',
              })
            : await reviewCodeInspectionFindingSuppression(reportId, finding.id, {
                decision: action,
                note: action === 'approve' ? '确认误报，批准忽略' : '不符合忽略条件',
              });
        setDetailState({ detail, loading: false, report: detail.report });
        message.success(
          action === 'request' ? '已提交忽略审批' : action === 'approve' ? '已批准忽略' : '已驳回忽略申请',
        );
        void reload();
      } catch (error) {
        message.error(formatMutationError(error));
      } finally {
        setSuppressionActionLoading(undefined);
      }
    },
    [detailState?.detail?.report.id, detailState?.report?.id, reload],
  );

  const columns = useMemo<ProColumns<CodeInspectionReportRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        sorter: true,
        title: '报告 ID',
        width: 190,
        render: (_, row) => compactText(row.id),
      },
      {
        dataIndex: 'product_id',
        title: '产品',
        width: 190,
        render: (_, row) => compactText(productDisplayText(row)),
      },
      {
        dataIndex: 'repository_name',
        title: '仓库',
        width: 190,
        render: (_, row) => compactText(row.repository_name || row.repository_path || row.repository_id),
      },
      {
        dataIndex: 'branch',
        title: '分支',
        width: 120,
        render: (_, row) => compactText(row.branch),
      },
      {
        dataIndex: 'committerCount',
        sorter: true,
        title: '提交人',
        width: 220,
        render: (_, row) => compactText(committerSummaryText(row)),
      },
      {
        dataIndex: 'riskLevel',
        sorter: true,
        title: '风险级别',
        width: 120,
        render: (_, row) => (
          <Tag color={riskColorByValue.get(row.risk_level) ?? 'default'}>{row.risk_level}</Tag>
        ),
      },
      {
        dataIndex: 'findingCount',
        sorter: true,
        title: '问题数',
        width: 100,
        render: (_, row) => row.finding_count,
      },
      {
        dataIndex: 'severeFindingCount',
        sorter: true,
        title: '严重问题',
        width: 120,
        render: (_, row) => row.severe_finding_count,
      },
      {
        dataIndex: 'status',
        sorter: true,
        title: '状态',
        width: 100,
        render: (_, row) =>
          row.status === 'completed' ? (
            <StatusTag color="green" label="已完成" />
          ) : (
            <StatusTag color="red" label={row.status} />
          ),
      },
      {
        dataIndex: 'summary',
        title: '摘要',
        width: 280,
        render: (_, row) => compactText(row.summary),
      },
      {
        dataIndex: 'createdAt',
        sorter: true,
        title: '创建时间',
        width: 160,
        render: (_, row) => compactText(formatDisplayDateTime(row.created_at)),
      },
      {
        fixed: 'right',
        key: 'actions',
        title: '操作',
        valueType: 'option',
        width: 150,
        render: (_, row) => {
          const fullChainHref = codeInspectionFullChainHref(row);
          return (
            <Space size={4}>
              {fullChainHref ? (
                <Button href={fullChainHref} type="link">
                  全链路
                </Button>
              ) : (
                <Button disabled title={fullChainUnavailableText(row)} type="link">
                  全链路
                </Button>
              )}
              <Button onClick={() => void openDetail(row)} type="link">
                详情
              </Button>
            </Space>
          );
        },
      },
    ],
    [openDetail],
  );

  return (
    <>
      <div className="code-inspections-page">
        <ManagementListPage<CodeInspectionReportRecord>
          beforeTable={
            <>
              <div className="code-inspections-scope-bar">
                <Space className="code-inspections-scope-main" size={12} wrap>
                  <Typography.Text strong>产品范围</Typography.Text>
                  <Select
                    aria-label="产品范围"
                    className="code-inspections-product-select"
                    onChange={handleProductChange}
                    optionFilterProp="label"
                    options={productOptions}
                    showSearch
                    value={selectedProductId ?? allProductsValue}
                  />
                  <Typography.Text type="secondary">
                    当前范围：{selectedProductLabel}
                  </Typography.Text>
                </Space>
                <Button
                  aria-label="刷新代码巡检"
                  className="code-inspections-scope-refresh"
                  loading={listState.status === 'loading' || dashboardState.status === 'loading'}
                  onClick={() => void reload()}
                >
                  刷新
                </Button>
              </div>
              <CodeInspectionGovernanceOverview
                dashboard={dashboardState.dashboard}
                loading={dashboardState.status === 'loading'}
              />
            </>
          }
          breadcrumbGroup="运营治理"
          columns={columns}
          dataSource={listState.rows}
          viewStorageKey="governance.code_inspections"
          filters={[
            { label: '报告/摘要', name: 'title', type: 'text' },
            { label: '提交人', name: 'committer', placeholder: '姓名 / 邮箱 / 用户名', type: 'text' },
            {
              label: '风险级别',
              name: 'riskLevel',
              options: [
                { label: 'critical', value: 'critical' },
                { label: 'high', value: 'high' },
                { label: 'medium', value: 'medium' },
                { label: 'low', value: 'low' },
              ],
              type: 'select',
            },
            {
              label: '状态',
              name: 'status',
              options: [
                { label: '已完成', value: 'completed' },
                { label: '部分完成', value: 'partial' },
                { label: '失败', value: 'failed' },
              ],
              type: 'select',
            },
          ]}
          loading={listState.status === 'loading'}
          onReload={reload}
          remote={{
            onChange: setListQuery,
            page: listState.page,
            pageSize: listState.pageSize,
            performance: listState.performance,
            total: listState.total,
          }}
          rowKey="id"
          tableTitle="代码巡检"
          title="代码巡检"
        />
      </div>

      <CodeInspectionDetailModal
        detailState={detailState}
        suppressionActionLoading={suppressionActionLoading}
        onClose={() => setDetailState(undefined)}
        onOpenAcceptedRisk={openAcceptedRiskModal}
        onSuppressionAction={handleSuppressionAction}
      />
      <Modal
        aria-label="接受风险"
        destroyOnHidden
        confirmLoading={acceptedRiskSubmitting}
        okText="提交接受风险"
        open={Boolean(acceptedRiskFinding)}
        title="接受风险"
        onCancel={closeAcceptedRiskModal}
        onOk={() => void submitAcceptedRisk()}
      >
        <Form form={acceptedRiskForm} layout="vertical">
          <Form.Item label="责任人" name="owner">
            <Input placeholder="默认使用提交人，可按实际责任人调整" />
          </Form.Item>
          <Form.Item
            label="到期时间"
            name="expires_at"
            rules={[
              { required: true, message: '请选择到期时间' },
              {
                validator: (_, value: Dayjs | undefined) => {
                  if (!value || value.isAfter(dayjs())) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('到期时间需晚于当前时间'));
                },
              },
            ]}
          >
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="接受说明" name="note">
            <Input.TextArea
              placeholder="说明接受原因、补偿控制或复核要求"
              rows={3}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
