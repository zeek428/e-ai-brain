import type { ProColumns } from '@ant-design/pro-components';
import { Button, Descriptions, Modal, Space, Table, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import {
  fetchCodeInspectionDetail,
  fetchCodeInspectionReports,
  type CodeInspectionDetailRecord,
  type CodeInspectionFindingRecord,
  type CodeInspectionListQuery,
  type CodeInspectionNotificationRecord,
  type CodeInspectionReportRecord,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';

const riskColorByValue = new Map([
  ['critical', 'red'],
  ['high', 'orange'],
  ['medium', 'gold'],
  ['low', 'green'],
]);

const severityColorByValue = new Map([
  ['critical', 'red'],
  ['high', 'orange'],
  ['medium', 'gold'],
  ['low', 'green'],
  ['info', 'blue'],
]);

const sortFieldMap: Record<string, string> = {
  createdAt: 'created_at',
  committerCount: 'committer_count',
  findingCount: 'finding_count',
  id: 'id',
  riskLevel: 'risk_level',
  severeFindingCount: 'severe_finding_count',
  status: 'status',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildCodeInspectionQuery(query: ManagementListQuery): CodeInspectionListQuery {
  return {
    committer: normalizeFilterText(query.filters.committer),
    page: query.page,
    pageSize: query.pageSize,
    riskLevel: normalizeFilterText(query.filters.riskLevel),
    sortField: query.sortField ? sortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
    title: normalizeFilterText(query.filters.title),
  };
}

function compactText(value?: string | null) {
  const text = value || '-';
  return (
    <Typography.Text ellipsis={{ tooltip: text }} style={{ display: 'block', maxWidth: '100%' }}>
      {text}
    </Typography.Text>
  );
}

function committerLabel(
  value?: {
    email?: string | null;
    finding_count?: number;
    name?: string | null;
    username?: string | null;
  } | null,
) {
  if (!value) {
    return '-';
  }
  const identity = value.name || value.username || value.email || '-';
  const email = value.email && value.email !== identity ? ` <${value.email}>` : '';
  const count = value.finding_count ? ` (${value.finding_count})` : '';
  return `${identity}${email}${count}`;
}

function committerSummaryText(row: CodeInspectionReportRecord) {
  const summary = row.committer_summary ?? [];
  if (!summary.length) {
    return '-';
  }
  return summary.slice(0, 3).map(committerLabel).join('、');
}

function bugLink(value?: string | null) {
  if (!value) {
    return '-';
  }
  return (
    <Typography.Link href={`/delivery/bugs?title=${encodeURIComponent(value)}`}>
      {value}
    </Typography.Link>
  );
}

export default function CodeInspectionsPage() {
  const [detailState, setDetailState] = useState<{
    detail?: CodeInspectionDetailRecord;
    loading: boolean;
    report?: CodeInspectionReportRecord;
  }>();
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'createdAt',
    sortOrder: 'descend',
  });
  const [listState, setListState] = useState<{
    page: number;
    pageSize: number;
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

  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchCodeInspectionReports(buildCodeInspectionQuery(listQuery));
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        rows: result.rows,
        status: 'ready',
        total: result.total,
      });
    } catch (error) {
      message.error(formatMutationError(error));
      setListState((current) => ({ ...current, rows: [], status: 'error' }));
    }
  }, [listQuery]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const openDetail = useCallback(async (report: CodeInspectionReportRecord) => {
    setDetailState({ loading: true, report });
    try {
      const detail = await fetchCodeInspectionDetail(report.id);
      setDetailState({ detail, loading: false, report });
    } catch (error) {
      setDetailState(undefined);
      message.error(formatMutationError(error));
    }
  }, []);

  const columns = useMemo<ProColumns<CodeInspectionReportRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        sorter: true,
        title: '报告 ID',
        width: 210,
        render: (_, row) => compactText(row.id),
      },
      {
        dataIndex: 'repository_name',
        title: '仓库',
        width: 220,
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
        width: 260,
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
        width: 110,
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
        width: 320,
        render: (_, row) => compactText(row.summary),
      },
      {
        dataIndex: 'createdAt',
        sorter: true,
        title: '创建时间',
        width: 180,
        render: (_, row) => compactText(row.created_at),
      },
      {
        fixed: 'right',
        key: 'actions',
        title: '操作',
        valueType: 'option',
        width: 110,
        render: (_, row) => (
          <Button onClick={() => void openDetail(row)} type="link">
            详情
          </Button>
        ),
      },
    ],
    [openDetail],
  );

  return (
    <>
      <ManagementListPage<CodeInspectionReportRecord>
        breadcrumbGroup="运营治理"
        columns={columns}
        dataSource={listState.rows}
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
          total: listState.total,
        }}
        rowKey="id"
        tableScroll={{ x: 1740 }}
        tableTitle="代码巡检"
        title="代码巡检"
        toolbarActions={[
          <Button key="reload" onClick={reload}>
            刷新
          </Button>,
        ]}
      />

      <Modal
        footer={<Button onClick={() => setDetailState(undefined)}>关闭</Button>}
        open={Boolean(detailState)}
        title="代码巡检详情"
        width={1040}
        onCancel={() => setDetailState(undefined)}
      >
        {detailState?.loading ? (
          <Typography.Text type="secondary">详情加载中...</Typography.Text>
        ) : detailState?.detail ? (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions
              bordered
              column={2}
              size="small"
              items={[
                { key: 'id', label: '报告 ID', children: detailState.detail.report.id },
                { key: 'risk', label: '风险级别', children: detailState.detail.report.risk_level },
                { key: 'repository', label: '仓库', children: detailState.detail.report.repository_name || '-' },
                { key: 'branch', label: '分支', children: detailState.detail.report.branch || '-' },
                { key: 'committer_count', label: '提交人数', children: detailState.detail.report.committer_count ?? 0 },
                {
                  key: 'committers',
                  label: '主要提交人',
                  children: committerSummaryText(detailState.detail.report),
                },
                { key: 'finding_count', label: '问题数', children: detailState.detail.report.finding_count },
                { key: 'severe_count', label: '严重问题', children: detailState.detail.report.severe_finding_count },
                { key: 'bugs', label: '创建 Bug', children: detailState.detail.report.created_bug_ids?.join('、') || '-' },
                { key: 'summary', label: '摘要', children: detailState.detail.report.summary || '-' },
              ]}
            />
            <Table<CodeInspectionFindingRecord>
              columns={[
                {
                  dataIndex: 'severity',
                  title: '级别',
                  width: 100,
                  render: (value) => <Tag color={severityColorByValue.get(String(value))}>{String(value)}</Tag>,
                },
                { dataIndex: 'category', title: '分类', width: 110 },
                { dataIndex: 'rule_id', title: '规则', width: 120 },
                { dataIndex: 'title', title: '问题', width: 220 },
                {
                  dataIndex: 'committer_email',
                  title: '提交人',
                  width: 260,
                  render: (_, row) =>
                    compactText(
                      committerLabel({
                        email: row.committer_email,
                        name: row.committer_name,
                        username: row.committer_username,
                      }),
                    ),
                },
                {
                  dataIndex: 'file_path',
                  title: '位置',
                  width: 260,
                  render: (_, row) => compactText(`${row.file_path || '-'}${row.line_number ? `:${row.line_number}` : ''}`),
                },
                { dataIndex: 'created_bug_id', title: 'Bug', width: 150, render: (value) => bugLink(String(value ?? '')) },
                { dataIndex: 'recommendation', title: '建议', render: (value) => compactText(String(value ?? '')) },
              ]}
              dataSource={detailState.detail.findings}
              pagination={false}
              rowKey="id"
              scroll={{ x: 1460 }}
              size="small"
            />
            <Table<CodeInspectionNotificationRecord>
              columns={[
                { dataIndex: 'channel', title: '渠道', width: 120 },
                { dataIndex: 'target', title: '目标', width: 320, render: (value) => compactText(String(value ?? '')) },
                { dataIndex: 'status', title: '状态', width: 120 },
                { dataIndex: 'message', title: '消息', render: (value) => compactText(String(value ?? '')) },
              ]}
              dataSource={detailState.detail.notifications}
              pagination={false}
              rowKey="id"
              size="small"
            />
          </Space>
        ) : null}
      </Modal>
    </>
  );
}
