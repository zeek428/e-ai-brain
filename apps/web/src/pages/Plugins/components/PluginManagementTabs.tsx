import { Tabs } from 'antd';

import type {
  AiExecutorRunnerRecord,
  PluginActionRecord,
  PluginConnectionRecord,
  PluginMarketplaceItem,
  PluginRecord,
} from '../../../services/aiBrain';
import { PluginActionTable } from './PluginActionTable';
import { PluginConnectionTable } from './PluginConnectionTable';
import { PluginMarketplaceTable } from './PluginMarketplaceTable';
import { PluginRunnerTable } from './PluginRunnerTable';
import { PluginTable } from './PluginTable';

type SelectOption = {
  label: string;
  value: string;
};

type PluginManagementTabsProps = {
  actions: PluginActionRecord[];
  connectionById: Map<string, PluginConnectionRecord>;
  connectionEnvironmentFilter?: string;
  connectionEnvironmentLabels: Map<string, string>;
  connectionEnvironmentOptions: SelectOption[];
  connections: PluginConnectionRecord[];
  formatWriteTarget: (writeTarget?: string | null) => string;
  loading: boolean;
  marketplaceItems: PluginMarketplaceItem[];
  onCopyOfficialPlugin: (plugin: PluginRecord) => void;
  onCopyRunnerSetupCommand: (command: string) => void;
  onCreateAction: () => void;
  onCreateActionForMarketplacePlugin: (item: PluginMarketplaceItem) => void;
  onCreateConnection: () => void;
  onCreateConnectionForPlugin: (pluginId?: string | null) => void;
  onCreatePlugin: () => void;
  onCreateRunner: () => void;
  onDeleteAction: (action: PluginActionRecord) => void;
  onDeleteConnection: (connection: PluginConnectionRecord) => void;
  onDeletePlugin: (plugin: PluginRecord) => void;
  onDeleteRunner: (runner: AiExecutorRunnerRecord) => void;
  onDownloadRunnerInstallPackage: (runner: AiExecutorRunnerRecord) => void;
  onEditAction: (action: PluginActionRecord) => void;
  onEditConnection: (connection: PluginConnectionRecord) => void;
  onEditPlugin: (plugin: PluginRecord) => void;
  onEditRunner: (runner: AiExecutorRunnerRecord) => void;
  onEnvironmentFilterChange: (environment?: string) => void;
  onOpenRunnerLogs: (runner: AiExecutorRunnerRecord) => void;
  onReload: () => void;
  onRotateRunnerToken: (runner: AiExecutorRunnerRecord) => void;
  onRunAction: (action: PluginActionRecord) => void;
  onTestConnection: (connection: PluginConnectionRecord) => void;
  onTestRunner: (runner: AiExecutorRunnerRecord) => void;
  onTrialAction: (action: PluginActionRecord) => void;
  pluginById: Map<string, PluginRecord>;
  plugins: PluginRecord[];
  runners: AiExecutorRunnerRecord[];
  testingConnectionId?: string;
  testingRunnerId?: string;
};

export function PluginManagementTabs({
  actions,
  connectionById,
  connectionEnvironmentFilter,
  connectionEnvironmentLabels,
  connectionEnvironmentOptions,
  connections,
  formatWriteTarget,
  loading,
  marketplaceItems,
  onCopyOfficialPlugin,
  onCopyRunnerSetupCommand,
  onCreateAction,
  onCreateActionForMarketplacePlugin,
  onCreateConnection,
  onCreateConnectionForPlugin,
  onCreatePlugin,
  onCreateRunner,
  onDeleteAction,
  onDeleteConnection,
  onDeletePlugin,
  onDeleteRunner,
  onDownloadRunnerInstallPackage,
  onEditAction,
  onEditConnection,
  onEditPlugin,
  onEditRunner,
  onEnvironmentFilterChange,
  onOpenRunnerLogs,
  onReload,
  onRotateRunnerToken,
  onRunAction,
  onTestConnection,
  onTestRunner,
  onTrialAction,
  pluginById,
  plugins,
  runners,
  testingConnectionId,
  testingRunnerId,
}: PluginManagementTabsProps) {
  return (
    <Tabs
      defaultActiveKey="plugins"
      items={[
        {
          key: 'marketplace',
          label: '插件市场',
          children: (
            <PluginMarketplaceTable
              items={marketplaceItems}
              loading={loading}
              onCreateAction={onCreateActionForMarketplacePlugin}
              onCreateConnection={onCreateConnectionForPlugin}
              onReload={onReload}
            />
          ),
        },
        {
          key: 'plugins',
          label: '插件',
          children: (
            <PluginTable
              loading={loading}
              plugins={plugins}
              onCopyOfficialPlugin={onCopyOfficialPlugin}
              onCreatePlugin={onCreatePlugin}
              onDeletePlugin={onDeletePlugin}
              onEditPlugin={onEditPlugin}
              onReload={onReload}
            />
          ),
        },
        {
          key: 'connections',
          label: '连接',
          children: (
            <PluginConnectionTable
              connections={connections}
              environmentFilter={connectionEnvironmentFilter}
              environmentLabels={connectionEnvironmentLabels}
              environmentOptions={connectionEnvironmentOptions}
              loading={loading}
              pluginById={pluginById}
              testingConnectionId={testingConnectionId}
              onCreateConnection={onCreateConnection}
              onDeleteConnection={onDeleteConnection}
              onEditConnection={onEditConnection}
              onEnvironmentFilterChange={onEnvironmentFilterChange}
              onReload={onReload}
              onTestConnection={onTestConnection}
            />
          ),
        },
        {
          key: 'runners',
          label: '执行器',
          children: (
            <PluginRunnerTable
              loading={loading}
              runners={runners}
              testingRunnerId={testingRunnerId}
              onCopySetupCommand={onCopyRunnerSetupCommand}
              onCreateRunner={onCreateRunner}
              onDeleteRunner={onDeleteRunner}
              onDownloadInstallPackage={onDownloadRunnerInstallPackage}
              onEditRunner={onEditRunner}
              onOpenLogs={onOpenRunnerLogs}
              onReload={onReload}
              onRotateToken={onRotateRunnerToken}
              onTestRunner={onTestRunner}
            />
          ),
        },
        {
          key: 'actions',
          label: '动作',
          children: (
            <PluginActionTable
              actions={actions}
              connectionById={connectionById}
              formatWriteTarget={formatWriteTarget}
              loading={loading}
              pluginById={pluginById}
              onCreateAction={onCreateAction}
              onDeleteAction={onDeleteAction}
              onEditAction={onEditAction}
              onReload={onReload}
              onRunAction={onRunAction}
              onTrialAction={onTrialAction}
            />
          ),
        },
      ]}
    />
  );
}
