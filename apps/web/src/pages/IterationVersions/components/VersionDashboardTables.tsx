import { LinkOutlined } from '@ant-design/icons';
import { Button, Empty, Space, Table, Tag, Typography } from 'antd';

import { StatusTag } from '../../../components/ManagementListPage';
import type { ProductVersionBranchConfigRecord, RequirementRecord } from '../../../data/management';
import { fullChainSubjectHref, type ProductVersionDashboard } from '../../../services/aiBrain';
import {
  blockerActionHref,
  blockerSubjectType,
  buildBlockerActionQueue,
  dashboardBlockerSourceLabels,
  dashboardDate,
  internalHref,
  type DashboardStatusImpactRow,
  type LabelItem,
} from './versionDashboardModel';

const { Text } = Typography;

function dashboardStatusTag(value: string | null | undefined, statusLabelMap: Record<string, LabelItem>) {
  const key = String(value ?? '-');
  const item = statusLabelMap[key] ?? { color: 'default', label: key };
  return <Tag color={item.color}>{item.label}</Tag>;
}

const knowledgeIndexStatusLabelMap: Record<string, LabelItem> = {
  archived: { color: 'default', label: '已归档' },
  importing: { color: 'processing', label: '导入中' },
  indexed: { color: 'green', label: '已索引' },
  index_failed: { color: 'red', label: '索引失败' },
  missing: { color: 'red', label: '文档缺失' },
  pending_index: { color: 'processing', label: '待索引' },
  text_indexed: { color: 'gold', label: '关键词可检索' },
  vector_indexed: { color: 'green', label: '向量可检索' },
};

const knowledgeRetrievalModeLabelMap: Record<string, LabelItem> = {
  hybrid: { color: 'green', label: '混合检索' },
  keyword: { color: 'gold', label: '关键词兜底' },
  unavailable: { color: 'red', label: '不可检索' },
};

type VersionDashboardStatusImpactTableProps = {
  rows: DashboardStatusImpactRow[];
  statusLabelMap: Record<string, LabelItem>;
};

export function VersionDashboardStatusImpactTable({ rows, statusLabelMap }: VersionDashboardStatusImpactTableProps) {
  return (
    <div>
      <Text strong>推进影响明细</Text>
      <Table<DashboardStatusImpactRow>
        columns={[
          {
            dataIndex: 'impact',
            render: (value, row) => {
              const color = value === 'blocked' ? 'red' : value === 'updated' ? 'blue' : 'default';
              return <Tag color={color}>{row.impactLabel}</Tag>;
            },
            title: '影响',
            width: 120,
          },
          {
            dataIndex: 'id',
            render: (value) => (
              <Typography.Link
                href={internalHref('/delivery/requirements', {
                  requirement_id: String(value),
                })}
              >
                {String(value)}
              </Typography.Link>
            ),
            title: '需求编号',
            width: 160,
          },
          {
            dataIndex: 'title',
            render: (value) => (
              <Text ellipsis style={{ maxWidth: 260 }}>
                {String(value ?? '-')}
              </Text>
            ),
            title: '需求标题',
            width: 280,
          },
          {
            dataIndex: 'from_status',
            render: (value) => dashboardStatusTag(String(value ?? '-'), statusLabelMap),
            title: '当前状态',
            width: 130,
          },
          {
            dataIndex: 'to_status',
            render: (value) =>
              value ? dashboardStatusTag(String(value), statusLabelMap) : <Text type="secondary">-</Text>,
            title: '目标状态',
            width: 130,
          },
          {
            dataIndex: 'block_reason',
            render: (value) => (
              <Text ellipsis style={{ maxWidth: 280 }}>
                {String(value ?? '-')}
              </Text>
            ),
            title: '说明',
          },
          {
            key: 'action',
            render: (_, row) => (
              <Button
                href={fullChainSubjectHref('requirement', row.id)}
                icon={<LinkOutlined />}
                size="small"
                type="link"
              >
                全链路
              </Button>
            ),
            title: '操作',
            width: 110,
          },
        ]}
        dataSource={rows}
        locale={{ emptyText: '下一阶段暂无需求状态影响' }}
        pagination={rows.length > 5 ? { pageSize: 5 } : false}
        rowKey={(row) => `${row.impact}-${row.id}`}
        scroll={{ x: 1090 }}
        size="small"
      />
    </div>
  );
}

type VersionDashboardBlockersTableProps = {
  dashboard: ProductVersionDashboard;
  statusLabelMap: Record<string, LabelItem>;
};

export function VersionDashboardBlockersTable({ dashboard, statusLabelMap }: VersionDashboardBlockersTableProps) {
  const blockerActionQueue = buildBlockerActionQueue(dashboard);

  return (
    <div>
      <Text strong>阻塞项</Text>
      {blockerActionQueue.length ? (
        <div style={{ marginTop: 10, marginBottom: 12 }}>
          <Space align="baseline" style={{ display: 'flex', marginBottom: 8 }} wrap>
            <Text strong>阻塞处理队列</Text>
            <Text type="secondary">按严重级别、来源类型和处理入口排序，优先处理发布准入风险。</Text>
          </Space>
          <Space size={8} style={{ display: 'flex' }} wrap>
            {blockerActionQueue.map((item) => {
              const severity = statusLabelMap[String(item.severity)] ?? {
                color: 'default',
                label: String(item.severity ?? '-'),
              };
              return (
                <div
                  key={`${item.sourceType}-${item.id ?? item.title}-queue`}
                  style={{
                    border: '1px solid #f0f0f0',
                    borderRadius: 6,
                    minHeight: 142,
                    padding: 12,
                    width: 300,
                  }}
                >
                  <Space size={4} style={{ display: 'flex' }} wrap>
                    <Tag color="blue">优先级 {item.priority}</Tag>
                    <Tag color={severity.color}>
                      {severity.label} · {item.sourceLabel}
                    </Tag>
                  </Space>
                  <div style={{ marginTop: 8 }}>
                    <Text strong ellipsis style={{ maxWidth: 260 }}>
                      {String(item.title ?? '-')}
                    </Text>
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary">{String(item.reason ?? '-')}</Text>
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary">解除条件：{String(item.resolutionHint ?? '-')}</Text>
                  </div>
                  <Space size={4} style={{ marginTop: 8 }} wrap>
                    {item.actionHref ? (
                      <Button href={item.actionHref} size="small" type="link">
                        {item.actionLabel}
                      </Button>
                    ) : null}
                    {item.fullChainHref ? (
                      <Button href={item.fullChainHref} icon={<LinkOutlined />} size="small" type="link">
                        全链路
                      </Button>
                    ) : null}
                  </Space>
                </div>
              );
            })}
          </Space>
        </div>
      ) : null}
      <Table<ProductVersionDashboard['blockers'][number]>
        columns={[
          {
            dataIndex: 'sourceType',
            render: (value) => dashboardBlockerSourceLabels[String(value)] ?? String(value ?? '-'),
            title: '来源',
            width: 120,
          },
          {
            dataIndex: 'title',
            render: (value) => (
              <Text ellipsis style={{ maxWidth: 220 }}>
                {String(value ?? '-')}
              </Text>
            ),
            title: '标题',
            width: 240,
          },
          {
            dataIndex: 'severity',
            render: (value) => dashboardStatusTag(String(value), statusLabelMap),
            title: '级别',
            width: 120,
          },
          {
            dataIndex: 'reason',
            render: (value) => (
              <Text ellipsis style={{ maxWidth: 460 }}>
                {String(value ?? '-')}
              </Text>
            ),
            title: '原因',
            width: 360,
          },
          {
            dataIndex: 'resolutionHint',
            render: (value) => (
              <Text ellipsis style={{ maxWidth: 340 }}>
                {String(value ?? '-')}
              </Text>
            ),
            title: '解除条件',
            width: 360,
          },
          {
            key: 'action',
            render: (_, row) => {
              const subjectType = blockerSubjectType(String(row.sourceType ?? ''));
              const actionHref = blockerActionHref(row, dashboard.version.id);
              return (
                <Space size={4}>
                  {actionHref ? (
                    <Button href={actionHref} size="small" type="link">
                      {row.actionLabel}
                    </Button>
                  ) : null}
                  {subjectType && row.id ? (
                    <Button
                      href={fullChainSubjectHref(subjectType, row.id)}
                      icon={<LinkOutlined />}
                      size="small"
                      type="link"
                    >
                      全链路
                    </Button>
                  ) : null}
                  {!actionHref && !(subjectType && row.id) ? <Text type="secondary">-</Text> : null}
                </Space>
              );
            },
            title: '操作',
            width: 180,
          },
        ]}
        dataSource={dashboard.blockers}
        locale={{
          emptyText: <Empty description="暂无阻塞项" image={Empty.PRESENTED_IMAGE_SIMPLE} />,
        }}
        pagination={false}
        rowKey={(row) => `${row.sourceType}-${row.id ?? row.title}`}
        scroll={{ x: 1490 }}
        size="small"
      />
    </div>
  );
}

type VersionDashboardRequirementTaskTablesProps = {
  dashboard: ProductVersionDashboard;
  statusLabelMap: Record<string, LabelItem>;
};

export function VersionDashboardRequirementTaskTables({
  dashboard,
  statusLabelMap,
}: VersionDashboardRequirementTaskTablesProps) {
  return (
    <div>
      <Text strong>需求与任务</Text>
      <Table<RequirementRecord>
        columns={[
          {
            dataIndex: 'id',
            render: (value) => (
              <Typography.Link
                href={internalHref('/delivery/requirements', {
                  requirement_id: String(value),
                })}
              >
                {String(value)}
              </Typography.Link>
            ),
            title: '需求编号',
            width: 160,
          },
          {
            dataIndex: 'title',
            render: (value) => (
              <Text ellipsis style={{ maxWidth: 260 }}>
                {String(value ?? '-')}
              </Text>
            ),
            title: '需求标题',
            width: 280,
          },
          {
            dataIndex: 'status',
            render: (value) => dashboardStatusTag(String(value), statusLabelMap),
            title: '状态',
            width: 120,
          },
          { dataIndex: 'priority', title: '优先级', width: 100 },
          { dataIndex: 'updatedAt', title: '更新时间', width: 170 },
          {
            key: 'action',
            render: (_, row) => (
              <Button
                href={fullChainSubjectHref('requirement', row.id)}
                icon={<LinkOutlined />}
                size="small"
                type="link"
              >
                全链路
              </Button>
            ),
            title: '操作',
            width: 110,
          },
        ]}
        dataSource={dashboard.requirements}
        locale={{ emptyText: '当前版本暂无需求' }}
        pagination={dashboard.requirements.length > 5 ? { pageSize: 5 } : false}
        rowKey="id"
        scroll={{ x: 940 }}
        size="small"
      />
      <Table<ProductVersionDashboard['tasks'][number]>
        columns={[
          {
            dataIndex: 'id',
            render: (value) => (
              <Typography.Link
                href={internalHref('/delivery/rd-tasks', {
                  task_id: String(value),
                })}
              >
                {String(value)}
              </Typography.Link>
            ),
            title: '任务编号',
            width: 160,
          },
          {
            dataIndex: 'label',
            render: (value) => (
              <Text ellipsis style={{ maxWidth: 260 }}>
                {String(value ?? '-')}
              </Text>
            ),
            title: '任务标题',
            width: 280,
          },
          { dataIndex: 'type', title: '类型', width: 130 },
          {
            dataIndex: 'status',
            render: (value) => dashboardStatusTag(String(value), statusLabelMap),
            title: '状态',
            width: 120,
          },
          { dataIndex: 'owner', title: '负责人', width: 120 },
          {
            key: 'action',
            render: (_, row) => (
              <Button href={fullChainSubjectHref('ai_task', row.id)} icon={<LinkOutlined />} size="small" type="link">
                全链路
              </Button>
            ),
            title: '操作',
            width: 110,
          },
        ]}
        dataSource={dashboard.tasks}
        locale={{ emptyText: '当前版本暂无 AI 任务' }}
        pagination={dashboard.tasks.length > 5 ? { pageSize: 5 } : false}
        rowKey="id"
        scroll={{ x: 920 }}
        size="small"
      />
    </div>
  );
}

type VersionDashboardQualityDeliveryTablesProps = {
  branchCreationSourceLabels: Record<ProductVersionBranchConfigRecord['creationSource'], string>;
  branchStatusLabels: Record<ProductVersionBranchConfigRecord['branchStatus'], LabelItem>;
  dashboard: ProductVersionDashboard;
  statusLabelMap: Record<string, LabelItem>;
};

export function VersionDashboardQualityDeliveryTables({
  branchCreationSourceLabels,
  branchStatusLabels,
  dashboard,
  statusLabelMap,
}: VersionDashboardQualityDeliveryTablesProps) {
  return (
    <div>
      <Text strong>质量与交付</Text>
      <Table<ProductVersionDashboard['bugs'][number]>
        columns={[
          {
            dataIndex: 'id',
            render: (value) => (
              <Typography.Link
                href={internalHref('/delivery/bugs', {
                  bug_id: String(value),
                })}
              >
                {String(value)}
              </Typography.Link>
            ),
            title: 'Bug 编号',
            width: 150,
          },
          {
            dataIndex: 'title',
            render: (value) => (
              <Text ellipsis style={{ maxWidth: 240 }}>
                {String(value ?? '-')}
              </Text>
            ),
            title: 'Bug 标题',
            width: 260,
          },
          {
            dataIndex: 'severity',
            render: (value) => dashboardStatusTag(String(value), statusLabelMap),
            title: '严重级别',
            width: 120,
          },
          {
            dataIndex: 'status',
            render: (value) => dashboardStatusTag(String(value), statusLabelMap),
            title: '状态',
            width: 120,
          },
          { dataIndex: 'assignee', title: '负责人', width: 120 },
          {
            key: 'action',
            render: (_, row) => (
              <Button href={fullChainSubjectHref('bug', row.id)} icon={<LinkOutlined />} size="small" type="link">
                全链路
              </Button>
            ),
            title: '操作',
            width: 110,
          },
        ]}
        dataSource={dashboard.bugs}
        locale={{ emptyText: '当前版本暂无 Bug' }}
        pagination={dashboard.bugs.length > 5 ? { pageSize: 5 } : false}
        rowKey="id"
        scroll={{ x: 900 }}
        size="small"
      />
      <Table<ProductVersionDashboard['codeInspectionReports'][number]>
        columns={[
          {
            dataIndex: 'repository_name',
            render: (value, row) => (
              <Typography.Link href={fullChainSubjectHref('code_inspection_report', row.id)}>
                {String(value ?? row.id)}
              </Typography.Link>
            ),
            title: '代码库',
            width: 180,
          },
          { dataIndex: 'branch', title: '分支', width: 170 },
          {
            dataIndex: 'risk_level',
            render: (value) => dashboardStatusTag(String(value), statusLabelMap),
            title: '风险',
            width: 120,
          },
          { dataIndex: 'finding_count', title: '问题数', width: 100 },
          {
            dataIndex: 'summary',
            render: (value) => (
              <Text ellipsis style={{ maxWidth: 300 }}>
                {String(value ?? '-')}
              </Text>
            ),
            title: '摘要',
            width: 320,
          },
          {
            dataIndex: 'created_at',
            render: (value) => dashboardDate(String(value ?? '')),
            title: '创建时间',
            width: 170,
          },
          {
            key: 'action',
            render: (_, row) => (
              <Space size={4}>
                <Button
                  href={internalHref('/governance/code-inspections', {
                    source_id: row.id,
                  })}
                  icon={<LinkOutlined />}
                  size="small"
                  type="link"
                >
                  详情
                </Button>
                <Button href={fullChainSubjectHref('code_inspection_report', row.id)} size="small" type="link">
                  全链路
                </Button>
              </Space>
            ),
            title: '操作',
            width: 150,
          },
        ]}
        dataSource={dashboard.codeInspectionReports}
        locale={{ emptyText: '当前版本暂无代码巡检报告' }}
        pagination={dashboard.codeInspectionReports.length > 5 ? { pageSize: 5 } : false}
        rowKey="id"
        scroll={{ x: 1210 }}
        size="small"
      />
      <Text strong>分支质量治理</Text>
      <Table<ProductVersionDashboard['branchQualityGovernance'][number]>
        columns={[
          {
            dataIndex: 'repositoryName',
            render: (value, row) => (
              <Typography.Link
                href={internalHref('/governance/code-inspections', {
                  repository_id: row.repositoryId,
                  version_id: dashboard.version.id,
                })}
              >
                {String(value ?? '-')}
              </Typography.Link>
            ),
            title: '代码库',
            width: 180,
          },
          {
            dataIndex: 'branch',
            render: (value, row) => (
              <Typography.Link
                href={
                  row.branchConfigId
                    ? internalHref('/delivery/versions', {
                        branch_config_id: row.branchConfigId,
                        version_id: dashboard.version.id,
                      })
                    : internalHref('/governance/code-inspections', {
                        repository_id: row.repositoryId,
                        version_id: dashboard.version.id,
                      })
                }
              >
                {String(value ?? '-')}
              </Typography.Link>
            ),
            title: '分支',
            width: 200,
          },
          {
            dataIndex: 'status',
            render: (value) => dashboardStatusTag(String(value), statusLabelMap),
            title: '治理状态',
            width: 120,
          },
          { dataIndex: 'reportCount', title: '报告数', width: 100 },
          { dataIndex: 'findingCount', title: '问题数', width: 100 },
          { dataIndex: 'severeFindingCount', title: '严重问题', width: 110 },
          { dataIndex: 'activeSevereFindingCount', title: '活跃严重', width: 110 },
          { dataIndex: 'uncoveredSevereBugCount', title: '缺 Bug', width: 100 },
          { dataIndex: 'uncoveredSevereTaskCount', title: '待推进任务', width: 120 },
          { dataIndex: 'falsePositiveCount', title: '误报忽略', width: 110 },
          { dataIndex: 'acceptedRiskCount', title: '接受风险', width: 110 },
          { dataIndex: 'expiredAcceptedRiskCount', title: '过期风险', width: 110 },
          { dataIndex: 'pendingSuppressionCount', title: '待审批忽略', width: 120 },
          { dataIndex: 'qualityGateFailedReportCount', title: '门禁失败报告', width: 130 },
          { dataIndex: 'qualityGateViolationCount', title: '门禁失败项', width: 120 },
          {
            key: 'latestReport',
            render: (_, row) =>
              row.latestReportId ? (
                <Typography.Link
                  href={internalHref('/governance/code-inspections', {
                    source_id: row.latestReportId,
                  })}
                >
                  <Text ellipsis style={{ maxWidth: 240 }}>
                    {row.latestReportSummary ?? row.latestReportId}
                  </Text>
                </Typography.Link>
              ) : (
                <Text type="secondary">-</Text>
              ),
            title: '最近报告',
            width: 260,
          },
          { dataIndex: 'latestReportTime', title: '最近时间', width: 170 },
        ]}
        dataSource={dashboard.branchQualityGovernance}
        locale={{ emptyText: '当前版本暂无分支质量治理数据' }}
        pagination={dashboard.branchQualityGovernance.length > 5 ? { pageSize: 5 } : false}
        rowKey="id"
        scroll={{ x: 2160 }}
        size="small"
      />
      <Table<ProductVersionDashboard['codeReviewReports'][number]>
        columns={[
          {
            dataIndex: 'summary',
            render: (value, row) => (
              <Typography.Link
                href={internalHref('/delivery/rd-tasks', {
                  code_review_report_id: row.id,
                })}
              >
                {String(value ?? row.id)}
              </Typography.Link>
            ),
            title: '代码评审',
            width: 260,
          },
          {
            dataIndex: 'taskTitle',
            render: (value, row) => (
              <Typography.Link
                href={internalHref('/delivery/rd-tasks', {
                  task_id: row.taskId,
                })}
              >
                {String(value ?? '-')}
              </Typography.Link>
            ),
            title: '关联任务',
            width: 220,
          },
          {
            dataIndex: 'riskLevel',
            render: (value) => dashboardStatusTag(String(value), statusLabelMap),
            title: '风险',
            width: 120,
          },
          {
            dataIndex: 'status',
            render: (value) => dashboardStatusTag(String(value), statusLabelMap),
            title: '状态',
            width: 120,
          },
          {
            dataIndex: 'executorName',
            title: '执行器',
            width: 140,
          },
          {
            dataIndex: 'findingCount',
            title: '问题数',
            width: 100,
          },
          {
            key: 'action',
            render: (_, row) => (
              <Space size={4}>
                <Button
                  href={internalHref('/delivery/rd-tasks', {
                    code_review_report_id: row.id,
                  })}
                  icon={<LinkOutlined />}
                  size="small"
                  type="link"
                >
                  详情
                </Button>
                <Button href={fullChainSubjectHref('code_review_report', row.id)} size="small" type="link">
                  全链路
                </Button>
              </Space>
            ),
            title: '操作',
            width: 150,
          },
        ]}
        dataSource={dashboard.codeReviewReports}
        locale={{ emptyText: '当前版本暂无代码评审报告' }}
        pagination={dashboard.codeReviewReports.length > 5 ? { pageSize: 5 } : false}
        rowKey="id"
        scroll={{ x: 1110 }}
        size="small"
      />
      <Table<ProductVersionDashboard['knowledgeDeposits'][number]>
        columns={[
          {
            dataIndex: 'title',
            render: (value, row) => (
              <Typography.Link href={fullChainSubjectHref('knowledge_deposit', row.id)}>
                {String(value ?? row.id)}
              </Typography.Link>
            ),
            title: '知识沉淀',
            width: 260,
          },
          {
            dataIndex: 'taskTitle',
            render: (value, row) => (
              <Typography.Link
                href={internalHref('/delivery/rd-tasks', {
                  task_id: row.aiTaskId,
                })}
              >
                {String(value ?? '-')}
              </Typography.Link>
            ),
            title: '来源任务',
            width: 220,
          },
          {
            dataIndex: 'status',
            render: (value) => dashboardStatusTag(String(value), statusLabelMap),
            title: '状态',
            width: 120,
          },
          {
            dataIndex: 'knowledgeDocumentId',
            render: (value, row) => (
              <Space orientation="vertical" size={0}>
                <Text ellipsis style={{ maxWidth: 220 }}>
                  {row.knowledgeDocumentTitle ?? String(value ?? '-')}
                </Text>
                {row.knowledgeDocumentTitle && value ? (
                  <Text ellipsis style={{ maxWidth: 220 }} type="secondary">
                    {String(value)}
                  </Text>
                ) : null}
              </Space>
            ),
            title: '知识文档',
            width: 240,
          },
          {
            key: 'knowledgeIndexHealth',
            render: (_, row) => (
              <Space orientation="vertical" size={2}>
                <Space size={4} wrap>
                  {dashboardStatusTag(row.knowledgeIndexStatus ?? '-', knowledgeIndexStatusLabelMap)}
                  {dashboardStatusTag(row.knowledgeRetrievalMode, knowledgeRetrievalModeLabelMap)}
                </Space>
                <Text type="secondary">
                  分块 {row.knowledgeChunkCount} / 向量 {row.knowledgeEmbeddingChunkCount}
                </Text>
                {row.knowledgeIndexError ? (
                  <Text ellipsis style={{ maxWidth: 240 }} type="secondary">
                    {row.knowledgeIndexError}
                  </Text>
                ) : null}
              </Space>
            ),
            title: '索引健康',
            width: 270,
          },
          {
            dataIndex: 'updatedAt',
            title: '更新时间',
            width: 170,
          },
          {
            key: 'action',
            render: (_, row) => (
              <Button
                href={fullChainSubjectHref('knowledge_deposit', row.id)}
                icon={<LinkOutlined />}
                size="small"
                type="link"
              >
                全链路
              </Button>
            ),
            title: '操作',
            width: 110,
          },
        ]}
        dataSource={dashboard.knowledgeDeposits}
        locale={{ emptyText: '当前版本暂无知识沉淀' }}
        pagination={dashboard.knowledgeDeposits.length > 5 ? { pageSize: 5 } : false}
        rowKey="id"
        scroll={{ x: 1350 }}
        size="small"
      />
      <Table<ProductVersionDashboard['branchConfigs'][number]>
        columns={[
          { dataIndex: 'repositoryName', title: '代码库', width: 180 },
          { dataIndex: 'baseBranch', title: '基准分支', width: 150 },
          {
            dataIndex: 'workingBranch',
            render: (value, row) => (
              <Typography.Link
                href={internalHref('/delivery/versions', {
                  branch_config_id: row.id,
                  version_id: row.versionId,
                })}
              >
                {String(value ?? '-')}
              </Typography.Link>
            ),
            title: '开发分支',
            width: 200,
          },
          {
            dataIndex: 'branchStatus',
            render: (_, row) => {
              const statusLabel = branchStatusLabels[row.branchStatus];
              return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
            },
            title: '状态',
            width: 120,
          },
          {
            dataIndex: 'creationSource',
            render: (_, row) => branchCreationSourceLabels[row.creationSource],
            title: '来源',
            width: 140,
          },
          {
            key: 'action',
            render: (_, row) => (
              <Button
                href={fullChainSubjectHref('product_version_branch_config', row.id)}
                icon={<LinkOutlined />}
                size="small"
                type="link"
              >
                全链路
              </Button>
            ),
            title: '操作',
            width: 110,
          },
        ]}
        dataSource={dashboard.branchConfigs}
        locale={{ emptyText: '当前版本暂无代码分支配置' }}
        pagination={false}
        rowKey="id"
        scroll={{ x: 900 }}
        size="small"
      />
      <Table<ProductVersionDashboard['releases'][number]>
        columns={[
          {
            dataIndex: 'id',
            render: (value) => (
              <Typography.Link
                href={internalHref('/governance/devops', {
                  version_id: dashboard.version.id,
                })}
              >
                {String(value ?? '-')}
              </Typography.Link>
            ),
            title: '发布编号',
            width: 180,
          },
          { dataIndex: 'jobName', title: '作业', width: 200 },
          { dataIndex: 'buildId', title: '构建号', width: 130 },
          {
            dataIndex: 'status',
            render: (value) => dashboardStatusTag(String(value), statusLabelMap),
            title: '状态',
            width: 120,
          },
          { dataIndex: 'createdAt', title: '时间', width: 170 },
          {
            key: 'action',
            render: (_, row) => (
              <Button
                href={fullChainSubjectHref('jenkins_release', row.id)}
                icon={<LinkOutlined />}
                size="small"
                type="link"
              >
                全链路
              </Button>
            ),
            title: '操作',
            width: 110,
          },
        ]}
        dataSource={dashboard.releases}
        locale={{ emptyText: '当前版本暂无发布记录' }}
        pagination={dashboard.releases.length > 5 ? { pageSize: 5 } : false}
        rowKey="id"
        scroll={{ x: 910 }}
        size="small"
      />
    </div>
  );
}
