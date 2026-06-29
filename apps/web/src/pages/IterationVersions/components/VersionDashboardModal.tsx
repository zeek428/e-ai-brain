import { LinkOutlined } from '@ant-design/icons';
import { Alert, Button, Modal, Space, Spin } from 'antd';

import type {
  ProductVersionBranchConfigRecord,
  ProductVersionRecord,
  RequirementRecord,
} from '../../../data/management';
import {
  fullChainSubjectHref,
  type ProductVersionDashboard,
} from '../../../services/aiBrain';
import {
  VersionDashboardActions,
  VersionDashboardDeliveryOverview,
  VersionDashboardGovernanceConclusion,
  VersionDashboardHealthSummary,
  VersionDashboardMetrics,
  VersionDashboardReadinessChecklist,
  VersionDashboardStatusDistribution,
  VersionDashboardStatusImpactNotice,
} from './VersionDashboardSummary';
import {
  VersionDashboardBlockersTable,
  VersionDashboardQualityDeliveryTables,
  VersionDashboardRequirementTaskTables,
  VersionDashboardStatusImpactTable,
} from './VersionDashboardTables';
import {
  buildDashboardHealthItems,
  buildDashboardGovernanceConclusion,
  buildDashboardReadinessItems,
  buildStatusImpactRows,
  buildStatusLabelMap,
  dashboardDate,
  type LabelItem,
} from './versionDashboardModel';

type VersionDashboardModalProps = {
  branchCreationSourceLabels: Record<
    ProductVersionBranchConfigRecord['creationSource'],
    string
  >;
  branchStatusLabels: Record<
    ProductVersionBranchConfigRecord['branchStatus'],
    LabelItem
  >;
  dashboard?: ProductVersionDashboard;
  loading?: boolean;
  onAdvanceVersion: (version: ProductVersionRecord) => void;
  onClose: () => void;
  onMaintainBranches: (version: ProductVersionRecord) => void;
  onViewRequirements: (version: ProductVersionRecord) => void;
  open: boolean;
  requirementStatusLabels: Record<RequirementRecord['status'], LabelItem>;
  version?: ProductVersionRecord;
  versionStatusLabels: Record<ProductVersionRecord['status'], LabelItem>;
};

export function VersionDashboardModal({
  branchCreationSourceLabels,
  branchStatusLabels,
  dashboard,
  loading,
  onAdvanceVersion,
  onClose,
  onMaintainBranches,
  onViewRequirements,
  open,
  requirementStatusLabels,
  version,
  versionStatusLabels,
}: VersionDashboardModalProps) {
  const dashboardVersion = dashboard?.version ?? version;
  const statusLabelMap = buildStatusLabelMap(
    versionStatusLabels,
    requirementStatusLabels,
  );
  const dashboardStatusImpactRows = buildStatusImpactRows(
    dashboard?.statusImpact,
  );
  const dashboardGovernanceConclusion =
    buildDashboardGovernanceConclusion(dashboard);
  const dashboardHealthItems = buildDashboardHealthItems(dashboard);
  const dashboardReadinessItems = buildDashboardReadinessItems(dashboard);

  return (
    <Modal
      destroyOnHidden
      footer={null}
      onCancel={onClose}
      open={open}
      title={
        dashboardVersion ? `版本总览 · ${dashboardVersion.code}` : '版本总览'
      }
      width={1180}
    >
      <Spin spinning={loading ?? false}>
        {dashboard ? (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Alert
              action={
                <Button
                  href={fullChainSubjectHref(
                    'product_version',
                    dashboard.version.id,
                  )}
                  icon={<LinkOutlined />}
                  size="small"
                >
                  版本全链路
                </Button>
              }
              description={`开始时间：${dashboardDate(dashboard.version.startDate)}；计划发布时间：${dashboardDate(
                dashboard.version.releaseDate,
              )}`}
              title={`${dashboard.version.productName ?? dashboard.version.productId ?? '-'} · ${
                dashboard.version.name
              } · ${versionStatusLabels[dashboard.version.status].label}`}
              type={dashboard.summary.blockers ? 'warning' : 'success'}
            />
            {dashboard.accessIssues.map((issue) => (
              <Alert
                key={`${issue.section}-${issue.code}`}
                showIcon
                title={issue.message}
                type="warning"
              />
            ))}
            <VersionDashboardActions
              dashboard={dashboard}
              onAdvanceVersion={onAdvanceVersion}
              onMaintainBranches={onMaintainBranches}
              onViewRequirements={onViewRequirements}
              versionStatusLabels={versionStatusLabels}
            />
            <VersionDashboardGovernanceConclusion
              conclusion={dashboardGovernanceConclusion}
            />
            <VersionDashboardMetrics dashboard={dashboard} />
            <VersionDashboardDeliveryOverview
              items={dashboardReadinessItems}
            />
            <VersionDashboardReadinessChecklist
              items={dashboardReadinessItems}
            />
            <VersionDashboardHealthSummary items={dashboardHealthItems} />
            <VersionDashboardStatusDistribution
              dashboard={dashboard}
              statusLabelMap={statusLabelMap}
            />
            <VersionDashboardStatusImpactNotice
              dashboard={dashboard}
              versionStatusLabels={versionStatusLabels}
            />
            {dashboard.statusImpact ? (
              <VersionDashboardStatusImpactTable
                rows={dashboardStatusImpactRows}
                statusLabelMap={statusLabelMap}
              />
            ) : null}
            <VersionDashboardBlockersTable
              dashboard={dashboard}
              statusLabelMap={statusLabelMap}
            />
            <VersionDashboardRequirementTaskTables
              dashboard={dashboard}
              statusLabelMap={statusLabelMap}
            />
            <VersionDashboardQualityDeliveryTables
              branchCreationSourceLabels={branchCreationSourceLabels}
              branchStatusLabels={branchStatusLabels}
              dashboard={dashboard}
              statusLabelMap={statusLabelMap}
            />
          </Space>
        ) : null}
      </Spin>
    </Modal>
  );
}
